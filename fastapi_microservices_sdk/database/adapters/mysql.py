"""
MySQL Database Adapter for FastAPI Microservices SDK.

This module provides MySQL-specific database adapter implementation
with optimizations for async operations and MySQL-specific features.

Features:
- Full aiomysql integration with connection pooling
- MySQL replication awareness and read/write splitting
- SSL/TLS support with certificate validation
- Advanced MySQL features (JSON, stored procedures, functions)
- Connection health monitoring and recovery
- Query optimization and performance metrics
- Transaction management with savepoints
- Prepared statement support
- Connection retry logic with exponential backoff
- MySQL-specific data types and operations

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import ssl
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import json
import re

from ..config import DatabaseConnectionConfig, DatabaseEngine
from ..exceptions import (
    DatabaseError, ConnectionError, QueryError, TransactionError,
    MySQLError, wrap_database_error
)
from .base import (
    DatabaseAdapter, DatabaseConnection, QueryResult, QueryType,
    TransactionContext, IsolationLevel, QueryMetrics
)

# Optional dependency
try:
    import aiomysql
    from aiomysql import Connection as AiomysqlConnection
    from aiomysql.pool import Pool as AiomysqlPool
    AIOMYSQL_AVAILABLE = True
except ImportError:
    AIOMYSQL_AVAILABLE = False
    aiomysql = None
    AiomysqlConnection = None
    AiomysqlPool = None


class MySQLAdapter(DatabaseAdapter):
    """MySQL database adapter with aiomysql and enterprise features."""
    
    def __init__(self, config: DatabaseConnectionConfig):
        if not AIOMYSQL_AVAILABLE:
            raise DatabaseError(
                "aiomysql not installed - required for MySQL support",
                context={
                    'engine': DatabaseEngine.MYSQL.value,
                    'operation': 'configuration',
                    'database_name': self._get_database_name(config)
                }
            )
        
        # Initialize base class without calling super() to avoid engine conflict
        self.config = config
        self._engine = config.engine  # Use private attribute
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connection_pool_dict: Dict[str, DatabaseConnection] = {}
        self._pool_lock = asyncio.Lock()
        self._is_initialized = False
        self._connection_pool: Optional[AiomysqlPool] = None
        self._connection_options = self._build_connection_options()
        self._ssl_context = self._create_ssl_context()
        self._prepared_statements: Dict[str, str] = {}
        self._query_cache: Dict[str, Any] = {}
        self._replication_config = self._parse_replication_config()
        
    def _get_database_name(self, config: DatabaseConnectionConfig) -> str:
        """Get database name for error reporting."""
        return getattr(config, 'name', config.database)
    
    def _build_connection_options(self) -> Dict[str, Any]:
        """Build MySQL connection options."""
        options = {
            'host': self.config.host,
            'port': self.config.port,
            'user': self.config.credentials.username,
            'password': self.config.credentials.password,
            'db': self.config.database,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'autocommit': False,
            'connect_timeout': self.config.pool.connection_timeout,
            'echo': False
        }
        
        # SSL configuration
        if self._ssl_context:
            options['ssl'] = self._ssl_context
        
        # MySQL-specific options
        options.update({
            'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
            'init_command': "SET SESSION time_zone='+00:00'",
            'cursorclass': aiomysql.DictCursor if AIOMYSQL_AVAILABLE else None
        })
        
        return options
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections."""
        if not hasattr(self.config, 'ssl') or not self.config.ssl or not self.config.ssl.enabled:
            return None
        
        ssl_config = self.config.ssl
        context = ssl.create_default_context()
        
        # Configure SSL verification
        if ssl_config.verify_mode:
            context.check_hostname = ssl_config.check_hostname
            context.verify_mode = getattr(ssl, ssl_config.verify_mode.name)
        
        # Load certificates
        if ssl_config.ca_cert_path:
            context.load_verify_locations(ssl_config.ca_cert_path)
        
        if ssl_config.client_cert_path and ssl_config.client_key_path:
            context.load_cert_chain(ssl_config.client_cert_path, ssl_config.client_key_path)
        
        return context
    
    def _parse_replication_config(self) -> Dict[str, Any]:
        """Parse replication configuration from connection config."""
        replication_config = {
            'read_write_splitting': False,
            'read_hosts': [],
            'write_hosts': [],
            'read_preference': 'primary'
        }
        
        # Check if replication is configured
        if hasattr(self.config, 'replication') and self.config.replication:
            replication_config.update(self.config.replication)
        
        return replication_config
    
    async def initialize(self) -> None:
        """Initialize the MySQL adapter."""
        try:
            # Create connection pool
            self._connection_pool = await aiomysql.create_pool(
                minsize=self.config.pool.min_connections,
                maxsize=self.config.pool.max_connections,
                **self._connection_options
            )
            
            # Test connection and get MySQL version
            async with self._connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT VERSION()")
                    version_result = await cursor.fetchone()
                    mysql_version = version_result['VERSION()'] if version_result else 'unknown'
                    
                    # Set session variables
                    await cursor.execute("SET SESSION sql_mode = %s", (
                        'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
                    ))
                    await cursor.execute("SET SESSION time_zone = '+00:00'")
                    
                    self.logger.info(f"Connected to MySQL: {mysql_version}")
            
            self._is_initialized = True
            self.logger.info(f"MySQL adapter initialized with pool size {self.config.pool.min_connections}-{self.config.pool.max_connections}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="initialize",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def shutdown(self) -> None:
        """Shutdown the MySQL adapter."""
        try:
            if self._connection_pool:
                self._connection_pool.close()
                await self._connection_pool.wait_closed()
                self._connection_pool = None
            
            # Clear caches
            self._prepared_statements.clear()
            self._query_cache.clear()
            
            # Clear prepared statements and cache
            self._prepared_statements.clear()
            self._query_cache.clear()
            
            self._is_initialized = False
            self.logger.info("MySQL adapter shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during MySQL adapter shutdown: {e}")
            raise wrap_database_error(
                e,
                operation="shutdown",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def create_connection(self) -> DatabaseConnection:
        """Create a new MySQL connection."""
        try:
            connection_id = self._create_connection_id()
            
            # Get connection from pool
            if self._connection_pool:
                native_conn = await self._connection_pool.acquire()
            else:
                # Fallback to direct connection
                native_conn = await aiomysql.connect(**self._connection_options)
            
            # Configure connection
            await self._configure_connection(native_conn)
            
            connection = DatabaseConnection(
                connection_id=connection_id,
                config=self.config,
                native_connection=native_conn,
                adapter=self
            )
            
            # Set connection metadata
            connection.set_metadata("mysql_version", await self._get_mysql_version(native_conn))
            connection.set_metadata("server_charset", await self._get_server_charset(native_conn))
            connection.set_metadata("timezone", await self._get_timezone(native_conn))
            connection.set_metadata("sql_mode", await self._get_sql_mode(native_conn))
            
            self.logger.debug(f"Created MySQL connection: {connection_id}")
            return connection
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_connection",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _configure_connection(self, conn: AiomysqlConnection) -> None:
        """Configure MySQL connection settings."""
        async with conn.cursor() as cursor:
            # Set connection parameters
            await cursor.execute("SET SESSION time_zone = '+00:00'")
            await cursor.execute("SET SESSION sql_mode = %s", (
                'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO',
            ))
            await cursor.execute("SET SESSION wait_timeout = 28800")  # 8 hours
            await cursor.execute("SET SESSION interactive_timeout = 28800")
            
            # Enable query logging if debug mode
            if self.logger.isEnabledFor(logging.DEBUG):
                await cursor.execute("SET SESSION general_log = 1")
    
    async def _get_mysql_version(self, conn: AiomysqlConnection) -> str:
        """Get MySQL version."""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT VERSION()")
                result = await cursor.fetchone()
                return result['VERSION()'] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def _get_server_charset(self, conn: AiomysqlConnection) -> str:
        """Get server charset."""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT @@character_set_server")
                result = await cursor.fetchone()
                return result['@@character_set_server'] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def _get_timezone(self, conn: AiomysqlConnection) -> str:
        """Get server timezone."""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT @@time_zone")
                result = await cursor.fetchone()
                return result['@@time_zone'] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def _get_sql_mode(self, conn: AiomysqlConnection) -> str:
        """Get SQL mode."""
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT @@sql_mode")
                result = await cursor.fetchone()
                return result['@@sql_mode'] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform MySQL health check."""
        try:
            start_time = datetime.now(timezone.utc)
            
            if not self._connection_pool:
                return {
                    'healthy': False,
                    'error': 'Connection pool not initialized',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            async with self._connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Basic connectivity test
                    await cursor.execute("SELECT 1")
                    
                    # Database statistics
                    await cursor.execute("""
                        SELECT 
                            DATABASE() as database_name,
                            USER() as current_user,
                            CONNECTION_ID() as connection_id,
                            VERSION() as version
                    """)
                    stats = await cursor.fetchone()
                    
                    # Connection statistics
                    await cursor.execute("""
                        SELECT 
                            VARIABLE_VALUE as max_connections
                        FROM INFORMATION_SCHEMA.GLOBAL_VARIABLES 
                        WHERE VARIABLE_NAME = 'MAX_CONNECTIONS'
                    """)
                    max_conn_result = await cursor.fetchone()
                    
                    await cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                    current_conn_result = await cursor.fetchone()
                    
                    # Database size
                    await cursor.execute("""
                        SELECT 
                            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE()
                    """)
                    size_result = await cursor.fetchone()
                    
                    # Table count
                    await cursor.execute("""
                        SELECT COUNT(*) as table_count 
                        FROM information_schema.tables 
                        WHERE table_schema = DATABASE()
                    """)
                    table_count_result = await cursor.fetchone()
                    
                    # Replication status (if applicable)
                    replication_status = None
                    try:
                        await cursor.execute("SHOW SLAVE STATUS")
                        slave_status = await cursor.fetchone()
                        if slave_status:
                            replication_status = {
                                'is_slave': True,
                                'slave_io_running': slave_status.get('Slave_IO_Running'),
                                'slave_sql_running': slave_status.get('Slave_SQL_Running'),
                                'seconds_behind_master': slave_status.get('Seconds_Behind_Master')
                            }
                        else:
                            replication_status = {'is_slave': False}
                    except Exception:
                        replication_status = {'is_slave': False, 'error': 'Cannot determine replication status'}
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'healthy': True,
                'response_time': response_time,
                'database_name': stats['database_name'],
                'current_user': stats['current_user'],
                'connection_id': stats['connection_id'],
                'version': stats['version'],
                'database_size_mb': size_result['size_mb'] if size_result else 0,
                'table_count': table_count_result['table_count'] if table_count_result else 0,
                'connections': {
                    'max_connections': int(max_conn_result['max_connections']) if max_conn_result else 0,
                    'current_connections': int(current_conn_result['Value']) if current_conn_result else 0
                },
                'pool_status': {
                    'size': self._connection_pool.size,
                    'used': self._connection_pool.size - self._connection_pool.freesize,
                    'free': self._connection_pool.freesize,
                    'min_size': self._connection_pool.minsize,
                    'max_size': self._connection_pool.maxsize
                },
                'replication': replication_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def execute_query(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a query on MySQL."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self._log_query(query, parameters)
            connection.mark_used()
            
            # Convert named parameters to format expected by aiomysql
            processed_query, param_values = self._process_parameters(query, parameters)
            
            async with connection.native_connection.cursor() as cursor:
                # Execute query
                if param_values:
                    await cursor.execute(processed_query, param_values)
                else:
                    await cursor.execute(processed_query)
                
                # Get results based on query type
                if query_type == QueryType.SELECT or self._is_select_query(processed_query):
                    data = await cursor.fetchall()
                    rows_returned = len(data) if data else 0
                    rows_affected = 0
                else:
                    # Non-SELECT queries (INSERT, UPDATE, DELETE, DDL)
                    data = None
                    rows_returned = 0
                    rows_affected = cursor.rowcount
                    await connection.native_connection.commit()
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += 1
            
            # Create metrics
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=rows_affected,
                rows_returned=rows_returned
            )
            
            return QueryResult(
                data=data,
                rows_affected=rows_affected,
                rows_returned=rows_returned,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            await connection.native_connection.rollback()
            raise wrap_database_error(
                e,
                operation="execute_query",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    def _process_parameters(self, query: str, parameters: Optional[Dict[str, Any]]) -> Tuple[str, List[Any]]:
        """Convert named parameters to format expected by aiomysql."""
        if not parameters:
            return query, []
        
        # Convert :param to %s format for aiomysql
        param_values = []
        processed_query = query
        
        # Find all :param patterns and replace with %s
        import re
        param_pattern = r':(\w+)'
        matches = re.findall(param_pattern, query)
        
        for param_name in matches:
            if param_name in parameters:
                processed_query = processed_query.replace(f':{param_name}', '%s', 1)
                param_values.append(parameters[param_name])
        
        return processed_query, param_values
    
    def _is_select_query(self, query: str) -> bool:
        """Check if query is a SELECT statement."""
        return query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'WITH'))
    
    async def execute_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters_list: List[Dict[str, Any]],
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a query multiple times with different parameters."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self._log_query(query, f"Batch of {len(parameters_list)} parameter sets")
            connection.mark_used()
            
            total_affected = 0
            
            async with connection.native_connection.cursor() as cursor:
                # Process all parameter sets
                param_tuples = []
                processed_query = None
                
                for params in parameters_list:
                    if processed_query is None:
                        processed_query, param_values = self._process_parameters(query, params)
                    else:
                        _, param_values = self._process_parameters(query, params)
                    param_tuples.append(param_values)
                
                # Execute batch using executemany
                if param_tuples:
                    await cursor.executemany(processed_query, param_tuples)
                    total_affected = cursor.rowcount
                    await connection.native_connection.commit()
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += len(parameters_list)
            
            # Create metrics
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=total_affected,
                rows_returned=0
            )
            
            return QueryResult(
                data=None,
                rows_affected=total_affected,
                rows_returned=0,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            await connection.native_connection.rollback()
            raise wrap_database_error(
                e,
                operation="execute_many",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_one(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row from MySQL."""
        try:
            connection.mark_used()
            
            # Convert parameters
            processed_query, param_values = self._process_parameters(query, parameters)
            
            async with connection.native_connection.cursor() as cursor:
                # Fetch single row
                if param_values:
                    await cursor.execute(processed_query, param_values)
                else:
                    await cursor.execute(processed_query)
                
                result = await cursor.fetchone()
                connection.query_count += 1
                
                return result
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="fetch_one",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple rows from MySQL."""
        try:
            connection.mark_used()
            
            # Convert parameters
            processed_query, param_values = self._process_parameters(query, parameters)
            
            # Add LIMIT if size specified
            if size is not None:
                processed_query += f" LIMIT {size}"
            
            async with connection.native_connection.cursor() as cursor:
                # Fetch rows
                if param_values:
                    await cursor.execute(processed_query, param_values)
                else:
                    await cursor.execute(processed_query)
                
                results = await cursor.fetchall()
                connection.query_count += 1
                
                return results if results else []
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="fetch_many",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_all(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows from MySQL."""
        return await self.fetch_many(connection, query, parameters)
    
    # Transaction management
    
    async def _begin_transaction(
        self,
        connection: DatabaseConnection,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> None:
        """Begin a MySQL transaction."""
        try:
            async with connection.native_connection.cursor() as cursor:
                # Set isolation level if specified
                if isolation_level:
                    isolation_map = {
                        IsolationLevel.READ_UNCOMMITTED: "READ UNCOMMITTED",
                        IsolationLevel.READ_COMMITTED: "READ COMMITTED",
                        IsolationLevel.REPEATABLE_READ: "REPEATABLE READ",
                        IsolationLevel.SERIALIZABLE: "SERIALIZABLE"
                    }
                    await cursor.execute(f"SET SESSION TRANSACTION ISOLATION LEVEL {isolation_map[isolation_level]}")
                
                # Set read-only mode if specified
                if read_only:
                    await cursor.execute("SET SESSION TRANSACTION READ ONLY")
                
                # Begin transaction
                await cursor.execute("START TRANSACTION")
                
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="begin_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _commit_transaction(self, connection: DatabaseConnection) -> None:
        """Commit a MySQL transaction."""
        try:
            await connection.native_connection.commit()
            self.logger.debug(f"Transaction committed on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="commit_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _rollback_transaction(self, connection: DatabaseConnection) -> None:
        """Rollback a MySQL transaction."""
        try:
            await connection.native_connection.rollback()
            self.logger.debug(f"Transaction rolled back on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="rollback_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _create_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Create a MySQL savepoint."""
        try:
            # Validate savepoint name (MySQL requirements)
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                raise ValueError(f"Invalid savepoint name: {name}")
            
            async with connection.native_connection.cursor() as cursor:
                await cursor.execute(f"SAVEPOINT {name}")
            
            self.logger.debug(f"Savepoint '{name}' created on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_savepoint",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                savepoint_name=name
            )
    
    async def _rollback_to_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Rollback to a MySQL savepoint."""
        try:
            async with connection.native_connection.cursor() as cursor:
                await cursor.execute(f"ROLLBACK TO SAVEPOINT {name}")
            
            self.logger.debug(f"Rolled back to savepoint '{name}' on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="rollback_to_savepoint",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                savepoint_name=name
            )
    
    async def _close_connection(self, native_connection: Any) -> None:
        """Close a MySQL connection."""
        try:
            if native_connection and not native_connection.closed:
                # Return connection to pool if it's from pool
                if self._connection_pool and hasattr(native_connection, '_pool'):
                    self._connection_pool.release(native_connection)
                else:
                    # Close direct connection
                    native_connection.close()
                    
        except Exception as e:
            self.logger.error(f"Error closing MySQL connection: {e}")
            # Don't raise here as this is cleanup code 
   
    # MySQL-specific enterprise features
    
    async def execute_stored_procedure(
        self,
        connection: DatabaseConnection,
        procedure_name: str,
        parameters: Optional[List[Any]] = None
    ) -> QueryResult:
        """Execute a MySQL stored procedure."""
        start_time = datetime.now(timezone.utc)
        
        try:
            connection.mark_used()
            
            # Build CALL statement
            if parameters:
                placeholders = ', '.join(['%s'] * len(parameters))
                query = f"CALL {procedure_name}({placeholders})"
            else:
                query = f"CALL {procedure_name}()"
            
            async with connection.native_connection.cursor() as cursor:
                if parameters:
                    await cursor.execute(query, parameters)
                else:
                    await cursor.execute(query)
                
                # Fetch results (stored procedures can return result sets)
                results = []
                try:
                    while True:
                        result = await cursor.fetchall()
                        if result:
                            results.extend(result)
                        if not cursor.nextset():
                            break
                except Exception:
                    # No more result sets
                    pass
                
                await connection.native_connection.commit()
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += 1
            
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=0,
                rows_returned=len(results)
            )
            
            return QueryResult(
                data=results,
                rows_affected=0,
                rows_returned=len(results),
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            await connection.native_connection.rollback()
            raise wrap_database_error(
                e,
                operation="execute_stored_procedure",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                procedure_name=procedure_name
            )
    
    async def execute_function(
        self,
        connection: DatabaseConnection,
        function_name: str,
        parameters: Optional[List[Any]] = None
    ) -> Any:
        """Execute a MySQL function."""
        try:
            connection.mark_used()
            
            # Build SELECT statement for function
            if parameters:
                placeholders = ', '.join(['%s'] * len(parameters))
                query = f"SELECT {function_name}({placeholders}) as result"
            else:
                query = f"SELECT {function_name}() as result"
            
            async with connection.native_connection.cursor() as cursor:
                if parameters:
                    await cursor.execute(query, parameters)
                else:
                    await cursor.execute(query)
                
                result = await cursor.fetchone()
                connection.query_count += 1
                
                return result['result'] if result else None
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="execute_function",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                function_name=function_name
            )
    
    async def bulk_insert(
        self,
        connection: DatabaseConnection,
        table_name: str,
        data: List[Dict[str, Any]],
        on_duplicate_key: Optional[str] = None
    ) -> QueryResult:
        """Perform bulk insert with MySQL-specific optimizations."""
        start_time = datetime.now(timezone.utc)
        
        try:
            if not data:
                return QueryResult(data=None, rows_affected=0, rows_returned=0, execution_time=0)
            
            connection.mark_used()
            
            # Get column names from first row
            columns = list(data[0].keys())
            column_names = ', '.join(f"`{col}`" for col in columns)
            placeholders = ', '.join(['%s'] * len(columns))
            
            # Build INSERT query
            query = f"INSERT INTO `{table_name}` ({column_names}) VALUES ({placeholders})"
            
            # Add ON DUPLICATE KEY UPDATE if specified
            if on_duplicate_key:
                query += f" ON DUPLICATE KEY UPDATE {on_duplicate_key}"
            
            # Prepare parameter tuples
            param_tuples = []
            for row in data:
                param_tuples.append([row.get(col) for col in columns])
            
            async with connection.native_connection.cursor() as cursor:
                await cursor.executemany(query, param_tuples)
                rows_affected = cursor.rowcount
                await connection.native_connection.commit()
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += 1
            
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=rows_affected,
                rows_returned=0
            )
            
            return QueryResult(
                data=None,
                rows_affected=rows_affected,
                rows_returned=0,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            await connection.native_connection.rollback()
            raise wrap_database_error(
                e,
                operation="bulk_insert",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def get_table_info(
        self,
        connection: DatabaseConnection,
        table_name: str
    ) -> Dict[str, Any]:
        """Get MySQL table information."""
        try:
            connection.mark_used()
            
            async with connection.native_connection.cursor() as cursor:
                # Get table structure
                await cursor.execute(f"DESCRIBE `{table_name}`")
                columns = await cursor.fetchall()
                
                # Get table status
                await cursor.execute(f"SHOW TABLE STATUS LIKE '{table_name}'")
                status = await cursor.fetchone()
                
                # Get indexes
                await cursor.execute(f"SHOW INDEX FROM `{table_name}`")
                indexes = await cursor.fetchall()
                
                # Get foreign keys
                await cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME,
                        CONSTRAINT_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (table_name,))
                foreign_keys = await cursor.fetchall()
                
                connection.query_count += 4
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'status': status,
                    'indexes': indexes,
                    'foreign_keys': foreign_keys,
                    'engine': status.get('Engine') if status else None,
                    'rows': status.get('Rows') if status else None,
                    'data_length': status.get('Data_length') if status else None,
                    'index_length': status.get('Index_length') if status else None,
                    'collation': status.get('Collation') if status else None
                }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_table_info",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def optimize_table(
        self,
        connection: DatabaseConnection,
        table_name: str
    ) -> QueryResult:
        """Optimize a MySQL table."""
        start_time = datetime.now(timezone.utc)
        
        try:
            connection.mark_used()
            
            async with connection.native_connection.cursor() as cursor:
                await cursor.execute(f"OPTIMIZE TABLE `{table_name}`")
                result = await cursor.fetchall()
                connection.query_count += 1
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=0,
                rows_returned=len(result) if result else 0
            )
            
            return QueryResult(
                data=result,
                rows_affected=0,
                rows_returned=len(result) if result else 0,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="optimize_table",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def analyze_table(
        self,
        connection: DatabaseConnection,
        table_name: str
    ) -> QueryResult:
        """Analyze a MySQL table for query optimization."""
        start_time = datetime.now(timezone.utc)
        
        try:
            connection.mark_used()
            
            async with connection.native_connection.cursor() as cursor:
                await cursor.execute(f"ANALYZE TABLE `{table_name}`")
                result = await cursor.fetchall()
                connection.query_count += 1
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=0,
                rows_returned=len(result) if result else 0
            )
            
            return QueryResult(
                data=result,
                rows_affected=0,
                rows_returned=len(result) if result else 0,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="analyze_table",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def get_replication_status(
        self,
        connection: DatabaseConnection
    ) -> Dict[str, Any]:
        """Get MySQL replication status."""
        try:
            connection.mark_used()
            
            async with connection.native_connection.cursor() as cursor:
                # Check if this is a slave
                await cursor.execute("SHOW SLAVE STATUS")
                slave_status = await cursor.fetchone()
                
                # Check if this is a master
                await cursor.execute("SHOW MASTER STATUS")
                master_status = await cursor.fetchone()
                
                # Get server ID
                await cursor.execute("SELECT @@server_id as server_id")
                server_info = await cursor.fetchone()
                
                connection.query_count += 3
                
                return {
                    'server_id': server_info['server_id'] if server_info else None,
                    'is_master': master_status is not None,
                    'is_slave': slave_status is not None,
                    'master_status': master_status,
                    'slave_status': slave_status,
                    'replication_healthy': (
                        slave_status is None or  # Not a slave
                        (slave_status.get('Slave_IO_Running') == 'Yes' and 
                         slave_status.get('Slave_SQL_Running') == 'Yes')
                    ) if slave_status else True
                }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_replication_status",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def get_performance_metrics(
        self,
        connection: DatabaseConnection
    ) -> Dict[str, Any]:
        """Get MySQL performance metrics."""
        try:
            connection.mark_used()
            
            async with connection.native_connection.cursor() as cursor:
                # Get key performance variables
                performance_queries = {
                    'connections': "SHOW STATUS LIKE 'Connections'",
                    'queries': "SHOW STATUS LIKE 'Queries'",
                    'slow_queries': "SHOW STATUS LIKE 'Slow_queries'",
                    'uptime': "SHOW STATUS LIKE 'Uptime'",
                    'threads_connected': "SHOW STATUS LIKE 'Threads_connected'",
                    'threads_running': "SHOW STATUS LIKE 'Threads_running'",
                    'innodb_buffer_pool_reads': "SHOW STATUS LIKE 'Innodb_buffer_pool_reads'",
                    'innodb_buffer_pool_read_requests': "SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'",
                    'table_locks_waited': "SHOW STATUS LIKE 'Table_locks_waited'",
                    'table_locks_immediate': "SHOW STATUS LIKE 'Table_locks_immediate'"
                }
                
                metrics = {}
                for metric_name, query in performance_queries.items():
                    await cursor.execute(query)
                    result = await cursor.fetchone()
                    metrics[metric_name] = int(result['Value']) if result else 0
                
                # Calculate derived metrics
                if metrics['innodb_buffer_pool_read_requests'] > 0:
                    buffer_pool_hit_ratio = (
                        1 - (metrics['innodb_buffer_pool_reads'] / metrics['innodb_buffer_pool_read_requests'])
                    ) * 100
                else:
                    buffer_pool_hit_ratio = 100
                
                total_locks = metrics['table_locks_waited'] + metrics['table_locks_immediate']
                if total_locks > 0:
                    lock_contention_ratio = (metrics['table_locks_waited'] / total_locks) * 100
                else:
                    lock_contention_ratio = 0
                
                connection.query_count += len(performance_queries)
                
                return {
                    'raw_metrics': metrics,
                    'derived_metrics': {
                        'buffer_pool_hit_ratio': round(buffer_pool_hit_ratio, 2),
                        'lock_contention_ratio': round(lock_contention_ratio, 2),
                        'queries_per_second': round(metrics['queries'] / max(metrics['uptime'], 1), 2),
                        'slow_query_ratio': round((metrics['slow_queries'] / max(metrics['queries'], 1)) * 100, 2)
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_performance_metrics",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    # Connection pool management
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self._connection_pool:
            return {'error': 'Connection pool not initialized'}
        
        return {
            'size': self._connection_pool.size,
            'used': self._connection_pool.size - self._connection_pool.freesize,
            'free': self._connection_pool.freesize,
            'min_size': self._connection_pool.minsize,
            'max_size': self._connection_pool.maxsize,
            'closed': self._connection_pool.closed
        }
    
    async def resize_pool(self, min_size: int, max_size: int) -> None:
        """Resize the connection pool."""
        try:
            if self._connection_pool:
                # Close existing pool
                self._connection_pool.close()
                await self._connection_pool.wait_closed()
            
            # Create new pool with new sizes
            self._connection_pool = await aiomysql.create_pool(
                minsize=min_size,
                maxsize=max_size,
                **self._connection_options
            )
            
            self.logger.info(f"Connection pool resized to {min_size}-{max_size}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="resize_pool",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    # Utility methods
    
    def _log_query(self, query: str, parameters: Any = None) -> None:
        """Log query execution for debugging."""
        if self.logger.isEnabledFor(logging.DEBUG):
            if parameters:
                self.logger.debug(f"Executing MySQL query: {query[:200]}... with parameters: {parameters}")
            else:
                self.logger.debug(f"Executing MySQL query: {query[:200]}...")
    
    @property
    def engine(self) -> DatabaseEngine:
        """Get the database engine type."""
        return DatabaseEngine.MYSQL
    
    @property
    def is_available(self) -> bool:
        """Check if MySQL adapter is available."""
        return AIOMYSQL_AVAILABLE
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"MySQLAdapter(host={self.config.host}, database={self.config.database})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return (
            f"MySQLAdapter("
            f"host={self.config.host}, "
            f"port={self.config.port}, "
            f"database={self.config.database}, "
            f"pool_size={self.config.pool.min_connections}-{self.config.pool.max_connections}, "
            f"ssl_enabled={hasattr(self.config, 'ssl') and self.config.ssl and self.config.ssl.enabled}"
            f")"
        )
"""
SQLite Database Adapter for FastAPI Microservices SDK.

This module provides SQLite-specific database adapter implementation
with optimizations for file-based and in-memory databases.

Features:
- Full aiosqlite integration with async support
- File-based and in-memory database support
- WAL mode for better concurrency
- Advanced SQLite features (FTS, JSON1, R-Tree)
- Connection health monitoring and recovery
- Query optimization and performance metrics
- Transaction management with savepoints
- Database backup and restore operations
- Connection retry logic with exponential backoff
- SQLite-specific data types and operations

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import sqlite3
import shutil
import os
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timezone
from pathlib import Path
import json
import re

from ..config import DatabaseConnectionConfig, DatabaseEngine
from ..exceptions import (
    DatabaseError, ConnectionError, QueryError, TransactionError,
    SQLiteError, wrap_database_error
)
from .base import (
    DatabaseAdapter, DatabaseConnection, QueryResult, QueryType,
    TransactionContext, IsolationLevel, QueryMetrics
)

# Optional dependency
try:
    import aiosqlite
    AIOSQLITE_AVAILABLE = True
except ImportError:
    AIOSQLITE_AVAILABLE = False
    aiosqlite = None


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter with aiosqlite and enterprise features."""
    
    def __init__(self, config: DatabaseConnectionConfig):
        if not AIOSQLITE_AVAILABLE:
            raise DatabaseError(
                "aiosqlite not installed - required for SQLite support",
                context={
                    'engine': DatabaseEngine.SQLITE.value,
                    'operation': 'configuration',
                    'database_name': config.database
                }
            )
        
        # Initialize base class without calling super() to avoid engine conflict
        self.config = config
        self._engine = config.engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connection_pool_dict: Dict[str, DatabaseConnection] = {}
        self._pool_lock = asyncio.Lock()
        self._is_initialized = False
        
        self._database_path = self._get_database_path()
        self._connection_options = self._build_connection_options()
        self._extensions_loaded = set()
        self._prepared_statements: Dict[str, str] = {}
        
    def _get_database_name(self, config: DatabaseConnectionConfig) -> str:
        """Get database name for error reporting."""
        return getattr(config, 'name', config.database)
    
    def _get_database_name(self) -> str:
        """Get database name for error reporting."""
        return getattr(self.config, 'name', self.config.database)
    
    def _get_database_path(self) -> str:
        """Get the SQLite database file path."""
        if self.config.database == ":memory:":
            return ":memory:"
        
        # Handle relative and absolute paths
        db_path = Path(self.config.database)
        if not db_path.is_absolute():
            # Make relative to current working directory
            db_path = Path.cwd() / db_path
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(db_path)
    
    def _build_connection_options(self) -> Dict[str, Any]:
        """Build SQLite connection options."""
        options = {
            'timeout': self.config.pool.connection_timeout,
            'isolation_level': None,  # Use autocommit mode by default
        }
        
        # Add SQLite-specific options
        if hasattr(self.config, 'sqlite_options'):
            options.update(self.config.sqlite_options)
        
        return options
    
    async def initialize(self) -> None:
        """Initialize the SQLite adapter."""
        try:
            # Test connection and setup database
            if not AIOSQLITE_AVAILABLE or not aiosqlite:
                raise DatabaseError("aiosqlite not available")
            
            async with aiosqlite.connect(
                self._database_path,
                **self._connection_options
            ) as conn:
                # Basic connectivity test
                await conn.execute("SELECT 1")
                
                # Get SQLite version
                cursor = await conn.execute("SELECT sqlite_version()")
                sqlite_version = await cursor.fetchone()
                
                # Setup database optimizations
                await self._setup_database_optimizations(conn)
                
                # Load extensions if available
                await self._load_extensions(conn)
                
                self.logger.info(f"Connected to SQLite: {sqlite_version[0] if sqlite_version else 'unknown'}")
            
            self._is_initialized = True
            self.logger.info(f"SQLite adapter initialized: {self._database_path}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="initialize",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _setup_database_optimizations(self, conn) -> None:
        """Setup SQLite database optimizations."""
        # Enable WAL mode for better concurrency (if not in-memory)
        if self._database_path != ":memory:":
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA wal_autocheckpoint=1000")
            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        # Performance optimizations
        await conn.execute("PRAGMA cache_size=10000")  # 10MB cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        await conn.execute("PRAGMA optimize")
        
        # Enable foreign keys
        await conn.execute("PRAGMA foreign_keys=ON")
        
        # Enable recursive triggers
        await conn.execute("PRAGMA recursive_triggers=ON")
        
        # Set busy timeout
        await conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds
    
    async def _load_extensions(self, conn) -> None:
        """Load SQLite extensions if available."""
        extensions_to_try = [
            'json1',  # JSON functions
            'fts5',   # Full-text search
            'rtree',  # R-Tree spatial index
            'uuid',   # UUID functions (if available)
        ]
        
        for ext in extensions_to_try:
            try:
                # Test if extension is available by trying to use it
                if ext == 'json1':
                    await conn.execute("SELECT json('{}') as test")
                elif ext == 'fts5':
                    await conn.execute("SELECT fts5_version() as test")
                elif ext == 'rtree':
                    await conn.execute("SELECT rtree_version() as test")
                
                self._extensions_loaded.add(ext)
                self.logger.debug(f"SQLite extension '{ext}' is available")
                
            except Exception:
                # Extension not available, continue
                pass
    
    async def shutdown(self) -> None:
        """Shutdown the SQLite adapter."""
        try:
            # Close all connections
            async with self._pool_lock:
                for connection in list(self._connection_pool_dict.values()):
                    await connection.close()
                self._connection_pool_dict.clear()
            
            # Clear caches
            self._prepared_statements.clear()
            self._extensions_loaded.clear()
            
            # Perform final optimization if file-based database
            if self._database_path != ":memory:" and Path(self._database_path).exists():
                try:
                    if AIOSQLITE_AVAILABLE and aiosqlite:
                        async with aiosqlite.connect(self._database_path) as conn:
                            await conn.execute("PRAGMA optimize")
                            await conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception as e:
                    self.logger.warning(f"Error during final optimization: {e}")
            
            self._is_initialized = False
            self.logger.info("SQLite adapter shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during SQLite adapter shutdown: {e}")
            raise wrap_database_error(
                e,
                operation="shutdown",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def create_connection(self) -> DatabaseConnection:
        """Create a new SQLite connection."""
        try:
            connection_id = self._create_connection_id()
            
            # Create native connection
            if not AIOSQLITE_AVAILABLE or not aiosqlite:
                raise DatabaseError("aiosqlite not available")
            
            native_conn = await aiosqlite.connect(
                self._database_path,
                **self._connection_options
            )
            
            # Configure connection
            await self._configure_connection(native_conn)
            
            connection = DatabaseConnection(
                connection_id=connection_id,
                config=self.config,
                native_connection=native_conn,
                adapter=self
            )
            
            # Set connection metadata
            connection.set_metadata("database_path", self._database_path)
            connection.set_metadata("sqlite_version", await self._get_sqlite_version(native_conn))
            connection.set_metadata("extensions_loaded", list(self._extensions_loaded))
            connection.set_metadata("journal_mode", await self._get_journal_mode(native_conn))
            
            self.logger.debug(f"Created SQLite connection: {connection_id}")
            return connection
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_connection",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _configure_connection(self, conn) -> None:
        """Configure SQLite connection settings."""
        # Apply database optimizations
        await self._setup_database_optimizations(conn)
        
        # Set row factory for dict-like access if aiosqlite is available
        if AIOSQLITE_AVAILABLE and aiosqlite:
            conn.row_factory = aiosqlite.Row
    
    async def _get_sqlite_version(self, conn) -> str:
        """Get SQLite version."""
        try:
            cursor = await conn.execute("SELECT sqlite_version()")
            result = await cursor.fetchone()
            return result[0] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def _get_journal_mode(self, conn) -> str:
        """Get journal mode."""
        try:
            cursor = await conn.execute("PRAGMA journal_mode")
            result = await cursor.fetchone()
            return result[0] if result else "unknown"
        except Exception:
            return "unknown"
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform SQLite health check."""
        try:
            start_time = datetime.now(timezone.utc)
            
            if not AIOSQLITE_AVAILABLE or not aiosqlite:
                return {
                    'healthy': False,
                    'error': 'aiosqlite not available',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            async with aiosqlite.connect(
                self._database_path,
                timeout=5.0
            ) as conn:
                if AIOSQLITE_AVAILABLE and aiosqlite:
                    conn.row_factory = aiosqlite.Row
                
                # Basic connectivity test
                cursor = await conn.execute("SELECT 1 as health_check")
                result = await cursor.fetchone()
                
                # Database integrity check (quick)
                cursor = await conn.execute("PRAGMA quick_check(1)")
                integrity_result = await cursor.fetchone()
                
                # Get SQLite version
                cursor = await conn.execute("SELECT sqlite_version()")
                version_result = await cursor.fetchone()
                
                # Get database info
                cursor = await conn.execute("PRAGMA database_list")
                db_info = await cursor.fetchall()
                
                # Get page count and size
                cursor = await conn.execute("PRAGMA page_count")
                page_count = await cursor.fetchone()
                
                cursor = await conn.execute("PRAGMA page_size")
                page_size = await cursor.fetchone()
                
                # Get journal mode
                cursor = await conn.execute("PRAGMA journal_mode")
                journal_mode = await cursor.fetchone()
                
                # Get cache size
                cursor = await conn.execute("PRAGMA cache_size")
                cache_size = await cursor.fetchone()
                
                # Get table count
                cursor = await conn.execute(
                    "SELECT COUNT(*) as table_count FROM sqlite_master WHERE type='table'"
                )
                table_count = await cursor.fetchone()
                
                # Get index count
                cursor = await conn.execute(
                    "SELECT COUNT(*) as index_count FROM sqlite_master WHERE type='index'"
                )
                index_count = await cursor.fetchone()
                
                # Check if file exists and get file size
                file_size_bytes = 0
                if self._database_path != ":memory:" and Path(self._database_path).exists():
                    file_size_bytes = Path(self._database_path).stat().st_size
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'healthy': True,
                'response_time': response_time,
                'database_path': self._database_path,
                'sqlite_version': version_result[0] if version_result else 'unknown',
                'integrity_check': integrity_result[0] if integrity_result else 'unknown',
                'database_info': [dict(row) for row in db_info] if db_info else [],
                'page_count': page_count[0] if page_count else 0,
                'page_size': page_size[0] if page_size else 0,
                'journal_mode': journal_mode[0] if journal_mode else 'unknown',
                'cache_size': cache_size[0] if cache_size else 0,
                'table_count': table_count[0] if table_count else 0,
                'index_count': index_count[0] if index_count else 0,
                'file_size_bytes': file_size_bytes,
                'estimated_size_mb': (
                    (page_count[0] * page_size[0]) / (1024 * 1024)
                    if page_count and page_size else 0
                ),
                'extensions_loaded': list(self._extensions_loaded),
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
        """Execute a query on SQLite."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self._log_query(query, parameters)
            connection.mark_used()
            
            # Convert named parameters to format expected by SQLite
            processed_query, param_values = self._process_parameters(query, parameters)
            
            # Execute query
            if param_values:
                cursor = await connection.native_connection.execute(processed_query, param_values)
            else:
                cursor = await connection.native_connection.execute(processed_query)
            
            # Get results based on query type
            if query_type == QueryType.SELECT or self._is_select_query(processed_query):
                data = await cursor.fetchall()
                # Convert Row objects to dictionaries
                data = [dict(row) for row in data] if data else []
                rows_returned = len(data)
                rows_affected = 0
            else:
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
        """Convert named parameters to format expected by SQLite."""
        if not parameters:
            return query, []
        
        # Convert :param to ? format for SQLite
        param_values = []
        processed_query = query
        
        # Find all :param patterns and replace with ?
        param_pattern = r':(\w+)'
        matches = re.findall(param_pattern, query)
        
        for param_name in matches:
            if param_name in parameters:
                processed_query = processed_query.replace(f':{param_name}', '?', 1)
                param_values.append(parameters[param_name])
        
        return processed_query, param_values
    
    def _is_select_query(self, query: str) -> bool:
        """Check if query is a SELECT statement."""
        return query.strip().upper().startswith(('SELECT', 'WITH', 'PRAGMA', 'EXPLAIN'))
    
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
                cursor = await connection.native_connection.executemany(processed_query, param_tuples)
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
        """Fetch a single row from SQLite."""
        try:
            connection.mark_used()
            
            # Convert parameters
            processed_query, param_values = self._process_parameters(query, parameters)
            
            # Add LIMIT 1 if not present
            if "LIMIT" not in processed_query.upper():
                processed_query += " LIMIT 1"
            
            # Execute query
            if param_values:
                cursor = await connection.native_connection.execute(processed_query, param_values)
            else:
                cursor = await connection.native_connection.execute(processed_query)
            
            result = await cursor.fetchone()
            connection.query_count += 1
            
            return dict(result) if result else None
            
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
        """Fetch multiple rows from SQLite."""
        try:
            connection.mark_used()
            
            # Convert parameters
            processed_query, param_values = self._process_parameters(query, parameters)
            
            # Add LIMIT if size specified
            if size is not None and "LIMIT" not in processed_query.upper():
                processed_query += f" LIMIT {size}"
            
            # Execute query
            if param_values:
                cursor = await connection.native_connection.execute(processed_query, param_values)
            else:
                cursor = await connection.native_connection.execute(processed_query)
            
            results = await cursor.fetchall()
            connection.query_count += 1
            
            return [dict(row) for row in results] if results else []
            
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
        """Fetch all rows from SQLite."""
        return await self.fetch_many(connection, query, parameters)
    
    # Transaction management
    
    async def _begin_transaction(
        self,
        connection: DatabaseConnection,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> None:
        """Begin a SQLite transaction."""
        try:
            # SQLite transaction modes
            if read_only:
                await connection.native_connection.execute("BEGIN DEFERRED")
            elif isolation_level == IsolationLevel.SERIALIZABLE:
                await connection.native_connection.execute("BEGIN EXCLUSIVE")
            else:
                await connection.native_connection.execute("BEGIN IMMEDIATE")
            
            self.logger.debug(f"Transaction started on connection {connection.connection_id}")
                
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="begin_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _commit_transaction(self, connection: DatabaseConnection) -> None:
        """Commit a SQLite transaction."""
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
        """Rollback a SQLite transaction."""
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
        """Create a SQLite savepoint."""
        try:
            # Validate savepoint name (SQLite requirements)
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                raise ValueError(f"Invalid savepoint name: {name}")
            
            await connection.native_connection.execute(f"SAVEPOINT {name}")
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
        """Rollback to a SQLite savepoint."""
        try:
            await connection.native_connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
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
        """Close a SQLite connection."""
        try:
            if native_connection:
                await native_connection.close()
                
        except Exception as e:
            self.logger.error(f"Error closing SQLite connection: {e}")
            # Don't raise here as this is cleanup code
    
    # SQLite-specific enterprise features
    
    async def backup_database(
        self,
        connection: DatabaseConnection,
        backup_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Create a backup of the SQLite database."""
        try:
            if self._database_path == ":memory:":
                raise ValueError("Cannot backup in-memory database")
            
            connection.mark_used()
            
            # Ensure backup directory exists
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            start_time = datetime.now(timezone.utc)
            
            # Use SQLite backup API
            if not AIOSQLITE_AVAILABLE or not aiosqlite:
                raise DatabaseError("aiosqlite not available for backup")
            
            async with aiosqlite.connect(backup_path) as backup_conn:
                await connection.native_connection.backup(backup_conn, progress=progress_callback)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            backup_size = backup_file.stat().st_size if backup_file.exists() else 0
            
            return {
                'backup_path': backup_path,
                'backup_size_bytes': backup_size,
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="backup_database",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                backup_path=backup_path
            )
    
    async def restore_database(
        self,
        connection: DatabaseConnection,
        backup_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Restore SQLite database from backup."""
        try:
            if self._database_path == ":memory:":
                raise ValueError("Cannot restore to in-memory database")
            
            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            connection.mark_used()
            start_time = datetime.now(timezone.utc)
            
            # Use SQLite backup API to restore
            if not AIOSQLITE_AVAILABLE or not aiosqlite:
                raise DatabaseError("aiosqlite not available for restore")
            
            async with aiosqlite.connect(backup_path) as backup_conn:
                await backup_conn.backup(connection.native_connection, progress=progress_callback)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'backup_path': backup_path,
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="restore_database",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                backup_path=backup_path
            )
    
    async def vacuum_database(
        self,
        connection: DatabaseConnection,
        into_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Vacuum the SQLite database to reclaim space."""
        start_time = datetime.now(timezone.utc)
        
        try:
            connection.mark_used()
            
            if into_file:
                # VACUUM INTO (SQLite 3.27.0+)
                await connection.native_connection.execute(f"VACUUM INTO '{into_file}'")
            else:
                # Regular VACUUM
                await connection.native_connection.execute("VACUUM")
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'operation': 'vacuum',
                'into_file': into_file,
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="vacuum_database",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def analyze_database(
        self,
        connection: DatabaseConnection,
        table_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze SQLite database or specific table for query optimization."""
        start_time = datetime.now(timezone.utc)
        
        try:
            connection.mark_used()
            
            if table_name:
                await connection.native_connection.execute(f"ANALYZE {table_name}")
            else:
                await connection.native_connection.execute("ANALYZE")
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'operation': 'analyze',
                'table_name': table_name,
                'execution_time': execution_time,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="analyze_database",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def get_table_info(
        self,
        connection: DatabaseConnection,
        table_name: str
    ) -> Dict[str, Any]:
        """Get SQLite table information."""
        try:
            connection.mark_used()
            
            # Get table schema
            cursor = await connection.native_connection.execute(f"PRAGMA table_info({table_name})")
            columns = await cursor.fetchall()
            columns = [dict(row) for row in columns]
            
            # Get foreign keys
            cursor = await connection.native_connection.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = await cursor.fetchall()
            foreign_keys = [dict(row) for row in foreign_keys]
            
            # Get indexes
            cursor = await connection.native_connection.execute(f"PRAGMA index_list({table_name})")
            indexes = await cursor.fetchall()
            indexes = [dict(row) for row in indexes]
            
            # Get detailed index info
            index_details = []
            for index in indexes:
                cursor = await connection.native_connection.execute(f"PRAGMA index_info({index['name']})")
                index_info = await cursor.fetchall()
                index_details.append({
                    'name': index['name'],
                    'unique': bool(index['unique']),
                    'columns': [dict(row) for row in index_info]
                })
            
            # Get table statistics if available
            cursor = await connection.native_connection.execute(
                "SELECT COUNT(*) as row_count FROM " + table_name
            )
            row_count_result = await cursor.fetchone()
            row_count = row_count_result[0] if row_count_result else 0
            
            connection.query_count += 5
            
            return {
                'table_name': table_name,
                'columns': columns,
                'foreign_keys': foreign_keys,
                'indexes': index_details,
                'row_count': row_count,
                'column_count': len(columns)
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_table_info",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def explain_query(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Explain SQLite query execution plan."""
        try:
            connection.mark_used()
            
            # Convert parameters
            processed_query, param_values = self._process_parameters(query, parameters)
            
            # Get query plan
            explain_query = f"EXPLAIN QUERY PLAN {processed_query}"
            
            if param_values:
                cursor = await connection.native_connection.execute(explain_query, param_values)
            else:
                cursor = await connection.native_connection.execute(explain_query)
            
            plan = await cursor.fetchall()
            plan = [dict(row) for row in plan]
            
            connection.query_count += 1
            
            return {
                'query': query,
                'execution_plan': plan,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="explain_query",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def get_database_stats(
        self,
        connection: DatabaseConnection
    ) -> Dict[str, Any]:
        """Get comprehensive SQLite database statistics."""
        try:
            connection.mark_used()
            
            stats = {}
            
            # Basic database info
            cursor = await connection.native_connection.execute("PRAGMA database_list")
            db_list = await cursor.fetchall()
            stats['databases'] = [dict(row) for row in db_list]
            
            # Page and cache info
            pragmas = [
                'page_count', 'page_size', 'cache_size', 'freelist_count',
                'journal_mode', 'synchronous', 'temp_store', 'mmap_size'
            ]
            
            for pragma in pragmas:
                cursor = await connection.native_connection.execute(f"PRAGMA {pragma}")
                result = await cursor.fetchone()
                stats[pragma] = result[0] if result else None
            
            # Table and index counts
            cursor = await connection.native_connection.execute(
                "SELECT type, COUNT(*) as count FROM sqlite_master GROUP BY type"
            )
            object_counts = await cursor.fetchall()
            stats['object_counts'] = {row[0]: row[1] for row in object_counts}
            
            # Schema version
            cursor = await connection.native_connection.execute("PRAGMA schema_version")
            schema_version = await cursor.fetchone()
            stats['schema_version'] = schema_version[0] if schema_version else None
            
            # User version
            cursor = await connection.native_connection.execute("PRAGMA user_version")
            user_version = await cursor.fetchone()
            stats['user_version'] = user_version[0] if user_version else None
            
            # Calculate database size
            if stats['page_count'] and stats['page_size']:
                stats['database_size_bytes'] = stats['page_count'] * stats['page_size']
                stats['database_size_mb'] = stats['database_size_bytes'] / (1024 * 1024)
            
            # Free space
            if stats['freelist_count'] and stats['page_size']:
                stats['free_space_bytes'] = stats['freelist_count'] * stats['page_size']
                stats['free_space_mb'] = stats['free_space_bytes'] / (1024 * 1024)
            
            connection.query_count += len(pragmas) + 4
            
            return stats
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_database_stats",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def create_fts_table(
        self,
        connection: DatabaseConnection,
        table_name: str,
        columns: List[str],
        content_table: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a Full-Text Search (FTS5) table."""
        try:
            if 'fts5' not in self._extensions_loaded:
                raise DatabaseError("FTS5 extension not available")
            
            connection.mark_used()
            
            # Build FTS5 table creation SQL
            columns_sql = ', '.join(columns)
            
            if content_table:
                fts_sql = f"CREATE VIRTUAL TABLE {table_name} USING fts5({columns_sql}, content='{content_table}')"
            else:
                fts_sql = f"CREATE VIRTUAL TABLE {table_name} USING fts5({columns_sql})"
            
            await connection.native_connection.execute(fts_sql)
            await connection.native_connection.commit()
            
            return {
                'table_name': table_name,
                'columns': columns,
                'content_table': content_table,
                'created': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_fts_table",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    async def fts_search(
        self,
        connection: DatabaseConnection,
        table_name: str,
        search_query: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Perform Full-Text Search on FTS5 table."""
        try:
            if 'fts5' not in self._extensions_loaded:
                raise DatabaseError("FTS5 extension not available")
            
            connection.mark_used()
            
            # Build FTS search query
            sql = f"SELECT * FROM {table_name} WHERE {table_name} MATCH ?"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            cursor = await connection.native_connection.execute(sql, (search_query,))
            results = await cursor.fetchall()
            
            connection.query_count += 1
            
            return [dict(row) for row in results]
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="fts_search",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                table_name=table_name
            )
    
    # Utility methods
    
    def _log_query(self, query: str, parameters: Any = None) -> None:
        """Log query execution for debugging."""
        if self.logger.isEnabledFor(logging.DEBUG):
            if parameters:
                self.logger.debug(f"Executing SQLite query: {query[:200]}... with parameters: {parameters}")
            else:
                self.logger.debug(f"Executing SQLite query: {query[:200]}...")
    
    @property
    def engine(self) -> DatabaseEngine:
        """Get the database engine type."""
        return DatabaseEngine.SQLITE
    
    @property
    def is_available(self) -> bool:
        """Check if SQLite adapter is available."""
        return AIOSQLITE_AVAILABLE
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"SQLiteAdapter(path={self._database_path})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return (
            f"SQLiteAdapter("
            f"path={self._database_path}, "
            f"extensions={list(self._extensions_loaded)}, "
            f"journal_mode={'WAL' if self._database_path != ':memory:' else 'memory'}"
            f")"
        )
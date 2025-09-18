"""
Database Manager for FastAPI Microservices SDK.

This module provides the central DatabaseManager class that orchestrates
all database operations, connection management, health monitoring, and
integration with other SDK components.

Features:
- Unified interface for all database engines (PostgreSQL, MySQL, MongoDB, SQLite)
- Enterprise-grade connection pooling and management
- Health monitoring and automatic recovery
- Transaction management with context managers
- Query execution with performance metrics
- Security integration and audit logging
- Load balancing and failover support
- Real-time monitoring and alerting
- Integration with communication and security systems

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, AsyncGenerator, Type
from datetime import datetime, timezone
import weakref
from contextlib import asynccontextmanager
import uuid
import json

from .config import DatabaseConfig, DatabaseConnectionConfig, DatabaseEngine
from .exceptions import (
    DatabaseError, ConnectionError, ConfigurationError, PoolError,
    wrap_database_error, create_error_from_driver_exception
)
from .adapters.base import DatabaseAdapter, QueryResult, QueryType, IsolationLevel
from .adapters.registry import AdapterRegistry

# Integration with communication logging
try:
    from ..communication.logging import CommunicationLogger
    COMMUNICATION_LOGGING_AVAILABLE = True
except ImportError:
    COMMUNICATION_LOGGING_AVAILABLE = False
    CommunicationLogger = None

# Integration with security system
try:
    from ..security.advanced.config_manager import SecurityConfigManager
    SECURITY_INTEGRATION_AVAILABLE = True
except ImportError:
    SECURITY_INTEGRATION_AVAILABLE = False
    SecurityConfigManager = None


class DatabaseConnection:
    """Represents a database connection with metadata."""
    
    def __init__(
        self,
        connection_id: str,
        config: DatabaseConnectionConfig,
        native_connection: Any,
        created_at: Optional[datetime] = None
    ):
        self.connection_id = connection_id
        self.config = config
        self.native_connection = native_connection
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_used = self.created_at
        self.is_healthy = True
        self.transaction_count = 0
        self.query_count = 0
        
    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used = datetime.now(timezone.utc)
        self.query_count += 1
    
    def begin_transaction(self):
        """Mark beginning of transaction."""
        self.transaction_count += 1
    
    def end_transaction(self):
        """Mark end of transaction."""
        if self.transaction_count > 0:
            self.transaction_count -= 1
    
    @property
    def is_in_transaction(self) -> bool:
        """Check if connection is currently in a transaction."""
        return self.transaction_count > 0
    
    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """Get connection idle time in seconds."""
        return (datetime.now(timezone.utc) - self.last_used).total_seconds()


class DatabaseStatus:
    """Database status information."""
    
    def __init__(self):
        self.is_connected = False
        self.connection_count = 0
        self.active_transactions = 0
        self.total_queries = 0
        self.last_health_check = None
        self.health_check_status = "unknown"
        self.error_count = 0
        self.last_error = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary."""
        return {
            'is_connected': self.is_connected,
            'connection_count': self.connection_count,
            'active_transactions': self.active_transactions,
            'total_queries': self.total_queries,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'health_check_status': self.health_check_status,
            'error_count': self.error_count,
            'last_error': str(self.last_error) if self.last_error else None
        }


class DatabaseManager:
    """
    Central database management orchestrator.
    
    Manages database connections, health monitoring, and integration
    with other SDK components using enterprise-grade adapters.
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._adapters: Dict[str, DatabaseAdapter] = {}
        self._connections: Dict[str, Dict[str, DatabaseConnection]] = {}
        self._status: Dict[str, DatabaseStatus] = {}
        self._initialized = False
        self._shutdown = False
        
        # Adapter registry for managing database adapters
        self._adapter_registry = AdapterRegistry()
        
        # Logging setup
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("database.manager")
        else:
            self.logger = logging.getLogger(__name__)
        
        # Security integration
        self.security_manager = None
        if SECURITY_INTEGRATION_AVAILABLE:
            try:
                self.security_manager = SecurityConfigManager()
            except Exception as e:
                self.logger.warning(f"Could not initialize security manager: {e}")
        
        # Health monitoring
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._health_check_interval = getattr(config, 'health_check_interval', 30.0)
        
        # Performance metrics
        self._query_metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._connection_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Load balancing and failover
        self._load_balancer_state: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks
        self._startup_callbacks: List[callable] = []
        self._shutdown_callbacks: List[callable] = []
        self._health_check_callbacks: List[callable] = []
        self._query_callbacks: List[callable] = []
        
        self.logger.info(f"DatabaseManager initialized with {len(config.databases)} databases")
    
    async def initialize(self) -> None:
        """Initialize all database adapters and start health monitoring."""
        if self._initialized:
            self.logger.warning("DatabaseManager already initialized")
            return
        
        try:
            self.logger.info("Initializing DatabaseManager...")
            
            # Initialize adapters for all databases
            for db_name, db_config in self.config.databases.items():
                await self._initialize_database_adapter(db_name, db_config)
            
            # Initialize metrics tracking
            for db_name in self.config.databases:
                self._query_metrics[db_name] = []
                self._connection_metrics[db_name] = {
                    'total_connections': 0,
                    'active_connections': 0,
                    'failed_connections': 0,
                    'total_queries': 0,
                    'failed_queries': 0,
                    'avg_response_time': 0.0
                }
                self._load_balancer_state[db_name] = {
                    'current_weight': 1.0,
                    'failure_count': 0,
                    'last_failure': None,
                    'circuit_breaker_open': False
                }
            
            # Execute startup callbacks
            for callback in self._startup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self)
                    else:
                        callback(self)
                except Exception as e:
                    self.logger.error(f"Startup callback failed: {e}")
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            self._initialized = True
            self.logger.info("DatabaseManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DatabaseManager: {e}")
            raise DatabaseError(f"DatabaseManager initialization failed: {e}", original_error=e)
    
    async def _initialize_database_adapter(self, db_name: str, db_config: DatabaseConnectionConfig) -> None:
        """Initialize a database adapter for the given configuration."""
        try:
            # Get adapter class from registry
            adapter_class = self._adapter_registry.get_adapter(db_config.engine)
            
            # Create and initialize adapter
            adapter = adapter_class(db_config)
            await adapter.initialize()
            
            # Store adapter and initialize status
            self._adapters[db_name] = adapter
            self._status[db_name] = DatabaseStatus()
            self._connections[db_name] = {}
            
            self.logger.info(f"Initialized {db_config.engine.value} adapter for database '{db_name}'")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize adapter for database '{db_name}': {e}")
            raise DatabaseError(f"Adapter initialization failed for {db_name}: {e}", original_error=e)
    
    async def shutdown(self) -> None:
        """Shutdown all database adapters and cleanup resources."""
        if self._shutdown:
            return
        
        try:
            self.logger.info("Shutting down DatabaseManager...")
            self._shutdown = True
            
            # Stop health monitoring
            await self._stop_health_monitoring()
            
            # Execute shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self)
                    else:
                        callback(self)
                except Exception as e:
                    self.logger.error(f"Shutdown callback failed: {e}")
            
            # Close all connections and shutdown adapters
            for db_name, connections in self._connections.items():
                for conn_id, connection in list(connections.items()):
                    try:
                        await connection.close()
                    except Exception as e:
                        self.logger.error(f"Error closing connection {conn_id}: {e}")
                connections.clear()
            
            # Shutdown all adapters
            for db_name, adapter in self._adapters.items():
                try:
                    await adapter.shutdown()
                    self.logger.info(f"Shutdown adapter for database '{db_name}'")
                except Exception as e:
                    self.logger.error(f"Error shutting down adapter for {db_name}: {e}")
            
            self._adapters.clear()
            self._initialized = False
            self.logger.info("DatabaseManager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during DatabaseManager shutdown: {e}")
            raise DatabaseError(f"DatabaseManager shutdown failed: {e}", original_error=e)
    
    async def get_connection(
        self,
        database_name: Optional[str] = None,
        read_only: bool = False
    ) -> DatabaseConnection:
        """
        Get a database connection using the appropriate adapter.
        
        Args:
            database_name: Name of database (uses default if None)
            read_only: Whether connection is for read-only operations
            
        Returns:
            DatabaseConnection instance
        """
        if not self._initialized:
            raise DatabaseError("DatabaseManager not initialized")
        
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            # Check circuit breaker
            if self._load_balancer_state[db_name]['circuit_breaker_open']:
                if self._should_retry_circuit_breaker(db_name):
                    self._load_balancer_state[db_name]['circuit_breaker_open'] = False
                    self.logger.info(f"Circuit breaker closed for database '{db_name}'")
                else:
                    raise DatabaseError(f"Circuit breaker open for database '{db_name}'")
            
            # Get connection from adapter
            adapter = self._adapters[db_name]
            connection = await adapter.create_connection()
            
            # Update metrics
            self._connection_metrics[db_name]['total_connections'] += 1
            self._connection_metrics[db_name]['active_connections'] += 1
            
            # Store connection
            self._connections[db_name][connection.connection_id] = connection
            
            # Update status
            self._status[db_name].connection_count += 1
            self._status[db_name].is_connected = True
            
            self.logger.debug(f"Created connection for database '{db_name}': {connection.connection_id}")
            return connection
            
        except Exception as e:
            # Update failure metrics
            self._connection_metrics[db_name]['failed_connections'] += 1
            self._status[db_name].error_count += 1
            self._status[db_name].last_error = e
            
            # Update circuit breaker
            self._update_circuit_breaker(db_name, False)
            
            error_msg = f"Failed to get connection for database '{db_name}': {e}"
            self.logger.error(error_msg)
            raise wrap_database_error(e, "get_connection", db_name)
    
    def _should_retry_circuit_breaker(self, db_name: str) -> bool:
        """Check if circuit breaker should be retried."""
        state = self._load_balancer_state[db_name]
        if state['last_failure']:
            # Retry after 60 seconds
            time_since_failure = (datetime.now(timezone.utc) - state['last_failure']).total_seconds()
            return time_since_failure > 60
        return True
    
    def _update_circuit_breaker(self, db_name: str, success: bool) -> None:
        """Update circuit breaker state based on operation result."""
        state = self._load_balancer_state[db_name]
        
        if success:
            state['failure_count'] = 0
            state['circuit_breaker_open'] = False
        else:
            state['failure_count'] += 1
            state['last_failure'] = datetime.now(timezone.utc)
            
            # Open circuit breaker after 5 consecutive failures
            if state['failure_count'] >= 5:
                state['circuit_breaker_open'] = True
                self.logger.warning(f"Circuit breaker opened for database '{db_name}' after {state['failure_count']} failures")
    

    
    async def health_check(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """Perform health check on database(s) using adapters."""
        if database_name:
            databases = [database_name]
        else:
            databases = list(self._adapters.keys())
        
        results = {}
        
        for db_name in databases:
            try:
                status = await self._health_check_database(db_name)
                results[db_name] = status
                
                # Update circuit breaker on success
                self._update_circuit_breaker(db_name, True)
                
            except Exception as e:
                results[db_name] = {
                    'healthy': False,
                    'error': str(e),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Update circuit breaker on failure
                self._update_circuit_breaker(db_name, False)
        
        return results
    
    async def _health_check_database(self, database_name: str) -> Dict[str, Any]:
        """Perform health check on specific database using its adapter."""
        if database_name not in self._adapters:
            raise ConfigurationError(f"Database '{database_name}' not configured")
        
        try:
            # Use adapter's health check method
            adapter = self._adapters[database_name]
            health_result = await adapter.health_check()
            
            # Update status
            self._status[database_name].last_health_check = datetime.now(timezone.utc)
            self._status[database_name].health_check_status = "healthy" if health_result.get('healthy') else "unhealthy"
            
            # Add manager-specific information
            health_result.update({
                'database_name': database_name,
                'engine': self.config.databases[database_name].engine.value,
                'connection_metrics': self._connection_metrics[database_name],
                'circuit_breaker_status': self._load_balancer_state[database_name]
            })
            
            return health_result
            
        except Exception as e:
            self._status[database_name].last_health_check = datetime.now(timezone.utc)
            self._status[database_name].health_check_status = "unhealthy"
            self._status[database_name].last_error = e
            
            raise DatabaseError(f"Health check failed for {database_name}: {e}", original_error=e)
    
    async def _start_health_monitoring(self) -> None:
        """Start background health monitoring tasks."""
        for db_name in self.config.databases:
            task = asyncio.create_task(self._health_monitor_loop(db_name))
            self._health_check_tasks[db_name] = task
    
    async def _stop_health_monitoring(self) -> None:
        """Stop background health monitoring tasks."""
        for task in self._health_check_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._health_check_tasks.clear()
    
    async def _health_monitor_loop(self, database_name: str) -> None:
        """Background health monitoring loop for a database."""
        while not self._shutdown:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self._shutdown:
                    break
                
                await self._health_check_database(database_name)
                
                # Execute health check callbacks
                for callback in self._health_check_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(database_name, True)
                        else:
                            callback(database_name, True)
                    except Exception as e:
                        self.logger.error(f"Health check callback failed: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check failed for {database_name}: {e}")
                
                # Execute health check callbacks for failure
                for callback in self._health_check_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(database_name, False)
                        else:
                            callback(database_name, False)
                    except Exception as e:
                        self.logger.error(f"Health check callback failed: {e}")
    
    def get_status(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status information for database(s)."""
        if database_name:
            if database_name not in self._status:
                raise ConfigurationError(f"Database '{database_name}' not configured")
            return {database_name: self._status[database_name].to_dict()}
        else:
            return {name: status.to_dict() for name, status in self._status.items()}
    
    def add_startup_callback(self, callback: callable) -> None:
        """Add callback to be executed during startup."""
        self._startup_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback: callable) -> None:
        """Add callback to be executed during shutdown."""
        self._shutdown_callbacks.append(callback)
    
    def add_health_check_callback(self, callback: callable) -> None:
        """Add callback to be executed after health checks."""
        self._health_check_callbacks.append(callback)
    
    @asynccontextmanager
    async def connection(
        self,
        database_name: Optional[str] = None,
        read_only: bool = False
    ) -> AsyncGenerator[DatabaseConnection, None]:
        """Context manager for database connections."""
        db_name = database_name or self.config.default_database
        conn = await self.get_connection(db_name, read_only)
        try:
            yield conn
        finally:
            await self._close_connection_safe(conn, db_name)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# Global database manager instance
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> Optional[DatabaseManager]:
    """Get the global database manager instance."""
    return _database_manager


def set_database_manager(manager: DatabaseManager) -> None:
    """Set the global database manager instance."""
    global _database_manager
    _database_manager = manager


async def initialize_database_manager(config: DatabaseConfig) -> DatabaseManager:
    """Initialize and return a database manager."""
    manager = DatabaseManager(config)
    await manager.initialize()
    set_database_manager(manager)
    return manager 
   
    # Query execution methods
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database_name: Optional[str] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """
        Execute a query on the specified database.
        
        Args:
            query: SQL query or operation to execute
            parameters: Query parameters
            database_name: Target database (uses default if None)
            query_type: Type of query for optimization
            
        Returns:
            QueryResult with execution details
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get connection
            connection = await self.get_connection(db_name)
            
            try:
                # Execute query using adapter
                adapter = self._adapters[db_name]
                result = await adapter.execute_query(connection, query, parameters, query_type)
                
                # Update metrics
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._update_query_metrics(db_name, execution_time, True)
                
                # Execute query callbacks
                for callback in self._query_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(db_name, query, result, execution_time)
                        else:
                            callback(db_name, query, result, execution_time)
                    except Exception as e:
                        self.logger.error(f"Query callback failed: {e}")
                
                return result
                
            finally:
                # Always close connection
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            # Update failure metrics
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_query_metrics(db_name, execution_time, False)
            self._update_circuit_breaker(db_name, False)
            
            self.logger.error(f"Query execution failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "execute_query", db_name, query=query[:100])
    
    async def execute_many(
        self,
        query: str,
        parameters_list: List[Dict[str, Any]],
        database_name: Optional[str] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query to execute
            parameters_list: List of parameter dictionaries
            database_name: Target database (uses default if None)
            query_type: Type of query for optimization
            
        Returns:
            QueryResult with batch execution details
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get connection
            connection = await self.get_connection(db_name)
            
            try:
                # Execute batch using adapter
                adapter = self._adapters[db_name]
                result = await adapter.execute_many(connection, query, parameters_list, query_type)
                
                # Update metrics
                execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                self._update_query_metrics(db_name, execution_time, True)
                
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._update_query_metrics(db_name, execution_time, False)
            self._update_circuit_breaker(db_name, False)
            
            self.logger.error(f"Batch query execution failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "execute_many", db_name, query=query[:100])
    
    async def fetch_one(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row from the database.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            database_name: Target database (uses default if None)
            
        Returns:
            Single row as dictionary or None
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            
            try:
                adapter = self._adapters[db_name]
                result = await adapter.fetch_one(connection, query, parameters)
                
                self._update_circuit_breaker(db_name, True)
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            self._update_circuit_breaker(db_name, False)
            self.logger.error(f"Fetch one failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "fetch_one", db_name, query=query[:100])
    
    async def fetch_many(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        database_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch multiple rows from the database.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            size: Maximum number of rows to fetch
            database_name: Target database (uses default if None)
            
        Returns:
            List of rows as dictionaries
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            
            try:
                adapter = self._adapters[db_name]
                result = await adapter.fetch_many(connection, query, parameters, size)
                
                self._update_circuit_breaker(db_name, True)
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            self._update_circuit_breaker(db_name, False)
            self.logger.error(f"Fetch many failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "fetch_many", db_name, query=query[:100])
    
    async def fetch_all(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all rows from the database.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            database_name: Target database (uses default if None)
            
        Returns:
            List of all rows as dictionaries
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            
            try:
                adapter = self._adapters[db_name]
                result = await adapter.fetch_all(connection, query, parameters)
                
                self._update_circuit_breaker(db_name, True)
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            self._update_circuit_breaker(db_name, False)
            self.logger.error(f"Fetch all failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "fetch_all", db_name, query=query[:100])
    
    # Transaction management
    
    @asynccontextmanager
    async def transaction(
        self,
        database_name: Optional[str] = None,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> AsyncGenerator[DatabaseConnection, None]:
        """
        Context manager for database transactions.
        
        Args:
            database_name: Target database (uses default if None)
            isolation_level: Transaction isolation level
            read_only: Whether transaction is read-only
            
        Yields:
            DatabaseConnection within transaction context
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        connection = await self.get_connection(db_name)
        adapter = self._adapters[db_name]
        
        try:
            # Begin transaction
            await adapter._begin_transaction(connection, isolation_level, read_only)
            connection.begin_transaction()
            
            self.logger.debug(f"Transaction started on database '{db_name}'")
            
            try:
                yield connection
                
                # Commit transaction
                await adapter._commit_transaction(connection)
                connection.end_transaction()
                
                self.logger.debug(f"Transaction committed on database '{db_name}'")
                
            except Exception as e:
                # Rollback transaction
                try:
                    await adapter._rollback_transaction(connection)
                    connection.end_transaction()
                    self.logger.debug(f"Transaction rolled back on database '{db_name}'")
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed on database '{db_name}': {rollback_error}")
                
                raise e
                
        finally:
            await self._close_connection_safe(connection, db_name)
    
    # Utility methods
    
    def _update_query_metrics(self, db_name: str, execution_time: float, success: bool) -> None:
        """Update query execution metrics."""
        metrics = self._connection_metrics[db_name]
        
        metrics['total_queries'] += 1
        if not success:
            metrics['failed_queries'] += 1
        
        # Update average response time (simple moving average)
        current_avg = metrics['avg_response_time']
        total_queries = metrics['total_queries']
        metrics['avg_response_time'] = ((current_avg * (total_queries - 1)) + execution_time) / total_queries
        
        # Store recent query metrics (keep last 100)
        query_metric = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'execution_time': execution_time,
            'success': success
        }
        
        if len(self._query_metrics[db_name]) >= 100:
            self._query_metrics[db_name].pop(0)
        self._query_metrics[db_name].append(query_metric)
    
    async def _close_connection_safe(self, connection: DatabaseConnection, db_name: str) -> None:
        """Safely close a connection and update metrics."""
        try:
            await connection.close()
            
            # Update metrics
            if db_name in self._connection_metrics:
                self._connection_metrics[db_name]['active_connections'] -= 1
            
            # Remove from tracking
            if db_name in self._connections and connection.connection_id in self._connections[db_name]:
                del self._connections[db_name][connection.connection_id]
                
        except Exception as e:
            self.logger.error(f"Error closing connection {connection.connection_id}: {e}")
    
    def get_adapter(self, database_name: Optional[str] = None) -> DatabaseAdapter:
        """
        Get the database adapter for direct access.
        
        Args:
            database_name: Target database (uses default if None)
            
        Returns:
            DatabaseAdapter instance
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        return self._adapters[db_name]
    
    def get_metrics(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for database(s).
        
        Args:
            database_name: Target database (uses default if None)
            
        Returns:
            Dictionary containing performance metrics
        """
        if database_name:
            if database_name not in self._connection_metrics:
                raise ConfigurationError(f"Database '{database_name}' not configured")
            
            return {
                'connection_metrics': self._connection_metrics[database_name],
                'recent_queries': self._query_metrics[database_name][-10:],  # Last 10 queries
                'circuit_breaker': self._load_balancer_state[database_name]
            }
        else:
            return {
                db_name: {
                    'connection_metrics': self._connection_metrics[db_name],
                    'recent_queries': self._query_metrics[db_name][-10:],
                    'circuit_breaker': self._load_balancer_state[db_name]
                }
                for db_name in self._adapters.keys()
            }
    
    def add_query_callback(self, callback: callable) -> None:
        """Add callback to be executed after query execution."""
        self._query_callbacks.append(callback)
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        database_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute a query and return list of rows as dictionaries."""
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            
            try:
                adapter = self._adapters[db_name]
                result = await adapter.fetch_many(connection, query, parameters, size)
                
                self._update_circuit_breaker(db_name, True)
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            self._update_circuit_breaker(db_name, False)
            self.logger.error(f"Fetch many failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "fetch_many", db_name, query=query[:100])
    
    async def fetch_all(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all rows from the database.
        
        Args:
            query: SQL query to execute
            parameters: Query parameters
            database_name: Target database (uses default if None)
            
        Returns:
            All rows as list of dictionaries
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            
            try:
                adapter = self._adapters[db_name]
                result = await adapter.fetch_all(connection, query, parameters)
                
                self._update_circuit_breaker(db_name, True)
                return result
                
            finally:
                await self._close_connection_safe(connection, db_name)
                
        except Exception as e:
            self._update_circuit_breaker(db_name, False)
            self.logger.error(f"Fetch all failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "fetch_all", db_name, query=query[:100])
    
    # Transaction management methods
    
    @asynccontextmanager
    async def transaction(
        self,
        database_name: Optional[str] = None,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> AsyncGenerator[DatabaseConnection, None]:
        """
        Context manager for database transactions.
        
        Args:
            database_name: Target database (uses default if None)
            isolation_level: Transaction isolation level
            read_only: Whether transaction is read-only
            
        Yields:
            DatabaseConnection within transaction context
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        connection = await self.get_connection(db_name, read_only)
        adapter = self._adapters[db_name]
        
        try:
            # Begin transaction
            await adapter.begin_transaction(connection, isolation_level)
            connection.begin_transaction()
            
            # Update status
            self._status[db_name].active_transactions += 1
            
            self.logger.debug(f"Started transaction on database '{db_name}': {connection.connection_id}")
            
            yield connection
            
            # Commit transaction
            await adapter.commit_transaction(connection)
            self.logger.debug(f"Committed transaction on database '{db_name}': {connection.connection_id}")
            
        except Exception as e:
            # Rollback transaction
            try:
                await adapter.rollback_transaction(connection)
                self.logger.debug(f"Rolled back transaction on database '{db_name}': {connection.connection_id}")
            except Exception as rollback_error:
                self.logger.error(f"Rollback failed: {rollback_error}")
            
            self.logger.error(f"Transaction failed on database '{db_name}': {e}")
            raise wrap_database_error(e, "transaction", db_name)
            
        finally:
            # Update status and close connection
            connection.end_transaction()
            self._status[db_name].active_transactions -= 1
            await self._close_connection_safe(connection, db_name)
    
    async def begin_transaction(
        self,
        database_name: Optional[str] = None,
        isolation_level: Optional[IsolationLevel] = None
    ) -> DatabaseConnection:
        """
        Begin a new transaction and return the connection.
        
        Args:
            database_name: Target database (uses default if None)
            isolation_level: Transaction isolation level
            
        Returns:
            DatabaseConnection with active transaction
        """
        db_name = database_name or self.config.default_database
        
        if db_name not in self._adapters:
            raise ConfigurationError(f"Database '{db_name}' not configured")
        
        try:
            connection = await self.get_connection(db_name)
            adapter = self._adapters[db_name]
            
            await adapter.begin_transaction(connection, isolation_level)
            connection.begin_transaction()
            
            self._status[db_name].active_transactions += 1
            
            self.logger.debug(f"Began transaction on database '{db_name}': {connection.connection_id}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to begin transaction on database '{db_name}': {e}")
            raise wrap_database_error(e, "begin_transaction", db_name)
    
    async def commit_transaction(self, connection: DatabaseConnection) -> None:
        """
        Commit a transaction.
        
        Args:
            connection: DatabaseConnection with active transaction
        """
        if not connection.is_in_transaction:
            raise DatabaseError("No active transaction to commit")
        
        try:
            # Find the database name for this connection
            db_name = None
            for name, connections in self._connections.items():
                if connection.connection_id in connections:
                    db_name = name
                    break
            
            if not db_name:
                raise DatabaseError("Connection not found in manager")
            
            adapter = self._adapters[db_name]
            await adapter.commit_transaction(connection)
            
            connection.end_transaction()
            self._status[db_name].active_transactions -= 1
            
            self.logger.debug(f"Committed transaction: {connection.connection_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {e}")
            raise wrap_database_error(e, "commit_transaction")
    
    async def rollback_transaction(self, connection: DatabaseConnection) -> None:
        """
        Rollback a transaction.
        
        Args:
            connection: DatabaseConnection with active transaction
        """
        if not connection.is_in_transaction:
            raise DatabaseError("No active transaction to rollback")
        
        try:
            # Find the database name for this connection
            db_name = None
            for name, connections in self._connections.items():
                if connection.connection_id in connections:
                    db_name = name
                    break
            
            if not db_name:
                raise DatabaseError("Connection not found in manager")
            
            adapter = self._adapters[db_name]
            await adapter.rollback_transaction(connection)
            
            connection.end_transaction()
            self._status[db_name].active_transactions -= 1
            
            self.logger.debug(f"Rolled back transaction: {connection.connection_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to rollback transaction: {e}")
            raise wrap_database_error(e, "rollback_transaction")
    
    # Utility methods
    
    def _update_query_metrics(self, database_name: str, execution_time: float, success: bool) -> None:
        """Update query execution metrics."""
        metrics = self._connection_metrics[database_name]
        
        metrics['total_queries'] += 1
        if not success:
            metrics['failed_queries'] += 1
        
        # Update average response time
        if metrics['total_queries'] == 1:
            metrics['avg_response_time'] = execution_time
        else:
            # Running average
            metrics['avg_response_time'] = (
                (metrics['avg_response_time'] * (metrics['total_queries'] - 1) + execution_time) /
                metrics['total_queries']
            )
        
        # Store detailed metrics (keep last 100 queries)
        query_metrics = self._query_metrics[database_name]
        query_metrics.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'execution_time': execution_time,
            'success': success
        })
        
        # Keep only last 100 entries
        if len(query_metrics) > 100:
            query_metrics.pop(0)
    
    async def _close_connection_safe(self, connection: DatabaseConnection, database_name: str) -> None:
        """Safely close a database connection."""
        try:
            # Remove from connections tracking
            if database_name in self._connections:
                self._connections[database_name].pop(connection.connection_id, None)
            
            # Close the connection using adapter
            if database_name in self._adapters:
                adapter = self._adapters[database_name]
                await adapter.close_connection(connection)
            
            # Update metrics
            if database_name in self._connection_metrics:
                self._connection_metrics[database_name]['active_connections'] -= 1
            
            # Update status
            if database_name in self._status:
                self._status[database_name].connection_count -= 1
                if self._status[database_name].connection_count <= 0:
                    self._status[database_name].is_connected = False
            
        except Exception as e:
            self.logger.error(f"Error closing connection {connection.connection_id}: {e}")
    
    def get_metrics(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for database(s).
        
        Args:
            database_name: Specific database name (all if None)
            
        Returns:
            Dictionary with performance metrics
        """
        if database_name:
            if database_name not in self._connection_metrics:
                raise ConfigurationError(f"Database '{database_name}' not configured")
            
            return {
                database_name: {
                    'connection_metrics': self._connection_metrics[database_name],
                    'query_metrics': self._query_metrics[database_name][-10:],  # Last 10 queries
                    'load_balancer_state': self._load_balancer_state[database_name]
                }
            }
        else:
            return {
                name: {
                    'connection_metrics': self._connection_metrics[name],
                    'query_metrics': self._query_metrics[name][-10:],  # Last 10 queries
                    'load_balancer_state': self._load_balancer_state[name]
                }
                for name in self._connection_metrics
            }
    
    def add_query_callback(self, callback: callable) -> None:
        """Add callback to be executed after query execution."""
        self._query_callbacks.append(callback)
    
    def get_adapter(self, database_name: str) -> DatabaseAdapter:
        """
        Get the database adapter for a specific database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            DatabaseAdapter instance
        """
        if database_name not in self._adapters:
            raise ConfigurationError(f"Database '{database_name}' not configured")
        
        return self._adapters[database_name]
    
    def list_databases(self) -> List[str]:
        """Get list of configured database names."""
        return list(self._adapters.keys())
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized
    
    def is_shutdown(self) -> bool:
        """Check if manager is shutdown."""
        return self._shutdown
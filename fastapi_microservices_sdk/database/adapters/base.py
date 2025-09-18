"""
Base Database Adapter Interface for FastAPI Microservices SDK.

This module defines the abstract base classes and interfaces that all database
adapters must implement. It provides a consistent API across different database
engines while allowing for engine-specific optimizations.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Union, AsyncGenerator, 
    Tuple, Type, Generic, TypeVar, Protocol
)
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..config import DatabaseConnectionConfig, DatabaseEngine
from ..exceptions import DatabaseError, ConnectionError, TransactionError

# Type variables for generic support
T = TypeVar('T')
ResultType = TypeVar('ResultType')


class IsolationLevel(Enum):
    """Database transaction isolation levels."""
    READ_UNCOMMITTED = "READ_UNCOMMITTED"
    READ_COMMITTED = "READ_COMMITTED"
    REPEATABLE_READ = "REPEATABLE_READ"
    SERIALIZABLE = "SERIALIZABLE"


class QueryType(Enum):
    """Types of database queries."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"  # Data Definition Language
    PROCEDURE = "PROCEDURE"
    FUNCTION = "FUNCTION"


@dataclass
class QueryMetrics:
    """Metrics for query execution."""
    execution_time: float
    rows_affected: Optional[int] = None
    rows_returned: Optional[int] = None
    memory_usage: Optional[int] = None
    cpu_time: Optional[float] = None
    io_operations: Optional[int] = None
    cache_hits: Optional[int] = None
    cache_misses: Optional[int] = None


@dataclass
class QueryResult:
    """Result of a database query execution."""
    data: Any
    rows_affected: int = 0
    rows_returned: int = 0
    execution_time: float = 0.0
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Optional[QueryMetrics] = None
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize metrics if not provided."""
        if self.metrics is None:
            self.metrics = QueryMetrics(
                execution_time=self.execution_time,
                rows_affected=self.rows_affected,
                rows_returned=self.rows_returned
            )


class DatabaseConnection:
    """Represents an active database connection with metadata and lifecycle management."""
    
    def __init__(
        self,
        connection_id: str,
        config: DatabaseConnectionConfig,
        native_connection: Any,
        adapter: 'DatabaseAdapter',
        created_at: Optional[datetime] = None
    ):
        self.connection_id = connection_id
        self.config = config
        self.native_connection = native_connection
        self.adapter = adapter
        self.created_at = created_at or datetime.now(timezone.utc)
        self.last_used = self.created_at
        self.is_active = True
        self.transaction_count = 0
        self.query_count = 0
        self._metadata: Dict[str, Any] = {}
        
    @property
    def age(self) -> float:
        """Get connection age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()
    
    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now(timezone.utc) - self.last_used).total_seconds()
    
    def mark_used(self):
        """Mark connection as recently used."""
        self.last_used = datetime.now(timezone.utc)
    
    def set_metadata(self, key: str, value: Any):
        """Set connection metadata."""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get connection metadata."""
        return self._metadata.get(key, default)
    
    async def close(self):
        """Close the database connection."""
        if self.is_active:
            await self.adapter._close_connection(self.native_connection)
            self.is_active = False


class TransactionContext:
    """Context manager for database transactions."""
    
    def __init__(
        self,
        connection: DatabaseConnection,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False,
        timeout: Optional[float] = None
    ):
        self.connection = connection
        self.isolation_level = isolation_level
        self.read_only = read_only
        self.timeout = timeout
        self.transaction_id = str(uuid.uuid4())
        self.started_at: Optional[datetime] = None
        self.committed = False
        self.rolled_back = False
        self._savepoints: List[str] = []
    
    async def __aenter__(self) -> 'TransactionContext':
        """Start the transaction."""
        self.started_at = datetime.now(timezone.utc)
        await self.connection.adapter._begin_transaction(
            self.connection,
            isolation_level=self.isolation_level,
            read_only=self.read_only
        )
        self.connection.transaction_count += 1
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End the transaction."""
        try:
            if exc_type is None and not self.rolled_back:
                await self.commit()
            else:
                await self.rollback()
        finally:
            self.connection.transaction_count -= 1
    
    async def commit(self):
        """Commit the transaction."""
        if not self.committed and not self.rolled_back:
            await self.connection.adapter._commit_transaction(self.connection)
            self.committed = True
    
    async def rollback(self):
        """Rollback the transaction."""
        if not self.committed and not self.rolled_back:
            await self.connection.adapter._rollback_transaction(self.connection)
            self.rolled_back = True
    
    async def savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint."""
        if name is None:
            name = f"sp_{len(self._savepoints) + 1}"
        await self.connection.adapter._create_savepoint(self.connection, name)
        self._savepoints.append(name)
        return name
    
    async def rollback_to_savepoint(self, name: str):
        """Rollback to a savepoint."""
        if name not in self._savepoints:
            raise TransactionError(f"Savepoint '{name}' not found")
        await self.connection.adapter._rollback_to_savepoint(self.connection, name)
        # Remove savepoints created after this one
        index = self._savepoints.index(name)
        self._savepoints = self._savepoints[:index + 1]


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""
    
    def __init__(self, config: DatabaseConnectionConfig):
        self.config = config
        self.engine = config.engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connection_pool: Dict[str, DatabaseConnection] = {}
        self._pool_lock = asyncio.Lock()
        self._is_initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._is_initialized
    
    @property
    def active_connections(self) -> int:
        """Get number of active connections."""
        return len([conn for conn in self._connection_pool.values() if conn.is_active])
    
    # Abstract methods that must be implemented by concrete adapters
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the database adapter."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the database adapter and close all connections."""
        pass
    
    @abstractmethod
    async def create_connection(self) -> DatabaseConnection:
        """Create a new database connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database."""
        pass
    
    @abstractmethod
    async def execute_query(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a query on the database."""
        pass
    
    @abstractmethod
    async def execute_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters_list: List[Dict[str, Any]],
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a query multiple times with different parameters."""
        pass
    
    @abstractmethod
    async def fetch_one(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database."""
        pass
    
    @abstractmethod
    async def fetch_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple rows from the database."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows from the database."""
        pass
    
    # Transaction management (abstract methods)
    
    @abstractmethod
    async def _begin_transaction(
        self,
        connection: DatabaseConnection,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> None:
        """Begin a transaction."""
        pass
    
    @abstractmethod
    async def _commit_transaction(self, connection: DatabaseConnection) -> None:
        """Commit a transaction."""
        pass
    
    @abstractmethod
    async def _rollback_transaction(self, connection: DatabaseConnection) -> None:
        """Rollback a transaction."""
        pass
    
    @abstractmethod
    async def _create_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Create a savepoint."""
        pass
    
    @abstractmethod
    async def _rollback_to_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Rollback to a savepoint."""
        pass
    
    @abstractmethod
    async def _close_connection(self, native_connection: Any) -> None:
        """Close a native database connection."""
        pass
    
    # Concrete methods with default implementations
    
    async def get_connection(self) -> DatabaseConnection:
        """Get a database connection from the pool or create a new one."""
        async with self._pool_lock:
            # Try to reuse an existing connection
            for conn in self._connection_pool.values():
                if conn.is_active and conn.transaction_count == 0:
                    conn.mark_used()
                    return conn
            
            # Create a new connection if pool is not full
            if len(self._connection_pool) < self.config.pool.max_connections:
                connection = await self.create_connection()
                self._connection_pool[connection.connection_id] = connection
                return connection
            
            # Pool is full, wait or raise error based on configuration
            raise ConnectionError(
                f"Connection pool exhausted (max: {self.config.pool.max_connections})",
                context={
                    'database_name': self.config.name,
                    'engine': self.engine.value,
                    'operation': 'get_connection',
                    'pool_size': len(self._connection_pool),
                    'max_connections': self.config.pool.max_connections
                }
            )
    
    async def return_connection(self, connection: DatabaseConnection) -> None:
        """Return a connection to the pool."""
        if connection.transaction_count > 0:
            self.logger.warning(
                f"Returning connection {connection.connection_id} with active transactions"
            )
        connection.mark_used()
    
    async def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from the pool."""
        async with self._pool_lock:
            if connection_id in self._connection_pool:
                connection = self._connection_pool.pop(connection_id)
                await connection.close()
    
    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[DatabaseConnection, None]:
        """Context manager for database connections."""
        conn = await self.get_connection()
        try:
            yield conn
        finally:
            await self.return_connection(conn)
    
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False,
        timeout: Optional[float] = None
    ) -> AsyncGenerator[TransactionContext, None]:
        """Context manager for database transactions."""
        async with self.connection() as conn:
            async with TransactionContext(
                conn, isolation_level, read_only, timeout
            ) as tx:
                yield tx
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status."""
        active_connections = sum(1 for conn in self._connection_pool.values() if conn.is_active)
        total_connections = len(self._connection_pool)
        
        return {
            'total_connections': total_connections,
            'active_connections': active_connections,
            'idle_connections': total_connections - active_connections,
            'max_connections': self.config.pool.max_connections,
            'min_connections': self.config.pool.min_connections,
            'pool_utilization': active_connections / self.config.pool.max_connections if self.config.pool.max_connections > 0 else 0
        }
    
    async def cleanup_idle_connections(self, max_idle_time: float = 300.0) -> int:
        """Clean up idle connections that exceed the maximum idle time."""
        cleaned_count = 0
        current_time = datetime.now(timezone.utc)
        
        async with self._pool_lock:
            connections_to_remove = []
            
            for conn_id, conn in self._connection_pool.items():
                if (conn.transaction_count == 0 and 
                    (current_time - conn.last_used).total_seconds() > max_idle_time):
                    connections_to_remove.append(conn_id)
            
            for conn_id in connections_to_remove:
                await self.remove_connection(conn_id)
                cleaned_count += 1
        
        return cleaned_count
    
    def _create_connection_id(self) -> str:
        """Create a unique connection ID."""
        return f"{self.engine.value}_{uuid.uuid4().hex[:8]}"
    
    def _log_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Log query execution (can be overridden for engine-specific logging)."""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Executing query: {query[:100]}...")
            if parameters:
                self.logger.debug(f"Parameters: {parameters}")


# Protocol for type checking
class AdapterProtocol(Protocol):
    """Protocol for database adapter type checking."""
    
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def create_connection(self) -> DatabaseConnection: ...
    async def health_check(self) -> Dict[str, Any]: ...
    async def execute_query(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult: ...
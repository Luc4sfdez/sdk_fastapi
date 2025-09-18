"""
Database Exceptions for FastAPI Microservices SDK.

This module provides a comprehensive hierarchy of database-specific exceptions
with detailed error information, context, and integration with the SDK's
logging and monitoring systems.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Integration with communication exceptions
try:
    from ..communication.exceptions import CommunicationError
    BASE_ERROR_CLASS = CommunicationError
except ImportError:
    # Fallback to standard Exception if communication module not available
    BASE_ERROR_CLASS = Exception


@dataclass
class DatabaseErrorContext:
    """Context information for database errors."""
    
    database_name: Optional[str] = None
    engine: Optional[str] = None
    operation: Optional[str] = None
    query: Optional[str] = None
    table_name: Optional[str] = None
    connection_id: Optional[str] = None
    transaction_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'database_name': self.database_name,
            'engine': self.engine,
            'operation': self.operation,
            'query': self.query,
            'table_name': self.table_name,
            'connection_id': self.connection_id,
            'transaction_id': self.transaction_id,
            'timestamp': self.timestamp.isoformat(),
            'additional_info': self.additional_info
        }


class DatabaseError(BASE_ERROR_CLASS):
    """Base exception for all database-related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[DatabaseErrorContext] = None,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.context = context or DatabaseErrorContext()
        self.original_error = original_error
        self.error_code = error_code
        self.timestamp = datetime.now(timezone.utc)
    
    def __str__(self) -> str:
        """String representation of the error."""
        base_msg = super().__str__()
        
        if isinstance(self.context, dict):
            if self.context.get('database_name'):
                base_msg += f" (Database: {self.context['database_name']})"
            if self.context.get('operation'):
                base_msg += f" (Operation: {self.context['operation']})"
        elif hasattr(self.context, 'database_name') and self.context.database_name:
            base_msg += f" (Database: {self.context.database_name})"
            if hasattr(self.context, 'operation') and self.context.operation:
                base_msg += f" (Operation: {self.context.operation})"
        
        if self.error_code:
            base_msg += f" (Code: {self.error_code})"
        
        return base_msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': str(self),
            'error_code': self.error_code,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context.to_dict() if self.context else None,
            'original_error': str(self.original_error) if self.original_error else None
        }


class ConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        context: Optional[DatabaseErrorContext] = None,
        **kwargs
    ):
        if context is None:
            context = DatabaseErrorContext(
                database_name=database,
                operation="connection",
                additional_info={
                    'host': host,
                    'port': port
                }
            )
        super().__init__(message, context=context, **kwargs)


class AuthenticationError(DatabaseError):
    """Exception raised when database authentication fails."""
    
    def __init__(
        self,
        message: str,
        username: Optional[str] = None,
        database: Optional[str] = None,
        context: Optional[DatabaseErrorContext] = None,
        **kwargs
    ):
        if context is None:
            context = DatabaseErrorContext(
                database_name=database,
                operation="authentication",
                additional_info={
                    'username': username
                }
            )
        super().__init__(message, context=context, **kwargs)


class QueryError(DatabaseError):
    """Exception raised when query execution fails."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        parameters: Optional[List[Any]] = None,
        **kwargs
    ):
        # Sanitize query for logging (remove sensitive data)
        sanitized_query = self._sanitize_query(query) if query else None
        
        context = DatabaseErrorContext(
            operation="query_execution",
            query=sanitized_query,
            additional_info={
                'parameter_count': len(parameters) if parameters else 0
            }
        )
        super().__init__(message, context=context, **kwargs)
    
    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Sanitize query for safe logging."""
        # Remove potential sensitive data patterns
        import re
        
        # Replace potential password patterns
        query = re.sub(r"password\s*=\s*['\"][^'\"]*['\"]", "password='***'", query, flags=re.IGNORECASE)
        
        # Replace potential token patterns
        query = re.sub(r"token\s*=\s*['\"][^'\"]*['\"]", "token='***'", query, flags=re.IGNORECASE)
        
        # Truncate very long queries
        if len(query) > 1000:
            query = query[:1000] + "... [truncated]"
        
        return query


class TransactionError(DatabaseError):
    """Exception raised when transaction operations fail."""
    
    def __init__(
        self,
        message: str,
        transaction_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation=f"transaction_{operation}" if operation else "transaction",
            transaction_id=transaction_id
        )
        super().__init__(message, context=context, **kwargs)


class MigrationError(DatabaseError):
    """Exception raised when database migration fails."""
    
    def __init__(
        self,
        message: str,
        migration_name: Optional[str] = None,
        migration_version: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation=f"migration_{operation}" if operation else "migration",
            additional_info={
                'migration_name': migration_name,
                'migration_version': migration_version
            }
        )
        super().__init__(message, context=context, **kwargs)


class PoolError(DatabaseError):
    """Exception raised when connection pool operations fail."""
    
    def __init__(
        self,
        message: str,
        pool_name: Optional[str] = None,
        pool_size: Optional[int] = None,
        active_connections: Optional[int] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="connection_pool",
            additional_info={
                'pool_name': pool_name,
                'pool_size': pool_size,
                'active_connections': active_connections
            }
        )
        super().__init__(message, context=context, **kwargs)


class SecurityError(DatabaseError):
    """Exception raised when database security violations occur."""
    
    def __init__(
        self,
        message: str,
        security_violation: Optional[str] = None,
        user: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="security_check",
            additional_info={
                'security_violation': security_violation,
                'user': user
            }
        )
        super().__init__(message, context=context, **kwargs)


class ConfigurationError(DatabaseError):
    """Exception raised when database configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="configuration",
            additional_info={
                'config_key': config_key,
                'config_value': str(config_value) if config_value is not None else None
            }
        )
        super().__init__(message, context=context, **kwargs)


class TimeoutError(DatabaseError):
    """Exception raised when database operations timeout."""
    
    def __init__(
        self,
        message: str,
        timeout_duration: Optional[float] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation=f"timeout_{operation}" if operation else "timeout",
            additional_info={
                'timeout_duration': timeout_duration
            }
        )
        super().__init__(message, context=context, **kwargs)


class IntegrityError(DatabaseError):
    """Exception raised when database integrity constraints are violated."""
    
    def __init__(
        self,
        message: str,
        constraint_name: Optional[str] = None,
        table_name: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="integrity_check",
            table_name=table_name,
            additional_info={
                'constraint_name': constraint_name
            }
        )
        super().__init__(message, context=context, **kwargs)


class LockError(DatabaseError):
    """Exception raised when database locking operations fail."""
    
    def __init__(
        self,
        message: str,
        lock_type: Optional[str] = None,
        resource: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="locking",
            additional_info={
                'lock_type': lock_type,
                'resource': resource
            }
        )
        super().__init__(message, context=context, **kwargs)


class ReplicationError(DatabaseError):
    """Exception raised when database replication operations fail."""
    
    def __init__(
        self,
        message: str,
        replica_host: Optional[str] = None,
        replication_lag: Optional[float] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="replication",
            additional_info={
                'replica_host': replica_host,
                'replication_lag': replication_lag
            }
        )
        super().__init__(message, context=context, **kwargs)


class BackupError(DatabaseError):
    """Exception raised when database backup operations fail."""
    
    def __init__(
        self,
        message: str,
        backup_type: Optional[str] = None,
        backup_path: Optional[str] = None,
        **kwargs
    ):
        context = DatabaseErrorContext(
            operation="backup",
            additional_info={
                'backup_type': backup_type,
                'backup_path': backup_path
            }
        )
        super().__init__(message, context=context, **kwargs)


# Engine-specific exceptions
class PostgreSQLError(DatabaseError):
    """PostgreSQL-specific database error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context', DatabaseErrorContext())
        context.engine = "postgresql"
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class MySQLError(DatabaseError):
    """MySQL-specific database error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context', DatabaseErrorContext())
        context.engine = "mysql"
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class MongoDBError(DatabaseError):
    """MongoDB-specific database error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context', DatabaseErrorContext())
        context.engine = "mongodb"
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class SQLiteError(DatabaseError):
    """SQLite-specific database error."""
    
    def __init__(self, message: str, **kwargs):
        context = kwargs.get('context', DatabaseErrorContext())
        context.engine = "sqlite"
        kwargs['context'] = context
        super().__init__(message, **kwargs)


# ORM-specific exceptions
class ORMError(DatabaseError):
    """Base exception for ORM-related errors."""
    
    def __init__(
        self,
        message: str,
        orm_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        context = kwargs.get('context', DatabaseErrorContext())
        context.operation = "orm_operation"
        context.additional_info.update({
            'orm_name': orm_name,
            'model_name': model_name
        })
        kwargs['context'] = context
        super().__init__(message, **kwargs)


class SQLAlchemyError(ORMError):
    """SQLAlchemy-specific ORM error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, orm_name="sqlalchemy", **kwargs)


class TortoiseError(ORMError):
    """Tortoise ORM-specific error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, orm_name="tortoise", **kwargs)


class BeanieError(ORMError):
    """Beanie ODM-specific error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, orm_name="beanie", **kwargs)


# Utility functions for error handling
def wrap_database_error(
    original_error: Exception,
    operation: str,
    database_name: Optional[str] = None,
    query: Optional[str] = None
) -> DatabaseError:
    """Wrap a generic exception as a DatabaseError with context."""
    
    context = DatabaseErrorContext(
        database_name=database_name,
        operation=operation,
        query=query
    )
    
    # Try to determine the most appropriate exception type
    error_message = str(original_error)
    error_type = type(original_error).__name__
    
    if "connection" in error_message.lower() or "connect" in error_message.lower():
        return ConnectionError(
            f"Connection failed: {error_message}",
            context=context,
            original_error=original_error
        )
    elif "authentication" in error_message.lower() or "auth" in error_message.lower():
        return AuthenticationError(
            f"Authentication failed: {error_message}",
            context=context,
            original_error=original_error
        )
    elif "timeout" in error_message.lower():
        return TimeoutError(
            f"Operation timed out: {error_message}",
            context=context,
            original_error=original_error
        )
    elif "integrity" in error_message.lower() or "constraint" in error_message.lower():
        return IntegrityError(
            f"Integrity constraint violation: {error_message}",
            context=context,
            original_error=original_error
        )
    else:
        return DatabaseError(
            f"Database operation failed ({error_type}): {error_message}",
            context=context,
            original_error=original_error
        )


def create_error_from_driver_exception(
    driver_error: Exception,
    engine: str,
    operation: str,
    **context_kwargs
) -> DatabaseError:
    """Create appropriate database error from driver-specific exception."""
    
    context = DatabaseErrorContext(
        engine=engine,
        operation=operation,
        **context_kwargs
    )
    
    error_message = str(driver_error)
    
    # Engine-specific error mapping
    if engine == "postgresql":
        return PostgreSQLError(
            f"PostgreSQL error: {error_message}",
            context=context,
            original_error=driver_error
        )
    elif engine == "mysql":
        return MySQLError(
            f"MySQL error: {error_message}",
            context=context,
            original_error=driver_error
        )
    elif engine == "mongodb":
        return MongoDBError(
            f"MongoDB error: {error_message}",
            context=context,
            original_error=driver_error
        )
    elif engine == "sqlite":
        return SQLiteError(
            f"SQLite error: {error_message}",
            context=context,
            original_error=driver_error
        )
    else:
        return DatabaseError(
            f"Database error ({engine}): {error_message}",
            context=context,
            original_error=driver_error
        )


# Exception hierarchy for easy catching
DATABASE_EXCEPTIONS = (
    DatabaseError,
    ConnectionError,
    AuthenticationError,
    QueryError,
    TransactionError,
    MigrationError,
    PoolError,
    SecurityError,
    ConfigurationError,
    TimeoutError,
    IntegrityError,
    LockError,
    ReplicationError,
    BackupError,
    ORMError
)

ENGINE_SPECIFIC_EXCEPTIONS = (
    PostgreSQLError,
    MySQLError,
    MongoDBError,
    SQLiteError
)

ORM_SPECIFIC_EXCEPTIONS = (
    SQLAlchemyError,
    TortoiseError,
    BeanieError
)
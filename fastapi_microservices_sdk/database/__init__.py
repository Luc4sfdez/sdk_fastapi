"""
Database Integration Module for FastAPI Microservices SDK.

This module provides comprehensive database integration with support for multiple
database engines, ORMs, connection pooling, migrations, and enterprise features.

Supported Databases:
- PostgreSQL (via asyncpg)
- MySQL (via aiomysql)  
- MongoDB (via motor)
- SQLite (via aiosqlite)

Supported ORMs:
- SQLAlchemy 2.0 (async)
- Tortoise ORM (FastAPI native)
- Beanie (MongoDB ODM)

Features:
- Connection pooling and load balancing
- Type-safe query builder
- Migration system with version control
- Security integration with credential management
- Performance monitoring and analytics
- Transaction management including distributed transactions

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .config import (
    DatabaseConfig,
    DatabaseConnectionConfig,
    ConnectionPoolConfig,
    MigrationConfig,
    DatabaseSecurityConfig,
    DatabaseEngine,
    DatabaseCredentials
)

from .exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    MigrationError,
    TransactionError,
    PoolError,
    SecurityError as DatabaseSecurityError
)

from .manager import (
    DatabaseManager,
    get_database_manager
)

# Optional imports with graceful fallback
try:
    from .adapters import (
        DatabaseAdapter,
        DatabaseConnection,
        QueryResult,
        TransactionContext,
        AdapterRegistry,
        PostgreSQLAdapter,
        MySQLAdapter,
        MongoDBAdapter,
        SQLiteAdapter,
        POSTGRESQL_AVAILABLE,
        MYSQL_AVAILABLE,
        MONGODB_AVAILABLE,
        SQLITE_AVAILABLE
    )
    DATABASE_ADAPTERS_AVAILABLE = True
except ImportError:
    DATABASE_ADAPTERS_AVAILABLE = False

try:
    from .pool import (
        ConnectionPool,
        PoolHealth,
        LoadBalancer
    )
    CONNECTION_POOL_AVAILABLE = True
except ImportError:
    CONNECTION_POOL_AVAILABLE = False

try:
    from .orm import (
        ORMIntegration,
        SQLAlchemyIntegration,
        TortoiseIntegration,
        BeanieIntegration
    )
    ORM_INTEGRATION_AVAILABLE = True
except ImportError:
    ORM_INTEGRATION_AVAILABLE = False

try:
    from .query import (
        QueryBuilder,
        QueryResult,
        QueryCache
    )
    QUERY_BUILDER_AVAILABLE = True
except ImportError:
    QUERY_BUILDER_AVAILABLE = False

try:
    from .migrations import (
        MigrationManager,
        Migration,
        MigrationOperation
    )
    MIGRATION_SYSTEM_AVAILABLE = True
except ImportError:
    MIGRATION_SYSTEM_AVAILABLE = False

try:
    from .security import (
        DatabaseCredentialManager,
        DatabaseSecurityManager
    )
    DATABASE_SECURITY_AVAILABLE = True
except ImportError:
    DATABASE_SECURITY_AVAILABLE = False

try:
    from .monitoring import (
        DatabaseMetrics,
        DatabaseMonitor,
        QueryAnalytics
    )
    DATABASE_MONITORING_AVAILABLE = True
except ImportError:
    DATABASE_MONITORING_AVAILABLE = False

try:
    from .caching import (
        CacheManager,
        CacheConfig,
        CacheBackend,
        CacheStrategy,
        InvalidationPolicy,
        SerializationFormat,
        CacheEntry,
        CacheStats,
        InvalidationManager,
        InvalidationEvent,
        InvalidationRule,
        CacheError,
        CacheBackendError,
        CacheSerializationError,
        CacheInvalidationError,
        CacheConfigurationError
    )
    DATABASE_CACHING_AVAILABLE = True
except ImportError:
    DATABASE_CACHING_AVAILABLE = False

try:
    from .transactions import (
        TransactionManager,
        Transaction,
        DistributedTransaction,
        SagaTransaction
    )
    TRANSACTION_MANAGEMENT_AVAILABLE = True
except ImportError:
    TRANSACTION_MANAGEMENT_AVAILABLE = False

try:
    from .fastapi_integration import (
        FastAPIDatabaseIntegration,
        get_database_session,
        database_dependency
    )
    FASTAPI_INTEGRATION_AVAILABLE = True
except ImportError:
    FASTAPI_INTEGRATION_AVAILABLE = False

# Version and availability information
__version__ = "1.0.0"
__author__ = "FastAPI Microservices SDK"

__all__ = [
    # Core configuration
    'DatabaseConfig',
    'DatabaseConnectionConfig', 
    'ConnectionPoolConfig',
    'MigrationConfig',
    'DatabaseSecurityConfig',
    'DatabaseEngine',
    'DatabaseCredentials',
    
    # Core exceptions
    'DatabaseError',
    'ConnectionError',
    'QueryError', 
    'MigrationError',
    'TransactionError',
    'PoolError',
    'DatabaseSecurityError',
    
    # Core manager
    'DatabaseManager',
    'get_database_manager',
    
    # Availability flags
    'DATABASE_ADAPTERS_AVAILABLE',
    'CONNECTION_POOL_AVAILABLE',
    'ORM_INTEGRATION_AVAILABLE',
    'QUERY_BUILDER_AVAILABLE',
    'MIGRATION_SYSTEM_AVAILABLE',
    'DATABASE_SECURITY_AVAILABLE',
    'DATABASE_MONITORING_AVAILABLE',
    'DATABASE_CACHING_AVAILABLE',
    'TRANSACTION_MANAGEMENT_AVAILABLE',
    'FASTAPI_INTEGRATION_AVAILABLE',
    
    # Version info
    '__version__',
    '__author__'
]

# Conditional exports based on availability
if DATABASE_ADAPTERS_AVAILABLE:
    __all__.extend([
        'DatabaseAdapter',
        'DatabaseConnection',
        'QueryResult',
        'TransactionContext',
        'AdapterRegistry',
        'PostgreSQLAdapter',
        'MySQLAdapter', 
        'MongoDBAdapter',
        'SQLiteAdapter',
        'POSTGRESQL_AVAILABLE',
        'MYSQL_AVAILABLE',
        'MONGODB_AVAILABLE',
        'SQLITE_AVAILABLE'
    ])

if CONNECTION_POOL_AVAILABLE:
    __all__.extend([
        'ConnectionPool',
        'PoolHealth',
        'LoadBalancer'
    ])

if ORM_INTEGRATION_AVAILABLE:
    __all__.extend([
        'ORMIntegration',
        'SQLAlchemyIntegration',
        'TortoiseIntegration',
        'BeanieIntegration'
    ])

if QUERY_BUILDER_AVAILABLE:
    __all__.extend([
        'QueryBuilder',
        'QueryResult',
        'QueryCache'
    ])

if MIGRATION_SYSTEM_AVAILABLE:
    __all__.extend([
        'MigrationManager',
        'Migration',
        'MigrationOperation'
    ])

if DATABASE_SECURITY_AVAILABLE:
    __all__.extend([
        'DatabaseCredentialManager',
        'DatabaseSecurityManager'
    ])

if DATABASE_MONITORING_AVAILABLE:
    __all__.extend([
        'DatabaseMetrics',
        'DatabaseMonitor',
        'QueryAnalytics'
    ])

if DATABASE_CACHING_AVAILABLE:
    __all__.extend([
        'CacheManager',
        'CacheConfig',
        'CacheBackend',
        'CacheStrategy',
        'InvalidationPolicy',
        'SerializationFormat',
        'CacheEntry',
        'CacheStats',
        'InvalidationManager',
        'InvalidationEvent',
        'InvalidationRule',
        'CacheError',
        'CacheBackendError',
        'CacheSerializationError',
        'CacheInvalidationError',
        'CacheConfigurationError'
    ])

if TRANSACTION_MANAGEMENT_AVAILABLE:
    __all__.extend([
        'TransactionManager',
        'Transaction',
        'DistributedTransaction',
        'SagaTransaction'
    ])

if FASTAPI_INTEGRATION_AVAILABLE:
    __all__.extend([
        'FastAPIDatabaseIntegration',
        'get_database_session',
        'database_dependency'
    ])


def check_database_dependencies():
    """Check if all required database dependencies are available."""
    missing_deps = []
    
    # Check core database drivers
    try:
        import asyncpg
    except ImportError:
        missing_deps.append('asyncpg (PostgreSQL)')
    
    try:
        import aiomysql
    except ImportError:
        missing_deps.append('aiomysql (MySQL)')
    
    try:
        import motor
    except ImportError:
        missing_deps.append('motor (MongoDB)')
    
    try:
        import aiosqlite
    except ImportError:
        missing_deps.append('aiosqlite (SQLite)')
    
    # Check ORM dependencies
    try:
        import sqlalchemy
        if not hasattr(sqlalchemy, '__version__') or not sqlalchemy.__version__.startswith('2.'):
            missing_deps.append('sqlalchemy>=2.0 (current version may be incompatible)')
    except ImportError:
        missing_deps.append('sqlalchemy>=2.0')
    
    try:
        import tortoise
    except ImportError:
        missing_deps.append('tortoise-orm')
    
    try:
        import beanie
    except ImportError:
        missing_deps.append('beanie')
    
    return missing_deps


def get_database_status():
    """Get the status of database dependencies and features."""
    missing_deps = check_database_dependencies()
    
    return {
        'adapters_available': DATABASE_ADAPTERS_AVAILABLE,
        'connection_pool_available': CONNECTION_POOL_AVAILABLE,
        'orm_integration_available': ORM_INTEGRATION_AVAILABLE,
        'query_builder_available': QUERY_BUILDER_AVAILABLE,
        'migration_system_available': MIGRATION_SYSTEM_AVAILABLE,
        'security_available': DATABASE_SECURITY_AVAILABLE,
        'monitoring_available': DATABASE_MONITORING_AVAILABLE,
        'caching_available': DATABASE_CACHING_AVAILABLE,
        'transaction_management_available': TRANSACTION_MANAGEMENT_AVAILABLE,
        'fastapi_integration_available': FASTAPI_INTEGRATION_AVAILABLE,
        'all_dependencies_available': len(missing_deps) == 0,
        'missing_dependencies': missing_deps,
        'version': __version__
    }


# Initialize logging for database module
import logging
logger = logging.getLogger(__name__)
logger.info(f"FastAPI Microservices SDK Database Module v{__version__} initialized")

# Log availability status
status = get_database_status()
if status['all_dependencies_available']:
    logger.info("All database dependencies are available")
else:
    logger.warning(f"Missing database dependencies: {', '.join(status['missing_dependencies'])}")
    logger.info("Some database features may not be available")

# Log feature availability
available_features = []
if DATABASE_ADAPTERS_AVAILABLE:
    available_features.append("Database Adapters")
if CONNECTION_POOL_AVAILABLE:
    available_features.append("Connection Pooling")
if ORM_INTEGRATION_AVAILABLE:
    available_features.append("ORM Integration")
if QUERY_BUILDER_AVAILABLE:
    available_features.append("Query Builder")
if MIGRATION_SYSTEM_AVAILABLE:
    available_features.append("Migration System")
if DATABASE_MONITORING_AVAILABLE:
    available_features.append("Database Monitoring")
if DATABASE_CACHING_AVAILABLE:
    available_features.append("Database Caching")

if available_features:
    logger.info(f"Available features: {', '.join(available_features)}")
else:
    logger.warning("No advanced database features available - only core configuration loaded")
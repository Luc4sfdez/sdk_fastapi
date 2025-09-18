"""
Database Foundation Example

This example demonstrates the database foundation components including:
- Database configuration for multiple engines
- Database manager with connection management
- Error handling and exception hierarchy
- Health monitoring and status tracking

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import SDK components
from fastapi_microservices_sdk.database.config import (
    DatabaseConfig,
    DatabaseConnectionConfig,
    ConnectionPoolConfig,
    MigrationConfig,
    DatabaseSecurityConfig,
    DatabaseEngine,
    DatabaseCredentials,
    create_postgresql_config,
    create_mysql_config,
    create_mongodb_config,
    create_sqlite_config
)

from fastapi_microservices_sdk.database.exceptions import (
    DatabaseError,
    ConnectionError,
    ConfigurationError,
    wrap_database_error
)

from fastapi_microservices_sdk.database.manager import (
    DatabaseManager,
    get_database_manager,
    set_database_manager,
    initialize_database_manager
)


async def demonstrate_database_configuration():
    """Demonstrate database configuration capabilities."""
    logger.info("=== Database Configuration Examples ===")
    
    # 1. SQLite Configuration (for development/testing)
    logger.info("\n--- SQLite Configuration ---")
    sqlite_config = create_sqlite_config(database="example.db")
    logger.info(f"SQLite Config: {sqlite_config.engine.value} -> {sqlite_config.database}")
    logger.info(f"Connection URL: {sqlite_config.get_connection_url()}")
    
    # 2. PostgreSQL Configuration
    logger.info("\n--- PostgreSQL Configuration ---")
    pg_config = create_postgresql_config(
        host="localhost",
        database="example_db",
        username="postgres",
        password="password",
        ssl_enabled=False
    )
    logger.info(f"PostgreSQL Config: {pg_config.host}:{pg_config.port}/{pg_config.database}")
    logger.info(f"Connection URL: {pg_config.get_connection_url()}")
    
    # 3. MySQL Configuration
    logger.info("\n--- MySQL Configuration ---")
    mysql_config = create_mysql_config(
        host="localhost",
        database="example_db",
        username="root",
        password="password"
    )
    logger.info(f"MySQL Config: {mysql_config.host}:{mysql_config.port}/{mysql_config.database}")
    logger.info(f"Connection URL: {mysql_config.get_connection_url()}")
    
    # 4. MongoDB Configuration
    logger.info("\n--- MongoDB Configuration ---")
    mongo_config = create_mongodb_config(
        host="localhost",
        database="example_db",
        username="admin",
        password="password",
        auth_source="admin"
    )
    logger.info(f"MongoDB Config: {mongo_config.host}:{mongo_config.port}/{mongo_config.database}")
    logger.info(f"Auth Source: {mongo_config.credentials.auth_source}")
    
    # 5. Multi-Database Configuration
    logger.info("\n--- Multi-Database Configuration ---")
    multi_db_config = DatabaseConfig(
        databases={
            "primary": sqlite_config,
            "analytics": pg_config,
            "cache": mongo_config
        },
        default_database="primary",
        connection_pools=ConnectionPoolConfig(
            min_connections=2,
            max_connections=20,
            connection_timeout=30.0
        ),
        migration_config=MigrationConfig(
            migrations_directory=Path("migrations"),
            backup_before_migration=True
        ),
        security_config=DatabaseSecurityConfig(
            use_secrets_manager=False,  # Disabled for example
            enable_audit_logging=True,
            enable_query_sanitization=True
        )
    )
    
    logger.info(f"Multi-DB Config: {len(multi_db_config.databases)} databases")
    logger.info(f"Default database: {multi_db_config.default_database}")
    logger.info(f"Pool config: {multi_db_config.connection_pools.min_connections}-{multi_db_config.connection_pools.max_connections} connections")
    
    return multi_db_config


async def demonstrate_database_manager():
    """Demonstrate database manager capabilities."""
    logger.info("\n=== Database Manager Examples ===")
    
    # Create configuration with SQLite for simplicity
    config = DatabaseConfig(
        databases={
            "primary": create_sqlite_config(database=":memory:"),  # In-memory for demo
            "secondary": create_sqlite_config(database="example.db")
        },
        default_database="primary"
    )
    
    # 1. Basic Manager Usage
    logger.info("\n--- Basic Manager Usage ---")
    manager = DatabaseManager(config)
    
    logger.info(f"Manager created with {len(config.databases)} databases")
    logger.info(f"Initialized: {manager._initialized}")
    
    # 2. Manager Lifecycle
    logger.info("\n--- Manager Lifecycle ---")
    
    # Add callbacks
    async def startup_callback(mgr):
        logger.info("🚀 Database manager startup callback executed")
    
    async def shutdown_callback(mgr):
        logger.info("🛑 Database manager shutdown callback executed")
    
    def health_callback(db_name, is_healthy):
        status = "✅ healthy" if is_healthy else "❌ unhealthy"
        logger.info(f"💓 Health check for {db_name}: {status}")
    
    manager.add_startup_callback(startup_callback)
    manager.add_shutdown_callback(shutdown_callback)
    manager.add_health_check_callback(health_callback)
    
    # Initialize manager
    await manager.initialize()
    logger.info(f"Manager initialized: {manager._initialized}")
    
    # 3. Status Monitoring
    logger.info("\n--- Status Monitoring ---")
    status = manager.get_status()
    for db_name, db_status in status.items():
        logger.info(f"Database {db_name}:")
        logger.info(f"  Connected: {db_status['is_connected']}")
        logger.info(f"  Connections: {db_status['connection_count']}")
        logger.info(f"  Health Status: {db_status['health_check_status']}")
    
    # 4. Health Checks
    logger.info("\n--- Health Checks ---")
    try:
        health_results = await manager.health_check()
        for db_name, health_info in health_results.items():
            logger.info(f"Health check {db_name}: {health_info}")
    except Exception as e:
        logger.warning(f"Health check failed (expected for demo): {e}")
    
    # 5. Connection Management (would work with real databases)
    logger.info("\n--- Connection Management ---")
    try:
        # This will fail because we don't have aiosqlite installed
        # but demonstrates the API
        async with manager.connection("primary") as conn:
            logger.info(f"Got connection: {conn.connection_id}")
    except Exception as e:
        logger.info(f"Connection demo (expected to fail without drivers): {type(e).__name__}")
    
    # Cleanup
    await manager.shutdown()
    logger.info(f"Manager shutdown: {not manager._initialized}")
    
    return manager


async def demonstrate_error_handling():
    """Demonstrate database error handling."""
    logger.info("\n=== Error Handling Examples ===")
    
    # 1. Configuration Errors
    logger.info("\n--- Configuration Errors ---")
    try:
        # Invalid configuration
        DatabaseConfig(databases={})  # Empty databases
    except ValueError as e:
        logger.info(f"Configuration error caught: {e}")
    
    try:
        # Invalid default database
        DatabaseConfig(
            databases={"test": create_sqlite_config()},
            default_database="nonexistent"
        )
    except ValueError as e:
        logger.info(f"Default database error caught: {e}")
    
    # 2. Connection Errors
    logger.info("\n--- Connection Errors ---")
    conn_error = ConnectionError(
        "Failed to connect to database",
        host="localhost",
        port=5432,
        database="nonexistent"
    )
    
    logger.info(f"Connection error: {conn_error}")
    logger.info(f"Error context: {conn_error.context.to_dict()}")
    
    # 3. Wrapping Generic Errors
    logger.info("\n--- Error Wrapping ---")
    original_error = ValueError("Connection refused")
    wrapped_error = wrap_database_error(
        original_error,
        operation="connect",
        database_name="test_db"
    )
    
    logger.info(f"Original error: {original_error}")
    logger.info(f"Wrapped error: {wrapped_error}")
    logger.info(f"Wrapped error type: {type(wrapped_error).__name__}")
    
    # 4. Error Serialization
    logger.info("\n--- Error Serialization ---")
    error_dict = wrapped_error.to_dict()
    logger.info("Error as dictionary:")
    for key, value in error_dict.items():
        logger.info(f"  {key}: {value}")


async def demonstrate_global_manager():
    """Demonstrate global database manager."""
    logger.info("\n=== Global Manager Examples ===")
    
    # 1. Global Manager Functions
    logger.info("\n--- Global Manager Functions ---")
    logger.info(f"Initial global manager: {get_database_manager()}")
    
    # 2. Initialize Global Manager
    logger.info("\n--- Initialize Global Manager ---")
    config = DatabaseConfig(
        databases={
            "default": create_sqlite_config(database=":memory:")
        }
    )
    
    try:
        global_manager = await initialize_database_manager(config)
        logger.info(f"Global manager initialized: {global_manager._initialized}")
        logger.info(f"Retrieved global manager: {get_database_manager() is global_manager}")
        
        # Use global manager
        status = global_manager.get_status()
        logger.info(f"Global manager status: {len(status)} databases")
        
        # Cleanup
        await global_manager.shutdown()
        set_database_manager(None)
        logger.info(f"Global manager cleaned up: {get_database_manager()}")
        
    except Exception as e:
        logger.info(f"Global manager demo (expected to fail without drivers): {type(e).__name__}")


async def demonstrate_advanced_configuration():
    """Demonstrate advanced configuration features."""
    logger.info("\n=== Advanced Configuration Examples ===")
    
    # 1. SSL Configuration
    logger.info("\n--- SSL Configuration ---")
    from fastapi_microservices_sdk.database.config import SSLConfig
    
    ssl_config = SSLConfig(
        enabled=True,
        verify_mode="CERT_REQUIRED",
        check_hostname=True
    )
    
    logger.info(f"SSL enabled: {ssl_config.enabled}")
    logger.info(f"Verify mode: {ssl_config.verify_mode}")
    logger.info(f"Check hostname: {ssl_config.check_hostname}")
    
    # Create SSL context (will work even without certificates)
    ssl_context = ssl_config.create_ssl_context()
    logger.info(f"SSL context created: {ssl_context is not None}")
    
    # 2. Connection Pool Configuration
    logger.info("\n--- Connection Pool Configuration ---")
    pool_config = ConnectionPoolConfig(
        min_connections=5,
        max_connections=50,
        connection_timeout=30.0,
        idle_timeout=600.0,
        scale_up_threshold=0.8,
        scale_down_threshold=0.2
    )
    
    logger.info(f"Pool size: {pool_config.min_connections}-{pool_config.max_connections}")
    logger.info(f"Timeouts: connection={pool_config.connection_timeout}s, idle={pool_config.idle_timeout}s")
    logger.info(f"Scaling: up@{pool_config.scale_up_threshold}, down@{pool_config.scale_down_threshold}")
    
    # 3. Migration Configuration
    logger.info("\n--- Migration Configuration ---")
    migration_config = MigrationConfig(
        migrations_directory=Path("db/migrations"),
        backup_before_migration=True,
        enable_rollback=True,
        max_rollback_steps=5
    )
    
    logger.info(f"Migrations dir: {migration_config.migrations_directory}")
    logger.info(f"Backup enabled: {migration_config.backup_before_migration}")
    logger.info(f"Rollback enabled: {migration_config.enable_rollback}")
    logger.info(f"Max rollback steps: {migration_config.max_rollback_steps}")
    
    # 4. Security Configuration
    logger.info("\n--- Security Configuration ---")
    security_config = DatabaseSecurityConfig(
        use_secrets_manager=True,
        secrets_manager_backend="vault",
        require_ssl=True,
        enable_query_sanitization=True,
        enable_audit_logging=True,
        max_query_length=5000
    )
    
    logger.info(f"Secrets manager: {security_config.use_secrets_manager} ({security_config.secrets_manager_backend})")
    logger.info(f"SSL required: {security_config.require_ssl}")
    logger.info(f"Query sanitization: {security_config.enable_query_sanitization}")
    logger.info(f"Audit logging: {security_config.enable_audit_logging}")
    logger.info(f"Max query length: {security_config.max_query_length}")


async def demonstrate_dependency_status():
    """Demonstrate dependency status checking."""
    logger.info("\n=== Dependency Status Examples ===")
    
    from fastapi_microservices_sdk.database import (
        check_database_dependencies,
        get_database_status
    )
    
    # 1. Check Missing Dependencies
    logger.info("\n--- Missing Dependencies ---")
    missing_deps = check_database_dependencies()
    if missing_deps:
        logger.info("Missing database dependencies:")
        for dep in missing_deps:
            logger.info(f"  ❌ {dep}")
    else:
        logger.info("✅ All database dependencies available!")
    
    # 2. Get Database Status
    logger.info("\n--- Database Status ---")
    status = get_database_status()
    
    logger.info("Database module status:")
    logger.info(f"  Adapters available: {status['adapters_available']}")
    logger.info(f"  Connection pool available: {status['connection_pool_available']}")
    logger.info(f"  ORM integration available: {status['orm_integration_available']}")
    logger.info(f"  Query builder available: {status['query_builder_available']}")
    logger.info(f"  Migration system available: {status['migration_system_available']}")
    logger.info(f"  Security available: {status['security_available']}")
    logger.info(f"  Monitoring available: {status['monitoring_available']}")
    logger.info(f"  Transaction management available: {status['transaction_management_available']}")
    logger.info(f"  FastAPI integration available: {status['fastapi_integration_available']}")
    
    logger.info(f"\nAll dependencies available: {status['all_dependencies_available']}")
    logger.info(f"Module version: {status['version']}")
    
    if status['missing_dependencies']:
        logger.info("\nTo install missing dependencies:")
        logger.info("  pip install asyncpg aiomysql motor aiosqlite")
        logger.info("  pip install sqlalchemy tortoise-orm beanie")


async def main():
    """Main example function."""
    logger.info("🚀 Starting Database Foundation Example")
    
    try:
        # Demonstrate configuration
        config = await demonstrate_database_configuration()
        
        # Demonstrate manager
        manager = await demonstrate_database_manager()
        
        # Demonstrate error handling
        await demonstrate_error_handling()
        
        # Demonstrate global manager
        await demonstrate_global_manager()
        
        # Demonstrate advanced configuration
        await demonstrate_advanced_configuration()
        
        # Demonstrate dependency status
        await demonstrate_dependency_status()
        
        logger.info("\n✅ All database foundation demonstrations completed successfully!")
        
        logger.info("\n📋 Summary:")
        logger.info("  ✅ Database configuration for multiple engines")
        logger.info("  ✅ Database manager with lifecycle management")
        logger.info("  ✅ Comprehensive error handling")
        logger.info("  ✅ Health monitoring and status tracking")
        logger.info("  ✅ Advanced configuration options")
        logger.info("  ✅ Dependency status checking")
        
        logger.info("\n🎯 Next Steps:")
        logger.info("  1. Install database drivers: pip install asyncpg aiomysql motor aiosqlite")
        logger.info("  2. Install ORMs: pip install sqlalchemy tortoise-orm beanie")
        logger.info("  3. Continue with Task 2.1: Database Adapters Implementation")
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
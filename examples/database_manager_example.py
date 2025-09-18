"""
Database Manager Example for FastAPI Microservices SDK.

This example demonstrates how to use the DatabaseManager to work with
multiple database engines in a unified way with enterprise-grade features.

Features demonstrated:
- Multi-database configuration and management
- Connection pooling and health monitoring
- Query execution with performance metrics
- Transaction management with proper error handling
- Circuit breaker and load balancing
- Real-time monitoring and callbacks
- Integration with security and logging systems

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi_microservices_sdk.database import (
    DatabaseManager,
    DatabaseConfig,
    DatabaseConnectionConfig,
    DatabaseEngine,
    QueryType,
    IsolationLevel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database_manager() -> DatabaseManager:
    """Setup and configure the database manager with multiple databases."""
    
    # Configure multiple databases
    config = DatabaseConfig(
        default_database="main_db",
        health_check_interval=30.0,
        databases={
            # PostgreSQL primary database
            "main_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.POSTGRESQL,
                host="localhost",
                port=5432,
                database="microservices_main",
                username="postgres",
                password="password",
                pool_size=10,
                max_overflow=20,
                pool_timeout=30.0,
                pool_recycle=3600,
                ssl_mode="prefer",
                options={
                    "application_name": "microservices_sdk",
                    "connect_timeout": 10
                }
            ),
            
            # MySQL analytics database
            "analytics_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.MYSQL,
                host="localhost",
                port=3306,
                database="analytics",
                username="mysql_user",
                password="mysql_password",
                pool_size=5,
                max_overflow=10,
                pool_timeout=20.0,
                options={
                    "charset": "utf8mb4",
                    "autocommit": False
                }
            ),
            
            # MongoDB document store
            "document_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.MONGODB,
                host="localhost",
                port=27017,
                database="documents",
                username="mongo_user",
                password="mongo_password",
                options={
                    "authSource": "admin",
                    "maxPoolSize": 10,
                    "minPoolSize": 2,
                    "serverSelectionTimeoutMS": 5000
                }
            ),
            
            # SQLite cache database
            "cache_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.SQLITE,
                database="cache.db",
                options={
                    "journal_mode": "WAL",
                    "synchronous": "NORMAL",
                    "cache_size": -64000,  # 64MB cache
                    "temp_store": "MEMORY"
                }
            )
        }
    )
    
    # Create and initialize manager
    manager = DatabaseManager(config)
    
    # Add callbacks for monitoring
    manager.add_startup_callback(on_startup)
    manager.add_shutdown_callback(on_shutdown)
    manager.add_health_check_callback(on_health_check)
    manager.add_query_callback(on_query_executed)
    
    await manager.initialize()
    return manager


async def on_startup(manager: DatabaseManager):
    """Callback executed during manager startup."""
    logger.info("Database Manager started successfully")
    logger.info(f"Configured databases: {manager.list_databases()}")


async def on_shutdown(manager: DatabaseManager):
    """Callback executed during manager shutdown."""
    logger.info("Database Manager shutting down")


async def on_health_check(database_name: str, healthy: bool):
    """Callback executed after health checks."""
    status = "healthy" if healthy else "unhealthy"
    logger.info(f"Health check for {database_name}: {status}")


async def on_query_executed(database_name: str, query: str, result: Any, execution_time: float):
    """Callback executed after query execution."""
    logger.info(f"Query on {database_name} took {execution_time:.3f}s: {query[:50]}...")


async def demonstrate_basic_operations(manager: DatabaseManager):
    """Demonstrate basic database operations."""
    logger.info("\n=== Basic Database Operations ===")
    
    # PostgreSQL operations
    try:
        # Create table
        await manager.execute_query(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            database_name="main_db",
            query_type=QueryType.DDL
        )
        
        # Insert data
        result = await manager.execute_query(
            "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s) RETURNING id",
            parameters={"name": "John Doe", "email": "john@example.com"},
            database_name="main_db",
            query_type=QueryType.INSERT
        )
        logger.info(f"Inserted user with ID: {result.data}")
        
        # Query data
        users = await manager.fetch_all(
            "SELECT * FROM users WHERE name LIKE %(pattern)s",
            parameters={"pattern": "John%"},
            database_name="main_db"
        )
        logger.info(f"Found {len(users)} users: {users}")
        
    except Exception as e:
        logger.error(f"PostgreSQL operations failed: {e}")
    
    # MongoDB operations
    try:
        # Insert document
        await manager.execute_query(
            "db.products.insertOne",
            parameters={
                "name": "Laptop",
                "price": 999.99,
                "category": "Electronics",
                "created_at": datetime.utcnow()
            },
            database_name="document_db",
            query_type=QueryType.INSERT
        )
        
        # Query documents
        products = await manager.fetch_all(
            "db.products.find",
            parameters={"category": "Electronics"},
            database_name="document_db"
        )
        logger.info(f"Found {len(products)} products")
        
    except Exception as e:
        logger.error(f"MongoDB operations failed: {e}")
    
    # SQLite operations
    try:
        # Create cache table
        await manager.execute_query(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
            """,
            database_name="cache_db",
            query_type=QueryType.DDL
        )
        
        # Cache some data
        await manager.execute_query(
            "INSERT OR REPLACE INTO cache_entries (key, value, expires_at) VALUES (?, ?, ?)",
            parameters=["user:123", '{"name": "John", "role": "admin"}', 1640995200],
            database_name="cache_db",
            query_type=QueryType.INSERT
        )
        
        # Retrieve cached data
        cached = await manager.fetch_one(
            "SELECT value FROM cache_entries WHERE key = ? AND expires_at > strftime('%s', 'now')",
            parameters=["user:123"],
            database_name="cache_db"
        )
        logger.info(f"Cached data: {cached}")
        
    except Exception as e:
        logger.error(f"SQLite operations failed: {e}")


async def demonstrate_transactions(manager: DatabaseManager):
    """Demonstrate transaction management."""
    logger.info("\n=== Transaction Management ===")
    
    # Successful transaction
    try:
        async with manager.transaction("main_db", IsolationLevel.READ_COMMITTED) as conn:
            # Insert multiple related records
            await manager.execute_query(
                "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s)",
                parameters={"name": "Alice Smith", "email": "alice@example.com"},
                database_name="main_db"
            )
            
            await manager.execute_query(
                "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s)",
                parameters={"name": "Bob Johnson", "email": "bob@example.com"},
                database_name="main_db"
            )
            
            logger.info("Transaction committed successfully")
            
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
    
    # Transaction with rollback
    try:
        async with manager.transaction("main_db") as conn:
            # This will succeed
            await manager.execute_query(
                "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s)",
                parameters={"name": "Charlie Brown", "email": "charlie@example.com"},
                database_name="main_db"
            )
            
            # This will fail due to duplicate email
            await manager.execute_query(
                "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s)",
                parameters={"name": "Charlie Duplicate", "email": "charlie@example.com"},
                database_name="main_db"
            )
            
    except Exception as e:
        logger.info(f"Transaction rolled back as expected: {e}")


async def demonstrate_batch_operations(manager: DatabaseManager):
    """Demonstrate batch operations."""
    logger.info("\n=== Batch Operations ===")
    
    try:
        # Batch insert
        users_data = [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"},
            {"name": "User 3", "email": "user3@example.com"},
            {"name": "User 4", "email": "user4@example.com"},
            {"name": "User 5", "email": "user5@example.com"}
        ]
        
        result = await manager.execute_many(
            "INSERT INTO users (name, email) VALUES (%(name)s, %(email)s)",
            users_data,
            database_name="main_db",
            query_type=QueryType.INSERT
        )
        
        logger.info(f"Batch insert completed: {result.rows_affected} rows affected")
        
    except Exception as e:
        logger.error(f"Batch operations failed: {e}")


async def demonstrate_health_monitoring(manager: DatabaseManager):
    """Demonstrate health monitoring and metrics."""
    logger.info("\n=== Health Monitoring ===")
    
    # Check health of all databases
    health_status = await manager.health_check()
    for db_name, status in health_status.items():
        logger.info(f"Database {db_name}: {'Healthy' if status.get('healthy') else 'Unhealthy'}")
    
    # Get performance metrics
    metrics = manager.get_metrics()
    for db_name, db_metrics in metrics.items():
        conn_metrics = db_metrics['connection_metrics']
        logger.info(f"Database {db_name} metrics:")
        logger.info(f"  Total connections: {conn_metrics['total_connections']}")
        logger.info(f"  Active connections: {conn_metrics['active_connections']}")
        logger.info(f"  Total queries: {conn_metrics['total_queries']}")
        logger.info(f"  Average response time: {conn_metrics['avg_response_time']:.3f}s")
    
    # Get status information
    status_info = manager.get_status()
    for db_name, status in status_info.items():
        logger.info(f"Database {db_name} status:")
        logger.info(f"  Connected: {status['is_connected']}")
        logger.info(f"  Active transactions: {status['active_transactions']}")
        logger.info(f"  Total queries: {status['total_queries']}")


async def demonstrate_connection_management(manager: DatabaseManager):
    """Demonstrate connection management."""
    logger.info("\n=== Connection Management ===")
    
    # Manual connection management
    try:
        async with manager.connection("main_db") as conn:
            logger.info(f"Got connection: {conn.connection_id}")
            
            # Use connection for multiple operations
            result1 = await manager.fetch_one(
                "SELECT COUNT(*) as user_count FROM users",
                database_name="main_db"
            )
            logger.info(f"User count: {result1}")
            
            result2 = await manager.fetch_all(
                "SELECT name FROM users LIMIT 5",
                database_name="main_db"
            )
            logger.info(f"Sample users: {[user['name'] for user in result2]}")
            
    except Exception as e:
        logger.error(f"Connection management failed: {e}")


async def demonstrate_error_handling(manager: DatabaseManager):
    """Demonstrate error handling and circuit breaker."""
    logger.info("\n=== Error Handling ===")
    
    # Simulate database errors
    try:
        # Invalid SQL
        await manager.execute_query(
            "INVALID SQL STATEMENT",
            database_name="main_db"
        )
    except Exception as e:
        logger.info(f"Handled invalid SQL error: {type(e).__name__}")
    
    try:
        # Non-existent database
        await manager.execute_query(
            "SELECT 1",
            database_name="non_existent_db"
        )
    except Exception as e:
        logger.info(f"Handled non-existent database error: {type(e).__name__}")


async def main():
    """Main example function."""
    logger.info("Starting Database Manager Example")
    
    # Setup database manager
    manager = await setup_database_manager()
    
    try:
        # Run demonstrations
        await demonstrate_basic_operations(manager)
        await demonstrate_transactions(manager)
        await demonstrate_batch_operations(manager)
        await demonstrate_connection_management(manager)
        await demonstrate_health_monitoring(manager)
        await demonstrate_error_handling(manager)
        
        logger.info("\n=== Example completed successfully ===")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        
    finally:
        # Cleanup
        await manager.shutdown()
        logger.info("Database Manager shutdown completed")


if __name__ == "__main__":
    asyncio.run(main())
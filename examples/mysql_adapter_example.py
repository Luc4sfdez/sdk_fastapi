"""
MySQL Database Adapter Example.

This example demonstrates the comprehensive usage of the MySQL adapter
including enterprise features, connection management, and advanced operations.

Features demonstrated:
- Basic connection and query operations
- Transaction management with savepoints
- MySQL-specific features (stored procedures, functions)
- Bulk operations and performance optimization
- SSL/TLS configuration
- Connection pooling and health monitoring
- Replication awareness
- Error handling and graceful fallback

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi_microservices_sdk.database.config import (
    DatabaseConnectionConfig, DatabaseEngine, DatabaseCredentials,
    ConnectionPoolConfig, SSLConfig
)
from fastapi_microservices_sdk.database.adapters.mysql import MySQLAdapter
from fastapi_microservices_sdk.database.adapters.base import (
    QueryType, IsolationLevel, TransactionContext
)
from fastapi_microservices_sdk.database.exceptions import DatabaseError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MySQLAdapterExample:
    """Comprehensive MySQL adapter example."""
    
    def __init__(self):
        self.adapter: Optional[MySQLAdapter] = None
        self.connection = None
    
    def create_basic_config(self) -> DatabaseConnectionConfig:
        """Create basic MySQL configuration."""
        return DatabaseConnectionConfig(
            engine=DatabaseEngine.MYSQL,
            host="localhost",
            port=3306,
            database="test_microservices",
            credentials=DatabaseCredentials(
                username="test_user",
                password="test_password"
            ),
            pool=ConnectionPoolConfig(
                min_connections=2,
                max_connections=20,
                connection_timeout=30,
                idle_timeout=300,
                max_lifetime=3600
            )
        )
    
    def create_ssl_config(self) -> DatabaseConnectionConfig:
        """Create MySQL configuration with SSL/TLS."""
        config = self.create_basic_config()
        config.ssl = SSLConfig(
            enabled=True,
            verify_mode="CERT_REQUIRED",
            check_hostname=True,
            ca_cert_path="/path/to/ca-cert.pem",
            client_cert_path="/path/to/client-cert.pem",
            client_key_path="/path/to/client-key.pem"
        )
        return config
    
    def create_replication_config(self) -> DatabaseConnectionConfig:
        """Create MySQL configuration with replication awareness."""
        config = self.create_basic_config()
        # Add replication configuration
        config.replication = {
            'read_write_splitting': True,
            'read_hosts': ['mysql-read-1:3306', 'mysql-read-2:3306'],
            'write_hosts': ['mysql-write:3306'],
            'read_preference': 'secondary'
        }
        return config
    
    async def initialize_adapter(self, use_ssl: bool = False, use_replication: bool = False):
        """Initialize MySQL adapter with configuration."""
        try:
            if use_ssl:
                config = self.create_ssl_config()
                logger.info("Creating MySQL adapter with SSL/TLS configuration")
            elif use_replication:
                config = self.create_replication_config()
                logger.info("Creating MySQL adapter with replication configuration")
            else:
                config = self.create_basic_config()
                logger.info("Creating basic MySQL adapter configuration")
            
            self.adapter = MySQLAdapter(config)
            
            # Check availability
            if not self.adapter.is_available:
                logger.warning("MySQL adapter not available - aiomysql not installed")
                return False
            
            # Initialize adapter
            await self.adapter.initialize()
            logger.info(f"MySQL adapter initialized: {self.adapter}")
            
            # Create connection
            self.connection = await self.adapter.create_connection()
            logger.info(f"Created connection: {self.connection.connection_id}")
            
            return True
            
        except DatabaseError as e:
            logger.error(f"Failed to initialize MySQL adapter: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            return False
    
    async def demonstrate_basic_operations(self):
        """Demonstrate basic database operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Basic Operations Demo ===")
        
        try:
            # Create test table
            await self.adapter.execute_query(
                self.connection,
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    age INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON,
                    INDEX idx_email (email),
                    INDEX idx_age (age)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """,
                query_type=QueryType.DDL
            )
            logger.info("Created users table")
            
            # Insert single record
            result = await self.adapter.execute_query(
                self.connection,
                """
                INSERT INTO users (name, email, age, metadata) 
                VALUES (:name, :email, :age, :metadata)
                """,
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30,
                    "metadata": '{"role": "admin", "preferences": {"theme": "dark"}}'
                },
                query_type=QueryType.INSERT
            )
            logger.info(f"Inserted user: {result.rows_affected} rows affected")
            
            # Fetch single record
            user = await self.adapter.fetch_one(
                self.connection,
                "SELECT * FROM users WHERE email = :email",
                {"email": "john@example.com"}
            )
            logger.info(f"Fetched user: {user}")
            
            # Update record
            result = await self.adapter.execute_query(
                self.connection,
                "UPDATE users SET age = :age WHERE email = :email",
                {"age": 31, "email": "john@example.com"},
                query_type=QueryType.UPDATE
            )
            logger.info(f"Updated user: {result.rows_affected} rows affected")
            
            # Fetch multiple records
            users = await self.adapter.fetch_many(
                self.connection,
                "SELECT * FROM users WHERE age > :min_age ORDER BY created_at DESC",
                {"min_age": 25},
                size=10
            )
            logger.info(f"Fetched {len(users)} users")
            
        except DatabaseError as e:
            logger.error(f"Database operation failed: {e}")
    
    async def demonstrate_batch_operations(self):
        """Demonstrate batch operations and bulk insert."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Batch Operations Demo ===")
        
        try:
            # Batch insert using execute_many
            users_data = [
                {"name": "Alice Smith", "email": "alice@example.com", "age": 28},
                {"name": "Bob Johnson", "email": "bob@example.com", "age": 35},
                {"name": "Carol Brown", "email": "carol@example.com", "age": 42},
                {"name": "David Wilson", "email": "david@example.com", "age": 29},
                {"name": "Eve Davis", "email": "eve@example.com", "age": 33}
            ]
            
            result = await self.adapter.execute_many(
                self.connection,
                "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
                users_data
            )
            logger.info(f"Batch insert: {result.rows_affected} rows affected")
            
            # Bulk insert with MySQL-specific features
            bulk_data = [
                {"name": "Frank Miller", "email": "frank@example.com", "age": 45},
                {"name": "Grace Lee", "email": "grace@example.com", "age": 27},
                {"name": "Henry Taylor", "email": "henry@example.com", "age": 38}
            ]
            
            result = await self.adapter.bulk_insert(
                self.connection,
                "users",
                bulk_data,
                on_duplicate_key="age = VALUES(age), name = VALUES(name)"
            )
            logger.info(f"Bulk insert: {result.rows_affected} rows affected")
            
            # Verify total count
            total_users = await self.adapter.fetch_one(
                self.connection,
                "SELECT COUNT(*) as total FROM users"
            )
            logger.info(f"Total users in database: {total_users['total']}")
            
        except DatabaseError as e:
            logger.error(f"Batch operation failed: {e}")
    
    async def demonstrate_transactions(self):
        """Demonstrate transaction management with savepoints."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Transaction Management Demo ===")
        
        try:
            # Start transaction with isolation level
            async with TransactionContext(
                self.connection,
                isolation_level=IsolationLevel.READ_COMMITTED
            ) as tx:
                logger.info("Started transaction with READ COMMITTED isolation")
                
                # Insert a user
                await self.adapter.execute_query(
                    self.connection,
                    "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
                    {"name": "Transaction User", "email": "tx@example.com", "age": 25}
                )
                logger.info("Inserted user in transaction")
                
                # Create savepoint
                await tx.create_savepoint("before_update")
                logger.info("Created savepoint 'before_update'")
                
                # Update user
                await self.adapter.execute_query(
                    self.connection,
                    "UPDATE users SET age = :age WHERE email = :email",
                    {"age": 26, "email": "tx@example.com"}
                )
                logger.info("Updated user after savepoint")
                
                # Simulate error condition and rollback to savepoint
                try:
                    # This would cause an error (duplicate email)
                    await self.adapter.execute_query(
                        self.connection,
                        "INSERT INTO users (name, email, age) VALUES (:name, :email, :age)",
                        {"name": "Duplicate", "email": "tx@example.com", "age": 30}
                    )
                except DatabaseError:
                    logger.info("Caught duplicate key error, rolling back to savepoint")
                    await tx.rollback_to_savepoint("before_update")
                
                # Verify user state
                user = await self.adapter.fetch_one(
                    self.connection,
                    "SELECT * FROM users WHERE email = :email",
                    {"email": "tx@example.com"}
                )
                logger.info(f"User after rollback: age = {user['age']}")
                
                # Transaction will auto-commit when exiting context
            
            logger.info("Transaction completed successfully")
            
        except DatabaseError as e:
            logger.error(f"Transaction failed: {e}")
    
    async def demonstrate_mysql_features(self):
        """Demonstrate MySQL-specific features."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== MySQL-Specific Features Demo ===")
        
        try:
            # Create stored procedure
            await self.adapter.execute_query(
                self.connection,
                """
                CREATE PROCEDURE IF NOT EXISTS GetUsersByAge(IN min_age INT)
                BEGIN
                    SELECT * FROM users WHERE age >= min_age ORDER BY age;
                END
                """,
                query_type=QueryType.DDL
            )
            logger.info("Created stored procedure GetUsersByAge")
            
            # Execute stored procedure
            result = await self.adapter.execute_stored_procedure(
                self.connection,
                "GetUsersByAge",
                [30]
            )
            logger.info(f"Stored procedure returned {result.rows_returned} rows")
            
            # Create function
            await self.adapter.execute_query(
                self.connection,
                """
                CREATE FUNCTION IF NOT EXISTS CalculateAgeGroup(user_age INT) 
                RETURNS VARCHAR(20)
                READS SQL DATA
                DETERMINISTIC
                BEGIN
                    DECLARE age_group VARCHAR(20);
                    IF user_age < 25 THEN
                        SET age_group = 'Young';
                    ELSEIF user_age < 40 THEN
                        SET age_group = 'Adult';
                    ELSE
                        SET age_group = 'Senior';
                    END IF;
                    RETURN age_group;
                END
                """,
                query_type=QueryType.DDL
            )
            logger.info("Created function CalculateAgeGroup")
            
            # Execute function
            age_group = await self.adapter.execute_function(
                self.connection,
                "CalculateAgeGroup",
                [35]
            )
            logger.info(f"Function result for age 35: {age_group}")
            
            # Use JSON functions
            json_users = await self.adapter.fetch_all(
                self.connection,
                """
                SELECT 
                    name, 
                    email,
                    JSON_EXTRACT(metadata, '$.role') as role,
                    JSON_EXTRACT(metadata, '$.preferences.theme') as theme
                FROM users 
                WHERE metadata IS NOT NULL
                """
            )
            logger.info(f"Found {len(json_users)} users with JSON metadata")
            
        except DatabaseError as e:
            logger.error(f"MySQL feature demonstration failed: {e}")
    
    async def demonstrate_performance_monitoring(self):
        """Demonstrate performance monitoring and optimization."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Performance Monitoring Demo ===")
        
        try:
            # Get table information
            table_info = await self.adapter.get_table_info(self.connection, "users")
            logger.info(f"Users table info:")
            logger.info(f"  Engine: {table_info['engine']}")
            logger.info(f"  Rows: {table_info['rows']}")
            logger.info(f"  Data length: {table_info['data_length']} bytes")
            logger.info(f"  Index length: {table_info['index_length']} bytes")
            logger.info(f"  Collation: {table_info['collation']}")
            logger.info(f"  Columns: {len(table_info['columns'])}")
            logger.info(f"  Indexes: {len(table_info['indexes'])}")
            
            # Analyze table
            analyze_result = await self.adapter.analyze_table(self.connection, "users")
            logger.info(f"Table analysis completed: {analyze_result.rows_returned} results")
            
            # Optimize table
            optimize_result = await self.adapter.optimize_table(self.connection, "users")
            logger.info(f"Table optimization completed: {optimize_result.rows_returned} results")
            
            # Get performance metrics
            metrics = await self.adapter.get_performance_metrics(self.connection)
            logger.info("Performance metrics:")
            logger.info(f"  Buffer pool hit ratio: {metrics['derived_metrics']['buffer_pool_hit_ratio']}%")
            logger.info(f"  Lock contention ratio: {metrics['derived_metrics']['lock_contention_ratio']}%")
            logger.info(f"  Queries per second: {metrics['derived_metrics']['queries_per_second']}")
            logger.info(f"  Slow query ratio: {metrics['derived_metrics']['slow_query_ratio']}%")
            
            # Get replication status
            replication = await self.adapter.get_replication_status(self.connection)
            logger.info("Replication status:")
            logger.info(f"  Server ID: {replication['server_id']}")
            logger.info(f"  Is master: {replication['is_master']}")
            logger.info(f"  Is slave: {replication['is_slave']}")
            logger.info(f"  Replication healthy: {replication['replication_healthy']}")
            
        except DatabaseError as e:
            logger.error(f"Performance monitoring failed: {e}")
    
    async def demonstrate_health_check(self):
        """Demonstrate health check functionality."""
        if not self.adapter:
            logger.error("No adapter available")
            return
        
        logger.info("=== Health Check Demo ===")
        
        try:
            # Perform health check
            health = await self.adapter.health_check()
            
            if health['healthy']:
                logger.info("✅ Database is healthy")
                logger.info(f"  Response time: {health['response_time']:.3f}s")
                logger.info(f"  Database: {health['database_name']}")
                logger.info(f"  Version: {health['version']}")
                logger.info(f"  Size: {health['database_size_mb']} MB")
                logger.info(f"  Tables: {health['table_count']}")
                logger.info(f"  Connections: {health['connections']['current_connections']}/{health['connections']['max_connections']}")
                logger.info(f"  Pool: {health['pool_status']['used']}/{health['pool_status']['max_size']} used")
            else:
                logger.error(f"❌ Database is unhealthy: {health['error']}")
            
            # Get pool statistics
            pool_stats = await self.adapter.get_pool_stats()
            logger.info("Connection pool statistics:")
            logger.info(f"  Size: {pool_stats['size']}")
            logger.info(f"  Used: {pool_stats['used']}")
            logger.info(f"  Free: {pool_stats['free']}")
            logger.info(f"  Min/Max: {pool_stats['min_size']}/{pool_stats['max_size']}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.connection:
                # Clean up test data
                await self.adapter.execute_query(
                    self.connection,
                    "DROP TABLE IF EXISTS users",
                    query_type=QueryType.DDL
                )
                logger.info("Cleaned up test table")
                
                # Drop procedures and functions
                await self.adapter.execute_query(
                    self.connection,
                    "DROP PROCEDURE IF EXISTS GetUsersByAge",
                    query_type=QueryType.DDL
                )
                await self.adapter.execute_query(
                    self.connection,
                    "DROP FUNCTION IF EXISTS CalculateAgeGroup",
                    query_type=QueryType.DDL
                )
                logger.info("Cleaned up stored procedures and functions")
                
                # Close connection
                await self.connection.close()
                logger.info("Connection closed")
            
            if self.adapter:
                await self.adapter.shutdown()
                logger.info("Adapter shutdown completed")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main example execution."""
    example = MySQLAdapterExample()
    
    try:
        # Initialize adapter (try different configurations)
        logger.info("🚀 Starting MySQL Adapter Example")
        
        # Try basic configuration first
        if not await example.initialize_adapter(use_ssl=False, use_replication=False):
            logger.warning("Failed to initialize with basic config, trying graceful fallback...")
            return
        
        # Run demonstrations
        await example.demonstrate_basic_operations()
        await example.demonstrate_batch_operations()
        await example.demonstrate_transactions()
        await example.demonstrate_mysql_features()
        await example.demonstrate_performance_monitoring()
        await example.demonstrate_health_check()
        
        logger.info("✅ All demonstrations completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Example execution failed: {e}")
    
    finally:
        # Always cleanup
        await example.cleanup()
        logger.info("🏁 MySQL Adapter Example completed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
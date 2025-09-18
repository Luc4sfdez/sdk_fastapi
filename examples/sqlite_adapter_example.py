"""
SQLite Database Adapter Example.

This example demonstrates the comprehensive usage of the SQLite adapter
including enterprise features, connection management, and advanced operations.

Features demonstrated:
- Basic SQL operations (CRUD)
- Transaction management with savepoints
- SQLite-specific features (FTS, JSON1, R-Tree)
- Database backup and restore operations
- Performance optimization (VACUUM, ANALYZE)
- File-based and in-memory databases
- Error handling and graceful fallback

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import json

from fastapi_microservices_sdk.database.config import (
    DatabaseConnectionConfig, DatabaseEngine, DatabaseCredentials,
    ConnectionPoolConfig
)
from fastapi_microservices_sdk.database.adapters.sqlite import SQLiteAdapter
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


class SQLiteAdapterExample:
    """Comprehensive SQLite adapter example."""
    
    def __init__(self):
        self.adapter: Optional[SQLiteAdapter] = None
        self.connection = None
        self.temp_dir = None
    
    def create_memory_config(self) -> DatabaseConnectionConfig:
        """Create in-memory SQLite configuration."""
        return DatabaseConnectionConfig(
            engine=DatabaseEngine.SQLITE,
            host="localhost",  # Not used for SQLite
            port=0,  # Not used for SQLite
            database=":memory:",
            credentials=DatabaseCredentials(
                username="",  # Not used for SQLite
                password=""   # Not used for SQLite
            ),
            pool=ConnectionPoolConfig(
                min_connections=1,
                max_connections=5,  # SQLite doesn't need many connections
                connection_timeout=30,
                idle_timeout=300,
                max_lifetime=3600
            )
        )
    
    def create_file_config(self, db_path: str) -> DatabaseConnectionConfig:
        """Create file-based SQLite configuration."""
        config = self.create_memory_config()
        config.database = db_path
        return config
    
    async def initialize_adapter(self, use_file: bool = False):
        """Initialize SQLite adapter with configuration."""
        try:
            if use_file:
                # Create temporary directory for file database
                self.temp_dir = tempfile.mkdtemp()
                db_path = Path(self.temp_dir) / "example.db"
                config = self.create_file_config(str(db_path))
                logger.info(f"Creating SQLite adapter with file database: {db_path}")
            else:
                config = self.create_memory_config()
                logger.info("Creating SQLite adapter with in-memory database")
            
            self.adapter = SQLiteAdapter(config)
            
            # Check availability
            if not self.adapter.is_available:
                logger.warning("SQLite adapter not available - aiosqlite not installed")
                return False
            
            # Initialize adapter
            await self.adapter.initialize()
            logger.info(f"SQLite adapter initialized: {self.adapter}")
            
            # Create connection
            self.connection = await self.adapter.create_connection()
            logger.info(f"Created connection: {self.connection.connection_id}")
            
            return True
            
        except DatabaseError as e:
            logger.error(f"Failed to initialize SQLite adapter: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            return False
    
    async def demonstrate_basic_operations(self):
        """Demonstrate basic SQL operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Basic SQL Operations Demo ===")
        
        try:
            # Create test table with various data types
            await self.adapter.execute_query(
                self.connection,
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    age INTEGER,
                    salary REAL,
                    active BOOLEAN DEFAULT 1,
                    metadata TEXT,  -- JSON data
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """,
                query_type=QueryType.DDL
            )
            logger.info("Created users table")
            
            # Create index for performance
            await self.adapter.execute_query(
                self.connection,
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
                query_type=QueryType.DDL
            )
            logger.info("Created index on email column")
            
            # Insert single record
            result = await self.adapter.execute_query(
                self.connection,
                """
                INSERT INTO users (name, email, age, salary, metadata) 
                VALUES (:name, :email, :age, :salary, :metadata)
                """,
                {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30,
                    "salary": 75000.50,
                    "metadata": json.dumps({
                        "role": "developer",
                        "skills": ["Python", "SQLite", "FastAPI"],
                        "preferences": {"theme": "dark"}
                    })
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
            
            # Parse JSON metadata
            if user and user['metadata']:
                metadata = json.loads(user['metadata'])
                logger.info(f"User metadata: {metadata}")
            
            # Update record
            result = await self.adapter.execute_query(
                self.connection,
                "UPDATE users SET age = :age, salary = :salary WHERE email = :email",
                {"age": 31, "salary": 80000.00, "email": "john@example.com"},
                query_type=QueryType.UPDATE
            )
            logger.info(f"Updated user: {result.rows_affected} rows affected")
            
            # Fetch multiple records with conditions
            users = await self.adapter.fetch_many(
                self.connection,
                """
                SELECT id, name, email, age, salary, active 
                FROM users 
                WHERE age > :min_age AND active = :active 
                ORDER BY salary DESC
                """,
                {"min_age": 25, "active": True},
                size=10
            )
            logger.info(f"Fetched {len(users)} active users")
            
        except DatabaseError as e:
            logger.error(f"SQL operation failed: {e}")
    
    async def demonstrate_batch_operations(self):
        """Demonstrate batch operations and bulk operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Batch Operations Demo ===")
        
        try:
            # Batch insert using execute_many
            users_data = [
                {"name": "Alice Smith", "email": "alice@example.com", "age": 28, "salary": 65000.00},
                {"name": "Bob Johnson", "email": "bob@example.com", "age": 35, "salary": 85000.00},
                {"name": "Carol Brown", "email": "carol@example.com", "age": 42, "salary": 95000.00},
                {"name": "David Wilson", "email": "david@example.com", "age": 29, "salary": 70000.00},
                {"name": "Eve Davis", "email": "eve@example.com", "age": 33, "salary": 78000.00}
            ]
            
            result = await self.adapter.execute_many(
                self.connection,
                "INSERT INTO users (name, email, age, salary) VALUES (:name, :email, :age, :salary)",
                users_data
            )
            logger.info(f"Batch insert: {result.rows_affected} rows affected")
            
            # Batch update with different conditions
            update_data = [
                {"bonus": 5000.00, "email": "alice@example.com"},
                {"bonus": 7000.00, "email": "bob@example.com"},
                {"bonus": 8000.00, "email": "carol@example.com"}
            ]
            
            # Add bonus column first
            await self.adapter.execute_query(
                self.connection,
                "ALTER TABLE users ADD COLUMN bonus REAL DEFAULT 0",
                query_type=QueryType.DDL
            )
            
            result = await self.adapter.execute_many(
                self.connection,
                "UPDATE users SET bonus = :bonus WHERE email = :email",
                update_data
            )
            logger.info(f"Batch update: {result.rows_affected} rows affected")
            
            # Verify total count and statistics
            stats = await self.adapter.fetch_one(
                self.connection,
                """
                SELECT 
                    COUNT(*) as total_users,
                    AVG(age) as avg_age,
                    AVG(salary) as avg_salary,
                    SUM(bonus) as total_bonus
                FROM users
                """
            )
            logger.info(f"Database statistics: {stats}")
            
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
                isolation_level=IsolationLevel.SERIALIZABLE
            ) as tx:
                logger.info("Started transaction with SERIALIZABLE isolation")
                
                # Insert a user
                await self.adapter.execute_query(
                    self.connection,
                    "INSERT INTO users (name, email, age, salary) VALUES (:name, :email, :age, :salary)",
                    {"name": "Transaction User", "email": "tx@example.com", "age": 25, "salary": 60000.00}
                )
                logger.info("Inserted user in transaction")
                
                # Create savepoint
                await tx.create_savepoint("before_update")
                logger.info("Created savepoint 'before_update'")
                
                # Update user
                await self.adapter.execute_query(
                    self.connection,
                    "UPDATE users SET age = :age, salary = :salary WHERE email = :email",
                    {"age": 26, "salary": 65000.00, "email": "tx@example.com"}
                )
                logger.info("Updated user after savepoint")
                
                # Create another savepoint
                await tx.create_savepoint("before_bonus")
                logger.info("Created savepoint 'before_bonus'")
                
                # Add bonus
                await self.adapter.execute_query(
                    self.connection,
                    "UPDATE users SET bonus = :bonus WHERE email = :email",
                    {"bonus": 3000.00, "email": "tx@example.com"}
                )
                logger.info("Added bonus after second savepoint")
                
                # Simulate error condition and rollback to first savepoint
                try:
                    # This would cause an error (duplicate email)
                    await self.adapter.execute_query(
                        self.connection,
                        "INSERT INTO users (name, email, age, salary) VALUES (:name, :email, :age, :salary)",
                        {"name": "Duplicate", "email": "tx@example.com", "age": 30, "salary": 70000.00}
                    )
                except DatabaseError:
                    logger.info("Caught duplicate key error, rolling back to first savepoint")
                    await tx.rollback_to_savepoint("before_update")
                
                # Verify user state
                user = await self.adapter.fetch_one(
                    self.connection,
                    "SELECT * FROM users WHERE email = :email",
                    {"email": "tx@example.com"}
                )
                logger.info(f"User after rollback: age = {user['age'] if user else 'Not found'}")
                
                # Transaction will auto-commit when exiting context
            
            logger.info("Transaction completed successfully")
            
        except DatabaseError as e:
            logger.error(f"Transaction failed: {e}")
    
    async def demonstrate_sqlite_features(self):
        """Demonstrate SQLite-specific features."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== SQLite-Specific Features Demo ===")
        
        try:
            # JSON operations (if JSON1 extension is available)
            if 'json1' in self.adapter._extensions_loaded:
                logger.info("JSON1 extension is available")
                
                # Query JSON data
                json_users = await self.adapter.fetch_all(
                    self.connection,
                    """
                    SELECT 
                        name, 
                        email,
                        json_extract(metadata, '$.role') as role,
                        json_extract(metadata, '$.skills') as skills
                    FROM users 
                    WHERE json_extract(metadata, '$.role') = 'developer'
                    """
                )
                logger.info(f"Found {len(json_users)} developers using JSON queries")
                
                # Update JSON data
                await self.adapter.execute_query(
                    self.connection,
                    """
                    UPDATE users 
                    SET metadata = json_set(metadata, '$.last_login', datetime('now'))
                    WHERE email = :email
                    """,
                    {"email": "john@example.com"}
                )
                logger.info("Updated JSON metadata with last_login timestamp")
            
            # Full-Text Search (if FTS5 extension is available)
            if 'fts5' in self.adapter._extensions_loaded:
                logger.info("FTS5 extension is available")
                
                # Create FTS table
                await self.adapter.create_fts_table(
                    self.connection,
                    "users_fts",
                    ["name", "email"]
                )
                logger.info("Created FTS5 table for full-text search")
                
                # Populate FTS table
                await self.adapter.execute_query(
                    self.connection,
                    """
                    INSERT INTO users_fts (name, email)
                    SELECT name, email FROM users
                    """
                )
                
                # Perform FTS search
                search_results = await self.adapter.fts_search(
                    self.connection,
                    "users_fts",
                    "john OR alice",
                    limit=10
                )
                logger.info(f"FTS search results: {len(search_results)} matches")
            
            # Common Table Expressions (CTE)
            cte_results = await self.adapter.fetch_all(
                self.connection,
                """
                WITH salary_stats AS (
                    SELECT 
                        AVG(salary) as avg_salary,
                        MAX(salary) as max_salary,
                        MIN(salary) as min_salary
                    FROM users
                )
                SELECT 
                    u.name,
                    u.salary,
                    CASE 
                        WHEN u.salary > s.avg_salary THEN 'Above Average'
                        WHEN u.salary = s.avg_salary THEN 'Average'
                        ELSE 'Below Average'
                    END as salary_category
                FROM users u
                CROSS JOIN salary_stats s
                ORDER BY u.salary DESC
                """
            )
            logger.info(f"CTE query results: {len(cte_results)} users categorized by salary")
            
            # Window functions
            window_results = await self.adapter.fetch_all(
                self.connection,
                """
                SELECT 
                    name,
                    salary,
                    ROW_NUMBER() OVER (ORDER BY salary DESC) as salary_rank,
                    NTILE(3) OVER (ORDER BY salary) as salary_tercile,
                    LAG(salary) OVER (ORDER BY salary) as prev_salary
                FROM users
                ORDER BY salary DESC
                """
            )
            logger.info(f"Window functions results: {len(window_results)} users with rankings")
            
        except DatabaseError as e:
            logger.error(f"SQLite feature demonstration failed: {e}")
    
    async def demonstrate_performance_optimization(self):
        """Demonstrate performance optimization and maintenance."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Performance Optimization Demo ===")
        
        try:
            # Get table information
            table_info = await self.adapter.get_table_info(self.connection, "users")
            logger.info(f"Users table info:")
            logger.info(f"  Columns: {len(table_info['columns'])}")
            logger.info(f"  Indexes: {len(table_info['indexes'])}")
            logger.info(f"  Foreign keys: {len(table_info['foreign_keys'])}")
            logger.info(f"  Row count: {table_info['row_count']}")
            
            for col in table_info['columns']:
                logger.info(f"    Column: {col['name']} ({col['type']}) - PK: {bool(col['pk'])}")
            
            for idx in table_info['indexes']:
                logger.info(f"    Index: {idx['name']} - Unique: {idx['unique']}")
            
            # Explain query performance
            explain_result = await self.adapter.explain_query(
                self.connection,
                "SELECT * FROM users WHERE email = :email ORDER BY salary DESC",
                {"email": "john@example.com"}
            )
            
            logger.info("Query execution plan:")
            for step in explain_result['execution_plan']:
                logger.info(f"  {step}")
            
            # Analyze database for optimization
            analyze_result = await self.adapter.analyze_database(self.connection)
            logger.info(f"Database analysis completed in {analyze_result['execution_time']:.3f}s")
            
            # Get comprehensive database statistics
            db_stats = await self.adapter.get_database_stats(self.connection)
            logger.info("Database statistics:")
            logger.info(f"  Page count: {db_stats.get('page_count', 0)}")
            logger.info(f"  Page size: {db_stats.get('page_size', 0)} bytes")
            logger.info(f"  Database size: {db_stats.get('database_size_mb', 0):.2f} MB")
            logger.info(f"  Free space: {db_stats.get('free_space_mb', 0):.2f} MB")
            logger.info(f"  Journal mode: {db_stats.get('journal_mode', 'unknown')}")
            logger.info(f"  Cache size: {db_stats.get('cache_size', 0)}")
            
            if 'object_counts' in db_stats:
                for obj_type, count in db_stats['object_counts'].items():
                    logger.info(f"  {obj_type.title()}s: {count}")
            
            # Vacuum database to reclaim space
            vacuum_result = await self.adapter.vacuum_database(self.connection)
            logger.info(f"Database vacuum completed in {vacuum_result['execution_time']:.3f}s")
            
        except DatabaseError as e:
            logger.error(f"Performance optimization failed: {e}")
    
    async def demonstrate_backup_restore(self):
        """Demonstrate backup and restore operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        # Only works with file databases
        if self.adapter._database_path == ":memory:":
            logger.info("=== Backup/Restore Demo (Skipped - In-Memory Database) ===")
            return
        
        logger.info("=== Backup and Restore Demo ===")
        
        try:
            # Create backup
            backup_path = Path(self.temp_dir) / "backup.db"
            
            backup_result = await self.adapter.backup_database(
                self.connection,
                str(backup_path)
            )
            logger.info(f"Database backup created:")
            logger.info(f"  Path: {backup_result['backup_path']}")
            logger.info(f"  Size: {backup_result['backup_size_bytes']} bytes")
            logger.info(f"  Time: {backup_result['execution_time']:.3f}s")
            
            # Verify backup file exists
            if backup_path.exists():
                logger.info(f"Backup file verified: {backup_path.stat().st_size} bytes")
            
            # Demonstrate restore (create a new connection to restore to)
            restore_path = Path(self.temp_dir) / "restored.db"
            restore_config = self.create_file_config(str(restore_path))
            
            # Create new adapter for restore target
            restore_adapter = SQLiteAdapter(restore_config)
            await restore_adapter.initialize()
            restore_connection = await restore_adapter.create_connection()
            
            # Restore from backup
            restore_result = await restore_adapter.restore_database(
                restore_connection,
                str(backup_path)
            )
            logger.info(f"Database restored in {restore_result['execution_time']:.3f}s")
            
            # Verify restored data
            restored_users = await restore_adapter.fetch_all(
                restore_connection,
                "SELECT COUNT(*) as count FROM users"
            )
            logger.info(f"Restored database contains {restored_users[0]['count']} users")
            
            # Cleanup restore connection
            await restore_connection.close()
            await restore_adapter.shutdown()
            
        except DatabaseError as e:
            logger.error(f"Backup/restore operation failed: {e}")
    
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
                logger.info(f"  Database path: {health['database_path']}")
                logger.info(f"  SQLite version: {health['sqlite_version']}")
                logger.info(f"  Integrity check: {health['integrity_check']}")
                logger.info(f"  Journal mode: {health['journal_mode']}")
                logger.info(f"  File size: {health['file_size_bytes']} bytes")
                logger.info(f"  Estimated size: {health['estimated_size_mb']:.2f} MB")
                logger.info(f"  Tables: {health['table_count']}")
                logger.info(f"  Indexes: {health['index_count']}")
                logger.info(f"  Extensions: {health['extensions_loaded']}")
            else:
                logger.error(f"❌ Database is unhealthy: {health['error']}")
            
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
                
                # Drop FTS table if it exists
                try:
                    await self.adapter.execute_query(
                        self.connection,
                        "DROP TABLE IF EXISTS users_fts",
                        query_type=QueryType.DDL
                    )
                    logger.info("Cleaned up FTS table")
                except:
                    pass  # FTS table might not exist
                
                # Close connection
                await self.connection.close()
                logger.info("Connection closed")
            
            if self.adapter:
                await self.adapter.shutdown()
                logger.info("Adapter shutdown completed")
            
            # Clean up temporary directory
            if self.temp_dir:
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info("Temporary directory cleaned up")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main example execution."""
    example = SQLiteAdapterExample()
    
    try:
        # Initialize adapter (try both in-memory and file-based)
        logger.info("🚀 Starting SQLite Adapter Example")
        
        # Try in-memory database first
        logger.info("\n--- In-Memory Database Example ---")
        if await example.initialize_adapter(use_file=False):
            await example.demonstrate_basic_operations()
            await example.demonstrate_batch_operations()
            await example.demonstrate_transactions()
            await example.demonstrate_sqlite_features()
            await example.demonstrate_performance_optimization()
            await example.demonstrate_health_check()
            await example.cleanup()
        
        # Try file-based database
        logger.info("\n--- File-Based Database Example ---")
        if await example.initialize_adapter(use_file=True):
            await example.demonstrate_basic_operations()
            await example.demonstrate_batch_operations()
            await example.demonstrate_backup_restore()
            await example.demonstrate_health_check()
            await example.cleanup()
        
        logger.info("✅ All demonstrations completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Example execution failed: {e}")
    
    finally:
        # Always cleanup
        await example.cleanup()
        logger.info("🏁 SQLite Adapter Example completed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
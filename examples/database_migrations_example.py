"""
Database Migration System Example for FastAPI Microservices SDK.

This example demonstrates how to use the migration system to manage
database schema changes across different database engines with
enterprise-grade features.

Features demonstrated:
- Migration creation and execution
- Multi-database migration management
- Rollback capabilities
- Migration validation and safety checks
- History tracking and status monitoring
- Dry-run capabilities
- Backup and restore integration

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
import tempfile

from fastapi_microservices_sdk.database import (
    DatabaseManager,
    DatabaseConfig,
    DatabaseConnectionConfig,
    DatabaseEngine
)
from fastapi_microservices_sdk.database.migrations import (
    MigrationManager,
    MigrationConfig,
    MigrationMode,
    BackupStrategy,
    SQLMigration,
    MigrationMetadata
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database_manager() -> DatabaseManager:
    """Setup database manager with multiple databases."""
    
    config = DatabaseConfig(
        default_database="main_db",
        databases={
            # PostgreSQL database
            "main_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.POSTGRESQL,
                host="localhost",
                port=5432,
                database="migration_demo",
                username="postgres",
                password="password"
            ),
            
            # MySQL database
            "analytics_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.MYSQL,
                host="localhost",
                port=3306,
                database="analytics_demo",
                username="mysql_user",
                password="mysql_password"
            ),
            
            # SQLite database
            "cache_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.SQLITE,
                database="cache_demo.db"
            )
        }
    )
    
    manager = DatabaseManager(config)
    await manager.initialize()
    return manager


def create_sample_migrations(migrations_dir: Path):
    """Create sample migration files for demonstration."""
    
    # PostgreSQL migrations
    pg_dir = migrations_dir / "main_db"
    pg_dir.mkdir(parents=True, exist_ok=True)
    
    # Migration 001: Create users table
    (pg_dir / "001_create_users_table.sql").write_text("""
-- Description: Create users table with basic fields
-- Author: Migration Demo
-- Tags: users, initial

-- UP
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- DOWN
DROP INDEX IF EXISTS idx_users_active;
DROP INDEX IF EXISTS idx_users_email;
DROP INDEX IF EXISTS idx_users_username;
DROP TABLE IF EXISTS users;
""")
    
    # Migration 002: Create posts table
    (pg_dir / "002_create_posts_table.sql").write_text("""
-- Description: Create posts table with foreign key to users
-- Author: Migration Demo
-- Depends: 001
-- Tags: posts, content

-- UP
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    status VARCHAR(20) DEFAULT 'draft',
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_published_at ON posts(published_at);

-- DOWN
DROP INDEX IF EXISTS idx_posts_published_at;
DROP INDEX IF EXISTS idx_posts_status;
DROP INDEX IF EXISTS idx_posts_user_id;
DROP TABLE IF EXISTS posts;
""")
    
    # Migration 003: Add profile fields to users
    (pg_dir / "003_add_user_profile_fields.sql").write_text("""
-- Description: Add profile fields to users table
-- Author: Migration Demo
-- Depends: 001
-- Tags: users, profile

-- UP
ALTER TABLE users 
ADD COLUMN first_name VARCHAR(50),
ADD COLUMN last_name VARCHAR(50),
ADD COLUMN bio TEXT,
ADD COLUMN avatar_url VARCHAR(500),
ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';

CREATE INDEX idx_users_name ON users(first_name, last_name);

-- DOWN
DROP INDEX IF EXISTS idx_users_name;
ALTER TABLE users 
DROP COLUMN IF EXISTS timezone,
DROP COLUMN IF EXISTS avatar_url,
DROP COLUMN IF EXISTS bio,
DROP COLUMN IF EXISTS last_name,
DROP COLUMN IF EXISTS first_name;
""")
    
    # MySQL migrations
    mysql_dir = migrations_dir / "analytics_db"
    mysql_dir.mkdir(parents=True, exist_ok=True)
    
    (mysql_dir / "001_create_events_table.sql").write_text("""
-- Description: Create events table for analytics
-- Author: Migration Demo
-- Tags: analytics, events

-- UP
CREATE TABLE events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_events_user_id (user_id),
    INDEX idx_events_type (event_type),
    INDEX idx_events_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DOWN
DROP TABLE IF EXISTS events;
""")
    
    # SQLite migrations
    sqlite_dir = migrations_dir / "cache_db"
    sqlite_dir.mkdir(parents=True, exist_ok=True)
    
    (sqlite_dir / "001_create_cache_table.sql").write_text("""
-- Description: Create cache table for key-value storage
-- Author: Migration Demo
-- Tags: cache, storage

-- UP
CREATE TABLE cache_entries (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX idx_cache_expires_at ON cache_entries(expires_at);
CREATE INDEX idx_cache_created_at ON cache_entries(created_at);

-- DOWN
DROP INDEX IF EXISTS idx_cache_created_at;
DROP INDEX IF EXISTS idx_cache_expires_at;
DROP TABLE IF EXISTS cache_entries;
""")


async def demonstrate_migration_status(migration_manager: MigrationManager):
    """Demonstrate migration status checking."""
    logger.info("\n=== Migration Status ===")
    
    # Get status for all databases
    status = await migration_manager.get_migration_status()
    
    for db_name, db_status in status.items():
        logger.info(f"\nDatabase: {db_name}")
        logger.info(f"  Total migrations: {db_status['total_migrations']}")
        logger.info(f"  Executed migrations: {db_status['executed_migrations']}")
        logger.info(f"  Pending migrations: {db_status['pending_migrations']}")
        
        if db_status['last_migration']:
            last = db_status['last_migration']
            logger.info(f"  Last migration: {last['version']} - {last['name']}")
            logger.info(f"  Executed at: {last['executed_at']}")
        
        if db_status['pending_list']:
            logger.info("  Pending migrations:")
            for pending in db_status['pending_list']:
                logger.info(f"    {pending['version']} - {pending['name']}: {pending['description']}")


async def demonstrate_dry_run(migration_manager: MigrationManager):
    """Demonstrate dry-run migration execution."""
    logger.info("\n=== Dry Run Migration ===")
    
    # Perform dry run for all databases
    results = await migration_manager.migrate(dry_run=True)
    
    for result in results:
        if result.get('status') == 'dry_run':
            logger.info(f"Dry run for {result['database']} - {result['migration_id']}")
            details = result.get('details', {})
            logger.info(f"  Would execute: {details.get('would_execute')}")
            logger.info(f"  Estimated duration: {details.get('estimated_duration')}s")
            logger.info(f"  Affected objects: {details.get('affected_objects')}")


async def demonstrate_migration_execution(migration_manager: MigrationManager):
    """Demonstrate actual migration execution."""
    logger.info("\n=== Migration Execution ===")
    
    # Execute migrations for all databases
    results = await migration_manager.migrate()
    
    for result in results:
        db_name = result['database']
        status = result['status']
        
        if status == 'completed':
            migration_id = result['migration_id']
            duration = result.get('duration', 0)
            affected = result.get('affected_objects', [])
            
            logger.info(f"✅ {db_name} - {migration_id}")
            logger.info(f"   Duration: {duration:.3f}s")
            logger.info(f"   Affected objects: {len(affected)}")
            
        elif status == 'failed':
            migration_id = result.get('migration_id', 'unknown')
            error = result.get('error', 'Unknown error')
            
            logger.error(f"❌ {db_name} - {migration_id}")
            logger.error(f"   Error: {error}")
        
        else:
            logger.info(f"ℹ️  {db_name} - {status}")


async def demonstrate_specific_database_migration(migration_manager: MigrationManager):
    """Demonstrate migration of specific database."""
    logger.info("\n=== Specific Database Migration ===")
    
    # Migrate only the main database
    results = await migration_manager.migrate(database_name="main_db")
    
    logger.info(f"Migrated main_db with {len(results)} operations")
    for result in results:
        logger.info(f"  {result['status']}: {result.get('migration_id', 'N/A')}")


async def demonstrate_target_version_migration(migration_manager: MigrationManager):
    """Demonstrate migration to specific version."""
    logger.info("\n=== Target Version Migration ===")
    
    # Migrate to specific version
    results = await migration_manager.migrate(
        database_name="main_db",
        target_version="002"
    )
    
    logger.info(f"Migrated main_db to version 002 with {len(results)} operations")


async def demonstrate_rollback(migration_manager: MigrationManager):
    """Demonstrate migration rollback."""
    logger.info("\n=== Migration Rollback ===")
    
    try:
        # Rollback last migration
        results = await migration_manager.rollback("main_db", steps=1)
        
        for result in results:
            status = result['status']
            migration_id = result.get('migration_id', 'unknown')
            
            if status == 'rolled_back':
                duration = result.get('duration', 0)
                logger.info(f"✅ Rolled back {migration_id} in {duration:.3f}s")
            elif status == 'rollback_failed':
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Rollback failed for {migration_id}: {error}")
    
    except Exception as e:
        logger.error(f"Rollback demonstration failed: {e}")


async def demonstrate_programmatic_migration():
    """Demonstrate creating migrations programmatically."""
    logger.info("\n=== Programmatic Migration ===")
    
    # Create migration programmatically
    metadata = MigrationMetadata(
        version="999",
        name="programmatic_test",
        description="Test migration created programmatically",
        author="Demo Script"
    )
    
    up_sql = """
    CREATE TABLE temp_test (
        id SERIAL PRIMARY KEY,
        test_data VARCHAR(100)
    );
    """
    
    down_sql = """
    DROP TABLE IF EXISTS temp_test;
    """
    
    migration = SQLMigration(metadata, up_sql, down_sql)
    
    logger.info(f"Created migration: {migration.id}")
    logger.info(f"Checksum: {migration.checksum}")
    logger.info(f"Dependencies: {migration.get_dependencies()}")


async def demonstrate_migration_validation(migration_manager: MigrationManager):
    """Demonstrate migration validation."""
    logger.info("\n=== Migration Validation ===")
    
    # Create an invalid migration for demonstration
    metadata = MigrationMetadata(
        version="",  # Invalid empty version
        name="invalid-name",  # Invalid name with hyphen
        description=""  # Empty description
    )
    
    # Destructive operation without permission
    destructive_sql = "DROP TABLE users;"
    
    invalid_migration = SQLMigration(metadata, destructive_sql, "")
    
    try:
        # This should fail validation
        adapter = migration_manager.database_manager.get_adapter("main_db")
        await migration_manager.validator.validate_migration(invalid_migration, adapter)
        logger.info("Migration validation passed (unexpected)")
    except Exception as e:
        logger.info(f"Migration validation failed as expected: {e}")


async def demonstrate_migration_history(migration_manager: MigrationManager):
    """Demonstrate migration history tracking."""
    logger.info("\n=== Migration History ===")
    
    # Get migration history for main database
    adapter = migration_manager.database_manager.get_adapter("main_db")
    history_entries = await migration_manager.history.get_migration_history(adapter, limit=10)
    
    logger.info(f"Found {len(history_entries)} history entries:")
    
    for entry in history_entries:
        status_icon = "✅" if entry.success else "❌"
        logger.info(f"  {status_icon} {entry.version} - {entry.name}")
        logger.info(f"     Executed: {entry.executed_at}")
        logger.info(f"     Duration: {entry.execution_time:.3f}s")
        logger.info(f"     Direction: {entry.direction}")
        
        if entry.error_message:
            logger.info(f"     Error: {entry.error_message}")


async def main():
    """Main demonstration function."""
    logger.info("Starting Database Migration System Example")
    
    # Create temporary directory for migrations
    with tempfile.TemporaryDirectory() as temp_dir:
        migrations_dir = Path(temp_dir) / "migrations"
        
        # Setup migration configuration
        migration_config = MigrationConfig(
            migrations_dir=migrations_dir,
            migration_table_name="schema_migrations",
            mode=MigrationMode.MANUAL,
            validate_checksums=True,
            strict_mode=True,
            backup_strategy=BackupStrategy.BEFORE_MIGRATION,
            allow_destructive_migrations=False,
            max_retries=3,
            migration_timeout=300.0
        )
        
        # Create sample migration files
        create_sample_migrations(migrations_dir)
        logger.info(f"Created sample migrations in: {migrations_dir}")
        
        # Setup database manager
        try:
            database_manager = await setup_database_manager()
            logger.info("Database manager initialized")
            
            # Setup migration manager
            migration_manager = MigrationManager(migration_config, database_manager)
            await migration_manager.initialize()
            logger.info("Migration manager initialized")
            
            # Run demonstrations
            await demonstrate_migration_status(migration_manager)
            await demonstrate_dry_run(migration_manager)
            await demonstrate_migration_execution(migration_manager)
            await demonstrate_migration_history(migration_manager)
            await demonstrate_specific_database_migration(migration_manager)
            await demonstrate_rollback(migration_manager)
            await demonstrate_programmatic_migration()
            await demonstrate_migration_validation(migration_manager)
            
            logger.info("\n=== Example completed successfully ===")
            
        except Exception as e:
            logger.error(f"Example failed: {e}")
            
        finally:
            # Cleanup
            try:
                await database_manager.shutdown()
                logger.info("Database manager shutdown completed")
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
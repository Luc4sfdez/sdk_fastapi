"""
Migration manager for the database migration system.

This module provides the central MigrationManager class that orchestrates
all migration operations across different database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timezone
import importlib.util
import re
from contextlib import asynccontextmanager

from ..adapters.base import DatabaseAdapter
from ..config import DatabaseEngine
from ..manager import DatabaseManager
from .base import Migration, MigrationDirection, MigrationStatus, SQLMigration, MigrationMetadata
from .config import MigrationConfig, MigrationMode, BackupStrategy
from .history import MigrationHistory
from .validator import MigrationValidator
from .exceptions import (
    MigrationError, MigrationValidationError, MigrationConflictError,
    MigrationExecutionError, MigrationDependencyError, MigrationLockError
)

# Integration with communication logging
try:
    from ...communication.logging import CommunicationLogger
    COMMUNICATION_LOGGING_AVAILABLE = True
except ImportError:
    COMMUNICATION_LOGGING_AVAILABLE = False
    CommunicationLogger = None


class MigrationLock:
    """Migration execution lock to prevent concurrent migrations."""
    
    def __init__(self, adapter: DatabaseAdapter, config: MigrationConfig):
        self.adapter = adapter
        self.config = config
        self.lock_id = "migration_lock"
        self.acquired = False
    
    async def acquire(self) -> bool:
        """Acquire migration lock."""
        try:
            # Implementation depends on database engine
            engine = self.adapter.config.engine
            
            if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL]:
                # Use advisory locks
                result = await self.adapter.fetch_one(
                    None,
                    "SELECT pg_try_advisory_lock(12345) as acquired" if engine == DatabaseEngine.POSTGRESQL
                    else "SELECT GET_LOCK('migration_lock', 0) as acquired"
                )
                self.acquired = bool(result['acquired'])
                
            elif engine == DatabaseEngine.SQLITE:
                # SQLite doesn't support advisory locks, use table-based locking
                try:
                    await self.adapter.execute_query(
                        None,
                        "CREATE TABLE IF NOT EXISTS migration_lock (id INTEGER PRIMARY KEY, acquired_at TEXT)"
                    )
                    await self.adapter.execute_query(
                        None,
                        "INSERT INTO migration_lock (id, acquired_at) VALUES (1, ?)",
                        [datetime.now(timezone.utc).isoformat()]
                    )
                    self.acquired = True
                except Exception:
                    self.acquired = False
                    
            elif engine == DatabaseEngine.MONGODB:
                # Use MongoDB's findAndModify for atomic lock
                result = await self.adapter.execute_query(
                    None,
                    "db.migration_lock.findOneAndUpdate",
                    parameters={
                        "filter": {"_id": "migration_lock"},
                        "update": {"$set": {"acquired_at": datetime.now(timezone.utc)}},
                        "options": {"upsert": True, "returnDocument": "after"}
                    }
                )
                self.acquired = True
            
            return self.acquired
            
        except Exception as e:
            raise MigrationLockError(f"Failed to acquire migration lock: {e}", original_error=e)
    
    async def release(self) -> None:
        """Release migration lock."""
        if not self.acquired:
            return
        
        try:
            engine = self.adapter.config.engine
            
            if engine == DatabaseEngine.POSTGRESQL:
                await self.adapter.execute_query(None, "SELECT pg_advisory_unlock(12345)")
            elif engine == DatabaseEngine.MYSQL:
                await self.adapter.execute_query(None, "SELECT RELEASE_LOCK('migration_lock')")
            elif engine == DatabaseEngine.SQLITE:
                await self.adapter.execute_query(None, "DELETE FROM migration_lock WHERE id = 1")
            elif engine == DatabaseEngine.MONGODB:
                await self.adapter.execute_query(
                    None,
                    "db.migration_lock.deleteOne",
                    parameters={"_id": "migration_lock"}
                )
            
            self.acquired = False
            
        except Exception as e:
            # Log error but don't raise - we don't want to prevent cleanup
            if COMMUNICATION_LOGGING_AVAILABLE:
                logger = CommunicationLogger("migration.lock")
                logger.error(f"Failed to release migration lock: {e}")


class MigrationManager:
    """
    Central migration management orchestrator.
    
    Manages database schema migrations across all supported database engines
    with enterprise-grade features like validation, rollback, and monitoring.
    """
    
    def __init__(self, config: MigrationConfig, database_manager: DatabaseManager):
        self.config = config
        self.database_manager = database_manager
        self.history = MigrationHistory(config)
        self.validator = MigrationValidator(config)
        
        # Logging setup
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("migration.manager")
        else:
            self.logger = logging.getLogger(__name__)
        
        # Migration cache
        self._migrations_cache: Dict[str, Dict[str, Migration]] = {}
        self._cache_loaded = False
        
        self.logger.info("MigrationManager initialized")
    
    async def initialize(self) -> None:
        """Initialize migration manager."""
        try:
            # Load migrations from filesystem
            await self._load_migrations()
            
            # Initialize history for all databases
            for db_name in self.database_manager.list_databases():
                adapter = self.database_manager.get_adapter(db_name)
                await self.history.initialize(adapter)
            
            self.logger.info("MigrationManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MigrationManager: {e}")
            raise MigrationError(f"MigrationManager initialization failed: {e}", original_error=e)
    
    async def _load_migrations(self) -> None:
        """Load migrations from filesystem."""
        if self._cache_loaded:
            return
        
        migrations_dir = self.config.migrations_dir
        if not migrations_dir.exists():
            self.logger.warning(f"Migrations directory does not exist: {migrations_dir}")
            return
        
        # Load migrations for each database
        for db_name in self.database_manager.list_databases():
            adapter = self.database_manager.get_adapter(db_name)
            engine = adapter.config.engine
            
            db_migrations_dir = migrations_dir / db_name
            if not db_migrations_dir.exists():
                self.logger.info(f"No migrations directory for database: {db_name}")
                continue
            
            migrations = await self._load_database_migrations(db_migrations_dir, engine)
            self._migrations_cache[db_name] = migrations
            
            self.logger.info(f"Loaded {len(migrations)} migrations for database: {db_name}")
        
        self._cache_loaded = True
    
    async def _load_database_migrations(self, migrations_dir: Path, engine: DatabaseEngine) -> Dict[str, Migration]:
        """Load migrations for a specific database."""
        migrations = {}
        file_pattern = self.config.get_migration_file_pattern(engine)
        
        # Find migration files
        migration_files = list(migrations_dir.glob(file_pattern))
        migration_files.sort()  # Ensure consistent ordering
        
        for file_path in migration_files:
            try:
                migration = await self._load_migration_file(file_path, engine)
                if migration:
                    migrations[migration.id] = migration
                    
            except Exception as e:
                self.logger.error(f"Failed to load migration file {file_path}: {e}")
                raise MigrationError(f"Failed to load migration: {file_path}", original_error=e)
        
        return migrations
    
    async def _load_migration_file(self, file_path: Path, engine: DatabaseEngine) -> Optional[Migration]:
        """Load a single migration file."""
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            return await self._load_sql_migration(file_path)
        elif engine == DatabaseEngine.MONGODB:
            return await self._load_python_migration(file_path)
        else:
            raise MigrationError(f"Unsupported database engine: {engine}")
    
    async def _load_sql_migration(self, file_path: Path) -> Optional[SQLMigration]:
        """Load SQL migration from file."""
        content = file_path.read_text(encoding='utf-8')
        
        # Parse migration metadata from comments
        metadata = self._parse_sql_metadata(content, file_path.stem)
        
        # Split up and down sections
        up_sql, down_sql = self._split_sql_migration(content)
        
        if not up_sql:
            self.logger.warning(f"No UP section found in migration: {file_path}")
            return None
        
        return SQLMigration(metadata, up_sql, down_sql)
    
    def _parse_sql_metadata(self, content: str, filename: str) -> MigrationMetadata:
        """Parse metadata from SQL migration comments."""
        # Extract version from filename (e.g., "001_create_users_table.sql")
        version_match = re.match(r'^(\d+)_(.+)$', filename)
        if not version_match:
            raise MigrationValidationError(f"Invalid migration filename format: {filename}")
        
        version = version_match.group(1)
        name = version_match.group(2).replace('.sql', '')
        
        # Parse metadata from comments
        description = ""
        author = None
        dependencies = []
        tags = []
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-- Description:'):
                description = line[15:].strip()
            elif line.startswith('-- Author:'):
                author = line[10:].strip()
            elif line.startswith('-- Depends:'):
                deps = line[11:].strip()
                dependencies = [d.strip() for d in deps.split(',') if d.strip()]
            elif line.startswith('-- Tags:'):
                tag_str = line[8:].strip()
                tags = [t.strip() for t in tag_str.split(',') if t.strip()]
        
        return MigrationMetadata(
            version=version,
            name=name,
            description=description or f"Migration {version}",
            author=author,
            dependencies=dependencies,
            tags=tags
        )
    
    def _split_sql_migration(self, content: str) -> Tuple[str, str]:
        """Split SQL migration into UP and DOWN sections."""
        lines = content.split('\n')
        up_lines = []
        down_lines = []
        current_section = None
        
        for line in lines:
            line_upper = line.strip().upper()
            
            if line_upper.startswith('-- UP') or line_upper.startswith('-- +MIGRATE UP'):
                current_section = 'up'
                continue
            elif line_upper.startswith('-- DOWN') or line_upper.startswith('-- +MIGRATE DOWN'):
                current_section = 'down'
                continue
            
            if current_section == 'up':
                up_lines.append(line)
            elif current_section == 'down':
                down_lines.append(line)
            elif current_section is None and not line.strip().startswith('--'):
                # If no sections defined, assume everything is UP
                up_lines.append(line)
        
        return '\n'.join(up_lines).strip(), '\n'.join(down_lines).strip()
    
    async def _load_python_migration(self, file_path: Path) -> Optional[Migration]:
        """Load Python migration from file (for MongoDB)."""
        # Load Python module dynamically
        spec = importlib.util.spec_from_file_location("migration", file_path)
        if not spec or not spec.loader:
            raise MigrationError(f"Cannot load migration module: {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for Migration class in module
        if hasattr(module, 'Migration'):
            migration_class = getattr(module, 'Migration')
            if issubclass(migration_class, Migration):
                return migration_class()
        
        raise MigrationError(f"No valid Migration class found in: {file_path}")
    
    async def migrate(
        self,
        database_name: Optional[str] = None,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute migrations.
        
        Args:
            database_name: Target database (all if None)
            target_version: Target migration version (latest if None)
            dry_run: Perform dry run without executing
            
        Returns:
            List of migration results
        """
        if not self._cache_loaded:
            await self._load_migrations()
        
        databases = [database_name] if database_name else self.database_manager.list_databases()
        results = []
        
        for db_name in databases:
            try:
                db_results = await self._migrate_database(db_name, target_version, dry_run)
                results.extend(db_results)
                
            except Exception as e:
                self.logger.error(f"Migration failed for database {db_name}: {e}")
                results.append({
                    'database': db_name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    async def _migrate_database(
        self,
        database_name: str,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """Migrate a specific database."""
        adapter = self.database_manager.get_adapter(database_name)
        migrations = self._migrations_cache.get(database_name, {})
        
        if not migrations:
            self.logger.info(f"No migrations found for database: {database_name}")
            return []
        
        # Get executed migrations
        executed_migrations = await self.history.get_executed_migrations(adapter)
        
        # Determine migrations to execute
        pending_migrations = self._get_pending_migrations(
            migrations, executed_migrations, target_version
        )
        
        if not pending_migrations:
            self.logger.info(f"No pending migrations for database: {database_name}")
            return []
        
        # Validate migration dependencies
        await self._validate_migration_dependencies(pending_migrations, executed_migrations)
        
        results = []
        
        if dry_run:
            # Perform dry run
            for migration in pending_migrations:
                dry_run_result = await migration.dry_run(adapter, MigrationDirection.UP)
                results.append({
                    'database': database_name,
                    'migration_id': migration.id,
                    'status': 'dry_run',
                    'details': dry_run_result
                })
        else:
            # Execute migrations with lock
            async with self._migration_lock(adapter):
                for migration in pending_migrations:
                    result = await self._execute_migration(adapter, migration, database_name)
                    results.append(result)
        
        return results
    
    def _get_pending_migrations(
        self,
        migrations: Dict[str, Migration],
        executed_migrations: Set[str],
        target_version: Optional[str] = None
    ) -> List[Migration]:
        """Get list of pending migrations to execute."""
        pending = []
        
        for migration_id, migration in migrations.items():
            version = migration.metadata.version
            
            # Skip if already executed
            if version in executed_migrations:
                continue
            
            # Skip if beyond target version
            if target_version and version > target_version:
                continue
            
            pending.append(migration)
        
        # Sort by version
        pending.sort(key=lambda m: m.metadata.version)
        return pending
    
    async def _validate_migration_dependencies(
        self,
        migrations: List[Migration],
        executed_migrations: Set[str]
    ) -> None:
        """Validate migration dependencies."""
        for migration in migrations:
            for dep_version in migration.metadata.dependencies:
                if dep_version not in executed_migrations:
                    # Check if dependency is in current batch
                    dep_in_batch = any(
                        m.metadata.version == dep_version for m in migrations
                    )
                    if not dep_in_batch:
                        raise MigrationDependencyError(
                            f"Migration {migration.id} depends on {dep_version} which is not executed",
                            migration_id=migration.id,
                            missing_dependencies=[dep_version]
                        )
    
    @asynccontextmanager
    async def _migration_lock(self, adapter: DatabaseAdapter):
        """Context manager for migration lock."""
        lock = MigrationLock(adapter, self.config)
        
        try:
            acquired = await lock.acquire()
            if not acquired:
                raise MigrationLockError("Could not acquire migration lock")
            
            yield lock
            
        finally:
            await lock.release()
    
    async def _execute_migration(
        self,
        adapter: DatabaseAdapter,
        migration: Migration,
        database_name: str
    ) -> Dict[str, Any]:
        """Execute a single migration."""
        self.logger.info(f"Executing migration {migration.id} on database {database_name}")
        
        try:
            # Validate migration
            if self.config.validate_checksums:
                await self.validator.validate_migration(migration, adapter)
            
            # Create backup if configured
            if self.config.backup_strategy != BackupStrategy.NONE:
                await self._create_backup(adapter, migration.id)
            
            # Execute migration
            result = await migration.up(adapter)
            
            # Record in history
            await self.history.record_migration(
                adapter,
                result,
                migration.metadata.name,
                migration.metadata.description,
                migration.checksum
            )
            
            self.logger.info(f"Migration {migration.id} completed successfully")
            
            return {
                'database': database_name,
                'migration_id': migration.id,
                'status': 'completed',
                'duration': result.duration,
                'affected_objects': result.affected_objects
            }
            
        except Exception as e:
            self.logger.error(f"Migration {migration.id} failed: {e}")
            
            # Attempt rollback if configured
            if hasattr(migration, 'down'):
                try:
                    await migration.down(adapter)
                    self.logger.info(f"Migration {migration.id} rolled back successfully")
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed for {migration.id}: {rollback_error}")
            
            return {
                'database': database_name,
                'migration_id': migration.id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _create_backup(self, adapter: DatabaseAdapter, migration_id: str) -> None:
        """Create backup before migration."""
        if not self.config.backup_dir:
            return
        
        try:
            backup_path = self.config.backup_dir / f"backup_{migration_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Use adapter's backup functionality if available
            if hasattr(adapter, 'create_backup'):
                await adapter.create_backup(str(backup_path))
                self.logger.info(f"Backup created: {backup_path}")
            
        except Exception as e:
            self.logger.warning(f"Backup creation failed: {e}")
            # Don't fail migration for backup errors unless strict mode
            if self.config.strict_mode:
                raise
    
    async def rollback(
        self,
        database_name: str,
        target_version: Optional[str] = None,
        steps: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rollback migrations.
        
        Args:
            database_name: Target database
            target_version: Rollback to this version
            steps: Number of migrations to rollback
            
        Returns:
            List of rollback results
        """
        adapter = self.database_manager.get_adapter(database_name)
        migrations = self._migrations_cache.get(database_name, {})
        
        # Get migration history
        history = await self.history.get_migration_history(adapter)
        
        # Determine migrations to rollback
        rollback_migrations = self._get_rollback_migrations(
            migrations, history, target_version, steps
        )
        
        if not rollback_migrations:
            self.logger.info(f"No migrations to rollback for database: {database_name}")
            return []
        
        results = []
        
        async with self._migration_lock(adapter):
            for migration in rollback_migrations:
                result = await self._rollback_migration(adapter, migration, database_name)
                results.append(result)
        
        return results
    
    def _get_rollback_migrations(
        self,
        migrations: Dict[str, Migration],
        history: List,
        target_version: Optional[str] = None,
        steps: Optional[int] = None
    ) -> List[Migration]:
        """Get list of migrations to rollback."""
        rollback_list = []
        
        # Filter successful migrations from history
        successful_history = [h for h in history if h.success and h.direction == 'up']
        
        if steps:
            # Rollback specific number of steps
            for entry in successful_history[:steps]:
                migration = migrations.get(f"{entry.version}_{entry.name}")
                if migration:
                    rollback_list.append(migration)
        elif target_version:
            # Rollback to specific version
            for entry in successful_history:
                if entry.version <= target_version:
                    break
                migration = migrations.get(f"{entry.version}_{entry.name}")
                if migration:
                    rollback_list.append(migration)
        
        return rollback_list
    
    async def _rollback_migration(
        self,
        adapter: DatabaseAdapter,
        migration: Migration,
        database_name: str
    ) -> Dict[str, Any]:
        """Rollback a single migration."""
        self.logger.info(f"Rolling back migration {migration.id} on database {database_name}")
        
        try:
            # Execute rollback
            result = await migration.down(adapter)
            
            # Remove from history
            await self.history.remove_migration_record(adapter, migration.metadata.version)
            
            self.logger.info(f"Migration {migration.id} rolled back successfully")
            
            return {
                'database': database_name,
                'migration_id': migration.id,
                'status': 'rolled_back',
                'duration': result.duration
            }
            
        except Exception as e:
            self.logger.error(f"Rollback failed for {migration.id}: {e}")
            
            return {
                'database': database_name,
                'migration_id': migration.id,
                'status': 'rollback_failed',
                'error': str(e)
            }
    
    async def get_migration_status(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get migration status for database(s).
        
        Args:
            database_name: Target database (all if None)
            
        Returns:
            Migration status information
        """
        if not self._cache_loaded:
            await self._load_migrations()
        
        databases = [database_name] if database_name else self.database_manager.list_databases()
        status = {}
        
        for db_name in databases:
            adapter = self.database_manager.get_adapter(db_name)
            migrations = self._migrations_cache.get(db_name, {})
            executed_migrations = await self.history.get_executed_migrations(adapter)
            
            total_migrations = len(migrations)
            executed_count = len(executed_migrations)
            pending_migrations = [
                m for m in migrations.values()
                if m.metadata.version not in executed_migrations
            ]
            
            last_migration = await self.history.get_last_migration(adapter)
            
            status[db_name] = {
                'total_migrations': total_migrations,
                'executed_migrations': executed_count,
                'pending_migrations': len(pending_migrations),
                'last_migration': {
                    'version': last_migration.version,
                    'name': last_migration.name,
                    'executed_at': last_migration.executed_at.isoformat()
                } if last_migration else None,
                'pending_list': [
                    {
                        'version': m.metadata.version,
                        'name': m.metadata.name,
                        'description': m.metadata.description
                    }
                    for m in sorted(pending_migrations, key=lambda x: x.metadata.version)
                ]
            }
        
        return status
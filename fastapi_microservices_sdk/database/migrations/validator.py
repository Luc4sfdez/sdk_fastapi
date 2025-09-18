"""
Migration validator for the database migration system.

This module provides validation functionality for migrations,
ensuring they are safe and follow best practices.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import re
from typing import List, Dict, Any, Set, Optional
from pathlib import Path

from ..adapters.base import DatabaseAdapter
from ..config import DatabaseEngine
from .base import Migration, SQLMigration
from .config import MigrationConfig
from .exceptions import MigrationValidationError


class MigrationValidator:
    """
    Validates migrations for safety and best practices.
    
    Provides comprehensive validation including syntax checking,
    destructive operation detection, and dependency validation.
    """
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        
        # Destructive SQL operations
        self.destructive_operations = {
            'DROP TABLE', 'DROP DATABASE', 'DROP SCHEMA', 'DROP VIEW',
            'DROP INDEX', 'DROP COLUMN', 'DROP CONSTRAINT',
            'DELETE', 'TRUNCATE', 'ALTER TABLE DROP'
        }
        
        # Risky SQL operations that need careful review
        self.risky_operations = {
            'ALTER TABLE', 'CREATE INDEX', 'DROP INDEX',
            'UPDATE', 'INSERT', 'RENAME'
        }
    
    async def validate_migration(self, migration: Migration, adapter: DatabaseAdapter) -> None:
        """
        Validate a migration before execution.
        
        Args:
            migration: Migration to validate
            adapter: Database adapter for context
            
        Raises:
            MigrationValidationError: If validation fails
        """
        errors = []
        
        # Basic metadata validation
        errors.extend(self._validate_metadata(migration))
        
        # Content validation based on migration type
        if isinstance(migration, SQLMigration):
            errors.extend(await self._validate_sql_migration(migration, adapter))
        
        # Checksum validation
        if self.config.validate_checksums:
            errors.extend(self._validate_checksum(migration))
        
        if errors:
            raise MigrationValidationError(
                f"Migration validation failed: {'; '.join(errors)}",
                migration_id=migration.id,
                validation_errors=errors
            )
    
    def _validate_metadata(self, migration: Migration) -> List[str]:
        """Validate migration metadata."""
        errors = []
        
        metadata = migration.metadata
        
        # Version validation
        if not metadata.version:
            errors.append("Migration version is required")
        elif not re.match(r'^\d+$', metadata.version):
            errors.append("Migration version must be numeric")
        
        # Name validation
        if not metadata.name:
            errors.append("Migration name is required")
        elif not re.match(r'^[a-zA-Z0-9_]+$', metadata.name):
            errors.append("Migration name must contain only alphanumeric characters and underscores")
        
        # Description validation
        if not metadata.description:
            errors.append("Migration description is required")
        
        # Dependencies validation
        for dep in metadata.dependencies:
            if not re.match(r'^\d+$', dep):
                errors.append(f"Invalid dependency version format: {dep}")
        
        return errors
    
    async def _validate_sql_migration(self, migration: SQLMigration, adapter: DatabaseAdapter) -> List[str]:
        """Validate SQL migration content."""
        errors = []
        
        # Validate UP SQL
        if not migration.up_sql.strip():
            errors.append("UP SQL is required")
        else:
            errors.extend(self._validate_sql_content(migration.up_sql, "UP", adapter.config.engine))
        
        # Validate DOWN SQL (optional but recommended)
        if migration.down_sql.strip():
            errors.extend(self._validate_sql_content(migration.down_sql, "DOWN", adapter.config.engine))
        elif self.config.strict_mode:
            errors.append("DOWN SQL is required in strict mode")
        
        # Cross-validation between UP and DOWN
        if migration.up_sql.strip() and migration.down_sql.strip():
            errors.extend(self._validate_sql_consistency(migration.up_sql, migration.down_sql))
        
        return errors
    
    def _validate_sql_content(self, sql: str, section: str, engine: DatabaseEngine) -> List[str]:
        """Validate SQL content for safety and best practices."""
        errors = []
        
        # Normalize SQL for analysis
        sql_upper = sql.upper().strip()
        
        # Check for destructive operations
        destructive_ops = self._find_destructive_operations(sql_upper)
        if destructive_ops and not self.config.allow_destructive_migrations:
            errors.append(f"{section} SQL contains destructive operations: {', '.join(destructive_ops)}")
        
        # Check for risky operations
        risky_ops = self._find_risky_operations(sql_upper)
        if risky_ops and self.config.strict_mode:
            errors.append(f"{section} SQL contains risky operations that need review: {', '.join(risky_ops)}")
        
        # Engine-specific validation
        errors.extend(self._validate_engine_specific_sql(sql, engine))
        
        # Syntax validation (basic)
        errors.extend(self._validate_sql_syntax(sql))
        
        return errors
    
    def _find_destructive_operations(self, sql: str) -> Set[str]:
        """Find destructive operations in SQL."""
        found_ops = set()
        
        for op in self.destructive_operations:
            if op in sql:
                found_ops.add(op)
        
        return found_ops
    
    def _find_risky_operations(self, sql: str) -> Set[str]:
        """Find risky operations in SQL."""
        found_ops = set()
        
        for op in self.risky_operations:
            if op in sql:
                found_ops.add(op)
        
        return found_ops
    
    def _validate_engine_specific_sql(self, sql: str, engine: DatabaseEngine) -> List[str]:
        """Validate engine-specific SQL features."""
        errors = []
        
        if engine == DatabaseEngine.POSTGRESQL:
            errors.extend(self._validate_postgresql_sql(sql))
        elif engine == DatabaseEngine.MYSQL:
            errors.extend(self._validate_mysql_sql(sql))
        elif engine == DatabaseEngine.SQLITE:
            errors.extend(self._validate_sqlite_sql(sql))
        
        return errors
    
    def _validate_postgresql_sql(self, sql: str) -> List[str]:
        """Validate PostgreSQL-specific SQL."""
        errors = []
        
        # Check for PostgreSQL-specific features
        if 'SERIAL' in sql.upper() and 'PRIMARY KEY' not in sql.upper():
            errors.append("SERIAL columns should typically be PRIMARY KEY")
        
        # Check for proper use of schemas
        if 'CREATE TABLE' in sql.upper() and '.' not in sql:
            # Could warn about not specifying schema, but it's optional
            pass
        
        return errors
    
    def _validate_mysql_sql(self, sql: str) -> List[str]:
        """Validate MySQL-specific SQL."""
        errors = []
        
        # Check for MySQL-specific features
        if 'AUTO_INCREMENT' in sql.upper() and 'PRIMARY KEY' not in sql.upper():
            errors.append("AUTO_INCREMENT columns should typically be PRIMARY KEY")
        
        # Check for storage engine specification
        if 'CREATE TABLE' in sql.upper() and 'ENGINE=' not in sql.upper():
            # Could warn about not specifying engine, but it's optional
            pass
        
        return errors
    
    def _validate_sqlite_sql(self, sql: str) -> List[str]:
        """Validate SQLite-specific SQL."""
        errors = []
        
        # SQLite limitations
        if 'ALTER TABLE' in sql.upper() and 'DROP COLUMN' in sql.upper():
            errors.append("SQLite does not support DROP COLUMN in ALTER TABLE")
        
        if 'ALTER TABLE' in sql.upper() and 'ADD CONSTRAINT' in sql.upper():
            errors.append("SQLite has limited support for ADD CONSTRAINT")
        
        return errors
    
    def _validate_sql_syntax(self, sql: str) -> List[str]:
        """Basic SQL syntax validation."""
        errors = []
        
        # Check for balanced parentheses
        paren_count = sql.count('(') - sql.count(')')
        if paren_count != 0:
            errors.append("Unbalanced parentheses in SQL")
        
        # Check for balanced quotes
        single_quote_count = sql.count("'") - sql.count("\\'")
        if single_quote_count % 2 != 0:
            errors.append("Unbalanced single quotes in SQL")
        
        double_quote_count = sql.count('"') - sql.count('\\"')
        if double_quote_count % 2 != 0:
            errors.append("Unbalanced double quotes in SQL")
        
        # Check for common syntax errors
        if sql.strip().endswith(','):
            errors.append("SQL ends with comma")
        
        return errors
    
    def _validate_sql_consistency(self, up_sql: str, down_sql: str) -> List[str]:
        """Validate consistency between UP and DOWN SQL."""
        errors = []
        
        up_upper = up_sql.upper()
        down_upper = down_sql.upper()
        
        # Check CREATE TABLE vs DROP TABLE consistency
        up_creates = re.findall(r'CREATE TABLE\s+(\w+)', up_upper)
        down_drops = re.findall(r'DROP TABLE\s+(\w+)', down_upper)
        
        for table in up_creates:
            if table not in down_drops:
                errors.append(f"Table {table} created in UP but not dropped in DOWN")
        
        # Check ADD COLUMN vs DROP COLUMN consistency
        up_adds = re.findall(r'ADD COLUMN\s+(\w+)', up_upper)
        down_drops_cols = re.findall(r'DROP COLUMN\s+(\w+)', down_upper)
        
        for column in up_adds:
            if column not in down_drops_cols:
                errors.append(f"Column {column} added in UP but not dropped in DOWN")
        
        return errors
    
    def _validate_checksum(self, migration: Migration) -> List[str]:
        """Validate migration checksum."""
        errors = []
        
        try:
            # Calculate current checksum
            current_checksum = migration.checksum
            
            # If metadata has a stored checksum, compare
            if migration.metadata.checksum and migration.metadata.checksum != current_checksum:
                errors.append(f"Checksum mismatch: expected {migration.metadata.checksum}, got {current_checksum}")
        
        except Exception as e:
            errors.append(f"Failed to validate checksum: {e}")
        
        return errors
    
    def validate_migration_dependencies(
        self,
        migrations: Dict[str, Migration],
        target_migrations: List[Migration]
    ) -> List[str]:
        """
        Validate migration dependencies.
        
        Args:
            migrations: All available migrations
            target_migrations: Migrations to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Build dependency graph
        migration_versions = {m.metadata.version: m for m in migrations.values()}
        
        for migration in target_migrations:
            # Check if all dependencies exist
            for dep_version in migration.metadata.dependencies:
                if dep_version not in migration_versions:
                    errors.append(f"Migration {migration.id} depends on non-existent migration {dep_version}")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(target_migrations)
        if circular_deps:
            errors.append(f"Circular dependencies detected: {' -> '.join(circular_deps)}")
        
        return errors
    
    def _detect_circular_dependencies(self, migrations: List[Migration]) -> Optional[List[str]]:
        """Detect circular dependencies in migrations."""
        # Build adjacency list
        graph = {}
        for migration in migrations:
            version = migration.metadata.version
            graph[version] = migration.metadata.dependencies
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
            if node in rec_stack:
                # Found cycle, return the cycle path
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                cycle = has_cycle(neighbor, path.copy())
                if cycle:
                    return cycle
            
            rec_stack.remove(node)
            return None
        
        for migration in migrations:
            version = migration.metadata.version
            if version not in visited:
                cycle = has_cycle(version, [])
                if cycle:
                    return cycle
        
        return None
    
    def validate_migration_file_structure(self, migrations_dir: Path) -> List[str]:
        """
        Validate migration file structure and naming.
        
        Args:
            migrations_dir: Directory containing migrations
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not migrations_dir.exists():
            errors.append(f"Migrations directory does not exist: {migrations_dir}")
            return errors
        
        # Check file naming convention
        migration_files = list(migrations_dir.glob("*.sql")) + list(migrations_dir.glob("*.py"))
        
        versions_seen = set()
        
        for file_path in migration_files:
            filename = file_path.stem
            
            # Check naming convention
            if not re.match(r'^\d+_[a-zA-Z0-9_]+$', filename):
                errors.append(f"Invalid migration filename: {file_path.name}")
                continue
            
            # Extract version
            version = filename.split('_')[0]
            
            # Check for duplicate versions
            if version in versions_seen:
                errors.append(f"Duplicate migration version: {version}")
            else:
                versions_seen.add(version)
        
        return errors
"""
Migration configuration for the database migration system.

This module provides configuration classes for managing migration settings
and behavior across different database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..config import DatabaseEngine


class MigrationMode(Enum):
    """Migration execution mode."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    DRY_RUN = "dry_run"


class BackupStrategy(Enum):
    """Backup strategy before migrations."""
    NONE = "none"
    BEFORE_MIGRATION = "before_migration"
    BEFORE_EACH_MIGRATION = "before_each_migration"
    FULL_BACKUP = "full_backup"


class MigrationConfig(BaseModel):
    """Configuration for database migrations."""
    
    # Migration directories
    migrations_dir: Path = Field(
        default=Path("migrations"),
        description="Directory containing migration files"
    )
    
    # Migration table/collection settings
    migration_table_name: str = Field(
        default="schema_migrations",
        description="Name of the table/collection to store migration history"
    )
    
    # Execution settings
    mode: MigrationMode = Field(
        default=MigrationMode.MANUAL,
        description="Migration execution mode"
    )
    
    auto_create_migration_table: bool = Field(
        default=True,
        description="Automatically create migration history table if it doesn't exist"
    )
    
    validate_checksums: bool = Field(
        default=True,
        description="Validate migration checksums before execution"
    )
    
    # Backup settings
    backup_strategy: BackupStrategy = Field(
        default=BackupStrategy.BEFORE_MIGRATION,
        description="Backup strategy before migrations"
    )
    
    backup_dir: Optional[Path] = Field(
        default=None,
        description="Directory to store backups"
    )
    
    # Timeout settings
    migration_timeout: float = Field(
        default=300.0,
        description="Timeout for individual migration execution (seconds)"
    )
    
    lock_timeout: float = Field(
        default=60.0,
        description="Timeout for acquiring migration lock (seconds)"
    )
    
    # Retry settings
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed migrations"
    )
    
    retry_delay: float = Field(
        default=5.0,
        description="Delay between retries (seconds)"
    )
    
    # Validation settings
    strict_mode: bool = Field(
        default=True,
        description="Enable strict validation of migrations"
    )
    
    allow_destructive_migrations: bool = Field(
        default=False,
        description="Allow migrations that may cause data loss"
    )
    
    # Engine-specific settings
    engine_settings: Dict[DatabaseEngine, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Engine-specific migration settings"
    )
    
    # Notification settings
    notify_on_success: bool = Field(
        default=False,
        description="Send notifications on successful migrations"
    )
    
    notify_on_failure: bool = Field(
        default=True,
        description="Send notifications on failed migrations"
    )
    
    notification_webhooks: List[str] = Field(
        default_factory=list,
        description="Webhook URLs for notifications"
    )
    
    @validator('migrations_dir')
    def validate_migrations_dir(cls, v):
        """Validate migrations directory."""
        if isinstance(v, str):
            v = Path(v)
        return v
    
    @validator('backup_dir')
    def validate_backup_dir(cls, v):
        """Validate backup directory."""
        if v is not None and isinstance(v, str):
            v = Path(v)
        return v
    
    @validator('migration_timeout', 'lock_timeout', 'retry_delay')
    def validate_positive_float(cls, v):
        """Validate positive float values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @validator('max_retries')
    def validate_max_retries(cls, v):
        """Validate max retries."""
        if v < 0:
            raise ValueError("Max retries must be non-negative")
        return v
    
    def get_engine_setting(self, engine: DatabaseEngine, key: str, default: Any = None) -> Any:
        """
        Get engine-specific setting.
        
        Args:
            engine: Database engine
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        return self.engine_settings.get(engine, {}).get(key, default)
    
    def set_engine_setting(self, engine: DatabaseEngine, key: str, value: Any) -> None:
        """
        Set engine-specific setting.
        
        Args:
            engine: Database engine
            key: Setting key
            value: Setting value
        """
        if engine not in self.engine_settings:
            self.engine_settings[engine] = {}
        self.engine_settings[engine][key] = value
    
    def get_migration_file_pattern(self, engine: DatabaseEngine) -> str:
        """
        Get migration file pattern for specific engine.
        
        Args:
            engine: Database engine
            
        Returns:
            File pattern for migrations
        """
        patterns = {
            DatabaseEngine.POSTGRESQL: "*.sql",
            DatabaseEngine.MYSQL: "*.sql",
            DatabaseEngine.SQLITE: "*.sql",
            DatabaseEngine.MONGODB: "*.py"
        }
        
        return self.get_engine_setting(
            engine, 
            'file_pattern', 
            patterns.get(engine, "*.sql")
        )
    
    def get_migration_table_schema(self, engine: DatabaseEngine) -> Dict[str, Any]:
        """
        Get migration table schema for specific engine.
        
        Args:
            engine: Database engine
            
        Returns:
            Schema definition for migration table
        """
        sql_schema = {
            'columns': [
                {'name': 'version', 'type': 'VARCHAR(255)', 'primary_key': True},
                {'name': 'name', 'type': 'VARCHAR(255)', 'nullable': False},
                {'name': 'description', 'type': 'TEXT'},
                {'name': 'checksum', 'type': 'VARCHAR(64)', 'nullable': False},
                {'name': 'executed_at', 'type': 'TIMESTAMP', 'nullable': False},
                {'name': 'execution_time', 'type': 'FLOAT'},
                {'name': 'success', 'type': 'BOOLEAN', 'nullable': False}
            ],
            'indexes': [
                {'name': 'idx_executed_at', 'columns': ['executed_at']},
                {'name': 'idx_success', 'columns': ['success']}
            ]
        }
        
        mongodb_schema = {
            'collection': self.migration_table_name,
            'indexes': [
                {'key': [('version', 1)], 'unique': True},
                {'key': [('executed_at', -1)]},
                {'key': [('success', 1)]}
            ]
        }
        
        schemas = {
            DatabaseEngine.POSTGRESQL: sql_schema,
            DatabaseEngine.MYSQL: sql_schema,
            DatabaseEngine.SQLITE: sql_schema,
            DatabaseEngine.MONGODB: mongodb_schema
        }
        
        return self.get_engine_setting(
            engine,
            'table_schema',
            schemas.get(engine, sql_schema)
        )
    
    def is_destructive_operation_allowed(self, operation: str) -> bool:
        """
        Check if destructive operation is allowed.
        
        Args:
            operation: Operation name (e.g., 'DROP TABLE', 'DELETE')
            
        Returns:
            True if operation is allowed
        """
        if self.allow_destructive_migrations:
            return True
        
        destructive_operations = {
            'DROP TABLE', 'DROP DATABASE', 'DROP SCHEMA',
            'DELETE', 'TRUNCATE', 'DROP INDEX', 'DROP COLUMN'
        }
        
        return operation.upper() not in destructive_operations
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
"""
Migration-specific exceptions for the database migration system.

This module defines custom exceptions for migration operations,
providing detailed error information and context.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, List, Dict, Any
from ..exceptions import DatabaseError


class MigrationError(DatabaseError):
    """Base exception for migration-related errors."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        migration_version: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error=original_error, context=context)
        self.migration_id = migration_id
        self.migration_version = migration_version


class MigrationValidationError(MigrationError):
    """Exception raised when migration validation fails."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.validation_errors = validation_errors or []


class MigrationConflictError(MigrationError):
    """Exception raised when migration conflicts are detected."""
    
    def __init__(
        self,
        message: str,
        conflicting_migrations: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.conflicting_migrations = conflicting_migrations or []


class MigrationExecutionError(MigrationError):
    """Exception raised during migration execution."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        execution_stage: Optional[str] = None,
        rollback_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.execution_stage = execution_stage
        self.rollback_info = rollback_info


class MigrationRollbackError(MigrationError):
    """Exception raised during migration rollback."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        rollback_stage: Optional[str] = None,
        partial_rollback: bool = False,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.rollback_stage = rollback_stage
        self.partial_rollback = partial_rollback


class MigrationLockError(MigrationError):
    """Exception raised when migration lock cannot be acquired."""
    
    def __init__(
        self,
        message: str,
        lock_holder: Optional[str] = None,
        lock_acquired_at: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.lock_holder = lock_holder
        self.lock_acquired_at = lock_acquired_at


class MigrationChecksumError(MigrationError):
    """Exception raised when migration checksum validation fails."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        expected_checksum: Optional[str] = None,
        actual_checksum: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.expected_checksum = expected_checksum
        self.actual_checksum = actual_checksum


class MigrationDependencyError(MigrationError):
    """Exception raised when migration dependencies are not satisfied."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        missing_dependencies: Optional[List[str]] = None,
        circular_dependencies: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.missing_dependencies = missing_dependencies or []
        self.circular_dependencies = circular_dependencies or []


class MigrationTimeoutError(MigrationError):
    """Exception raised when migration execution times out."""
    
    def __init__(
        self,
        message: str,
        migration_id: Optional[str] = None,
        timeout_duration: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, migration_id=migration_id, **kwargs)
        self.timeout_duration = timeout_duration


class MigrationBackupError(MigrationError):
    """Exception raised during migration backup operations."""
    
    def __init__(
        self,
        message: str,
        backup_path: Optional[str] = None,
        backup_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.backup_path = backup_path
        self.backup_type = backup_type


class MigrationRestoreError(MigrationError):
    """Exception raised during migration restore operations."""
    
    def __init__(
        self,
        message: str,
        backup_path: Optional[str] = None,
        restore_point: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.backup_path = backup_path
        self.restore_point = restore_point
"""
Database Migration System for FastAPI Microservices SDK.

This module provides a comprehensive migration system that works with all
supported database engines (PostgreSQL, MySQL, MongoDB, SQLite).

Features:
- Version-controlled schema migrations
- Automatic rollback capabilities
- Multi-database support
- Migration validation and testing
- Dependency management between migrations
- Backup and restore integration
- Migration history tracking
- Dry-run capabilities

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .manager import MigrationManager
from .base import Migration, MigrationDirection, MigrationStatus
from .config import MigrationConfig
from .exceptions import MigrationError, MigrationValidationError, MigrationConflictError
from .history import MigrationHistory
from .validator import MigrationValidator

__all__ = [
    # Core classes
    "MigrationManager",
    "Migration",
    "MigrationConfig",
    "MigrationHistory",
    "MigrationValidator",
    
    # Enums
    "MigrationDirection",
    "MigrationStatus",
    
    # Exceptions
    "MigrationError",
    "MigrationValidationError",
    "MigrationConflictError",
]
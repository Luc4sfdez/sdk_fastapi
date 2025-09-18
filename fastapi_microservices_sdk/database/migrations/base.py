"""
Base migration classes and interfaces for the migration system.

This module defines the core abstractions for database migrations,
including the Migration base class and related enums.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
import hashlib
import json

from ..adapters.base import DatabaseAdapter
from ..exceptions import DatabaseError


class MigrationDirection(Enum):
    """Direction of migration execution."""
    UP = "up"
    DOWN = "down"


class MigrationStatus(Enum):
    """Status of migration execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationMetadata:
    """Metadata for a migration."""
    version: str
    name: str
    description: str
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    checksum: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class MigrationResult:
    """Result of migration execution."""
    migration_id: str
    status: MigrationStatus
    direction: MigrationDirection
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[Exception] = None
    rollback_info: Optional[Dict[str, Any]] = None
    affected_objects: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Get migration execution duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success(self) -> bool:
        """Check if migration was successful."""
        return self.status == MigrationStatus.COMPLETED


class Migration(ABC):
    """
    Base class for database migrations.
    
    All migrations must inherit from this class and implement
    the up() and down() methods.
    """
    
    def __init__(self, metadata: MigrationMetadata):
        self.metadata = metadata
        self._checksum = None
        
    @property
    def id(self) -> str:
        """Get unique migration ID."""
        return f"{self.metadata.version}_{self.metadata.name}"
    
    @property
    def checksum(self) -> str:
        """Get migration content checksum."""
        if self._checksum is None:
            self._checksum = self._calculate_checksum()
        return self._checksum
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of migration content."""
        content = {
            'version': self.metadata.version,
            'name': self.metadata.name,
            'description': self.metadata.description,
            'dependencies': sorted(self.metadata.dependencies),
            'up_sql': self.get_up_sql() if hasattr(self, 'get_up_sql') else '',
            'down_sql': self.get_down_sql() if hasattr(self, 'get_down_sql') else ''
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    @abstractmethod
    async def up(self, adapter: DatabaseAdapter) -> MigrationResult:
        """
        Execute the migration (forward direction).
        
        Args:
            adapter: Database adapter to execute migration on
            
        Returns:
            MigrationResult with execution details
        """
        pass
    
    @abstractmethod
    async def down(self, adapter: DatabaseAdapter) -> MigrationResult:
        """
        Rollback the migration (backward direction).
        
        Args:
            adapter: Database adapter to execute rollback on
            
        Returns:
            MigrationResult with rollback details
        """
        pass
    
    async def validate(self, adapter: DatabaseAdapter) -> bool:
        """
        Validate migration before execution.
        
        Args:
            adapter: Database adapter to validate against
            
        Returns:
            True if migration is valid
        """
        return True
    
    async def dry_run(self, adapter: DatabaseAdapter, direction: MigrationDirection) -> Dict[str, Any]:
        """
        Perform a dry run of the migration.
        
        Args:
            adapter: Database adapter
            direction: Migration direction
            
        Returns:
            Dictionary with dry run results
        """
        return {
            'migration_id': self.id,
            'direction': direction.value,
            'would_execute': True,
            'estimated_duration': 0.0,
            'affected_objects': []
        }
    
    def get_dependencies(self) -> Set[str]:
        """Get migration dependencies."""
        return set(self.metadata.dependencies)
    
    def has_dependency(self, migration_id: str) -> bool:
        """Check if migration has a specific dependency."""
        return migration_id in self.metadata.dependencies
    
    def __str__(self) -> str:
        return f"Migration({self.id})"
    
    def __repr__(self) -> str:
        return f"Migration(id='{self.id}', version='{self.metadata.version}')"


class SQLMigration(Migration):
    """
    SQL-based migration for relational databases.
    
    This class provides a convenient way to define migrations
    using SQL statements.
    """
    
    def __init__(self, metadata: MigrationMetadata, up_sql: str, down_sql: str):
        super().__init__(metadata)
        self.up_sql = up_sql.strip()
        self.down_sql = down_sql.strip()
    
    def get_up_sql(self) -> str:
        """Get the up SQL statement."""
        return self.up_sql
    
    def get_down_sql(self) -> str:
        """Get the down SQL statement."""
        return self.down_sql
    
    async def up(self, adapter: DatabaseAdapter) -> MigrationResult:
        """Execute the up migration using SQL."""
        result = MigrationResult(
            migration_id=self.id,
            status=MigrationStatus.RUNNING,
            direction=MigrationDirection.UP,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Execute SQL statements
            statements = self._split_sql_statements(self.up_sql)
            affected_objects = []
            
            for statement in statements:
                if statement.strip():
                    query_result = await adapter.execute_query(
                        None,  # Will use a connection from the adapter
                        statement
                    )
                    affected_objects.extend(self._extract_affected_objects(statement))
            
            result.status = MigrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            result.affected_objects = affected_objects
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.completed_at = datetime.now(timezone.utc)
            result.error = e
            raise DatabaseError(f"Migration {self.id} failed: {e}", original_error=e)
        
        return result
    
    async def down(self, adapter: DatabaseAdapter) -> MigrationResult:
        """Execute the down migration using SQL."""
        result = MigrationResult(
            migration_id=self.id,
            status=MigrationStatus.RUNNING,
            direction=MigrationDirection.DOWN,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            # Execute rollback SQL statements
            statements = self._split_sql_statements(self.down_sql)
            affected_objects = []
            
            for statement in statements:
                if statement.strip():
                    query_result = await adapter.execute_query(
                        None,  # Will use a connection from the adapter
                        statement
                    )
                    affected_objects.extend(self._extract_affected_objects(statement))
            
            result.status = MigrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            result.affected_objects = affected_objects
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.completed_at = datetime.now(timezone.utc)
            result.error = e
            raise DatabaseError(f"Migration rollback {self.id} failed: {e}", original_error=e)
        
        return result
    
    def _split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL into individual statements."""
        # Simple split by semicolon - could be enhanced for more complex cases
        statements = []
        current_statement = ""
        
        for line in sql.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                current_statement += line + '\n'
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def _extract_affected_objects(self, sql: str) -> List[str]:
        """Extract affected database objects from SQL statement."""
        affected = []
        sql_upper = sql.upper().strip()
        
        # Simple extraction - could be enhanced with proper SQL parsing
        if sql_upper.startswith('CREATE TABLE'):
            # Extract table name
            parts = sql.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`"[]')
                        affected.append(f"table:{table_name}")
                    break
        elif sql_upper.startswith('DROP TABLE'):
            # Extract table name
            parts = sql.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`"[]')
                        affected.append(f"table:{table_name}")
                    break
        elif sql_upper.startswith('ALTER TABLE'):
            # Extract table name
            parts = sql.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`"[]')
                        affected.append(f"table:{table_name}")
                    break
        
        return affected


class DocumentMigration(Migration):
    """
    Document-based migration for NoSQL databases like MongoDB.
    
    This class provides migration capabilities for document databases.
    """
    
    def __init__(self, metadata: MigrationMetadata):
        super().__init__(metadata)
    
    async def up(self, adapter: DatabaseAdapter) -> MigrationResult:
        """Execute the up migration for document database."""
        result = MigrationResult(
            migration_id=self.id,
            status=MigrationStatus.RUNNING,
            direction=MigrationDirection.UP,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            await self.execute_document_migration(adapter, MigrationDirection.UP)
            
            result.status = MigrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.completed_at = datetime.now(timezone.utc)
            result.error = e
            raise DatabaseError(f"Document migration {self.id} failed: {e}", original_error=e)
        
        return result
    
    async def down(self, adapter: DatabaseAdapter) -> MigrationResult:
        """Execute the down migration for document database."""
        result = MigrationResult(
            migration_id=self.id,
            status=MigrationStatus.RUNNING,
            direction=MigrationDirection.DOWN,
            started_at=datetime.now(timezone.utc)
        )
        
        try:
            await self.execute_document_migration(adapter, MigrationDirection.DOWN)
            
            result.status = MigrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            result.status = MigrationStatus.FAILED
            result.completed_at = datetime.now(timezone.utc)
            result.error = e
            raise DatabaseError(f"Document migration rollback {self.id} failed: {e}", original_error=e)
        
        return result
    
    @abstractmethod
    async def execute_document_migration(self, adapter: DatabaseAdapter, direction: MigrationDirection):
        """
        Execute document migration operations.
        
        Args:
            adapter: Database adapter
            direction: Migration direction
        """
        pass
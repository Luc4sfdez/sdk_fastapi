"""
Migration history tracking for the database migration system.

This module provides functionality to track and manage migration
execution history across different database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
import json

from ..adapters.base import DatabaseAdapter
from ..config import DatabaseEngine
from .base import MigrationResult, MigrationStatus, MigrationDirection
from .config import MigrationConfig
from .exceptions import MigrationError


@dataclass
class MigrationHistoryEntry:
    """Entry in migration history."""
    version: str
    name: str
    description: str
    checksum: str
    executed_at: datetime
    execution_time: float
    success: bool
    direction: str
    error_message: Optional[str] = None
    rollback_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['executed_at'] = self.executed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationHistoryEntry':
        """Create from dictionary."""
        if isinstance(data['executed_at'], str):
            data['executed_at'] = datetime.fromisoformat(data['executed_at'])
        return cls(**data)


class MigrationHistory:
    """
    Manages migration execution history.
    
    Provides functionality to track, query, and manage migration
    execution history across different database engines.
    """
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self._initialized = False
    
    async def initialize(self, adapter: DatabaseAdapter) -> None:
        """
        Initialize migration history storage.
        
        Args:
            adapter: Database adapter to use
        """
        if self._initialized:
            return
        
        try:
            if self.config.auto_create_migration_table:
                await self._create_migration_table(adapter)
            
            self._initialized = True
            
        except Exception as e:
            raise MigrationError(f"Failed to initialize migration history: {e}", original_error=e)
    
    async def _create_migration_table(self, adapter: DatabaseAdapter) -> None:
        """Create migration history table/collection."""
        engine = adapter.config.engine
        table_name = self.config.migration_table_name
        
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            await self._create_sql_migration_table(adapter, table_name)
        elif engine == DatabaseEngine.MONGODB:
            await self._create_mongodb_migration_collection(adapter, table_name)
        else:
            raise MigrationError(f"Unsupported database engine: {engine}")
    
    async def _create_sql_migration_table(self, adapter: DatabaseAdapter, table_name: str) -> None:
        """Create SQL migration table."""
        engine = adapter.config.engine
        
        # Base SQL for creating migration table
        if engine == DatabaseEngine.POSTGRESQL:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                checksum VARCHAR(64) NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                execution_time FLOAT,
                success BOOLEAN NOT NULL,
                direction VARCHAR(10) NOT NULL DEFAULT 'up',
                error_message TEXT,
                rollback_info JSONB
            );
            
            CREATE INDEX IF NOT EXISTS idx_{table_name}_executed_at ON {table_name} (executed_at);
            CREATE INDEX IF NOT EXISTS idx_{table_name}_success ON {table_name} (success);
            """
        elif engine == DatabaseEngine.MYSQL:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                checksum VARCHAR(64) NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time FLOAT,
                success BOOLEAN NOT NULL,
                direction VARCHAR(10) NOT NULL DEFAULT 'up',
                error_message TEXT,
                rollback_info JSON
            );
            
            CREATE INDEX idx_{table_name}_executed_at ON {table_name} (executed_at);
            CREATE INDEX idx_{table_name}_success ON {table_name} (success);
            """
        elif engine == DatabaseEngine.SQLITE:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                checksum TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                execution_time REAL,
                success INTEGER NOT NULL,
                direction TEXT NOT NULL DEFAULT 'up',
                error_message TEXT,
                rollback_info TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_{table_name}_executed_at ON {table_name} (executed_at);
            CREATE INDEX IF NOT EXISTS idx_{table_name}_success ON {table_name} (success);
            """
        
        # Execute SQL statements
        statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
        for statement in statements:
            await adapter.execute_query(None, statement)
    
    async def _create_mongodb_migration_collection(self, adapter: DatabaseAdapter, collection_name: str) -> None:
        """Create MongoDB migration collection with indexes."""
        # MongoDB collections are created automatically, but we can create indexes
        try:
            # Create indexes for better performance
            await adapter.execute_query(
                None,
                f"db.{collection_name}.createIndex",
                parameters={"version": 1}, 
                options={"unique": True}
            )
            
            await adapter.execute_query(
                None,
                f"db.{collection_name}.createIndex",
                parameters={"executed_at": -1}
            )
            
            await adapter.execute_query(
                None,
                f"db.{collection_name}.createIndex",
                parameters={"success": 1}
            )
            
        except Exception:
            # Indexes might already exist, ignore errors
            pass
    
    async def record_migration(
        self,
        adapter: DatabaseAdapter,
        result: MigrationResult,
        migration_name: str,
        description: str,
        checksum: str
    ) -> None:
        """
        Record migration execution in history.
        
        Args:
            adapter: Database adapter
            result: Migration execution result
            migration_name: Migration name
            description: Migration description
            checksum: Migration checksum
        """
        if not self._initialized:
            await self.initialize(adapter)
        
        entry = MigrationHistoryEntry(
            version=result.migration_id.split('_')[0],  # Extract version from ID
            name=migration_name,
            description=description,
            checksum=checksum,
            executed_at=result.started_at,
            execution_time=result.duration or 0.0,
            success=result.success,
            direction=result.direction.value,
            error_message=str(result.error) if result.error else None,
            rollback_info=result.rollback_info
        )
        
        await self._insert_history_entry(adapter, entry)
    
    async def _insert_history_entry(self, adapter: DatabaseAdapter, entry: MigrationHistoryEntry) -> None:
        """Insert history entry into storage."""
        engine = adapter.config.engine
        table_name = self.config.migration_table_name
        
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            await self._insert_sql_history_entry(adapter, table_name, entry)
        elif engine == DatabaseEngine.MONGODB:
            await self._insert_mongodb_history_entry(adapter, table_name, entry)
    
    async def _insert_sql_history_entry(
        self,
        adapter: DatabaseAdapter,
        table_name: str,
        entry: MigrationHistoryEntry
    ) -> None:
        """Insert SQL history entry."""
        engine = adapter.config.engine
        
        if engine == DatabaseEngine.SQLITE:
            # SQLite uses different parameter style and data types
            sql = f"""
            INSERT OR REPLACE INTO {table_name} 
            (version, name, description, checksum, executed_at, execution_time, 
             success, direction, error_message, rollback_info)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = [
                entry.version,
                entry.name,
                entry.description,
                entry.checksum,
                entry.executed_at.isoformat(),
                entry.execution_time,
                1 if entry.success else 0,
                entry.direction,
                entry.error_message,
                json.dumps(entry.rollback_info) if entry.rollback_info else None
            ]
        else:
            # PostgreSQL and MySQL
            sql = f"""
            INSERT INTO {table_name} 
            (version, name, description, checksum, executed_at, execution_time, 
             success, direction, error_message, rollback_info)
            VALUES (%(version)s, %(name)s, %(description)s, %(checksum)s, %(executed_at)s, 
                    %(execution_time)s, %(success)s, %(direction)s, %(error_message)s, %(rollback_info)s)
            ON CONFLICT (version) DO UPDATE SET
                executed_at = EXCLUDED.executed_at,
                execution_time = EXCLUDED.execution_time,
                success = EXCLUDED.success,
                direction = EXCLUDED.direction,
                error_message = EXCLUDED.error_message,
                rollback_info = EXCLUDED.rollback_info
            """
            params = {
                'version': entry.version,
                'name': entry.name,
                'description': entry.description,
                'checksum': entry.checksum,
                'executed_at': entry.executed_at,
                'execution_time': entry.execution_time,
                'success': entry.success,
                'direction': entry.direction,
                'error_message': entry.error_message,
                'rollback_info': entry.rollback_info
            }
        
        await adapter.execute_query(None, sql, params)
    
    async def _insert_mongodb_history_entry(
        self,
        adapter: DatabaseAdapter,
        collection_name: str,
        entry: MigrationHistoryEntry
    ) -> None:
        """Insert MongoDB history entry."""
        document = entry.to_dict()
        
        await adapter.execute_query(
            None,
            f"db.{collection_name}.replaceOne",
            parameters={
                "filter": {"version": entry.version},
                "replacement": document,
                "options": {"upsert": True}
            }
        )
    
    async def get_executed_migrations(self, adapter: DatabaseAdapter) -> Set[str]:
        """
        Get set of executed migration versions.
        
        Args:
            adapter: Database adapter
            
        Returns:
            Set of executed migration versions
        """
        if not self._initialized:
            await self.initialize(adapter)
        
        engine = adapter.config.engine
        table_name = self.config.migration_table_name
        
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            sql = f"SELECT version FROM {table_name} WHERE success = true"
            if engine == DatabaseEngine.SQLITE:
                sql = f"SELECT version FROM {table_name} WHERE success = 1"
            
            results = await adapter.fetch_all(None, sql)
            return {row['version'] for row in results}
            
        elif engine == DatabaseEngine.MONGODB:
            results = await adapter.fetch_all(
                None,
                f"db.{table_name}.find",
                parameters={"success": True},
                projection={"version": 1}
            )
            return {doc['version'] for doc in results}
        
        return set()
    
    async def get_migration_history(
        self,
        adapter: DatabaseAdapter,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[MigrationHistoryEntry]:
        """
        Get migration history entries.
        
        Args:
            adapter: Database adapter
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            
        Returns:
            List of migration history entries
        """
        if not self._initialized:
            await self.initialize(adapter)
        
        engine = adapter.config.engine
        table_name = self.config.migration_table_name
        
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            sql = f"""
            SELECT version, name, description, checksum, executed_at, execution_time,
                   success, direction, error_message, rollback_info
            FROM {table_name}
            ORDER BY executed_at DESC
            """
            
            if limit:
                sql += f" LIMIT {limit}"
            if offset:
                sql += f" OFFSET {offset}"
            
            results = await adapter.fetch_all(None, sql)
            
            entries = []
            for row in results:
                # Handle different date formats and boolean types
                executed_at = row['executed_at']
                if isinstance(executed_at, str):
                    executed_at = datetime.fromisoformat(executed_at)
                
                success = row['success']
                if isinstance(success, int):
                    success = bool(success)
                
                rollback_info = row.get('rollback_info')
                if isinstance(rollback_info, str) and rollback_info:
                    rollback_info = json.loads(rollback_info)
                
                entry = MigrationHistoryEntry(
                    version=row['version'],
                    name=row['name'],
                    description=row['description'],
                    checksum=row['checksum'],
                    executed_at=executed_at,
                    execution_time=row['execution_time'] or 0.0,
                    success=success,
                    direction=row['direction'],
                    error_message=row.get('error_message'),
                    rollback_info=rollback_info
                )
                entries.append(entry)
            
            return entries
            
        elif engine == DatabaseEngine.MONGODB:
            query_params = {}
            if limit or offset:
                query_params['limit'] = limit
                query_params['skip'] = offset
            
            results = await adapter.fetch_all(
                None,
                f"db.{table_name}.find",
                parameters={},
                sort=[("executed_at", -1)],
                **query_params
            )
            
            return [MigrationHistoryEntry.from_dict(doc) for doc in results]
        
        return []
    
    async def get_last_migration(self, adapter: DatabaseAdapter) -> Optional[MigrationHistoryEntry]:
        """
        Get the last executed migration.
        
        Args:
            adapter: Database adapter
            
        Returns:
            Last migration entry or None
        """
        history = await self.get_migration_history(adapter, limit=1)
        return history[0] if history else None
    
    async def is_migration_executed(self, adapter: DatabaseAdapter, version: str) -> bool:
        """
        Check if a migration has been executed.
        
        Args:
            adapter: Database adapter
            version: Migration version
            
        Returns:
            True if migration has been executed successfully
        """
        executed_migrations = await self.get_executed_migrations(adapter)
        return version in executed_migrations
    
    async def remove_migration_record(self, adapter: DatabaseAdapter, version: str) -> None:
        """
        Remove migration record from history.
        
        Args:
            adapter: Database adapter
            version: Migration version to remove
        """
        if not self._initialized:
            await self.initialize(adapter)
        
        engine = adapter.config.engine
        table_name = self.config.migration_table_name
        
        if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL, DatabaseEngine.SQLITE]:
            sql = f"DELETE FROM {table_name} WHERE version = ?"
            if engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL]:
                sql = f"DELETE FROM {table_name} WHERE version = %(version)s"
                params = {'version': version}
            else:
                params = [version]
            
            await adapter.execute_query(None, sql, params)
            
        elif engine == DatabaseEngine.MONGODB:
            await adapter.execute_query(
                None,
                f"db.{table_name}.deleteOne",
                parameters={"version": version}
            )
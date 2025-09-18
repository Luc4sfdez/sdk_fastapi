"""
Cache manager for coordinating all caching activities.

This module provides the central CacheManager class that orchestrates
caching operations, strategies, invalidation, and performance optimization
across all database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from ..manager import DatabaseManager
from .config import CacheConfig, CacheBackend, CacheStrategy, InvalidationPolicy
from .backends import CacheBackendInterface, RedisCacheBackend, InMemoryCacheBackend, CacheEntry
from .exceptions import (
    CacheError,
    CacheBackendError,
    CacheConfigurationError,
    CacheKeyError
)

# Integration with communication logging
try:
    from ...communication.logging import CommunicationLogger
    COMMUNICATION_LOGGING_AVAILABLE = True
except ImportError:
    COMMUNICATION_LOGGING_AVAILABLE = False
    CommunicationLogger = None


@dataclass
class CacheStats:
    """Cache statistics and performance metrics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    average_get_time: float = 0.0
    average_set_time: float = 0.0
    
    def update_hit_rate(self) -> None:
        """Update hit and miss rates."""
        total_requests = self.hits + self.misses
        if total_requests > 0:
            self.hit_rate = self.hits / total_requests
            self.miss_rate = self.misses / total_requests
        else:
            self.hit_rate = 0.0
            self.miss_rate = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'evictions': self.evictions,
            'errors': self.errors,
            'total_size_bytes': self.total_size_bytes,
            'entry_count': self.entry_count,
            'hit_rate': self.hit_rate,
            'miss_rate': self.miss_rate,
            'average_get_time': self.average_get_time,
            'average_set_time': self.average_set_time
        }


class CacheManager:
    """
    Central cache management orchestrator.
    
    Coordinates caching operations, strategies, invalidation, and performance
    optimization across all database engines with enterprise-grade capabilities.
    """
    
    def __init__(self, config: CacheConfig, database_manager: DatabaseManager):
        self.config = config
        self.database_manager = database_manager
        
        # Backend management
        self._backends: Dict[str, CacheBackendInterface] = {}
        self._default_backend: Optional[CacheBackendInterface] = None
        
        # Statistics and monitoring
        self._stats = CacheStats()
        self._database_stats: Dict[str, CacheStats] = {}
        
        # State management
        self._initialized = False
        self._running = False
        
        # Performance tracking
        self._operation_times: Dict[str, List[float]] = {
            'get': [],
            'set': [],
            'delete': []
        }
        
        # Setup logging
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("cache.manager")
        else:
            self.logger = logging.getLogger(__name__)
        
        # Callbacks
        self._hit_callbacks: List[Callable] = []
        self._miss_callbacks: List[Callable] = []
        self._eviction_callbacks: List[Callable] = []
        
        # Cache warming
        self._warming_tasks: Dict[str, asyncio.Task] = {}
        
        self.logger.info("CacheManager initialized")
    
    async def initialize(self) -> None:
        """Initialize cache manager and backends."""
        if self._initialized:
            return
        
        try:
            self.logger.info("Initializing CacheManager...")
            
            # Initialize backends
            await self._initialize_backends()
            
            # Initialize database-specific stats
            for db_name in self.database_manager.list_databases():
                self._database_stats[db_name] = CacheStats()
            
            # Start cache warming if enabled
            if self.config.cache_warming_enabled:
                await self._start_cache_warming()
            
            self._initialized = True
            self.logger.info("CacheManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize CacheManager: {e}")
            raise CacheError(f"CacheManager initialization failed: {e}", original_error=e)
    
    async def _initialize_backends(self) -> None:
        """Initialize cache backends."""
        # Initialize default backend
        if self.config.default_backend == CacheBackend.REDIS:
            self._default_backend = RedisCacheBackend(self.config)
        elif self.config.default_backend == CacheBackend.MEMORY:
            self._default_backend = InMemoryCacheBackend(self.config)
        else:
            raise CacheConfigurationError(f"Unsupported default backend: {self.config.default_backend}")
        
        await self._default_backend.connect()
        self._backends['default'] = self._default_backend
        
        # Initialize database-specific backends if configured
        for db_name in self.database_manager.list_databases():
            db_config = self.config.get_database_config(db_name)
            if 'backend' in db_config:
                backend_type = CacheBackend(db_config['backend'])
                
                if backend_type == CacheBackend.REDIS:
                    backend = RedisCacheBackend(self.config)
                elif backend_type == CacheBackend.MEMORY:
                    backend = InMemoryCacheBackend(self.config)
                else:
                    continue
                
                await backend.connect()
                self._backends[db_name] = backend
    
    async def shutdown(self) -> None:
        """Shutdown cache manager and backends."""
        if not self._initialized:
            return
        
        try:
            self.logger.info("Shutting down CacheManager...")
            
            # Stop cache warming tasks
            for task in self._warming_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            self._warming_tasks.clear()
            
            # Disconnect backends
            for backend in self._backends.values():
                try:
                    await backend.disconnect()
                except Exception as e:
                    self.logger.error(f"Error disconnecting backend: {e}")
            
            self._backends.clear()
            self._default_backend = None
            self._initialized = False
            
            self.logger.info("CacheManager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during CacheManager shutdown: {e}")
    
    def _get_backend(self, database_name: Optional[str] = None) -> CacheBackendInterface:
        """Get appropriate backend for database."""
        if database_name and database_name in self._backends:
            return self._backends[database_name]
        return self._default_backend
    
    def _generate_cache_key(
        self,
        database_name: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None
    ) -> str:
        """Generate cache key for query."""
        # Create base key components
        key_components = [
            self.config.get_cache_key_prefix(database_name, table_name),
            query.strip()
        ]
        
        # Add parameters if present
        if parameters:
            # Sort parameters for consistent key generation
            sorted_params = json.dumps(parameters, sort_keys=True)
            key_components.append(sorted_params)
        
        # Create hash of the key components
        key_string = '|'.join(key_components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:32]
        
        # Create final key with prefix
        cache_key = f"cache:{database_name}:{key_hash}"
        
        # Validate key length
        if len(cache_key) > self.config.max_key_size:
            raise CacheKeyError(
                f"Cache key too long: {len(cache_key)} > {self.config.max_key_size}",
                cache_key=cache_key,
                reason="key_too_long"
            )
        
        return cache_key
    
    async def get(
        self,
        database_name: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached query result.
        
        Args:
            database_name: Name of the database
            query: SQL query string
            parameters: Query parameters
            table_name: Table name for key generation
            
        Returns:
            Cached result or None if not found
        """
        if not self.config.enabled:
            return None
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(database_name, query, parameters, table_name)
            
            # Get backend
            backend = self._get_backend(database_name)
            
            # Get from cache
            entry = await backend.get(cache_key)
            
            # Update statistics
            if entry:
                self._stats.hits += 1
                self._database_stats[database_name].hits += 1
                
                # Execute hit callbacks
                for callback in self._hit_callbacks:
                    try:
                        await callback(cache_key, entry.value)
                    except Exception as e:
                        self.logger.warning(f"Hit callback failed: {e}")
                
                return entry.value
            else:
                self._stats.misses += 1
                self._database_stats[database_name].misses += 1
                
                # Execute miss callbacks
                for callback in self._miss_callbacks:
                    try:
                        await callback(cache_key)
                    except Exception as e:
                        self.logger.warning(f"Miss callback failed: {e}")
                
                return None
        
        except Exception as e:
            self._stats.errors += 1
            self._database_stats[database_name].errors += 1
            self.logger.error(f"Cache get error: {e}")
            return None
        
        finally:
            # Update performance metrics
            operation_time = asyncio.get_event_loop().time() - start_time
            self._operation_times['get'].append(operation_time)
            
            # Keep only last 1000 measurements
            if len(self._operation_times['get']) > 1000:
                self._operation_times['get'] = self._operation_times['get'][-1000:]
            
            # Update average
            if self._operation_times['get']:
                self._stats.average_get_time = sum(self._operation_times['get']) / len(self._operation_times['get'])
            
            # Update hit rates
            self._stats.update_hit_rate()
            self._database_stats[database_name].update_hit_rate()
    
    async def set(
        self,
        database_name: str,
        query: str,
        result: Any,
        parameters: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None,
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Cache query result.
        
        Args:
            database_name: Name of the database
            query: SQL query string
            result: Query result to cache
            parameters: Query parameters
            table_name: Table name for key generation
            ttl: Time to live for cache entry
            tags: Tags for invalidation
            
        Returns:
            True if cached successfully
        """
        if not self.config.enabled:
            return False
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(database_name, query, parameters, table_name)
            
            # Get backend
            backend = self._get_backend(database_name)
            
            # Use default TTL if not provided
            if ttl is None:
                # Determine query type for TTL
                query_type = self._extract_query_type(query)
                ttl = self.config.get_ttl_for_query_type(query_type)
            
            # Generate tags if not provided
            if tags is None:
                tags = self.config.get_cache_tags_for_query(query, database_name)
            
            # Set in cache
            success = await backend.set(cache_key, result, ttl, tags)
            
            if success:
                self._stats.sets += 1
                self._database_stats[database_name].sets += 1
            
            return success
        
        except Exception as e:
            self._stats.errors += 1
            self._database_stats[database_name].errors += 1
            self.logger.error(f"Cache set error: {e}")
            return False
        
        finally:
            # Update performance metrics
            operation_time = asyncio.get_event_loop().time() - start_time
            self._operation_times['set'].append(operation_time)
            
            # Keep only last 1000 measurements
            if len(self._operation_times['set']) > 1000:
                self._operation_times['set'] = self._operation_times['set'][-1000:]
            
            # Update average
            if self._operation_times['set']:
                self._stats.average_set_time = sum(self._operation_times['set']) / len(self._operation_times['set'])
    
    async def delete(
        self,
        database_name: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        table_name: Optional[str] = None
    ) -> bool:
        """
        Delete cached query result.
        
        Args:
            database_name: Name of the database
            query: SQL query string
            parameters: Query parameters
            table_name: Table name for key generation
            
        Returns:
            True if deleted successfully
        """
        if not self.config.enabled:
            return False
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(database_name, query, parameters, table_name)
            
            # Get backend
            backend = self._get_backend(database_name)
            
            # Delete from cache
            success = await backend.delete(cache_key)
            
            if success:
                self._stats.deletes += 1
                self._database_stats[database_name].deletes += 1
            
            return success
        
        except Exception as e:
            self._stats.errors += 1
            self._database_stats[database_name].errors += 1
            self.logger.error(f"Cache delete error: {e}")
            return False
        
        finally:
            # Update performance metrics
            operation_time = asyncio.get_event_loop().time() - start_time
            self._operation_times['delete'].append(operation_time)
            
            # Keep only last 1000 measurements
            if len(self._operation_times['delete']) > 1000:
                self._operation_times['delete'] = self._operation_times['delete'][-1000:]
    
    async def invalidate_by_tags(self, tags: List[str], database_name: Optional[str] = None) -> int:
        """
        Invalidate cache entries by tags.
        
        Args:
            tags: Tags to invalidate
            database_name: Specific database or all if None
            
        Returns:
            Number of entries invalidated
        """
        if not self.config.enabled:
            return 0
        
        try:
            total_deleted = 0
            
            if database_name:
                # Invalidate for specific database
                backend = self._get_backend(database_name)
                deleted = await backend.delete_by_tags(tags)
                total_deleted += deleted
                self._database_stats[database_name].deletes += deleted
            else:
                # Invalidate across all backends
                for db_name, backend in self._backends.items():
                    deleted = await backend.delete_by_tags(tags)
                    total_deleted += deleted
                    if db_name != 'default' and db_name in self._database_stats:
                        self._database_stats[db_name].deletes += deleted
            
            self._stats.deletes += total_deleted
            return total_deleted
        
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {e}")
            return 0
    
    async def clear_database_cache(self, database_name: str) -> bool:
        """
        Clear all cache entries for a database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            True if cleared successfully
        """
        if not self.config.enabled:
            return False
        
        try:
            # Clear by database tag
            deleted = await self.invalidate_by_tags([f"db:{database_name}"], database_name)
            self.logger.info(f"Cleared {deleted} cache entries for database {database_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to clear database cache: {e}")
            return False
    
    async def clear_table_cache(self, database_name: str, table_name: str) -> bool:
        """
        Clear all cache entries for a table.
        
        Args:
            database_name: Name of the database
            table_name: Name of the table
            
        Returns:
            True if cleared successfully
        """
        if not self.config.enabled:
            return False
        
        try:
            # Clear by table tag
            deleted = await self.invalidate_by_tags([f"table:{table_name}"], database_name)
            self.logger.info(f"Cleared {deleted} cache entries for table {database_name}.{table_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to clear table cache: {e}")
            return False
    
    async def get_stats(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            database_name: Specific database or overall if None
            
        Returns:
            Statistics dictionary
        """
        if database_name and database_name in self._database_stats:
            stats = self._database_stats[database_name].to_dict()
            stats['database'] = database_name
        else:
            stats = self._stats.to_dict()
            stats['database'] = 'overall'
        
        # Add backend stats
        backend_stats = {}
        if database_name:
            backend = self._get_backend(database_name)
            backend_stats = await backend.get_stats()
        else:
            for name, backend in self._backends.items():
                backend_stats[name] = await backend.get_stats()
        
        stats['backend_stats'] = backend_stats
        return stats
    
    def add_hit_callback(self, callback: Callable) -> None:
        """Add callback for cache hits."""
        self._hit_callbacks.append(callback)
    
    def add_miss_callback(self, callback: Callable) -> None:
        """Add callback for cache misses."""
        self._miss_callbacks.append(callback)
    
    def add_eviction_callback(self, callback: Callable) -> None:
        """Add callback for cache evictions."""
        self._eviction_callbacks.append(callback)
    
    def _extract_query_type(self, query: str) -> str:
        """Extract query type from SQL query."""
        query_upper = query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            if 'COUNT(' in query_upper:
                return 'COUNT'
            elif any(func in query_upper for func in ['SUM(', 'AVG(', 'MIN(', 'MAX(', 'GROUP BY']):
                return 'AGGREGATE'
            else:
                return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        else:
            return 'OTHER'
    
    async def _start_cache_warming(self) -> None:
        """Start cache warming tasks."""
        # Implementation would depend on specific warming strategies
        # This is a placeholder for cache warming functionality
        self.logger.info("Cache warming started")
    
    @asynccontextmanager
    async def cache_context(self, database_name: str):
        """Context manager for cache operations."""
        try:
            yield self
        except Exception as e:
            self.logger.error(f"Cache context error for {database_name}: {e}")
            raise
    
    def should_cache_query(self, query: str, execution_time: float) -> bool:
        """
        Determine if a query should be cached.
        
        Args:
            query: SQL query string
            execution_time: Query execution time in seconds
            
        Returns:
            True if query should be cached
        """
        return self.config.should_cache_query(query, execution_time)
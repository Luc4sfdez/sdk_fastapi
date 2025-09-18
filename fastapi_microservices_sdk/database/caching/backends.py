"""
Cache backend implementations for the database caching system.

This module provides various cache backend implementations including
Redis, Memcached, and in-memory caching with a unified interface.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import json
import pickle
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
import threading
from collections import OrderedDict
import weakref

from .config import CacheConfig, CacheBackend
from .exceptions import (
    CacheBackendError,
    CacheConnectionError,
    CacheTimeoutError,
    CacheCapacityError
)

# Optional imports for cache backends
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

try:
    import aiomcache
    MEMCACHED_AVAILABLE = True
except ImportError:
    aiomcache = None
    MEMCACHED_AVAILABLE = False


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def age(self) -> timedelta:
        """Get age of the entry."""
        return datetime.now(timezone.utc) - self.created_at
    
    def mark_accessed(self) -> None:
        """Mark entry as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now(timezone.utc)


class CacheBackendInterface(ABC):
    """Abstract interface for cache backends."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the cache backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the cache backend."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass
    
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[CacheEntry]]:
        """Get multiple values from cache."""
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Set multiple values in cache."""
        result = {}
        for key, value in items.items():
            result[key] = await self.set(key, value, ttl, tags)
        return result
    
    async def delete_many(self, keys: List[str]) -> Dict[str, bool]:
        """Delete multiple values from cache."""
        result = {}
        for key in keys:
            result[key] = await self.delete(key)
        return result
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """Delete entries by tags (default implementation)."""
        # Default implementation - subclasses should override for efficiency
        deleted_count = 0
        # This is a placeholder - actual implementation depends on backend
        return deleted_count
    
    @property
    def is_connected(self) -> bool:
        """Check if backend is connected."""
        return self._connected


class RedisCacheBackend(CacheBackendInterface):
    """Redis cache backend implementation."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        if not REDIS_AVAILABLE:
            raise CacheBackendError("Redis is not available. Install redis package.")
        
        self.redis_config = config.get_backend_config(CacheBackend.REDIS)
        self._client: Optional[redis.Redis] = None
        self._connection_pool = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            # Create connection pool
            self._connection_pool = redis.ConnectionPool(
                host=self.redis_config.get("host", "localhost"),
                port=self.redis_config.get("port", 6379),
                db=self.redis_config.get("db", 0),
                password=self.redis_config.get("password"),
                ssl=self.redis_config.get("ssl", False),
                max_connections=self.redis_config.get("connection_pool_size", 10),
                socket_timeout=self.redis_config.get("socket_timeout", 5.0),
                socket_connect_timeout=self.redis_config.get("socket_connect_timeout", 5.0),
                retry_on_timeout=self.redis_config.get("retry_on_timeout", True)
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await self._client.ping()
            self._connected = True
            
        except Exception as e:
            raise CacheConnectionError(
                f"Failed to connect to Redis: {e}",
                backend="redis",
                host=self.redis_config.get("host"),
                port=self.redis_config.get("port")
            )
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
        
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None
        
        self._connected = False
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from Redis."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            # Get value and metadata
            pipe = self._client.pipeline()
            pipe.hgetall(f"{key}:meta")
            pipe.get(key)
            
            meta_data, value_data = await pipe.execute()
            
            if not value_data:
                return None
            
            # Deserialize value
            value = pickle.loads(value_data)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.fromisoformat(meta_data.get(b'created_at', b'').decode()) if meta_data.get(b'created_at') else datetime.now(timezone.utc),
                expires_at=datetime.fromisoformat(meta_data.get(b'expires_at', b'').decode()) if meta_data.get(b'expires_at') else None,
                access_count=int(meta_data.get(b'access_count', 0)),
                size_bytes=int(meta_data.get(b'size_bytes', 0)),
                tags=json.loads(meta_data.get(b'tags', b'[]').decode())
            )
            
            # Check if expired
            if entry.is_expired:
                await self.delete(key)
                return None
            
            # Update access count
            entry.mark_accessed()
            await self._update_metadata(key, entry)
            
            return entry
            
        except Exception as e:
            raise CacheBackendError(f"Failed to get from Redis: {e}", backend="redis", operation="get")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in Redis."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            # Serialize value
            serialized_value = pickle.dumps(value)
            
            # Calculate expiration
            expires_at = None
            if ttl:
                expires_at = datetime.now(timezone.utc) + ttl
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                size_bytes=len(serialized_value),
                tags=tags or []
            )
            
            # Store in Redis with pipeline
            pipe = self._client.pipeline()
            
            # Set value
            if ttl:
                pipe.setex(key, int(ttl.total_seconds()), serialized_value)
            else:
                pipe.set(key, serialized_value)
            
            # Set metadata
            meta_data = {
                'created_at': entry.created_at.isoformat(),
                'expires_at': entry.expires_at.isoformat() if entry.expires_at else '',
                'access_count': entry.access_count,
                'size_bytes': entry.size_bytes,
                'tags': json.dumps(entry.tags)
            }
            
            pipe.hset(f"{key}:meta", mapping=meta_data)
            
            if ttl:
                pipe.expire(f"{key}:meta", int(ttl.total_seconds()))
            
            # Add to tag indexes
            for tag in entry.tags:
                pipe.sadd(f"tag:{tag}", key)
                if ttl:
                    pipe.expire(f"tag:{tag}", int(ttl.total_seconds()))
            
            await pipe.execute()
            return True
            
        except Exception as e:
            raise CacheBackendError(f"Failed to set in Redis: {e}", backend="redis", operation="set")
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            # Get tags before deletion
            meta_data = await self._client.hgetall(f"{key}:meta")
            tags = json.loads(meta_data.get(b'tags', b'[]').decode()) if meta_data else []
            
            # Delete key and metadata
            pipe = self._client.pipeline()
            pipe.delete(key)
            pipe.delete(f"{key}:meta")
            
            # Remove from tag indexes
            for tag in tags:
                pipe.srem(f"tag:{tag}", key)
            
            results = await pipe.execute()
            return bool(results[0])  # First result is from key deletion
            
        except Exception as e:
            raise CacheBackendError(f"Failed to delete from Redis: {e}", backend="redis", operation="delete")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            return bool(await self._client.exists(key))
        except Exception as e:
            raise CacheBackendError(f"Failed to check existence in Redis: {e}", backend="redis", operation="exists")
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            await self._client.flushdb()
            return True
        except Exception as e:
            raise CacheBackendError(f"Failed to clear Redis: {e}", backend="redis", operation="clear")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            info = await self._client.info()
            return {
                'backend': 'redis',
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            raise CacheBackendError(f"Failed to get Redis stats: {e}", backend="redis", operation="stats")
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """Delete entries by tags."""
        if not self._client:
            raise CacheBackendError("Redis client not connected")
        
        try:
            deleted_count = 0
            
            for tag in tags:
                # Get all keys with this tag
                keys = await self._client.smembers(f"tag:{tag}")
                
                if keys:
                    # Delete all keys
                    pipe = self._client.pipeline()
                    for key in keys:
                        pipe.delete(key.decode())
                        pipe.delete(f"{key.decode()}:meta")
                    
                    # Delete tag index
                    pipe.delete(f"tag:{tag}")
                    
                    results = await pipe.execute()
                    deleted_count += sum(1 for r in results[::2] if r)  # Count successful deletions
            
            return deleted_count
            
        except Exception as e:
            raise CacheBackendError(f"Failed to delete by tags in Redis: {e}", backend="redis", operation="delete_by_tags")
    
    async def _update_metadata(self, key: str, entry: CacheEntry) -> None:
        """Update metadata for cache entry."""
        try:
            meta_data = {
                'access_count': entry.access_count,
                'last_accessed': entry.last_accessed.isoformat() if entry.last_accessed else ''
            }
            await self._client.hset(f"{key}:meta", mapping=meta_data)
        except Exception:
            # Ignore metadata update errors
            pass


class InMemoryCacheBackend(CacheBackendInterface):
    """In-memory cache backend implementation."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self.memory_config = config.get_backend_config(CacheBackend.MEMORY)
        
        self._cache: Dict[str, CacheEntry] = {}
        self._tag_index: Dict[str, set] = {}
        self._lock = threading.RLock() if self.memory_config.get("thread_safe", True) else None
        
        self._max_size = self.memory_config.get("max_size", 1000)
        self._max_memory_mb = self.memory_config.get("max_memory_mb", 100)
        self._cleanup_interval = self.memory_config.get("cleanup_interval", 60.0)
        
        self._current_memory_bytes = 0
        self._cleanup_task = None
    
    async def connect(self) -> None:
        """Connect to in-memory cache (start cleanup task)."""
        self._connected = True
        
        # Start cleanup task
        if self._cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def disconnect(self) -> None:
        """Disconnect from in-memory cache (stop cleanup task)."""
        self._connected = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from memory cache."""
        with self._lock if self._lock else nullcontext():
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            # Check if expired
            if entry.is_expired:
                self._remove_entry(key)
                return None
            
            # Update access info
            entry.mark_accessed()
            return entry
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in memory cache."""
        with self._lock if self._lock else nullcontext():
            # Calculate size
            import sys
            size_bytes = sys.getsizeof(value)
            
            # Check capacity limits
            if len(self._cache) >= self._max_size:
                self._evict_entries(1)
            
            if (self._current_memory_bytes + size_bytes) > (self._max_memory_mb * 1024 * 1024):
                # Try to free memory by evicting entries
                target_memory = self._max_memory_mb * 1024 * 1024 * 0.8  # 80% of max
                while self._current_memory_bytes > target_memory and self._cache:
                    self._evict_entries(1)
                
                # Check again
                if (self._current_memory_bytes + size_bytes) > (self._max_memory_mb * 1024 * 1024):
                    raise CacheCapacityError(
                        f"Cannot store entry: would exceed memory limit",
                        current_size=self._current_memory_bytes,
                        max_size=self._max_memory_mb * 1024 * 1024
                    )
            
            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)
            
            # Calculate expiration
            expires_at = None
            if ttl:
                expires_at = datetime.now(timezone.utc) + ttl
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                size_bytes=size_bytes,
                tags=tags or []
            )
            
            # Store entry
            self._cache[key] = entry
            self._current_memory_bytes += size_bytes
            
            # Update tag index
            for tag in entry.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(key)
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory cache."""
        with self._lock if self._lock else nullcontext():
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        with self._lock if self._lock else nullcontext():
            entry = self._cache.get(key)
            if entry and entry.is_expired:
                self._remove_entry(key)
                return False
            return entry is not None
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        with self._lock if self._lock else nullcontext():
            self._cache.clear()
            self._tag_index.clear()
            self._current_memory_bytes = 0
            return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        with self._lock if self._lock else nullcontext():
            return {
                'backend': 'memory',
                'total_entries': len(self._cache),
                'memory_usage_bytes': self._current_memory_bytes,
                'memory_usage_mb': self._current_memory_bytes / (1024 * 1024),
                'max_entries': self._max_size,
                'max_memory_mb': self._max_memory_mb,
                'tag_count': len(self._tag_index)
            }
    
    async def delete_by_tags(self, tags: List[str]) -> int:
        """Delete entries by tags."""
        with self._lock if self._lock else nullcontext():
            deleted_count = 0
            keys_to_delete = set()
            
            for tag in tags:
                if tag in self._tag_index:
                    keys_to_delete.update(self._tag_index[tag])
            
            for key in keys_to_delete:
                if key in self._cache:
                    self._remove_entry(key)
                    deleted_count += 1
            
            return deleted_count
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and update indexes."""
        entry = self._cache.pop(key, None)
        if entry:
            self._current_memory_bytes -= entry.size_bytes
            
            # Update tag index
            for tag in entry.tags:
                if tag in self._tag_index:
                    self._tag_index[tag].discard(key)
                    if not self._tag_index[tag]:
                        del self._tag_index[tag]
    
    def _evict_entries(self, count: int) -> None:
        """Evict entries using LRU strategy."""
        if not self._cache:
            return
        
        # Sort by last accessed time (LRU)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        for i in range(min(count, len(sorted_entries))):
            key = sorted_entries[i][0]
            self._remove_entry(key)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired entries."""
        while self._connected:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                if not self._connected:
                    break
                
                # Clean up expired entries
                with self._lock if self._lock else nullcontext():
                    expired_keys = [
                        key for key, entry in self._cache.items()
                        if entry.is_expired
                    ]
                    
                    for key in expired_keys:
                        self._remove_entry(key)
                
            except asyncio.CancelledError:
                break
            except Exception:
                # Continue cleanup loop even if there are errors
                continue


# Memcached backend placeholder
class MemcachedCacheBackend(CacheBackendInterface):
    """Memcached cache backend implementation."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        if not MEMCACHED_AVAILABLE:
            raise CacheBackendError("Memcached is not available. Install aiomcache package.")
        
        self.memcached_config = config.get_backend_config(CacheBackend.MEMCACHED)
        self._client = None
    
    async def connect(self) -> None:
        """Connect to Memcached."""
        # Implementation would go here
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from Memcached."""
        self._connected = False
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get value from Memcached."""
        # Implementation would go here
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in Memcached."""
        # Implementation would go here
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from Memcached."""
        # Implementation would go here
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Memcached."""
        # Implementation would go here
        return False
    
    async def clear(self) -> bool:
        """Clear all cache entries."""
        # Implementation would go here
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Memcached statistics."""
        # Implementation would go here
        return {'backend': 'memcached'}


# Context manager for thread safety
class nullcontext:
    """Null context manager for when no locking is needed."""
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
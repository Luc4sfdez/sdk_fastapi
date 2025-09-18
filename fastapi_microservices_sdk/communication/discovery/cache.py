"""
Service discovery caching layer with TTL support.

This module provides caching capabilities for service discovery results
to reduce load on service discovery backends and improve performance.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

from .base import ServiceInstance


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    
    data: List[ServiceInstance]
    created_at: float = field(default_factory=time.time)
    ttl: int = 60  # seconds
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """Get the age of the cache entry in seconds."""
        return time.time() - self.created_at
    
    def access(self) -> List[ServiceInstance]:
        """Access the cached data and update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data.copy()


class ServiceDiscoveryCache:
    """Cache for service discovery results with TTL and LRU eviction."""
    
    def __init__(
        self,
        ttl: int = 60,
        max_size: int = 1000,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.ttl = ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU eviction
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "cleanups": 0,
            "total_requests": 0
        }
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                print(f"Error in cache cleanup: {e}")
    
    async def _cleanup_expired(self) -> None:
        """Remove expired entries from the cache."""
        async with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            
            if expired_keys:
                self._stats["cleanups"] += len(expired_keys)
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entries to make space."""
        while len(self._cache) >= self.max_size and self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                self._stats["evictions"] += 1
    
    def _update_access_order(self, key: str) -> None:
        """Update the access order for LRU tracking."""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def get_services(self, cache_key: str) -> Optional[List[ServiceInstance]]:
        """Get cached service instances."""
        async with self._lock:
            self._stats["total_requests"] += 1
            
            if cache_key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._stats["misses"] += 1
                return None
            
            # Update access order and return data
            self._update_access_order(cache_key)
            self._stats["hits"] += 1
            return entry.access()
    
    async def set_services(
        self,
        cache_key: str,
        instances: List[ServiceInstance],
        ttl: Optional[int] = None
    ) -> None:
        """Cache service instances."""
        async with self._lock:
            # Evict LRU entries if needed
            await self._evict_lru()
            
            # Create cache entry
            entry_ttl = ttl if ttl is not None else self.ttl
            entry = CacheEntry(
                data=instances.copy(),
                ttl=entry_ttl
            )
            
            # Store in cache
            self._cache[cache_key] = entry
            self._update_access_order(cache_key)
    
    def invalidate_service(self, service_name: str) -> None:
        """Invalidate all cache entries for a specific service."""
        keys_to_remove = []
        
        for key in self._cache.keys():
            if key.startswith(f"{service_name}:") or key == service_name:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
    
    def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache entries matching a pattern."""
        keys_to_remove = []
        
        for key in self._cache.keys():
            if pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["total_requests"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": round(hit_rate, 2),
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "cleanups": self._stats["cleanups"],
            "total_requests": total_requests,
            "ttl": self.ttl,
            "cleanup_interval": self.cleanup_interval
        }
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        cache_info = {}
        
        for key, entry in self._cache.items():
            cache_info[key] = {
                "size": len(entry.data),
                "age": round(entry.age, 2),
                "ttl": entry.ttl,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
                "is_expired": entry.is_expired
            }
        
        return cache_info
    
    def get_service_cache_keys(self, service_name: str) -> List[str]:
        """Get all cache keys for a specific service."""
        return [key for key in self._cache.keys() if key.startswith(f"{service_name}:") or key == service_name]
    
    async def preload_services(self, service_data: Dict[str, List[ServiceInstance]]) -> None:
        """Preload multiple services into the cache."""
        async with self._lock:
            for service_name, instances in service_data.items():
                cache_key = service_name
                await self.set_services(cache_key, instances)
    
    def set_ttl(self, ttl: int) -> None:
        """Update the default TTL for new cache entries."""
        self.ttl = ttl
    
    def set_max_size(self, max_size: int) -> None:
        """Update the maximum cache size."""
        self.max_size = max_size
    
    async def stop(self) -> None:
        """Stop the cache and cleanup background tasks."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.clear()
    
    def __len__(self) -> int:
        """Get the number of cached entries."""
        return len(self._cache)
    
    def __contains__(self, cache_key: str) -> bool:
        """Check if a cache key exists and is not expired."""
        if cache_key not in self._cache:
            return False
        
        entry = self._cache[cache_key]
        if entry.is_expired:
            # Clean up expired entry
            del self._cache[cache_key]
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            return False
        
        return True


class ServiceInstanceCache:
    """Specialized cache for individual service instances."""
    
    def __init__(self, ttl: int = 300):  # 5 minutes default
        self.ttl = ttl
        self._instances: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    def _get_instance_key(self, service_name: str, instance_id: str) -> str:
        """Generate cache key for a service instance."""
        return f"{service_name}:{instance_id}"
    
    async def get_instance(self, service_name: str, instance_id: str) -> Optional[ServiceInstance]:
        """Get a cached service instance."""
        async with self._lock:
            key = self._get_instance_key(service_name, instance_id)
            
            if key not in self._instances:
                return None
            
            entry = self._instances[key]
            if entry.is_expired:
                del self._instances[key]
                return None
            
            # Return the first (and only) instance
            instances = entry.access()
            return instances[0] if instances else None
    
    async def set_instance(self, instance: ServiceInstance, ttl: Optional[int] = None) -> None:
        """Cache a service instance."""
        async with self._lock:
            key = self._get_instance_key(instance.service_name, instance.instance_id)
            entry_ttl = ttl if ttl is not None else self.ttl
            
            entry = CacheEntry(
                data=[instance],
                ttl=entry_ttl
            )
            
            self._instances[key] = entry
    
    def invalidate_instance(self, service_name: str, instance_id: str) -> None:
        """Invalidate a specific service instance."""
        key = self._get_instance_key(service_name, instance_id)
        self._instances.pop(key, None)
    
    def invalidate_service_instances(self, service_name: str) -> None:
        """Invalidate all instances for a service."""
        keys_to_remove = []
        prefix = f"{service_name}:"
        
        for key in self._instances.keys():
            if key.startswith(prefix):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._instances[key]
    
    def clear(self) -> None:
        """Clear all cached instances."""
        self._instances.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_instances = len(self._instances)
        expired_count = sum(1 for entry in self._instances.values() if entry.is_expired)
        
        return {
            "total_instances": total_instances,
            "expired_instances": expired_count,
            "active_instances": total_instances - expired_count,
            "ttl": self.ttl
        }
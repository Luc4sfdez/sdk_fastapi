# fastapi-microservices-sdk/fastapi_microservices_sdk/core/decorators/cache.py
"""
Cache decorator for FastAPI Microservices SDK.
"""

import asyncio
import functools
import hashlib
import json
import time
from typing import Callable, Any, Optional, Dict


# Simple in-memory cache
_cache: Dict[str, Dict[str, Any]] = {}


def cache(
    ttl: int = 300,  # 5 minutes default
    key_prefix: str = "",
    serialize_args: bool = True
):
    """
    Simple cache decorator for functions and coroutines.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        serialize_args: Whether to serialize arguments for cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix, serialize_args)
            
            # Check cache
            if cache_key in _cache:
                cache_entry = _cache[cache_key]
                if time.time() < cache_entry["expires_at"]:
                    return cache_entry["value"]
                else:
                    # Expired, remove from cache
                    del _cache[cache_key]
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            _cache[cache_key] = {
                "value": result,
                "expires_at": time.time() + ttl
            }
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix, serialize_args)
            
            # Check cache
            if cache_key in _cache:
                cache_entry = _cache[cache_key]
                if time.time() < cache_entry["expires_at"]:
                    return cache_entry["value"]
                else:
                    # Expired, remove from cache
                    del _cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = {
                "value": result,
                "expires_at": time.time() + ttl
            }
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def _generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: str,
    serialize_args: bool
) -> str:
    """Generate a cache key for the function call."""
    key_parts = [key_prefix, func.__name__]
    
    if serialize_args:
        try:
            # Try to serialize arguments
            args_str = json.dumps(args, sort_keys=True, default=str)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            key_parts.extend([args_str, kwargs_str])
        except (TypeError, ValueError):
            # Fallback to string representation
            key_parts.extend([str(args), str(kwargs)])
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def clear_cache(pattern: Optional[str] = None):
    """
    Clear cache entries.
    
    Args:
        pattern: If provided, only clear keys containing this pattern
    """
    if pattern is None:
        _cache.clear()
    else:
        keys_to_remove = [key for key in _cache.keys() if pattern in key]
        for key in keys_to_remove:
            del _cache[key]


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    current_time = time.time()
    expired_count = sum(1 for entry in _cache.values() if current_time >= entry["expires_at"])
    
    return {
        "total_entries": len(_cache),
        "expired_entries": expired_count,
        "active_entries": len(_cache) - expired_count
    }
"""
Database Caching Layer for FastAPI Microservices SDK.

This module provides intelligent caching capabilities for database operations
with support for multiple caching backends, strategies, and invalidation policies.

Features:
- Multi-backend caching (Redis, Memcached, In-Memory)
- Intelligent cache strategies (LRU, LFU, TTL-based)
- Automatic invalidation policies
- Distributed caching support
- Cache warming and preloading
- Performance optimization
- Cache analytics and monitoring
- Integration with database operations

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .config import (
    CacheConfig,
    CacheBackend,
    CacheStrategy,
    InvalidationPolicy,
    SerializationFormat
)
from .manager import (
    CacheManager,
    CacheEntry,
    CacheStats
)
from .backends import (
    CacheBackendInterface,
    RedisCacheBackend,
    MemcachedCacheBackend,
    InMemoryCacheBackend
)
from .strategies import (
    CacheStrategyInterface,
    LRUStrategy,
    LFUStrategy,
    TTLStrategy,
    AdaptiveStrategy
)
from .invalidation import (
    InvalidationManager,
    InvalidationRule,
    TagBasedInvalidation,
    TimeBasedInvalidation,
    EventBasedInvalidation
)
from .serializers import (
    SerializerInterface,
    JSONSerializer,
    PickleSerializer,
    CompressedSerializer
)
from .exceptions import (
    CacheError,
    CacheBackendError,
    CacheSerializationError,
    CacheInvalidationError,
    CacheConfigurationError
)

__all__ = [
    # Configuration
    "CacheConfig",
    "CacheBackend",
    "CacheStrategy",
    "InvalidationPolicy",
    "SerializationFormat",
    
    # Core Manager
    "CacheManager",
    "CacheEntry",
    "CacheStats",
    
    # Backends
    "CacheBackendInterface",
    "RedisCacheBackend",
    "MemcachedCacheBackend",
    "InMemoryCacheBackend",
    
    # Strategies
    "CacheStrategyInterface",
    "LRUStrategy",
    "LFUStrategy",
    "TTLStrategy",
    "AdaptiveStrategy",
    
    # Invalidation
    "InvalidationManager",
    "InvalidationRule",
    "TagBasedInvalidation",
    "TimeBasedInvalidation",
    "EventBasedInvalidation",
    
    # Serialization
    "SerializerInterface",
    "JSONSerializer",
    "PickleSerializer",
    "CompressedSerializer",
    
    # Exceptions
    "CacheError",
    "CacheBackendError",
    "CacheSerializationError",
    "CacheInvalidationError",
    "CacheConfigurationError",
]
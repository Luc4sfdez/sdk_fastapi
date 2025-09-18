"""
Caching configuration for the database caching system.

This module provides configuration classes for managing caching settings
and behavior across different backends and strategies.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from datetime import timedelta
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..config import DatabaseEngine


class CacheBackend(Enum):
    """Available cache backends."""
    REDIS = "redis"
    MEMCACHED = "memcached"
    MEMORY = "memory"
    HYBRID = "hybrid"


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    ADAPTIVE = "adaptive"  # Adaptive strategy based on usage patterns
    FIFO = "fifo"  # First In, First Out


class InvalidationPolicy(Enum):
    """Cache invalidation policies."""
    MANUAL = "manual"
    TIME_BASED = "time_based"
    TAG_BASED = "tag_based"
    EVENT_BASED = "event_based"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"


class SerializationFormat(Enum):
    """Serialization formats for cached data."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    COMPRESSED_JSON = "compressed_json"
    COMPRESSED_PICKLE = "compressed_pickle"


class CacheConfig(BaseModel):
    """Configuration for database caching system."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable caching system"
    )
    
    default_backend: CacheBackend = Field(
        default=CacheBackend.REDIS,
        description="Default cache backend"
    )
    
    # Backend configurations
    redis_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
            "ssl": False,
            "connection_pool_size": 10,
            "socket_timeout": 5.0,
            "socket_connect_timeout": 5.0,
            "retry_on_timeout": True,
            "health_check_interval": 30
        },
        description="Redis backend configuration"
    )
    
    memcached_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "servers": ["localhost:11211"],
            "binary": True,
            "behaviors": {
                "tcp_nodelay": True,
                "ketama": True
            },
            "socket_timeout": 3.0,
            "connect_timeout": 3.0,
            "retry_timeout": 2.0
        },
        description="Memcached backend configuration"
    )
    
    memory_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_size": 1000,
            "max_memory_mb": 100,
            "cleanup_interval": 60.0,
            "thread_safe": True
        },
        description="In-memory backend configuration"
    )
    
    # Cache strategy settings
    default_strategy: CacheStrategy = Field(
        default=CacheStrategy.LRU,
        description="Default cache eviction strategy"
    )
    
    default_ttl: timedelta = Field(
        default=timedelta(hours=1),
        description="Default time-to-live for cache entries"
    )
    
    max_key_size: int = Field(
        default=250,
        description="Maximum cache key size in characters"
    )
    
    max_value_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum cache value size in bytes"
    )
    
    # Serialization settings
    serialization_format: SerializationFormat = Field(
        default=SerializationFormat.JSON,
        description="Default serialization format"
    )
    
    compression_enabled: bool = Field(
        default=True,
        description="Enable compression for large values"
    )
    
    compression_threshold: int = Field(
        default=1024,  # 1KB
        description="Minimum size in bytes to trigger compression"
    )
    
    # Invalidation settings
    invalidation_policy: InvalidationPolicy = Field(
        default=InvalidationPolicy.TIME_BASED,
        description="Default invalidation policy"
    )
    
    invalidation_batch_size: int = Field(
        default=100,
        description="Batch size for bulk invalidation operations"
    )
    
    # Performance settings
    async_operations: bool = Field(
        default=True,
        description="Enable asynchronous cache operations"
    )
    
    connection_pool_size: int = Field(
        default=10,
        description="Connection pool size for cache backends"
    )
    
    operation_timeout: float = Field(
        default=5.0,
        description="Timeout for cache operations in seconds"
    )
    
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed operations"
    )
    
    retry_delay: float = Field(
        default=0.1,
        description="Delay between retry attempts in seconds"
    )
    
    # Monitoring settings
    metrics_enabled: bool = Field(
        default=True,
        description="Enable cache metrics collection"
    )
    
    metrics_interval: float = Field(
        default=60.0,
        description="Metrics collection interval in seconds"
    )
    
    # Warming settings
    cache_warming_enabled: bool = Field(
        default=False,
        description="Enable cache warming on startup"
    )
    
    warming_batch_size: int = Field(
        default=50,
        description="Batch size for cache warming operations"
    )
    
    warming_concurrency: int = Field(
        default=5,
        description="Number of concurrent warming operations"
    )
    
    # Database-specific settings
    database_cache_configs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Database-specific cache configurations"
    )
    
    # Engine-specific settings
    engine_settings: Dict[DatabaseEngine, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Engine-specific cache settings"
    )
    
    @validator('default_ttl')
    def validate_ttl(cls, v):
        """Validate TTL value."""
        if isinstance(v, (int, float)):
            v = timedelta(seconds=v)
        elif isinstance(v, str):
            # Parse string format like "1h", "30m", "3600s"
            if v.endswith('s'):
                v = timedelta(seconds=int(v[:-1]))
            elif v.endswith('m'):
                v = timedelta(minutes=int(v[:-1]))
            elif v.endswith('h'):
                v = timedelta(hours=int(v[:-1]))
            elif v.endswith('d'):
                v = timedelta(days=int(v[:-1]))
            else:
                v = timedelta(seconds=int(v))
        return v
    
    @validator('max_key_size', 'max_value_size', 'compression_threshold')
    def validate_positive_int(cls, v):
        """Validate positive integer values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @validator('operation_timeout', 'retry_delay', 'metrics_interval')
    def validate_positive_float(cls, v):
        """Validate positive float values."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @validator('retry_attempts')
    def validate_retry_attempts(cls, v):
        """Validate retry attempts."""
        if v < 0:
            raise ValueError("Retry attempts must be non-negative")
        return v
    
    def get_database_config(self, database_name: str) -> Dict[str, Any]:
        """
        Get database-specific cache configuration.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Database-specific configuration
        """
        return self.database_cache_configs.get(database_name, {})
    
    def set_database_config(self, database_name: str, config: Dict[str, Any]) -> None:
        """
        Set database-specific cache configuration.
        
        Args:
            database_name: Name of the database
            config: Configuration dictionary
        """
        self.database_cache_configs[database_name] = config
    
    def get_engine_setting(self, engine: DatabaseEngine, key: str, default: Any = None) -> Any:
        """
        Get engine-specific cache setting.
        
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
        Set engine-specific cache setting.
        
        Args:
            engine: Database engine
            key: Setting key
            value: Setting value
        """
        if engine not in self.engine_settings:
            self.engine_settings[engine] = {}
        self.engine_settings[engine][key] = value
    
    def get_backend_config(self, backend: CacheBackend) -> Dict[str, Any]:
        """
        Get configuration for specific cache backend.
        
        Args:
            backend: Cache backend type
            
        Returns:
            Backend configuration
        """
        if backend == CacheBackend.REDIS:
            return self.redis_config
        elif backend == CacheBackend.MEMCACHED:
            return self.memcached_config
        elif backend == CacheBackend.MEMORY:
            return self.memory_config
        else:
            return {}
    
    def get_cache_key_prefix(self, database_name: str, table_name: Optional[str] = None) -> str:
        """
        Generate cache key prefix for database and table.
        
        Args:
            database_name: Name of the database
            table_name: Name of the table (optional)
            
        Returns:
            Cache key prefix
        """
        prefix = f"db:{database_name}"
        if table_name:
            prefix += f":table:{table_name}"
        return prefix
    
    def get_ttl_for_query_type(self, query_type: str) -> timedelta:
        """
        Get TTL based on query type.
        
        Args:
            query_type: Type of query (SELECT, INSERT, etc.)
            
        Returns:
            TTL for the query type
        """
        # Different TTLs for different query types
        ttl_mapping = {
            'SELECT': self.default_ttl,
            'COUNT': self.default_ttl * 2,  # Count queries can be cached longer
            'AGGREGATE': self.default_ttl * 1.5,  # Aggregate queries
            'LOOKUP': timedelta(hours=6),  # Lookup tables
            'REFERENCE': timedelta(days=1),  # Reference data
        }
        
        return ttl_mapping.get(query_type.upper(), self.default_ttl)
    
    def should_cache_query(self, query: str, execution_time: float) -> bool:
        """
        Determine if a query should be cached based on various criteria.
        
        Args:
            query: SQL query string
            execution_time: Query execution time in seconds
            
        Returns:
            True if query should be cached
        """
        # Don't cache very fast queries (overhead not worth it)
        if execution_time < 0.01:
            return False
        
        # Don't cache queries with non-deterministic functions
        non_deterministic = ['NOW()', 'CURRENT_TIMESTAMP', 'RAND()', 'RANDOM()', 'UUID()']
        query_upper = query.upper()
        
        for func in non_deterministic:
            if func in query_upper:
                return False
        
        # Don't cache write operations
        write_operations = ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']
        for op in write_operations:
            if query_upper.strip().startswith(op):
                return False
        
        return True
    
    def get_cache_tags_for_query(self, query: str, database_name: str) -> List[str]:
        """
        Generate cache tags for a query to enable tag-based invalidation.
        
        Args:
            query: SQL query string
            database_name: Name of the database
            
        Returns:
            List of cache tags
        """
        tags = [f"db:{database_name}"]
        
        # Extract table names from query (simple regex-based extraction)
        import re
        
        # Match FROM and JOIN clauses
        table_patterns = [
            r'FROM\s+([\w\.]+)',
            r'JOIN\s+([\w\.]+)',
            r'UPDATE\s+([\w\.]+)',
            r'INSERT\s+INTO\s+([\w\.]+)',
            r'DELETE\s+FROM\s+([\w\.]+)'
        ]
        
        query_upper = query.upper()
        for pattern in table_patterns:
            matches = re.findall(pattern, query_upper)
            for match in matches:
                table_name = match.strip('`"[]')
                tags.append(f"table:{table_name}")
        
        return list(set(tags))  # Remove duplicates
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
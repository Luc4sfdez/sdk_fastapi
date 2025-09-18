"""
Caching-specific exceptions for the database caching system.

This module defines custom exceptions for caching operations,
providing detailed error information and context.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import DatabaseError


class CacheError(DatabaseError):
    """Base exception for cache-related errors."""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        backend: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error=original_error, context=context)
        self.cache_key = cache_key
        self.backend = backend


class CacheBackendError(CacheError):
    """Exception raised when cache backend operations fail."""
    
    def __init__(
        self,
        message: str,
        backend: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, backend=backend, **kwargs)
        self.operation = operation


class CacheConnectionError(CacheBackendError):
    """Exception raised when cache backend connection fails."""
    
    def __init__(
        self,
        message: str,
        backend: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, backend=backend, operation="connect", **kwargs)
        self.host = host
        self.port = port


class CacheSerializationError(CacheError):
    """Exception raised during cache serialization/deserialization."""
    
    def __init__(
        self,
        message: str,
        serializer: Optional[str] = None,
        operation: Optional[str] = None,  # 'serialize' or 'deserialize'
        data_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.serializer = serializer
        self.operation = operation
        self.data_type = data_type


class CacheInvalidationError(CacheError):
    """Exception raised during cache invalidation operations."""
    
    def __init__(
        self,
        message: str,
        invalidation_type: Optional[str] = None,
        affected_keys: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.invalidation_type = invalidation_type
        self.affected_keys = affected_keys


class CacheConfigurationError(CacheError):
    """Exception raised for cache configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class CacheKeyError(CacheError):
    """Exception raised for invalid cache keys."""
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, cache_key=cache_key, **kwargs)
        self.reason = reason


class CacheTimeoutError(CacheError):
    """Exception raised when cache operations timeout."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_duration: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.operation = operation
        self.timeout_duration = timeout_duration


class CacheCapacityError(CacheError):
    """Exception raised when cache capacity limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        current_size: Optional[int] = None,
        max_size: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.current_size = current_size
        self.max_size = max_size


class CacheConsistencyError(CacheError):
    """Exception raised when cache consistency issues are detected."""
    
    def __init__(
        self,
        message: str,
        inconsistent_keys: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.inconsistent_keys = inconsistent_keys or []
"""
Serialization system for cache data.

This module provides various serialization strategies for caching data
including JSON, Pickle, MessagePack, and compressed formats.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import json
import pickle
import gzip
import zlib
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import UUID

from .config import SerializationFormat
from .exceptions import CacheSerializationError

# Optional imports
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    msgpack = None
    MSGPACK_AVAILABLE = False

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    orjson = None
    ORJSON_AVAILABLE = False


class SerializerInterface(ABC):
    """Abstract interface for cache serializers."""
    
    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize data to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to data."""
        pass
    
    @property
    @abstractmethod
    def format_name(self) -> str:
        """Get serializer format name."""
        pass
    
    @property
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        return False


class JSONSerializer(SerializerInterface):
    """JSON serializer with support for common Python types."""
    
    def __init__(self, ensure_ascii: bool = False, indent: Optional[int] = None):
        self.ensure_ascii = ensure_ascii
        self.indent = indent
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON bytes."""
        try:
            if ORJSON_AVAILABLE:
                # Use orjson for better performance
                return orjson.dumps(data, default=self._json_serializer)
            else:
                # Use standard json
                json_str = json.dumps(
                    data,
                    default=self._json_serializer,
                    ensure_ascii=self.ensure_ascii,
                    indent=self.indent,
                    separators=(',', ':') if self.indent is None else None
                )
                return json_str.encode('utf-8')
        
        except Exception as e:
            raise CacheSerializationError(
                f"JSON serialization failed: {e}",
                serializer="json",
                operation="serialize",
                data_type=type(data).__name__,
                original_error=e
            )
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to data."""
        try:
            if ORJSON_AVAILABLE:
                return orjson.loads(data)
            else:
                return json.loads(data.decode('utf-8'))
        
        except Exception as e:
            raise CacheSerializationError(
                f"JSON deserialization failed: {e}",
                serializer="json",
                operation="deserialize",
                original_error=e
            )
    
    @property
    def format_name(self) -> str:
        """Get serializer format name."""
        return "json"
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for Python objects."""
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, date):
            return {
                '__type__': 'date',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, time):
            return {
                '__type__': 'time',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, timedelta):
            return {
                '__type__': 'timedelta',
                '__value__': obj.total_seconds()
            }
        elif isinstance(obj, Decimal):
            return {
                '__type__': 'decimal',
                '__value__': str(obj)
            }
        elif isinstance(obj, UUID):
            return {
                '__type__': 'uuid',
                '__value__': str(obj)
            }
        elif isinstance(obj, set):
            return {
                '__type__': 'set',
                '__value__': list(obj)
            }
        elif isinstance(obj, frozenset):
            return {
                '__type__': 'frozenset',
                '__value__': list(obj)
            }
        elif hasattr(obj, '__dict__'):
            # Handle custom objects
            return {
                '__type__': 'object',
                '__class__': f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                '__value__': obj.__dict__
            }
        
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class PickleSerializer(SerializerInterface):
    """Pickle serializer for Python objects."""
    
    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data using pickle."""
        try:
            return pickle.dumps(data, protocol=self.protocol)
        except Exception as e:
            raise CacheSerializationError(
                f"Pickle serialization failed: {e}",
                serializer="pickle",
                operation="serialize",
                data_type=type(data).__name__,
                original_error=e
            )
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize pickle bytes to data."""
        try:
            return pickle.loads(data)
        except Exception as e:
            raise CacheSerializationError(
                f"Pickle deserialization failed: {e}",
                serializer="pickle",
                operation="deserialize",
                original_error=e
            )
    
    @property
    def format_name(self) -> str:
        """Get serializer format name."""
        return "pickle"


class MessagePackSerializer(SerializerInterface):
    """MessagePack serializer for efficient binary serialization."""
    
    def __init__(self, use_bin_type: bool = True):
        if not MSGPACK_AVAILABLE:
            raise CacheSerializationError("MessagePack is not available. Install msgpack package.")
        
        self.use_bin_type = use_bin_type
    
    def serialize(self, data: Any) -> bytes:
        """Serialize data using MessagePack."""
        try:
            return msgpack.packb(
                data,
                default=self._msgpack_serializer,
                use_bin_type=self.use_bin_type
            )
        except Exception as e:
            raise CacheSerializationError(
                f"MessagePack serialization failed: {e}",
                serializer="msgpack",
                operation="serialize",
                data_type=type(data).__name__,
                original_error=e
            )
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize MessagePack bytes to data."""
        try:
            return msgpack.unpackb(
                data,
                object_hook=self._msgpack_deserializer,
                raw=False
            )
        except Exception as e:
            raise CacheSerializationError(
                f"MessagePack deserialization failed: {e}",
                serializer="msgpack",
                operation="deserialize",
                original_error=e
            )
    
    @property
    def format_name(self) -> str:
        """Get serializer format name."""
        return "msgpack"
    
    def _msgpack_serializer(self, obj: Any) -> Any:
        """Custom MessagePack serializer for Python objects."""
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, date):
            return {
                '__type__': 'date',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, time):
            return {
                '__type__': 'time',
                '__value__': obj.isoformat()
            }
        elif isinstance(obj, timedelta):
            return {
                '__type__': 'timedelta',
                '__value__': obj.total_seconds()
            }
        elif isinstance(obj, Decimal):
            return {
                '__type__': 'decimal',
                '__value__': str(obj)
            }
        elif isinstance(obj, UUID):
            return {
                '__type__': 'uuid',
                '__value__': str(obj)
            }
        elif isinstance(obj, set):
            return {
                '__type__': 'set',
                '__value__': list(obj)
            }
        elif isinstance(obj, frozenset):
            return {
                '__type__': 'frozenset',
                '__value__': list(obj)
            }
        
        raise TypeError(f"Object of type {type(obj)} is not MessagePack serializable")
    
    def _msgpack_deserializer(self, obj: Dict[str, Any]) -> Any:
        """Custom MessagePack deserializer for Python objects."""
        if isinstance(obj, dict) and '__type__' in obj:
            obj_type = obj['__type__']
            value = obj['__value__']
            
            if obj_type == 'datetime':
                return datetime.fromisoformat(value)
            elif obj_type == 'date':
                return date.fromisoformat(value)
            elif obj_type == 'time':
                return time.fromisoformat(value)
            elif obj_type == 'timedelta':
                return timedelta(seconds=value)
            elif obj_type == 'decimal':
                return Decimal(value)
            elif obj_type == 'uuid':
                return UUID(value)
            elif obj_type == 'set':
                return set(value)
            elif obj_type == 'frozenset':
                return frozenset(value)
        
        return obj


class CompressedSerializer(SerializerInterface):
    """Compressed serializer wrapper for other serializers."""
    
    def __init__(
        self,
        base_serializer: SerializerInterface,
        compression_method: str = 'gzip',
        compression_level: int = 6,
        compression_threshold: int = 1024
    ):
        self.base_serializer = base_serializer
        self.compression_method = compression_method
        self.compression_level = compression_level
        self.compression_threshold = compression_threshold
        
        # Validate compression method
        if compression_method not in ['gzip', 'zlib']:
            raise CacheSerializationError(f"Unsupported compression method: {compression_method}")
    
    def serialize(self, data: Any) -> bytes:
        """Serialize and optionally compress data."""
        try:
            # First serialize with base serializer
            serialized_data = self.base_serializer.serialize(data)
            
            # Compress if data is large enough
            if len(serialized_data) >= self.compression_threshold:
                if self.compression_method == 'gzip':
                    compressed_data = gzip.compress(serialized_data, compresslevel=self.compression_level)
                elif self.compression_method == 'zlib':
                    compressed_data = zlib.compress(serialized_data, level=self.compression_level)
                else:
                    compressed_data = serialized_data
                
                # Add compression header
                return b'COMPRESSED:' + self.compression_method.encode() + b':' + compressed_data
            else:
                # Add uncompressed header
                return b'UNCOMPRESSED:' + serialized_data
        
        except Exception as e:
            raise CacheSerializationError(
                f"Compressed serialization failed: {e}",
                serializer=f"compressed_{self.base_serializer.format_name}",
                operation="serialize",
                data_type=type(data).__name__,
                original_error=e
            )
    
    def deserialize(self, data: bytes) -> Any:
        """Decompress and deserialize data."""
        try:
            # Check compression header
            if data.startswith(b'COMPRESSED:'):
                # Extract compression method and data
                header_end = data.find(b':', 11)  # Find second colon
                if header_end == -1:
                    raise CacheSerializationError("Invalid compressed data format")
                
                compression_method = data[11:header_end].decode()
                compressed_data = data[header_end + 1:]
                
                # Decompress
                if compression_method == 'gzip':
                    decompressed_data = gzip.decompress(compressed_data)
                elif compression_method == 'zlib':
                    decompressed_data = zlib.decompress(compressed_data)
                else:
                    raise CacheSerializationError(f"Unknown compression method: {compression_method}")
                
                # Deserialize
                return self.base_serializer.deserialize(decompressed_data)
            
            elif data.startswith(b'UNCOMPRESSED:'):
                # Extract uncompressed data
                uncompressed_data = data[13:]  # Skip 'UNCOMPRESSED:' prefix
                return self.base_serializer.deserialize(uncompressed_data)
            
            else:
                # Assume legacy uncompressed format
                return self.base_serializer.deserialize(data)
        
        except Exception as e:
            raise CacheSerializationError(
                f"Compressed deserialization failed: {e}",
                serializer=f"compressed_{self.base_serializer.format_name}",
                operation="deserialize",
                original_error=e
            )
    
    @property
    def format_name(self) -> str:
        """Get serializer format name."""
        return f"compressed_{self.base_serializer.format_name}"
    
    @property
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        return True


def create_serializer(
    format_type: SerializationFormat,
    compression_enabled: bool = False,
    compression_threshold: int = 1024,
    **kwargs
) -> SerializerInterface:
    """
    Factory function to create serializer instances.
    
    Args:
        format_type: Type of serialization format
        compression_enabled: Enable compression wrapper
        compression_threshold: Minimum size for compression
        **kwargs: Additional serializer-specific arguments
        
    Returns:
        Serializer instance
        
    Raises:
        CacheSerializationError: If format type is not supported
    """
    # Create base serializer
    if format_type == SerializationFormat.JSON:
        base_serializer = JSONSerializer(**kwargs)
    elif format_type == SerializationFormat.PICKLE:
        base_serializer = PickleSerializer(**kwargs)
    elif format_type == SerializationFormat.MSGPACK:
        base_serializer = MessagePackSerializer(**kwargs)
    elif format_type == SerializationFormat.COMPRESSED_JSON:
        base_serializer = JSONSerializer(**kwargs)
        compression_enabled = True
    elif format_type == SerializationFormat.COMPRESSED_PICKLE:
        base_serializer = PickleSerializer(**kwargs)
        compression_enabled = True
    else:
        raise CacheSerializationError(f"Unsupported serialization format: {format_type}")
    
    # Wrap with compression if enabled
    if compression_enabled:
        return CompressedSerializer(
            base_serializer=base_serializer,
            compression_threshold=compression_threshold,
            **{k: v for k, v in kwargs.items() if k.startswith('compression_')}
        )
    
    return base_serializer


def get_serializer_for_data(data: Any) -> SerializerInterface:
    """
    Get optimal serializer for given data type.
    
    Args:
        data: Data to be serialized
        
    Returns:
        Optimal serializer for the data type
    """
    # Simple heuristics for serializer selection
    if isinstance(data, (dict, list, str, int, float, bool, type(None))):
        # JSON-serializable types
        return JSONSerializer()
    elif hasattr(data, '__dict__') or isinstance(data, (set, frozenset, tuple)):
        # Complex Python objects
        return PickleSerializer()
    else:
        # Default to pickle for unknown types
        return PickleSerializer()


def estimate_serialized_size(data: Any, serializer: SerializerInterface) -> int:
    """
    Estimate serialized size without actually serializing.
    
    Args:
        data: Data to estimate size for
        serializer: Serializer to use
        
    Returns:
        Estimated size in bytes
    """
    try:
        # For accurate estimation, we need to serialize
        # This is a trade-off between accuracy and performance
        serialized = serializer.serialize(data)
        return len(serialized)
    except Exception:
        # Fallback to rough estimation
        import sys
        return sys.getsizeof(data)
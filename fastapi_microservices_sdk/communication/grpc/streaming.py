"""
gRPC Streaming Support Module

This module provides comprehensive streaming support for gRPC services including:
- Streaming patterns (unary, server, client, bidirectional)
- Streaming error handling and backpressure management
- Streaming interceptors for authentication and rate limiting
- Streaming metrics and performance monitoring

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, AsyncGenerator, AsyncIterator, Callable, Dict, List, Optional, 
    Union, TypeVar, Generic, Tuple, Set
)
import json
from collections import defaultdict, deque
import weakref

# Optional gRPC imports with graceful fallback
try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

# Internal imports
from ..exceptions import CommunicationError
from ..logging import CommunicationLogger

# Type variables for generic streaming
T = TypeVar('T')
U = TypeVar('U')

logger = CommunicationLogger("grpc.streaming")


class StreamingPattern(str, Enum):
    """gRPC streaming patterns."""
    UNARY = "unary"
    SERVER_STREAMING = "server_streaming"
    CLIENT_STREAMING = "client_streaming"
    BIDIRECTIONAL_STREAMING = "bidirectional_streaming"


class StreamingState(str, Enum):
    """Streaming connection states."""
    IDLE = "idle"
    ACTIVE = "active"
    BACKPRESSURE = "backpressure"
    ERROR = "error"
    CLOSED = "closed"


class BackpressureStrategy(str, Enum):
    """Backpressure handling strategies."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    BUFFER_UNLIMITED = "buffer_unlimited"


@dataclass
class StreamingMetrics:
    """Metrics for streaming operations."""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    backpressure_events: int = 0
    connection_duration: float = 0.0
    average_latency: float = 0.0
    peak_throughput: float = 0.0
    buffer_size: int = 0
    dropped_messages: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'errors': self.errors,
            'backpressure_events': self.backpressure_events,
            'connection_duration': self.connection_duration,
            'average_latency': self.average_latency,
            'peak_throughput': self.peak_throughput,
            'buffer_size': self.buffer_size,
            'dropped_messages': self.dropped_messages
        }


@dataclass
class StreamingConfig:
    """Configuration for streaming operations."""
    max_buffer_size: int = 1000
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST
    enable_metrics: bool = True
    enable_authentication: bool = True
    enable_rate_limiting: bool = True
    max_message_size: int = 4 * 1024 * 1024  # 4MB
    keepalive_timeout: int = 30
    keepalive_interval: int = 5
    max_concurrent_streams: int = 100
    stream_timeout: int = 300  # 5 minutes
    
    def validate(self) -> None:
        """Validate streaming configuration."""
        if self.max_buffer_size <= 0:
            raise ValueError("max_buffer_size must be positive")
        if self.max_message_size <= 0:
            raise ValueError("max_message_size must be positive")
        if self.keepalive_timeout <= 0:
            raise ValueError("keepalive_timeout must be positive")
        if self.max_concurrent_streams <= 0:
            raise ValueError("max_concurrent_streams must be positive")


class StreamingError(CommunicationError):
    """Base exception for streaming operations."""
    
    def __init__(self, message: str, pattern: Optional[StreamingPattern] = None, 
                 stream_id: Optional[str] = None):
        super().__init__(message)
        self.pattern = pattern
        self.stream_id = stream_id


class BackpressureError(StreamingError):
    """Exception raised when backpressure limits are exceeded."""
    pass


class StreamingBuffer(Generic[T]):
    """Buffer for streaming messages with backpressure handling."""
    
    def __init__(self, max_size: int, strategy: BackpressureStrategy):
        self.max_size = max_size
        self.strategy = strategy
        self._buffer: deque = deque()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._closed = False
        
    async def put(self, item: T) -> bool:
        """Put item in buffer, handling backpressure."""
        async with self._lock:
            if self._closed:
                return False
                
            if len(self._buffer) >= self.max_size:
                if self.strategy == BackpressureStrategy.DROP_OLDEST:
                    self._buffer.popleft()
                elif self.strategy == BackpressureStrategy.DROP_NEWEST:
                    return False
                elif self.strategy == BackpressureStrategy.BLOCK:
                    await self._not_full.wait()
                elif self.strategy == BackpressureStrategy.BUFFER_UNLIMITED:
                    pass  # Allow unlimited buffering
                    
            self._buffer.append(item)
            self._not_empty.notify()
            return True
    
    async def get(self) -> Optional[T]:
        """Get item from buffer."""
        async with self._lock:
            while not self._buffer and not self._closed:
                await self._not_empty.wait()
                
            if not self._buffer:
                return None
                
            item = self._buffer.popleft()
            self._not_full.notify()
            return item
    
    async def close(self):
        """Close the buffer."""
        async with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()
    
    @property
    def size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return len(self._buffer) >= self.max_size


class StreamingInterceptor(ABC):
    """Base class for streaming interceptors."""
    
    @abstractmethod
    async def intercept_request(self, request: Any, context: Any) -> Any:
        """Intercept outgoing request."""
        pass
    
    @abstractmethod
    async def intercept_response(self, response: Any, context: Any) -> Any:
        """Intercept incoming response."""
        pass


class AuthenticationStreamingInterceptor(StreamingInterceptor):
    """Authentication interceptor for streaming."""
    
    def __init__(self, token_provider: Optional[Callable[[], str]] = None):
        self.token_provider = token_provider
        
    async def intercept_request(self, request: Any, context: Any) -> Any:
        """Add authentication to request."""
        if self.token_provider and GRPC_AVAILABLE:
            token = self.token_provider()
            if hasattr(context, 'set_credentials'):
                context.set_credentials(grpc.access_token_call_credentials(token))
        return request
    
    async def intercept_response(self, response: Any, context: Any) -> Any:
        """Process authenticated response."""
        return response


class RateLimitingStreamingInterceptor(StreamingInterceptor):
    """Rate limiting interceptor for streaming."""
    
    def __init__(self, max_requests_per_second: float = 100.0):
        self.max_requests_per_second = max_requests_per_second
        self.last_request_time = 0.0
        self.request_count = 0
        self._lock = asyncio.Lock()
        
    async def intercept_request(self, request: Any, context: Any) -> Any:
        """Apply rate limiting to request."""
        async with self._lock:
            current_time = time.time()
            
            # Reset counter every second
            if current_time - self.last_request_time >= 1.0:
                self.request_count = 0
                self.last_request_time = current_time
            
            # Check rate limit
            if self.request_count >= self.max_requests_per_second:
                await asyncio.sleep(1.0 - (current_time - self.last_request_time))
                self.request_count = 0
                self.last_request_time = time.time()
            
            self.request_count += 1
        
        return request
    
    async def intercept_response(self, response: Any, context: Any) -> Any:
        """Process rate-limited response."""
        return response


class StreamingMetricsCollector:
    """Collector for streaming metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, StreamingMetrics] = {}
        self._lock = asyncio.Lock()
        
    async def record_message_sent(self, stream_id: str, size: int):
        """Record sent message."""
        async with self._lock:
            if stream_id not in self._metrics:
                self._metrics[stream_id] = StreamingMetrics()
            
            metrics = self._metrics[stream_id]
            metrics.messages_sent += 1
            metrics.bytes_sent += size
    
    async def record_message_received(self, stream_id: str, size: int):
        """Record received message."""
        async with self._lock:
            if stream_id not in self._metrics:
                self._metrics[stream_id] = StreamingMetrics()
            
            metrics = self._metrics[stream_id]
            metrics.messages_received += 1
            metrics.bytes_received += size
    
    async def record_error(self, stream_id: str):
        """Record error."""
        async with self._lock:
            if stream_id not in self._metrics:
                self._metrics[stream_id] = StreamingMetrics()
            
            self._metrics[stream_id].errors += 1
    
    async def record_backpressure(self, stream_id: str):
        """Record backpressure event."""
        async with self._lock:
            if stream_id not in self._metrics:
                self._metrics[stream_id] = StreamingMetrics()
            
            self._metrics[stream_id].backpressure_events += 1
    
    async def get_metrics(self, stream_id: str) -> Optional[StreamingMetrics]:
        """Get metrics for stream."""
        async with self._lock:
            return self._metrics.get(stream_id)
    
    async def get_all_metrics(self) -> Dict[str, StreamingMetrics]:
        """Get all metrics."""
        async with self._lock:
            return self._metrics.copy()


class StreamingManager:
    """Manager for streaming operations."""
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        self.config = config or StreamingConfig()
        self.config.validate()
        
        self._streams: Dict[str, Any] = {}
        self._interceptors: List[StreamingInterceptor] = []
        self._metrics_collector = StreamingMetricsCollector()
        self._lock = asyncio.Lock()
        
        logger.info(f"StreamingManager initialized with config: {self.config}")
    
    def add_interceptor(self, interceptor: StreamingInterceptor):
        """Add streaming interceptor."""
        self._interceptors.append(interceptor)
        logger.info(f"Added interceptor: {type(interceptor).__name__}")
    
    async def create_server_stream(self, stream_id: str, 
                                 generator: AsyncGenerator[T, None]) -> AsyncGenerator[T, None]:
        """Create server streaming with interceptors and metrics."""
        async with self._lock:
            self._streams[stream_id] = {
                'pattern': StreamingPattern.SERVER_STREAMING,
                'state': StreamingState.ACTIVE,
                'start_time': time.time()
            }
        
        try:
            async for item in generator:
                # Apply interceptors
                for interceptor in self._interceptors:
                    item = await interceptor.intercept_response(item, None)
                
                # Record metrics
                if self.config.enable_metrics:
                    item_size = len(str(item).encode('utf-8'))
                    await self._metrics_collector.record_message_sent(stream_id, item_size)
                
                yield item
                
        except Exception as e:
            await self._metrics_collector.record_error(stream_id)
            logger.error(f"Server stream {stream_id} error: {e}")
            raise StreamingError(f"Server streaming error: {e}", 
                               StreamingPattern.SERVER_STREAMING, stream_id)
        finally:
            async with self._lock:
                if stream_id in self._streams:
                    self._streams[stream_id]['state'] = StreamingState.CLOSED
    
    async def create_client_stream(self, stream_id: str, 
                                 request_iterator: AsyncIterator[T]) -> List[T]:
        """Create client streaming with interceptors and metrics."""
        async with self._lock:
            self._streams[stream_id] = {
                'pattern': StreamingPattern.CLIENT_STREAMING,
                'state': StreamingState.ACTIVE,
                'start_time': time.time()
            }
        
        buffer = StreamingBuffer(self.config.max_buffer_size, 
                               self.config.backpressure_strategy)
        
        try:
            async for request in request_iterator:
                # Apply interceptors
                for interceptor in self._interceptors:
                    request = await interceptor.intercept_request(request, None)
                
                # Handle backpressure
                if not await buffer.put(request):
                    await self._metrics_collector.record_backpressure(stream_id)
                    if self.config.backpressure_strategy == BackpressureStrategy.DROP_NEWEST:
                        continue
                
                # Record metrics
                if self.config.enable_metrics:
                    request_size = len(str(request).encode('utf-8'))
                    await self._metrics_collector.record_message_received(stream_id, request_size)
            
            # Collect all buffered requests
            requests = []
            while True:
                request = await buffer.get()
                if request is None:
                    break
                requests.append(request)
            
            return requests
            
        except Exception as e:
            await self._metrics_collector.record_error(stream_id)
            logger.error(f"Client stream {stream_id} error: {e}")
            raise StreamingError(f"Client streaming error: {e}", 
                               StreamingPattern.CLIENT_STREAMING, stream_id)
        finally:
            await buffer.close()
            async with self._lock:
                if stream_id in self._streams:
                    self._streams[stream_id]['state'] = StreamingState.CLOSED
    
    async def create_bidirectional_stream(self, stream_id: str,
                                        request_iterator: AsyncIterator[T],
                                        response_handler: Callable[[T], AsyncGenerator[U, None]]
                                        ) -> AsyncGenerator[U, None]:
        """Create bidirectional streaming with interceptors and metrics."""
        async with self._lock:
            self._streams[stream_id] = {
                'pattern': StreamingPattern.BIDIRECTIONAL_STREAMING,
                'state': StreamingState.ACTIVE,
                'start_time': time.time()
            }
        
        request_buffer = StreamingBuffer(self.config.max_buffer_size, 
                                       self.config.backpressure_strategy)
        
        async def process_requests():
            """Process incoming requests."""
            try:
                async for request in request_iterator:
                    # Apply interceptors
                    for interceptor in self._interceptors:
                        request = await interceptor.intercept_request(request, None)
                    
                    # Handle backpressure
                    if not await request_buffer.put(request):
                        await self._metrics_collector.record_backpressure(stream_id)
                    
                    # Record metrics
                    if self.config.enable_metrics:
                        request_size = len(str(request).encode('utf-8'))
                        await self._metrics_collector.record_message_received(stream_id, request_size)
                        
            except Exception as e:
                logger.error(f"Bidirectional stream {stream_id} request processing error: {e}")
            finally:
                await request_buffer.close()
        
        # Start request processing task
        request_task = asyncio.create_task(process_requests())
        
        try:
            # Process requests and yield responses
            while True:
                request = await request_buffer.get()
                if request is None:
                    break
                
                # Generate responses for this request
                async for response in response_handler(request):
                    # Apply interceptors
                    for interceptor in self._interceptors:
                        response = await interceptor.intercept_response(response, None)
                    
                    # Record metrics
                    if self.config.enable_metrics:
                        response_size = len(str(response).encode('utf-8'))
                        await self._metrics_collector.record_message_sent(stream_id, response_size)
                    
                    yield response
                    
        except Exception as e:
            await self._metrics_collector.record_error(stream_id)
            logger.error(f"Bidirectional stream {stream_id} error: {e}")
            raise StreamingError(f"Bidirectional streaming error: {e}", 
                               StreamingPattern.BIDIRECTIONAL_STREAMING, stream_id)
        finally:
            request_task.cancel()
            try:
                await request_task
            except asyncio.CancelledError:
                pass
            
            async with self._lock:
                if stream_id in self._streams:
                    self._streams[stream_id]['state'] = StreamingState.CLOSED
    
    async def get_stream_metrics(self, stream_id: str) -> Optional[StreamingMetrics]:
        """Get metrics for specific stream."""
        return await self._metrics_collector.get_metrics(stream_id)
    
    async def get_all_metrics(self) -> Dict[str, StreamingMetrics]:
        """Get all streaming metrics."""
        return await self._metrics_collector.get_all_metrics()
    
    async def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active streams."""
        async with self._lock:
            return {
                stream_id: info.copy() 
                for stream_id, info in self._streams.items()
                if info['state'] == StreamingState.ACTIVE
            }
    
    async def close_stream(self, stream_id: str):
        """Close specific stream."""
        async with self._lock:
            if stream_id in self._streams:
                self._streams[stream_id]['state'] = StreamingState.CLOSED
                logger.info(f"Stream {stream_id} closed")
    
    async def close_all_streams(self):
        """Close all active streams."""
        async with self._lock:
            for stream_id in list(self._streams.keys()):
                self._streams[stream_id]['state'] = StreamingState.CLOSED
            logger.info("All streams closed")


# Factory functions for easy creation
def create_streaming_manager(config: Optional[StreamingConfig] = None) -> StreamingManager:
    """Create streaming manager with optional configuration."""
    return StreamingManager(config)


def create_authentication_interceptor(token_provider: Optional[Callable[[], str]] = None) -> AuthenticationStreamingInterceptor:
    """Create authentication interceptor."""
    return AuthenticationStreamingInterceptor(token_provider)


def create_rate_limiting_interceptor(max_requests_per_second: float = 100.0) -> RateLimitingStreamingInterceptor:
    """Create rate limiting interceptor."""
    return RateLimitingStreamingInterceptor(max_requests_per_second)


# Mock implementations for when gRPC is not available
if not GRPC_AVAILABLE:
    logger.warning("gRPC not available, using mock implementations")
    
    class MockStreamingManager(StreamingManager):
        """Mock streaming manager when gRPC is not available."""
        
        def __init__(self, config: Optional[StreamingConfig] = None):
            super().__init__(config)
            logger.info("Using mock streaming manager (gRPC not available)")
        
        async def create_server_stream(self, stream_id: str, 
                                     generator: AsyncGenerator[T, None]) -> AsyncGenerator[T, None]:
            """Mock server streaming."""
            logger.info(f"Mock server stream created: {stream_id}")
            async for item in generator:
                yield item
        
        async def create_client_stream(self, stream_id: str, 
                                     request_iterator: AsyncIterator[T]) -> List[T]:
            """Mock client streaming."""
            logger.info(f"Mock client stream created: {stream_id}")
            requests = []
            async for request in request_iterator:
                requests.append(request)
            return requests
    
    # Replace the real class with mock when gRPC not available
    StreamingManager = MockStreamingManager


__all__ = [
    'StreamingPattern',
    'StreamingState', 
    'BackpressureStrategy',
    'StreamingMetrics',
    'StreamingConfig',
    'StreamingError',
    'BackpressureError',
    'StreamingBuffer',
    'StreamingInterceptor',
    'AuthenticationStreamingInterceptor',
    'RateLimitingStreamingInterceptor',
    'StreamingMetricsCollector',
    'StreamingManager',
    'create_streaming_manager',
    'create_authentication_interceptor',
    'create_rate_limiting_interceptor'
]
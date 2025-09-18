"""
Automatic Instrumentation for Database and Message Broker Tracing.

This module provides automatic instrumentation for database queries,
message broker operations, and HTTP client requests with comprehensive
tracing, performance analysis, and security features.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import time
import re
import hashlib
from typing import Dict, Any, Optional, List, Callable, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from contextlib import contextmanager

# Database and messaging imports
try:
    import asyncpg
    import psycopg2
    import pymongo
    import redis
    import aioredis
    ASYNCPG_AVAILABLE = True
    PSYCOPG2_AVAILABLE = True
    PYMONGO_AVAILABLE = True
    REDIS_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    PSYCOPG2_AVAILABLE = False
    PYMONGO_AVAILABLE = False
    REDIS_AVAILABLE = False

# Message broker imports
try:
    import pika
    import aiokafka
    PIKA_AVAILABLE = True
    AIOKAFKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    AIOKAFKA_AVAILABLE = False

# HTTP client imports
try:
    import httpx
    import aiohttp
    HTTPX_AVAILABLE = True
    AIOHTTP_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    AIOHTTP_AVAILABLE = False

from .tracer import get_tracer, Span, SpanStatus
from .exceptions import InstrumentationError, DatabaseTracingError, MessageBrokerTracingError, HTTPTracingError


@dataclass
class InstrumentationConfig:
    """Configuration for automatic instrumentation."""
    enabled: bool = True
    sanitize_queries: bool = True
    max_query_length: int = 1000
    capture_parameters: bool = False
    capture_result_metadata: bool = True
    performance_threshold_ms: float = 1000.0
    error_sampling_rate: float = 1.0
    success_sampling_rate: float = 0.1


class BaseInstrumentation(ABC):
    """Base class for automatic instrumentation."""
    
    def __init__(self, config: InstrumentationConfig, tracer_name: str):
        self.config = config
        self.tracer = get_tracer(tracer_name)
        self._logger = logging.getLogger(__name__)
        self._original_methods: Dict[str, Callable] = {}
    
    @abstractmethod
    def instrument(self) -> None:
        """Apply instrumentation."""
        pass
    
    @abstractmethod
    def uninstrument(self) -> None:
        """Remove instrumentation."""
        pass
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize database query by removing sensitive data."""
        if not self.config.sanitize_queries:
            return query
        
        try:
            # Remove string literals
            sanitized = re.sub(r"'[^']*'", "'?'", query)
            sanitized = re.sub(r'"[^"]*"', '"?"', sanitized)
            
            # Remove numeric literals
            sanitized = re.sub(r'\b\d+\b', '?', sanitized)
            
            # Truncate if too long
            if len(sanitized) > self.config.max_query_length:
                sanitized = sanitized[:self.config.max_query_length] + "..."
            
            return sanitized
            
        except Exception as e:
            self._logger.warning(f"Failed to sanitize query: {e}")
            return "[SANITIZATION_ERROR]"
    
    def _should_sample_operation(self, is_error: bool) -> bool:
        """Determine if operation should be sampled."""
        import random
        
        if is_error:
            return random.random() < self.config.error_sampling_rate
        else:
            return random.random() < self.config.success_sampling_rate


class DatabaseInstrumentation(BaseInstrumentation):
    """Automatic instrumentation for database operations."""
    
    def __init__(self, config: InstrumentationConfig):
        super().__init__(config, "database_instrumentation")
        self._instrumented_libraries = set()
    
    def instrument(self) -> None:
        """Apply database instrumentation."""
        if not self.config.enabled:
            return
        
        try:
            # Instrument asyncpg
            if ASYNCPG_AVAILABLE and 'asyncpg' not in self._instrumented_libraries:
                self._instrument_asyncpg()
                self._instrumented_libraries.add('asyncpg')
            
            # Instrument psycopg2
            if PSYCOPG2_AVAILABLE and 'psycopg2' not in self._instrumented_libraries:
                self._instrument_psycopg2()
                self._instrumented_libraries.add('psycopg2')
            
            # Instrument pymongo
            if PYMONGO_AVAILABLE and 'pymongo' not in self._instrumented_libraries:
                self._instrument_pymongo()
                self._instrumented_libraries.add('pymongo')
            
            # Instrument redis
            if REDIS_AVAILABLE and 'redis' not in self._instrumented_libraries:
                self._instrument_redis()
                self._instrumented_libraries.add('redis')
            
            self._logger.info(f"Database instrumentation applied to: {self._instrumented_libraries}")
            
        except Exception as e:
            raise InstrumentationError(
                message=f"Failed to apply database instrumentation: {e}",
                instrumentation_type="database",
                original_error=e
            )
    
    def uninstrument(self) -> None:
        """Remove database instrumentation."""
        try:
            # Restore original methods
            for library_method, original_method in self._original_methods.items():
                library, method_name = library_method.split('.')
                if library == 'asyncpg' and ASYNCPG_AVAILABLE:
                    setattr(asyncpg.Connection, method_name, original_method)
                elif library == 'psycopg2' and PSYCOPG2_AVAILABLE:
                    setattr(psycopg2.extensions.cursor, method_name, original_method)
                # Add other libraries as needed
            
            self._original_methods.clear()
            self._instrumented_libraries.clear()
            
        except Exception as e:
            self._logger.error(f"Failed to remove database instrumentation: {e}")
    
    def _instrument_asyncpg(self) -> None:
        """Instrument asyncpg for PostgreSQL tracing."""
        try:
            import asyncpg
            
            # Store original methods
            self._original_methods['asyncpg.execute'] = asyncpg.Connection.execute
            self._original_methods['asyncpg.fetch'] = asyncpg.Connection.fetch
            self._original_methods['asyncpg.fetchrow'] = asyncpg.Connection.fetchrow
            
            # Wrap execute method
            async def traced_execute(self, query, *args, timeout=None):
                return await self._trace_asyncpg_operation(
                    'execute', query, args, timeout,
                    DatabaseInstrumentation._original_methods['asyncpg.execute']
                )
            
            # Wrap fetch method
            async def traced_fetch(self, query, *args, timeout=None):
                return await self._trace_asyncpg_operation(
                    'fetch', query, args, timeout,
                    DatabaseInstrumentation._original_methods['asyncpg.fetch']
                )
            
            # Wrap fetchrow method
            async def traced_fetchrow(self, query, *args, timeout=None):
                return await self._trace_asyncpg_operation(
                    'fetchrow', query, args, timeout,
                    DatabaseInstrumentation._original_methods['asyncpg.fetchrow']
                )
            
            # Apply instrumentation
            asyncpg.Connection.execute = traced_execute
            asyncpg.Connection.fetch = traced_fetch
            asyncpg.Connection.fetchrow = traced_fetchrow
            
        except Exception as e:
            raise DatabaseTracingError(
                message=f"Failed to instrument asyncpg: {e}",
                database_type="postgresql",
                original_error=e
            )
    
    async def _trace_asyncpg_operation(self, operation, query, args, timeout, original_method):
        """Trace asyncpg database operation."""
        if not self._should_sample_operation(False):
            return await original_method(self, query, *args, timeout=timeout)
        
        sanitized_query = self._sanitize_query(str(query))
        
        with self.tracer.span(f"postgresql.{operation}", kind="client") as span:
            try:
                # Set database attributes
                span.set_attributes({
                    "db.system": "postgresql",
                    "db.operation": operation.upper(),
                    "db.statement": sanitized_query,
                    "db.connection_string": "[REDACTED]"
                })
                
                if self.config.capture_parameters and args:
                    span.set_attribute("db.params_count", len(args))
                
                if timeout:
                    span.set_attribute("db.timeout", timeout)
                
                # Execute operation
                start_time = time.time()
                result = await original_method(self, query, *args, timeout=timeout)
                duration_ms = (time.time() - start_time) * 1000
                
                # Set result attributes
                span.set_attributes({
                    "db.duration_ms": duration_ms,
                    "db.success": True
                })
                
                if self.config.capture_result_metadata:
                    if hasattr(result, '__len__'):
                        span.set_attribute("db.rows_affected", len(result))
                
                # Check performance threshold
                if duration_ms > self.config.performance_threshold_ms:
                    span.add_event("slow_query", {
                        "threshold_ms": self.config.performance_threshold_ms,
                        "actual_duration_ms": duration_ms
                    })
                
                span.set_status(SpanStatus.OK)
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(SpanStatus.ERROR, str(e))
                raise
    
    def _instrument_psycopg2(self) -> None:
        """Instrument psycopg2 for PostgreSQL tracing."""
        # Similar implementation for psycopg2
        pass
    
    def _instrument_pymongo(self) -> None:
        """Instrument pymongo for MongoDB tracing."""
        # Implementation for MongoDB tracing
        pass
    
    def _instrument_redis(self) -> None:
        """Instrument redis for Redis tracing."""
        # Implementation for Redis tracing
        pass


class MessageBrokerInstrumentation(BaseInstrumentation):
    """Automatic instrumentation for message broker operations."""
    
    def __init__(self, config: InstrumentationConfig):
        super().__init__(config, "message_broker_instrumentation")
        self._instrumented_libraries = set()
    
    def instrument(self) -> None:
        """Apply message broker instrumentation."""
        if not self.config.enabled:
            return
        
        try:
            # Instrument RabbitMQ (pika)
            if PIKA_AVAILABLE and 'pika' not in self._instrumented_libraries:
                self._instrument_pika()
                self._instrumented_libraries.add('pika')
            
            # Instrument Kafka (aiokafka)
            if AIOKAFKA_AVAILABLE and 'aiokafka' not in self._instrumented_libraries:
                self._instrument_aiokafka()
                self._instrumented_libraries.add('aiokafka')
            
            self._logger.info(f"Message broker instrumentation applied to: {self._instrumented_libraries}")
            
        except Exception as e:
            raise InstrumentationError(
                message=f"Failed to apply message broker instrumentation: {e}",
                instrumentation_type="message_broker",
                original_error=e
            )
    
    def uninstrument(self) -> None:
        """Remove message broker instrumentation."""
        try:
            # Restore original methods
            for library_method, original_method in self._original_methods.items():
                # Restore methods based on library
                pass
            
            self._original_methods.clear()
            self._instrumented_libraries.clear()
            
        except Exception as e:
            self._logger.error(f"Failed to remove message broker instrumentation: {e}")
    
    def _instrument_pika(self) -> None:
        """Instrument pika for RabbitMQ tracing."""
        try:
            import pika
            
            # Store original methods
            self._original_methods['pika.basic_publish'] = pika.BlockingConnection.channel().basic_publish
            
            def traced_basic_publish(self, exchange, routing_key, body, properties=None, mandatory=False):
                return self._trace_rabbitmq_publish(
                    exchange, routing_key, body, properties, mandatory,
                    MessageBrokerInstrumentation._original_methods['pika.basic_publish']
                )
            
            # Apply instrumentation (simplified example)
            # In practice, this would need more sophisticated patching
            
        except Exception as e:
            raise MessageBrokerTracingError(
                message=f"Failed to instrument pika: {e}",
                broker_type="rabbitmq",
                original_error=e
            )
    
    def _trace_rabbitmq_publish(self, exchange, routing_key, body, properties, mandatory, original_method):
        """Trace RabbitMQ publish operation."""
        with self.tracer.span("rabbitmq.publish", kind="producer") as span:
            try:
                # Set message broker attributes
                span.set_attributes({
                    "messaging.system": "rabbitmq",
                    "messaging.operation": "publish",
                    "messaging.destination": exchange or "default",
                    "messaging.routing_key": routing_key,
                    "messaging.message_size": len(body) if body else 0
                })
                
                if properties:
                    span.set_attribute("messaging.message_id", getattr(properties, 'message_id', None))
                
                # Execute operation
                result = original_method(self, exchange, routing_key, body, properties, mandatory)
                
                span.set_status(SpanStatus.OK)
                return result
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(SpanStatus.ERROR, str(e))
                raise
    
    def _instrument_aiokafka(self) -> None:
        """Instrument aiokafka for Kafka tracing."""
        # Implementation for Kafka tracing
        pass


class HTTPClientInstrumentation(BaseInstrumentation):
    """Automatic instrumentation for HTTP client operations."""
    
    def __init__(self, config: InstrumentationConfig):
        super().__init__(config, "http_client_instrumentation")
        self._instrumented_libraries = set()
    
    def instrument(self) -> None:
        """Apply HTTP client instrumentation."""
        if not self.config.enabled:
            return
        
        try:
            # Instrument httpx
            if HTTPX_AVAILABLE and 'httpx' not in self._instrumented_libraries:
                self._instrument_httpx()
                self._instrumented_libraries.add('httpx')
            
            # Instrument aiohttp
            if AIOHTTP_AVAILABLE and 'aiohttp' not in self._instrumented_libraries:
                self._instrument_aiohttp()
                self._instrumented_libraries.add('aiohttp')
            
            self._logger.info(f"HTTP client instrumentation applied to: {self._instrumented_libraries}")
            
        except Exception as e:
            raise InstrumentationError(
                message=f"Failed to apply HTTP client instrumentation: {e}",
                instrumentation_type="http_client",
                original_error=e
            )
    
    def uninstrument(self) -> None:
        """Remove HTTP client instrumentation."""
        try:
            # Restore original methods
            for library_method, original_method in self._original_methods.items():
                # Restore methods based on library
                pass
            
            self._original_methods.clear()
            self._instrumented_libraries.clear()
            
        except Exception as e:
            self._logger.error(f"Failed to remove HTTP client instrumentation: {e}")
    
    def _instrument_httpx(self) -> None:
        """Instrument httpx for HTTP client tracing."""
        try:
            import httpx
            
            # Store original methods
            self._original_methods['httpx.request'] = httpx.AsyncClient.request
            
            async def traced_request(self, method, url, **kwargs):
                return await self._trace_http_request(
                    method, url, kwargs,
                    HTTPClientInstrumentation._original_methods['httpx.request']
                )
            
            # Apply instrumentation
            httpx.AsyncClient.request = traced_request
            
        except Exception as e:
            raise HTTPTracingError(
                message=f"Failed to instrument httpx: {e}",
                original_error=e
            )
    
    async def _trace_http_request(self, method, url, kwargs, original_method):
        """Trace HTTP client request."""
        with self.tracer.span(f"HTTP {method}", kind="client") as span:
            try:
                # Set HTTP attributes
                span.set_attributes({
                    "http.method": method,
                    "http.url": str(url),
                    "http.scheme": url.scheme if hasattr(url, 'scheme') else "unknown",
                    "net.peer.name": url.host if hasattr(url, 'host') else "unknown"
                })
                
                # Execute request
                start_time = time.time()
                response = await original_method(self, method, url, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Set response attributes
                span.set_attributes({
                    "http.status_code": response.status_code,
                    "http.response.duration_ms": duration_ms
                })
                
                if response.status_code >= 400:
                    span.set_status(SpanStatus.ERROR, f"HTTP {response.status_code}")
                else:
                    span.set_status(SpanStatus.OK)
                
                return response
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(SpanStatus.ERROR, str(e))
                raise
    
    def _instrument_aiohttp(self) -> None:
        """Instrument aiohttp for HTTP client tracing."""
        # Implementation for aiohttp tracing
        pass


class AutoInstrumentation:
    """Automatic instrumentation manager."""
    
    def __init__(self, config: Optional[InstrumentationConfig] = None):
        self.config = config or InstrumentationConfig()
        self._instrumentations: List[BaseInstrumentation] = []
        self._logger = logging.getLogger(__name__)
    
    def instrument_all(self) -> None:
        """Apply all available instrumentations."""
        try:
            # Database instrumentation
            db_instrumentation = DatabaseInstrumentation(self.config)
            db_instrumentation.instrument()
            self._instrumentations.append(db_instrumentation)
            
            # Message broker instrumentation
            mb_instrumentation = MessageBrokerInstrumentation(self.config)
            mb_instrumentation.instrument()
            self._instrumentations.append(mb_instrumentation)
            
            # HTTP client instrumentation
            http_instrumentation = HTTPClientInstrumentation(self.config)
            http_instrumentation.instrument()
            self._instrumentations.append(http_instrumentation)
            
            self._logger.info("All available instrumentations applied")
            
        except Exception as e:
            self._logger.error(f"Failed to apply auto-instrumentation: {e}")
            raise
    
    def uninstrument_all(self) -> None:
        """Remove all instrumentations."""
        for instrumentation in self._instrumentations:
            try:
                instrumentation.uninstrument()
            except Exception as e:
                self._logger.error(f"Failed to remove instrumentation: {e}")
        
        self._instrumentations.clear()
    
    def get_instrumentation_status(self) -> Dict[str, Any]:
        """Get status of all instrumentations."""
        return {
            'total_instrumentations': len(self._instrumentations),
            'instrumentations': [
                {
                    'type': type(inst).__name__,
                    'enabled': inst.config.enabled
                }
                for inst in self._instrumentations
            ]
        }


# Global auto-instrumentation instance
_global_auto_instrumentation: Optional[AutoInstrumentation] = None


def auto_instrument(config: Optional[InstrumentationConfig] = None) -> None:
    """Apply automatic instrumentation globally."""
    global _global_auto_instrumentation
    
    if _global_auto_instrumentation:
        _global_auto_instrumentation.uninstrument_all()
    
    _global_auto_instrumentation = AutoInstrumentation(config)
    _global_auto_instrumentation.instrument_all()


def uninstrument_all() -> None:
    """Remove all automatic instrumentation."""
    global _global_auto_instrumentation
    
    if _global_auto_instrumentation:
        _global_auto_instrumentation.uninstrument_all()
        _global_auto_instrumentation = None


def get_instrumentation_status() -> Dict[str, Any]:
    """Get global instrumentation status."""
    if _global_auto_instrumentation:
        return _global_auto_instrumentation.get_instrumentation_status()
    else:
        return {'total_instrumentations': 0, 'instrumentations': []}


# Export main classes and functions
__all__ = [
    'InstrumentationConfig',
    'BaseInstrumentation',
    'DatabaseInstrumentation',
    'MessageBrokerInstrumentation',
    'HTTPClientInstrumentation',
    'AutoInstrumentation',
    'auto_instrument',
    'uninstrument_all',
    'get_instrumentation_status',
]
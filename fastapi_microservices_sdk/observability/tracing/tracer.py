"""
Tracer and Span management for distributed tracing.

This module provides high-level interfaces for creating and managing
traces and spans with OpenTelemetry integration.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Union, ContextManager
from contextlib import contextmanager
from enum import Enum
from dataclasses import dataclass

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode, SpanKind
    from opentelemetry.trace.span import Span as OTelSpan
    from opentelemetry.util.types import AttributeValue
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Mock classes for development
    class Status:
        pass
    class StatusCode:
        OK = "OK"
        ERROR = "ERROR"
    class SpanKind:
        INTERNAL = "INTERNAL"
        SERVER = "SERVER"
        CLIENT = "CLIENT"
        PRODUCER = "PRODUCER"
        CONSUMER = "CONSUMER"
    class OTelSpan:
        pass

from .provider import get_tracer_provider
from .exceptions import (
    SpanCreationError,
    SpanFinishError,
    TracingError,
    handle_tracing_error,
    create_tracing_error_context
)


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "OK"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


@dataclass
class SpanContext:
    """Span context information."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 0
    trace_state: Optional[str] = None
    is_remote: bool = False


class Span:
    """High-level span wrapper for OpenTelemetry spans."""
    
    def __init__(self, otel_span: OTelSpan, operation_name: str):
        self._otel_span = otel_span
        self._operation_name = operation_name
        self._start_time = time.time()
        self._finished = False
        self._logger = logging.getLogger(__name__)
        
        # Span metadata
        self._attributes: Dict[str, Any] = {}
        self._events: List[Dict[str, Any]] = []
        self._status = SpanStatus.OK
        self._error: Optional[Exception] = None
    
    @property
    def operation_name(self) -> str:
        """Get span operation name."""
        return self._operation_name
    
    @property
    def trace_id(self) -> str:
        """Get trace ID."""
        if OPENTELEMETRY_AVAILABLE and self._otel_span:
            return format(self._otel_span.get_span_context().trace_id, '032x')
        return "unknown"
    
    @property
    def span_id(self) -> str:
        """Get span ID."""
        if OPENTELEMETRY_AVAILABLE and self._otel_span:
            return format(self._otel_span.get_span_context().span_id, '016x')
        return "unknown"
    
    @property
    def is_recording(self) -> bool:
        """Check if span is recording."""
        if OPENTELEMETRY_AVAILABLE and self._otel_span:
            return self._otel_span.is_recording()
        return False
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self._finished:
            return (self._finish_time - self._start_time) * 1000
        return (time.time() - self._start_time) * 1000
    
    def set_attribute(self, key: str, value: Any) -> 'Span':
        """Set span attribute."""
        try:
            if OPENTELEMETRY_AVAILABLE and self._otel_span and self._otel_span.is_recording():
                self._otel_span.set_attribute(key, value)
            
            self._attributes[key] = value
            return self
            
        except Exception as e:
            self._logger.warning(f"Failed to set span attribute {key}: {e}")
            return self
    
    def set_attributes(self, attributes: Dict[str, Any]) -> 'Span':
        """Set multiple span attributes."""
        for key, value in attributes.items():
            self.set_attribute(key, value)
        return self
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> 'Span':
        """Add event to span."""
        try:
            event_attributes = attributes or {}
            
            if OPENTELEMETRY_AVAILABLE and self._otel_span and self._otel_span.is_recording():
                self._otel_span.add_event(name, event_attributes)
            
            self._events.append({
                'name': name,
                'attributes': event_attributes,
                'timestamp': time.time()
            })
            
            return self
            
        except Exception as e:
            self._logger.warning(f"Failed to add span event {name}: {e}")
            return self
    
    def set_status(self, status: SpanStatus, description: Optional[str] = None) -> 'Span':
        """Set span status."""
        try:
            self._status = status
            
            if OPENTELEMETRY_AVAILABLE and self._otel_span and self._otel_span.is_recording():
                if status == SpanStatus.OK:
                    otel_status = Status(StatusCode.OK, description)
                elif status == SpanStatus.ERROR:
                    otel_status = Status(StatusCode.ERROR, description)
                else:
                    otel_status = Status(StatusCode.ERROR, description or status.value)
                
                self._otel_span.set_status(otel_status)
            
            return self
            
        except Exception as e:
            self._logger.warning(f"Failed to set span status: {e}")
            return self
    
    def record_exception(self, exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> 'Span':
        """Record exception in span."""
        try:
            self._error = exception
            self.set_status(SpanStatus.ERROR, str(exception))
            
            if OPENTELEMETRY_AVAILABLE and self._otel_span and self._otel_span.is_recording():
                self._otel_span.record_exception(exception, attributes)
            
            # Add exception as event
            exception_attributes = {
                'exception.type': type(exception).__name__,
                'exception.message': str(exception),
                **(attributes or {})
            }
            self.add_event('exception', exception_attributes)
            
            return self
            
        except Exception as e:
            self._logger.warning(f"Failed to record exception: {e}")
            return self
    
    def finish(self, end_time: Optional[float] = None) -> None:
        """Finish the span."""
        if self._finished:
            return
        
        try:
            self._finish_time = end_time or time.time()
            
            if OPENTELEMETRY_AVAILABLE and self._otel_span:
                if end_time:
                    self._otel_span.end(int(end_time * 1_000_000_000))  # Convert to nanoseconds
                else:
                    self._otel_span.end()
            
            self._finished = True
            
            # Log span completion
            duration_ms = self.duration_ms
            self._logger.debug(
                f"Span '{self._operation_name}' finished - "
                f"Duration: {duration_ms:.2f}ms, Status: {self._status.value}"
            )
            
        except Exception as e:
            self._logger.error(f"Failed to finish span: {e}")
            raise SpanFinishError(
                message=f"Failed to finish span '{self._operation_name}': {e}",
                span_id=self.span_id,
                span_duration_ms=self.duration_ms,
                original_error=e
            )
    
    def get_context(self) -> SpanContext:
        """Get span context."""
        if OPENTELEMETRY_AVAILABLE and self._otel_span:
            otel_context = self._otel_span.get_span_context()
            return SpanContext(
                trace_id=format(otel_context.trace_id, '032x'),
                span_id=format(otel_context.span_id, '016x'),
                trace_flags=otel_context.trace_flags,
                trace_state=str(otel_context.trace_state) if otel_context.trace_state else None,
                is_remote=otel_context.is_remote
            )
        
        return SpanContext(
            trace_id=self.trace_id,
            span_id=self.span_id
        )
    
    def get_span_data(self) -> Dict[str, Any]:
        """Get span data for debugging/monitoring."""
        return {
            'operation_name': self._operation_name,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'start_time': self._start_time,
            'duration_ms': self.duration_ms,
            'status': self._status.value,
            'finished': self._finished,
            'attributes': self._attributes.copy(),
            'events': self._events.copy(),
            'error': str(self._error) if self._error else None
        }
    
    def __enter__(self) -> 'Span':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        if exc_type is not None:
            self.record_exception(exc_val)
        self.finish()


class Tracer:
    """High-level tracer interface."""
    
    def __init__(self, name: str, version: Optional[str] = None):
        self.name = name
        self.version = version
        self._otel_tracer = None
        self._logger = logging.getLogger(__name__)
        
        # Initialize OpenTelemetry tracer
        self._initialize_tracer()
    
    def _initialize_tracer(self) -> None:
        """Initialize OpenTelemetry tracer."""
        try:
            provider = get_tracer_provider()
            if provider and provider.is_initialized():
                self._otel_tracer = provider.get_tracer(self.name, self.version)
            elif OPENTELEMETRY_AVAILABLE:
                # Fallback to global tracer provider
                self._otel_tracer = trace.get_tracer(self.name, self.version)
            
        except Exception as e:
            self._logger.warning(f"Failed to initialize tracer: {e}")
    
    def start_span(
        self,
        operation_name: str,
        parent: Optional[Union[Span, SpanContext]] = None,
        kind: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        start_time: Optional[float] = None
    ) -> Span:
        """Start a new span."""
        try:
            # Map kind to OpenTelemetry SpanKind
            otel_kind = None
            if kind:
                kind_mapping = {
                    'internal': SpanKind.INTERNAL,
                    'server': SpanKind.SERVER,
                    'client': SpanKind.CLIENT,
                    'producer': SpanKind.PRODUCER,
                    'consumer': SpanKind.CONSUMER
                }
                otel_kind = kind_mapping.get(kind.lower(), SpanKind.INTERNAL)
            
            # Create OpenTelemetry span
            otel_span = None
            if OPENTELEMETRY_AVAILABLE and self._otel_tracer:
                span_kwargs = {
                    'name': operation_name,
                    'kind': otel_kind
                }
                
                if start_time:
                    span_kwargs['start_time'] = int(start_time * 1_000_000_000)  # Convert to nanoseconds
                
                if parent:
                    if isinstance(parent, Span):
                        # Use parent span's context
                        span_kwargs['context'] = parent._otel_span.get_span_context() if parent._otel_span else None
                    elif isinstance(parent, SpanContext):
                        # Create context from SpanContext (would need more implementation)
                        pass
                
                otel_span = self._otel_tracer.start_span(**span_kwargs)
            
            # Create our span wrapper
            span = Span(otel_span, operation_name)
            
            # Set initial attributes
            if attributes:
                span.set_attributes(attributes)
            
            self._logger.debug(f"Started span '{operation_name}' - Trace ID: {span.trace_id}")
            
            return span
            
        except Exception as e:
            self._logger.error(f"Failed to start span '{operation_name}': {e}")
            raise SpanCreationError(
                message=f"Failed to start span '{operation_name}': {e}",
                operation_name=operation_name,
                original_error=e
            )
    
    @contextmanager
    def span(
        self,
        operation_name: str,
        parent: Optional[Union[Span, SpanContext]] = None,
        kind: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> ContextManager[Span]:
        """Context manager for creating spans."""
        span = self.start_span(operation_name, parent, kind, attributes)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.finish()
    
    def get_current_span(self) -> Optional[Span]:
        """Get current active span."""
        try:
            if OPENTELEMETRY_AVAILABLE:
                otel_span = trace.get_current_span()
                if otel_span and otel_span.is_recording():
                    # Create wrapper for current span
                    return Span(otel_span, "current_span")
            
            return None
            
        except Exception as e:
            self._logger.warning(f"Failed to get current span: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if tracer is available and functional."""
        return OPENTELEMETRY_AVAILABLE and self._otel_tracer is not None


class TracingSystem:
    """Central tracing system manager."""
    
    def __init__(self):
        self._tracers: Dict[str, Tracer] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
    
    def get_tracer(self, name: str, version: Optional[str] = None) -> Tracer:
        """Get or create a tracer."""
        tracer_key = f"{name}:{version or 'default'}"
        
        with self._lock:
            if tracer_key not in self._tracers:
                self._tracers[tracer_key] = Tracer(name, version)
            
            return self._tracers[tracer_key]
    
    def create_tracer(self, name: str, version: Optional[str] = None) -> Tracer:
        """Create a new tracer (alias for get_tracer)."""
        return self.get_tracer(name, version)
    
    def get_all_tracers(self) -> List[Tracer]:
        """Get all registered tracers."""
        with self._lock:
            return list(self._tracers.values())
    
    def get_tracing_status(self) -> Dict[str, Any]:
        """Get tracing system status."""
        with self._lock:
            return {
                'available': OPENTELEMETRY_AVAILABLE,
                'tracer_count': len(self._tracers),
                'tracers': [
                    {
                        'name': tracer.name,
                        'version': tracer.version,
                        'available': tracer.is_available()
                    }
                    for tracer in self._tracers.values()
                ]
            }


# Global tracing system instance
_global_tracing_system = TracingSystem()


def get_tracer(name: str, version: Optional[str] = None) -> Tracer:
    """Get a tracer from the global tracing system."""
    return _global_tracing_system.get_tracer(name, version)


def create_tracer(name: str, version: Optional[str] = None) -> Tracer:
    """Create a tracer from the global tracing system."""
    return _global_tracing_system.create_tracer(name, version)


def get_current_span() -> Optional[Span]:
    """Get the current active span."""
    try:
        if OPENTELEMETRY_AVAILABLE:
            otel_span = trace.get_current_span()
            if otel_span and otel_span.is_recording():
                return Span(otel_span, "current_span")
        
        return None
        
    except Exception:
        return None


def create_span(
    operation_name: str,
    tracer_name: str = "default",
    parent: Optional[Union[Span, SpanContext]] = None,
    kind: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Span:
    """Create a span using the global tracing system."""
    tracer = get_tracer(tracer_name)
    return tracer.start_span(operation_name, parent, kind, attributes)


@contextmanager
def trace_operation(
    operation_name: str,
    tracer_name: str = "default",
    attributes: Optional[Dict[str, Any]] = None
) -> ContextManager[Span]:
    """Context manager for tracing operations."""
    tracer = get_tracer(tracer_name)
    with tracer.span(operation_name, attributes=attributes) as span:
        yield span


# Export main classes and functions
__all__ = [
    'SpanStatus',
    'SpanContext',
    'Span',
    'Tracer',
    'TracingSystem',
    'get_tracer',
    'create_tracer',
    'get_current_span',
    'create_span',
    'trace_operation',
    'OPENTELEMETRY_AVAILABLE',
]
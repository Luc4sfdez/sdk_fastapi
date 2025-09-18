"""
Tracing-specific exceptions for the distributed tracing system.

This module defines custom exceptions for tracing operations,
providing detailed error information and context for debugging and monitoring.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..exceptions import ObservabilityError


class TracingError(ObservabilityError):
    """Base exception for tracing-related errors."""
    
    def __init__(
        self,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        span_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, component="tracing", **kwargs)
        self.trace_id = trace_id
        self.span_id = span_id
        self.span_name = span_name
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'span_name': self.span_name
        })
        return data


class SpanCreationError(TracingError):
    """Exception raised during span creation."""
    
    def __init__(
        self,
        message: str,
        operation_name: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="create_span", **kwargs)
        self.operation_name = operation_name
        self.parent_span_id = parent_span_id
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'operation_name': self.operation_name,
            'parent_span_id': self.parent_span_id
        })
        return data


class SpanFinishError(TracingError):
    """Exception raised when finishing a span."""
    
    def __init__(
        self,
        message: str,
        span_duration_ms: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, operation="finish_span", **kwargs)
        self.span_duration_ms = span_duration_ms


class TraceExportError(TracingError):
    """Exception raised during trace export."""
    
    def __init__(
        self,
        message: str,
        exporter_type: Optional[str] = None,
        batch_size: Optional[int] = None,
        export_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="export_trace", **kwargs)
        self.exporter_type = exporter_type
        self.batch_size = batch_size
        self.export_endpoint = export_endpoint
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'exporter_type': self.exporter_type,
            'batch_size': self.batch_size,
            'export_endpoint': self.export_endpoint
        })
        return data


class SamplingError(TracingError):
    """Exception raised during sampling decisions."""
    
    def __init__(
        self,
        message: str,
        sampling_strategy: Optional[str] = None,
        sampling_rate: Optional[float] = None,
        **kwargs
    ):
        super().__init__(message, operation="sampling", **kwargs)
        self.sampling_strategy = sampling_strategy
        self.sampling_rate = sampling_rate
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'sampling_strategy': self.sampling_strategy,
            'sampling_rate': self.sampling_rate
        })
        return data


class ContextPropagationError(TracingError):
    """Exception raised during context propagation."""
    
    def __init__(
        self,
        message: str,
        propagation_type: Optional[str] = None,
        carrier_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="context_propagation", **kwargs)
        self.propagation_type = propagation_type  # inject, extract
        self.carrier_type = carrier_type  # http_headers, grpc_metadata, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'propagation_type': self.propagation_type,
            'carrier_type': self.carrier_type
        })
        return data


class TracerProviderError(TracingError):
    """Exception raised during tracer provider operations."""
    
    def __init__(
        self,
        message: str,
        provider_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="tracer_provider", **kwargs)
        self.provider_type = provider_type


class InstrumentationError(TracingError):
    """Exception raised during automatic instrumentation."""
    
    def __init__(
        self,
        message: str,
        instrumentation_type: Optional[str] = None,
        target_library: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="instrumentation", **kwargs)
        self.instrumentation_type = instrumentation_type
        self.target_library = target_library
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'instrumentation_type': self.instrumentation_type,
            'target_library': self.target_library
        })
        return data


class JaegerExportError(TraceExportError):
    """Exception raised during Jaeger export."""
    
    def __init__(
        self,
        message: str,
        jaeger_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, exporter_type="jaeger", **kwargs)
        self.jaeger_endpoint = jaeger_endpoint


class ZipkinExportError(TraceExportError):
    """Exception raised during Zipkin export."""
    
    def __init__(
        self,
        message: str,
        zipkin_endpoint: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, exporter_type="zipkin", **kwargs)
        self.zipkin_endpoint = zipkin_endpoint


class OTLPExportError(TraceExportError):
    """Exception raised during OTLP export."""
    
    def __init__(
        self,
        message: str,
        otlp_endpoint: Optional[str] = None,
        otlp_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(message, exporter_type="otlp", **kwargs)
        self.otlp_endpoint = otlp_endpoint
        self.otlp_headers = otlp_headers or {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'otlp_endpoint': self.otlp_endpoint,
            'otlp_headers': self.otlp_headers
        })
        return data


class DatabaseTracingError(TracingError):
    """Exception raised during database operation tracing."""
    
    def __init__(
        self,
        message: str,
        database_type: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="database_tracing", **kwargs)
        self.database_type = database_type
        self.query = query  # Should be sanitized
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'database_type': self.database_type,
            'query': self.query
        })
        return data


class HTTPTracingError(TracingError):
    """Exception raised during HTTP request/response tracing."""
    
    def __init__(
        self,
        message: str,
        http_method: Optional[str] = None,
        http_url: Optional[str] = None,
        http_status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, operation="http_tracing", **kwargs)
        self.http_method = http_method
        self.http_url = http_url
        self.http_status_code = http_status_code
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'http_method': self.http_method,
            'http_url': self.http_url,
            'http_status_code': self.http_status_code
        })
        return data


class MessageBrokerTracingError(TracingError):
    """Exception raised during message broker tracing."""
    
    def __init__(
        self,
        message: str,
        broker_type: Optional[str] = None,
        topic_or_queue: Optional[str] = None,
        operation_type: Optional[str] = None,  # publish, consume, etc.
        **kwargs
    ):
        super().__init__(message, operation="message_broker_tracing", **kwargs)
        self.broker_type = broker_type
        self.topic_or_queue = topic_or_queue
        self.operation_type = operation_type
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'broker_type': self.broker_type,
            'topic_or_queue': self.topic_or_queue,
            'operation_type': self.operation_type
        })
        return data


class CorrelationError(TracingError):
    """Exception raised during trace correlation operations."""
    
    def __init__(
        self,
        message: str,
        correlation_type: Optional[str] = None,  # logging, metrics, etc.
        correlation_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="correlation", **kwargs)
        self.correlation_type = correlation_type
        self.correlation_id = correlation_id
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'correlation_type': self.correlation_type,
            'correlation_id': self.correlation_id
        })
        return data


# Exception handler utilities for tracing
def handle_tracing_error(
    error: Exception,
    operation: str,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> TracingError:
    """Convert generic exceptions to tracing-specific exceptions."""
    if isinstance(error, TracingError):
        return error
    
    # Map common exceptions to specific tracing errors
    error_mapping = {
        'create_span': SpanCreationError,
        'finish_span': SpanFinishError,
        'export_trace': TraceExportError,
        'sampling': SamplingError,
        'context_propagation': ContextPropagationError,
        'tracer_provider': TracerProviderError,
        'instrumentation': InstrumentationError,
        'database_tracing': DatabaseTracingError,
        'http_tracing': HTTPTracingError,
        'message_broker_tracing': MessageBrokerTracingError,
        'correlation': CorrelationError
    }
    
    error_class = error_mapping.get(operation, TracingError)
    
    return error_class(
        message=str(error),
        operation=operation,
        trace_id=trace_id,
        span_id=span_id,
        original_error=error,
        context=context,
        correlation_id=correlation_id
    )


def create_tracing_error_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    operation_name: Optional[str] = None,
    service_name: Optional[str] = None,
    **additional_context
) -> Dict[str, Any]:
    """Create standardized error context for tracing exceptions."""
    context = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service_name': service_name or 'unknown'
    }
    
    if trace_id:
        context['trace_id'] = trace_id
    if span_id:
        context['span_id'] = span_id
    if operation_name:
        context['operation_name'] = operation_name
    
    context.update(additional_context)
    return context


# Export all exception classes
__all__ = [
    'TracingError',
    'SpanCreationError',
    'SpanFinishError',
    'TraceExportError',
    'SamplingError',
    'ContextPropagationError',
    'TracerProviderError',
    'InstrumentationError',
    'JaegerExportError',
    'ZipkinExportError',
    'OTLPExportError',
    'DatabaseTracingError',
    'HTTPTracingError',
    'MessageBrokerTracingError',
    'CorrelationError',
    'handle_tracing_error',
    'create_tracing_error_context',
]
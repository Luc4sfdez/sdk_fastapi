"""
FastAPI Middleware for automatic distributed tracing.

This module provides middleware for FastAPI applications to automatically
create traces for HTTP requests with context propagation and correlation.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from urllib.parse import urlparse

try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Mock classes for development
    class Request:
        pass
    class Response:
        pass
    class BaseHTTPMiddleware:
        pass

# OpenTelemetry context propagation
try:
    from opentelemetry import propagate, trace
    from opentelemetry.trace import SpanKind, Status, StatusCode
    from opentelemetry.propagators.textmap import CarrierT
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from .tracer import get_tracer, Span, SpanStatus
from .exceptions import HTTPTracingError, ContextPropagationError
from ..config import TracingConfig


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic request tracing."""
    
    def __init__(
        self,
        app: ASGIApp,
        config: Optional[TracingConfig] = None,
        tracer_name: str = "fastapi-http",
        exclude_paths: Optional[List[str]] = None,
        include_request_body: bool = False,
        include_response_body: bool = False,
        sanitize_headers: bool = True,
        max_body_size: int = 1024
    ):
        super().__init__(app)
        self.config = config or TracingConfig()
        self.tracer_name = tracer_name
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.sanitize_headers = sanitize_headers
        self.max_body_size = max_body_size
        
        # Get tracer
        self.tracer = get_tracer(tracer_name)
        self._logger = logging.getLogger(__name__)
        
        # Sensitive headers to exclude
        self.sensitive_headers = {
            'authorization', 'cookie', 'set-cookie', 'x-api-key',
            'x-auth-token', 'x-csrf-token', 'x-forwarded-for'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request with tracing."""
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Extract trace context from headers
        trace_context = self._extract_trace_context(request)
        
        # Create span for the request
        operation_name = f"{request.method} {request.url.path}"
        
        try:
            with self.tracer.span(
                operation_name=operation_name,
                kind="server",
                attributes=self._get_request_attributes(request)
            ) as span:
                # Set correlation ID
                correlation_id = self._get_or_create_correlation_id(request)
                span.set_attribute("correlation.id", correlation_id)
                
                # Add trace context to request state
                request.state.trace_span = span
                request.state.correlation_id = correlation_id
                
                # Process request
                start_time = time.time()
                
                try:
                    response = await call_next(request)
                    
                    # Add response attributes
                    self._add_response_attributes(span, response, time.time() - start_time)
                    
                    # Inject trace context into response headers
                    self._inject_trace_context(response, span)
                    
                    return response
                    
                except Exception as e:
                    # Record exception in span
                    span.record_exception(e)
                    span.set_status(SpanStatus.ERROR, str(e))
                    
                    # Re-raise the exception
                    raise
        
        except Exception as e:
            self._logger.error(f"Error in tracing middleware: {e}")
            # Continue processing even if tracing fails
            return await call_next(request)
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from tracing."""
        return any(path.startswith(exclude_path) for exclude_path in self.exclude_paths)
    
    def _extract_trace_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract trace context from request headers."""
        try:
            if not OPENTELEMETRY_AVAILABLE:
                return None
            
            # Convert headers to dict for propagation
            headers = dict(request.headers)
            
            # Extract context using OpenTelemetry propagators
            context = propagate.extract(headers)
            
            return context
            
        except Exception as e:
            self._logger.warning(f"Failed to extract trace context: {e}")
            return None
    
    def _inject_trace_context(self, response: Response, span: Span) -> None:
        """Inject trace context into response headers."""
        try:
            if not OPENTELEMETRY_AVAILABLE:
                return
            
            # Add trace ID to response headers
            response.headers["X-Trace-Id"] = span.trace_id
            response.headers["X-Span-Id"] = span.span_id
            
            # Inject context using OpenTelemetry propagators
            carrier = {}
            propagate.inject(carrier)
            
            # Add propagated headers to response
            for key, value in carrier.items():
                response.headers[f"X-{key}"] = value
                
        except Exception as e:
            self._logger.warning(f"Failed to inject trace context: {e}")
    
    def _get_request_attributes(self, request: Request) -> Dict[str, Any]:
        """Get attributes for request span."""
        attributes = {
            # HTTP attributes
            "http.method": request.method,
            "http.url": str(request.url),
            "http.scheme": request.url.scheme,
            "http.host": request.url.hostname or "unknown",
            "http.target": request.url.path,
            "http.user_agent": request.headers.get("user-agent", "unknown"),
            
            # Server attributes
            "net.host.name": request.url.hostname or "unknown",
            "net.host.port": request.url.port or (443 if request.url.scheme == "https" else 80),
            
            # Custom attributes
            "service.name": self.config.service_name,
            "service.version": self.config.service_version or "unknown"
        }
        
        # Add query parameters (sanitized)
        if request.url.query:
            attributes["http.query_string"] = self._sanitize_query_string(request.url.query)
        
        # Add request headers (sanitized)
        if self.sanitize_headers:
            headers = self._sanitize_headers(dict(request.headers))
            for key, value in headers.items():
                attributes[f"http.request.header.{key}"] = value
        
        # Add client IP
        client_ip = self._get_client_ip(request)
        if client_ip:
            attributes["net.peer.ip"] = client_ip
        
        return attributes
    
    def _add_response_attributes(self, span: Span, response: Response, duration: float) -> None:
        """Add response attributes to span."""
        try:
            # HTTP response attributes
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response.duration_ms", duration * 1000)
            
            # Set span status based on HTTP status code
            if response.status_code >= 400:
                if response.status_code >= 500:
                    span.set_status(SpanStatus.ERROR, f"HTTP {response.status_code}")
                else:
                    span.set_status(SpanStatus.ERROR, f"HTTP {response.status_code}")
            else:
                span.set_status(SpanStatus.OK)
            
            # Add response headers (sanitized)
            if self.sanitize_headers:
                headers = self._sanitize_headers(dict(response.headers))
                for key, value in headers.items():
                    span.set_attribute(f"http.response.header.{key}", value)
            
            # Add response size if available
            content_length = response.headers.get("content-length")
            if content_length:
                span.set_attribute("http.response.body.size", int(content_length))
                
        except Exception as e:
            self._logger.warning(f"Failed to add response attributes: {e}")
    
    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Get or create correlation ID for request."""
        # Check for existing correlation ID in headers
        correlation_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id") or
            request.headers.get("correlation-id") or
            request.headers.get("request-id")
        )
        
        if not correlation_id:
            # Generate new correlation ID
            correlation_id = str(uuid.uuid4())
        
        return correlation_id
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Get client IP address from request."""
        # Check forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check other common headers
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers by removing sensitive information."""
        sanitized = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            
            if key_lower in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            elif "password" in key_lower or "secret" in key_lower or "token" in key_lower:
                sanitized[key] = "[REDACTED]"
            else:
                # Truncate long values
                if len(value) > 256:
                    sanitized[key] = value[:256] + "..."
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _sanitize_query_string(self, query_string: str) -> str:
        """Sanitize query string by removing sensitive parameters."""
        try:
            from urllib.parse import parse_qs, urlencode
            
            params = parse_qs(query_string)
            sanitized_params = {}
            
            for key, values in params.items():
                key_lower = key.lower()
                
                if any(sensitive in key_lower for sensitive in ["password", "secret", "token", "key"]):
                    sanitized_params[key] = ["[REDACTED]"]
                else:
                    sanitized_params[key] = values
            
            return urlencode(sanitized_params, doseq=True)
            
        except Exception:
            return "[SANITIZATION_ERROR]"


class FastAPITracingMiddleware:
    """Factory for creating FastAPI tracing middleware."""
    
    @staticmethod
    def create(
        config: Optional[TracingConfig] = None,
        tracer_name: str = "fastapi-http",
        exclude_paths: Optional[List[str]] = None,
        **kwargs
    ) -> TracingMiddleware:
        """Create tracing middleware with configuration."""
        return TracingMiddleware(
            app=None,  # Will be set by FastAPI
            config=config,
            tracer_name=tracer_name,
            exclude_paths=exclude_paths,
            **kwargs
        )


def create_tracing_middleware(
    config: Optional[TracingConfig] = None,
    **kwargs
) -> Callable:
    """Create tracing middleware function for FastAPI."""
    
    def middleware_factory(app: ASGIApp) -> TracingMiddleware:
        return TracingMiddleware(app, config, **kwargs)
    
    return middleware_factory


# Utility functions for manual tracing in FastAPI routes
def get_current_trace_info(request: Request) -> Optional[Dict[str, Any]]:
    """Get current trace information from request."""
    try:
        if hasattr(request.state, 'trace_span'):
            span = request.state.trace_span
            return {
                'trace_id': span.trace_id,
                'span_id': span.span_id,
                'correlation_id': getattr(request.state, 'correlation_id', None)
            }
        
        return None
        
    except Exception:
        return None


def add_trace_attribute(request: Request, key: str, value: Any) -> None:
    """Add attribute to current trace span."""
    try:
        if hasattr(request.state, 'trace_span'):
            request.state.trace_span.set_attribute(key, value)
    except Exception:
        pass


def add_trace_event(request: Request, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add event to current trace span."""
    try:
        if hasattr(request.state, 'trace_span'):
            request.state.trace_span.add_event(name, attributes)
    except Exception:
        pass


def record_trace_exception(request: Request, exception: Exception) -> None:
    """Record exception in current trace span."""
    try:
        if hasattr(request.state, 'trace_span'):
            request.state.trace_span.record_exception(exception)
    except Exception:
        pass


# Export main classes and functions
__all__ = [
    'TracingMiddleware',
    'FastAPITracingMiddleware',
    'create_tracing_middleware',
    'get_current_trace_info',
    'add_trace_attribute',
    'add_trace_event',
    'record_trace_exception',
    'FASTAPI_AVAILABLE',
    'OPENTELEMETRY_AVAILABLE',
]
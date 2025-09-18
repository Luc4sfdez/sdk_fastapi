"""
FastAPI middleware for automatic HTTP metrics collection.

This module provides middleware components that automatically collect
HTTP request/response metrics for FastAPI applications.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from urllib.parse import urlparse

try:
    from fastapi import FastAPI, Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    Request = None
    Response = None
    BaseHTTPMiddleware = None
    ASGIApp = None

from .collector import HTTPMetricsCollector
from .exporter import PrometheusExporter
from .registry import MetricRegistry, get_global_registry
from .exceptions import HTTPMetricsError, handle_http_metrics_error


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Prometheus metrics collection."""
    
    def __init__(
        self,
        app: ASGIApp,
        registry: Optional[MetricRegistry] = None,
        metrics_endpoint: str = "/metrics",
        exclude_paths: Optional[List[str]] = None,
        include_paths: Optional[List[str]] = None,
        group_paths: bool = True,
        track_request_size: bool = True,
        track_response_size: bool = True,
        track_in_progress: bool = True
    ):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for PrometheusMiddleware")
        
        super().__init__(app)
        
        self.registry = registry or get_global_registry()
        self.metrics_endpoint = metrics_endpoint
        self.exclude_paths = set(exclude_paths or [])
        self.include_paths = set(include_paths or []) if include_paths else None
        self.group_paths = group_paths
        
        # Add metrics endpoint to excluded paths
        self.exclude_paths.add(metrics_endpoint)
        
        # Create HTTP metrics collector
        collector_config = {
            'registry': self.registry,
            'track_request_size': track_request_size,
            'track_response_size': track_response_size,
            'track_in_progress': track_in_progress,
            'enabled': True
        }
        
        self.http_collector = HTTPMetricsCollector(config=collector_config)
        self.exporter = PrometheusExporter(self.registry)
        
        self.logger = logging.getLogger("observability.prometheus_middleware")
        
        # Path grouping patterns
        self.path_patterns = {
            r'/api/v\d+/users/\d+': '/api/v{version}/users/{id}',
            r'/api/v\d+/items/\d+': '/api/v{version}/items/{id}',
            r'/files/[^/]+': '/files/{filename}',
            r'/docs.*': '/docs',
            r'/redoc.*': '/redoc',
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request and collect metrics."""
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Handle metrics endpoint
        if request.url.path == self.metrics_endpoint:
            return await self._handle_metrics_endpoint(request)
        
        # Start request tracking
        start_time = time.time()
        self.http_collector.start_request()
        
        try:
            # Get request size
            request_size = await self._get_request_size(request)
            
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Get response size
            response_size = self._get_response_size(response)
            
            # Record metrics
            endpoint = self._normalize_endpoint(request.url.path)
            
            self.http_collector.record_request(
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration_seconds=duration,
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            endpoint = self._normalize_endpoint(request.url.path)
            
            try:
                self.http_collector.record_request(
                    method=request.method,
                    endpoint=endpoint,
                    status_code=500,
                    duration_seconds=duration
                )
            except Exception as metrics_error:
                self.logger.error(f"Failed to record error metrics: {metrics_error}")
            
            raise
        
        finally:
            # End request tracking
            self.http_collector.end_request()
    
    async def _handle_metrics_endpoint(self, request: Request) -> Response:
        """Handle the metrics endpoint request."""
        try:
            metrics_content = self.exporter.export_metrics()
            
            return Response(
                content=metrics_content,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return Response(
                content="# Failed to export metrics\n",
                status_code=500,
                media_type="text/plain"
            )
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from metrics."""
        # Check explicit exclusions
        if path in self.exclude_paths:
            return True
        
        # Check if path matches any exclusion pattern
        for exclude_pattern in self.exclude_paths:
            if '*' in exclude_pattern:
                # Simple wildcard matching
                if exclude_pattern.replace('*', '') in path:
                    return True
        
        # Check inclusions (if specified)
        if self.include_paths is not None:
            if path not in self.include_paths:
                # Check if path matches any inclusion pattern
                for include_pattern in self.include_paths:
                    if '*' in include_pattern:
                        if include_pattern.replace('*', '') in path:
                            return False
                return True
        
        return False
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics grouping."""
        if not self.group_paths:
            return path
        
        # Apply path grouping patterns
        import re
        for pattern, replacement in self.path_patterns.items():
            if re.match(pattern, path):
                return replacement
        
        # Default grouping for paths with IDs
        normalized = re.sub(r'/\d+', '/{id}', path)
        normalized = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', normalized)  # UUIDs
        normalized = re.sub(r'/[a-f0-9]{24}', '/{objectid}', normalized)  # MongoDB ObjectIds
        
        return normalized
    
    async def _get_request_size(self, request: Request) -> Optional[int]:
        """Get request content length."""
        try:
            content_length = request.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            # For requests without content-length, try to read body
            if hasattr(request, '_body'):
                return len(request._body) if request._body else 0
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get request size: {e}")
            return None
    
    def _get_response_size(self, response: Response) -> Optional[int]:
        """Get response content length."""
        try:
            # Check content-length header
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            # For responses with body, estimate size
            if hasattr(response, 'body') and response.body:
                return len(response.body)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to get response size: {e}")
            return None


class MetricsMiddleware(BaseHTTPMiddleware):
    """Generic metrics middleware with configurable collectors."""
    
    def __init__(
        self,
        app: ASGIApp,
        collectors: Optional[List[HTTPMetricsCollector]] = None,
        registry: Optional[MetricRegistry] = None,
        exclude_paths: Optional[List[str]] = None,
        include_paths: Optional[List[str]] = None
    ):
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI is required for MetricsMiddleware")
        
        super().__init__(app)
        
        self.registry = registry or get_global_registry()
        self.collectors = collectors or []
        self.exclude_paths = set(exclude_paths or [])
        self.include_paths = set(include_paths or []) if include_paths else None
        
        self.logger = logging.getLogger("observability.metrics_middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request with multiple collectors."""
        # Check if path should be excluded
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # Start request tracking for all collectors
        start_time = time.time()
        for collector in self.collectors:
            collector.start_request()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics with all collectors
            for collector in self.collectors:
                try:
                    collector.record_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=response.status_code,
                        duration_seconds=duration
                    )
                except Exception as e:
                    self.logger.error(f"Collector {collector.name} failed to record metrics: {e}")
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            
            for collector in self.collectors:
                try:
                    collector.record_request(
                        method=request.method,
                        endpoint=request.url.path,
                        status_code=500,
                        duration_seconds=duration
                    )
                except Exception as metrics_error:
                    self.logger.error(f"Collector {collector.name} failed to record error metrics: {metrics_error}")
            
            raise
        
        finally:
            # End request tracking for all collectors
            for collector in self.collectors:
                collector.end_request()
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from metrics."""
        if path in self.exclude_paths:
            return True
        
        if self.include_paths is not None and path not in self.include_paths:
            return True
        
        return False


# Utility functions for FastAPI integration

def add_prometheus_middleware(
    app: FastAPI,
    registry: Optional[MetricRegistry] = None,
    metrics_endpoint: str = "/metrics",
    exclude_paths: Optional[List[str]] = None,
    **kwargs
) -> PrometheusMiddleware:
    """Add Prometheus middleware to FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for Prometheus middleware")
    
    middleware = PrometheusMiddleware(
        app=app,
        registry=registry,
        metrics_endpoint=metrics_endpoint,
        exclude_paths=exclude_paths,
        **kwargs
    )
    
    app.add_middleware(PrometheusMiddleware, **{
        'registry': registry,
        'metrics_endpoint': metrics_endpoint,
        'exclude_paths': exclude_paths,
        **kwargs
    })
    
    return middleware


def add_metrics_middleware(
    app: FastAPI,
    collectors: Optional[List[HTTPMetricsCollector]] = None,
    registry: Optional[MetricRegistry] = None,
    exclude_paths: Optional[List[str]] = None,
    **kwargs
) -> MetricsMiddleware:
    """Add generic metrics middleware to FastAPI application."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required for metrics middleware")
    
    middleware = MetricsMiddleware(
        app=app,
        collectors=collectors,
        registry=registry,
        exclude_paths=exclude_paths,
        **kwargs
    )
    
    app.add_middleware(MetricsMiddleware, **{
        'collectors': collectors,
        'registry': registry,
        'exclude_paths': exclude_paths,
        **kwargs
    })
    
    return middleware


# Decorator for manual metrics collection

def collect_metrics(
    collector: Optional[HTTPMetricsCollector] = None,
    endpoint_name: Optional[str] = None
):
    """Decorator for manual HTTP metrics collection."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if collector is None:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            collector.start_request()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Extract request info if available
                method = "UNKNOWN"
                endpoint = endpoint_name or func.__name__
                status_code = 200
                
                # Try to extract from FastAPI request context
                for arg in args:
                    if hasattr(arg, 'method'):
                        method = arg.method
                        endpoint = endpoint_name or arg.url.path
                        break
                
                collector.record_request(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration_seconds=duration
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                collector.record_request(
                    method="UNKNOWN",
                    endpoint=endpoint_name or func.__name__,
                    status_code=500,
                    duration_seconds=duration
                )
                
                raise
            
            finally:
                collector.end_request()
        
        return wrapper
    return decorator
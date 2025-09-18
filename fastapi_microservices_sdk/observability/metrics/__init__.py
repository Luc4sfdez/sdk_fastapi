"""
Metrics collection system for FastAPI Microservices SDK.

This module provides comprehensive metrics collection capabilities including
Prometheus integration, system metrics, custom metrics, and HTTP middleware
for automatic request/response metrics collection.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .collector import (
    MetricsCollector,
    SystemMetricsCollector,
    HTTPMetricsCollector
)
from .registry import (
    MetricRegistry,
    MetricInfo,
    MetricCollisionError
)
from .types import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricType,
    MetricValue
)
from .middleware import (
    PrometheusMiddleware,
    MetricsMiddleware
)
from .exporter import (
    PrometheusExporter,
    MetricsExporter
)
from .exceptions import (
    MetricsError,
    MetricsCollectionError,
    MetricsExportError,
    MetricRegistrationError
)

__all__ = [
    # Core collectors
    'MetricsCollector',
    'SystemMetricsCollector', 
    'HTTPMetricsCollector',
    
    # Registry
    'MetricRegistry',
    'MetricInfo',
    'MetricCollisionError',
    
    # Metric types
    'Counter',
    'Gauge',
    'Histogram',
    'Summary',
    'MetricType',
    'MetricValue',
    
    # Middleware
    'PrometheusMiddleware',
    'MetricsMiddleware',
    
    # Exporters
    'PrometheusExporter',
    'MetricsExporter',
    
    # Exceptions
    'MetricsError',
    'MetricsCollectionError',
    'MetricsExportError',
    'MetricRegistrationError',
]
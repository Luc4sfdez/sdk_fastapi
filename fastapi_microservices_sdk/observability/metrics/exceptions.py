"""
Metrics-specific exceptions.

This module defines custom exceptions for metrics operations,
providing detailed error information for debugging and monitoring.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from ..exceptions import ObservabilityError


class MetricsError(ObservabilityError):
    """Base exception for metrics-related errors."""
    
    def __init__(
        self,
        message: str,
        metric_name: Optional[str] = None,
        metric_type: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        super().__init__(message, component="metrics", **kwargs)
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.labels = labels or {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            'metric_name': self.metric_name,
            'metric_type': self.metric_type,
            'labels': self.labels
        })
        return data


class MetricsCollectionError(MetricsError):
    """Exception raised during metrics collection."""
    
    def __init__(
        self,
        message: str,
        collection_source: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="collect", **kwargs)
        self.collection_source = collection_source


class MetricsExportError(MetricsError):
    """Exception raised during metrics export."""
    
    def __init__(
        self,
        message: str,
        export_destination: Optional[str] = None,
        export_format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="export", **kwargs)
        self.export_destination = export_destination
        self.export_format = export_format


class MetricRegistrationError(MetricsError):
    """Exception raised during metric registration."""
    
    def __init__(
        self,
        message: str,
        registration_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="register", **kwargs)
        self.registration_type = registration_type


class MetricCollisionError(MetricRegistrationError):
    """Exception raised when metric names collide."""
    
    def __init__(
        self,
        message: str,
        existing_metric: Optional[str] = None,
        conflicting_metric: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, registration_type="collision", **kwargs)
        self.existing_metric = existing_metric
        self.conflicting_metric = conflicting_metric


class MetricValidationError(MetricsError):
    """Exception raised during metric validation."""
    
    def __init__(
        self,
        message: str,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="validate", **kwargs)
        self.validation_rule = validation_rule


class PrometheusIntegrationError(MetricsError):
    """Exception raised for Prometheus integration errors."""
    
    def __init__(
        self,
        message: str,
        prometheus_operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="prometheus_integration", **kwargs)
        self.prometheus_operation = prometheus_operation


class SystemMetricsError(MetricsCollectionError):
    """Exception raised during system metrics collection."""
    
    def __init__(
        self,
        message: str,
        system_component: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, collection_source="system", **kwargs)
        self.system_component = system_component


class HTTPMetricsError(MetricsCollectionError):
    """Exception raised during HTTP metrics collection."""
    
    def __init__(
        self,
        message: str,
        http_method: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, collection_source="http", **kwargs)
        self.http_method = http_method
        self.endpoint = endpoint
        self.status_code = status_code


# Utility functions for error handling

def handle_prometheus_error(error: Exception, operation: str, metric_name: Optional[str] = None) -> PrometheusIntegrationError:
    """Convert Prometheus client errors to our exception format."""
    return PrometheusIntegrationError(
        message=f"Prometheus {operation} failed: {str(error)}",
        prometheus_operation=operation,
        metric_name=metric_name,
        original_error=error
    )


def handle_system_metrics_error(error: Exception, component: str) -> SystemMetricsError:
    """Convert system metrics errors to our exception format."""
    return SystemMetricsError(
        message=f"System metrics collection failed for {component}: {str(error)}",
        system_component=component,
        original_error=error
    )


def handle_http_metrics_error(
    error: Exception,
    method: Optional[str] = None,
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None
) -> HTTPMetricsError:
    """Convert HTTP metrics errors to our exception format."""
    return HTTPMetricsError(
        message=f"HTTP metrics collection failed: {str(error)}",
        http_method=method,
        endpoint=endpoint,
        status_code=status_code,
        original_error=error
    )
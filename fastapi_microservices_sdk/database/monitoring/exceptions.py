"""
Monitoring-specific exceptions for the database monitoring system.

This module defines custom exceptions for monitoring operations,
providing detailed error information and context.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import DatabaseError


class MonitoringError(DatabaseError):
    """Base exception for monitoring-related errors."""
    
    def __init__(
        self,
        message: str,
        database_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error=original_error, context=context)
        self.database_name = database_name
        self.metric_name = metric_name


class MetricsCollectionError(MonitoringError):
    """Exception raised when metrics collection fails."""
    
    def __init__(
        self,
        message: str,
        database_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        collection_stage: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, database_name=database_name, metric_name=metric_name, **kwargs)
        self.collection_stage = collection_stage


class AnalyticsError(MonitoringError):
    """Exception raised during analytics processing."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.analysis_type = analysis_type


class AlertingError(MonitoringError):
    """Exception raised during alerting operations."""
    
    def __init__(
        self,
        message: str,
        alert_channel: Optional[str] = None,
        alert_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.alert_channel = alert_channel
        self.alert_type = alert_type


class ConfigurationError(MonitoringError):
    """Exception raised for monitoring configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key


class StorageError(MonitoringError):
    """Exception raised for metrics storage errors."""
    
    def __init__(
        self,
        message: str,
        storage_backend: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.storage_backend = storage_backend
        self.operation = operation
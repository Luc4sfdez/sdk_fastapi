"""
Observability Exceptions - Custom exceptions for observability components

This module defines custom exceptions used throughout the observability system.
"""


class ObservabilityError(Exception):
    """Base exception for observability-related errors."""
    pass


class MetricsError(ObservabilityError):
    """Exception raised for metrics-related errors."""
    pass


class TracingError(ObservabilityError):
    """Exception raised for tracing-related errors."""
    pass


class LoggingError(ObservabilityError):
    """Exception raised for logging-related errors."""
    pass


class HealthCheckError(ObservabilityError):
    """Exception raised for health check-related errors."""
    pass


class AlertError(ObservabilityError):
    """Exception raised for alert-related errors."""
    pass


class AlertingError(ObservabilityError):
    """Exception raised for alerting system errors."""
    pass


class ConfigurationError(ObservabilityError):
    """Exception raised for configuration-related errors."""
    pass


class ConnectionError(ObservabilityError):
    """Exception raised for connection-related errors."""
    pass


class TimeoutError(ObservabilityError):
    """Exception raised for timeout-related errors."""
    pass


class ValidationError(ObservabilityError):
    """Exception raised for validation-related errors."""
    pass


class ComponentStatus:
    """Component status information."""
    
    def __init__(self, name: str, status: str, message: str = ""):
        self.name = name
        self.status = status
        self.message = message
        self.timestamp = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp
        }
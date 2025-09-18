# fastapi-microservices-sdk/fastapi_microservices_sdk/exceptions.py 
"""
Exception classes for FastAPI Microservices SDK.

This module defines all custom exceptions used throughout the SDK.
"""

from typing import Optional, Dict, Any


class SDKError(Exception):
    """Base exception for all SDK errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ServiceError(SDKError):
    """Exception raised for service-related errors."""
    pass


class CommunicationError(SDKError):
    """Exception raised for communication errors between services."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, 
                 status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        self.status_code = status_code
        super().__init__(message, details)


class DiscoveryError(SDKError):
    """Exception raised for service discovery errors."""
    pass


class ConfigurationError(SDKError):
    """Exception raised for configuration errors."""
    pass


class ValidationError(SDKError):
    """Exception raised for validation errors."""
    pass


class TimeoutError(SDKError):
    """Exception raised for timeout errors."""
    pass


class CircuitBreakerError(SDKError):
    """Exception raised when circuit breaker is open."""
    pass


class SecurityError(SDKError):
    """Exception raised for security-related errors."""
    pass
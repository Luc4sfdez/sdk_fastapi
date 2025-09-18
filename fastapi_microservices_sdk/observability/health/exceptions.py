"""
Health monitoring exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the health monitoring system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import ObservabilityError


class HealthCheckError(ObservabilityError):
    """Base exception for health check related errors."""
    
    def __init__(
        self,
        message: str,
        check_name: Optional[str] = None,
        check_type: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error, context)
        self.check_name = check_name
        self.check_type = check_type


class HealthTimeoutError(HealthCheckError):
    """Exception raised when health check times out."""
    
    def __init__(
        self,
        message: str,
        check_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            check_name=check_name,
            check_type="timeout",
            original_error=original_error,
            context={
                'timeout_seconds': timeout_seconds
            }
        )
        self.timeout_seconds = timeout_seconds


class DependencyHealthError(HealthCheckError):
    """Exception raised when dependency health check fails."""
    
    def __init__(
        self,
        message: str,
        dependency_name: Optional[str] = None,
        dependency_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            check_name=dependency_name,
            check_type="dependency",
            original_error=original_error,
            context={
                'dependency_type': dependency_type,
                'endpoint': endpoint
            }
        )
        self.dependency_name = dependency_name
        self.dependency_type = dependency_type
        self.endpoint = endpoint


class ProbeConfigurationError(HealthCheckError):
    """Exception raised when probe configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        probe_type: Optional[str] = None,
        configuration_field: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            check_type="probe_configuration",
            original_error=original_error,
            context={
                'probe_type': probe_type,
                'configuration_field': configuration_field
            }
        )
        self.probe_type = probe_type
        self.configuration_field = configuration_field


class CircuitBreakerError(HealthCheckError):
    """Exception raised when circuit breaker operations fail."""
    
    def __init__(
        self,
        message: str,
        circuit_name: Optional[str] = None,
        circuit_state: Optional[str] = None,
        failure_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            check_name=circuit_name,
            check_type="circuit_breaker",
            original_error=original_error,
            context={
                'circuit_state': circuit_state,
                'failure_count': failure_count
            }
        )
        self.circuit_name = circuit_name
        self.circuit_state = circuit_state
        self.failure_count = failure_count


class HealthRegistryError(HealthCheckError):
    """Exception raised when health registry operations fail."""
    
    def __init__(
        self,
        message: str,
        registry_operation: Optional[str] = None,
        check_name: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            check_name=check_name,
            check_type="registry",
            original_error=original_error,
            context={
                'registry_operation': registry_operation
            }
        )
        self.registry_operation = registry_operation


# Export all exceptions
__all__ = [
    'HealthCheckError',
    'HealthTimeoutError',
    'DependencyHealthError',
    'ProbeConfigurationError',
    'CircuitBreakerError',
    'HealthRegistryError',
]
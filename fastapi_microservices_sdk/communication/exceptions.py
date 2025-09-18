"""
Communication Exceptions for FastAPI Microservices SDK.

This module defines the exception hierarchy for all communication-related errors
including message brokers, HTTP clients, service discovery, gRPC, and event sourcing.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CommunicationErrorContext:
    """Context information for communication errors."""
    service_name: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'service_name': self.service_name,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'correlation_id': self.correlation_id,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


class CommunicationError(Exception):
    """Base exception for all communication-related errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[CommunicationErrorContext] = None,
        cause: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message)
        self.message = message
        self.context = context or CommunicationErrorContext(**kwargs)
        self.cause = cause


class CommunicationTimeoutError(CommunicationError):
    """Exception raised when communication operations timeout."""
    pass


class CommunicationConnectionError(CommunicationError):
    """Exception raised when connection to service fails."""
    pass


class CommunicationAuthenticationError(CommunicationError):
    """Exception raised when authentication fails."""
    pass


class CommunicationRateLimitError(CommunicationError):
    """Exception raised when rate limits are exceeded."""
    pass
    
    def __str__(self) -> str:
        """String representation of the error."""
        base_msg = self.message
        if self.context.service_name:
            base_msg += f" (service: {self.context.service_name})"
        if self.context.correlation_id:
            base_msg += f" (correlation_id: {self.context.correlation_id})"
        return base_msg
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'context': self.context.to_dict(),
            'cause': str(self.cause) if self.cause else None
        }


# Message Broker Exceptions
class MessageBrokerError(CommunicationError):
    """Base exception for message broker errors."""
    pass


class MessageBrokerConnectionError(MessageBrokerError):
    """Exception raised when message broker connection fails."""
    pass


class MessageBrokerAuthenticationError(MessageBrokerError):
    """Exception raised when message broker authentication fails."""
    pass


class MessagePublishError(MessageBrokerError):
    """Exception raised when message publishing fails."""
    pass


class MessageConsumptionError(MessageBrokerError):
    """Exception raised when message consumption fails."""
    pass


class DeadLetterQueueError(MessageBrokerError):
    """Exception raised when dead letter queue operations fail."""
    pass


class MessageSerializationError(MessageBrokerError):
    """Exception raised when message serialization/deserialization fails."""
    pass


# HTTP Client Exceptions
class HTTPClientError(CommunicationError):
    """Base exception for HTTP client errors."""
    pass


class HTTPConnectionError(HTTPClientError):
    """Exception raised when HTTP connection fails."""
    pass


class HTTPTimeoutError(HTTPClientError):
    """Exception raised when HTTP request times out."""
    pass


class HTTPRetryExhaustedError(HTTPClientError):
    """Exception raised when all HTTP retry attempts are exhausted."""
    pass


class CircuitBreakerOpenError(HTTPClientError):
    """Exception raised when circuit breaker is open."""
    pass


class LoadBalancerError(HTTPClientError):
    """Exception raised when load balancer operations fail."""
    pass


class HTTPResponseError(HTTPClientError):
    """Exception raised for HTTP response errors."""
    pass


# Service Discovery Exceptions
class ServiceDiscoveryError(CommunicationError):
    """Base exception for service discovery errors."""
    pass


class ServiceRegistrationError(ServiceDiscoveryError):
    """Exception raised when service registration fails."""
    pass


class ServiceDeregistrationError(ServiceDiscoveryError):
    """Exception raised when service deregistration fails."""
    pass


class ServiceNotFoundError(ServiceDiscoveryError):
    """Exception raised when service is not found."""
    pass


class ServiceDiscoveryConnectionError(ServiceDiscoveryError):
    """Exception raised when service discovery connection fails."""
    pass


class HealthCheckError(ServiceDiscoveryError):
    """Exception raised when health check fails."""
    pass


# gRPC Exceptions
class GRPCError(CommunicationError):
    """Base exception for gRPC errors."""
    pass


class GRPCConnectionError(GRPCError):
    """Exception raised when gRPC connection fails."""
    pass


class GRPCAuthenticationError(GRPCError):
    """Exception raised when gRPC authentication fails."""
    pass


class GRPCTimeoutError(GRPCError):
    """Exception raised when gRPC request times out."""
    pass


class GRPCStreamingError(GRPCError):
    """Exception raised when gRPC streaming fails."""
    pass


class GRPCCodeGenerationError(GRPCError):
    """Exception raised when gRPC code generation fails."""
    pass


class GRPCServerError(GRPCError):
    """Exception raised when gRPC server operations fail."""
    pass


class GRPCClientError(GRPCError):
    """Exception raised when gRPC client operations fail."""
    pass


# Event Sourcing Exceptions
class EventSourcingError(CommunicationError):
    """Base exception for event sourcing errors."""
    pass


class EventStoreError(EventSourcingError):
    """Exception raised when event store operations fail."""
    pass


class EventSerializationError(EventSourcingError):
    """Exception raised when event serialization fails."""
    pass


class EventHandlerError(EventSourcingError):
    """Exception raised when event handler fails."""
    pass


class SagaError(EventSourcingError):
    """Exception raised when saga operations fail."""
    pass


class ProjectionError(EventSourcingError):
    """Exception raised when projection operations fail."""
    pass


class CQRSError(EventSourcingError):
    """Exception raised when CQRS operations fail."""
    pass


# Configuration Exceptions
class CommunicationConfigurationError(CommunicationError):
    """Exception raised for communication configuration errors."""
    pass


class InvalidConfigurationError(CommunicationConfigurationError):
    """Exception raised when configuration is invalid."""
    pass


class MissingConfigurationError(CommunicationConfigurationError):
    """Exception raised when required configuration is missing."""
    pass


class ConfigurationValidationError(CommunicationConfigurationError):
    """Exception raised when configuration validation fails."""
    pass


# Factory for creating exceptions
class CommunicationExceptionFactory:
    """Factory for creating communication exceptions."""
    
    _exception_map = {
        # Message Broker
        'message_broker': MessageBrokerError,
        'message_broker_connection': MessageBrokerConnectionError,
        'message_broker_auth': MessageBrokerAuthenticationError,
        'message_publish': MessagePublishError,
        'message_consumption': MessageConsumptionError,
        'dead_letter_queue': DeadLetterQueueError,
        'message_serialization': MessageSerializationError,
        
        # HTTP Client
        'http_client': HTTPClientError,
        'http_connection': HTTPConnectionError,
        'http_timeout': HTTPTimeoutError,
        'http_retry_exhausted': HTTPRetryExhaustedError,
        'circuit_breaker_open': CircuitBreakerOpenError,
        'load_balancer': LoadBalancerError,
        'http_response': HTTPResponseError,
        
        # Service Discovery
        'service_discovery': ServiceDiscoveryError,
        'service_registration': ServiceRegistrationError,
        'service_deregistration': ServiceDeregistrationError,
        'service_not_found': ServiceNotFoundError,
        'service_discovery_connection': ServiceDiscoveryConnectionError,
        'health_check': HealthCheckError,
        
        # gRPC
        'grpc': GRPCError,
        'grpc_connection': GRPCConnectionError,
        'grpc_auth': GRPCAuthenticationError,
        'grpc_timeout': GRPCTimeoutError,
        'grpc_streaming': GRPCStreamingError,
        'grpc_codegen': GRPCCodeGenerationError,
        
        # Event Sourcing
        'event_sourcing': EventSourcingError,
        'event_store': EventStoreError,
        'event_serialization': EventSerializationError,
        'event_handler': EventHandlerError,
        'saga': SagaError,
        'projection': ProjectionError,
        'cqrs': CQRSError,
        
        # Configuration
        'communication_config': CommunicationConfigurationError,
        'invalid_config': InvalidConfigurationError,
        'missing_config': MissingConfigurationError,
        'config_validation': ConfigurationValidationError,
    }
    
    @classmethod
    def create_exception(
        self,
        exception_type: str,
        message: str,
        context: Optional[CommunicationErrorContext] = None,
        cause: Optional[Exception] = None,
        **kwargs
    ) -> CommunicationError:
        """Create exception by type name."""
        exception_class = self._exception_map.get(exception_type, CommunicationError)
        return exception_class(message, context, cause, **kwargs)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available exception types."""
        return list(cls._exception_map.keys())


# Utility functions for common error scenarios
def create_timeout_error(
    service_name: str,
    timeout: float,
    correlation_id: Optional[str] = None
) -> HTTPTimeoutError:
    """Create a timeout error with standard context."""
    context = CommunicationErrorContext(
        service_name=service_name,
        correlation_id=correlation_id,
        details={'timeout': timeout}
    )
    return HTTPTimeoutError(
        f"Request to {service_name} timed out after {timeout}s",
        context=context
    )


def create_connection_error(
    service_name: str,
    endpoint: str,
    cause: Exception,
    correlation_id: Optional[str] = None
) -> HTTPConnectionError:
    """Create a connection error with standard context."""
    context = CommunicationErrorContext(
        service_name=service_name,
        endpoint=endpoint,
        correlation_id=correlation_id,
        details={'cause': str(cause)}
    )
    return HTTPConnectionError(
        f"Failed to connect to {service_name} at {endpoint}",
        context=context,
        cause=cause
    )


def create_service_not_found_error(
    service_name: str,
    correlation_id: Optional[str] = None
) -> ServiceNotFoundError:
    """Create a service not found error with standard context."""
    context = CommunicationErrorContext(
        service_name=service_name,
        correlation_id=correlation_id
    )
    return ServiceNotFoundError(
        f"Service {service_name} not found in service discovery",
        context=context
    )


def create_circuit_breaker_error(
    service_name: str,
    correlation_id: Optional[str] = None
) -> CircuitBreakerOpenError:
    """Create a circuit breaker open error with standard context."""
    context = CommunicationErrorContext(
        service_name=service_name,
        correlation_id=correlation_id
    )
    return CircuitBreakerOpenError(
        f"Circuit breaker is open for service {service_name}",
        context=context
    )
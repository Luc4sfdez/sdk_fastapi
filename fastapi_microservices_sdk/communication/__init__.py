# fastapi-microservices-sdk/fastapi_microservices_sdk/communication/__init__.py 
"""
Communication module for FastAPI Microservices SDK.

This module provides comprehensive communication capabilities for microservices
including message brokers, HTTP clients, service discovery, gRPC, and event sourcing.
"""

from .config import (
    CommunicationConfig,
    MessageBrokerConfig,
    HTTPClientConfig,
    ServiceDiscoveryConfig,
    GRPCConfig,
    EventSourcingConfig,
    TimeoutConfig,
    RetryPolicyConfig,
    CircuitBreakerConfig,
    LoadBalancerConfig,
    MessageBrokerType,
    ServiceDiscoveryType,
    LoadBalancingStrategy,
    DEFAULT_COMMUNICATION_CONFIG,
    DEFAULT_RABBITMQ_CONFIG,
    DEFAULT_KAFKA_CONFIG,
    DEFAULT_REDIS_CONFIG,
    DEFAULT_HTTP_CLIENT_CONFIG
)

from .exceptions import (
    CommunicationError,
    CommunicationErrorContext,
    MessageBrokerError,
    MessageBrokerConnectionError,
    MessageBrokerAuthenticationError,
    MessagePublishError,
    MessageConsumptionError,
    MessageSerializationError,
    DeadLetterQueueError,
    HTTPClientError,
    ServiceDiscoveryError,
    GRPCError,
    EventSourcingError,
    CommunicationConfigurationError,
    CommunicationExceptionFactory,
    create_timeout_error,
    create_connection_error,
    create_service_not_found_error,
    create_circuit_breaker_error
)

from .manager import (
    CommunicationManager,
    ComponentStatus,
    get_communication_manager,
    set_communication_manager,
    initialize_communication,
    shutdown_communication
)

# Legacy imports for backward compatibility
from .http import HTTPServiceClient

# Import messaging components conditionally
try:
    from .messaging import RabbitMQClient
    _RABBITMQ_AVAILABLE = True
except ImportError:
    _RABBITMQ_AVAILABLE = False

try:
    from .messaging import RedisPubSubClient
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

__all__ = [
    # Configuration
    "CommunicationConfig",
    "MessageBrokerConfig", 
    "HTTPClientConfig",
    "ServiceDiscoveryConfig",
    "GRPCConfig",
    "EventSourcingConfig",
    "TimeoutConfig",
    "RetryPolicyConfig",
    "CircuitBreakerConfig",
    "LoadBalancerConfig",
    "MessageBrokerType",
    "ServiceDiscoveryType", 
    "LoadBalancingStrategy",
    "DEFAULT_COMMUNICATION_CONFIG",
    "DEFAULT_RABBITMQ_CONFIG",
    "DEFAULT_KAFKA_CONFIG",
    "DEFAULT_REDIS_CONFIG",
    "DEFAULT_HTTP_CLIENT_CONFIG",
    
    # Exceptions
    "CommunicationError",
    "CommunicationErrorContext",
    "MessageBrokerError",
    "MessageBrokerConnectionError",
    "MessageBrokerAuthenticationError", 
    "MessagePublishError",
    "MessageConsumptionError",
    "MessageSerializationError",
    "DeadLetterQueueError",
    "HTTPClientError", 
    "ServiceDiscoveryError",
    "GRPCError",
    "EventSourcingError",
    "CommunicationConfigurationError",
    "CommunicationExceptionFactory",
    "create_timeout_error",
    "create_connection_error",
    "create_service_not_found_error",
    "create_circuit_breaker_error",
    
    # Manager
    "CommunicationManager",
    "ComponentStatus",
    "get_communication_manager",
    "set_communication_manager", 
    "initialize_communication",
    "shutdown_communication",
    
    # Legacy (backward compatibility)
    "HTTPServiceClient"
]

# Add messaging clients if available
if _RABBITMQ_AVAILABLE:
    __all__.append("RabbitMQClient")

if _REDIS_AVAILABLE:
    __all__.append("RedisPubSubClient")

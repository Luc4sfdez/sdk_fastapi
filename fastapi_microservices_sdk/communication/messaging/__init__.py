# fastapi-microservices-sdk/fastapi_microservices_sdk/communication/messaging/__init__.py
"""
Messaging module for FastAPI Microservices SDK.

This module provides message broker implementations and reliability patterns
for robust asynchronous communication between microservices.
"""

from .base import (
    MessageBroker,
    Message,
    MessageAcknowledgment,
    MessageHandler,
    MessageStatus,
    DeliveryMode,
    ReliabilityManager
)

from .reliability import (
    DeadLetterQueue,
    DeadLetterMessage,
    MessageDeduplicator,
    MessagingCircuitBreaker,
    MessageMetrics,
    CircuitBreakerState
)

# Message broker implementations
try:
    from .rabbitmq import (
        RabbitMQClient,
        RabbitMQExchangeConfig,
        RabbitMQQueueConfig,
        RabbitMQBindingConfig,
        RabbitMQExchangeType,
        RabbitMQQueueType,
        create_rabbitmq_client
    )
    _RABBITMQ_AVAILABLE = True
except ImportError:
    _RABBITMQ_AVAILABLE = False

# Kafka implementation
try:
    from .kafka import (
        KafkaClient,
        KafkaProducer,
        KafkaConsumer,
        KafkaMessage,
        KafkaClusterConfig,
        KafkaProducerConfig,
        KafkaConsumerConfig,
        KafkaSecurityConfig,
        KafkaTopicConfig,
        KafkaDeadLetterConfig,
        KafkaSecurityMode,
        KafkaSASLMechanism,
        KafkaCompressionType,
        KafkaOffsetResetStrategy,
        KafkaIsolationLevel,
        KafkaError,
        KafkaConnectionError,
        KafkaProducerError,
        KafkaConsumerError,
        KafkaTransactionError,
        create_kafka_cluster_config,
        create_kafka_producer_config,
        create_kafka_consumer_config,
        create_kafka_security_config,
        create_ssl_context,
    )
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False

# Legacy Redis import (will be updated in future tasks)
try:
    from .redis_pubsub import RedisPubSubClient
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

# Build __all__ list dynamically based on available implementations
__all__ = [
    # Base interfaces
    "MessageBroker",
    "Message",
    "MessageAcknowledgment", 
    "MessageHandler",
    "MessageStatus",
    "DeliveryMode",
    "ReliabilityManager",
    
    # Reliability patterns
    "DeadLetterQueue",
    "DeadLetterMessage",
    "MessageDeduplicator",
    "MessagingCircuitBreaker",
    "MessageMetrics",
    "CircuitBreakerState"
]

# Add RabbitMQ exports if available
if _RABBITMQ_AVAILABLE:
    __all__.extend([
        "RabbitMQClient",
        "RabbitMQExchangeConfig",
        "RabbitMQQueueConfig",
        "RabbitMQBindingConfig", 
        "RabbitMQExchangeType",
        "RabbitMQQueueType",
        "create_rabbitmq_client"
    ])

# Add Kafka exports if available
if _KAFKA_AVAILABLE:
    __all__.extend([
        "KafkaClient",
        "KafkaProducer",
        "KafkaConsumer",
        "KafkaMessage",
        "KafkaClusterConfig",
        "KafkaProducerConfig",
        "KafkaConsumerConfig",
        "KafkaSecurityConfig",
        "KafkaTopicConfig",
        "KafkaDeadLetterConfig",
        "KafkaSecurityMode",
        "KafkaSASLMechanism",
        "KafkaCompressionType",
        "KafkaOffsetResetStrategy",
        "KafkaIsolationLevel",
        "KafkaError",
        "KafkaConnectionError",
        "KafkaProducerError",
        "KafkaConsumerError",
        "KafkaTransactionError",
        "create_kafka_cluster_config",
        "create_kafka_producer_config",
        "create_kafka_consumer_config",
        "create_kafka_security_config",
        "create_ssl_context",
    ])

# Add Redis exports if available
if _REDIS_AVAILABLE:
    __all__.append("RedisPubSubClient")
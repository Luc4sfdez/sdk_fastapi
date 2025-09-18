"""
Communication Configuration for FastAPI Microservices SDK.

This module provides configuration management for all communication components
including message brokers, HTTP clients, service discovery, gRPC, and event sourcing.
"""

import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator, model_validator


class MessageBrokerType(str, Enum):
    """Supported message broker types."""
    RABBITMQ = "rabbitmq"
    KAFKA = "kafka"
    REDIS = "redis"
    MEMORY = "memory"  # For testing


class ServiceDiscoveryType(str, Enum):
    """Supported service discovery types."""
    CONSUL = "consul"
    ETCD = "etcd"
    KUBERNETES = "kubernetes"
    MEMORY = "memory"  # For testing


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TimeoutConfig(BaseModel):
    """Timeout configuration."""
    connection: float = Field(default=5.0, description="Connection timeout in seconds")
    read: float = Field(default=30.0, description="Read timeout in seconds")
    write: float = Field(default=30.0, description="Write timeout in seconds")
    total: float = Field(default=60.0, description="Total timeout in seconds")
    
    @validator('connection', 'read', 'write', 'total')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("Timeout values must be positive")
        return v


class RetryPolicyConfig(BaseModel):
    """Retry policy configuration."""
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    base_delay: float = Field(default=1.0, description="Base delay between retries in seconds")
    max_delay: float = Field(default=60.0, description="Maximum delay between retries in seconds")
    exponential_base: float = Field(default=2.0, description="Exponential backoff base")
    jitter: bool = Field(default=True, description="Add random jitter to delays")
    
    @validator('max_attempts')
    def validate_max_attempts(cls, v):
        if v < 0:
            raise ValueError("Max attempts must be non-negative")
        return v
    
    @validator('base_delay', 'max_delay')
    def validate_delays(cls, v):
        if v <= 0:
            raise ValueError("Delay values must be positive")
        return v


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
    failure_threshold: int = Field(default=5, description="Number of failures to open circuit")
    recovery_timeout: int = Field(default=60, description="Timeout before attempting recovery in seconds")
    success_threshold: int = Field(default=3, description="Number of successes to close circuit")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    
    @validator('failure_threshold', 'success_threshold')
    def validate_thresholds(cls, v):
        if v <= 0:
            raise ValueError("Thresholds must be positive")
        return v


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration."""
    strategy: LoadBalancingStrategy = Field(default=LoadBalancingStrategy.ROUND_ROBIN)
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    unhealthy_threshold: int = Field(default=3, description="Failures to mark as unhealthy")
    healthy_threshold: int = Field(default=2, description="Successes to mark as healthy")
    weights: Dict[str, float] = Field(default_factory=dict, description="Service weights for weighted strategy")


class MessageBrokerSecurityConfig(BaseModel):
    """Message broker security configuration."""
    enable_tls: bool = Field(default=True, description="Enable TLS encryption")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    ca_cert_path: Optional[str] = Field(default=None, description="CA certificate path")
    client_cert_path: Optional[str] = Field(default=None, description="Client certificate path")
    client_key_path: Optional[str] = Field(default=None, description="Client key path")
    username: Optional[str] = Field(default=None, description="Authentication username")
    password: Optional[str] = Field(default=None, description="Authentication password")
    sasl_mechanism: Optional[str] = Field(default=None, description="SASL mechanism for Kafka")


class MessageBrokerConfig(BaseModel):
    """Message broker configuration."""
    type: MessageBrokerType = Field(..., description="Message broker type")
    connection_url: str = Field(..., description="Connection URL")
    connection_pool_size: int = Field(default=10, description="Connection pool size")
    max_connections: int = Field(default=100, description="Maximum connections")
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)
    security: MessageBrokerSecurityConfig = Field(default_factory=MessageBrokerSecurityConfig)
    dead_letter_queue: bool = Field(default=True, description="Enable dead letter queue")
    message_ttl: Optional[int] = Field(default=None, description="Message TTL in seconds")
    
    # Broker-specific configurations
    rabbitmq_config: Dict[str, Any] = Field(default_factory=dict, description="RabbitMQ specific config")
    kafka_config: Dict[str, Any] = Field(default_factory=dict, description="Kafka specific config")
    redis_config: Dict[str, Any] = Field(default_factory=dict, description="Redis specific config")


class HTTPClientConfig(BaseModel):
    """HTTP client configuration."""
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    retry_policy: RetryPolicyConfig = Field(default_factory=RetryPolicyConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    load_balancer: LoadBalancerConfig = Field(default_factory=LoadBalancerConfig)
    connection_pool_size: int = Field(default=100, description="HTTP connection pool size")
    max_keepalive_connections: int = Field(default=20, description="Max keepalive connections")
    keepalive_expiry: float = Field(default=5.0, description="Keepalive expiry in seconds")
    enable_http2: bool = Field(default=False, description="Enable HTTP/2 support")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class ServiceDiscoveryConfig(BaseModel):
    """Service discovery configuration."""
    type: ServiceDiscoveryType = Field(default=ServiceDiscoveryType.MEMORY)
    connection_url: Optional[str] = Field(default=None, description="Service discovery connection URL")
    namespace: Optional[str] = Field(default=None, description="Namespace for service registration")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    service_ttl: int = Field(default=300, description="Service TTL in seconds")
    cache_ttl: int = Field(default=60, description="Discovery cache TTL in seconds")
    
    # Backend-specific configurations
    consul_config: Dict[str, Any] = Field(default_factory=dict, description="Consul specific config")
    etcd_config: Dict[str, Any] = Field(default_factory=dict, description="etcd specific config")
    kubernetes_config: Dict[str, Any] = Field(default_factory=dict, description="Kubernetes specific config")


class GRPCConfig(BaseModel):
    """gRPC configuration."""
    server_port: int = Field(default=50051, description="gRPC server port")
    max_workers: int = Field(default=10, description="Maximum gRPC workers")
    max_message_length: int = Field(default=4 * 1024 * 1024, description="Max message length in bytes")
    keepalive_time: int = Field(default=30, description="Keepalive time in seconds")
    keepalive_timeout: int = Field(default=5, description="Keepalive timeout in seconds")
    keepalive_permit_without_calls: bool = Field(default=True, description="Permit keepalive without calls")
    max_connection_idle: int = Field(default=300, description="Max connection idle time in seconds")
    enable_reflection: bool = Field(default=False, description="Enable gRPC reflection")
    enable_health_check: bool = Field(default=True, description="Enable health check service")
    
    # Security configuration
    enable_tls: bool = Field(default=True, description="Enable TLS")
    server_cert_path: Optional[str] = Field(default=None, description="Server certificate path")
    server_key_path: Optional[str] = Field(default=None, description="Server key path")
    ca_cert_path: Optional[str] = Field(default=None, description="CA certificate path")
    require_client_auth: bool = Field(default=False, description="Require client authentication")


class EventSourcingConfig(BaseModel):
    """Event sourcing configuration."""
    enable_event_store: bool = Field(default=True, description="Enable event store")
    store_type: str = Field(default="memory", description="Event store type (memory, postgresql, mongodb)")
    connection_url: Optional[str] = Field(default=None, description="Event store connection URL")
    snapshot_frequency: int = Field(default=100, description="Snapshot frequency (events)")
    max_events_per_stream: int = Field(default=10000, description="Maximum events per stream")
    enable_projections: bool = Field(default=True, description="Enable event projections")
    projection_batch_size: int = Field(default=100, description="Projection batch size")
    
    # CQRS configuration
    enable_cqrs: bool = Field(default=True, description="Enable CQRS pattern")
    command_timeout: float = Field(default=30.0, description="Command timeout in seconds")
    query_timeout: float = Field(default=10.0, description="Query timeout in seconds")
    
    # Saga configuration
    enable_sagas: bool = Field(default=True, description="Enable saga pattern")
    saga_timeout: float = Field(default=300.0, description="Saga timeout in seconds")
    compensation_timeout: float = Field(default=60.0, description="Compensation timeout in seconds")


class CommunicationConfig(BaseModel):
    """Main communication configuration."""
    
    # Message brokers
    message_brokers: Dict[str, MessageBrokerConfig] = Field(
        default_factory=dict, 
        description="Message broker configurations"
    )
    
    # HTTP clients
    http_clients: Dict[str, HTTPClientConfig] = Field(
        default_factory=dict,
        description="HTTP client configurations"
    )
    
    # Service discovery
    service_discovery: ServiceDiscoveryConfig = Field(
        default_factory=ServiceDiscoveryConfig,
        description="Service discovery configuration"
    )
    
    # gRPC
    grpc: GRPCConfig = Field(
        default_factory=GRPCConfig,
        description="gRPC configuration"
    )
    
    # Event sourcing
    event_sourcing: EventSourcingConfig = Field(
        default_factory=EventSourcingConfig,
        description="Event sourcing configuration"
    )
    
    # Global settings
    enable_security_integration: bool = Field(
        default=True, 
        description="Enable integration with security system"
    )
    enable_observability: bool = Field(
        default=True,
        description="Enable observability features"
    )
    enable_health_checks: bool = Field(
        default=True,
        description="Enable health checks"
    )
    correlation_id_header: str = Field(
        default="X-Correlation-ID",
        description="Correlation ID header name"
    )
    service_name_header: str = Field(
        default="X-Service-Name",
        description="Service name header name"
    )
    
    @model_validator(mode='after')
    def validate_config(self):
        """Validate the entire configuration."""
        # Validate that at least one communication method is configured
        if not self.message_brokers and not self.http_clients and not self.grpc:
            raise ValueError("At least one communication method must be configured")
        
        return self
    
    @classmethod
    def from_env(cls) -> 'CommunicationConfig':
        """Create configuration from environment variables."""
        config_data = {}
        
        # Load basic settings from environment
        if os.getenv('COMMUNICATION_ENABLE_SECURITY'):
            config_data['enable_security_integration'] = os.getenv('COMMUNICATION_ENABLE_SECURITY').lower() == 'true'
        
        if os.getenv('COMMUNICATION_ENABLE_OBSERVABILITY'):
            config_data['enable_observability'] = os.getenv('COMMUNICATION_ENABLE_OBSERVABILITY').lower() == 'true'
        
        # Load service discovery config
        if os.getenv('SERVICE_DISCOVERY_TYPE'):
            config_data['service_discovery'] = {
                'type': os.getenv('SERVICE_DISCOVERY_TYPE'),
                'connection_url': os.getenv('SERVICE_DISCOVERY_URL'),
                'namespace': os.getenv('SERVICE_DISCOVERY_NAMESPACE')
            }
        
        # Load message broker config
        if os.getenv('MESSAGE_BROKER_TYPE'):
            broker_name = os.getenv('MESSAGE_BROKER_NAME', 'default')
            config_data['message_brokers'] = {
                broker_name: {
                    'type': os.getenv('MESSAGE_BROKER_TYPE'),
                    'connection_url': os.getenv('MESSAGE_BROKER_URL', 'amqp://localhost:5672')
                }
            }
        
        # Load gRPC config
        if os.getenv('GRPC_SERVER_PORT'):
            config_data['grpc'] = {
                'server_port': int(os.getenv('GRPC_SERVER_PORT')),
                'enable_tls': os.getenv('GRPC_ENABLE_TLS', 'true').lower() == 'true'
            }
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def get_message_broker_config(self, name: str) -> Optional[MessageBrokerConfig]:
        """Get message broker configuration by name."""
        return self.message_brokers.get(name)
    
    def get_http_client_config(self, name: str) -> Optional[HTTPClientConfig]:
        """Get HTTP client configuration by name."""
        return self.http_clients.get(name)
    
    def add_message_broker(self, name: str, config: MessageBrokerConfig) -> None:
        """Add message broker configuration."""
        self.message_brokers[name] = config
    
    def add_http_client(self, name: str, config: HTTPClientConfig) -> None:
        """Add HTTP client configuration."""
        self.http_clients[name] = config


# Default configurations for common scenarios
DEFAULT_RABBITMQ_CONFIG = MessageBrokerConfig(
    type=MessageBrokerType.RABBITMQ,
    connection_url="amqp://guest:guest@localhost:5672/",
    connection_pool_size=10,
    dead_letter_queue=True
)

DEFAULT_KAFKA_CONFIG = MessageBrokerConfig(
    type=MessageBrokerType.KAFKA,
    connection_url="localhost:9092",
    connection_pool_size=10,
    kafka_config={
        "bootstrap_servers": ["localhost:9092"],
        "client_id": "fastapi-microservices-sdk",
        "group_id": "default-group"
    }
)

DEFAULT_REDIS_CONFIG = MessageBrokerConfig(
    type=MessageBrokerType.REDIS,
    connection_url="redis://localhost:6379/0",
    connection_pool_size=10
)

DEFAULT_HTTP_CLIENT_CONFIG = HTTPClientConfig(
    timeout=TimeoutConfig(),
    retry_policy=RetryPolicyConfig(),
    circuit_breaker=CircuitBreakerConfig(),
    connection_pool_size=100
)

DEFAULT_COMMUNICATION_CONFIG = CommunicationConfig(
    message_brokers={
        "default": DEFAULT_RABBITMQ_CONFIG
    },
    http_clients={
        "default": DEFAULT_HTTP_CLIENT_CONFIG
    },
    service_discovery=ServiceDiscoveryConfig(),
    grpc=GRPCConfig(),
    event_sourcing=EventSourcingConfig()
)
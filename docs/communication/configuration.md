# Configuration Management

El módulo de configuración proporciona gestión centralizada de configuraciones para todos los componentes de comunicación del SDK.

## Arquitectura

### Configuration Classes

El sistema de configuración utiliza Pydantic para validación y tipado:

```python
from fastapi_microservices_sdk.communication.config import (
    CommunicationConfig,
    MessageBrokerConfig,
    HTTPClientConfig,
    ServiceDiscoveryConfig,
    CircuitBreakerConfig
)
```

### Environment-Based Configuration

```python
import os
from fastapi_microservices_sdk.communication.config import CommunicationConfig

# Configuración desde variables de entorno
config = CommunicationConfig.from_env()

# O configuración manual
config = CommunicationConfig(
    message_broker=MessageBrokerConfig(
        type="rabbitmq",
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        username=os.getenv("RABBITMQ_USER", "guest"),
        password=os.getenv("RABBITMQ_PASS", "guest")
    ),
    http_client=HTTPClientConfig(
        timeout=30.0,
        max_retries=3,
        circuit_breaker_enabled=True
    )
)
```

## Message Broker Configuration

### RabbitMQ Configuration

```python
from fastapi_microservices_sdk.communication.config import MessageBrokerConfig, MessageBrokerType

rabbitmq_config = MessageBrokerConfig(
    type=MessageBrokerType.RABBITMQ,
    host="rabbitmq.example.com",
    port=5672,
    username="service_user",
    password="secure_password",
    virtual_host="/production",
    
    # Connection settings
    connection_timeout=10.0,
    heartbeat=600,
    blocked_connection_timeout=300,
    
    # SSL/TLS
    ssl_enabled=True,
    ssl_cert_path="/etc/ssl/certs/client.crt",
    ssl_key_path="/etc/ssl/private/client.key",
    ssl_ca_path="/etc/ssl/certs/ca.crt",
    
    # Exchange settings
    exchange_name="microservices",
    exchange_type="topic",
    exchange_durable=True,
    
    # Queue settings
    queue_durable=True,
    queue_auto_delete=False,
    queue_exclusive=False,
    
    # Message settings
    message_ttl=3600000,  # 1 hour
    max_priority=10,
    
    # Performance
    prefetch_count=10,
    confirm_delivery=True,
    
    # Retry and reliability
    max_retries=3,
    retry_delay=5.0,
    dead_letter_exchange="dlx",
    
    # Monitoring
    enable_metrics=True,
    metrics_interval=60
)
```

### Kafka Configuration

```python
kafka_config = MessageBrokerConfig(
    type=MessageBrokerType.KAFKA,
    bootstrap_servers=["kafka1:9092", "kafka2:9092", "kafka3:9092"],
    
    # Security
    security_protocol="SASL_SSL",
    sasl_mechanism="PLAIN",
    sasl_username="kafka_user",
    sasl_password="kafka_password",
    ssl_ca_location="/etc/ssl/certs/ca.pem",
    ssl_certificate_location="/etc/ssl/certs/client.crt",
    ssl_key_location="/etc/ssl/private/client.key",
    
    # Producer settings
    producer_config={
        "acks": "all",
        "retries": 3,
        "batch_size": 16384,
        "linger_ms": 10,
        "buffer_memory": 33554432,
        "compression_type": "snappy",
        "max_in_flight_requests_per_connection": 5,
        "enable_idempotence": True
    },
    
    # Consumer settings
    consumer_config={
        "group_id": "microservice-group",
        "auto_offset_reset": "earliest",
        "enable_auto_commit": False,
        "max_poll_records": 500,
        "max_poll_interval_ms": 300000,
        "session_timeout_ms": 30000,
        "heartbeat_interval_ms": 3000
    },
    
    # Topic settings
    topic_config={
        "num_partitions": 3,
        "replication_factor": 3,
        "cleanup_policy": "delete",
        "retention_ms": 604800000,  # 7 days
        "segment_ms": 86400000      # 1 day
    }
)
```

### Redis Configuration

```python
redis_config = MessageBrokerConfig(
    type=MessageBrokerType.REDIS,
    host="redis.example.com",
    port=6379,
    password="redis_password",
    db=0,
    
    # Connection pool
    max_connections=20,
    retry_on_timeout=True,
    socket_timeout=5.0,
    socket_connect_timeout=5.0,
    socket_keepalive=True,
    socket_keepalive_options={},
    
    # SSL
    ssl=True,
    ssl_cert_reqs="required",
    ssl_ca_certs="/etc/ssl/certs/ca.crt",
    ssl_certfile="/etc/ssl/certs/client.crt",
    ssl_keyfile="/etc/ssl/private/client.key",
    
    # Pub/Sub settings
    pubsub_patterns=["events.*", "notifications.*"],
    pubsub_ignore_subscribe_messages=True,
    
    # Clustering
    cluster_enabled=True,
    cluster_nodes=[
        {"host": "redis1.example.com", "port": 6379},
        {"host": "redis2.example.com", "port": 6379},
        {"host": "redis3.example.com", "port": 6379}
    ],
    
    # Sentinel
    sentinel_enabled=False,
    sentinel_hosts=[
        {"host": "sentinel1.example.com", "port": 26379},
        {"host": "sentinel2.example.com", "port": 26379}
    ],
    sentinel_service_name="mymaster"
)
```

## HTTP Client Configuration

### Basic HTTP Configuration

```python
from fastapi_microservices_sdk.communication.config import HTTPClientConfig, TimeoutConfig

http_config = HTTPClientConfig(
    base_url="https://api.example.com",
    
    # Timeouts
    timeout=TimeoutConfig(
        connection=10.0,
        read=30.0,
        write=30.0,
        total=60.0
    ),
    
    # Connection pooling
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0,
    
    # Headers
    default_headers={
        "User-Agent": "MyService/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
    },
    
    # SSL/TLS
    verify_ssl=True,
    ssl_cert_path="/etc/ssl/certs/client.crt",
    ssl_key_path="/etc/ssl/private/client.key",
    ssl_ca_path="/etc/ssl/certs/ca.crt",
    
    # Proxy
    proxy_url="http://proxy.example.com:8080",
    proxy_auth=("proxy_user", "proxy_pass"),
    
    # Cookies
    enable_cookies=True,
    cookie_jar_path="/tmp/cookies.jar"
)
```

### Advanced HTTP Configuration

```python
from fastapi_microservices_sdk.communication.config import (
    RetryConfig,
    CircuitBreakerConfig,
    CacheConfig,
    RateLimitConfig
)

advanced_http_config = HTTPClientConfig(
    base_url="https://api.example.com",
    
    # Retry configuration
    retry=RetryConfig(
        max_attempts=5,
        backoff_strategy="exponential",
        base_delay=1.0,
        max_delay=60.0,
        jitter=True,
        retry_on_status_codes=[500, 502, 503, 504],
        retry_on_exceptions=["ConnectionError", "TimeoutError"]
    ),
    
    # Circuit breaker
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        recovery_timeout=60,
        half_open_max_calls=3,
        expected_exceptions=["ConnectionError", "HTTPError"]
    ),
    
    # Caching
    cache=CacheConfig(
        enabled=True,
        backend="redis",
        redis_url="redis://localhost:6379/1",
        default_ttl=300,
        max_size=1000,
        cache_control_header=True,
        etag_support=True
    ),
    
    # Rate limiting
    rate_limit=RateLimitConfig(
        enabled=True,
        requests_per_minute=100,
        burst_size=20,
        storage_backend="redis",
        storage_url="redis://localhost:6379/2"
    ),
    
    # Authentication
    auth_config={
        "type": "bearer",
        "token": "your-jwt-token",
        "auto_refresh": True,
        "refresh_url": "/auth/refresh",
        "refresh_threshold": 300  # Refresh 5 minutes before expiry
    },
    
    # Monitoring
    enable_metrics=True,
    enable_tracing=True,
    trace_headers=["X-Trace-ID", "X-Span-ID"],
    
    # Logging
    log_requests=True,
    log_responses=True,
    log_request_body=False,  # Security consideration
    log_response_body=False,
    max_log_body_size=1024
)
```

## Service Discovery Configuration

### Consul Configuration

```python
from fastapi_microservices_sdk.communication.config import ServiceDiscoveryConfig, ServiceDiscoveryType

consul_config = ServiceDiscoveryConfig(
    type=ServiceDiscoveryType.CONSUL,
    host="consul.example.com",
    port=8500,
    
    # Authentication
    token="consul-token",
    username="consul_user",
    password="consul_password",
    
    # SSL/TLS
    scheme="https",
    verify_ssl=True,
    ssl_cert_path="/etc/ssl/certs/consul.crt",
    ssl_key_path="/etc/ssl/private/consul.key",
    ssl_ca_path="/etc/ssl/certs/ca.crt",
    
    # Service registration
    service_name="user-service",
    service_id="user-service-1",
    service_address="10.0.1.100",
    service_port=8000,
    service_tags=["api", "v1", "users"],
    service_meta={
        "version": "1.0.0",
        "environment": "production",
        "region": "us-east-1"
    },
    
    # Health check
    health_check_url="/health",
    health_check_interval="30s",
    health_check_timeout="10s",
    health_check_deregister_critical_after="5m",
    
    # Discovery settings
    watch_services=["order-service", "payment-service"],
    watch_interval=30,
    cache_ttl=60,
    
    # Load balancing
    load_balancing_strategy=LoadBalancingStrategy.HEALTH_BASED,
    health_check_required=True
)
```

### Kubernetes Configuration

```python
kubernetes_config = ServiceDiscoveryConfig(
    type=ServiceDiscoveryType.KUBERNETES,
    
    # Kubernetes API
    api_server="https://kubernetes.default.svc",
    token_file="/var/run/secrets/kubernetes.io/serviceaccount/token",
    ca_cert_file="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt",
    
    # Service discovery
    namespace="default",
    label_selector="app=microservice",
    field_selector="status.phase=Running",
    
    # Service registration (for custom resources)
    service_name="user-service",
    service_port=8000,
    service_labels={
        "app": "user-service",
        "version": "v1",
        "component": "api"
    },
    service_annotations={
        "prometheus.io/scrape": "true",
        "prometheus.io/port": "9090"
    },
    
    # Watch settings
    watch_enabled=True,
    watch_timeout=300,
    reconnect_on_failure=True,
    
    # Load balancing
    load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,
    endpoint_slice_mirroring=True
)
```

## Circuit Breaker Configuration

```python
from fastapi_microservices_sdk.communication.config import CircuitBreakerConfig

circuit_breaker_config = CircuitBreakerConfig(
    enabled=True,
    
    # Thresholds
    failure_threshold=5,
    success_threshold=3,
    timeout_threshold=10.0,
    
    # Timing
    recovery_timeout=60,
    half_open_timeout=30,
    
    # Monitoring
    monitoring_period=60,
    minimum_throughput=10,
    
    # Exceptions
    expected_exceptions=[
        "ConnectionError",
        "TimeoutError", 
        "HTTPError"
    ],
    ignored_exceptions=[
        "ValidationError",
        "AuthenticationError"
    ],
    
    # Callbacks
    on_open_callback="circuit_breaker_opened",
    on_close_callback="circuit_breaker_closed",
    on_half_open_callback="circuit_breaker_half_opened",
    
    # Fallback
    fallback_enabled=True,
    fallback_function="get_cached_response",
    fallback_timeout=5.0
)
```

## Environment-Based Configuration

### Configuration from Environment Variables

```python
import os
from fastapi_microservices_sdk.communication.config import CommunicationConfig

# Definir variables de entorno
os.environ.update({
    # Message Broker
    "MESSAGE_BROKER_TYPE": "rabbitmq",
    "MESSAGE_BROKER_HOST": "rabbitmq.example.com",
    "MESSAGE_BROKER_PORT": "5672",
    "MESSAGE_BROKER_USERNAME": "service_user",
    "MESSAGE_BROKER_PASSWORD": "secure_password",
    
    # HTTP Client
    "HTTP_CLIENT_BASE_URL": "https://api.example.com",
    "HTTP_CLIENT_TIMEOUT": "30.0",
    "HTTP_CLIENT_MAX_RETRIES": "3",
    
    # Service Discovery
    "SERVICE_DISCOVERY_TYPE": "consul",
    "SERVICE_DISCOVERY_HOST": "consul.example.com",
    "SERVICE_DISCOVERY_PORT": "8500",
    
    # Circuit Breaker
    "CIRCUIT_BREAKER_ENABLED": "true",
    "CIRCUIT_BREAKER_FAILURE_THRESHOLD": "5",
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT": "60"
})

# Cargar configuración automáticamente
config = CommunicationConfig.from_env()
```

### Configuration Files

```python
# config.yaml
communication:
  message_broker:
    type: rabbitmq
    host: rabbitmq.example.com
    port: 5672
    username: service_user
    password: secure_password
    ssl_enabled: true
    exchange_name: microservices
    
  http_client:
    base_url: https://api.example.com
    timeout:
      connection: 10.0
      read: 30.0
      write: 30.0
    retry:
      max_attempts: 3
      backoff_strategy: exponential
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      
  service_discovery:
    type: consul
    host: consul.example.com
    port: 8500
    service_name: user-service
    health_check_url: /health
```

```python
# Cargar desde archivo
from fastapi_microservices_sdk.communication.config import CommunicationConfig

config = CommunicationConfig.from_file("config.yaml")
```

## Configuration Validation

### Custom Validators

```python
from pydantic import validator
from fastapi_microservices_sdk.communication.config import MessageBrokerConfig

class CustomMessageBrokerConfig(MessageBrokerConfig):
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('connection_timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

### Configuration Testing

```python
import pytest
from fastapi_microservices_sdk.communication.config import CommunicationConfig

def test_valid_configuration():
    config = CommunicationConfig(
        message_broker={
            "type": "rabbitmq",
            "host": "localhost",
            "port": 5672
        }
    )
    assert config.message_broker.type == "rabbitmq"
    assert config.message_broker.host == "localhost"

def test_invalid_configuration():
    with pytest.raises(ValueError):
        CommunicationConfig(
            message_broker={
                "type": "invalid_type",
                "host": "localhost"
            }
        )
```

## Configuration Management Patterns

### Configuration Factory

```python
from typing import Dict, Any
from fastapi_microservices_sdk.communication.config import CommunicationConfig

class ConfigurationFactory:
    @staticmethod
    def create_development_config() -> CommunicationConfig:
        return CommunicationConfig(
            message_broker={
                "type": "memory",
                "host": "localhost"
            },
            http_client={
                "base_url": "http://localhost:8000",
                "timeout": {"connection": 5.0, "read": 10.0}
            },
            service_discovery={
                "type": "memory"
            }
        )
    
    @staticmethod
    def create_production_config() -> CommunicationConfig:
        return CommunicationConfig.from_env()
    
    @staticmethod
    def create_test_config() -> CommunicationConfig:
        return CommunicationConfig(
            message_broker={"type": "memory"},
            http_client={"base_url": "http://test-api"},
            service_discovery={"type": "memory"}
        )

# Uso
import os
environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    config = ConfigurationFactory.create_production_config()
elif environment == "test":
    config = ConfigurationFactory.create_test_config()
else:
    config = ConfigurationFactory.create_development_config()
```

### Configuration Profiles

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ConfigurationProfile:
    name: str
    config: Dict[str, Any]
    description: str = ""

class ProfileManager:
    def __init__(self):
        self.profiles = {
            "local": ConfigurationProfile(
                name="local",
                description="Local development configuration",
                config={
                    "message_broker": {"type": "memory"},
                    "http_client": {"base_url": "http://localhost:8000"},
                    "service_discovery": {"type": "memory"}
                }
            ),
            "staging": ConfigurationProfile(
                name="staging",
                description="Staging environment configuration",
                config={
                    "message_broker": {
                        "type": "rabbitmq",
                        "host": "rabbitmq-staging.example.com"
                    },
                    "http_client": {
                        "base_url": "https://api-staging.example.com"
                    },
                    "service_discovery": {
                        "type": "consul",
                        "host": "consul-staging.example.com"
                    }
                }
            ),
            "production": ConfigurationProfile(
                name="production",
                description="Production environment configuration",
                config={
                    "message_broker": {
                        "type": "rabbitmq",
                        "host": "rabbitmq.example.com",
                        "ssl_enabled": True
                    },
                    "http_client": {
                        "base_url": "https://api.example.com",
                        "circuit_breaker": {"enabled": True}
                    },
                    "service_discovery": {
                        "type": "consul",
                        "host": "consul.example.com",
                        "scheme": "https"
                    }
                }
            )
        }
    
    def get_config(self, profile_name: str) -> CommunicationConfig:
        if profile_name not in self.profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        profile = self.profiles[profile_name]
        return CommunicationConfig(**profile.config)

# Uso
profile_manager = ProfileManager()
config = profile_manager.get_config("production")
```

## Best Practices

### 1. Security

```python
# Nunca hardcodear credenciales
# ❌ Malo
config = MessageBrokerConfig(
    password="hardcoded_password"
)

# ✅ Bueno
config = MessageBrokerConfig(
    password=os.getenv("MESSAGE_BROKER_PASSWORD")
)

# Usar secrets management
from fastapi_microservices_sdk.security.secrets import SecretManager

secret_manager = SecretManager()
config = MessageBrokerConfig(
    password=secret_manager.get_secret("message_broker_password")
)
```

### 2. Configuration Validation

```python
# Validar configuración al inicio
def validate_configuration(config: CommunicationConfig):
    errors = []
    
    # Validar conectividad
    if config.message_broker.type == "rabbitmq":
        try:
            # Test connection
            test_connection(config.message_broker)
        except Exception as e:
            errors.append(f"Message broker connection failed: {e}")
    
    # Validar URLs
    if config.http_client.base_url:
        if not config.http_client.base_url.startswith(("http://", "https://")):
            errors.append("HTTP client base URL must start with http:// or https://")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

# Usar al inicio de la aplicación
config = CommunicationConfig.from_env()
validate_configuration(config)
```

### 3. Configuration Monitoring

```python
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigurationWatcher(FileSystemEventHandler):
    def __init__(self, config_file: str, reload_callback):
        self.config_file = config_file
        self.reload_callback = reload_callback
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        if event.src_path == self.config_file:
            self.logger.info("Configuration file changed, reloading...")
            try:
                new_config = CommunicationConfig.from_file(self.config_file)
                self.reload_callback(new_config)
                self.logger.info("Configuration reloaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to reload configuration: {e}")

# Uso
def reload_configuration(new_config: CommunicationConfig):
    # Actualizar componentes con nueva configuración
    global current_config
    current_config = new_config

observer = Observer()
observer.schedule(
    ConfigurationWatcher("config.yaml", reload_configuration),
    path=".",
    recursive=False
)
observer.start()
```

## Troubleshooting

### Common Issues

1. **Configuration Validation Errors**
   ```python
   try:
       config = CommunicationConfig.from_env()
   except ValueError as e:
       print(f"Configuration error: {e}")
       # Usar configuración por defecto o salir
   ```

2. **Missing Environment Variables**
   ```python
   import os
   
   required_vars = [
       "MESSAGE_BROKER_HOST",
       "MESSAGE_BROKER_USERNAME", 
       "MESSAGE_BROKER_PASSWORD"
   ]
   
   missing_vars = [var for var in required_vars if not os.getenv(var)]
   if missing_vars:
       raise ValueError(f"Missing required environment variables: {missing_vars}")
   ```

3. **Configuration Conflicts**
   ```python
   def check_configuration_conflicts(config: CommunicationConfig):
       warnings = []
       
       # Verificar conflictos de puerto
       if (config.service_discovery.port == config.message_broker.port and
           config.service_discovery.host == config.message_broker.host):
           warnings.append("Service discovery and message broker using same port")
       
       # Verificar configuración SSL
       if config.http_client.verify_ssl and not config.http_client.ssl_ca_path:
           warnings.append("SSL verification enabled but no CA certificate provided")
       
       for warning in warnings:
           logging.warning(f"Configuration warning: {warning}")
   ```

## Examples

Ver ejemplos completos en:
- `examples/configuration_example.py`
- `examples/environment_config_example.py`
- `examples/profile_management_example.py`
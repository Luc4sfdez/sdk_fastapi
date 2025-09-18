# Communication Module Documentation

El módulo de comunicación del FastAPI Microservices SDK proporciona una suite completa de herramientas para la comunicación entre microservicios.

## Componentes Principales

### 🌐 HTTP Communication
- **[HTTP Client](http_client.md)** - Cliente HTTP básico y avanzado
- **[Enhanced HTTP Client](enhanced_http_client.md)** - Cliente con circuit breaker, retry, caching
- **[Advanced Policies](advanced_policies.md)** - Políticas avanzadas de retry y load balancing

### 📨 Messaging
- **[Messaging Components](messaging.md)** - Redis Pub/Sub, RabbitMQ, Apache Kafka
- **Message Brokers** - Abstracción unificada para diferentes brokers
- **Reliability Features** - Circuit breakers, retry logic, dead letter queues

### 🔍 Service Discovery & Protocols
- **[gRPC](grpc.md)** - Comunicación gRPC de alto rendimiento
- **[Protocols](protocols.md)** - API Gateway y Service Mesh patterns

### ⚙️ Configuration & Monitoring
- **[Configuration](configuration.md)** - Gestión centralizada de configuraciones
- **[Logging](logging.md)** - Logging estructurado con correlation tracking
- **[Communication Manager](communication_manager.md)** - Gestión unificada de comunicación

## Quick Start

### Instalación

```bash
pip install fastapi-microservices-sdk[communication]
```

### Configuración Básica

```python
from fastapi_microservices_sdk.communication import CommunicationManager
from fastapi_microservices_sdk.communication.config import CommunicationConfig

# Configuración desde variables de entorno
config = CommunicationConfig.from_env()

# Crear manager de comunicación
comm_manager = CommunicationManager(config)

# Inicializar componentes
await comm_manager.initialize()
```

### HTTP Client

```python
from fastapi_microservices_sdk.communication.http import EnhancedHTTPClient

# Cliente HTTP con características avanzadas
client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    circuit_breaker_enabled=True,
    retry_enabled=True,
    caching_enabled=True
)

# Realizar peticiones
response = await client.get("/users/123")
user = response.json()
```

### Message Broker

```python
from fastapi_microservices_sdk.communication.messaging import RedisPubSubClient

# Cliente Redis Pub/Sub
redis_client = RedisPubSubClient(
    host="localhost",
    port=6379
)

# Publicar mensaje
await redis_client.publish("user.events", {
    "event": "user_created",
    "user_id": "123"
})

# Suscribirse a mensajes
async def handle_user_event(message, metadata):
    print(f"Received: {message}")

await redis_client.subscribe("user.events", handle_user_event)
```

## Arquitectura

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                Communication Module                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    HTTP     │  │  Messaging  │  │    gRPC     │         │
│  │             │  │             │  │             │         │
│  │ • Client    │  │ • RabbitMQ  │  │ • Client    │         │
│  │ • Enhanced  │  │ • Kafka     │  │ • Server    │         │
│  │ • Policies  │  │ • Redis     │  │ • Proto Gen │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Protocols   │  │   Config    │  │   Logging   │         │
│  │             │  │             │  │             │         │
│  │ • Gateway   │  │ • Env Vars  │  │ • Structured│         │
│  │ • Mesh      │  │ • Profiles  │  │ • Correlation│        │
│  │ • Discovery │  │ • Validation│  │ • Security  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                Communication Manager                        │
│              (Unified Interface)                            │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Comunicación

```
┌─────────────┐    HTTP/gRPC     ┌─────────────┐
│   Service   │ ────────────────▶│   Service   │
│      A      │                  │      B      │
└─────────────┘                  └─────────────┘
       │                                │
       │ Publish                        │ Subscribe
       ▼                                ▼
┌─────────────────────────────────────────────────┐
│              Message Broker                     │
│         (RabbitMQ/Kafka/Redis)                  │
└─────────────────────────────────────────────────┘
       ▲                                ▲
       │ Events                         │ Events
       ▼                                ▼
┌─────────────┐                  ┌─────────────┐
│   Service   │                  │   Service   │
│      C      │                  │      D      │
└─────────────┘                  └─────────────┘
```

## Características Principales

### 🔄 Resilience Patterns
- **Circuit Breaker** - Protección contra fallos en cascada
- **Retry Logic** - Reintentos inteligentes con backoff
- **Timeout Management** - Control granular de timeouts
- **Bulkhead Pattern** - Aislamiento de recursos

### 📊 Observability
- **Structured Logging** - Logs estructurados en JSON
- **Correlation Tracking** - Seguimiento de requests distribuidos
- **Metrics Collection** - Métricas automáticas de Prometheus
- **Distributed Tracing** - Integración con OpenTelemetry

### 🔒 Security
- **Authentication** - JWT, OAuth2, API Keys
- **Authorization** - Control de acceso granular
- **mTLS Support** - Comunicación segura entre servicios
- **Security Logging** - Auditoría de eventos de seguridad

### ⚡ Performance
- **Connection Pooling** - Reutilización eficiente de conexiones
- **Caching** - Cache inteligente con TTL y invalidación
- **Load Balancing** - Distribución inteligente de carga
- **Async/Await** - Operaciones no bloqueantes

## Patrones de Uso

### 1. Microservice-to-Microservice Communication

```python
# Configuración del servicio
from fastapi_microservices_sdk.communication import CommunicationManager

class UserService:
    def __init__(self):
        self.comm = CommunicationManager.from_env()
        
    async def get_user_profile(self, user_id: int):
        # HTTP call to profile service
        profile = await self.comm.http.get(f"/profiles/{user_id}")
        
        # Publish event
        await self.comm.messaging.publish("user.profile.accessed", {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return profile
```

### 2. Event-Driven Architecture

```python
# Event publisher
async def create_user(user_data):
    user = await database.create_user(user_data)
    
    # Publish user created event
    await comm_manager.messaging.publish("user.created", {
        "user_id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    })
    
    return user

# Event subscriber
@comm_manager.messaging.subscribe("user.created")
async def send_welcome_email(event_data):
    user_id = event_data["user_id"]
    email = event_data["email"]
    
    await email_service.send_welcome_email(user_id, email)
```

### 3. API Gateway Pattern

```python
from fastapi_microservices_sdk.communication.protocols import APIGateway

# Configure API Gateway
gateway = APIGateway(
    host="0.0.0.0",
    port=8080,
    services={
        "user-service": "http://user-service:8000",
        "order-service": "http://order-service:8000",
        "payment-service": "http://payment-service:8000"
    }
)

# Routes are automatically configured
# GET /api/v1/users/* -> user-service
# GET /api/v1/orders/* -> order-service
# POST /api/v1/payments/* -> payment-service
```

## Configuration Examples

### Environment Variables

```bash
# Message Broker
MESSAGE_BROKER_TYPE=rabbitmq
MESSAGE_BROKER_HOST=rabbitmq.example.com
MESSAGE_BROKER_USERNAME=service_user
MESSAGE_BROKER_PASSWORD=secure_password

# HTTP Client
HTTP_CLIENT_BASE_URL=https://api.example.com
HTTP_CLIENT_TIMEOUT=30.0
HTTP_CLIENT_MAX_RETRIES=3

# Service Discovery
SERVICE_DISCOVERY_TYPE=consul
SERVICE_DISCOVERY_HOST=consul.example.com
SERVICE_DISCOVERY_PORT=8500

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
CORRELATION_HEADER=X-Correlation-ID
```

### Configuration File

```yaml
# communication.yaml
communication:
  message_broker:
    type: rabbitmq
    host: rabbitmq.example.com
    port: 5672
    username: service_user
    password: secure_password
    ssl_enabled: true
    
  http_client:
    base_url: https://api.example.com
    timeout:
      connection: 10.0
      read: 30.0
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      
  service_discovery:
    type: consul
    host: consul.example.com
    port: 8500
    
  logging:
    level: INFO
    format: json
    correlation_header: X-Correlation-ID
    enable_security_logging: true
```

## Best Practices

### 1. Error Handling

```python
from fastapi_microservices_sdk.communication.exceptions import (
    CommunicationError,
    CircuitBreakerOpenError,
    ServiceUnavailableError
)

async def resilient_service_call():
    try:
        response = await http_client.get("/external-service")
        return response.json()
    except CircuitBreakerOpenError:
        # Use cached data or fallback
        return await get_cached_data()
    except ServiceUnavailableError:
        # Degrade functionality
        return {"status": "service_unavailable"}
    except CommunicationError as e:
        # Log and re-raise
        logger.error(f"Communication error: {e}")
        raise
```

### 2. Configuration Management

```python
# Use environment-specific configurations
import os

def get_communication_config():
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return CommunicationConfig.from_file("config/production.yaml")
    elif env == "staging":
        return CommunicationConfig.from_file("config/staging.yaml")
    else:
        return CommunicationConfig.from_file("config/development.yaml")
```

### 3. Monitoring and Observability

```python
# Enable comprehensive monitoring
comm_manager = CommunicationManager(
    config=config,
    enable_metrics=True,
    enable_tracing=True,
    enable_health_checks=True
)

# Health check endpoint
@app.get("/health")
async def health_check():
    health = await comm_manager.health_check()
    return {
        "status": "healthy" if health.is_healthy else "unhealthy",
        "components": health.component_status,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Migration Guide

### From Basic HTTP Client

```python
# Before
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/users")

# After
from fastapi_microservices_sdk.communication.http import EnhancedHTTPClient

async with EnhancedHTTPClient(base_url="https://api.example.com") as client:
    response = await client.get("/users")
    # Automatic retry, circuit breaker, caching, etc.
```

### From Basic Message Queue

```python
# Before
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')

# After
from fastapi_microservices_sdk.communication.messaging import RabbitMQClient

async with RabbitMQClient(host="localhost") as client:
    await client.publish("hello", {"message": "Hello World!"})
    # Automatic reconnection, dead letter queues, metrics, etc.
```

## Performance Considerations

### Connection Pooling

```python
# Configure appropriate pool sizes
http_config = HTTPClientConfig(
    max_connections=100,  # Total connections
    max_keepalive_connections=20,  # Persistent connections
    keepalive_expiry=30.0  # Connection lifetime
)
```

### Message Broker Optimization

```python
# RabbitMQ optimization
rabbitmq_config = MessageBrokerConfig(
    prefetch_count=10,  # Messages per consumer
    confirm_delivery=True,  # Publisher confirms
    connection_timeout=10.0,
    heartbeat=600
)

# Kafka optimization
kafka_config = MessageBrokerConfig(
    producer_config={
        "batch_size": 16384,
        "linger_ms": 10,
        "compression_type": "snappy"
    },
    consumer_config={
        "max_poll_records": 500,
        "fetch_min_bytes": 1024
    }
)
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   - Increase timeout values
   - Check network connectivity
   - Verify service availability

2. **Circuit Breaker Activation**
   - Check downstream service health
   - Adjust failure thresholds
   - Implement proper fallbacks

3. **Message Delivery Failures**
   - Verify broker connectivity
   - Check queue/topic configuration
   - Monitor dead letter queues

4. **High Memory Usage**
   - Adjust connection pool sizes
   - Configure message batching
   - Enable compression

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger("fastapi_microservices_sdk.communication").setLevel(logging.DEBUG)

# Enable detailed metrics
comm_manager = CommunicationManager(
    config=config,
    debug_mode=True,
    detailed_metrics=True
)
```

## Examples

Consulta los ejemplos completos en el directorio `examples/`:

- `communication_manager_example.py` - Uso completo del Communication Manager
- `http_client_example.py` - Cliente HTTP básico y avanzado
- `messaging_example.py` - Pub/Sub con diferentes brokers
- `service_discovery_example.py` - Descubrimiento de servicios
- `resilience_patterns_example.py` - Patrones de resiliencia
- `observability_example.py` - Monitoreo y observabilidad

## Contributing

Para contribuir al módulo de comunicación:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Implementa tests comprehensivos
4. Actualiza la documentación
5. Envía un pull request

## Support

- 📖 **Documentation**: [docs/communication/](.)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- 📧 **Email**: support@example.com
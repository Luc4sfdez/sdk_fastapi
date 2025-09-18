# Communication Logging

El módulo de logging proporciona capacidades de logging estructurado para todos los componentes de comunicación con seguimiento de correlation IDs y integración con el sistema de logging de seguridad.

## Arquitectura

### Structured Logging

El sistema utiliza logging estructurado con formato JSON para facilitar el análisis:

```python
from fastapi_microservices_sdk.communication.logging import CommunicationLogger

logger = CommunicationLogger(
    service_name="user-service",
    service_version="1.0.0",
    environment="production"
)
```

### Event Types

```python
from fastapi_microservices_sdk.communication.logging import CommunicationEventType

# Tipos de eventos disponibles
event_types = [
    CommunicationEventType.HTTP_REQUEST,
    CommunicationEventType.HTTP_RESPONSE,
    CommunicationEventType.MESSAGE_PUBLISH,
    CommunicationEventType.MESSAGE_CONSUME,
    CommunicationEventType.SERVICE_DISCOVERY,
    CommunicationEventType.GRPC_CALL,
    CommunicationEventType.GRPC_RESPONSE,
    CommunicationEventType.CIRCUIT_BREAKER,
    CommunicationEventType.HEALTH_CHECK,
    CommunicationEventType.CONNECTION,
    CommunicationEventType.ERROR
]
```

## Basic Usage

### Logger Configuration

```python
from fastapi_microservices_sdk.communication.logging import (
    CommunicationLogger,
    LogLevel,
    LogFormat
)

# Configuración básica
logger = CommunicationLogger(
    service_name="user-service",
    service_version="1.0.0",
    environment="production",
    log_level=LogLevel.INFO,
    log_format=LogFormat.JSON
)

# Configuración avanzada
logger = CommunicationLogger(
    service_name="user-service",
    service_version="1.0.0",
    environment="production",
    
    # Output configuration
    log_level=LogLevel.INFO,
    log_format=LogFormat.JSON,
    output_file="/var/log/communication.log",
    max_file_size="100MB",
    backup_count=5,
    
    # Correlation tracking
    enable_correlation_tracking=True,
    correlation_header="X-Correlation-ID",
    
    # Performance
    async_logging=True,
    buffer_size=1000,
    flush_interval=5.0,
    
    # Security integration
    enable_security_logging=True,
    security_log_level=LogLevel.WARNING,
    
    # Filtering
    exclude_paths=["/health", "/metrics"],
    exclude_headers=["Authorization", "Cookie"],
    max_body_size=1024,
    
    # Sampling
    sampling_rate=1.0,  # Log 100% of events
    error_sampling_rate=1.0  # Always log errors
)
```

### Basic Logging

```python
# Log de eventos HTTP
await logger.log_http_request(
    method="GET",
    url="/api/users/123",
    headers={"User-Agent": "MyService/1.0"},
    correlation_id="req-123-456"
)

await logger.log_http_response(
    status_code=200,
    response_time=0.150,
    response_size=1024,
    correlation_id="req-123-456"
)

# Log de mensajería
await logger.log_message_publish(
    topic="user.events",
    message_id="msg-789",
    message_size=512,
    broker_type="rabbitmq"
)

await logger.log_message_consume(
    topic="user.events",
    message_id="msg-789",
    processing_time=0.050,
    success=True
)
```

## HTTP Request/Response Logging

### Automatic HTTP Logging

```python
from fastapi_microservices_sdk.communication.logging.middleware import HTTPLoggingMiddleware
from fastapi import FastAPI

app = FastAPI()

# Middleware para logging automático
app.add_middleware(
    HTTPLoggingMiddleware,
    logger=logger,
    log_requests=True,
    log_responses=True,
    log_request_body=False,  # Por seguridad
    log_response_body=False,
    exclude_paths=["/health", "/metrics"],
    correlation_header="X-Correlation-ID"
)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Request y response se loggean automáticamente
    return {"user_id": user_id, "name": "John Doe"}
```

### Manual HTTP Logging

```python
import time
from fastapi_microservices_sdk.communication.logging import HTTPRequestEvent, HTTPResponseEvent

async def make_http_request():
    correlation_id = "req-" + str(uuid.uuid4())
    start_time = time.time()
    
    # Log request
    request_event = HTTPRequestEvent(
        method="POST",
        url="https://api.example.com/users",
        headers={"Content-Type": "application/json"},
        body_size=256,
        correlation_id=correlation_id,
        user_agent="MyService/1.0",
        remote_addr="10.0.1.100"
    )
    await logger.log_event(request_event)
    
    try:
        # Hacer request HTTP
        response = await http_client.post("/users", json={"name": "John"})
        
        # Log successful response
        response_event = HTTPResponseEvent(
            status_code=response.status_code,
            response_time=time.time() - start_time,
            response_size=len(response.content),
            correlation_id=correlation_id,
            cache_hit=False
        )
        await logger.log_event(response_event)
        
    except Exception as e:
        # Log error
        error_event = ErrorEvent(
            error_type=type(e).__name__,
            error_message=str(e),
            correlation_id=correlation_id,
            stack_trace=traceback.format_exc()
        )
        await logger.log_event(error_event)
        raise
```

## Message Broker Logging

### RabbitMQ Logging

```python
from fastapi_microservices_sdk.communication.logging import MessageEvent

async def publish_message():
    correlation_id = "msg-" + str(uuid.uuid4())
    
    # Log message publish
    publish_event = MessageEvent(
        event_type=CommunicationEventType.MESSAGE_PUBLISH,
        broker_type="rabbitmq",
        topic="user.events",
        message_id=correlation_id,
        message_size=512,
        routing_key="user.created",
        exchange="microservices",
        correlation_id=correlation_id,
        properties={
            "delivery_mode": 2,  # Persistent
            "priority": 1,
            "ttl": 3600
        }
    )
    await logger.log_event(publish_event)
    
    # Publish message
    await rabbitmq_client.publish(
        routing_key="user.created",
        message={"user_id": 123, "event": "created"},
        correlation_id=correlation_id
    )

async def consume_message(message, metadata):
    start_time = time.time()
    correlation_id = metadata.get("correlation_id")
    
    try:
        # Process message
        await process_user_event(message)
        
        # Log successful consumption
        consume_event = MessageEvent(
            event_type=CommunicationEventType.MESSAGE_CONSUME,
            broker_type="rabbitmq",
            topic=metadata["routing_key"],
            message_id=metadata["message_id"],
            processing_time=time.time() - start_time,
            correlation_id=correlation_id,
            success=True
        )
        await logger.log_event(consume_event)
        
    except Exception as e:
        # Log processing error
        error_event = MessageEvent(
            event_type=CommunicationEventType.ERROR,
            broker_type="rabbitmq",
            topic=metadata["routing_key"],
            message_id=metadata["message_id"],
            processing_time=time.time() - start_time,
            correlation_id=correlation_id,
            success=False,
            error_message=str(e)
        )
        await logger.log_event(error_event)
        raise
```

### Kafka Logging

```python
async def kafka_producer_logging():
    correlation_id = "kafka-" + str(uuid.uuid4())
    
    # Log Kafka produce
    produce_event = MessageEvent(
        event_type=CommunicationEventType.MESSAGE_PUBLISH,
        broker_type="kafka",
        topic="user-events",
        message_id=correlation_id,
        partition=0,
        offset=None,  # Will be set after produce
        key="user-123",
        headers={"source": "user-service"},
        correlation_id=correlation_id
    )
    await logger.log_event(produce_event)

async def kafka_consumer_logging():
    async for message in kafka_consumer:
        correlation_id = message.headers.get("correlation_id", "unknown")
        start_time = time.time()
        
        try:
            # Process message
            await process_kafka_message(message.value)
            
            # Log successful consumption
            consume_event = MessageEvent(
                event_type=CommunicationEventType.MESSAGE_CONSUME,
                broker_type="kafka",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                processing_time=time.time() - start_time,
                correlation_id=correlation_id,
                success=True
            )
            await logger.log_event(consume_event)
            
            # Commit offset
            await kafka_consumer.commit()
            
        except Exception as e:
            # Log error and don't commit
            error_event = MessageEvent(
                event_type=CommunicationEventType.ERROR,
                broker_type="kafka",
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                processing_time=time.time() - start_time,
                correlation_id=correlation_id,
                success=False,
                error_message=str(e)
            )
            await logger.log_event(error_event)
```

## Service Discovery Logging

```python
from fastapi_microservices_sdk.communication.logging import ServiceDiscoveryEvent

async def log_service_discovery():
    # Log service registration
    registration_event = ServiceDiscoveryEvent(
        event_type=CommunicationEventType.SERVICE_DISCOVERY,
        action="register",
        service_name="user-service",
        service_id="user-service-1",
        service_address="10.0.1.100",
        service_port=8000,
        discovery_backend="consul",
        tags=["api", "v1"],
        health_check_url="/health"
    )
    await logger.log_event(registration_event)
    
    # Log service discovery
    discovery_event = ServiceDiscoveryEvent(
        event_type=CommunicationEventType.SERVICE_DISCOVERY,
        action="discover",
        service_name="order-service",
        discovered_instances=3,
        discovery_backend="consul",
        discovery_time=0.025
    )
    await logger.log_event(discovery_event)
```

## Circuit Breaker Logging

```python
from fastapi_microservices_sdk.communication.logging import CircuitBreakerEvent

class LoggingCircuitBreaker:
    def __init__(self, service_name: str, logger: CommunicationLogger):
        self.service_name = service_name
        self.logger = logger
    
    async def on_circuit_open(self):
        event = CircuitBreakerEvent(
            event_type=CommunicationEventType.CIRCUIT_BREAKER,
            service_name=self.service_name,
            state="open",
            failure_count=5,
            failure_threshold=5,
            last_failure_time=time.time()
        )
        await self.logger.log_event(event)
    
    async def on_circuit_close(self):
        event = CircuitBreakerEvent(
            event_type=CommunicationEventType.CIRCUIT_BREAKER,
            service_name=self.service_name,
            state="closed",
            success_count=3,
            success_threshold=3
        )
        await self.logger.log_event(event)
    
    async def on_circuit_half_open(self):
        event = CircuitBreakerEvent(
            event_type=CommunicationEventType.CIRCUIT_BREAKER,
            service_name=self.service_name,
            state="half_open",
            recovery_timeout=60
        )
        await self.logger.log_event(event)
```

## Correlation ID Tracking

### Automatic Correlation Tracking

```python
from fastapi_microservices_sdk.communication.logging.correlation import CorrelationTracker

# Configurar tracking automático
tracker = CorrelationTracker(
    header_name="X-Correlation-ID",
    generate_if_missing=True,
    propagate_downstream=True
)

# Middleware para FastAPI
from fastapi_microservices_sdk.communication.logging.middleware import CorrelationMiddleware

app.add_middleware(
    CorrelationMiddleware,
    tracker=tracker,
    logger=logger
)

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    # Correlation ID está disponible automáticamente
    correlation_id = tracker.get_current_correlation_id()
    
    # Llamadas downstream automáticamente incluyen correlation ID
    profile = await http_client.get(f"/profiles/{user_id}")
    
    return {"user_id": user_id, "profile": profile}
```

### Manual Correlation Tracking

```python
from fastapi_microservices_sdk.communication.logging.correlation import correlation_context

async def process_with_correlation():
    correlation_id = "manual-" + str(uuid.uuid4())
    
    # Establecer contexto de correlación
    async with correlation_context(correlation_id):
        # Todos los logs dentro de este contexto incluirán el correlation ID
        await logger.info("Processing started")
        
        # Llamar otros servicios
        await call_downstream_service()
        
        await logger.info("Processing completed")

async def call_downstream_service():
    # El correlation ID se propaga automáticamente
    correlation_id = get_current_correlation_id()
    
    await logger.log_http_request(
        method="GET",
        url="/downstream/api",
        correlation_id=correlation_id
    )
```

## Performance Monitoring

### Response Time Tracking

```python
from fastapi_microservices_sdk.communication.logging.performance import PerformanceTracker

performance_tracker = PerformanceTracker(
    logger=logger,
    slow_request_threshold=1.0,  # Log requests > 1 second
    enable_percentiles=True,
    percentiles=[50, 90, 95, 99]
)

@performance_tracker.track_performance
async def slow_operation():
    # Operation is automatically timed and logged
    await asyncio.sleep(2.0)
    return "result"

# Manual performance tracking
async def manual_performance_tracking():
    with performance_tracker.track("database_query"):
        result = await database.query("SELECT * FROM users")
    
    # Automatically logs if query took > threshold
    return result
```

### Memory and Resource Tracking

```python
from fastapi_microservices_sdk.communication.logging.resources import ResourceTracker

resource_tracker = ResourceTracker(
    logger=logger,
    track_memory=True,
    track_cpu=True,
    track_connections=True,
    log_interval=60  # Log every minute
)

# Start resource tracking
await resource_tracker.start()

# Resource usage is logged automatically
# Manual resource logging
await resource_tracker.log_current_usage()
```

## Security Integration

### Security Event Logging

```python
from fastapi_microservices_sdk.communication.logging.security import SecurityEventLogger

security_logger = SecurityEventLogger(
    communication_logger=logger,
    security_log_level=LogLevel.WARNING,
    enable_audit_trail=True
)

# Log authentication events
await security_logger.log_authentication_attempt(
    user_id="user123",
    success=True,
    method="jwt",
    correlation_id="req-123"
)

# Log authorization events
await security_logger.log_authorization_check(
    user_id="user123",
    resource="/api/users/456",
    action="read",
    allowed=False,
    reason="insufficient_permissions",
    correlation_id="req-123"
)

# Log suspicious activity
await security_logger.log_suspicious_activity(
    event_type="rate_limit_exceeded",
    source_ip="192.168.1.100",
    user_agent="Suspicious Bot",
    details={"requests_per_minute": 1000},
    correlation_id="req-123"
)
```

## Log Aggregation and Analysis

### Structured Log Format

```json
{
  "timestamp": "2025-01-01T12:00:00.000Z",
  "level": "INFO",
  "service_name": "user-service",
  "service_version": "1.0.0",
  "environment": "production",
  "event_type": "http_request",
  "correlation_id": "req-123-456",
  "trace_id": "trace-789",
  "span_id": "span-012",
  "method": "GET",
  "url": "/api/users/123",
  "status_code": 200,
  "response_time": 0.150,
  "response_size": 1024,
  "user_agent": "MyService/1.0",
  "remote_addr": "10.0.1.100",
  "headers": {
    "Accept": "application/json",
    "Content-Type": "application/json"
  },
  "metadata": {
    "cache_hit": false,
    "circuit_breaker_state": "closed",
    "retry_count": 0
  }
}
```

### ELK Stack Integration

```python
from fastapi_microservices_sdk.communication.logging.exporters import ElasticsearchExporter

# Configurar exportador a Elasticsearch
elasticsearch_exporter = ElasticsearchExporter(
    hosts=["elasticsearch1:9200", "elasticsearch2:9200"],
    index_pattern="communication-logs-{date}",
    username="elastic_user",
    password="elastic_password",
    ssl_verify=True,
    ca_certs="/etc/ssl/certs/ca.crt"
)

# Configurar logger con exportador
logger = CommunicationLogger(
    service_name="user-service",
    exporters=[elasticsearch_exporter]
)
```

### Prometheus Metrics Integration

```python
from fastapi_microservices_sdk.communication.logging.metrics import PrometheusMetricsExporter

# Configurar exportador de métricas
metrics_exporter = PrometheusMetricsExporter(
    registry=prometheus_client.REGISTRY,
    prefix="communication_",
    labels=["service_name", "environment"]
)

# Las métricas se generan automáticamente desde los logs
logger = CommunicationLogger(
    service_name="user-service",
    exporters=[metrics_exporter]
)

# Métricas disponibles:
# - communication_http_requests_total
# - communication_http_request_duration_seconds
# - communication_message_publish_total
# - communication_message_consume_total
# - communication_circuit_breaker_state
# - communication_errors_total
```

## Configuration

### Logger Configuration

```python
from fastapi_microservices_sdk.communication.logging.config import LoggingConfig

logging_config = LoggingConfig(
    # Basic settings
    service_name="user-service",
    service_version="1.0.0",
    environment="production",
    log_level="INFO",
    
    # Output settings
    output_format="json",
    output_file="/var/log/communication.log",
    max_file_size="100MB",
    backup_count=5,
    
    # Correlation tracking
    correlation_header="X-Correlation-ID",
    generate_correlation_id=True,
    propagate_correlation_id=True,
    
    # Performance settings
    async_logging=True,
    buffer_size=1000,
    flush_interval=5.0,
    
    # Filtering
    exclude_paths=["/health", "/metrics", "/favicon.ico"],
    exclude_headers=["Authorization", "Cookie", "X-API-Key"],
    max_body_size=1024,
    
    # Sampling
    sampling_rate=1.0,
    error_sampling_rate=1.0,
    slow_request_threshold=1.0,
    
    # Security
    enable_security_logging=True,
    mask_sensitive_data=True,
    sensitive_fields=["password", "token", "secret"],
    
    # Exporters
    exporters=[
        {
            "type": "elasticsearch",
            "hosts": ["elasticsearch:9200"],
            "index_pattern": "communication-logs-{date}"
        },
        {
            "type": "prometheus",
            "registry": "default",
            "prefix": "communication_"
        }
    ]
)

logger = CommunicationLogger.from_config(logging_config)
```

## Testing

### Log Testing

```python
import pytest
from fastapi_microservices_sdk.communication.logging.testing import LogCapture

@pytest.fixture
def log_capture():
    return LogCapture()

async def test_http_request_logging(log_capture):
    logger = CommunicationLogger(
        service_name="test-service",
        exporters=[log_capture]
    )
    
    await logger.log_http_request(
        method="GET",
        url="/test",
        correlation_id="test-123"
    )
    
    # Verify log was captured
    logs = log_capture.get_logs()
    assert len(logs) == 1
    assert logs[0]["event_type"] == "http_request"
    assert logs[0]["method"] == "GET"
    assert logs[0]["correlation_id"] == "test-123"

async def test_correlation_tracking(log_capture):
    tracker = CorrelationTracker()
    logger = CommunicationLogger(
        service_name="test-service",
        exporters=[log_capture]
    )
    
    async with correlation_context("test-correlation"):
        await logger.info("Test message")
    
    logs = log_capture.get_logs()
    assert logs[0]["correlation_id"] == "test-correlation"
```

## Best Practices

### 1. Structured Logging

```python
# ✅ Bueno - Usar campos estructurados
await logger.log_http_request(
    method="GET",
    url="/api/users/123",
    status_code=200,
    response_time=0.150
)

# ❌ Malo - Logging no estructurado
logger.info("GET /api/users/123 returned 200 in 0.150s")
```

### 2. Correlation ID Propagation

```python
# ✅ Bueno - Propagar correlation ID
async def call_downstream_service(correlation_id: str):
    headers = {"X-Correlation-ID": correlation_id}
    response = await http_client.get("/downstream", headers=headers)
    return response

# ❌ Malo - No propagar correlation ID
async def call_downstream_service():
    response = await http_client.get("/downstream")
    return response
```

### 3. Sensitive Data Masking

```python
# ✅ Bueno - Enmascarar datos sensibles
await logger.log_http_request(
    method="POST",
    url="/auth/login",
    headers={"Content-Type": "application/json"},
    body_size=256,
    # No loggear body con credenciales
)

# ❌ Malo - Loggear datos sensibles
await logger.log_http_request(
    method="POST",
    url="/auth/login",
    body={"username": "user", "password": "secret123"}  # ¡Nunca!
)
```

### 4. Performance Considerations

```python
# ✅ Bueno - Logging asíncrono para alto rendimiento
logger = CommunicationLogger(
    service_name="high-traffic-service",
    async_logging=True,
    buffer_size=10000,
    sampling_rate=0.1  # Log 10% de requests normales
)

# ✅ Siempre loggear errores
logger = CommunicationLogger(
    service_name="service",
    sampling_rate=0.1,
    error_sampling_rate=1.0  # 100% de errores
)
```

## Troubleshooting

### Common Issues

1. **High Log Volume**
   ```python
   # Usar sampling para reducir volumen
   logger = CommunicationLogger(
       sampling_rate=0.1,  # 10% de logs normales
       error_sampling_rate=1.0,  # 100% de errores
       slow_request_threshold=1.0  # Solo requests lentos
   )
   ```

2. **Missing Correlation IDs**
   ```python
   # Verificar middleware order
   app.add_middleware(CorrelationMiddleware)  # Debe ser primero
   app.add_middleware(HTTPLoggingMiddleware)
   ```

3. **Performance Impact**
   ```python
   # Usar logging asíncrono
   logger = CommunicationLogger(
       async_logging=True,
       buffer_size=1000,
       flush_interval=5.0
   )
   ```

## Examples

Ver ejemplos completos en:
- `examples/communication_logging_example.py`
- `examples/correlation_tracking_example.py`
- `examples/performance_logging_example.py`
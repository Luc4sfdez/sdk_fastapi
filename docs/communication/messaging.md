# Messaging Components

El módulo de messaging proporciona una abstracción unificada para diferentes sistemas de mensajería, incluyendo Redis Pub/Sub, RabbitMQ y Apache Kafka.

## Arquitectura

### Base Message Broker

Todos los message brokers implementan la interfaz base `MessageBroker`:

```python
from fastapi_microservices_sdk.communication.messaging.base import MessageBroker

class CustomBroker(MessageBroker):
    async def connect(self) -> None:
        # Implementar conexión
        pass
    
    async def disconnect(self) -> None:
        # Implementar desconexión
        pass
    
    async def publish(self, topic: str, message: dict, **kwargs) -> None:
        # Implementar publicación
        pass
    
    async def subscribe(self, topic: str, handler: Callable, **kwargs) -> None:
        # Implementar suscripción
        pass
```

### Reliability Features

El módulo incluye características de confiabilidad:

- **Message Acknowledgment**: Confirmación de procesamiento de mensajes
- **Dead Letter Queues**: Manejo de mensajes fallidos
- **Retry Logic**: Reintentos automáticos con backoff
- **Circuit Breaker**: Protección contra fallos en cascada

## Redis Pub/Sub

### Configuración Básica

```python
from fastapi_microservices_sdk.communication.messaging.redis_pubsub import RedisPubSubClient

# Configuración simple
client = RedisPubSubClient(
    host="localhost",
    port=6379,
    db=0
)

# Configuración avanzada
client = RedisPubSubClient(
    host="redis.example.com",
    port=6379,
    password="secret",
    ssl=True,
    max_connections=20,
    retry_on_timeout=True
)
```

### Publicación de Mensajes

```python
await client.connect()

# Mensaje simple
await client.publish("user.events", {
    "event": "user_created",
    "user_id": "123",
    "timestamp": "2025-01-01T00:00:00Z"
})

# Mensaje con metadatos
await client.publish(
    topic="order.events",
    message={"order_id": "456", "status": "completed"},
    correlation_id="req-789",
    priority=1
)
```

### Suscripción a Mensajes

```python
async def handle_user_event(message: dict, metadata: dict):
    user_id = message.get("user_id")
    event = message.get("event")
    
    print(f"Processing {event} for user {user_id}")
    
    # Procesar mensaje
    if event == "user_created":
        await send_welcome_email(user_id)

# Suscribirse a un topic
await client.subscribe("user.events", handle_user_event)

# Suscribirse con patrón
await client.subscribe_pattern("user.*", handle_user_event)
```

### Características Avanzadas

```python
# Suscripción con configuración avanzada
await client.subscribe(
    topic="critical.events",
    handler=handle_critical_event,
    max_retries=5,
    retry_delay=2.0,
    dead_letter_topic="critical.events.dlq"
)

# Publicación con TTL
await client.publish(
    topic="temp.events",
    message={"data": "temporary"},
    ttl=3600  # 1 hora
)
```

## RabbitMQ

### Configuración

```python
from fastapi_microservices_sdk.communication.messaging.rabbitmq import RabbitMQClient

client = RabbitMQClient(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    virtual_host="/",
    exchange_name="microservices",
    exchange_type="topic"
)
```

### Uso Básico

```python
await client.connect()

# Declarar queue
await client.declare_queue(
    queue_name="user.notifications",
    durable=True,
    auto_delete=False
)

# Publicar mensaje
await client.publish(
    routing_key="user.email.send",
    message={
        "to": "user@example.com",
        "subject": "Welcome!",
        "body": "Welcome to our service"
    }
)

# Consumir mensajes
async def process_email(message: dict, delivery_tag: str):
    try:
        await send_email(message)
        await client.ack_message(delivery_tag)
    except Exception as e:
        await client.nack_message(delivery_tag, requeue=True)

await client.consume("user.notifications", process_email)
```

### Características Avanzadas

```python
# Queue con Dead Letter Exchange
await client.declare_queue(
    queue_name="orders.processing",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "orders.dlx",
        "x-dead-letter-routing-key": "failed",
        "x-message-ttl": 300000  # 5 minutos
    }
)

# Publicación con confirmación
await client.publish(
    routing_key="orders.new",
    message={"order_id": "123"},
    mandatory=True,
    confirm=True
)
```

## Apache Kafka

### Configuración

```python
from fastapi_microservices_sdk.communication.messaging.kafka import KafkaClient

client = KafkaClient(
    bootstrap_servers=["localhost:9092"],
    client_id="microservice-1",
    security_protocol="PLAINTEXT"
)

# Configuración con autenticación
client = KafkaClient(
    bootstrap_servers=["kafka1:9092", "kafka2:9092"],
    security_protocol="SASL_SSL",
    sasl_mechanism="PLAIN",
    sasl_username="user",
    sasl_password="password",
    ssl_cafile="/path/to/ca.pem"
)
```

### Producción de Mensajes

```python
await client.connect()

# Mensaje simple
await client.produce(
    topic="user-events",
    message={
        "event": "user_registered",
        "user_id": "123",
        "email": "user@example.com"
    }
)

# Mensaje con key y headers
await client.produce(
    topic="user-events",
    key="user-123",
    message={"event": "profile_updated"},
    headers={"source": "user-service", "version": "1.0"}
)

# Producción en lote
messages = [
    {"key": "user-1", "value": {"event": "login"}},
    {"key": "user-2", "value": {"event": "logout"}},
]
await client.produce_batch("user-activity", messages)
```

### Consumo de Mensajes

```python
async def process_user_event(message: dict, metadata: dict):
    event = message.get("event")
    user_id = message.get("user_id")
    
    if event == "user_registered":
        await create_user_profile(user_id)
    elif event == "profile_updated":
        await update_search_index(user_id)

# Consumir desde el último offset
await client.consume(
    topics=["user-events"],
    group_id="user-processor",
    handler=process_user_event
)

# Consumir desde el principio
await client.consume(
    topics=["user-events"],
    group_id="analytics-processor",
    handler=process_user_event,
    auto_offset_reset="earliest"
)
```

### Características Avanzadas

```python
# Consumo con configuración avanzada
await client.consume(
    topics=["orders", "payments"],
    group_id="order-processor",
    handler=process_order_event,
    max_poll_records=100,
    session_timeout_ms=30000,
    enable_auto_commit=False,  # Commit manual
    max_retries=3
)

# Commit manual
async def process_with_manual_commit(message: dict, metadata: dict):
    try:
        await process_message(message)
        await client.commit_offset(metadata["topic"], metadata["partition"], metadata["offset"])
    except Exception as e:
        logger.error(f"Failed to process message: {e}")
        # No commit - mensaje será reprocesado
```

## Reliability Features

### Circuit Breaker

```python
from fastapi_microservices_sdk.communication.messaging.reliability import MessageCircuitBreaker

circuit_breaker = MessageCircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=ConnectionError
)

@circuit_breaker
async def publish_with_protection(topic: str, message: dict):
    await client.publish(topic, message)
```

### Retry Logic

```python
from fastapi_microservices_sdk.communication.messaging.reliability import RetryableMessageHandler

@RetryableMessageHandler(
    max_retries=3,
    backoff_factor=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
async def reliable_message_handler(message: dict, metadata: dict):
    # Procesamiento que puede fallar
    await external_api_call(message)
```

### Dead Letter Queue

```python
# Configuración automática de DLQ
client = RedisPubSubClient(
    host="localhost",
    port=6379,
    enable_dlq=True,
    dlq_suffix=".dlq",
    max_retries=3
)

# Los mensajes fallidos automáticamente van a topic.dlq
await client.subscribe("orders", process_order, enable_dlq=True)
```

## Monitoreo y Métricas

### Métricas Automáticas

```python
# Las métricas se recolectan automáticamente
metrics = await client.get_metrics()

print(f"Messages published: {metrics.messages_published}")
print(f"Messages consumed: {metrics.messages_consumed}")
print(f"Connection errors: {metrics.connection_errors}")
print(f"Processing errors: {metrics.processing_errors}")
```

### Health Checks

```python
# Verificar salud del cliente
health = await client.health_check()

if health.is_healthy:
    print("Client is healthy")
else:
    print(f"Client issues: {health.issues}")
```

## Mejores Prácticas

### 1. Manejo de Conexiones

```python
# Usar context manager
async with RedisPubSubClient(host="localhost") as client:
    await client.publish("topic", {"data": "value"})
    # Conexión se cierra automáticamente

# O manejo manual
client = RedisPubSubClient(host="localhost")
try:
    await client.connect()
    await client.publish("topic", {"data": "value"})
finally:
    await client.disconnect()
```

### 2. Serialización de Mensajes

```python
import json
from datetime import datetime

# Serializar objetos complejos
message = {
    "user_id": "123",
    "timestamp": datetime.now().isoformat(),
    "data": {"key": "value"}
}

await client.publish("events", message)
```

### 3. Manejo de Errores

```python
async def robust_message_handler(message: dict, metadata: dict):
    try:
        await process_message(message)
    except ValidationError as e:
        # Error de validación - no reintentar
        logger.error(f"Invalid message: {e}")
        await client.send_to_dlq(message, "validation_error")
    except ConnectionError as e:
        # Error de conexión - reintentar
        logger.warning(f"Connection error: {e}")
        raise  # Permitir retry automático
    except Exception as e:
        # Error desconocido - log y enviar a DLQ
        logger.error(f"Unexpected error: {e}")
        await client.send_to_dlq(message, "processing_error")
```

### 4. Configuración por Ambiente

```python
import os

config = {
    "development": {
        "redis_host": "localhost",
        "rabbitmq_host": "localhost",
        "kafka_servers": ["localhost:9092"]
    },
    "production": {
        "redis_host": os.getenv("REDIS_HOST"),
        "rabbitmq_host": os.getenv("RABBITMQ_HOST"),
        "kafka_servers": os.getenv("KAFKA_SERVERS", "").split(",")
    }
}

env = os.getenv("ENVIRONMENT", "development")
client_config = config[env]
```

## Troubleshooting

### Problemas Comunes

1. **Conexión Perdida**
   ```python
   # Configurar reconexión automática
   client = RedisPubSubClient(
       host="localhost",
       auto_reconnect=True,
       reconnect_delay=5.0,
       max_reconnect_attempts=10
   )
   ```

2. **Mensajes Duplicados**
   ```python
   # Implementar idempotencia
   processed_messages = set()
   
   async def idempotent_handler(message: dict, metadata: dict):
       message_id = metadata.get("message_id")
       if message_id in processed_messages:
           return  # Ya procesado
       
       await process_message(message)
       processed_messages.add(message_id)
   ```

3. **Backpressure**
   ```python
   # Limitar concurrencia
   semaphore = asyncio.Semaphore(10)
   
   async def rate_limited_handler(message: dict, metadata: dict):
       async with semaphore:
           await process_message(message)
   ```

## Ejemplos Completos

Ver los archivos de ejemplo en `examples/`:
- `redis_client_example.py`
- `rabbitmq_client_example.py`
- `kafka_client_example.py`
- `message_broker_base_example.py`
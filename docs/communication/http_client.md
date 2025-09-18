# HTTP Client Components

El módulo HTTP proporciona clientes HTTP avanzados con características empresariales como circuit breakers, retry logic, autenticación, y más.

## Arquitectura

### HTTP Client Base

El cliente HTTP base proporciona funcionalidad fundamental:

```python
from fastapi_microservices_sdk.communication.http.client import HTTPClient

client = HTTPClient(
    base_url="https://api.example.com",
    timeout=30.0,
    headers={"User-Agent": "MyService/1.0"}
)
```

### Enhanced HTTP Client

El cliente mejorado incluye características avanzadas:

```python
from fastapi_microservices_sdk.communication.http.enhanced_client import EnhancedHTTPClient

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    circuit_breaker_enabled=True,
    retry_enabled=True,
    caching_enabled=True,
    rate_limiting_enabled=True
)
```

## Configuración Básica

### Cliente Simple

```python
from fastapi_microservices_sdk.communication.http.client import HTTPClient

# Configuración básica
client = HTTPClient(base_url="https://jsonplaceholder.typicode.com")

# Realizar peticiones
response = await client.get("/posts/1")
print(response.json())

response = await client.post("/posts", json={
    "title": "New Post",
    "body": "Post content",
    "userId": 1
})
```

### Cliente con Autenticación

```python
from fastapi_microservices_sdk.communication.http.authentication import (
    BearerTokenAuth, BasicAuth, APIKeyAuth
)

# Bearer Token
auth = BearerTokenAuth(token="your-jwt-token")
client = HTTPClient(base_url="https://api.example.com", auth=auth)

# Basic Auth
auth = BasicAuth(username="user", password="pass")
client = HTTPClient(base_url="https://api.example.com", auth=auth)

# API Key
auth = APIKeyAuth(api_key="your-api-key", header_name="X-API-Key")
client = HTTPClient(base_url="https://api.example.com", auth=auth)
```

## Enhanced HTTP Client

### Configuración Avanzada

```python
from fastapi_microservices_sdk.communication.http.enhanced_client import EnhancedHTTPClient
from fastapi_microservices_sdk.communication.http.authentication import BearerTokenAuth

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    
    # Circuit Breaker
    circuit_breaker_enabled=True,
    failure_threshold=5,
    recovery_timeout=60,
    
    # Retry Logic
    retry_enabled=True,
    max_retries=3,
    retry_backoff_factor=2.0,
    
    # Caching
    caching_enabled=True,
    cache_ttl=300,  # 5 minutos
    
    # Rate Limiting
    rate_limiting_enabled=True,
    rate_limit=100,  # 100 requests per minute
    
    # Connection Pooling
    max_connections=20,
    max_keepalive_connections=5,
    
    # Timeouts
    timeout=30.0,
    connect_timeout=10.0,
    read_timeout=30.0,
    
    # Authentication
    auth=BearerTokenAuth(token="your-token"),
    
    # Headers
    default_headers={
        "User-Agent": "MyService/1.0",
        "Accept": "application/json"
    }
)
```

### Uso Básico

```python
# GET request
response = await client.get("/users/123")
user = response.json()

# POST request
new_user = {
    "name": "John Doe",
    "email": "john@example.com"
}
response = await client.post("/users", json=new_user)

# PUT request
updated_user = {"name": "Jane Doe"}
response = await client.put("/users/123", json=updated_user)

# DELETE request
response = await client.delete("/users/123")
```

### Características Avanzadas

#### Circuit Breaker

```python
# El circuit breaker se activa automáticamente
try:
    response = await client.get("/unreliable-endpoint")
except CircuitBreakerOpenError:
    print("Circuit breaker is open - service is down")
    # Usar fallback o cache
    response = await get_cached_response()
```

#### Retry Logic

```python
# Los reintentos son automáticos para errores transitorios
response = await client.get("/sometimes-fails")
# Se reintentará automáticamente en caso de:
# - Errores de conexión
# - Timeouts
# - Errores 5xx del servidor
```

#### Caching Inteligente

```python
# Primera llamada - va al servidor
response1 = await client.get("/users/123")

# Segunda llamada - viene del cache (si está dentro del TTL)
response2 = await client.get("/users/123")

# Invalidar cache manualmente
await client.invalidate_cache("/users/123")

# Cache con headers personalizados
response = await client.get(
    "/users/123",
    cache_key="user-123-profile",
    cache_ttl=600  # 10 minutos
)
```

#### Rate Limiting

```python
# El rate limiting es automático
for i in range(150):  # Más del límite
    try:
        response = await client.get(f"/users/{i}")
    except RateLimitExceededError as e:
        print(f"Rate limit exceeded. Retry after: {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
        response = await client.get(f"/users/{i}")
```

## Advanced Policies

### Retry Policies

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import (
    AdvancedRetryPolicy, RetryStrategy
)

# Exponential backoff
retry_policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.EXPONENTIAL,
    max_attempts=5,
    base_delay=1.0,
    max_delay=60.0,
    jitter=True
)

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    retry_policy=retry_policy
)
```

### Load Balancing

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import (
    LoadBalancer, LoadBalancingStrategy
)

# Round Robin Load Balancer
load_balancer = LoadBalancer(
    strategy=LoadBalancingStrategy.ROUND_ROBIN,
    endpoints=[
        "https://api1.example.com",
        "https://api2.example.com",
        "https://api3.example.com"
    ]
)

client = EnhancedHTTPClient(load_balancer=load_balancer)

# El cliente automáticamente distribuirá las peticiones
response = await client.get("/users")  # Puede ir a cualquier endpoint
```

### Service Discovery Integration

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import ServiceEndpoint

# Endpoints con health monitoring
endpoints = [
    ServiceEndpoint(
        url="https://api1.example.com",
        weight=1.0,
        health_check_path="/health"
    ),
    ServiceEndpoint(
        url="https://api2.example.com",
        weight=2.0,  # Doble peso
        health_check_path="/health"
    )
]

load_balancer = LoadBalancer(
    strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
    endpoints=endpoints,
    health_check_interval=30  # Verificar cada 30 segundos
)
```

## Middleware y Interceptors

### Request Interceptors

```python
async def logging_interceptor(request):
    print(f"Making request to: {request.url}")
    return request

async def auth_interceptor(request):
    # Renovar token si es necesario
    if await token_needs_refresh():
        new_token = await refresh_token()
        request.headers["Authorization"] = f"Bearer {new_token}"
    return request

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    request_interceptors=[logging_interceptor, auth_interceptor]
)
```

### Response Interceptors

```python
async def metrics_interceptor(response):
    # Registrar métricas
    await record_response_time(response.elapsed)
    await record_status_code(response.status_code)
    return response

async def error_interceptor(response):
    if response.status_code >= 400:
        await log_error(response)
    return response

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    response_interceptors=[metrics_interceptor, error_interceptor]
)
```

## Autenticación Avanzada

### JWT Token Management

```python
from fastapi_microservices_sdk.communication.http.authentication import JWTTokenAuth

class AutoRefreshJWTAuth(JWTTokenAuth):
    def __init__(self, initial_token: str, refresh_url: str):
        super().__init__(initial_token)
        self.refresh_url = refresh_url
    
    async def refresh_token_if_needed(self, request):
        if self.is_token_expired():
            new_token = await self.refresh_token()
            self.token = new_token
        return await super().apply_auth(request)

auth = AutoRefreshJWTAuth(
    initial_token="your-jwt-token",
    refresh_url="https://auth.example.com/refresh"
)

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    auth=auth
)
```

### OAuth 2.0

```python
from fastapi_microservices_sdk.communication.http.authentication import OAuth2Auth

auth = OAuth2Auth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.example.com/oauth/token",
    scopes=["read", "write"]
)

client = EnhancedHTTPClient(
    base_url="https://api.example.com",
    auth=auth
)
```

## Monitoreo y Métricas

### Métricas Automáticas

```python
# Obtener métricas del cliente
metrics = await client.get_metrics()

print(f"Total requests: {metrics.total_requests}")
print(f"Successful requests: {metrics.successful_requests}")
print(f"Failed requests: {metrics.failed_requests}")
print(f"Average response time: {metrics.avg_response_time}ms")
print(f"Circuit breaker activations: {metrics.circuit_breaker_activations}")
print(f"Cache hits: {metrics.cache_hits}")
print(f"Cache misses: {metrics.cache_misses}")
```

### Health Checks

```python
# Verificar salud del cliente
health = await client.health_check()

if health.is_healthy:
    print("Client is healthy")
    print(f"Active connections: {health.active_connections}")
    print(f"Circuit breaker state: {health.circuit_breaker_state}")
else:
    print(f"Client issues: {health.issues}")
```

### Tracing

```python
# Request tracing automático
response = await client.get("/users/123")

# Obtener información de tracing
trace_info = response.trace_info
print(f"Request ID: {trace_info.request_id}")
print(f"Total time: {trace_info.total_time}ms")
print(f"DNS lookup: {trace_info.dns_lookup_time}ms")
print(f"Connection: {trace_info.connection_time}ms")
print(f"TLS handshake: {trace_info.tls_handshake_time}ms")
print(f"Request sent: {trace_info.request_sent_time}ms")
print(f"Response received: {trace_info.response_received_time}ms")
```

## Configuración SSL/TLS

### Certificados Personalizados

```python
import ssl

# Crear contexto SSL personalizado
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# O cargar certificados específicos
ssl_context.load_cert_chain("/path/to/client.crt", "/path/to/client.key")
ssl_context.load_verify_locations("/path/to/ca.crt")

client = EnhancedHTTPClient(
    base_url="https://secure-api.example.com",
    ssl_context=ssl_context
)
```

### Mutual TLS (mTLS)

```python
client = EnhancedHTTPClient(
    base_url="https://secure-api.example.com",
    client_cert="/path/to/client.crt",
    client_key="/path/to/client.key",
    ca_cert="/path/to/ca.crt"
)
```

## Mejores Prácticas

### 1. Gestión de Conexiones

```python
# Usar context manager
async with EnhancedHTTPClient(base_url="https://api.example.com") as client:
    response = await client.get("/users")
    # Conexiones se cierran automáticamente

# O gestión manual
client = EnhancedHTTPClient(base_url="https://api.example.com")
try:
    await client.start()
    response = await client.get("/users")
finally:
    await client.close()
```

### 2. Manejo de Errores

```python
from fastapi_microservices_sdk.communication.exceptions import (
    CommunicationError,
    CommunicationTimeoutError,
    CommunicationConnectionError
)

try:
    response = await client.get("/users/123")
except CommunicationTimeoutError:
    # Timeout específico
    response = await get_cached_user(123)
except CommunicationConnectionError:
    # Error de conexión
    response = await fallback_service.get_user(123)
except CommunicationError as e:
    # Error general de comunicación
    logger.error(f"Communication error: {e}")
    raise
```

### 3. Configuración por Ambiente

```python
import os

def create_http_client():
    if os.getenv("ENVIRONMENT") == "production":
        return EnhancedHTTPClient(
            base_url=os.getenv("API_BASE_URL"),
            circuit_breaker_enabled=True,
            retry_enabled=True,
            caching_enabled=True,
            rate_limiting_enabled=True,
            max_connections=50,
            timeout=30.0
        )
    else:
        return HTTPClient(
            base_url="http://localhost:8000",
            timeout=10.0
        )

client = create_http_client()
```

### 4. Testing

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_client():
    client = AsyncMock(spec=EnhancedHTTPClient)
    client.get.return_value.json.return_value = {"id": 123, "name": "Test User"}
    client.get.return_value.status_code = 200
    return client

async def test_get_user(mock_client):
    response = await mock_client.get("/users/123")
    user = response.json()
    
    assert user["id"] == 123
    assert user["name"] == "Test User"
    mock_client.get.assert_called_once_with("/users/123")
```

## Troubleshooting

### Problemas Comunes

1. **Timeouts Frecuentes**
   ```python
   # Aumentar timeouts
   client = EnhancedHTTPClient(
       base_url="https://slow-api.example.com",
       timeout=60.0,
       connect_timeout=30.0,
       read_timeout=60.0
   )
   ```

2. **Circuit Breaker Activándose**
   ```python
   # Ajustar configuración
   client = EnhancedHTTPClient(
       base_url="https://api.example.com",
       failure_threshold=10,  # Más tolerante
       recovery_timeout=30    # Recuperación más rápida
   )
   ```

3. **Problemas de SSL**
   ```python
   # Deshabilitar verificación SSL (solo desarrollo)
   client = EnhancedHTTPClient(
       base_url="https://self-signed.example.com",
       verify_ssl=False
   )
   ```

## Ejemplos Completos

Ver los archivos de ejemplo en `examples/`:
- `enhanced_http_client_example.py`
- `advanced_policies_example.py`
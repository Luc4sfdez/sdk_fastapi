# Communication Protocols

El módulo de protocolos proporciona abstracciones para patrones de comunicación avanzados como API Gateway y Service Mesh.

> **Nota**: Los componentes de protocolos están actualmente en desarrollo. Esta documentación describe la funcionalidad planificada.

## API Gateway

### Arquitectura

El API Gateway actúa como punto de entrada único para todos los clientes, proporcionando:

- **Routing**: Enrutamiento de requests a servicios backend
- **Authentication**: Autenticación centralizada
- **Rate Limiting**: Control de tasa de requests
- **Load Balancing**: Distribución de carga
- **Request/Response Transformation**: Transformación de datos
- **Caching**: Cache de respuestas
- **Monitoring**: Monitoreo y métricas

### Configuración Básica

```python
from fastapi_microservices_sdk.communication.protocols.api_gateway import APIGateway

gateway = APIGateway(
    host="0.0.0.0",
    port=8080,
    services={
        "user-service": "http://user-service:8000",
        "order-service": "http://order-service:8000",
        "payment-service": "http://payment-service:8000"
    }
)
```

### Configuración de Rutas

```python
# Configuración declarativa
routes = [
    {
        "path": "/api/v1/users/*",
        "service": "user-service",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "auth_required": True,
        "rate_limit": "100/minute"
    },
    {
        "path": "/api/v1/orders/*",
        "service": "order-service", 
        "methods": ["GET", "POST"],
        "auth_required": True,
        "rate_limit": "50/minute",
        "cache_ttl": 300
    },
    {
        "path": "/api/v1/payments/*",
        "service": "payment-service",
        "methods": ["POST"],
        "auth_required": True,
        "rate_limit": "10/minute",
        "require_https": True
    }
]

gateway.configure_routes(routes)
```

### Middleware Pipeline

```python
from fastapi_microservices_sdk.communication.protocols.api_gateway.middleware import (
    AuthenticationMiddleware,
    RateLimitingMiddleware,
    LoggingMiddleware,
    CachingMiddleware,
    CORSMiddleware
)

gateway.add_middleware([
    CORSMiddleware(
        allow_origins=["https://frontend.example.com"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"]
    ),
    AuthenticationMiddleware(
        jwt_secret="your-secret-key",
        jwt_algorithm="HS256"
    ),
    RateLimitingMiddleware(
        default_rate_limit="1000/hour",
        storage="redis://localhost:6379"
    ),
    CachingMiddleware(
        cache_backend="redis://localhost:6379",
        default_ttl=300
    ),
    LoggingMiddleware(
        log_requests=True,
        log_responses=True,
        log_level="INFO"
    )
])
```

### Load Balancing

```python
# Configuración de load balancing por servicio
services_config = {
    "user-service": {
        "instances": [
            "http://user-service-1:8000",
            "http://user-service-2:8000", 
            "http://user-service-3:8000"
        ],
        "load_balancing": "round_robin",
        "health_check": "/health",
        "health_check_interval": 30
    },
    "order-service": {
        "instances": [
            "http://order-service-1:8000",
            "http://order-service-2:8000"
        ],
        "load_balancing": "least_connections",
        "health_check": "/health"
    }
}

gateway.configure_services(services_config)
```

### Request/Response Transformation

```python
# Transformadores personalizados
class RequestTransformer:
    async def transform_request(self, request):
        # Agregar headers personalizados
        request.headers["X-Gateway-Version"] = "1.0"
        request.headers["X-Request-ID"] = generate_request_id()
        
        # Transformar body si es necesario
        if request.path.startswith("/api/v1/legacy"):
            request.body = await self.transform_legacy_format(request.body)
        
        return request

class ResponseTransformer:
    async def transform_response(self, response):
        # Agregar headers de respuesta
        response.headers["X-Gateway-Response-Time"] = str(response.elapsed)
        
        # Transformar formato de respuesta
        if response.headers.get("Content-Type") == "application/xml":
            response.body = await self.xml_to_json(response.body)
            response.headers["Content-Type"] = "application/json"
        
        return response

gateway.add_transformers(
    request_transformer=RequestTransformer(),
    response_transformer=ResponseTransformer()
)
```

### Circuit Breaker

```python
from fastapi_microservices_sdk.communication.protocols.api_gateway.circuit_breaker import CircuitBreaker

# Configurar circuit breaker por servicio
circuit_breakers = {
    "user-service": CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60,
        expected_exception=ConnectionError
    ),
    "payment-service": CircuitBreaker(
        failure_threshold=3,  # Más sensible para pagos
        recovery_timeout=120,
        expected_exception=(ConnectionError, TimeoutError)
    )
}

gateway.configure_circuit_breakers(circuit_breakers)
```

### Autenticación y Autorización

```python
from fastapi_microservices_sdk.communication.protocols.api_gateway.auth import (
    JWTAuthProvider,
    OAuth2AuthProvider,
    APIKeyAuthProvider
)

# Múltiples proveedores de autenticación
auth_providers = [
    JWTAuthProvider(
        secret_key="jwt-secret",
        algorithm="HS256",
        token_url="/auth/token"
    ),
    OAuth2AuthProvider(
        client_id="gateway-client",
        client_secret="gateway-secret",
        authorization_url="https://auth.example.com/oauth/authorize",
        token_url="https://auth.example.com/oauth/token"
    ),
    APIKeyAuthProvider(
        api_key_header="X-API-Key",
        api_key_query="api_key"
    )
]

gateway.configure_auth(auth_providers)
```

### Configuración Avanzada

```python
gateway = APIGateway(
    host="0.0.0.0",
    port=8080,
    
    # SSL/TLS
    ssl_cert="/path/to/cert.pem",
    ssl_key="/path/to/key.pem",
    
    # Performance
    max_connections=1000,
    keepalive_timeout=65,
    
    # Timeouts
    request_timeout=30,
    upstream_timeout=25,
    
    # Retry
    max_retries=3,
    retry_backoff=2.0,
    
    # Monitoring
    enable_metrics=True,
    metrics_port=9090,
    
    # Logging
    access_log=True,
    error_log=True,
    log_level="INFO"
)
```

## Service Mesh

### Arquitectura

El Service Mesh proporciona una capa de infraestructura para la comunicación entre servicios:

- **Service Discovery**: Descubrimiento automático de servicios
- **Load Balancing**: Balanceeo de carga inteligente
- **Circuit Breaking**: Protección contra fallos
- **Retry Logic**: Reintentos automáticos
- **Observability**: Métricas, logging y tracing
- **Security**: mTLS automático entre servicios

### Configuración Básica

```python
from fastapi_microservices_sdk.communication.protocols.service_mesh import ServiceMesh

mesh = ServiceMesh(
    service_name="user-service",
    service_version="1.0.0",
    namespace="production",
    
    # Service Discovery
    discovery_backend="consul",  # consul, etcd, kubernetes
    discovery_config={
        "host": "consul.example.com",
        "port": 8500
    },
    
    # Security
    enable_mtls=True,
    cert_path="/etc/certs/service.crt",
    key_path="/etc/certs/service.key",
    ca_path="/etc/certs/ca.crt"
)
```

### Service Registration

```python
# Registro automático del servicio
await mesh.register_service(
    service_id="user-service-1",
    address="10.0.1.100",
    port=8000,
    health_check="/health",
    tags=["api", "v1", "users"],
    metadata={
        "version": "1.0.0",
        "environment": "production",
        "region": "us-east-1"
    }
)

# Health check automático
@mesh.health_check
async def health_check():
    # Verificar dependencias
    db_healthy = await check_database()
    cache_healthy = await check_cache()
    
    if db_healthy and cache_healthy:
        return {"status": "healthy", "checks": {"db": "ok", "cache": "ok"}}
    else:
        return {"status": "unhealthy", "checks": {"db": db_healthy, "cache": cache_healthy}}
```

### Service Discovery

```python
# Descubrir servicios
order_service = await mesh.discover_service("order-service")
print(f"Order service available at: {order_service.address}:{order_service.port}")

# Descubrir múltiples instancias
payment_services = await mesh.discover_services("payment-service")
for service in payment_services:
    print(f"Payment service: {service.address}:{service.port} (health: {service.health})")

# Watch para cambios en servicios
@mesh.watch_service("notification-service")
async def on_notification_service_change(event, service):
    if event == "added":
        print(f"New notification service instance: {service.address}")
    elif event == "removed":
        print(f"Notification service instance removed: {service.address}")
    elif event == "updated":
        print(f"Notification service instance updated: {service.address}")
```

### Intelligent Load Balancing

```python
from fastapi_microservices_sdk.communication.protocols.service_mesh.load_balancer import (
    LoadBalancingStrategy
)

# Configurar estrategias de load balancing
mesh.configure_load_balancing({
    "order-service": {
        "strategy": LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        "health_check_required": True,
        "weights": {
            "order-service-1": 1.0,
            "order-service-2": 2.0,  # Instancia más potente
            "order-service-3": 1.0
        }
    },
    "payment-service": {
        "strategy": LoadBalancingStrategy.ROUND_ROBIN,
        "sticky_sessions": True,
        "session_affinity_header": "X-User-ID"
    }
})
```

### Circuit Breaker Integration

```python
# Circuit breakers automáticos por servicio
mesh.configure_circuit_breakers({
    "external-api": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "half_open_max_calls": 3
    },
    "payment-gateway": {
        "failure_threshold": 3,
        "recovery_timeout": 120,
        "timeout": 10.0
    }
})

# Uso automático con decorador
@mesh.circuit_breaker("external-api")
async def call_external_api(data):
    async with mesh.get_client("external-api") as client:
        return await client.post("/api/process", json=data)
```

### Retry Policies

```python
# Configurar políticas de retry por servicio
mesh.configure_retry_policies({
    "user-service": {
        "max_attempts": 3,
        "backoff_strategy": "exponential",
        "base_delay": 1.0,
        "max_delay": 10.0,
        "jitter": True
    },
    "notification-service": {
        "max_attempts": 5,
        "backoff_strategy": "linear",
        "base_delay": 0.5
    }
})
```

### Observability

```python
# Métricas automáticas
metrics = await mesh.get_metrics()
print(f"Service calls: {metrics.total_calls}")
print(f"Success rate: {metrics.success_rate}%")
print(f"Average latency: {metrics.avg_latency}ms")

# Tracing distribuido
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@mesh.trace_calls
async def process_order(order_data):
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_data["id"])
        
        # Llamadas automáticamente trazadas
        user = await mesh.call_service("user-service", "/users/{}", order_data["user_id"])
        payment = await mesh.call_service("payment-service", "/payments", order_data["payment"])
        
        return {"user": user, "payment": payment}
```

### Security (mTLS)

```python
# mTLS automático entre servicios
mesh = ServiceMesh(
    service_name="user-service",
    enable_mtls=True,
    
    # Certificados automáticos
    auto_cert_renewal=True,
    cert_authority="internal-ca",
    
    # Políticas de seguridad
    security_policies={
        "allow_services": ["order-service", "payment-service"],
        "deny_services": ["external-service"],
        "require_auth": True
    }
)

# Verificación automática de certificados
@mesh.require_valid_cert
async def secure_endpoint(request):
    # Solo servicios con certificados válidos pueden acceder
    return {"message": "Secure data"}
```

### Configuration Management

```python
# Configuración distribuida
config = await mesh.get_config("database")
db_url = config.get("url")
db_pool_size = config.get("pool_size", 10)

# Watch para cambios de configuración
@mesh.watch_config("feature_flags")
async def on_feature_flags_change(config):
    global feature_flags
    feature_flags = config
    print("Feature flags updated:", feature_flags)
```

## Integration Patterns

### API Gateway + Service Mesh

```python
# Integración completa
from fastapi_microservices_sdk.communication.protocols import APIGateway, ServiceMesh

# Service Mesh para comunicación interna
mesh = ServiceMesh(
    service_name="api-gateway",
    discovery_backend="kubernetes",
    enable_mtls=True
)

# API Gateway para tráfico externo
gateway = APIGateway(
    host="0.0.0.0",
    port=8080,
    service_mesh=mesh,  # Usar service mesh para descubrimiento
    
    # Rutas dinámicas basadas en service discovery
    dynamic_routing=True,
    route_prefix="/api/v1"
)

# Las rutas se crean automáticamente basadas en servicios descubiertos
await gateway.start()
```

### Microservice Integration

```python
from fastapi import FastAPI
from fastapi_microservices_sdk.communication.protocols.integration import ServiceMeshMiddleware

app = FastAPI()

# Middleware para integración automática
app.add_middleware(
    ServiceMeshMiddleware,
    service_name="user-service",
    service_version="1.0.0",
    enable_tracing=True,
    enable_metrics=True,
    enable_service_discovery=True
)

@app.get("/users/{user_id}")
async def get_user(user_id: int, mesh: ServiceMesh = Depends(get_service_mesh)):
    # Llamadas automáticamente balanceadas y trazadas
    profile = await mesh.call_service("profile-service", f"/profiles/{user_id}")
    preferences = await mesh.call_service("preference-service", f"/preferences/{user_id}")
    
    return {
        "user_id": user_id,
        "profile": profile,
        "preferences": preferences
    }
```

## Deployment

### Docker Configuration

```dockerfile
# API Gateway
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080 9090

CMD ["python", "-m", "api_gateway"]
```

### Kubernetes Deployment

```yaml
# API Gateway Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: api-gateway:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: SERVICE_MESH_ENABLED
          value: "true"
        - name: DISCOVERY_BACKEND
          value: "kubernetes"
---
# Service Mesh ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: service-mesh-config
data:
  config.yaml: |
    service_mesh:
      discovery:
        backend: kubernetes
        namespace: default
      security:
        enable_mtls: true
        auto_cert_renewal: true
      load_balancing:
        default_strategy: round_robin
      circuit_breaker:
        default_failure_threshold: 5
        default_recovery_timeout: 60
```

### Istio Integration

```yaml
# Istio VirtualService para API Gateway
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-gateway
spec:
  hosts:
  - api.example.com
  gateways:
  - api-gateway
  http:
  - match:
    - uri:
        prefix: /api/v1/
    route:
    - destination:
        host: api-gateway
        port:
          number: 8080
    fault:
      delay:
        percentage:
          value: 0.1
        fixedDelay: 5s
    retries:
      attempts: 3
      perTryTimeout: 10s
```

## Monitoring and Observability

### Metrics

```python
# Métricas automáticas disponibles
from prometheus_client import CollectorRegistry, generate_latest

registry = CollectorRegistry()

# API Gateway metrics
gateway_requests_total = Counter(
    'gateway_requests_total',
    'Total gateway requests',
    ['method', 'path', 'status'],
    registry=registry
)

gateway_request_duration = Histogram(
    'gateway_request_duration_seconds',
    'Gateway request duration',
    ['method', 'path'],
    registry=registry
)

# Service Mesh metrics
mesh_service_calls_total = Counter(
    'mesh_service_calls_total',
    'Total service mesh calls',
    ['source_service', 'target_service', 'status'],
    registry=registry
)

mesh_circuit_breaker_state = Gauge(
    'mesh_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service'],
    registry=registry
)
```

### Health Checks

```python
# Health checks integrados
@gateway.health_check
async def gateway_health():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "services": await check_downstream_services()
    }
    
    healthy = all(checks.values())
    
    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Best Practices

### 1. Service Design

```python
# Diseño de servicios para service mesh
class UserService:
    def __init__(self, mesh: ServiceMesh):
        self.mesh = mesh
    
    @mesh.circuit_breaker("profile-service")
    @mesh.retry_policy("profile-service")
    @mesh.trace_calls
    async def get_user_profile(self, user_id: int):
        return await self.mesh.call_service(
            "profile-service",
            f"/profiles/{user_id}"
        )
```

### 2. Error Handling

```python
from fastapi_microservices_sdk.communication.protocols.exceptions import (
    ServiceUnavailableError,
    CircuitBreakerOpenError,
    ServiceDiscoveryError
)

async def resilient_service_call(service_name: str, endpoint: str):
    try:
        return await mesh.call_service(service_name, endpoint)
    except CircuitBreakerOpenError:
        # Usar cache o fallback
        return await get_cached_response(service_name, endpoint)
    except ServiceUnavailableError:
        # Degradar funcionalidad
        return await get_fallback_response()
    except ServiceDiscoveryError:
        # Log y usar configuración estática
        logger.error(f"Service discovery failed for {service_name}")
        return await call_static_endpoint(endpoint)
```

### 3. Configuration Management

```python
import os
from typing import Dict, Any

def get_protocol_config() -> Dict[str, Any]:
    return {
        "api_gateway": {
            "host": os.getenv("GATEWAY_HOST", "0.0.0.0"),
            "port": int(os.getenv("GATEWAY_PORT", "8080")),
            "enable_auth": os.getenv("GATEWAY_AUTH_ENABLED", "true").lower() == "true",
            "rate_limit": os.getenv("GATEWAY_RATE_LIMIT", "1000/hour")
        },
        "service_mesh": {
            "service_name": os.getenv("SERVICE_NAME"),
            "discovery_backend": os.getenv("DISCOVERY_BACKEND", "kubernetes"),
            "enable_mtls": os.getenv("MTLS_ENABLED", "true").lower() == "true",
            "namespace": os.getenv("SERVICE_NAMESPACE", "default")
        }
    }
```

## Roadmap

### Características Planificadas

- ✅ API Gateway básico
- ✅ Service Mesh básico
- 🔄 Service Discovery avanzado
- 🔄 Load Balancing inteligente
- 🔄 Circuit Breaker patterns
- 🔄 mTLS automático
- 🔄 Observability completa
- 🔄 Integración con Istio/Linkerd
- 🔄 GraphQL Gateway
- 🔄 WebSocket support

> **Estado**: En desarrollo activo. Los componentes básicos están siendo implementados.

## Examples

Una vez implementados, los ejemplos estarán disponibles en:
- `examples/api_gateway_example.py`
- `examples/service_mesh_example.py`
- `examples/protocols_integration_example.py`
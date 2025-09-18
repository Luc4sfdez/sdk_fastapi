# gRPC Components

El módulo gRPC proporciona soporte para comunicación de alto rendimiento entre microservicios usando Protocol Buffers y gRPC.

> **Nota**: Los componentes gRPC están actualmente en desarrollo. Esta documentación describe la funcionalidad planificada.

## Arquitectura

### gRPC Client

Cliente para realizar llamadas gRPC a otros servicios:

```python
from fastapi_microservices_sdk.communication.grpc.client import GRPCClient

# Configuración básica
client = GRPCClient(
    host="localhost",
    port=50051,
    secure=False
)

# Configuración con TLS
client = GRPCClient(
    host="grpc.example.com",
    port=443,
    secure=True,
    credentials="/path/to/credentials.pem"
)
```

### gRPC Server

Servidor para exponer servicios gRPC:

```python
from fastapi_microservices_sdk.communication.grpc.server import GRPCServer

server = GRPCServer(
    host="0.0.0.0",
    port=50051,
    max_workers=10
)

# Registrar servicios
server.add_service(UserServiceServicer(), user_service_pb2_grpc.add_UserServiceServicer_to_server)

# Iniciar servidor
await server.start()
```

### Proto Generator

Generador automático de archivos Protocol Buffer:

```python
from fastapi_microservices_sdk.communication.grpc.proto_generator import ProtoGenerator

generator = ProtoGenerator()

# Generar proto desde modelo Pydantic
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

proto_content = generator.generate_from_pydantic(User, service_name="UserService")
```

## Uso Básico (Planificado)

### Definición de Servicios

```python
# user_service.proto (generado automáticamente)
syntax = "proto3";

package user;

service UserService {
    rpc GetUser(GetUserRequest) returns (User);
    rpc CreateUser(CreateUserRequest) returns (User);
    rpc UpdateUser(UpdateUserRequest) returns (User);
    rpc DeleteUser(DeleteUserRequest) returns (Empty);
}

message User {
    int32 id = 1;
    string name = 2;
    string email = 3;
}

message GetUserRequest {
    int32 id = 1;
}

message CreateUserRequest {
    string name = 1;
    string email = 2;
}
```

### Implementación del Servidor

```python
import grpc
from concurrent import futures
from fastapi_microservices_sdk.communication.grpc.server import GRPCServer
import user_service_pb2_grpc
import user_service_pb2

class UserServiceServicer(user_service_pb2_grpc.UserServiceServicer):
    async def GetUser(self, request, context):
        # Lógica para obtener usuario
        user = await get_user_from_db(request.id)
        return user_service_pb2.User(
            id=user.id,
            name=user.name,
            email=user.email
        )
    
    async def CreateUser(self, request, context):
        # Lógica para crear usuario
        user = await create_user_in_db(request.name, request.email)
        return user_service_pb2.User(
            id=user.id,
            name=user.name,
            email=user.email
        )

# Configurar y iniciar servidor
server = GRPCServer(port=50051)
server.add_service(UserServiceServicer(), user_service_pb2_grpc.add_UserServiceServicer_to_server)
await server.start()
```

### Cliente gRPC

```python
from fastapi_microservices_sdk.communication.grpc.client import GRPCClient
import user_service_pb2_grpc
import user_service_pb2

# Crear cliente
client = GRPCClient(host="localhost", port=50051)
await client.connect()

# Crear stub
stub = user_service_pb2_grpc.UserServiceStub(client.channel)

# Realizar llamadas
request = user_service_pb2.GetUserRequest(id=123)
response = await stub.GetUser(request)

print(f"User: {response.name} ({response.email})")
```

## Características Avanzadas (Planificadas)

### Streaming

```python
# Server streaming
class UserServiceServicer(user_service_pb2_grpc.UserServiceServicer):
    async def ListUsers(self, request, context):
        users = await get_all_users()
        for user in users:
            yield user_service_pb2.User(
                id=user.id,
                name=user.name,
                email=user.email
            )

# Client streaming
async def create_users_batch(stub):
    async def user_generator():
        for i in range(10):
            yield user_service_pb2.CreateUserRequest(
                name=f"User {i}",
                email=f"user{i}@example.com"
            )
    
    response = await stub.CreateUsersBatch(user_generator())
    return response
```

### Interceptors

```python
from fastapi_microservices_sdk.communication.grpc.interceptors import (
    LoggingInterceptor,
    MetricsInterceptor,
    AuthInterceptor
)

# Server interceptors
server = GRPCServer(
    port=50051,
    interceptors=[
        LoggingInterceptor(),
        MetricsInterceptor(),
        AuthInterceptor(secret_key="your-secret")
    ]
)

# Client interceptors
client = GRPCClient(
    host="localhost",
    port=50051,
    interceptors=[
        LoggingInterceptor(),
        MetricsInterceptor()
    ]
)
```

### Load Balancing

```python
# Cliente con load balancing
client = GRPCClient(
    targets=[
        "grpc1.example.com:50051",
        "grpc2.example.com:50051",
        "grpc3.example.com:50051"
    ],
    load_balancing_policy="round_robin"
)
```

### Health Checking

```python
from grpc_health.v1 import health_pb2_grpc, health_pb2

# Implementar health check
class HealthServicer(health_pb2_grpc.HealthServicer):
    async def Check(self, request, context):
        # Verificar salud del servicio
        if await is_service_healthy():
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.SERVING
            )
        else:
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.NOT_SERVING
            )

# Agregar al servidor
server.add_service(HealthServicer(), health_pb2_grpc.add_HealthServicer_to_server)
```

## Integración con FastAPI

### Middleware gRPC

```python
from fastapi import FastAPI
from fastapi_microservices_sdk.communication.grpc.middleware import GRPCMiddleware

app = FastAPI()

# Agregar middleware para manejar requests gRPC
app.add_middleware(
    GRPCMiddleware,
    grpc_server_port=50051,
    enable_reflection=True
)
```

### Generación Automática de Endpoints

```python
from fastapi_microservices_sdk.communication.grpc.integration import grpc_to_rest

# Generar endpoints REST desde servicios gRPC
@grpc_to_rest(UserServiceServicer)
class UserAPI:
    pass

# Automáticamente genera:
# GET /users/{id} -> GetUser
# POST /users -> CreateUser
# PUT /users/{id} -> UpdateUser
# DELETE /users/{id} -> DeleteUser
```

## Configuración y Deployment

### Configuración de Producción

```python
import ssl

# Configuración SSL/TLS
credentials = grpc.ssl_server_credentials([
    (private_key, certificate_chain)
])

server = GRPCServer(
    port=50051,
    credentials=credentials,
    max_workers=50,
    options=[
        ('grpc.keepalive_time_ms', 30000),
        ('grpc.keepalive_timeout_ms', 5000),
        ('grpc.keepalive_permit_without_calls', True),
        ('grpc.http2.max_pings_without_data', 0),
        ('grpc.http2.min_time_between_pings_ms', 10000),
        ('grpc.http2.min_ping_interval_without_data_ms', 300000)
    ]
)
```

### Docker Configuration

```dockerfile
# Dockerfile para servicio gRPC
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 50051

CMD ["python", "-m", "grpc_server"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-grpc-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-grpc-service
  template:
    metadata:
      labels:
        app: user-grpc-service
    spec:
      containers:
      - name: user-service
        image: user-grpc-service:latest
        ports:
        - containerPort: 50051
          name: grpc
        env:
        - name: GRPC_PORT
          value: "50051"
---
apiVersion: v1
kind: Service
metadata:
  name: user-grpc-service
spec:
  selector:
    app: user-grpc-service
  ports:
  - port: 50051
    targetPort: 50051
    name: grpc
  type: ClusterIP
```

## Monitoreo y Observabilidad

### Métricas

```python
from prometheus_client import Counter, Histogram, Gauge

# Métricas automáticas
grpc_requests_total = Counter(
    'grpc_requests_total',
    'Total gRPC requests',
    ['method', 'status']
)

grpc_request_duration = Histogram(
    'grpc_request_duration_seconds',
    'gRPC request duration',
    ['method']
)

grpc_active_connections = Gauge(
    'grpc_active_connections',
    'Active gRPC connections'
)
```

### Logging

```python
import logging
from fastapi_microservices_sdk.communication.grpc.logging import GRPCLogger

logger = GRPCLogger(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Logging automático de requests/responses
server = GRPCServer(
    port=50051,
    logger=logger,
    log_requests=True,
    log_responses=True
)
```

### Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer

# Configurar tracing
tracer = trace.get_tracer(__name__)

# Instrumentar servidor gRPC
GrpcInstrumentorServer().instrument()

server = GRPCServer(port=50051)
```

## Testing

### Unit Testing

```python
import pytest
import grpc_testing
import user_service_pb2_grpc
import user_service_pb2

@pytest.fixture
def grpc_channel():
    servicers = {
        user_service_pb2_grpc.DESCRIPTOR.services_by_name['UserService']: UserServiceServicer()
    }
    return grpc_testing.channel(servicers, grpc_testing.strict_real_time())

async def test_get_user(grpc_channel):
    stub = user_service_pb2_grpc.UserServiceStub(grpc_channel)
    
    request = user_service_pb2.GetUserRequest(id=123)
    response = await stub.GetUser(request)
    
    assert response.id == 123
    assert response.name == "Test User"
```

### Integration Testing

```python
import pytest
from fastapi_microservices_sdk.communication.grpc.testing import GRPCTestClient

@pytest.fixture
async def grpc_test_client():
    client = GRPCTestClient(UserServiceServicer())
    await client.start()
    yield client
    await client.stop()

async def test_user_service_integration(grpc_test_client):
    # Test crear usuario
    create_request = user_service_pb2.CreateUserRequest(
        name="John Doe",
        email="john@example.com"
    )
    user = await grpc_test_client.CreateUser(create_request)
    
    # Test obtener usuario
    get_request = user_service_pb2.GetUserRequest(id=user.id)
    retrieved_user = await grpc_test_client.GetUser(get_request)
    
    assert retrieved_user.name == "John Doe"
    assert retrieved_user.email == "john@example.com"
```

## Mejores Prácticas

### 1. Definición de Servicios

```python
# Usar versionado en servicios
syntax = "proto3";

package user.v1;

service UserServiceV1 {
    // Métodos del servicio
}
```

### 2. Manejo de Errores

```python
import grpc

class UserServiceServicer(user_service_pb2_grpc.UserServiceServicer):
    async def GetUser(self, request, context):
        try:
            user = await get_user_from_db(request.id)
            if not user:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User not found")
                return user_service_pb2.User()
            
            return user_service_pb2.User(
                id=user.id,
                name=user.name,
                email=user.email
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.User()
```

### 3. Configuración por Ambiente

```python
import os

def create_grpc_server():
    if os.getenv("ENVIRONMENT") == "production":
        return GRPCServer(
            port=50051,
            max_workers=50,
            enable_reflection=False,
            credentials=load_ssl_credentials()
        )
    else:
        return GRPCServer(
            port=50051,
            max_workers=10,
            enable_reflection=True
        )
```

## Roadmap

### Características Planificadas

- ✅ Cliente gRPC básico
- ✅ Servidor gRPC básico  
- ✅ Generador de Protocol Buffers
- 🔄 Interceptors avanzados
- 🔄 Load balancing
- 🔄 Health checking
- 🔄 Streaming support
- 🔄 Integración con FastAPI
- 🔄 Testing utilities
- 🔄 Métricas y observabilidad

> **Estado**: En desarrollo activo. Los componentes básicos están siendo implementados.

## Ejemplos

Una vez implementados, los ejemplos estarán disponibles en:
- `examples/grpc_client_example.py`
- `examples/grpc_server_example.py`
- `examples/grpc_streaming_example.py`
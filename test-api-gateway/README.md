# test-api-gateway

Test API Gateway

## Características

- 🌐 **Proxy transparente** a microservicios
- 🚦 **Rate limiting** configurable
- 📊 **Logging** de requests/responses
- 🔒 **Headers de seguridad** automáticos
- 📚 **Documentación automática** con Swagger/OpenAPI
- 🐳 **Docker** ready
- ✅ **Health checks** de servicios

## Inicio Rápido

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar gateway
python main.py
```

### Docker

```bash
# Build y ejecutar
docker-compose up --build

# Solo ejecutar
docker-compose up -d
```

## Configuración

### Variables de Entorno

```env
PORT=8092
ENVIRONMENT=development

# Servicios backend
SERVICES={"auth":"http://localhost:8001","users":"http://localhost:8002"}

# Rate limiting
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60

# Timeouts
REQUEST_TIMEOUT=30
```

### Configurar Servicios

Edita la configuración de servicios en `config.py`:

```python
SERVICES = {
    "auth": "http://auth-service:8001",
    "users": "http://user-service:8002", 
    "products": "http://product-service:8003",
    "orders": "http://order-service:8004"
}
```

## Uso

### Routing Automático

El gateway enruta automáticamente requests usando el patrón:

```
/api/{service_name}/{endpoint}
```

**Ejemplos:**

```bash
# Login (auth service)
curl -X POST "http://localhost:8092/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Get users (users service)  
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8092/api/users/"

# Get products (products service)
curl "http://localhost:8092/api/products/"
```

### Endpoints del Gateway

- `GET /` - Información del gateway
- `GET /api/services` - Estado de servicios backend
- `GET /api/routes` - Rutas disponibles
- `GET /health/` - Health check completo
- `GET /docs` - Documentación Swagger

### Monitoreo

```bash
# Estado de servicios
curl "http://localhost:8092/api/services"

# Health check
curl "http://localhost:8092/health/"

# Rutas disponibles
curl "http://localhost:8092/api/routes"
```

## Características Avanzadas

### Rate Limiting

- **Límite por defecto**: 100 requests por minuto por IP
- **Headers de respuesta**: `X-RateLimit-*`
- **Configurable** via variables de entorno

### Logging

- **Request/Response logging** automático
- **Tiempo de procesamiento** en headers
- **Logs estructurados** en JSON

### Headers de Seguridad

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `X-Gateway: test-api-gateway`

### Manejo de Errores

- **Timeout**: 504 Gateway Timeout
- **Service unavailable**: 503 Service Unavailable
- **Service not found**: 404 Not Found
- **Rate limit**: 429 Too Many Requests

## Arquitectura

```
Client Request
     ↓
API Gateway (8092)
     ↓
┌─────────────────────────────────┐
│  Middleware Stack               │
│  ├── CORS                       │
│  ├── Rate Limiting              │
│  ├── Logging                    │
│  └── Security Headers           │
└─────────────────────────────────┘
     ↓
┌─────────────────────────────────┐
│  Service Router                 │
│  ├── /api/auth/* → Auth Service │
│  ├── /api/users/* → User Service│
│  └── /api/products/* → Products │
└─────────────────────────────────┘
     ↓
Backend Microservices
```

## Documentación

- **Swagger UI**: http://localhost:8092/docs
- **ReDoc**: http://localhost:8092/redoc
- **Health Check**: http://localhost:8092/health/

## Licencia

MIT License
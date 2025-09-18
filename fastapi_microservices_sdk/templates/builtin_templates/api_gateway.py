"""
API Gateway Template

Gateway unificado para todos los microservicios.
"""

from typing import Dict, Any
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class APIGatewayTemplate:
    """Template para API Gateway."""
    
    @staticmethod
    def create_template() -> Template:
        """Crear template de API Gateway."""
        config = TemplateConfig(
            id="api_gateway",
            name="API Gateway",
            description="Gateway unificado para enrutar requests a microservicios",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Nombre del gateway",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="description",
                    type=VariableType.STRING,
                    description="Descripción del gateway",
                    default="API Gateway para microservicios",
                    required=False
                ),
                TemplateVariable(
                    name="author",
                    type=VariableType.STRING,
                    description="Autor",
                    default="Developer",
                    required=False
                ),
                TemplateVariable(
                    name="version",
                    type=VariableType.STRING,
                    description="Versión inicial",
                    default="1.0.0",
                    required=False
                ),
                TemplateVariable(
                    name="service_port",
                    type=VariableType.INTEGER,
                    description="Puerto del gateway",
                    default=8000,
                    required=False
                )
            ]
        )
        
        files = [
            # Main application
            TemplateFile(
                path="main.py",
                content=APIGatewayTemplate._get_main_py_content(),
                is_binary=False
            ),
            
            # Configuration
            TemplateFile(
                path="config.py",
                content=APIGatewayTemplate._get_config_py_content(),
                is_binary=False
            ),
            
            # Gateway router
            TemplateFile(
                path="app/gateway.py",
                content=APIGatewayTemplate._get_gateway_py_content(),
                is_binary=False
            ),
            
            # Middleware
            TemplateFile(
                path="app/middleware.py",
                content=APIGatewayTemplate._get_middleware_py_content(),
                is_binary=False
            ),
            
            # Health check
            TemplateFile(
                path="app/health.py",
                content=APIGatewayTemplate._get_health_py_content(),
                is_binary=False
            ),
            
            # Requirements
            TemplateFile(
                path="requirements.txt",
                content=APIGatewayTemplate._get_requirements_content(),
                is_binary=False
            ),
            
            # Docker
            TemplateFile(
                path="Dockerfile",
                content=APIGatewayTemplate._get_dockerfile_content(),
                is_binary=False
            ),
            
            # Docker Compose
            TemplateFile(
                path="docker-compose.yml",
                content=APIGatewayTemplate._get_docker_compose_content(),
                is_binary=False
            ),
            
            # README
            TemplateFile(
                path="README.md",
                content=APIGatewayTemplate._get_readme_content(),
                is_binary=False
            ),
            
            # .gitignore
            TemplateFile(
                path=".gitignore",
                content=APIGatewayTemplate._get_gitignore_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)
    
    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - API Gateway

{{ description }}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.gateway import gateway_router
from app.health import health_router
from app.middleware import RateLimitMiddleware, LoggingMiddleware

# Create FastAPI app
app = FastAPI(
    title="{{ project_name }}",
    description="{{ description }}",
    version="{{ version }}",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)  # 100 calls per minute

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(gateway_router, prefix="/api", tags=["gateway"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "{{ project_name }} - API Gateway",
        "version": "{{ version }}",
        "status": "running",
        "services": settings.SERVICES,
        "endpoints": {
            "health": "/health/",
            "gateway": "/api/",
            "documentation": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
'''
    
    @staticmethod
    def _get_config_py_content() -> str:
        return '''"""
Configuration Settings for API Gateway
"""

from typing import List, Dict
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    PROJECT_NAME: str = "{{ project_name }}"
    VERSION: str = "{{ version }}"
    DESCRIPTION: str = "{{ description }}"
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default={{ service_port }}, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Microservices configuration
    SERVICES: Dict[str, str] = Field(
        default={
            "auth": "http://localhost:8001",
            "users": "http://localhost:8002", 
            "products": "http://localhost:8003",
            "orders": "http://localhost:8004"
        },
        env="SERVICES"
    )
    
    # Rate limiting
    RATE_LIMIT_CALLS: int = Field(default=100, env="RATE_LIMIT_CALLS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")
    
    # Timeout settings
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''
    
    @staticmethod
    def _get_gateway_py_content() -> str:
        return '''"""
Gateway routing and proxy functionality.
"""

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
from typing import Dict, Any
import logging

from config import settings

gateway_router = APIRouter()
logger = logging.getLogger(__name__)


class GatewayService:
    """Service for handling gateway operations."""
    
    @staticmethod
    async def proxy_request(service_name: str, path: str, request: Request) -> Response:
        """Proxy request to target microservice."""
        
        # Get service URL
        service_url = settings.SERVICES.get(service_name)
        if not service_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found"
            )
        
        # Build target URL
        target_url = f"{service_url}{path}"
        
        # Get request data
        method = request.method
        headers = dict(request.headers)
        
        # Remove host header to avoid conflicts
        headers.pop("host", None)
        
        try:
            # Get request body
            body = await request.body()
            
            # Make request to target service
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout calling service {service_name} at {target_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {service_name} timeout"
            )
        except httpx.ConnectError:
            logger.error(f"Connection error to service {service_name} at {target_url}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} unavailable"
            )
        except Exception as e:
            logger.error(f"Error proxying to {service_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal gateway error"
            )


@gateway_router.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_service(service_name: str, path: str, request: Request):
    """Proxy requests to microservices."""
    
    logger.info(f"Proxying {request.method} /{service_name}/{path}")
    
    # Add leading slash to path if not present
    if not path.startswith("/"):
        path = "/" + path
    
    return await GatewayService.proxy_request(service_name, path, request)


@gateway_router.get("/services")
async def list_services():
    """List available services."""
    
    services_status = {}
    
    async with httpx.AsyncClient(timeout=5) as client:
        for service_name, service_url in settings.SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health/")
                services_status[service_name] = {
                    "url": service_url,
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                services_status[service_name] = {
                    "url": service_url,
                    "status": "unavailable",
                    "error": str(e)
                }
    
    return {
        "gateway": "{{ project_name }}",
        "services": services_status,
        "total_services": len(settings.SERVICES)
    }


@gateway_router.get("/routes")
async def list_routes():
    """List available routes."""
    
    routes = []
    for service_name, service_url in settings.SERVICES.items():
        routes.append({
            "service": service_name,
            "pattern": f"/api/{service_name}/*",
            "target": service_url,
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"]
        })
    
    return {
        "gateway_routes": routes,
        "usage": "Use /api/{service_name}/{endpoint} to access services"
    }
'''
    
    @staticmethod
    def _get_middleware_py_content() -> str:
        return '''"""
Custom middleware for the API Gateway.
"""

import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Dict, DefaultDict

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: DefaultDict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        
        # Get client IP
        client_ip = request.client.host
        
        # Clean old entries
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        self.clients[client_ip] = [
            timestamp for timestamp in self.clients[client_ip]
            if timestamp > cutoff
        ]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {self.calls} calls per {self.period} seconds"
            )
        
        # Add current request
        self.clients[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(self.calls - len(self.clients[client_ip]))
        response.headers["X-RateLimit-Reset"] = str(int((now + timedelta(seconds=self.period)).timestamp()))
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with logging."""
        
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url} "
            f"from {request.client.host}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} "
            f"in {process_time:.4f}s"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with additional headers."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with CORS headers."""
        
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Gateway"] = "{{ project_name }}"
        
        return response
'''
    
    @staticmethod
    def _get_health_py_content() -> str:
        return '''"""
Health check endpoints for API Gateway.
"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

from config import settings

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str = "{{ version }}"
    gateway: str = "{{ project_name }}"
    services: Dict[str, Any] = {}


@health_router.get("/", response_model=HealthResponse)
async def health_check():
    """Gateway health check with services status."""
    
    services_health = {}
    
    # Check each service health
    async with httpx.AsyncClient(timeout=5) as client:
        for service_name, service_url in settings.SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health/")
                services_health[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": service_url,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                services_health[service_name] = {
                    "status": "unavailable",
                    "url": service_url,
                    "error": str(e)
                }
    
    # Determine overall status
    all_healthy = all(
        service["status"] == "healthy" 
        for service in services_health.values()
    )
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=time.time(),
        services=services_health
    )


@health_router.get("/ready")
async def readiness_check():
    """Gateway readiness check."""
    
    return {
        "ready": True,
        "timestamp": time.time(),
        "gateway": "{{ project_name }}",
        "services_configured": len(settings.SERVICES),
        "rate_limiting": True,
        "logging": True
    }


@health_router.get("/live")
async def liveness_check():
    """Gateway liveness check."""
    
    return {
        "status": "alive",
        "timestamp": time.time(),
        "gateway": "{{ project_name }}"
    }
'''
    
    @staticmethod
    def _get_requirements_content() -> str:
        return '''# Core dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# HTTP client for proxying
httpx>=0.25.0

# Development dependencies
pytest>=7.4.0
'''
    
    @staticmethod
    def _get_dockerfile_content() -> str:
        return '''FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE {{ service_port }}

# Run application
CMD ["python", "main.py"]
'''
    
    @staticmethod
    def _get_docker_compose_content() -> str:
        return '''version: '3.8'

services:
  api-gateway:
    build: .
    ports:
      - "{{ service_port }}:{{ service_port }}"
    environment:
      - ENVIRONMENT=development
      - PORT={{ service_port }}
      - SERVICES={"auth":"http://auth-service:8001","users":"http://user-service:8002"}
    depends_on:
      - auth-service
      - user-service
    restart: unless-stopped

  # Example services (uncomment and configure as needed)
  # auth-service:
  #   image: your-auth-service:latest
  #   ports:
  #     - "8001:8001"
  
  # user-service:
  #   image: your-user-service:latest
  #   ports:
  #     - "8002:8002"
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }}

{{ description }}

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
PORT={{ service_port }}
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
curl -X POST "http://localhost:{{ service_port }}/api/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin123"}'

# Get users (users service)  
curl -H "Authorization: Bearer <token>" \\
  "http://localhost:{{ service_port }}/api/users/"

# Get products (products service)
curl "http://localhost:{{ service_port }}/api/products/"
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
curl "http://localhost:{{ service_port }}/api/services"

# Health check
curl "http://localhost:{{ service_port }}/health/"

# Rutas disponibles
curl "http://localhost:{{ service_port }}/api/routes"
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
- `X-Gateway: {{ project_name }}`

### Manejo de Errores

- **Timeout**: 504 Gateway Timeout
- **Service unavailable**: 503 Service Unavailable
- **Service not found**: 404 Not Found
- **Rate limit**: 429 Too Many Requests

## Arquitectura

```
Client Request
     ↓
API Gateway ({{ service_port }})
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

- **Swagger UI**: http://localhost:{{ service_port }}/docs
- **ReDoc**: http://localhost:{{ service_port }}/redoc
- **Health Check**: http://localhost:{{ service_port }}/health/

## Licencia

MIT License
'''
    
    @staticmethod
    def _get_gitignore_content() -> str:
        return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Docker
.dockerignore
'''
"""
Auth Service Template

Servicio especializado en autenticación y autorización.
"""

from typing import Dict, Any
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class AuthServiceTemplate:
    """Template para servicio de autenticación."""
    
    @staticmethod
    def create_template() -> Template:
        """Crear template de auth service."""
        config = TemplateConfig(
            id="auth_service",
            name="Authentication Service",
            description="Servicio especializado en autenticación y autorización",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Nombre del servicio",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="description",
                    type=VariableType.STRING,
                    description="Descripción del servicio",
                    default="Servicio de autenticación",
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
                    description="Puerto del servicio",
                    default=8001,
                    required=False
                )
            ]
        )
        
        files = [
            # Main application
            TemplateFile(
                path="main.py",
                content=AuthServiceTemplate._get_main_py_content(),
                is_binary=False
            ),
            
            # Configuration
            TemplateFile(
                path="config.py",
                content=AuthServiceTemplate._get_config_py_content(),
                is_binary=False
            ),
            
            # App package init
            TemplateFile(
                path="app/__init__.py",
                content='"""\\n{{ project_name }} App Package\\n"""',
                is_binary=False
            ),
            
            # Auth module
            TemplateFile(
                path="app/auth.py",
                content=AuthServiceTemplate._get_auth_py_content(),
                is_binary=False
            ),
            
            # User models
            TemplateFile(
                path="app/models.py",
                content=AuthServiceTemplate._get_models_py_content(),
                is_binary=False
            ),
            
            # Schemas
            TemplateFile(
                path="app/schemas.py",
                content=AuthServiceTemplate._get_schemas_py_content(),
                is_binary=False
            ),
            
            # Health check
            TemplateFile(
                path="app/health.py",
                content=AuthServiceTemplate._get_health_py_content(),
                is_binary=False
            ),
            
            # Requirements
            TemplateFile(
                path="requirements.txt",
                content=AuthServiceTemplate._get_requirements_content(),
                is_binary=False
            ),
            
            # Docker
            TemplateFile(
                path="Dockerfile",
                content=AuthServiceTemplate._get_dockerfile_content(),
                is_binary=False
            ),
            
            # Docker Compose
            TemplateFile(
                path="docker-compose.yml",
                content=AuthServiceTemplate._get_docker_compose_content(),
                is_binary=False
            ),
            
            # README
            TemplateFile(
                path="README.md",
                content=AuthServiceTemplate._get_readme_content(),
                is_binary=False
            ),
            
            # .gitignore
            TemplateFile(
                path=".gitignore",
                content=AuthServiceTemplate._get_gitignore_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)
    
    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - Authentication Service

{{ description }}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.auth import auth_router
from app.health import health_router

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

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "{{ project_name }} Authentication Service",
        "version": "{{ version }}",
        "status": "running",
        "endpoints": {
            "health": "/health/",
            "authentication": "/auth/",
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
Configuration Settings for Authentication Service
"""

from typing import List
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
    
    # JWT settings
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # Database settings (for user storage)
    DATABASE_URL: str = Field(
        default="sqlite:///./auth.db",
        env="DATABASE_URL"
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''
    
    @staticmethod
    def _get_auth_py_content() -> str:
        return '''"""
Authentication endpoints and JWT handling.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from passlib.context import CryptContext

from config import settings
from .schemas import LoginRequest, LoginResponse, TokenInfo, UserCreate, UserResponse
from .models import MOCK_USERS

auth_router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint."""
    # Find user (in real app, query database)
    user = None
    for u in MOCK_USERS:
        if u["username"] == request.username:
            user = u
            break
    
    if not user or not AuthService.verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create tokens
    access_token = AuthService.create_access_token(
        data={"sub": user["username"], "user_id": user["id"], "role": user["role"]}
    )
    refresh_token = AuthService.create_refresh_token(
        data={"sub": user["username"], "user_id": user["id"]}
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(**user)
    )


@auth_router.post("/refresh", response_model=LoginResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh access token."""
    payload = AuthService.verify_token(credentials.credentials)
    
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    username = payload.get("sub")
    user_id = payload.get("user_id")
    
    # Find user
    user = None
    for u in MOCK_USERS:
        if u["username"] == username:
            user = u
            break
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new tokens
    access_token = AuthService.create_access_token(
        data={"sub": username, "user_id": user_id, "role": user["role"]}
    )
    refresh_token = AuthService.create_refresh_token(
        data={"sub": username, "user_id": user_id}
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(**user)
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info."""
    payload = AuthService.verify_token(credentials.credentials)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    username = payload.get("sub")
    
    # Find user
    user = None
    for u in MOCK_USERS:
        if u["username"] == username:
            user = u
            break
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)


@auth_router.post("/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate token (for other services)."""
    payload = AuthService.verify_token(credentials.credentials)
    
    return {
        "valid": True,
        "user_id": payload.get("user_id"),
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "expires_at": payload.get("exp")
    }


@auth_router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout endpoint."""
    # In a real implementation, you'd add the token to a blacklist
    return {"message": "Successfully logged out"}


# Dependency for other services to validate tokens
async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""
    payload = AuthService.verify_token(credentials.credentials)
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("sub"),
        "role": payload.get("role")
    }
'''
    
    @staticmethod
    def _get_models_py_content() -> str:
        return '''"""
User models and mock data.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mock users for demonstration
MOCK_USERS = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Administrator",
        "role": "admin",
        "is_active": True,
        "password_hash": pwd_context.hash("admin123")  # password: admin123
    },
    {
        "id": 2,
        "username": "user",
        "email": "user@example.com", 
        "full_name": "Regular User",
        "role": "user",
        "is_active": True,
        "password_hash": pwd_context.hash("user123")  # password: user123
    },
    {
        "id": 3,
        "username": "manager",
        "email": "manager@example.com",
        "full_name": "Manager User", 
        "role": "manager",
        "is_active": True,
        "password_hash": pwd_context.hash("manager123")  # password: manager123
    }
]
'''
    
    @staticmethod
    def _get_schemas_py_content() -> str:
        return '''"""
Pydantic schemas for authentication.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response schema (without password)."""
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenInfo(BaseModel):
    """Token information schema."""
    valid: bool
    user_id: int
    username: str
    role: str
    expires_at: int


class UserCreate(BaseModel):
    """User creation schema."""
    username: str
    email: EmailStr
    full_name: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
'''
    
    @staticmethod
    def _get_health_py_content() -> str:
        return '''"""
Health check endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str = "{{ version }}"
    service: str = "{{ project_name }}"
    checks: Dict[str, Any] = {}


@health_router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        checks={
            "auth_service": "running",
            "jwt": "configured",
            "users": "available"
        }
    )


@health_router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "ready": True,
        "timestamp": time.time(),
        "service": "{{ project_name }}",
        "components": {
            "jwt_service": True,
            "user_store": True,
            "password_hashing": True
        }
    }


@health_router.get("/live")
async def liveness_check():
    """Liveness check endpoint."""
    return {
        "status": "alive",
        "timestamp": time.time(),
        "service": "{{ project_name }}"
    }
'''
    
    @staticmethod
    def _get_requirements_content() -> str:
        return '''# Core dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# Development dependencies
pytest>=7.4.0
httpx>=0.25.0
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
  auth-service:
    build: .
    ports:
      - "{{ service_port }}:{{ service_port }}"
    environment:
      - ENVIRONMENT=development
      - PORT={{ service_port }}
      - SECRET_KEY=dev-secret-key-change-in-production
    volumes:
      - .:/app
    restart: unless-stopped
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }}

{{ description }}

## Características

- 🔐 **Autenticación JWT** con access y refresh tokens
- 👥 **Gestión de usuarios** con roles
- 🔒 **Hash de contraseñas** seguro con bcrypt
- 📚 **Documentación automática** con Swagger/OpenAPI
- 🐳 **Docker** ready
- ✅ **Health checks** integrados

## Inicio Rápido

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar servicio
python main.py
```

### Docker

```bash
# Build y ejecutar
docker-compose up --build

# Solo ejecutar
docker-compose up -d
```

## Uso

### Endpoints Principales

- `POST /auth/login` - Login con usuario/contraseña
- `POST /auth/refresh` - Renovar access token
- `GET /auth/me` - Información del usuario actual
- `POST /auth/validate` - Validar token (para otros servicios)
- `POST /auth/logout` - Logout

### Usuarios de Prueba

| Usuario | Contraseña | Rol |
|---------|------------|-----|
| admin | admin123 | admin |
| user | user123 | user |
| manager | manager123 | manager |

### Ejemplo de Login

```bash
curl -X POST "http://localhost:{{ service_port }}/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "admin", "password": "admin123"}'
```

### Usar Token

```bash
curl -H "Authorization: Bearer <tu-token>" \\
  "http://localhost:{{ service_port }}/auth/me"
```

## Documentación

- **Swagger UI**: http://localhost:{{ service_port }}/docs
- **ReDoc**: http://localhost:{{ service_port }}/redoc
- **Health Check**: http://localhost:{{ service_port }}/health/

## Configuración

Variables de entorno principales:

```env
PORT={{ service_port }}
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
```

## Integración con Otros Servicios

Este servicio puede ser usado por otros microservicios para validar tokens:

```python
# En otro servicio
import httpx

async def validate_token(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://auth-service:{{ service_port }}/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

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

# Database
*.db
*.sqlite
*.sqlite3

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
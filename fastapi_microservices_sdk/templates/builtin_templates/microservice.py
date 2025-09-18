"""
Microservice Template

Basic microservice template with FastAPI, database, and observability.
"""

from typing import Dict, Any
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class MicroserviceTemplate:
    """Basic microservice template."""
    
    @staticmethod
    def create_template() -> Template:
        """Create microservice template."""
        config = TemplateConfig(
            id="microservice",
            name="Basic Microservice",
            description="A basic FastAPI microservice with database and observability",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Project name",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="description",
                    type=VariableType.STRING,
                    description="Project description",
                    default="A FastAPI microservice",
                    required=False
                ),
                TemplateVariable(
                    name="author",
                    type=VariableType.STRING,
                    description="Author name",
                    default="",
                    required=False
                ),
                TemplateVariable(
                    name="version",
                    type=VariableType.STRING,
                    description="Initial version",
                    default="0.1.0",
                    required=False
                ),
                TemplateVariable(
                    name="python_version",
                    type=VariableType.STRING,
                    description="Python version",
                    default="3.8+",
                    choices=["3.8+", "3.9+", "3.10+", "3.11+", "3.12+"],
                    required=False
                ),
                TemplateVariable(
                    name="database",
                    type=VariableType.STRING,
                    description="Database type",
                    default="postgresql",
                    choices=["postgresql", "mysql", "mongodb", "sqlite", "none"],
                    required=False
                ),
                TemplateVariable(
                    name="use_redis",
                    type=VariableType.BOOLEAN,
                    description="Use Redis for caching",
                    default=True,
                    required=False
                ),
                TemplateVariable(
                    name="enable_observability",
                    type=VariableType.BOOLEAN,
                    description="Enable observability features",
                    default=True,
                    required=False
                ),
                TemplateVariable(
                    name="enable_security",
                    type=VariableType.BOOLEAN,
                    description="Enable security features",
                    default=True,
                    required=False
                )
            ]
        )
        
        files = [
            # Main application
            TemplateFile(
                path="main.py",
                content=MicroserviceTemplate._get_main_py_content(),
                is_binary=False
            ),
            
            # Configuration
            TemplateFile(
                path="config.py",
                content=MicroserviceTemplate._get_config_py_content(),
                is_binary=False
            ),
            
            # Requirements
            TemplateFile(
                path="requirements.txt",
                content=MicroserviceTemplate._get_requirements_content(),
                is_binary=False
            ),
            
            # pyproject.toml
            TemplateFile(
                path="pyproject.toml",
                content=MicroserviceTemplate._get_pyproject_content(),
                is_binary=False
            ),
            
            # README
            TemplateFile(
                path="README.md",
                content=MicroserviceTemplate._get_readme_content(),
                is_binary=False
            ),
            
            # Docker
            TemplateFile(
                path="Dockerfile",
                content=MicroserviceTemplate._get_dockerfile_content(),
                is_binary=False
            ),
            
            # Docker Compose
            TemplateFile(
                path="docker-compose.yml",
                content=MicroserviceTemplate._get_docker_compose_content(),
                is_binary=False
            ),
            
            # .gitignore
            TemplateFile(
                path=".gitignore",
                content=MicroserviceTemplate._get_gitignore_content(),
                is_binary=False
            ),
            
            # Health check
            TemplateFile(
                path="app/health.py",
                content=MicroserviceTemplate._get_health_py_content(),
                is_binary=False
            ),
            
            # Models
            TemplateFile(
                path="app/models/__init__.py",
                content="# Models module",
                is_binary=False
            ),
            
            # API
            TemplateFile(
                path="app/api/__init__.py",
                content="# API module",
                is_binary=False
            ),
            
            # Services
            TemplateFile(
                path="app/services/__init__.py",
                content="# Services module",
                is_binary=False
            ),
            
            # Tests
            TemplateFile(
                path="tests/__init__.py",
                content="# Tests module",
                is_binary=False
            ),
            
            TemplateFile(
                path="tests/test_main.py",
                content=MicroserviceTemplate._get_test_main_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)
    
    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - Main Application

{{ description }}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
{% if enable_observability %}
from fastapi_microservices_sdk.observability import ObservabilityManager
{% endif %}
{% if enable_security %}
from fastapi_microservices_sdk.security import SecurityManager
{% endif %}
{% if database != "none" %}
from fastapi_microservices_sdk.database import DatabaseManager
{% endif %}

from .config import settings
from .health import health_router

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

{% if enable_observability %}
# Initialize observability
observability = ObservabilityManager()
observability.setup_fastapi(app)
{% endif %}

{% if enable_security %}
# Initialize security
security = SecurityManager()
security.setup_fastapi(app)
{% endif %}

{% if database != "none" %}
# Initialize database
database = DatabaseManager()

@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    await database.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    await database.disconnect()
{% endif %}

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to {{ project_name }}!",
        "version": "{{ version }}",
        "status": "running"
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
Configuration Settings

Application configuration using Pydantic settings.
"""

from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    PROJECT_NAME: str = "{{ project_name }}"
    VERSION: str = "{{ version }}"
    DESCRIPTION: str = "{{ description }}"
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    {% if database != "none" %}
    # Database settings
    DATABASE_URL: str = Field(
        default="{% if database == 'postgresql' %}postgresql://user:password@localhost/{{ project_name }}{% elif database == 'mysql' %}mysql://user:password@localhost/{{ project_name }}{% elif database == 'mongodb' %}mongodb://localhost:27017/{{ project_name }}{% elif database == 'sqlite' %}sqlite:///./{{ project_name }}.db{% endif %}",
        env="DATABASE_URL"
    )
    {% endif %}
    
    {% if use_redis %}
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    {% endif %}
    
    # Security settings
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''
    
    @staticmethod
    def _get_requirements_content() -> str:
        return '''# Core dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0

# FastAPI Microservices SDK
fastapi-microservices-sdk

{% if database == "postgresql" %}
# PostgreSQL
asyncpg>=0.29.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.12.0
{% elif database == "mysql" %}
# MySQL
aiomysql>=0.2.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.12.0
{% elif database == "mongodb" %}
# MongoDB
motor>=3.3.0
beanie>=1.23.0
{% elif database == "sqlite" %}
# SQLite
aiosqlite>=0.19.0
sqlalchemy[asyncio]>=2.0.0
alembic>=1.12.0
{% endif %}

{% if use_redis %}
# Redis
redis>=5.0.0
aioredis>=2.0.0
{% endif %}

# Development dependencies (install with: pip install -e ".[dev]")
# pytest>=7.4.0
# pytest-asyncio>=0.21.0
# httpx>=0.25.0
# black>=23.0.0
# isort>=5.12.0
# flake8>=6.0.0
# mypy>=1.6.0
'''
    
    @staticmethod
    def _get_pyproject_content() -> str:
        return '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{{ project_name }}"
version = "{{ version }}"
description = "{{ description }}"
authors = [
    {name = "{{ author }}", email = "author@example.com"}
]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">={{ python_version.replace('+', '') }}"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Framework :: FastAPI",
]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "fastapi-microservices-sdk",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.6.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/{{ project_name }}"
Repository = "https://github.com/yourusername/{{ project_name }}.git"
Issues = "https://github.com/yourusername/{{ project_name }}/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]

[tool.black]
line-length = 88
target-version = ['py38']
include = '\\.pyi?$'

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }}

{{ description }}

## Features

- ⚡ **FastAPI**: Modern, fast web framework for building APIs
{% if database != "none" %}
- 🗄️ **Database**: {{ database.title() }} integration with async support
{% endif %}
{% if use_redis %}
- 🔄 **Redis**: Caching and session management
{% endif %}
{% if enable_observability %}
- 📊 **Observability**: Comprehensive monitoring and logging
{% endif %}
{% if enable_security %}
- 🔒 **Security**: Built-in authentication and authorization
{% endif %}
- 🐳 **Docker**: Containerized deployment
- 🧪 **Testing**: Comprehensive test suite
- 📚 **Documentation**: Auto-generated API documentation

## Quick Start

### Prerequisites

- Python {{ python_version }}
- Docker (optional)
{% if database == "postgresql" %}
- PostgreSQL
{% elif database == "mysql" %}
- MySQL
{% elif database == "mongodb" %}
- MongoDB
{% endif %}
{% if use_redis %}
- Redis
{% endif %}

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd {{ project_name }}
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

{% if database != "none" %}
5. Set up the database:
```bash
# Create database and run migrations
alembic upgrade head
```
{% endif %}

6. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

- API Documentation: `http://localhost:8000/docs`
- Alternative Documentation: `http://localhost:8000/redoc`

### Docker Deployment

1. Build the image:
```bash
docker-compose build
```

2. Run the services:
```bash
docker-compose up -d
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - API documentation (ReDoc)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Type Checking

```bash
mypy .
```

## Configuration

The application uses environment variables for configuration. See `.env.example` for available options.

Key configuration options:

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `ENVIRONMENT`: Environment (development/production)
{% if database != "none" %}
- `DATABASE_URL`: Database connection URL
{% endif %}
{% if use_redis %}
- `REDIS_URL`: Redis connection URL
{% endif %}
- `SECRET_KEY`: Secret key for security features

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## Support

For support and questions, please open an issue in the repository.
'''
    
    @staticmethod
    def _get_dockerfile_content() -> str:
        return '''FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        gcc \\
        && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]
'''
    
    @staticmethod
    def _get_docker_compose_content() -> str:
        return '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      {% if database != "none" %}
      - DATABASE_URL={{ "postgresql://postgres:password@db:5432/" + project_name if database == "postgresql" else "mysql://root:password@db:3306/" + project_name if database == "mysql" else "mongodb://db:27017/" + project_name if database == "mongodb" else "sqlite:///./data/" + project_name + ".db" }}
      {% endif %}
      {% if use_redis %}
      - REDIS_URL=redis://redis:6379
      {% endif %}
    volumes:
      - .:/app
    depends_on:
      {% if database == "postgresql" %}
      - db
      {% elif database == "mysql" %}
      - db
      {% elif database == "mongodb" %}
      - db
      {% endif %}
      {% if use_redis %}
      - redis
      {% endif %}

  {% if database == "postgresql" %}
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB={{ project_name }}
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  {% elif database == "mysql" %}
  db:
    image: mysql:8.0
    environment:
      - MYSQL_DATABASE={{ project_name }}
      - MYSQL_ROOT_PASSWORD=password
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
  {% elif database == "mongodb" %}
  db:
    image: mongo:7
    environment:
      - MONGO_INITDB_DATABASE={{ project_name }}
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
  {% endif %}

  {% if use_redis %}
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  {% endif %}

volumes:
  {% if database == "postgresql" %}
  postgres_data:
  {% elif database == "mysql" %}
  mysql_data:
  {% elif database == "mongodb" %}
  mongo_data:
  {% endif %}
  {% if use_redis %}
  redis_data:
  {% endif %}
'''
    
    @staticmethod
    def _get_gitignore_content() -> str:
        return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
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
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# poetry
poetry.lock

# pdm
.pdm.toml

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
.idea/

# VS Code
.vscode/

# Database files
*.db
*.sqlite
*.sqlite3

# Log files
*.log

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
data/
uploads/
.fastapi-sdk/
'''
    
    @staticmethod
    def _get_health_py_content() -> str:
        return '''"""
Health Check Endpoints

Health check and readiness endpoints for the application.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time
{% if database != "none" %}
from ..database import get_database_health
{% endif %}
{% if use_redis %}
from ..cache import get_redis_health
{% endif %}

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str = "{{ version }}"
    checks: Dict[str, Any] = {}


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    timestamp: float
    services: Dict[str, bool] = {}


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns the current status of the application.
    """
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        checks={
            "application": "running",
            "memory": "ok",
            "disk": "ok"
        }
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks if the application is ready to serve requests.
    """
    services = {}
    ready = True
    
    {% if database != "none" %}
    # Check database connectivity
    try:
        db_healthy = await get_database_health()
        services["database"] = db_healthy
        if not db_healthy:
            ready = False
    except Exception:
        services["database"] = False
        ready = False
    {% endif %}
    
    {% if use_redis %}
    # Check Redis connectivity
    try:
        redis_healthy = await get_redis_health()
        services["redis"] = redis_healthy
        if not redis_healthy:
            ready = False
    except Exception:
        services["redis"] = False
        ready = False
    {% endif %}
    
    return ReadinessResponse(
        ready=ready,
        timestamp=time.time(),
        services=services
    )


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Simple endpoint to check if the application is alive.
    """
    return {"status": "alive", "timestamp": time.time()}


{% if database != "none" %}
async def get_database_health() -> bool:
    """Check database health."""
    try:
        # Add your database health check logic here
        # For example, execute a simple query
        return True
    except Exception:
        return False
{% endif %}


{% if use_redis %}
async def get_redis_health() -> bool:
    """Check Redis health."""
    try:
        # Add your Redis health check logic here
        # For example, ping Redis
        return True
    except Exception:
        return False
{% endif %}
'''
    
    @staticmethod
    def _get_test_main_content() -> str:
        return '''"""
Main Application Tests

Tests for the main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to {{ project_name }}!"
    assert data["version"] == "{{ version }}"
    assert data["status"] == "running"


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "checks" in data


def test_readiness_check():
    """Test readiness check endpoint."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "ready" in data
    assert "timestamp" in data
    assert "services" in data


def test_liveness_check():
    """Test liveness check endpoint."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_docs_endpoint():
    """Test API documentation endpoint."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    """Test OpenAPI schema endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "{{ project_name }}"
    assert schema["info"]["version"] == "{{ version }}"
'''
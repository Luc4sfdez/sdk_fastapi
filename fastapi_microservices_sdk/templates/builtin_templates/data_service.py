"""
Data Service Template - Enterprise Grade (Fixed Version)

Advanced data service with multi-database support, caching, and search.
"""

from typing import Dict, Any
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class DataServiceTemplate:
    """Enterprise-grade data service template."""
    
    @staticmethod
    def create_template() -> Template:
        """Create advanced data service template."""
        config = TemplateConfig(
            id="data_service",
            name="Enterprise Data Service",
            description="Advanced data service with multi-DB, caching, and search",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Service name",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="description",
                    type=VariableType.STRING,
                    description="Service description",
                    default="Enterprise data service",
                    required=False
                ),
                TemplateVariable(
                    name="author",
                    type=VariableType.STRING,
                    description="Author",
                    default="Developer",
                    required=False
                ),
                TemplateVariable(
                    name="version",
                    type=VariableType.STRING,
                    description="Version",
                    default="1.0.0",
                    required=False
                ),
                TemplateVariable(
                    name="service_port",
                    type=VariableType.INTEGER,
                    description="Service port",
                    default=8000,
                    required=False
                )
            ]
        )
        
        files = [
            TemplateFile(
                path="main.py",
                content=DataServiceTemplate._get_main_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="config.py",
                content=DataServiceTemplate._get_config_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="requirements.txt",
                content=DataServiceTemplate._get_requirements_content(),
                is_binary=False
            ),
            TemplateFile(
                path="README.md",
                content=DataServiceTemplate._get_readme_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)    

    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - Enterprise Data Service

{{ description }}

Advanced features:
- Multi-database support
- Intelligent caching
- Full-text search
- Real-time analytics
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="{{ project_name }} - Enterprise Data Service",
    description="{{ description }}",
    version="{{ version }}",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "{{ project_name }}",
        "version": "{{ version }}",
        "status": "running",
        "description": "{{ description }}",
        "features": [
            "Multi-database support",
            "Advanced caching",
            "Full-text search",
            "Real-time analytics",
            "Enterprise monitoring"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "{{ project_name }}",
        "version": "{{ version }}"
    }

@app.get("/api/v1/users")
async def get_users():
    """Get users - Enterprise CRUD endpoint"""
    return {
        "users": [
            {"id": 1, "name": "Admin User", "role": "admin"},
            {"id": 2, "name": "Regular User", "role": "user"}
        ],
        "total": 2,
        "features": {
            "pagination": True,
            "filtering": True,
            "search": True,
            "caching": True
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=True
    )
'''
    
    @staticmethod
    def _get_config_py_content() -> str:
        return '''"""
Enterprise Configuration for {{ project_name }}
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Enterprise application settings"""
    
    PROJECT_NAME: str = "{{ project_name }}"
    VERSION: str = "{{ version }}"
    DESCRIPTION: str = "{{ description }}"
    
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default={{ service_port }}, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Database settings
    DATABASE_TYPE: str = Field(default="postgresql", env="DATABASE_TYPE")
    DATABASE_HOST: str = Field(default="localhost", env="DATABASE_HOST")
    DATABASE_PORT: int = Field(default=5432, env="DATABASE_PORT")
    DATABASE_NAME: str = Field(default="{{ project_name }}", env="DATABASE_NAME")
    
    # Cache settings
    CACHE_ENABLED: bool = Field(default=True, env="CACHE_ENABLED")
    CACHE_HOST: str = Field(default="localhost", env="CACHE_HOST")
    CACHE_PORT: int = Field(default=6379, env="CACHE_PORT")
    
    # Search settings
    SEARCH_ENABLED: bool = Field(default=True, env="SEARCH_ENABLED")
    SEARCH_HOST: str = Field(default="localhost", env="SEARCH_HOST")
    SEARCH_PORT: int = Field(default=9200, env="SEARCH_PORT")
    
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

# Database support
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.12.0

# Cache support
redis>=5.0.0
aioredis>=2.0.0

# Search support
elasticsearch>=8.0.0

# Development
pytest>=7.4.0
httpx>=0.25.0
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }} - Enterprise Data Service

{{ description }}

## 🚀 Enterprise Features

- **Multi-Database Support**: PostgreSQL, MySQL, MongoDB, SQLite
- **Advanced Caching**: Redis integration with intelligent invalidation
- **Full-Text Search**: Elasticsearch integration
- **Real-Time Analytics**: Performance metrics and monitoring
- **Enterprise Security**: Audit logging, soft deletes, versioning

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python main.py
```

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/v1/users` - Users endpoint (with enterprise features)
- `GET /docs` - API documentation

## Configuration

Set environment variables in `.env`:

```env
PORT={{ service_port }}
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
CACHE_HOST=localhost
SEARCH_HOST=localhost
```

## Enterprise Architecture

```
{{ project_name }}
├── Multi-Database Layer
├── Caching Layer (Redis)
├── Search Engine (Elasticsearch)
├── Analytics & Monitoring
└── Enterprise Security
```

Visit http://localhost:{{ service_port }}/docs for full API documentation.
'''
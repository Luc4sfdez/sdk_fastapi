"""
Docker Generator for FastAPI microservices.

This module provides Docker configuration generation including Dockerfiles,
docker-compose files, and container orchestration for FastAPI microservices.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
from dataclasses import dataclass, field

from ..config import TemplateConfig, TemplateVariable, VariableType
from ..exceptions import TemplateError


class BaseTemplate:
    """Base template class."""
    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        raise NotImplementedError
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate files from template."""
        raise NotImplementedError


@dataclass
class DockerService:
    """Docker service configuration."""
    name: str
    image: Optional[str] = None
    build: Optional[str] = None
    ports: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    networks: List[str] = field(default_factory=list)
    restart: str = "unless-stopped"
    healthcheck: Optional[Dict[str, Any]] = None


class DockerGenerator:
    """Generator for Docker configurations."""
    
    def __init__(self):
        self.supported_python_versions = ["3.8", "3.9", "3.10", "3.11", "3.12"]
        self.supported_base_images = ["python", "python-slim", "alpine"]
    
    def generate_dockerfile(self, python_version: str = "3.11", 
                          base_image: str = "python-slim",
                          app_name: str = "fastapi-app",
                          requirements_file: str = "requirements.txt") -> str:
        """Generate Dockerfile for FastAPI application."""
        
        if python_version not in self.supported_python_versions:
            raise TemplateError(f"Unsupported Python version: {python_version}")
        
        if base_image not in self.supported_base_images:
            raise TemplateError(f"Unsupported base image: {base_image}")
        
        if base_image == "python":
            base_image_name = f"python:{python_version}"
        elif base_image == "python-slim":
            base_image_name = f"python:{python_version}-slim"
        elif base_image == "alpine":
            base_image_name = f"python:{python_version}-alpine"
        else:
            base_image_name = f"python:{python_version}-{base_image}"
        
        dockerfile_content = f'''# FastAPI Microservice Dockerfile
FROM {base_image_name}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app \\
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
{self._get_system_dependencies(base_image)}

# Copy requirements and install Python dependencies
COPY {requirements_file} .
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r {requirements_file}

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' --shell /bin/bash appuser && \\
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        
        return dockerfile_content
    
    def generate_docker_compose(self, services: List[DockerService], 
                               networks: Optional[List[str]] = None,
                               volumes: Optional[List[str]] = None) -> str:
        """Generate docker-compose.yml file."""
        
        compose_content = '''version: '3.8'

services:
'''
        
        # Generate services
        for service in services:
            compose_content += self._generate_compose_service(service)
        
        # Generate networks
        if networks:
            compose_content += '\nnetworks:\n'
            for network in networks:
                compose_content += f'  {network}:\n    driver: bridge\n'
        
        # Generate volumes
        if volumes:
            compose_content += '\nvolumes:\n'
            for volume in volumes:
                compose_content += f'  {volume}:\n'
        
        return compose_content
    
    def generate_development_compose(self, app_name: str = "fastapi-app",
                                   database_type: str = "postgresql") -> str:
        """Generate development docker-compose.yml."""
        
        services = [
            DockerService(
                name=app_name,
                build=".",
                ports=["8000:8000"],
                environment={
                    "DATABASE_URL": self._get_database_url(database_type),
                    "ENVIRONMENT": "development",
                    "DEBUG": "true"
                },
                volumes=[
                    ".:/app",
                    "/app/__pycache__"
                ],
                depends_on=[database_type] if database_type != "sqlite" else [],
                networks=["app-network"]
            )
        ]
        
        # Add database service
        if database_type != "sqlite":
            db_service = self._get_database_service(database_type)
            services.append(db_service)
        
        # Add Redis for caching
        redis_service = DockerService(
            name="redis",
            image="redis:7-alpine",
            ports=["6379:6379"],
            networks=["app-network"],
            healthcheck={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5
            }
        )
        services.append(redis_service)
        
        return self.generate_docker_compose(
            services, 
            networks=["app-network"],
            volumes=["postgres_data"] if database_type == "postgresql" else None
        )
    
    def generate_production_compose(self, app_name: str = "fastapi-app",
                                  database_type: str = "postgresql",
                                  replicas: int = 3) -> str:
        """Generate production docker-compose.yml."""
        
        services = []
        
        # Nginx reverse proxy
        nginx_service = DockerService(
            name="nginx",
            image="nginx:alpine",
            ports=["80:80", "443:443"],
            volumes=[
                "./nginx.conf:/etc/nginx/nginx.conf:ro",
                "./ssl:/etc/nginx/ssl:ro"
            ],
            depends_on=[app_name],
            networks=["app-network"],
            restart="always"
        )
        services.append(nginx_service)
        
        # FastAPI application
        app_service = DockerService(
            name=app_name,
            build=".",
            environment={
                "DATABASE_URL": self._get_database_url(database_type, production=True),
                "ENVIRONMENT": "production",
                "DEBUG": "false"
            },
            depends_on=[database_type] if database_type != "sqlite" else [],
            networks=["app-network"],
            restart="always",
            healthcheck={
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3
            }
        )
        services.append(app_service)
        
        # Database service
        if database_type != "sqlite":
            db_service = self._get_database_service(database_type, production=True)
            services.append(db_service)
        
        # Redis for caching and sessions
        redis_service = DockerService(
            name="redis",
            image="redis:7-alpine",
            volumes=["redis_data:/data"],
            networks=["app-network"],
            restart="always",
            healthcheck={
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5
            }
        )
        services.append(redis_service)
        
        volumes = ["redis_data"]
        if database_type == "postgresql":
            volumes.append("postgres_data")
        elif database_type == "mysql":
            volumes.append("mysql_data")
        
        return self.generate_docker_compose(
            services,
            networks=["app-network"],
            volumes=volumes
        )
    
    def generate_dockerignore(self) -> str:
        """Generate .dockerignore file."""
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
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/_build/

# Docker
Dockerfile*
docker-compose*.yml
.dockerignore

# Git
.git/
.gitignore

# CI/CD
.github/
.gitlab-ci.yml

# Local development
.env.local
.env.development
.env.test

# Temporary files
*.tmp
*.temp
'''
    
    def generate_nginx_config(self, app_name: str = "fastapi-app",
                            upstream_servers: List[str] = None) -> str:
        """Generate Nginx configuration for production."""
        
        if not upstream_servers:
            upstream_servers = [f"{app_name}:8000"]
        
        upstream_block = "upstream fastapi_backend {\n"
        for server in upstream_servers:
            upstream_block += f"    server {server};\n"
        upstream_block += "}\n\n"
        
        return f'''{upstream_block}server {{
    listen 80;
    server_name localhost;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {{
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }}
    
    location /health {{
        proxy_pass http://fastapi_backend/health;
        access_log off;
    }}
    
    location /static/ {{
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}
'''
    
    def generate_docker_files(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Generate all Docker-related files."""
        files = {}
        
        app_name = config.get("app_name", "fastapi-app")
        python_version = config.get("python_version", "3.11")
        base_image = config.get("base_image", "python-slim")
        database_type = config.get("database_type", "postgresql")
        environment = config.get("environment", "development")
        
        # Generate Dockerfile
        files["Dockerfile"] = self.generate_dockerfile(
            python_version=python_version,
            base_image=base_image,
            app_name=app_name
        )
        
        # Generate .dockerignore
        files[".dockerignore"] = self.generate_dockerignore()
        
        # Generate docker-compose files
        if environment == "development":
            files["docker-compose.yml"] = self.generate_development_compose(
                app_name=app_name,
                database_type=database_type
            )
        else:
            files["docker-compose.yml"] = self.generate_production_compose(
                app_name=app_name,
                database_type=database_type
            )
            files["docker-compose.dev.yml"] = self.generate_development_compose(
                app_name=app_name,
                database_type=database_type
            )
        
        # Generate Nginx config for production
        if environment == "production":
            files["nginx.conf"] = self.generate_nginx_config(app_name=app_name)
        
        # Generate Docker scripts
        files.update(self._generate_docker_scripts(app_name, environment))
        
        return files
    
    def _generate_compose_service(self, service: DockerService) -> str:
        """Generate docker-compose service configuration."""
        content = f"  {service.name}:\n"
        
        if service.image:
            content += f"    image: {service.image}\n"
        
        if service.build:
            content += f"    build: {service.build}\n"
        
        if service.ports:
            content += "    ports:\n"
            for port in service.ports:
                content += f"      - \"{port}\"\n"
        
        if service.environment:
            content += "    environment:\n"
            for key, value in service.environment.items():
                content += f"      {key}: {value}\n"
        
        if service.volumes:
            content += "    volumes:\n"
            for volume in service.volumes:
                content += f"      - {volume}\n"
        
        if service.depends_on:
            content += "    depends_on:\n"
            for dep in service.depends_on:
                content += f"      - {dep}\n"
        
        if service.networks:
            content += "    networks:\n"
            for network in service.networks:
                content += f"      - {network}\n"
        
        if service.restart:
            content += f"    restart: {service.restart}\n"
        
        if service.healthcheck:
            content += "    healthcheck:\n"
            for key, value in service.healthcheck.items():
                if isinstance(value, list):
                    content += f"      {key}: {json.dumps(value)}\n"
                else:
                    content += f"      {key}: {value}\n"
        
        content += "\n"
        return content
    
    def _get_database_service(self, database_type: str, production: bool = False) -> DockerService:
        """Get database service configuration."""
        
        if database_type == "postgresql":
            return DockerService(
                name="postgres",
                image="postgres:15-alpine",
                environment={
                    "POSTGRES_DB": "fastapi_db",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "postgres" if not production else "${POSTGRES_PASSWORD}"
                },
                volumes=["postgres_data:/var/lib/postgresql/data"],
                ports=["5432:5432"] if not production else [],
                networks=["app-network"],
                healthcheck={
                    "test": ["CMD-SHELL", "pg_isready -U postgres"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5
                }
            )
        
        elif database_type == "mysql":
            return DockerService(
                name="mysql",
                image="mysql:8.0",
                environment={
                    "MYSQL_DATABASE": "fastapi_db",
                    "MYSQL_USER": "mysql",
                    "MYSQL_PASSWORD": "mysql" if not production else "${MYSQL_PASSWORD}",
                    "MYSQL_ROOT_PASSWORD": "root" if not production else "${MYSQL_ROOT_PASSWORD}"
                },
                volumes=["mysql_data:/var/lib/mysql"],
                ports=["3306:3306"] if not production else [],
                networks=["app-network"],
                healthcheck={
                    "test": ["CMD", "mysqladmin", "ping", "-h", "localhost"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5
                }
            )
        
        elif database_type == "mongodb":
            return DockerService(
                name="mongodb",
                image="mongo:6.0",
                environment={
                    "MONGO_INITDB_DATABASE": "fastapi_db",
                    "MONGO_INITDB_ROOT_USERNAME": "mongo" if not production else "${MONGO_USERNAME}",
                    "MONGO_INITDB_ROOT_PASSWORD": "mongo" if not production else "${MONGO_PASSWORD}"
                },
                volumes=["mongodb_data:/data/db"],
                ports=["27017:27017"] if not production else [],
                networks=["app-network"],
                healthcheck={
                    "test": ["CMD", "mongo", "--eval", "db.adminCommand('ping')"],
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5
                }
            )
        
        raise TemplateError(f"Unsupported database type: {database_type}")
    
    def _get_database_url(self, database_type: str, production: bool = False) -> str:
        """Get database URL for environment."""
        
        if production:
            urls = {
                "postgresql": "${DATABASE_URL}",
                "mysql": "${DATABASE_URL}",
                "mongodb": "${DATABASE_URL}",
                "sqlite": "sqlite:///./app.db"
            }
        else:
            urls = {
                "postgresql": "postgresql://postgres:postgres@postgres:5432/fastapi_db",
                "mysql": "mysql://mysql:mysql@mysql:3306/fastapi_db",
                "mongodb": "mongodb://mongo:mongo@mongodb:27017/fastapi_db",
                "sqlite": "sqlite:///./app.db"
            }
        
        return urls.get(database_type, urls["sqlite"])
    
    def _get_system_dependencies(self, base_image: str) -> str:
        """Get system dependencies installation commands."""
        
        if base_image == "alpine":
            return '''RUN apk update && apk add --no-cache \\
    gcc \\
    musl-dev \\
    libffi-dev \\
    openssl-dev \\
    curl \\
    && rm -rf /var/cache/apk/*'''
        else:
            return '''RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    g++ \\
    libffi-dev \\
    libssl-dev \\
    curl \\
    && rm -rf /var/lib/apt/lists/*'''
    
    def _generate_docker_scripts(self, app_name: str, environment: str) -> Dict[str, str]:
        """Generate Docker utility scripts."""
        
        scripts = {}
        
        # Build script
        scripts["scripts/docker-build.sh"] = f'''#!/bin/bash
set -e

echo "Building {app_name} Docker image..."
docker build -t {app_name}:latest .

echo "Build completed successfully!"
'''
        
        # Run script
        scripts["scripts/docker-run.sh"] = f'''#!/bin/bash
set -e

echo "Starting {app_name} with Docker Compose..."
docker-compose up -d

echo "Application started successfully!"
echo "API available at: http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
'''
        
        # Stop script
        scripts["scripts/docker-stop.sh"] = f'''#!/bin/bash
set -e

echo "Stopping {app_name}..."
docker-compose down

echo "Application stopped successfully!"
'''
        
        # Logs script
        scripts["scripts/docker-logs.sh"] = f'''#!/bin/bash

if [ -z "$1" ]; then
    echo "Showing logs for all services..."
    docker-compose logs -f
else
    echo "Showing logs for service: $1"
    docker-compose logs -f "$1"
fi
'''
        
        # Clean script
        scripts["scripts/docker-clean.sh"] = f'''#!/bin/bash
set -e

echo "Cleaning up Docker resources..."

# Stop and remove containers
docker-compose down -v

# Remove images
docker rmi {app_name}:latest 2>/dev/null || true

# Remove unused volumes
docker volume prune -f

# Remove unused networks
docker network prune -f

echo "Cleanup completed!"
'''
        
        return scripts


class DockerTemplate(BaseTemplate):
    """Template for Docker configuration generation."""
    
    def __init__(self):
        super().__init__(
            name="docker",
            description="Docker configuration generator for FastAPI microservices",
            version="1.0.0"
        )
        self.generator = DockerGenerator()
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        return TemplateConfig(
            variables=[
                TemplateVariable(
                    name="app_name",
                    description="Application name",
                    type=VariableType.STRING,
                    default="fastapi-app"
                ),
                TemplateVariable(
                    name="python_version",
                    description="Python version",
                    type=VariableType.STRING,
                    choices=["3.8", "3.9", "3.10", "3.11", "3.12"],
                    default="3.11"
                ),
                TemplateVariable(
                    name="base_image",
                    description="Base Docker image",
                    type=VariableType.STRING,
                    choices=["python", "python-slim", "alpine"],
                    default="python-slim"
                ),
                TemplateVariable(
                    name="database_type",
                    description="Database type",
                    type=VariableType.STRING,
                    choices=["postgresql", "mysql", "mongodb", "sqlite"],
                    default="postgresql"
                ),
                TemplateVariable(
                    name="environment",
                    description="Target environment",
                    type=VariableType.STRING,
                    choices=["development", "production"],
                    default="development"
                )
            ]
        )
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate Docker configuration files."""
        return self.generator.generate_docker_files(context)
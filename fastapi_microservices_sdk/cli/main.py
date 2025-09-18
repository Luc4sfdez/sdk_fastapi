# fastapi-microservices-sdk/fastapi_microservices_sdk/cli/main.py 
"""
Command Line Interface for FastAPI Microservices SDK.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ..version import __version__, print_version_info
from ..config import SDKConfig
from ..utils.validators import validate_service_name
from ..utils.helpers import sanitize_service_name

# Import command modules
from .commands.create import create_app
from .commands.deploy import deploy_app
from .commands.generate import generate_app
from .commands.monitor import monitor_app
from .commands.init import init_app
from .commands.discover import discover_app

app = typer.Typer(
    name="fastapi-sdk",
    help="FastAPI Microservices SDK CLI",
    add_completion=False
)
console = Console()

# Add command groups
app.add_typer(create_app, name="create")
app.add_typer(deploy_app, name="deploy")
app.add_typer(generate_app, name="generate")
app.add_typer(monitor_app, name="monitor")
app.add_typer(init_app, name="init")
app.add_typer(discover_app, name="discover")


@app.command()
def version():
    """Show SDK version information."""
    print_version_info()


@app.command()
def create(
    name: str = typer.Argument(..., help="Service name"),
    template: str = typer.Option("base", help="Service template to use"),
    output_dir: str = typer.Option(".", help="Output directory"),
    port: int = typer.Option(8000, help="Default port for the service"),
    force: bool = typer.Option(False, help="Overwrite existing directory")
):
    """Create a new microservice from template."""
    
    # Validate and sanitize service name
    if not validate_service_name(name):
        sanitized_name = sanitize_service_name(name)
        if not typer.confirm(f"Invalid service name. Use '{sanitized_name}' instead?"):
            raise typer.Exit(1)
        name = sanitized_name
    
    # Determine output path
    output_path = Path(output_dir) / name
    
    # Check if directory exists
    if output_path.exists() and not force:
        if not typer.confirm(f"Directory '{output_path}' already exists. Overwrite?"):
            raise typer.Exit(1)
        shutil.rmtree(output_path)
    
    # Create service directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Copy template files
        _copy_template(template, output_path, name, port)
        
        rprint(f"✅ [green]Successfully created service '{name}' in '{output_path}'[/green]")
        rprint(f"📁 Service directory: {output_path.absolute()}")
        rprint(f"🚀 To run the service:")
        rprint(f"   cd {name}")
        rprint(f"   python main.py")
        
    except Exception as e:
        rprint(f"❌ [red]Error creating service: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_templates():
    """List available service templates."""
    templates = _get_available_templates()
    
    if not templates:
        rprint("❌ [red]No templates found[/red]")
        return
    
    table = Table(title="Available Service Templates")
    table.add_column("Template", style="cyan")
    table.add_column("Description", style="green")
    
    template_descriptions = {
        "base": "Basic microservice with CRUD operations",
        "api_gateway": "API Gateway with routing and middleware",
        "auth_service": "Authentication service with JWT",
        "data_service": "Data service with database integration",
        "worker_service": "Background worker service",
        "websocket_service": "WebSocket service for real-time communication"
    }
    
    for template in templates:
        description = template_descriptions.get(template, "No description available")
        table.add_row(template, description)
    
    console.print(table)


@app.command()
def init(
    directory: str = typer.Option(".", help="Directory to initialize"),
    config_only: bool = typer.Option(False, help="Only create configuration files")
):
    """Initialize a new microservices project."""
    
    project_path = Path(directory)
    project_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create basic project structure
        if not config_only:
            (project_path / "services").mkdir(exist_ok=True)
            (project_path / "shared").mkdir(exist_ok=True)
            (project_path / "tests").mkdir(exist_ok=True)
        
        # Create configuration files
        _create_config_files(project_path)
        
        # Create docker-compose for development
        _create_docker_compose(project_path)
        
        # Create .gitignore
        _create_gitignore(project_path)
        
        # Create README
        _create_readme(project_path)
        
        rprint(f"✅ [green]Successfully initialized microservices project in '{project_path.absolute()}'[/green]")
        
        if not config_only:
            rprint("📁 Project structure:")
            rprint("   services/     - Individual microservices")
            rprint("   shared/       - Shared code and utilities")
            rprint("   tests/        - Integration tests")
        
        rprint("⚙️  Configuration files:")
        rprint("   .env.example  - Environment variables template")
        rprint("   docker-compose.yml - Development environment")
        
    except Exception as e:
        rprint(f"❌ [red]Error initializing project: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config(
    show: bool = typer.Option(False, help="Show current configuration"),
    validate: bool = typer.Option(False, help="Validate configuration")
):
    """Manage SDK configuration."""
    
    if show:
        config = SDKConfig.from_env()
        config_dict = config.to_dict()
        
        rprint("📋 [bold]Current SDK Configuration:[/bold]")
        for key, value in config_dict.items():
            if isinstance(value, dict):
                rprint(f"  {key}:")
                for sub_key, sub_value in value.items():
                    rprint(f"    {sub_key}: {sub_value}")
            else:
                rprint(f"  {key}: {value}")
    
    if validate:
        config = SDKConfig.from_env()
        issues = config.validate()
        
        if issues:
            rprint("❌ [red]Configuration issues found:[/red]")
            for issue in issues:
                rprint(f"  • {issue}")
        else:
            rprint("✅ [green]Configuration is valid[/green]")


def _get_available_templates() -> list:
    """Get list of available templates."""
    try:
        from .. import templates
        templates_path = Path(templates.__file__).parent
        
        templates = []
        for item in templates_path.iterdir():
            if item.is_dir() and not item.name.startswith('__'):
                templates.append(item.name)
        
        return sorted(templates)
    except Exception:
        return ["base"]  # Fallback to base template


def _copy_template(template_name: str, output_path: Path, service_name: str, port: int):
    """Copy template files to output directory."""
    try:
        from .. import templates
        templates_path = Path(templates.__file__).parent
        template_path = templates_path / template_name
        
        if not template_path.exists():
            # Fallback to base template
            template_path = templates_path / "base_service"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template '{template_name}' not found")
        
        # Copy template files
        for item in template_path.rglob("*"):
            if item.is_file() and not item.name.startswith('.'):
                relative_path = item.relative_to(template_path)
                dest_path = output_path / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Read and process template content
                content = item.read_text(encoding='utf-8')
                
                # Replace template variables
                content = content.replace("{{SERVICE_NAME}}", service_name)
                content = content.replace("{{SERVICE_PORT}}", str(port))
                content = content.replace("base-service", service_name)
                
                dest_path.write_text(content, encoding='utf-8')
        
        # Create additional files
        _create_service_files(output_path, service_name, port)
        
    except Exception as e:
        raise Exception(f"Failed to copy template: {e}")


def _create_service_files(service_path: Path, service_name: str, port: int):
    """Create additional service files."""
    
    # Create requirements.txt
    requirements_content = """fastapi-microservices-sdk>=0.1.0
uvicorn[standard]>=0.24.0
"""
    (service_path / "requirements.txt").write_text(requirements_content)
    
    # Create Dockerfile
    dockerfile_content = f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {port}

CMD ["python", "main.py"]
"""
    (service_path / "Dockerfile").write_text(dockerfile_content)
    
    # Create .env.example
    env_content = f"""# Service Configuration
SERVICE_NAME={service_name}
SERVICE_PORT={port}
SERVICE_HOST=0.0.0.0
ENVIRONMENT=development

# SDK Configuration
SDK_LOG_LEVEL=INFO
SDK_ENABLE_DISCOVERY=true
SDK_ENABLE_MONITORING=true

# Database (if needed)
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=password
DATABASE_DB={service_name.replace('-', '_')}
"""
    (service_path / ".env.example").write_text(env_content)


def _create_config_files(project_path: Path):
    """Create project configuration files."""
    
    # Create .env.example
    env_content = """# Global SDK Configuration
SDK_ENVIRONMENT=development
SDK_LOG_LEVEL=INFO
SDK_DEFAULT_TIMEOUT=30

# Service Discovery
SERVICE_DISCOVERY_TYPE=memory
SERVICE_DISCOVERY_URL=

# Message Broker
MESSAGE_BROKER_TYPE=memory
MESSAGE_BROKER_URL=

# Database
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=password

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=*

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_URL=http://localhost:14268/api/traces
"""
    (project_path / ".env.example").write_text(env_content)


def _create_docker_compose(project_path: Path):
    """Create docker-compose.yml for development."""
    
    compose_content = """version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: microservices
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  postgres_data:
"""
    (project_path / "docker-compose.yml").write_text(compose_content)


def _create_gitignore(project_path: Path):
    """Create .gitignore file."""
    
    gitignore_content = """# Python
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

# Docker
.dockerignore
"""
    (project_path / ".gitignore").write_text(gitignore_content)


def _create_readme(project_path: Path):
    """Create README.md file."""
    
    readme_content = """# Microservices Project

This project was created using the FastAPI Microservices SDK.

## Getting Started

1. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

2. Start development services:
   ```bash
   docker-compose up -d
   ```

3. Create your first service:
   ```bash
   fastapi-sdk create my-service
   cd my-service
   python main.py
   ```

## Project Structure

- `services/` - Individual microservices
- `shared/` - Shared code and utilities
- `tests/` - Integration tests
- `docker-compose.yml` - Development environment

## Available Commands

- `fastapi-sdk create <name>` - Create a new service
- `fastapi-sdk list-templates` - List available templates
- `fastapi-sdk config --show` - Show current configuration

## Documentation

Visit the service documentation at http://localhost:8000/docs after starting a service.
"""
    (project_path / "README.md").write_text(readme_content)


def main():
    """Main entry point for the CLI."""
    app()

if __name__ == "__main__":
    main()

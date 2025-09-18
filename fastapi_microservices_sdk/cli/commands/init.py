"""
Init command for FastAPI Microservices SDK CLI.
Enhanced initialization with project wizard.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import print as rprint

from ...templates.manager import ProjectManager
from ...templates.config import TemplateConfig
from ...utils.validators import validate_service_name
from ...utils.helpers import sanitize_service_name

console = Console()
init_app = typer.Typer(name="init", help="Initialize projects and services")


@init_app.command("project")
def init_project(
    name: Optional[str] = typer.Argument(None, help="Project name"),
    directory: str = typer.Option(".", help="Directory to initialize"),
    template: str = typer.Option("microservices", help="Project template"),
    interactive: bool = typer.Option(True, help="Interactive setup wizard"),
    force: bool = typer.Option(False, help="Overwrite existing files")
):
    """Initialize a new microservices project."""
    
    project_path = Path(directory).resolve()
    
    # Interactive project setup
    if interactive:
        rprint("🚀 [blue]FastAPI Microservices SDK - Project Initialization Wizard[/blue]")
        rprint("Let's set up your new microservices project!\n")
        
        # Get project name
        if not name:
            name = Prompt.ask("📝 Project name", default="my-microservices-project")
        
        # Validate and sanitize name
        if not validate_service_name(name):
            sanitized_name = sanitize_service_name(name)
            if Confirm.ask(f"Invalid project name. Use '{sanitized_name}' instead?"):
                name = sanitized_name
            else:
                rprint("❌ [red]Project initialization cancelled[/red]")
                raise typer.Exit(1)
        
        # Project configuration
        config = _interactive_project_config(name)
        
        # Confirm setup
        _show_project_summary(name, project_path, config)
        if not Confirm.ask("Proceed with project creation?", default=True):
            rprint("❌ [yellow]Project initialization cancelled[/yellow]")
            raise typer.Exit(0)
    else:
        if not name:
            name = project_path.name
        config = _default_project_config(name)
    
    # Create project
    try:
        _create_project_structure(project_path, name, config, force)
        _create_project_files(project_path, name, config)
        
        rprint(f"✅ [green]Project '{name}' created successfully![/green]")
        rprint(f"📁 Location: {project_path.absolute()}")
        
        # Show next steps
        _show_next_steps(project_path, name)
        
    except Exception as e:
        rprint(f"❌ [red]Failed to create project: {e}[/red]")
        raise typer.Exit(1)


@init_app.command("service")
def init_service(
    name: str = typer.Argument(..., help="Service name"),
    project_path: str = typer.Option(".", help="Project directory"),
    template: str = typer.Option("base", help="Service template"),
    port: int = typer.Option(8000, help="Service port"),
    interactive: bool = typer.Option(True, help="Interactive setup"),
    add_to_compose: bool = typer.Option(True, help="Add to docker-compose.yml")
):
    """Initialize a new service within a project."""
    
    project_path = Path(project_path).resolve()
    
    if not project_path.exists():
        rprint(f"❌ [red]Project directory '{project_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Validate service name
    if not validate_service_name(name):
        sanitized_name = sanitize_service_name(name)
        if Confirm.ask(f"Invalid service name. Use '{sanitized_name}' instead?"):
            name = sanitized_name
        else:
            rprint("❌ [red]Service initialization cancelled[/red]")
            raise typer.Exit(1)
    
    services_dir = project_path / "services"
    service_path = services_dir / name
    
    # Check if service already exists
    if service_path.exists():
        if not Confirm.ask(f"Service '{name}' already exists. Overwrite?"):
            rprint("❌ [yellow]Service initialization cancelled[/yellow]")
            raise typer.Exit(0)
        shutil.rmtree(service_path)
    
    # Interactive service setup
    if interactive:
        rprint(f"🔧 [blue]Setting up service: {name}[/blue]")
        
        # Service configuration
        service_config = _interactive_service_config(name, template, port)
        
        # Show summary
        _show_service_summary(name, service_config)
        if not Confirm.ask("Create service?", default=True):
            rprint("❌ [yellow]Service initialization cancelled[/yellow]")
            raise typer.Exit(0)
    else:
        service_config = _default_service_config(name, template, port)
    
    try:
        # Create service
        _create_service_structure(service_path, name, service_config)
        _create_service_files(service_path, name, service_config)
        
        # Add to docker-compose if requested
        if add_to_compose:
            _add_service_to_compose(project_path, name, service_config)
        
        rprint(f"✅ [green]Service '{name}' created successfully![/green]")
        rprint(f"📁 Location: {service_path}")
        
        # Show service next steps
        _show_service_next_steps(service_path, name, service_config)
        
    except Exception as e:
        rprint(f"❌ [red]Failed to create service: {e}[/red]")
        raise typer.Exit(1)


@init_app.command("config")
def init_config(
    project_path: str = typer.Option(".", help="Project directory"),
    config_type: str = typer.Option("env", help="Configuration type (env, yaml, json)"),
    environment: str = typer.Option("development", help="Environment name"),
    interactive: bool = typer.Option(True, help="Interactive configuration")
):
    """Initialize configuration files for a project."""
    
    project_path = Path(project_path).resolve()
    
    if not project_path.exists():
        rprint(f"❌ [red]Project directory '{project_path}' not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"⚙️  [blue]Initializing {config_type} configuration for {environment}[/blue]")
    
    if interactive:
        config_data = _interactive_config_setup(environment)
    else:
        config_data = _default_config_data(environment)
    
    try:
        if config_type == "env":
            _create_env_config(project_path, environment, config_data)
        elif config_type in ["yaml", "yml"]:
            _create_yaml_config(project_path, environment, config_data)
        elif config_type == "json":
            _create_json_config(project_path, environment, config_data)
        else:
            rprint(f"❌ [red]Unsupported config type: {config_type}[/red]")
            raise typer.Exit(1)
        
        rprint("✅ [green]Configuration initialized successfully![/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to initialize configuration: {e}[/red]")
        raise typer.Exit(1)


def _interactive_project_config(name: str) -> Dict[str, Any]:
    """Interactive project configuration setup."""
    
    rprint("📋 [blue]Project Configuration[/blue]")
    
    # Basic settings
    description = Prompt.ask("📝 Project description", default=f"Microservices project: {name}")
    author = Prompt.ask("👤 Author name", default="Developer")
    
    # Technology choices
    rprint("\n🛠️  [blue]Technology Stack[/blue]")
    
    database_choices = ["postgresql", "mysql", "mongodb", "sqlite", "none"]
    database = Prompt.ask("💾 Primary database", choices=database_choices, default="postgresql")
    
    message_broker_choices = ["rabbitmq", "kafka", "redis", "none"]
    message_broker = Prompt.ask("📨 Message broker", choices=message_broker_choices, default="rabbitmq")
    
    cache_choices = ["redis", "memcached", "none"]
    cache = Prompt.ask("🚀 Cache system", choices=cache_choices, default="redis")
    
    # Features
    rprint("\n✨ [blue]Features[/blue]")
    
    enable_auth = Confirm.ask("🔐 Enable authentication system?", default=True)
    enable_monitoring = Confirm.ask("📊 Enable monitoring and observability?", default=True)
    enable_api_gateway = Confirm.ask("🌐 Include API Gateway?", default=True)
    enable_discovery = Confirm.ask("🔍 Enable service discovery?", default=True)
    
    # Development tools
    rprint("\n🛠️  [blue]Development Tools[/blue]")
    
    enable_docker = Confirm.ask("🐳 Generate Docker configuration?", default=True)
    enable_k8s = Confirm.ask("☸️  Generate Kubernetes manifests?", default=False)
    enable_ci_cd = Confirm.ask("🔄 Generate CI/CD configuration?", default=True)
    
    return {
        "name": name,
        "description": description,
        "author": author,
        "database": database,
        "message_broker": message_broker,
        "cache": cache,
        "enable_auth": enable_auth,
        "enable_monitoring": enable_monitoring,
        "enable_api_gateway": enable_api_gateway,
        "enable_discovery": enable_discovery,
        "enable_docker": enable_docker,
        "enable_k8s": enable_k8s,
        "enable_ci_cd": enable_ci_cd
    }


def _interactive_service_config(name: str, template: str, port: int) -> Dict[str, Any]:
    """Interactive service configuration setup."""
    
    # Service details
    description = Prompt.ask("📝 Service description", default=f"Microservice: {name}")
    
    # Template selection
    available_templates = ["base", "api", "worker", "websocket", "auth", "data"]
    template = Prompt.ask("🏗️  Service template", choices=available_templates, default=template)
    
    # Port configuration
    port = int(Prompt.ask("🔌 Service port", default=str(port)))
    
    # Database
    enable_database = Confirm.ask("💾 Enable database integration?", default=True)
    database_type = None
    if enable_database:
        db_choices = ["postgresql", "mysql", "mongodb", "sqlite"]
        database_type = Prompt.ask("💾 Database type", choices=db_choices, default="postgresql")
    
    # Features
    enable_auth = Confirm.ask("🔐 Enable authentication?", default=False)
    enable_caching = Confirm.ask("🚀 Enable caching?", default=True)
    enable_messaging = Confirm.ask("📨 Enable message broker integration?", default=True)
    enable_monitoring = Confirm.ask("📊 Enable monitoring?", default=True)
    
    return {
        "name": name,
        "description": description,
        "template": template,
        "port": port,
        "enable_database": enable_database,
        "database_type": database_type,
        "enable_auth": enable_auth,
        "enable_caching": enable_caching,
        "enable_messaging": enable_messaging,
        "enable_monitoring": enable_monitoring
    }


def _interactive_config_setup(environment: str) -> Dict[str, Any]:
    """Interactive configuration setup."""
    
    rprint(f"⚙️  [blue]Configuration for {environment} environment[/blue]")
    
    # Database configuration
    rprint("\n💾 [blue]Database Configuration[/blue]")
    db_host = Prompt.ask("Database host", default="localhost")
    db_port = int(Prompt.ask("Database port", default="5432"))
    db_name = Prompt.ask("Database name", default="microservices")
    db_user = Prompt.ask("Database user", default="postgres")
    
    # Security configuration
    rprint("\n🔐 [blue]Security Configuration[/blue]")
    jwt_secret = Prompt.ask("JWT secret key", default="change-me-in-production")
    
    # Monitoring configuration
    rprint("\n📊 [blue]Monitoring Configuration[/blue]")
    enable_metrics = Confirm.ask("Enable metrics collection?", default=True)
    enable_tracing = Confirm.ask("Enable distributed tracing?", default=True)
    
    return {
        "database": {
            "host": db_host,
            "port": db_port,
            "name": db_name,
            "user": db_user
        },
        "security": {
            "jwt_secret": jwt_secret
        },
        "monitoring": {
            "enable_metrics": enable_metrics,
            "enable_tracing": enable_tracing
        }
    }


def _default_project_config(name: str) -> Dict[str, Any]:
    """Default project configuration."""
    return {
        "name": name,
        "description": f"Microservices project: {name}",
        "author": "Developer",
        "database": "postgresql",
        "message_broker": "rabbitmq",
        "cache": "redis",
        "enable_auth": True,
        "enable_monitoring": True,
        "enable_api_gateway": True,
        "enable_discovery": True,
        "enable_docker": True,
        "enable_k8s": False,
        "enable_ci_cd": True
    }


def _default_service_config(name: str, template: str, port: int) -> Dict[str, Any]:
    """Default service configuration."""
    return {
        "name": name,
        "description": f"Microservice: {name}",
        "template": template,
        "port": port,
        "enable_database": True,
        "database_type": "postgresql",
        "enable_auth": False,
        "enable_caching": True,
        "enable_messaging": True,
        "enable_monitoring": True
    }


def _default_config_data(environment: str) -> Dict[str, Any]:
    """Default configuration data."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "microservices",
            "user": "postgres"
        },
        "security": {
            "jwt_secret": "change-me-in-production"
        },
        "monitoring": {
            "enable_metrics": True,
            "enable_tracing": True
        }
    }


def _show_project_summary(name: str, path: Path, config: Dict[str, Any]):
    """Show project creation summary."""
    
    table = Table(title=f"Project Summary: {name}")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", config["name"])
    table.add_row("Description", config["description"])
    table.add_row("Author", config["author"])
    table.add_row("Location", str(path.absolute()))
    table.add_row("Database", config["database"])
    table.add_row("Message Broker", config["message_broker"])
    table.add_row("Cache", config["cache"])
    
    # Features
    features = []
    if config["enable_auth"]:
        features.append("Authentication")
    if config["enable_monitoring"]:
        features.append("Monitoring")
    if config["enable_api_gateway"]:
        features.append("API Gateway")
    if config["enable_discovery"]:
        features.append("Service Discovery")
    
    table.add_row("Features", ", ".join(features))
    
    # Tools
    tools = []
    if config["enable_docker"]:
        tools.append("Docker")
    if config["enable_k8s"]:
        tools.append("Kubernetes")
    if config["enable_ci_cd"]:
        tools.append("CI/CD")
    
    table.add_row("Tools", ", ".join(tools))
    
    console.print(table)


def _show_service_summary(name: str, config: Dict[str, Any]):
    """Show service creation summary."""
    
    table = Table(title=f"Service Summary: {name}")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", config["name"])
    table.add_row("Description", config["description"])
    table.add_row("Template", config["template"])
    table.add_row("Port", str(config["port"]))
    
    if config["enable_database"]:
        table.add_row("Database", config["database_type"])
    
    # Features
    features = []
    if config["enable_auth"]:
        features.append("Authentication")
    if config["enable_caching"]:
        features.append("Caching")
    if config["enable_messaging"]:
        features.append("Messaging")
    if config["enable_monitoring"]:
        features.append("Monitoring")
    
    if features:
        table.add_row("Features", ", ".join(features))
    
    console.print(table)


def _create_project_structure(path: Path, name: str, config: Dict[str, Any], force: bool):
    """Create project directory structure."""
    
    if path.exists() and any(path.iterdir()) and not force:
        if not Confirm.ask(f"Directory '{path}' is not empty. Continue?"):
            raise Exception("Directory not empty")
    
    # Create main directories
    directories = [
        "services",
        "shared",
        "tests",
        "docs",
        "scripts",
        "config"
    ]
    
    if config["enable_docker"]:
        directories.append("docker")
    
    if config["enable_k8s"]:
        directories.append("k8s")
    
    if config["enable_ci_cd"]:
        directories.append(".github/workflows")
    
    for directory in directories:
        (path / directory).mkdir(parents=True, exist_ok=True)


def _create_project_files(path: Path, name: str, config: Dict[str, Any]):
    """Create project files."""
    
    # README.md
    readme_content = f"""# {config['name']}

{config['description']}

## Author
{config['author']}

## Architecture

This project uses the FastAPI Microservices SDK to provide:

- **Database**: {config['database']}
- **Message Broker**: {config['message_broker']}
- **Cache**: {config['cache']}

## Features

"""
    
    features = []
    if config["enable_auth"]:
        features.append("- 🔐 Authentication and Authorization")
    if config["enable_monitoring"]:
        features.append("- 📊 Monitoring and Observability")
    if config["enable_api_gateway"]:
        features.append("- 🌐 API Gateway")
    if config["enable_discovery"]:
        features.append("- 🔍 Service Discovery")
    
    readme_content += "\n".join(features)
    
    readme_content += """

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start infrastructure services:
   ```bash
   docker-compose up -d
   ```

3. Create your first service:
   ```bash
   fastapi-sdk init service my-service
   ```

4. Run the service:
   ```bash
   cd services/my-service
   python main.py
   ```

## Project Structure

- `services/` - Individual microservices
- `shared/` - Shared code and utilities
- `tests/` - Integration and E2E tests
- `docs/` - Project documentation
- `scripts/` - Utility scripts
- `config/` - Configuration files

## Documentation

Visit the service documentation at http://localhost:8000/docs after starting a service.
"""
    
    (path / "README.md").write_text(readme_content)
    
    # requirements.txt
    requirements = [
        "fastapi-microservices-sdk>=0.1.0",
        "uvicorn[standard]>=0.24.0",
        "python-dotenv>=1.0.0"
    ]
    
    if config["database"] == "postgresql":
        requirements.append("asyncpg>=0.29.0")
    elif config["database"] == "mysql":
        requirements.append("aiomysql>=0.2.0")
    elif config["database"] == "mongodb":
        requirements.append("motor>=3.3.0")
    
    if config["message_broker"] == "rabbitmq":
        requirements.append("aio-pika>=9.3.0")
    elif config["message_broker"] == "kafka":
        requirements.append("aiokafka>=0.10.0")
    
    if config["cache"] == "redis":
        requirements.append("redis>=5.0.0")
    
    (path / "requirements.txt").write_text("\n".join(requirements))
    
    # .env.example
    env_content = f"""# Project Configuration
PROJECT_NAME={name}
ENVIRONMENT=development

# Database Configuration
DATABASE_TYPE={config['database']}
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=password
DATABASE_DB={name.replace('-', '_')}

# Message Broker Configuration
MESSAGE_BROKER_TYPE={config['message_broker']}
MESSAGE_BROKER_URL=

# Cache Configuration
CACHE_TYPE={config['cache']}
CACHE_URL=

# Security Configuration
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_URL=http://localhost:14268/api/traces
"""
    
    (path / ".env.example").write_text(env_content)
    
    # docker-compose.yml
    if config["enable_docker"]:
        _create_docker_compose(path, config)
    
    # .gitignore
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

# Kubernetes
*.kubeconfig

# CI/CD
.github/secrets/
"""
    
    (path / ".gitignore").write_text(gitignore_content)


def _create_service_structure(path: Path, name: str, config: Dict[str, Any]):
    """Create service directory structure."""
    
    directories = [
        "api",
        "models",
        "services",
        "tests",
        "config"
    ]
    
    for directory in directories:
        (path / directory).mkdir(parents=True, exist_ok=True)


def _create_service_files(path: Path, name: str, config: Dict[str, Any]):
    """Create service files."""
    
    # main.py
    main_content = f'''"""
{config['description']}
"""

from fastapi import FastAPI
from fastapi_microservices_sdk import MicroserviceApp

# Create FastAPI app
app = FastAPI(
    title="{name}",
    description="{config['description']}",
    version="1.0.0"
)

# Initialize SDK
microservice = MicroserviceApp(
    app=app,
    service_name="{name}",
    port={config['port']}
)

# Configure features
'''
    
    if config["enable_database"]:
        main_content += f'''
# Database configuration
microservice.configure_database(
    database_type="{config['database_type']}",
    host="localhost",
    port=5432,
    database="{name.replace('-', '_')}",
    user="postgres",
    password="password"
)
'''
    
    if config["enable_auth"]:
        main_content += '''
# Authentication configuration
microservice.configure_security(
    enable_jwt=True,
    jwt_secret="your-secret-key"
)
'''
    
    if config["enable_monitoring"]:
        main_content += '''
# Monitoring configuration
microservice.configure_observability(
    enable_metrics=True,
    enable_tracing=True,
    enable_logging=True
)
'''
    
    main_content += '''

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": f"Welcome to {name} service!"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "{name}"}

if __name__ == "__main__":
    microservice.run()
'''
    
    (path / "main.py").write_text(main_content)
    
    # requirements.txt
    requirements = [
        "fastapi-microservices-sdk>=0.1.0",
        "uvicorn[standard]>=0.24.0"
    ]
    
    (path / "requirements.txt").write_text("\n".join(requirements))
    
    # .env.example
    env_content = f"""# Service Configuration
SERVICE_NAME={name}
SERVICE_PORT={config['port']}
SERVICE_HOST=0.0.0.0
ENVIRONMENT=development

# SDK Configuration
SDK_LOG_LEVEL=INFO
SDK_ENABLE_DISCOVERY=true
SDK_ENABLE_MONITORING=true
"""
    
    if config["enable_database"]:
        env_content += f"""
# Database Configuration
DATABASE_TYPE={config['database_type']}
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=password
DATABASE_DB={name.replace('-', '_')}
"""
    
    (path / ".env.example").write_text(env_content)


def _create_docker_compose(path: Path, config: Dict[str, Any]):
    """Create docker-compose.yml for the project."""
    
    compose_content = """version: '3.8'

services:
"""
    
    if config["database"] == "postgresql":
        compose_content += """  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: microservices
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

"""
    
    if config["message_broker"] == "rabbitmq":
        compose_content += """  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    ports:
      - "5672:5672"
      - "15672:15672"

"""
    
    if config["cache"] == "redis":
        compose_content += """  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

"""
    
    if config["enable_monitoring"]:
        compose_content += """  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "14268:14268"

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml

"""
    
    compose_content += """volumes:
  postgres_data:
"""
    
    (path / "docker-compose.yml").write_text(compose_content)


def _add_service_to_compose(project_path: Path, name: str, config: Dict[str, Any]):
    """Add service to docker-compose.yml."""
    
    compose_file = project_path / "docker-compose.yml"
    if not compose_file.exists():
        return
    
    # This is a simplified version - in practice, you'd parse and modify the YAML
    service_entry = f"""
  {name}:
    build: ./services/{name}
    ports:
      - "{config['port']}:{config['port']}"
    environment:
      - SERVICE_NAME={name}
      - SERVICE_PORT={config['port']}
    depends_on:
      - postgres
      - redis
"""
    
    # Append to compose file (simplified approach)
    with open(compose_file, 'a') as f:
        f.write(service_entry)


def _create_env_config(path: Path, environment: str, config_data: Dict[str, Any]):
    """Create environment configuration file."""
    
    env_content = f"""# {environment.title()} Environment Configuration

# Database Configuration
DATABASE_HOST={config_data['database']['host']}
DATABASE_PORT={config_data['database']['port']}
DATABASE_NAME={config_data['database']['name']}
DATABASE_USER={config_data['database']['user']}

# Security Configuration
JWT_SECRET_KEY={config_data['security']['jwt_secret']}

# Monitoring Configuration
ENABLE_METRICS={str(config_data['monitoring']['enable_metrics']).lower()}
ENABLE_TRACING={str(config_data['monitoring']['enable_tracing']).lower()}
"""
    
    config_file = path / f".env.{environment}"
    config_file.write_text(env_content)
    
    rprint(f"📁 Created: {config_file}")


def _create_yaml_config(path: Path, environment: str, config_data: Dict[str, Any]):
    """Create YAML configuration file."""
    
    import yaml
    
    config_file = path / f"config.{environment}.yml"
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    rprint(f"📁 Created: {config_file}")


def _create_json_config(path: Path, environment: str, config_data: Dict[str, Any]):
    """Create JSON configuration file."""
    
    import json
    
    config_file = path / f"config.{environment}.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)
    
    rprint(f"📁 Created: {config_file}")


def _show_next_steps(path: Path, name: str):
    """Show next steps after project creation."""
    
    rprint("\n🚀 [blue]Next Steps:[/blue]")
    rprint(f"   1. Navigate to project: cd {path}")
    rprint("   2. Copy environment variables: cp .env.example .env")
    rprint("   3. Start infrastructure: docker-compose up -d")
    rprint("   4. Create your first service: fastapi-sdk init service my-service")
    rprint("   5. Start developing! 🎉")


def _show_service_next_steps(path: Path, name: str, config: Dict[str, Any]):
    """Show next steps after service creation."""
    
    rprint("\n🚀 [blue]Next Steps:[/blue]")
    rprint(f"   1. Navigate to service: cd {path}")
    rprint("   2. Install dependencies: pip install -r requirements.txt")
    rprint("   3. Copy environment variables: cp .env.example .env")
    rprint(f"   4. Start the service: python main.py")
    rprint(f"   5. Visit: http://localhost:{config['port']}/docs")


if __name__ == "__main__":
    init_app()
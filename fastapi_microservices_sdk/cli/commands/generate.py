"""
Generate command for FastAPI Microservices SDK CLI.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ...templates.generators.test_generator import TestGenerator
from ...templates.generators.api_generator import APIGenerator
from ...templates.generators.model_generator import ModelGenerator
from ...templates.generators.service_generator import ServiceGenerator
from ...templates.config import TemplateConfig, TemplateVariable, VariableType
from ...utils.validators import validate_service_name

console = Console()
generate_app = typer.Typer(name="generate", help="Generate code components")


@generate_app.command("api")
def generate_api(
    name: str = typer.Argument(..., help="API name (e.g., 'user', 'product')"),
    service_path: str = typer.Option(".", help="Path to service directory"),
    model: Optional[str] = typer.Option(None, help="Associated model name"),
    crud: bool = typer.Option(True, help="Generate CRUD operations"),
    auth: bool = typer.Option(False, help="Add authentication decorators"),
    validation: bool = typer.Option(True, help="Add request/response validation"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory for generated files")
):
    """Generate API endpoints and routes."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Validate API name
    if not validate_service_name(name):
        rprint(f"❌ [red]Invalid API name: {name}[/red]")
        raise typer.Exit(1)
    
    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = service_path / "api" / f"{name}"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    rprint(f"🔧 [blue]Generating API: {name}[/blue]")
    rprint(f"📁 Output directory: {output_path}")
    
    try:
        # Create API generator configuration
        config = TemplateConfig(
            id=f"api_{name}",
            name=f"{name.title()} API",
            description=f"Generated API for {name}",
            variables=[
                TemplateVariable(
                    name="api_name",
                    type=VariableType.STRING,
                    description="Name of the API",
                    default=name,
                    required=True
                ),
                TemplateVariable(
                    name="model_name",
                    type=VariableType.STRING,
                    description="Associated model name",
                    default=model or name,
                    required=False
                ),
                TemplateVariable(
                    name="enable_crud",
                    type=VariableType.BOOLEAN,
                    description="Enable CRUD operations",
                    default=crud,
                    required=False
                ),
                TemplateVariable(
                    name="enable_auth",
                    type=VariableType.BOOLEAN,
                    description="Enable authentication",
                    default=auth,
                    required=False
                ),
                TemplateVariable(
                    name="enable_validation",
                    type=VariableType.BOOLEAN,
                    description="Enable validation",
                    default=validation,
                    required=False
                )
            ]
        )
        
        # Generate API files
        generator = APIGenerator(config)
        variables = {
            "api_name": name,
            "model_name": model or name,
            "enable_crud": crud,
            "enable_auth": auth,
            "enable_validation": validation
        }
        
        generated_files = generator.generate(variables, output_path)
        
        rprint("✅ [green]API generated successfully![/green]")
        rprint("📁 Generated files:")
        for file_path in generated_files:
            rprint(f"   • {file_path}")
        
        # Show next steps
        rprint("\n🚀 [blue]Next steps:[/blue]")
        rprint(f"   1. Review generated files in: {output_path}")
        rprint(f"   2. Import the router in your main.py:")
        rprint(f"      from api.{name}.router import router as {name}_router")
        rprint(f"      app.include_router({name}_router, prefix='/api/{name}', tags=['{name}'])")
        rprint(f"   3. Test the API at: http://localhost:8000/docs")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate API: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("model")
def generate_model(
    name: str = typer.Argument(..., help="Model name (e.g., 'User', 'Product')"),
    service_path: str = typer.Option(".", help="Path to service directory"),
    fields: Optional[List[str]] = typer.Option(None, help="Model fields (format: name:type)"),
    database: str = typer.Option("sqlalchemy", help="Database ORM (sqlalchemy, mongoengine)"),
    validation: bool = typer.Option(True, help="Add Pydantic validation"),
    timestamps: bool = typer.Option(True, help="Add created_at/updated_at fields"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory for generated files")
):
    """Generate data models and schemas."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Validate model name
    if not name.replace('_', '').isalnum():
        rprint(f"❌ [red]Invalid model name: {name}[/red]")
        raise typer.Exit(1)
    
    # Parse fields
    parsed_fields = []
    if fields:
        for field in fields:
            if ':' in field:
                field_name, field_type = field.split(':', 1)
                parsed_fields.append({
                    'name': field_name.strip(),
                    'type': field_type.strip()
                })
            else:
                parsed_fields.append({
                    'name': field.strip(),
                    'type': 'str'
                })
    
    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = service_path / "models"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    rprint(f"🔧 [blue]Generating model: {name}[/blue]")
    rprint(f"📁 Output directory: {output_path}")
    
    try:
        # Create model generator configuration
        config = TemplateConfig(
            id=f"model_{name.lower()}",
            name=f"{name} Model",
            description=f"Generated model for {name}",
            variables=[
                TemplateVariable(
                    name="model_name",
                    type=VariableType.STRING,
                    description="Name of the model",
                    default=name,
                    required=True
                ),
                TemplateVariable(
                    name="database_type",
                    type=VariableType.STRING,
                    description="Database ORM type",
                    default=database,
                    required=True
                ),
                TemplateVariable(
                    name="enable_validation",
                    type=VariableType.BOOLEAN,
                    description="Enable Pydantic validation",
                    default=validation,
                    required=False
                ),
                TemplateVariable(
                    name="enable_timestamps",
                    type=VariableType.BOOLEAN,
                    description="Add timestamp fields",
                    default=timestamps,
                    required=False
                )
            ]
        )
        
        # Generate model files
        generator = ModelGenerator(config)
        variables = {
            "model_name": name,
            "fields": parsed_fields,
            "database_type": database,
            "enable_validation": validation,
            "enable_timestamps": timestamps
        }
        
        generated_files = generator.generate(variables, output_path)
        
        rprint("✅ [green]Model generated successfully![/green]")
        rprint("📁 Generated files:")
        for file_path in generated_files:
            rprint(f"   • {file_path}")
        
        # Show next steps
        rprint("\n🚀 [blue]Next steps:[/blue]")
        rprint(f"   1. Review generated files in: {output_path}")
        rprint(f"   2. Import the model in your database setup")
        rprint(f"   3. Run database migrations if needed")
        rprint(f"   4. Use the schema in your API endpoints")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate model: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("service")
def generate_service(
    name: str = typer.Argument(..., help="Service name (e.g., 'user_service', 'email_service')"),
    service_path: str = typer.Option(".", help="Path to service directory"),
    template: str = typer.Option("base", help="Service template to use"),
    async_methods: bool = typer.Option(True, help="Generate async methods"),
    error_handling: bool = typer.Option(True, help="Add error handling"),
    logging: bool = typer.Option(True, help="Add logging"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory for generated files")
):
    """Generate service layer components."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Validate service name
    if not validate_service_name(name):
        rprint(f"❌ [red]Invalid service name: {name}[/red]")
        raise typer.Exit(1)
    
    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = service_path / "services"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    rprint(f"🔧 [blue]Generating service: {name}[/blue]")
    rprint(f"📁 Output directory: {output_path}")
    
    try:
        # Create service generator configuration
        config = TemplateConfig(
            id=f"service_{name}",
            name=f"{name.title()} Service",
            description=f"Generated service for {name}",
            variables=[
                TemplateVariable(
                    name="service_name",
                    type=VariableType.STRING,
                    description="Name of the service",
                    default=name,
                    required=True
                ),
                TemplateVariable(
                    name="template_type",
                    type=VariableType.STRING,
                    description="Service template type",
                    default=template,
                    required=True
                ),
                TemplateVariable(
                    name="enable_async",
                    type=VariableType.BOOLEAN,
                    description="Enable async methods",
                    default=async_methods,
                    required=False
                ),
                TemplateVariable(
                    name="enable_error_handling",
                    type=VariableType.BOOLEAN,
                    description="Enable error handling",
                    default=error_handling,
                    required=False
                ),
                TemplateVariable(
                    name="enable_logging",
                    type=VariableType.BOOLEAN,
                    description="Enable logging",
                    default=logging,
                    required=False
                )
            ]
        )
        
        # Generate service files
        generator = ServiceGenerator(config)
        variables = {
            "service_name": name,
            "template_type": template,
            "enable_async": async_methods,
            "enable_error_handling": error_handling,
            "enable_logging": logging
        }
        
        generated_files = generator.generate(variables, output_path)
        
        rprint("✅ [green]Service generated successfully![/green]")
        rprint("📁 Generated files:")
        for file_path in generated_files:
            rprint(f"   • {file_path}")
        
        # Show next steps
        rprint("\n🚀 [blue]Next steps:[/blue]")
        rprint(f"   1. Review generated files in: {output_path}")
        rprint(f"   2. Implement business logic in the service methods")
        rprint(f"   3. Import and use the service in your API endpoints")
        rprint(f"   4. Add unit tests for the service methods")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate service: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("tests")
def generate_tests(
    target: str = typer.Argument(..., help="Target to generate tests for (file or directory)"),
    service_path: str = typer.Option(".", help="Path to service directory"),
    test_type: str = typer.Option("all", help="Type of tests (unit, integration, e2e, all)"),
    coverage: bool = typer.Option(True, help="Generate coverage configuration"),
    fixtures: bool = typer.Option(True, help="Generate test fixtures"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory for test files")
):
    """Generate test files and configurations."""
    
    service_path = Path(service_path).resolve()
    target_path = service_path / target
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    if not target_path.exists():
        rprint(f"❌ [red]Target '{target}' not found in service directory[/red]")
        raise typer.Exit(1)
    
    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = service_path / "tests"
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    rprint(f"🔧 [blue]Generating tests for: {target}[/blue]")
    rprint(f"📁 Output directory: {output_path}")
    rprint(f"🧪 Test type: {test_type}")
    
    try:
        # Create test generator configuration
        config = TemplateConfig(
            id="test_generator",
            name="Test Generator",
            description="Generate comprehensive test suites",
            variables=[
                TemplateVariable(
                    name="target_path",
                    type=VariableType.STRING,
                    description="Target to test",
                    default=str(target_path),
                    required=True
                ),
                TemplateVariable(
                    name="test_type",
                    type=VariableType.STRING,
                    description="Type of tests to generate",
                    default=test_type,
                    required=True
                ),
                TemplateVariable(
                    name="enable_coverage",
                    type=VariableType.BOOLEAN,
                    description="Generate coverage configuration",
                    default=coverage,
                    required=False
                ),
                TemplateVariable(
                    name="enable_fixtures",
                    type=VariableType.BOOLEAN,
                    description="Generate test fixtures",
                    default=fixtures,
                    required=False
                )
            ]
        )
        
        # Generate test files
        generator = TestGenerator(config)
        variables = {
            "target_path": str(target_path),
            "test_type": test_type,
            "enable_coverage": coverage,
            "enable_fixtures": fixtures
        }
        
        generated_files = generator.generate(variables, output_path)
        
        rprint("✅ [green]Tests generated successfully![/green]")
        rprint("📁 Generated files:")
        for file_path in generated_files:
            rprint(f"   • {file_path}")
        
        # Show next steps
        rprint("\n🚀 [blue]Next steps:[/blue]")
        rprint(f"   1. Review generated test files in: {output_path}")
        rprint(f"   2. Install test dependencies: pip install pytest pytest-asyncio pytest-cov")
        rprint(f"   3. Run tests: pytest {output_path}")
        if coverage:
            rprint(f"   4. Generate coverage report: pytest --cov={target} {output_path}")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate tests: {e}[/red]")
        raise typer.Exit(1)


@generate_app.command("config")
def generate_config(
    service_path: str = typer.Option(".", help="Path to service directory"),
    config_type: str = typer.Option("env", help="Configuration type (env, yaml, json)"),
    include_secrets: bool = typer.Option(False, help="Include secret configuration"),
    environment: str = typer.Option("development", help="Target environment")
):
    """Generate configuration files."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"🔧 [blue]Generating {config_type} configuration for {environment}[/blue]")
    
    try:
        if config_type == "env":
            _generate_env_config(service_path, environment, include_secrets)
        elif config_type in ["yaml", "yml"]:
            _generate_yaml_config(service_path, environment, include_secrets)
        elif config_type == "json":
            _generate_json_config(service_path, environment, include_secrets)
        else:
            rprint(f"❌ [red]Unsupported config type: {config_type}[/red]")
            raise typer.Exit(1)
        
        rprint("✅ [green]Configuration generated successfully![/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to generate configuration: {e}[/red]")
        raise typer.Exit(1)


def _generate_env_config(service_path: Path, environment: str, include_secrets: bool):
    """Generate .env configuration file."""
    
    config_content = f"""# {environment.title()} Environment Configuration
# Generated by FastAPI Microservices SDK

# Service Configuration
SERVICE_NAME={service_path.name}
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
ENVIRONMENT={environment}

# SDK Configuration
SDK_LOG_LEVEL={"DEBUG" if environment == "development" else "INFO"}
SDK_ENABLE_DISCOVERY=true
SDK_ENABLE_MONITORING=true

# Database Configuration
DATABASE_TYPE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD={"password" if not include_secrets else "CHANGE_ME"}
DATABASE_DB={service_path.name.replace('-', '_')}

# Security Configuration
JWT_SECRET_KEY={"dev-secret-key" if not include_secrets else "CHANGE_ME_IN_PRODUCTION"}
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=*
CORS_METHODS=GET,POST,PUT,DELETE
CORS_HEADERS=*

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_TRACING={"true" if environment != "production" else "false"}
JAEGER_URL=http://localhost:14268/api/traces

# Message Broker Configuration
MESSAGE_BROKER_TYPE=memory
MESSAGE_BROKER_URL=

# Cache Configuration
CACHE_TYPE=memory
CACHE_URL=
"""
    
    config_file = service_path / f".env.{environment}"
    config_file.write_text(config_content)
    
    rprint(f"📁 Generated: {config_file}")


def _generate_yaml_config(service_path: Path, environment: str, include_secrets: bool):
    """Generate YAML configuration file."""
    
    config_content = f"""# {environment.title()} Environment Configuration
# Generated by FastAPI Microservices SDK

service:
  name: {service_path.name}
  host: 0.0.0.0
  port: 8000
  environment: {environment}

sdk:
  log_level: {"DEBUG" if environment == "development" else "INFO"}
  enable_discovery: true
  enable_monitoring: true

database:
  type: postgresql
  host: localhost
  port: 5432
  user: postgres
  password: {"password" if not include_secrets else "CHANGE_ME"}
  database: {service_path.name.replace('-', '_')}

security:
  jwt:
    secret_key: {"dev-secret-key" if not include_secrets else "CHANGE_ME_IN_PRODUCTION"}
    algorithm: HS256
    expire_minutes: 30
  
  cors:
    origins: ["*"]
    methods: ["GET", "POST", "PUT", "DELETE"]
    headers: ["*"]

monitoring:
  enable_metrics: true
  enable_tracing: {"true" if environment != "production" else "false"}
  jaeger_url: http://localhost:14268/api/traces

message_broker:
  type: memory
  url: ""

cache:
  type: memory
  url: ""
"""
    
    config_file = service_path / f"config.{environment}.yml"
    config_file.write_text(config_content)
    
    rprint(f"📁 Generated: {config_file}")


def _generate_json_config(service_path: Path, environment: str, include_secrets: bool):
    """Generate JSON configuration file."""
    
    import json
    
    config_data = {
        "service": {
            "name": service_path.name,
            "host": "0.0.0.0",
            "port": 8000,
            "environment": environment
        },
        "sdk": {
            "log_level": "DEBUG" if environment == "development" else "INFO",
            "enable_discovery": True,
            "enable_monitoring": True
        },
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password" if not include_secrets else "CHANGE_ME",
            "database": service_path.name.replace('-', '_')
        },
        "security": {
            "jwt": {
                "secret_key": "dev-secret-key" if not include_secrets else "CHANGE_ME_IN_PRODUCTION",
                "algorithm": "HS256",
                "expire_minutes": 30
            },
            "cors": {
                "origins": ["*"],
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "headers": ["*"]
            }
        },
        "monitoring": {
            "enable_metrics": True,
            "enable_tracing": environment != "production",
            "jaeger_url": "http://localhost:14268/api/traces"
        },
        "message_broker": {
            "type": "memory",
            "url": ""
        },
        "cache": {
            "type": "memory",
            "url": ""
        }
    }
    
    config_file = service_path / f"config.{environment}.json"
    config_file.write_text(json.dumps(config_data, indent=2))
    
    rprint(f"📁 Generated: {config_file}")


if __name__ == "__main__":
    generate_app()
"""
Create command for FastAPI Microservices SDK CLI.
Enhanced service creation with templates.
"""

import shutil
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from ..utils.console import success, error, warning, info, folder, rocket

from ...templates.manager import ProjectManager, ServiceManager
from ...templates.registry import TemplateManager
from ...utils.validators import validate_service_name
from ...utils.helpers import sanitize_service_name

console = Console()
create_app = typer.Typer(name="create", help="Create services and components")


@create_app.command("service")
def create_service(
    name: str = typer.Argument(..., help="Service name"),
    template: str = typer.Option("base", help="Service template to use"),
    output_dir: str = typer.Option(".", help="Output directory"),
    port: int = typer.Option(8000, help="Default port for the service"),
    force: bool = typer.Option(False, help="Overwrite existing directory"),
    interactive: bool = typer.Option(True, help="Interactive template configuration")
):
    """Create a new microservice from template."""
    
    # Validate and sanitize service name
    if not validate_service_name(name):
        sanitized_name = sanitize_service_name(name)
        if not Confirm.ask(f"Invalid service name. Use '{sanitized_name}' instead?"):
            raise typer.Exit(1)
        name = sanitized_name
    
    # Determine output path
    output_path = Path(output_dir) / name
    
    # Check if directory exists
    if output_path.exists() and not force:
        if not Confirm.ask(f"Directory '{output_path}' already exists. Overwrite?"):
            raise typer.Exit(1)
        shutil.rmtree(output_path)
    
    # Create service directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get available templates
        template_manager = TemplateManager()
        available_templates = template_manager.list_templates()
        
        if template not in [t.id for t in available_templates]:
            warning(f"Template '{template}' not found. Available templates:")
            _show_available_templates(available_templates)
            
            if interactive:
                template = Prompt.ask("Choose a template", choices=[t.id for t in available_templates], default="base")
            else:
                template = "base"
        
        # Create service using template
        from ...templates.engine import TemplateEngine
        template_engine = TemplateEngine()
        service_manager = ServiceManager(template_engine)
        
        if interactive:
            # Interactive template configuration
            template_config = _interactive_template_config(template, name, port)
        else:
            # Default configuration
            template_config = {
                "project_name": name,
                "service_name": name,
                "description": f"FastAPI microservice: {name}",
                "service_port": port,
                "author": "Developer",
                "version": "1.0.0"
            }
        
        # Generate service
        generated_files = service_manager.create_standalone_service(
            template_id=template,
            service_name=name,
            output_path=output_path,
            variables=template_config
        )
        
        success(f"Successfully created service '{name}' using template '{template}'")
        folder(f"Service directory: {output_path.absolute()}")
        
        # Show generated files
        if generated_files:
            rprint("📄 Generated files:")
            for file_path in generated_files:
                rprint(f"   • {file_path}")
        
        # Show next steps
        _show_service_next_steps(output_path, name, port, template)
        
    except Exception as e:
        error(f"Error creating service: {e}")
        raise typer.Exit(1)


@create_app.command("project")
def create_project(
    name: str = typer.Argument(..., help="Project name"),
    template: str = typer.Option("microservices", help="Project template to use"),
    output_dir: str = typer.Option(".", help="Output directory"),
    force: bool = typer.Option(False, help="Overwrite existing directory"),
    interactive: bool = typer.Option(True, help="Interactive project setup")
):
    """Create a new microservices project."""
    
    # Validate and sanitize project name
    if not validate_service_name(name):
        sanitized_name = sanitize_service_name(name)
        if not Confirm.ask(f"Invalid project name. Use '{sanitized_name}' instead?"):
            raise typer.Exit(1)
        name = sanitized_name
    
    # Determine output path
    output_path = Path(output_dir) / name
    
    # Check if directory exists
    if output_path.exists() and not force:
        if not Confirm.ask(f"Directory '{output_path}' already exists. Overwrite?"):
            raise typer.Exit(1)
        shutil.rmtree(output_path)
    
    # Create project directory
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create project using template
        project_manager = ProjectManager()
        
        if interactive:
            # Interactive project configuration
            project_config = _interactive_project_config(name)
        else:
            # Default configuration
            project_config = {
                "project_name": name,
                "author": "Developer",
                "version": "1.0.0",
                "description": f"Microservices project: {name}"
            }
        
        # Generate project
        generated_files = project_manager.create_project(
            template_id=template,
            project_name=name,
            output_path=output_path,
            variables=project_config
        )
        
        rprint(f"✅ [green]Successfully created project '{name}' using template '{template}'[/green]")
        rprint(f"📁 Project directory: {output_path.absolute()}")
        
        # Show generated files
        if generated_files:
            rprint("📄 Generated files:")
            for file_path in generated_files:
                rprint(f"   • {file_path}")
        
        # Show next steps
        _show_project_next_steps(output_path, name)
        
    except Exception as e:
        rprint(f"❌ [red]Error creating project: {e}[/red]")
        raise typer.Exit(1)


@create_app.command("component")
def create_component(
    component_type: str = typer.Argument(..., help="Component type (api, model, service, middleware)"),
    name: str = typer.Argument(..., help="Component name"),
    service_path: str = typer.Option(".", help="Path to service directory"),
    template: Optional[str] = typer.Option(None, help="Component template"),
    output_dir: Optional[str] = typer.Option(None, help="Output directory for component")
):
    """Create individual components within a service."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Validate component name
    if not name.replace('_', '').replace('-', '').isalnum():
        rprint(f"❌ [red]Invalid component name: {name}[/red]")
        raise typer.Exit(1)
    
    # Determine output directory based on component type
    if output_dir:
        output_path = Path(output_dir)
    else:
        component_dirs = {
            "api": "api",
            "model": "models",
            "service": "services",
            "middleware": "middleware",
            "schema": "schemas",
            "repository": "repositories"
        }
        
        component_dir = component_dirs.get(component_type, component_type)
        output_path = service_path / component_dir
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    rprint(f"🔧 [blue]Creating {component_type}: {name}[/blue]")
    rprint(f"📁 Output directory: {output_path}")
    
    try:
        if component_type == "api":
            _create_api_component(output_path, name, template)
        elif component_type == "model":
            _create_model_component(output_path, name, template)
        elif component_type == "service":
            _create_service_component(output_path, name, template)
        elif component_type == "middleware":
            _create_middleware_component(output_path, name, template)
        elif component_type == "schema":
            _create_schema_component(output_path, name, template)
        elif component_type == "repository":
            _create_repository_component(output_path, name, template)
        else:
            rprint(f"❌ [red]Unknown component type: {component_type}[/red]")
            rprint("Available types: api, model, service, middleware, schema, repository")
            raise typer.Exit(1)
        
        rprint(f"✅ [green]{component_type.title()} '{name}' created successfully![/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Failed to create {component_type}: {e}[/red]")
        raise typer.Exit(1)


def _interactive_template_config(template: str, name: str, port: int) -> dict:
    """Interactive template configuration."""
    
    rprint(f"🔧 [blue]Configuring template: {template}[/blue]")
    
    config = {
        "service_name": name,
        "service_port": port
    }
    
    # Basic information
    config["author"] = Prompt.ask("👤 Author name", default="Developer")
    config["version"] = Prompt.ask("📦 Version", default="1.0.0")
    config["description"] = Prompt.ask("📝 Description", default=f"Microservice: {name}")
    
    # Template-specific configuration
    if template in ["data_service", "api_service"]:
        config["enable_database"] = Confirm.ask("💾 Enable database integration?", default=True)
        if config["enable_database"]:
            db_choices = ["postgresql", "mysql", "mongodb", "sqlite"]
            config["database_type"] = Prompt.ask("💾 Database type", choices=db_choices, default="postgresql")
    
    if template == "auth_service":
        config["jwt_algorithm"] = Prompt.ask("🔐 JWT Algorithm", default="HS256")
        config["token_expire_minutes"] = int(Prompt.ask("⏰ Token expiry (minutes)", default="30"))
    
    if template == "api_gateway":
        config["enable_rate_limiting"] = Confirm.ask("🚦 Enable rate limiting?", default=True)
        config["enable_circuit_breaker"] = Confirm.ask("🔌 Enable circuit breaker?", default=True)
    
    # Common features
    config["enable_monitoring"] = Confirm.ask("📊 Enable monitoring?", default=True)
    config["enable_caching"] = Confirm.ask("🚀 Enable caching?", default=True)
    config["enable_messaging"] = Confirm.ask("📨 Enable messaging?", default=False)
    
    return config


def _interactive_project_config(name: str) -> dict:
    """Interactive project configuration."""
    
    rprint(f"🏗️  [blue]Configuring project: {name}[/blue]")
    
    config = {
        "project_name": name
    }
    
    # Basic information
    config["author"] = Prompt.ask("👤 Author name", default="Developer")
    config["version"] = Prompt.ask("📦 Version", default="1.0.0")
    config["description"] = Prompt.ask("📝 Description", default=f"Microservices project: {name}")
    
    # Technology stack
    rprint("\n🛠️  [blue]Technology Stack[/blue]")
    
    database_choices = ["postgresql", "mysql", "mongodb", "sqlite", "none"]
    config["database"] = Prompt.ask("💾 Primary database", choices=database_choices, default="postgresql")
    
    message_broker_choices = ["rabbitmq", "kafka", "redis", "none"]
    config["message_broker"] = Prompt.ask("📨 Message broker", choices=message_broker_choices, default="rabbitmq")
    
    cache_choices = ["redis", "memcached", "none"]
    config["cache"] = Prompt.ask("🚀 Cache system", choices=cache_choices, default="redis")
    
    # Features
    rprint("\n✨ [blue]Features[/blue]")
    config["enable_auth"] = Confirm.ask("🔐 Include authentication service?", default=True)
    config["enable_api_gateway"] = Confirm.ask("🌐 Include API Gateway?", default=True)
    config["enable_monitoring"] = Confirm.ask("📊 Enable monitoring stack?", default=True)
    config["enable_discovery"] = Confirm.ask("🔍 Enable service discovery?", default=True)
    
    # Development tools
    rprint("\n🛠️  [blue]Development Tools[/blue]")
    config["enable_docker"] = Confirm.ask("🐳 Generate Docker configuration?", default=True)
    config["enable_k8s"] = Confirm.ask("☸️  Generate Kubernetes manifests?", default=False)
    config["enable_ci_cd"] = Confirm.ask("🔄 Generate CI/CD pipeline?", default=True)
    
    return config


def _show_available_templates(templates: List) -> None:
    """Show available templates in a table."""
    
    table = Table(title="Available Service Templates")
    table.add_column("Template ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="yellow")
    table.add_column("Category", style="blue")
    
    for template in templates:
        table.add_row(
            template.id,
            template.name,
            template.description,
            template.category.value if hasattr(template, 'category') else "general"
        )
    
    console.print(table)


def _create_api_component(output_path: Path, name: str, template: Optional[str]):
    """Create API component (router + endpoints)."""
    
    # Create router file
    router_content = f'''"""
API router for {name}.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from ..models.{name} import {name.title()}
from ..schemas.{name} import {name.title()}Create, {name.title()}Update, {name.title()}Response
from ..services.{name}_service import {name.title()}Service

router = APIRouter()


@router.get("/", response_model=List[{name.title()}Response])
async def get_{name}s(
    skip: int = 0,
    limit: int = 100,
    service: {name.title()}Service = Depends()
):
    """Get all {name}s."""
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{{item_id}}", response_model={name.title()}Response)
async def get_{name}(
    item_id: int,
    service: {name.title()}Service = Depends()
):
    """Get {name} by ID."""
    item = await service.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="{name.title()} not found")
    return item


@router.post("/", response_model={name.title()}Response)
async def create_{name}(
    item: {name.title()}Create,
    service: {name.title()}Service = Depends()
):
    """Create new {name}."""
    return await service.create(item)


@router.put("/{{item_id}}", response_model={name.title()}Response)
async def update_{name}(
    item_id: int,
    item: {name.title()}Update,
    service: {name.title()}Service = Depends()
):
    """Update {name}."""
    updated_item = await service.update(item_id, item)
    if not updated_item:
        raise HTTPException(status_code=404, detail="{name.title()} not found")
    return updated_item


@router.delete("/{{item_id}}")
async def delete_{name}(
    item_id: int,
    service: {name.title()}Service = Depends()
):
    """Delete {name}."""
    success = await service.delete(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="{name.title()} not found")
    return {{"message": "{name.title()} deleted successfully"}}
'''
    
    router_file = output_path / f"{name}_router.py"
    router_file.write_text(router_content)
    
    rprint(f"📄 Created: {router_file}")


def _create_model_component(output_path: Path, name: str, template: Optional[str]):
    """Create model component (database model)."""
    
    model_content = f'''"""
Database model for {name}.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class {name.title()}(Base):
    """Database model for {name}."""
    
    __tablename__ = "{name}s"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<{name.title()}(id={{self.id}}, name={{self.name}})>"
'''
    
    model_file = output_path / f"{name}.py"
    model_file.write_text(model_content)
    
    rprint(f"📄 Created: {model_file}")


def _create_service_component(output_path: Path, name: str, template: Optional[str]):
    """Create service component (business logic)."""
    
    service_content = f'''"""
Service layer for {name}.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from ..models.{name} import {name.title()}
from ..schemas.{name} import {name.title()}Create, {name.title()}Update


class {name.title()}Service:
    """Service class for {name} business logic."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[{name.title()}]:
        """Get all {name}s."""
        return self.db.query({name.title()}).offset(skip).limit(limit).all()
    
    async def get_by_id(self, item_id: int) -> Optional[{name.title()}]:
        """Get {name} by ID."""
        return self.db.query({name.title()}).filter({name.title()}.id == item_id).first()
    
    async def create(self, item: {name.title()}Create) -> {name.title()}:
        """Create new {name}."""
        db_item = {name.title()}(**item.dict())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    async def update(self, item_id: int, item: {name.title()}Update) -> Optional[{name.title()}]:
        """Update {name}."""
        db_item = self.db.query({name.title()}).filter({name.title()}.id == item_id).first()
        if db_item:
            for key, value in item.dict(exclude_unset=True).items():
                setattr(db_item, key, value)
            self.db.commit()
            self.db.refresh(db_item)
        return db_item
    
    async def delete(self, item_id: int) -> bool:
        """Delete {name}."""
        db_item = self.db.query({name.title()}).filter({name.title()}.id == item_id).first()
        if db_item:
            self.db.delete(db_item)
            self.db.commit()
            return True
        return False
'''
    
    service_file = output_path / f"{name}_service.py"
    service_file.write_text(service_content)
    
    rprint(f"📄 Created: {service_file}")


def _create_middleware_component(output_path: Path, name: str, template: Optional[str]):
    """Create middleware component."""
    
    middleware_content = f'''"""
Middleware for {name}.
"""

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)


class {name.title()}Middleware(BaseHTTPMiddleware):
    """Custom middleware for {name}."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and response."""
        start_time = time.time()
        
        # Pre-processing
        logger.info(f"Processing request: {{request.method}} {{request.url}}")
        
        # Process request
        response = await call_next(request)
        
        # Post-processing
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(f"Request processed in {{process_time:.4f}}s")
        
        return response
'''
    
    middleware_file = output_path / f"{name}_middleware.py"
    middleware_file.write_text(middleware_content)
    
    rprint(f"📄 Created: {middleware_file}")


def _create_schema_component(output_path: Path, name: str, template: Optional[str]):
    """Create schema component (Pydantic models)."""
    
    schema_content = f'''"""
Pydantic schemas for {name}.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class {name.title()}Base(BaseModel):
    """Base schema for {name}."""
    name: str = Field(..., description="Name of the {name}")
    description: Optional[str] = Field(None, description="Description of the {name}")
    is_active: bool = Field(True, description="Whether the {name} is active")


class {name.title()}Create({name.title()}Base):
    """Schema for creating {name}."""
    pass


class {name.title()}Update(BaseModel):
    """Schema for updating {name}."""
    name: Optional[str] = Field(None, description="Name of the {name}")
    description: Optional[str] = Field(None, description="Description of the {name}")
    is_active: Optional[bool] = Field(None, description="Whether the {name} is active")


class {name.title()}Response({name.title()}Base):
    """Schema for {name} response."""
    id: int = Field(..., description="ID of the {name}")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
'''
    
    schema_file = output_path / f"{name}.py"
    schema_file.write_text(schema_content)
    
    rprint(f"📄 Created: {schema_file}")


def _create_repository_component(output_path: Path, name: str, template: Optional[str]):
    """Create repository component (data access layer)."""
    
    repository_content = f'''"""
Repository for {name} data access.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..models.{name} import {name.title()}


class {name.title()}Repository:
    """Repository class for {name} data access."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[{name.title()}]:
        """Get all {name}s."""
        return self.db.query({name.title()}).offset(skip).limit(limit).all()
    
    def get_by_id(self, item_id: int) -> Optional[{name.title()}]:
        """Get {name} by ID."""
        return self.db.query({name.title()}).filter({name.title()}.id == item_id).first()
    
    def get_by_name(self, name: str) -> Optional[{name.title()}]:
        """Get {name} by name."""
        return self.db.query({name.title()}).filter({name.title()}.name == name).first()
    
    def search(self, query: str) -> List[{name.title()}]:
        """Search {name}s by name or description."""
        return self.db.query({name.title()}).filter(
            or_(
                {name.title()}.name.ilike(f"%{{query}}%"),
                {name.title()}.description.ilike(f"%{{query}}%")
            )
        ).all()
    
    def get_active(self) -> List[{name.title()}]:
        """Get all active {name}s."""
        return self.db.query({name.title()}).filter({name.title()}.is_active == True).all()
    
    def create(self, **kwargs) -> {name.title()}:
        """Create new {name}."""
        db_item = {name.title()}(**kwargs)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item
    
    def update(self, item_id: int, **kwargs) -> Optional[{name.title()}]:
        """Update {name}."""
        db_item = self.get_by_id(item_id)
        if db_item:
            for key, value in kwargs.items():
                if hasattr(db_item, key):
                    setattr(db_item, key, value)
            self.db.commit()
            self.db.refresh(db_item)
        return db_item
    
    def delete(self, item_id: int) -> bool:
        """Delete {name}."""
        db_item = self.get_by_id(item_id)
        if db_item:
            self.db.delete(db_item)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """Count total {name}s."""
        return self.db.query({name.title()}).count()
'''
    
    repository_file = output_path / f"{name}_repository.py"
    repository_file.write_text(repository_content)
    
    rprint(f"📄 Created: {repository_file}")


def _show_service_next_steps(output_path: Path, name: str, port: int, template: str):
    """Show next steps after service creation."""
    
    rocket("Next Steps:")
    rprint(f"   1. Navigate to service: cd {output_path}")
    rprint("   2. Install dependencies: pip install -r requirements.txt")
    rprint("   3. Copy environment variables: cp .env.example .env")
    rprint("   4. Configure your database and other settings in .env")
    rprint(f"   5. Start the service: python main.py")
    rprint(f"   6. Visit the API docs: http://localhost:{port}/docs")
    
    if template in ["data_service", "api_service"]:
        rprint("   7. Run database migrations if needed")
    
    rprint("   8. Start building your API endpoints!")


def _show_project_next_steps(output_path: Path, name: str):
    """Show next steps after project creation."""
    
    rprint("\n🚀 [blue]Next Steps:[/blue]")
    rprint(f"   1. Navigate to project: cd {output_path}")
    rprint("   2. Copy environment variables: cp .env.example .env")
    rprint("   3. Start infrastructure services: docker-compose up -d")
    rprint("   4. Create your first service: fastapi-sdk create service my-service")
    rprint("   5. Explore the project structure and documentation")
    rprint("   6. Start developing your microservices! 🎉")


if __name__ == "__main__":
    create_app()
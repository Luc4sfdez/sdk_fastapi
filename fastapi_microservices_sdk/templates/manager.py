"""
Project and Service Management

Project lifecycle management and service orchestration within projects.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
import json
import yaml
from datetime import datetime

from .config import ProjectConfig, ServiceConfig, TemplateConfig
from .engine import TemplateEngine, RenderedTemplate
from .registry import TemplateRegistry, TemplateInfo
from .exceptions import ProjectError, ServiceError, ConfigurationError


@dataclass
class Project:
    """Project definition and management."""
    config: ProjectConfig
    services: List['Service'] = field(default_factory=list)
    path: Optional[Path] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Project name."""
        return self.config.name
    
    @property
    def service_names(self) -> List[str]:
        """List of service names."""
        return [service.name for service in self.services]
    
    def get_service(self, name: str) -> Optional['Service']:
        """Get service by name."""
        for service in self.services:
            if service.name == name:
                return service
        return None
    
    def add_service(self, service: 'Service') -> None:
        """Add service to project."""
        if self.get_service(service.name):
            raise ServiceError(
                service_name=service.name,
                operation="add",
                error_message="Service already exists in project"
            )
        
        self.services.append(service)
        self.updated_at = datetime.now()
    
    def remove_service(self, name: str) -> None:
        """Remove service from project."""
        service = self.get_service(name)
        if not service:
            raise ServiceError(
                service_name=name,
                operation="remove",
                error_message="Service not found in project"
            )
        
        self.services.remove(service)
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary."""
        return {
            'config': {
                'name': self.config.name,
                'description': self.config.description,
                'version': self.config.version,
                'author': self.config.author,
                'license': self.config.license,
                'python_version': self.config.python_version,
                'dependencies': self.config.dependencies,
                'dev_dependencies': self.config.dev_dependencies,
                'services': self.config.services
            },
            'services': [service.to_dict() for service in self.services],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], path: Optional[Path] = None) -> 'Project':
        """Create project from dictionary."""
        config = ProjectConfig.from_dict(data['config'])
        
        services = []
        for service_data in data.get('services', []):
            service = Service.from_dict(service_data)
            services.append(service)
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            config=config,
            services=services,
            path=path,
            created_at=created_at,
            updated_at=updated_at
        )


@dataclass
class Service:
    """Service definition within a project."""
    config: ServiceConfig
    template_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def name(self) -> str:
        """Service name."""
        return self.config.name
    
    @property
    def type(self) -> str:
        """Service type."""
        return self.config.type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert service to dictionary."""
        return {
            'config': {
                'name': self.config.name,
                'type': self.config.type,
                'template': self.config.template,
                'port': self.config.port,
                'database': self.config.database,
                'message_broker': self.config.message_broker,
                'dependencies': self.config.dependencies,
                'environment': self.config.environment
            },
            'template_id': self.template_id,
            'variables': self.variables,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Service':
        """Create service from dictionary."""
        config = ServiceConfig.from_dict(data['config'])
        
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            config=config,
            template_id=data['template_id'],
            variables=data.get('variables', {}),
            created_at=created_at,
            updated_at=updated_at
        )


class ProjectManager:
    """Project lifecycle management."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
        self.template_manager = TemplateManager()
    
    def create_project(self, name: str, template_id: str, variables: Dict[str, Any], output_path: Path) -> Project:
        """Create new project from template."""
        try:
            # Validate output path
            if output_path.exists():
                raise ProjectError(
                    project_name=name,
                    operation="create",
                    error_message=f"Directory {output_path} already exists"
                )
            
            # Generate project from template
            rendered = self.template_engine.generate_project(
                template_id=template_id,
                variables=variables,
                output_path=output_path
            )
            
            # Create project configuration
            project_config = ProjectConfig(
                name=name,
                description=variables.get('description', f'{name} microservice project'),
                version=variables.get('version', '1.0.0'),
                author=variables.get('author', ''),
                license=variables.get('license', 'MIT')
            )
            
            # Create project instance
            project = Project(
                config=project_config,
                path=output_path,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save project metadata
            self._save_project_metadata(project)
            
            return project
            
        except Exception as e:
            raise ProjectError(
                project_name=name,
                operation="create",
                error_message=str(e)
            )
    
    def load_project(self, project_path: Path) -> Project:
        """Load existing project."""
        try:
            metadata_file = project_path / ".fastapi-sdk" / "project.yaml"
            
            if not metadata_file.exists():
                raise ProjectError(
                    project_name=str(project_path),
                    operation="load",
                    error_message="Project metadata not found"
                )
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            project = Project.from_dict(data, path=project_path)
            return project
            
        except Exception as e:
            raise ProjectError(
                project_name=str(project_path),
                operation="load",
                error_message=str(e)
            )
    
    def save_project(self, project: Project) -> None:
        """Save project metadata."""
        try:
            project.updated_at = datetime.now()
            self._save_project_metadata(project)
        except Exception as e:
            raise ProjectError(
                project_name=project.name,
                operation="save",
                error_message=str(e)
            )
    
    def update_project(self, project: Project, updates: Dict[str, Any]) -> Project:
        """Update project configuration."""
        try:
            # Update configuration
            if 'description' in updates:
                project.config.description = updates['description']
            if 'version' in updates:
                project.config.version = updates['version']
            if 'author' in updates:
                project.config.author = updates['author']
            if 'license' in updates:
                project.config.license = updates['license']
            if 'dependencies' in updates:
                project.config.dependencies = updates['dependencies']
            if 'dev_dependencies' in updates:
                project.config.dev_dependencies = updates['dev_dependencies']
            
            # Save changes
            self.save_project(project)
            
            return project
            
        except Exception as e:
            raise ProjectError(
                project_name=project.name,
                operation="update",
                error_message=str(e)
            )
    
    def validate_project(self, project: Project) -> List[str]:
        """Validate project configuration and structure."""
        errors = []
        
        # Validate configuration
        if not project.config.name:
            errors.append("Project name is required")
        
        if not project.config.description:
            errors.append("Project description is required")
        
        # Validate services
        service_names = set()
        for service in project.services:
            if service.name in service_names:
                errors.append(f"Duplicate service name: {service.name}")
            service_names.add(service.name)
            
            # Validate service dependencies
            for dep in service.config.dependencies:
                if dep not in service_names and dep not in project.config.services:
                    errors.append(f"Service {service.name} depends on unknown service: {dep}")
        
        # Validate project structure
        if project.path and project.path.exists():
            required_files = [
                "pyproject.toml",
                "README.md",
                ".gitignore"
            ]
            
            for required_file in required_files:
                if not (project.path / required_file).exists():
                    errors.append(f"Missing required file: {required_file}")
        
        return errors
    
    def _save_project_metadata(self, project: Project) -> None:
        """Save project metadata to file."""
        if not project.path:
            raise ProjectError(
                project_name=project.name,
                operation="save_metadata",
                error_message="Project path not set"
            )
        
        metadata_dir = project.path / ".fastapi-sdk"
        metadata_dir.mkdir(exist_ok=True)
        
        metadata_file = metadata_dir / "project.yaml"
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            yaml.dump(project.to_dict(), f, default_flow_style=False)


class ServiceManager:
    """Service lifecycle management."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.template_engine = template_engine
    
    def create_service(self, project: Project, name: str, template_id: str, variables: Dict[str, Any]) -> Service:
        """Create new service in project."""
        try:
            # Validate service name
            if project.get_service(name):
                raise ServiceError(
                    service_name=name,
                    operation="create",
                    error_message="Service already exists in project"
                )
            
            # Create service configuration
            service_config = ServiceConfig(
                name=name,
                type=variables.get('type', 'api'),
                template=template_id,
                port=variables.get('port', 8000),
                database=variables.get('database'),
                message_broker=variables.get('message_broker'),
                dependencies=variables.get('dependencies', []),
                environment=variables.get('environment', {})
            )
            
            # Create service instance
            service = Service(
                config=service_config,
                template_id=template_id,
                variables=variables,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Generate service code
            if project.path:
                service_path = project.path / "services" / name
                service.path = service_path
                
                # Prepare service variables
                service_variables = variables.copy()
                service_variables.update({
                    'service_name': name,
                    'project_name': project.name,
                    'service_port': service_config.port
                })
                
                # Generate service from template
                self.template_engine.generate_project(
                    template_id=template_id,
                    variables=service_variables,
                    output_path=service_path
                )
            
            # Add service to project
            project.add_service(service)
            
            return service
            
        except Exception as e:
            raise ServiceError(
                service_name=name,
                operation="create",
                error_message=str(e)
            )
    
    def create_standalone_service(self, template_id: str, service_name: str, output_path: Path, variables: Dict[str, Any]) -> List[Path]:
        """Create a standalone service without a project context."""
        try:
            # Get the actual template instance
            template = self._get_builtin_template(template_id)
            if not template:
                raise ServiceError(
                    service_name=service_name,
                    operation="create_standalone", 
                    error_message=f"Template '{template_id}' not found"
                )
            
            # Prepare service variables
            service_variables = variables.copy()
            service_variables.update({
                'service_name': service_name,
                'project_name': service_variables.get('project_name', service_name),
                'service_port': variables.get('service_port', 8000)
            })
            
            # Validate variables
            validation_errors = template.validate_variables(service_variables)
            if validation_errors:
                raise ServiceError(
                    service_name=service_name,
                    operation="create_standalone",
                    error_message=f"Variable validation failed: {', '.join(validation_errors)}"
                )
            
            # Generate files
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
            
            generated_files = []
            for template_file in template.files:
                try:
                    rendered_content = template_file.render(service_variables)
                    file_path = output_path / template_file.path
                    
                    # Create parent directories
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    if template_file.is_binary:
                        file_path.write_bytes(rendered_content.encode() if isinstance(rendered_content, str) else rendered_content)
                    else:
                        file_path.write_text(rendered_content, encoding='utf-8')
                    
                    generated_files.append(file_path)
                    
                except Exception as e:
                    raise ServiceError(
                        service_name=service_name,
                        operation="create_standalone",
                        error_message=f"Failed to render file {template_file.path}: {str(e)}"
                    )
            
            return generated_files
            
        except ServiceError:
            raise
        except Exception as e:
            raise ServiceError(
                service_name=service_name,
                operation="create_standalone",
                error_message=str(e)
            )
    
    def _get_builtin_template(self, template_id: str):
        """Get builtin template instance."""
        template_map = {
            "auth_service": "fastapi_microservices_sdk.templates.builtin_templates.auth_service.AuthServiceTemplate",
            "api_gateway": "fastapi_microservices_sdk.templates.builtin_templates.api_gateway.APIGatewayTemplate", 
            "data_service": "fastapi_microservices_sdk.templates.builtin_templates.data_service.DataServiceTemplate",
            "microservice": "fastapi_microservices_sdk.templates.builtin_templates.microservice.MicroserviceTemplate",
            "file_service": "fastapi_microservices_sdk.templates.builtin_templates.file_service.FileServiceTemplate",
            "notification_service": "fastapi_microservices_sdk.templates.builtin_templates.notification_service.NotificationServiceTemplate"
        }
        
        if template_id not in template_map:
            return None
        
        try:
            module_path, class_name = template_map[template_id].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            template_class = getattr(module, class_name)
            return template_class.create_template()
        except Exception:
            return None
    
    def update_service(self, project: Project, service_name: str, updates: Dict[str, Any]) -> Service:
        """Update service configuration."""
        try:
            service = project.get_service(service_name)
            if not service:
                raise ServiceError(
                    service_name=service_name,
                    operation="update",
                    error_message="Service not found in project"
                )
            
            # Update configuration
            if 'port' in updates:
                service.config.port = updates['port']
            if 'database' in updates:
                service.config.database = updates['database']
            if 'message_broker' in updates:
                service.config.message_broker = updates['message_broker']
            if 'dependencies' in updates:
                service.config.dependencies = updates['dependencies']
            if 'environment' in updates:
                service.config.environment.update(updates['environment'])
            
            # Update variables
            if 'variables' in updates:
                service.variables.update(updates['variables'])
            
            service.updated_at = datetime.now()
            project.updated_at = datetime.now()
            
            return service
            
        except Exception as e:
            raise ServiceError(
                service_name=service_name,
                operation="update",
                error_message=str(e)
            )
    
    def remove_service(self, project: Project, service_name: str) -> None:
        """Remove service from project."""
        try:
            service = project.get_service(service_name)
            if not service:
                raise ServiceError(
                    service_name=service_name,
                    operation="remove",
                    error_message="Service not found in project"
                )
            
            # Remove service directory if it exists
            if service.path and service.path.exists():
                import shutil
                shutil.rmtree(service.path)
            
            # Remove service from project
            project.remove_service(service_name)
            
        except Exception as e:
            raise ServiceError(
                service_name=service_name,
                operation="remove",
                error_message=str(e)
            )
    
    def validate_service(self, service: Service) -> List[str]:
        """Validate service configuration."""
        errors = []
        
        # Validate configuration
        if not service.config.name:
            errors.append("Service name is required")
        
        if not service.config.type:
            errors.append("Service type is required")
        
        if not service.config.template:
            errors.append("Service template is required")
        
        # Validate port
        if service.config.port < 1 or service.config.port > 65535:
            errors.append(f"Invalid port number: {service.config.port}")
        
        # Validate template exists
        try:
            self.template_engine.get_template(service.template_id)
        except Exception as e:
            errors.append(f"Template validation failed: {str(e)}")
        
        return errors
    
    def regenerate_service(self, project: Project, service_name: str, overwrite: bool = False) -> Service:
        """Regenerate service from template."""
        try:
            service = project.get_service(service_name)
            if not service:
                raise ServiceError(
                    service_name=service_name,
                    operation="regenerate",
                    error_message="Service not found in project"
                )
            
            if not service.path:
                raise ServiceError(
                    service_name=service_name,
                    operation="regenerate",
                    error_message="Service path not set"
                )
            
            # Prepare service variables
            service_variables = service.variables.copy()
            service_variables.update({
                'service_name': service.name,
                'project_name': project.name,
                'service_port': service.config.port
            })
            
            # Regenerate service from template
            self.template_engine.generate_project(
                template_id=service.template_id,
                variables=service_variables,
                output_path=service.path,
                overwrite=overwrite
            )
            
            service.updated_at = datetime.now()
            
            return service
            
        except Exception as e:
            raise ServiceError(
                service_name=service_name,
                operation="regenerate",
                error_message=str(e)
            )
    
    def get_project_templates(self) -> List[TemplateInfo]:
        """Get available project templates."""
        return self.template_manager.list_templates()
    
    def get_service_templates(self) -> List[TemplateInfo]:
        """Get available service templates."""
        # Filter templates suitable for services
        all_templates = self.template_manager.list_templates()
        return [t for t in all_templates if 'service' in t.tags or t.category.value.endswith('_service')]
    
    def analyze_project_structure(self, project: Project) -> Dict[str, Any]:
        """Analyze project structure and provide insights."""
        analysis = {
            'services_count': len(project.services),
            'service_types': {},
            'dependencies': {},
            'ports_used': [],
            'databases_used': set(),
            'message_brokers_used': set(),
            'potential_issues': []
        }
        
        # Analyze services
        for service in project.services:
            # Count service types
            service_type = service.config.type
            analysis['service_types'][service_type] = analysis['service_types'].get(service_type, 0) + 1
            
            # Collect ports
            analysis['ports_used'].append(service.config.port)
            
            # Collect databases
            if service.config.database:
                analysis['databases_used'].add(service.config.database)
            
            # Collect message brokers
            if service.config.message_broker:
                analysis['message_brokers_used'].add(service.config.message_broker)
            
            # Analyze dependencies
            for dep in service.config.dependencies:
                if dep not in analysis['dependencies']:
                    analysis['dependencies'][dep] = []
                analysis['dependencies'][dep].append(service.name)
        
        # Check for potential issues
        port_counts = {}
        for port in analysis['ports_used']:
            port_counts[port] = port_counts.get(port, 0) + 1
        
        for port, count in port_counts.items():
            if count > 1:
                analysis['potential_issues'].append(f"Port {port} is used by {count} services")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(project)
        if circular_deps:
            analysis['potential_issues'].extend([f"Circular dependency: {' -> '.join(cycle)}" for cycle in circular_deps])
        
        # Convert sets to lists for JSON serialization
        analysis['databases_used'] = list(analysis['databases_used'])
        analysis['message_brokers_used'] = list(analysis['message_brokers_used'])
        
        return analysis
    
    def _detect_circular_dependencies(self, project: Project) -> List[List[str]]:
        """Detect circular dependencies in project services."""
        # Build dependency graph
        graph = {}
        for service in project.services:
            graph[service.name] = service.config.dependencies
        
        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor in graph:  # Only follow dependencies to services in this project
                    dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for service_name in graph:
            if service_name not in visited:
                dfs(service_name, [])
        
        return cycles
    
    def generate_project_documentation(self, project: Project) -> str:
        """Generate comprehensive project documentation."""
        analysis = self.analyze_project_structure(project)
        
        doc = f"""# {project.name}

{project.config.description}

## Project Information

- **Version**: {project.config.version}
- **Author**: {project.config.author}
- **License**: {project.config.license}
- **Python Version**: {project.config.python_version}

## Architecture Overview

This project contains {analysis['services_count']} services:

"""
        
        # Service types summary
        if analysis['service_types']:
            doc += "### Service Types\n\n"
            for service_type, count in analysis['service_types'].items():
                doc += f"- **{service_type.title()}**: {count} service{'s' if count > 1 else ''}\n"
            doc += "\n"
        
        # Services list
        doc += "### Services\n\n"
        for service in project.services:
            doc += f"#### {service.name}\n\n"
            doc += f"- **Type**: {service.config.type}\n"
            doc += f"- **Template**: {service.template_id}\n"
            doc += f"- **Port**: {service.config.port}\n"
            
            if service.config.database:
                doc += f"- **Database**: {service.config.database}\n"
            
            if service.config.message_broker:
                doc += f"- **Message Broker**: {service.config.message_broker}\n"
            
            if service.config.dependencies:
                doc += f"- **Dependencies**: {', '.join(service.config.dependencies)}\n"
            
            doc += "\n"
        
        # Infrastructure
        if analysis['databases_used'] or analysis['message_brokers_used']:
            doc += "## Infrastructure\n\n"
            
            if analysis['databases_used']:
                doc += f"**Databases**: {', '.join(analysis['databases_used'])}\n\n"
            
            if analysis['message_brokers_used']:
                doc += f"**Message Brokers**: {', '.join(analysis['message_brokers_used'])}\n\n"
        
        # Dependencies
        if analysis['dependencies']:
            doc += "## Service Dependencies\n\n"
            for service, dependents in analysis['dependencies'].items():
                doc += f"- **{service}** is used by: {', '.join(dependents)}\n"
            doc += "\n"
        
        # Issues
        if analysis['potential_issues']:
            doc += "## Potential Issues\n\n"
            for issue in analysis['potential_issues']:
                doc += f"⚠️ {issue}\n"
            doc += "\n"
        
        # Getting started
        doc += """## Getting Started

### Prerequisites

- Python {python_version}
- Docker and Docker Compose

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Start services: `docker-compose up -d`

### Development

- Run tests: `pytest`
- Format code: `black . && isort .`
- Type check: `mypy .`

## API Documentation

Each service provides its own API documentation:

""".format(python_version=project.config.python_version)
        
        for service in project.services:
            doc += f"- **{service.name}**: http://localhost:{service.config.port}/docs\n"
        
        return doc
    
    def export_project_config(self, project: Project) -> Dict[str, Any]:
        """Export project configuration for backup or sharing."""
        return {
            'project': project.to_dict(),
            'analysis': self.analyze_project_structure(project),
            'exported_at': datetime.now().isoformat(),
            'sdk_version': '1.0.0'
        }
    
    def import_project_config(self, config_data: Dict[str, Any], project_path: Path) -> Project:
        """Import project configuration from exported data."""
        try:
            project_data = config_data['project']
            project = Project.from_dict(project_data, path=project_path)
            
            # Validate imported project
            validation_errors = self.validate_project(project)
            if validation_errors:
                raise ProjectError(
                    project_name=project.name,
                    operation="import",
                    error_message=f"Validation failed: {', '.join(validation_errors)}"
                )
            
            return project
            
        except Exception as e:
            raise ProjectError(
                project_name="unknown",
                operation="import",
                error_message=str(e)
            )
    
    def clone_project(self, source_project: Project, new_name: str, output_path: Path) -> Project:
        """Clone an existing project with a new name."""
        try:
            # Export source project
            config_data = self.export_project_config(source_project)
            
            # Modify for new project
            project_data = config_data['project']
            project_data['config']['name'] = new_name
            
            # Update service names to avoid conflicts
            for i, service_data in enumerate(project_data['services']):
                old_name = service_data['config']['name']
                new_service_name = f"{new_name}-{old_name}"
                service_data['config']['name'] = new_service_name
            
            # Create new project
            new_project = Project.from_dict(project_data, path=output_path)
            new_project.created_at = datetime.now()
            new_project.updated_at = datetime.now()
            
            # Save new project
            self._save_project_metadata(new_project)
            
            return new_project
            
        except Exception as e:
            raise ProjectError(
                project_name=new_name,
                operation="clone",
                error_message=str(e)
            )


# Duplicate ServiceManager removed


class TemplateManager:
    """Template management and orchestration."""
    
    def __init__(self):
        self.registry = TemplateRegistry()
        self.engine = TemplateEngine()
    
    def get_available_templates(self) -> List[TemplateInfo]:
        """Get list of available templates."""
        return self.registry.list_templates()
    
    def get_template(self, template_id: str) -> Optional[TemplateInfo]:
        """Get template by ID."""
        return self.registry.get_template(template_id)
    
    def render_template(self, template_id: str, variables: Dict[str, Any], 
                       output_path: Path) -> RenderedTemplate:
        """Render template with variables."""
        template_info = self.get_template(template_id)
        if not template_info:
            raise ProjectError(
                project_name=template_id,
                operation="render",
                error_message=f"Template '{template_id}' not found"
            )
        
        # Load template
        template = self.registry.loader.load_template(template_info.path or template_id)
        
        # Render template
        return self.engine.render_template(template, variables, output_path)
    
    def list_template_categories(self) -> List[str]:
        """List available template categories."""
        templates = self.get_available_templates()
        categories = set()
        for template in templates:
            categories.add(template.category.value)
        return sorted(list(categories))
    
    def get_templates_by_category(self, category: str) -> List[TemplateInfo]:
        """Get templates filtered by category."""
        templates = self.get_available_templates()
        return [t for t in templates if t.category.value == category]
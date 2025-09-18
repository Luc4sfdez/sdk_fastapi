"""
CLI Commands

Core CLI commands for template operations and project management.
"""

import argparse
from pathlib import Path
from typing import Dict, Any, List

from .framework import Command, CommandResult
from .context import CLIContext
from .wizard import (
    ProjectCreationWizard,
    ServiceCreationWizard,
    CRUDGenerationWizard,
    create_template_variable_wizard
)
from .exceptions import CommandError, ArgumentError
from ..generators import CRUDGenerator, APIGenerator, TestGenerator
from ..exceptions import TemplateError, ProjectError, ServiceError


class CreateCommand(Command):
    """Create new projects from templates."""
    
    def __init__(self):
        super().__init__(
            name="create",
            description="Create a new project from a template"
        )
    
    def _setup_arguments(self):
        """Setup command arguments."""
        self.add_argument(
            "name",
            help="Project name",
            type=str
        )
        
        self.add_option(
            "template",
            help="Template to use",
            short_name="t",
            type=str
        )
        
        self.add_option(
            "output",
            help="Output directory",
            short_name="o",
            type=str
        )
        
        self.add_option(
            "interactive",
            help="Use interactive wizard",
            short_name="i",
            action="store_true"
        )
        
        self.add_option(
            "overwrite",
            help="Overwrite existing directory",
            action="store_true"
        )
    
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute create command."""
        try:
            project_name = args.name
            output_path = Path(args.output) if args.output else Path.cwd() / project_name
            
            # Use interactive wizard if requested or no template specified
            if args.interactive or not args.template:
                context.print_info("Starting interactive project creation wizard...")
                
                wizard = ProjectCreationWizard()
                wizard_results = wizard.run(context)
                
                template_id = wizard_results.get('template', 'microservice')
                variables = wizard_results
                variables['project_name'] = project_name
                
            else:
                # Use specified template
                template_id = args.template
                variables = {
                    'project_name': project_name,
                    'description': f'{project_name} microservice project'
                }
            
            # Check if output directory exists
            if output_path.exists() and not args.overwrite:
                if not context.confirm(f"Directory '{output_path}' already exists. Overwrite?"):
                    return CommandResult(
                        success=False,
                        message="Project creation cancelled",
                        exit_code=1
                    )
            
            # Create project
            context.print_info(f"Creating project '{project_name}' using template '{template_id}'...")
            
            if context.dry_run:
                context.print_info("DRY RUN: Would create project with following configuration:")
                for key, value in variables.items():
                    context.print_info(f"  {key}: {value}")
                return CommandResult(
                    success=True,
                    message="Dry run completed successfully"
                )
            
            project = context.project_manager.create_project(
                name=project_name,
                template_id=template_id,
                variables=variables,
                output_path=output_path
            )
            
            return CommandResult(
                success=True,
                message=f"Project '{project_name}' created successfully at {output_path}",
                data={'project_path': str(output_path), 'project_name': project_name}
            )
            
        except TemplateError as e:
            return CommandResult(
                success=False,
                message=f"Template error: {e.message}",
                exit_code=1
            )
        except ProjectError as e:
            return CommandResult(
                success=False,
                message=f"Project creation failed: {e.message}",
                exit_code=1
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                exit_code=1
            )


class GenerateCommand(Command):
    """Generate code from templates and schemas."""
    
    def __init__(self):
        super().__init__(
            name="generate",
            description="Generate code from templates and schemas"
        )
    
    def _setup_arguments(self):
        """Setup command arguments."""
        self.add_argument(
            "type",
            help="Type of generation (crud, api, service, test)",
            choices=["crud", "api", "service", "test"]
        )
        
        self.add_argument(
            "name",
            help="Name of the item to generate"
        )
        
        self.add_option(
            "schema",
            help="Path to schema file",
            short_name="s",
            type=str
        )
        
        self.add_option(
            "output",
            help="Output directory",
            short_name="o",
            type=str
        )
        
        self.add_option(
            "template",
            help="Template to use",
            short_name="t",
            type=str
        )
        
        self.add_option(
            "interactive",
            help="Use interactive wizard",
            short_name="i",
            action="store_true"
        )
    
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute generate command."""
        try:
            generation_type = args.type
            name = args.name
            output_path = Path(args.output) if args.output else Path.cwd()
            
            if generation_type == "crud":
                return self._generate_crud(context, args, name, output_path)
            elif generation_type == "api":
                return self._generate_api(context, args, name, output_path)
            elif generation_type == "service":
                return self._generate_service(context, args, name, output_path)
            elif generation_type == "test":
                return self._generate_test(context, args, name, output_path)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown generation type: {generation_type}",
                    exit_code=1
                )
                
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Generation failed: {str(e)}",
                exit_code=1
            )
    
    def _generate_crud(self, context: CLIContext, args: argparse.Namespace, name: str, output_path: Path) -> CommandResult:
        """Generate CRUD operations."""
        if args.interactive:
            wizard = CRUDGenerationWizard()
            wizard_results = wizard.run(context)
            
            schema = {
                'name': wizard_results['model_name'],
                'fields': [
                    {'name': 'id', 'type': 'integer', 'required': True},
                    {'name': 'name', 'type': 'string', 'required': True},
                    {'name': 'description', 'type': 'string', 'required': False}
                ]
            }
            options = {
                'generate_tests': wizard_results.get('generate_tests', True),
                'database': wizard_results.get('database_type', 'postgresql')
            }
        else:
            # Use provided schema or create default
            if args.schema:
                import json
                with open(args.schema, 'r') as f:
                    schema = json.load(f)
            else:
                schema = {
                    'name': name,
                    'fields': [
                        {'name': 'id', 'type': 'integer', 'required': True},
                        {'name': 'name', 'type': 'string', 'required': True}
                    ]
                }
            options = {}
        
        generator = CRUDGenerator()
        result = generator.generate(schema, options)
        
        if not context.dry_run:
            result.write_to_directory(output_path)
        
        return CommandResult(
            success=True,
            message=f"CRUD operations for '{schema['name']}' generated successfully",
            data={'files_generated': len(result.files)}
        )
    
    def _generate_api(self, context: CLIContext, args: argparse.Namespace, name: str, output_path: Path) -> CommandResult:
        """Generate API from OpenAPI spec."""
        if not args.schema:
            return CommandResult(
                success=False,
                message="Schema file required for API generation",
                exit_code=1
            )
        
        import json
        import yaml
        
        schema_path = Path(args.schema)
        if schema_path.suffix.lower() in ['.yaml', '.yml']:
            with open(schema_path, 'r') as f:
                schema = yaml.safe_load(f)
        else:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
        
        generator = APIGenerator()
        result = generator.generate(schema)
        
        if not context.dry_run:
            result.write_to_directory(output_path)
        
        return CommandResult(
            success=True,
            message=f"API '{name}' generated successfully from {schema_path}",
            data={'files_generated': len(result.files)}
        )
    
    def _generate_service(self, context: CLIContext, args: argparse.Namespace, name: str, output_path: Path) -> CommandResult:
        """Generate service in current project."""
        # Check if we're in a project
        project = context.load_project()
        if not project:
            return CommandResult(
                success=False,
                message="Not in a project directory. Use 'create' command to create a new project first.",
                exit_code=1
            )
        
        if args.interactive:
            wizard = ServiceCreationWizard()
            wizard_results = wizard.run(context)
            
            service_name = wizard_results['service_name']
            template_id = wizard_results['template']
            variables = wizard_results
        else:
            service_name = name
            template_id = args.template or 'data-service'
            variables = {
                'service_name': service_name,
                'service_type': 'api',
                'port': 8000
            }
        
        service = context.service_manager.create_service(
            project=project,
            name=service_name,
            template_id=template_id,
            variables=variables
        )
        
        # Save project
        context.project_manager.save_project(project)
        
        return CommandResult(
            success=True,
            message=f"Service '{service_name}' added to project '{project.name}'",
            data={'service_name': service_name}
        )
    
    def _generate_test(self, context: CLIContext, args: argparse.Namespace, name: str, output_path: Path) -> CommandResult:
        """Generate test cases."""
        schema = {
            'type': 'unit',
            'target': name
        }
        
        generator = TestGenerator()
        result = generator.generate(schema)
        
        if not context.dry_run:
            result.write_to_directory(output_path)
        
        return CommandResult(
            success=True,
            message=f"Tests for '{name}' generated successfully",
            data={'files_generated': len(result.files)}
        )


class ListCommand(Command):
    """List available templates and project information."""
    
    def __init__(self):
        super().__init__(
            name="list",
            description="List templates, projects, and services"
        )
    
    def _setup_arguments(self):
        """Setup command arguments."""
        self.add_argument(
            "type",
            help="What to list (templates, services, projects)",
            choices=["templates", "services", "projects"],
            default="templates",
            nargs="?"
        )
        
        self.add_option(
            "category",
            help="Filter templates by category",
            short_name="c",
            type=str
        )
        
        self.add_option(
            "verbose",
            help="Show detailed information",
            short_name="v",
            action="store_true"
        )
    
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute list command."""
        try:
            list_type = args.type
            
            if list_type == "templates":
                return self._list_templates(context, args)
            elif list_type == "services":
                return self._list_services(context, args)
            elif list_type == "projects":
                return self._list_projects(context, args)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown list type: {list_type}",
                    exit_code=1
                )
                
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"List operation failed: {str(e)}",
                exit_code=1
            )
    
    def _list_templates(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """List available templates."""
        templates = context.template_engine.list_templates()
        
        if not templates:
            return CommandResult(
                success=True,
                message="No templates found"
            )
        
        context.print_info("Available Templates:")
        context.print_info("=" * 40)
        
        for template_id in templates:
            try:
                template = context.template_engine.get_template(template_id)
                
                print(f"📋 {template.name} ({template_id})")
                if args.verbose:
                    print(f"   Version: {template.version}")
                    print(f"   Author: {template.config.author}")
                    print(f"   Description: {template.config.description}")
                    print(f"   Category: {template.config.category.value}")
                    if template.config.variables:
                        print(f"   Variables: {len(template.config.variables)}")
                    print()
                
            except Exception as e:
                print(f"❌ {template_id}: Error loading template - {str(e)}")
        
        return CommandResult(
            success=True,
            message=f"Found {len(templates)} templates",
            data={'templates': templates}
        )
    
    def _list_services(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """List services in current project."""
        project = context.load_project()
        if not project:
            return CommandResult(
                success=False,
                message="Not in a project directory",
                exit_code=1
            )
        
        if not project.services:
            return CommandResult(
                success=True,
                message="No services found in project"
            )
        
        context.print_info(f"Services in '{project.name}':")
        context.print_info("=" * 40)
        
        for service in project.services:
            print(f"🔧 {service.name}")
            if args.verbose:
                print(f"   Type: {service.type}")
                print(f"   Template: {service.template_id}")
                print(f"   Port: {service.config.port}")
                if service.config.database:
                    print(f"   Database: {service.config.database}")
                if service.config.dependencies:
                    print(f"   Dependencies: {', '.join(service.config.dependencies)}")
                print()
        
        return CommandResult(
            success=True,
            message=f"Found {len(project.services)} services",
            data={'services': [s.name for s in project.services]}
        )
    
    def _list_projects(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """List recent projects."""
        # This would typically scan for projects in common locations
        # For now, just show current project if available
        
        project = context.load_project()
        if project:
            context.print_info("Current Project:")
            context.print_info("=" * 40)
            print(f"📁 {project.name}")
            if args.verbose:
                print(f"   Description: {project.config.description}")
                print(f"   Version: {project.config.version}")
                print(f"   Author: {project.config.author}")
                print(f"   Services: {len(project.services)}")
                print(f"   Path: {project.path}")
            
            return CommandResult(
                success=True,
                message="Current project information displayed"
            )
        else:
            return CommandResult(
                success=True,
                message="No project found in current directory"
            )


class ConfigCommand(Command):
    """Manage CLI configuration."""
    
    def __init__(self):
        super().__init__(
            name="config",
            description="Manage CLI configuration"
        )
    
    def _setup_arguments(self):
        """Setup command arguments."""
        self.add_argument(
            "action",
            help="Configuration action",
            choices=["get", "set", "list", "reset"]
        )
        
        self.add_argument(
            "key",
            help="Configuration key",
            nargs="?"
        )
        
        self.add_argument(
            "value",
            help="Configuration value",
            nargs="?"
        )
        
        self.add_option(
            "global",
            help="Use global configuration",
            short_name="g",
            action="store_true"
        )
    
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute config command."""
        try:
            action = args.action
            
            if action == "list":
                return self._list_config(context, args)
            elif action == "get":
                return self._get_config(context, args)
            elif action == "set":
                return self._set_config(context, args)
            elif action == "reset":
                return self._reset_config(context, args)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown config action: {action}",
                    exit_code=1
                )
                
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Config operation failed: {str(e)}",
                exit_code=1
            )
    
    def _list_config(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """List configuration values."""
        config = context.config
        
        context.print_info("Current Configuration:")
        context.print_info("=" * 40)
        
        print(f"Template Paths: {config.template_paths}")
        print(f"Cache Enabled: {config.cache_enabled}")
        print(f"Cache TTL: {config.cache_ttl}")
        print(f"Auto Update: {config.auto_update}")
        print(f"Default Author: {config.default_author}")
        print(f"Default License: {config.default_license}")
        
        return CommandResult(
            success=True,
            message="Configuration displayed"
        )
    
    def _get_config(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Get configuration value."""
        if not args.key:
            return CommandResult(
                success=False,
                message="Configuration key required",
                exit_code=1
            )
        
        config = context.config
        value = getattr(config, args.key.replace('-', '_'), None)
        
        if value is None:
            return CommandResult(
                success=False,
                message=f"Configuration key '{args.key}' not found",
                exit_code=1
            )
        
        print(f"{args.key}: {value}")
        
        return CommandResult(
            success=True,
            message=f"Configuration value for '{args.key}' displayed"
        )
    
    def _set_config(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Set configuration value."""
        if not args.key or not args.value:
            return CommandResult(
                success=False,
                message="Both key and value required",
                exit_code=1
            )
        
        config = context.config
        key = args.key.replace('-', '_')
        
        if not hasattr(config, key):
            return CommandResult(
                success=False,
                message=f"Configuration key '{args.key}' not found",
                exit_code=1
            )
        
        # Convert value to appropriate type
        current_value = getattr(config, key)
        if isinstance(current_value, bool):
            value = args.value.lower() in ['true', '1', 'yes', 'on']
        elif isinstance(current_value, int):
            value = int(args.value)
        elif isinstance(current_value, list):
            value = args.value.split(',')
        else:
            value = args.value
        
        setattr(config, key, value)
        
        # Save configuration
        config.save_to_file()
        
        return CommandResult(
            success=True,
            message=f"Configuration '{args.key}' set to '{value}'"
        )
    
    def _reset_config(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Reset configuration to defaults."""
        if context.confirm("Reset configuration to defaults?"):
            from ..config import CLIConfig
            default_config = CLIConfig()
            default_config.save_to_file()
            
            return CommandResult(
                success=True,
                message="Configuration reset to defaults"
            )
        else:
            return CommandResult(
                success=True,
                message="Configuration reset cancelled"
            )


class InitCommand(Command):
    """Initialize a new project in current directory."""
    
    def __init__(self):
        super().__init__(
            name="init",
            description="Initialize a new project in current directory"
        )
    
    def _setup_arguments(self):
        """Setup command arguments."""
        self.add_option(
            "template",
            help="Template to use",
            short_name="t",
            type=str
        )
        
        self.add_option(
            "interactive",
            help="Use interactive wizard",
            short_name="i",
            action="store_true"
        )
        
        self.add_option(
            "force",
            help="Force initialization in non-empty directory",
            short_name="f",
            action="store_true"
        )
    
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute init command."""
        try:
            current_dir = context.current_directory
            project_name = current_dir.name
            
            # Check if directory is empty
            if any(current_dir.iterdir()) and not args.force:
                if not context.confirm("Directory is not empty. Continue with initialization?"):
                    return CommandResult(
                        success=False,
                        message="Initialization cancelled",
                        exit_code=1
                    )
            
            # Use interactive wizard if requested
            if args.interactive or not args.template:
                context.print_info("Starting interactive project initialization...")
                
                wizard = ProjectCreationWizard()
                wizard_results = wizard.run(context)
                
                template_id = wizard_results.get('template', 'microservice')
                variables = wizard_results
                variables['project_name'] = project_name
                
            else:
                template_id = args.template
                variables = {
                    'project_name': project_name,
                    'description': f'{project_name} microservice project'
                }
            
            # Initialize project
            context.print_info(f"Initializing project '{project_name}' in current directory...")
            
            if context.dry_run:
                context.print_info("DRY RUN: Would initialize project with following configuration:")
                for key, value in variables.items():
                    context.print_info(f"  {key}: {value}")
                return CommandResult(
                    success=True,
                    message="Dry run completed successfully"
                )
            
            project = context.project_manager.create_project(
                name=project_name,
                template_id=template_id,
                variables=variables,
                output_path=current_dir
            )
            
            return CommandResult(
                success=True,
                message=f"Project '{project_name}' initialized successfully",
                data={'project_name': project_name}
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Initialization failed: {str(e)}",
                exit_code=1
            )
"""
Interactive Wizard System

Interactive wizards for complex CLI operations with step-by-step guidance.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re

from .context import CLIContext
from .exceptions import WizardError, ValidationError
from ..config import TemplateVariable, VariableType


@dataclass
class WizardStep:
    """Individual step in an interactive wizard."""
    
    name: str
    title: str
    description: str
    variable_name: Optional[str] = None
    input_type: str = 'text'  # text, choice, boolean, number, password
    choices: Optional[List[Any]] = None
    default: Any = None
    required: bool = True
    validation_pattern: Optional[str] = None
    validation_function: Optional[Callable[[Any], bool]] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if step should be executed based on context."""
        if self.condition:
            return self.condition(context)
        return True
    
    def validate_input(self, value: Any) -> bool:
        """Validate input value."""
        # Check required
        if self.required and (value is None or value == ""):
            return False
        
        # Check pattern
        if self.validation_pattern and isinstance(value, str):
            if not re.match(self.validation_pattern, value):
                return False
        
        # Check custom validation
        if self.validation_function:
            return self.validation_function(value)
        
        return True
    
    def get_input_prompt(self) -> str:
        """Get input prompt for step."""
        prompt = f"📝 {self.title}"
        
        if self.description:
            prompt += f"\n   {self.description}"
        
        if self.choices:
            prompt += "\n   Choices:"
            for i, choice in enumerate(self.choices, 1):
                prompt += f"\n     {i}. {choice}"
        
        if self.default is not None:
            prompt += f" (default: {self.default})"
        
        prompt += ": "
        return prompt


class InteractiveWizard:
    """Interactive wizard for step-by-step user input collection."""
    
    def __init__(self, name: str, title: str, description: str = ""):
        self.name = name
        self.title = title
        self.description = description
        self.steps: List[WizardStep] = []
        self.results: Dict[str, Any] = {}
    
    def add_step(self, step: WizardStep) -> None:
        """Add step to wizard."""
        self.steps.append(step)
    
    def add_text_step(self, name: str, title: str, description: str = "", **kwargs) -> None:
        """Add text input step."""
        step = WizardStep(
            name=name,
            title=title,
            description=description,
            variable_name=kwargs.get('variable_name', name),
            input_type='text',
            **kwargs
        )
        self.add_step(step)
    
    def add_choice_step(self, name: str, title: str, choices: List[Any], description: str = "", **kwargs) -> None:
        """Add choice selection step."""
        step = WizardStep(
            name=name,
            title=title,
            description=description,
            variable_name=kwargs.get('variable_name', name),
            input_type='choice',
            choices=choices,
            **kwargs
        )
        self.add_step(step)
    
    def add_boolean_step(self, name: str, title: str, description: str = "", **kwargs) -> None:
        """Add boolean (yes/no) step."""
        step = WizardStep(
            name=name,
            title=title,
            description=description,
            variable_name=kwargs.get('variable_name', name),
            input_type='boolean',
            **kwargs
        )
        self.add_step(step)
    
    def add_number_step(self, name: str, title: str, description: str = "", **kwargs) -> None:
        """Add number input step."""
        step = WizardStep(
            name=name,
            title=title,
            description=description,
            variable_name=kwargs.get('variable_name', name),
            input_type='number',
            **kwargs
        )
        self.add_step(step)
    
    def execute_step(self, step: WizardStep, context: CLIContext) -> Any:
        """Execute individual wizard step."""
        if not step.should_execute(self.results):
            return None
        
        while True:
            try:
                # Print step header
                print(f"\n{'='*60}")
                print(f"🧙 {self.title} - Step {len([s for s in self.steps if s.name in self.results]) + 1}/{len(self.steps)}")
                print(f"{'='*60}")
                
                # Get input based on type
                if step.input_type == 'choice':
                    value = self._get_choice_input(step)
                elif step.input_type == 'boolean':
                    value = self._get_boolean_input(step)
                elif step.input_type == 'number':
                    value = self._get_number_input(step)
                elif step.input_type == 'password':
                    value = self._get_password_input(step)
                else:
                    value = self._get_text_input(step)
                
                # Use default if no input and default available
                if (value == "" or value is None) and step.default is not None:
                    value = step.default
                
                # Validate input
                if not step.validate_input(value):
                    context.print_error("Invalid input. Please try again.")
                    continue
                
                return value
                
            except KeyboardInterrupt:
                raise WizardError(
                    wizard_name=self.name,
                    step_name=step.name,
                    error_message="Wizard cancelled by user"
                )
            except Exception as e:
                context.print_error(f"Error in step '{step.name}': {str(e)}")
                continue
    
    def _get_text_input(self, step: WizardStep) -> str:
        """Get text input from user."""
        prompt = step.get_input_prompt()
        return input(prompt).strip()
    
    def _get_choice_input(self, step: WizardStep) -> Any:
        """Get choice input from user."""
        prompt = step.get_input_prompt()
        
        while True:
            response = input(prompt).strip()
            
            if not response and step.default is not None:
                return step.default
            
            # Try to parse as number (1-based index)
            try:
                index = int(response) - 1
                if 0 <= index < len(step.choices):
                    return step.choices[index]
            except ValueError:
                pass
            
            # Try to match choice directly
            for choice in step.choices:
                if str(choice).lower() == response.lower():
                    return choice
            
            print("❌ Invalid choice. Please select a number or enter the choice directly.")
    
    def _get_boolean_input(self, step: WizardStep) -> bool:
        """Get boolean input from user."""
        prompt = step.get_input_prompt()
        if step.default is not None:
            suffix = " [Y/n]" if step.default else " [y/N]"
            prompt = prompt.rstrip(": ") + suffix + ": "
        
        response = input(prompt).strip().lower()
        
        if not response and step.default is not None:
            return step.default
        
        return response in ['y', 'yes', 'true', '1']
    
    def _get_number_input(self, step: WizardStep) -> Union[int, float]:
        """Get number input from user."""
        prompt = step.get_input_prompt()
        
        while True:
            response = input(prompt).strip()
            
            if not response and step.default is not None:
                return step.default
            
            try:
                # Try integer first
                if '.' not in response:
                    return int(response)
                else:
                    return float(response)
            except ValueError:
                print("❌ Please enter a valid number.")
    
    def _get_password_input(self, step: WizardStep) -> str:
        """Get password input from user."""
        import getpass
        prompt = step.get_input_prompt()
        return getpass.getpass(prompt)
    
    def run(self, context: CLIContext) -> Dict[str, Any]:
        """Run the complete wizard."""
        try:
            # Print wizard header
            print(f"\n{'🚀 ' + self.title + ' 🚀':^60}")
            if self.description:
                print(f"{self.description:^60}")
            print("=" * 60)
            
            # Execute steps
            for step in self.steps:
                if step.should_execute(self.results):
                    value = self.execute_step(step, context)
                    if step.variable_name:
                        self.results[step.variable_name] = value
            
            # Print summary
            print(f"\n{'✅ Wizard Complete! ✅':^60}")
            print("=" * 60)
            
            if context.verbose:
                print("📋 Collected Information:")
                for key, value in self.results.items():
                    print(f"   {key}: {value}")
            
            return self.results
            
        except Exception as e:
            if isinstance(e, WizardError):
                raise
            else:
                raise WizardError(
                    wizard_name=self.name,
                    step_name="unknown",
                    error_message=str(e)
                )


class ProjectCreationWizard(InteractiveWizard):
    """Wizard for creating new projects."""
    
    def __init__(self):
        super().__init__(
            name="project_creation",
            title="Project Creation Wizard",
            description="Create a new FastAPI microservices project"
        )
        self._setup_steps()
    
    def _setup_steps(self):
        """Setup wizard steps."""
        # Project name
        self.add_text_step(
            name="project_name",
            title="Project Name",
            description="Enter the name for your new project (lowercase, hyphens allowed)",
            validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$',
            required=True
        )
        
        # Project description
        self.add_text_step(
            name="description",
            title="Project Description",
            description="Brief description of your project",
            default="A FastAPI microservices project",
            required=False
        )
        
        # Template selection
        self.add_choice_step(
            name="template",
            title="Project Template",
            description="Choose a project template",
            choices=["microservice", "event-driven", "multi-tenant", "api-gateway"],
            default="microservice"
        )
        
        # Database selection
        self.add_choice_step(
            name="database",
            title="Database",
            description="Choose your primary database",
            choices=["postgresql", "mysql", "mongodb", "sqlite", "none"],
            default="postgresql"
        )
        
        # Message broker
        self.add_choice_step(
            name="message_broker",
            title="Message Broker",
            description="Choose a message broker (optional)",
            choices=["rabbitmq", "kafka", "redis", "none"],
            default="none",
            condition=lambda ctx: ctx.get("template") in ["event-driven", "multi-tenant"]
        )
        
        # Observability
        self.add_choice_step(
            name="observability",
            title="Observability Stack",
            description="Choose observability level",
            choices=["full", "basic", "custom", "none"],
            default="basic"
        )
        
        # Security level
        self.add_choice_step(
            name="security",
            title="Security Level",
            description="Choose security configuration",
            choices=["enterprise", "basic", "custom", "none"],
            default="basic"
        )
        
        # Author information
        self.add_text_step(
            name="author",
            title="Author Name",
            description="Your name or organization",
            required=False
        )
        
        # License
        self.add_choice_step(
            name="license",
            title="License",
            description="Choose a license for your project",
            choices=["MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Proprietary"],
            default="MIT"
        )


class ServiceCreationWizard(InteractiveWizard):
    """Wizard for adding services to projects."""
    
    def __init__(self):
        super().__init__(
            name="service_creation",
            title="Service Creation Wizard",
            description="Add a new service to your project"
        )
        self._setup_steps()
    
    def _setup_steps(self):
        """Setup wizard steps."""
        # Service name
        self.add_text_step(
            name="service_name",
            title="Service Name",
            description="Enter the name for your new service (lowercase, hyphens allowed)",
            validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$',
            required=True
        )
        
        # Service type
        self.add_choice_step(
            name="service_type",
            title="Service Type",
            description="Choose the type of service",
            choices=["api", "worker", "gateway", "auth", "data", "event", "monitoring"],
            default="api"
        )
        
        # Template selection
        self.add_choice_step(
            name="template",
            title="Service Template",
            description="Choose a service template",
            choices=["auth-service", "api-gateway", "data-service", "event-service", "monitoring-service"],
            default="data-service"
        )
        
        # Port number
        self.add_number_step(
            name="port",
            title="Service Port",
            description="Port number for the service",
            default=8000,
            validation_function=lambda x: 1000 <= x <= 65535
        )
        
        # Database
        self.add_choice_step(
            name="database",
            title="Database",
            description="Database for this service (optional)",
            choices=["postgresql", "mysql", "mongodb", "sqlite", "shared", "none"],
            default="shared"
        )
        
        # Dependencies
        self.add_text_step(
            name="dependencies",
            title="Service Dependencies",
            description="Comma-separated list of service dependencies (optional)",
            required=False
        )


class CRUDGenerationWizard(InteractiveWizard):
    """Wizard for generating CRUD operations."""
    
    def __init__(self):
        super().__init__(
            name="crud_generation",
            title="CRUD Generation Wizard",
            description="Generate CRUD operations for a model"
        )
        self._setup_steps()
    
    def _setup_steps(self):
        """Setup wizard steps."""
        # Model name
        self.add_text_step(
            name="model_name",
            title="Model Name",
            description="Enter the model name (PascalCase, e.g., User, Product)",
            validation_pattern=r'^[A-Z][a-zA-Z0-9]*$',
            required=True
        )
        
        # Generate tests
        self.add_boolean_step(
            name="generate_tests",
            title="Generate Tests",
            description="Generate test cases for CRUD operations?",
            default=True
        )
        
        # Database type
        self.add_choice_step(
            name="database_type",
            title="Database Type",
            description="Target database type",
            choices=["postgresql", "mysql", "mongodb", "sqlite"],
            default="postgresql"
        )
        
        # Include relationships
        self.add_boolean_step(
            name="include_relationships",
            title="Include Relationships",
            description="Include relationship handling in generated code?",
            default=False
        )


class ProjectWizard(ProjectCreationWizard):
    """Alias for ProjectCreationWizard for backward compatibility."""
    pass


def create_template_variable_wizard(variables: List[TemplateVariable]) -> InteractiveWizard:
    """Create wizard from template variables."""
    wizard = InteractiveWizard(
        name="template_variables",
        title="Template Configuration",
        description="Configure template variables"
    )
    
    for var in variables:
        step_kwargs = {
            'variable_name': var.name,
            'description': var.description,
            'default': var.default,
            'required': var.required
        }
        
        if var.validation_pattern:
            step_kwargs['validation_pattern'] = var.validation_pattern
        
        if var.type == VariableType.BOOLEAN:
            wizard.add_boolean_step(var.name, var.name.replace('_', ' ').title(), **step_kwargs)
        elif var.type == VariableType.INTEGER:
            wizard.add_number_step(var.name, var.name.replace('_', ' ').title(), **step_kwargs)
        elif var.choices:
            wizard.add_choice_step(
                var.name, 
                var.name.replace('_', ' ').title(), 
                choices=var.choices,
                **step_kwargs
            )
        else:
            wizard.add_text_step(var.name, var.name.replace('_', ' ').title(), **step_kwargs)
    
    return wizard
"""
FastAPI Microservices SDK - Templates Module

This module provides comprehensive template engine and code generation capabilities
for rapid microservice development.

Key Components:
- Template Engine: Core template processing and rendering
- Code Generators: Specialized generators for different code types
- CLI Tools: Command-line interface for template operations
- Project Manager: Project lifecycle management
"""

from .engine import TemplateEngine, Template, TemplateRenderer
from .generators import CRUDGenerator, APIGenerator, TestGenerator
from .manager import ProjectManager, ServiceManager
from .registry import TemplateManager, TemplateRegistry, TemplateInfo
from .cli import CLIFramework, Command, InteractiveWizard
from .exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    GenerationError
)

__all__ = [
    # Core Engine
    'TemplateEngine',
    'Template', 
    'TemplateRenderer',
    
    # Generators
    'CRUDGenerator',
    'APIGenerator',
    'TestGenerator',
    
    # Managers
    'ProjectManager',
    'ServiceManager',
    'TemplateManager',
    'TemplateRegistry',
    'TemplateInfo',
    
    # CLI Framework
    'CLIFramework',
    'Command',
    'InteractiveWizard',
    
    # Exceptions
    'TemplateError',
    'TemplateNotFoundError',
    'TemplateValidationError',
    'GenerationError'
]

__version__ = "1.0.0"
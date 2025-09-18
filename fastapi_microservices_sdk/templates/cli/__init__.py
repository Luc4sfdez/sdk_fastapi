"""
CLI Framework for FastAPI Microservices SDK Templates

Command-line interface framework with interactive wizards and comprehensive
command management for template operations.
"""

from .framework import CLIFramework, Command, CommandRegistry
from .commands import (
    CreateCommand,
    GenerateCommand,
    ListCommand,
    ConfigCommand,
    InitCommand
)
from .wizard import InteractiveWizard, WizardStep
from .context import CLIContext
from .exceptions import CLIError, CommandError, WizardError

__all__ = [
    # Core Framework
    'CLIFramework',
    'Command',
    'CommandRegistry',
    
    # Commands
    'CreateCommand',
    'GenerateCommand', 
    'ListCommand',
    'ConfigCommand',
    'InitCommand',
    
    # Interactive Components
    'InteractiveWizard',
    'WizardStep',
    'CLIContext',
    
    # Exceptions
    'CLIError',
    'CommandError',
    'WizardError'
]
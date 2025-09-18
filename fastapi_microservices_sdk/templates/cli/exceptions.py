"""
CLI Framework Exceptions

Custom exceptions for CLI operations and command execution.
"""

from typing import Optional, Dict, Any


class CLIError(Exception):
    """Base exception for CLI-related errors."""
    
    def __init__(self, message: str, exit_code: int = 1, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.details = details or {}


class CommandError(CLIError):
    """Raised when command execution fails."""
    
    def __init__(self, command_name: str, error_message: str, exit_code: int = 1):
        message = f"Command '{command_name}' failed: {error_message}"
        super().__init__(message, exit_code, {
            'command_name': command_name,
            'error_message': error_message
        })


class CommandNotFoundError(CLIError):
    """Raised when a requested command is not found."""
    
    def __init__(self, command_name: str, available_commands: Optional[list] = None):
        message = f"Command '{command_name}' not found"
        if available_commands:
            message += f". Available commands: {', '.join(available_commands)}"
        
        super().__init__(message, 1, {
            'command_name': command_name,
            'available_commands': available_commands or []
        })


class ArgumentError(CLIError):
    """Raised when command arguments are invalid."""
    
    def __init__(self, argument_name: str, error_message: str):
        message = f"Invalid argument '{argument_name}': {error_message}"
        super().__init__(message, 1, {
            'argument_name': argument_name,
            'error_message': error_message
        })


class WizardError(CLIError):
    """Raised when interactive wizard fails."""
    
    def __init__(self, wizard_name: str, step_name: str, error_message: str):
        message = f"Wizard '{wizard_name}' failed at step '{step_name}': {error_message}"
        super().__init__(message, 1, {
            'wizard_name': wizard_name,
            'step_name': step_name,
            'error_message': error_message
        })


class ValidationError(CLIError):
    """Raised when input validation fails."""
    
    def __init__(self, field_name: str, value: Any, validation_message: str):
        message = f"Validation failed for '{field_name}': {validation_message}"
        super().__init__(message, 1, {
            'field_name': field_name,
            'value': value,
            'validation_message': validation_message
        })
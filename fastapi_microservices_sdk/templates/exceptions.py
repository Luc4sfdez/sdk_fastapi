"""
Template System Exceptions

Custom exceptions for template engine and code generation operations.
"""

from typing import Optional, Dict, Any


class TemplateError(Exception):
    """Base exception for template-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TemplateNotFoundError(TemplateError):
    """Raised when a requested template cannot be found."""
    
    def __init__(self, template_id: str, search_paths: Optional[list] = None):
        message = f"Template '{template_id}' not found"
        if search_paths:
            message += f" in paths: {', '.join(search_paths)}"
        
        super().__init__(message, {
            'template_id': template_id,
            'search_paths': search_paths or []
        })


class TemplateValidationError(TemplateError):
    """Raised when template validation fails."""
    
    def __init__(self, template_id: str, validation_errors: list):
        message = f"Template '{template_id}' validation failed: {len(validation_errors)} errors"
        
        super().__init__(message, {
            'template_id': template_id,
            'validation_errors': validation_errors
        })


class TemplateRenderError(TemplateError):
    """Raised when template rendering fails."""
    
    def __init__(self, template_id: str, render_error: str, context: Optional[Dict[str, Any]] = None):
        message = f"Failed to render template '{template_id}': {render_error}"
        
        super().__init__(message, {
            'template_id': template_id,
            'render_error': render_error,
            'context': context or {}
        })


class GenerationError(TemplateError):
    """Raised when code generation fails."""
    
    def __init__(self, generator_type: str, error_message: str, context: Optional[Dict[str, Any]] = None):
        message = f"Code generation failed ({generator_type}): {error_message}"
        
        super().__init__(message, {
            'generator_type': generator_type,
            'error_message': error_message,
            'context': context or {}
        })


class ProjectError(TemplateError):
    """Raised when project operations fail."""
    
    def __init__(self, project_name: str, operation: str, error_message: str):
        message = f"Project '{project_name}' {operation} failed: {error_message}"
        
        super().__init__(message, {
            'project_name': project_name,
            'operation': operation,
            'error_message': error_message
        })


class ServiceError(TemplateError):
    """Raised when service operations fail."""
    
    def __init__(self, service_name: str, operation: str, error_message: str):
        message = f"Service '{service_name}' {operation} failed: {error_message}"
        
        super().__init__(message, {
            'service_name': service_name,
            'operation': operation,
            'error_message': error_message
        })


class ConfigurationError(TemplateError):
    """Raised when configuration validation fails."""
    
    def __init__(self, config_type: str, validation_errors: list):
        message = f"Configuration validation failed ({config_type}): {len(validation_errors)} errors"
        
        super().__init__(message, {
            'config_type': config_type,
            'validation_errors': validation_errors
        })
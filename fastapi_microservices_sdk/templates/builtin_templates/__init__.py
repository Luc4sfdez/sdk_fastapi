"""
Built-in Templates

Built-in templates for common microservice patterns.
"""

from .microservice import MicroserviceTemplate
from .auth_service import AuthServiceTemplate
from .api_gateway import APIGatewayTemplate
from .data_service import DataServiceTemplate

__all__ = [
    'MicroserviceTemplate',
    'AuthServiceTemplate',
    'APIGatewayTemplate', 
    'DataServiceTemplate'
]
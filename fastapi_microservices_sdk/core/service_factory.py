# fastapi-microservices-sdk/fastapi_microservices_sdk/core/service_factory.py 
"""
Service factory for creating configured microservice instances.
"""

import os
from typing import Optional, Dict, Any, Type

from .microservice import MicroserviceApp
from ..config import SDKConfig, get_config
from ..exceptions import ConfigurationError, ValidationError
from ..utils.validators import validate_service_name


class ServiceFactory:
    """
    Factory class for creating microservice instances with proper configuration.
    """
    
    @staticmethod
    def create_service(
        name: str,
        version: str = "1.0.0",
        description: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        config: Optional[SDKConfig] = None,
        service_type: str = "api",
        auto_register: bool = True,
        enable_docs: bool = True,
        **kwargs
    ) -> MicroserviceApp:
        """
        Create a new microservice instance.
        
        Args:
            name: Service name
            version: Service version
            description: Service description
            host: Host to bind to
            port: Port to bind to
            config: SDK configuration
            service_type: Type of service (api, worker, gateway, etc.)
            auto_register: Whether to auto-register with service discovery
            enable_docs: Whether to enable FastAPI docs
            **kwargs: Additional FastAPI arguments
            
        Returns:
            Configured MicroserviceApp instance
            
        Raises:
            ValidationError: If service name is invalid
            ConfigurationError: If configuration is invalid
        """
        # Validate service name
        if not validate_service_name(name):
            raise ValidationError(f"Invalid service name: {name}")
        
        # Get configuration
        if config is None:
            config = get_config()
        
        # Validate configuration
        config_issues = config.validate()
        if config_issues:
            raise ConfigurationError(f"Configuration issues: {', '.join(config_issues)}")
        
        # Determine host and port
        service_host = host or os.getenv('SERVICE_HOST') or config.default_host
        service_port = port or int(os.getenv('SERVICE_PORT', config.default_port))
        
        # Create service instance
        service = MicroserviceApp(
            service_name=name,
            version=version,
            description=description,
            host=service_host,
            port=service_port,
            config=config,
            auto_register=auto_register,
            enable_docs=enable_docs,
            **kwargs
        )
        
        # Add service type metadata
        service.service_type = service_type
        
        return service
    
    @staticmethod
    def create_api_service(
        name: str,
        version: str = "1.0.0",
        **kwargs
    ) -> MicroserviceApp:
        """Create an API microservice."""
        return ServiceFactory.create_service(
            name=name,
            version=version,
            service_type="api",
            **kwargs
        )
    
    @staticmethod
    def create_worker_service(
        name: str,
        version: str = "1.0.0",
        **kwargs
    ) -> MicroserviceApp:
        """Create a worker microservice (no docs by default)."""
        return ServiceFactory.create_service(
            name=name,
            version=version,
            service_type="worker",
            enable_docs=False,
            **kwargs
        )
    
    @staticmethod
    def create_gateway_service(
        name: str,
        version: str = "1.0.0",
        **kwargs
    ) -> MicroserviceApp:
        """Create a gateway microservice."""
        return ServiceFactory.create_service(
            name=name,
            version=version,
            service_type="gateway",
            **kwargs
        )
    
    @staticmethod
    def from_config_file(
        config_file: str,
        service_name: Optional[str] = None
    ) -> MicroserviceApp:
        """
        Create a service from a configuration file.
        
        Args:
            config_file: Path to configuration file
            service_name: Override service name from config
            
        Returns:
            Configured MicroserviceApp instance
        """
        config = SDKConfig.from_file(config_file)
        
        # Extract service configuration
        service_config = config.to_dict()
        name = service_name or service_config.get('service_name', 'unnamed-service')
        
        return ServiceFactory.create_service(
            name=name,
            config=config,
            **service_config
        )


# Convenience function for quick service creation
def create_service(
    name: str,
    version: str = "1.0.0",
    **kwargs
) -> MicroserviceApp:
    """
    Quick service creation function.
    
    Args:
        name: Service name
        version: Service version
        **kwargs: Additional arguments passed to ServiceFactory
        
    Returns:
        Configured MicroserviceApp instance
        
    Example:
        from fastapi_microservices_sdk import create_service
        
        app = create_service("user-service")
        
        @app.get("/users")
        async def get_users():
            return {"users": []}
    """
    return ServiceFactory.create_service(name=name, version=version, **kwargs)

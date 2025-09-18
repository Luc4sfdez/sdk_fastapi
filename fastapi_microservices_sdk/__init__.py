# fastapi-microservices-sdk/fastapi_microservices_sdk/__init__.py 
# fastapi-microservices-sdk/fastapi_microservices_sdk/__init__.py
"""
FastAPI Microservices SDK

A comprehensive SDK for building, managing, and deploying microservices with FastAPI.
Compatible with FastAPI Full-Stack Template.

Example usage:
    from fastapi_microservices_sdk import MicroserviceApp, create_service
    
    app = create_service("user-service")
    
    @app.get("/users")
    async def get_users():
        return {"users": []}
"""

from .version import __version__
from .core.microservice import MicroserviceApp
from .core.service_factory import ServiceFactory, create_service
from .core.service_registry import ServiceRegistry
from .config import SDKConfig

# Import key decorators
from .core.decorators.service_endpoint import service_endpoint
from .core.decorators.retry import retry
from .core.decorators.cache import cache

# Import middleware
from .core.middleware.service_discovery import ServiceDiscoveryMiddleware
from .core.middleware.load_balancer import LoadBalancerMiddleware
from .core.middleware.circuit_breaker import CircuitBreakerMiddleware
from .core.middleware.request_tracing import RequestTracingMiddleware

# Import communication clients
from .communication.http.client import HTTPServiceClient
from .communication.messaging.rabbitmq import RabbitMQClient

# Conditional import for Redis client
try:
    from .communication.messaging.redis_pubsub import RedisPubSubClient
except ImportError:
    RedisPubSubClient = None

# Import utilities
from .utils.validators import validate_service_name, validate_endpoint_path
from .utils.helpers import generate_service_id, get_service_info
from .exceptions import (
    SDKError,
    ServiceError,
    CommunicationError,
    DiscoveryError,
    ConfigurationError
)

# Package metadata
__title__ = "fastapi-microservices-sdk"
__author__ = "FastAPI Microservices Team"
__email__ = "team@fastapi-microservices.com"
__license__ = "MIT"
__copyright__ = "Copyright 2024 FastAPI Microservices Team"

# Version info tuple for programmatic access
VERSION_INFO = tuple(int(part) for part in __version__.split('.'))

# Main exports - what users import when they do "from fastapi_microservices_sdk import *"
__all__ = [
    # Version
    "__version__",
    "VERSION_INFO",
    
    # Core classes
    "MicroserviceApp",
    "ServiceFactory", 
    "ServiceRegistry",
    "SDKConfig",
    
    # Factory function
    "create_service",
    
    # Decorators
    "service_endpoint",
    "retry",
    "cache",
    
    # Middleware
    "ServiceDiscoveryMiddleware",
    "LoadBalancerMiddleware", 
    "CircuitBreakerMiddleware",
    "RequestTracingMiddleware",
    
    # Communication clients
    "HTTPServiceClient",
    "RabbitMQClient",
    "RedisPubSubClient",
    
    # Utilities
    "validate_service_name",
    "validate_endpoint_path", 
    "generate_service_id",
    "get_service_info",
    
    # Exceptions
    "SDKError",
    "ServiceError",
    "CommunicationError", 
    "DiscoveryError",
    "ConfigurationError",
]

# SDK initialization flag
_sdk_initialized = False

def initialize_sdk(config: SDKConfig = None) -> None:
    """
    Initialize the FastAPI Microservices SDK.
    
    This function sets up global configuration, logging, and
    other SDK-wide settings. It should be called once at the
    start of your application.
    
    Args:
        config: SDK configuration object. If None, default config is used.
        
    Example:
        from fastapi_microservices_sdk import initialize_sdk, SDKConfig
        
        config = SDKConfig(
            service_discovery_url="http://consul:8500",
            default_timeout=30,
            enable_tracing=True
        )
        initialize_sdk(config)
    """
    global _sdk_initialized
    
    if _sdk_initialized:
        return
        
    # Use default config if none provided
    if config is None:
        config = SDKConfig()
    
    # Set global config
    SDKConfig.set_global_config(config)
    
    # Initialize logging
    import logging
    logging.basicConfig(
        level=config.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Initialize service registry if enabled
    if config.auto_register_services:
        ServiceRegistry.initialize()
    
    _sdk_initialized = True

def get_sdk_info() -> dict:
    """
    Get information about the SDK installation and configuration.
    
    Returns:
        Dictionary containing SDK version, configuration, and status.
        
    Example:
        from fastapi_microservices_sdk import get_sdk_info
        
        info = get_sdk_info()
        print(f"SDK Version: {info['version']}")
        print(f"Initialized: {info['initialized']}")
    """
    config = SDKConfig.get_global_config()
    
    return {
        "version": __version__,
        "version_info": VERSION_INFO,
        "initialized": _sdk_initialized,
        "config": {
            "service_discovery_enabled": config.service_discovery_url is not None,
            "auto_register": config.auto_register_services,
            "default_timeout": config.default_timeout,
            "tracing_enabled": config.enable_tracing,
            "log_level": config.log_level,
        } if config else None,
        "available_features": {
            "http_client": True,
            "service_discovery": True,
            "load_balancing": True,
            "circuit_breaker": True,
            "request_tracing": True,
            "rabbitmq": True,
            "redis_pubsub": True,
        }
    }

# Convenience function for quick service creation
def quick_service(
    name: str,
    port: int = 8000,
    host: str = "0.0.0.0",
    auto_register: bool = True,
    enable_docs: bool = True
) -> MicroserviceApp:
    """
    Quickly create a microservice with sensible defaults.
    
    This is a convenience function that creates a service with
    common configuration options pre-set.
    
    Args:
        name: Service name
        port: Port to run the service on
        host: Host to bind to
        auto_register: Whether to auto-register with service discovery
        enable_docs: Whether to enable FastAPI docs
        
    Returns:
        Configured MicroserviceApp instance
        
    Example:
        from fastapi_microservices_sdk import quick_service
        
        app = quick_service("user-service", port=8001)
        
        @app.get("/users")
        async def get_users():
            return {"users": []}
            
        if __name__ == "__main__":
            app.run()
    """
    # Ensure SDK is initialized
    if not _sdk_initialized:
        initialize_sdk()
    
    # Create service with factory
    app = create_service(
        name=name,
        port=port,
        host=host,
        auto_register=auto_register,
        enable_docs=enable_docs
    )
    
    return app

# Auto-initialize with default config if imported directly
# This allows simple usage without explicit initialization
def _auto_initialize():
    """Auto-initialize SDK with default configuration."""
    try:
        initialize_sdk()
    except Exception:
        # Silent fail for auto-initialization
        # User can still call initialize_sdk() explicitly if needed
        pass

# Only auto-initialize if this module is imported, not if it's run as script
if __name__ != "__main__":
    _auto_initialize()
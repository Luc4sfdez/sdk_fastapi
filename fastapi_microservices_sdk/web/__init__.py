"""
Enhanced web interface for the FastAPI Microservices SDK.

Provides comprehensive web-based management for microservices including:
- Service lifecycle management
- Real-time monitoring and metrics
- Deployment management
- Configuration management
- Log management and streaming
- WebSocket real-time updates
- Authentication and authorization
"""

from .app import create_web_app, AdvancedWebApp, get_web_app
from .core.config import WebConfig, web_config
from .core.dependency_container import DependencyContainer
from .core.base_manager import BaseManager

__all__ = [
    "create_web_app",
    "AdvancedWebApp", 
    "get_web_app",
    "WebConfig",
    "web_config",
    "DependencyContainer",
    "BaseManager"
]
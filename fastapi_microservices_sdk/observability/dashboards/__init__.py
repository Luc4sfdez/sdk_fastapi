"""
FastAPI Microservices SDK - Dashboard and Visualization System

This module provides comprehensive dashboard and visualization capabilities for the observability system,
including real-time dashboards, custom dashboard builders, and advanced visualization components.

Key Features:
- Real-time dashboard streaming with live data updates
- Custom dashboard builder with drag-and-drop interface
- Dashboard templates for common use cases
- Role-based access control for dashboard viewing and editing
- Dashboard sharing and collaboration features
- Mobile-responsive dashboard layouts
- Dashboard alerting with visual indicators
- Advanced visualization types (heatmaps, topology, flow diagrams)
- Dashboard embedding capabilities for external applications
- Dashboard versioning and rollback capabilities
- Performance optimization for large datasets

Components:
- DashboardManager: Central dashboard management and coordination
- DashboardBuilder: Custom dashboard creation and editing
- VisualizationEngine: Advanced visualization rendering
- DashboardTemplates: Pre-built dashboard templates
- DashboardSecurity: Access control and permissions
- DashboardStreaming: Real-time data streaming
- DashboardExporter: Dashboard export and sharing
"""

from typing import Dict, List, Optional, Any, Union
import logging

from .manager import DashboardManager
from .builder import DashboardBuilder, DashboardConfig
from .visualization import VisualizationEngine
from .templates import DashboardTemplateManager, DashboardTemplate
from .security import DashboardSecurity, DashboardPermission
from .streaming import DashboardStreaming, StreamingConfig
from .exporter import DashboardExporter, ExportFormat
from .exceptions import (
    DashboardError,
    DashboardNotFoundError,
    DashboardPermissionError,
    DashboardConfigError,
    VisualizationError
)

# Version info
__version__ = "1.0.0"
__author__ = "FastAPI Microservices SDK Team"

# Module logger
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_DASHBOARD_CONFIG = {
    "streaming_enabled": True,
    "real_time_updates": True,
    "auto_refresh_interval": 30,
    "max_data_points": 1000,
    "cache_enabled": True,
    "cache_ttl": 300,
    "security_enabled": True,
    "export_enabled": True,
    "mobile_responsive": True,
    "theme": "default"
}

# Exported classes and functions
__all__ = [
    # Core classes
    "DashboardManager",
    "DashboardBuilder",
    "DashboardConfig",
    "VisualizationEngine",
    "VisualizationType",
    
    # Templates and security
    "DashboardTemplateManager",
    "DashboardTemplate",
    "DashboardSecurity",
    "DashboardPermission",
    
    # Streaming and export
    "DashboardStreaming",
    "StreamingConfig",
    "DashboardExporter",
    "ExportFormat",
    
    # Exceptions
    "DashboardError",
    "DashboardNotFoundError",
    "DashboardPermissionError",
    "DashboardConfigError",
    "VisualizationError",
    
    # Utilities
    "create_dashboard_manager",
    "configure_dashboard_system",
    "get_default_templates",
    
    # Constants
    "DEFAULT_DASHBOARD_CONFIG",
    "__version__"
]


def create_dashboard_manager(
    config: Optional[Dict[str, Any]] = None,
    enable_streaming: bool = True,
    enable_security: bool = True,
    enable_templates: bool = True
) -> DashboardManager:
    """
    Create and configure a dashboard manager with default settings.
    
    Args:
        config: Optional dashboard configuration
        enable_streaming: Enable real-time streaming
        enable_security: Enable dashboard security
        enable_templates: Enable dashboard templates
        
    Returns:
        Configured DashboardManager instance
        
    Example:
        ```python
        # Create dashboard manager with defaults
        dashboard_manager = create_dashboard_manager()
        
        # Create with custom config
        dashboard_manager = create_dashboard_manager({
            "auto_refresh_interval": 60,
            "max_data_points": 2000
        })
        ```
    """
    # Merge with default config
    final_config = DEFAULT_DASHBOARD_CONFIG.copy()
    if config:
        final_config.update(config)
    
    # Create manager
    manager = DashboardManager(DashboardConfig(**final_config))
    
    # Configure components
    if enable_streaming:
        streaming = DashboardStreaming(StreamingConfig(
            enabled=True,
            real_time_updates=final_config.get("real_time_updates", True),
            auto_refresh_interval=final_config.get("auto_refresh_interval", 30)
        ))
        manager.set_streaming(streaming)
    
    if enable_security:
        security = DashboardSecurity()
        manager.set_security(security)
    
    if enable_templates:
        templates = DashboardTemplateManager()
        manager.set_templates(templates)
    
    logger.info("Dashboard manager created successfully")
    return manager


def configure_dashboard_system(
    app: Any,
    config: Optional[Dict[str, Any]] = None,
    mount_path: str = "/dashboards"
) -> DashboardManager:
    """
    Configure dashboard system for FastAPI application.
    
    Args:
        app: FastAPI application instance
        config: Dashboard configuration
        mount_path: Path to mount dashboard endpoints
        
    Returns:
        Configured DashboardManager instance
        
    Example:
        ```python
        from fastapi import FastAPI
        from fastapi_microservices_sdk.observability.dashboards import configure_dashboard_system
        
        app = FastAPI()
        dashboard_manager = configure_dashboard_system(app)
        ```
    """
    # Create dashboard manager
    manager = create_dashboard_manager(config)
    
    # Mount dashboard routes
    from .routes import create_dashboard_routes
    dashboard_routes = create_dashboard_routes(manager)
    app.mount(mount_path, dashboard_routes)
    
    # Add startup/shutdown events
    @app.on_event("startup")
    async def startup_dashboards():
        await manager.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_dashboards():
        await manager.shutdown()
    
    logger.info(f"Dashboard system configured at {mount_path}")
    return manager


def get_default_templates() -> List[DashboardTemplate]:
    """
    Get list of default dashboard templates.
    
    Returns:
        List of default dashboard templates
        
    Example:
        ```python
        templates = get_default_templates()
        for template in templates:
            print(f"Template: {template.name} - {template.description}")
        ```
    """
    template_manager = DashboardTemplateManager()
    return template_manager.get_default_templates()


# Initialize module
logger.info(f"Dashboard and Visualization module initialized (v{__version__})")
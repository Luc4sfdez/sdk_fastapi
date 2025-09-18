"""
Enhanced FastAPI Web Interface for Microservices SDK

Advanced web application for creating, managing, monitoring, and deploying microservices
through a comprehensive browser interface.
"""

import logging
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import asyncio

from ..templates.registry import TemplateRegistry
from ..templates.manager import ServiceManager as LegacyServiceManager
from ..templates.engine import TemplateEngine

# Import new enhanced components
from .core.config import WebConfig, web_config
from .core.dependency_container import DependencyContainer
from .services.service_manager import ServiceManager
from .monitoring.monitoring_manager import MonitoringManager
from .deployment.deployment_manager import DeploymentManager
from .configuration.configuration_manager import ConfigurationManager
from .logs.log_manager import LogManager
from .websockets.websocket_manager import WebSocketManager
from .auth.auth_manager import AuthenticationManager
from .templates_mgmt.template_analytics import TemplateAnalytics
from .templates_mgmt.template_manager import TemplateManager
from .diagnostics.system_diagnostics_manager import SystemDiagnosticsManager
from .diagnostics.health_monitor import HealthMonitor
from .diagnostics.resource_monitor import ResourceMonitor
from .diagnostics.performance_analyzer import PerformanceAnalyzer

# Import API routers
from .api.services import router as services_router
from .api.monitoring import create_monitoring_router
from .api.deployment import router as deployment_router
from .api.configuration import router as configuration_router
from .api.logs import router as logs_router
from .api.templates import router as templates_router
from .api.docs import router as docs_router
from .api.system_health import router as system_health_router
from .api.auth import router as auth_router

# Import authentication components
from .auth.jwt_manager import JWTManager
from .auth.security_middleware import SecurityMiddleware


class AdvancedWebApp:
    """
    Advanced web application with comprehensive microservices management.
    
    Features:
    - Service lifecycle management
    - Real-time monitoring and metrics
    - Deployment management
    - Configuration management
    - Log management and streaming
    - WebSocket real-time updates
    - Authentication and authorization
    """
    
    def __init__(self, config: Optional[WebConfig] = None):
        """
        Initialize the advanced web application.
        
        Args:
            config: Optional web configuration
        """
        self.config = config or web_config
        self.logger = logging.getLogger("web.app")
        self.container = DependencyContainer()
        self.app: Optional[FastAPI] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """
        Initialize the web application and all managers.
        
        Returns:
            True if initialization successful
        """
        try:
            # Setup logging
            self.config.setup_logging()
            
            # Register dependencies
            self._register_dependencies()
            
            # Initialize all managers
            success = await self.container.initialize_managers()
            if not success:
                self.logger.error("Failed to initialize some managers")
                return False
            
            # Create FastAPI app
            self.app = self._create_fastapi_app()
            
            self._initialized = True
            self.logger.info("Advanced web application initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize web application: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the web application and cleanup resources.
        
        Returns:
            True if shutdown successful
        """
        try:
            if self.container:
                await self.container.shutdown_managers()
            
            self._initialized = False
            self.logger.info("Advanced web application shutdown successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to shutdown web application: {e}")
            return False
    
    def _register_dependencies(self) -> None:
        """Register all dependencies in the container."""
        # Register managers as singletons
        self.container.register_singleton(
            ServiceManager, 
            ServiceManager,
            config={"health_check_interval": 60}
        )
        
        self.container.register_singleton(
            MonitoringManager, 
            MonitoringManager,
            config={"metrics_retention_days": self.config.monitoring.metrics_retention_days}
        )
        
        self.container.register_singleton(
            DeploymentManager, 
            DeploymentManager,
            config={"supported_targets": ["docker", "kubernetes", "cloud"]}
        )
        
        self.container.register_singleton(
            ConfigurationManager, 
            ConfigurationManager,
            config={"validation_enabled": True}
        )
        
        self.container.register_singleton(
            LogManager, 
            LogManager,
            config={"retention_days": 30}
        )
        
        self.container.register_singleton(
            WebSocketManager, 
            WebSocketManager,
            config={
                "max_connections": self.config.websocket.max_connections,
                "heartbeat_interval": self.config.websocket.heartbeat_interval
            }
        )
        
        self.container.register_singleton(
            AuthenticationManager, 
            AuthenticationManager,
            config={
                "secret_key": self.config.security.secret_key,
                "jwt_algorithm": self.config.security.jwt_algorithm,
                "jwt_expiration_hours": self.config.security.jwt_expiration_hours
            }
        )
        
        self.container.register_singleton(
            TemplateAnalytics, 
            TemplateAnalytics,
            config={}
        )
        
        self.container.register_singleton(
            TemplateManager, 
            TemplateManager,
            config={"storage_path": "templates"}
        )
        
        self.container.register_singleton(
            SystemDiagnosticsManager, 
            SystemDiagnosticsManager,
            config={
                "health_check_interval": 30,
                "metrics_retention_hours": 24,
                "alert_thresholds": {
                    "cpu_percent": 80.0,
                    "memory_percent": 85.0,
                    "disk_percent": 90.0,
                    "response_time": 5.0
                }
            }
        )
        
        self.container.register_singleton(
            HealthMonitor, 
            HealthMonitor,
            config={}
        )
        
        self.container.register_singleton(
            ResourceMonitor, 
            ResourceMonitor,
            config={"history_size": 1000}
        )
        
        self.container.register_singleton(
            PerformanceAnalyzer, 
            PerformanceAnalyzer,
            config={"max_metrics": 10000}
        )
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="FastAPI Microservices SDK - Advanced Dashboard",
            description="Advanced web interface for comprehensive microservices management",
            version="2.0.0",
            debug=self.config.debug
        )
        
        # Setup templates and static files
        web_dir = Path(__file__).parent
        templates = Jinja2Templates(directory=str(web_dir / "templates"))
        
        # Mount static files
        static_dir = web_dir / "static"
        static_dir.mkdir(exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Setup authentication
        auth_manager = self.container.resolve(AuthenticationManager)
        jwt_manager = JWTManager(
            secret_key=self.config.security.secret_key,
            algorithm=self.config.security.jwt_algorithm,
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
        
        # Add security middleware
        security_middleware = SecurityMiddleware(
            jwt_manager=jwt_manager,
            auth_manager=auth_manager,
            excluded_paths=[
                "/docs", "/redoc", "/openapi.json",
                "/api/auth/login", "/api/auth/register",
                "/health", "/ping", "/", "/static"
            ]
        )
        app.middleware("http")(security_middleware)
        
        # Include API routers
        app.include_router(auth_router)  # Add auth router first
        app.include_router(services_router)
        monitoring_router = create_monitoring_router(self.container)
        app.include_router(monitoring_router)
        app.include_router(deployment_router)
        app.include_router(configuration_router)
        app.include_router(logs_router)
        app.include_router(templates_router)
        app.include_router(docs_router)
        app.include_router(system_health_router)
        
        # Initialize legacy components for backward compatibility
        registry = TemplateRegistry()
        template_engine = TemplateEngine()
        legacy_service_manager = LegacyServiceManager(template_engine)
        
        # Add startup and shutdown events
        @app.on_event("startup")
        async def startup_event():
            """Application startup event."""
            self.logger.info("FastAPI application starting up")
        
        @app.on_event("shutdown")
        async def shutdown_event():
            """Application shutdown event."""
            await self.shutdown()
            self.logger.info("FastAPI application shut down")
        
        # Authentication routes
        @app.get("/login", response_class=HTMLResponse)
        async def login_page(request: Request):
            """Login page."""
            return templates.TemplateResponse("login.html", {
                "request": request,
                "title": "Login - FastAPI Microservices SDK"
            })
        
        # Basic routes (legacy compatibility)
        @app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main dashboard."""
            templates_list = registry.list_templates()
            
            # Get service manager for enhanced features
            service_manager = self.container.resolve(ServiceManager)
            services = await service_manager.list_services()
            
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "templates": templates_list,
                "services": services,
                "title": "FastAPI Microservices SDK - Advanced Dashboard"
            })
        
        @app.get("/create", response_class=HTMLResponse)
        async def create_service_form(request: Request):
            """Service creation form."""
            templates_list = registry.list_templates()
            return templates.TemplateResponse("create_service.html", {
                "request": request,
                "templates": templates_list,
                "title": "Create New Service"
            })
        
        @app.get("/configuration", response_class=HTMLResponse)
        async def configuration_management(request: Request):
            """Configuration management interface."""
            return templates.TemplateResponse("configuration.html", {
                "request": request,
                "title": "Configuration Management"
            })
        
        @app.get("/logs", response_class=HTMLResponse)
        async def log_management(request: Request):
            """Log management interface."""
            return templates.TemplateResponse("logs.html", {
                "request": request,
                "title": "Log Management"
            })
        
        @app.get("/templates", response_class=HTMLResponse)
        async def template_management(request: Request):
            """Template management interface."""
            return templates.TemplateResponse("templates_mgmt.html", {
                "request": request,
                "title": "Template Management"
            })
        
        @app.get("/api-docs", response_class=HTMLResponse)
        async def api_documentation(request: Request):
            """API documentation interface."""
            return templates.TemplateResponse("api_docs.html", {
                "request": request,
                "title": "API Documentation"
            })
        
        @app.get("/system-health", response_class=HTMLResponse)
        async def system_health_dashboard(request: Request):
            """System health and diagnostics dashboard."""
            return templates.TemplateResponse("system_health.html", {
                "request": request,
                "title": "System Health & Diagnostics"
            })
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Application health check."""
            health_status = await self.container.health_check_managers()
            overall_health = all(health_status.values())
            
            return {
                "status": "healthy" if overall_health else "unhealthy",
                "managers": health_status,
                "timestamp": "2024-01-01T00:00:00Z"  # Will be replaced with actual timestamp
            }
        
        # System info endpoint
        @app.get("/info")
        async def system_info():
            """System information."""
            return {
                "application": "FastAPI Microservices SDK",
                "version": "2.0.0",
                "environment": self.config.environment.value,
                "features": {
                    "authentication": self.config.enable_authentication,
                    "websockets": self.config.enable_websockets,
                    "metrics": self.config.enable_metrics,
                    "deployment": self.config.enable_deployment,
                    "log_streaming": self.config.enable_log_streaming
                },
                "managers": self.container.get_registration_info()
            }
        
        return app
    
    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application instance.
        
        Returns:
            FastAPI application
            
        Raises:
            RuntimeError: If application not initialized
        """
        if not self._initialized or not self.app:
            raise RuntimeError("Web application not initialized. Call initialize() first.")
        
        return self.app
    
    def get_manager(self, manager_type: type):
        """
        Get a manager instance from the dependency container.
        
        Args:
            manager_type: Manager class type
            
        Returns:
            Manager instance
        """
        return self.container.resolve(manager_type)


# Global application instance
_web_app_instance: Optional[AdvancedWebApp] = None


async def get_web_app() -> AdvancedWebApp:
    """
    Get or create the global web application instance.
    
    Returns:
        AdvancedWebApp instance
    """
    global _web_app_instance
    
    if _web_app_instance is None:
        _web_app_instance = AdvancedWebApp()
        await _web_app_instance.initialize()
    
    return _web_app_instance


def create_web_app(config: Optional[WebConfig] = None) -> FastAPI:
    """
    Create and configure the web application (legacy compatibility).
    
    Args:
        config: Optional web configuration
        
    Returns:
        FastAPI application
    """
    # Create advanced web app
    advanced_app = AdvancedWebApp(config)
    
    # Initialize synchronously (for backward compatibility)
    # In production, this should be done asynchronously
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if not loop.is_running():
        loop.run_until_complete(advanced_app.initialize())
    else:
        # If loop is already running, create a task
        asyncio.create_task(advanced_app.initialize())
    
    return advanced_app.get_app()
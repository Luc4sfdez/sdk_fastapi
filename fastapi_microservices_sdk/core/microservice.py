# fastapi-microservices-sdk/fastapi_microservices_sdk/core/microservice.py 
"""
Core MicroserviceApp class that extends FastAPI with microservices capabilities.
"""

import asyncio
import logging
import uuid
from typing import Optional, Dict, Any, List, Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import SDKConfig, get_config
from ..constants import (
    HEALTH_CHECK_PATH, METRICS_PATH, SERVICE_NAME_HEADER,
    REQUEST_ID_HEADER, STATUS_HEALTHY, STATUS_UNHEALTHY
)
from ..exceptions import ServiceError, ConfigurationError


class MicroserviceApp(FastAPI):
    """
    Enhanced FastAPI application with microservices capabilities.
    
    This class extends FastAPI to provide built-in support for:
    - Service discovery
    - Health checks
    - Metrics collection
    - Request tracing
    - Inter-service communication
    """
    
    def __init__(
        self,
        service_name: str,
        version: str = "1.0.0",
        description: Optional[str] = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        config: Optional[SDKConfig] = None,
        auto_register: bool = True,
        enable_docs: bool = True,
        **kwargs
    ):
        """
        Initialize the microservice application.
        
        Args:
            service_name: Name of the microservice
            version: Service version
            description: Service description
            host: Host to bind to
            port: Port to bind to
            config: SDK configuration
            auto_register: Whether to auto-register with service discovery
            enable_docs: Whether to enable FastAPI docs
            **kwargs: Additional FastAPI arguments
        """
        self.service_name = service_name
        self.service_version = version
        self.service_id = f"{service_name}-{uuid.uuid4().hex[:8]}"
        self.host = host
        self.port = port
        self.config = config or get_config()
        self.auto_register = auto_register
        self._health_checks: List[Callable] = []
        self._startup_tasks: List[Callable] = []
        self._shutdown_tasks: List[Callable] = []
        
        # Configure FastAPI
        super().__init__(
            title=service_name,
            version=version,
            description=description or f"{service_name} microservice",
            docs_url="/docs" if enable_docs else None,
            redoc_url="/redoc" if enable_docs else None,
            lifespan=self._lifespan,
            **kwargs
        )
        
        self._setup_middleware()
        self._setup_default_routes()
        
        self.logger = logging.getLogger(f"microservice.{service_name}")
        self.logger.info(f"Initialized microservice: {service_name} v{version}")
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Handle application lifespan events."""
        # Startup
        self.logger.info(f"Starting microservice: {self.service_name}")
        
        # Run startup tasks
        for task in self._startup_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                self.logger.error(f"Startup task failed: {e}")
        
        # Register with service discovery if enabled
        if self.auto_register and self.config.enable_service_discovery:
            await self._register_service()
        
        self.logger.info(f"Microservice {self.service_name} started successfully")
        
        yield
        
        # Shutdown
        self.logger.info(f"Shutting down microservice: {self.service_name}")
        
        # Unregister from service discovery
        if self.auto_register and self.config.enable_service_discovery:
            await self._unregister_service()
        
        # Run shutdown tasks
        for task in self._shutdown_tasks:
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
            except Exception as e:
                self.logger.error(f"Shutdown task failed: {e}")
        
        self.logger.info(f"Microservice {self.service_name} shut down successfully")
    
    def _setup_middleware(self):
        """Setup default middleware."""
        # CORS middleware
        if self.config.security.cors_origins:
            self.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.security.cors_origins,
                allow_methods=self.config.security.cors_methods,
                allow_headers=self.config.security.cors_headers,
                allow_credentials=True,
            )
        
        # Request ID middleware
        @self.middleware("http")
        async def add_request_id(request: Request, call_next):
            request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
            request.state.request_id = request_id
            
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[SERVICE_NAME_HEADER] = self.service_name
            
            return response
    
    def _setup_default_routes(self):
        """Setup default routes for health checks and metrics."""
        
        @self.get(HEALTH_CHECK_PATH, tags=["Health"])
        async def health_check():
            """Health check endpoint."""
            health_status = {
                "service": self.service_name,
                "version": self.service_version,
                "status": STATUS_HEALTHY,
                "timestamp": asyncio.get_event_loop().time(),
                "checks": {}
            }
            
            # Run custom health checks
            overall_healthy = True
            for check in self._health_checks:
                try:
                    check_name = getattr(check, '__name__', 'unknown')
                    if asyncio.iscoroutinefunction(check):
                        result = await check()
                    else:
                        result = check()
                    
                    if isinstance(result, dict):
                        health_status["checks"][check_name] = result
                        if not result.get("healthy", True):
                            overall_healthy = False
                    else:
                        health_status["checks"][check_name] = {
                            "healthy": bool(result),
                            "message": str(result) if result else "OK"
                        }
                        if not result:
                            overall_healthy = False
                            
                except Exception as e:
                    health_status["checks"][check_name] = {
                        "healthy": False,
                        "error": str(e)
                    }
                    overall_healthy = False
            
            if not overall_healthy:
                health_status["status"] = STATUS_UNHEALTHY
                return JSONResponse(
                    status_code=503,
                    content=health_status
                )
            
            return health_status
        
        @self.get("/info", tags=["Info"])
        async def service_info():
            """Service information endpoint."""
            return {
                "service": self.service_name,
                "version": self.service_version,
                "service_id": self.service_id,
                "host": self.host,
                "port": self.port,
                "environment": self.config.environment,
                "sdk_version": "0.1.0"  # TODO: Get from version module
            }
    
    def add_health_check(self, check_func: Callable):
        """
        Add a custom health check function.
        
        Args:
            check_func: Function that returns True/False or dict with health info
        """
        self._health_checks.append(check_func)
    
    def add_startup_task(self, task: Callable):
        """Add a startup task."""
        self._startup_tasks.append(task)
    
    def add_shutdown_task(self, task: Callable):
        """Add a shutdown task."""
        self._shutdown_tasks.append(task)
    
    async def _register_service(self):
        """Register service with service discovery."""
        # TODO: Implement service registration
        self.logger.info(f"Service registration not yet implemented")
        pass
    
    async def _unregister_service(self):
        """Unregister service from service discovery."""
        # TODO: Implement service unregistration
        self.logger.info(f"Service unregistration not yet implemented")
        pass
    
    def run(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        reload: bool = False,
        **kwargs
    ):
        """
        Run the microservice.
        
        Args:
            host: Host to bind to (overrides instance host)
            port: Port to bind to (overrides instance port)
            reload: Enable auto-reload for development
            **kwargs: Additional uvicorn arguments
        """
        run_host = host or self.host
        run_port = port or self.port
        
        self.logger.info(f"Starting {self.service_name} on {run_host}:{run_port}")
        
        uvicorn.run(
            self,
            host=run_host,
            port=run_port,
            reload=reload,
            **kwargs
        )
    
    def get_service_url(self) -> str:
        """Get the service URL."""
        return f"http://{self.host}:{self.port}"
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            "name": self.service_name,
            "version": self.service_version,
            "service_id": self.service_id,
            "host": self.host,
            "port": self.port,
            "url": self.get_service_url(),
            "environment": self.config.environment
        }

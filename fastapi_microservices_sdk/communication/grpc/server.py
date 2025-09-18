"""
gRPC Server Integration with FastAPI.

This module provides enterprise-grade gRPC server implementation that can run
alongside FastAPI applications, with service discovery integration, health checks,
and comprehensive security features.
"""

import asyncio
import logging
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import asynccontextmanager
# Optional imports with graceful fallback
try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    from grpc_health.v1.health import HealthServicer
    GRPC_HEALTH_AVAILABLE = True
except ImportError:
    GRPC_HEALTH_AVAILABLE = False
    health_pb2 = None
    health_pb2_grpc = None
    HealthServicer = None

try:
    from grpc_reflection.v1alpha import reflection
    GRPC_REFLECTION_AVAILABLE = True
except ImportError:
    GRPC_REFLECTION_AVAILABLE = False
    reflection = None

import ssl
from pathlib import Path

from ..config import CommunicationConfig
from ..exceptions import CommunicationError, GRPCServerError
import logging
from ..discovery.base import ServiceInstance, ServiceStatus
from ..discovery.registry import EnhancedServiceRegistry

# Optional imports with graceful fallback
try:
    import grpcio_tools
    GRPCIO_TOOLS_AVAILABLE = True
except ImportError:
    GRPCIO_TOOLS_AVAILABLE = False

try:
    from grpc_interceptor import AsyncServerInterceptor
    GRPC_INTERCEPTOR_AVAILABLE = True
except ImportError:
    GRPC_INTERCEPTOR_AVAILABLE = False


logger = logging.getLogger(__name__)


class GRPCServerConfig:
    """Configuration for gRPC server."""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 50051,
        max_workers: int = 10,
        max_receive_message_length: int = 4 * 1024 * 1024,  # 4MB
        max_send_message_length: int = 4 * 1024 * 1024,  # 4MB
        enable_reflection: bool = True,
        enable_health_check: bool = True,
        enable_tls: bool = False,
        tls_cert_path: Optional[str] = None,
        tls_key_path: Optional[str] = None,
        tls_ca_cert_path: Optional[str] = None,
        require_client_cert: bool = False,
        service_name: str = "grpc-service",
        service_version: str = "1.0.0",
        enable_service_discovery: bool = True,
        graceful_shutdown_timeout: int = 30,
        **kwargs
    ):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.max_receive_message_length = max_receive_message_length
        self.max_send_message_length = max_send_message_length
        self.enable_reflection = enable_reflection
        self.enable_health_check = enable_health_check
        self.enable_tls = enable_tls
        self.tls_cert_path = tls_cert_path
        self.tls_key_path = tls_key_path
        self.tls_ca_cert_path = tls_ca_cert_path
        self.require_client_cert = require_client_cert
        self.service_name = service_name
        self.service_version = service_version
        self.enable_service_discovery = enable_service_discovery
        self.graceful_shutdown_timeout = graceful_shutdown_timeout
        
        # Additional options
        for key, value in kwargs.items():
            setattr(self, key, value)


class SecurityInterceptor:
    """Security interceptor for gRPC server."""
    
    def __init__(self, jwt_secret: Optional[str] = None, require_auth: bool = True):
        self.jwt_secret = jwt_secret
        self.require_auth = require_auth
        self.logger = logging.getLogger(f"{__name__}.SecurityInterceptor")
    
    async def intercept_service(self, continuation, handler_call_details):
        """Intercept gRPC calls for security validation."""
        try:
            # Extract metadata
            metadata = dict(handler_call_details.invocation_metadata)
            
            # Skip health check and reflection services
            method_name = handler_call_details.method
            if any(service in method_name for service in ['/grpc.health.v1.Health', '/grpc.reflection']):
                return await continuation(handler_call_details)
            
            # Validate authentication if required
            if self.require_auth:
                auth_header = metadata.get('authorization', '')
                if not auth_header.startswith('Bearer '):
                    self.logger.warning(f"Unauthorized gRPC call to {method_name}")
                    if GRPC_AVAILABLE:
                        raise grpc.RpcError(grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid authorization")
                    else:
                        raise Exception("Missing or invalid authorization")
                
                # TODO: Validate JWT token here
                # token = auth_header[7:]  # Remove 'Bearer ' prefix
                # validate_jwt_token(token, self.jwt_secret)
            
            # Add correlation ID
            correlation_id = metadata.get('x-correlation-id', f"grpc-{asyncio.current_task().get_name()}")
            
            self.logger.info(f"Processing gRPC call: {method_name}", extra={
                'correlation_id': correlation_id,
                'method': method_name,
                'client_ip': metadata.get('x-forwarded-for', 'unknown')
            })
            
            return await continuation(handler_call_details)
            
        except Exception as e:
            self.logger.error(f"Security interceptor error: {e}")
            if GRPC_AVAILABLE:
                raise grpc.RpcError(grpc.StatusCode.INTERNAL, "Internal security error")
            else:
                raise Exception("Internal security error")


class ObservabilityInterceptor:
    """Observability interceptor for metrics and tracing."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.ObservabilityInterceptor")
        self.request_count = 0
        self.error_count = 0
    
    async def intercept_service(self, continuation, handler_call_details):
        """Intercept gRPC calls for observability."""
        import time
        
        method_name = handler_call_details.method
        start_time = time.time()
        
        try:
            self.request_count += 1
            
            # Call the actual service method
            response = await continuation(handler_call_details)
            
            # Log successful request
            duration = time.time() - start_time
            self.logger.info(f"gRPC call completed: {method_name}", extra={
                'method': method_name,
                'duration_ms': round(duration * 1000, 2),
                'status': 'success'
            })
            
            return response
            
        except Exception as e:
            self.error_count += 1
            duration = time.time() - start_time
            
            self.logger.error(f"gRPC call failed: {method_name}", extra={
                'method': method_name,
                'duration_ms': round(duration * 1000, 2),
                'status': 'error',
                'error': str(e)
            })
            
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1)
        }


# Conditional class definition based on availability
if GRPC_HEALTH_AVAILABLE and HealthServicer is not None:
    class EnhancedHealthServicer(HealthServicer):
        """Enhanced health check servicer with custom health logic."""
        
        def __init__(self):
            super().__init__()
            self.logger = logging.getLogger(f"{__name__}.EnhancedHealthServicer")
            self._custom_health_checks: Dict[str, Callable[[], bool]] = {}
        
        def add_health_check(self, service_name: str, health_check_func: Callable[[], bool]):
            """Add a custom health check for a service."""
            self._custom_health_checks[service_name] = health_check_func
            self.logger.info(f"Added health check for service: {service_name}")
        
        async def Check(self, request, context):
            """Handle health check requests."""
            service_name = request.service
            
            try:
                # Check if we have a custom health check
                if service_name in self._custom_health_checks:
                    is_healthy = self._custom_health_checks[service_name]()
                    status = health_pb2.HealthCheckResponse.SERVING if is_healthy else health_pb2.HealthCheckResponse.NOT_SERVING
                else:
                    # Default to serving
                    status = health_pb2.HealthCheckResponse.SERVING
                
                self.logger.debug(f"Health check for {service_name}: {'SERVING' if status == health_pb2.HealthCheckResponse.SERVING else 'NOT_SERVING'}")
                
                return health_pb2.HealthCheckResponse(status=status)
                
            except Exception as e:
                self.logger.error(f"Health check error for {service_name}: {e}")
                return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.NOT_SERVING)
else:
    class EnhancedHealthServicer:
        """Mock health servicer when gRPC health is not available."""
        
        def __init__(self):
            self.logger = logging.getLogger(f"{__name__}.EnhancedHealthServicer")
            self._custom_health_checks: Dict[str, Callable[[], bool]] = {}
        
        def add_health_check(self, service_name: str, health_check_func: Callable[[], bool]):
            """Add a custom health check for a service."""
            self._custom_health_checks[service_name] = health_check_func
            self.logger.info(f"Added health check for service: {service_name} (mock)")
        
        async def Check(self, request, context):
            """Mock health check."""
            self.logger.warning("Health check called but gRPC health is not available")
            return None


class GRPCServerManager:
    """
    Enterprise-grade gRPC server manager with FastAPI integration.
    
    Features:
    - Co-hosting with FastAPI on different ports
    - Service discovery integration
    - Health checks and reflection
    - Security interceptors
    - Observability and metrics
    - Graceful shutdown
    - TLS/mTLS support
    """
    
    def __init__(
        self,
        config: Optional[GRPCServerConfig] = None,
        service_registry: Optional[EnhancedServiceRegistry] = None
    ):
        if not GRPC_AVAILABLE:
            raise ImportError(
                "gRPC dependencies are not available. "
                "Install with: pip install grpcio grpcio-tools grpcio-health-checking grpcio-reflection"
            )
        self.config = config or GRPCServerConfig()
        self.service_registry = service_registry
        self.logger = logging.getLogger(f"{__name__}.GRPCServerManager")
        
        # Server components
        self.server: Optional[aio.Server] = None
        self.health_servicer = EnhancedHealthServicer()
        self.security_interceptor = SecurityInterceptor()
        self.observability_interceptor = ObservabilityInterceptor()
        
        # State management
        self.is_running = False
        self.is_stopping = False
        self._shutdown_event = asyncio.Event()
        self._services: List[Any] = []
        self._service_instance: Optional[ServiceInstance] = None
        
        # Thread pool for blocking operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    def add_service(self, service_class, service_implementation):
        """Add a gRPC service to the server."""
        try:
            self._services.append((service_class, service_implementation))
            self.logger.info(f"Added gRPC service: {service_class.__name__}")
            
            # Add health check for the service
            service_name = getattr(service_implementation, 'SERVICE_NAME', service_class.__name__)
            if hasattr(service_implementation, 'health_check'):
                self.health_servicer.add_health_check(service_name, service_implementation.health_check)
            
        except Exception as e:
            self.logger.error(f"Failed to add service {service_class.__name__}: {e}")
            raise GRPCServerError(f"Failed to add service: {e}")
    
    def _create_ssl_credentials(self) -> Optional[Any]:
        """Create SSL credentials for TLS/mTLS."""
        if not self.config.enable_tls:
            return None
        
        try:
            # Read certificate files
            if not self.config.tls_cert_path or not self.config.tls_key_path:
                raise ValueError("TLS cert and key paths are required when TLS is enabled")
            
            cert_path = Path(self.config.tls_cert_path)
            key_path = Path(self.config.tls_key_path)
            
            if not cert_path.exists() or not key_path.exists():
                raise FileNotFoundError("TLS certificate or key file not found")
            
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            
            with open(key_path, 'rb') as f:
                key_data = f.read()
            
            # Read CA certificate if provided (for mTLS)
            ca_cert_data = None
            if self.config.tls_ca_cert_path:
                ca_cert_path = Path(self.config.tls_ca_cert_path)
                if ca_cert_path.exists():
                    with open(ca_cert_path, 'rb') as f:
                        ca_cert_data = f.read()
            
            # Create credentials
            if self.config.require_client_cert and ca_cert_data:
                # mTLS - require client certificates
                if GRPC_AVAILABLE:
                    credentials = grpc.ssl_server_credentials(
                        [(key_data, cert_data)],
                        root_certificates=ca_cert_data,
                        require_client_auth=True
                    )
                else:
                    credentials = None
                self.logger.info("Created mTLS server credentials")
            else:
                # Regular TLS
                if GRPC_AVAILABLE:
                    credentials = grpc.ssl_server_credentials([(key_data, cert_data)])
                else:
                    credentials = None
                self.logger.info("Created TLS server credentials")
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to create SSL credentials: {e}")
            raise GRPCServerError(f"SSL configuration error: {e}")
    
    async def _register_with_service_discovery(self):
        """Register the gRPC service with service discovery."""
        if not self.service_registry or not self.config.enable_service_discovery:
            return
        
        try:
            # Create service instance
            self._service_instance = ServiceInstance(
                service_name=self.config.service_name,
                instance_id=f"{self.config.service_name}-{self.config.host}-{self.config.port}",
                address=self.config.host,
                port=self.config.port,
                status=ServiceStatus.HEALTHY,
                metadata={
                    'version': self.config.service_version,
                    'protocol': 'grpc',
                    'tls_enabled': self.config.enable_tls,
                    'health_check_enabled': self.config.enable_health_check
                },
                tags={'grpc', 'microservice', f'version:{self.config.service_version}'}
            )
            
            # Register with service discovery
            await self.service_registry.register_service(self._service_instance)
            self.logger.info(f"Registered gRPC service with service discovery: {self.config.service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register with service discovery: {e}")
            # Don't fail startup if service discovery registration fails
    
    async def _deregister_from_service_discovery(self):
        """Deregister the gRPC service from service discovery."""
        if not self.service_registry or not self._service_instance:
            return
        
        try:
            await self.service_registry.deregister_service(
                self._service_instance.service_name,
                self._service_instance.instance_id
            )
            self.logger.info(f"Deregistered gRPC service from service discovery: {self.config.service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to deregister from service discovery: {e}")
    
    async def start(self) -> None:
        """Start the gRPC server."""
        if self.is_running:
            self.logger.warning("gRPC server is already running")
            return
        
        try:
            self.logger.info(f"Starting gRPC server on {self.config.host}:{self.config.port}")
            
            # Create server with interceptors
            interceptors = [
                self.security_interceptor.intercept_service,
                self.observability_interceptor.intercept_service
            ]
            
            if GRPC_AVAILABLE:
                self.server = aio.server(
                    interceptors=interceptors,
                    options=[
                        ('grpc.max_receive_message_length', self.config.max_receive_message_length),
                        ('grpc.max_send_message_length', self.config.max_send_message_length),
                        ('grpc.keepalive_time_ms', 30000),
                        ('grpc.keepalive_timeout_ms', 5000),
                        ('grpc.keepalive_permit_without_calls', True),
                        ('grpc.http2.max_pings_without_data', 0),
                        ('grpc.http2.min_time_between_pings_ms', 10000),
                        ('grpc.http2.min_ping_interval_without_data_ms', 300000)
                    ]
                )
            else:
                self.server = None
            
            # Add services
            for service_class, service_implementation in self._services:
                service_class.add_to_server(service_implementation, self.server)
                self.logger.info(f"Added service to server: {service_class.__name__}")
            
            # Add health check service
            if self.config.enable_health_check and GRPC_HEALTH_AVAILABLE:
                health_pb2_grpc.add_HealthServicer_to_server(self.health_servicer, self.server)
                self.logger.info("Added health check service")
            
            # Add reflection service
            if self.config.enable_reflection:
                service_names = [
                    service_class.DESCRIPTOR.services_by_name[list(service_class.DESCRIPTOR.services_by_name.keys())[0]].full_name
                    for service_class, _ in self._services
                ]
                if self.config.enable_health_check:
                    service_names.append(health_pb2.DESCRIPTOR.services_by_name['Health'].full_name)
                
                reflection.enable_server_reflection(service_names, self.server)
                self.logger.info("Added reflection service")
            
            # Configure TLS if enabled
            credentials = self._create_ssl_credentials()
            
            # Add port
            listen_addr = f"{self.config.host}:{self.config.port}"
            if credentials:
                self.server.add_secure_port(listen_addr, credentials)
                self.logger.info(f"Added secure port: {listen_addr}")
            else:
                self.server.add_insecure_port(listen_addr)
                self.logger.info(f"Added insecure port: {listen_addr}")
            
            # Start server
            await self.server.start()
            self.is_running = True
            
            # Register with service discovery
            await self._register_with_service_discovery()
            
            self.logger.info(f"gRPC server started successfully on {listen_addr}")
            
        except Exception as e:
            self.logger.error(f"Failed to start gRPC server: {e}")
            raise GRPCServerError(f"Server startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop the gRPC server gracefully."""
        if not self.is_running or self.is_stopping:
            return
        
        self.is_stopping = True
        self.logger.info("Stopping gRPC server...")
        
        try:
            # Deregister from service discovery first
            await self._deregister_from_service_discovery()
            
            # Stop accepting new requests
            if self.server:
                await self.server.stop(grace=self.config.graceful_shutdown_timeout)
                self.logger.info("gRPC server stopped gracefully")
            
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            self.is_running = False
            self.is_stopping = False
            self._shutdown_event.set()
            
        except Exception as e:
            self.logger.error(f"Error during gRPC server shutdown: {e}")
            raise GRPCServerError(f"Server shutdown failed: {e}")
    
    async def wait_for_termination(self) -> None:
        """Wait for the server to terminate."""
        if self.server:
            await self.server.wait_for_termination()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get server metrics."""
        return {
            'server_status': 'running' if self.is_running else 'stopped',
            'services_count': len(self._services),
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'tls_enabled': self.config.enable_tls,
                'health_check_enabled': self.config.enable_health_check,
                'reflection_enabled': self.config.enable_reflection
            },
            'observability': self.observability_interceptor.get_metrics()
        }
    
    @asynccontextmanager
    async def lifespan(self):
        """Context manager for server lifecycle."""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()


class FastAPIGRPCIntegration:
    """
    Integration helper for running FastAPI and gRPC servers together.
    
    This class provides utilities to run both FastAPI and gRPC servers
    in the same application with coordinated lifecycle management.
    """
    
    def __init__(
        self,
        fastapi_app,
        grpc_manager: GRPCServerManager,
        fastapi_host: str = "0.0.0.0",
        fastapi_port: int = 8000
    ):
        self.fastapi_app = fastapi_app
        self.grpc_manager = grpc_manager
        self.fastapi_host = fastapi_host
        self.fastapi_port = fastapi_port
        self.logger = logging.getLogger(f"{__name__}.FastAPIGRPCIntegration")
        
        # Add health endpoint to FastAPI
        self._add_health_endpoints()
    
    def _add_health_endpoints(self):
        """Add health check endpoints to FastAPI."""
        @self.fastapi_app.get("/health")
        async def health_check():
            """Combined health check for both FastAPI and gRPC."""
            grpc_metrics = self.grpc_manager.get_metrics()
            
            return {
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "services": {
                    "fastapi": {
                        "status": "running",
                        "host": self.fastapi_host,
                        "port": self.fastapi_port
                    },
                    "grpc": grpc_metrics
                }
            }
        
        @self.fastapi_app.get("/metrics")
        async def metrics():
            """Get metrics for both services."""
            return {
                "grpc": self.grpc_manager.get_metrics(),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def start_both_servers(self):
        """Start both FastAPI and gRPC servers."""
        try:
            # Start gRPC server
            await self.grpc_manager.start()
            
            # FastAPI server would be started separately by uvicorn
            # This method is mainly for coordination
            
            self.logger.info(f"Both servers configured - FastAPI: {self.fastapi_host}:{self.fastapi_port}, gRPC: {self.grpc_manager.config.host}:{self.grpc_manager.config.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start servers: {e}")
            await self.grpc_manager.stop()
            raise
    
    async def stop_both_servers(self):
        """Stop both servers gracefully."""
        try:
            await self.grpc_manager.stop()
            self.logger.info("Both servers stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping servers: {e}")
            raise


# Utility functions for common gRPC patterns

def create_grpc_server_config_from_communication_config(
    comm_config: CommunicationConfig,
    **overrides
) -> GRPCServerConfig:
    """Create gRPC server config from communication config."""
    grpc_config = comm_config.grpc if hasattr(comm_config, 'grpc') else {}
    
    return GRPCServerConfig(
        host=grpc_config.get('host', '0.0.0.0'),
        port=grpc_config.get('port', 50051),
        enable_tls=grpc_config.get('enable_tls', False),
        tls_cert_path=grpc_config.get('tls_cert_path'),
        tls_key_path=grpc_config.get('tls_key_path'),
        **overrides
    )


def setup_signal_handlers(grpc_manager: GRPCServerManager):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logging.getLogger(__name__).info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(grpc_manager.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
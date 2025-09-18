"""
gRPC Client with Service Discovery and Interceptors.

This module provides enterprise-grade gRPC client implementation with
service discovery integration, load balancing, security interceptors,
and comprehensive observability features.
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

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
    GRPC_HEALTH_AVAILABLE = True
except ImportError:
    GRPC_HEALTH_AVAILABLE = False
    health_pb2 = None
    health_pb2_grpc = None

from ..config import CommunicationConfig
from ..exceptions import (
    GRPCClientError, 
    GRPCConnectionError, 
    GRPCAuthenticationError,
    GRPCTimeoutError,
    ServiceNotFoundError
)
from ..discovery.base import ServiceInstance, ServiceStatus
from ..discovery.registry import EnhancedServiceRegistry
try:
    from ..http.advanced_policies import RetryStrategy
except ImportError:
    # Define RetryStrategy locally if not available
    class RetryStrategy(str, Enum):
        FIXED = "fixed"
        LINEAR = "linear"
        EXPONENTIAL = "exponential"

# Define CircuitBreakerState locally
class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for gRPC client."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    HEALTH_BASED = "health_based"


@dataclass
class GRPCEndpoint:
    """gRPC endpoint information."""
    host: str
    port: int
    weight: int = 1
    active_connections: int = 0
    is_healthy: bool = True
    last_health_check: Optional[float] = None
    response_time_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    
    @property
    def address(self) -> str:
        """Get the full address."""
        return f"{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.error_count
        return self.success_count / max(total, 1)


class GRPCClientConfig:
    """Configuration for gRPC client."""
    
    def __init__(
        self,
        service_name: str,
        # Connection settings
        timeout: float = 30.0,
        max_receive_message_length: int = 4 * 1024 * 1024,  # 4MB
        max_send_message_length: int = 4 * 1024 * 1024,  # 4MB
        # Load balancing
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        # Service discovery
        enable_service_discovery: bool = True,
        service_discovery_refresh_interval: float = 30.0,
        # Security
        enable_tls: bool = False,
        tls_ca_cert_path: Optional[str] = None,
        tls_client_cert_path: Optional[str] = None,
        tls_client_key_path: Optional[str] = None,
        jwt_token: Optional[str] = None,
        # Retry and circuit breaker
        enable_retry: bool = True,
        max_retry_attempts: int = 3,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        enable_circuit_breaker: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: float = 60.0,
        # Health checking
        enable_health_check: bool = True,
        health_check_interval: float = 30.0,
        health_check_timeout: float = 5.0,
        # Connection pooling
        max_connections_per_endpoint: int = 10,
        connection_idle_timeout: float = 300.0,
        # Observability
        enable_metrics: bool = True,
        enable_tracing: bool = True,
        **kwargs
    ):
        self.service_name = service_name
        self.timeout = timeout
        self.max_receive_message_length = max_receive_message_length
        self.max_send_message_length = max_send_message_length
        self.load_balancing_strategy = load_balancing_strategy
        self.enable_service_discovery = enable_service_discovery
        self.service_discovery_refresh_interval = service_discovery_refresh_interval
        self.enable_tls = enable_tls
        self.tls_ca_cert_path = tls_ca_cert_path
        self.tls_client_cert_path = tls_client_cert_path
        self.tls_client_key_path = tls_client_key_path
        self.jwt_token = jwt_token
        self.enable_retry = enable_retry
        self.max_retry_attempts = max_retry_attempts
        self.retry_strategy = retry_strategy
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breaker_failure_threshold = circuit_breaker_failure_threshold
        self.circuit_breaker_recovery_timeout = circuit_breaker_recovery_timeout
        self.enable_health_check = enable_health_check
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.max_connections_per_endpoint = max_connections_per_endpoint
        self.connection_idle_timeout = connection_idle_timeout
        self.enable_metrics = enable_metrics
        self.enable_tracing = enable_tracing
        
        # Additional options
        for key, value in kwargs.items():
            setattr(self, key, value)


class GRPCClientInterceptor:
    """Base class for gRPC client interceptors."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercept unary-unary calls."""
        return await continuation(client_call_details, request)
    
    async def intercept_unary_stream(self, continuation, client_call_details, request):
        """Intercept unary-stream calls."""
        return await continuation(client_call_details, request)
    
    async def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        """Intercept stream-unary calls."""
        return await continuation(client_call_details, request_iterator)
    
    async def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        """Intercept stream-stream calls."""
        return await continuation(client_call_details, request_iterator)


class AuthenticationInterceptor(GRPCClientInterceptor):
    """Authentication interceptor for gRPC client."""
    
    def __init__(self, jwt_token: Optional[str] = None):
        super().__init__("AuthenticationInterceptor")
        self.jwt_token = jwt_token
    
    def _add_auth_metadata(self, metadata):
        """Add authentication metadata."""
        if not metadata:
            metadata = []
        
        if self.jwt_token:
            metadata.append(('authorization', f'Bearer {self.jwt_token}'))
        
        return metadata
    
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        """Add authentication to unary-unary calls."""
        new_details = client_call_details._replace(
            metadata=self._add_auth_metadata(client_call_details.metadata)
        )
        return await continuation(new_details, request)
    
    async def intercept_unary_stream(self, continuation, client_call_details, request):
        """Add authentication to unary-stream calls."""
        new_details = client_call_details._replace(
            metadata=self._add_auth_metadata(client_call_details.metadata)
        )
        return await continuation(new_details, request)
    
    async def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        """Add authentication to stream-unary calls."""
        new_details = client_call_details._replace(
            metadata=self._add_auth_metadata(client_call_details.metadata)
        )
        return await continuation(new_details, request_iterator)
    
    async def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        """Add authentication to stream-stream calls."""
        new_details = client_call_details._replace(
            metadata=self._add_auth_metadata(client_call_details.metadata)
        )
        return await continuation(new_details, request_iterator)


class ObservabilityClientInterceptor(GRPCClientInterceptor):
    """Observability interceptor for gRPC client."""
    
    def __init__(self):
        super().__init__("ObservabilityClientInterceptor")
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
        self.method_metrics: Dict[str, Dict[str, Any]] = {}
    
    def _record_request(self, method: str, duration: float, success: bool):
        """Record request metrics."""
        self.request_count += 1
        self.total_duration += duration
        
        if not success:
            self.error_count += 1
        
        if method not in self.method_metrics:
            self.method_metrics[method] = {
                'count': 0,
                'errors': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0
            }
        
        metrics = self.method_metrics[method]
        metrics['count'] += 1
        metrics['total_duration'] += duration
        metrics['min_duration'] = min(metrics['min_duration'], duration)
        metrics['max_duration'] = max(metrics['max_duration'], duration)
        
        if not success:
            metrics['errors'] += 1
    
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercept and measure unary-unary calls."""
        method = client_call_details.method
        start_time = time.time()
        
        try:
            response = await continuation(client_call_details, request)
            duration = time.time() - start_time
            self._record_request(method, duration, True)
            
            self.logger.debug(f"gRPC call completed: {method}", extra={
                'method': method,
                'duration_ms': round(duration * 1000, 2),
                'status': 'success'
            })
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_request(method, duration, False)
            
            self.logger.error(f"gRPC call failed: {method}", extra={
                'method': method,
                'duration_ms': round(duration * 1000, 2),
                'status': 'error',
                'error': str(e)
            })
            
            raise
    
    async def intercept_unary_stream(self, continuation, client_call_details, request):
        """Intercept and measure unary-stream calls."""
        method = client_call_details.method
        start_time = time.time()
        
        try:
            response_iterator = await continuation(client_call_details, request)
            
            # Wrap the iterator to measure completion
            async def measured_iterator():
                try:
                    async for response in response_iterator:
                        yield response
                    
                    duration = time.time() - start_time
                    self._record_request(method, duration, True)
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_request(method, duration, False)
                    raise
            
            return measured_iterator()
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_request(method, duration, False)
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_duration = self.total_duration / max(self.request_count, 1)
        error_rate = self.error_count / max(self.request_count, 1)
        
        method_stats = {}
        for method, metrics in self.method_metrics.items():
            method_stats[method] = {
                'count': metrics['count'],
                'error_rate': metrics['errors'] / max(metrics['count'], 1),
                'avg_duration_ms': round((metrics['total_duration'] / max(metrics['count'], 1)) * 1000, 2),
                'min_duration_ms': round(metrics['min_duration'] * 1000, 2),
                'max_duration_ms': round(metrics['max_duration'] * 1000, 2)
            }
        
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': round(error_rate, 4),
            'avg_duration_ms': round(avg_duration * 1000, 2),
            'method_metrics': method_stats
        }


class CircuitBreakerInterceptor(GRPCClientInterceptor):
    """Circuit breaker interceptor for gRPC client."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        super().__init__("CircuitBreakerInterceptor")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on circuit breaker state."""
        current_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if current_time - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self):
        """Record successful request."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:  # Require 3 successes to close
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    def _record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
    
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        """Apply circuit breaker to unary-unary calls."""
        if not self._should_allow_request():
            raise GRPCClientError(
                f"Circuit breaker is {self.state.value} for service",
                context={'method': client_call_details.method, 'state': self.state.value}
            )
        
        try:
            response = await continuation(client_call_details, request)
            self._record_success()
            return response
        except Exception as e:
            self._record_failure()
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


class LoadBalancer:
    """Load balancer for gRPC endpoints."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.endpoints: List[GRPCEndpoint] = []
        self.current_index = 0
        self.logger = logging.getLogger(f"{__name__}.LoadBalancer")
    
    def add_endpoint(self, endpoint: GRPCEndpoint):
        """Add an endpoint to the load balancer."""
        self.endpoints.append(endpoint)
        self.logger.info(f"Added endpoint: {endpoint.address}")
    
    def remove_endpoint(self, address: str):
        """Remove an endpoint by address."""
        self.endpoints = [ep for ep in self.endpoints if ep.address != address]
        self.logger.info(f"Removed endpoint: {address}")
    
    def update_endpoints(self, service_instances: List[ServiceInstance]):
        """Update endpoints from service instances."""
        new_endpoints = []
        
        for instance in service_instances:
            if instance.status == ServiceStatus.HEALTHY:
                endpoint = GRPCEndpoint(
                    host=instance.address,
                    port=instance.port,
                    weight=instance.metadata.get('weight', 1),
                    is_healthy=True
                )
                new_endpoints.append(endpoint)
        
        # Preserve connection counts for existing endpoints
        endpoint_map = {ep.address: ep for ep in self.endpoints}
        for endpoint in new_endpoints:
            if endpoint.address in endpoint_map:
                existing = endpoint_map[endpoint.address]
                endpoint.active_connections = existing.active_connections
                endpoint.response_time_ms = existing.response_time_ms
                endpoint.error_count = existing.error_count
                endpoint.success_count = existing.success_count
        
        self.endpoints = new_endpoints
        self.logger.info(f"Updated endpoints: {[ep.address for ep in self.endpoints]}")
    
    def get_endpoint(self) -> Optional[GRPCEndpoint]:
        """Get next endpoint based on load balancing strategy."""
        healthy_endpoints = [ep for ep in self.endpoints if ep.is_healthy]
        
        if not healthy_endpoints:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin(healthy_endpoints)
        elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
            return self._health_based(healthy_endpoints)
        else:
            return self._round_robin(healthy_endpoints)
    
    def _round_robin(self, endpoints: List[GRPCEndpoint]) -> GRPCEndpoint:
        """Round robin selection."""
        if not endpoints:
            return None
        
        endpoint = endpoints[self.current_index % len(endpoints)]
        self.current_index += 1
        return endpoint
    
    def _random(self, endpoints: List[GRPCEndpoint]) -> GRPCEndpoint:
        """Random selection."""
        return random.choice(endpoints)
    
    def _least_connections(self, endpoints: List[GRPCEndpoint]) -> GRPCEndpoint:
        """Least connections selection."""
        return min(endpoints, key=lambda ep: ep.active_connections)
    
    def _weighted_round_robin(self, endpoints: List[GRPCEndpoint]) -> GRPCEndpoint:
        """Weighted round robin selection."""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return self._round_robin(endpoints)
        
        # Simple weighted selection
        weights = [ep.weight for ep in endpoints]
        return random.choices(endpoints, weights=weights)[0]
    
    def _health_based(self, endpoints: List[GRPCEndpoint]) -> GRPCEndpoint:
        """Health-based selection (prefer endpoints with better success rates)."""
        # Sort by success rate (descending) and response time (ascending)
        sorted_endpoints = sorted(
            endpoints,
            key=lambda ep: (-ep.success_rate, ep.response_time_ms)
        )
        return sorted_endpoints[0]
    
    def record_request_start(self, endpoint: GRPCEndpoint):
        """Record that a request started to an endpoint."""
        endpoint.active_connections += 1
    
    def record_request_end(self, endpoint: GRPCEndpoint, success: bool, duration_ms: float):
        """Record that a request ended."""
        endpoint.active_connections = max(0, endpoint.active_connections - 1)
        endpoint.response_time_ms = (endpoint.response_time_ms + duration_ms) / 2  # Moving average
        
        if success:
            endpoint.success_count += 1
        else:
            endpoint.error_count += 1


class GRPCClient:
    """
    Enterprise-grade gRPC client with service discovery and interceptors.
    
    Features:
    - Service discovery integration
    - Load balancing with multiple strategies
    - Circuit breaker pattern
    - Retry logic with exponential backoff
    - Security interceptors (JWT, mTLS)
    - Observability and metrics
    - Connection pooling
    - Health checking
    """
    
    def __init__(
        self,
        config: GRPCClientConfig,
        service_registry: Optional[EnhancedServiceRegistry] = None
    ):
        if not GRPC_AVAILABLE:
            raise ImportError(
                "gRPC dependencies are not available. "
                "Install with: pip install grpcio grpcio-tools grpcio-health-checking"
            )
        
        self.config = config
        self.service_registry = service_registry
        self.logger = logging.getLogger(f"{__name__}.GRPCClient")
        
        # Load balancer
        self.load_balancer = LoadBalancer(config.load_balancing_strategy)
        
        # Interceptors
        self.interceptors = []
        self._setup_interceptors()
        
        # Connection management
        self.channels: Dict[str, aio.Channel] = {}
        self.stubs: Dict[str, Any] = {}
        
        # State management
        self.is_running = False
        self._discovery_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.observability_interceptor: Optional[ObservabilityClientInterceptor] = None
        self.circuit_breaker: Optional[CircuitBreakerInterceptor] = None
    
    def _setup_interceptors(self):
        """Setup client interceptors."""
        # Authentication interceptor
        if self.config.jwt_token:
            auth_interceptor = AuthenticationInterceptor(self.config.jwt_token)
            self.interceptors.append(auth_interceptor)
        
        # Observability interceptor
        if self.config.enable_metrics:
            self.observability_interceptor = ObservabilityClientInterceptor()
            self.interceptors.append(self.observability_interceptor)
        
        # Circuit breaker interceptor
        if self.config.enable_circuit_breaker:
            self.circuit_breaker = CircuitBreakerInterceptor(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                recovery_timeout=self.config.circuit_breaker_recovery_timeout
            )
            self.interceptors.append(self.circuit_breaker)
    
    def _create_channel_credentials(self):
        """Create channel credentials for TLS."""
        if not self.config.enable_tls:
            return None
        
        try:
            # Read CA certificate
            ca_cert = None
            if self.config.tls_ca_cert_path:
                with open(self.config.tls_ca_cert_path, 'rb') as f:
                    ca_cert = f.read()
            
            # Read client certificate and key
            client_cert = None
            client_key = None
            if self.config.tls_client_cert_path and self.config.tls_client_key_path:
                with open(self.config.tls_client_cert_path, 'rb') as f:
                    client_cert = f.read()
                with open(self.config.tls_client_key_path, 'rb') as f:
                    client_key = f.read()
            
            # Create credentials
            if GRPC_AVAILABLE:
                if client_cert and client_key:
                    # mTLS
                    credentials = grpc.ssl_channel_credentials(
                        root_certificates=ca_cert,
                        private_key=client_key,
                        certificate_chain=client_cert
                    )
                    self.logger.info("Created mTLS channel credentials")
                else:
                    # Regular TLS
                    credentials = grpc.ssl_channel_credentials(root_certificates=ca_cert)
                    self.logger.info("Created TLS channel credentials")
            else:
                credentials = None
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to create channel credentials: {e}")
            raise GRPCClientError(f"TLS configuration error: {e}")
    
    async def _create_channel(self, endpoint: GRPCEndpoint) -> Any:
        """Create a gRPC channel for an endpoint."""
        address = endpoint.address
        
        if address in self.channels:
            return self.channels[address]
        
        try:
            # Channel options
            options = [
                ('grpc.max_receive_message_length', self.config.max_receive_message_length),
                ('grpc.max_send_message_length', self.config.max_send_message_length),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
            ]
            
            # Create channel
            credentials = self._create_channel_credentials()
            
            if GRPC_AVAILABLE:
                if credentials:
                    channel = aio.secure_channel(address, credentials, options=options)
                else:
                    channel = aio.insecure_channel(address, options=options)
            else:
                channel = None
            
            self.channels[address] = channel
            self.logger.info(f"Created gRPC channel: {address}")
            
            return channel
            
        except Exception as e:
            self.logger.error(f"Failed to create channel for {address}: {e}")
            raise GRPCConnectionError(f"Failed to connect to {address}: {e}")
    
    async def _discover_services(self):
        """Discover services using service registry."""
        if not self.service_registry or not self.config.enable_service_discovery:
            return
        
        try:
            instances = await self.service_registry.discover_services(self.config.service_name)
            self.load_balancer.update_endpoints(instances)
            
            self.logger.debug(f"Discovered {len(instances)} instances for {self.config.service_name}")
            
        except Exception as e:
            self.logger.error(f"Service discovery failed: {e}")
    
    async def _health_check_endpoints(self):
        """Perform health checks on endpoints."""
        if not self.config.enable_health_check or not GRPC_HEALTH_AVAILABLE:
            return
        
        for endpoint in self.load_balancer.endpoints:
            try:
                channel = await self._create_channel(endpoint)
                stub = health_pb2_grpc.HealthStub(channel)
                
                request = health_pb2.HealthCheckRequest(service=self.config.service_name)
                
                # Perform health check with timeout
                response = await asyncio.wait_for(
                    stub.Check(request),
                    timeout=self.config.health_check_timeout
                )
                
                is_healthy = response.status == health_pb2.HealthCheckResponse.SERVING
                endpoint.is_healthy = is_healthy
                endpoint.last_health_check = time.time()
                
                self.logger.debug(f"Health check for {endpoint.address}: {'healthy' if is_healthy else 'unhealthy'}")
                
            except Exception as e:
                endpoint.is_healthy = False
                endpoint.last_health_check = time.time()
                self.logger.warning(f"Health check failed for {endpoint.address}: {e}")
    
    async def _service_discovery_loop(self):
        """Background service discovery loop."""
        while self.is_running:
            try:
                await self._discover_services()
                await asyncio.sleep(self.config.service_discovery_refresh_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Service discovery loop error: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def _health_check_loop(self):
        """Background health check loop."""
        while self.is_running:
            try:
                await self._health_check_endpoints()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def start(self):
        """Start the gRPC client."""
        if self.is_running:
            self.logger.warning("gRPC client is already running")
            return
        
        try:
            self.logger.info(f"Starting gRPC client for service: {self.config.service_name}")
            
            # Initial service discovery
            await self._discover_services()
            
            # Start background tasks
            self.is_running = True
            
            if self.config.enable_service_discovery:
                self._discovery_task = asyncio.create_task(self._service_discovery_loop())
            
            if self.config.enable_health_check:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.logger.info("gRPC client started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start gRPC client: {e}")
            raise GRPCClientError(f"Client startup failed: {e}")
    
    async def stop(self):
        """Stop the gRPC client."""
        if not self.is_running:
            return
        
        self.logger.info("Stopping gRPC client...")
        self.is_running = False
        
        try:
            # Cancel background tasks
            if self._discovery_task:
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass
            
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Close channels
            for address, channel in self.channels.items():
                await channel.close()
                self.logger.debug(f"Closed channel: {address}")
            
            self.channels.clear()
            self.stubs.clear()
            
            self.logger.info("gRPC client stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error during gRPC client shutdown: {e}")
    
    def get_stub(self, stub_class):
        """Get or create a stub for the given stub class."""
        stub_name = stub_class.__name__
        
        if stub_name in self.stubs:
            return self.stubs[stub_name]
        
        # Get endpoint from load balancer
        endpoint = self.load_balancer.get_endpoint()
        if not endpoint:
            raise ServiceNotFoundError(f"No healthy endpoints available for {self.config.service_name}")
        
        try:
            # Create channel and stub
            channel = asyncio.create_task(self._create_channel(endpoint))
            stub = stub_class(channel.result())
            
            self.stubs[stub_name] = stub
            return stub
            
        except Exception as e:
            self.logger.error(f"Failed to create stub {stub_name}: {e}")
            raise GRPCClientError(f"Failed to create stub: {e}")
    
    async def call_unary_unary(self, stub_method, request, **kwargs):
        """Make a unary-unary gRPC call with retry logic."""
        endpoint = None
        
        for attempt in range(self.config.max_retry_attempts + 1):
            try:
                # Get endpoint
                endpoint = self.load_balancer.get_endpoint()
                if not endpoint:
                    raise ServiceNotFoundError(f"No healthy endpoints available for {self.config.service_name}")
                
                # Record request start
                self.load_balancer.record_request_start(endpoint)
                start_time = time.time()
                
                # Make the call
                response = await asyncio.wait_for(
                    stub_method(request, **kwargs),
                    timeout=self.config.timeout
                )
                
                # Record success
                duration_ms = (time.time() - start_time) * 1000
                self.load_balancer.record_request_end(endpoint, True, duration_ms)
                
                return response
                
            except Exception as e:
                # Record failure
                if endpoint:
                    duration_ms = (time.time() - start_time) * 1000
                    self.load_balancer.record_request_end(endpoint, False, duration_ms)
                
                # Check if we should retry
                if attempt < self.config.max_retry_attempts and self.config.enable_retry:
                    delay = self._calculate_retry_delay(attempt)
                    self.logger.warning(f"gRPC call failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                
                # Final failure
                self.logger.error(f"gRPC call failed after {attempt + 1} attempts: {e}")
                
                if isinstance(e, asyncio.TimeoutError):
                    raise GRPCTimeoutError(f"Request timed out after {self.config.timeout}s")
                else:
                    raise GRPCClientError(f"gRPC call failed: {e}")
        
        raise GRPCClientError("Maximum retry attempts exceeded")
    
    async def call_unary_stream(self, stub_method, request, **kwargs):
        """Make a unary-stream gRPC call."""
        endpoint = self.load_balancer.get_endpoint()
        if not endpoint:
            raise ServiceNotFoundError(f"No healthy endpoints available for {self.config.service_name}")
        
        try:
            self.load_balancer.record_request_start(endpoint)
            start_time = time.time()
            
            response_iterator = await stub_method(request, **kwargs)
            
            # Wrap iterator to record completion
            async def wrapped_iterator():
                try:
                    async for response in response_iterator:
                        yield response
                    
                    # Record success
                    duration_ms = (time.time() - start_time) * 1000
                    self.load_balancer.record_request_end(endpoint, True, duration_ms)
                    
                except Exception as e:
                    # Record failure
                    duration_ms = (time.time() - start_time) * 1000
                    self.load_balancer.record_request_end(endpoint, False, duration_ms)
                    raise
            
            return wrapped_iterator()
            
        except Exception as e:
            self.logger.error(f"gRPC streaming call failed: {e}")
            raise GRPCClientError(f"gRPC streaming call failed: {e}")
    
    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate retry delay based on strategy."""
        if self.config.retry_strategy == RetryStrategy.FIXED:
            return self.config.base_delay
        elif self.config.retry_strategy == RetryStrategy.LINEAR:
            return self.config.base_delay * (attempt + 1)
        elif self.config.retry_strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
            # Add jitter
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
            return min(delay, self.config.max_delay)
        else:
            return self.config.base_delay
    
    def add_endpoint(self, host: str, port: int, weight: int = 1):
        """Manually add an endpoint."""
        endpoint = GRPCEndpoint(host=host, port=port, weight=weight)
        self.load_balancer.add_endpoint(endpoint)
        self.logger.info(f"Added manual endpoint: {host}:{port}")
    
    def remove_endpoint(self, host: str, port: int):
        """Manually remove an endpoint."""
        address = f"{host}:{port}"
        self.load_balancer.remove_endpoint(address)
        
        # Close channel if exists
        if address in self.channels:
            asyncio.create_task(self.channels[address].close())
            del self.channels[address]
        
        self.logger.info(f"Removed endpoint: {address}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics."""
        metrics = {
            'client_status': 'running' if self.is_running else 'stopped',
            'service_name': self.config.service_name,
            'config': {
                'timeout': self.config.timeout,
                'enable_tls': self.config.enable_tls,
                'enable_retry': self.config.enable_retry,
                'max_retry_attempts': self.config.max_retry_attempts,
                'enable_circuit_breaker': self.config.enable_circuit_breaker,
                'enable_health_check': self.config.enable_health_check
            },
            'endpoints': [
                {
                    'address': ep.address,
                    'weight': ep.weight,
                    'is_healthy': ep.is_healthy,
                    'active_connections': ep.active_connections,
                    'success_rate': ep.success_rate,
                    'response_time_ms': ep.response_time_ms
                }
                for ep in self.load_balancer.endpoints
            ],
            'load_balancing_strategy': self.config.load_balancing_strategy.value
        }
        
        if self.observability_interceptor:
            metrics['observability'] = self.observability_interceptor.get_metrics()
        
        if self.circuit_breaker:
            metrics['circuit_breaker'] = self.circuit_breaker.get_state()
        
        return metrics


# Utility functions

def create_grpc_client_config_from_communication_config(
    comm_config: CommunicationConfig,
    service_name: str,
    **overrides
) -> GRPCClientConfig:
    """Create gRPC client config from communication config."""
    grpc_config = getattr(comm_config, 'grpc', {})
    
    return GRPCClientConfig(
        service_name=service_name,
        timeout=grpc_config.get('timeout', 30.0),
        enable_tls=grpc_config.get('enable_tls', False),
        tls_ca_cert_path=grpc_config.get('tls_ca_cert_path'),
        tls_client_cert_path=grpc_config.get('tls_client_cert_path'),
        tls_client_key_path=grpc_config.get('tls_client_key_path'),
        **overrides
    )


async def create_grpc_client(
    service_name: str,
    config: Optional[GRPCClientConfig] = None,
    service_registry: Optional[EnhancedServiceRegistry] = None
) -> GRPCClient:
    """Create and start a gRPC client."""
    if config is None:
        config = GRPCClientConfig(service_name=service_name)
    
    client = GRPCClient(config=config, service_registry=service_registry)
    await client.start()
    return client
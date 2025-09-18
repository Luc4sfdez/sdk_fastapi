#!/usr/bin/env python3
"""
Enhanced HTTP Client with Advanced Policies Integration.

This module integrates the Enhanced HTTP Client with advanced retry policies
and load balancing strategies for enterprise-grade HTTP communication.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager

import httpx
from pydantic import BaseModel, Field

from .enhanced_client import (
    EnhancedHTTPClient as BaseEnhancedHTTPClient,
    EnhancedHTTPClientConfig,
    HTTPMethod,
    AuthenticationType,
    HTTPMetrics as BaseHTTPMetrics
)
from .advanced_policies import (
    AdvancedRetryPolicy,
    RetryStrategy,
    TimeoutConfig,
    LoadBalancerConfig,
    LoadBalancingStrategy,
    ServiceEndpoint,
    EndpointHealth,
    create_load_balancer,
    LoadBalancer,
    LoggingInterceptor,
    MetricsInterceptor,
    ConnectionPoolOptimizer,
    RequestInterceptor,
    ResponseInterceptor
)
from ..logging import CommunicationLogger
from ..exceptions import (
    CommunicationError,
    CommunicationTimeoutError,
    CommunicationConnectionError
)


class EnhancedHTTPClientAdvancedConfig(BaseModel):
    """Enhanced HTTP client configuration with advanced policies."""
    
    # Base configuration
    base_url: Optional[str] = None  # Can be None when using load balancer
    service_urls: List[str] = Field(default_factory=list)  # Multiple URLs for load balancing
    
    # Timeout configuration
    timeout: TimeoutConfig = Field(default_factory=TimeoutConfig)
    
    # Advanced retry policy
    retry_policy: AdvancedRetryPolicy = Field(default_factory=AdvancedRetryPolicy)
    
    # Load balancer configuration
    load_balancer: LoadBalancerConfig = Field(default_factory=LoadBalancerConfig)
    
    # Connection pool optimization
    max_connections: int = Field(default=100, ge=1)
    max_keepalive_connections: int = Field(default=20, ge=1)
    keepalive_expiry: float = Field(default=5.0, gt=0)
    
    # Security
    verify_ssl: bool = Field(default=True)
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    # Headers and user agent
    default_headers: Dict[str, str] = Field(default_factory=dict)
    user_agent: str = Field(default="FastAPI-Microservices-SDK-Advanced/1.0")
    
    # Interceptors
    enable_logging_interceptor: bool = Field(default=True)
    enable_metrics_interceptor: bool = Field(default=True)
    
    # Health checks
    enable_health_checks: bool = Field(default=True)
    
    class Config:
        arbitrary_types_allowed = True


class AdvancedHTTPMetrics(BaseHTTPMetrics):
    """Extended HTTP metrics with advanced policy information."""
    
    def __init__(self):
        super().__init__()
        self.retry_attempts: int = 0
        self.load_balancer_selections: Dict[str, int] = {}
        self.endpoint_failures: Dict[str, int] = {}
        self.circuit_breaker_activations: int = 0
    
    def record_retry_attempt(self, endpoint_url: str):
        """Record a retry attempt."""
        self.retry_attempts += 1
        self.endpoint_failures[endpoint_url] = self.endpoint_failures.get(endpoint_url, 0) + 1
    
    def record_endpoint_selection(self, endpoint_url: str):
        """Record endpoint selection by load balancer."""
        self.load_balancer_selections[endpoint_url] = self.load_balancer_selections.get(endpoint_url, 0) + 1
    
    def record_circuit_breaker_activation(self):
        """Record circuit breaker activation."""
        self.circuit_breaker_activations += 1
    
    def get_advanced_metrics(self) -> Dict[str, Any]:
        """Get advanced metrics including policy information."""
        base_metrics = {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': self.cache_hit_rate,
            'average_response_time': self.average_response_time,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None
        }
        
        advanced_metrics = {
            'retry_attempts': self.retry_attempts,
            'load_balancer_selections': self.load_balancer_selections.copy(),
            'endpoint_failures': self.endpoint_failures.copy(),
            'circuit_breaker_activations': self.circuit_breaker_activations
        }
        
        return {**base_metrics, **advanced_metrics}


class EnhancedHTTPClientWithPolicies:
    """
    Enhanced HTTP Client with advanced retry policies and load balancing.
    
    This client provides enterprise-grade HTTP communication with:
    - Advanced retry policies (exponential, linear, fibonacci, custom)
    - Multiple load balancing strategies
    - Comprehensive health checking
    - Request/response interceptors
    - Connection pool optimization
    - Detailed metrics and monitoring
    """
    
    def __init__(
        self,
        config: EnhancedHTTPClientAdvancedConfig,
        logger: Optional[CommunicationLogger] = None
    ):
        self.config = config
        self.logger = logger or CommunicationLogger("enhanced_http_client_advanced")
        
        # Initialize components
        self._client: Optional[httpx.AsyncClient] = None
        self._load_balancer: Optional[LoadBalancer] = None
        self._metrics = AdvancedHTTPMetrics()
        
        # Interceptors
        self._request_interceptors: List[RequestInterceptor] = []
        self._response_interceptors: List[ResponseInterceptor] = []
        
        # Initialize built-in interceptors
        if config.enable_logging_interceptor:
            self._request_interceptors.append(LoggingInterceptor(self.logger))
            self._response_interceptors.append(LoggingInterceptor(self.logger))
        
        if config.enable_metrics_interceptor:
            self._metrics_interceptor = MetricsInterceptor()
            self._request_interceptors.append(self._metrics_interceptor)
            self._response_interceptors.append(self._metrics_interceptor)
        
        # Connection pool optimizer
        self._pool_optimizer = ConnectionPoolOptimizer(
            max_connections=config.max_connections,
            max_keepalive_connections=config.max_keepalive_connections,
            keepalive_expiry=config.keepalive_expiry
        )
        
        # State
        self._is_connected = False
        self._setup_load_balancer()
    
    def _setup_load_balancer(self):
        """Setup load balancer with configured endpoints."""
        if self.config.service_urls:
            # Multiple URLs - use load balancer
            self._load_balancer = create_load_balancer(
                self.config.load_balancer.strategy,
                self.config.load_balancer,
                self.logger
            )
            
            # Add all service URLs as endpoints
            for url in self.config.service_urls:
                endpoint = self._load_balancer.add_endpoint(url)
                endpoint.update_health(EndpointHealth.HEALTHY)  # Assume healthy initially
            
            self.logger.info(f"Load balancer configured with {len(self.config.service_urls)} endpoints")
        
        elif self.config.base_url:
            # Single URL - create simple load balancer with one endpoint
            self._load_balancer = create_load_balancer(
                LoadBalancingStrategy.ROUND_ROBIN,
                self.config.load_balancer,
                self.logger
            )
            
            endpoint = self._load_balancer.add_endpoint(self.config.base_url)
            endpoint.update_health(EndpointHealth.HEALTHY)
        
        else:
            raise ValueError("Either base_url or service_urls must be provided")
    
    async def connect(self):
        """Initialize HTTP client connection."""
        if self._is_connected:
            return
        
        try:
            # Create optimized connection limits
            limits = self._pool_optimizer.create_limits()
            
            # Create timeout configuration
            timeout = self.config.timeout.to_httpx_timeout()
            
            # SSL configuration
            verify = self.config.verify_ssl
            cert = None
            if self.config.ssl_cert_path and self.config.ssl_key_path:
                cert = (self.config.ssl_cert_path, self.config.ssl_key_path)
            
            # Default headers
            headers = {
                "User-Agent": self.config.user_agent,
                **self.config.default_headers
            }
            
            # Create HTTP client
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                verify=verify,
                cert=cert,
                headers=headers
            )
            
            # Start health checks if enabled
            if self.config.enable_health_checks and self._load_balancer:
                await self._load_balancer.start_health_checks()
            
            self._is_connected = True
            self.logger.info("Enhanced HTTP client with advanced policies connected")
            
        except Exception as e:
            self.logger.error(f"Failed to connect HTTP client: {e}")
            raise CommunicationConnectionError(f"HTTP client connection failed: {e}")
    
    async def disconnect(self):
        """Close HTTP client connection."""
        if not self._is_connected:
            return
        
        try:
            # Stop health checks
            if self._load_balancer:
                await self._load_balancer.stop_health_checks()
            
            # Close HTTP client
            if self._client:
                await self._client.aclose()
                self._client = None
            
            self._is_connected = False
            self.logger.info("Enhanced HTTP client disconnected")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting HTTP client: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected and self._client is not None
    
    def add_request_interceptor(self, interceptor: RequestInterceptor):
        """Add custom request interceptor."""
        self._request_interceptors.append(interceptor)
    
    def add_response_interceptor(self, interceptor: ResponseInterceptor):
        """Add custom response interceptor."""
        self._response_interceptors.append(interceptor)
    
    async def request(
        self,
        method: Union[str, HTTPMethod],
        path: str = "/",
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        retry_policy: Optional[AdvancedRetryPolicy] = None
    ) -> httpx.Response:
        """
        Make HTTP request with advanced retry policies and load balancing.
        
        Args:
            method: HTTP method
            path: Request path (relative to selected endpoint)
            params: Query parameters
            json: JSON data to send
            data: Raw data to send
            headers: Additional headers
            timeout: Request timeout override
            retry_policy: Override retry policy for this request
            
        Returns:
            HTTP response
            
        Raises:
            CommunicationError: On request failure
            CommunicationTimeoutError: On timeout
            CommunicationConnectionError: On connection failure
        """
        if not self.is_connected:
            await self.connect()
        
        if not self._load_balancer:
            raise CommunicationError("No load balancer configured")
        
        method_str = method.value if isinstance(method, HTTPMethod) else method.upper()
        policy = retry_policy or self.config.retry_policy
        
        # Execute request with retry policy
        return await self._execute_request_with_advanced_retry(
            method_str, path, params, json, data, headers, timeout, policy
        )
    
    async def _execute_request_with_advanced_retry(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]],
        json: Optional[Any],
        data: Optional[Any],
        headers: Optional[Dict[str, str]],
        timeout: Optional[float],
        retry_policy: AdvancedRetryPolicy
    ) -> httpx.Response:
        """Execute request with advanced retry policy."""
        last_exception = None
        
        for attempt in range(1, retry_policy.max_attempts + 1):
            try:
                # Select endpoint using load balancer
                endpoint = await self._load_balancer.select_endpoint()
                self._metrics.record_endpoint_selection(endpoint.url)
                
                # Build full URL
                full_url = f"{endpoint.url.rstrip('/')}/{path.lstrip('/')}"
                
                # Execute single request
                start_time = time.time()
                response = await self._execute_single_request_with_interceptors(
                    method, full_url, params, json, data, headers, timeout, endpoint, attempt
                )
                
                response_time = time.time() - start_time
                
                # Check if response indicates success
                if response.is_success:
                    # Record success
                    self._metrics.record_request(True, response_time)
                    endpoint.record_request_end(True, response_time)
                    
                    self.logger.debug(f"Request successful: {method} {full_url}", metadata={
                        'status_code': response.status_code,
                        'response_time': response_time,
                        'attempt': attempt,
                        'endpoint': endpoint.url
                    })
                    
                    return response
                
                # Check if we should retry
                elif retry_policy.should_retry(attempt, status_code=response.status_code):
                    self._metrics.record_retry_attempt(endpoint.url)
                    endpoint.record_request_end(False, response_time)
                    
                    if attempt < retry_policy.max_attempts:
                        delay = retry_policy.calculate_delay(attempt)
                        self.logger.warning(f"Request failed, retrying in {delay:.2f}s", metadata={
                            'method': method,
                            'url': full_url,
                            'status_code': response.status_code,
                            'attempt': attempt,
                            'delay': delay
                        })
                        await asyncio.sleep(delay)
                        continue
                
                # Don't retry - return response or raise error
                self._metrics.record_request(False, response_time)
                endpoint.record_request_end(False, response_time)
                
                if response.status_code == 401:
                    raise CommunicationError("Authentication failed")
                elif response.status_code == 429:
                    raise CommunicationError("Rate limit exceeded")
                else:
                    raise CommunicationError(f"HTTP {response.status_code}: {response.text}")
            
            except (httpx.TimeoutException, asyncio.TimeoutError) as e:
                last_exception = CommunicationTimeoutError(f"Request timeout: {e}")
                self._metrics.record_retry_attempt(endpoint.url if 'endpoint' in locals() else 'unknown')
                
            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = CommunicationConnectionError(f"Connection error: {e}")
                self._metrics.record_retry_attempt(endpoint.url if 'endpoint' in locals() else 'unknown')
                
            except Exception as e:
                last_exception = CommunicationError(f"Request failed: {e}")
                self._metrics.record_retry_attempt(endpoint.url if 'endpoint' in locals() else 'unknown')
            
            # Check if we should retry on exception
            if retry_policy.should_retry(attempt, exception=last_exception):
                if attempt < retry_policy.max_attempts:
                    delay = retry_policy.calculate_delay(attempt)
                    self.logger.warning(f"Request failed with exception, retrying in {delay:.2f}s", metadata={
                        'method': method,
                        'path': path,
                        'attempt': attempt,
                        'delay': delay,
                        'error': str(last_exception)
                    })
                    await asyncio.sleep(delay)
                    continue
            
            # No more retries
            break
        
        # All retries exhausted
        self._metrics.record_request(False, 0.0)
        self.logger.error(f"Request failed after {retry_policy.max_attempts} attempts", metadata={
            'method': method,
            'path': path,
            'final_error': str(last_exception)
        })
        
        raise last_exception or CommunicationError("Request failed after all retries")
    
    async def _execute_single_request_with_interceptors(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json: Optional[Any],
        data: Optional[Any],
        headers: Optional[Dict[str, str]],
        timeout: Optional[float],
        endpoint: ServiceEndpoint,
        attempt: int
    ) -> httpx.Response:
        """Execute single request with interceptor pipeline."""
        if not self._client:
            raise CommunicationConnectionError("HTTP client not connected")
        
        # Build request
        request = self._client.build_request(
            method=method,
            url=url,
            params=params,
            json=json,
            data=data,
            headers=headers,
            timeout=timeout
        )
        
        # Process request interceptors
        for interceptor in self._request_interceptors:
            request = await interceptor.intercept_request(request, endpoint, attempt)
        
        # Record request start
        endpoint.record_request_start()
        request_start_time = time.time()
        
        try:
            # Send request
            response = await self._client.send(request)
            
            # Process response interceptors
            for interceptor in self._response_interceptors:
                response = await interceptor.intercept_response(response, endpoint, request_start_time)
            
            return response
        
        except Exception:
            # Ensure we clean up connection count on error
            endpoint.active_connections = max(0, endpoint.active_connections - 1)
            raise
    
    # Convenience methods
    async def get(self, path: str = "/", **kwargs) -> httpx.Response:
        """Make GET request."""
        return await self.request(HTTPMethod.GET, path, **kwargs)
    
    async def post(self, path: str = "/", **kwargs) -> httpx.Response:
        """Make POST request."""
        return await self.request(HTTPMethod.POST, path, **kwargs)
    
    async def put(self, path: str = "/", **kwargs) -> httpx.Response:
        """Make PUT request."""
        return await self.request(HTTPMethod.PUT, path, **kwargs)
    
    async def patch(self, path: str = "/", **kwargs) -> httpx.Response:
        """Make PATCH request."""
        return await self.request(HTTPMethod.PATCH, path, **kwargs)
    
    async def delete(self, path: str = "/", **kwargs) -> httpx.Response:
        """Make DELETE request."""
        return await self.request(HTTPMethod.DELETE, path, **kwargs)
    
    # Health and monitoring
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            if not self.is_connected:
                return {
                    'status': 'unhealthy',
                    'error': 'Client not connected',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Check load balancer health
            healthy_endpoints = self._load_balancer.get_healthy_endpoints() if self._load_balancer else []
            total_endpoints = len(self._load_balancer.endpoints) if self._load_balancer else 0
            
            if not healthy_endpoints:
                return {
                    'status': 'unhealthy',
                    'error': 'No healthy endpoints available',
                    'total_endpoints': total_endpoints,
                    'healthy_endpoints': 0,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Try a simple request to one of the healthy endpoints
            try:
                start_time = time.time()
                response = await self.request(HTTPMethod.HEAD, "/", timeout=5.0)
                response_time = time.time() - start_time
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'total_endpoints': total_endpoints,
                    'healthy_endpoints': len(healthy_endpoints),
                    'load_balancer_strategy': self.config.load_balancer.strategy.value,
                    'metrics': self.get_metrics(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                return {
                    'status': 'degraded',
                    'error': str(e),
                    'total_endpoints': total_endpoints,
                    'healthy_endpoints': len(healthy_endpoints),
                    'metrics': self.get_metrics(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': f"Health check failed: {e}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        metrics = self._metrics.get_advanced_metrics()
        
        # Add load balancer metrics
        if self._load_balancer:
            endpoint_metrics = []
            for endpoint in self._load_balancer.endpoints:
                endpoint_metrics.append({
                    'url': endpoint.url,
                    'health': endpoint.health.value,
                    'weight': endpoint.weight,
                    'active_connections': endpoint.active_connections,
                    'total_requests': endpoint.total_requests,
                    'success_rate': endpoint.success_rate,
                    'average_response_time': endpoint.average_response_time,
                    'consecutive_failures': endpoint.consecutive_failures,
                    'circuit_breaker_open': endpoint.circuit_breaker_open
                })
            
            metrics['load_balancer'] = {
                'strategy': self.config.load_balancer.strategy.value,
                'total_endpoints': len(self._load_balancer.endpoints),
                'healthy_endpoints': len(self._load_balancer.get_healthy_endpoints()),
                'endpoints': endpoint_metrics
            }
        
        # Add interceptor metrics if available
        if hasattr(self, '_metrics_interceptor'):
            interceptor_metrics = self._metrics_interceptor.get_metrics()
            metrics['interceptor_metrics'] = interceptor_metrics
        
        return metrics
    
    def get_endpoint_status(self) -> List[Dict[str, Any]]:
        """Get detailed status of all endpoints."""
        if not self._load_balancer:
            return []
        
        return [
            {
                'url': endpoint.url,
                'health': endpoint.health.value,
                'available': endpoint.is_available,
                'weight': endpoint.weight,
                'active_connections': endpoint.active_connections,
                'total_requests': endpoint.total_requests,
                'successful_requests': endpoint.successful_requests,
                'failed_requests': endpoint.failed_requests,
                'success_rate': endpoint.success_rate,
                'average_response_time': endpoint.average_response_time,
                'last_response_time': endpoint.last_response_time,
                'consecutive_failures': endpoint.consecutive_failures,
                'consecutive_successes': endpoint.consecutive_successes,
                'circuit_breaker_open': endpoint.circuit_breaker_open,
                'circuit_breaker_open_until': endpoint.circuit_breaker_open_until.isoformat() if endpoint.circuit_breaker_open_until else None,
                'last_health_check': endpoint.last_health_check.isoformat() if endpoint.last_health_check else None
            }
            for endpoint in self._load_balancer.endpoints
        ]
    
    def optimize_connection_pool(self, expected_rps: float, avg_response_time: float):
        """Optimize connection pool based on expected load."""
        if self._client:
            # Can't change limits on existing client
            self.logger.warning("Cannot optimize connection pool on active client. Restart client to apply changes.")
            return
        
        # Update optimizer configuration
        optimized_limits = self._pool_optimizer.optimize_for_load(expected_rps, avg_response_time)
        
        self.config.max_connections = optimized_limits.max_connections
        self.config.max_keepalive_connections = optimized_limits.max_keepalive_connections
        
        self.logger.info(f"Connection pool optimized for {expected_rps} RPS", metadata={
            'expected_rps': expected_rps,
            'avg_response_time': avg_response_time,
            'max_connections': optimized_limits.max_connections,
            'max_keepalive': optimized_limits.max_keepalive_connections
        })
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for client lifecycle."""
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    def __repr__(self) -> str:
        endpoint_count = len(self._load_balancer.endpoints) if self._load_balancer else 0
        return f"EnhancedHTTPClientWithPolicies(endpoints={endpoint_count}, connected={self.is_connected})"


# Convenience alias
AdvancedHTTPClient = EnhancedHTTPClientWithPolicies
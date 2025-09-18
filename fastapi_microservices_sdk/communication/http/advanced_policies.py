#!/usr/bin/env python3
"""
Advanced Retry Policies and Load Balancing for HTTP Client.

This module provides enterprise-grade retry policies and load balancing strategies:
- Advanced retry policies with exponential backoff and jitter
- Multiple load balancing strategies (round-robin, weighted, health-based)
- Timeout management (connection, read, total timeouts)
- Request/response interceptors for logging and metrics
- Service discovery integration for dynamic endpoint resolution
- Connection pooling optimization and keep-alive management
"""

import asyncio
import time
import random
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, Protocol
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import statistics
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, validator

from ..logging import CommunicationLogger
from ..exceptions import (
    CommunicationError,
    CommunicationTimeoutError,
    CommunicationConnectionError
)


class RetryStrategy(str, Enum):
    """Retry strategy enumeration."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    HEALTH_BASED = "health_based"
    RANDOM = "random"
    WEIGHTED_RANDOM = "weighted_random"
    CONSISTENT_HASH = "consistent_hash"


class EndpointHealth(str, Enum):
    """Endpoint health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    exception: Optional[Exception] = None
    response_code: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ServiceEndpoint:
    """Service endpoint with health and performance metrics."""
    url: str
    weight: float = 1.0
    health: EndpointHealth = EndpointHealth.UNKNOWN
    
    # Performance metrics
    active_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_response_time: float = 0.0
    
    # Health check
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    # Circuit breaker state
    circuit_breaker_open: bool = False
    circuit_breaker_open_until: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize computed fields."""
        if not self.last_health_check:
            self.last_health_check = datetime.now(timezone.utc)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_available(self) -> bool:
        """Check if endpoint is available for requests."""
        if self.circuit_breaker_open:
            if self.circuit_breaker_open_until and datetime.now(timezone.utc) > self.circuit_breaker_open_until:
                self.circuit_breaker_open = False
                self.circuit_breaker_open_until = None
            else:
                return False
        
        return self.health in [EndpointHealth.HEALTHY, EndpointHealth.DEGRADED]
    
    def record_request_start(self):
        """Record the start of a request."""
        self.active_connections += 1
        self.total_requests += 1
    
    def record_request_end(self, success: bool, response_time: float):
        """Record the end of a request."""
        self.active_connections = max(0, self.active_connections - 1)
        self.last_response_time = response_time
        
        if success:
            self.successful_requests += 1
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0
        
        # Update average response time
        if self.successful_requests > 0:
            total_time = self.average_response_time * (self.successful_requests - 1) + response_time
            self.average_response_time = total_time / self.successful_requests
    
    def update_health(self, health: EndpointHealth):
        """Update endpoint health status."""
        self.health = health
        self.last_health_check = datetime.now(timezone.utc)
    
    def open_circuit_breaker(self, timeout_seconds: float = 60.0):
        """Open circuit breaker for this endpoint."""
        self.circuit_breaker_open = True
        self.circuit_breaker_open_until = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)


class AdvancedRetryPolicy(BaseModel):
    """Advanced retry policy configuration."""
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=1.0, gt=0)
    max_delay: float = Field(default=60.0, gt=0)
    exponential_base: float = Field(default=2.0, gt=1)
    jitter: bool = Field(default=True)
    jitter_range: float = Field(default=0.1, ge=0, le=1)
    
    # Retry conditions
    retry_on_status_codes: List[int] = Field(default_factory=lambda: [500, 502, 503, 504])
    retry_on_exceptions: List[str] = Field(default_factory=lambda: [
        "httpx.ConnectError", "httpx.TimeoutException", "httpx.NetworkError"
    ])
    
    # Custom retry function
    custom_retry_function: Optional[Callable[[int], float]] = Field(default=None, exclude=True)
    
    @validator('max_delay')
    def validate_max_delay(cls, v, values):
        if 'base_delay' in values and v < values['base_delay']:
            raise ValueError('max_delay must be >= base_delay')
        return v
    
    class Config:
        arbitrary_types_allowed = True
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.custom_retry_function:
            delay = self.custom_retry_function(attempt)
        elif self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        elif self.strategy == RetryStrategy.FIBONACCI:
            delay = self.base_delay * self._fibonacci(attempt)
        else:
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Apply jitter if enabled
        if self.jitter:
            jitter_amount = delay * self.jitter_range
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Ensure minimum delay
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number."""
        if n <= 1:
            return 1
        elif n == 2:
            return 1
        else:
            a, b = 1, 1
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b
    
    def should_retry(self, attempt: int, exception: Exception = None, status_code: int = None) -> bool:
        """Determine if request should be retried."""
        if attempt >= self.max_attempts:
            return False
        
        # Check status code
        if status_code and status_code in self.retry_on_status_codes:
            return True
        
        # Check exception type
        if exception:
            exception_name = f"{exception.__class__.__module__}.{exception.__class__.__name__}"
            if exception_name in self.retry_on_exceptions:
                return True
        
        return False


class TimeoutConfig(BaseModel):
    """Timeout configuration for HTTP requests."""
    connect: float = Field(default=5.0, gt=0)
    read: float = Field(default=30.0, gt=0)
    write: float = Field(default=30.0, gt=0)
    total: float = Field(default=60.0, gt=0)
    
    @validator('total')
    def validate_total_timeout(cls, v, values):
        if 'connect' in values and 'read' in values:
            min_total = values['connect'] + values['read']
            if v < min_total:
                raise ValueError(f'total timeout must be >= connect + read ({min_total})')
        return v
    
    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout object."""
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.total
        )


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration."""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_interval: float = Field(default=30.0, gt=0)
    health_check_timeout: float = Field(default=5.0, gt=0)
    health_check_path: str = Field(default="/health")
    
    # Circuit breaker settings
    failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout: float = Field(default=60.0, gt=0)
    
    # Consistent hashing settings (for CONSISTENT_HASH strategy)
    hash_key_function: Optional[Callable[[str], str]] = Field(default=None, exclude=True)
    virtual_nodes: int = Field(default=150, ge=1)
    
    class Config:
        arbitrary_types_allowed = True


class RequestInterceptor(Protocol):
    """Request interceptor protocol."""
    
    async def intercept_request(
        self, 
        request: httpx.Request, 
        endpoint: ServiceEndpoint,
        attempt: int
    ) -> httpx.Request:
        """Intercept and potentially modify outgoing request."""
        ...


class ResponseInterceptor(Protocol):
    """Response interceptor protocol."""
    
    async def intercept_response(
        self, 
        response: httpx.Response, 
        endpoint: ServiceEndpoint,
        request_start_time: float
    ) -> httpx.Response:
        """Intercept and potentially modify incoming response."""
        ...


class LoadBalancer(ABC):
    """Abstract base class for load balancers."""
    
    def __init__(self, config: LoadBalancerConfig, logger: Optional[CommunicationLogger] = None):
        self.config = config
        self.logger = logger or CommunicationLogger("load_balancer")
        self.endpoints: List[ServiceEndpoint] = []
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
    
    @abstractmethod
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select an endpoint for the request."""
        pass
    
    def add_endpoint(self, url: str, weight: float = 1.0) -> ServiceEndpoint:
        """Add an endpoint to the load balancer."""
        endpoint = ServiceEndpoint(url=url, weight=weight)
        self.endpoints.append(endpoint)
        self.logger.info(f"Added endpoint: {url} (weight: {weight})")
        return endpoint
    
    def remove_endpoint(self, url: str) -> bool:
        """Remove an endpoint from the load balancer."""
        for i, endpoint in enumerate(self.endpoints):
            if endpoint.url == url:
                del self.endpoints[i]
                self.logger.info(f"Removed endpoint: {url}")
                return True
        return False
    
    def get_healthy_endpoints(self) -> List[ServiceEndpoint]:
        """Get list of healthy endpoints."""
        return [ep for ep in self.endpoints if ep.is_available]
    
    async def start_health_checks(self):
        """Start periodic health checks."""
        if self._health_check_task:
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self.logger.info("Started health check monitoring")
    
    async def stop_health_checks(self):
        """Stop periodic health checks."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
        self.logger.info("Stopped health check monitoring")
    
    async def _health_check_loop(self):
        """Health check loop."""
        while self._running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(5.0)  # Brief pause on error
    
    async def _perform_health_checks(self):
        """Perform health checks on all endpoints."""
        tasks = []
        for endpoint in self.endpoints:
            task = asyncio.create_task(self._check_endpoint_health(endpoint))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_endpoint_health(self, endpoint: ServiceEndpoint):
        """Check health of a single endpoint."""
        try:
            timeout = httpx.Timeout(self.config.health_check_timeout)
            async with httpx.AsyncClient(timeout=timeout) as client:
                health_url = f"{endpoint.url.rstrip('/')}{self.config.health_check_path}"
                response = await client.get(health_url)
                
                if 200 <= response.status_code < 300:
                    endpoint.update_health(EndpointHealth.HEALTHY)
                    endpoint.consecutive_failures = 0
                elif 400 <= response.status_code < 500:
                    endpoint.update_health(EndpointHealth.DEGRADED)
                else:
                    endpoint.update_health(EndpointHealth.UNHEALTHY)
                    endpoint.consecutive_failures += 1
        
        except Exception as e:
            endpoint.update_health(EndpointHealth.UNHEALTHY)
            endpoint.consecutive_failures += 1
            self.logger.warning(f"Health check failed for {endpoint.url}: {e}")
        
        # Open circuit breaker if too many failures
        if endpoint.consecutive_failures >= self.config.failure_threshold:
            endpoint.open_circuit_breaker(self.config.circuit_breaker_timeout)
            self.logger.warning(f"Circuit breaker opened for {endpoint.url}")


class RoundRobinLoadBalancer(LoadBalancer):
    """Round-robin load balancer."""
    
    def __init__(self, config: LoadBalancerConfig, logger: Optional[CommunicationLogger] = None):
        super().__init__(config, logger)
        self._current_index = 0
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint using round-robin strategy."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        # Simple round-robin selection
        endpoint = healthy_endpoints[self._current_index % len(healthy_endpoints)]
        self._current_index += 1
        
        return endpoint


class WeightedRoundRobinLoadBalancer(LoadBalancer):
    """Weighted round-robin load balancer."""
    
    def __init__(self, config: LoadBalancerConfig, logger: Optional[CommunicationLogger] = None):
        super().__init__(config, logger)
        self._current_weights: Dict[str, int] = {}
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint using weighted round-robin strategy."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        # Initialize weights if needed
        for endpoint in healthy_endpoints:
            if endpoint.url not in self._current_weights:
                self._current_weights[endpoint.url] = 0
        
        # Find endpoint with highest current weight
        selected_endpoint = None
        max_weight = -1
        
        for endpoint in healthy_endpoints:
            self._current_weights[endpoint.url] += int(endpoint.weight * 100)
            if self._current_weights[endpoint.url] > max_weight:
                max_weight = self._current_weights[endpoint.url]
                selected_endpoint = endpoint
        
        # Reduce selected endpoint's weight
        if selected_endpoint:
            self._current_weights[selected_endpoint.url] -= sum(
                int(ep.weight * 100) for ep in healthy_endpoints
            )
        
        return selected_endpoint or healthy_endpoints[0]


class LeastConnectionsLoadBalancer(LoadBalancer):
    """Least connections load balancer."""
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint with least active connections."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        # Select endpoint with minimum active connections
        return min(healthy_endpoints, key=lambda ep: ep.active_connections)


class LeastResponseTimeLoadBalancer(LoadBalancer):
    """Least response time load balancer."""
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint with least average response time."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        # Select endpoint with minimum average response time
        # Prefer endpoints with some history over completely new ones
        endpoints_with_history = [ep for ep in healthy_endpoints if ep.total_requests > 0]
        
        if endpoints_with_history:
            return min(endpoints_with_history, key=lambda ep: ep.average_response_time)
        else:
            # If no endpoints have history, use round-robin
            return healthy_endpoints[0]


class RandomLoadBalancer(LoadBalancer):
    """Random load balancer."""
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint randomly."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        return random.choice(healthy_endpoints)


class WeightedRandomLoadBalancer(LoadBalancer):
    """Weighted random load balancer."""
    
    async def select_endpoint(self, request_context: Dict[str, Any] = None) -> ServiceEndpoint:
        """Select endpoint using weighted random selection."""
        healthy_endpoints = self.get_healthy_endpoints()
        
        if not healthy_endpoints:
            raise CommunicationError("No healthy endpoints available")
        
        # Calculate total weight
        total_weight = sum(ep.weight for ep in healthy_endpoints)
        
        if total_weight == 0:
            return random.choice(healthy_endpoints)
        
        # Select random point in weight range
        random_weight = random.uniform(0, total_weight)
        current_weight = 0
        
        for endpoint in healthy_endpoints:
            current_weight += endpoint.weight
            if random_weight <= current_weight:
                return endpoint
        
        # Fallback (shouldn't reach here)
        return healthy_endpoints[-1]


def create_load_balancer(
    strategy: LoadBalancingStrategy, 
    config: LoadBalancerConfig,
    logger: Optional[CommunicationLogger] = None
) -> LoadBalancer:
    """Factory function to create load balancer based on strategy."""
    
    if strategy == LoadBalancingStrategy.ROUND_ROBIN:
        return RoundRobinLoadBalancer(config, logger)
    elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
        return WeightedRoundRobinLoadBalancer(config, logger)
    elif strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
        return LeastConnectionsLoadBalancer(config, logger)
    elif strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
        return LeastResponseTimeLoadBalancer(config, logger)
    elif strategy == LoadBalancingStrategy.RANDOM:
        return RandomLoadBalancer(config, logger)
    elif strategy == LoadBalancingStrategy.WEIGHTED_RANDOM:
        return WeightedRandomLoadBalancer(config, logger)
    else:
        raise ValueError(f"Unsupported load balancing strategy: {strategy}")


# Built-in interceptors
class LoggingInterceptor:
    """Request/response logging interceptor."""
    
    def __init__(self, logger: Optional[CommunicationLogger] = None):
        self.logger = logger or CommunicationLogger("http_interceptor")
    
    async def intercept_request(
        self, 
        request: httpx.Request, 
        endpoint: ServiceEndpoint,
        attempt: int
    ) -> httpx.Request:
        """Log outgoing request."""
        self.logger.info(f"Request: {request.method} {request.url} (attempt {attempt})", metadata={
            'method': request.method,
            'url': str(request.url),
            'endpoint': endpoint.url,
            'attempt': attempt,
            'headers': dict(request.headers)
        })
        return request
    
    async def intercept_response(
        self, 
        response: httpx.Response, 
        endpoint: ServiceEndpoint,
        request_start_time: float
    ) -> httpx.Response:
        """Log incoming response."""
        response_time = time.time() - request_start_time
        
        self.logger.info(f"Response: {response.status_code} in {response_time:.3f}s", metadata={
            'status_code': response.status_code,
            'response_time': response_time,
            'endpoint': endpoint.url,
            'headers': dict(response.headers)
        })
        return response


class MetricsInterceptor:
    """Request/response metrics interceptor."""
    
    def __init__(self):
        self.request_count = 0
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
    
    async def intercept_request(
        self, 
        request: httpx.Request, 
        endpoint: ServiceEndpoint,
        attempt: int
    ) -> httpx.Request:
        """Record request metrics."""
        self.request_count += 1
        endpoint.record_request_start()
        return request
    
    async def intercept_response(
        self, 
        response: httpx.Response, 
        endpoint: ServiceEndpoint,
        request_start_time: float
    ) -> httpx.Response:
        """Record response metrics."""
        response_time = time.time() - request_start_time
        success = 200 <= response.status_code < 400
        
        # Update endpoint metrics
        endpoint.record_request_end(success, response_time)
        
        # Update global metrics
        self.response_times.append(response_time)
        self.status_codes[response.status_code] = self.status_codes.get(response.status_code, 0) + 1
        
        # Keep only recent response times (last 1000)
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        return {
            'total_requests': self.request_count,
            'average_response_time': statistics.mean(self.response_times) if self.response_times else 0,
            'median_response_time': statistics.median(self.response_times) if self.response_times else 0,
            'p95_response_time': statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) >= 20 else 0,
            'status_code_distribution': self.status_codes.copy()
        }


class ConnectionPoolOptimizer:
    """Connection pool optimizer for HTTP clients."""
    
    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 5.0,
        max_connections_per_host: int = 10
    ):
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.max_connections_per_host = max_connections_per_host
    
    def create_limits(self) -> httpx.Limits:
        """Create optimized httpx.Limits configuration."""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry
        )
    
    def optimize_for_load(self, expected_rps: float, avg_response_time: float) -> httpx.Limits:
        """Optimize connection pool based on expected load."""
        # Calculate required connections based on Little's Law
        # Connections needed = RPS * Average Response Time
        required_connections = int(expected_rps * avg_response_time * 1.2)  # 20% buffer
        
        # Ensure we don't exceed reasonable limits
        max_conn = min(required_connections, 200)
        keepalive_conn = min(max_conn // 2, 50)
        
        return httpx.Limits(
            max_connections=max_conn,
            max_keepalive_connections=keepalive_conn,
            keepalive_expiry=self.keepalive_expiry
        )
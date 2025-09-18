"""Enhanced HTTP Client with Circuit Breaker Pattern."""

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import httpx
from pydantic import BaseModel, Field


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthenticationType(str, Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"


class RetryConfig(BaseModel):
    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay: float = Field(default=1.0, gt=0)
    max_delay: float = Field(default=60.0, gt=0)
    exponential_base: float = Field(default=2.0, gt=1)
    jitter: bool = Field(default=True)
    retry_on_status: List[int] = Field(default_factory=lambda: [500, 502, 503, 504])


class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = Field(default=5, ge=1)
    success_threshold: int = Field(default=3, ge=1)
    timeout: float = Field(default=60.0, gt=0)


class CacheConfig(BaseModel):
    ttl: int = Field(default=300, ge=0)
    max_size: int = Field(default=1000, ge=0)


class AuthenticationConfig(BaseModel):
    type: AuthenticationType = AuthenticationType.NONE
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_header: str = Field(default="X-API-Key")


class RateLimitConfig(BaseModel):
    requests_per_second: float = Field(default=10.0, gt=0)
    burst_size: int = Field(default=20, ge=1)


class EnhancedHTTPClientConfig(BaseModel):
    base_url: str
    timeout: float = Field(default=30.0, gt=0)
    max_connections: int = Field(default=100, ge=1)
    max_keepalive_connections: int = Field(default=20, ge=1)
    keepalive_expiry: float = Field(default=5.0, gt=0)
    
    retry: RetryConfig = Field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    rate_limit: Optional[RateLimitConfig] = None
    
    verify_ssl: bool = Field(default=True)
    default_headers: Dict[str, str] = Field(default_factory=dict)
    user_agent: str = Field(default="FastAPI-Microservices-SDK/1.0")
    enable_tracing: bool = Field(default=True)
    trace_header_name: str = Field(default="X-Trace-ID")
    
    class Config:
        arbitrary_types_allowed = True


class HTTPMetrics:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.circuit_breaker_opens = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.average_response_time = 0.0
        self.last_request_time = None
    
    def record_request(self, success: bool, response_time: float):
        self.total_requests += 1
        self.last_request_time = datetime.now(timezone.utc)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        if self.total_requests == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )
    
    def record_circuit_breaker_open(self):
        self.circuit_breaker_opens += 1
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests


class SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: float, success_threshold: int):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._state = "CLOSED"
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
    
    @property
    def state(self):
        if self._state == "OPEN":
            if self._last_failure_time and (time.time() - self._last_failure_time) > self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._success_count = 0
        return self._state
    
    async def record_success(self):
        if self._state == "HALF_OPEN":
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = "CLOSED"
                self._failure_count = 0
        elif self._state == "CLOSED":
            self._failure_count = 0
    
    async def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"


class HTTPCache:
    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache = {}
    
    def get(self, method: str, url: str, headers=None):
        key = f"{method}:{url}"
        return self._cache.get(key)
    
    def set(self, method: str, url: str, data, headers=None):
        key = f"{method}:{url}"
        if len(self._cache) >= self.config.max_size:
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[key] = data
    
    def clear(self):
        self._cache.clear()
    
    def size(self):
        return len(self._cache)


class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens = float(config.burst_size)
        self._last_update = time.time()
    
    async def acquire(self):
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(
            self.config.burst_size,
            self._tokens + elapsed * self.config.requests_per_second
        )
        self._last_update = now
        
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return
        
        wait_time = (1.0 - self._tokens) / self.config.requests_per_second
        await asyncio.sleep(wait_time)
        self._tokens = 0.0


class TracingMiddleware:
    def __init__(self, trace_header_name: str = "X-Trace-ID"):
        self.trace_header_name = trace_header_name
    
    async def process_request(self, request: httpx.Request):
        if self.trace_header_name not in request.headers:
            import uuid
            trace_id = str(uuid.uuid4())
            request.headers[self.trace_header_name] = trace_id
        return request


class AuthenticationMiddleware:
    def __init__(self, config: AuthenticationConfig):
        self.config = config
    
    async def process_request(self, request: httpx.Request):
        if self.config.type == AuthenticationType.BASIC:
            if self.config.username and self.config.password:
                import base64
                credentials = f"{self.config.username}:{self.config.password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                request.headers["Authorization"] = f"Basic {encoded}"
        
        elif self.config.type == AuthenticationType.BEARER:
            if self.config.token:
                request.headers["Authorization"] = f"Bearer {self.config.token}"
        
        elif self.config.type == AuthenticationType.API_KEY:
            if self.config.api_key:
                request.headers[self.config.api_key_header] = self.config.api_key
        
        return request


class EnhancedHTTPClient:
    """Enhanced HTTP client with circuit breaker pattern and advanced features."""
    
    def __init__(self, config: EnhancedHTTPClientConfig, logger=None):
        self.config = config
        self.logger = logger
        
        self._client = None
        self._circuit_breaker = SimpleCircuitBreaker(
            failure_threshold=config.circuit_breaker.failure_threshold,
            recovery_timeout=config.circuit_breaker.timeout,
            success_threshold=config.circuit_breaker.success_threshold
        )
        self._cache = HTTPCache(config.cache)
        self._rate_limiter = RateLimiter(config.rate_limit) if config.rate_limit else None
        self._metrics = HTTPMetrics()
        
        self._request_middleware = []
        self._response_middleware = []
        
        if config.enable_tracing:
            self._request_middleware.append(TracingMiddleware(config.trace_header_name))
        
        if config.authentication.type != AuthenticationType.NONE:
            self._request_middleware.append(AuthenticationMiddleware(config.authentication))
        
        self._is_connected = False
    
    async def connect(self):
        if self._is_connected:
            return
        
        try:
            limits = httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_keepalive_connections,
                keepalive_expiry=self.config.keepalive_expiry
            )
            
            timeout = httpx.Timeout(self.config.timeout)
            headers = {"User-Agent": self.config.user_agent, **self.config.default_headers}
            
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                limits=limits,
                timeout=timeout,
                verify=self.config.verify_ssl,
                headers=headers
            )
            
            self._is_connected = True
            if self.logger:
                self.logger.info("Enhanced HTTP client connected")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to connect HTTP client: {e}")
            raise Exception(f"HTTP client connection failed: {e}")
    
    async def disconnect(self):
        if not self._is_connected:
            return
        
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            self._is_connected = False
            if self.logger:
                self.logger.info("Enhanced HTTP client disconnected")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error disconnecting HTTP client: {e}")
    
    @property
    def is_connected(self):
        return self._is_connected and self._client is not None
    
    def add_request_middleware(self, middleware):
        self._request_middleware.append(middleware)
    
    def add_response_middleware(self, middleware):
        self._response_middleware.append(middleware)
    
    async def request(
        self,
        method: Union[str, HTTPMethod],
        url: str,
        *,
        params=None,
        json=None,
        data=None,
        headers=None,
        timeout=None,
        use_cache=True,
        bypass_circuit_breaker=False
    ):
        if not self.is_connected:
            await self.connect()
        
        method_str = method.value if isinstance(method, HTTPMethod) else method.upper()
        
        if self._rate_limiter:
            await self._rate_limiter.acquire()
        
        if use_cache and method_str == "GET":
            cached_response = self._cache.get(method_str, url, headers)
            if cached_response is not None:
                self._metrics.record_cache_hit()
                return cached_response
            self._metrics.record_cache_miss()
        
        if not bypass_circuit_breaker and self._circuit_breaker.state == "OPEN":
            self._metrics.record_circuit_breaker_open()
            raise Exception("Circuit breaker is open")
        
        return await self._execute_request_with_retry(
            method_str, url, params, json, data, headers, timeout, use_cache
        )
    
    async def _execute_request_with_retry(self, method, url, params, json, data, headers, timeout, use_cache):
        last_exception = None
        
        for attempt in range(self.config.retry.max_retries + 1):
            try:
                start_time = time.time()
                response = await self._execute_single_request(method, url, params, json, data, headers, timeout)
                response_time = time.time() - start_time
                
                if response.is_success:
                    self._metrics.record_request(True, response_time)
                    await self._circuit_breaker.record_success()
                    
                    if use_cache and method == "GET" and response.status_code == 200:
                        self._cache.set(method, url, response, headers)
                    
                    return response
                
                elif response.status_code in self.config.retry.retry_on_status:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                else:
                    self._metrics.record_request(False, response_time)
                    await self._circuit_breaker.record_failure()
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            except Exception as e:
                last_exception = e
                self._metrics.record_request(False, time.time() - start_time)
                await self._circuit_breaker.record_failure()
            
            if attempt < self.config.retry.max_retries:
                delay = self._calculate_retry_delay(attempt)
                await asyncio.sleep(delay)
        
        raise last_exception or Exception("Request failed after all retries")
    
    async def _execute_single_request(self, method, url, params, json, data, headers, timeout):
        if not self._client:
            raise Exception("HTTP client not connected")
        
        request = self._client.build_request(
            method=method, url=url, params=params, json=json, data=data, headers=headers, timeout=timeout
        )
        
        for middleware in self._request_middleware:
            request = await middleware.process_request(request)
        
        response = await self._client.send(request)
        
        for middleware in self._response_middleware:
            response = await middleware.process_response(response)
        
        return response
    
    def _calculate_retry_delay(self, attempt):
        delay = min(
            self.config.retry.initial_delay * (self.config.retry.exponential_base ** attempt),
            self.config.retry.max_delay
        )
        
        if self.config.retry.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    async def get(self, url, *, params=None, headers=None, timeout=None, use_cache=True):
        return await self.request(HTTPMethod.GET, url, params=params, headers=headers, timeout=timeout, use_cache=use_cache)
    
    async def post(self, url, *, json=None, data=None, params=None, headers=None, timeout=None):
        return await self.request(HTTPMethod.POST, url, json=json, data=data, params=params, headers=headers, timeout=timeout, use_cache=False)
    
    async def put(self, url, *, json=None, data=None, params=None, headers=None, timeout=None):
        return await self.request(HTTPMethod.PUT, url, json=json, data=data, params=params, headers=headers, timeout=timeout, use_cache=False)
    
    async def patch(self, url, *, json=None, data=None, params=None, headers=None, timeout=None):
        return await self.request(HTTPMethod.PATCH, url, json=json, data=data, params=params, headers=headers, timeout=timeout, use_cache=False)
    
    async def delete(self, url, *, params=None, headers=None, timeout=None):
        return await self.request(HTTPMethod.DELETE, url, params=params, headers=headers, timeout=timeout, use_cache=False)
    
    async def health_check(self):
        try:
            if not self.is_connected:
                return {
                    'status': 'unhealthy',
                    'error': 'Client not connected',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            start_time = time.time()
            try:
                response = await self.request(HTTPMethod.HEAD, "/", bypass_circuit_breaker=True, use_cache=False, timeout=5.0)
                response_time = time.time() - start_time
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'circuit_breaker_state': self._circuit_breaker.state,
                    'metrics': self.get_metrics(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'error': str(e),
                    'circuit_breaker_state': self._circuit_breaker.state,
                    'metrics': self.get_metrics(),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': f"Health check failed: {e}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def get_metrics(self):
        return {
            'total_requests': self._metrics.total_requests,
            'successful_requests': self._metrics.successful_requests,
            'failed_requests': self._metrics.failed_requests,
            'success_rate': self._metrics.success_rate,
            'circuit_breaker_opens': self._metrics.circuit_breaker_opens,
            'cache_hits': self._metrics.cache_hits,
            'cache_misses': self._metrics.cache_misses,
            'cache_hit_rate': self._metrics.cache_hit_rate,
            'cache_size': self._cache.size(),
            'average_response_time': self._metrics.average_response_time,
            'last_request_time': self._metrics.last_request_time.isoformat() if self._metrics.last_request_time else None
        }
    
    def clear_cache(self):
        self._cache.clear()
        if self.logger:
            self.logger.info("HTTP cache cleared")
    
    def reset_circuit_breaker(self):
        self._circuit_breaker._state = "CLOSED"
        self._circuit_breaker._failure_count = 0
        self._circuit_breaker._success_count = 0
        self._circuit_breaker._last_failure_time = None
        if self.logger:
            self.logger.info("Circuit breaker reset")
    
    @asynccontextmanager
    async def lifespan(self):
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    def __repr__(self):
        return f"EnhancedHTTPClient(base_url='{self.config.base_url}', connected={self.is_connected})"
# Enhanced HTTP Client

The Enhanced HTTP Client is an enterprise-grade HTTP client that provides advanced features for building resilient microservices. It implements the Circuit Breaker pattern and includes comprehensive monitoring, caching, authentication, and rate limiting capabilities.

## Features

### Core Features
- **Circuit Breaker Pattern**: Automatic fault tolerance with configurable failure thresholds
- **Advanced Retry Logic**: Exponential backoff with jitter for optimal retry behavior
- **Connection Pooling**: Efficient connection management and reuse
- **Request/Response Middleware**: Extensible pipeline for request/response processing
- **Comprehensive Metrics**: Detailed monitoring and performance tracking

### Advanced Features
- **Multiple Authentication Types**: Bearer, Basic, API Key, OAuth2, and custom authentication
- **Intelligent Caching**: Memory-based caching with TTL and LRU eviction
- **Rate Limiting**: Token bucket algorithm for request throttling
- **Request Tracing**: Automatic correlation ID injection for distributed tracing
- **SSL/TLS Support**: Full SSL certificate validation and client certificate support

## Quick Start

### Basic Usage

```python
import asyncio
from fastapi_microservices_sdk.communication.http import (
    EnhancedHTTPClient,
    EnhancedHTTPClientConfig
)

async def main():
    # Create basic configuration
    config = EnhancedHTTPClientConfig(
        base_url="https://api.example.com",
        timeout=30.0
    )
    
    # Create and use client
    client = EnhancedHTTPClient(config)
    
    async with client.lifespan():
        # Make requests
        response = await client.get("/users")
        print(f"Status: {response.status_code}")
        
        # POST with JSON
        response = await client.post("/users", json={
            "name": "John Doe",
            "email": "john@example.com"
        })

asyncio.run(main())
```

### Advanced Configuration

```python
from fastapi_microservices_sdk.communication.http import (
    EnhancedHTTPClient,
    EnhancedHTTPClientConfig,
    RetryConfig,
    CircuitBreakerConfig,
    CacheConfig,
    AuthenticationConfig,
    RateLimitConfig,
    CacheStrategy,
    AuthenticationType
)

# Advanced configuration
config = EnhancedHTTPClientConfig(
    base_url="https://api.example.com",
    timeout=15.0,
    max_connections=50,
    
    # Retry configuration
    retry=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True
    ),
    
    # Circuit breaker
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=3,
        timeout=60.0
    ),
    
    # Caching
    cache=CacheConfig(
        strategy=CacheStrategy.MEMORY,
        ttl=300,  # 5 minutes
        max_size=1000
    ),
    
    # Authentication
    authentication=AuthenticationConfig(
        type=AuthenticationType.BEARER,
        token="your-api-token"
    ),
    
    # Rate limiting
    rate_limit=RateLimitConfig(
        requests_per_second=10.0,
        burst_size=20
    )
)

client = EnhancedHTTPClient(config)
```

## Configuration

### EnhancedHTTPClientConfig

The main configuration class for the Enhanced HTTP Client.

#### Basic Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | Required | Base URL for all requests |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `max_connections` | `int` | `100` | Maximum concurrent connections |
| `max_keepalive_connections` | `int` | `20` | Maximum keepalive connections |
| `keepalive_expiry` | `float` | `5.0` | Keepalive connection expiry time |

#### Security Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `verify_ssl` | `bool` | `True` | Enable SSL certificate verification |
| `ssl_cert_path` | `str` | `None` | Path to client SSL certificate |
| `ssl_key_path` | `str` | `None` | Path to client SSL private key |

#### Headers and Tracing

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_headers` | `Dict[str, str]` | `{}` | Default headers for all requests |
| `user_agent` | `str` | `"FastAPI-Microservices-SDK/1.0"` | User agent string |
| `enable_tracing` | `bool` | `True` | Enable request tracing |
| `trace_header_name` | `str` | `"X-Trace-ID"` | Header name for trace ID |

### RetryConfig

Configuration for retry behavior.

```python
RetryConfig(
    max_retries=3,           # Maximum number of retries
    initial_delay=1.0,       # Initial delay between retries
    max_delay=60.0,          # Maximum delay between retries
    exponential_base=2.0,    # Exponential backoff base
    jitter=True,             # Add random jitter to delays
    retry_on_status=[500, 502, 503, 504]  # HTTP status codes to retry
)
```

### CircuitBreakerConfig

Configuration for circuit breaker behavior.

```python
CircuitBreakerConfig(
    failure_threshold=5,     # Number of failures to open circuit
    success_threshold=3,     # Number of successes to close circuit
    timeout=60.0,           # Timeout before trying half-open state
    half_open_max_calls=3   # Max calls in half-open state
)
```

### CacheConfig

Configuration for response caching.

```python
CacheConfig(
    strategy=CacheStrategy.MEMORY,  # Cache strategy (MEMORY, REDIS, DISK, NONE)
    ttl=300,                       # Time to live in seconds
    max_size=1000,                 # Maximum cache entries
    key_prefix="http_cache"        # Cache key prefix
)
```

### AuthenticationConfig

Configuration for authentication.

```python
# Bearer Token
AuthenticationConfig(
    type=AuthenticationType.BEARER,
    token="your-bearer-token"
)

# Basic Authentication
AuthenticationConfig(
    type=AuthenticationType.BASIC,
    username="username",
    password="password"
)

# API Key
AuthenticationConfig(
    type=AuthenticationType.API_KEY,
    api_key="your-api-key",
    api_key_header="X-API-Key"
)

# Custom Headers
AuthenticationConfig(
    type=AuthenticationType.CUSTOM,
    custom_headers={
        "Authorization": "Custom auth-token",
        "X-Custom-Header": "value"
    }
)
```

### RateLimitConfig

Configuration for rate limiting.

```python
RateLimitConfig(
    requests_per_second=10.0,  # Maximum requests per second
    burst_size=20              # Maximum burst size
)
```

## HTTP Methods

The Enhanced HTTP Client provides convenient methods for all common HTTP operations:

### GET Requests

```python
# Simple GET
response = await client.get("/users")

# GET with query parameters
response = await client.get("/users", params={
    "page": 1,
    "limit": 10,
    "filter": "active"
})

# GET with custom headers
response = await client.get("/users", headers={
    "Accept": "application/json",
    "X-Custom-Header": "value"
})
```

### POST Requests

```python
# POST with JSON data
response = await client.post("/users", json={
    "name": "John Doe",
    "email": "john@example.com"
})

# POST with form data
response = await client.post("/users", data={
    "name": "John Doe",
    "email": "john@example.com"
})

# POST with custom headers
response = await client.post("/users", 
    json={"name": "John"},
    headers={"Content-Type": "application/json"}
)
```

### PUT, PATCH, DELETE

```python
# PUT request
response = await client.put("/users/1", json={
    "name": "Updated Name"
})

# PATCH request
response = await client.patch("/users/1", json={
    "email": "new@example.com"
})

# DELETE request
response = await client.delete("/users/1")
```

### Generic Request Method

```python
# Generic request with full control
response = await client.request(
    method="POST",
    url="/users",
    json={"data": "value"},
    headers={"Custom": "header"},
    timeout=10.0,
    use_cache=False,
    bypass_circuit_breaker=False
)
```

## Middleware

The Enhanced HTTP Client supports a flexible middleware system for processing requests and responses.

### Built-in Middleware

#### Tracing Middleware
Automatically adds trace IDs to requests for distributed tracing.

```python
# Enabled by default when enable_tracing=True
config = EnhancedHTTPClientConfig(
    base_url="https://api.example.com",
    enable_tracing=True,
    trace_header_name="X-Trace-ID"
)
```

#### Authentication Middleware
Automatically adds authentication headers based on configuration.

```python
config = EnhancedHTTPClientConfig(
    base_url="https://api.example.com",
    authentication=AuthenticationConfig(
        type=AuthenticationType.BEARER,
        token="your-token"
    )
)
```

### Custom Middleware

You can create custom middleware to modify requests and responses:

```python
class CustomRequestMiddleware:
    async def process_request(self, request):
        # Modify request
        request.headers["X-Custom"] = "value"
        return request

class CustomResponseMiddleware:
    async def process_response(self, response):
        # Process response
        print(f"Response: {response.status_code}")
        return response

# Add middleware to client
client.add_request_middleware(CustomRequestMiddleware())
client.add_response_middleware(CustomResponseMiddleware())
```

## Circuit Breaker

The circuit breaker automatically protects your application from cascading failures by monitoring request success/failure rates.

### Circuit Breaker States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Circuit is open, requests fail immediately
3. **HALF_OPEN**: Testing if service has recovered

### Configuration

```python
circuit_breaker=CircuitBreakerConfig(
    failure_threshold=5,     # Open after 5 failures
    success_threshold=3,     # Close after 3 successes in half-open
    timeout=60.0,           # Wait 60s before trying half-open
    half_open_max_calls=3   # Max 3 calls in half-open state
)
```

### Manual Control

```python
# Check circuit breaker state
state = client._circuit_breaker.state
print(f"Circuit breaker state: {state.value}")

# Reset circuit breaker
client.reset_circuit_breaker()

# Bypass circuit breaker for specific requests
response = await client.get("/health", bypass_circuit_breaker=True)
```

## Caching

The Enhanced HTTP Client includes intelligent caching for GET requests.

### Cache Strategies

- **MEMORY**: In-memory caching with LRU eviction
- **REDIS**: Redis-based caching (future implementation)
- **DISK**: Disk-based caching (future implementation)
- **NONE**: Disable caching

### Cache Configuration

```python
cache=CacheConfig(
    strategy=CacheStrategy.MEMORY,
    ttl=300,        # 5 minutes TTL
    max_size=1000,  # Maximum 1000 entries
    key_prefix="api_cache"
)
```

### Cache Control

```python
# Disable caching for specific request
response = await client.get("/users", use_cache=False)

# Clear all cached entries
client.clear_cache()

# Get cache statistics
metrics = client.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.1%}")
```

## Rate Limiting

The client includes built-in rate limiting using a token bucket algorithm.

### Configuration

```python
rate_limit=RateLimitConfig(
    requests_per_second=10.0,  # 10 requests per second
    burst_size=20              # Allow bursts up to 20 requests
)
```

### Behavior

- Requests are automatically throttled to stay within limits
- Burst requests are allowed up to the burst size
- Excess requests wait for tokens to become available

## Monitoring and Metrics

The Enhanced HTTP Client provides comprehensive monitoring capabilities.

### Health Checks

```python
# Perform health check
health = await client.health_check()
print(f"Status: {health['status']}")
print(f"Response time: {health['response_time']:.3f}s")
```

### Metrics

```python
# Get detailed metrics
metrics = client.get_metrics()

# Available metrics:
# - total_requests: Total number of requests made
# - successful_requests: Number of successful requests
# - failed_requests: Number of failed requests
# - success_rate: Success rate as a percentage
# - circuit_breaker_opens: Number of times circuit breaker opened
# - cache_hits: Number of cache hits
# - cache_misses: Number of cache misses
# - cache_hit_rate: Cache hit rate as a percentage
# - cache_size: Current cache size
# - average_response_time: Average response time in seconds
# - last_request_time: Timestamp of last request
```

### Example Monitoring

```python
async def monitor_client(client):
    while True:
        health = await client.health_check()
        metrics = client.get_metrics()
        
        print(f"Health: {health['status']}")
        print(f"Requests: {metrics['total_requests']}")
        print(f"Success Rate: {metrics['success_rate']:.1%}")
        print(f"Circuit Breaker: {health['circuit_breaker_state']}")
        
        await asyncio.sleep(30)  # Monitor every 30 seconds
```

## Error Handling

The Enhanced HTTP Client provides comprehensive error handling with specific exception types.

### Exception Types

```python
from fastapi_microservices_sdk.communication.exceptions import (
    CommunicationError,           # Base communication error
    CommunicationTimeoutError,    # Request timeout
    CommunicationConnectionError, # Connection error
    CommunicationAuthenticationError, # Authentication failed
    CommunicationRateLimitError   # Rate limit exceeded
)
```

### Error Handling Example

```python
try:
    response = await client.get("/users")
    print(f"Success: {response.status_code}")
    
except CommunicationTimeoutError:
    print("Request timed out")
    
except CommunicationConnectionError:
    print("Connection failed")
    
except CommunicationAuthenticationError:
    print("Authentication failed")
    
except CommunicationRateLimitError:
    print("Rate limit exceeded")
    
except CommunicationError as e:
    print(f"Communication error: {e}")
```

## Best Practices

### 1. Use Context Managers

Always use the `lifespan()` context manager for proper connection management:

```python
async with client.lifespan():
    # Make requests here
    response = await client.get("/users")
```

### 2. Configure Appropriate Timeouts

Set reasonable timeouts based on your service requirements:

```python
config = EnhancedHTTPClientConfig(
    base_url="https://api.example.com",
    timeout=30.0,  # 30 second default timeout
    retry=RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0
    )
)
```

### 3. Monitor Circuit Breaker State

Regularly check circuit breaker state and metrics:

```python
# Check circuit breaker state
if client._circuit_breaker.state == CircuitBreakerState.OPEN:
    print("Circuit breaker is open - service may be down")
    
# Get failure metrics
metrics = client.get_metrics()
if metrics['success_rate'] < 0.9:  # Less than 90% success
    print("High failure rate detected")
```

### 4. Use Appropriate Cache TTL

Set cache TTL based on data freshness requirements:

```python
# Short TTL for frequently changing data
cache=CacheConfig(ttl=60)  # 1 minute

# Longer TTL for stable data
cache=CacheConfig(ttl=3600)  # 1 hour
```

### 5. Implement Graceful Degradation

Handle circuit breaker open states gracefully:

```python
try:
    response = await client.get("/users")
    return response.json()
except CommunicationError:
    # Return cached data or default response
    return {"users": [], "error": "Service temporarily unavailable"}
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from fastapi_microservices_sdk.communication.http import (
    EnhancedHTTPClient,
    EnhancedHTTPClientConfig
)

app = FastAPI()

# Create client instance
def get_http_client():
    config = EnhancedHTTPClientConfig(
        base_url="https://api.external-service.com",
        authentication=AuthenticationConfig(
            type=AuthenticationType.BEARER,
            token="your-token"
        )
    )
    return EnhancedHTTPClient(config)

@app.get("/users/{user_id}")
async def get_user(user_id: int, client: EnhancedHTTPClient = Depends(get_http_client)):
    async with client.lifespan():
        response = await client.get(f"/users/{user_id}")
        return response.json()
```

### Background Task Integration

```python
import asyncio
from fastapi import BackgroundTasks

async def sync_data_task():
    config = EnhancedHTTPClientConfig(
        base_url="https://api.data-source.com",
        retry=RetryConfig(max_retries=5),
        circuit_breaker=CircuitBreakerConfig(failure_threshold=3)
    )
    
    client = EnhancedHTTPClient(config)
    
    async with client.lifespan():
        try:
            response = await client.get("/data")
            # Process data
            print(f"Synced {len(response.json())} records")
        except CommunicationError as e:
            print(f"Sync failed: {e}")

@app.post("/trigger-sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_data_task)
    return {"message": "Sync triggered"}
```

## Troubleshooting

### Common Issues

#### 1. Circuit Breaker Opens Frequently

**Symptoms**: Requests fail with "Circuit breaker is open" error

**Solutions**:
- Increase `failure_threshold` in circuit breaker config
- Check if downstream service is healthy
- Implement proper retry logic
- Add monitoring to identify root cause

#### 2. High Memory Usage

**Symptoms**: Application memory usage grows over time

**Solutions**:
- Reduce cache `max_size`
- Lower cache `ttl`
- Clear cache periodically: `client.clear_cache()`
- Monitor cache hit rate and adjust accordingly

#### 3. Slow Response Times

**Symptoms**: Requests take longer than expected

**Solutions**:
- Check network connectivity
- Increase connection pool size
- Enable HTTP/2 if supported
- Monitor `average_response_time` metric

#### 4. Authentication Failures

**Symptoms**: 401/403 errors despite correct credentials

**Solutions**:
- Verify token/credentials are current
- Check authentication type configuration
- Ensure proper headers are being sent
- Monitor authentication middleware

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# The client will log detailed information about:
# - Request/response details
# - Circuit breaker state changes
# - Cache hits/misses
# - Retry attempts
# - Authentication header injection
```

### Performance Tuning

#### Connection Pool Tuning

```python
config = EnhancedHTTPClientConfig(
    base_url="https://api.example.com",
    max_connections=200,        # Increase for high throughput
    max_keepalive_connections=50,  # Increase for better reuse
    keepalive_expiry=10.0      # Adjust based on server settings
)
```

#### Retry Optimization

```python
retry=RetryConfig(
    max_retries=2,           # Reduce for faster failure detection
    initial_delay=0.5,       # Reduce for faster retries
    max_delay=5.0,          # Cap maximum delay
    jitter=True             # Always enable jitter
)
```

#### Cache Optimization

```python
cache=CacheConfig(
    strategy=CacheStrategy.MEMORY,
    ttl=300,                # Adjust based on data freshness needs
    max_size=5000,          # Increase for better hit rate
    key_prefix="myapp"      # Use unique prefix per service
)
```

This documentation provides comprehensive coverage of the Enhanced HTTP Client's features and usage patterns. For additional examples and advanced use cases, refer to the example files in the `examples/` directory.
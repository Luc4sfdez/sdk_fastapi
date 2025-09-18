# Advanced Retry Policies and Load Balancing

The Advanced Policies module provides enterprise-grade retry policies and load balancing strategies for resilient HTTP communication in microservices architectures.

## Features

### Advanced Retry Policies
- **Multiple Strategies**: Exponential, Linear, Fibonacci, Fixed, and Custom backoff
- **Intelligent Jitter**: Reduces thundering herd problems
- **Configurable Conditions**: Retry on specific status codes and exceptions
- **Maximum Limits**: Prevents infinite retry loops

### Load Balancing Strategies
- **Round Robin**: Simple rotation through endpoints
- **Weighted Round Robin**: Distribution based on endpoint weights
- **Least Connections**: Routes to endpoint with fewest active connections
- **Least Response Time**: Routes to fastest responding endpoint
- **Random**: Random endpoint selection
- **Weighted Random**: Random selection with weight bias
- **Health-Based**: Automatic endpoint health monitoring

### Advanced Features
- **Circuit Breaker Integration**: Per-endpoint circuit breakers
- **Health Monitoring**: Automatic endpoint health checks
- **Request/Response Interceptors**: Extensible middleware pipeline
- **Connection Pool Optimization**: Dynamic pool sizing based on load
- **Comprehensive Metrics**: Detailed performance and health metrics

## Quick Start

### Basic Retry Policy

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import (
    AdvancedRetryPolicy,
    RetryStrategy
)

# Exponential backoff with jitter
retry_policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.EXPONENTIAL,
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_status_codes=[500, 502, 503, 504, 429]
)

# Calculate delays
for attempt in range(1, 6):
    delay = retry_policy.calculate_delay(attempt)
    should_retry = retry_policy.should_retry(attempt, status_code=500)
    print(f"Attempt {attempt}: {delay:.2f}s (retry: {should_retry})")
```

### Load Balancer Setup

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import (
    LoadBalancerConfig,
    LoadBalancingStrategy,
    create_load_balancer,
    ServiceEndpoint,
    EndpointHealth
)

# Create load balancer configuration
config = LoadBalancerConfig(
    strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
    health_check_interval=30.0,
    failure_threshold=3,
    circuit_breaker_timeout=60.0
)

# Create load balancer
load_balancer = create_load_balancer(config.strategy, config)

# Add endpoints
endpoints = [
    "https://api1.example.com",
    "https://api2.example.com",
    "https://api3.example.com"
]

for url in endpoints:
    endpoint = load_balancer.add_endpoint(url, weight=1.0)
    endpoint.update_health(EndpointHealth.HEALTHY)

# Start health monitoring
await load_balancer.start_health_checks()

# Select endpoint for request
selected_endpoint = await load_balancer.select_endpoint()
print(f"Selected: {selected_endpoint.url}")
```

### Enhanced HTTP Client Integration

```python
from fastapi_microservices_sdk.communication.http.enhanced_http_client import (
    EnhancedHTTPClientWithPolicies,
    EnhancedHTTPClientAdvancedConfig,
    AdvancedRetryPolicy,
    TimeoutConfig,
    LoadBalancerConfig
)

# Advanced configuration
config = EnhancedHTTPClientAdvancedConfig(
    service_urls=[
        "https://api1.example.com",
        "https://api2.example.com",
        "https://api3.example.com"
    ],
    
    # Advanced retry policy
    retry_policy=AdvancedRetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=4,
        base_delay=0.5,
        max_delay=10.0,
        jitter=True
    ),
    
    # Load balancer
    load_balancer=LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        health_check_interval=30.0,
        failure_threshold=3
    ),
    
    # Timeout configuration
    timeout=TimeoutConfig(
        connect=5.0,
        read=30.0,
        write=30.0,
        total=60.0
    ),
    
    # Enable interceptors
    enable_logging_interceptor=True,
    enable_metrics_interceptor=True,
    enable_health_checks=True
)

# Create client
client = EnhancedHTTPClientWithPolicies(config)

# Use client
async with client.lifespan():
    response = await client.get("/users")
    print(f"Response: {response.status_code}")
    
    # Get comprehensive metrics
    metrics = client.get_metrics()
    print(f"Success rate: {metrics['success_rate']:.1%}")
    print(f"Retry attempts: {metrics['retry_attempts']}")
```

## Retry Strategies

### 1. Exponential Backoff

Delays increase exponentially with each attempt:

```python
policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    exponential_base=2.0,
    max_delay=60.0
)

# Delays: 1s, 2s, 4s, 8s, 16s, 32s, 60s (capped)
```

### 2. Linear Backoff

Delays increase linearly:

```python
policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.LINEAR,
    base_delay=2.0
)

# Delays: 2s, 4s, 6s, 8s, 10s...
```

### 3. Fibonacci Backoff

Delays follow Fibonacci sequence:

```python
policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.FIBONACCI,
    base_delay=1.0
)

# Delays: 1s, 1s, 2s, 3s, 5s, 8s, 13s...
```

### 4. Fixed Backoff

Constant delay between attempts:

```python
policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.FIXED,
    base_delay=3.0
)

# Delays: 3s, 3s, 3s, 3s...
```

### 5. Custom Backoff

Define your own delay function:

```python
def custom_delay(attempt: int) -> float:
    return min(attempt ** 1.5, 30.0)

policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.CUSTOM,
    custom_retry_function=custom_delay
)
```

## Load Balancing Strategies

### 1. Round Robin

Simple rotation through available endpoints:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
lb = create_load_balancer(config.strategy, config)

# Selects: endpoint1 → endpoint2 → endpoint3 → endpoint1...
```

### 2. Weighted Round Robin

Distribution based on endpoint weights:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN)
lb = create_load_balancer(config.strategy, config)

# Add endpoints with different weights
lb.add_endpoint("https://api1.example.com", weight=1.0)
lb.add_endpoint("https://api2.example.com", weight=2.0)  # Gets 2x traffic
lb.add_endpoint("https://api3.example.com", weight=1.0)
```

### 3. Least Connections

Routes to endpoint with fewest active connections:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
lb = create_load_balancer(config.strategy, config)

# Automatically selects endpoint with minimum active_connections
```

### 4. Least Response Time

Routes to fastest responding endpoint:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME)
lb = create_load_balancer(config.strategy, config)

# Selects endpoint with lowest average_response_time
```

### 5. Random Selection

Random endpoint selection:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.RANDOM)
lb = create_load_balancer(config.strategy, config)

# Randomly selects from healthy endpoints
```

### 6. Weighted Random

Random selection with weight bias:

```python
config = LoadBalancerConfig(strategy=LoadBalancingStrategy.WEIGHTED_RANDOM)
lb = create_load_balancer(config.strategy, config)

# Higher weight = higher probability of selection
```

## Endpoint Health Management

### Health States

- **HEALTHY**: Endpoint is fully operational
- **DEGRADED**: Endpoint has issues but still usable
- **UNHEALTHY**: Endpoint is not responding properly
- **UNKNOWN**: Health status not yet determined

### Automatic Health Checks

```python
config = LoadBalancerConfig(
    health_check_interval=30.0,  # Check every 30 seconds
    health_check_timeout=5.0,    # 5 second timeout
    health_check_path="/health", # Health endpoint path
    failure_threshold=3,         # Open circuit after 3 failures
    circuit_breaker_timeout=60.0 # Keep circuit open for 60s
)

lb = create_load_balancer(LoadBalancingStrategy.ROUND_ROBIN, config)

# Start automatic health monitoring
await lb.start_health_checks()

# Health checks will automatically:
# - Update endpoint health status
# - Open circuit breakers on repeated failures
# - Close circuit breakers after recovery timeout
```

### Manual Health Management

```python
endpoint = ServiceEndpoint(url="https://api.example.com")

# Update health status
endpoint.update_health(EndpointHealth.HEALTHY)
endpoint.update_health(EndpointHealth.DEGRADED)
endpoint.update_health(EndpointHealth.UNHEALTHY)

# Check availability
if endpoint.is_available:
    print("Endpoint is available for requests")

# Manual circuit breaker control
endpoint.open_circuit_breaker(timeout_seconds=60.0)
```

## Request/Response Interceptors

### Built-in Interceptors

#### Logging Interceptor

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import LoggingInterceptor

interceptor = LoggingInterceptor(logger)

# Automatically logs all requests and responses
```

#### Metrics Interceptor

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import MetricsInterceptor

interceptor = MetricsInterceptor()

# Collect detailed metrics
metrics = interceptor.get_metrics()
print(f"Average response time: {metrics['average_response_time']:.3f}s")
print(f"Status code distribution: {metrics['status_code_distribution']}")
```

### Custom Interceptors

```python
class CustomRequestInterceptor:
    async def intercept_request(self, request, endpoint, attempt):
        # Add custom headers
        request.headers["X-Custom-Header"] = "value"
        request.headers["X-Attempt"] = str(attempt)
        return request

class CustomResponseInterceptor:
    async def intercept_response(self, response, endpoint, request_start_time):
        # Log slow responses
        response_time = time.time() - request_start_time
        if response_time > 1.0:
            print(f"Slow response: {response_time:.3f}s from {endpoint.url}")
        return response

# Add to client
client.add_request_interceptor(CustomRequestInterceptor())
client.add_response_interceptor(CustomResponseInterceptor())
```

## Connection Pool Optimization

### Automatic Optimization

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import ConnectionPoolOptimizer

optimizer = ConnectionPoolOptimizer()

# Optimize based on expected load
limits = optimizer.optimize_for_load(
    expected_rps=100.0,      # 100 requests per second
    avg_response_time=0.5    # 500ms average response time
)

print(f"Recommended connections: {limits.max_connections}")
print(f"Recommended keepalive: {limits.max_keepalive_connections}")
```

### Manual Configuration

```python
config = EnhancedHTTPClientAdvancedConfig(
    max_connections=200,           # Total connection pool size
    max_keepalive_connections=50,  # Persistent connections
    keepalive_expiry=10.0         # Keep connections alive for 10s
)
```

## Timeout Configuration

### Comprehensive Timeout Management

```python
from fastapi_microservices_sdk.communication.http.advanced_policies import TimeoutConfig

# Different timeout configurations for different scenarios
timeout_config = TimeoutConfig(
    connect=5.0,   # Connection establishment timeout
    read=30.0,     # Reading response timeout
    write=30.0,    # Writing request timeout
    total=60.0     # Total request timeout
)

# Validate configuration
httpx_timeout = timeout_config.to_httpx_timeout()
```

### Scenario-Based Timeouts

```python
# Fast API calls
fast_timeouts = TimeoutConfig(
    connect=2.0, read=5.0, write=5.0, total=10.0
)

# File upload APIs
upload_timeouts = TimeoutConfig(
    connect=10.0, read=30.0, write=300.0, total=600.0
)

# Long-running processing
processing_timeouts = TimeoutConfig(
    connect=5.0, read=120.0, write=30.0, total=180.0
)
```

## Metrics and Monitoring

### Advanced Metrics

```python
# Get comprehensive metrics
metrics = client.get_metrics()

# Basic metrics
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']:.1%}")
print(f"Average response time: {metrics['average_response_time']:.3f}s")

# Advanced policy metrics
print(f"Retry attempts: {metrics['retry_attempts']}")
print(f"Circuit breaker activations: {metrics['circuit_breaker_activations']}")
print(f"Load balancer selections: {metrics['load_balancer_selections']}")

# Endpoint-specific metrics
for endpoint_url, count in metrics['endpoint_failures'].items():
    print(f"Failures on {endpoint_url}: {count}")
```

### Endpoint Status

```python
# Get detailed endpoint status
endpoint_status = client.get_endpoint_status()

for endpoint in endpoint_status:
    print(f"Endpoint: {endpoint['url']}")
    print(f"  Health: {endpoint['health']}")
    print(f"  Available: {endpoint['available']}")
    print(f"  Success Rate: {endpoint['success_rate']:.1%}")
    print(f"  Avg Response Time: {endpoint['average_response_time']:.3f}s")
    print(f"  Active Connections: {endpoint['active_connections']}")
    print(f"  Circuit Breaker Open: {endpoint['circuit_breaker_open']}")
```

### Health Checks

```python
# Comprehensive health check
health = await client.health_check()

print(f"Status: {health['status']}")
print(f"Healthy Endpoints: {health['healthy_endpoints']}/{health['total_endpoints']}")
print(f"Load Balancer Strategy: {health['load_balancer_strategy']}")

if health['status'] == 'healthy':
    print(f"Response Time: {health['response_time']:.3f}s")
```

## Best Practices

### 1. Retry Policy Selection

- **Use Exponential Backoff** for most scenarios to avoid overwhelming services
- **Add Jitter** to prevent thundering herd problems
- **Set Reasonable Limits** to avoid infinite retry loops
- **Customize Status Codes** based on your service's error responses

```python
# Recommended retry policy
retry_policy = AdvancedRetryPolicy(
    strategy=RetryStrategy.EXPONENTIAL,
    max_attempts=4,
    base_delay=0.5,
    max_delay=30.0,
    jitter=True,
    retry_on_status_codes=[500, 502, 503, 504, 429]
)
```

### 2. Load Balancer Strategy

- **Use Least Response Time** for performance-critical applications
- **Use Weighted Round Robin** when endpoints have different capacities
- **Use Health-Based** strategies for high availability requirements
- **Monitor Endpoint Health** continuously

```python
# Recommended for most scenarios
config = LoadBalancerConfig(
    strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
    health_check_interval=30.0,
    failure_threshold=3,
    circuit_breaker_timeout=60.0
)
```

### 3. Connection Pool Optimization

- **Size Pools Based on Load** using Little's Law: Connections = RPS × Response Time
- **Monitor Pool Utilization** to avoid connection exhaustion
- **Use Keep-Alive** for better performance
- **Adjust Based on Metrics** regularly

```python
# Calculate optimal pool size
expected_rps = 50.0
avg_response_time = 0.3
optimal_connections = int(expected_rps * avg_response_time * 1.2)  # 20% buffer
```

### 4. Timeout Configuration

- **Set Conservative Timeouts** initially, then optimize based on metrics
- **Use Different Timeouts** for different operation types
- **Monitor Timeout Rates** to identify issues
- **Consider Network Latency** in timeout calculations

### 5. Monitoring and Alerting

- **Track Success Rates** and alert on degradation
- **Monitor Response Times** for performance issues
- **Watch Circuit Breaker States** for service health
- **Alert on Endpoint Failures** for quick response

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from fastapi_microservices_sdk.communication.http.enhanced_http_client import (
    EnhancedHTTPClientWithPolicies,
    EnhancedHTTPClientAdvancedConfig
)

app = FastAPI()

# Create client configuration
def get_http_client_config():
    return EnhancedHTTPClientAdvancedConfig(
        service_urls=[
            "https://api1.example.com",
            "https://api2.example.com"
        ],
        retry_policy=AdvancedRetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            max_attempts=3
        ),
        load_balancer=LoadBalancerConfig(
            strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME
        )
    )

# Dependency injection
async def get_http_client():
    config = get_http_client_config()
    client = EnhancedHTTPClientWithPolicies(config)
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()

@app.get("/users/{user_id}")
async def get_user(
    user_id: int, 
    client: EnhancedHTTPClientWithPolicies = Depends(get_http_client)
):
    response = await client.get(f"/users/{user_id}")
    return response.json()

@app.get("/health")
async def health_check(
    client: EnhancedHTTPClientWithPolicies = Depends(get_http_client)
):
    return await client.health_check()

@app.get("/metrics")
async def get_metrics(
    client: EnhancedHTTPClientWithPolicies = Depends(get_http_client)
):
    return client.get_metrics()
```

### Background Task Integration

```python
import asyncio
from fastapi import BackgroundTasks

async def sync_data_with_retry():
    config = EnhancedHTTPClientAdvancedConfig(
        service_urls=["https://data-api.example.com"],
        retry_policy=AdvancedRetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL,
            max_attempts=5,
            base_delay=2.0
        )
    )
    
    client = EnhancedHTTPClientWithPolicies(config)
    
    async with client.lifespan():
        try:
            response = await client.get("/data/sync")
            print(f"Sync completed: {response.status_code}")
            
            # Get metrics
            metrics = client.get_metrics()
            print(f"Retry attempts: {metrics['retry_attempts']}")
            
        except Exception as e:
            print(f"Sync failed: {e}")

@app.post("/trigger-sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_data_with_retry)
    return {"message": "Sync triggered"}
```

## Troubleshooting

### Common Issues

#### 1. High Retry Rates

**Symptoms**: Many retry attempts, degraded performance

**Solutions**:
- Check downstream service health
- Adjust retry policy (reduce max_attempts or increase delays)
- Implement circuit breakers
- Monitor endpoint health

#### 2. Load Balancer Not Distributing Evenly

**Symptoms**: Some endpoints get more traffic than others

**Solutions**:
- Check endpoint weights configuration
- Verify health check configuration
- Monitor endpoint response times
- Consider different load balancing strategy

#### 3. Connection Pool Exhaustion

**Symptoms**: Connection timeout errors, slow responses

**Solutions**:
- Increase max_connections
- Optimize connection pool based on load
- Check for connection leaks
- Monitor pool utilization

#### 4. Circuit Breakers Opening Frequently

**Symptoms**: "Circuit breaker is open" errors

**Solutions**:
- Increase failure_threshold
- Check downstream service health
- Adjust circuit breaker timeout
- Implement proper fallback strategies

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# The client will log detailed information about:
# - Retry attempts and delays
# - Load balancer selections
# - Endpoint health changes
# - Circuit breaker state transitions
# - Request/response details
```

### Performance Tuning

#### Optimize for High Throughput

```python
config = EnhancedHTTPClientAdvancedConfig(
    service_urls=["https://api.example.com"],
    
    # Aggressive connection pooling
    max_connections=500,
    max_keepalive_connections=100,
    keepalive_expiry=30.0,
    
    # Fast retry policy
    retry_policy=AdvancedRetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=2,
        base_delay=0.1,
        max_delay=1.0
    ),
    
    # Performance-focused load balancing
    load_balancer=LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        health_check_interval=60.0
    ),
    
    # Optimized timeouts
    timeout=TimeoutConfig(
        connect=2.0,
        read=10.0,
        write=10.0,
        total=15.0
    )
)
```

#### Optimize for Reliability

```python
config = EnhancedHTTPClientAdvancedConfig(
    service_urls=[
        "https://api1.example.com",
        "https://api2.example.com",
        "https://api3.example.com"
    ],
    
    # Conservative retry policy
    retry_policy=AdvancedRetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=5,
        base_delay=1.0,
        max_delay=60.0,
        jitter=True
    ),
    
    # Health-focused load balancing
    load_balancer=LoadBalancerConfig(
        strategy=LoadBalancingStrategy.HEALTH_BASED,
        health_check_interval=15.0,
        failure_threshold=2,
        circuit_breaker_timeout=120.0
    ),
    
    # Conservative timeouts
    timeout=TimeoutConfig(
        connect=10.0,
        read=60.0,
        write=60.0,
        total=120.0
    ),
    
    # Enable all monitoring
    enable_logging_interceptor=True,
    enable_metrics_interceptor=True,
    enable_health_checks=True
)
```

This comprehensive documentation covers all aspects of the Advanced Retry Policies and Load Balancing system, providing developers with the knowledge needed to implement resilient HTTP communication in their microservices architectures.
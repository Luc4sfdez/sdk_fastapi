#!/usr/bin/env python3
"""
Advanced Retry Policies and Load Balancing Example.

This example demonstrates how to use advanced retry policies and load balancing
strategies for resilient HTTP communication in microservices architectures.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from fastapi_microservices_sdk.communication.http.advanced_policies import (
    AdvancedRetryPolicy,
    RetryStrategy,
    TimeoutConfig,
    LoadBalancerConfig,
    LoadBalancingStrategy,
    ServiceEndpoint,
    EndpointHealth,
    create_load_balancer,
    LoggingInterceptor,
    MetricsInterceptor,
    ConnectionPoolOptimizer,
    RetryAttempt
)
from fastapi_microservices_sdk.communication.logging import CommunicationLogger


async def retry_policy_examples():
    """Demonstrate different retry policy strategies."""
    print("\n🔄 Advanced Retry Policy Examples")
    print("=" * 50)
    
    # 1. Exponential Backoff with Jitter
    print("\n📈 Exponential Backoff with Jitter")
    exponential_policy = AdvancedRetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=5,
        base_delay=0.5,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True,
        jitter_range=0.2
    )
    
    print("Retry delays:")
    for attempt in range(1, 6):
        delay = exponential_policy.calculate_delay(attempt)
        should_retry = exponential_policy.should_retry(attempt, status_code=500)
        print(f"  Attempt {attempt}: {delay:.2f}s (retry: {should_retry})")
    
    # 2. Linear Backoff
    print("\n📊 Linear Backoff")
    linear_policy = AdvancedRetryPolicy(
        strategy=RetryStrategy.LINEAR,
        max_attempts=4,
        base_delay=1.0,
        jitter=False
    )
    
    print("Retry delays:")
    for attempt in range(1, 5):
        delay = linear_policy.calculate_delay(attempt)
        print(f"  Attempt {attempt}: {delay:.2f}s")
    
    # 3. Fibonacci Backoff
    print("\n🌀 Fibonacci Backoff")
    fibonacci_policy = AdvancedRetryPolicy(
        strategy=RetryStrategy.FIBONACCI,
        max_attempts=6,
        base_delay=0.5,
        jitter=False
    )
    
    print("Retry delays:")
    for attempt in range(1, 7):
        delay = fibonacci_policy.calculate_delay(attempt)
        print(f"  Attempt {attempt}: {delay:.2f}s")
    
    # 4. Custom Retry Function
    print("\n🎯 Custom Retry Function")
    def custom_delay_function(attempt: int) -> float:
        """Custom delay: square root of attempt number."""
        return (attempt ** 0.5) * 2.0
    
    custom_policy = AdvancedRetryPolicy(
        strategy=RetryStrategy.CUSTOM,
        custom_retry_function=custom_delay_function,
        max_attempts=5,
        jitter=False
    )
    
    print("Custom retry delays:")
    for attempt in range(1, 6):
        delay = custom_policy.calculate_delay(attempt)
        print(f"  Attempt {attempt}: {delay:.2f}s")
    
    # 5. Retry Decision Logic
    print("\n🤔 Retry Decision Logic")
    policy = AdvancedRetryPolicy(
        max_attempts=3,
        retry_on_status_codes=[500, 502, 503, 504, 429]
    )
    
    test_cases = [
        (1, 500, "Server Error"),
        (1, 404, "Not Found"),
        (1, 429, "Rate Limited"),
        (3, 500, "Max Attempts Reached"),
        (2, 200, "Success")
    ]
    
    for attempt, status_code, description in test_cases:
        should_retry = policy.should_retry(attempt, status_code=status_code)
        print(f"  {description} (attempt {attempt}, status {status_code}): retry = {should_retry}")


async def load_balancing_examples():
    """Demonstrate different load balancing strategies."""
    print("\n⚖️ Load Balancing Strategy Examples")
    print("=" * 50)
    
    # Create test endpoints
    endpoints = [
        ServiceEndpoint(url="https://api1.example.com", weight=1.0),
        ServiceEndpoint(url="https://api2.example.com", weight=2.0),
        ServiceEndpoint(url="https://api3.example.com", weight=1.0),
        ServiceEndpoint(url="https://api4.example.com", weight=3.0)
    ]
    
    # Mark all as healthy
    for endpoint in endpoints:
        endpoint.update_health(EndpointHealth.HEALTHY)
    
    # Simulate different loads
    endpoints[0].active_connections = 5
    endpoints[1].active_connections = 2
    endpoints[2].active_connections = 8
    endpoints[3].active_connections = 1
    
    # Simulate response times
    endpoints[0].total_requests = 100
    endpoints[0].average_response_time = 0.3
    endpoints[1].total_requests = 100
    endpoints[1].average_response_time = 0.5
    endpoints[2].total_requests = 100
    endpoints[2].average_response_time = 0.2
    endpoints[3].total_requests = 100
    endpoints[3].average_response_time = 0.8
    
    config = LoadBalancerConfig()
    
    # 1. Round Robin
    print("\n🔄 Round Robin Load Balancing")
    rr_lb = create_load_balancer(LoadBalancingStrategy.ROUND_ROBIN, config)
    for endpoint in endpoints:
        rr_lb.endpoints.append(endpoint)
    
    print("Selection order:")
    for i in range(8):
        selected = await rr_lb.select_endpoint()
        print(f"  Request {i+1}: {selected.url}")
    
    # 2. Weighted Round Robin
    print("\n⚖️ Weighted Round Robin Load Balancing")
    wrr_lb = create_load_balancer(LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN, config)
    for endpoint in endpoints:
        wrr_lb.endpoints.append(endpoint)
    
    print("Selection with weights (api2=2.0, api4=3.0):")
    selections = {}
    for i in range(20):
        selected = await wrr_lb.select_endpoint()
        url = selected.url
        selections[url] = selections.get(url, 0) + 1
    
    for url, count in selections.items():
        weight = next(ep.weight for ep in endpoints if ep.url == url)
        print(f"  {url}: {count} selections (weight: {weight})")
    
    # 3. Least Connections
    print("\n🔗 Least Connections Load Balancing")
    lc_lb = create_load_balancer(LoadBalancingStrategy.LEAST_CONNECTIONS, config)
    for endpoint in endpoints:
        lc_lb.endpoints.append(endpoint)
    
    print("Active connections:")
    for endpoint in endpoints:
        print(f"  {endpoint.url}: {endpoint.active_connections} connections")
    
    selected = await lc_lb.select_endpoint()
    print(f"Selected: {selected.url} (least connections)")
    
    # 4. Least Response Time
    print("\n⏱️ Least Response Time Load Balancing")
    lrt_lb = create_load_balancer(LoadBalancingStrategy.LEAST_RESPONSE_TIME, config)
    for endpoint in endpoints:
        lrt_lb.endpoints.append(endpoint)
    
    print("Average response times:")
    for endpoint in endpoints:
        print(f"  {endpoint.url}: {endpoint.average_response_time:.3f}s")
    
    selected = await lrt_lb.select_endpoint()
    print(f"Selected: {selected.url} (fastest response time)")
    
    # 5. Random Selection
    print("\n🎲 Random Load Balancing")
    random_lb = create_load_balancer(LoadBalancingStrategy.RANDOM, config)
    for endpoint in endpoints:
        random_lb.endpoints.append(endpoint)
    
    print("Random selections:")
    for i in range(5):
        selected = await random_lb.select_endpoint()
        print(f"  Selection {i+1}: {selected.url}")


async def endpoint_health_management_example():
    """Demonstrate endpoint health management."""
    print("\n🏥 Endpoint Health Management Example")
    print("=" * 50)
    
    # Create endpoints with different health states
    endpoints = [
        ServiceEndpoint(url="https://healthy-api.example.com"),
        ServiceEndpoint(url="https://degraded-api.example.com"),
        ServiceEndpoint(url="https://unhealthy-api.example.com"),
        ServiceEndpoint(url="https://circuit-breaker-api.example.com")
    ]
    
    # Set different health states
    endpoints[0].update_health(EndpointHealth.HEALTHY)
    endpoints[1].update_health(EndpointHealth.DEGRADED)
    endpoints[2].update_health(EndpointHealth.UNHEALTHY)
    endpoints[3].update_health(EndpointHealth.HEALTHY)
    
    print("Initial endpoint states:")
    for endpoint in endpoints:
        print(f"  {endpoint.url}: {endpoint.health.value} (available: {endpoint.is_available})")
    
    # Simulate circuit breaker opening
    print("\n⚡ Opening circuit breaker for one endpoint...")
    endpoints[3].open_circuit_breaker(timeout_seconds=2.0)
    
    print("States after circuit breaker:")
    for endpoint in endpoints:
        print(f"  {endpoint.url}: {endpoint.health.value} (available: {endpoint.is_available})")
    
    # Test load balancer with mixed health states
    config = LoadBalancerConfig()
    lb = create_load_balancer(LoadBalancingStrategy.ROUND_ROBIN, config)
    for endpoint in endpoints:
        lb.endpoints.append(endpoint)
    
    print("\nAvailable endpoints for load balancing:")
    healthy_endpoints = lb.get_healthy_endpoints()
    for endpoint in healthy_endpoints:
        print(f"  {endpoint.url}")
    
    # Wait for circuit breaker to recover
    print("\n⏳ Waiting for circuit breaker recovery...")
    await asyncio.sleep(2.1)
    
    print("States after circuit breaker recovery:")
    for endpoint in endpoints:
        print(f"  {endpoint.url}: {endpoint.health.value} (available: {endpoint.is_available})")


async def request_metrics_example():
    """Demonstrate request metrics tracking."""
    print("\n📊 Request Metrics Tracking Example")
    print("=" * 50)
    
    # Create endpoint and simulate requests
    endpoint = ServiceEndpoint(url="https://api.example.com")
    endpoint.update_health(EndpointHealth.HEALTHY)
    
    print("Simulating requests...")
    
    # Simulate successful requests
    for i in range(10):
        endpoint.record_request_start()
        # Simulate processing time
        await asyncio.sleep(0.01)
        response_time = 0.1 + (i * 0.02)  # Varying response times
        endpoint.record_request_end(success=True, response_time=response_time)
    
    # Simulate some failed requests
    for i in range(3):
        endpoint.record_request_start()
        await asyncio.sleep(0.01)
        endpoint.record_request_end(success=False, response_time=1.0)
    
    print(f"\nEndpoint Metrics:")
    print(f"  URL: {endpoint.url}")
    print(f"  Total Requests: {endpoint.total_requests}")
    print(f"  Successful Requests: {endpoint.successful_requests}")
    print(f"  Failed Requests: {endpoint.failed_requests}")
    print(f"  Success Rate: {endpoint.success_rate:.1%}")
    print(f"  Average Response Time: {endpoint.average_response_time:.3f}s")
    print(f"  Last Response Time: {endpoint.last_response_time:.3f}s")
    print(f"  Active Connections: {endpoint.active_connections}")
    print(f"  Consecutive Successes: {endpoint.consecutive_successes}")
    print(f"  Consecutive Failures: {endpoint.consecutive_failures}")


async def interceptor_example():
    """Demonstrate request/response interceptors."""
    print("\n🔍 Request/Response Interceptor Example")
    print("=" * 50)
    
    # Create interceptors
    logger = CommunicationLogger("interceptor_example")
    logging_interceptor = LoggingInterceptor(logger)
    metrics_interceptor = MetricsInterceptor()
    
    # Mock request and response
    class MockRequest:
        def __init__(self):
            self.method = "GET"
            self.url = "https://api.example.com/users"
            self.headers = {"Authorization": "Bearer token123"}
    
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.headers = {"Content-Type": "application/json"}
    
    endpoint = ServiceEndpoint(url="https://api.example.com")
    
    print("Processing requests with interceptors...")
    
    # Simulate multiple requests
    for i in range(5):
        request = MockRequest()
        
        # Request interception
        await logging_interceptor.intercept_request(request, endpoint, i + 1)
        await metrics_interceptor.intercept_request(request, endpoint, i + 1)
        
        # Simulate request processing
        start_time = time.time() - (0.1 + i * 0.05)  # Varying response times
        
        # Response interception
        status_code = 200 if i < 4 else 500  # Last request fails
        response = MockResponse(status_code)
        
        await logging_interceptor.intercept_response(response, endpoint, start_time)
        await metrics_interceptor.intercept_response(response, endpoint, start_time)
    
    # Get metrics summary
    print("\n📈 Collected Metrics:")
    metrics = metrics_interceptor.get_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")


async def timeout_configuration_example():
    """Demonstrate timeout configuration."""
    print("\n⏱️ Timeout Configuration Example")
    print("=" * 50)
    
    # Different timeout configurations for different scenarios
    
    # 1. Fast API calls
    fast_config = TimeoutConfig(
        connect=2.0,
        read=5.0,
        write=5.0,
        total=10.0
    )
    
    print("Fast API Configuration:")
    print(f"  Connect: {fast_config.connect}s")
    print(f"  Read: {fast_config.read}s")
    print(f"  Write: {fast_config.write}s")
    print(f"  Total: {fast_config.total}s")
    
    # 2. Slow processing APIs
    slow_config = TimeoutConfig(
        connect=5.0,
        read=60.0,
        write=30.0,
        total=120.0
    )
    
    print("\nSlow Processing API Configuration:")
    print(f"  Connect: {slow_config.connect}s")
    print(f"  Read: {slow_config.read}s")
    print(f"  Write: {slow_config.write}s")
    print(f"  Total: {slow_config.total}s")
    
    # 3. File upload APIs
    upload_config = TimeoutConfig(
        connect=10.0,
        read=30.0,
        write=300.0,  # Long write timeout for uploads
        total=600.0
    )
    
    print("\nFile Upload API Configuration:")
    print(f"  Connect: {upload_config.connect}s")
    print(f"  Read: {upload_config.read}s")
    print(f"  Write: {upload_config.write}s")
    print(f"  Total: {upload_config.total}s")
    
    # Convert to httpx timeout
    httpx_timeout = fast_config.to_httpx_timeout()
    print(f"\nConverted to httpx.Timeout: {httpx_timeout}")


async def connection_pool_optimization_example():
    """Demonstrate connection pool optimization."""
    print("\n🏊 Connection Pool Optimization Example")
    print("=" * 50)
    
    optimizer = ConnectionPoolOptimizer()
    
    # Default configuration
    default_limits = optimizer.create_limits()
    print("Default Configuration:")
    print(f"  Max Connections: {default_limits.max_connections}")
    print(f"  Max Keepalive: {default_limits.max_keepalive_connections}")
    print(f"  Keepalive Expiry: {default_limits.keepalive_expiry}s")
    
    # Optimize for different load scenarios
    scenarios = [
        (10.0, 0.1, "Low Load (10 RPS, 100ms avg)"),
        (100.0, 0.5, "Medium Load (100 RPS, 500ms avg)"),
        (500.0, 1.0, "High Load (500 RPS, 1s avg)"),
        (1000.0, 2.0, "Very High Load (1000 RPS, 2s avg)")
    ]
    
    for rps, avg_time, description in scenarios:
        limits = optimizer.optimize_for_load(rps, avg_time)
        print(f"\n{description}:")
        print(f"  Recommended Max Connections: {limits.max_connections}")
        print(f"  Recommended Keepalive: {limits.max_keepalive_connections}")
        print(f"  Calculation: {rps} RPS × {avg_time}s × 1.2 buffer = {int(rps * avg_time * 1.2)} connections")


async def comprehensive_example():
    """Comprehensive example combining all features."""
    print("\n🚀 Comprehensive Advanced Policies Example")
    print("=" * 50)
    
    # Create advanced retry policy
    retry_policy = AdvancedRetryPolicy(
        strategy=RetryStrategy.EXPONENTIAL,
        max_attempts=4,
        base_delay=0.5,
        max_delay=10.0,
        jitter=True,
        retry_on_status_codes=[500, 502, 503, 504, 429]
    )
    
    # Create load balancer with health checks
    lb_config = LoadBalancerConfig(
        strategy=LoadBalancingStrategy.LEAST_RESPONSE_TIME,
        health_check_interval=30.0,
        failure_threshold=3,
        circuit_breaker_timeout=60.0
    )
    
    load_balancer = create_load_balancer(lb_config.strategy, lb_config)
    
    # Add multiple endpoints
    endpoints = [
        "https://api1.example.com",
        "https://api2.example.com", 
        "https://api3.example.com"
    ]
    
    for url in endpoints:
        endpoint = load_balancer.add_endpoint(url, weight=1.0)
        endpoint.update_health(EndpointHealth.HEALTHY)
    
    # Create timeout configuration
    timeout_config = TimeoutConfig(
        connect=5.0,
        read=30.0,
        write=30.0,
        total=60.0
    )
    
    # Create connection pool optimizer
    optimizer = ConnectionPoolOptimizer()
    pool_limits = optimizer.optimize_for_load(expected_rps=50.0, avg_response_time=0.3)
    
    # Create interceptors
    logger = CommunicationLogger("comprehensive_example")
    logging_interceptor = LoggingInterceptor(logger)
    metrics_interceptor = MetricsInterceptor()
    
    print("Configuration Summary:")
    print(f"  Retry Strategy: {retry_policy.strategy.value}")
    print(f"  Max Retry Attempts: {retry_policy.max_attempts}")
    print(f"  Load Balancing: {lb_config.strategy.value}")
    print(f"  Endpoints: {len(endpoints)}")
    print(f"  Connection Pool: {pool_limits.max_connections} max connections")
    print(f"  Timeout: {timeout_config.total}s total")
    
    # Simulate request processing
    print("\nSimulating request with full policy stack...")
    
    try:
        # Select endpoint
        selected_endpoint = await load_balancer.select_endpoint()
        print(f"Selected endpoint: {selected_endpoint.url}")
        
        # Simulate retry attempts
        for attempt in range(1, retry_policy.max_attempts + 1):
            delay = retry_policy.calculate_delay(attempt)
            should_retry = retry_policy.should_retry(attempt, status_code=500)
            
            print(f"  Attempt {attempt}: delay={delay:.2f}s, will_retry={should_retry}")
            
            if attempt == 3:  # Simulate success on 3rd attempt
                print(f"  ✅ Request succeeded on attempt {attempt}")
                selected_endpoint.record_request_start()
                selected_endpoint.record_request_end(success=True, response_time=0.25)
                break
            elif should_retry:
                print(f"  ❌ Request failed, retrying after {delay:.2f}s...")
                await asyncio.sleep(min(delay, 0.1))  # Shortened for demo
        
        # Show final metrics
        print(f"\nFinal endpoint metrics:")
        print(f"  Success Rate: {selected_endpoint.success_rate:.1%}")
        print(f"  Average Response Time: {selected_endpoint.average_response_time:.3f}s")
        print(f"  Total Requests: {selected_endpoint.total_requests}")
    
    except Exception as e:
        print(f"Request failed: {e}")


async def main():
    """Run all examples."""
    print("🌟 Advanced Retry Policies and Load Balancing Examples")
    print("=" * 70)
    
    try:
        await retry_policy_examples()
        await load_balancing_examples()
        await endpoint_health_management_example()
        await request_metrics_example()
        await interceptor_example()
        await timeout_configuration_example()
        await connection_pool_optimization_example()
        await comprehensive_example()
        
        print("\n✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error in examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
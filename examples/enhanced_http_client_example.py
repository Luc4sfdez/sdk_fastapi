#!/usr/bin/env python3
"""
Enhanced HTTP Client Example.

This example demonstrates how to use the Enhanced HTTP Client with all its advanced features:
- Circuit breaker pattern for fault tolerance
- Advanced retry mechanisms with exponential backoff
- Request/Response middleware pipeline
- Connection pooling and resource management
- Comprehensive monitoring and metrics
- Security integration (authentication, SSL/TLS)
- Caching capabilities
- Rate limiting
- Request tracing and correlation
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from fastapi_microservices_sdk.communication.http.enhanced_client import (
    EnhancedHTTPClient,
    EnhancedHTTPClientConfig,
    RetryConfig,
    CircuitBreakerConfig,
    CacheConfig,
    AuthenticationConfig,
    RateLimitConfig,
    HTTPMethod,
    CacheStrategy,
    AuthenticationType
)
from fastapi_microservices_sdk.communication.exceptions import (
    CommunicationError,
    CommunicationTimeoutError,
    CommunicationConnectionError
)


class CustomRequestMiddleware:
    """Custom request middleware example."""
    
    async def process_request(self, request):
        """Add custom headers to all requests."""
        request.headers["X-Client-Version"] = "1.0.0"
        request.headers["X-Request-Time"] = datetime.utcnow().isoformat()
        print(f"🔄 Processing request: {request.method} {request.url}")
        return request


class CustomResponseMiddleware:
    """Custom response middleware example."""
    
    async def process_response(self, response):
        """Process all responses."""
        print(f"✅ Response received: {response.status_code} in {response.elapsed.total_seconds():.3f}s")
        return response


async def basic_usage_example():
    """Basic usage example with minimal configuration."""
    print("\n🚀 Basic Enhanced HTTP Client Example")
    print("=" * 50)
    
    # Create basic configuration
    config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=10.0
    )
    
    # Create client
    client = EnhancedHTTPClient(config)
    
    try:
        # Use context manager for automatic connection management
        async with client.lifespan():
            print(f"📡 Connected to: {config.base_url}")
            
            # Make simple GET request
            response = await client.get("/get", params={"test": "value"})
            print(f"GET Response: {response.status_code}")
            
            # Make POST request with JSON data
            response = await client.post("/post", json={
                "message": "Hello from Enhanced HTTP Client!",
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"POST Response: {response.status_code}")
            
            # Get client metrics
            metrics = client.get_metrics()
            print(f"📊 Metrics: {metrics['total_requests']} requests, "
                  f"{metrics['success_rate']:.1%} success rate")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def advanced_configuration_example():
    """Advanced configuration example with all features."""
    print("\n🔧 Advanced Configuration Example")
    print("=" * 50)
    
    # Create advanced configuration
    config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=15.0,
        max_connections=50,
        max_keepalive_connections=10,
        
        # Retry configuration
        retry=RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retry_on_status=[500, 502, 503, 504]
        ),
        
        # Circuit breaker configuration
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=3,
            timeout=60.0,
            half_open_max_calls=3
        ),
        
        # Cache configuration
        cache=CacheConfig(
            strategy=CacheStrategy.MEMORY,
            ttl=300,  # 5 minutes
            max_size=1000,
            key_prefix="api_cache"
        ),
        
        # Authentication configuration
        authentication=AuthenticationConfig(
            type=AuthenticationType.BEARER,
            token="your-api-token-here"
        ),
        
        # Rate limiting configuration
        rate_limit=RateLimitConfig(
            requests_per_second=10.0,
            burst_size=20
        ),
        
        # Security settings
        verify_ssl=True,
        
        # Default headers
        default_headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        user_agent="MyApp/1.0 (Enhanced HTTP Client)",
        
        # Tracing
        enable_tracing=True,
        trace_header_name="X-Trace-ID"
    )
    
    # Create client
    client = EnhancedHTTPClient(config)
    
    # Add custom middleware
    client.add_request_middleware(CustomRequestMiddleware())
    client.add_response_middleware(CustomResponseMiddleware())
    
    try:
        async with client.lifespan():
            print(f"📡 Connected with advanced configuration")
            
            # Test caching with multiple requests
            print("\n🗄️ Testing caching...")
            for i in range(3):
                response = await client.get("/get", params={"cache_test": "value"})
                print(f"Request {i+1}: {response.status_code}")
            
            # Test different HTTP methods
            print("\n🔄 Testing HTTP methods...")
            
            # GET with parameters
            response = await client.get("/get", params={
                "param1": "value1",
                "param2": "value2"
            })
            print(f"GET: {response.status_code}")
            
            # POST with JSON
            response = await client.post("/post", json={
                "data": "test data",
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"POST: {response.status_code}")
            
            # PUT with JSON
            response = await client.put("/put", json={
                "id": 1,
                "name": "Updated Item"
            })
            print(f"PUT: {response.status_code}")
            
            # PATCH with JSON
            response = await client.patch("/patch", json={
                "field": "updated_value"
            })
            print(f"PATCH: {response.status_code}")
            
            # DELETE
            response = await client.delete("/delete")
            print(f"DELETE: {response.status_code}")
            
            # Get comprehensive metrics
            metrics = client.get_metrics()
            print(f"\n📊 Final Metrics:")
            print(f"  Total requests: {metrics['total_requests']}")
            print(f"  Success rate: {metrics['success_rate']:.1%}")
            print(f"  Average response time: {metrics['average_response_time']:.3f}s")
            print(f"  Cache hits: {metrics['cache_hits']}")
            print(f"  Cache hit rate: {metrics['cache_hit_rate']:.1%}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def error_handling_example():
    """Error handling and resilience example."""
    print("\n🛡️ Error Handling and Resilience Example")
    print("=" * 50)
    
    # Configuration with aggressive retry and circuit breaker
    config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=5.0,
        retry=RetryConfig(
            max_retries=2,
            initial_delay=0.5,
            max_delay=5.0
        ),
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=30.0
        )
    )
    
    client = EnhancedHTTPClient(config)
    
    try:
        async with client.lifespan():
            print("📡 Testing error handling...")
            
            # Test timeout handling
            try:
                print("\n⏱️ Testing timeout...")
                response = await client.get("/delay/10", timeout=2.0)
                print(f"Response: {response.status_code}")
            except CommunicationTimeoutError as e:
                print(f"✅ Timeout handled correctly: {e}")
            
            # Test retry on server errors
            try:
                print("\n🔄 Testing retry on server errors...")
                response = await client.get("/status/500")
                print(f"Response: {response.status_code}")
            except CommunicationError as e:
                print(f"✅ Server error handled with retries: {e}")
            
            # Test circuit breaker (simulate multiple failures)
            print("\n⚡ Testing circuit breaker...")
            for i in range(5):
                try:
                    response = await client.get("/status/500")
                    print(f"Attempt {i+1}: {response.status_code}")
                except CommunicationError as e:
                    print(f"Attempt {i+1} failed: {e}")
            
            # Check circuit breaker state
            print(f"Circuit breaker state: {client._circuit_breaker.state.value}")
            
            # Get error metrics
            metrics = client.get_metrics()
            print(f"\n📊 Error Metrics:")
            print(f"  Total requests: {metrics['total_requests']}")
            print(f"  Failed requests: {metrics['failed_requests']}")
            print(f"  Circuit breaker opens: {metrics['circuit_breaker_opens']}")
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


async def authentication_example():
    """Authentication example with different auth types."""
    print("\n🔐 Authentication Example")
    print("=" * 50)
    
    # Bearer token authentication
    print("\n🎫 Bearer Token Authentication")
    bearer_config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        authentication=AuthenticationConfig(
            type=AuthenticationType.BEARER,
            token="your-bearer-token"
        )
    )
    
    bearer_client = EnhancedHTTPClient(bearer_config)
    
    try:
        async with bearer_client.lifespan():
            response = await bearer_client.get("/bearer")
            print(f"Bearer auth response: {response.status_code}")
    except Exception as e:
        print(f"Bearer auth error: {e}")
    
    # Basic authentication
    print("\n🔑 Basic Authentication")
    basic_config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        authentication=AuthenticationConfig(
            type=AuthenticationType.BASIC,
            username="testuser",
            password="testpass"
        )
    )
    
    basic_client = EnhancedHTTPClient(basic_config)
    
    try:
        async with basic_client.lifespan():
            response = await basic_client.get("/basic-auth/testuser/testpass")
            print(f"Basic auth response: {response.status_code}")
    except Exception as e:
        print(f"Basic auth error: {e}")
    
    # API Key authentication
    print("\n🗝️ API Key Authentication")
    api_key_config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        authentication=AuthenticationConfig(
            type=AuthenticationType.API_KEY,
            api_key="your-api-key",
            api_key_header="X-API-Key"
        )
    )
    
    api_key_client = EnhancedHTTPClient(api_key_config)
    
    try:
        async with api_key_client.lifespan():
            response = await api_key_client.get("/get")
            print(f"API key auth response: {response.status_code}")
    except Exception as e:
        print(f"API key auth error: {e}")


async def monitoring_example():
    """Monitoring and health check example."""
    print("\n📊 Monitoring and Health Check Example")
    print("=" * 50)
    
    config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        timeout=10.0
    )
    
    client = EnhancedHTTPClient(config)
    
    try:
        async with client.lifespan():
            # Make some requests to generate metrics
            for i in range(5):
                try:
                    response = await client.get(f"/get?request={i}")
                    print(f"Request {i+1}: {response.status_code}")
                except Exception as e:
                    print(f"Request {i+1} failed: {e}")
            
            # Perform health check
            print("\n🏥 Health Check")
            health = await client.health_check()
            print(f"Health status: {health['status']}")
            if health['status'] == 'healthy':
                print(f"Response time: {health['response_time']:.3f}s")
                print(f"Circuit breaker state: {health['circuit_breaker_state']}")
            
            # Get detailed metrics
            print("\n📈 Detailed Metrics")
            metrics = client.get_metrics()
            for key, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")
            
            # Clear cache and reset circuit breaker
            print("\n🧹 Maintenance Operations")
            client.clear_cache()
            print("Cache cleared")
            
            client.reset_circuit_breaker()
            print("Circuit breaker reset")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def rate_limiting_example():
    """Rate limiting example."""
    print("\n🚦 Rate Limiting Example")
    print("=" * 50)
    
    # Configure with strict rate limiting
    config = EnhancedHTTPClientConfig(
        base_url="https://httpbin.org",
        rate_limit=RateLimitConfig(
            requests_per_second=2.0,  # 2 requests per second
            burst_size=3  # Allow burst of 3 requests
        )
    )
    
    client = EnhancedHTTPClient(config)
    
    try:
        async with client.lifespan():
            print("🚦 Testing rate limiting (2 req/s, burst=3)...")
            
            # Make requests and measure timing
            import time
            start_time = time.time()
            
            for i in range(6):
                request_start = time.time()
                try:
                    response = await client.get(f"/get?request={i}")
                    elapsed = time.time() - request_start
                    total_elapsed = time.time() - start_time
                    print(f"Request {i+1}: {response.status_code} "
                          f"(took {elapsed:.2f}s, total {total_elapsed:.2f}s)")
                except Exception as e:
                    print(f"Request {i+1} failed: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    """Run all examples."""
    print("🌟 Enhanced HTTP Client Examples")
    print("=" * 60)
    
    try:
        await basic_usage_example()
        await advanced_configuration_example()
        await error_handling_example()
        await authentication_example()
        await monitoring_example()
        await rate_limiting_example()
        
        print("\n✅ All examples completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error in examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())
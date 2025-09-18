"""
OpenTelemetry Distributed Tracing Example

This example demonstrates the comprehensive distributed tracing capabilities
using OpenTelemetry integration with FastAPI middleware, context propagation,
and multiple exporters.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, Any

# FastAPI imports
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

from fastapi_microservices_sdk.observability import (
    ObservabilityConfig,
    TracingConfig,
    create_development_config
)
from fastapi_microservices_sdk.observability.tracing import (
    TracingProvider,
    TraceProviderConfig,
    ExporterType,
    configure_tracing,
    get_tracer,
    create_span,
    trace_operation,
    get_current_span
)
from fastapi_microservices_sdk.observability.tracing.middleware import (
    TracingMiddleware,
    create_tracing_middleware,
    get_current_trace_info,
    add_trace_attribute,
    add_trace_event
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_basic_tracing():
    """Demonstrate basic tracing functionality."""
    logger.info("=== Basic Tracing Demo ===")
    
    # Configure tracing
    config = TraceProviderConfig(
        service_name="tracing_demo_service",
        service_version="1.0.0",
        exporters=[ExporterType.CONSOLE],
        sampling_rate=1.0  # Sample all traces for demo
    )
    
    provider = configure_tracing(config)
    logger.info("Tracing provider configured")
    
    # Get tracer
    tracer = get_tracer("demo_tracer", "1.0.0")
    
    # Create spans manually
    with tracer.span("demo_operation") as span:
        span.set_attribute("demo.attribute", "demo_value")
        span.set_attribute("demo.number", 42)
        
        # Add event
        span.add_event("demo_event", {"event.data": "test_data"})
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        # Create child span
        with tracer.span("child_operation", parent=span) as child_span:
            child_span.set_attribute("child.attribute", "child_value")
            
            # Simulate more work
            await asyncio.sleep(0.05)
            
            # Add event to child
            child_span.add_event("child_event", {"child.data": "child_test"})
        
        # Add final event to parent
        span.add_event("operation_completed")
    
    logger.info("Basic tracing demo completed")


async def demonstrate_error_tracing():
    """Demonstrate error handling in tracing."""
    logger.info("=== Error Tracing Demo ===")
    
    tracer = get_tracer("error_demo_tracer")
    
    # Demonstrate successful operation
    with tracer.span("successful_operation") as span:
        span.set_attribute("operation.type", "success")
        await asyncio.sleep(0.05)
        span.add_event("operation_success")
    
    # Demonstrate error handling
    try:
        with tracer.span("error_operation") as span:
            span.set_attribute("operation.type", "error")
            span.add_event("operation_started")
            
            # Simulate error
            await asyncio.sleep(0.02)
            raise ValueError("Simulated error for tracing demo")
            
    except ValueError as e:
        logger.info(f"Caught expected error: {e}")
    
    logger.info("Error tracing demo completed")


async def demonstrate_context_propagation():
    """Demonstrate context propagation between operations."""
    logger.info("=== Context Propagation Demo ===")
    
    tracer = get_tracer("context_demo_tracer")
    
    async def service_a_operation():
        """Simulate service A operation."""
        with tracer.span("service_a_operation") as span:
            span.set_attribute("service.name", "service_a")
            span.add_event("service_a_started")
            
            # Simulate work
            await asyncio.sleep(0.03)
            
            # Call service B
            await service_b_operation()
            
            span.add_event("service_a_completed")
    
    async def service_b_operation():
        """Simulate service B operation."""
        # Get current span context
        current_span = get_current_span()
        
        with tracer.span("service_b_operation", parent=current_span) as span:
            span.set_attribute("service.name", "service_b")
            span.add_event("service_b_started")
            
            # Simulate work
            await asyncio.sleep(0.02)
            
            # Call service C
            await service_c_operation()
            
            span.add_event("service_b_completed")
    
    async def service_c_operation():
        """Simulate service C operation."""
        current_span = get_current_span()
        
        with tracer.span("service_c_operation", parent=current_span) as span:
            span.set_attribute("service.name", "service_c")
            span.add_event("service_c_started")
            
            # Simulate work
            await asyncio.sleep(0.01)
            
            span.add_event("service_c_completed")
    
    # Start the operation chain
    await service_a_operation()
    
    logger.info("Context propagation demo completed")


async def demonstrate_database_tracing():
    """Demonstrate database operation tracing."""
    logger.info("=== Database Tracing Demo ===")
    
    tracer = get_tracer("database_demo_tracer")
    
    async def simulate_database_query(query: str, params: Dict[str, Any] = None):
        """Simulate database query with tracing."""
        with tracer.span("database_query", kind="client") as span:
            # Set database attributes
            span.set_attribute("db.system", "postgresql")
            span.set_attribute("db.name", "demo_database")
            span.set_attribute("db.operation", "SELECT")
            span.set_attribute("db.statement", query)  # In production, sanitize this
            
            if params:
                span.set_attribute("db.params_count", len(params))
            
            span.add_event("query_started")
            
            # Simulate query execution
            await asyncio.sleep(0.02)
            
            # Simulate result
            rows_affected = 5
            span.set_attribute("db.rows_affected", rows_affected)
            span.add_event("query_completed", {"rows_returned": rows_affected})
            
            return {"rows": rows_affected, "data": "simulated_data"}
    
    # Simulate multiple database operations
    with tracer.span("user_service_operation") as span:
        span.set_attribute("service.operation", "get_user_profile")
        
        # Query user data
        user_data = await simulate_database_query(
            "SELECT * FROM users WHERE id = $1",
            {"user_id": 123}
        )
        
        # Query user preferences
        preferences = await simulate_database_query(
            "SELECT * FROM user_preferences WHERE user_id = $1",
            {"user_id": 123}
        )
        
        span.set_attribute("user.id", 123)
        span.add_event("user_profile_retrieved")
    
    logger.info("Database tracing demo completed")


async def demonstrate_http_client_tracing():
    """Demonstrate HTTP client tracing."""
    logger.info("=== HTTP Client Tracing Demo ===")
    
    tracer = get_tracer("http_client_demo_tracer")
    
    async def simulate_http_request(method: str, url: str, headers: Dict[str, str] = None):
        """Simulate HTTP request with tracing."""
        with tracer.span(f"HTTP {method}", kind="client") as span:
            # Set HTTP client attributes
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", url)
            span.set_attribute("http.scheme", "https")
            span.set_attribute("net.peer.name", "api.example.com")
            
            if headers:
                for key, value in headers.items():
                    span.set_attribute(f"http.request.header.{key}", value)
            
            span.add_event("request_started")
            
            # Simulate request
            await asyncio.sleep(0.05)
            
            # Simulate response
            status_code = 200
            span.set_attribute("http.status_code", status_code)
            span.set_attribute("http.response.body.size", 1024)
            
            span.add_event("response_received", {"status_code": status_code})
            
            return {"status": status_code, "data": "response_data"}
    
    # Simulate API calls
    with tracer.span("external_api_integration") as span:
        span.set_attribute("integration.name", "external_api")
        
        # Make multiple API calls
        await simulate_http_request("GET", "https://api.example.com/users/123")
        await simulate_http_request("POST", "https://api.example.com/events", {"content-type": "application/json"})
        await simulate_http_request("PUT", "https://api.example.com/users/123/profile")
        
        span.add_event("api_integration_completed")
    
    logger.info("HTTP client tracing demo completed")


def create_demo_fastapi_app() -> FastAPI:
    """Create FastAPI application with tracing middleware."""
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available - skipping FastAPI demo")
        return None
    
    app = FastAPI(title="Tracing Demo API", version="1.0.0")
    
    # Configure tracing
    tracing_config = TracingConfig(
        enabled=True,
        service_name="fastapi_tracing_demo",
        service_version="1.0.0",
        sampling_rate=1.0
    )
    
    # Add tracing middleware
    app.add_middleware(
        TracingMiddleware,
        config=tracing_config,
        exclude_paths=["/health", "/metrics"]
    )
    
    @app.get("/")
    async def root():
        return {"message": "Tracing Demo API"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/users/{user_id}")
    async def get_user(user_id: int, request: Request):
        # Get trace info
        trace_info = get_current_trace_info(request)
        
        # Add custom attributes
        add_trace_attribute(request, "user.id", user_id)
        add_trace_event(request, "user_lookup_started")
        
        # Simulate user lookup
        await asyncio.sleep(0.02)
        
        if user_id == 404:
            add_trace_event(request, "user_not_found")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Simulate database call
        tracer = get_tracer("user_service")
        with tracer.span("database_lookup") as span:
            span.set_attribute("db.table", "users")
            span.set_attribute("user.id", user_id)
            await asyncio.sleep(0.01)
        
        add_trace_event(request, "user_found")
        
        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "trace_info": trace_info
        }
    
    @app.post("/users/{user_id}/events")
    async def create_event(user_id: int, event_data: Dict[str, Any], request: Request):
        # Add custom attributes
        add_trace_attribute(request, "user.id", user_id)
        add_trace_attribute(request, "event.type", event_data.get("type", "unknown"))
        
        # Simulate event processing
        tracer = get_tracer("event_service")
        
        with tracer.span("event_validation") as span:
            span.set_attribute("event.type", event_data.get("type"))
            await asyncio.sleep(0.01)
        
        with tracer.span("event_storage") as span:
            span.set_attribute("db.table", "events")
            await asyncio.sleep(0.02)
        
        add_trace_event(request, "event_created", {"event.id": "evt_123"})
        
        return {"event_id": "evt_123", "status": "created"}
    
    @app.get("/error")
    async def error_endpoint(request: Request):
        add_trace_event(request, "error_endpoint_called")
        raise HTTPException(status_code=500, detail="Simulated error")
    
    return app


async def demonstrate_fastapi_tracing():
    """Demonstrate FastAPI tracing integration."""
    logger.info("=== FastAPI Tracing Demo ===")
    
    if not FASTAPI_AVAILABLE:
        logger.warning("FastAPI not available - skipping FastAPI demo")
        return
    
    app = create_demo_fastapi_app()
    
    # Simulate HTTP requests (in a real scenario, these would come from clients)
    logger.info("FastAPI app created with tracing middleware")
    logger.info("In a real scenario, you would:")
    logger.info("1. Run: uvicorn app:app --host 0.0.0.0 --port 8000")
    logger.info("2. Make requests to: http://localhost:8000/users/123")
    logger.info("3. View traces in your configured backend (Jaeger, Zipkin, etc.)")
    
    logger.info("FastAPI tracing demo setup completed")


async def demonstrate_performance_analysis():
    """Demonstrate performance analysis with tracing."""
    logger.info("=== Performance Analysis Demo ===")
    
    tracer = get_tracer("performance_demo_tracer")
    
    async def slow_operation():
        """Simulate slow operation for performance analysis."""
        with tracer.span("slow_operation") as span:
            span.set_attribute("operation.type", "cpu_intensive")
            
            # Simulate different performance characteristics
            operations = [
                ("initialization", 0.02),
                ("data_processing", 0.08),
                ("validation", 0.03),
                ("finalization", 0.01)
            ]
            
            for op_name, duration in operations:
                with tracer.span(f"slow_operation.{op_name}", parent=span) as sub_span:
                    sub_span.set_attribute("operation.duration_target", duration)
                    
                    start_time = time.time()
                    await asyncio.sleep(duration)
                    actual_duration = time.time() - start_time
                    
                    sub_span.set_attribute("operation.duration_actual", actual_duration)
                    
                    # Add performance event
                    if actual_duration > duration * 1.2:  # 20% slower than expected
                        sub_span.add_event("performance_degradation", {
                            "expected_duration": duration,
                            "actual_duration": actual_duration,
                            "degradation_percent": ((actual_duration - duration) / duration) * 100
                        })
    
    # Run performance analysis
    with tracer.span("performance_analysis_session") as session_span:
        session_span.set_attribute("analysis.type", "performance_benchmark")
        
        # Run multiple iterations
        for i in range(3):
            session_span.add_event(f"iteration_{i}_started")
            await slow_operation()
            session_span.add_event(f"iteration_{i}_completed")
    
    logger.info("Performance analysis demo completed")


async def main():
    """Main demonstration function."""
    logger.info("Starting OpenTelemetry Distributed Tracing Example")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_basic_tracing()
        await demonstrate_error_tracing()
        await demonstrate_context_propagation()
        await demonstrate_database_tracing()
        await demonstrate_http_client_tracing()
        await demonstrate_fastapi_tracing()
        await demonstrate_performance_analysis()
        
        logger.info("=" * 60)
        logger.info("OpenTelemetry Distributed Tracing Example completed successfully!")
        
        # Show tracing status
        from fastapi_microservices_sdk.observability.tracing.provider import get_tracing_status
        status = get_tracing_status()
        logger.info(f"Tracing Status: {status}")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise
    
    finally:
        # Cleanup
        from fastapi_microservices_sdk.observability.tracing.provider import shutdown_tracing
        shutdown_tracing()
        logger.info("Tracing system shutdown")


if __name__ == "__main__":
    asyncio.run(main())
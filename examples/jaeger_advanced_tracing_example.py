"""
Jaeger Advanced Tracing Features Example

This example demonstrates advanced Jaeger integration and tracing capabilities
including intelligent sampling, automatic instrumentation, performance analysis,
bottleneck detection, and comprehensive trace annotation.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any

from fastapi_microservices_sdk.observability.tracing import (
    TracingProvider,
    TraceProviderConfig,
    ExporterType,
    configure_tracing,
    get_tracer
)
from fastapi_microservices_sdk.observability.tracing.sampling import (
    ProbabilisticSampler,
    RateLimitingSampler,
    AdaptiveSampler,
    PrioritySampler,
    CompositeSampler,
    SamplingContext,
    create_adaptive_sampler,
    create_priority_sampler
)
from fastapi_microservices_sdk.observability.tracing.instrumentation import (
    InstrumentationConfig,
    AutoInstrumentation,
    auto_instrument,
    get_instrumentation_status
)
from fastapi_microservices_sdk.observability.tracing.analysis import (
    PerformanceAnalyzer,
    BottleneckType,
    SeverityLevel
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_intelligent_sampling():
    """Demonstrate intelligent sampling strategies."""
    logger.info("=== Intelligent Sampling Demo ===")
    
    # Create different sampling strategies
    probabilistic_sampler = ProbabilisticSampler(0.3, "probabilistic_30")
    rate_limiting_sampler = RateLimitingSampler(10.0, "rate_limit_10")
    adaptive_sampler = create_adaptive_sampler(
        base_sampling_rate=0.1,
        max_sampling_rate=1.0,
        min_sampling_rate=0.001,
        error_rate_threshold=0.05
    )
    
    # Priority-based sampling
    priority_rules = {
        "login": 1.0,      # Always sample login operations
        "payment": 1.0,    # Always sample payment operations
        "health": 0.01,    # Rarely sample health checks
        "metrics": 0.001   # Almost never sample metrics
    }
    priority_sampler = create_priority_sampler(priority_rules, 0.1)
    
    # Composite sampling (combine multiple strategies)
    composite_sampler = CompositeSampler(
        samplers=[probabilistic_sampler, priority_sampler],
        combination_strategy="any"
    )
    
    # Test sampling decisions
    test_operations = [
        ("user_login", {"priority": "high"}),
        ("process_payment", {"amount": 100}),
        ("health_check", {}),
        ("get_metrics", {}),
        ("user_profile", {}),
        ("error_operation", {"error": "true"})
    ]
    
    logger.info("Testing sampling decisions:")
    for operation, attributes in test_operations:
        context = SamplingContext(
            trace_id=f"trace_{random.randint(1000, 9999)}",
            span_name=operation,
            attributes=attributes,
            error_rate=0.02 if "error" not in operation else 0.15
        )
        
        # Test different samplers
        prob_decision = probabilistic_sampler.should_sample(context)
        rate_decision = rate_limiting_sampler.should_sample(context)
        adaptive_decision = adaptive_sampler.should_sample(context)
        priority_decision = priority_sampler.should_sample(context)
        composite_decision = composite_sampler.should_sample(context)
        
        logger.info(f"  {operation}:")
        logger.info(f"    Probabilistic: {prob_decision.value}")
        logger.info(f"    Rate Limiting: {rate_decision.value}")
        logger.info(f"    Adaptive: {adaptive_decision.value}")
        logger.info(f"    Priority: {priority_decision.value}")
        logger.info(f"    Composite: {composite_decision.value}")
    
    # Show sampling statistics
    logger.info("\nSampling Statistics:")
    for sampler in [probabilistic_sampler, rate_limiting_sampler, adaptive_sampler, priority_sampler]:
        stats = sampler.get_stats()
        logger.info(f"  {stats['sampler_name']}: {stats['sampling_rate']:.3f} rate, {stats['total_decisions']} decisions")


async def demonstrate_automatic_instrumentation():
    """Demonstrate automatic instrumentation capabilities."""
    logger.info("=== Automatic Instrumentation Demo ===")
    
    # Configure instrumentation
    config = InstrumentationConfig(
        enabled=True,
        sanitize_queries=True,
        max_query_length=500,
        capture_parameters=False,  # Security: don't capture sensitive parameters
        capture_result_metadata=True,
        performance_threshold_ms=500.0,
        error_sampling_rate=1.0,
        success_sampling_rate=0.2
    )
    
    # Apply automatic instrumentation
    auto_instrumentation = AutoInstrumentation(config)
    
    try:
        auto_instrumentation.instrument_all()
        
        # Get instrumentation status
        status = get_instrumentation_status()
        logger.info(f"Instrumentation Status: {status}")
        
        # Simulate database operations (would be automatically traced)
        await simulate_database_operations()
        
        # Simulate HTTP client operations (would be automatically traced)
        await simulate_http_client_operations()
        
        # Simulate message broker operations (would be automatically traced)
        await simulate_message_broker_operations()
        
    finally:
        auto_instrumentation.uninstrument_all()
    
    logger.info("Automatic instrumentation demo completed")


async def simulate_database_operations():
    """Simulate database operations for tracing demonstration."""
    tracer = get_tracer("database_demo")
    
    # Simulate different database operations
    operations = [
        ("SELECT * FROM users WHERE id = ?", 0.05),
        ("INSERT INTO orders (user_id, amount) VALUES (?, ?)", 0.08),
        ("UPDATE user_profile SET last_login = ? WHERE user_id = ?", 0.03),
        ("SELECT COUNT(*) FROM products WHERE category = ?", 0.12),
        ("DELETE FROM sessions WHERE expires_at < ?", 0.15)
    ]
    
    for query, base_duration in operations:
        # Add some randomness to duration
        duration = base_duration + random.uniform(-0.02, 0.05)
        
        with tracer.span("database_query", kind="client") as span:
            span.set_attributes({
                "db.system": "postgresql",
                "db.operation": query.split()[0],
                "db.statement": query,
                "db.name": "demo_database"
            })
            
            # Simulate query execution
            await asyncio.sleep(duration)
            
            # Simulate occasional errors
            if random.random() < 0.05:  # 5% error rate
                span.record_exception(Exception("Database connection timeout"))
                span.set_attribute("db.error", "connection_timeout")
            else:
                span.set_attribute("db.rows_affected", random.randint(1, 100))


async def simulate_http_client_operations():
    """Simulate HTTP client operations for tracing demonstration."""
    tracer = get_tracer("http_client_demo")
    
    # Simulate different HTTP operations
    endpoints = [
        ("GET", "https://api.example.com/users/123", 0.1),
        ("POST", "https://api.example.com/orders", 0.2),
        ("PUT", "https://api.example.com/users/123/profile", 0.15),
        ("GET", "https://api.external.com/data", 0.3),
        ("DELETE", "https://api.example.com/sessions/abc123", 0.08)
    ]
    
    for method, url, base_duration in endpoints:
        duration = base_duration + random.uniform(-0.05, 0.1)
        
        with tracer.span(f"HTTP {method}", kind="client") as span:
            span.set_attributes({
                "http.method": method,
                "http.url": url,
                "http.scheme": "https",
                "net.peer.name": url.split("//")[1].split("/")[0]
            })
            
            # Simulate request
            await asyncio.sleep(duration)
            
            # Simulate response
            status_code = random.choices([200, 201, 400, 404, 500], weights=[70, 10, 10, 5, 5])[0]
            span.set_attribute("http.status_code", status_code)
            
            if status_code >= 400:
                span.record_exception(Exception(f"HTTP {status_code} error"))


async def simulate_message_broker_operations():
    """Simulate message broker operations for tracing demonstration."""
    tracer = get_tracer("message_broker_demo")
    
    # Simulate different messaging operations
    operations = [
        ("publish", "user.events", "user_registered", 0.02),
        ("publish", "order.events", "order_created", 0.03),
        ("consume", "notification.queue", "send_email", 0.05),
        ("publish", "analytics.events", "page_view", 0.01),
        ("consume", "payment.queue", "process_payment", 0.1)
    ]
    
    for operation, destination, message_type, base_duration in operations:
        duration = base_duration + random.uniform(-0.01, 0.02)
        
        kind = "producer" if operation == "publish" else "consumer"
        
        with tracer.span(f"rabbitmq.{operation}", kind=kind) as span:
            span.set_attributes({
                "messaging.system": "rabbitmq",
                "messaging.operation": operation,
                "messaging.destination": destination,
                "messaging.message_type": message_type,
                "messaging.message_size": random.randint(100, 5000)
            })
            
            # Simulate operation
            await asyncio.sleep(duration)
            
            # Simulate occasional failures
            if random.random() < 0.03:  # 3% error rate
                span.record_exception(Exception("Message broker connection lost"))


async def demonstrate_performance_analysis():
    """Demonstrate performance analysis and bottleneck detection."""
    logger.info("=== Performance Analysis Demo ===")
    
    # Create performance analyzer
    analyzer = PerformanceAnalyzer(
        bottleneck_threshold_ms=200.0,
        error_rate_threshold=0.05,
        sample_size_threshold=5
    )
    
    # Generate sample trace data
    tracer = get_tracer("performance_demo")
    
    # Simulate various operations with different performance characteristics
    operations = [
        ("fast_operation", 0.05, 0.01),      # Fast, low variance
        ("slow_operation", 0.5, 0.1),        # Slow, medium variance
        ("unstable_operation", 0.2, 0.15),   # Medium, high variance
        ("error_prone_operation", 0.1, 0.05) # Fast but with errors
    ]
    
    logger.info("Generating sample trace data...")
    
    for _ in range(50):  # Generate 50 traces
        for operation, base_duration, variance in operations:
            # Add randomness
            duration = max(0.01, base_duration + random.uniform(-variance, variance))
            
            with tracer.span(operation, kind="internal") as span:
                span.set_attributes({
                    "service.name": "performance_demo_service",
                    "operation.type": "business_logic"
                })
                
                # Simulate work
                await asyncio.sleep(duration)
                
                # Simulate errors for error-prone operation
                if operation == "error_prone_operation" and random.random() < 0.1:
                    span.record_exception(Exception("Simulated error"))
                    span.set_attribute("status", "error")
                else:
                    span.set_attribute("status", "success")
                
                # Record span for analysis
                analyzer.record_span(span)
    
    logger.info("Analyzing performance data...")
    
    # Analyze bottlenecks
    bottlenecks = analyzer.analyze_bottlenecks()
    
    logger.info(f"Detected {len(bottlenecks)} bottlenecks:")
    for bottleneck in bottlenecks:
        logger.info(f"  {bottleneck.bottleneck_type.value} in {bottleneck.service}.{bottleneck.operation}")
        logger.info(f"    Severity: {bottleneck.severity.value}")
        logger.info(f"    Description: {bottleneck.description}")
        logger.info(f"    Recommendations: {bottleneck.recommendations[:2]}")  # Show first 2
    
    # Analyze latency for each operation
    logger.info("\nLatency Analysis:")
    for operation, _, _ in operations:
        latency_analysis = analyzer.analyze_latency("performance_demo_service", operation)
        if latency_analysis:
            logger.info(f"  {operation}:")
            logger.info(f"    Mean: {latency_analysis.mean_latency_ms:.1f}ms")
            logger.info(f"    P95: {latency_analysis.p95_latency_ms:.1f}ms")
            logger.info(f"    P99: {latency_analysis.p99_latency_ms:.1f}ms")
            logger.info(f"    Trend: {latency_analysis.trend}")
    
    # Get performance recommendations
    logger.info("\nPerformance Recommendations:")
    for operation, _, _ in operations:
        recommendations = analyzer.get_performance_recommendations("performance_demo_service", operation)
        if recommendations:
            logger.info(f"  {operation}:")
            for rec in recommendations[:2]:  # Show first 2 recommendations
                logger.info(f"    - {rec}")
    
    # Get analysis summary
    summary = analyzer.get_analysis_summary()
    logger.info(f"\nAnalysis Summary:")
    logger.info(f"  Total spans analyzed: {summary.get('total_spans_analyzed', 0)}")
    logger.info(f"  Bottlenecks detected: {summary.get('bottlenecks_detected', 0)}")
    logger.info(f"  Services analyzed: {summary.get('services_analyzed', 0)}")


async def demonstrate_trace_annotation():
    """Demonstrate advanced trace annotation with custom tags and baggage."""
    logger.info("=== Trace Annotation Demo ===")
    
    tracer = get_tracer("annotation_demo")
    
    # Simulate a complex business operation with rich annotations
    with tracer.span("process_order", kind="internal") as root_span:
        # Set business context
        root_span.set_attributes({
            "business.operation": "order_processing",
            "business.domain": "e-commerce",
            "order.id": "ORD-12345",
            "customer.id": "CUST-67890",
            "order.amount": 299.99,
            "order.currency": "USD",
            "order.items_count": 3
        })
        
        # Add business events
        root_span.add_event("order_validation_started", {
            "validation.rules": ["inventory_check", "payment_validation", "fraud_detection"]
        })
        
        # Simulate inventory check
        with tracer.span("check_inventory", parent=root_span, kind="internal") as inventory_span:
            inventory_span.set_attributes({
                "inventory.warehouse": "WH-001",
                "inventory.items_to_check": 3,
                "inventory.check_type": "real_time"
            })
            
            await asyncio.sleep(0.05)
            
            # Simulate inventory results
            inventory_span.set_attributes({
                "inventory.available": True,
                "inventory.reserved_items": 3,
                "inventory.reservation_id": "RES-789"
            })
            
            inventory_span.add_event("inventory_reserved", {
                "reservation.expires_at": "2024-01-01T12:00:00Z",
                "reservation.warehouse": "WH-001"
            })
        
        # Simulate payment processing
        with tracer.span("process_payment", parent=root_span, kind="client") as payment_span:
            payment_span.set_attributes({
                "payment.provider": "stripe",
                "payment.method": "credit_card",
                "payment.amount": 299.99,
                "payment.currency": "USD",
                "payment.card_type": "visa",
                "payment.card_last4": "1234"
            })
            
            await asyncio.sleep(0.1)
            
            # Simulate payment result
            payment_span.set_attributes({
                "payment.status": "success",
                "payment.transaction_id": "TXN-456789",
                "payment.authorization_code": "AUTH-123",
                "payment.processing_fee": 8.97
            })
            
            payment_span.add_event("payment_authorized", {
                "authorization.amount": 299.99,
                "authorization.expires_at": "2024-01-01T12:00:00Z"
            })
        
        # Simulate fraud detection
        with tracer.span("fraud_detection", parent=root_span, kind="internal") as fraud_span:
            fraud_span.set_attributes({
                "fraud.provider": "internal_ml_model",
                "fraud.model_version": "v2.1.0",
                "fraud.features_count": 25
            })
            
            await asyncio.sleep(0.03)
            
            # Simulate fraud analysis
            fraud_score = random.uniform(0.1, 0.3)  # Low fraud score
            fraud_span.set_attributes({
                "fraud.score": fraud_score,
                "fraud.threshold": 0.8,
                "fraud.risk_level": "low",
                "fraud.decision": "approve"
            })
            
            fraud_span.add_event("fraud_analysis_completed", {
                "analysis.duration_ms": 30,
                "analysis.features_used": 25,
                "analysis.confidence": 0.95
            })
        
        # Final order processing
        root_span.add_event("order_approved", {
            "approval.timestamp": "2024-01-01T10:30:00Z",
            "approval.automated": True
        })
        
        # Set final order status
        root_span.set_attributes({
            "order.status": "confirmed",
            "order.confirmation_number": "CONF-ABC123",
            "order.estimated_delivery": "2024-01-03",
            "order.processing_time_ms": 180
        })
        
        root_span.add_event("order_processing_completed", {
            "completion.timestamp": "2024-01-01T10:30:01Z",
            "completion.total_time_ms": 180,
            "completion.success": True
        })
    
    logger.info("Complex order processing trace created with rich annotations")


async def demonstrate_jaeger_integration():
    """Demonstrate Jaeger-specific integration features."""
    logger.info("=== Jaeger Integration Demo ===")
    
    # Configure tracing with Jaeger
    config = TraceProviderConfig(
        service_name="jaeger_advanced_demo",
        service_version="1.0.0",
        environment="demo",
        exporters=[ExporterType.JAEGER, ExporterType.CONSOLE],
        sampling_rate=1.0,  # Sample all traces for demo
        jaeger_endpoint="http://localhost:14268/api/traces",
        jaeger_agent_host="localhost",
        jaeger_agent_port=6831
    )
    
    provider = configure_tracing(config)
    logger.info("Jaeger tracing configured")
    
    # Create traces with Jaeger-specific features
    tracer = get_tracer("jaeger_demo", "1.0.0")
    
    # Simulate a distributed transaction
    with tracer.span("distributed_transaction", kind="server") as root_span:
        root_span.set_attributes({
            "service.name": "order_service",
            "service.version": "1.0.0",
            "deployment.environment": "demo",
            "transaction.id": "TXN-DIST-001",
            "transaction.type": "order_fulfillment"
        })
        
        # Simulate calls to different services
        services = [
            ("user_service", "get_user_profile", 0.05),
            ("inventory_service", "check_availability", 0.08),
            ("payment_service", "process_payment", 0.12),
            ("notification_service", "send_confirmation", 0.03),
            ("analytics_service", "track_event", 0.02)
        ]
        
        for service_name, operation, duration in services:
            with tracer.span(f"{service_name}.{operation}", parent=root_span, kind="client") as service_span:
                service_span.set_attributes({
                    "service.name": service_name,
                    "service.operation": operation,
                    "rpc.system": "http",
                    "rpc.service": service_name,
                    "rpc.method": operation
                })
                
                await asyncio.sleep(duration)
                
                # Add service-specific attributes
                if service_name == "payment_service":
                    service_span.set_attributes({
                        "payment.amount": 299.99,
                        "payment.currency": "USD",
                        "payment.provider": "stripe"
                    })
                elif service_name == "inventory_service":
                    service_span.set_attributes({
                        "inventory.items_checked": 3,
                        "inventory.warehouse": "WH-001"
                    })
                
                service_span.add_event(f"{operation}_completed")
        
        root_span.add_event("distributed_transaction_completed", {
            "services_called": len(services),
            "total_duration_ms": sum(duration * 1000 for _, _, duration in services)
        })
    
    logger.info("Jaeger traces created - view them at http://localhost:16686")


async def main():
    """Main demonstration function."""
    logger.info("Starting Jaeger Advanced Tracing Features Example")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_intelligent_sampling()
        await demonstrate_automatic_instrumentation()
        await demonstrate_performance_analysis()
        await demonstrate_trace_annotation()
        await demonstrate_jaeger_integration()
        
        logger.info("=" * 60)
        logger.info("Jaeger Advanced Tracing Features Example completed successfully!")
        
        logger.info("\nTo view traces in Jaeger UI:")
        logger.info("1. Ensure Jaeger is running: docker run -d --name jaeger -p 16686:16686 -p 14268:14268 jaegertracing/all-in-one:latest")
        logger.info("2. Open http://localhost:16686 in your browser")
        logger.info("3. Search for service 'jaeger_advanced_demo' to see the traces")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
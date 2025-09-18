"""
Prometheus Metrics Foundation Example

This example demonstrates the comprehensive metrics collection system
including Prometheus integration, system metrics, HTTP metrics, and
custom business metrics.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any

# Core metrics components
from fastapi_microservices_sdk.observability.metrics import (
    MetricRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricsCollector,
    SystemMetricsCollector,
    HTTPMetricsCollector,
    PrometheusExporter,
    MetricsExporter,
    register_counter,
    register_gauge,
    register_histogram,
    register_summary
)

# FastAPI integration (optional)
try:
    from fastapi import FastAPI, Request
    from fastapi_microservices_sdk.observability.metrics.middleware import (
        PrometheusMiddleware,
        add_prometheus_middleware
    )
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_basic_metrics():
    """Demonstrate basic metric types and operations."""
    logger.info("=== Basic Metrics Demo ===")
    
    # Create metrics registry
    registry = MetricRegistry()
    
    # Create different metric types
    request_counter = Counter(
        'http_requests_total',
        'Total HTTP requests',
        labels=['method', 'endpoint', 'status']
    )
    
    cpu_gauge = Gauge(
        'cpu_usage_percent',
        'CPU usage percentage',
        unit='percent'
    )
    
    response_time_histogram = Histogram(
        'http_response_time_seconds',
        'HTTP response time distribution',
        labels=['endpoint'],
        unit='seconds',
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, float('inf')]
    )
    
    request_size_summary = Summary(
        'http_request_size_bytes',
        'HTTP request size summary',
        labels=['method'],
        unit='bytes',
        quantiles=[0.5, 0.9, 0.95, 0.99]
    )
    
    # Register metrics
    registry.register(request_counter)
    registry.register(cpu_gauge)
    registry.register(response_time_histogram)
    registry.register(request_size_summary)
    
    logger.info(f"Registered {len(registry.list_metrics())} metrics")
    
    # Simulate metric updates
    for i in range(100):
        # Counter operations
        method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
        endpoint = random.choice(['/api/users', '/api/items', '/api/orders'])
        status = random.choice(['200', '201', '400', '404', '500'])
        
        request_counter.inc(1.0, {
            'method': method,
            'endpoint': endpoint,
            'status': status
        })
        
        # Gauge operations
        cpu_usage = random.uniform(10.0, 90.0)
        cpu_gauge.set(cpu_usage)
        
        # Histogram observations
        response_time = random.uniform(0.05, 3.0)
        response_time_histogram.observe(response_time, {'endpoint': endpoint})
        
        # Summary observations
        request_size = random.uniform(100, 10000)
        request_size_summary.observe(request_size, {'method': method})
        
        if i % 20 == 0:
            logger.info(f"Processed {i+1} metric updates")
    
    # Display metric values
    logger.info("=== Metric Values ===")
    logger.info(f"Request counter total: {sum(request_counter.get_all_values().values())}")
    logger.info(f"Current CPU usage: {cpu_gauge.get_value():.2f}%")
    
    # Histogram statistics
    histogram_stats = response_time_histogram.get_value({'endpoint': '/api/users'})
    logger.info(f"Response time stats: count={histogram_stats['count']}, avg={histogram_stats['average']:.3f}s")
    
    # Summary statistics
    summary_stats = request_size_summary.get_value({'method': 'GET'})
    logger.info(f"Request size stats: count={summary_stats['count']}, avg={summary_stats['average']:.0f} bytes")
    logger.info(f"Request size quantiles: {summary_stats['quantiles']}")
    
    return registry


async def demonstrate_registry_features():
    """Demonstrate advanced registry features."""
    logger.info("=== Registry Features Demo ===")
    
    registry = MetricRegistry(enable_collision_detection=True)
    
    # Register metrics using convenience functions
    user_counter = register_counter(
        'active_users_total',
        'Total active users',
        labels=['region'],
        registry=registry
    )
    
    memory_gauge = register_gauge(
        'memory_usage_bytes',
        'Memory usage in bytes',
        unit='bytes',
        registry=registry
    )
    
    latency_histogram = register_histogram(
        'api_latency_seconds',
        'API latency distribution',
        labels=['service'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, float('inf')],
        registry=registry
    )
    
    # Test collision detection
    try:
        # This should fail due to collision
        duplicate_counter = Counter('active_users_total', 'Duplicate counter')
        registry.register(duplicate_counter)
    except Exception as e:
        logger.info(f"Collision detected (expected): {e}")
    
    # Update metrics
    for region in ['us-east', 'us-west', 'eu-central']:
        user_counter.inc(random.randint(10, 100), {'region': region})
    
    memory_gauge.set(random.randint(1000000, 5000000))
    
    for service in ['auth', 'api', 'db']:
        for _ in range(50):
            latency = random.uniform(0.001, 2.0)
            latency_histogram.observe(latency, {'service': service})
    
    # Get registry statistics
    stats = registry.get_statistics()
    logger.info(f"Registry statistics: {stats}")
    
    # List metrics by type
    counters = registry.list_by_type(Counter('', '').get_type())
    gauges = registry.list_by_type(Gauge('', '').get_type())
    histograms = registry.list_by_type(Histogram('', '').get_type())
    
    logger.info(f"Counters: {counters}")
    logger.info(f"Gauges: {gauges}")
    logger.info(f"Histograms: {histograms}")
    
    return registry


async def demonstrate_system_metrics():
    """Demonstrate system metrics collection."""
    logger.info("=== System Metrics Demo ===")
    
    # Create system metrics collector
    config = {
        'collection_interval': 2.0,
        'collect_cpu': True,
        'collect_memory': True,
        'collect_disk': True,
        'collect_network': True,
        'collect_processes': True,
        'collect_load': True,
        'disk_paths': ['/'],
        'enabled': True
    }
    
    system_collector = SystemMetricsCollector(config=config)
    
    try:
        # Initialize collector
        await system_collector.initialize()
        logger.info("System metrics collector initialized")
        
        # Let it collect for a few seconds
        await asyncio.sleep(5.0)
        
        # Get health check
        health = await system_collector.health_check()
        logger.info(f"System collector health: {health}")
        
        # Get some metric values
        registry = system_collector.registry
        
        cpu_metric = registry.get('system_cpu_usage_percent')
        if cpu_metric:
            logger.info(f"Current CPU usage: {cpu_metric.get_value():.2f}%")
        
        memory_metric = registry.get('system_memory_usage_percent')
        if memory_metric:
            logger.info(f"Current memory usage: {memory_metric.get_value():.2f}%")
        
        process_metric = registry.get('system_processes_count')
        if process_metric:
            logger.info(f"Running processes: {process_metric.get_value()}")
        
    finally:
        await system_collector.shutdown()
        logger.info("System metrics collector shutdown")


async def demonstrate_http_metrics():
    """Demonstrate HTTP metrics collection."""
    logger.info("=== HTTP Metrics Demo ===")
    
    # Create HTTP metrics collector
    config = {
        'track_request_size': True,
        'track_response_size': True,
        'track_in_progress': True,
        'enabled': True
    }
    
    http_collector = HTTPMetricsCollector(config=config)
    
    try:
        # Initialize collector
        await http_collector.initialize()
        logger.info("HTTP metrics collector initialized")
        
        # Simulate HTTP requests
        endpoints = ['/api/users', '/api/items', '/api/orders', '/health']
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        status_codes = [200, 201, 400, 404, 500]
        
        for i in range(200):
            method = random.choice(methods)
            endpoint = random.choice(endpoints)
            status_code = random.choice(status_codes)
            duration = random.uniform(0.01, 2.0)
            request_size = random.randint(100, 5000) if method in ['POST', 'PUT'] else None
            response_size = random.randint(200, 10000)
            
            # Record request
            http_collector.record_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration_seconds=duration,
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )
            
            if i % 50 == 0:
                logger.info(f"Recorded {i+1} HTTP requests")
        
        # Get health check
        health = await http_collector.health_check()
        logger.info(f"HTTP collector health: {health}")
        
        # Get some metric values
        registry = http_collector.registry
        
        request_count_metric = registry.get('http_requests_total')
        if request_count_metric:
            total_requests = sum(request_count_metric.get_all_values().values())
            logger.info(f"Total HTTP requests recorded: {total_requests}")
        
        duration_metric = registry.get('http_request_duration_seconds')
        if duration_metric:
            duration_stats = duration_metric.get_value({'method': 'GET', 'endpoint': '/api/users'})
            logger.info(f"GET /api/users duration stats: {duration_stats}")
        
    finally:
        await http_collector.shutdown()
        logger.info("HTTP metrics collector shutdown")


async def demonstrate_prometheus_export():
    """Demonstrate Prometheus metrics export."""
    logger.info("=== Prometheus Export Demo ===")
    
    # Create registry with sample metrics
    registry = MetricRegistry()
    
    # Add various metrics
    request_counter = register_counter(
        'demo_requests_total',
        'Demo request counter',
        labels=['method', 'status'],
        registry=registry
    )
    
    temperature_gauge = register_gauge(
        'demo_temperature_celsius',
        'Demo temperature gauge',
        labels=['location'],
        unit='celsius',
        registry=registry
    )
    
    response_histogram = register_histogram(
        'demo_response_time_seconds',
        'Demo response time histogram',
        labels=['endpoint'],
        registry=registry
    )
    
    size_summary = register_summary(
        'demo_payload_size_bytes',
        'Demo payload size summary',
        registry=registry
    )
    
    # Generate sample data
    for _ in range(100):
        request_counter.inc(1, {'method': 'GET', 'status': '200'})
        request_counter.inc(1, {'method': 'POST', 'status': '201'})
        
        temperature_gauge.set(random.uniform(18.0, 25.0), {'location': 'server_room'})
        temperature_gauge.set(random.uniform(20.0, 30.0), {'location': 'office'})
        
        response_histogram.observe(random.uniform(0.01, 1.0), {'endpoint': '/api'})
        
        size_summary.observe(random.uniform(100, 10000))
    
    # Create exporter and export metrics
    exporter = PrometheusExporter(registry)
    
    # Export without timestamps
    metrics_output = exporter.export_metrics(include_timestamp=False)
    logger.info("=== Prometheus Export (without timestamps) ===")
    logger.info(metrics_output[:500] + "..." if len(metrics_output) > 500 else metrics_output)
    
    # Export with timestamps
    metrics_with_timestamps = exporter.export_metrics(include_timestamp=True)
    logger.info("=== Prometheus Export (with timestamps) ===")
    logger.info(metrics_with_timestamps[:500] + "..." if len(metrics_with_timestamps) > 500 else metrics_with_timestamps)
    
    # Export to file
    try:
        generic_exporter = MetricsExporter(registry)
        generic_exporter.export_to_file('/tmp/metrics.txt', 'prometheus')
        logger.info("Metrics exported to /tmp/metrics.txt")
    except Exception as e:
        logger.warning(f"Failed to export to file: {e}")
    
    # Get export statistics
    export_stats = exporter.get_export_statistics()
    logger.info(f"Export statistics: {export_stats}")


async def demonstrate_fastapi_integration():
    """Demonstrate FastAPI integration (if available)."""
    if not FASTAPI_AVAILABLE:
        logger.info("=== FastAPI Integration Demo ===")
        logger.info("FastAPI not available - skipping integration demo")
        return
    
    logger.info("=== FastAPI Integration Demo ===")
    
    # Create FastAPI app
    app = FastAPI(title="Metrics Demo API")
    
    # Add Prometheus middleware
    registry = MetricRegistry()
    
    # Note: In a real application, you would use:
    # add_prometheus_middleware(app, registry=registry, metrics_endpoint="/metrics")
    
    # For this demo, we'll just show the middleware creation
    try:
        middleware = PrometheusMiddleware(
            app=app,
            registry=registry,
            metrics_endpoint="/metrics",
            exclude_paths=["/health", "/docs"],
            group_paths=True,
            track_request_size=True,
            track_response_size=True
        )
        logger.info("Prometheus middleware created successfully")
        
        # Simulate some requests (normally handled by FastAPI)
        http_collector = HTTPMetricsCollector(config={'registry': registry, 'enabled': True})
        await http_collector.initialize()
        
        # Simulate API requests
        for _ in range(50):
            method = random.choice(['GET', 'POST', 'PUT'])
            endpoint = random.choice(['/api/users/{id}', '/api/items', '/api/orders/{id}'])
            status = random.choice([200, 201, 400, 404])
            duration = random.uniform(0.01, 0.5)
            
            http_collector.record_request(method, endpoint, status, duration)
        
        # Export metrics
        exporter = PrometheusExporter(registry)
        metrics = exporter.export_metrics()
        
        logger.info("FastAPI metrics collected successfully")
        logger.info(f"Metrics sample:\n{metrics[:300]}...")
        
        await http_collector.shutdown()
        
    except Exception as e:
        logger.error(f"FastAPI integration error: {e}")


async def demonstrate_custom_business_metrics():
    """Demonstrate custom business metrics."""
    logger.info("=== Custom Business Metrics Demo ===")
    
    registry = MetricRegistry()
    
    # Business-specific metrics
    orders_counter = register_counter(
        'business_orders_total',
        'Total orders processed',
        labels=['product_category', 'payment_method', 'region'],
        registry=registry
    )
    
    revenue_gauge = register_gauge(
        'business_revenue_usd',
        'Current revenue in USD',
        labels=['currency'],
        unit='usd',
        registry=registry
    )
    
    order_value_histogram = register_histogram(
        'business_order_value_usd',
        'Order value distribution',
        labels=['product_category'],
        buckets=[10, 50, 100, 500, 1000, 5000, float('inf')],
        registry=registry
    )
    
    processing_time_summary = register_summary(
        'business_order_processing_seconds',
        'Order processing time',
        labels=['complexity'],
        quantiles=[0.5, 0.9, 0.95, 0.99],
        registry=registry
    )
    
    # Simulate business operations
    categories = ['electronics', 'clothing', 'books', 'home']
    payment_methods = ['credit_card', 'paypal', 'bank_transfer']
    regions = ['north_america', 'europe', 'asia']
    complexities = ['simple', 'medium', 'complex']
    
    total_revenue = 0.0
    
    for _ in range(500):
        category = random.choice(categories)
        payment = random.choice(payment_methods)
        region = random.choice(regions)
        complexity = random.choice(complexities)
        
        # Process order
        orders_counter.inc(1, {
            'product_category': category,
            'payment_method': payment,
            'region': region
        })
        
        # Order value
        order_value = random.uniform(10, 2000)
        order_value_histogram.observe(order_value, {'product_category': category})
        
        # Update revenue
        total_revenue += order_value
        revenue_gauge.set(total_revenue, {'currency': 'USD'})
        
        # Processing time
        processing_time = random.uniform(0.1, 10.0)
        processing_time_summary.observe(processing_time, {'complexity': complexity})
    
    # Display business metrics
    logger.info(f"Total orders processed: {sum(orders_counter.get_all_values().values())}")
    logger.info(f"Total revenue: ${revenue_gauge.get_value():.2f}")
    
    # Category breakdown
    electronics_orders = orders_counter.get_value({
        'product_category': 'electronics',
        'payment_method': 'credit_card',
        'region': 'north_america'
    })
    logger.info(f"Electronics orders (credit card, North America): {electronics_orders}")
    
    # Order value statistics
    electronics_value_stats = order_value_histogram.get_value({'product_category': 'electronics'})
    logger.info(f"Electronics order value stats: {electronics_value_stats}")
    
    # Processing time statistics
    complex_processing_stats = processing_time_summary.get_value({'complexity': 'complex'})
    logger.info(f"Complex order processing stats: {complex_processing_stats}")
    
    # Export business metrics
    exporter = PrometheusExporter(registry)
    business_metrics = exporter.export_metrics()
    
    logger.info("Business metrics exported successfully")
    return registry


async def main():
    """Main demonstration function."""
    logger.info("Starting Prometheus Metrics Foundation Example")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_basic_metrics()
        await demonstrate_registry_features()
        await demonstrate_system_metrics()
        await demonstrate_http_metrics()
        await demonstrate_prometheus_export()
        await demonstrate_fastapi_integration()
        await demonstrate_custom_business_metrics()
        
        logger.info("=" * 60)
        logger.info("Prometheus Metrics Foundation Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
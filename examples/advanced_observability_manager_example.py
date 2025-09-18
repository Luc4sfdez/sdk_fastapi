"""
Advanced Observability Manager Example

This example demonstrates the advanced features of the observability system
including hot configuration reload, performance monitoring, health aggregation,
and integration management.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, Any

from fastapi_microservices_sdk.observability import (
    ObservabilityConfig,
    create_development_config,
    create_production_config
)
from fastapi_microservices_sdk.observability.advanced_manager import (
    AdvancedObservabilityManager,
    AdvancedComponentRegistry,
    ConfigurationManager,
    IntegrationManager,
    PerformanceMetrics,
    ComponentHealthHistory,
    create_advanced_observability_manager,
    initialize_advanced_observability
)
from fastapi_microservices_sdk.observability.manager import (
    ObservabilityComponent,
    ComponentType,
    ComponentStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdvancedMetricsComponent(ObservabilityComponent):
    """Advanced metrics component with performance tracking."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.metrics_collected = 0
        self.collection_errors = 0
        self.last_collection_time = 0.0
        self.performance_data = []
    
    async def _initialize(self) -> None:
        """Initialize with performance tracking."""
        start_time = time.time()
        self.logger.info("Initializing advanced metrics component...")
        
        # Simulate initialization work
        await asyncio.sleep(0.2)
        
        initialization_time = (time.time() - start_time) * 1000  # ms
        self.logger.info(f"Advanced metrics component initialized in {initialization_time:.2f}ms")
    
    async def _shutdown(self) -> None:
        """Shutdown with cleanup."""
        self.logger.info("Shutting down advanced metrics component...")
        await asyncio.sleep(0.1)
        self.logger.info("Advanced metrics component shutdown completed")
    
    async def _health_check(self) -> Dict[str, Any]:
        """Advanced health check with performance metrics."""
        start_time = time.time()
        
        # Simulate health check work
        await asyncio.sleep(0.05)
        
        check_time = (time.time() - start_time) * 1000  # ms
        
        return {
            'metrics_collected': self.metrics_collected,
            'collection_errors': self.collection_errors,
            'error_rate': self.collection_errors / max(1, self.metrics_collected + self.collection_errors),
            'avg_collection_time_ms': sum(self.performance_data) / len(self.performance_data) if self.performance_data else 0,
            'health_check_time_ms': check_time,
            'last_collection_ago_seconds': time.time() - self.last_collection_time if self.last_collection_time else 0
        }
    
    async def collect_metric(self, name: str, value: float, simulate_error: bool = False) -> None:
        """Collect metric with performance tracking."""
        start_time = time.time()
        
        try:
            if simulate_error:
                raise Exception("Simulated collection error")
            
            # Simulate metric collection
            await asyncio.sleep(0.01)
            
            collection_time = (time.time() - start_time) * 1000  # ms
            self.performance_data.append(collection_time)
            
            # Keep only last 100 measurements
            if len(self.performance_data) > 100:
                self.performance_data = self.performance_data[-100:]
            
            self.metrics_collected += 1
            self.last_collection_time = time.time()
            self.logger.debug(f"Collected metric {name}: {value} in {collection_time:.2f}ms")
            
        except Exception as e:
            self.collection_errors += 1
            self.logger.error(f"Failed to collect metric {name}: {e}")
            raise


class AdvancedTracingComponent(ObservabilityComponent):
    """Advanced tracing component with dependency tracking."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.traces_created = 0
        self.spans_created = 0
        self.trace_errors = 0
        self.dependency_health = {}
    
    async def _initialize(self) -> None:
        """Initialize with dependency checks."""
        self.logger.info("Initializing advanced tracing component...")
        
        # Check dependencies
        await self._check_dependencies()
        
        await asyncio.sleep(0.15)
        self.logger.info("Advanced tracing component initialized")
    
    async def _shutdown(self) -> None:
        """Shutdown with cleanup."""
        self.logger.info("Shutting down advanced tracing component...")
        await asyncio.sleep(0.1)
        self.logger.info("Advanced tracing component shutdown completed")
    
    async def _health_check(self) -> Dict[str, Any]:
        """Health check with dependency status."""
        await self._check_dependencies()
        
        return {
            'traces_created': self.traces_created,
            'spans_created': self.spans_created,
            'trace_errors': self.trace_errors,
            'error_rate': self.trace_errors / max(1, self.traces_created),
            'avg_spans_per_trace': self.spans_created / max(1, self.traces_created),
            'dependency_health': self.dependency_health
        }
    
    async def _check_dependencies(self) -> None:
        """Check health of dependencies."""
        # Simulate dependency checks
        dependencies = ['jaeger-collector', 'trace-storage', 'sampling-service']
        
        for dep in dependencies:
            # Simulate dependency health check
            await asyncio.sleep(0.01)
            # Randomly simulate some dependency issues
            import random
            self.dependency_health[dep] = 'healthy' if random.random() > 0.1 else 'degraded'
    
    async def create_trace(self, operation_name: str, simulate_error: bool = False) -> str:
        """Create trace with error simulation."""
        try:
            if simulate_error:
                raise Exception("Simulated trace creation error")
            
            trace_id = f"trace_{self.traces_created + 1}"
            self.traces_created += 1
            self.logger.debug(f"Created trace {trace_id} for operation {operation_name}")
            return trace_id
            
        except Exception as e:
            self.trace_errors += 1
            self.logger.error(f"Failed to create trace for {operation_name}: {e}")
            raise


async def demonstrate_advanced_registry():
    """Demonstrate advanced component registry features."""
    logger.info("=== Advanced Component Registry Demo ===")
    
    registry = AdvancedComponentRegistry()
    
    # Create advanced components
    metrics_component = AdvancedMetricsComponent("advanced_metrics", {"enabled": True})
    tracing_component = AdvancedTracingComponent("advanced_tracing", {"enabled": True})
    
    # Register components with groups
    registry.register_component(
        name="advanced_metrics",
        component_type=ComponentType.METRICS,
        instance=metrics_component,
        config={"collection_interval": 10.0},
        dependencies=[],
        group="core_observability"
    )
    
    registry.register_component(
        name="advanced_tracing",
        component_type=ComponentType.TRACING,
        instance=tracing_component,
        config={"sampling_rate": 0.1},
        dependencies=["advanced_metrics"],
        group="core_observability"
    )
    
    # Initialize components
    await metrics_component.initialize()
    await tracing_component.initialize()
    
    # Simulate some operations
    await metrics_component.collect_metric("cpu_usage", 75.5)
    await metrics_component.collect_metric("memory_usage", 60.2)
    await metrics_component.collect_metric("error_metric", 0.0, simulate_error=True)
    
    await tracing_component.create_trace("user_request")
    await tracing_component.create_trace("database_query")
    await tracing_component.create_trace("error_trace", simulate_error=True)
    
    # Perform health checks and record results
    metrics_health = await metrics_component.health_check()
    tracing_health = await tracing_component.health_check()
    
    registry.record_health_check("advanced_metrics", metrics_health)
    registry.record_health_check("advanced_tracing", tracing_health)
    
    # Update performance metrics
    registry.update_component_performance("advanced_metrics", cpu_usage=25.0, memory_usage=128.0)
    registry.update_component_performance("advanced_tracing", cpu_usage=15.0, memory_usage=64.0)
    
    # Get performance and health summaries
    performance_summary = registry.get_performance_summary()
    health_summary = registry.get_health_summary()
    
    logger.info(f"Performance Summary: {performance_summary}")
    logger.info(f"Health Summary: {health_summary}")
    
    # Get components by group
    core_components = registry.get_components_by_group("core_observability")
    logger.info(f"Core observability components: {[c.name for c in core_components]}")
    
    # Cleanup
    await metrics_component.shutdown()
    await tracing_component.shutdown()
    
    return registry


async def demonstrate_configuration_manager():
    """Demonstrate configuration hot-reload capabilities."""
    logger.info("=== Configuration Manager Demo ===")
    
    # Create initial configuration
    initial_config = create_development_config()
    initial_config.service_name = "config_demo_service"
    
    config_manager = ConfigurationManager(initial_config)
    
    # Add change listener
    def on_config_change(old_config, new_config):
        logger.info(f"Configuration changed from {old_config.environment} to {new_config.environment}")
        logger.info(f"Service name changed from {old_config.service_name} to {new_config.service_name}")
    
    config_manager.add_change_listener(on_config_change)
    
    # Update configuration
    new_config = create_production_config()
    new_config.service_name = "config_demo_service_prod"
    new_config.service_version = "2.0.0"
    
    logger.info("Updating configuration...")
    config_manager.update_config(new_config)
    
    # Get configuration history
    history = config_manager.get_config_history()
    logger.info(f"Configuration history: {len(history)} versions")
    for entry in history:
        logger.info(f"  Version {entry['version']}: {entry['service_name']} ({entry['environment']})")
    
    # Rollback configuration
    logger.info("Rolling back configuration...")
    config_manager.rollback_config()
    
    current_config = config_manager.get_current_config()
    logger.info(f"Current config after rollback: {current_config.service_name} ({current_config.environment})")
    
    return config_manager


async def demonstrate_integration_manager():
    """Demonstrate integration management."""
    logger.info("=== Integration Manager Demo ===")
    
    integration_manager = IntegrationManager()
    
    # Initialize integrations
    config = create_development_config()
    await integration_manager.initialize_integrations(config)
    
    # Get integration status
    status = integration_manager.get_integration_status()
    logger.info(f"Integration status: {status}")
    
    # Check specific integrations
    for integration_name, available in status.items():
        logger.info(f"  {integration_name}: {'Available' if available else 'Not Available'}")
    
    return integration_manager


async def demonstrate_advanced_manager():
    """Demonstrate advanced observability manager."""
    logger.info("=== Advanced Observability Manager Demo ===")
    
    # Create configuration
    config = create_development_config()
    config.service_name = "advanced_demo_service"
    config.service_version = "1.0.0"
    
    # Create advanced manager
    manager = create_advanced_observability_manager(config)
    
    # Add event handlers
    def on_config_changed(event_type, **kwargs):
        logger.info(f"Event: {event_type} - Configuration updated")
    
    def on_registry_event(event_type, *args, **kwargs):
        logger.info(f"Registry event: {event_type}")
    
    manager.add_event_handler('config_changed', on_config_changed)
    manager.add_event_handler('registry_component_registered', on_registry_event)
    
    try:
        # Initialize manager
        await manager.initialize()
        logger.info("Advanced manager initialized successfully")
        
        # Get advanced health check
        health_status = await manager.get_advanced_health_check()
        logger.info(f"Advanced health status: {health_status['status']}")
        logger.info(f"Performance summary: {health_status.get('performance_summary', {})}")
        logger.info(f"Integration status: {health_status.get('integration_status', {})}")
        
        # Demonstrate configuration hot-reload
        logger.info("Testing configuration hot-reload...")
        new_config = create_production_config()
        new_config.service_name = "advanced_demo_service_prod"
        
        await manager.reload_configuration(new_config)
        logger.info("Configuration reloaded successfully")
        
        # Get configuration manager
        config_manager = manager.get_configuration_manager()
        history = config_manager.get_config_history()
        logger.info(f"Configuration versions after reload: {len(history)}")
        
        # Get integration manager
        integration_manager = manager.get_integration_manager()
        integrations = integration_manager.get_integration_status()
        logger.info(f"Available integrations: {list(integrations.keys())}")
        
        # Simulate some work and monitoring
        await asyncio.sleep(2.0)
        
        # Get final health check
        final_health = await manager.get_advanced_health_check()
        logger.info(f"Final health check - Uptime: {final_health.get('uptime_seconds', 0):.2f}s")
        
    finally:
        # Shutdown manager
        await manager.shutdown()
        logger.info("Advanced manager shutdown successfully")


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring capabilities."""
    logger.info("=== Performance Monitoring Demo ===")
    
    config = create_development_config()
    manager = AdvancedObservabilityManager(config)
    
    # Create and register a component for monitoring
    test_component = AdvancedMetricsComponent("perf_test", {"enabled": True})
    
    manager.registry.register_component(
        name="perf_test",
        component_type=ComponentType.METRICS,
        instance=test_component,
        config={}
    )
    
    try:
        await manager.initialize()
        await test_component.initialize()
        
        # Simulate operations with performance tracking
        for i in range(10):
            await test_component.collect_metric(f"test_metric_{i}", float(i * 10))
            
            # Update performance metrics
            manager.registry.update_component_performance(
                "perf_test",
                cpu_usage=20.0 + i * 2,
                memory_usage=100.0 + i * 5,
                response_time=50.0 + i * 10,
                error_occurred=(i % 4 == 0)  # Simulate some errors
            )
            
            # Record health check
            health_result = await test_component.health_check()
            manager.registry.record_health_check("perf_test", health_result)
            
            await asyncio.sleep(0.1)
        
        # Get component insights
        insights = manager.get_component_insights("perf_test")
        logger.info("Component Insights:")
        logger.info(f"  Performance: {insights.get('performance_metrics', {})}")
        logger.info(f"  Health History: {insights.get('health_history', {})}")
        logger.info(f"  Recent Health Checks: {len(insights.get('recent_health_checks', []))}")
        
        # Get performance metrics
        performance = manager.registry.get_component_performance("perf_test")
        if performance:
            logger.info(f"  CPU Usage: {performance.cpu_usage_percent:.1f}%")
            logger.info(f"  Memory Usage: {performance.memory_usage_mb:.1f}MB")
            logger.info(f"  Average Response Time: {performance.average_response_time_ms:.1f}ms")
            logger.info(f"  Error Count: {performance.error_count}")
            logger.info(f"  Success Count: {performance.success_count}")
        
        # Get health history
        health_history = manager.registry.get_component_health_history("perf_test")
        if health_history:
            logger.info(f"  Uptime Percentage: {health_history.uptime_percentage:.1f}%")
            logger.info(f"  Failure Count: {health_history.failure_count}")
            logger.info(f"  Recovery Count: {health_history.recovery_count}")
        
    finally:
        await test_component.shutdown()
        await manager.shutdown()


async def demonstrate_event_system():
    """Demonstrate the event system."""
    logger.info("=== Event System Demo ===")
    
    config = create_development_config()
    manager = AdvancedObservabilityManager(config)
    
    # Event counters
    event_counts = {}
    
    def count_events(event_type, **kwargs):
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        logger.info(f"Event received: {event_type} (count: {event_counts[event_type]})")
    
    # Add event handlers
    manager.add_event_handler('config_changed', count_events)
    manager.add_event_handler('registry_component_registered', count_events)
    manager.add_event_handler('custom_event', count_events)
    
    try:
        await manager.initialize()
        
        # Emit custom events
        manager.emit_event('custom_event', message="Test event 1")
        manager.emit_event('custom_event', message="Test event 2")
        
        # Trigger configuration change event
        new_config = create_production_config()
        await manager.reload_configuration(new_config)
        
        logger.info(f"Total events received: {sum(event_counts.values())}")
        logger.info(f"Event breakdown: {event_counts}")
        
    finally:
        await manager.shutdown()


async def main():
    """Main demonstration function."""
    logger.info("Starting Advanced Observability Manager Example")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        await demonstrate_advanced_registry()
        await demonstrate_configuration_manager()
        await demonstrate_integration_manager()
        await demonstrate_advanced_manager()
        await demonstrate_performance_monitoring()
        await demonstrate_event_system()
        
        logger.info("=" * 60)
        logger.info("Advanced Observability Manager Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
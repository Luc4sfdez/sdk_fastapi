"""
Observability Foundation Example

This example demonstrates the basic usage of the observability system
foundation including configuration, manager initialization, and component
registry functionality.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any

from fastapi_microservices_sdk.observability import (
    ObservabilityConfig,
    ObservabilityManager,
    ComponentRegistry,
    ComponentStatus,
    ComponentType,
    create_development_config,
    create_production_config,
    create_testing_config,
    validate_observability_config
)
from fastapi_microservices_sdk.observability.manager import (
    ObservabilityComponent,
    ComponentInfo
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExampleMetricsComponent(ObservabilityComponent):
    """Example metrics component for demonstration."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.metrics_collected = 0
        self.collection_errors = 0
    
    async def _initialize(self) -> None:
        """Initialize the metrics component."""
        self.logger.info("Initializing example metrics component...")
        # Simulate initialization work
        await asyncio.sleep(0.1)
        self.logger.info("Example metrics component initialized")
    
    async def _shutdown(self) -> None:
        """Shutdown the metrics component."""
        self.logger.info("Shutting down example metrics component...")
        await asyncio.sleep(0.1)
        self.logger.info("Example metrics component shutdown")
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'metrics_collected': self.metrics_collected,
            'collection_errors': self.collection_errors,
            'collection_rate': self.metrics_collected / max(1, self.metrics_collected + self.collection_errors)
        }
    
    async def collect_metric(self, name: str, value: float) -> None:
        """Simulate metric collection."""
        try:
            # Simulate metric collection
            await asyncio.sleep(0.01)
            self.metrics_collected += 1
            self.logger.debug(f"Collected metric {name}: {value}")
        except Exception as e:
            self.collection_errors += 1
            self.logger.error(f"Failed to collect metric {name}: {e}")


class ExampleTracingComponent(ObservabilityComponent):
    """Example tracing component for demonstration."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.traces_created = 0
        self.spans_created = 0
    
    async def _initialize(self) -> None:
        """Initialize the tracing component."""
        self.logger.info("Initializing example tracing component...")
        await asyncio.sleep(0.1)
        self.logger.info("Example tracing component initialized")
    
    async def _shutdown(self) -> None:
        """Shutdown the tracing component."""
        self.logger.info("Shutting down example tracing component...")
        await asyncio.sleep(0.1)
        self.logger.info("Example tracing component shutdown")
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        return {
            'traces_created': self.traces_created,
            'spans_created': self.spans_created,
            'avg_spans_per_trace': self.spans_created / max(1, self.traces_created)
        }
    
    async def create_trace(self, operation_name: str) -> str:
        """Simulate trace creation."""
        trace_id = f"trace_{self.traces_created + 1}"
        self.traces_created += 1
        self.logger.debug(f"Created trace {trace_id} for operation {operation_name}")
        return trace_id
    
    async def create_span(self, trace_id: str, span_name: str) -> str:
        """Simulate span creation."""
        span_id = f"span_{self.spans_created + 1}"
        self.spans_created += 1
        self.logger.debug(f"Created span {span_id} in trace {trace_id}")
        return span_id


async def demonstrate_configuration():
    """Demonstrate configuration management."""
    logger.info("=== Configuration Management Demo ===")
    
    # Create different environment configurations
    dev_config = create_development_config()
    prod_config = create_production_config()
    test_config = create_testing_config()
    
    logger.info(f"Development config - Tracing sampling rate: {dev_config.tracing.sampling_rate}")
    logger.info(f"Production config - Tracing sampling rate: {prod_config.tracing.sampling_rate}")
    logger.info(f"Testing config - Metrics enabled: {test_config.metrics.enabled}")
    
    # Create configuration from environment
    env_config = ObservabilityConfig.from_env()
    logger.info(f"Environment config - Service name: {env_config.service_name}")
    
    # Validate configuration
    issues = validate_observability_config(prod_config)
    if issues:
        logger.warning(f"Configuration issues found: {issues}")
    else:
        logger.info("Configuration validation passed")
    
    # Demonstrate configuration serialization
    config_dict = prod_config.to_dict()
    logger.info(f"Configuration serialized to {len(config_dict)} keys")
    
    return dev_config


async def demonstrate_component_registry():
    """Demonstrate component registry functionality."""
    logger.info("=== Component Registry Demo ===")
    
    registry = ComponentRegistry()
    
    # Create example components
    metrics_component = ExampleMetricsComponent("example_metrics", {"enabled": True})
    tracing_component = ExampleTracingComponent("example_tracing", {"enabled": True})
    
    # Register components
    registry.register_component(
        name="example_metrics",
        component_type=ComponentType.METRICS,
        instance=metrics_component,
        config={"collection_interval": 15.0},
        dependencies=[]
    )
    
    registry.register_component(
        name="example_tracing",
        component_type=ComponentType.TRACING,
        instance=tracing_component,
        config={"sampling_rate": 0.1},
        dependencies=["example_metrics"]  # Tracing depends on metrics
    )
    
    # Demonstrate registry operations
    logger.info(f"Total components registered: {len(registry.get_all_components())}")
    
    metrics_components = registry.get_components_by_type(ComponentType.METRICS)
    logger.info(f"Metrics components: {len(metrics_components)}")
    
    tracing_components = registry.get_components_by_type(ComponentType.TRACING)
    logger.info(f"Tracing components: {len(tracing_components)}")
    
    # Get startup order based on dependencies
    startup_order = registry.get_startup_order()
    logger.info(f"Component startup order: {startup_order}")
    
    # Get registry statistics
    stats = registry.get_registry_stats()
    logger.info(f"Registry stats: {stats}")
    
    return registry


async def demonstrate_observability_manager():
    """Demonstrate observability manager functionality."""
    logger.info("=== Observability Manager Demo ===")
    
    # Create configuration
    config = create_development_config()
    config.service_name = "example_service"
    config.service_version = "1.0.0"
    
    # Create and initialize manager
    manager = ObservabilityManager(config)
    
    # Add startup and shutdown hooks
    async def startup_hook(mgr):
        logger.info("Startup hook executed")
    
    async def shutdown_hook(mgr):
        logger.info("Shutdown hook executed")
    
    manager.add_startup_hook(startup_hook)
    manager.add_shutdown_hook(shutdown_hook)
    
    try:
        # Initialize the manager
        await manager.initialize()
        logger.info("Observability manager initialized successfully")
        
        # Perform health check
        health_status = await manager.health_check()
        logger.info(f"Health check status: {health_status['status']}")
        logger.info(f"System uptime: {health_status.get('uptime_seconds', 0):.2f} seconds")
        
        # Get registry statistics
        registry_stats = manager.registry.get_registry_stats()
        logger.info(f"Registry statistics: {registry_stats}")
        
        # Demonstrate configuration access
        current_config = manager.get_config()
        logger.info(f"Current service name: {current_config.service_name}")
        
        # Check if manager is initialized
        logger.info(f"Manager initialized: {manager.is_initialized()}")
        
        # Simulate some work
        await asyncio.sleep(1.0)
        
    finally:
        # Shutdown the manager
        await manager.shutdown()
        logger.info("Observability manager shutdown successfully")


async def demonstrate_managed_lifecycle():
    """Demonstrate managed lifecycle context manager."""
    logger.info("=== Managed Lifecycle Demo ===")
    
    config = create_development_config()
    config.service_name = "managed_service"
    
    # Use context manager for automatic lifecycle management
    async with ObservabilityManager(config).managed_lifecycle() as manager:
        logger.info("Inside managed lifecycle context")
        
        # Perform health check
        health_status = await manager.health_check()
        logger.info(f"Health status: {health_status['status']}")
        
        # Simulate work
        await asyncio.sleep(0.5)
        
        logger.info("Exiting managed lifecycle context")
    
    logger.info("Managed lifecycle completed")


async def demonstrate_component_operations():
    """Demonstrate individual component operations."""
    logger.info("=== Component Operations Demo ===")
    
    # Create and test metrics component
    metrics_component = ExampleMetricsComponent("test_metrics", {"enabled": True})
    
    try:
        # Initialize component
        await metrics_component.initialize()
        logger.info(f"Metrics component status: {metrics_component.status}")
        
        # Perform some operations
        await metrics_component.collect_metric("cpu_usage", 75.5)
        await metrics_component.collect_metric("memory_usage", 60.2)
        await metrics_component.collect_metric("disk_usage", 45.8)
        
        # Perform health check
        health_result = await metrics_component.health_check()
        logger.info(f"Metrics component health: {health_result}")
        
        # Get component metrics
        component_metrics = metrics_component.get_metrics()
        logger.info(f"Component metrics: {component_metrics}")
        
    finally:
        # Shutdown component
        await metrics_component.shutdown()
        logger.info(f"Metrics component final status: {metrics_component.status}")


async def demonstrate_error_handling():
    """Demonstrate error handling in observability system."""
    logger.info("=== Error Handling Demo ===")
    
    # Create a component that will fail during initialization
    class FailingComponent(ObservabilityComponent):
        async def _initialize(self) -> None:
            raise Exception("Simulated initialization failure")
    
    failing_component = FailingComponent("failing_component", {})
    
    try:
        await failing_component.initialize()
    except Exception as e:
        logger.info(f"Expected initialization failure: {e}")
        logger.info(f"Component status after failure: {failing_component.status}")
    
    # Test configuration validation errors
    invalid_config = ObservabilityConfig(
        tracing={"sampling_rate": 1.5}  # Invalid sampling rate
    )
    
    try:
        issues = validate_observability_config(invalid_config)
        if issues:
            logger.info(f"Configuration validation caught issues: {issues}")
    except Exception as e:
        logger.info(f"Configuration validation error: {e}")


async def main():
    """Main demonstration function."""
    logger.info("Starting Observability Foundation Example")
    logger.info("=" * 50)
    
    try:
        # Run all demonstrations
        await demonstrate_configuration()
        await demonstrate_component_registry()
        await demonstrate_observability_manager()
        await demonstrate_managed_lifecycle()
        await demonstrate_component_operations()
        await demonstrate_error_handling()
        
        logger.info("=" * 50)
        logger.info("Observability Foundation Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
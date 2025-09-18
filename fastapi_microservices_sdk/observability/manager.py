"""
Observability Manager and Component Registry.

This module provides the central management system for all observability
components, handling initialization, lifecycle management, and coordination
between different observability systems.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Type, Union
from datetime import datetime, timezone
from enum import Enum
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from .config import ObservabilityConfig
from .exceptions import (
    ObservabilityError,
    ConfigurationError,
    ComponentStatus as ComponentStatusError
)

# Integration with existing systems
try:
    from ..communication.manager import CommunicationManager
    COMMUNICATION_INTEGRATION_AVAILABLE = True
except ImportError:
    COMMUNICATION_INTEGRATION_AVAILABLE = False
    CommunicationManager = None

try:
    from ..database.manager import DatabaseManager
    DATABASE_INTEGRATION_AVAILABLE = True
except ImportError:
    DATABASE_INTEGRATION_AVAILABLE = False
    DatabaseManager = None


class ComponentStatus(Enum):
    """Status of observability components."""
    NOT_INITIALIZED = "not_initialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


class ComponentType(Enum):
    """Types of observability components."""
    METRICS = "metrics"
    TRACING = "tracing"
    LOGGING = "logging"
    HEALTH = "health"
    ALERTING = "alerting"
    DASHBOARD = "dashboard"


@dataclass
class ComponentInfo:
    """Information about an observability component."""
    name: str
    component_type: ComponentType
    status: ComponentStatus = ComponentStatus.NOT_INITIALIZED
    instance: Optional[Any] = None
    config: Optional[Dict[str, Any]] = None
    last_health_check: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    startup_time: Optional[datetime] = None
    shutdown_time: Optional[datetime] = None


class ObservabilityComponent:
    """Base class for observability components."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ComponentStatus.NOT_INITIALIZED
        self.logger = logging.getLogger(f"observability.{name}")
        self._health_check_interval = 30.0
        self._last_health_check = None
        self._health_check_task = None
    
    async def initialize(self) -> None:
        """Initialize the component."""
        self.status = ComponentStatus.INITIALIZING
        try:
            await self._initialize()
            self.status = ComponentStatus.RUNNING
            self.logger.info(f"Component {self.name} initialized successfully")
        except Exception as e:
            self.status = ComponentStatus.ERROR
            self.logger.error(f"Failed to initialize component {self.name}: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the component."""
        self.status = ComponentStatus.STOPPING
        try:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            await self._shutdown()
            self.status = ComponentStatus.STOPPED
            self.logger.info(f"Component {self.name} shutdown successfully")
        except Exception as e:
            self.status = ComponentStatus.ERROR
            self.logger.error(f"Failed to shutdown component {self.name}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the component."""
        try:
            health_data = await self._health_check()
            self._last_health_check = datetime.now(timezone.utc)
            return {
                'status': 'healthy',
                'timestamp': self._last_health_check.isoformat(),
                'component': self.name,
                **health_data
            }
        except Exception as e:
            self.logger.error(f"Health check failed for component {self.name}: {e}")
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'component': self.name,
                'error': str(e)
            }
    
    async def _initialize(self) -> None:
        """Component-specific initialization logic."""
        pass
    
    async def _shutdown(self) -> None:
        """Component-specific shutdown logic."""
        pass
    
    async def _health_check(self) -> Dict[str, Any]:
        """Component-specific health check logic."""
        return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get component metrics."""
        return {
            'status': self.status.value,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'uptime_seconds': (datetime.now(timezone.utc) - self._last_health_check).total_seconds() if self._last_health_check else 0
        }


class ComponentRegistry:
    """Registry for managing observability components."""
    
    def __init__(self):
        self._components: Dict[str, ComponentInfo] = {}
        self._component_types: Dict[ComponentType, List[str]] = {
            component_type: [] for component_type in ComponentType
        }
        self._lock = threading.RLock()
        self._logger = logging.getLogger("observability.registry")
    
    def register_component(
        self,
        name: str,
        component_type: ComponentType,
        instance: ObservabilityComponent,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """Register a new observability component."""
        with self._lock:
            if name in self._components:
                raise ValueError(f"Component {name} is already registered")
            
            component_info = ComponentInfo(
                name=name,
                component_type=component_type,
                instance=instance,
                config=config or {},
                dependencies=dependencies or []
            )
            
            self._components[name] = component_info
            self._component_types[component_type].append(name)
            
            self._logger.info(f"Registered component: {name} ({component_type.value})")
    
    def unregister_component(self, name: str) -> None:
        """Unregister an observability component."""
        with self._lock:
            if name not in self._components:
                raise ValueError(f"Component {name} is not registered")
            
            component_info = self._components[name]
            self._component_types[component_info.component_type].remove(name)
            del self._components[name]
            
            self._logger.info(f"Unregistered component: {name}")
    
    def get_component(self, name: str) -> Optional[ComponentInfo]:
        """Get component information by name."""
        with self._lock:
            return self._components.get(name)
    
    def get_components_by_type(self, component_type: ComponentType) -> List[ComponentInfo]:
        """Get all components of a specific type."""
        with self._lock:
            component_names = self._component_types.get(component_type, [])
            return [self._components[name] for name in component_names]
    
    def get_all_components(self) -> List[ComponentInfo]:
        """Get all registered components."""
        with self._lock:
            return list(self._components.values())
    
    def update_component_status(self, name: str, status: ComponentStatus, error_message: Optional[str] = None) -> None:
        """Update component status."""
        with self._lock:
            if name in self._components:
                self._components[name].status = status
                self._components[name].error_message = error_message
                if status == ComponentStatus.RUNNING and not self._components[name].startup_time:
                    self._components[name].startup_time = datetime.now(timezone.utc)
                elif status == ComponentStatus.STOPPED:
                    self._components[name].shutdown_time = datetime.now(timezone.utc)
    
    def get_component_dependencies(self, name: str) -> List[str]:
        """Get component dependencies."""
        with self._lock:
            component = self._components.get(name)
            return component.dependencies if component else []
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get the complete dependency graph."""
        with self._lock:
            return {
                name: info.dependencies
                for name, info in self._components.items()
            }
    
    def get_startup_order(self) -> List[str]:
        """Get components in startup order based on dependencies."""
        dependency_graph = self.get_dependency_graph()
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(component: str):
            if component in temp_visited:
                raise ValueError(f"Circular dependency detected involving {component}")
            if component in visited:
                return
            
            temp_visited.add(component)
            for dependency in dependency_graph.get(component, []):
                if dependency in dependency_graph:  # Only visit registered dependencies
                    visit(dependency)
            temp_visited.remove(component)
            visited.add(component)
            result.append(component)
        
        for component in dependency_graph:
            if component not in visited:
                visit(component)
        
        return result
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            stats = {
                'total_components': len(self._components),
                'components_by_type': {
                    component_type.value: len(components)
                    for component_type, components in self._component_types.items()
                },
                'components_by_status': {},
                'healthy_components': 0,
                'unhealthy_components': 0
            }
            
            for component in self._components.values():
                status = component.status.value
                stats['components_by_status'][status] = stats['components_by_status'].get(status, 0) + 1
                
                if component.status == ComponentStatus.RUNNING:
                    stats['healthy_components'] += 1
                elif component.status in [ComponentStatus.ERROR, ComponentStatus.DEGRADED]:
                    stats['unhealthy_components'] += 1
            
            return stats


class ObservabilityManager:
    """Central manager for all observability components."""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.registry = ComponentRegistry()
        self._logger = logging.getLogger("observability.manager")
        self._initialized = False
        self._shutdown_event = asyncio.Event()
        self._health_check_task = None
        self._health_check_interval = 30.0
        self._startup_time = None
        self._shutdown_time = None
        
        # Integration managers
        self._communication_manager = None
        self._database_manager = None
        
        # Component factories
        self._component_factories: Dict[str, Callable] = {}
        
        # Lifecycle hooks
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
    
    async def initialize(self) -> None:
        """Initialize the observability system."""
        if self._initialized:
            self._logger.warning("Observability manager is already initialized")
            return
        
        self._logger.info("Initializing observability system...")
        self._startup_time = datetime.now(timezone.utc)
        
        try:
            # Initialize integrations
            await self._initialize_integrations()
            
            # Register and initialize components
            await self._register_components()
            await self._initialize_components()
            
            # Start health monitoring
            await self._start_health_monitoring()
            
            # Execute startup hooks
            await self._execute_startup_hooks()
            
            self._initialized = True
            self._logger.info("Observability system initialized successfully")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize observability system: {e}")
            await self._cleanup_on_error()
            raise ObservabilityError(
                message="Failed to initialize observability system",
                component="manager",
                operation="initialize",
                original_error=e
            )
    
    async def shutdown(self) -> None:
        """Shutdown the observability system."""
        if not self._initialized:
            self._logger.warning("Observability manager is not initialized")
            return
        
        self._logger.info("Shutting down observability system...")
        self._shutdown_time = datetime.now(timezone.utc)
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Execute shutdown hooks
            await self._execute_shutdown_hooks()
            
            # Stop health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown components in reverse order
            await self._shutdown_components()
            
            self._initialized = False
            self._logger.info("Observability system shutdown successfully")
            
        except Exception as e:
            self._logger.error(f"Error during observability system shutdown: {e}")
            raise ObservabilityError(
                message="Error during observability system shutdown",
                component="manager",
                operation="shutdown",
                original_error=e
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        if not self._initialized:
            return {
                'status': 'unhealthy',
                'reason': 'not_initialized',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        try:
            component_health = {}
            overall_healthy = True
            
            # Check all components
            for component_info in self.registry.get_all_components():
                if component_info.instance:
                    health_result = await component_info.instance.health_check()
                    component_health[component_info.name] = health_result
                    
                    if health_result.get('status') != 'healthy':
                        overall_healthy = False
                else:
                    component_health[component_info.name] = {
                        'status': 'unhealthy',
                        'reason': 'no_instance'
                    }
                    overall_healthy = False
            
            # Get system metrics
            system_metrics = await self._get_system_metrics()
            
            return {
                'status': 'healthy' if overall_healthy else 'degraded',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'uptime_seconds': (datetime.now(timezone.utc) - self._startup_time).total_seconds() if self._startup_time else 0,
                'components': component_health,
                'system_metrics': system_metrics,
                'registry_stats': self.registry.get_registry_stats()
            }
            
        except Exception as e:
            self._logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'reason': 'health_check_error',
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def register_component_factory(self, component_type: str, factory: Callable) -> None:
        """Register a component factory."""
        self._component_factories[component_type] = factory
        self._logger.info(f"Registered component factory: {component_type}")
    
    def add_startup_hook(self, hook: Callable) -> None:
        """Add a startup hook."""
        self._startup_hooks.append(hook)
    
    def add_shutdown_hook(self, hook: Callable) -> None:
        """Add a shutdown hook."""
        self._shutdown_hooks.append(hook)
    
    def get_component(self, name: str) -> Optional[ObservabilityComponent]:
        """Get a component instance by name."""
        component_info = self.registry.get_component(name)
        return component_info.instance if component_info else None
    
    def get_components_by_type(self, component_type: ComponentType) -> List[ObservabilityComponent]:
        """Get all component instances of a specific type."""
        component_infos = self.registry.get_components_by_type(component_type)
        return [info.instance for info in component_infos if info.instance]
    
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._initialized
    
    def get_config(self) -> ObservabilityConfig:
        """Get the current configuration."""
        return self.config
    
    def update_config(self, new_config: ObservabilityConfig) -> None:
        """Update configuration (requires restart)."""
        self.config = new_config
        self._logger.info("Configuration updated - restart required for changes to take effect")
    
    async def reload_config(self) -> None:
        """Reload configuration and restart components."""
        if not self._initialized:
            raise ObservabilityError("Cannot reload config - manager not initialized")
        
        self._logger.info("Reloading configuration...")
        
        # Shutdown current components
        await self._shutdown_components()
        
        # Re-register and initialize with new config
        await self._register_components()
        await self._initialize_components()
        
        self._logger.info("Configuration reloaded successfully")
    
    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager for automatic lifecycle management."""
        try:
            await self.initialize()
            yield self
        finally:
            await self.shutdown()
    
    # Private methods
    
    async def _initialize_integrations(self) -> None:
        """Initialize integration with other SDK components."""
        if COMMUNICATION_INTEGRATION_AVAILABLE:
            try:
                # Integration with communication manager will be implemented
                # when communication components are available
                pass
            except Exception as e:
                self._logger.warning(f"Failed to initialize communication integration: {e}")
        
        if DATABASE_INTEGRATION_AVAILABLE:
            try:
                # Integration with database manager will be implemented
                # when database components are available
                pass
            except Exception as e:
                self._logger.warning(f"Failed to initialize database integration: {e}")
    
    async def _register_components(self) -> None:
        """Register all enabled components."""
        # This will be expanded as we implement each component type
        self._logger.info("Registering observability components...")
        
        # Register metrics component if enabled
        if self.config.metrics.enabled:
            await self._register_metrics_component()
        
        # Register tracing component if enabled
        if self.config.tracing.enabled:
            await self._register_tracing_component()
        
        # Register logging component if enabled
        if self.config.logging.enabled:
            await self._register_logging_component()
        
        # Register health component if enabled
        if self.config.health.enabled:
            await self._register_health_component()
        
        # Register alerting component if enabled
        if self.config.alerting.enabled:
            await self._register_alerting_component()
        
        # Register dashboard component if enabled
        if self.config.dashboard.enabled:
            await self._register_dashboard_component()
    
    async def _register_metrics_component(self) -> None:
        """Register metrics component (placeholder)."""
        # This will be implemented in Task 2.1
        self._logger.info("Metrics component registration - will be implemented in Task 2.1")
    
    async def _register_tracing_component(self) -> None:
        """Register tracing component (placeholder)."""
        # This will be implemented in Task 3.1
        self._logger.info("Tracing component registration - will be implemented in Task 3.1")
    
    async def _register_logging_component(self) -> None:
        """Register logging component (placeholder)."""
        # This will be implemented in Task 4.1
        self._logger.info("Logging component registration - will be implemented in Task 4.1")
    
    async def _register_health_component(self) -> None:
        """Register health component (placeholder)."""
        # This will be implemented in Task 5.1
        self._logger.info("Health component registration - will be implemented in Task 5.1")
    
    async def _register_alerting_component(self) -> None:
        """Register alerting component (placeholder)."""
        # This will be implemented in Task 6.1
        self._logger.info("Alerting component registration - will be implemented in Task 6.1")
    
    async def _register_dashboard_component(self) -> None:
        """Register dashboard component (placeholder)."""
        # This will be implemented in Task 8.1
        self._logger.info("Dashboard component registration - will be implemented in Task 8.1")
    
    async def _initialize_components(self) -> None:
        """Initialize all registered components in dependency order."""
        startup_order = self.registry.get_startup_order()
        
        for component_name in startup_order:
            component_info = self.registry.get_component(component_name)
            if component_info and component_info.instance:
                try:
                    self._logger.info(f"Initializing component: {component_name}")
                    await component_info.instance.initialize()
                    self.registry.update_component_status(component_name, ComponentStatus.RUNNING)
                except Exception as e:
                    self._logger.error(f"Failed to initialize component {component_name}: {e}")
                    self.registry.update_component_status(component_name, ComponentStatus.ERROR, str(e))
                    raise
    
    async def _shutdown_components(self) -> None:
        """Shutdown all components in reverse dependency order."""
        startup_order = self.registry.get_startup_order()
        shutdown_order = list(reversed(startup_order))
        
        for component_name in shutdown_order:
            component_info = self.registry.get_component(component_name)
            if component_info and component_info.instance:
                try:
                    self._logger.info(f"Shutting down component: {component_name}")
                    await component_info.instance.shutdown()
                    self.registry.update_component_status(component_name, ComponentStatus.STOPPED)
                except Exception as e:
                    self._logger.error(f"Failed to shutdown component {component_name}: {e}")
                    self.registry.update_component_status(component_name, ComponentStatus.ERROR, str(e))
    
    async def _start_health_monitoring(self) -> None:
        """Start periodic health monitoring."""
        async def health_monitor():
            while not self._shutdown_event.is_set():
                try:
                    await asyncio.sleep(self._health_check_interval)
                    if self._shutdown_event.is_set():
                        break
                    
                    # Perform health checks on all components
                    for component_info in self.registry.get_all_components():
                        if component_info.instance and component_info.status == ComponentStatus.RUNNING:
                            try:
                                health_result = await component_info.instance.health_check()
                                component_info.last_health_check = datetime.now(timezone.utc)
                                
                                if health_result.get('status') != 'healthy':
                                    self.registry.update_component_status(
                                        component_info.name,
                                        ComponentStatus.DEGRADED,
                                        health_result.get('error', 'Health check failed')
                                    )
                                elif component_info.status == ComponentStatus.DEGRADED:
                                    # Component recovered
                                    self.registry.update_component_status(component_info.name, ComponentStatus.RUNNING)
                                    
                            except Exception as e:
                                self._logger.error(f"Health check failed for {component_info.name}: {e}")
                                self.registry.update_component_status(
                                    component_info.name,
                                    ComponentStatus.ERROR,
                                    str(e)
                                )
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Error in health monitoring: {e}")
        
        self._health_check_task = asyncio.create_task(health_monitor())
    
    async def _execute_startup_hooks(self) -> None:
        """Execute all startup hooks."""
        for hook in self._startup_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                self._logger.error(f"Startup hook failed: {e}")
    
    async def _execute_shutdown_hooks(self) -> None:
        """Execute all shutdown hooks."""
        for hook in self._shutdown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self)
                else:
                    hook(self)
            except Exception as e:
                self._logger.error(f"Shutdown hook failed: {e}")
    
    async def _cleanup_on_error(self) -> None:
        """Cleanup resources on initialization error."""
        try:
            await self._shutdown_components()
        except Exception as e:
            self._logger.error(f"Error during cleanup: {e}")
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics."""
        import psutil
        
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids()),
                'boot_time': psutil.boot_time()
            }
        except Exception as e:
            self._logger.warning(f"Failed to get system metrics: {e}")
            return {}


# Utility functions for creating and managing observability managers

def create_observability_manager(config: Optional[ObservabilityConfig] = None) -> ObservabilityManager:
    """Create an observability manager with the given configuration."""
    if config is None:
        config = ObservabilityConfig()
    
    return ObservabilityManager(config)


async def initialize_observability(config: Optional[ObservabilityConfig] = None) -> ObservabilityManager:
    """Initialize and return a ready-to-use observability manager."""
    manager = create_observability_manager(config)
    await manager.initialize()
    return manager


# Export main classes and functions
__all__ = [
    'ComponentStatus',
    'ComponentType',
    'ComponentInfo',
    'ObservabilityComponent',
    'ComponentRegistry',
    'ObservabilityManager',
    'create_observability_manager',
    'initialize_observability',
]
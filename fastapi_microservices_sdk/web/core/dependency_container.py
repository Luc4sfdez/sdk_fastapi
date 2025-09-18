"""
Dependency injection container for web dashboard managers.
"""

import logging
from typing import Any, Dict, Type, TypeVar, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from .base_manager import BaseManager


T = TypeVar('T')


class LifecycleScope(Enum):
    """Dependency lifecycle scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


@dataclass
class DependencyRegistration:
    """Registration information for a dependency."""
    dependency_type: Type
    implementation: Type
    factory: Optional[Callable] = None
    scope: LifecycleScope = LifecycleScope.SINGLETON
    config: Optional[Dict[str, Any]] = None


class DependencyContainer:
    """
    Dependency injection container for managing web dashboard components.
    
    Provides:
    - Service registration and resolution
    - Lifecycle management (singleton, transient, scoped)
    - Configuration injection
    - Circular dependency detection
    - Manager initialization and health checking
    """
    
    def __init__(self):
        """Initialize the dependency container."""
        self.logger = logging.getLogger("web.container")
        self._registrations: Dict[Type, DependencyRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._current_scope: Optional[str] = None
        self._resolution_stack: list = []
        
    def register_singleton(
        self, 
        interface: Type[T], 
        implementation: Type[T], 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a singleton dependency.
        
        Args:
            interface: Interface type
            implementation: Implementation type
            config: Optional configuration
        """
        self._registrations[interface] = DependencyRegistration(
            dependency_type=interface,
            implementation=implementation,
            scope=LifecycleScope.SINGLETON,
            config=config
        )
        self.logger.debug(f"Registered singleton: {interface.__name__} -> {implementation.__name__}")
    
    def register_transient(
        self, 
        interface: Type[T], 
        implementation: Type[T], 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a transient dependency.
        
        Args:
            interface: Interface type
            implementation: Implementation type
            config: Optional configuration
        """
        self._registrations[interface] = DependencyRegistration(
            dependency_type=interface,
            implementation=implementation,
            scope=LifecycleScope.TRANSIENT,
            config=config
        )
        self.logger.debug(f"Registered transient: {interface.__name__} -> {implementation.__name__}")
    
    def register_scoped(
        self, 
        interface: Type[T], 
        implementation: Type[T], 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a scoped dependency.
        
        Args:
            interface: Interface type
            implementation: Implementation type
            config: Optional configuration
        """
        self._registrations[interface] = DependencyRegistration(
            dependency_type=interface,
            implementation=implementation,
            scope=LifecycleScope.SCOPED,
            config=config
        )
        self.logger.debug(f"Registered scoped: {interface.__name__} -> {implementation.__name__}")
    
    def register_factory(
        self, 
        interface: Type[T], 
        factory: Callable[[], T], 
        scope: LifecycleScope = LifecycleScope.SINGLETON
    ) -> None:
        """
        Register a factory function for creating dependencies.
        
        Args:
            interface: Interface type
            factory: Factory function
            scope: Lifecycle scope
        """
        self._registrations[interface] = DependencyRegistration(
            dependency_type=interface,
            implementation=None,
            factory=factory,
            scope=scope
        )
        self.logger.debug(f"Registered factory for: {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a dependency.
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Instance of the requested type
            
        Raises:
            ValueError: If dependency not registered or circular dependency detected
        """
        # Check for circular dependencies
        if interface in self._resolution_stack:
            cycle = " -> ".join([t.__name__ for t in self._resolution_stack] + [interface.__name__])
            raise ValueError(f"Circular dependency detected: {cycle}")
        
        if interface not in self._registrations:
            raise ValueError(f"Dependency not registered: {interface.__name__}")
        
        registration = self._registrations[interface]
        
        # Handle different scopes
        if registration.scope == LifecycleScope.SINGLETON:
            return self._resolve_singleton(interface, registration)
        elif registration.scope == LifecycleScope.SCOPED:
            return self._resolve_scoped(interface, registration)
        else:  # TRANSIENT
            return self._resolve_transient(interface, registration)
    
    def _resolve_singleton(self, interface: Type[T], registration: DependencyRegistration) -> T:
        """Resolve singleton dependency."""
        if interface in self._singletons:
            return self._singletons[interface]
        
        instance = self._create_instance(interface, registration)
        self._singletons[interface] = instance
        return instance
    
    def _resolve_scoped(self, interface: Type[T], registration: DependencyRegistration) -> T:
        """Resolve scoped dependency."""
        if self._current_scope is None:
            raise ValueError("No active scope for scoped dependency resolution")
        
        if self._current_scope not in self._scoped_instances:
            self._scoped_instances[self._current_scope] = {}
        
        scope_instances = self._scoped_instances[self._current_scope]
        if interface in scope_instances:
            return scope_instances[interface]
        
        instance = self._create_instance(interface, registration)
        scope_instances[interface] = instance
        return instance
    
    def _resolve_transient(self, interface: Type[T], registration: DependencyRegistration) -> T:
        """Resolve transient dependency."""
        return self._create_instance(interface, registration)
    
    def _create_instance(self, interface: Type[T], registration: DependencyRegistration) -> T:
        """Create instance using factory or constructor."""
        self._resolution_stack.append(interface)
        
        try:
            if registration.factory:
                instance = registration.factory()
            else:
                # Create instance with configuration if it's a BaseManager
                if issubclass(registration.implementation, BaseManager):
                    instance = registration.implementation(
                        name=interface.__name__.lower().replace('manager', ''),
                        config=registration.config
                    )
                else:
                    instance = registration.implementation()
            
            self.logger.debug(f"Created instance: {interface.__name__}")
            return instance
        finally:
            self._resolution_stack.pop()
    
    def begin_scope(self, scope_id: str) -> None:
        """
        Begin a new dependency scope.
        
        Args:
            scope_id: Unique identifier for the scope
        """
        self._current_scope = scope_id
        if scope_id not in self._scoped_instances:
            self._scoped_instances[scope_id] = {}
        self.logger.debug(f"Began scope: {scope_id}")
    
    def end_scope(self, scope_id: str) -> None:
        """
        End a dependency scope and cleanup scoped instances.
        
        Args:
            scope_id: Scope identifier to end
        """
        if scope_id in self._scoped_instances:
            # Cleanup scoped instances if they implement cleanup
            for instance in self._scoped_instances[scope_id].values():
                if hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        self.logger.error(f"Error cleaning up scoped instance: {e}")
            
            del self._scoped_instances[scope_id]
        
        if self._current_scope == scope_id:
            self._current_scope = None
        
        self.logger.debug(f"Ended scope: {scope_id}")
    
    async def initialize_managers(self) -> bool:
        """
        Initialize all registered BaseManager instances.
        
        Returns:
            True if all managers initialized successfully
        """
        success = True
        managers = []
        
        # Collect all manager instances
        for interface, registration in self._registrations.items():
            if (registration.implementation and 
                issubclass(registration.implementation, BaseManager)):
                try:
                    manager = self.resolve(interface)
                    managers.append(manager)
                except Exception as e:
                    self.logger.error(f"Failed to resolve manager {interface.__name__}: {e}")
                    success = False
        
        # Initialize managers
        for manager in managers:
            if not await manager.initialize():
                success = False
        
        return success
    
    async def shutdown_managers(self) -> bool:
        """
        Shutdown all BaseManager instances.
        
        Returns:
            True if all managers shutdown successfully
        """
        success = True
        
        # Shutdown singleton managers
        for instance in self._singletons.values():
            if isinstance(instance, BaseManager):
                if not await instance.shutdown():
                    success = False
        
        return success
    
    async def health_check_managers(self) -> Dict[str, bool]:
        """
        Perform health checks on all BaseManager instances.
        
        Returns:
            Dictionary mapping manager names to health status
        """
        health_status = {}
        
        # Check singleton managers
        for interface, instance in self._singletons.items():
            if isinstance(instance, BaseManager):
                manager_name = interface.__name__
                health_status[manager_name] = await instance.health_check()
        
        return health_status
    
    def get_registration_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered dependencies.
        
        Returns:
            Dictionary with registration information
        """
        info = {}
        for interface, registration in self._registrations.items():
            info[interface.__name__] = {
                "implementation": registration.implementation.__name__ if registration.implementation else "Factory",
                "scope": registration.scope.value,
                "has_config": registration.config is not None,
                "is_singleton_created": interface in self._singletons
            }
        return info
    
    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._registrations.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        self._current_scope = None
        self.logger.info("Dependency container cleared")

# Global container instance
_container_instance: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global container instance."""
    global _container_instance
    if _container_instance is None:
        _container_instance = DependencyContainer()
    return _container_instance


# Dependency injection functions for FastAPI

def get_service_manager():
    """Get ServiceManager instance for dependency injection."""
    from ..services.service_manager import ServiceManager
    container = get_container()
    return container.resolve(ServiceManager)


def get_monitoring_manager():
    """Get MonitoringManager instance for dependency injection."""
    from ..monitoring.monitoring_manager import MonitoringManager
    container = get_container()
    return container.resolve(MonitoringManager)


def get_deployment_manager():
    """Get DeploymentManager instance for dependency injection."""
    from ..deployment.deployment_manager import DeploymentManager
    container = get_container()
    return container.resolve(DeploymentManager)


def get_configuration_manager():
    """Get ConfigurationManager instance for dependency injection."""
    from ..configuration.configuration_manager import ConfigurationManager
    container = get_container()
    return container.resolve(ConfigurationManager)


def get_log_manager():
    """Get LogManager instance for dependency injection."""
    from ..logs.log_manager import LogManager
    container = get_container()
    return container.resolve(LogManager)


def get_websocket_manager():
    """Get WebSocketManager instance for dependency injection."""
    from ..websockets.websocket_manager import WebSocketManager
    container = get_container()
    return container.resolve(WebSocketManager)


def get_auth_manager():
    """Get AuthenticationManager instance for dependency injection."""
    from ..auth.auth_manager import AuthenticationManager
    container = get_container()
    return container.resolve(AuthenticationManager)


def get_template_manager():
    """Get TemplateManager instance for dependency injection."""
    from ..templates_mgmt.template_manager import TemplateManager
    container = get_container()
    return container.resolve(TemplateManager)


def get_template_analytics():
    """Get TemplateAnalytics instance for dependency injection."""
    from ..templates_mgmt.template_analytics import TemplateAnalytics
    container = get_container()
    return container.resolve(TemplateAnalytics)


def get_system_diagnostics_manager():
    """Get SystemDiagnosticsManager instance for dependency injection."""
    from ..diagnostics.system_diagnostics_manager import SystemDiagnosticsManager
    container = get_container()
    return container.resolve(SystemDiagnosticsManager)


def get_health_monitor():
    """Get HealthMonitor instance for dependency injection."""
    from ..diagnostics.health_monitor import HealthMonitor
    container = get_container()
    return container.resolve(HealthMonitor)


def get_resource_monitor():
    """Get ResourceMonitor instance for dependency injection."""
    from ..diagnostics.resource_monitor import ResourceMonitor
    container = get_container()
    return container.resolve(ResourceMonitor)


def get_performance_analyzer():
    """Get PerformanceAnalyzer instance for dependency injection."""
    from ..diagnostics.performance_analyzer import PerformanceAnalyzer
    container = get_container()
    return container.resolve(PerformanceAnalyzer)
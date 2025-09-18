"""
Enhanced service registry with multi-backend support and caching.

This module provides an enhanced service registry that can work with multiple
service discovery backends and includes caching and health check capabilities.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Callable

from .base import (
    ServiceRegistry,
    ServiceDiscoveryBackend,
    ServiceInstance,
    ServiceStatus,
    ServiceFilter,
    ServiceSelector,
    LoadBalancingStrategy,
    DiscoveryEvent,
    DiscoveryEventType
)
from .cache import ServiceDiscoveryCache
try:
    from .health import HealthCheckScheduler
    HEALTH_CHECKING_AVAILABLE = True
except ImportError:
    HEALTH_CHECKING_AVAILABLE = False
    HealthCheckScheduler = None


logger = logging.getLogger(__name__)


class EnhancedServiceRegistry(ServiceRegistry):
    """Enhanced service registry with multi-backend support."""
    
    def __init__(
        self,
        backends: List[ServiceDiscoveryBackend],
        cache_ttl: int = 60,
        enable_health_checks: bool = True,
        health_check_interval: int = 30,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    ):
        self.backends = {backend.name: backend for backend in backends}
        self.primary_backend = backends[0] if backends else None
        
        # Caching
        self.cache = ServiceDiscoveryCache(ttl=cache_ttl)
        
        # Health checking
        self.enable_health_checks = enable_health_checks and HEALTH_CHECKING_AVAILABLE
        self.health_scheduler = None
        
        if self.enable_health_checks and HealthCheckScheduler:
            self.health_scheduler = HealthCheckScheduler(
                registry=self,
                interval=health_check_interval
            )
        
        # Load balancing
        self.service_selector = ServiceSelector(strategy=load_balancing_strategy)
        
        # Event handling
        self.event_handlers: List[Callable[[DiscoveryEvent], None]] = []
        
        # Internal state
        self._local_services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._is_started = False
        self._lock = asyncio.Lock()
        
        # Setup event handlers for backends
        for backend in backends:
            backend.add_event_handler(self._handle_backend_event)
    
    async def start(self) -> None:
        """Start the registry and all backends."""
        if self._is_started:
            return
        
        async with self._lock:
            if self._is_started:
                return
            
            logger.info("Starting enhanced service registry")
            
            # Connect all backends
            for backend in self.backends.values():
                try:
                    await backend.connect()
                    logger.info(f"Connected to backend: {backend.name}")
                except Exception as e:
                    logger.error(f"Failed to connect to backend {backend.name}: {e}")
            
            # Start health check scheduler
            if self.health_scheduler:
                await self.health_scheduler.start()
            
            self._is_started = True
            logger.info("Enhanced service registry started")
    
    async def stop(self) -> None:
        """Stop the registry and all backends."""
        if not self._is_started:
            return
        
        async with self._lock:
            if not self._is_started:
                return
            
            logger.info("Stopping enhanced service registry")
            
            # Stop health check scheduler
            if self.health_scheduler:
                await self.health_scheduler.stop()
            
            # Disconnect all backends
            for backend in self.backends.values():
                try:
                    await backend.disconnect()
                    logger.info(f"Disconnected from backend: {backend.name}")
                except Exception as e:
                    logger.error(f"Failed to disconnect from backend {backend.name}: {e}")
            
            self._is_started = False
            logger.info("Enhanced service registry stopped")
    
    async def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance across all backends."""
        if not self._is_started:
            await self.start()
        
        logger.info(f"Registering service instance: {instance.service_name}/{instance.instance_id}")
        
        success_count = 0
        total_backends = len(self.backends)
        
        # Register with all backends
        for backend_name, backend in self.backends.items():
            try:
                if await backend.register_service(instance):
                    success_count += 1
                    logger.debug(f"Registered with backend {backend_name}")
                else:
                    logger.warning(f"Failed to register with backend {backend_name}")
            except Exception as e:
                logger.error(f"Error registering with backend {backend_name}: {e}")
        
        # Store locally
        if instance.service_name not in self._local_services:
            self._local_services[instance.service_name] = {}
        self._local_services[instance.service_name][instance.instance_id] = instance
        
        # Invalidate cache
        self.cache.invalidate_service(instance.service_name)
        
        # Emit event
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.SERVICE_REGISTERED,
            service_name=instance.service_name,
            instance=instance,
            metadata={"backends_registered": success_count, "total_backends": total_backends}
        ))
        
        # Consider successful if registered with at least one backend
        return success_count > 0
    
    async def deregister(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance from all backends."""
        logger.info(f"Deregistering service instance: {service_name}/{instance_id}")
        
        success_count = 0
        total_backends = len(self.backends)
        
        # Get instance before deregistering
        instance = await self.get_service(service_name, instance_id)
        
        # Deregister from all backends
        for backend_name, backend in self.backends.items():
            try:
                if await backend.deregister_service(service_name, instance_id):
                    success_count += 1
                    logger.debug(f"Deregistered from backend {backend_name}")
                else:
                    logger.warning(f"Failed to deregister from backend {backend_name}")
            except Exception as e:
                logger.error(f"Error deregistering from backend {backend_name}: {e}")
        
        # Remove locally
        if service_name in self._local_services:
            self._local_services[service_name].pop(instance_id, None)
            if not self._local_services[service_name]:
                del self._local_services[service_name]
        
        # Invalidate cache
        self.cache.invalidate_service(service_name)
        
        # Emit event
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.SERVICE_DEREGISTERED,
            service_name=service_name,
            instance=instance,
            metadata={"backends_deregistered": success_count, "total_backends": total_backends}
        ))
        
        return success_count > 0
    
    async def discover(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances with caching."""
        # Check cache first
        cache_key = f"{service_name}:{','.join(sorted(tags)) if tags else ''}"
        cached_instances = self.cache.get_services(cache_key)
        if cached_instances is not None:
            logger.debug(f"Cache hit for service discovery: {service_name}")
            return cached_instances
        
        logger.debug(f"Cache miss for service discovery: {service_name}")
        
        # Discover from primary backend
        instances = []
        if self.primary_backend:
            try:
                instances = await self.primary_backend.discover_services(service_name, tags)
                logger.debug(f"Discovered {len(instances)} instances from primary backend")
            except Exception as e:
                logger.error(f"Error discovering from primary backend: {e}")
        
        # Fallback to other backends if primary fails
        if not instances:
            for backend_name, backend in self.backends.items():
                if backend == self.primary_backend:
                    continue
                
                try:
                    instances = await backend.discover_services(service_name, tags)
                    if instances:
                        logger.debug(f"Discovered {len(instances)} instances from fallback backend {backend_name}")
                        break
                except Exception as e:
                    logger.error(f"Error discovering from backend {backend_name}: {e}")
        
        # Filter instances if tags specified
        if tags:
            filter_obj = ServiceFilter(tags=tags)
            instances = [i for i in instances if filter_obj.matches(i)]
        
        # Cache the results
        self.cache.set_services(cache_key, instances)
        
        return instances
    
    async def discover_with_load_balancing(
        self,
        service_name: str,
        tags: Optional[Set[str]] = None,
        count: int = 1
    ) -> List[ServiceInstance]:
        """Discover service instances with load balancing."""
        all_instances = await self.discover(service_name, tags)
        
        if not all_instances:
            return []
        
        if count >= len(all_instances):
            return all_instances
        
        selected_instances = []
        for _ in range(count):
            instance = self.service_selector.select_instance(all_instances)
            if instance:
                selected_instances.append(instance)
                # Record connection for load balancing
                self.service_selector.record_connection(instance)
        
        return selected_instances
    
    async def get_service(self, service_name: str, instance_id: str) -> Optional[ServiceInstance]:
        """Get a specific service instance."""
        # Check local cache first
        if service_name in self._local_services:
            if instance_id in self._local_services[service_name]:
                return self._local_services[service_name][instance_id]
        
        # Query backends
        for backend in self.backends.values():
            try:
                instances = await backend.discover_services(service_name)
                for instance in instances:
                    if instance.instance_id == instance_id:
                        return instance
            except Exception as e:
                logger.error(f"Error querying backend {backend.name}: {e}")
        
        return None
    
    async def list_services(self) -> List[str]:
        """List all service names."""
        service_names = set()
        
        # Get from all backends
        for backend in self.backends.values():
            try:
                all_services = await backend.get_all_services()
                service_names.update(all_services.keys())
            except Exception as e:
                logger.error(f"Error listing services from backend {backend.name}: {e}")
        
        # Add local services
        service_names.update(self._local_services.keys())
        
        return sorted(list(service_names))
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the registry and all backends."""
        health_status = {
            "registry": {
                "status": "healthy" if self._is_started else "unhealthy",
                "started": self._is_started,
                "local_services": len(self._local_services),
                "cache_size": len(self.cache._cache),
                "backends": len(self.backends)
            },
            "backends": {}
        }
        
        # Check each backend
        for backend_name, backend in self.backends.items():
            try:
                backend_healthy = await backend.health_check()
                health_status["backends"][backend_name] = {
                    "status": "healthy" if backend_healthy else "unhealthy",
                    "connected": backend.is_connected
                }
            except Exception as e:
                health_status["backends"][backend_name] = {
                    "status": "error",
                    "error": str(e),
                    "connected": False
                }
        
        # Overall health
        backend_statuses = [b.get("status") for b in health_status["backends"].values()]
        all_backends_healthy = all(status == "healthy" for status in backend_statuses)
        
        health_status["overall"] = {
            "status": "healthy" if (self._is_started and all_backends_healthy) else "unhealthy",
            "healthy_backends": sum(1 for status in backend_statuses if status == "healthy"),
            "total_backends": len(backend_statuses)
        }
        
        return health_status
    
    async def update_service_health(
        self,
        service_name: str,
        instance_id: str,
        status: ServiceStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update the health status of a service instance."""
        logger.debug(f"Updating health for {service_name}/{instance_id}: {status.value}")
        
        success_count = 0
        
        # Update in backends
        for backend in self.backends.values():
            try:
                if await backend.update_service_health(service_name, instance_id, status):
                    success_count += 1
            except Exception as e:
                logger.error(f"Error updating health in backend {backend.name}: {e}")
        
        # Update locally
        if service_name in self._local_services:
            if instance_id in self._local_services[service_name]:
                instance = self._local_services[service_name][instance_id]
                instance.update_health(status, metadata)
        
        # Invalidate cache
        self.cache.invalidate_service(service_name)
        
        # Emit event
        instance = await self.get_service(service_name, instance_id)
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.SERVICE_HEALTH_CHANGED,
            service_name=service_name,
            instance=instance,
            metadata={"new_status": status.value, "backends_updated": success_count}
        ))
        
        return success_count > 0
    
    async def watch_services(self, service_names: Optional[List[str]] = None) -> None:
        """Watch for service changes across all backends."""
        if not service_names:
            service_names = await self.list_services()
        
        # Start watching on all backends that support it
        for backend in self.backends.values():
            try:
                for service_name in service_names:
                    await backend.watch_services(service_name)
            except Exception as e:
                logger.error(f"Error starting watch on backend {backend.name}: {e}")
    
    def add_event_handler(self, handler: Callable[[DiscoveryEvent], None]) -> None:
        """Add an event handler for discovery events."""
        self.event_handlers.append(handler)
    
    def remove_event_handler(self, handler: Callable[[DiscoveryEvent], None]) -> None:
        """Remove an event handler."""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
    
    async def _emit_event(self, event: DiscoveryEvent) -> None:
        """Emit a discovery event to all handlers."""
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def _handle_backend_event(self, event: DiscoveryEvent) -> None:
        """Handle events from backends."""
        # Invalidate cache for affected service
        self.cache.invalidate_service(event.service_name)
        
        # Re-emit the event
        await self._emit_event(event)
    
    def get_backend(self, name: str) -> Optional[ServiceDiscoveryBackend]:
        """Get a specific backend by name."""
        return self.backends.get(name)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """Clear the service discovery cache."""
        self.cache.clear()
        logger.info("Service discovery cache cleared")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
# fastapi-microservices-sdk/fastapi_microservices_sdk/core/service_registry.py 
"""
Service registry for managing microservice discovery and registration.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from ..config import get_config
from ..exceptions import DiscoveryError
from ..constants import SERVICE_REGISTRY_TTL, SERVICE_HEARTBEAT_INTERVAL


@dataclass
class ServiceInstance:
    """Represents a service instance in the registry."""
    name: str
    service_id: str
    host: str
    port: int
    version: str
    status: str = "healthy"
    metadata: Dict[str, Any] = None
    registered_at: float = None
    last_heartbeat: float = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = time.time()
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()
    
    @property
    def url(self) -> str:
        """Get the service URL."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if the service instance is healthy."""
        return self.status == "healthy"
    
    @property
    def is_expired(self) -> bool:
        """Check if the service instance has expired."""
        return time.time() - self.last_heartbeat > SERVICE_REGISTRY_TTL
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ServiceRegistry:
    """
    In-memory service registry for development and testing.
    
    In production, this would be replaced with external service discovery
    systems like Consul, etcd, or Kubernetes service discovery.
    """
    
    _instance: Optional['ServiceRegistry'] = None
    _initialized: bool = False
    
    def __init__(self):
        self._services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger("service_registry")
    
    @classmethod
    def get_instance(cls) -> 'ServiceRegistry':
        """Get singleton instance of the service registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def initialize(cls):
        """Initialize the service registry."""
        if not cls._initialized:
            instance = cls.get_instance()
            instance._start_cleanup_task()
            cls._initialized = True
    
    def _start_cleanup_task(self):
        """Start the cleanup task for expired services."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_services())
    
    async def _cleanup_expired_services(self):
        """Periodically clean up expired service instances."""
        while True:
            try:
                await asyncio.sleep(SERVICE_HEARTBEAT_INTERVAL)
                await self._remove_expired_services()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
    
    async def _remove_expired_services(self):
        """Remove expired service instances."""
        async with self._lock:
            expired_services = []
            
            for service_name, instances in self._services.items():
                expired_instances = [
                    instance_id for instance_id, instance in instances.items()
                    if instance.is_expired
                ]
                
                for instance_id in expired_instances:
                    expired_services.append((service_name, instance_id))
                    del instances[instance_id]
                
                # Remove empty service entries
                if not instances:
                    del self._services[service_name]
            
            if expired_services:
                self.logger.info(f"Removed {len(expired_services)} expired service instances")
    
    async def register_service(
        self,
        name: str,
        service_id: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a service instance.
        
        Args:
            name: Service name
            service_id: Unique service instance ID
            host: Service host
            port: Service port
            version: Service version
            metadata: Additional metadata
            
        Returns:
            True if registration successful
        """
        try:
            async with self._lock:
                if name not in self._services:
                    self._services[name] = {}
                
                instance = ServiceInstance(
                    name=name,
                    service_id=service_id,
                    host=host,
                    port=port,
                    version=version,
                    metadata=metadata or {}
                )
                
                self._services[name][service_id] = instance
                
                self.logger.info(f"Registered service: {name} ({service_id}) at {host}:{port}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to register service {name}: {e}")
            raise DiscoveryError(f"Service registration failed: {e}")
    
    async def unregister_service(self, name: str, service_id: str) -> bool:
        """
        Unregister a service instance.
        
        Args:
            name: Service name
            service_id: Service instance ID
            
        Returns:
            True if unregistration successful
        """
        try:
            async with self._lock:
                if name in self._services and service_id in self._services[name]:
                    del self._services[name][service_id]
                    
                    # Remove empty service entries
                    if not self._services[name]:
                        del self._services[name]
                    
                    self.logger.info(f"Unregistered service: {name} ({service_id})")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to unregister service {name}: {e}")
            raise DiscoveryError(f"Service unregistration failed: {e}")
    
    async def discover_service(self, name: str) -> List[ServiceInstance]:
        """
        Discover instances of a service.
        
        Args:
            name: Service name to discover
            
        Returns:
            List of healthy service instances
        """
        async with self._lock:
            if name not in self._services:
                return []
            
            # Return only healthy, non-expired instances
            instances = [
                instance for instance in self._services[name].values()
                if instance.is_healthy and not instance.is_expired
            ]
            
            return instances
    
    async def get_service_instance(self, name: str, service_id: str) -> Optional[ServiceInstance]:
        """
        Get a specific service instance.
        
        Args:
            name: Service name
            service_id: Service instance ID
            
        Returns:
            Service instance or None if not found
        """
        async with self._lock:
            if name in self._services and service_id in self._services[name]:
                instance = self._services[name][service_id]
                if not instance.is_expired:
                    return instance
            return None
    
    async def update_service_status(self, name: str, service_id: str, status: str) -> bool:
        """
        Update service instance status.
        
        Args:
            name: Service name
            service_id: Service instance ID
            status: New status
            
        Returns:
            True if update successful
        """
        async with self._lock:
            if name in self._services and service_id in self._services[name]:
                self._services[name][service_id].status = status
                self._services[name][service_id].update_heartbeat()
                return True
            return False
    
    async def heartbeat(self, name: str, service_id: str) -> bool:
        """
        Send heartbeat for a service instance.
        
        Args:
            name: Service name
            service_id: Service instance ID
            
        Returns:
            True if heartbeat successful
        """
        async with self._lock:
            if name in self._services and service_id in self._services[name]:
                self._services[name][service_id].update_heartbeat()
                return True
            return False
    
    async def list_services(self) -> Dict[str, List[ServiceInstance]]:
        """
        List all registered services.
        
        Returns:
            Dictionary mapping service names to their instances
        """
        async with self._lock:
            result = {}
            for name, instances in self._services.items():
                healthy_instances = [
                    instance for instance in instances.values()
                    if instance.is_healthy and not instance.is_expired
                ]
                if healthy_instances:
                    result[name] = healthy_instances
            return result
    
    async def get_service_count(self) -> int:
        """Get total number of registered services."""
        services = await self.list_services()
        return len(services)
    
    async def get_instance_count(self) -> int:
        """Get total number of service instances."""
        services = await self.list_services()
        return sum(len(instances) for instances in services.values())
    
    def stop(self):
        """Stop the service registry and cleanup tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

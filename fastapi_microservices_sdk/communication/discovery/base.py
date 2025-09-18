"""
Base classes and interfaces for service discovery.

This module provides the abstract base classes and data models for service discovery
implementations across different backends.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, validator


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    CRITICAL = "critical"


class DiscoveryEventType(str, Enum):
    """Service discovery event types."""
    SERVICE_REGISTERED = "service_registered"
    SERVICE_DEREGISTERED = "service_deregistered"
    SERVICE_UPDATED = "service_updated"
    SERVICE_HEALTH_CHANGED = "service_health_changed"
    BACKEND_CONNECTED = "backend_connected"
    BACKEND_DISCONNECTED = "backend_disconnected"


@dataclass
class ServiceInstance:
    """Represents a service instance in the service registry."""
    
    service_name: str
    instance_id: str
    address: str
    port: int
    status: ServiceStatus = ServiceStatus.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    health_check_url: Optional[str] = None
    health_check_interval: int = 30  # seconds
    last_health_check: Optional[datetime] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def url(self) -> str:
        """Get the full URL for this service instance."""
        scheme = self.metadata.get("scheme", "http")
        return f"{scheme}://{self.address}:{self.port}"
    
    @property
    def is_healthy(self) -> bool:
        """Check if the service instance is healthy."""
        return self.status == ServiceStatus.HEALTHY
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if the service instance data is stale."""
        if not self.last_health_check:
            return True
        
        age = (datetime.now(timezone.utc) - self.last_health_check).total_seconds()
        return age > max_age_seconds
    
    def update_health(self, status: ServiceStatus, metadata: Optional[Dict[str, Any]] = None):
        """Update the health status of this service instance."""
        self.status = status
        self.last_health_check = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        
        if metadata:
            self.metadata.update(metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "service_name": self.service_name,
            "instance_id": self.instance_id,
            "address": self.address,
            "port": self.port,
            "status": self.status.value,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "health_check_url": self.health_check_url,
            "health_check_interval": self.health_check_interval,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "registered_at": self.registered_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "url": self.url,
            "is_healthy": self.is_healthy
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceInstance":
        """Create instance from dictionary representation."""
        instance = cls(
            service_name=data["service_name"],
            instance_id=data["instance_id"],
            address=data["address"],
            port=data["port"],
            status=ServiceStatus(data.get("status", ServiceStatus.UNKNOWN.value)),
            metadata=data.get("metadata", {}),
            tags=set(data.get("tags", [])),
            health_check_url=data.get("health_check_url"),
            health_check_interval=data.get("health_check_interval", 30)
        )
        
        if data.get("last_health_check"):
            instance.last_health_check = datetime.fromisoformat(data["last_health_check"])
        
        if data.get("registered_at"):
            instance.registered_at = datetime.fromisoformat(data["registered_at"])
            
        if data.get("updated_at"):
            instance.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return instance


@dataclass
class DiscoveryEvent:
    """Represents a service discovery event."""
    
    event_type: DiscoveryEventType
    service_name: str
    instance: Optional[ServiceInstance] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceDiscoveryBackend(ABC):
    """Abstract base class for service discovery backends."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.is_connected = False
        self.event_handlers: List[Callable[[DiscoveryEvent], None]] = []
        self._connection_lock = asyncio.Lock()
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the service discovery backend."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service discovery backend."""
        pass
    
    @abstractmethod
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        pass
    
    @abstractmethod
    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        pass
    
    @abstractmethod
    async def discover_services(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances by name and optional tags."""
        pass
    
    @abstractmethod
    async def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the backend is healthy."""
        pass
    
    async def update_service_health(self, service_name: str, instance_id: str, status: ServiceStatus) -> bool:
        """Update the health status of a service instance."""
        # Default implementation - can be overridden by specific backends
        return True
    
    async def watch_services(self, service_name: Optional[str] = None) -> None:
        """Watch for service changes (optional implementation)."""
        pass
    
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
                # Log error but don't fail the operation
                print(f"Error in event handler: {e}")
    
    async def ensure_connected(self) -> None:
        """Ensure the backend is connected."""
        if not self.is_connected:
            async with self._connection_lock:
                if not self.is_connected:
                    await self.connect()


class ServiceRegistry(ABC):
    """Abstract base class for service registries."""
    
    @abstractmethod
    async def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        pass
    
    @abstractmethod
    async def deregister(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        pass
    
    @abstractmethod
    async def discover(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances."""
        pass
    
    @abstractmethod
    async def get_service(self, service_name: str, instance_id: str) -> Optional[ServiceInstance]:
        """Get a specific service instance."""
        pass
    
    @abstractmethod
    async def list_services(self) -> List[str]:
        """List all service names."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the registry."""
        pass


class ServiceFilter:
    """Filter for service discovery queries."""
    
    def __init__(
        self,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: Optional[ServiceStatus] = None,
        healthy_only: bool = True
    ):
        self.tags = tags or set()
        self.metadata = metadata or {}
        self.status = status
        self.healthy_only = healthy_only
    
    def matches(self, instance: ServiceInstance) -> bool:
        """Check if a service instance matches this filter."""
        # Check health status
        if self.healthy_only and not instance.is_healthy:
            return False
        
        # Check specific status
        if self.status and instance.status != self.status:
            return False
        
        # Check tags
        if self.tags and not self.tags.issubset(instance.tags):
            return False
        
        # Check metadata
        for key, value in self.metadata.items():
            if key not in instance.metadata or instance.metadata[key] != value:
                return False
        
        return True


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for service selection."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    HEALTH_BASED = "health_based"


class ServiceSelector:
    """Service selection with load balancing strategies."""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self._round_robin_counters: Dict[str, int] = {}
        self._connection_counts: Dict[str, int] = {}
    
    def select_instance(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Select a service instance based on the load balancing strategy."""
        if not instances:
            return None
        
        # Filter healthy instances
        healthy_instances = [i for i in instances if i.is_healthy]
        if not healthy_instances:
            # Fallback to any instance if no healthy ones
            healthy_instances = instances
        
        if len(healthy_instances) == 1:
            return healthy_instances[0]
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(healthy_instances)
        elif self.strategy == LoadBalancingStrategy.HEALTH_BASED:
            return self._health_based_select(healthy_instances)
        else:
            return healthy_instances[0]
    
    def _round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Round robin selection."""
        service_name = instances[0].service_name
        counter = self._round_robin_counters.get(service_name, 0)
        selected = instances[counter % len(instances)]
        self._round_robin_counters[service_name] = counter + 1
        return selected
    
    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Random selection."""
        import random
        return random.choice(instances)
    
    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Least connections selection."""
        min_connections = float('inf')
        selected = instances[0]
        
        for instance in instances:
            key = f"{instance.address}:{instance.port}"
            connections = self._connection_counts.get(key, 0)
            if connections < min_connections:
                min_connections = connections
                selected = instance
        
        return selected
    
    def _weighted_round_robin_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Weighted round robin selection based on instance metadata."""
        weights = []
        for instance in instances:
            weight = instance.metadata.get("weight", 1.0)
            weights.append(max(weight, 0.1))  # Minimum weight
        
        # Simple weighted selection
        import random
        total_weight = sum(weights)
        r = random.uniform(0, total_weight)
        
        cumulative_weight = 0
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return instances[i]
        
        return instances[-1]
    
    def _health_based_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """Health-based selection prioritizing recently healthy instances."""
        now = datetime.now(timezone.utc)
        
        # Score instances based on health check recency
        scored_instances = []
        for instance in instances:
            if instance.last_health_check:
                age = (now - instance.last_health_check).total_seconds()
                score = max(0, 300 - age)  # Higher score for more recent checks
            else:
                score = 0
            
            scored_instances.append((score, instance))
        
        # Sort by score (descending) and return the best
        scored_instances.sort(key=lambda x: x[0], reverse=True)
        return scored_instances[0][1]
    
    def record_connection(self, instance: ServiceInstance) -> None:
        """Record a new connection to an instance."""
        key = f"{instance.address}:{instance.port}"
        self._connection_counts[key] = self._connection_counts.get(key, 0) + 1
    
    def record_disconnection(self, instance: ServiceInstance) -> None:
        """Record a disconnection from an instance."""
        key = f"{instance.address}:{instance.port}"
        if key in self._connection_counts:
            self._connection_counts[key] = max(0, self._connection_counts[key] - 1)


# Configuration models
class ServiceDiscoveryConfig(BaseModel):
    """Configuration for service discovery."""
    
    backend: str = Field(..., description="Service discovery backend type")
    host: str = Field(default="localhost", description="Backend host")
    port: int = Field(default=8500, description="Backend port")
    scheme: str = Field(default="http", description="Connection scheme")
    timeout: float = Field(default=10.0, description="Connection timeout")
    
    # Authentication
    username: Optional[str] = Field(default=None, description="Username for authentication")
    password: Optional[str] = Field(default=None, description="Password for authentication")
    token: Optional[str] = Field(default=None, description="Token for authentication")
    
    # SSL/TLS
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca_path: Optional[str] = Field(default=None, description="SSL CA certificate path")
    
    # Service registration
    service_name: Optional[str] = Field(default=None, description="Service name to register")
    service_id: Optional[str] = Field(default=None, description="Service instance ID")
    service_address: Optional[str] = Field(default=None, description="Service address")
    service_port: Optional[int] = Field(default=None, description="Service port")
    service_tags: List[str] = Field(default_factory=list, description="Service tags")
    service_metadata: Dict[str, Any] = Field(default_factory=dict, description="Service metadata")
    
    # Health checks
    health_check_url: Optional[str] = Field(default=None, description="Health check URL")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=10, description="Health check timeout in seconds")
    health_check_deregister_critical_after: int = Field(
        default=300, description="Deregister after critical for seconds"
    )
    
    # Discovery settings
    watch_services: List[str] = Field(default_factory=list, description="Services to watch")
    watch_interval: int = Field(default=30, description="Watch interval in seconds")
    cache_ttl: int = Field(default=60, description="Cache TTL in seconds")
    
    # Load balancing
    load_balancing_strategy: LoadBalancingStrategy = Field(
        default=LoadBalancingStrategy.ROUND_ROBIN, description="Load balancing strategy"
    )
    health_check_required: bool = Field(default=True, description="Require health checks")
    
    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v
    
    @validator('health_check_interval')
    def validate_health_check_interval(cls, v):
        if v <= 0:
            raise ValueError('Health check interval must be positive')
        return v
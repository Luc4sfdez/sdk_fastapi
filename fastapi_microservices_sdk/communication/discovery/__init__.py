"""
Service Discovery module for FastAPI Microservices SDK.

This module provides service discovery capabilities with support for multiple backends
including Consul, etcd, and Kubernetes.
"""

from .base import ServiceDiscoveryBackend, ServiceInstance, ServiceRegistry
from .registry import EnhancedServiceRegistry
from .cache import ServiceDiscoveryCache
from .health import HealthCheckScheduler

__all__ = [
    "ServiceDiscoveryBackend",
    "ServiceInstance", 
    "ServiceRegistry",
    "EnhancedServiceRegistry",
    "ServiceDiscoveryCache",
    "HealthCheckScheduler"
]

# Optional imports for specific backends
try:
    from .consul import ConsulServiceDiscovery
    __all__.append("ConsulServiceDiscovery")
except ImportError:
    pass

try:
    from .etcd import EtcdServiceDiscovery
    __all__.append("EtcdServiceDiscovery")
except ImportError:
    pass

try:
    from .kubernetes import KubernetesServiceDiscovery
    __all__.append("KubernetesServiceDiscovery")
except ImportError:
    pass
"""
Data types for service management.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class ServiceStatus(Enum):
    """Service status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"
    UNKNOWN = "unknown"


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class ResourceUsage:
    """Resource usage information."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    network_in_mb: float = 0.0
    network_out_mb: float = 0.0


@dataclass
class ServiceInfo:
    """Service information data class."""
    id: str
    name: str
    template_type: str
    status: ServiceStatus
    port: int
    created_at: datetime
    last_updated: datetime
    health_status: HealthStatus
    resource_usage: ResourceUsage
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ServiceDetails:
    """Detailed service information."""
    service_info: ServiceInfo
    endpoints: List[str]
    dependencies: List[str]
    environment_variables: Dict[str, str]
    logs_path: Optional[str] = None
    metrics_enabled: bool = True
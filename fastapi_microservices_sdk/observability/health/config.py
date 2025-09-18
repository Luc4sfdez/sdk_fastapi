"""
Health monitoring configuration for FastAPI Microservices SDK.

This module provides configuration classes for health monitoring,
Kubernetes probes, and dependency health checking.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ProbeType(str, Enum):
    """Kubernetes probe type enumeration."""
    READINESS = "readiness"
    LIVENESS = "liveness"
    STARTUP = "startup"


class DependencyType(str, Enum):
    """Dependency type enumeration."""
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    EXTERNAL_API = "external_api"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    SERVICE = "service"


@dataclass
class ProbeConfig:
    """Kubernetes probe configuration."""
    enabled: bool = True
    path: str = "/health"
    port: int = 8000
    scheme: str = "HTTP"
    
    # Timing configuration
    initial_delay_seconds: int = 10
    period_seconds: int = 10
    timeout_seconds: int = 5
    success_threshold: int = 1
    failure_threshold: int = 3
    
    # HTTP headers for probe requests
    http_headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Kubernetes manifest."""
        config = {
            "httpGet": {
                "path": self.path,
                "port": self.port,
                "scheme": self.scheme
            },
            "initialDelaySeconds": self.initial_delay_seconds,
            "periodSeconds": self.period_seconds,
            "timeoutSeconds": self.timeout_seconds,
            "successThreshold": self.success_threshold,
            "failureThreshold": self.failure_threshold
        }
        
        if self.http_headers:
            config["httpGet"]["httpHeaders"] = [
                {"name": k, "value": v} for k, v in self.http_headers.items()
            ]
        
        return config


@dataclass
class DependencyConfig:
    """Dependency health check configuration."""
    name: str
    type: DependencyType
    enabled: bool = True
    
    # Connection details
    host: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    database_name: Optional[str] = None
    
    # Health check configuration
    timeout_seconds: float = 5.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Circuit breaker configuration
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3
    
    # Custom health check
    custom_check_function: Optional[str] = None
    custom_check_params: Dict[str, Any] = field(default_factory=dict)
    
    # Monitoring
    collect_metrics: bool = True
    alert_on_failure: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.type.value,
            'enabled': self.enabled,
            'host': self.host,
            'port': self.port,
            'url': self.url,
            'database_name': self.database_name,
            'timeout_seconds': self.timeout_seconds,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'circuit_breaker_enabled': self.circuit_breaker_enabled,
            'failure_threshold': self.failure_threshold,
            'recovery_timeout': self.recovery_timeout,
            'half_open_max_calls': self.half_open_max_calls,
            'custom_check_function': self.custom_check_function,
            'custom_check_params': self.custom_check_params,
            'collect_metrics': self.collect_metrics,
            'alert_on_failure': self.alert_on_failure
        }


class HealthConfig(BaseModel):
    """Health monitoring configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # Health monitoring settings
    enabled: bool = Field(True, description="Enable health monitoring")
    health_check_interval: int = Field(30, description="Health check interval in seconds")
    health_timeout: float = Field(10.0, description="Health check timeout in seconds")
    
    # Kubernetes probe configurations
    readiness_probe: ProbeConfig = Field(
        default_factory=lambda: ProbeConfig(
            path="/health/ready",
            initial_delay_seconds=5,
            period_seconds=10,
            timeout_seconds=5,
            failure_threshold=3
        ),
        description="Readiness probe configuration"
    )
    
    liveness_probe: ProbeConfig = Field(
        default_factory=lambda: ProbeConfig(
            path="/health/live",
            initial_delay_seconds=30,
            period_seconds=30,
            timeout_seconds=10,
            failure_threshold=3
        ),
        description="Liveness probe configuration"
    )
    
    startup_probe: ProbeConfig = Field(
        default_factory=lambda: ProbeConfig(
            path="/health/startup",
            initial_delay_seconds=0,
            period_seconds=5,
            timeout_seconds=3,
            failure_threshold=30
        ),
        description="Startup probe configuration"
    )
    
    # Dependency configurations
    dependencies: List[DependencyConfig] = Field(
        default_factory=list,
        description="Dependency health check configurations"
    )
    
    # Health aggregation settings
    aggregate_health: bool = Field(True, description="Aggregate dependency health")
    fail_on_dependency_failure: bool = Field(False, description="Fail health check if dependency fails")
    degraded_threshold: float = Field(0.8, description="Threshold for degraded status (0.0-1.0)")
    
    # Metrics and monitoring
    collect_health_metrics: bool = Field(True, description="Collect health metrics")
    expose_detailed_health: bool = Field(True, description="Expose detailed health information")
    include_system_info: bool = Field(True, description="Include system information in health")
    
    # Security settings
    require_authentication: bool = Field(False, description="Require authentication for health endpoints")
    allowed_ips: List[str] = Field(default_factory=list, description="Allowed IP addresses")
    health_check_token: Optional[str] = Field(None, description="Health check authentication token")
    
    # Caching settings
    cache_health_results: bool = Field(True, description="Cache health check results")
    cache_ttl_seconds: int = Field(30, description="Health cache TTL in seconds")
    
    # Alerting settings
    alert_on_health_change: bool = Field(True, description="Alert when health status changes")
    alert_channels: List[str] = Field(default_factory=list, description="Alert notification channels")
    
    @validator('degraded_threshold')
    def validate_degraded_threshold(cls, v):
        """Validate degraded threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('degraded_threshold must be between 0.0 and 1.0')
        return v
    
    @validator('health_timeout')
    def validate_health_timeout(cls, v):
        """Validate health timeout is positive."""
        if v <= 0:
            raise ValueError('health_timeout must be positive')
        return v
    
    @validator('health_check_interval')
    def validate_health_check_interval(cls, v):
        """Validate health check interval is positive."""
        if v <= 0:
            raise ValueError('health_check_interval must be positive')
        return v
    
    def add_dependency(self, dependency: DependencyConfig):
        """Add dependency configuration."""
        self.dependencies.append(dependency)
    
    def get_dependency(self, name: str) -> Optional[DependencyConfig]:
        """Get dependency configuration by name."""
        for dep in self.dependencies:
            if dep.name == name:
                return dep
        return None
    
    def remove_dependency(self, name: str) -> bool:
        """Remove dependency configuration by name."""
        for i, dep in enumerate(self.dependencies):
            if dep.name == name:
                del self.dependencies[i]
                return True
        return False
    
    def to_kubernetes_manifest(self) -> Dict[str, Any]:
        """Generate Kubernetes deployment manifest with probes."""
        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": self.service_name,
                "labels": {
                    "app": self.service_name,
                    "version": self.service_version,
                    "environment": self.environment
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": self.service_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": self.service_name,
                            "version": self.service_version,
                            "environment": self.environment
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": self.service_name,
                            "image": f"{self.service_name}:{self.service_version}",
                            "ports": [{
                                "containerPort": self.readiness_probe.port,
                                "name": "http"
                            }]
                        }]
                    }
                }
            }
        }
        
        container = manifest["spec"]["template"]["spec"]["containers"][0]
        
        # Add probes if enabled
        if self.readiness_probe.enabled:
            container["readinessProbe"] = self.readiness_probe.to_dict()
        
        if self.liveness_probe.enabled:
            container["livenessProbe"] = self.liveness_probe.to_dict()
        
        if self.startup_probe.enabled:
            container["startupProbe"] = self.startup_probe.to_dict()
        
        return manifest
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


def create_health_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> HealthConfig:
    """Create health configuration with defaults."""
    return HealthConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


def create_database_dependency(
    name: str,
    host: str,
    port: int,
    database_name: str,
    **kwargs
) -> DependencyConfig:
    """Create database dependency configuration."""
    return DependencyConfig(
        name=name,
        type=DependencyType.DATABASE,
        host=host,
        port=port,
        database_name=database_name,
        **kwargs
    )


def create_cache_dependency(
    name: str,
    host: str,
    port: int,
    **kwargs
) -> DependencyConfig:
    """Create cache dependency configuration."""
    return DependencyConfig(
        name=name,
        type=DependencyType.CACHE,
        host=host,
        port=port,
        **kwargs
    )


def create_api_dependency(
    name: str,
    url: str,
    **kwargs
) -> DependencyConfig:
    """Create external API dependency configuration."""
    return DependencyConfig(
        name=name,
        type=DependencyType.EXTERNAL_API,
        url=url,
        **kwargs
    )


# Export main classes and functions
__all__ = [
    'HealthStatus',
    'ProbeType',
    'DependencyType',
    'ProbeConfig',
    'DependencyConfig',
    'HealthConfig',
    'create_health_config',
    'create_database_dependency',
    'create_cache_dependency',
    'create_api_dependency',
]
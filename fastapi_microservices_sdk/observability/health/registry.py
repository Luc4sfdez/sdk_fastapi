"""
Health Check Registry for FastAPI Microservices SDK.

This module provides a registry system for health checks with
automatic discovery and management capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from .config import HealthConfig, DependencyConfig
from .monitor import HealthCheckResult, HealthMonitor
from .dependencies import DependencyChecker, create_dependency_checker
from .exceptions import HealthRegistryError


class HealthCheckCategory(str, Enum):
    """Health check category enumeration."""
    CORE = "core"
    DEPENDENCY = "dependency"
    SYSTEM = "system"
    CUSTOM = "custom"


@dataclass
class HealthCheckInfo:
    """Health check information."""
    name: str
    category: HealthCheckCategory
    description: str
    enabled: bool = True
    timeout_seconds: float = 5.0
    check_function: Optional[Callable] = None
    dependency_config: Optional[DependencyConfig] = None
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'category': self.category.value,
            'description': self.description,
            'enabled': self.enabled,
            'timeout_seconds': self.timeout_seconds,
            'tags': list(self.tags),
            'metadata': self.metadata
        }


class HealthCheckRegistry:
    """Registry for health checks with automatic discovery."""
    
    def __init__(self, config: HealthConfig, health_monitor: HealthMonitor):
        self.config = config
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(__name__)
        
        # Registry storage
        self._health_checks: Dict[str, HealthCheckInfo] = {}
        self._dependency_checkers: Dict[str, DependencyChecker] = {}
        
        # Auto-discovery settings
        self._auto_discovery_enabled = True
        self._discovery_patterns: List[str] = []
        
        # Statistics
        self._registration_count = 0
        self._discovery_count = 0
        
        # Initialize with built-in checks
        self._register_builtin_checks()
        self._register_dependency_checks()
    
    def _register_builtin_checks(self):
        """Register built-in health checks."""
        # Core application health check
        self.register_health_check(
            HealthCheckInfo(
                name="application",
                category=HealthCheckCategory.CORE,
                description="Core application health check",
                check_function=self.health_monitor._check_application_health,
                tags={"core", "application"}
            )
        )
        
        # System health checks
        if self.config.include_system_info:
            self.register_health_check(
                HealthCheckInfo(
                    name="system_memory",
                    category=HealthCheckCategory.SYSTEM,
                    description="System memory usage check",
                    check_function=self.health_monitor._check_memory_usage,
                    tags={"system", "memory"}
                )
            )
            
            self.register_health_check(
                HealthCheckInfo(
                    name="system_disk",
                    category=HealthCheckCategory.SYSTEM,
                    description="System disk usage check",
                    check_function=self.health_monitor._check_disk_usage,
                    tags={"system", "disk"}
                )
            )
    
    def _register_dependency_checks(self):
        """Register dependency health checks."""
        for dependency in self.config.dependencies:
            if not dependency.enabled:
                continue
            
            # Create dependency checker
            checker = create_dependency_checker(dependency)
            self._dependency_checkers[dependency.name] = checker
            
            # Register health check info
            self.register_health_check(
                HealthCheckInfo(
                    name=dependency.name,
                    category=HealthCheckCategory.DEPENDENCY,
                    description=f"{dependency.type.value} dependency health check",
                    timeout_seconds=dependency.timeout_seconds,
                    dependency_config=dependency,
                    tags={dependency.type.value, "dependency"},
                    metadata={
                        'host': dependency.host,
                        'port': dependency.port,
                        'url': dependency.url,
                        'circuit_breaker_enabled': dependency.circuit_breaker_enabled
                    }
                )
            )
    
    def register_health_check(self, health_check_info: HealthCheckInfo):
        """Register a health check."""
        try:
            if health_check_info.name in self._health_checks:
                self.logger.warning(f"Health check {health_check_info.name} already registered, overwriting")
            
            self._health_checks[health_check_info.name] = health_check_info
            self._registration_count += 1
            
            # Register with health monitor if it has a check function
            if health_check_info.check_function:
                self.health_monitor.register_health_check(
                    health_check_info.name,
                    health_check_info.check_function
                )
            
            # Register dependency checker if it's a dependency
            if (health_check_info.category == HealthCheckCategory.DEPENDENCY and
                health_check_info.dependency_config):
                
                if health_check_info.name not in self._dependency_checkers:
                    checker = create_dependency_checker(health_check_info.dependency_config)
                    self._dependency_checkers[health_check_info.name] = checker
                    
                    # Register checker function with health monitor
                    async def dependency_check_wrapper(dep_config=health_check_info.dependency_config):
                        checker = self._dependency_checkers[dep_config.name]
                        health = await checker.check_health()
                        
                        return HealthCheckResult(
                            name=health.name,
                            status=health.status,
                            message=health.message,
                            timestamp=health.timestamp,
                            duration_ms=health.response_time_ms,
                            details=health.details,
                            error=health.error
                        )
                    
                    self.health_monitor.register_dependency_checker(
                        health_check_info.name,
                        dependency_check_wrapper
                    )
            
            self.logger.info(f"Registered health check: {health_check_info.name}")
            
        except Exception as e:
            raise HealthRegistryError(
                f"Failed to register health check {health_check_info.name}: {e}",
                registry_operation="register",
                check_name=health_check_info.name,
                original_error=e
            )
    
    def unregister_health_check(self, name: str) -> bool:
        """Unregister a health check."""
        try:
            if name not in self._health_checks:
                return False
            
            # Remove from registry
            del self._health_checks[name]
            
            # Remove from health monitor
            self.health_monitor.unregister_health_check(name)
            
            # Remove dependency checker if exists
            if name in self._dependency_checkers:
                del self._dependency_checkers[name]
            
            self.logger.info(f"Unregistered health check: {name}")
            return True
            
        except Exception as e:
            raise HealthRegistryError(
                f"Failed to unregister health check {name}: {e}",
                registry_operation="unregister",
                check_name=name,
                original_error=e
            )
    
    def get_health_check(self, name: str) -> Optional[HealthCheckInfo]:
        """Get health check information by name."""
        return self._health_checks.get(name)
    
    def list_health_checks(
        self,
        category: Optional[HealthCheckCategory] = None,
        enabled_only: bool = False,
        tags: Optional[Set[str]] = None
    ) -> List[HealthCheckInfo]:
        """List health checks with optional filtering."""
        checks = list(self._health_checks.values())
        
        # Filter by category
        if category:
            checks = [check for check in checks if check.category == category]
        
        # Filter by enabled status
        if enabled_only:
            checks = [check for check in checks if check.enabled]
        
        # Filter by tags
        if tags:
            checks = [check for check in checks if check.tags.intersection(tags)]
        
        return checks
    
    def enable_health_check(self, name: str) -> bool:
        """Enable a health check."""
        if name in self._health_checks:
            self._health_checks[name].enabled = True
            self.logger.info(f"Enabled health check: {name}")
            return True
        return False
    
    def disable_health_check(self, name: str) -> bool:
        """Disable a health check."""
        if name in self._health_checks:
            self._health_checks[name].enabled = False
            self.logger.info(f"Disabled health check: {name}")
            return True
        return False
    
    def add_tag(self, name: str, tag: str) -> bool:
        """Add tag to health check."""
        if name in self._health_checks:
            self._health_checks[name].tags.add(tag)
            return True
        return False
    
    def remove_tag(self, name: str, tag: str) -> bool:
        """Remove tag from health check."""
        if name in self._health_checks:
            self._health_checks[name].tags.discard(tag)
            return True
        return False
    
    def update_metadata(self, name: str, metadata: Dict[str, Any]) -> bool:
        """Update health check metadata."""
        if name in self._health_checks:
            self._health_checks[name].metadata.update(metadata)
            return True
        return False
    
    async def discover_health_checks(self) -> List[str]:
        """Discover health checks automatically."""
        if not self._auto_discovery_enabled:
            return []
        
        discovered = []
        
        try:
            # Discover from environment variables
            discovered.extend(await self._discover_from_environment())
            
            # Discover from configuration files
            discovered.extend(await self._discover_from_config())
            
            # Discover from service annotations
            discovered.extend(await self._discover_from_annotations())
            
            self._discovery_count += len(discovered)
            
            if discovered:
                self.logger.info(f"Discovered {len(discovered)} health checks: {discovered}")
            
            return discovered
            
        except Exception as e:
            self.logger.error(f"Health check discovery failed: {e}")
            return []
    
    async def _discover_from_environment(self) -> List[str]:
        """Discover health checks from environment variables."""
        import os
        discovered = []
        
        # Look for environment variables with health check patterns
        for key, value in os.environ.items():
            if key.startswith('HEALTH_CHECK_'):
                check_name = key.replace('HEALTH_CHECK_', '').lower()
                
                # Parse the value as JSON configuration
                try:
                    import json
                    config = json.loads(value)
                    
                    # Create health check from environment config
                    health_check = HealthCheckInfo(
                        name=check_name,
                        category=HealthCheckCategory.CUSTOM,
                        description=config.get('description', f'Environment health check: {check_name}'),
                        enabled=config.get('enabled', True),
                        timeout_seconds=config.get('timeout_seconds', 5.0),
                        tags=set(config.get('tags', []))
                    )
                    
                    self.register_health_check(health_check)
                    discovered.append(check_name)
                    
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Failed to parse health check config from {key}: {e}")
        
        return discovered
    
    async def _discover_from_config(self) -> List[str]:
        """Discover health checks from configuration files."""
        discovered = []
        
        # This would typically read from configuration files
        # For now, we'll just return empty list
        
        return discovered
    
    async def _discover_from_annotations(self) -> List[str]:
        """Discover health checks from service annotations."""
        discovered = []
        
        # This would typically read from Kubernetes annotations or service discovery
        # For now, we'll just return empty list
        
        return discovered
    
    def get_registry_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        category_counts = {}
        for check in self._health_checks.values():
            category = check.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        enabled_count = sum(1 for check in self._health_checks.values() if check.enabled)
        
        return {
            'total_checks': len(self._health_checks),
            'enabled_checks': enabled_count,
            'disabled_checks': len(self._health_checks) - enabled_count,
            'category_counts': category_counts,
            'dependency_checkers': len(self._dependency_checkers),
            'registration_count': self._registration_count,
            'discovery_count': self._discovery_count,
            'auto_discovery_enabled': self._auto_discovery_enabled
        }
    
    def export_registry(self) -> Dict[str, Any]:
        """Export registry configuration."""
        return {
            'health_checks': {
                name: check.to_dict()
                for name, check in self._health_checks.items()
            },
            'statistics': self.get_registry_statistics(),
            'export_timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def import_registry(self, registry_data: Dict[str, Any]):
        """Import registry configuration."""
        try:
            health_checks = registry_data.get('health_checks', {})
            
            for name, check_data in health_checks.items():
                health_check = HealthCheckInfo(
                    name=check_data['name'],
                    category=HealthCheckCategory(check_data['category']),
                    description=check_data['description'],
                    enabled=check_data.get('enabled', True),
                    timeout_seconds=check_data.get('timeout_seconds', 5.0),
                    tags=set(check_data.get('tags', [])),
                    metadata=check_data.get('metadata', {})
                )
                
                self.register_health_check(health_check)
            
            self.logger.info(f"Imported {len(health_checks)} health checks")
            
        except Exception as e:
            raise HealthRegistryError(
                f"Failed to import registry: {e}",
                registry_operation="import",
                original_error=e
            )


def create_health_registry(
    config: HealthConfig,
    health_monitor: HealthMonitor
) -> HealthCheckRegistry:
    """Create health check registry."""
    return HealthCheckRegistry(config, health_monitor)


# Export main classes and functions
__all__ = [
    'HealthCheckCategory',
    'HealthCheckInfo',
    'HealthCheckRegistry',
    'create_health_registry',
]
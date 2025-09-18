"""
Advanced Observability Manager with Enhanced Features.

This module extends the basic observability manager with advanced features
including hot configuration reload, advanced health aggregation, performance
monitoring, and integration with communication and database systems.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import threading
import time
import json
import weakref
from typing import Dict, Any, Optional, List, Callable, Set, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import psutil

from .manager import (
    ObservabilityManager,
    ComponentRegistry,
    ComponentStatus,
    ComponentType,
    ComponentInfo,
    ObservabilityComponent
)
from .config import ObservabilityConfig
from .exceptions import (
    ObservabilityError,
    ConfigurationError,
    ComponentStatus as ComponentStatusError
)

# Integration imports
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


@dataclass
class PerformanceMetrics:
    """Performance metrics for observability components."""
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    initialization_time_ms: float = 0.0
    health_check_time_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    last_error_time: Optional[datetime] = None
    average_response_time_ms: float = 0.0
    throughput_per_second: float = 0.0


@dataclass
class ComponentHealthHistory:
    """Health history tracking for components."""
    component_name: str
    health_checks: deque = field(default_factory=lambda: deque(maxlen=100))
    error_history: deque = field(default_factory=lambda: deque(maxlen=50))
    performance_history: deque = field(default_factory=lambda: deque(maxlen=100))
    uptime_percentage: float = 100.0
    mean_time_to_recovery: float = 0.0
    last_failure_time: Optional[datetime] = None
    failure_count: int = 0
    recovery_count: int = 0


class AdvancedComponentRegistry(ComponentRegistry):
    """Enhanced component registry with advanced features."""
    
    def __init__(self):
        super().__init__()
        self._performance_metrics: Dict[str, PerformanceMetrics] = {}
        self._health_history: Dict[str, ComponentHealthHistory] = {}
        self._component_groups: Dict[str, Set[str]] = defaultdict(set)
        self._watchers: List[Callable] = []
        self._metrics_lock = threading.RLock()
        
    def register_component(
        self,
        name: str,
        component_type: ComponentType,
        instance: ObservabilityComponent,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        group: Optional[str] = None
    ) -> None:
        """Register component with enhanced tracking."""
        super().register_component(name, component_type, instance, config, dependencies)
        
        with self._metrics_lock:
            # Initialize performance metrics
            self._performance_metrics[name] = PerformanceMetrics()
            
            # Initialize health history
            self._health_history[name] = ComponentHealthHistory(component_name=name)
            
            # Add to group if specified
            if group:
                self._component_groups[group].add(name)
        
        # Notify watchers
        self._notify_watchers('component_registered', name, component_type)
    
    def unregister_component(self, name: str) -> None:
        """Unregister component with cleanup."""
        super().unregister_component(name)
        
        with self._metrics_lock:
            # Clean up metrics and history
            self._performance_metrics.pop(name, None)
            self._health_history.pop(name, None)
            
            # Remove from groups
            for group_components in self._component_groups.values():
                group_components.discard(name)
        
        # Notify watchers
        self._notify_watchers('component_unregistered', name)
    
    def update_component_performance(
        self,
        name: str,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        response_time: Optional[float] = None,
        error_occurred: bool = False
    ) -> None:
        """Update component performance metrics."""
        with self._metrics_lock:
            if name not in self._performance_metrics:
                return
            
            metrics = self._performance_metrics[name]
            
            if cpu_usage is not None:
                metrics.cpu_usage_percent = cpu_usage
            
            if memory_usage is not None:
                metrics.memory_usage_mb = memory_usage
            
            if response_time is not None:
                # Update average response time (exponential moving average)
                alpha = 0.1
                if metrics.average_response_time_ms == 0:
                    metrics.average_response_time_ms = response_time
                else:
                    metrics.average_response_time_ms = (
                        alpha * response_time + 
                        (1 - alpha) * metrics.average_response_time_ms
                    )
            
            if error_occurred:
                metrics.error_count += 1
                metrics.last_error_time = datetime.now(timezone.utc)
            else:
                metrics.success_count += 1
            
            # Update throughput (operations per second)
            total_operations = metrics.error_count + metrics.success_count
            if total_operations > 0:
                # Simple throughput calculation (can be enhanced)
                metrics.throughput_per_second = total_operations / max(1, time.time() - 3600)  # Last hour
    
    def record_health_check(self, name: str, health_result: Dict[str, Any]) -> None:
        """Record health check result with history."""
        with self._metrics_lock:
            if name not in self._health_history:
                return
            
            history = self._health_history[name]
            timestamp = datetime.now(timezone.utc)
            
            # Record health check
            health_record = {
                'timestamp': timestamp,
                'status': health_result.get('status', 'unknown'),
                'details': health_result
            }
            history.health_checks.append(health_record)
            
            # Update uptime percentage
            if len(history.health_checks) > 1:
                healthy_checks = sum(
                    1 for check in history.health_checks 
                    if check['status'] == 'healthy'
                )
                history.uptime_percentage = (healthy_checks / len(history.health_checks)) * 100
            
            # Track failures and recoveries
            if health_result.get('status') == 'unhealthy':
                if history.last_failure_time is None:
                    history.failure_count += 1
                    history.last_failure_time = timestamp
            elif health_result.get('status') == 'healthy' and history.last_failure_time:
                # Recovery detected
                recovery_time = (timestamp - history.last_failure_time).total_seconds()
                if history.mean_time_to_recovery == 0:
                    history.mean_time_to_recovery = recovery_time
                else:
                    # Exponential moving average
                    alpha = 0.2
                    history.mean_time_to_recovery = (
                        alpha * recovery_time + 
                        (1 - alpha) * history.mean_time_to_recovery
                    )
                
                history.recovery_count += 1
                history.last_failure_time = None
    
    def get_component_performance(self, name: str) -> Optional[PerformanceMetrics]:
        """Get performance metrics for a component."""
        with self._metrics_lock:
            return self._performance_metrics.get(name)
    
    def get_component_health_history(self, name: str) -> Optional[ComponentHealthHistory]:
        """Get health history for a component."""
        with self._metrics_lock:
            return self._health_history.get(name)
    
    def get_components_by_group(self, group: str) -> List[ComponentInfo]:
        """Get all components in a specific group."""
        with self._lock:
            component_names = self._component_groups.get(group, set())
            return [self._components[name] for name in component_names if name in self._components]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        with self._metrics_lock:
            total_cpu = 0.0
            total_memory = 0.0
            total_errors = 0
            total_successes = 0
            component_count = len(self._performance_metrics)
            
            for metrics in self._performance_metrics.values():
                total_cpu += metrics.cpu_usage_percent
                total_memory += metrics.memory_usage_mb
                total_errors += metrics.error_count
                total_successes += metrics.success_count
            
            return {
                'average_cpu_usage': total_cpu / max(1, component_count),
                'total_memory_usage_mb': total_memory,
                'total_errors': total_errors,
                'total_successes': total_successes,
                'error_rate': total_errors / max(1, total_errors + total_successes),
                'component_count': component_count
            }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        with self._metrics_lock:
            total_uptime = 0.0
            total_mttr = 0.0
            total_failures = 0
            total_recoveries = 0
            component_count = len(self._health_history)
            
            for history in self._health_history.values():
                total_uptime += history.uptime_percentage
                total_mttr += history.mean_time_to_recovery
                total_failures += history.failure_count
                total_recoveries += history.recovery_count
            
            return {
                'average_uptime_percentage': total_uptime / max(1, component_count),
                'average_mttr_seconds': total_mttr / max(1, component_count),
                'total_failures': total_failures,
                'total_recoveries': total_recoveries,
                'recovery_rate': total_recoveries / max(1, total_failures),
                'component_count': component_count
            }
    
    def add_watcher(self, callback: Callable) -> None:
        """Add a watcher for registry events."""
        self._watchers.append(callback)
    
    def remove_watcher(self, callback: Callable) -> None:
        """Remove a watcher."""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def _notify_watchers(self, event_type: str, *args, **kwargs) -> None:
        """Notify all watchers of an event."""
        for watcher in self._watchers:
            try:
                watcher(event_type, *args, **kwargs)
            except Exception as e:
                self._logger.error(f"Watcher notification failed: {e}")


class ConfigurationManager:
    """Manages configuration hot-reload and validation."""
    
    def __init__(self, initial_config: ObservabilityConfig):
        self._current_config = initial_config
        self._config_history: deque = deque(maxlen=10)
        self._config_lock = threading.RLock()
        self._change_listeners: List[Callable] = []
        self._logger = logging.getLogger("observability.config_manager")
        
        # Store initial config in history
        self._config_history.append({
            'config': initial_config.copy(deep=True),
            'timestamp': datetime.now(timezone.utc),
            'version': 1
        })
    
    def get_current_config(self) -> ObservabilityConfig:
        """Get the current configuration."""
        with self._config_lock:
            return self._current_config.copy(deep=True)
    
    def update_config(self, new_config: ObservabilityConfig, validate: bool = True) -> bool:
        """Update configuration with validation and history tracking."""
        with self._config_lock:
            if validate:
                # Validate new configuration
                from .config import validate_observability_config
                issues = validate_observability_config(new_config)
                if issues:
                    raise ConfigurationError(
                        message=f"Configuration validation failed: {issues}",
                        validation_error=str(issues)
                    )
            
            # Store old config
            old_config = self._current_config
            
            # Update current config
            self._current_config = new_config.copy(deep=True)
            
            # Add to history
            version = len(self._config_history) + 1
            self._config_history.append({
                'config': new_config.copy(deep=True),
                'timestamp': datetime.now(timezone.utc),
                'version': version
            })
            
            # Notify listeners
            self._notify_change_listeners(old_config, new_config)
            
            self._logger.info(f"Configuration updated to version {version}")
            return True
    
    def rollback_config(self, version: Optional[int] = None) -> bool:
        """Rollback to a previous configuration version."""
        with self._config_lock:
            if len(self._config_history) < 2:
                return False
            
            if version is None:
                # Rollback to previous version
                target_config = self._config_history[-2]['config']
            else:
                # Rollback to specific version
                target_entry = None
                for entry in self._config_history:
                    if entry['version'] == version:
                        target_entry = entry
                        break
                
                if target_entry is None:
                    return False
                
                target_config = target_entry['config']
            
            # Update to target config
            return self.update_config(target_config, validate=False)
    
    def get_config_history(self) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        with self._config_lock:
            return [
                {
                    'version': entry['version'],
                    'timestamp': entry['timestamp'].isoformat(),
                    'service_name': entry['config'].service_name,
                    'environment': entry['config'].environment
                }
                for entry in self._config_history
            ]
    
    def add_change_listener(self, callback: Callable) -> None:
        """Add a configuration change listener."""
        self._change_listeners.append(callback)
    
    def remove_change_listener(self, callback: Callable) -> None:
        """Remove a configuration change listener."""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)
    
    def _notify_change_listeners(self, old_config: ObservabilityConfig, new_config: ObservabilityConfig) -> None:
        """Notify all change listeners."""
        for listener in self._change_listeners:
            try:
                listener(old_config, new_config)
            except Exception as e:
                self._logger.error(f"Configuration change listener failed: {e}")


class IntegrationManager:
    """Manages integration with other SDK components."""
    
    def __init__(self):
        self._communication_manager: Optional[CommunicationManager] = None
        self._database_manager: Optional[DatabaseManager] = None
        self._integration_status: Dict[str, bool] = {}
        self._logger = logging.getLogger("observability.integration")
    
    async def initialize_integrations(self, config: ObservabilityConfig) -> None:
        """Initialize integrations with other SDK components."""
        # Initialize communication integration
        if COMMUNICATION_INTEGRATION_AVAILABLE:
            try:
                await self._initialize_communication_integration(config)
                self._integration_status['communication'] = True
            except Exception as e:
                self._logger.warning(f"Communication integration failed: {e}")
                self._integration_status['communication'] = False
        
        # Initialize database integration
        if DATABASE_INTEGRATION_AVAILABLE:
            try:
                await self._initialize_database_integration(config)
                self._integration_status['database'] = True
            except Exception as e:
                self._logger.warning(f"Database integration failed: {e}")
                self._integration_status['database'] = False
    
    async def _initialize_communication_integration(self, config: ObservabilityConfig) -> None:
        """Initialize communication system integration."""
        # This will be implemented when communication components are available
        self._logger.info("Communication integration initialized (placeholder)")
    
    async def _initialize_database_integration(self, config: ObservabilityConfig) -> None:
        """Initialize database system integration."""
        # This will be implemented when database components are available
        self._logger.info("Database integration initialized (placeholder)")
    
    def get_integration_status(self) -> Dict[str, bool]:
        """Get status of all integrations."""
        return self._integration_status.copy()
    
    def is_integration_available(self, integration_name: str) -> bool:
        """Check if an integration is available and working."""
        return self._integration_status.get(integration_name, False)


class AdvancedObservabilityManager(ObservabilityManager):
    """Enhanced observability manager with advanced features."""
    
    def __init__(self, config: ObservabilityConfig):
        # Use advanced registry
        super().__init__(config)
        self.registry = AdvancedComponentRegistry()
        
        # Advanced managers
        self._config_manager = ConfigurationManager(config)
        self._integration_manager = IntegrationManager()
        
        # Performance monitoring
        self._system_monitor_task = None
        self._system_metrics_history: deque = deque(maxlen=1000)
        
        # Advanced health monitoring
        self._health_aggregator_task = None
        self._health_trends: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Event system
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Configuration hot-reload
        self._config_reload_enabled = True
        self._config_manager.add_change_listener(self._on_config_changed)
        
        self._logger = logging.getLogger("observability.advanced_manager")
    
    async def initialize(self) -> None:
        """Initialize with advanced features."""
        await super().initialize()
        
        # Initialize integrations
        await self._integration_manager.initialize_integrations(self.config)
        
        # Start advanced monitoring
        await self._start_system_monitoring()
        await self._start_health_aggregation()
        
        # Setup registry watchers
        self.registry.add_watcher(self._on_registry_event)
        
        self._logger.info("Advanced observability manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown with advanced cleanup."""
        # Stop advanced monitoring
        if self._system_monitor_task:
            self._system_monitor_task.cancel()
            try:
                await self._system_monitor_task
            except asyncio.CancelledError:
                pass
        
        if self._health_aggregator_task:
            self._health_aggregator_task.cancel()
            try:
                await self._health_aggregator_task
            except asyncio.CancelledError:
                pass
        
        await super().shutdown()
        self._logger.info("Advanced observability manager shutdown")
    
    async def reload_configuration(self, new_config: ObservabilityConfig) -> bool:
        """Hot-reload configuration without full restart."""
        if not self._config_reload_enabled:
            raise ObservabilityError("Configuration hot-reload is disabled")
        
        try:
            # Update configuration
            self._config_manager.update_config(new_config)
            
            # The actual reload will be handled by the change listener
            return True
            
        except Exception as e:
            self._logger.error(f"Configuration reload failed: {e}")
            raise ObservabilityError(
                message="Configuration reload failed",
                component="advanced_manager",
                operation="reload_configuration",
                original_error=e
            )
    
    async def get_advanced_health_check(self) -> Dict[str, Any]:
        """Get advanced health check with trends and predictions."""
        basic_health = await super().health_check()
        
        # Add advanced metrics
        performance_summary = self.registry.get_performance_summary()
        health_summary = self.registry.get_health_summary()
        integration_status = self._integration_manager.get_integration_status()
        
        # Get system trends
        system_trends = self._get_system_trends()
        
        # Predict health issues
        health_predictions = self._predict_health_issues()
        
        return {
            **basic_health,
            'performance_summary': performance_summary,
            'health_summary': health_summary,
            'integration_status': integration_status,
            'system_trends': system_trends,
            'health_predictions': health_predictions,
            'config_version': len(self._config_manager._config_history)
        }
    
    def get_component_insights(self, component_name: str) -> Dict[str, Any]:
        """Get detailed insights for a specific component."""
        component_info = self.registry.get_component(component_name)
        if not component_info:
            return {}
        
        performance = self.registry.get_component_performance(component_name)
        health_history = self.registry.get_component_health_history(component_name)
        
        return {
            'component_info': {
                'name': component_info.name,
                'type': component_info.component_type.value,
                'status': component_info.status.value,
                'dependencies': component_info.dependencies,
                'startup_time': component_info.startup_time.isoformat() if component_info.startup_time else None
            },
            'performance_metrics': performance.__dict__ if performance else {},
            'health_history': {
                'uptime_percentage': health_history.uptime_percentage if health_history else 0,
                'mean_time_to_recovery': health_history.mean_time_to_recovery if health_history else 0,
                'failure_count': health_history.failure_count if health_history else 0,
                'recovery_count': health_history.recovery_count if health_history else 0
            } if health_history else {},
            'recent_health_checks': [
                {
                    'timestamp': check['timestamp'].isoformat(),
                    'status': check['status']
                }
                for check in (health_history.health_checks if health_history else [])
            ][-10:]  # Last 10 checks
        }
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add an event handler."""
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove an event handler."""
        if handler in self._event_handlers[event_type]:
            self._event_handlers[event_type].remove(handler)
    
    def emit_event(self, event_type: str, **kwargs) -> None:
        """Emit an event to all handlers."""
        for handler in self._event_handlers[event_type]:
            try:
                handler(event_type, **kwargs)
            except Exception as e:
                self._logger.error(f"Event handler failed for {event_type}: {e}")
    
    def get_configuration_manager(self) -> ConfigurationManager:
        """Get the configuration manager."""
        return self._config_manager
    
    def get_integration_manager(self) -> IntegrationManager:
        """Get the integration manager."""
        return self._integration_manager
    
    def enable_config_hot_reload(self, enabled: bool = True) -> None:
        """Enable or disable configuration hot-reload."""
        self._config_reload_enabled = enabled
        self._logger.info(f"Configuration hot-reload {'enabled' if enabled else 'disabled'}")
    
    # Private methods for advanced features
    
    async def _start_system_monitoring(self) -> None:
        """Start system-level monitoring."""
        async def system_monitor():
            while not self._shutdown_event.is_set():
                try:
                    # Collect system metrics
                    system_metrics = {
                        'timestamp': datetime.now(timezone.utc),
                        'cpu_percent': psutil.cpu_percent(interval=1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'disk_percent': psutil.disk_usage('/').percent,
                        'network_io': psutil.net_io_counters()._asdict(),
                        'process_count': len(psutil.pids())
                    }
                    
                    self._system_metrics_history.append(system_metrics)
                    
                    # Update component performance metrics
                    for component_info in self.registry.get_all_components():
                        if component_info.instance:
                            # Simulate component-specific metrics (would be real in production)
                            self.registry.update_component_performance(
                                component_info.name,
                                cpu_usage=system_metrics['cpu_percent'] / len(self.registry.get_all_components()),
                                memory_usage=system_metrics['memory_percent'] / len(self.registry.get_all_components())
                            )
                    
                    await asyncio.sleep(30)  # Monitor every 30 seconds
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"System monitoring error: {e}")
                    await asyncio.sleep(30)
        
        self._system_monitor_task = asyncio.create_task(system_monitor())
    
    async def _start_health_aggregation(self) -> None:
        """Start advanced health aggregation."""
        async def health_aggregator():
            while not self._shutdown_event.is_set():
                try:
                    # Perform health checks and record results
                    for component_info in self.registry.get_all_components():
                        if component_info.instance and component_info.status == ComponentStatus.RUNNING:
                            start_time = time.time()
                            health_result = await component_info.instance.health_check()
                            check_time = (time.time() - start_time) * 1000  # ms
                            
                            # Record in registry
                            self.registry.record_health_check(component_info.name, health_result)
                            
                            # Update performance metrics
                            self.registry.update_component_performance(
                                component_info.name,
                                response_time=check_time,
                                error_occurred=health_result.get('status') != 'healthy'
                            )
                            
                            # Store trend data
                            self._health_trends[component_info.name].append({
                                'timestamp': datetime.now(timezone.utc),
                                'status': health_result.get('status'),
                                'response_time': check_time
                            })
                    
                    await asyncio.sleep(self._health_check_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self._logger.error(f"Health aggregation error: {e}")
                    await asyncio.sleep(self._health_check_interval)
        
        self._health_aggregator_task = asyncio.create_task(health_aggregator())
    
    def _on_config_changed(self, old_config: ObservabilityConfig, new_config: ObservabilityConfig) -> None:
        """Handle configuration changes."""
        self._logger.info("Configuration changed - applying updates")
        
        # Update internal config reference
        self.config = new_config
        
        # Emit configuration change event
        self.emit_event('config_changed', old_config=old_config, new_config=new_config)
        
        # Note: In a full implementation, this would selectively restart
        # only the components that need to be restarted based on config changes
    
    def _on_registry_event(self, event_type: str, *args, **kwargs) -> None:
        """Handle registry events."""
        self._logger.debug(f"Registry event: {event_type}")
        self.emit_event(f"registry_{event_type}", *args, **kwargs)
    
    def _get_system_trends(self) -> Dict[str, Any]:
        """Get system performance trends."""
        if len(self._system_metrics_history) < 2:
            return {}
        
        recent_metrics = list(self._system_metrics_history)[-10:]  # Last 10 readings
        
        cpu_trend = [m['cpu_percent'] for m in recent_metrics]
        memory_trend = [m['memory_percent'] for m in recent_metrics]
        
        return {
            'cpu_trend': {
                'current': cpu_trend[-1] if cpu_trend else 0,
                'average': sum(cpu_trend) / len(cpu_trend) if cpu_trend else 0,
                'trend_direction': 'increasing' if len(cpu_trend) > 1 and cpu_trend[-1] > cpu_trend[0] else 'stable'
            },
            'memory_trend': {
                'current': memory_trend[-1] if memory_trend else 0,
                'average': sum(memory_trend) / len(memory_trend) if memory_trend else 0,
                'trend_direction': 'increasing' if len(memory_trend) > 1 and memory_trend[-1] > memory_trend[0] else 'stable'
            }
        }
    
    def _predict_health_issues(self) -> Dict[str, Any]:
        """Predict potential health issues based on trends."""
        predictions = {}
        
        # Analyze each component's health trends
        for component_name, trends in self._health_trends.items():
            if len(trends) < 5:
                continue
            
            recent_trends = list(trends)[-10:]  # Last 10 health checks
            
            # Calculate failure rate
            failures = sum(1 for t in recent_trends if t['status'] != 'healthy')
            failure_rate = failures / len(recent_trends)
            
            # Calculate response time trend
            response_times = [t['response_time'] for t in recent_trends]
            avg_response_time = sum(response_times) / len(response_times)
            
            # Simple prediction logic
            risk_level = 'low'
            if failure_rate > 0.3:
                risk_level = 'high'
            elif failure_rate > 0.1 or avg_response_time > 1000:  # > 1 second
                risk_level = 'medium'
            
            predictions[component_name] = {
                'risk_level': risk_level,
                'failure_rate': failure_rate,
                'avg_response_time_ms': avg_response_time,
                'recommendation': self._get_health_recommendation(risk_level, failure_rate, avg_response_time)
            }
        
        return predictions
    
    def _get_health_recommendation(self, risk_level: str, failure_rate: float, avg_response_time: float) -> str:
        """Get health recommendation based on metrics."""
        if risk_level == 'high':
            return "Immediate attention required - high failure rate detected"
        elif risk_level == 'medium':
            if failure_rate > 0.1:
                return "Monitor closely - increased failure rate"
            else:
                return "Monitor performance - slow response times detected"
        else:
            return "Component operating normally"


# Factory functions for advanced manager

def create_advanced_observability_manager(config: Optional[ObservabilityConfig] = None) -> AdvancedObservabilityManager:
    """Create an advanced observability manager."""
    if config is None:
        config = ObservabilityConfig()
    
    return AdvancedObservabilityManager(config)


async def initialize_advanced_observability(config: Optional[ObservabilityConfig] = None) -> AdvancedObservabilityManager:
    """Initialize and return a ready-to-use advanced observability manager."""
    manager = create_advanced_observability_manager(config)
    await manager.initialize()
    return manager


# Export advanced classes and functions
__all__ = [
    'PerformanceMetrics',
    'ComponentHealthHistory',
    'AdvancedComponentRegistry',
    'ConfigurationManager',
    'IntegrationManager',
    'AdvancedObservabilityManager',
    'create_advanced_observability_manager',
    'initialize_advanced_observability',
]
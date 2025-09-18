"""
System Diagnostics Manager - Advanced system health monitoring and diagnostics
"""
import asyncio
import psutil
import platform
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json

from ..core.base_manager import BaseManager

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ComponentType(Enum):
    SYSTEM = "system"
    SERVICE = "service"
    DATABASE = "database"
    NETWORK = "network"
    STORAGE = "storage"
    MEMORY = "memory"
    CPU = "cpu"

@dataclass
class HealthCheck:
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float
    details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, int]
    disk_io: Dict[str, int]
    process_count: int
    uptime: float
    load_average: Optional[List[float]] = None

@dataclass
class Alert:
    id: str
    severity: str
    component: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None

class SystemDiagnosticsManager(BaseManager):
    """
    Advanced system diagnostics and health monitoring manager.
    
    Features:
    - Real-time system health monitoring
    - Resource usage tracking and alerting
    - Component health checks
    - Performance metrics collection
    - Automated diagnostics and recommendations
    """
    
    def __init__(self, name: str = "system_diagnostics", config: Optional[Dict[str, Any]] = None):
        super().__init__(name, config)
        
        # Configuration
        self.health_check_interval = config.get("health_check_interval", 30) if config else 30
        self.metrics_retention_hours = config.get("metrics_retention_hours", 24) if config else 24
        self.alert_thresholds = config.get("alert_thresholds", {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0
        }) if config else {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time": 5.0
        }
        
        # State
        self.health_checks: List[HealthCheck] = []
        self.system_metrics: List[SystemMetrics] = []
        self.alerts: List[Alert] = []
        self.registered_components: Dict[str, Dict[str, Any]] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.last_health_check = datetime.now()
        
        # System info
        self.system_info = self._get_system_info()
        
    async def initialize(self) -> bool:
        """Initialize the system diagnostics manager"""
        try:
            self.logger.info("Initializing System Diagnostics Manager...")
            
            # Register core system components
            await self._register_core_components()
            
            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            # Perform initial health check
            await self.perform_health_check()
            
            self.logger.info("System Diagnostics Manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize System Diagnostics Manager: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the system diagnostics manager"""
        try:
            self.logger.info("Shutting down System Diagnostics Manager...")
            
            # Cancel monitoring task
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Clean up resources
            await self._cleanup_old_data()
            
            self.logger.info("System Diagnostics Manager shutdown successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to shutdown System Diagnostics Manager: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on the diagnostics manager"""
        try:
            # Check if monitoring is running
            if not self.monitoring_task or self.monitoring_task.done():
                return False
            
            # Check if recent health checks exist
            recent_checks = [
                hc for hc in self.health_checks 
                if hc.timestamp > datetime.now() - timedelta(minutes=5)
            ]
            
            return len(recent_checks) > 0
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def register_component(
        self, 
        component_name: str, 
        component_type: ComponentType,
        health_check_func: Optional[callable] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Register a component for health monitoring"""
        try:
            self.registered_components[component_name] = {
                "type": component_type,
                "health_check_func": health_check_func,
                "config": config or {},
                "registered_at": datetime.now(),
                "last_check": None,
                "status": HealthStatus.UNKNOWN
            }
            
            self.logger.info(f"Registered component: {component_name} ({component_type.value})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register component {component_name}: {e}")
            return False
    
    async def unregister_component(self, component_name: str) -> bool:
        """Unregister a component from health monitoring"""
        try:
            if component_name in self.registered_components:
                del self.registered_components[component_name]
                self.logger.info(f"Unregistered component: {component_name}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to unregister component {component_name}: {e}")
            return False
    
    async def perform_health_check(self) -> Dict[str, HealthCheck]:
        """Perform health checks on all registered components"""
        try:
            health_results = {}
            
            # Check system components
            system_health = await self._check_system_health()
            health_results.update(system_health)
            
            # Check registered components
            for component_name, component_info in self.registered_components.items():
                health_check = await self._check_component_health(component_name, component_info)
                health_results[component_name] = health_check
                
                # Update component status
                component_info["last_check"] = datetime.now()
                component_info["status"] = health_check.status
            
            # Store health checks
            self.health_checks.extend(health_results.values())
            self.last_health_check = datetime.now()
            
            # Check for alerts
            await self._process_health_alerts(health_results)
            
            return health_results
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {}
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network I/O
            network_io = psutil.net_io_counters()._asdict()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()._asdict()
            
            # Process count
            process_count = len(psutil.pids())
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            # Load average (Unix systems only)
            load_average = None
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_average = list(psutil.getloadavg())
            except (AttributeError, OSError):
                pass
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                disk_io=disk_io,
                process_count=process_count,
                uptime=uptime,
                load_average=load_average
            )
            
            # Store metrics
            self.system_metrics.append(metrics)
            
            # Check for metric-based alerts
            await self._process_metric_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_io={},
                disk_io={},
                process_count=0,
                uptime=0.0
            )
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        try:
            recent_checks = [
                hc for hc in self.health_checks 
                if hc.timestamp > datetime.now() - timedelta(minutes=10)
            ]
            
            if not recent_checks:
                return {
                    "overall_status": HealthStatus.UNKNOWN.value,
                    "components_checked": 0,
                    "healthy_components": 0,
                    "warning_components": 0,
                    "critical_components": 0,
                    "last_check": None
                }
            
            # Count statuses
            status_counts = {
                HealthStatus.HEALTHY: 0,
                HealthStatus.WARNING: 0,
                HealthStatus.CRITICAL: 0,
                HealthStatus.UNKNOWN: 0
            }
            
            for check in recent_checks:
                status_counts[check.status] += 1
            
            # Determine overall status
            overall_status = HealthStatus.HEALTHY
            if status_counts[HealthStatus.CRITICAL] > 0:
                overall_status = HealthStatus.CRITICAL
            elif status_counts[HealthStatus.WARNING] > 0:
                overall_status = HealthStatus.WARNING
            
            return {
                "overall_status": overall_status.value,
                "components_checked": len(recent_checks),
                "healthy_components": status_counts[HealthStatus.HEALTHY],
                "warning_components": status_counts[HealthStatus.WARNING],
                "critical_components": status_counts[HealthStatus.CRITICAL],
                "unknown_components": status_counts[HealthStatus.UNKNOWN],
                "last_check": self.last_health_check.isoformat(),
                "system_uptime": time.time() - psutil.boot_time(),
                "active_alerts": len([a for a in self.alerts if not a.resolved])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get health summary: {e}")
            return {"overall_status": HealthStatus.UNKNOWN.value}
    
    async def get_alerts(self, resolved: Optional[bool] = None) -> List[Alert]:
        """Get system alerts"""
        try:
            if resolved is None:
                return self.alerts.copy()
            
            return [alert for alert in self.alerts if alert.resolved == resolved]
            
        except Exception as e:
            self.logger.error(f"Failed to get alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            for alert in self.alerts:
                if alert.id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    self.logger.info(f"Resolved alert: {alert_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def get_performance_analysis(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance analysis for the specified time period"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.system_metrics 
                if m.timestamp > cutoff_time
            ]
            
            if not recent_metrics:
                return {"error": "No metrics available for the specified period"}
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_disk = sum(m.disk_percent for m in recent_metrics) / len(recent_metrics)
            
            # Find peaks
            max_cpu = max(m.cpu_percent for m in recent_metrics)
            max_memory = max(m.memory_percent for m in recent_metrics)
            max_disk = max(m.disk_percent for m in recent_metrics)
            
            # Calculate trends
            cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
            memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])
            
            return {
                "period_hours": hours,
                "metrics_count": len(recent_metrics),
                "averages": {
                    "cpu_percent": round(avg_cpu, 2),
                    "memory_percent": round(avg_memory, 2),
                    "disk_percent": round(avg_disk, 2)
                },
                "peaks": {
                    "cpu_percent": round(max_cpu, 2),
                    "memory_percent": round(max_memory, 2),
                    "disk_percent": round(max_disk, 2)
                },
                "trends": {
                    "cpu_trend": cpu_trend,
                    "memory_trend": memory_trend
                },
                "recommendations": self._generate_performance_recommendations(
                    avg_cpu, avg_memory, max_cpu, max_memory
                )
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance analysis: {e}")
            return {"error": str(e)}
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                "platform": platform.platform(),
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return {}
    
    async def _register_core_components(self) -> None:
        """Register core system components for monitoring"""
        # System components
        await self.register_component("system_cpu", ComponentType.CPU)
        await self.register_component("system_memory", ComponentType.MEMORY)
        await self.register_component("system_storage", ComponentType.STORAGE)
        await self.register_component("system_network", ComponentType.NETWORK)
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                # Collect system metrics
                await self.get_system_metrics()
                
                # Perform health checks
                if (datetime.now() - self.last_health_check).seconds >= self.health_check_interval:
                    await self.perform_health_check()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Wait for next iteration
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error    

    async def _check_system_health(self) -> Dict[str, HealthCheck]:
        """Check health of core system components"""
        health_checks = {}
        
        try:
            # CPU Health Check
            start_time = time.time()
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_response_time = (time.time() - start_time) * 1000
            
            cpu_status = HealthStatus.HEALTHY
            cpu_message = f"CPU usage: {cpu_percent}%"
            
            if cpu_percent > self.alert_thresholds["cpu_percent"]:
                cpu_status = HealthStatus.CRITICAL
                cpu_message = f"High CPU usage: {cpu_percent}%"
            elif cpu_percent > self.alert_thresholds["cpu_percent"] * 0.8:
                cpu_status = HealthStatus.WARNING
                cpu_message = f"Elevated CPU usage: {cpu_percent}%"
            
            health_checks["system_cpu"] = HealthCheck(
                component="system_cpu",
                component_type=ComponentType.CPU,
                status=cpu_status,
                message=cpu_message,
                timestamp=datetime.now(),
                response_time=cpu_response_time,
                metrics={"cpu_percent": cpu_percent}
            )
            
            # Memory Health Check
            start_time = time.time()
            memory = psutil.virtual_memory()
            memory_response_time = (time.time() - start_time) * 1000
            
            memory_status = HealthStatus.HEALTHY
            memory_message = f"Memory usage: {memory.percent}%"
            
            if memory.percent > self.alert_thresholds["memory_percent"]:
                memory_status = HealthStatus.CRITICAL
                memory_message = f"High memory usage: {memory.percent}%"
            elif memory.percent > self.alert_thresholds["memory_percent"] * 0.8:
                memory_status = HealthStatus.WARNING
                memory_message = f"Elevated memory usage: {memory.percent}%"
            
            health_checks["system_memory"] = HealthCheck(
                component="system_memory",
                component_type=ComponentType.MEMORY,
                status=memory_status,
                message=memory_message,
                timestamp=datetime.now(),
                response_time=memory_response_time,
                metrics={
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "memory_used": memory.used
                }
            )
            
            # Storage Health Check
            start_time = time.time()
            disk = psutil.disk_usage('/')
            disk_response_time = (time.time() - start_time) * 1000
            
            disk_status = HealthStatus.HEALTHY
            disk_message = f"Disk usage: {disk.percent}%"
            
            if disk.percent > self.alert_thresholds["disk_percent"]:
                disk_status = HealthStatus.CRITICAL
                disk_message = f"High disk usage: {disk.percent}%"
            elif disk.percent > self.alert_thresholds["disk_percent"] * 0.8:
                disk_status = HealthStatus.WARNING
                disk_message = f"Elevated disk usage: {disk.percent}%"
            
            health_checks["system_storage"] = HealthCheck(
                component="system_storage",
                component_type=ComponentType.STORAGE,
                status=disk_status,
                message=disk_message,
                timestamp=datetime.now(),
                response_time=disk_response_time,
                metrics={
                    "disk_percent": disk.percent,
                    "disk_free": disk.free,
                    "disk_used": disk.used
                }
            )
            
            # Network Health Check
            start_time = time.time()
            network_io = psutil.net_io_counters()
            network_response_time = (time.time() - start_time) * 1000
            
            network_status = HealthStatus.HEALTHY
            network_message = "Network connectivity OK"
            
            health_checks["system_network"] = HealthCheck(
                component="system_network",
                component_type=ComponentType.NETWORK,
                status=network_status,
                message=network_message,
                timestamp=datetime.now(),
                response_time=network_response_time,
                metrics={
                    "bytes_sent": network_io.bytes_sent,
                    "bytes_recv": network_io.bytes_recv,
                    "packets_sent": network_io.packets_sent,
                    "packets_recv": network_io.packets_recv
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
            
            # Add error health check
            health_checks["system_error"] = HealthCheck(
                component="system_error",
                component_type=ComponentType.SYSTEM,
                status=HealthStatus.CRITICAL,
                message=f"System health check failed: {str(e)}",
                timestamp=datetime.now(),
                response_time=0.0
            )
        
        return health_checks
    
    async def _check_component_health(self, component_name: str, component_info: Dict[str, Any]) -> HealthCheck:
        """Check health of a registered component"""
        try:
            start_time = time.time()
            
            # Use custom health check function if provided
            if component_info.get("health_check_func"):
                try:
                    result = await component_info["health_check_func"]()
                    response_time = (time.time() - start_time) * 1000
                    
                    if isinstance(result, dict):
                        return HealthCheck(
                            component=component_name,
                            component_type=component_info["type"],
                            status=HealthStatus(result.get("status", "healthy")),
                            message=result.get("message", "Component OK"),
                            timestamp=datetime.now(),
                            response_time=response_time,
                            details=result.get("details"),
                            metrics=result.get("metrics")
                        )
                    else:
                        status = HealthStatus.HEALTHY if result else HealthStatus.CRITICAL
                        return HealthCheck(
                            component=component_name,
                            component_type=component_info["type"],
                            status=status,
                            message="Component OK" if result else "Component failed",
                            timestamp=datetime.now(),
                            response_time=response_time
                        )
                        
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    return HealthCheck(
                        component=component_name,
                        component_type=component_info["type"],
                        status=HealthStatus.CRITICAL,
                        message=f"Health check failed: {str(e)}",
                        timestamp=datetime.now(),
                        response_time=response_time
                    )
            
            # Default health check (just verify component is registered)
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                component=component_name,
                component_type=component_info["type"],
                status=HealthStatus.HEALTHY,
                message="Component registered and monitored",
                timestamp=datetime.now(),
                response_time=response_time
            )
            
        except Exception as e:
            return HealthCheck(
                component=component_name,
                component_type=component_info.get("type", ComponentType.SYSTEM),
                status=HealthStatus.CRITICAL,
                message=f"Component health check error: {str(e)}",
                timestamp=datetime.now(),
                response_time=0.0
            )
    
    async def _process_health_alerts(self, health_results: Dict[str, HealthCheck]) -> None:
        """Process health check results and generate alerts"""
        try:
            for component_name, health_check in health_results.items():
                if health_check.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                    # Check if alert already exists
                    existing_alert = None
                    for alert in self.alerts:
                        if (alert.component == component_name and 
                            not alert.resolved and 
                            alert.severity == health_check.status.value):
                            existing_alert = alert
                            break
                    
                    if not existing_alert:
                        # Create new alert
                        alert = Alert(
                            id=f"{component_name}_{health_check.status.value}_{int(time.time())}",
                            severity=health_check.status.value,
                            component=component_name,
                            message=health_check.message,
                            timestamp=health_check.timestamp,
                            details={
                                "component_type": health_check.component_type.value,
                                "response_time": health_check.response_time,
                                "metrics": health_check.metrics
                            }
                        )
                        self.alerts.append(alert)
                        self.logger.warning(f"New alert: {alert.severity} - {alert.message}")
                
                elif health_check.status == HealthStatus.HEALTHY:
                    # Resolve existing alerts for this component
                    for alert in self.alerts:
                        if alert.component == component_name and not alert.resolved:
                            alert.resolved = True
                            alert.resolved_at = datetime.now()
                            self.logger.info(f"Auto-resolved alert: {alert.id}")
                            
        except Exception as e:
            self.logger.error(f"Error processing health alerts: {e}")
    
    async def _process_metric_alerts(self, metrics: SystemMetrics) -> None:
        """Process system metrics and generate alerts"""
        try:
            # CPU alert
            if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
                alert_id = f"cpu_high_{int(time.time())}"
                if not any(a.id.startswith("cpu_high") and not a.resolved for a in self.alerts):
                    alert = Alert(
                        id=alert_id,
                        severity="critical",
                        component="system_cpu",
                        message=f"High CPU usage: {metrics.cpu_percent}%",
                        timestamp=metrics.timestamp,
                        details={"cpu_percent": metrics.cpu_percent}
                    )
                    self.alerts.append(alert)
            
            # Memory alert
            if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
                alert_id = f"memory_high_{int(time.time())}"
                if not any(a.id.startswith("memory_high") and not a.resolved for a in self.alerts):
                    alert = Alert(
                        id=alert_id,
                        severity="critical",
                        component="system_memory",
                        message=f"High memory usage: {metrics.memory_percent}%",
                        timestamp=metrics.timestamp,
                        details={"memory_percent": metrics.memory_percent}
                    )
                    self.alerts.append(alert)
            
            # Disk alert
            if metrics.disk_percent > self.alert_thresholds["disk_percent"]:
                alert_id = f"disk_high_{int(time.time())}"
                if not any(a.id.startswith("disk_high") and not a.resolved for a in self.alerts):
                    alert = Alert(
                        id=alert_id,
                        severity="critical",
                        component="system_storage",
                        message=f"High disk usage: {metrics.disk_percent}%",
                        timestamp=metrics.timestamp,
                        details={"disk_percent": metrics.disk_percent}
                    )
                    self.alerts.append(alert)
                    
        except Exception as e:
            self.logger.error(f"Error processing metric alerts: {e}")
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old metrics and health checks"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.metrics_retention_hours)
            
            # Clean old metrics
            self.system_metrics = [
                m for m in self.system_metrics 
                if m.timestamp > cutoff_time
            ]
            
            # Clean old health checks
            self.health_checks = [
                hc for hc in self.health_checks 
                if hc.timestamp > cutoff_time
            ]
            
            # Clean old resolved alerts (keep for 7 days)
            alert_cutoff = datetime.now() - timedelta(days=7)
            self.alerts = [
                a for a in self.alerts 
                if not a.resolved or (a.resolved_at and a.resolved_at > alert_cutoff)
            ]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        diff_percent = ((second_avg - first_avg) / first_avg) * 100
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_performance_recommendations(
        self, 
        avg_cpu: float, 
        avg_memory: float, 
        max_cpu: float, 
        max_memory: float
    ) -> List[str]:
        """Generate performance recommendations based on metrics"""
        recommendations = []
        
        if avg_cpu > 70:
            recommendations.append("Consider optimizing CPU-intensive processes or scaling horizontally")
        
        if max_cpu > 95:
            recommendations.append("CPU spikes detected - investigate high-CPU processes")
        
        if avg_memory > 80:
            recommendations.append("High memory usage detected - consider increasing available memory")
        
        if max_memory > 95:
            recommendations.append("Memory spikes detected - check for memory leaks")
        
        if avg_cpu < 20 and avg_memory < 30:
            recommendations.append("System resources are underutilized - consider cost optimization")
        
        if not recommendations:
            recommendations.append("System performance is within normal parameters")
        
        return recommendations
    
    async def get_diagnostic_report(self) -> Dict[str, Any]:
        """Generate comprehensive diagnostic report"""
        try:
            health_summary = await self.get_health_summary()
            performance_analysis = await self.get_performance_analysis(hours=1)
            recent_alerts = await self.get_alerts(resolved=False)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "system_info": self.system_info,
                "health_summary": health_summary,
                "performance_analysis": performance_analysis,
                "active_alerts": [asdict(alert) for alert in recent_alerts],
                "registered_components": {
                    name: {
                        "type": info["type"].value,
                        "status": info["status"].value,
                        "last_check": info["last_check"].isoformat() if info["last_check"] else None
                    }
                    for name, info in self.registered_components.items()
                },
                "monitoring_status": {
                    "monitoring_active": self.monitoring_task and not self.monitoring_task.done(),
                    "last_health_check": self.last_health_check.isoformat(),
                    "metrics_count": len(self.system_metrics),
                    "health_checks_count": len(self.health_checks)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate diagnostic report: {e}")
            return {"error": str(e)}
    
    async def _initialize_impl(self) -> None:
        """Implementation of abstract method from BaseManager"""
        # Register core system components
        await self._register_core_components()
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Perform initial health check
        await self.perform_health_check()
        
        self.logger.info("System Diagnostics Manager initialized successfully")
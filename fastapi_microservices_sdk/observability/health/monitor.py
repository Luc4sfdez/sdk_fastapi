"""
Health Monitor for FastAPI Microservices SDK.

This module provides the core health monitoring functionality including
health status aggregation, dependency checking, and health reporting.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging

from .config import HealthConfig, HealthStatus, DependencyConfig
from .exceptions import HealthCheckError, HealthTimeoutError


@dataclass
class HealthCheckResult:
    """Health check result container."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'duration_ms': self.duration_ms,
            'details': self.details,
            'error': self.error
        }


@dataclass
class SystemInfo:
    """System information container."""
    hostname: str
    platform: str
    python_version: str
    cpu_count: int
    memory_total: int
    memory_available: int
    disk_usage: Dict[str, Any]
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'hostname': self.hostname,
            'platform': self.platform,
            'python_version': self.python_version,
            'cpu_count': self.cpu_count,
            'memory_total': self.memory_total,
            'memory_available': self.memory_available,
            'disk_usage': self.disk_usage,
            'uptime_seconds': self.uptime_seconds
        }


class HealthMonitor:
    """Comprehensive health monitoring system."""
    
    def __init__(self, config: HealthConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Health check functions registry
        self._health_checks: Dict[str, Callable] = {}
        self._dependency_checkers: Dict[str, Callable] = {}
        
        # Health status cache
        self._health_cache: Dict[str, HealthCheckResult] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
        # Overall health status
        self._overall_status = HealthStatus.UNKNOWN
        self._last_health_check = None
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._check_count = 0
        self._failure_count = 0
        self._total_check_time = 0.0
        
        # System info
        self._system_info = self._collect_system_info()
        self._start_time = time.time()
        
        # Initialize built-in health checks
        self._register_builtin_checks()
    
    def _collect_system_info(self) -> SystemInfo:
        """Collect system information."""
        import platform
        import psutil
        import sys
        import socket
        
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return SystemInfo(
                hostname=socket.gethostname(),
                platform=platform.platform(),
                python_version=sys.version,
                cpu_count=psutil.cpu_count(),
                memory_total=memory.total,
                memory_available=memory.available,
                disk_usage={
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                },
                uptime_seconds=time.time() - self._start_time
            )
        except Exception as e:
            self.logger.warning(f"Failed to collect system info: {e}")
            return SystemInfo(
                hostname="unknown",
                platform="unknown",
                python_version=sys.version,
                cpu_count=1,
                memory_total=0,
                memory_available=0,
                disk_usage={},
                uptime_seconds=time.time() - self._start_time
            )
    
    def _register_builtin_checks(self):
        """Register built-in health checks."""
        # Basic application health check
        self.register_health_check("application", self._check_application_health)
        
        # System resource checks
        if self.config.include_system_info:
            self.register_health_check("system_memory", self._check_memory_usage)
            self.register_health_check("system_disk", self._check_disk_usage)
    
    async def _check_application_health(self) -> HealthCheckResult:
        """Basic application health check."""
        start_time = time.time()
        
        try:
            # Basic application checks
            checks = {
                'service_running': True,
                'configuration_valid': self.config is not None,
                'dependencies_configured': len(self.config.dependencies) >= 0
            }
            
            all_healthy = all(checks.values())
            status = HealthStatus.HEALTHY if all_healthy else HealthStatus.UNHEALTHY
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="application",
                status=status,
                message="Application health check completed",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                details=checks
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="application",
                status=HealthStatus.UNHEALTHY,
                message=f"Application health check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_memory_usage(self) -> HealthCheckResult:
        """Check system memory usage."""
        start_time = time.time()
        
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            memory_percent = memory.percent
            status = HealthStatus.HEALTHY
            
            if memory_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif memory_percent > 80:
                status = HealthStatus.DEGRADED
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="system_memory",
                status=status,
                message=f"Memory usage: {memory_percent:.1f}%",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                details={
                    'memory_percent': memory_percent,
                    'memory_total': memory.total,
                    'memory_available': memory.available,
                    'memory_used': memory.used
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="system_memory",
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_disk_usage(self) -> HealthCheckResult:
        """Check system disk usage."""
        start_time = time.time()
        
        try:
            import psutil
            disk = psutil.disk_usage('/')
            
            disk_percent = (disk.used / disk.total) * 100
            status = HealthStatus.HEALTHY
            
            if disk_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif disk_percent > 85:
                status = HealthStatus.DEGRADED
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="system_disk",
                status=status,
                message=f"Disk usage: {disk_percent:.1f}%",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                details={
                    'disk_percent': disk_percent,
                    'disk_total': disk.total,
                    'disk_used': disk.used,
                    'disk_free': disk.free
                }
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="system_disk",
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    def register_health_check(self, name: str, check_function: Callable):
        """Register a health check function."""
        self._health_checks[name] = check_function
        self.logger.info(f"Registered health check: {name}")
    
    def unregister_health_check(self, name: str):
        """Unregister a health check function."""
        if name in self._health_checks:
            del self._health_checks[name]
            self.logger.info(f"Unregistered health check: {name}")
    
    def register_dependency_checker(self, name: str, checker_function: Callable):
        """Register a dependency checker function."""
        self._dependency_checkers[name] = checker_function
        self.logger.info(f"Registered dependency checker: {name}")
    
    async def check_health(self, check_name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """Perform health checks."""
        results = {}
        
        # Check cache if enabled
        if self.config.cache_health_results and check_name:
            cached_result = self._get_cached_result(check_name)
            if cached_result:
                return {check_name: cached_result}
        
        # Determine which checks to run
        checks_to_run = {}
        if check_name:
            if check_name in self._health_checks:
                checks_to_run[check_name] = self._health_checks[check_name]
        else:
            checks_to_run = self._health_checks.copy()
        
        # Run health checks
        for name, check_func in checks_to_run.items():
            try:
                # Apply timeout
                result = await asyncio.wait_for(
                    check_func(),
                    timeout=self.config.health_timeout
                )
                results[name] = result
                
                # Cache result
                if self.config.cache_health_results:
                    self._cache_result(name, result)
                
                # Update statistics
                self._check_count += 1
                self._total_check_time += result.duration_ms
                
                if result.status != HealthStatus.HEALTHY:
                    self._failure_count += 1
                
            except asyncio.TimeoutError:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check timed out after {self.config.health_timeout}s",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=self.config.health_timeout * 1000,
                    error="timeout"
                )
                results[name] = result
                self._failure_count += 1
                
            except Exception as e:
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=0.0,
                    error=str(e)
                )
                results[name] = result
                self._failure_count += 1
        
        return results
    
    async def check_dependencies(self) -> Dict[str, HealthCheckResult]:
        """Check dependency health."""
        results = {}
        
        for dependency in self.config.dependencies:
            if not dependency.enabled:
                continue
            
            try:
                # Check if we have a custom checker
                if dependency.name in self._dependency_checkers:
                    checker = self._dependency_checkers[dependency.name]
                    result = await asyncio.wait_for(
                        checker(dependency),
                        timeout=dependency.timeout_seconds
                    )
                else:
                    # Use built-in dependency checker
                    result = await self._check_dependency(dependency)
                
                results[dependency.name] = result
                
            except asyncio.TimeoutError:
                result = HealthCheckResult(
                    name=dependency.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Dependency check timed out after {dependency.timeout_seconds}s",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=dependency.timeout_seconds * 1000,
                    error="timeout"
                )
                results[dependency.name] = result
                
            except Exception as e:
                result = HealthCheckResult(
                    name=dependency.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Dependency check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=0.0,
                    error=str(e)
                )
                results[dependency.name] = result
        
        return results
    
    async def _check_dependency(self, dependency: DependencyConfig) -> HealthCheckResult:
        """Built-in dependency health check."""
        start_time = time.time()
        
        try:
            if dependency.type.value == "database":
                return await self._check_database_dependency(dependency, start_time)
            elif dependency.type.value == "cache":
                return await self._check_cache_dependency(dependency, start_time)
            elif dependency.type.value == "external_api":
                return await self._check_api_dependency(dependency, start_time)
            else:
                # Generic network connectivity check
                return await self._check_network_dependency(dependency, start_time)
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Dependency check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_database_dependency(self, dependency: DependencyConfig, start_time: float) -> HealthCheckResult:
        """Check database dependency."""
        try:
            import asyncpg  # PostgreSQL example
            
            conn = await asyncpg.connect(
                host=dependency.host,
                port=dependency.port,
                database=dependency.database_name,
                timeout=dependency.timeout_seconds
            )
            
            # Simple query to test connection
            await conn.fetchval("SELECT 1")
            await conn.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                details={
                    'host': dependency.host,
                    'port': dependency.port,
                    'database': dependency.database_name
                }
            )
            
        except ImportError:
            # Fallback to basic network check
            return await self._check_network_dependency(dependency, start_time)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_cache_dependency(self, dependency: DependencyConfig, start_time: float) -> HealthCheckResult:
        """Check cache dependency (Redis example)."""
        try:
            import aioredis
            
            redis = aioredis.from_url(
                f"redis://{dependency.host}:{dependency.port}",
                socket_timeout=dependency.timeout_seconds
            )
            
            # Simple ping to test connection
            await redis.ping()
            await redis.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.HEALTHY,
                message="Cache connection successful",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                details={
                    'host': dependency.host,
                    'port': dependency.port
                }
            )
            
        except ImportError:
            # Fallback to basic network check
            return await self._check_network_dependency(dependency, start_time)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Cache connection failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_api_dependency(self, dependency: DependencyConfig, start_time: float) -> HealthCheckResult:
        """Check external API dependency."""
        try:
            import aiohttp
            
            timeout = aiohttp.ClientTimeout(total=dependency.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(dependency.url) as response:
                    status_ok = 200 <= response.status < 400
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if status_ok:
                        return HealthCheckResult(
                            name=dependency.name,
                            status=HealthStatus.HEALTHY,
                            message=f"API responded with status {response.status}",
                            timestamp=datetime.now(timezone.utc),
                            duration_ms=duration_ms,
                            details={
                                'url': dependency.url,
                                'status_code': response.status
                            }
                        )
                    else:
                        return HealthCheckResult(
                            name=dependency.name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"API responded with status {response.status}",
                            timestamp=datetime.now(timezone.utc),
                            duration_ms=duration_ms,
                            details={
                                'url': dependency.url,
                                'status_code': response.status
                            }
                        )
                        
        except ImportError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNKNOWN,
                message="aiohttp not available for API health check",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error="missing_dependency"
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def _check_network_dependency(self, dependency: DependencyConfig, start_time: float) -> HealthCheckResult:
        """Basic network connectivity check."""
        try:
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(dependency.timeout_seconds)
            
            result = sock.connect_ex((dependency.host, dependency.port))
            sock.close()
            
            duration_ms = (time.time() - start_time) * 1000
            
            if result == 0:
                return HealthCheckResult(
                    name=dependency.name,
                    status=HealthStatus.HEALTHY,
                    message="Network connection successful",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    details={
                        'host': dependency.host,
                        'port': dependency.port
                    }
                )
            else:
                return HealthCheckResult(
                    name=dependency.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Network connection failed (code: {result})",
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=duration_ms,
                    error=f"connection_error_{result}"
                )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=dependency.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Network check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                error=str(e)
            )
    
    async def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status."""
        # Run all health checks
        health_results = await self.check_health()
        dependency_results = await self.check_dependencies()
        
        # Combine results
        all_results = {**health_results, **dependency_results}
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(all_results)
        
        # Update system info
        if self.config.include_system_info:
            self._system_info = self._collect_system_info()
        
        health_report = {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'service': {
                'name': self.config.service_name,
                'version': self.config.service_version,
                'environment': self.config.environment
            },
            'checks': {name: result.to_dict() for name, result in all_results.items()},
            'statistics': self.get_health_statistics()
        }
        
        if self.config.include_system_info:
            health_report['system'] = self._system_info.to_dict()
        
        # Store overall status
        self._overall_status = overall_status
        self._last_health_check = datetime.now(timezone.utc)
        
        return health_report
    
    def _calculate_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Calculate overall health status from individual results."""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        # If any check is unhealthy, overall is unhealthy (unless configured otherwise)
        if HealthStatus.UNHEALTHY in statuses:
            if self.config.fail_on_dependency_failure:
                return HealthStatus.UNHEALTHY
            else:
                # Check if it's just dependencies that are failing
                dependency_names = [dep.name for dep in self.config.dependencies]
                core_results = {name: result for name, result in results.items() 
                              if name not in dependency_names}
                
                if core_results:
                    core_statuses = [result.status for result in core_results.values()]
                    if HealthStatus.UNHEALTHY in core_statuses:
                        return HealthStatus.UNHEALTHY
        
        # Calculate health percentage
        healthy_count = sum(1 for status in statuses if status == HealthStatus.HEALTHY)
        total_count = len(statuses)
        health_percentage = healthy_count / total_count
        
        if health_percentage >= self.config.degraded_threshold:
            return HealthStatus.HEALTHY
        elif health_percentage > 0.5:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def _get_cached_result(self, check_name: str) -> Optional[HealthCheckResult]:
        """Get cached health check result."""
        if check_name not in self._health_cache:
            return None
        
        cache_time = self._cache_timestamps.get(check_name, 0)
        if time.time() - cache_time > self.config.cache_ttl_seconds:
            # Cache expired
            del self._health_cache[check_name]
            del self._cache_timestamps[check_name]
            return None
        
        return self._health_cache[check_name]
    
    def _cache_result(self, check_name: str, result: HealthCheckResult):
        """Cache health check result."""
        self._health_cache[check_name] = result
        self._cache_timestamps[check_name] = time.time()
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """Get health monitoring statistics."""
        avg_check_time = self._total_check_time / max(1, self._check_count)
        failure_rate = self._failure_count / max(1, self._check_count)
        
        return {
            'total_checks': self._check_count,
            'total_failures': self._failure_count,
            'failure_rate': failure_rate,
            'average_check_time_ms': avg_check_time,
            'registered_checks': len(self._health_checks),
            'registered_dependencies': len(self.config.dependencies),
            'cache_size': len(self._health_cache),
            'uptime_seconds': time.time() - self._start_time,
            'last_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'overall_status': self._overall_status.value
        }
    
    async def start_monitoring(self):
        """Start background health monitoring."""
        if not self.config.enabled:
            return
        
        async def monitoring_loop():
            while not self._shutdown_event.is_set():
                try:
                    await self.get_overall_health()
                    await asyncio.sleep(self.config.health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in health monitoring loop: {e}")
                    await asyncio.sleep(self.config.health_check_interval)
        
        self._monitoring_task = asyncio.create_task(monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop background health monitoring."""
        self._shutdown_event.set()
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health monitoring stopped")


def create_health_monitor(config: HealthConfig) -> HealthMonitor:
    """Create health monitor instance."""
    return HealthMonitor(config)


# Export main classes and functions
__all__ = [
    'HealthCheckResult',
    'SystemInfo',
    'HealthMonitor',
    'create_health_monitor',
]
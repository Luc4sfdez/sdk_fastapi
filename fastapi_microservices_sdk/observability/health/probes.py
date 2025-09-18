"""
Kubernetes Probes for FastAPI Microservices SDK.

This module provides Kubernetes readiness, liveness, and startup probes
with comprehensive health checking and integration capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import logging

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from .config import HealthConfig, ProbeConfig, ProbeType, HealthStatus
from .monitor import HealthMonitor, HealthCheckResult
from .exceptions import ProbeConfigurationError


class ProbeStatus(str, Enum):
    """Probe status enumeration."""
    READY = "ready"
    NOT_READY = "not_ready"
    ALIVE = "alive"
    NOT_ALIVE = "not_alive"
    STARTING = "starting"
    STARTED = "started"


@dataclass
class ProbeResult:
    """Probe check result."""
    probe_type: ProbeType
    status: ProbeStatus
    message: str
    timestamp: datetime
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'probe_type': self.probe_type.value,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


class KubernetesProbe:
    """Base Kubernetes probe implementation."""
    
    def __init__(
        self,
        probe_type: ProbeType,
        config: ProbeConfig,
        health_monitor: HealthMonitor
    ):
        self.probe_type = probe_type
        self.config = config
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(__name__)
        
        # Probe state
        self._probe_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
        # Probe status
        self._current_status = ProbeStatus.NOT_READY
        self._last_check_time = None
        
    async def check(self) -> ProbeResult:
        """Perform probe check."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Increment probe count
            self._probe_count += 1
            
            # Perform the actual health check
            result = await self._perform_check()
            
            # Update statistics
            if result.status in [ProbeStatus.READY, ProbeStatus.ALIVE, ProbeStatus.STARTED]:
                self._success_count += 1
                self._consecutive_successes += 1
                self._consecutive_failures = 0
            else:
                self._failure_count += 1
                self._consecutive_failures += 1
                self._consecutive_successes = 0
            
            # Update current status based on thresholds
            self._update_status(result.status)
            
            # Update last check time
            self._last_check_time = start_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Probe check failed: {e}")
            
            # Create failure result
            result = ProbeResult(
                probe_type=self.probe_type,
                status=ProbeStatus.NOT_READY,
                message=f"Probe check failed: {e}",
                timestamp=start_time,
                details={'error': str(e)}
            )
            
            # Update failure statistics
            self._failure_count += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._update_status(result.status)
            
            return result
    
    async def _perform_check(self) -> ProbeResult:
        """Perform the actual probe check - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _perform_check")
    
    def _update_status(self, check_status: ProbeStatus):
        """Update probe status based on success/failure thresholds."""
        # Apply success threshold
        if (check_status in [ProbeStatus.READY, ProbeStatus.ALIVE, ProbeStatus.STARTED] and
            self._consecutive_successes >= self.config.success_threshold):
            self._current_status = check_status
        
        # Apply failure threshold
        elif (check_status in [ProbeStatus.NOT_READY, ProbeStatus.NOT_ALIVE] and
              self._consecutive_failures >= self.config.failure_threshold):
            self._current_status = check_status
    
    def get_status(self) -> ProbeStatus:
        """Get current probe status."""
        return self._current_status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get probe statistics."""
        success_rate = self._success_count / max(1, self._probe_count)
        
        return {
            'probe_type': self.probe_type.value,
            'total_checks': self._probe_count,
            'success_count': self._success_count,
            'failure_count': self._failure_count,
            'success_rate': success_rate,
            'consecutive_failures': self._consecutive_failures,
            'consecutive_successes': self._consecutive_successes,
            'current_status': self._current_status.value,
            'last_check_time': self._last_check_time.isoformat() if self._last_check_time else None
        }


class ReadinessProbe(KubernetesProbe):
    """Kubernetes readiness probe implementation."""
    
    def __init__(self, config: ProbeConfig, health_monitor: HealthMonitor):
        super().__init__(ProbeType.READINESS, config, health_monitor)
    
    async def _perform_check(self) -> ProbeResult:
        """Perform readiness check."""
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Get overall health status
            health_report = await self.health_monitor.get_overall_health()
            overall_status = HealthStatus(health_report['status'])
            
            # Readiness criteria:
            # - Service is healthy or degraded (not unhealthy)
            # - All critical dependencies are available
            
            if overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
                return ProbeResult(
                    probe_type=self.probe_type,
                    status=ProbeStatus.READY,
                    message="Service is ready to receive traffic",
                    timestamp=timestamp,
                    details={
                        'overall_health': overall_status.value,
                        'checks_passed': len([c for c in health_report['checks'].values() 
                                            if c['status'] == 'healthy']),
                        'total_checks': len(health_report['checks'])
                    }
                )
            else:
                return ProbeResult(
                    probe_type=self.probe_type,
                    status=ProbeStatus.NOT_READY,
                    message=f"Service not ready - health status: {overall_status.value}",
                    timestamp=timestamp,
                    details={
                        'overall_health': overall_status.value,
                        'failed_checks': [name for name, check in health_report['checks'].items()
                                        if check['status'] != 'healthy']
                    }
                )
                
        except Exception as e:
            return ProbeResult(
                probe_type=self.probe_type,
                status=ProbeStatus.NOT_READY,
                message=f"Readiness check failed: {e}",
                timestamp=timestamp,
                details={'error': str(e)}
            )


class LivenessProbe(KubernetesProbe):
    """Kubernetes liveness probe implementation."""
    
    def __init__(self, config: ProbeConfig, health_monitor: HealthMonitor):
        super().__init__(ProbeType.LIVENESS, config, health_monitor)
    
    async def _perform_check(self) -> ProbeResult:
        """Perform liveness check."""
        timestamp = datetime.now(timezone.utc)
        
        try:
            # Liveness criteria:
            # - Application is running (basic health checks pass)
            # - No deadlocks or critical failures
            # - Core functionality is working
            
            # Check core application health
            core_health = await self.health_monitor.check_health("application")
            
            if core_health and "application" in core_health:
                app_result = core_health["application"]
                
                if app_result.status == HealthStatus.HEALTHY:
                    return ProbeResult(
                        probe_type=self.probe_type,
                        status=ProbeStatus.ALIVE,
                        message="Service is alive and functioning",
                        timestamp=timestamp,
                        details={
                            'application_health': app_result.status.value,
                            'check_duration_ms': app_result.duration_ms
                        }
                    )
                else:
                    return ProbeResult(
                        probe_type=self.probe_type,
                        status=ProbeStatus.NOT_ALIVE,
                        message=f"Application health check failed: {app_result.message}",
                        timestamp=timestamp,
                        details={
                            'application_health': app_result.status.value,
                            'error': app_result.error
                        }
                    )
            else:
                return ProbeResult(
                    probe_type=self.probe_type,
                    status=ProbeStatus.NOT_ALIVE,
                    message="No application health check available",
                    timestamp=timestamp,
                    details={'error': 'no_health_check'}
                )
                
        except Exception as e:
            return ProbeResult(
                probe_type=self.probe_type,
                status=ProbeStatus.NOT_ALIVE,
                message=f"Liveness check failed: {e}",
                timestamp=timestamp,
                details={'error': str(e)}
            )


class StartupProbe(KubernetesProbe):
    """Kubernetes startup probe implementation."""
    
    def __init__(self, config: ProbeConfig, health_monitor: HealthMonitor):
        super().__init__(ProbeType.STARTUP, config, health_monitor)
        self._startup_completed = False
    
    async def _perform_check(self) -> ProbeResult:
        """Perform startup check."""
        timestamp = datetime.now(timezone.utc)
        
        try:
            # If startup already completed, always return success
            if self._startup_completed:
                return ProbeResult(
                    probe_type=self.probe_type,
                    status=ProbeStatus.STARTED,
                    message="Service startup completed",
                    timestamp=timestamp,
                    details={'startup_completed': True}
                )
            
            # Startup criteria:
            # - Basic application health check passes
            # - Critical dependencies are initialized
            # - Service is ready to start accepting traffic
            
            # Check application health
            app_health = await self.health_monitor.check_health("application")
            
            if app_health and "application" in app_health:
                app_result = app_health["application"]
                
                if app_result.status == HealthStatus.HEALTHY:
                    # Mark startup as completed
                    self._startup_completed = True
                    
                    return ProbeResult(
                        probe_type=self.probe_type,
                        status=ProbeStatus.STARTED,
                        message="Service startup completed successfully",
                        timestamp=timestamp,
                        details={
                            'startup_completed': True,
                            'application_health': app_result.status.value,
                            'startup_time_seconds': self.health_monitor.get_health_statistics()['uptime_seconds']
                        }
                    )
                else:
                    return ProbeResult(
                        probe_type=self.probe_type,
                        status=ProbeStatus.STARTING,
                        message=f"Service still starting up: {app_result.message}",
                        timestamp=timestamp,
                        details={
                            'startup_completed': False,
                            'application_health': app_result.status.value
                        }
                    )
            else:
                return ProbeResult(
                    probe_type=self.probe_type,
                    status=ProbeStatus.STARTING,
                    message="Service startup in progress",
                    timestamp=timestamp,
                    details={'startup_completed': False}
                )
                
        except Exception as e:
            return ProbeResult(
                probe_type=self.probe_type,
                status=ProbeStatus.STARTING,
                message=f"Startup check failed: {e}",
                timestamp=timestamp,
                details={'error': str(e), 'startup_completed': False}
            )


class ProbeManager:
    """Kubernetes probe manager."""
    
    def __init__(self, config: HealthConfig, health_monitor: HealthMonitor):
        self.config = config
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(__name__)
        
        # Initialize probes
        self.probes: Dict[ProbeType, KubernetesProbe] = {}
        
        if config.readiness_probe.enabled:
            self.probes[ProbeType.READINESS] = ReadinessProbe(
                config.readiness_probe, health_monitor
            )
        
        if config.liveness_probe.enabled:
            self.probes[ProbeType.LIVENESS] = LivenessProbe(
                config.liveness_probe, health_monitor
            )
        
        if config.startup_probe.enabled:
            self.probes[ProbeType.STARTUP] = StartupProbe(
                config.startup_probe, health_monitor
            )
    
    async def check_probe(self, probe_type: ProbeType) -> ProbeResult:
        """Check specific probe."""
        if probe_type not in self.probes:
            raise ProbeConfigurationError(
                f"Probe {probe_type.value} is not configured or enabled",
                probe_type=probe_type.value
            )
        
        return await self.probes[probe_type].check()
    
    async def check_all_probes(self) -> Dict[ProbeType, ProbeResult]:
        """Check all configured probes."""
        results = {}
        
        for probe_type, probe in self.probes.items():
            try:
                result = await probe.check()
                results[probe_type] = result
            except Exception as e:
                self.logger.error(f"Failed to check {probe_type.value} probe: {e}")
                results[probe_type] = ProbeResult(
                    probe_type=probe_type,
                    status=ProbeStatus.NOT_READY,
                    message=f"Probe check failed: {e}",
                    timestamp=datetime.now(timezone.utc),
                    details={'error': str(e)}
                )
        
        return results
    
    def get_probe_status(self, probe_type: ProbeType) -> Optional[ProbeStatus]:
        """Get current status of specific probe."""
        if probe_type in self.probes:
            return self.probes[probe_type].get_status()
        return None
    
    def get_all_probe_statuses(self) -> Dict[ProbeType, ProbeStatus]:
        """Get current status of all probes."""
        return {
            probe_type: probe.get_status()
            for probe_type, probe in self.probes.items()
        }
    
    def get_probe_statistics(self) -> Dict[str, Any]:
        """Get statistics for all probes."""
        return {
            probe_type.value: probe.get_statistics()
            for probe_type, probe in self.probes.items()
        }


def create_kubernetes_probes(
    config: HealthConfig,
    health_monitor: HealthMonitor
) -> ProbeManager:
    """Create Kubernetes probe manager."""
    return ProbeManager(config, health_monitor)


# Export main classes and functions
__all__ = [
    'ProbeStatus',
    'ProbeResult',
    'KubernetesProbe',
    'ReadinessProbe',
    'LivenessProbe',
    'StartupProbe',
    'ProbeManager',
    'create_kubernetes_probes',
]
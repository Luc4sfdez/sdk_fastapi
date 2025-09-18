"""
Security Monitoring Integration for FastAPI Microservices SDK.

This module provides comprehensive security monitoring capabilities including:
- Integrated security logging across all components
- Correlation ID tracking for request tracing
- Security metrics collection and performance monitoring
- Real-time security event aggregation
- Integration with external monitoring systems

Features:
- Unified security event logging
- Performance metrics collection
- Request correlation tracking
- Security dashboard integration
- SIEM system integration
- Real-time alerting
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import json
from abc import ABC, abstractmethod

from .logging import SecurityLogger, SecurityEvent, SecurityEventType, SecurityEventSeverity
from .exceptions import SecurityConfigurationError


class MetricType(Enum):
    """Types of security metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MonitoringLevel(Enum):
    """Security monitoring levels."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"
    DEBUG = "debug"


@dataclass
class SecurityMetric:
    """Security metric data structure."""
    name: str
    metric_type: MetricType
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""


@dataclass
class PerformanceMetric:
    """Performance metric for security operations."""
    operation: str
    duration_ms: float
    success: bool
    component: str
    correlation_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAlert:
    """Security alert for monitoring systems."""
    alert_id: str
    severity: SecurityEventSeverity
    title: str
    description: str
    component: str
    correlation_id: Optional[str] = None
    affected_resources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """Collects and aggregates security metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[SecurityMetric]] = defaultdict(list)
        self.performance_metrics: List[PerformanceMetric] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def record_metric(self, metric: SecurityMetric):
        """Record a security metric."""
        async with self._lock:
            self.metrics[metric.name].append(metric)
            
            # Update aggregated metrics
            if metric.metric_type == MetricType.COUNTER:
                self.counters[metric.name] += int(metric.value)
            elif metric.metric_type == MetricType.GAUGE:
                self.gauges[metric.name] = float(metric.value)
            elif metric.metric_type == MetricType.HISTOGRAM:
                self.histograms[metric.name].append(float(metric.value))
            elif metric.metric_type == MetricType.TIMER:
                self.timers[metric.name].append(float(metric.value))
    
    async def record_performance(self, performance: PerformanceMetric):
        """Record a performance metric."""
        async with self._lock:
            self.performance_metrics.append(performance)
            
            # Also record as timer metric
            timer_metric = SecurityMetric(
                name=f"performance.{performance.component}.{performance.operation}",
                metric_type=MetricType.TIMER,
                value=performance.duration_ms,
                labels={
                    "component": performance.component,
                    "operation": performance.operation,
                    "success": str(performance.success)
                }
            )
            await self.record_metric(timer_metric)
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Get gauge value."""
        return self.gauges.get(name)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        values = self.histograms.get(name, [])
        if not values:
            return {}
        
        sorted_values = sorted(values)
        count = len(values)
        
        return {
            "count": count,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / count,
            "p50": sorted_values[int(count * 0.5)],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)]
        }
    
    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get timer statistics."""
        return self.get_histogram_stats(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {name: self.get_histogram_stats(name) for name in self.histograms},
            "timers": {name: self.get_timer_stats(name) for name in self.timers},
            "total_metrics": sum(len(metrics) for metrics in self.metrics.values()),
            "performance_metrics_count": len(self.performance_metrics)
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics.clear()
        self.performance_metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()


class CorrelationTracker:
    """Tracks correlation IDs across security layers."""
    
    def __init__(self):
        self.active_requests: Dict[str, Dict[str, Any]] = {}
        self.completed_requests: deque = deque(maxlen=10000)  # Keep last 10k requests
        self._lock = asyncio.Lock()
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID."""
        return f"sec_{uuid.uuid4().hex[:12]}"
    
    async def start_request(self, correlation_id: str, metadata: Dict[str, Any] = None):
        """Start tracking a request."""
        async with self._lock:
            self.active_requests[correlation_id] = {
                "start_time": datetime.now(timezone.utc),
                "metadata": metadata or {},
                "events": [],
                "components": set()
            }
    
    async def add_event(self, correlation_id: str, component: str, event: str, metadata: Dict[str, Any] = None):
        """Add an event to a tracked request."""
        async with self._lock:
            if correlation_id in self.active_requests:
                self.active_requests[correlation_id]["events"].append({
                    "timestamp": datetime.now(timezone.utc),
                    "component": component,
                    "event": event,
                    "metadata": metadata or {}
                })
                self.active_requests[correlation_id]["components"].add(component)
    
    async def complete_request(self, correlation_id: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Complete tracking a request."""
        async with self._lock:
            if correlation_id in self.active_requests:
                request_data = self.active_requests.pop(correlation_id)
                request_data["end_time"] = datetime.now(timezone.utc)
                request_data["duration"] = (request_data["end_time"] - request_data["start_time"]).total_seconds()
                request_data["success"] = success
                request_data["completion_metadata"] = metadata or {}
                
                self.completed_requests.append(request_data)
    
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active requests."""
        return self.active_requests.copy()
    
    def get_request_trace(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get trace for a specific request."""
        # Check active requests first
        if correlation_id in self.active_requests:
            return self.active_requests[correlation_id]
        
        # Check completed requests
        for request in self.completed_requests:
            if request.get("correlation_id") == correlation_id:
                return request
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get correlation tracking statistics."""
        return {
            "active_requests": len(self.active_requests),
            "completed_requests": len(self.completed_requests),
            "total_tracked": len(self.active_requests) + len(self.completed_requests)
        }


class SecurityMonitor:
    """
    Comprehensive security monitoring system.
    
    Integrates security logging across all components with correlation ID tracking,
    metrics collection, and performance monitoring.
    """
    
    def __init__(self, monitoring_level: MonitoringLevel = MonitoringLevel.DETAILED):
        self.monitoring_level = monitoring_level
        self.logger = SecurityLogger("SecurityMonitor")
        self.metrics_collector = MetricsCollector()
        self.correlation_tracker = CorrelationTracker()
        self.alerts: List[SecurityAlert] = []
        self.event_handlers: List[Callable[[SecurityEvent], None]] = []
        self.metric_handlers: List[Callable[[SecurityMetric], None]] = []
        self.alert_handlers: List[Callable[[SecurityAlert], None]] = []
        self._lock = asyncio.Lock()
        
        # Component-specific loggers
        self.component_loggers: Dict[str, SecurityLogger] = {}
        
        # Performance tracking
        self.performance_thresholds: Dict[str, float] = {
            "mtls_validation": 100.0,  # ms
            "jwt_validation": 50.0,    # ms
            "rbac_check": 25.0,        # ms
            "abac_evaluation": 100.0,  # ms
            "threat_analysis": 200.0   # ms
        }
    
    def get_component_logger(self, component: str) -> SecurityLogger:
        """Get or create a component-specific logger."""
        if component not in self.component_loggers:
            self.component_loggers[component] = SecurityLogger(f"Security.{component}")
        return self.component_loggers[component]
    
    def add_event_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add a security event handler."""
        self.event_handlers.append(handler)
    
    def add_metric_handler(self, handler: Callable[[SecurityMetric], None]):
        """Add a metric handler."""
        self.metric_handlers.append(handler)
    
    def add_alert_handler(self, handler: Callable[[SecurityAlert], None]):
        """Add an alert handler."""
        self.alert_handlers.append(handler)
    
    async def start_request_monitoring(self, correlation_id: Optional[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Start monitoring a security request."""
        if not correlation_id:
            correlation_id = self.correlation_tracker.generate_correlation_id()
        
        await self.correlation_tracker.start_request(correlation_id, metadata)
        
        # Record metric
        await self.record_metric(SecurityMetric(
            name="security.requests.started",
            metric_type=MetricType.COUNTER,
            value=1,
            labels={"correlation_id": correlation_id}
        ))
        
        return correlation_id
    
    async def log_security_event(self, event: SecurityEvent, correlation_id: Optional[str] = None):
        """Log a security event with correlation tracking."""
        # Add correlation ID to event details
        if correlation_id:
            event.details["correlation_id"] = correlation_id
            await self.correlation_tracker.add_event(
                correlation_id, 
                event.details.get("component", "unknown"),
                event.event_type,
                event.details
            )
        
        # Log the event
        await self.logger.log_security_event(event)
        
        # Notify handlers
        for handler in self.event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")
        
        # Check if event should trigger an alert
        await self._check_alert_conditions(event, correlation_id)
    
    async def record_metric(self, metric: SecurityMetric):
        """Record a security metric."""
        await self.metrics_collector.record_metric(metric)
        
        # Notify handlers
        for handler in self.metric_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(metric)
                else:
                    handler(metric)
            except Exception as e:
                self.logger.error(f"Error in metric handler: {e}")
    
    async def record_performance(self, component: str, operation: str, duration_ms: float, 
                               success: bool = True, correlation_id: Optional[str] = None,
                               metadata: Dict[str, Any] = None):
        """Record performance metrics for security operations."""
        performance = PerformanceMetric(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            component=component,
            correlation_id=correlation_id or "unknown",
            metadata=metadata or {}
        )
        
        await self.metrics_collector.record_performance(performance)
        
        # Check performance thresholds
        threshold_key = f"{component}_{operation}"
        if threshold_key in self.performance_thresholds:
            if duration_ms > self.performance_thresholds[threshold_key]:
                await self._create_performance_alert(component, operation, duration_ms, correlation_id)
        
        # Add to correlation trace
        if correlation_id:
            await self.correlation_tracker.add_event(
                correlation_id,
                component,
                f"performance_{operation}",
                {"duration_ms": duration_ms, "success": success}
            )
    
    async def complete_request_monitoring(self, correlation_id: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Complete monitoring a security request."""
        await self.correlation_tracker.complete_request(correlation_id, success, metadata)
        
        # Record completion metric
        await self.record_metric(SecurityMetric(
            name="security.requests.completed",
            metric_type=MetricType.COUNTER,
            value=1,
            labels={
                "correlation_id": correlation_id,
                "success": str(success)
            }
        ))
    
    async def create_alert(self, severity: SecurityEventSeverity, title: str, description: str,
                          component: str, correlation_id: Optional[str] = None,
                          affected_resources: List[str] = None, metadata: Dict[str, Any] = None) -> SecurityAlert:
        """Create a security alert."""
        alert = SecurityAlert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            severity=severity,
            title=title,
            description=description,
            component=component,
            correlation_id=correlation_id,
            affected_resources=affected_resources or [],
            metadata=metadata or {}
        )
        
        async with self._lock:
            self.alerts.append(alert)
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")
        
        # Log alert creation
        await self.log_security_event(SecurityEvent(
            event_type="alert_created",
            severity=severity,
            component=component,
            details={
                "alert_id": alert.alert_id,
                "title": title,
                "description": description,
                "correlation_id": correlation_id
            }
        ), correlation_id)
        
        return alert
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str = ""):
        """Resolve a security alert."""
        async with self._lock:
            for alert in self.alerts:
                if alert.alert_id == alert_id and not alert.resolved:
                    alert.resolved = True
                    alert.resolved_at = datetime.now(timezone.utc)
                    alert.metadata["resolved_by"] = resolved_by
                    if resolution_notes:
                        alert.metadata["resolution_notes"] = resolution_notes
                    
                    # Log resolution
                    await self.log_security_event(SecurityEvent(
                        event_type="alert_resolved",
                        severity=SecurityEventSeverity.INFO,
                        component=alert.component,
                        details={
                            "alert_id": alert_id,
                            "resolved_by": resolved_by,
                            "resolution_notes": resolution_notes
                        }
                    ), alert.correlation_id)
                    
                    return True
        return False
    
    async def _check_alert_conditions(self, event: SecurityEvent, correlation_id: Optional[str]):
        """Check if event should trigger an alert."""
        # High severity events automatically create alerts
        if event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
            await self.create_alert(
                severity=event.severity,
                title=f"Security Event: {event.event_type}",
                description=f"High severity security event detected: {event.event_type}",
                component=event.component,
                correlation_id=correlation_id,
                metadata=event.details
            )
    
    async def _create_performance_alert(self, component: str, operation: str, duration_ms: float, correlation_id: Optional[str]):
        """Create performance alert for slow operations."""
        threshold = self.performance_thresholds.get(f"{component}_{operation}", 0)
        await self.create_alert(
            severity=SecurityEventSeverity.MEDIUM,
            title=f"Performance Alert: {component}.{operation}",
            description=f"Operation {operation} in {component} took {duration_ms:.2f}ms (threshold: {threshold}ms)",
            component=component,
            correlation_id=correlation_id,
            metadata={
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold
            }
        )
    
    def get_active_alerts(self) -> List[SecurityAlert]:
        """Get all active (unresolved) alerts."""
        return [alert for alert in self.alerts if not alert.resolved]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        metrics = self.metrics_collector.get_all_metrics()
        correlation_stats = self.correlation_tracker.get_statistics()
        
        return {
            "metrics": metrics,
            "correlation_tracking": correlation_stats,
            "alerts": {
                "total": len(self.alerts),
                "active": len(self.get_active_alerts()),
                "resolved": len([a for a in self.alerts if a.resolved])
            },
            "monitoring_level": self.monitoring_level.value,
            "components_monitored": len(self.component_loggers)
        }
    
    def get_request_trace(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get complete trace for a request."""
        return self.correlation_tracker.get_request_trace(correlation_id)
    
    def set_performance_threshold(self, component: str, operation: str, threshold_ms: float):
        """Set performance threshold for an operation."""
        key = f"{component}_{operation}"
        self.performance_thresholds[key] = threshold_ms


# Context manager for performance monitoring
class PerformanceMonitor:
    """Context manager for monitoring operation performance."""
    
    def __init__(self, monitor: SecurityMonitor, component: str, operation: str, 
                 correlation_id: Optional[str] = None, metadata: Dict[str, Any] = None):
        self.monitor = monitor
        self.component = component
        self.operation = operation
        self.correlation_id = correlation_id
        self.metadata = metadata or {}
        self.start_time = None
        self.success = True
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            
            await self.monitor.record_performance(
                component=self.component,
                operation=self.operation,
                duration_ms=duration_ms,
                success=self.success,
                correlation_id=self.correlation_id,
                metadata=self.metadata
            )
    
    def mark_failure(self):
        """Mark the operation as failed."""
        self.success = False


# Integration helpers
def create_security_monitor(monitoring_level: MonitoringLevel = MonitoringLevel.DETAILED) -> SecurityMonitor:
    """Create a configured security monitor."""
    return SecurityMonitor(monitoring_level)


def setup_component_monitoring(monitor: SecurityMonitor, component_name: str) -> SecurityLogger:
    """Setup monitoring for a specific security component."""
    logger = monitor.get_component_logger(component_name)
    
    # Add default event handler that forwards to monitor
    async def forward_to_monitor(event: SecurityEvent):
        await monitor.log_security_event(event)
    
    # Note: In a real implementation, you'd integrate this with the component's logging
    return logger


# Export main classes and functions
__all__ = [
    "SecurityMonitor",
    "MetricsCollector",
    "CorrelationTracker",
    "PerformanceMonitor",
    "SecurityMetric",
    "PerformanceMetric",
    "SecurityAlert",
    "MetricType",
    "MonitoringLevel",
    "create_security_monitor",
    "setup_component_monitoring"
]
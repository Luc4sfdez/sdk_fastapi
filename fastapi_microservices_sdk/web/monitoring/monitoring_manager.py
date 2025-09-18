"""
Monitoring and metrics management for the web dashboard.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

from ..core.base_manager import BaseManager
from ...observability.dashboards.metrics_collector import MetricsCollector, SystemMetricsCollector
from ..services.types import ServiceInfo, ServiceStatus, HealthStatus


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TimeRange:
    """Time range for metrics queries."""
    start: datetime
    end: datetime


@dataclass
class MetricsData:
    """Metrics data structure."""
    service_id: str
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    request_count: int
    response_time: float
    error_rate: float
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    timestamp: datetime
    total_services: int
    running_services: int
    total_cpu_usage: float
    total_memory_usage: float
    total_requests: int
    average_response_time: float


@dataclass
class Alert:
    """Alert information."""
    id: str
    service_id: Optional[str]
    severity: AlertSeverity
    title: str
    message: str
    created_at: datetime
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration."""
    id: str
    name: str
    service_id: Optional[str]
    metric_name: str
    threshold: float
    comparison: str  # >, <, >=, <=, ==
    severity: AlertSeverity
    enabled: bool = True
    description: Optional[str] = None
    evaluation_interval: int = 60  # seconds
    for_duration: int = 300  # seconds - how long condition must be true
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DashboardData:
    """Dashboard data structure."""
    dashboard_id: str
    title: str
    widgets: List[Dict[str, Any]]
    last_updated: datetime


class MonitoringManager(BaseManager):
    """
    Monitoring and metrics management for the web dashboard.
    
    Handles:
    - Metrics collection and aggregation with MetricsCollector integration
    - Alert management and notifications
    - Dashboard data preparation
    - Real-time monitoring and service-specific metrics
    """
    
    def __init__(self, name: str = "monitoring", config: Optional[Dict[str, Any]] = None):
        """Initialize the monitoring manager."""
        super().__init__(name, config)
        
        # Core components
        self._metrics_collector: Optional[MetricsCollector] = None
        self._system_metrics_collector: Optional[SystemMetricsCollector] = None
        
        # Data storage
        self._alerts: Dict[str, Alert] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._dashboards: Dict[str, DashboardData] = {}
        self._service_collectors: Dict[str, Dict[str, Callable]] = {}
        
        # Alert evaluation
        self._alert_evaluation_task: Optional[asyncio.Task] = None
        self._alert_states: Dict[str, Dict[str, Any]] = {}  # Rule ID -> state info
        
        # Configuration
        self._metrics_retention_hours = self.get_config("metrics_retention_hours", 24)
        self._alert_evaluation_interval = self.get_config("alert_evaluation_interval", 30)
        self._notification_handlers: List[Callable] = []
    
    async def _initialize_impl(self) -> None:
        """Initialize the monitoring manager."""
        # Initialize metrics collector
        self._metrics_collector = MetricsCollector(
            retention_hours=self._metrics_retention_hours
        )
        await self._metrics_collector.initialize()
        
        # Initialize system metrics collector
        self._system_metrics_collector = SystemMetricsCollector(self._metrics_collector)
        
        # Setup default dashboards
        await self._setup_default_dashboards()
        
        # Start alert evaluation task
        self._alert_evaluation_task = asyncio.create_task(self._alert_evaluation_loop())
        
        self.logger.info("Monitoring manager initialized with metrics collection")
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the monitoring manager."""
        # Stop alert evaluation
        if self._alert_evaluation_task:
            self._alert_evaluation_task.cancel()
            try:
                await self._alert_evaluation_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown metrics collector
        if self._metrics_collector:
            await self._metrics_collector.shutdown()
        
        self.logger.info("Monitoring manager shutdown complete")
    
    # Service Metrics Management
    
    async def register_service_metrics(self, service_id: str, service_info: ServiceInfo) -> None:
        """
        Register metrics collectors for a service.
        
        Args:
            service_id: Service identifier
            service_info: Service information
        """
        if not self._metrics_collector:
            return
        
        # Register basic service metrics
        collectors = {}
        
        # CPU usage for service
        collectors[f"service_{service_id}_cpu_percent"] = lambda: self._get_service_cpu(service_id)
        
        # Memory usage for service
        collectors[f"service_{service_id}_memory_mb"] = lambda: self._get_service_memory(service_id)
        
        # Request count (if HTTP service)
        if service_info.template_type in ["api_gateway", "auth_service", "data_service"]:
            collectors[f"service_{service_id}_request_count"] = lambda: self._get_service_requests(service_id)
            collectors[f"service_{service_id}_response_time_ms"] = lambda: self._get_service_response_time(service_id)
            collectors[f"service_{service_id}_error_rate"] = lambda: self._get_service_error_rate(service_id)
        
        # Register collectors
        for metric_name, collector_func in collectors.items():
            self._metrics_collector.register_metric_collector(
                metric_name=metric_name,
                collector_func=collector_func,
                interval_seconds=30,
                labels={
                    "service_id": service_id,
                    "service_name": service_info.name,
                    "template_type": service_info.template_type
                }
            )
        
        self._service_collectors[service_id] = collectors
        self.logger.info(f"Registered metrics collectors for service: {service_id}")
    
    async def unregister_service_metrics(self, service_id: str) -> None:
        """
        Unregister metrics collectors for a service.
        
        Args:
            service_id: Service identifier
        """
        if service_id in self._service_collectors:
            # Note: MetricsCollector doesn't have unregister method in current implementation
            # In a full implementation, we would add this functionality
            del self._service_collectors[service_id]
            self.logger.info(f"Unregistered metrics collectors for service: {service_id}")
    
    async def get_service_metrics(self, service_id: str, time_range: TimeRange) -> List[MetricsData]:
        """
        Get metrics for a specific service.
        
        Args:
            service_id: Service identifier
            time_range: Time range for metrics
            
        Returns:
            List of metrics data
        """
        return await self._safe_execute(
            "get_service_metrics",
            self._get_service_metrics_impl,
            service_id,
            time_range
        ) or []
    
    async def get_system_metrics(self, time_range: TimeRange) -> List[SystemMetrics]:
        """
        Get system-wide metrics.
        
        Args:
            time_range: Time range for metrics
            
        Returns:
            List of system metrics
        """
        return await self._safe_execute(
            "get_system_metrics",
            self._get_system_metrics_impl,
            time_range
        ) or []
    
    async def get_aggregated_metrics(
        self, 
        metric_names: List[str], 
        time_range: TimeRange,
        aggregation: str = "avg"
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for multiple metrics.
        
        Args:
            metric_names: List of metric names
            time_range: Time range for metrics
            aggregation: Aggregation function (avg, sum, min, max)
            
        Returns:
            Aggregated metrics data
        """
        if not self._metrics_collector:
            return {}
        
        return self._metrics_collector.get_multiple_metrics(
            metric_names=metric_names,
            start_time=time_range.start,
            end_time=time_range.end,
            aggregation=aggregation
        )
    
    # Alert Management
    
    async def create_alert_rule(self, rule: AlertRule) -> str:
        """
        Create a new alert rule.
        
        Args:
            rule: Alert rule configuration
            
        Returns:
            Alert rule ID
        """
        result = await self._safe_execute(
            "create_alert_rule",
            self._create_alert_rule_impl,
            rule
        )
        return result or ""
    
    async def update_alert_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing alert rule.
        
        Args:
            rule_id: Alert rule ID
            updates: Fields to update
            
        Returns:
            True if updated successfully
        """
        if rule_id not in self._alert_rules:
            return False
        
        rule = self._alert_rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        self.logger.info(f"Updated alert rule: {rule_id}")
        return True
    
    async def delete_alert_rule(self, rule_id: str) -> bool:
        """
        Delete an alert rule.
        
        Args:
            rule_id: Alert rule ID
            
        Returns:
            True if deleted successfully
        """
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            if rule_id in self._alert_states:
                del self._alert_states[rule_id]
            self.logger.info(f"Deleted alert rule: {rule_id}")
            return True
        return False
    
    async def get_alert_rules(self, service_id: Optional[str] = None) -> List[AlertRule]:
        """
        Get alert rules, optionally filtered by service.
        
        Args:
            service_id: Optional service filter
            
        Returns:
            List of alert rules
        """
        rules = list(self._alert_rules.values())
        if service_id:
            rules = [r for r in rules if r.service_id == service_id]
        return rules
    
    async def get_alerts(self, service_id: Optional[str] = None, resolved: Optional[bool] = None) -> List[Alert]:
        """
        Get alerts, optionally filtered by service and resolution status.
        
        Args:
            service_id: Optional service filter
            resolved: Optional resolution status filter
            
        Returns:
            List of alerts
        """
        return await self._safe_execute(
            "get_alerts",
            self._get_alerts_impl,
            service_id,
            resolved
        ) or []
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            acknowledged_by: User who acknowledged the alert
            
        Returns:
            True if acknowledged successfully
        """
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if resolved successfully
        """
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            self.logger.info(f"Alert resolved: {alert_id}")
            return True
        return False
    
    # Dashboard Management
    
    async def get_dashboard_data(self, dashboard_id: str) -> Optional[DashboardData]:
        """
        Get dashboard data.
        
        Args:
            dashboard_id: Dashboard identifier
            
        Returns:
            Dashboard data or None if not found
        """
        return await self._safe_execute(
            "get_dashboard_data",
            self._get_dashboard_data_impl,
            dashboard_id
        )
    
    async def create_dashboard(self, dashboard: DashboardData) -> str:
        """
        Create a new dashboard.
        
        Args:
            dashboard: Dashboard configuration
            
        Returns:
            Dashboard ID
        """
        self._dashboards[dashboard.dashboard_id] = dashboard
        self.logger.info(f"Created dashboard: {dashboard.dashboard_id}")
        return dashboard.dashboard_id
    
    async def update_dashboard(self, dashboard_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            updates: Updates to apply
            
        Returns:
            True if updated successfully
        """
        if dashboard_id in self._dashboards:
            dashboard = self._dashboards[dashboard_id]
            for key, value in updates.items():
                if hasattr(dashboard, key):
                    setattr(dashboard, key, value)
            dashboard.last_updated = datetime.utcnow()
            return True
        return False
    
    # Notification Management
    
    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add a notification handler for alerts.
        
        Args:
            handler: Function to handle alert notifications
        """
        self._notification_handlers.append(handler)
        self.logger.info("Added notification handler")
    
    async def send_notification(self, alert: Alert) -> None:
        """
        Send notifications for an alert.
        
        Args:
            alert: Alert to send notifications for
        """
        for handler in self._notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Error in notification handler: {e}")
    
    # Implementation methods
    
    async def _get_service_metrics_impl(self, service_id: str, time_range: TimeRange) -> List[MetricsData]:
        """Implementation for getting service metrics."""
        if not self._metrics_collector:
            return []
        
        # Get service-specific metrics
        metric_names = [
            f"service_{service_id}_cpu_percent",
            f"service_{service_id}_memory_mb",
            f"service_{service_id}_request_count",
            f"service_{service_id}_response_time_ms",
            f"service_{service_id}_error_rate"
        ]
        
        metrics_data = []
        
        # Get time series data for each metric
        for metric_name in metric_names:
            series_data = self._metrics_collector.get_metric_series(
                metric_name=metric_name,
                start_time=time_range.start,
                end_time=time_range.end
            )
            
            # Convert to MetricsData format
            for point in series_data:
                timestamp = datetime.fromisoformat(point["timestamp"].replace('Z', '+00:00'))
                
                # Find or create MetricsData for this timestamp
                existing_data = next(
                    (md for md in metrics_data if md.timestamp == timestamp),
                    None
                )
                
                if not existing_data:
                    existing_data = MetricsData(
                        service_id=service_id,
                        timestamp=timestamp,
                        cpu_usage=0.0,
                        memory_usage=0.0,
                        request_count=0,
                        response_time=0.0,
                        error_rate=0.0,
                        custom_metrics={}
                    )
                    metrics_data.append(existing_data)
                
                # Update the appropriate field
                if "cpu_percent" in metric_name:
                    existing_data.cpu_usage = point["value"]
                elif "memory_mb" in metric_name:
                    existing_data.memory_usage = point["value"]
                elif "request_count" in metric_name:
                    existing_data.request_count = int(point["value"])
                elif "response_time_ms" in metric_name:
                    existing_data.response_time = point["value"]
                elif "error_rate" in metric_name:
                    existing_data.error_rate = point["value"]
        
        return sorted(metrics_data, key=lambda x: x.timestamp)
    
    async def _get_system_metrics_impl(self, time_range: TimeRange) -> List[SystemMetrics]:
        """Implementation for getting system metrics."""
        if not self._metrics_collector:
            return []
        
        # Get system metrics
        system_metric_names = [
            "system_cpu_usage_percent",
            "system_memory_usage_percent",
            "system_disk_usage_percent",
            "system_network_bytes_sent",
            "system_network_bytes_received"
        ]
        
        system_metrics = []
        
        # Get aggregated system data
        for metric_name in system_metric_names:
            series_data = self._metrics_collector.get_metric_series(
                metric_name=metric_name,
                start_time=time_range.start,
                end_time=time_range.end
            )
            
            for point in series_data:
                timestamp = datetime.fromisoformat(point["timestamp"].replace('Z', '+00:00'))
                
                # Find or create SystemMetrics for this timestamp
                existing_metrics = next(
                    (sm for sm in system_metrics if sm.timestamp == timestamp),
                    None
                )
                
                if not existing_metrics:
                    existing_metrics = SystemMetrics(
                        timestamp=timestamp,
                        total_services=len(self._service_collectors),
                        running_services=len(self._service_collectors),  # Simplified
                        total_cpu_usage=0.0,
                        total_memory_usage=0.0,
                        total_requests=0,
                        average_response_time=0.0
                    )
                    system_metrics.append(existing_metrics)
                
                # Update the appropriate field
                if "cpu_usage" in metric_name:
                    existing_metrics.total_cpu_usage = point["value"]
                elif "memory_usage" in metric_name:
                    existing_metrics.total_memory_usage = point["value"]
        
        return sorted(system_metrics, key=lambda x: x.timestamp)
    
    async def _get_alerts_impl(self, service_id: Optional[str] = None, resolved: Optional[bool] = None) -> List[Alert]:
        """Implementation for getting alerts."""
        alerts = list(self._alerts.values())
        
        if service_id:
            alerts = [a for a in alerts if a.service_id == service_id]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    async def _create_alert_rule_impl(self, rule: AlertRule) -> str:
        """Implementation for creating alert rule."""
        if not rule.id:
            rule.id = str(uuid.uuid4())
        
        self._alert_rules[rule.id] = rule
        self._alert_states[rule.id] = {
            "last_evaluation": None,
            "condition_start_time": None,
            "firing": False
        }
        
        self.logger.info(f"Created alert rule: {rule.name} ({rule.id})")
        return rule.id
    
    async def _get_dashboard_data_impl(self, dashboard_id: str) -> Optional[DashboardData]:
        """Implementation for getting dashboard data."""
        if dashboard_id in self._dashboards:
            dashboard = self._dashboards[dashboard_id]
            
            # Update dashboard with latest data
            await self._update_dashboard_widgets(dashboard)
            
            return dashboard
        return None
    
    async def _setup_default_dashboards(self) -> None:
        """Setup default dashboards."""
        # System overview dashboard
        system_dashboard = DashboardData(
            dashboard_id="system_overview",
            title="System Overview",
            widgets=[
                {
                    "id": "system_cpu",
                    "type": "gauge",
                    "title": "System CPU Usage",
                    "metric": "system_cpu_usage_percent",
                    "unit": "%"
                },
                {
                    "id": "system_memory",
                    "type": "gauge", 
                    "title": "System Memory Usage",
                    "metric": "system_memory_usage_percent",
                    "unit": "%"
                },
                {
                    "id": "services_status",
                    "type": "stat",
                    "title": "Services Status",
                    "metrics": ["total_services", "running_services"]
                }
            ],
            last_updated=datetime.utcnow()
        )
        
        self._dashboards["system_overview"] = system_dashboard
        self.logger.info("Setup default dashboards")
    
    async def _update_dashboard_widgets(self, dashboard: DashboardData) -> None:
        """Update dashboard widgets with latest data."""
        if not self._metrics_collector:
            return
        
        for widget in dashboard.widgets:
            if "metric" in widget:
                # Single metric widget
                latest_value = self._metrics_collector.get_metric_value(
                    widget["metric"], "last"
                )
                widget["current_value"] = latest_value
            elif "metrics" in widget:
                # Multi-metric widget
                widget["values"] = {}
                for metric in widget["metrics"]:
                    value = self._metrics_collector.get_metric_value(metric, "last")
                    widget["values"][metric] = value
        
        dashboard.last_updated = datetime.utcnow()
    
    async def _alert_evaluation_loop(self) -> None:
        """Background task for evaluating alert rules."""
        while True:
            try:
                await self._evaluate_alert_rules()
                await asyncio.sleep(self._alert_evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(self._alert_evaluation_interval)
    
    async def _evaluate_alert_rules(self) -> None:
        """Evaluate all alert rules."""
        if not self._metrics_collector:
            return
        
        current_time = datetime.utcnow()
        
        for rule_id, rule in self._alert_rules.items():
            if not rule.enabled:
                continue
            
            try:
                await self._evaluate_single_rule(rule, current_time)
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule_id}: {e}")
    
    async def _evaluate_single_rule(self, rule: AlertRule, current_time: datetime) -> None:
        """Evaluate a single alert rule."""
        if not self._metrics_collector:
            return
        
        # Get current metric value
        metric_value = self._metrics_collector.get_metric_value(rule.metric_name, "last")
        
        if metric_value is None:
            return
        
        # Evaluate condition
        condition_met = self._evaluate_condition(metric_value, rule.threshold, rule.comparison)
        
        rule_state = self._alert_states[rule.id]
        
        if condition_met:
            if rule_state["condition_start_time"] is None:
                rule_state["condition_start_time"] = current_time
            
            # Check if condition has been true for required duration
            duration = (current_time - rule_state["condition_start_time"]).total_seconds()
            
            if duration >= rule.for_duration and not rule_state["firing"]:
                # Fire alert
                await self._fire_alert(rule, metric_value, current_time)
                rule_state["firing"] = True
        else:
            # Condition not met, reset state
            rule_state["condition_start_time"] = None
            if rule_state["firing"]:
                # Resolve any existing alerts for this rule
                await self._resolve_rule_alerts(rule.id)
                rule_state["firing"] = False
        
        rule_state["last_evaluation"] = current_time
    
    def _evaluate_condition(self, value: float, threshold: float, comparison: str) -> bool:
        """Evaluate alert condition."""
        if comparison == ">":
            return value > threshold
        elif comparison == ">=":
            return value >= threshold
        elif comparison == "<":
            return value < threshold
        elif comparison == "<=":
            return value <= threshold
        elif comparison == "==":
            return value == threshold
        elif comparison == "!=":
            return value != threshold
        else:
            return False
    
    async def _fire_alert(self, rule: AlertRule, metric_value: float, timestamp: datetime) -> None:
        """Fire an alert for a rule."""
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            id=alert_id,
            service_id=rule.service_id,
            severity=rule.severity,
            title=f"Alert: {rule.name}",
            message=f"Metric {rule.metric_name} is {metric_value} (threshold: {rule.comparison} {rule.threshold})",
            created_at=timestamp,
            metadata={
                "rule_id": rule.id,
                "metric_name": rule.metric_name,
                "metric_value": metric_value,
                "threshold": rule.threshold,
                "comparison": rule.comparison
            }
        )
        
        self._alerts[alert_id] = alert
        
        # Send notifications
        await self.send_notification(alert)
        
        self.logger.warning(f"Alert fired: {rule.name} - {alert.message}")
    
    async def _resolve_rule_alerts(self, rule_id: str) -> None:
        """Resolve all alerts for a specific rule."""
        for alert in self._alerts.values():
            if (not alert.resolved and 
                alert.metadata.get("rule_id") == rule_id):
                alert.resolved = True
                alert.resolved_at = datetime.utcnow()
                self.logger.info(f"Auto-resolved alert: {alert.id}")
    
    # API Methods for Dashboard Endpoints
    
    async def query_metrics(
        self,
        service_ids: Optional[List[str]] = None,
        metric_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation: str = "raw",
        interval: str = "1m",
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Query metrics data with filtering and aggregation.
        
        Args:
            service_ids: List of service IDs to query
            metric_names: List of metric names to include
            start_time: Query start time
            end_time: Query end time
            aggregation: Aggregation type (raw, avg, sum, min, max)
            interval: Aggregation interval
            filters: Additional filters
            
        Returns:
            Nested dict: {service_id: {metric_name: [data_points]}}
        """
        if not self._metrics_collector:
            return {}
        
        # Default time range if not provided
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        result = {}
        
        # Get all service IDs if not specified
        if not service_ids:
            service_ids = list(self._service_collectors.keys())
        
        for service_id in service_ids:
            service_metrics = {}
            
            # Get metric names for this service if not specified
            if not metric_names:
                service_metric_names = [
                    name for name in self._service_collectors.get(service_id, {}).keys()
                ]
            else:
                # Filter metric names for this service
                service_metric_names = [
                    f"service_{service_id}_{name}" if not name.startswith(f"service_{service_id}_") else name
                    for name in metric_names
                ]
            
            for metric_name in service_metric_names:
                try:
                    # Get metric data from collector
                    series_data = self._metrics_collector.get_metric_series(
                        metric_name=metric_name,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    # Apply aggregation if needed
                    if aggregation != "raw" and series_data:
                        series_data = self._apply_aggregation(series_data, aggregation, interval)
                    
                    # Apply filters if provided
                    if filters:
                        series_data = self._apply_filters(series_data, filters)
                    
                    # Clean metric name for response
                    clean_name = metric_name.replace(f"service_{service_id}_", "")
                    service_metrics[clean_name] = series_data
                    
                except Exception as e:
                    self.logger.error(f"Error querying metric {metric_name}: {e}")
                    continue
            
            if service_metrics:
                result[service_id] = service_metrics
        
        return result
    
    async def get_available_services(self) -> List[str]:
        """Get list of services with metrics."""
        return await self._safe_execute(
            "get_available_services",
            self._get_available_services_impl
        ) or []
    
    async def _get_available_services_impl(self) -> List[str]:
        """Implementation for getting available services."""
        return list(self._service_collectors.keys())
    
    async def get_available_metrics(self, service_id: Optional[str] = None) -> List[str]:
        """
        Get list of available metric names.
        
        Args:
            service_id: Optional service filter
            
        Returns:
            List of metric names
        """
        return await self._safe_execute(
            "get_available_metrics",
            self._get_available_metrics_impl,
            service_id
        ) or []
    
    async def _get_available_metrics_impl(self, service_id: Optional[str] = None) -> List[str]:
        """Implementation for getting available metrics."""
        if not self._metrics_collector:
            return []
        
        if service_id and service_id in self._service_collectors:
            # Return metrics for specific service
            return [
                name.replace(f"service_{service_id}_", "")
                for name in self._service_collectors[service_id].keys()
            ]
        else:
            # Return all available metrics
            all_metrics = set()
            for service_id, collectors in self._service_collectors.items():
                for metric_name in collectors.keys():
                    clean_name = metric_name.replace(f"service_{service_id}_", "")
                    all_metrics.add(clean_name)
            return sorted(list(all_metrics))
    
    async def create_alert_rule(
        self,
        name: str,
        description: Optional[str] = None,
        service_id: Optional[str] = None,
        metric_name: str = "",
        condition: str = "",
        threshold: float = 0.0,
        severity: str = "medium",
        enabled: bool = True,
        notification_channels: Optional[List[str]] = None,
        evaluation_interval: int = 60,
        for_duration: int = 300
    ) -> Dict[str, Any]:
        """
        Create a new alert rule.
        
        Args:
            name: Rule name
            description: Rule description
            service_id: Target service ID
            metric_name: Metric to monitor
            condition: Alert condition
            threshold: Alert threshold
            severity: Alert severity
            enabled: Whether rule is enabled
            notification_channels: Notification channels
            evaluation_interval: Evaluation interval in seconds
            for_duration: Duration condition must be true
            
        Returns:
            Created alert rule data
        """
        # Parse condition to extract comparison operator
        comparison = ">"
        if condition:
            for op in [">=", "<=", "!=", "==", ">", "<"]:
                if op in condition:
                    comparison = op
                    break
        
        rule = AlertRule(
            id=str(uuid.uuid4()),
            name=name,
            service_id=service_id,
            metric_name=metric_name,
            threshold=threshold,
            comparison=comparison,
            severity=AlertSeverity(severity),
            enabled=enabled,
            description=description,
            evaluation_interval=evaluation_interval,
            for_duration=for_duration
        )
        
        rule_id = await self._create_alert_rule_impl(rule)
        
        return {
            "id": rule_id,
            "name": rule.name,
            "description": rule.description,
            "service_id": rule.service_id,
            "metric_name": rule.metric_name,
            "condition": condition,
            "threshold": rule.threshold,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "notification_channels": notification_channels or [],
            "evaluation_interval": rule.evaluation_interval,
            "for_duration": rule.for_duration,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
            "last_evaluation": None
        }
    
    async def get_alert_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get specific alert rule."""
        if rule_id not in self._alert_rules:
            return None
        
        rule = self._alert_rules[rule_id]
        state = self._alert_states.get(rule_id, {})
        
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "service_id": rule.service_id,
            "metric_name": rule.metric_name,
            "condition": f"{rule.comparison} {rule.threshold}",
            "threshold": rule.threshold,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "notification_channels": [],
            "evaluation_interval": rule.evaluation_interval,
            "for_duration": rule.for_duration,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
            "last_evaluation": state.get("last_evaluation")
        }
    
    async def update_alert_rule(
        self,
        rule_id: str,
        name: str,
        description: Optional[str] = None,
        service_id: Optional[str] = None,
        metric_name: str = "",
        condition: str = "",
        threshold: float = 0.0,
        severity: str = "medium",
        enabled: bool = True,
        notification_channels: Optional[List[str]] = None,
        evaluation_interval: int = 60,
        for_duration: int = 300
    ) -> Optional[Dict[str, Any]]:
        """Update an existing alert rule."""
        if rule_id not in self._alert_rules:
            return None
        
        # Parse condition to extract comparison operator
        comparison = ">"
        if condition:
            for op in [">=", "<=", "!=", "==", ">", "<"]:
                if op in condition:
                    comparison = op
                    break
        
        updates = {
            "name": name,
            "description": description,
            "service_id": service_id,
            "metric_name": metric_name,
            "threshold": threshold,
            "comparison": comparison,
            "severity": AlertSeverity(severity),
            "enabled": enabled,
            "evaluation_interval": evaluation_interval,
            "for_duration": for_duration
        }
        
        success = await self.update_alert_rule(rule_id, updates)
        if success:
            return await self.get_alert_rule(rule_id)
        return None
    
    async def get_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get alerts with filtering.
        
        Args:
            status: Filter by status (active, acknowledged, resolved)
            severity: Filter by severity
            service_id: Filter by service ID
            limit: Maximum number of alerts
            
        Returns:
            List of alert data
        """
        alerts = []
        
        for alert in list(self._alerts.values())[:limit]:
            # Apply filters
            if status:
                alert_status = "resolved" if alert.resolved else ("acknowledged" if alert.acknowledged else "active")
                if alert_status != status:
                    continue
            
            if severity and alert.severity.value != severity:
                continue
            
            if service_id and alert.service_id != service_id:
                continue
            
            # Get rule info
            rule_id = alert.metadata.get("rule_id")
            rule_name = ""
            if rule_id and rule_id in self._alert_rules:
                rule_name = self._alert_rules[rule_id].name
            
            alert_data = {
                "id": alert.id,
                "rule_id": rule_id or "",
                "rule_name": rule_name,
                "service_id": alert.service_id,
                "metric_name": alert.metadata.get("metric_name", ""),
                "current_value": alert.metadata.get("metric_value", 0),
                "threshold": alert.metadata.get("threshold", 0),
                "severity": alert.severity.value,
                "status": "resolved" if alert.resolved else ("acknowledged" if alert.acknowledged else "active"),
                "message": alert.message,
                "started_at": alert.created_at,
                "acknowledged_at": alert.acknowledged_at,
                "acknowledged_by": alert.acknowledged_by,
                "resolved_at": alert.resolved_at,
                "labels": {}
            }
            
            alerts.append(alert_data)
        
        return alerts
    
    async def create_dashboard(
        self,
        name: str,
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        refresh_interval: int = 30,
        time_range: str = "1h",
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new dashboard configuration."""
        dashboard_id = str(uuid.uuid4())
        
        dashboard = DashboardData(
            dashboard_id=dashboard_id,
            title=name,
            widgets=widgets or [],
            last_updated=datetime.utcnow()
        )
        
        await self.create_dashboard(dashboard)
        
        return {
            "id": dashboard_id,
            "name": name,
            "description": description,
            "layout": layout or {},
            "widgets": widgets or [],
            "refresh_interval": refresh_interval,
            "time_range": time_range,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": created_by
        }
    
    async def get_dashboards(self, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of dashboard configurations."""
        dashboards = []
        
        for dashboard in self._dashboards.values():
            dashboard_data = {
                "id": dashboard.dashboard_id,
                "name": dashboard.title,
                "description": "",
                "layout": {},
                "widgets": dashboard.widgets,
                "refresh_interval": 30,
                "time_range": "1h",
                "created_at": dashboard.last_updated,
                "updated_at": dashboard.last_updated,
                "created_by": created_by
            }
            dashboards.append(dashboard_data)
        
        return dashboards
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get specific dashboard configuration."""
        dashboard_data = await self.get_dashboard_data(dashboard_id)
        
        if not dashboard_data:
            return None
        
        return {
            "id": dashboard_data.dashboard_id,
            "name": dashboard_data.title,
            "description": "",
            "layout": {},
            "widgets": dashboard_data.widgets,
            "refresh_interval": 30,
            "time_range": "1h",
            "created_at": dashboard_data.last_updated,
            "updated_at": dashboard_data.last_updated,
            "created_by": None
        }
    
    async def update_dashboard(
        self,
        dashboard_id: str,
        name: str,
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        refresh_interval: int = 30,
        time_range: str = "1h"
    ) -> Optional[Dict[str, Any]]:
        """Update dashboard configuration."""
        updates = {
            "title": name,
            "widgets": widgets or []
        }
        
        success = await self.update_dashboard(dashboard_id, updates)
        if success:
            return await self.get_dashboard(dashboard_id)
        return None
    
    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete dashboard configuration."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False
    
    def _apply_aggregation(
        self, 
        data_points: List[Dict[str, Any]], 
        aggregation: str, 
        interval: str
    ) -> List[Dict[str, Any]]:
        """Apply aggregation to data points."""
        if not data_points or aggregation == "raw":
            return data_points
        
        # Simple aggregation implementation
        # In a full implementation, this would handle time-based bucketing
        values = [point.get("value", 0) for point in data_points]
        
        if aggregation == "avg":
            aggregated_value = sum(values) / len(values) if values else 0
        elif aggregation == "sum":
            aggregated_value = sum(values)
        elif aggregation == "min":
            aggregated_value = min(values) if values else 0
        elif aggregation == "max":
            aggregated_value = max(values) if values else 0
        elif aggregation == "count":
            aggregated_value = len(values)
        else:
            return data_points
        
        # Return single aggregated point
        return [{
            "timestamp": data_points[-1]["timestamp"] if data_points else datetime.utcnow().isoformat(),
            "value": aggregated_value
        }]
    
    def _apply_filters(
        self, 
        data_points: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to data points."""
        # Simple filter implementation
        # In a full implementation, this would handle complex filtering
        filtered_points = []
        
        for point in data_points:
            include_point = True
            
            # Apply value filters
            if "min_value" in filters and point.get("value", 0) < filters["min_value"]:
                include_point = False
            if "max_value" in filters and point.get("value", 0) > filters["max_value"]:
                include_point = False
            
            if include_point:
                filtered_points.append(point)
        
        return filtered_points
    
    # Service metric collection helpers
    
    def _get_service_cpu(self, service_id: str) -> float:
        """Get CPU usage for a service."""
        # This would integrate with actual service monitoring
        # For now, return a simulated value based on service activity
        import random
        base_cpu = 15.0  # Base CPU usage
        variation = random.uniform(-5.0, 25.0)  # Random variation
        return max(0.0, min(100.0, base_cpu + variation))
    
    def _get_service_memory(self, service_id: str) -> float:
        """Get memory usage for a service in MB."""
        import random
        base_memory = 128.0  # Base memory usage in MB
        variation = random.uniform(-20.0, 100.0)  # Random variation
        return max(50.0, base_memory + variation)
    
    def _get_service_requests(self, service_id: str) -> int:
        """Get request count for a service."""
        import random
        # Simulate request count based on time of day
        hour = datetime.utcnow().hour
        base_requests = 10 if 6 <= hour <= 22 else 2  # More requests during day
        variation = random.randint(0, 20)
        return base_requests + variation
    
    def _get_service_response_time(self, service_id: str) -> float:
        """Get average response time for a service in milliseconds."""
        import random
        base_response_time = 150.0  # Base response time in ms
        variation = random.uniform(-50.0, 200.0)  # Random variation
        return max(10.0, base_response_time + variation)
    
    def _get_service_error_rate(self, service_id: str) -> float:
        """Get error rate for a service as percentage."""
        import random
        # Most services should have low error rates
        return random.uniform(0.0, 5.0)
        import random
        return random.uniform(0, 100)
    
    def _get_service_memory(self, service_id: str) -> float:
        """Get memory usage for a service."""
        # This would integrate with actual service monitoring
        # For now, return a simulated value
        import random
        return random.uniform(50, 500)
    
    def _get_service_requests(self, service_id: str) -> int:
        """Get request count for a service."""
        # This would integrate with actual service monitoring
        # For now, return a simulated value
        import random
        return random.randint(0, 1000)
    
    def _get_service_response_time(self, service_id: str) -> float:
        """Get response time for a service."""
        # This would integrate with actual service monitoring
        # For now, return a simulated value
        import random
        return random.uniform(10, 500)
    
    def _get_service_error_rate(self, service_id: str) -> float:
        """Get error rate for a service."""
        # This would integrate with actual service monitoring
        # For now, return a simulated value
        import random
        return random.uniform(0, 5)
    
    # New API methods for monitoring endpoints
    
    async def query_metrics(self, service_ids: Optional[List[str]] = None,
                           metric_names: Optional[List[str]] = None,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           aggregation: str = "raw",
                           interval: str = "1m",
                           filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Query metrics data with time range and aggregation.
        
        Args:
            service_ids: List of service IDs to query
            metric_names: List of metric names to include
            start_time: Query start time
            end_time: Query end time
            aggregation: Aggregation type (raw, avg, sum, min, max, count, p95, p99)
            interval: Aggregation interval
            filters: Additional filters
            
        Returns:
            Dictionary of metrics data organized by service and metric name
        """
        return await self._safe_execute(
            "query_metrics",
            self._query_metrics_impl,
            service_ids, metric_names, start_time, end_time,
            aggregation, interval, filters or {}
        ) or {}
    
    async def get_available_services(self) -> List[str]:
        """Get list of available services with metrics."""
        return await self._safe_execute(
            "get_available_services",
            self._get_available_services_impl
        ) or []
    
    async def get_available_metrics(self, service_id: Optional[str] = None) -> List[str]:
        """Get list of available metric names."""
        return await self._safe_execute(
            "get_available_metrics",
            self._get_available_metrics_impl,
            service_id
        ) or []
    
    async def create_alert_rule(self, name: str, description: Optional[str],
                               service_id: Optional[str], metric_name: str,
                               condition: str, threshold: float, severity: str,
                               enabled: bool, notification_channels: List[str],
                               evaluation_interval: int, for_duration: int) -> Dict[str, Any]:
        """Create a new alert rule."""
        return await self._safe_execute(
            "create_alert_rule",
            self._create_alert_rule_impl,
            name, description, service_id, metric_name, condition,
            threshold, severity, enabled, notification_channels,
            evaluation_interval, for_duration
        ) or {}
    
    async def get_alert_rules(self, service_id: Optional[str] = None,
                             enabled: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get list of alert rules."""
        return await self._safe_execute(
            "get_alert_rules",
            self._get_alert_rules_impl,
            service_id, enabled
        ) or []
    
    async def get_alert_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get specific alert rule."""
        return await self._safe_execute(
            "get_alert_rule",
            self._get_alert_rule_impl,
            rule_id
        )
    
    async def update_alert_rule(self, rule_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update an alert rule."""
        return await self._safe_execute(
            "update_alert_rule",
            self._update_alert_rule_impl,
            rule_id, kwargs
        )
    
    async def delete_alert_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        return await self._safe_execute(
            "delete_alert_rule",
            self._delete_alert_rule_impl,
            rule_id
        ) or False
    
    async def get_alerts(self, status: Optional[str] = None,
                        severity: Optional[str] = None,
                        service_id: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        return await self._safe_execute(
            "get_alerts",
            self._get_alerts_impl,
            status, severity, service_id, limit
        ) or []
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        return await self._safe_execute(
            "acknowledge_alert",
            self._acknowledge_alert_impl,
            alert_id, acknowledged_by
        ) or False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        return await self._safe_execute(
            "resolve_alert",
            self._resolve_alert_impl,
            alert_id
        ) or False
    
    async def create_dashboard(self, name: str, description: Optional[str],
                              layout: Dict[str, Any], widgets: List[Dict[str, Any]],
                              refresh_interval: int, time_range: str,
                              created_by: Optional[str]) -> Dict[str, Any]:
        """Create a new dashboard configuration."""
        return await self._safe_execute(
            "create_dashboard",
            self._create_dashboard_impl,
            name, description, layout, widgets, refresh_interval,
            time_range, created_by
        ) or {}
    
    async def get_dashboards(self, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of dashboard configurations."""
        return await self._safe_execute(
            "get_dashboards",
            self._get_dashboards_impl,
            created_by
        ) or []
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get specific dashboard configuration."""
        return await self._safe_execute(
            "get_dashboard",
            self._get_dashboard_impl,
            dashboard_id
        )
    
    async def update_dashboard(self, dashboard_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a dashboard configuration."""
        return await self._safe_execute(
            "update_dashboard",
            self._update_dashboard_impl,
            dashboard_id, kwargs
        )
    
    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard configuration."""
        return await self._safe_execute(
            "delete_dashboard",
            self._delete_dashboard_impl,
            dashboard_id
        ) or False
    
    async def _delete_dashboard_impl(self, dashboard_id: str) -> bool:
        """Implementation for deleting dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False
        
        return rules
    
    async def _get_alert_rule_impl(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Implementation for getting specific alert rule."""
        rule = self._alert_rules.get(rule_id)
        if not rule:
            return None
        
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "service_id": rule.service_id,
            "metric_name": rule.metric_name,
            "condition": f"{rule.comparison} {rule.threshold}",
            "threshold": rule.threshold,
            "severity": rule.severity.value,
            "enabled": rule.enabled,
            "notification_channels": rule.notification_channels,
            "evaluation_interval": rule.evaluation_interval,
            "for_duration": rule.for_duration,
            "created_at": rule.created_at,
            "updated_at": rule.created_at,
            "last_evaluation": self._alert_states[rule.id]["last_evaluation"]
        }
    
    async def _update_alert_rule_impl(self, rule_id: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Implementation for updating alert rule."""
        rule = self._alert_rules.get(rule_id)
        if not rule:
            return None
        
        # Update rule fields
        if "name" in kwargs:
            rule.name = kwargs["name"]
        if "description" in kwargs:
            rule.description = kwargs["description"]
        if "enabled" in kwargs:
            rule.enabled = kwargs["enabled"]
        if "threshold" in kwargs:
            rule.threshold = kwargs["threshold"]
        if "severity" in kwargs:
            rule.severity = AlertSeverity(kwargs["severity"])
        
        return await self._get_alert_rule_impl(rule_id)
    
    async def _delete_alert_rule_impl(self, rule_id: str) -> bool:
        """Implementation for deleting alert rule."""
        if rule_id in self._alert_rules:
            del self._alert_rules[rule_id]
            del self._alert_states[rule_id]
            return True
        return False
    
    async def _get_alerts_impl(self, status: Optional[str], severity: Optional[str],
                              service_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Implementation for getting alerts."""
        alerts = []
        
        for alert in list(self._alerts.values())[:limit]:
            # Filter by status
            if status:
                alert_status = "resolved" if alert.resolved else "active"
                if alert_status != status:
                    continue
            
            # Filter by severity
            if severity and alert.severity.value != severity:
                continue
            
            # Filter by service_id
            if service_id and alert.service_id != service_id:
                continue
            
            alert_dict = {
                "id": alert.id,
                "rule_id": alert.metadata.get("rule_id"),
                "rule_name": alert.title,
                "service_id": alert.service_id,
                "metric_name": alert.metadata.get("metric_name"),
                "current_value": alert.metadata.get("metric_value"),
                "threshold": alert.metadata.get("threshold"),
                "severity": alert.severity.value,
                "status": "resolved" if alert.resolved else "active",
                "message": alert.message,
                "started_at": alert.created_at,
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": alert.resolved_at,
                "labels": {"service": alert.service_id}
            }
            alerts.append(alert_dict)
        
        return alerts
    
    async def _acknowledge_alert_impl(self, alert_id: str, acknowledged_by: str) -> bool:
        """Implementation for acknowledging alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        # For now, just log the acknowledgment
        # In a real implementation, you'd update the alert status
        self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        return True
    
    async def _resolve_alert_impl(self, alert_id: str) -> bool:
        """Implementation for resolving alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        return True
    
    async def _create_dashboard_impl(self, name: str, description: Optional[str],
                                    layout: Dict[str, Any], widgets: List[Dict[str, Any]],
                                    refresh_interval: int, time_range: str,
                                    created_by: Optional[str]) -> Dict[str, Any]:
        """Implementation for creating dashboard."""
        dashboard_id = str(uuid.uuid4())
        
        dashboard = {
            "id": dashboard_id,
            "name": name,
            "description": description,
            "layout": layout,
            "widgets": widgets,
            "refresh_interval": refresh_interval,
            "time_range": time_range,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": created_by
        }
        
        self._dashboards[dashboard_id] = dashboard
        return dashboard
    
    async def _get_dashboards_impl(self, created_by: Optional[str]) -> List[Dict[str, Any]]:
        """Implementation for getting dashboards."""
        dashboards = []
        
        for dashboard in self._dashboards.values():
            # Filter by creator if specified
            if created_by and dashboard.get("created_by") != created_by:
                continue
            
            dashboards.append(dashboard)
        
        return dashboards
    
    async def _get_dashboard_impl(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Implementation for getting specific dashboard."""
        return self._dashboards.get(dashboard_id)
    
    async def _update_dashboard_impl(self, dashboard_id: str, kwargs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Implementation for updating dashboard."""
        dashboard = self._dashboards.get(dashboard_id)
        if not dashboard:
            return None
        
        # Update dashboard fields
        for key, value in kwargs.items():
            if key in ["name", "description", "layout", "widgets", "refresh_interval", "time_range"]:
                dashboard[key] = value
        
        dashboard["updated_at"] = datetime.utcnow()
        return dashboard
    
    async def _delete_dashboard_impl(self, dashboard_id: str) -> bool:
        """Implementation for deleting dashboard."""
        if dashboard_id in self._dashboards:
            del self._dashboards[dashboard_id]
            return True
        return False
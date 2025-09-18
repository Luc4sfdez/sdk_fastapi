"""
Database monitoring manager for coordinating all monitoring activities.

This module provides the central MonitoringManager class that orchestrates
metrics collection, analytics, alerting, and health monitoring across
all database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
import json

from ..manager import DatabaseManager
from .config import MonitoringConfig, AlertChannel
from .metrics import MetricsCollector, DatabaseMetrics
from .analytics import DatabaseAnalytics, AnalyticsFinding, Severity
from .exceptions import MonitoringError, AlertingError

# Integration with communication logging
try:
    from ...communication.logging import CommunicationLogger
    COMMUNICATION_LOGGING_AVAILABLE = True
except ImportError:
    COMMUNICATION_LOGGING_AVAILABLE = False
    CommunicationLogger = None


class AlertManager:
    """Manages alerting and notifications."""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._alert_history: Dict[str, datetime] = {}
        
        # Setup logging
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("monitoring.alerts")
        else:
            self.logger = logging.getLogger(__name__)
    
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: Severity,
        database_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send alert through configured channels.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity
            database_name: Database name
            metadata: Additional metadata
        """
        if not self.config.alerting_enabled:
            return
        
        # Check cooldown period
        alert_key = f"{alert_type}_{database_name}"
        if self._is_in_cooldown(alert_key):
            return
        
        # Record alert time
        self._alert_history[alert_key] = datetime.now(timezone.utc)
        
        # Prepare alert data
        alert_data = {
            'alert_type': alert_type,
            'message': message,
            'severity': severity.value,
            'database_name': database_name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        # Send through configured channels
        for channel in self.config.alert_channels:
            try:
                await self._send_alert_to_channel(channel, alert_data)
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel.value}: {e}")
    
    def _is_in_cooldown(self, alert_key: str) -> bool:
        """Check if alert is in cooldown period."""
        if alert_key not in self._alert_history:
            return False
        
        last_alert = self._alert_history[alert_key]
        cooldown_end = last_alert + self.config.alert_cooldown_period
        
        return datetime.now(timezone.utc) < cooldown_end
    
    async def _send_alert_to_channel(self, channel: AlertChannel, alert_data: Dict[str, Any]) -> None:
        """Send alert to specific channel."""
        if channel == AlertChannel.EMAIL:
            await self._send_email_alert(alert_data)
        elif channel == AlertChannel.SLACK:
            await self._send_slack_alert(alert_data)
        elif channel == AlertChannel.WEBHOOK:
            await self._send_webhook_alert(alert_data)
        # Add other channels as needed
    
    async def _send_email_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send email alert (placeholder for email implementation)."""
        # This would implement actual email sending
        self.logger.info(f"Email alert: {alert_data['message']}")
    
    async def _send_slack_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send Slack alert (placeholder for Slack implementation)."""
        # This would implement actual Slack integration
        self.logger.info(f"Slack alert: {alert_data['message']}")
    
    async def _send_webhook_alert(self, alert_data: Dict[str, Any]) -> None:
        """Send webhook alert."""
        # This would implement webhook posting
        for webhook_url in self.config.notification_webhooks:
            self.logger.info(f"Webhook alert to {webhook_url}: {alert_data['message']}")


class MonitoringManager:
    """
    Central monitoring management orchestrator.
    
    Coordinates metrics collection, analytics, alerting, and health monitoring
    across all database engines with enterprise-grade capabilities.
    """
    
    def __init__(self, config: MonitoringConfig, database_manager: DatabaseManager):
        self.config = config
        self.database_manager = database_manager
        
        # Core components
        self.metrics_collector = MetricsCollector(config)
        self.analytics = DatabaseAnalytics(config, self.metrics_collector)
        self.alert_manager = AlertManager(config)
        
        # State management
        self._initialized = False
        self._running = False
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Setup logging
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("monitoring.manager")
        else:
            self.logger = logging.getLogger(__name__)
        
        # Callbacks
        self._alert_callbacks: List[Callable] = []
        self._health_callbacks: List[Callable] = []
        
        self.logger.info("MonitoringManager initialized")
    
    async def initialize(self) -> None:
        """Initialize monitoring manager."""
        if self._initialized:
            return
        
        try:
            self.logger.info("Initializing MonitoringManager...")
            
            # Get database adapters
            database_adapters = {}
            for db_name in self.database_manager.list_databases():
                adapter = self.database_manager.get_adapter(db_name)
                database_adapters[db_name] = adapter
            
            # Start metrics collection
            if self.config.enabled:
                await self.metrics_collector.start_collection(database_adapters)
            
            self._initialized = True
            self.logger.info("MonitoringManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MonitoringManager: {e}")
            raise MonitoringError(f"MonitoringManager initialization failed: {e}", original_error=e)
    
    async def start_monitoring(self) -> None:
        """Start all monitoring activities."""
        if not self._initialized:
            await self.initialize()
        
        if self._running:
            return
        
        try:
            self._running = True
            
            # Start monitoring tasks for each database
            for db_name in self.database_manager.list_databases():
                task = asyncio.create_task(self._monitoring_loop(db_name))
                self._monitoring_tasks[db_name] = task
            
            self.logger.info("Monitoring started for all databases")
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise MonitoringError(f"Failed to start monitoring: {e}", original_error=e)
    
    async def stop_monitoring(self) -> None:
        """Stop all monitoring activities."""
        if not self._running:
            return
        
        try:
            self._running = False
            
            # Stop monitoring tasks
            for task in self._monitoring_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            self._monitoring_tasks.clear()
            
            # Stop metrics collection
            await self.metrics_collector.stop_collection()
            
            self.logger.info("Monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
    
    async def _monitoring_loop(self, database_name: str) -> None:
        """Main monitoring loop for a database."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self._running:
                    break
                
                # Perform health assessment
                await self._perform_health_check(database_name)
                
                # Check for alerts
                await self._check_alerts(database_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop for {database_name}: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
    
    async def _perform_health_check(self, database_name: str) -> None:
        """Perform health check for a database."""
        try:
            # Generate health assessment
            assessment = await self.analytics.generate_health_assessment(database_name)
            
            # Execute health callbacks
            for callback in self._health_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(database_name, assessment)
                    else:
                        callback(database_name, assessment)
                except Exception as e:
                    self.logger.error(f"Health callback failed: {e}")
            
            # Check if health score is concerning
            health_score = assessment.get('health_score', 100)
            if health_score < 60:
                await self.alert_manager.send_alert(
                    alert_type="health_degradation",
                    message=f"Database {database_name} health score is {health_score:.1f}",
                    severity=Severity.HIGH if health_score < 40 else Severity.MEDIUM,
                    database_name=database_name,
                    metadata={'health_score': health_score, 'assessment': assessment}
                )
            
        except Exception as e:
            self.logger.error(f"Health check failed for {database_name}: {e}")
    
    async def _check_alerts(self, database_name: str) -> None:
        """Check for alert conditions."""
        try:
            # Get latest metrics
            latest_metrics = self.metrics_collector.get_latest_metrics(database_name)
            if not latest_metrics:
                return
            
            # Check alert thresholds
            adapter = self.database_manager.get_adapter(database_name)
            thresholds = self.config.get_alert_thresholds(adapter.config.engine)
            
            await self._check_metric_thresholds(database_name, latest_metrics, thresholds)
            
            # Detect anomalies
            anomalies = await self.analytics.detect_anomalies(database_name)
            for anomaly in anomalies:
                if anomaly.severity in [Severity.HIGH, Severity.CRITICAL]:
                    await self.alert_manager.send_alert(
                        alert_type="anomaly_detected",
                        message=f"Anomaly detected: {anomaly.title}",
                        severity=anomaly.severity,
                        database_name=database_name,
                        metadata=anomaly.to_dict()
                    )
            
        except Exception as e:
            self.logger.error(f"Alert checking failed for {database_name}: {e}")
    
    async def _check_metric_thresholds(
        self,
        database_name: str,
        metrics: DatabaseMetrics,
        thresholds: Dict[str, float]
    ) -> None:
        """Check metrics against alert thresholds."""
        # Check query duration
        if metrics.p95_query_duration > thresholds.get('query_duration_p95', 5.0):
            await self.alert_manager.send_alert(
                alert_type="slow_queries",
                message=f"95th percentile query duration is {metrics.p95_query_duration:.2f}s",
                severity=Severity.MEDIUM,
                database_name=database_name,
                metadata={'p95_duration': metrics.p95_query_duration}
            )
        
        # Check connection utilization
        if metrics.connection_pool_utilization > thresholds.get('connection_utilization', 0.8):
            await self.alert_manager.send_alert(
                alert_type="high_connection_utilization",
                message=f"Connection pool utilization is {metrics.connection_pool_utilization:.1%}",
                severity=Severity.HIGH if metrics.connection_pool_utilization > 0.95 else Severity.MEDIUM,
                database_name=database_name,
                metadata={'utilization': metrics.connection_pool_utilization}
            )
        
        # Check error rate
        if metrics.error_rate > thresholds.get('error_rate', 0.05):
            await self.alert_manager.send_alert(
                alert_type="high_error_rate",
                message=f"Error rate is {metrics.error_rate:.1%}",
                severity=Severity.HIGH,
                database_name=database_name,
                metadata={'error_rate': metrics.error_rate}
            )
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            'initialized': self._initialized,
            'running': self._running,
            'monitored_databases': list(self._monitoring_tasks.keys()),
            'metrics_collection_enabled': self.config.enabled,
            'alerting_enabled': self.config.alerting_enabled,
            'analytics_enabled': self.config.analytics_enabled,
            'last_update': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_database_health(self, database_name: str) -> Dict[str, Any]:
        """Get health assessment for a specific database."""
        return await self.analytics.generate_health_assessment(database_name)
    
    async def get_performance_trends(
        self,
        database_name: str,
        period: timedelta = timedelta(hours=24)
    ) -> List[Dict[str, Any]]:
        """Get performance trends for a database."""
        trends = await self.analytics.analyze_performance_trends(database_name, period)
        return [trend.to_dict() for trend in trends]
    
    async def get_query_optimization_suggestions(
        self,
        database_name: str,
        query_samples: List[str]
    ) -> List[Dict[str, Any]]:
        """Get query optimization suggestions."""
        suggestions = await self.analytics.analyze_query_optimization(database_name, query_samples)
        return [suggestion.to_dict() for suggestion in suggestions]
    
    async def get_resource_utilization(
        self,
        database_name: str,
        period: timedelta = timedelta(hours=24)
    ) -> List[Dict[str, Any]]:
        """Get resource utilization analysis."""
        analysis = await self.analytics.analyze_resource_utilization(database_name, period)
        return [item.to_dict() for item in analysis]
    
    def record_query_execution(
        self,
        database_name: str,
        query: str,
        duration: float,
        success: bool,
        error: Optional[Exception] = None
    ) -> None:
        """
        Record query execution for monitoring.
        
        Args:
            database_name: Name of the database
            query: Executed query
            duration: Execution duration in seconds
            success: Whether query was successful
            error: Error if query failed
        """
        # Record duration
        self.metrics_collector.record_query_duration(database_name, duration)
        
        # Record error if applicable
        if not success and error:
            self.metrics_collector.record_query_error(database_name, error)
        
        # Check for slow query alert
        if duration > self.config.slow_query_threshold:
            asyncio.create_task(self._handle_slow_query(database_name, query, duration))
    
    async def _handle_slow_query(self, database_name: str, query: str, duration: float) -> None:
        """Handle slow query detection."""
        try:
            await self.alert_manager.send_alert(
                alert_type="slow_query",
                message=f"Slow query detected: {duration:.2f}s",
                severity=Severity.MEDIUM,
                database_name=database_name,
                metadata={
                    'duration': duration,
                    'query': query[:200] + '...' if len(query) > 200 else query
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to send slow query alert: {e}")
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add callback for alert events."""
        self._alert_callbacks.append(callback)
    
    def add_health_callback(self, callback: Callable) -> None:
        """Add callback for health check events."""
        self._health_callbacks.append(callback)
    
    async def export_metrics(
        self,
        database_name: str,
        format: str = "json",
        period: Optional[timedelta] = None
    ) -> str:
        """
        Export metrics in specified format.
        
        Args:
            database_name: Name of the database
            format: Export format (json, csv, prometheus)
            period: Time period for export
            
        Returns:
            Exported metrics as string
        """
        if period is None:
            period = timedelta(hours=1)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - period
        
        metrics = self.metrics_collector.get_metrics(database_name, None, start_time, end_time)
        
        if format.lower() == "json":
            return json.dumps([metric.to_dict() for metric in metrics], indent=2)
        elif format.lower() == "prometheus":
            return self._export_prometheus_format(database_name, metrics)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_prometheus_format(self, database_name: str, metrics: List) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Group metrics by name
        metric_groups = {}
        for metric in metrics:
            for label, value in metric.labels.items():
                if label not in metric_groups:
                    metric_groups[label] = []
                metric_groups[label].append((metric.timestamp, metric.value))
        
        # Generate Prometheus format
        for metric_name, values in metric_groups.items():
            lines.append(f"# HELP {metric_name} Database metric")
            lines.append(f"# TYPE {metric_name} gauge")
            
            for timestamp, value in values:
                timestamp_ms = int(timestamp.timestamp() * 1000)
                lines.append(f'{metric_name}{{database="{database_name}"}} {value} {timestamp_ms}')
        
        return '\n'.join(lines)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        await self.start_monitoring()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_monitoring()
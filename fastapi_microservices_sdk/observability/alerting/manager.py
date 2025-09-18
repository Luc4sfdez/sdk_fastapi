"""
Alert Manager for FastAPI Microservices SDK.

This module provides the main alert management system that integrates
rule evaluation, notifications, escalation, grouping, and deduplication.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import AlertConfig, AlertSeverity, AlertStatus
from .exceptions import AlertManagerError, AlertingError
from .rules import AlertRuleEngine, AlertRule, MetricDataPoint
from .notifications import NotificationManager, NotificationMessage
from .escalation import EscalationManager
from .grouping import AlertGrouper, AlertDeduplicator, GroupingStrategy, DeduplicationStrategy


@dataclass
class AlertInstance:
    """Active alert instance."""
    alert_id: str
    rule_name: str
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    escalation_id: Optional[str] = None
    group_id: Optional[str] = None
    notification_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'rule_name': self.rule_name,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'labels': self.labels,
            'annotations': self.annotations,
            'escalation_id': self.escalation_id,
            'group_id': self.group_id,
            'notification_count': self.notification_count
        }
    
    def to_notification_message(self) -> NotificationMessage:
        """Convert to notification message."""
        return NotificationMessage(
            alert_id=self.alert_id,
            title=self.title,
            message=self.message,
            severity=self.severity,
            timestamp=self.updated_at,
            labels=self.labels,
            annotations=self.annotations
        )


class AlertManager:
    """Main alert management system."""
    
    def __init__(self, config: AlertConfig):
        """Initialize alert manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.rule_engine = AlertRuleEngine(
            evaluation_interval=timedelta(seconds=config.evaluation_interval)
        )
        self.notification_manager = NotificationManager()
        self.escalation_manager = EscalationManager(self.notification_manager)
        
        # Grouping and deduplication
        if config.enable_grouping:
            self.grouper = AlertGrouper(
                grouping_window=timedelta(seconds=config.grouping_window)
            )
        else:
            self.grouper = None
        
        if config.enable_deduplication:
            self.deduplicator = AlertDeduplicator(
                deduplication_window=timedelta(seconds=config.deduplication_window)
            )
        else:
            self.deduplicator = None
        
        # Alert storage
        self._active_alerts: Dict[str, AlertInstance] = {}
        self._alert_history: List[AlertInstance] = []
        
        # Manager state
        self._running = False
        self._processing_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._alert_callbacks: List[Callable[[AlertInstance], None]] = []
        self._resolve_callbacks: List[Callable[[AlertInstance], None]] = []
        
        # Setup rule engine callbacks
        self.rule_engine.add_alert_callback(self._handle_new_alert)
        self.rule_engine.add_resolve_callback(self._handle_resolved_alert)
    
    async def start(self):
        """Start alert manager."""
        if self._running:
            return
        
        self._running = True
        
        # Start components
        await self.rule_engine.start()
        await self.escalation_manager.start()
        
        # Start processing task
        self._processing_task = asyncio.create_task(self._processing_loop())
        
        self.logger.info("Alert manager started")
    
    async def stop(self):
        """Stop alert manager."""
        if not self._running:
            return
        
        self._running = False
        
        # Stop components
        await self.rule_engine.stop()
        await self.escalation_manager.stop()
        
        # Stop processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Alert manager stopped")
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.rule_engine.add_rule(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule."""
        self.rule_engine.remove_rule(rule_name)
    
    def set_metric_data_source(self, metric_name: str, data_source: Callable[[str], List[MetricDataPoint]]):
        """Set data source for metrics."""
        self.rule_engine.set_data_source(metric_name, data_source)
    
    def add_alert_callback(self, callback: Callable[[AlertInstance], None]):
        """Add callback for new alerts."""
        self._alert_callbacks.append(callback)
    
    def add_resolve_callback(self, callback: Callable[[AlertInstance], None]):
        """Add callback for resolved alerts."""
        self._resolve_callbacks.append(callback)
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system"):
        """Acknowledge alert."""
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now(timezone.utc)
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.now(timezone.utc)
                
                # Cancel escalation if active
                if alert.escalation_id:
                    await self.escalation_manager.acknowledge_escalation(alert.escalation_id)
                
                self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                
        except Exception as e:
            self.logger.error(f"Error acknowledging alert {alert_id}: {e}")
            raise AlertManagerError(
                f"Failed to acknowledge alert {alert_id}",
                alert_id=alert_id,
                original_error=e
            )
    
    async def resolve_alert(self, alert_id: str):
        """Manually resolve alert."""
        try:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                await self._resolve_alert(alert)
                
        except Exception as e:
            self.logger.error(f"Error resolving alert {alert_id}: {e}")
            raise AlertManagerError(
                f"Failed to resolve alert {alert_id}",
                alert_id=alert_id,
                original_error=e
            )
    
    def get_alert(self, alert_id: str) -> Optional[AlertInstance]:
        """Get alert by ID."""
        return self._active_alerts.get(alert_id)
    
    def list_active_alerts(self) -> List[AlertInstance]:
        """List all active alerts."""
        return list(self._active_alerts.values())
    
    def list_alerts_by_status(self, status: AlertStatus) -> List[AlertInstance]:
        """List alerts by status."""
        return [alert for alert in self._active_alerts.values() if alert.status == status]
    
    def list_alerts_by_severity(self, severity: AlertSeverity) -> List[AlertInstance]:
        """List alerts by severity."""
        return [alert for alert in self._active_alerts.values() if alert.severity == severity]
    
    async def _processing_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                await self._process_alert_groups()
                await self._cleanup_old_alerts()
                await asyncio.sleep(30)  # Process every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _process_alert_groups(self):
        """Process ready alert groups."""
        if not self.grouper:
            return
        
        ready_groups = self.grouper.get_ready_groups()
        
        for group in ready_groups:
            try:
                # Convert group to notification message
                group_message = group.to_notification_message()
                
                # Send group notification
                await self._send_notification(group_message)
                
                # Remove processed group
                self.grouper.remove_group(group.group_id)
                
            except Exception as e:
                self.logger.error(f"Error processing alert group {group.group_id}: {e}")
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.alert_retention_days)
        
        # Move old alerts to history
        expired_alerts = []
        for alert_id, alert in self._active_alerts.items():
            if (alert.status in [AlertStatus.RESOLVED, AlertStatus.EXPIRED] and
                alert.updated_at <= cutoff_time):
                expired_alerts.append(alert_id)
        
        for alert_id in expired_alerts:
            alert = self._active_alerts.pop(alert_id)
            self._alert_history.append(alert)
        
        # Limit history size
        max_history = 10000
        if len(self._alert_history) > max_history:
            self._alert_history = self._alert_history[-max_history:]
    
    def _handle_new_alert(self, rule: AlertRule):
        """Handle new alert from rule engine."""
        try:
            # Create alert instance
            alert_id = f"alert_{rule.config.name}_{int(time.time())}"
            
            alert = AlertInstance(
                alert_id=alert_id,
                rule_name=rule.config.name,
                title=f"Alert: {rule.config.name}",
                message=rule.config.description,
                severity=rule.config.severity,
                status=AlertStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                labels=rule.config.labels.copy(),
                annotations=rule.config.annotations.copy()
            )
            
            self._active_alerts[alert_id] = alert
            
            # Process alert through pipeline
            asyncio.create_task(self._process_new_alert(alert))
            
            # Trigger callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling new alert from rule {rule.config.name}: {e}")
    
    def _handle_resolved_alert(self, rule: AlertRule):
        """Handle resolved alert from rule engine."""
        try:
            # Find active alerts for this rule
            rule_alerts = [
                alert for alert in self._active_alerts.values()
                if alert.rule_name == rule.config.name and alert.status == AlertStatus.ACTIVE
            ]
            
            for alert in rule_alerts:
                asyncio.create_task(self._resolve_alert(alert))
                
        except Exception as e:
            self.logger.error(f"Error handling resolved alert from rule {rule.config.name}: {e}")
    
    async def _process_new_alert(self, alert: AlertInstance):
        """Process new alert through the pipeline."""
        try:
            # Convert to notification message
            message = alert.to_notification_message()
            
            # Check deduplication
            if self.deduplicator and self.deduplicator.is_duplicate(message):
                self.logger.debug(f"Alert {alert.alert_id} is duplicate, skipping")
                return
            
            # Handle grouping
            if self.grouper:
                group_id = self.grouper.add_alert(message, GroupingStrategy.BY_LABELS)
                alert.group_id = group_id
                
                # Don't send individual notification if grouping is enabled
                # Groups will be processed later
                return
            
            # Send immediate notification
            await self._send_notification(message)
            
            # Start escalation if configured
            if self.config.enable_escalation:
                escalation_id = await self.escalation_manager.start_escalation(
                    alert.alert_id,
                    message
                )
                alert.escalation_id = escalation_id
                
        except Exception as e:
            self.logger.error(f"Error processing new alert {alert.alert_id}: {e}")
    
    async def _resolve_alert(self, alert: AlertInstance):
        """Resolve alert."""
        try:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            alert.updated_at = datetime.now(timezone.utc)
            
            # Cancel escalation if active
            if alert.escalation_id:
                await self.escalation_manager.cancel_escalation(alert.escalation_id)
            
            # Send resolution notification
            resolution_message = NotificationMessage(
                alert_id=alert.alert_id,
                title=f"RESOLVED: {alert.title}",
                message=f"Alert {alert.alert_id} has been resolved",
                severity=AlertSeverity.INFO,
                timestamp=datetime.now(timezone.utc),
                labels=alert.labels,
                annotations={**alert.annotations, 'resolution': 'true'}
            )
            
            await self._send_notification(resolution_message)
            
            # Trigger callbacks
            for callback in self._resolve_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in resolve callback: {e}")
            
            self.logger.info(f"Alert {alert.alert_id} resolved")
            
        except Exception as e:
            self.logger.error(f"Error resolving alert {alert.alert_id}: {e}")
    
    async def _send_notification(self, message: NotificationMessage):
        """Send notification through notification manager."""
        try:
            results = await self.notification_manager.send_notification(message)
            
            # Log results
            success_count = sum(1 for result in results.values() if result.success)
            total_count = len(results)
            
            if success_count > 0:
                self.logger.info(f"Notification sent: {success_count}/{total_count} channels succeeded")
            else:
                self.logger.warning(f"Notification failed: all {total_count} channels failed")
                
            # Update alert notification count
            if message.alert_id in self._active_alerts:
                self._active_alerts[message.alert_id].notification_count += 1
                
        except Exception as e:
            self.logger.error(f"Error sending notification for alert {message.alert_id}: {e}")
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics."""
        active_alerts = len(self._active_alerts)
        
        status_counts = {}
        severity_counts = {}
        
        for alert in self._active_alerts.values():
            # Count by status
            status = alert.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by severity
            severity = alert.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        stats = {
            'active_alerts': active_alerts,
            'status_counts': status_counts,
            'severity_counts': severity_counts,
            'alert_history_size': len(self._alert_history),
            'running': self._running,
            'rule_engine_stats': self.rule_engine.get_engine_stats(),
            'notification_manager_stats': self.notification_manager.get_manager_stats(),
            'escalation_manager_stats': self.escalation_manager.get_manager_stats()
        }
        
        if self.grouper:
            stats['grouper_stats'] = self.grouper.get_grouper_stats()
        
        if self.deduplicator:
            stats['deduplicator_stats'] = self.deduplicator.get_deduplicator_stats()
        
        return stats


def create_alert_manager(config: AlertConfig) -> AlertManager:
    """Create alert manager."""
    return AlertManager(config)


# Export main classes and functions
__all__ = [
    'AlertInstance',
    'AlertManager',
    'create_alert_manager',
]
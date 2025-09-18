"""
Dashboard Alerts - Alert management for dashboards

This module provides alert management functionality for dashboards,
including threshold monitoring, notification routing, and alert history.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


class Alert:
    """Dashboard alert."""
    
    def __init__(
        self,
        id: str,
        name: str,
        severity: AlertSeverity,
        message: str,
        component_id: str,
        dashboard_id: str,
        threshold_config: Dict[str, Any],
        current_value: Any,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.severity = severity
        self.message = message
        self.component_id = component_id
        self.dashboard_id = dashboard_id
        self.threshold_config = threshold_config
        self.current_value = current_value
        self.created_at = created_at or datetime.utcnow()
        self.status = AlertStatus.ACTIVE
        self.acknowledged_at: Optional[datetime] = None
        self.resolved_at: Optional[datetime] = None
        self.acknowledged_by: Optional[str] = None
    
    def acknowledge(self, user: str) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user
    
    def resolve(self) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value,
            "message": self.message,
            "component_id": self.component_id,
            "dashboard_id": self.dashboard_id,
            "threshold_config": self.threshold_config,
            "current_value": self.current_value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by
        }


class AlertRule:
    """Alert rule configuration."""
    
    def __init__(
        self,
        id: str,
        name: str,
        component_id: str,
        dashboard_id: str,
        condition: str,
        threshold: float,
        severity: AlertSeverity,
        message_template: str,
        enabled: bool = True,
        cooldown_minutes: int = 5
    ):
        self.id = id
        self.name = name
        self.component_id = component_id
        self.dashboard_id = dashboard_id
        self.condition = condition  # "greater_than", "less_than", "equals", "not_equals"
        self.threshold = threshold
        self.severity = severity
        self.message_template = message_template
        self.enabled = enabled
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered: Optional[datetime] = None
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should trigger."""
        if not self.enabled:
            return False
        
        # Check cooldown
        if self.last_triggered:
            cooldown_end = self.last_triggered + timedelta(minutes=self.cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                return False
        
        # Check condition
        if self.condition == "greater_than":
            return current_value > self.threshold
        elif self.condition == "less_than":
            return current_value < self.threshold
        elif self.condition == "equals":
            return abs(current_value - self.threshold) < 0.001
        elif self.condition == "not_equals":
            return abs(current_value - self.threshold) >= 0.001
        
        return False
    
    def create_alert(self, current_value: float) -> Alert:
        """Create alert from rule."""
        message = self.message_template.format(
            value=current_value,
            threshold=self.threshold,
            component_id=self.component_id
        )
        
        alert = Alert(
            id=f"{self.id}_{int(datetime.utcnow().timestamp())}",
            name=self.name,
            severity=self.severity,
            message=message,
            component_id=self.component_id,
            dashboard_id=self.dashboard_id,
            threshold_config={
                "condition": self.condition,
                "threshold": self.threshold
            },
            current_value=current_value
        )
        
        self.last_triggered = datetime.utcnow()
        return alert
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "component_id": self.component_id,
            "dashboard_id": self.dashboard_id,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "message_template": self.message_template,
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None
        }


class DashboardAlertManager:
    """
    Dashboard alert management system.
    
    Provides:
    - Alert rule management
    - Alert evaluation and triggering
    - Alert notification routing
    - Alert history and analytics
    """
    
    def __init__(self):
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable] = []
        self.is_running = False
        self.evaluation_task: Optional[asyncio.Task] = None
        
        logger.info("Dashboard alert manager initialized")
    
    async def initialize(self) -> None:
        """Initialize alert manager."""
        self.is_running = True
        
        # Start alert evaluation loop
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        
        logger.info("Dashboard alert manager started")
    
    async def shutdown(self) -> None:
        """Shutdown alert manager."""
        self.is_running = False
        
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Dashboard alert manager stopped")
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add alert rule."""
        self.alert_rules[rule.id] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_id: str) -> None:
        """Remove alert rule."""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
    
    def get_alert_rules(self, dashboard_id: Optional[str] = None) -> List[AlertRule]:
        """Get alert rules, optionally filtered by dashboard."""
        rules = list(self.alert_rules.values())
        
        if dashboard_id:
            rules = [rule for rule in rules if rule.dashboard_id == dashboard_id]
        
        return rules
    
    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add notification handler."""
        self.notification_handlers.append(handler)
        logger.info("Added notification handler")
    
    async def evaluate_component_value(
        self,
        component_id: str,
        dashboard_id: str,
        current_value: float
    ) -> List[Alert]:
        """
        Evaluate component value against alert rules.
        
        Args:
            component_id: Component ID
            dashboard_id: Dashboard ID
            current_value: Current component value
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        # Find applicable rules
        applicable_rules = [
            rule for rule in self.alert_rules.values()
            if rule.component_id == component_id and rule.dashboard_id == dashboard_id
        ]
        
        for rule in applicable_rules:
            if rule.should_trigger(current_value):
                alert = rule.create_alert(current_value)
                
                # Add to active alerts
                self.active_alerts[alert.id] = alert
                
                # Add to history
                self.alert_history.append(alert)
                
                # Send notifications
                await self._send_notifications(alert)
                
                triggered_alerts.append(alert)
                
                logger.warning(f"Alert triggered: {alert.name} - {alert.message}")
        
        return triggered_alerts
    
    async def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledge(user)
            logger.info(f"Alert acknowledged: {alert_id} by {user}")
            return True
        
        return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolve()
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
        
        return False
    
    def get_active_alerts(
        self,
        dashboard_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts with optional filtering."""
        alerts = list(self.active_alerts.values())
        
        if dashboard_id:
            alerts = [alert for alert in alerts if alert.dashboard_id == dashboard_id]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return alerts
    
    def get_alert_history(
        self,
        dashboard_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Alert]:
        """Get alert history."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        alerts = [
            alert for alert in self.alert_history
            if alert.created_at >= cutoff_time
        ]
        
        if dashboard_id:
            alerts = [alert for alert in alerts if alert.dashboard_id == dashboard_id]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    def get_alert_statistics(self, dashboard_id: Optional[str] = None) -> Dict[str, Any]:
        """Get alert statistics."""
        alerts = self.alert_history
        
        if dashboard_id:
            alerts = [alert for alert in alerts if alert.dashboard_id == dashboard_id]
        
        # Calculate statistics
        total_alerts = len(alerts)
        active_count = len(self.get_active_alerts(dashboard_id))
        
        severity_counts = {}
        for severity in AlertSeverity:
            severity_counts[severity.value] = len([
                alert for alert in alerts if alert.severity == severity
            ])
        
        # Recent activity (last 24 hours)
        recent_alerts = self.get_alert_history(dashboard_id, hours=24)
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_count,
            "severity_breakdown": severity_counts,
            "recent_alerts_24h": len(recent_alerts),
            "alert_rules_count": len(self.get_alert_rules(dashboard_id))
        }
    
    async def _evaluation_loop(self) -> None:
        """Background alert evaluation loop."""
        while self.is_running:
            try:
                # Auto-resolve alerts that are no longer active
                await self._auto_resolve_alerts()
                
                # Clean up old history
                await self._cleanup_history()
                
                # Wait before next evaluation
                await asyncio.sleep(30)  # Evaluate every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert evaluation loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _auto_resolve_alerts(self) -> None:
        """Auto-resolve alerts that are no longer active."""
        # This would typically re-evaluate conditions and auto-resolve
        # For now, we'll just resolve very old alerts
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        alerts_to_resolve = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.created_at < cutoff_time and alert.status == AlertStatus.ACTIVE
        ]
        
        for alert_id in alerts_to_resolve:
            await self.resolve_alert(alert_id)
            logger.info(f"Auto-resolved old alert: {alert_id}")
    
    async def _cleanup_history(self) -> None:
        """Clean up old alert history."""
        cutoff_time = datetime.utcnow() - timedelta(days=30)  # Keep 30 days
        
        original_count = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.created_at >= cutoff_time
        ]
        
        cleaned_count = original_count - len(self.alert_history)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old alerts from history")
    
    async def _send_notifications(self, alert: Alert) -> None:
        """Send alert notifications."""
        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error sending notification: {e}")
    
    def create_standard_rules_for_dashboard(
        self,
        dashboard_id: str,
        components: List[Dict[str, Any]]
    ) -> List[AlertRule]:
        """Create standard alert rules for dashboard components."""
        rules = []
        
        for component in components:
            component_id = component.get("id", "")
            component_type = component.get("type", "")
            
            # Create rules based on component type
            if component_type == "metric":
                # High value alert
                rule = AlertRule(
                    id=f"{component_id}_high",
                    name=f"{component.get('title', 'Component')} High Value",
                    component_id=component_id,
                    dashboard_id=dashboard_id,
                    condition="greater_than",
                    threshold=100,  # Default threshold
                    severity=AlertSeverity.WARNING,
                    message_template="Component {component_id} value {value} exceeds threshold {threshold}"
                )
                rules.append(rule)
                
                # Low value alert (if applicable)
                if component.get("alert_on_low", False):
                    rule = AlertRule(
                        id=f"{component_id}_low",
                        name=f"{component.get('title', 'Component')} Low Value",
                        component_id=component_id,
                        dashboard_id=dashboard_id,
                        condition="less_than",
                        threshold=0,
                        severity=AlertSeverity.WARNING,
                        message_template="Component {component_id} value {value} below threshold {threshold}"
                    )
                    rules.append(rule)
        
        # Add rules to manager
        for rule in rules:
            self.add_alert_rule(rule)
        
        logger.info(f"Created {len(rules)} standard alert rules for dashboard {dashboard_id}")
        return rules
    
    def get_status(self) -> Dict[str, Any]:
        """Get alert manager status."""
        return {
            "running": self.is_running,
            "alert_rules_count": len(self.alert_rules),
            "active_alerts_count": len(self.active_alerts),
            "notification_handlers_count": len(self.notification_handlers),
            "history_size": len(self.alert_history)
        }
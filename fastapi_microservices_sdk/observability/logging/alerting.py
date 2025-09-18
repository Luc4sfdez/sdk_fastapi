"""
Log-based Alerting and Notification System for FastAPI Microservices SDK.
This module provides intelligent alerting, anomaly detection notifications,
and multi-channel alert delivery for enterprise logging systems.
Author: FastAPI Microservices SDK
Version: 1.0.0
"""
import asyncio
import json
import smtplib
import time
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Optional dependencies for notifications
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .config import LoggingConfig
from .exceptions import LoggingError
from .search import SearchQuery, SearchResult, LogSearchEngine, Anomaly, AnomalyType


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    TEAMS = "teams"
    DISCORD = "discord"


class AlertCondition(str, Enum):
    """Alert condition types."""
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"
    PATTERN = "pattern"
    RATE = "rate"
    ABSENCE = "absence"


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    description: str
    condition_type: AlertCondition
    severity: AlertSeverity
    
    # Query configuration
    search_query: SearchQuery
    evaluation_window: int = 300  # seconds
    evaluation_interval: int = 60  # seconds
    
    # Condition parameters
    threshold_value: Optional[float] = None
    threshold_operator: str = "gt"  # gt, lt, gte, lte, eq, ne
    rate_window: int = 300  # seconds for rate calculations
    
    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    notification_template: Optional[str] = None
    
    # Suppression settings
    suppression_window: int = 3600  # seconds
    max_alerts_per_window: int = 5
    
    # Escalation settings
    escalation_rules: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'condition_type': self.condition_type.value,
            'severity': self.severity.value,
            'search_query': {
                'criteria': [(c.field, c.operator.value, c.value) for c in self.search_query.criteria],
                'time_range': self.search_query.time_range,
                'limit': self.search_query.limit
            },
            'evaluation_window': self.evaluation_window,
            'evaluation_interval': self.evaluation_interval,
            'threshold_value': self.threshold_value,
            'threshold_operator': self.threshold_operator,
            'notification_channels': [ch.value for ch in self.notification_channels],
            'suppression_window': self.suppression_window,
            'max_alerts_per_window': self.max_alerts_per_window,
            'tags': self.tags,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str
    
    # Timing
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Context
    triggering_logs: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Notification tracking
    notifications_sent: List[Dict[str, Any]] = field(default_factory=list)
    escalation_level: int = 0
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'status': self.status.value,
            'title': self.title,
            'description': self.description,
            'triggered_at': self.triggered_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'triggering_logs': self.triggering_logs,
            'metrics': self.metrics,
            'notifications_sent': self.notifications_sent,
            'escalation_level': self.escalation_level,
            'tags': self.tags,
            'custom_fields': self.custom_fields
        }


@dataclass
class NotificationConfig:
    """Notification channel configuration."""
    channel: NotificationChannel
    config: Dict[str, Any]
    enabled: bool = True
    
    # Rate limiting
    rate_limit_window: int = 300  # seconds
    max_notifications_per_window: int = 10
    
    # Retry settings
    max_retries: int = 3
    retry_delay: int = 30  # seconds


class AlertManager:
    """Log-based alert management system."""
    
    def __init__(
        self,
        config: LoggingConfig,
        search_engine: LogSearchEngine
    ):
        self.config = config
        self.search_engine = search_engine
        self.logger = logging.getLogger(__name__)
        
        # Alert rules and active alerts
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Notification configurations
        self.notification_configs: Dict[NotificationChannel, NotificationConfig] = {}
        
        # Evaluation state
        self._evaluation_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._alerts_triggered = 0
        self._notifications_sent = 0
        self._false_positives = 0
        
        # Rate limiting tracking
        self._notification_counts: Dict[str, List[datetime]] = {}
        self._alert_counts: Dict[str, List[datetime]] = {}
    
    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule."""
        self.alert_rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
        
        # Start evaluation task if enabled
        if rule.enabled:
            self._start_rule_evaluation(rule)
    
    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule."""
        if rule_name in self.alert_rules:
            # Stop evaluation task
            if rule_name in self._evaluation_tasks:
                self._evaluation_tasks[rule_name].cancel()
                del self._evaluation_tasks[rule_name]
            
            del self.alert_rules[rule_name]
            self.logger.info(f"Removed alert rule: {rule_name}")
    
    def add_notification_config(self, config: NotificationConfig):
        """Add notification configuration."""
        self.notification_configs[config.channel] = config
        self.logger.info(f"Added notification config for {config.channel.value}")
    
    def _start_rule_evaluation(self, rule: AlertRule):
        """Start evaluation task for rule."""
        async def evaluate_rule():
            while not self._shutdown_event.is_set():
                try:
                    await self._evaluate_rule(rule)
                    await asyncio.sleep(rule.evaluation_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error evaluating rule {rule.name}: {e}")
                    await asyncio.sleep(rule.evaluation_interval)
        
        task = asyncio.create_task(evaluate_rule())
        self._evaluation_tasks[rule.name] = task
    
    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate alert rule."""
        try:
            # Check if rule is suppressed
            if self._is_rule_suppressed(rule):
                return
            
            # Execute search query
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(seconds=rule.evaluation_window)
            
            # Update query time range
            query = rule.search_query
            query.time_range = (start_time, end_time)
            
            # Search logs (assuming file-based for now)
            if self.config.file_output and self.config.file_path:
                result = self.search_engine.search(query, self.config.file_path)
            else:
                # Skip if no log source available
                return
            
            # Evaluate condition
            should_alert = self._evaluate_condition(rule, result)
            
            if should_alert:
                await self._trigger_alert(rule, result)
                
        except Exception as e:
            self.logger.error(f"Failed to evaluate rule {rule.name}: {e}")
    
    def _evaluate_condition(self, rule: AlertRule, result: SearchResult) -> bool:
        """Evaluate alert condition."""
        if rule.condition_type == AlertCondition.THRESHOLD:
            value = result.total_count
            return self._check_threshold(value, rule.threshold_value, rule.threshold_operator)
        
        elif rule.condition_type == AlertCondition.RATE:
            # Calculate rate per minute
            rate = result.total_count / (rule.evaluation_window / 60)
            return self._check_threshold(rate, rule.threshold_value, rule.threshold_operator)
        
        elif rule.condition_type == AlertCondition.ABSENCE:
            # Alert if no logs found
            return result.total_count == 0
        
        elif rule.condition_type == AlertCondition.PATTERN:
            # Pattern-based alerting (simplified)
            return result.total_count > 0
        
        return False
    
    def _check_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Check threshold condition."""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "eq":
            return value == threshold
        elif operator == "ne":
            return value != threshold
        return False
    
    def _is_rule_suppressed(self, rule: AlertRule) -> bool:
        """Check if rule is suppressed."""
        rule_key = f"rule_{rule.name}"
        now = datetime.now(timezone.utc)
        
        # Clean old counts
        if rule_key in self._alert_counts:
            cutoff = now - timedelta(seconds=rule.suppression_window)
            self._alert_counts[rule_key] = [
                ts for ts in self._alert_counts[rule_key] if ts > cutoff
            ]
        
        # Check if max alerts reached
        alert_count = len(self._alert_counts.get(rule_key, []))
        return alert_count >= rule.max_alerts_per_window
    
    async def _trigger_alert(self, rule: AlertRule, result: SearchResult):
        """Trigger alert."""
        try:
            # Generate alert ID
            alert_id = f"alert-{rule.name}-{int(time.time())}"
            
            # Create alert
            alert = Alert(
                alert_id=alert_id,
                rule_name=rule.name,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                title=f"Alert: {rule.name}",
                description=rule.description,
                triggered_at=datetime.now(timezone.utc),
                triggering_logs=result.logs[:10],  # Sample logs
                metrics={
                    'log_count': result.total_count,
                    'query_time_ms': result.query_time_ms,
                    'evaluation_window': rule.evaluation_window
                },
                tags=rule.tags
            )
            
            # Store alert
            self.active_alerts[alert_id] = alert
            self._alerts_triggered += 1
            
            # Track alert count for suppression
            rule_key = f"rule_{rule.name}"
            if rule_key not in self._alert_counts:
                self._alert_counts[rule_key] = []
            self._alert_counts[rule_key].append(alert.triggered_at)
            
            # Send notifications
            await self._send_notifications(alert, rule)
            
            self.logger.warning(f"Alert triggered: {alert.title} (ID: {alert_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alert for rule {rule.name}: {e}")
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule):
        """Send notifications for alert."""
        for channel in rule.notification_channels:
            if channel not in self.notification_configs:
                continue
            
            config = self.notification_configs[channel]
            if not config.enabled:
                continue
            
            # Check rate limiting
            if self._is_notification_rate_limited(channel, config):
                continue
            
            try:
                await self._send_notification(alert, channel, config)
                
                # Track notification
                alert.notifications_sent.append({
                    'channel': channel.value,
                    'sent_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'success'
                })
                self._notifications_sent += 1
                
                # Update rate limiting
                self._track_notification(channel)
                
            except Exception as e:
                self.logger.error(f"Failed to send notification via {channel.value}: {e}")
                alert.notifications_sent.append({
                    'channel': channel.value,
                    'sent_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'failed',
                    'error': str(e)
                })
    
    def _is_notification_rate_limited(
        self,
        channel: NotificationChannel,
        config: NotificationConfig
    ) -> bool:
        """Check if notification is rate limited."""
        channel_key = f"notification_{channel.value}"
        now = datetime.now(timezone.utc)
        
        # Clean old counts
        if channel_key in self._notification_counts:
            cutoff = now - timedelta(seconds=config.rate_limit_window)
            self._notification_counts[channel_key] = [
                ts for ts in self._notification_counts[channel_key] if ts > cutoff
            ]
        
        # Check rate limit
        notification_count = len(self._notification_counts.get(channel_key, []))
        return notification_count >= config.max_notifications_per_window
    
    def _track_notification(self, channel: NotificationChannel):
        """Track notification for rate limiting."""
        channel_key = f"notification_{channel.value}"
        if channel_key not in self._notification_counts:
            self._notification_counts[channel_key] = []
        self._notification_counts[channel_key].append(datetime.now(timezone.utc))
    
    async def _send_notification(
        self,
        alert: Alert,
        channel: NotificationChannel,
        config: NotificationConfig
    ):
        """Send notification via specific channel."""
        if channel == NotificationChannel.EMAIL:
            await self._send_email_notification(alert, config)
        elif channel == NotificationChannel.SLACK:
            await self._send_slack_notification(alert, config)
        elif channel == NotificationChannel.WEBHOOK:
            await self._send_webhook_notification(alert, config)
        elif channel == NotificationChannel.PAGERDUTY:
            await self._send_pagerduty_notification(alert, config)
        else:
            self.logger.warning(f"Unsupported notification channel: {channel.value}")
    
    async def _send_email_notification(self, alert: Alert, config: NotificationConfig):
        """Send email notification."""
        email_config = config.config
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = email_config['from_email']
        msg['To'] = ', '.join(email_config['to_emails'])
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
        
        # Create body
        body = f"""
Alert Details:
- Alert ID: {alert.alert_id}
- Rule: {alert.rule_name}
- Severity: {alert.severity.value}
- Triggered: {alert.triggered_at.isoformat()}
- Description: {alert.description}

Metrics:
{json.dumps(alert.metrics, indent=2)}

Triggering Logs:
{json.dumps(alert.triggering_logs[:3], indent=2)}
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            server = smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port'])
            if email_config.get('use_tls'):
                server.starttls()
            if email_config.get('username'):
                server.login(email_config['username'], email_config['password'])
            
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            raise LoggingError(f"Failed to send email: {e}")
    
    async def _send_slack_notification(self, alert: Alert, config: NotificationConfig):
        """Send Slack notification."""
        if not AIOHTTP_AVAILABLE:
            raise LoggingError("aiohttp not available for Slack notifications")
        
        slack_config = config.config
        webhook_url = slack_config['webhook_url']
        
        # Create Slack message
        color = {
            AlertSeverity.LOW: "good",
            AlertSeverity.MEDIUM: "warning", 
            AlertSeverity.HIGH: "danger",
            AlertSeverity.CRITICAL: "danger"
        }.get(alert.severity, "warning")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": alert.title,
                "text": alert.description,
                "fields": [
                    {"title": "Alert ID", "value": alert.alert_id, "short": True},
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Rule", "value": alert.rule_name, "short": True},
                    {"title": "Triggered", "value": alert.triggered_at.isoformat(), "short": True}
                ],
                "footer": "FastAPI Microservices SDK",
                "ts": int(alert.triggered_at.timestamp())
            }]
        }
        
        # Send to Slack
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    raise LoggingError(f"Slack notification failed: {response.status}")
    
    async def _send_webhook_notification(self, alert: Alert, config: NotificationConfig):
        """Send webhook notification."""
        if not AIOHTTP_AVAILABLE:
            raise LoggingError("aiohttp not available for webhook notifications")
        
        webhook_config = config.config
        webhook_url = webhook_config['url']
        
        # Create payload
        payload = {
            "alert": alert.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "fastapi-microservices-sdk"
        }
        
        # Send webhook
        headers = webhook_config.get('headers', {})
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers) as response:
                if response.status not in [200, 201, 202]:
                    raise LoggingError(f"Webhook notification failed: {response.status}")
    
    async def _send_pagerduty_notification(self, alert: Alert, config: NotificationConfig):
        """Send PagerDuty notification."""
        if not AIOHTTP_AVAILABLE:
            raise LoggingError("aiohttp not available for PagerDuty notifications")
        
        pd_config = config.config
        
        # Create PagerDuty event
        payload = {
            "routing_key": pd_config['integration_key'],
            "event_action": "trigger",
            "dedup_key": alert.alert_id,
            "payload": {
                "summary": alert.title,
                "source": "fastapi-microservices-sdk",
                "severity": alert.severity.value,
                "component": alert.rule_name,
                "group": "logging",
                "class": "alert",
                "custom_details": {
                    "alert_id": alert.alert_id,
                    "description": alert.description,
                    "metrics": alert.metrics,
                    "triggered_at": alert.triggered_at.isoformat()
                }
            }
        }
        
        # Send to PagerDuty
        url = "https://events.pagerduty.com/v2/enqueue"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 202:
                    raise LoggingError(f"PagerDuty notification failed: {response.status}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.custom_fields['acknowledged_by'] = acknowledged_by
            
            self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
            alert.custom_fields['resolved_by'] = resolved_by
            
            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]
            
            # Keep only recent history
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            
            self.logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            return True
        return False
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alerting statistics."""
        return {
            'total_rules': len(self.alert_rules),
            'active_alerts': len(self.active_alerts),
            'alerts_triggered': self._alerts_triggered,
            'notifications_sent': self._notifications_sent,
            'false_positives': self._false_positives,
            'notification_channels': len(self.notification_configs),
            'evaluation_tasks': len(self._evaluation_tasks)
        }
    
    async def shutdown(self):
        """Shutdown alert manager."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all evaluation tasks
        for task in self._evaluation_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self._evaluation_tasks:
            await asyncio.gather(*self._evaluation_tasks.values(), return_exceptions=True)
        
        self.logger.info("Alert manager shutdown completed")


# Factory functions
def create_alert_manager(
    config: LoggingConfig,
    search_engine: LogSearchEngine
) -> AlertManager:
    """Create alert manager."""
    return AlertManager(config, search_engine)


def create_alert_rule(
    name: str,
    search_query: SearchQuery,
    condition_type: AlertCondition,
    severity: AlertSeverity,
    **kwargs
) -> AlertRule:
    """Create alert rule."""
    return AlertRule(
        name=name,
        description=kwargs.get('description', f'Alert rule for {name}'),
        condition_type=condition_type,
        severity=severity,
        search_query=search_query,
        **kwargs
    )


def create_notification_config(
    channel: NotificationChannel,
    config: Dict[str, Any],
    **kwargs
) -> NotificationConfig:
    """Create notification configuration."""
    return NotificationConfig(
        channel=channel,
        config=config,
        **kwargs
    )


# Export main classes and functions
__all__ = [
    'AlertSeverity',
    'AlertStatus',
    'NotificationChannel',
    'AlertCondition',
    'AlertRule',
    'Alert',
    'NotificationConfig',
    'AlertManager',
    'create_alert_manager',
    'create_alert_rule',
    'create_notification_config',
]
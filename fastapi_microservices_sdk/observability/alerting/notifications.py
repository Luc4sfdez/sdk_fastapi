"""
Notification System for FastAPI Microservices SDK.

This module provides multi-channel notification capabilities including
email, Slack, PagerDuty, webhooks, and other notification channels.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import logging

# Optional dependencies for notifications
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

from .config import NotificationConfig, NotificationChannel, AlertSeverity
from .exceptions import NotificationError, AlertingError


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    RATE_LIMITED = "rate_limited"


@dataclass
class NotificationMessage:
    """Notification message data."""
    alert_id: str
    title: str
    message: str
    severity: AlertSeverity
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    alert_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'annotations': self.annotations,
            'alert_url': self.alert_url
        }


@dataclass
class NotificationResult:
    """Notification delivery result."""
    success: bool
    status: NotificationStatus
    message: str
    delivery_time: Optional[datetime] = None
    retry_count: int = 0
    error_details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'status': self.status.value,
            'message': self.message,
            'delivery_time': self.delivery_time.isoformat() if self.delivery_time else None,
            'retry_count': self.retry_count,
            'error_details': self.error_details
        }


class BaseNotificationChannel(ABC):
    """Base class for notification channels."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize notification channel."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self._rate_limiter = RateLimiter(
            config.rate_limit_per_minute,
            config.rate_limit_per_hour
        )
    
    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send notification message."""
        pass
    
    def should_send(self, message: NotificationMessage) -> bool:
        """Check if notification should be sent based on filters."""
        # Check if channel is enabled
        if not self.config.enabled:
            return False
        
        # Check severity filter
        if (self.config.severity_filter and 
            message.severity not in self.config.severity_filter):
            return False
        
        # Check label filters
        for label_key, label_value in self.config.label_filters.items():
            if message.labels.get(label_key) != label_value:
                return False
        
        # Check rate limiting
        if not self._rate_limiter.allow_request():
            return False
        
        return True
    
    async def send_with_retry(self, message: NotificationMessage) -> NotificationResult:
        """Send notification with retry logic."""
        last_result = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await self.send_notification(message)
                result.retry_count = attempt
                
                if result.success:
                    return result
                
                last_result = result
                
                # Wait before retry
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay.total_seconds())
                    
            except Exception as e:
                self.logger.error(f"Notification attempt {attempt + 1} failed: {e}")
                last_result = NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    message=f"Attempt {attempt + 1} failed: {str(e)}",
                    retry_count=attempt,
                    error_details=str(e)
                )
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay.total_seconds())
        
        return last_result or NotificationResult(
            success=False,
            status=NotificationStatus.FAILED,
            message="All retry attempts failed"
        )


class EmailNotifier(BaseNotificationChannel):
    """Email notification channel."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize email notifier."""
        super().__init__(config)
        
        if not EMAIL_AVAILABLE:
            raise NotificationError(
                "Email dependencies not available. Install aiosmtplib and email packages.",
                channel_type="email"
            )
        
        # Validate email settings
        required_settings = ['smtp_host', 'smtp_port', 'username', 'password', 'from_email', 'to_emails']
        for setting in required_settings:
            if setting not in config.settings:
                raise NotificationError(
                    f"Missing required email setting: {setting}",
                    channel_type="email",
                    channel_config=setting
                )
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send email notification."""
        try:
            settings = self.config.settings
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings['from_email']
            msg['To'] = ', '.join(settings['to_emails'])
            msg['Subject'] = f"[{message.severity.value.upper()}] {message.title}"
            
            # Create email body
            body = self._create_email_body(message)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            smtp = aiosmtplib.SMTP(
                hostname=settings['smtp_host'],
                port=settings['smtp_port'],
                use_tls=settings.get('use_tls', True)
            )
            
            await smtp.connect()
            await smtp.login(settings['username'], settings['password'])
            await smtp.send_message(msg)
            await smtp.quit()
            
            return NotificationResult(
                success=True,
                status=NotificationStatus.SENT,
                message="Email sent successfully",
                delivery_time=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                message=f"Email delivery failed: {str(e)}",
                error_details=str(e)
            )
    
    def _create_email_body(self, message: NotificationMessage) -> str:
        """Create HTML email body."""
        severity_colors = {
            AlertSeverity.CRITICAL: '#dc3545',
            AlertSeverity.HIGH: '#fd7e14',
            AlertSeverity.MEDIUM: '#ffc107',
            AlertSeverity.LOW: '#28a745',
            AlertSeverity.INFO: '#17a2b8'
        }
        
        color = severity_colors.get(message.severity, '#6c757d')
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    {message.severity.value.upper()} Alert: {message.title}
                </h2>
                <p><strong>Alert ID:</strong> {message.alert_id}</p>
                <p><strong>Timestamp:</strong> {message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Message:</strong></p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                    {message.message}
                </div>
                
                {self._format_labels_html(message.labels) if message.labels else ''}
                {self._format_annotations_html(message.annotations) if message.annotations else ''}
                
                {f'<p><a href="{message.alert_url}" style="color: {color};">View Alert Details</a></p>' if message.alert_url else ''}
            </div>
        </body>
        </html>
        """
    
    def _format_labels_html(self, labels: Dict[str, str]) -> str:
        """Format labels as HTML."""
        if not labels:
            return ""
        
        items = [f"<li><strong>{k}:</strong> {v}</li>" for k, v in labels.items()]
        return f"<p><strong>Labels:</strong></p><ul>{''.join(items)}</ul>"
    
    def _format_annotations_html(self, annotations: Dict[str, str]) -> str:
        """Format annotations as HTML."""
        if not annotations:
            return ""
        
        items = [f"<li><strong>{k}:</strong> {v}</li>" for k, v in annotations.items()]
        return f"<p><strong>Annotations:</strong></p><ul>{''.join(items)}</ul>"


class SlackNotifier(BaseNotificationChannel):
    """Slack notification channel."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize Slack notifier."""
        super().__init__(config)
        
        if not AIOHTTP_AVAILABLE:
            raise NotificationError(
                "HTTP dependencies not available. Install aiohttp package.",
                channel_type="slack"
            )
        
        # Validate Slack settings
        if 'webhook_url' not in config.settings:
            raise NotificationError(
                "Missing required Slack setting: webhook_url",
                channel_type="slack",
                channel_config="webhook_url"
            )
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send Slack notification."""
        try:
            settings = self.config.settings
            
            # Create Slack payload
            payload = self._create_slack_payload(message, settings)
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings['webhook_url'],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return NotificationResult(
                            success=True,
                            status=NotificationStatus.SENT,
                            message="Slack message sent successfully",
                            delivery_time=datetime.now(timezone.utc)
                        )
                    else:
                        error_text = await response.text()
                        return NotificationResult(
                            success=False,
                            status=NotificationStatus.FAILED,
                            message=f"Slack API error: {response.status}",
                            error_details=error_text
                        )
                        
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                message=f"Slack delivery failed: {str(e)}",
                error_details=str(e)
            )
    
    def _create_slack_payload(self, message: NotificationMessage, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create Slack message payload."""
        severity_colors = {
            AlertSeverity.CRITICAL: 'danger',
            AlertSeverity.HIGH: 'warning',
            AlertSeverity.MEDIUM: 'warning',
            AlertSeverity.LOW: 'good',
            AlertSeverity.INFO: '#17a2b8'
        }
        
        color = severity_colors.get(message.severity, '#6c757d')
        
        # Create attachment
        attachment = {
            'color': color,
            'title': f"{message.severity.value.upper()} Alert: {message.title}",
            'text': message.message,
            'fields': [
                {
                    'title': 'Alert ID',
                    'value': message.alert_id,
                    'short': True
                },
                {
                    'title': 'Timestamp',
                    'value': message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'short': True
                }
            ],
            'footer': 'FastAPI Microservices SDK',
            'ts': int(message.timestamp.timestamp())
        }
        
        # Add labels and annotations
        if message.labels:
            labels_text = ', '.join([f"{k}: {v}" for k, v in message.labels.items()])
            attachment['fields'].append({
                'title': 'Labels',
                'value': labels_text,
                'short': False
            })
        
        if message.annotations:
            annotations_text = ', '.join([f"{k}: {v}" for k, v in message.annotations.items()])
            attachment['fields'].append({
                'title': 'Annotations',
                'value': annotations_text,
                'short': False
            })
        
        # Add alert URL if available
        if message.alert_url:
            attachment['title_link'] = message.alert_url
        
        payload = {
            'channel': settings.get('channel', '#alerts'),
            'username': settings.get('username', 'AlertBot'),
            'icon_emoji': settings.get('icon_emoji', ':warning:'),
            'attachments': [attachment]
        }
        
        return payload


class PagerDutyNotifier(BaseNotificationChannel):
    """PagerDuty notification channel."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize PagerDuty notifier."""
        super().__init__(config)
        
        if not AIOHTTP_AVAILABLE:
            raise NotificationError(
                "HTTP dependencies not available. Install aiohttp package.",
                channel_type="pagerduty"
            )
        
        # Validate PagerDuty settings
        if 'integration_key' not in config.settings:
            raise NotificationError(
                "Missing required PagerDuty setting: integration_key",
                channel_type="pagerduty",
                channel_config="integration_key"
            )
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send PagerDuty notification."""
        try:
            settings = self.config.settings
            
            # Create PagerDuty event
            event = self._create_pagerduty_event(message, settings)
            
            # Send to PagerDuty Events API
            url = "https://events.pagerduty.com/v2/enqueue"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=event,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 202:
                        response_data = await response.json()
                        return NotificationResult(
                            success=True,
                            status=NotificationStatus.SENT,
                            message=f"PagerDuty event sent: {response_data.get('dedup_key', 'unknown')}",
                            delivery_time=datetime.now(timezone.utc)
                        )
                    else:
                        error_text = await response.text()
                        return NotificationResult(
                            success=False,
                            status=NotificationStatus.FAILED,
                            message=f"PagerDuty API error: {response.status}",
                            error_details=error_text
                        )
                        
        except Exception as e:
            self.logger.error(f"Failed to send PagerDuty notification: {e}")
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                message=f"PagerDuty delivery failed: {str(e)}",
                error_details=str(e)
            )
    
    def _create_pagerduty_event(self, message: NotificationMessage, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create PagerDuty event payload."""
        severity_mapping = settings.get('severity_mapping', {
            AlertSeverity.CRITICAL: 'critical',
            AlertSeverity.HIGH: 'error',
            AlertSeverity.MEDIUM: 'warning',
            AlertSeverity.LOW: 'info',
            AlertSeverity.INFO: 'info'
        })
        
        pd_severity = severity_mapping.get(message.severity, 'warning')
        
        event = {
            'routing_key': settings['integration_key'],
            'event_action': 'trigger',
            'dedup_key': message.alert_id,
            'payload': {
                'summary': f"{message.title}: {message.message}",
                'severity': pd_severity,
                'source': message.labels.get('instance', 'unknown'),
                'component': message.labels.get('service', 'unknown'),
                'group': message.labels.get('team', 'unknown'),
                'class': message.labels.get('alertname', 'alert'),
                'custom_details': {
                    'alert_id': message.alert_id,
                    'timestamp': message.timestamp.isoformat(),
                    'labels': message.labels,
                    'annotations': message.annotations
                }
            }
        }
        
        if message.alert_url:
            event['links'] = [{
                'href': message.alert_url,
                'text': 'View Alert Details'
            }]
        
        return event


class WebhookNotifier(BaseNotificationChannel):
    """Webhook notification channel."""
    
    def __init__(self, config: NotificationConfig):
        """Initialize webhook notifier."""
        super().__init__(config)
        
        if not AIOHTTP_AVAILABLE:
            raise NotificationError(
                "HTTP dependencies not available. Install aiohttp package.",
                channel_type="webhook"
            )
        
        # Validate webhook settings
        if 'url' not in config.settings:
            raise NotificationError(
                "Missing required webhook setting: url",
                channel_type="webhook",
                channel_config="url"
            )
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send webhook notification."""
        try:
            settings = self.config.settings
            
            # Create webhook payload
            payload = message.to_dict()
            
            # Prepare request
            method = settings.get('method', 'POST').upper()
            headers = settings.get('headers', {'Content-Type': 'application/json'})
            
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    settings['url'],
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if 200 <= response.status < 300:
                        return NotificationResult(
                            success=True,
                            status=NotificationStatus.SENT,
                            message=f"Webhook delivered successfully: {response.status}",
                            delivery_time=datetime.now(timezone.utc)
                        )
                    else:
                        error_text = await response.text()
                        return NotificationResult(
                            success=False,
                            status=NotificationStatus.FAILED,
                            message=f"Webhook error: {response.status}",
                            error_details=error_text
                        )
                        
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                message=f"Webhook delivery failed: {str(e)}",
                error_details=str(e)
            )


class RateLimiter:
    """Rate limiter for notifications."""
    
    def __init__(self, per_minute: int, per_hour: int):
        """Initialize rate limiter."""
        self.per_minute = per_minute
        self.per_hour = per_hour
        
        # Tracking windows
        self._minute_requests: List[float] = []
        self._hour_requests: List[float] = []
    
    def allow_request(self) -> bool:
        """Check if request is allowed."""
        now = time.time()
        
        # Clean old requests
        self._clean_old_requests(now)
        
        # Check limits
        if len(self._minute_requests) >= self.per_minute:
            return False
        
        if len(self._hour_requests) >= self.per_hour:
            return False
        
        # Record request
        self._minute_requests.append(now)
        self._hour_requests.append(now)
        
        return True
    
    def _clean_old_requests(self, now: float):
        """Clean old requests from tracking windows."""
        # Clean minute window
        minute_cutoff = now - 60
        self._minute_requests = [req for req in self._minute_requests if req > minute_cutoff]
        
        # Clean hour window
        hour_cutoff = now - 3600
        self._hour_requests = [req for req in self._hour_requests if req > hour_cutoff]


class NotificationManager:
    """Notification manager for multiple channels."""
    
    def __init__(self):
        """Initialize notification manager."""
        self.logger = logging.getLogger(__name__)
        self._channels: Dict[str, BaseNotificationChannel] = {}
    
    def add_channel(self, name: str, channel: BaseNotificationChannel):
        """Add notification channel."""
        self._channels[name] = channel
        self.logger.info(f"Added notification channel: {name} ({channel.config.channel_type.value})")
    
    def remove_channel(self, name: str):
        """Remove notification channel."""
        if name in self._channels:
            del self._channels[name]
            self.logger.info(f"Removed notification channel: {name}")
    
    def get_channel(self, name: str) -> Optional[BaseNotificationChannel]:
        """Get notification channel by name."""
        return self._channels.get(name)
    
    def list_channels(self) -> List[str]:
        """List all channel names."""
        return list(self._channels.keys())
    
    async def send_notification(
        self,
        message: NotificationMessage,
        channels: Optional[List[str]] = None
    ) -> Dict[str, NotificationResult]:
        """Send notification to specified channels."""
        if channels is None:
            channels = list(self._channels.keys())
        
        results = {}
        tasks = []
        
        for channel_name in channels:
            if channel_name in self._channels:
                channel = self._channels[channel_name]
                
                # Check if channel should send this message
                if channel.should_send(message):
                    task = asyncio.create_task(
                        self._send_to_channel(channel_name, channel, message)
                    )
                    tasks.append((channel_name, task))
                else:
                    results[channel_name] = NotificationResult(
                        success=False,
                        status=NotificationStatus.RATE_LIMITED,
                        message="Message filtered or rate limited"
                    )
        
        # Wait for all notifications to complete
        for channel_name, task in tasks:
            try:
                result = await task
                results[channel_name] = result
            except Exception as e:
                self.logger.error(f"Error sending to channel {channel_name}: {e}")
                results[channel_name] = NotificationResult(
                    success=False,
                    status=NotificationStatus.FAILED,
                    message=f"Channel error: {str(e)}",
                    error_details=str(e)
                )
        
        return results
    
    async def _send_to_channel(
        self,
        channel_name: str,
        channel: BaseNotificationChannel,
        message: NotificationMessage
    ) -> NotificationResult:
        """Send notification to single channel."""
        try:
            return await channel.send_with_retry(message)
        except Exception as e:
            self.logger.error(f"Error in channel {channel_name}: {e}")
            return NotificationResult(
                success=False,
                status=NotificationStatus.FAILED,
                message=f"Channel error: {str(e)}",
                error_details=str(e)
            )
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get notification manager statistics."""
        return {
            'total_channels': len(self._channels),
            'channels': {
                name: {
                    'type': channel.config.channel_type.value,
                    'enabled': channel.config.enabled
                }
                for name, channel in self._channels.items()
            }
        }


def create_notification_manager() -> NotificationManager:
    """Create notification manager."""
    return NotificationManager()


def create_email_notifier(config: NotificationConfig) -> EmailNotifier:
    """Create email notifier."""
    return EmailNotifier(config)


def create_slack_notifier(config: NotificationConfig) -> SlackNotifier:
    """Create Slack notifier."""
    return SlackNotifier(config)


def create_pagerduty_notifier(config: NotificationConfig) -> PagerDutyNotifier:
    """Create PagerDuty notifier."""
    return PagerDutyNotifier(config)


def create_webhook_notifier(config: NotificationConfig) -> WebhookNotifier:
    """Create webhook notifier."""
    return WebhookNotifier(config)


# Export main classes and functions
__all__ = [
    'NotificationStatus',
    'NotificationMessage',
    'NotificationResult',
    'BaseNotificationChannel',
    'EmailNotifier',
    'SlackNotifier',
    'PagerDutyNotifier',
    'WebhookNotifier',
    'RateLimiter',
    'NotificationManager',
    'create_notification_manager',
    'create_email_notifier',
    'create_slack_notifier',
    'create_pagerduty_notifier',
    'create_webhook_notifier',
]
"""
Alerting configuration for FastAPI Microservices SDK.

This module provides configuration classes for the alerting system,
including alert rules, notification channels, and escalation policies.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator, SecretStr
from datetime import timedelta


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


class NotificationChannel(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    SMS = "sms"
    TEAMS = "teams"


class ConditionOperator(str, Enum):
    """Condition operators for alert rules."""
    GREATER_THAN = "gt"
    GREATER_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    REGEX_MATCH = "regex"


class AggregationFunction(str, Enum):
    """Aggregation functions for metrics."""
    AVG = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    RATE = "rate"
    PERCENTILE = "percentile"


@dataclass
class AlertRuleConfig:
    """Alert rule configuration."""
    name: str
    description: str
    metric_name: str
    condition_operator: ConditionOperator
    threshold_value: Union[float, int, str]
    severity: AlertSeverity = AlertSeverity.MEDIUM
    
    # Time-based settings
    evaluation_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    for_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # Aggregation settings
    aggregation_function: AggregationFunction = AggregationFunction.AVG
    aggregation_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # Labels and annotations
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    # Advanced settings
    enabled: bool = True
    group_by: List[str] = field(default_factory=list)
    percentile: Optional[float] = None  # For percentile aggregation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'metric_name': self.metric_name,
            'condition_operator': self.condition_operator.value,
            'threshold_value': self.threshold_value,
            'severity': self.severity.value,
            'evaluation_interval': self.evaluation_interval.total_seconds(),
            'for_duration': self.for_duration.total_seconds(),
            'aggregation_function': self.aggregation_function.value,
            'aggregation_window': self.aggregation_window.total_seconds(),
            'labels': self.labels,
            'annotations': self.annotations,
            'enabled': self.enabled,
            'group_by': self.group_by,
            'percentile': self.percentile
        }


@dataclass
class NotificationConfig:
    """Notification channel configuration."""
    channel_type: NotificationChannel
    name: str
    enabled: bool = True
    
    # Channel-specific settings
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Rate limiting
    rate_limit_per_minute: int = 10
    rate_limit_per_hour: int = 100
    
    # Retry settings
    max_retries: int = 3
    retry_delay: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    
    # Filtering
    severity_filter: List[AlertSeverity] = field(default_factory=list)
    label_filters: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'channel_type': self.channel_type.value,
            'name': self.name,
            'enabled': self.enabled,
            'settings': self.settings,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay.total_seconds(),
            'severity_filter': [s.value for s in self.severity_filter],
            'label_filters': self.label_filters
        }


@dataclass
class EscalationConfig:
    """Escalation policy configuration."""
    name: str
    description: str
    enabled: bool = True
    
    # Escalation levels
    levels: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing settings
    escalation_delay: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    max_escalations: int = 3
    
    # Conditions
    severity_filter: List[AlertSeverity] = field(default_factory=list)
    label_filters: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'enabled': self.enabled,
            'levels': self.levels,
            'escalation_delay': self.escalation_delay.total_seconds(),
            'max_escalations': self.max_escalations,
            'severity_filter': [s.value for s in self.severity_filter],
            'label_filters': self.label_filters
        }


class AlertConfig(BaseModel):
    """Main alerting system configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # Alerting settings
    enabled: bool = Field(True, description="Enable alerting system")
    default_severity: AlertSeverity = Field(AlertSeverity.MEDIUM, description="Default alert severity")
    
    # Evaluation settings
    evaluation_interval: int = Field(60, description="Default evaluation interval in seconds")
    evaluation_timeout: int = Field(30, description="Evaluation timeout in seconds")
    
    # Alert lifecycle
    alert_retention_days: int = Field(30, description="Alert retention period in days")
    auto_resolve_timeout: int = Field(3600, description="Auto-resolve timeout in seconds")
    
    # Grouping and deduplication
    enable_grouping: bool = Field(True, description="Enable alert grouping")
    enable_deduplication: bool = Field(True, description="Enable alert deduplication")
    grouping_window: int = Field(300, description="Grouping window in seconds")
    deduplication_window: int = Field(600, description="Deduplication window in seconds")
    
    # Rate limiting
    global_rate_limit_per_minute: int = Field(100, description="Global rate limit per minute")
    global_rate_limit_per_hour: int = Field(1000, description="Global rate limit per hour")
    
    # Storage settings
    storage_backend: str = Field("memory", description="Storage backend (memory, file, database)")
    storage_path: Optional[str] = Field(None, description="Storage path for file backend")
    database_url: Optional[str] = Field(None, description="Database URL for database backend")
    
    # Integration settings
    metrics_integration: bool = Field(True, description="Enable metrics integration")
    logging_integration: bool = Field(True, description="Enable logging integration")
    tracing_integration: bool = Field(True, description="Enable tracing integration")
    
    # Notification settings
    notification_timeout: int = Field(30, description="Notification timeout in seconds")
    notification_retries: int = Field(3, description="Default notification retries")
    
    # Escalation settings
    enable_escalation: bool = Field(True, description="Enable alert escalation")
    escalation_timeout: int = Field(900, description="Escalation timeout in seconds")
    
    # Maintenance windows
    enable_maintenance_windows: bool = Field(True, description="Enable maintenance windows")
    maintenance_window_buffer: int = Field(300, description="Maintenance window buffer in seconds")
    
    # Security settings
    require_authentication: bool = Field(False, description="Require authentication for alert endpoints")
    allowed_roles: List[str] = Field(default_factory=list, description="Allowed roles for alert access")
    
    # Performance settings
    max_concurrent_evaluations: int = Field(10, description="Maximum concurrent rule evaluations")
    max_concurrent_notifications: int = Field(20, description="Maximum concurrent notifications")
    
    @validator('evaluation_interval')
    def validate_evaluation_interval(cls, v):
        """Validate evaluation interval."""
        if v <= 0:
            raise ValueError('evaluation_interval must be positive')
        return v
    
    @validator('alert_retention_days')
    def validate_retention_days(cls, v):
        """Validate alert retention days."""
        if v <= 0:
            raise ValueError('alert_retention_days must be positive')
        return v
    
    @validator('global_rate_limit_per_minute')
    def validate_rate_limit(cls, v):
        """Validate rate limit."""
        if v <= 0:
            raise ValueError('global_rate_limit_per_minute must be positive')
        return v
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        config = {
            'backend': self.storage_backend,
            'retention_days': self.alert_retention_days
        }
        
        if self.storage_backend == 'file' and self.storage_path:
            config['path'] = self.storage_path
        elif self.storage_backend == 'database' and self.database_url:
            config['url'] = self.database_url
        
        return config
    
    def get_rate_limit_config(self) -> Dict[str, int]:
        """Get rate limiting configuration."""
        return {
            'per_minute': self.global_rate_limit_per_minute,
            'per_hour': self.global_rate_limit_per_hour
        }
    
    def get_integration_config(self) -> Dict[str, bool]:
        """Get integration configuration."""
        return {
            'metrics': self.metrics_integration,
            'logging': self.logging_integration,
            'tracing': self.tracing_integration
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


def create_alert_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> AlertConfig:
    """Create alert configuration with defaults."""
    return AlertConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


def create_alert_rule_config(
    name: str,
    metric_name: str,
    condition_operator: ConditionOperator,
    threshold_value: Union[float, int, str],
    **kwargs
) -> AlertRuleConfig:
    """Create alert rule configuration."""
    return AlertRuleConfig(
        name=name,
        description=kwargs.get('description', f"Alert rule for {metric_name}"),
        metric_name=metric_name,
        condition_operator=condition_operator,
        threshold_value=threshold_value,
        **{k: v for k, v in kwargs.items() if k != 'description'}
    )


def create_notification_config(
    channel_type: NotificationChannel,
    name: str,
    settings: Dict[str, Any],
    **kwargs
) -> NotificationConfig:
    """Create notification configuration."""
    return NotificationConfig(
        channel_type=channel_type,
        name=name,
        settings=settings,
        **kwargs
    )


def create_escalation_config(
    name: str,
    levels: List[Dict[str, Any]],
    **kwargs
) -> EscalationConfig:
    """Create escalation configuration."""
    return EscalationConfig(
        name=name,
        description=kwargs.get('description', f"Escalation policy: {name}"),
        levels=levels,
        **{k: v for k, v in kwargs.items() if k != 'description'}
    )


# Email notification settings helper
def create_email_settings(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    from_email: str,
    to_emails: List[str],
    use_tls: bool = True
) -> Dict[str, Any]:
    """Create email notification settings."""
    return {
        'smtp_host': smtp_host,
        'smtp_port': smtp_port,
        'username': username,
        'password': password,
        'from_email': from_email,
        'to_emails': to_emails,
        'use_tls': use_tls
    }


# Slack notification settings helper
def create_slack_settings(
    webhook_url: str,
    channel: str,
    username: str = "AlertBot",
    icon_emoji: str = ":warning:"
) -> Dict[str, Any]:
    """Create Slack notification settings."""
    return {
        'webhook_url': webhook_url,
        'channel': channel,
        'username': username,
        'icon_emoji': icon_emoji
    }


# PagerDuty notification settings helper
def create_pagerduty_settings(
    integration_key: str,
    severity_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Create PagerDuty notification settings."""
    return {
        'integration_key': integration_key,
        'severity_mapping': severity_mapping or {
            'critical': 'critical',
            'high': 'error',
            'medium': 'warning',
            'low': 'info',
            'info': 'info'
        }
    }


# Webhook notification settings helper
def create_webhook_settings(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """Create webhook notification settings."""
    settings = {
        'url': url,
        'method': method,
        'headers': headers or {'Content-Type': 'application/json'}
    }
    
    if auth_token:
        settings['headers']['Authorization'] = f"Bearer {auth_token}"
    
    return settings


# Export main classes and functions
__all__ = [
    'AlertSeverity',
    'AlertStatus',
    'NotificationChannel',
    'ConditionOperator',
    'AggregationFunction',
    'AlertRuleConfig',
    'NotificationConfig',
    'EscalationConfig',
    'AlertConfig',
    'create_alert_config',
    'create_alert_rule_config',
    'create_notification_config',
    'create_escalation_config',
    'create_email_settings',
    'create_slack_settings',
    'create_pagerduty_settings',
    'create_webhook_settings',
]
"""
Alert Management System for FastAPI Microservices SDK.

This module provides comprehensive alerting capabilities including
rule-based alerting, multiple notification channels, escalation policies,
and alert lifecycle management for enterprise microservices.

Features:
- Rule-based alert engine with complex condition evaluation
- Multiple notification channels (email, Slack, PagerDuty, webhooks)
- Alert escalation policies with time-based triggers
- Alert grouping and deduplication to prevent alert storms
- Alert acknowledgment and resolution tracking
- Integration with observability systems

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    AlertingError,
    AlertRuleError,
    NotificationError,
    EscalationError,
    AlertManagerError
)

from .config import (
    AlertConfig,
    AlertRuleConfig,
    NotificationConfig,
    EscalationConfig,
    create_alert_config
)

from .rules import (
    AlertRule,
    AlertCondition,
    AlertRuleEngine,
    create_alert_rule,
    create_alert_rule_engine
)

from .notifications import (
    NotificationChannel,
    EmailNotifier,
    SlackNotifier,
    PagerDutyNotifier,
    WebhookNotifier,
    NotificationManager,
    create_notification_manager
)

from .escalation import (
    EscalationPolicy,
    EscalationLevel,
    EscalationManager,
    create_escalation_manager
)

from .manager import (
    AlertManager,
    AlertInstance,
    AlertStatus,
    AlertSeverity,
    create_alert_manager
)

from .grouping import (
    AlertGrouper,
    AlertDeduplicator,
    create_alert_grouper
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'AlertingError',
    'AlertRuleError',
    'NotificationError',
    'EscalationError',
    'AlertManagerError',
    
    # Configuration
    'AlertConfig',
    'AlertRuleConfig',
    'NotificationConfig',
    'EscalationConfig',
    'create_alert_config',
    
    # Alert Rules
    'AlertRule',
    'AlertCondition',
    'AlertRuleEngine',
    'create_alert_rule',
    'create_alert_rule_engine',
    
    # Notifications
    'NotificationChannel',
    'EmailNotifier',
    'SlackNotifier',
    'PagerDutyNotifier',
    'WebhookNotifier',
    'NotificationManager',
    'create_notification_manager',
    
    # Escalation
    'EscalationPolicy',
    'EscalationLevel',
    'EscalationManager',
    'create_escalation_manager',
    
    # Alert Management
    'AlertManager',
    'AlertInstance',
    'AlertStatus',
    'AlertSeverity',
    'create_alert_manager',
    
    # Grouping and Deduplication
    'AlertGrouper',
    'AlertDeduplicator',
    'create_alert_grouper',
]


def get_alerting_info() -> dict:
    """Get information about alerting capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Rule-based Alert Engine',
            'Complex Condition Evaluation',
            'Multiple Notification Channels',
            'Alert Escalation Policies',
            'Alert Grouping and Deduplication',
            'Alert Acknowledgment and Resolution',
            'Time-based Triggers',
            'Alert Storm Prevention',
            'Notification Rate Limiting',
            'Alert Lifecycle Management'
        ],
        'notification_channels': [
            'email',
            'slack',
            'pagerduty',
            'webhook',
            'sms',
            'teams'
        ],
        'alert_severities': [
            'critical',
            'high',
            'medium',
            'low',
            'info'
        ],
        'alert_statuses': [
            'active',
            'acknowledged',
            'resolved',
            'suppressed',
            'expired'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Alert Management module loaded")
logger.info("Features: Rule Engine, Multi-channel Notifications, Escalation Policies")
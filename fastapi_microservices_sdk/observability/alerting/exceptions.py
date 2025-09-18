"""
Alerting exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the alerting system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any


class AlertingError(Exception):
    """Base exception for alerting related errors."""
    
    def __init__(
        self,
        message: str,
        alert_operation: Optional[str] = None,
        alert_id: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.alert_operation = alert_operation
        self.alert_id = alert_id
        self.original_error = original_error
        self.context = context or {}
    
    def __str__(self) -> str:
        """String representation of the error."""
        return self.message


class AlertRuleError(AlertingError):
    """Exception raised when alert rule operations fail."""
    
    def __init__(
        self,
        message: str,
        rule_name: Optional[str] = None,
        rule_condition: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="rule_evaluation",
            original_error=original_error,
            context={
                'rule_name': rule_name,
                'rule_condition': rule_condition
            }
        )
        self.rule_name = rule_name
        self.rule_condition = rule_condition


class NotificationError(AlertingError):
    """Exception raised when notification operations fail."""
    
    def __init__(
        self,
        message: str,
        channel_type: Optional[str] = None,
        channel_config: Optional[str] = None,
        recipient: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="notification",
            original_error=original_error,
            context={
                'channel_type': channel_type,
                'channel_config': channel_config,
                'recipient': recipient
            }
        )
        self.channel_type = channel_type
        self.channel_config = channel_config
        self.recipient = recipient


class EscalationError(AlertingError):
    """Exception raised when escalation operations fail."""
    
    def __init__(
        self,
        message: str,
        escalation_policy: Optional[str] = None,
        escalation_level: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="escalation",
            original_error=original_error,
            context={
                'escalation_policy': escalation_policy,
                'escalation_level': escalation_level
            }
        )
        self.escalation_policy = escalation_policy
        self.escalation_level = escalation_level


class AlertManagerError(AlertingError):
    """Exception raised when alert manager operations fail."""
    
    def __init__(
        self,
        message: str,
        manager_operation: Optional[str] = None,
        alert_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="alert_management",
            original_error=original_error,
            context={
                'manager_operation': manager_operation,
                'alert_count': alert_count
            }
        )
        self.manager_operation = manager_operation
        self.alert_count = alert_count


class AlertGroupingError(AlertingError):
    """Exception raised when alert grouping operations fail."""
    
    def __init__(
        self,
        message: str,
        grouping_strategy: Optional[str] = None,
        group_size: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="alert_grouping",
            original_error=original_error,
            context={
                'grouping_strategy': grouping_strategy,
                'group_size': group_size
            }
        )
        self.grouping_strategy = grouping_strategy
        self.group_size = group_size


class AlertDeduplicationError(AlertingError):
    """Exception raised when alert deduplication operations fail."""
    
    def __init__(
        self,
        message: str,
        deduplication_key: Optional[str] = None,
        duplicate_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="alert_deduplication",
            original_error=original_error,
            context={
                'deduplication_key': deduplication_key,
                'duplicate_count': duplicate_count
            }
        )
        self.deduplication_key = deduplication_key
        self.duplicate_count = duplicate_count


class AlertConfigurationError(AlertingError):
    """Exception raised when alert configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        config_value: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            alert_operation="configuration",
            original_error=original_error,
            context={
                'config_field': config_field,
                'config_value': config_value
            }
        )
        self.config_field = config_field
        self.config_value = config_value


# Export all exceptions
__all__ = [
    'AlertingError',
    'AlertRuleError',
    'NotificationError',
    'EscalationError',
    'AlertManagerError',
    'AlertGroupingError',
    'AlertDeduplicationError',
    'AlertConfigurationError',
]
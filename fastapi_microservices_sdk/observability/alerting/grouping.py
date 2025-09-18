"""
Alert Grouping and Deduplication for FastAPI Microservices SDK.

This module provides alert grouping, deduplication, and storm prevention
capabilities to reduce alert noise and improve alert management.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import hashlib
import time
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import AlertSeverity
from .exceptions import AlertGroupingError, AlertDeduplicationError
from .notifications import NotificationMessage


class GroupingStrategy(str, Enum):
    """Alert grouping strategy."""
    BY_LABELS = "by_labels"
    BY_SERVICE = "by_service"
    BY_SEVERITY = "by_severity"
    BY_RULE = "by_rule"
    CUSTOM = "custom"


class DeduplicationStrategy(str, Enum):
    """Alert deduplication strategy."""
    BY_FINGERPRINT = "by_fingerprint"
    BY_CONTENT = "by_content"
    BY_LABELS = "by_labels"
    CUSTOM = "custom"


@dataclass
class AlertGroup:
    """Alert group containing multiple related alerts."""
    group_id: str
    group_key: str
    strategy: GroupingStrategy
    created_at: datetime
    updated_at: datetime
    alerts: List[NotificationMessage] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def add_alert(self, alert: NotificationMessage):
        """Add alert to group."""
        self.alerts.append(alert)
        self.updated_at = datetime.now(timezone.utc)
        
        # Update group labels and annotations
        self._update_group_metadata()
    
    def _update_group_metadata(self):
        """Update group metadata based on alerts."""
        if not self.alerts:
            return
        
        # Merge common labels
        common_labels = {}
        if self.alerts:
            # Start with first alert's labels
            common_labels = dict(self.alerts[0].labels)
            
            # Keep only labels that are common to all alerts
            for alert in self.alerts[1:]:
                common_labels = {
                    k: v for k, v in common_labels.items()
                    if k in alert.labels and alert.labels[k] == v
                }
        
        self.labels = common_labels
        
        # Merge annotations
        all_annotations = {}
        for alert in self.alerts:
            all_annotations.update(alert.annotations)
        
        self.annotations = all_annotations
    
    def get_summary(self) -> Dict[str, Any]:
        """Get group summary."""
        if not self.alerts:
            return {}
        
        severities = [alert.severity for alert in self.alerts]
        severity_counts = {
            severity: severities.count(severity)
            for severity in set(severities)
        }
        
        return {
            'group_id': self.group_id,
            'group_key': self.group_key,
            'strategy': self.strategy.value,
            'alert_count': len(self.alerts),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'severity_counts': {s.value: count for s, count in severity_counts.items()},
            'highest_severity': max(severities, key=lambda s: list(AlertSeverity).index(s)).value,
            'labels': self.labels,
            'annotations': self.annotations
        }
    
    def to_notification_message(self) -> NotificationMessage:
        """Convert group to notification message."""
        if not self.alerts:
            raise AlertGroupingError(
                "Cannot create notification from empty group",
                group_size=0
            )
        
        # Determine group severity (highest)
        severities = [alert.severity for alert in self.alerts]
        group_severity = max(severities, key=lambda s: list(AlertSeverity).index(s))
        
        # Create group message
        alert_count = len(self.alerts)
        title = f"Alert Group: {alert_count} alerts"
        
        if alert_count == 1:
            # Single alert, use original title
            title = self.alerts[0].title
            message = self.alerts[0].message
        else:
            # Multiple alerts, create summary
            message = f"Group of {alert_count} related alerts:\n"
            for i, alert in enumerate(self.alerts[:5], 1):  # Show first 5
                message += f"{i}. {alert.title}\n"
            
            if alert_count > 5:
                message += f"... and {alert_count - 5} more alerts"
        
        return NotificationMessage(
            alert_id=self.group_id,
            title=title,
            message=message,
            severity=group_severity,
            timestamp=self.updated_at,
            labels=self.labels,
            annotations={
                **self.annotations,
                'alert_group': 'true',
                'alert_count': str(alert_count),
                'grouping_strategy': self.strategy.value
            }
        )


@dataclass
class DeduplicationEntry:
    """Deduplication entry for tracking duplicate alerts."""
    fingerprint: str
    first_seen: datetime
    last_seen: datetime
    count: int = 1
    original_alert: Optional[NotificationMessage] = None
    
    def update(self, alert: NotificationMessage):
        """Update deduplication entry with new occurrence."""
        self.last_seen = datetime.now(timezone.utc)
        self.count += 1


class AlertGrouper:
    """Alert grouping system."""
    
    def __init__(
        self,
        grouping_window: timedelta = timedelta(minutes=5),
        max_group_size: int = 100
    ):
        """Initialize alert grouper."""
        self.grouping_window = grouping_window
        self.max_group_size = max_group_size
        self.logger = logging.getLogger(__name__)
        
        # Active groups
        self._groups: Dict[str, AlertGroup] = {}
        self._group_keys: Dict[str, str] = {}  # key -> group_id mapping
        
        # Grouping strategies
        self._strategies: Dict[GroupingStrategy, Callable[[NotificationMessage], str]] = {
            GroupingStrategy.BY_LABELS: self._group_by_labels,
            GroupingStrategy.BY_SERVICE: self._group_by_service,
            GroupingStrategy.BY_SEVERITY: self._group_by_severity,
            GroupingStrategy.BY_RULE: self._group_by_rule
        }
        
        # Custom strategy
        self._custom_strategy: Optional[Callable[[NotificationMessage], str]] = None
    
    def set_custom_strategy(self, strategy: Callable[[NotificationMessage], str]):
        """Set custom grouping strategy."""
        self._custom_strategy = strategy
    
    def add_alert(
        self,
        alert: NotificationMessage,
        strategy: GroupingStrategy = GroupingStrategy.BY_LABELS
    ) -> str:
        """Add alert to appropriate group."""
        try:
            # Generate group key
            if strategy == GroupingStrategy.CUSTOM and self._custom_strategy:
                group_key = self._custom_strategy(alert)
            elif strategy in self._strategies:
                group_key = self._strategies[strategy](alert)
            else:
                raise AlertGroupingError(
                    f"Unknown grouping strategy: {strategy}",
                    grouping_strategy=strategy.value
                )
            
            # Find or create group
            group_id = self._group_keys.get(group_key)
            
            if group_id and group_id in self._groups:
                # Add to existing group
                group = self._groups[group_id]
                
                # Check group size limit
                if len(group.alerts) >= self.max_group_size:
                    self.logger.warning(f"Group {group_id} has reached maximum size")
                    return group_id
                
                group.add_alert(alert)
                
            else:
                # Create new group
                group_id = f"group_{int(time.time())}_{hash(group_key) % 10000}"
                
                group = AlertGroup(
                    group_id=group_id,
                    group_key=group_key,
                    strategy=strategy,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                
                group.add_alert(alert)
                
                self._groups[group_id] = group
                self._group_keys[group_key] = group_id
            
            # Clean up old groups
            self._cleanup_old_groups()
            
            return group_id
            
        except Exception as e:
            self.logger.error(f"Error adding alert to group: {e}")
            raise AlertGroupingError(
                "Failed to add alert to group",
                original_error=e
            )
    
    def get_group(self, group_id: str) -> Optional[AlertGroup]:
        """Get alert group by ID."""
        return self._groups.get(group_id)
    
    def list_groups(self) -> List[AlertGroup]:
        """List all active groups."""
        return list(self._groups.values())
    
    def get_ready_groups(self) -> List[AlertGroup]:
        """Get groups ready for notification (past grouping window)."""
        cutoff_time = datetime.now(timezone.utc) - self.grouping_window
        
        ready_groups = []
        for group in self._groups.values():
            if group.updated_at <= cutoff_time and group.alerts:
                ready_groups.append(group)
        
        return ready_groups
    
    def remove_group(self, group_id: str):
        """Remove group from active groups."""
        if group_id in self._groups:
            group = self._groups[group_id]
            
            # Remove from key mapping
            if group.group_key in self._group_keys:
                del self._group_keys[group.group_key]
            
            # Remove group
            del self._groups[group_id]
    
    def _group_by_labels(self, alert: NotificationMessage) -> str:
        """Group alerts by common labels."""
        # Use specific labels for grouping
        grouping_labels = ['alertname', 'service', 'instance', 'job']
        
        key_parts = []
        for label in grouping_labels:
            if label in alert.labels:
                key_parts.append(f"{label}={alert.labels[label]}")
        
        return "|".join(key_parts) if key_parts else "default"
    
    def _group_by_service(self, alert: NotificationMessage) -> str:
        """Group alerts by service."""
        service = alert.labels.get('service', alert.labels.get('job', 'unknown'))
        return f"service={service}"
    
    def _group_by_severity(self, alert: NotificationMessage) -> str:
        """Group alerts by severity."""
        return f"severity={alert.severity.value}"
    
    def _group_by_rule(self, alert: NotificationMessage) -> str:
        """Group alerts by alert rule."""
        rule_name = alert.labels.get('alertname', alert.labels.get('rule', 'unknown'))
        return f"rule={rule_name}"
    
    def _cleanup_old_groups(self):
        """Clean up old groups."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)  # Keep for 1 hour
        
        expired_groups = [
            group_id for group_id, group in self._groups.items()
            if group.updated_at <= cutoff_time
        ]
        
        for group_id in expired_groups:
            self.remove_group(group_id)
    
    def get_grouper_stats(self) -> Dict[str, Any]:
        """Get grouper statistics."""
        total_alerts = sum(len(group.alerts) for group in self._groups.values())
        
        return {
            'active_groups': len(self._groups),
            'total_alerts': total_alerts,
            'grouping_window': self.grouping_window.total_seconds(),
            'max_group_size': self.max_group_size
        }


class AlertDeduplicator:
    """Alert deduplication system."""
    
    def __init__(
        self,
        deduplication_window: timedelta = timedelta(minutes=10),
        max_entries: int = 10000
    ):
        """Initialize alert deduplicator."""
        self.deduplication_window = deduplication_window
        self.max_entries = max_entries
        self.logger = logging.getLogger(__name__)
        
        # Deduplication entries
        self._entries: Dict[str, DeduplicationEntry] = {}
        
        # Deduplication strategies
        self._strategies: Dict[DeduplicationStrategy, Callable[[NotificationMessage], str]] = {
            DeduplicationStrategy.BY_FINGERPRINT: self._fingerprint_by_content,
            DeduplicationStrategy.BY_CONTENT: self._fingerprint_by_content,
            DeduplicationStrategy.BY_LABELS: self._fingerprint_by_labels
        }
        
        # Custom strategy
        self._custom_strategy: Optional[Callable[[NotificationMessage], str]] = None
    
    def set_custom_strategy(self, strategy: Callable[[NotificationMessage], str]):
        """Set custom deduplication strategy."""
        self._custom_strategy = strategy
    
    def is_duplicate(
        self,
        alert: NotificationMessage,
        strategy: DeduplicationStrategy = DeduplicationStrategy.BY_FINGERPRINT
    ) -> bool:
        """Check if alert is a duplicate."""
        try:
            # Generate fingerprint
            if strategy == DeduplicationStrategy.CUSTOM and self._custom_strategy:
                fingerprint = self._custom_strategy(alert)
            elif strategy in self._strategies:
                fingerprint = self._strategies[strategy](alert)
            else:
                raise AlertDeduplicationError(
                    f"Unknown deduplication strategy: {strategy}",
                    deduplication_key=strategy.value
                )
            
            # Check if we've seen this fingerprint recently
            if fingerprint in self._entries:
                entry = self._entries[fingerprint]
                
                # Check if within deduplication window
                if (datetime.now(timezone.utc) - entry.last_seen) <= self.deduplication_window:
                    # Update entry
                    entry.update(alert)
                    return True
                else:
                    # Outside window, treat as new
                    del self._entries[fingerprint]
            
            # New alert, record it
            self._entries[fingerprint] = DeduplicationEntry(
                fingerprint=fingerprint,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                original_alert=alert
            )
            
            # Clean up old entries
            self._cleanup_old_entries()
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for duplicate: {e}")
            # On error, assume not duplicate to avoid losing alerts
            return False
    
    def get_duplicate_count(self, alert: NotificationMessage) -> int:
        """Get duplicate count for alert."""
        try:
            fingerprint = self._fingerprint_by_content(alert)
            
            if fingerprint in self._entries:
                return self._entries[fingerprint].count
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Error getting duplicate count: {e}")
            return 0
    
    def _fingerprint_by_content(self, alert: NotificationMessage) -> str:
        """Generate fingerprint based on alert content."""
        # Create fingerprint from key alert attributes
        content = f"{alert.title}|{alert.message}|{alert.severity.value}"
        
        # Add sorted labels
        if alert.labels:
            labels_str = "|".join(f"{k}={v}" for k, v in sorted(alert.labels.items()))
            content += f"|{labels_str}"
        
        # Generate hash
        return hashlib.md5(content.encode()).hexdigest()
    
    def _fingerprint_by_labels(self, alert: NotificationMessage) -> str:
        """Generate fingerprint based on alert labels."""
        # Use specific labels for fingerprinting
        fingerprint_labels = ['alertname', 'service', 'instance', 'severity']
        
        content_parts = []
        for label in fingerprint_labels:
            if label == 'severity':
                content_parts.append(f"severity={alert.severity.value}")
            elif label in alert.labels:
                content_parts.append(f"{label}={alert.labels[label]}")
        
        content = "|".join(content_parts)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cleanup_old_entries(self):
        """Clean up old deduplication entries."""
        if len(self._entries) <= self.max_entries:
            return
        
        # Remove oldest entries
        cutoff_time = datetime.now(timezone.utc) - self.deduplication_window
        
        expired_fingerprints = [
            fingerprint for fingerprint, entry in self._entries.items()
            if entry.last_seen <= cutoff_time
        ]
        
        for fingerprint in expired_fingerprints:
            del self._entries[fingerprint]
        
        # If still too many, remove oldest
        if len(self._entries) > self.max_entries:
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: x[1].last_seen
            )
            
            to_remove = len(self._entries) - self.max_entries
            for fingerprint, _ in sorted_entries[:to_remove]:
                del self._entries[fingerprint]
    
    def get_deduplicator_stats(self) -> Dict[str, Any]:
        """Get deduplicator statistics."""
        total_duplicates = sum(entry.count - 1 for entry in self._entries.values())
        
        return {
            'active_entries': len(self._entries),
            'total_duplicates_prevented': total_duplicates,
            'deduplication_window': self.deduplication_window.total_seconds(),
            'max_entries': self.max_entries
        }


def create_alert_grouper(
    grouping_window: timedelta = timedelta(minutes=5),
    max_group_size: int = 100
) -> AlertGrouper:
    """Create alert grouper."""
    return AlertGrouper(grouping_window, max_group_size)


def create_alert_deduplicator(
    deduplication_window: timedelta = timedelta(minutes=10),
    max_entries: int = 10000
) -> AlertDeduplicator:
    """Create alert deduplicator."""
    return AlertDeduplicator(deduplication_window, max_entries)


# Export main classes and functions
__all__ = [
    'GroupingStrategy',
    'DeduplicationStrategy',
    'AlertGroup',
    'DeduplicationEntry',
    'AlertGrouper',
    'AlertDeduplicator',
    'create_alert_grouper',
    'create_alert_deduplicator',
]
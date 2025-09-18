"""
Alert Escalation System for FastAPI Microservices SDK.

This module provides alert escalation policies, time-based triggers,
and escalation management for the alerting system.

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

from .config import EscalationConfig, AlertSeverity
from .exceptions import EscalationError, AlertingError
from .notifications import NotificationMessage, NotificationManager


class EscalationStatus(str, Enum):
    """Escalation status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class EscalationLevel:
    """Escalation level definition."""
    level: int
    delay: timedelta
    notification_channels: List[str]
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'level': self.level,
            'delay': self.delay.total_seconds(),
            'notification_channels': self.notification_channels,
            'conditions': self.conditions
        }


@dataclass
class EscalationInstance:
    """Active escalation instance."""
    escalation_id: str
    alert_id: str
    policy_name: str
    created_at: datetime
    current_level: int = 0
    status: EscalationStatus = EscalationStatus.PENDING
    next_escalation_at: Optional[datetime] = None
    completed_levels: List[int] = field(default_factory=list)
    failed_levels: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'escalation_id': self.escalation_id,
            'alert_id': self.alert_id,
            'policy_name': self.policy_name,
            'created_at': self.created_at.isoformat(),
            'current_level': self.current_level,
            'status': self.status.value,
            'next_escalation_at': self.next_escalation_at.isoformat() if self.next_escalation_at else None,
            'completed_levels': self.completed_levels,
            'failed_levels': self.failed_levels
        }


class EscalationPolicy:
    """Escalation policy with multiple levels."""
    
    def __init__(self, config: EscalationConfig):
        """Initialize escalation policy."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Parse escalation levels
        self.levels = self._parse_levels(config.levels)
        
        # Validation
        if not self.levels:
            raise EscalationError(
                f"Escalation policy {config.name} has no levels defined",
                escalation_policy=config.name
            )
    
    def _parse_levels(self, level_configs: List[Dict[str, Any]]) -> List[EscalationLevel]:
        """Parse escalation level configurations."""
        levels = []
        
        for i, level_config in enumerate(level_configs):
            try:
                level = EscalationLevel(
                    level=level_config.get('level', i + 1),
                    delay=timedelta(seconds=level_config.get('delay', self.config.escalation_delay.total_seconds())),
                    notification_channels=level_config.get('notification_channels', []),
                    conditions=level_config.get('conditions', {})
                )
                levels.append(level)
                
            except Exception as e:
                raise EscalationError(
                    f"Invalid escalation level configuration at index {i}",
                    escalation_policy=self.config.name,
                    escalation_level=i,
                    original_error=e
                )
        
        # Sort levels by level number
        levels.sort(key=lambda x: x.level)
        return levels
    
    def should_escalate(self, message: NotificationMessage) -> bool:
        """Check if alert should be escalated."""
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
        
        return True
    
    def get_next_level(self, current_level: int) -> Optional[EscalationLevel]:
        """Get next escalation level."""
        for level in self.levels:
            if level.level > current_level:
                return level
        return None
    
    def get_level(self, level_number: int) -> Optional[EscalationLevel]:
        """Get escalation level by number."""
        for level in self.levels:
            if level.level == level_number:
                return level
        return None
    
    def get_max_level(self) -> int:
        """Get maximum escalation level."""
        return max(level.level for level in self.levels) if self.levels else 0


class EscalationManager:
    """Escalation manager for handling alert escalations."""
    
    def __init__(self, notification_manager: NotificationManager):
        """Initialize escalation manager."""
        self.notification_manager = notification_manager
        self.logger = logging.getLogger(__name__)
        
        # Policies and instances
        self._policies: Dict[str, EscalationPolicy] = {}
        self._active_escalations: Dict[str, EscalationInstance] = {}
        
        # Background task
        self._running = False
        self._escalation_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._escalation_callbacks: List[Callable[[EscalationInstance, EscalationLevel], None]] = []
    
    def add_policy(self, policy: EscalationPolicy):
        """Add escalation policy."""
        self._policies[policy.config.name] = policy
        self.logger.info(f"Added escalation policy: {policy.config.name}")
    
    def remove_policy(self, policy_name: str):
        """Remove escalation policy."""
        if policy_name in self._policies:
            del self._policies[policy_name]
            self.logger.info(f"Removed escalation policy: {policy_name}")
    
    def get_policy(self, policy_name: str) -> Optional[EscalationPolicy]:
        """Get escalation policy by name."""
        return self._policies.get(policy_name)
    
    def list_policies(self) -> List[EscalationPolicy]:
        """List all escalation policies."""
        return list(self._policies.values())
    
    def add_escalation_callback(self, callback: Callable[[EscalationInstance, EscalationLevel], None]):
        """Add callback for escalation events."""
        self._escalation_callbacks.append(callback)
    
    async def start_escalation(
        self,
        alert_id: str,
        message: NotificationMessage,
        policy_name: Optional[str] = None
    ) -> Optional[str]:
        """Start escalation for alert."""
        try:
            # Find applicable policy
            policy = None
            
            if policy_name:
                policy = self._policies.get(policy_name)
                if not policy:
                    raise EscalationError(
                        f"Escalation policy not found: {policy_name}",
                        escalation_policy=policy_name
                    )
            else:
                # Find first matching policy
                for pol in self._policies.values():
                    if pol.should_escalate(message):
                        policy = pol
                        break
            
            if not policy:
                self.logger.debug(f"No escalation policy found for alert {alert_id}")
                return None
            
            # Create escalation instance
            escalation_id = f"esc_{alert_id}_{int(time.time())}"
            
            instance = EscalationInstance(
                escalation_id=escalation_id,
                alert_id=alert_id,
                policy_name=policy.config.name,
                created_at=datetime.now(timezone.utc)
            )
            
            # Schedule first escalation
            first_level = policy.get_next_level(0)
            if first_level:
                instance.next_escalation_at = instance.created_at + first_level.delay
                instance.status = EscalationStatus.ACTIVE
            else:
                instance.status = EscalationStatus.COMPLETED
            
            self._active_escalations[escalation_id] = instance
            
            self.logger.info(f"Started escalation {escalation_id} for alert {alert_id} using policy {policy.config.name}")
            
            return escalation_id
            
        except Exception as e:
            self.logger.error(f"Failed to start escalation for alert {alert_id}: {e}")
            raise EscalationError(
                f"Failed to start escalation for alert {alert_id}",
                original_error=e
            )
    
    async def cancel_escalation(self, escalation_id: str):
        """Cancel active escalation."""
        if escalation_id in self._active_escalations:
            instance = self._active_escalations[escalation_id]
            instance.status = EscalationStatus.CANCELLED
            
            self.logger.info(f"Cancelled escalation {escalation_id}")
    
    async def acknowledge_escalation(self, escalation_id: str):
        """Acknowledge escalation (stops further escalation)."""
        if escalation_id in self._active_escalations:
            instance = self._active_escalations[escalation_id]
            instance.status = EscalationStatus.COMPLETED
            
            self.logger.info(f"Acknowledged escalation {escalation_id}")
    
    def get_escalation(self, escalation_id: str) -> Optional[EscalationInstance]:
        """Get escalation instance by ID."""
        return self._active_escalations.get(escalation_id)
    
    def list_active_escalations(self) -> List[EscalationInstance]:
        """List all active escalations."""
        return [
            instance for instance in self._active_escalations.values()
            if instance.status == EscalationStatus.ACTIVE
        ]
    
    async def start(self):
        """Start escalation manager."""
        if self._running:
            return
        
        self._running = True
        self._escalation_task = asyncio.create_task(self._escalation_loop())
        self.logger.info("Escalation manager started")
    
    async def stop(self):
        """Stop escalation manager."""
        if not self._running:
            return
        
        self._running = False
        
        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Escalation manager stopped")
    
    async def _escalation_loop(self):
        """Main escalation processing loop."""
        while self._running:
            try:
                await self._process_escalations()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in escalation loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _process_escalations(self):
        """Process pending escalations."""
        now = datetime.now(timezone.utc)
        
        for escalation_id, instance in list(self._active_escalations.items()):
            try:
                if (instance.status == EscalationStatus.ACTIVE and
                    instance.next_escalation_at and
                    now >= instance.next_escalation_at):
                    
                    await self._execute_escalation(instance)
                    
                # Clean up completed/cancelled escalations
                elif instance.status in [EscalationStatus.COMPLETED, EscalationStatus.CANCELLED]:
                    # Keep for a while for audit purposes
                    if (now - instance.created_at).total_seconds() > 3600:  # 1 hour
                        del self._active_escalations[escalation_id]
                        
            except Exception as e:
                self.logger.error(f"Error processing escalation {escalation_id}: {e}")
                instance.status = EscalationStatus.FAILED
    
    async def _execute_escalation(self, instance: EscalationInstance):
        """Execute escalation level."""
        try:
            policy = self._policies.get(instance.policy_name)
            if not policy:
                self.logger.error(f"Policy not found for escalation {instance.escalation_id}")
                instance.status = EscalationStatus.FAILED
                return
            
            # Get next level to execute
            next_level = policy.get_next_level(instance.current_level)
            if not next_level:
                instance.status = EscalationStatus.COMPLETED
                return
            
            self.logger.info(f"Executing escalation level {next_level.level} for {instance.escalation_id}")
            
            # Create escalation message
            message = NotificationMessage(
                alert_id=instance.alert_id,
                title=f"ESCALATED: Alert {instance.alert_id}",
                message=f"Alert has been escalated to level {next_level.level}",
                severity=AlertSeverity.HIGH,  # Escalated alerts are high severity
                timestamp=datetime.now(timezone.utc),
                labels={'escalation_level': str(next_level.level)},
                annotations={'escalation_policy': policy.config.name}
            )
            
            # Send notifications to escalation channels
            if next_level.notification_channels:
                results = await self.notification_manager.send_notification(
                    message,
                    next_level.notification_channels
                )
                
                # Check if any notifications succeeded
                success = any(result.success for result in results.values())
                
                if success:
                    instance.completed_levels.append(next_level.level)
                else:
                    instance.failed_levels.append(next_level.level)
                    self.logger.warning(f"All notifications failed for escalation level {next_level.level}")
            
            # Update instance state
            instance.current_level = next_level.level
            
            # Schedule next escalation
            next_next_level = policy.get_next_level(next_level.level)
            if next_next_level and instance.current_level < policy.config.max_escalations:
                instance.next_escalation_at = datetime.now(timezone.utc) + next_next_level.delay
            else:
                instance.status = EscalationStatus.COMPLETED
                instance.next_escalation_at = None
            
            # Trigger callbacks
            for callback in self._escalation_callbacks:
                try:
                    callback(instance, next_level)
                except Exception as e:
                    self.logger.error(f"Error in escalation callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error executing escalation {instance.escalation_id}: {e}")
            instance.status = EscalationStatus.FAILED
            instance.failed_levels.append(instance.current_level + 1)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get escalation manager statistics."""
        active_count = len([
            instance for instance in self._active_escalations.values()
            if instance.status == EscalationStatus.ACTIVE
        ])
        
        completed_count = len([
            instance for instance in self._active_escalations.values()
            if instance.status == EscalationStatus.COMPLETED
        ])
        
        failed_count = len([
            instance for instance in self._active_escalations.values()
            if instance.status == EscalationStatus.FAILED
        ])
        
        return {
            'total_policies': len(self._policies),
            'active_escalations': active_count,
            'completed_escalations': completed_count,
            'failed_escalations': failed_count,
            'running': self._running
        }


def create_escalation_policy(config: EscalationConfig) -> EscalationPolicy:
    """Create escalation policy from configuration."""
    return EscalationPolicy(config)


def create_escalation_manager(notification_manager: NotificationManager) -> EscalationManager:
    """Create escalation manager."""
    return EscalationManager(notification_manager)


# Export main classes and functions
__all__ = [
    'EscalationStatus',
    'EscalationLevel',
    'EscalationInstance',
    'EscalationPolicy',
    'EscalationManager',
    'create_escalation_policy',
    'create_escalation_manager',
]
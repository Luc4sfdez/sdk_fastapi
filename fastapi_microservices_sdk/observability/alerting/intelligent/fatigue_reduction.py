"""
Alert Fatigue Reduction System for FastAPI Microservices SDK.

This module provides intelligent alert filtering and fatigue reduction
to minimize alert noise and improve alert effectiveness.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import IntelligentAlertingConfig, FilteringStrategy
from .exceptions import FatigueReductionError
from ..notifications import NotificationMessage
from ..config import AlertSeverity


class FatigueLevel(str, Enum):
    """Alert fatigue level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FatigueMetrics:
    """Alert fatigue metrics."""
    total_alerts: int
    filtered_alerts: int
    fatigue_score: float
    fatigue_level: FatigueLevel
    alert_frequency: float  # alerts per hour
    duplicate_rate: float
    acknowledgment_rate: float
    resolution_time_avg: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_alerts': self.total_alerts,
            'filtered_alerts': self.filtered_alerts,
            'fatigue_score': self.fatigue_score,
            'fatigue_level': self.fatigue_level.value,
            'alert_frequency': self.alert_frequency,
            'duplicate_rate': self.duplicate_rate,
            'acknowledgment_rate': self.acknowledgment_rate,
            'resolution_time_avg': self.resolution_time_avg
        }


@dataclass
class FilteringRule:
    """Alert filtering rule."""
    name: str
    strategy: FilteringStrategy
    conditions: Dict[str, Any]
    enabled: bool = True
    priority: int = 1  # Higher priority = applied first
    
    def matches(self, alert: NotificationMessage) -> bool:
        """Check if alert matches filtering rule."""
        try:
            if not self.enabled:
                return False
            
            # Check conditions
            for condition_key, condition_value in self.conditions.items():
                if condition_key == 'severity':
                    if alert.severity.value != condition_value:
                        return False
                elif condition_key == 'labels':
                    for label_key, label_value in condition_value.items():
                        if alert.labels.get(label_key) != label_value:
                            return False
                elif condition_key == 'frequency_threshold':
                    # This would be checked by the fatigue analyzer
                    continue
                elif condition_key == 'similarity_threshold':
                    # This would be checked by similarity analysis
                    continue
            
            return True
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error matching filtering rule {self.name}: {e}")
            return False
"""
Alert Rules Engine for FastAPI Microservices SDK.

This module provides alert rule evaluation, condition checking,
and rule management capabilities for the alerting system.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import re
import time
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import (
    AlertRuleConfig,
    AlertSeverity,
    ConditionOperator,
    AggregationFunction
)
from .exceptions import AlertRuleError, AlertingError


class AlertConditionResult(str, Enum):
    """Alert condition evaluation result."""
    TRUE = "true"
    FALSE = "false"
    NO_DATA = "no_data"
    ERROR = "error"


@dataclass
class MetricDataPoint:
    """Metric data point for rule evaluation."""
    timestamp: datetime
    value: Union[float, int, str]
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertCondition:
    """Alert condition definition."""
    metric_name: str
    operator: ConditionOperator
    threshold: Union[float, int, str]
    aggregation: AggregationFunction = AggregationFunction.AVG
    window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    group_by: List[str] = field(default_factory=list)
    percentile: Optional[float] = None
    
    def evaluate(self, data_points: List[MetricDataPoint]) -> AlertConditionResult:
        """Evaluate condition against data points."""
        try:
            if not data_points:
                return AlertConditionResult.NO_DATA
            
            # Apply aggregation
            aggregated_value = self._apply_aggregation(data_points)
            
            if aggregated_value is None:
                return AlertConditionResult.NO_DATA
            
            # Evaluate condition
            return self._evaluate_condition(aggregated_value)
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error evaluating condition: {e}")
            return AlertConditionResult.ERROR
    
    def _apply_aggregation(self, data_points: List[MetricDataPoint]) -> Optional[Union[float, int, str]]:
        """Apply aggregation function to data points."""
        try:
            # Filter data points by time window
            cutoff_time = datetime.now(timezone.utc) - self.window
            filtered_points = [
                dp for dp in data_points
                if dp.timestamp >= cutoff_time
            ]
            
            if not filtered_points:
                return None
            
            # Extract numeric values
            numeric_values = []
            string_values = []
            
            for dp in filtered_points:
                if isinstance(dp.value, (int, float)):
                    numeric_values.append(dp.value)
                else:
                    string_values.append(str(dp.value))
            
            # Apply aggregation based on type
            if self.aggregation in [AggregationFunction.AVG, AggregationFunction.SUM, 
                                   AggregationFunction.MIN, AggregationFunction.MAX,
                                   AggregationFunction.PERCENTILE]:
                if not numeric_values:
                    return None
                
                if self.aggregation == AggregationFunction.AVG:
                    return sum(numeric_values) / len(numeric_values)
                elif self.aggregation == AggregationFunction.SUM:
                    return sum(numeric_values)
                elif self.aggregation == AggregationFunction.MIN:
                    return min(numeric_values)
                elif self.aggregation == AggregationFunction.MAX:
                    return max(numeric_values)
                elif self.aggregation == AggregationFunction.PERCENTILE:
                    if self.percentile is None:
                        return None
                    sorted_values = sorted(numeric_values)
                    index = int((self.percentile / 100) * len(sorted_values))
                    return sorted_values[min(index, len(sorted_values) - 1)]
            
            elif self.aggregation == AggregationFunction.COUNT:
                return len(filtered_points)
            
            elif self.aggregation == AggregationFunction.RATE:
                if len(filtered_points) < 2:
                    return None
                
                # Calculate rate per second
                time_span = (filtered_points[-1].timestamp - filtered_points[0].timestamp).total_seconds()
                if time_span <= 0:
                    return None
                
                return len(filtered_points) / time_span
            
            return None
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error applying aggregation: {e}")
            return None
    
    def _evaluate_condition(self, value: Union[float, int, str]) -> AlertConditionResult:
        """Evaluate condition against aggregated value."""
        try:
            if self.operator == ConditionOperator.GREATER_THAN:
                return AlertConditionResult.TRUE if value > self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.GREATER_EQUAL:
                return AlertConditionResult.TRUE if value >= self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.LESS_THAN:
                return AlertConditionResult.TRUE if value < self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.LESS_EQUAL:
                return AlertConditionResult.TRUE if value <= self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.EQUAL:
                return AlertConditionResult.TRUE if value == self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.NOT_EQUAL:
                return AlertConditionResult.TRUE if value != self.threshold else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.CONTAINS:
                return AlertConditionResult.TRUE if str(self.threshold) in str(value) else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.NOT_CONTAINS:
                return AlertConditionResult.TRUE if str(self.threshold) not in str(value) else AlertConditionResult.FALSE
            elif self.operator == ConditionOperator.REGEX_MATCH:
                pattern = re.compile(str(self.threshold))
                return AlertConditionResult.TRUE if pattern.search(str(value)) else AlertConditionResult.FALSE
            
            return AlertConditionResult.FALSE
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error evaluating condition: {e}")
            return AlertConditionResult.ERROR


@dataclass
class AlertRuleState:
    """Alert rule evaluation state."""
    rule_name: str
    last_evaluation: Optional[datetime] = None
    last_result: Optional[AlertConditionResult] = None
    consecutive_true_count: int = 0
    consecutive_false_count: int = 0
    firing_since: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    evaluation_count: int = 0
    error_count: int = 0


class AlertRule:
    """Alert rule with condition evaluation."""
    
    def __init__(self, config: AlertRuleConfig):
        """Initialize alert rule."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create condition from config
        self.condition = AlertCondition(
            metric_name=config.metric_name,
            operator=config.condition_operator,
            threshold=config.threshold_value,
            aggregation=config.aggregation_function,
            window=config.aggregation_window,
            group_by=config.group_by,
            percentile=config.percentile
        )
        
        # Rule state
        self.state = AlertRuleState(rule_name=config.name)
        
        # Metrics data source (to be set by rule engine)
        self._data_source: Optional[Callable[[str], List[MetricDataPoint]]] = None
    
    def set_data_source(self, data_source: Callable[[str], List[MetricDataPoint]]):
        """Set data source for metric retrieval."""
        self._data_source = data_source
    
    async def evaluate(self) -> AlertConditionResult:
        """Evaluate alert rule."""
        try:
            if not self.config.enabled:
                return AlertConditionResult.FALSE
            
            # Get metric data
            if not self._data_source:
                raise AlertRuleError(
                    "No data source configured for rule",
                    rule_name=self.config.name
                )
            
            data_points = self._data_source(self.config.metric_name)
            
            # Evaluate condition
            result = self.condition.evaluate(data_points)
            
            # Update state
            self._update_state(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error evaluating rule {self.config.name}: {e}")
            self.state.error_count += 1
            raise AlertRuleError(
                f"Failed to evaluate rule {self.config.name}",
                rule_name=self.config.name,
                original_error=e
            )
    
    def _update_state(self, result: AlertConditionResult):
        """Update rule evaluation state."""
        now = datetime.now(timezone.utc)
        
        self.state.last_evaluation = now
        self.state.last_result = result
        self.state.evaluation_count += 1
        
        if result == AlertConditionResult.TRUE:
            self.state.consecutive_true_count += 1
            self.state.consecutive_false_count = 0
            
            # Check if rule should start firing
            if (self.state.consecutive_true_count == 1 and 
                self.state.firing_since is None):
                self.state.firing_since = now
                
        elif result == AlertConditionResult.FALSE:
            self.state.consecutive_false_count += 1
            self.state.consecutive_true_count = 0
            
            # Check if rule should stop firing
            if self.state.firing_since is not None:
                self.state.resolved_at = now
                self.state.firing_since = None
        
        # Handle NO_DATA and ERROR cases
        elif result in [AlertConditionResult.NO_DATA, AlertConditionResult.ERROR]:
            # Reset consecutive counts but don't change firing state
            self.state.consecutive_true_count = 0
            self.state.consecutive_false_count = 0
    
    def is_firing(self) -> bool:
        """Check if rule is currently firing."""
        if not self.state.firing_since:
            return False
        
        # Check if rule has been firing long enough
        firing_duration = datetime.now(timezone.utc) - self.state.firing_since
        return firing_duration >= self.config.for_duration
    
    def should_alert(self) -> bool:
        """Check if rule should trigger an alert."""
        return (
            self.config.enabled and
            self.is_firing() and
            self.state.last_result == AlertConditionResult.TRUE
        )
    
    def get_alert_data(self) -> Dict[str, Any]:
        """Get alert data for notification."""
        return {
            'rule_name': self.config.name,
            'description': self.config.description,
            'metric_name': self.config.metric_name,
            'severity': self.config.severity.value,
            'threshold': self.config.threshold_value,
            'operator': self.config.condition_operator.value,
            'labels': self.config.labels,
            'annotations': self.config.annotations,
            'firing_since': self.state.firing_since.isoformat() if self.state.firing_since else None,
            'evaluation_count': self.state.evaluation_count,
            'last_evaluation': self.state.last_evaluation.isoformat() if self.state.last_evaluation else None
        }


class AlertRuleEngine:
    """Alert rule evaluation engine."""
    
    def __init__(self, evaluation_interval: timedelta = timedelta(minutes=1)):
        """Initialize rule engine."""
        self.evaluation_interval = evaluation_interval
        self.logger = logging.getLogger(__name__)
        
        # Rules storage
        self._rules: Dict[str, AlertRule] = {}
        self._data_sources: Dict[str, Callable[[str], List[MetricDataPoint]]] = {}
        
        # Engine state
        self._running = False
        self._evaluation_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._alert_callbacks: List[Callable[[AlertRule], None]] = []
        self._resolve_callbacks: List[Callable[[AlertRule], None]] = []
    
    def add_rule(self, rule: AlertRule):
        """Add alert rule to engine."""
        try:
            # Set data source if available
            if rule.config.metric_name in self._data_sources:
                rule.set_data_source(self._data_sources[rule.config.metric_name])
            
            self._rules[rule.config.name] = rule
            self.logger.info(f"Added alert rule: {rule.config.name}")
            
        except Exception as e:
            raise AlertRuleError(
                f"Failed to add rule {rule.config.name}",
                rule_name=rule.config.name,
                original_error=e
            )
    
    def remove_rule(self, rule_name: str):
        """Remove alert rule from engine."""
        if rule_name in self._rules:
            del self._rules[rule_name]
            self.logger.info(f"Removed alert rule: {rule_name}")
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """Get alert rule by name."""
        return self._rules.get(rule_name)
    
    def list_rules(self) -> List[AlertRule]:
        """List all alert rules."""
        return list(self._rules.values())
    
    def set_data_source(self, metric_name: str, data_source: Callable[[str], List[MetricDataPoint]]):
        """Set data source for metric."""
        self._data_sources[metric_name] = data_source
        
        # Update existing rules
        for rule in self._rules.values():
            if rule.config.metric_name == metric_name:
                rule.set_data_source(data_source)
    
    def add_alert_callback(self, callback: Callable[[AlertRule], None]):
        """Add callback for new alerts."""
        self._alert_callbacks.append(callback)
    
    def add_resolve_callback(self, callback: Callable[[AlertRule], None]):
        """Add callback for resolved alerts."""
        self._resolve_callbacks.append(callback)
    
    async def start(self):
        """Start rule evaluation engine."""
        if self._running:
            return
        
        self._running = True
        self._evaluation_task = asyncio.create_task(self._evaluation_loop())
        self.logger.info("Alert rule engine started")
    
    async def stop(self):
        """Stop rule evaluation engine."""
        if not self._running:
            return
        
        self._running = False
        
        if self._evaluation_task:
            self._evaluation_task.cancel()
            try:
                await self._evaluation_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Alert rule engine stopped")
    
    async def _evaluation_loop(self):
        """Main evaluation loop."""
        while self._running:
            try:
                await self._evaluate_all_rules()
                await asyncio.sleep(self.evaluation_interval.total_seconds())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in evaluation loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _evaluate_all_rules(self):
        """Evaluate all rules."""
        evaluation_tasks = []
        
        for rule in self._rules.values():
            if rule.config.enabled:
                task = asyncio.create_task(self._evaluate_rule(rule))
                evaluation_tasks.append(task)
        
        if evaluation_tasks:
            await asyncio.gather(*evaluation_tasks, return_exceptions=True)
    
    async def _evaluate_rule(self, rule: AlertRule):
        """Evaluate single rule."""
        try:
            # Store previous firing state
            was_firing = rule.is_firing()
            
            # Evaluate rule
            result = await rule.evaluate()
            
            # Check for state changes
            is_firing = rule.is_firing()
            
            # Trigger callbacks
            if not was_firing and is_firing:
                # New alert
                for callback in self._alert_callbacks:
                    try:
                        callback(rule)
                    except Exception as e:
                        self.logger.error(f"Error in alert callback: {e}")
            
            elif was_firing and not is_firing:
                # Resolved alert
                for callback in self._resolve_callbacks:
                    try:
                        callback(rule)
                    except Exception as e:
                        self.logger.error(f"Error in resolve callback: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error evaluating rule {rule.config.name}: {e}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_rules = len(self._rules)
        enabled_rules = sum(1 for rule in self._rules.values() if rule.config.enabled)
        firing_rules = sum(1 for rule in self._rules.values() if rule.is_firing())
        
        return {
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'firing_rules': firing_rules,
            'running': self._running,
            'evaluation_interval': self.evaluation_interval.total_seconds(),
            'data_sources': len(self._data_sources)
        }


def create_alert_rule(config: AlertRuleConfig) -> AlertRule:
    """Create alert rule from configuration."""
    return AlertRule(config)


def create_alert_rule_engine(
    evaluation_interval: timedelta = timedelta(minutes=1)
) -> AlertRuleEngine:
    """Create alert rule engine."""
    return AlertRuleEngine(evaluation_interval)


# Export main classes and functions
__all__ = [
    'AlertConditionResult',
    'MetricDataPoint',
    'AlertCondition',
    'AlertRuleState',
    'AlertRule',
    'AlertRuleEngine',
    'create_alert_rule',
    'create_alert_rule_engine',
]
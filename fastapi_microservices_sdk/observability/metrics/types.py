"""
Metric types and value containers.

This module defines the core metric types (Counter, Gauge, Histogram, Summary)
and their associated value containers and operations.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from .exceptions import MetricValidationError, MetricsError


class MetricType(Enum):
    """Types of metrics supported by the system."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """Container for metric values with metadata."""
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not isinstance(self.value, (int, float)):
            raise MetricValidationError(
                message="Metric value must be numeric",
                validation_rule="numeric_value"
            )


class BaseMetric(ABC):
    """Base class for all metric types."""
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        unit: str = ""
    ):
        self.name = name
        self.description = description
        self.labels = labels or []
        self.unit = unit
        self.created_at = time.time()
        self._lock = threading.RLock()
        
        # Validate metric name
        self._validate_name(name)
        
        # Validate labels
        if labels:
            for label in labels:
                self._validate_label_name(label)
    
    def _validate_name(self, name: str) -> None:
        """Validate metric name according to Prometheus conventions."""
        if not name:
            raise MetricValidationError(
                message="Metric name cannot be empty",
                validation_rule="non_empty_name"
            )
        
        if not name.replace('_', '').replace(':', '').isalnum():
            raise MetricValidationError(
                message=f"Invalid metric name '{name}'. Must contain only alphanumeric characters, underscores, and colons",
                validation_rule="valid_characters"
            )
        
        if name[0].isdigit():
            raise MetricValidationError(
                message=f"Metric name '{name}' cannot start with a digit",
                validation_rule="no_leading_digit"
            )
    
    def _validate_label_name(self, label: str) -> None:
        """Validate label name according to Prometheus conventions."""
        if not label:
            raise MetricValidationError(
                message="Label name cannot be empty",
                validation_rule="non_empty_label"
            )
        
        if label.startswith('__'):
            raise MetricValidationError(
                message=f"Label name '{label}' cannot start with '__' (reserved for internal use)",
                validation_rule="no_reserved_prefix"
            )
        
        if not label.replace('_', '').isalnum():
            raise MetricValidationError(
                message=f"Invalid label name '{label}'. Must contain only alphanumeric characters and underscores",
                validation_rule="valid_label_characters"
            )
    
    def _validate_label_values(self, label_values: Dict[str, str]) -> None:
        """Validate label values."""
        if not label_values:
            return
        
        # Check that all required labels are provided
        if self.labels:
            missing_labels = set(self.labels) - set(label_values.keys())
            if missing_labels:
                raise MetricValidationError(
                    message=f"Missing required labels: {missing_labels}",
                    validation_rule="required_labels"
                )
        
        # Check for unexpected labels
        if self.labels:
            unexpected_labels = set(label_values.keys()) - set(self.labels)
            if unexpected_labels:
                raise MetricValidationError(
                    message=f"Unexpected labels: {unexpected_labels}",
                    validation_rule="unexpected_labels"
                )
        
        # Validate label values
        for key, value in label_values.items():
            if not isinstance(value, str):
                raise MetricValidationError(
                    message=f"Label value for '{key}' must be a string, got {type(value)}",
                    validation_rule="string_label_values"
                )
    
    @abstractmethod
    def get_type(self) -> MetricType:
        """Get the metric type."""
        pass
    
    @abstractmethod
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Union[float, Dict[str, Any]]:
        """Get the current metric value."""
        pass
    
    @abstractmethod
    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset the metric value."""
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metric metadata."""
        return {
            'name': self.name,
            'description': self.description,
            'type': self.get_type().value,
            'labels': self.labels,
            'unit': self.unit,
            'created_at': self.created_at
        }


class Counter(BaseMetric):
    """Counter metric that only increases."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None, unit: str = ""):
        super().__init__(name, description, labels, unit)
        self._values: Dict[str, float] = defaultdict(float)
    
    def get_type(self) -> MetricType:
        return MetricType.COUNTER
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the counter."""
        if amount < 0:
            raise MetricValidationError(
                message="Counter increment must be non-negative",
                validation_rule="non_negative_increment"
            )
        
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            self._values[label_key] += amount
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get the current counter value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            return self._values.get(label_key, 0.0)
    
    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset the counter value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            if labels:
                label_key = self._labels_to_key(labels)
                self._values[label_key] = 0.0
            else:
                self._values.clear()
    
    def get_all_values(self) -> Dict[str, float]:
        """Get all counter values with their labels."""
        with self._lock:
            return dict(self._values)
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Gauge(BaseMetric):
    """Gauge metric that can increase and decrease."""
    
    def __init__(self, name: str, description: str = "", labels: Optional[List[str]] = None, unit: str = ""):
        super().__init__(name, description, labels, unit)
        self._values: Dict[str, float] = defaultdict(float)
    
    def get_type(self) -> MetricType:
        return MetricType.GAUGE
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set the gauge value."""
        if not isinstance(value, (int, float)):
            raise MetricValidationError(
                message="Gauge value must be numeric",
                validation_rule="numeric_value"
            )
        
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            self._values[label_key] = float(value)
    
    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment the gauge value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            self._values[label_key] += amount
    
    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement the gauge value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            self._values[label_key] -= amount
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get the current gauge value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            return self._values.get(label_key, 0.0)
    
    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset the gauge value."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            if labels:
                label_key = self._labels_to_key(labels)
                self._values[label_key] = 0.0
            else:
                self._values.clear()
    
    def get_all_values(self) -> Dict[str, float]:
        """Get all gauge values with their labels."""
        with self._lock:
            return dict(self._values)
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class Histogram(BaseMetric):
    """Histogram metric for measuring distributions."""
    
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf')]
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        unit: str = "",
        buckets: Optional[List[float]] = None
    ):
        super().__init__(name, description, labels, unit)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        
        # Ensure +Inf bucket exists
        if float('inf') not in self.buckets:
            self.buckets.append(float('inf'))
        
        # Initialize bucket counters and sum/count
        self._bucket_counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._sums: Dict[str, float] = defaultdict(float)
        self._counts: Dict[str, int] = defaultdict(int)
    
    def get_type(self) -> MetricType:
        return MetricType.HISTOGRAM
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in the histogram."""
        if not isinstance(value, (int, float)):
            raise MetricValidationError(
                message="Histogram observation must be numeric",
                validation_rule="numeric_observation"
            )
        
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            
            # Update sum and count
            self._sums[label_key] += value
            self._counts[label_key] += 1
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[label_key][bucket] += 1
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get histogram statistics."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            
            count = self._counts.get(label_key, 0)
            sum_value = self._sums.get(label_key, 0.0)
            buckets = dict(self._bucket_counts.get(label_key, {}))
            
            return {
                'count': count,
                'sum': sum_value,
                'buckets': buckets,
                'average': sum_value / count if count > 0 else 0.0
            }
    
    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset histogram values."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            if labels:
                label_key = self._labels_to_key(labels)
                self._bucket_counts[label_key].clear()
                self._sums[label_key] = 0.0
                self._counts[label_key] = 0
            else:
                self._bucket_counts.clear()
                self._sums.clear()
                self._counts.clear()
    
    def get_all_values(self) -> Dict[str, Dict[str, Any]]:
        """Get all histogram values with their labels."""
        with self._lock:
            result = {}
            for label_key in self._counts.keys():
                labels = self._key_to_labels(label_key)
                result[label_key] = self.get_value(labels)
            return result
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        return dict(item.split('=', 1) for item in key.split(','))


class Summary(BaseMetric):
    """Summary metric for measuring distributions with quantiles."""
    
    DEFAULT_QUANTILES = [0.5, 0.9, 0.95, 0.99]
    
    def __init__(
        self,
        name: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        unit: str = "",
        quantiles: Optional[List[float]] = None,
        max_age_seconds: float = 600.0,
        age_buckets: int = 5
    ):
        super().__init__(name, description, labels, unit)
        self.quantiles = quantiles or self.DEFAULT_QUANTILES
        self.max_age_seconds = max_age_seconds
        self.age_buckets = age_buckets
        
        # Validate quantiles
        for q in self.quantiles:
            if not 0 <= q <= 1:
                raise MetricValidationError(
                    message=f"Quantile {q} must be between 0 and 1",
                    validation_rule="valid_quantile"
                )
        
        # Initialize observations storage
        self._observations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._sums: Dict[str, float] = defaultdict(float)
        self._counts: Dict[str, int] = defaultdict(int)
    
    def get_type(self) -> MetricType:
        return MetricType.SUMMARY
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in the summary."""
        if not isinstance(value, (int, float)):
            raise MetricValidationError(
                message="Summary observation must be numeric",
                validation_rule="numeric_observation"
            )
        
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            
            # Add observation with timestamp
            observation = (value, time.time())
            self._observations[label_key].append(observation)
            
            # Update sum and count
            self._sums[label_key] += value
            self._counts[label_key] += 1
            
            # Clean old observations
            self._clean_old_observations(label_key)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get summary statistics including quantiles."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            label_key = self._labels_to_key(labels)
            
            # Clean old observations first
            self._clean_old_observations(label_key)
            
            observations = self._observations.get(label_key, deque())
            count = len(observations)
            sum_value = sum(obs[0] for obs in observations)
            
            if count == 0:
                return {
                    'count': 0,
                    'sum': 0.0,
                    'quantiles': {q: 0.0 for q in self.quantiles}
                }
            
            # Calculate quantiles
            values = sorted([obs[0] for obs in observations])
            quantile_values = {}
            
            for q in self.quantiles:
                if q == 0.0:
                    quantile_values[q] = values[0]
                elif q == 1.0:
                    quantile_values[q] = values[-1]
                else:
                    index = int(q * (count - 1))
                    quantile_values[q] = values[index]
            
            return {
                'count': count,
                'sum': sum_value,
                'quantiles': quantile_values,
                'average': sum_value / count
            }
    
    def reset(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Reset summary values."""
        labels = labels or {}
        self._validate_label_values(labels)
        
        with self._lock:
            if labels:
                label_key = self._labels_to_key(labels)
                self._observations[label_key].clear()
                self._sums[label_key] = 0.0
                self._counts[label_key] = 0
            else:
                self._observations.clear()
                self._sums.clear()
                self._counts.clear()
    
    def get_all_values(self) -> Dict[str, Dict[str, Any]]:
        """Get all summary values with their labels."""
        with self._lock:
            result = {}
            for label_key in self._observations.keys():
                labels = self._key_to_labels(label_key)
                result[label_key] = self.get_value(labels)
            return result
    
    def _clean_old_observations(self, label_key: str) -> None:
        """Remove observations older than max_age_seconds."""
        if label_key not in self._observations:
            return
        
        current_time = time.time()
        cutoff_time = current_time - self.max_age_seconds
        
        observations = self._observations[label_key]
        
        # Remove old observations from the left
        while observations and observations[0][1] < cutoff_time:
            old_value, _ = observations.popleft()
            self._sums[label_key] -= old_value
            self._counts[label_key] -= 1
    
    def _labels_to_key(self, labels: Dict[str, str]) -> str:
        """Convert labels dict to a string key."""
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    
    def _key_to_labels(self, key: str) -> Dict[str, str]:
        """Convert string key back to labels dict."""
        if not key:
            return {}
        return dict(item.split('=', 1) for item in key.split(','))


# Utility functions for metric creation

def create_counter(name: str, description: str = "", labels: Optional[List[str]] = None, unit: str = "") -> Counter:
    """Create a new Counter metric."""
    return Counter(name, description, labels, unit)


def create_gauge(name: str, description: str = "", labels: Optional[List[str]] = None, unit: str = "") -> Gauge:
    """Create a new Gauge metric."""
    return Gauge(name, description, labels, unit)


def create_histogram(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    buckets: Optional[List[float]] = None
) -> Histogram:
    """Create a new Histogram metric."""
    return Histogram(name, description, labels, unit, buckets)


def create_summary(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    quantiles: Optional[List[float]] = None,
    max_age_seconds: float = 600.0,
    age_buckets: int = 5
) -> Summary:
    """Create a new Summary metric."""
    return Summary(name, description, labels, unit, quantiles, max_age_seconds, age_buckets)
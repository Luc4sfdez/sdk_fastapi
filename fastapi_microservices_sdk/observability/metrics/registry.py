"""
Metrics registry with collision detection and validation.

This module provides a centralized registry for managing metrics,
including collision detection, validation, and metadata management.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import threading
import time
from typing import Dict, List, Optional, Any, Set, Type, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .types import BaseMetric, Counter, Gauge, Histogram, Summary, MetricType
from .exceptions import (
    MetricCollisionError,
    MetricRegistrationError,
    MetricValidationError,
    MetricsError
)


@dataclass
class MetricInfo:
    """Information about a registered metric."""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str]
    unit: str
    instance: BaseMetric
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    
    def update_access(self) -> None:
        """Update access tracking information."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1


class MetricRegistry:
    """Registry for managing metrics with collision detection and validation."""
    
    def __init__(self, enable_collision_detection: bool = True):
        self._metrics: Dict[str, MetricInfo] = {}
        self._lock = threading.RLock()
        self._enable_collision_detection = enable_collision_detection
        self._reserved_names: Set[str] = {
            'up', 'scrape_duration_seconds', 'scrape_samples_scraped',
            'scrape_samples_post_metric_relabeling', 'scrape_series_added'
        }
        
        # Statistics
        self._registration_count = 0
        self._collision_count = 0
        self._validation_errors = 0
    
    def register(
        self,
        metric: BaseMetric,
        allow_override: bool = False
    ) -> None:
        """Register a metric in the registry."""
        with self._lock:
            try:
                self._validate_metric(metric)
                
                if metric.name in self._metrics:
                    if not allow_override:
                        existing_metric = self._metrics[metric.name]
                        self._collision_count += 1
                        raise MetricCollisionError(
                            message=f"Metric '{metric.name}' already registered",
                            existing_metric=existing_metric.name,
                            conflicting_metric=metric.name,
                            metric_name=metric.name,
                            metric_type=metric.get_type().value
                        )
                    else:
                        # Override existing metric
                        self._metrics[metric.name].instance = metric
                        self._metrics[metric.name].registered_at = datetime.now(timezone.utc)
                        return
                
                # Register new metric
                metric_info = MetricInfo(
                    name=metric.name,
                    metric_type=metric.get_type(),
                    description=metric.description,
                    labels=metric.labels,
                    unit=metric.unit,
                    instance=metric
                )
                
                self._metrics[metric.name] = metric_info
                self._registration_count += 1
                
            except Exception as e:
                if not isinstance(e, (MetricCollisionError, MetricValidationError)):
                    raise MetricRegistrationError(
                        message=f"Failed to register metric '{metric.name}': {str(e)}",
                        metric_name=metric.name,
                        original_error=e
                    )
                raise
    
    def unregister(self, name: str) -> bool:
        """Unregister a metric from the registry."""
        with self._lock:
            if name in self._metrics:
                del self._metrics[name]
                return True
            return False
    
    def get(self, name: str) -> Optional[BaseMetric]:
        """Get a metric by name."""
        with self._lock:
            if name in self._metrics:
                metric_info = self._metrics[name]
                metric_info.update_access()
                return metric_info.instance
            return None
    
    def get_info(self, name: str) -> Optional[MetricInfo]:
        """Get metric information by name."""
        with self._lock:
            return self._metrics.get(name)
    
    def list_metrics(self) -> List[str]:
        """List all registered metric names."""
        with self._lock:
            return list(self._metrics.keys())
    
    def list_by_type(self, metric_type: MetricType) -> List[str]:
        """List metrics by type."""
        with self._lock:
            return [
                name for name, info in self._metrics.items()
                if info.metric_type == metric_type
            ]
    
    def get_all_metrics(self) -> Dict[str, BaseMetric]:
        """Get all registered metrics."""
        with self._lock:
            result = {}
            for name, info in self._metrics.items():
                info.update_access()
                result[name] = info.instance
            return result
    
    def get_metrics_info(self) -> Dict[str, MetricInfo]:
        """Get information about all registered metrics."""
        with self._lock:
            return dict(self._metrics)
    
    def clear(self) -> None:
        """Clear all registered metrics."""
        with self._lock:
            self._metrics.clear()
    
    def exists(self, name: str) -> bool:
        """Check if a metric exists in the registry."""
        with self._lock:
            return name in self._metrics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            return {
                'total_metrics': len(self._metrics),
                'registration_count': self._registration_count,
                'collision_count': self._collision_count,
                'validation_errors': self._validation_errors,
                'metrics_by_type': self._get_metrics_by_type_count(),
                'most_accessed_metrics': self._get_most_accessed_metrics(),
                'recently_registered': self._get_recently_registered_metrics()
            }
    
    def validate_all_metrics(self) -> List[str]:
        """Validate all registered metrics and return list of issues."""
        issues = []
        with self._lock:
            for name, info in self._metrics.items():
                try:
                    self._validate_metric(info.instance)
                except MetricValidationError as e:
                    issues.append(f"Metric '{name}': {e.message}")
        return issues
    
    def cleanup_unused_metrics(self, max_age_hours: float = 24.0) -> int:
        """Remove metrics that haven't been accessed recently."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        with self._lock:
            to_remove = []
            for name, info in self._metrics.items():
                if info.last_accessed.timestamp() < cutoff_time and info.access_count == 0:
                    to_remove.append(name)
            
            for name in to_remove:
                del self._metrics[name]
                removed_count += 1
        
        return removed_count
    
    def _validate_metric(self, metric: BaseMetric) -> None:
        """Validate a metric before registration."""
        try:
            # Check reserved names
            if metric.name in self._reserved_names:
                raise MetricValidationError(
                    message=f"Metric name '{metric.name}' is reserved",
                    validation_rule="reserved_name",
                    metric_name=metric.name
                )
            
            # Validate metric name format
            if not metric.name:
                raise MetricValidationError(
                    message="Metric name cannot be empty",
                    validation_rule="non_empty_name",
                    metric_name=metric.name
                )
            
            # Check for collision detection if enabled
            if self._enable_collision_detection and metric.name in self._metrics:
                existing_info = self._metrics[metric.name]
                
                # Check if types match
                if existing_info.metric_type != metric.get_type():
                    raise MetricCollisionError(
                        message=f"Metric '{metric.name}' type mismatch. "
                               f"Existing: {existing_info.metric_type.value}, "
                               f"New: {metric.get_type().value}",
                        existing_metric=existing_info.name,
                        conflicting_metric=metric.name,
                        metric_name=metric.name
                    )
                
                # Check if labels match
                if set(existing_info.labels) != set(metric.labels):
                    raise MetricCollisionError(
                        message=f"Metric '{metric.name}' label mismatch. "
                               f"Existing: {existing_info.labels}, "
                               f"New: {metric.labels}",
                        existing_metric=existing_info.name,
                        conflicting_metric=metric.name,
                        metric_name=metric.name
                    )
            
        except Exception as e:
            self._validation_errors += 1
            if not isinstance(e, (MetricValidationError, MetricCollisionError)):
                raise MetricValidationError(
                    message=f"Metric validation failed: {str(e)}",
                    validation_rule="general_validation",
                    metric_name=metric.name,
                    original_error=e
                )
            raise
    
    def _get_metrics_by_type_count(self) -> Dict[str, int]:
        """Get count of metrics by type."""
        counts = {}
        for info in self._metrics.values():
            metric_type = info.metric_type.value
            counts[metric_type] = counts.get(metric_type, 0) + 1
        return counts
    
    def _get_most_accessed_metrics(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most accessed metrics."""
        sorted_metrics = sorted(
            self._metrics.items(),
            key=lambda x: x[1].access_count,
            reverse=True
        )
        
        return [
            {
                'name': name,
                'access_count': info.access_count,
                'last_accessed': info.last_accessed.isoformat()
            }
            for name, info in sorted_metrics[:limit]
        ]
    
    def _get_recently_registered_metrics(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recently registered metrics."""
        sorted_metrics = sorted(
            self._metrics.items(),
            key=lambda x: x[1].registered_at,
            reverse=True
        )
        
        return [
            {
                'name': name,
                'type': info.metric_type.value,
                'registered_at': info.registered_at.isoformat()
            }
            for name, info in sorted_metrics[:limit]
        ]


# Global registry instance
_global_registry: Optional[MetricRegistry] = None
_registry_lock = threading.Lock()


def get_global_registry() -> MetricRegistry:
    """Get the global metric registry instance."""
    global _global_registry
    
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = MetricRegistry()
    
    return _global_registry


def set_global_registry(registry: MetricRegistry) -> None:
    """Set the global metric registry instance."""
    global _global_registry
    
    with _registry_lock:
        _global_registry = registry


def create_registry(enable_collision_detection: bool = True) -> MetricRegistry:
    """Create a new metric registry."""
    return MetricRegistry(enable_collision_detection)


# Convenience functions for metric registration

def register_counter(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    registry: Optional[MetricRegistry] = None
) -> Counter:
    """Register a counter metric."""
    counter = Counter(name, description, labels, unit)
    reg = registry or get_global_registry()
    reg.register(counter)
    return counter


def register_gauge(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    registry: Optional[MetricRegistry] = None
) -> Gauge:
    """Register a gauge metric."""
    gauge = Gauge(name, description, labels, unit)
    reg = registry or get_global_registry()
    reg.register(gauge)
    return gauge


def register_histogram(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    buckets: Optional[List[float]] = None,
    registry: Optional[MetricRegistry] = None
) -> Histogram:
    """Register a histogram metric."""
    histogram = Histogram(name, description, labels, unit, buckets)
    reg = registry or get_global_registry()
    reg.register(histogram)
    return histogram


def register_summary(
    name: str,
    description: str = "",
    labels: Optional[List[str]] = None,
    unit: str = "",
    quantiles: Optional[List[float]] = None,
    max_age_seconds: float = 600.0,
    age_buckets: int = 5,
    registry: Optional[MetricRegistry] = None
) -> Summary:
    """Register a summary metric."""
    summary = Summary(name, description, labels, unit, quantiles, max_age_seconds, age_buckets)
    reg = registry or get_global_registry()
    reg.register(summary)
    return summary
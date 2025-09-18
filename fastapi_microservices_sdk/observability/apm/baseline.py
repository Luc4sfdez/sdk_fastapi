"""
Performance Baseline Manager for FastAPI Microservices SDK.

This module provides performance baseline establishment and drift detection
to identify performance degradations and improvements over time.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
from scipy import stats
from collections import defaultdict, deque

from .config import APMConfig
from .exceptions import BaselineError


class BaselineStatus(str, Enum):
    """Baseline status enumeration."""
    ESTABLISHING = "establishing"
    ESTABLISHED = "established"
    UPDATING = "updating"
    DRIFT_DETECTED = "drift_detected"
    INVALID = "invalid"


class DriftSeverity(str, Enum):
    """Drift severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BaselineStatistics:
    """Baseline statistical metrics."""
    mean: float
    median: float
    std_dev: float
    percentile_95: float
    percentile_99: float
    min_value: float
    max_value: float
    sample_count: int
    confidence_interval_lower: float
    confidence_interval_upper: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'mean': self.mean,
            'median': self.median,
            'std_dev': self.std_dev,
            'percentile_95': self.percentile_95,
            'percentile_99': self.percentile_99,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'sample_count': self.sample_count,
            'confidence_interval_lower': self.confidence_interval_lower,
            'confidence_interval_upper': self.confidence_interval_upper
        }


@dataclass
class PerformanceBaseline:
    """Performance baseline definition."""
    metric_name: str
    baseline_id: str
    status: BaselineStatus
    created_at: datetime
    updated_at: datetime
    baseline_period: timedelta
    statistics: Optional[BaselineStatistics]
    raw_data: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'baseline_id': self.baseline_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'baseline_period': self.baseline_period.total_seconds(),
            'statistics': self.statistics.to_dict() if self.statistics else None,
            'sample_count': len(self.raw_data),
            'metadata': self.metadata
        }


@dataclass
class BaselineDrift:
    """Baseline drift detection result."""
    metric_name: str
    baseline_id: str
    drift_detected: bool
    drift_severity: DriftSeverity
    drift_percentage: float
    current_value: float
    baseline_mean: float
    statistical_significance: float
    detection_time: datetime
    drift_direction: str  # "increase" or "decrease"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'baseline_id': self.baseline_id,
            'drift_detected': self.drift_detected,
            'drift_severity': self.drift_severity.value,
            'drift_percentage': self.drift_percentage,
            'current_value': self.current_value,
            'baseline_mean': self.baseline_mean,
            'statistical_significance': self.statistical_significance,
            'detection_time': self.detection_time.isoformat(),
            'drift_direction': self.drift_direction
        }


class BaselineManager:
    """Performance baseline manager."""
    
    def __init__(self, config: APMConfig):
        """Initialize baseline manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Baseline storage
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.drift_history: List[BaselineDrift] = []
        
        # Data collection
        self.metric_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        
        # Background tasks
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        self.drift_detection_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the baseline manager."""
        try:
            if self.is_running:
                self.logger.warning("Baseline manager is already running")
                return
            
            self.logger.info("Starting baseline manager...")
            
            # Start background tasks
            if self.config.baseline.enabled:
                self.update_task = asyncio.create_task(self._baseline_update_loop())
                
                if self.config.baseline.drift_detection_enabled:
                    self.drift_detection_task = asyncio.create_task(self._drift_detection_loop())
            
            self.is_running = True
            self.logger.info("Baseline manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting baseline manager: {e}")
            raise BaselineError(
                f"Failed to start baseline manager: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop the baseline manager."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping baseline manager...")
            
            # Cancel background tasks
            if self.update_task:
                self.update_task.cancel()
                try:
                    await self.update_task
                except asyncio.CancelledError:
                    pass
            
            if self.drift_detection_task:
                self.drift_detection_task.cancel()
                try:
                    await self.drift_detection_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Baseline manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping baseline manager: {e}")
    
    async def add_metric_data(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add metric data point for baseline calculation."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Add to metric data
            self.metric_data[metric_name].append((timestamp, value))
            
            # Check if we need to establish or update baseline
            if metric_name not in self.baselines:
                await self._maybe_establish_baseline(metric_name)
            else:
                await self._maybe_update_baseline(metric_name)
                
        except Exception as e:
            self.logger.error(f"Error adding metric data: {e}")
            raise BaselineError(
                f"Failed to add metric data: {e}",
                metric_name=metric_name,
                original_error=e
            )
    
    async def establish_baseline(self, metric_name: str, force: bool = False) -> PerformanceBaseline:
        """Establish performance baseline for a metric."""
        try:
            if metric_name in self.baselines and not force:
                raise BaselineError(f"Baseline already exists for {metric_name}")
            
            # Get metric data
            data_points = list(self.metric_data[metric_name])
            
            if len(data_points) < self.config.baseline.min_data_points:
                raise BaselineError(
                    f"Insufficient data points for baseline: {len(data_points)} < {self.config.baseline.min_data_points}",
                    metric_name=metric_name
                )
            
            # Extract values and filter outliers if enabled
            values = [point[1] for point in data_points]
            
            if self.config.baseline.outlier_removal:
                values = self._remove_outliers(values)
            
            # Calculate statistics
            statistics = self._calculate_statistics(values)
            
            # Create baseline
            baseline = PerformanceBaseline(
                metric_name=metric_name,
                baseline_id=f"baseline_{metric_name}_{int(datetime.now().timestamp())}",
                status=BaselineStatus.ESTABLISHED,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                baseline_period=self.config.baseline.baseline_period,
                statistics=statistics,
                raw_data=values,
                metadata={
                    'establishment_method': 'automatic',
                    'outliers_removed': self.config.baseline.outlier_removal,
                    'confidence_level': self.config.baseline.confidence_level
                }
            )
            
            self.baselines[metric_name] = baseline
            
            self.logger.info(f"Established baseline for {metric_name}: {baseline.baseline_id}")
            return baseline
            
        except Exception as e:
            self.logger.error(f"Error establishing baseline: {e}")
            raise BaselineError(
                f"Failed to establish baseline: {e}",
                metric_name=metric_name,
                original_error=e
            )
    
    async def update_baseline(self, metric_name: str) -> PerformanceBaseline:
        """Update existing baseline with new data."""
        try:
            if metric_name not in self.baselines:
                raise BaselineError(f"No baseline exists for {metric_name}")
            
            baseline = self.baselines[metric_name]
            baseline.status = BaselineStatus.UPDATING
            
            # Get recent data
            cutoff_time = datetime.now(timezone.utc) - self.config.baseline.baseline_period
            recent_data = [
                point[1] for point in self.metric_data[metric_name]
                if point[0] >= cutoff_time
            ]
            
            if len(recent_data) < self.config.baseline.min_data_points:
                baseline.status = BaselineStatus.INVALID
                raise BaselineError(
                    f"Insufficient recent data for baseline update: {len(recent_data)}",
                    metric_name=metric_name
                )
            
            # Filter outliers if enabled
            if self.config.baseline.outlier_removal:
                recent_data = self._remove_outliers(recent_data)
            
            # Calculate new statistics
            new_statistics = self._calculate_statistics(recent_data)
            
            # Update baseline
            baseline.statistics = new_statistics
            baseline.raw_data = recent_data
            baseline.updated_at = datetime.now(timezone.utc)
            baseline.status = BaselineStatus.ESTABLISHED
            
            self.logger.info(f"Updated baseline for {metric_name}")
            return baseline
            
        except Exception as e:
            self.logger.error(f"Error updating baseline: {e}")
            raise BaselineError(
                f"Failed to update baseline: {e}",
                metric_name=metric_name,
                original_error=e
            )
    
    async def detect_drift(self, metric_name: str, current_value: float) -> BaselineDrift:
        """Detect baseline drift for a metric."""
        try:
            if metric_name not in self.baselines:
                raise BaselineError(f"No baseline exists for {metric_name}")
            
            baseline = self.baselines[metric_name]
            
            if baseline.status != BaselineStatus.ESTABLISHED:
                raise BaselineError(f"Baseline not established for {metric_name}")
            
            stats = baseline.statistics
            
            # Calculate drift percentage
            drift_percentage = abs(current_value - stats.mean) / stats.mean * 100
            
            # Determine drift direction
            drift_direction = "increase" if current_value > stats.mean else "decrease"
            
            # Check if drift exceeds threshold
            drift_threshold = self.config.baseline.drift_threshold * 100  # Convert to percentage
            drift_detected = drift_percentage > drift_threshold
            
            # Determine drift severity
            drift_severity = self._calculate_drift_severity(drift_percentage, drift_threshold)
            
            # Calculate statistical significance using z-test
            z_score = (current_value - stats.mean) / stats.std_dev
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # Two-tailed test
            
            # Create drift result
            drift_result = BaselineDrift(
                metric_name=metric_name,
                baseline_id=baseline.baseline_id,
                drift_detected=drift_detected,
                drift_severity=drift_severity,
                drift_percentage=drift_percentage,
                current_value=current_value,
                baseline_mean=stats.mean,
                statistical_significance=p_value,
                detection_time=datetime.now(timezone.utc),
                drift_direction=drift_direction
            )
            
            # Update baseline status if significant drift detected
            if drift_detected and drift_severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
                baseline.status = BaselineStatus.DRIFT_DETECTED
            
            # Store drift result
            self.drift_history.append(drift_result)
            
            # Maintain drift history size
            if len(self.drift_history) > 1000:
                self.drift_history = self.drift_history[-1000:]
            
            if drift_detected:
                self.logger.warning(
                    f"Drift detected for {metric_name}: {drift_percentage:.2f}% "
                    f"({drift_severity.value} severity)"
                )
            
            return drift_result
            
        except Exception as e:
            self.logger.error(f"Error detecting drift: {e}")
            raise BaselineError(
                f"Failed to detect drift: {e}",
                metric_name=metric_name,
                original_error=e
            )
    
    async def get_baseline(self, metric_name: str) -> Optional[PerformanceBaseline]:
        """Get baseline for a metric."""
        return self.baselines.get(metric_name)
    
    async def get_all_baselines(self) -> Dict[str, PerformanceBaseline]:
        """Get all baselines."""
        return self.baselines.copy()
    
    async def get_drift_history(self, metric_name: Optional[str] = None, limit: int = 100) -> List[BaselineDrift]:
        """Get drift detection history."""
        if metric_name:
            history = [d for d in self.drift_history if d.metric_name == metric_name]
        else:
            history = self.drift_history
        
        return history[-limit:]
    
    async def delete_baseline(self, metric_name: str):
        """Delete baseline for a metric."""
        if metric_name in self.baselines:
            del self.baselines[metric_name]
            self.logger.info(f"Deleted baseline for {metric_name}")
    
    def _calculate_statistics(self, values: List[float]) -> BaselineStatistics:
        """Calculate baseline statistics."""
        if not values:
            raise ValueError("No values provided for statistics calculation")
        
        values_array = np.array(values)
        
        mean = np.mean(values_array)
        median = np.median(values_array)
        std_dev = np.std(values_array)
        percentile_95 = np.percentile(values_array, 95)
        percentile_99 = np.percentile(values_array, 99)
        min_value = np.min(values_array)
        max_value = np.max(values_array)
        
        # Calculate confidence interval
        confidence_level = self.config.baseline.confidence_level
        alpha = 1 - confidence_level
        degrees_freedom = len(values) - 1
        t_critical = stats.t.ppf(1 - alpha/2, degrees_freedom)
        margin_error = t_critical * (std_dev / np.sqrt(len(values)))
        
        confidence_interval_lower = mean - margin_error
        confidence_interval_upper = mean + margin_error
        
        return BaselineStatistics(
            mean=mean,
            median=median,
            std_dev=std_dev,
            percentile_95=percentile_95,
            percentile_99=percentile_99,
            min_value=min_value,
            max_value=max_value,
            sample_count=len(values),
            confidence_interval_lower=confidence_interval_lower,
            confidence_interval_upper=confidence_interval_upper
        )
    
    def _remove_outliers(self, values: List[float]) -> List[float]:
        """Remove outliers using IQR method."""
        if len(values) < 4:
            return values
        
        values_array = np.array(values)
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered_values = [v for v in values if lower_bound <= v <= upper_bound]
        
        # Ensure we don't remove too many values
        if len(filtered_values) < len(values) * 0.5:
            return values  # Return original if too many outliers
        
        return filtered_values
    
    def _calculate_drift_severity(self, drift_percentage: float, threshold: float) -> DriftSeverity:
        """Calculate drift severity based on percentage."""
        if drift_percentage <= threshold:
            return DriftSeverity.LOW
        elif drift_percentage <= threshold * 2:
            return DriftSeverity.MEDIUM
        elif drift_percentage <= threshold * 4:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL
    
    async def _maybe_establish_baseline(self, metric_name: str):
        """Check if baseline should be established."""
        data_count = len(self.metric_data[metric_name])
        
        if data_count >= self.config.baseline.min_data_points:
            try:
                await self.establish_baseline(metric_name)
            except Exception as e:
                self.logger.error(f"Error auto-establishing baseline for {metric_name}: {e}")
    
    async def _maybe_update_baseline(self, metric_name: str):
        """Check if baseline should be updated."""
        if not self.config.baseline.auto_update:
            return
        
        baseline = self.baselines[metric_name]
        time_since_update = datetime.now(timezone.utc) - baseline.updated_at
        
        if time_since_update >= self.config.baseline.update_frequency:
            try:
                await self.update_baseline(metric_name)
            except Exception as e:
                self.logger.error(f"Error auto-updating baseline for {metric_name}: {e}")
    
    async def _baseline_update_loop(self):
        """Background loop for baseline updates."""
        while self.is_running:
            try:
                # Update baselines periodically
                update_interval = self.config.baseline.update_frequency.total_seconds() / 4
                await asyncio.sleep(update_interval)
                
                if not self.is_running:
                    break
                
                # Check for baselines that need updating
                for metric_name in list(self.baselines.keys()):
                    await self._maybe_update_baseline(metric_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in baseline update loop: {e}")
                await asyncio.sleep(60)
    
    async def _drift_detection_loop(self):
        """Background loop for drift detection."""
        while self.is_running:
            try:
                # Check for drift periodically
                await asyncio.sleep(self.config.baseline.drift_window.total_seconds())
                
                if not self.is_running:
                    break
                
                # Perform drift detection for recent data
                await self._periodic_drift_detection()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in drift detection loop: {e}")
                await asyncio.sleep(60)
    
    async def _periodic_drift_detection(self):
        """Perform periodic drift detection."""
        try:
            for metric_name, baseline in self.baselines.items():
                if baseline.status != BaselineStatus.ESTABLISHED:
                    continue
                
                # Get recent data points
                recent_data = list(self.metric_data[metric_name])[-10:]  # Last 10 points
                
                if not recent_data:
                    continue
                
                # Check drift for recent values
                for _, value in recent_data[-3:]:  # Check last 3 values
                    await self.detect_drift(metric_name, value)
                    
        except Exception as e:
            self.logger.error(f"Error in periodic drift detection: {e}")
    
    async def get_baseline_health(self) -> Dict[str, Any]:
        """Get baseline manager health status."""
        return {
            'is_running': self.is_running,
            'total_baselines': len(self.baselines),
            'established_baselines': len([
                b for b in self.baselines.values() 
                if b.status == BaselineStatus.ESTABLISHED
            ]),
            'drift_detected_baselines': len([
                b for b in self.baselines.values() 
                if b.status == BaselineStatus.DRIFT_DETECTED
            ]),
            'total_drift_detections': len(self.drift_history),
            'metrics_tracked': len(self.metric_data)
        }


def create_baseline_manager(config: APMConfig) -> BaselineManager:
    """Create baseline manager instance."""
    return BaselineManager(config)
"""
Adaptive Thresholds System for FastAPI Microservices SDK.

This module provides adaptive threshold management using machine learning
to automatically adjust alert thresholds based on historical data and patterns.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import json

# Optional ML dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .config import IntelligentAlertingConfig, AdaptationStrategy, AdaptiveThresholdConfig
from .exceptions import ThresholdAdaptationError, MLModelError
from ..rules import MetricDataPoint


class ThresholdAdaptationResult(str, Enum):
    """Threshold adaptation result."""
    ADAPTED = "adapted"
    NO_CHANGE = "no_change"
    INSUFFICIENT_DATA = "insufficient_data"
    ERROR = "error"


@dataclass
class ThresholdAdaptation:
    """Threshold adaptation record."""
    metric_name: str
    rule_name: str
    old_threshold: float
    new_threshold: float
    adaptation_reason: str
    confidence_score: float
    data_points_used: int
    adaptation_timestamp: datetime
    strategy_used: AdaptationStrategy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'rule_name': self.rule_name,
            'old_threshold': self.old_threshold,
            'new_threshold': self.new_threshold,
            'adaptation_reason': self.adaptation_reason,
            'confidence_score': self.confidence_score,
            'data_points_used': self.data_points_used,
            'adaptation_timestamp': self.adaptation_timestamp.isoformat(),
            'strategy_used': self.strategy_used.value
        }


@dataclass
class ThresholdModel:
    """Threshold model for a specific metric."""
    metric_name: str
    rule_name: str
    current_threshold: float
    adaptation_history: List[ThresholdAdaptation] = field(default_factory=list)
    last_adaptation: Optional[datetime] = None
    model_data: Optional[Dict[str, Any]] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def add_adaptation(self, adaptation: ThresholdAdaptation):
        """Add adaptation to history."""
        self.adaptation_history.append(adaptation)
        self.last_adaptation = adaptation.adaptation_timestamp
        self.current_threshold = adaptation.new_threshold
        
        # Keep only recent adaptations
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
        self.adaptation_history = [
            adapt for adapt in self.adaptation_history
            if adapt.adaptation_timestamp >= cutoff_time
        ]
    
    def get_adaptation_frequency(self) -> float:
        """Get adaptation frequency (adaptations per day)."""
        if len(self.adaptation_history) < 2:
            return 0.0
        
        time_span = (
            self.adaptation_history[-1].adaptation_timestamp - 
            self.adaptation_history[0].adaptation_timestamp
        ).total_seconds() / 86400  # Convert to days
        
        return len(self.adaptation_history) / max(time_span, 1.0)
    
    def get_recent_performance(self) -> Dict[str, float]:
        """Get recent performance metrics."""
        return self.performance_metrics.copy()


class AdaptiveThresholdManager:
    """Adaptive threshold management system."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize adaptive threshold manager."""
        self.config = config
        self.threshold_config = config.adaptive_threshold_config
        self.logger = logging.getLogger(__name__)
        
        # Threshold models
        self._models: Dict[str, ThresholdModel] = {}
        
        # Data storage
        self._metric_data: Dict[str, List[MetricDataPoint]] = {}
        
        # ML components
        self._scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
        # Manager state
        self._running = False
        self._adaptation_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start adaptive threshold manager."""
        if self._running:
            return
        
        self._running = True
        
        if self.threshold_config.enabled:
            self._adaptation_task = asyncio.create_task(self._adaptation_loop())
        
        self.logger.info("Adaptive threshold manager started")
    
    async def stop(self):
        """Stop adaptive threshold manager."""
        if not self._running:
            return
        
        self._running = False
        
        if self._adaptation_task:
            self._adaptation_task.cancel()
            try:
                await self._adaptation_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Adaptive threshold manager stopped")
    
    def register_threshold(
        self,
        metric_name: str,
        rule_name: str,
        initial_threshold: float
    ):
        """Register a threshold for adaptation."""
        model_key = f"{metric_name}:{rule_name}"
        
        if model_key not in self._models:
            self._models[model_key] = ThresholdModel(
                metric_name=metric_name,
                rule_name=rule_name,
                current_threshold=initial_threshold
            )
            
            self.logger.info(f"Registered threshold for {model_key}: {initial_threshold}")
    
    def add_metric_data(self, metric_name: str, data_points: List[MetricDataPoint]):
        """Add metric data for threshold adaptation."""
        if metric_name not in self._metric_data:
            self._metric_data[metric_name] = []
        
        self._metric_data[metric_name].extend(data_points)
        
        # Keep only recent data
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            days=self.config.data_retention_days
        )
        
        self._metric_data[metric_name] = [
            dp for dp in self._metric_data[metric_name]
            if dp.timestamp >= cutoff_time
        ]
    
    async def adapt_threshold(
        self,
        metric_name: str,
        rule_name: str,
        force: bool = False
    ) -> ThresholdAdaptationResult:
        """Adapt threshold for specific metric and rule."""
        try:
            model_key = f"{metric_name}:{rule_name}"
            
            if model_key not in self._models:
                raise ThresholdAdaptationError(
                    f"No threshold model found for {model_key}",
                    adaptation_strategy=self.threshold_config.adaptation_strategy.value
                )
            
            model = self._models[model_key]
            
            # Check if adaptation is needed
            if not force and not self._should_adapt(model):
                return ThresholdAdaptationResult.NO_CHANGE
            
            # Get metric data
            if metric_name not in self._metric_data:
                return ThresholdAdaptationResult.INSUFFICIENT_DATA
            
            data_points = self._metric_data[metric_name]
            
            if len(data_points) < self.threshold_config.min_data_points:
                return ThresholdAdaptationResult.INSUFFICIENT_DATA
            
            # Perform adaptation based on strategy
            adaptation_result = await self._perform_adaptation(model, data_points)
            
            if adaptation_result:
                model.add_adaptation(adaptation_result)
                self.logger.info(
                    f"Adapted threshold for {model_key}: "
                    f"{adaptation_result.old_threshold} -> {adaptation_result.new_threshold}"
                )
                return ThresholdAdaptationResult.ADAPTED
            
            return ThresholdAdaptationResult.NO_CHANGE
            
        except Exception as e:
            self.logger.error(f"Error adapting threshold for {metric_name}:{rule_name}: {e}")
            return ThresholdAdaptationResult.ERROR
    
    def get_current_threshold(self, metric_name: str, rule_name: str) -> Optional[float]:
        """Get current threshold for metric and rule."""
        model_key = f"{metric_name}:{rule_name}"
        
        if model_key in self._models:
            return self._models[model_key].current_threshold
        
        return None
    
    def get_threshold_model(self, metric_name: str, rule_name: str) -> Optional[ThresholdModel]:
        """Get threshold model for metric and rule."""
        model_key = f"{metric_name}:{rule_name}"
        return self._models.get(model_key)
    
    def list_threshold_models(self) -> List[ThresholdModel]:
        """List all threshold models."""
        return list(self._models.values())
    
    async def _adaptation_loop(self):
        """Main adaptation loop."""
        while self._running:
            try:
                await self._process_all_adaptations()
                
                # Wait for next adaptation interval
                interval_seconds = self.threshold_config.adaptation_interval_hours * 3600
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in adaptation loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _process_all_adaptations(self):
        """Process adaptations for all registered thresholds."""
        adaptation_tasks = []
        
        for model_key, model in self._models.items():
            metric_name, rule_name = model_key.split(':', 1)
            
            task = asyncio.create_task(
                self.adapt_threshold(metric_name, rule_name)
            )
            adaptation_tasks.append(task)
        
        if adaptation_tasks:
            await asyncio.gather(*adaptation_tasks, return_exceptions=True)
    
    def _should_adapt(self, model: ThresholdModel) -> bool:
        """Check if threshold should be adapted."""
        # Check stability period
        if model.last_adaptation:
            stability_period = timedelta(hours=self.threshold_config.stability_period_hours)
            if datetime.now(timezone.utc) - model.last_adaptation < stability_period:
                return False
        
        # Check adaptation frequency
        frequency = model.get_adaptation_frequency()
        max_frequency = 1.0  # Max 1 adaptation per day
        
        if frequency > max_frequency:
            return False
        
        return True
    
    async def _perform_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform threshold adaptation."""
        try:
            strategy = self.threshold_config.adaptation_strategy
            
            if strategy == AdaptationStrategy.STATISTICAL_BASED:
                return await self._statistical_adaptation(model, data_points)
            elif strategy == AdaptationStrategy.ML_BASED:
                return await self._ml_adaptation(model, data_points)
            elif strategy == AdaptationStrategy.HYBRID:
                return await self._hybrid_adaptation(model, data_points)
            elif strategy == AdaptationStrategy.TIME_SERIES_BASED:
                return await self._time_series_adaptation(model, data_points)
            elif strategy == AdaptationStrategy.SEASONAL_AWARE:
                return await self._seasonal_adaptation(model, data_points)
            else:
                # Default to statistical
                return await self._statistical_adaptation(model, data_points)
                
        except Exception as e:
            raise ThresholdAdaptationError(
                f"Failed to perform adaptation for {model.metric_name}",
                adaptation_strategy=strategy.value,
                current_threshold=model.current_threshold,
                original_error=e
            )
    
    async def _statistical_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform statistical-based threshold adaptation."""
        try:
            # Extract values from recent data
            recent_cutoff = datetime.now(timezone.utc) - timedelta(
                hours=self.threshold_config.adaptation_interval_hours * 2
            )
            
            recent_values = [
                dp.value for dp in data_points
                if dp.timestamp >= recent_cutoff and isinstance(dp.value, (int, float))
            ]
            
            if len(recent_values) < self.threshold_config.min_data_points:
                return None
            
            # Calculate statistical metrics
            mean_value = statistics.mean(recent_values)
            std_value = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
            
            # Calculate new threshold based on confidence level
            confidence_multiplier = self._get_confidence_multiplier(
                self.threshold_config.confidence_level
            )
            
            new_threshold = mean_value + (confidence_multiplier * std_value)
            
            # Apply adaptation rate
            current_threshold = model.current_threshold
            threshold_change = new_threshold - current_threshold
            adapted_change = threshold_change * self.threshold_config.adaptation_rate
            
            final_threshold = current_threshold + adapted_change
            
            # Check maximum change limit
            max_change = current_threshold * self.threshold_config.max_threshold_change
            
            if abs(adapted_change) > max_change:
                final_threshold = current_threshold + (
                    max_change if adapted_change > 0 else -max_change
                )
            
            # Only adapt if change is significant
            if abs(final_threshold - current_threshold) < (current_threshold * 0.05):  # 5% minimum change
                return None
            
            return ThresholdAdaptation(
                metric_name=model.metric_name,
                rule_name=model.rule_name,
                old_threshold=current_threshold,
                new_threshold=final_threshold,
                adaptation_reason=f"Statistical adaptation: mean={mean_value:.3f}, std={std_value:.3f}",
                confidence_score=self.threshold_config.confidence_level,
                data_points_used=len(recent_values),
                adaptation_timestamp=datetime.now(timezone.utc),
                strategy_used=AdaptationStrategy.STATISTICAL_BASED
            )
            
        except Exception as e:
            raise ThresholdAdaptationError(
                "Statistical adaptation failed",
                adaptation_strategy="statistical_based",
                original_error=e
            )
    
    async def _ml_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform ML-based threshold adaptation."""
        try:
            if not SKLEARN_AVAILABLE:
                self.logger.warning("Scikit-learn not available, falling back to statistical adaptation")
                return await self._statistical_adaptation(model, data_points)
            
            # Prepare features
            features, values = self._prepare_ml_features(data_points)
            
            if len(features) < self.threshold_config.min_data_points:
                return None
            
            # Train anomaly detection model
            isolation_forest = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            # Fit model
            isolation_forest.fit(features)
            
            # Get anomaly scores
            anomaly_scores = isolation_forest.decision_function(features)
            
            # Calculate threshold based on anomaly scores
            # Use percentile approach
            threshold_percentile = (1 - self.threshold_config.confidence_level) * 100
            score_threshold = np.percentile(anomaly_scores, threshold_percentile)
            
            # Map back to metric values
            # Find values corresponding to normal behavior
            normal_indices = anomaly_scores >= score_threshold
            normal_values = [values[i] for i in range(len(values)) if normal_indices[i]]
            
            if not normal_values:
                return None
            
            # Calculate new threshold
            new_threshold = max(normal_values) * 1.1  # 10% buffer
            
            # Apply adaptation rate
            current_threshold = model.current_threshold
            threshold_change = new_threshold - current_threshold
            adapted_change = threshold_change * self.threshold_config.adaptation_rate
            
            final_threshold = current_threshold + adapted_change
            
            # Check maximum change limit
            max_change = current_threshold * self.threshold_config.max_threshold_change
            
            if abs(adapted_change) > max_change:
                final_threshold = current_threshold + (
                    max_change if adapted_change > 0 else -max_change
                )
            
            # Only adapt if change is significant
            if abs(final_threshold - current_threshold) < (current_threshold * 0.05):
                return None
            
            return ThresholdAdaptation(
                metric_name=model.metric_name,
                rule_name=model.rule_name,
                old_threshold=current_threshold,
                new_threshold=final_threshold,
                adaptation_reason=f"ML adaptation: anomaly detection, normal_values={len(normal_values)}",
                confidence_score=self.threshold_config.confidence_level,
                data_points_used=len(features),
                adaptation_timestamp=datetime.now(timezone.utc),
                strategy_used=AdaptationStrategy.ML_BASED
            )
            
        except Exception as e:
            raise ThresholdAdaptationError(
                "ML adaptation failed",
                adaptation_strategy="ml_based",
                original_error=e
            )
    
    async def _hybrid_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform hybrid adaptation (statistical + ML)."""
        try:
            # Try ML adaptation first
            ml_result = await self._ml_adaptation(model, data_points)
            
            # Try statistical adaptation
            stat_result = await self._statistical_adaptation(model, data_points)
            
            # If both succeed, use weighted average
            if ml_result and stat_result:
                ml_weight = 0.7
                stat_weight = 0.3
                
                combined_threshold = (
                    ml_result.new_threshold * ml_weight +
                    stat_result.new_threshold * stat_weight
                )
                
                return ThresholdAdaptation(
                    metric_name=model.metric_name,
                    rule_name=model.rule_name,
                    old_threshold=model.current_threshold,
                    new_threshold=combined_threshold,
                    adaptation_reason=f"Hybrid adaptation: ML({ml_result.new_threshold:.3f}) + Stat({stat_result.new_threshold:.3f})",
                    confidence_score=(ml_result.confidence_score + stat_result.confidence_score) / 2,
                    data_points_used=max(ml_result.data_points_used, stat_result.data_points_used),
                    adaptation_timestamp=datetime.now(timezone.utc),
                    strategy_used=AdaptationStrategy.HYBRID
                )
            
            # Use whichever succeeded
            return ml_result or stat_result
            
        except Exception as e:
            raise ThresholdAdaptationError(
                "Hybrid adaptation failed",
                adaptation_strategy="hybrid",
                original_error=e
            )
    
    async def _time_series_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform time series-based adaptation."""
        try:
            # Extract time series data
            time_series = []
            for dp in sorted(data_points, key=lambda x: x.timestamp):
                if isinstance(dp.value, (int, float)):
                    time_series.append(dp.value)
            
            if len(time_series) < self.threshold_config.min_data_points:
                return None
            
            # Calculate trend
            if len(time_series) >= 2:
                # Simple linear trend
                x = list(range(len(time_series)))
                y = time_series
                
                # Calculate slope
                n = len(x)
                sum_x = sum(x)
                sum_y = sum(y)
                sum_xy = sum(x[i] * y[i] for i in range(n))
                sum_x2 = sum(x[i] ** 2 for i in range(n))
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
                
                # Project future values
                future_steps = 24  # 24 time steps ahead
                projected_value = time_series[-1] + (slope * future_steps)
                
                # Add buffer for threshold
                new_threshold = projected_value * 1.2  # 20% buffer
                
                # Apply adaptation constraints
                current_threshold = model.current_threshold
                threshold_change = new_threshold - current_threshold
                adapted_change = threshold_change * self.threshold_config.adaptation_rate
                
                final_threshold = current_threshold + adapted_change
                
                # Check maximum change limit
                max_change = current_threshold * self.threshold_config.max_threshold_change
                
                if abs(adapted_change) > max_change:
                    final_threshold = current_threshold + (
                        max_change if adapted_change > 0 else -max_change
                    )
                
                # Only adapt if change is significant
                if abs(final_threshold - current_threshold) < (current_threshold * 0.05):
                    return None
                
                return ThresholdAdaptation(
                    metric_name=model.metric_name,
                    rule_name=model.rule_name,
                    old_threshold=current_threshold,
                    new_threshold=final_threshold,
                    adaptation_reason=f"Time series adaptation: trend_slope={slope:.6f}, projected={projected_value:.3f}",
                    confidence_score=min(0.9, abs(slope) * 100),  # Confidence based on trend strength
                    data_points_used=len(time_series),
                    adaptation_timestamp=datetime.now(timezone.utc),
                    strategy_used=AdaptationStrategy.TIME_SERIES_BASED
                )
            
            return None
            
        except Exception as e:
            raise ThresholdAdaptationError(
                "Time series adaptation failed",
                adaptation_strategy="time_series_based",
                original_error=e
            )
    
    async def _seasonal_adaptation(
        self,
        model: ThresholdModel,
        data_points: List[MetricDataPoint]
    ) -> Optional[ThresholdAdaptation]:
        """Perform seasonal-aware adaptation."""
        try:
            # Group data by hour of day for seasonal patterns
            hourly_data = {}
            current_hour = datetime.now(timezone.utc).hour
            
            for dp in data_points:
                if isinstance(dp.value, (int, float)):
                    hour = dp.timestamp.hour
                    if hour not in hourly_data:
                        hourly_data[hour] = []
                    hourly_data[hour].append(dp.value)
            
            # Calculate seasonal threshold for current hour
            if current_hour in hourly_data and len(hourly_data[current_hour]) >= 5:
                hour_values = hourly_data[current_hour]
                hour_mean = statistics.mean(hour_values)
                hour_std = statistics.stdev(hour_values) if len(hour_values) > 1 else 0
                
                # Calculate seasonal threshold
                confidence_multiplier = self._get_confidence_multiplier(
                    self.threshold_config.confidence_level
                )
                
                seasonal_threshold = hour_mean + (confidence_multiplier * hour_std)
                
                # Apply adaptation rate
                current_threshold = model.current_threshold
                threshold_change = seasonal_threshold - current_threshold
                adapted_change = threshold_change * self.threshold_config.adaptation_rate
                
                final_threshold = current_threshold + adapted_change
                
                # Check maximum change limit
                max_change = current_threshold * self.threshold_config.max_threshold_change
                
                if abs(adapted_change) > max_change:
                    final_threshold = current_threshold + (
                        max_change if adapted_change > 0 else -max_change
                    )
                
                # Only adapt if change is significant
                if abs(final_threshold - current_threshold) < (current_threshold * 0.05):
                    return None
                
                return ThresholdAdaptation(
                    metric_name=model.metric_name,
                    rule_name=model.rule_name,
                    old_threshold=current_threshold,
                    new_threshold=final_threshold,
                    adaptation_reason=f"Seasonal adaptation: hour={current_hour}, mean={hour_mean:.3f}, std={hour_std:.3f}",
                    confidence_score=self.threshold_config.confidence_level,
                    data_points_used=len(hour_values),
                    adaptation_timestamp=datetime.now(timezone.utc),
                    strategy_used=AdaptationStrategy.SEASONAL_AWARE
                )
            
            return None
            
        except Exception as e:
            raise ThresholdAdaptationError(
                "Seasonal adaptation failed",
                adaptation_strategy="seasonal_aware",
                original_error=e
            )
    
    def _prepare_ml_features(self, data_points: List[MetricDataPoint]) -> Tuple[List[List[float]], List[float]]:
        """Prepare features for ML models."""
        features = []
        values = []
        
        for dp in data_points:
            if isinstance(dp.value, (int, float)):
                # Time-based features
                hour = dp.timestamp.hour
                day_of_week = dp.timestamp.weekday()
                minute_of_hour = dp.timestamp.minute
                
                # Create feature vector
                feature_vector = [
                    hour,
                    day_of_week,
                    minute_of_hour,
                    dp.value  # Include the value itself as a feature
                ]
                
                features.append(feature_vector)
                values.append(dp.value)
        
        return features, values
    
    def _get_confidence_multiplier(self, confidence_level: float) -> float:
        """Get confidence multiplier for statistical calculations."""
        # Standard normal distribution multipliers
        confidence_multipliers = {
            0.68: 1.0,   # 1 sigma
            0.90: 1.645, # 90%
            0.95: 1.96,  # 95%
            0.99: 2.576, # 99%
            0.999: 3.29  # 99.9%
        }
        
        # Find closest confidence level
        closest_level = min(confidence_multipliers.keys(), 
                          key=lambda x: abs(x - confidence_level))
        
        return confidence_multipliers[closest_level]
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get adaptive threshold manager statistics."""
        total_models = len(self._models)
        total_adaptations = sum(len(model.adaptation_history) for model in self._models.values())
        
        recent_adaptations = 0
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        for model in self._models.values():
            recent_adaptations += sum(
                1 for adapt in model.adaptation_history
                if adapt.adaptation_timestamp >= recent_cutoff
            )
        
        return {
            'total_models': total_models,
            'total_adaptations': total_adaptations,
            'recent_adaptations_24h': recent_adaptations,
            'running': self._running,
            'adaptation_strategy': self.threshold_config.adaptation_strategy.value,
            'adaptation_interval_hours': self.threshold_config.adaptation_interval_hours,
            'confidence_level': self.threshold_config.confidence_level
        }


def create_adaptive_threshold_manager(config: IntelligentAlertingConfig) -> AdaptiveThresholdManager:
    """Create adaptive threshold manager."""
    return AdaptiveThresholdManager(config)


# Export main classes and functions
__all__ = [
    'ThresholdAdaptationResult',
    'ThresholdAdaptation',
    'ThresholdModel',
    'AdaptiveThresholdManager',
    'create_adaptive_threshold_manager',
]
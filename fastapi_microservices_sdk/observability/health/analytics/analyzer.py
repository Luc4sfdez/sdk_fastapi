"""
Health Analytics Analyzer for FastAPI Microservices SDK.

This module provides comprehensive health analytics including trend analysis,
pattern detection, and statistical analysis of health data.

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

# Optional dependencies for advanced analytics
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .config import AnalyticsConfig, TrendType, TrendConfig
from .exceptions import HealthAnalyticsError, TrendAnalysisError
from ..config import HealthStatus
from ..monitor import HealthCheckResult


class TrendDirection(str, Enum):
    """Trend direction enumeration."""
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


@dataclass
class HealthDataPoint:
    """Health data point for analysis."""
    timestamp: datetime
    status: HealthStatus
    response_time: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Trend analysis result."""
    trend_type: TrendType
    direction: TrendDirection
    confidence: float
    slope: float
    correlation: float
    prediction: Optional[float] = None
    analysis_period: timedelta = field(default_factory=lambda: timedelta(hours=24))
    data_points: int = 0


class HealthAnalyzer:
    """Advanced health analytics analyzer."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize health analyzer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._data_points: List[HealthDataPoint] = []
        self._analysis_cache: Dict[str, Any] = {}
        
    async def add_data_point(self, result: HealthCheckResult) -> None:
        """Add health check result for analysis."""
        try:
            data_point = HealthDataPoint(
                timestamp=datetime.now(timezone.utc),
                status=result.status,
                response_time=result.response_time or 0.0,
                success_rate=1.0 if result.status == HealthStatus.HEALTHY else 0.0,
                error_count=1 if result.status != HealthStatus.HEALTHY else 0,
                metadata=result.details or {}
            )
            
            self._data_points.append(data_point)
            
            # Cleanup old data points
            await self._cleanup_old_data()
            
            # Clear cache when new data arrives
            self._analysis_cache.clear()
            
        except Exception as e:
            self.logger.error(f"Error adding data point: {e}")
            raise HealthAnalyticsError(
                "Failed to add health data point",
                analytics_operation="add_data_point",
                original_error=e
            )
    
    async def analyze_trends(
        self,
        trend_types: Optional[List[TrendType]] = None,
        time_window: Optional[timedelta] = None
    ) -> Dict[TrendType, TrendAnalysis]:
        """Analyze health trends."""
        try:
            trend_types = trend_types or self.config.trend_config.trend_types
            time_window = time_window or timedelta(hours=self.config.trend_config.analysis_window_hours)
            
            # Filter data points by time window
            cutoff_time = datetime.now(timezone.utc) - time_window
            filtered_data = [
                dp for dp in self._data_points
                if dp.timestamp >= cutoff_time
            ]
            
            if len(filtered_data) < self.config.trend_config.data_points_minimum:
                raise TrendAnalysisError(
                    f"Insufficient data points for analysis. Need at least {self.config.trend_config.data_points_minimum}, got {len(filtered_data)}",
                    data_points=len(filtered_data)
                )
            
            results = {}
            for trend_type in trend_types:
                analysis = await self._analyze_single_trend(filtered_data, trend_type)
                results[trend_type] = analysis
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            raise TrendAnalysisError(
                "Failed to analyze health trends",
                original_error=e
            )
    
    async def _analyze_single_trend(
        self,
        data_points: List[HealthDataPoint],
        trend_type: TrendType
    ) -> TrendAnalysis:
        """Analyze single trend type."""
        try:
            if trend_type == TrendType.LINEAR:
                return await self._linear_trend_analysis(data_points)
            elif trend_type == TrendType.MOVING_AVERAGE:
                return await self._moving_average_analysis(data_points)
            elif trend_type == TrendType.SEASONAL:
                return await self._seasonal_analysis(data_points)
            else:
                # Default to linear analysis
                return await self._linear_trend_analysis(data_points)
                
        except Exception as e:
            raise TrendAnalysisError(
                f"Failed to analyze {trend_type.value} trend",
                trend_type=trend_type.value,
                original_error=e
            )
    
    async def _linear_trend_analysis(self, data_points: List[HealthDataPoint]) -> TrendAnalysis:
        """Perform linear trend analysis."""
        try:
            # Extract response times and timestamps
            times = [(dp.timestamp.timestamp() - data_points[0].timestamp.timestamp()) / 3600 for dp in data_points]  # Hours
            response_times = [dp.response_time for dp in data_points]
            
            if NUMPY_AVAILABLE:
                # Use numpy for more accurate calculations
                times_array = np.array(times)
                response_array = np.array(response_times)
                
                # Calculate linear regression
                slope, intercept = np.polyfit(times_array, response_array, 1)
                correlation = np.corrcoef(times_array, response_array)[0, 1]
                
                # Predict next value
                next_time = times[-1] + 1  # Next hour
                prediction = slope * next_time + intercept
                
            else:
                # Fallback to basic statistics
                n = len(times)
                sum_x = sum(times)
                sum_y = sum(response_times)
                sum_xy = sum(x * y for x, y in zip(times, response_times))
                sum_x2 = sum(x * x for x in times)
                
                # Calculate slope and correlation
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                # Simple correlation approximation
                mean_x = sum_x / n
                mean_y = sum_y / n
                correlation = sum((x - mean_x) * (y - mean_y) for x, y in zip(times, response_times)) / (
                    (sum((x - mean_x) ** 2 for x in times) * sum((y - mean_y) ** 2 for y in response_times)) ** 0.5
                )
                
                # Predict next value
                intercept = mean_y - slope * mean_x
                next_time = times[-1] + 1
                prediction = slope * next_time + intercept
            
            # Determine trend direction
            if abs(slope) < 0.01:  # Threshold for stability
                direction = TrendDirection.STABLE
            elif slope > 0:
                direction = TrendDirection.DEGRADING  # Higher response time is worse
            else:
                direction = TrendDirection.IMPROVING
            
            # Calculate confidence based on correlation
            confidence = abs(correlation) if correlation is not None else 0.0
            
            return TrendAnalysis(
                trend_type=TrendType.LINEAR,
                direction=direction,
                confidence=confidence,
                slope=slope,
                correlation=correlation or 0.0,
                prediction=prediction,
                data_points=len(data_points)
            )
            
        except Exception as e:
            raise TrendAnalysisError(
                "Failed to perform linear trend analysis",
                trend_type="linear",
                original_error=e
            )
    
    async def _moving_average_analysis(self, data_points: List[HealthDataPoint]) -> TrendAnalysis:
        """Perform moving average analysis."""
        try:
            window_size = min(5, len(data_points) // 2)  # Adaptive window size
            response_times = [dp.response_time for dp in data_points]
            
            # Calculate moving averages
            moving_averages = []
            for i in range(window_size, len(response_times)):
                avg = statistics.mean(response_times[i-window_size:i])
                moving_averages.append(avg)
            
            if len(moving_averages) < 2:
                return TrendAnalysis(
                    trend_type=TrendType.MOVING_AVERAGE,
                    direction=TrendDirection.UNKNOWN,
                    confidence=0.0,
                    slope=0.0,
                    correlation=0.0,
                    data_points=len(data_points)
                )
            
            # Calculate trend from moving averages
            first_half = moving_averages[:len(moving_averages)//2]
            second_half = moving_averages[len(moving_averages)//2:]
            
            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)
            
            slope = second_avg - first_avg
            
            # Determine direction
            if abs(slope) < 0.01:
                direction = TrendDirection.STABLE
            elif slope > 0:
                direction = TrendDirection.DEGRADING
            else:
                direction = TrendDirection.IMPROVING
            
            # Calculate volatility as confidence measure
            volatility = statistics.stdev(moving_averages) if len(moving_averages) > 1 else 0
            confidence = max(0, 1 - (volatility / max(moving_averages)))
            
            return TrendAnalysis(
                trend_type=TrendType.MOVING_AVERAGE,
                direction=direction,
                confidence=confidence,
                slope=slope,
                correlation=0.0,  # Not applicable for moving average
                prediction=moving_averages[-1] + slope,
                data_points=len(data_points)
            )
            
        except Exception as e:
            raise TrendAnalysisError(
                "Failed to perform moving average analysis",
                trend_type="moving_average",
                original_error=e
            )
    
    async def _seasonal_analysis(self, data_points: List[HealthDataPoint]) -> TrendAnalysis:
        """Perform seasonal pattern analysis."""
        try:
            # Group by hour of day for seasonal patterns
            hourly_data = {}
            for dp in data_points:
                hour = dp.timestamp.hour
                if hour not in hourly_data:
                    hourly_data[hour] = []
                hourly_data[hour].append(dp.response_time)
            
            # Calculate average response time per hour
            hourly_averages = {
                hour: statistics.mean(times)
                for hour, times in hourly_data.items()
                if len(times) > 0
            }
            
            if len(hourly_averages) < 3:
                return TrendAnalysis(
                    trend_type=TrendType.SEASONAL,
                    direction=TrendDirection.UNKNOWN,
                    confidence=0.0,
                    slope=0.0,
                    correlation=0.0,
                    data_points=len(data_points)
                )
            
            # Calculate seasonal variation
            overall_avg = statistics.mean(hourly_averages.values())
            variations = [abs(avg - overall_avg) for avg in hourly_averages.values()]
            seasonal_strength = statistics.mean(variations) / overall_avg if overall_avg > 0 else 0
            
            # Determine if there's a clear seasonal pattern
            if seasonal_strength > 0.1:  # 10% variation threshold
                direction = TrendDirection.VOLATILE
                confidence = min(1.0, seasonal_strength)
            else:
                direction = TrendDirection.STABLE
                confidence = 1.0 - seasonal_strength
            
            return TrendAnalysis(
                trend_type=TrendType.SEASONAL,
                direction=direction,
                confidence=confidence,
                slope=0.0,  # Not applicable for seasonal
                correlation=seasonal_strength,
                data_points=len(data_points)
            )
            
        except Exception as e:
            raise TrendAnalysisError(
                "Failed to perform seasonal analysis",
                trend_type="seasonal",
                original_error=e
            )
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old data points based on retention policy."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.data_retention_days)
            self._data_points = [
                dp for dp in self._data_points
                if dp.timestamp >= cutoff_time
            ]
        except Exception as e:
            self.logger.warning(f"Error cleaning up old data: {e}")


class TrendAnalyzer:
    """Specialized trend analyzer."""
    
    def __init__(self, config: TrendConfig):
        """Initialize trend analyzer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def detect_anomalies(
        self,
        data_points: List[HealthDataPoint],
        threshold: Optional[float] = None
    ) -> List[HealthDataPoint]:
        """Detect anomalous data points."""
        try:
            threshold = threshold or self.config.outlier_threshold
            
            if len(data_points) < 3:
                return []
            
            response_times = [dp.response_time for dp in data_points]
            mean_time = statistics.mean(response_times)
            std_time = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            anomalies = []
            for dp in data_points:
                if std_time > 0:
                    z_score = abs(dp.response_time - mean_time) / std_time
                    if z_score > threshold:
                        anomalies.append(dp)
            
            return anomalies
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return []


class PatternDetector:
    """Health pattern detection."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize pattern detector."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def detect_patterns(
        self,
        data_points: List[HealthDataPoint]
    ) -> Dict[str, Any]:
        """Detect health patterns."""
        try:
            patterns = {
                'cyclical': await self._detect_cyclical_patterns(data_points),
                'degradation': await self._detect_degradation_patterns(data_points),
                'recovery': await self._detect_recovery_patterns(data_points)
            }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error detecting patterns: {e}")
            return {}
    
    async def _detect_cyclical_patterns(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Detect cyclical patterns in health data."""
        # Simplified cyclical detection
        return {
            'detected': False,
            'period': None,
            'confidence': 0.0
        }
    
    async def _detect_degradation_patterns(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Detect degradation patterns."""
        if len(data_points) < 5:
            return {'detected': False, 'severity': 0.0}
        
        # Check for consistent increase in response times
        recent_times = [dp.response_time for dp in data_points[-5:]]
        is_degrading = all(
            recent_times[i] >= recent_times[i-1]
            for i in range(1, len(recent_times))
        )
        
        severity = 0.0
        if is_degrading:
            severity = (recent_times[-1] - recent_times[0]) / recent_times[0] if recent_times[0] > 0 else 0
        
        return {
            'detected': is_degrading,
            'severity': min(1.0, severity)
        }
    
    async def _detect_recovery_patterns(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Detect recovery patterns."""
        if len(data_points) < 5:
            return {'detected': False, 'improvement': 0.0}
        
        # Check for consistent decrease in response times
        recent_times = [dp.response_time for dp in data_points[-5:]]
        is_recovering = all(
            recent_times[i] <= recent_times[i-1]
            for i in range(1, len(recent_times))
        )
        
        improvement = 0.0
        if is_recovering and recent_times[-1] > 0:
            improvement = (recent_times[0] - recent_times[-1]) / recent_times[0]
        
        return {
            'detected': is_recovering,
            'improvement': min(1.0, improvement)
        }


def create_health_analyzer(config: AnalyticsConfig) -> HealthAnalyzer:
    """Create health analyzer instance."""
    return HealthAnalyzer(config)


# Export main classes
__all__ = [
    'TrendDirection',
    'HealthDataPoint',
    'TrendAnalysis',
    'HealthAnalyzer',
    'TrendAnalyzer',
    'PatternDetector',
    'create_health_analyzer',
]
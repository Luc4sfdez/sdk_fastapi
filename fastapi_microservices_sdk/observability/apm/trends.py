"""
Trend Analysis and Capacity Planning for FastAPI Microservices SDK.

This module provides performance trend analysis and capacity planning
insights for proactive resource management.

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
from collections import defaultdict, deque
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from .config import APMConfig, TrendDirection
from .exceptions import TrendAnalysisError


class TrendType(str, Enum):
    """Trend type enumeration."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"
    VOLATILE = "volatile"


@dataclass
class PerformanceTrend:
    """Performance trend analysis result."""
    trend_id: str
    metric_name: str
    trend_type: TrendType
    trend_direction: TrendDirection
    trend_strength: float  # 0-1 scale
    growth_rate: float  # percentage per day
    confidence_level: float
    analysis_period: timedelta
    forecast_horizon: timedelta
    predicted_values: List[Tuple[datetime, float]]
    statistical_significance: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trend_id': self.trend_id,
            'metric_name': self.metric_name,
            'trend_type': self.trend_type.value,
            'trend_direction': self.trend_direction.value,
            'trend_strength': self.trend_strength,
            'growth_rate': self.growth_rate,
            'confidence_level': self.confidence_level,
            'analysis_period': self.analysis_period.total_seconds(),
            'forecast_horizon': self.forecast_horizon.total_seconds(),
            'predicted_values': [
                (dt.isoformat(), val) for dt, val in self.predicted_values
            ],
            'statistical_significance': self.statistical_significance
        }


@dataclass
class CapacityInsight:
    """Capacity planning insight."""
    insight_id: str
    resource_type: str
    current_utilization: float
    projected_utilization: float
    capacity_exhaustion_date: Optional[datetime]
    recommended_action: str
    urgency_level: str  # "low", "medium", "high", "critical"
    cost_impact: str  # "low", "medium", "high"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'insight_id': self.insight_id,
            'resource_type': self.resource_type,
            'current_utilization': self.current_utilization,
            'projected_utilization': self.projected_utilization,
            'capacity_exhaustion_date': self.capacity_exhaustion_date.isoformat() if self.capacity_exhaustion_date else None,
            'recommended_action': self.recommended_action,
            'urgency_level': self.urgency_level,
            'cost_impact': self.cost_impact
        }


class TrendAnalyzer:
    """Performance trend analyzer and capacity planner."""
    
    def __init__(self, config: APMConfig):
        """Initialize trend analyzer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Trend analysis state
        self.trend_history: List[PerformanceTrend] = []
        self.capacity_insights: List[CapacityInsight] = []
        
        # Metrics storage
        self.metric_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        
        # ML models for forecasting
        self.forecasting_models: Dict[str, Any] = {}
        
        # Background tasks
        self.is_running = False
        self.analysis_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start trend analyzer."""
        try:
            if self.is_running:
                self.logger.warning("Trend analyzer is already running")
                return
            
            self.logger.info("Starting trend analyzer...")
            
            # Start background analysis
            if self.config.trend.enabled:
                self.analysis_task = asyncio.create_task(self._analysis_loop())
            
            self.is_running = True
            self.logger.info("Trend analyzer started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting trend analyzer: {e}")
            raise TrendAnalysisError(
                f"Failed to start trend analyzer: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop trend analyzer."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping trend analyzer...")
            
            # Cancel background tasks
            if self.analysis_task:
                self.analysis_task.cancel()
                try:
                    await self.analysis_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Trend analyzer stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping trend analyzer: {e}")
    
    async def add_metric_data(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add metric data for trend analysis."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            self.metric_data[metric_name].append((timestamp, value))
            
        except Exception as e:
            self.logger.error(f"Error adding metric data: {e}")
    
    async def analyze_trend(self, metric_name: str, analysis_period: Optional[timedelta] = None) -> Optional[PerformanceTrend]:
        """Analyze trend for a specific metric."""
        try:
            if analysis_period is None:
                analysis_period = self.config.trend.trend_window
            
            # Get data for analysis period
            cutoff_time = datetime.now(timezone.utc) - analysis_period
            data_points = [
                (timestamp, value) for timestamp, value in self.metric_data[metric_name]
                if timestamp >= cutoff_time
            ]
            
            if len(data_points) < self.config.trend.min_data_points:
                return None
            
            # Prepare data for analysis
            timestamps = [point[0] for point in data_points]
            values = [point[1] for point in data_points]
            
            # Convert timestamps to numeric values (seconds since first timestamp)
            base_time = timestamps[0]
            x_values = [(ts - base_time).total_seconds() for ts in timestamps]
            
            # Perform trend analysis
            trend_result = await self._perform_trend_analysis(
                metric_name, x_values, values, analysis_period
            )
            
            if trend_result:
                self.trend_history.append(trend_result)
                
                # Maintain history size
                if len(self.trend_history) > 1000:
                    self.trend_history = self.trend_history[-1000:]
            
            return trend_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend for {metric_name}: {e}")
            raise TrendAnalysisError(
                f"Failed to analyze trend: {e}",
                analysis_type="trend_analysis",
                original_error=e
            )
    
    async def generate_capacity_insights(self, resource_type: str) -> List[CapacityInsight]:
        """Generate capacity planning insights."""
        try:
            insights = []
            
            # Find metrics related to the resource type
            related_metrics = [
                name for name in self.metric_data.keys()
                if resource_type.lower() in name.lower()
            ]
            
            for metric_name in related_metrics:
                # Analyze trend for capacity planning
                trend = await self.analyze_trend(metric_name)
                
                if not trend:
                    continue
                
                # Generate capacity insight
                insight = await self._generate_capacity_insight(trend, resource_type)
                if insight:
                    insights.append(insight)
            
            self.capacity_insights.extend(insights)
            
            # Maintain insights size
            if len(self.capacity_insights) > 500:
                self.capacity_insights = self.capacity_insights[-500:]
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating capacity insights: {e}")
            raise TrendAnalysisError(
                f"Failed to generate capacity insights: {e}",
                analysis_type="capacity_planning",
                original_error=e
            )
    
    async def forecast_metric(self, metric_name: str, forecast_horizon: timedelta) -> List[Tuple[datetime, float]]:
        """Forecast metric values."""
        try:
            # Get recent data
            recent_data = list(self.metric_data[metric_name])[-100:]
            
            if len(recent_data) < 20:
                return []
            
            # Prepare data
            timestamps = [point[0] for point in recent_data]
            values = [point[1] for point in recent_data]
            
            # Convert to numeric
            base_time = timestamps[0]
            x_values = np.array([(ts - base_time).total_seconds() for ts in timestamps]).reshape(-1, 1)
            y_values = np.array(values)
            
            # Train forecasting model
            model = LinearRegression()
            model.fit(x_values, y_values)
            
            # Generate forecast
            forecast_points = []
            start_time = timestamps[-1]
            forecast_seconds = forecast_horizon.total_seconds()
            
            for i in range(1, 25):  # 24 forecast points
                future_time = start_time + timedelta(seconds=forecast_seconds * i / 24)
                future_x = np.array([[(future_time - base_time).total_seconds()]])
                predicted_value = model.predict(future_x)[0]
                forecast_points.append((future_time, max(0, predicted_value)))
            
            return forecast_points
            
        except Exception as e:
            self.logger.error(f"Error forecasting metric {metric_name}: {e}")
            return []
    
    async def _perform_trend_analysis(
        self,
        metric_name: str,
        x_values: List[float],
        y_values: List[float],
        analysis_period: timedelta
    ) -> Optional[PerformanceTrend]:
        """Perform statistical trend analysis."""
        try:
            # Linear regression for trend detection
            x_array = np.array(x_values).reshape(-1, 1)
            y_array = np.array(y_values)
            
            model = LinearRegression()
            model.fit(x_array, y_array)
            
            # Calculate trend metrics
            slope = model.coef_[0]
            r_squared = model.score(x_array, y_array)
            
            # Statistical significance test
            n = len(x_values)
            if n > 2:
                t_stat = slope * np.sqrt((n - 2) / (1 - r_squared)) if r_squared < 1 else 0
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2)) if t_stat != 0 else 1
            else:
                p_value = 1.0
            
            # Determine trend direction and strength
            if abs(slope) < 1e-6:
                trend_direction = TrendDirection.STABLE
                trend_strength = 0.0
            elif slope > 0:
                trend_direction = TrendDirection.INCREASING
                trend_strength = min(abs(slope) / (max(y_values) - min(y_values)) * 100, 1.0)
            else:
                trend_direction = TrendDirection.DECREASING
                trend_strength = min(abs(slope) / (max(y_values) - min(y_values)) * 100, 1.0)
            
            # Calculate growth rate (percentage per day)
            if len(y_values) > 1:
                time_span_days = (x_values[-1] - x_values[0]) / 86400  # Convert to days
                if time_span_days > 0:
                    growth_rate = (slope * 86400 / statistics.mean(y_values)) * 100  # % per day
                else:
                    growth_rate = 0.0
            else:
                growth_rate = 0.0
            
            # Generate forecast
            forecast_horizon = self.config.trend.planning_horizon
            forecast_points = await self.forecast_metric(metric_name, forecast_horizon)
            
            # Determine trend type (simplified)
            if r_squared > 0.8:
                trend_type = TrendType.LINEAR
            elif r_squared > 0.5:
                trend_type = TrendType.EXPONENTIAL
            else:
                trend_type = TrendType.VOLATILE
            
            trend_id = f"trend_{metric_name}_{int(datetime.now().timestamp())}"
            
            return PerformanceTrend(
                trend_id=trend_id,
                metric_name=metric_name,
                trend_type=trend_type,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                growth_rate=growth_rate,
                confidence_level=r_squared,
                analysis_period=analysis_period,
                forecast_horizon=forecast_horizon,
                predicted_values=forecast_points,
                statistical_significance=p_value
            )
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis: {e}")
            return None
    
    async def _generate_capacity_insight(self, trend: PerformanceTrend, resource_type: str) -> Optional[CapacityInsight]:
        """Generate capacity planning insight from trend."""
        try:
            # Get current utilization
            recent_data = list(self.metric_data[trend.metric_name])[-10:]
            if not recent_data:
                return None
            
            current_utilization = statistics.mean([point[1] for point in recent_data])
            
            # Project future utilization
            days_ahead = self.config.trend.planning_horizon.days
            projected_growth = trend.growth_rate * days_ahead
            projected_utilization = current_utilization + (current_utilization * projected_growth / 100)
            
            # Determine capacity exhaustion date
            capacity_threshold = 90.0  # 90% utilization threshold
            exhaustion_date = None
            
            if trend.growth_rate > 0 and current_utilization < capacity_threshold:
                days_to_exhaustion = (capacity_threshold - current_utilization) / (current_utilization * trend.growth_rate / 100)
                if days_to_exhaustion > 0:
                    exhaustion_date = datetime.now(timezone.utc) + timedelta(days=days_to_exhaustion)
            
            # Determine urgency and recommended action
            if exhaustion_date and exhaustion_date <= datetime.now(timezone.utc) + timedelta(days=30):
                urgency_level = "critical"
                recommended_action = f"Immediate {resource_type} scaling required"
                cost_impact = "high"
            elif exhaustion_date and exhaustion_date <= datetime.now(timezone.utc) + timedelta(days=90):
                urgency_level = "high"
                recommended_action = f"Plan {resource_type} scaling within 90 days"
                cost_impact = "medium"
            elif projected_utilization > 80:
                urgency_level = "medium"
                recommended_action = f"Monitor {resource_type} usage closely"
                cost_impact = "low"
            else:
                urgency_level = "low"
                recommended_action = f"Continue monitoring {resource_type}"
                cost_impact = "low"
            
            insight_id = f"capacity_{resource_type}_{int(datetime.now().timestamp())}"
            
            return CapacityInsight(
                insight_id=insight_id,
                resource_type=resource_type,
                current_utilization=current_utilization,
                projected_utilization=projected_utilization,
                capacity_exhaustion_date=exhaustion_date,
                recommended_action=recommended_action,
                urgency_level=urgency_level,
                cost_impact=cost_impact
            )
            
        except Exception as e:
            self.logger.error(f"Error generating capacity insight: {e}")
            return None
    
    async def _analysis_loop(self):
        """Background trend analysis loop."""
        while self.is_running:
            try:
                # Analyze trends periodically
                await asyncio.sleep(3600)  # Every hour
                
                if not self.is_running:
                    break
                
                # Analyze trends for all metrics with sufficient data
                for metric_name in list(self.metric_data.keys()):
                    if len(self.metric_data[metric_name]) >= self.config.trend.min_data_points:
                        try:
                            await self.analyze_trend(metric_name)
                        except Exception as e:
                            self.logger.error(f"Error analyzing trend for {metric_name}: {e}")
                
                # Generate capacity insights
                resource_types = ["cpu", "memory", "disk", "network"]
                for resource_type in resource_types:
                    try:
                        await self.generate_capacity_insights(resource_type)
                    except Exception as e:
                        self.logger.error(f"Error generating capacity insights for {resource_type}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in trend analysis loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def get_trend_history(self, metric_name: Optional[str] = None, limit: int = 100) -> List[PerformanceTrend]:
        """Get trend analysis history."""
        if metric_name:
            trends = [t for t in self.trend_history if t.metric_name == metric_name]
        else:
            trends = self.trend_history
        
        return trends[-limit:]
    
    async def get_capacity_insights(self, resource_type: Optional[str] = None, limit: int = 50) -> List[CapacityInsight]:
        """Get capacity planning insights."""
        if resource_type:
            insights = [i for i in self.capacity_insights if i.resource_type == resource_type]
        else:
            insights = self.capacity_insights
        
        return insights[-limit:]
    
    async def get_analyzer_health(self) -> Dict[str, Any]:
        """Get trend analyzer health status."""
        return {
            'is_running': self.is_running,
            'metrics_tracked': len(self.metric_data),
            'trends_analyzed': len(self.trend_history),
            'capacity_insights': len(self.capacity_insights),
            'forecasting_models': len(self.forecasting_models)
        }


def create_trend_analyzer(config: APMConfig) -> TrendAnalyzer:
    """Create trend analyzer instance."""
    return TrendAnalyzer(config)
"""
Advanced Health Analytics and Reporting for FastAPI Microservices SDK.

This module provides health trend analysis, predictive monitoring,
performance optimization, and comprehensive reporting capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import deque, defaultdict
import logging

# Optional dependencies for advanced analytics
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .config import HealthConfig, HealthStatus
from .monitor import HealthMonitor, HealthCheckResult
from .exceptions import HealthCheckError


class TrendDirection(str, Enum):
    """Health trend direction enumeration."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


class PredictionConfidence(str, Enum):
    """Prediction confidence level enumeration."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Health metric data point."""
    timestamp: datetime
    value: float
    status: HealthStatus
    check_name: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'status': self.status.value,
            'check_name': self.check_name,
            'duration_ms': self.duration_ms,
            'metadata': self.metadata
        }


@dataclass
class HealthTrend:
    """Health trend analysis result."""
    check_name: str
    direction: TrendDirection
    slope: float
    confidence: float
    period_hours: int
    data_points: int
    current_value: float
    predicted_value: Optional[float] = None
    prediction_confidence: PredictionConfidence = PredictionConfidence.UNKNOWN
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'check_name': self.check_name,
            'direction': self.direction.value,
            'slope': self.slope,
            'confidence': self.confidence,
            'period_hours': self.period_hours,
            'data_points': self.data_points,
            'current_value': self.current_value,
            'predicted_value': self.predicted_value,
            'prediction_confidence': self.prediction_confidence.value
        }


@dataclass
class HealthPrediction:
    """Health prediction result."""
    check_name: str
    predicted_status: HealthStatus
    predicted_value: float
    confidence: PredictionConfidence
    prediction_horizon_hours: int
    factors: List[str] = field(default_factory=list)
    risk_level: str = "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'check_name': self.check_name,
            'predicted_status': self.predicted_status.value,
            'predicted_value': self.predicted_value,
            'confidence': self.confidence.value,
            'prediction_horizon_hours': self.prediction_horizon_hours,
            'factors': self.factors,
            'risk_level': self.risk_level
        }


@dataclass
class HealthReport:
    """Comprehensive health report."""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # Summary statistics
    total_checks: int
    healthy_percentage: float
    average_response_time: float
    
    # Trend analysis
    trends: List[HealthTrend] = field(default_factory=list)
    predictions: List[HealthPrediction] = field(default_factory=list)
    
    # Performance metrics
    performance_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'total_checks': self.total_checks,
            'healthy_percentage': self.healthy_percentage,
            'average_response_time': self.average_response_time,
            'trends': [trend.to_dict() for trend in self.trends],
            'predictions': [pred.to_dict() for pred in self.predictions],
            'performance_summary': self.performance_summary,
            'recommendations': self.recommendations
        }


class HealthAnalytics:
    """Advanced health analytics engine."""
    
    def __init__(self, config: HealthConfig, health_monitor: HealthMonitor):
        self.config = config
        self.health_monitor = health_monitor
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self._metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._performance_history: deque = deque(maxlen=1000)
        
        # Analytics configuration
        self._trend_analysis_window = 24  # hours
        self._prediction_horizon = 4  # hours
        self._min_data_points = 10
        
        # Statistics
        self._analysis_count = 0
        self._prediction_count = 0
        self._trend_accuracy = 0.0
        
        # Background analytics
        self._analytics_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Performance optimization
        self._last_optimization = None
        self._optimization_interval = 3600  # 1 hour
    
    async def start_analytics(self):
        """Start background analytics processing."""
        async def analytics_loop():
            while not self._shutdown_event.is_set():
                try:
                    await self._collect_metrics()
                    await self._analyze_trends()
                    await self._optimize_performance()
                    await asyncio.sleep(300)  # 5 minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in analytics loop: {e}")
                    await asyncio.sleep(60)
        
        self._analytics_task = asyncio.create_task(analytics_loop())
        self.logger.info("Health analytics started")
    
    async def stop_analytics(self):
        """Stop background analytics processing."""
        self._shutdown_event.set()
        
        if self._analytics_task:
            self._analytics_task.cancel()
            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Health analytics stopped")
    
    async def _collect_metrics(self):
        """Collect health metrics for analysis."""
        try:
            # Get current health status
            health_results = await self.health_monitor.check_health()
            
            current_time = datetime.now(timezone.utc)
            
            for check_name, result in health_results.items():
                # Convert health status to numeric value for analysis
                status_value = self._status_to_numeric(result.status)
                
                metric = HealthMetric(
                    timestamp=current_time,
                    value=status_value,
                    status=result.status,
                    check_name=check_name,
                    duration_ms=result.duration_ms,
                    metadata=result.details
                )
                
                self._metrics_history[check_name].append(metric)
            
            # Collect performance metrics
            stats = self.health_monitor.get_health_statistics()
            self._performance_history.append({
                'timestamp': current_time,
                'total_checks': stats['total_checks'],
                'failure_rate': stats['failure_rate'],
                'average_check_time_ms': stats['average_check_time_ms']
            })
            
        except Exception as e:
            self.logger.error(f"Failed to collect metrics: {e}")
    
    def _status_to_numeric(self, status: HealthStatus) -> float:
        """Convert health status to numeric value."""
        mapping = {
            HealthStatus.HEALTHY: 1.0,
            HealthStatus.DEGRADED: 0.5,
            HealthStatus.UNHEALTHY: 0.0,
            HealthStatus.UNKNOWN: 0.25
        }
        return mapping.get(status, 0.0)
    
    def _numeric_to_status(self, value: float) -> HealthStatus:
        """Convert numeric value to health status."""
        if value >= 0.8:
            return HealthStatus.HEALTHY
        elif value >= 0.4:
            return HealthStatus.DEGRADED
        elif value >= 0.1:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    async def _analyze_trends(self):
        """Analyze health trends."""
        try:
            self._analysis_count += 1
            
            for check_name, metrics in self._metrics_history.items():
                if len(metrics) < self._min_data_points:
                    continue
                
                # Analyze trend for this check
                trend = self._calculate_trend(check_name, metrics)
                if trend:
                    # Store trend for reporting
                    # In a real implementation, you'd store this in a database
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to analyze trends: {e}")
    
    def _calculate_trend(self, check_name: str, metrics: deque) -> Optional[HealthTrend]:
        """Calculate trend for a specific health check."""
        try:
            # Get recent metrics within the analysis window
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self._trend_analysis_window)
            recent_metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if len(recent_metrics) < self._min_data_points:
                return None
            
            # Extract values and timestamps
            values = [m.value for m in recent_metrics]
            timestamps = [(m.timestamp - recent_metrics[0].timestamp).total_seconds() / 3600 
                         for m in recent_metrics]
            
            # Calculate trend using linear regression if available
            if SKLEARN_AVAILABLE and len(values) > 5:
                slope, confidence = self._calculate_linear_trend(timestamps, values)
            else:
                # Simple slope calculation
                slope = self._calculate_simple_slope(timestamps, values)
                confidence = 0.5  # Medium confidence for simple calculation
            
            # Determine trend direction
            direction = self._determine_trend_direction(slope, confidence)
            
            # Calculate prediction if possible
            predicted_value = None
            prediction_confidence = PredictionConfidence.UNKNOWN
            
            if confidence > 0.6 and len(values) > 10:
                predicted_value = values[-1] + (slope * self._prediction_horizon)
                prediction_confidence = self._calculate_prediction_confidence(confidence, len(values))
            
            return HealthTrend(
                check_name=check_name,
                direction=direction,
                slope=slope,
                confidence=confidence,
                period_hours=self._trend_analysis_window,
                data_points=len(recent_metrics),
                current_value=values[-1],
                predicted_value=predicted_value,
                prediction_confidence=prediction_confidence
            )
            
        except Exception as e:
            self.logger.error(f"Failed to calculate trend for {check_name}: {e}")
            return None
    
    def _calculate_linear_trend(self, timestamps: List[float], values: List[float]) -> Tuple[float, float]:
        """Calculate linear trend using scikit-learn."""
        try:
            X = np.array(timestamps).reshape(-1, 1)
            y = np.array(values)
            
            model = LinearRegression()
            model.fit(X, y)
            
            slope = model.coef_[0]
            r_squared = model.score(X, y)
            
            return slope, r_squared
            
        except Exception as e:
            self.logger.error(f"Linear trend calculation failed: {e}")
            return 0.0, 0.0
    
    def _calculate_simple_slope(self, timestamps: List[float], values: List[float]) -> float:
        """Calculate simple slope using least squares."""
        try:
            n = len(timestamps)
            if n < 2:
                return 0.0
            
            sum_x = sum(timestamps)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(timestamps, values))
            sum_x2 = sum(x * x for x in timestamps)
            
            denominator = n * sum_x2 - sum_x * sum_x
            if abs(denominator) < 1e-10:
                return 0.0
            
            slope = (n * sum_xy - sum_x * sum_y) / denominator
            return slope
            
        except Exception as e:
            self.logger.error(f"Simple slope calculation failed: {e}")
            return 0.0
    
    def _determine_trend_direction(self, slope: float, confidence: float) -> TrendDirection:
        """Determine trend direction from slope and confidence."""
        if confidence < 0.3:
            return TrendDirection.VOLATILE
        
        if abs(slope) < 0.01:
            return TrendDirection.STABLE
        elif slope > 0:
            return TrendDirection.IMPROVING
        else:
            return TrendDirection.DEGRADING
    
    def _calculate_prediction_confidence(self, trend_confidence: float, data_points: int) -> PredictionConfidence:
        """Calculate prediction confidence level."""
        # Combine trend confidence with data sufficiency
        data_factor = min(data_points / 50, 1.0)  # More data = higher confidence
        combined_confidence = trend_confidence * data_factor
        
        if combined_confidence >= 0.8:
            return PredictionConfidence.HIGH
        elif combined_confidence >= 0.6:
            return PredictionConfidence.MEDIUM
        elif combined_confidence >= 0.3:
            return PredictionConfidence.LOW
        else:
            return PredictionConfidence.UNKNOWN
    
    async def _optimize_performance(self):
        """Optimize health check performance based on analytics."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check if optimization is due
            if (self._last_optimization and 
                (current_time - self._last_optimization).total_seconds() < self._optimization_interval):
                return
            
            # Analyze performance patterns
            if len(self._performance_history) < 10:
                return
            
            recent_performance = list(self._performance_history)[-10:]
            
            # Calculate average response times
            avg_response_times = {}
            for check_name, metrics in self._metrics_history.items():
                if len(metrics) > 0:
                    recent_metrics = [m for m in metrics 
                                    if (current_time - m.timestamp).total_seconds() < 3600]
                    if recent_metrics:
                        avg_response_times[check_name] = statistics.mean(
                            [m.duration_ms for m in recent_metrics]
                        )
            
            # Identify slow checks
            slow_checks = {name: time_ms for name, time_ms in avg_response_times.items() 
                          if time_ms > 5000}  # > 5 seconds
            
            if slow_checks:
                self.logger.warning(f"Slow health checks detected: {slow_checks}")
                # In a real implementation, you could:
                # - Increase timeouts for slow checks
                # - Reduce check frequency for non-critical checks
                # - Enable caching for expensive checks
            
            # Update optimization timestamp
            self._last_optimization = current_time
            
        except Exception as e:
            self.logger.error(f"Performance optimization failed: {e}")
    
    async def generate_predictions(self, horizon_hours: int = 4) -> List[HealthPrediction]:
        """Generate health predictions."""
        predictions = []
        
        try:
            self._prediction_count += 1
            
            for check_name, metrics in self._metrics_history.items():
                if len(metrics) < self._min_data_points:
                    continue
                
                prediction = await self._predict_health_status(check_name, metrics, horizon_hours)
                if prediction:
                    predictions.append(prediction)
            
        except Exception as e:
            self.logger.error(f"Failed to generate predictions: {e}")
        
        return predictions
    
    async def _predict_health_status(
        self, 
        check_name: str, 
        metrics: deque, 
        horizon_hours: int
    ) -> Optional[HealthPrediction]:
        """Predict health status for a specific check."""
        try:
            # Get recent trend
            trend = self._calculate_trend(check_name, metrics)
            if not trend or trend.predicted_value is None:
                return None
            
            # Predict status based on trend
            predicted_status = self._numeric_to_status(trend.predicted_value)
            
            # Determine risk factors
            factors = []
            risk_level = "low"
            
            if trend.direction == TrendDirection.DEGRADING:
                factors.append("degrading_trend")
                risk_level = "medium" if trend.confidence > 0.7 else "low"
            
            if trend.predicted_value < 0.3:
                factors.append("predicted_unhealthy")
                risk_level = "high"
            
            # Check for volatility
            recent_metrics = list(metrics)[-20:]  # Last 20 data points
            if len(recent_metrics) > 5:
                values = [m.value for m in recent_metrics]
                volatility = statistics.stdev(values) if len(values) > 1 else 0
                if volatility > 0.3:
                    factors.append("high_volatility")
                    risk_level = "medium"
            
            return HealthPrediction(
                check_name=check_name,
                predicted_status=predicted_status,
                predicted_value=trend.predicted_value,
                confidence=trend.prediction_confidence,
                prediction_horizon_hours=horizon_hours,
                factors=factors,
                risk_level=risk_level
            )
            
        except Exception as e:
            self.logger.error(f"Failed to predict health for {check_name}: {e}")
            return None
    
    async def generate_health_report(
        self, 
        period_hours: int = 24
    ) -> HealthReport:
        """Generate comprehensive health report."""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=period_hours)
            
            # Collect metrics for the period
            all_metrics = []
            for metrics in self._metrics_history.values():
                period_metrics = [m for m in metrics if start_time <= m.timestamp <= end_time]
                all_metrics.extend(period_metrics)
            
            # Calculate summary statistics
            total_checks = len(all_metrics)
            healthy_count = sum(1 for m in all_metrics if m.status == HealthStatus.HEALTHY)
            healthy_percentage = (healthy_count / total_checks * 100) if total_checks > 0 else 0
            
            avg_response_time = statistics.mean([m.duration_ms for m in all_metrics]) if all_metrics else 0
            
            # Generate trends and predictions
            trends = []
            predictions = await self.generate_predictions()
            
            for check_name in self._metrics_history.keys():
                trend = self._calculate_trend(check_name, self._metrics_history[check_name])
                if trend:
                    trends.append(trend)
            
            # Performance summary
            performance_summary = {
                'average_response_time_ms': avg_response_time,
                'slowest_checks': self._get_slowest_checks(),
                'most_volatile_checks': self._get_most_volatile_checks(),
                'optimization_opportunities': self._get_optimization_opportunities()
            }
            
            # Generate recommendations
            recommendations = self._generate_recommendations(trends, predictions, all_metrics)
            
            report = HealthReport(
                report_id=f"health-report-{int(end_time.timestamp())}",
                generated_at=end_time,
                period_start=start_time,
                period_end=end_time,
                total_checks=total_checks,
                healthy_percentage=healthy_percentage,
                average_response_time=avg_response_time,
                trends=trends,
                predictions=predictions,
                performance_summary=performance_summary,
                recommendations=recommendations
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate health report: {e}")
            raise HealthCheckError(f"Report generation failed: {e}")
    
    def _get_slowest_checks(self) -> List[Dict[str, Any]]:
        """Get slowest health checks."""
        slowest = []
        
        for check_name, metrics in self._metrics_history.items():
            if len(metrics) > 0:
                recent_metrics = list(metrics)[-10:]
                avg_time = statistics.mean([m.duration_ms for m in recent_metrics])
                slowest.append({
                    'check_name': check_name,
                    'average_duration_ms': avg_time
                })
        
        return sorted(slowest, key=lambda x: x['average_duration_ms'], reverse=True)[:5]
    
    def _get_most_volatile_checks(self) -> List[Dict[str, Any]]:
        """Get most volatile health checks."""
        volatile = []
        
        for check_name, metrics in self._metrics_history.items():
            if len(metrics) > 5:
                recent_metrics = list(metrics)[-20:]
                values = [m.value for m in recent_metrics]
                volatility = statistics.stdev(values) if len(values) > 1 else 0
                volatile.append({
                    'check_name': check_name,
                    'volatility': volatility
                })
        
        return sorted(volatile, key=lambda x: x['volatility'], reverse=True)[:5]
    
    def _get_optimization_opportunities(self) -> List[str]:
        """Get optimization opportunities."""
        opportunities = []
        
        # Check for slow checks
        slowest = self._get_slowest_checks()
        if slowest and slowest[0]['average_duration_ms'] > 5000:
            opportunities.append(f"Optimize slow check: {slowest[0]['check_name']}")
        
        # Check for volatile checks
        volatile = self._get_most_volatile_checks()
        if volatile and volatile[0]['volatility'] > 0.3:
            opportunities.append(f"Stabilize volatile check: {volatile[0]['check_name']}")
        
        # Check cache hit rate
        if hasattr(self.health_monitor, '_cache_hits') and hasattr(self.health_monitor, '_search_count'):
            cache_hit_rate = (self.health_monitor._cache_hits / 
                            max(1, self.health_monitor._search_count))
            if cache_hit_rate < 0.5:
                opportunities.append("Improve health check caching")
        
        return opportunities
    
    def _generate_recommendations(
        self, 
        trends: List[HealthTrend], 
        predictions: List[HealthPrediction],
        metrics: List[HealthMetric]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Trend-based recommendations
        degrading_trends = [t for t in trends if t.direction == TrendDirection.DEGRADING]
        if degrading_trends:
            recommendations.append(
                f"Monitor degrading health checks: {', '.join([t.check_name for t in degrading_trends])}"
            )
        
        # Prediction-based recommendations
        high_risk_predictions = [p for p in predictions if p.risk_level == "high"]
        if high_risk_predictions:
            recommendations.append(
                f"Take preventive action for high-risk checks: {', '.join([p.check_name for p in high_risk_predictions])}"
            )
        
        # Performance-based recommendations
        if metrics:
            avg_response_time = statistics.mean([m.duration_ms for m in metrics])
            if avg_response_time > 3000:
                recommendations.append("Consider optimizing health check performance")
        
        # Reliability recommendations
        failure_rate = len([m for m in metrics if m.status != HealthStatus.HEALTHY]) / len(metrics) if metrics else 0
        if failure_rate > 0.1:
            recommendations.append("Investigate high failure rate in health checks")
        
        return recommendations
    
    def get_analytics_statistics(self) -> Dict[str, Any]:
        """Get analytics statistics."""
        return {
            'analysis_count': self._analysis_count,
            'prediction_count': self._prediction_count,
            'trend_accuracy': self._trend_accuracy,
            'metrics_stored': sum(len(metrics) for metrics in self._metrics_history.values()),
            'checks_monitored': len(self._metrics_history),
            'performance_history_size': len(self._performance_history),
            'last_optimization': self._last_optimization.isoformat() if self._last_optimization else None,
            'numpy_available': NUMPY_AVAILABLE,
            'sklearn_available': SKLEARN_AVAILABLE
        }


def create_health_analytics(
    config: HealthConfig,
    health_monitor: HealthMonitor
) -> HealthAnalytics:
    """Create health analytics instance."""
    return HealthAnalytics(config, health_monitor)


# Export main classes and functions
__all__ = [
    'TrendDirection',
    'PredictionConfidence',
    'HealthMetric',
    'HealthTrend',
    'HealthPrediction',
    'HealthReport',
    'HealthAnalytics',
    'create_health_analytics',
]
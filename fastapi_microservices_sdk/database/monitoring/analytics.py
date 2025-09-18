"""
Database analytics and performance analysis.

This module provides advanced analytics capabilities for database
performance analysis, trend detection, and optimization recommendations.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import re
from collections import defaultdict, Counter
import json
import math

from ..adapters.base import DatabaseAdapter
from ..config import DatabaseEngine
from .config import MonitoringConfig
from .metrics import MetricsCollector, DatabaseMetrics, MetricValue
from .exceptions import MonitoringError


class AnalysisType(Enum):
    """Types of analytics analysis."""
    PERFORMANCE_TREND = "performance_trend"
    QUERY_OPTIMIZATION = "query_optimization"
    RESOURCE_UTILIZATION = "resource_utilization"
    ANOMALY_DETECTION = "anomaly_detection"
    CAPACITY_PLANNING = "capacity_planning"
    HEALTH_ASSESSMENT = "health_assessment"


class Severity(Enum):
    """Severity levels for findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(Enum):
    """Trend direction indicators."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


@dataclass
class AnalyticsFinding:
    """Individual analytics finding."""
    finding_id: str
    analysis_type: AnalysisType
    severity: Severity
    title: str
    description: str
    recommendation: str
    affected_metrics: List[str] = field(default_factory=list)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'finding_id': self.finding_id,
            'analysis_type': self.analysis_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'recommendation': self.recommendation,
            'affected_metrics': self.affected_metrics,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class PerformanceTrend:
    """Performance trend analysis result."""
    metric_name: str
    direction: TrendDirection
    change_percentage: float
    baseline_value: float
    current_value: float
    trend_confidence: float
    period_analyzed: timedelta
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'direction': self.direction.value,
            'change_percentage': self.change_percentage,
            'baseline_value': self.baseline_value,
            'current_value': self.current_value,
            'trend_confidence': self.trend_confidence,
            'period_analyzed': self.period_analyzed.total_seconds()
        }


@dataclass
class QueryOptimizationSuggestion:
    """Query optimization suggestion."""
    query_pattern: str
    issue_type: str
    description: str
    suggestion: str
    estimated_improvement: float
    confidence: float
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query_pattern': self.query_pattern,
            'issue_type': self.issue_type,
            'description': self.description,
            'suggestion': self.suggestion,
            'estimated_improvement': self.estimated_improvement,
            'confidence': self.confidence,
            'examples': self.examples
        }


@dataclass
class ResourceUtilizationAnalysis:
    """Resource utilization analysis result."""
    resource_type: str
    current_utilization: float
    peak_utilization: float
    average_utilization: float
    trend: TrendDirection
    projected_exhaustion: Optional[datetime] = None
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'resource_type': self.resource_type,
            'current_utilization': self.current_utilization,
            'peak_utilization': self.peak_utilization,
            'average_utilization': self.average_utilization,
            'trend': self.trend.value,
            'projected_exhaustion': self.projected_exhaustion.isoformat() if self.projected_exhaustion else None,
            'recommendations': self.recommendations
        }


class DatabaseAnalytics:
    """
    Advanced database analytics and performance analysis.
    
    Provides comprehensive analysis of database performance metrics,
    trend detection, optimization recommendations, and predictive analytics.
    """
    
    def __init__(self, config: MonitoringConfig, metrics_collector: MetricsCollector):
        self.config = config
        self.metrics_collector = metrics_collector
        
        # Analysis cache
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = timedelta(minutes=15)
        
        # Query patterns for optimization
        self._query_patterns = self._initialize_query_patterns()
        
        # Baseline metrics for trend analysis
        self._baselines: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Anomaly detection thresholds
        self._anomaly_thresholds: Dict[str, Dict[str, float]] = defaultdict(dict)
    
    def _initialize_query_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize query optimization patterns."""
        return {
            'missing_index': {
                'pattern': r'SELECT.*FROM\s+(\w+).*WHERE\s+(\w+)\s*=',
                'description': 'Query may benefit from an index',
                'suggestion': 'Consider adding an index on the WHERE clause columns',
                'confidence': 0.8
            },
            'select_star': {
                'pattern': r'SELECT\s+\*\s+FROM',
                'description': 'Using SELECT * can be inefficient',
                'suggestion': 'Select only the columns you need',
                'confidence': 0.9
            },
            'no_limit': {
                'pattern': r'SELECT.*FROM.*(?!.*LIMIT)',
                'description': 'Query without LIMIT may return too many rows',
                'suggestion': 'Consider adding LIMIT clause for large result sets',
                'confidence': 0.7
            },
            'cartesian_join': {
                'pattern': r'FROM\s+\w+\s*,\s*\w+(?!.*WHERE)',
                'description': 'Potential cartesian join detected',
                'suggestion': 'Add proper JOIN conditions',
                'confidence': 0.95
            },
            'function_in_where': {
                'pattern': r'WHERE\s+\w+\([^)]*\w+[^)]*\)',
                'description': 'Function in WHERE clause prevents index usage',
                'suggestion': 'Avoid functions in WHERE clause or use functional indexes',
                'confidence': 0.85
            }
        }
    
    async def analyze_performance_trends(
        self,
        database_name: str,
        period: timedelta = timedelta(hours=24)
    ) -> List[PerformanceTrend]:
        """
        Analyze performance trends over a time period.
        
        Args:
            database_name: Name of the database
            period: Time period to analyze
            
        Returns:
            List of performance trends
        """
        cache_key = f"trends_{database_name}_{period.total_seconds()}"
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return [PerformanceTrend(**trend) for trend in self._analysis_cache[cache_key]['data']]
        
        trends = []
        end_time = datetime.now(timezone.utc)
        start_time = end_time - period
        
        # Key metrics to analyze
        key_metrics = [
            'avg_query_duration',
            'p95_query_duration',
            'connection_pool_utilization',
            'error_rate',
            'slow_queries'
        ]
        
        for metric_name in key_metrics:
            try:
                trend = await self._analyze_metric_trend(
                    database_name, metric_name, start_time, end_time
                )
                if trend:
                    trends.append(trend)
            except Exception as e:
                # Continue with other metrics if one fails
                continue
        
        # Cache results
        self._cache_analysis(cache_key, [trend.to_dict() for trend in trends])
        
        return trends
    
    async def _analyze_metric_trend(
        self,
        database_name: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[PerformanceTrend]:
        """Analyze trend for a specific metric."""
        metrics = self.metrics_collector.get_metrics(
            database_name, metric_name, start_time, end_time
        )
        
        if len(metrics) < 10:  # Need sufficient data points
            return None
        
        values = [m.value for m in metrics]
        
        # Calculate baseline (first 25% of data)
        baseline_size = max(1, len(values) // 4)
        baseline_values = values[:baseline_size]
        current_values = values[-baseline_size:]
        
        baseline_avg = statistics.mean(baseline_values)
        current_avg = statistics.mean(current_values)
        
        # Calculate change percentage
        if baseline_avg != 0:
            change_percentage = ((current_avg - baseline_avg) / baseline_avg) * 100
        else:
            change_percentage = 0
        
        # Determine trend direction
        direction = self._determine_trend_direction(values, change_percentage)
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_trend_confidence(values)
        
        return PerformanceTrend(
            metric_name=metric_name,
            direction=direction,
            change_percentage=change_percentage,
            baseline_value=baseline_avg,
            current_value=current_avg,
            trend_confidence=confidence,
            period_analyzed=end_time - start_time
        )
    
    def _determine_trend_direction(self, values: List[float], change_percentage: float) -> TrendDirection:
        """Determine trend direction from values and change percentage."""
        # Calculate volatility
        if len(values) > 1:
            volatility = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) != 0 else 0
        else:
            volatility = 0
        
        # High volatility indicates unstable trend
        if volatility > 0.5:
            return TrendDirection.VOLATILE
        
        # Determine direction based on change
        if abs(change_percentage) < 5:  # Less than 5% change
            return TrendDirection.STABLE
        elif change_percentage > 0:
            return TrendDirection.DEGRADING  # Assuming higher values are worse for most metrics
        else:
            return TrendDirection.IMPROVING
    
    def _calculate_trend_confidence(self, values: List[float]) -> float:
        """Calculate confidence in trend analysis."""
        if len(values) < 5:
            return 0.3
        
        # More data points = higher confidence
        data_confidence = min(1.0, len(values) / 100)
        
        # Lower volatility = higher confidence
        if statistics.mean(values) != 0:
            volatility = statistics.stdev(values) / statistics.mean(values)
            volatility_confidence = max(0.1, 1.0 - volatility)
        else:
            volatility_confidence = 0.5
        
        return (data_confidence + volatility_confidence) / 2
    
    async def analyze_query_optimization(
        self,
        database_name: str,
        query_samples: List[str]
    ) -> List[QueryOptimizationSuggestion]:
        """
        Analyze queries for optimization opportunities.
        
        Args:
            database_name: Name of the database
            query_samples: Sample queries to analyze
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        for query in query_samples:
            query_suggestions = self._analyze_single_query(query)
            suggestions.extend(query_suggestions)
        
        # Group similar suggestions
        grouped_suggestions = self._group_optimization_suggestions(suggestions)
        
        return grouped_suggestions
    
    def _analyze_single_query(self, query: str) -> List[QueryOptimizationSuggestion]:
        """Analyze a single query for optimization opportunities."""
        suggestions = []
        query_upper = query.upper().strip()
        
        for pattern_name, pattern_info in self._query_patterns.items():
            if re.search(pattern_info['pattern'], query_upper, re.IGNORECASE):
                suggestion = QueryOptimizationSuggestion(
                    query_pattern=pattern_name,
                    issue_type=pattern_name,
                    description=pattern_info['description'],
                    suggestion=pattern_info['suggestion'],
                    estimated_improvement=self._estimate_improvement(pattern_name),
                    confidence=pattern_info['confidence'],
                    examples=[query[:100] + '...' if len(query) > 100 else query]
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def _estimate_improvement(self, pattern_name: str) -> float:
        """Estimate performance improvement percentage for optimization."""
        improvement_estimates = {
            'missing_index': 80.0,
            'select_star': 30.0,
            'no_limit': 50.0,
            'cartesian_join': 95.0,
            'function_in_where': 60.0
        }
        
        return improvement_estimates.get(pattern_name, 25.0)
    
    def _group_optimization_suggestions(
        self,
        suggestions: List[QueryOptimizationSuggestion]
    ) -> List[QueryOptimizationSuggestion]:
        """Group similar optimization suggestions."""
        grouped = defaultdict(list)
        
        for suggestion in suggestions:
            grouped[suggestion.issue_type].append(suggestion)
        
        result = []
        for issue_type, group in grouped.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Merge similar suggestions
                merged = QueryOptimizationSuggestion(
                    query_pattern=issue_type,
                    issue_type=issue_type,
                    description=group[0].description,
                    suggestion=group[0].suggestion,
                    estimated_improvement=statistics.mean([s.estimated_improvement for s in group]),
                    confidence=statistics.mean([s.confidence for s in group]),
                    examples=[s.examples[0] for s in group[:5]]  # Limit examples
                )
                result.append(merged)
        
        return result
    
    async def analyze_resource_utilization(
        self,
        database_name: str,
        period: timedelta = timedelta(hours=24)
    ) -> List[ResourceUtilizationAnalysis]:
        """
        Analyze resource utilization patterns.
        
        Args:
            database_name: Name of the database
            period: Time period to analyze
            
        Returns:
            List of resource utilization analyses
        """
        analyses = []
        
        # Resources to analyze
        resources = [
            'connection_pool_utilization',
            'cpu_utilization',
            'memory_utilization',
            'disk_utilization'
        ]
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - period
        
        for resource in resources:
            try:
                analysis = await self._analyze_resource_utilization(
                    database_name, resource, start_time, end_time
                )
                if analysis:
                    analyses.append(analysis)
            except Exception:
                continue
        
        return analyses
    
    async def _analyze_resource_utilization(
        self,
        database_name: str,
        resource_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> Optional[ResourceUtilizationAnalysis]:
        """Analyze utilization for a specific resource."""
        metrics = self.metrics_collector.get_metrics(
            database_name, resource_type, start_time, end_time
        )
        
        if not metrics:
            return None
        
        values = [m.value for m in metrics]
        
        current_utilization = values[-1] if values else 0
        peak_utilization = max(values)
        average_utilization = statistics.mean(values)
        
        # Determine trend
        trend = self._determine_trend_direction(values, 0)
        
        # Project exhaustion if trending upward
        projected_exhaustion = None
        if trend == TrendDirection.DEGRADING and len(values) > 10:
            projected_exhaustion = self._project_resource_exhaustion(
                values, [m.timestamp for m in metrics]
            )
        
        # Generate recommendations
        recommendations = self._generate_resource_recommendations(
            resource_type, current_utilization, peak_utilization, trend
        )
        
        return ResourceUtilizationAnalysis(
            resource_type=resource_type,
            current_utilization=current_utilization,
            peak_utilization=peak_utilization,
            average_utilization=average_utilization,
            trend=trend,
            projected_exhaustion=projected_exhaustion,
            recommendations=recommendations
        )
    
    def _project_resource_exhaustion(
        self,
        values: List[float],
        timestamps: List[datetime]
    ) -> Optional[datetime]:
        """Project when resource might be exhausted based on trend."""
        if len(values) < 10:
            return None
        
        try:
            # Simple linear regression to project trend
            x_values = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
            
            # Calculate slope
            n = len(values)
            sum_x = sum(x_values)
            sum_y = sum(values)
            sum_xy = sum(x * y for x, y in zip(x_values, values))
            sum_x2 = sum(x * x for x in x_values)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            if slope <= 0:  # Not increasing
                return None
            
            # Project when it reaches 100%
            current_value = values[-1]
            current_time = timestamps[-1]
            
            if current_value >= 1.0:  # Already at 100%
                return current_time
            
            seconds_to_exhaustion = (1.0 - current_value) / slope
            
            if seconds_to_exhaustion > 0:
                return current_time + timedelta(seconds=seconds_to_exhaustion)
        
        except (ZeroDivisionError, ValueError):
            pass
        
        return None
    
    def _generate_resource_recommendations(
        self,
        resource_type: str,
        current: float,
        peak: float,
        trend: TrendDirection
    ) -> List[str]:
        """Generate recommendations for resource utilization."""
        recommendations = []
        
        if resource_type == 'connection_pool_utilization':
            if current > 0.8:
                recommendations.append("Consider increasing connection pool size")
            if peak > 0.95:
                recommendations.append("Connection pool frequently at capacity - monitor for bottlenecks")
            if trend == TrendDirection.DEGRADING:
                recommendations.append("Connection usage is increasing - plan for capacity expansion")
        
        elif resource_type == 'cpu_utilization':
            if current > 0.8:
                recommendations.append("High CPU utilization - consider query optimization")
            if peak > 0.95:
                recommendations.append("CPU frequently at capacity - consider scaling up")
        
        elif resource_type == 'memory_utilization':
            if current > 0.9:
                recommendations.append("High memory utilization - monitor for memory leaks")
            if trend == TrendDirection.DEGRADING:
                recommendations.append("Memory usage increasing - consider adding more RAM")
        
        elif resource_type == 'disk_utilization':
            if current > 0.85:
                recommendations.append("Disk space running low - plan for expansion")
            if trend == TrendDirection.DEGRADING:
                recommendations.append("Disk usage increasing - implement data archival strategy")
        
        return recommendations
    
    async def detect_anomalies(
        self,
        database_name: str,
        period: timedelta = timedelta(hours=1)
    ) -> List[AnalyticsFinding]:
        """
        Detect performance anomalies.
        
        Args:
            database_name: Name of the database
            period: Time period to analyze
            
        Returns:
            List of anomaly findings
        """
        findings = []
        
        # Metrics to check for anomalies
        metrics_to_check = [
            'avg_query_duration',
            'error_rate',
            'connection_pool_utilization',
            'slow_queries'
        ]
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - period
        
        for metric_name in metrics_to_check:
            try:
                anomalies = await self._detect_metric_anomalies(
                    database_name, metric_name, start_time, end_time
                )
                findings.extend(anomalies)
            except Exception:
                continue
        
        return findings
    
    async def _detect_metric_anomalies(
        self,
        database_name: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[AnalyticsFinding]:
        """Detect anomalies for a specific metric."""
        findings = []
        
        # Get recent metrics
        metrics = self.metrics_collector.get_metrics(
            database_name, metric_name, start_time, end_time
        )
        
        if len(metrics) < 10:
            return findings
        
        values = [m.value for m in metrics]
        
        # Calculate statistical thresholds
        mean_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # Define anomaly thresholds (2 standard deviations)
        upper_threshold = mean_value + (2 * std_dev)
        lower_threshold = max(0, mean_value - (2 * std_dev))
        
        # Check for anomalies
        for i, metric in enumerate(metrics):
            if metric.value > upper_threshold:
                finding = AnalyticsFinding(
                    finding_id=f"anomaly_{database_name}_{metric_name}_{i}",
                    analysis_type=AnalysisType.ANOMALY_DETECTION,
                    severity=self._determine_anomaly_severity(metric.value, upper_threshold, mean_value),
                    title=f"High {metric_name} detected",
                    description=f"{metric_name} value {metric.value:.2f} is significantly above normal ({mean_value:.2f})",
                    recommendation=self._get_anomaly_recommendation(metric_name, "high"),
                    affected_metrics=[metric_name],
                    confidence=0.8,
                    metadata={
                        'value': metric.value,
                        'threshold': upper_threshold,
                        'baseline': mean_value,
                        'timestamp': metric.timestamp.isoformat()
                    }
                )
                findings.append(finding)
        
        return findings
    
    def _determine_anomaly_severity(self, value: float, threshold: float, baseline: float) -> Severity:
        """Determine severity of anomaly based on deviation."""
        if baseline == 0:
            return Severity.MEDIUM
        
        deviation_ratio = (value - threshold) / baseline
        
        if deviation_ratio > 2.0:
            return Severity.CRITICAL
        elif deviation_ratio > 1.0:
            return Severity.HIGH
        elif deviation_ratio > 0.5:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    def _get_anomaly_recommendation(self, metric_name: str, anomaly_type: str) -> str:
        """Get recommendation for specific anomaly."""
        recommendations = {
            'avg_query_duration': {
                'high': 'Investigate slow queries and consider query optimization or indexing'
            },
            'error_rate': {
                'high': 'Check application logs and database connectivity issues'
            },
            'connection_pool_utilization': {
                'high': 'Monitor for connection leaks and consider increasing pool size'
            },
            'slow_queries': {
                'high': 'Analyze slow query log and optimize problematic queries'
            }
        }
        
        return recommendations.get(metric_name, {}).get(anomaly_type, 'Monitor the situation and investigate if it persists')
    
    async def generate_health_assessment(self, database_name: str) -> Dict[str, Any]:
        """
        Generate comprehensive health assessment.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Health assessment report
        """
        assessment = {
            'database_name': database_name,
            'assessment_time': datetime.now(timezone.utc).isoformat(),
            'overall_health': 'unknown',
            'health_score': 0.0,
            'findings': [],
            'recommendations': [],
            'trends': [],
            'resource_analysis': [],
            'anomalies': []
        }
        
        try:
            # Analyze trends
            trends = await self.analyze_performance_trends(database_name)
            assessment['trends'] = [trend.to_dict() for trend in trends]
            
            # Analyze resource utilization
            resource_analysis = await self.analyze_resource_utilization(database_name)
            assessment['resource_analysis'] = [analysis.to_dict() for analysis in resource_analysis]
            
            # Detect anomalies
            anomalies = await self.detect_anomalies(database_name)
            assessment['anomalies'] = [anomaly.to_dict() for anomaly in anomalies]
            
            # Calculate health score
            health_score = self._calculate_health_score(trends, resource_analysis, anomalies)
            assessment['health_score'] = health_score
            
            # Determine overall health
            assessment['overall_health'] = self._determine_overall_health(health_score)
            
            # Generate recommendations
            recommendations = self._generate_health_recommendations(trends, resource_analysis, anomalies)
            assessment['recommendations'] = recommendations
            
        except Exception as e:
            assessment['error'] = str(e)
        
        return assessment
    
    def _calculate_health_score(
        self,
        trends: List[PerformanceTrend],
        resource_analysis: List[ResourceUtilizationAnalysis],
        anomalies: List[AnalyticsFinding]
    ) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # Deduct points for negative trends
        for trend in trends:
            if trend.direction == TrendDirection.DEGRADING:
                score -= min(20, abs(trend.change_percentage) / 2)
            elif trend.direction == TrendDirection.VOLATILE:
                score -= 10
        
        # Deduct points for high resource utilization
        for analysis in resource_analysis:
            if analysis.current_utilization > 0.9:
                score -= 15
            elif analysis.current_utilization > 0.8:
                score -= 10
            elif analysis.current_utilization > 0.7:
                score -= 5
        
        # Deduct points for anomalies
        for anomaly in anomalies:
            if anomaly.severity == Severity.CRITICAL:
                score -= 25
            elif anomaly.severity == Severity.HIGH:
                score -= 15
            elif anomaly.severity == Severity.MEDIUM:
                score -= 10
            elif anomaly.severity == Severity.LOW:
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _determine_overall_health(self, health_score: float) -> str:
        """Determine overall health status from score."""
        if health_score >= 90:
            return 'excellent'
        elif health_score >= 75:
            return 'good'
        elif health_score >= 60:
            return 'fair'
        elif health_score >= 40:
            return 'poor'
        else:
            return 'critical'
    
    def _generate_health_recommendations(
        self,
        trends: List[PerformanceTrend],
        resource_analysis: List[ResourceUtilizationAnalysis],
        anomalies: List[AnalyticsFinding]
    ) -> List[str]:
        """Generate health-based recommendations."""
        recommendations = []
        
        # Trend-based recommendations
        degrading_trends = [t for t in trends if t.direction == TrendDirection.DEGRADING]
        if degrading_trends:
            recommendations.append(f"Monitor {len(degrading_trends)} degrading performance metrics")
        
        # Resource-based recommendations
        high_utilization = [r for r in resource_analysis if r.current_utilization > 0.8]
        if high_utilization:
            recommendations.append(f"Address high utilization in {len(high_utilization)} resources")
        
        # Anomaly-based recommendations
        critical_anomalies = [a for a in anomalies if a.severity == Severity.CRITICAL]
        if critical_anomalies:
            recommendations.append(f"Immediately investigate {len(critical_anomalies)} critical anomalies")
        
        return recommendations
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached analysis is still valid."""
        if cache_key not in self._analysis_cache:
            return False
        
        cache_time = self._analysis_cache[cache_key]['timestamp']
        return datetime.now(timezone.utc) - cache_time < self._cache_ttl
    
    def _cache_analysis(self, cache_key: str, data: Any) -> None:
        """Cache analysis results."""
        self._analysis_cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now(timezone.utc)
        }
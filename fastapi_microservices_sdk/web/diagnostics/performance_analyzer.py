"""
Performance Analyzer - Advanced system performance analysis and optimization recommendations
"""
import time
import asyncio
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str
    tags: Optional[Dict[str, str]] = None

@dataclass
class PerformanceBenchmark:
    name: str
    duration_ms: float
    operations_count: int
    ops_per_second: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class OptimizationRecommendation:
    category: str
    priority: str  # high, medium, low
    title: str
    description: str
    impact: str
    implementation_effort: str
    estimated_improvement: str
    timestamp: datetime

class PerformanceAnalyzer:
    """
    Advanced performance analysis and optimization recommendations.
    
    Features:
    - Performance metric collection and analysis
    - Bottleneck identification
    - Optimization recommendations
    - Performance benchmarking
    - Trend analysis and forecasting
    """
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.benchmarks: deque = deque(maxlen=1000)
        self.recommendations: List[OptimizationRecommendation] = []
        
        # Performance thresholds
        self.thresholds = {
            "response_time_ms": 1000,
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_io_wait": 10,
            "network_latency_ms": 100
        }
        
        # Analysis state
        self.last_analysis = None
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    def record_metric(
        self, 
        name: str, 
        value: float, 
        unit: str = "", 
        category: str = "general",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                category=category,
                tags=tags or {}
            )
            
            self.metrics.append(metric)
            
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
    
    def record_benchmark(
        self, 
        name: str, 
        duration_ms: float, 
        operations_count: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance benchmark"""
        try:
            ops_per_second = operations_count / (duration_ms / 1000) if duration_ms > 0 else 0
            
            benchmark = PerformanceBenchmark(
                name=name,
                duration_ms=duration_ms,
                operations_count=operations_count,
                ops_per_second=ops_per_second,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            self.benchmarks.append(benchmark)
            
        except Exception as e:
            logger.error(f"Failed to record benchmark {name}: {e}")
    
    async def benchmark_function(
        self, 
        func: Callable, 
        name: str, 
        iterations: int = 1,
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """Benchmark a function's performance"""
        try:
            durations = []
            
            for i in range(iterations):
                start_time = time.perf_counter()
                
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                durations.append(duration_ms)
            
            # Calculate statistics
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            std_dev = statistics.stdev(durations) if len(durations) > 1 else 0
            
            # Record benchmark
            self.record_benchmark(
                name=name,
                duration_ms=avg_duration,
                operations_count=iterations,
                metadata={
                    "min_duration_ms": min_duration,
                    "max_duration_ms": max_duration,
                    "std_dev_ms": std_dev,
                    "iterations": iterations
                }
            )
            
            return {
                "name": name,
                "iterations": iterations,
                "avg_duration_ms": avg_duration,
                "min_duration_ms": min_duration,
                "max_duration_ms": max_duration,
                "std_dev_ms": std_dev,
                "ops_per_second": iterations / (avg_duration / 1000),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to benchmark function {name}: {e}")
            return {"error": str(e)}
    
    def get_metrics_by_category(self, category: str, hours: int = 1) -> List[PerformanceMetric]:
        """Get metrics by category within time range"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            return [
                metric for metric in self.metrics
                if metric.category == category and metric.timestamp > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Failed to get metrics by category {category}: {e}")
            return []
    
    def get_metric_statistics(self, metric_name: str, hours: int = 1) -> Dict[str, Any]:
        """Get statistical analysis of a specific metric"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            values = [
                metric.value for metric in self.metrics
                if metric.name == metric_name and metric.timestamp > cutoff_time
            ]
            
            if not values:
                return {"error": f"No data found for metric {metric_name}"}
            
            return {
                "metric_name": metric_name,
                "count": len(values),
                "average": statistics.mean(values),
                "median": statistics.median(values),
                "minimum": min(values),
                "maximum": max(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "percentile_95": self._calculate_percentile(values, 95),
                "percentile_99": self._calculate_percentile(values, 99),
                "period_hours": hours,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get metric statistics for {metric_name}: {e}")
            return {"error": str(e)}
    
    def analyze_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        cache_key = f"trends_{hours}"
        
        # Check cache
        if (cache_key in self.analysis_cache and 
            time.time() - self.analysis_cache[cache_key]["timestamp"] < self.cache_ttl):
            return self.analysis_cache[cache_key]["data"]
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
            
            if not recent_metrics:
                return {"error": "No metrics available for trend analysis"}
            
            # Group metrics by name
            metric_groups = defaultdict(list)
            for metric in recent_metrics:
                metric_groups[metric.name].append(metric.value)
            
            trends = {}
            for metric_name, values in metric_groups.items():
                if len(values) >= 3:  # Need at least 3 points for trend
                    trend = self._calculate_trend(values)
                    trends[metric_name] = {
                        "trend": trend,
                        "current_value": values[-1],
                        "change_percent": self._calculate_change_percent(values),
                        "volatility": statistics.stdev(values) if len(values) > 1 else 0
                    }
            
            result = {
                "period_hours": hours,
                "metrics_analyzed": len(trends),
                "trends": trends,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            self.analysis_cache[cache_key] = {
                "data": result,
                "timestamp": time.time()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze performance trends: {e}")
            return {"error": str(e)}
    
    def identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        try:
            bottlenecks = []
            
            # Analyze recent metrics
            recent_metrics = [
                m for m in self.metrics 
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            # Group by category and analyze
            category_metrics = defaultdict(list)
            for metric in recent_metrics:
                category_metrics[metric.category].append(metric)
            
            for category, metrics in category_metrics.items():
                # Check for high values
                for metric in metrics:
                    threshold_key = f"{metric.name}_{metric.unit}".lower()
                    if threshold_key in self.thresholds:
                        if metric.value > self.thresholds[threshold_key]:
                            bottlenecks.append({
                                "type": "threshold_exceeded",
                                "category": category,
                                "metric": metric.name,
                                "current_value": metric.value,
                                "threshold": self.thresholds[threshold_key],
                                "severity": "high" if metric.value > self.thresholds[threshold_key] * 1.2 else "medium",
                                "timestamp": metric.timestamp.isoformat()
                            })
                
                # Check for high variability
                if len(metrics) > 5:
                    values = [m.value for m in metrics]
                    std_dev = statistics.stdev(values)
                    mean_val = statistics.mean(values)
                    
                    if std_dev > mean_val * 0.5:  # High variability
                        bottlenecks.append({
                            "type": "high_variability",
                            "category": category,
                            "metric": metrics[0].name,
                            "variability_ratio": std_dev / mean_val,
                            "severity": "medium",
                            "timestamp": datetime.now().isoformat()
                        })
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Failed to identify bottlenecks: {e}")
            return []
    
    def generate_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on analysis"""
        try:
            recommendations = []
            
            # Analyze bottlenecks
            bottlenecks = self.identify_bottlenecks()
            
            for bottleneck in bottlenecks:
                if bottleneck["type"] == "threshold_exceeded":
                    if "cpu" in bottleneck["metric"].lower():
                        recommendations.append(OptimizationRecommendation(
                            category="cpu",
                            priority="high",
                            title="High CPU Usage Detected",
                            description=f"CPU usage is {bottleneck['current_value']:.1f}%, exceeding threshold of {bottleneck['threshold']}%",
                            impact="Performance degradation, slower response times",
                            implementation_effort="Medium",
                            estimated_improvement="20-40% performance improvement",
                            timestamp=datetime.now()
                        ))
                    
                    elif "memory" in bottleneck["metric"].lower():
                        recommendations.append(OptimizationRecommendation(
                            category="memory",
                            priority="high",
                            title="High Memory Usage Detected",
                            description=f"Memory usage is {bottleneck['current_value']:.1f}%, exceeding threshold of {bottleneck['threshold']}%",
                            impact="Risk of out-of-memory errors, system instability",
                            implementation_effort="Medium",
                            estimated_improvement="Prevent system crashes, improve stability",
                            timestamp=datetime.now()
                        ))
                
                elif bottleneck["type"] == "high_variability":
                    recommendations.append(OptimizationRecommendation(
                        category="stability",
                        priority="medium",
                        title="Performance Variability Detected",
                        description=f"High variability in {bottleneck['metric']} performance",
                        impact="Inconsistent user experience, unpredictable performance",
                        implementation_effort="Low",
                        estimated_improvement="More consistent performance",
                        timestamp=datetime.now()
                    ))
            
            # Analyze benchmarks for slow operations
            recent_benchmarks = [
                b for b in self.benchmarks 
                if b.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            for benchmark in recent_benchmarks:
                if benchmark.duration_ms > 1000:  # Slow operation
                    recommendations.append(OptimizationRecommendation(
                        category="performance",
                        priority="medium",
                        title=f"Slow Operation: {benchmark.name}",
                        description=f"Operation takes {benchmark.duration_ms:.1f}ms on average",
                        impact="Slower response times, poor user experience",
                        implementation_effort="High",
                        estimated_improvement="50-80% faster execution",
                        timestamp=datetime.now()
                    ))
            
            # Store recommendations
            self.recommendations.extend(recommendations)
            
            # Keep only recent recommendations
            cutoff_time = datetime.now() - timedelta(days=7)
            self.recommendations = [
                r for r in self.recommendations 
                if r.timestamp > cutoff_time
            ]
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            return []
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            # Get recent data
            recent_metrics = [
                m for m in self.metrics 
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            recent_benchmarks = [
                b for b in self.benchmarks 
                if b.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            # Analyze trends
            trends = self.analyze_performance_trends(hours=24)
            
            # Identify bottlenecks
            bottlenecks = self.identify_bottlenecks()
            
            # Generate recommendations
            recommendations = self.generate_optimization_recommendations()
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(bottlenecks, recent_metrics)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "performance_score": performance_score,
                "summary": {
                    "total_metrics": len(self.metrics),
                    "recent_metrics": len(recent_metrics),
                    "total_benchmarks": len(self.benchmarks),
                    "recent_benchmarks": len(recent_benchmarks),
                    "active_bottlenecks": len(bottlenecks),
                    "recommendations_count": len(recommendations)
                },
                "trends": trends,
                "bottlenecks": bottlenecks,
                "recommendations": [asdict(r) for r in recommendations],
                "top_slow_operations": self._get_slowest_operations(5),
                "performance_categories": self._analyze_performance_by_category()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 3:
            return "stable"
        
        # Simple trend calculation using first and last third
        first_third = values[:len(values)//3]
        last_third = values[-len(values)//3:]
        
        first_avg = statistics.mean(first_third)
        last_avg = statistics.mean(last_third)
        
        change_percent = ((last_avg - first_avg) / first_avg) * 100 if first_avg != 0 else 0
        
        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_change_percent(self, values: List[float]) -> float:
        """Calculate percentage change from first to last value"""
        if len(values) < 2 or values[0] == 0:
            return 0.0
        
        return ((values[-1] - values[0]) / values[0]) * 100
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _calculate_performance_score(self, bottlenecks: List[Dict], metrics: List[PerformanceMetric]) -> int:
        """Calculate overall performance score (0-100)"""
        base_score = 100
        
        # Deduct points for bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.get("severity") == "high":
                base_score -= 20
            elif bottleneck.get("severity") == "medium":
                base_score -= 10
            else:
                base_score -= 5
        
        # Deduct points for high metric values
        for metric in metrics:
            threshold_key = f"{metric.name}_{metric.unit}".lower()
            if threshold_key in self.thresholds:
                if metric.value > self.thresholds[threshold_key]:
                    base_score -= 5
        
        return max(0, base_score)
    
    def _get_slowest_operations(self, limit: int) -> List[Dict[str, Any]]:
        """Get slowest operations from benchmarks"""
        try:
            recent_benchmarks = [
                b for b in self.benchmarks 
                if b.timestamp > datetime.now() - timedelta(hours=24)
            ]
            
            # Sort by duration
            sorted_benchmarks = sorted(recent_benchmarks, key=lambda b: b.duration_ms, reverse=True)
            
            return [
                {
                    "name": b.name,
                    "duration_ms": b.duration_ms,
                    "ops_per_second": b.ops_per_second,
                    "timestamp": b.timestamp.isoformat()
                }
                for b in sorted_benchmarks[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Failed to get slowest operations: {e}")
            return []
    
    def _analyze_performance_by_category(self) -> Dict[str, Any]:
        """Analyze performance metrics by category"""
        try:
            recent_metrics = [
                m for m in self.metrics 
                if m.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            categories = defaultdict(list)
            for metric in recent_metrics:
                categories[metric.category].append(metric.value)
            
            category_analysis = {}
            for category, values in categories.items():
                if values:
                    category_analysis[category] = {
                        "count": len(values),
                        "average": statistics.mean(values),
                        "maximum": max(values),
                        "minimum": min(values),
                        "std_dev": statistics.stdev(values) if len(values) > 1 else 0
                    }
            
            return category_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze performance by category: {e}")
            return {}
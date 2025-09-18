"""
Performance Analysis and Bottleneck Detection for Distributed Tracing.

This module provides advanced performance analysis capabilities including
bottleneck detection, latency analysis, dependency mapping, and intelligent
performance recommendations based on trace data.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import time
import statistics
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from enum import Enum

from .tracer import Span, SpanStatus
from .exceptions import TracingError


class BottleneckType(Enum):
    """Types of performance bottlenecks."""
    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    RESOURCE_CONTENTION = "resource_contention"
    DEPENDENCY_SLOWDOWN = "dependency_slowdown"
    MEMORY_LEAK = "memory_leak"
    CPU_INTENSIVE = "cpu_intensive"
    IO_BOUND = "io_bound"
    NETWORK_LATENCY = "network_latency"


class SeverityLevel(Enum):
    """Severity levels for performance issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Performance metric data point."""
    timestamp: datetime
    value: float
    operation: str
    service: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BottleneckDetection:
    """Bottleneck detection result."""
    bottleneck_type: BottleneckType
    severity: SeverityLevel
    operation: str
    service: str
    description: str
    metrics: Dict[str, float]
    recommendations: List[str]
    affected_traces: List[str]
    detection_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LatencyAnalysis:
    """Latency analysis result."""
    operation: str
    service: str
    sample_count: int
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    std_deviation: float
    trend: str  # "increasing", "decreasing", "stable"
    analysis_period: timedelta


@dataclass
class DependencyMapping:
    """Service dependency mapping."""
    service: str
    dependencies: Dict[str, float]  # service -> call_frequency
    dependents: Dict[str, float]   # service -> call_frequency
    critical_path: List[str]
    total_calls: int
    error_rate: float


class PerformanceAnalyzer:
    """Advanced performance analyzer for distributed traces."""
    
    def __init__(
        self,
        analysis_window: timedelta = timedelta(minutes=15),
        bottleneck_threshold_ms: float = 1000.0,
        error_rate_threshold: float = 0.05,
        sample_size_threshold: int = 10
    ):
        self.analysis_window = analysis_window
        self.bottleneck_threshold_ms = bottleneck_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.sample_size_threshold = sample_size_threshold
        
        # Data storage
        self._span_data: deque = deque(maxlen=10000)
        self._performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._service_operations: Dict[str, Set[str]] = defaultdict(set)
        
        # Analysis results cache
        self._bottleneck_cache: Dict[str, BottleneckDetection] = {}
        self._latency_cache: Dict[str, LatencyAnalysis] = {}
        self._dependency_cache: Dict[str, DependencyMapping] = {}
        
        self._logger = logging.getLogger(__name__)
    
    def record_span(self, span: Span) -> None:
        """Record span data for analysis."""
        try:
            span_data = span.get_span_data()
            
            # Add timestamp if not present
            if 'timestamp' not in span_data:
                span_data['timestamp'] = datetime.now(timezone.utc)
            
            self._span_data.append(span_data)
            
            # Extract service and operation info
            service_name = span_data.get('attributes', {}).get('service.name', 'unknown')
            operation_name = span_data.get('operation_name', 'unknown')
            
            self._service_operations[service_name].add(operation_name)
            
            # Record performance metric
            if 'duration_ms' in span_data:
                metric = PerformanceMetric(
                    timestamp=span_data['timestamp'],
                    value=span_data['duration_ms'],
                    operation=operation_name,
                    service=service_name,
                    metadata=span_data.get('attributes', {})
                )
                
                metric_key = f"{service_name}.{operation_name}"
                self._performance_metrics[metric_key].append(metric)
            
            # Update dependency graph
            self._update_dependency_graph(span_data)
            
        except Exception as e:
            self._logger.error(f"Failed to record span data: {e}")
    
    def analyze_bottlenecks(self) -> List[BottleneckDetection]:
        """Analyze traces for performance bottlenecks."""
        bottlenecks = []
        
        try:
            # Analyze each service-operation combination
            for metric_key, metrics in self._performance_metrics.items():
                if len(metrics) < self.sample_size_threshold:
                    continue
                
                service, operation = metric_key.split('.', 1)
                
                # Get recent metrics within analysis window
                cutoff_time = datetime.now(timezone.utc) - self.analysis_window
                recent_metrics = [
                    m for m in metrics 
                    if m.timestamp >= cutoff_time
                ]
                
                if len(recent_metrics) < self.sample_size_threshold:
                    continue
                
                # Analyze for different bottleneck types
                bottlenecks.extend(self._detect_latency_bottlenecks(service, operation, recent_metrics))
                bottlenecks.extend(self._detect_error_rate_bottlenecks(service, operation, recent_metrics))
                bottlenecks.extend(self._detect_resource_bottlenecks(service, operation, recent_metrics))
            
            # Cache results
            for bottleneck in bottlenecks:
                cache_key = f"{bottleneck.service}.{bottleneck.operation}.{bottleneck.bottleneck_type.value}"
                self._bottleneck_cache[cache_key] = bottleneck
            
            return bottlenecks
            
        except Exception as e:
            self._logger.error(f"Failed to analyze bottlenecks: {e}")
            return []
    
    def analyze_latency(self, service: str, operation: str) -> Optional[LatencyAnalysis]:
        """Analyze latency patterns for a specific operation."""
        try:
            metric_key = f"{service}.{operation}"
            metrics = self._performance_metrics.get(metric_key, [])
            
            if len(metrics) < self.sample_size_threshold:
                return None
            
            # Get recent metrics
            cutoff_time = datetime.now(timezone.utc) - self.analysis_window
            recent_metrics = [
                m.value for m in metrics 
                if m.timestamp >= cutoff_time
            ]
            
            if len(recent_metrics) < self.sample_size_threshold:
                return None
            
            # Calculate statistics
            mean_latency = statistics.mean(recent_metrics)
            median_latency = statistics.median(recent_metrics)
            std_dev = statistics.stdev(recent_metrics) if len(recent_metrics) > 1 else 0
            
            # Calculate percentiles
            sorted_metrics = sorted(recent_metrics)
            p95_index = int(0.95 * len(sorted_metrics))
            p99_index = int(0.99 * len(sorted_metrics))
            
            p95_latency = sorted_metrics[p95_index] if p95_index < len(sorted_metrics) else sorted_metrics[-1]
            p99_latency = sorted_metrics[p99_index] if p99_index < len(sorted_metrics) else sorted_metrics[-1]
            
            # Determine trend
            trend = self._calculate_latency_trend(metrics)
            
            analysis = LatencyAnalysis(
                operation=operation,
                service=service,
                sample_count=len(recent_metrics),
                mean_latency_ms=mean_latency,
                median_latency_ms=median_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                max_latency_ms=max(recent_metrics),
                min_latency_ms=min(recent_metrics),
                std_deviation=std_dev,
                trend=trend,
                analysis_period=self.analysis_window
            )
            
            # Cache result
            cache_key = f"{service}.{operation}"
            self._latency_cache[cache_key] = analysis
            
            return analysis
            
        except Exception as e:
            self._logger.error(f"Failed to analyze latency for {service}.{operation}: {e}")
            return None
    
    def map_dependencies(self) -> Dict[str, DependencyMapping]:
        """Map service dependencies based on trace data."""
        try:
            dependency_mappings = {}
            
            # Analyze dependency relationships
            for service in self._service_operations.keys():
                dependencies = {}
                dependents = {}
                total_calls = 0
                error_count = 0
                
                # Count calls to dependencies
                for dependency in self._dependency_graph.get(service, set()):
                    call_count = self._count_service_calls(service, dependency)
                    if call_count > 0:
                        dependencies[dependency] = call_count
                        total_calls += call_count
                
                # Count calls from dependents
                for dependent_service, deps in self._dependency_graph.items():
                    if service in deps:
                        call_count = self._count_service_calls(dependent_service, service)
                        if call_count > 0:
                            dependents[dependent_service] = call_count
                
                # Calculate error rate
                error_rate = self._calculate_service_error_rate(service)
                
                # Determine critical path
                critical_path = self._find_critical_path(service)
                
                mapping = DependencyMapping(
                    service=service,
                    dependencies=dependencies,
                    dependents=dependents,
                    critical_path=critical_path,
                    total_calls=total_calls,
                    error_rate=error_rate
                )
                
                dependency_mappings[service] = mapping
                self._dependency_cache[service] = mapping
            
            return dependency_mappings
            
        except Exception as e:
            self._logger.error(f"Failed to map dependencies: {e}")
            return {}
    
    def get_performance_recommendations(self, service: str, operation: str) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        try:
            # Get latency analysis
            latency_analysis = self.analyze_latency(service, operation)
            if latency_analysis:
                if latency_analysis.p95_latency_ms > self.bottleneck_threshold_ms:
                    recommendations.append(
                        f"High P95 latency ({latency_analysis.p95_latency_ms:.1f}ms). "
                        "Consider optimizing database queries or adding caching."
                    )
                
                if latency_analysis.std_deviation > latency_analysis.mean_latency_ms * 0.5:
                    recommendations.append(
                        "High latency variance detected. "
                        "Consider implementing connection pooling or load balancing."
                    )
                
                if latency_analysis.trend == "increasing":
                    recommendations.append(
                        "Latency trend is increasing. "
                        "Monitor for resource leaks or scaling issues."
                    )
            
            # Check for bottlenecks
            bottlenecks = [
                b for b in self._bottleneck_cache.values()
                if b.service == service and b.operation == operation
            ]
            
            for bottleneck in bottlenecks:
                recommendations.extend(bottleneck.recommendations)
            
            # Check dependencies
            dependency_mapping = self._dependency_cache.get(service)
            if dependency_mapping and dependency_mapping.error_rate > self.error_rate_threshold:
                recommendations.append(
                    f"High error rate ({dependency_mapping.error_rate:.2%}). "
                    "Implement circuit breakers and retry mechanisms."
                )
            
            return list(set(recommendations))  # Remove duplicates
            
        except Exception as e:
            self._logger.error(f"Failed to get recommendations for {service}.{operation}: {e}")
            return []
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary."""
        try:
            # Get all bottlenecks
            bottlenecks = self.analyze_bottlenecks()
            
            # Count by severity
            severity_counts = defaultdict(int)
            for bottleneck in bottlenecks:
                severity_counts[bottleneck.severity.value] += 1
            
            # Get service statistics
            service_stats = {}
            for service in self._service_operations.keys():
                error_rate = self._calculate_service_error_rate(service)
                avg_latency = self._calculate_service_avg_latency(service)
                
                service_stats[service] = {
                    'error_rate': error_rate,
                    'avg_latency_ms': avg_latency,
                    'operations_count': len(self._service_operations[service])
                }
            
            return {
                'analysis_window_minutes': self.analysis_window.total_seconds() / 60,
                'total_spans_analyzed': len(self._span_data),
                'bottlenecks_detected': len(bottlenecks),
                'bottlenecks_by_severity': dict(severity_counts),
                'services_analyzed': len(self._service_operations),
                'service_statistics': service_stats,
                'dependency_graph_size': sum(len(deps) for deps in self._dependency_graph.values()),
                'analysis_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self._logger.error(f"Failed to get analysis summary: {e}")
            return {}
    
    # Private helper methods
    
    def _detect_latency_bottlenecks(
        self, 
        service: str, 
        operation: str, 
        metrics: List[PerformanceMetric]
    ) -> List[BottleneckDetection]:
        """Detect latency-based bottlenecks."""
        bottlenecks = []
        
        try:
            latencies = [m.value for m in metrics]
            avg_latency = statistics.mean(latencies)
            p95_latency = sorted(latencies)[int(0.95 * len(latencies))]
            
            if p95_latency > self.bottleneck_threshold_ms:
                severity = SeverityLevel.HIGH if p95_latency > self.bottleneck_threshold_ms * 2 else SeverityLevel.MEDIUM
                
                bottleneck = BottleneckDetection(
                    bottleneck_type=BottleneckType.HIGH_LATENCY,
                    severity=severity,
                    operation=operation,
                    service=service,
                    description=f"High P95 latency detected: {p95_latency:.1f}ms",
                    metrics={
                        'avg_latency_ms': avg_latency,
                        'p95_latency_ms': p95_latency,
                        'threshold_ms': self.bottleneck_threshold_ms
                    },
                    recommendations=[
                        "Optimize database queries and add appropriate indexes",
                        "Implement caching for frequently accessed data",
                        "Consider connection pooling for external services",
                        "Review and optimize algorithm complexity"
                    ],
                    affected_traces=[m.metadata.get('trace_id', 'unknown') for m in metrics[-10:]]
                )
                
                bottlenecks.append(bottleneck)
        
        except Exception as e:
            self._logger.error(f"Failed to detect latency bottlenecks: {e}")
        
        return bottlenecks
    
    def _detect_error_rate_bottlenecks(
        self, 
        service: str, 
        operation: str, 
        metrics: List[PerformanceMetric]
    ) -> List[BottleneckDetection]:
        """Detect error rate bottlenecks."""
        bottlenecks = []
        
        try:
            error_count = sum(1 for m in metrics if m.metadata.get('status') == 'error')
            error_rate = error_count / len(metrics) if metrics else 0
            
            if error_rate > self.error_rate_threshold:
                severity = SeverityLevel.CRITICAL if error_rate > 0.2 else SeverityLevel.HIGH
                
                bottleneck = BottleneckDetection(
                    bottleneck_type=BottleneckType.HIGH_ERROR_RATE,
                    severity=severity,
                    operation=operation,
                    service=service,
                    description=f"High error rate detected: {error_rate:.2%}",
                    metrics={
                        'error_rate': error_rate,
                        'error_count': error_count,
                        'total_requests': len(metrics),
                        'threshold': self.error_rate_threshold
                    },
                    recommendations=[
                        "Implement circuit breaker pattern for external dependencies",
                        "Add comprehensive error handling and retry logic",
                        "Monitor and fix underlying service issues",
                        "Implement graceful degradation strategies"
                    ],
                    affected_traces=[m.metadata.get('trace_id', 'unknown') for m in metrics if m.metadata.get('status') == 'error']
                )
                
                bottlenecks.append(bottleneck)
        
        except Exception as e:
            self._logger.error(f"Failed to detect error rate bottlenecks: {e}")
        
        return bottlenecks
    
    def _detect_resource_bottlenecks(
        self, 
        service: str, 
        operation: str, 
        metrics: List[PerformanceMetric]
    ) -> List[BottleneckDetection]:
        """Detect resource contention bottlenecks."""
        bottlenecks = []
        
        try:
            # Analyze latency variance as indicator of resource contention
            latencies = [m.value for m in metrics]
            if len(latencies) > 1:
                std_dev = statistics.stdev(latencies)
                mean_latency = statistics.mean(latencies)
                coefficient_of_variation = std_dev / mean_latency if mean_latency > 0 else 0
                
                # High variance indicates resource contention
                if coefficient_of_variation > 1.0:  # CV > 1 indicates high variance
                    bottleneck = BottleneckDetection(
                        bottleneck_type=BottleneckType.RESOURCE_CONTENTION,
                        severity=SeverityLevel.MEDIUM,
                        operation=operation,
                        service=service,
                        description=f"High latency variance detected (CV: {coefficient_of_variation:.2f})",
                        metrics={
                            'coefficient_of_variation': coefficient_of_variation,
                            'std_deviation': std_dev,
                            'mean_latency': mean_latency
                        },
                        recommendations=[
                            "Implement connection pooling to reduce resource contention",
                            "Add load balancing to distribute requests evenly",
                            "Monitor CPU and memory usage for resource constraints",
                            "Consider horizontal scaling if resource limits are reached"
                        ],
                        affected_traces=[m.metadata.get('trace_id', 'unknown') for m in metrics[-5:]]
                    )
                    
                    bottlenecks.append(bottleneck)
        
        except Exception as e:
            self._logger.error(f"Failed to detect resource bottlenecks: {e}")
        
        return bottlenecks
    
    def _update_dependency_graph(self, span_data: Dict[str, Any]) -> None:
        """Update service dependency graph from span data."""
        try:
            service_name = span_data.get('attributes', {}).get('service.name', 'unknown')
            
            # Look for dependency indicators in attributes
            attributes = span_data.get('attributes', {})
            
            # Database dependencies
            if 'db.system' in attributes:
                db_system = attributes['db.system']
                self._dependency_graph[service_name].add(f"database.{db_system}")
            
            # HTTP client dependencies
            if 'http.url' in attributes:
                url = attributes['http.url']
                # Extract host from URL
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    if parsed.hostname:
                        self._dependency_graph[service_name].add(f"http.{parsed.hostname}")
                except Exception:
                    pass
            
            # Message broker dependencies
            if 'messaging.system' in attributes:
                messaging_system = attributes['messaging.system']
                self._dependency_graph[service_name].add(f"messaging.{messaging_system}")
        
        except Exception as e:
            self._logger.error(f"Failed to update dependency graph: {e}")
    
    def _calculate_latency_trend(self, metrics: List[PerformanceMetric]) -> str:
        """Calculate latency trend over time."""
        try:
            if len(metrics) < 10:
                return "stable"
            
            # Sort by timestamp
            sorted_metrics = sorted(metrics, key=lambda m: m.timestamp)
            
            # Split into two halves and compare averages
            mid_point = len(sorted_metrics) // 2
            first_half_avg = statistics.mean([m.value for m in sorted_metrics[:mid_point]])
            second_half_avg = statistics.mean([m.value for m in sorted_metrics[mid_point:]])
            
            # Calculate percentage change
            if first_half_avg > 0:
                change_percent = (second_half_avg - first_half_avg) / first_half_avg
                
                if change_percent > 0.1:  # 10% increase
                    return "increasing"
                elif change_percent < -0.1:  # 10% decrease
                    return "decreasing"
            
            return "stable"
        
        except Exception:
            return "stable"
    
    def _count_service_calls(self, from_service: str, to_service: str) -> int:
        """Count calls between services."""
        # This would be implemented based on actual span data analysis
        # For now, return a placeholder
        return 0
    
    def _calculate_service_error_rate(self, service: str) -> float:
        """Calculate error rate for a service."""
        try:
            service_spans = [
                span for span in self._span_data
                if span.get('attributes', {}).get('service.name') == service
            ]
            
            if not service_spans:
                return 0.0
            
            error_count = sum(
                1 for span in service_spans
                if span.get('status') == 'error'
            )
            
            return error_count / len(service_spans)
        
        except Exception:
            return 0.0
    
    def _calculate_service_avg_latency(self, service: str) -> float:
        """Calculate average latency for a service."""
        try:
            service_spans = [
                span for span in self._span_data
                if span.get('attributes', {}).get('service.name') == service
                and 'duration_ms' in span
            ]
            
            if not service_spans:
                return 0.0
            
            latencies = [span['duration_ms'] for span in service_spans]
            return statistics.mean(latencies)
        
        except Exception:
            return 0.0
    
    def _find_critical_path(self, service: str) -> List[str]:
        """Find critical path for a service."""
        # This would implement critical path analysis
        # For now, return a simple path
        return [service]


# Export main classes and functions
__all__ = [
    'BottleneckType',
    'SeverityLevel',
    'PerformanceMetric',
    'BottleneckDetection',
    'LatencyAnalysis',
    'DependencyMapping',
    'PerformanceAnalyzer',
]
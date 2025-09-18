"""
Bottleneck Detection System for FastAPI Microservices SDK.

This module provides intelligent bottleneck detection and performance
recommendation system for identifying and resolving performance issues.

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
from scipy.stats import pearsonr

from .config import APMConfig, BottleneckType
from .exceptions import BottleneckDetectionError


class BottleneckSeverity(str, Enum):
    """Bottleneck severity enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationType(str, Enum):
    """Performance recommendation type enumeration."""
    SCALE_UP = "scale_up"
    SCALE_OUT = "scale_out"
    OPTIMIZE_CODE = "optimize_code"
    CACHE_IMPLEMENTATION = "cache_implementation"
    DATABASE_OPTIMIZATION = "database_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"
    RESOURCE_ALLOCATION = "resource_allocation"


@dataclass
class PerformanceRecommendation:
    """Performance optimization recommendation."""
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    priority: str  # "low", "medium", "high", "critical"
    estimated_impact: str  # "low", "medium", "high"
    implementation_effort: str  # "low", "medium", "high"
    specific_actions: List[str]
    metrics_to_monitor: List[str]
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'recommendation_id': self.recommendation_id,
            'recommendation_type': self.recommendation_type.value,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'estimated_impact': self.estimated_impact,
            'implementation_effort': self.implementation_effort,
            'specific_actions': self.specific_actions,
            'metrics_to_monitor': self.metrics_to_monitor,
            'confidence_score': self.confidence_score
        }


@dataclass
class BottleneckAnalysis:
    """Bottleneck analysis result."""
    analysis_id: str
    bottleneck_type: BottleneckType
    severity: BottleneckSeverity
    detected_at: datetime
    resource_name: str
    utilization_percent: float
    impact_score: float
    root_cause: str
    affected_operations: List[str]
    recommendations: List[PerformanceRecommendation]
    correlation_data: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'analysis_id': self.analysis_id,
            'bottleneck_type': self.bottleneck_type.value,
            'severity': self.severity.value,
            'detected_at': self.detected_at.isoformat(),
            'resource_name': self.resource_name,
            'utilization_percent': self.utilization_percent,
            'impact_score': self.impact_score,
            'root_cause': self.root_cause,
            'affected_operations': self.affected_operations,
            'recommendations': [r.to_dict() for r in self.recommendations],
            'correlation_data': self.correlation_data
        }


class BottleneckDetector:
    """Intelligent bottleneck detection and analysis system."""
    
    def __init__(self, config: APMConfig):
        """Initialize bottleneck detector."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Detection state
        self.bottleneck_history: List[BottleneckAnalysis] = []
        self.active_bottlenecks: Dict[str, BottleneckAnalysis] = {}
        
        # Metrics collection
        self.resource_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.performance_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # Analysis parameters
        self.correlation_cache: Dict[str, float] = {}
        
        # Background tasks
        self.is_running = False
        self.detection_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start bottleneck detection."""
        try:
            if self.is_running:
                self.logger.warning("Bottleneck detector is already running")
                return
            
            self.logger.info("Starting bottleneck detector...")
            
            # Start background detection
            if self.config.bottleneck.enabled:
                self.detection_task = asyncio.create_task(self._detection_loop())
            
            self.is_running = True
            self.logger.info("Bottleneck detector started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting bottleneck detector: {e}")
            raise BottleneckDetectionError(
                f"Failed to start bottleneck detector: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop bottleneck detection."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping bottleneck detector...")
            
            # Cancel background tasks
            if self.detection_task:
                self.detection_task.cancel()
                try:
                    await self.detection_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Bottleneck detector stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping bottleneck detector: {e}")
    
    async def add_resource_metric(self, resource_name: str, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Add resource utilization metric."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            metric_key = f"{resource_name}_{metric_type}"
            self.resource_metrics[metric_key].append((timestamp, value))
            
            # Trigger immediate analysis for high utilization
            if value > 90.0:  # High utilization threshold
                await self._analyze_resource_bottleneck(resource_name, metric_type, value)
                
        except Exception as e:
            self.logger.error(f"Error adding resource metric: {e}")
    
    async def add_performance_metric(self, operation_name: str, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Add performance metric."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            metric_key = f"{operation_name}_{metric_type}"
            self.performance_metrics[metric_key].append((timestamp, value))
            
        except Exception as e:
            self.logger.error(f"Error adding performance metric: {e}")
    
    async def detect_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect current bottlenecks."""
        try:
            detected_bottlenecks = []
            
            # Analyze CPU bottlenecks
            cpu_bottlenecks = await self._detect_cpu_bottlenecks()
            detected_bottlenecks.extend(cpu_bottlenecks)
            
            # Analyze memory bottlenecks
            memory_bottlenecks = await self._detect_memory_bottlenecks()
            detected_bottlenecks.extend(memory_bottlenecks)
            
            # Analyze I/O bottlenecks
            io_bottlenecks = await self._detect_io_bottlenecks()
            detected_bottlenecks.extend(io_bottlenecks)
            
            # Analyze network bottlenecks
            network_bottlenecks = await self._detect_network_bottlenecks()
            detected_bottlenecks.extend(network_bottlenecks)
            
            # Analyze database bottlenecks
            db_bottlenecks = await self._detect_database_bottlenecks()
            detected_bottlenecks.extend(db_bottlenecks)
            
            # Update active bottlenecks
            for bottleneck in detected_bottlenecks:
                self.active_bottlenecks[bottleneck.analysis_id] = bottleneck
                self.bottleneck_history.append(bottleneck)
            
            # Maintain history size
            if len(self.bottleneck_history) > 1000:
                self.bottleneck_history = self.bottleneck_history[-1000:]
            
            return detected_bottlenecks
            
        except Exception as e:
            self.logger.error(f"Error detecting bottlenecks: {e}")
            raise BottleneckDetectionError(
                f"Failed to detect bottlenecks: {e}",
                original_error=e
            )
    
    async def analyze_bottleneck(self, resource_name: str, bottleneck_type: BottleneckType) -> Optional[BottleneckAnalysis]:
        """Analyze specific bottleneck."""
        try:
            if bottleneck_type == BottleneckType.CPU_BOUND:
                return await self._analyze_cpu_bottleneck(resource_name)
            elif bottleneck_type == BottleneckType.MEMORY_BOUND:
                return await self._analyze_memory_bottleneck(resource_name)
            elif bottleneck_type == BottleneckType.IO_BOUND:
                return await self._analyze_io_bottleneck(resource_name)
            elif bottleneck_type == BottleneckType.NETWORK_BOUND:
                return await self._analyze_network_bottleneck(resource_name)
            elif bottleneck_type == BottleneckType.DATABASE_BOUND:
                return await self._analyze_database_bottleneck(resource_name)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error analyzing bottleneck: {e}")
            raise BottleneckDetectionError(
                f"Failed to analyze bottleneck: {e}",
                detection_method="specific_analysis",
                resource_type=bottleneck_type.value,
                original_error=e
            )
    
    async def get_recommendations(self, bottleneck_analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate performance recommendations for bottleneck."""
        try:
            recommendations = []
            
            if bottleneck_analysis.bottleneck_type == BottleneckType.CPU_BOUND:
                recommendations.extend(await self._generate_cpu_recommendations(bottleneck_analysis))
            elif bottleneck_analysis.bottleneck_type == BottleneckType.MEMORY_BOUND:
                recommendations.extend(await self._generate_memory_recommendations(bottleneck_analysis))
            elif bottleneck_analysis.bottleneck_type == BottleneckType.IO_BOUND:
                recommendations.extend(await self._generate_io_recommendations(bottleneck_analysis))
            elif bottleneck_analysis.bottleneck_type == BottleneckType.NETWORK_BOUND:
                recommendations.extend(await self._generate_network_recommendations(bottleneck_analysis))
            elif bottleneck_analysis.bottleneck_type == BottleneckType.DATABASE_BOUND:
                recommendations.extend(await self._generate_database_recommendations(bottleneck_analysis))
            
            # Sort by priority and confidence
            recommendations.sort(key=lambda r: (
                self._priority_score(r.priority),
                r.confidence_score
            ), reverse=True)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _detect_cpu_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect CPU bottlenecks."""
        bottlenecks = []
        
        for metric_key, data in self.resource_metrics.items():
            if "cpu" in metric_key.lower():
                recent_data = list(data)[-20:]  # Last 20 data points
                
                if len(recent_data) < 10:
                    continue
                
                values = [point[1] for point in recent_data]
                avg_utilization = statistics.mean(values)
                
                if avg_utilization > self.config.bottleneck.cpu_bottleneck_threshold:
                    analysis = await self._create_bottleneck_analysis(
                        BottleneckType.CPU_BOUND,
                        metric_key.split('_')[0],
                        avg_utilization,
                        "High CPU utilization detected"
                    )
                    bottlenecks.append(analysis)
        
        return bottlenecks
    
    async def _detect_memory_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect memory bottlenecks."""
        bottlenecks = []
        
        for metric_key, data in self.resource_metrics.items():
            if "memory" in metric_key.lower():
                recent_data = list(data)[-20:]
                
                if len(recent_data) < 10:
                    continue
                
                values = [point[1] for point in recent_data]
                avg_utilization = statistics.mean(values)
                
                if avg_utilization > self.config.bottleneck.memory_bottleneck_threshold:
                    analysis = await self._create_bottleneck_analysis(
                        BottleneckType.MEMORY_BOUND,
                        metric_key.split('_')[0],
                        avg_utilization,
                        "High memory utilization detected"
                    )
                    bottlenecks.append(analysis)
        
        return bottlenecks
    
    async def _detect_io_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect I/O bottlenecks."""
        bottlenecks = []
        
        for metric_key, data in self.resource_metrics.items():
            if "io" in metric_key.lower() or "disk" in metric_key.lower():
                recent_data = list(data)[-20:]
                
                if len(recent_data) < 10:
                    continue
                
                values = [point[1] for point in recent_data]
                avg_utilization = statistics.mean(values)
                
                if avg_utilization > self.config.bottleneck.io_bottleneck_threshold:
                    analysis = await self._create_bottleneck_analysis(
                        BottleneckType.IO_BOUND,
                        metric_key.split('_')[0],
                        avg_utilization,
                        "High I/O utilization detected"
                    )
                    bottlenecks.append(analysis)
        
        return bottlenecks
    
    async def _detect_network_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect network bottlenecks."""
        bottlenecks = []
        
        for metric_key, data in self.resource_metrics.items():
            if "network" in metric_key.lower():
                recent_data = list(data)[-20:]
                
                if len(recent_data) < 10:
                    continue
                
                values = [point[1] for point in recent_data]
                avg_utilization = statistics.mean(values)
                
                if avg_utilization > self.config.bottleneck.network_bottleneck_threshold:
                    analysis = await self._create_bottleneck_analysis(
                        BottleneckType.NETWORK_BOUND,
                        metric_key.split('_')[0],
                        avg_utilization,
                        "High network utilization detected"
                    )
                    bottlenecks.append(analysis)
        
        return bottlenecks
    
    async def _detect_database_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Detect database bottlenecks."""
        bottlenecks = []
        
        # Look for database-related performance metrics
        for metric_key, data in self.performance_metrics.items():
            if "db" in metric_key.lower() or "database" in metric_key.lower():
                recent_data = list(data)[-20:]
                
                if len(recent_data) < 10:
                    continue
                
                values = [point[1] for point in recent_data]
                avg_response_time = statistics.mean(values)
                
                # Check if database response time is high
                if avg_response_time > 1000:  # 1 second threshold
                    analysis = await self._create_bottleneck_analysis(
                        BottleneckType.DATABASE_BOUND,
                        metric_key.split('_')[0],
                        avg_response_time,
                        "High database response time detected"
                    )
                    bottlenecks.append(analysis)
        
        return bottlenecks
    
    async def _create_bottleneck_analysis(
        self,
        bottleneck_type: BottleneckType,
        resource_name: str,
        utilization: float,
        root_cause: str
    ) -> BottleneckAnalysis:
        """Create bottleneck analysis."""
        analysis_id = f"bottleneck_{bottleneck_type.value}_{int(datetime.now().timestamp())}"
        
        # Calculate severity
        severity = self._calculate_severity(utilization, bottleneck_type)
        
        # Calculate impact score
        impact_score = self._calculate_impact_score(bottleneck_type, utilization)
        
        # Find affected operations
        affected_operations = await self._find_affected_operations(resource_name, bottleneck_type)
        
        # Calculate correlations
        correlation_data = await self._calculate_correlations(resource_name, bottleneck_type)
        
        # Generate recommendations
        analysis = BottleneckAnalysis(
            analysis_id=analysis_id,
            bottleneck_type=bottleneck_type,
            severity=severity,
            detected_at=datetime.now(timezone.utc),
            resource_name=resource_name,
            utilization_percent=utilization,
            impact_score=impact_score,
            root_cause=root_cause,
            affected_operations=affected_operations,
            recommendations=[],  # Will be populated later
            correlation_data=correlation_data
        )
        
        # Generate recommendations if enabled
        if self.config.bottleneck.generate_recommendations:
            analysis.recommendations = await self.get_recommendations(analysis)
        
        return analysis
    
    def _calculate_severity(self, utilization: float, bottleneck_type: BottleneckType) -> BottleneckSeverity:
        """Calculate bottleneck severity."""
        if bottleneck_type == BottleneckType.CPU_BOUND:
            threshold = self.config.bottleneck.cpu_bottleneck_threshold
        elif bottleneck_type == BottleneckType.MEMORY_BOUND:
            threshold = self.config.bottleneck.memory_bottleneck_threshold
        elif bottleneck_type == BottleneckType.IO_BOUND:
            threshold = self.config.bottleneck.io_bottleneck_threshold
        elif bottleneck_type == BottleneckType.NETWORK_BOUND:
            threshold = self.config.bottleneck.network_bottleneck_threshold
        else:
            threshold = 80.0
        
        if utilization >= threshold * 1.2:  # 20% above threshold
            return BottleneckSeverity.CRITICAL
        elif utilization >= threshold * 1.1:  # 10% above threshold
            return BottleneckSeverity.HIGH
        elif utilization >= threshold * 1.05:  # 5% above threshold
            return BottleneckSeverity.MEDIUM
        else:
            return BottleneckSeverity.LOW
    
    def _calculate_impact_score(self, bottleneck_type: BottleneckType, utilization: float) -> float:
        """Calculate impact score (0-100)."""
        base_score = min(utilization, 100.0)
        
        # Weight by bottleneck type criticality
        type_weights = {
            BottleneckType.CPU_BOUND: 1.0,
            BottleneckType.MEMORY_BOUND: 0.9,
            BottleneckType.IO_BOUND: 0.8,
            BottleneckType.NETWORK_BOUND: 0.7,
            BottleneckType.DATABASE_BOUND: 0.85
        }
        
        weight = type_weights.get(bottleneck_type, 0.5)
        return base_score * weight
    
    async def _find_affected_operations(self, resource_name: str, bottleneck_type: BottleneckType) -> List[str]:
        """Find operations affected by bottleneck."""
        affected = []
        
        # Look for performance metrics that correlate with resource utilization
        for metric_key in self.performance_metrics.keys():
            if resource_name in metric_key or bottleneck_type.value in metric_key:
                operation_name = metric_key.split('_')[0]
                if operation_name not in affected:
                    affected.append(operation_name)
        
        return affected[:10]  # Limit to top 10
    
    async def _calculate_correlations(self, resource_name: str, bottleneck_type: BottleneckType) -> Dict[str, float]:
        """Calculate correlations between resource utilization and performance metrics."""
        correlations = {}
        
        # Find resource metric data
        resource_metric_key = f"{resource_name}_{bottleneck_type.value}"
        resource_data = self.resource_metrics.get(resource_metric_key, deque())
        
        if len(resource_data) < 10:
            return correlations
        
        resource_values = [point[1] for point in list(resource_data)[-50:]]
        resource_times = [point[0] for point in list(resource_data)[-50:]]
        
        # Calculate correlations with performance metrics
        for perf_key, perf_data in self.performance_metrics.items():
            if len(perf_data) < 10:
                continue
            
            # Align time series
            perf_values = []
            for res_time in resource_times:
                # Find closest performance metric value
                closest_perf = min(
                    perf_data,
                    key=lambda x: abs((x[0] - res_time).total_seconds()),
                    default=None
                )
                if closest_perf and abs((closest_perf[0] - res_time).total_seconds()) < 300:  # 5 minutes
                    perf_values.append(closest_perf[1])
                else:
                    perf_values.append(0.0)
            
            if len(perf_values) == len(resource_values) and len(perf_values) > 5:
                try:
                    correlation, p_value = pearsonr(resource_values, perf_values)
                    if not np.isnan(correlation) and p_value < 0.05:  # Significant correlation
                        correlations[perf_key] = correlation
                except Exception:
                    pass
        
        return correlations
    
    async def _generate_cpu_recommendations(self, analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate CPU bottleneck recommendations."""
        recommendations = []
        
        # Scale up recommendation
        scale_up = PerformanceRecommendation(
            recommendation_id=f"cpu_scale_up_{analysis.analysis_id}",
            recommendation_type=RecommendationType.SCALE_UP,
            title="Increase CPU Resources",
            description="Add more CPU cores or upgrade to a higher CPU tier",
            priority="high" if analysis.severity in [BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL] else "medium",
            estimated_impact="high",
            implementation_effort="medium",
            specific_actions=[
                "Increase CPU allocation in container/VM configuration",
                "Consider upgrading to a higher CPU tier",
                "Monitor CPU utilization after scaling"
            ],
            metrics_to_monitor=["cpu_utilization", "response_time", "throughput"],
            confidence_score=0.8
        )
        recommendations.append(scale_up)
        
        # Code optimization recommendation
        optimize_code = PerformanceRecommendation(
            recommendation_id=f"cpu_optimize_{analysis.analysis_id}",
            recommendation_type=RecommendationType.OPTIMIZE_CODE,
            title="Optimize CPU-Intensive Code",
            description="Review and optimize algorithms and code paths that consume high CPU",
            priority="medium",
            estimated_impact="medium",
            implementation_effort="high",
            specific_actions=[
                "Profile application to identify CPU hotspots",
                "Optimize algorithms and data structures",
                "Implement caching for expensive computations",
                "Consider asynchronous processing for CPU-intensive tasks"
            ],
            metrics_to_monitor=["cpu_utilization", "function_execution_time"],
            confidence_score=0.7
        )
        recommendations.append(optimize_code)
        
        return recommendations
    
    async def _generate_memory_recommendations(self, analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate memory bottleneck recommendations."""
        recommendations = []
        
        # Scale up memory
        scale_up = PerformanceRecommendation(
            recommendation_id=f"memory_scale_up_{analysis.analysis_id}",
            recommendation_type=RecommendationType.SCALE_UP,
            title="Increase Memory Allocation",
            description="Add more RAM to handle memory-intensive operations",
            priority="high" if analysis.severity in [BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL] else "medium",
            estimated_impact="high",
            implementation_effort="low",
            specific_actions=[
                "Increase memory allocation in container/VM configuration",
                "Monitor memory usage patterns",
                "Implement memory usage alerts"
            ],
            metrics_to_monitor=["memory_utilization", "gc_frequency", "response_time"],
            confidence_score=0.9
        )
        recommendations.append(scale_up)
        
        # Memory optimization
        optimize_memory = PerformanceRecommendation(
            recommendation_id=f"memory_optimize_{analysis.analysis_id}",
            recommendation_type=RecommendationType.OPTIMIZE_CODE,
            title="Optimize Memory Usage",
            description="Implement memory optimization techniques to reduce memory consumption",
            priority="medium",
            estimated_impact="medium",
            implementation_effort="medium",
            specific_actions=[
                "Implement object pooling for frequently used objects",
                "Optimize data structures and reduce memory footprint",
                "Implement proper garbage collection tuning",
                "Add memory leak detection and monitoring"
            ],
            metrics_to_monitor=["memory_utilization", "gc_time", "object_count"],
            confidence_score=0.7
        )
        recommendations.append(optimize_memory)
        
        return recommendations
    
    async def _generate_io_recommendations(self, analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate I/O bottleneck recommendations."""
        recommendations = []
        
        # Implement caching
        caching = PerformanceRecommendation(
            recommendation_id=f"io_caching_{analysis.analysis_id}",
            recommendation_type=RecommendationType.CACHE_IMPLEMENTATION,
            title="Implement I/O Caching",
            description="Add caching layer to reduce I/O operations",
            priority="high",
            estimated_impact="high",
            implementation_effort="medium",
            specific_actions=[
                "Implement Redis or in-memory caching",
                "Cache frequently accessed data",
                "Implement cache invalidation strategies",
                "Monitor cache hit rates"
            ],
            metrics_to_monitor=["io_operations", "cache_hit_rate", "response_time"],
            confidence_score=0.8
        )
        recommendations.append(caching)
        
        return recommendations
    
    async def _generate_network_recommendations(self, analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate network bottleneck recommendations."""
        recommendations = []
        
        # Network optimization
        network_opt = PerformanceRecommendation(
            recommendation_id=f"network_optimize_{analysis.analysis_id}",
            recommendation_type=RecommendationType.NETWORK_OPTIMIZATION,
            title="Optimize Network Usage",
            description="Implement network optimization techniques",
            priority="medium",
            estimated_impact="medium",
            implementation_effort="medium",
            specific_actions=[
                "Implement request batching",
                "Use connection pooling",
                "Compress network payloads",
                "Optimize API call patterns"
            ],
            metrics_to_monitor=["network_throughput", "connection_count", "response_time"],
            confidence_score=0.7
        )
        recommendations.append(network_opt)
        
        return recommendations
    
    async def _generate_database_recommendations(self, analysis: BottleneckAnalysis) -> List[PerformanceRecommendation]:
        """Generate database bottleneck recommendations."""
        recommendations = []
        
        # Database optimization
        db_opt = PerformanceRecommendation(
            recommendation_id=f"db_optimize_{analysis.analysis_id}",
            recommendation_type=RecommendationType.DATABASE_OPTIMIZATION,
            title="Optimize Database Performance",
            description="Implement database optimization techniques",
            priority="high",
            estimated_impact="high",
            implementation_effort="medium",
            specific_actions=[
                "Add database indexes for slow queries",
                "Implement query optimization",
                "Use database connection pooling",
                "Consider database caching",
                "Optimize database schema"
            ],
            metrics_to_monitor=["db_response_time", "query_count", "connection_pool_usage"],
            confidence_score=0.8
        )
        recommendations.append(db_opt)
        
        return recommendations
    
    def _priority_score(self, priority: str) -> int:
        """Convert priority to numeric score."""
        priority_scores = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        return priority_scores.get(priority, 0)
    
    async def _analyze_resource_bottleneck(self, resource_name: str, metric_type: str, value: float):
        """Analyze immediate resource bottleneck."""
        try:
            # Determine bottleneck type
            if "cpu" in metric_type.lower():
                bottleneck_type = BottleneckType.CPU_BOUND
            elif "memory" in metric_type.lower():
                bottleneck_type = BottleneckType.MEMORY_BOUND
            elif "io" in metric_type.lower() or "disk" in metric_type.lower():
                bottleneck_type = BottleneckType.IO_BOUND
            elif "network" in metric_type.lower():
                bottleneck_type = BottleneckType.NETWORK_BOUND
            else:
                return
            
            # Create analysis
            analysis = await self._create_bottleneck_analysis(
                bottleneck_type,
                resource_name,
                value,
                f"High {metric_type} utilization: {value:.1f}%"
            )
            
            self.active_bottlenecks[analysis.analysis_id] = analysis
            self.bottleneck_history.append(analysis)
            
            self.logger.warning(
                f"Bottleneck detected: {bottleneck_type.value} on {resource_name} "
                f"({value:.1f}% utilization)"
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing resource bottleneck: {e}")
    
    async def _detection_loop(self):
        """Background bottleneck detection loop."""
        while self.is_running:
            try:
                # Detect bottlenecks at configured interval
                await asyncio.sleep(self.config.bottleneck.analysis_window.total_seconds())
                
                if not self.is_running:
                    break
                
                # Run bottleneck detection
                await self.detect_bottlenecks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in bottleneck detection loop: {e}")
                await asyncio.sleep(60)
    
    async def get_bottleneck_history(self, limit: int = 100) -> List[BottleneckAnalysis]:
        """Get bottleneck detection history."""
        return self.bottleneck_history[-limit:]
    
    async def get_active_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Get currently active bottlenecks."""
        return list(self.active_bottlenecks.values())
    
    async def resolve_bottleneck(self, analysis_id: str):
        """Mark bottleneck as resolved."""
        if analysis_id in self.active_bottlenecks:
            del self.active_bottlenecks[analysis_id]
            self.logger.info(f"Bottleneck resolved: {analysis_id}")
    
    async def get_detector_health(self) -> Dict[str, Any]:
        """Get bottleneck detector health status."""
        return {
            'is_running': self.is_running,
            'active_bottlenecks': len(self.active_bottlenecks),
            'total_detections': len(self.bottleneck_history),
            'resource_metrics_tracked': len(self.resource_metrics),
            'performance_metrics_tracked': len(self.performance_metrics)
        }


def create_bottleneck_detector(config: APMConfig) -> BottleneckDetector:
    """Create bottleneck detector instance."""
    return BottleneckDetector(config)
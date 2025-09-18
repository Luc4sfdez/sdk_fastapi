"""
Optimization Recommendation Engine for FastAPI Microservices SDK.

This module provides intelligent performance optimization recommendations
using ML algorithms and performance analysis.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import numpy as np
from collections import defaultdict, deque

from .config import OptimizationConfig, RecommendationType, OptimizationStrategy
from .exceptions import RecommendationError


class RecommendationPriority(str, Enum):
    """Recommendation priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImplementationComplexity(str, Enum):
    """Implementation complexity enumeration."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class PerformanceRecommendation:
    """Performance optimization recommendation."""
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    priority: RecommendationPriority
    confidence_score: float
    estimated_performance_gain: float  # Percentage improvement
    estimated_cost_impact: float  # Cost change (positive = increase, negative = decrease)
    implementation_complexity: ImplementationComplexity
    implementation_steps: List[str]
    validation_metrics: List[str]
    rollback_plan: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'recommendation_id': self.recommendation_id,
            'recommendation_type': self.recommendation_type.value,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'confidence_score': self.confidence_score,
            'estimated_performance_gain': self.estimated_performance_gain,
            'estimated_cost_impact': self.estimated_cost_impact,
            'implementation_complexity': self.implementation_complexity.value,
            'implementation_steps': self.implementation_steps,
            'validation_metrics': self.validation_metrics,
            'rollback_plan': self.rollback_plan,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'metadata': self.metadata
        }


class OptimizationRecommendationEngine:
    """Intelligent optimization recommendation engine."""
    
    def __init__(self, config: OptimizationConfig):
        """Initialize recommendation engine."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Recommendation state
        self.active_recommendations: Dict[str, PerformanceRecommendation] = {}
        self.recommendation_history: List[PerformanceRecommendation] = []
        self.implemented_recommendations: Dict[str, Dict[str, Any]] = {}
        
        # Performance data for analysis
        self.performance_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self.resource_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        
        # ML models for recommendations
        self.recommendation_models: Dict[str, Any] = {}
        
        # Background tasks
        self.is_running = False
        self.recommendation_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the recommendation engine."""
        try:
            if self.is_running:
                self.logger.warning("Recommendation engine is already running")
                return
            
            self.logger.info("Starting optimization recommendation engine...")
            
            # Start background recommendation generation
            if self.config.recommendations.enabled:
                self.recommendation_task = asyncio.create_task(self._recommendation_loop())
            
            self.is_running = True
            self.logger.info("Recommendation engine started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting recommendation engine: {e}")
            raise RecommendationError(
                f"Failed to start recommendation engine: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop the recommendation engine."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping recommendation engine...")
            
            # Cancel background tasks
            if self.recommendation_task:
                self.recommendation_task.cancel()
                try:
                    await self.recommendation_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Recommendation engine stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping recommendation engine: {e}")
    
    async def add_performance_data(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add performance data for analysis."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            self.performance_metrics[metric_name].append((timestamp, value))
            
        except Exception as e:
            self.logger.error(f"Error adding performance data: {e}")
    
    async def add_resource_data(self, resource_name: str, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Add resource utilization data for analysis."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            metric_key = f"{resource_name}_{metric_type}"
            self.resource_metrics[metric_key].append((timestamp, value))
            
        except Exception as e:
            self.logger.error(f"Error adding resource data: {e}")
    
    async def generate_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate optimization recommendations based on current performance data."""
        try:
            recommendations = []
            
            # Generate CPU optimization recommendations
            cpu_recommendations = await self._generate_cpu_recommendations()
            recommendations.extend(cpu_recommendations)
            
            # Generate memory optimization recommendations
            memory_recommendations = await self._generate_memory_recommendations()
            recommendations.extend(memory_recommendations)
            
            # Generate I/O optimization recommendations
            io_recommendations = await self._generate_io_recommendations()
            recommendations.extend(io_recommendations)
            
            # Generate database optimization recommendations
            db_recommendations = await self._generate_database_recommendations()
            recommendations.extend(db_recommendations)
            
            # Generate cache optimization recommendations
            cache_recommendations = await self._generate_cache_recommendations()
            recommendations.extend(cache_recommendations)
            
            # Filter by confidence threshold
            filtered_recommendations = [
                rec for rec in recommendations
                if rec.confidence_score >= self.config.recommendations.min_confidence_threshold
            ]
            
            # Sort by priority and confidence
            filtered_recommendations.sort(
                key=lambda r: (self._priority_score(r.priority), r.confidence_score),
                reverse=True
            )
            
            # Limit number of recommendations
            max_recommendations = self.config.recommendations.max_recommendations_per_analysis
            final_recommendations = filtered_recommendations[:max_recommendations]
            
            # Store active recommendations
            for rec in final_recommendations:
                self.active_recommendations[rec.recommendation_id] = rec
                self.recommendation_history.append(rec)
            
            # Maintain history size
            if len(self.recommendation_history) > 1000:
                self.recommendation_history = self.recommendation_history[-1000:]
            
            self.logger.info(f"Generated {len(final_recommendations)} optimization recommendations")
            return final_recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            raise RecommendationError(
                f"Failed to generate recommendations: {e}",
                original_error=e
            )
    
    async def _generate_cpu_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate CPU optimization recommendations."""
        recommendations = []
        
        # Analyze CPU utilization patterns
        cpu_metrics = [
            key for key in self.resource_metrics.keys()
            if 'cpu' in key.lower()
        ]
        
        for metric_key in cpu_metrics:
            data = list(self.resource_metrics[metric_key])
            if len(data) < 10:
                continue
            
            recent_values = [point[1] for point in data[-20:]]
            avg_cpu = statistics.mean(recent_values)
            max_cpu = max(recent_values)
            
            # High CPU utilization recommendation
            if avg_cpu > 80.0:
                rec = PerformanceRecommendation(
                    recommendation_id=f"cpu_high_util_{int(datetime.now().timestamp())}",
                    recommendation_type=RecommendationType.CPU_OPTIMIZATION,
                    title="Optimize High CPU Utilization",
                    description=f"CPU utilization is high (avg: {avg_cpu:.1f}%). Consider CPU optimization strategies.",
                    priority=RecommendationPriority.HIGH if avg_cpu > 90 else RecommendationPriority.MEDIUM,
                    confidence_score=0.9,
                    estimated_performance_gain=15.0,
                    estimated_cost_impact=0.0,
                    implementation_complexity=ImplementationComplexity.MODERATE,
                    implementation_steps=[
                        "Profile application to identify CPU hotspots",
                        "Optimize algorithms and data structures",
                        "Implement CPU-intensive task offloading",
                        "Consider horizontal scaling"
                    ],
                    validation_metrics=["cpu_utilization", "response_time", "throughput"],
                    rollback_plan="Revert code changes and restore previous configuration",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                    metadata={
                        'current_cpu_avg': avg_cpu,
                        'current_cpu_max': max_cpu,
                        'metric_source': metric_key
                    }
                )
                recommendations.append(rec)
            
            # CPU underutilization recommendation
            elif avg_cpu < 20.0:
                rec = PerformanceRecommendation(
                    recommendation_id=f"cpu_under_util_{int(datetime.now().timestamp())}",
                    recommendation_type=RecommendationType.CPU_OPTIMIZATION,
                    title="Optimize CPU Resource Allocation",
                    description=f"CPU utilization is low (avg: {avg_cpu:.1f}%). Consider reducing CPU allocation to save costs.",
                    priority=RecommendationPriority.LOW,
                    confidence_score=0.8,
                    estimated_performance_gain=0.0,
                    estimated_cost_impact=-20.0,  # Cost reduction
                    implementation_complexity=ImplementationComplexity.SIMPLE,
                    implementation_steps=[
                        "Monitor CPU usage patterns over longer period",
                        "Reduce CPU allocation in container/VM configuration",
                        "Implement CPU usage alerts for monitoring"
                    ],
                    validation_metrics=["cpu_utilization", "cost_metrics"],
                    rollback_plan="Restore previous CPU allocation if performance degrades",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                    metadata={
                        'current_cpu_avg': avg_cpu,
                        'potential_cost_savings': 20.0
                    }
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _generate_memory_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate memory optimization recommendations."""
        recommendations = []
        
        # Analyze memory utilization patterns
        memory_metrics = [
            key for key in self.resource_metrics.keys()
            if 'memory' in key.lower()
        ]
        
        for metric_key in memory_metrics:
            data = list(self.resource_metrics[metric_key])
            if len(data) < 10:
                continue
            
            recent_values = [point[1] for point in data[-20:]]
            avg_memory = statistics.mean(recent_values)
            max_memory = max(recent_values)
            
            # High memory utilization
            if avg_memory > 85.0:
                rec = PerformanceRecommendation(
                    recommendation_id=f"memory_high_util_{int(datetime.now().timestamp())}",
                    recommendation_type=RecommendationType.MEMORY_OPTIMIZATION,
                    title="Optimize High Memory Usage",
                    description=f"Memory utilization is high (avg: {avg_memory:.1f}%). Implement memory optimization strategies.",
                    priority=RecommendationPriority.HIGH if avg_memory > 95 else RecommendationPriority.MEDIUM,
                    confidence_score=0.85,
                    estimated_performance_gain=20.0,
                    estimated_cost_impact=5.0,
                    implementation_complexity=ImplementationComplexity.MODERATE,
                    implementation_steps=[
                        "Implement memory profiling to identify leaks",
                        "Optimize data structures and object lifecycle",
                        "Implement memory caching strategies",
                        "Consider memory allocation tuning"
                    ],
                    validation_metrics=["memory_utilization", "gc_frequency", "response_time"],
                    rollback_plan="Revert memory optimization changes if issues occur",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=5),
                    metadata={
                        'current_memory_avg': avg_memory,
                        'current_memory_max': max_memory
                    }
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _generate_io_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate I/O optimization recommendations."""
        recommendations = []
        
        # Analyze I/O patterns from performance metrics
        io_metrics = [
            key for key in self.performance_metrics.keys()
            if 'io' in key.lower() or 'disk' in key.lower()
        ]
        
        for metric_key in io_metrics:
            data = list(self.performance_metrics[metric_key])
            if len(data) < 10:
                continue
            
            recent_values = [point[1] for point in data[-20:]]
            avg_io = statistics.mean(recent_values)
            
            # High I/O latency
            if avg_io > 100:  # Assuming milliseconds
                rec = PerformanceRecommendation(
                    recommendation_id=f"io_optimization_{int(datetime.now().timestamp())}",
                    recommendation_type=RecommendationType.IO_OPTIMIZATION,
                    title="Optimize I/O Performance",
                    description=f"I/O latency is high (avg: {avg_io:.1f}ms). Implement I/O optimization strategies.",
                    priority=RecommendationPriority.MEDIUM,
                    confidence_score=0.75,
                    estimated_performance_gain=25.0,
                    estimated_cost_impact=10.0,
                    implementation_complexity=ImplementationComplexity.MODERATE,
                    implementation_steps=[
                        "Implement I/O caching layer",
                        "Optimize database queries and indexes",
                        "Consider SSD storage upgrade",
                        "Implement asynchronous I/O operations"
                    ],
                    validation_metrics=["io_latency", "throughput", "response_time"],
                    rollback_plan="Disable caching and revert to synchronous I/O if needed",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=10),
                    metadata={
                        'current_io_latency': avg_io,
                        'metric_source': metric_key
                    }
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _generate_database_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate database optimization recommendations."""
        recommendations = []
        
        # Analyze database performance metrics
        db_metrics = [
            key for key in self.performance_metrics.keys()
            if 'db' in key.lower() or 'database' in key.lower() or 'query' in key.lower()
        ]
        
        for metric_key in db_metrics:
            data = list(self.performance_metrics[metric_key])
            if len(data) < 10:
                continue
            
            recent_values = [point[1] for point in data[-20:]]
            avg_db_time = statistics.mean(recent_values)
            
            # Slow database queries
            if avg_db_time > 500:  # Assuming milliseconds
                rec = PerformanceRecommendation(
                    recommendation_id=f"db_optimization_{int(datetime.now().timestamp())}",
                    recommendation_type=RecommendationType.DATABASE_OPTIMIZATION,
                    title="Optimize Database Performance",
                    description=f"Database query time is high (avg: {avg_db_time:.1f}ms). Implement database optimization.",
                    priority=RecommendationPriority.HIGH,
                    confidence_score=0.9,
                    estimated_performance_gain=30.0,
                    estimated_cost_impact=0.0,
                    implementation_complexity=ImplementationComplexity.COMPLEX,
                    implementation_steps=[
                        "Analyze slow query logs",
                        "Add missing database indexes",
                        "Optimize query structure and joins",
                        "Implement database connection pooling",
                        "Consider query result caching"
                    ],
                    validation_metrics=["db_query_time", "db_connection_count", "response_time"],
                    rollback_plan="Remove new indexes and revert query changes if performance degrades",
                    created_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                    metadata={
                        'current_db_time': avg_db_time,
                        'optimization_type': 'query_optimization'
                    }
                )
                recommendations.append(rec)
        
        return recommendations
    
    async def _generate_cache_recommendations(self) -> List[PerformanceRecommendation]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        # Analyze cache hit rates and performance
        cache_metrics = [
            key for key in self.performance_metrics.keys()
            if 'cache' in key.lower()
        ]
        
        for metric_key in cache_metrics:
            if 'hit_rate' in metric_key.lower():
                data = list(self.performance_metrics[metric_key])
                if len(data) < 10:
                    continue
                
                recent_values = [point[1] for point in data[-20:]]
                avg_hit_rate = statistics.mean(recent_values)
                
                # Low cache hit rate
                if avg_hit_rate < 0.8:  # Less than 80%
                    rec = PerformanceRecommendation(
                        recommendation_id=f"cache_optimization_{int(datetime.now().timestamp())}",
                        recommendation_type=RecommendationType.CACHE_OPTIMIZATION,
                        title="Improve Cache Hit Rate",
                        description=f"Cache hit rate is low ({avg_hit_rate:.1%}). Optimize caching strategy.",
                        priority=RecommendationPriority.MEDIUM,
                        confidence_score=0.8,
                        estimated_performance_gain=20.0,
                        estimated_cost_impact=5.0,
                        implementation_complexity=ImplementationComplexity.MODERATE,
                        implementation_steps=[
                            "Analyze cache usage patterns",
                            "Optimize cache key strategies",
                            "Implement cache warming",
                            "Adjust cache TTL settings",
                            "Consider cache size optimization"
                        ],
                        validation_metrics=["cache_hit_rate", "cache_miss_rate", "response_time"],
                        rollback_plan="Revert cache configuration changes",
                        created_at=datetime.now(timezone.utc),
                        expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                        metadata={
                            'current_hit_rate': avg_hit_rate,
                            'target_hit_rate': 0.9
                        }
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _priority_score(self, priority: RecommendationPriority) -> int:
        """Convert priority to numeric score."""
        priority_scores = {
            RecommendationPriority.CRITICAL: 4,
            RecommendationPriority.HIGH: 3,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 1
        }
        return priority_scores.get(priority, 0)
    
    async def mark_recommendation_implemented(self, recommendation_id: str, implementation_result: Dict[str, Any]):
        """Mark a recommendation as implemented."""
        try:
            if recommendation_id in self.active_recommendations:
                recommendation = self.active_recommendations[recommendation_id]
                
                self.implemented_recommendations[recommendation_id] = {
                    'recommendation': recommendation,
                    'implementation_result': implementation_result,
                    'implemented_at': datetime.now(timezone.utc)
                }
                
                # Remove from active recommendations
                del self.active_recommendations[recommendation_id]
                
                self.logger.info(f"Marked recommendation {recommendation_id} as implemented")
                
        except Exception as e:
            self.logger.error(f"Error marking recommendation as implemented: {e}")
    
    async def get_active_recommendations(self) -> List[PerformanceRecommendation]:
        """Get currently active recommendations."""
        return list(self.active_recommendations.values())
    
    async def get_recommendation_history(self, limit: int = 100) -> List[PerformanceRecommendation]:
        """Get recommendation history."""
        return self.recommendation_history[-limit:]
    
    async def _recommendation_loop(self):
        """Background loop for generating recommendations."""
        while self.is_running:
            try:
                # Generate recommendations at configured interval
                interval = self.config.recommendations.recommendation_refresh_interval.total_seconds()
                await asyncio.sleep(interval)
                
                if not self.is_running:
                    break
                
                # Generate new recommendations
                await self.generate_recommendations()
                
                # Clean up expired recommendations
                await self._cleanup_expired_recommendations()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in recommendation loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _cleanup_expired_recommendations(self):
        """Clean up expired recommendations."""
        try:
            current_time = datetime.now(timezone.utc)
            expired_ids = []
            
            for rec_id, recommendation in self.active_recommendations.items():
                if recommendation.expires_at and recommendation.expires_at <= current_time:
                    expired_ids.append(rec_id)
            
            for rec_id in expired_ids:
                del self.active_recommendations[rec_id]
                self.logger.info(f"Removed expired recommendation: {rec_id}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired recommendations: {e}")
    
    async def get_engine_health(self) -> Dict[str, Any]:
        """Get recommendation engine health status."""
        return {
            'is_running': self.is_running,
            'active_recommendations': len(self.active_recommendations),
            'total_recommendations_generated': len(self.recommendation_history),
            'implemented_recommendations': len(self.implemented_recommendations),
            'performance_metrics_tracked': len(self.performance_metrics),
            'resource_metrics_tracked': len(self.resource_metrics)
        }


def create_recommendation_engine(config: OptimizationConfig) -> OptimizationRecommendationEngine:
    """Create optimization recommendation engine instance."""
    return OptimizationRecommendationEngine(config)
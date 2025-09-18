"""
Performance Impact Analysis for FastAPI Microservices SDK.

This module provides performance impact analysis for code changes,
deployments, and configuration modifications.

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

from .config import OptimizationConfig
from .exceptions import ImpactAnalysisError


class ImpactType(str, Enum):
    """Impact type enumeration."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class ChangeType(str, Enum):
    """Change type enumeration."""
    CODE_DEPLOYMENT = "code_deployment"
    CONFIGURATION_CHANGE = "configuration_change"
    INFRASTRUCTURE_CHANGE = "infrastructure_change"
    SCALING_EVENT = "scaling_event"


@dataclass
class CodeChangeImpact:
    """Code change impact details."""
    change_id: str
    change_type: ChangeType
    change_description: str
    deployment_time: datetime
    baseline_period: timedelta
    analysis_period: timedelta
    
    # Performance impact metrics
    response_time_impact: float  # Percentage change
    throughput_impact: float
    error_rate_impact: float
    resource_usage_impact: Dict[str, float]
    
    # Statistical significance
    statistical_significance: float
    confidence_level: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'change_id': self.change_id,
            'change_type': self.change_type.value,
            'change_description': self.change_description,
            'deployment_time': self.deployment_time.isoformat(),
            'baseline_period': self.baseline_period.total_seconds(),
            'analysis_period': self.analysis_period.total_seconds(),
            'response_time_impact': self.response_time_impact,
            'throughput_impact': self.throughput_impact,
            'error_rate_impact': self.error_rate_impact,
            'resource_usage_impact': self.resource_usage_impact,
            'statistical_significance': self.statistical_significance,
            'confidence_level': self.confidence_level
        }


@dataclass
class ImpactAnalysisResult:
    """Impact analysis result."""
    analysis_id: str
    change_impact: CodeChangeImpact
    overall_impact_type: ImpactType
    impact_score: float  # -100 to +100 (negative = degradation, positive = improvement)
    recommendations: List[str]
    rollback_recommended: bool
    analysis_timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'analysis_id': self.analysis_id,
            'change_impact': self.change_impact.to_dict(),
            'overall_impact_type': self.overall_impact_type.value,
            'impact_score': self.impact_score,
            'recommendations': self.recommendations,
            'rollback_recommended': self.rollback_recommended,
            'analysis_timestamp': self.analysis_timestamp.isoformat()
        }


class PerformanceImpactAnalyzer:
    """Performance impact analyzer for code changes and deployments."""
    
    def __init__(self, config: OptimizationConfig):
        """Initialize impact analyzer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Analysis state
        self.impact_history: List[ImpactAnalysisResult] = []
        self.pending_analyses: Dict[str, Dict[str, Any]] = {}
        
        # Performance data storage
        self.performance_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=2000)
        )
        
        # Change tracking
        self.tracked_changes: Dict[str, Dict[str, Any]] = {}
        
        # Background tasks
        self.is_running = False
        self.analysis_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the impact analyzer."""
        try:
            if self.is_running:
                self.logger.warning("Impact analyzer is already running")
                return
            
            self.logger.info("Starting performance impact analyzer...")
            
            # Start background analysis
            if self.config.impact_analysis.enabled:
                self.analysis_task = asyncio.create_task(self._analysis_loop())
            
            self.is_running = True
            self.logger.info("Impact analyzer started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting impact analyzer: {e}")
            raise ImpactAnalysisError(
                f"Failed to start impact analyzer: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop the impact analyzer."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping impact analyzer...")
            
            # Cancel background tasks
            if self.analysis_task:
                self.analysis_task.cancel()
                try:
                    await self.analysis_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Impact analyzer stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping impact analyzer: {e}")
    
    async def record_performance_data(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Record performance data for impact analysis."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            self.performance_data[metric_name].append((timestamp, value))
            
        except Exception as e:
            self.logger.error(f"Error recording performance data: {e}")
    
    async def register_change(self, change_id: str, change_type: ChangeType, description: str, deployment_time: Optional[datetime] = None):
        """Register a code/configuration change for impact analysis."""
        try:
            if deployment_time is None:
                deployment_time = datetime.now(timezone.utc)
            
            self.tracked_changes[change_id] = {
                'change_type': change_type,
                'description': description,
                'deployment_time': deployment_time,
                'analysis_scheduled': True
            }
            
            # Schedule impact analysis
            analysis_delay = timedelta(minutes=30)  # Wait 30 minutes after deployment
            self.pending_analyses[change_id] = {
                'scheduled_time': deployment_time + analysis_delay,
                'change_info': self.tracked_changes[change_id]
            }
            
            self.logger.info(f"Registered change {change_id} for impact analysis")
            
        except Exception as e:
            self.logger.error(f"Error registering change: {e}")
            raise ImpactAnalysisError(
                f"Failed to register change: {e}",
                code_change_id=change_id,
                original_error=e
            )
    
    async def analyze_change_impact(self, change_id: str) -> Optional[ImpactAnalysisResult]:
        """Analyze the performance impact of a specific change."""
        try:
            if change_id not in self.tracked_changes:
                raise ImpactAnalysisError(f"Change {change_id} not found in tracked changes")
            
            change_info = self.tracked_changes[change_id]
            deployment_time = change_info['deployment_time']
            
            # Define analysis periods
            baseline_period = self.config.impact_analysis.baseline_comparison_window
            analysis_period = timedelta(hours=2)  # Analyze 2 hours after deployment
            
            # Calculate baseline and post-deployment metrics
            baseline_start = deployment_time - baseline_period
            baseline_end = deployment_time
            analysis_start = deployment_time
            analysis_end = deployment_time + analysis_period
            
            # Analyze response time impact
            response_time_impact = await self._analyze_metric_impact(
                "response_time", baseline_start, baseline_end, analysis_start, analysis_end
            )
            
            # Analyze throughput impact
            throughput_impact = await self._analyze_metric_impact(
                "throughput", baseline_start, baseline_end, analysis_start, analysis_end
            )
            
            # Analyze error rate impact
            error_rate_impact = await self._analyze_metric_impact(
                "error_rate", baseline_start, baseline_end, analysis_start, analysis_end
            )
            
            # Analyze resource usage impact
            resource_impact = {}
            for resource in ["cpu_usage", "memory_usage", "io_usage"]:
                impact = await self._analyze_metric_impact(
                    resource, baseline_start, baseline_end, analysis_start, analysis_end
                )
                if impact is not None:
                    resource_impact[resource] = impact
            
            # Calculate statistical significance
            significance = await self._calculate_statistical_significance(
                "response_time", baseline_start, baseline_end, analysis_start, analysis_end
            )
            
            # Create change impact
            change_impact = CodeChangeImpact(
                change_id=change_id,
                change_type=change_info['change_type'],
                change_description=change_info['description'],
                deployment_time=deployment_time,
                baseline_period=baseline_period,
                analysis_period=analysis_period,
                response_time_impact=response_time_impact or 0.0,
                throughput_impact=throughput_impact or 0.0,
                error_rate_impact=error_rate_impact or 0.0,
                resource_usage_impact=resource_impact,
                statistical_significance=significance,
                confidence_level=0.95
            )
            
            # Determine overall impact
            overall_impact, impact_score = self._calculate_overall_impact(change_impact)
            
            # Generate recommendations
            recommendations = self._generate_impact_recommendations(change_impact, overall_impact)
            
            # Determine if rollback is recommended
            rollback_recommended = (
                overall_impact == ImpactType.NEGATIVE and 
                impact_score < -20  # More than 20% degradation
            )
            
            # Create analysis result
            analysis_result = ImpactAnalysisResult(
                analysis_id=f"impact_{change_id}_{int(datetime.now().timestamp())}",
                change_impact=change_impact,
                overall_impact_type=overall_impact,
                impact_score=impact_score,
                recommendations=recommendations,
                rollback_recommended=rollback_recommended,
                analysis_timestamp=datetime.now(timezone.utc)
            )
            
            # Store result
            self.impact_history.append(analysis_result)
            
            # Maintain history size
            if len(self.impact_history) > 500:
                self.impact_history = self.impact_history[-500:]
            
            # Log results
            if rollback_recommended:
                self.logger.warning(f"Rollback recommended for change {change_id}: {impact_score:.1f}% impact")
            else:
                self.logger.info(f"Impact analysis completed for {change_id}: {impact_score:.1f}% impact")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing change impact: {e}")
            raise ImpactAnalysisError(
                f"Failed to analyze change impact: {e}",
                code_change_id=change_id,
                original_error=e
            )
    
    async def _analyze_metric_impact(
        self,
        metric_name: str,
        baseline_start: datetime,
        baseline_end: datetime,
        analysis_start: datetime,
        analysis_end: datetime
    ) -> Optional[float]:
        """Analyze impact on a specific metric."""
        try:
            # Find matching metrics
            matching_metrics = [
                key for key in self.performance_data.keys()
                if metric_name.lower() in key.lower()
            ]
            
            if not matching_metrics:
                return None
            
            # Use the first matching metric
            metric_key = matching_metrics[0]
            data = list(self.performance_data[metric_key])
            
            # Extract baseline data
            baseline_data = [
                value for timestamp, value in data
                if baseline_start <= timestamp <= baseline_end
            ]
            
            # Extract analysis data
            analysis_data = [
                value for timestamp, value in data
                if analysis_start <= timestamp <= analysis_end
            ]
            
            if len(baseline_data) < 5 or len(analysis_data) < 5:
                return None
            
            # Calculate percentage change
            baseline_mean = statistics.mean(baseline_data)
            analysis_mean = statistics.mean(analysis_data)
            
            if baseline_mean == 0:
                return 0.0
            
            percentage_change = ((analysis_mean - baseline_mean) / baseline_mean) * 100
            return percentage_change
            
        except Exception as e:
            self.logger.error(f"Error analyzing metric impact for {metric_name}: {e}")
            return None
    
    async def _calculate_statistical_significance(
        self,
        metric_name: str,
        baseline_start: datetime,
        baseline_end: datetime,
        analysis_start: datetime,
        analysis_end: datetime
    ) -> float:
        """Calculate statistical significance of the impact."""
        try:
            # Find matching metrics
            matching_metrics = [
                key for key in self.performance_data.keys()
                if metric_name.lower() in key.lower()
            ]
            
            if not matching_metrics:
                return 1.0  # No significance
            
            metric_key = matching_metrics[0]
            data = list(self.performance_data[metric_key])
            
            # Extract data
            baseline_data = [
                value for timestamp, value in data
                if baseline_start <= timestamp <= baseline_end
            ]
            
            analysis_data = [
                value for timestamp, value in data
                if analysis_start <= timestamp <= analysis_end
            ]
            
            if len(baseline_data) < 5 or len(analysis_data) < 5:
                return 1.0
            
            # Perform t-test
            t_stat, p_value = stats.ttest_ind(baseline_data, analysis_data)
            return p_value
            
        except Exception as e:
            self.logger.error(f"Error calculating statistical significance: {e}")
            return 1.0
    
    def _calculate_overall_impact(self, change_impact: CodeChangeImpact) -> Tuple[ImpactType, float]:
        """Calculate overall impact type and score."""
        # Weight different metrics
        weights = {
            'response_time': -0.4,  # Negative because increase is bad
            'throughput': 0.3,      # Positive because increase is good
            'error_rate': -0.3      # Negative because increase is bad
        }
        
        # Calculate weighted impact score
        impact_score = 0.0
        impact_score += change_impact.response_time_impact * weights['response_time']
        impact_score += change_impact.throughput_impact * weights['throughput']
        impact_score += change_impact.error_rate_impact * weights['error_rate']
        
        # Add resource usage impact
        for resource, impact in change_impact.resource_usage_impact.items():
            impact_score += impact * -0.1  # Resource increase is generally bad
        
        # Determine impact type
        if abs(impact_score) < 5:  # Less than 5% change
            impact_type = ImpactType.NEUTRAL
        elif impact_score > 0:
            impact_type = ImpactType.POSITIVE
        else:
            impact_type = ImpactType.NEGATIVE
        
        return impact_type, impact_score
    
    def _generate_impact_recommendations(self, change_impact: CodeChangeImpact, overall_impact: ImpactType) -> List[str]:
        """Generate recommendations based on impact analysis."""
        recommendations = []
        
        if overall_impact == ImpactType.NEGATIVE:
            recommendations.append("Consider rolling back the change if impact is severe")
            
            if change_impact.response_time_impact > 10:
                recommendations.append("Investigate response time degradation")
            
            if change_impact.error_rate_impact > 5:
                recommendations.append("Review error logs for new error patterns")
            
            if any(impact > 20 for impact in change_impact.resource_usage_impact.values()):
                recommendations.append("Monitor resource usage and consider scaling")
        
        elif overall_impact == ImpactType.POSITIVE:
            recommendations.append("Change shows positive performance impact")
            recommendations.append("Consider applying similar optimizations to other services")
        
        else:
            recommendations.append("Change has neutral impact - continue monitoring")
        
        # Add statistical significance note
        if change_impact.statistical_significance > 0.05:
            recommendations.append("Impact may not be statistically significant - continue monitoring")
        
        return recommendations
    
    async def _analysis_loop(self):
        """Background loop for scheduled impact analyses."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                if not self.is_running:
                    break
                
                # Check for pending analyses
                current_time = datetime.now(timezone.utc)
                ready_analyses = []
                
                for change_id, analysis_info in self.pending_analyses.items():
                    if analysis_info['scheduled_time'] <= current_time:
                        ready_analyses.append(change_id)
                
                # Perform ready analyses
                for change_id in ready_analyses:
                    try:
                        await self.analyze_change_impact(change_id)
                        del self.pending_analyses[change_id]
                    except Exception as e:
                        self.logger.error(f"Error in scheduled analysis for {change_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(60)
    
    async def get_impact_history(self, limit: int = 50) -> List[ImpactAnalysisResult]:
        """Get impact analysis history."""
        return self.impact_history[-limit:]
    
    async def get_analyzer_health(self) -> Dict[str, Any]:
        """Get impact analyzer health status."""
        return {
            'is_running': self.is_running,
            'tracked_changes': len(self.tracked_changes),
            'pending_analyses': len(self.pending_analyses),
            'completed_analyses': len(self.impact_history),
            'performance_metrics_tracked': len(self.performance_data)
        }


def create_impact_analyzer(config: OptimizationConfig) -> PerformanceImpactAnalyzer:
    """Create performance impact analyzer instance."""
    return PerformanceImpactAnalyzer(config)
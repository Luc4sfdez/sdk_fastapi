"""
Advanced Optimization Manager for FastAPI Microservices SDK.

This module provides the main manager for advanced performance optimization,
coordinating all optimization components.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
import logging

from .config import OptimizationConfig, OptimizationStrategy
from .exceptions import OptimizationError
from .recommendations import OptimizationRecommendationEngine, create_recommendation_engine
from .impact_analysis import PerformanceImpactAnalyzer, create_impact_analyzer, ChangeType
from .resource_optimizer import ResourceOptimizer, create_resource_optimizer, OptimizationObjective


class AdvancedOptimizationManager:
    """Main manager for advanced performance optimization system."""
    
    def __init__(self, config: OptimizationConfig):
        """Initialize optimization manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.recommendation_engine = create_recommendation_engine(config)
        self.impact_analyzer = create_impact_analyzer(config)
        self.resource_optimizer = create_resource_optimizer(config)
        
        # State management
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Optimization statistics
        self.stats = {
            'recommendations_generated': 0,
            'optimizations_applied': 0,
            'performance_improvements': 0,
            'cost_savings': 0.0
        }
        
        # Callbacks
        self.optimization_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
    
    async def start(self):
        """Start the optimization system."""
        try:
            if self.is_running:
                self.logger.warning("Optimization manager is already running")
                return
            
            self.logger.info("Starting advanced optimization manager...")
            
            # Start all components
            await self.recommendation_engine.start()
            await self.impact_analyzer.start()
            await self.resource_optimizer.start()
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._optimization_coordination_loop()),
                asyncio.create_task(self._performance_monitoring_loop()),
                asyncio.create_task(self._stats_reporting_loop())
            ]
            
            self.is_running = True
            self.logger.info("Advanced optimization manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting optimization manager: {e}")
            raise OptimizationError(
                f"Failed to start optimization manager: {e}",
                optimization_operation="system_start",
                original_error=e
            )
    
    async def stop(self):
        """Stop the optimization system."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping optimization manager...")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Stop all components
            await self.recommendation_engine.stop()
            await self.impact_analyzer.stop()
            await self.resource_optimizer.stop()
            
            self.is_running = False
            self.background_tasks.clear()
            
            self.logger.info("Optimization manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping optimization manager: {e}")
    
    async def record_performance_metric(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Record performance metric across optimization components."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Add to recommendation engine
            await self.recommendation_engine.add_performance_data(metric_name, value, timestamp)
            
            # Add to impact analyzer
            await self.impact_analyzer.record_performance_data(metric_name, value, timestamp)
            
        except Exception as e:
            self.logger.error(f"Error recording performance metric: {e}")
            raise OptimizationError(
                f"Failed to record performance metric: {e}",
                optimization_operation="metric_recording",
                original_error=e
            )
    
    async def record_resource_metric(self, resource_name: str, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Record resource utilization metric."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Add to recommendation engine
            await self.recommendation_engine.add_resource_data(resource_name, metric_type, value, timestamp)
            
        except Exception as e:
            self.logger.error(f"Error recording resource metric: {e}")
            raise OptimizationError(
                f"Failed to record resource metric: {e}",
                optimization_operation="resource_metric_recording",
                original_error=e
            )
    
    async def register_deployment(self, deployment_id: str, description: str, deployment_time: Optional[datetime] = None):
        """Register a deployment for impact analysis."""
        try:
            await self.impact_analyzer.register_change(
                deployment_id,
                ChangeType.CODE_DEPLOYMENT,
                description,
                deployment_time
            )
            
            self.logger.info(f"Registered deployment {deployment_id} for impact analysis")
            
        except Exception as e:
            self.logger.error(f"Error registering deployment: {e}")
            raise OptimizationError(
                f"Failed to register deployment: {e}",
                optimization_operation="deployment_registration",
                original_error=e
            )
    
    async def generate_optimization_recommendations(self):
        """Generate optimization recommendations."""
        try:
            recommendations = await self.recommendation_engine.generate_recommendations()
            self.stats['recommendations_generated'] += len(recommendations)
            
            # Trigger callbacks
            for callback in self.optimization_callbacks:
                try:
                    await callback('recommendations_generated', {
                        'count': len(recommendations),
                        'recommendations': [r.to_dict() for r in recommendations]
                    })
                except Exception as e:
                    self.logger.error(f"Error in optimization callback: {e}")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            raise OptimizationError(
                f"Failed to generate recommendations: {e}",
                optimization_operation="recommendation_generation",
                original_error=e
            )
    
    async def optimize_resources(self, objective: OptimizationObjective = OptimizationObjective.BALANCED):
        """Optimize resource allocation."""
        try:
            optimization_result = await self.resource_optimizer.optimize_resources(objective)
            self.stats['optimizations_applied'] += 1
            
            # Update cost savings if applicable
            if objective in [OptimizationObjective.COST, OptimizationObjective.BALANCED]:
                cost_diff = optimization_result.current_allocation.estimated_cost - optimization_result.optimized_allocation.estimated_cost
                if cost_diff > 0:
                    self.stats['cost_savings'] += cost_diff
            
            # Update performance improvements
            if optimization_result.improvement_percentage > 0:
                self.stats['performance_improvements'] += 1
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"Error optimizing resources: {e}")
            raise OptimizationError(
                f"Failed to optimize resources: {e}",
                optimization_operation="resource_optimization",
                original_error=e
            )
    
    async def analyze_deployment_impact(self, deployment_id: str):
        """Analyze the impact of a specific deployment."""
        try:
            impact_result = await self.impact_analyzer.analyze_change_impact(deployment_id)
            
            # Trigger alerts if rollback is recommended
            if impact_result and impact_result.rollback_recommended:
                for callback in self.alert_callbacks:
                    try:
                        await callback(f"Rollback recommended for deployment {deployment_id}")
                    except Exception as e:
                        self.logger.error(f"Error in alert callback: {e}")
            
            return impact_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing deployment impact: {e}")
            raise OptimizationError(
                f"Failed to analyze deployment impact: {e}",
                optimization_operation="impact_analysis",
                original_error=e
            )
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive optimization summary."""
        try:
            # Get component health
            recommendation_health = await self.recommendation_engine.get_engine_health()
            impact_health = await self.impact_analyzer.get_analyzer_health()
            
            # Get recent data
            active_recommendations = await self.recommendation_engine.get_active_recommendations()
            recent_impacts = await self.impact_analyzer.get_impact_history(limit=10)
            recent_optimizations = await self.resource_optimizer.get_optimization_history(limit=10)
            
            return {
                'system_status': 'healthy' if self.is_running else 'stopped',
                'optimization_strategy': self.config.optimization_strategy.value,
                'statistics': self.stats.copy(),
                'components': {
                    'recommendation_engine': recommendation_health,
                    'impact_analyzer': impact_health,
                    'resource_optimizer': {
                        'is_running': self.resource_optimizer.is_running,
                        'optimizations_completed': len(recent_optimizations)
                    }
                },
                'active_recommendations': len(active_recommendations),
                'recent_impacts': len(recent_impacts),
                'recent_optimizations': len(recent_optimizations)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting optimization summary: {e}")
            return {
                'system_status': 'error',
                'error': str(e)
            }
    
    async def implement_recommendation(self, recommendation_id: str, implementation_result: Dict[str, Any]):
        """Mark a recommendation as implemented."""
        try:
            await self.recommendation_engine.mark_recommendation_implemented(
                recommendation_id, 
                implementation_result
            )
            
            self.logger.info(f"Recommendation {recommendation_id} marked as implemented")
            
        except Exception as e:
            self.logger.error(f"Error implementing recommendation: {e}")
            raise OptimizationError(
                f"Failed to implement recommendation: {e}",
                optimization_operation="recommendation_implementation",
                original_error=e
            )
    
    def add_optimization_callback(self, callback: Callable):
        """Add callback for optimization events."""
        self.optimization_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for optimization alerts."""
        self.alert_callbacks.append(callback)
    
    async def _optimization_coordination_loop(self):
        """Background loop for coordinating optimization activities."""
        while self.is_running:
            try:
                # Coordinate optimization activities every 30 minutes
                await asyncio.sleep(1800)
                
                if not self.is_running:
                    break
                
                # Generate recommendations periodically
                await self.generate_optimization_recommendations()
                
                # Perform resource optimization if strategy allows
                if self.config.optimization_strategy in [OptimizationStrategy.PERFORMANCE_FIRST, OptimizationStrategy.BALANCED]:
                    await self.optimize_resources(OptimizationObjective.BALANCED)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in optimization coordination loop: {e}")
                await asyncio.sleep(300)
    
    async def _performance_monitoring_loop(self):
        """Background loop for performance monitoring."""
        while self.is_running:
            try:
                # Monitor performance every 5 minutes
                await asyncio.sleep(300)
                
                if not self.is_running:
                    break
                
                # Check for performance degradations
                await self._check_performance_degradations()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _stats_reporting_loop(self):
        """Background loop for statistics reporting."""
        while self.is_running:
            try:
                # Report stats every hour
                await asyncio.sleep(3600)
                
                if not self.is_running:
                    break
                
                # Log statistics
                self.logger.info(f"Optimization stats: {self.stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in stats reporting loop: {e}")
                await asyncio.sleep(300)
    
    async def _check_performance_degradations(self):
        """Check for performance degradations that need immediate attention."""
        try:
            # This would implement real-time performance monitoring
            # and trigger immediate optimization if needed
            pass
        except Exception as e:
            self.logger.error(f"Error checking performance degradations: {e}")


def create_optimization_manager(config: OptimizationConfig) -> AdvancedOptimizationManager:
    """Create advanced optimization manager instance."""
    return AdvancedOptimizationManager(config)
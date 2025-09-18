"""
Resource Optimizer for FastAPI Microservices SDK.

This module provides ML-based resource optimization for optimal
performance and cost efficiency.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
from collections import defaultdict, deque

from .config import OptimizationConfig
from .exceptions import ResourceOptimizationError


class OptimizationObjective(str, Enum):
    """Optimization objective enumeration."""
    PERFORMANCE = "performance"
    COST = "cost"
    BALANCED = "balanced"
    RELIABILITY = "reliability"


@dataclass
class ResourceAllocation:
    """Resource allocation specification."""
    cpu_cores: float
    memory_mb: int
    storage_gb: int
    network_mbps: float
    estimated_cost: float
    estimated_performance_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'cpu_cores': self.cpu_cores,
            'memory_mb': self.memory_mb,
            'storage_gb': self.storage_gb,
            'network_mbps': self.network_mbps,
            'estimated_cost': self.estimated_cost,
            'estimated_performance_score': self.estimated_performance_score
        }


@dataclass
class OptimizationResult:
    """Resource optimization result."""
    optimization_id: str
    current_allocation: ResourceAllocation
    optimized_allocation: ResourceAllocation
    optimization_objective: OptimizationObjective
    improvement_percentage: float
    confidence_score: float
    implementation_steps: List[str]
    rollback_plan: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'optimization_id': self.optimization_id,
            'current_allocation': self.current_allocation.to_dict(),
            'optimized_allocation': self.optimized_allocation.to_dict(),
            'optimization_objective': self.optimization_objective.value,
            'improvement_percentage': self.improvement_percentage,
            'confidence_score': self.confidence_score,
            'implementation_steps': self.implementation_steps,
            'rollback_plan': self.rollback_plan,
            'created_at': self.created_at.isoformat()
        }


class ResourceOptimizer:
    """ML-based resource optimizer."""
    
    def __init__(self, config: OptimizationConfig):
        """Initialize resource optimizer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Optimization state
        self.optimization_history: List[OptimizationResult] = []
        self.current_allocation: Optional[ResourceAllocation] = None
        
        # Performance and cost data
        self.performance_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.cost_data: deque = deque(maxlen=1000)
        
        # ML models for optimization
        self.optimization_models: Dict[str, Any] = {}
        
        # Background tasks
        self.is_running = False
        self.optimization_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the resource optimizer."""
        try:
            if self.is_running:
                return
            
            self.logger.info("Starting resource optimizer...")
            
            if self.config.resource_optimization.enabled:
                self.optimization_task = asyncio.create_task(self._optimization_loop())
            
            self.is_running = True
            self.logger.info("Resource optimizer started")
            
        except Exception as e:
            self.logger.error(f"Error starting resource optimizer: {e}")
            raise ResourceOptimizationError(f"Failed to start optimizer: {e}", original_error=e)
    
    async def stop(self):
        """Stop the resource optimizer."""
        try:
            if not self.is_running:
                return
            
            if self.optimization_task:
                self.optimization_task.cancel()
                try:
                    await self.optimization_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("Resource optimizer stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping resource optimizer: {e}")
    
    async def optimize_resources(self, objective: OptimizationObjective = OptimizationObjective.BALANCED) -> OptimizationResult:
        """Optimize resource allocation based on objective."""
        try:
            # Get current resource allocation
            current_allocation = await self._get_current_allocation()
            
            # Generate optimized allocation
            optimized_allocation = await self._generate_optimized_allocation(current_allocation, objective)
            
            # Calculate improvement
            improvement = self._calculate_improvement(current_allocation, optimized_allocation, objective)
            
            # Generate implementation steps
            steps = self._generate_implementation_steps(current_allocation, optimized_allocation)
            
            # Create optimization result
            result = OptimizationResult(
                optimization_id=f"opt_{int(datetime.now().timestamp())}",
                current_allocation=current_allocation,
                optimized_allocation=optimized_allocation,
                optimization_objective=objective,
                improvement_percentage=improvement,
                confidence_score=0.8,  # Would be calculated based on model confidence
                implementation_steps=steps,
                rollback_plan="Revert to previous resource allocation if performance degrades",
                created_at=datetime.now(timezone.utc)
            )
            
            self.optimization_history.append(result)
            
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-100:]
            
            self.logger.info(f"Generated optimization with {improvement:.1f}% improvement")
            return result
            
        except Exception as e:
            self.logger.error(f"Error optimizing resources: {e}")
            raise ResourceOptimizationError(f"Failed to optimize resources: {e}", original_error=e)
    
    async def _get_current_allocation(self) -> ResourceAllocation:
        """Get current resource allocation."""
        # This would typically query the actual infrastructure
        # For now, return a default allocation
        return ResourceAllocation(
            cpu_cores=2.0,
            memory_mb=4096,
            storage_gb=100,
            network_mbps=1000,
            estimated_cost=100.0,
            estimated_performance_score=75.0
        )
    
    async def _generate_optimized_allocation(self, current: ResourceAllocation, objective: OptimizationObjective) -> ResourceAllocation:
        """Generate optimized resource allocation."""
        # Simple optimization logic - would use ML models in practice
        if objective == OptimizationObjective.PERFORMANCE:
            # Increase resources for better performance
            return ResourceAllocation(
                cpu_cores=current.cpu_cores * 1.5,
                memory_mb=int(current.memory_mb * 1.3),
                storage_gb=current.storage_gb,
                network_mbps=current.network_mbps * 1.2,
                estimated_cost=current.estimated_cost * 1.4,
                estimated_performance_score=current.estimated_performance_score * 1.2
            )
        elif objective == OptimizationObjective.COST:
            # Reduce resources for cost savings
            return ResourceAllocation(
                cpu_cores=current.cpu_cores * 0.8,
                memory_mb=int(current.memory_mb * 0.9),
                storage_gb=current.storage_gb,
                network_mbps=current.network_mbps,
                estimated_cost=current.estimated_cost * 0.7,
                estimated_performance_score=current.estimated_performance_score * 0.95
            )
        else:  # BALANCED
            # Optimize for balance
            return ResourceAllocation(
                cpu_cores=current.cpu_cores * 1.1,
                memory_mb=int(current.memory_mb * 1.1),
                storage_gb=current.storage_gb,
                network_mbps=current.network_mbps,
                estimated_cost=current.estimated_cost * 1.1,
                estimated_performance_score=current.estimated_performance_score * 1.1
            )
    
    def _calculate_improvement(self, current: ResourceAllocation, optimized: ResourceAllocation, objective: OptimizationObjective) -> float:
        """Calculate improvement percentage."""
        if objective == OptimizationObjective.PERFORMANCE:
            return ((optimized.estimated_performance_score - current.estimated_performance_score) / current.estimated_performance_score) * 100
        elif objective == OptimizationObjective.COST:
            return ((current.estimated_cost - optimized.estimated_cost) / current.estimated_cost) * 100
        else:  # BALANCED
            perf_improvement = (optimized.estimated_performance_score - current.estimated_performance_score) / current.estimated_performance_score
            cost_improvement = (current.estimated_cost - optimized.estimated_cost) / current.estimated_cost
            return (perf_improvement + cost_improvement) * 50  # Average and scale
    
    def _generate_implementation_steps(self, current: ResourceAllocation, optimized: ResourceAllocation) -> List[str]:
        """Generate implementation steps."""
        steps = []
        
        if optimized.cpu_cores != current.cpu_cores:
            steps.append(f"Adjust CPU allocation from {current.cpu_cores} to {optimized.cpu_cores} cores")
        
        if optimized.memory_mb != current.memory_mb:
            steps.append(f"Adjust memory allocation from {current.memory_mb}MB to {optimized.memory_mb}MB")
        
        if optimized.network_mbps != current.network_mbps:
            steps.append(f"Adjust network bandwidth from {current.network_mbps}Mbps to {optimized.network_mbps}Mbps")
        
        steps.append("Monitor performance metrics after changes")
        steps.append("Validate cost impact")
        
        return steps
    
    async def _optimization_loop(self):
        """Background optimization loop."""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                if not self.is_running:
                    break
                
                # Perform periodic optimization
                await self.optimize_resources()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(300)
    
    async def get_optimization_history(self, limit: int = 50) -> List[OptimizationResult]:
        """Get optimization history."""
        return self.optimization_history[-limit:]


def create_resource_optimizer(config: OptimizationConfig) -> ResourceOptimizer:
    """Create resource optimizer instance."""
    return ResourceOptimizer(config)
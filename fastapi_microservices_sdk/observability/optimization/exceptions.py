"""
Performance optimization exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the performance optimization system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import ObservabilityError


class OptimizationError(ObservabilityError):
    """Base exception for performance optimization related errors."""
    
    def __init__(
        self,
        message: str,
        optimization_operation: Optional[str] = None,
        component: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            observability_operation="performance_optimization",
            original_error=original_error,
            context=context or {}
        )
        self.optimization_operation = optimization_operation
        self.component = component


class RecommendationError(OptimizationError):
    """Exception raised when optimization recommendation operations fail."""
    
    def __init__(
        self,
        message: str,
        recommendation_type: Optional[str] = None,
        optimization_strategy: Optional[str] = None,
        confidence_score: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="recommendation_generation",
            component="recommendation_engine",
            original_error=original_error,
            context={
                'recommendation_type': recommendation_type,
                'optimization_strategy': optimization_strategy,
                'confidence_score': confidence_score
            }
        )
        self.recommendation_type = recommendation_type
        self.optimization_strategy = optimization_strategy
        self.confidence_score = confidence_score


class ImpactAnalysisError(OptimizationError):
    """Exception raised when performance impact analysis operations fail."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        code_change_id: Optional[str] = None,
        baseline_version: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="impact_analysis",
            component="impact_analyzer",
            original_error=original_error,
            context={
                'analysis_type': analysis_type,
                'code_change_id': code_change_id,
                'baseline_version': baseline_version
            }
        )
        self.analysis_type = analysis_type
        self.code_change_id = code_change_id
        self.baseline_version = baseline_version


class ResourceOptimizationError(OptimizationError):
    """Exception raised when resource optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        optimization_algorithm: Optional[str] = None,
        current_allocation: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="resource_optimization",
            component="resource_optimizer",
            original_error=original_error,
            context={
                'resource_type': resource_type,
                'optimization_algorithm': optimization_algorithm,
                'current_allocation': current_allocation
            }
        )
        self.resource_type = resource_type
        self.optimization_algorithm = optimization_algorithm
        self.current_allocation = current_allocation


class PerformanceTestingError(OptimizationError):
    """Exception raised when performance testing operations fail."""
    
    def __init__(
        self,
        message: str,
        testing_tool: Optional[str] = None,
        test_scenario: Optional[str] = None,
        test_duration: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="performance_testing",
            component="performance_testing",
            original_error=original_error,
            context={
                'testing_tool': testing_tool,
                'test_scenario': test_scenario,
                'test_duration': test_duration
            }
        )
        self.testing_tool = testing_tool
        self.test_scenario = test_scenario
        self.test_duration = test_duration


class BudgetEnforcementError(OptimizationError):
    """Exception raised when performance budget enforcement operations fail."""
    
    def __init__(
        self,
        message: str,
        budget_name: Optional[str] = None,
        budget_threshold: Optional[float] = None,
        actual_value: Optional[float] = None,
        enforcement_action: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="budget_enforcement",
            component="budget_manager",
            original_error=original_error,
            context={
                'budget_name': budget_name,
                'budget_threshold': budget_threshold,
                'actual_value': actual_value,
                'enforcement_action': enforcement_action
            }
        )
        self.budget_name = budget_name
        self.budget_threshold = budget_threshold
        self.actual_value = actual_value
        self.enforcement_action = enforcement_action


class AutoScalingError(OptimizationError):
    """Exception raised when auto-scaling operations fail."""
    
    def __init__(
        self,
        message: str,
        scaling_action: Optional[str] = None,
        current_instances: Optional[int] = None,
        target_instances: Optional[int] = None,
        scaling_trigger: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="auto_scaling",
            component="auto_scaler",
            original_error=original_error,
            context={
                'scaling_action': scaling_action,
                'current_instances': current_instances,
                'target_instances': target_instances,
                'scaling_trigger': scaling_trigger
            }
        )
        self.scaling_action = scaling_action
        self.current_instances = current_instances
        self.target_instances = target_instances
        self.scaling_trigger = scaling_trigger


class MLOptimizationError(OptimizationError):
    """Exception raised when ML-based optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        ml_algorithm: Optional[str] = None,
        model_version: Optional[str] = None,
        training_data_size: Optional[int] = None,
        optimization_target: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="ml_optimization",
            component="ml_optimizer",
            original_error=original_error,
            context={
                'ml_algorithm': ml_algorithm,
                'model_version': model_version,
                'training_data_size': training_data_size,
                'optimization_target': optimization_target
            }
        )
        self.ml_algorithm = ml_algorithm
        self.model_version = model_version
        self.training_data_size = training_data_size
        self.optimization_target = optimization_target


class CostOptimizationError(OptimizationError):
    """Exception raised when cost optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        cost_model: Optional[str] = None,
        current_cost: Optional[float] = None,
        target_cost: Optional[float] = None,
        optimization_strategy: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="cost_optimization",
            component="cost_optimizer",
            original_error=original_error,
            context={
                'cost_model': cost_model,
                'current_cost': current_cost,
                'target_cost': target_cost,
                'optimization_strategy': optimization_strategy
            }
        )
        self.cost_model = cost_model
        self.current_cost = current_cost
        self.target_cost = target_cost
        self.optimization_strategy = optimization_strategy


class ConfigurationOptimizationError(OptimizationError):
    """Exception raised when configuration optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        configuration_type: Optional[str] = None,
        parameter_name: Optional[str] = None,
        current_value: Optional[Any] = None,
        suggested_value: Optional[Any] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            optimization_operation="configuration_optimization",
            component="config_optimizer",
            original_error=original_error,
            context={
                'configuration_type': configuration_type,
                'parameter_name': parameter_name,
                'current_value': current_value,
                'suggested_value': suggested_value
            }
        )
        self.configuration_type = configuration_type
        self.parameter_name = parameter_name
        self.current_value = current_value
        self.suggested_value = suggested_value


# Export all exceptions
__all__ = [
    'OptimizationError',
    'RecommendationError',
    'ImpactAnalysisError',
    'ResourceOptimizationError',
    'PerformanceTestingError',
    'BudgetEnforcementError',
    'AutoScalingError',
    'MLOptimizationError',
    'CostOptimizationError',
    'ConfigurationOptimizationError',
]
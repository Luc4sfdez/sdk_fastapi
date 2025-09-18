"""
Performance optimization configuration for FastAPI Microservices SDK.

This module provides configuration classes for the performance optimization
system including recommendations, impact analysis, resource optimization,
and auto-scaling.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import timedelta


class OptimizationStrategy(str, Enum):
    """Optimization strategy enumeration."""
    PERFORMANCE_FIRST = "performance_first"
    COST_FIRST = "cost_first"
    BALANCED = "balanced"
    RESOURCE_EFFICIENT = "resource_efficient"
    LATENCY_OPTIMIZED = "latency_optimized"


class RecommendationType(str, Enum):
    """Recommendation type enumeration."""
    CPU_OPTIMIZATION = "cpu_optimization"
    MEMORY_OPTIMIZATION = "memory_optimization"
    IO_OPTIMIZATION = "io_optimization"
    NETWORK_OPTIMIZATION = "network_optimization"
    DATABASE_OPTIMIZATION = "database_optimization"
    CACHE_OPTIMIZATION = "cache_optimization"
    ALGORITHM_OPTIMIZATION = "algorithm_optimization"
    CONFIGURATION_TUNING = "configuration_tuning"


class ScalingStrategy(str, Enum):
    """Auto-scaling strategy enumeration."""
    REACTIVE = "reactive"
    PREDICTIVE = "predictive"
    HYBRID = "hybrid"
    ML_BASED = "ml_based"


@dataclass
class RecommendationConfig:
    """Optimization recommendation configuration."""
    enabled: bool = True
    
    # Recommendation generation
    min_confidence_threshold: float = 0.7
    max_recommendations_per_analysis: int = 10
    recommendation_refresh_interval: timedelta = field(default_factory=lambda: timedelta(hours=6))
    
    # ML-based recommendations
    use_ml_recommendations: bool = True
    ml_model_retrain_interval: timedelta = field(default_factory=lambda: timedelta(days=7))
    
    # Recommendation types to enable
    enabled_recommendation_types: List[RecommendationType] = field(
        default_factory=lambda: [
            RecommendationType.CPU_OPTIMIZATION,
            RecommendationType.MEMORY_OPTIMIZATION,
            RecommendationType.DATABASE_OPTIMIZATION
        ]
    )
    
    # Impact estimation
    estimate_performance_impact: bool = True
    estimate_cost_impact: bool = True
    estimate_implementation_effort: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'min_confidence_threshold': self.min_confidence_threshold,
            'max_recommendations_per_analysis': self.max_recommendations_per_analysis,
            'recommendation_refresh_interval': self.recommendation_refresh_interval.total_seconds(),
            'use_ml_recommendations': self.use_ml_recommendations,
            'ml_model_retrain_interval': self.ml_model_retrain_interval.total_seconds(),
            'enabled_recommendation_types': [rt.value for rt in self.enabled_recommendation_types],
            'estimate_performance_impact': self.estimate_performance_impact,
            'estimate_cost_impact': self.estimate_cost_impact,
            'estimate_implementation_effort': self.estimate_implementation_effort
        }


@dataclass
class ImpactAnalysisConfig:
    """Performance impact analysis configuration."""
    enabled: bool = True
    
    # Analysis parameters
    baseline_comparison_window: timedelta = field(default_factory=lambda: timedelta(hours=24))
    statistical_significance_threshold: float = 0.05
    min_samples_for_analysis: int = 30
    
    # Impact metrics
    analyze_response_time_impact: bool = True
    analyze_throughput_impact: bool = True
    analyze_resource_usage_impact: bool = True
    analyze_error_rate_impact: bool = True
    
    # Code change tracking
    track_deployment_impact: bool = True
    track_configuration_changes: bool = True
    track_infrastructure_changes: bool = True
    
    # Reporting
    generate_impact_reports: bool = True
    report_generation_interval: timedelta = field(default_factory=lambda: timedelta(hours=12))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'baseline_comparison_window': self.baseline_comparison_window.total_seconds(),
            'statistical_significance_threshold': self.statistical_significance_threshold,
            'min_samples_for_analysis': self.min_samples_for_analysis,
            'analyze_response_time_impact': self.analyze_response_time_impact,
            'analyze_throughput_impact': self.analyze_throughput_impact,
            'analyze_resource_usage_impact': self.analyze_resource_usage_impact,
            'analyze_error_rate_impact': self.analyze_error_rate_impact,
            'track_deployment_impact': self.track_deployment_impact,
            'track_configuration_changes': self.track_configuration_changes,
            'track_infrastructure_changes': self.track_infrastructure_changes,
            'generate_impact_reports': self.generate_impact_reports,
            'report_generation_interval': self.report_generation_interval.total_seconds()
        }


@dataclass
class ResourceOptimizationConfig:
    """Resource optimization configuration."""
    enabled: bool = True
    
    # Optimization algorithms
    optimization_algorithm: str = "genetic_algorithm"  # genetic_algorithm, gradient_descent, bayesian
    optimization_iterations: int = 100
    convergence_threshold: float = 0.01
    
    # Resource constraints
    cpu_min_allocation: float = 0.1  # CPU cores
    cpu_max_allocation: float = 8.0
    memory_min_allocation: int = 128  # MB
    memory_max_allocation: int = 8192
    
    # Optimization targets
    optimize_for_performance: bool = True
    optimize_for_cost: bool = True
    optimize_for_reliability: bool = True
    
    # ML-based optimization
    use_ml_optimization: bool = True
    ml_model_type: str = "reinforcement_learning"
    learning_rate: float = 0.01
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'optimization_algorithm': self.optimization_algorithm,
            'optimization_iterations': self.optimization_iterations,
            'convergence_threshold': self.convergence_threshold,
            'cpu_min_allocation': self.cpu_min_allocation,
            'cpu_max_allocation': self.cpu_max_allocation,
            'memory_min_allocation': self.memory_min_allocation,
            'memory_max_allocation': self.memory_max_allocation,
            'optimize_for_performance': self.optimize_for_performance,
            'optimize_for_cost': self.optimize_for_cost,
            'optimize_for_reliability': self.optimize_for_reliability,
            'use_ml_optimization': self.use_ml_optimization,
            'ml_model_type': self.ml_model_type,
            'learning_rate': self.learning_rate
        }


@dataclass
class PerformanceTestingConfig:
    """Performance testing integration configuration."""
    enabled: bool = True
    
    # Testing tools
    default_testing_tool: str = "locust"  # locust, jmeter, k6, artillery
    testing_tools_config: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'locust': {
            'host': 'localhost',
            'port': 8089,
            'users': 100,
            'spawn_rate': 10
        },
        'k6': {
            'vus': 100,
            'duration': '5m'
        }
    })
    
    # Test scenarios
    default_test_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    ramp_up_duration: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    cool_down_duration: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    
    # Test execution
    parallel_test_execution: bool = True
    max_concurrent_tests: int = 3
    test_result_retention_days: int = 30
    
    # Integration with CI/CD
    run_tests_on_deployment: bool = True
    performance_gate_enabled: bool = True
    performance_gate_threshold: float = 0.1  # 10% performance degradation threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'default_testing_tool': self.default_testing_tool,
            'testing_tools_config': self.testing_tools_config,
            'default_test_duration': self.default_test_duration.total_seconds(),
            'ramp_up_duration': self.ramp_up_duration.total_seconds(),
            'cool_down_duration': self.cool_down_duration.total_seconds(),
            'parallel_test_execution': self.parallel_test_execution,
            'max_concurrent_tests': self.max_concurrent_tests,
            'test_result_retention_days': self.test_result_retention_days,
            'run_tests_on_deployment': self.run_tests_on_deployment,
            'performance_gate_enabled': self.performance_gate_enabled,
            'performance_gate_threshold': self.performance_gate_threshold
        }


@dataclass
class BudgetConfig:
    """Performance budget configuration."""
    enabled: bool = True
    
    # Budget definitions
    default_response_time_budget_ms: float = 1000.0
    default_throughput_budget_rps: float = 100.0
    default_error_rate_budget_percent: float = 1.0
    default_resource_budget_percent: float = 80.0
    
    # Budget enforcement
    enforcement_enabled: bool = True
    enforcement_actions: List[str] = field(default_factory=lambda: [
        "alert", "block_deployment", "auto_scale"
    ])
    
    # Budget monitoring
    monitoring_interval: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    budget_violation_threshold: int = 3  # Consecutive violations before action
    
    # Budget adjustment
    auto_adjust_budgets: bool = True
    budget_adjustment_factor: float = 0.1  # 10% adjustment
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'default_response_time_budget_ms': self.default_response_time_budget_ms,
            'default_throughput_budget_rps': self.default_throughput_budget_rps,
            'default_error_rate_budget_percent': self.default_error_rate_budget_percent,
            'default_resource_budget_percent': self.default_resource_budget_percent,
            'enforcement_enabled': self.enforcement_enabled,
            'enforcement_actions': self.enforcement_actions,
            'monitoring_interval': self.monitoring_interval.total_seconds(),
            'budget_violation_threshold': self.budget_violation_threshold,
            'auto_adjust_budgets': self.auto_adjust_budgets,
            'budget_adjustment_factor': self.budget_adjustment_factor
        }


@dataclass
class AutoScalingConfig:
    """Auto-scaling configuration."""
    enabled: bool = True
    
    # Scaling strategy
    scaling_strategy: ScalingStrategy = ScalingStrategy.HYBRID
    
    # Scaling parameters
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    
    # Scaling behavior
    scale_up_cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    scale_down_cooldown: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    scale_up_step_size: int = 1
    scale_down_step_size: int = 1
    
    # Predictive scaling
    enable_predictive_scaling: bool = True
    prediction_horizon: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    prediction_confidence_threshold: float = 0.8
    
    # ML-based scaling
    use_ml_scaling_decisions: bool = True
    ml_model_retrain_interval: timedelta = field(default_factory=lambda: timedelta(days=1))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'scaling_strategy': self.scaling_strategy.value,
            'min_instances': self.min_instances,
            'max_instances': self.max_instances,
            'target_cpu_utilization': self.target_cpu_utilization,
            'target_memory_utilization': self.target_memory_utilization,
            'scale_up_cooldown': self.scale_up_cooldown.total_seconds(),
            'scale_down_cooldown': self.scale_down_cooldown.total_seconds(),
            'scale_up_step_size': self.scale_up_step_size,
            'scale_down_step_size': self.scale_down_step_size,
            'enable_predictive_scaling': self.enable_predictive_scaling,
            'prediction_horizon': self.prediction_horizon.total_seconds(),
            'prediction_confidence_threshold': self.prediction_confidence_threshold,
            'use_ml_scaling_decisions': self.use_ml_scaling_decisions,
            'ml_model_retrain_interval': self.ml_model_retrain_interval.total_seconds()
        }


class OptimizationConfig(BaseModel):
    """Main optimization configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # Optimization settings
    enabled: bool = Field(True, description="Enable performance optimization")
    optimization_strategy: OptimizationStrategy = Field(
        OptimizationStrategy.BALANCED,
        description="Overall optimization strategy"
    )
    
    # Data collection and analysis
    data_collection_interval: int = Field(60, description="Data collection interval in seconds")
    analysis_window: int = Field(3600, description="Analysis window in seconds")
    
    # Component configurations
    recommendations: RecommendationConfig = Field(
        default_factory=RecommendationConfig,
        description="Recommendation engine configuration"
    )
    
    impact_analysis: ImpactAnalysisConfig = Field(
        default_factory=ImpactAnalysisConfig,
        description="Impact analysis configuration"
    )
    
    resource_optimization: ResourceOptimizationConfig = Field(
        default_factory=ResourceOptimizationConfig,
        description="Resource optimization configuration"
    )
    
    performance_testing: PerformanceTestingConfig = Field(
        default_factory=PerformanceTestingConfig,
        description="Performance testing configuration"
    )
    
    budget_management: BudgetConfig = Field(
        default_factory=BudgetConfig,
        description="Performance budget configuration"
    )
    
    auto_scaling: AutoScalingConfig = Field(
        default_factory=AutoScalingConfig,
        description="Auto-scaling configuration"
    )
    
    # Advanced settings
    enable_experimental_features: bool = Field(False, description="Enable experimental features")
    optimization_aggressiveness: float = Field(0.5, description="Optimization aggressiveness (0.0-1.0)")
    
    @validator('optimization_aggressiveness')
    def validate_aggressiveness(cls, v):
        """Validate optimization aggressiveness."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Optimization aggressiveness must be between 0.0 and 1.0')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_name': self.service_name,
            'service_version': self.service_version,
            'environment': self.environment,
            'enabled': self.enabled,
            'optimization_strategy': self.optimization_strategy.value,
            'data_collection_interval': self.data_collection_interval,
            'analysis_window': self.analysis_window,
            'recommendations': self.recommendations.to_dict(),
            'impact_analysis': self.impact_analysis.to_dict(),
            'resource_optimization': self.resource_optimization.to_dict(),
            'performance_testing': self.performance_testing.to_dict(),
            'budget_management': self.budget_management.to_dict(),
            'auto_scaling': self.auto_scaling.to_dict(),
            'enable_experimental_features': self.enable_experimental_features,
            'optimization_aggressiveness': self.optimization_aggressiveness
        }


def create_optimization_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> OptimizationConfig:
    """Create optimization configuration with defaults."""
    return OptimizationConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


# Export configuration classes
__all__ = [
    'OptimizationStrategy',
    'RecommendationType',
    'ScalingStrategy',
    'RecommendationConfig',
    'ImpactAnalysisConfig',
    'ResourceOptimizationConfig',
    'PerformanceTestingConfig',
    'BudgetConfig',
    'AutoScalingConfig',
    'OptimizationConfig',
    'create_optimization_config',
]
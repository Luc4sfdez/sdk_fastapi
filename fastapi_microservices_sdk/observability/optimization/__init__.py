"""
Advanced Performance Optimization Module for FastAPI Microservices SDK.

This module provides advanced performance optimization capabilities including
automatic optimization recommendations, performance impact analysis, ML-based
resource optimization, performance testing integration, performance budgets,
and auto-scaling mechanisms.

Features:
- Automatic performance optimization recommendations
- Performance impact analysis for code changes
- Resource utilization optimization with ML insights
- Performance testing integration with load testing tools
- Performance budgets with enforcement mechanisms
- Performance-based auto-scaling and resource allocation
- ML-driven optimization strategies
- Real-time performance optimization

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    OptimizationError,
    RecommendationError,
    ImpactAnalysisError,
    ResourceOptimizationError,
    PerformanceTestingError,
    BudgetEnforcementError,
    AutoScalingError
)

from .config import (
    OptimizationConfig,
    RecommendationConfig,
    ImpactAnalysisConfig,
    ResourceOptimizationConfig,
    PerformanceTestingConfig,
    BudgetConfig,
    AutoScalingConfig,
    create_optimization_config
)

from .recommendations import (
    OptimizationRecommendationEngine,
    PerformanceRecommendation,
    RecommendationType,
    OptimizationStrategy,
    create_recommendation_engine
)

from .impact_analysis import (
    PerformanceImpactAnalyzer,
    ImpactAnalysisResult,
    CodeChangeImpact,
    create_impact_analyzer
)

from .resource_optimizer import (
    ResourceOptimizer,
    OptimizationResult,
    ResourceAllocation,
    create_resource_optimizer
)

from .performance_testing import (
    PerformanceTestingIntegration,
    LoadTestResult,
    TestScenario,
    create_performance_testing
)

from .budget_manager import (
    PerformanceBudgetManager,
    PerformanceBudget,
    BudgetViolation,
    create_budget_manager
)

from .auto_scaler import (
    PerformanceAutoScaler,
    ScalingDecision,
    ScalingMetrics,
    create_auto_scaler
)

from .manager import (
    AdvancedOptimizationManager,
    create_optimization_manager
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'OptimizationError',
    'RecommendationError',
    'ImpactAnalysisError',
    'ResourceOptimizationError',
    'PerformanceTestingError',
    'BudgetEnforcementError',
    'AutoScalingError',
    
    # Configuration
    'OptimizationConfig',
    'RecommendationConfig',
    'ImpactAnalysisConfig',
    'ResourceOptimizationConfig',
    'PerformanceTestingConfig',
    'BudgetConfig',
    'AutoScalingConfig',
    'create_optimization_config',
    
    # Optimization Recommendations
    'OptimizationRecommendationEngine',
    'PerformanceRecommendation',
    'RecommendationType',
    'OptimizationStrategy',
    'create_recommendation_engine',
    
    # Impact Analysis
    'PerformanceImpactAnalyzer',
    'ImpactAnalysisResult',
    'CodeChangeImpact',
    'create_impact_analyzer',
    
    # Resource Optimization
    'ResourceOptimizer',
    'OptimizationResult',
    'ResourceAllocation',
    'create_resource_optimizer',
    
    # Performance Testing
    'PerformanceTestingIntegration',
    'LoadTestResult',
    'TestScenario',
    'create_performance_testing',
    
    # Budget Management
    'PerformanceBudgetManager',
    'PerformanceBudget',
    'BudgetViolation',
    'create_budget_manager',
    
    # Auto Scaling
    'PerformanceAutoScaler',
    'ScalingDecision',
    'ScalingMetrics',
    'create_auto_scaler',
    
    # Optimization Manager
    'AdvancedOptimizationManager',
    'create_optimization_manager',
]


def get_optimization_info() -> dict:
    """Get information about optimization capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Automatic Performance Optimization',
            'ML-based Resource Optimization',
            'Performance Impact Analysis',
            'Load Testing Integration',
            'Performance Budget Management',
            'Auto-scaling and Resource Allocation',
            'Real-time Optimization Recommendations',
            'Performance Regression Prevention',
            'Cost Optimization',
            'Capacity Planning Integration'
        ],
        'optimization_strategies': [
            'cpu_optimization',
            'memory_optimization',
            'io_optimization',
            'network_optimization',
            'database_optimization',
            'cache_optimization',
            'algorithm_optimization',
            'resource_allocation'
        ],
        'ml_techniques': [
            'reinforcement_learning',
            'genetic_algorithms',
            'gradient_descent',
            'bayesian_optimization',
            'neural_networks',
            'ensemble_methods'
        ],
        'testing_integrations': [
            'locust',
            'jmeter',
            'k6',
            'artillery',
            'wrk',
            'custom_tools'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Advanced Performance Optimization module loaded")
logger.info("Features: Auto-optimization, ML insights, Performance budgets, Auto-scaling")
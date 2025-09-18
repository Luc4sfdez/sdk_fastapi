"""
Application Performance Monitoring (APM) Module for FastAPI Microservices SDK.

This module provides comprehensive APM capabilities including performance profiling,
baseline establishment, SLA monitoring, bottleneck identification, trend analysis,
and regression detection for enterprise microservices.

Features:
- Automatic performance profiling and monitoring
- Performance baseline establishment and drift detection
- SLA monitoring with violation detection and reporting
- Performance bottleneck identification and recommendations
- Performance trend analysis with capacity planning insights
- Performance regression detection in CI/CD pipelines
- Real-time performance metrics collection and analysis
- Performance optimization recommendations

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    APMError,
    ProfilingError,
    BaselineError,
    SLAViolationError,
    BottleneckDetectionError,
    RegressionDetectionError
)

from .config import (
    APMConfig,
    ProfilingConfig,
    BaselineConfig,
    SLAConfig,
    BottleneckConfig,
    RegressionConfig,
    create_apm_config
)

from .profiler import (
    PerformanceProfiler,
    ProfileResult,
    ProfileMetrics,
    create_performance_profiler
)

from .baseline import (
    BaselineManager,
    PerformanceBaseline,
    BaselineDrift,
    create_baseline_manager
)

from .sla import (
    SLAMonitor,
    SLADefinition,
    SLAViolation,
    SLAReport,
    create_sla_monitor
)

from .bottleneck import (
    BottleneckDetector,
    BottleneckAnalysis,
    PerformanceRecommendation,
    create_bottleneck_detector
)

from .trends import (
    TrendAnalyzer,
    PerformanceTrend,
    CapacityInsight,
    create_trend_analyzer
)

from .regression import (
    RegressionDetector,
    PerformanceRegression,
    RegressionReport,
    create_regression_detector
)

from .manager import (
    APMManager,
    create_apm_manager
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'APMError',
    'ProfilingError',
    'BaselineError',
    'SLAViolationError',
    'BottleneckDetectionError',
    'RegressionDetectionError',
    
    # Configuration
    'APMConfig',
    'ProfilingConfig',
    'BaselineConfig',
    'SLAConfig',
    'BottleneckConfig',
    'RegressionConfig',
    'create_apm_config',
    
    # Performance Profiler
    'PerformanceProfiler',
    'ProfileResult',
    'ProfileMetrics',
    'create_performance_profiler',
    
    # Baseline Management
    'BaselineManager',
    'PerformanceBaseline',
    'BaselineDrift',
    'create_baseline_manager',
    
    # SLA Monitoring
    'SLAMonitor',
    'SLADefinition',
    'SLAViolation',
    'SLAReport',
    'create_sla_monitor',
    
    # Bottleneck Detection
    'BottleneckDetector',
    'BottleneckAnalysis',
    'PerformanceRecommendation',
    'create_bottleneck_detector',
    
    # Trend Analysis
    'TrendAnalyzer',
    'PerformanceTrend',
    'CapacityInsight',
    'create_trend_analyzer',
    
    # Regression Detection
    'RegressionDetector',
    'PerformanceRegression',
    'RegressionReport',
    'create_regression_detector',
    
    # APM Manager
    'APMManager',
    'create_apm_manager',
]


def get_apm_info() -> dict:
    """Get information about APM capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Automatic Performance Profiling',
            'Performance Baseline Management',
            'SLA Monitoring and Violation Detection',
            'Bottleneck Identification and Analysis',
            'Performance Trend Analysis',
            'Capacity Planning Insights',
            'Regression Detection in CI/CD',
            'Real-time Performance Monitoring',
            'Performance Optimization Recommendations',
            'Performance Budget Management'
        ],
        'profiling_types': [
            'cpu_profiling',
            'memory_profiling',
            'io_profiling',
            'network_profiling',
            'database_profiling',
            'custom_profiling'
        ],
        'sla_metrics': [
            'response_time',
            'throughput',
            'error_rate',
            'availability',
            'resource_utilization',
            'custom_metrics'
        ],
        'analysis_capabilities': [
            'bottleneck_detection',
            'trend_analysis',
            'capacity_planning',
            'regression_detection',
            'performance_optimization',
            'anomaly_detection'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK APM module loaded")
logger.info("Features: Performance Profiling, SLA Monitoring, Bottleneck Detection")
"""
Health Monitoring Module for FastAPI Microservices SDK.

This module provides comprehensive health monitoring capabilities including
Kubernetes probes, dependency health checking, circuit breaker integration,
and health status aggregation for enterprise microservices.

Features:
- Kubernetes readiness and liveness probes
- Dependency health checking with circuit breakers
- Health check registry with automatic discovery
- Health status aggregation and reporting
- Health check timeouts and failure handling
- Integration with observability systems

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    HealthCheckError,
    HealthTimeoutError,
    DependencyHealthError,
    ProbeConfigurationError,
    CircuitBreakerError,
    HealthRegistryError
)

from .config import (
    HealthConfig,
    ProbeConfig,
    DependencyConfig,
    HealthStatus,
    ProbeType,
    DependencyType,
    create_health_config,
    create_database_dependency,
    create_cache_dependency,
    create_api_dependency
)

from .monitor import (
    HealthCheckResult,
    SystemInfo,
    HealthMonitor,
    create_health_monitor
)

from .probes import (
    ProbeStatus,
    ProbeResult,
    KubernetesProbe,
    ReadinessProbe,
    LivenessProbe,
    StartupProbe,
    ProbeManager,
    create_kubernetes_probes
)

from .dependencies import (
    CircuitState,
    CircuitBreakerStats,
    CircuitBreaker,
    DependencyHealth,
    DependencyChecker,
    create_dependency_checker
)

from .registry import (
    HealthCheckCategory,
    HealthCheckInfo,
    HealthCheckRegistry,
    create_health_registry
)

from .endpoints import (
    HealthEndpoints,
    create_health_endpoints
)

# Advanced Analytics (Task 5.2)
from .analytics import (
    # Advanced Analytics Components
    HealthAnalyzer,
    HealthPredictor,
    CapacityPlanner,
    AnomalyPredictor,
    DashboardGenerator,
    SLAMonitor,
    # Analytics Configuration
    AnalyticsConfig,
    TrendConfig,
    PredictionConfig,
    ReportConfig,
    create_analytics_config,
    create_health_analyzer,
    create_health_predictor,
    create_health_reporter,
    # Analytics Data Types
    HealthDataPoint,
    TrendAnalysis,
    PredictionResult,
    CapacityForecast,
    AnomalyPrediction,
    HealthReport,
    SLAMetrics,
    DashboardData,
    # Analytics Enums
    TrendType,
    TrendDirection,
    PredictionModel,
    PredictionHorizon,
    ReportType,
    ReportFormat,
    ReportPeriod
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'HealthCheckError',
    'HealthTimeoutError',
    'DependencyHealthError',
    'ProbeConfigurationError',
    'CircuitBreakerError',
    'HealthRegistryError',
    
    # Configuration
    'HealthConfig',
    'ProbeConfig',
    'DependencyConfig',
    'HealthStatus',
    'ProbeType',
    'DependencyType',
    'create_health_config',
    'create_database_dependency',
    'create_cache_dependency',
    'create_api_dependency',
    
    # Core Health Monitoring
    'HealthCheckResult',
    'SystemInfo',
    'HealthMonitor',
    'create_health_monitor',
    
    # Kubernetes Probes
    'ProbeStatus',
    'ProbeResult',
    'KubernetesProbe',
    'ReadinessProbe',
    'LivenessProbe',
    'StartupProbe',
    'ProbeManager',
    'create_kubernetes_probes',
    
    # Dependency Health
    'CircuitState',
    'CircuitBreakerStats',
    'CircuitBreaker',
    'DependencyHealth',
    'DependencyChecker',
    'create_dependency_checker',
    
    # Health Registry
    'HealthCheckCategory',
    'HealthCheckInfo',
    'HealthCheckRegistry',
    'create_health_registry',
    
    # Health Endpoints
    'HealthEndpoints',
    'create_health_endpoints',
    
    # Advanced Analytics (Task 5.2)
    'HealthAnalyzer',
    'HealthPredictor',
    'CapacityPlanner',
    'AnomalyPredictor',
    'DashboardGenerator',
    'SLAMonitor',
    'AnalyticsConfig',
    'TrendConfig',
    'PredictionConfig',
    'ReportConfig',
    'create_analytics_config',
    'create_health_analyzer',
    'create_health_predictor',
    'create_health_reporter',
    'HealthDataPoint',
    'TrendAnalysis',
    'PredictionResult',
    'CapacityForecast',
    'AnomalyPrediction',
    'HealthReport',
    'SLAMetrics',
    'DashboardData',
    'TrendType',
    'TrendDirection',
    'PredictionModel',
    'PredictionHorizon',
    'ReportType',
    'ReportFormat',
    'ReportPeriod',
]


def get_health_info() -> dict:
    """Get information about health monitoring capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Kubernetes Readiness Probes',
            'Kubernetes Liveness Probes',
            'Kubernetes Startup Probes',
            'Dependency Health Checking',
            'Circuit Breaker Integration',
            'Health Check Registry',
            'Health Status Aggregation',
            'Timeout and Failure Handling',
            'Real-time Health Monitoring',
            'Health Metrics Collection',
            # Advanced Analytics (Task 5.2)
            'Advanced Health Trend Analysis',
            'Predictive Health Monitoring',
            'Capacity Planning and Auto-scaling',
            'Anomaly Detection and Prediction',
            'Real-time Health Dashboards',
            'SLA Monitoring and Compliance',
            'Health Report Generation',
            'Performance Correlation Analysis'
        ],
        'probe_types': [
            'readiness',
            'liveness',
            'startup'
        ],
        'dependency_types': [
            'database',
            'cache',
            'message_queue',
            'external_api',
            'file_system',
            'network'
        ],
        'health_statuses': [
            'healthy',
            'unhealthy',
            'degraded',
            'unknown'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Health Monitoring module loaded")
logger.info("Features: Kubernetes Probes, Dependency Health, Circuit Breakers")
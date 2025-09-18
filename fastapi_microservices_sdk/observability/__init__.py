"""
Observability Module for FastAPI Microservices SDK.

This module provides comprehensive observability capabilities including
metrics collection, distributed tracing, structured logging, health monitoring,
and intelligent alerting for enterprise-grade microservices.

Features:
- Prometheus metrics collection and export
- OpenTelemetry distributed tracing with Jaeger integration
- Structured logging with ELK stack integration
- Kubernetes-native health checks and probes
- Intelligent alerting with multiple notification channels
- Performance analytics and APM capabilities
- Cloud platform integrations (AWS, GCP, Azure)
- Security and compliance features

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .config import (
    ObservabilityConfig,
    MetricsConfig,
    TracingConfig,
    LoggingConfig,
    HealthConfig,
    AlertConfig,
    MetricType,
    SamplingStrategy,
    LogLevel,
    HealthState,
    AlertSeverity
)

from .manager import (
    ObservabilityManager,
    ComponentRegistry,
    ComponentStatus,
    ComponentType,
    ComponentInfo,
    ObservabilityComponent,
    create_observability_manager,
    initialize_observability
)

# Advanced manager components (Task 1.2)
try:
    from .advanced_manager import (
        AdvancedObservabilityManager,
        AdvancedComponentRegistry,
        ConfigurationManager,
        IntegrationManager,
        PerformanceMetrics,
        ComponentHealthHistory,
        create_advanced_observability_manager,
        initialize_advanced_observability
    )
    ADVANCED_MANAGER_AVAILABLE = True
except ImportError:
    ADVANCED_MANAGER_AVAILABLE = False

from .exceptions import (
    ObservabilityError,
    MetricsError,
    TracingError,
    LoggingError,
    HealthCheckError,
    AlertingError,
    ConfigurationError as ObservabilityConfigurationError
)

# Optional imports with graceful fallback
try:
    from .metrics import (
        MetricsCollector,
        PrometheusExporter,
        Counter,
        Gauge,
        Histogram,
        Summary,
        MetricRegistry
    )
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Tracing temporarily disabled for stability
TRACING_AVAILABLE = False
# try:
#     from .tracing import (
#         TracingSystem,
#         Tracer,
#         Span,
#         SpanContext,
#         TraceSampler,
#         JaegerExporter
#     )
#     TRACING_AVAILABLE = True
# except ImportError:
#     TRACING_AVAILABLE = False

try:
    from .logging import (
        StructuredLogger,
        LogFormatter,
        LogShipper,
        AuditLogger,
        ELKIntegration
    )
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

try:
    from .health import (
        HealthMonitor,
        HealthCheck,
        HealthStatus,
        ReadinessProbe,
        LivenessProbe,
        DependencyCheck
    )
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False

try:
    from .alerting import (
        AlertManager,
        AlertRule,
        Alert,
        NotificationChannel,
        EscalationPolicy,
        AlertProcessor
    )
    ALERTING_AVAILABLE = True
except ImportError:
    ALERTING_AVAILABLE = False

try:
    from .analytics import (
        PerformanceAnalyzer,
        APMCollector,
        SLAMonitor,
        BottleneckDetector,
        CapacityPlanner
    )
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from .dashboards import (
        DashboardManager,
        GrafanaIntegration,
        DashboardTemplate,
        VisualizationEngine
    )
    DASHBOARDS_AVAILABLE = True
except ImportError:
    DASHBOARDS_AVAILABLE = False

try:
    from .integrations import (
        CloudIntegration,
        KubernetesIntegration,
        ServiceMeshIntegration,
        PrometheusIntegration
    )
    INTEGRATIONS_AVAILABLE = True
except ImportError:
    INTEGRATIONS_AVAILABLE = False

# Version and availability information
__version__ = "1.0.0"
__author__ = "FastAPI Microservices SDK"

__all__ = [
    # Core configuration
    'ObservabilityConfig',
    'MetricsConfig',
    'TracingConfig',
    'LoggingConfig',
    'HealthConfig',
    'AlertConfig',
    'MetricType',
    'SamplingStrategy',
    'LogLevel',
    'HealthState',
    'AlertSeverity',
    
    # Core manager
    'ObservabilityManager',
    'ComponentRegistry',
    'ComponentStatus',
    'ComponentType',
    'ComponentInfo',
    'ObservabilityComponent',
    'create_observability_manager',
    'initialize_observability',
    
    # Core exceptions
    'ObservabilityError',
    'MetricsError',
    'TracingError',
    'LoggingError',
    'HealthCheckError',
    'AlertingError',
    'ObservabilityConfigurationError',
    
    # Availability flags
    'METRICS_AVAILABLE',
    'TRACING_AVAILABLE',
    'LOGGING_AVAILABLE',
    'HEALTH_AVAILABLE',
    'ALERTING_AVAILABLE',
    'ANALYTICS_AVAILABLE',
    'DASHBOARDS_AVAILABLE',
    'INTEGRATIONS_AVAILABLE',
    
    # Version info
    '__version__',
    '__author__'
]

# Conditional exports based on availability
if METRICS_AVAILABLE:
    __all__.extend([
        'MetricsCollector',
        'PrometheusExporter',
        'Counter',
        'Gauge',
        'Histogram',
        'Summary',
        'MetricRegistry'
    ])

if TRACING_AVAILABLE:
    __all__.extend([
        'TracingSystem',
        'Tracer',
        'Span',
        'SpanContext',
        'TraceSampler',
        'JaegerExporter'
    ])

if LOGGING_AVAILABLE:
    __all__.extend([
        'StructuredLogger',
        'LogFormatter',
        'LogShipper',
        'AuditLogger',
        'ELKIntegration'
    ])

if HEALTH_AVAILABLE:
    __all__.extend([
        'HealthMonitor',
        'HealthCheck',
        'HealthStatus',
        'ReadinessProbe',
        'LivenessProbe',
        'DependencyCheck'
    ])

if ALERTING_AVAILABLE:
    __all__.extend([
        'AlertManager',
        'AlertRule',
        'Alert',
        'NotificationChannel',
        'EscalationPolicy',
        'AlertProcessor'
    ])

if ANALYTICS_AVAILABLE:
    __all__.extend([
        'PerformanceAnalyzer',
        'APMCollector',
        'SLAMonitor',
        'BottleneckDetector',
        'CapacityPlanner'
    ])

if DASHBOARDS_AVAILABLE:
    __all__.extend([
        'DashboardManager',
        'GrafanaIntegration',
        'DashboardTemplate',
        'VisualizationEngine'
    ])

if INTEGRATIONS_AVAILABLE:
    __all__.extend([
        'CloudIntegration',
        'KubernetesIntegration',
        'ServiceMeshIntegration',
        'PrometheusIntegration'
    ])


def check_observability_dependencies():
    """Check if all required observability dependencies are available."""
    missing_deps = []
    
    # Check core observability libraries
    try:
        import prometheus_client
    except ImportError:
        missing_deps.append('prometheus-client (metrics)')
    
    try:
        import opentelemetry
    except ImportError:
        missing_deps.append('opentelemetry-api (tracing)')
    
    try:
        import jaeger_client
    except ImportError:
        missing_deps.append('jaeger-client (tracing backend)')
    
    try:
        import elasticsearch
    except ImportError:
        missing_deps.append('elasticsearch (logging backend)')
    
    try:
        import grafana_api
    except ImportError:
        missing_deps.append('grafana-api (dashboards)')
    
    # Check optional cloud integrations
    try:
        import boto3
    except ImportError:
        missing_deps.append('boto3 (AWS integration - optional)')
    
    try:
        import google.cloud.monitoring
    except ImportError:
        missing_deps.append('google-cloud-monitoring (GCP integration - optional)')
    
    return missing_deps


def get_observability_status():
    """Get the status of observability dependencies and features."""
    missing_deps = check_observability_dependencies()
    
    return {
        'metrics_available': METRICS_AVAILABLE,
        'tracing_available': TRACING_AVAILABLE,
        'logging_available': LOGGING_AVAILABLE,
        'health_available': HEALTH_AVAILABLE,
        'alerting_available': ALERTING_AVAILABLE,
        'analytics_available': ANALYTICS_AVAILABLE,
        'dashboards_available': DASHBOARDS_AVAILABLE,
        'integrations_available': INTEGRATIONS_AVAILABLE,
        'all_dependencies_available': len(missing_deps) == 0,
        'missing_dependencies': missing_deps,
        'version': __version__
    }


# Initialize logging for observability module
import logging
logger = logging.getLogger(__name__)
logger.info(f"FastAPI Microservices SDK Observability Module v{__version__} initialized")

# Log availability status
status = get_observability_status()
if status['all_dependencies_available']:
    logger.info("All observability dependencies are available")
else:
    logger.warning(f"Missing observability dependencies: {', '.join(status['missing_dependencies'])}")
    logger.info("Some observability features may not be available")

# Log feature availability
available_features = []
if METRICS_AVAILABLE:
    available_features.append("Metrics Collection")
if TRACING_AVAILABLE:
    available_features.append("Distributed Tracing")
if LOGGING_AVAILABLE:
    available_features.append("Structured Logging")
if HEALTH_AVAILABLE:
    available_features.append("Health Monitoring")
if ALERTING_AVAILABLE:
    available_features.append("Intelligent Alerting")
if ANALYTICS_AVAILABLE:
    available_features.append("Performance Analytics")

if available_features:
    logger.info(f"Available features: {', '.join(available_features)}")
else:
    logger.warning("No advanced observability features available - only core configuration loaded")
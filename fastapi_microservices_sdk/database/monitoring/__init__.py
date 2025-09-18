"""
Database Monitoring System for FastAPI Microservices SDK.

This module provides comprehensive database monitoring, analytics,
and performance analysis capabilities for all supported database engines.

Features:
- Real-time metrics collection
- Performance trend analysis
- Query optimization recommendations
- Resource utilization monitoring
- Anomaly detection
- Health assessments
- Alerting and notifications
- Integration with monitoring platforms

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .config import (
    MonitoringConfig,
    MonitoringLevel,
    MetricsStorage,
    AlertChannel
)
from .metrics import (
    MetricsCollector,
    DatabaseMetrics,
    MetricValue,
    MetricType
)
from .analytics import (
    DatabaseAnalytics,
    AnalyticsFinding,
    PerformanceTrend,
    QueryOptimizationSuggestion,
    ResourceUtilizationAnalysis,
    AnalysisType,
    Severity,
    TrendDirection
)
from .exceptions import (
    MonitoringError,
    MetricsCollectionError,
    AnalyticsError,
    AlertingError,
    ConfigurationError,
    StorageError
)

__all__ = [
    # Configuration
    "MonitoringConfig",
    "MonitoringLevel",
    "MetricsStorage",
    "AlertChannel",
    
    # Metrics
    "MetricsCollector",
    "DatabaseMetrics",
    "MetricValue",
    "MetricType",
    
    # Analytics
    "DatabaseAnalytics",
    "AnalyticsFinding",
    "PerformanceTrend",
    "QueryOptimizationSuggestion",
    "ResourceUtilizationAnalysis",
    "AnalysisType",
    "Severity",
    "TrendDirection",
    
    # Exceptions
    "MonitoringError",
    "MetricsCollectionError",
    "AnalyticsError",
    "AlertingError",
    "ConfigurationError",
    "StorageError",
]
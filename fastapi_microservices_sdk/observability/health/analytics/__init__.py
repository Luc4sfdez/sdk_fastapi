"""
Advanced Health Analytics Module for FastAPI Microservices SDK.

This module provides comprehensive health analytics capabilities including
trend analysis, predictive health monitoring, capacity planning,
and advanced reporting for enterprise microservices.

Features:
- Health trend analysis and pattern recognition
- Predictive health monitoring with ML integration
- Capacity planning and resource optimization
- Advanced health dashboards and visualization
- Health anomaly detection and alerting
- Performance correlation analysis
- Health SLA monitoring and reporting
- Custom health metrics and KPIs

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    HealthAnalyticsError,
    TrendAnalysisError,
    PredictionError,
    ReportGenerationError
)

from .config import (
    AnalyticsConfig,
    TrendConfig,
    PredictionConfig,
    ReportConfig,
    create_analytics_config
)

from .analyzer import (
    HealthAnalyzer,
    TrendAnalyzer,
    PatternDetector,
    create_health_analyzer
)

from .predictor import (
    HealthPredictor,
    CapacityPlanner,
    AnomalyPredictor,
    create_health_predictor
)

from .reporter import (
    HealthReporter,
    DashboardGenerator,
    SLAMonitor,
    create_health_reporter
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'HealthAnalyticsError',
    'TrendAnalysisError',
    'PredictionError',
    'ReportGenerationError',
    
    # Configuration
    'AnalyticsConfig',
    'TrendConfig',
    'PredictionConfig',
    'ReportConfig',
    'create_analytics_config',
    
    # Health Analysis
    'HealthAnalyzer',
    'TrendAnalyzer',
    'PatternDetector',
    'create_health_analyzer',
    
    # Health Prediction
    'HealthPredictor',
    'CapacityPlanner',
    'AnomalyPredictor',
    'create_health_predictor',
    
    # Health Reporting
    'HealthReporter',
    'DashboardGenerator',
    'SLAMonitor',
    'create_health_reporter',
]
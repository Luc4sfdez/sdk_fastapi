"""
Intelligent Alerting and Machine Learning Module for FastAPI Microservices SDK.

This module provides intelligent alerting capabilities including adaptive thresholds,
anomaly detection, alert fatigue reduction, predictive alerting, and ML-based
optimization for enterprise microservices.

Features:
- Adaptive alerting with machine learning-based thresholds
- Anomaly detection for metrics and logs using ML algorithms
- Alert fatigue reduction with intelligent filtering
- Predictive alerting based on trend analysis
- Alert effectiveness analysis and optimization
- Maintenance window management with automatic suppression
- ML model training and validation for alerting

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    IntelligentAlertingError,
    MLModelError,
    AnomalyDetectionError,
    ThresholdAdaptationError,
    AlertOptimizationError
)

from .config import (
    IntelligentAlertingConfig,
    MLModelConfig,
    AnomalyDetectionConfig,
    AdaptiveThresholdConfig,
    AlertOptimizationConfig,
    create_intelligent_alerting_config
)

from .adaptive_thresholds import (
    AdaptiveThresholdManager,
    ThresholdModel,
    ThresholdAdaptationStrategy,
    create_adaptive_threshold_manager
)

from .anomaly_detection import (
    AnomalyDetector,
    AnomalyModel,
    AnomalyType,
    AnomalyResult,
    create_anomaly_detector
)

from .ml_models import (
    MLModelManager,
    AlertingMLModel,
    ModelType,
    ModelTrainingResult,
    create_ml_model_manager
)

from .alert_optimization import (
    AlertOptimizer,
    AlertEffectivenessAnalyzer,
    OptimizationRecommendation,
    create_alert_optimizer
)

from .predictive_alerting import (
    PredictiveAlerter,
    PredictiveModel,
    PredictionResult,
    create_predictive_alerter
)

from .fatigue_reduction import (
    AlertFatigueReducer,
    FatigueAnalyzer,
    FilteringStrategy,
    create_fatigue_reducer
)

from .maintenance_windows import (
    MaintenanceWindowManager,
    MaintenanceWindow,
    SuppressionRule,
    create_maintenance_manager
)

from .intelligent_manager import (
    IntelligentAlertManager,
    create_intelligent_alert_manager
)

# Export all main classes and functions
__all__ = [
    # Exceptions
    'IntelligentAlertingError',
    'MLModelError',
    'AnomalyDetectionError',
    'ThresholdAdaptationError',
    'AlertOptimizationError',
    
    # Configuration
    'IntelligentAlertingConfig',
    'MLModelConfig',
    'AnomalyDetectionConfig',
    'AdaptiveThresholdConfig',
    'AlertOptimizationConfig',
    'create_intelligent_alerting_config',
    
    # Adaptive Thresholds
    'AdaptiveThresholdManager',
    'ThresholdModel',
    'ThresholdAdaptationStrategy',
    'create_adaptive_threshold_manager',
    
    # Anomaly Detection
    'AnomalyDetector',
    'AnomalyModel',
    'AnomalyType',
    'AnomalyResult',
    'create_anomaly_detector',
    
    # ML Models
    'MLModelManager',
    'AlertingMLModel',
    'ModelType',
    'ModelTrainingResult',
    'create_ml_model_manager',
    
    # Alert Optimization
    'AlertOptimizer',
    'AlertEffectivenessAnalyzer',
    'OptimizationRecommendation',
    'create_alert_optimizer',
    
    # Predictive Alerting
    'PredictiveAlerter',
    'PredictiveModel',
    'PredictionResult',
    'create_predictive_alerter',
    
    # Fatigue Reduction
    'AlertFatigueReducer',
    'FatigueAnalyzer',
    'FilteringStrategy',
    'create_fatigue_reducer',
    
    # Maintenance Windows
    'MaintenanceWindowManager',
    'MaintenanceWindow',
    'SuppressionRule',
    'create_maintenance_manager',
    
    # Intelligent Manager
    'IntelligentAlertManager',
    'create_intelligent_alert_manager',
]


def get_intelligent_alerting_info() -> dict:
    """Get information about intelligent alerting capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Adaptive ML-based Thresholds',
            'Anomaly Detection for Metrics and Logs',
            'Alert Fatigue Reduction',
            'Predictive Alerting',
            'Alert Effectiveness Analysis',
            'Maintenance Window Management',
            'ML Model Training and Validation',
            'Intelligent Alert Filtering',
            'Threshold Auto-adaptation',
            'Alert Storm Prevention'
        ],
        'ml_algorithms': [
            'isolation_forest',
            'one_class_svm',
            'local_outlier_factor',
            'statistical_outlier',
            'lstm_autoencoder',
            'gaussian_mixture',
            'dbscan_clustering'
        ],
        'adaptation_strategies': [
            'statistical_based',
            'ml_based',
            'hybrid',
            'time_series_based',
            'seasonal_aware'
        ],
        'optimization_metrics': [
            'alert_precision',
            'alert_recall',
            'false_positive_rate',
            'mean_time_to_acknowledge',
            'alert_volume_reduction',
            'effectiveness_score'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Intelligent Alerting module loaded")
logger.info("Features: Adaptive Thresholds, Anomaly Detection, ML Optimization")
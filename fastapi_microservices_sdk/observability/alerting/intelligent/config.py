"""
Intelligent alerting configuration for FastAPI Microservices SDK.

This module provides configuration classes for intelligent alerting,
ML models, anomaly detection, and adaptive thresholds.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import timedelta


class MLAlgorithm(str, Enum):
    """Machine learning algorithm types."""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"
    STATISTICAL_OUTLIER = "statistical_outlier"
    LSTM_AUTOENCODER = "lstm_autoencoder"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    DBSCAN_CLUSTERING = "dbscan_clustering"


class AdaptationStrategy(str, Enum):
    """Threshold adaptation strategy."""
    STATISTICAL_BASED = "statistical_based"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"
    TIME_SERIES_BASED = "time_series_based"
    SEASONAL_AWARE = "seasonal_aware"


class OptimizationMetric(str, Enum):
    """Alert optimization metrics."""
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    MEAN_TIME_TO_ACKNOWLEDGE = "mean_time_to_acknowledge"
    ALERT_VOLUME_REDUCTION = "alert_volume_reduction"
    EFFECTIVENESS_SCORE = "effectiveness_score"


class FilteringStrategy(str, Enum):
    """Alert filtering strategies."""
    FREQUENCY_BASED = "frequency_based"
    SIMILARITY_BASED = "similarity_based"
    IMPORTANCE_BASED = "importance_based"
    ML_BASED = "ml_based"
    HYBRID = "hybrid"


@dataclass
class MLModelConfig:
    """ML model configuration."""
    algorithm: MLAlgorithm
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    training_window_days: int = 7
    retrain_interval_hours: int = 24
    validation_split: float = 0.2
    cross_validation_folds: int = 5
    feature_selection: bool = True
    auto_hyperparameter_tuning: bool = True
    model_persistence: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'algorithm': self.algorithm.value,
            'hyperparameters': self.hyperparameters,
            'training_window_days': self.training_window_days,
            'retrain_interval_hours': self.retrain_interval_hours,
            'validation_split': self.validation_split,
            'cross_validation_folds': self.cross_validation_folds,
            'feature_selection': self.feature_selection,
            'auto_hyperparameter_tuning': self.auto_hyperparameter_tuning,
            'model_persistence': self.model_persistence
        }


@dataclass
class AnomalyDetectionConfig:
    """Anomaly detection configuration."""
    enabled: bool = True
    algorithms: List[MLAlgorithm] = field(default_factory=lambda: [
        MLAlgorithm.ISOLATION_FOREST,
        MLAlgorithm.STATISTICAL_OUTLIER
    ])
    contamination_rate: float = 0.1  # Expected proportion of anomalies
    sensitivity: float = 0.8  # Detection sensitivity
    ensemble_voting: str = "soft"  # soft or hard voting
    min_samples_for_training: int = 100
    anomaly_score_threshold: float = 0.5
    temporal_correlation: bool = True
    seasonal_adjustment: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'algorithms': [alg.value for alg in self.algorithms],
            'contamination_rate': self.contamination_rate,
            'sensitivity': self.sensitivity,
            'ensemble_voting': self.ensemble_voting,
            'min_samples_for_training': self.min_samples_for_training,
            'anomaly_score_threshold': self.anomaly_score_threshold,
            'temporal_correlation': self.temporal_correlation,
            'seasonal_adjustment': self.seasonal_adjustment
        }


@dataclass
class AdaptiveThresholdConfig:
    """Adaptive threshold configuration."""
    enabled: bool = True
    adaptation_strategy: AdaptationStrategy = AdaptationStrategy.HYBRID
    adaptation_interval_hours: int = 6
    min_data_points: int = 50
    confidence_level: float = 0.95
    adaptation_rate: float = 0.1  # How quickly to adapt (0-1)
    stability_period_hours: int = 24  # Period to wait before adapting again
    max_threshold_change: float = 0.5  # Maximum change per adaptation (0-1)
    seasonal_awareness: bool = True
    trend_awareness: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'adaptation_strategy': self.adaptation_strategy.value,
            'adaptation_interval_hours': self.adaptation_interval_hours,
            'min_data_points': self.min_data_points,
            'confidence_level': self.confidence_level,
            'adaptation_rate': self.adaptation_rate,
            'stability_period_hours': self.stability_period_hours,
            'max_threshold_change': self.max_threshold_change,
            'seasonal_awareness': self.seasonal_awareness,
            'trend_awareness': self.trend_awareness
        }


@dataclass
class AlertOptimizationConfig:
    """Alert optimization configuration."""
    enabled: bool = True
    optimization_metrics: List[OptimizationMetric] = field(default_factory=lambda: [
        OptimizationMetric.PRECISION,
        OptimizationMetric.RECALL,
        OptimizationMetric.FALSE_POSITIVE_RATE
    ])
    optimization_interval_hours: int = 24
    min_alerts_for_analysis: int = 100
    effectiveness_threshold: float = 0.7
    auto_optimization: bool = True
    optimization_history_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'optimization_metrics': [metric.value for metric in self.optimization_metrics],
            'optimization_interval_hours': self.optimization_interval_hours,
            'min_alerts_for_analysis': self.min_alerts_for_analysis,
            'effectiveness_threshold': self.effectiveness_threshold,
            'auto_optimization': self.auto_optimization,
            'optimization_history_days': self.optimization_history_days
        }


class IntelligentAlertingConfig(BaseModel):
    """Intelligent alerting system configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # Intelligent alerting settings
    enabled: bool = Field(True, description="Enable intelligent alerting")
    ml_enabled: bool = Field(True, description="Enable machine learning features")
    
    # Data settings
    data_collection_interval: int = Field(60, description="Data collection interval in seconds")
    data_retention_days: int = Field(30, description="Data retention period in days")
    feature_engineering_enabled: bool = Field(True, description="Enable automatic feature engineering")
    
    # ML model configuration
    ml_model_config: MLModelConfig = Field(
        default_factory=MLModelConfig,
        description="ML model configuration"
    )
    
    # Anomaly detection configuration
    anomaly_detection_config: AnomalyDetectionConfig = Field(
        default_factory=AnomalyDetectionConfig,
        description="Anomaly detection configuration"
    )
    
    # Adaptive threshold configuration
    adaptive_threshold_config: AdaptiveThresholdConfig = Field(
        default_factory=AdaptiveThresholdConfig,
        description="Adaptive threshold configuration"
    )
    
    # Alert optimization configuration
    alert_optimization_config: AlertOptimizationConfig = Field(
        default_factory=AlertOptimizationConfig,
        description="Alert optimization configuration"
    )
    
    # Predictive alerting settings
    predictive_alerting_enabled: bool = Field(True, description="Enable predictive alerting")
    prediction_horizon_hours: int = Field(24, description="Prediction horizon in hours")
    prediction_confidence_threshold: float = Field(0.8, description="Minimum prediction confidence")
    
    # Alert fatigue reduction settings
    fatigue_reduction_enabled: bool = Field(True, description="Enable alert fatigue reduction")
    fatigue_threshold: float = Field(0.7, description="Fatigue threshold (0-1)")
    filtering_strategies: List[FilteringStrategy] = Field(
        default_factory=lambda: [FilteringStrategy.FREQUENCY_BASED, FilteringStrategy.SIMILARITY_BASED],
        description="Alert filtering strategies"
    )
    
    # Maintenance window settings
    maintenance_windows_enabled: bool = Field(True, description="Enable maintenance windows")
    auto_suppression_enabled: bool = Field(True, description="Enable automatic suppression")
    suppression_buffer_minutes: int = Field(15, description="Suppression buffer in minutes")
    
    # Performance settings
    max_concurrent_ml_operations: int = Field(5, description="Maximum concurrent ML operations")
    model_cache_enabled: bool = Field(True, description="Enable model caching")
    model_cache_ttl_hours: int = Field(24, description="Model cache TTL in hours")
    
    # Storage settings
    model_storage_backend: str = Field("file", description="Model storage backend (file, database, s3)")
    model_storage_path: Optional[str] = Field(None, description="Model storage path")
    
    # Monitoring settings
    performance_monitoring_enabled: bool = Field(True, description="Enable performance monitoring")
    model_drift_detection_enabled: bool = Field(True, description="Enable model drift detection")
    drift_detection_threshold: float = Field(0.1, description="Model drift threshold")
    
    # Security settings
    model_encryption_enabled: bool = Field(False, description="Enable model encryption")
    access_control_enabled: bool = Field(False, description="Enable access control for ML features")
    
    @validator('data_collection_interval')
    def validate_collection_interval(cls, v):
        """Validate data collection interval."""
        if v <= 0:
            raise ValueError('data_collection_interval must be positive')
        return v
    
    @validator('data_retention_days')
    def validate_retention_days(cls, v):
        """Validate data retention days."""
        if v <= 0:
            raise ValueError('data_retention_days must be positive')
        return v
    
    @validator('prediction_confidence_threshold')
    def validate_confidence_threshold(cls, v):
        """Validate prediction confidence threshold."""
        if not 0 <= v <= 1:
            raise ValueError('prediction_confidence_threshold must be between 0 and 1')
        return v
    
    @validator('fatigue_threshold')
    def validate_fatigue_threshold(cls, v):
        """Validate fatigue threshold."""
        if not 0 <= v <= 1:
            raise ValueError('fatigue_threshold must be between 0 and 1')
        return v
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Get ML configuration."""
        return {
            'enabled': self.ml_enabled,
            'model_config': self.ml_model_config.to_dict(),
            'anomaly_detection': self.anomaly_detection_config.to_dict(),
            'adaptive_thresholds': self.adaptive_threshold_config.to_dict(),
            'optimization': self.alert_optimization_config.to_dict()
        }
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        config = {
            'backend': self.model_storage_backend,
            'retention_days': self.data_retention_days,
            'cache_enabled': self.model_cache_enabled,
            'cache_ttl_hours': self.model_cache_ttl_hours
        }
        
        if self.model_storage_backend == 'file' and self.model_storage_path:
            config['path'] = self.model_storage_path
        
        return config
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return {
            'max_concurrent_operations': self.max_concurrent_ml_operations,
            'monitoring_enabled': self.performance_monitoring_enabled,
            'drift_detection_enabled': self.model_drift_detection_enabled,
            'drift_threshold': self.drift_detection_threshold
        }
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


def create_intelligent_alerting_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> IntelligentAlertingConfig:
    """Create intelligent alerting configuration with defaults."""
    return IntelligentAlertingConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


def create_ml_model_config(
    algorithm: MLAlgorithm,
    **kwargs
) -> MLModelConfig:
    """Create ML model configuration."""
    return MLModelConfig(
        algorithm=algorithm,
        **kwargs
    )


def create_anomaly_detection_config(
    algorithms: Optional[List[MLAlgorithm]] = None,
    **kwargs
) -> AnomalyDetectionConfig:
    """Create anomaly detection configuration."""
    if algorithms is None:
        algorithms = [MLAlgorithm.ISOLATION_FOREST, MLAlgorithm.STATISTICAL_OUTLIER]
    
    return AnomalyDetectionConfig(
        algorithms=algorithms,
        **kwargs
    )


def create_adaptive_threshold_config(
    strategy: AdaptationStrategy = AdaptationStrategy.HYBRID,
    **kwargs
) -> AdaptiveThresholdConfig:
    """Create adaptive threshold configuration."""
    return AdaptiveThresholdConfig(
        adaptation_strategy=strategy,
        **kwargs
    )


def create_alert_optimization_config(
    metrics: Optional[List[OptimizationMetric]] = None,
    **kwargs
) -> AlertOptimizationConfig:
    """Create alert optimization configuration."""
    if metrics is None:
        metrics = [
            OptimizationMetric.PRECISION,
            OptimizationMetric.RECALL,
            OptimizationMetric.FALSE_POSITIVE_RATE
        ]
    
    return AlertOptimizationConfig(
        optimization_metrics=metrics,
        **kwargs
    )


# Default hyperparameters for different algorithms
DEFAULT_HYPERPARAMETERS = {
    MLAlgorithm.ISOLATION_FOREST: {
        'n_estimators': 100,
        'contamination': 0.1,
        'random_state': 42
    },
    MLAlgorithm.ONE_CLASS_SVM: {
        'kernel': 'rbf',
        'gamma': 'scale',
        'nu': 0.1
    },
    MLAlgorithm.LOCAL_OUTLIER_FACTOR: {
        'n_neighbors': 20,
        'contamination': 0.1,
        'algorithm': 'auto'
    },
    MLAlgorithm.STATISTICAL_OUTLIER: {
        'method': 'iqr',
        'threshold': 1.5,
        'window_size': 100
    },
    MLAlgorithm.GAUSSIAN_MIXTURE: {
        'n_components': 2,
        'covariance_type': 'full',
        'random_state': 42
    },
    MLAlgorithm.DBSCAN_CLUSTERING: {
        'eps': 0.5,
        'min_samples': 5,
        'algorithm': 'auto'
    }
}


def get_default_hyperparameters(algorithm: MLAlgorithm) -> Dict[str, Any]:
    """Get default hyperparameters for algorithm."""
    return DEFAULT_HYPERPARAMETERS.get(algorithm, {})


# Export main classes and functions
__all__ = [
    'MLAlgorithm',
    'AdaptationStrategy',
    'OptimizationMetric',
    'FilteringStrategy',
    'MLModelConfig',
    'AnomalyDetectionConfig',
    'AdaptiveThresholdConfig',
    'AlertOptimizationConfig',
    'IntelligentAlertingConfig',
    'create_intelligent_alerting_config',
    'create_ml_model_config',
    'create_anomaly_detection_config',
    'create_adaptive_threshold_config',
    'create_alert_optimization_config',
    'get_default_hyperparameters',
]
"""
Intelligent alerting exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the intelligent alerting system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import AlertingError


class IntelligentAlertingError(AlertingError):
    """Base exception for intelligent alerting related errors."""
    
    def __init__(
        self,
        message: str,
        intelligent_operation: Optional[str] = None,
        model_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            alert_operation="intelligent_alerting",
            original_error=original_error,
            context=context or {}
        )
        self.intelligent_operation = intelligent_operation
        self.model_name = model_name


class MLModelError(IntelligentAlertingError):
    """Exception raised when ML model operations fail."""
    
    def __init__(
        self,
        message: str,
        model_type: Optional[str] = None,
        model_version: Optional[str] = None,
        training_data_size: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="ml_model",
            original_error=original_error,
            context={
                'model_type': model_type,
                'model_version': model_version,
                'training_data_size': training_data_size
            }
        )
        self.model_type = model_type
        self.model_version = model_version
        self.training_data_size = training_data_size


class AnomalyDetectionError(IntelligentAlertingError):
    """Exception raised when anomaly detection operations fail."""
    
    def __init__(
        self,
        message: str,
        detection_algorithm: Optional[str] = None,
        data_points_count: Optional[int] = None,
        anomaly_threshold: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="anomaly_detection",
            original_error=original_error,
            context={
                'detection_algorithm': detection_algorithm,
                'data_points_count': data_points_count,
                'anomaly_threshold': anomaly_threshold
            }
        )
        self.detection_algorithm = detection_algorithm
        self.data_points_count = data_points_count
        self.anomaly_threshold = anomaly_threshold


class ThresholdAdaptationError(IntelligentAlertingError):
    """Exception raised when threshold adaptation operations fail."""
    
    def __init__(
        self,
        message: str,
        adaptation_strategy: Optional[str] = None,
        current_threshold: Optional[float] = None,
        proposed_threshold: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="threshold_adaptation",
            original_error=original_error,
            context={
                'adaptation_strategy': adaptation_strategy,
                'current_threshold': current_threshold,
                'proposed_threshold': proposed_threshold
            }
        )
        self.adaptation_strategy = adaptation_strategy
        self.current_threshold = current_threshold
        self.proposed_threshold = proposed_threshold


class AlertOptimizationError(IntelligentAlertingError):
    """Exception raised when alert optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        optimization_metric: Optional[str] = None,
        optimization_target: Optional[float] = None,
        current_performance: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="alert_optimization",
            original_error=original_error,
            context={
                'optimization_metric': optimization_metric,
                'optimization_target': optimization_target,
                'current_performance': current_performance
            }
        )
        self.optimization_metric = optimization_metric
        self.optimization_target = optimization_target
        self.current_performance = current_performance


class PredictiveAlertingError(IntelligentAlertingError):
    """Exception raised when predictive alerting operations fail."""
    
    def __init__(
        self,
        message: str,
        prediction_horizon: Optional[str] = None,
        prediction_confidence: Optional[float] = None,
        model_accuracy: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="predictive_alerting",
            original_error=original_error,
            context={
                'prediction_horizon': prediction_horizon,
                'prediction_confidence': prediction_confidence,
                'model_accuracy': model_accuracy
            }
        )
        self.prediction_horizon = prediction_horizon
        self.prediction_confidence = prediction_confidence
        self.model_accuracy = model_accuracy


class FatigueReductionError(IntelligentAlertingError):
    """Exception raised when alert fatigue reduction operations fail."""
    
    def __init__(
        self,
        message: str,
        filtering_strategy: Optional[str] = None,
        alert_volume_before: Optional[int] = None,
        alert_volume_after: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="fatigue_reduction",
            original_error=original_error,
            context={
                'filtering_strategy': filtering_strategy,
                'alert_volume_before': alert_volume_before,
                'alert_volume_after': alert_volume_after
            }
        )
        self.filtering_strategy = filtering_strategy
        self.alert_volume_before = alert_volume_before
        self.alert_volume_after = alert_volume_after


class MaintenanceWindowError(IntelligentAlertingError):
    """Exception raised when maintenance window operations fail."""
    
    def __init__(
        self,
        message: str,
        window_id: Optional[str] = None,
        window_type: Optional[str] = None,
        suppression_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="maintenance_window",
            original_error=original_error,
            context={
                'window_id': window_id,
                'window_type': window_type,
                'suppression_count': suppression_count
            }
        )
        self.window_id = window_id
        self.window_type = window_type
        self.suppression_count = suppression_count


class ModelTrainingError(IntelligentAlertingError):
    """Exception raised when ML model training fails."""
    
    def __init__(
        self,
        message: str,
        model_algorithm: Optional[str] = None,
        training_duration: Optional[float] = None,
        validation_score: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="model_training",
            original_error=original_error,
            context={
                'model_algorithm': model_algorithm,
                'training_duration': training_duration,
                'validation_score': validation_score
            }
        )
        self.model_algorithm = model_algorithm
        self.training_duration = training_duration
        self.validation_score = validation_score


class DataPreprocessingError(IntelligentAlertingError):
    """Exception raised when data preprocessing fails."""
    
    def __init__(
        self,
        message: str,
        preprocessing_step: Optional[str] = None,
        input_data_size: Optional[int] = None,
        output_data_size: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            intelligent_operation="data_preprocessing",
            original_error=original_error,
            context={
                'preprocessing_step': preprocessing_step,
                'input_data_size': input_data_size,
                'output_data_size': output_data_size
            }
        )
        self.preprocessing_step = preprocessing_step
        self.input_data_size = input_data_size
        self.output_data_size = output_data_size


# Export all exceptions
__all__ = [
    'IntelligentAlertingError',
    'MLModelError',
    'AnomalyDetectionError',
    'ThresholdAdaptationError',
    'AlertOptimizationError',
    'PredictiveAlertingError',
    'FatigueReductionError',
    'MaintenanceWindowError',
    'ModelTrainingError',
    'DataPreprocessingError',
]
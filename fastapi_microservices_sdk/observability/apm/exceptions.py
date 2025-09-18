"""
APM exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the APM system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import ObservabilityError


class APMError(ObservabilityError):
    """Base exception for APM related errors."""
    
    def __init__(
        self,
        message: str,
        apm_operation: Optional[str] = None,
        component: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            observability_operation="apm",
            original_error=original_error,
            context=context or {}
        )
        self.apm_operation = apm_operation
        self.component = component


class ProfilingError(APMError):
    """Exception raised when performance profiling operations fail."""
    
    def __init__(
        self,
        message: str,
        profiler_type: Optional[str] = None,
        profile_duration: Optional[float] = None,
        target_function: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="profiling",
            component="profiler",
            original_error=original_error,
            context={
                'profiler_type': profiler_type,
                'profile_duration': profile_duration,
                'target_function': target_function
            }
        )
        self.profiler_type = profiler_type
        self.profile_duration = profile_duration
        self.target_function = target_function


class BaselineError(APMError):
    """Exception raised when baseline operations fail."""
    
    def __init__(
        self,
        message: str,
        baseline_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        baseline_period: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="baseline_management",
            component="baseline_manager",
            original_error=original_error,
            context={
                'baseline_type': baseline_type,
                'metric_name': metric_name,
                'baseline_period': baseline_period
            }
        )
        self.baseline_type = baseline_type
        self.metric_name = metric_name
        self.baseline_period = baseline_period


class SLAViolationError(APMError):
    """Exception raised when SLA violations are detected."""
    
    def __init__(
        self,
        message: str,
        sla_name: Optional[str] = None,
        violation_type: Optional[str] = None,
        threshold_value: Optional[float] = None,
        actual_value: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="sla_monitoring",
            component="sla_monitor",
            original_error=original_error,
            context={
                'sla_name': sla_name,
                'violation_type': violation_type,
                'threshold_value': threshold_value,
                'actual_value': actual_value
            }
        )
        self.sla_name = sla_name
        self.violation_type = violation_type
        self.threshold_value = threshold_value
        self.actual_value = actual_value


class BottleneckDetectionError(APMError):
    """Exception raised when bottleneck detection operations fail."""
    
    def __init__(
        self,
        message: str,
        detection_method: Optional[str] = None,
        analysis_scope: Optional[str] = None,
        resource_type: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="bottleneck_detection",
            component="bottleneck_detector",
            original_error=original_error,
            context={
                'detection_method': detection_method,
                'analysis_scope': analysis_scope,
                'resource_type': resource_type
            }
        )
        self.detection_method = detection_method
        self.analysis_scope = analysis_scope
        self.resource_type = resource_type


class TrendAnalysisError(APMError):
    """Exception raised when trend analysis operations fail."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        time_window: Optional[str] = None,
        metric_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="trend_analysis",
            component="trend_analyzer",
            original_error=original_error,
            context={
                'analysis_type': analysis_type,
                'time_window': time_window,
                'metric_count': metric_count
            }
        )
        self.analysis_type = analysis_type
        self.time_window = time_window
        self.metric_count = metric_count


class RegressionDetectionError(APMError):
    """Exception raised when regression detection operations fail."""
    
    def __init__(
        self,
        message: str,
        detection_algorithm: Optional[str] = None,
        baseline_version: Optional[str] = None,
        current_version: Optional[str] = None,
        regression_threshold: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="regression_detection",
            component="regression_detector",
            original_error=original_error,
            context={
                'detection_algorithm': detection_algorithm,
                'baseline_version': baseline_version,
                'current_version': current_version,
                'regression_threshold': regression_threshold
            }
        )
        self.detection_algorithm = detection_algorithm
        self.baseline_version = baseline_version
        self.current_version = current_version
        self.regression_threshold = regression_threshold


class CapacityPlanningError(APMError):
    """Exception raised when capacity planning operations fail."""
    
    def __init__(
        self,
        message: str,
        planning_horizon: Optional[str] = None,
        resource_type: Optional[str] = None,
        prediction_model: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="capacity_planning",
            component="capacity_planner",
            original_error=original_error,
            context={
                'planning_horizon': planning_horizon,
                'resource_type': resource_type,
                'prediction_model': prediction_model
            }
        )
        self.planning_horizon = planning_horizon
        self.resource_type = resource_type
        self.prediction_model = prediction_model


class PerformanceOptimizationError(APMError):
    """Exception raised when performance optimization operations fail."""
    
    def __init__(
        self,
        message: str,
        optimization_type: Optional[str] = None,
        target_metric: Optional[str] = None,
        optimization_strategy: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="performance_optimization",
            component="optimizer",
            original_error=original_error,
            context={
                'optimization_type': optimization_type,
                'target_metric': target_metric,
                'optimization_strategy': optimization_strategy
            }
        )
        self.optimization_type = optimization_type
        self.target_metric = target_metric
        self.optimization_strategy = optimization_strategy


class MetricsCollectionError(APMError):
    """Exception raised when metrics collection operations fail."""
    
    def __init__(
        self,
        message: str,
        collector_type: Optional[str] = None,
        metric_name: Optional[str] = None,
        collection_interval: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="metrics_collection",
            component="metrics_collector",
            original_error=original_error,
            context={
                'collector_type': collector_type,
                'metric_name': metric_name,
                'collection_interval': collection_interval
            }
        )
        self.collector_type = collector_type
        self.metric_name = metric_name
        self.collection_interval = collection_interval


class ReportGenerationError(APMError):
    """Exception raised when report generation operations fail."""
    
    def __init__(
        self,
        message: str,
        report_type: Optional[str] = None,
        report_format: Optional[str] = None,
        data_range: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            apm_operation="report_generation",
            component="report_generator",
            original_error=original_error,
            context={
                'report_type': report_type,
                'report_format': report_format,
                'data_range': data_range
            }
        )
        self.report_type = report_type
        self.report_format = report_format
        self.data_range = data_range


# Export all exceptions
__all__ = [
    'APMError',
    'ProfilingError',
    'BaselineError',
    'SLAViolationError',
    'BottleneckDetectionError',
    'TrendAnalysisError',
    'RegressionDetectionError',
    'CapacityPlanningError',
    'PerformanceOptimizationError',
    'MetricsCollectionError',
    'ReportGenerationError',
]
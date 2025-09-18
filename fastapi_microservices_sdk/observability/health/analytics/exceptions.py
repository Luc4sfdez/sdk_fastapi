"""
Health analytics exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the health analytics system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import HealthCheckError


class HealthAnalyticsError(HealthCheckError):
    """Base exception for health analytics related errors."""
    
    def __init__(
        self,
        message: str,
        analytics_operation: Optional[str] = None,
        data_source: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            check_type="analytics",
            original_error=original_error,
            context=context or {}
        )
        self.analytics_operation = analytics_operation
        self.data_source = data_source


class TrendAnalysisError(HealthAnalyticsError):
    """Exception raised when trend analysis operations fail."""
    
    def __init__(
        self,
        message: str,
        trend_type: Optional[str] = None,
        time_period: Optional[str] = None,
        data_points: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            analytics_operation="trend_analysis",
            original_error=original_error,
            context={
                'trend_type': trend_type,
                'time_period': time_period,
                'data_points': data_points
            }
        )
        self.trend_type = trend_type
        self.time_period = time_period
        self.data_points = data_points


class PredictionError(HealthAnalyticsError):
    """Exception raised when health prediction operations fail."""
    
    def __init__(
        self,
        message: str,
        prediction_model: Optional[str] = None,
        prediction_horizon: Optional[str] = None,
        confidence_level: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            analytics_operation="prediction",
            original_error=original_error,
            context={
                'prediction_model': prediction_model,
                'prediction_horizon': prediction_horizon,
                'confidence_level': confidence_level
            }
        )
        self.prediction_model = prediction_model
        self.prediction_horizon = prediction_horizon
        self.confidence_level = confidence_level


class ReportGenerationError(HealthAnalyticsError):
    """Exception raised when report generation fails."""
    
    def __init__(
        self,
        message: str,
        report_type: Optional[str] = None,
        report_format: Optional[str] = None,
        template_name: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            analytics_operation="report_generation",
            original_error=original_error,
            context={
                'report_type': report_type,
                'report_format': report_format,
                'template_name': template_name
            }
        )
        self.report_type = report_type
        self.report_format = report_format
        self.template_name = template_name


# Export all exceptions
__all__ = [
    'HealthAnalyticsError',
    'TrendAnalysisError',
    'PredictionError',
    'ReportGenerationError',
]
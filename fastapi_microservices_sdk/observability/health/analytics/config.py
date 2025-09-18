"""
Health analytics configuration for FastAPI Microservices SDK.

This module provides configuration classes for health analytics,
trend analysis, prediction models, and reporting systems.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator


class TrendType(str, Enum):
    """Trend analysis type enumeration."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    SEASONAL = "seasonal"
    POLYNOMIAL = "polynomial"
    MOVING_AVERAGE = "moving_average"


class PredictionModel(str, Enum):
    """Prediction model type enumeration."""
    LINEAR_REGRESSION = "linear_regression"
    TIME_SERIES = "time_series"
    ARIMA = "arima"
    PROPHET = "prophet"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    MARKDOWN = "markdown"


@dataclass
class TrendConfig:
    """Trend analysis configuration."""
    enabled: bool = True
    trend_types: List[TrendType] = field(default_factory=lambda: [TrendType.LINEAR, TrendType.MOVING_AVERAGE])
    analysis_window_hours: int = 24
    data_points_minimum: int = 10
    confidence_threshold: float = 0.8
    seasonal_period: int = 24  # hours
    smoothing_factor: float = 0.3
    outlier_detection: bool = True
    outlier_threshold: float = 2.0  # standard deviations


@dataclass
class PredictionConfig:
    """Prediction model configuration."""
    enabled: bool = True
    models: List[PredictionModel] = field(default_factory=lambda: [PredictionModel.LINEAR_REGRESSION, PredictionModel.TIME_SERIES])
    prediction_horizon_hours: int = 24
    training_window_days: int = 7
    retrain_interval_hours: int = 24
    confidence_intervals: List[float] = field(default_factory=lambda: [0.8, 0.95])
    cross_validation_folds: int = 5


@dataclass
class ReportConfig:
    """Report generation configuration."""
    enabled: bool = True
    formats: List[ReportFormat] = field(default_factory=lambda: [ReportFormat.HTML, ReportFormat.JSON])
    generation_schedule: str = "0 6 * * *"  # Daily at 6 AM
    retention_days: int = 30
    template_directory: Optional[str] = None
    output_directory: str = "reports"
    include_charts: bool = True


class AnalyticsConfig(BaseModel):
    """Health analytics configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # Analytics settings
    enabled: bool = Field(True, description="Enable health analytics")
    data_collection_interval: int = Field(60, description="Data collection interval in seconds")
    data_retention_days: int = Field(30, description="Data retention period in days")
    
    # Storage configuration
    storage_backend: str = Field("memory", description="Storage backend (memory, file, database)")
    storage_path: Optional[str] = Field(None, description="Storage path for file backend")
    database_url: Optional[str] = Field(None, description="Database URL for database backend")
    
    # Trend analysis configuration
    trend_config: TrendConfig = Field(
        default_factory=TrendConfig,
        description="Trend analysis configuration"
    )
    
    # Prediction configuration
    prediction_config: PredictionConfig = Field(
        default_factory=PredictionConfig,
        description="Prediction model configuration"
    )
    
    # Report configuration
    report_config: ReportConfig = Field(
        default_factory=ReportConfig,
        description="Report generation configuration"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


def create_analytics_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> AnalyticsConfig:
    """Create analytics configuration with defaults."""
    return AnalyticsConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


# Export main classes and functions
__all__ = [
    'TrendType',
    'PredictionModel',
    'ReportFormat',
    'TrendConfig',
    'PredictionConfig',
    'ReportConfig',
    'AnalyticsConfig',
    'create_analytics_config',
]
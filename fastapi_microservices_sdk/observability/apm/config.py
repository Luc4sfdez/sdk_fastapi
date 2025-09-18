"""
APM configuration for FastAPI Microservices SDK.

This module provides configuration classes for the APM system,
including profiling, baseline management, SLA monitoring, and more.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator
from datetime import timedelta


class ProfilingType(str, Enum):
    """Performance profiling type enumeration."""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    DATABASE = "database"
    CUSTOM = "custom"


class SLAMetricType(str, Enum):
    """SLA metric type enumeration."""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"
    RESOURCE_UTILIZATION = "resource_utilization"
    CUSTOM = "custom"


class BottleneckType(str, Enum):
    """Bottleneck type enumeration."""
    CPU_BOUND = "cpu_bound"
    MEMORY_BOUND = "memory_bound"
    IO_BOUND = "io_bound"
    NETWORK_BOUND = "network_bound"
    DATABASE_BOUND = "database_bound"
    LOCK_CONTENTION = "lock_contention"


class TrendDirection(str, Enum):
    """Trend direction enumeration."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


@dataclass
class ProfilingConfig:
    """Performance profiling configuration."""
    enabled: bool = True
    profiling_types: List[ProfilingType] = field(
        default_factory=lambda: [
            ProfilingType.CPU,
            ProfilingType.MEMORY,
            ProfilingType.IO
        ]
    )
    
    # Profiling intervals
    cpu_profiling_interval: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    memory_profiling_interval: timedelta = field(default_factory=lambda: timedelta(seconds=60))
    io_profiling_interval: timedelta = field(default_factory=lambda: timedelta(seconds=30))
    
    # Profiling thresholds
    cpu_threshold: float = 80.0  # CPU usage percentage
    memory_threshold: float = 85.0  # Memory usage percentage
    io_threshold: float = 1000.0  # IO operations per second
    
    # Profiling duration
    profile_duration: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_profile_size: int = 100 * 1024 * 1024  # 100MB
    
    # Sampling configuration
    sampling_rate: float = 0.1  # 10% sampling
    adaptive_sampling: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'profiling_types': [pt.value for pt in self.profiling_types],
            'cpu_profiling_interval': self.cpu_profiling_interval.total_seconds(),
            'memory_profiling_interval': self.memory_profiling_interval.total_seconds(),
            'io_profiling_interval': self.io_profiling_interval.total_seconds(),
            'cpu_threshold': self.cpu_threshold,
            'memory_threshold': self.memory_threshold,
            'io_threshold': self.io_threshold,
            'profile_duration': self.profile_duration.total_seconds(),
            'max_profile_size': self.max_profile_size,
            'sampling_rate': self.sampling_rate,
            'adaptive_sampling': self.adaptive_sampling
        }


@dataclass
class BaselineConfig:
    """Performance baseline configuration."""
    enabled: bool = True
    
    # Baseline establishment
    baseline_period: timedelta = field(default_factory=lambda: timedelta(days=7))
    min_data_points: int = 100
    confidence_level: float = 0.95
    
    # Drift detection
    drift_detection_enabled: bool = True
    drift_threshold: float = 0.2  # 20% deviation
    drift_window: timedelta = field(default_factory=lambda: timedelta(hours=1))
    
    # Baseline update
    auto_update: bool = True
    update_frequency: timedelta = field(default_factory=lambda: timedelta(days=1))
    
    # Statistical parameters
    outlier_removal: bool = True
    outlier_threshold: float = 3.0  # Standard deviations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'baseline_period': self.baseline_period.total_seconds(),
            'min_data_points': self.min_data_points,
            'confidence_level': self.confidence_level,
            'drift_detection_enabled': self.drift_detection_enabled,
            'drift_threshold': self.drift_threshold,
            'drift_window': self.drift_window.total_seconds(),
            'auto_update': self.auto_update,
            'update_frequency': self.update_frequency.total_seconds(),
            'outlier_removal': self.outlier_removal,
            'outlier_threshold': self.outlier_threshold
        }


@dataclass
class SLAConfig:
    """SLA monitoring configuration."""
    enabled: bool = True
    
    # Default SLA thresholds
    default_response_time_ms: float = 1000.0
    default_throughput_rps: float = 100.0
    default_error_rate_percent: float = 1.0
    default_availability_percent: float = 99.9
    
    # Monitoring intervals
    monitoring_interval: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    evaluation_window: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    
    # Violation handling
    violation_threshold: int = 3  # Number of consecutive violations
    escalation_enabled: bool = True
    escalation_delay: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    
    # Reporting
    report_generation: bool = True
    report_frequency: timedelta = field(default_factory=lambda: timedelta(hours=24))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'default_response_time_ms': self.default_response_time_ms,
            'default_throughput_rps': self.default_throughput_rps,
            'default_error_rate_percent': self.default_error_rate_percent,
            'default_availability_percent': self.default_availability_percent,
            'monitoring_interval': self.monitoring_interval.total_seconds(),
            'evaluation_window': self.evaluation_window.total_seconds(),
            'violation_threshold': self.violation_threshold,
            'escalation_enabled': self.escalation_enabled,
            'escalation_delay': self.escalation_delay.total_seconds(),
            'report_generation': self.report_generation,
            'report_frequency': self.report_frequency.total_seconds()
        }


@dataclass
class BottleneckConfig:
    """Bottleneck detection configuration."""
    enabled: bool = True
    
    # Detection algorithms
    detection_algorithms: List[str] = field(
        default_factory=lambda: [
            "resource_utilization",
            "queue_analysis",
            "response_time_analysis"
        ]
    )
    
    # Detection thresholds
    cpu_bottleneck_threshold: float = 90.0
    memory_bottleneck_threshold: float = 95.0
    io_bottleneck_threshold: float = 80.0
    network_bottleneck_threshold: float = 80.0
    
    # Analysis parameters
    analysis_window: timedelta = field(default_factory=lambda: timedelta(minutes=10))
    min_samples: int = 50
    correlation_threshold: float = 0.7
    
    # Recommendation generation
    generate_recommendations: bool = True
    recommendation_confidence_threshold: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'detection_algorithms': self.detection_algorithms,
            'cpu_bottleneck_threshold': self.cpu_bottleneck_threshold,
            'memory_bottleneck_threshold': self.memory_bottleneck_threshold,
            'io_bottleneck_threshold': self.io_bottleneck_threshold,
            'network_bottleneck_threshold': self.network_bottleneck_threshold,
            'analysis_window': self.analysis_window.total_seconds(),
            'min_samples': self.min_samples,
            'correlation_threshold': self.correlation_threshold,
            'generate_recommendations': self.generate_recommendations,
            'recommendation_confidence_threshold': self.recommendation_confidence_threshold
        }


@dataclass
class TrendConfig:
    """Trend analysis configuration."""
    enabled: bool = True
    
    # Analysis parameters
    trend_window: timedelta = field(default_factory=lambda: timedelta(days=30))
    min_data_points: int = 100
    trend_significance_threshold: float = 0.05  # p-value
    
    # Capacity planning
    capacity_planning_enabled: bool = True
    planning_horizon: timedelta = field(default_factory=lambda: timedelta(days=90))
    growth_rate_threshold: float = 0.1  # 10% growth
    
    # Forecasting
    forecasting_models: List[str] = field(
        default_factory=lambda: [
            "linear_regression",
            "exponential_smoothing",
            "arima"
        ]
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'trend_window': self.trend_window.total_seconds(),
            'min_data_points': self.min_data_points,
            'trend_significance_threshold': self.trend_significance_threshold,
            'capacity_planning_enabled': self.capacity_planning_enabled,
            'planning_horizon': self.planning_horizon.total_seconds(),
            'growth_rate_threshold': self.growth_rate_threshold,
            'forecasting_models': self.forecasting_models
        }


@dataclass
class RegressionConfig:
    """Regression detection configuration."""
    enabled: bool = True
    
    # Detection parameters
    regression_threshold: float = 0.1  # 10% performance degradation
    statistical_significance: float = 0.05  # p-value
    min_samples: int = 30
    
    # Comparison methods
    comparison_methods: List[str] = field(
        default_factory=lambda: [
            "statistical_test",
            "percentile_comparison",
            "trend_analysis"
        ]
    )
    
    # CI/CD integration
    cicd_integration: bool = True
    fail_build_on_regression: bool = False
    regression_report_format: str = "json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'regression_threshold': self.regression_threshold,
            'statistical_significance': self.statistical_significance,
            'min_samples': self.min_samples,
            'comparison_methods': self.comparison_methods,
            'cicd_integration': self.cicd_integration,
            'fail_build_on_regression': self.fail_build_on_regression,
            'regression_report_format': self.regression_report_format
        }


class APMConfig(BaseModel):
    """Main APM configuration."""
    
    # Service information
    service_name: str = Field(..., description="Service name")
    service_version: str = Field("1.0.0", description="Service version")
    environment: str = Field("development", description="Environment")
    
    # APM settings
    enabled: bool = Field(True, description="Enable APM")
    data_retention_days: int = Field(30, description="Data retention period in days")
    
    # Sampling configuration
    sampling_enabled: bool = Field(True, description="Enable sampling")
    sampling_rate: float = Field(0.1, description="Sampling rate (0.0-1.0)")
    
    # Performance thresholds
    performance_budget_ms: Optional[float] = Field(None, description="Performance budget in milliseconds")
    
    # Component configurations
    profiling: ProfilingConfig = Field(
        default_factory=ProfilingConfig,
        description="Profiling configuration"
    )
    
    baseline: BaselineConfig = Field(
        default_factory=BaselineConfig,
        description="Baseline configuration"
    )
    
    sla: SLAConfig = Field(
        default_factory=SLAConfig,
        description="SLA configuration"
    )
    
    bottleneck: BottleneckConfig = Field(
        default_factory=BottleneckConfig,
        description="Bottleneck detection configuration"
    )
    
    trend: TrendConfig = Field(
        default_factory=TrendConfig,
        description="Trend analysis configuration"
    )
    
    regression: RegressionConfig = Field(
        default_factory=RegressionConfig,
        description="Regression detection configuration"
    )
    
    # Storage configuration
    storage_backend: str = Field("memory", description="Storage backend (memory, redis, database)")
    storage_config: Dict[str, Any] = Field(default_factory=dict, description="Storage configuration")
    
    # Export configuration
    export_enabled: bool = Field(False, description="Enable data export")
    export_format: str = Field("json", description="Export format")
    export_interval: int = Field(3600, description="Export interval in seconds")
    
    @validator('sampling_rate')
    def validate_sampling_rate(cls, v):
        """Validate sampling rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Sampling rate must be between 0.0 and 1.0')
        return v
    
    @validator('data_retention_days')
    def validate_retention_days(cls, v):
        """Validate data retention days."""
        if v < 1:
            raise ValueError('Data retention days must be at least 1')
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_name': self.service_name,
            'service_version': self.service_version,
            'environment': self.environment,
            'enabled': self.enabled,
            'data_retention_days': self.data_retention_days,
            'sampling_enabled': self.sampling_enabled,
            'sampling_rate': self.sampling_rate,
            'performance_budget_ms': self.performance_budget_ms,
            'profiling': self.profiling.to_dict(),
            'baseline': self.baseline.to_dict(),
            'sla': self.sla.to_dict(),
            'bottleneck': self.bottleneck.to_dict(),
            'trend': self.trend.to_dict(),
            'regression': self.regression.to_dict(),
            'storage_backend': self.storage_backend,
            'storage_config': self.storage_config,
            'export_enabled': self.export_enabled,
            'export_format': self.export_format,
            'export_interval': self.export_interval
        }


def create_apm_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: str = "development",
    **kwargs
) -> APMConfig:
    """Create APM configuration with defaults."""
    return APMConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        **kwargs
    )


# Export configuration classes
__all__ = [
    'ProfilingType',
    'SLAMetricType',
    'BottleneckType',
    'TrendDirection',
    'ProfilingConfig',
    'BaselineConfig',
    'SLAConfig',
    'BottleneckConfig',
    'TrendConfig',
    'RegressionConfig',
    'APMConfig',
    'create_apm_config',
]
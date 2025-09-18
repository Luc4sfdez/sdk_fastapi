"""
Monitoring configuration for the database monitoring system.

This module provides configuration classes for managing monitoring settings,
metrics collection, alerting, and analytics across different database engines.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import timedelta

from ..config import DatabaseEngine


class MonitoringLevel(Enum):
    """Monitoring detail level."""
    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class MetricsStorage(Enum):
    """Metrics storage backend."""
    MEMORY = "memory"
    REDIS = "redis"
    PROMETHEUS = "prometheus"
    INFLUXDB = "influxdb"
    CUSTOM = "custom"


class AlertChannel(Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"


class MonitoringConfig(BaseModel):
    """Configuration for database monitoring and analytics."""
    
    # General monitoring settings
    enabled: bool = Field(
        default=True,
        description="Enable database monitoring"
    )
    
    monitoring_level: MonitoringLevel = Field(
        default=MonitoringLevel.DETAILED,
        description="Level of monitoring detail"
    )
    
    # Metrics collection settings
    metrics_collection_interval: float = Field(
        default=30.0,
        description="Metrics collection interval in seconds"
    )
    
    metrics_retention_period: timedelta = Field(
        default=timedelta(days=30),
        description="How long to retain metrics data"
    )
    
    metrics_storage: MetricsStorage = Field(
        default=MetricsStorage.MEMORY,
        description="Backend for storing metrics"
    )
    
    # Query monitoring settings
    slow_query_threshold: float = Field(
        default=1.0,
        description="Threshold for slow query detection (seconds)"
    )
    
    query_sampling_rate: float = Field(
        default=0.1,
        description="Rate of query sampling (0.0 to 1.0)"
    )
    
    max_query_history: int = Field(
        default=10000,
        description="Maximum number of queries to keep in history"
    )
    
    # Performance monitoring settings
    performance_baseline_period: timedelta = Field(
        default=timedelta(hours=24),
        description="Period for establishing performance baselines"
    )
    
    performance_alert_threshold: float = Field(
        default=2.0,
        description="Performance degradation threshold (multiplier)"
    )
    
    # Health monitoring settings
    health_check_interval: float = Field(
        default=60.0,
        description="Health check interval in seconds"
    )
    
    health_check_timeout: float = Field(
        default=10.0,
        description="Health check timeout in seconds"
    )
    
    # Connection monitoring settings
    connection_pool_monitoring: bool = Field(
        default=True,
        description="Enable connection pool monitoring"
    )
    
    connection_leak_detection: bool = Field(
        default=True,
        description="Enable connection leak detection"
    )
    
    connection_leak_threshold: float = Field(
        default=300.0,
        description="Connection leak detection threshold (seconds)"
    )
    
    # Alerting settings
    alerting_enabled: bool = Field(
        default=True,
        description="Enable alerting system"
    )
    
    alert_channels: List[AlertChannel] = Field(
        default_factory=lambda: [AlertChannel.EMAIL],
        description="Alert notification channels"
    )
    
    alert_cooldown_period: timedelta = Field(
        default=timedelta(minutes=15),
        description="Cooldown period between similar alerts"
    )
    
    # Analytics settings
    analytics_enabled: bool = Field(
        default=True,
        description="Enable analytics and optimization"
    )
    
    query_optimization_enabled: bool = Field(
        default=True,
        description="Enable automatic query optimization suggestions"
    )
    
    predictive_analytics_enabled: bool = Field(
        default=False,
        description="Enable predictive failure analytics"
    )
    
    # Storage settings
    data_directory: Optional[Path] = Field(
        default=None,
        description="Directory for storing monitoring data"
    )
    
    # Integration settings
    prometheus_enabled: bool = Field(
        default=False,
        description="Enable Prometheus metrics export"
    )
    
    prometheus_port: int = Field(
        default=8000,
        description="Port for Prometheus metrics endpoint"
    )
    
    grafana_dashboard_enabled: bool = Field(
        default=False,
        description="Enable Grafana dashboard generation"
    )
    
    # Engine-specific settings
    engine_settings: Dict[DatabaseEngine, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Engine-specific monitoring settings"
    )
    
    # Custom metrics
    custom_metrics: List[str] = Field(
        default_factory=list,
        description="List of custom metrics to collect"
    )
    
    # Notification settings
    notification_webhooks: List[str] = Field(
        default_factory=list,
        description="Webhook URLs for notifications"
    )
    
    email_settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Email notification settings"
    )
    
    slack_settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Slack notification settings"
    )
    
    @validator('metrics_collection_interval', 'health_check_interval')
    def validate_positive_intervals(cls, v):
        """Validate positive interval values."""
        if v <= 0:
            raise ValueError("Interval must be positive")
        return v
    
    @validator('query_sampling_rate')
    def validate_sampling_rate(cls, v):
        """Validate sampling rate is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Sampling rate must be between 0.0 and 1.0")
        return v
    
    @validator('prometheus_port')
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    def get_engine_setting(self, engine: DatabaseEngine, key: str, default: Any = None) -> Any:
        """
        Get engine-specific setting.
        
        Args:
            engine: Database engine
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value or default
        """
        return self.engine_settings.get(engine, {}).get(key, default)
    
    def set_engine_setting(self, engine: DatabaseEngine, key: str, value: Any) -> None:
        """
        Set engine-specific setting.
        
        Args:
            engine: Database engine
            key: Setting key
            value: Setting value
        """
        if engine not in self.engine_settings:
            self.engine_settings[engine] = {}
        self.engine_settings[engine][key] = value
    
    def get_metrics_to_collect(self, engine: DatabaseEngine) -> Set[str]:
        """
        Get metrics to collect for specific engine.
        
        Args:
            engine: Database engine
            
        Returns:
            Set of metric names to collect
        """
        base_metrics = {
            'query_count',
            'query_duration',
            'connection_count',
            'active_connections',
            'failed_queries',
            'slow_queries'
        }
        
        engine_specific = {
            DatabaseEngine.POSTGRESQL: {
                'pg_stat_database',
                'pg_stat_user_tables',
                'pg_locks',
                'pg_stat_activity'
            },
            DatabaseEngine.MYSQL: {
                'mysql_global_status',
                'mysql_processlist',
                'mysql_innodb_metrics'
            },
            DatabaseEngine.MONGODB: {
                'mongodb_server_status',
                'mongodb_db_stats',
                'mongodb_collection_stats'
            },
            DatabaseEngine.SQLITE: {
                'sqlite_pragma_stats',
                'sqlite_table_info'
            }
        }
        
        metrics = base_metrics.copy()
        metrics.update(engine_specific.get(engine, set()))
        metrics.update(self.custom_metrics)
        
        return metrics
    
    def get_alert_thresholds(self, engine: DatabaseEngine) -> Dict[str, float]:
        """
        Get alert thresholds for specific engine.
        
        Args:
            engine: Database engine
            
        Returns:
            Dictionary of metric thresholds
        """
        default_thresholds = {
            'query_duration_p95': 5.0,  # 95th percentile query duration
            'connection_utilization': 0.8,  # 80% connection pool utilization
            'error_rate': 0.05,  # 5% error rate
            'slow_query_rate': 0.1,  # 10% slow query rate
            'cpu_utilization': 0.8,  # 80% CPU utilization
            'memory_utilization': 0.9,  # 90% memory utilization
            'disk_utilization': 0.85  # 85% disk utilization
        }
        
        # Engine-specific thresholds
        engine_thresholds = self.get_engine_setting(engine, 'alert_thresholds', {})
        
        # Merge with defaults
        thresholds = default_thresholds.copy()
        thresholds.update(engine_thresholds)
        
        return thresholds
    
    def is_metric_enabled(self, metric_name: str, engine: DatabaseEngine) -> bool:
        """
        Check if a specific metric is enabled for collection.
        
        Args:
            metric_name: Name of the metric
            engine: Database engine
            
        Returns:
            True if metric should be collected
        """
        if not self.enabled:
            return False
        
        enabled_metrics = self.get_metrics_to_collect(engine)
        return metric_name in enabled_metrics
    
    def get_retention_policy(self, metric_type: str) -> timedelta:
        """
        Get retention policy for specific metric type.
        
        Args:
            metric_type: Type of metric
            
        Returns:
            Retention period
        """
        retention_policies = {
            'real_time': timedelta(hours=1),
            'short_term': timedelta(days=7),
            'medium_term': timedelta(days=30),
            'long_term': timedelta(days=365)
        }
        
        return retention_policies.get(metric_type, self.metrics_retention_period)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
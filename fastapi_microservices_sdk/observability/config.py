"""
Configuration management for the observability system.

This module provides comprehensive configuration classes for all observability
components including metrics, tracing, logging, health monitoring, and alerting.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Dict, Any, Optional, List, Union
from datetime import timedelta
from pathlib import Path
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

# Integration with existing configuration system
try:
    from ..security.advanced.config_manager import SecurityConfigManager
    SECURITY_INTEGRATION_AVAILABLE = True
except ImportError:
    SECURITY_INTEGRATION_AVAILABLE = False
    SecurityConfigManager = None


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class TracingBackend(Enum):
    """Supported tracing backends."""
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    OTLP = "otlp"
    CONSOLE = "console"


class LoggingBackend(Enum):
    """Supported logging backends."""
    ELASTICSEARCH = "elasticsearch"
    LOGSTASH = "logstash"
    FLUENTD = "fluentd"
    CONSOLE = "console"
    FILE = "file"


class AlertChannel(Enum):
    """Supported alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    SMS = "sms"


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    NONE = "none"


class SamplingStrategy(Enum):
    """Tracing sampling strategies."""
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class HealthState(Enum):
    """Health check states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    ADAPTIVE = "adaptive"


class MetricsConfig(BaseModel):
    """Configuration for metrics collection and export."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    
    # Prometheus settings
    prometheus_enabled: bool = Field(
        default=True,
        description="Enable Prometheus metrics export"
    )
    
    prometheus_endpoint: str = Field(
        default="/metrics",
        description="Prometheus metrics endpoint path"
    )
    
    prometheus_port: int = Field(
        default=8000,
        description="Port for Prometheus metrics server"
    )
    
    # Collection settings
    collection_interval: float = Field(
        default=15.0,
        description="Metrics collection interval in seconds"
    )
    
    system_metrics_enabled: bool = Field(
        default=True,
        description="Enable system metrics collection (CPU, memory, etc.)"
    )
    
    application_metrics_enabled: bool = Field(
        default=True,
        description="Enable application metrics collection"
    )
    
    # Storage and retention
    retention_days: int = Field(
        default=30,
        description="Metrics retention period in days"
    )
    
    max_series: int = Field(
        default=100000,
        description="Maximum number of metric series"
    )
    
    high_cardinality_limit: int = Field(
        default=10000,
        description="Limit for high cardinality metrics"
    )
    
    # Labels and dimensions
    default_labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Default labels applied to all metrics"
    )
    
    label_value_length_limit: int = Field(
        default=128,
        description="Maximum length for label values"
    )
    
    # Performance settings
    batch_size: int = Field(
        default=1000,
        description="Batch size for metrics export"
    )
    
    export_timeout: float = Field(
        default=30.0,
        description="Timeout for metrics export in seconds"
    )
    
    # Custom metrics configuration
    custom_metrics: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Custom metrics definitions"
    )
    
    @validator('collection_interval', 'export_timeout')
    def validate_positive_float(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v
    
    @validator('retention_days', 'max_series', 'high_cardinality_limit')
    def validate_positive_int(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class TracingConfig(BaseModel):
    """Configuration for distributed tracing."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable distributed tracing"
    )
    
    service_name: str = Field(
        default="fastapi-microservice",
        description="Service name for tracing"
    )
    
    service_version: Optional[str] = Field(
        default=None,
        description="Service version for tracing"
    )
    
    # Backend configuration
    backend: TracingBackend = Field(
        default=TracingBackend.JAEGER,
        description="Tracing backend to use"
    )
    
    # Jaeger settings
    jaeger_endpoint: str = Field(
        default="http://localhost:14268/api/traces",
        description="Jaeger collector endpoint"
    )
    
    jaeger_agent_host: str = Field(
        default="localhost",
        description="Jaeger agent host"
    )
    
    jaeger_agent_port: int = Field(
        default=6831,
        description="Jaeger agent port"
    )
    
    # OTLP settings
    otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OTLP collector endpoint"
    )
    
    otlp_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="OTLP headers for authentication"
    )
    
    # Sampling configuration
    sampling_strategy: SamplingStrategy = Field(
        default=SamplingStrategy.PROBABILISTIC,
        description="Sampling strategy to use"
    )
    
    sampling_rate: float = Field(
        default=0.1,
        description="Sampling rate (0.0 to 1.0)"
    )
    
    max_spans_per_trace: int = Field(
        default=1000,
        description="Maximum spans per trace"
    )
    
    # Export settings
    export_timeout: float = Field(
        default=30.0,
        description="Timeout for trace export in seconds"
    )
    
    batch_size: int = Field(
        default=512,
        description="Batch size for span export"
    )
    
    max_queue_size: int = Field(
        default=2048,
        description="Maximum queue size for spans"
    )
    
    # Resource attributes
    resource_attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Resource attributes for tracing"
    )
    
    @validator('sampling_rate')
    def validate_sampling_rate(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Sampling rate must be between 0.0 and 1.0")
        return v
    
    @validator('export_timeout')
    def validate_positive_float(cls, v):
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class LoggingConfig(BaseModel):
    """Configuration for structured logging."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable structured logging"
    )
    
    level: str = Field(
        default="INFO",
        description="Default logging level"
    )
    
    format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    
    # Correlation settings
    correlation_id_enabled: bool = Field(
        default=True,
        description="Enable correlation ID tracking"
    )
    
    trace_integration_enabled: bool = Field(
        default=True,
        description="Enable tracing integration"
    )
    
    # Backend configuration
    backends: List[LoggingBackend] = Field(
        default=[LoggingBackend.CONSOLE],
        description="Logging backends to use"
    )
    
    # Elasticsearch settings
    elasticsearch_hosts: List[str] = Field(
        default=["localhost:9200"],
        description="Elasticsearch hosts"
    )
    
    elasticsearch_index: str = Field(
        default="fastapi-logs",
        description="Elasticsearch index name"
    )
    
    elasticsearch_username: Optional[str] = Field(
        default=None,
        description="Elasticsearch username"
    )
    
    elasticsearch_password: Optional[str] = Field(
        default=None,
        description="Elasticsearch password"
    )
    
    # File logging settings
    file_path: Optional[Path] = Field(
        default=None,
        description="Log file path"
    )
    
    file_max_size: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum log file size in bytes"
    )
    
    file_backup_count: int = Field(
        default=5,
        description="Number of backup log files"
    )
    
    # Processing settings
    buffer_size: int = Field(
        default=1000,
        description="Log buffer size"
    )
    
    flush_interval: float = Field(
        default=5.0,
        description="Log flush interval in seconds"
    )
    
    # Security settings
    mask_sensitive_data: bool = Field(
        default=True,
        description="Enable sensitive data masking"
    )
    
    sensitive_fields: List[str] = Field(
        default=["password", "token", "secret", "key", "authorization"],
        description="Fields to mask in logs"
    )
    
    # Audit logging
    audit_enabled: bool = Field(
        default=True,
        description="Enable audit logging"
    )
    
    audit_events: List[str] = Field(
        default=["login", "logout", "create", "update", "delete"],
        description="Events to audit"
    )


class HealthConfig(BaseModel):
    """Configuration for health monitoring."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable health monitoring"
    )
    
    # Probe endpoints
    readiness_endpoint: str = Field(
        default="/health/ready",
        description="Readiness probe endpoint"
    )
    
    liveness_endpoint: str = Field(
        default="/health/live",
        description="Liveness probe endpoint"
    )
    
    health_endpoint: str = Field(
        default="/health",
        description="General health endpoint"
    )
    
    # Check intervals
    check_interval: float = Field(
        default=30.0,
        description="Health check interval in seconds"
    )
    
    timeout: float = Field(
        default=10.0,
        description="Health check timeout in seconds"
    )
    
    # Dependency checks
    dependency_checks_enabled: bool = Field(
        default=True,
        description="Enable dependency health checks"
    )
    
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of dependencies to check"
    )
    
    # Circuit breaker integration
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker integration"
    )
    
    failure_threshold: int = Field(
        default=5,
        description="Failure threshold for circuit breaker"
    )
    
    recovery_timeout: float = Field(
        default=60.0,
        description="Recovery timeout in seconds"
    )


class AlertConfig(BaseModel):
    """Configuration for alerting system."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable alerting system"
    )
    
    # Alert channels
    channels: List[AlertChannel] = Field(
        default=[AlertChannel.EMAIL],
        description="Alert notification channels"
    )
    
    # Email settings
    email_smtp_host: str = Field(
        default="localhost",
        description="SMTP host for email alerts"
    )
    
    email_smtp_port: int = Field(
        default=587,
        description="SMTP port for email alerts"
    )
    
    email_username: Optional[str] = Field(
        default=None,
        description="SMTP username"
    )
    
    email_password: Optional[str] = Field(
        default=None,
        description="SMTP password"
    )
    
    email_from: str = Field(
        default="alerts@fastapi-microservices.com",
        description="From email address"
    )
    
    email_to: List[str] = Field(
        default_factory=list,
        description="Default email recipients"
    )
    
    # Slack settings
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL"
    )
    
    slack_channel: str = Field(
        default="#alerts",
        description="Slack channel for alerts"
    )
    
    # PagerDuty settings
    pagerduty_integration_key: Optional[str] = Field(
        default=None,
        description="PagerDuty integration key"
    )
    
    # Webhook settings
    webhook_urls: List[str] = Field(
        default_factory=list,
        description="Webhook URLs for alerts"
    )
    
    # Alert rules
    default_rules: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Default alert rules"
    )
    
    # Escalation settings
    escalation_enabled: bool = Field(
        default=True,
        description="Enable alert escalation"
    )
    
    escalation_timeout: float = Field(
        default=300.0,  # 5 minutes
        description="Escalation timeout in seconds"
    )
    
    # Grouping and deduplication
    grouping_enabled: bool = Field(
        default=True,
        description="Enable alert grouping"
    )
    
    grouping_window: float = Field(
        default=60.0,
        description="Alert grouping window in seconds"
    )
    
    deduplication_enabled: bool = Field(
        default=True,
        description="Enable alert deduplication"
    )


class DashboardConfig(BaseModel):
    """Configuration for dashboard and visualization."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable dashboard system"
    )
    
    # Grafana integration
    grafana_enabled: bool = Field(
        default=True,
        description="Enable Grafana integration"
    )
    
    grafana_url: str = Field(
        default="http://localhost:3000",
        description="Grafana server URL"
    )
    
    grafana_api_key: Optional[str] = Field(
        default=None,
        description="Grafana API key"
    )
    
    grafana_org_id: int = Field(
        default=1,
        description="Grafana organization ID"
    )
    
    # Dashboard settings
    auto_provision: bool = Field(
        default=True,
        description="Auto-provision dashboards"
    )
    
    dashboard_path: str = Field(
        default="/dashboards",
        description="Dashboard endpoint path"
    )
    
    refresh_interval: int = Field(
        default=30,
        description="Dashboard refresh interval in seconds"
    )
    
    # Data retention
    data_retention_days: int = Field(
        default=90,
        description="Dashboard data retention in days"
    )


class IntegrationConfig(BaseModel):
    """Configuration for external integrations."""
    
    # Cloud provider settings
    cloud_provider: CloudProvider = Field(
        default=CloudProvider.NONE,
        description="Cloud provider for integration"
    )
    
    # AWS settings
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region"
    )
    
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    
    cloudwatch_enabled: bool = Field(
        default=False,
        description="Enable CloudWatch integration"
    )
    
    # GCP settings
    gcp_project_id: Optional[str] = Field(
        default=None,
        description="GCP project ID"
    )
    
    gcp_credentials_path: Optional[str] = Field(
        default=None,
        description="Path to GCP credentials file"
    )
    
    stackdriver_enabled: bool = Field(
        default=False,
        description="Enable Stackdriver integration"
    )
    
    # Azure settings
    azure_subscription_id: Optional[str] = Field(
        default=None,
        description="Azure subscription ID"
    )
    
    azure_resource_group: Optional[str] = Field(
        default=None,
        description="Azure resource group"
    )
    
    azure_monitor_enabled: bool = Field(
        default=False,
        description="Enable Azure Monitor integration"
    )
    
    # Kubernetes settings
    kubernetes_enabled: bool = Field(
        default=False,
        description="Enable Kubernetes integration"
    )
    
    kubernetes_namespace: str = Field(
        default="default",
        description="Kubernetes namespace"
    )
    
    kubernetes_config_path: Optional[str] = Field(
        default=None,
        description="Path to Kubernetes config file"
    )


class ObservabilityConfig(BaseModel):
    """Main configuration class for the observability system."""
    
    # General settings
    enabled: bool = Field(
        default=True,
        description="Enable observability system"
    )
    
    service_name: str = Field(
        default="fastapi-microservice",
        description="Service name for observability"
    )
    
    service_version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    # Component configurations
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig,
        description="Metrics configuration"
    )
    
    tracing: TracingConfig = Field(
        default_factory=TracingConfig,
        description="Tracing configuration"
    )
    
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    
    health: HealthConfig = Field(
        default_factory=HealthConfig,
        description="Health monitoring configuration"
    )
    
    alerting: AlertConfig = Field(
        default_factory=AlertConfig,
        description="Alerting configuration"
    )
    
    dashboard: DashboardConfig = Field(
        default_factory=DashboardConfig,
        description="Dashboard configuration"
    )
    
    integration: IntegrationConfig = Field(
        default_factory=IntegrationConfig,
        description="Integration configuration"
    )
    
    # Security settings
    security_enabled: bool = Field(
        default=True,
        description="Enable security features"
    )
    
    encryption_enabled: bool = Field(
        default=True,
        description="Enable data encryption"
    )
    
    # Performance settings
    max_memory_usage_mb: int = Field(
        default=512,
        description="Maximum memory usage in MB"
    )
    
    max_cpu_usage_percent: float = Field(
        default=80.0,
        description="Maximum CPU usage percentage"
    )
    
    # Global labels
    global_labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Global labels applied to all observability data"
    )
    
    @root_validator(skip_on_failure=True)
    def validate_config(cls, values):
        """Validate the entire configuration."""
        # Ensure service name is consistent across components
        service_name = values.get('service_name')
        if service_name:
            if 'tracing' in values:
                values['tracing'].service_name = service_name
        
        # Validate cloud provider settings
        integration = values.get('integration')
        if integration and integration.cloud_provider != CloudProvider.NONE:
            if integration.cloud_provider == CloudProvider.AWS:
                if not integration.aws_access_key_id or not integration.aws_secret_access_key:
                    if integration.cloudwatch_enabled:
                        raise ValueError("AWS credentials required for CloudWatch integration")
            elif integration.cloud_provider == CloudProvider.GCP:
                if not integration.gcp_project_id:
                    if integration.stackdriver_enabled:
                        raise ValueError("GCP project ID required for Stackdriver integration")
            elif integration.cloud_provider == CloudProvider.AZURE:
                if not integration.azure_subscription_id:
                    if integration.azure_monitor_enabled:
                        raise ValueError("Azure subscription ID required for Azure Monitor integration")
        
        return values
    
    @classmethod
    def from_env(cls) -> 'ObservabilityConfig':
        """Create configuration from environment variables."""
        import os
        
        # Basic settings
        config_data = {
            'service_name': os.getenv('OBSERVABILITY_SERVICE_NAME', 'fastapi-microservice'),
            'service_version': os.getenv('OBSERVABILITY_SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('OBSERVABILITY_ENVIRONMENT', 'development'),
            'enabled': os.getenv('OBSERVABILITY_ENABLED', 'true').lower() == 'true',
        }
        
        # Metrics configuration
        metrics_config = {
            'enabled': os.getenv('METRICS_ENABLED', 'true').lower() == 'true',
            'prometheus_enabled': os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true',
            'prometheus_endpoint': os.getenv('PROMETHEUS_ENDPOINT', '/metrics'),
            'prometheus_port': int(os.getenv('PROMETHEUS_PORT', '8000')),
            'collection_interval': float(os.getenv('METRICS_COLLECTION_INTERVAL', '15.0')),
        }
        config_data['metrics'] = MetricsConfig(**metrics_config)
        
        # Tracing configuration
        tracing_config = {
            'enabled': os.getenv('TRACING_ENABLED', 'true').lower() == 'true',
            'backend': TracingBackend(os.getenv('TRACING_BACKEND', 'jaeger')),
            'jaeger_endpoint': os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces'),
            'sampling_rate': float(os.getenv('TRACING_SAMPLING_RATE', '0.1')),
        }
        config_data['tracing'] = TracingConfig(**tracing_config)
        
        # Logging configuration
        logging_config = {
            'enabled': os.getenv('LOGGING_ENABLED', 'true').lower() == 'true',
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': os.getenv('LOG_FORMAT', 'json'),
        }
        config_data['logging'] = LoggingConfig(**logging_config)
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def get_component_config(self, component: str) -> Optional[BaseModel]:
        """Get configuration for a specific component."""
        return getattr(self, component, None)
    
    def is_component_enabled(self, component: str) -> bool:
        """Check if a component is enabled."""
        component_config = self.get_component_config(component)
        if component_config and hasattr(component_config, 'enabled'):
            return component_config.enabled
        return False
    
    def get_security_config(self) -> Optional[Dict[str, Any]]:
        """Get security configuration if available."""
        if SECURITY_INTEGRATION_AVAILABLE and self.security_enabled:
            try:
                security_manager = SecurityConfigManager()
                return security_manager.get_observability_config()
            except Exception:
                return None
        return None


# Configuration factory functions
def create_development_config() -> ObservabilityConfig:
    """Create configuration optimized for development environment."""
    return ObservabilityConfig(
        environment="development",
        metrics=MetricsConfig(
            collection_interval=5.0,
            system_metrics_enabled=True
        ),
        tracing=TracingConfig(
            sampling_rate=1.0,  # Sample all traces in development
            backend=TracingBackend.CONSOLE
        ),
        logging=LoggingConfig(
            level="DEBUG",
            backends=[LoggingBackend.CONSOLE]
        ),
        alerting=AlertConfig(
            enabled=False  # Disable alerts in development
        )
    )


def create_production_config() -> ObservabilityConfig:
    """Create configuration optimized for production environment."""
    return ObservabilityConfig(
        environment="production",
        metrics=MetricsConfig(
            collection_interval=30.0,
            retention_days=90,
            high_cardinality_limit=50000
        ),
        tracing=TracingConfig(
            sampling_rate=0.01,  # Low sampling rate in production
            backend=TracingBackend.JAEGER
        ),
        logging=LoggingConfig(
            level="INFO",
            backends=[LoggingBackend.ELASTICSEARCH],
            mask_sensitive_data=True
        ),
        alerting=AlertConfig(
            enabled=True,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.PAGERDUTY]
        ),
        security_enabled=True,
        encryption_enabled=True
    )


def create_testing_config() -> ObservabilityConfig:
    """Create configuration optimized for testing environment."""
    return ObservabilityConfig(
        environment="testing",
        metrics=MetricsConfig(
            enabled=False  # Disable metrics in tests
        ),
        tracing=TracingConfig(
            enabled=False  # Disable tracing in tests
        ),
        logging=LoggingConfig(
            level="WARNING",
            backends=[LoggingBackend.CONSOLE]
        ),
        health=HealthConfig(
            check_interval=5.0,
            timeout=2.0
        ),
        alerting=AlertConfig(
            enabled=False  # Disable alerts in tests
        )
    )


# Configuration validation utilities
def validate_observability_config(config: ObservabilityConfig) -> List[str]:
    """Validate observability configuration and return list of issues."""
    issues = []
    
    # Check required fields
    if not config.service_name:
        issues.append("Service name is required")
    
    # Validate metrics configuration
    if config.metrics.enabled:
        if config.metrics.prometheus_enabled and config.metrics.prometheus_port <= 0:
            issues.append("Invalid Prometheus port")
        
        if config.metrics.collection_interval <= 0:
            issues.append("Collection interval must be positive")
    
    # Validate tracing configuration
    if config.tracing.enabled:
        if not (0.0 <= config.tracing.sampling_rate <= 1.0):
            issues.append("Sampling rate must be between 0.0 and 1.0")
        
        if config.tracing.backend == TracingBackend.JAEGER:
            if not config.tracing.jaeger_endpoint:
                issues.append("Jaeger endpoint is required when using Jaeger backend")
    
    # Validate logging configuration
    if config.logging.enabled:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if config.logging.level not in valid_levels:
            issues.append(f"Invalid log level. Must be one of: {valid_levels}")
    
    # Validate alerting configuration
    if config.alerting.enabled:
        if AlertChannel.EMAIL in config.alerting.channels:
            if not config.alerting.email_smtp_host:
                issues.append("SMTP host is required for email alerts")
        
        if AlertChannel.SLACK in config.alerting.channels:
            if not config.alerting.slack_webhook_url:
                issues.append("Slack webhook URL is required for Slack alerts")
    
    return issues


# Export configuration classes and utilities
__all__ = [
    # Enums
    'MetricType',
    'TracingBackend', 
    'LoggingBackend',
    'AlertChannel',
    'CloudProvider',
    'SamplingStrategy',
    
    # Configuration classes
    'MetricsConfig',
    'TracingConfig',
    'LoggingConfig',
    'HealthConfig',
    'AlertConfig',
    'DashboardConfig',
    'IntegrationConfig',
    'ObservabilityConfig',
    
    # Factory functions
    'create_development_config',
    'create_production_config',
    'create_testing_config',
    
    # Utilities
    'validate_observability_config',
]
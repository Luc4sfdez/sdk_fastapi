"""
Logging Configuration for FastAPI Microservices SDK.

This module provides comprehensive configuration for structured logging,
ELK integration, security, and compliance features.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field, validator


class LogLevel(str, Enum):
    """Log level enumeration."""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class LogFormat(str, Enum):
    """Log format enumeration."""
    JSON = "json"
    ELK = "elk"
    COMPLIANCE = "compliance"
    STRUCTURED = "structured"
    PLAIN = "plain"


class ELKComponent(str, Enum):
    """ELK stack component enumeration."""
    ELASTICSEARCH = "elasticsearch"
    LOGSTASH = "logstash"
    KIBANA = "kibana"


class ComplianceStandard(str, Enum):
    """Compliance standard enumeration."""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"


class RetentionPeriod(str, Enum):
    """Log retention period enumeration."""
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"
    DAYS_365 = "365d"
    YEARS_7 = "7y"
    FOREVER = "forever"


@dataclass
class ELKConfig:
    """Configuration for ELK stack integration."""
    
    # Elasticsearch configuration
    elasticsearch_hosts: List[str] = field(default_factory=lambda: ["http://localhost:9200"])
    elasticsearch_index_pattern: str = "logs-{service}-{date}"
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    elasticsearch_api_key: Optional[str] = None
    elasticsearch_ssl_verify: bool = True
    elasticsearch_ssl_cert_path: Optional[str] = None
    elasticsearch_timeout: float = 30.0
    elasticsearch_max_retries: int = 3
    elasticsearch_retry_delay: float = 1.0
    
    # Logstash configuration
    logstash_host: str = "localhost"
    logstash_port: int = 5044
    logstash_protocol: str = "tcp"  # tcp, udp, http
    logstash_ssl_enabled: bool = False
    logstash_ssl_cert_path: Optional[str] = None
    logstash_timeout: float = 10.0
    
    # Kibana configuration
    kibana_host: str = "http://localhost:5601"
    kibana_username: Optional[str] = None
    kibana_password: Optional[str] = None
    kibana_ssl_verify: bool = True
    
    # Pipeline configuration
    pipeline_name: str = "default"
    pipeline_workers: int = 1
    pipeline_batch_size: int = 100
    pipeline_batch_timeout: float = 5.0
    pipeline_buffer_size: int = 1000
    pipeline_flush_interval: float = 30.0
    
    # Index management
    index_template_name: str = "microservices-logs"
    index_lifecycle_policy: Optional[str] = None
    index_shards: int = 1
    index_replicas: int = 1
    
    @classmethod
    def from_env(cls) -> 'ELKConfig':
        """Create ELK config from environment variables."""
        return cls(
            elasticsearch_hosts=os.getenv('ELK_ELASTICSEARCH_HOSTS', 'http://localhost:9200').split(','),
            elasticsearch_username=os.getenv('ELK_ELASTICSEARCH_USERNAME'),
            elasticsearch_password=os.getenv('ELK_ELASTICSEARCH_PASSWORD'),
            elasticsearch_api_key=os.getenv('ELK_ELASTICSEARCH_API_KEY'),
            logstash_host=os.getenv('ELK_LOGSTASH_HOST', 'localhost'),
            logstash_port=int(os.getenv('ELK_LOGSTASH_PORT', '5044')),
            kibana_host=os.getenv('ELK_KIBANA_HOST', 'http://localhost:5601'),
            kibana_username=os.getenv('ELK_KIBANA_USERNAME'),
            kibana_password=os.getenv('ELK_KIBANA_PASSWORD'),
        )


@dataclass
class SecurityConfig:
    """Configuration for logging security features."""
    
    # Data masking
    enable_data_masking: bool = True
    masking_patterns: Dict[str, str] = field(default_factory=lambda: {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}-\d{3}-\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    })
    masking_replacement: str = "***MASKED***"
    
    # PII protection
    enable_pii_protection: bool = True
    pii_fields: List[str] = field(default_factory=lambda: [
        'password', 'token', 'secret', 'key', 'auth', 'credential',
        'email', 'phone', 'ssn', 'address', 'name', 'dob'
    ])
    pii_replacement: str = "***PII***"
    
    # Encryption
    enable_log_encryption: bool = False
    encryption_key: Optional[str] = None
    encryption_algorithm: str = "AES-256-GCM"
    
    # Digital signatures
    enable_digital_signatures: bool = False
    signing_key: Optional[str] = None
    signature_algorithm: str = "RS256"
    
    # Access control
    enable_access_control: bool = True
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=lambda: ["admin", "auditor"])
    
    @classmethod
    def from_env(cls) -> 'SecurityConfig':
        """Create security config from environment variables."""
        return cls(
            enable_data_masking=os.getenv('LOG_ENABLE_DATA_MASKING', 'true').lower() == 'true',
            enable_pii_protection=os.getenv('LOG_ENABLE_PII_PROTECTION', 'true').lower() == 'true',
            enable_log_encryption=os.getenv('LOG_ENABLE_ENCRYPTION', 'false').lower() == 'true',
            encryption_key=os.getenv('LOG_ENCRYPTION_KEY'),
            enable_digital_signatures=os.getenv('LOG_ENABLE_SIGNATURES', 'false').lower() == 'true',
            signing_key=os.getenv('LOG_SIGNING_KEY'),
        )


@dataclass
class RetentionConfig:
    """Configuration for log retention policies."""
    
    # Retention periods by log level
    retention_periods: Dict[LogLevel, RetentionPeriod] = field(default_factory=lambda: {
        LogLevel.CRITICAL: RetentionPeriod.YEARS_7,
        LogLevel.ERROR: RetentionPeriod.DAYS_365,
        LogLevel.WARNING: RetentionPeriod.DAYS_90,
        LogLevel.INFO: RetentionPeriod.DAYS_30,
        LogLevel.DEBUG: RetentionPeriod.DAYS_7,
    })
    
    # Retention by compliance standard
    compliance_retention: Dict[ComplianceStandard, RetentionPeriod] = field(default_factory=lambda: {
        ComplianceStandard.GDPR: RetentionPeriod.DAYS_90,
        ComplianceStandard.HIPAA: RetentionPeriod.YEARS_7,
        ComplianceStandard.SOX: RetentionPeriod.YEARS_7,
        ComplianceStandard.PCI_DSS: RetentionPeriod.DAYS_365,
        ComplianceStandard.ISO_27001: RetentionPeriod.DAYS_365,
    })
    
    # Cleanup configuration
    enable_automatic_cleanup: bool = True
    cleanup_interval: float = 86400.0  # 24 hours
    cleanup_batch_size: int = 1000
    cleanup_dry_run: bool = False
    
    # Archive configuration
    enable_archiving: bool = False
    archive_storage_path: Optional[str] = None
    archive_compression: bool = True
    archive_encryption: bool = False
    
    @classmethod
    def from_env(cls) -> 'RetentionConfig':
        """Create retention config from environment variables."""
        return cls(
            enable_automatic_cleanup=os.getenv('LOG_ENABLE_AUTO_CLEANUP', 'true').lower() == 'true',
            cleanup_interval=float(os.getenv('LOG_CLEANUP_INTERVAL', '86400')),
            enable_archiving=os.getenv('LOG_ENABLE_ARCHIVING', 'false').lower() == 'true',
            archive_storage_path=os.getenv('LOG_ARCHIVE_PATH'),
        )


class LoggingConfig(BaseModel):
    """Main logging configuration."""
    
    # Basic configuration
    service_name: str = Field(default="fastapi-microservice", description="Service name for logging")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Environment name")
    
    # Log levels
    root_level: LogLevel = Field(default=LogLevel.INFO, description="Root logger level")
    logger_levels: Dict[str, LogLevel] = Field(default_factory=dict, description="Per-logger levels")
    
    # Formatting
    log_format: LogFormat = Field(default=LogFormat.JSON, description="Log format")
    include_timestamp: bool = Field(default=True, description="Include timestamp in logs")
    include_level: bool = Field(default=True, description="Include log level")
    include_logger_name: bool = Field(default=True, description="Include logger name")
    include_thread_info: bool = Field(default=False, description="Include thread information")
    include_process_info: bool = Field(default=False, description="Include process information")
    
    # Correlation
    enable_trace_correlation: bool = Field(default=True, description="Enable trace correlation")
    enable_request_correlation: bool = Field(default=True, description="Enable request correlation")
    correlation_id_header: str = Field(default="X-Correlation-ID", description="Correlation ID header")
    
    # Output configuration
    console_output: bool = Field(default=True, description="Enable console output")
    file_output: bool = Field(default=False, description="Enable file output")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    file_rotation: bool = Field(default=True, description="Enable file rotation")
    file_max_size: str = Field(default="100MB", description="Maximum file size")
    file_backup_count: int = Field(default=5, description="Number of backup files")
    
    # Buffering and performance
    enable_buffering: bool = Field(default=True, description="Enable log buffering")
    buffer_size: int = Field(default=1000, description="Buffer size")
    flush_interval: float = Field(default=5.0, description="Flush interval in seconds")
    flush_level: LogLevel = Field(default=LogLevel.ERROR, description="Auto-flush level")
    
    # ELK integration
    enable_elk: bool = Field(default=False, description="Enable ELK integration")
    elk_config: Optional[ELKConfig] = Field(default=None, description="ELK configuration")
    
    # Security
    security_config: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
    
    # Retention
    retention_config: RetentionConfig = Field(default_factory=RetentionConfig, description="Retention configuration")
    
    # Compliance
    compliance_standards: List[ComplianceStandard] = Field(default_factory=list, description="Compliance standards")
    enable_audit_logging: bool = Field(default=False, description="Enable audit logging")
    audit_log_path: Optional[str] = Field(default=None, description="Audit log file path")
    
    # Performance
    async_logging: bool = Field(default=True, description="Enable async logging")
    worker_threads: int = Field(default=2, description="Number of worker threads")
    queue_size: int = Field(default=10000, description="Log queue size")
    
    @validator('elk_config', pre=True, always=True)
    def set_elk_config(cls, v, values):
        """Set ELK config if ELK is enabled."""
        if values.get('enable_elk', False) and v is None:
            return ELKConfig()
        return v
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Create logging config from environment variables."""
        return cls(
            service_name=os.getenv('SERVICE_NAME', 'fastapi-microservice'),
            service_version=os.getenv('SERVICE_VERSION', '1.0.0'),
            environment=os.getenv('ENVIRONMENT', 'development'),
            root_level=LogLevel(os.getenv('LOG_LEVEL', 'INFO')),
            log_format=LogFormat(os.getenv('LOG_FORMAT', 'json')),
            enable_elk=os.getenv('ENABLE_ELK', 'false').lower() == 'true',
            elk_config=ELKConfig.from_env() if os.getenv('ENABLE_ELK', 'false').lower() == 'true' else None,
            security_config=SecurityConfig.from_env(),
            retention_config=RetentionConfig.from_env(),
            enable_audit_logging=os.getenv('ENABLE_AUDIT_LOGGING', 'false').lower() == 'true',
            console_output=os.getenv('LOG_CONSOLE', 'true').lower() == 'true',
            file_output=os.getenv('LOG_FILE_ENABLED', 'false').lower() == 'true',
            file_path=os.getenv('LOG_FILE_PATH'),
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True


def create_logging_config(
    service_name: str = "fastapi-microservice",
    environment: str = "development",
    log_level: LogLevel = LogLevel.INFO,
    enable_elk: bool = False,
    **kwargs
) -> LoggingConfig:
    """Create a logging configuration with common defaults."""
    config_data = {
        'service_name': service_name,
        'environment': environment,
        'root_level': log_level,
        'enable_elk': enable_elk,
        **kwargs
    }
    
    return LoggingConfig(**config_data)


# Export main classes and functions
__all__ = [
    'LogLevel',
    'LogFormat',
    'ELKComponent',
    'ComplianceStandard',
    'RetentionPeriod',
    'ELKConfig',
    'SecurityConfig',
    'RetentionConfig',
    'LoggingConfig',
    'create_logging_config',
]
"""
Logging Module for FastAPI Microservices SDK.
This module provides comprehensive logging capabilities including structured logging,
ELK integration, audit logging, compliance features, log search, alerting, and dashboards.
Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .config import (
    LoggingConfig,
    SecurityConfig,
    RetentionConfig,
    ELKConfig,
    ComplianceStandard,
    RetentionPeriod,
    create_logging_config
)

from .exceptions import (
    LoggingError,
    LogFormatError,
    LogShippingError,
    LogValidationError,
    LogRetentionError,
    ELKConnectionError,
    LogCorrelationError,
    DataMaskingError,
    AuditLogError,
    LogBufferError
)

from .structured_logger import (
    LogLevel,
    LogRecord,
    StructuredLogger,
    create_structured_logger
)

from .formatters import (
    JSONFormatter,
    ELKFormatter,
    ComplianceFormatter,
    create_json_formatter,
    create_elk_formatter,
    create_compliance_formatter
)

from .handlers import (
    ELKHandler,
    RotatingFileHandler,
    ComplianceHandler,
    create_elk_handler,
    create_rotating_file_handler,
    create_compliance_handler
)

from .audit import (
    AuditEventType,
    AuditOutcome,
    ComplianceFramework,
    AuditContext,
    AuditRecord,
    AuditLogger,
    ComplianceLogger,
    create_audit_logger,
    create_compliance_logger
)

from .retention import (
    RetentionAction,
    RetentionStatus,
    RetentionPolicy,
    RetentionJob,
    RetentionManager,
    create_retention_manager,
    create_retention_policy
)

from .search import (
    SearchOperator,
    AggregationType,
    AnomalyType,
    SearchCriteria,
    SearchQuery,
    SearchResult,
    PatternMatch,
    Anomaly,
    LogSearchEngine,
    PatternDetector,
    AnomalyDetector,
    create_search_engine,
    create_pattern_detector,
    create_anomaly_detector
)

from .alerting import (
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
    AlertCondition,
    AlertRule,
    Alert,
    NotificationConfig,
    AlertManager,
    create_alert_manager,
    create_alert_rule,
    create_notification_config
)

from .dashboards import (
    ReportType,
    ReportFormat,
    ComplianceStatus,
    ComplianceMetric,
    ComplianceReport,
    DashboardWidget,
    Dashboard,
    ComplianceDashboardManager,
    create_dashboard_manager
)

# Export all main classes and functions
__all__ = [
    # Configuration
    'LoggingConfig',
    'SecurityConfig', 
    'RetentionConfig',
    'ELKConfig',
    'ComplianceStandard',
    'RetentionPeriod',
    'create_logging_config',
    
    # Exceptions
    'LoggingError',
    'LogFormatError',
    'LogShippingError',
    'LogValidationError',
    'LogRetentionError',
    'ELKConnectionError',
    'LogCorrelationError',
    'DataMaskingError',
    'AuditLogError',
    'LogBufferError',
    
    # Structured Logger
    'LogLevel',
    'LogRecord',
    'StructuredLogger',
    'create_structured_logger',
    
    # Formatters
    'JSONFormatter',
    'ELKFormatter',
    'ComplianceFormatter',
    'create_json_formatter',
    'create_elk_formatter',
    'create_compliance_formatter',
    
    # Handlers
    'ELKHandler',
    'RotatingFileHandler',
    'ComplianceHandler',
    'create_elk_handler',
    'create_rotating_file_handler',
    'create_compliance_handler',
    
    # Audit Logging
    'AuditEventType',
    'AuditOutcome',
    'ComplianceFramework',
    'AuditContext',
    'AuditRecord',
    'AuditLogger',
    'ComplianceLogger',
    'create_audit_logger',
    'create_compliance_logger',
    
    # Retention Management
    'RetentionAction',
    'RetentionStatus',
    'RetentionPolicy',
    'RetentionJob',
    'RetentionManager',
    'create_retention_manager',
    'create_retention_policy',
    
    # Search and Analysis
    'SearchOperator',
    'AggregationType',
    'AnomalyType',
    'SearchCriteria',
    'SearchQuery',
    'SearchResult',
    'PatternMatch',
    'Anomaly',
    'LogSearchEngine',
    'PatternDetector',
    'AnomalyDetector',
    'create_search_engine',
    'create_pattern_detector',
    'create_anomaly_detector',
    
    # Alerting
    'AlertSeverity',
    'AlertStatus',
    'NotificationChannel',
    'AlertCondition',
    'AlertRule',
    'Alert',
    'NotificationConfig',
    'AlertManager',
    'create_alert_manager',
    'create_alert_rule',
    'create_notification_config',
    
    # Dashboards and Compliance
    'ReportType',
    'ReportFormat',
    'ComplianceStatus',
    'ComplianceMetric',
    'ComplianceReport',
    'DashboardWidget',
    'Dashboard',
    'ComplianceDashboardManager',
    'create_dashboard_manager',
]


def get_logging_info() -> dict:
    """Get information about logging module capabilities."""
    return {
        'version': '1.0.0',
        'features': [
            'Structured JSON Logging',
            'ELK Stack Integration', 
            'Audit Logging with Digital Signatures',
            'Compliance Logging (GDPR, HIPAA, SOX)',
            'Log Retention and Cleanup',
            'Advanced Log Search and Analysis',
            'Pattern Detection and Anomaly Detection',
            'Multi-channel Alerting',
            'Compliance Dashboards and Reporting',
            'Data Masking and PII Protection',
            'Tamper-proof Timestamps',
            'Log Aggregation and Analytics'
        ],
        'compliance_frameworks': [
            'GDPR',
            'HIPAA', 
            'SOX',
            'PCI-DSS',
            'ISO 27001',
            'NIST'
        ],
        'notification_channels': [
            'Email',
            'Slack',
            'Webhook',
            'PagerDuty',
            'Microsoft Teams',
            'Discord'
        ],
        'export_formats': [
            'JSON',
            'CSV',
            'PDF',
            'HTML',
            'Excel'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Advanced Logging module loaded")
logger.info("Features: Audit Logging, Compliance, Search, Alerting, Dashboards")
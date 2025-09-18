"""
Advanced Security Features for FastAPI Microservices SDK.
This module provides enterprise-grade security capabilities including:
- mTLS (Mutual TLS) for service-to-service communication
- RBAC (Role-Based Access Control) with hierarchical roles
- ABAC (Attribute-Based Access Control) with contextual policies
- Security logging and auditing
- Certificate management with automatic rotation
- Threat detection and response
"""
from .config import AdvancedSecurityConfig
from .exceptions import (
    AdvancedSecurityError,
    MTLSError,
    CertificateError,
    RBACError,
    ABACError,
    ThreatDetectionError,
    SecurityLoggingError
)
from .rbac import RBACManager, RBACEngine
from .abac import ABACManager
from .logging import (
    SecurityLogger,
    SecurityEvent,
    AuthEvent,
    AuthzEvent,
    ThreatEvent,
    CertificateEvent,
    SecurityEventType,
    SecurityEventSeverity,
    get_security_logger,
    configure_security_logger
)
from .certificates import (
    Certificate,
    CertificateChain,
    CertificateStore,
    CertificateRevocationList,
    CertificateInfo,
    CertificateFormat,
    CertificateStatus,
    KeyType
)
from .certificate_manager import (
    CertificateManager,
    SecureStorage,
    RotationTask,
    CertificateMetadata,
    RotationStatus,
    StorageEncryption
)
from .ca_client import (
    CAClient,
    CAConfig,
    CAProtocol,
    CertificateRequest,
    CertificateRequestStatus,
    CAClientFactory
)
from .unified_middleware import (
    UnifiedSecurityMiddleware,
    SecurityLayerType,
    SecurityLayerStatus,
    SecurityLayerConfig,
    SecurityContext,
    SecurityMetrics,
    setup_unified_security_middleware,
    create_default_layer_configs
)
from .config_manager import (
    SecurityConfigManager,
    ConfigProvider,
    ConfigValidator,
    FileConfigProvider,
    EnvironmentConfigProvider,
    SecurityConfigValidator,
    RBACConfigValidator,
    ABACConfigValidator,
    ConfigFormat,
    ConfigSource,
    ConfigChangeType,
    ConfigChange,
    ConfigVersion,
    create_file_config_manager,
    create_env_config_manager,
    create_hybrid_config_manager
)
from .monitoring import (
    SecurityMonitor,
    MetricsCollector,
    CorrelationTracker,
    PerformanceMonitor,
    SecurityMetric,
    PerformanceMetric,
    SecurityAlert,
    MetricType,
    MonitoringLevel,
    create_security_monitor,
    setup_component_monitoring
)

__all__ = [
    "AdvancedSecurityConfig",
    "AdvancedSecurityError",
    "MTLSError", 
    "CertificateError",
    "RBACError",
    "ABACError",
    "ThreatDetectionError",
    "SecurityLoggingError",
    "SecurityLogger",
    "SecurityEvent",
    "AuthEvent",
    "AuthzEvent",
    "ThreatEvent",
    "CertificateEvent",
    "SecurityEventType",
    "SecurityEventSeverity",
    "get_security_logger",
    "configure_security_logger",
    "Certificate",
    "CertificateChain",
    "CertificateStore",
    "CertificateRevocationList",
    "CertificateInfo",
    "CertificateFormat",
    "CertificateStatus",
    "KeyType",
    "CertificateManager",
    "SecureStorage",
    "RotationTask",
    "CertificateMetadata",
    "RotationStatus",
    "StorageEncryption",
    "CAClient",
    "CAConfig",
    "CAProtocol",
    "CertificateRequest",
    "CertificateRequestStatus",
    "CAClientFactory",
    "UnifiedSecurityMiddleware",
    "SecurityLayerType",
    "SecurityLayerStatus",
    "SecurityLayerConfig",
    "SecurityContext",
    "SecurityMetrics",
    "setup_unified_security_middleware",
    "create_default_layer_configs",
    "SecurityConfigManager",
    "ConfigProvider",
    "ConfigValidator",
    "FileConfigProvider",
    "EnvironmentConfigProvider",
    "SecurityConfigValidator",
    "RBACConfigValidator",
    "ABACConfigValidator",
    "ConfigFormat",
    "ConfigSource",
    "ConfigChangeType",
    "ConfigChange",
    "ConfigVersion",
    "create_file_config_manager",
    "create_env_config_manager",
    "create_hybrid_config_manager",
    "SecurityMonitor",
    "MetricsCollector",
    "CorrelationTracker",
    "PerformanceMonitor",
    "SecurityMetric",
    "PerformanceMetric",
    "SecurityAlert",
    "MetricType",
    "MonitoringLevel",
    "create_security_monitor",
    "setup_component_monitoring"
]
"""
Advanced Security Configuration for FastAPI Microservices SDK.

This module provides configuration classes for advanced security features
including mTLS, RBAC, ABAC, Certificate Management, Threat Detection,
and Security Logging.
"""

import os
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

from ..exceptions import ConfigurationError


class MTLSMode(str, Enum):
    """mTLS operation modes."""
    DISABLED = "disabled"
    OPTIONAL = "optional"  # Accept both mTLS and non-mTLS
    REQUIRED = "required"  # Reject non-mTLS connections


class CertificateBackend(str, Enum):
    """Certificate storage backends."""
    FILE_SYSTEM = "filesystem"
    VAULT = "vault"
    KUBERNETES = "kubernetes"
    AWS_ACM = "aws_acm"
    AZURE_KEY_VAULT = "azure_key_vault"


class PolicyEngine(str, Enum):
    """Policy engine types for RBAC/ABAC."""
    MEMORY = "memory"
    DATABASE = "database"
    REDIS = "redis"
    EXTERNAL_API = "external_api"


class ThreatDetectionLevel(str, Enum):
    """Threat detection sensitivity levels."""
    DISABLED = "disabled"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PARANOID = "paranoid"


class SecurityLogLevel(str, Enum):
    """Security logging levels."""
    NONE = "none"
    BASIC = "basic"
    DETAILED = "detailed"
    VERBOSE = "verbose"


@dataclass
class MTLSConfig:
    """Mutual TLS configuration."""
    
    # Basic mTLS settings
    enabled: bool = False
    mode: MTLSMode = MTLSMode.DISABLED
    
    # Certificate paths
    server_cert_path: Optional[str] = None
    server_key_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    ca_cert_path: Optional[str] = None
    
    # Certificate validation settings
    verify_client_cert: bool = True
    verify_server_cert: bool = True
    check_hostname: bool = True
    check_revocation: bool = True
    
    # SSL/TLS settings
    ssl_version: str = "TLSv1.2"
    cipher_suites: List[str] = field(default_factory=lambda: [
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES256-SHA384",
        "ECDHE-RSA-AES128-SHA256"
    ])
    
    # Connection settings
    handshake_timeout: int = 10
    connection_timeout: int = 30
    
    def validate(self) -> List[str]:
        """Validate mTLS configuration."""
        issues = []
        
        if self.enabled and self.mode == MTLSMode.DISABLED:
            issues.append("mTLS is enabled but mode is set to DISABLED")
        
        if self.mode != MTLSMode.DISABLED:
            if not self.server_cert_path:
                issues.append("server_cert_path is required when mTLS is not disabled")
            if not self.server_key_path:
                issues.append("server_key_path is required when mTLS is not disabled")
            if not self.ca_cert_path:
                issues.append("ca_cert_path is required when mTLS is not disabled")
            
            # Check if certificate files exist
            for cert_type, path in [
                ("server_cert", self.server_cert_path),
                ("server_key", self.server_key_path),
                ("client_cert", self.client_cert_path),
                ("client_key", self.client_key_path),
                ("ca_cert", self.ca_cert_path)
            ]:
                if path and not Path(path).exists():
                    issues.append(f"{cert_type}_path file does not exist: {path}")
        
        if self.handshake_timeout < 1:
            issues.append("handshake_timeout must be > 0")
        
        if self.connection_timeout < 1:
            issues.append("connection_timeout must be > 0")
        
        return issues


@dataclass
class CertificateConfig:
    """Certificate management configuration."""
    
    # Certificate backend
    backend: CertificateBackend = CertificateBackend.FILE_SYSTEM
    
    # Auto-rotation settings
    auto_rotation_enabled: bool = True
    rotation_threshold_days: int = 30  # Rotate when cert expires in X days
    rotation_check_interval: int = 3600  # Check every hour
    
    # Certificate Authority settings
    ca_url: Optional[str] = None
    ca_username: Optional[str] = None
    ca_password: Optional[str] = None
    ca_token: Optional[str] = None
    
    # Certificate generation settings
    key_size: int = 2048
    key_algorithm: str = "RSA"  # RSA, ECDSA
    signature_algorithm: str = "SHA256"
    certificate_validity_days: int = 365
    
    # Storage settings
    storage_path: str = "/etc/ssl/microservices"
    backup_enabled: bool = True
    backup_retention_days: int = 90
    
    # Vault backend settings (if using Vault)
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    vault_mount_path: str = "pki"
    vault_role: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate certificate configuration."""
        issues = []
        
        if self.rotation_threshold_days < 1:
            issues.append("rotation_threshold_days must be > 0")
        
        if self.rotation_check_interval < 60:
            issues.append("rotation_check_interval must be >= 60 seconds")
        
        if self.key_size < 2048:
            issues.append("key_size must be >= 2048 for security")
        
        if self.certificate_validity_days < 1:
            issues.append("certificate_validity_days must be > 0")
        
        if self.backend == CertificateBackend.VAULT:
            if not self.vault_url:
                issues.append("vault_url is required when using Vault backend")
            if not self.vault_token:
                issues.append("vault_token is required when using Vault backend")
        
        if self.backend == CertificateBackend.FILE_SYSTEM:
            storage_path = Path(self.storage_path)
            if not storage_path.parent.exists():
                issues.append(f"Certificate storage parent directory does not exist: {storage_path.parent}")
        
        return issues


@dataclass
class RBACConfig:
    """Role-Based Access Control configuration."""
    
    # RBAC engine settings
    enabled: bool = False
    policy_engine: PolicyEngine = PolicyEngine.MEMORY
    
    # Role hierarchy settings
    enable_role_hierarchy: bool = True
    max_hierarchy_depth: int = 10
    
    # Permission settings
    default_deny: bool = True  # Deny by default if no explicit permission
    case_sensitive_permissions: bool = False
    
    # Policy storage settings
    policy_file_path: Optional[str] = None
    policy_database_url: Optional[str] = None
    policy_redis_url: Optional[str] = None
    policy_api_url: Optional[str] = None
    
    # Cache settings
    enable_policy_cache: bool = True
    policy_cache_ttl: int = 300  # 5 minutes
    role_cache_ttl: int = 600    # 10 minutes
    
    # Performance settings
    max_roles_per_user: int = 50
    max_permissions_per_role: int = 1000
    
    def validate(self) -> List[str]:
        """Validate RBAC configuration."""
        issues = []
        
        if self.enabled:
            if self.policy_engine == PolicyEngine.DATABASE and not self.policy_database_url:
                issues.append("policy_database_url is required when using database policy engine")
            
            if self.policy_engine == PolicyEngine.REDIS and not self.policy_redis_url:
                issues.append("policy_redis_url is required when using Redis policy engine")
            
            if self.policy_engine == PolicyEngine.EXTERNAL_API and not self.policy_api_url:
                issues.append("policy_api_url is required when using external API policy engine")
        
        if self.max_hierarchy_depth < 1:
            issues.append("max_hierarchy_depth must be > 0")
        
        if self.policy_cache_ttl < 0:
            issues.append("policy_cache_ttl must be >= 0")
        
        if self.role_cache_ttl < 0:
            issues.append("role_cache_ttl must be >= 0")
        
        if self.max_roles_per_user < 1:
            issues.append("max_roles_per_user must be > 0")
        
        if self.max_permissions_per_role < 1:
            issues.append("max_permissions_per_role must be > 0")
        
        return issues


@dataclass
class ABACConfig:
    """Attribute-Based Access Control configuration."""
    
    # ABAC engine settings
    enabled: bool = False
    policy_engine: PolicyEngine = PolicyEngine.MEMORY
    
    # Policy evaluation settings
    default_decision: str = "DENY"  # ALLOW, DENY
    policy_combining_algorithm: str = "DENY_OVERRIDES"  # DENY_OVERRIDES, PERMIT_OVERRIDES, FIRST_APPLICABLE
    
    # Attribute settings
    enable_dynamic_attributes: bool = True
    attribute_cache_enabled: bool = True
    attribute_cache_ttl: int = 300  # 5 minutes
    
    # Policy storage settings (same as RBAC)
    policy_file_path: Optional[str] = None
    policy_database_url: Optional[str] = None
    policy_redis_url: Optional[str] = None
    policy_api_url: Optional[str] = None
    
    # Performance settings
    max_policies_per_request: int = 100
    policy_evaluation_timeout: int = 5  # seconds
    max_attribute_size: int = 1024  # bytes
    
    # Context settings
    include_environment_attributes: bool = True
    include_time_attributes: bool = True
    include_location_attributes: bool = False
    
    def validate(self) -> List[str]:
        """Validate ABAC configuration."""
        issues = []
        
        if self.enabled:
            if self.policy_engine == PolicyEngine.DATABASE and not self.policy_database_url:
                issues.append("policy_database_url is required when using database policy engine")
            
            if self.policy_engine == PolicyEngine.REDIS and not self.policy_redis_url:
                issues.append("policy_redis_url is required when using Redis policy engine")
            
            if self.policy_engine == PolicyEngine.EXTERNAL_API and not self.policy_api_url:
                issues.append("policy_api_url is required when using external API policy engine")
        
        if self.default_decision not in ["ALLOW", "DENY"]:
            issues.append("default_decision must be 'ALLOW' or 'DENY'")
        
        if self.policy_combining_algorithm not in ["DENY_OVERRIDES", "PERMIT_OVERRIDES", "FIRST_APPLICABLE"]:
            issues.append("Invalid policy_combining_algorithm")
        
        if self.policy_evaluation_timeout < 1:
            issues.append("policy_evaluation_timeout must be > 0")
        
        if self.max_policies_per_request < 1:
            issues.append("max_policies_per_request must be > 0")
        
        if self.max_attribute_size < 1:
            issues.append("max_attribute_size must be > 0")
        
        return issues


@dataclass
class SecurityLoggingConfig:
    """Security logging and auditing configuration."""
    
    # Basic logging settings
    enabled: bool = True
    log_level: SecurityLogLevel = SecurityLogLevel.DETAILED
    
    # Log format and structure
    log_format: str = "json"  # json, text
    include_request_body: bool = False
    include_response_body: bool = False
    max_body_size: int = 1024  # bytes
    
    # Log destinations
    log_to_file: bool = True
    log_to_console: bool = True
    log_to_syslog: bool = False
    log_to_external: bool = False
    
    # File logging settings
    log_file_path: str = "/var/log/microservices/security.log"
    log_file_max_size: int = 100 * 1024 * 1024  # 100MB
    log_file_backup_count: int = 10
    log_file_rotation_interval: str = "daily"  # daily, weekly, monthly
    
    # External logging settings
    external_log_url: Optional[str] = None
    external_log_token: Optional[str] = None
    external_log_batch_size: int = 100
    external_log_flush_interval: int = 30  # seconds
    
    # Audit trail settings
    enable_audit_trail: bool = True
    audit_trail_encryption: bool = True
    audit_trail_signing: bool = True
    audit_retention_days: int = 2555  # 7 years for compliance
    
    # Event filtering
    log_authentication_events: bool = True
    log_authorization_events: bool = True
    log_certificate_events: bool = True
    log_threat_events: bool = True
    log_configuration_events: bool = True
    
    def validate(self) -> List[str]:
        """Validate security logging configuration."""
        issues = []
        
        if self.log_format not in ["json", "text"]:
            issues.append("log_format must be 'json' or 'text'")
        
        if self.max_body_size < 0:
            issues.append("max_body_size must be >= 0")
        
        if self.log_to_file:
            log_dir = Path(self.log_file_path).parent
            if not log_dir.exists():
                issues.append(f"Log directory does not exist: {log_dir}")
        
        if self.log_file_max_size < 1024:
            issues.append("log_file_max_size must be >= 1024 bytes")
        
        if self.log_file_backup_count < 0:
            issues.append("log_file_backup_count must be >= 0")
        
        if self.log_file_rotation_interval not in ["daily", "weekly", "monthly"]:
            issues.append("log_file_rotation_interval must be 'daily', 'weekly', or 'monthly'")
        
        if self.log_to_external and not self.external_log_url:
            issues.append("external_log_url is required when log_to_external is enabled")
        
        if self.external_log_batch_size < 1:
            issues.append("external_log_batch_size must be > 0")
        
        if self.external_log_flush_interval < 1:
            issues.append("external_log_flush_interval must be > 0")
        
        if self.audit_retention_days < 1:
            issues.append("audit_retention_days must be > 0")
        
        return issues


@dataclass
class ThreatDetectionConfig:
    """Threat detection configuration."""
    
    # Basic threat detection settings
    enabled: bool = False
    detection_level: ThreatDetectionLevel = ThreatDetectionLevel.MEDIUM
    
    # Brute force detection
    brute_force_enabled: bool = True
    brute_force_threshold: int = 5  # failed attempts
    brute_force_window: int = 300   # 5 minutes
    brute_force_lockout: int = 900  # 15 minutes
    
    # Anomaly detection
    anomaly_detection_enabled: bool = True
    anomaly_threshold: float = 0.8  # confidence threshold
    anomaly_learning_period: int = 86400  # 24 hours
    
    # Geographic anomaly detection
    geo_anomaly_enabled: bool = False
    impossible_travel_threshold: int = 500  # km/h
    suspicious_countries: List[str] = field(default_factory=list)
    
    # Rate-based detection
    rate_anomaly_enabled: bool = True
    rate_anomaly_multiplier: float = 10.0  # X times normal rate
    rate_anomaly_window: int = 300  # 5 minutes
    
    # Privilege escalation detection
    privilege_escalation_enabled: bool = True
    privilege_escalation_threshold: int = 3  # attempts
    
    # Response settings
    auto_response_enabled: bool = True
    auto_block_enabled: bool = False  # Automatically block threats
    alert_threshold: float = 0.7  # Generate alert above this confidence
    
    # Integration settings
    siem_integration_enabled: bool = False
    siem_url: Optional[str] = None
    siem_token: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate threat detection configuration."""
        issues = []
        
        if self.brute_force_threshold < 1:
            issues.append("brute_force_threshold must be > 0")
        
        if self.brute_force_window < 60:
            issues.append("brute_force_window must be >= 60 seconds")
        
        if self.brute_force_lockout < 60:
            issues.append("brute_force_lockout must be >= 60 seconds")
        
        if not 0.0 <= self.anomaly_threshold <= 1.0:
            issues.append("anomaly_threshold must be between 0.0 and 1.0")
        
        if self.anomaly_learning_period < 3600:
            issues.append("anomaly_learning_period must be >= 3600 seconds (1 hour)")
        
        if self.impossible_travel_threshold < 1:
            issues.append("impossible_travel_threshold must be > 0")
        
        if self.rate_anomaly_multiplier < 1.0:
            issues.append("rate_anomaly_multiplier must be >= 1.0")
        
        if self.rate_anomaly_window < 60:
            issues.append("rate_anomaly_window must be >= 60 seconds")
        
        if self.privilege_escalation_threshold < 1:
            issues.append("privilege_escalation_threshold must be > 0")
        
        if not 0.0 <= self.alert_threshold <= 1.0:
            issues.append("alert_threshold must be between 0.0 and 1.0")
        
        if self.siem_integration_enabled and not self.siem_url:
            issues.append("siem_url is required when SIEM integration is enabled")
        
        return issues


@dataclass
class AdvancedSecurityConfig:
    """Advanced security configuration container."""
    
    # Component configurations
    mtls: MTLSConfig = field(default_factory=MTLSConfig)
    certificates: CertificateConfig = field(default_factory=CertificateConfig)
    rbac: RBACConfig = field(default_factory=RBACConfig)
    abac: ABACConfig = field(default_factory=ABACConfig)
    security_logging: SecurityLoggingConfig = field(default_factory=SecurityLoggingConfig)
    threat_detection: ThreatDetectionConfig = field(default_factory=ThreatDetectionConfig)
    
    # Global advanced security settings
    enabled: bool = False
    fail_secure: bool = True  # Fail to most restrictive policy
    defense_in_depth: bool = True  # Enable multiple security layers
    
    # Performance settings
    security_cache_enabled: bool = True
    security_cache_ttl: int = 300  # 5 minutes
    max_concurrent_security_checks: int = 1000
    
    @classmethod
    def from_env(cls) -> 'AdvancedSecurityConfig':
        """Create advanced security configuration from environment variables."""
        
        # mTLS configuration
        mtls_config = MTLSConfig(
            enabled=os.getenv('MTLS_ENABLED', 'false').lower() == 'true',
            mode=MTLSMode(os.getenv('MTLS_MODE', 'disabled')),
            server_cert_path=os.getenv('MTLS_SERVER_CERT_PATH'),
            server_key_path=os.getenv('MTLS_SERVER_KEY_PATH'),
            client_cert_path=os.getenv('MTLS_CLIENT_CERT_PATH'),
            client_key_path=os.getenv('MTLS_CLIENT_KEY_PATH'),
            ca_cert_path=os.getenv('MTLS_CA_CERT_PATH'),
            verify_client_cert=os.getenv('MTLS_VERIFY_CLIENT', 'true').lower() == 'true',
            verify_server_cert=os.getenv('MTLS_VERIFY_SERVER', 'true').lower() == 'true',
            handshake_timeout=int(os.getenv('MTLS_HANDSHAKE_TIMEOUT', '10')),
            connection_timeout=int(os.getenv('MTLS_CONNECTION_TIMEOUT', '30'))
        )
        
        # Certificate configuration
        cert_config = CertificateConfig(
            backend=CertificateBackend(os.getenv('CERT_BACKEND', 'filesystem')),
            auto_rotation_enabled=os.getenv('CERT_AUTO_ROTATION', 'true').lower() == 'true',
            rotation_threshold_days=int(os.getenv('CERT_ROTATION_THRESHOLD_DAYS', '30')),
            ca_url=os.getenv('CERT_CA_URL'),
            storage_path=os.getenv('CERT_STORAGE_PATH', '/etc/ssl/microservices'),
            vault_url=os.getenv('CERT_VAULT_URL'),
            vault_token=os.getenv('CERT_VAULT_TOKEN')
        )
        
        # RBAC configuration
        rbac_config = RBACConfig(
            enabled=os.getenv('RBAC_ENABLED', 'false').lower() == 'true',
            policy_engine=PolicyEngine(os.getenv('RBAC_POLICY_ENGINE', 'memory')),
            enable_role_hierarchy=os.getenv('RBAC_ROLE_HIERARCHY', 'true').lower() == 'true',
            default_deny=os.getenv('RBAC_DEFAULT_DENY', 'true').lower() == 'true',
            policy_file_path=os.getenv('RBAC_POLICY_FILE_PATH'),
            policy_database_url=os.getenv('RBAC_POLICY_DATABASE_URL'),
            policy_redis_url=os.getenv('RBAC_POLICY_REDIS_URL')
        )
        
        # ABAC configuration
        abac_config = ABACConfig(
            enabled=os.getenv('ABAC_ENABLED', 'false').lower() == 'true',
            policy_engine=PolicyEngine(os.getenv('ABAC_POLICY_ENGINE', 'memory')),
            default_decision=os.getenv('ABAC_DEFAULT_DECISION', 'DENY'),
            policy_combining_algorithm=os.getenv('ABAC_COMBINING_ALGORITHM', 'DENY_OVERRIDES'),
            enable_dynamic_attributes=os.getenv('ABAC_DYNAMIC_ATTRIBUTES', 'true').lower() == 'true',
            policy_file_path=os.getenv('ABAC_POLICY_FILE_PATH'),
            policy_database_url=os.getenv('ABAC_POLICY_DATABASE_URL')
        )
        
        # Security logging configuration
        logging_config = SecurityLoggingConfig(
            enabled=os.getenv('SECURITY_LOGGING_ENABLED', 'true').lower() == 'true',
            log_level=SecurityLogLevel(os.getenv('SECURITY_LOG_LEVEL', 'detailed')),
            log_format=os.getenv('SECURITY_LOG_FORMAT', 'json'),
            log_file_path=os.getenv('SECURITY_LOG_FILE_PATH', '/var/log/microservices/security.log'),
            enable_audit_trail=os.getenv('SECURITY_AUDIT_TRAIL', 'true').lower() == 'true',
            external_log_url=os.getenv('SECURITY_EXTERNAL_LOG_URL')
        )
        
        # Threat detection configuration
        threat_config = ThreatDetectionConfig(
            enabled=os.getenv('THREAT_DETECTION_ENABLED', 'false').lower() == 'true',
            detection_level=ThreatDetectionLevel(os.getenv('THREAT_DETECTION_LEVEL', 'medium')),
            brute_force_enabled=os.getenv('THREAT_BRUTE_FORCE_ENABLED', 'true').lower() == 'true',
            brute_force_threshold=int(os.getenv('THREAT_BRUTE_FORCE_THRESHOLD', '5')),
            anomaly_detection_enabled=os.getenv('THREAT_ANOMALY_ENABLED', 'true').lower() == 'true',
            auto_response_enabled=os.getenv('THREAT_AUTO_RESPONSE', 'true').lower() == 'true'
        )
        
        return cls(
            mtls=mtls_config,
            certificates=cert_config,
            rbac=rbac_config,
            abac=abac_config,
            security_logging=logging_config,
            threat_detection=threat_config,
            enabled=os.getenv('ADVANCED_SECURITY_ENABLED', 'false').lower() == 'true',
            fail_secure=os.getenv('SECURITY_FAIL_SECURE', 'true').lower() == 'true',
            defense_in_depth=os.getenv('SECURITY_DEFENSE_IN_DEPTH', 'true').lower() == 'true'
        )
    
    def validate(self) -> List[str]:
        """Validate all advanced security configuration."""
        issues = []
        
        # Validate individual components
        issues.extend(self.mtls.validate())
        issues.extend(self.certificates.validate())
        issues.extend(self.rbac.validate())
        issues.extend(self.abac.validate())
        issues.extend(self.security_logging.validate())
        issues.extend(self.threat_detection.validate())
        
        # Cross-component validation
        if self.mtls.enabled and not self.certificates.auto_rotation_enabled:
            issues.append("Certificate auto-rotation should be enabled when mTLS is active")
        
        if (self.rbac.enabled or self.abac.enabled) and not self.security_logging.enabled:
            issues.append("Security logging should be enabled when RBAC/ABAC is active")
        
        if self.threat_detection.enabled and not self.security_logging.log_authentication_events:
            issues.append("Authentication event logging should be enabled for threat detection")
        
        # Performance validation
        if self.max_concurrent_security_checks < 1:
            issues.append("max_concurrent_security_checks must be > 0")
        
        if self.security_cache_ttl < 0:
            issues.append("security_cache_ttl must be >= 0")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enabled': self.enabled,
            'fail_secure': self.fail_secure,
            'defense_in_depth': self.defense_in_depth,
            'security_cache_enabled': self.security_cache_enabled,
            'security_cache_ttl': self.security_cache_ttl,
            'max_concurrent_security_checks': self.max_concurrent_security_checks,
            'mtls': {k: v.value if isinstance(v, Enum) else v for k, v in self.mtls.__dict__.items()},
            'certificates': {k: v.value if isinstance(v, Enum) else v for k, v in self.certificates.__dict__.items()},
            'rbac': {k: v.value if isinstance(v, Enum) else v for k, v in self.rbac.__dict__.items()},
            'abac': {k: v.value if isinstance(v, Enum) else v for k, v in self.abac.__dict__.items()},
            'security_logging': {k: v.value if isinstance(v, Enum) else v for k, v in self.security_logging.__dict__.items()},
            'threat_detection': {k: v.value if isinstance(v, Enum) else v for k, v in self.threat_detection.__dict__.items()}
        }
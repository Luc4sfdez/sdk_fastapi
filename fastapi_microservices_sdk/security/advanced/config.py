"""
Advanced Security Configuration for FastAPI Microservices SDK.
This module provides comprehensive configuration management for advanced security features
including mTLS, RBAC, ABAC, threat detection, and security logging.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import yaml
from pydantic import BaseModel, validator, Field

from ...exceptions import ConfigurationError


class SecurityLevel(Enum):
    """Security levels for different environments."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"


class CertificateType(Enum):
    """Certificate types for mTLS configuration."""
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    ECC_256 = "ecc_256"
    ECC_384 = "ecc_384"


class ThreatDetectionMode(Enum):
    """Threat detection operation modes."""
    DISABLED = "disabled"
    MONITOR = "monitor"
    BLOCK = "block"
    ADAPTIVE = "adaptive"


@dataclass
class MTLSConfig:
    """Configuration for Mutual TLS."""
    enabled: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    ca_path: Optional[str] = None
    cert_type: CertificateType = CertificateType.RSA_2048
    verify_mode: str = "CERT_REQUIRED"
    check_hostname: bool = True
    ciphers: Optional[str] = None
    protocols: List[str] = field(default_factory=lambda: ["TLSv1.2", "TLSv1.3"])
    
    # Certificate validation settings
    verify_chain: bool = True
    check_revocation: bool = True
    allow_self_signed: bool = False
    max_chain_depth: int = 10
    
    # Rotation settings
    auto_rotate: bool = True
    rotation_threshold_days: int = 30
    rotation_check_interval: int = 3600  # seconds

    def __post_init__(self):
        """Validate mTLS configuration."""
        if self.enabled:
            if not self.cert_path or not self.key_path:
                raise ConfigurationError("mTLS enabled but cert_path or key_path not provided")
            if not Path(self.cert_path).exists():
                raise ConfigurationError(f"Certificate file not found: {self.cert_path}")
            if not Path(self.key_path).exists():
                raise ConfigurationError(f"Private key file not found: {self.key_path}")
            if self.ca_path and not Path(self.ca_path).exists():
                raise ConfigurationError(f"CA certificate file not found: {self.ca_path}")


@dataclass
class RBACConfig:
    """Configuration for Role-Based Access Control."""
    enabled: bool = False
    roles_file: Optional[str] = None
    permissions_file: Optional[str] = None
    default_role: str = "user"
    allow_role_inheritance: bool = True
    max_role_depth: int = 5
    cache_ttl: int = 300  # seconds
    
    # Role assignment settings
    auto_assign_default: bool = True
    require_explicit_permissions: bool = False
    case_sensitive_roles: bool = False
    
    # Integration settings
    jwt_role_claim: str = "roles"
    jwt_permission_claim: str = "permissions"

    def __post_init__(self):
        """Validate RBAC configuration."""
        if self.enabled:
            if self.roles_file and not Path(self.roles_file).exists():
                raise ConfigurationError(f"Roles file not found: {self.roles_file}")
            if self.permissions_file and not Path(self.permissions_file).exists():
                raise ConfigurationError(f"Permissions file not found: {self.permissions_file}")
            if self.max_role_depth < 1:
                raise ConfigurationError("max_role_depth must be at least 1")


@dataclass
class ABACConfig:
    """Configuration for Attribute-Based Access Control."""
    enabled: bool = False
    policies_file: Optional[str] = None
    attributes_file: Optional[str] = None
    default_decision: str = "DENY"
    policy_evaluation_timeout: float = 1.0  # seconds
    cache_ttl: int = 300  # seconds
    
    # Policy settings
    allow_dynamic_policies: bool = False
    policy_precedence: str = "deny_overrides"  # deny_overrides, permit_overrides, first_applicable
    require_all_attributes: bool = False
    
    # Attribute providers
    user_attribute_providers: List[str] = field(default_factory=list)
    resource_attribute_providers: List[str] = field(default_factory=list)
    environment_attribute_providers: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate ABAC configuration."""
        if self.enabled:
            if self.policies_file and not Path(self.policies_file).exists():
                raise ConfigurationError(f"Policies file not found: {self.policies_file}")
            if self.attributes_file and not Path(self.attributes_file).exists():
                raise ConfigurationError(f"Attributes file not found: {self.attributes_file}")
            if self.default_decision not in ["ALLOW", "DENY"]:
                raise ConfigurationError("default_decision must be 'ALLOW' or 'DENY'")
            if self.policy_precedence not in ["deny_overrides", "permit_overrides", "first_applicable"]:
                raise ConfigurationError("Invalid policy_precedence value")


@dataclass
class SecurityLoggingConfig:
    """Configuration for Security Logging."""
    enabled: bool = True
    log_level: str = "INFO"
    log_format: str = "json"  # json, text
    log_file: Optional[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 5
    
    # Event logging settings
    log_authentication: bool = True
    log_authorization: bool = True
    log_security_violations: bool = True
    log_certificate_events: bool = True
    log_threat_events: bool = True
    
    # Audit trail settings
    enable_audit_trail: bool = True
    audit_trail_encryption: bool = True
    audit_retention_days: int = 365
    
    # Performance settings
    async_logging: bool = True
    buffer_size: int = 1000
    flush_interval: float = 5.0  # seconds

    def __post_init__(self):
        """Validate security logging configuration."""
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ConfigurationError(f"Invalid log_level: {self.log_level}")
        if self.log_format not in ["json", "text"]:
            raise ConfigurationError(f"Invalid log_format: {self.log_format}")
        if self.max_file_size < 1024:  # Minimum 1KB
            raise ConfigurationError("max_file_size must be at least 1024 bytes")


@dataclass
class ThreatDetectionConfig:
    """Configuration for Threat Detection."""
    enabled: bool = False
    mode: ThreatDetectionMode = ThreatDetectionMode.MONITOR
    rules_file: Optional[str] = None
    
    # Brute force detection
    brute_force_enabled: bool = True
    brute_force_threshold: int = 5
    brute_force_window: int = 300  # seconds
    brute_force_lockout: int = 900  # seconds
    
    # Anomaly detection
    anomaly_detection_enabled: bool = True
    anomaly_threshold: float = 0.8
    learning_period_days: int = 7
    
    # Geographic anomaly detection
    geo_anomaly_enabled: bool = False
    impossible_travel_threshold: float = 500.0  # km/h
    
    # Attack signature detection
    signature_detection_enabled: bool = True
    signature_database: Optional[str] = None
    
    # Response settings
    auto_block_enabled: bool = False
    alert_threshold: float = 0.7
    escalation_threshold: float = 0.9

    def __post_init__(self):
        """Validate threat detection configuration."""
        if self.enabled:
            if self.rules_file and not Path(self.rules_file).exists():
                raise ConfigurationError(f"Threat rules file not found: {self.rules_file}")
            if self.signature_database and not Path(self.signature_database).exists():
                raise ConfigurationError(f"Signature database not found: {self.signature_database}")
            if not 0 <= self.anomaly_threshold <= 1:
                raise ConfigurationError("anomaly_threshold must be between 0 and 1")
            if not 0 <= self.alert_threshold <= 1:
                raise ConfigurationError("alert_threshold must be between 0 and 1")


@dataclass
class CertificateManagementConfig:
    """Configuration for Certificate Management."""
    enabled: bool = False
    storage_path: str = "./certificates"
    ca_url: Optional[str] = None
    ca_auth_method: str = "token"  # token, cert, basic
    ca_credentials: Dict[str, str] = field(default_factory=dict)
    
    # Certificate settings
    default_key_size: int = 2048
    default_validity_days: int = 365
    certificate_format: str = "PEM"  # PEM, DER
    
    # Rotation settings
    auto_rotation_enabled: bool = True
    rotation_threshold_days: int = 30
    rotation_check_interval: int = 3600  # seconds
    backup_old_certificates: bool = True
    
    # Validation settings
    verify_certificate_chain: bool = True
    check_certificate_revocation: bool = True
    ocsp_enabled: bool = False
    crl_check_enabled: bool = True

    def __post_init__(self):
        """Validate certificate management configuration."""
        if self.enabled:
            storage_path = Path(self.storage_path)
            if not storage_path.exists():
                storage_path.mkdir(parents=True, exist_ok=True)
            if self.default_key_size < 2048:
                raise ConfigurationError("default_key_size must be at least 2048 bits")
            if self.default_validity_days < 1:
                raise ConfigurationError("default_validity_days must be at least 1")


class AdvancedSecurityConfig(BaseModel):
    """
    Comprehensive configuration for advanced security features.
    This class manages configuration for all advanced security components
    including mTLS, RBAC, ABAC, security logging, threat detection, and
    certificate management.
    """
    # Global security settings
    security_level: SecurityLevel = SecurityLevel.STANDARD
    enabled_features: List[str] = Field(default_factory=list)
    
    # Component configurations
    mtls: MTLSConfig = Field(default_factory=MTLSConfig)
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    abac: ABACConfig = Field(default_factory=ABACConfig)
    security_logging: SecurityLoggingConfig = Field(default_factory=SecurityLoggingConfig)
    threat_detection: ThreatDetectionConfig = Field(default_factory=ThreatDetectionConfig)
    certificate_management: CertificateManagementConfig = Field(default_factory=CertificateManagementConfig)
    
    # Integration settings
    fail_secure: bool = True
    graceful_degradation: bool = True
    security_headers_integration: bool = True
    rate_limiting_integration: bool = True

    class Config:
        extra = "forbid"
        validate_assignment = True

    @validator('enabled_features')
    def validate_enabled_features(cls, v):
        """Validate enabled features list."""
        valid_features = {
            "mtls", "rbac", "abac", "security_logging", 
            "threat_detection", "certificate_management"
        }
        for feature in v:
            if feature not in valid_features:
                raise ValueError(f"Invalid feature: {feature}. Valid features: {valid_features}")
        return v

    def __init__(self, **data):
        """Initialize advanced security configuration."""
        super().__init__(**data)
        self._apply_security_level_defaults()
        self._validate_feature_dependencies()

    def _apply_security_level_defaults(self):
        """Apply security level-specific defaults."""
        if self.security_level == SecurityLevel.MINIMAL:
            self.security_logging.enabled = True
            self.security_logging.log_level = "WARNING"
        elif self.security_level == SecurityLevel.STANDARD:
            self.security_logging.enabled = True
            self.security_logging.log_level = "INFO"
            self.threat_detection.enabled = True
            self.threat_detection.mode = ThreatDetectionMode.MONITOR
        elif self.security_level == SecurityLevel.HIGH:
            self.mtls.enabled = True
            self.rbac.enabled = True
            self.security_logging.enabled = True
            self.security_logging.log_level = "INFO"
            self.threat_detection.enabled = True
            self.threat_detection.mode = ThreatDetectionMode.BLOCK
            self.certificate_management.enabled = True
        elif self.security_level == SecurityLevel.MAXIMUM:
            self.mtls.enabled = True
            self.rbac.enabled = True
            self.abac.enabled = True
            self.security_logging.enabled = True
            self.security_logging.log_level = "DEBUG"
            self.security_logging.enable_audit_trail = True
            self.security_logging.audit_trail_encryption = True
            self.threat_detection.enabled = True
            self.threat_detection.mode = ThreatDetectionMode.ADAPTIVE
            self.threat_detection.auto_block_enabled = True
            self.certificate_management.enabled = True
            self.certificate_management.auto_rotation_enabled = True

    def _validate_feature_dependencies(self):
        """Validate dependencies between security features."""
        # mTLS requires certificate management
        if self.mtls.enabled and not self.certificate_management.enabled:
            raise ConfigurationError("mTLS requires certificate_management to be enabled")
        
        # ABAC typically works better with RBAC
        if self.abac.enabled and not self.rbac.enabled:
            import warnings
            warnings.warn("ABAC is enabled without RBAC. Consider enabling RBAC for better access control.")
        
        # Threat detection requires security logging
        if self.threat_detection.enabled and not self.security_logging.enabled:
            raise ConfigurationError("Threat detection requires security_logging to be enabled")

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'AdvancedSecurityConfig':
        """Load configuration from file (JSON or YAML)."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ConfigurationError(f"Unsupported configuration file format: {config_path.suffix}")
            return cls(**data)
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")

    @classmethod
    def from_env(cls, prefix: str = "ADVANCED_SECURITY_") -> 'AdvancedSecurityConfig':
        """Load configuration from environment variables."""
        config_data = {}
        
        # Map environment variables to configuration structure
        env_mappings = {
            f"{prefix}SECURITY_LEVEL": ("security_level", str),
            f"{prefix}MTLS_ENABLED": ("mtls.enabled", bool),
            f"{prefix}MTLS_CERT_PATH": ("mtls.cert_path", str),
            f"{prefix}MTLS_KEY_PATH": ("mtls.key_path", str),
            f"{prefix}MTLS_CA_PATH": ("mtls.ca_path", str),
            f"{prefix}RBAC_ENABLED": ("rbac.enabled", bool),
            f"{prefix}RBAC_ROLES_FILE": ("rbac.roles_file", str),
            f"{prefix}ABAC_ENABLED": ("abac.enabled", bool),
            f"{prefix}ABAC_POLICIES_FILE": ("abac.policies_file", str),
            f"{prefix}THREAT_DETECTION_ENABLED": ("threat_detection.enabled", bool),
            f"{prefix}THREAT_DETECTION_MODE": ("threat_detection.mode", str),
        }
        
        for env_var, (config_path, config_type) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert value to appropriate type
                if config_type == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_type == int:
                    value = int(value)
                elif config_type == float:
                    value = float(value)
                
                # Set nested configuration value
                cls._set_nested_value(config_data, config_path, value)
        
        return cls(**config_data)

    @staticmethod
    def _set_nested_value(data: dict, path: str, value: Any):
        """Set a nested dictionary value using dot notation."""
        keys = path.split('.')
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()

    def to_file(self, config_path: Union[str, Path], format: str = "yaml"):
        """Save configuration to file."""
        config_path = Path(config_path)
        config_data = self.to_dict()
        
        try:
            with open(config_path, 'w') as f:
                if format.lower() in ['yaml', 'yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ConfigurationError(f"Unsupported format: {format}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}")

    def validate_configuration(self) -> List[str]:
        """Validate the entire configuration and return any warnings."""
        warnings = []
        
        # Check for security level consistency
        if self.security_level == SecurityLevel.MAXIMUM:
            if not self.mtls.enabled:
                warnings.append("MAXIMUM security level should have mTLS enabled")
            if not self.abac.enabled:
                warnings.append("MAXIMUM security level should have ABAC enabled")
        
        # Check certificate paths if mTLS is enabled
        if self.mtls.enabled:
            if not self.mtls.cert_path or not Path(self.mtls.cert_path).exists():
                warnings.append("mTLS enabled but certificate path is invalid")
        
        # Check policy files if RBAC/ABAC are enabled
        if self.rbac.enabled and self.rbac.roles_file:
            if not Path(self.rbac.roles_file).exists():
                warnings.append("RBAC enabled but roles file not found")
        
        if self.abac.enabled and self.abac.policies_file:
            if not Path(self.abac.policies_file).exists():
                warnings.append("ABAC enabled but policies file not found")
        
        return warnings

    def get_enabled_features(self) -> List[str]:
        """Get list of currently enabled security features."""
        enabled = []
        if self.mtls.enabled:
            enabled.append("mtls")
        if self.rbac.enabled:
            enabled.append("rbac")
        if self.abac.enabled:
            enabled.append("abac")
        if self.security_logging.enabled:
            enabled.append("security_logging")
        if self.threat_detection.enabled:
            enabled.append("threat_detection")
        if self.certificate_management.enabled:
            enabled.append("certificate_management")
        return enabled

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a specific security feature is enabled."""
        feature_map = {
            "mtls": self.mtls.enabled,
            "rbac": self.rbac.enabled,
            "abac": self.abac.enabled,
            "security_logging": self.security_logging.enabled,
            "threat_detection": self.threat_detection.enabled,
            "certificate_management": self.certificate_management.enabled,
        }
        return feature_map.get(feature, False)
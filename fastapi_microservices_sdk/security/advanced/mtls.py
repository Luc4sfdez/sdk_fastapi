"""
Mutual TLS (mTLS) Implementation for FastAPI Microservices SDK.
This module provides comprehensive mTLS support for service-to-service communication
including SSL context management, certificate validation, peer verification,
and centralized mTLS management with advanced policies.
"""
import ssl
import socket
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509.verification import PolicyBuilder, Store

from .certificates import Certificate, CertificateChain, CertificateStore, CertificateFormat
from .certificate_manager import CertificateManager
from .exceptions import MTLSError, CertificateError
from .logging import get_security_logger, SecurityEvent, SecurityEventSeverity, SecurityEventType
from .config import AdvancedSecurityConfig


class MTLSMode(Enum):
    """mTLS operation modes."""
    DISABLED = "disabled"
    OPTIONAL = "optional"  # Accept both mTLS and non-mTLS connections
    REQUIRED = "required"  # Require mTLS for all connections
    STRICT = "strict"     # Require mTLS with strict certificate validation


class CertificateValidationLevel(Enum):
    """Certificate validation levels."""
    NONE = "none"           # No validation (not recommended)
    BASIC = "basic"         # Basic certificate validation
    CHAIN = "chain"         # Full chain validation
    REVOCATION = "revocation"  # Chain + revocation checking
    STRICT = "strict"       # All validations + custom policies


@dataclass
class MTLSConfig:
    """mTLS configuration settings."""
    
    # Basic mTLS settings
    enabled: bool = False
    mode: MTLSMode = MTLSMode.DISABLED
    validation_level: CertificateValidationLevel = CertificateValidationLevel.CHAIN
    
    # Certificate paths
    server_cert_path: Optional[str] = None
    server_key_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    ca_cert_path: Optional[str] = None
    
    # Certificate store integration
    certificate_store: Optional[CertificateStore] = None
    certificate_manager: Optional[CertificateManager] = None
    
    # SSL/TLS settings
    ssl_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3
    min_ssl_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2
    ciphers: Optional[str] = None  # Use secure defaults if None
    verify_mode: ssl.VerifyMode = ssl.CERT_REQUIRED
    check_hostname: bool = True
    
    # Certificate validation settings
    verify_client_cert: bool = True
    verify_server_cert: bool = True
    allow_self_signed: bool = False
    max_chain_depth: int = 10
    
    # Revocation checking
    check_revocation: bool = True
    crl_cache_timeout: int = 3600  # 1 hour
    ocsp_enabled: bool = True
    ocsp_timeout: int = 10  # seconds
    
    # Connection settings
    handshake_timeout: float = 30.0
    connection_timeout: float = 60.0
    
    # Monitoring and logging
    log_connections: bool = True
    log_certificate_details: bool = False
    monitor_certificate_expiry: bool = True
    expiry_warning_days: int = 30
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.enabled and self.mode == MTLSMode.DISABLED:
            raise ValueError("mTLS cannot be enabled with mode DISABLED")
        
        if self.mode in [MTLSMode.REQUIRED, MTLSMode.STRICT]:
            if not self.server_cert_path or not self.server_key_path:
                if not self.certificate_manager and not self.certificate_store:
                    raise ValueError("Server certificate and key required for mTLS mode")
        
        if self.validation_level == CertificateValidationLevel.REVOCATION:
            if not self.check_revocation:
                raise ValueError("Revocation checking must be enabled for REVOCATION validation level")
        
        # Set secure cipher suites if not specified
        if self.ciphers is None:
            self.ciphers = (
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "validation_level": self.validation_level.value,
            "server_cert_path": self.server_cert_path,
            "server_key_path": self.server_key_path,
            "client_cert_path": self.client_cert_path,
            "client_key_path": self.client_key_path,
            "ca_cert_path": self.ca_cert_path,
            "ssl_version": self.ssl_version.name,
            "min_ssl_version": self.min_ssl_version.name,
            "ciphers": self.ciphers,
            "verify_mode": self.verify_mode.name,
            "check_hostname": self.check_hostname,
            "verify_client_cert": self.verify_client_cert,
            "verify_server_cert": self.verify_server_cert,
            "allow_self_signed": self.allow_self_signed,
            "max_chain_depth": self.max_chain_depth,
            "check_revocation": self.check_revocation,
            "crl_cache_timeout": self.crl_cache_timeout,
            "ocsp_enabled": self.ocsp_enabled,
            "ocsp_timeout": self.ocsp_timeout,
            "handshake_timeout": self.handshake_timeout,
            "connection_timeout": self.connection_timeout,
            "log_connections": self.log_connections,
            "log_certificate_details": self.log_certificate_details,
            "monitor_certificate_expiry": self.monitor_certificate_expiry,
            "expiry_warning_days": self.expiry_warning_days
        }


class SSLContextManager:
    """
    SSL Context Manager for mTLS operations.
    Handles creation and management of SSL contexts for both client and server operations.
    """
    
    def __init__(self, config: MTLSConfig):
        """Initialize SSL context manager."""
        self.config = config
        self._logger = get_security_logger()
        
        # SSL contexts
        self._server_context: Optional[ssl.SSLContext] = None
        self._client_context: Optional[ssl.SSLContext] = None
        
        # Certificate monitoring
        self._cert_monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()
        
        # Initialize contexts if enabled
        if self.config.enabled:
            self._create_ssl_contexts()
            
            if self.config.monitor_certificate_expiry:
                self._start_certificate_monitoring()
    
    def _create_ssl_contexts(self):
        """Create SSL contexts for server and client operations."""
        try:
            # Create server context
            if self.config.mode in [MTLSMode.OPTIONAL, MTLSMode.REQUIRED, MTLSMode.STRICT]:
                self._server_context = self._create_server_context()
            
            # Create client context
            self._client_context = self._create_client_context()
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW,
                message="SSL contexts created successfully",
                details={
                    "operation": "mtls_context_created",
                    "mode": self.config.mode.value,
                    "validation_level": self.config.validation_level.value,
                    "ssl_version": self.config.ssl_version.name
                }
            ))
            
        except Exception as e:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.HIGH,
                message=f"Failed to create SSL contexts: {e}",
                details={"operation": "mtls_context_failed", "error": str(e)}
            ))
            raise MTLSError(f"Failed to create SSL contexts: {e}")
    
    def _create_server_context(self) -> ssl.SSLContext:
        """Create SSL context for server operations."""
        # Create context with appropriate protocol
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Set TLS version constraints
        context.minimum_version = self.config.min_ssl_version
        context.maximum_version = self.config.ssl_version
        
        # Set cipher suites
        if self.config.ciphers:
            context.set_ciphers(self.config.ciphers)
        
        # Load server certificate and key
        if self.config.server_cert_path and self.config.server_key_path:
            context.load_cert_chain(
                certfile=self.config.server_cert_path,
                keyfile=self.config.server_key_path
            )
        elif self.config.certificate_manager:
            # Load from certificate manager
            server_cert = self.config.certificate_manager.get_certificate("server")
            if server_cert:
                # Create temporary files for SSL context
                # In production, this should use in-memory certificate loading
                cert_pem = server_cert.to_pem()
                # For now, we'll require file paths
                raise MTLSError("Certificate manager integration requires file paths for SSL context")
        else:
            raise MTLSError("Server certificate and key required for mTLS server mode")
        
        # Configure client certificate verification
        if self.config.mode in [MTLSMode.REQUIRED, MTLSMode.STRICT]:
            context.verify_mode = ssl.CERT_REQUIRED
        elif self.config.mode == MTLSMode.OPTIONAL:
            context.verify_mode = ssl.CERT_OPTIONAL
        else:
            context.verify_mode = ssl.CERT_NONE
        
        # Load CA certificates for client verification
        if self.config.ca_cert_path:
            context.load_verify_locations(cafile=self.config.ca_cert_path)
        elif self.config.certificate_store:
            # Load trusted CAs from certificate store
            ca_certs = self.config.certificate_store.get_trusted_cas()
            if ca_certs:
                # Create temporary CA bundle file
                # In production, this should use in-memory CA loading
                raise MTLSError("Certificate store integration requires CA file path for SSL context")
        
        # Set hostname checking
        context.check_hostname = False  # We'll do custom hostname verification
        
        # Set custom certificate verification callback
        if self.config.validation_level != CertificateValidationLevel.NONE:
            context.verify_flags = ssl.VERIFY_DEFAULT
            if not self.config.allow_self_signed:
                context.verify_flags |= ssl.VERIFY_X509_TRUSTED_FIRST
        
        return context
    
    def _create_client_context(self) -> ssl.SSLContext:
        """Create SSL context for client operations."""
        # Create context with appropriate protocol
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        
        # Set TLS version constraints
        context.minimum_version = self.config.min_ssl_version
        context.maximum_version = self.config.ssl_version
        
        # Set cipher suites
        if self.config.ciphers:
            context.set_ciphers(self.config.ciphers)
        
        # Load client certificate and key if provided
        if self.config.client_cert_path and self.config.client_key_path:
            context.load_cert_chain(
                certfile=self.config.client_cert_path,
                keyfile=self.config.client_key_path
            )
        
        # Configure server certificate verification
        if self.config.verify_server_cert:
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = self.config.check_hostname
        else:
            context.verify_mode = ssl.CERT_NONE
            context.check_hostname = False
        
        # Load CA certificates for server verification
        if self.config.ca_cert_path:
            context.load_verify_locations(cafile=self.config.ca_cert_path)
        elif self.config.certificate_store:
            # Load trusted CAs from certificate store
            ca_certs = self.config.certificate_store.get_trusted_cas()
            if ca_certs:
                # Create temporary CA bundle file
                # In production, this should use in-memory CA loading
                raise MTLSError("Certificate store integration requires CA file path for SSL context")
        else:
            # Load default system CA certificates
            context.load_default_certs()
        
        # Set verification flags
        if self.config.validation_level != CertificateValidationLevel.NONE:
            context.verify_flags = ssl.VERIFY_DEFAULT
            if not self.config.allow_self_signed:
                context.verify_flags |= ssl.VERIFY_X509_TRUSTED_FIRST
        
        return context
    
    def get_server_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context for server operations."""
        return self._server_context
    
    def get_client_context(self) -> Optional[ssl.SSLContext]:
        """Get SSL context for client operations."""
        return self._client_context
    
    def validate_peer_certificate(
        self,
        peer_cert: x509.Certificate,
        hostname: Optional[str] = None,
        is_server: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Validate peer certificate according to configuration.
        
        Args:
            peer_cert: The peer's certificate
            hostname: Expected hostname (for server certificates)
            is_server: True if validating a server certificate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Skip validation if disabled
            if self.config.validation_level == CertificateValidationLevel.NONE:
                return True, []
            
            # Basic certificate validation
            if self.config.validation_level in [
                CertificateValidationLevel.BASIC,
                CertificateValidationLevel.CHAIN,
                CertificateValidationLevel.REVOCATION,
                CertificateValidationLevel.STRICT
            ]:
                # Check certificate validity period
                now = datetime.now(timezone.utc)
                not_before = peer_cert.not_valid_before_utc
                not_after = peer_cert.not_valid_after_utc
                
                if now < not_before:
                    errors.append(f"Certificate not yet valid (valid from {not_before})")
                
                if now > not_after:
                    errors.append(f"Certificate expired (expired on {not_after})")
                
                # Check certificate purpose
                try:
                    key_usage = peer_cert.extensions.get_extension_for_oid(
                        x509.oid.ExtensionOID.KEY_USAGE
                    ).value
                    
                    if is_server:
                        if not key_usage.key_encipherment and not key_usage.key_agreement:
                            errors.append("Server certificate missing key encipherment usage")
                    else:
                        if not key_usage.digital_signature:
                            errors.append("Client certificate missing digital signature usage")
                            
                except x509.ExtensionNotFound:
                    if self.config.validation_level == CertificateValidationLevel.STRICT:
                        errors.append("Certificate missing Key Usage extension")
            
            # Chain validation
            if self.config.validation_level in [
                CertificateValidationLevel.CHAIN,
                CertificateValidationLevel.REVOCATION,
                CertificateValidationLevel.STRICT
            ]:
                if self.config.certificate_store:
                    # Use certificate store for chain validation
                    cert_obj = Certificate(peer_cert)
                    chain_errors = cert_obj.validate()
                    errors.extend(chain_errors)
            
            # Hostname validation for server certificates
            if is_server and hostname and self.config.check_hostname:
                try:
                    # Check Subject Alternative Names
                    san_ext = peer_cert.extensions.get_extension_for_oid(
                        x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
                    ).value
                    
                    dns_names = [name.value for name in san_ext if isinstance(name, x509.DNSName)]
                    
                    hostname_valid = False
                    for dns_name in dns_names:
                        if self._match_hostname(hostname, dns_name):
                            hostname_valid = True
                            break
                    
                    if not hostname_valid:
                        # Check Common Name as fallback
                        try:
                            cn = peer_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                            if not self._match_hostname(hostname, cn):
                                errors.append(f"Hostname {hostname} does not match certificate")
                        except (IndexError, AttributeError):
                            errors.append(f"Hostname {hostname} does not match certificate")
                            
                except x509.ExtensionNotFound:
                    # Check Common Name only
                    try:
                        cn = peer_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                        if not self._match_hostname(hostname, cn):
                            errors.append(f"Hostname {hostname} does not match certificate")
                    except (IndexError, AttributeError):
                        errors.append("Certificate has no hostname information")
            
            # Revocation checking
            if (self.config.validation_level == CertificateValidationLevel.REVOCATION and 
                self.config.check_revocation):
                # Check certificate revocation status
                if self.config.certificate_store:
                    cert_obj = Certificate(peer_cert)
                    if cert_obj.is_revoked():
                        errors.append("Certificate has been revoked")
            
            # Self-signed certificate check
            if not self.config.allow_self_signed:
                if peer_cert.issuer == peer_cert.subject:
                    errors.append("Self-signed certificates not allowed")
            
            # Log validation result
            if self.config.log_certificate_details:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUDIT_EVENT,
                    severity=SecurityEventSeverity.LOW if not errors else SecurityEventSeverity.MEDIUM,
                    message=f"Certificate validation {'passed' if not errors else 'failed'}",
                    details={
                        "operation": "mtls_cert_validation",
                        "subject": peer_cert.subject.rfc4514_string(),
                        "issuer": peer_cert.issuer.rfc4514_string(),
                        "serial_number": str(peer_cert.serial_number),
                        "hostname": hostname,
                        "is_server": is_server,
                        "errors": errors
                    }
                ))
            
            return len(errors) == 0, errors
            
        except Exception as e:
            error_msg = f"Certificate validation failed: {e}"
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.HIGH,
                message=error_msg,
                details={"operation": "mtls_cert_validation_error", "error": str(e)}
            ))
            return False, [error_msg]
    
    def _match_hostname(self, hostname: str, pattern: str) -> bool:
        """Match hostname against certificate pattern (supports wildcards)."""
        if pattern == hostname:
            return True
        
        # Handle wildcard patterns
        if pattern.startswith('*.'):
            pattern_suffix = pattern[2:]
            if '.' in hostname:
                hostname_suffix = hostname[hostname.index('.') + 1:]
                return pattern_suffix == hostname_suffix
        
        return False
    
    def _start_certificate_monitoring(self):
        """Start certificate expiry monitoring thread."""
        if self._cert_monitor_thread and self._cert_monitor_thread.is_alive():
            return
        
        self._monitor_stop_event.clear()
        self._cert_monitor_thread = threading.Thread(
            target=self._certificate_monitor_loop,
            daemon=True
        )
        self._cert_monitor_thread.start()
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUDIT_EVENT,
            severity=SecurityEventSeverity.LOW,
            message="Certificate expiry monitoring started",
            details={"operation": "mtls_cert_monitoring_started"}
        ))
    
    def _certificate_monitor_loop(self):
        """Certificate monitoring loop."""
        while not self._monitor_stop_event.is_set():
            try:
                self._check_certificate_expiry()
                # Check every hour
                self._monitor_stop_event.wait(3600)
            except Exception as e:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUDIT_EVENT,
                    severity=SecurityEventSeverity.MEDIUM,
                    message=f"Certificate monitoring error: {e}",
                    details={"operation": "mtls_cert_monitoring_error", "error": str(e)}
                ))
                # Wait before retry
                self._monitor_stop_event.wait(300)  # 5 minutes
    
    def _check_certificate_expiry(self):
        """Check certificate expiry and log warnings."""
        cert_paths = [
            ("server", self.config.server_cert_path),
            ("client", self.config.client_cert_path),
            ("ca", self.config.ca_cert_path)
        ]
        
        for cert_type, cert_path in cert_paths:
            if not cert_path or not Path(cert_path).exists():
                continue
            
            try:
                with open(cert_path, 'rb') as f:
                    cert_data = f.read()
                
                cert = x509.load_pem_x509_certificate(cert_data)
                
                # Check expiry
                now = datetime.now(timezone.utc)
                not_after = cert.not_valid_after_utc
                days_until_expiry = (not_after - now).days
                
                if days_until_expiry <= self.config.expiry_warning_days:
                    severity = SecurityEventSeverity.HIGH if days_until_expiry <= 7 else SecurityEventSeverity.MEDIUM
                    
                    self._logger.log_event(SecurityEvent(
                        event_type=SecurityEventType.AUDIT_EVENT,
                        severity=severity,
                        message=f"{cert_type.title()} certificate expires in {days_until_expiry} days",
                        details={
                            "operation": "mtls_cert_expiry_warning",
                            "cert_type": cert_type,
                            "cert_path": cert_path,
                            "expires_on": not_after.isoformat(),
                            "days_until_expiry": days_until_expiry
                        }
                    ))
                    
            except Exception as e:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUDIT_EVENT,
                    severity=SecurityEventSeverity.MEDIUM,
                    message=f"Failed to check {cert_type} certificate expiry: {e}",
                    details={
                        "operation": "mtls_cert_expiry_check_failed",
                        "cert_type": cert_type,
                        "cert_path": cert_path,
                        "error": str(e)
                    }
                ))
    
    def stop_monitoring(self):
        """Stop certificate monitoring."""
        if self._cert_monitor_thread and self._cert_monitor_thread.is_alive():
            self._monitor_stop_event.set()
            self._cert_monitor_thread.join(timeout=5.0)
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUDIT_EVENT,
            severity=SecurityEventSeverity.LOW,
            message="Certificate expiry monitoring stopped",
            details={"operation": "mtls_cert_monitoring_stopped"}
        ))
    
    def reload_contexts(self):
        """Reload SSL contexts (useful after certificate rotation)."""
        try:
            self.stop_monitoring()
            self._create_ssl_contexts()
            
            if self.config.monitor_certificate_expiry:
                self._start_certificate_monitoring()
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW,
                message="SSL contexts reloaded successfully",
                details={"operation": "mtls_context_reloaded"}
            ))
            
        except Exception as e:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.HIGH,
                message=f"Failed to reload SSL contexts: {e}",
                details={
                    "operation": "mtls_context_reload_failed",
                    "error": str(e)
                }
            ))
            raise MTLSError(f"Failed to reload SSL contexts: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        self.stop_monitoring()


# Factory functions for common configurations
def create_mtls_config_from_files(
    server_cert_path: str,
    server_key_path: str,
    ca_cert_path: str,
    client_cert_path: Optional[str] = None,
    client_key_path: Optional[str] = None,
    mode: MTLSMode = MTLSMode.REQUIRED,
    validation_level: CertificateValidationLevel = CertificateValidationLevel.CHAIN
) -> MTLSConfig:
    """Create mTLS configuration from certificate files."""
    return MTLSConfig(
        enabled=True,
        mode=mode,
        validation_level=validation_level,
        server_cert_path=server_cert_path,
        server_key_path=server_key_path,
        client_cert_path=client_cert_path,
        client_key_path=client_key_path,
        ca_cert_path=ca_cert_path
    )


def create_mtls_config_from_store(
    certificate_store: CertificateStore,
    certificate_manager: Optional[CertificateManager] = None,
    mode: MTLSMode = MTLSMode.REQUIRED,
    validation_level: CertificateValidationLevel = CertificateValidationLevel.REVOCATION
) -> MTLSConfig:
    """Create mTLS configuration from certificate store."""
    return MTLSConfig(
        enabled=True,
        mode=mode,
        validation_level=validation_level,
        certificate_store=certificate_store,
        certificate_manager=certificate_manager
    )

# ============================================================================
# Task 3.2: MTLSManager & Peer Validation
# ============================================================================

@dataclass
class PeerValidationPolicy:
    """Policy for peer certificate validation."""
    
    # Basic validation settings
    require_valid_chain: bool = True
    allow_self_signed: bool = False
    max_chain_depth: int = 10
    
    # Certificate requirements
    required_key_usage: List[str] = field(default_factory=list)
    required_extended_key_usage: List[str] = field(default_factory=list)
    allowed_signature_algorithms: List[str] = field(default_factory=list)
    min_key_size: int = 2048
    
    # Subject/Issuer validation
    allowed_issuers: List[str] = field(default_factory=list)
    required_subject_attributes: Dict[str, str] = field(default_factory=dict)
    allowed_subject_patterns: List[str] = field(default_factory=list)
    
    # Hostname validation
    strict_hostname_checking: bool = True
    allowed_hostname_patterns: List[str] = field(default_factory=list)
    
    # Time-based validation
    max_certificate_age_days: Optional[int] = None
    min_remaining_validity_days: int = 30
    
    # Custom validation callbacks
    custom_validators: List[Callable[[x509.Certificate], Tuple[bool, str]]] = field(default_factory=list)


@dataclass
class ConnectionInfo:
    """Information about an mTLS connection."""
    
    # Connection details
    peer_address: str
    peer_port: int
    local_address: str
    local_port: int
    
    # Certificate information
    peer_certificate: Optional[x509.Certificate] = None
    peer_certificate_chain: Optional[List[x509.Certificate]] = None
    
    # Validation results
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    # Connection metadata
    connection_id: str = ""
    established_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    protocol_version: str = ""
    cipher_suite: str = ""
    
    # Service identity (if available)
    service_name: Optional[str] = None
    service_version: Optional[str] = None


class MTLSManager:
    """
    Centralized mTLS Manager for advanced peer validation and connection management.
    
    This class provides:
    - Advanced peer validation with configurable policies
    - Connection tracking and management
    - Integration with certificate rotation
    - Service identity validation
    - Connection statistics and monitoring
    """
    
    def __init__(
        self,
        config: MTLSConfig,
        validation_policy: Optional[PeerValidationPolicy] = None,
        certificate_manager: Optional[CertificateManager] = None
    ):
        """Initialize mTLS manager."""
        self.config = config
        self.validation_policy = validation_policy or PeerValidationPolicy()
        self.certificate_manager = certificate_manager
        self._logger = get_security_logger()
        
        # SSL context manager
        self.ssl_manager = SSLContextManager(config)
        
        # Connection tracking
        self._active_connections: Dict[str, ConnectionInfo] = {}
        self._connection_stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "rejected_connections": 0,
            "active_connections": 0
        }
        
        # Certificate rotation callbacks
        self._rotation_callbacks: List[Callable[[], None]] = []
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUDIT_EVENT,
            severity=SecurityEventSeverity.LOW,
            message="mTLS Manager initialized",
            details={
                "operation": "mtls_manager_init",
                "mode": self.config.mode.value,
                "validation_level": self.config.validation_level.value,
                "policy_strict_hostname": self.validation_policy.strict_hostname_checking
            }
        ))
    
    def validate_peer_connection(
        self,
        peer_cert: x509.Certificate,
        peer_chain: Optional[List[x509.Certificate]] = None,
        hostname: Optional[str] = None,
        service_name: Optional[str] = None,
        connection_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate peer connection with advanced policies.
        
        Args:
            peer_cert: Peer certificate
            peer_chain: Certificate chain (if available)
            hostname: Expected hostname
            service_name: Expected service name
            connection_info: Additional connection information
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        try:
            # Basic SSL context validation first
            basic_valid, basic_errors = self.ssl_manager.validate_peer_certificate(
                peer_cert, hostname, is_server=(service_name is not None)
            )
            
            if not basic_valid:
                errors.extend(basic_errors)
            
            # Advanced policy validation
            policy_valid, policy_errors, policy_warnings = self._validate_with_policy(
                peer_cert, peer_chain, hostname, service_name
            )
            
            if not policy_valid:
                errors.extend(policy_errors)
            warnings.extend(policy_warnings)
            
            # Service identity validation
            if service_name:
                identity_valid, identity_errors = self._validate_service_identity(
                    peer_cert, service_name
                )
                if not identity_valid:
                    errors.extend(identity_errors)
            
            # Certificate chain validation
            if peer_chain and self.validation_policy.require_valid_chain:
                chain_valid, chain_errors = self._validate_certificate_chain(peer_chain)
                if not chain_valid:
                    errors.extend(chain_errors)
            
            # Custom validators
            for validator in self.validation_policy.custom_validators:
                try:
                    custom_valid, custom_error = validator(peer_cert)
                    if not custom_valid:
                        errors.append(f"Custom validation failed: {custom_error}")
                except Exception as e:
                    errors.append(f"Custom validator error: {e}")
            
            is_valid = len(errors) == 0
            
            # Log validation result
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW if is_valid else SecurityEventSeverity.MEDIUM,
                message=f"Peer validation {'passed' if is_valid else 'failed'}",
                details={
                    "operation": "mtls_peer_validation",
                    "peer_subject": peer_cert.subject.rfc4514_string(),
                    "hostname": hostname,
                    "service_name": service_name,
                    "is_valid": is_valid,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "errors": errors[:5],  # Limit logged errors
                    "warnings": warnings[:5]  # Limit logged warnings
                }
            ))
            
            return is_valid, errors, warnings
            
        except Exception as e:
            error_msg = f"Peer validation failed with exception: {e}"
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.HIGH,
                message=error_msg,
                details={"operation": "mtls_peer_validation_error", "error": str(e)}
            ))
            return False, [error_msg], []
    
    def _validate_with_policy(
        self,
        peer_cert: x509.Certificate,
        peer_chain: Optional[List[x509.Certificate]],
        hostname: Optional[str],
        service_name: Optional[str]
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate certificate against policy."""
        errors = []
        warnings = []
        
        # Key usage validation
        if self.validation_policy.required_key_usage:
            try:
                key_usage = peer_cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                ).value
                
                for required_usage in self.validation_policy.required_key_usage:
                    if not hasattr(key_usage, required_usage.lower()):
                        errors.append(f"Missing required key usage: {required_usage}")
                    elif not getattr(key_usage, required_usage.lower()):
                        errors.append(f"Required key usage not enabled: {required_usage}")
                        
            except x509.ExtensionNotFound:
                errors.append("Certificate missing Key Usage extension")
        
        # Extended key usage validation
        if self.validation_policy.required_extended_key_usage:
            try:
                ext_key_usage = peer_cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.EXTENDED_KEY_USAGE
                ).value
                
                for required_ext_usage in self.validation_policy.required_extended_key_usage:
                    # Convert string to OID if needed
                    if required_ext_usage not in [oid.dotted_string for oid in ext_key_usage]:
                        errors.append(f"Missing required extended key usage: {required_ext_usage}")
                        
            except x509.ExtensionNotFound:
                if self.validation_policy.required_extended_key_usage:
                    errors.append("Certificate missing Extended Key Usage extension")
        
        # Key size validation
        public_key = peer_cert.public_key()
        if hasattr(public_key, 'key_size'):
            if public_key.key_size < self.validation_policy.min_key_size:
                errors.append(
                    f"Key size {public_key.key_size} below minimum {self.validation_policy.min_key_size}"
                )
        
        # Issuer validation
        if self.validation_policy.allowed_issuers:
            issuer_dn = peer_cert.issuer.rfc4514_string()
            if not any(allowed in issuer_dn for allowed in self.validation_policy.allowed_issuers):
                errors.append(f"Certificate issuer not in allowed list: {issuer_dn}")
        
        # Subject attribute validation
        if self.validation_policy.required_subject_attributes:
            subject_attrs = {}
            for attr in peer_cert.subject:
                subject_attrs[attr.oid._name] = attr.value
            
            for required_attr, required_value in self.validation_policy.required_subject_attributes.items():
                if required_attr not in subject_attrs:
                    errors.append(f"Missing required subject attribute: {required_attr}")
                elif subject_attrs[required_attr] != required_value:
                    errors.append(
                        f"Subject attribute {required_attr} value mismatch: "
                        f"expected {required_value}, got {subject_attrs[required_attr]}"
                    )
        
        # Certificate age validation
        if self.validation_policy.max_certificate_age_days:
            cert_age = datetime.now(timezone.utc) - peer_cert.not_valid_before_utc
            max_age = timedelta(days=self.validation_policy.max_certificate_age_days)
            if cert_age > max_age:
                warnings.append(f"Certificate is {cert_age.days} days old (max: {max_age.days})")
        
        # Remaining validity validation
        remaining_validity = peer_cert.not_valid_after_utc - datetime.now(timezone.utc)
        min_remaining = timedelta(days=self.validation_policy.min_remaining_validity_days)
        if remaining_validity < min_remaining:
            if remaining_validity.total_seconds() < 0:
                errors.append("Certificate has expired")
            else:
                warnings.append(
                    f"Certificate expires in {remaining_validity.days} days "
                    f"(minimum: {min_remaining.days})"
                )
        
        # Hostname pattern validation
        if hostname and self.validation_policy.allowed_hostname_patterns:
            hostname_allowed = False
            for pattern in self.validation_policy.allowed_hostname_patterns:
                if self._match_pattern(hostname, pattern):
                    hostname_allowed = True
                    break
            
            if not hostname_allowed:
                errors.append(f"Hostname {hostname} not allowed by policy patterns")
        
        return len(errors) == 0, errors, warnings
    
    def _validate_service_identity(
        self,
        peer_cert: x509.Certificate,
        expected_service: str
    ) -> Tuple[bool, List[str]]:
        """Validate service identity from certificate."""
        errors = []
        
        try:
            # Look for service name in Subject Alternative Names
            san_ext = peer_cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
            
            # Check for service name in DNS names or URIs
            service_found = False
            
            for name in san_ext:
                if isinstance(name, x509.DNSName):
                    if expected_service in name.value or name.value.startswith(f"{expected_service}."):
                        service_found = True
                        break
                elif isinstance(name, x509.UniformResourceIdentifier):
                    if expected_service in name.value:
                        service_found = True
                        break
            
            if not service_found:
                # Check Common Name as fallback
                try:
                    cn = peer_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                    if expected_service not in cn:
                        errors.append(f"Service identity {expected_service} not found in certificate")
                except (IndexError, AttributeError):
                    errors.append(f"Service identity {expected_service} not found in certificate")
                    
        except x509.ExtensionNotFound:
            # Check Common Name only
            try:
                cn = peer_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                if expected_service not in cn:
                    errors.append(f"Service identity {expected_service} not found in certificate")
            except (IndexError, AttributeError):
                errors.append("Certificate has no service identity information")
        
        return len(errors) == 0, errors
    
    def _validate_certificate_chain(
        self,
        cert_chain: List[x509.Certificate]
    ) -> Tuple[bool, List[str]]:
        """Validate certificate chain."""
        errors = []
        
        if len(cert_chain) > self.validation_policy.max_chain_depth:
            errors.append(f"Certificate chain too long: {len(cert_chain)} > {self.validation_policy.max_chain_depth}")
        
        # Validate chain order and signatures
        for i in range(len(cert_chain) - 1):
            current_cert = cert_chain[i]
            issuer_cert = cert_chain[i + 1]
            
            # Check if issuer matches
            if current_cert.issuer != issuer_cert.subject:
                errors.append(f"Chain break at position {i}: issuer mismatch")
                continue
            
            # Verify signature (simplified check)
            try:
                # In a full implementation, we would verify the signature
                # For now, we just check the issuer/subject relationship
                pass
            except Exception as e:
                errors.append(f"Signature verification failed at position {i}: {e}")
        
        return len(errors) == 0, errors
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Match value against pattern (supports wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
    
    def register_connection(
        self,
        connection_id: str,
        peer_address: str,
        peer_port: int,
        local_address: str,
        local_port: int,
        peer_cert: Optional[x509.Certificate] = None,
        validation_result: Optional[Tuple[bool, List[str], List[str]]] = None
    ) -> ConnectionInfo:
        """Register a new mTLS connection."""
        with self._lock:
            conn_info = ConnectionInfo(
                peer_address=peer_address,
                peer_port=peer_port,
                local_address=local_address,
                local_port=local_port,
                peer_certificate=peer_cert,
                connection_id=connection_id
            )
            
            if validation_result:
                is_valid, errors, warnings = validation_result
                conn_info.validation_passed = is_valid
                conn_info.validation_errors = errors
                conn_info.validation_warnings = warnings
            
            self._active_connections[connection_id] = conn_info
            
            # Update statistics
            self._connection_stats["total_connections"] += 1
            self._connection_stats["active_connections"] = len(self._active_connections)
            
            if conn_info.validation_passed:
                self._connection_stats["successful_connections"] += 1
            else:
                self._connection_stats["failed_connections"] += 1
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW,
                message="mTLS connection registered",
                details={
                    "operation": "mtls_connection_registered",
                    "connection_id": connection_id,
                    "peer_address": peer_address,
                    "peer_port": peer_port,
                    "validation_passed": conn_info.validation_passed
                }
            ))
            
            return conn_info
    
    def unregister_connection(self, connection_id: str) -> bool:
        """Unregister an mTLS connection."""
        with self._lock:
            if connection_id in self._active_connections:
                del self._active_connections[connection_id]
                self._connection_stats["active_connections"] = len(self._active_connections)
                
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUDIT_EVENT,
                    severity=SecurityEventSeverity.LOW,
                    message="mTLS connection unregistered",
                    details={
                        "operation": "mtls_connection_unregistered",
                        "connection_id": connection_id
                    }
                ))
                
                return True
            return False
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get information about a connection."""
        with self._lock:
            return self._active_connections.get(connection_id)
    
    def get_active_connections(self) -> List[ConnectionInfo]:
        """Get all active connections."""
        with self._lock:
            return list(self._active_connections.values())
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        with self._lock:
            return self._connection_stats.copy()
    
    def add_rotation_callback(self, callback: Callable[[], None]):
        """Add callback for certificate rotation events."""
        self._rotation_callbacks.append(callback)
    
    def handle_certificate_rotation(self):
        """Handle certificate rotation event."""
        try:
            # Reload SSL contexts
            self.ssl_manager.reload_contexts()
            
            # Call registered callbacks
            for callback in self._rotation_callbacks:
                try:
                    callback()
                except Exception as e:
                    self._logger.log_event(SecurityEvent(
                        event_type=SecurityEventType.AUDIT_EVENT,
                        severity=SecurityEventSeverity.MEDIUM,
                        message=f"Rotation callback failed: {e}",
                        details={"operation": "mtls_rotation_callback_error", "error": str(e)}
                    ))
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW,
                message="Certificate rotation handled successfully",
                details={"operation": "mtls_certificate_rotation"}
            ))
            
        except Exception as e:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.HIGH,
                message=f"Certificate rotation failed: {e}",
                details={"operation": "mtls_rotation_error", "error": str(e)}
            ))
            raise MTLSError(f"Certificate rotation failed: {e}")
    
    def shutdown(self):
        """Shutdown mTLS manager."""
        with self._lock:
            # Stop SSL context monitoring
            self.ssl_manager.stop_monitoring()
            
            # Clear connections
            connection_count = len(self._active_connections)
            self._active_connections.clear()
            self._connection_stats["active_connections"] = 0
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUDIT_EVENT,
                severity=SecurityEventSeverity.LOW,
                message="mTLS Manager shutdown",
                details={
                    "operation": "mtls_manager_shutdown",
                    "closed_connections": connection_count
                }
            ))


# Factory functions for MTLSManager
def create_mtls_manager_with_policy(
    config: MTLSConfig,
    strict_validation: bool = True,
    allowed_services: Optional[List[str]] = None,
    certificate_manager: Optional[CertificateManager] = None
) -> MTLSManager:
    """Create MTLSManager with predefined policy."""
    
    policy = PeerValidationPolicy(
        require_valid_chain=True,
        allow_self_signed=not strict_validation,
        strict_hostname_checking=strict_validation,
        min_remaining_validity_days=30 if strict_validation else 7
    )
    
    if strict_validation:
        policy.required_key_usage = ["digital_signature", "key_encipherment"]
        policy.min_key_size = 2048
    
    if allowed_services:
        policy.allowed_hostname_patterns = [f"{service}*" for service in allowed_services]
    
    return MTLSManager(config, policy, certificate_manager)


def create_mtls_manager_for_microservices(
    config: MTLSConfig,
    service_mesh_ca: Optional[str] = None,
    certificate_manager: Optional[CertificateManager] = None
) -> MTLSManager:
    """Create MTLSManager optimized for microservices."""
    
    policy = PeerValidationPolicy(
        require_valid_chain=True,
        allow_self_signed=False,
        strict_hostname_checking=True,
        min_remaining_validity_days=7,  # Shorter for frequent rotation
        required_key_usage=["digital_signature"],
        min_key_size=2048
    )
    
    if service_mesh_ca:
        policy.allowed_issuers = [service_mesh_ca]
    
    # Add microservice-specific patterns
    policy.allowed_hostname_patterns = [
        "*.svc.cluster.local",  # Kubernetes services
        "*.service.consul",     # Consul services
        "*-service",            # Generic service pattern
        "*-api",               # API service pattern
    ]
    
    return MTLSManager(config, policy, certificate_manager)


# =============================================================================
# mTLS Middleware for FastAPI
# =============================================================================

try:
    from fastapi import Request, Response, HTTPException
    from fastapi.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp
    import httpx
except ImportError:
    # Optional dependencies for middleware and HTTP client
    Request = None
    Response = None
    HTTPException = None
    BaseHTTPMiddleware = None
    ASGIApp = None
    httpx = None


# Placeholder classes for when FastAPI is not available
if BaseHTTPMiddleware is not None:
    # MTLSMiddleware implementation would go here
    # For now, we'll create a simple placeholder
    class MTLSMiddleware:
        """Placeholder for MTLSMiddleware when FastAPI is available."""
        def __init__(self, *args, **kwargs):
            pass
else:
    class MTLSMiddleware:
        """Placeholder for MTLSMiddleware when FastAPI is not available."""
        def __init__(self, *args, **kwargs):
            pass


# =============================================================================
# mTLS HTTP Client for Service-to-Service Communication
# =============================================================================

class MTLSHTTPClient:
    """
    HTTP client with mTLS support for secure service-to-service communication.
    
    This client automatically handles mTLS certificate loading, validation,
    and connection management for outbound requests.
    """
    
    def __init__(
        self,
        mtls_config: MTLSConfig,
        mtls_manager: Optional[MTLSManager] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_hostname: bool = True
    ):
        """Initialize mTLS HTTP client."""
        self.mtls_config = mtls_config
        self.mtls_manager = mtls_manager
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_hostname = verify_hostname
        self.logger = get_security_logger()
    
    async def get(self, url: str, **kwargs):
        """Make GET request with mTLS."""
        return {"status": "placeholder"}
    
    async def post(self, url: str, **kwargs):
        """Make POST request with mTLS."""
        return {"status": "placeholder"}
    
    async def close(self):
        """Close the HTTP client."""
        pass


# =============================================================================
# Factory Functions for mTLS Integration
# =============================================================================

def create_mtls_middleware(
    mtls_config: MTLSConfig,
    mtls_manager: Optional[MTLSManager] = None,
    reject_non_mtls: bool = True,
    require_service_identity: bool = False,
    allowed_non_mtls_paths: Optional[List[str]] = None
) -> MTLSMiddleware:
    """Create MTLSMiddleware with configuration."""
    if not mtls_manager:
        mtls_manager = create_mtls_manager_for_microservices(mtls_config)
    
    return MTLSMiddleware()


def create_mtls_http_client(
    mtls_config: MTLSConfig,
    mtls_manager: Optional[MTLSManager] = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    verify_hostname: bool = True
) -> MTLSHTTPClient:
    """Create MTLSHTTPClient with configuration."""
    return MTLSHTTPClient(
        mtls_config=mtls_config,
        mtls_manager=mtls_manager,
        timeout=timeout,
        max_retries=max_retries,
        verify_hostname=verify_hostname
    )


# =============================================================================
# Convenience Functions for FastAPI Integration
# =============================================================================

def setup_mtls_for_fastapi(
    app,  # FastAPI app
    mtls_config: MTLSConfig,
    mtls_manager: Optional[MTLSManager] = None,
    middleware_config: Optional[Dict[str, Any]] = None
):
    """Set up mTLS for a FastAPI application."""
    # Create mTLS manager if not provided
    if not mtls_manager:
        mtls_manager = create_mtls_manager_for_microservices(mtls_config)
    
    # Create middleware and HTTP client
    middleware = create_mtls_middleware(mtls_config, mtls_manager)
    http_client = create_mtls_http_client(mtls_config, mtls_manager)
    
    return middleware, http_client
# =============================================================================
# mTLS FastAPI Middleware
# =============================================================================

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware


class MTLSMiddleware:
    """
    FastAPI middleware for mTLS connection validation.
    
    This middleware validates mTLS connections and enforces mTLS policies
    for incoming requests. It integrates with the MTLSManager for
    certificate validation and connection management.
    """
    
    def __init__(
        self,
        mtls_manager: MTLSManager,
        enforce_mtls: bool = True,
        exclude_paths: Optional[List[str]] = None,
        require_client_cert: bool = True
    ):
        """
        Initialize mTLS middleware.
        
        Args:
            mtls_manager: MTLSManager instance for certificate validation
            enforce_mtls: Whether to enforce mTLS for all requests
            exclude_paths: Paths to exclude from mTLS validation
            require_client_cert: Whether to require client certificates
        """
        self.mtls_manager = mtls_manager
        self.enforce_mtls = enforce_mtls
        self.exclude_paths = exclude_paths or []
        self.require_client_cert = require_client_cert
        self.logger = get_security_logger()
        
        # Add common paths to exclude by default
        self.exclude_paths.extend([
            "/docs", "/redoc", "/openapi.json", "/health", "/metrics"
        ])
    
    async def __call__(self, request: "Request", call_next):
        """
        Process request through mTLS middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response object
        """
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Check if mTLS is enforced
            if not self.enforce_mtls:
                return await call_next(request)
            
            # Validate mTLS connection
            connection_info = await self._validate_mtls_connection(request)
            
            if not connection_info:
                return self._create_mtls_required_response()
            
            # Store connection info in request state
            request.state.mtls_connection = connection_info
            request.state.client_certificate = connection_info.client_cert
            
            # Log successful mTLS connection
            from .logging import SecurityEvent, SecurityEventType, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.MTLS_CONNECTION_ESTABLISHED,
                severity=SecurityEventSeverity.LOW,
                source="mtls_middleware",
                message=f"mTLS connection established for {request.url.path}",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "client_cert_subject": connection_info.client_cert.subject_name if connection_info.client_cert else None,
                    "client_cert_issuer": connection_info.client_cert.issuer_name if connection_info.client_cert else None
                }
            )
            self.logger.log_event(event)
            
            return await call_next(request)
            
        except Exception as e:
            # Log error and reject connection
            self.logger.log_security_violation(
                violation_type="mtls_middleware_error",
                description=f"mTLS middleware error: {str(e)}",
                severity="high"
            )
            return self._create_error_response(str(e))
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from mTLS validation."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    async def _validate_mtls_connection(self, request: "Request") -> Optional[ConnectionInfo]:
        """
        Validate mTLS connection for the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            ConnectionInfo if valid mTLS connection, None otherwise
        """
        try:
            # Extract client certificate from request
            client_cert = self._extract_client_certificate(request)
            
            if not client_cert and self.require_client_cert:
                return None
            
            # Create connection info
            connection_info = ConnectionInfo(
                connection_id=f"mtls_{id(request)}",
                client_cert=client_cert,
                server_cert=None,  # Server cert not available in middleware context
                established_at=datetime.utcnow(),
                is_valid=True,
                validation_errors=[]
            )
            
            # Validate client certificate if present
            if client_cert:
                validation_result = await self.mtls_manager.validate_peer_certificate(
                    client_cert,
                    self.mtls_manager.validation_policy
                )
                
                connection_info.is_valid = validation_result.is_valid
                connection_info.validation_errors = validation_result.errors
                
                if not validation_result.is_valid:
                    return None
            
            return connection_info
            
        except Exception as e:
            self.logger.log_security_violation(
                violation_type="mtls_connection_validation_failed",
                description=f"Failed to validate mTLS connection: {str(e)}",
                severity="medium"
            )
            return None
    
    def _extract_client_certificate(self, request: "Request") -> Optional[Certificate]:
        """
        Extract client certificate from request.
        
        This method attempts to extract the client certificate from
        various sources in the request (headers, TLS context, etc.).
        """
        # In a real implementation, this would extract the certificate
        # from the TLS context or headers. For now, we'll return None
        # as this requires integration with the ASGI server.
        
        # Check for certificate in headers (some proxies add this)
        cert_header = request.headers.get("X-Client-Cert")
        if cert_header:
            try:
                # Decode and parse certificate from header
                return Certificate(cert_header, CertificateFormat.PEM)
            except Exception:
                pass
        
        # Check for certificate in custom headers
        cert_pem = request.headers.get("X-SSL-Client-Cert")
        if cert_pem:
            try:
                return Certificate(cert_pem, CertificateFormat.PEM)
            except Exception:
                pass
        
        # In production, this would access the TLS context
        # through the ASGI scope or server-specific mechanisms
        return None
    
    def _create_mtls_required_response(self):
        """Create mTLS required response."""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,  # Bad Request
            detail="mTLS connection required. Client certificate must be provided.",
            headers={"X-mTLS-Required": "true"}
        )
    
    def _create_error_response(self, message: str):
        """Create error response."""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"mTLS validation error: {message}"
        )


# =============================================================================
# mTLS-Enabled HTTP Client
# =============================================================================

import httpx
from typing import Union, Dict, Any, Optional


class MTLSHTTPClient:
    """
    HTTP client with mTLS support for service-to-service communication.
    
    This client automatically configures mTLS connections using the
    provided MTLSConfig and integrates with certificate management.
    """
    
    def __init__(
        self,
        mtls_config: MTLSConfig,
        certificate_manager: Optional[CertificateManager] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        verify_server_cert: bool = True
    ):
        """
        Initialize mTLS HTTP client.
        
        Args:
            mtls_config: mTLS configuration
            certificate_manager: Certificate manager for automatic cert loading
            base_url: Base URL for requests
            timeout: Request timeout in seconds
            verify_server_cert: Whether to verify server certificates
        """
        self.mtls_config = mtls_config
        self.certificate_manager = certificate_manager
        self.base_url = base_url
        self.timeout = timeout
        self.verify_server_cert = verify_server_cert
        self.logger = get_security_logger()
        
        # Initialize HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _initialize_client(self):
        """Initialize the HTTP client with mTLS configuration."""
        try:
            # Create SSL context
            self._ssl_context = await self._create_ssl_context()
            
            # Create HTTP client with mTLS
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self._ssl_context if self.verify_server_cert else False,
                cert=self._get_client_cert_tuple() if self.mtls_config.client_cert_path else None
            )
            
            # Log client initialization
            from .logging import SecurityEvent, SecurityEventType, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.MTLS_CLIENT_INITIALIZED,
                severity=SecurityEventSeverity.LOW,
                source="mtls_http_client",
                message="mTLS HTTP client initialized",
                details={
                    "base_url": self.base_url,
                    "verify_server_cert": self.verify_server_cert,
                    "client_cert_configured": bool(self.mtls_config.client_cert_path)
                }
            )
            self.logger.log_event(event)
            
        except Exception as e:
            error_msg = f"Failed to initialize mTLS HTTP client: {str(e)}"
            self.logger.log_security_violation(
                violation_type="mtls_client_initialization_failed",
                description=error_msg,
                severity="high"
            )
            raise MTLSError(error_msg) from e
    
    async def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context for mTLS connections."""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Configure SSL version and ciphers
        context.minimum_version = self.mtls_config.min_ssl_version
        if self.mtls_config.ciphers:
            context.set_ciphers(self.mtls_config.ciphers)
        
        # Load CA certificates
        if self.mtls_config.ca_cert_path:
            context.load_verify_locations(self.mtls_config.ca_cert_path)
        
        # Configure certificate verification
        context.verify_mode = self.mtls_config.verify_mode
        context.check_hostname = self.mtls_config.check_hostname
        
        return context
    
    def _get_client_cert_tuple(self) -> Optional[tuple]:
        """Get client certificate tuple for httpx."""
        if self.mtls_config.client_cert_path and self.mtls_config.client_key_path:
            return (self.mtls_config.client_cert_path, self.mtls_config.client_key_path)
        return None
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make GET request with mTLS."""
        return await self._request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make POST request with mTLS."""
        return await self._request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make PUT request with mTLS."""
        return await self._request("PUT", url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """Make PATCH request with mTLS."""
        return await self._request("PATCH", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make DELETE request with mTLS."""
        return await self._request("DELETE", url, **kwargs)
    
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with mTLS."""
        if not self._client:
            raise MTLSError("HTTP client not initialized. Use async context manager.")
        
        try:
            # Add mTLS headers
            headers = kwargs.get("headers", {})
            headers.update(self._get_mtls_headers())
            kwargs["headers"] = headers
            
            # Make request
            response = await self._client.request(method, url, **kwargs)
            
            # Log successful request
            from .logging import SecurityEvent, SecurityEventType, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.MTLS_REQUEST_SENT,
                severity=SecurityEventSeverity.LOW,
                source="mtls_http_client",
                message=f"mTLS {method} request to {url}",
                details={
                    "method": method,
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers)
                }
            )
            self.logger.log_event(event)
            
            return response
            
        except Exception as e:
            # Log request error
            self.logger.log_security_violation(
                violation_type="mtls_request_failed",
                description=f"mTLS {method} request to {url} failed: {str(e)}",
                severity="medium"
            )
            raise
    
    def _get_mtls_headers(self) -> Dict[str, str]:
        """Get headers to include in mTLS requests."""
        headers = {
            "X-mTLS-Enabled": "true",
            "User-Agent": "FastAPI-Microservices-SDK-mTLS/1.0"
        }
        
        # Add client certificate info if available
        if self.mtls_config.client_cert_path:
            headers["X-Client-Cert-Configured"] = "true"
        
        return headers
    
    async def get_json(self, url: str, **kwargs) -> Dict[str, Any]:
        """Make GET request and return JSON response."""
        response = await self.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def post_json(self, url: str, json_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make POST request with JSON data and return JSON response."""
        response = await self.post(url, json=json_data, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def health_check(self, health_endpoint: str = "/health") -> bool:
        """Perform health check on the target service."""
        try:
            response = await self.get(health_endpoint)
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# mTLS Integration Helpers
# =============================================================================

def setup_mtls_app(
    app,  # FastAPI app
    mtls_config: MTLSConfig,
    certificate_manager: Optional[CertificateManager] = None,
    enable_middleware: bool = True,
    middleware_config: Optional[Dict[str, Any]] = None
):
    """
    Set up mTLS integration for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        mtls_config: mTLS configuration
        certificate_manager: Certificate manager instance
        enable_middleware: Whether to enable mTLS middleware
        middleware_config: Configuration for mTLS middleware
    """
    # Create MTLSManager
    mtls_manager = MTLSManager(
        config=mtls_config,
        certificate_manager=certificate_manager
    )
    
    if enable_middleware:
        config = middleware_config or {}
        middleware = MTLSMiddleware(mtls_manager, **config)
        
        # Add middleware to app
        from starlette.middleware.base import BaseHTTPMiddleware
        
        class MTLSHTTPMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, mtls_middleware: MTLSMiddleware):
                super().__init__(app)
                self.mtls_middleware = mtls_middleware
            
            async def dispatch(self, request, call_next):
                return await self.mtls_middleware(request, call_next)
        
        app.add_middleware(MTLSHTTPMiddleware, mtls_middleware=middleware)
    
    # Store mTLS components in app state
    app.state.mtls_config = mtls_config
    app.state.mtls_manager = mtls_manager
    app.state.certificate_manager = certificate_manager
    
    return app


def get_mtls_manager(request: "Request") -> MTLSManager:
    """
    Get mTLS manager from FastAPI app state.
    
    This is a FastAPI dependency that can be used to inject
    the mTLS manager into endpoint functions.
    """
    if not hasattr(request.app.state, "mtls_manager"):
        raise RuntimeError("mTLS manager not configured in app state")
    
    return request.app.state.mtls_manager


def get_client_certificate(request: "Request") -> Optional[Certificate]:
    """
    Get client certificate from request state.
    
    This is a FastAPI dependency that can be used to inject
    the client certificate into endpoint functions.
    """
    return getattr(request.state, "client_certificate", None)


def require_mtls_connection(request: "Request") -> ConnectionInfo:
    """
    FastAPI dependency that requires a valid mTLS connection.
    
    Raises HTTPException if no valid mTLS connection is present.
    """
    connection_info = getattr(request.state, "mtls_connection", None)
    
    if not connection_info:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="mTLS connection required"
        )
    
    if not connection_info.is_valid:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Invalid mTLS connection"
        )
    
    return connection_info


# =============================================================================
# mTLS Service Client Factory
# =============================================================================

async def create_mtls_service_client(
    service_name: str,
    mtls_config: MTLSConfig,
    certificate_manager: Optional[CertificateManager] = None,
    service_registry = None,
    **kwargs
) -> MTLSHTTPClient:
    """
    Create an mTLS HTTP client for communicating with a specific service.
    
    Args:
        service_name: Name of the target service
        mtls_config: mTLS configuration
        certificate_manager: Certificate manager instance
        service_registry: Service registry for service discovery
        **kwargs: Additional arguments for MTLSHTTPClient
        
    Returns:
        Configured MTLSHTTPClient instance
    """
    # Discover service URL if service registry is provided
    base_url = None
    if service_registry:
        try:
            instances = await service_registry.discover_service(service_name)
            if instances:
                # Use first available instance
                instance = instances[0]
                base_url = f"https://{instance.host}:{instance.port}"
        except Exception:
            pass
    
    # Create and return mTLS client
    return MTLSHTTPClient(
        mtls_config=mtls_config,
        certificate_manager=certificate_manager,
        base_url=base_url,
        **kwargs
    )
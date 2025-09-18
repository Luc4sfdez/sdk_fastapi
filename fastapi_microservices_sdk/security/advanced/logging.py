"""
Security Logging Infrastructure for FastAPI Microservices SDK.
This module provides structured security logging with audit trails,
tamper-evident logs, and comprehensive security event tracking.
"""
import json
import logging
import asyncio
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import threading
from queue import Queue, Empty
from logging.handlers import RotatingFileHandler
import uuid

from .exceptions import SecurityLoggingError, AuditTrailError, LogRotationError


class SecurityEventType(Enum):
    """Types of security events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ACCESS_DENIED = "access_denied"
    CERTIFICATE_EVENT = "certificate_event"
    THREAT_DETECTED = "threat_detected"
    SECURITY_VIOLATION = "security_violation"
    CONFIGURATION_CHANGE = "configuration_change"
    AUDIT_EVENT = "audit_event"
    # RBAC Events
    RBAC_ROLE_CREATED = "rbac_role_created"
    RBAC_ROLE_DELETED = "rbac_role_deleted"
    RBAC_ROLE_ASSIGNED = "rbac_role_assigned"
    RBAC_ROLE_REVOKED = "rbac_role_revoked"
    RBAC_PERMISSION_CREATED = "rbac_permission_created"
    RBAC_PERMISSION_DELETED = "rbac_permission_deleted"
    RBAC_ACCESS_GRANTED = "rbac_access_granted"
    RBAC_ACCESS_DENIED = "rbac_access_denied"
    RBAC_CLEANUP = "rbac_cleanup"


class SecurityEventSeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Base security event data model."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: SecurityEventType = SecurityEventType.AUDIT_EVENT
    severity: SecurityEventSeverity = SecurityEventSeverity.LOW
    source: str = "unknown"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    service_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime to ISO format
        data['timestamp'] = self.timestamp.isoformat()
        # Convert enums to string values
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AuthEvent(SecurityEvent):
    """Authentication-specific security event."""
    event_type: SecurityEventType = SecurityEventType.AUTHENTICATION
    auth_method: Optional[str] = None
    success: bool = False
    failure_reason: Optional[str] = None
    token_type: Optional[str] = None
    
    def __post_init__(self):
        """Set severity based on authentication result."""
        if not self.success:
            self.severity = SecurityEventSeverity.MEDIUM
        else:
            self.severity = SecurityEventSeverity.LOW


@dataclass
class AuthzEvent(SecurityEvent):
    """Authorization-specific security event."""
    event_type: SecurityEventType = SecurityEventType.AUTHORIZATION
    resource: Optional[str] = None
    action: Optional[str] = None
    permission: Optional[str] = None
    role: Optional[str] = None
    decision: str = "DENY"
    policy_name: Optional[str] = None
    
    def __post_init__(self):
        """Set severity based on authorization decision."""
        if self.decision == "DENY":
            self.severity = SecurityEventSeverity.MEDIUM
        else:
            self.severity = SecurityEventSeverity.LOW


@dataclass
class ThreatEvent(SecurityEvent):
    """Threat detection security event."""
    event_type: SecurityEventType = SecurityEventType.THREAT_DETECTED
    threat_type: Optional[str] = None
    confidence_score: Optional[float] = None
    detection_rule: Optional[str] = None
    blocked: bool = False
    
    def __post_init__(self):
        """Set severity based on threat confidence."""
        if self.confidence_score is not None:
            if self.confidence_score >= 0.9:
                self.severity = SecurityEventSeverity.CRITICAL
            elif self.confidence_score >= 0.7:
                self.severity = SecurityEventSeverity.HIGH
            elif self.confidence_score >= 0.5:
                self.severity = SecurityEventSeverity.MEDIUM
            else:
                self.severity = SecurityEventSeverity.LOW


@dataclass
class CertificateEvent(SecurityEvent):
    """Certificate-related security event."""
    event_type: SecurityEventType = SecurityEventType.CERTIFICATE_EVENT
    certificate_id: Optional[str] = None
    certificate_subject: Optional[str] = None
    certificate_issuer: Optional[str] = None
    operation: Optional[str] = None  # load, validate, rotate, expire
    expiry_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Set severity based on certificate operation."""
        if self.operation in ["expire", "revoke"]:
            self.severity = SecurityEventSeverity.HIGH
        elif self.operation in ["rotate", "renew"]:
            self.severity = SecurityEventSeverity.MEDIUM
        else:
            self.severity = SecurityEventSeverity.LOW


class AuditTrail:
    """Tamper-evident audit trail for security events."""
    
    def __init__(self, secret_key: str):
        """Initialize audit trail with secret key for HMAC."""
        self.secret_key = secret_key.encode('utf-8')
        self.previous_hash = "0" * 64  # Genesis hash
    
    def create_audit_record(self, event: SecurityEvent) -> Dict[str, Any]:
        """Create tamper-evident audit record."""
        # Create base audit record
        audit_record = {
            "audit_id": str(uuid.uuid4()),
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.to_dict(),
            "previous_hash": self.previous_hash
        }
        
        # Calculate hash for this record
        record_data = json.dumps(audit_record, sort_keys=True)
        current_hash = hmac.new(
            self.secret_key,
            record_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        audit_record["hash"] = current_hash
        self.previous_hash = current_hash
        
        return audit_record
    
    def verify_audit_record(self, audit_record: Dict[str, Any]) -> bool:
        """Verify integrity of audit record."""
        try:
            # Extract hash and create record without hash
            stored_hash = audit_record.pop("hash")
            record_data = json.dumps(audit_record, sort_keys=True)
            
            # Calculate expected hash
            expected_hash = hmac.new(
                self.secret_key,
                record_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Restore hash to record
            audit_record["hash"] = stored_hash
            
            return hmac.compare_digest(stored_hash, expected_hash)
        except Exception:
            return False


class SecurityLogger:
    """
    Comprehensive security logging system with structured events,
    audit trails, and tamper-evident logging.
    """
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        log_file: Optional[str] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 5,
        enable_audit_trail: bool = True,
        audit_secret_key: Optional[str] = None,
        async_logging: bool = True,
        buffer_size: int = 1000,
        flush_interval: float = 5.0
    ):
        """Initialize security logger."""
        self.log_level = getattr(logging, log_level.upper())
        self.log_format = log_format
        self.enable_audit_trail = enable_audit_trail
        self.async_logging = async_logging
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        
        # Initialize logger
        self.logger = logging.getLogger("security")
        self.logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup file handler if specified
        if log_file:
            try:
                # Ensure directory exists
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_file_size,
                    backupCount=backup_count
                )
                file_handler.setLevel(self.log_level)
                
                if log_format == "json":
                    formatter = logging.Formatter('%(message)s')
                else:
                    formatter = logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    )
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                raise SecurityLoggingError(f"Failed to setup file handler: {e}")
        
        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        if log_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Initialize audit trail
        if self.enable_audit_trail:
            if not audit_secret_key:
                audit_secret_key = "default-audit-key-change-in-production"
            self.audit_trail = AuditTrail(audit_secret_key)
        else:
            self.audit_trail = None
        
        # Initialize async logging
        if self.async_logging:
            self.log_queue = Queue(maxsize=self.buffer_size)
            self.stop_logging = threading.Event()
            self.logging_thread = threading.Thread(
                target=self._async_log_worker,
                daemon=True
            )
            self.logging_thread.start()
            
            # Start flush timer
            self.flush_timer = threading.Timer(self.flush_interval, self._flush_logs)
            self.flush_timer.daemon = True
            self.flush_timer.start()
    
    def _async_log_worker(self):
        """Async logging worker thread."""
        while not self.stop_logging.is_set():
            try:
                # Get log entry with timeout
                log_entry = self.log_queue.get(timeout=1.0)
                if log_entry is None:  # Shutdown signal
                    break
                
                # Process log entry
                self._write_log_entry(log_entry)
                self.log_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                # Log error to stderr to avoid recursion
                print(f"Security logging error: {e}")
    
    def _flush_logs(self):
        """Flush pending logs and restart timer."""
        try:
            # Process all pending logs
            while not self.log_queue.empty():
                try:
                    log_entry = self.log_queue.get_nowait()
                    self._write_log_entry(log_entry)
                    self.log_queue.task_done()
                except Empty:
                    break
            
            # Restart timer
            if not self.stop_logging.is_set():
                self.flush_timer = threading.Timer(self.flush_interval, self._flush_logs)
                self.flush_timer.daemon = True
                self.flush_timer.start()
        except Exception as e:
            print(f"Security log flush error: {e}")
    
    def _write_log_entry(self, log_entry: Dict[str, Any]):
        """Write log entry to configured handlers."""
        try:
            if self.log_format == "json":
                message = json.dumps(log_entry)
            else:
                message = f"Security Event: {log_entry.get('message', 'Unknown')}"
            
            # Log based on severity
            severity = log_entry.get('severity', 'low')
            if severity == 'critical':
                self.logger.critical(message)
            elif severity == 'high':
                self.logger.error(message)
            elif severity == 'medium':
                self.logger.warning(message)
            else:
                self.logger.info(message)
                
        except Exception as e:
            raise SecurityLoggingError(f"Failed to write log entry: {e}")
    
    def log_event(self, event: SecurityEvent):
        """Log a security event."""
        try:
            # Create log entry
            log_entry = event.to_dict()
            
            # Add audit trail if enabled
            if self.audit_trail:
                audit_record = self.audit_trail.create_audit_record(event)
                log_entry["audit"] = audit_record
            
            # Log asynchronously or synchronously
            if self.async_logging:
                try:
                    self.log_queue.put_nowait(log_entry)
                except:
                    # Queue full, log synchronously as fallback
                    self._write_log_entry(log_entry)
            else:
                self._write_log_entry(log_entry)
                
        except Exception as e:
            raise SecurityLoggingError(f"Failed to log security event: {e}")
    
    def log_auth_event(
        self,
        user_id: str,
        success: bool,
        auth_method: str = "unknown",
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ):
        """Log authentication event."""
        event = AuthEvent(
            user_id=user_id,
            success=success,
            auth_method=auth_method,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
            message=f"Authentication {'successful' if success else 'failed'} for user {user_id}",
            **kwargs
        )
        self.log_event(event)
    
    def log_authz_event(
        self,
        user_id: str,
        resource: str,
        action: str,
        decision: str,
        role: Optional[str] = None,
        permission: Optional[str] = None,
        policy_name: Optional[str] = None,
        **kwargs
    ):
        """Log authorization event."""
        event = AuthzEvent(
            user_id=user_id,
            resource=resource,
            action=action,
            decision=decision,
            role=role,
            permission=permission,
            policy_name=policy_name,
            message=f"Authorization {decision} for user {user_id} on {resource}:{action}",
            **kwargs
        )
        self.log_event(event)
    
    def log_threat_event(
        self,
        threat_type: str,
        confidence_score: float,
        detection_rule: str,
        blocked: bool = False,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs
    ):
        """Log threat detection event."""
        event = ThreatEvent(
            threat_type=threat_type,
            confidence_score=confidence_score,
            detection_rule=detection_rule,
            blocked=blocked,
            user_id=user_id,
            ip_address=ip_address,
            message=f"Threat detected: {threat_type} (confidence: {confidence_score:.2f})",
            **kwargs
        )
        self.log_event(event)
    
    def log_certificate_event(
        self,
        certificate_id: str,
        operation: str,
        certificate_subject: Optional[str] = None,
        certificate_issuer: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        **kwargs
    ):
        """Log certificate-related event."""
        event = CertificateEvent(
            certificate_id=certificate_id,
            operation=operation,
            certificate_subject=certificate_subject,
            certificate_issuer=certificate_issuer,
            expiry_date=None,  # Don't include datetime in event to avoid JSON serialization issues
            message=f"Certificate {operation}: {certificate_id}",
            **kwargs
        )
        
        # Add expiry_date to details if provided
        if expiry_date:
            event.details["expiry_date"] = expiry_date.isoformat()
        
        self.log_event(event)
    
    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: SecurityEventSeverity = SecurityEventSeverity.HIGH,
        **kwargs
    ):
        """Log security violation."""
        event = SecurityEvent(
            event_type=SecurityEventType.SECURITY_VIOLATION,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            message=f"Security violation: {violation_type} - {description}",
            details={"violation_type": violation_type, "description": description},
            **kwargs
        )
        self.log_event(event)
    
    def verify_audit_trail(self, audit_records: List[Dict[str, Any]]) -> bool:
        """Verify integrity of audit trail."""
        if not self.audit_trail:
            raise AuditTrailError("Audit trail not enabled")
        
        try:
            # Reset audit trail state for verification
            temp_audit = AuditTrail(self.audit_trail.secret_key.decode('utf-8'))
            
            for record in audit_records:
                if not temp_audit.verify_audit_record(record.copy()):
                    return False
                # Update previous hash for next verification
                temp_audit.previous_hash = record.get("hash", "")
            
            return True
        except Exception as e:
            raise AuditTrailError(f"Audit trail verification failed: {e}")
    
    def shutdown(self):
        """Shutdown security logger gracefully."""
        if self.async_logging:
            # Signal shutdown
            self.stop_logging.set()
            
            # Cancel flush timer
            if hasattr(self, 'flush_timer'):
                self.flush_timer.cancel()
            
            # Put shutdown signal in queue
            try:
                self.log_queue.put_nowait(None)
            except:
                pass
            
            # Wait for logging thread to finish
            if self.logging_thread.is_alive():
                self.logging_thread.join(timeout=5.0)
            
            # Process remaining logs
            while not self.log_queue.empty():
                try:
                    log_entry = self.log_queue.get_nowait()
                    if log_entry is not None:
                        self._write_log_entry(log_entry)
                except Empty:
                    break
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()


# Global security logger instance
_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get global security logger instance."""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def configure_security_logger(
    log_level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    **kwargs
) -> SecurityLogger:
    """Configure global security logger."""
    global _security_logger
    if _security_logger:
        _security_logger.shutdown()
    
    _security_logger = SecurityLogger(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        **kwargs
    )
    return _security_logger


def shutdown_security_logger():
    """Shutdown global security logger."""
    global _security_logger
    if _security_logger:
        _security_logger.shutdown()
        _security_logger = None
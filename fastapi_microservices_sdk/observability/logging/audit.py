"""
Audit Logging and Compliance Features for FastAPI Microservices SDK.

This module provides enterprise-grade audit logging with tamper-proof timestamps,
compliance features for GDPR/HIPAA/SOX, and advanced security capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod

# Cryptographic imports
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from .config import LoggingConfig, ComplianceStandard
from .exceptions import AuditLogError, LogValidationError
from .structured_logger import StructuredLogger, LogRecord, LogEventType


class AuditEventType(str, Enum):
    """Audit event type enumeration."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    USER_DELETION = "user_deletion"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    PERMISSION_CHANGE = "permission_change"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ACCESS = "system_access"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    FINANCIAL_TRANSACTION = "financial_transaction"
    MEDICAL_ACCESS = "medical_access"
    ADMINISTRATIVE_ACTION = "administrative_action"


class AuditOutcome(str, Enum):
    """Audit outcome enumeration."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"
    ERROR = "error"


class ComplianceRisk(str, Enum):
    """Compliance risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditContext:
    """Context information for audit events."""
    
    # User information
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    user_email: Optional[str] = None
    
    # Session information
    session_id: Optional[str] = None
    session_start_time: Optional[str] = None
    
    # Request information
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_owner: Optional[str] = None
    
    # Organization information
    tenant_id: Optional[str] = None
    organization_id: Optional[str] = None
    department: Optional[str] = None
    
    # Technical information
    service_name: Optional[str] = None
    service_version: Optional[str] = None
    environment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AuditRecord:
    """Comprehensive audit record."""
    
    # Core audit fields
    audit_id: str
    timestamp: str
    event_type: AuditEventType
    event_description: str
    outcome: AuditOutcome
    
    # Context information
    context: AuditContext
    
    # Event details
    event_data: Dict[str, Any] = field(default_factory=dict)
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    
    # Compliance information
    compliance_standards: List[ComplianceStandard] = field(default_factory=list)
    risk_level: ComplianceRisk = ComplianceRisk.LOW
    retention_period: Optional[str] = None
    
    # Security information
    integrity_hash: Optional[str] = None
    digital_signature: Optional[str] = None
    tamper_proof_timestamp: Optional[str] = None
    
    # Additional metadata
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit record to dictionary."""
        data = asdict(self)
        # Convert context to dict
        data['context'] = self.context.to_dict()
        return data
    
    def to_json(self) -> str:
        """Convert audit record to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


class TamperProofTimestamp:
    """Tamper-proof timestamp generator."""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or "default-audit-secret"
    
    def generate(self, data: str) -> str:
        """Generate tamper-proof timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Create HMAC signature
        message = f"{timestamp}:{data}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{timestamp}:{signature}"
    
    def verify(self, tamper_proof_timestamp: str, data: str) -> bool:
        """Verify tamper-proof timestamp."""
        try:
            timestamp, signature = tamper_proof_timestamp.rsplit(':', 1)
            message = f"{timestamp}:{data}"
            
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False


class DigitalSigner:
    """Digital signature generator for audit records."""
    
    def __init__(self, private_key_pem: Optional[str] = None, public_key_pem: Optional[str] = None):
        self.private_key = None
        self.public_key = None
        
        if CRYPTOGRAPHY_AVAILABLE and private_key_pem:
            try:
                self.private_key = load_pem_private_key(
                    private_key_pem.encode(),
                    password=None
                )
            except Exception:
                pass
        
        if CRYPTOGRAPHY_AVAILABLE and public_key_pem:
            try:
                self.public_key = load_pem_public_key(public_key_pem.encode())
            except Exception:
                pass
    
    def sign(self, data: str) -> Optional[str]:
        """Generate digital signature for data."""
        if not CRYPTOGRAPHY_AVAILABLE or not self.private_key:
            return None
        
        try:
            signature = self.private_key.sign(
                data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return signature.hex()
        except Exception:
            return None
    
    def verify(self, data: str, signature: str) -> bool:
        """Verify digital signature."""
        if not CRYPTOGRAPHY_AVAILABLE or not self.public_key:
            return False
        
        try:
            signature_bytes = bytes.fromhex(signature)
            self.public_key.verify(
                signature_bytes,
                data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class ComplianceValidator:
    """Validator for compliance requirements."""
    
    def __init__(self, standards: List[ComplianceStandard]):
        self.standards = standards
    
    def validate_audit_record(self, record: AuditRecord) -> List[str]:
        """Validate audit record against compliance standards."""
        violations = []
        
        for standard in self.standards:
            if standard == ComplianceStandard.GDPR:
                violations.extend(self._validate_gdpr(record))
            elif standard == ComplianceStandard.HIPAA:
                violations.extend(self._validate_hipaa(record))
            elif standard == ComplianceStandard.SOX:
                violations.extend(self._validate_sox(record))
            elif standard == ComplianceStandard.PCI_DSS:
                violations.extend(self._validate_pci_dss(record))
        
        return violations
    
    def _validate_gdpr(self, record: AuditRecord) -> List[str]:
        """Validate GDPR compliance."""
        violations = []
        
        # Check for required fields
        if not record.context.user_id and record.event_type in [
            AuditEventType.DATA_ACCESS,
            AuditEventType.DATA_MODIFICATION,
            AuditEventType.DATA_DELETION
        ]:
            violations.append("GDPR: User identification required for data operations")
        
        # Check for lawful basis
        if record.event_type == AuditEventType.DATA_ACCESS:
            if 'lawful_basis' not in record.event_data:
                violations.append("GDPR: Lawful basis required for data access")
        
        # Check for data subject rights
        if record.event_type == AuditEventType.DATA_DELETION:
            if 'deletion_reason' not in record.event_data:
                violations.append("GDPR: Deletion reason required")
        
        return violations
    
    def _validate_hipaa(self, record: AuditRecord) -> List[str]:
        """Validate HIPAA compliance."""
        violations = []
        
        # Check for PHI access logging
        if record.event_type == AuditEventType.MEDICAL_ACCESS:
            required_fields = ['patient_id', 'healthcare_provider_id', 'access_purpose']
            for field in required_fields:
                if field not in record.event_data:
                    violations.append(f"HIPAA: {field} required for medical access")
        
        # Check for minimum necessary principle
        if record.event_type in [AuditEventType.DATA_ACCESS, AuditEventType.MEDICAL_ACCESS]:
            if 'access_justification' not in record.event_data:
                violations.append("HIPAA: Access justification required")
        
        return violations
    
    def _validate_sox(self, record: AuditRecord) -> List[str]:
        """Validate SOX compliance."""
        violations = []
        
        # Check for financial transaction logging
        if record.event_type == AuditEventType.FINANCIAL_TRANSACTION:
            required_fields = ['transaction_id', 'amount', 'approver_id']
            for field in required_fields:
                if field not in record.event_data:
                    violations.append(f"SOX: {field} required for financial transactions")
        
        # Check for segregation of duties
        if record.event_type == AuditEventType.CONFIGURATION_CHANGE:
            if 'approver_id' not in record.event_data:
                violations.append("SOX: Approver required for configuration changes")
        
        return violations
    
    def _validate_pci_dss(self, record: AuditRecord) -> List[str]:
        """Validate PCI-DSS compliance."""
        violations = []
        
        # Check for cardholder data access
        if 'cardholder_data' in str(record.event_data):
            if record.event_type != AuditEventType.SECURITY_EVENT:
                violations.append("PCI-DSS: Cardholder data access must be security event")
        
        return violations


class AuditLogger:
    """Enterprise audit logger with compliance features."""
    
    def __init__(
        self,
        config: LoggingConfig,
        structured_logger: StructuredLogger,
        compliance_standards: Optional[List[ComplianceStandard]] = None
    ):
        self.config = config
        self.structured_logger = structured_logger
        self.compliance_standards = compliance_standards or []
        
        # Initialize security components
        self.timestamp_generator = TamperProofTimestamp(
            config.security_config.encryption_key
        )
        
        self.digital_signer = DigitalSigner(
            config.security_config.signing_key,
            None  # Public key would be provided separately
        )
        
        self.compliance_validator = ComplianceValidator(self.compliance_standards)
        
        # Audit metrics
        self._audit_count = 0
        self._compliance_violations = 0
        self._last_audit_time = 0.0
    
    def audit(
        self,
        event_type: AuditEventType,
        event_description: str,
        context: AuditContext,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        event_data: Optional[Dict[str, Any]] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        risk_level: ComplianceRisk = ComplianceRisk.LOW,
        **kwargs
    ) -> str:
        """Create audit log entry."""
        
        # Generate audit ID
        audit_id = str(uuid.uuid4())
        
        # Create audit record
        record = AuditRecord(
            audit_id=audit_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            event_description=event_description,
            outcome=outcome,
            context=context,
            event_data=event_data or {},
            before_state=before_state,
            after_state=after_state,
            compliance_standards=self.compliance_standards,
            risk_level=risk_level,
            **kwargs
        )
        
        # Validate compliance
        violations = self.compliance_validator.validate_audit_record(record)
        if violations:
            self._compliance_violations += len(violations)
            record.event_data['compliance_violations'] = violations
            record.risk_level = ComplianceRisk.HIGH
        
        # Generate integrity hash
        record_json = record.to_json()
        record.integrity_hash = hashlib.sha256(record_json.encode()).hexdigest()
        
        # Generate tamper-proof timestamp
        record.tamper_proof_timestamp = self.timestamp_generator.generate(record_json)
        
        # Generate digital signature
        record.digital_signature = self.digital_signer.sign(record_json)
        
        # Log the audit record
        try:
            self.structured_logger.audit(
                f"AUDIT: {event_description}",
                extra={
                    'audit_record': record.to_dict(),
                    'audit_id': audit_id,
                    'event_type': event_type.value,
                    'outcome': outcome.value,
                    'risk_level': risk_level.value,
                    'compliance_standards': [std.value for std in self.compliance_standards],
                    'compliance_violations': violations
                }
            )
            
            # Update metrics
            self._audit_count += 1
            self._last_audit_time = time.time()
            
            return audit_id
            
        except Exception as e:
            raise AuditLogError(
                message=f"Failed to create audit log: {e}",
                audit_event=event_type.value,
                user_id=context.user_id,
                resource_id=context.resource_id,
                original_error=e
            )
    
    def verify_audit_record(self, record: AuditRecord) -> bool:
        """Verify the integrity of an audit record."""
        try:
            # Verify integrity hash
            record_copy = AuditRecord(**record.to_dict())
            record_copy.integrity_hash = None
            record_copy.digital_signature = None
            record_copy.tamper_proof_timestamp = None
            
            expected_hash = hashlib.sha256(record_copy.to_json().encode()).hexdigest()
            if record.integrity_hash != expected_hash:
                return False
            
            # Verify tamper-proof timestamp
            if record.tamper_proof_timestamp:
                if not self.timestamp_generator.verify(
                    record.tamper_proof_timestamp,
                    record_copy.to_json()
                ):
                    return False
            
            # Verify digital signature
            if record.digital_signature:
                if not self.digital_signer.verify(
                    record_copy.to_json(),
                    record.digital_signature
                ):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_audit_metrics(self) -> Dict[str, Any]:
        """Get audit logging metrics."""
        return {
            'audit_count': self._audit_count,
            'compliance_violations': self._compliance_violations,
            'violation_rate': self._compliance_violations / max(1, self._audit_count),
            'last_audit_time': self._last_audit_time,
            'compliance_standards': [std.value for std in self.compliance_standards],
            'cryptography_available': CRYPTOGRAPHY_AVAILABLE
        }


# Convenience functions for common audit events
def audit_user_login(
    audit_logger: AuditLogger,
    user_id: str,
    user_name: str,
    source_ip: str,
    success: bool = True,
    **kwargs
) -> str:
    """Audit user login event."""
    context = AuditContext(
        user_id=user_id,
        user_name=user_name,
        source_ip=source_ip,
        **kwargs
    )
    
    return audit_logger.audit(
        event_type=AuditEventType.USER_LOGIN,
        event_description=f"User {user_name} login attempt",
        context=context,
        outcome=AuditOutcome.SUCCESS if success else AuditOutcome.FAILURE,
        event_data={
            'login_method': kwargs.get('login_method', 'password'),
            'user_agent': kwargs.get('user_agent'),
            'session_id': kwargs.get('session_id')
        }
    )


def audit_data_access(
    audit_logger: AuditLogger,
    user_id: str,
    resource_type: str,
    resource_id: str,
    access_type: str = "read",
    **kwargs
) -> str:
    """Audit data access event."""
    context = AuditContext(
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        **kwargs
    )
    
    return audit_logger.audit(
        event_type=AuditEventType.DATA_ACCESS,
        event_description=f"Data access: {access_type} {resource_type}",
        context=context,
        outcome=AuditOutcome.SUCCESS,
        event_data={
            'access_type': access_type,
            'lawful_basis': kwargs.get('lawful_basis', 'legitimate_interest'),
            'access_justification': kwargs.get('access_justification')
        },
        risk_level=ComplianceRisk.MEDIUM if access_type in ['write', 'delete'] else ComplianceRisk.LOW
    )


def audit_configuration_change(
    audit_logger: AuditLogger,
    user_id: str,
    config_type: str,
    config_id: str,
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    **kwargs
) -> str:
    """Audit configuration change event."""
    context = AuditContext(
        user_id=user_id,
        resource_type=config_type,
        resource_id=config_id,
        **kwargs
    )
    
    return audit_logger.audit(
        event_type=AuditEventType.CONFIGURATION_CHANGE,
        event_description=f"Configuration change: {config_type}",
        context=context,
        outcome=AuditOutcome.SUCCESS,
        event_data={
            'change_reason': kwargs.get('change_reason'),
            'approver_id': kwargs.get('approver_id')
        },
        before_state=before_state,
        after_state=after_state,
        risk_level=ComplianceRisk.HIGH
    )


# Export main classes and functions
__all__ = [
    'AuditEventType',
    'AuditOutcome',
    'ComplianceRisk',
    'AuditContext',
    'AuditRecord',
    'TamperProofTimestamp',
    'DigitalSigner',
    'ComplianceValidator',
    'AuditLogger',
    'audit_user_login',
    'audit_data_access',
    'audit_configuration_change',
    'CRYPTOGRAPHY_AVAILABLE',
]
"""
Advanced Security Exceptions for FastAPI Microservices SDK.
This module defines the exception hierarchy for advanced security features
including mTLS, RBAC, ABAC, certificate management, threat detection, and security logging.
"""
from typing import Optional, Dict, Any
from ...exceptions import SecurityError


class AdvancedSecurityError(SecurityError):
    """
    Base exception for advanced security features.
    This is the parent class for all advanced security-related exceptions,
    providing common functionality and error handling patterns.
    """
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": str(self),
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }


class MTLSError(AdvancedSecurityError):
    """
    Mutual TLS related errors.
    Raised when mTLS operations fail, including certificate validation,
    handshake failures, and configuration issues.
    """
    def __init__(
        self, 
        message: str, 
        certificate_info: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.certificate_info = certificate_info or {}
        if certificate_info:
            self.details.update({"certificate_info": certificate_info})


class CertificateError(AdvancedSecurityError):
    """
    Certificate management errors.
    Raised when certificate operations fail, including loading, validation,
    rotation, and storage issues.
    """
    def __init__(
        self, 
        message: str, 
        certificate_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.certificate_id = certificate_id
        self.operation = operation
        if certificate_id:
            self.details["certificate_id"] = certificate_id
        if operation:
            self.details["operation"] = operation


class CertificateValidationError(CertificateError):
    """Certificate validation specific errors."""
    def __init__(
        self, 
        message: str, 
        validation_errors: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, operation="validation", **kwargs)
        self.validation_errors = validation_errors or []
        if validation_errors:
            self.details["validation_errors"] = validation_errors


class CertificateRotationError(CertificateError):
    """Certificate rotation specific errors."""
    def __init__(
        self, 
        message: str, 
        rotation_stage: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation="rotation", **kwargs)
        self.rotation_stage = rotation_stage
        if rotation_stage:
            self.details["rotation_stage"] = rotation_stage


class RBACError(AdvancedSecurityError):
    """
    Role-Based Access Control errors.
    Raised when RBAC operations fail, including role assignment,
    permission checking, and policy evaluation.
    """
    def __init__(
        self, 
        message: str, 
        user_id: Optional[str] = None,
        role: Optional[str] = None,
        permission: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.user_id = user_id
        self.role = role
        self.permission = permission
        if user_id:
            self.details["user_id"] = user_id
        if role:
            self.details["role"] = role
        if permission:
            self.details["permission"] = permission


class RoleNotFoundError(RBACError):
    """Specific error for when a role is not found."""
    def __init__(self, message: str = None, role: str = None, **kwargs):
        if message is None and role:
            message = f"Role not found: {role}"
        elif message is None:
            message = "Role not found"
        super().__init__(message, role=role, **kwargs)


class PermissionDeniedError(RBACError):
    """Specific error for permission denied scenarios."""
    def __init__(
        self, 
        message: str = None,
        user_id: str = None, 
        permission: str = None, 
        user_roles: Optional[list] = None,
        **kwargs
    ):
        if message is None and user_id and permission:
            message = f"Permission denied for user {user_id}: {permission}"
        elif message is None:
            message = "Permission denied"
        super().__init__(message, user_id=user_id, permission=permission, **kwargs)
        if user_roles:
            self.details["user_roles"] = user_roles


class RoleError(RBACError):
    """Role-specific errors in RBAC operations."""
    def __init__(
        self, 
        message: str, 
        role_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, role=role_id, **kwargs)
        self.role_id = role_id
        self.operation = operation
        if operation:
            self.details["operation"] = operation


class PermissionError(RBACError):
    """Permission-specific errors in RBAC operations."""
    def __init__(
        self, 
        message: str, 
        permission_id: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, permission=permission_id, **kwargs)
        self.permission_id = permission_id
        self.operation = operation
        if operation:
            self.details["operation"] = operation


class ABACError(AdvancedSecurityError):
    """
    Attribute-Based Access Control errors.
    Raised when ABAC operations fail, including policy evaluation,
    attribute retrieval, and context analysis.
    """
    def __init__(
        self, 
        message: str, 
        policy_name: Optional[str] = None,
        subject: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.policy_name = policy_name
        self.subject = subject
        self.resource = resource
        self.action = action
        if policy_name:
            self.details["policy_name"] = policy_name
        if subject:
            self.details["subject"] = subject
        if resource:
            self.details["resource"] = resource
        if action:
            self.details["action"] = action


class PolicyEvaluationError(ABACError):
    """Policy evaluation specific errors."""
    def __init__(
        self, 
        message: str, 
        evaluation_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.evaluation_context = evaluation_context or {}
        if evaluation_context:
            self.details["evaluation_context"] = evaluation_context


class AttributeError(ABACError):
    """Attribute retrieval and validation errors."""
    def __init__(
        self, 
        message: str, 
        attribute_name: Optional[str] = None,
        attribute_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.attribute_name = attribute_name
        self.attribute_type = attribute_type
        if attribute_name:
            self.details["attribute_name"] = attribute_name
        if attribute_type:
            self.details["attribute_type"] = attribute_type


class ThreatDetectionError(AdvancedSecurityError):
    """
    Threat detection errors.
    Raised when threat detection operations fail, including rule evaluation,
    anomaly detection, and response actions.
    """
    def __init__(
        self, 
        message: str, 
        threat_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        detection_rule: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.threat_type = threat_type
        self.confidence_score = confidence_score
        self.detection_rule = detection_rule
        if threat_type:
            self.details["threat_type"] = threat_type
        if confidence_score is not None:
            self.details["confidence_score"] = confidence_score
        if detection_rule:
            self.details["detection_rule"] = detection_rule


class ThreatDetectedError(ThreatDetectionError):
    """Specific error raised when a threat is detected."""
    def __init__(
        self, 
        message: str = None,
        threat_type: str = None, 
        confidence_score: float = None,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ):
        if message is None and threat_type and confidence_score is not None:
            message = f"Threat detected: {threat_type} (confidence: {confidence_score:.2f})"
        elif message is None:
            message = "Threat detected"
        super().__init__(
            message, 
            threat_type=threat_type, 
            confidence_score=confidence_score,
            **kwargs
        )
        if source_ip:
            self.details["source_ip"] = source_ip
        if user_id:
            self.details["user_id"] = user_id


class SecurityLoggingError(AdvancedSecurityError):
    """
    Security logging errors.
    Raised when security logging operations fail, including log writing,
    audit trail maintenance, and log rotation.
    """
    def __init__(
        self, 
        message: str, 
        log_operation: Optional[str] = None,
        log_level: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.log_operation = log_operation
        self.log_level = log_level
        if log_operation:
            self.details["log_operation"] = log_operation
        if log_level:
            self.details["log_level"] = log_level


class SecurityConfigurationError(AdvancedSecurityError):
    """
    Security configuration errors.
    Raised when security configuration operations fail, including loading,
    validation, and updating configuration.
    """
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_source: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_source = config_source
        if config_key:
            self.details["config_key"] = config_key
        if config_source:
            self.details["config_source"] = config_source


class AuditTrailError(SecurityLoggingError):
    """Audit trail specific errors."""
    def __init__(
        self, 
        message: str, 
        audit_event_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, log_operation="audit_trail", **kwargs)
        self.audit_event_id = audit_event_id
        if audit_event_id:
            self.details["audit_event_id"] = audit_event_id


class LogRotationError(SecurityLoggingError):
    """Log rotation specific errors."""
    def __init__(
        self, 
        message: str, 
        log_file: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, log_operation="rotation", **kwargs)
        self.log_file = log_file
        if log_file:
            self.details["log_file"] = log_file


# Exception mapping for easy lookup
EXCEPTION_MAP = {
    "mtls": MTLSError,
    "certificate": CertificateError,
    "certificate_validation": CertificateValidationError,
    "certificate_rotation": CertificateRotationError,
    "rbac": RBACError,
    "role_not_found": RoleNotFoundError,
    "permission_denied": PermissionDeniedError,
    "role_error": RoleError,
    "permission_error": PermissionError,
    "abac": ABACError,
    "policy_evaluation": PolicyEvaluationError,
    "attribute": AttributeError,
    "threat_detection": ThreatDetectionError,
    "threat_detected": ThreatDetectedError,
    "security_logging": SecurityLoggingError,
    "security_configuration": SecurityConfigurationError,
    "audit_trail": AuditTrailError,
    "log_rotation": LogRotationError,
}


def create_security_exception(
    exception_type: str, 
    message: str, 
    **kwargs
) -> AdvancedSecurityError:
    """
    Factory function to create security exceptions by type.
    
    Args:
        exception_type: Type of exception to create
        message: Error message
        **kwargs: Additional arguments for the exception
    
    Returns:
        Appropriate security exception instance
    
    Raises:
        ValueError: If exception_type is not recognized
    """
    if exception_type not in EXCEPTION_MAP:
        raise ValueError(f"Unknown exception type: {exception_type}")
    
    exception_class = EXCEPTION_MAP[exception_type]
    return exception_class(message, **kwargs)
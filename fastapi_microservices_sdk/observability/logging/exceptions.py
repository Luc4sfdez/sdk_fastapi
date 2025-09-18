"""
Logging-specific exceptions for FastAPI Microservices SDK.

This module defines custom exceptions for the logging system,
providing detailed error information and context for debugging.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from ..exceptions import ObservabilityError


class LoggingError(ObservabilityError):
    """Base exception for logging-related errors."""
    
    def __init__(
        self,
        message: str,
        logger_name: Optional[str] = None,
        log_level: Optional[str] = None,
        original_error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, original_error, context)
        self.logger_name = logger_name
        self.log_level = log_level


class LogFormatError(LoggingError):
    """Exception raised when log formatting fails."""
    
    def __init__(
        self,
        message: str,
        formatter_type: Optional[str] = None,
        log_record: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'formatter_type': formatter_type,
                'log_record': log_record
            }
        )
        self.formatter_type = formatter_type
        self.log_record = log_record


class LogShippingError(LoggingError):
    """Exception raised when log shipping fails."""
    
    def __init__(
        self,
        message: str,
        destination: Optional[str] = None,
        batch_size: Optional[int] = None,
        retry_count: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'destination': destination,
                'batch_size': batch_size,
                'retry_count': retry_count
            }
        )
        self.destination = destination
        self.batch_size = batch_size
        self.retry_count = retry_count


class LogValidationError(LoggingError):
    """Exception raised when log validation fails."""
    
    def __init__(
        self,
        message: str,
        schema_name: Optional[str] = None,
        validation_errors: Optional[list] = None,
        log_data: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'schema_name': schema_name,
                'validation_errors': validation_errors,
                'log_data': log_data
            }
        )
        self.schema_name = schema_name
        self.validation_errors = validation_errors or []
        self.log_data = log_data


class LogRetentionError(LoggingError):
    """Exception raised when log retention operations fail."""
    
    def __init__(
        self,
        message: str,
        retention_policy: Optional[str] = None,
        log_age: Optional[str] = None,
        cleanup_operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'retention_policy': retention_policy,
                'log_age': log_age,
                'cleanup_operation': cleanup_operation
            }
        )
        self.retention_policy = retention_policy
        self.log_age = log_age
        self.cleanup_operation = cleanup_operation


class ELKConnectionError(LoggingError):
    """Exception raised when ELK stack connection fails."""
    
    def __init__(
        self,
        message: str,
        elk_component: Optional[str] = None,
        endpoint: Optional[str] = None,
        connection_timeout: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'elk_component': elk_component,
                'endpoint': endpoint,
                'connection_timeout': connection_timeout
            }
        )
        self.elk_component = elk_component
        self.endpoint = endpoint
        self.connection_timeout = connection_timeout


class LogCorrelationError(LoggingError):
    """Exception raised when log correlation fails."""
    
    def __init__(
        self,
        message: str,
        correlation_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'correlation_type': correlation_type,
                'trace_id': trace_id,
                'span_id': span_id
            }
        )
        self.correlation_type = correlation_type
        self.trace_id = trace_id
        self.span_id = span_id


class DataMaskingError(LoggingError):
    """Exception raised when data masking fails."""
    
    def __init__(
        self,
        message: str,
        masking_rule: Optional[str] = None,
        field_name: Optional[str] = None,
        data_type: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'masking_rule': masking_rule,
                'field_name': field_name,
                'data_type': data_type
            }
        )
        self.masking_rule = masking_rule
        self.field_name = field_name
        self.data_type = data_type


class AuditLogError(LoggingError):
    """Exception raised when audit logging fails."""
    
    def __init__(
        self,
        message: str,
        audit_event: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        compliance_standard: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'audit_event': audit_event,
                'user_id': user_id,
                'resource_id': resource_id,
                'compliance_standard': compliance_standard
            }
        )
        self.audit_event = audit_event
        self.user_id = user_id
        self.resource_id = resource_id
        self.compliance_standard = compliance_standard


class LogBufferError(LoggingError):
    """Exception raised when log buffering fails."""
    
    def __init__(
        self,
        message: str,
        buffer_size: Optional[int] = None,
        buffer_type: Optional[str] = None,
        flush_interval: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message=message,
            original_error=original_error,
            context={
                'buffer_size': buffer_size,
                'buffer_type': buffer_type,
                'flush_interval': flush_interval
            }
        )
        self.buffer_size = buffer_size
        self.buffer_type = buffer_type
        self.flush_interval = flush_interval


# Export all exceptions
__all__ = [
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
]
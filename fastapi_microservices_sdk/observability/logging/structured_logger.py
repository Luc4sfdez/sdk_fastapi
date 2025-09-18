"""
Structured Logger for FastAPI Microservices SDK.

This module provides enterprise-grade structured logging with JSON formatting,
schema validation, trace correlation, and ELK integration.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import json
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from contextvars import ContextVar
from enum import Enum

# OpenTelemetry imports for trace correlation
try:
    from opentelemetry import trace
    from opentelemetry.trace import get_current_span, format_trace_id, format_span_id
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from .config import LoggingConfig, LogLevel, LogFormat
from .exceptions import LoggingError, LogFormatError, LogValidationError


# Context variables for correlation
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class LogEventType(str, Enum):
    """Log event type enumeration."""
    APPLICATION = "application"
    SECURITY = "security"
    AUDIT = "audit"
    PERFORMANCE = "performance"
    ERROR = "error"
    BUSINESS = "business"
    SYSTEM = "system"


@dataclass
class LogRecord:
    """Structured log record."""
    
    # Core fields
    timestamp: str
    level: str
    logger_name: str
    message: str
    
    # Service information
    service_name: str
    service_version: str
    environment: str
    
    # Correlation fields
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    
    # Context fields
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
    
    # Technical fields
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    hostname: Optional[str] = None
    
    # Event information
    event_type: LogEventType = LogEventType.APPLICATION
    event_category: Optional[str] = None
    event_action: Optional[str] = None
    
    # Additional data
    extra: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Error information
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    exception_traceback: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log record to dictionary."""
        data = asdict(self)
        
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """Convert log record to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


class LogSchema:
    """Log schema validator."""
    
    def __init__(self, required_fields: Optional[List[str]] = None):
        self.required_fields = required_fields or [
            'timestamp', 'level', 'logger_name', 'message',
            'service_name', 'service_version', 'environment'
        ]
    
    def validate(self, log_data: Dict[str, Any]) -> bool:
        """Validate log data against schema."""
        try:
            # Check required fields
            missing_fields = []
            for field in self.required_fields:
                if field not in log_data:
                    missing_fields.append(field)
            
            if missing_fields:
                raise LogValidationError(
                    message=f"Missing required fields: {missing_fields}",
                    schema_name="default",
                    validation_errors=missing_fields,
                    log_data=log_data
                )
            
            # Validate field types
            type_errors = []
            
            # Timestamp should be string
            if not isinstance(log_data.get('timestamp'), str):
                type_errors.append("timestamp must be string")
            
            # Level should be valid log level
            if log_data.get('level') not in [level.value for level in LogLevel]:
                type_errors.append(f"level must be one of {[level.value for level in LogLevel]}")
            
            # Message should be string
            if not isinstance(log_data.get('message'), str):
                type_errors.append("message must be string")
            
            if type_errors:
                raise LogValidationError(
                    message=f"Type validation errors: {type_errors}",
                    schema_name="default",
                    validation_errors=type_errors,
                    log_data=log_data
                )
            
            return True
            
        except LogValidationError:
            raise
        except Exception as e:
            raise LogValidationError(
                message=f"Schema validation failed: {e}",
                schema_name="default",
                original_error=e,
                log_data=log_data
            )


class StructuredLogger:
    """Enterprise-grade structured logger."""
    
    def __init__(
        self,
        name: str,
        config: LoggingConfig,
        schema: Optional[LogSchema] = None
    ):
        self.name = name
        self.config = config
        self.schema = schema or LogSchema()
        
        # Create underlying logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, config.root_level.value))
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Performance tracking
        self._log_count = 0
        self._error_count = 0
        self._last_log_time = 0.0
        
        # Correlation tracking
        self._correlation_extractors: List[Callable[[], Dict[str, Any]]] = []
        
        # Add default correlation extractors
        self._add_default_extractors()
    
    def _add_default_extractors(self):
        """Add default correlation extractors."""
        
        def extract_context_vars():
            """Extract correlation data from context variables."""
            return {
                'correlation_id': correlation_id_var.get(),
                'request_id': request_id_var.get(),
                'user_id': user_id_var.get(),
            }
        
        def extract_opentelemetry():
            """Extract correlation data from OpenTelemetry."""
            if not OPENTELEMETRY_AVAILABLE:
                return {}
            
            try:
                span = get_current_span()
                if span and span.is_recording():
                    span_context = span.get_span_context()
                    return {
                        'trace_id': format_trace_id(span_context.trace_id),
                        'span_id': format_span_id(span_context.span_id),
                    }
            except Exception:
                pass
            
            return {}
        
        self._correlation_extractors.extend([
            extract_context_vars,
            extract_opentelemetry
        ])
    
    def add_correlation_extractor(self, extractor: Callable[[], Dict[str, Any]]):
        """Add custom correlation extractor."""
        self._correlation_extractors.append(extractor)
    
    def _extract_correlation_data(self) -> Dict[str, Any]:
        """Extract correlation data from all extractors."""
        correlation_data = {}
        
        for extractor in self._correlation_extractors:
            try:
                data = extractor()
                if data:
                    correlation_data.update(data)
            except Exception as e:
                # Log extraction errors but don't fail logging
                pass
        
        return correlation_data
    
    def _create_log_record(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        event_type: LogEventType = LogEventType.APPLICATION,
        **kwargs
    ) -> LogRecord:
        """Create structured log record."""
        
        # Get current timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract correlation data
        correlation_data = self._extract_correlation_data()
        
        # Get thread and process info if enabled
        thread_id = threading.get_ident() if self.config.include_thread_info else None
        process_id = os.getpid() if self.config.include_process_info else None
        
        # Get hostname
        hostname = None
        try:
            import socket
            hostname = socket.gethostname()
        except Exception:
            pass
        
        # Handle exception information
        exception_type = None
        exception_message = None
        exception_traceback = None
        
        if exception:
            exception_type = type(exception).__name__
            exception_message = str(exception)
            
            # Get traceback if available
            try:
                import traceback
                exception_traceback = traceback.format_exc()
            except Exception:
                pass
        
        # Create log record
        record = LogRecord(
            timestamp=timestamp,
            level=level.value,
            logger_name=self.name,
            message=message,
            service_name=self.config.service_name,
            service_version=self.config.service_version,
            environment=self.config.environment,
            event_type=event_type,
            thread_id=thread_id,
            process_id=process_id,
            hostname=hostname,
            exception_type=exception_type,
            exception_message=exception_message,
            exception_traceback=exception_traceback,
            extra=extra or {},
            **correlation_data,
            **kwargs
        )
        
        return record
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        event_type: LogEventType = LogEventType.APPLICATION,
        **kwargs
    ):
        """Internal logging method."""
        
        with self._lock:
            try:
                # Create log record
                record = self._create_log_record(
                    level=level,
                    message=message,
                    extra=extra,
                    exception=exception,
                    event_type=event_type,
                    **kwargs
                )
                
                # Validate record
                record_dict = record.to_dict()
                self.schema.validate(record_dict)
                
                # Format record based on configuration
                if self.config.log_format == LogFormat.JSON:
                    formatted_message = record.to_json()
                else:
                    formatted_message = f"{record.timestamp} [{record.level}] {record.logger_name}: {record.message}"
                
                # Log using underlying logger
                log_level = getattr(logging, level.value)
                self._logger.log(log_level, formatted_message, extra={'structured_record': record_dict})
                
                # Update metrics
                self._log_count += 1
                self._last_log_time = time.time()
                
            except Exception as e:
                self._error_count += 1
                # Fallback to simple logging
                try:
                    self._logger.error(f"Structured logging failed: {e}. Original message: {message}")
                except Exception:
                    # Last resort - print to stderr
                    import sys
                    print(f"LOGGING FAILURE: {e}. Original: {message}", file=sys.stderr)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message."""
        self._log(LogLevel.ERROR, message, exception=exception, event_type=LogEventType.ERROR, **kwargs)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, exception=exception, event_type=LogEventType.ERROR, **kwargs)
    
    def audit(self, message: str, **kwargs):
        """Log audit message."""
        self._log(LogLevel.INFO, message, event_type=LogEventType.AUDIT, **kwargs)
    
    def security(self, message: str, **kwargs):
        """Log security message."""
        self._log(LogLevel.WARNING, message, event_type=LogEventType.SECURITY, **kwargs)
    
    def performance(self, message: str, duration_ms: Optional[float] = None, **kwargs):
        """Log performance message."""
        self._log(
            LogLevel.INFO, 
            message, 
            event_type=LogEventType.PERFORMANCE,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def business(self, message: str, **kwargs):
        """Log business event message."""
        self._log(LogLevel.INFO, message, event_type=LogEventType.BUSINESS, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logger metrics."""
        with self._lock:
            return {
                'logger_name': self.name,
                'log_count': self._log_count,
                'error_count': self._error_count,
                'error_rate': self._error_count / max(1, self._log_count),
                'last_log_time': self._last_log_time,
                'config': {
                    'level': self.config.root_level.value,
                    'format': self.config.log_format.value,
                    'service_name': self.config.service_name,
                    'environment': self.config.environment
                }
            }


# Global logger registry
_logger_registry: Dict[str, StructuredLogger] = {}
_registry_lock = threading.RLock()


def create_logger(
    name: str,
    config: Optional[LoggingConfig] = None,
    schema: Optional[LogSchema] = None
) -> StructuredLogger:
    """Create a structured logger."""
    
    if config is None:
        config = LoggingConfig()
    
    logger = StructuredLogger(name, config, schema)
    
    # Register logger
    with _registry_lock:
        _logger_registry[name] = logger
    
    return logger


def get_logger(name: str) -> Optional[StructuredLogger]:
    """Get logger from registry."""
    with _registry_lock:
        return _logger_registry.get(name)


def get_all_loggers() -> Dict[str, StructuredLogger]:
    """Get all registered loggers."""
    with _registry_lock:
        return _logger_registry.copy()


# Correlation context managers
def set_correlation_id(correlation_id: str):
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def set_request_id(request_id: str):
    """Set request ID in context."""
    request_id_var.set(request_id)


def set_user_id(user_id: str):
    """Set user ID in context."""
    user_id_var.set(user_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from context."""
    return correlation_id_var.get()


def generate_correlation_id() -> str:
    """Generate new correlation ID."""
    return str(uuid.uuid4())


# Import os for process info
import os


# Export main classes and functions
__all__ = [
    'LogEventType',
    'LogRecord',
    'LogSchema',
    'StructuredLogger',
    'create_logger',
    'get_logger',
    'get_all_loggers',
    'set_correlation_id',
    'set_request_id',
    'set_user_id',
    'get_correlation_id',
    'generate_correlation_id',
]
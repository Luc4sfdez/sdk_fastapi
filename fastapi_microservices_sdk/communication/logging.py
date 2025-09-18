"""
Communication Logging for FastAPI Microservices SDK.

This module provides structured logging capabilities for communication components
with correlation ID tracking and integration with the security logging system.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextvars import ContextVar

# Integration with security logging
try:
    from ..security.advanced.logging import SecurityLogger, SecurityEvent
    SECURITY_LOGGING_AVAILABLE = True
except ImportError:
    SECURITY_LOGGING_AVAILABLE = False


class CommunicationEventType(str, Enum):
    """Types of communication events."""
    HTTP_REQUEST = "http_request"
    HTTP_RESPONSE = "http_response"
    MESSAGE_PUBLISH = "message_publish"
    MESSAGE_CONSUME = "message_consume"
    SERVICE_DISCOVERY = "service_discovery"
    GRPC_CALL = "grpc_call"
    GRPC_RESPONSE = "grpc_response"
    EVENT_SOURCING = "event_sourcing"
    CIRCUIT_BREAKER = "circuit_breaker"
    HEALTH_CHECK = "health_check"
    CONNECTION = "connection"
    ERROR = "error"


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class CommunicationEvent:
    """Communication event for structured logging."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: CommunicationEventType = CommunicationEventType.HTTP_REQUEST
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    service_name: Optional[str] = None
    component: Optional[str] = None
    operation: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# Context variables for correlation tracking
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
service_name_context: ContextVar[Optional[str]] = ContextVar('service_name', default=None)


class CommunicationLogger:
    """
    Structured logger for communication events.
    
    Provides correlation ID tracking, structured logging, and integration
    with the security logging system.
    """
    
    def __init__(
        self,
        name: str = "communication",
        level: LogLevel = LogLevel.INFO,
        enable_security_integration: bool = True
    ):
        """
        Initialize communication logger.
        
        Args:
            name: Logger name
            level: Log level
            enable_security_integration: Enable integration with security logging
        """
        self.name = name
        self.level = level
        self.enable_security_integration = enable_security_integration and SECURITY_LOGGING_AVAILABLE
        
        # Standard Python logger
        self.logger = logging.getLogger(f"communication.{name}")
        self.logger.setLevel(getattr(logging, level.value))
        
        # Security logger integration
        if self.enable_security_integration:
            self.security_logger = SecurityLogger()
        else:
            self.security_logger = None
        
        # Event handlers
        self._event_handlers: List[callable] = []
    
    def _get_correlation_id(self) -> str:
        """Get or generate correlation ID."""
        correlation_id = correlation_id_context.get()
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
            correlation_id_context.set(correlation_id)
        return correlation_id
    
    def _get_service_name(self) -> Optional[str]:
        """Get service name from context."""
        return service_name_context.get()
    
    def _create_event(
        self,
        event_type: CommunicationEventType,
        message: str,
        **kwargs
    ) -> CommunicationEvent:
        """Create communication event."""
        return CommunicationEvent(
            event_type=event_type,
            correlation_id=self._get_correlation_id(),
            service_name=self._get_service_name(),
            component=self.name,
            operation=kwargs.get('operation'),
            status=kwargs.get('status'),
            duration_ms=kwargs.get('duration_ms'),
            metadata={
                'message': message,
                **kwargs.get('metadata', {})
            }
        )
    
    def _log_event(self, event: CommunicationEvent, level: LogLevel) -> None:
        """Log communication event."""
        # Standard logging
        log_data = event.to_dict()
        self.logger.log(
            getattr(logging, level.value),
            f"[{event.correlation_id}] {event.metadata.get('message', '')}",
            extra={'communication_event': log_data}
        )
        
        # Security logging integration
        if self.security_logger and event.event_type in [
            CommunicationEventType.ERROR,
            CommunicationEventType.HTTP_REQUEST,
            CommunicationEventType.GRPC_CALL
        ]:
            try:
                security_event = SecurityEvent(
                    event_type="communication",
                    component=event.component or "communication",
                    action=event.operation or event.event_type.value,
                    resource=event.service_name,
                    outcome="success" if event.status == "success" else "failure",
                    correlation_id=event.correlation_id,
                    metadata=event.metadata
                )
                self.security_logger.log_event(security_event)
            except Exception as e:
                self.logger.error(f"Failed to log security event: {e}")
        
        # Execute event handlers
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
    
    def debug(self, message: str, event_type: CommunicationEventType = CommunicationEventType.HTTP_REQUEST, **kwargs):
        """Log debug message."""
        event = self._create_event(event_type, message, **kwargs)
        self._log_event(event, LogLevel.DEBUG)
    
    def info(self, message: str, event_type: CommunicationEventType = CommunicationEventType.HTTP_REQUEST, **kwargs):
        """Log info message."""
        event = self._create_event(event_type, message, **kwargs)
        self._log_event(event, LogLevel.INFO)
    
    def warning(self, message: str, event_type: CommunicationEventType = CommunicationEventType.ERROR, **kwargs):
        """Log warning message."""
        event = self._create_event(event_type, message, **kwargs)
        self._log_event(event, LogLevel.WARNING)
    
    def error(self, message: str, event_type: CommunicationEventType = CommunicationEventType.ERROR, **kwargs):
        """Log error message."""
        event = self._create_event(event_type, message, **kwargs)
        self._log_event(event, LogLevel.ERROR)
    
    def critical(self, message: str, event_type: CommunicationEventType = CommunicationEventType.ERROR, **kwargs):
        """Log critical message."""
        event = self._create_event(event_type, message, **kwargs)
        self._log_event(event, LogLevel.CRITICAL)
    
    def log_http_request(
        self,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log HTTP request."""
        self.info(
            f"{method} {url}",
            event_type=CommunicationEventType.HTTP_REQUEST,
            operation=f"{method} {url}",
            status="success" if status_code and 200 <= status_code < 400 else "failure",
            duration_ms=duration_ms,
            metadata={
                'method': method,
                'url': url,
                'status_code': status_code,
                **kwargs
            }
        )
    
    def log_http_response(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """Log HTTP response."""
        level = LogLevel.INFO if 200 <= status_code < 400 else LogLevel.ERROR
        event_type = CommunicationEventType.HTTP_RESPONSE
        
        if level == LogLevel.INFO:
            self.info(
                f"{method} {url} -> {status_code} ({duration_ms:.2f}ms)",
                event_type=event_type,
                operation=f"{method} {url}",
                status="success",
                duration_ms=duration_ms,
                metadata={
                    'method': method,
                    'url': url,
                    'status_code': status_code,
                    **kwargs
                }
            )
        else:
            self.error(
                f"{method} {url} -> {status_code} ({duration_ms:.2f}ms)",
                event_type=event_type,
                operation=f"{method} {url}",
                status="failure",
                duration_ms=duration_ms,
                metadata={
                    'method': method,
                    'url': url,
                    'status_code': status_code,
                    **kwargs
                }
            )
    
    def log_message_publish(
        self,
        broker_type: str,
        topic: str,
        message_size: Optional[int] = None,
        **kwargs
    ):
        """Log message publish."""
        self.info(
            f"Published message to {broker_type}:{topic}",
            event_type=CommunicationEventType.MESSAGE_PUBLISH,
            operation=f"publish:{topic}",
            status="success",
            metadata={
                'broker_type': broker_type,
                'topic': topic,
                'message_size': message_size,
                **kwargs
            }
        )
    
    def log_message_consume(
        self,
        broker_type: str,
        topic: str,
        message_size: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        **kwargs
    ):
        """Log message consumption."""
        self.info(
            f"Consumed message from {broker_type}:{topic}",
            event_type=CommunicationEventType.MESSAGE_CONSUME,
            operation=f"consume:{topic}",
            status="success",
            duration_ms=processing_time_ms,
            metadata={
                'broker_type': broker_type,
                'topic': topic,
                'message_size': message_size,
                **kwargs
            }
        )
    
    def log_service_discovery(
        self,
        operation: str,
        service_name: str,
        backend: str,
        **kwargs
    ):
        """Log service discovery operation."""
        self.info(
            f"Service discovery {operation}: {service_name} via {backend}",
            event_type=CommunicationEventType.SERVICE_DISCOVERY,
            operation=f"{operation}:{service_name}",
            status="success",
            metadata={
                'operation': operation,
                'service_name': service_name,
                'backend': backend,
                **kwargs
            }
        )
    
    def log_grpc_call(
        self,
        service: str,
        method: str,
        status: str,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log gRPC call."""
        level = LogLevel.INFO if status == "success" else LogLevel.ERROR
        
        if level == LogLevel.INFO:
            self.info(
                f"gRPC call {service}/{method} -> {status}",
                event_type=CommunicationEventType.GRPC_CALL,
                operation=f"{service}/{method}",
                status=status,
                duration_ms=duration_ms,
                metadata={
                    'service': service,
                    'method': method,
                    **kwargs
                }
            )
        else:
            self.error(
                f"gRPC call {service}/{method} -> {status}",
                event_type=CommunicationEventType.GRPC_CALL,
                operation=f"{service}/{method}",
                status=status,
                duration_ms=duration_ms,
                metadata={
                    'service': service,
                    'method': method,
                    **kwargs
                }
            )
    
    def log_circuit_breaker(
        self,
        service_name: str,
        state: str,
        failure_count: int,
        **kwargs
    ):
        """Log circuit breaker state change."""
        level = LogLevel.WARNING if state == "open" else LogLevel.INFO
        
        if level == LogLevel.WARNING:
            self.warning(
                f"Circuit breaker {state} for {service_name} (failures: {failure_count})",
                event_type=CommunicationEventType.CIRCUIT_BREAKER,
                operation=f"circuit_breaker:{state}",
                status="failure" if state == "open" else "success",
                metadata={
                    'service_name': service_name,
                    'state': state,
                    'failure_count': failure_count,
                    **kwargs
                }
            )
        else:
            self.info(
                f"Circuit breaker {state} for {service_name}",
                event_type=CommunicationEventType.CIRCUIT_BREAKER,
                operation=f"circuit_breaker:{state}",
                status="success",
                metadata={
                    'service_name': service_name,
                    'state': state,
                    'failure_count': failure_count,
                    **kwargs
                }
            )
    
    def log_health_check(
        self,
        component: str,
        status: str,
        **kwargs
    ):
        """Log health check result."""
        level = LogLevel.INFO if status == "healthy" else LogLevel.ERROR
        
        if level == LogLevel.INFO:
            self.info(
                f"Health check {component}: {status}",
                event_type=CommunicationEventType.HEALTH_CHECK,
                operation=f"health_check:{component}",
                status="success",
                metadata={
                    'component': component,
                    'health_status': status,
                    **kwargs
                }
            )
        else:
            self.error(
                f"Health check {component}: {status}",
                event_type=CommunicationEventType.HEALTH_CHECK,
                operation=f"health_check:{component}",
                status="failure",
                metadata={
                    'component': component,
                    'health_status': status,
                    **kwargs
                }
            )
    
    def add_event_handler(self, handler: callable) -> None:
        """Add event handler."""
        self._event_handlers.append(handler)
    
    def remove_event_handler(self, handler: callable) -> None:
        """Remove event handler."""
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)


# Context managers for correlation tracking
class CorrelationContext:
    """Context manager for correlation ID tracking."""
    
    def __init__(self, correlation_id: Optional[str] = None, service_name: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.service_name = service_name
        self._correlation_token = None
        self._service_token = None
    
    def __enter__(self):
        self._correlation_token = correlation_id_context.set(self.correlation_id)
        if self.service_name:
            self._service_token = service_name_context.set(self.service_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        correlation_id_context.reset(self._correlation_token)
        if self._service_token:
            service_name_context.reset(self._service_token)


# Utility functions
def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_context.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_context.set(correlation_id)


def get_service_name() -> Optional[str]:
    """Get current service name from context."""
    return service_name_context.get()


def set_service_name(service_name: str) -> None:
    """Set service name in context."""
    service_name_context.set(service_name)


# Default logger instance
default_logger = CommunicationLogger()


# Convenience functions using default logger
def log_http_request(method: str, url: str, **kwargs):
    """Log HTTP request using default logger."""
    default_logger.log_http_request(method, url, **kwargs)


def log_http_response(method: str, url: str, status_code: int, duration_ms: float, **kwargs):
    """Log HTTP response using default logger."""
    default_logger.log_http_response(method, url, status_code, duration_ms, **kwargs)


def log_message_publish(broker_type: str, topic: str, **kwargs):
    """Log message publish using default logger."""
    default_logger.log_message_publish(broker_type, topic, **kwargs)


def log_message_consume(broker_type: str, topic: str, **kwargs):
    """Log message consumption using default logger."""
    default_logger.log_message_consume(broker_type, topic, **kwargs)
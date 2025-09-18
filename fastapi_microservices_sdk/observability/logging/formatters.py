"""
Log Formatters for FastAPI Microservices SDK.

This module provides various log formatters for different output formats
including JSON, ELK, compliance, and structured formats.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List, Pattern
from datetime import datetime
from abc import ABC, abstractmethod

from .config import LoggingConfig, LogFormat, ComplianceStandard
from .exceptions import LogFormatError
from .structured_logger import LogRecord


class BaseFormatter(ABC):
    """Base class for log formatters."""
    
    def __init__(self, config: LoggingConfig):
        self.config = config
    
    @abstractmethod
    def format(self, record: LogRecord) -> str:
        """Format log record."""
        pass
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data from log record."""
        if not self.config.security_config.enable_data_masking:
            return data
        
        sanitized = data.copy()
        
        # Apply PII protection
        if self.config.security_config.enable_pii_protection:
            for field in self.config.security_config.pii_fields:
                if field in sanitized:
                    sanitized[field] = self.config.security_config.pii_replacement
        
        # Apply pattern-based masking
        for field_name, pattern in self.config.security_config.masking_patterns.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            sanitized = self._apply_pattern_masking(sanitized, compiled_pattern, field_name)
        
        return sanitized
    
    def _apply_pattern_masking(
        self, 
        data: Dict[str, Any], 
        pattern: Pattern, 
        field_name: str
    ) -> Dict[str, Any]:
        """Apply pattern-based masking to data."""
        
        def mask_value(value):
            if isinstance(value, str):
                return pattern.sub(self.config.security_config.masking_replacement, value)
            elif isinstance(value, dict):
                return {k: mask_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [mask_value(item) for item in value]
            return value
        
        return {k: mask_value(v) for k, v in data.items()}


class JSONFormatter(BaseFormatter):
    """JSON log formatter."""
    
    def __init__(self, config: LoggingConfig, indent: Optional[int] = None):
        super().__init__(config)
        self.indent = indent
    
    def format(self, record: LogRecord) -> str:
        """Format log record as JSON."""
        try:
            # Convert record to dictionary
            data = record.to_dict()
            
            # Sanitize sensitive data
            data = self._sanitize_data(data)
            
            # Format as JSON
            return json.dumps(
                data,
                indent=self.indent,
                default=str,
                ensure_ascii=False,
                separators=(',', ':') if self.indent is None else None
            )
            
        except Exception as e:
            raise LogFormatError(
                message=f"Failed to format log record as JSON: {e}",
                formatter_type="json",
                log_record=record.to_dict(),
                original_error=e
            )


class ELKFormatter(BaseFormatter):
    """ELK stack optimized formatter."""
    
    def __init__(self, config: LoggingConfig):
        super().__init__(config)
    
    def format(self, record: LogRecord) -> str:
        """Format log record for ELK stack."""
        try:
            # Convert record to dictionary
            data = record.to_dict()
            
            # Sanitize sensitive data
            data = self._sanitize_data(data)
            
            # Add ELK-specific fields
            elk_data = {
                '@timestamp': data.get('timestamp'),
                '@version': '1',
                'host': data.get('hostname', 'unknown'),
                'source': f"{data.get('service_name', 'unknown')}-{data.get('environment', 'unknown')}",
                'type': 'application-log',
                'tags': data.get('tags', []) + [
                    f"service:{data.get('service_name', 'unknown')}",
                    f"environment:{data.get('environment', 'unknown')}",
                    f"level:{data.get('level', 'unknown')}"
                ],
                'fields': {
                    'service': {
                        'name': data.get('service_name'),
                        'version': data.get('service_version'),
                        'environment': data.get('environment')
                    },
                    'log': {
                        'level': data.get('level'),
                        'logger': data.get('logger_name'),
                        'message': data.get('message')
                    },
                    'trace': {
                        'id': data.get('trace_id'),
                        'span_id': data.get('span_id'),
                        'parent_span_id': data.get('parent_span_id')
                    },
                    'correlation': {
                        'id': data.get('correlation_id'),
                        'request_id': data.get('request_id'),
                        'user_id': data.get('user_id'),
                        'session_id': data.get('session_id'),
                        'tenant_id': data.get('tenant_id')
                    },
                    'event': {
                        'type': data.get('event_type'),
                        'category': data.get('event_category'),
                        'action': data.get('event_action')
                    },
                    'error': {
                        'type': data.get('exception_type'),
                        'message': data.get('exception_message'),
                        'stack_trace': data.get('exception_traceback')
                    } if data.get('exception_type') else None,
                    'performance': {
                        'duration_ms': data.get('duration_ms'),
                        'memory_usage_mb': data.get('memory_usage_mb'),
                        'cpu_usage_percent': data.get('cpu_usage_percent')
                    } if data.get('duration_ms') is not None else None,
                    'extra': data.get('extra', {})
                }
            }
            
            # Remove None values from nested structures
            elk_data['fields'] = {k: v for k, v in elk_data['fields'].items() if v is not None}
            
            return json.dumps(elk_data, default=str, ensure_ascii=False)
            
        except Exception as e:
            raise LogFormatError(
                message=f"Failed to format log record for ELK: {e}",
                formatter_type="elk",
                log_record=record.to_dict(),
                original_error=e
            )


class ComplianceFormatter(BaseFormatter):
    """Compliance-focused log formatter."""
    
    def __init__(self, config: LoggingConfig, standards: List[ComplianceStandard]):
        super().__init__(config)
        self.standards = standards
    
    def format(self, record: LogRecord) -> str:
        """Format log record for compliance requirements."""
        try:
            # Convert record to dictionary
            data = record.to_dict()
            
            # Apply extra sanitization for compliance
            data = self._sanitize_for_compliance(data)
            
            # Create compliance-focused structure
            compliance_data = {
                'timestamp': data.get('timestamp'),
                'event_id': f"{data.get('correlation_id', 'unknown')}-{hash(data.get('message', '')) % 10000:04d}",
                'severity': self._map_level_to_severity(data.get('level', 'INFO')),
                'source': {
                    'service': data.get('service_name'),
                    'version': data.get('service_version'),
                    'environment': data.get('environment'),
                    'host': data.get('hostname'),
                    'logger': data.get('logger_name')
                },
                'event': {
                    'type': data.get('event_type'),
                    'category': data.get('event_category'),
                    'action': data.get('event_action'),
                    'message': data.get('message'),
                    'outcome': 'success' if data.get('level') not in ['ERROR', 'CRITICAL'] else 'failure'
                },
                'user': {
                    'id': data.get('user_id'),
                    'session_id': data.get('session_id'),
                    'tenant_id': data.get('tenant_id')
                } if data.get('user_id') else None,
                'trace': {
                    'correlation_id': data.get('correlation_id'),
                    'request_id': data.get('request_id'),
                    'trace_id': data.get('trace_id'),
                    'span_id': data.get('span_id')
                },
                'compliance': {
                    'standards': [standard.value for standard in self.standards],
                    'retention_required': True,
                    'audit_trail': True,
                    'data_classification': self._classify_data_sensitivity(data)
                },
                'integrity': {
                    'checksum': self._calculate_checksum(data),
                    'signature': None  # Would be populated by digital signature if enabled
                },
                'additional_data': data.get('extra', {})
            }
            
            # Remove None values
            compliance_data = {k: v for k, v in compliance_data.items() if v is not None}
            
            return json.dumps(compliance_data, default=str, ensure_ascii=False)
            
        except Exception as e:
            raise LogFormatError(
                message=f"Failed to format log record for compliance: {e}",
                formatter_type="compliance",
                log_record=record.to_dict(),
                original_error=e
            )
    
    def _sanitize_for_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply extra sanitization for compliance requirements."""
        sanitized = self._sanitize_data(data)
        
        # Additional compliance-specific sanitization
        compliance_sensitive_fields = [
            'password', 'token', 'secret', 'key', 'auth', 'credential',
            'ssn', 'social_security', 'tax_id', 'passport', 'license',
            'medical_record', 'health_info', 'diagnosis', 'treatment',
            'financial_account', 'credit_card', 'bank_account', 'routing'
        ]
        
        for field in compliance_sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***COMPLIANCE_PROTECTED***"
        
        return sanitized
    
    def _map_level_to_severity(self, level: str) -> str:
        """Map log level to compliance severity."""
        mapping = {
            'DEBUG': 'informational',
            'INFO': 'informational',
            'WARNING': 'low',
            'ERROR': 'medium',
            'CRITICAL': 'high'
        }
        return mapping.get(level, 'informational')
    
    def _classify_data_sensitivity(self, data: Dict[str, Any]) -> str:
        """Classify data sensitivity level."""
        # Check for high sensitivity indicators
        high_sensitivity_indicators = [
            'password', 'ssn', 'credit_card', 'medical', 'financial',
            'authentication', 'authorization', 'security'
        ]
        
        data_str = json.dumps(data, default=str).lower()
        
        for indicator in high_sensitivity_indicators:
            if indicator in data_str:
                return 'high'
        
        # Check for medium sensitivity
        medium_sensitivity_indicators = [
            'user_id', 'email', 'phone', 'address', 'name'
        ]
        
        for indicator in medium_sensitivity_indicators:
            if indicator in data_str:
                return 'medium'
        
        return 'low'
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for integrity verification."""
        import hashlib
        
        # Create deterministic string representation
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(sorted_data.encode()).hexdigest()


class StructuredFormatter(BaseFormatter):
    """Human-readable structured formatter."""
    
    def __init__(self, config: LoggingConfig, include_extra: bool = True):
        super().__init__(config)
        self.include_extra = include_extra
    
    def format(self, record: LogRecord) -> str:
        """Format log record as structured text."""
        try:
            # Convert record to dictionary
            data = record.to_dict()
            
            # Sanitize sensitive data
            data = self._sanitize_data(data)
            
            # Build structured format
            lines = []
            
            # Header line
            header_parts = [
                data.get('timestamp', 'unknown'),
                f"[{data.get('level', 'UNKNOWN')}]",
                data.get('logger_name', 'unknown'),
            ]
            
            if data.get('correlation_id'):
                header_parts.append(f"({data['correlation_id'][:8]})")
            
            lines.append(' '.join(header_parts))
            
            # Message
            lines.append(f"Message: {data.get('message', 'No message')}")
            
            # Service info
            service_info = []
            if data.get('service_name'):
                service_info.append(f"service={data['service_name']}")
            if data.get('environment'):
                service_info.append(f"env={data['environment']}")
            if data.get('service_version'):
                service_info.append(f"version={data['service_version']}")
            
            if service_info:
                lines.append(f"Service: {', '.join(service_info)}")
            
            # Trace info
            trace_info = []
            if data.get('trace_id'):
                trace_info.append(f"trace={data['trace_id']}")
            if data.get('span_id'):
                trace_info.append(f"span={data['span_id']}")
            if data.get('request_id'):
                trace_info.append(f"request={data['request_id']}")
            
            if trace_info:
                lines.append(f"Trace: {', '.join(trace_info)}")
            
            # User context
            user_info = []
            if data.get('user_id'):
                user_info.append(f"user={data['user_id']}")
            if data.get('session_id'):
                user_info.append(f"session={data['session_id']}")
            if data.get('tenant_id'):
                user_info.append(f"tenant={data['tenant_id']}")
            
            if user_info:
                lines.append(f"User: {', '.join(user_info)}")
            
            # Error info
            if data.get('exception_type'):
                lines.append(f"Exception: {data['exception_type']}: {data.get('exception_message', 'No message')}")
                if data.get('exception_traceback'):
                    lines.append("Traceback:")
                    for line in data['exception_traceback'].split('\n'):
                        if line.strip():
                            lines.append(f"  {line}")
            
            # Performance info
            perf_info = []
            if data.get('duration_ms') is not None:
                perf_info.append(f"duration={data['duration_ms']:.2f}ms")
            if data.get('memory_usage_mb') is not None:
                perf_info.append(f"memory={data['memory_usage_mb']:.2f}MB")
            if data.get('cpu_usage_percent') is not None:
                perf_info.append(f"cpu={data['cpu_usage_percent']:.1f}%")
            
            if perf_info:
                lines.append(f"Performance: {', '.join(perf_info)}")
            
            # Extra data
            if self.include_extra and data.get('extra'):
                lines.append(f"Extra: {json.dumps(data['extra'], default=str)}")
            
            return '\n'.join(lines)
            
        except Exception as e:
            raise LogFormatError(
                message=f"Failed to format log record as structured text: {e}",
                formatter_type="structured",
                log_record=record.to_dict(),
                original_error=e
            )


class PlainFormatter(BaseFormatter):
    """Simple plain text formatter."""
    
    def format(self, record: LogRecord) -> str:
        """Format log record as plain text."""
        try:
            # Simple format: timestamp [level] logger: message
            return f"{record.timestamp} [{record.level}] {record.logger_name}: {record.message}"
            
        except Exception as e:
            raise LogFormatError(
                message=f"Failed to format log record as plain text: {e}",
                formatter_type="plain",
                log_record=record.to_dict(),
                original_error=e
            )


def create_formatter(
    format_type: LogFormat,
    config: LoggingConfig,
    **kwargs
) -> BaseFormatter:
    """Create formatter based on format type."""
    
    if format_type == LogFormat.JSON:
        return JSONFormatter(config, **kwargs)
    elif format_type == LogFormat.ELK:
        return ELKFormatter(config, **kwargs)
    elif format_type == LogFormat.COMPLIANCE:
        standards = kwargs.get('standards', [])
        return ComplianceFormatter(config, standards, **kwargs)
    elif format_type == LogFormat.STRUCTURED:
        return StructuredFormatter(config, **kwargs)
    elif format_type == LogFormat.PLAIN:
        return PlainFormatter(config, **kwargs)
    else:
        raise LogFormatError(
            message=f"Unsupported format type: {format_type}",
            formatter_type=format_type.value
        )


# Export main classes and functions
__all__ = [
    'BaseFormatter',
    'JSONFormatter',
    'ELKFormatter',
    'ComplianceFormatter',
    'StructuredFormatter',
    'PlainFormatter',
    'create_formatter',
]
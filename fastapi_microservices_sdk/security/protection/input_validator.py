"""
Input validation for FastAPI Microservices SDK.

This module provides advanced input validation capabilities for microservices.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator
from fastapi import HTTPException

from ...exceptions import ValidationError, SecurityError


class InputValidator:
    """Advanced input validator for microservices."""
    
    # Common regex patterns
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        'slug': r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
        'username': r'^[a-zA-Z0-9_]{3,20}$',
        'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        'ip_address': r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        'url': r'^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                # JavaScript injection
        r'on\w+\s*=',                 # Event handlers
        r'union\s+select',             # SQL injection
        r'drop\s+table',               # SQL injection
        r'insert\s+into',              # SQL injection
        r'delete\s+from',              # SQL injection
        r'\.\./.*',                    # Path traversal
        r'file://',                    # File protocol
        r'data:',                      # Data URLs
    ]
    
    @classmethod
    def validate_pattern(cls, value: str, pattern_name: str) -> bool:
        """Validate value against a named pattern."""
        if pattern_name not in cls.PATTERNS:
            raise ValidationError(f"Unknown pattern: {pattern_name}")
        
        pattern = cls.PATTERNS[pattern_name]
        return bool(re.match(pattern, value, re.IGNORECASE))
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email address."""
        return cls.validate_pattern(email, 'email')
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validate phone number."""
        return cls.validate_pattern(phone, 'phone')
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format."""
        return cls.validate_pattern(uuid_str, 'uuid')
    
    @classmethod
    def validate_slug(cls, slug: str) -> bool:
        """Validate URL slug."""
        return cls.validate_pattern(slug, 'slug')
    
    @classmethod
    def validate_username(cls, username: str) -> bool:
        """Validate username format."""
        return cls.validate_pattern(username, 'username')
    
    @classmethod
    def validate_password_strength(cls, password: str) -> bool:
        """Validate password strength."""
        return cls.validate_pattern(password, 'password')
    
    @classmethod
    def validate_ip_address(cls, ip: str) -> bool:
        """Validate IP address."""
        return cls.validate_pattern(ip, 'ip_address')
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Validate URL format."""
        return cls.validate_pattern(url, 'url')
    
    @classmethod
    def sanitize_input(cls, value: str) -> str:
        """Sanitize input by removing dangerous patterns."""
        if not isinstance(value, str):
            return value
        
        sanitized = value
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @classmethod
    def check_for_injection(cls, value: str) -> None:
        """Check for potential injection attacks."""
        if not isinstance(value, str):
            return
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise SecurityError(f"Potential injection attack detected: {pattern}")
    
    @classmethod
    def validate_length(cls, value: str, min_length: int = 0, max_length: int = 1000) -> bool:
        """Validate string length."""
        if not isinstance(value, str):
            return False
        
        return min_length <= len(value) <= max_length
    
    @classmethod
    def validate_json_structure(cls, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate JSON structure has required fields."""
        if not isinstance(data, dict):
            return False
        
        return all(field in data for field in required_fields)
    
    @classmethod
    def validate_and_sanitize(cls, value: str, pattern_name: Optional[str] = None) -> str:
        """Validate and sanitize input in one step."""
        # First sanitize
        sanitized = cls.sanitize_input(value)
        
        # Check for injection
        cls.check_for_injection(sanitized)
        
        # Validate pattern if provided
        if pattern_name and not cls.validate_pattern(sanitized, pattern_name):
            raise ValidationError(f"Value does not match pattern: {pattern_name}")
        
        return sanitized


class SecureBaseModel(BaseModel):
    """Base model with built-in security validation."""
    
    class Config:
        # Prevent extra fields
        extra = "forbid"
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True
    
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Override dict to sanitize output."""
        data = super().dict(**kwargs)
        return self._sanitize_dict(data)
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputValidator.sanitize_input(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputValidator.sanitize_input(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


# Validation decorators
def validate_input(pattern_name: Optional[str] = None, sanitize: bool = True):
    """Decorator to validate function input parameters."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate and sanitize string arguments
            new_args = []
            for arg in args:
                if isinstance(arg, str):
                    if sanitize:
                        arg = InputValidator.sanitize_input(arg)
                    if pattern_name:
                        if not InputValidator.validate_pattern(arg, pattern_name):
                            raise ValidationError(f"Invalid input format: {pattern_name}")
                    InputValidator.check_for_injection(arg)
                new_args.append(arg)
            
            # Validate and sanitize keyword arguments
            new_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, str):
                    if sanitize:
                        value = InputValidator.sanitize_input(value)
                    if pattern_name:
                        if not InputValidator.validate_pattern(value, pattern_name):
                            raise ValidationError(f"Invalid input format: {pattern_name}")
                    InputValidator.check_for_injection(value)
                new_kwargs[key] = value
            
            return func(*new_args, **new_kwargs)
        return wrapper
    return decorator


# FastAPI dependency for input validation
async def validate_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """FastAPI dependency to validate request data."""
    validated_data = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            # Sanitize and check for injection
            sanitized_value = InputValidator.sanitize_input(value)
            InputValidator.check_for_injection(sanitized_value)
            validated_data[key] = sanitized_value
        else:
            validated_data[key] = value
    
    return validated_data
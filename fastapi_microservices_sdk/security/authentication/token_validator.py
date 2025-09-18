# fastapi-microservices-sdk/fastapi_microservices_sdk/security/authentication/token_validator.py
"""
Advanced Token Validator for FastAPI Microservices SDK.

This module provides comprehensive token validation with support for
multiple token types, custom validation rules, and security policies.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
import logging
import hashlib

import jwt

from ...exceptions import SecurityError, ValidationError


class TokenValidator:
    """
    Advanced token validator with support for multiple validation strategies.
    
    Features:
    - Multiple token type support
    - Custom validation rules
    - Token blacklist management
    - Rate limiting per token
    - Audit logging
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        max_token_age_hours: int = 24,
        enable_blacklist: bool = True,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize Token Validator.
        
        Args:
            secret_key: JWT secret key
            algorithm: JWT algorithm
            max_token_age_hours: Maximum token age in hours
            enable_blacklist: Enable token blacklist
            enable_rate_limiting: Enable rate limiting per token
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.max_token_age_hours = max_token_age_hours
        self.enable_blacklist = enable_blacklist
        self.enable_rate_limiting = enable_rate_limiting
        
        self.logger = logging.getLogger("token_validator")
        
        # Token blacklist (in production, use Redis or database)
        self._blacklisted_tokens: Set[str] = set()
        
        # Rate limiting (token_id -> {count, window_start})
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        
        # Custom validation rules
        self._validation_rules: List[Callable[[Dict[str, Any]], bool]] = []
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
    
    def add_validation_rule(self, rule: Callable[[Dict[str, Any]], bool], name: str = None):
        """
        Add custom validation rule.
        
        Args:
            rule: Function that takes payload and returns True if valid
            name: Rule name for logging
        """
        rule._rule_name = name or f"custom_rule_{len(self._validation_rules)}"
        self._validation_rules.append(rule)
        self.logger.info(f"Added validation rule: {rule._rule_name}")
    
    def validate_token(
        self,
        token: str,
        expected_type: Optional[str] = None,
        expected_audience: Optional[str] = None,
        expected_issuer: Optional[str] = None,
        required_claims: Optional[List[str]] = None,
        check_rate_limit: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive token validation.
        
        Args:
            token: JWT token to validate
            expected_type: Expected token type
            expected_audience: Expected audience
            expected_issuer: Expected issuer
            required_claims: Required claims in token
            check_rate_limit: Whether to check rate limits
            
        Returns:
            Validated token payload
            
        Raises:
            SecurityError: If validation fails
        """
        validation_start = time.time()
        
        try:
            # Step 1: Basic JWT validation
            payload = self._validate_jwt_structure(token, expected_audience, expected_issuer)
            
            # Step 2: Check blacklist
            if self.enable_blacklist:
                self._check_blacklist(token, payload)
            
            # Step 3: Validate token type
            if expected_type:
                self._validate_token_type(payload, expected_type)
            
            # Step 4: Check required claims
            if required_claims:
                self._validate_required_claims(payload, required_claims)
            
            # Step 5: Check token age
            self._validate_token_age(payload)
            
            # Step 6: Apply custom validation rules
            self._apply_custom_rules(payload)
            
            # Step 7: Rate limiting
            if check_rate_limit and self.enable_rate_limiting:
                self._check_rate_limit(payload)
            
            # Step 8: Audit log
            self._log_validation_success(payload, validation_start)
            
            return payload
            
        except Exception as e:
            self._log_validation_failure(token, str(e), validation_start)
            raise
    
    def _validate_jwt_structure(
        self,
        token: str,
        expected_audience: Optional[str],
        expected_issuer: Optional[str]
    ) -> Dict[str, Any]:
        """Validate basic JWT structure and claims."""
        try:
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": expected_audience is not None,
                "verify_iss": expected_issuer is not None,
            }
            
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=expected_audience,
                issuer=expected_issuer,
                options=options
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise SecurityError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise SecurityError(f"Invalid JWT token: {e}")
    
    def _check_blacklist(self, token: str, payload: Dict[str, Any]):
        """Check if token is blacklisted."""
        token_id = payload.get("jti")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if token_id in self._blacklisted_tokens or token_hash in self._blacklisted_tokens:
            raise SecurityError("Token has been revoked")
    
    def _validate_token_type(self, payload: Dict[str, Any], expected_type: str):
        """Validate token type."""
        token_type = payload.get("token_type")
        if token_type != expected_type:
            raise SecurityError(f"Invalid token type. Expected: {expected_type}, Got: {token_type}")
    
    def _validate_required_claims(self, payload: Dict[str, Any], required_claims: List[str]):
        """Validate required claims are present."""
        missing_claims = []
        for claim in required_claims:
            if claim not in payload:
                missing_claims.append(claim)
        
        if missing_claims:
            raise SecurityError(f"Missing required claims: {missing_claims}")
    
    def _validate_token_age(self, payload: Dict[str, Any]):
        """Validate token is not too old."""
        issued_at = payload.get("iat")
        if not issued_at:
            raise SecurityError("Token missing issued at (iat) claim")
        
        token_age = datetime.utcnow() - datetime.fromtimestamp(issued_at)
        max_age = timedelta(hours=self.max_token_age_hours)
        
        if token_age > max_age:
            raise SecurityError(f"Token too old. Age: {token_age}, Max: {max_age}")
    
    def _apply_custom_rules(self, payload: Dict[str, Any]):
        """Apply custom validation rules."""
        for rule in self._validation_rules:
            try:
                if not rule(payload):
                    rule_name = getattr(rule, '_rule_name', 'unknown')
                    raise SecurityError(f"Custom validation rule failed: {rule_name}")
            except Exception as e:
                rule_name = getattr(rule, '_rule_name', 'unknown')
                raise SecurityError(f"Custom validation rule error ({rule_name}): {e}")
    
    def _check_rate_limit(self, payload: Dict[str, Any], max_requests: int = 100, window_minutes: int = 1):
        """Check rate limiting for token."""
        token_id = payload.get("jti", "unknown")
        now = time.time()
        window_start = now - (window_minutes * 60)
        
        # Clean old entries
        if token_id in self._rate_limits:
            rate_data = self._rate_limits[token_id]
            if rate_data["window_start"] < window_start:
                rate_data["count"] = 0
                rate_data["window_start"] = now
        else:
            self._rate_limits[token_id] = {"count": 0, "window_start": now}
        
        # Check limit
        rate_data = self._rate_limits[token_id]
        rate_data["count"] += 1
        
        if rate_data["count"] > max_requests:
            raise SecurityError(f"Rate limit exceeded for token. Max: {max_requests} per {window_minutes} minutes")
    
    def _log_validation_success(self, payload: Dict[str, Any], start_time: float):
        """Log successful validation."""
        duration = time.time() - start_time
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "token_validation_success",
            "service_name": payload.get("service_name", "unknown"),
            "token_type": payload.get("token_type", "unknown"),
            "token_id": payload.get("jti", "unknown"),
            "duration_ms": round(duration * 1000, 2),
        }
        
        self._audit_log.append(log_entry)
        self.logger.debug(f"Token validation successful: {log_entry}")
    
    def _log_validation_failure(self, token: str, error: str, start_time: float):
        """Log validation failure."""
        duration = time.time() - start_time
        
        # Try to get token info without validation
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            service_name = unverified_payload.get("service_name", "unknown")
            token_id = unverified_payload.get("jti", "unknown")
        except:
            service_name = "unknown"
            token_id = "unknown"
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "token_validation_failure",
            "service_name": service_name,
            "token_id": token_id,
            "error": error,
            "duration_ms": round(duration * 1000, 2),
        }
        
        self._audit_log.append(log_entry)
        self.logger.warning(f"Token validation failed: {log_entry}")
    
    def blacklist_token(self, token: str = None, token_id: str = None):
        """
        Add token to blacklist.
        
        Args:
            token: Full JWT token
            token_id: JWT ID (jti claim)
        """
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self._blacklisted_tokens.add(token_hash)
            self.logger.info(f"Blacklisted token by hash")
        
        if token_id:
            self._blacklisted_tokens.add(token_id)
            self.logger.info(f"Blacklisted token by ID: {token_id}")
    
    def is_token_blacklisted(self, token: str = None, token_id: str = None) -> bool:
        """Check if token is blacklisted."""
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if token_hash in self._blacklisted_tokens:
                return True
        
        if token_id and token_id in self._blacklisted_tokens:
            return True
        
        return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        recent_logs = [log for log in self._audit_log if 
                      datetime.fromisoformat(log["timestamp"]) > datetime.utcnow() - timedelta(hours=1)]
        
        success_count = len([log for log in recent_logs if log["event"] == "token_validation_success"])
        failure_count = len([log for log in recent_logs if log["event"] == "token_validation_failure"])
        
        return {
            "total_validations_last_hour": len(recent_logs),
            "successful_validations": success_count,
            "failed_validations": failure_count,
            "success_rate": (success_count / len(recent_logs)) * 100 if recent_logs else 0,
            "blacklisted_tokens": len(self._blacklisted_tokens),
            "active_rate_limits": len(self._rate_limits),
            "custom_rules": len(self._validation_rules),
        }
    
    def clear_audit_log(self, older_than_hours: int = 24):
        """Clear old audit log entries."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        original_count = len(self._audit_log)
        self._audit_log = [
            log for log in self._audit_log 
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]
        
        cleared_count = original_count - len(self._audit_log)
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old audit log entries")
    
    def export_audit_log(self, format: str = "json") -> List[Dict[str, Any]]:
        """Export audit log for external analysis."""
        if format == "json":
            return self._audit_log.copy()
        else:
            raise ValueError(f"Unsupported export format: {format}")
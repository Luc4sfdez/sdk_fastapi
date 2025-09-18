# fastapi-microservices-sdk/fastapi_microservices_sdk/security/authentication/jwt_service_auth.py
"""
JWT Service-to-Service Authentication for FastAPI Microservices SDK.

This module provides secure JWT-based authentication between microservices
with support for service identity, token validation, and automatic token refresh.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import logging

import jwt
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...config import get_config
from ...exceptions import SecurityError, ValidationError
from ...constants import SERVICE_NAME_HEADER


class JWTServiceAuth:
    """
    JWT Authentication manager for service-to-service communication.
    
    Features:
    - Service identity tokens
    - Token validation and verification
    - Automatic token refresh
    - Audience and issuer validation
    - Custom claims support
    """
    
    def __init__(
        self,
        service_name: str,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expiry_minutes: int = 30,
        refresh_threshold_minutes: int = 5,
        audience: Optional[List[str]] = None,
        issuer: Optional[str] = None
    ):
        """
        Initialize JWT Service Authentication.
        
        Args:
            service_name: Name of this service
            secret_key: JWT secret key (from config if None)
            algorithm: JWT algorithm
            token_expiry_minutes: Token expiration time
            refresh_threshold_minutes: When to refresh token
            audience: Valid audiences for tokens
            issuer: Token issuer
        """
        self.service_name = service_name
        self.config = get_config()
        self.secret_key = secret_key or self.config.security.jwt_secret_key
        self.algorithm = algorithm
        self.token_expiry_minutes = token_expiry_minutes
        self.refresh_threshold_minutes = refresh_threshold_minutes
        self.audience = audience or [service_name]
        self.issuer = issuer or "fastapi-microservices-sdk"
        
        self.logger = logging.getLogger(f"jwt_auth.{service_name}")
        
        # Token cache
        self._current_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Security bearer
        self.security = HTTPBearer(auto_error=False)
    
    def generate_service_token(
        self,
        target_service: Optional[str] = None,
        custom_claims: Optional[Dict[str, Any]] = None,
        expiry_minutes: Optional[int] = None
    ) -> str:
        """
        Generate a JWT token for service-to-service communication.
        
        Args:
            target_service: Target service name (audience)
            custom_claims: Additional claims to include
            expiry_minutes: Custom expiry time
            
        Returns:
            JWT token string
            
        Raises:
            SecurityError: If token generation fails
        """
        try:
            now = datetime.now(timezone.utc)
            expiry = expiry_minutes or self.token_expiry_minutes
            expires_at = now + timedelta(minutes=expiry)
            
            # Standard JWT claims
            payload = {
                "iss": self.issuer,  # Issuer
                "sub": self.service_name,  # Subject (this service)
                "aud": target_service or self.audience,  # Audience
                "iat": int(now.timestamp()),  # Issued at
                "exp": int(expires_at.timestamp()),  # Expires at
                "nbf": int(now.timestamp()),  # Not before
                "jti": str(uuid.uuid4()),  # JWT ID
            }
            
            # Service-specific claims
            payload.update({
                "service_name": self.service_name,
                "service_type": "microservice",
                "token_type": "service_auth",
                "permissions": ["service_call", "health_check"],
            })
            
            # Add custom claims
            if custom_claims:
                payload.update(custom_claims)
            
            # Generate token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            self.logger.debug(f"Generated service token for {target_service or 'any'}")
            return token
            
        except Exception as e:
            self.logger.error(f"Failed to generate service token: {e}")
            raise SecurityError(f"Token generation failed: {e}")
    
    def validate_token(
        self,
        token: str,
        expected_audience: Optional[str] = None,
        required_permissions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token to validate
            expected_audience: Expected audience claim
            required_permissions: Required permissions in token
            
        Returns:
            Decoded token payload
            
        Raises:
            SecurityError: If token is invalid
        """
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=expected_audience or self.audience,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            # Validate service-specific claims
            if "service_name" not in payload:
                raise SecurityError("Missing service_name claim")
            
            if "token_type" not in payload or payload["token_type"] != "service_auth":
                raise SecurityError("Invalid token type")
            
            # Check required permissions
            if required_permissions:
                token_permissions = payload.get("permissions", [])
                missing_permissions = set(required_permissions) - set(token_permissions)
                if missing_permissions:
                    raise SecurityError(f"Missing permissions: {missing_permissions}")
            
            self.logger.debug(f"Validated token from service: {payload['service_name']}")
            return payload
            
        except jwt.ExpiredSignatureError:
            raise SecurityError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise SecurityError(f"Invalid token: {e}")
        except Exception as e:
            self.logger.error(f"Token validation failed: {e}")
            raise SecurityError(f"Token validation failed: {e}")
    
    def get_current_token(self, target_service: Optional[str] = None) -> str:
        """
        Get current valid token, refreshing if necessary.
        
        Args:
            target_service: Target service for the token
            
        Returns:
            Valid JWT token
        """
        now = datetime.now(timezone.utc)
        
        # Check if we need to refresh the token
        if (
            self._current_token is None or
            self._token_expires_at is None or
            now >= self._token_expires_at - timedelta(minutes=self.refresh_threshold_minutes)
        ):
            self._refresh_token(target_service)
        
        return self._current_token
    
    def _refresh_token(self, target_service: Optional[str] = None):
        """Refresh the current token."""
        self._current_token = self.generate_service_token(target_service)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.token_expiry_minutes)
        self.logger.debug("Refreshed service token")
    
    def create_auth_dependency(
        self,
        required_permissions: Optional[List[str]] = None,
        allow_service_tokens_only: bool = True
    ):
        """
        Create FastAPI dependency for JWT authentication.
        
        Args:
            required_permissions: Required permissions for access
            allow_service_tokens_only: Only allow service tokens
            
        Returns:
            FastAPI dependency function
        """
        async def jwt_auth_dependency(
            request: Request,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(self.security)
        ) -> Dict[str, Any]:
            """JWT authentication dependency."""
            
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Missing authentication token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            try:
                # Validate token
                payload = self.validate_token(
                    credentials.credentials,
                    expected_audience=self.service_name,
                    required_permissions=required_permissions
                )
                
                # Check if service token is required
                if allow_service_tokens_only and payload.get("token_type") != "service_auth":
                    raise HTTPException(
                        status_code=403,
                        detail="Service tokens required"
                    )
                
                # Add token info to request state
                request.state.jwt_payload = payload
                request.state.calling_service = payload.get("service_name")
                
                return payload
                
            except SecurityError as e:
                raise HTTPException(
                    status_code=401,
                    detail=str(e),
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        return jwt_auth_dependency
    
    def add_auth_header(self, headers: Dict[str, str], target_service: Optional[str] = None) -> Dict[str, str]:
        """
        Add JWT authentication header to request headers.
        
        Args:
            headers: Existing headers dictionary
            target_service: Target service name
            
        Returns:
            Headers with authentication added
        """
        token = self.get_current_token(target_service)
        headers = headers.copy()
        headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Get token information without validation (for debugging).
        
        Args:
            token: JWT token
            
        Returns:
            Token payload (unverified)
        """
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            return {"error": str(e)}
    
    def revoke_token(self, token_id: str):
        """
        Revoke a token (placeholder for token blacklist).
        
        Args:
            token_id: JWT ID to revoke
        """
        # TODO: Implement token blacklist/revocation
        self.logger.info(f"Token revocation requested for JTI: {token_id}")
        pass
    
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        return {
            "service_name": self.service_name,
            "algorithm": self.algorithm,
            "token_expiry_minutes": self.token_expiry_minutes,
            "current_token_valid": self._current_token is not None,
            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None,
            "audience": self.audience,
            "issuer": self.issuer,
        }
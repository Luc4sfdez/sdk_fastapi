# fastapi-microservices-sdk/fastapi_microservices_sdk/security/__init__.py
"""
Security module for FastAPI Microservices SDK.

This module provides comprehensive security features for microservices:
- JWT service-to-service authentication
- Secrets management
- Input validation and sanitization
- Security headers (OWASP compliance)
- Rate limiting
- CORS management
"""

from .authentication import JWTServiceAuth, TokenValidator, ServiceIdentity
from .secrets import SecretsManager, VaultClient, EnvSecrets
from .protection import SecurityHeaders, InputValidator, RateLimiter, CORSManager

__all__ = [
    # Authentication
    "JWTServiceAuth",
    "TokenValidator", 
    "ServiceIdentity",
    
    # Secrets Management
    "SecretsManager",
    "VaultClient",
    "EnvSecrets",
    
    # Protection
    "SecurityHeaders",
    "InputValidator",
    "RateLimiter",
    "CORSManager",
]
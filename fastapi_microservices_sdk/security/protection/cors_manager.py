"""
CORS management for FastAPI Microservices SDK.

This module provides advanced CORS configuration and management.
"""

from typing import List, Optional, Union, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ...exceptions import ConfigurationError


class CORSConfig(BaseModel):
    """CORS configuration model."""
    
    allow_origins: List[str] = ["*"]
    allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    allow_headers: List[str] = ["*"]
    allow_credentials: bool = False
    expose_headers: List[str] = []
    max_age: int = 600
    
    # Advanced options
    allow_origin_regex: Optional[str] = None
    vary_header: bool = True
    preflight_max_age: Optional[int] = None
    
    class Config:
        extra = "forbid"


class CORSManager:
    """Advanced CORS manager for microservices."""
    
    def __init__(self, config: Optional[CORSConfig] = None):
        self.config = config or CORSConfig()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate CORS configuration."""
        # Check for security issues
        if "*" in self.config.allow_origins and self.config.allow_credentials:
            raise ConfigurationError(
                "Cannot use allow_credentials=True with allow_origins=['*']. "
                "Specify explicit origins instead."
            )
        
        # Validate methods (allow "*" for headers but not methods)
        valid_methods = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"}
        for method in self.config.allow_methods:
            if method != "*" and method.upper() not in valid_methods:
                raise ConfigurationError(f"Invalid HTTP method: {method}")
        
        # Validate max_age
        if self.config.max_age < 0:
            raise ConfigurationError("max_age must be non-negative")
    
    def apply_to_app(self, app: FastAPI) -> None:
        """Apply CORS configuration to FastAPI app."""
        cors_kwargs = {
            "allow_origins": self.config.allow_origins,
            "allow_credentials": self.config.allow_credentials,
            "allow_methods": self.config.allow_methods,
            "allow_headers": self.config.allow_headers,
            "expose_headers": self.config.expose_headers,
            "max_age": self.config.max_age,
        }
        
        # Add optional parameters if set
        if self.config.allow_origin_regex:
            cors_kwargs["allow_origin_regex"] = self.config.allow_origin_regex
        
        app.add_middleware(CORSMiddleware, **cors_kwargs)
    
    def get_secure_config(self, allowed_origins: List[str]) -> CORSConfig:
        """Get a secure CORS configuration for production."""
        return CORSConfig(
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Authorization",
                "X-Requested-With",
                "X-Request-ID",
                "X-Service-Name",
                "X-Service-Version"
            ],
            allow_credentials=True,
            expose_headers=[
                "X-Request-ID",
                "X-Response-Time",
                "X-Rate-Limit-Limit",
                "X-Rate-Limit-Remaining"
            ],
            max_age=86400,  # 24 hours
            vary_header=True
        )
    
    def get_development_config(self) -> CORSConfig:
        """Get a permissive CORS configuration for development."""
        return CORSConfig(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
            allow_headers=["*"],
            allow_credentials=False,
            max_age=3600  # 1 hour
        )
    
    def get_microservice_config(self, service_origins: List[str]) -> CORSConfig:
        """Get CORS configuration optimized for microservice communication."""
        return CORSConfig(
            allow_origins=service_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-Request-ID",
                "X-Service-Name",
                "X-Service-Version",
                "X-Service-Token",
                "X-Correlation-ID",
                "X-Trace-ID"
            ],
            allow_credentials=True,
            expose_headers=[
                "X-Request-ID",
                "X-Response-Time",
                "X-Service-Name",
                "X-Service-Version"
            ],
            max_age=3600
        )
    
    @classmethod
    def create_for_environment(cls, environment: str, origins: Optional[List[str]] = None) -> 'CORSManager':
        """Create CORS manager based on environment."""
        if environment.lower() in ["development", "dev", "local"]:
            return cls(cls().get_development_config())
        elif environment.lower() in ["production", "prod"]:
            if not origins:
                raise ConfigurationError("Production environment requires explicit origins")
            return cls(cls().get_secure_config(origins))
        elif environment.lower() in ["staging", "test"]:
            # Staging: more permissive than prod, more restrictive than dev
            staging_origins = origins or ["http://localhost:3000", "https://staging.example.com"]
            return cls(cls().get_secure_config(staging_origins))
        else:
            raise ConfigurationError(f"Unknown environment: {environment}")
    
    def update_config(self, **kwargs) -> None:
        """Update CORS configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            else:
                raise ConfigurationError(f"Unknown CORS config parameter: {key}")
        
        self._validate_config()
    
    def add_origin(self, origin: str) -> None:
        """Add an allowed origin."""
        if origin not in self.config.allow_origins:
            self.config.allow_origins.append(origin)
    
    def remove_origin(self, origin: str) -> None:
        """Remove an allowed origin."""
        if origin in self.config.allow_origins:
            self.config.allow_origins.remove(origin)
    
    def add_header(self, header: str) -> None:
        """Add an allowed header."""
        if header not in self.config.allow_headers:
            self.config.allow_headers.append(header)
    
    def remove_header(self, header: str) -> None:
        """Remove an allowed header."""
        if header in self.config.allow_headers:
            self.config.allow_headers.remove(header)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get CORS configuration as dictionary."""
        return self.config.dict()
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if "*" in self.config.allow_origins:
            return True
        
        if origin in self.config.allow_origins:
            return True
        
        # Check regex pattern if configured
        if self.config.allow_origin_regex:
            import re
            pattern = re.compile(self.config.allow_origin_regex)
            return bool(pattern.match(origin))
        
        return False
    
    def get_security_recommendations(self) -> List[str]:
        """Get security recommendations for current CORS config."""
        recommendations = []
        
        if "*" in self.config.allow_origins:
            recommendations.append(
                "Consider specifying explicit origins instead of '*' for better security"
            )
        
        if self.config.allow_credentials and "*" in self.config.allow_origins:
            recommendations.append(
                "CRITICAL: Cannot use credentials with wildcard origins"
            )
        
        if "*" in self.config.allow_headers:
            recommendations.append(
                "Consider specifying explicit headers instead of '*'"
            )
        
        if self.config.max_age > 86400:  # 24 hours
            recommendations.append(
                "Consider reducing max_age for better security (current: {} seconds)".format(
                    self.config.max_age
                )
            )
        
        dangerous_methods = {"TRACE", "CONNECT"}
        if any(method in dangerous_methods for method in self.config.allow_methods):
            recommendations.append(
                "Consider removing potentially dangerous HTTP methods (TRACE, CONNECT)"
            )
        
        return recommendations


# Predefined CORS configurations
class CORSPresets:
    """Predefined CORS configurations for common scenarios."""
    
    @staticmethod
    def strict() -> CORSConfig:
        """Strict CORS configuration for high-security environments."""
        return CORSConfig(
            allow_origins=[],  # Must be explicitly set
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
            allow_credentials=True,
            max_age=300  # 5 minutes
        )
    
    @staticmethod
    def api_only() -> CORSConfig:
        """CORS configuration for API-only services."""
        return CORSConfig(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
            allow_credentials=False,
            max_age=3600
        )
    
    @staticmethod
    def spa_friendly() -> CORSConfig:
        """CORS configuration friendly for Single Page Applications."""
        return CORSConfig(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=False,
            expose_headers=["X-Total-Count", "X-Page-Count"],
            max_age=3600
        )
    
    @staticmethod
    def microservice() -> CORSConfig:
        """CORS configuration for microservice-to-microservice communication."""
        return CORSConfig(
            allow_origins=["*"],  # Should be restricted to service network
            allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            allow_headers=[
                "Content-Type",
                "Authorization",
                "X-Service-Token",
                "X-Request-ID",
                "X-Correlation-ID"
            ],
            allow_credentials=True,
            max_age=86400
        )
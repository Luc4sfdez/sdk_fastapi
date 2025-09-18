# fastapi-microservices-sdk/fastapi_microservices_sdk/security/protection/security_headers.py
"""
Security Headers Manager for FastAPI Microservices SDK.

This module implements OWASP-compliant security headers to protect
microservices from common web vulnerabilities.
"""

from typing import Dict, Any, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from ...config import get_config


class SecurityHeaders:
    """
    OWASP-compliant Security Headers Manager.
    
    Features:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    - Custom headers support
    """
    
    def __init__(
        self,
        enable_csp: bool = True,
        enable_hsts: bool = True,
        enable_frame_options: bool = True,
        enable_content_type_options: bool = True,
        enable_xss_protection: bool = True,
        enable_referrer_policy: bool = True,
        enable_permissions_policy: bool = True,
        custom_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Security Headers Manager.
        
        Args:
            enable_csp: Enable Content Security Policy
            enable_hsts: Enable HTTP Strict Transport Security
            enable_frame_options: Enable X-Frame-Options
            enable_content_type_options: Enable X-Content-Type-Options
            enable_xss_protection: Enable X-XSS-Protection
            enable_referrer_policy: Enable Referrer-Policy
            enable_permissions_policy: Enable Permissions-Policy
            custom_headers: Custom security headers
        """
        self.enable_csp = enable_csp
        self.enable_hsts = enable_hsts
        self.enable_frame_options = enable_frame_options
        self.enable_content_type_options = enable_content_type_options
        self.enable_xss_protection = enable_xss_protection
        self.enable_referrer_policy = enable_referrer_policy
        self.enable_permissions_policy = enable_permissions_policy
        self.custom_headers = custom_headers or {}
        
        self.logger = logging.getLogger("security_headers")
        self.config = get_config()
        
        # Default CSP policy for APIs
        self.default_csp = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    
    def get_security_headers(
        self,
        request: Request,
        response: Response,
        custom_csp: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate security headers for a request/response.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            custom_csp: Custom CSP policy for this response
            
        Returns:
            Dictionary of security headers
        """
        headers = {}
        
        # Content Security Policy
        if self.enable_csp:
            csp_policy = custom_csp or self.default_csp
            headers["Content-Security-Policy"] = csp_policy
        
        # HTTP Strict Transport Security
        if self.enable_hsts and self._is_https_request(request):
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # X-Frame-Options
        if self.enable_frame_options:
            headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        if self.enable_content_type_options:
            headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection (legacy but still useful)
        if self.enable_xss_protection:
            headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        if self.enable_referrer_policy:
            headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        if self.enable_permissions_policy:
            headers["Permissions-Policy"] = (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        
        # Server header (security through obscurity)
        headers["Server"] = "FastAPI-Microservices-SDK"
        
        # X-Powered-By removal (if present)
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        # Custom headers
        headers.update(self.custom_headers)
        
        # API-specific headers
        if self._is_api_endpoint(request):
            headers.update(self._get_api_security_headers())
        
        return headers
    
    def _is_https_request(self, request: Request) -> bool:
        """Check if request is HTTPS."""
        return (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https" or
            request.headers.get("x-forwarded-ssl") == "on"
        )
    
    def _is_api_endpoint(self, request: Request) -> bool:
        """Check if request is for an API endpoint."""
        path = request.url.path
        return (
            path.startswith("/api/") or
            path.startswith("/v1/") or
            path.startswith("/v2/") or
            "application/json" in request.headers.get("accept", "")
        )
    
    def _get_api_security_headers(self) -> Dict[str, str]:
        """Get API-specific security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-API-Version": "1.0",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    
    def create_middleware(self):
        """Create FastAPI middleware for automatic header injection."""
        
        class SecurityHeadersMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, security_headers: SecurityHeaders):
                super().__init__(app)
                self.security_headers = security_headers
            
            async def dispatch(self, request: Request, call_next):
                response = await call_next(request)
                
                # Get security headers
                headers = self.security_headers.get_security_headers(request, response)
                
                # Apply headers to response
                for header_name, header_value in headers.items():
                    response.headers[header_name] = header_value
                
                return response
        
        return SecurityHeadersMiddleware
    
    def validate_csp_policy(self, csp_policy: str) -> Dict[str, Any]:
        """
        Validate CSP policy syntax.
        
        Args:
            csp_policy: CSP policy string
            
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "directives": {},
        }
        
        try:
            # Parse CSP directives
            directives = {}
            for directive in csp_policy.split(";"):
                directive = directive.strip()
                if not directive:
                    continue
                
                parts = directive.split()
                if len(parts) < 1:
                    continue
                
                directive_name = parts[0]
                directive_values = parts[1:] if len(parts) > 1 else []
                directives[directive_name] = directive_values
            
            results["directives"] = directives
            
            # Check for common issues
            if "default-src" not in directives:
                results["warnings"].append("Missing default-src directive")
            
            if "'unsafe-eval'" in str(directives):
                results["warnings"].append("Using 'unsafe-eval' reduces security")
            
            if "'unsafe-inline'" in str(directives):
                results["warnings"].append("Using 'unsafe-inline' reduces security")
            
            # Check for required directives for APIs
            recommended_directives = ["default-src", "script-src", "style-src"]
            for directive in recommended_directives:
                if directive not in directives:
                    results["warnings"].append(f"Consider adding {directive} directive")
            
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"CSP parsing error: {e}")
        
        return results
    
    def generate_csp_for_docs(self) -> str:
        """Generate CSP policy for API documentation pages."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
    
    def get_security_report(self, request: Request) -> Dict[str, Any]:
        """
        Generate security report for a request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Security analysis report
        """
        report = {
            "timestamp": request.state.get("request_time", "unknown"),
            "url": str(request.url),
            "method": request.method,
            "https": self._is_https_request(request),
            "api_endpoint": self._is_api_endpoint(request),
            "security_headers": {},
            "recommendations": [],
        }
        
        # Analyze request headers
        security_relevant_headers = [
            "user-agent", "referer", "origin", "x-forwarded-for",
            "x-real-ip", "authorization", "cookie"
        ]
        
        for header in security_relevant_headers:
            value = request.headers.get(header)
            if value:
                report["security_headers"][header] = value[:100]  # Truncate for safety
        
        # Security recommendations
        if not self._is_https_request(request):
            report["recommendations"].append("Use HTTPS for secure communication")
        
        if "authorization" not in request.headers and self._is_api_endpoint(request):
            report["recommendations"].append("Consider adding authentication")
        
        user_agent = request.headers.get("user-agent", "")
        if not user_agent or len(user_agent) < 10:
            report["recommendations"].append("Suspicious or missing User-Agent header")
        
        return report
    
    def create_security_policy_document(self) -> Dict[str, Any]:
        """Create a security policy document."""
        return {
            "security_policy": {
                "version": "1.0",
                "last_updated": "2025-01-09",
                "headers": {
                    "content_security_policy": {
                        "enabled": self.enable_csp,
                        "default_policy": self.default_csp,
                        "description": "Prevents XSS and data injection attacks"
                    },
                    "strict_transport_security": {
                        "enabled": self.enable_hsts,
                        "max_age": 31536000,
                        "include_subdomains": True,
                        "preload": True,
                        "description": "Enforces HTTPS connections"
                    },
                    "x_frame_options": {
                        "enabled": self.enable_frame_options,
                        "value": "DENY",
                        "description": "Prevents clickjacking attacks"
                    },
                    "x_content_type_options": {
                        "enabled": self.enable_content_type_options,
                        "value": "nosniff",
                        "description": "Prevents MIME type sniffing"
                    },
                    "x_xss_protection": {
                        "enabled": self.enable_xss_protection,
                        "value": "1; mode=block",
                        "description": "Legacy XSS protection"
                    },
                    "referrer_policy": {
                        "enabled": self.enable_referrer_policy,
                        "value": "strict-origin-when-cross-origin",
                        "description": "Controls referrer information"
                    },
                    "permissions_policy": {
                        "enabled": self.enable_permissions_policy,
                        "description": "Controls browser feature access"
                    }
                },
                "custom_headers": self.custom_headers,
                "compliance": {
                    "owasp": "Compliant with OWASP security headers guidelines",
                    "standards": ["RFC 7034", "RFC 6797", "W3C CSP Level 3"]
                }
            }
        }
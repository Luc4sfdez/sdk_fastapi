"""
Unified Security Middleware Stack for FastAPI Microservices SDK.

This module provides a comprehensive security middleware that coordinates
all security layers in the proper order:
1. mTLS (Transport Security)
2. JWT Authentication 
3. RBAC (Role-Based Access Control)
4. ABAC (Attribute-Based Access Control)
5. Threat Detection & Response
6. Application Layer

The middleware ensures proper security layer ordering, failure handling,
and graceful degradation when security components are unavailable.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

# Import security components
from .config import AdvancedSecurityConfig
from .exceptions import (
    AdvancedSecurityError, MTLSError, RBACError, ABACError,
    ThreatDetectionError, SecurityConfigurationError
)
from .logging import SecurityLogger, SecurityEvent, AuthEvent, AuthzEvent
from .mtls import MTLSManager, MTLSMiddleware
from .rbac import RBACEngine, RBACMiddleware
from .abac import ABACEngine, ABACMiddleware
from .threat_detection import ThreatDetector


class SecurityLayerType(Enum):
    """Types of security layers in the middleware stack."""
    MTLS = "mtls"
    JWT = "jwt"
    RBAC = "rbac"
    ABAC = "abac"
    THREAT_DETECTION = "threat_detection"
    APPLICATION = "application"


class SecurityLayerStatus(Enum):
    """Status of individual security layers."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"
    BYPASSED = "bypassed"


@dataclass
class SecurityLayerConfig:
    """Configuration for individual security layers."""
    layer_type: SecurityLayerType
    enabled: bool = True
    required: bool = True
    fail_open: bool = False  # If True, allows requests to continue on failure
    timeout_seconds: float = 5.0
    retry_attempts: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityContext:
    """Security context passed between middleware layers."""
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    client_cert_subject: Optional[str] = None
    jwt_claims: Dict[str, Any] = field(default_factory=dict)
    rbac_roles: List[str] = field(default_factory=list)
    rbac_permissions: List[str] = field(default_factory=list)
    abac_attributes: Dict[str, Any] = field(default_factory=dict)
    threat_assessment: Optional[Any] = None  # ThreatAssessment object
    layer_results: Dict[SecurityLayerType, Dict[str, Any]] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_layer_result(self, layer: SecurityLayerType, result: Dict[str, Any]):
        """Add result from a security layer."""
        self.layer_results[layer] = result
        
    def get_layer_result(self, layer: SecurityLayerType) -> Optional[Dict[str, Any]]:
        """Get result from a specific security layer."""
        return self.layer_results.get(layer)
        
    def is_layer_successful(self, layer: SecurityLayerType) -> bool:
        """Check if a security layer was successful."""
        result = self.get_layer_result(layer)
        return result is not None and result.get("success", False)


@dataclass
class SecurityMetrics:
    """Security metrics for monitoring and alerting."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    layer_failures: Dict[SecurityLayerType, int] = field(default_factory=dict)
    average_processing_time: float = 0.0
    threat_detections: int = 0
    blocked_requests: int = 0
    
    def record_request(self, success: bool, processing_time: float):
        """Record a request result."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
        # Update average processing time
        self.average_processing_time = (
            (self.average_processing_time * (self.total_requests - 1) + processing_time) 
            / self.total_requests
        )
    
    def record_layer_failure(self, layer: SecurityLayerType):
        """Record a failure in a specific security layer."""
        if layer not in self.layer_failures:
            self.layer_failures[layer] = 0
        self.layer_failures[layer] += 1
    
    def record_threat_detection(self):
        """Record a threat detection."""
        self.threat_detections += 1
    
    def record_blocked_request(self):
        """Record a blocked request."""
        self.blocked_requests += 1


class UnifiedSecurityMiddleware(BaseHTTPMiddleware):
    """
    Unified security middleware that coordinates all security layers.
    
    This middleware processes requests through multiple security layers in order:
    1. mTLS validation (if enabled)
    2. JWT authentication (if enabled) 
    3. RBAC authorization (if enabled)
    4. ABAC authorization (if enabled)
    5. Threat detection (if enabled)
    
    Features:
    - Configurable security layer ordering
    - Graceful degradation on component failures
    - Comprehensive security logging and metrics
    - Request correlation tracking
    - Performance monitoring
    """
    
    def __init__(
        self,
        app: ASGIApp,
        config: AdvancedSecurityConfig,
        layer_configs: Optional[List[SecurityLayerConfig]] = None,
        mtls_manager: Optional[MTLSManager] = None,
        rbac_engine: Optional[RBACEngine] = None,
        abac_engine: Optional[ABACEngine] = None,
        threat_detector: Optional[ThreatDetector] = None,
        jwt_bearer: Optional[HTTPBearer] = None
    ):
        super().__init__(app)
        self.config = config
        self.logger = SecurityLogger("UnifiedSecurityMiddleware")
        self.metrics = SecurityMetrics()
        
        # Initialize security components
        self.mtls_manager = mtls_manager
        self.rbac_engine = rbac_engine
        self.abac_engine = abac_engine
        self.threat_detector = threat_detector
        self.jwt_bearer = jwt_bearer or HTTPBearer(auto_error=False)
        
        # Configure security layers
        self.layer_configs = self._setup_layer_configs(layer_configs)
        
        # Initialize individual middleware components
        self._setup_middleware_components()
        
        self.logger.info("UnifiedSecurityMiddleware initialized", extra={
            "enabled_layers": [layer.layer_type.value for layer in self.layer_configs if layer.enabled],
            "total_layers": len(self.layer_configs)
        })
    
    def _setup_layer_configs(self, layer_configs: Optional[List[SecurityLayerConfig]]) -> List[SecurityLayerConfig]:
        """Setup default layer configurations if not provided."""
        if layer_configs:
            return layer_configs
            
        # Default security layer configuration
        return [
            SecurityLayerConfig(
                layer_type=SecurityLayerType.MTLS,
                enabled=self.config.mtls_enabled,
                required=True,
                fail_open=False
            ),
            SecurityLayerConfig(
                layer_type=SecurityLayerType.JWT,
                enabled=True,  # JWT is typically always enabled
                required=True,
                fail_open=False
            ),
            SecurityLayerConfig(
                layer_type=SecurityLayerType.RBAC,
                enabled=self.config.rbac_enabled,
                required=False,
                fail_open=True  # RBAC can fail open for graceful degradation
            ),
            SecurityLayerConfig(
                layer_type=SecurityLayerType.ABAC,
                enabled=self.config.abac_enabled,
                required=False,
                fail_open=True  # ABAC can fail open for graceful degradation
            ),
            SecurityLayerConfig(
                layer_type=SecurityLayerType.THREAT_DETECTION,
                enabled=self.config.threat_detection_enabled,
                required=False,
                fail_open=True  # Threat detection should not block requests on failure
            )
        ]
    
    def _setup_middleware_components(self):
        """Initialize individual middleware components."""
        # Setup individual middlewares for delegation
        if self.mtls_manager:
            self.mtls_middleware = MTLSMiddleware(None, self.mtls_manager)
        
        if self.rbac_engine:
            self.rbac_middleware = RBACMiddleware(None, self.rbac_engine)
            
        if self.abac_engine:
            self.abac_middleware = ABACMiddleware(None, self.abac_engine)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Main middleware dispatch method that processes requests through security layers.
        """
        start_time = time.time()
        
        # Generate request correlation ID
        request_id = self._generate_request_id()
        
        # Initialize security context
        security_context = SecurityContext(request_id=request_id)
        
        # Add correlation ID to request state
        request.state.security_context = security_context
        request.state.request_id = request_id
        
        try:
            # Process through security layers in order
            for layer_config in self.layer_configs:
                if not layer_config.enabled:
                    continue
                    
                try:
                    await self._process_security_layer(request, security_context, layer_config)
                except Exception as e:
                    await self._handle_layer_failure(request, security_context, layer_config, e)
                    
                    # If layer is required and doesn't fail open, block the request
                    if layer_config.required and not layer_config.fail_open:
                        return await self._create_security_error_response(
                            request, security_context, layer_config.layer_type, str(e)
                        )
            
            # All security layers passed, proceed to application
            response = await call_next(request)
            
            # Post-process response through security layers
            await self._post_process_response(request, response, security_context)
            
            # Record successful request
            processing_time = time.time() - start_time
            self.metrics.record_request(True, processing_time)
            
            # Log successful security processing
            await self._log_security_success(request, security_context, processing_time)
            
            return response
            
        except Exception as e:
            # Record failed request
            processing_time = time.time() - start_time
            self.metrics.record_request(False, processing_time)
            
            # Log security failure
            await self._log_security_failure(request, security_context, e, processing_time)
            
            # Return appropriate error response
            return await self._create_security_error_response(
                request, security_context, SecurityLayerType.APPLICATION, str(e)
            )
    
    async def _process_security_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process a request through a specific security layer."""
        layer_type = layer_config.layer_type
        
        self.logger.debug(f"Processing security layer: {layer_type.value}", extra={
            "request_id": security_context.request_id,
            "layer": layer_type.value
        })
        
        if layer_type == SecurityLayerType.MTLS:
            await self._process_mtls_layer(request, security_context, layer_config)
        elif layer_type == SecurityLayerType.JWT:
            await self._process_jwt_layer(request, security_context, layer_config)
        elif layer_type == SecurityLayerType.RBAC:
            await self._process_rbac_layer(request, security_context, layer_config)
        elif layer_type == SecurityLayerType.ABAC:
            await self._process_abac_layer(request, security_context, layer_config)
        elif layer_type == SecurityLayerType.THREAT_DETECTION:
            await self._process_threat_detection_layer(request, security_context, layer_config)
    
    async def _process_mtls_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process mTLS validation layer."""
        if not self.mtls_manager:
            raise MTLSError("mTLS manager not configured")
        
        try:
            # Extract client certificate from request
            client_cert = request.headers.get("X-Client-Cert")
            if not client_cert:
                # Check if mTLS is required
                if layer_config.required:
                    raise MTLSError("Client certificate required but not provided")
                return
            
            # Validate client certificate
            validation_result = await self.mtls_manager.validate_peer_certificate(client_cert)
            
            if validation_result.get("valid", False):
                security_context.client_cert_subject = validation_result.get("subject")
                security_context.add_layer_result(SecurityLayerType.MTLS, {
                    "success": True,
                    "subject": validation_result.get("subject"),
                    "issuer": validation_result.get("issuer")
                })
            else:
                raise MTLSError(f"Invalid client certificate: {validation_result.get('error')}")
                
        except Exception as e:
            self.metrics.record_layer_failure(SecurityLayerType.MTLS)
            raise MTLSError(f"mTLS validation failed: {str(e)}")
    
    async def _process_jwt_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process JWT authentication layer."""
        try:
            # Extract JWT token from request
            credentials: HTTPAuthorizationCredentials = await self.jwt_bearer(request)
            
            if not credentials:
                if layer_config.required:
                    raise HTTPException(status_code=401, detail="JWT token required")
                return
            
            # Validate JWT token (this would integrate with existing JWT service)
            # For now, we'll simulate JWT validation
            token = credentials.credentials
            
            # TODO: Integrate with actual JWT validation service
            # jwt_claims = await self.jwt_service.validate_token(token)
            
            # Simulated JWT validation
            jwt_claims = self._simulate_jwt_validation(token)
            
            security_context.user_id = jwt_claims.get("sub")
            security_context.session_id = jwt_claims.get("session_id")
            security_context.jwt_claims = jwt_claims
            
            security_context.add_layer_result(SecurityLayerType.JWT, {
                "success": True,
                "user_id": security_context.user_id,
                "claims": jwt_claims
            })
            
        except HTTPException:
            self.metrics.record_layer_failure(SecurityLayerType.JWT)
            raise
        except Exception as e:
            self.metrics.record_layer_failure(SecurityLayerType.JWT)
            raise HTTPException(status_code=401, detail=f"JWT validation failed: {str(e)}")
    
    async def _process_rbac_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process RBAC authorization layer."""
        if not self.rbac_engine:
            if layer_config.required:
                raise RBACError("RBAC engine not configured")
            return
        
        try:
            user_id = security_context.user_id
            if not user_id:
                if layer_config.required:
                    raise RBACError("User ID required for RBAC authorization")
                return
            
            # Get required permission from request path and method
            required_permission = self._extract_required_permission(request)
            
            if required_permission:
                # Check RBAC permission
                has_permission = await self.rbac_engine.check_permission(user_id, required_permission)
                
                if not has_permission:
                    raise RBACError(f"User {user_id} lacks required permission: {required_permission}")
                
                # Get user roles and permissions for context
                user_roles = await self.rbac_engine.get_user_roles(user_id)
                user_permissions = await self.rbac_engine.get_user_permissions(user_id)
                
                security_context.rbac_roles = user_roles
                security_context.rbac_permissions = user_permissions
            
            security_context.add_layer_result(SecurityLayerType.RBAC, {
                "success": True,
                "user_id": user_id,
                "roles": security_context.rbac_roles,
                "permissions": security_context.rbac_permissions,
                "required_permission": required_permission
            })
            
        except Exception as e:
            self.metrics.record_layer_failure(SecurityLayerType.RBAC)
            if isinstance(e, RBACError):
                raise
            raise RBACError(f"RBAC authorization failed: {str(e)}")
    
    async def _process_abac_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process ABAC authorization layer."""
        if not self.abac_engine:
            if layer_config.required:
                raise ABACError("ABAC engine not configured")
            return
        
        try:
            # Build ABAC context from request and security context
            abac_context = self._build_abac_context(request, security_context)
            
            # Evaluate ABAC policies
            decision = await self.abac_engine.evaluate(abac_context)
            
            if decision.decision != "Permit":
                raise ABACError(f"ABAC authorization denied: {decision.reason}")
            
            security_context.abac_attributes = abac_context
            security_context.add_layer_result(SecurityLayerType.ABAC, {
                "success": True,
                "decision": decision.decision,
                "reason": decision.reason,
                "context": abac_context
            })
            
        except Exception as e:
            self.metrics.record_layer_failure(SecurityLayerType.ABAC)
            if isinstance(e, ABACError):
                raise
            raise ABACError(f"ABAC authorization failed: {str(e)}")
    
    async def _process_threat_detection_layer(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig
    ):
        """Process threat detection layer."""
        if not self.threat_detector:
            return  # Threat detection is optional
        
        try:
            # Analyze request for threats
            client_ip = self._extract_client_ip(request)
            user_agent = request.headers.get("User-Agent", "")
            
            # Create login event for threat analysis (if this is an auth endpoint)
            if self._is_auth_endpoint(request):
                assessment = self.threat_detector.analyze_login_event(
                    user_id=security_context.user_id or "anonymous",
                    source_ip=client_ip,
                    success=True,  # We'll update this based on final result
                    user_agent=user_agent
                )
            else:
                # Create session event for threat analysis
                assessment = self.threat_detector.analyze_session_event(
                    user_id=security_context.user_id or "anonymous",
                    session_id=security_context.session_id or "anonymous",
                    source_ip=client_ip,
                    endpoint=str(request.url.path),
                    method=request.method,
                    user_agent=user_agent
                )
            
            security_context.threat_assessment = assessment
            
            # Check if threats were detected
            if assessment.detected_threats:
                self.metrics.record_threat_detection()
                
                # Log threat detection
                self.logger.warning("Threats detected in request", extra={
                    "request_id": security_context.request_id,
                    "threats": [t.value for t in assessment.detected_threats],
                    "threat_level": assessment.threat_level.value,
                    "confidence": assessment.confidence
                })
                
                # If high-confidence threats, consider blocking
                if assessment.threat_level.value in ["HIGH", "CRITICAL"] and assessment.confidence > 0.8:
                    self.metrics.record_blocked_request()
                    raise ThreatDetectionError(
                        f"High-confidence threats detected: {[t.value for t in assessment.detected_threats]}"
                    )
            
            security_context.add_layer_result(SecurityLayerType.THREAT_DETECTION, {
                "success": True,
                "assessment_id": assessment.assessment_id,
                "threat_level": assessment.threat_level.value,
                "confidence": assessment.confidence,
                "detected_threats": [t.value for t in assessment.detected_threats]
            })
            
        except Exception as e:
            self.metrics.record_layer_failure(SecurityLayerType.THREAT_DETECTION)
            if isinstance(e, ThreatDetectionError):
                raise
            # Don't fail on threat detection errors unless required
            if layer_config.required:
                raise ThreatDetectionError(f"Threat detection failed: {str(e)}")    

    async def _handle_layer_failure(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        layer_config: SecurityLayerConfig, 
        error: Exception
    ):
        """Handle failure in a security layer."""
        layer_type = layer_config.layer_type
        
        self.logger.error(f"Security layer failure: {layer_type.value}", extra={
            "request_id": security_context.request_id,
            "layer": layer_type.value,
            "error": str(error),
            "fail_open": layer_config.fail_open,
            "required": layer_config.required
        })
        
        # Record layer failure in context
        security_context.add_layer_result(layer_type, {
            "success": False,
            "error": str(error),
            "fail_open": layer_config.fail_open
        })
        
        # Log security event
        await self._log_security_event(request, security_context, "layer_failure", {
            "layer": layer_type.value,
            "error": str(error)
        })
    
    async def _post_process_response(
        self, 
        request: Request, 
        response: Response, 
        security_context: SecurityContext
    ):
        """Post-process response through security layers."""
        # Add security headers
        self._add_security_headers(response, security_context)
        
        # Update threat detection with final result
        if security_context.threat_assessment and self.threat_detector:
            # Update assessment with final success status
            success = 200 <= response.status_code < 400
            # Note: In a real implementation, you'd update the threat detector
            # with the final result for learning purposes
    
    def _add_security_headers(self, response: Response, security_context: SecurityContext):
        """Add security headers to response."""
        # Add correlation ID header
        response.headers["X-Request-ID"] = security_context.request_id
        
        # Add security layer status headers (for debugging)
        if self.config.debug_mode:
            for layer_type, result in security_context.layer_results.items():
                header_name = f"X-Security-{layer_type.value.replace('_', '-').title()}"
                header_value = "success" if result.get("success") else "failed"
                response.headers[header_name] = header_value
    
    async def _create_security_error_response(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        failed_layer: SecurityLayerType, 
        error_message: str
    ) -> JSONResponse:
        """Create appropriate error response for security failures."""
        
        # Determine appropriate status code based on layer
        status_code = 500  # Default server error
        error_type = "security_error"
        
        if failed_layer == SecurityLayerType.MTLS:
            status_code = 401
            error_type = "mtls_error"
        elif failed_layer == SecurityLayerType.JWT:
            status_code = 401
            error_type = "authentication_error"
        elif failed_layer in [SecurityLayerType.RBAC, SecurityLayerType.ABAC]:
            status_code = 403
            error_type = "authorization_error"
        elif failed_layer == SecurityLayerType.THREAT_DETECTION:
            status_code = 429  # Too Many Requests
            error_type = "threat_detected"
        
        error_response = {
            "error": error_type,
            "message": error_message,
            "request_id": security_context.request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add debug information if enabled
        if self.config.debug_mode:
            error_response["debug"] = {
                "failed_layer": failed_layer.value,
                "layer_results": security_context.layer_results
            }
        
        # Log security error event
        await self._log_security_event(request, security_context, "security_error", {
            "failed_layer": failed_layer.value,
            "status_code": status_code,
            "error_message": error_message
        })
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={"X-Request-ID": security_context.request_id}
        )
    
    # Utility methods
    def _generate_request_id(self) -> str:
        """Generate unique request correlation ID."""
        import uuid
        return f"req_{uuid.uuid4().hex[:12]}"
    
    def _simulate_jwt_validation(self, token: str) -> Dict[str, Any]:
        """Simulate JWT validation (replace with actual JWT service integration)."""
        # This is a placeholder - integrate with actual JWT validation
        return {
            "sub": "user123",
            "session_id": "session456",
            "roles": ["user"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time())
        }
    
    def _extract_required_permission(self, request: Request) -> Optional[str]:
        """Extract required permission from request path and method."""
        # Simple permission mapping based on HTTP method and path
        method = request.method.lower()
        path = request.url.path
        
        # Basic permission mapping (customize based on your API structure)
        if path.startswith("/admin"):
            return f"admin.{method}"
        elif path.startswith("/api/v1"):
            return f"api.{method}"
        else:
            return f"general.{method}"
    
    def _build_abac_context(self, request: Request, security_context: SecurityContext) -> Dict[str, Any]:
        """Build ABAC context from request and security context."""
        return {
            "subject": {
                "user_id": security_context.user_id,
                "roles": security_context.rbac_roles,
                "session_id": security_context.session_id
            },
            "resource": {
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params)
            },
            "environment": {
                "time": datetime.now(timezone.utc).isoformat(),
                "client_ip": self._extract_client_ip(request),
                "user_agent": request.headers.get("User-Agent", ""),
                "request_id": security_context.request_id
            },
            "action": {
                "operation": f"{request.method}:{request.url.path}"
            }
        }
    
    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _is_auth_endpoint(self, request: Request) -> bool:
        """Check if request is to an authentication endpoint."""
        auth_paths = ["/auth", "/login", "/token", "/oauth"]
        return any(request.url.path.startswith(path) for path in auth_paths)
    
    # Logging methods
    async def _log_security_success(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        processing_time: float
    ):
        """Log successful security processing."""
        event = SecurityEvent(
            event_type="security_success",
            user_id=security_context.user_id,
            session_id=security_context.session_id,
            source_ip=self._extract_client_ip(request),
            resource=f"{request.method} {request.url.path}",
            outcome="success",
            details={
                "request_id": security_context.request_id,
                "processing_time": processing_time,
                "layers_processed": list(security_context.layer_results.keys()),
                "user_agent": request.headers.get("User-Agent", "")
            }
        )
        
        await self.logger.log_security_event(event)
    
    async def _log_security_failure(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        error: Exception, 
        processing_time: float
    ):
        """Log security processing failure."""
        event = SecurityEvent(
            event_type="security_failure",
            user_id=security_context.user_id,
            session_id=security_context.session_id,
            source_ip=self._extract_client_ip(request),
            resource=f"{request.method} {request.url.path}",
            outcome="failure",
            details={
                "request_id": security_context.request_id,
                "processing_time": processing_time,
                "error": str(error),
                "layers_processed": list(security_context.layer_results.keys()),
                "user_agent": request.headers.get("User-Agent", "")
            }
        )
        
        await self.logger.log_security_event(event)
    
    async def _log_security_event(
        self, 
        request: Request, 
        security_context: SecurityContext, 
        event_type: str, 
        details: Dict[str, Any]
    ):
        """Log a general security event."""
        event = SecurityEvent(
            event_type=event_type,
            user_id=security_context.user_id,
            session_id=security_context.session_id,
            source_ip=self._extract_client_ip(request),
            resource=f"{request.method} {request.url.path}",
            outcome=details.get("outcome", "unknown"),
            details={
                "request_id": security_context.request_id,
                **details
            }
        )
        
        await self.logger.log_security_event(event)
    
    # Metrics and monitoring methods
    def get_metrics(self) -> Dict[str, Any]:
        """Get current security metrics."""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": (
                self.metrics.successful_requests / self.metrics.total_requests 
                if self.metrics.total_requests > 0 else 0
            ),
            "average_processing_time": self.metrics.average_processing_time,
            "layer_failures": dict(self.metrics.layer_failures),
            "threat_detections": self.metrics.threat_detections,
            "blocked_requests": self.metrics.blocked_requests
        }
    
    def reset_metrics(self):
        """Reset security metrics."""
        self.metrics = SecurityMetrics()


# Convenience functions for FastAPI integration
def setup_unified_security_middleware(
    app: FastAPI,
    config: AdvancedSecurityConfig,
    layer_configs: Optional[List[SecurityLayerConfig]] = None,
    mtls_manager: Optional[MTLSManager] = None,
    rbac_engine: Optional[RBACEngine] = None,
    abac_engine: Optional[ABACEngine] = None,
    threat_detector: Optional[ThreatDetector] = None,
    jwt_bearer: Optional[HTTPBearer] = None
) -> UnifiedSecurityMiddleware:
    """
    Setup unified security middleware for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        config: Advanced security configuration
        layer_configs: Optional custom layer configurations
        mtls_manager: Optional mTLS manager instance
        rbac_engine: Optional RBAC engine instance
        abac_engine: Optional ABAC engine instance
        threat_detector: Optional threat detector instance
        jwt_bearer: Optional JWT bearer instance
    
    Returns:
        Configured UnifiedSecurityMiddleware instance
    """
    middleware = UnifiedSecurityMiddleware(
        app=app,
        config=config,
        layer_configs=layer_configs,
        mtls_manager=mtls_manager,
        rbac_engine=rbac_engine,
        abac_engine=abac_engine,
        threat_detector=threat_detector,
        jwt_bearer=jwt_bearer
    )
    
    app.add_middleware(UnifiedSecurityMiddleware, **{
        "config": config,
        "layer_configs": layer_configs,
        "mtls_manager": mtls_manager,
        "rbac_engine": rbac_engine,
        "abac_engine": abac_engine,
        "threat_detector": threat_detector,
        "jwt_bearer": jwt_bearer
    })
    
    return middleware


def create_default_layer_configs(config: AdvancedSecurityConfig) -> List[SecurityLayerConfig]:
    """Create default security layer configurations."""
    return [
        SecurityLayerConfig(
            layer_type=SecurityLayerType.MTLS,
            enabled=config.mtls_enabled,
            required=True,
            fail_open=False,
            timeout_seconds=5.0
        ),
        SecurityLayerConfig(
            layer_type=SecurityLayerType.JWT,
            enabled=True,
            required=True,
            fail_open=False,
            timeout_seconds=3.0
        ),
        SecurityLayerConfig(
            layer_type=SecurityLayerType.RBAC,
            enabled=config.rbac_enabled,
            required=False,
            fail_open=True,
            timeout_seconds=2.0
        ),
        SecurityLayerConfig(
            layer_type=SecurityLayerType.ABAC,
            enabled=config.abac_enabled,
            required=False,
            fail_open=True,
            timeout_seconds=3.0
        ),
        SecurityLayerConfig(
            layer_type=SecurityLayerType.THREAT_DETECTION,
            enabled=config.threat_detection_enabled,
            required=False,
            fail_open=True,
            timeout_seconds=1.0
        )
    ]


# Export main classes and functions
__all__ = [
    "UnifiedSecurityMiddleware",
    "SecurityLayerType",
    "SecurityLayerStatus", 
    "SecurityLayerConfig",
    "SecurityContext",
    "SecurityMetrics",
    "setup_unified_security_middleware",
    "create_default_layer_configs"
]
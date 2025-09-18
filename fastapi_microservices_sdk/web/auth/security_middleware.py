"""
Security Middleware for FastAPI Web Dashboard
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from typing import Optional, List, Callable, Any
import logging
from datetime import datetime

from .jwt_manager import JWTManager, TokenType
from .auth_manager import AuthManager, UserRole

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Advanced security middleware for API protection"""
    
    def __init__(self, 
                 jwt_manager: JWTManager,
                 auth_manager: AuthManager,
                 excluded_paths: List[str] = None):
        self.jwt_manager = jwt_manager
        self.auth_manager = auth_manager
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json",
            "/api/auth/login", "/api/auth/register",
            "/health", "/ping"
        ]
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request, call_next: Callable) -> Any:
        """Middleware execution"""
        try:
            # Check if path is excluded
            if self._is_excluded_path(request.url.path):
                return await call_next(request)
            
            # Extract and verify token
            token = await self._extract_token(request)
            if not token:
                return self._unauthorized_response("Missing or invalid authorization header")
            
            # Verify JWT token
            payload = self.jwt_manager.verify_token(token, TokenType.ACCESS)
            if not payload:
                return self._unauthorized_response("Invalid or expired token")
            
            # Get user information
            user = await self.auth_manager.get_user(payload.user_id)
            if not user or not user.is_active:
                return self._unauthorized_response("User not found or inactive")
            
            # Add user info to request state
            request.state.current_user = user
            request.state.token_payload = payload
            
            # Log access
            logger.info(f"Authenticated request: {user.username} -> {request.method} {request.url.path}")
            
            # Continue with request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return self._server_error_response("Authentication error")
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        try:
            # Try Authorization header first
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                return auth_header.split(" ")[1]
            
            # Try cookie as fallback
            token = request.cookies.get("access_token")
            if token:
                return token
            
            return None
            
        except Exception as e:
            logger.error(f"Token extraction failed: {e}")
            return None
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return unauthorized response"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _server_error_response(self, message: str) -> JSONResponse:
        """Return server error response"""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def _add_security_headers(self, response) -> None:
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"


class RoleBasedAccessControl:
    """Role-based access control decorator and utilities"""
    
    @staticmethod
    def require_role(required_roles: List[UserRole]):
        """Decorator to require specific roles for endpoint access"""
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                # Get current user from request state
                current_user = getattr(request.state, 'current_user', None)
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                # Check if user has required role
                if current_user.role not in required_roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required roles: {[r.value for r in required_roles]}"
                    )
                
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_admin(func):
        """Decorator to require admin role"""
        return RoleBasedAccessControl.require_role([UserRole.ADMIN])(func)
    
    @staticmethod
    def require_developer_or_admin(func):
        """Decorator to require developer or admin role"""
        return RoleBasedAccessControl.require_role([UserRole.DEVELOPER, UserRole.ADMIN])(func)
    
    @staticmethod
    def check_resource_access(user: Any, resource_id: str, action: str) -> bool:
        """Check if user can access specific resource"""
        # Admin can access everything
        if user.role == UserRole.ADMIN:
            return True
        
        # Developer can read/write most resources
        if user.role == UserRole.DEVELOPER:
            if action in ["read", "write", "update"]:
                return True
            if action == "delete":
                # Developers can't delete critical resources
                return not resource_id.startswith("critical_")
        
        # Viewer can only read
        if user.role == UserRole.VIEWER:
            return action == "read"
        
        return False


# Dependency functions for FastAPI
async def get_current_user(request: Request) -> Any:
    """FastAPI dependency to get current authenticated user"""
    user = getattr(request.state, 'current_user', None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user

async def get_current_admin_user(request: Request) -> Any:
    """FastAPI dependency to get current admin user"""
    user = await get_current_user(request)
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def get_current_developer_user(request: Request) -> Any:
    """FastAPI dependency to get current developer or admin user"""
    user = await get_current_user(request)
    if user.role not in [UserRole.DEVELOPER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer or admin access required"
        )
    return user
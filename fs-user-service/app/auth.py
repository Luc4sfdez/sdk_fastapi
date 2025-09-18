"""
Authentication module for fs-user-service.

Integrates FastAPI Microservices SDK JWT authentication.
"""

import sys
from pathlib import Path

# Add SDK to path (temporary solution)
sdk_path = Path(__file__).parent.parent.parent / "fastapi_microservices_sdk"
sys.path.insert(0, str(sdk_path))

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

try:
    from fastapi_microservices_sdk.security.authentication.jwt_service_auth import JWTServiceAuth
except ImportError:
    # Fallback if SDK not available
    JWTServiceAuth = None

auth_router = APIRouter()
security = HTTPBearer()

# Initialize JWT Auth
jwt_auth = None
if JWTServiceAuth:
    jwt_auth = JWTServiceAuth(
        service_name="fs-user-service",
        secret_key="your-secret-key-change-in-production",  # Should come from config
        token_expiry_minutes=30
    )

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    service_name: str


class TokenInfo(BaseModel):
    """Token information model."""
    service_name: str
    token_type: str
    permissions: list
    expires_at: int


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint - generates JWT token.
    
    For now, this is a simple implementation.
    In production, you'd validate against a database.
    """
    # Simple validation (replace with real user validation)
    if request.username == "admin" and request.password == "admin123":
        
        if jwt_auth:
            # Generate service token with user claims
            token = jwt_auth.generate_service_token(
                custom_claims={
                    "username": request.username,
                    "user_type": "admin",
                    "permissions": ["user_read", "user_write", "user_delete"]
                }
            )
            
            return LoginResponse(
                access_token=token,
                expires_in=jwt_auth.token_expiry_minutes * 60,
                service_name=jwt_auth.service_name
            )
        else:
            # Fallback simple token
            return LoginResponse(
                access_token="simple-token-for-testing",
                expires_in=1800,
                service_name="fs-user-service"
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )


@auth_router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh JWT token."""
    
    if not jwt_auth:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="JWT authentication not available"
        )
    
    try:
        # Validate current token
        payload = jwt_auth.validate_token(credentials.credentials)
        
        # Generate new token with same claims
        new_token = jwt_auth.generate_service_token(
            custom_claims={
                "username": payload.get("username"),
                "user_type": payload.get("user_type"),
                "permissions": payload.get("permissions", [])
            }
        )
        
        return LoginResponse(
            access_token=new_token,
            expires_in=jwt_auth.token_expiry_minutes * 60,
            service_name=jwt_auth.service_name
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


@auth_router.get("/me", response_model=TokenInfo)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information from token."""
    
    if not jwt_auth:
        # Fallback for testing
        return TokenInfo(
            service_name="fs-user-service",
            token_type="simple",
            permissions=["user_read"],
            expires_at=0
        )
    
    try:
        payload = jwt_auth.validate_token(credentials.credentials)
        
        return TokenInfo(
            service_name=payload.get("service_name", "fs-user-service"),
            token_type=payload.get("token_type", "service_auth"),
            permissions=payload.get("permissions", []),
            expires_at=payload.get("exp", 0)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


@auth_router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout endpoint."""
    
    # In a real implementation, you'd add the token to a blacklist
    return {"message": "Successfully logged out"}


@auth_router.get("/token/info")
async def get_token_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get detailed token information (for debugging)."""
    
    if not jwt_auth:
        return {"error": "JWT authentication not available"}
    
    token_info = jwt_auth.get_token_info(credentials.credentials)
    return token_info


# Dependency for protected routes
async def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""
    
    if not jwt_auth:
        # Fallback for testing
        return {
            "service_name": "fs-user-service",
            "username": "test_user",
            "permissions": ["user_read"]
        }
    
    try:
        payload = jwt_auth.validate_token(credentials.credentials)
        return payload
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Dependency for admin-only routes
async def get_admin_user_dependency(current_user: Dict[str, Any] = Depends(get_current_user_dependency)) -> Dict[str, Any]:
    """Dependency for admin-only routes."""
    
    user_permissions = current_user.get("permissions", [])
    if "user_write" not in user_permissions and "admin" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    
    return current_user
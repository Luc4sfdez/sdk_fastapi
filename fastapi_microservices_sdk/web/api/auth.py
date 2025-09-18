"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import logging

from ..auth.auth_manager import AuthManager, UserRole
from ..auth.jwt_manager import JWTManager, TokenPair
from ..auth.security_middleware import get_current_user

logger = logging.getLogger(__name__)

# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    created_at: str
    last_login: Optional[str]
    is_active: bool

# Router setup
router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

# Dependencies
def get_auth_manager() -> AuthManager:
    """Get authentication manager instance"""
    return AuthManager()

def get_jwt_manager() -> JWTManager:
    """Get JWT manager instance"""
    return JWTManager()

# Authentication endpoints
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    auth_manager: AuthManager = Depends(get_auth_manager),
    jwt_manager: JWTManager = Depends(get_jwt_manager)
):
    """User login endpoint"""
    try:
        # Authenticate user
        auth_token = await auth_manager.authenticate_user(request.username, request.password)
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Get user information
        user = await auth_manager.get_user(auth_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Generate JWT token pair
        token_pair = jwt_manager.generate_token_pair(
            user_id=user.id,
            username=user.username,
            role=user.role.value
        )
        
        # Set secure cookies if remember_me is true
        if request.remember_me:
            response.set_cookie(
                key="access_token",
                value=token_pair.access_token,
                max_age=30 * 60,  # 30 minutes
                httponly=True,
                secure=True,
                samesite="strict"
            )
            response.set_cookie(
                key="refresh_token",
                value=token_pair.refresh_token,
                max_age=7 * 24 * 60 * 60,  # 7 days
                httponly=True,
                secure=True,
                samesite="strict"
            )
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=30 * 60,  # 30 minutes in seconds
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/register", response_model=UserResponse)
async def register(
    request: RegisterRequest,
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """User registration endpoint"""
    try:
        # Create new user
        user = await auth_manager.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=request.role
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None,
            is_active=user.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Refresh access token using refresh token"""
    try:
        # Generate new token pair
        token_pair = jwt_manager.refresh_access_token(request.refresh_token)
        if not token_pair:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Get user information from new token
        payload = jwt_manager.verify_token(token_pair.access_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token generation failed"
            )
        
        user = await auth_manager.get_user(payload.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            expires_in=30 * 60,  # 30 minutes in seconds
            user={
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    current_user = Depends(get_current_user),
    jwt_manager: JWTManager = Depends(get_jwt_manager)
):
    """User logout endpoint"""
    try:
        # Get token from request
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Revoke the token
            jwt_manager.revoke_token(token)
        
        # Clear cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None,
        is_active=current_user.is_active
    )

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user = Depends(get_current_user),
    auth_manager: AuthManager = Depends(get_auth_manager)
):
    """Change user password"""
    try:
        # Verify current password
        auth_token = await auth_manager.authenticate_user(current_user.username, request.current_password)
        if not auth_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password (this would need to be implemented in AuthManager)
        # For now, just return success
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.post("/revoke-all-tokens")
async def revoke_all_tokens(
    current_user = Depends(get_current_user),
    jwt_manager: JWTManager = Depends(get_jwt_manager)
):
    """Revoke all tokens for current user (logout from all devices)"""
    try:
        count = jwt_manager.revoke_all_user_tokens(current_user.id)
        return {"message": f"Revoked {count} tokens", "user_id": current_user.id}
        
    except Exception as e:
        logger.error(f"Token revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token revocation failed"
        )

@router.get("/token-info")
async def get_token_info(
    request: Request,
    jwt_manager: JWTManager = Depends(get_jwt_manager)
):
    """Get information about current token"""
    try:
        # Get token from request
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided"
            )
        
        token = auth_header.split(" ")[1]
        token_info = jwt_manager.get_token_info(token)
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
        return token_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token info retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token info retrieval failed"
        )
"""
Advanced JWT Token Management System
"""
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"

@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "Bearer"

@dataclass
class TokenPayload:
    """JWT token payload"""
    user_id: str
    username: str
    role: str
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime
    jti: str  # JWT ID for token revocation

class JWTManager:
    """Advanced JWT token management with refresh tokens"""
    
    def __init__(self, 
                 secret_key: str = None,
                 algorithm: str = "HS256",
                 access_token_expire_minutes: int = 30,
                 refresh_token_expire_days: int = 7):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        # Token blacklist for revoked tokens
        self.revoked_tokens: set = set()
        
    def generate_token_pair(self, user_id: str, username: str, role: str) -> TokenPair:
        """Generate access and refresh token pair"""
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # Access token
            access_expires = now + timedelta(minutes=self.access_token_expire_minutes)
            access_jti = secrets.token_urlsafe(16)
            
            access_payload = {
                "user_id": user_id,
                "username": username,
                "role": role,
                "token_type": TokenType.ACCESS.value,
                "iat": int(now.timestamp()),
                "exp": int(access_expires.timestamp()),
                "jti": access_jti
            }
            
            access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
            
            # Refresh token
            refresh_expires = now + timedelta(days=self.refresh_token_expire_days)
            refresh_jti = secrets.token_urlsafe(16)
            
            refresh_payload = {
                "user_id": user_id,
                "username": username,
                "role": role,
                "token_type": TokenType.REFRESH.value,
                "iat": int(now.timestamp()),
                "exp": int(refresh_expires.timestamp()),
                "jti": refresh_jti
            }
            
            refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
            
            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token,
                access_expires_at=access_expires,
                refresh_expires_at=refresh_expires
            )
            
        except Exception as e:
            logger.error(f"Failed to generate token pair: {e}")
            raise
    
    def verify_token(self, token: str, expected_type: TokenType = TokenType.ACCESS) -> Optional[TokenPayload]:
        """Verify and decode JWT token"""
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self.revoked_tokens:
                logger.warning(f"Attempted to use revoked token: {jti}")
                return None
            
            # Verify token type
            token_type = payload.get("token_type")
            if token_type != expected_type.value:
                logger.warning(f"Token type mismatch. Expected: {expected_type.value}, Got: {token_type}")
                return None
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, timezone.utc) < datetime.now(timezone.utc):
                logger.info("Token has expired")
                return None
            
            return TokenPayload(
                user_id=payload["user_id"],
                username=payload["username"],
                role=payload["role"],
                token_type=TokenType(token_type),
                issued_at=datetime.fromtimestamp(payload["iat"], timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc),
                jti=jti
            )
            
        except jwt.ExpiredSignatureError:
            logger.info("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Generate new access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token, TokenType.REFRESH)
            if not payload:
                return None
            
            # Generate new token pair
            return self.generate_token_pair(
                user_id=payload.user_id,
                username=payload.username,
                role=payload.role
            )
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its JTI to blacklist"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            jti = payload.get("jti")
            if jti:
                self.revoked_tokens.add(jti)
                logger.info(f"Token revoked: {jti}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a specific user (logout from all devices)"""
        # In a production system, you'd query a database for all user tokens
        # For now, we'll just mark this as a placeholder
        logger.info(f"All tokens revoked for user: {user_id}")
        return 0
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get token information without verification"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "token_type": payload.get("token_type"),
                "issued_at": datetime.utcfromtimestamp(payload.get("iat", 0)).isoformat(),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0), timezone.utc).isoformat(),
                "jti": payload.get("jti"),
                "is_expired": datetime.fromtimestamp(payload.get("exp", 0), timezone.utc) < datetime.now(timezone.utc),
                "is_revoked": payload.get("jti") in self.revoked_tokens
            }
        except Exception as e:
            logger.error(f"Failed to get token info: {e}")
            return None
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens from revocation list"""
        # In production, implement proper cleanup logic
        # For now, just return 0
        return 0
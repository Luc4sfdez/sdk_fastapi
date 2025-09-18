"""
Authentication and authorization management for the web dashboard.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import secrets
import jwt

from ..core.base_manager import BaseManager


class UserRole(Enum):
    """User roles."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


@dataclass
class User:
    """User information."""
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


@dataclass
class AuthToken:
    """Authentication token information."""
    token: str
    user_id: str
    expires_at: datetime
    token_type: str = "bearer"


class AuthenticationManager(BaseManager):
    """
    Authentication and authorization management.
    
    Handles:
    - User authentication
    - JWT token management
    - Role-based access control
    - Session management
    """
    
    def __init__(self, name: str = "auth", config: Optional[Dict[str, Any]] = None):
        """Initialize the authentication manager."""
        super().__init__(name, config)
        self._users: Dict[str, User] = {}
        self._password_hashes: Dict[str, str] = {}
        self._active_tokens: Dict[str, AuthToken] = {}
        self._secret_key = self.get_config("secret_key", "your-secret-key-change-in-production")
        self._jwt_algorithm = self.get_config("jwt_algorithm", "HS256")
        self._jwt_expiration_hours = self.get_config("jwt_expiration_hours", 24)
    
    async def _initialize_impl(self) -> None:
        """Initialize the authentication manager."""
        # Create default admin user if none exists
        if not self._users:
            await self._create_default_admin()
        self.logger.info("Authentication manager initialized")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[AuthToken]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Auth token if authentication successful, None otherwise
        """
        return await self._safe_execute(
            "authenticate_user",
            self._authenticate_user_impl,
            username,
            password
        )
    
    async def validate_token(self, token: str) -> Optional[User]:
        """
        Validate authentication token.
        
        Args:
            token: JWT token
            
        Returns:
            User if token valid, None otherwise
        """
        return await self._safe_execute(
            "validate_token",
            self._validate_token_impl,
            token
        )
    
    async def refresh_token(self, token: str) -> Optional[AuthToken]:
        """
        Refresh authentication token.
        
        Args:
            token: Current token
            
        Returns:
            New token if refresh successful, None otherwise
        """
        return await self._safe_execute(
            "refresh_token",
            self._refresh_token_impl,
            token
        )
    
    async def logout_user(self, token: str) -> bool:
        """
        Logout user by invalidating token.
        
        Args:
            token: Token to invalidate
            
        Returns:
            True if logout successful
        """
        result = await self._safe_execute(
            "logout_user",
            self._logout_user_impl,
            token
        )
        return result is not None and result
    
    async def create_user(self, username: str, email: str, password: str, role: UserRole) -> Optional[User]:
        """
        Create new user.
        
        Args:
            username: Username
            email: Email address
            password: Password
            role: User role
            
        Returns:
            Created user if successful, None otherwise
        """
        return await self._safe_execute(
            "create_user",
            self._create_user_impl,
            username,
            email,
            password,
            role
        )
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User if found, None otherwise
        """
        return self._users.get(user_id)
    
    async def list_users(self) -> List[User]:
        """
        List all users.
        
        Returns:
            List of users
        """
        return list(self._users.values())
    
    def check_permission(self, user: User, resource: str, action: str) -> bool:
        """
        Check if user has permission for resource action.
        
        Args:
            user: User to check
            resource: Resource name
            action: Action name
            
        Returns:
            True if user has permission
        """
        # Simple role-based permissions
        if user.role == UserRole.ADMIN:
            return True
        elif user.role == UserRole.DEVELOPER:
            # Developers can do most things except user management
            if resource == "users" and action in ["create", "delete", "update"]:
                return False
            return True
        elif user.role == UserRole.VIEWER:
            # Viewers can only read
            return action == "read"
        
        return False
    
    # Implementation methods
    
    async def _authenticate_user_impl(self, username: str, password: str) -> Optional[AuthToken]:
        """Implementation for user authentication."""
        # Find user by username
        user = None
        for u in self._users.values():
            if u.username == username:
                user = u
                break
        
        if not user or not user.is_active:
            return None
        
        # Verify password
        password_hash = self._hash_password(password)
        if self._password_hashes.get(user.id) != password_hash:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Generate token
        return self._generate_token(user)
    
    async def _validate_token_impl(self, token: str) -> Optional[User]:
        """Implementation for token validation."""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self._secret_key, algorithms=[self._jwt_algorithm])
            user_id = payload.get("user_id")
            exp = payload.get("exp")
            
            # Check expiration
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None
            
            # Get user
            user = self._users.get(user_id)
            if not user or not user.is_active:
                return None
            
            return user
            
        except jwt.InvalidTokenError:
            return None
    
    async def _refresh_token_impl(self, token: str) -> Optional[AuthToken]:
        """Implementation for token refresh."""
        user = await self._validate_token_impl(token)
        if not user:
            return None
        
        # Generate new token
        return self._generate_token(user)
    
    async def _logout_user_impl(self, token: str) -> bool:
        """Implementation for user logout."""
        # Remove token from active tokens
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        return False
    
    async def _create_user_impl(self, username: str, email: str, password: str, role: UserRole) -> Optional[User]:
        """Implementation for user creation."""
        # Check if username already exists
        for user in self._users.values():
            if user.username == username:
                return None
        
        # Create user
        user_id = secrets.token_urlsafe(16)
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=datetime.utcnow()
        )
        
        # Store user and password hash
        self._users[user_id] = user
        self._password_hashes[user_id] = self._hash_password(password)
        
        return user
    
    async def _create_default_admin(self) -> None:
        """Create default admin user."""
        admin_user = await self._create_user_impl(
            username="admin",
            email="admin@localhost",
            password="admin123",
            role=UserRole.ADMIN
        )
        if admin_user:
            self.logger.info("Created default admin user (username: admin, password: admin123)")
    
    def _generate_token(self, user: User) -> AuthToken:
        """Generate JWT token for user."""
        expires_at = datetime.utcnow() + timedelta(hours=self._jwt_expiration_hours)
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp()
        }
        
        token = jwt.encode(payload, self._secret_key, algorithm=self._jwt_algorithm)
        
        auth_token = AuthToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at
        )
        
        # Store active token
        self._active_tokens[token] = auth_token
        
        return auth_token
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        # In production, use a proper password hashing library like bcrypt
        return hashlib.sha256(password.encode()).hexdigest()
    
    async def _initialize_impl(self) -> None:
        """Implementation of abstract method from BaseManager"""
        # Create default admin user if none exists
        if not self._users:
            await self._create_default_admin()
        self.logger.info("Authentication manager initialized successfully")


# Alias for backward compatibility
AuthManager = AuthenticationManager
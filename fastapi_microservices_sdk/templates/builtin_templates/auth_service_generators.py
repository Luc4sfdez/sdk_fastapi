"""
Authentication Service Template - Additional Generators

Additional generator methods for the authentication service template.
"""

from typing import Dict, Any, List
from pathlib import Path


class AuthServiceGenerators:
    """Additional generators for authentication service template."""
    
    @staticmethod
    def generate_database_config(variables: Dict[str, Any]) -> str:
        """Generate database configuration."""
        database_type = variables.get("database_type", "postgresql")
        
        if database_type == "mongodb":
            return '''"""
Database Configuration for MongoDB

MongoDB connection and configuration.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from typing import Optional

from ..models.user import User
from ..models.role import Role
from ..models.permission import Permission
from ..config import settings


class Database:
    """Database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    database = None


db = Database()


async def connect_to_mongo():
    """Create database connection."""
    db.client = AsyncIOMotorClient(settings.DATABASE_URL)
    db.database = db.client[settings.DATABASE_NAME]
    
    # Initialize Beanie with document models
    await init_beanie(
        database=db.database,
        document_models=[User, Role, Permission]
    )


async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()


async def get_database():
    """Get database instance."""
    return db.database
'''
        else:
            return f'''"""
Database Configuration for {database_type.title()}

SQLAlchemy database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from ..config import settings

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop database tables."""
    Base.metadata.drop_all(bind=engine)
'''
    
    @staticmethod
    def generate_user_service(variables: Dict[str, Any]) -> str:
        """Generate user service."""
        enable_rbac = variables.get("enable_rbac", True)
        enable_2fa = variables.get("enable_2fa", False)
        database_type = variables.get("database_type", "postgresql")
        
        if database_type == "mongodb":
            return f'''"""
User Service for MongoDB

Business logic for user operations with MongoDB.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from beanie import PydanticObjectId
from fastapi import HTTPException, status

from ..models.user import User
from ..models.role import Role
from ..models.permission import Permission
from ..schemas.user import UserCreate, UserUpdate, UserPasswordUpdate
from ..auth.password import password_handler
from ..utils.email import send_verification_email, send_password_reset_email
from ..config import settings


class UserService:
    """User service for business logic."""
    
    async def create_user(self, user_data: UserCreate, verify_email: bool = True) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await User.find_one(
            {{"$or": [{{"email": user_data.email}}, {{"username": user_data.username}}]}}
        )
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username.lower(),
            full_name=user_data.full_name,
            hashed_password=password_handler.hash_password(user_data.password),
            is_verified=not verify_email
        )
        
        await user.insert()
        
        # Send verification email if required
        if verify_email and settings.ENABLE_EMAIL_VERIFICATION:
            await send_verification_email(user.email, user.id)
        
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            return await User.get(PydanticObjectId(user_id))
        except:
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await User.find_one(User.email == email)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await User.find_one(User.username == username.lower())
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        # Check for email/username conflicts
        if "email" in update_data:
            existing = await User.find_one(
                {{"email": update_data["email"], "_id": {{"$ne": user.id}}}}
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        if "username" in update_data:
            update_data["username"] = update_data["username"].lower()
            existing = await User.find_one(
                {{"username": update_data["username"], "_id": {{"$ne": user.id}}}}
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        update_data["updated_at"] = datetime.utcnow()
        
        await user.update({{"$set": update_data}})
        return await self.get_user_by_id(user_id)
    
    async def change_password(self, user_id: str, password_data: UserPasswordUpdate) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not password_handler.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = password_handler.hash_password(password_data.new_password)
        user.updated_at = datetime.utcnow()
        await user.save()
        
        return True
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        await user.delete()
        return True
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        # Check if account is locked
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to too many failed login attempts"
            )
        
        # Verify password
        if not password_handler.verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.increment_login_attempts()
            
            # Lock account if too many attempts
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.lock_account(settings.LOCKOUT_DURATION_MINUTES)
            
            await user.save()
            return None
        
        # Successful login
        user.update_last_login()
        await user.save()
        
        return user
    
    async def get_users(self, skip: int = 0, limit: int = 100, search: str = None) -> List[User]:
        """Get users with pagination and search."""
        query = {{}}
        
        if search:
            query["$or"] = [
                {{"email": {{"$regex": search, "$options": "i"}}}},
                {{"username": {{"$regex": search, "$options": "i"}}}},
                {{"full_name": {{"$regex": search, "$options": "i"}}}}
            ]
        
        return await User.find(query).skip(skip).limit(limit).to_list()
    
    async def count_users(self, search: str = None) -> int:
        """Count users."""
        query = {{}}
        
        if search:
            query["$or"] = [
                {{"email": {{"$regex": search, "$options": "i"}}}},
                {{"username": {{"$regex": search, "$options": "i"}}}},
                {{"full_name": {{"$regex": search, "$options": "i"}}}}
            ]
        
        return await User.find(query).count()
    
    {"async def assign_role(self, user_id: str, role_id: str) -> bool:" if enable_rbac else ""}
    {f'''    \"\"\"Assign role to user.\"\"\"
        user = await self.get_user_by_id(user_id)
        role = await Role.get(PydanticObjectId(role_id))
        
        if not user or not role:
            return False
        
        if role_id not in user.role_ids:
            user.role_ids.append(role_id)
            await user.save()
        
        return True''' if enable_rbac else ""}
    
    {"async def remove_role(self, user_id: str, role_id: str) -> bool:" if enable_rbac else ""}
    {f'''    \"\"\"Remove role from user.\"\"\"
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if role_id in user.role_ids:
            user.role_ids.remove(role_id)
            await user.save()
        
        return True''' if enable_rbac else ""}
'''
        else:
            # SQLAlchemy version
            return f'''"""
User Service for SQLAlchemy

Business logic for user operations with SQLAlchemy.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status

from ..models.user import User
{"from ..models.role import Role" if enable_rbac else ""}
{"from ..models.permission import Permission" if enable_rbac else ""}
from ..schemas.user import UserCreate, UserUpdate, UserPasswordUpdate
from ..auth.password import password_handler
from ..utils.email import send_verification_email, send_password_reset_email
from ..config import settings


class UserService:
    """User service for business logic."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_user(self, user_data: UserCreate, verify_email: bool = True) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            or_(User.email == user_data.email, User.username == user_data.username.lower())
        ).first()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username.lower(),
            full_name=user_data.full_name,
            hashed_password=password_handler.hash_password(user_data.password),
            is_verified=not verify_email
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Send verification email if required
        if verify_email and settings.ENABLE_EMAIL_VERIFICATION:
            await send_verification_email(user.email, user.id)
        
        return user
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username.lower()).first()
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """Update user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        
        # Check for email/username conflicts
        if "email" in update_data:
            existing = self.db.query(User).filter(
                and_(User.email == update_data["email"], User.id != user_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        if "username" in update_data:
            update_data["username"] = update_data["username"].lower()
            existing = self.db.query(User).filter(
                and_(User.username == update_data["username"], User.id != user_id)
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Update user
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    async def change_password(self, user_id: int, password_data: UserPasswordUpdate) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # Verify current password
        if not password_handler.verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.hashed_password = password_handler.hash_password(password_data.new_password)
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    async def delete_user(self, user_id: int) -> bool:
        """Delete user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        return True
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        # Check if account is locked
        if user.is_locked():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to too many failed login attempts"
            )
        
        # Verify password
        if not password_handler.verify_password(password, user.hashed_password):
            # Increment failed attempts
            user.increment_login_attempts()
            
            # Lock account if too many attempts
            if user.login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.lock_account(settings.LOCKOUT_DURATION_MINUTES)
            
            self.db.commit()
            return None
        
        # Successful login
        user.update_last_login()
        self.db.commit()
        
        return user
    
    async def get_users(self, skip: int = 0, limit: int = 100, search: str = None) -> List[User]:
        """Get users with pagination and search."""
        query = self.db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{{search}}%"),
                    User.username.ilike(f"%{{search}}%"),
                    User.full_name.ilike(f"%{{search}}%")
                )
            )
        
        return query.offset(skip).limit(limit).all()
    
    async def count_users(self, search: str = None) -> int:
        """Count users."""
        query = self.db.query(User)
        
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{{search}}%"),
                    User.username.ilike(f"%{{search}}%"),
                    User.full_name.ilike(f"%{{search}}%")
                )
            )
        
        return query.count()
    
    {"async def assign_role(self, user_id: int, role_id: int) -> bool:" if enable_rbac else ""}
    {f'''    \"\"\"Assign role to user.\"\"\"
        user = await self.get_user_by_id(user_id)
        role = self.db.query(Role).filter(Role.id == role_id).first()
        
        if not user or not role:
            return False
        
        if role not in user.roles:
            user.roles.append(role)
            self.db.commit()
        
        return True''' if enable_rbac else ""}
    
    {"async def remove_role(self, user_id: int, role_id: int) -> bool:" if enable_rbac else ""}
    {f'''    \"\"\"Remove role from user.\"\"\"
        user = await self.get_user_by_id(user_id)
        role = self.db.query(Role).filter(Role.id == role_id).first()
        
        if not user or not role:
            return False
        
        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()
        
        return True''' if enable_rbac else ""}
'''
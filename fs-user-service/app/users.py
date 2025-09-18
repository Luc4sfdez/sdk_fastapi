"""
Users API endpoints for fs-user-service.

Demonstrates protected routes using JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

from .auth import get_current_user_dependency, get_admin_user_dependency

users_router = APIRouter()

# Mock user data (replace with database in production)
MOCK_USERS = [
    {
        "id": 1,
        "username": "admin",
        "email": "admin@facturascripts.com",
        "nombre": "Administrador",
        "apellidos": "Sistema",
        "rol": "admin",
        "activo": True,
        "fecha_creacion": "2024-01-01T00:00:00Z",
        "ultima_conexion": "2024-12-15T10:30:00Z"
    },
    {
        "id": 2,
        "username": "usuario1",
        "email": "usuario1@empresa.com",
        "nombre": "Juan",
        "apellidos": "Pérez García",
        "rol": "user",
        "activo": True,
        "fecha_creacion": "2024-06-15T09:00:00Z",
        "ultima_conexion": "2024-12-14T16:45:00Z"
    },
    {
        "id": 3,
        "username": "contable",
        "email": "contable@empresa.com",
        "nombre": "María",
        "apellidos": "López Martín",
        "rol": "accountant",
        "activo": True,
        "fecha_creacion": "2024-03-10T14:20:00Z",
        "ultima_conexion": "2024-12-15T08:15:00Z"
    }
]


class User(BaseModel):
    """User model."""
    id: int
    username: str
    email: str
    nombre: str
    apellidos: str
    rol: str
    activo: bool
    fecha_creacion: str
    ultima_conexion: Optional[str] = None


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: str
    nombre: str
    apellidos: str
    rol: str = "user"
    password: str


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[str] = None
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    id: int
    username: str
    email: str
    nombre: str
    apellidos: str
    rol: str
    activo: bool
    fecha_creacion: str
    ultima_conexion: Optional[str] = None


@users_router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user_dependency)
):
    """
    Get list of users.
    
    Requires authentication.
    """
    # Filter users based on pagination
    users = MOCK_USERS[skip:skip + limit]
    
    return [UserResponse(**user) for user in users]


@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user_dependency)
):
    """
    Get user by ID.
    
    Requires authentication.
    """
    user = next((u for u in MOCK_USERS if u["id"] == user_id), None)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)


@users_router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: Dict[str, Any] = Depends(get_admin_user_dependency)
):
    """
    Create new user.
    
    Requires admin permissions.
    """
    # Check if username already exists
    if any(u["username"] == user_data.username for u in MOCK_USERS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create new user
    new_user = {
        "id": max(u["id"] for u in MOCK_USERS) + 1,
        "username": user_data.username,
        "email": user_data.email,
        "nombre": user_data.nombre,
        "apellidos": user_data.apellidos,
        "rol": user_data.rol,
        "activo": True,
        "fecha_creacion": datetime.now().isoformat() + "Z",
        "ultima_conexion": None
    }
    
    MOCK_USERS.append(new_user)
    
    return UserResponse(**new_user)


@users_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_admin_user_dependency)
):
    """
    Update user.
    
    Requires admin permissions.
    """
    user_index = next((i for i, u in enumerate(MOCK_USERS) if u["id"] == user_id), None)
    
    if user_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user data
    user = MOCK_USERS[user_index]
    update_data = user_data.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if key in user:
            user[key] = value
    
    return UserResponse(**user)


@users_router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_admin_user_dependency)
):
    """
    Delete user.
    
    Requires admin permissions.
    """
    user_index = next((i for i, u in enumerate(MOCK_USERS) if u["id"] == user_id), None)
    
    if user_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Don't allow deleting admin user
    if MOCK_USERS[user_index]["username"] == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin user"
        )
    
    deleted_user = MOCK_USERS.pop(user_index)
    
    return {
        "message": f"User {deleted_user['username']} deleted successfully",
        "deleted_user_id": user_id
    }


@users_router.get("/profile/me", response_model=UserResponse)
async def get_my_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_dependency)
):
    """
    Get current user's profile.
    
    Requires authentication.
    """
    username = current_user.get("username", "admin")
    user = next((u for u in MOCK_USERS if u["username"] == username), None)
    
    if not user:
        # Return basic info from token if user not found in mock data
        return UserResponse(
            id=0,
            username=username,
            email=f"{username}@facturascripts.com",
            nombre="Usuario",
            apellidos="Token",
            rol=current_user.get("user_type", "user"),
            activo=True,
            fecha_creacion=datetime.now().isoformat() + "Z"
        )
    
    return UserResponse(**user)


@users_router.get("/stats/summary", operation_id="get_users_statistics")
async def get_user_stats(
    current_user: Dict[str, Any] = Depends(get_current_user_dependency)
):
    """
    Get user statistics summary.
    
    Requires authentication.
    """
    total_users = len(MOCK_USERS)
    active_users = len([u for u in MOCK_USERS if u["activo"]])
    roles_count = {}
    
    for user in MOCK_USERS:
        role = user["rol"]
        roles_count[role] = roles_count.get(role, 0) + 1
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "roles_distribution": roles_count,
        "last_updated": datetime.now().isoformat() + "Z"
    }
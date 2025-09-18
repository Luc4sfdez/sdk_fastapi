# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control) System for FastAPI Microservices SDK.

This module provides a comprehensive RBAC implementation with:
- Hierarchical role system with inheritance
- Granular permission management
- Dynamic role assignment and revocation
- Context-aware permissions
- Performance optimizations with caching

Author: FastAPI Microservices SDK Team
Version: 1.0.0
Date: 2025-09-02
"""

from __future__ import annotations

import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
from abc import ABC, abstractmethod

from .exceptions import (
    AdvancedSecurityError, RBACError, RoleError, PermissionError
)
from .logging import get_security_logger, SecurityEventType


# =============================================================================
# RBAC Enums and Constants
# =============================================================================

class ActionType(str, Enum):
    """Standard action types for permissions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    LIST = "list"
    SEARCH = "search"
    EXPORT = "export"
    IMPORT = "import"


class ResourceType(str, Enum):
    """Standard resource types."""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    SERVICE = "service"
    API = "api"
    DATA = "data"
    FILE = "file"
    SYSTEM = "system"
    AUDIT = "audit"
    CONFIG = "config"


class PermissionEffect(str, Enum):
    """Permission effect types."""
    ALLOW = "allow"
    DENY = "deny"


class RoleType(str, Enum):
    """Role classification types."""
    SYSTEM = "system"        # Built-in system roles
    SERVICE = "service"      # Service-specific roles
    CUSTOM = "custom"        # User-defined roles
    TEMPORARY = "temporary"  # Temporary elevated roles


# =============================================================================
# RBAC Data Models
# =============================================================================

class Permission(BaseModel):
    """
    Permission model representing a specific action on a resource.
    
    Permissions define what actions can be performed on specific resources,
    with optional conditions for context-aware access control.
    """
    
    id: str = Field(..., description="Unique permission identifier")
    resource: str = Field(..., description="Resource type or name")
    action: ActionType = Field(..., description="Action type")
    effect: PermissionEffect = Field(default=PermissionEffect.ALLOW, description="Permission effect")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Context conditions")
    description: Optional[str] = Field(default=None, description="Permission description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('id')
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Permission ID cannot be empty")
        return v.strip()
    
    @validator('resource')
    def validate_resource(cls, v):
        if not v or not v.strip():
            raise ValueError("Resource cannot be empty")
        return v.strip().lower()
    
    def matches_resource(self, resource: str) -> bool:
        """Check if this permission matches a given resource."""
        # Support wildcards
        if self.resource == "*":
            return True
        if self.resource.endswith("*"):
            return resource.startswith(self.resource[:-1])
        return self.resource == resource.lower()
    
    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate permission conditions against context."""
        if not self.conditions:
            return True
        
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
            
            actual_value = context[key]
            
            # Handle different condition types
            if isinstance(expected_value, dict):
                # Complex conditions (e.g., {"$gt": 18} for age > 18)
                if not self._evaluate_complex_condition(actual_value, expected_value):
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    def _evaluate_complex_condition(self, actual: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate complex conditions like $gt, $lt, $in, etc."""
        for operator, value in condition.items():
            if operator == "$gt" and not (actual > value):
                return False
            elif operator == "$gte" and not (actual >= value):
                return False
            elif operator == "$lt" and not (actual < value):
                return False
            elif operator == "$lte" and not (actual <= value):
                return False
            elif operator == "$in" and actual not in value:
                return False
            elif operator == "$nin" and actual in value:
                return False
            elif operator == "$ne" and actual == value:
                return False
        return True
    
    def __str__(self) -> str:
        return f"{self.effect.value}:{self.action.value}:{self.resource}"
    
    def __hash__(self) -> int:
        return hash((self.id, self.resource, self.action.value, self.effect.value))


class Role(BaseModel):
    """
    Role model representing a collection of permissions with hierarchy support.
    
    Roles can inherit from parent roles, creating a hierarchical permission system.
    """
    
    id: str = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Human-readable role name")
    description: Optional[str] = Field(default=None, description="Role description")
    role_type: RoleType = Field(default=RoleType.CUSTOM, description="Role classification")
    parent_roles: List[str] = Field(default_factory=list, description="Parent role IDs for inheritance")
    permissions: List[str] = Field(default_factory=list, description="Direct permission IDs")
    is_active: bool = Field(default=True, description="Whether role is active")
    priority: int = Field(default=0, description="Role priority for conflict resolution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('id')
    def validate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Role ID cannot be empty")
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()
    
    @validator('parent_roles')
    def validate_parent_roles(cls, v, values):
        # Prevent self-reference
        role_id = values.get('id')
        if role_id and role_id in v:
            raise ValueError("Role cannot be its own parent")
        return v
    
    def add_permission(self, permission_id: str) -> None:
        """Add a permission to this role."""
        if permission_id not in self.permissions:
            self.permissions.append(permission_id)
            self.updated_at = datetime.utcnow()
    
    def remove_permission(self, permission_id: str) -> None:
        """Remove a permission from this role."""
        if permission_id in self.permissions:
            self.permissions.remove(permission_id)
            self.updated_at = datetime.utcnow()
    
    def add_parent_role(self, parent_role_id: str) -> None:
        """Add a parent role for inheritance."""
        if parent_role_id != self.id and parent_role_id not in self.parent_roles:
            self.parent_roles.append(parent_role_id)
            self.updated_at = datetime.utcnow()
    
    def remove_parent_role(self, parent_role_id: str) -> None:
        """Remove a parent role."""
        if parent_role_id in self.parent_roles:
            self.parent_roles.remove(parent_role_id)
            self.updated_at = datetime.utcnow()
    
    def __str__(self) -> str:
        return f"Role({self.id}: {self.name})"
    
    def __hash__(self) -> int:
        return hash(self.id)


class UserRole(BaseModel):
    """
    User-Role assignment model with temporal and conditional constraints.
    
    Represents the assignment of a role to a user with optional expiration
    and conditions.
    """
    
    user_id: str = Field(..., description="User identifier")
    role_id: str = Field(..., description="Role identifier")
    granted_by: str = Field(..., description="Who granted this role")
    granted_at: datetime = Field(default_factory=datetime.utcnow, description="When role was granted")
    expires_at: Optional[datetime] = Field(default=None, description="When role expires")
    is_active: bool = Field(default=True, description="Whether assignment is active")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Assignment conditions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('user_id', 'role_id', 'granted_by')
    def validate_ids(cls, v):
        if not v or not v.strip():
            raise ValueError("ID fields cannot be empty")
        return v.strip()
    
    def is_expired(self) -> bool:
        """Check if this role assignment has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this role assignment is currently valid."""
        if not self.is_active:
            return False
        
        if self.is_expired():
            return False
        
        if self.conditions and context:
            return self._evaluate_conditions(context)
        
        return True
    
    def _evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate assignment conditions against context."""
        if not self.conditions:
            return True
        
        # Similar to Permission condition evaluation
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
            
            actual_value = context[key]
            if actual_value != expected_value:
                return False
        
        return True
    
    def extend_expiration(self, duration: timedelta) -> None:
        """Extend the expiration time of this role assignment."""
        if self.expires_at:
            self.expires_at += duration
        else:
            self.expires_at = datetime.utcnow() + duration
    
    def __str__(self) -> str:
        return f"UserRole({self.user_id} -> {self.role_id})"


@dataclass
class RoleHierarchy:
    """
    Role hierarchy representation for efficient permission resolution.
    
    Maintains the hierarchical structure of roles and provides methods
    for traversing the hierarchy.
    """
    
    roles: Dict[str, Role] = field(default_factory=dict)
    _hierarchy_cache: Dict[str, Set[str]] = field(default_factory=dict)
    _permission_cache: Dict[str, Set[str]] = field(default_factory=dict)
    _cache_ttl: int = 300  # 5 minutes
    _last_cache_update: float = field(default_factory=time.time)
    
    def add_role(self, role: Role) -> None:
        """Add a role to the hierarchy."""
        self.roles[role.id] = role
        self._invalidate_cache()
    
    def remove_role(self, role_id: str) -> None:
        """Remove a role from the hierarchy."""
        if role_id in self.roles:
            # Remove from parent roles of other roles
            for role in self.roles.values():
                if role_id in role.parent_roles:
                    role.remove_parent_role(role_id)
            
            del self.roles[role_id]
            self._invalidate_cache()
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self.roles.get(role_id)
    
    def get_all_parent_roles(self, role_id: str) -> Set[str]:
        """Get all parent roles (including transitive parents) for a role."""
        if self._is_cache_valid() and role_id in self._hierarchy_cache:
            return self._hierarchy_cache[role_id].copy()
        
        parents = set()
        visited = set()
        
        def _collect_parents(current_role_id: str):
            if current_role_id in visited:
                return  # Prevent infinite loops
            
            visited.add(current_role_id)
            role = self.roles.get(current_role_id)
            
            if role:
                for parent_id in role.parent_roles:
                    if parent_id in self.roles:
                        parents.add(parent_id)
                        _collect_parents(parent_id)
        
        _collect_parents(role_id)
        
        # Cache the result
        self._hierarchy_cache[role_id] = parents.copy()
        return parents
    
    def get_all_permissions(self, role_id: str) -> Set[str]:
        """Get all permissions for a role (including inherited permissions)."""
        if self._is_cache_valid() and role_id in self._permission_cache:
            return self._permission_cache[role_id].copy()
        
        permissions = set()
        
        # Get direct permissions
        role = self.roles.get(role_id)
        if role:
            permissions.update(role.permissions)
        
        # Get inherited permissions
        parent_roles = self.get_all_parent_roles(role_id)
        for parent_id in parent_roles:
            parent_role = self.roles.get(parent_id)
            if parent_role:
                permissions.update(parent_role.permissions)
        
        # Cache the result
        self._permission_cache[role_id] = permissions.copy()
        return permissions
    
    def has_circular_dependency(self, role_id: str, parent_id: str) -> bool:
        """Check if adding a parent would create a circular dependency."""
        if role_id == parent_id:
            return True
        
        parent_ancestors = self.get_all_parent_roles(parent_id)
        return role_id in parent_ancestors
    
    def validate_hierarchy(self) -> List[str]:
        """Validate the role hierarchy and return any issues found."""
        issues = []
        
        for role_id, role in self.roles.items():
            # Check for missing parent roles
            for parent_id in role.parent_roles:
                if parent_id not in self.roles:
                    issues.append(f"Role '{role_id}' references missing parent role '{parent_id}'")
            
            # Check for circular dependencies
            for parent_id in role.parent_roles:
                if self.has_circular_dependency(role_id, parent_id):
                    issues.append(f"Circular dependency detected: '{role_id}' -> '{parent_id}'")
        
        return issues
    
    def _invalidate_cache(self) -> None:
        """Invalidate the hierarchy and permission caches."""
        self._hierarchy_cache.clear()
        self._permission_cache.clear()
        self._last_cache_update = time.time()
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        return (time.time() - self._last_cache_update) < self._cache_ttl
    
    def get_role_tree(self, role_id: str) -> Dict[str, Any]:
        """Get a tree representation of a role and its hierarchy."""
        role = self.roles.get(role_id)
        if not role:
            return {}
        
        def _build_tree(current_role_id: str, visited: Set[str]) -> Dict[str, Any]:
            if current_role_id in visited:
                return {"id": current_role_id, "circular": True}
            
            visited.add(current_role_id)
            current_role = self.roles.get(current_role_id)
            
            if not current_role:
                return {"id": current_role_id, "missing": True}
            
            tree = {
                "id": current_role_id,
                "name": current_role.name,
                "permissions": len(current_role.permissions),
                "children": []
            }
            
            for parent_id in current_role.parent_roles:
                child_tree = _build_tree(parent_id, visited.copy())
                tree["children"].append(child_tree)
            
            return tree
        
        return _build_tree(role_id, set())


# =============================================================================
# RBAC Storage Interface
# =============================================================================

class RBACStorage(ABC):
    """Abstract base class for RBAC data storage."""
    
    @abstractmethod
    async def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        pass
    
    @abstractmethod
    async def save_role(self, role: Role) -> None:
        """Save a role."""
        pass
    
    @abstractmethod
    async def delete_role(self, role_id: str) -> None:
        """Delete a role."""
        pass
    
    @abstractmethod
    async def list_roles(self, role_type: Optional[RoleType] = None) -> List[Role]:
        """List all roles, optionally filtered by type."""
        pass
    
    @abstractmethod
    async def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get a permission by ID."""
        pass
    
    @abstractmethod
    async def save_permission(self, permission: Permission) -> None:
        """Save a permission."""
        pass
    
    @abstractmethod
    async def delete_permission(self, permission_id: str) -> None:
        """Delete a permission."""
        pass
    
    @abstractmethod
    async def list_permissions(self, resource: Optional[str] = None) -> List[Permission]:
        """List all permissions, optionally filtered by resource."""
        pass
    
    @abstractmethod
    async def get_user_roles(self, user_id: str) -> List[UserRole]:
        """Get all role assignments for a user."""
        pass
    
    @abstractmethod
    async def assign_role(self, user_role: UserRole) -> None:
        """Assign a role to a user."""
        pass
    
    @abstractmethod
    async def revoke_role(self, user_id: str, role_id: str) -> None:
        """Revoke a role from a user."""
        pass
    
    @abstractmethod
    async def cleanup_expired_roles(self) -> int:
        """Clean up expired role assignments and return count of cleaned up roles."""
        pass


# =============================================================================
# Factory Functions
# =============================================================================

def create_permission(
    resource: str,
    action: Union[str, ActionType],
    effect: PermissionEffect = PermissionEffect.ALLOW,
    conditions: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None
) -> Permission:
    """Create a permission with automatic ID generation."""
    if isinstance(action, str):
        action = ActionType(action)
    
    permission_id = f"{resource}.{action.value}"
    if conditions:
        # Add hash of conditions to make ID unique
        condition_hash = hashlib.md5(str(sorted(conditions.items())).encode()).hexdigest()[:8]
        permission_id += f".{condition_hash}"
    
    return Permission(
        id=permission_id,
        resource=resource,
        action=action,
        effect=effect,
        conditions=conditions,
        description=description or f"{action.value.title()} {resource}"
    )


def create_role(
    name: str,
    permissions: List[str],
    parent_roles: Optional[List[str]] = None,
    role_type: RoleType = RoleType.CUSTOM,
    description: Optional[str] = None
) -> Role:
    """Create a role with automatic ID generation."""
    role_id = name.lower().replace(" ", "_").replace("-", "_")
    
    return Role(
        id=role_id,
        name=name,
        description=description,
        role_type=role_type,
        parent_roles=parent_roles or [],
        permissions=permissions
    )


def create_user_role(
    user_id: str,
    role_id: str,
    granted_by: str,
    expires_in: Optional[timedelta] = None,
    conditions: Optional[Dict[str, Any]] = None
) -> UserRole:
    """Create a user role assignment."""
    expires_at = None
    if expires_in:
        expires_at = datetime.utcnow() + expires_in
    
    return UserRole(
        user_id=user_id,
        role_id=role_id,
        granted_by=granted_by,
        expires_at=expires_at,
        conditions=conditions
    )

# =============================================================================
# In-Memory RBAC Storage Implementation
# =============================================================================

class InMemoryRBACStorage(RBACStorage):
    """In-memory implementation of RBAC storage for development and testing."""
    
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self.user_roles: Dict[str, List[UserRole]] = {}  # user_id -> [UserRole]
        self.logger = get_security_logger()
    
    async def get_role(self, role_id: str) -> Optional[Role]:
        return self.roles.get(role_id)
    
    async def save_role(self, role: Role) -> None:
        self.roles[role.id] = role
        # Log role creation event
        from .logging import SecurityEvent, SecurityEventSeverity
        event = SecurityEvent(
            event_type=SecurityEventType.RBAC_ROLE_CREATED,
            severity=SecurityEventSeverity.LOW,
            source="rbac_storage",
            message=f"Role saved: {role.id}",
            details={"role_id": role.id, "role_name": role.name}
        )
        self.logger.log_event(event)
    
    async def delete_role(self, role_id: str) -> None:
        if role_id in self.roles:
            del self.roles[role_id]
            
            # Remove role assignments
            for user_id, roles in self.user_roles.items():
                self.user_roles[user_id] = [ur for ur in roles if ur.role_id != role_id]
            
            # Log role deletion event
            from .logging import SecurityEvent, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.RBAC_ROLE_DELETED,
                severity=SecurityEventSeverity.MEDIUM,
                source="rbac_storage",
                message=f"Role deleted: {role_id}",
                details={"role_id": role_id}
            )
            self.logger.log_event(event)
    
    async def list_roles(self, role_type: Optional[RoleType] = None) -> List[Role]:
        roles = list(self.roles.values())
        if role_type:
            roles = [r for r in roles if r.role_type == role_type]
        return roles
    
    async def get_permission(self, permission_id: str) -> Optional[Permission]:
        return self.permissions.get(permission_id)
    
    async def save_permission(self, permission: Permission) -> None:
        self.permissions[permission.id] = permission
        # Log permission creation event
        from .logging import SecurityEvent, SecurityEventSeverity
        event = SecurityEvent(
            event_type=SecurityEventType.RBAC_PERMISSION_CREATED,
            severity=SecurityEventSeverity.LOW,
            source="rbac_storage",
            message=f"Permission saved: {permission.id}",
            details={
                "permission_id": permission.id,
                "resource": permission.resource,
                "action": permission.action.value
            }
        )
        self.logger.log_event(event)
    
    async def delete_permission(self, permission_id: str) -> None:
        if permission_id in self.permissions:
            del self.permissions[permission_id]
            
            # Remove permission from roles
            for role in self.roles.values():
                if permission_id in role.permissions:
                    role.remove_permission(permission_id)
            
            # Log permission deletion event
            from .logging import SecurityEvent, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.RBAC_PERMISSION_DELETED,
                severity=SecurityEventSeverity.MEDIUM,
                source="rbac_storage",
                message=f"Permission deleted: {permission_id}",
                details={"permission_id": permission_id}
            )
            self.logger.log_event(event)
    
    async def list_permissions(self, resource: Optional[str] = None) -> List[Permission]:
        permissions = list(self.permissions.values())
        if resource:
            permissions = [p for p in permissions if p.matches_resource(resource)]
        return permissions
    
    async def get_user_roles(self, user_id: str) -> List[UserRole]:
        return self.user_roles.get(user_id, [])
    
    async def assign_role(self, user_role: UserRole) -> None:
        if user_role.user_id not in self.user_roles:
            self.user_roles[user_role.user_id] = []
        
        # Remove existing assignment if it exists
        self.user_roles[user_role.user_id] = [
            ur for ur in self.user_roles[user_role.user_id] 
            if ur.role_id != user_role.role_id
        ]
        
        # Add new assignment
        self.user_roles[user_role.user_id].append(user_role)
        
        # Log role assignment event
        from .logging import SecurityEvent, SecurityEventSeverity
        event = SecurityEvent(
            event_type=SecurityEventType.RBAC_ROLE_ASSIGNED,
            severity=SecurityEventSeverity.LOW,
            source="rbac_storage",
            user_id=user_role.user_id,
            message=f"Role assigned: {user_role.role_id} to {user_role.user_id}",
            details={
                "user_id": user_role.user_id,
                "role_id": user_role.role_id,
                "granted_by": user_role.granted_by
            }
        )
        self.logger.log_event(event)
    
    async def revoke_role(self, user_id: str, role_id: str) -> None:
        if user_id in self.user_roles:
            original_count = len(self.user_roles[user_id])
            self.user_roles[user_id] = [
                ur for ur in self.user_roles[user_id] 
                if ur.role_id != role_id
            ]
            
            if len(self.user_roles[user_id]) < original_count:
                # Log role revocation event
                from .logging import SecurityEvent, SecurityEventSeverity
                event = SecurityEvent(
                    event_type=SecurityEventType.RBAC_ROLE_REVOKED,
                    severity=SecurityEventSeverity.MEDIUM,
                    source="rbac_storage",
                    user_id=user_id,
                    message=f"Role revoked: {role_id} from {user_id}",
                    details={"user_id": user_id, "role_id": role_id}
                )
                self.logger.log_event(event)
    
    async def cleanup_expired_roles(self) -> int:
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        for user_id, roles in self.user_roles.items():
            original_count = len(roles)
            self.user_roles[user_id] = [
                ur for ur in roles 
                if not ur.expires_at or ur.expires_at > current_time
            ]
            cleaned_count += original_count - len(self.user_roles[user_id])
        
        if cleaned_count > 0:
            # Log cleanup event
            from .logging import SecurityEvent, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.RBAC_CLEANUP,
                severity=SecurityEventSeverity.LOW,
                source="rbac_storage",
                message=f"Cleaned up {cleaned_count} expired role assignments",
                details={"cleaned_count": cleaned_count}
            )
            self.logger.log_event(event)
        
        return cleaned_count


# =============================================================================
# Built-in System Roles and Permissions
# =============================================================================

def create_system_permissions() -> List[Permission]:
    """Create standard system permissions."""
    permissions = []
    
    # User management permissions
    for action in [ActionType.CREATE, ActionType.READ, ActionType.UPDATE, ActionType.DELETE, ActionType.LIST]:
        permissions.append(Permission(
            id=f"user.{action.value}",
            resource=ResourceType.USER.value,
            action=action,
            description=f"{action.value.title()} users"
        ))
    
    # Role management permissions
    for action in [ActionType.CREATE, ActionType.READ, ActionType.UPDATE, ActionType.DELETE, ActionType.LIST]:
        permissions.append(Permission(
            id=f"role.{action.value}",
            resource=ResourceType.ROLE.value,
            action=action,
            description=f"{action.value.title()} roles"
        ))
    
    # Permission management permissions
    for action in [ActionType.CREATE, ActionType.READ, ActionType.UPDATE, ActionType.DELETE, ActionType.LIST]:
        permissions.append(Permission(
            id=f"permission.{action.value}",
            resource=ResourceType.PERMISSION.value,
            action=action,
            description=f"{action.value.title()} permissions"
        ))
    
    # System administration permissions
    permissions.extend([
        Permission(
            id="system.admin",
            resource=ResourceType.SYSTEM.value,
            action=ActionType.ADMIN,
            description="Full system administration"
        ),
        Permission(
            id="audit.read",
            resource=ResourceType.AUDIT.value,
            action=ActionType.READ,
            description="Read audit logs"
        ),
        Permission(
            id="config.update",
            resource=ResourceType.CONFIG.value,
            action=ActionType.UPDATE,
            description="Update system configuration"
        )
    ])
    
    return permissions


def create_system_roles() -> List[Role]:
    """Create standard system roles."""
    return [
        Role(
            id="admin",
            name="Administrator",
            description="Full system administrator with all permissions",
            role_type=RoleType.SYSTEM,
            permissions=[
                "system.admin", "user.create", "user.read", "user.update", "user.delete", "user.list",
                "role.create", "role.read", "role.update", "role.delete", "role.list",
                "permission.create", "permission.read", "permission.update", "permission.delete", "permission.list",
                "audit.read", "config.update"
            ],
            priority=1000
        ),
        Role(
            id="user_manager",
            name="User Manager",
            description="Can manage users and their roles",
            role_type=RoleType.SYSTEM,
            permissions=[
                "user.create", "user.read", "user.update", "user.delete", "user.list",
                "role.read", "role.list"
            ],
            priority=500
        ),
        Role(
            id="viewer",
            name="Viewer",
            description="Read-only access to most resources",
            role_type=RoleType.SYSTEM,
            permissions=[
                "user.read", "user.list", "role.read", "role.list", "permission.read", "permission.list"
            ],
            priority=100
        ),
        Role(
            id="service",
            name="Service Account",
            description="Basic permissions for service-to-service communication",
            role_type=RoleType.SERVICE,
            permissions=["user.read", "role.read"],
            priority=200
        )
    ]


# =============================================================================
# RBAC Initialization Helper
# =============================================================================

async def initialize_rbac_system(storage: RBACStorage) -> RoleHierarchy:
    """Initialize RBAC system with default roles and permissions."""
    hierarchy = RoleHierarchy()
    
    # Create system permissions
    system_permissions = create_system_permissions()
    for permission in system_permissions:
        await storage.save_permission(permission)
    
    # Create system roles
    system_roles = create_system_roles()
    for role in system_roles:
        await storage.save_role(role)
        hierarchy.add_role(role)
    
    return hierarchy
# =============================================================================
# RBAC Engine - Main RBAC Orchestrator
# =============================================================================

class RBACEngine:
    """
    Main RBAC Engine for permission checking and role management.
    
    This class orchestrates the RBAC system, providing high-level operations
    for permission checking, role assignment, and user role management.
    It integrates with storage backends and role hierarchy for complete
    access control functionality.
    """
    
    def __init__(
        self,
        storage: RBACStorage,
        hierarchy: Optional[RoleHierarchy] = None,
        cache_ttl: int = 300,
        enable_caching: bool = True
    ):
        """
        Initialize RBAC Engine.
        
        Args:
            storage: RBAC storage backend
            hierarchy: Role hierarchy manager (optional, will be created if None)
            cache_ttl: Cache time-to-live in seconds
            enable_caching: Whether to enable permission caching
        """
        self.storage = storage
        self.hierarchy = hierarchy or RoleHierarchy()
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        self.logger = get_security_logger()
        
        # Permission cache: user_id -> {permission_id: (result, timestamp)}
        self._permission_cache: Dict[str, Dict[str, Tuple[bool, float]]] = {}
        
        # User roles cache: user_id -> (roles, timestamp)
        self._user_roles_cache: Dict[str, Tuple[List[UserRole], float]] = {}
    
    async def initialize(self) -> None:
        """Initialize the RBAC engine by loading roles into hierarchy."""
        try:
            # Load all roles into hierarchy
            roles = await self.storage.list_roles()
            for role in roles:
                self.hierarchy.add_role(role)
            
            # Validate hierarchy
            issues = self.hierarchy.validate_hierarchy()
            if issues:
                self.logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                    severity=SecurityEventSeverity.HIGH,
                    source="rbac_engine",
                    message=f"Role hierarchy validation issues: {issues}",
                    details={"validation_issues": issues}
                ))
            
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_GRANTED,
                severity=SecurityEventSeverity.LOW,
                source="rbac_engine",
                message=f"RBAC Engine initialized with {len(roles)} roles",
                details={"roles_count": len(roles), "hierarchy_issues": len(issues)}
            ))
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.CRITICAL,
                source="rbac_engine",
                message=f"Failed to initialize RBAC Engine: {e}",
                details={"error": str(e)}
            ))
            raise RBACError(f"Failed to initialize RBAC Engine: {e}")
    
    async def check_permission(
        self,
        user_id: str,
        required_permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a user has a specific permission.
        
        Args:
            user_id: User identifier
            required_permission: Permission to check (e.g., "orders.read")
            context: Optional context for conditional permissions
        
        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Check cache first
            if self.enable_caching and self._is_permission_cached(user_id, required_permission):
                cached_result = self._get_cached_permission(user_id, required_permission)
                if cached_result is not None:
                    return cached_result
            
            # Get user roles
            user_roles = await self.get_user_roles(user_id)
            valid_roles = [ur for ur in user_roles if ur.is_valid(context)]
            
            if not valid_roles:
                self._log_permission_check(user_id, required_permission, False, "No valid roles")
                self._cache_permission_result(user_id, required_permission, False)
                return False
            
            # Check permissions through role hierarchy
            has_permission = False
            for user_role in valid_roles:
                role_permissions = self.hierarchy.get_all_permissions(user_role.role_id)
                
                # Check if any permission matches
                for permission_id in role_permissions:
                    permission = await self.storage.get_permission(permission_id)
                    if permission and self._permission_matches(permission, required_permission, context):
                        has_permission = True
                        break
                
                if has_permission:
                    break
            
            # Log and cache result
            self._log_permission_check(user_id, required_permission, has_permission, 
                                     f"Roles: {[ur.role_id for ur in valid_roles]}")
            self._cache_permission_result(user_id, required_permission, has_permission)
            
            return has_permission
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.HIGH,
                source="rbac_engine",
                user_id=user_id,
                message=f"Permission check failed: {e}",
                details={"permission": required_permission, "error": str(e)}
            ))
            # Fail secure - deny access on error
            return False
    
    async def check_permission_by_roles(
        self,
        user_roles: List[str],
        required_permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check permission using a list of role IDs directly.
        
        Args:
            user_roles: List of role IDs
            required_permission: Permission to check
            context: Optional context for conditional permissions
        
        Returns:
            True if any role has the permission, False otherwise
        """
        try:
            for role_id in user_roles:
                role_permissions = self.hierarchy.get_all_permissions(role_id)
                
                for permission_id in role_permissions:
                    permission = await self.storage.get_permission(permission_id)
                    if permission and self._permission_matches(permission, required_permission, context):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.HIGH,
                source="rbac_engine",
                message=f"Role-based permission check failed: {e}",
                details={"roles": user_roles, "permission": required_permission, "error": str(e)}
            ))
            return False
    
    async def get_user_roles(self, user_id: str) -> List[UserRole]:
        """
        Get all valid roles for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of UserRole objects for the user
        """
        try:
            # Check cache first
            if self.enable_caching and self._is_user_roles_cached(user_id):
                cached_roles = self._get_cached_user_roles(user_id)
                if cached_roles is not None:
                    return cached_roles
            
            # Get roles from storage
            user_roles = await self.storage.get_user_roles(user_id)
            
            # Cache and return
            self._cache_user_roles(user_id, user_roles)
            return user_roles
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.MEDIUM,
                source="rbac_engine",
                user_id=user_id,
                message=f"Failed to get user roles: {e}",
                details={"error": str(e)}
            ))
            return []
    
    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        granted_by: str,
        expires_in: Optional[timedelta] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User identifier
            role_id: Role identifier to assign
            granted_by: Who is granting the role
            expires_in: Optional expiration time
            conditions: Optional conditions for the role assignment
        
        Returns:
            True if role was assigned successfully, False otherwise
        """
        try:
            # Verify role exists
            role = await self.storage.get_role(role_id)
            if not role:
                raise RoleError(f"Role not found: {role_id}", role_id=role_id, operation="assign")
            
            # Create user role assignment
            user_role = create_user_role(
                user_id=user_id,
                role_id=role_id,
                granted_by=granted_by,
                expires_in=expires_in,
                conditions=conditions
            )
            
            # Assign role
            await self.storage.assign_role(user_role)
            
            # Invalidate caches
            self._invalidate_user_cache(user_id)
            
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ROLE_ASSIGNED,
                severity=SecurityEventSeverity.LOW,
                source="rbac_engine",
                user_id=user_id,
                message=f"Role assigned: {role_id} to {user_id}",
                details={
                    "role_id": role_id,
                    "granted_by": granted_by,
                    "expires_in": str(expires_in) if expires_in else None,
                    "conditions": conditions
                }
            ))
            
            return True
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.HIGH,
                source="rbac_engine",
                user_id=user_id,
                message=f"Failed to assign role: {e}",
                details={"role_id": role_id, "error": str(e)}
            ))
            return False
    
    async def revoke_role(self, user_id: str, role_id: str) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_id: User identifier
            role_id: Role identifier to revoke
        
        Returns:
            True if role was revoked successfully, False otherwise
        """
        try:
            await self.storage.revoke_role(user_id, role_id)
            
            # Invalidate caches
            self._invalidate_user_cache(user_id)
            
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ROLE_REVOKED,
                severity=SecurityEventSeverity.MEDIUM,
                source="rbac_engine",
                user_id=user_id,
                message=f"Role revoked: {role_id} from {user_id}",
                details={"role_id": role_id}
            ))
            
            return True
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.HIGH,
                source="rbac_engine",
                user_id=user_id,
                message=f"Failed to revoke role: {e}",
                details={"role_id": role_id, "error": str(e)}
            ))
            return False
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """
        Get all permissions for a user (aggregated from all roles).
        
        Args:
            user_id: User identifier
        
        Returns:
            Set of permission IDs the user has
        """
        try:
            user_roles = await self.get_user_roles(user_id)
            valid_roles = [ur for ur in user_roles if ur.is_valid()]
            
            all_permissions = set()
            for user_role in valid_roles:
                role_permissions = self.hierarchy.get_all_permissions(user_role.role_id)
                all_permissions.update(role_permissions)
            
            return all_permissions
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.MEDIUM,
                source="rbac_engine",
                user_id=user_id,
                message=f"Failed to get user permissions: {e}",
                details={"error": str(e)}
            ))
            return set()
    
    async def cleanup_expired_roles(self) -> int:
        """
        Clean up expired role assignments.
        
        Returns:
            Number of expired roles cleaned up
        """
        try:
            cleaned_count = await self.storage.cleanup_expired_roles()
            
            # Clear all caches since roles may have changed
            self._clear_all_caches()
            
            if cleaned_count > 0:
                self.logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.RBAC_CLEANUP,
                    severity=SecurityEventSeverity.LOW,
                    source="rbac_engine",
                    message=f"Cleaned up {cleaned_count} expired role assignments",
                    details={"cleaned_count": cleaned_count}
                ))
            
            return cleaned_count
            
        except Exception as e:
            self.logger.log_event(SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_DENIED,
                severity=SecurityEventSeverity.HIGH,
                source="rbac_engine",
                message=f"Failed to cleanup expired roles: {e}",
                details={"error": str(e)}
            ))
            return 0
    
    def _permission_matches(
        self,
        permission: Permission,
        required_permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if a permission matches the required permission."""
        # Parse required permission (e.g., "orders.read" -> resource="orders", action="read")
        if "." not in required_permission:
            return False
        
        resource, action = required_permission.split(".", 1)
        
        # Check resource and action match
        if not permission.matches_resource(resource):
            return False
        
        if permission.action.value != action:
            return False
        
        # Check effect (deny overrides allow)
        if permission.effect == PermissionEffect.DENY:
            return False
        
        # Check conditions if present
        if permission.conditions and context:
            return permission.evaluate_conditions(context)
        
        return True
    
    def _log_permission_check(
        self,
        user_id: str,
        permission: str,
        granted: bool,
        details: str
    ) -> None:
        """Log permission check result."""
        event_type = SecurityEventType.RBAC_ACCESS_GRANTED if granted else SecurityEventType.RBAC_ACCESS_DENIED
        severity = SecurityEventSeverity.LOW if granted else SecurityEventSeverity.MEDIUM
        
        self.logger.log_event(SecurityEvent(
            event_type=event_type,
            severity=severity,
            source="rbac_engine",
            user_id=user_id,
            message=f"Permission check: {permission} -> {'GRANTED' if granted else 'DENIED'}",
            details={"permission": permission, "result": granted, "details": details}
        ))
    
    # Cache management methods
    def _is_permission_cached(self, user_id: str, permission: str) -> bool:
        """Check if permission result is cached and valid."""
        if user_id not in self._permission_cache:
            return False
        
        if permission not in self._permission_cache[user_id]:
            return False
        
        _, timestamp = self._permission_cache[user_id][permission]
        return (time.time() - timestamp) < self.cache_ttl
    
    def _get_cached_permission(self, user_id: str, permission: str) -> Optional[bool]:
        """Get cached permission result."""
        if not self._is_permission_cached(user_id, permission):
            return None
        
        result, _ = self._permission_cache[user_id][permission]
        return result
    
    def _cache_permission_result(self, user_id: str, permission: str, result: bool) -> None:
        """Cache permission check result."""
        if not self.enable_caching:
            return
        
        if user_id not in self._permission_cache:
            self._permission_cache[user_id] = {}
        
        self._permission_cache[user_id][permission] = (result, time.time())
    
    def _is_user_roles_cached(self, user_id: str) -> bool:
        """Check if user roles are cached and valid."""
        if user_id not in self._user_roles_cache:
            return False
        
        _, timestamp = self._user_roles_cache[user_id]
        return (time.time() - timestamp) < self.cache_ttl
    
    def _get_cached_user_roles(self, user_id: str) -> Optional[List[UserRole]]:
        """Get cached user roles."""
        if not self._is_user_roles_cached(user_id):
            return None
        
        roles, _ = self._user_roles_cache[user_id]
        return roles
    
    def _cache_user_roles(self, user_id: str, roles: List[UserRole]) -> None:
        """Cache user roles."""
        if not self.enable_caching:
            return
        
        self._user_roles_cache[user_id] = (roles, time.time())
    
    def _invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cache entries for a user."""
        if user_id in self._permission_cache:
            del self._permission_cache[user_id]
        
        if user_id in self._user_roles_cache:
            del self._user_roles_cache[user_id]
    
    def _clear_all_caches(self) -> None:
        """Clear all caches."""
        self._permission_cache.clear()
        self._user_roles_cache.clear()


# =============================================================================
# RBAC Engine Factory and Convenience Functions
# =============================================================================

async def create_rbac_engine(
    storage: Optional[RBACStorage] = None,
    initialize_system_roles: bool = True,
    cache_ttl: int = 300
) -> RBACEngine:
    """
    Create and initialize an RBAC engine.
    
    Args:
        storage: RBAC storage backend (uses InMemoryRBACStorage if None)
        initialize_system_roles: Whether to create system roles and permissions
        cache_ttl: Cache time-to-live in seconds
    
    Returns:
        Initialized RBACEngine instance
    """
    if storage is None:
        storage = InMemoryRBACStorage()
    
    # Initialize system roles and permissions if requested
    if initialize_system_roles:
        hierarchy = await initialize_rbac_system(storage)
    else:
        hierarchy = RoleHierarchy()
    
    # Create and initialize engine
    engine = RBACEngine(storage=storage, hierarchy=hierarchy, cache_ttl=cache_ttl)
    await engine.initialize()
    
    return engine


def require_permission(permission: str):
    """
    Decorator factory for requiring specific permissions on functions.
    
    Args:
        permission: Required permission (e.g., "orders.read")
    
    Returns:
        Decorator function
    """
    def decorator(func):
        func._required_permission = permission
        return func
    return decorator


def require_role(role: str):
    """
    Decorator factory for requiring specific roles on functions.
    
    Args:
        role: Required role (e.g., "admin")
    
    Returns:
        Decorator function
    """
    def decorator(func):
        func._required_role = role
        return func
    return decorator


# =============================================================================
# RBAC FastAPI Middleware and Dependencies
# =============================================================================

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request, Response
    from fastapi.security import HTTPBearer
    from starlette.middleware.base import BaseHTTPMiddleware


class RBACMiddleware:
    """
    FastAPI middleware for automatic RBAC enforcement.
    
    This middleware automatically checks permissions for protected endpoints
    based on configured RBAC policies and user roles.
    """
    
    def __init__(
        self,
        rbac_engine: RBACEngine,
        exclude_paths: Optional[List[str]] = None,
        require_authentication: bool = True,
        default_deny: bool = True
    ):
        """
        Initialize RBAC middleware.
        
        Args:
            rbac_engine: RBAC engine instance
            exclude_paths: Paths to exclude from RBAC checking
            require_authentication: Whether to require authentication
            default_deny: Whether to deny access by default if no permissions defined
        """
        self.rbac_engine = rbac_engine
        self.exclude_paths = exclude_paths or []
        self.require_authentication = require_authentication
        self.default_deny = default_deny
        self.logger = get_security_logger()
        
        # Add common paths to exclude by default
        self.exclude_paths.extend([
            "/docs", "/redoc", "/openapi.json", "/health", "/metrics"
        ])
    
    async def __call__(self, request: "Request", call_next):
        """
        Process request through RBAC middleware.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in chain
            
        Returns:
            Response object
        """
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Extract user information from request
            user_info = await self._extract_user_info(request)
            
            if not user_info and self.require_authentication:
                return self._create_auth_required_response()
            
            # Check if endpoint has RBAC requirements
            endpoint_permissions = self._get_endpoint_permissions(request)
            
            if not endpoint_permissions:
                if self.default_deny:
                    return self._create_access_denied_response(
                        "No permissions defined for this endpoint"
                    )
                else:
                    # Allow access if no permissions defined and default_deny is False
                    return await call_next(request)
            
            # Check permissions for each required permission
            user_id = user_info.get("user_id") if user_info else None
            
            for permission in endpoint_permissions:
                has_permission = await self.rbac_engine.check_permission(
                    user_id=user_id,
                    required_permission=permission,
                    context=self._extract_context(request)
                )
                
                if not has_permission:
                    return self._create_access_denied_response(
                        f"Permission denied: {permission} required"
                    )
            
            # Store user info in request state for use by endpoints
            request.state.user = user_info
            request.state.rbac_context = self._extract_context(request)
            
            # Log successful access
            from .logging import SecurityEvent, SecurityEventType, SecurityEventSeverity
            event = SecurityEvent(
                event_type=SecurityEventType.RBAC_ACCESS_GRANTED,
                severity=SecurityEventSeverity.LOW,
                source="rbac_middleware",
                user_id=user_id,
                message=f"Access granted to {request.url.path}",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "permissions": endpoint_permissions
                }
            )
            self.logger.log_event(event)
            
            return await call_next(request)
            
        except Exception as e:
            # Log error and deny access
            self.logger.log_security_violation(
                violation_type="rbac_middleware_error",
                description=f"RBAC middleware error: {str(e)}",
                severity="high",
                user_id=user_info.get("user_id") if user_info else None
            )
            return self._create_error_response(str(e))
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from RBAC checking."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    async def _extract_user_info(self, request: "Request") -> Optional[Dict[str, Any]]:
        """
        Extract user information from request.
        
        This method looks for user info in various places:
        1. Request state (set by authentication middleware)
        2. JWT token in Authorization header
        3. Session data
        """
        # Check if user info is already in request state
        if hasattr(request.state, "user") and request.state.user:
            return request.state.user
        
        # Try to extract from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                # This would typically decode JWT token
                # For now, we'll return a placeholder
                return {"user_id": "extracted_from_token"}
            except Exception:
                pass
        
        return None
    
    def _get_endpoint_permissions(self, request: "Request") -> List[str]:
        """
        Get required permissions for the current endpoint.
        
        This method checks for permissions defined in:
        1. Route metadata
        2. Endpoint function annotations
        3. Path-based configuration
        """
        permissions = []
        
        # Check if route has permission metadata
        if hasattr(request, "route") and hasattr(request.route, "endpoint"):
            endpoint = request.route.endpoint
            
            # Check for permission decorators or metadata
            if hasattr(endpoint, "__rbac_permissions__"):
                permissions.extend(endpoint.__rbac_permissions__)
            
            if hasattr(endpoint, "__rbac_roles__"):
                # Convert roles to permissions (simplified)
                for role in endpoint.__rbac_roles__:
                    permissions.append(f"role:{role}")
        
        return permissions
    
    def _extract_context(self, request: "Request") -> Dict[str, Any]:
        """Extract context information for ABAC evaluation."""
        return {
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "path": request.url.path,
            "method": request.method,
            "timestamp": datetime.utcnow().isoformat(),
            "headers": dict(request.headers)
        }
    
    def _create_auth_required_response(self):
        """Create authentication required response."""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _create_access_denied_response(self, message: str):
        """Create access denied response."""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail=message
        )
    
    def _create_error_response(self, message: str):
        """Create error response."""
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Internal security error: {message}"
        )


# =============================================================================
# FastAPI Dependencies for RBAC
# =============================================================================

def create_rbac_dependency(
    rbac_engine: RBACEngine,
    required_permission: str,
    context_extractor: Optional[Callable] = None
):
    """
    Create a FastAPI dependency for RBAC permission checking.
    
    Args:
        rbac_engine: RBAC engine instance
        required_permission: Permission required to access the endpoint
        context_extractor: Optional function to extract additional context
        
    Returns:
        FastAPI dependency function
    """
    async def rbac_dependency(request: "Request") -> bool:
        """FastAPI dependency that checks RBAC permissions."""
        # Get user info from request state (set by middleware or auth)
        user_info = getattr(request.state, "user", None)
        
        if not user_info:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        user_id = user_info.get("user_id")
        if not user_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Invalid user information"
            )
        
        # Extract context
        context = {}
        if context_extractor:
            context.update(context_extractor(request))
        
        # Add default context
        context.update({
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent"),
            "path": request.url.path,
            "method": request.method
        })
        
        # Check permission
        has_permission = await rbac_engine.check_permission(
            user_id=user_id,
            required_permission=required_permission,
            context=context
        )
        
        if not has_permission:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {required_permission} required"
            )
        
        return True
    
    return rbac_dependency


def create_role_dependency(
    rbac_engine: RBACEngine,
    required_roles: Union[str, List[str]],
    require_all: bool = False
):
    """
    Create a FastAPI dependency for role-based access control.
    
    Args:
        rbac_engine: RBAC engine instance
        required_roles: Role(s) required to access the endpoint
        require_all: Whether all roles are required (AND) or any role (OR)
        
    Returns:
        FastAPI dependency function
    """
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    async def role_dependency(request: "Request") -> bool:
        """FastAPI dependency that checks user roles."""
        # Get user info from request state
        user_info = getattr(request.state, "user", None)
        
        if not user_info:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Authentication required"
            )
        
        user_id = user_info.get("user_id")
        if not user_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=401,
                detail="Invalid user information"
            )
        
        # Get user roles
        user_roles = await rbac_engine.get_user_roles(user_id)
        user_role_ids = [ur.role_id for ur in user_roles if ur.is_valid()]
        
        # Check role requirements
        if require_all:
            # User must have ALL required roles
            missing_roles = set(required_roles) - set(user_role_ids)
            if missing_roles:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required roles: {', '.join(missing_roles)}"
                )
        else:
            # User must have ANY of the required roles
            if not any(role in user_role_ids for role in required_roles):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail=f"One of these roles required: {', '.join(required_roles)}"
                )
        
        return True
    
    return role_dependency


# =============================================================================
# RBAC Decorators for Enhanced Integration
# =============================================================================

def rbac_protected(
    permission: Optional[str] = None,
    roles: Optional[Union[str, List[str]]] = None,
    require_all_roles: bool = False
):
    """
    Decorator to mark endpoints as RBAC protected.
    
    This decorator adds metadata to endpoint functions that can be
    used by the RBACMiddleware for automatic protection.
    
    Args:
        permission: Required permission for the endpoint
        roles: Required role(s) for the endpoint
        require_all_roles: Whether all roles are required
    """
    def decorator(func):
        # Add RBAC metadata to function
        if permission:
            if not hasattr(func, "__rbac_permissions__"):
                func.__rbac_permissions__ = []
            func.__rbac_permissions__.append(permission)
        
        if roles:
            if not hasattr(func, "__rbac_roles__"):
                func.__rbac_roles__ = []
            
            if isinstance(roles, str):
                func.__rbac_roles__.append(roles)
            else:
                func.__rbac_roles__.extend(roles)
            
            func.__rbac_require_all_roles__ = require_all_roles
        
        return func
    
    return decorator


# =============================================================================
# RBAC Integration Helpers
# =============================================================================

def setup_rbac_app(
    app,  # FastAPI app
    rbac_engine: RBACEngine,
    enable_middleware: bool = True,
    middleware_config: Optional[Dict[str, Any]] = None
):
    """
    Set up RBAC integration for a FastAPI application.
    
    Args:
        app: FastAPI application instance
        rbac_engine: RBAC engine instance
        enable_middleware: Whether to enable RBAC middleware
        middleware_config: Configuration for RBAC middleware
    """
    if enable_middleware:
        config = middleware_config or {}
        middleware = RBACMiddleware(rbac_engine, **config)
        
        # Add middleware to app
        from starlette.middleware.base import BaseHTTPMiddleware
        
        class RBACHTTPMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, rbac_middleware: RBACMiddleware):
                super().__init__(app)
                self.rbac_middleware = rbac_middleware
            
            async def dispatch(self, request, call_next):
                return await self.rbac_middleware(request, call_next)
        
        app.add_middleware(RBACHTTPMiddleware, rbac_middleware=middleware)
    
    # Store RBAC engine in app state for use by dependencies
    app.state.rbac_engine = rbac_engine
    
    return app


def get_rbac_engine(request: "Request") -> RBACEngine:
    """
    Get RBAC engine from FastAPI app state.
    
    This is a FastAPI dependency that can be used to inject
    the RBAC engine into endpoint functions.
    """
    if not hasattr(request.app.state, "rbac_engine"):
        raise RuntimeError("RBAC engine not configured in app state")
    
    return request.app.state.rbac_engine


def get_current_user(request: "Request") -> Dict[str, Any]:
    """
    Get current user information from request state.
    
    This is a FastAPI dependency that can be used to inject
    current user information into endpoint functions.
    """
    user_info = getattr(request.state, "user", None)
    
    if not user_info:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return user_info


# =============================================================================
# Aliases for backward compatibility and convenience
# =============================================================================

# RBACManager is an alias for RBACEngine for better naming consistency
RBACManager = RBACEngine
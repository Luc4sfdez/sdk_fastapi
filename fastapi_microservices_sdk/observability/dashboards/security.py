"""
Dashboard Security - Access control and permissions for dashboards

This module provides security and access control functionality for dashboards
including role-based permissions and user authentication.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from datetime import datetime

from .exceptions import DashboardPermissionError

logger = logging.getLogger(__name__)


class DashboardPermission(Enum):
    """Dashboard permission types."""
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    SHARE = "share"
    EXPORT = "export"
    ADMIN = "admin"


class DashboardSecurity:
    """
    Dashboard security manager for access control and permissions.
    
    Provides functionality for:
    - User authentication and authorization
    - Role-based access control
    - Dashboard permissions management
    - Security auditing
    """
    
    def __init__(self):
        self.user_permissions: Dict[str, Dict[str, Set[DashboardPermission]]] = {}
        self.role_permissions: Dict[str, Set[DashboardPermission]] = {}
        self.user_roles: Dict[str, Set[str]] = {}
        self.dashboard_acl: Dict[str, Dict[str, Set[DashboardPermission]]] = {}
        self.is_initialized = False
        
        logger.info("Dashboard security manager initialized")
    
    async def initialize(self) -> None:
        """Initialize security manager."""
        if self.is_initialized:
            return
        
        try:
            # Initialize default roles
            await self._initialize_default_roles()
            
            self.is_initialized = True
            logger.info("Dashboard security manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard security: {e}")
            raise DashboardPermissionError(f"Security initialization failed: {e}")
    
    async def can_view_dashboard(self, user: str, dashboard: Any) -> bool:
        """
        Check if user can view dashboard.
        
        Args:
            user: User identifier
            dashboard: Dashboard object
            
        Returns:
            True if user can view dashboard
        """
        return await self._check_permission(user, dashboard.id, DashboardPermission.VIEW) or \
               dashboard.is_public or \
               dashboard.owner == user or \
               user in dashboard.shared_with
    
    async def can_edit_dashboard(self, user: str, dashboard: Any) -> bool:
        """
        Check if user can edit dashboard.
        
        Args:
            user: User identifier
            dashboard: Dashboard object
            
        Returns:
            True if user can edit dashboard
        """
        return await self._check_permission(user, dashboard.id, DashboardPermission.EDIT) or \
               dashboard.owner == user
    
    async def can_delete_dashboard(self, user: str, dashboard: Any) -> bool:
        """
        Check if user can delete dashboard.
        
        Args:
            user: User identifier
            dashboard: Dashboard object
            
        Returns:
            True if user can delete dashboard
        """
        return await self._check_permission(user, dashboard.id, DashboardPermission.DELETE) or \
               dashboard.owner == user
    
    async def can_share_dashboard(self, user: str, dashboard: Any) -> bool:
        """
        Check if user can share dashboard.
        
        Args:
            user: User identifier
            dashboard: Dashboard object
            
        Returns:
            True if user can share dashboard
        """
        return await self._check_permission(user, dashboard.id, DashboardPermission.SHARE) or \
               dashboard.owner == user
    
    async def can_export_dashboard(self, user: str, dashboard: Any) -> bool:
        """
        Check if user can export dashboard.
        
        Args:
            user: User identifier
            dashboard: Dashboard object
            
        Returns:
            True if user can export dashboard
        """
        return await self._check_permission(user, dashboard.id, DashboardPermission.EXPORT) or \
               await self.can_view_dashboard(user, dashboard)
    
    async def grant_dashboard_permissions(
        self,
        user: str,
        dashboard_id: str,
        permissions: List[str]
    ) -> None:
        """
        Grant dashboard permissions to user.
        
        Args:
            user: User identifier
            dashboard_id: Dashboard ID
            permissions: List of permissions to grant
        """
        if user not in self.user_permissions:
            self.user_permissions[user] = {}
        
        if dashboard_id not in self.user_permissions[user]:
            self.user_permissions[user][dashboard_id] = set()
        
        for permission in permissions:
            try:
                perm = DashboardPermission(permission)
                self.user_permissions[user][dashboard_id].add(perm)
            except ValueError:
                logger.warning(f"Invalid permission: {permission}")
        
        logger.info(f"Granted permissions {permissions} to user {user} for dashboard {dashboard_id}")
    
    async def revoke_dashboard_permissions(
        self,
        user: str,
        dashboard_id: str,
        permissions: List[str]
    ) -> None:
        """
        Revoke dashboard permissions from user.
        
        Args:
            user: User identifier
            dashboard_id: Dashboard ID
            permissions: List of permissions to revoke
        """
        if user not in self.user_permissions or dashboard_id not in self.user_permissions[user]:
            return
        
        for permission in permissions:
            try:
                perm = DashboardPermission(permission)
                self.user_permissions[user][dashboard_id].discard(perm)
            except ValueError:
                logger.warning(f"Invalid permission: {permission}")
        
        # Clean up empty permission sets
        if not self.user_permissions[user][dashboard_id]:
            del self.user_permissions[user][dashboard_id]
        
        if not self.user_permissions[user]:
            del self.user_permissions[user]
        
        logger.info(f"Revoked permissions {permissions} from user {user} for dashboard {dashboard_id}")
    
    async def assign_role(self, user: str, role: str) -> None:
        """
        Assign role to user.
        
        Args:
            user: User identifier
            role: Role name
        """
        if role not in self.role_permissions:
            raise DashboardPermissionError(f"Unknown role: {role}")
        
        if user not in self.user_roles:
            self.user_roles[user] = set()
        
        self.user_roles[user].add(role)
        logger.info(f"Assigned role {role} to user {user}")
    
    async def remove_role(self, user: str, role: str) -> None:
        """
        Remove role from user.
        
        Args:
            user: User identifier
            role: Role name
        """
        if user in self.user_roles:
            self.user_roles[user].discard(role)
            
            # Clean up empty role sets
            if not self.user_roles[user]:
                del self.user_roles[user]
        
        logger.info(f"Removed role {role} from user {user}")
    
    async def create_role(
        self,
        role: str,
        permissions: List[DashboardPermission]
    ) -> None:
        """
        Create new role with permissions.
        
        Args:
            role: Role name
            permissions: List of permissions for the role
        """
        self.role_permissions[role] = set(permissions)
        logger.info(f"Created role {role} with permissions {[p.value for p in permissions]}")
    
    async def get_user_permissions(
        self,
        user: str,
        dashboard_id: Optional[str] = None
    ) -> Dict[str, Set[DashboardPermission]]:
        """
        Get user permissions.
        
        Args:
            user: User identifier
            dashboard_id: Optional dashboard ID filter
            
        Returns:
            Dictionary of dashboard permissions
        """
        permissions = {}
        
        # Direct user permissions
        if user in self.user_permissions:
            if dashboard_id:
                if dashboard_id in self.user_permissions[user]:
                    permissions[dashboard_id] = self.user_permissions[user][dashboard_id].copy()
            else:
                permissions.update({
                    did: perms.copy() 
                    for did, perms in self.user_permissions[user].items()
                })
        
        # Role-based permissions
        if user in self.user_roles:
            for role in self.user_roles[user]:
                if role in self.role_permissions:
                    role_perms = self.role_permissions[role]
                    
                    if dashboard_id:
                        if dashboard_id not in permissions:
                            permissions[dashboard_id] = set()
                        permissions[dashboard_id].update(role_perms)
                    else:
                        # Apply role permissions to all dashboards user has access to
                        for did in permissions:
                            permissions[did].update(role_perms)
        
        return permissions
    
    async def get_user_roles(self, user: str) -> Set[str]:
        """
        Get user roles.
        
        Args:
            user: User identifier
            
        Returns:
            Set of role names
        """
        return self.user_roles.get(user, set()).copy()
    
    async def get_available_roles(self) -> Dict[str, Set[DashboardPermission]]:
        """
        Get available roles and their permissions.
        
        Returns:
            Dictionary of roles and permissions
        """
        return {role: perms.copy() for role, perms in self.role_permissions.items()}
    
    async def audit_user_access(
        self,
        user: str,
        dashboard_id: str,
        action: str,
        success: bool
    ) -> None:
        """
        Audit user access attempt.
        
        Args:
            user: User identifier
            dashboard_id: Dashboard ID
            action: Action attempted
            success: Whether action was successful
        """
        # In real implementation, this would log to audit system
        log_level = logging.INFO if success else logging.WARNING
        logger.log(
            log_level,
            f"User {user} attempted {action} on dashboard {dashboard_id}: {'SUCCESS' if success else 'DENIED'}"
        )
    
    async def _check_permission(
        self,
        user: str,
        dashboard_id: str,
        permission: DashboardPermission
    ) -> bool:
        """Check if user has specific permission for dashboard."""
        # Check direct user permissions
        if user in self.user_permissions:
            if dashboard_id in self.user_permissions[user]:
                if permission in self.user_permissions[user][dashboard_id]:
                    return True
        
        # Check role-based permissions
        if user in self.user_roles:
            for role in self.user_roles[user]:
                if role in self.role_permissions:
                    if permission in self.role_permissions[role]:
                        return True
        
        return False
    
    async def _initialize_default_roles(self) -> None:
        """Initialize default roles."""
        # Viewer role - can only view dashboards
        await self.create_role("viewer", [
            DashboardPermission.VIEW,
            DashboardPermission.EXPORT
        ])
        
        # Editor role - can view and edit dashboards
        await self.create_role("editor", [
            DashboardPermission.VIEW,
            DashboardPermission.EDIT,
            DashboardPermission.EXPORT
        ])
        
        # Admin role - full permissions
        await self.create_role("admin", [
            DashboardPermission.VIEW,
            DashboardPermission.EDIT,
            DashboardPermission.DELETE,
            DashboardPermission.SHARE,
            DashboardPermission.EXPORT,
            DashboardPermission.ADMIN
        ])
        
        logger.debug("Initialized default roles: viewer, editor, admin")
    
    def get_status(self) -> Dict[str, Any]:
        """Get security manager status."""
        return {
            "initialized": self.is_initialized,
            "total_users": len(self.user_permissions),
            "total_roles": len(self.role_permissions),
            "users_with_roles": len(self.user_roles),
            "available_roles": list(self.role_permissions.keys()),
            "available_permissions": [p.value for p in DashboardPermission]
        }
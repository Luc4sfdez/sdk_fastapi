#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBAC (Role-Based Access Control) System Example

This example demonstrates how to use the RBAC system in the FastAPI Microservices SDK.
It shows:
- Creating permissions and roles
- Setting up role hierarchy
- Assigning roles to users
- Checking permissions
- Managing role inheritance

Author: FastAPI Microservices SDK Team
Version: 1.0.0
Date: 2025-09-02
"""

import asyncio
from datetime import timedelta
from fastapi_microservices_sdk.security.advanced.rbac import (
    Permission, Role, UserRole, RoleHierarchy,
    ActionType, ResourceType, RoleType,
    InMemoryRBACStorage,
    create_permission, create_role, create_user_role,
    create_system_permissions, create_system_roles,
    initialize_rbac_system
)


async def main():
    """Main example function demonstrating RBAC usage."""
    print("🔐 FastAPI Microservices SDK - RBAC System Example")
    print("=" * 60)
    
    # Initialize storage and RBAC system
    print("\n1. Initializing RBAC System...")
    storage = InMemoryRBACStorage()
    hierarchy = await initialize_rbac_system(storage)
    
    print(f"   ✅ Created {len(hierarchy.roles)} system roles")
    print(f"   ✅ Created {len(await storage.list_permissions())} system permissions")
    
    # Create custom permissions
    print("\n2. Creating Custom Permissions...")
    custom_permissions = [
        create_permission("orders", ActionType.CREATE, description="Create new orders"),
        create_permission("orders", ActionType.READ, description="View orders"),
        create_permission("orders", ActionType.UPDATE, description="Modify orders"),
        create_permission("orders", ActionType.DELETE, description="Delete orders"),
        create_permission("products", ActionType.READ, description="View products"),
        create_permission("products", ActionType.UPDATE, description="Modify products"),
        create_permission("reports", ActionType.READ, description="View reports"),
        create_permission("analytics", ActionType.READ, description="View analytics"),
    ]
    
    for permission in custom_permissions:
        await storage.save_permission(permission)
        print(f"   ✅ Created permission: {permission.id}")
    
    # Create custom roles with hierarchy
    print("\n3. Creating Custom Role Hierarchy...")
    
    # Base role - Customer Service Representative
    csr_role = create_role(
        name="Customer Service Representative",
        permissions=["orders.read", "products.read"],
        description="Can view orders and products"
    )
    await storage.save_role(csr_role)
    hierarchy.add_role(csr_role)
    print(f"   ✅ Created role: {csr_role.name}")
    
    # Mid-level role - Order Manager (inherits from CSR)
    order_manager_role = create_role(
        name="Order Manager",
        permissions=["orders.create", "orders.update", "orders.delete"],
        parent_roles=[csr_role.id],  # Inherits CSR permissions
        description="Can manage orders, inherits CSR permissions"
    )
    await storage.save_role(order_manager_role)
    hierarchy.add_role(order_manager_role)
    print(f"   ✅ Created role: {order_manager_role.name}")
    
    # High-level role - Department Manager (inherits from Order Manager)
    dept_manager_role = create_role(
        name="Department Manager",
        permissions=["products.update", "reports.read"],
        parent_roles=[order_manager_role.id],  # Inherits Order Manager permissions
        description="Can manage products and view reports"
    )
    await storage.save_role(dept_manager_role)
    hierarchy.add_role(dept_manager_role)
    print(f"   ✅ Created role: {dept_manager_role.name}")
    
    # Executive role - Analytics Manager
    analytics_manager_role = create_role(
        name="Analytics Manager",
        permissions=["analytics.read", "reports.read"],
        parent_roles=["viewer"],  # Inherits from system viewer role
        description="Can view analytics and reports"
    )
    await storage.save_role(analytics_manager_role)
    hierarchy.add_role(analytics_manager_role)
    print(f"   ✅ Created role: {analytics_manager_role.name}")
    
    # Assign roles to users
    print("\n4. Assigning Roles to Users...")
    
    # Assign CSR role to Alice
    alice_csr = create_user_role(
        user_id="alice",
        role_id=csr_role.id,
        granted_by="system_admin"
    )
    await storage.assign_role(alice_csr)
    print(f"   ✅ Assigned '{csr_role.name}' to Alice")
    
    # Assign Order Manager role to Bob
    bob_manager = create_user_role(
        user_id="bob",
        role_id=order_manager_role.id,
        granted_by="system_admin"
    )
    await storage.assign_role(bob_manager)
    print(f"   ✅ Assigned '{order_manager_role.name}' to Bob")
    
    # Assign Department Manager role to Carol
    carol_dept_manager = create_user_role(
        user_id="carol",
        role_id=dept_manager_role.id,
        granted_by="system_admin"
    )
    await storage.assign_role(carol_dept_manager)
    print(f"   ✅ Assigned '{dept_manager_role.name}' to Carol")
    
    # Assign temporary Analytics Manager role to David (expires in 24 hours)
    david_analytics = create_user_role(
        user_id="david",
        role_id=analytics_manager_role.id,
        granted_by="system_admin",
        expires_in=timedelta(hours=24)
    )
    await storage.assign_role(david_analytics)
    print(f"   ✅ Assigned '{analytics_manager_role.name}' to David (expires in 24h)")
    
    # Demonstrate permission checking
    print("\n5. Checking User Permissions...")
    
    async def check_user_permission(user_id: str, permission_id: str):
        """Check if a user has a specific permission through their roles."""
        user_roles = await storage.get_user_roles(user_id)
        valid_roles = [ur for ur in user_roles if ur.is_valid()]
        
        all_permissions = set()
        for user_role in valid_roles:
            role_permissions = hierarchy.get_all_permissions(user_role.role_id)
            all_permissions.update(role_permissions)
        
        has_permission = permission_id in all_permissions
        status = "✅ ALLOWED" if has_permission else "❌ DENIED"
        print(f"   {status} {user_id} -> {permission_id}")
        return has_permission
    
    # Test Alice (CSR) - should only have read permissions
    print(f"\n   Testing Alice ({csr_role.name}):")
    await check_user_permission("alice", "orders.read")      # ✅ Direct permission
    await check_user_permission("alice", "products.read")    # ✅ Direct permission
    await check_user_permission("alice", "orders.create")    # ❌ No permission
    await check_user_permission("alice", "reports.read")     # ❌ No permission
    
    # Test Bob (Order Manager) - should have CSR permissions + order management
    print(f"\n   Testing Bob ({order_manager_role.name}):")
    await check_user_permission("bob", "orders.read")        # ✅ Inherited from CSR
    await check_user_permission("bob", "products.read")      # ✅ Inherited from CSR
    await check_user_permission("bob", "orders.create")      # ✅ Direct permission
    await check_user_permission("bob", "orders.update")      # ✅ Direct permission
    await check_user_permission("bob", "orders.delete")      # ✅ Direct permission
    await check_user_permission("bob", "products.update")    # ❌ No permission
    await check_user_permission("bob", "reports.read")       # ❌ No permission
    
    # Test Carol (Department Manager) - should have all lower-level permissions + more
    print(f"\n   Testing Carol ({dept_manager_role.name}):")
    await check_user_permission("carol", "orders.read")      # ✅ Inherited from CSR
    await check_user_permission("carol", "products.read")    # ✅ Inherited from CSR
    await check_user_permission("carol", "orders.create")    # ✅ Inherited from Order Manager
    await check_user_permission("carol", "orders.update")    # ✅ Inherited from Order Manager
    await check_user_permission("carol", "orders.delete")    # ✅ Inherited from Order Manager
    await check_user_permission("carol", "products.update")  # ✅ Direct permission
    await check_user_permission("carol", "reports.read")     # ✅ Direct permission
    await check_user_permission("carol", "analytics.read")   # ❌ No permission
    
    # Test David (Analytics Manager) - should have viewer permissions + analytics
    print(f"\n   Testing David ({analytics_manager_role.name}):")
    await check_user_permission("david", "user.read")        # ✅ Inherited from viewer
    await check_user_permission("david", "role.read")        # ✅ Inherited from viewer
    await check_user_permission("david", "analytics.read")   # ✅ Direct permission
    await check_user_permission("david", "reports.read")     # ✅ Direct permission
    await check_user_permission("david", "orders.create")    # ❌ No permission
    
    # Demonstrate role hierarchy visualization
    print("\n6. Role Hierarchy Visualization...")
    
    def print_role_tree(tree, indent=0):
        """Recursively print role hierarchy tree."""
        prefix = "  " * indent
        if tree.get("circular"):
            print(f"{prefix}🔄 {tree['id']} (CIRCULAR REFERENCE)")
        elif tree.get("missing"):
            print(f"{prefix}❓ {tree['id']} (MISSING ROLE)")
        else:
            name = tree.get("name", tree["id"])
            permissions_count = tree.get("permissions", 0)
            print(f"{prefix}📋 {name} ({permissions_count} direct permissions)")
            
            for child in tree.get("children", []):
                print_role_tree(child, indent + 1)
    
    print(f"\n   Department Manager Hierarchy:")
    dept_tree = hierarchy.get_role_tree(dept_manager_role.id)
    print_role_tree(dept_tree)
    
    print(f"\n   Analytics Manager Hierarchy:")
    analytics_tree = hierarchy.get_role_tree(analytics_manager_role.id)
    print_role_tree(analytics_tree)
    
    # Demonstrate permission aggregation
    print("\n7. Permission Aggregation Summary...")
    
    for user_id in ["alice", "bob", "carol", "david"]:
        user_roles = await storage.get_user_roles(user_id)
        valid_roles = [ur for ur in user_roles if ur.is_valid()]
        
        if valid_roles:
            role_names = [hierarchy.get_role(ur.role_id).name for ur in valid_roles]
            all_permissions = set()
            for user_role in valid_roles:
                role_permissions = hierarchy.get_all_permissions(user_role.role_id)
                all_permissions.update(role_permissions)
            
            print(f"\n   👤 {user_id.title()}:")
            print(f"      Roles: {', '.join(role_names)}")
            print(f"      Total Permissions: {len(all_permissions)}")
            print(f"      Permissions: {', '.join(sorted(all_permissions))}")
    
    # Demonstrate role validation
    print("\n8. Role Hierarchy Validation...")
    issues = hierarchy.validate_hierarchy()
    if issues:
        print("   ⚠️  Issues found:")
        for issue in issues:
            print(f"      - {issue}")
    else:
        print("   ✅ Role hierarchy is valid - no issues found")
    
    # Demonstrate expired role cleanup
    print("\n9. Role Expiration and Cleanup...")
    
    # Create an expired role for demonstration
    expired_role = create_user_role(
        user_id="temp_user",
        role_id="viewer",
        granted_by="system_admin",
        expires_in=timedelta(seconds=-1)  # Already expired
    )
    await storage.assign_role(expired_role)
    print(f"   ✅ Created expired role assignment for temp_user")
    
    # Check roles before cleanup
    temp_roles_before = await storage.get_user_roles("temp_user")
    print(f"   📊 temp_user has {len(temp_roles_before)} role(s) before cleanup")
    
    # Cleanup expired roles
    cleaned_count = await storage.cleanup_expired_roles()
    print(f"   🧹 Cleaned up {cleaned_count} expired role assignment(s)")
    
    # Check roles after cleanup
    temp_roles_after = await storage.get_user_roles("temp_user")
    print(f"   📊 temp_user has {len(temp_roles_after)} role(s) after cleanup")
    
    print("\n" + "=" * 60)
    print("🎉 RBAC System Example Completed Successfully!")
    print("\nKey Features Demonstrated:")
    print("✅ Role hierarchy with inheritance")
    print("✅ Permission aggregation through role chain")
    print("✅ Temporal role assignments with expiration")
    print("✅ Role validation and circular dependency detection")
    print("✅ Automatic cleanup of expired roles")
    print("✅ Flexible permission checking system")


if __name__ == "__main__":
    asyncio.run(main())
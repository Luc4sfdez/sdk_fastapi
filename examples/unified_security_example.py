"""
Example: Unified Security Middleware Integration

This example demonstrates how to set up and use the UnifiedSecurityMiddleware
to coordinate all security layers in a FastAPI application.

The middleware processes requests through multiple security layers:
1. mTLS validation (if enabled)
2. JWT authentication
3. RBAC authorization
4. ABAC authorization  
5. Threat detection

Features demonstrated:
- Complete security stack setup
- Custom layer configurations
- Security metrics monitoring
- Error handling and graceful degradation
- Real-world endpoint protection
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import security components
from fastapi_microservices_sdk.security.advanced import (
    AdvancedSecurityConfig,
    UnifiedSecurityMiddleware,
    SecurityLayerType,
    SecurityLayerConfig,
    setup_unified_security_middleware,
    create_default_layer_configs
)
from fastapi_microservices_sdk.security.advanced.rbac import RBACEngine, Role, Permission
from fastapi_microservices_sdk.security.advanced.abac import ABACEngine
from fastapi_microservices_sdk.security.advanced.threat_detection import ThreatDetector


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_rbac_engine() -> RBACEngine:
    """Setup RBAC engine with roles and permissions."""
    engine = RBACEngine()
    
    # Define roles
    admin_role = Role(name="admin", description="System administrator")
    manager_role = Role(name="manager", description="Department manager")
    user_role = Role(name="user", description="Regular user")
    
    # Define permissions
    permissions = [
        Permission(name="users.read", description="Read user information"),
        Permission(name="users.write", description="Create/update users"),
        Permission(name="users.delete", description="Delete users"),
        Permission(name="reports.read", description="Read reports"),
        Permission(name="reports.write", description="Create reports"),
        Permission(name="admin.read", description="Read admin data"),
        Permission(name="admin.write", description="Modify admin settings"),
    ]
    
    # Add roles and permissions
    await engine.add_role(admin_role)
    await engine.add_role(manager_role)
    await engine.add_role(user_role)
    
    for perm in permissions:
        await engine.add_permission(perm)
    
    # Assign permissions to roles
    # Admin has all permissions
    admin_perms = ["users.read", "users.write", "users.delete", 
                   "reports.read", "reports.write", "admin.read", "admin.write"]
    for perm in admin_perms:
        await engine.assign_permission_to_role("admin", perm)
    
    # Manager has user and report permissions
    manager_perms = ["users.read", "users.write", "reports.read", "reports.write"]
    for perm in manager_perms:
        await engine.assign_permission_to_role("manager", perm)
    
    # User has read-only permissions
    user_perms = ["users.read", "reports.read"]
    for perm in user_perms:
        await engine.assign_permission_to_role("user", perm)
    
    # Assign roles to test users
    await engine.assign_role_to_user("alice", "admin")
    await engine.assign_role_to_user("bob", "manager")
    await engine.assign_role_to_user("charlie", "user")
    
    logger.info("RBAC engine configured with roles and permissions")
    return engine


async def setup_abac_engine() -> ABACEngine:
    """Setup ABAC engine with policies."""
    engine = ABACEngine()
    
    # Business hours policy
    business_hours_policy = {
        "id": "business_hours",
        "description": "Allow access during business hours (9 AM - 6 PM)",
        "target": {
            "resource": {"path": "/api/*"},
            "environment": {"time": "*"}
        },
        "rule": """
            import datetime
            now = datetime.datetime.now()
            return 9 <= now.hour < 18
        """,
        "effect": "Permit"
    }
    
    # Admin access policy
    admin_policy = {
        "id": "admin_access",
        "description": "Admins can access everything",
        "target": {
            "subject": {"roles": ["admin"]},
            "resource": {"path": "*"}
        },
        "rule": "subject.roles contains 'admin'",
        "effect": "Permit"
    }
    
    # Manager access policy
    manager_policy = {
        "id": "manager_access", 
        "description": "Managers can access user and report endpoints",
        "target": {
            "subject": {"roles": ["manager"]},
            "resource": {"path": ["/api/users/*", "/api/reports/*"]}
        },
        "rule": """
            subject.roles contains 'manager' and (
                resource.path starts_with '/api/users' or 
                resource.path starts_with '/api/reports'
            )
        """,
        "effect": "Permit"
    }
    
    # User read-only policy
    user_policy = {
        "id": "user_readonly",
        "description": "Users can read their own data",
        "target": {
            "subject": {"roles": ["user"]},
            "resource": {"method": "GET"}
        },
        "rule": "subject.roles contains 'user' and action.operation starts_with 'GET:'",
        "effect": "Permit"
    }
    
    # Add policies
    await engine.add_policy(business_hours_policy)
    await engine.add_policy(admin_policy)
    await engine.add_policy(manager_policy)
    await engine.add_policy(user_policy)
    
    logger.info("ABAC engine configured with policies")
    return engine


def create_security_config() -> AdvancedSecurityConfig:
    """Create security configuration."""
    return AdvancedSecurityConfig(
        # Disable mTLS for this example (would require certificates)
        mtls_enabled=False,
        
        # Enable RBAC and ABAC
        rbac_enabled=True,
        abac_enabled=True,
        
        # Enable threat detection
        threat_detection_enabled=True,
        
        # Enable debug mode for detailed logging
        debug_mode=True,
        log_level="INFO",
        
        # Security settings
        jwt_secret_key="your-secret-key-here",
        jwt_algorithm="HS256",
        jwt_expiration_minutes=60
    )


def create_custom_layer_configs() -> list[SecurityLayerConfig]:
    """Create custom security layer configurations."""
    return [
        # JWT authentication - required and fail closed
        SecurityLayerConfig(
            layer_type=SecurityLayerType.JWT,
            enabled=True,
            required=True,
            fail_open=False,
            timeout_seconds=3.0
        ),
        
        # RBAC authorization - enabled but can fail open for graceful degradation
        SecurityLayerConfig(
            layer_type=SecurityLayerType.RBAC,
            enabled=True,
            required=False,
            fail_open=True,
            timeout_seconds=2.0
        ),
        
        # ABAC authorization - enabled but can fail open
        SecurityLayerConfig(
            layer_type=SecurityLayerType.ABAC,
            enabled=True,
            required=False,
            fail_open=True,
            timeout_seconds=3.0
        ),
        
        # Threat detection - enabled but should not block requests on failure
        SecurityLayerConfig(
            layer_type=SecurityLayerType.THREAT_DETECTION,
            enabled=True,
            required=False,
            fail_open=True,
            timeout_seconds=1.0
        )
    ]


async def create_app() -> FastAPI:
    """Create and configure FastAPI application with unified security."""
    app = FastAPI(
        title="Unified Security Example",
        description="Example application demonstrating unified security middleware",
        version="1.0.0"
    )
    
    # Setup security components
    security_config = create_security_config()
    rbac_engine = await setup_rbac_engine()
    abac_engine = await setup_abac_engine()
    threat_detector = ThreatDetector(enable_auto_response=False)
    
    # Setup unified security middleware
    security_middleware = setup_unified_security_middleware(
        app=app,
        config=security_config,
        layer_configs=create_custom_layer_configs(),
        rbac_engine=rbac_engine,
        abac_engine=abac_engine,
        threat_detector=threat_detector
    )
    
    # Store middleware reference for metrics access
    app.state.security_middleware = security_middleware
    
    # API Endpoints
    
    @app.get("/")
    async def root():
        """Public endpoint - no authentication required."""
        return {"message": "Welcome to the Unified Security Example API"}
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    # User management endpoints
    @app.get("/api/users")
    async def list_users():
        """List all users - requires users.read permission."""
        return {
            "users": [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "manager"},
                {"id": 3, "name": "Charlie", "role": "user"}
            ]
        }
    
    @app.post("/api/users")
    async def create_user():
        """Create new user - requires users.write permission."""
        return {"message": "User created successfully", "id": 4}
    
    @app.delete("/api/users/{user_id}")
    async def delete_user(user_id: int):
        """Delete user - requires users.delete permission."""
        return {"message": f"User {user_id} deleted successfully"}
    
    # Report endpoints
    @app.get("/api/reports")
    async def list_reports():
        """List reports - requires reports.read permission."""
        return {
            "reports": [
                {"id": 1, "title": "Monthly Sales", "created_by": "bob"},
                {"id": 2, "title": "User Analytics", "created_by": "alice"}
            ]
        }
    
    @app.post("/api/reports")
    async def create_report():
        """Create report - requires reports.write permission."""
        return {"message": "Report created successfully", "id": 3}
    
    # Admin endpoints
    @app.get("/admin/settings")
    async def get_admin_settings():
        """Get admin settings - requires admin.read permission."""
        return {
            "settings": {
                "max_users": 1000,
                "security_level": "high",
                "backup_enabled": True
            }
        }
    
    @app.post("/admin/settings")
    async def update_admin_settings():
        """Update admin settings - requires admin.write permission."""
        return {"message": "Admin settings updated successfully"}
    
    # Security metrics endpoint
    @app.get("/security/metrics")
    async def get_security_metrics():
        """Get security metrics from the middleware."""
        if hasattr(app.state, 'security_middleware'):
            metrics = app.state.security_middleware.get_metrics()
            return {"security_metrics": metrics}
        return {"error": "Security middleware not available"}
    
    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Custom HTTP exception handler."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "status_code": exc.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    logger.info("FastAPI application configured with unified security middleware")
    return app


# Example usage and testing
async def test_security_scenarios():
    """Test various security scenarios."""
    logger.info("Testing security scenarios...")
    
    # This would typically be done with a test client
    # For demonstration, we'll show the expected behavior
    
    scenarios = [
        {
            "name": "Admin accessing admin endpoint",
            "user": "alice",
            "roles": ["admin"],
            "endpoint": "GET /admin/settings",
            "expected": "SUCCESS - Admin has all permissions"
        },
        {
            "name": "Manager accessing user endpoint",
            "user": "bob", 
            "roles": ["manager"],
            "endpoint": "GET /api/users",
            "expected": "SUCCESS - Manager has users.read permission"
        },
        {
            "name": "User accessing admin endpoint",
            "user": "charlie",
            "roles": ["user"],
            "endpoint": "GET /admin/settings", 
            "expected": "DENIED - User lacks admin.read permission"
        },
        {
            "name": "User creating report",
            "user": "charlie",
            "roles": ["user"],
            "endpoint": "POST /api/reports",
            "expected": "DENIED - User lacks reports.write permission"
        },
        {
            "name": "Unauthenticated request",
            "user": None,
            "roles": [],
            "endpoint": "GET /api/users",
            "expected": "DENIED - No JWT token provided"
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"Scenario: {scenario['name']}")
        logger.info(f"  User: {scenario['user']}")
        logger.info(f"  Roles: {scenario['roles']}")
        logger.info(f"  Endpoint: {scenario['endpoint']}")
        logger.info(f"  Expected: {scenario['expected']}")
        logger.info("")


if __name__ == "__main__":
    # Run the example
    import uvicorn
    
    async def main():
        # Test security scenarios
        await test_security_scenarios()
        
        # Create and run the application
        app = await create_app()
        
        logger.info("Starting server with unified security middleware...")
        logger.info("Available endpoints:")
        logger.info("  GET  /                    - Public welcome message")
        logger.info("  GET  /health              - Health check")
        logger.info("  GET  /api/users           - List users (requires users.read)")
        logger.info("  POST /api/users           - Create user (requires users.write)")
        logger.info("  DELETE /api/users/{id}    - Delete user (requires users.delete)")
        logger.info("  GET  /api/reports         - List reports (requires reports.read)")
        logger.info("  POST /api/reports         - Create report (requires reports.write)")
        logger.info("  GET  /admin/settings      - Admin settings (requires admin.read)")
        logger.info("  POST /admin/settings      - Update settings (requires admin.write)")
        logger.info("  GET  /security/metrics    - Security metrics")
        logger.info("")
        logger.info("Test with different JWT tokens containing different user roles:")
        logger.info("  - alice (admin): Full access to all endpoints")
        logger.info("  - bob (manager): Access to users and reports")
        logger.info("  - charlie (user): Read-only access")
        logger.info("")
        logger.info("Example curl commands:")
        logger.info("  curl -H 'Authorization: Bearer <jwt_token>' http://localhost:8000/api/users")
        logger.info("  curl http://localhost:8000/security/metrics")
        
        # Run the server
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    
    # Run the async main function
    asyncio.run(main())
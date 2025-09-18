#!/usr/bin/env python3
"""
ABAC (Attribute-Based Access Control) Example

This example demonstrates how to use the ABAC system with FastAPI,
including policy creation, middleware setup, and attribute providers.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

# Import ABAC components
from fastapi_microservices_sdk.security.advanced.abac import (
    # Core classes
    ABACEngine, PolicyStore, Policy, PolicyRule, PolicyCondition,
    AttributeType, ComparisonOperator, PolicyEffect, LogicalOperator,
    AttributeValue, Attributes, ABACContext,
    
    # Middleware and integration
    setup_abac_middleware, abac_protected, get_abac_decision,
    
    # Attribute providers
    DatabaseAttributeProvider, CompositeAttributeProvider,
    
    # Factory functions
    create_abac_engine, ABACEngineBuilder,
    
    # Conflict resolution
    PolicyConflictResolver
)


# =============================================================================
# SAMPLE POLICIES
# =============================================================================

def create_sample_policies():
    """Create sample ABAC policies for demonstration."""
    
    policies = []
    
    # Policy 1: Admin users can do anything
    admin_condition = PolicyCondition(
        AttributeType.USER, "role", ComparisonOperator.EQUALS, "admin"
    )
    admin_rule = PolicyRule(conditions=[admin_condition])
    admin_policy = Policy(
        policy_id="admin_full_access",
        name="Admin Full Access",
        description="Administrators have full access to all resources",
        effect=PolicyEffect.ALLOW,
        rules=[admin_rule],
        priority=100
    )
    policies.append(admin_policy)
    
    # Policy 2: Users can read their own data
    user_condition1 = PolicyCondition(
        AttributeType.USER, "role", ComparisonOperator.EQUALS, "user"
    )
    user_condition2 = PolicyCondition(
        AttributeType.ACTION, "category", ComparisonOperator.EQUALS, "read"
    )
    user_condition3 = PolicyCondition(
        AttributeType.USER, "id", ComparisonOperator.EQUALS, "{{resource.owner_id}}"
    )
    user_rule = PolicyRule(
        conditions=[user_condition1, user_condition2, user_condition3],
        operator=LogicalOperator.AND
    )
    user_policy = Policy(
        policy_id="user_own_data_read",
        name="User Own Data Read",
        description="Users can read their own data",
        effect=PolicyEffect.ALLOW,
        rules=[user_rule],
        priority=50
    )
    policies.append(user_policy)
    
    # Policy 3: Deny access during maintenance hours
    maintenance_condition = PolicyCondition(
        AttributeType.ENVIRONMENT, "maintenance_mode", ComparisonOperator.EQUALS, True
    )
    maintenance_rule = PolicyRule(conditions=[maintenance_condition])
    maintenance_policy = Policy(
        policy_id="deny_during_maintenance",
        name="Deny During Maintenance",
        description="Deny all access during maintenance",
        effect=PolicyEffect.DENY,
        rules=[maintenance_rule],
        priority=200  # High priority to override other policies
    )
    policies.append(maintenance_policy)
    
    # Policy 4: IT department can manage users during business hours
    it_condition1 = PolicyCondition(
        AttributeType.USER, "department", ComparisonOperator.EQUALS, "IT"
    )
    it_condition2 = PolicyCondition(
        AttributeType.ENVIRONMENT, "is_business_hours", ComparisonOperator.EQUALS, True
    )
    it_condition3 = PolicyCondition(
        AttributeType.RESOURCE, "type", ComparisonOperator.EQUALS, "user"
    )
    it_rule = PolicyRule(
        conditions=[it_condition1, it_condition2, it_condition3],
        operator=LogicalOperator.AND
    )
    it_policy = Policy(
        policy_id="it_user_management",
        name="IT User Management",
        description="IT can manage users during business hours",
        effect=PolicyEffect.ALLOW,
        rules=[it_rule],
        priority=75
    )
    policies.append(it_policy)
    
    # Policy 5: Deny external access to sensitive resources
    external_condition1 = PolicyCondition(
        AttributeType.ENVIRONMENT, "is_internal_ip", ComparisonOperator.EQUALS, False
    )
    external_condition2 = PolicyCondition(
        AttributeType.RESOURCE, "classification", ComparisonOperator.EQUALS, "sensitive"
    )
    external_rule = PolicyRule(
        conditions=[external_condition1, external_condition2],
        operator=LogicalOperator.AND
    )
    external_policy = Policy(
        policy_id="deny_external_sensitive",
        name="Deny External Sensitive Access",
        description="Deny external access to sensitive resources",
        effect=PolicyEffect.DENY,
        rules=[external_rule],
        priority=150
    )
    policies.append(external_policy)
    
    return policies


# =============================================================================
# CUSTOM ATTRIBUTE PROVIDER
# =============================================================================

class CustomAttributeProvider:
    """Custom attribute provider with realistic data."""
    
    def __init__(self):
        # Simulate user database
        self.users = {
            "admin_user": {
                "id": "admin_user",
                "role": "admin",
                "department": "IT",
                "clearance_level": "top_secret"
            },
            "john_doe": {
                "id": "john_doe", 
                "role": "user",
                "department": "Sales",
                "clearance_level": "public"
            },
            "jane_smith": {
                "id": "jane_smith",
                "role": "user", 
                "department": "IT",
                "clearance_level": "confidential"
            },
            "it_admin": {
                "id": "it_admin",
                "role": "it_admin",
                "department": "IT",
                "clearance_level": "secret"
            }
        }
        
        # Simulate resource database
        self.resources = {
            "/users/john_doe": {
                "id": "/users/john_doe",
                "type": "user",
                "owner_id": "john_doe",
                "classification": "public"
            },
            "/users/jane_smith": {
                "id": "/users/jane_smith",
                "type": "user", 
                "owner_id": "jane_smith",
                "classification": "confidential"
            },
            "/admin/config": {
                "id": "/admin/config",
                "type": "configuration",
                "owner_id": "system",
                "classification": "sensitive"
            },
            "/reports/financial": {
                "id": "/reports/financial",
                "type": "report",
                "owner_id": "system", 
                "classification": "sensitive"
            }
        }
        
        # Maintenance mode flag
        self.maintenance_mode = False
    
    async def get_user_attributes(self, user_id: str) -> dict:
        """Get user attributes."""
        user_data = self.users.get(user_id, {})
        
        attributes = {}
        for key, value in user_data.items():
            attributes[key] = AttributeValue(value, type(value).__name__, "custom_provider")
        
        # Add computed attributes
        attributes["authenticated"] = AttributeValue(user_id != "anonymous", "boolean", "custom_provider")
        attributes["created_at"] = AttributeValue(datetime.now(timezone.utc), "datetime", "custom_provider")
        
        return attributes
    
    async def get_resource_attributes(self, resource_id: str) -> dict:
        """Get resource attributes."""
        resource_data = self.resources.get(resource_id, {
            "id": resource_id,
            "type": "unknown",
            "classification": "public"
        })
        
        attributes = {}
        for key, value in resource_data.items():
            attributes[key] = AttributeValue(value, type(value).__name__, "custom_provider")
        
        attributes["created_at"] = AttributeValue(datetime.now(timezone.utc), "datetime", "custom_provider")
        
        return attributes
    
    async def get_environment_attributes(self, context: dict) -> dict:
        """Get environment attributes."""
        current_time = datetime.now(timezone.utc)
        
        attributes = {
            "current_time": AttributeValue(current_time, "datetime", "custom_provider"),
            "day_of_week": AttributeValue(current_time.strftime("%A").lower(), "string", "custom_provider"),
            "hour": AttributeValue(current_time.hour, "integer", "custom_provider"),
            "is_business_hours": AttributeValue(9 <= current_time.hour <= 17, "boolean", "custom_provider"),
            "is_weekend": AttributeValue(current_time.weekday() >= 5, "boolean", "custom_provider"),
            "maintenance_mode": AttributeValue(self.maintenance_mode, "boolean", "custom_provider")
        }
        
        # Add request context
        if "source_ip" in context:
            ip = context["source_ip"]
            attributes["source_ip"] = AttributeValue(ip, "string", "custom_provider")
            attributes["is_internal_ip"] = AttributeValue(
                ip.startswith(("192.168.", "10.", "172.16.")), 
                "boolean", "custom_provider"
            )
        
        if "user_agent" in context:
            attributes["user_agent"] = AttributeValue(context["user_agent"], "string", "custom_provider")
        
        return attributes
    
    async def get_action_attributes(self, action: str) -> dict:
        """Get action attributes."""
        attributes = {
            "name": AttributeValue(action, "string", "custom_provider"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "custom_provider")
        }
        
        # Categorize actions
        action_lower = action.lower()
        if any(keyword in action_lower for keyword in ["get", "read", "view", "list"]):
            attributes["category"] = AttributeValue("read", "string", "custom_provider")
            attributes["risk_level"] = AttributeValue("low", "string", "custom_provider")
        elif any(keyword in action_lower for keyword in ["post", "create", "add"]):
            attributes["category"] = AttributeValue("create", "string", "custom_provider")
            attributes["risk_level"] = AttributeValue("medium", "string", "custom_provider")
        elif any(keyword in action_lower for keyword in ["put", "patch", "update"]):
            attributes["category"] = AttributeValue("update", "string", "custom_provider")
            attributes["risk_level"] = AttributeValue("medium", "string", "custom_provider")
        elif any(keyword in action_lower for keyword in ["delete", "remove"]):
            attributes["category"] = AttributeValue("delete", "string", "custom_provider")
            attributes["risk_level"] = AttributeValue("high", "string", "custom_provider")
        else:
            attributes["category"] = AttributeValue("other", "string", "custom_provider")
            attributes["risk_level"] = AttributeValue("medium", "string", "custom_provider")
        
        return attributes


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Create FastAPI app
app = FastAPI(
    title="ABAC Example API",
    description="Demonstration of Attribute-Based Access Control with FastAPI",
    version="1.0.0"
)

# Create custom attribute provider
custom_provider = CustomAttributeProvider()

# Create ABAC engine with custom provider
abac_engine = (ABACEngineBuilder()
              .with_attribute_provider(custom_provider)
              .with_cache_ttl(300)
              .build())

# Add sample policies
for policy in create_sample_policies():
    abac_engine.add_policy(policy)

# Custom extractors for the middleware
def extract_user_id(request: Request) -> str:
    """Extract user ID from request headers."""
    return request.headers.get("X-User-ID", "anonymous")

def extract_resource_id(request: Request) -> str:
    """Extract resource ID from request path."""
    return request.url.path

def extract_action(request: Request) -> str:
    """Extract action from request method and path."""
    method = request.method.lower()
    path = request.url.path.replace("/", "_").strip("_")
    return f"{method}_{path}" if path else method

# Setup ABAC middleware
setup_abac_middleware(
    app,
    abac_engine,
    extract_user_id=extract_user_id,
    extract_resource_id=extract_resource_id,
    extract_action=extract_action,
    precedence_rule="deny_overrides",
    skip_paths=["/", "/docs", "/redoc", "/openapi.json", "/health", "/policies"]
)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint (not protected)."""
    return {
        "message": "ABAC Example API",
        "description": "Use X-User-ID header to simulate different users",
        "users": ["admin_user", "john_doe", "jane_smith", "it_admin", "anonymous"],
        "endpoints": [
            "GET /health - Health check",
            "GET /policies - List policies", 
            "GET /users/{user_id} - Get user info",
            "POST /users - Create user",
            "PUT /users/{user_id} - Update user",
            "DELETE /users/{user_id} - Delete user",
            "GET /admin/config - Admin configuration",
            "GET /reports/financial - Financial reports",
            "POST /maintenance/toggle - Toggle maintenance mode"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint (not protected)."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@app.get("/policies")
async def list_policies():
    """List all ABAC policies (not protected)."""
    policies = abac_engine.get_all_policies()
    return {
        "policies": [
            {
                "id": p.policy_id,
                "name": p.name,
                "description": p.description,
                "effect": p.effect.value,
                "priority": p.priority,
                "enabled": p.enabled
            }
            for p in policies
        ]
    }

@app.get("/users/{user_id}")
@abac_protected(resource_type="user", action_override="read_user")
async def get_user(user_id: str, request: Request):
    """Get user information (ABAC protected)."""
    decision = get_abac_decision(request)
    
    # Simulate getting user data
    user_data = custom_provider.users.get(user_id, {"error": "User not found"})
    
    return {
        "user": user_data,
        "abac_decision": decision.to_dict() if decision else None,
        "access_granted": True
    }

@app.post("/users")
@abac_protected(resource_type="user", action_override="create_user")
async def create_user(request: Request):
    """Create new user (ABAC protected)."""
    decision = get_abac_decision(request)
    
    return {
        "message": "User created successfully",
        "abac_decision": decision.to_dict() if decision else None
    }

@app.put("/users/{user_id}")
@abac_protected(resource_type="user", action_override="update_user")
async def update_user(user_id: str, request: Request):
    """Update user (ABAC protected)."""
    decision = get_abac_decision(request)
    
    return {
        "message": f"User {user_id} updated successfully",
        "abac_decision": decision.to_dict() if decision else None
    }

@app.delete("/users/{user_id}")
@abac_protected(resource_type="user", action_override="delete_user")
async def delete_user(user_id: str, request: Request):
    """Delete user (ABAC protected)."""
    decision = get_abac_decision(request)
    
    return {
        "message": f"User {user_id} deleted successfully",
        "abac_decision": decision.to_dict() if decision else None
    }

@app.get("/admin/config")
@abac_protected(resource_type="configuration", action_override="read_config")
async def get_admin_config(request: Request):
    """Get admin configuration (ABAC protected)."""
    decision = get_abac_decision(request)
    
    return {
        "config": {
            "maintenance_mode": custom_provider.maintenance_mode,
            "max_users": 1000,
            "security_level": "high"
        },
        "abac_decision": decision.to_dict() if decision else None
    }

@app.get("/reports/financial")
@abac_protected(resource_type="report", action_override="read_report")
async def get_financial_report(request: Request):
    """Get financial report (ABAC protected)."""
    decision = get_abac_decision(request)
    
    return {
        "report": {
            "revenue": "$1,000,000",
            "expenses": "$800,000", 
            "profit": "$200,000"
        },
        "abac_decision": decision.to_dict() if decision else None
    }

@app.post("/maintenance/toggle")
async def toggle_maintenance(request: Request):
    """Toggle maintenance mode (affects ABAC policies)."""
    user_id = extract_user_id(request)
    
    # Only admin can toggle maintenance
    if user_id != "admin_user":
        raise HTTPException(status_code=403, detail="Only admin can toggle maintenance mode")
    
    custom_provider.maintenance_mode = not custom_provider.maintenance_mode
    
    # Clear ABAC cache since environment changed
    abac_engine._clear_cache()
    
    return {
        "maintenance_mode": custom_provider.maintenance_mode,
        "message": f"Maintenance mode {'enabled' if custom_provider.maintenance_mode else 'disabled'}"
    }

@app.get("/debug/attributes")
async def debug_attributes(request: Request):
    """Debug endpoint to see current attributes (not protected)."""
    user_id = extract_user_id(request)
    resource_id = extract_resource_id(request)
    action = extract_action(request)
    
    context = {
        "source_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "session_id": request.headers.get("X-Session-ID")
    }
    
    # Get attributes
    user_attrs = await custom_provider.get_user_attributes(user_id)
    resource_attrs = await custom_provider.get_resource_attributes(resource_id)
    env_attrs = await custom_provider.get_environment_attributes(context)
    action_attrs = await custom_provider.get_action_attributes(action)
    
    return {
        "extracted_ids": {
            "user_id": user_id,
            "resource_id": resource_id,
            "action": action
        },
        "attributes": {
            "user": {k: v.value for k, v in user_attrs.items()},
            "resource": {k: v.value for k, v in resource_attrs.items()},
            "environment": {k: v.value for k, v in env_attrs.items()},
            "action": {k: v.value for k, v in action_attrs.items()}
        },
        "context": context
    }


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting ABAC Example API")
    print("📋 Available test users:")
    print("  - admin_user (admin role)")
    print("  - john_doe (regular user)")
    print("  - jane_smith (IT user)")
    print("  - it_admin (IT admin)")
    print("  - anonymous (no header)")
    print()
    print("🔧 Usage:")
    print("  curl -H 'X-User-ID: admin_user' http://localhost:8000/users/john_doe")
    print("  curl -H 'X-User-ID: john_doe' http://localhost:8000/users/john_doe")
    print("  curl -H 'X-User-ID: anonymous' http://localhost:8000/admin/config")
    print()
    print("📊 Visit http://localhost:8000/docs for interactive API documentation")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
# ABAC (Attribute-Based Access Control) Documentation

## Overview

The ABAC (Attribute-Based Access Control) system provides fine-grained, contextual access control for FastAPI microservices. Unlike traditional role-based systems, ABAC makes access decisions based on attributes of users, resources, actions, and environmental context.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Data Models](#data-models)
- [Policy Engine](#policy-engine)
- [Middleware Integration](#middleware-integration)
- [Attribute Providers](#attribute-providers)
- [Policy Management](#policy-management)
- [Conflict Resolution](#conflict-resolution)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

## Core Concepts

### Attributes

ABAC decisions are based on four types of attributes:

- **User Attributes**: Properties of the requesting user (role, department, clearance level)
- **Resource Attributes**: Properties of the requested resource (type, classification, owner)
- **Action Attributes**: Properties of the requested action (category, risk level)
- **Environment Attributes**: Contextual properties (time, location, IP address)

### Policies

Policies define access rules using boolean logic and comparison operators:

```json
{
  "policy_id": "admin_access",
  "name": "Admin Access Policy",
  "effect": "allow",
  "priority": 100,
  "rules": [
    {
      "operator": "and",
      "conditions": [
        {
          "attribute_type": "user",
          "attribute_name": "role",
          "operator": "eq",
          "value": "admin"
        },
        {
          "attribute_type": "environment",
          "attribute_name": "is_business_hours",
          "operator": "eq",
          "value": true
        }
      ]
    }
  ]
}
```

### Decision Flow

1. **Request arrives** at protected endpoint
2. **Attributes collected** from various sources
3. **Policies evaluated** against attributes
4. **Conflicts resolved** using precedence rules
5. **Decision enforced** (ALLOW/DENY)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  ABAC Middleware │────│  Policy Engine  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                       ┌────────▼────────┐    ┌─────────▼─────────┐
                       │ Attribute       │    │ Policy Store      │
                       │ Providers       │    │ & Evaluator       │
                       └─────────────────┘    └───────────────────┘
```

## Quick Start

### 1. Basic Setup

```python
from fastapi import FastAPI
from fastapi_microservices_sdk.security.advanced.abac import (
    create_abac_engine, setup_abac_middleware, abac_protected
)

app = FastAPI()

# Create ABAC engine
engine = create_abac_engine()

# Setup middleware
setup_abac_middleware(app, engine)

@app.get("/protected")
@abac_protected(resource_type="document", action_override="read_document")
async def protected_endpoint():
    return {"message": "Access granted"}
```

### 2. Add Policies

```python
from fastapi_microservices_sdk.security.advanced.abac import (
    Policy, PolicyRule, PolicyCondition, AttributeType, 
    ComparisonOperator, PolicyEffect
)

# Create admin policy
condition = PolicyCondition(
    AttributeType.USER, "role", ComparisonOperator.EQUALS, "admin"
)
rule = PolicyRule(conditions=[condition])
policy = Policy(
    policy_id="admin_policy",
    name="Admin Access",
    description="Allow admin users",
    effect=PolicyEffect.ALLOW,
    rules=[rule]
)

engine.add_policy(policy)
```

### 3. Custom Attribute Provider

```python
from fastapi_microservices_sdk.security.advanced.abac import AttributeProvider

class CustomAttributeProvider(AttributeProvider):
    async def get_user_attributes(self, user_id: str):
        # Fetch from your user database
        user = await get_user_from_db(user_id)
        return {
            "role": AttributeValue(user.role, "string", "database"),
            "department": AttributeValue(user.department, "string", "database")
        }
    
    # Implement other methods...

# Use custom provider
engine = create_abac_engine(attribute_provider=CustomAttributeProvider())
```

## Data Models

### AttributeValue

Represents a single attribute with metadata:

```python
class AttributeValue:
    def __init__(self, value: Any, type: str, source: str):
        self.value = value           # The actual value
        self.type = type            # Data type (string, integer, boolean, etc.)
        self.source = source        # Where it came from (database, system, etc.)
        self.timestamp = datetime.now(timezone.utc)
```

### Attributes

Container for all attributes in a request context:

```python
attributes = Attributes()
attributes.set_attribute(AttributeType.USER, "role", 
                        AttributeValue("admin", "string", "database"))
```

### PolicyCondition

Defines a single condition in a policy:

```python
condition = PolicyCondition(
    attribute_type=AttributeType.USER,
    attribute_name="role",
    operator=ComparisonOperator.EQUALS,
    value="admin"
)
```

**Available Operators:**
- `EQUALS` / `NOT_EQUALS`
- `GREATER_THAN` / `LESS_THAN` / `GREATER_THAN_OR_EQUAL` / `LESS_THAN_OR_EQUAL`
- `IN` / `NOT_IN`
- `CONTAINS` / `NOT_CONTAINS`
- `MATCHES` (regex)

### PolicyRule

Combines conditions with logical operators:

```python
rule = PolicyRule(
    conditions=[condition1, condition2],
    operator=LogicalOperator.AND  # AND, OR, NOT
)
```

### Policy

Complete access control policy:

```python
policy = Policy(
    policy_id="unique_id",
    name="Human Readable Name",
    description="Policy description",
    effect=PolicyEffect.ALLOW,  # ALLOW or DENY
    rules=[rule1, rule2],
    priority=100,               # Higher = more important
    enabled=True
)
```

## Policy Engine

### ABACEngine

Main engine for policy evaluation:

```python
engine = ABACEngine(
    policy_store=PolicyStore(),
    attribute_provider=DefaultAttributeProvider(),
    logger=SecurityLogger()
)

# Evaluate access
decision = await engine.evaluate_access(
    user_id="john_doe",
    resource_id="/documents/123",
    action="read_document",
    context={"source_ip": "192.168.1.1"},
    precedence_rule="deny_overrides"
)

print(f"Decision: {decision.decision}")  # ALLOW or DENY
print(f"Reason: {decision.reason}")
```

### PolicyEvaluator

Handles policy evaluation with precedence rules:

**Precedence Rules:**
- `deny_overrides`: Any DENY decision overrides ALLOW
- `allow_overrides`: Any ALLOW decision overrides DENY  
- `first_applicable`: First matching policy wins
- `only_one_applicable`: Error if multiple policies match

### Caching

The engine includes intelligent caching:

```python
# Configure cache
engine.set_cache_ttl(600)  # 10 minutes

# Get cache statistics
stats = engine.get_cache_stats()
print(f"Cache entries: {stats['total_entries']}")

# Clear cache (e.g., after policy changes)
engine._clear_cache()
```

## Middleware Integration

### Setup Middleware

```python
from fastapi_microservices_sdk.security.advanced.abac import setup_abac_middleware

def extract_user_id(request):
    return request.headers.get("X-User-ID", "anonymous")

def extract_resource_id(request):
    return request.url.path

def extract_action(request):
    return f"{request.method.lower()}_{request.url.path.replace('/', '_')}"

setup_abac_middleware(
    app,
    abac_engine,
    extract_user_id=extract_user_id,
    extract_resource_id=extract_resource_id,
    extract_action=extract_action,
    precedence_rule="deny_overrides",
    skip_paths=["/health", "/docs"]
)
```

### Protect Endpoints

```python
@app.get("/users/{user_id}")
@abac_protected(resource_type="user", action_override="read_user")
async def get_user(user_id: str, request: Request):
    # Get ABAC decision details
    decision = get_abac_decision(request)
    
    return {
        "user_id": user_id,
        "decision": decision.to_dict() if decision else None
    }
```

### Custom Middleware

For advanced use cases, create custom middleware:

```python
from fastapi_microservices_sdk.security.advanced.abac import ABACMiddleware

middleware = ABACMiddleware(
    abac_engine=engine,
    extract_user_id=custom_user_extractor,
    precedence_rule="allow_overrides"
)

app.add_middleware(middleware.create_fastapi_middleware(), abac_middleware=middleware)
```

## Attribute Providers

### Default Provider

Provides basic attributes:

```python
provider = DefaultAttributeProvider()

# User attributes: id, authenticated, created_at
# Resource attributes: id, type, created_at  
# Environment attributes: current_time, day_of_week, hour, etc.
# Action attributes: name, category (read/create/update/delete)
```

### Database Provider

Fetches attributes from database with caching:

```python
provider = DatabaseAttributeProvider(
    db_connection=db,
    cache_ttl=300  # 5 minutes
)
```

### Composite Provider

Combines multiple providers:

```python
provider = CompositeAttributeProvider([
    DatabaseAttributeProvider(),
    DefaultAttributeProvider(),
    CustomAttributeProvider()
])
```

### Custom Provider

Implement your own provider:

```python
class MyAttributeProvider(AttributeProvider):
    async def get_user_attributes(self, user_id: str) -> Dict[str, AttributeValue]:
        # Your implementation
        return {
            "role": AttributeValue("admin", "string", "ldap"),
            "clearance": AttributeValue("secret", "string", "security_db")
        }
    
    async def get_resource_attributes(self, resource_id: str) -> Dict[str, AttributeValue]:
        # Your implementation
        pass
    
    async def get_environment_attributes(self, context: Dict[str, Any]) -> Dict[str, AttributeValue]:
        # Your implementation  
        pass
    
    async def get_action_attributes(self, action: str) -> Dict[str, AttributeValue]:
        # Your implementation
        pass
```

## Policy Management

### Loading from Files

```python
# Load from directory
engine.load_policies_from_directory("./policies")

# Load single policy
parser = PolicyParser()
policy = parser.parse_policy_from_file("policy.json")
engine.add_policy(policy)
```

### Policy Store Operations

```python
store = PolicyStore()

# Add policy
store.add_policy(policy)

# Get policy
policy = store.get_policy("policy_id")

# Get all enabled policies
policies = store.get_enabled_policies()

# Get by priority
policies = store.get_policies_by_priority()

# Remove policy
store.remove_policy("policy_id")

# Clear all
store.clear()
```

### Dynamic Policy Updates

```python
# Add new policy
engine.add_policy(new_policy)

# Remove policy  
engine.remove_policy("old_policy_id")

# Cache is automatically cleared
```

## Conflict Resolution

### PolicyConflictResolver

Handles conflicts between multiple applicable policies:

```python
resolver = PolicyConflictResolver()

decisions = [
    PolicyDecision(PolicyEffect.ALLOW, "policy1", "Allow reason"),
    PolicyDecision(PolicyEffect.DENY, "policy2", "Deny reason")
]

# Resolve conflict
final_decision = resolver.resolve_conflicts(decisions, "deny_overrides")
```

### Resolution Strategies

1. **deny_overrides** (default): Any DENY overrides ALLOW
2. **allow_overrides**: Any ALLOW overrides DENY
3. **first_applicable**: First policy in priority order wins
4. **unanimous**: All policies must agree
5. **majority**: Majority decision wins

## Examples

### Complete Example

See `examples/abac_example.py` for a full working example with:

- Multiple realistic policies
- Custom attribute provider
- FastAPI integration
- Interactive API documentation
- Maintenance mode toggle
- Debug endpoints

### Policy Examples

#### Time-Based Access

```json
{
  "policy_id": "business_hours_only",
  "name": "Business Hours Access",
  "effect": "deny",
  "rules": [{
    "operator": "and",
    "conditions": [{
      "attribute_type": "environment",
      "attribute_name": "is_business_hours",
      "operator": "eq",
      "value": false
    }]
  }]
}
```

#### Department-Based Access

```json
{
  "policy_id": "it_admin_access",
  "name": "IT Admin Access",
  "effect": "allow",
  "rules": [{
    "operator": "and", 
    "conditions": [
      {
        "attribute_type": "user",
        "attribute_name": "department",
        "operator": "eq",
        "value": "IT"
      },
      {
        "attribute_type": "user",
        "attribute_name": "role",
        "operator": "in",
        "value": ["admin", "manager"]
      }
    ]
  }]
}
```

#### IP-Based Restrictions

```json
{
  "policy_id": "external_access_deny",
  "name": "Deny External Access",
  "effect": "deny",
  "priority": 200,
  "rules": [{
    "operator": "and",
    "conditions": [
      {
        "attribute_type": "environment",
        "attribute_name": "is_internal_ip", 
        "operator": "eq",
        "value": false
      },
      {
        "attribute_type": "resource",
        "attribute_name": "classification",
        "operator": "eq",
        "value": "confidential"
      }
    ]
  }]
}
```

## Best Practices

### Policy Design

1. **Use descriptive names** and IDs for policies
2. **Set appropriate priorities** (higher = more important)
3. **Keep policies simple** - complex logic is hard to debug
4. **Use DENY policies sparingly** - prefer ALLOW with conditions
5. **Document policy intent** in descriptions

### Performance

1. **Use caching** for attribute providers
2. **Set reasonable cache TTL** (5-15 minutes typical)
3. **Monitor cache hit rates** with `get_cache_stats()`
4. **Limit policy complexity** to avoid evaluation overhead
5. **Use skip_paths** for public endpoints

### Security

1. **Default to DENY** - secure by default
2. **Validate all inputs** in custom providers
3. **Log all decisions** for audit trails
4. **Use precedence rules** appropriate for your security model
5. **Regularly review policies** for correctness

### Debugging

1. **Use debug endpoints** to inspect attributes
2. **Check decision reasons** in logs
3. **Test policies** with different attribute combinations
4. **Monitor conflict resolution** logs
5. **Use maintenance mode** for testing

### Scalability

1. **Use database providers** for production
2. **Implement connection pooling** in providers
3. **Consider policy distribution** for multiple services
4. **Monitor evaluation performance** 
5. **Cache frequently accessed data**

## API Reference

### Core Classes

- `ABACEngine` - Main policy evaluation engine
- `PolicyStore` - Policy storage and management
- `PolicyEvaluator` - Policy evaluation with precedence
- `PolicyConflictResolver` - Conflict resolution strategies

### Data Models

- `AttributeValue` - Single attribute with metadata
- `Attributes` - Attribute container
- `PolicyCondition` - Single policy condition
- `PolicyRule` - Rule with logical operators
- `Policy` - Complete access policy
- `PolicyDecision` - Evaluation result

### Middleware

- `ABACMiddleware` - FastAPI middleware
- `setup_abac_middleware()` - Setup helper
- `@abac_protected` - Endpoint decorator
- `get_abac_decision()` - Decision helper

### Attribute Providers

- `AttributeProvider` - Base interface
- `DefaultAttributeProvider` - Basic implementation
- `DatabaseAttributeProvider` - Database-backed with caching
- `CompositeAttributeProvider` - Multiple provider composition

### Builders and Factories

- `ABACEngineBuilder` - Builder pattern for engine configuration
- `create_abac_engine()` - Factory function with common configs

### Enums

- `AttributeType` - USER, RESOURCE, ACTION, ENVIRONMENT
- `ComparisonOperator` - EQUALS, IN, CONTAINS, MATCHES, etc.
- `LogicalOperator` - AND, OR, NOT
- `PolicyEffect` - ALLOW, DENY

For detailed API documentation, see the inline docstrings in the source code.
"""Integration tests for ABAC middleware."""

import pytest
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from fastapi_microservices_sdk.security.advanced.abac import (
    ABACEngine, ABACMiddleware, PolicyStore, Policy, PolicyRule, PolicyCondition,
    AttributeType, ComparisonOperator, PolicyEffect, AttributeValue, Attributes,
    ABACContext, setup_abac_middleware, abac_protected, get_abac_decision,
    DatabaseAttributeProvider, CompositeAttributeProvider, ABACEngineBuilder,
    create_abac_engine, PolicyConflictResolver
)


class TestABACMiddleware:
    """Test cases for ABAC middleware integration."""
    
    @pytest.fixture
    def sample_policy(self):
        """Create sample policy for testing."""
        condition = PolicyCondition(
            AttributeType.USER, "role", ComparisonOperator.EQUALS, "admin"
        )
        rule = PolicyRule(conditions=[condition])
        
        return Policy(
            policy_id="admin_policy",
            name="Admin Policy",
            description="Allow admin users",
            effect=PolicyEffect.ALLOW,
            rules=[rule]
        )
    
    @pytest.fixture
    def abac_engine(self, sample_policy):
        """Create ABAC engine for testing."""
        engine = ABACEngine()
        engine.add_policy(sample_policy)
        return engine
    
    @pytest.fixture
    def test_app(self, abac_engine):
        """Create test FastAPI app with ABAC middleware."""
        app = FastAPI()
        
        # Custom extractors for testing
        def extract_user_id(request):
            return request.headers.get("X-User-ID", "anonymous")
        
        def extract_resource_id(request):
            return request.path_params.get("id", request.url.path)
        
        def extract_action(request):
            return f"{request.method.lower()}_resource"
        
        # Setup ABAC middleware
        setup_abac_middleware(
            app,
            abac_engine,
            extract_user_id=extract_user_id,
            extract_resource_id=extract_resource_id,
            extract_action=extract_action,
            skip_paths=["/health", "/docs"]
        )
        
        @app.get("/health")
        async def health():
            return {"status": "ok"}
        
        @app.get("/protected")
        async def protected():
            return {"message": "protected resource"}
        
        @app.get("/users/{id}")
        @abac_protected(resource_type="user", action_override="read_user")
        async def get_user(id: str, request: Request):
            decision = get_abac_decision(request)
            return {
                "user_id": id,
                "decision": decision.to_dict() if decision else None
            }
        
        return app
    
    def test_middleware_skips_health_endpoint(self, test_app):
        """Test that middleware skips health endpoint."""
        client = TestClient(test_app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    @patch('fastapi_microservices_sdk.security.advanced.abac.DefaultAttributeProvider.get_user_attributes')
    def test_middleware_allows_admin_user(self, mock_get_user_attrs, test_app):
        """Test that middleware allows admin user."""
        # Mock user attributes to return admin role
        mock_get_user_attrs.return_value = asyncio.create_task(asyncio.coroutine(lambda: {
            "role": AttributeValue("admin", "string", "test")
        })())
        
        client = TestClient(test_app)
        
        response = client.get(
            "/protected",
            headers={"X-User-ID": "admin_user"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"message": "protected resource"}
    
    @patch('fastapi_microservices_sdk.security.advanced.abac.DefaultAttributeProvider.get_user_attributes')
    def test_middleware_denies_regular_user(self, mock_get_user_attrs, test_app):
        """Test that middleware denies regular user."""
        # Mock user attributes to return regular role
        mock_get_user_attrs.return_value = asyncio.create_task(asyncio.coroutine(lambda: {
            "role": AttributeValue("user", "string", "test")
        })())
        
        client = TestClient(test_app)
        
        response = client.get(
            "/protected",
            headers={"X-User-ID": "regular_user"}
        )
        
        assert response.status_code == 403
        assert "Access Denied" in response.json()["detail"]["error"]
    
    def test_middleware_denies_anonymous_user(self, test_app):
        """Test that middleware denies anonymous user."""
        client = TestClient(test_app)
        
        response = client.get("/protected")
        
        assert response.status_code == 403
        assert "Access Denied" in response.json()["detail"]["error"]
    
    @patch('fastapi_microservices_sdk.security.advanced.abac.DefaultAttributeProvider.get_user_attributes')
    def test_abac_protected_decorator(self, mock_get_user_attrs, test_app):
        """Test ABAC protected decorator functionality."""
        # Mock user attributes to return admin role
        mock_get_user_attrs.return_value = asyncio.create_task(asyncio.coroutine(lambda: {
            "role": AttributeValue("admin", "string", "test")
        })())
        
        client = TestClient(test_app)
        
        response = client.get(
            "/users/123",
            headers={"X-User-ID": "admin_user"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "123"
        assert data["decision"] is not None
        assert data["decision"]["decision"] == "allow"
    
    def test_get_abac_decision_helper(self, test_app):
        """Test get_abac_decision helper function."""
        # This is tested indirectly through the /users/{id} endpoint
        # which uses get_abac_decision in its implementation
        pass


class TestDatabaseAttributeProvider:
    """Test cases for DatabaseAttributeProvider."""
    
    @pytest.fixture
    def db_provider(self):
        """Create database attribute provider for testing."""
        return DatabaseAttributeProvider(cache_ttl=60)
    
    @pytest.mark.asyncio
    async def test_get_user_attributes_with_caching(self, db_provider):
        """Test user attributes retrieval with caching."""
        # First call
        attrs1 = await db_provider.get_user_attributes("user123")
        
        assert "id" in attrs1
        assert attrs1["id"].value == "user123"
        assert "authenticated" in attrs1
        
        # Second call should use cache
        attrs2 = await db_provider.get_user_attributes("user123")
        
        # Should be the same object (cached)
        assert attrs1 is attrs2
    
    @pytest.mark.asyncio
    async def test_get_resource_attributes_with_caching(self, db_provider):
        """Test resource attributes retrieval with caching."""
        attrs = await db_provider.get_resource_attributes("resource456")
        
        assert "id" in attrs
        assert attrs["id"].value == "resource456"
        assert "type" in attrs
    
    @pytest.mark.asyncio
    async def test_get_environment_attributes_enhanced(self, db_provider):
        """Test enhanced environment attributes."""
        context = {
            "source_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0 (Mobile)",
            "session_id": "session_123"
        }
        
        attrs = await db_provider.get_environment_attributes(context)
        
        assert "current_time" in attrs
        assert "is_business_hours" in attrs
        assert "is_weekend" in attrs
        assert "source_ip" in attrs
        assert attrs["source_ip"].value == "192.168.1.1"
        assert "is_internal_ip" in attrs
        assert attrs["is_internal_ip"].value is True  # 192.168.x.x is internal
        assert "user_agent" in attrs
        assert "is_mobile" in attrs
        assert attrs["is_mobile"].value is True  # Contains "Mobile"
    
    @pytest.mark.asyncio
    async def test_get_action_attributes_enhanced(self, db_provider):
        """Test enhanced action attributes with risk levels."""
        # Test read action
        read_attrs = await db_provider.get_action_attributes("get_users")
        assert read_attrs["category"].value == "read"
        assert read_attrs["risk_level"].value == "low"
        
        # Test create action
        create_attrs = await db_provider.get_action_attributes("create_user")
        assert create_attrs["category"].value == "create"
        assert create_attrs["risk_level"].value == "medium"
        
        # Test delete action
        delete_attrs = await db_provider.get_action_attributes("delete_user")
        assert delete_attrs["category"].value == "delete"
        assert delete_attrs["risk_level"].value == "high"
        
        # Test admin action
        admin_attrs = await db_provider.get_action_attributes("admin_configure")
        assert admin_attrs["category"].value == "admin"
        assert admin_attrs["risk_level"].value == "critical"


class TestCompositeAttributeProvider:
    """Test cases for CompositeAttributeProvider."""
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock attribute providers."""
        provider1 = Mock()
        provider1.get_user_attributes = AsyncMock(return_value={
            "role": AttributeValue("admin", "string", "provider1")
        })
        provider1.get_resource_attributes = AsyncMock(return_value={
            "type": AttributeValue("document", "string", "provider1")
        })
        provider1.get_environment_attributes = AsyncMock(return_value={
            "location": AttributeValue("office", "string", "provider1")
        })
        provider1.get_action_attributes = AsyncMock(return_value={
            "category": AttributeValue("read", "string", "provider1")
        })
        
        provider2 = Mock()
        provider2.get_user_attributes = AsyncMock(return_value={
            "department": AttributeValue("IT", "string", "provider2")
        })
        provider2.get_resource_attributes = AsyncMock(return_value={
            "classification": AttributeValue("public", "string", "provider2")
        })
        provider2.get_environment_attributes = AsyncMock(return_value={
            "time_of_day": AttributeValue("morning", "string", "provider2")
        })
        provider2.get_action_attributes = AsyncMock(return_value={
            "risk_level": AttributeValue("low", "string", "provider2")
        })
        
        return [provider1, provider2]
    
    @pytest.fixture
    def composite_provider(self, mock_providers):
        """Create composite attribute provider."""
        return CompositeAttributeProvider(mock_providers)
    
    @pytest.mark.asyncio
    async def test_merge_user_attributes(self, composite_provider):
        """Test merging user attributes from multiple providers."""
        attrs = await composite_provider.get_user_attributes("user123")
        
        assert "role" in attrs
        assert attrs["role"].value == "admin"
        assert "department" in attrs
        assert attrs["department"].value == "IT"
    
    @pytest.mark.asyncio
    async def test_merge_resource_attributes(self, composite_provider):
        """Test merging resource attributes from multiple providers."""
        attrs = await composite_provider.get_resource_attributes("resource456")
        
        assert "type" in attrs
        assert attrs["type"].value == "document"
        assert "classification" in attrs
        assert attrs["classification"].value == "public"
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self, mock_providers):
        """Test handling of provider failures."""
        # Make one provider fail
        mock_providers[0].get_user_attributes.side_effect = Exception("Provider failed")
        
        composite_provider = CompositeAttributeProvider(mock_providers)
        attrs = await composite_provider.get_user_attributes("user123")
        
        # Should still get attributes from working provider
        assert "department" in attrs
        assert attrs["department"].value == "IT"


class TestPolicyConflictResolver:
    """Test cases for PolicyConflictResolver."""
    
    @pytest.fixture
    def resolver(self):
        """Create policy conflict resolver."""
        return PolicyConflictResolver()
    
    @pytest.fixture
    def sample_decisions(self):
        """Create sample policy decisions for testing."""
        allow_decision = PolicyDecision(
            decision=PolicyEffect.ALLOW,
            policy_id="allow_policy",
            reason="Allow decision"
        )
        
        deny_decision = PolicyDecision(
            decision=PolicyEffect.DENY,
            policy_id="deny_policy",
            reason="Deny decision"
        )
        
        return [allow_decision, deny_decision]
    
    def test_deny_overrides_strategy(self, resolver, sample_decisions):
        """Test deny overrides conflict resolution."""
        result = resolver.resolve_conflicts(sample_decisions, "deny_overrides")
        
        assert result.decision == PolicyEffect.DENY
        assert result.policy_id == "deny_policy"
    
    def test_allow_overrides_strategy(self, resolver, sample_decisions):
        """Test allow overrides conflict resolution."""
        result = resolver.resolve_conflicts(sample_decisions, "allow_overrides")
        
        assert result.decision == PolicyEffect.ALLOW
        assert result.policy_id == "allow_policy"
    
    def test_first_applicable_strategy(self, resolver, sample_decisions):
        """Test first applicable conflict resolution."""
        result = resolver.resolve_conflicts(sample_decisions, "first_applicable")
        
        assert result.decision == PolicyEffect.ALLOW  # First in list
        assert result.policy_id == "allow_policy"
    
    def test_unanimous_strategy_all_allow(self, resolver):
        """Test unanimous strategy with all ALLOW decisions."""
        decisions = [
            PolicyDecision(PolicyEffect.ALLOW, "policy1", "Allow 1"),
            PolicyDecision(PolicyEffect.ALLOW, "policy2", "Allow 2")
        ]
        
        result = resolver.resolve_conflicts(decisions, "unanimous")
        
        assert result.decision == PolicyEffect.ALLOW
        assert "Unanimous ALLOW" in result.reason
    
    def test_unanimous_strategy_mixed_decisions(self, resolver, sample_decisions):
        """Test unanimous strategy with mixed decisions."""
        result = resolver.resolve_conflicts(sample_decisions, "unanimous")
        
        assert result.decision == PolicyEffect.DENY
        assert "No unanimous decision" in result.reason
    
    def test_majority_strategy_allow_wins(self, resolver):
        """Test majority strategy where ALLOW wins."""
        decisions = [
            PolicyDecision(PolicyEffect.ALLOW, "policy1", "Allow 1"),
            PolicyDecision(PolicyEffect.ALLOW, "policy2", "Allow 2"),
            PolicyDecision(PolicyEffect.DENY, "policy3", "Deny 1")
        ]
        
        result = resolver.resolve_conflicts(decisions, "majority")
        
        assert result.decision == PolicyEffect.ALLOW
        assert "Majority ALLOW" in result.reason
    
    def test_majority_strategy_tie(self, resolver, sample_decisions):
        """Test majority strategy with tie."""
        result = resolver.resolve_conflicts(sample_decisions, "majority")
        
        assert result.decision == PolicyEffect.DENY
        assert "Tie in majority vote" in result.reason
    
    def test_empty_decisions(self, resolver):
        """Test conflict resolution with empty decisions."""
        result = resolver.resolve_conflicts([], "deny_overrides")
        
        assert result.decision == PolicyEffect.DENY
        assert "No decisions to resolve" in result.reason
    
    def test_single_decision(self, resolver):
        """Test conflict resolution with single decision."""
        decision = PolicyDecision(PolicyEffect.ALLOW, "single", "Single decision")
        result = resolver.resolve_conflicts([decision], "deny_overrides")
        
        assert result.decision == PolicyEffect.ALLOW
        assert result.policy_id == "single"


class TestABACEngineBuilder:
    """Test cases for ABACEngineBuilder."""
    
    def test_builder_pattern(self):
        """Test ABAC engine builder pattern."""
        policy_store = PolicyStore()
        provider = DatabaseAttributeProvider()
        
        engine = (ABACEngineBuilder()
                 .with_policy_store(policy_store)
                 .with_attribute_provider(provider)
                 .with_cache_ttl(600)
                 .build())
        
        assert engine._policy_store is policy_store
        assert engine._attribute_provider is provider
        assert engine._cache_ttl == 600
    
    def test_builder_with_database_provider(self):
        """Test builder with database provider."""
        engine = (ABACEngineBuilder()
                 .with_database_provider()
                 .build())
        
        assert isinstance(engine._attribute_provider, DatabaseAttributeProvider)
    
    def test_builder_with_composite_provider(self):
        """Test builder with composite provider."""
        providers = [DatabaseAttributeProvider()]
        
        engine = (ABACEngineBuilder()
                 .with_composite_provider(providers)
                 .build())
        
        assert isinstance(engine._attribute_provider, CompositeAttributeProvider)


class TestABACFactory:
    """Test cases for ABAC factory functions."""
    
    def test_create_abac_engine_default(self):
        """Test creating ABAC engine with defaults."""
        engine = create_abac_engine()
        
        assert engine is not None
        assert engine._cache_ttl == 300
        assert engine._policy_store is not None
        assert engine._attribute_provider is not None
    
    def test_create_abac_engine_with_config(self):
        """Test creating ABAC engine with custom config."""
        engine = create_abac_engine(
            cache_ttl=600,
            precedence_rule="allow_overrides"
        )
        
        assert engine._cache_ttl == 600
    
    @patch('fastapi_microservices_sdk.security.advanced.abac.PolicyStore.load_policies_from_directory')
    def test_create_abac_engine_with_policy_directory(self, mock_load):
        """Test creating ABAC engine with policy directory."""
        engine = create_abac_engine(policy_directory="./test_policies")
        
        mock_load.assert_called_once_with("./test_policies")


if __name__ == "__main__":
    pytest.main([__file__])
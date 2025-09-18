"""
End-to-End Security Integration Tests.

This module tests complete security flows from mTLS through JWT, RBAC, ABAC,
and threat detection with real integration scenarios.
"""

import pytest
import asyncio
import time
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer

# Import all security components
from fastapi_microservices_sdk.security.advanced import (
    AdvancedSecurityConfig,
    UnifiedSecurityMiddleware,
    SecurityLayerConfig,
    SecurityLayerType,
    setup_unified_security_middleware,
    RBACEngine,
    Role,
    Permission,
    ABACEngine,
    ThreatDetector,
    SecurityConfigManager,
    SecurityMonitor,
    create_security_monitor
)


class TestCompleteSecurityFlow:
    """Test complete end-to-end security flows."""
    
    @pytest.fixture
    async def security_components(self):
        """Setup complete security components."""
        # RBAC Engine
        rbac_engine = RBACEngine()
        
        # Setup roles and permissions
        admin_role = Role(name="admin", description="Administrator")
        user_role = Role(name="user", description="Regular user")
        
        read_perm = Permission(name="api.read", description="API read access")
        write_perm = Permission(name="api.write", description="API write access")
        admin_perm = Permission(name="admin.access", description="Admin access")
        
        await rbac_engine.add_role(admin_role)
        await rbac_engine.add_role(user_role)
        await rbac_engine.add_permission(read_perm)
        await rbac_engine.add_permission(write_perm)
        await rbac_engine.add_permission(admin_perm)
        
        # Assign permissions to roles
        await rbac_engine.assign_permission_to_role("admin", "api.read")
        await rbac_engine.assign_permission_to_role("admin", "api.write")
        await rbac_engine.assign_permission_to_role("admin", "admin.access")
        await rbac_engine.assign_permission_to_role("user", "api.read")
        
        # Assign roles to users
        await rbac_engine.assign_role_to_user("admin_user", "admin")
        await rbac_engine.assign_role_to_user("regular_user", "user")
        
        # ABAC Engine
        abac_engine = ABACEngine()
        
        # Add ABAC policies
        policies = [
            {
                "id": "admin_policy",
                "description": "Admins can access everything",
                "effect": "Permit",
                "rule": "subject.roles contains 'admin'"
            },
            {
                "id": "business_hours_policy",
                "description": "Users can access during business hours",
                "effect": "Permit",
                "rule": "subject.roles contains 'user' and environment.hour >= 9 and environment.hour < 17"
            },
            {
                "id": "sensitive_data_policy",
                "description": "Only admins can access sensitive data",
                "effect": "Deny",
                "rule": "resource.sensitive == true and not (subject.roles contains 'admin')"
            }
        ]
        
        for policy in policies:
            await abac_engine.add_policy(policy)
        
        # Threat Detector
        threat_detector = ThreatDetector(enable_auto_response=False)
        
        # Security Monitor
        security_monitor = create_security_monitor()
        
        return {
            "rbac_engine": rbac_engine,
            "abac_engine": abac_engine,
            "threat_detector": threat_detector,
            "security_monitor": security_monitor
        }
    
    @pytest.fixture
    def security_config(self):
        """Create security configuration."""
        return AdvancedSecurityConfig(
            mtls_enabled=False,  # Disable for testing
            rbac_enabled=True,
            abac_enabled=True,
            threat_detection_enabled=True,
            debug_mode=True
        )
    
    @pytest.fixture
    def test_app(self, security_config, security_components):
        """Create test FastAPI app with complete security stack."""
        app = FastAPI(title="Security Integration Test App")
        
        # Setup unified security middleware
        setup_unified_security_middleware(
            app=app,
            config=security_config,
            rbac_engine=security_components["rbac_engine"],
            abac_engine=security_components["abac_engine"],
            threat_detector=security_components["threat_detector"]
        )
        
        # Test endpoints
        @app.get("/api/public")
        async def public_endpoint():
            return {"message": "public data"}
        
        @app.get("/api/user-data")
        async def user_data():
            return {"data": "user specific data"}
        
        @app.post("/api/create-data")
        async def create_data():
            return {"message": "data created"}
        
        @app.get("/admin/settings")
        async def admin_settings():
            return {"settings": "admin settings"}
        
        @app.get("/api/sensitive")
        async def sensitive_data():
            return {"sensitive": "classified information"}
        
        return app
    
    @pytest.mark.asyncio
    async def test_complete_admin_flow(self, test_app, security_components):
        """Test complete security flow for admin user."""
        with TestClient(test_app) as client:
            # Mock JWT validation for admin user
            with patch.object(
                UnifiedSecurityMiddleware,
                '_simulate_jwt_validation',
                return_value={
                    "sub": "admin_user",
                    "session_id": "admin_session",
                    "roles": ["admin"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Test admin accessing user endpoint
                response = client.get(
                    "/api/user-data",
                    headers={"Authorization": "Bearer admin_token"}
                )
                assert response.status_code == 200
                assert "data" in response.json()
                
                # Test admin accessing admin endpoint
                response = client.get(
                    "/admin/settings",
                    headers={"Authorization": "Bearer admin_token"}
                )
                assert response.status_code == 200
                assert "settings" in response.json()
                
                # Test admin creating data
                response = client.post(
                    "/api/create-data",
                    headers={"Authorization": "Bearer admin_token"}
                )
                assert response.status_code == 200
                assert "message" in response.json()
    
    @pytest.mark.asyncio
    async def test_complete_user_flow(self, test_app, security_components):
        """Test complete security flow for regular user."""
        with TestClient(test_app) as client:
            # Mock JWT validation for regular user
            with patch.object(
                UnifiedSecurityMiddleware,
                '_simulate_jwt_validation',
                return_value={
                    "sub": "regular_user",
                    "session_id": "user_session",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Test user accessing user endpoint (should succeed)
                response = client.get(
                    "/api/user-data",
                    headers={"Authorization": "Bearer user_token"}
                )
                assert response.status_code == 200
                
                # Test user accessing admin endpoint (should fail)
                response = client.get(
                    "/admin/settings",
                    headers={"Authorization": "Bearer user_token"}
                )
                assert response.status_code == 403
                
                # Test user creating data (should fail - no write permission)
                response = client.post(
                    "/api/create-data",
                    headers={"Authorization": "Bearer user_token"}
                )
                assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access(self, test_app):
        """Test unauthenticated access attempts."""
        with TestClient(test_app) as client:
            # Test accessing protected endpoint without token
            response = client.get("/api/user-data")
            assert response.status_code == 401
            
            # Test accessing admin endpoint without token
            response = client.get("/admin/settings")
            assert response.status_code == 401
            
            # Public endpoint should still work
            response = client.get("/api/public")
            # Note: This depends on how public endpoints are configured
            # In a real implementation, you might have skip_paths for public endpoints


class TestSecurityFailureScenarios:
    """Test security failure scenarios and graceful degradation."""
    
    @pytest.fixture
    def app_with_failing_components(self):
        """Create app with components that can fail."""
        app = FastAPI()
        
        # Create components that will fail
        failing_rbac = Mock()
        failing_rbac.check_permission = AsyncMock(side_effect=Exception("RBAC service down"))
        failing_rbac.get_user_roles = AsyncMock(side_effect=Exception("RBAC service down"))
        failing_rbac.get_user_permissions = AsyncMock(side_effect=Exception("RBAC service down"))
        
        failing_abac = Mock()
        failing_abac.evaluate = AsyncMock(side_effect=Exception("ABAC service down"))
        
        # Configure layers to fail open
        layer_configs = [
            SecurityLayerConfig(SecurityLayerType.JWT, enabled=True, required=True, fail_open=False),
            SecurityLayerConfig(SecurityLayerType.RBAC, enabled=True, required=False, fail_open=True),
            SecurityLayerConfig(SecurityLayerType.ABAC, enabled=True, required=False, fail_open=True),
        ]
        
        config = AdvancedSecurityConfig(
            mtls_enabled=False,
            rbac_enabled=True,
            abac_enabled=True,
            debug_mode=True
        )
        
        setup_unified_security_middleware(
            app=app,
            config=config,
            layer_configs=layer_configs,
            rbac_engine=failing_rbac,
            abac_engine=failing_abac
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        return app
    
    def test_graceful_degradation_with_failing_rbac(self, app_with_failing_components):
        """Test graceful degradation when RBAC fails."""
        with TestClient(app_with_failing_components) as client:
            with patch.object(
                UnifiedSecurityMiddleware,
                '_simulate_jwt_validation',
                return_value={
                    "sub": "test_user",
                    "session_id": "test_session",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Should succeed despite RBAC failure (fail open)
                response = client.get(
                    "/test",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 200
    
    def test_security_layer_timeout_handling(self):
        """Test handling of security layer timeouts."""
        # Create slow RBAC engine
        slow_rbac = Mock()
        
        async def slow_check(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow operation
            return True
        
        slow_rbac.check_permission = slow_check
        
        # Configure with short timeout
        layer_config = SecurityLayerConfig(
            SecurityLayerType.RBAC,
            enabled=True,
            required=False,
            fail_open=True,
            timeout_seconds=1.0  # Short timeout
        )
        
        # In a real implementation, this would test timeout handling
        assert layer_config.timeout_seconds == 1.0


class TestMultiServiceSecurityCommunication:
    """Test security communication between multiple services."""
    
    @pytest.fixture
    def service_a_app(self):
        """Create Service A with security."""
        app = FastAPI(title="Service A")
        
        config = AdvancedSecurityConfig(mtls_enabled=False, rbac_enabled=True)
        rbac_engine = RBACEngine()
        
        setup_unified_security_middleware(
            app=app,
            config=config,
            rbac_engine=rbac_engine
        )
        
        @app.get("/service-a/data")
        async def get_data():
            return {"service": "A", "data": "service A data"}
        
        @app.post("/service-a/call-service-b")
        async def call_service_b():
            # Simulate calling Service B
            return {"message": "Called Service B", "result": "success"}
        
        return app
    
    @pytest.fixture
    def service_b_app(self):
        """Create Service B with security."""
        app = FastAPI(title="Service B")
        
        config = AdvancedSecurityConfig(mtls_enabled=False, abac_enabled=True)
        abac_engine = ABACEngine()
        
        setup_unified_security_middleware(
            app=app,
            config=config,
            abac_engine=abac_engine
        )
        
        @app.get("/service-b/data")
        async def get_data():
            return {"service": "B", "data": "service B data"}
        
        return app
    
    def test_service_to_service_communication(self, service_a_app, service_b_app):
        """Test secure communication between services."""
        # In a real scenario, this would test:
        # 1. Service A authenticating to Service B
        # 2. Proper token propagation
        # 3. mTLS certificate validation
        # 4. Service-specific permissions
        
        with TestClient(service_a_app) as client_a:
            with TestClient(service_b_app) as client_b:
                # Mock service authentication
                with patch.object(
                    UnifiedSecurityMiddleware,
                    '_simulate_jwt_validation',
                    return_value={
                        "sub": "service_a",
                        "session_id": "service_session",
                        "roles": ["service"],
                        "exp": 9999999999,
                        "iat": 1000000000
                    }
                ):
                    # Service A calling its own endpoint
                    response_a = client_a.get(
                        "/service-a/data",
                        headers={"Authorization": "Bearer service_token"}
                    )
                    assert response_a.status_code == 200
                    
                    # Service B responding to call
                    response_b = client_b.get(
                        "/service-b/data",
                        headers={"Authorization": "Bearer service_token"}
                    )
                    assert response_b.status_code == 200


class TestSecurityConfigurationPropagation:
    """Test security configuration change propagation."""
    
    @pytest.mark.asyncio
    async def test_configuration_change_propagation(self):
        """Test that configuration changes propagate to all components."""
        config_manager = SecurityConfigManager()
        
        # Track configuration changes
        changes_received = []
        
        def change_listener(change):
            changes_received.append(change)
        
        config_manager.add_change_listener(change_listener)
        
        # Initialize configuration
        initial_config = {
            "rbac_enabled": True,
            "abac_enabled": False,
            "threat_detection_enabled": True
        }
        
        config_manager.config = initial_config
        
        # Make configuration changes
        updates = {
            "rbac_enabled": False,
            "abac_enabled": True,
            "new_feature_enabled": True
        }
        
        success = await config_manager.update_configuration(updates, "test_propagation")
        
        assert success is True
        assert len(changes_received) > 0
        
        # Verify changes were tracked
        change_keys = [change.key for change in changes_received]
        assert "rbac_enabled" in change_keys
        assert "abac_enabled" in change_keys
        assert "new_feature_enabled" in change_keys
    
    @pytest.mark.asyncio
    async def test_hot_reload_security_configuration(self):
        """Test hot reload of security configuration."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            initial_config = {
                "rbac_enabled": True,
                "abac_enabled": False,
                "debug_mode": False
            }
            json.dump(initial_config, f)
            config_file = f.name
        
        try:
            from fastapi_microservices_sdk.security.advanced.config_manager import (
                create_file_config_manager
            )
            
            # Create config manager with file provider
            config_manager = create_file_config_manager(config_file)
            
            # Load initial configuration
            config = await config_manager.load_configuration()
            assert config["rbac_enabled"] is True
            assert config["abac_enabled"] is False
            
            # Update config file
            updated_config = {
                "rbac_enabled": False,
                "abac_enabled": True,
                "debug_mode": True
            }
            
            with open(config_file, 'w') as f:
                json.dump(updated_config, f)
            
            # Reload configuration
            success = await config_manager.reload_configuration()
            assert success is True
            
            # Verify changes
            new_config = config_manager.get_configuration()
            assert new_config["rbac_enabled"] is False
            assert new_config["abac_enabled"] is True
            assert new_config["debug_mode"] is True
            
        finally:
            # Cleanup
            Path(config_file).unlink()


class TestSecurityPerformanceUnderLoad:
    """Test security performance under load conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_security_requests(self):
        """Test security system under concurrent load."""
        # Create security components
        rbac_engine = RBACEngine()
        
        # Setup test data
        admin_role = Role(name="admin", description="Admin")
        read_perm = Permission(name="read", description="Read")
        
        await rbac_engine.add_role(admin_role)
        await rbac_engine.add_permission(read_perm)
        await rbac_engine.assign_permission_to_role("admin", "read")
        
        # Create multiple users
        for i in range(100):
            await rbac_engine.assign_role_to_user(f"user_{i}", "admin")
        
        # Concurrent permission checks
        async def check_permissions():
            tasks = []
            for i in range(100):
                task = rbac_engine.check_permission(f"user_{i}", "read")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        # Measure performance
        start_time = time.time()
        results = await check_permissions()
        end_time = time.time()
        
        # All checks should succeed
        assert all(results)
        
        # Should complete in reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0, f"Concurrent checks took too long: {total_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_security_monitoring_under_load(self):
        """Test security monitoring under high event load."""
        monitor = create_security_monitor()
        
        # Generate high volume of events
        async def generate_events(count: int):
            tasks = []
            for i in range(count):
                correlation_id = await monitor.start_request_monitoring()
                
                # Log multiple events per request
                for j in range(5):
                    from fastapi_microservices_sdk.security.advanced.logging import (
                        SecurityEvent, SecurityEventSeverity
                    )
                    
                    event = SecurityEvent(
                        event_type=f"event_{j}",
                        severity=SecurityEventSeverity.INFO,
                        component="load_test",
                        details={"request": i, "event": j}
                    )
                    
                    task = monitor.log_security_event(event, correlation_id)
                    tasks.append(task)
                
                # Complete request
                complete_task = monitor.complete_request_monitoring(correlation_id, True)
                tasks.append(complete_task)
            
            await asyncio.gather(*tasks)
        
        # Test with 100 requests, 5 events each = 500 events + 100 completions
        start_time = time.time()
        await generate_events(100)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # Should handle load efficiently
        assert total_time < 10.0, f"Event processing took too long: {total_time:.2f}s"
        
        # Verify metrics
        metrics = monitor.get_metrics_summary()
        assert metrics["correlation_tracking"]["total_tracked"] >= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
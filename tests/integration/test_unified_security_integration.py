"""
Integration tests for Unified Security Middleware.

This module tests the complete security stack integration with real
FastAPI applications and end-to-end request flows.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastapi_microservices_sdk.security.advanced.unified_middleware import (
    UnifiedSecurityMiddleware,
    SecurityLayerType,
    SecurityLayerConfig,
    setup_unified_security_middleware,
    create_default_layer_configs
)
from fastapi_microservices_sdk.security.advanced.config import AdvancedSecurityConfig
from fastapi_microservices_sdk.security.advanced.rbac import RBACEngine, Role, Permission
from fastapi_microservices_sdk.security.advanced.abac import ABACEngine, ABACDecision
from fastapi_microservices_sdk.security.advanced.threat_detection import ThreatDetector, ThreatAssessment, ThreatLevel


class TestCompleteSecurityStack:
    """Test suite for complete security stack integration."""
    
    @pytest.fixture
    def security_config(self):
        """Create security configuration for testing."""
        return AdvancedSecurityConfig(
            mtls_enabled=False,  # Disable mTLS for simpler testing
            rbac_enabled=True,
            abac_enabled=True,
            threat_detection_enabled=True,
            debug_mode=True,
            log_level="DEBUG"
        )
    
    @pytest.fixture
    def rbac_engine(self):
        """Create RBAC engine with test data."""
        engine = RBACEngine()
        
        # Setup test roles and permissions
        admin_role = Role(name="admin", description="Administrator role")
        user_role = Role(name="user", description="Regular user role")
        
        read_perm = Permission(name="api.get", description="Read API access")
        write_perm = Permission(name="api.post", description="Write API access")
        admin_perm = Permission(name="admin.get", description="Admin access")
        
        # Add roles and permissions
        asyncio.run(engine.add_role(admin_role))
        asyncio.run(engine.add_role(user_role))
        asyncio.run(engine.add_permission(read_perm))
        asyncio.run(engine.add_permission(write_perm))
        asyncio.run(engine.add_permission(admin_perm))
        
        # Assign permissions to roles
        asyncio.run(engine.assign_permission_to_role("admin", "api.get"))
        asyncio.run(engine.assign_permission_to_role("admin", "api.post"))
        asyncio.run(engine.assign_permission_to_role("admin", "admin.get"))
        asyncio.run(engine.assign_permission_to_role("user", "api.get"))
        
        # Assign roles to users
        asyncio.run(engine.assign_role_to_user("admin_user", "admin"))
        asyncio.run(engine.assign_role_to_user("regular_user", "user"))
        
        return engine
    
    @pytest.fixture
    def abac_engine(self):
        """Create ABAC engine with test policies."""
        engine = ABACEngine()
        
        # Add test policies
        admin_policy = {
            "id": "admin_access",
            "description": "Admin users can access admin endpoints",
            "target": {
                "subject": {"roles": ["admin"]},
                "resource": {"path": "/admin/*"}
            },
            "rule": "subject.roles contains 'admin' and resource.path starts_with '/admin'",
            "effect": "Permit"
        }
        
        user_policy = {
            "id": "user_access",
            "description": "Users can access API endpoints during business hours",
            "target": {
                "subject": {"roles": ["user", "admin"]},
                "resource": {"path": "/api/*"}
            },
            "rule": "subject.roles contains 'user' or subject.roles contains 'admin'",
            "effect": "Permit"
        }
        
        asyncio.run(engine.add_policy(admin_policy))
        asyncio.run(engine.add_policy(user_policy))
        
        return engine
    
    @pytest.fixture
    def threat_detector(self):
        """Create threat detector for testing."""
        return ThreatDetector(enable_auto_response=False)
    
    @pytest.fixture
    def test_app(self, security_config, rbac_engine, abac_engine, threat_detector):
        """Create test FastAPI application with security middleware."""
        app = FastAPI(title="Test Security App")
        
        # Setup security middleware
        setup_unified_security_middleware(
            app=app,
            config=security_config,
            rbac_engine=rbac_engine,
            abac_engine=abac_engine,
            threat_detector=threat_detector
        )
        
        # Test endpoints
        @app.get("/api/data")
        async def get_data():
            return {"data": "public data"}
        
        @app.post("/api/data")
        async def create_data():
            return {"message": "data created"}
        
        @app.get("/admin/users")
        async def get_users():
            return {"users": ["admin_user", "regular_user"]}
        
        @app.get("/public/info")
        async def get_info():
            return {"info": "public information"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        return app
    
    def test_successful_admin_request(self, test_app):
        """Test successful admin request through complete security stack."""
        with TestClient(test_app) as client:
            # Mock JWT token for admin user
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "admin_user",
                    "session_id": "admin_session_123",
                    "roles": ["admin"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/admin/users",
                    headers={"Authorization": "Bearer admin_token"}
                )
                
                assert response.status_code == 200
                assert response.json() == {"users": ["admin_user", "regular_user"]}
                assert "X-Request-ID" in response.headers
    
    def test_successful_user_request(self, test_app):
        """Test successful user request through complete security stack."""
        with TestClient(test_app) as client:
            # Mock JWT token for regular user
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "regular_user",
                    "session_id": "user_session_456",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/api/data",
                    headers={"Authorization": "Bearer user_token"}
                )
                
                assert response.status_code == 200
                assert response.json() == {"data": "public data"}
                assert "X-Request-ID" in response.headers
    
    def test_rbac_authorization_failure(self, test_app):
        """Test RBAC authorization failure."""
        with TestClient(test_app) as client:
            # Mock JWT token for user trying to access admin endpoint
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "regular_user",
                    "session_id": "user_session_456",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/admin/users",
                    headers={"Authorization": "Bearer user_token"}
                )
                
                assert response.status_code == 403
                assert "authorization_error" in response.json()["error"]
                assert "X-Request-ID" in response.headers
    
    def test_jwt_authentication_failure(self, test_app):
        """Test JWT authentication failure."""
        with TestClient(test_app) as client:
            # Request without JWT token
            response = client.get("/api/data")
            
            assert response.status_code == 401
            assert "authentication_error" in response.json()["error"]
            assert "X-Request-ID" in response.headers
    
    def test_abac_authorization_success(self, test_app):
        """Test ABAC authorization success."""
        with TestClient(test_app) as client:
            # Mock JWT token for admin user accessing API
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "admin_user",
                    "session_id": "admin_session_123",
                    "roles": ["admin"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/api/data",
                    headers={"Authorization": "Bearer admin_token"}
                )
                
                assert response.status_code == 200
                assert response.json() == {"data": "public data"}
    
    def test_threat_detection_integration(self, test_app):
        """Test threat detection integration."""
        with TestClient(test_app) as client:
            # Mock JWT token
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "regular_user",
                    "session_id": "user_session_456",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Mock threat assessment with high threat level
                mock_assessment = Mock()
                mock_assessment.assessment_id = "threat_123"
                mock_assessment.detected_threats = []  # No threats for successful test
                mock_assessment.threat_level = Mock()
                mock_assessment.threat_level.value = "LOW"
                mock_assessment.confidence = 0.1
                
                with patch.object(
                    ThreatDetector,
                    'analyze_session_event',
                    return_value=mock_assessment
                ):
                    response = client.get(
                        "/api/data",
                        headers={"Authorization": "Bearer user_token"}
                    )
                    
                    assert response.status_code == 200
                    assert response.json() == {"data": "public data"}
    
    def test_high_threat_blocking(self, test_app):
        """Test blocking of high-threat requests."""
        with TestClient(test_app) as client:
            # Mock JWT token
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "suspicious_user",
                    "session_id": "suspicious_session",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Mock threat assessment with high threat level
                from fastapi_microservices_sdk.security.advanced.threat_detection import ThreatType
                
                mock_assessment = Mock()
                mock_assessment.assessment_id = "threat_456"
                mock_assessment.detected_threats = [ThreatType.BRUTE_FORCE]
                mock_assessment.threat_level = Mock()
                mock_assessment.threat_level.value = "CRITICAL"
                mock_assessment.confidence = 0.95
                
                with patch.object(
                    ThreatDetector,
                    'analyze_session_event',
                    return_value=mock_assessment
                ):
                    response = client.get(
                        "/api/data",
                        headers={"Authorization": "Bearer suspicious_token"}
                    )
                    
                    assert response.status_code == 429  # Too Many Requests
                    assert "threat_detected" in response.json()["error"]
    
    def test_security_headers_added(self, test_app):
        """Test that security headers are added to responses."""
        with TestClient(test_app) as client:
            # Mock JWT token
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "regular_user",
                    "session_id": "user_session_456",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/api/data",
                    headers={"Authorization": "Bearer user_token"}
                )
                
                assert response.status_code == 200
                assert "X-Request-ID" in response.headers
                
                # Check debug headers (when debug mode is enabled)
                assert "X-Security-Jwt" in response.headers
                assert "X-Security-Rbac" in response.headers
                assert "X-Security-Abac" in response.headers
                assert "X-Security-Threat-Detection" in response.headers
    
    def test_multiple_concurrent_requests(self, test_app):
        """Test handling multiple concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            with TestClient(test_app) as client:
                with patch.object(
                    UnifiedSecurityMiddleware, 
                    '_simulate_jwt_validation',
                    return_value={
                        "sub": "regular_user",
                        "session_id": f"session_{threading.current_thread().ident}",
                        "roles": ["user"],
                        "exp": 9999999999,
                        "iat": 1000000000
                    }
                ):
                    response = client.get(
                        "/api/data",
                        headers={"Authorization": "Bearer user_token"}
                    )
                    results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5


class TestSecurityLayerFailures:
    """Test suite for security layer failure scenarios."""
    
    @pytest.fixture
    def security_config(self):
        """Create security configuration for failure testing."""
        return AdvancedSecurityConfig(
            mtls_enabled=False,
            rbac_enabled=True,
            abac_enabled=True,
            threat_detection_enabled=True,
            debug_mode=True,
            log_level="DEBUG"
        )
    
    @pytest.fixture
    def failing_rbac_engine(self):
        """Create RBAC engine that fails."""
        engine = Mock()
        engine.check_permission = AsyncMock(side_effect=Exception("RBAC service unavailable"))
        engine.get_user_roles = AsyncMock(side_effect=Exception("RBAC service unavailable"))
        engine.get_user_permissions = AsyncMock(side_effect=Exception("RBAC service unavailable"))
        return engine
    
    @pytest.fixture
    def failing_abac_engine(self):
        """Create ABAC engine that fails."""
        engine = Mock()
        engine.evaluate = AsyncMock(side_effect=Exception("ABAC service unavailable"))
        return engine
    
    def test_rbac_failure_with_fail_open(self, security_config):
        """Test RBAC failure with fail-open configuration."""
        app = FastAPI()
        
        # Configure RBAC to fail open
        layer_configs = [
            SecurityLayerConfig(SecurityLayerType.JWT, enabled=True, required=True),
            SecurityLayerConfig(SecurityLayerType.RBAC, enabled=True, required=False, fail_open=True),
        ]
        
        failing_rbac = Mock()
        failing_rbac.check_permission = AsyncMock(side_effect=Exception("RBAC unavailable"))
        
        setup_unified_security_middleware(
            app=app,
            config=security_config,
            layer_configs=layer_configs,
            rbac_engine=failing_rbac
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        with TestClient(app) as client:
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "user123",
                    "session_id": "session123",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/test",
                    headers={"Authorization": "Bearer token"}
                )
                
                # Should succeed despite RBAC failure (fail open)
                assert response.status_code == 200
                assert response.json() == {"message": "success"}
    
    def test_rbac_failure_with_fail_closed(self, security_config):
        """Test RBAC failure with fail-closed configuration."""
        app = FastAPI()
        
        # Configure RBAC to fail closed
        layer_configs = [
            SecurityLayerConfig(SecurityLayerType.JWT, enabled=True, required=True),
            SecurityLayerConfig(SecurityLayerType.RBAC, enabled=True, required=True, fail_open=False),
        ]
        
        failing_rbac = Mock()
        failing_rbac.check_permission = AsyncMock(side_effect=Exception("RBAC unavailable"))
        
        setup_unified_security_middleware(
            app=app,
            config=security_config,
            layer_configs=layer_configs,
            rbac_engine=failing_rbac
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        with TestClient(app) as client:
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "user123",
                    "session_id": "session123",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                response = client.get(
                    "/test",
                    headers={"Authorization": "Bearer token"}
                )
                
                # Should fail due to RBAC failure (fail closed)
                assert response.status_code == 403
                assert "authorization_error" in response.json()["error"]


class TestSecurityMetrics:
    """Test suite for security metrics collection."""
    
    def test_metrics_collection_during_requests(self):
        """Test that metrics are collected during request processing."""
        app = FastAPI()
        config = AdvancedSecurityConfig(
            mtls_enabled=False,
            rbac_enabled=False,
            abac_enabled=False,
            threat_detection_enabled=False,
            debug_mode=True
        )
        
        middleware = setup_unified_security_middleware(app=app, config=config)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        with TestClient(app) as client:
            with patch.object(
                UnifiedSecurityMiddleware, 
                '_simulate_jwt_validation',
                return_value={
                    "sub": "user123",
                    "session_id": "session123",
                    "roles": ["user"],
                    "exp": 9999999999,
                    "iat": 1000000000
                }
            ):
                # Make successful request
                response = client.get(
                    "/test",
                    headers={"Authorization": "Bearer token"}
                )
                assert response.status_code == 200
                
                # Make failed request (no auth)
                response = client.get("/test")
                assert response.status_code == 401
        
        # Check metrics
        metrics = middleware.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 1
        assert metrics["failed_requests"] == 1
        assert metrics["success_rate"] == 0.5
        assert metrics["average_processing_time"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
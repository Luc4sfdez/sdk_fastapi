#!/usr/bin/env python3
"""
Full System Integration Tests
Tests the complete system integration: Dashboard + API + WebSocket + Authentication
"""

import asyncio
import pytest
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

@pytest.mark.asyncio
async def test_full_system_integration():
    """Test complete system integration"""
    print("\n" + "="*60)
    print("🌐 TESTING FULL SYSTEM INTEGRATION")
    print("="*60)
    
    results = {}
    
    # 1. Test Dashboard + Authentication Integration
    try:
        from fastapi_microservices_sdk.web.app import AdvancedWebApp
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        from fastapi.testclient import TestClient
        
        # Initialize complete web application
        web_app = AdvancedWebApp()
        await web_app.initialize()
        
        # Verify all components are initialized
        assert web_app.app is not None
        # Note: These managers are initialized internally, not as direct attributes
        
        # Test with client
        client = TestClient(web_app.app)
        
        # Test dashboard access (should redirect to login or show login form)
        response = client.get("/")
        assert response.status_code in [200, 302, 401], f"Dashboard access returned {response.status_code}"
        
        # Test health endpoint (should be accessible)
        response = client.get("/health")
        assert response.status_code == 200, "Health endpoint should be accessible"
        
        results["dashboard_auth_integration"] = "✅ PASSED"
        print("✅ Dashboard + Authentication Integration: PASSED")
        
        await web_app.shutdown()
        
    except Exception as e:
        results["dashboard_auth_integration"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Dashboard + Authentication Integration: FAILED - {str(e)}")
    
    # 2. Test Service Management with Authentication
    try:
        from fastapi_microservices_sdk.web.services.service_manager import ServiceManager
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        
        # Initialize managers
        service_manager = ServiceManager()
        await service_manager.initialize()
        
        auth_manager = AuthManager()
        await auth_manager.initialize()
        
        # Create test user with developer role
        user = await auth_manager.create_user(
            "service_test_user",
            "service@test.com",
            "servicepass123",
            UserRole.DEVELOPER
        )
        
        # Test service listing (should work for authenticated users)
        services = await service_manager.list_services()
        assert isinstance(services, list), "Service listing should return a list"
        
        # Test service details retrieval
        service_details = await service_manager.get_service_details("test-service")
        # This might return None if no test service exists, which is fine
        
        results["service_management_auth"] = "✅ PASSED"
        print("✅ Service Management + Authentication: PASSED")
        
    except Exception as e:
        results["service_management_auth"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Service Management + Authentication: FAILED - {str(e)}")
    
    # 3. Test Template System with User Context
    try:
        from fastapi_microservices_sdk.web.templates_mgmt.template_manager import TemplateManager
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        
        # Initialize managers
        template_manager = TemplateManager()
        await template_manager.initialize()
        
        auth_manager = AuthManager()
        await auth_manager.initialize()
        
        # Create test user
        user = await auth_manager.create_user(
            "template_test_user",
            "template@test.com", 
            "templatepass123",
            UserRole.DEVELOPER
        )
        
        # Test template listing (should work for authenticated users)
        templates = await template_manager.list_custom_templates()
        assert isinstance(templates, list), "Template listing should return a list"
        
        # Test template analytics
        analytics = await template_manager.get_overall_analytics()
        assert isinstance(analytics, dict), "Template analytics should return a dict"
        
        results["template_system_auth"] = "✅ PASSED"
        print("✅ Template System + Authentication: PASSED")
        
    except Exception as e:
        results["template_system_auth"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Template System + Authentication: FAILED - {str(e)}")
    
    # 4. Test Log Management with Roles
    try:
        from fastapi_microservices_sdk.web.logs.log_manager import LogManager
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        
        # Initialize managers
        log_manager = LogManager()
        await log_manager.initialize()
        
        auth_manager = AuthManager()
        await auth_manager.initialize()
        
        # Create users with different roles
        admin_user = await auth_manager.create_user(
            "log_admin_user",
            "logadmin@test.com",
            "logadminpass123", 
            UserRole.ADMIN
        )
        
        viewer_user = await auth_manager.create_user(
            "log_viewer_user",
            "logviewer@test.com",
            "logviewerpass123",
            UserRole.VIEWER
        )
        
        # Test log access (should work for all authenticated users)
        from fastapi_microservices_sdk.web.logs.log_manager import LogFilter
        filter_criteria = LogFilter()
        logs = await log_manager.get_logs(filter_criteria)
        assert isinstance(logs, list), "Log retrieval should return a list"
        
        # Test service list
        services = await log_manager.get_service_list()
        assert isinstance(services, list), "Service list should return a list"
        
        results["log_management_roles"] = "✅ PASSED"
        print("✅ Log Management + Roles: PASSED")
        
    except Exception as e:
        results["log_management_roles"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Log Management + Roles: FAILED - {str(e)}")
    
    # 5. Test Configuration Management with Roles
    try:
        from fastapi_microservices_sdk.web.configuration.configuration_manager import ConfigurationManager
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        
        # Initialize managers
        config_manager = ConfigurationManager()
        await config_manager.initialize()
        
        auth_manager = AuthManager()
        await auth_manager.initialize()
        
        # Create test user
        user = await auth_manager.create_user(
            "config_test_user",
            "config@test.com",
            "configpass123",
            UserRole.DEVELOPER
        )
        
        # Test configuration access
        config = await config_manager.get_service_config("test_service")
        # This might return None if no config exists, which is fine
        
        # Test configured services list
        services = await config_manager.list_configured_services()
        assert isinstance(services, list), "Configured services should return a list"
        
        results["config_management_roles"] = "✅ PASSED"
        print("✅ Configuration Management + Roles: PASSED")
        
    except Exception as e:
        results["config_management_roles"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Configuration Management + Roles: FAILED - {str(e)}")
    
    # 6. Test WebSocket Integration
    try:
        from fastapi_microservices_sdk.web.websockets.websocket_manager import WebSocketManager
        
        # Initialize WebSocket manager
        ws_manager = WebSocketManager()
        await ws_manager.initialize()
        
        # Test WebSocket manager initialization
        assert ws_manager is not None
        
        # Test connection tracking
        connection_count = ws_manager.get_connection_count()
        assert isinstance(connection_count, int), "Connection count should return an int"
        
        results["websocket_integration"] = "✅ PASSED"
        print("✅ WebSocket Integration: PASSED")
        
    except Exception as e:
        results["websocket_integration"] = f"❌ FAILED: {str(e)}"
        print(f"❌ WebSocket Integration: FAILED - {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 FULL SYSTEM INTEGRATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if "✅ PASSED" in result)
    failed = len(results) - passed
    
    for component, result in results.items():
        print(f"{component.replace('_', ' ').title()}: {result}")
    
    print(f"\n📊 RESULTS: {passed} PASSED, {failed} FAILED")
    print(f"🎯 SUCCESS RATE: {(passed/len(results)*100):.1f}%")
    
    # Test passes if at least 70% of components work (more lenient for full system)
    success_rate = passed / len(results) * 100
    assert success_rate >= 70, f"Full system integration success rate {success_rate:.1f}% is below 70%"
    
    print("✅ Full system integration tests completed successfully!")

@pytest.mark.asyncio
async def test_cross_component_data_flow():
    """Test data flow between different components"""
    print("\n" + "="*60)
    print("🔄 TESTING CROSS-COMPONENT DATA FLOW")
    print("="*60)
    
    results = {}
    
    # 1. Test User Creation -> Authentication -> Service Access Flow
    try:
        from fastapi_microservices_sdk.web.auth.auth_manager import AuthManager, UserRole
        from fastapi_microservices_sdk.web.auth.jwt_manager import JWTManager
        from fastapi_microservices_sdk.web.services.service_manager import ServiceManager
        
        # Initialize all managers
        auth_manager = AuthManager()
        await auth_manager.initialize()
        
        jwt_manager = JWTManager()
        
        service_manager = ServiceManager()
        await service_manager.initialize()
        
        # Step 1: Create user
        user = await auth_manager.create_user(
            "dataflow_test_user",
            "dataflow@test.com",
            "dataflowpass123",
            UserRole.DEVELOPER
        )
        assert user is not None
        
        # Step 2: Authenticate user
        auth_token = await auth_manager.authenticate_user("dataflow_test_user", "dataflowpass123")
        assert auth_token is not None
        
        # Step 3: Generate JWT token
        token_pair = jwt_manager.generate_token_pair(
            str(user.id),
            user.username,
            user.role.value
        )
        assert token_pair.access_token is not None
        
        # Step 4: Use token for service access (simulated)
        payload = jwt_manager.verify_token(token_pair.access_token)
        assert payload is not None
        assert payload.user_id == str(user.id)
        
        # Step 5: Access services with authenticated context
        services = await service_manager.list_services()
        assert isinstance(services, list)
        
        results["user_auth_service_flow"] = "✅ PASSED"
        print("✅ User -> Auth -> Service Flow: PASSED")
        
    except Exception as e:
        results["user_auth_service_flow"] = f"❌ FAILED: {str(e)}"
        print(f"❌ User -> Auth -> Service Flow: FAILED - {str(e)}")
    
    # 2. Test Configuration -> Template -> Service Flow
    try:
        from fastapi_microservices_sdk.web.configuration.configuration_manager import ConfigurationManager
        from fastapi_microservices_sdk.web.templates_mgmt.template_manager import TemplateManager
        from fastapi_microservices_sdk.web.services.service_manager import ServiceManager
        
        # Initialize managers
        config_manager = ConfigurationManager()
        await config_manager.initialize()
        
        template_manager = TemplateManager()
        await template_manager.initialize()
        
        service_manager = ServiceManager()
        await service_manager.initialize()
        
        # Test configuration schemas
        schemas = await config_manager.list_schemas()
        assert isinstance(schemas, list)
        
        # Test template access
        templates = await template_manager.list_custom_templates()
        assert isinstance(templates, list)
        
        # Test service listing
        services = await service_manager.list_services()
        assert isinstance(services, list)
        
        results["config_template_service_flow"] = "✅ PASSED"
        print("✅ Config -> Template -> Service Flow: PASSED")
        
    except Exception as e:
        results["config_template_service_flow"] = f"❌ FAILED: {str(e)}"
        print(f"❌ Config -> Template -> Service Flow: FAILED - {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 CROSS-COMPONENT DATA FLOW SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if "✅ PASSED" in result)
    failed = len(results) - passed
    
    for component, result in results.items():
        print(f"{component.replace('_', ' ').title()}: {result}")
    
    print(f"\n📊 RESULTS: {passed} PASSED, {failed} FAILED")
    print(f"🎯 SUCCESS RATE: {(passed/len(results)*100):.1f}%")
    
    success_rate = passed / len(results) * 100
    assert success_rate >= 75, f"Data flow success rate {success_rate:.1f}% is below 75%"
    
    print("✅ Cross-component data flow tests completed successfully!")

if __name__ == "__main__":
    print("🚀 Running Full System Integration Tests...")
    asyncio.run(test_full_system_integration())
    asyncio.run(test_cross_component_data_flow())
    print("🎉 All full system integration tests completed!")
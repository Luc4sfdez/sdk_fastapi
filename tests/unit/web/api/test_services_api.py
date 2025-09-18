"""
Unit tests for service management API endpoints.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from fastapi_microservices_sdk.web.api.services import router
from fastapi_microservices_sdk.web.services.types import (
    ServiceInfo, ServiceDetails, ServiceStatus, HealthStatus, ResourceUsage
)


@pytest.fixture
def app():
    """Create FastAPI test application."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_service_manager():
    """Create mock service manager."""
    manager = AsyncMock()
    manager.is_initialized.return_value = True
    return manager


@pytest.fixture
def sample_service_info():
    """Create sample service info."""
    return ServiceInfo(
        id="test-service",
        name="Test Service",
        template_type="base",
        status=ServiceStatus.RUNNING,
        port=8000,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        last_updated=datetime(2024, 1, 1, 12, 30, 0),
        health_status=HealthStatus.HEALTHY,
        resource_usage=ResourceUsage(
            cpu_percent=25.5,
            memory_mb=128.0,
            disk_mb=512.0,
            network_in_mb=10.0,
            network_out_mb=5.0
        ),
        description="A test service",
        version="1.0.0"
    )


@pytest.fixture
def sample_service_details(sample_service_info):
    """Create sample service details."""
    return ServiceDetails(
        service_info=sample_service_info,
        endpoints=["http://localhost:8000", "http://localhost:8000/docs"],
        dependencies=["fastapi", "uvicorn"],
        environment_variables={"DEBUG": "true", "PORT": "8000"},
        logs_path="/var/log/test-service.log",
        metrics_enabled=True
    )


class TestServicesAPI:
    """Test cases for services API endpoints."""
    
    def test_list_services(self, client, mock_service_manager, sample_service_info):
        """Test listing services."""
        mock_service_manager.list_services.return_value = [sample_service_info]
        
        # Override the dependency
        from fastapi_microservices_sdk.web.api.services import get_service_manager
        client.app.dependency_overrides[get_service_manager] = lambda: mock_service_manager
        
        response = client.get("/api/services/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-service"
        assert data[0]["name"] == "Test Service"
        assert data[0]["status"] == "running"
        assert data[0]["health_status"] == "healthy"
        assert data[0]["resource_usage"]["cpu_percent"] == 25.5
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_list_services_with_filters(self, mock_get_manager, client, mock_service_manager, sample_service_info):
        """Test listing services with filters."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.list_services.return_value = [sample_service_info]
        
        # Test status filter
        response = client.get("/api/services/?status=running")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        # Test template type filter
        response = client.get("/api/services/?template_type=base")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        
        # Test search filter
        response = client.get("/api/services/?search=Test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_list_services_with_pagination(self, mock_get_manager, client, mock_service_manager, sample_service_info):
        """Test listing services with pagination."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.list_services.return_value = [sample_service_info] * 5
        
        response = client.get("/api/services/?skip=2&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_list_services_invalid_status(self, mock_get_manager, client, mock_service_manager):
        """Test listing services with invalid status filter."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.list_services.return_value = []
        
        response = client.get("/api/services/?status=invalid")
        
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service details."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_info"]["id"] == "test-service"
        assert data["service_info"]["name"] == "Test Service"
        assert data["endpoints"] == ["http://localhost:8000", "http://localhost:8000/docs"]
        assert data["dependencies"] == ["fastapi", "uvicorn"]
        assert data["environment_variables"]["DEBUG"] == "true"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_not_found(self, mock_get_manager, client, mock_service_manager):
        """Test getting non-existent service."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = None
        
        response = client.get("/api/services/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_start(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test starting a service."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        mock_service_manager.start_service.return_value = True
        
        response = client.post(
            "/api/services/test-service/actions",
            json={"action": "start", "force": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["action"] == "start"
        assert data["service_id"] == "test-service"
        assert "successful" in data["message"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_stop(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test stopping a service."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        mock_service_manager.stop_service.return_value = True
        
        response = client.post(
            "/api/services/test-service/actions",
            json={"action": "stop", "force": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["action"] == "stop"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_restart(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test restarting a service."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        mock_service_manager.restart_service.return_value = True
        
        response = client.post(
            "/api/services/test-service/actions",
            json={"action": "restart", "force": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["action"] == "restart"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_invalid(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test invalid service action."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.post(
            "/api/services/test-service/actions",
            json={"action": "invalid", "force": False}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_failure(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test service action failure."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        mock_service_manager.start_service.return_value = False
        
        response = client.post(
            "/api/services/test-service/actions",
            json={"action": "start", "force": False}
        )
        
        assert response.status_code == 500
        assert "Failed to start service" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_perform_service_action_not_found(self, mock_get_manager, client, mock_service_manager):
        """Test service action on non-existent service."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = None
        
        response = client.post(
            "/api/services/nonexistent/actions",
            json={"action": "start", "force": False}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_status(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service status."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-service"
        assert data["name"] == "Test Service"
        assert data["status"] == "running"
        assert data["health_status"] == "healthy"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_health(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service health."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_health.return_value = HealthStatus.HEALTHY
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == "test-service"
        assert data["health_status"] == "healthy"
        assert data["status"] == "running"
        assert "resource_usage" in data
        assert "endpoints" in data
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_delete_service(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test deleting a service."""
        # Create stopped service for deletion
        stopped_service = sample_service_details
        stopped_service.service_info.status = ServiceStatus.STOPPED
        
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = stopped_service
        mock_service_manager.delete_service.return_value = True
        
        response = client.delete("/api/services/test-service")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["service_id"] == "test-service"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_delete_running_service_without_force(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test deleting a running service without force flag."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details  # Running service
        
        response = client.delete("/api/services/test-service")
        
        assert response.status_code == 400
        assert "currently running" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_delete_running_service_with_force(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test deleting a running service with force flag."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details  # Running service
        mock_service_manager.delete_service.return_value = True
        
        response = client.delete("/api/services/test-service?force=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_delete_service_failure(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test service deletion failure."""
        stopped_service = sample_service_details
        stopped_service.service_info.status = ServiceStatus.STOPPED
        
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = stopped_service
        mock_service_manager.delete_service.return_value = False
        
        response = client.delete("/api/services/test-service")
        
        assert response.status_code == 500
        assert "Failed to delete service" in response.json()["detail"]
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_logs(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service logs."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == "test-service"
        assert "logs" in data
        assert isinstance(data["logs"], list)
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_logs_with_params(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service logs with parameters."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service/logs?lines=50&level=ERROR&follow=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == "test-service"
        assert data["follow"] == True
        assert data["level_filter"] == "ERROR"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_metrics(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service metrics."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get("/api/services/test-service/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service_id"] == "test-service"
        assert "metrics" in data
        assert data["metrics"]["cpu_percent"] == 25.5
        assert data["metrics"]["memory_mb"] == 128.0
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_get_service_metrics_with_time_range(self, mock_get_manager, client, mock_service_manager, sample_service_details):
        """Test getting service metrics with time range."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.get_service_details.return_value = sample_service_details
        
        response = client.get(
            "/api/services/test-service/metrics"
            "?start_time=2024-01-01T00:00:00Z&end_time=2024-01-01T23:59:59Z&interval=5m"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_time"] == "2024-01-01T00:00:00Z"
        assert data["end_time"] == "2024-01-01T23:59:59Z"
        assert data["interval"] == "5m"
    
    @patch('fastapi_microservices_sdk.web.api.services.get_service_manager')
    def test_api_error_handling(self, mock_get_manager, client, mock_service_manager):
        """Test API error handling."""
        mock_get_manager.return_value = mock_service_manager
        mock_service_manager.list_services.side_effect = Exception("Database error")
        
        response = client.get("/api/services/")
        
        assert response.status_code == 500
        assert "Failed to list services" in response.json()["detail"]
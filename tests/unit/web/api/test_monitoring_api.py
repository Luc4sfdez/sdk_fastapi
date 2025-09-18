"""
Tests for monitoring API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from fastapi_microservices_sdk.web.api.monitoring import (
    create_monitoring_router,
    MetricsQueryRequest,
    AlertRuleRequest,
    DashboardConfigRequest,
    TimeRange,
    AggregationType,
    AlertSeverity
)
from fastapi_microservices_sdk.web.core.dependency_container import DependencyContainer
from fastapi_microservices_sdk.web.monitoring.monitoring_manager import MonitoringManager
from fastapi_microservices_sdk.web.websockets.websocket_manager import WebSocketManager


class TestMonitoringAPI:
    """Test cases for monitoring API endpoints."""
    
    @pytest.fixture
    def mock_monitoring_manager(self):
        """Create mock monitoring manager."""
        manager = AsyncMock(spec=MonitoringManager)
        
        # Mock query_metrics response
        manager.query_metrics.return_value = {
            "service1": {
                "cpu_usage": [
                    {"timestamp": datetime.utcnow(), "value": 75.5, "labels": {"service": "service1"}},
                    {"timestamp": datetime.utcnow(), "value": 80.2, "labels": {"service": "service1"}}
                ],
                "memory_usage": [
                    {"timestamp": datetime.utcnow(), "value": 1024, "labels": {"service": "service1"}},
                    {"timestamp": datetime.utcnow(), "value": 1100, "labels": {"service": "service1"}}
                ]
            }
        }
        
        # Mock available services
        manager.get_available_services.return_value = ["service1", "service2", "service3"]
        
        # Mock available metrics
        manager.get_available_metrics.return_value = ["cpu_usage", "memory_usage", "request_count"]
        
        # Mock alert rule creation
        manager.create_alert_rule.return_value = {
            "id": "rule123",
            "name": "High CPU Alert",
            "description": "Alert when CPU usage is high",
            "service_id": "service1",
            "metric_name": "cpu_usage",
            "condition": "> 80",
            "threshold": 80.0,
            "severity": "high",
            "enabled": True,
            "notification_channels": ["email"],
            "evaluation_interval": 60,
            "for_duration": 300,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_evaluation": None
        }
        
        # Mock alert rules list
        manager.get_alert_rules.return_value = [
            {
                "id": "rule123",
                "name": "High CPU Alert",
                "service_id": "service1",
                "metric_name": "cpu_usage",
                "condition": "> 80",
                "threshold": 80.0,
                "severity": "high",
                "enabled": True
            }
        ]
        
        # Mock alerts list
        manager.get_alerts.return_value = [
            {
                "id": "alert456",
                "rule_id": "rule123",
                "rule_name": "High CPU Alert",
                "service_id": "service1",
                "metric_name": "cpu_usage",
                "current_value": 85.5,
                "threshold": 80.0,
                "severity": "high",
                "status": "active",
                "message": "CPU usage is 85.5% (threshold: > 80%)",
                "started_at": datetime.utcnow(),
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved_at": None,
                "labels": {"service": "service1"}
            }
        ]
        
        # Mock dashboard creation
        manager.create_dashboard.return_value = {
            "id": "dash789",
            "name": "System Overview",
            "description": "Main system dashboard",
            "layout": {"columns": 2, "rows": 3},
            "widgets": [{"type": "chart", "metric": "cpu_usage"}],
            "refresh_interval": 30,
            "time_range": "1h",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": "admin"
        }
        
        return manager
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.get_connection_count.return_value = 5
        manager.get_metrics_subscribers_count.return_value = 3
        manager.get_service_status_subscribers_count.return_value = 2
        return manager
    
    @pytest.fixture
    def mock_container(self, mock_monitoring_manager, mock_websocket_manager):
        """Create mock dependency container."""
        container = MagicMock()
        container.get_monitoring_manager.return_value = mock_monitoring_manager
        container.get_websocket_manager.return_value = mock_websocket_manager
        return container
    
    @pytest.fixture
    def app(self, mock_container):
        """Create FastAPI test app."""
        app = FastAPI()
        router = create_monitoring_router(mock_container)
        app.include_router(router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_query_metrics_endpoint(self, client, mock_monitoring_manager):
        """Test metrics query endpoint."""
        request_data = {
            "service_ids": ["service1"],
            "metric_names": ["cpu_usage", "memory_usage"],
            "time_range": "1h",
            "aggregation": "raw",
            "interval": "1m"
        }
        
        response = client.post("/api/v1/monitoring/metrics/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "series" in data
        assert "total_points" in data
        assert "execution_time_ms" in data
        
        # Verify the query was called with correct parameters
        mock_monitoring_manager.query_metrics.assert_called_once()
        call_args = mock_monitoring_manager.query_metrics.call_args
        assert call_args[1]["service_ids"] == ["service1"]
        assert call_args[1]["metric_names"] == ["cpu_usage", "memory_usage"]
    
    def test_query_metrics_custom_time_range(self, client, mock_monitoring_manager):
        """Test metrics query with custom time range."""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()
        
        request_data = {
            "time_range": "custom",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "aggregation": "avg",
            "interval": "5m"
        }
        
        response = client.post("/api/v1/monitoring/metrics/query", json=request_data)
        
        assert response.status_code == 200
        mock_monitoring_manager.query_metrics.assert_called_once()
    
    def test_get_available_services(self, client, mock_monitoring_manager):
        """Test get available services endpoint."""
        response = client.get("/api/v1/monitoring/metrics/services")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert "service1" in data
        assert "service2" in data
        assert "service3" in data
        
        mock_monitoring_manager.get_available_services.assert_called_once()
    
    def test_get_available_metrics(self, client, mock_monitoring_manager):
        """Test get available metrics endpoint."""
        response = client.get("/api/v1/monitoring/metrics/names")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "request_count" in data
        
        mock_monitoring_manager.get_available_metrics.assert_called_once_with(service_id=None)
    
    def test_get_available_metrics_filtered(self, client, mock_monitoring_manager):
        """Test get available metrics endpoint with service filter."""
        response = client.get("/api/v1/monitoring/metrics/names?service_id=service1")
        
        assert response.status_code == 200
        mock_monitoring_manager.get_available_metrics.assert_called_once_with(service_id="service1")
    
    def test_create_alert_rule(self, client, mock_monitoring_manager):
        """Test create alert rule endpoint."""
        request_data = {
            "name": "High CPU Alert",
            "description": "Alert when CPU usage is high",
            "service_id": "service1",
            "metric_name": "cpu_usage",
            "condition": "> 80",
            "threshold": 80.0,
            "severity": "high",
            "enabled": True,
            "notification_channels": ["email"],
            "evaluation_interval": 60,
            "for_duration": 300
        }
        
        response = client.post("/api/v1/monitoring/alerts/rules", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "High CPU Alert"
        assert data["service_id"] == "service1"
        assert data["metric_name"] == "cpu_usage"
        assert data["threshold"] == 80.0
        assert data["severity"] == "high"
        
        mock_monitoring_manager.create_alert_rule.assert_called_once()
    
    def test_get_alert_rules(self, client, mock_monitoring_manager):
        """Test get alert rules endpoint."""
        response = client.get("/api/v1/monitoring/alerts/rules")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "High CPU Alert"
        
        mock_monitoring_manager.get_alert_rules.assert_called_once_with(
            service_id=None, enabled=None
        )
    
    def test_get_alert_rules_filtered(self, client, mock_monitoring_manager):
        """Test get alert rules endpoint with filters."""
        response = client.get("/api/v1/monitoring/alerts/rules?service_id=service1&enabled=true")
        
        assert response.status_code == 200
        mock_monitoring_manager.get_alert_rules.assert_called_once_with(
            service_id="service1", enabled=True
        )
    
    def test_get_alert_rule_by_id(self, client, mock_monitoring_manager):
        """Test get specific alert rule endpoint."""
        mock_monitoring_manager.get_alert_rule.return_value = {
            "id": "rule123",
            "name": "High CPU Alert",
            "service_id": "service1",
            "metric_name": "cpu_usage"
        }
        
        response = client.get("/api/v1/monitoring/alerts/rules/rule123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "rule123"
        assert data["name"] == "High CPU Alert"
        
        mock_monitoring_manager.get_alert_rule.assert_called_once_with("rule123")
    
    def test_get_alert_rule_not_found(self, client, mock_monitoring_manager):
        """Test get alert rule that doesn't exist."""
        mock_monitoring_manager.get_alert_rule.return_value = None
        
        response = client.get("/api/v1/monitoring/alerts/rules/nonexistent")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_update_alert_rule(self, client, mock_monitoring_manager):
        """Test update alert rule endpoint."""
        mock_monitoring_manager.update_alert_rule.return_value = {
            "id": "rule123",
            "name": "Updated Alert",
            "threshold": 90.0
        }
        
        request_data = {
            "name": "Updated Alert",
            "description": "Updated description",
            "service_id": "service1",
            "metric_name": "cpu_usage",
            "condition": "> 90",
            "threshold": 90.0,
            "severity": "critical",
            "enabled": True,
            "notification_channels": ["email", "slack"],
            "evaluation_interval": 30,
            "for_duration": 180
        }
        
        response = client.put("/api/v1/monitoring/alerts/rules/rule123", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Alert"
        assert data["threshold"] == 90.0
        
        mock_monitoring_manager.update_alert_rule.assert_called_once()
    
    def test_delete_alert_rule(self, client, mock_monitoring_manager):
        """Test delete alert rule endpoint."""
        mock_monitoring_manager.delete_alert_rule.return_value = True
        
        response = client.delete("/api/v1/monitoring/alerts/rules/rule123")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        mock_monitoring_manager.delete_alert_rule.assert_called_once_with("rule123")
    
    def test_get_alerts(self, client, mock_monitoring_manager):
        """Test get alerts endpoint."""
        response = client.get("/api/v1/monitoring/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["rule_name"] == "High CPU Alert"
        assert data[0]["status"] == "active"
        
        mock_monitoring_manager.get_alerts.assert_called_once_with(
            status=None, severity=None, service_id=None, limit=100
        )
    
    def test_get_alerts_filtered(self, client, mock_monitoring_manager):
        """Test get alerts endpoint with filters."""
        response = client.get("/api/v1/monitoring/alerts?status=active&severity=high&limit=50")
        
        assert response.status_code == 200
        mock_monitoring_manager.get_alerts.assert_called_once_with(
            status="active", severity="high", service_id=None, limit=50
        )
    
    def test_acknowledge_alert(self, client, mock_monitoring_manager):
        """Test acknowledge alert endpoint."""
        mock_monitoring_manager.acknowledge_alert.return_value = True
        
        response = client.post("/api/v1/monitoring/alerts/alert456/acknowledge?acknowledged_by=admin")
        
        assert response.status_code == 200
        assert "acknowledged successfully" in response.json()["message"]
        
        mock_monitoring_manager.acknowledge_alert.assert_called_once_with("alert456", "admin")
    
    def test_resolve_alert(self, client, mock_monitoring_manager):
        """Test resolve alert endpoint."""
        mock_monitoring_manager.resolve_alert.return_value = True
        
        response = client.post("/api/v1/monitoring/alerts/alert456/resolve")
        
        assert response.status_code == 200
        assert "resolved successfully" in response.json()["message"]
        
        mock_monitoring_manager.resolve_alert.assert_called_once_with("alert456")
    
    def test_create_dashboard(self, client, mock_monitoring_manager):
        """Test create dashboard endpoint."""
        request_data = {
            "name": "System Overview",
            "description": "Main system dashboard",
            "layout": {"columns": 2, "rows": 3},
            "widgets": [{"type": "chart", "metric": "cpu_usage"}],
            "refresh_interval": 30,
            "time_range": "1h"
        }
        
        response = client.post("/api/v1/monitoring/dashboards?created_by=admin", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "System Overview"
        assert data["refresh_interval"] == 30
        assert data["created_by"] == "admin"
        
        mock_monitoring_manager.create_dashboard.assert_called_once()
    
    def test_get_dashboards(self, client, mock_monitoring_manager):
        """Test get dashboards endpoint."""
        mock_monitoring_manager.get_dashboards.return_value = [
            {
                "id": "dash789",
                "name": "System Overview",
                "created_by": "admin"
            }
        ]
        
        response = client.get("/api/v1/monitoring/dashboards")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "System Overview"
        
        mock_monitoring_manager.get_dashboards.assert_called_once_with(created_by=None)
    
    def test_get_dashboard_by_id(self, client, mock_monitoring_manager):
        """Test get specific dashboard endpoint."""
        mock_monitoring_manager.get_dashboard.return_value = {
            "id": "dash789",
            "name": "System Overview",
            "widgets": [{"type": "chart"}]
        }
        
        response = client.get("/api/v1/monitoring/dashboards/dash789")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == "dash789"
        assert data["name"] == "System Overview"
        
        mock_monitoring_manager.get_dashboard.assert_called_once_with("dash789")
    
    def test_update_dashboard(self, client, mock_monitoring_manager):
        """Test update dashboard endpoint."""
        mock_monitoring_manager.update_dashboard.return_value = {
            "id": "dash789",
            "name": "Updated Dashboard",
            "refresh_interval": 60
        }
        
        request_data = {
            "name": "Updated Dashboard",
            "description": "Updated description",
            "layout": {"columns": 3, "rows": 2},
            "widgets": [{"type": "gauge", "metric": "memory_usage"}],
            "refresh_interval": 60,
            "time_range": "6h"
        }
        
        response = client.put("/api/v1/monitoring/dashboards/dash789", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Dashboard"
        assert data["refresh_interval"] == 60
        
        mock_monitoring_manager.update_dashboard.assert_called_once()
    
    def test_delete_dashboard(self, client, mock_monitoring_manager):
        """Test delete dashboard endpoint."""
        mock_monitoring_manager.delete_dashboard.return_value = True
        
        response = client.delete("/api/v1/monitoring/dashboards/dash789")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        mock_monitoring_manager.delete_dashboard.assert_called_once_with("dash789")
    
    def test_get_websocket_info(self, client, mock_websocket_manager):
        """Test get WebSocket info endpoint."""
        response = client.get("/api/v1/monitoring/websocket/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["active_connections"] == 5
        assert data["metrics_subscribers"] == 3
        assert data["service_status_subscribers"] == 2
        assert data["websocket_url"] == "/ws/monitoring"
        assert "metrics" in data["supported_subscriptions"]
        assert "service_status" in data["supported_subscriptions"]
        assert "alerts" in data["supported_subscriptions"]


class TestMonitoringAPIModels:
    """Test monitoring API request/response models."""
    
    def test_metrics_query_request_validation(self):
        """Test MetricsQueryRequest validation."""
        # Valid request
        request = MetricsQueryRequest(
            service_ids=["service1"],
            metric_names=["cpu_usage"],
            time_range=TimeRange.LAST_1H,
            aggregation=AggregationType.AVERAGE
        )
        
        assert request.service_ids == ["service1"]
        assert request.time_range == TimeRange.LAST_1H
        assert request.aggregation == AggregationType.AVERAGE
    
    def test_metrics_query_request_custom_time_validation(self):
        """Test custom time range validation."""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()
        
        # Valid custom time range
        request = MetricsQueryRequest(
            time_range=TimeRange.CUSTOM,
            start_time=start_time,
            end_time=end_time
        )
        
        assert request.start_time == start_time
        assert request.end_time == end_time
    
    def test_alert_rule_request_validation(self):
        """Test AlertRuleRequest validation."""
        request = AlertRuleRequest(
            name="High CPU Alert",
            service_id="service1",
            metric_name="cpu_usage",
            condition="> 80",
            threshold=80.0,
            severity=AlertSeverity.HIGH,
            evaluation_interval=60,
            for_duration=300
        )
        
        assert request.name == "High CPU Alert"
        assert request.threshold == 80.0
        assert request.severity == AlertSeverity.HIGH
    
    def test_dashboard_config_request_validation(self):
        """Test DashboardConfigRequest validation."""
        request = DashboardConfigRequest(
            name="System Dashboard",
            layout={"columns": 2, "rows": 3},
            widgets=[{"type": "chart", "metric": "cpu_usage"}],
            refresh_interval=30,
            time_range=TimeRange.LAST_1H
        )
        
        assert request.name == "System Dashboard"
        assert request.refresh_interval == 30
        assert len(request.widgets) == 1
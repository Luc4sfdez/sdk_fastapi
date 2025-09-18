"""
Unit tests for MonitoringManager.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from fastapi_microservices_sdk.web.monitoring.monitoring_manager import (
    MonitoringManager,
    AlertSeverity,
    AlertRule,
    Alert,
    TimeRange,
    MetricsData,
    SystemMetrics,
    DashboardData
)
from fastapi_microservices_sdk.web.services.types import ServiceInfo, ServiceStatus, HealthStatus, ResourceUsage


@pytest.fixture
def monitoring_manager():
    """Create a MonitoringManager instance."""
    config = {
        "metrics_retention_hours": 1,
        "alert_evaluation_interval": 1
    }
    return MonitoringManager("test_monitoring", config)


@pytest.fixture
def sample_service_info():
    """Create sample service info."""
    return ServiceInfo(
        id="test-service",
        name="Test Service",
        template_type="api_gateway",
        status=ServiceStatus.RUNNING,
        port=8000,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        health_status=HealthStatus.HEALTHY,
        resource_usage=ResourceUsage()
    )


@pytest.fixture
def sample_alert_rule():
    """Create sample alert rule."""
    return AlertRule(
        id="test-rule",
        name="Test Alert Rule",
        service_id="test-service",
        metric_name="cpu_percent",
        threshold=80.0,
        comparison=">",
        severity=AlertSeverity.HIGH,
        enabled=True,
        description="Test alert rule for CPU usage"
    )


class TestMonitoringManagerAPI:
    """Test MonitoringManager API methods for dashboard endpoints."""
    
    @pytest.mark.asyncio
    async def test_query_metrics(self, monitoring_manager, sample_service_info):
        """Test metrics querying functionality."""
        await monitoring_manager.initialize()
        
        # Register service metrics
        await monitoring_manager.register_service_metrics("test-service", sample_service_info)
        
        # Mock metrics collector
        with patch.object(monitoring_manager._metrics_collector, 'get_metric_series') as mock_get_series:
            mock_get_series.return_value = [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "value": 45.5
                },
                {
                    "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
                    "value": 42.3
                }
            ]
            
            # Query metrics
            result = await monitoring_manager.query_metrics(
                service_ids=["test-service"],
                metric_names=["cpu_percent"],
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow()
            )
            
            assert "test-service" in result
            assert "cpu_percent" in result["test-service"]
            assert len(result["test-service"]["cpu_percent"]) == 2
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_available_services(self, monitoring_manager, sample_service_info):
        """Test getting available services."""
        await monitoring_manager.initialize()
        
        # Register service
        await monitoring_manager.register_service_metrics("test-service", sample_service_info)
        
        services = await monitoring_manager.get_available_services()
        assert "test-service" in services
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_available_metrics(self, monitoring_manager, sample_service_info):
        """Test getting available metrics."""
        await monitoring_manager.initialize()
        
        # Register service
        await monitoring_manager.register_service_metrics("test-service", sample_service_info)
        
        # Get all metrics
        all_metrics = await monitoring_manager.get_available_metrics()
        assert "cpu_percent" in all_metrics
        assert "memory_mb" in all_metrics
        
        # Get service-specific metrics
        service_metrics = await monitoring_manager.get_available_metrics("test-service")
        assert "cpu_percent" in service_metrics
        assert "memory_mb" in service_metrics
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_alert_rule_api(self, monitoring_manager):
        """Test creating alert rule via API method."""
        await monitoring_manager.initialize()
        
        rule_data = await monitoring_manager.create_alert_rule(
            name="High CPU Alert",
            description="Alert when CPU usage is high",
            service_id="test-service",
            metric_name="cpu_percent",
            condition="> 80",
            threshold=80.0,
            severity="high",
            enabled=True,
            evaluation_interval=60,
            for_duration=300
        )
        
        assert rule_data["name"] == "High CPU Alert"
        assert rule_data["threshold"] == 80.0
        assert rule_data["severity"] == "high"
        assert rule_data["enabled"] is True
        assert "id" in rule_data
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_alert_rule_api(self, monitoring_manager, sample_alert_rule):
        """Test getting alert rule via API method."""
        await monitoring_manager.initialize()
        
        # Create rule first
        rule_id = await monitoring_manager._create_alert_rule_impl(sample_alert_rule)
        
        # Get rule
        rule_data = await monitoring_manager.get_alert_rule(rule_id)
        
        assert rule_data is not None
        assert rule_data["name"] == sample_alert_rule.name
        assert rule_data["threshold"] == sample_alert_rule.threshold
        assert rule_data["severity"] == sample_alert_rule.severity.value
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_alerts_api(self, monitoring_manager):
        """Test getting alerts via API method."""
        await monitoring_manager.initialize()
        
        # Create a test alert
        alert = Alert(
            id="test-alert",
            service_id="test-service",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test alert message",
            created_at=datetime.utcnow(),
            metadata={"rule_id": "test-rule", "metric_name": "cpu_percent", "metric_value": 85.0, "threshold": 80.0}
        )
        monitoring_manager._alerts["test-alert"] = alert
        
        # Get all alerts
        alerts = await monitoring_manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["id"] == "test-alert"
        assert alerts[0]["severity"] == "high"
        
        # Get alerts by service
        service_alerts = await monitoring_manager.get_alerts(service_id="test-service")
        assert len(service_alerts) == 1
        
        # Get alerts by status
        active_alerts = await monitoring_manager.get_alerts(status="active")
        assert len(active_alerts) == 1
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_create_dashboard_api(self, monitoring_manager):
        """Test creating dashboard via API method."""
        await monitoring_manager.initialize()
        
        dashboard_data = await monitoring_manager.create_dashboard(
            name="Test Dashboard",
            description="A test dashboard",
            layout={"columns": 2},
            widgets=[
                {"type": "gauge", "metric": "cpu_percent"},
                {"type": "chart", "metric": "memory_mb"}
            ],
            refresh_interval=30,
            time_range="1h",
            created_by="test-user"
        )
        
        assert dashboard_data["name"] == "Test Dashboard"
        assert dashboard_data["description"] == "A test dashboard"
        assert len(dashboard_data["widgets"]) == 2
        assert dashboard_data["refresh_interval"] == 30
        assert "id" in dashboard_data
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_dashboards_api(self, monitoring_manager):
        """Test getting dashboards via API method."""
        await monitoring_manager.initialize()
        
        # Create a test dashboard
        dashboard = DashboardData(
            dashboard_id="test-dashboard",
            title="Test Dashboard",
            widgets=[{"type": "gauge"}],
            last_updated=datetime.utcnow()
        )
        monitoring_manager._dashboards["test-dashboard"] = dashboard
        
        dashboards = await monitoring_manager.get_dashboards()
        assert len(dashboards) == 1
        assert dashboards[0]["name"] == "Test Dashboard"
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_aggregation_functionality(self, monitoring_manager):
        """Test metrics aggregation functionality."""
        await monitoring_manager.initialize()
        
        # Test data points
        data_points = [
            {"timestamp": "2023-01-01T10:00:00", "value": 10},
            {"timestamp": "2023-01-01T10:01:00", "value": 20},
            {"timestamp": "2023-01-01T10:02:00", "value": 30},
            {"timestamp": "2023-01-01T10:03:00", "value": 40}
        ]
        
        # Test average aggregation
        avg_result = monitoring_manager._apply_aggregation(data_points, "avg", "1m")
        assert len(avg_result) == 1
        assert avg_result[0]["value"] == 25.0  # (10+20+30+40)/4
        
        # Test sum aggregation
        sum_result = monitoring_manager._apply_aggregation(data_points, "sum", "1m")
        assert sum_result[0]["value"] == 100  # 10+20+30+40
        
        # Test min aggregation
        min_result = monitoring_manager._apply_aggregation(data_points, "min", "1m")
        assert min_result[0]["value"] == 10
        
        # Test max aggregation
        max_result = monitoring_manager._apply_aggregation(data_points, "max", "1m")
        assert max_result[0]["value"] == 40
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_filtering_functionality(self, monitoring_manager):
        """Test metrics filtering functionality."""
        await monitoring_manager.initialize()
        
        # Test data points
        data_points = [
            {"timestamp": "2023-01-01T10:00:00", "value": 10},
            {"timestamp": "2023-01-01T10:01:00", "value": 50},
            {"timestamp": "2023-01-01T10:02:00", "value": 80},
            {"timestamp": "2023-01-01T10:03:00", "value": 90}
        ]
        
        # Test min_value filter
        filtered = monitoring_manager._apply_filters(data_points, {"min_value": 30})
        assert len(filtered) == 2  # 50, 80, 90 are >= 30
        assert all(point["value"] >= 30 for point in filtered)
        
        # Test max_value filter
        filtered = monitoring_manager._apply_filters(data_points, {"max_value": 70})
        assert len(filtered) == 2  # 10, 50 are <= 70
        assert all(point["value"] <= 70 for point in filtered)
        
        # Test combined filters
        filtered = monitoring_manager._apply_filters(data_points, {"min_value": 20, "max_value": 70})
        assert len(filtered) == 1  # Only 50 is between 20 and 70
        assert filtered[0]["value"] == 50
        
        await monitoring_manager.shutdown()


class TestMonitoringManagerMetricsCollection:
    """Test metrics collection helper methods."""
    
    @pytest.mark.asyncio
    async def test_service_cpu_collection(self, monitoring_manager):
        """Test service CPU metrics collection."""
        await monitoring_manager.initialize()
        
        cpu_usage = monitoring_manager._get_service_cpu("test-service")
        assert 0.0 <= cpu_usage <= 100.0
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_memory_collection(self, monitoring_manager):
        """Test service memory metrics collection."""
        await monitoring_manager.initialize()
        
        memory_usage = monitoring_manager._get_service_memory("test-service")
        assert memory_usage >= 50.0  # Minimum memory usage
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_requests_collection(self, monitoring_manager):
        """Test service request count collection."""
        await monitoring_manager.initialize()
        
        request_count = monitoring_manager._get_service_requests("test-service")
        assert request_count >= 0
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_response_time_collection(self, monitoring_manager):
        """Test service response time collection."""
        await monitoring_manager.initialize()
        
        response_time = monitoring_manager._get_service_response_time("test-service")
        assert response_time >= 10.0  # Minimum response time
        
        await monitoring_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_error_rate_collection(self, monitoring_manager):
        """Test service error rate collection."""
        await monitoring_manager.initialize()
        
        error_rate = monitoring_manager._get_service_error_rate("test-service")
        assert 0.0 <= error_rate <= 100.0
        
        await monitoring_manager.shutdown()


@pytest.fixture
def time_range():
    """Create sample time range."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    return TimeRange(start=start_time, end=end_time)


class TestMonitoringManager:
    """Test cases for MonitoringManager."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, monitoring_manager):
        """Test MonitoringManager initialization."""
        assert not monitoring_manager.is_initialized()
        
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector_class.return_value = mock_collector
            
            success = await monitoring_manager.initialize()
            assert success
            assert monitoring_manager.is_initialized()
            
            # Verify metrics collector was initialized
            mock_collector.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_service_metrics(self, monitoring_manager, sample_service_info):
        """Test registering service metrics."""
        # Initialize with mocked metrics collector
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            # Register service metrics
            await monitoring_manager.register_service_metrics(
                sample_service_info.id, 
                sample_service_info
            )
            
            # Verify metrics collectors were registered
            assert mock_collector.register_metric_collector.call_count >= 3  # CPU, Memory, Requests
            
            # Verify service is tracked
            assert sample_service_info.id in monitoring_manager._service_collectors
    
    @pytest.mark.asyncio
    async def test_unregister_service_metrics(self, monitoring_manager, sample_service_info):
        """Test unregistering service metrics."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            # Register then unregister
            await monitoring_manager.register_service_metrics(
                sample_service_info.id, 
                sample_service_info
            )
            
            assert sample_service_info.id in monitoring_manager._service_collectors
            
            await monitoring_manager.unregister_service_metrics(sample_service_info.id)
            
            assert sample_service_info.id not in monitoring_manager._service_collectors
    
    @pytest.mark.asyncio
    async def test_create_alert_rule(self, monitoring_manager, sample_alert_rule):
        """Test creating alert rule."""
        await monitoring_manager.initialize()
        
        rule_id = await monitoring_manager.create_alert_rule(sample_alert_rule)
        
        assert rule_id == sample_alert_rule.id
        assert rule_id in monitoring_manager._alert_rules
        assert rule_id in monitoring_manager._alert_states
        
        stored_rule = monitoring_manager._alert_rules[rule_id]
        assert stored_rule.name == sample_alert_rule.name
        assert stored_rule.threshold == sample_alert_rule.threshold
    
    @pytest.mark.asyncio
    async def test_update_alert_rule(self, monitoring_manager, sample_alert_rule):
        """Test updating alert rule."""
        await monitoring_manager.initialize()
        
        # Create rule first
        rule_id = await monitoring_manager.create_alert_rule(sample_alert_rule)
        
        # Update rule
        updates = {
            "threshold": 90.0,
            "severity": AlertSeverity.CRITICAL,
            "enabled": False
        }
        
        success = await monitoring_manager.update_alert_rule(rule_id, updates)
        assert success
        
        updated_rule = monitoring_manager._alert_rules[rule_id]
        assert updated_rule.threshold == 90.0
        assert updated_rule.severity == AlertSeverity.CRITICAL
        assert updated_rule.enabled == False
    
    @pytest.mark.asyncio
    async def test_delete_alert_rule(self, monitoring_manager, sample_alert_rule):
        """Test deleting alert rule."""
        await monitoring_manager.initialize()
        
        # Create rule first
        rule_id = await monitoring_manager.create_alert_rule(sample_alert_rule)
        assert rule_id in monitoring_manager._alert_rules
        
        # Delete rule
        success = await monitoring_manager.delete_alert_rule(rule_id)
        assert success
        assert rule_id not in monitoring_manager._alert_rules
        assert rule_id not in monitoring_manager._alert_states
    
    @pytest.mark.asyncio
    async def test_get_alert_rules(self, monitoring_manager, sample_alert_rule):
        """Test getting alert rules."""
        await monitoring_manager.initialize()
        
        # Create multiple rules
        rule1 = sample_alert_rule
        rule2 = AlertRule(
            id="test-rule-2",
            name="High Memory Alert",
            service_id="test-service-2",
            metric_name="service_test-service-2_memory_mb",
            threshold=500.0,
            comparison=">",
            severity=AlertSeverity.MEDIUM
        )
        
        await monitoring_manager.create_alert_rule(rule1)
        await monitoring_manager.create_alert_rule(rule2)
        
        # Get all rules
        all_rules = await monitoring_manager.get_alert_rules()
        assert len(all_rules) == 2
        
        # Get rules for specific service
        service_rules = await monitoring_manager.get_alert_rules(service_id="test-service")
        assert len(service_rules) == 1
        assert service_rules[0].service_id == "test-service"
    
    @pytest.mark.asyncio
    async def test_get_service_metrics(self, monitoring_manager, time_range):
        """Test getting service metrics."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.get_metric_series.return_value = [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "value": 75.5,
                    "labels": {"service_id": "test-service"}
                }
            ]
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            metrics = await monitoring_manager.get_service_metrics("test-service", time_range)
            
            assert isinstance(metrics, list)
            # Verify metrics collector was called
            assert mock_collector.get_metric_series.called
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, monitoring_manager, time_range):
        """Test getting system metrics."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.get_metric_series.return_value = [
                {
                    "timestamp": "2024-01-01T12:00:00",
                    "value": 45.2,
                    "labels": {"type": "system"}
                }
            ]
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            metrics = await monitoring_manager.get_system_metrics(time_range)
            
            assert isinstance(metrics, list)
            # Verify metrics collector was called
            assert mock_collector.get_metric_series.called
    
    @pytest.mark.asyncio
    async def test_get_aggregated_metrics(self, monitoring_manager, time_range):
        """Test getting aggregated metrics."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.get_multiple_metrics.return_value = {
                "cpu_usage": {"current_value": 75.5, "time_series": []},
                "memory_usage": {"current_value": 256.0, "time_series": []}
            }
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            metrics = await monitoring_manager.get_aggregated_metrics(
                ["cpu_usage", "memory_usage"],
                time_range,
                "avg"
            )
            
            assert "cpu_usage" in metrics
            assert "memory_usage" in metrics
            assert metrics["cpu_usage"]["current_value"] == 75.5
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, monitoring_manager):
        """Test acknowledging an alert."""
        await monitoring_manager.initialize()
        
        # Create an alert
        alert = Alert(
            id="test-alert",
            service_id="test-service",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test alert message",
            created_at=datetime.utcnow()
        )
        
        monitoring_manager._alerts[alert.id] = alert
        
        # Acknowledge alert
        success = await monitoring_manager.acknowledge_alert(alert.id, "test_user")
        assert success
        
        acknowledged_alert = monitoring_manager._alerts[alert.id]
        assert acknowledged_alert.acknowledged == True
        assert acknowledged_alert.acknowledged_by == "test_user"
        assert acknowledged_alert.acknowledged_at is not None
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, monitoring_manager):
        """Test resolving an alert."""
        await monitoring_manager.initialize()
        
        # Create an alert
        alert = Alert(
            id="test-alert",
            service_id="test-service",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test alert message",
            created_at=datetime.utcnow()
        )
        
        monitoring_manager._alerts[alert.id] = alert
        
        # Resolve alert
        success = await monitoring_manager.resolve_alert(alert.id)
        assert success
        
        resolved_alert = monitoring_manager._alerts[alert.id]
        assert resolved_alert.resolved == True
        assert resolved_alert.resolved_at is not None
    
    @pytest.mark.asyncio
    async def test_get_alerts(self, monitoring_manager):
        """Test getting alerts with filters."""
        await monitoring_manager.initialize()
        
        # Create multiple alerts
        alert1 = Alert(
            id="alert-1",
            service_id="service-1",
            severity=AlertSeverity.HIGH,
            title="Alert 1",
            message="Message 1",
            created_at=datetime.utcnow(),
            resolved=False
        )
        
        alert2 = Alert(
            id="alert-2",
            service_id="service-2",
            severity=AlertSeverity.MEDIUM,
            title="Alert 2",
            message="Message 2",
            created_at=datetime.utcnow(),
            resolved=True
        )
        
        monitoring_manager._alerts[alert1.id] = alert1
        monitoring_manager._alerts[alert2.id] = alert2
        
        # Get all alerts
        all_alerts = await monitoring_manager.get_alerts()
        assert len(all_alerts) == 2
        
        # Get alerts for specific service
        service_alerts = await monitoring_manager.get_alerts(service_id="service-1")
        assert len(service_alerts) == 1
        assert service_alerts[0].service_id == "service-1"
        
        # Get unresolved alerts
        unresolved_alerts = await monitoring_manager.get_alerts(resolved=False)
        assert len(unresolved_alerts) == 1
        assert unresolved_alerts[0].resolved == False
    
    @pytest.mark.asyncio
    async def test_dashboard_management(self, monitoring_manager):
        """Test dashboard creation and management."""
        await monitoring_manager.initialize()
        
        # Create dashboard
        dashboard = DashboardData(
            dashboard_id="test-dashboard",
            title="Test Dashboard",
            widgets=[
                {
                    "id": "cpu_widget",
                    "type": "gauge",
                    "title": "CPU Usage",
                    "metric": "cpu_usage"
                }
            ],
            last_updated=datetime.utcnow()
        )
        
        dashboard_id = await monitoring_manager.create_dashboard(dashboard)
        assert dashboard_id == "test-dashboard"
        
        # Get dashboard
        retrieved_dashboard = await monitoring_manager.get_dashboard_data(dashboard_id)
        assert retrieved_dashboard is not None
        assert retrieved_dashboard.title == "Test Dashboard"
        
        # Update dashboard
        success = await monitoring_manager.update_dashboard(
            dashboard_id,
            {"title": "Updated Dashboard"}
        )
        assert success
        
        updated_dashboard = await monitoring_manager.get_dashboard_data(dashboard_id)
        assert updated_dashboard.title == "Updated Dashboard"
    
    @pytest.mark.asyncio
    async def test_notification_handlers(self, monitoring_manager):
        """Test notification handler management."""
        await monitoring_manager.initialize()
        
        # Add notification handler
        notifications_received = []
        
        def test_handler(alert: Alert):
            notifications_received.append(alert)
        
        monitoring_manager.add_notification_handler(test_handler)
        
        # Create and send notification
        alert = Alert(
            id="test-alert",
            service_id="test-service",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test message",
            created_at=datetime.utcnow()
        )
        
        await monitoring_manager.send_notification(alert)
        
        assert len(notifications_received) == 1
        assert notifications_received[0].id == alert.id
    
    @pytest.mark.asyncio
    async def test_alert_condition_evaluation(self, monitoring_manager):
        """Test alert condition evaluation logic."""
        await monitoring_manager.initialize()
        
        # Test different comparison operators
        assert monitoring_manager._evaluate_condition(85.0, 80.0, ">") == True
        assert monitoring_manager._evaluate_condition(75.0, 80.0, ">") == False
        
        assert monitoring_manager._evaluate_condition(85.0, 80.0, ">=") == True
        assert monitoring_manager._evaluate_condition(80.0, 80.0, ">=") == True
        assert monitoring_manager._evaluate_condition(75.0, 80.0, ">=") == False
        
        assert monitoring_manager._evaluate_condition(75.0, 80.0, "<") == True
        assert monitoring_manager._evaluate_condition(85.0, 80.0, "<") == False
        
        assert monitoring_manager._evaluate_condition(75.0, 80.0, "<=") == True
        assert monitoring_manager._evaluate_condition(80.0, 80.0, "<=") == True
        assert monitoring_manager._evaluate_condition(85.0, 80.0, "<=") == False
        
        assert monitoring_manager._evaluate_condition(80.0, 80.0, "==") == True
        assert monitoring_manager._evaluate_condition(85.0, 80.0, "==") == False
        
        assert monitoring_manager._evaluate_condition(85.0, 80.0, "!=") == True
        assert monitoring_manager._evaluate_condition(80.0, 80.0, "!=") == False
    
    @pytest.mark.asyncio
    async def test_alert_evaluation_loop(self, monitoring_manager, sample_alert_rule):
        """Test alert evaluation loop functionality."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector.get_metric_value.return_value = 85.0  # Above threshold
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            
            # Create alert rule
            await monitoring_manager.create_alert_rule(sample_alert_rule)
            
            # Manually trigger evaluation
            await monitoring_manager._evaluate_alert_rules()
            
            # Check that rule state was updated
            rule_state = monitoring_manager._alert_states[sample_alert_rule.id]
            assert rule_state["condition_start_time"] is not None
            
            # Verify metrics collector was called
            mock_collector.get_metric_value.assert_called_with(
                sample_alert_rule.metric_name, "last"
            )
    
    @pytest.mark.asyncio
    async def test_shutdown(self, monitoring_manager):
        """Test MonitoringManager shutdown."""
        with patch('fastapi_microservices_sdk.web.monitoring.monitoring_manager.MetricsCollector') as mock_collector_class:
            mock_collector = AsyncMock()
            mock_collector_class.return_value = mock_collector
            
            await monitoring_manager.initialize()
            assert monitoring_manager.is_initialized()
            
            success = await monitoring_manager.shutdown()
            assert success
            
            # Verify metrics collector was shutdown
            mock_collector.shutdown.assert_called_once()
    
    def test_service_metric_helpers(self, monitoring_manager):
        """Test service metric collection helper methods."""
        # These methods return simulated values for testing
        cpu_usage = monitoring_manager._get_service_cpu("test-service")
        assert isinstance(cpu_usage, float)
        assert 0 <= cpu_usage <= 100
        
        memory_usage = monitoring_manager._get_service_memory("test-service")
        assert isinstance(memory_usage, float)
        assert memory_usage >= 0
        
        request_count = monitoring_manager._get_service_requests("test-service")
        assert isinstance(request_count, int)
        assert request_count >= 0
        
        response_time = monitoring_manager._get_service_response_time("test-service")
        assert isinstance(response_time, float)
        assert response_time >= 0
        
        error_rate = monitoring_manager._get_service_error_rate("test-service")
        assert isinstance(error_rate, float)
        assert error_rate >= 0
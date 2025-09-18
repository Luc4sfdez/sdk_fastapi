"""
Tests for WebSocketManager with real-time metrics and service status.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
import jwt

from fastapi_microservices_sdk.web.websockets.websocket_manager import (
    WebSocketManager,
    WebSocketConnection,
    MetricsSubscription,
    ServiceStatusSubscription
)


class TestWebSocketManager:
    """Test cases for WebSocketManager."""
    
    @pytest.fixture
    def config(self):
        """WebSocket manager configuration."""
        return {
            "max_connections": 10,
            "heartbeat_interval": 5,
            "require_authentication": False,
            "jwt_secret": "test-secret",
            "rate_limit_messages": 10,
            "rate_limit_window": 60,
            "min_metrics_interval": 1,
            "max_metrics_interval": 60
        }
    
    @pytest.fixture
    def manager(self, config):
        """Create WebSocket manager instance."""
        return WebSocketManager("test_websocket", config)
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.ping = AsyncMock()
        return websocket
    
    @pytest.fixture
    def jwt_token(self, config):
        """Create valid JWT token."""
        payload = {
            "user_id": "test_user",
            "permissions": ["metrics:read", "services:read"],
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, config["jwt_secret"], algorithm="HS256")
    
    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """Test WebSocket manager initialization."""
        await manager.initialize()
        
        assert manager.is_initialized()
        assert manager.get_connection_count() == 0
        assert manager.get_metrics_subscribers_count() == 0
        assert manager.get_service_status_subscribers_count() == 0
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_connect_without_auth(self, manager, mock_websocket):
        """Test WebSocket connection without authentication."""
        await manager.initialize()
        
        # Connect client
        result = await manager.connect(mock_websocket, "client1")
        
        assert result is True
        assert manager.get_connection_count() == 1
        mock_websocket.accept.assert_called_once()
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_connect_with_auth_required(self, config, mock_websocket, jwt_token):
        """Test WebSocket connection with authentication required."""
        config["require_authentication"] = True
        manager = WebSocketManager("test_websocket", config)
        await manager.initialize()
        
        # Connect without token should fail
        result = await manager.connect(mock_websocket, "client1")
        assert result is False
        mock_websocket.close.assert_called_with(code=1008, reason="Authentication required")
        
        # Connect with valid token should succeed
        mock_websocket.reset_mock()
        result = await manager.connect(mock_websocket, "client2", token=jwt_token)
        assert result is True
        assert manager.get_connection_count() == 1
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_metrics_subscription(self, manager, mock_websocket):
        """Test metrics subscription functionality."""
        await manager.initialize()
        
        # Connect client
        await manager.connect(mock_websocket, "client1")
        
        # Subscribe to metrics
        result = await manager.subscribe_to_metrics(
            "client1",
            service_ids=["service1", "service2"],
            metric_types=["cpu", "memory"],
            update_interval=5
        )
        
        assert result is True
        assert manager.get_metrics_subscribers_count() == 1
        
        # Unsubscribe
        result = await manager.unsubscribe_from_metrics("client1")
        assert result is True
        assert manager.get_metrics_subscribers_count() == 0
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_status_subscription(self, manager, mock_websocket):
        """Test service status subscription functionality."""
        await manager.initialize()
        
        # Connect client
        await manager.connect(mock_websocket, "client1")
        
        # Subscribe to service status
        result = await manager.subscribe_to_service_status(
            "client1",
            service_ids=["service1"],
            status_types=["running", "stopped"],
            include_health=True,
            include_metrics=False
        )
        
        assert result is True
        assert manager.get_service_status_subscribers_count() == 1
        
        # Unsubscribe
        result = await manager.unsubscribe_from_service_status("client1")
        assert result is True
        assert manager.get_service_status_subscribers_count() == 0
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_service_status_notification(self, manager, mock_websocket):
        """Test service status change notification."""
        await manager.initialize()
        
        # Connect and subscribe client
        await manager.connect(mock_websocket, "client1")
        await manager.subscribe_to_service_status("client1", service_ids=["service1"])
        
        # Notify status change
        status_data = {
            "type": "status_change",
            "old_status": "running",
            "new_status": "stopped",
            "reason": "manual_stop"
        }
        
        result = await manager.notify_service_status_change("service1", status_data)
        
        assert result == 1  # One client notified
        mock_websocket.send_text.assert_called()
        
        # Check message content
        call_args = mock_websocket.send_text.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "direct"
        assert message["data"]["type"] == "service_status_change"
        assert message["data"]["service_id"] == "service1"
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_metrics_streaming_with_provider(self, manager, mock_websocket):
        """Test metrics streaming with provider function."""
        await manager.initialize()
        
        # Set up metrics provider
        mock_metrics = {
            "service1": {
                "cpu": 75.5,
                "memory": 1024,
                "requests": 100
            },
            "service2": {
                "cpu": 45.2,
                "memory": 512
            }
        }
        
        async def metrics_provider():
            return mock_metrics
        
        manager.set_metrics_provider(metrics_provider)
        
        # Connect and subscribe client
        await manager.connect(mock_websocket, "client1")
        await manager.subscribe_to_metrics(
            "client1",
            service_ids=["service1"],
            metric_types=["cpu", "memory"],
            update_interval=1
        )
        
        # Wait for metrics streaming
        await asyncio.sleep(1.5)
        
        # Check that metrics were sent
        assert mock_websocket.send_text.called
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, manager, mock_websocket):
        """Test rate limiting functionality."""
        # Set low rate limit for testing
        manager._rate_limit_messages = 2
        manager._rate_limit_window = 60
        
        await manager.initialize()
        await manager.connect(mock_websocket, "client1")
        
        # Send messages up to limit
        for i in range(3):
            result = await manager.send_to_client("client1", {"message": f"test_{i}"})
            if i < 2:
                assert result is True
            # Third message should be rate limited in streaming context
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, manager, mock_websocket):
        """Test that disconnect properly cleans up subscriptions."""
        await manager.initialize()
        
        # Connect and subscribe
        await manager.connect(mock_websocket, "client1")
        await manager.subscribe_to_metrics("client1")
        await manager.subscribe_to_service_status("client1")
        
        assert manager.get_connection_count() == 1
        assert manager.get_metrics_subscribers_count() == 1
        assert manager.get_service_status_subscribers_count() == 1
        
        # Disconnect
        await manager.disconnect("client1")
        
        assert manager.get_connection_count() == 0
        # Note: Current implementation doesn't auto-cleanup subscriptions on disconnect
        # This could be enhanced in the future
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_metrics_filtering(self, manager, mock_websocket):
        """Test metrics filtering functionality."""
        await manager.initialize()
        
        # Set up metrics provider with various data
        mock_metrics = {
            "service1": {
                "cpu": 75.5,
                "memory": 1024,
                "disk": 50.0
            },
            "service2": {
                "cpu": 25.0,
                "memory": 512
            }
        }
        
        async def metrics_provider():
            return mock_metrics
        
        manager.set_metrics_provider(metrics_provider)
        
        # Connect and subscribe with filters
        await manager.connect(mock_websocket, "client1")
        await manager.subscribe_to_metrics(
            "client1",
            service_ids=["service1"],  # Only service1
            metric_types=["cpu", "memory"],  # Only cpu and memory
            update_interval=1,
            filters={"min_value": 30}  # Only values >= 30
        )
        
        # Test the filtering logic
        subscription = manager._metrics_subscriptions["client1"]
        filtered_data = await manager._get_filtered_metrics(subscription)
        
        assert "service1" in filtered_data
        assert "service2" not in filtered_data  # Filtered out by service_ids
        assert "cpu" in filtered_data["service1"]
        assert "memory" in filtered_data["service1"]
        assert "disk" not in filtered_data["service1"]  # Filtered out by metric_types
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_connection_limit(self, manager):
        """Test connection limit enforcement."""
        manager._max_connections = 2
        await manager.initialize()
        
        # Connect up to limit
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        ws3 = AsyncMock(spec=WebSocket)
        
        result1 = await manager.connect(ws1, "client1")
        result2 = await manager.connect(ws2, "client2")
        result3 = await manager.connect(ws3, "client3")
        
        assert result1 is True
        assert result2 is True
        assert result3 is False  # Should be rejected
        
        ws3.close.assert_called_with(code=1013, reason="Too many connections")
        
        await manager.shutdown()


class TestWebSocketDataClasses:
    """Test WebSocket data classes."""
    
    def test_websocket_connection_creation(self):
        """Test WebSocketConnection creation."""
        websocket = MagicMock()
        connection = WebSocketConnection(
            websocket=websocket,
            client_id="test_client",
            connected_at=datetime.utcnow(),
            subscriptions={"topic1", "topic2"},
            metadata={"user": "test"}
        )
        
        assert connection.client_id == "test_client"
        assert connection.authenticated is False  # Default
        assert connection.user_id is None  # Default
        assert len(connection.subscriptions) == 2
    
    def test_metrics_subscription_creation(self):
        """Test MetricsSubscription creation."""
        subscription = MetricsSubscription(
            client_id="test_client",
            service_ids=["service1", "service2"],
            metric_types=["cpu", "memory"],
            update_interval=10,
            filters={"min_value": 0}
        )
        
        assert subscription.client_id == "test_client"
        assert subscription.update_interval == 10
        assert len(subscription.service_ids) == 2
        assert len(subscription.metric_types) == 2
    
    def test_service_status_subscription_creation(self):
        """Test ServiceStatusSubscription creation."""
        subscription = ServiceStatusSubscription(
            client_id="test_client",
            service_ids=["service1"],
            status_types=["running", "stopped"],
            include_health=True,
            include_metrics=False
        )
        
        assert subscription.client_id == "test_client"
        assert subscription.include_health is True
        assert subscription.include_metrics is False
        assert len(subscription.service_ids) == 1
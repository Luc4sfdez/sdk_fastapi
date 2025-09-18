"""
WebSocket management for real-time communication.
"""

from typing import Dict, Set, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import asyncio
import time
from collections import defaultdict
from fastapi import WebSocket, HTTPException
import jwt

from ..core.base_manager import BaseManager


@dataclass
class WebSocketConnection:
    """WebSocket connection information."""
    websocket: WebSocket
    client_id: str
    connected_at: datetime
    subscriptions: Set[str]
    metadata: Dict[str, Any]
    authenticated: bool = False
    user_id: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    rate_limit_reset: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MetricsSubscription:
    """Metrics subscription configuration."""
    client_id: str
    service_ids: Optional[List[str]] = None  # None means all services
    metric_types: Optional[List[str]] = None  # None means all metrics
    update_interval: int = 5  # seconds
    last_update: datetime = field(default_factory=datetime.utcnow)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceStatusSubscription:
    """Service status subscription configuration."""
    client_id: str
    service_ids: Optional[List[str]] = None  # None means all services
    status_types: Optional[List[str]] = None  # None means all status types
    include_health: bool = True
    include_metrics: bool = False


class WebSocketManager(BaseManager):
    """
    WebSocket management for real-time communication.
    
    Handles:
    - WebSocket connection management
    - Subscription management
    - Message broadcasting
    - Connection health monitoring
    - Real-time metrics streaming
    - Service status notifications
    - Authentication and rate limiting
    """
    
    def __init__(self, name: str = "websocket", config: Optional[Dict[str, Any]] = None):
        """Initialize the WebSocket manager."""
        super().__init__(name, config)
        self._connections: Dict[str, WebSocketConnection] = {}
        self._subscriptions: Dict[str, Set[str]] = {}  # topic -> client_ids
        self._metrics_subscriptions: Dict[str, MetricsSubscription] = {}
        self._service_status_subscriptions: Dict[str, ServiceStatusSubscription] = {}
        
        # Configuration
        self._max_connections = self.get_config("max_connections", 100)
        self._heartbeat_interval = self.get_config("heartbeat_interval", 30)
        self._require_auth = self.get_config("require_authentication", True)
        self._jwt_secret = self.get_config("jwt_secret", "your-secret-key")
        self._jwt_algorithm = self.get_config("jwt_algorithm", "HS256")
        self._rate_limit_messages = self.get_config("rate_limit_messages", 60)  # per minute
        self._rate_limit_window = self.get_config("rate_limit_window", 60)  # seconds
        self._min_metrics_interval = self.get_config("min_metrics_interval", 1)  # seconds
        self._max_metrics_interval = self.get_config("max_metrics_interval", 300)  # seconds
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._metrics_streaming_task: Optional[asyncio.Task] = None
        
        # Callbacks for external integration
        self._metrics_provider: Optional[Callable] = None
        self._service_status_provider: Optional[Callable] = None
        
        # Rate limiting tracking
        self._rate_limit_tracking: Dict[str, List[float]] = defaultdict(list)
    
    async def _initialize_impl(self) -> None:
        """Initialize the WebSocket manager."""
        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._metrics_streaming_task = asyncio.create_task(self._metrics_streaming_loop())
        self.logger.info("WebSocket manager initialized")
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the WebSocket manager."""
        # Cancel background tasks
        for task in [self._heartbeat_task, self._metrics_streaming_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all connections
        for connection in list(self._connections.values()):
            await self.disconnect(connection.client_id)
    
    async def connect(self, websocket: WebSocket, client_id: str, 
                     token: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Connect a WebSocket client.
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
            token: JWT authentication token (required if auth is enabled)
            metadata: Optional client metadata
            
        Returns:
            True if connection successful
        """
        return await self._safe_execute(
            "connect",
            self._connect_impl,
            websocket,
            client_id,
            token,
            metadata or {}
        ) or False
    
    async def disconnect(self, client_id: str) -> bool:
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if disconnection successful
        """
        return await self._safe_execute(
            "disconnect",
            self._disconnect_impl,
            client_id
        ) or False
    
    async def subscribe_to_topic(self, client_id: str, topic: str) -> bool:
        """
        Subscribe client to a topic.
        
        Args:
            client_id: Client identifier
            topic: Topic to subscribe to
            
        Returns:
            True if subscription successful
        """
        return await self._safe_execute(
            "subscribe_to_topic",
            self._subscribe_to_topic_impl,
            client_id,
            topic
        ) or False
    
    async def unsubscribe_from_topic(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe client from a topic.
        
        Args:
            client_id: Client identifier
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscription successful
        """
        return await self._safe_execute(
            "unsubscribe_from_topic",
            self._unsubscribe_from_topic_impl,
            client_id,
            topic
        ) or False
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]) -> int:
        """
        Broadcast message to all subscribers of a topic.
        
        Args:
            topic: Topic to broadcast to
            message: Message to broadcast
            
        Returns:
            Number of clients message was sent to
        """
        result = await self._safe_execute(
            "broadcast_to_topic",
            self._broadcast_to_topic_impl,
            topic,
            message
        )
        return result or 0
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to specific client.
        
        Args:
            client_id: Client identifier
            message: Message to send
            
        Returns:
            True if message sent successfully
        """
        return await self._safe_execute(
            "send_to_client",
            self._send_to_client_impl,
            client_id,
            message
        ) or False
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)
    
    def get_topic_subscribers(self, topic: str) -> List[str]:
        """Get list of subscribers for a topic."""
        return list(self._subscriptions.get(topic, set()))
    
    # New methods for real-time metrics and service status
    
    async def subscribe_to_metrics(self, client_id: str, service_ids: Optional[List[str]] = None,
                                  metric_types: Optional[List[str]] = None, 
                                  update_interval: int = 5,
                                  filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Subscribe client to real-time metrics updates.
        
        Args:
            client_id: Client identifier
            service_ids: List of service IDs to monitor (None for all)
            metric_types: List of metric types to include (None for all)
            update_interval: Update interval in seconds (min 1, max 300)
            filters: Additional filters for metrics
            
        Returns:
            True if subscription successful
        """
        return await self._safe_execute(
            "subscribe_to_metrics",
            self._subscribe_to_metrics_impl,
            client_id,
            service_ids,
            metric_types,
            update_interval,
            filters or {}
        ) or False
    
    async def unsubscribe_from_metrics(self, client_id: str) -> bool:
        """
        Unsubscribe client from metrics updates.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if unsubscription successful
        """
        return await self._safe_execute(
            "unsubscribe_from_metrics",
            self._unsubscribe_from_metrics_impl,
            client_id
        ) or False
    
    async def subscribe_to_service_status(self, client_id: str, service_ids: Optional[List[str]] = None,
                                        status_types: Optional[List[str]] = None,
                                        include_health: bool = True,
                                        include_metrics: bool = False) -> bool:
        """
        Subscribe client to service status updates.
        
        Args:
            client_id: Client identifier
            service_ids: List of service IDs to monitor (None for all)
            status_types: List of status types to include (None for all)
            include_health: Include health check updates
            include_metrics: Include basic metrics in status updates
            
        Returns:
            True if subscription successful
        """
        return await self._safe_execute(
            "subscribe_to_service_status",
            self._subscribe_to_service_status_impl,
            client_id,
            service_ids,
            status_types,
            include_health,
            include_metrics
        ) or False
    
    async def unsubscribe_from_service_status(self, client_id: str) -> bool:
        """
        Unsubscribe client from service status updates.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if unsubscription successful
        """
        return await self._safe_execute(
            "unsubscribe_from_service_status",
            self._unsubscribe_from_service_status_impl,
            client_id
        ) or False
    
    async def notify_service_status_change(self, service_id: str, status_data: Dict[str, Any]) -> int:
        """
        Notify subscribers about service status change.
        
        Args:
            service_id: Service identifier
            status_data: Status change data
            
        Returns:
            Number of clients notified
        """
        return await self._safe_execute(
            "notify_service_status_change",
            self._notify_service_status_change_impl,
            service_id,
            status_data
        ) or 0
    
    def set_metrics_provider(self, provider: Callable) -> None:
        """
        Set the metrics provider function.
        
        Args:
            provider: Function that returns current metrics data
        """
        self._metrics_provider = provider
    
    def set_service_status_provider(self, provider: Callable) -> None:
        """
        Set the service status provider function.
        
        Args:
            provider: Function that returns current service status data
        """
        self._service_status_provider = provider
    
    def get_metrics_subscribers_count(self) -> int:
        """Get number of active metrics subscribers."""
        return len(self._metrics_subscriptions)
    
    def get_service_status_subscribers_count(self) -> int:
        """Get number of active service status subscribers."""
        return len(self._service_status_subscriptions)
    
    # Implementation methods
    
    async def _connect_impl(self, websocket: WebSocket, client_id: str, 
                           token: Optional[str], metadata: Dict[str, Any]) -> bool:
        """Implementation for connecting WebSocket client."""
        # Check connection limit
        if len(self._connections) >= self._max_connections:
            await websocket.close(code=1013, reason="Too many connections")
            return False
        
        # Accept connection first
        await websocket.accept()
        
        # Authenticate if required
        authenticated = False
        user_id = None
        permissions = set()
        
        if self._require_auth:
            if not token:
                await websocket.close(code=1008, reason="Authentication required")
                return False
            
            try:
                payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
                user_id = payload.get("user_id")
                permissions = set(payload.get("permissions", []))
                authenticated = True
            except jwt.InvalidTokenError as e:
                await websocket.close(code=1008, reason=f"Invalid token: {str(e)}")
                return False
        else:
            authenticated = True
        
        # Store connection
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id,
            connected_at=datetime.utcnow(),
            subscriptions=set(),
            metadata=metadata,
            authenticated=authenticated,
            user_id=user_id,
            permissions=permissions
        )
        self._connections[client_id] = connection
        
        self.logger.info(f"WebSocket client connected: {client_id} (authenticated: {authenticated})")
        return True
    
    async def _disconnect_impl(self, client_id: str) -> bool:
        """Implementation for disconnecting WebSocket client."""
        if client_id not in self._connections:
            return False
        
        connection = self._connections[client_id]
        
        # Remove from all subscriptions
        for topic in connection.subscriptions.copy():
            await self._unsubscribe_from_topic_impl(client_id, topic)
        
        # Close WebSocket connection
        try:
            await connection.websocket.close()
        except Exception as e:
            self.logger.warning(f"Error closing WebSocket for {client_id}: {e}")
        
        # Remove connection
        del self._connections[client_id]
        
        self.logger.info(f"WebSocket client disconnected: {client_id}")
        return True
    
    async def _subscribe_to_topic_impl(self, client_id: str, topic: str) -> bool:
        """Implementation for subscribing to topic."""
        if client_id not in self._connections:
            return False
        
        # Add to connection subscriptions
        self._connections[client_id].subscriptions.add(topic)
        
        # Add to topic subscriptions
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()
        self._subscriptions[topic].add(client_id)
        
        self.logger.debug(f"Client {client_id} subscribed to topic: {topic}")
        return True
    
    async def _unsubscribe_from_topic_impl(self, client_id: str, topic: str) -> bool:
        """Implementation for unsubscribing from topic."""
        if client_id not in self._connections:
            return False
        
        # Remove from connection subscriptions
        self._connections[client_id].subscriptions.discard(topic)
        
        # Remove from topic subscriptions
        if topic in self._subscriptions:
            self._subscriptions[topic].discard(client_id)
            if not self._subscriptions[topic]:
                del self._subscriptions[topic]
        
        self.logger.debug(f"Client {client_id} unsubscribed from topic: {topic}")
        return True
    
    async def _broadcast_to_topic_impl(self, topic: str, message: Dict[str, Any]) -> int:
        """Implementation for broadcasting to topic."""
        if topic not in self._subscriptions:
            return 0
        
        subscribers = self._subscriptions[topic].copy()
        sent_count = 0
        
        # Prepare message
        message_data = {
            "type": "broadcast",
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
            "data": message
        }
        message_text = json.dumps(message_data)
        
        # Send to all subscribers
        for client_id in subscribers:
            if await self._send_message_to_client(client_id, message_text):
                sent_count += 1
        
        return sent_count
    
    async def _send_to_client_impl(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Implementation for sending message to client."""
        message_data = {
            "type": "direct",
            "timestamp": datetime.utcnow().isoformat(),
            "data": message
        }
        message_text = json.dumps(message_data)
        
        return await self._send_message_to_client(client_id, message_text)
    
    async def _send_message_to_client(self, client_id: str, message_text: str) -> bool:
        """Send raw message text to client."""
        if client_id not in self._connections:
            return False
        
        connection = self._connections[client_id]
        
        try:
            await connection.websocket.send_text(message_text)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to send message to {client_id}: {e}")
            # Remove disconnected client
            await self._disconnect_impl(client_id)
            return False
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop to check connection health."""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                # Send ping to all connections
                disconnected_clients = []
                for client_id, connection in self._connections.items():
                    try:
                        await connection.websocket.ping()
                    except Exception:
                        disconnected_clients.append(client_id)
                
                # Remove disconnected clients
                for client_id in disconnected_clients:
                    await self._disconnect_impl(client_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
    
    # New implementation methods
    
    async def _subscribe_to_metrics_impl(self, client_id: str, service_ids: Optional[List[str]],
                                        metric_types: Optional[List[str]], update_interval: int,
                                        filters: Dict[str, Any]) -> bool:
        """Implementation for subscribing to metrics."""
        if client_id not in self._connections:
            return False
        
        # Validate permissions
        connection = self._connections[client_id]
        if self._require_auth and "metrics:read" not in connection.permissions:
            return False
        
        # Validate interval
        update_interval = max(self._min_metrics_interval, 
                            min(self._max_metrics_interval, update_interval))
        
        # Create subscription
        subscription = MetricsSubscription(
            client_id=client_id,
            service_ids=service_ids,
            metric_types=metric_types,
            update_interval=update_interval,
            filters=filters
        )
        self._metrics_subscriptions[client_id] = subscription
        
        self.logger.debug(f"Client {client_id} subscribed to metrics (interval: {update_interval}s)")
        return True
    
    async def _unsubscribe_from_metrics_impl(self, client_id: str) -> bool:
        """Implementation for unsubscribing from metrics."""
        if client_id in self._metrics_subscriptions:
            del self._metrics_subscriptions[client_id]
            self.logger.debug(f"Client {client_id} unsubscribed from metrics")
            return True
        return False
    
    async def _subscribe_to_service_status_impl(self, client_id: str, service_ids: Optional[List[str]],
                                              status_types: Optional[List[str]], include_health: bool,
                                              include_metrics: bool) -> bool:
        """Implementation for subscribing to service status."""
        if client_id not in self._connections:
            return False
        
        # Validate permissions
        connection = self._connections[client_id]
        if self._require_auth and "services:read" not in connection.permissions:
            return False
        
        # Create subscription
        subscription = ServiceStatusSubscription(
            client_id=client_id,
            service_ids=service_ids,
            status_types=status_types,
            include_health=include_health,
            include_metrics=include_metrics
        )
        self._service_status_subscriptions[client_id] = subscription
        
        self.logger.debug(f"Client {client_id} subscribed to service status")
        return True
    
    async def _unsubscribe_from_service_status_impl(self, client_id: str) -> bool:
        """Implementation for unsubscribing from service status."""
        if client_id in self._service_status_subscriptions:
            del self._service_status_subscriptions[client_id]
            self.logger.debug(f"Client {client_id} unsubscribed from service status")
            return True
        return False
    
    async def _notify_service_status_change_impl(self, service_id: str, status_data: Dict[str, Any]) -> int:
        """Implementation for notifying service status change."""
        sent_count = 0
        
        # Find relevant subscribers
        for client_id, subscription in self._service_status_subscriptions.items():
            # Check if client is interested in this service
            if subscription.service_ids and service_id not in subscription.service_ids:
                continue
            
            # Check if client is interested in this status type
            status_type = status_data.get("type")
            if subscription.status_types and status_type not in subscription.status_types:
                continue
            
            # Prepare message
            message = {
                "type": "service_status_change",
                "service_id": service_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": status_data
            }
            
            # Send message
            if await self._send_to_client_impl(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def _metrics_streaming_loop(self) -> None:
        """Background loop for streaming metrics to subscribers."""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                
                if not self._metrics_subscriptions or not self._metrics_provider:
                    continue
                
                current_time = datetime.utcnow()
                
                # Process each metrics subscription
                for client_id, subscription in list(self._metrics_subscriptions.items()):
                    # Check if it's time to send update
                    time_since_last = (current_time - subscription.last_update).total_seconds()
                    if time_since_last < subscription.update_interval:
                        continue
                    
                    # Check if client is still connected
                    if client_id not in self._connections:
                        del self._metrics_subscriptions[client_id]
                        continue
                    
                    # Check rate limiting
                    if not self._check_rate_limit(client_id):
                        continue
                    
                    try:
                        # Get metrics data
                        metrics_data = await self._get_filtered_metrics(subscription)
                        
                        if metrics_data:
                            # Prepare message
                            message = {
                                "type": "metrics_update",
                                "timestamp": current_time.isoformat(),
                                "subscription": {
                                    "service_ids": subscription.service_ids,
                                    "metric_types": subscription.metric_types,
                                    "interval": subscription.update_interval
                                },
                                "data": metrics_data
                            }
                            
                            # Send message
                            if await self._send_to_client_impl(client_id, message):
                                subscription.last_update = current_time
                    
                    except Exception as e:
                        self.logger.error(f"Error sending metrics to {client_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics streaming loop: {e}")
    
    async def _get_filtered_metrics(self, subscription: MetricsSubscription) -> Optional[Dict[str, Any]]:
        """Get filtered metrics data for a subscription."""
        if not self._metrics_provider:
            return None
        
        try:
            # Get all metrics
            all_metrics = await self._metrics_provider()
            
            if not all_metrics:
                return None
            
            # Apply filters
            filtered_metrics = {}
            
            for service_id, service_metrics in all_metrics.items():
                # Filter by service IDs
                if subscription.service_ids and service_id not in subscription.service_ids:
                    continue
                
                filtered_service_metrics = {}
                
                for metric_name, metric_data in service_metrics.items():
                    # Filter by metric types
                    if subscription.metric_types and metric_name not in subscription.metric_types:
                        continue
                    
                    # Apply additional filters
                    if self._apply_metric_filters(metric_data, subscription.filters):
                        filtered_service_metrics[metric_name] = metric_data
                
                if filtered_service_metrics:
                    filtered_metrics[service_id] = filtered_service_metrics
            
            return filtered_metrics if filtered_metrics else None
        
        except Exception as e:
            self.logger.error(f"Error filtering metrics: {e}")
            return None
    
    def _apply_metric_filters(self, metric_data: Any, filters: Dict[str, Any]) -> bool:
        """Apply additional filters to metric data."""
        if not filters:
            return True
        
        # Example filter implementations
        for filter_key, filter_value in filters.items():
            if filter_key == "min_value" and isinstance(metric_data, (int, float)):
                if metric_data < filter_value:
                    return False
            elif filter_key == "max_value" and isinstance(metric_data, (int, float)):
                if metric_data > filter_value:
                    return False
            # Add more filter types as needed
        
        return True
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits."""
        current_time = time.time()
        
        # Clean old entries
        client_messages = self._rate_limit_tracking[client_id]
        cutoff_time = current_time - self._rate_limit_window
        self._rate_limit_tracking[client_id] = [
            msg_time for msg_time in client_messages if msg_time > cutoff_time
        ]
        
        # Check limit
        if len(self._rate_limit_tracking[client_id]) >= self._rate_limit_messages:
            return False
        
        # Add current message
        self._rate_limit_tracking[client_id].append(current_time)
        return True
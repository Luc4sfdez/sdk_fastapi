"""
Communication Manager for FastAPI Microservices SDK.

This module provides the central orchestrator for all communication components
including message brokers, HTTP clients, service discovery, gRPC services, and event sourcing.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, Union, Callable
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from .config import CommunicationConfig, MessageBrokerConfig, HTTPClientConfig
from .exceptions import (
    CommunicationError, 
    CommunicationConfigurationError,
    CommunicationErrorContext
)

# Import implemented components
from .messaging.base import MessageBroker

# Optional imports for message brokers
try:
    from .messaging.rabbitmq import RabbitMQClient
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

try:
    from .messaging.kafka import KafkaClient
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

try:
    from .messaging.redis_pubsub import RedisClient
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Import base interfaces (will be implemented in subsequent tasks)
# from .http.client import AdvancedHTTPClient  
# from .discovery.base import ServiceDiscovery
# from .grpc.server import GRPCServerManager
# from .events.store import EventStore


class ComponentStatus:
    """Status tracking for communication components."""
    
    def __init__(self, name: str, component_type: str):
        self.name = name
        self.component_type = component_type
        self.status = "initialized"
        self.last_health_check = None
        self.error_count = 0
        self.last_error = None
        self.metadata = {}
    
    def mark_healthy(self):
        """Mark component as healthy."""
        self.status = "healthy"
        self.last_health_check = datetime.now(timezone.utc)
        self.error_count = 0
        self.last_error = None
    
    def mark_unhealthy(self, error: Exception):
        """Mark component as unhealthy."""
        self.status = "unhealthy"
        self.last_health_check = datetime.now(timezone.utc)
        self.error_count += 1
        self.last_error = str(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary."""
        return {
            'name': self.name,
            'type': self.component_type,
            'status': self.status,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'metadata': self.metadata
        }


class CommunicationManager:
    """
    Central manager for all communication components.
    
    This class orchestrates the lifecycle of message brokers, HTTP clients,
    service discovery, gRPC services, and event sourcing components.
    """
    
    def __init__(self, config: CommunicationConfig):
        """
        Initialize the communication manager.
        
        Args:
            config: Communication configuration
        """
        self.config = config
        self.logger = logging.getLogger("communication_manager")
        
        # Component registries
        self.message_brokers: Dict[str, Any] = {}  # Will be MessageBroker instances
        self.http_clients: Dict[str, Any] = {}     # Will be AdvancedHTTPClient instances
        self.grpc_services: Dict[str, Any] = {}    # Will be GRPCService instances
        self.service_discovery: Optional[Any] = None  # Will be ServiceDiscovery instance
        self.event_store: Optional[Any] = None     # Will be EventStore instance
        
        # Status tracking
        self.component_status: Dict[str, ComponentStatus] = {}
        
        # Lifecycle management
        self._initialized = False
        self._shutdown = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Event callbacks
        self._startup_callbacks: List[Callable] = []
        self._shutdown_callbacks: List[Callable] = []
        self._health_check_callbacks: List[Callable] = []
    
    async def initialize(self) -> None:
        """
        Initialize all communication components.
        
        This method sets up message brokers, HTTP clients, service discovery,
        gRPC services, and event sourcing based on the configuration.
        """
        if self._initialized:
            self.logger.warning("Communication manager already initialized")
            return
        
        try:
            self.logger.info("Initializing communication manager")
            
            # Initialize service discovery first (other components may depend on it)
            await self._initialize_service_discovery()
            
            # Initialize message brokers
            await self._initialize_message_brokers()
            
            # Initialize HTTP clients
            await self._initialize_http_clients()
            
            # Initialize gRPC services
            await self._initialize_grpc_services()
            
            # Initialize event sourcing
            await self._initialize_event_sourcing()
            
            # Start health check monitoring
            if self.config.enable_health_checks:
                await self._start_health_monitoring()
            
            # Execute startup callbacks
            await self._execute_startup_callbacks()
            
            self._initialized = True
            self.logger.info("Communication manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize communication manager: {e}")
            await self.shutdown()  # Cleanup on failure
            raise CommunicationConfigurationError(
                "Failed to initialize communication manager",
                context=CommunicationErrorContext(details={'error': str(e)}),
                cause=e
            )
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown all communication components.
        """
        if self._shutdown:
            return
        
        self.logger.info("Shutting down communication manager")
        self._shutdown = True
        
        try:
            # Execute shutdown callbacks
            await self._execute_shutdown_callbacks()
            
            # Stop health monitoring
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Shutdown components in reverse order
            await self._shutdown_event_sourcing()
            await self._shutdown_grpc_services()
            await self._shutdown_http_clients()
            await self._shutdown_message_brokers()
            await self._shutdown_service_discovery()
            
            self.logger.info("Communication manager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def _initialize_service_discovery(self) -> None:
        """Initialize service discovery component."""
        if not self.config.service_discovery:
            return
        
        self.logger.info("Initializing service discovery")
        
        # TODO: Implement in subsequent tasks
        # from .discovery.factory import create_service_discovery
        # self.service_discovery = create_service_discovery(self.config.service_discovery)
        # await self.service_discovery.initialize()
        
        # For now, create a placeholder status
        status = ComponentStatus("service_discovery", "service_discovery")
        status.mark_healthy()
        self.component_status["service_discovery"] = status
        
        self.logger.info("Service discovery initialized (placeholder)")
    
    async def _initialize_message_brokers(self) -> None:
        """Initialize message broker components."""
        for name, broker_config in self.config.message_brokers.items():
            self.logger.info(f"Initializing message broker: {name}")
            
            try:
                # Create the appropriate message broker client
                broker = await self._create_message_broker(broker_config)
                
                # Connect to the broker
                await broker.connect()
                
                # Store the broker instance
                self.message_brokers[name] = broker
                
                # Create healthy status
                status = ComponentStatus(name, f"message_broker_{broker_config.type.value}")
                status.mark_healthy()
                status.metadata = {
                    'connection_url': broker_config.connection_url,
                    'type': broker_config.type.value,
                    'pool_size': getattr(broker_config, 'connection_pool_size', 'N/A')
                }
                self.component_status[f"message_broker_{name}"] = status
                
                self.logger.info(f"Message broker {name} ({broker_config.type.value}) initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize message broker {name}: {e}")
                status = ComponentStatus(name, f"message_broker_{broker_config.type.value}")
                status.mark_unhealthy(e)
                self.component_status[f"message_broker_{name}"] = status
                # Don't raise - continue with other brokers
                continue
    
    async def _initialize_http_clients(self) -> None:
        """Initialize HTTP client components."""
        for name, client_config in self.config.http_clients.items():
            self.logger.info(f"Initializing HTTP client: {name}")
            
            try:
                # TODO: Implement in subsequent tasks
                # from .http.factory import create_http_client
                # client = create_http_client(client_config, self.service_discovery)
                # self.http_clients[name] = client
                
                # For now, create a placeholder status
                status = ComponentStatus(name, "http_client")
                status.mark_healthy()
                self.component_status[f"http_client_{name}"] = status
                
                self.logger.info(f"HTTP client {name} initialized (placeholder)")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize HTTP client {name}: {e}")
                status = ComponentStatus(name, "http_client")
                status.mark_unhealthy(e)
                self.component_status[f"http_client_{name}"] = status
                raise
    
    async def _initialize_grpc_services(self) -> None:
        """Initialize gRPC service components."""
        if not self.config.grpc:
            return
        
        self.logger.info("Initializing gRPC services")
        
        try:
            # TODO: Implement in subsequent tasks
            # from .grpc.factory import create_grpc_server
            # grpc_server = create_grpc_server(self.config.grpc)
            # await grpc_server.start()
            # self.grpc_services["server"] = grpc_server
            
            # For now, create a placeholder status
            status = ComponentStatus("grpc_server", "grpc_server")
            status.mark_healthy()
            self.component_status["grpc_server"] = status
            
            self.logger.info("gRPC services initialized (placeholder)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize gRPC services: {e}")
            status = ComponentStatus("grpc_server", "grpc_server")
            status.mark_unhealthy(e)
            self.component_status["grpc_server"] = status
            raise
    
    async def _initialize_event_sourcing(self) -> None:
        """Initialize event sourcing components."""
        if not self.config.event_sourcing.enable_event_store:
            return
        
        self.logger.info("Initializing event sourcing")
        
        try:
            # TODO: Implement in subsequent tasks
            # from .events.factory import create_event_store
            # event_store = create_event_store(self.config.event_sourcing)
            # await event_store.initialize()
            # self.event_store = event_store
            
            # For now, create a placeholder status
            status = ComponentStatus("event_store", "event_store")
            status.mark_healthy()
            self.component_status["event_store"] = status
            
            self.logger.info("Event sourcing initialized (placeholder)")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize event sourcing: {e}")
            status = ComponentStatus("event_store", "event_store")
            status.mark_unhealthy(e)
            self.component_status["event_store"] = status
            raise
    
    async def _start_health_monitoring(self) -> None:
        """Start health check monitoring for all components."""
        self.logger.info("Starting health check monitoring")
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self) -> None:
        """Health check monitoring loop."""
        while not self._shutdown:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all components."""
        for component_name, status in self.component_status.items():
            try:
                # Perform actual health checks for message brokers
                if component_name.startswith('message_broker_'):
                    broker_name = component_name.replace('message_broker_', '')
                    if broker_name in self.message_brokers:
                        broker = self.message_brokers[broker_name]
                        health_result = await broker.health_check()
                        
                        if health_result.get('status') == 'healthy':
                            status.mark_healthy()
                        else:
                            error_msg = health_result.get('error', 'Health check failed')
                            status.mark_unhealthy(Exception(error_msg))
                else:
                    # For other components, just update timestamp (placeholder)
                    status.last_health_check = datetime.now(timezone.utc)
                
                # Execute health check callbacks
                for callback in self._health_check_callbacks:
                    try:
                        await callback(component_name, status)
                    except Exception as e:
                        self.logger.error(f"Health check callback error: {e}")
                        
            except Exception as e:
                self.logger.error(f"Health check failed for {component_name}: {e}")
                status.mark_unhealthy(e)
    
    async def _execute_startup_callbacks(self) -> None:
        """Execute startup callbacks."""
        for callback in self._startup_callbacks:
            try:
                await callback(self)
            except Exception as e:
                self.logger.error(f"Startup callback error: {e}")
    
    async def _execute_shutdown_callbacks(self) -> None:
        """Execute shutdown callbacks."""
        for callback in self._shutdown_callbacks:
            try:
                await callback(self)
            except Exception as e:
                self.logger.error(f"Shutdown callback error: {e}")
    
    async def _create_message_broker(self, broker_config: MessageBrokerConfig) -> MessageBroker:
        """
        Create message broker instance based on configuration.
        
        Args:
            broker_config: Message broker configuration
            
        Returns:
            Message broker instance
            
        Raises:
            CommunicationConfigurationError: If broker type not supported
        """
        from .config import MessageBrokerType
        
        # Create reliability manager if configured (placeholder for now)
        reliability_manager = None
        # TODO: Implement ReliabilityManager in subsequent tasks
        # if hasattr(broker_config, 'reliability') and broker_config.reliability:
        #     reliability_manager = ReliabilityManager(...)
        
        # Create broker based on type
        if broker_config.type == MessageBrokerType.RABBITMQ:
            if not RABBITMQ_AVAILABLE:
                raise CommunicationConfigurationError(
                    "RabbitMQ client not available. Install with: pip install aio-pika",
                    context=CommunicationErrorContext(details={'type': 'rabbitmq'})
                )
            
            from .messaging.rabbitmq import RabbitMQConnectionConfig
            
            # Convert generic config to RabbitMQ specific config
            connection_config = RabbitMQConnectionConfig(
                connection_url=broker_config.connection_url,
                max_connections=getattr(broker_config, 'connection_pool_size', 10),
                heartbeat=getattr(broker_config, 'heartbeat', 600),
                blocked_connection_timeout=getattr(broker_config, 'blocked_connection_timeout', 300)
            )
            
            return RabbitMQClient(
                connection_config=connection_config,
                reliability_manager=reliability_manager
            )
            
        elif broker_config.type == MessageBrokerType.KAFKA:
            if not KAFKA_AVAILABLE:
                raise CommunicationConfigurationError(
                    "Kafka client not available. Install with: pip install aiokafka kafka-python",
                    context=CommunicationErrorContext(details={'type': 'kafka'})
                )
            
            from .messaging.kafka import KafkaConnectionConfig
            
            # Convert generic config to Kafka specific config
            connection_config = KafkaConnectionConfig(
                bootstrap_servers=broker_config.connection_url.split(','),
                client_id=getattr(broker_config, 'client_id', 'communication-manager'),
                security_protocol=getattr(broker_config, 'security_protocol', 'PLAINTEXT')
            )
            
            return KafkaClient(
                connection_config=connection_config,
                reliability_manager=reliability_manager
            )
            
        elif broker_config.type == MessageBrokerType.REDIS:
            if not REDIS_AVAILABLE:
                raise CommunicationConfigurationError(
                    "Redis client not available. Install with: pip install redis[hiredis]",
                    context=CommunicationErrorContext(details={'type': 'redis'})
                )
            
            from .messaging.redis_pubsub import RedisConnectionConfig, RedisPubSubConfig, RedisStreamConfig
            
            # Parse Redis URL
            import urllib.parse
            parsed = urllib.parse.urlparse(broker_config.connection_url)
            
            connection_config = RedisConnectionConfig(
                host=parsed.hostname or 'localhost',
                port=parsed.port or 6379,
                db=int(parsed.path.lstrip('/')) if parsed.path else 0,
                password=parsed.password,
                max_connections=getattr(broker_config, 'connection_pool_size', 10)
            )
            
            pubsub_config = RedisPubSubConfig()
            stream_config = RedisStreamConfig(
                consumer_group="communication-manager",
                consumer_name="manager-consumer"
            )
            
            return RedisClient(
                connection_config=connection_config,
                pubsub_config=pubsub_config,
                stream_config=stream_config
            )
            
        else:
            raise CommunicationConfigurationError(
                f"Unsupported message broker type: {broker_config.type}",
                context=CommunicationErrorContext(details={'type': broker_config.type.value})
            )
    
    async def _shutdown_service_discovery(self) -> None:
        """Shutdown service discovery."""
        if self.service_discovery:
            try:
                # TODO: Implement in subsequent tasks
                # await self.service_discovery.shutdown()
                pass
            except Exception as e:
                self.logger.error(f"Error shutting down service discovery: {e}")
    
    async def _shutdown_message_brokers(self) -> None:
        """Shutdown message brokers."""
        for name, broker in self.message_brokers.items():
            try:
                self.logger.info(f"Shutting down message broker: {name}")
                await broker.disconnect()
                self.logger.info(f"Message broker {name} shutdown completed")
            except Exception as e:
                self.logger.error(f"Error shutting down message broker {name}: {e}")
    
    async def _shutdown_http_clients(self) -> None:
        """Shutdown HTTP clients."""
        for name, client in self.http_clients.items():
            try:
                # TODO: Implement in subsequent tasks
                # await client.close()
                pass
            except Exception as e:
                self.logger.error(f"Error shutting down HTTP client {name}: {e}")
    
    async def _shutdown_grpc_services(self) -> None:
        """Shutdown gRPC services."""
        for name, service in self.grpc_services.items():
            try:
                # TODO: Implement in subsequent tasks
                # await service.stop()
                pass
            except Exception as e:
                self.logger.error(f"Error shutting down gRPC service {name}: {e}")
    
    async def _shutdown_event_sourcing(self) -> None:
        """Shutdown event sourcing."""
        if self.event_store:
            try:
                # TODO: Implement in subsequent tasks
                # await self.event_store.shutdown()
                pass
            except Exception as e:
                self.logger.error(f"Error shutting down event store: {e}")
    
    # Public API methods
    def get_message_broker(self, name: str = "default") -> MessageBroker:
        """
        Get message broker by name.
        
        Args:
            name: Broker name
            
        Returns:
            Message broker instance
            
        Raises:
            CommunicationError: If broker not found or not initialized
        """
        if not self._initialized:
            raise CommunicationError("Communication manager not initialized")
            
        if name not in self.message_brokers:
            available_brokers = list(self.message_brokers.keys())
            raise CommunicationError(
                f"Message broker '{name}' not found. Available brokers: {available_brokers}"
            )
            
        broker = self.message_brokers[name]
        if not broker.is_connected:
            raise CommunicationError(f"Message broker '{name}' is not connected")
            
        return broker
    
    def get_http_client(self, name: str = "default") -> Any:
        """
        Get HTTP client by name.
        
        Args:
            name: Client name
            
        Returns:
            HTTP client instance
            
        Raises:
            CommunicationError: If client not found
        """
        if name not in self.http_clients:
            raise CommunicationError(f"HTTP client '{name}' not found")
        return self.http_clients[name]
    
    def get_grpc_service(self, name: str) -> Any:
        """
        Get gRPC service by name.
        
        Args:
            name: Service name
            
        Returns:
            gRPC service instance
            
        Raises:
            CommunicationError: If service not found
        """
        if name not in self.grpc_services:
            raise CommunicationError(f"gRPC service '{name}' not found")
        return self.grpc_services[name]
    
    def get_service_discovery(self) -> Any:
        """
        Get service discovery instance.
        
        Returns:
            Service discovery instance
            
        Raises:
            CommunicationError: If service discovery not configured
        """
        if not self.service_discovery:
            raise CommunicationError("Service discovery not configured")
        return self.service_discovery
    
    def get_event_store(self) -> Any:
        """
        Get event store instance.
        
        Returns:
            Event store instance
            
        Raises:
            CommunicationError: If event store not configured
        """
        if not self.event_store:
            raise CommunicationError("Event store not configured")
        return self.event_store
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of all components.
        
        Returns:
            Dictionary with component health status
        """
        return {
            'overall_status': 'healthy' if all(
                status.status == 'healthy' 
                for status in self.component_status.values()
            ) else 'unhealthy',
            'components': {
                name: status.to_dict() 
                for name, status in self.component_status.items()
            },
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def add_startup_callback(self, callback: Callable) -> None:
        """Add startup callback."""
        self._startup_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback: Callable) -> None:
        """Add shutdown callback."""
        self._shutdown_callbacks.append(callback)
    
    def add_health_check_callback(self, callback: Callable) -> None:
        """Add health check callback."""
        self._health_check_callbacks.append(callback)
    
    # Convenience methods for message brokers
    async def publish_message(self, broker_name: str, topic: str, message: Any, **kwargs) -> None:
        """
        Publish message using specified broker.
        
        Args:
            broker_name: Name of the message broker
            topic: Topic/queue/channel name
            message: Message to publish
            **kwargs: Additional broker-specific options
        """
        broker = self.get_message_broker(broker_name)
        await broker.publish(topic, message, **kwargs)
    
    async def subscribe_to_topic(self, broker_name: str, topic: str, handler, **kwargs) -> None:
        """
        Subscribe to topic using specified broker.
        
        Args:
            broker_name: Name of the message broker
            topic: Topic/queue/channel name
            handler: Message handler function
            **kwargs: Additional broker-specific options
        """
        broker = self.get_message_broker(broker_name)
        await broker.subscribe(topic, handler, **kwargs)
    
    def list_message_brokers(self) -> List[Dict[str, Any]]:
        """
        List all configured message brokers.
        
        Returns:
            List of broker information
        """
        brokers = []
        for name, broker in self.message_brokers.items():
            status = self.component_status.get(f"message_broker_{name}")
            brokers.append({
                'name': name,
                'type': type(broker).__name__,
                'connected': broker.is_connected if hasattr(broker, 'is_connected') else False,
                'status': status.status if status else 'unknown',
                'last_health_check': status.last_health_check.isoformat() if status and status.last_health_check else None
            })
        return brokers
    
    async def reconnect_message_broker(self, name: str) -> bool:
        """
        Reconnect a specific message broker.
        
        Args:
            name: Broker name
            
        Returns:
            True if reconnection successful
        """
        if name not in self.message_brokers:
            raise CommunicationError(f"Message broker '{name}' not found")
        
        broker = self.message_brokers[name]
        status = self.component_status.get(f"message_broker_{name}")
        
        try:
            self.logger.info(f"Reconnecting message broker: {name}")
            
            # Disconnect if connected
            if hasattr(broker, 'is_connected') and broker.is_connected:
                await broker.disconnect()
            
            # Reconnect
            await broker.connect()
            
            # Update status
            if status:
                status.mark_healthy()
            
            self.logger.info(f"Message broker {name} reconnected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reconnect message broker {name}: {e}")
            if status:
                status.mark_unhealthy(e)
            return False
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for lifecycle management."""
        await self.initialize()
        try:
            yield self
        finally:
            await self.shutdown()
    
    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized
    
    @property
    def is_shutdown(self) -> bool:
        """Check if manager is shutdown."""
        return self._shutdown


# Global instance management
_communication_manager: Optional[CommunicationManager] = None


def get_communication_manager() -> Optional[CommunicationManager]:
    """Get the global communication manager instance."""
    return _communication_manager


def set_communication_manager(manager: CommunicationManager) -> None:
    """Set the global communication manager instance."""
    global _communication_manager
    _communication_manager = manager


async def initialize_communication(config: CommunicationConfig) -> CommunicationManager:
    """
    Initialize global communication manager.
    
    Args:
        config: Communication configuration
        
    Returns:
        Initialized communication manager
    """
    manager = CommunicationManager(config)
    await manager.initialize()
    set_communication_manager(manager)
    return manager


async def shutdown_communication() -> None:
    """Shutdown global communication manager."""
    manager = get_communication_manager()
    if manager:
        await manager.shutdown()
        set_communication_manager(None)
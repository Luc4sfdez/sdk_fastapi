"""
RabbitMQ Client Implementation for FastAPI Microservices SDK.

This module provides a comprehensive RabbitMQ client with advanced features including:
- Exchange and queue management with automatic declaration
- Dead letter queue setup and handling
- Publisher confirms and consumer acknowledgments
- Routing key patterns and message routing logic
- Integration with security system for authentication
- Full integration with reliability patterns (retry, circuit breaker, deduplication, metrics)
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import ssl

try:
    import aio_pika
    from aio_pika import Message as AioPikaMessage, DeliveryMode, ExchangeType
    from aio_pika.abc import AbstractConnection, AbstractChannel, AbstractExchange, AbstractQueue
except ImportError:
    raise ImportError(
        "aio_pika is required for RabbitMQ support. "
        "Install it with: pip install aio_pika"
    )

from ..config import MessageBrokerConfig, MessageBrokerType
from ..exceptions import (
    CommunicationError, 
    MessageBrokerConnectionError, 
    MessageBrokerError,
    MessagePublishError,
    MessageConsumptionError,
    CommunicationConfigurationError
)
from ..logging import CommunicationLogger
from .base import (
    MessageBroker, 
    Message, 
    MessageHandler, 
    MessageAcknowledgment, 
    MessageStatus,
    DeliveryMode as SDKDeliveryMode,
    ReliabilityManager
)


class RabbitMQExchangeType(str, Enum):
    """RabbitMQ exchange types."""
    DIRECT = "direct"
    FANOUT = "fanout"
    TOPIC = "topic"
    HEADERS = "headers"


class RabbitMQQueueType(str, Enum):
    """RabbitMQ queue types."""
    CLASSIC = "classic"
    QUORUM = "quorum"
    STREAM = "stream"


@dataclass
class RabbitMQExchangeConfig:
    """RabbitMQ exchange configuration."""
    name: str
    type: RabbitMQExchangeType = RabbitMQExchangeType.DIRECT
    durable: bool = True
    auto_delete: bool = False
    internal: bool = False
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RabbitMQQueueConfig:
    """RabbitMQ queue configuration."""
    name: str
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    queue_type: RabbitMQQueueType = RabbitMQQueueType.CLASSIC
    max_length: Optional[int] = None
    max_length_bytes: Optional[int] = None
    message_ttl: Optional[int] = None
    expires: Optional[int] = None
    max_priority: Optional[int] = None
    dead_letter_exchange: Optional[str] = None
    dead_letter_routing_key: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    
    def to_arguments(self) -> Dict[str, Any]:
        """Convert queue config to RabbitMQ arguments."""
        args = self.arguments.copy()
        
        if self.queue_type != RabbitMQQueueType.CLASSIC:
            args["x-queue-type"] = self.queue_type.value
        
        if self.max_length is not None:
            args["x-max-length"] = self.max_length
        
        if self.max_length_bytes is not None:
            args["x-max-length-bytes"] = self.max_length_bytes
        
        if self.message_ttl is not None:
            args["x-message-ttl"] = self.message_ttl
        
        if self.expires is not None:
            args["x-expires"] = self.expires
        
        if self.max_priority is not None:
            args["x-max-priority"] = self.max_priority
        
        if self.dead_letter_exchange is not None:
            args["x-dead-letter-exchange"] = self.dead_letter_exchange
        
        if self.dead_letter_routing_key is not None:
            args["x-dead-letter-routing-key"] = self.dead_letter_routing_key
        
        return args


@dataclass
class RabbitMQBindingConfig:
    """RabbitMQ queue binding configuration."""
    queue_name: str
    exchange_name: str
    routing_key: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


class RabbitMQClient(MessageBroker):
    """
    Advanced RabbitMQ client with enterprise features.
    
    Features:
    - Automatic connection management with reconnection
    - Exchange and queue declaration with full configuration
    - Dead letter queue setup and handling
    - Publisher confirms and consumer acknowledgments
    - Message routing with patterns
    - Integration with reliability patterns
    - Security integration for authentication
    - Comprehensive metrics and monitoring
    """
    
    def __init__(
        self,
        config: MessageBrokerConfig,
        reliability_manager: Optional[ReliabilityManager] = None,
        logger: Optional[CommunicationLogger] = None
    ):
        """
        Initialize RabbitMQ client.
        
        Args:
            config: Message broker configuration
            reliability_manager: Reliability manager for patterns
            logger: Communication logger
        """
        if config.type != MessageBrokerType.RABBITMQ:
            raise CommunicationConfigurationError(f"Invalid broker type: {config.type}. Expected: {MessageBrokerType.RABBITMQ}")
        
        super().__init__(config)
        
        # Store additional components
        self.reliability_manager = reliability_manager
        self.logger = logger or CommunicationLogger("rabbitmq_client")
        
        # RabbitMQ specific configuration
        self.rabbitmq_config = config.rabbitmq_config
        
        # Connection and channel management
        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.publisher_confirms: bool = True
        
        # Resource management
        self.exchanges: Dict[str, AbstractExchange] = {}
        self.queues: Dict[str, AbstractQueue] = {}
        self.bindings: Set[str] = set()  # Track bindings to avoid duplicates
        
        # Consumer management
        self.consumers: Dict[str, Any] = {}  # queue_name -> consumer_tag
        self.consumer_handlers: Dict[str, MessageHandler] = {}
        
        # Dead letter queue management
        self.dlq_exchanges: Dict[str, AbstractExchange] = {}
        self.dlq_queues: Dict[str, AbstractQueue] = {}
        
        # Connection state
        self._connection_lock = asyncio.Lock()
        self._is_connecting = False
        
        self.logger.info(
            "RabbitMQ client initialized",
            extra={
                "broker_type": config.type.value,
                "connection_url": self._sanitize_url(config.connection_url),
                "publisher_confirms": self.publisher_confirms
            }
        )
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize connection URL for logging (remove credentials)."""
        try:
            # Simple sanitization - replace password in URL
            if "@" in url and "://" in url:
                protocol, rest = url.split("://", 1)
                if "@" in rest:
                    credentials, host_part = rest.split("@", 1)
                    if ":" in credentials:
                        username, _ = credentials.split(":", 1)
                        return f"{protocol}://{username}:***@{host_part}"
            return url
        except Exception:
            return "***" 
   
    async def connect(self) -> None:
        """Establish connection to RabbitMQ broker."""
        async with self._connection_lock:
            if self.connection and not self.connection.is_closed:
                return
            
            if self._is_connecting:
                # Wait for ongoing connection attempt
                while self._is_connecting:
                    await asyncio.sleep(0.1)
                return
            
            self._is_connecting = True
            
            try:
                self.logger.info("Connecting to RabbitMQ broker")
                
                # Build connection parameters
                connection_kwargs = {
                    "url": self.config.connection_url,
                    "loop": asyncio.get_event_loop()
                }
                
                # Add SSL configuration if enabled
                if self.config.security.enable_tls:
                    ssl_context = self._create_ssl_context()
                    if ssl_context:
                        connection_kwargs["ssl_context"] = ssl_context
                
                # Add connection parameters from config
                if "connection_name" in self.rabbitmq_config:
                    connection_kwargs["client_properties"] = {
                        "connection_name": self.rabbitmq_config["connection_name"]
                    }
                
                # Establish connection
                self.connection = await aio_pika.connect_robust(**connection_kwargs)
                
                # Create channel
                self.channel = await self.connection.channel()
                
                # Enable publisher confirms if configured
                if self.publisher_confirms:
                    await self.channel.set_qos(prefetch_count=1)
                
                self.logger.info(
                    "Successfully connected to RabbitMQ",
                    extra={
                        "connection_id": str(id(self.connection)),
                        "channel_id": str(id(self.channel))
                    }
                )
                
                # Update metrics
                if self.metrics:
                    self.metrics.record_connection_established()
                
            except Exception as e:
                self.logger.error(
                    "Failed to connect to RabbitMQ",
                    extra={"error": str(e)},
                    exc_info=True
                )
                if self.metrics:
                    self.metrics.record_connection_failed()
                raise MessageBrokerConnectionError(f"Failed to connect to RabbitMQ: {e}") from e
            
            finally:
                self._is_connecting = False
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections."""
        if not self.config.security.enable_tls:
            return None
        
        try:
            ssl_context = ssl.create_default_context()
            
            # Configure SSL verification
            if not self.config.security.verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            # Load CA certificate if provided
            if self.config.security.ca_cert_path:
                ssl_context.load_verify_locations(self.config.security.ca_cert_path)
            
            # Load client certificate if provided
            if self.config.security.client_cert_path and self.config.security.client_key_path:
                ssl_context.load_cert_chain(
                    self.config.security.client_cert_path,
                    self.config.security.client_key_path
                )
            
            return ssl_context
        
        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            return None
    
    async def disconnect(self) -> None:
        """Close connection to RabbitMQ broker."""
        try:
            self.logger.info("Disconnecting from RabbitMQ broker")
            
            # Stop all consumers
            for queue_name, consumer_tag in self.consumers.items():
                try:
                    if self.channel and not self.channel.is_closed:
                        await self.channel.basic_cancel(consumer_tag)
                except Exception as e:
                    self.logger.warning(f"Failed to cancel consumer for queue {queue_name}: {e}")
            
            self.consumers.clear()
            self.consumer_handlers.clear()
            
            # Close channel
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            
            # Close connection
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            
            # Clear resources
            self.exchanges.clear()
            self.queues.clear()
            self.bindings.clear()
            self.dlq_exchanges.clear()
            self.dlq_queues.clear()
            
            self.logger.info("Successfully disconnected from RabbitMQ")
            
            # Update metrics
            if self.metrics:
                self.metrics.record_connection_closed()
        
        except Exception as e:
            self.logger.error(f"Error during RabbitMQ disconnect: {e}")
            raise MessageBrokerConnectionError(f"Failed to disconnect from RabbitMQ: {e}") from e
    
    async def health_check(self) -> bool:
        """Check RabbitMQ broker health status."""
        try:
            if not self.connection or self.connection.is_closed:
                return False
            
            if not self.channel or self.channel.is_closed:
                return False
            
            # Try to declare a temporary queue to test connectivity
            temp_queue_name = f"health_check_{datetime.now().timestamp()}"
            temp_queue = await self.channel.declare_queue(
                temp_queue_name,
                exclusive=True,
                auto_delete=True
            )
            await temp_queue.delete()
            
            return True
        
        except Exception as e:
            self.logger.warning(f"RabbitMQ health check failed: {e}")
            return False    

    async def declare_exchange(self, config: RabbitMQExchangeConfig) -> AbstractExchange:
        """Declare RabbitMQ exchange with configuration."""
        await self.ensure_connected()
        
        if config.name in self.exchanges:
            return self.exchanges[config.name]
        
        try:
            self.logger.debug(f"Declaring exchange: {config.name}")
            
            # Convert exchange type
            exchange_type = ExchangeType(config.type.value)
            
            # Declare exchange
            exchange = await self.channel.declare_exchange(
                name=config.name,
                type=exchange_type,
                durable=config.durable,
                auto_delete=config.auto_delete,
                internal=config.internal,
                arguments=config.arguments
            )
            
            self.exchanges[config.name] = exchange
            
            self.logger.info(
                "Exchange declared successfully",
                extra={
                    "exchange_name": config.name,
                    "exchange_type": config.type.value,
                    "durable": config.durable
                }
            )
            
            return exchange
        
        except Exception as e:
            self.logger.error(
                f"Failed to declare exchange {config.name}",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MessageBrokerError(f"Failed to declare exchange {config.name}: {e}") from e
    
    async def declare_queue(self, config: RabbitMQQueueConfig) -> AbstractQueue:
        """Declare RabbitMQ queue with configuration."""
        await self.ensure_connected()
        
        if config.name in self.queues:
            return self.queues[config.name]
        
        try:
            self.logger.debug(f"Declaring queue: {config.name}")
            
            # Build queue arguments
            arguments = config.to_arguments()
            
            # Declare queue
            queue = await self.channel.declare_queue(
                name=config.name,
                durable=config.durable,
                exclusive=config.exclusive,
                auto_delete=config.auto_delete,
                arguments=arguments
            )
            
            self.queues[config.name] = queue
            
            self.logger.info(
                "Queue declared successfully",
                extra={
                    "queue_name": config.name,
                    "durable": config.durable,
                    "queue_type": config.queue_type.value,
                    "arguments": arguments
                }
            )
            
            return queue
        
        except Exception as e:
            self.logger.error(
                f"Failed to declare queue {config.name}",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MessageBrokerError(f"Failed to declare queue {config.name}: {e}") from e
    
    async def bind_queue(self, binding: RabbitMQBindingConfig) -> None:
        """Bind queue to exchange with routing key."""
        await self.ensure_connected()
        
        binding_key = f"{binding.queue_name}:{binding.exchange_name}:{binding.routing_key}"
        if binding_key in self.bindings:
            return
        
        try:
            # Ensure queue and exchange exist
            if binding.queue_name not in self.queues:
                raise MessageBrokerError(f"Queue {binding.queue_name} not declared")
            
            if binding.exchange_name not in self.exchanges:
                raise MessageBrokerError(f"Exchange {binding.exchange_name} not declared")
            
            queue = self.queues[binding.queue_name]
            exchange = self.exchanges[binding.exchange_name]
            
            # Bind queue to exchange
            await queue.bind(
                exchange=exchange,
                routing_key=binding.routing_key,
                arguments=binding.arguments
            )
            
            self.bindings.add(binding_key)
            
            self.logger.info(
                "Queue bound to exchange successfully",
                extra={
                    "queue_name": binding.queue_name,
                    "exchange_name": binding.exchange_name,
                    "routing_key": binding.routing_key
                }
            )
        
        except Exception as e:
            self.logger.error(
                f"Failed to bind queue {binding.queue_name} to exchange {binding.exchange_name}",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MessageBrokerError(
                f"Failed to bind queue {binding.queue_name} to exchange {binding.exchange_name}: {e}"
            ) from e
    
    async def setup_dead_letter_queue(
        self,
        queue_name: str,
        dlq_exchange_name: Optional[str] = None,
        dlq_queue_name: Optional[str] = None
    ) -> tuple[AbstractExchange, AbstractQueue]:
        """Setup dead letter queue for failed messages."""
        await self.ensure_connected()
        
        # Generate DLQ names if not provided
        if not dlq_exchange_name:
            dlq_exchange_name = f"{queue_name}.dlx"
        
        if not dlq_queue_name:
            dlq_queue_name = f"{queue_name}.dlq"
        
        try:
            # Check if DLQ already exists
            if dlq_exchange_name in self.dlq_exchanges and dlq_queue_name in self.dlq_queues:
                return self.dlq_exchanges[dlq_exchange_name], self.dlq_queues[dlq_queue_name]
            
            self.logger.debug(f"Setting up dead letter queue for {queue_name}")
            
            # Declare DLQ exchange
            dlq_exchange_config = RabbitMQExchangeConfig(
                name=dlq_exchange_name,
                type=RabbitMQExchangeType.DIRECT,
                durable=True
            )
            dlq_exchange = await self.declare_exchange(dlq_exchange_config)
            self.dlq_exchanges[dlq_exchange_name] = dlq_exchange
            
            # Declare DLQ queue
            dlq_queue_config = RabbitMQQueueConfig(
                name=dlq_queue_name,
                durable=True,
                queue_type=RabbitMQQueueType.CLASSIC
            )
            dlq_queue = await self.declare_queue(dlq_queue_config)
            self.dlq_queues[dlq_queue_name] = dlq_queue
            
            # Bind DLQ queue to DLQ exchange
            dlq_binding = RabbitMQBindingConfig(
                queue_name=dlq_queue_name,
                exchange_name=dlq_exchange_name,
                routing_key=queue_name  # Use original queue name as routing key
            )
            await self.bind_queue(dlq_binding)
            
            self.logger.info(
                "Dead letter queue setup completed",
                extra={
                    "original_queue": queue_name,
                    "dlq_exchange": dlq_exchange_name,
                    "dlq_queue": dlq_queue_name
                }
            )
            
            return dlq_exchange, dlq_queue
        
        except Exception as e:
            self.logger.error(
                f"Failed to setup dead letter queue for {queue_name}",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MessageBrokerError(f"Failed to setup dead letter queue for {queue_name}: {e}") from e
    
    async def publish(
        self,
        topic: str,
        message: Union[Message, dict, str, bytes],
        routing_key: str = "",
        exchange_name: str = "",
        **kwargs
    ) -> None:
        """Publish message to RabbitMQ exchange."""
        await self.ensure_connected()
        
        # Use topic as routing key if not provided
        if not routing_key:
            routing_key = topic
        
        # Convert message to SDK Message format
        if not isinstance(message, Message):
            sdk_message = Message(
                content=message,
                topic=topic,
                routing_key=routing_key
            )
        else:
            sdk_message = message
            sdk_message.topic = topic
            sdk_message.routing_key = routing_key
        
        # Apply reliability patterns
        async def _publish_operation():
            return await self._do_publish(sdk_message, exchange_name, **kwargs)
        
        if self.reliability_manager:
            await self.reliability_manager.execute_with_reliability(
                operation=_publish_operation,
                operation_type="publish",
                context={"topic": topic, "routing_key": routing_key}
            )
        else:
            await _publish_operation()
    
    async def _do_publish(self, message: Message, exchange_name: str = "", **kwargs) -> None:
        """Internal method to publish message."""
        try:
            start_time = datetime.now()
            
            # Get exchange (use default exchange if not specified)
            if exchange_name:
                if exchange_name not in self.exchanges:
                    raise MessageBrokerError(f"Exchange {exchange_name} not declared")
                exchange = self.exchanges[exchange_name]
            else:
                exchange = self.channel.default_exchange
            
            # Convert SDK delivery mode to aio_pika delivery mode
            delivery_mode = DeliveryMode.PERSISTENT
            if message.delivery_mode == SDKDeliveryMode.AT_MOST_ONCE:
                delivery_mode = DeliveryMode.NOT_PERSISTENT
            
            # Serialize message content
            if isinstance(message.content, (dict, list)):
                body = json.dumps(message.content).encode('utf-8')
                content_type = "application/json"
            elif isinstance(message.content, str):
                body = message.content.encode('utf-8')
                content_type = "text/plain"
            elif isinstance(message.content, bytes):
                body = message.content
                content_type = "application/octet-stream"
            else:
                body = str(message.content).encode('utf-8')
                content_type = "text/plain"
            
            # Build message headers
            headers = message.metadata.copy()
            headers.update({
                "message_id": message.id,
                "timestamp": message.timestamp.isoformat(),
                "correlation_id": message.correlation_id
            })
            
            # Create aio_pika message
            aio_pika_message = AioPikaMessage(
                body=body,
                headers=headers,
                content_type=content_type,
                delivery_mode=delivery_mode,
                message_id=message.id,
                correlation_id=message.correlation_id,
                timestamp=message.timestamp,
                **kwargs
            )
            
            # Publish message
            await exchange.publish(
                message=aio_pika_message,
                routing_key=message.routing_key or message.topic
            )
            
            # Calculate latency
            latency = (datetime.now() - start_time).total_seconds()
            
            # Update metrics
            if self.metrics:
                self.metrics.record_message_published(message.topic, latency)
            
            self.logger.debug(
                "Message published successfully",
                extra={
                    "message_id": message.id,
                    "topic": message.topic,
                    "routing_key": message.routing_key,
                    "exchange": exchange_name or "default",
                    "latency_ms": latency * 1000
                }
            )
        
        except Exception as e:
            # Update metrics
            if self.metrics:
                self.metrics.record_message_publish_error(message.topic, str(e))
            
            self.logger.error(
                "Failed to publish message",
                extra={
                    "message_id": message.id,
                    "topic": message.topic,
                    "error": str(e)
                },
                exc_info=True
            )
            raise MessagePublishError(f"Failed to publish message to {message.topic}: {e}") from e
    
    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler,
        queue_config: Optional[RabbitMQQueueConfig] = None,
        exchange_config: Optional[RabbitMQExchangeConfig] = None,
        binding_config: Optional[RabbitMQBindingConfig] = None,
        **kwargs
    ) -> str:
        """Subscribe to RabbitMQ queue with message handler."""
        await self.ensure_connected()
        
        try:
            self.logger.debug(f"Setting up subscription for topic: {topic}")
            
            # Setup queue configuration
            if not queue_config:
                queue_config = RabbitMQQueueConfig(
                    name=topic,
                    durable=True,
                    queue_type=RabbitMQQueueType.CLASSIC
                )
                
                # Setup dead letter queue if enabled
                if self.config.dead_letter_queue:
                    dlq_exchange, dlq_queue = await self.setup_dead_letter_queue(topic)
                    queue_config.dead_letter_exchange = dlq_exchange.name
                    queue_config.dead_letter_routing_key = topic
            
            # Declare queue
            queue = await self.declare_queue(queue_config)
            
            # Setup exchange and binding if provided
            if exchange_config:
                exchange = await self.declare_exchange(exchange_config)
                
                if binding_config:
                    await self.bind_queue(binding_config)
                else:
                    # Create default binding
                    default_binding = RabbitMQBindingConfig(
                        queue_name=queue_config.name,
                        exchange_name=exchange_config.name,
                        routing_key=topic
                    )
                    await self.bind_queue(default_binding)
            
            # Create message processor with reliability patterns
            async def message_processor(aio_pika_message: AioPikaMessage):
                await self._process_message(aio_pika_message, handler, topic)
            
            # Start consuming
            consumer_tag = await queue.consume(
                callback=message_processor,
                no_ack=False,  # Always use manual acknowledgments
                **kwargs
            )
            
            # Store consumer information
            self.consumers[topic] = consumer_tag
            self.consumer_handlers[topic] = handler
            
            self.logger.info(
                "Successfully subscribed to topic",
                extra={
                    "topic": topic,
                    "queue_name": queue_config.name,
                    "consumer_tag": consumer_tag
                }
            )
            
            return consumer_tag
        
        except Exception as e:
            self.logger.error(
                f"Failed to subscribe to topic {topic}",
                extra={"error": str(e)},
                exc_info=True
            )
            raise MessageConsumptionError(f"Failed to subscribe to topic {topic}: {e}") from e    

    async def _process_message(
        self,
        aio_pika_message: AioPikaMessage,
        handler: MessageHandler,
        topic: str
    ) -> None:
        """Process incoming message with reliability patterns."""
        start_time = datetime.now()
        message_id = aio_pika_message.message_id or f"msg_{datetime.now().timestamp()}"
        
        try:
            # Convert aio_pika message to SDK Message
            sdk_message = await self._convert_aio_pika_message(aio_pika_message, topic)
            
            # Apply deduplication if available
            if self.deduplicator:
                if await self.deduplicator.is_duplicate(sdk_message):
                    self.logger.debug(
                        "Duplicate message detected, acknowledging",
                        extra={"message_id": message_id, "topic": topic}
                    )
                    await aio_pika_message.ack()
                    return
                
                await self.deduplicator.track_message(sdk_message)
            
            # Process message with reliability patterns
            async def _process_operation():
                return await handler.handle(sdk_message)
            
            if self.reliability_manager:
                acknowledgment = await self.reliability_manager.execute_with_reliability(
                    operation=_process_operation,
                    operation_type="consume",
                    context={"topic": topic, "message_id": message_id}
                )
            else:
                acknowledgment = await _process_operation()
            
            # Handle acknowledgment
            if acknowledgment and acknowledgment.status == MessageStatus.SUCCESS:
                await aio_pika_message.ack()
                
                # Calculate processing latency
                latency = (datetime.now() - start_time).total_seconds()
                
                # Update metrics
                if self.metrics:
                    self.metrics.record_message_consumed(topic, latency)
                
                self.logger.debug(
                    "Message processed successfully",
                    extra={
                        "message_id": message_id,
                        "topic": topic,
                        "processing_time_ms": latency * 1000
                    }
                )
            else:
                # Message processing failed
                error_msg = acknowledgment.error_message if acknowledgment else "Unknown error"
                
                # Check if we should retry or send to DLQ
                if self._should_retry_message(aio_pika_message):
                    await aio_pika_message.nack(requeue=True)
                    self.logger.warning(
                        "Message processing failed, requeuing",
                        extra={
                            "message_id": message_id,
                            "topic": topic,
                            "error": error_msg
                        }
                    )
                else:
                    await aio_pika_message.nack(requeue=False)
                    self.logger.error(
                        "Message processing failed, sending to DLQ",
                        extra={
                            "message_id": message_id,
                            "topic": topic,
                            "error": error_msg
                        }
                    )
                
                # Update metrics
                if self.metrics:
                    self.metrics.record_message_consume_error(topic, error_msg)
        
        except Exception as e:
            self.logger.error(
                "Unexpected error processing message",
                extra={
                    "message_id": message_id,
                    "topic": topic,
                    "error": str(e)
                },
                exc_info=True
            )
            
            # Nack message without requeue on unexpected errors
            try:
                await aio_pika_message.nack(requeue=False)
            except Exception as nack_error:
                self.logger.error(f"Failed to nack message: {nack_error}")
            
            # Update metrics
            if self.metrics:
                self.metrics.record_message_consume_error(topic, str(e))
    
    async def _convert_aio_pika_message(self, aio_pika_message: AioPikaMessage, topic: str) -> Message:
        """Convert aio_pika message to SDK Message."""
        try:
            # Deserialize content based on content type
            content_type = aio_pika_message.content_type or "application/octet-stream"
            body = aio_pika_message.body
            
            if content_type == "application/json":
                content = json.loads(body.decode('utf-8'))
            elif content_type == "text/plain":
                content = body.decode('utf-8')
            else:
                content = body
            
            # Extract metadata from headers
            metadata = {}
            if aio_pika_message.headers:
                metadata.update(aio_pika_message.headers)
            
            # Create SDK message
            sdk_message = Message(
                id=aio_pika_message.message_id or f"msg_{datetime.now().timestamp()}",
                content=content,
                topic=topic,
                metadata=metadata,
                correlation_id=aio_pika_message.correlation_id,
                timestamp=aio_pika_message.timestamp or datetime.now()
            )
            
            return sdk_message
        
        except Exception as e:
            self.logger.error(f"Failed to convert aio_pika message: {e}")
            raise MessageBrokerError(f"Failed to convert message: {e}") from e
    
    def _should_retry_message(self, aio_pika_message: AioPikaMessage) -> bool:
        """Determine if message should be retried based on delivery count."""
        try:
            # Check delivery count from headers
            headers = aio_pika_message.headers or {}
            delivery_count = headers.get('x-delivery-count', 0)
            
            # Get max retry attempts from config
            max_attempts = 3
            if self.reliability_manager and self.reliability_manager.retry_policy:
                max_attempts = self.reliability_manager.retry_policy.max_attempts
            
            return delivery_count < max_attempts
        
        except Exception:
            # Default to not retry on errors
            return False
    
    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic."""
        try:
            if topic in self.consumers:
                consumer_tag = self.consumers[topic]
                
                if self.channel and not self.channel.is_closed:
                    await self.channel.basic_cancel(consumer_tag)
                
                del self.consumers[topic]
                
                if topic in self.consumer_handlers:
                    del self.consumer_handlers[topic]
                
                self.logger.info(f"Successfully unsubscribed from topic: {topic}")
            else:
                self.logger.warning(f"No active subscription found for topic: {topic}")
        
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from topic {topic}: {e}")
            raise MessageConsumptionError(f"Failed to unsubscribe from topic {topic}: {e}") from e
    
    async def ensure_connected(self) -> None:
        """Ensure connection is established."""
        if not self.connection or self.connection.is_closed:
            await self.connect()
        
        if not self.channel or self.channel.is_closed:
            await self.connect()
    
    async def get_queue_info(self, queue_name: str) -> Dict[str, Any]:
        """Get information about a queue."""
        await self.ensure_connected()
        
        try:
            if queue_name not in self.queues:
                raise MessageBrokerError(f"Queue {queue_name} not declared")
            
            queue = self.queues[queue_name]
            
            # Get queue declaration result for message count
            declaration_result = await self.channel.declare_queue(
                queue_name,
                passive=True  # Don't create, just get info
            )
            
            return {
                "name": queue_name,
                "message_count": declaration_result.method.message_count,
                "consumer_count": declaration_result.method.consumer_count,
                "durable": queue.durable,
                "exclusive": queue.exclusive,
                "auto_delete": queue.auto_delete
            }
        
        except Exception as e:
            self.logger.error(f"Failed to get queue info for {queue_name}: {e}")
            raise MessageBrokerError(f"Failed to get queue info for {queue_name}: {e}") from e
    
    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from a queue."""
        await self.ensure_connected()
        
        try:
            if queue_name not in self.queues:
                raise MessageBrokerError(f"Queue {queue_name} not declared")
            
            queue = self.queues[queue_name]
            result = await queue.purge()
            
            self.logger.info(f"Purged {result.method.message_count} messages from queue {queue_name}")
            return result.method.message_count
        
        except Exception as e:
            self.logger.error(f"Failed to purge queue {queue_name}: {e}")
            raise MessageBrokerError(f"Failed to purge queue {queue_name}: {e}") from e
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            "broker_type": "rabbitmq",
            "connection_url": self._sanitize_url(self.config.connection_url),
            "connected": self.connection is not None and not self.connection.is_closed,
            "channel_open": self.channel is not None and not self.channel.is_closed,
            "exchanges_count": len(self.exchanges),
            "queues_count": len(self.queues),
            "consumers_count": len(self.consumers),
            "bindings_count": len(self.bindings)
        }


# Factory function for easy RabbitMQ client creation
def create_rabbitmq_client(
    connection_url: str = "amqp://guest:guest@localhost:5672/",
    enable_dead_letter_queue: bool = True,
    enable_security: bool = True,
    **kwargs
) -> RabbitMQClient:
    """Create RabbitMQ client with default configuration."""
    from ..config import MessageBrokerConfig, MessageBrokerType, MessageBrokerSecurityConfig
    
    # Create configuration
    config = MessageBrokerConfig(
        type=MessageBrokerType.RABBITMQ,
        connection_url=connection_url,
        dead_letter_queue=enable_dead_letter_queue,
        security=MessageBrokerSecurityConfig(
            enable_tls=enable_security,
            verify_ssl=enable_security
        ),
        **kwargs
    )
    
    # Create reliability manager
    reliability_manager = ReliabilityManager(config.retry_policy)
    
    # Create logger
    logger = CommunicationLogger("rabbitmq_client")
    
    return RabbitMQClient(
        config=config,
        reliability_manager=reliability_manager,
        logger=logger
    )
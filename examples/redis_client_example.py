"""
Redis Pub/Sub Client Enterprise-Grade Example

This example demonstrates the comprehensive usage of the Redis client with:
- Pub/Sub patterns with channels and pattern matching
- Redis Streams with consumer groups and dead letter streams
- Redis Sentinel for high availability
- SSL/TLS security and authentication
- Connection pooling and resource management
- Reliability patterns integration
- Health monitoring and error handling

Author: FastAPI Microservices SDK Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import ssl
import time
from typing import Dict, Any

from fastapi_microservices_sdk.communication.messaging.redis_pubsub import (
    RedisClient,
    RedisConnectionConfig,
    RedisPubSubConfig,
    RedisStreamConfig,
    RedisSentinelConfig,
    RedisConnectionType,
    RedisMessage
)
from fastapi_microservices_sdk.communication.messaging.base import (
    MessageHandler,
    MessageAcknowledgment,
    MessageStatus
)
from fastapi_microservices_sdk.communication.messaging.reliability import (
    ReliabilityManager,
    RetryPolicyConfig,
    CircuitBreakerConfig,
    DeadLetterQueueConfig
)
from fastapi_microservices_sdk.communication.logging import CommunicationLogger


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = CommunicationLogger(__name__)


class OrderEventHandler(MessageHandler):
    """Example message handler for order events."""
    
    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0
        self.failed_count = 0
    
    async def handle(self, message: RedisMessage, ack: MessageAcknowledgment) -> None:
        """Handle order event message."""
        try:
            logger.info(
                f"[{self.name}] Processing message from {message.channel}",
                extra={
                    "handler": self.name,
                    "channel": message.channel,
                    "message_id": message.message_id,
                    "stream_id": message.stream_id,
                    "consumer_group": message.consumer_group,
                    "delivery_count": message.delivery_count
                }
            )
            
            # Simulate message processing
            if isinstance(message.content, dict):
                order_id = message.content.get('order_id')
                action = message.content.get('action')
                
                logger.info(f"[{self.name}] Processing order {order_id} - {action}")
                
                # Simulate processing time
                await asyncio.sleep(0.1)
                
                # Simulate occasional failures for testing reliability patterns
                if order_id and str(order_id).endswith('999'):
                    raise Exception(f"Simulated processing failure for order {order_id}")
                
                self.processed_count += 1
                ack.status = MessageStatus.SUCCESS
                
                logger.info(
                    f"[{self.name}] Successfully processed order {order_id}",
                    extra={
                        "order_id": order_id,
                        "action": action,
                        "processed_count": self.processed_count
                    }
                )
            else:
                # Handle non-JSON messages
                logger.info(f"[{self.name}] Processing raw message: {message.content}")
                self.processed_count += 1
                ack.status = MessageStatus.SUCCESS
                
        except Exception as e:
            self.failed_count += 1
            ack.status = MessageStatus.FAILED
            ack.error_message = str(e)
            
            logger.error(
                f"[{self.name}] Failed to process message: {e}",
                extra={
                    "error": str(e),
                    "failed_count": self.failed_count,
                    "message_id": message.message_id
                }
            )
            raise


class NotificationHandler(MessageHandler):
    """Example message handler for notifications."""
    
    def __init__(self):
        self.notifications_sent = 0
    
    async def handle(self, message: RedisMessage, ack: MessageAcknowledgment) -> None:
        """Handle notification message."""
        try:
            logger.info(f"Sending notification: {message.content}")
            
            # Simulate notification sending
            await asyncio.sleep(0.05)
            
            self.notifications_sent += 1
            ack.status = MessageStatus.SUCCESS
            
            logger.info(f"Notification sent successfully (total: {self.notifications_sent})")
            
        except Exception as e:
            ack.status = MessageStatus.FAILED
            ack.error_message = str(e)
            logger.error(f"Failed to send notification: {e}")
            raise


async def demonstrate_pubsub_patterns(client: RedisClient):
    """Demonstrate Redis Pub/Sub patterns."""
    logger.info("=== Demonstrating Redis Pub/Sub Patterns ===")
    
    # Create message handlers
    order_handler = OrderEventHandler("PubSub-OrderHandler")
    notification_handler = NotificationHandler()
    
    try:
        # Subscribe to specific channels
        await client.subscribe("orders.created", order_handler)
        await client.subscribe("orders.updated", order_handler)
        await client.subscribe("notifications", notification_handler)
        
        # Subscribe to pattern-based channels (would need pattern support in implementation)
        # await client.subscribe("orders.*", order_handler, use_patterns=True)
        
        logger.info("Subscribed to channels: orders.created, orders.updated, notifications")
        
        # Publish some test messages
        test_messages = [
            ("orders.created", {"order_id": "ORD-001", "action": "created", "customer": "john@example.com"}),
            ("orders.updated", {"order_id": "ORD-002", "action": "updated", "status": "shipped"}),
            ("orders.created", {"order_id": "ORD-999", "action": "created", "customer": "test@example.com"}),  # Will fail
            ("notifications", {"type": "email", "recipient": "admin@example.com", "subject": "Order Alert"}),
        ]
        
        for channel, message in test_messages:
            await client.publish(channel, message)
            logger.info(f"Published message to {channel}: {message}")
            await asyncio.sleep(0.5)  # Give time for processing
        
        # Wait for message processing
        await asyncio.sleep(2)
        
        logger.info(f"Order handler processed: {order_handler.processed_count} messages")
        logger.info(f"Order handler failed: {order_handler.failed_count} messages")
        logger.info(f"Notification handler sent: {notification_handler.notifications_sent} notifications")
        
    except Exception as e:
        logger.error(f"Error in pub/sub demonstration: {e}")
    finally:
        # Unsubscribe from channels
        await client.unsubscribe("orders.created")
        await client.unsubscribe("orders.updated")
        await client.unsubscribe("notifications")
        logger.info("Unsubscribed from all channels")


async def demonstrate_streams_patterns(client: RedisClient):
    """Demonstrate Redis Streams patterns."""
    logger.info("=== Demonstrating Redis Streams Patterns ===")
    
    # Create message handlers
    order_processor = OrderEventHandler("Stream-OrderProcessor")
    
    try:
        # Subscribe to stream with consumer group
        await client.subscribe(
            "order-events-stream",
            order_processor,
            use_streams=True,
            consumer_group="order-processing-group",
            consumer_name="processor-1"
        )
        
        logger.info("Subscribed to stream: order-events-stream with consumer group")
        
        # Publish messages to stream
        stream_messages = [
            {"order_id": "STR-001", "action": "created", "timestamp": int(time.time())},
            {"order_id": "STR-002", "action": "paid", "timestamp": int(time.time())},
            {"order_id": "STR-003", "action": "shipped", "timestamp": int(time.time())},
            {"order_id": "STR-999", "action": "created", "timestamp": int(time.time())},  # Will fail
            {"order_id": "STR-004", "action": "delivered", "timestamp": int(time.time())},
        ]
        
        for message in stream_messages:
            await client.publish(
                "order-events-stream",
                message,
                use_streams=True,
                stream_maxlen=1000  # Keep last 1000 messages
            )
            logger.info(f"Published to stream: {message}")
            await asyncio.sleep(0.3)
        
        # Wait for stream processing
        await asyncio.sleep(3)
        
        logger.info(f"Stream processor handled: {order_processor.processed_count} messages")
        logger.info(f"Stream processor failed: {order_processor.failed_count} messages")
        
    except Exception as e:
        logger.error(f"Error in streams demonstration: {e}")
    finally:
        # Unsubscribe from stream
        await client.unsubscribe("order-events-stream")
        logger.info("Unsubscribed from stream")


async def demonstrate_health_monitoring(client: RedisClient):
    """Demonstrate health monitoring capabilities."""
    logger.info("=== Demonstrating Health Monitoring ===")
    
    try:
        # Get health status
        health = await client.health_check()
        logger.info(f"Redis client health status: {health['status']}")
        
        # Log detailed health information
        for check_name, check_result in health.get('checks', {}).items():
            status = check_result.get('status', 'unknown')
            logger.info(f"  {check_name}: {status}")
            
            # Log additional details for specific checks
            if check_name == 'connection':
                logger.info(f"    Connected: {check_result.get('connected', False)}")
                logger.info(f"    Connection type: {check_result.get('connection_type', 'unknown')}")
            elif check_name == 'pubsub':
                logger.info(f"    Subscribed channels: {check_result.get('subscribed_channels', 0)}")
                logger.info(f"    Subscribed patterns: {check_result.get('subscribed_patterns', 0)}")
            elif check_name == 'streams':
                logger.info(f"    Consumer groups: {check_result.get('consumer_groups', 0)}")
            elif check_name == 'consumers':
                logger.info(f"    Active tasks: {check_result.get('active_tasks', 0)}")
                logger.info(f"    Total tasks: {check_result.get('total_tasks', 0)}")
        
        # Get Redis server info if available
        if hasattr(client, 'get_info'):
            try:
                info = await client.get_info()
                logger.info(f"Redis server version: {info.get('redis_version', 'unknown')}")
                logger.info(f"Connected clients: {info.get('connected_clients', 'unknown')}")
                logger.info(f"Used memory: {info.get('used_memory_human', 'unknown')}")
            except Exception as e:
                logger.warning(f"Could not get Redis server info: {e}")
        
    except Exception as e:
        logger.error(f"Error in health monitoring demonstration: {e}")


async def demonstrate_reliability_patterns(client: RedisClient):
    """Demonstrate reliability patterns integration."""
    logger.info("=== Demonstrating Reliability Patterns ===")
    
    # Create a handler that will fail occasionally
    unreliable_handler = OrderEventHandler("Unreliable-Handler")
    
    try:
        # Subscribe with reliability patterns enabled
        await client.subscribe("unreliable-channel", unreliable_handler)
        
        # Publish messages that will trigger reliability patterns
        test_messages = [
            {"order_id": "REL-001", "action": "test"},
            {"order_id": "REL-999", "action": "test"},  # Will fail and trigger retry/DLQ
            {"order_id": "REL-002", "action": "test"},
            {"order_id": "REL-999", "action": "test"},  # Will fail again
        ]
        
        for message in test_messages:
            await client.publish("unreliable-channel", message)
            await asyncio.sleep(0.5)
        
        # Wait for processing and retries
        await asyncio.sleep(3)
        
        logger.info(f"Reliability test - Processed: {unreliable_handler.processed_count}")
        logger.info(f"Reliability test - Failed: {unreliable_handler.failed_count}")
        
        # Check if reliability manager has metrics
        if client.reliability_manager:
            logger.info("Reliability patterns are active and monitoring failures")
        
    except Exception as e:
        logger.error(f"Error in reliability patterns demonstration: {e}")
    finally:
        await client.unsubscribe("unreliable-channel")


async def main():
    """Main example function."""
    logger.info("Starting Redis Client Enterprise-Grade Example")
    
    # Configuration for different scenarios
    configs = {
        "standalone": {
            "connection": RedisConnectionConfig(
                host="localhost",
                port=6379,
                db=0,
                password=None,  # Set if Redis requires auth
                connection_type=RedisConnectionType.STANDALONE,
                max_connections=50,
                socket_timeout=5.0,
                ssl_enabled=False  # Set to True for SSL/TLS
            ),
            "pubsub": RedisPubSubConfig(
                ignore_subscribe_messages=True,
                decode_responses=True,
                max_connections=10
            ),
            "stream": RedisStreamConfig(
                consumer_group="example-group",
                consumer_name="example-consumer",
                block_time=1000,
                count=10,
                max_deliveries=3,
                dead_letter_stream_suffix=":DLQ"
            )
        },
        
        "sentinel": {
            "connection": RedisConnectionConfig(
                connection_type=RedisConnectionType.SENTINEL,
                max_connections=50
            ),
            "sentinel": RedisSentinelConfig(
                sentinels=[("localhost", 26379)],
                service_name="mymaster",
                socket_timeout=0.5
            ),
            "pubsub": RedisPubSubConfig(),
            "stream": RedisStreamConfig()
        },
        
        "ssl": {
            "connection": RedisConnectionConfig(
                host="redis.example.com",
                port=6380,
                ssl_enabled=True,
                ssl_cert_reqs="required",
                ssl_ca_certs="/path/to/ca.pem",
                ssl_certfile="/path/to/client.pem",
                ssl_keyfile="/path/to/client.key",
                ssl_check_hostname=True
            ),
            "pubsub": RedisPubSubConfig(),
            "stream": RedisStreamConfig()
        }
    }
    
    # Choose configuration (standalone for this example)
    config_name = "standalone"
    config = configs[config_name]
    
    logger.info(f"Using {config_name} configuration")
    
    # Create reliability manager for enhanced patterns
    reliability_config = RetryPolicyConfig(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0,
        exponential_base=2.0,
        jitter=True
    )
    
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
        expected_exception=Exception
    )
    
    dlq_config = DeadLetterQueueConfig(
        max_size=1000,
        ttl_seconds=86400  # 24 hours
    )
    
    reliability_manager = ReliabilityManager(
        retry_config=reliability_config,
        circuit_breaker_config=circuit_breaker_config,
        dlq_config=dlq_config,
        logger=logger
    )
    
    # Create Redis client
    client = RedisClient(
        connection_config=config["connection"],
        pubsub_config=config["pubsub"],
        stream_config=config["stream"],
        sentinel_config=config.get("sentinel"),
        reliability_manager=reliability_manager,
        logger=logger
    )
    
    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await client.connect()
        logger.info("Successfully connected to Redis")
        
        # Demonstrate different features
        await demonstrate_health_monitoring(client)
        await asyncio.sleep(1)
        
        await demonstrate_pubsub_patterns(client)
        await asyncio.sleep(1)
        
        await demonstrate_streams_patterns(client)
        await asyncio.sleep(1)
        
        await demonstrate_reliability_patterns(client)
        await asyncio.sleep(1)
        
        # Final health check
        await demonstrate_health_monitoring(client)
        
    except Exception as e:
        logger.error(f"Error in Redis client example: {e}")
        raise
    finally:
        # Disconnect from Redis
        logger.info("Disconnecting from Redis...")
        await client.disconnect()
        logger.info("Successfully disconnected from Redis")
    
    logger.info("Redis Client Enterprise-Grade Example completed successfully")


if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExample interrupted by user")
    except Exception as e:
        print(f"Example failed with error: {e}")
        raise
"""
RabbitMQ Client Example for FastAPI Microservices SDK.

This example demonstrates the comprehensive usage of the RabbitMQ client including:
- Connection management with SSL and authentication
- Exchange and queue declaration with advanced configurations
- Message publishing with different formats and routing patterns
- Message consumption with acknowledgments and error handling
- Dead letter queue setup and handling
- Integration with reliability patterns (retry, circuit breaker, deduplication)
- Queue management operations and monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi_microservices_sdk.communication.messaging.rabbitmq import (
    RabbitMQClient,
    RabbitMQExchangeConfig,
    RabbitMQQueueConfig,
    RabbitMQBindingConfig,
    RabbitMQExchangeType,
    RabbitMQQueueType,
    create_rabbitmq_client
)
from fastapi_microservices_sdk.communication.config import (
    MessageBrokerConfig,
    MessageBrokerType,
    MessageBrokerSecurityConfig,
    RetryPolicyConfig
)
from fastapi_microservices_sdk.communication.messaging.base import (
    Message,
    MessageHandler,
    MessageAcknowledgment,
    MessageStatus,
    DeliveryMode
)
from fastapi_microservices_sdk.communication.messaging.reliability import ReliabilityManager
from fastapi_microservices_sdk.communication.logging import CommunicationLogger


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderHandler(MessageHandler):
    """Example message handler for order processing."""
    
    async def handle(self, message: Message) -> MessageAcknowledgment:
        """Handle order message."""
        try:
            logger.info(f"Processing order message: {message.id}")
            
            # Simulate order processing
            order_data = message.content
            
            if isinstance(order_data, dict):
                order_id = order_data.get('order_id')
                customer_id = order_data.get('customer_id')
                amount = order_data.get('amount', 0)
                
                logger.info(f"Order {order_id} for customer {customer_id}, amount: ${amount}")
                
                # Simulate processing time
                await asyncio.sleep(0.1)
                
                # Simulate occasional failures for demonstration
                if order_id and str(order_id).endswith('999'):
                    logger.error(f"Simulated failure for order {order_id}")
                    return MessageAcknowledgment(
                        message_id=message.id,
                        status=MessageStatus.FAILED,
                        error_message="Simulated processing failure",
                        processing_time=0.1
                    )
                
                logger.info(f"Successfully processed order {order_id}")
                return MessageAcknowledgment(
                    message_id=message.id,
                    status=MessageStatus.SUCCESS,
                    processing_time=0.1
                )
            else:
                logger.warning(f"Invalid order data format: {type(order_data)}")
                return MessageAcknowledgment(
                    message_id=message.id,
                    status=MessageStatus.FAILED,
                    error_message="Invalid message format",
                    processing_time=0.1
                )
        
        except Exception as e:
            logger.error(f"Error processing order message: {e}")
            return MessageAcknowledgment(
                message_id=message.id,
                status=MessageStatus.FAILED,
                error_message=str(e),
                processing_time=0.1
            )


class NotificationHandler(MessageHandler):
    """Example message handler for notifications."""
    
    async def handle(self, message: Message) -> MessageAcknowledgment:
        """Handle notification message."""
        try:
            logger.info(f"Processing notification message: {message.id}")
            
            notification_data = message.content
            
            if isinstance(notification_data, dict):
                notification_type = notification_data.get('type')
                recipient = notification_data.get('recipient')
                content = notification_data.get('content')
                
                logger.info(f"Sending {notification_type} notification to {recipient}")
                logger.info(f"Content: {content}")
                
                # Simulate notification sending
                await asyncio.sleep(0.05)
                
                logger.info(f"Successfully sent notification {message.id}")
                return MessageAcknowledgment(
                    message_id=message.id,
                    status=MessageStatus.SUCCESS,
                    processing_time=0.05
                )
            else:
                return MessageAcknowledgment(
                    message_id=message.id,
                    status=MessageStatus.FAILED,
                    error_message="Invalid notification format",
                    processing_time=0.05
                )
        
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            return MessageAcknowledgment(
                message_id=message.id,
                status=MessageStatus.FAILED,
                error_message=str(e),
                processing_time=0.05
            )


async def setup_rabbitmq_infrastructure(client: RabbitMQClient):
    """Setup RabbitMQ exchanges, queues, and bindings."""
    logger.info("Setting up RabbitMQ infrastructure...")
    
    # 1. Declare exchanges
    logger.info("Declaring exchanges...")
    
    # Orders exchange (topic exchange for routing by order type)
    orders_exchange = RabbitMQExchangeConfig(
        name="orders.exchange",
        type=RabbitMQExchangeType.TOPIC,
        durable=True,
        arguments={"description": "Orders processing exchange"}
    )
    await client.declare_exchange(orders_exchange)
    
    # Notifications exchange (direct exchange for simple routing)
    notifications_exchange = RabbitMQExchangeConfig(
        name="notifications.exchange",
        type=RabbitMQExchangeType.DIRECT,
        durable=True
    )
    await client.declare_exchange(notifications_exchange)
    
    # 2. Declare queues with advanced configurations
    logger.info("Declaring queues...")
    
    # High priority orders queue (quorum queue for high availability)
    high_priority_orders_queue = RabbitMQQueueConfig(
        name="orders.high_priority",
        durable=True,
        queue_type=RabbitMQQueueType.QUORUM,
        max_length=10000,
        message_ttl=3600000,  # 1 hour TTL
        max_priority=10,
        dead_letter_exchange="orders.dlx",
        dead_letter_routing_key="orders.high_priority.failed"
    )
    await client.declare_queue(high_priority_orders_queue)
    
    # Standard orders queue (classic queue)
    standard_orders_queue = RabbitMQQueueConfig(
        name="orders.standard",
        durable=True,
        queue_type=RabbitMQQueueType.CLASSIC,
        max_length=50000,
        message_ttl=7200000,  # 2 hours TTL
        dead_letter_exchange="orders.dlx",
        dead_letter_routing_key="orders.standard.failed"
    )
    await client.declare_queue(standard_orders_queue)
    
    # Email notifications queue
    email_notifications_queue = RabbitMQQueueConfig(
        name="notifications.email",
        durable=True,
        max_length=100000,
        dead_letter_exchange="notifications.dlx",
        dead_letter_routing_key="notifications.email.failed"
    )
    await client.declare_queue(email_notifications_queue)
    
    # SMS notifications queue
    sms_notifications_queue = RabbitMQQueueConfig(
        name="notifications.sms",
        durable=True,
        max_length=100000,
        dead_letter_exchange="notifications.dlx",
        dead_letter_routing_key="notifications.sms.failed"
    )
    await client.declare_queue(sms_notifications_queue)
    
    # 3. Setup dead letter queues
    logger.info("Setting up dead letter queues...")
    await client.setup_dead_letter_queue("orders.high_priority")
    await client.setup_dead_letter_queue("orders.standard")
    await client.setup_dead_letter_queue("notifications.email")
    await client.setup_dead_letter_queue("notifications.sms")
    
    # 4. Create bindings
    logger.info("Creating queue bindings...")
    
    # Bind high priority orders
    high_priority_binding = RabbitMQBindingConfig(
        queue_name="orders.high_priority",
        exchange_name="orders.exchange",
        routing_key="orders.high_priority.*"
    )
    await client.bind_queue(high_priority_binding)
    
    # Bind standard orders
    standard_binding = RabbitMQBindingConfig(
        queue_name="orders.standard",
        exchange_name="orders.exchange",
        routing_key="orders.standard.*"
    )
    await client.bind_queue(standard_binding)
    
    # Bind email notifications
    email_binding = RabbitMQBindingConfig(
        queue_name="notifications.email",
        exchange_name="notifications.exchange",
        routing_key="email"
    )
    await client.bind_queue(email_binding)
    
    # Bind SMS notifications
    sms_binding = RabbitMQBindingConfig(
        queue_name="notifications.sms",
        exchange_name="notifications.exchange",
        routing_key="sms"
    )
    await client.bind_queue(sms_binding)
    
    logger.info("RabbitMQ infrastructure setup completed!")


async def publish_sample_messages(client: RabbitMQClient):
    """Publish sample messages to demonstrate different scenarios."""
    logger.info("Publishing sample messages...")
    
    # 1. Publish high priority orders
    logger.info("Publishing high priority orders...")
    for i in range(5):
        order_data = {
            "order_id": f"HP{i+1:03d}",
            "customer_id": f"CUST{i+1:04d}",
            "amount": 1000 + (i * 100),
            "priority": "high",
            "timestamp": datetime.now().isoformat()
        }
        
        await client.publish(
            topic="orders.high_priority.new",
            message=order_data,
            exchange_name="orders.exchange",
            routing_key="orders.high_priority.new"
        )
    
    # 2. Publish standard orders (including one that will fail)
    logger.info("Publishing standard orders...")
    for i in range(8):
        order_id = f"ST{i+1:03d}" if i < 7 else "ST999"  # Last one will fail
        order_data = {
            "order_id": order_id,
            "customer_id": f"CUST{i+10:04d}",
            "amount": 100 + (i * 50),
            "priority": "standard",
            "timestamp": datetime.now().isoformat()
        }
        
        await client.publish(
            topic="orders.standard.new",
            message=order_data,
            exchange_name="orders.exchange",
            routing_key="orders.standard.new"
        )
    
    # 3. Publish email notifications
    logger.info("Publishing email notifications...")
    for i in range(3):
        notification_data = {
            "type": "email",
            "recipient": f"user{i+1}@example.com",
            "subject": f"Order Confirmation #{i+1}",
            "content": f"Your order has been confirmed and is being processed.",
            "timestamp": datetime.now().isoformat()
        }
        
        await client.publish(
            topic="notifications.email",
            message=notification_data,
            exchange_name="notifications.exchange",
            routing_key="email"
        )
    
    # 4. Publish SMS notifications
    logger.info("Publishing SMS notifications...")
    for i in range(2):
        notification_data = {
            "type": "sms",
            "recipient": f"+1555000{i+1:04d}",
            "content": f"Your order #{i+1} has been shipped!",
            "timestamp": datetime.now().isoformat()
        }
        
        await client.publish(
            topic="notifications.sms",
            message=notification_data,
            exchange_name="notifications.exchange",
            routing_key="sms"
        )
    
    # 5. Publish different message formats
    logger.info("Publishing different message formats...")
    
    # String message
    await client.publish(
        topic="orders.standard.text",
        message="Simple text order message",
        exchange_name="orders.exchange",
        routing_key="orders.standard.text"
    )
    
    # Binary message
    await client.publish(
        topic="orders.standard.binary",
        message=b"\x00\x01\x02\x03Binary order data",
        exchange_name="orders.exchange",
        routing_key="orders.standard.binary"
    )
    
    # SDK Message object
    sdk_message = Message(
        id="custom_msg_001",
        content={"custom": "message", "with": "metadata"},
        topic="orders.high_priority.custom",
        correlation_id="corr_001",
        metadata={"source": "example_app", "version": "1.0"},
        delivery_mode=DeliveryMode.EXACTLY_ONCE
    )
    
    await client.publish(
        topic="orders.high_priority.custom",
        message=sdk_message,
        exchange_name="orders.exchange",
        routing_key="orders.high_priority.custom"
    )
    
    logger.info("Sample messages published!")


async def setup_consumers(client: RabbitMQClient):
    """Setup message consumers."""
    logger.info("Setting up message consumers...")
    
    # Create handlers
    order_handler = OrderHandler()
    notification_handler = NotificationHandler()
    
    # Subscribe to high priority orders
    await client.subscribe(
        topic="orders.high_priority",
        handler=order_handler
    )
    logger.info("Subscribed to high priority orders")
    
    # Subscribe to standard orders
    await client.subscribe(
        topic="orders.standard",
        handler=order_handler
    )
    logger.info("Subscribed to standard orders")
    
    # Subscribe to email notifications
    await client.subscribe(
        topic="notifications.email",
        handler=notification_handler
    )
    logger.info("Subscribed to email notifications")
    
    # Subscribe to SMS notifications
    await client.subscribe(
        topic="notifications.sms",
        handler=notification_handler
    )
    logger.info("Subscribed to SMS notifications")
    
    logger.info("All consumers setup completed!")


async def monitor_queues(client: RabbitMQClient):
    """Monitor queue status and metrics."""
    logger.info("Monitoring queue status...")
    
    queues_to_monitor = [
        "orders.high_priority",
        "orders.standard",
        "notifications.email",
        "notifications.sms"
    ]
    
    for queue_name in queues_to_monitor:
        try:
            info = await client.get_queue_info(queue_name)
            logger.info(f"Queue {queue_name}: {info['message_count']} messages, {info['consumer_count']} consumers")
        except Exception as e:
            logger.error(f"Failed to get info for queue {queue_name}: {e}")
    
    # Show connection info
    conn_info = client.get_connection_info()
    logger.info(f"Connection info: {conn_info}")


async def demonstrate_queue_management(client: RabbitMQClient):
    """Demonstrate queue management operations."""
    logger.info("Demonstrating queue management...")
    
    # Create a temporary queue for demonstration
    temp_queue_config = RabbitMQQueueConfig(
        name="temp.demo.queue",
        durable=False,
        auto_delete=True
    )
    await client.declare_queue(temp_queue_config)
    
    # Publish some messages to it
    for i in range(5):
        await client.publish(
            topic="temp.demo.queue",
            message=f"Demo message {i+1}"
        )
    
    # Check queue info
    info = await client.get_queue_info("temp.demo.queue")
    logger.info(f"Temp queue has {info['message_count']} messages")
    
    # Purge the queue
    purged_count = await client.purge_queue("temp.demo.queue")
    logger.info(f"Purged {purged_count} messages from temp queue")
    
    # Check again
    info = await client.get_queue_info("temp.demo.queue")
    logger.info(f"Temp queue now has {info['message_count']} messages")


async def main():
    """Main example function."""
    logger.info("Starting RabbitMQ Client Example")
    
    try:
        # 1. Create RabbitMQ client with configuration
        logger.info("Creating RabbitMQ client...")
        
        # Option 1: Using factory function (simple)
        # client = create_rabbitmq_client(
        #     connection_url="amqp://guest:guest@localhost:5672/",
        #     enable_dead_letter_queue=True,
        #     enable_security=False  # Disable for local development
        # )
        
        # Option 2: Using full configuration (advanced)
        config = MessageBrokerConfig(
            type=MessageBrokerType.RABBITMQ,
            connection_url="amqp://guest:guest@localhost:5672/",
            connection_pool_size=10,
            dead_letter_queue=True,
            security=MessageBrokerSecurityConfig(
                enable_tls=False,  # Disable for local development
                verify_ssl=False,
                username="guest",
                password="guest"
            ),
            retry_policy=RetryPolicyConfig(
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            ),
            rabbitmq_config={
                "connection_name": "FastAPI-Microservices-SDK-Example"
            }
        )
        
        reliability_manager = ReliabilityManager(config.retry_policy)
        logger_instance = CommunicationLogger("rabbitmq_example")
        
        client = RabbitMQClient(
            config=config,
            reliability_manager=reliability_manager,
            logger=logger_instance
        )
        
        # 2. Connect to RabbitMQ
        logger.info("Connecting to RabbitMQ...")
        await client.connect()
        
        # 3. Check health
        is_healthy = await client.health_check()
        logger.info(f"RabbitMQ health check: {'PASSED' if is_healthy else 'FAILED'}")
        
        if not is_healthy:
            logger.error("RabbitMQ is not healthy, exiting...")
            return
        
        # 4. Setup infrastructure
        await setup_rabbitmq_infrastructure(client)
        
        # 5. Setup consumers
        await setup_consumers(client)
        
        # 6. Publish sample messages
        await publish_sample_messages(client)
        
        # 7. Wait for message processing
        logger.info("Waiting for message processing...")
        await asyncio.sleep(5)
        
        # 8. Monitor queues
        await monitor_queues(client)
        
        # 9. Demonstrate queue management
        await demonstrate_queue_management(client)
        
        # 10. Wait a bit more to see all processing
        logger.info("Waiting for final message processing...")
        await asyncio.sleep(3)
        
        # 11. Final monitoring
        await monitor_queues(client)
        
        logger.info("Example completed successfully!")
    
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
    
    finally:
        # Cleanup
        try:
            if 'client' in locals():
                logger.info("Disconnecting from RabbitMQ...")
                await client.disconnect()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
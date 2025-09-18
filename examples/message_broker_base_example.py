"""
Message Broker Base Interface and Reliability Patterns Example.

This example demonstrates the base message broker interface, reliability patterns,
dead letter queues, circuit breakers, and message deduplication.
"""

import asyncio
import json
import time
from datetime import datetime, timezone

from fastapi_microservices_sdk.communication.messaging import (
    MessageBroker,
    Message,
    MessageAcknowledgment,
    MessageHandler,
    MessageStatus,
    DeliveryMode,
    ReliabilityManager,
    DeadLetterQueue,
    MessageDeduplicator,
    MessagingCircuitBreaker,
    MessageMetrics
)

from fastapi_microservices_sdk.communication import (
    MessageBrokerConfig,
    RetryPolicyConfig,
    MessageBrokerType,
    MessagePublishError,
    MessageConsumptionError
)

from fastapi_microservices_sdk.communication.logging import (
    CommunicationLogger,
    CorrelationContext
)

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = CommunicationLogger("message_broker_example")


class ExampleMessageHandler(MessageHandler):
    """Example message handler that can simulate failures."""
    
    def __init__(self, name: str, failure_rate: float = 0.0):
        """
        Initialize handler.
        
        Args:
            name: Handler name
            failure_rate: Probability of failure (0.0 to 1.0)
        """
        self.name = name
        self.failure_rate = failure_rate
        self.processed_count = 0
        self.failed_count = 0
        self.logger = CommunicationLogger(f"handler_{name}")
    
    async def handle_message(self, message: Message) -> MessageAcknowledgment:
        """Handle a message with optional failure simulation."""
        self.processed_count += 1
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        # Simulate random failures
        import random
        if random.random() < self.failure_rate:
            self.failed_count += 1
            raise Exception(f"Handler {self.name} simulated failure")
        
        self.logger.info(
            f"Message processed successfully by {self.name}",
            metadata={
                'message_id': message.id,
                'topic': message.topic,
                'processed_count': self.processed_count
            }
        )
        
        return MessageAcknowledgment(
            message_id=message.id,
            status=MessageStatus.ACKNOWLEDGED
        )


class MockMessageBroker(MessageBroker):
    """Mock message broker for demonstration purposes."""
    
    def __init__(self, config: MessageBrokerConfig):
        super().__init__(config)
        self.published_messages = []
        self.subscribers = {}
        self.should_fail_publish = False
        self.should_fail_connect = False
    
    async def connect(self) -> None:
        """Connect to mock broker."""
        if self.should_fail_connect:
            raise Exception("Mock connection failure")
        
        self._connected = True
        self.logger.info("Connected to mock message broker")
    
    async def disconnect(self) -> None:
        """Disconnect from mock broker."""
        self._connected = False
        self.logger.info("Disconnected from mock message broker")
    
    async def publish(self, topic: str, message, **kwargs) -> str:
        """Publish message to mock broker."""
        if not self._connected:
            raise MessagePublishError("Not connected to broker")
        
        if self.should_fail_publish:
            raise MessagePublishError("Mock publish failure")
        
        msg = self._ensure_message(message)
        msg.topic = topic
        
        self.published_messages.append(msg)
        
        self.logger.log_message_publish(
            self.config.type.value,
            topic,
            message_size=len(msg.serialize())
        )
        
        return msg.id
    
    async def subscribe(self, topic: str, handler: MessageHandler, **kwargs) -> None:
        """Subscribe to topic with handler."""
        if not self._connected:
            raise MessageConsumptionError("Not connected to broker")
        
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(handler)
        
        self.logger.info(
            f"Subscribed to topic {topic}",
            metadata={'topic': topic, 'handler': handler.__class__.__name__}
        )
    
    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from topic."""
        if topic in self.subscribers:
            del self.subscribers[topic]
        
        self.logger.info(f"Unsubscribed from topic {topic}")
    
    async def health_check(self) -> bool:
        """Check broker health."""
        return self._connected
    
    async def simulate_message_delivery(self, topic: str, message: Message) -> None:
        """Simulate delivering a message to subscribers."""
        if topic not in self.subscribers:
            return
        
        for handler in self.subscribers[topic]:
            try:
                ack = await self._process_message(message, handler)
                
                self.logger.info(
                    f"Message delivery result: {ack.status.value}",
                    metadata={
                        'message_id': message.id,
                        'topic': topic,
                        'handler': handler.__class__.__name__
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    f"Message delivery failed: {e}",
                    metadata={
                        'message_id': message.id,
                        'topic': topic,
                        'error': str(e)
                    }
                )


async def demonstrate_message_operations():
    """Demonstrate basic message operations."""
    
    logger.info("=== Message Operations Demo ===")
    
    # Create messages
    message1 = Message(
        topic="user.events",
        payload={"user_id": 123, "action": "login"},
        correlation_id="demo-001",
        delivery_mode=DeliveryMode.AT_LEAST_ONCE
    )
    
    message2 = Message(
        topic="order.events", 
        payload="Order created: #12345",
        content_type="text/plain"
    )
    
    # Demonstrate serialization
    logger.info("Message serialization demo")
    
    serialized1 = message1.serialize()
    logger.info(f"JSON message serialized: {len(serialized1)} bytes")
    
    serialized2 = message2.serialize()
    logger.info(f"Text message serialized: {len(serialized2)} bytes")
    
    # Demonstrate deserialization
    deserialized1 = Message.deserialize(serialized1, "application/json")
    logger.info(f"Deserialized message topic: {deserialized1.topic}")
    
    # Demonstrate message conversion
    dict_data = message1.to_dict()
    message_from_dict = Message.from_dict(dict_data)
    logger.info(f"Round-trip conversion successful: {message_from_dict.id == message1.id}")


async def demonstrate_reliability_manager():
    """Demonstrate reliability manager with retry logic."""
    
    logger.info("=== Reliability Manager Demo ===")
    
    # Create retry configuration
    retry_config = RetryPolicyConfig(
        max_attempts=3,
        base_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter=False
    )
    
    reliability_manager = ReliabilityManager(retry_config)
    
    # Test successful operation
    logger.info("Testing successful operation")
    
    async def successful_operation():
        return "Operation succeeded"
    
    result = await reliability_manager.execute_with_retry(successful_operation)
    logger.info(f"Result: {result}")
    
    # Test operation that succeeds after retries
    logger.info("Testing operation with eventual success")
    
    attempt_count = 0
    
    async def eventually_successful_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"Temporary failure (attempt {attempt_count})")
        return "Eventually succeeded"
    
    result = await reliability_manager.execute_with_retry(eventually_successful_operation)
    logger.info(f"Result after retries: {result}")
    
    # Test failed message handling
    logger.info("Testing failed message handling")
    
    message = Message(id="test-msg", retry_count=1, max_retries=3)
    error = Exception("Processing error")
    
    ack = await reliability_manager.handle_failed_message(message, error)
    logger.info(f"Failed message handling result: {ack.status.value}, retry_count: {ack.retry_count}")


async def demonstrate_dead_letter_queue():
    """Demonstrate dead letter queue functionality."""
    
    logger.info("=== Dead Letter Queue Demo ===")
    
    dlq = DeadLetterQueue(max_size=100)
    
    # Add failed messages
    failed_messages = []
    for i in range(3):
        message = Message(
            id=f"failed-msg-{i}",
            topic="test.topic",
            payload=f"Message {i} data"
        )
        failed_messages.append(message)
        
        await dlq.add_message(message, f"Processing error {i}", "test.topic")
    
    # Get statistics
    stats = await dlq.get_statistics()
    logger.info(f"DLQ Statistics: {stats}")
    
    # Retrieve messages by topic
    topic_messages = await dlq.get_messages_by_topic("test.topic")
    logger.info(f"Messages in topic 'test.topic': {len(topic_messages)}")
    
    # Simulate reprocessing
    logger.info("Simulating message reprocessing")
    
    async def reprocess_handler(message):
        logger.info(f"Reprocessing message {message.id}")
        # Simulate successful reprocessing
        return True
    
    success = await dlq.reprocess_message("failed-msg-0", reprocess_handler)
    logger.info(f"Reprocessing result: {success}")
    
    # Check updated statistics
    stats = await dlq.get_statistics()
    logger.info(f"Updated DLQ Statistics: {stats}")


async def demonstrate_message_deduplication():
    """Demonstrate message deduplication."""
    
    logger.info("=== Message Deduplication Demo ===")
    
    deduplicator = MessageDeduplicator(window_minutes=60, max_entries=1000)
    
    # Test duplicate detection by ID
    message1 = Message(id="duplicate-test", payload="Original message")
    message2 = Message(id="duplicate-test", payload="Duplicate message")
    
    is_dup1 = await deduplicator.is_duplicate(message1)
    is_dup2 = await deduplicator.is_duplicate(message2)
    
    logger.info(f"First message duplicate: {is_dup1}")
    logger.info(f"Second message duplicate: {is_dup2}")
    
    # Test content-based deduplication
    message3 = Message(topic="test", payload="content", correlation_id="123")
    message4 = Message(topic="test", payload="content", correlation_id="123")
    
    # Clear IDs to force content hashing
    message3.id = ""
    message4.id = ""
    
    is_dup3 = await deduplicator.is_duplicate(message3)
    is_dup4 = await deduplicator.is_duplicate(message4)
    
    logger.info(f"Content-based - First message duplicate: {is_dup3}")
    logger.info(f"Content-based - Second message duplicate: {is_dup4}")
    
    # Get statistics
    stats = await deduplicator.get_statistics()
    logger.info(f"Deduplicator statistics: {stats}")


async def demonstrate_circuit_breaker():
    """Demonstrate messaging circuit breaker."""
    
    logger.info("=== Circuit Breaker Demo ===")
    
    circuit_breaker = MessagingCircuitBreaker(
        failure_threshold=3,
        recovery_timeout=2,
        success_threshold=2
    )
    
    # Test successful operations
    logger.info("Testing successful operations")
    
    async def successful_operation():
        return "Success"
    
    for i in range(2):
        result = await circuit_breaker.call(successful_operation)
        logger.info(f"Operation {i+1} result: {result}")
    
    # Test failing operations to open circuit
    logger.info("Testing failing operations")
    
    async def failing_operation():
        raise Exception("Operation failed")
    
    for i in range(3):
        try:
            await circuit_breaker.call(failing_operation)
        except Exception as e:
            logger.info(f"Failure {i+1}: {e}")
    
    # Check circuit state
    status = await circuit_breaker.get_status()
    logger.info(f"Circuit breaker status: {status}")
    
    # Try operation while circuit is open
    try:
        await circuit_breaker.call(successful_operation)
    except Exception as e:
        logger.info(f"Circuit open error: {e}")
    
    # Wait for recovery and test
    logger.info("Waiting for circuit recovery...")
    await asyncio.sleep(2.1)
    
    # Should transition to half-open and allow operations
    result = await circuit_breaker.call(successful_operation)
    logger.info(f"Recovery operation result: {result}")
    
    # Complete recovery
    result = await circuit_breaker.call(successful_operation)
    logger.info(f"Final recovery operation result: {result}")
    
    status = await circuit_breaker.get_status()
    logger.info(f"Final circuit breaker status: {status}")


async def demonstrate_message_metrics():
    """Demonstrate message metrics collection."""
    
    logger.info("=== Message Metrics Demo ===")
    
    metrics = MessageMetrics(window_minutes=5)
    
    # Simulate message operations
    topics = ["user.events", "order.events", "notification.events"]
    
    for i in range(10):
        topic = topics[i % len(topics)]
        
        # Record publish metrics
        publish_latency = 50 + (i * 10)  # Simulate varying latency
        await metrics.record_publish(topic, publish_latency)
        
        # Record consume metrics
        consume_latency = 25 + (i * 5)
        await metrics.record_consume(topic, consume_latency)
        
        # Occasionally record errors
        if i % 4 == 0:
            await metrics.record_error(topic, "timeout_error")
    
    # Get metrics summary
    stats = await metrics.get_metrics()
    
    logger.info("Message Metrics Summary:")
    logger.info(f"  Publish throughput: {stats['publish_throughput_per_minute']:.2f} msg/min")
    logger.info(f"  Consume throughput: {stats['consume_throughput_per_minute']:.2f} msg/min")
    logger.info(f"  Avg publish latency: {stats['avg_publish_latency_ms']:.2f} ms")
    logger.info(f"  Avg consume latency: {stats['avg_consume_latency_ms']:.2f} ms")
    logger.info(f"  Total errors: {stats['total_errors']}")
    
    for topic, topic_stats in stats['topic_metrics'].items():
        logger.info(f"  Topic {topic}: {topic_stats}")


async def demonstrate_mock_broker_integration():
    """Demonstrate integration with mock message broker."""
    
    logger.info("=== Mock Broker Integration Demo ===")
    
    # Create broker configuration
    config = MessageBrokerConfig(
        type=MessageBrokerType.MEMORY,
        connection_url="memory://test",
        retry_policy=RetryPolicyConfig(max_attempts=3)
    )
    
    # Create mock broker
    broker = MockMessageBroker(config)
    
    # Connect to broker
    await broker.connect()
    
    # Create message handlers
    reliable_handler = ExampleMessageHandler("reliable", failure_rate=0.0)
    unreliable_handler = ExampleMessageHandler("unreliable", failure_rate=0.3)
    
    # Subscribe to topics
    await broker.subscribe("reliable.topic", reliable_handler)
    await broker.subscribe("unreliable.topic", unreliable_handler)
    
    # Publish messages
    messages = []
    for i in range(5):
        message = Message(
            topic="reliable.topic" if i % 2 == 0 else "unreliable.topic",
            payload=f"Test message {i}",
            correlation_id=f"demo-{i}"
        )
        messages.append(message)
        
        msg_id = await broker.publish(message.topic, message)
        logger.info(f"Published message {msg_id} to {message.topic}")
    
    # Simulate message delivery
    logger.info("Simulating message delivery...")
    
    for message in messages:
        await broker.simulate_message_delivery(message.topic, message)
        await asyncio.sleep(0.1)  # Small delay between deliveries
    
    # Report handler statistics
    logger.info(f"Reliable handler: {reliable_handler.processed_count} processed, {reliable_handler.failed_count} failed")
    logger.info(f"Unreliable handler: {unreliable_handler.processed_count} processed, {unreliable_handler.failed_count} failed")
    
    # Disconnect
    await broker.disconnect()


async def main():
    """Main example function."""
    
    print("🚀 FastAPI Microservices SDK - Message Broker Base Interface Example")
    print("=" * 70)
    
    try:
        with CorrelationContext("message-broker-demo", "message-broker-example"):
            
            # Demonstrate different aspects
            await demonstrate_message_operations()
            print()
            
            await demonstrate_reliability_manager()
            print()
            
            await demonstrate_dead_letter_queue()
            print()
            
            await demonstrate_message_deduplication()
            print()
            
            await demonstrate_circuit_breaker()
            print()
            
            await demonstrate_message_metrics()
            print()
            
            await demonstrate_mock_broker_integration()
            print()
        
        print("✅ All message broker demonstrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
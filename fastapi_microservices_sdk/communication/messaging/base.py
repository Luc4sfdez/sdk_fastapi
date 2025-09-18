"""
Base Message Broker Interface for FastAPI Microservices SDK.

This module provides the abstract base class and common interfaces for all
message broker implementations, along with reliability patterns and utilities.
"""

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from ..config import MessageBrokerConfig, RetryPolicyConfig
from ..exceptions import (
    MessageBrokerError,
    MessagePublishError,
    MessageConsumptionError,
    MessageSerializationError,
    DeadLetterQueueError
)
from ..logging import CommunicationLogger, CommunicationEventType


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class DeliveryMode(str, Enum):
    """Message delivery modes."""
    AT_MOST_ONCE = "at_most_once"      # Fire and forget
    AT_LEAST_ONCE = "at_least_once"    # Guaranteed delivery, possible duplicates
    EXACTLY_ONCE = "exactly_once"      # Guaranteed delivery, no duplicates


@dataclass
class Message:
    """Base message class for all message brokers."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    payload: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    content_type: str = "application/json"
    delivery_mode: DeliveryMode = DeliveryMode.AT_LEAST_ONCE
    ttl: Optional[int] = None  # Time to live in seconds
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'topic': self.topic,
            'payload': self.payload,
            'headers': self.headers,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'content_type': self.content_type,
            'delivery_mode': self.delivery_mode.value,
            'ttl': self.ttl,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        message = cls()
        message.id = data.get('id', message.id)
        message.topic = data.get('topic', '')
        message.payload = data.get('payload')
        message.headers = data.get('headers', {})
        
        if 'timestamp' in data:
            message.timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        message.correlation_id = data.get('correlation_id')
        message.reply_to = data.get('reply_to')
        message.content_type = data.get('content_type', 'application/json')
        message.delivery_mode = DeliveryMode(data.get('delivery_mode', DeliveryMode.AT_LEAST_ONCE.value))
        message.ttl = data.get('ttl')
        message.priority = data.get('priority', 0)
        message.retry_count = data.get('retry_count', 0)
        message.max_retries = data.get('max_retries', 3)
        
        return message
    
    def serialize(self) -> bytes:
        """Serialize message to bytes."""
        try:
            if self.content_type == 'application/json':
                return json.dumps(self.to_dict(), default=str).encode('utf-8')
            elif self.content_type == 'text/plain':
                return str(self.payload).encode('utf-8')
            else:
                # For binary data, assume payload is already bytes
                return self.payload if isinstance(self.payload, bytes) else str(self.payload).encode('utf-8')
        except Exception as e:
            raise MessageSerializationError(f"Failed to serialize message: {e}")
    
    @classmethod
    def deserialize(cls, data: bytes, content_type: str = 'application/json') -> 'Message':
        """Deserialize message from bytes."""
        try:
            if content_type == 'application/json':
                message_dict = json.loads(data.decode('utf-8'))
                return cls.from_dict(message_dict)
            elif content_type == 'text/plain':
                message = cls()
                message.payload = data.decode('utf-8')
                message.content_type = content_type
                return message
            else:
                message = cls()
                message.payload = data
                message.content_type = content_type
                return message
        except Exception as e:
            raise MessageSerializationError(f"Failed to deserialize message: {e}")


@dataclass
class MessageAcknowledgment:
    """Message acknowledgment information."""
    
    message_id: str
    status: MessageStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None
    retry_count: int = 0
    processing_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert acknowledgment to dictionary."""
        return {
            'message_id': self.message_id,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'error': self.error,
            'retry_count': self.retry_count,
            'processing_time_ms': self.processing_time_ms
        }


class MessageHandler(ABC):
    """Abstract base class for message handlers."""
    
    @abstractmethod
    async def handle_message(self, message: Message) -> MessageAcknowledgment:
        """
        Handle a received message.
        
        Args:
            message: The message to handle
            
        Returns:
            MessageAcknowledgment with processing result
        """
        pass
    
    async def handle_error(self, message: Message, error: Exception) -> MessageAcknowledgment:
        """
        Handle message processing error.
        
        Args:
            message: The message that failed
            error: The error that occurred
            
        Returns:
            MessageAcknowledgment with error information
        """
        return MessageAcknowledgment(
            message_id=message.id,
            status=MessageStatus.FAILED,
            error=str(error),
            retry_count=message.retry_count
        )


class ReliabilityManager:
    """
    Manager for reliability patterns including retry logic, exponential backoff,
    dead letter queues, and message acknowledgments.
    """
    
    def __init__(self, config: RetryPolicyConfig):
        """
        Initialize reliability manager.
        
        Args:
            config: Retry policy configuration
        """
        self.config = config
        self.logger = CommunicationLogger("reliability_manager")
    
    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute operation with retry logic and exponential backoff.
        
        Args:
            operation: The async operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                self.logger.debug(
                    f"Executing operation (attempt {attempt + 1}/{self.config.max_attempts})",
                    metadata={'operation': operation.__name__ if hasattr(operation, '__name__') else str(operation)}
                )
                
                result = await operation(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(
                        f"Operation succeeded after {attempt + 1} attempts",
                        metadata={'operation': operation.__name__ if hasattr(operation, '__name__') else str(operation)}
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                self.logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self.config.max_attempts}): {e}",
                    metadata={
                        'operation': operation.__name__ if hasattr(operation, '__name__') else str(operation),
                        'error': str(e)
                    }
                )
                
                # Don't wait after the last attempt
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        # All attempts failed
        self.logger.error(
            f"Operation failed after {self.config.max_attempts} attempts",
            metadata={
                'operation': operation.__name__ if hasattr(operation, '__name__') else str(operation),
                'final_error': str(last_exception)
            }
        )
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for exponential backoff with jitter.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            import random
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    def should_retry(self, message: Message, error: Exception) -> bool:
        """
        Determine if a message should be retried.
        
        Args:
            message: The message that failed
            error: The error that occurred
            
        Returns:
            True if message should be retried
        """
        # Don't retry if max retries exceeded
        if message.retry_count >= message.max_retries:
            return False
        
        # Don't retry certain types of errors (e.g., serialization errors)
        if isinstance(error, MessageSerializationError):
            return False
        
        return True
    
    async def handle_failed_message(
        self,
        message: Message,
        error: Exception,
        dead_letter_handler: Optional[Callable] = None
    ) -> MessageAcknowledgment:
        """
        Handle a failed message with retry logic or dead letter queue.
        
        Args:
            message: The failed message
            error: The error that occurred
            dead_letter_handler: Optional handler for dead letter messages
            
        Returns:
            MessageAcknowledgment with final status
        """
        if self.should_retry(message, error):
            message.retry_count += 1
            
            self.logger.info(
                f"Message will be retried (attempt {message.retry_count}/{message.max_retries})",
                event_type=CommunicationEventType.MESSAGE_CONSUME,
                metadata={
                    'message_id': message.id,
                    'retry_count': message.retry_count,
                    'error': str(error)
                }
            )
            
            return MessageAcknowledgment(
                message_id=message.id,
                status=MessageStatus.PENDING,
                retry_count=message.retry_count,
                error=str(error)
            )
        else:
            # Send to dead letter queue
            if dead_letter_handler:
                try:
                    await dead_letter_handler(message, error)
                    
                    self.logger.warning(
                        f"Message sent to dead letter queue",
                        event_type=CommunicationEventType.MESSAGE_CONSUME,
                        metadata={
                            'message_id': message.id,
                            'retry_count': message.retry_count,
                            'final_error': str(error)
                        }
                    )
                    
                    return MessageAcknowledgment(
                        message_id=message.id,
                        status=MessageStatus.DEAD_LETTER,
                        retry_count=message.retry_count,
                        error=str(error)
                    )
                except Exception as dlq_error:
                    self.logger.error(
                        f"Failed to send message to dead letter queue: {dlq_error}",
                        metadata={
                            'message_id': message.id,
                            'original_error': str(error),
                            'dlq_error': str(dlq_error)
                        }
                    )
            
            # Final failure
            self.logger.error(
                f"Message processing failed permanently",
                event_type=CommunicationEventType.ERROR,
                metadata={
                    'message_id': message.id,
                    'retry_count': message.retry_count,
                    'final_error': str(error)
                }
            )
            
            return MessageAcknowledgment(
                message_id=message.id,
                status=MessageStatus.FAILED,
                retry_count=message.retry_count,
                error=str(error)
            )


class MessageBroker(ABC):
    """
    Abstract base class for message brokers.
    
    This class defines the common interface that all message broker
    implementations must follow.
    """
    
    def __init__(self, config: MessageBrokerConfig):
        """
        Initialize message broker.
        
        Args:
            config: Message broker configuration
        """
        self.config = config
        self.logger = CommunicationLogger(f"message_broker_{config.type.value}")
        self.reliability_manager = ReliabilityManager(config.retry_policy)
        self._connected = False
        self._subscribers: Dict[str, List[MessageHandler]] = {}
        self._dead_letter_handlers: Dict[str, Callable] = {}
    
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the message broker.
        
        Raises:
            MessageBrokerConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the message broker.
        """
        pass
    
    @abstractmethod
    async def publish(
        self,
        topic: str,
        message: Union[Message, Dict[str, Any], str, bytes],
        **kwargs
    ) -> str:
        """
        Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            message: Message to publish
            **kwargs: Additional broker-specific options
            
        Returns:
            Message ID
            
        Raises:
            MessagePublishError: If publishing fails
        """
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler,
        **kwargs
    ) -> None:
        """
        Subscribe to a topic with a message handler.
        
        Args:
            topic: Topic to subscribe to
            handler: Message handler
            **kwargs: Additional broker-specific options
            
        Raises:
            MessageConsumptionError: If subscription fails
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, topic: str) -> None:
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check broker health status.
        
        Returns:
            True if broker is healthy
        """
        pass
    
    # Common utility methods
    def _ensure_message(self, data: Union[Message, Dict[str, Any], str, bytes]) -> Message:
        """
        Ensure data is converted to Message object.
        
        Args:
            data: Data to convert
            
        Returns:
            Message object
        """
        if isinstance(data, Message):
            return data
        elif isinstance(data, dict):
            return Message.from_dict(data)
        elif isinstance(data, str):
            message = Message()
            message.payload = data
            message.content_type = 'text/plain'
            return message
        elif isinstance(data, bytes):
            return Message.deserialize(data)
        else:
            message = Message()
            message.payload = data
            return message
    
    async def _process_message(
        self,
        message: Message,
        handler: MessageHandler
    ) -> MessageAcknowledgment:
        """
        Process a message with error handling and reliability patterns.
        
        Args:
            message: Message to process
            handler: Message handler
            
        Returns:
            MessageAcknowledgment with processing result
        """
        start_time = time.time()
        
        try:
            self.logger.debug(
                f"Processing message {message.id}",
                event_type=CommunicationEventType.MESSAGE_CONSUME,
                metadata={
                    'message_id': message.id,
                    'topic': message.topic,
                    'retry_count': message.retry_count
                }
            )
            
            # Process message
            ack = await handler.handle_message(message)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            ack.processing_time_ms = processing_time
            
            self.logger.info(
                f"Message processed successfully",
                event_type=CommunicationEventType.MESSAGE_CONSUME,
                metadata={
                    'message_id': message.id,
                    'status': ack.status.value,
                    'processing_time_ms': processing_time
                }
            )
            
            return ack
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            self.logger.error(
                f"Message processing failed: {e}",
                event_type=CommunicationEventType.ERROR,
                metadata={
                    'message_id': message.id,
                    'error': str(e),
                    'processing_time_ms': processing_time
                }
            )
            
            # Handle error with reliability patterns
            dead_letter_handler = self._dead_letter_handlers.get(message.topic)
            ack = await self.reliability_manager.handle_failed_message(
                message, e, dead_letter_handler
            )
            ack.processing_time_ms = processing_time
            
            return ack
    
    def add_dead_letter_handler(self, topic: str, handler: Callable) -> None:
        """
        Add dead letter queue handler for a topic.
        
        Args:
            topic: Topic name
            handler: Dead letter handler function
        """
        self._dead_letter_handlers[topic] = handler
    
    def remove_dead_letter_handler(self, topic: str) -> None:
        """
        Remove dead letter queue handler for a topic.
        
        Args:
            topic: Topic name
        """
        self._dead_letter_handlers.pop(topic, None)
    
    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self._connected
    
    def __str__(self) -> str:
        """String representation of the broker."""
        return f"{self.__class__.__name__}({self.config.type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the broker."""
        return f"{self.__class__.__name__}(type={self.config.type.value}, url={self.config.connection_url})"
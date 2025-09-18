"""
Reliability Patterns for Message Brokers.

This module provides advanced reliability patterns including dead letter queues,
message deduplication, circuit breakers for messaging, and monitoring utilities.
"""

import asyncio
import hashlib
import time
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from enum import Enum

from .base import Message, MessageAcknowledgment, MessageStatus
from ..exceptions import DeadLetterQueueError, MessageBrokerError
from ..logging import CommunicationLogger, CommunicationEventType


class CircuitBreakerState(str, Enum):
    """Circuit breaker states for messaging."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class DeadLetterMessage:
    """Dead letter message with metadata."""
    
    original_message: Message
    error: str
    failed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    topic: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'original_message': self.original_message.to_dict(),
            'error': self.error,
            'failed_at': self.failed_at.isoformat(),
            'retry_count': self.retry_count,
            'topic': self.topic
        }


class DeadLetterQueue:
    """
    Dead Letter Queue implementation for failed messages.
    
    Provides storage, retrieval, and reprocessing capabilities for messages
    that failed processing after all retry attempts.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize dead letter queue.
        
        Args:
            max_size: Maximum number of messages to store
        """
        self.max_size = max_size
        self.messages: Dict[str, DeadLetterMessage] = {}
        self.topic_messages: Dict[str, List[str]] = defaultdict(list)
        self.logger = CommunicationLogger("dead_letter_queue")
        self._lock = asyncio.Lock()
    
    async def add_message(
        self,
        message: Message,
        error: str,
        topic: str = ""
    ) -> None:
        """
        Add a failed message to the dead letter queue.
        
        Args:
            message: The failed message
            error: Error description
            topic: Topic the message failed on
            
        Raises:
            DeadLetterQueueError: If queue operations fail
        """
        async with self._lock:
            try:
                # Check if queue is full
                if len(self.messages) >= self.max_size:
                    # Remove oldest message
                    oldest_id = next(iter(self.messages))
                    await self._remove_message_internal(oldest_id)
                
                # Create dead letter message
                dl_message = DeadLetterMessage(
                    original_message=message,
                    error=error,
                    retry_count=message.retry_count,
                    topic=topic or message.topic
                )
                
                # Store message
                self.messages[message.id] = dl_message
                self.topic_messages[dl_message.topic].append(message.id)
                
                self.logger.warning(
                    f"Message added to dead letter queue",
                    event_type=CommunicationEventType.MESSAGE_CONSUME,
                    metadata={
                        'message_id': message.id,
                        'topic': dl_message.topic,
                        'error': error,
                        'retry_count': message.retry_count,
                        'queue_size': len(self.messages)
                    }
                )
                
            except Exception as e:
                raise DeadLetterQueueError(f"Failed to add message to dead letter queue: {e}")
    
    async def get_message(self, message_id: str) -> Optional[DeadLetterMessage]:
        """
        Get a message from the dead letter queue.
        
        Args:
            message_id: Message ID to retrieve
            
        Returns:
            DeadLetterMessage if found, None otherwise
        """
        async with self._lock:
            return self.messages.get(message_id)
    
    async def get_messages_by_topic(self, topic: str) -> List[DeadLetterMessage]:
        """
        Get all messages for a specific topic.
        
        Args:
            topic: Topic name
            
        Returns:
            List of dead letter messages for the topic
        """
        async with self._lock:
            message_ids = self.topic_messages.get(topic, [])
            return [self.messages[msg_id] for msg_id in message_ids if msg_id in self.messages]
    
    async def remove_message(self, message_id: str) -> bool:
        """
        Remove a message from the dead letter queue.
        
        Args:
            message_id: Message ID to remove
            
        Returns:
            True if message was removed, False if not found
        """
        async with self._lock:
            return await self._remove_message_internal(message_id)
    
    async def _remove_message_internal(self, message_id: str) -> bool:
        """Internal method to remove message (assumes lock is held)."""
        if message_id not in self.messages:
            return False
        
        dl_message = self.messages.pop(message_id)
        
        # Remove from topic index
        if dl_message.topic in self.topic_messages:
            try:
                self.topic_messages[dl_message.topic].remove(message_id)
                if not self.topic_messages[dl_message.topic]:
                    del self.topic_messages[dl_message.topic]
            except ValueError:
                pass  # Message not in topic list
        
        return True
    
    async def reprocess_message(
        self,
        message_id: str,
        reprocess_handler: Callable[[Message], Any]
    ) -> bool:
        """
        Reprocess a message from the dead letter queue.
        
        Args:
            message_id: Message ID to reprocess
            reprocess_handler: Handler to reprocess the message
            
        Returns:
            True if reprocessing succeeded
        """
        async with self._lock:
            if message_id not in self.messages:
                return False
            
            dl_message = self.messages[message_id]
            
        try:
            # Reset retry count for reprocessing
            dl_message.original_message.retry_count = 0
            
            # Attempt reprocessing
            await reprocess_handler(dl_message.original_message)
            
            # Remove from dead letter queue on success
            await self.remove_message(message_id)
            
            self.logger.info(
                f"Message reprocessed successfully from dead letter queue",
                metadata={
                    'message_id': message_id,
                    'topic': dl_message.topic
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"Failed to reprocess message from dead letter queue: {e}",
                metadata={
                    'message_id': message_id,
                    'error': str(e)
                }
            )
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get dead letter queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        async with self._lock:
            topic_counts = {
                topic: len(message_ids) 
                for topic, message_ids in self.topic_messages.items()
            }
            
            return {
                'total_messages': len(self.messages),
                'max_size': self.max_size,
                'utilization': len(self.messages) / self.max_size,
                'topics': list(self.topic_messages.keys()),
                'topic_counts': topic_counts
            }
    
    async def cleanup_old_messages(self, max_age_hours: int = 24) -> int:
        """
        Clean up old messages from the dead letter queue.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of messages cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        async with self._lock:
            messages_to_remove = []
            
            for message_id, dl_message in self.messages.items():
                if dl_message.failed_at < cutoff_time:
                    messages_to_remove.append(message_id)
            
            for message_id in messages_to_remove:
                await self._remove_message_internal(message_id)
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(
                f"Cleaned up {cleaned_count} old messages from dead letter queue",
                metadata={
                    'cleaned_count': cleaned_count,
                    'max_age_hours': max_age_hours
                }
            )
        
        return cleaned_count


class MessageDeduplicator:
    """
    Message deduplication utility to prevent processing duplicate messages.
    
    Uses message IDs and content hashes to detect duplicates within a time window.
    """
    
    def __init__(self, window_minutes: int = 60, max_entries: int = 100000):
        """
        Initialize message deduplicator.
        
        Args:
            window_minutes: Deduplication window in minutes
            max_entries: Maximum number of entries to track
        """
        self.window_minutes = window_minutes
        self.max_entries = max_entries
        self.message_hashes: Dict[str, datetime] = {}
        self.logger = CommunicationLogger("message_deduplicator")
        self._lock = asyncio.Lock()
    
    def _calculate_message_hash(self, message: Message) -> str:
        """
        Calculate hash for message deduplication.
        
        Args:
            message: Message to hash
            
        Returns:
            Message hash string
        """
        # Use message ID if available
        if message.id:
            return f"id:{message.id}"
        
        # Otherwise, hash the content
        content = f"{message.topic}:{message.payload}:{message.correlation_id}"
        return f"hash:{hashlib.sha256(content.encode()).hexdigest()}"
    
    async def is_duplicate(self, message: Message) -> bool:
        """
        Check if message is a duplicate.
        
        Args:
            message: Message to check
            
        Returns:
            True if message is a duplicate
        """
        async with self._lock:
            message_hash = self._calculate_message_hash(message)
            current_time = datetime.now(timezone.utc)
            
            # Clean up old entries
            await self._cleanup_old_entries(current_time)
            
            # Check if message hash exists
            if message_hash in self.message_hashes:
                self.logger.debug(
                    f"Duplicate message detected",
                    metadata={
                        'message_id': message.id,
                        'message_hash': message_hash,
                        'topic': message.topic
                    }
                )
                return True
            
            # Add message hash
            self.message_hashes[message_hash] = current_time
            
            # Limit memory usage
            if len(self.message_hashes) > self.max_entries:
                # Remove oldest entries
                sorted_entries = sorted(
                    self.message_hashes.items(),
                    key=lambda x: x[1]
                )
                entries_to_remove = len(self.message_hashes) - self.max_entries + 1000
                for hash_key, _ in sorted_entries[:entries_to_remove]:
                    del self.message_hashes[hash_key]
            
            return False
    
    async def _cleanup_old_entries(self, current_time: datetime) -> None:
        """Clean up entries outside the deduplication window."""
        cutoff_time = current_time - timedelta(minutes=self.window_minutes)
        
        entries_to_remove = [
            hash_key for hash_key, timestamp in self.message_hashes.items()
            if timestamp < cutoff_time
        ]
        
        for hash_key in entries_to_remove:
            del self.message_hashes[hash_key]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get deduplicator statistics."""
        async with self._lock:
            return {
                'tracked_messages': len(self.message_hashes),
                'max_entries': self.max_entries,
                'window_minutes': self.window_minutes
            }


class MessagingCircuitBreaker:
    """
    Circuit breaker pattern for messaging operations.
    
    Prevents cascading failures by temporarily stopping message processing
    when error rates exceed thresholds.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3
    ):
        """
        Initialize messaging circuit breaker.
        
        Args:
            failure_threshold: Number of failures to open circuit
            recovery_timeout: Timeout before attempting recovery (seconds)
            success_threshold: Number of successes to close circuit
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        
        self.logger = CommunicationLogger("messaging_circuit_breaker")
        self._lock = asyncio.Lock()
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """
        Execute operation with circuit breaker protection.
        
        Args:
            operation: Operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
            
        Raises:
            MessageBrokerError: If circuit is open
        """
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.logger.info(
                        "Circuit breaker transitioning to half-open",
                        event_type=CommunicationEventType.CIRCUIT_BREAKER,
                        metadata={'state': self.state.value}
                    )
                else:
                    raise MessageBrokerError("Circuit breaker is open")
        
        try:
            result = await operation(*args, **kwargs)
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self.failure_count = 0
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                
                if self.success_count >= self.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.success_count = 0
                    
                    self.logger.info(
                        "Circuit breaker closed after successful recovery",
                        event_type=CommunicationEventType.CIRCUIT_BREAKER,
                        metadata={'state': self.state.value}
                    )
    
    async def _on_failure(self) -> None:
        """Handle failed operation."""
        async with self._lock:
            self.failure_count += 1
            self.success_count = 0
            self.last_failure_time = datetime.now(timezone.utc)
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                
                self.logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures",
                    event_type=CommunicationEventType.CIRCUIT_BREAKER,
                    metadata={
                        'state': self.state.value,
                        'failure_count': self.failure_count
                    }
                )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        async with self._lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
                'success_threshold': self.success_threshold
            }


class MessageMetrics:
    """
    Metrics collection for message broker operations.
    
    Tracks throughput, latency, error rates, and other operational metrics.
    """
    
    def __init__(self, window_minutes: int = 5):
        """
        Initialize message metrics.
        
        Args:
            window_minutes: Metrics collection window in minutes
        """
        self.window_minutes = window_minutes
        self.logger = CommunicationLogger("message_metrics")
        
        # Metrics storage
        self.publish_times: deque = deque()
        self.consume_times: deque = deque()
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.topic_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'published': 0,
            'consumed': 0,
            'errors': 0,
            'total_latency_ms': 0.0
        })
        
        self._lock = asyncio.Lock()
    
    async def record_publish(self, topic: str, latency_ms: float) -> None:
        """
        Record message publish metrics.
        
        Args:
            topic: Topic name
            latency_ms: Publish latency in milliseconds
        """
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            
            self.publish_times.append((current_time, latency_ms))
            self.topic_metrics[topic]['published'] += 1
            self.topic_metrics[topic]['total_latency_ms'] += latency_ms
            
            await self._cleanup_old_metrics(current_time)
    
    async def record_consume(self, topic: str, latency_ms: float) -> None:
        """
        Record message consume metrics.
        
        Args:
            topic: Topic name
            latency_ms: Processing latency in milliseconds
        """
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            
            self.consume_times.append((current_time, latency_ms))
            self.topic_metrics[topic]['consumed'] += 1
            self.topic_metrics[topic]['total_latency_ms'] += latency_ms
            
            await self._cleanup_old_metrics(current_time)
    
    async def record_error(self, topic: str, error_type: str) -> None:
        """
        Record error metrics.
        
        Args:
            topic: Topic name
            error_type: Type of error
        """
        async with self._lock:
            self.error_counts[error_type] += 1
            self.topic_metrics[topic]['errors'] += 1
    
    async def _cleanup_old_metrics(self, current_time: datetime) -> None:
        """Clean up metrics outside the collection window."""
        cutoff_time = current_time - timedelta(minutes=self.window_minutes)
        
        # Clean publish times
        while self.publish_times and self.publish_times[0][0] < cutoff_time:
            self.publish_times.popleft()
        
        # Clean consume times
        while self.consume_times and self.consume_times[0][0] < cutoff_time:
            self.consume_times.popleft()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics summary.
        
        Returns:
            Dictionary with metrics data
        """
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            await self._cleanup_old_metrics(current_time)
            
            # Calculate throughput (messages per minute)
            publish_throughput = len(self.publish_times) / self.window_minutes
            consume_throughput = len(self.consume_times) / self.window_minutes
            
            # Calculate average latency
            avg_publish_latency = (
                sum(latency for _, latency in self.publish_times) / len(self.publish_times)
                if self.publish_times else 0.0
            )
            
            avg_consume_latency = (
                sum(latency for _, latency in self.consume_times) / len(self.consume_times)
                if self.consume_times else 0.0
            )
            
            # Topic-specific metrics
            topic_stats = {}
            for topic, metrics in self.topic_metrics.items():
                avg_topic_latency = (
                    metrics['total_latency_ms'] / (metrics['published'] + metrics['consumed'])
                    if (metrics['published'] + metrics['consumed']) > 0 else 0.0
                )
                
                topic_stats[topic] = {
                    'published': metrics['published'],
                    'consumed': metrics['consumed'],
                    'errors': metrics['errors'],
                    'avg_latency_ms': avg_topic_latency,
                    'error_rate': (
                        metrics['errors'] / (metrics['published'] + metrics['consumed'])
                        if (metrics['published'] + metrics['consumed']) > 0 else 0.0
                    )
                }
            
            return {
                'window_minutes': self.window_minutes,
                'publish_throughput_per_minute': publish_throughput,
                'consume_throughput_per_minute': consume_throughput,
                'avg_publish_latency_ms': avg_publish_latency,
                'avg_consume_latency_ms': avg_consume_latency,
                'total_errors': sum(self.error_counts.values()),
                'error_types': dict(self.error_counts),
                'topic_metrics': topic_stats,
                'timestamp': current_time.isoformat()
            }
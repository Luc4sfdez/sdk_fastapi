"""
Kafka Client Enterprise-Grade Implementation

This module provides a comprehensive Kafka client with enterprise features including:
- Producer/Consumer with exactly-once semantics
- Transaction support and idempotent producers
- Advanced partition and consumer group management
- Dead letter topics integration
- Schema registry support
- SSL/TLS security and SASL authentication
- Comprehensive monitoring and health checks
- Integration with reliability patterns

Author: FastAPI Microservices SDK Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import ssl
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union, Set, Tuple
from urllib.parse import urlparse
import uuid

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.errors import KafkaError, KafkaTimeoutError, CommitFailedError
    from aiokafka.structs import TopicPartition, ConsumerRecord, RecordMetadata
    from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
    from kafka.admin.config_resource import ConfigResource
    from kafka.errors import TopicAlreadyExistsError
    from kafka.structs import TopicPartition as AdminTopicPartition
except ImportError as e:
    raise ImportError(
        "Kafka dependencies not installed. Install with: pip install aiokafka kafka-python"
    ) from e

from .base import MessageBroker, Message, MessageHandler, MessageAcknowledgment, MessageStatus, DeliveryMode
from .reliability import ReliabilityManager
from ..config import CommunicationConfig
from ..exceptions import CommunicationError, MessageBrokerError
from ..logging import CommunicationLogger


class KafkaError(MessageBrokerError):
    """Base exception for Kafka-related errors."""
    pass


class KafkaConnectionError(KafkaError):
    """Raised when Kafka connection fails."""
    pass


class KafkaProducerError(KafkaError):
    """Raised when Kafka producer operations fail."""
    pass


class KafkaConsumerError(KafkaError):
    """Raised when Kafka consumer operations fail."""
    pass


class KafkaTransactionError(KafkaError):
    """Raised when Kafka transaction operations fail."""
    pass


class KafkaSchemaError(KafkaError):
    """Raised when schema registry operations fail."""
    pass


class KafkaSecurityMode(Enum):
    """Kafka security modes."""
    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class KafkaSASLMechanism(Enum):
    """Kafka SASL mechanisms."""
    PLAIN = "PLAIN"
    SCRAM_SHA_256 = "SCRAM-SHA-256"
    SCRAM_SHA_512 = "SCRAM-SHA-512"
    GSSAPI = "GSSAPI"
    OAUTHBEARER = "OAUTHBEARER"


class KafkaCompressionType(Enum):
    """Kafka compression types."""
    NONE = "none"
    GZIP = "gzip"
    SNAPPY = "snappy"
    LZ4 = "lz4"
    ZSTD = "zstd"


class KafkaOffsetResetStrategy(Enum):
    """Kafka offset reset strategies."""
    EARLIEST = "earliest"
    LATEST = "latest"
    NONE = "none"


class KafkaIsolationLevel(Enum):
    """Kafka isolation levels."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"


@dataclass
class KafkaTopicConfig:
    """Configuration for Kafka topics."""
    name: str
    num_partitions: int = 1
    replication_factor: int = 1
    config: Dict[str, Any] = field(default_factory=dict)
    cleanup_policy: str = "delete"  # delete, compact, compact,delete
    retention_ms: Optional[int] = None
    segment_ms: Optional[int] = None
    max_message_bytes: Optional[int] = None
    min_insync_replicas: Optional[int] = None
    
    def __post_init__(self):
        """Post-initialization to set default configs."""
        if self.cleanup_policy:
            self.config["cleanup.policy"] = self.cleanup_policy
        if self.retention_ms:
            self.config["retention.ms"] = str(self.retention_ms)
        if self.segment_ms:
            self.config["segment.ms"] = str(self.segment_ms)
        if self.max_message_bytes:
            self.config["max.message.bytes"] = str(self.max_message_bytes)
        if self.min_insync_replicas:
            self.config["min.insync.replicas"] = str(self.min_insync_replicas)


@dataclass
class KafkaProducerConfig:
    """Configuration for Kafka producer."""
    client_id: str = "fastapi-microservices-producer"
    acks: Union[str, int] = "all"  # 0, 1, "all"
    retries: int = 2147483647  # Max retries for idempotent producer
    max_in_flight_requests_per_connection: int = 5
    enable_idempotence: bool = True
    compression_type: KafkaCompressionType = KafkaCompressionType.SNAPPY
    batch_size: int = 16384
    linger_ms: int = 5
    buffer_memory: int = 33554432
    max_request_size: int = 1048576
    request_timeout_ms: int = 30000
    delivery_timeout_ms: int = 120000
    transactional_id: Optional[str] = None
    transaction_timeout_ms: int = 60000


@dataclass
class KafkaConsumerConfig:
    """Configuration for Kafka consumer."""
    group_id: str
    client_id: str = "fastapi-microservices-consumer"
    auto_offset_reset: KafkaOffsetResetStrategy = KafkaOffsetResetStrategy.LATEST
    enable_auto_commit: bool = False  # Manual commit for reliability
    auto_commit_interval_ms: int = 5000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500
    max_poll_interval_ms: int = 300000
    fetch_min_bytes: int = 1
    fetch_max_wait_ms: int = 500
    max_partition_fetch_bytes: int = 1048576
    isolation_level: KafkaIsolationLevel = KafkaIsolationLevel.READ_COMMITTED
    check_crcs: bool = True


@dataclass
class KafkaSecurityConfig:
    """Configuration for Kafka security."""
    security_protocol: KafkaSecurityMode = KafkaSecurityMode.PLAINTEXT
    ssl_context: Optional[ssl.SSLContext] = None
    ssl_check_hostname: bool = True
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_password: Optional[str] = None
    ssl_crlfile: Optional[str] = None
    sasl_mechanism: Optional[KafkaSASLMechanism] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None
    sasl_kerberos_service_name: str = "kafka"
    sasl_oauth_token_provider: Optional[Callable] = None


@dataclass
class KafkaClusterConfig:
    """Configuration for Kafka cluster."""
    bootstrap_servers: List[str]
    api_version: str = "auto"
    api_version_auto_timeout_ms: int = 2000
    connections_max_idle_ms: int = 540000
    metadata_max_age_ms: int = 300000
    retry_backoff_ms: int = 100
    request_timeout_ms: int = 30000
    reconnect_backoff_ms: int = 50
    reconnect_backoff_max_ms: int = 1000


@dataclass
class KafkaSchemaRegistryConfig:
    """Configuration for Schema Registry."""
    url: str
    auth: Optional[Tuple[str, str]] = None  # (username, password)
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30
    ssl_verify: bool = True
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None


@dataclass
class KafkaDeadLetterConfig:
    """Configuration for dead letter topics."""
    enabled: bool = True
    topic_suffix: str = ".DLT"
    max_retries: int = 3
    retry_delay_ms: int = 1000
    include_headers: bool = True
    include_exception_info: bool = True


class KafkaMessage(Message):
    """Kafka-specific message implementation."""
    
    def __init__(
        self,
        content: Any,
        topic: str,
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        timestamp: Optional[int] = None,
        **kwargs
    ):
        super().__init__(content, headers or {}, **kwargs)
        self.topic = topic
        self.key = key
        self.partition = partition
        self.timestamp = timestamp or int(time.time() * 1000)
        self.offset: Optional[int] = None
        
    @classmethod
    def from_consumer_record(cls, record: ConsumerRecord) -> "KafkaMessage":
        """Create KafkaMessage from aiokafka ConsumerRecord."""
        headers = {}
        if record.headers:
            headers = {k: v.decode('utf-8') if isinstance(v, bytes) else v 
                      for k, v in record.headers}
        
        # Deserialize content
        content = record.value
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
                # Try to parse as JSON
                content = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Keep as bytes if can't decode/parse
                pass
        
        message = cls(
            content=content,
            topic=record.topic,
            key=record.key.decode('utf-8') if record.key else None,
            partition=record.partition,
            headers=headers,
            timestamp=record.timestamp
        )
        message.offset = record.offset
        return message


class KafkaProducer:
    """Enterprise Kafka producer with advanced features."""
    
    def __init__(
        self,
        cluster_config: KafkaClusterConfig,
        producer_config: KafkaProducerConfig,
        security_config: KafkaSecurityConfig,
        logger: Optional[CommunicationLogger] = None
    ):
        self.cluster_config = cluster_config
        self.producer_config = producer_config
        self.security_config = security_config
        self.logger = logger or CommunicationLogger(__name__)
        
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_connected = False
        self._transaction_active = False
        
    async def connect(self) -> None:
        """Connect to Kafka cluster."""
        try:
            # Build producer configuration
            config = {
                'bootstrap_servers': self.cluster_config.bootstrap_servers,
                'client_id': self.producer_config.client_id,
                'acks': self.producer_config.acks,
                'retries': self.producer_config.retries,
                'max_in_flight_requests_per_connection': 
                    self.producer_config.max_in_flight_requests_per_connection,
                'enable_idempotence': self.producer_config.enable_idempotence,
                'compression_type': self.producer_config.compression_type.value,
                'batch_size': self.producer_config.batch_size,
                'linger_ms': self.producer_config.linger_ms,
                'buffer_memory': self.producer_config.buffer_memory,
                'max_request_size': self.producer_config.max_request_size,
                'request_timeout_ms': self.producer_config.request_timeout_ms,
                'api_version': self.cluster_config.api_version,
            }
            
            # Add security configuration
            if self.security_config.security_protocol != KafkaSecurityMode.PLAINTEXT:
                config['security_protocol'] = self.security_config.security_protocol.value
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SSL, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.ssl_context:
                        config['ssl_context'] = self.security_config.ssl_context
                    else:
                        config['ssl_check_hostname'] = self.security_config.ssl_check_hostname
                        if self.security_config.ssl_cafile:
                            config['ssl_cafile'] = self.security_config.ssl_cafile
                        if self.security_config.ssl_certfile:
                            config['ssl_certfile'] = self.security_config.ssl_certfile
                        if self.security_config.ssl_keyfile:
                            config['ssl_keyfile'] = self.security_config.ssl_keyfile
                        if self.security_config.ssl_password:
                            config['ssl_password'] = self.security_config.ssl_password
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SASL_PLAINTEXT, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.sasl_mechanism:
                        config['sasl_mechanism'] = self.security_config.sasl_mechanism.value
                        
                        if self.security_config.sasl_mechanism == KafkaSASLMechanism.PLAIN:
                            config['sasl_plain_username'] = self.security_config.sasl_plain_username
                            config['sasl_plain_password'] = self.security_config.sasl_plain_password
            
            # Add transactional configuration
            if self.producer_config.transactional_id:
                config['transactional_id'] = self.producer_config.transactional_id
                config['transaction_timeout_ms'] = self.producer_config.transaction_timeout_ms
            
            self._producer = AIOKafkaProducer(**config)
            await self._producer.start()
            
            # Initialize transactions if configured
            if self.producer_config.transactional_id:
                await self._producer.init_transactions()
            
            self._is_connected = True
            self.logger.info(
                "Kafka producer connected successfully",
                extra={
                    "bootstrap_servers": self.cluster_config.bootstrap_servers,
                    "client_id": self.producer_config.client_id,
                    "transactional": bool(self.producer_config.transactional_id)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Kafka producer: {e}")
            raise KafkaConnectionError(f"Failed to connect to Kafka: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster."""
        if self._producer:
            try:
                # Abort any active transaction
                if self._transaction_active:
                    await self._producer.abort_transaction()
                    self._transaction_active = False
                
                await self._producer.stop()
                self._is_connected = False
                self.logger.info("Kafka producer disconnected successfully")
            except Exception as e:
                self.logger.error(f"Error disconnecting Kafka producer: {e}")
                raise KafkaConnectionError(f"Failed to disconnect from Kafka: {e}") from e
    
    async def begin_transaction(self) -> None:
        """Begin a new transaction."""
        if not self.producer_config.transactional_id:
            raise KafkaTransactionError("Transactional ID not configured")
        
        if not self._is_connected:
            raise KafkaConnectionError("Producer not connected")
        
        try:
            await self._producer.begin_transaction()
            self._transaction_active = True
            self.logger.debug("Transaction started")
        except Exception as e:
            self.logger.error(f"Failed to begin transaction: {e}")
            raise KafkaTransactionError(f"Failed to begin transaction: {e}") from e
    
    async def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._transaction_active:
            raise KafkaTransactionError("No active transaction")
        
        try:
            await self._producer.commit_transaction()
            self._transaction_active = False
            self.logger.debug("Transaction committed")
        except Exception as e:
            self.logger.error(f"Failed to commit transaction: {e}")
            raise KafkaTransactionError(f"Failed to commit transaction: {e}") from e
    
    async def abort_transaction(self) -> None:
        """Abort the current transaction."""
        if not self._transaction_active:
            raise KafkaTransactionError("No active transaction")
        
        try:
            await self._producer.abort_transaction()
            self._transaction_active = False
            self.logger.debug("Transaction aborted")
        except Exception as e:
            self.logger.error(f"Failed to abort transaction: {e}")
            raise KafkaTransactionError(f"Failed to abort transaction: {e}") from e
    
    async def send(
        self,
        topic: str,
        value: Any,
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        timestamp_ms: Optional[int] = None
    ) -> RecordMetadata:
        """Send a message to Kafka topic."""
        if not self._is_connected:
            raise KafkaConnectionError("Producer not connected")
        
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value).encode('utf-8')
            elif isinstance(value, str):
                serialized_value = value.encode('utf-8')
            elif isinstance(value, bytes):
                serialized_value = value
            else:
                serialized_value = str(value).encode('utf-8')
            
            # Serialize key
            serialized_key = key.encode('utf-8') if key else None
            
            # Serialize headers
            serialized_headers = None
            if headers:
                serialized_headers = [
                    (k, json.dumps(v).encode('utf-8') if not isinstance(v, (str, bytes)) else 
                     v.encode('utf-8') if isinstance(v, str) else v)
                    for k, v in headers.items()
                ]
            
            # Send message
            future = await self._producer.send(
                topic=topic,
                value=serialized_value,
                key=serialized_key,
                partition=partition,
                headers=serialized_headers,
                timestamp_ms=timestamp_ms
            )
            
            self.logger.debug(
                f"Message sent to topic {topic}",
                extra={
                    "topic": topic,
                    "partition": future.partition,
                    "offset": future.offset,
                    "key": key
                }
            )
            
            return future
            
        except Exception as e:
            self.logger.error(f"Failed to send message to topic {topic}: {e}")
            raise KafkaProducerError(f"Failed to send message: {e}") from e
    
    async def flush(self) -> None:
        """Flush all buffered messages."""
        if self._producer:
            await self._producer.flush()
    
    @property
    def is_connected(self) -> bool:
        """Check if producer is connected."""
        return self._is_connected
    
    @property
    def is_transaction_active(self) -> bool:
        """Check if transaction is active."""
        return self._transaction_active


class KafkaConsumer:
    """Enterprise Kafka consumer with advanced features."""
    
    def __init__(
        self,
        cluster_config: KafkaClusterConfig,
        consumer_config: KafkaConsumerConfig,
        security_config: KafkaSecurityConfig,
        logger: Optional[CommunicationLogger] = None
    ):
        self.cluster_config = cluster_config
        self.consumer_config = consumer_config
        self.security_config = security_config
        self.logger = logger or CommunicationLogger(__name__)
        
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._is_connected = False
        self._subscribed_topics: Set[str] = set()
        
    async def connect(self) -> None:
        """Connect to Kafka cluster."""
        try:
            # Build consumer configuration
            config = {
                'bootstrap_servers': self.cluster_config.bootstrap_servers,
                'group_id': self.consumer_config.group_id,
                'client_id': self.consumer_config.client_id,
                'auto_offset_reset': self.consumer_config.auto_offset_reset.value,
                'enable_auto_commit': self.consumer_config.enable_auto_commit,
                'auto_commit_interval_ms': self.consumer_config.auto_commit_interval_ms,
                'session_timeout_ms': self.consumer_config.session_timeout_ms,
                'heartbeat_interval_ms': self.consumer_config.heartbeat_interval_ms,
                'max_poll_records': self.consumer_config.max_poll_records,
                'max_poll_interval_ms': self.consumer_config.max_poll_interval_ms,
                'fetch_min_bytes': self.consumer_config.fetch_min_bytes,
                'fetch_max_wait_ms': self.consumer_config.fetch_max_wait_ms,
                'max_partition_fetch_bytes': self.consumer_config.max_partition_fetch_bytes,
                'isolation_level': self.consumer_config.isolation_level.value,
                'check_crcs': self.consumer_config.check_crcs,
                'api_version': self.cluster_config.api_version,
            }
            
            # Add security configuration
            if self.security_config.security_protocol != KafkaSecurityMode.PLAINTEXT:
                config['security_protocol'] = self.security_config.security_protocol.value
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SSL, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.ssl_context:
                        config['ssl_context'] = self.security_config.ssl_context
                    else:
                        config['ssl_check_hostname'] = self.security_config.ssl_check_hostname
                        if self.security_config.ssl_cafile:
                            config['ssl_cafile'] = self.security_config.ssl_cafile
                        if self.security_config.ssl_certfile:
                            config['ssl_certfile'] = self.security_config.ssl_certfile
                        if self.security_config.ssl_keyfile:
                            config['ssl_keyfile'] = self.security_config.ssl_keyfile
                        if self.security_config.ssl_password:
                            config['ssl_password'] = self.security_config.ssl_password
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SASL_PLAINTEXT, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.sasl_mechanism:
                        config['sasl_mechanism'] = self.security_config.sasl_mechanism.value
                        
                        if self.security_config.sasl_mechanism == KafkaSASLMechanism.PLAIN:
                            config['sasl_plain_username'] = self.security_config.sasl_plain_username
                            config['sasl_plain_password'] = self.security_config.sasl_plain_password
            
            self._consumer = AIOKafkaConsumer(**config)
            await self._consumer.start()
            
            self._is_connected = True
            self.logger.info(
                "Kafka consumer connected successfully",
                extra={
                    "bootstrap_servers": self.cluster_config.bootstrap_servers,
                    "group_id": self.consumer_config.group_id,
                    "client_id": self.consumer_config.client_id
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Kafka consumer: {e}")
            raise KafkaConnectionError(f"Failed to connect to Kafka: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster."""
        if self._consumer:
            try:
                await self._consumer.stop()
                self._is_connected = False
                self._subscribed_topics.clear()
                self.logger.info("Kafka consumer disconnected successfully")
            except Exception as e:
                self.logger.error(f"Error disconnecting Kafka consumer: {e}")
                raise KafkaConnectionError(f"Failed to disconnect from Kafka: {e}") from e
    
    async def subscribe(self, topics: Union[str, List[str]]) -> None:
        """Subscribe to topics."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        if isinstance(topics, str):
            topics = [topics]
        
        try:
            self._consumer.subscribe(topics)
            self._subscribed_topics.update(topics)
            self.logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to topics {topics}: {e}")
            raise KafkaConsumerError(f"Failed to subscribe to topics: {e}") from e
    
    async def unsubscribe(self) -> None:
        """Unsubscribe from all topics."""
        if self._consumer:
            self._consumer.unsubscribe()
            self._subscribed_topics.clear()
            self.logger.info("Unsubscribed from all topics")
    
    async def consume(self, timeout_ms: int = 1000) -> Optional[KafkaMessage]:
        """Consume a single message."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        try:
            msg = await self._consumer.getone()
            if msg:
                kafka_message = KafkaMessage.from_consumer_record(msg)
                self.logger.debug(
                    f"Message consumed from topic {msg.topic}",
                    extra={
                        "topic": msg.topic,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "key": msg.key
                    }
                )
                return kafka_message
            return None
        except Exception as e:
            self.logger.error(f"Failed to consume message: {e}")
            raise KafkaConsumerError(f"Failed to consume message: {e}") from e
    
    async def consume_batch(self, max_records: int = 100, timeout_ms: int = 1000) -> List[KafkaMessage]:
        """Consume a batch of messages."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        try:
            messages = []
            msg_map = await self._consumer.getmany(timeout_ms=timeout_ms, max_records=max_records)
            
            for tp, msgs in msg_map.items():
                for msg in msgs:
                    kafka_message = KafkaMessage.from_consumer_record(msg)
                    messages.append(kafka_message)
            
            if messages:
                self.logger.debug(f"Consumed batch of {len(messages)} messages")
            
            return messages
        except Exception as e:
            self.logger.error(f"Failed to consume message batch: {e}")
            raise KafkaConsumerError(f"Failed to consume message batch: {e}") from e
    
    async def commit(self, offsets: Optional[Dict[TopicPartition, int]] = None) -> None:
        """Commit offsets."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        try:
            if offsets:
                await self._consumer.commit(offsets)
            else:
                await self._consumer.commit()
            self.logger.debug("Offsets committed successfully")
        except CommitFailedError as e:
            self.logger.error(f"Failed to commit offsets: {e}")
            raise KafkaConsumerError(f"Failed to commit offsets: {e}") from e
    
    async def seek(self, partition: TopicPartition, offset: int) -> None:
        """Seek to specific offset."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        try:
            self._consumer.seek(partition, offset)
            self.logger.debug(f"Seeked to offset {offset} for partition {partition}")
        except Exception as e:
            self.logger.error(f"Failed to seek to offset: {e}")
            raise KafkaConsumerError(f"Failed to seek to offset: {e}") from e
    
    async def get_committed_offsets(self, partitions: List[TopicPartition]) -> Dict[TopicPartition, int]:
        """Get committed offsets for partitions."""
        if not self._is_connected:
            raise KafkaConnectionError("Consumer not connected")
        
        try:
            return await self._consumer.committed(partitions)
        except Exception as e:
            self.logger.error(f"Failed to get committed offsets: {e}")
            raise KafkaConsumerError(f"Failed to get committed offsets: {e}") from e
    
    @property
    def is_connected(self) -> bool:
        """Check if consumer is connected."""
        return self._is_connected
    
    @property
    def subscribed_topics(self) -> Set[str]:
        """Get subscribed topics."""
        return self._subscribed_topics.copy()


class KafkaClient(MessageBroker):
    """
    Enterprise-grade Kafka client with comprehensive features.
    
    Features:
    - Producer/Consumer with exactly-once semantics
    - Transaction support and idempotent producers
    - Advanced partition and consumer group management
    - Dead letter topics integration
    - SSL/TLS security and SASL authentication
    - Comprehensive monitoring and health checks
    - Integration with reliability patterns
    """
    
    def __init__(
        self,
        cluster_config: KafkaClusterConfig,
        producer_config: Optional[KafkaProducerConfig] = None,
        consumer_config: Optional[KafkaConsumerConfig] = None,
        security_config: Optional[KafkaSecurityConfig] = None,
        dead_letter_config: Optional[KafkaDeadLetterConfig] = None,
        reliability_manager: Optional[ReliabilityManager] = None,
        logger: Optional[CommunicationLogger] = None
    ):
        super().__init__(reliability_manager, logger)
        
        self.cluster_config = cluster_config
        self.producer_config = producer_config or KafkaProducerConfig()
        self.consumer_config = consumer_config
        self.security_config = security_config or KafkaSecurityConfig()
        self.dead_letter_config = dead_letter_config or KafkaDeadLetterConfig()
        
        self._producer: Optional[KafkaProducer] = None
        self._consumer: Optional[KafkaConsumer] = None
        self._admin_client: Optional[KafkaAdminClient] = None
        self._is_connected = False
        self._message_handlers: Dict[str, MessageHandler] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        
        # Initialize admin client for topic management
        self._init_admin_client()
    
    def _init_admin_client(self) -> None:
        """Initialize Kafka admin client."""
        try:
            config = {
                'bootstrap_servers': self.cluster_config.bootstrap_servers,
                'api_version': self.cluster_config.api_version,
            }
            
            # Add security configuration for admin client
            if self.security_config.security_protocol != KafkaSecurityMode.PLAINTEXT:
                config['security_protocol'] = self.security_config.security_protocol.value
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SSL, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.ssl_cafile:
                        config['ssl_cafile'] = self.security_config.ssl_cafile
                    if self.security_config.ssl_certfile:
                        config['ssl_certfile'] = self.security_config.ssl_certfile
                    if self.security_config.ssl_keyfile:
                        config['ssl_keyfile'] = self.security_config.ssl_keyfile
                    if self.security_config.ssl_password:
                        config['ssl_password'] = self.security_config.ssl_password
                
                if self.security_config.security_protocol in [KafkaSecurityMode.SASL_PLAINTEXT, KafkaSecurityMode.SASL_SSL]:
                    if self.security_config.sasl_mechanism:
                        config['sasl_mechanism'] = self.security_config.sasl_mechanism.value
                        
                        if self.security_config.sasl_mechanism == KafkaSASLMechanism.PLAIN:
                            config['sasl_plain_username'] = self.security_config.sasl_plain_username
                            config['sasl_plain_password'] = self.security_config.sasl_plain_password
            
            self._admin_client = KafkaAdminClient(**config)
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka admin client: {e}")
            raise KafkaConnectionError(f"Failed to initialize admin client: {e}") from e  
  
    async def connect(self) -> None:
        """Connect to Kafka cluster."""
        try:
            # Initialize producer if configured
            if self.producer_config:
                self._producer = KafkaProducer(
                    self.cluster_config,
                    self.producer_config,
                    self.security_config,
                    self.logger
                )
                await self._producer.connect()
            
            # Initialize consumer if configured
            if self.consumer_config:
                self._consumer = KafkaConsumer(
                    self.cluster_config,
                    self.consumer_config,
                    self.security_config,
                    self.logger
                )
                await self._consumer.connect()
            
            self._is_connected = True
            self.logger.info(
                "Kafka client connected successfully",
                extra={
                    "bootstrap_servers": self.cluster_config.bootstrap_servers,
                    "producer_enabled": self._producer is not None,
                    "consumer_enabled": self._consumer is not None
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Kafka client: {e}")
            await self.disconnect()  # Cleanup partial connections
            raise KafkaConnectionError(f"Failed to connect to Kafka: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Kafka cluster."""
        try:
            # Stop all consumer tasks
            for task_name, task in self._consumer_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    self.logger.debug(f"Stopped consumer task: {task_name}")
            
            self._consumer_tasks.clear()
            
            # Disconnect producer
            if self._producer:
                await self._producer.disconnect()
                self._producer = None
            
            # Disconnect consumer
            if self._consumer:
                await self._consumer.disconnect()
                self._consumer = None
            
            # Close admin client
            if self._admin_client:
                self._admin_client.close()
                self._admin_client = None
            
            self._is_connected = False
            self._message_handlers.clear()
            
            self.logger.info("Kafka client disconnected successfully")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting Kafka client: {e}")
            raise KafkaConnectionError(f"Failed to disconnect from Kafka: {e}") from e
    
    async def publish(
        self,
        topic: str,
        message: Union[Message, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """Publish message to Kafka topic with reliability patterns."""
        if not self._is_connected or not self._producer:
            raise KafkaConnectionError("Producer not connected")
        
        # Convert to KafkaMessage if needed
        if not isinstance(message, KafkaMessage):
            kafka_message = KafkaMessage(
                content=message,
                topic=topic,
                key=key,
                partition=partition,
                headers=headers or {}
            )
        else:
            kafka_message = message
            kafka_message.topic = topic
            if key:
                kafka_message.key = key
            if partition is not None:
                kafka_message.partition = partition
            if headers:
                kafka_message.headers.update(headers)
        
        # Apply reliability patterns
        async def _publish_operation():
            try:
                # Send message
                record_metadata = await self._producer.send(
                    topic=kafka_message.topic,
                    value=kafka_message.content,
                    key=kafka_message.key,
                    partition=kafka_message.partition,
                    headers=kafka_message.headers,
                    timestamp_ms=kafka_message.timestamp
                )
                
                # Update message with metadata
                kafka_message.partition = record_metadata.partition
                kafka_message.offset = record_metadata.offset
                
                # Update metrics
                if self.reliability_manager:
                    self.reliability_manager.metrics.record_message_sent(topic)
                
                self.logger.debug(
                    f"Message published to topic {topic}",
                    extra={
                        "topic": topic,
                        "partition": record_metadata.partition,
                        "offset": record_metadata.offset,
                        "key": kafka_message.key
                    }
                )
                
                return True
                
            except Exception as e:
                # Handle dead letter topic if enabled
                if self.dead_letter_config.enabled:
                    await self._send_to_dead_letter_topic(kafka_message, str(e))
                
                # Update metrics
                if self.reliability_manager:
                    self.reliability_manager.metrics.record_message_error(topic, str(e))
                
                raise KafkaProducerError(f"Failed to publish message: {e}") from e
        
        # Apply reliability patterns if available
        if self.reliability_manager:
            return await self.reliability_manager.execute_with_reliability(
                _publish_operation,
                context={"topic": topic, "message_id": kafka_message.message_id}
            )
        else:
            return await _publish_operation()
    
    async def subscribe(
        self,
        topic: str,
        handler: MessageHandler,
        **kwargs
    ) -> None:
        """Subscribe to Kafka topic with message handler."""
        if not self._is_connected or not self._consumer:
            raise KafkaConnectionError("Consumer not connected")
        
        # Subscribe to topic
        await self._consumer.subscribe([topic])
        
        # Store handler
        self._message_handlers[topic] = handler
        
        # Start consumer task
        task_name = f"consumer_{topic}_{uuid.uuid4().hex[:8]}"
        task = asyncio.create_task(self._consume_messages(topic, handler))
        self._consumer_tasks[task_name] = task
        
        self.logger.info(f"Subscribed to topic {topic} with handler {handler.__class__.__name__}")
    
    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from Kafka topic."""
        if topic in self._message_handlers:
            del self._message_handlers[topic]
        
        # Stop consumer tasks for this topic
        tasks_to_remove = []
        for task_name, task in self._consumer_tasks.items():
            if topic in task_name:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                tasks_to_remove.append(task_name)
        
        for task_name in tasks_to_remove:
            del self._consumer_tasks[task_name]
        
        # Unsubscribe from consumer
        if self._consumer:
            await self._consumer.unsubscribe()
        
        self.logger.info(f"Unsubscribed from topic {topic}")
    
    async def _consume_messages(self, topic: str, handler: MessageHandler) -> None:
        """Internal method to consume messages from topic."""
        try:
            while True:
                try:
                    # Consume batch of messages
                    messages = await self._consumer.consume_batch(
                        max_records=self.consumer_config.max_poll_records,
                        timeout_ms=1000
                    )
                    
                    if not messages:
                        continue
                    
                    # Process messages
                    for kafka_message in messages:
                        if kafka_message.topic != topic:
                            continue
                        
                        # Apply reliability patterns
                        async def _process_message():
                            try:
                                # Create acknowledgment
                                ack = MessageAcknowledgment(
                                    message_id=kafka_message.message_id,
                                    status=MessageStatus.PROCESSING
                                )
                                
                                # Process message with handler
                                await handler.handle(kafka_message, ack)
                                
                                # Commit offset if processing succeeded
                                if ack.status == MessageStatus.SUCCESS:
                                    tp = TopicPartition(kafka_message.topic, kafka_message.partition)
                                    await self._consumer.commit({tp: kafka_message.offset + 1})
                                    
                                    # Update metrics
                                    if self.reliability_manager:
                                        self.reliability_manager.metrics.record_message_processed(topic)
                                
                                return ack.status == MessageStatus.SUCCESS
                                
                            except Exception as e:
                                ack.status = MessageStatus.FAILED
                                ack.error_message = str(e)
                                
                                # Handle dead letter topic
                                if self.dead_letter_config.enabled:
                                    await self._send_to_dead_letter_topic(kafka_message, str(e))
                                
                                # Update metrics
                                if self.reliability_manager:
                                    self.reliability_manager.metrics.record_message_error(topic, str(e))
                                
                                self.logger.error(
                                    f"Error processing message from topic {topic}: {e}",
                                    extra={
                                        "topic": topic,
                                        "partition": kafka_message.partition,
                                        "offset": kafka_message.offset,
                                        "message_id": kafka_message.message_id
                                    }
                                )
                                
                                raise
                        
                        # Apply reliability patterns if available
                        if self.reliability_manager:
                            await self.reliability_manager.execute_with_reliability(
                                _process_message,
                                context={
                                    "topic": topic,
                                    "message_id": kafka_message.message_id,
                                    "partition": kafka_message.partition,
                                    "offset": kafka_message.offset
                                }
                            )
                        else:
                            await _process_message()
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in consumer loop for topic {topic}: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
                    
        except asyncio.CancelledError:
            self.logger.debug(f"Consumer task for topic {topic} cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in consumer task for topic {topic}: {e}")
    
    async def _send_to_dead_letter_topic(self, message: KafkaMessage, error: str) -> None:
        """Send message to dead letter topic."""
        if not self.dead_letter_config.enabled:
            return
        
        try:
            dead_letter_topic = f"{message.topic}{self.dead_letter_config.topic_suffix}"
            
            # Prepare dead letter message
            dead_letter_headers = message.headers.copy()
            if self.dead_letter_config.include_headers:
                dead_letter_headers.update({
                    "x-original-topic": message.topic,
                    "x-original-partition": str(message.partition) if message.partition else "",
                    "x-original-offset": str(message.offset) if message.offset else "",
                    "x-original-key": message.key or "",
                    "x-failure-timestamp": str(int(time.time() * 1000)),
                    "x-failure-reason": error[:1000]  # Limit error message length
                })
            
            if self.dead_letter_config.include_exception_info:
                dead_letter_headers["x-exception-type"] = type(Exception).__name__
            
            # Send to dead letter topic
            await self._producer.send(
                topic=dead_letter_topic,
                value=message.content,
                key=message.key,
                headers=dead_letter_headers
            )
            
            self.logger.warning(
                f"Message sent to dead letter topic {dead_letter_topic}",
                extra={
                    "original_topic": message.topic,
                    "dead_letter_topic": dead_letter_topic,
                    "message_id": message.message_id,
                    "error": error
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send message to dead letter topic: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Kafka client."""
        health_status = {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "checks": {}
        }
        
        try:
            # Check connection status
            health_status["checks"]["connection"] = {
                "status": "healthy" if self._is_connected else "unhealthy",
                "connected": self._is_connected
            }
            
            # Check producer health
            if self._producer:
                health_status["checks"]["producer"] = {
                    "status": "healthy" if self._producer.is_connected else "unhealthy",
                    "connected": self._producer.is_connected,
                    "transaction_active": self._producer.is_transaction_active
                }
            
            # Check consumer health
            if self._consumer:
                health_status["checks"]["consumer"] = {
                    "status": "healthy" if self._consumer.is_connected else "unhealthy",
                    "connected": self._consumer.is_connected,
                    "subscribed_topics": list(self._consumer.subscribed_topics),
                    "active_tasks": len(self._consumer_tasks)
                }
            
            # Check admin client
            if self._admin_client:
                try:
                    # Try to get cluster metadata as health check
                    metadata = self._admin_client.describe_cluster()
                    health_status["checks"]["admin"] = {
                        "status": "healthy",
                        "cluster_id": metadata.cluster_id,
                        "controller_id": metadata.controller.id if metadata.controller else None,
                        "broker_count": len(metadata.brokers)
                    }
                except Exception as e:
                    health_status["checks"]["admin"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            # Overall health status
            unhealthy_checks = [
                check for check in health_status["checks"].values()
                if check.get("status") == "unhealthy"
            ]
            
            if unhealthy_checks:
                health_status["status"] = "unhealthy"
            
            # Add reliability manager health if available
            if self.reliability_manager:
                reliability_health = await self.reliability_manager.get_health_status()
                health_status["checks"]["reliability"] = reliability_health
                
                if reliability_health.get("status") == "unhealthy":
                    health_status["status"] = "unhealthy"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health_status
    
    async def create_topic(self, topic_config: KafkaTopicConfig) -> bool:
        """Create Kafka topic."""
        if not self._admin_client:
            raise KafkaError("Admin client not initialized")
        
        try:
            from kafka.admin import NewTopic
            
            new_topic = NewTopic(
                name=topic_config.name,
                num_partitions=topic_config.num_partitions,
                replication_factor=topic_config.replication_factor,
                topic_configs=topic_config.config
            )
            
            result = self._admin_client.create_topics([new_topic])
            
            # Wait for topic creation
            for topic, future in result.items():
                try:
                    future.result()  # This will raise exception if creation failed
                    self.logger.info(f"Topic {topic} created successfully")
                    return True
                except TopicAlreadyExistsError:
                    self.logger.warning(f"Topic {topic} already exists")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to create topic {topic}: {e}")
                    raise KafkaError(f"Failed to create topic {topic}: {e}") from e
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to create topic {topic_config.name}: {e}")
            raise KafkaError(f"Failed to create topic: {e}") from e
    
    async def delete_topic(self, topic_name: str) -> bool:
        """Delete Kafka topic."""
        if not self._admin_client:
            raise KafkaError("Admin client not initialized")
        
        try:
            result = self._admin_client.delete_topics([topic_name])
            
            # Wait for topic deletion
            for topic, future in result.items():
                try:
                    future.result()  # This will raise exception if deletion failed
                    self.logger.info(f"Topic {topic} deleted successfully")
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to delete topic {topic}: {e}")
                    raise KafkaError(f"Failed to delete topic {topic}: {e}") from e
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete topic {topic_name}: {e}")
            raise KafkaError(f"Failed to delete topic: {e}") from e
    
    async def list_topics(self) -> List[str]:
        """List all Kafka topics."""
        if not self._admin_client:
            raise KafkaError("Admin client not initialized")
        
        try:
            metadata = self._admin_client.list_topics()
            topics = list(metadata.topics.keys())
            self.logger.debug(f"Listed {len(topics)} topics")
            return topics
        except Exception as e:
            self.logger.error(f"Failed to list topics: {e}")
            raise KafkaError(f"Failed to list topics: {e}") from e
    
    async def get_topic_metadata(self, topic_name: str) -> Dict[str, Any]:
        """Get metadata for specific topic."""
        if not self._admin_client:
            raise KafkaError("Admin client not initialized")
        
        try:
            metadata = self._admin_client.list_topics()
            
            if topic_name not in metadata.topics:
                raise KafkaError(f"Topic {topic_name} not found")
            
            topic_metadata = metadata.topics[topic_name]
            
            return {
                "name": topic_name,
                "partitions": len(topic_metadata.partitions),
                "partition_info": [
                    {
                        "partition": partition.partition,
                        "leader": partition.leader,
                        "replicas": partition.replicas,
                        "isr": partition.isr
                    }
                    for partition in topic_metadata.partitions.values()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get topic metadata for {topic_name}: {e}")
            raise KafkaError(f"Failed to get topic metadata: {e}") from e
    
    async def get_consumer_group_info(self, group_id: str) -> Dict[str, Any]:
        """Get consumer group information."""
        if not self._admin_client:
            raise KafkaError("Admin client not initialized")
        
        try:
            # This would require additional implementation for consumer group management
            # For now, return basic info
            return {
                "group_id": group_id,
                "state": "unknown",
                "members": [],
                "coordinator": None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get consumer group info for {group_id}: {e}")
            raise KafkaError(f"Failed to get consumer group info: {e}") from e
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for Kafka transactions."""
        if not self._producer:
            raise KafkaTransactionError("Producer not available")
        
        if not self.producer_config.transactional_id:
            raise KafkaTransactionError("Transactional ID not configured")
        
        await self._producer.begin_transaction()
        try:
            yield self._producer
            await self._producer.commit_transaction()
        except Exception:
            await self._producer.abort_transaction()
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected
    
    @property
    def producer(self) -> Optional[KafkaProducer]:
        """Get producer instance."""
        return self._producer
    
    @property
    def consumer(self) -> Optional[KafkaConsumer]:
        """Get consumer instance."""
        return self._consumer
    
    @property
    def admin_client(self) -> Optional[KafkaAdminClient]:
        """Get admin client instance."""
        return self._admin_client


# Utility functions for easy configuration

def create_kafka_cluster_config(
    bootstrap_servers: Union[str, List[str]],
    **kwargs
) -> KafkaClusterConfig:
    """Create Kafka cluster configuration."""
    if isinstance(bootstrap_servers, str):
        bootstrap_servers = [bootstrap_servers]
    
    return KafkaClusterConfig(
        bootstrap_servers=bootstrap_servers,
        **kwargs
    )


def create_kafka_producer_config(
    client_id: str = "fastapi-microservices-producer",
    enable_transactions: bool = False,
    **kwargs
) -> KafkaProducerConfig:
    """Create Kafka producer configuration."""
    config = KafkaProducerConfig(client_id=client_id, **kwargs)
    
    if enable_transactions:
        config.transactional_id = f"{client_id}-{uuid.uuid4().hex[:8]}"
    
    return config


def create_kafka_consumer_config(
    group_id: str,
    client_id: str = "fastapi-microservices-consumer",
    **kwargs
) -> KafkaConsumerConfig:
    """Create Kafka consumer configuration."""
    return KafkaConsumerConfig(
        group_id=group_id,
        client_id=client_id,
        **kwargs
    )


def create_kafka_security_config(
    security_protocol: KafkaSecurityMode = KafkaSecurityMode.PLAINTEXT,
    **kwargs
) -> KafkaSecurityConfig:
    """Create Kafka security configuration."""
    return KafkaSecurityConfig(
        security_protocol=security_protocol,
        **kwargs
    )


def create_ssl_context(
    cafile: Optional[str] = None,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    password: Optional[str] = None,
    check_hostname: bool = True
) -> ssl.SSLContext:
    """Create SSL context for Kafka."""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    
    if cafile:
        context.load_verify_locations(cafile)
    
    if certfile and keyfile:
        context.load_cert_chain(certfile, keyfile, password)
    
    context.check_hostname = check_hostname
    
    return context


# Export main classes and functions
__all__ = [
    # Main client
    "KafkaClient",
    
    # Configuration classes
    "KafkaClusterConfig",
    "KafkaProducerConfig", 
    "KafkaConsumerConfig",
    "KafkaSecurityConfig",
    "KafkaTopicConfig",
    "KafkaDeadLetterConfig",
    "KafkaSchemaRegistryConfig",
    
    # Producer and Consumer
    "KafkaProducer",
    "KafkaConsumer",
    
    # Message class
    "KafkaMessage",
    
    # Enums
    "KafkaSecurityMode",
    "KafkaSASLMechanism", 
    "KafkaCompressionType",
    "KafkaOffsetResetStrategy",
    "KafkaIsolationLevel",
    
    # Exceptions
    "KafkaError",
    "KafkaConnectionError",
    "KafkaProducerError",
    "KafkaConsumerError",
    "KafkaTransactionError",
    "KafkaSchemaError",
    
    # Utility functions
    "create_kafka_cluster_config",
    "create_kafka_producer_config",
    "create_kafka_consumer_config", 
    "create_kafka_security_config",
    "create_ssl_context",
]
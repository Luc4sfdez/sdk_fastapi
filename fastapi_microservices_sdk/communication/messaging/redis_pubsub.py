"""
Redis Pub/Sub Client Enterprise-Grade Implementation

This module provides a comprehensive Redis client with enterprise features including:
- Pub/Sub patterns with channels and pattern matching
- Redis Streams support with consumer groups
- Redis Cluster and Sentinel integration
- Connection pooling and high availability
- SSL/TLS security and authentication
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
from typing import Any, Dict, List, Optional, Callable, Union, Set, Tuple, AsyncGenerator
from urllib.parse import urlparse
import uuid

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis, ConnectionPool, Sentinel
    from redis.asyncio.cluster import RedisCluster
    from redis.exceptions import (
        RedisError as BaseRedisError, ConnectionError as BaseRedisConnectionError,
        TimeoutError as RedisTimeoutError, ResponseError,
        ClusterError, SentinelManagedConnection
    )
    REDIS_AVAILABLE = True
except ImportError:
    # Create mock classes when Redis is not available
    REDIS_AVAILABLE = False
    Redis = None
    ConnectionPool = None
    Sentinel = None
    RedisCluster = None
    BaseRedisError = Exception
    BaseRedisConnectionError = Exception
    RedisTimeoutError = Exception
    ResponseError = Exception
    ClusterError = Exception
    SentinelManagedConnection = None

from .base import MessageBroker, Message, MessageHandler, MessageAcknowledgment, MessageStatus, DeliveryMode
try:
    from .reliability import ReliabilityManager
except ImportError:
    ReliabilityManager = None
from ..config import CommunicationConfig
from ..exceptions import CommunicationError, MessageBrokerError
from ..logging import CommunicationLogger


class RedisError(MessageBrokerError):
    """Base exception for Redis-related errors."""
    pass


class RedisConnectionError(RedisError):
    """Raised when Redis connection fails."""
    pass


class RedisPublishError(RedisError):
    """Raised when Redis publish operations fail."""
    pass


class RedisSubscribeError(RedisError):
    """Raised when Redis subscribe operations fail."""
    pass


class RedisStreamError(RedisError):
    """Raised when Redis stream operations fail."""
    pass


class RedisClusterError(RedisError):
    """Raised when Redis cluster operations fail."""
    pass


class RedisConnectionType(Enum):
    """Redis connection types."""
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


class RedisSSLMode(Enum):
    """Redis SSL modes."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    REQUIRED = "required"


class RedisStreamReadMode(Enum):
    """Redis stream read modes."""
    LATEST = "$"
    EARLIEST = "0"
    NEW_MESSAGES = ">"


@dataclass
class RedisConnectionConfig:
    """Configuration for Redis connection."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    connection_type: RedisConnectionType = RedisConnectionType.STANDALONE
    
    # Connection pool settings
    max_connections: int = 50
    retry_on_timeout: bool = True
    retry_on_error: List[Exception] = field(default_factory=lambda: [ConnectionError, TimeoutError])
    health_check_interval: int = 30
    
    # Timeout settings
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=dict)
    
    # SSL settings
    ssl_enabled: bool = False
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_cert_reqs: str = "required"
    ssl_ca_certs: Optional[str] = None
    ssl_check_hostname: bool = True


@dataclass
class RedisClusterConfig:
    """Configuration for Redis Cluster."""
    startup_nodes: List[Dict[str, Any]] = field(default_factory=list)
    max_connections_per_node: int = 50
    skip_full_coverage_check: bool = False
    readonly_mode: bool = False
    decode_responses: bool = True
    health_check_interval: int = 30


@dataclass
class RedisSentinelConfig:
    """Configuration for Redis Sentinel."""
    sentinels: List[Tuple[str, int]] = field(default_factory=list)
    service_name: str = "mymaster"
    sentinel_kwargs: Dict[str, Any] = field(default_factory=dict)
    connection_kwargs: Dict[str, Any] = field(default_factory=dict)
    check_connection: bool = False


@dataclass
class RedisPubSubConfig:
    """Configuration for Redis Pub/Sub."""
    ignore_subscribe_messages: bool = True
    decode_responses: bool = True
    max_connections: int = 10
    connection_pool_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RedisStreamConfig:
    """Configuration for Redis Streams."""
    consumer_group: str
    consumer_name: str
    stream_maxlen: Optional[int] = None
    stream_approximate: bool = True
    block_time: int = 1000  # milliseconds
    count: int = 10
    auto_claim_min_idle_time: int = 60000  # milliseconds
    auto_claim_count: int = 10


@dataclass
class RedisMessage(Message):
    """Redis-specific message implementation."""
    
    def __init__(
        self,
        content: Any,
        channel: Optional[str] = None,
        pattern: Optional[str] = None,
        stream_id: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        super().__init__(payload=content, headers=headers or {}, **kwargs)
        self.channel = channel
        self.pattern = pattern
        self.stream_id = stream_id
        self.redis_type: Optional[str] = None  # 'pubsub', 'stream', etc.
        
    @classmethod
    def from_pubsub_message(cls, message: Dict[str, Any]) -> "RedisMessage":
        """Create RedisMessage from Redis pub/sub message."""
        content = message.get('data')
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
                # Try to parse as JSON
                content = json.loads(content)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Keep as string if can't decode/parse
                pass
        
        redis_msg = cls(
            content=content,
            channel=message.get('channel'),
            pattern=message.get('pattern')
        )
        redis_msg.redis_type = 'pubsub'
        return redis_msg
    
    @classmethod
    def from_stream_message(cls, stream_name: str, message_id: str, fields: Dict[str, Any]) -> "RedisMessage":
        """Create RedisMessage from Redis stream message."""
        # Convert fields to content
        content = dict(fields)
        
        # Try to parse JSON content if it's a single field
        if len(fields) == 1 and 'data' in fields:
            try:
                content = json.loads(fields['data'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        redis_msg = cls(
            content=content,
            channel=stream_name,
            stream_id=message_id
        )
        redis_msg.redis_type = 'stream'
        return redis_msg


class RedisPubSubClient:
    """Enterprise Redis Pub/Sub client with advanced features."""
    
    def __init__(
        self,
        connection_config: RedisConnectionConfig,
        pubsub_config: RedisPubSubConfig,
        logger: Optional[CommunicationLogger] = None
    ):
        self.connection_config = connection_config
        self.pubsub_config = pubsub_config
        self.logger = logger or CommunicationLogger(__name__)
        
        self._redis: Optional[Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._is_connected = False
        self._subscribed_channels: Set[str] = set()
        self._subscribed_patterns: Set[str] = set()
        
    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            # Create connection pool
            pool_kwargs = {
                'host': self.connection_config.host,
                'port': self.connection_config.port,
                'db': self.connection_config.db,
                'max_connections': self.connection_config.max_connections,
                'retry_on_timeout': self.connection_config.retry_on_timeout,
                'health_check_interval': self.connection_config.health_check_interval,
                'socket_timeout': self.connection_config.socket_timeout,
                'socket_connect_timeout': self.connection_config.socket_connect_timeout,
                'socket_keepalive': self.connection_config.socket_keepalive,
                'socket_keepalive_options': self.connection_config.socket_keepalive_options,
                'decode_responses': self.pubsub_config.decode_responses,
            }
            
            # Add authentication
            if self.connection_config.username:
                pool_kwargs['username'] = self.connection_config.username
            if self.connection_config.password:
                pool_kwargs['password'] = self.connection_config.password
            
            # Add SSL configuration
            if self.connection_config.ssl_enabled:
                pool_kwargs['ssl'] = True
                if self.connection_config.ssl_keyfile:
                    pool_kwargs['ssl_keyfile'] = self.connection_config.ssl_keyfile
                if self.connection_config.ssl_certfile:
                    pool_kwargs['ssl_certfile'] = self.connection_config.ssl_certfile
                if self.connection_config.ssl_ca_certs:
                    pool_kwargs['ssl_ca_certs'] = self.connection_config.ssl_ca_certs
                pool_kwargs['ssl_cert_reqs'] = self.connection_config.ssl_cert_reqs
                pool_kwargs['ssl_check_hostname'] = self.connection_config.ssl_check_hostname
            
            # Create connection pool
            pool = ConnectionPool(**pool_kwargs)
            self._redis = Redis(connection_pool=pool)
            
            # Test connection
            await self._redis.ping()
            
            # Create pub/sub instance
            self._pubsub = self._redis.pubsub(
                ignore_subscribe_messages=self.pubsub_config.ignore_subscribe_messages
            )
            
            self._is_connected = True
            self.logger.info(
                "Redis Pub/Sub client connected successfully",
                extra={
                    "host": self.connection_config.host,
                    "port": self.connection_config.port,
                    "db": self.connection_config.db
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Redis Pub/Sub client: {e}")
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        try:
            if self._pubsub:
                await self._pubsub.close()
                self._pubsub = None
            
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            self._is_connected = False
            self._subscribed_channels.clear()
            self._subscribed_patterns.clear()
            
            self.logger.info("Redis Pub/Sub client disconnected successfully")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting Redis Pub/Sub client: {e}")
            raise RedisConnectionError(f"Failed to disconnect from Redis: {e}") from e
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publish message to Redis channel."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis client not connected")
        
        try:
            # Serialize message
            if isinstance(message, (dict, list)):
                serialized_message = json.dumps(message)
            elif isinstance(message, str):
                serialized_message = message
            else:
                serialized_message = str(message)
            
            # Publish message
            result = await self._redis.publish(channel, serialized_message)
            
            self.logger.debug(
                f"Message published to channel {channel}",
                extra={
                    "channel": channel,
                    "subscribers": result
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to publish message to channel {channel}: {e}")
            raise RedisPublishError(f"Failed to publish message: {e}") from e
    
    async def subscribe(self, *channels: str) -> None:
        """Subscribe to Redis channels."""
        if not self._is_connected or not self._pubsub:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        try:
            await self._pubsub.subscribe(*channels)
            self._subscribed_channels.update(channels)
            
            self.logger.info(f"Subscribed to channels: {channels}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to channels {channels}: {e}")
            raise RedisSubscribeError(f"Failed to subscribe to channels: {e}") from e
    
    async def psubscribe(self, *patterns: str) -> None:
        """Subscribe to Redis channel patterns."""
        if not self._is_connected or not self._pubsub:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        try:
            await self._pubsub.psubscribe(*patterns)
            self._subscribed_patterns.update(patterns)
            
            self.logger.info(f"Subscribed to patterns: {patterns}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to patterns {patterns}: {e}")
            raise RedisSubscribeError(f"Failed to subscribe to patterns: {e}") from e
    
    async def unsubscribe(self, *channels: str) -> None:
        """Unsubscribe from Redis channels."""
        if self._pubsub:
            await self._pubsub.unsubscribe(*channels)
            self._subscribed_channels.difference_update(channels)
            self.logger.info(f"Unsubscribed from channels: {channels}")
    
    async def punsubscribe(self, *patterns: str) -> None:
        """Unsubscribe from Redis channel patterns."""
        if self._pubsub:
            await self._pubsub.punsubscribe(*patterns)
            self._subscribed_patterns.difference_update(patterns)
            self.logger.info(f"Unsubscribed from patterns: {patterns}")
    
    async def get_message(self, timeout: float = 1.0) -> Optional[RedisMessage]:
        """Get a single message from subscribed channels."""
        if not self._is_connected or not self._pubsub:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        try:
            message = await self._pubsub.get_message(timeout=timeout)
            
            if message and message['type'] == 'message':
                redis_message = RedisMessage.from_pubsub_message(message)
                
                self.logger.debug(
                    f"Message received from channel {message['channel']}",
                    extra={
                        "channel": message['channel'],
                        "pattern": message.get('pattern')
                    }
                )
                
                return redis_message
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get message: {e}")
            raise RedisSubscribeError(f"Failed to get message: {e}") from e
    
    async def listen(self) -> AsyncGenerator[RedisMessage, None]:
        """Listen for messages from subscribed channels."""
        if not self._is_connected or not self._pubsub:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        try:
            async for message in self._pubsub.listen():
                if message['type'] == 'message':
                    redis_message = RedisMessage.from_pubsub_message(message)
                    yield redis_message
                    
        except Exception as e:
            self.logger.error(f"Error in message listener: {e}")
            raise RedisSubscribeError(f"Error in message listener: {e}") from e
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected
    
    @property
    def subscribed_channels(self) -> Set[str]:
        """Get subscribed channels."""
        return self._subscribed_channels.copy()
    
    @property
    def subscribed_patterns(self) -> Set[str]:
        """Get subscribed patterns."""
        return self._subscribed_patterns.copy()


class RedisStreamClient:
    """Enterprise Redis Streams client with consumer groups."""
    
    def __init__(
        self,
        connection_config: RedisConnectionConfig,
        stream_config: RedisStreamConfig,
        logger: Optional[CommunicationLogger] = None
    ):
        self.connection_config = connection_config
        self.stream_config = stream_config
        self.logger = logger or CommunicationLogger(__name__)
        
        self._redis: Optional[Redis] = None
        self._is_connected = False
        
    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            # Create connection (similar to PubSub client)
            pool_kwargs = {
                'host': self.connection_config.host,
                'port': self.connection_config.port,
                'db': self.connection_config.db,
                'max_connections': self.connection_config.max_connections,
                'retry_on_timeout': self.connection_config.retry_on_timeout,
                'health_check_interval': self.connection_config.health_check_interval,
                'socket_timeout': self.connection_config.socket_timeout,
                'socket_connect_timeout': self.connection_config.socket_connect_timeout,
                'socket_keepalive': self.connection_config.socket_keepalive,
                'decode_responses': True,  # Always decode for streams
            }
            
            # Add authentication
            if self.connection_config.username:
                pool_kwargs['username'] = self.connection_config.username
            if self.connection_config.password:
                pool_kwargs['password'] = self.connection_config.password
            
            # Add SSL configuration
            if self.connection_config.ssl_enabled:
                pool_kwargs['ssl'] = True
                if self.connection_config.ssl_keyfile:
                    pool_kwargs['ssl_keyfile'] = self.connection_config.ssl_keyfile
                if self.connection_config.ssl_certfile:
                    pool_kwargs['ssl_certfile'] = self.connection_config.ssl_certfile
                if self.connection_config.ssl_ca_certs:
                    pool_kwargs['ssl_ca_certs'] = self.connection_config.ssl_ca_certs
                pool_kwargs['ssl_cert_reqs'] = self.connection_config.ssl_cert_reqs
                pool_kwargs['ssl_check_hostname'] = self.connection_config.ssl_check_hostname
            
            # Create connection pool
            pool = ConnectionPool(**pool_kwargs)
            self._redis = Redis(connection_pool=pool)
            
            # Test connection
            await self._redis.ping()
            
            self._is_connected = True
            self.logger.info(
                "Redis Streams client connected successfully",
                extra={
                    "host": self.connection_config.host,
                    "port": self.connection_config.port,
                    "consumer_group": self.stream_config.consumer_group
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Redis Streams client: {e}")
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        try:
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            self._is_connected = False
            self.logger.info("Redis Streams client disconnected successfully")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting Redis Streams client: {e}")
            raise RedisConnectionError(f"Failed to disconnect from Redis: {e}") from e
    
    async def create_consumer_group(self, stream_name: str, start_id: str = "0") -> bool:
        """Create consumer group for stream."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            await self._redis.xgroup_create(
                stream_name,
                self.stream_config.consumer_group,
                id=start_id,
                mkstream=True
            )
            
            self.logger.info(
                f"Created consumer group {self.stream_config.consumer_group} for stream {stream_name}"
            )
            return True
            
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Consumer group already exists
                self.logger.debug(
                    f"Consumer group {self.stream_config.consumer_group} already exists for stream {stream_name}"
                )
                return True
            else:
                self.logger.error(f"Failed to create consumer group: {e}")
                raise RedisStreamError(f"Failed to create consumer group: {e}") from e
        except Exception as e:
            self.logger.error(f"Failed to create consumer group: {e}")
            raise RedisStreamError(f"Failed to create consumer group: {e}") from e
    
    async def add_to_stream(
        self,
        stream_name: str,
        fields: Dict[str, Any],
        message_id: str = "*",
        maxlen: Optional[int] = None,
        approximate: bool = True
    ) -> str:
        """Add message to Redis stream."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            # Serialize complex fields
            serialized_fields = {}
            for key, value in fields.items():
                if isinstance(value, (dict, list)):
                    serialized_fields[key] = json.dumps(value)
                else:
                    serialized_fields[key] = str(value)
            
            # Add to stream
            result_id = await self._redis.xadd(
                stream_name,
                serialized_fields,
                id=message_id,
                maxlen=maxlen or self.stream_config.stream_maxlen,
                approximate=approximate
            )
            
            self.logger.debug(
                f"Message added to stream {stream_name}",
                extra={
                    "stream": stream_name,
                    "message_id": result_id
                }
            )
            
            return result_id
            
        except Exception as e:
            self.logger.error(f"Failed to add message to stream {stream_name}: {e}")
            raise RedisStreamError(f"Failed to add message to stream: {e}") from e
    
    async def read_from_stream(
        self,
        stream_name: str,
        start_id: str = RedisStreamReadMode.NEW_MESSAGES.value,
        count: Optional[int] = None,
        block: Optional[int] = None
    ) -> List[RedisMessage]:
        """Read messages from Redis stream using consumer group."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            # Read from stream using consumer group
            messages = await self._redis.xreadgroup(
                self.stream_config.consumer_group,
                self.stream_config.consumer_name,
                {stream_name: start_id},
                count=count or self.stream_config.count,
                block=block or self.stream_config.block_time
            )
            
            redis_messages = []
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    redis_message = RedisMessage.from_stream_message(stream, msg_id, fields)
                    redis_messages.append(redis_message)
            
            if redis_messages:
                self.logger.debug(
                    f"Read {len(redis_messages)} messages from stream {stream_name}"
                )
            
            return redis_messages
            
        except Exception as e:
            self.logger.error(f"Failed to read from stream {stream_name}: {e}")
            raise RedisStreamError(f"Failed to read from stream: {e}") from e
    
    async def acknowledge_message(self, stream_name: str, message_id: str) -> int:
        """Acknowledge message processing."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            result = await self._redis.xack(
                stream_name,
                self.stream_config.consumer_group,
                message_id
            )
            
            self.logger.debug(
                f"Acknowledged message {message_id} from stream {stream_name}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge message {message_id}: {e}")
            raise RedisStreamError(f"Failed to acknowledge message: {e}") from e
    
    async def claim_pending_messages(
        self,
        stream_name: str,
        min_idle_time: Optional[int] = None,
        count: Optional[int] = None
    ) -> List[RedisMessage]:
        """Claim pending messages from other consumers."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            # Auto-claim pending messages
            result = await self._redis.xautoclaim(
                stream_name,
                self.stream_config.consumer_group,
                self.stream_config.consumer_name,
                min_idle_time or self.stream_config.auto_claim_min_idle_time,
                start_id="0-0",
                count=count or self.stream_config.auto_claim_count
            )
            
            # Parse claimed messages
            claimed_messages = []
            if len(result) >= 2 and result[1]:  # Check if messages were claimed
                for msg_id, fields in result[1]:
                    redis_message = RedisMessage.from_stream_message(stream_name, msg_id, fields)
                    claimed_messages.append(redis_message)
            
            if claimed_messages:
                self.logger.info(
                    f"Claimed {len(claimed_messages)} pending messages from stream {stream_name}"
                )
            
            return claimed_messages
            
        except Exception as e:
            self.logger.error(f"Failed to claim pending messages from stream {stream_name}: {e}")
            raise RedisStreamError(f"Failed to claim pending messages: {e}") from e
    
    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about Redis stream."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            info = await self._redis.xinfo_stream(stream_name)
            return dict(info)
            
        except Exception as e:
            self.logger.error(f"Failed to get stream info for {stream_name}: {e}")
            raise RedisStreamError(f"Failed to get stream info: {e}") from e
    
    async def get_consumer_group_info(self, stream_name: str) -> List[Dict[str, Any]]:
        """Get consumer group information."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis Streams client not connected")
        
        try:
            groups = await self._redis.xinfo_groups(stream_name)
            return [dict(group) for group in groups]
            
        except Exception as e:
            self.logger.error(f"Failed to get consumer group info for {stream_name}: {e}")
            raise RedisStreamError(f"Failed to get consumer group info: {e}") from e
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected


class RedisClient(MessageBroker):
    """
    Enterprise-grade Redis client with comprehensive features.
    
    Features:
    - Pub/Sub patterns with channels and pattern matching
    - Redis Streams support with consumer groups
    - Redis Cluster and Sentinel integration
    - Connection pooling and high availability
    - SSL/TLS security and authentication
    - Comprehensive monitoring and health checks
    - Integration with reliability patterns
    """
    
    def __init__(
        self,
        connection_config: RedisConnectionConfig,
        pubsub_config: Optional[RedisPubSubConfig] = None,
        stream_config: Optional[RedisStreamConfig] = None,
        cluster_config: Optional[RedisClusterConfig] = None,
        sentinel_config: Optional[RedisSentinelConfig] = None,
        reliability_manager: Optional[Any] = None,
        logger: Optional[CommunicationLogger] = None
    ):
        super().__init__(reliability_manager, logger)
        
        self.connection_config = connection_config
        self.pubsub_config = pubsub_config or RedisPubSubConfig()
        self.stream_config = stream_config
        self.cluster_config = cluster_config
        self.sentinel_config = sentinel_config
        
        self._redis: Optional[Union[Redis, RedisCluster]] = None
        self._pubsub_client: Optional[RedisPubSubClient] = None
        self._stream_client: Optional[RedisStreamClient] = None
        self._sentinel: Optional[Sentinel] = None
        self._is_connected = False
        self._message_handlers: Dict[str, MessageHandler] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self) -> None:
        """Connect to Redis server/cluster."""
        try:
            if self.connection_config.connection_type == RedisConnectionType.CLUSTER:
                await self._connect_cluster()
            elif self.connection_config.connection_type == RedisConnectionType.SENTINEL:
                await self._connect_sentinel()
            else:
                await self._connect_standalone()
            
            # Initialize Pub/Sub client if configured
            if self.pubsub_config:
                self._pubsub_client = RedisPubSubClient(
                    self.connection_config,
                    self.pubsub_config,
                    self.logger
                )
                await self._pubsub_client.connect()
            
            # Initialize Streams client if configured
            if self.stream_config:
                self._stream_client = RedisStreamClient(
                    self.connection_config,
                    self.stream_config,
                    self.logger
                )
                await self._stream_client.connect()
            
            self._is_connected = True
            self.logger.info(
                "Redis client connected successfully",
                extra={
                    "connection_type": self.connection_config.connection_type.value,
                    "pubsub_enabled": self._pubsub_client is not None,
                    "streams_enabled": self._stream_client is not None
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to connect Redis client: {e}")
            await self.disconnect()  # Cleanup partial connections
            raise RedisConnectionError(f"Failed to connect to Redis: {e}") from e
    
    async def _connect_standalone(self) -> None:
        """Connect to standalone Redis server."""
        pool_kwargs = {
            'host': self.connection_config.host,
            'port': self.connection_config.port,
            'db': self.connection_config.db,
            'max_connections': self.connection_config.max_connections,
            'retry_on_timeout': self.connection_config.retry_on_timeout,
            'health_check_interval': self.connection_config.health_check_interval,
            'socket_timeout': self.connection_config.socket_timeout,
            'socket_connect_timeout': self.connection_config.socket_connect_timeout,
            'socket_keepalive': self.connection_config.socket_keepalive,
            'decode_responses': True,
        }
        
        # Add authentication
        if self.connection_config.username:
            pool_kwargs['username'] = self.connection_config.username
        if self.connection_config.password:
            pool_kwargs['password'] = self.connection_config.password
        
        # Add SSL configuration
        if self.connection_config.ssl_enabled:
            pool_kwargs['ssl'] = True
            if self.connection_config.ssl_keyfile:
                pool_kwargs['ssl_keyfile'] = self.connection_config.ssl_keyfile
            if self.connection_config.ssl_certfile:
                pool_kwargs['ssl_certfile'] = self.connection_config.ssl_certfile
            if self.connection_config.ssl_ca_certs:
                pool_kwargs['ssl_ca_certs'] = self.connection_config.ssl_ca_certs
            pool_kwargs['ssl_cert_reqs'] = self.connection_config.ssl_cert_reqs
            pool_kwargs['ssl_check_hostname'] = self.connection_config.ssl_check_hostname
        
        # Create connection pool
        pool = ConnectionPool(**pool_kwargs)
        self._redis = Redis(connection_pool=pool)
        
        # Test connection
        await self._redis.ping()
    
    async def _connect_cluster(self) -> None:
        """Connect to Redis Cluster."""
        if not self.cluster_config or not self.cluster_config.startup_nodes:
            raise RedisClusterError("Cluster configuration required for cluster connection")
        
        cluster_kwargs = {
            'startup_nodes': self.cluster_config.startup_nodes,
            'max_connections_per_node': self.cluster_config.max_connections_per_node,
            'skip_full_coverage_check': self.cluster_config.skip_full_coverage_check,
            'readonly_mode': self.cluster_config.readonly_mode,
            'decode_responses': self.cluster_config.decode_responses,
            'health_check_interval': self.cluster_config.health_check_interval,
        }
        
        # Add authentication
        if self.connection_config.username:
            cluster_kwargs['username'] = self.connection_config.username
        if self.connection_config.password:
            cluster_kwargs['password'] = self.connection_config.password
        
        # Add SSL configuration
        if self.connection_config.ssl_enabled:
            cluster_kwargs['ssl'] = True
            if self.connection_config.ssl_keyfile:
                cluster_kwargs['ssl_keyfile'] = self.connection_config.ssl_keyfile
            if self.connection_config.ssl_certfile:
                cluster_kwargs['ssl_certfile'] = self.connection_config.ssl_certfile
            if self.connection_config.ssl_ca_certs:
                cluster_kwargs['ssl_ca_certs'] = self.connection_config.ssl_ca_certs
            cluster_kwargs['ssl_cert_reqs'] = self.connection_config.ssl_cert_reqs
            cluster_kwargs['ssl_check_hostname'] = self.connection_config.ssl_check_hostname
        
        self._redis = RedisCluster(**cluster_kwargs)
        
        # Test connection
        await self._redis.ping()
    
    async def _connect_sentinel(self) -> None:
        """Connect to Redis via Sentinel."""
        if not self.sentinel_config or not self.sentinel_config.sentinels:
            raise RedisConnectionError("Sentinel configuration required for sentinel connection")
        
        self._sentinel = Sentinel(
            self.sentinel_config.sentinels,
            sentinel_kwargs=self.sentinel_config.sentinel_kwargs
        )
        
        # Get master connection
        master_kwargs = self.sentinel_config.connection_kwargs.copy()
        if self.connection_config.password:
            master_kwargs['password'] = self.connection_config.password
        
        self._redis = self._sentinel.master_for(
            self.sentinel_config.service_name,
            **master_kwargs
        )
        
        # Test connection
        await self._redis.ping()
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server/cluster."""
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
            
            # Disconnect Pub/Sub client
            if self._pubsub_client:
                await self._pubsub_client.disconnect()
                self._pubsub_client = None
            
            # Disconnect Streams client
            if self._stream_client:
                await self._stream_client.disconnect()
                self._stream_client = None
            
            # Disconnect main Redis client
            if self._redis:
                await self._redis.close()
                self._redis = None
            
            # Close sentinel
            if self._sentinel:
                # Sentinel doesn't have a close method in redis-py
                self._sentinel = None
            
            self._is_connected = False
            self._message_handlers.clear()
            
            self.logger.info("Redis client disconnected successfully")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting Redis client: {e}")
            raise RedisConnectionError(f"Failed to disconnect from Redis: {e}") from e
    
    async def publish(
        self,
        channel: str,
        message: Union[Message, Any],
        **kwargs
    ) -> bool:
        """Publish message to Redis channel with reliability patterns."""
        if not self._is_connected:
            raise RedisConnectionError("Redis client not connected")
        
        # Convert to RedisMessage if needed
        if not isinstance(message, RedisMessage):
            redis_message = RedisMessage(
                content=message,
                channel=channel
            )
        else:
            redis_message = message
            redis_message.channel = channel
        
        # Apply reliability patterns
        async def _publish_operation():
            try:
                if self._pubsub_client:
                    # Use Pub/Sub client
                    subscribers = await self._pubsub_client.publish(channel, redis_message.content)
                elif self._redis:
                    # Use main Redis client
                    if isinstance(redis_message.content, (dict, list)):
                        serialized_content = json.dumps(redis_message.content)
                    else:
                        serialized_content = str(redis_message.content)
                    
                    subscribers = await self._redis.publish(channel, serialized_content)
                else:
                    raise RedisConnectionError("No Redis client available")
                
                # Update metrics
                if self.reliability_manager:
                    self.reliability_manager.metrics.record_message_sent(channel)
                
                self.logger.debug(
                    f"Message published to channel {channel}",
                    extra={
                        "channel": channel,
                        "subscribers": subscribers,
                        "message_id": redis_message.message_id
                    }
                )
                
                return True
                
            except Exception as e:
                # Update metrics
                if self.reliability_manager:
                    self.reliability_manager.metrics.record_message_error(channel, str(e))
                
                raise RedisPublishError(f"Failed to publish message: {e}") from e
        
        # Apply reliability patterns if available
        if self.reliability_manager:
            return await self.reliability_manager.execute_with_reliability(
                _publish_operation,
                context={"channel": channel, "message_id": redis_message.message_id}
            )
        else:
            return await _publish_operation()
    
    async def subscribe(
        self,
        channel: str,
        handler: MessageHandler,
        **kwargs
    ) -> None:
        """Subscribe to Redis channel with message handler."""
        if not self._is_connected or not self._pubsub_client:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        # Subscribe to channel
        await self._pubsub_client.subscribe(channel)
        
        # Store handler
        self._message_handlers[channel] = handler
        
        # Start consumer task
        task_name = f"pubsub_consumer_{channel}_{uuid.uuid4().hex[:8]}"
        task = asyncio.create_task(self._consume_pubsub_messages(channel, handler))
        self._consumer_tasks[task_name] = task
        
        self.logger.info(f"Subscribed to channel {channel} with handler {handler.__class__.__name__}")
    
    async def subscribe_pattern(
        self,
        pattern: str,
        handler: MessageHandler,
        **kwargs
    ) -> None:
        """Subscribe to Redis channel pattern with message handler."""
        if not self._is_connected or not self._pubsub_client:
            raise RedisConnectionError("Redis Pub/Sub client not connected")
        
        # Subscribe to pattern
        await self._pubsub_client.psubscribe(pattern)
        
        # Store handler
        self._message_handlers[pattern] = handler
        
        # Start consumer task
        task_name = f"pattern_consumer_{pattern}_{uuid.uuid4().hex[:8]}"
        task = asyncio.create_task(self._consume_pattern_messages(pattern, handler))
        self._consumer_tasks[task_name] = task
        
        self.logger.info(f"Subscribed to pattern {pattern} with handler {handler.__class__.__name__}")
    
    async def subscribe_stream(
        self,
        stream_name: str,
        handler: MessageHandler,
        **kwargs
    ) -> None:
        """Subscribe to Redis stream with message handler."""
        if not self._is_connected or not self._stream_client:
            raise RedisConnectionError("Redis Streams client not connected")
        
        # Create consumer group if it doesn't exist
        await self._stream_client.create_consumer_group(stream_name)
        
        # Store handler
        self._message_handlers[stream_name] = handler
        
        # Start consumer task
        task_name = f"stream_consumer_{stream_name}_{uuid.uuid4().hex[:8]}"
        task = asyncio.create_task(self._consume_stream_messages(stream_name, handler))
        self._consumer_tasks[task_name] = task
        
        self.logger.info(f"Subscribed to stream {stream_name} with handler {handler.__class__.__name__}")
    
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from Redis channel."""
        if channel in self._message_handlers:
            del self._message_handlers[channel]
        
        # Stop consumer tasks for this channel
        tasks_to_remove = []
        for task_name, task in self._consumer_tasks.items():
            if channel in task_name:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                tasks_to_remove.append(task_name)
        
        for task_name in tasks_to_remove:
            del self._consumer_tasks[task_name]
        
        # Unsubscribe from Pub/Sub client
        if self._pubsub_client:
            await self._pubsub_client.unsubscribe(channel)
        
        self.logger.info(f"Unsubscribed from channel {channel}")
    
    async def _consume_pubsub_messages(self, channel: str, handler: MessageHandler) -> None:
        """Internal method to consume Pub/Sub messages."""
        try:
            async for redis_message in self._pubsub_client.listen():
                if redis_message.channel != channel:
                    continue
                
                # Apply reliability patterns
                async def _process_message():
                    try:
                        # Create acknowledgment
                        ack = MessageAcknowledgment(
                            message_id=redis_message.message_id,
                            status=MessageStatus.PROCESSING
                        )
                        
                        # Process message with handler
                        await handler.handle(redis_message, ack)
                        
                        # Update metrics
                        if self.reliability_manager and ack.status == MessageStatus.SUCCESS:
                            self.reliability_manager.metrics.record_message_processed(channel)
                        
                        return ack.status == MessageStatus.SUCCESS
                        
                    except Exception as e:
                        ack.status = MessageStatus.FAILED
                        ack.error_message = str(e)
                        
                        # Update metrics
                        if self.reliability_manager:
                            self.reliability_manager.metrics.record_message_error(channel, str(e))
                        
                        self.logger.error(
                            f"Error processing Pub/Sub message from channel {channel}: {e}",
                            extra={
                                "channel": channel,
                                "message_id": redis_message.message_id
                            }
                        )
                        
                        raise
                
                # Apply reliability patterns if available
                if self.reliability_manager:
                    await self.reliability_manager.execute_with_reliability(
                        _process_message,
                        context={
                            "channel": channel,
                            "message_id": redis_message.message_id
                        }
                    )
                else:
                    await _process_message()
                    
        except asyncio.CancelledError:
            self.logger.debug(f"Pub/Sub consumer task for channel {channel} cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in Pub/Sub consumer task for channel {channel}: {e}")
    
    async def _consume_pattern_messages(self, pattern: str, handler: MessageHandler) -> None:
        """Internal method to consume pattern messages."""
        try:
            async for redis_message in self._pubsub_client.listen():
                if not redis_message.pattern or redis_message.pattern != pattern:
                    continue
                
                # Similar processing as Pub/Sub messages
                async def _process_message():
                    try:
                        ack = MessageAcknowledgment(
                            message_id=redis_message.message_id,
                            status=MessageStatus.PROCESSING
                        )
                        
                        await handler.handle(redis_message, ack)
                        
                        if self.reliability_manager and ack.status == MessageStatus.SUCCESS:
                            self.reliability_manager.metrics.record_message_processed(pattern)
                        
                        return ack.status == MessageStatus.SUCCESS
                        
                    except Exception as e:
                        ack.status = MessageStatus.FAILED
                        ack.error_message = str(e)
                        
                        if self.reliability_manager:
                            self.reliability_manager.metrics.record_message_error(pattern, str(e))
                        
                        self.logger.error(
                            f"Error processing pattern message from {pattern}: {e}",
                            extra={
                                "pattern": pattern,
                                "channel": redis_message.channel,
                                "message_id": redis_message.message_id
                            }
                        )
                        
                        raise
                
                if self.reliability_manager:
                    await self.reliability_manager.execute_with_reliability(
                        _process_message,
                        context={
                            "pattern": pattern,
                            "channel": redis_message.channel,
                            "message_id": redis_message.message_id
                        }
                    )
                else:
                    await _process_message()
                    
        except asyncio.CancelledError:
            self.logger.debug(f"Pattern consumer task for pattern {pattern} cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in pattern consumer task for pattern {pattern}: {e}")
    
    async def _consume_stream_messages(self, stream_name: str, handler: MessageHandler) -> None:
        """Internal method to consume stream messages."""
        try:
            while True:
                try:
                    # Read messages from stream
                    messages = await self._stream_client.read_from_stream(stream_name)
                    
                    if not messages:
                        continue
                    
                    # Process messages
                    for redis_message in messages:
                        async def _process_message():
                            try:
                                ack = MessageAcknowledgment(
                                    message_id=redis_message.message_id,
                                    status=MessageStatus.PROCESSING
                                )
                                
                                await handler.handle(redis_message, ack)
                                
                                # Acknowledge message if processing succeeded
                                if ack.status == MessageStatus.SUCCESS:
                                    await self._stream_client.acknowledge_message(
                                        stream_name, redis_message.stream_id
                                    )
                                    
                                    if self.reliability_manager:
                                        self.reliability_manager.metrics.record_message_processed(stream_name)
                                
                                return ack.status == MessageStatus.SUCCESS
                                
                            except Exception as e:
                                ack.status = MessageStatus.FAILED
                                ack.error_message = str(e)
                                
                                if self.reliability_manager:
                                    self.reliability_manager.metrics.record_message_error(stream_name, str(e))
                                
                                self.logger.error(
                                    f"Error processing stream message from {stream_name}: {e}",
                                    extra={
                                        "stream": stream_name,
                                        "message_id": redis_message.stream_id
                                    }
                                )
                                
                                raise
                        
                        if self.reliability_manager:
                            await self.reliability_manager.execute_with_reliability(
                                _process_message,
                                context={
                                    "stream": stream_name,
                                    "message_id": redis_message.stream_id
                                }
                            )
                        else:
                            await _process_message()
                    
                    # Claim pending messages periodically
                    if len(messages) == 0:  # No new messages, check for pending
                        pending_messages = await self._stream_client.claim_pending_messages(stream_name)
                        for pending_message in pending_messages:
                            # Process pending messages similar to new messages
                            # (implementation similar to above)
                            pass
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in stream consumer loop for {stream_name}: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
                    
        except asyncio.CancelledError:
            self.logger.debug(f"Stream consumer task for {stream_name} cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in stream consumer task for {stream_name}: {e}")
    
    async def add_to_stream(
        self,
        stream_name: str,
        fields: Dict[str, Any],
        **kwargs
    ) -> str:
        """Add message to Redis stream."""
        if not self._is_connected or not self._stream_client:
            raise RedisConnectionError("Redis Streams client not connected")
        
        return await self._stream_client.add_to_stream(stream_name, fields, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis client."""
        health_status = {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "checks": {}
        }
        
        try:
            # Check main connection
            if self._redis:
                try:
                    await self._redis.ping()
                    health_status["checks"]["main_connection"] = {
                        "status": "healthy",
                        "connected": True,
                        "connection_type": self.connection_config.connection_type.value
                    }
                except Exception as e:
                    health_status["checks"]["main_connection"] = {
                        "status": "unhealthy",
                        "connected": False,
                        "error": str(e)
                    }
            
            # Check Pub/Sub client
            if self._pubsub_client:
                health_status["checks"]["pubsub"] = {
                    "status": "healthy" if self._pubsub_client.is_connected else "unhealthy",
                    "connected": self._pubsub_client.is_connected,
                    "subscribed_channels": len(self._pubsub_client.subscribed_channels),
                    "subscribed_patterns": len(self._pubsub_client.subscribed_patterns)
                }
            
            # Check Streams client
            if self._stream_client:
                health_status["checks"]["streams"] = {
                    "status": "healthy" if self._stream_client.is_connected else "unhealthy",
                    "connected": self._stream_client.is_connected,
                    "consumer_group": self.stream_config.consumer_group if self.stream_config else None,
                    "consumer_name": self.stream_config.consumer_name if self.stream_config else None
                }
            
            # Check active consumer tasks
            health_status["checks"]["consumers"] = {
                "status": "healthy",
                "active_tasks": len(self._consumer_tasks),
                "task_names": list(self._consumer_tasks.keys())
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
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis client not connected")
        
        try:
            info = await self._redis.info()
            return dict(info)
        except Exception as e:
            self.logger.error(f"Failed to get Redis info: {e}")
            raise RedisError(f"Failed to get Redis info: {e}") from e
    
    async def get_client_list(self) -> List[Dict[str, Any]]:
        """Get list of connected clients."""
        if not self._is_connected or not self._redis:
            raise RedisConnectionError("Redis client not connected")
        
        try:
            clients = await self._redis.client_list()
            return clients
        except Exception as e:
            self.logger.error(f"Failed to get client list: {e}")
            raise RedisError(f"Failed to get client list: {e}") from e
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected
    
    @property
    def pubsub_client(self) -> Optional[RedisPubSubClient]:
        """Get Pub/Sub client instance."""
        return self._pubsub_client
    
    @property
    def stream_client(self) -> Optional[RedisStreamClient]:
        """Get Streams client instance."""
        return self._stream_client
    
    @property
    def redis_client(self) -> Optional[Union[Redis, RedisCluster]]:
        """Get main Redis client instance."""
        return self._redis


# Utility functions for easy configuration

def create_redis_connection_config(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
    **kwargs
) -> RedisConnectionConfig:
    """Create Redis connection configuration."""
    return RedisConnectionConfig(
        host=host,
        port=port,
        db=db,
        password=password,
        **kwargs
    )


def create_redis_pubsub_config(**kwargs) -> RedisPubSubConfig:
    """Create Redis Pub/Sub configuration."""
    return RedisPubSubConfig(**kwargs)


def create_redis_stream_config(
    consumer_group: str,
    consumer_name: str,
    **kwargs
) -> RedisStreamConfig:
    """Create Redis Streams configuration."""
    return RedisStreamConfig(
        consumer_group=consumer_group,
        consumer_name=consumer_name,
        **kwargs
    )


def create_redis_cluster_config(
    startup_nodes: List[Dict[str, Any]],
    **kwargs
) -> RedisClusterConfig:
    """Create Redis Cluster configuration."""
    return RedisClusterConfig(
        startup_nodes=startup_nodes,
        **kwargs
    )


def create_redis_sentinel_config(
    sentinels: List[Tuple[str, int]],
    service_name: str = "mymaster",
    **kwargs
) -> RedisSentinelConfig:
    """Create Redis Sentinel configuration."""
    return RedisSentinelConfig(
        sentinels=sentinels,
        service_name=service_name,
        **kwargs
    )


def create_ssl_redis_config(
    host: str = "localhost",
    port: int = 6380,
    ssl_certfile: Optional[str] = None,
    ssl_keyfile: Optional[str] = None,
    ssl_ca_certs: Optional[str] = None,
    **kwargs
) -> RedisConnectionConfig:
    """Create SSL-enabled Redis configuration."""
    return RedisConnectionConfig(
        host=host,
        port=port,
        ssl_enabled=True,
        ssl_certfile=ssl_certfile,
        ssl_keyfile=ssl_keyfile,
        ssl_ca_certs=ssl_ca_certs,
        **kwargs
    )


# Export main classes and functions
__all__ = [
    # Main client
    "RedisClient",
    
    # Specialized clients
    "RedisPubSubClient",
    "RedisStreamClient",
    
    # Configuration classes
    "RedisConnectionConfig",
    "RedisPubSubConfig",
    "RedisStreamConfig",
    "RedisClusterConfig",
    "RedisSentinelConfig",
    
    # Message class
    "RedisMessage",
    
    # Enums
    "RedisConnectionType",
    "RedisSSLMode",
    "RedisStreamReadMode",
    
    # Exceptions
    "RedisError",
    "RedisConnectionError",
    "RedisPublishError",
    "RedisSubscribeError",
    "RedisStreamError",
    "RedisClusterError",
    
    # Utility functions
    "create_redis_connection_config",
    "create_redis_pubsub_config",
    "create_redis_stream_config",
    "create_redis_cluster_config",
    "create_redis_sentinel_config",
    "create_ssl_redis_config",
]
# CommunicationManager Enterprise-Grade

## Overview

The CommunicationManager is the central orchestrator for all communication components in the FastAPI Microservices SDK. It provides unified lifecycle management, health monitoring, and a registry pattern for message brokers, HTTP clients, gRPC services, and event sourcing components.

## Features

### Core Capabilities
- **Central Orchestration**: Unified management of all communication components
- **Lifecycle Management**: Graceful startup and shutdown coordination
- **Component Registry**: Registry pattern for dynamic component access
- **Health Monitoring**: Aggregated health checks for all components
- **Error Recovery**: Automatic reconnection and recovery mechanisms
- **Global Access**: Singleton pattern with global instance management

### Enterprise Features
- **Callback System**: Startup, shutdown, and health check callbacks
- **Context Manager**: Async context manager for resource lifecycle
- **Convenience API**: High-level methods for common operations
- **Optional Dependencies**: Graceful handling of missing dependencies
- **Robust Error Handling**: Comprehensive error handling with detailed logging
- **Status Tracking**: Real-time component status with metadata

## Quick Start

### Basic Configuration

```python
from fastapi_microservices_sdk.communication import (
    CommunicationConfig,
    MessageBrokerConfig,
    MessageBrokerType,
    CommunicationManager
)

# Configure message brokers
config = CommunicationConfig(
    message_brokers={
        "rabbitmq": MessageBrokerConfig(
            type=MessageBrokerType.RABBITMQ,
            connection_url="amqp://guest:guest@localhost:5672/"
        ),
        "redis": MessageBrokerConfig(
            type=MessageBrokerType.REDIS,
            connection_url="redis://localhost:6379/0"
        )
    },
    enable_health_checks=True,
    enable_security_integration=True
)

# Create manager
manager = CommunicationManager(config)
```

### Lifecycle Management

```python
import asyncio

async def main():
    # Initialize all components
    await manager.initialize()
    
    # Check overall health
    health = manager.get_health_status()
    print(f"Overall status: {health['overall_status']}")
    
    # Use components
    broker = manager.get_message_broker("rabbitmq")
    await manager.publish_message("rabbitmq", "orders", {"order_id": "123"})
    
    # Graceful shutdown
    await manager.shutdown()

asyncio.run(main())
```

### Context Manager Usage

```python
async def with_context_manager():
    async with manager.lifespan() as mgr:
        # Manager is automatically initialized
        brokers = mgr.list_message_brokers()
        
        for broker_info in brokers:
            if broker_info['connected']:
                await mgr.publish_message(
                    broker_info['name'], 
                    "test.topic", 
                    {"message": "Hello World!"}
                )
    # Manager is automatically shutdown
```

## Advanced Configuration

### Callback System

```python
async def startup_callback(manager):
    print(f"Manager started with {len(manager.component_status)} components")

async def shutdown_callback(manager):
    print("Manager shutting down")

async def health_callback(component_name, status):
    if status.status == 'unhealthy':
        print(f"Component {component_name} is unhealthy: {status.last_error}")

# Register callbacks
manager.add_startup_callback(startup_callback)
manager.add_shutdown_callback(shutdown_callback)
manager.add_health_check_callback(health_callback)
```

### Global Instance Management

```python
from fastapi_microservices_sdk.communication import (
    initialize_communication,
    get_communication_manager,
    shutdown_communication
)

# Initialize global manager
await initialize_communication(config)

# Access from anywhere in your application
manager = get_communication_manager()
if manager:
    await manager.publish_message("redis", "events", {"event": "user_login"})

# Shutdown global manager
await shutdown_communication()
```

## API Reference

### Core Methods

#### Lifecycle Management

```python
async def initialize() -> None
    """Initialize all communication components."""

async def shutdown() -> None
    """Gracefully shutdown all components."""

@property
def is_initialized() -> bool
    """Check if manager is initialized."""

@property
def is_shutdown() -> bool
    """Check if manager is shutdown."""
```

#### Component Access

```python
def get_message_broker(name: str = "default") -> MessageBroker
    """Get message broker by name."""

def get_http_client(name: str = "default") -> HTTPClient
    """Get HTTP client by name."""

def get_grpc_service(name: str) -> GRPCService
    """Get gRPC service by name."""

def get_service_discovery() -> ServiceDiscovery
    """Get service discovery instance."""

def get_event_store() -> EventStore
    """Get event store instance."""
```

#### Health Monitoring

```python
def get_health_status() -> Dict[str, Any]
    """Get health status of all components."""

def list_message_brokers() -> List[Dict[str, Any]]
    """List all configured message brokers."""

async def reconnect_message_broker(name: str) -> bool
    """Reconnect a specific message broker."""
```

#### Convenience Methods

```python
async def publish_message(broker_name: str, topic: str, message: Any, **kwargs) -> None
    """Publish message using specified broker."""

async def subscribe_to_topic(broker_name: str, topic: str, handler, **kwargs) -> None
    """Subscribe to topic using specified broker."""
```

#### Callback Management

```python
def add_startup_callback(callback: Callable) -> None
    """Add startup callback."""

def add_shutdown_callback(callback: Callable) -> None
    """Add shutdown callback."""

def add_health_check_callback(callback: Callable) -> None
    """Add health check callback."""
```

### ComponentStatus Class

```python
class ComponentStatus:
    name: str                    # Component name
    component_type: str          # Component type
    status: str                  # Current status (healthy/unhealthy)
    last_health_check: datetime  # Last health check timestamp
    error_count: int             # Number of errors
    last_error: str              # Last error message
    metadata: Dict[str, Any]     # Additional metadata
    
    def mark_healthy() -> None
        """Mark component as healthy."""
    
    def mark_unhealthy(error: Exception) -> None
        """Mark component as unhealthy."""
    
    def to_dict() -> Dict[str, Any]
        """Convert status to dictionary."""
```

## Health Monitoring

### Health Status Structure

```python
{
    "overall_status": "healthy",  # or "unhealthy"
    "components": {
        "message_broker_rabbitmq": {
            "name": "rabbitmq",
            "type": "message_broker_rabbitmq",
            "status": "healthy",
            "last_health_check": "2025-01-09T10:30:00Z",
            "error_count": 0,
            "last_error": null,
            "metadata": {
                "connection_url": "amqp://localhost:5672",
                "type": "rabbitmq",
                "pool_size": 10
            }
        }
    },
    "timestamp": "2025-01-09T10:30:00Z"
}
```

### Health Check Callbacks

```python
async def monitor_health(component_name: str, status: ComponentStatus):
    """Custom health monitoring logic."""
    if status.status == 'unhealthy':
        # Send alert
        await send_alert(f"Component {component_name} is down")
        
        # Attempt recovery
        if component_name.startswith('message_broker_'):
            broker_name = component_name.replace('message_broker_', '')
            success = await manager.reconnect_message_broker(broker_name)
            if success:
                print(f"Successfully reconnected {broker_name}")

manager.add_health_check_callback(monitor_health)
```

## Error Handling

### Exception Types

The CommunicationManager uses specific exception types for different error scenarios:

```python
from fastapi_microservices_sdk.communication.exceptions import (
    CommunicationError,
    CommunicationConfigurationError
)

try:
    broker = manager.get_message_broker("nonexistent")
except CommunicationError as e:
    print(f"Broker not found: {e}")

try:
    await manager.initialize()
except CommunicationConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Error Recovery

```python
# Automatic recovery example
async def handle_broker_failure():
    try:
        await manager.publish_message("rabbitmq", "orders", {"test": "message"})
    except Exception as e:
        print(f"Publish failed: {e}")
        
        # Attempt reconnection
        success = await manager.reconnect_message_broker("rabbitmq")
        if success:
            # Retry the operation
            await manager.publish_message("rabbitmq", "orders", {"test": "message"})
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await manager.initialize()
    yield
    # Shutdown
    await manager.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health_check():
    return manager.get_health_status()

@app.post("/publish/{broker_name}/{topic}")
async def publish_message(broker_name: str, topic: str, message: dict):
    await manager.publish_message(broker_name, topic, message)
    return {"status": "published"}
```

### Microservice Integration

```python
from fastapi_microservices_sdk.core import MicroserviceApp

class OrderService(MicroserviceApp):
    def __init__(self):
        super().__init__("order-service")
        self.communication_manager = None
    
    async def startup(self):
        # Initialize communication
        config = CommunicationConfig(...)
        self.communication_manager = CommunicationManager(config)
        await self.communication_manager.initialize()
    
    async def shutdown(self):
        if self.communication_manager:
            await self.communication_manager.shutdown()
    
    async def process_order(self, order_data):
        # Publish order event
        await self.communication_manager.publish_message(
            "rabbitmq", 
            "order.events", 
            {"event": "order_created", "order": order_data}
        )
```

## Performance Considerations

### Connection Pooling

The CommunicationManager automatically manages connection pools for optimal performance:

```python
# Connection pools are managed automatically
config = CommunicationConfig(
    message_brokers={
        "rabbitmq": MessageBrokerConfig(
            type=MessageBrokerType.RABBITMQ,
            connection_url="amqp://localhost:5672/",
            connection_pool_size=20  # Managed by the broker
        )
    }
)
```

### Async Operations

All operations are fully asynchronous for maximum performance:

```python
# Concurrent operations
import asyncio

async def concurrent_publishing():
    tasks = []
    for i in range(100):
        task = manager.publish_message("redis", f"topic-{i}", f"message-{i}")
        tasks.append(task)
    
    # Execute all concurrently
    await asyncio.gather(*tasks)
```

### Resource Management

```python
# Proper resource management
async def long_running_service():
    async with manager.lifespan() as mgr:
        while True:
            # Process messages
            await process_messages(mgr)
            await asyncio.sleep(1)
    # Resources automatically cleaned up
```

## Testing

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_manager_lifecycle():
    config = CommunicationConfig(message_brokers={})
    manager = CommunicationManager(config)
    
    await manager.initialize()
    assert manager.is_initialized
    
    await manager.shutdown()
    assert manager.is_shutdown

@pytest.mark.asyncio
async def test_health_monitoring():
    manager = CommunicationManager(config)
    await manager.initialize()
    
    health = manager.get_health_status()
    assert health['overall_status'] in ['healthy', 'unhealthy']
    assert 'components' in health
    
    await manager.shutdown()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_message_broker_integration():
    config = CommunicationConfig(
        message_brokers={
            "test": MessageBrokerConfig(
                type=MessageBrokerType.REDIS,
                connection_url="redis://localhost:6379/15"  # Test DB
            )
        }
    )
    
    async with CommunicationManager(config).lifespan() as manager:
        # Test broker access
        brokers = manager.list_message_brokers()
        assert len(brokers) == 1
        
        # Test publishing (if broker is available)
        if brokers[0]['connected']:
            await manager.publish_message("test", "test.topic", {"test": "data"})
```

## Best Practices

1. **Lifecycle Management**: Always use proper lifecycle management (initialize/shutdown or context manager)
2. **Error Handling**: Implement proper error handling for all operations
3. **Health Monitoring**: Regularly check component health and implement recovery logic
4. **Resource Cleanup**: Use context managers or ensure proper shutdown
5. **Configuration**: Validate configuration before initializing components
6. **Logging**: Use structured logging for better observability
7. **Testing**: Test both success and failure scenarios
8. **Performance**: Use async operations and connection pooling for high throughput

## Troubleshooting

### Common Issues

1. **Component Not Found**: Ensure component is configured in CommunicationConfig
2. **Connection Failures**: Check network connectivity and credentials
3. **Health Check Failures**: Verify component dependencies are available
4. **Memory Leaks**: Ensure proper shutdown and resource cleanup
5. **Performance Issues**: Check connection pool sizes and async usage

### Debug Logging

```python
import logging

# Enable debug logging
logging.getLogger("communication_manager").setLevel(logging.DEBUG)

# The manager will log detailed information about:
# - Component initialization
# - Health check results
# - Error conditions
# - Recovery attempts
```

For more examples and advanced usage, see the complete example in `examples/communication_manager_example.py`.
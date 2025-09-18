"""
Communication Manager Example for FastAPI Microservices SDK.

This example demonstrates how to use the CommunicationManager to orchestrate
all communication components in a microservices architecture.
"""

import asyncio
import logging
from datetime import datetime

from fastapi_microservices_sdk.communication import (
    CommunicationConfig,
    MessageBrokerConfig,
    HTTPClientConfig,
    ServiceDiscoveryConfig,
    GRPCConfig,
    EventSourcingConfig,
    MessageBrokerType,
    ServiceDiscoveryType,
    CommunicationManager,
    initialize_communication,
    shutdown_communication,
    get_communication_manager
)

from fastapi_microservices_sdk.communication.logging import (
    CommunicationLogger,
    CorrelationContext,
    set_service_name
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = CommunicationLogger("example")


async def create_sample_configuration() -> CommunicationConfig:
    """Create a sample communication configuration."""
    
    # Message broker configuration
    rabbitmq_config = MessageBrokerConfig(
        type=MessageBrokerType.RABBITMQ,
        connection_url="amqp://guest:guest@localhost:5672/",
        connection_pool_size=10,
        dead_letter_queue=True
    )
    
    kafka_config = MessageBrokerConfig(
        type=MessageBrokerType.KAFKA,
        connection_url="localhost:9092",
        kafka_config={
            "bootstrap_servers": ["localhost:9092"],
            "client_id": "example-service",
            "group_id": "example-group"
        }
    )
    
    # HTTP client configuration
    http_config = HTTPClientConfig()
    
    # Service discovery configuration
    service_discovery_config = ServiceDiscoveryConfig(
        type=ServiceDiscoveryType.CONSUL,
        connection_url="http://localhost:8500",
        namespace="microservices"
    )
    
    # gRPC configuration
    grpc_config = GRPCConfig(
        server_port=50051,
        enable_tls=True,
        enable_health_check=True
    )
    
    # Event sourcing configuration
    event_sourcing_config = EventSourcingConfig(
        enable_event_store=True,
        store_type="memory",
        enable_cqrs=True,
        enable_sagas=True
    )
    
    # Main configuration
    config = CommunicationConfig(
        message_brokers={
            "rabbitmq": rabbitmq_config,
            "kafka": kafka_config
        },
        http_clients={
            "default": http_config,
            "external": http_config
        },
        service_discovery=service_discovery_config,
        grpc=grpc_config,
        event_sourcing=event_sourcing_config,
        enable_security_integration=True,
        enable_observability=True
    )
    
    logger.info("Sample configuration created", metadata={
        'message_brokers': len(config.message_brokers),
        'http_clients': len(config.http_clients),
        'service_discovery': config.service_discovery.type,
        'grpc_enabled': True,
        'event_sourcing_enabled': config.event_sourcing.enable_event_store
    })
    
    return config


async def demonstrate_manager_lifecycle():
    """Demonstrate communication manager lifecycle."""
    
    logger.info("=== Communication Manager Lifecycle Demo ===")
    
    # Create configuration
    config = await create_sample_configuration()
    
    # Method 1: Direct manager usage
    logger.info("Creating CommunicationManager directly")
    manager = CommunicationManager(config)
    
    # Add callbacks
    async def startup_callback(mgr):
        logger.info("Startup callback executed", metadata={
            'components': len(mgr.component_status)
        })
    
    async def shutdown_callback(mgr):
        logger.info("Shutdown callback executed")
    
    async def health_callback(component_name, status):
        logger.log_health_check(component_name, status.status)
    
    manager.add_startup_callback(startup_callback)
    manager.add_shutdown_callback(shutdown_callback)
    manager.add_health_check_callback(health_callback)
    
    # Initialize manager
    logger.info("Initializing communication manager")
    await manager.initialize()
    
    # Check status
    health_status = manager.get_health_status()
    logger.info("Manager initialized", metadata={
        'overall_status': health_status['overall_status'],
        'component_count': len(health_status['components'])
    })
    
    # List available message brokers
    brokers = manager.list_message_brokers()
    logger.info("Available message brokers", metadata={
        'brokers': [{'name': b['name'], 'type': b['type'], 'status': b['status']} for b in brokers]
    })
    
    # Demonstrate broker usage (if any are available and connected)
    for broker_info in brokers:
        if broker_info['connected']:
            try:
                logger.info(f"Testing broker: {broker_info['name']}")
                
                # Test publish (will work with real brokers)
                await manager.publish_message(
                    broker_info['name'], 
                    "test.topic", 
                    {"message": "Hello from CommunicationManager!", "timestamp": datetime.now().isoformat()}
                )
                
                logger.info(f"Successfully published to {broker_info['name']}")
                
            except Exception as e:
                logger.info(f"Broker {broker_info['name']} not fully functional (expected): {e}")
    
    # Simulate some work
    await asyncio.sleep(1)
    
    # Shutdown manager
    logger.info("Shutting down communication manager")
    await manager.shutdown()
    
    logger.info("Manager lifecycle completed")


async def demonstrate_global_manager():
    """Demonstrate global communication manager."""
    
    logger.info("=== Global Communication Manager Demo ===")
    
    # Create configuration
    config = await create_sample_configuration()
    
    # Initialize global manager
    logger.info("Initializing global communication manager")
    manager = await initialize_communication(config)
    
    # Get global manager instance
    global_manager = get_communication_manager()
    assert global_manager is manager
    
    logger.info("Global manager initialized", metadata={
        'is_same_instance': global_manager is manager,
        'is_initialized': manager.is_initialized
    })
    
    # Check health status
    health_status = global_manager.get_health_status()
    logger.info("Global manager health check", metadata=health_status)
    
    # Shutdown global manager
    logger.info("Shutting down global communication manager")
    await shutdown_communication()
    
    logger.info("Global manager demo completed")


async def demonstrate_context_manager():
    """Demonstrate communication manager as context manager."""
    
    logger.info("=== Context Manager Demo ===")
    
    # Create configuration
    config = await create_sample_configuration()
    manager = CommunicationManager(config)
    
    # Use as context manager
    logger.info("Using manager as async context manager")
    async with manager.lifespan() as mgr:
        logger.info("Inside context manager", metadata={
            'is_initialized': mgr.is_initialized,
            'is_shutdown': mgr.is_shutdown
        })
        
        # Simulate work
        await asyncio.sleep(0.5)
        
        # Check component status
        for name, status in mgr.component_status.items():
            logger.log_health_check(name, status.status, metadata={
                'component_type': status.component_type,
                'error_count': status.error_count
            })
    
    logger.info("Context manager demo completed", metadata={
        'is_shutdown': manager.is_shutdown
    })


async def demonstrate_correlation_tracking():
    """Demonstrate correlation ID tracking."""
    
    logger.info("=== Correlation Tracking Demo ===")
    
    # Set service name context
    set_service_name("example-service")
    
    # Use correlation context
    with CorrelationContext("demo-correlation-123", "example-service"):
        logger.info("Inside correlation context")
        
        # Log various communication events
        logger.log_http_request("GET", "http://api.example.com/users", status_code=200, duration_ms=150.5)
        logger.log_message_publish("rabbitmq", "user.events", message_size=1024)
        logger.log_service_discovery("register", "example-service", "consul")
        logger.log_grpc_call("UserService", "GetUser", "success", duration_ms=75.2)
        
        # Simulate nested operations
        await simulate_nested_operations()
    
    logger.info("Correlation tracking demo completed")


async def simulate_nested_operations():
    """Simulate nested operations with correlation tracking."""
    
    logger.info("Nested operation started")
    
    # These logs will inherit the correlation ID from the context
    logger.log_http_response("POST", "http://api.example.com/users", 201, 200.0)
    logger.log_message_consume("kafka", "user.commands", processing_time_ms=50.0)
    
    await asyncio.sleep(0.1)
    
    logger.info("Nested operation completed")


async def demonstrate_message_broker_integration():
    """Demonstrate message broker integration capabilities."""
    
    logger.info("=== Message Broker Integration Demo ===")
    
    # Create configuration with memory brokers for testing
    config = CommunicationConfig(
        message_brokers={
            "memory1": MessageBrokerConfig(
                type=MessageBrokerType.MEMORY,
                connection_url="memory://broker1"
            ),
            "memory2": MessageBrokerConfig(
                type=MessageBrokerType.MEMORY,
                connection_url="memory://broker2"
            )
        },
        enable_health_checks=True
    )
    
    manager = CommunicationManager(config)
    
    try:
        await manager.initialize()
        
        # List all brokers
        brokers = manager.list_message_brokers()
        logger.info("Configured message brokers", metadata={
            'broker_count': len(brokers),
            'brokers': [{'name': b['name'], 'type': b['type']} for b in brokers]
        })
        
        # Test individual broker access
        for broker_info in brokers:
            broker_name = broker_info['name']
            
            try:
                # Get broker instance
                broker = manager.get_message_broker(broker_name)
                logger.info(f"Retrieved broker: {broker_name}", metadata={
                    'broker_type': type(broker).__name__,
                    'connected': getattr(broker, 'is_connected', False)
                })
                
                # Test convenience methods
                test_message = {
                    'id': f'test-{broker_name}',
                    'content': f'Hello from {broker_name}!',
                    'timestamp': datetime.now().isoformat()
                }
                
                # This will work with actual broker implementations
                logger.info(f"Testing publish to {broker_name}")
                
            except Exception as e:
                logger.info(f"Broker {broker_name} test failed (expected with placeholders): {e}")
        
        # Test health monitoring
        logger.info("Performing health checks")
        await manager._perform_health_checks()
        
        health_status = manager.get_health_status()
        logger.info("Health check results", metadata={
            'overall_status': health_status['overall_status'],
            'healthy_components': sum(1 for c in health_status['components'].values() if c['status'] == 'healthy'),
            'total_components': len(health_status['components'])
        })
        
        await manager.shutdown()
        
    except Exception as e:
        logger.error(f"Message broker integration demo failed: {e}")


async def demonstrate_error_scenarios():
    """Demonstrate error handling scenarios."""
    
    logger.info("=== Error Scenarios Demo ===")
    
    # Create configuration with invalid settings to trigger errors
    config = CommunicationConfig(
        message_brokers={
            "invalid": MessageBrokerConfig(
                type=MessageBrokerType.RABBITMQ,
                connection_url="amqp://invalid:5672/"
            )
        }
    )
    
    manager = CommunicationManager(config)
    
    try:
        # This will try to connect to real brokers and may fail
        await manager.initialize()
        
        # Check component status for errors
        health_status = manager.get_health_status()
        logger.info("Manager with invalid config initialized", metadata={
            'overall_status': health_status['overall_status'],
            'components': list(health_status['components'].keys())
        })
        
        # Test error handling
        try:
            manager.get_message_broker('nonexistent')
        except Exception as e:
            logger.info(f"Expected error for nonexistent broker: {e}")
        
        # Log some error scenarios
        logger.log_circuit_breaker("invalid-service", "open", 5)
        logger.log_health_check("invalid-component", "unhealthy", metadata={
            'error': 'Connection refused'
        })
        
        await manager.shutdown()
        
    except Exception as e:
        logger.error(f"Error during initialization (expected): {e}")


async def main():
    """Main example function."""
    
    print("🚀 FastAPI Microservices SDK - Communication Manager Example")
    print("=" * 60)
    
    try:
        # Set up correlation context for the entire demo
        with CorrelationContext("main-demo-session", "communication-example"):
            
            # Demonstrate different aspects of the communication manager
            await demonstrate_manager_lifecycle()
            print()
            
            await demonstrate_global_manager()
            print()
            
            await demonstrate_context_manager()
            print()
            
            await demonstrate_correlation_tracking()
            print()
            
            await demonstrate_message_broker_integration()
            print()
            
            await demonstrate_error_scenarios()
            print()
        
        print("✅ All demonstrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
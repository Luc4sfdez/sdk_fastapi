"""
Advanced Consul Service Discovery Example

This example demonstrates advanced Consul features including:
- ACL integration
- KV store operations
- Leader election
- Cluster monitoring
- Multiple health checks
- Configuration management
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consul_acl_example():
    """Example demonstrating Consul ACL operations."""
    print("\n=== Consul ACL Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        
        # Create Consul backend with ACL enabled
        consul = ConsulServiceDiscovery(
            host="localhost",
            port=8500,
            token="master-token",  # Use your master token
            acl_enabled=True,
            acl_default_policy="deny"
        )
        
        await consul.connect()
        
        # Create ACL token for a service
        print("Creating ACL token...")
        service_rules = '''
        service "user-service" {
            policy = "write"
        }
        service "" {
            policy = "read"
        }
        key "config/user-service/" {
            policy = "write"
        }
        '''
        
        token_id = await consul.create_acl_token(
            name="user-service-token",
            type_="client",
            rules=service_rules
        )
        
        if token_id:
            print(f"Created ACL token: {token_id}")
            
            # Get token information
            token_info = await consul.get_acl_token_info(token_id)
            if token_info:
                print(f"Token info: {token_info['Name']} ({token_info['Type']})")
            
            # Clean up - destroy token
            success = await consul.destroy_acl_token(token_id)
            print(f"Token destroyed: {success}")
        
        await consul.disconnect()
        print("ACL example completed!")
        
    except Exception as e:
        print(f"ACL example failed: {e}")
        print("Make sure Consul is running with ACL enabled and you have a master token")


async def consul_kv_store_example():
    """Example demonstrating Consul KV store operations."""
    print("\n=== Consul KV Store Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        
        consul = ConsulServiceDiscovery(
            host="localhost",
            port=8500,
            kv_prefix="myapp/"
        )
        
        await consul.connect()
        
        # Set simple key-value pairs
        print("Setting configuration values...")
        await consul.set_kv_value("database/host", "db.example.com")
        await consul.set_kv_value("database/port", "5432")
        await consul.set_kv_value("database/name", "myapp_prod")
        
        # Set JSON configuration
        app_config = {
            "features": {
                "feature_a": True,
                "feature_b": False,
                "feature_c": "beta"
            },
            "limits": {
                "max_connections": 100,
                "timeout": 30,
                "retry_attempts": 3
            },
            "cache": {
                "enabled": True,
                "ttl": 3600,
                "max_size": 1000
            }
        }
        
        await consul.set_kv_json("app/config", app_config)
        print("Configuration stored in KV store")
        
        # Retrieve values
        print("\nRetrieving configuration...")
        db_host = await consul.get_kv_value("database/host")
        db_port = await consul.get_kv_value("database/port")
        print(f"Database: {db_host}:{db_port}")
        
        # Retrieve JSON configuration
        retrieved_config = await consul.get_kv_json("app/config")
        if retrieved_config:
            print(f"App config features: {retrieved_config['features']}")
            print(f"Connection limit: {retrieved_config['limits']['max_connections']}")
        
        # Get all keys with prefix
        print("\nAll configuration keys:")
        keys = await consul.get_kv_keys("")
        for key in keys:
            print(f"  - {key}")
        
        # Get recursive configuration
        print("\nRecursive configuration:")
        all_config = await consul.get_kv_recursive("")
        for key, value in all_config.items():
            print(f"  {key}: {value}")
        
        # Service-specific configuration
        print("\nService configuration management...")
        service_config = {
            "database": {
                "host": "service-db.example.com",
                "port": 5432,
                "pool_size": 20
            },
            "redis": {
                "host": "service-redis.example.com",
                "port": 6379,
                "db": 1
            }
        }
        
        await consul.set_service_config("user-service", service_config)
        retrieved_service_config = await consul.get_service_config("user-service")
        print(f"User service config: {retrieved_service_config}")
        
        await consul.disconnect()
        print("KV store example completed!")
        
    except Exception as e:
        print(f"KV store example failed: {e}")


async def consul_leader_election_example():
    """Example demonstrating Consul leader election."""
    print("\n=== Consul Leader Election Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        
        # Create multiple Consul clients simulating different service instances
        instances = []
        for i in range(3):
            consul = ConsulServiceDiscovery(
                host="localhost",
                port=8500,
                leader_election_key="service/user-service/leader",
                enable_cluster_monitoring=True
            )
            consul.name = f"user-service-{i}"  # Override name for identification
            instances.append(consul)
        
        # Connect all instances
        for consul in instances:
            await consul.connect()
        
        # Try to acquire leadership from all instances
        print("Attempting leader election...")
        leaders = []
        for i, consul in enumerate(instances):
            is_leader = await consul.acquire_leadership(session_ttl=30)
            print(f"Instance {i} ({consul.name}) leader: {is_leader}")
            if is_leader:
                leaders.append(consul)
        
        # Should have exactly one leader
        print(f"\nNumber of leaders: {len(leaders)}")
        if leaders:
            leader = leaders[0]
            print(f"Leader: {leader.name}")
            
            # Simulate leader doing work
            print("Leader performing work...")
            await asyncio.sleep(2)
            
            # Release leadership
            print("Leader releasing leadership...")
            await leader.release_leadership()
            print(f"Leadership released by {leader.name}")
            
            # Another instance can now become leader
            for consul in instances:
                if consul != leader:
                    is_new_leader = await consul.acquire_leadership()
                    if is_new_leader:
                        print(f"New leader: {consul.name}")
                        await consul.release_leadership()
                        break
        
        # Disconnect all instances
        for consul in instances:
            await consul.disconnect()
        
        print("Leader election example completed!")
        
    except Exception as e:
        print(f"Leader election example failed: {e}")


async def consul_cluster_monitoring_example():
    """Example demonstrating Consul cluster monitoring."""
    print("\n=== Consul Cluster Monitoring Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        
        consul = ConsulServiceDiscovery(
            host="localhost",
            port=8500,
            enable_cluster_monitoring=True
        )
        
        await consul.connect()
        
        # Get cluster information
        print("Cluster Information:")
        cluster_info = await consul.get_cluster_info()
        print(f"  Leader: {cluster_info.get('leader', 'Unknown')}")
        print(f"  Peers: {cluster_info.get('peer_count', 0)}")
        
        # Get datacenter information
        print("\nDatacenter Information:")
        dc_info = await consul.get_datacenter_info()
        print(f"  Available datacenters: {dc_info.get('datacenters', [])}")
        print(f"  Current datacenter: {dc_info.get('current_datacenter', 'default')}")
        
        # Get comprehensive cluster health
        print("\nCluster Health:")
        health = await consul.get_cluster_health()
        
        if "error" not in health:
            print(f"  Total nodes: {health['nodes']['total']}")
            print(f"  Healthy nodes: {health['nodes']['healthy']}")
            print(f"  Unhealthy nodes: {health['nodes']['unhealthy']}")
            print(f"  Total services: {health['services']['total']}")
            print(f"  Is leader: {health['is_leader']}")
        else:
            print(f"  Error getting health: {health['error']}")
        
        # Monitor for a short time
        print("\nMonitoring cluster for 10 seconds...")
        await asyncio.sleep(10)
        
        await consul.disconnect()
        print("Cluster monitoring example completed!")
        
    except Exception as e:
        print(f"Cluster monitoring example failed: {e}")


async def consul_advanced_service_registration_example():
    """Example demonstrating advanced service registration with multiple health checks."""
    print("\n=== Advanced Service Registration Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        from fastapi_microservices_sdk.communication.discovery.base import ServiceInstance, ServiceStatus
        
        consul = ConsulServiceDiscovery(
            host="localhost",
            port=8500
        )
        
        await consul.connect()
        
        # Create service instance
        instance = ServiceInstance(
            service_name="user-service",
            instance_id="user-service-1",
            address="192.168.1.100",
            port=8080,
            status=ServiceStatus.HEALTHY,
            metadata={
                "version": "1.2.0",
                "environment": "production",
                "region": "us-east-1",
                "weight": 1.0
            },
            tags={"api", "v1", "users", "production"},
            health_check_url="/health"
        )
        
        # Define multiple health checks
        health_checks = [
            {
                "Name": "HTTP Health Check",
                "HTTP": f"http://{instance.address}:{instance.port}/health",
                "Interval": "30s",
                "Timeout": "10s",
                "DeregisterCriticalServiceAfter": "5m"
            },
            {
                "Name": "TCP Connectivity Check",
                "TCP": f"{instance.address}:{instance.port}",
                "Interval": "10s",
                "Timeout": "3s"
            },
            {
                "Name": "Database Connectivity",
                "HTTP": f"http://{instance.address}:{instance.port}/health/db",
                "Interval": "60s",
                "Timeout": "15s"
            },
            {
                "Name": "Memory Usage Check",
                "Script": "/usr/local/bin/check_memory.sh",
                "Interval": "120s",
                "Timeout": "30s"
            }
        ]
        
        # Register service with multiple health checks
        print("Registering service with multiple health checks...")
        success = await consul.register_service_with_checks(instance, health_checks)
        print(f"Service registered: {success}")
        
        if success:
            # Wait a moment for health checks to run
            await asyncio.sleep(5)
            
            # Get detailed health information
            print("\nDetailed health information:")
            health_info = await consul.get_service_health_detailed("user-service")
            
            if "error" not in health_info:
                print(f"Service: {health_info['service_name']}")
                print(f"Total instances: {health_info['summary']['total']}")
                print(f"Passing: {health_info['summary']['passing']}")
                print(f"Warning: {health_info['summary']['warning']}")
                print(f"Critical: {health_info['summary']['critical']}")
                
                for instance_health in health_info['instances']:
                    print(f"\nInstance: {instance_health['instance_id']}")
                    print(f"  Status: {instance_health['status']}")
                    print(f"  Address: {instance_health['address']}:{instance_health['port']}")
                    print("  Checks:")
                    for check in instance_health['checks']:
                        print(f"    - {check['name']}: {check['status']}")
                        if check['output']:
                            print(f"      Output: {check['output'][:100]}...")
            
            # Deregister service
            print("\nDeregistering service...")
            await consul.deregister_service("user-service", "user-service-1")
            print("Service deregistered")
        
        await consul.disconnect()
        print("Advanced service registration example completed!")
        
    except Exception as e:
        print(f"Advanced service registration example failed: {e}")


async def consul_configuration_watch_example():
    """Example demonstrating configuration watching."""
    print("\n=== Configuration Watch Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.consul import ConsulServiceDiscovery
        
        consul = ConsulServiceDiscovery(
            host="localhost",
            port=8500,
            kv_prefix="app/"
        )
        
        await consul.connect()
        
        # Set initial configuration
        initial_config = {
            "database": {"host": "db1.example.com", "port": 5432},
            "cache": {"enabled": True, "ttl": 3600},
            "features": {"feature_x": False}
        }
        
        await consul.set_kv_json("config", initial_config)
        print("Initial configuration set")
        
        # Configuration change handler
        config_changes = []
        
        async def config_change_handler(changes):
            print(f"\n📡 Configuration changed!")
            for key, value in changes.items():
                print(f"  {key}: {value}")
            config_changes.append(changes)
        
        # Start watching configuration
        print("Starting configuration watch...")
        await consul.watch_kv_prefix("", config_change_handler)
        
        # Simulate configuration changes
        print("\nSimulating configuration changes...")
        await asyncio.sleep(2)
        
        # Update configuration
        updated_config = {
            "database": {"host": "db2.example.com", "port": 5432},
            "cache": {"enabled": True, "ttl": 7200},
            "features": {"feature_x": True, "feature_y": True}
        }
        
        await consul.set_kv_json("config", updated_config)
        print("Configuration updated")
        
        # Wait for watch to detect changes
        await asyncio.sleep(3)
        
        print(f"Total configuration changes detected: {len(config_changes)}")
        
        await consul.disconnect()
        print("Configuration watch example completed!")
        
    except Exception as e:
        print(f"Configuration watch example failed: {e}")


async def main():
    """Run all Consul advanced examples."""
    print("🔍 FastAPI Microservices SDK - Advanced Consul Examples")
    print("=" * 60)
    
    # Run examples
    await consul_kv_store_example()
    await consul_advanced_service_registration_example()
    await consul_cluster_monitoring_example()
    await consul_leader_election_example()
    await consul_configuration_watch_example()
    await consul_acl_example()
    
    print("\n" + "=" * 60)
    print("✅ All advanced Consul examples completed!")
    print("\nNote: Some examples may fail if Consul is not running or properly configured.")
    print("To run all examples successfully, ensure you have:")
    print("  - Consul running on localhost:8500")
    print("  - ACL enabled with a master token (for ACL example)")
    print("  - Proper network connectivity")


if __name__ == "__main__":
    asyncio.run(main())
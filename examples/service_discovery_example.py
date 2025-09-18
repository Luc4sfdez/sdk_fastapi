"""
Service Discovery Example

This example demonstrates how to use the service discovery components
with different backends (Consul, etcd, Kubernetes).
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi_microservices_sdk.communication.discovery import (
    ServiceInstance,
    ServiceStatus,
    EnhancedServiceRegistry,
    ConsulServiceDiscovery,
    EtcdServiceDiscovery,
    KubernetesServiceDiscovery,
    LoadBalancingStrategy,
    DiscoveryEvent
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def consul_example():
    """Example using Consul service discovery."""
    print("\n=== Consul Service Discovery Example ===")
    
    try:
        # Create Consul backend
        consul_backend = ConsulServiceDiscovery(
            host="localhost",
            port=8500,
            token=None  # Add token if Consul ACL is enabled
        )
        
        # Create registry with Consul backend
        registry = EnhancedServiceRegistry(
            backends=[consul_backend],
            cache_ttl=60,
            enable_health_checks=True,
            load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN
        )
        
        # Start registry
        await registry.start()
        
        # Create service instances
        instances = [
            ServiceInstance(
                service_name="user-service",
                instance_id=f"user-service-{i}",
                address=f"192.168.1.{100 + i}",
                port=8080,
                status=ServiceStatus.HEALTHY,
                metadata={"version": "1.0.0", "region": "us-east-1"},
                tags={"api", "v1"},
                health_check_url="/health"
            )
            for i in range(3)
        ]
        
        # Register services
        print("Registering services...")
        for instance in instances:
            success = await registry.register(instance)
            print(f"Registered {instance.instance_id}: {success}")
        
        # Discover services
        print("\nDiscovering services...")
        discovered = await registry.discover("user-service")
        print(f"Discovered {len(discovered)} instances:")
        for instance in discovered:
            print(f"  - {instance.instance_id} at {instance.url} (status: {instance.status.value})")
        
        # Load balanced discovery
        print("\nLoad balanced discovery...")
        for i in range(5):
            selected = await registry.discover_with_load_balancing("user-service", count=1)
            if selected:
                print(f"  Round {i+1}: Selected {selected[0].instance_id}")
        
        # Health check
        print("\nRegistry health check...")
        health = await registry.health_check()
        print(f"Overall status: {health['overall']['status']}")
        print(f"Healthy backends: {health['overall']['healthy_backends']}/{health['overall']['total_backends']}")
        
        # Deregister services
        print("\nDeregistering services...")
        for instance in instances:
            success = await registry.deregister(instance.service_name, instance.instance_id)
            print(f"Deregistered {instance.instance_id}: {success}")
        
        # Stop registry
        await registry.stop()
        print("Consul example completed successfully!")
        
    except Exception as e:
        print(f"Consul example failed: {e}")
        print("Make sure Consul is running on localhost:8500")


async def etcd_example():
    """Example using etcd service discovery."""
    print("\n=== etcd Service Discovery Example ===")
    
    try:
        # Create etcd backend
        etcd_backend = EtcdServiceDiscovery(
            host="localhost",
            port=2379,
            lease_ttl=30
        )
        
        # Create registry with etcd backend
        registry = EnhancedServiceRegistry(
            backends=[etcd_backend],
            cache_ttl=60,
            enable_health_checks=False,  # Disable for this example
            load_balancing_strategy=LoadBalancingStrategy.RANDOM
        )
        
        # Start registry
        await registry.start()
        
        # Create service instance
        instance = ServiceInstance(
            service_name="order-service",
            instance_id="order-service-1",
            address="192.168.1.200",
            port=8081,
            status=ServiceStatus.HEALTHY,
            metadata={"version": "2.0.0", "database": "postgresql"},
            tags={"api", "v2", "orders"},
            health_check_url="/health"
        )
        
        # Register service
        print("Registering service...")
        success = await registry.register(instance)
        print(f"Registered {instance.instance_id}: {success}")
        
        # Discover service
        print("\nDiscovering service...")
        discovered = await registry.discover("order-service")
        print(f"Discovered {len(discovered)} instances:")
        for inst in discovered:
            print(f"  - {inst.instance_id} at {inst.url}")
            print(f"    Metadata: {inst.metadata}")
            print(f"    Tags: {inst.tags}")
        
        # Discover with tag filter
        print("\nDiscovering with tag filter (v2)...")
        discovered_v2 = await registry.discover("order-service", tags={"v2"})
        print(f"Discovered {len(discovered_v2)} v2 instances")
        
        # Update service health
        print("\nUpdating service health...")
        await registry.update_service_health(
            instance.service_name,
            instance.instance_id,
            ServiceStatus.UNHEALTHY
        )
        
        # Discover again to see health change
        discovered_after_update = await registry.discover("order-service")
        if discovered_after_update:
            print(f"Service status after update: {discovered_after_update[0].status.value}")
        
        # Deregister service
        print("\nDeregistering service...")
        success = await registry.deregister(instance.service_name, instance.instance_id)
        print(f"Deregistered {instance.instance_id}: {success}")
        
        # Stop registry
        await registry.stop()
        print("etcd example completed successfully!")
        
    except Exception as e:
        print(f"etcd example failed: {e}")
        print("Make sure etcd is running on localhost:2379")
        print("Install etcd3 package: pip install etcd3")


async def kubernetes_example():
    """Example using Kubernetes service discovery."""
    print("\n=== Kubernetes Service Discovery Example ===")
    
    try:
        # Create Kubernetes backend
        k8s_backend = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,  # Set to True when running inside cluster
            label_selector="managed-by=fastapi-microservices-sdk"
        )
        
        # Create registry with Kubernetes backend
        registry = EnhancedServiceRegistry(
            backends=[k8s_backend],
            cache_ttl=30,
            enable_health_checks=False,
            load_balancing_strategy=LoadBalancingStrategy.HEALTH_BASED
        )
        
        # Start registry
        await registry.start()
        
        # Create service instance
        instance = ServiceInstance(
            service_name="payment-service",
            instance_id="payment-service-1",
            address="10.244.1.100",
            port=8082,
            status=ServiceStatus.HEALTHY,
            metadata={"version": "1.5.0", "payment-provider": "stripe"},
            tags={"api", "payments", "secure"},
            health_check_url="/health"
        )
        
        # Register service (creates Kubernetes Service and Endpoints)
        print("Registering service...")
        success = await registry.register(instance)
        print(f"Registered {instance.instance_id}: {success}")
        
        # Discover service
        print("\nDiscovering service...")
        discovered = await registry.discover("payment-service")
        print(f"Discovered {len(discovered)} instances:")
        for inst in discovered:
            print(f"  - {inst.instance_id} at {inst.url}")
        
        # List all services
        print("\nListing all services...")
        all_services = await registry.list_services()
        print(f"All services: {all_services}")
        
        # Get cluster info (Kubernetes-specific)
        print("\nGetting cluster info...")
        cluster_info = await k8s_backend.get_cluster_info()
        if cluster_info:
            print(f"Cluster version: {cluster_info.get('version', {}).get('gitVersion', 'Unknown')}")
            print(f"Node count: {cluster_info.get('node_count', 0)}")
        
        # Deregister service
        print("\nDeregistering service...")
        success = await registry.deregister(instance.service_name, instance.instance_id)
        print(f"Deregistered {instance.instance_id}: {success}")
        
        # Stop registry
        await registry.stop()
        print("Kubernetes example completed successfully!")
        
    except Exception as e:
        print(f"Kubernetes example failed: {e}")
        print("Make sure you have access to a Kubernetes cluster")
        print("Install kubernetes-asyncio package: pip install kubernetes-asyncio")


async def multi_backend_example():
    """Example using multiple service discovery backends."""
    print("\n=== Multi-Backend Service Discovery Example ===")
    
    try:
        # Create multiple backends (mock for this example)
        from fastapi_microservices_sdk.communication.discovery.base import ServiceDiscoveryBackend
        
        class MockBackend(ServiceDiscoveryBackend):
            def __init__(self, name: str):
                super().__init__(name, {})
                self._services = {}
            
            async def connect(self):
                self.is_connected = True
            
            async def disconnect(self):
                self.is_connected = False
            
            async def register_service(self, instance):
                if instance.service_name not in self._services:
                    self._services[instance.service_name] = []
                self._services[instance.service_name].append(instance)
                return True
            
            async def deregister_service(self, service_name, instance_id):
                if service_name in self._services:
                    self._services[service_name] = [
                        i for i in self._services[service_name]
                        if i.instance_id != instance_id
                    ]
                return True
            
            async def discover_services(self, service_name, tags=None):
                return self._services.get(service_name, [])
            
            async def get_all_services(self):
                return self._services
            
            async def health_check(self):
                return True
        
        # Create multiple mock backends
        primary_backend = MockBackend("primary")
        secondary_backend = MockBackend("secondary")
        
        # Create registry with multiple backends
        registry = EnhancedServiceRegistry(
            backends=[primary_backend, secondary_backend],
            cache_ttl=60,
            enable_health_checks=False,
            load_balancing_strategy=LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
        )
        
        # Add event handler
        def handle_discovery_event(event: DiscoveryEvent):
            print(f"Event: {event.event_type.value} for service {event.service_name}")
        
        registry.add_event_handler(handle_discovery_event)
        
        # Start registry
        await registry.start()
        
        # Create service instances
        instances = [
            ServiceInstance(
                service_name="notification-service",
                instance_id=f"notification-{i}",
                address=f"192.168.2.{100 + i}",
                port=8083,
                status=ServiceStatus.HEALTHY,
                metadata={"weight": float(i + 1), "provider": "email"},
                tags={"notifications", "email"}
            )
            for i in range(2)
        ]
        
        # Register services (will register to all backends)
        print("Registering services to multiple backends...")
        for instance in instances:
            success = await registry.register(instance)
            print(f"Registered {instance.instance_id}: {success}")
        
        # Discover services
        print("\nDiscovering services...")
        discovered = await registry.discover("notification-service")
        print(f"Discovered {len(discovered)} instances from primary backend")
        
        # Test load balancing
        print("\nTesting load balancing...")
        for i in range(6):
            selected = await registry.discover_with_load_balancing("notification-service", count=1)
            if selected:
                weight = selected[0].metadata.get("weight", 1.0)
                print(f"  Selection {i+1}: {selected[0].instance_id} (weight: {weight})")
        
        # Get cache statistics
        print("\nCache statistics...")
        cache_stats = registry.get_cache_stats()
        print(f"Cache hits: {cache_stats['hits']}, misses: {cache_stats['misses']}")
        print(f"Hit rate: {cache_stats['hit_rate']}%")
        
        # Health check
        print("\nMulti-backend health check...")
        health = await registry.health_check()
        print(f"Overall status: {health['overall']['status']}")
        for backend_name, backend_health in health['backends'].items():
            print(f"  {backend_name}: {backend_health['status']}")
        
        # Stop registry
        await registry.stop()
        print("Multi-backend example completed successfully!")
        
    except Exception as e:
        print(f"Multi-backend example failed: {e}")


async def event_handling_example():
    """Example demonstrating service discovery event handling."""
    print("\n=== Event Handling Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.base import ServiceDiscoveryBackend
        
        class EventEmittingBackend(ServiceDiscoveryBackend):
            def __init__(self):
                super().__init__("event-backend", {})
                self._services = {}
            
            async def connect(self):
                self.is_connected = True
                await self._emit_event(DiscoveryEvent(
                    event_type=DiscoveryEventType.BACKEND_CONNECTED,
                    service_name="event-backend"
                ))
            
            async def disconnect(self):
                self.is_connected = False
                await self._emit_event(DiscoveryEvent(
                    event_type=DiscoveryEventType.BACKEND_DISCONNECTED,
                    service_name="event-backend"
                ))
            
            async def register_service(self, instance):
                if instance.service_name not in self._services:
                    self._services[instance.service_name] = []
                self._services[instance.service_name].append(instance)
                
                await self._emit_event(DiscoveryEvent(
                    event_type=DiscoveryEventType.SERVICE_REGISTERED,
                    service_name=instance.service_name,
                    instance=instance
                ))
                return True
            
            async def deregister_service(self, service_name, instance_id):
                if service_name in self._services:
                    self._services[service_name] = [
                        i for i in self._services[service_name]
                        if i.instance_id != instance_id
                    ]
                
                await self._emit_event(DiscoveryEvent(
                    event_type=DiscoveryEventType.SERVICE_DEREGISTERED,
                    service_name=service_name,
                    metadata={"instance_id": instance_id}
                ))
                return True
            
            async def discover_services(self, service_name, tags=None):
                return self._services.get(service_name, [])
            
            async def get_all_services(self):
                return self._services
            
            async def health_check(self):
                return True
        
        # Event handler
        events_received = []
        
        async def event_handler(event: DiscoveryEvent):
            events_received.append(event)
            print(f"📡 Event received: {event.event_type.value}")
            print(f"   Service: {event.service_name}")
            print(f"   Timestamp: {event.timestamp}")
            if event.instance:
                print(f"   Instance: {event.instance.instance_id}")
            print()
        
        # Create backend and registry
        backend = EventEmittingBackend()
        registry = EnhancedServiceRegistry(
            backends=[backend],
            enable_health_checks=False
        )
        
        # Add event handler
        registry.add_event_handler(event_handler)
        
        # Start registry (should emit BACKEND_CONNECTED event)
        print("Starting registry...")
        await registry.start()
        
        # Create and register service (should emit SERVICE_REGISTERED event)
        instance = ServiceInstance(
            service_name="event-test-service",
            instance_id="event-test-1",
            address="192.168.3.100",
            port=8084
        )
        
        print("Registering service...")
        await registry.register(instance)
        
        # Deregister service (should emit SERVICE_DEREGISTERED event)
        print("Deregistering service...")
        await registry.deregister(instance.service_name, instance.instance_id)
        
        # Stop registry (should emit BACKEND_DISCONNECTED event)
        print("Stopping registry...")
        await registry.stop()
        
        # Summary
        print(f"Total events received: {len(events_received)}")
        for i, event in enumerate(events_received, 1):
            print(f"  {i}. {event.event_type.value} - {event.service_name}")
        
        print("Event handling example completed successfully!")
        
    except Exception as e:
        print(f"Event handling example failed: {e}")


async def main():
    """Run all service discovery examples."""
    print("🔍 FastAPI Microservices SDK - Service Discovery Examples")
    print("=" * 60)
    
    # Run examples
    await consul_example()
    await etcd_example()
    await kubernetes_example()
    await multi_backend_example()
    await event_handling_example()
    
    print("\n" + "=" * 60)
    print("✅ All service discovery examples completed!")
    print("\nNote: Some examples may fail if the required backends are not running.")
    print("To run all examples successfully, ensure you have:")
    print("  - Consul running on localhost:8500")
    print("  - etcd running on localhost:2379")
    print("  - Access to a Kubernetes cluster")


if __name__ == "__main__":
    asyncio.run(main())
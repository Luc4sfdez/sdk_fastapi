"""
Advanced etcd and Kubernetes Service Discovery Example

This example demonstrates advanced features including:
- etcd distributed locking and leader election
- etcd configuration management
- Kubernetes RBAC integration
- Cross-cluster service discovery
- Service mesh integration
- DNS-based discovery
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def etcd_distributed_locking_example():
    """Example demonstrating etcd distributed locking."""
    print("\n=== etcd Distributed Locking Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.etcd import EtcdServiceDiscovery
        
        # Create multiple etcd clients simulating different service instances
        instances = []
        for i in range(3):
            etcd_client = EtcdServiceDiscovery(
                host="localhost",
                port=2379,
                lock_ttl=30
            )
            etcd_client.name = f"service-instance-{i}"
            instances.append(etcd_client)
        
        # Connect all instances
        for etcd_client in instances:
            await etcd_client.connect()
        
        # Try to acquire lock from all instances
        print("Attempting to acquire distributed lock...")
        lock_holders = []
        
        for i, etcd_client in enumerate(instances):
            has_lock = await etcd_client.acquire_lock("critical-section", ttl=60)
            print(f"Instance {i} ({etcd_client.name}) acquired lock: {has_lock}")
            if has_lock:
                lock_holders.append(etcd_client)
        
        # Should have exactly one lock holder
        print(f"\nNumber of lock holders: {len(lock_holders)}")
        
        if lock_holders:
            lock_holder = lock_holders[0]
            print(f"Lock holder: {lock_holder.name}")
            
            # Simulate critical work
            print("Performing critical work...")
            await asyncio.sleep(2)
            
            # Release lock
            print("Releasing lock...")
            await lock_holder.release_lock("critical-section")
            print(f"Lock released by {lock_holder.name}")
            
            # Another instance can now acquire the lock
            for etcd_client in instances:
                if etcd_client != lock_holder:
                    has_lock = await etcd_client.acquire_lock("critical-section", ttl=30)
                    if has_lock:
                        print(f"New lock holder: {etcd_client.name}")
                        await etcd_client.release_lock("critical-section")
                        break
        
        # Disconnect all instances
        for etcd_client in instances:
            await etcd_client.disconnect()
        
        print("Distributed locking example completed!")
        
    except Exception as e:
        print(f"Distributed locking example failed: {e}")
        print("Make sure etcd is running on localhost:2379")
        print("Install etcd3 package: pip install etcd3")


async def etcd_configuration_management_example():
    """Example demonstrating etcd configuration management."""
    print("\n=== etcd Configuration Management Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.etcd import EtcdServiceDiscovery
        
        etcd_client = EtcdServiceDiscovery(
            host="localhost",
            port=2379,
            config_prefix="/myapp/config/"
        )
        
        await etcd_client.connect()
        
        # Set service-specific configuration
        print("Setting service configuration...")
        service_config = {
            "database": {
                "host": "db.example.com",
                "port": 5432,
                "pool_size": 20,
                "timeout": 30
            },
            "cache": {
                "enabled": True,
                "host": "redis.example.com",
                "port": 6379,
                "ttl": 3600
            },
            "features": {
                "new_auth": True,
                "beta_features": False,
                "rate_limiting": True
            }
        }
        
        await etcd_client.set_service_config("user-service", service_config)
        print("Service configuration stored")
        
        # Retrieve service configuration
        print("\nRetrieving service configuration...")
        retrieved_config = await etcd_client.get_service_config("user-service")
        if retrieved_config:
            print(f"Database host: {retrieved_config['database']['host']}")
            print(f"Cache enabled: {retrieved_config['cache']['enabled']}")
            print(f"New auth feature: {retrieved_config['features']['new_auth']}")
        
        # Set global configuration
        print("\nSetting global configuration...")
        await etcd_client.set_global_config_value("max_connections", 1000)
        await etcd_client.set_global_config_value("timeout", 30)
        await etcd_client.set_global_config_value("environment", "production")
        
        # Get all global configuration
        global_config = await etcd_client.get_global_config()
        print("Global configuration:")
        for key, value in global_config.items():
            print(f"  {key}: {value}")
        
        # Configuration watching
        print("\nStarting configuration watch...")
        config_changes = []
        
        async def config_change_handler(change_info):
            print(f"📡 Configuration changed: {change_info['key']} = {change_info['value']}")
            config_changes.append(change_info)
        
        await etcd_client.watch_config_prefix("services/", config_change_handler)
        
        # Simulate configuration change
        await asyncio.sleep(1)
        updated_config = {**service_config, "version": "1.1.0"}
        await etcd_client.set_service_config("user-service", updated_config)
        
        # Wait for watch to detect change
        await asyncio.sleep(2)
        print(f"Configuration changes detected: {len(config_changes)}")
        
        await etcd_client.disconnect()
        print("Configuration management example completed!")
        
    except Exception as e:
        print(f"Configuration management example failed: {e}")


async def etcd_leader_election_example():
    """Example demonstrating etcd leader election."""
    print("\n=== etcd Leader Election Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.etcd import EtcdServiceDiscovery
        
        # Create multiple etcd clients for leader election
        candidates = []
        for i in range(3):
            etcd_client = EtcdServiceDiscovery(
                host="localhost",
                port=2379,
                lock_ttl=30
            )
            etcd_client.name = f"candidate-{i}"
            candidates.append(etcd_client)
        
        # Connect all candidates
        for candidate in candidates:
            await candidate.connect()
        
        # Leader election
        print("Starting leader election...")
        leaders = []
        
        for i, candidate in enumerate(candidates):
            is_leader = await candidate.acquire_leadership("service-coordinator")
            print(f"Candidate {i} ({candidate.name}) is leader: {is_leader}")
            if is_leader:
                leaders.append(candidate)
        
        # Should have exactly one leader
        print(f"\nElected leaders: {len(leaders)}")
        
        if leaders:
            leader = leaders[0]
            print(f"Leader: {leader.name}")
            
            # Leader performs coordination work
            print("Leader performing coordination tasks...")
            await asyncio.sleep(3)
            
            # Get cluster health as leader
            health = await leader.get_cluster_health()
            print(f"Cluster health (from leader): {health.get('cluster_info', {})}")
            
            # Release leadership
            print("Leader stepping down...")
            await leader.release_leadership()
            print(f"Leadership released by {leader.name}")
            
            # New leader election
            print("\nNew leader election...")
            for candidate in candidates:
                if candidate != leader:
                    is_new_leader = await candidate.acquire_leadership("service-coordinator")
                    if is_new_leader:
                        print(f"New leader elected: {candidate.name}")
                        await candidate.release_leadership()
                        break
        
        # Disconnect all candidates
        for candidate in candidates:
            await candidate.disconnect()
        
        print("Leader election example completed!")
        
    except Exception as e:
        print(f"Leader election example failed: {e}")


async def kubernetes_rbac_example():
    """Example demonstrating Kubernetes RBAC integration."""
    print("\n=== Kubernetes RBAC Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.kubernetes import KubernetesServiceDiscovery
        
        k8s_client = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,  # Set to True when running in cluster
            enable_rbac=True
        )
        
        await k8s_client.connect()
        
        # Check various RBAC permissions
        print("Checking RBAC permissions...")
        
        permissions_to_check = [
            ("services", "get"),
            ("services", "create"),
            ("endpoints", "get"),
            ("pods", "list"),
            ("secrets", "get"),
            ("configmaps", "get")
        ]
        
        for resource, verb in permissions_to_check:
            allowed = await k8s_client.check_rbac_permissions(resource, verb)
            status = "✅ ALLOWED" if allowed else "❌ DENIED"
            print(f"  {verb.upper()} {resource}: {status}")
        
        # Get service account information
        print("\nService account information:")
        sa_info = await k8s_client.get_service_account_info()
        if "error" not in sa_info:
            print(f"  Service Account: {sa_info.get('service_account', 'Unknown')}")
            print(f"  Namespace: {sa_info.get('namespace', 'Unknown')}")
        else:
            print(f"  Error: {sa_info['error']}")
        
        await k8s_client.disconnect()
        print("RBAC example completed!")
        
    except Exception as e:
        print(f"RBAC example failed: {e}")
        print("Make sure you have access to a Kubernetes cluster")
        print("Install kubernetes-asyncio package: pip install kubernetes-asyncio")


async def kubernetes_service_mesh_example():
    """Example demonstrating Kubernetes service mesh integration."""
    print("\n=== Kubernetes Service Mesh Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.kubernetes import KubernetesServiceDiscovery
        
        # Test with Istio
        k8s_istio = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,
            enable_service_mesh=True,
            service_mesh_type="istio"
        )
        
        await k8s_istio.connect()
        
        print("Getting Istio service mesh configuration...")
        istio_config = await k8s_istio.get_service_mesh_config("user-service")
        
        if istio_config:
            print(f"Service mesh type: {istio_config.get('type', 'unknown')}")
            print(f"VirtualServices: {len(istio_config.get('virtual_services', []))}")
            print(f"DestinationRules: {len(istio_config.get('destination_rules', []))}")
        else:
            print("No Istio configuration found (expected if Istio is not installed)")
        
        await k8s_istio.disconnect()
        
        # Test with Linkerd
        k8s_linkerd = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,
            enable_service_mesh=True,
            service_mesh_type="linkerd"
        )
        
        await k8s_linkerd.connect()
        
        print("\nGetting Linkerd service mesh configuration...")
        linkerd_config = await k8s_linkerd.get_service_mesh_config("user-service")
        
        if linkerd_config:
            print(f"Service mesh type: {linkerd_config.get('type', 'unknown')}")
            print(f"ServiceProfiles: {len(linkerd_config.get('service_profiles', []))}")
        else:
            print("No Linkerd configuration found (expected if Linkerd is not installed)")
        
        await k8s_linkerd.disconnect()
        print("Service mesh example completed!")
        
    except Exception as e:
        print(f"Service mesh example failed: {e}")


async def kubernetes_cross_cluster_example():
    """Example demonstrating cross-cluster service discovery."""
    print("\n=== Kubernetes Cross-Cluster Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.kubernetes import KubernetesServiceDiscovery
        
        k8s_client = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,
            cross_cluster=True,
            cluster_configs=[
                {
                    "name": "production-east",
                    "kubeconfig_path": "/path/to/prod-east-config"
                },
                {
                    "name": "production-west", 
                    "kubeconfig_path": "/path/to/prod-west-config"
                }
            ]
        )
        
        await k8s_client.connect()
        
        # Discover services across clusters
        print("Discovering services across clusters...")
        cluster_services = await k8s_client.discover_services_cross_cluster("user-service")
        
        print(f"Found services in {len(cluster_services)} clusters:")
        for cluster_name, instances in cluster_services.items():
            print(f"\n  Cluster: {cluster_name}")
            for instance in instances:
                print(f"    - {instance.instance_id} at {instance.url}")
                print(f"      Cluster: {instance.metadata.get('cluster', 'unknown')}")
        
        # Get cluster resources
        print("\nCluster resources:")
        resources = await k8s_client.get_cluster_resources()
        if resources:
            print(f"  Nodes: {resources['nodes']['ready']}/{resources['nodes']['total']} ready")
            print(f"  Namespaces: {resources['namespaces']['active']}/{resources['namespaces']['total']} active")
            print(f"  PVs: {resources['persistent_volumes']['available']}/{resources['persistent_volumes']['total']} available")
        
        await k8s_client.disconnect()
        print("Cross-cluster example completed!")
        
    except Exception as e:
        print(f"Cross-cluster example failed: {e}")
        print("Note: This example requires multiple Kubernetes clusters configured")


async def kubernetes_dns_discovery_example():
    """Example demonstrating DNS-based service discovery."""
    print("\n=== Kubernetes DNS Discovery Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.kubernetes import KubernetesServiceDiscovery
        
        k8s_client = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False,
            enable_dns_discovery=True,
            dns_suffix="cluster.local"
        )
        
        await k8s_client.connect()
        
        # Test DNS-based discovery
        print("Testing DNS-based service discovery...")
        
        # Common Kubernetes services to test
        test_services = ["kubernetes", "kube-dns"]
        
        for service_name in test_services:
            print(f"\nDiscovering {service_name} via DNS...")
            dns_instances = await k8s_client.discover_services_via_dns(service_name)
            
            if dns_instances:
                print(f"  Found {len(dns_instances)} instances via DNS:")
                for instance in dns_instances:
                    print(f"    - {instance.address}:{instance.port}")
                    print(f"      DNS name: {instance.metadata.get('dns_name', 'unknown')}")
            else:
                print(f"  No instances found via DNS for {service_name}")
        
        await k8s_client.disconnect()
        print("DNS discovery example completed!")
        
    except Exception as e:
        print(f"DNS discovery example failed: {e}")


async def kubernetes_service_dependencies_example():
    """Example demonstrating service dependency analysis."""
    print("\n=== Kubernetes Service Dependencies Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery.kubernetes import KubernetesServiceDiscovery
        
        k8s_client = KubernetesServiceDiscovery(
            namespace="default",
            in_cluster=False
        )
        
        await k8s_client.connect()
        
        # Analyze service dependencies
        print("Analyzing service dependencies...")
        
        test_services = ["user-service", "order-service", "payment-service"]
        
        for service_name in test_services:
            print(f"\nDependencies for {service_name}:")
            dependencies = await k8s_client.get_service_dependencies(service_name)
            
            if dependencies:
                # Ingress dependencies
                if dependencies.get("ingress"):
                    print("  Ingress routes:")
                    for ingress in dependencies["ingress"]:
                        print(f"    - {ingress['name']}: {ingress['host']}{ingress['path']}")
                
                # Network policies
                if dependencies.get("network_policies"):
                    print("  Network policies:")
                    for policy in dependencies["network_policies"]:
                        print(f"    - {policy['name']}: {policy['policy_types']}")
                
                # ConfigMaps
                if dependencies.get("config_maps"):
                    print(f"  ConfigMaps: {', '.join(dependencies['config_maps'])}")
                
                # Secrets
                if dependencies.get("secrets"):
                    print(f"  Secrets: {', '.join(dependencies['secrets'])}")
                
                # PVCs
                if dependencies.get("persistent_volume_claims"):
                    print(f"  PVCs: {', '.join(dependencies['persistent_volume_claims'])}")
            else:
                print("  No dependencies found")
        
        await k8s_client.disconnect()
        print("Service dependencies example completed!")
        
    except Exception as e:
        print(f"Service dependencies example failed: {e}")


async def integrated_service_discovery_example():
    """Example demonstrating integrated service discovery with multiple backends."""
    print("\n=== Integrated Service Discovery Example ===")
    
    try:
        from fastapi_microservices_sdk.communication.discovery import EnhancedServiceRegistry
        from fastapi_microservices_sdk.communication.discovery.base import ServiceInstance, ServiceStatus
        
        # Create mock backends for demonstration
        class MockEtcdBackend:
            def __init__(self, name):
                self.name = name
                self.is_connected = False
                self.event_handlers = []
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
            
            def add_event_handler(self, handler):
                self.event_handlers.append(handler)
        
        # Create backends
        etcd_backend = MockEtcdBackend("etcd-mock")
        k8s_backend = MockEtcdBackend("kubernetes-mock")
        
        # Create integrated registry
        registry = EnhancedServiceRegistry(
            backends=[etcd_backend, k8s_backend],
            cache_ttl=60,
            enable_health_checks=False
        )
        
        await registry.start()
        
        # Register services with different characteristics
        services = [
            ServiceInstance(
                service_name="user-service",
                instance_id="user-v1-1",
                address="192.168.1.100",
                port=8080,
                metadata={"version": "1.0.0", "backend": "etcd"},
                tags={"api", "v1", "users"}
            ),
            ServiceInstance(
                service_name="user-service",
                instance_id="user-v2-1",
                address="192.168.1.101",
                port=8080,
                metadata={"version": "2.0.0", "backend": "kubernetes"},
                tags={"api", "v2", "users"}
            ),
            ServiceInstance(
                service_name="order-service",
                instance_id="order-1",
                address="192.168.1.200",
                port=8081,
                metadata={"version": "1.5.0", "backend": "etcd"},
                tags={"api", "orders"}
            )
        ]
        
        # Register all services
        print("Registering services across backends...")
        for service in services:
            success = await registry.register(service)
            backend = service.metadata.get("backend", "unknown")
            print(f"  Registered {service.instance_id} ({backend}): {success}")
        
        # Discover services
        print("\nDiscovering services...")
        user_services = await registry.discover("user-service")
        print(f"User service instances: {len(user_services)}")
        for instance in user_services:
            version = instance.metadata.get("version", "unknown")
            backend = instance.metadata.get("backend", "unknown")
            print(f"  - {instance.instance_id} v{version} ({backend})")
        
        # Discover with tag filtering
        print("\nDiscovering v2 services...")
        v2_services = await registry.discover("user-service", tags={"v2"})
        print(f"V2 user service instances: {len(v2_services)}")
        
        # Load balanced discovery
        print("\nLoad balanced discovery...")
        for i in range(5):
            selected = await registry.discover_with_load_balancing("user-service", count=1)
            if selected:
                version = selected[0].metadata.get("version", "unknown")
                print(f"  Round {i+1}: {selected[0].instance_id} v{version}")
        
        # Registry health check
        print("\nRegistry health check...")
        health = await registry.health_check()
        print(f"Overall status: {health['overall']['status']}")
        print(f"Backends: {health['overall']['healthy_backends']}/{health['overall']['total_backends']}")
        
        await registry.stop()
        print("Integrated service discovery example completed!")
        
    except Exception as e:
        print(f"Integrated service discovery example failed: {e}")


async def main():
    """Run all advanced etcd and Kubernetes examples."""
    print("🔍 FastAPI Microservices SDK - Advanced etcd & Kubernetes Examples")
    print("=" * 70)
    
    # Run examples
    await etcd_distributed_locking_example()
    await etcd_configuration_management_example()
    await etcd_leader_election_example()
    await kubernetes_rbac_example()
    await kubernetes_service_mesh_example()
    await kubernetes_cross_cluster_example()
    await kubernetes_dns_discovery_example()
    await kubernetes_service_dependencies_example()
    await integrated_service_discovery_example()
    
    print("\n" + "=" * 70)
    print("✅ All advanced etcd & Kubernetes examples completed!")
    print("\nNote: Some examples may fail if the required services are not running.")
    print("To run all examples successfully, ensure you have:")
    print("  - etcd running on localhost:2379")
    print("  - Access to a Kubernetes cluster")
    print("  - Service mesh installed (Istio/Linkerd) for mesh examples")
    print("  - Proper RBAC permissions for RBAC examples")


if __name__ == "__main__":
    asyncio.run(main())
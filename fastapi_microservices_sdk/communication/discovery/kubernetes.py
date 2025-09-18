"""
Enhanced Kubernetes service discovery implementation.

This module provides comprehensive Kubernetes integration for service discovery with
RBAC authentication, namespace-aware discovery, cross-cluster support, and advanced
service mesh integration capabilities.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Union
from urllib.parse import urljoin

try:
    from kubernetes_asyncio import client, config, watch
    from kubernetes_asyncio.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None
    watch = None
    ApiException = None

from .base import (
    ServiceDiscoveryBackend,
    ServiceInstance,
    ServiceStatus,
    DiscoveryEvent,
    DiscoveryEventType
)


logger = logging.getLogger(__name__)


class KubernetesServiceDiscovery(ServiceDiscoveryBackend):
    """Enhanced Kubernetes service discovery backend implementation with advanced features."""
    
    def __init__(
        self,
        namespace: str = "default",
        in_cluster: bool = True,
        kubeconfig_path: Optional[str] = None,
        # Service discovery settings
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
        service_port_name: str = "http",
        health_check_path: str = "/health",
        use_endpoints: bool = True,
        # Cross-cluster and namespace settings
        cross_namespace: bool = False,
        cross_cluster: bool = False,
        cluster_configs: Optional[List[Dict[str, Any]]] = None,
        # RBAC and authentication
        enable_rbac: bool = True,
        service_account_token_path: Optional[str] = None,
        # Service mesh integration
        enable_service_mesh: bool = False,
        service_mesh_type: str = "istio",  # istio, linkerd, consul-connect
        # Advanced features
        enable_pod_monitoring: bool = True,
        enable_node_monitoring: bool = False,
        enable_event_watching: bool = True,
        # DNS-based discovery
        enable_dns_discovery: bool = True,
        dns_suffix: str = "cluster.local",
        **kwargs
    ):
        if not KUBERNETES_AVAILABLE:
            raise ImportError("kubernetes-asyncio package is required for Kubernetes service discovery")
        
        super().__init__("kubernetes", {
            "namespace": namespace,
            "in_cluster": in_cluster,
            "kubeconfig_path": kubeconfig_path,
            "label_selector": label_selector,
            "field_selector": field_selector,
            "service_port_name": service_port_name,
            "health_check_path": health_check_path,
            "use_endpoints": use_endpoints,
            "cross_namespace": cross_namespace,
            "cross_cluster": cross_cluster,
            "cluster_configs": cluster_configs,
            "enable_rbac": enable_rbac,
            "service_account_token_path": service_account_token_path,
            "enable_service_mesh": enable_service_mesh,
            "service_mesh_type": service_mesh_type,
            "enable_pod_monitoring": enable_pod_monitoring,
            "enable_node_monitoring": enable_node_monitoring,
            "enable_event_watching": enable_event_watching,
            "enable_dns_discovery": enable_dns_discovery,
            "dns_suffix": dns_suffix,
            **kwargs
        })
        
        self.namespace = namespace
        self.in_cluster = in_cluster
        self.kubeconfig_path = kubeconfig_path
        
        # Service discovery settings
        self.label_selector = label_selector
        self.field_selector = field_selector
        self.service_port_name = service_port_name
        self.health_check_path = health_check_path
        self.use_endpoints = use_endpoints
        
        # Cross-cluster and namespace settings
        self.cross_namespace = cross_namespace
        self.cross_cluster = cross_cluster
        self.cluster_configs = cluster_configs or []
        
        # RBAC and authentication
        self.enable_rbac = enable_rbac
        self.service_account_token_path = service_account_token_path or "/var/run/secrets/kubernetes.io/serviceaccount/token"
        
        # Service mesh integration
        self.enable_service_mesh = enable_service_mesh
        self.service_mesh_type = service_mesh_type
        
        # Advanced features
        self.enable_pod_monitoring = enable_pod_monitoring
        self.enable_node_monitoring = enable_node_monitoring
        self.enable_event_watching = enable_event_watching
        
        # DNS-based discovery
        self.enable_dns_discovery = enable_dns_discovery
        self.dns_suffix = dns_suffix
        
        # API clients
        self._api_client: Optional[client.ApiClient] = None
        self._core_v1_api: Optional[client.CoreV1Api] = None
        self._apps_v1_api: Optional[client.AppsV1Api] = None
        self._networking_v1_api: Optional[client.NetworkingV1Api] = None
        self._rbac_v1_api: Optional[client.RbacAuthorizationV1Api] = None
        
        # Multi-cluster clients
        self._cluster_clients: Dict[str, Dict[str, Any]] = {}
        
        # Watch tasks
        self._watch_tasks: Dict[str, asyncio.Task] = {}
        self._event_watch_task: Optional[asyncio.Task] = None
        
        # Monitoring state
        self._cluster_info: Dict[str, Any] = {}
        self._node_info: Dict[str, Any] = {}
        self._pod_metrics: Dict[str, Any] = {}
    
    async def connect(self) -> None:
        """Connect to Kubernetes API."""
        try:
            # Load Kubernetes configuration
            if self.in_cluster:
                config.load_incluster_config()
            else:
                await config.load_kube_config(config_file=self.kubeconfig_path)
            
            # Create API clients
            self._api_client = client.ApiClient()
            self._core_v1_api = client.CoreV1Api(self._api_client)
            self._apps_v1_api = client.AppsV1Api(self._api_client)
            self._networking_v1_api = client.NetworkingV1Api(self._api_client)
            
            if self.enable_rbac:
                self._rbac_v1_api = client.RbacAuthorizationV1Api(self._api_client)
            
            # Test connection
            await self._core_v1_api.get_api_resources()
            
            # Setup cross-cluster clients if enabled
            if self.cross_cluster:
                await self.setup_cross_cluster_clients()
            
            # Start event watching if enabled
            if self.enable_event_watching:
                await self.start_event_watching()
            
            self.is_connected = True
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.BACKEND_CONNECTED,
                service_name="kubernetes",
                metadata={
                    "backend": "kubernetes", 
                    "namespace": self.namespace,
                    "cross_namespace": self.cross_namespace,
                    "cross_cluster": self.cross_cluster,
                    "rbac_enabled": self.enable_rbac,
                    "service_mesh_enabled": self.enable_service_mesh,
                    "dns_discovery_enabled": self.enable_dns_discovery
                }
            ))
            
            logger.info(f"Connected to Kubernetes API in namespace {self.namespace}")
            if self.cross_cluster:
                logger.info(f"Cross-cluster discovery enabled with {len(self.cluster_configs)} clusters")
            if self.enable_service_mesh:
                logger.info(f"Service mesh integration enabled: {self.service_mesh_type}")
            if self.enable_rbac:
                logger.info("RBAC integration enabled")
        
        except Exception as e:
            self.is_connected = False
            logger.error(f"Failed to connect to Kubernetes API: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Kubernetes API."""
        # Stop event watching
        await self.stop_event_watching()
        
        # Cancel all watch tasks
        for task in self._watch_tasks.values():
            if not task.done():
                task.cancel()
        
        if self._watch_tasks:
            await asyncio.gather(*self._watch_tasks.values(), return_exceptions=True)
        
        self._watch_tasks.clear()
        
        # Close cross-cluster clients
        for cluster_clients in self._cluster_clients.values():
            try:
                await cluster_clients["api_client"].close()
            except Exception as e:
                logger.error(f"Error closing cross-cluster client: {e}")
        
        self._cluster_clients.clear()
        
        # Close main API client
        if self._api_client:
            await self._api_client.close()
        
        self._api_client = None
        self._core_v1_api = None
        self._apps_v1_api = None
        self._networking_v1_api = None
        self._rbac_v1_api = None
        self.is_connected = False
        
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.BACKEND_DISCONNECTED,
            service_name="kubernetes",
            metadata={"backend": "kubernetes"}
        ))
        
        logger.info("Disconnected from Kubernetes API")
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance with Kubernetes (creates Service and Endpoints)."""
        if not self._core_v1_api:
            return False
        
        try:
            # Create Service object
            service_body = client.V1Service(
                metadata=client.V1ObjectMeta(
                    name=instance.service_name,
                    namespace=self.namespace,
                    labels={
                        "app": instance.service_name,
                        "managed-by": "fastapi-microservices-sdk"
                    },
                    annotations=instance.metadata
                ),
                spec=client.V1ServiceSpec(
                    selector={"app": instance.service_name},
                    ports=[
                        client.V1ServicePort(
                            name=self.service_port_name,
                            port=instance.port,
                            target_port=instance.port,
                            protocol="TCP"
                        )
                    ],
                    type="ClusterIP"
                )
            )
            
            # Try to create or update the service
            try:
                await self._core_v1_api.create_namespaced_service(
                    namespace=self.namespace,
                    body=service_body
                )
                logger.info(f"Created Kubernetes service {instance.service_name}")
            except ApiException as e:
                if e.status == 409:  # Already exists
                    await self._core_v1_api.patch_namespaced_service(
                        name=instance.service_name,
                        namespace=self.namespace,
                        body=service_body
                    )
                    logger.info(f"Updated Kubernetes service {instance.service_name}")
                else:
                    raise
            
            # Create Endpoints object if using manual endpoints
            if self.use_endpoints:
                endpoints_body = client.V1Endpoints(
                    metadata=client.V1ObjectMeta(
                        name=instance.service_name,
                        namespace=self.namespace,
                        labels={
                            "app": instance.service_name,
                            "managed-by": "fastapi-microservices-sdk"
                        }
                    ),
                    subsets=[
                        client.V1EndpointSubset(
                            addresses=[
                                client.V1EndpointAddress(
                                    ip=instance.address,
                                    target_ref=client.V1ObjectReference(
                                        kind="Pod",
                                        name=instance.instance_id,
                                        namespace=self.namespace
                                    )
                                )
                            ],
                            ports=[
                                client.V1EndpointPort(
                                    name=self.service_port_name,
                                    port=instance.port,
                                    protocol="TCP"
                                )
                            ]
                        )
                    ]
                )
                
                try:
                    await self._core_v1_api.create_namespaced_endpoints(
                        namespace=self.namespace,
                        body=endpoints_body
                    )
                    logger.info(f"Created Kubernetes endpoints for {instance.service_name}")
                except ApiException as e:
                    if e.status == 409:  # Already exists
                        await self._core_v1_api.patch_namespaced_endpoints(
                            name=instance.service_name,
                            namespace=self.namespace,
                            body=endpoints_body
                        )
                        logger.info(f"Updated Kubernetes endpoints for {instance.service_name}")
                    else:
                        raise
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_REGISTERED,
                service_name=instance.service_name,
                instance=instance,
                metadata={"backend": "kubernetes", "namespace": self.namespace}
            ))
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service with Kubernetes: {e}")
            return False
    
    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance from Kubernetes."""
        if not self._core_v1_api:
            return False
        
        try:
            # Delete Service
            try:
                await self._core_v1_api.delete_namespaced_service(
                    name=service_name,
                    namespace=self.namespace
                )
                logger.info(f"Deleted Kubernetes service {service_name}")
            except ApiException as e:
                if e.status != 404:  # Ignore not found
                    logger.error(f"Failed to delete service {service_name}: {e}")
            
            # Delete Endpoints if using manual endpoints
            if self.use_endpoints:
                try:
                    await self._core_v1_api.delete_namespaced_endpoints(
                        name=service_name,
                        namespace=self.namespace
                    )
                    logger.info(f"Deleted Kubernetes endpoints for {service_name}")
                except ApiException as e:
                    if e.status != 404:  # Ignore not found
                        logger.error(f"Failed to delete endpoints {service_name}: {e}")
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_DEREGISTERED,
                service_name=service_name,
                metadata={"backend": "kubernetes", "instance_id": instance_id}
            ))
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to deregister service from Kubernetes: {e}")
            return False
    
    async def discover_services(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances from Kubernetes."""
        if not self._core_v1_api:
            return []
        
        try:
            instances = []
            
            # Get service information
            try:
                service = await self._core_v1_api.read_namespaced_service(
                    name=service_name,
                    namespace=self.namespace
                )
            except ApiException as e:
                if e.status == 404:
                    return []
                raise
            
            # Get endpoints
            try:
                endpoints = await self._core_v1_api.read_namespaced_endpoints(
                    name=service_name,
                    namespace=self.namespace
                )
                
                # Process endpoints
                for subset in endpoints.subsets or []:
                    for address in subset.addresses or []:
                        # Find the port
                        port = None
                        for endpoint_port in subset.ports or []:
                            if endpoint_port.name == self.service_port_name:
                                port = endpoint_port.port
                                break
                        
                        if port is None and subset.ports:
                            port = subset.ports[0].port
                        
                        if port is None:
                            continue
                        
                        # Create service instance
                        instance_id = f"{service_name}-{address.ip}-{port}"
                        if address.target_ref and address.target_ref.name:
                            instance_id = address.target_ref.name
                        
                        # Determine health status (simplified)
                        status = ServiceStatus.HEALTHY  # Assume healthy if in endpoints
                        
                        # Extract metadata from service annotations
                        metadata = {}
                        if service.metadata.annotations:
                            metadata.update(service.metadata.annotations)
                        
                        # Extract tags from service labels
                        service_tags = set()
                        if service.metadata.labels:
                            service_tags.update(service.metadata.labels.keys())
                        
                        # Filter by tags if specified
                        if tags and not tags.issubset(service_tags):
                            continue
                        
                        instance = ServiceInstance(
                            service_name=service_name,
                            instance_id=instance_id,
                            address=address.ip,
                            port=port,
                            status=status,
                            metadata=metadata,
                            tags=service_tags,
                            health_check_url=self.health_check_path
                        )
                        
                        instances.append(instance)
            
            except ApiException as e:
                if e.status != 404:  # Ignore not found endpoints
                    logger.error(f"Failed to get endpoints for service {service_name}: {e}")
            
            logger.debug(f"Discovered {len(instances)} instances for service {service_name}")
            return instances
        
        except Exception as e:
            logger.error(f"Failed to discover services from Kubernetes: {e}")
            return []
    
    async def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services from Kubernetes."""
        if not self._core_v1_api:
            return {}
        
        try:
            # Get all services in namespace
            services_list = await self._core_v1_api.list_namespaced_service(
                namespace=self.namespace,
                label_selector=self.label_selector,
                field_selector=self.field_selector
            )
            
            all_services = {}
            for service in services_list.items:
                service_name = service.metadata.name
                instances = await self.discover_services(service_name)
                if instances:
                    all_services[service_name] = instances
            
            return all_services
        
        except Exception as e:
            logger.error(f"Failed to get all services from Kubernetes: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if Kubernetes API is healthy."""
        if not self._core_v1_api:
            return False
        
        try:
            await self._core_v1_api.get_api_resources()
            return True
        except Exception:
            return False
    
    async def update_service_health(self, service_name: str, instance_id: str, status: ServiceStatus) -> bool:
        """Update service health status in Kubernetes (via annotations)."""
        if not self._core_v1_api:
            return False
        
        try:
            # Update service annotations with health status
            patch_body = {
                "metadata": {
                    "annotations": {
                        f"health.fastapi-microservices-sdk/{instance_id}": status.value,
                        f"health.fastapi-microservices-sdk/{instance_id}.timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
            
            await self._core_v1_api.patch_namespaced_service(
                name=service_name,
                namespace=self.namespace,
                body=patch_body
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update service health in Kubernetes: {e}")
            return False
    
    async def watch_services(self, service_name: Optional[str] = None) -> None:
        """Watch for service changes in Kubernetes."""
        if not self._core_v1_api:
            return
        
        if service_name:
            if service_name not in self._watch_tasks:
                task = asyncio.create_task(self._watch_service(service_name))
                self._watch_tasks[service_name] = task
        else:
            # Watch all services
            task = asyncio.create_task(self._watch_all_services())
            self._watch_tasks["_all"] = task
    
    async def _watch_service(self, service_name: str) -> None:
        """Watch a specific service for changes."""
        if not self._core_v1_api:
            return
        
        try:
            w = watch.Watch()
            
            async for event in w.stream(
                self._core_v1_api.list_namespaced_service,
                namespace=self.namespace,
                field_selector=f"metadata.name={service_name}"
            ):
                event_type_map = {
                    "ADDED": DiscoveryEventType.SERVICE_REGISTERED,
                    "DELETED": DiscoveryEventType.SERVICE_DEREGISTERED,
                    "MODIFIED": DiscoveryEventType.SERVICE_UPDATED
                }
                
                event_type = event_type_map.get(event["type"], DiscoveryEventType.SERVICE_UPDATED)
                
                await self._emit_event(DiscoveryEvent(
                    event_type=event_type,
                    service_name=service_name,
                    metadata={
                        "backend": "kubernetes",
                        "event_type": event["type"],
                        "namespace": self.namespace
                    }
                ))
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error watching service {service_name}: {e}")
    
    async def _watch_all_services(self) -> None:
        """Watch all services for changes."""
        if not self._core_v1_api:
            return
        
        try:
            w = watch.Watch()
            
            async for event in w.stream(
                self._core_v1_api.list_namespaced_service,
                namespace=self.namespace,
                label_selector=self.label_selector,
                field_selector=self.field_selector
            ):
                service = event["object"]
                service_name = service.metadata.name
                
                event_type_map = {
                    "ADDED": DiscoveryEventType.SERVICE_REGISTERED,
                    "DELETED": DiscoveryEventType.SERVICE_DEREGISTERED,
                    "MODIFIED": DiscoveryEventType.SERVICE_UPDATED
                }
                
                event_type = event_type_map.get(event["type"], DiscoveryEventType.SERVICE_UPDATED)
                
                await self._emit_event(DiscoveryEvent(
                    event_type=event_type,
                    service_name=service_name,
                    metadata={
                        "backend": "kubernetes",
                        "event_type": event["type"],
                        "namespace": self.namespace
                    }
                ))
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error watching all services: {e}")
    
    # Kubernetes-specific methods
    
    async def get_namespace_info(self) -> Dict[str, Any]:
        """Get namespace information."""
        if not self._core_v1_api:
            return {}
        
        try:
            namespace = await self._core_v1_api.read_namespace(name=self.namespace)
            
            return {
                "name": namespace.metadata.name,
                "labels": namespace.metadata.labels or {},
                "annotations": namespace.metadata.annotations or {},
                "status": namespace.status.phase if namespace.status else "Unknown",
                "created": namespace.metadata.creation_timestamp.isoformat() if namespace.metadata.creation_timestamp else None
            }
        
        except Exception as e:
            logger.error(f"Failed to get namespace info: {e}")
            return {}
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get Kubernetes cluster information."""
        if not self._core_v1_api:
            return {}
        
        try:
            # Get nodes
            nodes = await self._core_v1_api.list_node()
            
            # Get cluster version
            version_info = await self._api_client.call_api(
                "/version", "GET", response_type="object"
            )
            
            return {
                "version": version_info[0] if version_info else {},
                "nodes": [
                    {
                        "name": node.metadata.name,
                        "status": "Ready" if any(
                            condition.type == "Ready" and condition.status == "True"
                            for condition in node.status.conditions or []
                        ) else "NotReady",
                        "roles": list(node.metadata.labels.keys()) if node.metadata.labels else [],
                        "version": node.status.node_info.kubelet_version if node.status and node.status.node_info else None
                    }
                    for node in nodes.items
                ],
                "node_count": len(nodes.items)
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster info: {e}")
            return {}
    
    async def get_pod_info(self, service_name: str) -> List[Dict[str, Any]]:
        """Get pod information for a service."""
        if not self._core_v1_api:
            return []
        
        try:
            pods = await self._core_v1_api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"app={service_name}"
            )
            
            pod_info = []
            for pod in pods.items:
                pod_info.append({
                    "name": pod.metadata.name,
                    "status": pod.status.phase if pod.status else "Unknown",
                    "ready": all(
                        condition.status == "True"
                        for condition in pod.status.conditions or []
                        if condition.type == "Ready"
                    ),
                    "restarts": sum(
                        container_status.restart_count or 0
                        for container_status in pod.status.container_statuses or []
                    ),
                    "node": pod.spec.node_name if pod.spec else None,
                    "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                })
            
            return pod_info
        
        except Exception as e:
            logger.error(f"Failed to get pod info for service {service_name}: {e}")
            return []
    
    # Cross-Cluster Service Discovery
    
    async def setup_cross_cluster_clients(self) -> None:
        """Setup clients for cross-cluster service discovery."""
        if not self.cross_cluster or not self.cluster_configs:
            return
        
        for cluster_config in self.cluster_configs:
            cluster_name = cluster_config.get("name")
            if not cluster_name:
                continue
            
            try:
                # Load cluster-specific config
                if cluster_config.get("kubeconfig_path"):
                    await config.load_kube_config(config_file=cluster_config["kubeconfig_path"])
                else:
                    await config.load_kube_config()
                
                # Create cluster-specific clients
                api_client = client.ApiClient()
                cluster_clients = {
                    "api_client": api_client,
                    "core_v1": client.CoreV1Api(api_client),
                    "apps_v1": client.AppsV1Api(api_client),
                    "networking_v1": client.NetworkingV1Api(api_client)
                }
                
                self._cluster_clients[cluster_name] = cluster_clients
                logger.info(f"Setup cross-cluster client for: {cluster_name}")
                
            except Exception as e:
                logger.error(f"Failed to setup cross-cluster client for {cluster_name}: {e}")
    
    async def discover_services_cross_cluster(self, service_name: str) -> Dict[str, List[ServiceInstance]]:
        """Discover services across multiple clusters."""
        if not self.cross_cluster:
            return {}
        
        cluster_services = {}
        
        # Discover from local cluster
        local_instances = await self.discover_services(service_name)
        if local_instances:
            cluster_services["local"] = local_instances
        
        # Discover from remote clusters
        for cluster_name, cluster_clients in self._cluster_clients.items():
            try:
                core_v1 = cluster_clients["core_v1"]
                
                # Get services from remote cluster
                services_list = await core_v1.list_namespaced_service(
                    namespace=self.namespace,
                    field_selector=f"metadata.name={service_name}"
                )
                
                instances = []
                for service in services_list.items:
                    # Get endpoints for the service
                    try:
                        endpoints = await core_v1.read_namespaced_endpoints(
                            name=service_name,
                            namespace=self.namespace
                        )
                        
                        for subset in endpoints.subsets or []:
                            for address in subset.addresses or []:
                                port = None
                                for endpoint_port in subset.ports or []:
                                    if endpoint_port.name == self.service_port_name:
                                        port = endpoint_port.port
                                        break
                                
                                if port is None and subset.ports:
                                    port = subset.ports[0].port
                                
                                if port:
                                    instance = ServiceInstance(
                                        service_name=service_name,
                                        instance_id=f"{cluster_name}-{address.ip}-{port}",
                                        address=address.ip,
                                        port=port,
                                        status=ServiceStatus.HEALTHY,
                                        metadata={
                                            "cluster": cluster_name,
                                            "namespace": self.namespace
                                        },
                                        tags={f"cluster:{cluster_name}"}
                                    )
                                    instances.append(instance)
                    
                    except ApiException as e:
                        if e.status != 404:
                            logger.error(f"Failed to get endpoints for {service_name} in {cluster_name}: {e}")
                
                if instances:
                    cluster_services[cluster_name] = instances
                
            except Exception as e:
                logger.error(f"Failed to discover services in cluster {cluster_name}: {e}")
        
        return cluster_services
    
    # RBAC Integration
    
    async def check_rbac_permissions(self, resource: str, verb: str, namespace: Optional[str] = None) -> bool:
        """Check RBAC permissions for a specific resource and verb."""
        if not self.enable_rbac or not self._rbac_v1_api:
            return True  # Assume allowed if RBAC is disabled
        
        try:
            # Create SelfSubjectAccessReview
            access_review = client.V1SelfSubjectAccessReview(
                spec=client.V1SelfSubjectAccessReviewSpec(
                    resource_attributes=client.V1ResourceAttributes(
                        namespace=namespace or self.namespace,
                        verb=verb,
                        resource=resource
                    )
                )
            )
            
            # Check access
            result = await self._rbac_v1_api.create_self_subject_access_review(access_review)
            return result.status.allowed if result.status else False
        
        except Exception as e:
            logger.error(f"Failed to check RBAC permissions: {e}")
            return False
    
    async def get_service_account_info(self) -> Dict[str, Any]:
        """Get current service account information."""
        try:
            # Read service account token
            token_path = self.service_account_token_path
            if os.path.exists(token_path):
                with open(token_path, 'r') as f:
                    token = f.read().strip()
                
                # Decode token to get service account info (simplified)
                import base64
                try:
                    # JWT tokens have 3 parts separated by dots
                    parts = token.split('.')
                    if len(parts) >= 2:
                        # Decode payload (add padding if needed)
                        payload = parts[1]
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = base64.b64decode(payload)
                        token_info = json.loads(decoded.decode('utf-8'))
                        
                        return {
                            "service_account": token_info.get("kubernetes.io/serviceaccount/service-account.name"),
                            "namespace": token_info.get("kubernetes.io/serviceaccount/namespace"),
                            "token_expires": token_info.get("exp")
                        }
                except Exception:
                    pass
            
            return {"error": "Could not read service account information"}
        
        except Exception as e:
            logger.error(f"Failed to get service account info: {e}")
            return {"error": str(e)}
    
    # Service Mesh Integration
    
    async def get_service_mesh_config(self, service_name: str) -> Dict[str, Any]:
        """Get service mesh configuration for a service."""
        if not self.enable_service_mesh:
            return {}
        
        try:
            if self.service_mesh_type == "istio":
                return await self._get_istio_config(service_name)
            elif self.service_mesh_type == "linkerd":
                return await self._get_linkerd_config(service_name)
            elif self.service_mesh_type == "consul-connect":
                return await self._get_consul_connect_config(service_name)
            else:
                return {}
        
        except Exception as e:
            logger.error(f"Failed to get service mesh config: {e}")
            return {}
    
    async def _get_istio_config(self, service_name: str) -> Dict[str, Any]:
        """Get Istio-specific configuration."""
        try:
            # Get VirtualService
            custom_api = client.CustomObjectsApi(self._api_client)
            
            virtual_services = await custom_api.list_namespaced_custom_object(
                group="networking.istio.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="virtualservices",
                field_selector=f"metadata.name={service_name}"
            )
            
            destination_rules = await custom_api.list_namespaced_custom_object(
                group="networking.istio.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="destinationrules",
                field_selector=f"metadata.name={service_name}"
            )
            
            return {
                "type": "istio",
                "virtual_services": virtual_services.get("items", []),
                "destination_rules": destination_rules.get("items", [])
            }
        
        except Exception as e:
            logger.error(f"Failed to get Istio config: {e}")
            return {}
    
    async def _get_linkerd_config(self, service_name: str) -> Dict[str, Any]:
        """Get Linkerd-specific configuration."""
        try:
            # Get ServiceProfile
            custom_api = client.CustomObjectsApi(self._api_client)
            
            service_profiles = await custom_api.list_namespaced_custom_object(
                group="linkerd.io",
                version="v1alpha2",
                namespace=self.namespace,
                plural="serviceprofiles",
                field_selector=f"metadata.name={service_name}"
            )
            
            return {
                "type": "linkerd",
                "service_profiles": service_profiles.get("items", [])
            }
        
        except Exception as e:
            logger.error(f"Failed to get Linkerd config: {e}")
            return {}
    
    async def _get_consul_connect_config(self, service_name: str) -> Dict[str, Any]:
        """Get Consul Connect-specific configuration."""
        try:
            # Get ServiceDefaults and ServiceIntentions
            custom_api = client.CustomObjectsApi(self._api_client)
            
            service_defaults = await custom_api.list_namespaced_custom_object(
                group="consul.hashicorp.com",
                version="v1alpha1",
                namespace=self.namespace,
                plural="servicedefaults",
                field_selector=f"metadata.name={service_name}"
            )
            
            service_intentions = await custom_api.list_namespaced_custom_object(
                group="consul.hashicorp.com",
                version="v1alpha1",
                namespace=self.namespace,
                plural="serviceintentions"
            )
            
            return {
                "type": "consul-connect",
                "service_defaults": service_defaults.get("items", []),
                "service_intentions": service_intentions.get("items", [])
            }
        
        except Exception as e:
            logger.error(f"Failed to get Consul Connect config: {e}")
            return {}
    
    # DNS-Based Service Discovery
    
    async def discover_services_via_dns(self, service_name: str) -> List[ServiceInstance]:
        """Discover services using DNS resolution."""
        if not self.enable_dns_discovery:
            return []
        
        try:
            import socket
            
            # Construct DNS name
            dns_name = f"{service_name}.{self.namespace}.svc.{self.dns_suffix}"
            
            # Resolve DNS
            try:
                addresses = socket.getaddrinfo(dns_name, None)
                instances = []
                
                for addr_info in addresses:
                    ip = addr_info[4][0]
                    
                    # Try to get port from service
                    try:
                        service = await self._core_v1_api.read_namespaced_service(
                            name=service_name,
                            namespace=self.namespace
                        )
                        
                        port = 80  # Default
                        if service.spec.ports:
                            for service_port in service.spec.ports:
                                if service_port.name == self.service_port_name:
                                    port = service_port.port
                                    break
                            else:
                                port = service.spec.ports[0].port
                        
                        instance = ServiceInstance(
                            service_name=service_name,
                            instance_id=f"dns-{ip}-{port}",
                            address=ip,
                            port=port,
                            status=ServiceStatus.HEALTHY,
                            metadata={
                                "discovery_method": "dns",
                                "dns_name": dns_name
                            },
                            tags={"dns"}
                        )
                        instances.append(instance)
                    
                    except Exception as e:
                        logger.error(f"Failed to get service info for DNS discovery: {e}")
                
                return instances
            
            except socket.gaierror:
                logger.debug(f"DNS resolution failed for {dns_name}")
                return []
        
        except Exception as e:
            logger.error(f"Failed DNS-based service discovery: {e}")
            return []
    
    # Event Watching
    
    async def start_event_watching(self) -> None:
        """Start watching Kubernetes events."""
        if self.enable_event_watching and not self._event_watch_task:
            self._event_watch_task = asyncio.create_task(self._event_watch_loop())
    
    async def stop_event_watching(self) -> None:
        """Stop watching Kubernetes events."""
        if self._event_watch_task and not self._event_watch_task.done():
            self._event_watch_task.cancel()
            try:
                await self._event_watch_task
            except asyncio.CancelledError:
                pass
    
    async def _event_watch_loop(self) -> None:
        """Watch Kubernetes events and emit relevant discovery events."""
        if not self._core_v1_api:
            return
        
        try:
            w = watch.Watch()
            
            async for event in w.stream(
                self._core_v1_api.list_namespaced_event,
                namespace=self.namespace
            ):
                try:
                    k8s_event = event["object"]
                    event_type = event["type"]
                    
                    # Filter for service-related events
                    if (k8s_event.involved_object and 
                        k8s_event.involved_object.kind in ["Service", "Endpoints", "Pod"]):
                        
                        await self._emit_event(DiscoveryEvent(
                            event_type=DiscoveryEventType.SERVICE_UPDATED,
                            service_name=k8s_event.involved_object.name,
                            metadata={
                                "backend": "kubernetes",
                                "k8s_event_type": event_type,
                                "k8s_object_kind": k8s_event.involved_object.kind,
                                "reason": k8s_event.reason,
                                "message": k8s_event.message
                            }
                        ))
                
                except Exception as e:
                    logger.error(f"Error processing Kubernetes event: {e}")
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in event watch loop: {e}")
    
    # Advanced Monitoring
    
    async def get_cluster_resources(self) -> Dict[str, Any]:
        """Get cluster resource information."""
        try:
            # Get nodes
            nodes = await self._core_v1_api.list_node()
            
            # Get namespaces
            namespaces = await self._core_v1_api.list_namespace()
            
            # Get persistent volumes
            pvs = await self._core_v1_api.list_persistent_volume()
            
            return {
                "nodes": {
                    "total": len(nodes.items),
                    "ready": sum(1 for node in nodes.items if self._is_node_ready(node))
                },
                "namespaces": {
                    "total": len(namespaces.items),
                    "active": sum(1 for ns in namespaces.items if ns.status.phase == "Active")
                },
                "persistent_volumes": {
                    "total": len(pvs.items),
                    "available": sum(1 for pv in pvs.items if pv.status.phase == "Available")
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster resources: {e}")
            return {}
    
    def _is_node_ready(self, node) -> bool:
        """Check if a node is ready."""
        if not node.status or not node.status.conditions:
            return False
        
        for condition in node.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        
        return False
    
    async def get_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Get service dependencies and relationships."""
        try:
            dependencies = {
                "ingress": [],
                "network_policies": [],
                "config_maps": [],
                "secrets": [],
                "persistent_volume_claims": []
            }
            
            # Get Ingress resources
            if self._networking_v1_api:
                ingresses = await self._networking_v1_api.list_namespaced_ingress(
                    namespace=self.namespace
                )
                
                for ingress in ingresses.items:
                    if ingress.spec.rules:
                        for rule in ingress.spec.rules:
                            if rule.http and rule.http.paths:
                                for path in rule.http.paths:
                                    if (path.backend.service and 
                                        path.backend.service.name == service_name):
                                        dependencies["ingress"].append({
                                            "name": ingress.metadata.name,
                                            "host": rule.host,
                                            "path": path.path
                                        })
            
            # Get NetworkPolicies
            network_policies = await self._networking_v1_api.list_namespaced_network_policy(
                namespace=self.namespace
            )
            
            for policy in network_policies.items:
                # Check if policy affects this service
                if (policy.spec.pod_selector and 
                    policy.spec.pod_selector.match_labels and
                    policy.spec.pod_selector.match_labels.get("app") == service_name):
                    dependencies["network_policies"].append({
                        "name": policy.metadata.name,
                        "policy_types": policy.spec.policy_types or []
                    })
            
            # Get ConfigMaps and Secrets used by pods
            pods = await self._core_v1_api.list_namespaced_pod(
                namespace=self.namespace,
                label_selector=f"app={service_name}"
            )
            
            config_maps = set()
            secrets = set()
            pvcs = set()
            
            for pod in pods.items:
                if pod.spec.volumes:
                    for volume in pod.spec.volumes:
                        if volume.config_map:
                            config_maps.add(volume.config_map.name)
                        elif volume.secret:
                            secrets.add(volume.secret.secret_name)
                        elif volume.persistent_volume_claim:
                            pvcs.add(volume.persistent_volume_claim.claim_name)
            
            dependencies["config_maps"] = list(config_maps)
            dependencies["secrets"] = list(secrets)
            dependencies["persistent_volume_claims"] = list(pvcs)
            
            return dependencies
        
        except Exception as e:
            logger.error(f"Failed to get service dependencies: {e}")
            return {}
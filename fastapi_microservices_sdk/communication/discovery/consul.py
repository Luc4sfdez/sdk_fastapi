"""
Enhanced Consul service discovery implementation.

This module provides comprehensive Consul integration for service discovery with 
advanced health checks, KV store support, ACL integration, and cluster monitoring.
"""

import asyncio
import json
import logging
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Union
from urllib.parse import urljoin

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base import (
    ServiceDiscoveryBackend,
    ServiceInstance,
    ServiceStatus,
    DiscoveryEvent,
    DiscoveryEventType
)


logger = logging.getLogger(__name__)


class ConsulServiceDiscovery(ServiceDiscoveryBackend):
    """Enhanced Consul service discovery backend implementation with advanced features."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8500,
        scheme: str = "http",
        token: Optional[str] = None,
        datacenter: Optional[str] = None,
        timeout: float = 10.0,
        # ACL settings
        acl_enabled: bool = False,
        acl_default_policy: str = "allow",
        # Health check settings
        check_interval: str = "30s",
        check_timeout: str = "10s",
        deregister_critical_after: str = "5m",
        # KV store settings
        kv_prefix: str = "config/",
        # Monitoring settings
        enable_cluster_monitoring: bool = True,
        leader_election_key: Optional[str] = None,
        **kwargs
    ):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp package is required for Consul service discovery")
        
        super().__init__("consul", {
            "host": host,
            "port": port,
            "scheme": scheme,
            "token": token,
            "datacenter": datacenter,
            "timeout": timeout,
            "acl_enabled": acl_enabled,
            "acl_default_policy": acl_default_policy,
            "check_interval": check_interval,
            "check_timeout": check_timeout,
            "deregister_critical_after": deregister_critical_after,
            "kv_prefix": kv_prefix,
            "enable_cluster_monitoring": enable_cluster_monitoring,
            "leader_election_key": leader_election_key,
            **kwargs
        })
        
        self.host = host
        self.port = port
        self.scheme = scheme
        self.token = token
        self.datacenter = datacenter
        self.timeout = timeout
        
        # ACL settings
        self.acl_enabled = acl_enabled
        self.acl_default_policy = acl_default_policy
        
        # Health check settings
        self.check_interval = check_interval
        self.check_timeout = check_timeout
        self.deregister_critical_after = deregister_critical_after
        
        # KV store settings
        self.kv_prefix = kv_prefix
        
        # Monitoring settings
        self.enable_cluster_monitoring = enable_cluster_monitoring
        self.leader_election_key = leader_election_key
        
        self.base_url = f"{scheme}://{host}:{port}"
        self._session: Optional["aiohttp.ClientSession"] = None
        self._watch_tasks: Dict[str, asyncio.Task] = {}
        self._cluster_monitor_task: Optional[asyncio.Task] = None
        
        # Cluster state
        self._cluster_info: Dict[str, Any] = {}
        self._is_leader: bool = False
        self._leader_session: Optional[str] = None
    
    async def _get_session(self) -> "aiohttp.ClientSession":
        """Get or create HTTP session with Consul configuration."""
        if self._session is None or self._session.closed:
            headers = {}
            if self.token:
                headers["X-Consul-Token"] = self.token
            
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout
            )
        
        return self._session
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Consul API."""
        url = urljoin(self.base_url, endpoint)
        
        # Add datacenter to params if specified
        if params is None:
            params = {}
        if self.datacenter:
            params["dc"] = self.datacenter
        
        session = await self._get_session()
        
        try:
            async with session.request(method, url, params=params, json=json_data) as response:
                if response.status == 404:
                    return {}
                
                response.raise_for_status()
                
                if response.content_type == 'application/json':
                    return await response.json()
                else:
                    return {"data": await response.text()}
        
        except aiohttp.ClientError as e:
            logger.error(f"Consul API request failed: {e}")
            raise
    
    async def connect(self) -> None:
        """Connect to Consul and verify connectivity."""
        try:
            # Test connection by getting Consul status
            await self._make_request("GET", "/v1/status/leader")
            self.is_connected = True
            
            # Start cluster monitoring if enabled
            await self.start_cluster_monitoring()
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.BACKEND_CONNECTED,
                service_name="consul",
                metadata={
                    "backend": "consul", 
                    "host": self.host, 
                    "port": self.port,
                    "acl_enabled": self.acl_enabled,
                    "cluster_monitoring": self.enable_cluster_monitoring
                }
            ))
            
            logger.info(f"Connected to Consul at {self.base_url}")
            if self.acl_enabled:
                logger.info("ACL is enabled")
            if self.enable_cluster_monitoring:
                logger.info("Cluster monitoring started")
        
        except Exception as e:
            self.is_connected = False
            logger.error(f"Failed to connect to Consul: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from Consul."""
        # Release leadership if we have it
        if self._is_leader:
            await self.release_leadership()
        
        # Stop cluster monitoring
        await self.stop_cluster_monitoring()
        
        # Cancel all watch tasks
        for task in self._watch_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._watch_tasks:
            await asyncio.gather(*self._watch_tasks.values(), return_exceptions=True)
        
        self._watch_tasks.clear()
        
        # Close HTTP session
        if self._session and not self._session.closed:
            await self._session.close()
        
        self.is_connected = False
        
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.BACKEND_DISCONNECTED,
            service_name="consul",
            metadata={"backend": "consul"}
        ))
        
        logger.info("Disconnected from Consul")
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance with Consul."""
        try:
            # Build service registration payload
            service_data = {
                "ID": instance.instance_id,
                "Name": instance.service_name,
                "Address": instance.address,
                "Port": instance.port,
                "Tags": list(instance.tags),
                "Meta": instance.metadata
            }
            
            # Add health check if URL is provided
            if instance.health_check_url:
                health_check_url = instance.health_check_url
                if not health_check_url.startswith(('http://', 'https://')):
                    health_check_url = f"http://{instance.address}:{instance.port}{health_check_url}"
                
                service_data["Check"] = {
                    "HTTP": health_check_url,
                    "Interval": self.check_interval,
                    "Timeout": self.check_timeout,
                    "DeregisterCriticalServiceAfter": self.deregister_critical_after
                }
            
            # Register service
            await self._make_request(
                "PUT",
                f"/v1/agent/service/register",
                json_data=service_data
            )
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_REGISTERED,
                service_name=instance.service_name,
                instance=instance,
                metadata={"backend": "consul"}
            ))
            
            logger.info(f"Registered service {instance.service_name}/{instance.instance_id} with Consul")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service with Consul: {e}")
            return False
    
    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance from Consul."""
        try:
            await self._make_request(
                "PUT",
                f"/v1/agent/service/deregister/{instance_id}"
            )
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_DEREGISTERED,
                service_name=service_name,
                metadata={"backend": "consul", "instance_id": instance_id}
            ))
            
            logger.info(f"Deregistered service {service_name}/{instance_id} from Consul")
            return True
        
        except Exception as e:
            logger.error(f"Failed to deregister service from Consul: {e}")
            return False
    
    async def discover_services(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances from Consul."""
        try:
            params = {"passing": "true"}  # Only return healthy services
            if tags:
                params["tag"] = list(tags)
            
            response = await self._make_request(
                "GET",
                f"/v1/health/service/{service_name}",
                params=params
            )
            
            instances = []
            for service_data in response:
                service_info = service_data.get("Service", {})
                health_info = service_data.get("Checks", [])
                
                # Determine health status
                status = ServiceStatus.HEALTHY
                for check in health_info:
                    if check.get("Status") == "critical":
                        status = ServiceStatus.CRITICAL
                        break
                    elif check.get("Status") == "warning":
                        status = ServiceStatus.UNHEALTHY
                
                # Create service instance
                instance = ServiceInstance(
                    service_name=service_info.get("Service", service_name),
                    instance_id=service_info.get("ID", ""),
                    address=service_info.get("Address", ""),
                    port=service_info.get("Port", 0),
                    status=status,
                    metadata=service_info.get("Meta", {}),
                    tags=set(service_info.get("Tags", [])),
                    health_check_url=None  # Consul manages health checks
                )
                
                instances.append(instance)
            
            logger.debug(f"Discovered {len(instances)} instances for service {service_name}")
            return instances
        
        except Exception as e:
            logger.error(f"Failed to discover services from Consul: {e}")
            return []
    
    async def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services from Consul."""
        try:
            # Get list of all services
            services_response = await self._make_request("GET", "/v1/catalog/services")
            
            all_services = {}
            for service_name in services_response.keys():
                instances = await self.discover_services(service_name)
                if instances:
                    all_services[service_name] = instances
            
            return all_services
        
        except Exception as e:
            logger.error(f"Failed to get all services from Consul: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if Consul is healthy."""
        try:
            await self._make_request("GET", "/v1/status/leader")
            return True
        except Exception:
            return False
    
    async def update_service_health(self, service_name: str, instance_id: str, status: ServiceStatus) -> bool:
        """Update service health status in Consul."""
        try:
            # Consul manages health checks automatically, but we can force a check
            if status == ServiceStatus.CRITICAL:
                # Force service to critical state
                await self._make_request(
                    "PUT",
                    f"/v1/agent/check/fail/service:{instance_id}"
                )
            elif status == ServiceStatus.HEALTHY:
                # Force service to passing state
                await self._make_request(
                    "PUT",
                    f"/v1/agent/check/pass/service:{instance_id}"
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update service health in Consul: {e}")
            return False
    
    async def watch_services(self, service_name: Optional[str] = None) -> None:
        """Watch for service changes in Consul."""
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
        index = 0
        
        while self.is_connected:
            try:
                params = {
                    "index": index,
                    "wait": "30s"  # Long polling
                }
                
                response = await self._make_request(
                    "GET",
                    f"/v1/health/service/{service_name}",
                    params=params
                )
                
                # Check if there are changes (simplified)
                if response:
                    await self._emit_event(DiscoveryEvent(
                        event_type=DiscoveryEventType.SERVICE_UPDATED,
                        service_name=service_name,
                        metadata={"backend": "consul", "change_type": "service_updated"}
                    ))
                
                # Update index for next request
                # In a real implementation, you'd extract the X-Consul-Index header
                index += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error watching service {service_name}: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _watch_all_services(self) -> None:
        """Watch all services for changes."""
        index = 0
        
        while self.is_connected:
            try:
                params = {
                    "index": index,
                    "wait": "30s"
                }
                
                response = await self._make_request(
                    "GET",
                    "/v1/catalog/services",
                    params=params
                )
                
                if response:
                    await self._emit_event(DiscoveryEvent(
                        event_type=DiscoveryEventType.SERVICE_UPDATED,
                        service_name="*",
                        metadata={"backend": "consul", "change_type": "services_updated"}
                    ))
                
                index += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error watching all services: {e}")
                await asyncio.sleep(30)
    
    # Consul-specific methods
    
    async def get_kv_value(self, key: str) -> Optional[str]:
        """Get a value from Consul KV store."""
        try:
            response = await self._make_request("GET", f"/v1/kv/{key}")
            if response:
                # Consul returns base64 encoded values
                import base64
                encoded_value = response[0].get("Value", "")
                if encoded_value:
                    return base64.b64decode(encoded_value).decode('utf-8')
            return None
        
        except Exception as e:
            logger.error(f"Failed to get KV value from Consul: {e}")
            return None
    
    async def set_kv_value(self, key: str, value: str) -> bool:
        """Set a value in Consul KV store."""
        try:
            await self._make_request(
                "PUT",
                f"/v1/kv/{key}",
                json_data=value
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to set KV value in Consul: {e}")
            return False
    
    async def delete_kv_value(self, key: str) -> bool:
        """Delete a value from Consul KV store."""
        try:
            await self._make_request("DELETE", f"/v1/kv/{key}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete KV value from Consul: {e}")
            return False
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get Consul cluster information."""
        try:
            leader = await self._make_request("GET", "/v1/status/leader")
            peers = await self._make_request("GET", "/v1/status/peers")
            
            return {
                "leader": leader,
                "peers": peers,
                "peer_count": len(peers) if isinstance(peers, list) else 0
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster info from Consul: {e}")
            return {}
    
    async def get_datacenter_info(self) -> Dict[str, Any]:
        """Get datacenter information."""
        try:
            datacenters = await self._make_request("GET", "/v1/catalog/datacenters")
            return {
                "datacenters": datacenters,
                "current_datacenter": self.datacenter
            }
        
        except Exception as e:
            logger.error(f"Failed to get datacenter info from Consul: {e}")
            return {}
    
    # Enhanced KV Store Operations
    
    async def get_kv_keys(self, prefix: str = "") -> List[str]:
        """Get all keys with a given prefix from Consul KV store."""
        try:
            full_prefix = f"{self.kv_prefix}{prefix}"
            params = {"keys": "true"}
            response = await self._make_request("GET", f"/v1/kv/{full_prefix}", params=params)
            
            if isinstance(response, list):
                # Remove the kv_prefix from returned keys
                return [key.replace(self.kv_prefix, "", 1) for key in response]
            return []
        
        except Exception as e:
            logger.error(f"Failed to get KV keys from Consul: {e}")
            return []
    
    async def get_kv_recursive(self, prefix: str = "") -> Dict[str, str]:
        """Get all key-value pairs recursively from a prefix."""
        try:
            full_prefix = f"{self.kv_prefix}{prefix}"
            params = {"recurse": "true"}
            response = await self._make_request("GET", f"/v1/kv/{full_prefix}", params=params)
            
            result = {}
            if isinstance(response, list):
                for item in response:
                    key = item.get("Key", "").replace(self.kv_prefix, "", 1)
                    encoded_value = item.get("Value", "")
                    if encoded_value:
                        try:
                            value = base64.b64decode(encoded_value).decode('utf-8')
                            result[key] = value
                        except Exception:
                            result[key] = encoded_value
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to get KV recursive from Consul: {e}")
            return {}
    
    async def set_kv_json(self, key: str, value: Any) -> bool:
        """Set a JSON value in Consul KV store."""
        try:
            json_value = json.dumps(value)
            return await self.set_kv_value(key, json_value)
        
        except Exception as e:
            logger.error(f"Failed to set KV JSON value in Consul: {e}")
            return False
    
    async def get_kv_json(self, key: str) -> Optional[Any]:
        """Get a JSON value from Consul KV store."""
        try:
            value = await self.get_kv_value(key)
            if value:
                return json.loads(value)
            return None
        
        except Exception as e:
            logger.error(f"Failed to get KV JSON value from Consul: {e}")
            return None
    
    async def watch_kv_prefix(self, prefix: str, callback) -> None:
        """Watch for changes in KV store with a given prefix."""
        watch_key = f"kv_watch_{prefix}"
        if watch_key not in self._watch_tasks:
            task = asyncio.create_task(self._watch_kv_prefix(prefix, callback))
            self._watch_tasks[watch_key] = task
    
    async def _watch_kv_prefix(self, prefix: str, callback) -> None:
        """Internal method to watch KV prefix changes."""
        index = 0
        full_prefix = f"{self.kv_prefix}{prefix}"
        
        while self.is_connected:
            try:
                params = {
                    "index": index,
                    "wait": "30s",
                    "recurse": "true"
                }
                
                response = await self._make_request(
                    "GET",
                    f"/v1/kv/{full_prefix}",
                    params=params
                )
                
                if response:
                    # Process changes
                    changes = {}
                    if isinstance(response, list):
                        for item in response:
                            key = item.get("Key", "").replace(self.kv_prefix, "", 1)
                            encoded_value = item.get("Value", "")
                            if encoded_value:
                                try:
                                    value = base64.b64decode(encoded_value).decode('utf-8')
                                    changes[key] = value
                                except Exception:
                                    changes[key] = encoded_value
                    
                    # Call callback with changes
                    if asyncio.iscoroutinefunction(callback):
                        await callback(changes)
                    else:
                        callback(changes)
                
                index += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error watching KV prefix {prefix}: {e}")
                await asyncio.sleep(30)
    
    # ACL Operations
    
    async def create_acl_token(
        self,
        name: str,
        type_: str = "client",
        rules: Optional[str] = None
    ) -> Optional[str]:
        """Create an ACL token."""
        if not self.acl_enabled:
            logger.warning("ACL is not enabled")
            return None
        
        try:
            token_data = {
                "Name": name,
                "Type": type_
            }
            
            if rules:
                token_data["Rules"] = rules
            
            response = await self._make_request(
                "PUT",
                "/v1/acl/create",
                json_data=token_data
            )
            
            return response.get("ID") if response else None
        
        except Exception as e:
            logger.error(f"Failed to create ACL token: {e}")
            return None
    
    async def get_acl_token_info(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Get ACL token information."""
        if not self.acl_enabled:
            return None
        
        try:
            response = await self._make_request("GET", f"/v1/acl/info/{token_id}")
            return response[0] if response and isinstance(response, list) else None
        
        except Exception as e:
            logger.error(f"Failed to get ACL token info: {e}")
            return None
    
    async def destroy_acl_token(self, token_id: str) -> bool:
        """Destroy an ACL token."""
        if not self.acl_enabled:
            return False
        
        try:
            await self._make_request("PUT", f"/v1/acl/destroy/{token_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to destroy ACL token: {e}")
            return False
    
    # Leader Election
    
    async def acquire_leadership(self, session_ttl: int = 15) -> bool:
        """Acquire leadership using Consul sessions."""
        if not self.leader_election_key:
            logger.error("Leader election key not configured")
            return False
        
        try:
            # Create session
            session_data = {
                "Name": f"leader-election-{self.name}",
                "TTL": f"{session_ttl}s",
                "Behavior": "release"
            }
            
            session_response = await self._make_request(
                "PUT",
                "/v1/session/create",
                json_data=session_data
            )
            
            if not session_response or "ID" not in session_response:
                return False
            
            session_id = session_response["ID"]
            self._leader_session = session_id
            
            # Try to acquire lock
            lock_data = {"leader": self.name, "acquired_at": datetime.now(timezone.utc).isoformat()}
            params = {"acquire": session_id}
            
            response = await self._make_request(
                "PUT",
                f"/v1/kv/{self.leader_election_key}",
                params=params,
                json_data=json.dumps(lock_data)
            )
            
            self._is_leader = response is True
            
            if self._is_leader:
                logger.info(f"Acquired leadership with session {session_id}")
                # Start session renewal
                asyncio.create_task(self._renew_leader_session())
            
            return self._is_leader
        
        except Exception as e:
            logger.error(f"Failed to acquire leadership: {e}")
            return False
    
    async def release_leadership(self) -> bool:
        """Release leadership."""
        if not self._leader_session or not self.leader_election_key:
            return False
        
        try:
            params = {"release": self._leader_session}
            await self._make_request(
                "PUT",
                f"/v1/kv/{self.leader_election_key}",
                params=params
            )
            
            # Destroy session
            await self._make_request("PUT", f"/v1/session/destroy/{self._leader_session}")
            
            self._is_leader = False
            self._leader_session = None
            
            logger.info("Released leadership")
            return True
        
        except Exception as e:
            logger.error(f"Failed to release leadership: {e}")
            return False
    
    async def _renew_leader_session(self) -> None:
        """Renew leader session to maintain leadership."""
        while self._is_leader and self._leader_session:
            try:
                await asyncio.sleep(5)  # Renew every 5 seconds
                
                response = await self._make_request(
                    "PUT",
                    f"/v1/session/renew/{self._leader_session}"
                )
                
                if not response:
                    logger.warning("Failed to renew leader session, losing leadership")
                    self._is_leader = False
                    self._leader_session = None
                    break
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error renewing leader session: {e}")
                await asyncio.sleep(5)
    
    @property
    def is_leader(self) -> bool:
        """Check if this instance is the current leader."""
        return self._is_leader
    
    # Cluster Monitoring
    
    async def start_cluster_monitoring(self) -> None:
        """Start cluster monitoring task."""
        if self.enable_cluster_monitoring and not self._cluster_monitor_task:
            self._cluster_monitor_task = asyncio.create_task(self._cluster_monitor_loop())
    
    async def stop_cluster_monitoring(self) -> None:
        """Stop cluster monitoring task."""
        if self._cluster_monitor_task and not self._cluster_monitor_task.done():
            self._cluster_monitor_task.cancel()
            try:
                await self._cluster_monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _cluster_monitor_loop(self) -> None:
        """Monitor cluster health and leader changes."""
        while self.is_connected:
            try:
                # Get cluster info
                cluster_info = await self.get_cluster_info()
                
                # Check for leader changes
                current_leader = cluster_info.get("leader")
                previous_leader = self._cluster_info.get("leader")
                
                if current_leader != previous_leader:
                    await self._emit_event(DiscoveryEvent(
                        event_type=DiscoveryEventType.BACKEND_CONNECTED,  # Reuse for leader change
                        service_name="consul-cluster",
                        metadata={
                            "event": "leader_change",
                            "new_leader": current_leader,
                            "previous_leader": previous_leader
                        }
                    ))
                
                self._cluster_info = cluster_info
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cluster monitoring: {e}")
                await asyncio.sleep(30)
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get comprehensive cluster health information."""
        try:
            # Get basic cluster info
            cluster_info = await self.get_cluster_info()
            
            # Get node health
            nodes_response = await self._make_request("GET", "/v1/catalog/nodes")
            healthy_nodes = 0
            total_nodes = len(nodes_response) if nodes_response else 0
            
            for node in nodes_response or []:
                node_name = node.get("Node")
                if node_name:
                    # Check node health
                    health_response = await self._make_request(
                        "GET",
                        f"/v1/health/node/{node_name}"
                    )
                    
                    if health_response:
                        # Check if all checks are passing
                        all_passing = all(
                            check.get("Status") == "passing"
                            for check in health_response
                        )
                        if all_passing:
                            healthy_nodes += 1
            
            # Get service health summary
            services_response = await self._make_request("GET", "/v1/catalog/services")
            total_services = len(services_response) if services_response else 0
            
            return {
                "cluster_info": cluster_info,
                "nodes": {
                    "total": total_nodes,
                    "healthy": healthy_nodes,
                    "unhealthy": total_nodes - healthy_nodes
                },
                "services": {
                    "total": total_services
                },
                "is_leader": self._is_leader,
                "leader_session": self._leader_session,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Enhanced Service Operations
    
    async def register_service_with_checks(
        self,
        instance: ServiceInstance,
        checks: List[Dict[str, Any]]
    ) -> bool:
        """Register service with multiple health checks."""
        try:
            service_data = {
                "ID": instance.instance_id,
                "Name": instance.service_name,
                "Address": instance.address,
                "Port": instance.port,
                "Tags": list(instance.tags),
                "Meta": instance.metadata,
                "Checks": checks
            }
            
            await self._make_request(
                "PUT",
                "/v1/agent/service/register",
                json_data=service_data
            )
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_REGISTERED,
                service_name=instance.service_name,
                instance=instance,
                metadata={"backend": "consul", "checks_count": len(checks)}
            ))
            
            logger.info(f"Registered service {instance.service_name}/{instance.instance_id} with {len(checks)} checks")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service with checks: {e}")
            return False
    
    async def get_service_health_detailed(self, service_name: str) -> Dict[str, Any]:
        """Get detailed health information for a service."""
        try:
            response = await self._make_request(
                "GET",
                f"/v1/health/service/{service_name}"
            )
            
            detailed_health = {
                "service_name": service_name,
                "instances": [],
                "summary": {
                    "total": 0,
                    "passing": 0,
                    "warning": 0,
                    "critical": 0
                }
            }
            
            for service_data in response or []:
                service_info = service_data.get("Service", {})
                checks = service_data.get("Checks", [])
                
                # Analyze checks
                check_statuses = [check.get("Status") for check in checks]
                overall_status = "passing"
                
                if "critical" in check_statuses:
                    overall_status = "critical"
                elif "warning" in check_statuses:
                    overall_status = "warning"
                
                instance_health = {
                    "instance_id": service_info.get("ID"),
                    "address": service_info.get("Address"),
                    "port": service_info.get("Port"),
                    "status": overall_status,
                    "checks": [
                        {
                            "name": check.get("Name"),
                            "status": check.get("Status"),
                            "output": check.get("Output", "")[:200],  # Truncate output
                            "notes": check.get("Notes", "")
                        }
                        for check in checks
                    ]
                }
                
                detailed_health["instances"].append(instance_health)
                detailed_health["summary"]["total"] += 1
                detailed_health["summary"][overall_status] += 1
            
            return detailed_health
        
        except Exception as e:
            logger.error(f"Failed to get detailed service health: {e}")
            return {"error": str(e)}
    
    # Configuration Management Integration
    
    async def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service from KV store."""
        config_key = f"services/{service_name}"
        return await self.get_kv_json(config_key) or {}
    
    async def set_service_config(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Set configuration for a specific service in KV store."""
        config_key = f"services/{service_name}"
        return await self.set_kv_json(config_key, config)
    
    async def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration from KV store."""
        return await self.get_kv_recursive("global/")
    
    async def set_global_config_value(self, key: str, value: Any) -> bool:
        """Set a global configuration value."""
        config_key = f"global/{key}"
        if isinstance(value, (dict, list)):
            return await self.set_kv_json(config_key, value)
        else:
            return await self.set_kv_value(config_key, str(value))
"""
Enhanced etcd service discovery implementation.

This module provides comprehensive etcd integration for service discovery with 
advanced lease management, distributed locking, configuration management,
and cluster monitoring capabilities.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Union, Callable
from urllib.parse import quote

try:
    import etcd3
    from etcd3 import events
    ETCD3_AVAILABLE = True
except ImportError:
    ETCD3_AVAILABLE = False
    events = None

from .base import (
    ServiceDiscoveryBackend,
    ServiceInstance,
    ServiceStatus,
    DiscoveryEvent,
    DiscoveryEventType
)


logger = logging.getLogger(__name__)


class EtcdServiceDiscovery(ServiceDiscoveryBackend):
    """Enhanced etcd service discovery backend implementation with advanced features."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 2379,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ca_cert: Optional[str] = None,
        cert_key: Optional[str] = None,
        cert_cert: Optional[str] = None,
        timeout: float = 10.0,
        # Lease management
        lease_ttl: int = 30,
        lease_renewal_interval: int = 10,
        # Configuration management
        config_prefix: str = "/config/",
        # Distributed locking
        lock_prefix: str = "/locks/",
        lock_ttl: int = 60,
        # Cluster settings
        enable_cluster_monitoring: bool = True,
        # Service discovery settings
        service_prefix: str = "/services/",
        enable_service_versioning: bool = True,
        **kwargs
    ):
        if not ETCD3_AVAILABLE:
            raise ImportError("etcd3 package is required for etcd service discovery")
        
        super().__init__("etcd", {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "ca_cert": ca_cert,
            "cert_key": cert_key,
            "cert_cert": cert_cert,
            "timeout": timeout,
            "lease_ttl": lease_ttl,
            "lease_renewal_interval": lease_renewal_interval,
            "config_prefix": config_prefix,
            "lock_prefix": lock_prefix,
            "lock_ttl": lock_ttl,
            "enable_cluster_monitoring": enable_cluster_monitoring,
            "service_prefix": service_prefix,
            "enable_service_versioning": enable_service_versioning,
            **kwargs
        })
        
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ca_cert = ca_cert
        self.cert_key = cert_key
        self.cert_cert = cert_cert
        self.timeout = timeout
        
        # Lease management
        self.lease_ttl = lease_ttl
        self.lease_renewal_interval = lease_renewal_interval
        
        # Configuration management
        self.config_prefix = config_prefix
        
        # Distributed locking
        self.lock_prefix = lock_prefix
        self.lock_ttl = lock_ttl
        
        # Cluster settings
        self.enable_cluster_monitoring = enable_cluster_monitoring
        
        # Service discovery settings
        self.service_prefix = service_prefix
        self.enable_service_versioning = enable_service_versioning
        
        self._client: Optional[etcd3.Etcd3Client] = None
        self._leases: Dict[str, int] = {}  # instance_id -> lease_id
        self._locks: Dict[str, etcd3.Lock] = {}  # lock_name -> lock
        self._watch_tasks: Dict[str, asyncio.Task] = {}
        self._lease_renewal_task: Optional[asyncio.Task] = None
        self._cluster_monitor_task: Optional[asyncio.Task] = None
        
        # Cluster state
        self._cluster_info: Dict[str, Any] = {}
        self._is_leader: bool = False
        self._leader_key: Optional[str] = None
    
    def _get_service_key(self, service_name: str, instance_id: str) -> str:
        """Generate etcd key for a service instance."""
        return f"{self.service_prefix}{service_name}/{instance_id}"
    
    def _get_service_prefix_key(self, service_name: str) -> str:
        """Generate etcd key prefix for a service."""
        return f"{self.service_prefix}{service_name}/"
    
    async def connect(self) -> None:
        """Connect to etcd cluster."""
        try:
            # Create etcd client
            self._client = etcd3.client(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                ca_cert=self.ca_cert,
                cert_key=self.cert_key,
                cert_cert=self.cert_cert,
                timeout=self.timeout
            )
            
            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.status
            )
            
            self.is_connected = True
            
            # Start lease renewal task
            self._lease_renewal_task = asyncio.create_task(self._lease_renewal_loop())
            
            # Start cluster monitoring if enabled
            await self.start_cluster_monitoring()
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.BACKEND_CONNECTED,
                service_name="etcd",
                metadata={
                    "backend": "etcd", 
                    "host": self.host, 
                    "port": self.port,
                    "cluster_monitoring": self.enable_cluster_monitoring,
                    "service_versioning": self.enable_service_versioning
                }
            ))
            
            logger.info(f"Connected to etcd at {self.host}:{self.port}")
            if self.enable_cluster_monitoring:
                logger.info("Cluster monitoring started")
            if self.enable_service_versioning:
                logger.info("Service versioning enabled")
        
        except Exception as e:
            self.is_connected = False
            logger.error(f"Failed to connect to etcd: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from etcd cluster."""
        # Release leadership if we have it
        if self._is_leader:
            await self.release_leadership()
        
        # Release all locks
        for lock_name in list(self._locks.keys()):
            await self.release_lock(lock_name)
        
        # Stop cluster monitoring
        await self.stop_cluster_monitoring()
        
        # Cancel lease renewal task
        if self._lease_renewal_task and not self._lease_renewal_task.done():
            self._lease_renewal_task.cancel()
            try:
                await self._lease_renewal_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all watch tasks
        for task in self._watch_tasks.values():
            if not task.done():
                task.cancel()
        
        if self._watch_tasks:
            await asyncio.gather(*self._watch_tasks.values(), return_exceptions=True)
        
        self._watch_tasks.clear()
        
        # Revoke all leases
        if self._client:
            for lease_id in self._leases.values():
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._client.revoke_lease, lease_id
                    )
                except Exception as e:
                    logger.error(f"Failed to revoke lease {lease_id}: {e}")
        
        self._leases.clear()
        
        # Close client
        if self._client:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._client.close
                )
            except Exception as e:
                logger.error(f"Error closing etcd client: {e}")
        
        self._client = None
        self.is_connected = False
        
        await self._emit_event(DiscoveryEvent(
            event_type=DiscoveryEventType.BACKEND_DISCONNECTED,
            service_name="etcd",
            metadata={"backend": "etcd"}
        ))
        
        logger.info("Disconnected from etcd")
    
    async def register_service(self, instance: ServiceInstance) -> bool:
        """Register a service instance with etcd."""
        if not self._client:
            return False
        
        try:
            # Create lease
            lease = await asyncio.get_event_loop().run_in_executor(
                None, self._client.lease, self.lease_ttl
            )
            
            # Store lease ID
            self._leases[instance.instance_id] = lease.id
            
            # Prepare service data
            service_data = {
                "service_name": instance.service_name,
                "instance_id": instance.instance_id,
                "address": instance.address,
                "port": instance.port,
                "status": instance.status.value,
                "metadata": instance.metadata,
                "tags": list(instance.tags),
                "health_check_url": instance.health_check_url,
                "registered_at": instance.registered_at.isoformat(),
                "updated_at": instance.updated_at.isoformat()
            }
            
            # Store service instance data
            key = self._get_service_key(instance.service_name, instance.instance_id)
            value = json.dumps(service_data)
            
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.put, key, value, lease
            )
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_REGISTERED,
                service_name=instance.service_name,
                instance=instance,
                metadata={"backend": "etcd", "lease_id": lease.id}
            ))
            
            logger.info(f"Registered service {instance.service_name}/{instance.instance_id} with etcd")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register service with etcd: {e}")
            return False
    
    async def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance from etcd."""
        if not self._client:
            return False
        
        try:
            # Delete service key
            key = self._get_service_key(service_name, instance_id)
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.delete, key
            )
            
            # Revoke lease if exists
            if instance_id in self._leases:
                lease_id = self._leases.pop(instance_id)
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._client.revoke_lease, lease_id
                    )
                except Exception as e:
                    logger.error(f"Failed to revoke lease {lease_id}: {e}")
            
            await self._emit_event(DiscoveryEvent(
                event_type=DiscoveryEventType.SERVICE_DEREGISTERED,
                service_name=service_name,
                metadata={"backend": "etcd", "instance_id": instance_id}
            ))
            
            logger.info(f"Deregistered service {service_name}/{instance_id} from etcd")
            return True
        
        except Exception as e:
            logger.error(f"Failed to deregister service from etcd: {e}")
            return False
    
    async def discover_services(self, service_name: str, tags: Optional[Set[str]] = None) -> List[ServiceInstance]:
        """Discover service instances from etcd."""
        if not self._client:
            return []
        
        try:
            # Get all instances for the service
            prefix = self._get_service_prefix_key(service_name)
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_prefix, prefix
            )
            
            instances = []
            for value, metadata in result:
                try:
                    service_data = json.loads(value.decode('utf-8'))
                    
                    # Create service instance
                    instance = ServiceInstance(
                        service_name=service_data["service_name"],
                        instance_id=service_data["instance_id"],
                        address=service_data["address"],
                        port=service_data["port"],
                        status=ServiceStatus(service_data.get("status", ServiceStatus.UNKNOWN.value)),
                        metadata=service_data.get("metadata", {}),
                        tags=set(service_data.get("tags", [])),
                        health_check_url=service_data.get("health_check_url")
                    )
                    
                    # Parse timestamps
                    if service_data.get("registered_at"):
                        instance.registered_at = datetime.fromisoformat(service_data["registered_at"])
                    if service_data.get("updated_at"):
                        instance.updated_at = datetime.fromisoformat(service_data["updated_at"])
                    
                    # Filter by tags if specified
                    if tags and not tags.issubset(instance.tags):
                        continue
                    
                    instances.append(instance)
                
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.error(f"Failed to parse service data: {e}")
                    continue
            
            logger.debug(f"Discovered {len(instances)} instances for service {service_name}")
            return instances
        
        except Exception as e:
            logger.error(f"Failed to discover services from etcd: {e}")
            return []
    
    async def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services from etcd."""
        if not self._client:
            return {}
        
        try:
            # Get all service data
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_prefix, self.service_prefix
            )
            
            services = {}
            for value, metadata in result:
                try:
                    service_data = json.loads(value.decode('utf-8'))
                    service_name = service_data["service_name"]
                    
                    if service_name not in services:
                        services[service_name] = []
                    
                    # Create service instance
                    instance = ServiceInstance(
                        service_name=service_data["service_name"],
                        instance_id=service_data["instance_id"],
                        address=service_data["address"],
                        port=service_data["port"],
                        status=ServiceStatus(service_data.get("status", ServiceStatus.UNKNOWN.value)),
                        metadata=service_data.get("metadata", {}),
                        tags=set(service_data.get("tags", [])),
                        health_check_url=service_data.get("health_check_url")
                    )
                    
                    services[service_name].append(instance)
                
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.error(f"Failed to parse service data: {e}")
                    continue
            
            return services
        
        except Exception as e:
            logger.error(f"Failed to get all services from etcd: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check if etcd is healthy."""
        if not self._client:
            return False
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.status
            )
            return True
        except Exception:
            return False
    
    async def update_service_health(self, service_name: str, instance_id: str, status: ServiceStatus) -> bool:
        """Update service health status in etcd."""
        if not self._client:
            return False
        
        try:
            # Get current service data
            key = self._get_service_key(service_name, instance_id)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get, key
            )
            
            if result[0] is None:
                return False
            
            # Update service data
            service_data = json.loads(result[0].decode('utf-8'))
            service_data["status"] = status.value
            service_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Get lease for the key
            lease_id = self._leases.get(instance_id)
            lease = None
            if lease_id:
                try:
                    lease = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: etcd3.lease.Lease(lease_id, self._client)
                    )
                except Exception:
                    pass  # Lease might have expired
            
            # Update the key
            value = json.dumps(service_data)
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.put, key, value, lease
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update service health in etcd: {e}")
            return False
    
    async def watch_services(self, service_name: Optional[str] = None) -> None:
        """Watch for service changes in etcd."""
        if not self._client:
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
        if not self._client:
            return
        
        prefix = self._get_service_prefix_key(service_name)
        
        try:
            events_iterator, cancel = await asyncio.get_event_loop().run_in_executor(
                None, self._client.watch_prefix, prefix
            )
            
            while self.is_connected:
                try:
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, next, events_iterator
                    )
                    
                    # Process the event
                    if event.type == etcd3.events.PutEvent:
                        event_type = DiscoveryEventType.SERVICE_REGISTERED
                    elif event.type == etcd3.events.DeleteEvent:
                        event_type = DiscoveryEventType.SERVICE_DEREGISTERED
                    else:
                        event_type = DiscoveryEventType.SERVICE_UPDATED
                    
                    await self._emit_event(DiscoveryEvent(
                        event_type=event_type,
                        service_name=service_name,
                        metadata={"backend": "etcd", "key": event.key.decode('utf-8')}
                    ))
                
                except StopIteration:
                    break
                except Exception as e:
                    logger.error(f"Error in etcd watch for service {service_name}: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Failed to watch service {service_name}: {e}")
    
    async def _watch_all_services(self) -> None:
        """Watch all services for changes."""
        if not self._client:
            return
        
        try:
            events_iterator, cancel = await asyncio.get_event_loop().run_in_executor(
                None, self._client.watch_prefix, self.service_prefix
            )
            
            while self.is_connected:
                try:
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, next, events_iterator
                    )
                    
                    # Extract service name from key
                    key = event.key.decode('utf-8')
                    service_name = key.replace(self.service_prefix, "").split("/")[0]
                    
                    # Process the event
                    if event.type == etcd3.events.PutEvent:
                        event_type = DiscoveryEventType.SERVICE_REGISTERED
                    elif event.type == etcd3.events.DeleteEvent:
                        event_type = DiscoveryEventType.SERVICE_DEREGISTERED
                    else:
                        event_type = DiscoveryEventType.SERVICE_UPDATED
                    
                    await self._emit_event(DiscoveryEvent(
                        event_type=event_type,
                        service_name=service_name,
                        metadata={"backend": "etcd", "key": key}
                    ))
                
                except StopIteration:
                    break
                except Exception as e:
                    logger.error(f"Error in etcd watch for all services: {e}")
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Failed to watch all services: {e}")
    
    async def _lease_renewal_loop(self) -> None:
        """Background task to renew leases."""
        while self.is_connected:
            try:
                # Renew all active leases
                for instance_id, lease_id in list(self._leases.items()):
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None, self._client.refresh_lease, lease_id
                        )
                        logger.debug(f"Renewed lease {lease_id} for instance {instance_id}")
                    except Exception as e:
                        logger.error(f"Failed to renew lease {lease_id}: {e}")
                        # Remove failed lease
                        self._leases.pop(instance_id, None)
                
                # Wait before next renewal (renew at 2/3 of TTL)
                await asyncio.sleep(self.lease_ttl * 2 / 3)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lease renewal loop: {e}")
                await asyncio.sleep(10)
    
    # etcd-specific methods
    
    async def get_cluster_info(self) -> Dict[str, Any]:
        """Get etcd cluster information."""
        if not self._client:
            return {}
        
        try:
            status = await asyncio.get_event_loop().run_in_executor(
                None, self._client.status
            )
            
            members = await asyncio.get_event_loop().run_in_executor(
                None, self._client.members
            )
            
            return {
                "leader": status.leader,
                "members": [
                    {
                        "id": member.id,
                        "name": member.name,
                        "peer_urls": member.peer_urls,
                        "client_urls": member.client_urls
                    }
                    for member in members
                ],
                "member_count": len(members)
            }
        
        except Exception as e:
            logger.error(f"Failed to get cluster info from etcd: {e}")
            return {}
    
    async def get_lease_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get lease information for a service instance."""
        if not self._client or instance_id not in self._leases:
            return None
        
        try:
            lease_id = self._leases[instance_id]
            lease_info = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_lease_info, lease_id
            )
            
            return {
                "lease_id": lease_id,
                "ttl": lease_info.TTL,
                "granted_ttl": lease_info.grantedTTL
            }
        
        except Exception as e:
            logger.error(f"Failed to get lease info: {e}")
            return None
    
    # Enhanced Configuration Management
    
    async def get_config_value(self, key: str) -> Optional[str]:
        """Get a configuration value from etcd."""
        if not self._client:
            return None
        
        try:
            full_key = f"{self.config_prefix}{key}"
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get, full_key
            )
            
            if result[0] is not None:
                return result[0].decode('utf-8')
            return None
        
        except Exception as e:
            logger.error(f"Failed to get config value: {e}")
            return None
    
    async def set_config_value(self, key: str, value: str) -> bool:
        """Set a configuration value in etcd."""
        if not self._client:
            return False
        
        try:
            full_key = f"{self.config_prefix}{key}"
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.put, full_key, value
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to set config value: {e}")
            return False
    
    async def get_config_json(self, key: str) -> Optional[Any]:
        """Get a JSON configuration value from etcd."""
        try:
            value = await self.get_config_value(key)
            if value:
                return json.loads(value)
            return None
        
        except Exception as e:
            logger.error(f"Failed to get config JSON: {e}")
            return None
    
    async def set_config_json(self, key: str, value: Any) -> bool:
        """Set a JSON configuration value in etcd."""
        try:
            json_value = json.dumps(value)
            return await self.set_config_value(key, json_value)
        
        except Exception as e:
            logger.error(f"Failed to set config JSON: {e}")
            return False
    
    async def get_config_prefix(self, prefix: str) -> Dict[str, str]:
        """Get all configuration values with a given prefix."""
        if not self._client:
            return {}
        
        try:
            full_prefix = f"{self.config_prefix}{prefix}"
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get_prefix, full_prefix
            )
            
            config = {}
            for value, metadata in result:
                key = metadata.key.decode('utf-8').replace(self.config_prefix, "", 1)
                config[key] = value.decode('utf-8')
            
            return config
        
        except Exception as e:
            logger.error(f"Failed to get config prefix: {e}")
            return {}
    
    async def watch_config_prefix(self, prefix: str, callback: Callable) -> None:
        """Watch for configuration changes with a given prefix."""
        if not self._client:
            return
        
        watch_key = f"config_watch_{prefix}"
        if watch_key not in self._watch_tasks:
            task = asyncio.create_task(self._watch_config_prefix(prefix, callback))
            self._watch_tasks[watch_key] = task
    
    async def _watch_config_prefix(self, prefix: str, callback: Callable) -> None:
        """Internal method to watch configuration prefix changes."""
        if not self._client:
            return
        
        full_prefix = f"{self.config_prefix}{prefix}"
        
        try:
            events_iterator, cancel = await asyncio.get_event_loop().run_in_executor(
                None, self._client.watch_prefix, full_prefix
            )
            
            while self.is_connected:
                try:
                    event = await asyncio.get_event_loop().run_in_executor(
                        None, next, events_iterator
                    )
                    
                    # Process the event
                    key = event.key.decode('utf-8').replace(self.config_prefix, "", 1)
                    
                    if hasattr(event, 'value') and event.value:
                        value = event.value.decode('utf-8')
                    else:
                        value = None
                    
                    # Call callback with change
                    change_info = {
                        "key": key,
                        "value": value,
                        "event_type": "PUT" if event.type == events.PutEvent else "DELETE"
                    }
                    
                    if asyncio.iscoroutinefunction(callback):
                        await callback(change_info)
                    else:
                        callback(change_info)
                
                except StopIteration:
                    break
                except Exception as e:
                    logger.error(f"Error in config watch for prefix {prefix}: {e}")
                    await asyncio.sleep(5)
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Failed to watch config prefix {prefix}: {e}")
    
    # Distributed Locking
    
    async def acquire_lock(self, lock_name: str, ttl: Optional[int] = None) -> bool:
        """Acquire a distributed lock."""
        if not self._client:
            return False
        
        try:
            lock_key = f"{self.lock_prefix}{lock_name}"
            lock_ttl = ttl or self.lock_ttl
            
            # Create a lease for the lock
            lease = await asyncio.get_event_loop().run_in_executor(
                None, self._client.lease, lock_ttl
            )
            
            # Try to acquire the lock
            lock = self._client.lock(lock_key, ttl=lock_ttl)
            
            # Attempt to acquire with timeout
            acquired = await asyncio.get_event_loop().run_in_executor(
                None, lock.acquire, 1  # 1 second timeout
            )
            
            if acquired:
                self._locks[lock_name] = lock
                logger.info(f"Acquired lock: {lock_name}")
                return True
            else:
                logger.warning(f"Failed to acquire lock: {lock_name}")
                return False
        
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_name}: {e}")
            return False
    
    async def release_lock(self, lock_name: str) -> bool:
        """Release a distributed lock."""
        if lock_name not in self._locks:
            return False
        
        try:
            lock = self._locks.pop(lock_name)
            await asyncio.get_event_loop().run_in_executor(
                None, lock.release
            )
            logger.info(f"Released lock: {lock_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error releasing lock {lock_name}: {e}")
            return False
    
    async def is_lock_acquired(self, lock_name: str) -> bool:
        """Check if a lock is currently acquired by this client."""
        return lock_name in self._locks
    
    # Leader Election using Distributed Locking
    
    async def acquire_leadership(self, leader_key: str, ttl: Optional[int] = None) -> bool:
        """Acquire leadership using distributed locking."""
        success = await self.acquire_lock(f"leader_{leader_key}", ttl)
        if success:
            self._is_leader = True
            self._leader_key = leader_key
            logger.info(f"Acquired leadership for: {leader_key}")
        return success
    
    async def release_leadership(self) -> bool:
        """Release leadership."""
        if not self._leader_key:
            return False
        
        success = await self.release_lock(f"leader_{self._leader_key}")
        if success:
            self._is_leader = False
            self._leader_key = None
            logger.info("Released leadership")
        return success
    
    @property
    def is_leader(self) -> bool:
        """Check if this instance is the current leader."""
        return self._is_leader
    
    # Service Versioning
    
    async def register_service_with_version(
        self,
        instance: ServiceInstance,
        version: str
    ) -> bool:
        """Register a service instance with version information."""
        if not self.enable_service_versioning:
            return await self.register_service(instance)
        
        # Add version to metadata
        versioned_instance = ServiceInstance(
            service_name=instance.service_name,
            instance_id=instance.instance_id,
            address=instance.address,
            port=instance.port,
            status=instance.status,
            metadata={**instance.metadata, "version": version},
            tags=instance.tags | {f"version:{version}"},
            health_check_url=instance.health_check_url
        )
        
        return await self.register_service(versioned_instance)
    
    async def discover_services_by_version(
        self,
        service_name: str,
        version: str,
        tags: Optional[Set[str]] = None
    ) -> List[ServiceInstance]:
        """Discover service instances by version."""
        version_tags = {f"version:{version}"}
        if tags:
            version_tags.update(tags)
        
        return await self.discover_services(service_name, version_tags)
    
    async def get_service_versions(self, service_name: str) -> List[str]:
        """Get all available versions for a service."""
        instances = await self.discover_services(service_name)
        versions = set()
        
        for instance in instances:
            version = instance.metadata.get("version")
            if version:
                versions.add(version)
        
        return sorted(list(versions))
    
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
        """Monitor cluster health and member changes."""
        while self.is_connected:
            try:
                # Get cluster info
                cluster_info = await self.get_cluster_info()
                
                # Check for member changes
                current_members = cluster_info.get("member_count", 0)
                previous_members = self._cluster_info.get("member_count", 0)
                
                if current_members != previous_members:
                    await self._emit_event(DiscoveryEvent(
                        event_type=DiscoveryEventType.BACKEND_CONNECTED,  # Reuse for member change
                        service_name="etcd-cluster",
                        metadata={
                            "event": "member_change",
                            "current_members": current_members,
                            "previous_members": previous_members
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
            cluster_info = await self.get_cluster_info()
            
            # Get additional health metrics
            health_info = {
                "cluster_info": cluster_info,
                "is_leader": self._is_leader,
                "leader_key": self._leader_key,
                "active_leases": len(self._leases),
                "active_locks": len(self._locks),
                "active_watches": len(self._watch_tasks),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return health_info
        
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Enhanced Service Operations
    
    async def get_service_metadata(self, service_name: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific service instance."""
        if not self._client:
            return None
        
        try:
            key = self._get_service_key(service_name, instance_id)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get, key
            )
            
            if result[0] is None:
                return None
            
            service_data = json.loads(result[0].decode('utf-8'))
            return service_data.get("metadata", {})
        
        except Exception as e:
            logger.error(f"Failed to get service metadata: {e}")
            return None
    
    async def update_service_metadata(
        self,
        service_name: str,
        instance_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update metadata for a specific service instance."""
        if not self._client:
            return False
        
        try:
            key = self._get_service_key(service_name, instance_id)
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._client.get, key
            )
            
            if result[0] is None:
                return False
            
            # Update service data
            service_data = json.loads(result[0].decode('utf-8'))
            service_data["metadata"].update(metadata)
            service_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Get lease for the key
            lease_id = self._leases.get(instance_id)
            lease = None
            if lease_id:
                try:
                    lease = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: etcd3.lease.Lease(lease_id, self._client)
                    )
                except Exception:
                    pass
            
            # Update the key
            value = json.dumps(service_data)
            await asyncio.get_event_loop().run_in_executor(
                None, self._client.put, key, value, lease
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update service metadata: {e}")
            return False
    
    # Service Configuration Management
    
    async def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service."""
        config_key = f"services/{service_name}"
        return await self.get_config_json(config_key) or {}
    
    async def set_service_config(self, service_name: str, config: Dict[str, Any]) -> bool:
        """Set configuration for a specific service."""
        config_key = f"services/{service_name}"
        return await self.set_config_json(config_key, config)
    
    async def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration."""
        return await self.get_config_prefix("global/")
    
    async def set_global_config_value(self, key: str, value: Any) -> bool:
        """Set a global configuration value."""
        config_key = f"global/{key}"
        if isinstance(value, (dict, list)):
            return await self.set_config_json(config_key, value)
        else:
            return await self.set_config_value(config_key, str(value))
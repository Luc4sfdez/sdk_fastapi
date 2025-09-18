"""
Health check scheduler for service discovery.

This module provides health check scheduling and automatic service removal
for unhealthy service instances.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Callable
from urllib.parse import urljoin

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base import ServiceInstance, ServiceStatus, DiscoveryEvent, DiscoveryEventType


logger = logging.getLogger(__name__)


class HealthCheckResult:
    """Result of a health check operation."""
    
    def __init__(
        self,
        instance: ServiceInstance,
        status: ServiceStatus,
        response_time: float,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.instance = instance
        self.status = status
        self.response_time = response_time
        self.status_code = status_code
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)
    
    @property
    def is_healthy(self) -> bool:
        """Check if the health check indicates a healthy service."""
        return self.status == ServiceStatus.HEALTHY
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "service_name": self.instance.service_name,
            "instance_id": self.instance.instance_id,
            "status": self.status.value,
            "response_time": self.response_time,
            "status_code": self.status_code,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class HealthChecker:
    """Performs health checks on service instances."""
    
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp package is required for health checking")
        
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._session: Optional["aiohttp.ClientSession"] = None
    
    async def _get_session(self) -> "aiohttp.ClientSession":
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def check_instance(self, instance: ServiceInstance) -> HealthCheckResult:
        """Perform health check on a service instance."""
        start_time = time.time()
        
        if not instance.health_check_url:
            # No health check URL - assume healthy if recently registered
            age = (datetime.now(timezone.utc) - instance.registered_at).total_seconds()
            status = ServiceStatus.HEALTHY if age < 300 else ServiceStatus.UNKNOWN
            return HealthCheckResult(
                instance=instance,
                status=status,
                response_time=0.0,
                metadata={"reason": "no_health_check_url"}
            )
        
        # Build health check URL
        if instance.health_check_url.startswith(('http://', 'https://')):
            health_url = instance.health_check_url
        else:
            health_url = urljoin(instance.url, instance.health_check_url)
        
        # Perform health check with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = await self._get_session()
                async with session.get(health_url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        # Try to parse response for additional metadata
                        metadata = {}
                        try:
                            if response.content_type == 'application/json':
                                response_data = await response.json()
                                if isinstance(response_data, dict):
                                    metadata = response_data
                        except Exception:
                            pass  # Ignore JSON parsing errors
                        
                        return HealthCheckResult(
                            instance=instance,
                            status=ServiceStatus.HEALTHY,
                            response_time=response_time,
                            status_code=response.status,
                            metadata=metadata
                        )
                    elif response.status in (503, 429):  # Service unavailable or rate limited
                        return HealthCheckResult(
                            instance=instance,
                            status=ServiceStatus.UNHEALTHY,
                            response_time=response_time,
                            status_code=response.status,
                            error=f"HTTP {response.status}"
                        )
                    else:
                        return HealthCheckResult(
                            instance=instance,
                            status=ServiceStatus.CRITICAL,
                            response_time=response_time,
                            status_code=response.status,
                            error=f"HTTP {response.status}"
                        )
            
            except asyncio.TimeoutError:
                last_error = "Health check timeout"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
            
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
        
        # All retries failed
        response_time = time.time() - start_time
        return HealthCheckResult(
            instance=instance,
            status=ServiceStatus.CRITICAL,
            response_time=response_time,
            error=last_error
        )
    
    async def check_instances(self, instances: List[ServiceInstance]) -> List[HealthCheckResult]:
        """Perform health checks on multiple instances concurrently."""
        if not instances:
            return []
        
        # Create tasks for concurrent health checks
        tasks = [self.check_instance(instance) for instance in instances]
        
        # Execute with limited concurrency
        semaphore = asyncio.Semaphore(10)  # Limit concurrent checks
        
        async def check_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[check_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions and return valid results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {instances[i].instance_id}: {result}")
                # Create error result
                valid_results.append(HealthCheckResult(
                    instance=instances[i],
                    status=ServiceStatus.CRITICAL,
                    response_time=0.0,
                    error=str(result)
                ))
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()


class HealthCheckScheduler:
    """Schedules and manages health checks for service instances."""
    
    def __init__(
        self,
        registry,  # EnhancedServiceRegistry
        interval: int = 30,
        unhealthy_threshold: int = 3,
        critical_threshold: int = 5,
        removal_threshold: int = 10,
        max_concurrent_checks: int = 50
    ):
        self.registry = registry
        self.interval = interval
        self.unhealthy_threshold = unhealthy_threshold
        self.critical_threshold = critical_threshold
        self.removal_threshold = removal_threshold
        self.max_concurrent_checks = max_concurrent_checks
        
        self.health_checker = HealthChecker()
        self._is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._failure_counts: Dict[str, int] = {}  # instance_id -> failure_count
        self._last_check_times: Dict[str, datetime] = {}
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._stats = {
            "total_checks": 0,
            "healthy_checks": 0,
            "unhealthy_checks": 0,
            "critical_checks": 0,
            "removed_instances": 0,
            "last_check_time": None
        }
    
    async def start(self) -> None:
        """Start the health check scheduler."""
        if self._is_running:
            return
        
        async with self._lock:
            if self._is_running:
                return
            
            logger.info("Starting health check scheduler")
            self._is_running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
    
    async def stop(self) -> None:
        """Stop the health check scheduler."""
        if not self._is_running:
            return
        
        async with self._lock:
            if not self._is_running:
                return
            
            logger.info("Stopping health check scheduler")
            self._is_running = False
            
            if self._scheduler_task and not self._scheduler_task.done():
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
            
            await self.health_checker.close()
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._is_running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check scheduler: {e}")
                await asyncio.sleep(self.interval)
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all registered services."""
        try:
            # Get all services
            service_names = await self.registry.list_services()
            all_instances = []
            
            for service_name in service_names:
                try:
                    instances = await self.registry.discover(service_name)
                    all_instances.extend(instances)
                except Exception as e:
                    logger.error(f"Error discovering service {service_name}: {e}")
            
            if not all_instances:
                return
            
            logger.debug(f"Performing health checks on {len(all_instances)} instances")
            
            # Perform health checks
            results = await self.health_checker.check_instances(all_instances)
            
            # Process results
            await self._process_health_check_results(results)
            
            # Update statistics
            self._stats["total_checks"] += len(results)
            self._stats["last_check_time"] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            logger.error(f"Error performing health checks: {e}")
    
    async def _process_health_check_results(self, results: List[HealthCheckResult]) -> None:
        """Process health check results and update service statuses."""
        for result in results:
            instance = result.instance
            instance_key = f"{instance.service_name}:{instance.instance_id}"
            
            # Update statistics
            if result.status == ServiceStatus.HEALTHY:
                self._stats["healthy_checks"] += 1
            elif result.status == ServiceStatus.UNHEALTHY:
                self._stats["unhealthy_checks"] += 1
            elif result.status == ServiceStatus.CRITICAL:
                self._stats["critical_checks"] += 1
            
            # Store health history
            if instance_key not in self._health_history:
                self._health_history[instance_key] = []
            
            self._health_history[instance_key].append(result)
            
            # Keep only last 10 results
            if len(self._health_history[instance_key]) > 10:
                self._health_history[instance_key] = self._health_history[instance_key][-10:]
            
            # Update failure counts
            if result.is_healthy:
                # Reset failure count on successful health check
                self._failure_counts[instance_key] = 0
            else:
                # Increment failure count
                self._failure_counts[instance_key] = self._failure_counts.get(instance_key, 0) + 1
            
            # Update last check time
            self._last_check_times[instance_key] = result.timestamp
            
            # Determine action based on failure count
            failure_count = self._failure_counts.get(instance_key, 0)
            
            if failure_count >= self.removal_threshold:
                # Remove instance after too many failures
                await self._remove_unhealthy_instance(instance)
            elif failure_count >= self.critical_threshold:
                # Mark as critical
                await self._update_instance_status(instance, ServiceStatus.CRITICAL)
            elif failure_count >= self.unhealthy_threshold:
                # Mark as unhealthy
                await self._update_instance_status(instance, ServiceStatus.UNHEALTHY)
            else:
                # Mark as healthy
                await self._update_instance_status(instance, ServiceStatus.HEALTHY)
    
    async def _update_instance_status(self, instance: ServiceInstance, status: ServiceStatus) -> None:
        """Update the status of a service instance."""
        if instance.status != status:
            logger.info(f"Updating status for {instance.service_name}/{instance.instance_id}: {status.value}")
            
            try:
                await self.registry.update_service_health(
                    instance.service_name,
                    instance.instance_id,
                    status
                )
            except Exception as e:
                logger.error(f"Error updating instance status: {e}")
    
    async def _remove_unhealthy_instance(self, instance: ServiceInstance) -> None:
        """Remove an unhealthy service instance."""
        logger.warning(f"Removing unhealthy instance: {instance.service_name}/{instance.instance_id}")
        
        try:
            await self.registry.deregister(instance.service_name, instance.instance_id)
            
            # Clean up tracking data
            instance_key = f"{instance.service_name}:{instance.instance_id}"
            self._failure_counts.pop(instance_key, None)
            self._last_check_times.pop(instance_key, None)
            self._health_history.pop(instance_key, None)
            
            self._stats["removed_instances"] += 1
            
        except Exception as e:
            logger.error(f"Error removing unhealthy instance: {e}")
    
    async def check_instance_now(self, instance: ServiceInstance) -> HealthCheckResult:
        """Perform an immediate health check on a specific instance."""
        return await self.health_checker.check_instance(instance)
    
    async def check_service_now(self, service_name: str) -> List[HealthCheckResult]:
        """Perform immediate health checks on all instances of a service."""
        try:
            instances = await self.registry.discover(service_name)
            return await self.health_checker.check_instances(instances)
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            return []
    
    def get_instance_health_history(self, service_name: str, instance_id: str) -> List[HealthCheckResult]:
        """Get health check history for a specific instance."""
        instance_key = f"{service_name}:{instance_id}"
        return self._health_history.get(instance_key, [])
    
    def get_instance_failure_count(self, service_name: str, instance_id: str) -> int:
        """Get the current failure count for an instance."""
        instance_key = f"{service_name}:{instance_id}"
        return self._failure_counts.get(instance_key, 0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get health check statistics."""
        return {
            **self._stats,
            "is_running": self._is_running,
            "interval": self.interval,
            "tracked_instances": len(self._failure_counts),
            "unhealthy_threshold": self.unhealthy_threshold,
            "critical_threshold": self.critical_threshold,
            "removal_threshold": self.removal_threshold
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of current health status."""
        healthy_count = 0
        unhealthy_count = 0
        critical_count = 0
        
        for failure_count in self._failure_counts.values():
            if failure_count == 0:
                healthy_count += 1
            elif failure_count < self.critical_threshold:
                unhealthy_count += 1
            else:
                critical_count += 1
        
        return {
            "healthy_instances": healthy_count,
            "unhealthy_instances": unhealthy_count,
            "critical_instances": critical_count,
            "total_instances": len(self._failure_counts)
        }
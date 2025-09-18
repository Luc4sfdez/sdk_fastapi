"""
Health Monitor - Specialized health monitoring utilities
"""
import asyncio
import aiohttp
import socket
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class HealthCheckType(Enum):
    HTTP = "http"
    TCP = "tcp"
    DATABASE = "database"
    CUSTOM = "custom"

@dataclass
class HealthCheckConfig:
    name: str
    check_type: HealthCheckType
    target: str
    timeout: float = 5.0
    interval: int = 30
    retries: int = 3
    expected_status: Optional[int] = None
    expected_response: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    custom_check: Optional[Callable] = None

class HealthMonitor:
    """
    Specialized health monitoring for external services and dependencies.
    
    Features:
    - HTTP endpoint monitoring
    - TCP port monitoring
    - Database connection monitoring
    - Custom health check functions
    - Retry logic and timeout handling
    """
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheckConfig] = {}
        self.health_results: Dict[str, Dict[str, Any]] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> bool:
        """Initialize the health monitor"""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Health Monitor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Health Monitor: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the health monitor"""
        try:
            # Cancel all monitoring tasks
            for task in self.monitoring_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Close HTTP session
            if self.session:
                await self.session.close()
            
            logger.info("Health Monitor shutdown successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to shutdown Health Monitor: {e}")
            return False
    
    def add_http_check(
        self, 
        name: str, 
        url: str, 
        expected_status: int = 200,
        timeout: float = 5.0,
        interval: int = 30,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Add HTTP health check"""
        try:
            config = HealthCheckConfig(
                name=name,
                check_type=HealthCheckType.HTTP,
                target=url,
                timeout=timeout,
                interval=interval,
                expected_status=expected_status,
                headers=headers or {}
            )
            
            return self._add_health_check(config)
            
        except Exception as e:
            logger.error(f"Failed to add HTTP check {name}: {e}")
            return False
    
    def add_tcp_check(
        self, 
        name: str, 
        host: str, 
        port: int,
        timeout: float = 5.0,
        interval: int = 30
    ) -> bool:
        """Add TCP port health check"""
        try:
            config = HealthCheckConfig(
                name=name,
                check_type=HealthCheckType.TCP,
                target=f"{host}:{port}",
                timeout=timeout,
                interval=interval
            )
            
            return self._add_health_check(config)
            
        except Exception as e:
            logger.error(f"Failed to add TCP check {name}: {e}")
            return False
    
    def add_custom_check(
        self, 
        name: str, 
        check_function: Callable,
        interval: int = 30,
        timeout: float = 5.0
    ) -> bool:
        """Add custom health check function"""
        try:
            config = HealthCheckConfig(
                name=name,
                check_type=HealthCheckType.CUSTOM,
                target="custom",
                timeout=timeout,
                interval=interval,
                custom_check=check_function
            )
            
            return self._add_health_check(config)
            
        except Exception as e:
            logger.error(f"Failed to add custom check {name}: {e}")
            return False
    
    def _add_health_check(self, config: HealthCheckConfig) -> bool:
        """Add health check configuration and start monitoring"""
        try:
            self.health_checks[config.name] = config
            
            # Start monitoring task
            task = asyncio.create_task(self._monitor_health_check(config))
            self.monitoring_tasks[config.name] = task
            
            logger.info(f"Added health check: {config.name} ({config.check_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add health check {config.name}: {e}")
            return False
    
    def remove_health_check(self, name: str) -> bool:
        """Remove health check"""
        try:
            if name in self.health_checks:
                # Cancel monitoring task
                if name in self.monitoring_tasks:
                    self.monitoring_tasks[name].cancel()
                    del self.monitoring_tasks[name]
                
                # Remove configuration and results
                del self.health_checks[name]
                if name in self.health_results:
                    del self.health_results[name]
                
                logger.info(f"Removed health check: {name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove health check {name}: {e}")
            return False
    
    async def _monitor_health_check(self, config: HealthCheckConfig) -> None:
        """Monitor a single health check"""
        while True:
            try:
                # Perform health check
                result = await self._perform_health_check(config)
                
                # Store result
                self.health_results[config.name] = result
                
                # Wait for next check
                await asyncio.sleep(config.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring health check {config.name}: {e}")
                
                # Store error result
                self.health_results[config.name] = {
                    "status": "critical",
                    "message": f"Monitoring error: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": 0.0,
                    "success": False
                }
                
                await asyncio.sleep(config.interval)
    
    async def _perform_health_check(self, config: HealthCheckConfig) -> Dict[str, Any]:
        """Perform a single health check"""
        start_time = time.time()
        
        try:
            if config.check_type == HealthCheckType.HTTP:
                return await self._check_http(config, start_time)
            elif config.check_type == HealthCheckType.TCP:
                return await self._check_tcp(config, start_time)
            elif config.check_type == HealthCheckType.CUSTOM:
                return await self._check_custom(config, start_time)
            else:
                return {
                    "status": "unknown",
                    "message": f"Unknown check type: {config.check_type}",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": 0.0,
                    "success": False
                }
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "critical",
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "success": False,
                "error": str(e)
            }
    
    async def _check_http(self, config: HealthCheckConfig, start_time: float) -> Dict[str, Any]:
        """Perform HTTP health check"""
        if not self.session:
            raise Exception("HTTP session not initialized")
        
        for attempt in range(config.retries):
            try:
                async with self.session.get(
                    config.target, 
                    headers=config.headers,
                    timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    success = True
                    status = "healthy"
                    message = f"HTTP {response.status}"
                    
                    # Check expected status
                    if config.expected_status and response.status != config.expected_status:
                        success = False
                        status = "critical"
                        message = f"Expected status {config.expected_status}, got {response.status}"
                    
                    # Check response content if specified
                    if config.expected_response:
                        text = await response.text()
                        if config.expected_response not in text:
                            success = False
                            status = "critical"
                            message = f"Expected response content not found"
                    
                    return {
                        "status": status,
                        "message": message,
                        "timestamp": datetime.now().isoformat(),
                        "response_time": response_time,
                        "success": success,
                        "http_status": response.status,
                        "attempt": attempt + 1
                    }
                    
            except asyncio.TimeoutError:
                if attempt == config.retries - 1:
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "status": "critical",
                        "message": f"HTTP request timeout after {config.timeout}s",
                        "timestamp": datetime.now().isoformat(),
                        "response_time": response_time,
                        "success": False,
                        "attempts": config.retries
                    }
                await asyncio.sleep(1)  # Wait before retry
                
            except Exception as e:
                if attempt == config.retries - 1:
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "status": "critical",
                        "message": f"HTTP request failed: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "response_time": response_time,
                        "success": False,
                        "error": str(e),
                        "attempts": config.retries
                    }
                await asyncio.sleep(1)  # Wait before retry
    
    async def _check_tcp(self, config: HealthCheckConfig, start_time: float) -> Dict[str, Any]:
        """Perform TCP port health check"""
        host, port = config.target.split(':')
        port = int(port)
        
        for attempt in range(config.retries):
            try:
                # Try to connect to the TCP port
                future = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(future, timeout=config.timeout)
                
                # Close connection
                writer.close()
                await writer.wait_closed()
                
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "message": f"TCP connection to {host}:{port} successful",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": response_time,
                    "success": True,
                    "attempt": attempt + 1
                }
                
            except asyncio.TimeoutError:
                if attempt == config.retries - 1:
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "status": "critical",
                        "message": f"TCP connection timeout to {host}:{port}",
                        "timestamp": datetime.now().isoformat(),
                        "response_time": response_time,
                        "success": False,
                        "attempts": config.retries
                    }
                await asyncio.sleep(1)
                
            except Exception as e:
                if attempt == config.retries - 1:
                    response_time = (time.time() - start_time) * 1000
                    return {
                        "status": "critical",
                        "message": f"TCP connection failed to {host}:{port}: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                        "response_time": response_time,
                        "success": False,
                        "error": str(e),
                        "attempts": config.retries
                    }
                await asyncio.sleep(1)
    
    async def _check_custom(self, config: HealthCheckConfig, start_time: float) -> Dict[str, Any]:
        """Perform custom health check"""
        if not config.custom_check:
            raise Exception("Custom check function not provided")
        
        try:
            # Execute custom check function
            if asyncio.iscoroutinefunction(config.custom_check):
                result = await asyncio.wait_for(config.custom_check(), timeout=config.timeout)
            else:
                result = config.custom_check()
            
            response_time = (time.time() - start_time) * 1000
            
            # Handle different result types
            if isinstance(result, dict):
                result["timestamp"] = datetime.now().isoformat()
                result["response_time"] = response_time
                return result
            elif isinstance(result, bool):
                return {
                    "status": "healthy" if result else "critical",
                    "message": "Custom check passed" if result else "Custom check failed",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": response_time,
                    "success": result
                }
            else:
                return {
                    "status": "healthy",
                    "message": f"Custom check result: {result}",
                    "timestamp": datetime.now().isoformat(),
                    "response_time": response_time,
                    "success": True,
                    "result": result
                }
                
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "critical",
                "message": f"Custom check timeout after {config.timeout}s",
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
                "success": False
            }
    
    def get_health_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get health status for a specific check"""
        return self.health_results.get(name)
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all checks"""
        return self.health_results.copy()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary"""
        total_checks = len(self.health_checks)
        if total_checks == 0:
            return {
                "overall_status": "unknown",
                "total_checks": 0,
                "healthy_checks": 0,
                "critical_checks": 0,
                "unknown_checks": 0
            }
        
        healthy_count = 0
        critical_count = 0
        unknown_count = 0
        
        for result in self.health_results.values():
            status = result.get("status", "unknown")
            if status == "healthy":
                healthy_count += 1
            elif status == "critical":
                critical_count += 1
            else:
                unknown_count += 1
        
        # Determine overall status
        if critical_count > 0:
            overall_status = "critical"
        elif unknown_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "total_checks": total_checks,
            "healthy_checks": healthy_count,
            "critical_checks": critical_count,
            "unknown_checks": unknown_count,
            "last_updated": datetime.now().isoformat()
        }
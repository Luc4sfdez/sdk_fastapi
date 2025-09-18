"""
Dependency Health Checking with Circuit Breakers for FastAPI Microservices SDK.

This module provides comprehensive dependency health checking with
circuit breaker integration for resilient microservices.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import DependencyConfig, DependencyType, HealthStatus
from .monitor import HealthCheckResult
from .exceptions import DependencyHealthError, CircuitBreakerError


class CircuitState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls are failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    state_changed_time: datetime
    total_calls: int
    failed_calls: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_success_time': self.last_success_time.isoformat() if self.last_success_time else None,
            'state_changed_time': self.state_changed_time.isoformat(),
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'failure_rate': self.failed_calls / max(1, self.total_calls)
        }


class CircuitBreaker:
    """Circuit breaker implementation for dependency health checking."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        # Circuit state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        self._state_changed_time = datetime.now(timezone.utc)
        self._half_open_calls = 0
        
        # Statistics
        self._total_calls = 0
        self._failed_calls = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        self._total_calls += 1
        
        # Check if circuit is open
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._state_changed_time = datetime.now(timezone.utc)
                self.logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN state")
            else:
                # Circuit is open, fail fast
                raise CircuitBreakerError(
                    f"Circuit breaker {self.name} is OPEN",
                    circuit_name=self.name,
                    circuit_state=self._state.value,
                    failure_count=self._failure_count
                )
        
        # Check half-open state limits
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(
                    f"Circuit breaker {self.name} HALF_OPEN call limit exceeded",
                    circuit_name=self.name,
                    circuit_state=self._state.value,
                    failure_count=self._failure_count
                )
            self._half_open_calls += 1
        
        # Execute the function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - record it
            self._on_success()
            return result
            
        except Exception as e:
            # Failure - record it
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        self._success_count += 1
        self._last_success_time = datetime.now(timezone.utc)
        
        if self._state == CircuitState.HALF_OPEN:
            # If we're in half-open and got enough successes, close the circuit
            if self._success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._state_changed_time = datetime.now(timezone.utc)
                self.logger.info(f"Circuit breaker {self.name} moved to CLOSED state")
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self._failed_calls += 1
        self._last_failure_time = datetime.now(timezone.utc)
        
        if self._state == CircuitState.CLOSED:
            # Check if we should open the circuit
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._state_changed_time = datetime.now(timezone.utc)
                self.logger.warning(f"Circuit breaker {self.name} moved to OPEN state")
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state opens the circuit
            self._state = CircuitState.OPEN
            self._state_changed_time = datetime.now(timezone.utc)
            self.logger.warning(f"Circuit breaker {self.name} moved back to OPEN state")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self._last_failure_time is None:
            return True
        
        time_since_failure = datetime.now(timezone.utc) - self._last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return CircuitBreakerStats(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_success_time=self._last_success_time,
            state_changed_time=self._state_changed_time,
            total_calls=self._total_calls,
            failed_calls=self._failed_calls
        )
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._state_changed_time = datetime.now(timezone.utc)
        self.logger.info(f"Circuit breaker {self.name} manually reset")


@dataclass
class DependencyHealth:
    """Dependency health information."""
    name: str
    type: DependencyType
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time_ms: float
    circuit_breaker_state: Optional[CircuitState] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.type.value,
            'status': self.status.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'response_time_ms': self.response_time_ms,
            'circuit_breaker_state': self.circuit_breaker_state.value if self.circuit_breaker_state else None,
            'details': self.details,
            'error': self.error
        }


class DependencyChecker:
    """Dependency health checker with circuit breaker integration."""
    
    def __init__(self, dependency_config: DependencyConfig):
        self.config = dependency_config
        self.logger = logging.getLogger(__name__)
        
        # Circuit breaker
        self.circuit_breaker = None
        if dependency_config.circuit_breaker_enabled:
            self.circuit_breaker = CircuitBreaker(
                name=dependency_config.name,
                failure_threshold=dependency_config.failure_threshold,
                recovery_timeout=dependency_config.recovery_timeout,
                half_open_max_calls=dependency_config.half_open_max_calls
            )
        
        # Statistics
        self._check_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_response_time = 0.0
        
        # Custom check function
        self._custom_check_function = None
        if dependency_config.custom_check_function:
            self._load_custom_check_function()
    
    def _load_custom_check_function(self):
        """Load custom check function from string reference."""
        try:
            # This would typically load a function from a module
            # For now, we'll just log that it's configured
            self.logger.info(f"Custom check function configured: {self.config.custom_check_function}")
        except Exception as e:
            self.logger.error(f"Failed to load custom check function: {e}")
    
    async def check_health(self) -> DependencyHealth:
        """Check dependency health."""
        start_time = time.time()
        
        try:
            # Use circuit breaker if enabled
            if self.circuit_breaker:
                result = await self.circuit_breaker.call(self._perform_health_check)
            else:
                result = await self._perform_health_check()
            
            # Update statistics
            self._check_count += 1
            self._success_count += 1
            response_time = (time.time() - start_time) * 1000
            self._total_response_time += response_time
            
            return DependencyHealth(
                name=self.config.name,
                type=self.config.type,
                status=HealthStatus.HEALTHY,
                message=result.get('message', 'Dependency is healthy'),
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                circuit_breaker_state=self.circuit_breaker.get_stats().state if self.circuit_breaker else None,
                details=result
            )
            
        except CircuitBreakerError as e:
            # Circuit breaker is open
            response_time = (time.time() - start_time) * 1000
            
            return DependencyHealth(
                name=self.config.name,
                type=self.config.type,
                status=HealthStatus.UNHEALTHY,
                message=f"Circuit breaker is {e.circuit_state}",
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                circuit_breaker_state=CircuitState(e.circuit_state),
                error=str(e)
            )
            
        except Exception as e:
            # Health check failed
            self._check_count += 1
            self._failure_count += 1
            response_time = (time.time() - start_time) * 1000
            
            return DependencyHealth(
                name=self.config.name,
                type=self.config.type,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                circuit_breaker_state=self.circuit_breaker.get_stats().state if self.circuit_breaker else None,
                error=str(e)
            )
    
    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform the actual health check."""
        # Use custom check function if available
        if self._custom_check_function:
            return await self._custom_check_function(self.config)
        
        # Use built-in checks based on dependency type
        if self.config.type == DependencyType.DATABASE:
            return await self._check_database()
        elif self.config.type == DependencyType.CACHE:
            return await self._check_cache()
        elif self.config.type == DependencyType.MESSAGE_QUEUE:
            return await self._check_message_queue()
        elif self.config.type == DependencyType.EXTERNAL_API:
            return await self._check_external_api()
        elif self.config.type == DependencyType.FILE_SYSTEM:
            return await self._check_file_system()
        elif self.config.type == DependencyType.NETWORK:
            return await self._check_network()
        else:
            return await self._check_generic()
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database dependency."""
        try:
            # Try to import and use appropriate database client
            if 'postgres' in self.config.name.lower():
                return await self._check_postgresql()
            elif 'mysql' in self.config.name.lower():
                return await self._check_mysql()
            elif 'mongo' in self.config.name.lower():
                return await self._check_mongodb()
            else:
                # Generic database check
                return await self._check_generic_database()
                
        except Exception as e:
            raise DependencyHealthError(
                f"Database health check failed: {e}",
                dependency_name=self.config.name,
                dependency_type=self.config.type.value,
                endpoint=f"{self.config.host}:{self.config.port}",
                original_error=e
            )
    
    async def _check_postgresql(self) -> Dict[str, Any]:
        """Check PostgreSQL database."""
        try:
            import asyncpg
            
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database_name,
                    timeout=self.config.timeout_seconds
                ),
                timeout=self.config.timeout_seconds
            )
            
            # Test query
            result = await conn.fetchval("SELECT version()")
            await conn.close()
            
            return {
                'message': 'PostgreSQL connection successful',
                'version': result,
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database_name
            }
            
        except ImportError:
            # Fallback to generic network check
            return await self._check_network()
    
    async def _check_mysql(self) -> Dict[str, Any]:
        """Check MySQL database."""
        try:
            import aiomysql
            
            conn = await asyncio.wait_for(
                aiomysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.database_name,
                    connect_timeout=self.config.timeout_seconds
                ),
                timeout=self.config.timeout_seconds
            )
            
            # Test query
            cursor = await conn.cursor()
            await cursor.execute("SELECT VERSION()")
            result = await cursor.fetchone()
            await cursor.close()
            conn.close()
            
            return {
                'message': 'MySQL connection successful',
                'version': result[0] if result else 'unknown',
                'host': self.config.host,
                'port': self.config.port,
                'database': self.config.database_name
            }
            
        except ImportError:
            # Fallback to generic network check
            return await self._check_network()
    
    async def _check_mongodb(self) -> Dict[str, Any]:
        """Check MongoDB database."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            client = AsyncIOMotorClient(
                f"mongodb://{self.config.host}:{self.config.port}",
                serverSelectionTimeoutMS=int(self.config.timeout_seconds * 1000)
            )
            
            # Test connection
            await asyncio.wait_for(
                client.admin.command('ping'),
                timeout=self.config.timeout_seconds
            )
            
            # Get server info
            server_info = await client.server_info()
            client.close()
            
            return {
                'message': 'MongoDB connection successful',
                'version': server_info.get('version', 'unknown'),
                'host': self.config.host,
                'port': self.config.port
            }
            
        except ImportError:
            # Fallback to generic network check
            return await self._check_network()
    
    async def _check_generic_database(self) -> Dict[str, Any]:
        """Generic database check using network connectivity."""
        return await self._check_network()
    
    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache dependency (Redis)."""
        try:
            import aioredis
            
            redis = aioredis.from_url(
                f"redis://{self.config.host}:{self.config.port}",
                socket_timeout=self.config.timeout_seconds
            )
            
            # Test connection
            await asyncio.wait_for(
                redis.ping(),
                timeout=self.config.timeout_seconds
            )
            
            # Get info
            info = await redis.info()
            await redis.close()
            
            return {
                'message': 'Redis connection successful',
                'version': info.get('redis_version', 'unknown'),
                'host': self.config.host,
                'port': self.config.port,
                'connected_clients': info.get('connected_clients', 0)
            }
            
        except ImportError:
            # Fallback to generic network check
            return await self._check_network()
    
    async def _check_message_queue(self) -> Dict[str, Any]:
        """Check message queue dependency."""
        # This would implement specific message queue checks
        # For now, use generic network check
        return await self._check_network()
    
    async def _check_external_api(self) -> Dict[str, Any]:
        """Check external API dependency."""
        try:
            import aiohttp
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.config.url) as response:
                    return {
                        'message': f'API responded with status {response.status}',
                        'status_code': response.status,
                        'url': self.config.url,
                        'headers': dict(response.headers)
                    }
                    
        except ImportError:
            raise DependencyHealthError(
                "aiohttp not available for API health check",
                dependency_name=self.config.name,
                dependency_type=self.config.type.value,
                endpoint=self.config.url
            )
    
    async def _check_file_system(self) -> Dict[str, Any]:
        """Check file system dependency."""
        import os
        import tempfile
        
        # Test file system access
        test_file = os.path.join(tempfile.gettempdir(), f"health_check_{self.config.name}")
        
        try:
            # Write test
            with open(test_file, 'w') as f:
                f.write('health_check')
            
            # Read test
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            os.remove(test_file)
            
            if content == 'health_check':
                return {
                    'message': 'File system access successful',
                    'test_path': test_file
                }
            else:
                raise Exception("File content mismatch")
                
        except Exception as e:
            # Cleanup on error
            try:
                os.remove(test_file)
            except:
                pass
            raise e
    
    async def _check_network(self) -> Dict[str, Any]:
        """Check network connectivity."""
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.config.timeout_seconds)
        
        try:
            result = sock.connect_ex((self.config.host, self.config.port))
            sock.close()
            
            if result == 0:
                return {
                    'message': 'Network connection successful',
                    'host': self.config.host,
                    'port': self.config.port
                }
            else:
                raise Exception(f"Connection failed with code {result}")
                
        except Exception as e:
            sock.close()
            raise e
    
    async def _check_generic(self) -> Dict[str, Any]:
        """Generic health check."""
        return {
            'message': 'Generic health check passed',
            'dependency_name': self.config.name,
            'dependency_type': self.config.type.value
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dependency checker statistics."""
        avg_response_time = self._total_response_time / max(1, self._check_count)
        success_rate = self._success_count / max(1, self._check_count)
        
        stats = {
            'dependency_name': self.config.name,
            'dependency_type': self.config.type.value,
            'total_checks': self._check_count,
            'success_count': self._success_count,
            'failure_count': self._failure_count,
            'success_rate': success_rate,
            'average_response_time_ms': avg_response_time
        }
        
        if self.circuit_breaker:
            stats['circuit_breaker'] = self.circuit_breaker.get_stats().to_dict()
        
        return stats


def create_dependency_checker(dependency_config: DependencyConfig) -> DependencyChecker:
    """Create dependency checker instance."""
    return DependencyChecker(dependency_config)


# Export main classes and functions
__all__ = [
    'CircuitState',
    'CircuitBreakerStats',
    'CircuitBreaker',
    'DependencyHealth',
    'DependencyChecker',
    'create_dependency_checker',
]
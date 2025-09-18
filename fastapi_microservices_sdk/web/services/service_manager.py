"""
Service management for the web dashboard.
"""

import os
import signal
import psutil
import subprocess
import asyncio
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..core.base_manager import BaseManager
from .database import get_database_manager, ServiceDatabaseManager
from .repository import ServiceRepository


# Import types from separate module to avoid circular imports
from .types import (
    ServiceStatus, HealthStatus, ResourceUsage, ServiceInfo, ServiceDetails
)


class ServiceManager(BaseManager):
    """
    Service management for the web dashboard.
    
    Handles:
    - Service lifecycle operations (start, stop, restart)
    - Service discovery and status monitoring
    - Service health checking
    - Service information retrieval
    """
    
    def __init__(self, name: str = "service", config: Optional[Dict[str, Any]] = None):
        """Initialize the service manager."""
        super().__init__(name, config)
        self._services: Dict[str, ServiceInfo] = {}
        self._processes: Dict[str, subprocess.Popen] = {}
        self._health_check_interval = self.get_config("health_check_interval", 60)
        self._services_directory = Path(self.get_config("services_directory", "."))
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Database integration
        self._db_manager: Optional[ServiceDatabaseManager] = None
        self._repository: Optional[ServiceRepository] = None
        self._use_database = self.get_config("use_database", True)
    
    async def _initialize_impl(self) -> None:
        """Initialize the service manager."""
        # Initialize database if enabled
        if self._use_database:
            database_url = self.get_config("database_url")
            self._db_manager = get_database_manager(database_url)
            
            # Load services from database
            await self._load_services_from_database()
        
        # Discover existing services from filesystem
        await self._discover_services()
        
        # Start health checking task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        self.logger.info("Service manager initialized")
    
    async def list_services(self) -> List[ServiceInfo]:
        """
        Get list of all services.
        
        Returns:
            List of service information
        """
        return await self._safe_execute(
            "list_services",
            self._list_services_impl
        ) or []
    
    async def get_service_details(self, service_id: str) -> Optional[ServiceDetails]:
        """
        Get detailed information about a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service details or None if not found
        """
        return await self._safe_execute(
            "get_service_details",
            self._get_service_details_impl,
            service_id
        )
    
    async def start_service(self, service_id: str) -> bool:
        """
        Start a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if service started successfully
        """
        result = await self._safe_execute(
            "start_service",
            self._start_service_impl,
            service_id
        )
        return result is not None and result
    
    async def stop_service(self, service_id: str) -> bool:
        """
        Stop a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if service stopped successfully
        """
        result = await self._safe_execute(
            "stop_service",
            self._stop_service_impl,
            service_id
        )
        return result is not None and result
    
    async def restart_service(self, service_id: str) -> bool:
        """
        Restart a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if service restarted successfully
        """
        result = await self._safe_execute(
            "restart_service",
            self._restart_service_impl,
            service_id
        )
        return result is not None and result
    
    async def delete_service(self, service_id: str) -> bool:
        """
        Delete a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if service deleted successfully
        """
        result = await self._safe_execute(
            "delete_service",
            self._delete_service_impl,
            service_id
        )
        return result is not None and result
    
    async def get_service_health(self, service_id: str) -> HealthStatus:
        """
        Get service health status.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Health status
        """
        result = await self._safe_execute(
            "get_service_health",
            self._get_service_health_impl,
            service_id
        )
        return result or HealthStatus.UNKNOWN
    
    # Implementation methods
    
    async def _discover_services(self) -> None:
        """Discover existing services in the services directory."""
        try:
            # Look for service directories
            if not self._services_directory.exists():
                self.logger.info("Services directory does not exist, creating it")
                self._services_directory.mkdir(parents=True, exist_ok=True)
                return
            
            # Scan for service directories
            for service_dir in self._services_directory.iterdir():
                if service_dir.is_dir() and not service_dir.name.startswith('.'):
                    await self._discover_service(service_dir)
                    
        except Exception as e:
            self.logger.error(f"Error discovering services: {e}")
    
    async def _discover_service(self, service_dir: Path) -> None:
        """Discover a single service from its directory."""
        try:
            service_name = service_dir.name
            
            # Look for main.py or app.py
            main_file = service_dir / "main.py"
            app_file = service_dir / "app.py"
            
            if not (main_file.exists() or app_file.exists()):
                return
            
            # Try to read service configuration
            config_file = service_dir / "config.py"
            requirements_file = service_dir / "requirements.txt"
            
            # Extract service information
            service_info = await self._extract_service_info(service_dir)
            if service_info:
                self._services[service_info.id] = service_info
                # Save to database
                await self._save_service_to_database(service_info)
                self.logger.info(f"Discovered service: {service_name}")
                
        except Exception as e:
            self.logger.error(f"Error discovering service in {service_dir}: {e}")
    
    async def _extract_service_info(self, service_dir: Path) -> Optional[ServiceInfo]:
        """Extract service information from service directory."""
        try:
            service_name = service_dir.name
            service_id = service_name
            
            # Default values
            port = 8000
            template_type = "unknown"
            description = None
            version = None
            
            # Try to read configuration
            config_file = service_dir / "config.py"
            if config_file.exists():
                config_content = config_file.read_text()
                # Simple parsing for port
                for line in config_content.split('\n'):
                    if 'PORT' in line and '=' in line:
                        try:
                            port = int(line.split('=')[1].strip().strip('"\''))
                        except:
                            pass
            
            # Try to read README for description
            readme_file = service_dir / "README.md"
            if readme_file.exists():
                readme_content = readme_file.read_text()
                lines = readme_content.split('\n')
                # Look for the first non-empty line after the title
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() and not line.startswith('#'):
                        description = line.strip()
                        break
            
            # Try to determine template type from structure
            if (service_dir / "app" / "auth.py").exists():
                template_type = "auth_service"
            elif (service_dir / "app" / "gateway.py").exists():
                template_type = "api_gateway"
            elif (service_dir / "app" / "models").exists():
                template_type = "data_service"
            else:
                template_type = "base"
            
            # Get creation time
            created_at = datetime.fromtimestamp(service_dir.stat().st_ctime)
            
            # Check if service is running
            status = await self._check_service_status(service_id, port)
            health_status = await self._check_service_health(service_id, port)
            
            # Get resource usage
            resource_usage = await self._get_service_resource_usage(service_id)
            
            return ServiceInfo(
                id=service_id,
                name=service_name,
                template_type=template_type,
                status=status,
                port=port,
                created_at=created_at,
                last_updated=datetime.utcnow(),
                health_status=health_status,
                resource_usage=resource_usage,
                description=description,
                version=version
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting service info from {service_dir}: {e}")
            return None
    
    async def _check_service_status(self, service_id: str, port: int) -> ServiceStatus:
        """Check if a service is currently running."""
        try:
            # Check if process is running on the port
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # Get connections separately to handle access issues
                    connections = proc.connections()
                    if connections:
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr.port == port and conn.status == 'LISTEN':
                                return ServiceStatus.RUNNING
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    continue
            
            return ServiceStatus.STOPPED
            
        except Exception as e:
            self.logger.error(f"Error checking service status for {service_id}: {e}")
            return ServiceStatus.UNKNOWN
    
    async def _check_service_health(self, service_id: str, port: int) -> HealthStatus:
        """Check service health by making HTTP request."""
        try:
            import aiohttp
            import asyncio
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{port}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return HealthStatus.HEALTHY
                        else:
                            return HealthStatus.DEGRADED
                except asyncio.TimeoutError:
                    return HealthStatus.DEGRADED
                except aiohttp.ClientError:
                    # Try root endpoint
                    try:
                        async with session.get(
                            f"http://localhost:{port}/",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status < 500:
                                return HealthStatus.HEALTHY
                            else:
                                return HealthStatus.DEGRADED
                    except:
                        return HealthStatus.UNHEALTHY
                        
        except ImportError:
            # aiohttp not available, use basic check
            status = await self._check_service_status(service_id, port)
            if status == ServiceStatus.RUNNING:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
        except Exception as e:
            self.logger.error(f"Error checking service health for {service_id}: {e}")
            return HealthStatus.UNKNOWN
    
    async def _get_service_resource_usage(self, service_id: str) -> ResourceUsage:
        """Get resource usage for a service."""
        try:
            # Find process by service name or port
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info.get('name', '')
                    if service_id in proc_name:
                        cpu_percent = proc.cpu_percent()
                        memory_info = proc.memory_info()
                        memory_mb = memory_info.rss / 1024 / 1024
                        
                        return ResourceUsage(
                            cpu_percent=cpu_percent,
                            memory_mb=memory_mb
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                    continue
            
            return ResourceUsage()
            
        except Exception as e:
            self.logger.error(f"Error getting resource usage for {service_id}: {e}")
            return ResourceUsage()
    
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checking."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Update health status for all services
                for service_id, service_info in self._services.items():
                    health_status = await self._check_service_health(service_id, service_info.port)
                    status = await self._check_service_status(service_id, service_info.port)
                    resource_usage = await self._get_service_resource_usage(service_id)
                    
                    # Update service info
                    service_info.health_status = health_status
                    service_info.status = status
                    service_info.resource_usage = resource_usage
                    service_info.last_updated = datetime.utcnow()
                    
                    # Save to database
                    await self._save_service_to_database(service_info)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
    
    async def _list_services_impl(self) -> List[ServiceInfo]:
        """Implementation for listing services."""
        return list(self._services.values())
    
    async def _get_service_details_impl(self, service_id: str) -> Optional[ServiceDetails]:
        """Implementation for getting service details."""
        if service_id not in self._services:
            return None
        
        service_info = self._services[service_id]
        service_dir = self._services_directory / service_id
        
        # Get endpoints
        endpoints = [f"http://localhost:{service_info.port}"]
        if service_info.status == ServiceStatus.RUNNING:
            endpoints.extend([
                f"http://localhost:{service_info.port}/docs",
                f"http://localhost:{service_info.port}/health"
            ])
        
        # Get dependencies from requirements.txt
        dependencies = []
        requirements_file = service_dir / "requirements.txt"
        if requirements_file.exists():
            dependencies = requirements_file.read_text().strip().split('\n')
        
        # Get environment variables from .env
        env_vars = {}
        env_file = service_dir / ".env"
        if env_file.exists():
            for line in env_file.read_text().split('\n'):
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        # Get logs path
        logs_path = str(service_dir / "logs") if (service_dir / "logs").exists() else None
        
        return ServiceDetails(
            service_info=service_info,
            endpoints=endpoints,
            dependencies=dependencies,
            environment_variables=env_vars,
            logs_path=logs_path,
            metrics_enabled=True
        )
    
    async def _start_service_impl(self, service_id: str) -> bool:
        """Implementation for starting a service."""
        if service_id not in self._services:
            return False
        
        service_info = self._services[service_id]
        service_dir = self._services_directory / service_id
        
        if not service_dir.exists():
            self.logger.error(f"Service directory not found: {service_dir}")
            return False
        
        try:
            # Update status to starting
            service_info.status = ServiceStatus.STARTING
            service_info.last_updated = datetime.utcnow()
            
            # Find main file
            main_file = service_dir / "main.py"
            if not main_file.exists():
                main_file = service_dir / "app.py"
            
            if not main_file.exists():
                self.logger.error(f"No main.py or app.py found in {service_dir}")
                service_info.status = ServiceStatus.ERROR
                return False
            
            # Start the service process
            process = subprocess.Popen(
                ["python", str(main_file)],
                cwd=str(service_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Store process reference
            self._processes[service_id] = process
            
            # Wait a moment to check if process started successfully
            await asyncio.sleep(2)
            
            if process.poll() is None:  # Process is still running
                service_info.status = ServiceStatus.RUNNING
                service_info.last_updated = datetime.utcnow()
                self.logger.info(f"Service {service_id} started successfully")
                return True
            else:
                # Process exited
                service_info.status = ServiceStatus.ERROR
                service_info.last_updated = datetime.utcnow()
                self.logger.error(f"Service {service_id} failed to start")
                return False
                
        except Exception as e:
            service_info.status = ServiceStatus.ERROR
            service_info.last_updated = datetime.utcnow()
            self.logger.error(f"Error starting service {service_id}: {e}")
            return False
    
    async def _stop_service_impl(self, service_id: str) -> bool:
        """Implementation for stopping a service."""
        if service_id not in self._services:
            return False
        
        service_info = self._services[service_id]
        
        try:
            # Update status to stopping
            service_info.status = ServiceStatus.STOPPING
            service_info.last_updated = datetime.utcnow()
            
            # If we have a process reference, terminate it
            if service_id in self._processes:
                process = self._processes[service_id]
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    
                    # Wait for graceful shutdown
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful shutdown failed
                        process.kill()
                        process.wait()
                
                del self._processes[service_id]
            else:
                # Try to find and kill process by port
                for proc in psutil.process_iter(['pid']):
                    try:
                        connections = proc.connections()
                        if connections:
                            for conn in connections:
                                if hasattr(conn, 'laddr') and conn.laddr.port == service_info.port and conn.status == 'LISTEN':
                                    proc.terminate()
                                    proc.wait(timeout=10)
                                    break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired, AttributeError):
                        continue
            
            service_info.status = ServiceStatus.STOPPED
            service_info.health_status = HealthStatus.UNKNOWN
            service_info.last_updated = datetime.utcnow()
            self.logger.info(f"Service {service_id} stopped successfully")
            return True
            
        except Exception as e:
            service_info.status = ServiceStatus.ERROR
            service_info.last_updated = datetime.utcnow()
            self.logger.error(f"Error stopping service {service_id}: {e}")
            return False
    
    async def _restart_service_impl(self, service_id: str) -> bool:
        """Implementation for restarting a service."""
        # Stop the service first
        stop_success = await self._stop_service_impl(service_id)
        if not stop_success:
            return False
        
        # Wait a moment before starting
        await asyncio.sleep(1)
        
        # Start the service
        return await self._start_service_impl(service_id)
    
    async def _delete_service_impl(self, service_id: str) -> bool:
        """Implementation for deleting a service."""
        if service_id not in self._services:
            return False
        
        try:
            # Stop the service first
            await self._stop_service_impl(service_id)
            
            # Remove service directory
            service_dir = self._services_directory / service_id
            if service_dir.exists():
                import shutil
                shutil.rmtree(service_dir)
            
            # Remove from services dict
            del self._services[service_id]
            
            # Remove from database
            await self._delete_service_from_database(service_id)
            
            self.logger.info(f"Service {service_id} deleted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting service {service_id}: {e}")
            return False
    
    async def _get_service_health_impl(self, service_id: str) -> HealthStatus:
        """Implementation for getting service health."""
        if service_id not in self._services:
            return HealthStatus.UNKNOWN
        
        service_info = self._services[service_id]
        return await self._check_service_health(service_id, service_info.port)
    
    async def _shutdown_impl(self) -> None:
        """Shutdown implementation."""
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop all running processes
        for service_id, process in self._processes.items():
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass
        
        self._processes.clear()
    
    async def _load_services_from_database(self) -> None:
        """Load services from database."""
        if not self._db_manager:
            return
        
        try:
            with self._db_manager.session_scope() as session:
                repository = ServiceRepository(session)
                service_models = repository.get_all_services()
                
                for service_model in service_models:
                    service_info = repository.service_model_to_info(service_model)
                    self._services[service_info.id] = service_info
                
                self.logger.info(f"Loaded {len(service_models)} services from database")
                
        except Exception as e:
            self.logger.error(f"Error loading services from database: {e}")
    
    async def _save_service_to_database(self, service_info: ServiceInfo) -> bool:
        """Save service to database."""
        if not self._db_manager:
            return True  # Skip if database not enabled
        
        try:
            with self._db_manager.session_scope() as session:
                repository = ServiceRepository(session)
                
                # Check if service exists
                existing_service = repository.get_service_by_id(service_info.id)
                if existing_service:
                    # Update existing service
                    repository.update_service(
                        service_info.id,
                        name=service_info.name,
                        template_type=service_info.template_type,
                        status=service_info.status.value,
                        port=service_info.port,
                        description=service_info.description,
                        version=service_info.version,
                        health_status=service_info.health_status.value,
                        cpu_percent=service_info.resource_usage.cpu_percent,
                        memory_mb=service_info.resource_usage.memory_mb,
                        disk_mb=service_info.resource_usage.disk_mb,
                        network_in_mb=service_info.resource_usage.network_in_mb,
                        network_out_mb=service_info.resource_usage.network_out_mb,
                        config=service_info.config
                    )
                else:
                    # Create new service
                    repository.create_service(service_info)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving service to database: {e}")
            return False
    
    async def _delete_service_from_database(self, service_id: str) -> bool:
        """Delete service from database."""
        if not self._db_manager:
            return True  # Skip if database not enabled
        
        try:
            with self._db_manager.session_scope() as session:
                repository = ServiceRepository(session)
                return repository.delete_service(service_id)
                
        except Exception as e:
            self.logger.error(f"Error deleting service from database: {e}")
            return False
    
    def get_repository(self) -> Optional[ServiceRepository]:
        """Get service repository instance."""
        if not self._db_manager:
            return None
        
        session = self._db_manager.get_session()
        return ServiceRepository(session)
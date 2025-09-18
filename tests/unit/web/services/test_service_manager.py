"""
Unit tests for ServiceManager.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from fastapi_microservices_sdk.web.services.service_manager import (
    ServiceManager,
    ServiceInfo,
    ServiceDetails,
    ServiceStatus,
    HealthStatus,
    ResourceUsage
)


@pytest.fixture
def temp_services_dir():
    """Create a temporary services directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def service_manager(temp_services_dir):
    """Create a ServiceManager instance with temporary directory."""
    config = {
        "services_directory": str(temp_services_dir),
        "health_check_interval": 1
    }
    return ServiceManager("test_service", config)


@pytest.fixture
def sample_service_dir(temp_services_dir):
    """Create a sample service directory."""
    service_dir = temp_services_dir / "test-service"
    service_dir.mkdir()
    
    # Create main.py
    main_file = service_dir / "main.py"
    main_file.write_text("""
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
""")
    
    # Create config.py
    config_file = service_dir / "config.py"
    config_file.write_text("""
PORT = 8000
DEBUG = True
""")
    
    # Create requirements.txt
    requirements_file = service_dir / "requirements.txt"
    requirements_file.write_text("""
fastapi==0.104.1
uvicorn==0.24.0
""")
    
    # Create README.md
    readme_file = service_dir / "README.md"
    readme_file.write_text("""
# Test Service
A test service for unit testing
""")
    
    return service_dir


class TestServiceManager:
    """Test cases for ServiceManager."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, service_manager):
        """Test ServiceManager initialization."""
        assert not service_manager.is_initialized()
        
        success = await service_manager.initialize()
        assert success
        assert service_manager.is_initialized()
    
    @pytest.mark.asyncio
    async def test_service_discovery(self, service_manager, sample_service_dir):
        """Test service discovery functionality."""
        await service_manager.initialize()
        
        services = await service_manager.list_services()
        assert len(services) == 1
        
        service = services[0]
        assert service.name == "test-service"
        assert service.port == 8000
        assert service.template_type == "base"
        assert service.description == "A test service for unit testing"
    
    @pytest.mark.asyncio
    async def test_get_service_details(self, service_manager, sample_service_dir):
        """Test getting service details."""
        await service_manager.initialize()
        
        details = await service_manager.get_service_details("test-service")
        assert details is not None
        assert details.service_info.name == "test-service"
        assert "http://localhost:8000" in details.endpoints
        assert "fastapi==0.104.1" in details.dependencies
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_service_details(self, service_manager):
        """Test getting details for nonexistent service."""
        await service_manager.initialize()
        
        details = await service_manager.get_service_details("nonexistent")
        assert details is None
    
    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_service_success(self, mock_popen, service_manager, sample_service_dir):
        """Test successful service start."""
        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process is running
        mock_popen.return_value = mock_process
        
        await service_manager.initialize()
        
        success = await service_manager.start_service("test-service")
        assert success
        
        # Check service status
        services = await service_manager.list_services()
        service = next(s for s in services if s.name == "test-service")
        assert service.status == ServiceStatus.RUNNING
    
    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    async def test_start_service_failure(self, mock_popen, service_manager, sample_service_dir):
        """Test service start failure."""
        # Mock process that exits immediately
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited with error
        mock_popen.return_value = mock_process
        
        await service_manager.initialize()
        
        success = await service_manager.start_service("test-service")
        assert not success
        
        # Check service status
        services = await service_manager.list_services()
        service = next(s for s in services if s.name == "test-service")
        assert service.status == ServiceStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_start_nonexistent_service(self, service_manager):
        """Test starting nonexistent service."""
        await service_manager.initialize()
        
        success = await service_manager.start_service("nonexistent")
        assert not success
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_stop_service_success(self, mock_process_iter, service_manager, sample_service_dir):
        """Test successful service stop."""
        # Mock running process
        mock_process = Mock()
        mock_conn = Mock()
        mock_conn.laddr.port = 8000
        mock_conn.status = 'LISTEN'
        mock_process.connections.return_value = [mock_conn]
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        mock_process_iter.return_value = [mock_process]
        
        await service_manager.initialize()
        
        # Set service as running first
        services = await service_manager.list_services()
        service = services[0]
        service.status = ServiceStatus.RUNNING
        
        success = await service_manager.stop_service("test-service")
        assert success
        
        # Check service status
        services = await service_manager.list_services()
        service = next(s for s in services if s.name == "test-service")
        assert service.status == ServiceStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_service(self, service_manager):
        """Test stopping nonexistent service."""
        await service_manager.initialize()
        
        success = await service_manager.stop_service("nonexistent")
        assert not success
    
    @pytest.mark.asyncio
    @patch('fastapi_microservices_sdk.web.services.service_manager.ServiceManager._stop_service_impl')
    @patch('fastapi_microservices_sdk.web.services.service_manager.ServiceManager._start_service_impl')
    async def test_restart_service(self, mock_start, mock_stop, service_manager, sample_service_dir):
        """Test service restart."""
        mock_stop.return_value = True
        mock_start.return_value = True
        
        await service_manager.initialize()
        
        success = await service_manager.restart_service("test-service")
        assert success
        
        mock_stop.assert_called_once_with("test-service")
        mock_start.assert_called_once_with("test-service")
    
    @pytest.mark.asyncio
    @patch('fastapi_microservices_sdk.web.services.service_manager.ServiceManager._stop_service_impl')
    async def test_restart_service_stop_failure(self, mock_stop, service_manager, sample_service_dir):
        """Test service restart when stop fails."""
        mock_stop.return_value = False
        
        await service_manager.initialize()
        
        success = await service_manager.restart_service("test-service")
        assert not success
    
    @pytest.mark.asyncio
    @patch('shutil.rmtree')
    @patch('fastapi_microservices_sdk.web.services.service_manager.ServiceManager._stop_service_impl')
    async def test_delete_service(self, mock_stop, mock_rmtree, service_manager, sample_service_dir):
        """Test service deletion."""
        mock_stop.return_value = True
        
        await service_manager.initialize()
        
        # Verify service exists
        services = await service_manager.list_services()
        assert len(services) == 1
        
        success = await service_manager.delete_service("test-service")
        assert success
        
        # Verify service is removed
        services = await service_manager.list_services()
        assert len(services) == 0
        
        mock_stop.assert_called_once_with("test-service")
        mock_rmtree.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_service(self, service_manager):
        """Test deleting nonexistent service."""
        await service_manager.initialize()
        
        success = await service_manager.delete_service("nonexistent")
        assert not success
    
    @pytest.mark.asyncio
    async def test_get_service_health_healthy(self, service_manager, sample_service_dir):
        """Test getting healthy service health status."""
        await service_manager.initialize()
        
        # Mock the health check method directly
        with patch.object(service_manager, '_check_service_health') as mock_health_check:
            mock_health_check.return_value = HealthStatus.HEALTHY
            
            health = await service_manager.get_service_health("test-service")
            assert health == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_get_service_health_unhealthy(self, service_manager, sample_service_dir):
        """Test getting unhealthy service health status."""
        await service_manager.initialize()
        
        # Mock the health check method directly
        with patch.object(service_manager, '_check_service_health') as mock_health_check:
            mock_health_check.return_value = HealthStatus.UNHEALTHY
            
            health = await service_manager.get_service_health("test-service")
            assert health == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_get_health_nonexistent_service(self, service_manager):
        """Test getting health for nonexistent service."""
        await service_manager.initialize()
        
        health = await service_manager.get_service_health("nonexistent")
        assert health == HealthStatus.UNKNOWN
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_check_service_status_running(self, mock_process_iter, service_manager):
        """Test checking running service status."""
        # Mock running process
        mock_process = Mock()
        mock_process.info = {'name': 'python'}
        mock_conn = Mock()
        mock_conn.laddr.port = 8000
        mock_conn.status = 'LISTEN'
        mock_process.connections.return_value = [mock_conn]
        mock_process_iter.return_value = [mock_process]
        
        await service_manager.initialize()
        
        status = await service_manager._check_service_status("test-service", 8000)
        assert status == ServiceStatus.RUNNING
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_check_service_status_stopped(self, mock_process_iter, service_manager):
        """Test checking stopped service status."""
        # Mock no running processes
        mock_process_iter.return_value = []
        
        await service_manager.initialize()
        
        status = await service_manager._check_service_status("test-service", 8000)
        assert status == ServiceStatus.STOPPED
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_get_service_resource_usage(self, mock_process_iter, service_manager):
        """Test getting service resource usage."""
        # Mock process with resource usage
        mock_process = Mock()
        mock_process.info = {'name': 'test-service'}
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = Mock(rss=1024*1024*100)  # 100MB
        mock_process_iter.return_value = [mock_process]
        
        await service_manager.initialize()
        
        usage = await service_manager._get_service_resource_usage("test-service")
        assert usage.cpu_percent == 25.5
        assert usage.memory_mb == 100.0
    
    @pytest.mark.asyncio
    async def test_extract_service_info_auth_service(self, temp_services_dir):
        """Test extracting service info for auth service."""
        # Create auth service structure
        service_dir = temp_services_dir / "auth-service"
        service_dir.mkdir()
        (service_dir / "main.py").write_text("# Auth service")
        (service_dir / "app").mkdir()
        (service_dir / "app" / "auth.py").write_text("# Auth module")
        
        service_manager = ServiceManager("test", {"services_directory": str(temp_services_dir)})
        await service_manager.initialize()
        
        service_info = await service_manager._extract_service_info(service_dir)
        assert service_info is not None
        assert service_info.template_type == "auth_service"
    
    @pytest.mark.asyncio
    async def test_extract_service_info_api_gateway(self, temp_services_dir):
        """Test extracting service info for API gateway."""
        # Create API gateway structure
        service_dir = temp_services_dir / "api-gateway"
        service_dir.mkdir()
        (service_dir / "main.py").write_text("# API Gateway")
        (service_dir / "app").mkdir()
        (service_dir / "app" / "gateway.py").write_text("# Gateway module")
        
        service_manager = ServiceManager("test", {"services_directory": str(temp_services_dir)})
        await service_manager.initialize()
        
        service_info = await service_manager._extract_service_info(service_dir)
        assert service_info is not None
        assert service_info.template_type == "api_gateway"
    
    @pytest.mark.asyncio
    async def test_extract_service_info_data_service(self, temp_services_dir):
        """Test extracting service info for data service."""
        # Create data service structure
        service_dir = temp_services_dir / "data-service"
        service_dir.mkdir()
        (service_dir / "main.py").write_text("# Data service")
        (service_dir / "app").mkdir()
        (service_dir / "app" / "models").mkdir()
        (service_dir / "app" / "models" / "__init__.py").write_text("")
        
        service_manager = ServiceManager("test", {"services_directory": str(temp_services_dir)})
        await service_manager.initialize()
        
        service_info = await service_manager._extract_service_info(service_dir)
        assert service_info is not None
        assert service_info.template_type == "data_service"
    
    @pytest.mark.asyncio
    async def test_health_check_loop_cancellation(self, service_manager):
        """Test health check loop cancellation."""
        await service_manager.initialize()
        
        # Health check task should be running
        assert service_manager._health_check_task is not None
        assert not service_manager._health_check_task.done()
        
        # Shutdown should cancel the task
        await service_manager.shutdown()
        
        # Task should be cancelled
        assert service_manager._health_check_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service_manager):
        """Test error handling in service operations."""
        await service_manager.initialize()
        
        # Test starting a service that doesn't exist - this should return False but not add errors
        # since it's handled gracefully
        success = await service_manager.start_service("nonexistent-service")
        assert not success
        
        # Test an operation that would cause an actual error
        with patch.object(service_manager, '_start_service_impl', side_effect=Exception("Test error")):
            success = await service_manager.start_service("test-service")
            assert success is False  # start_service converts None to False
        
        # Check that errors are logged
        errors = service_manager.get_errors()
        assert len(errors) > 0
    
    @pytest.mark.asyncio
    async def test_config_parsing(self, temp_services_dir):
        """Test configuration parsing from service files."""
        service_dir = temp_services_dir / "config-test"
        service_dir.mkdir()
        (service_dir / "main.py").write_text("# Test service")
        
        # Create config with different port
        config_file = service_dir / "config.py"
        config_file.write_text("""
DEBUG = True
PORT = 9000
DATABASE_URL = "sqlite:///test.db"
""")
        
        service_manager = ServiceManager("test", {"services_directory": str(temp_services_dir)})
        await service_manager.initialize()
        
        service_info = await service_manager._extract_service_info(service_dir)
        assert service_info is not None
        assert service_info.port == 9000
    
    @pytest.mark.asyncio
    async def test_environment_variables_parsing(self, temp_services_dir):
        """Test environment variables parsing."""
        service_dir = temp_services_dir / "env-test"
        service_dir.mkdir()
        (service_dir / "main.py").write_text("# Test service")
        
        # Create .env file
        env_file = service_dir / ".env"
        env_file.write_text("""
DEBUG=true
DATABASE_URL=postgresql://localhost/test
SECRET_KEY=test-secret
# This is a comment
EMPTY_VALUE=
""")
        
        service_manager = ServiceManager("test", {"services_directory": str(temp_services_dir)})
        await service_manager.initialize()
        
        details = await service_manager.get_service_details("env-test")
        assert details is not None
        
        env_vars = details.environment_variables
        assert env_vars["DEBUG"] == "true"
        assert env_vars["DATABASE_URL"] == "postgresql://localhost/test"
        assert env_vars["SECRET_KEY"] == "test-secret"
        assert "EMPTY_VALUE" in env_vars
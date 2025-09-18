"""
Unit tests for ServiceRepository.
"""

import pytest
import tempfile
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi_microservices_sdk.web.services.models import Base, ServiceModel
from fastapi_microservices_sdk.web.services.repository import ServiceRepository
from fastapi_microservices_sdk.web.services.types import (
    ServiceInfo, ServiceStatus, HealthStatus, ResourceUsage
)


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def repository(db_session):
    """Create a ServiceRepository instance."""
    return ServiceRepository(db_session)


@pytest.fixture
def sample_service_info():
    """Create a sample ServiceInfo object."""
    return ServiceInfo(
        id="test-service",
        name="Test Service",
        template_type="base",
        status=ServiceStatus.STOPPED,
        port=8000,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow(),
        health_status=HealthStatus.UNKNOWN,
        resource_usage=ResourceUsage(
            cpu_percent=25.5,
            memory_mb=128.0,
            disk_mb=512.0
        ),
        description="A test service",
        version="1.0.0"
    )


class TestServiceRepository:
    """Test cases for ServiceRepository."""
    
    def test_create_service(self, repository, sample_service_info):
        """Test creating a service."""
        service_model = repository.create_service(sample_service_info)
        
        assert service_model.id == sample_service_info.id
        assert service_model.name == sample_service_info.name
        assert service_model.template_type == sample_service_info.template_type
        assert service_model.status == sample_service_info.status.value
        assert service_model.port == sample_service_info.port
        assert service_model.description == sample_service_info.description
        assert service_model.version == sample_service_info.version
        assert service_model.health_status == sample_service_info.health_status.value
        assert service_model.cpu_percent == sample_service_info.resource_usage.cpu_percent
        assert service_model.memory_mb == sample_service_info.resource_usage.memory_mb
    
    def test_get_service_by_id(self, repository, sample_service_info):
        """Test getting service by ID."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Get service by ID
        service_model = repository.get_service_by_id(sample_service_info.id)
        assert service_model is not None
        assert service_model.id == sample_service_info.id
        assert service_model.name == sample_service_info.name
    
    def test_get_service_by_id_not_found(self, repository):
        """Test getting service by ID when not found."""
        service_model = repository.get_service_by_id("nonexistent")
        assert service_model is None
    
    def test_get_service_by_name(self, repository, sample_service_info):
        """Test getting service by name."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Get service by name
        service_model = repository.get_service_by_name(sample_service_info.name)
        assert service_model is not None
        assert service_model.name == sample_service_info.name
        assert service_model.id == sample_service_info.id
    
    def test_get_all_services(self, repository, sample_service_info):
        """Test getting all services."""
        # Create multiple services
        service1 = sample_service_info
        repository.create_service(service1)
        
        service2 = ServiceInfo(
            id="test-service-2",
            name="Test Service 2",
            template_type="api_gateway",
            status=ServiceStatus.RUNNING,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.HEALTHY,
            resource_usage=ResourceUsage()
        )
        repository.create_service(service2)
        
        # Get all services
        services = repository.get_all_services()
        assert len(services) == 2
        
        service_ids = [s.id for s in services]
        assert service1.id in service_ids
        assert service2.id in service_ids
    
    def test_get_all_services_with_pagination(self, repository, sample_service_info):
        """Test getting all services with pagination."""
        # Create multiple services
        for i in range(5):
            service = ServiceInfo(
                id=f"test-service-{i}",
                name=f"Test Service {i}",
                template_type="base",
                status=ServiceStatus.STOPPED,
                port=8000 + i,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                health_status=HealthStatus.UNKNOWN,
                resource_usage=ResourceUsage()
            )
            repository.create_service(service)
        
        # Test pagination
        services_page1 = repository.get_all_services(skip=0, limit=3)
        assert len(services_page1) == 3
        
        services_page2 = repository.get_all_services(skip=3, limit=3)
        assert len(services_page2) == 2
    
    def test_get_services_by_status(self, repository, sample_service_info):
        """Test getting services by status."""
        # Create services with different statuses
        service1 = sample_service_info  # STOPPED
        repository.create_service(service1)
        
        service2 = ServiceInfo(
            id="test-service-2",
            name="Test Service 2",
            template_type="base",
            status=ServiceStatus.RUNNING,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.HEALTHY,
            resource_usage=ResourceUsage()
        )
        repository.create_service(service2)
        
        # Get services by status
        stopped_services = repository.get_services_by_status(ServiceStatus.STOPPED)
        assert len(stopped_services) == 1
        assert stopped_services[0].id == service1.id
        
        running_services = repository.get_services_by_status(ServiceStatus.RUNNING)
        assert len(running_services) == 1
        assert running_services[0].id == service2.id
    
    def test_get_services_by_template_type(self, repository, sample_service_info):
        """Test getting services by template type."""
        # Create services with different template types
        service1 = sample_service_info  # base
        repository.create_service(service1)
        
        service2 = ServiceInfo(
            id="test-service-2",
            name="Test Service 2",
            template_type="api_gateway",
            status=ServiceStatus.STOPPED,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.UNKNOWN,
            resource_usage=ResourceUsage()
        )
        repository.create_service(service2)
        
        # Get services by template type
        base_services = repository.get_services_by_template_type("base")
        assert len(base_services) == 1
        assert base_services[0].id == service1.id
        
        gateway_services = repository.get_services_by_template_type("api_gateway")
        assert len(gateway_services) == 1
        assert gateway_services[0].id == service2.id
    
    def test_update_service(self, repository, sample_service_info):
        """Test updating service information."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Update service
        updated_service = repository.update_service(
            sample_service_info.id,
            description="Updated description",
            version="2.0.0",
            port=9000
        )
        
        assert updated_service is not None
        assert updated_service.description == "Updated description"
        assert updated_service.version == "2.0.0"
        assert updated_service.port == 9000
    
    def test_update_service_status(self, repository, sample_service_info):
        """Test updating service status."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Update status
        success = repository.update_service_status(
            sample_service_info.id,
            ServiceStatus.RUNNING,
            HealthStatus.HEALTHY
        )
        
        assert success
        
        # Verify update
        service = repository.get_service_by_id(sample_service_info.id)
        assert service.status == ServiceStatus.RUNNING.value
        assert service.health_status == HealthStatus.HEALTHY.value
    
    def test_update_service_resources(self, repository, sample_service_info):
        """Test updating service resource usage."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Update resources
        new_resources = ResourceUsage(
            cpu_percent=50.0,
            memory_mb=256.0,
            disk_mb=1024.0,
            network_in_mb=10.0,
            network_out_mb=5.0
        )
        
        success = repository.update_service_resources(sample_service_info.id, new_resources)
        assert success
        
        # Verify update
        service = repository.get_service_by_id(sample_service_info.id)
        assert service.cpu_percent == 50.0
        assert service.memory_mb == 256.0
        assert service.disk_mb == 1024.0
        assert service.network_in_mb == 10.0
        assert service.network_out_mb == 5.0
    
    def test_delete_service(self, repository, sample_service_info):
        """Test deleting service."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Verify service exists
        service = repository.get_service_by_id(sample_service_info.id)
        assert service is not None
        
        # Delete service
        success = repository.delete_service(sample_service_info.id)
        assert success
        
        # Verify service is deleted
        service = repository.get_service_by_id(sample_service_info.id)
        assert service is None
    
    def test_search_services(self, repository, sample_service_info):
        """Test searching services."""
        # Create services with different names and descriptions
        service1 = sample_service_info
        repository.create_service(service1)
        
        service2 = ServiceInfo(
            id="auth-service",
            name="Authentication Service",
            template_type="auth_service",
            status=ServiceStatus.STOPPED,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.UNKNOWN,
            resource_usage=ResourceUsage(),
            description="Handles user authentication"
        )
        repository.create_service(service2)
        
        # Search by name
        results = repository.search_services("Test")
        assert len(results) == 1
        assert results[0].id == service1.id
        
        # Search by description
        results = repository.search_services("authentication")
        assert len(results) == 1
        assert results[0].id == service2.id
        
        # Search with no matches
        results = repository.search_services("nonexistent")
        assert len(results) == 0
    
    def test_count_services(self, repository, sample_service_info):
        """Test counting services."""
        # Initially no services
        count = repository.count_services()
        assert count == 0
        
        # Create services
        repository.create_service(sample_service_info)
        
        service2 = ServiceInfo(
            id="test-service-2",
            name="Test Service 2",
            template_type="base",
            status=ServiceStatus.RUNNING,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.HEALTHY,
            resource_usage=ResourceUsage()
        )
        repository.create_service(service2)
        
        # Count services
        count = repository.count_services()
        assert count == 2
    
    def test_count_services_by_status(self, repository, sample_service_info):
        """Test counting services by status."""
        # Create services with different statuses
        service1 = sample_service_info  # STOPPED
        repository.create_service(service1)
        
        service2 = ServiceInfo(
            id="test-service-2",
            name="Test Service 2",
            template_type="base",
            status=ServiceStatus.RUNNING,
            port=8001,
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            health_status=HealthStatus.HEALTHY,
            resource_usage=ResourceUsage()
        )
        repository.create_service(service2)
        
        # Count by status
        stopped_count = repository.count_services_by_status(ServiceStatus.STOPPED)
        assert stopped_count == 1
        
        running_count = repository.count_services_by_status(ServiceStatus.RUNNING)
        assert running_count == 1
        
        starting_count = repository.count_services_by_status(ServiceStatus.STARTING)
        assert starting_count == 0
    
    def test_service_model_to_info(self, repository, sample_service_info):
        """Test converting ServiceModel to ServiceInfo."""
        # Create service
        service_model = repository.create_service(sample_service_info)
        
        # Convert back to ServiceInfo
        service_info = repository.service_model_to_info(service_model)
        
        assert service_info.id == sample_service_info.id
        assert service_info.name == sample_service_info.name
        assert service_info.template_type == sample_service_info.template_type
        assert service_info.status == sample_service_info.status
        assert service_info.port == sample_service_info.port
        assert service_info.description == sample_service_info.description
        assert service_info.version == sample_service_info.version
        assert service_info.health_status == sample_service_info.health_status
        assert service_info.resource_usage.cpu_percent == sample_service_info.resource_usage.cpu_percent
        assert service_info.resource_usage.memory_mb == sample_service_info.resource_usage.memory_mb
    
    def test_create_service_configuration(self, repository, sample_service_info):
        """Test creating service configuration."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Create configuration
        config_data = {
            "debug": True,
            "database_url": "sqlite:///test.db",
            "api_key": "test-key"
        }
        
        config_model = repository.create_service_configuration(
            sample_service_info.id,
            config_data,
            created_by="test_user",
            description="Initial configuration"
        )
        
        assert config_model.service_id == sample_service_info.id
        assert config_model.configuration == config_data
        assert config_model.version == 1
        assert config_model.created_by == "test_user"
        assert config_model.description == "Initial configuration"
        assert config_model.is_active == True
    
    def test_get_service_configuration(self, repository, sample_service_info):
        """Test getting service configuration."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Create configuration
        config_data = {"debug": True}
        repository.create_service_configuration(sample_service_info.id, config_data)
        
        # Get active configuration
        config = repository.get_service_configuration(sample_service_info.id)
        assert config is not None
        assert config.configuration == config_data
        assert config.is_active == True
        
        # Get specific version
        config_v1 = repository.get_service_configuration(sample_service_info.id, version=1)
        assert config_v1 is not None
        assert config_v1.version == 1
    
    def test_service_configuration_versioning(self, repository, sample_service_info):
        """Test service configuration versioning."""
        # Create service first
        repository.create_service(sample_service_info)
        
        # Create first configuration
        config1 = {"debug": True}
        repository.create_service_configuration(sample_service_info.id, config1)
        
        # Create second configuration
        config2 = {"debug": False, "port": 9000}
        repository.create_service_configuration(sample_service_info.id, config2)
        
        # Get configuration history
        history = repository.get_service_configuration_history(sample_service_info.id)
        assert len(history) == 2
        
        # Latest should be version 2
        latest = history[0]
        assert latest.version == 2
        assert latest.configuration == config2
        assert latest.is_active == True
        
        # Previous should be version 1 and inactive
        previous = history[1]
        assert previous.version == 1
        assert previous.configuration == config1
        assert previous.is_active == False
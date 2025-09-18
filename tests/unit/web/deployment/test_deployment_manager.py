"""
Tests for DeploymentManager with multi-target support.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from fastapi_microservices_sdk.web.deployment.deployment_manager import (
    DeploymentManager,
    DeploymentConfig,
    DeploymentType,
    DeploymentStatus,
    DeploymentStage,
    ResourceRequirements,
    NetworkConfig,
    SecurityConfig,
    DeploymentProgress
)


class TestDeploymentManager:
    """Test cases for DeploymentManager."""
    
    @pytest.fixture
    def config(self):
        """Deployment manager configuration."""
        return {
            "docker_registry": "test-registry:5000",
            "kubernetes_context": "test-context",
            "build_timeout": 300,
            "deploy_timeout": 600,
            "health_check_timeout": 120
        }
    
    @pytest.fixture
    def manager(self, config):
        """Create deployment manager instance."""
        return DeploymentManager("test_deployment", config)
    
    @pytest.fixture
    def deployment_config(self):
        """Create test deployment configuration."""
        return DeploymentConfig(
            service_id="test-service",
            target_environment="staging",
            deployment_type=DeploymentType.KUBERNETES,
            image="nginx",
            tag="1.21",
            configuration={},
            resources=ResourceRequirements(
                cpu="200m",
                memory="256Mi",
                replicas=2
            ),
            network=NetworkConfig(
                ports=[{"containerPort": 80, "hostPort": 8080}]
            ),
            security=SecurityConfig(
                image_pull_secrets=["regcred"]
            ),
            environment_variables={
                "ENV": "staging",
                "DEBUG": "false"
            }
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """Test deployment manager initialization."""
        with patch('subprocess.run') as mock_run:
            # Mock successful tool checks
            mock_run.return_value.returncode = 0
            
            await manager.initialize()
            
            assert manager.is_initialized()
            assert DeploymentType.DOCKER in manager._deployment_providers
            assert DeploymentType.KUBERNETES in manager._deployment_providers
            assert DeploymentType.CLOUD_RUN in manager._deployment_providers
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_validate_deployment_config_valid(self, manager, deployment_config):
        """Test deployment configuration validation with valid config."""
        await manager.initialize()
        
        result = await manager.validate_deployment_config(deployment_config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert "validated_at" in result
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_validate_deployment_config_invalid(self, manager):
        """Test deployment configuration validation with invalid config."""
        await manager.initialize()
        
        # Create invalid config
        invalid_config = DeploymentConfig(
            service_id="",  # Empty service ID
            target_environment="",  # Empty environment
            deployment_type=DeploymentType.DOCKER,
            image="",  # Empty image
            resources=ResourceRequirements(replicas=0)  # Invalid replicas
        )
        
        result = await manager.validate_deployment_config(invalid_config)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "Service ID is required" in result["errors"]
        assert "Container image is required" in result["errors"]
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_deploy_service_kubernetes(self, manager, deployment_config):
        """Test Kubernetes service deployment."""
        await manager.initialize()
        
        # Mock progress callback
        progress_updates = []
        def progress_callback(deployment_id, progress):
            progress_updates.append((deployment_id, progress.stage, progress.message))
        
        manager.add_progress_callback(progress_callback)
        
        # Start deployment
        deployment_id = await manager.deploy_service(deployment_config)
        
        assert deployment_id
        assert deployment_id in manager._deployments
        
        # Wait for deployment to complete
        await asyncio.sleep(0.1)  # Let the pipeline start
        
        # Check initial status
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment is not None
        assert deployment.service_id == "test-service"
        assert deployment.deployment_type == DeploymentType.KUBERNETES
        assert deployment.status in [DeploymentStatus.PENDING, DeploymentStatus.VALIDATING, 
                                    DeploymentStatus.IN_PROGRESS]
        
        # Wait for completion (with timeout)
        max_wait = 50  # 5 seconds
        wait_count = 0
        while wait_count < max_wait:
            deployment = await manager.get_deployment_status(deployment_id)
            if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
                break
            await asyncio.sleep(0.1)
            wait_count += 1
        
        # Check final status
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.COMPLETED
        assert len(deployment.logs) > 0
        assert len(deployment.progress) > 0
        assert deployment.health_status == "healthy"
        assert deployment.deployment_url is not None
        
        # Check progress updates
        assert len(progress_updates) > 0
        stages = [update[1] for update in progress_updates]
        assert DeploymentStage.VALIDATION in stages
        assert DeploymentStage.DEPLOY in stages
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_deploy_service_docker(self, manager, deployment_config):
        """Test Docker service deployment."""
        await manager.initialize()
        
        # Change to Docker deployment
        deployment_config.deployment_type = DeploymentType.DOCKER
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        assert deployment_id
        
        # Wait for completion
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            deployment = await manager.get_deployment_status(deployment_id)
            if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
                break
            await asyncio.sleep(0.1)
            wait_count += 1
        
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.COMPLETED
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_deploy_service_cloud_run(self, manager, deployment_config):
        """Test Google Cloud Run deployment."""
        await manager.initialize()
        
        deployment_config.deployment_type = DeploymentType.CLOUD_RUN
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait for completion
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            deployment = await manager.get_deployment_status(deployment_id)
            if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
                break
            await asyncio.sleep(0.1)
            wait_count += 1
        
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.COMPLETED
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_cancel_deployment(self, manager, deployment_config):
        """Test deployment cancellation."""
        await manager.initialize()
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait a bit for deployment to start
        await asyncio.sleep(0.1)
        
        # Cancel deployment
        result = await manager.cancel_deployment(deployment_id)
        assert result is True
        
        # Check status
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.CANCELLED
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_rollback_deployment(self, manager, deployment_config):
        """Test deployment rollback."""
        await manager.initialize()
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait for completion
        max_wait = 50
        wait_count = 0
        while wait_count < max_wait:
            deployment = await manager.get_deployment_status(deployment_id)
            if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
                break
            await asyncio.sleep(0.1)
            wait_count += 1
        
        # Rollback
        result = await manager.rollback_deployment(deployment_id)
        assert result is True
        
        # Check status
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.ROLLED_BACK
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_deployment_logs(self, manager, deployment_config):
        """Test getting deployment logs."""
        await manager.initialize()
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait a bit for logs to accumulate
        await asyncio.sleep(0.2)
        
        logs = await manager.get_deployment_logs(deployment_id, lines=10)
        
        assert isinstance(logs, list)
        assert len(logs) > 0
        
        # Test getting all logs
        all_logs = await manager.get_deployment_logs(deployment_id, lines=0)
        assert len(all_logs) >= len(logs)
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_deployment_progress(self, manager, deployment_config):
        """Test getting deployment progress."""
        await manager.initialize()
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait a bit for progress to be recorded
        await asyncio.sleep(0.1)
        
        progress = await manager.get_deployment_progress(deployment_id)
        
        assert progress is not None
        assert isinstance(progress.stage, DeploymentStage)
        assert 0.0 <= progress.progress <= 1.0
        assert progress.message
        assert progress.timestamp
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_list_deployments(self, manager, deployment_config):
        """Test listing deployments."""
        await manager.initialize()
        
        # Deploy multiple services
        deployment_id1 = await manager.deploy_service(deployment_config)
        
        deployment_config.service_id = "test-service-2"
        deployment_id2 = await manager.deploy_service(deployment_config)
        
        # List all deployments
        all_deployments = await manager.list_deployments()
        assert len(all_deployments) == 2
        
        # List deployments for specific service
        service_deployments = await manager.list_deployments(service_id="test-service")
        assert len(service_deployments) == 1
        assert service_deployments[0].service_id == "test-service"
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_progress_callbacks(self, manager, deployment_config):
        """Test progress callback functionality."""
        await manager.initialize()
        
        callback_calls = []
        
        def test_callback(deployment_id, progress):
            callback_calls.append((deployment_id, progress.stage, progress.progress))
        
        # Add callback
        manager.add_progress_callback(test_callback)
        
        deployment_id = await manager.deploy_service(deployment_config)
        
        # Wait for some progress
        await asyncio.sleep(0.2)
        
        assert len(callback_calls) > 0
        
        # Remove callback
        manager.remove_progress_callback(test_callback)
        
        # Verify callback was removed
        assert test_callback not in manager._progress_callbacks
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_deployment_validation_warnings(self, manager, deployment_config):
        """Test deployment validation with warnings."""
        await manager.initialize()
        
        # Create config that generates warnings
        deployment_config.resources.replicas = 50  # High replica count
        deployment_config.security.image_pull_secrets = []  # No secrets for private image
        deployment_config.image = "private-registry/app"
        
        result = await manager.validate_deployment_config(deployment_config)
        
        assert result["valid"] is True  # Should still be valid
        assert len(result["warnings"]) > 0
        assert any("High replica count" in warning for warning in result["warnings"])
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_deployment_with_invalid_config_fails(self, manager):
        """Test that deployment fails with invalid configuration."""
        await manager.initialize()
        
        # Create invalid config
        invalid_config = DeploymentConfig(
            service_id="",
            target_environment="test",
            deployment_type=DeploymentType.DOCKER,
            image=""
        )
        
        deployment_id = await manager.deploy_service(invalid_config)
        
        # Wait for failure
        max_wait = 20
        wait_count = 0
        while wait_count < max_wait:
            deployment = await manager.get_deployment_status(deployment_id)
            if deployment.status == DeploymentStatus.FAILED:
                break
            await asyncio.sleep(0.1)
            wait_count += 1
        
        deployment = await manager.get_deployment_status(deployment_id)
        assert deployment.status == DeploymentStatus.FAILED
        assert deployment.error_message is not None
        assert "validation failed" in deployment.error_message.lower()
        
        await manager.shutdown()


class TestDeploymentDataClasses:
    """Test deployment data classes."""
    
    def test_resource_requirements_creation(self):
        """Test ResourceRequirements creation."""
        resources = ResourceRequirements(
            cpu="500m",
            memory="1Gi",
            replicas=3,
            storage="10Gi",
            gpu="1"
        )
        
        assert resources.cpu == "500m"
        assert resources.memory == "1Gi"
        assert resources.replicas == 3
        assert resources.storage == "10Gi"
        assert resources.gpu == "1"
    
    def test_network_config_creation(self):
        """Test NetworkConfig creation."""
        network = NetworkConfig(
            ports=[
                {"containerPort": 80, "hostPort": 8080},
                {"containerPort": 443, "hostPort": 8443}
            ],
            ingress={"enabled": True, "host": "example.com"},
            load_balancer={"type": "LoadBalancer"}
        )
        
        assert len(network.ports) == 2
        assert network.ingress["enabled"] is True
        assert network.load_balancer["type"] == "LoadBalancer"
    
    def test_security_config_creation(self):
        """Test SecurityConfig creation."""
        security = SecurityConfig(
            image_pull_secrets=["regcred", "dockerhub"],
            service_account="my-service-account",
            security_context={"runAsUser": 1000}
        )
        
        assert len(security.image_pull_secrets) == 2
        assert security.service_account == "my-service-account"
        assert security.security_context["runAsUser"] == 1000
    
    def test_deployment_config_creation(self):
        """Test DeploymentConfig creation."""
        config = DeploymentConfig(
            service_id="my-service",
            target_environment="production",
            deployment_type=DeploymentType.KUBERNETES,
            image="nginx",
            tag="1.21",
            environment_variables={"ENV": "prod"}
        )
        
        assert config.service_id == "my-service"
        assert config.deployment_type == DeploymentType.KUBERNETES
        assert config.environment_variables["ENV"] == "prod"
        assert config.tag == "1.21"
    
    def test_deployment_progress_creation(self):
        """Test DeploymentProgress creation."""
        progress = DeploymentProgress(
            stage=DeploymentStage.BUILD,
            progress=0.75,
            message="Building image...",
            timestamp=datetime.utcnow(),
            details={"step": "docker build"}
        )
        
        assert progress.stage == DeploymentStage.BUILD
        assert progress.progress == 0.75
        assert progress.message == "Building image..."
        assert progress.details["step"] == "docker build"
"""
Cloud Deployment Module for FastAPI Microservices SDK.

This module provides deployment capabilities for major cloud providers:
- AWS ECS (Elastic Container Service)
- Azure Container Instances
- Google Cloud Run

Each provider module includes deployment, management, and monitoring capabilities
for FastAPI microservices with auto-scaling and production-ready configurations.
"""

from typing import Dict, Any, Optional, List
import importlib
from enum import Enum

# Import functions will be done lazily to avoid circular imports


class CloudProvider(Enum):
    """Supported cloud providers."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class CloudDeploymentManager:
    """Unified cloud deployment manager."""
    
    def __init__(self):
        pass
    
    def deploy(self, provider: CloudProvider, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to specified cloud provider."""
        if provider == CloudProvider.AWS:
            from .aws_ecs import deploy_to_aws_ecs
            return deploy_to_aws_ecs(config)
        elif provider == CloudProvider.AZURE:
            from .azure_containers import deploy_to_azure_containers, validate_azure_config
            errors = validate_azure_config(config)
            if errors:
                raise ValueError(f"Configuration validation failed: {errors}")
            return deploy_to_azure_containers(config)
        elif provider == CloudProvider.GCP:
            from .gcp_run import deploy_to_gcp_run, validate_gcp_config
            errors = validate_gcp_config(config)
            if errors:
                raise ValueError(f"Configuration validation failed: {errors}")
            return deploy_to_gcp_run(config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate_config(self, provider: CloudProvider, app_name: str, 
                       image_uri: str, **kwargs) -> Dict[str, Any]:
        """Generate deployment configuration for specified provider."""
        if provider == CloudProvider.AWS:
            from .aws_ecs import generate_ecs_deployment_config
            return generate_ecs_deployment_config(app_name, image_uri)
        elif provider == CloudProvider.AZURE:
            from .azure_containers import generate_azure_deployment_config
            subscription_id = kwargs.get('subscription_id')
            if not subscription_id:
                raise ValueError("subscription_id is required for Azure")
            return generate_azure_deployment_config(app_name, image_uri, subscription_id)
        elif provider == CloudProvider.GCP:
            from .gcp_run import generate_gcp_deployment_config
            project_id = kwargs.get('project_id')
            if not project_id:
                raise ValueError("project_id is required for GCP")
            return generate_gcp_deployment_config(app_name, image_uri, project_id)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def get_deployer(self, provider: CloudProvider, **kwargs) -> Any:
        """Get deployer instance for specified provider."""
        if provider == CloudProvider.AWS:
            from .aws_ecs import AWSECSDeployer
            region = kwargs.get('region', 'us-east-1')
            profile = kwargs.get('profile')
            return AWSECSDeployer(region=region, profile=profile)
        elif provider == CloudProvider.AZURE:
            from .azure_containers import AzureContainerDeployer
            subscription_id = kwargs.get('subscription_id')
            if not subscription_id:
                raise ValueError("subscription_id is required for Azure")
            credential = kwargs.get('credential')
            return AzureContainerDeployer(subscription_id=subscription_id, credential=credential)
        elif provider == CloudProvider.GCP:
            from .gcp_run import GoogleCloudRunDeployer
            project_id = kwargs.get('project_id')
            if not project_id:
                raise ValueError("project_id is required for GCP")
            region = kwargs.get('region', 'us-central1')
            credentials_path = kwargs.get('credentials_path')
            return GoogleCloudRunDeployer(
                project_id=project_id,
                region=region,
                credentials_path=credentials_path
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def list_supported_providers(self) -> List[str]:
        """List supported cloud providers."""
        return [provider.value for provider in CloudProvider]
    
    def get_provider_requirements(self, provider: CloudProvider) -> Dict[str, Any]:
        """Get requirements for specified provider."""
        requirements = {
            CloudProvider.AWS: {
                'packages': ['boto3'],
                'credentials': 'AWS credentials (AWS CLI, IAM roles, or environment variables)',
                'required_config': ['app_name', 'image_uri'],
                'optional_config': ['region', 'profile', 'cpu', 'memory', 'desired_count']
            },
            CloudProvider.AZURE: {
                'packages': ['azure-mgmt-containerinstance', 'azure-mgmt-resource', 'azure-identity'],
                'credentials': 'Azure credentials (Service Principal, Managed Identity, or Azure CLI)',
                'required_config': ['app_name', 'image_uri', 'subscription_id'],
                'optional_config': ['location', 'cpu', 'memory', 'client_id', 'client_secret', 'tenant_id']
            },
            CloudProvider.GCP: {
                'packages': ['google-cloud-run', 'google-cloud-resource-manager'],
                'credentials': 'GCP credentials (Service Account JSON, Application Default Credentials)',
                'required_config': ['app_name', 'image_uri', 'project_id'],
                'optional_config': ['region', 'credentials_path', 'cpu', 'memory', 'min_instances', 'max_instances']
            }
        }
        
        return requirements.get(provider, {})


def deploy_to_cloud(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy FastAPI application to specified cloud provider."""
    try:
        cloud_provider = CloudProvider(provider.lower())
    except ValueError:
        raise ValueError(f"Unsupported provider: {provider}")
    
    manager = CloudDeploymentManager()
    return manager.deploy(cloud_provider, config)


def generate_deployment_config(provider: str, app_name: str, image_uri: str, 
                             **kwargs) -> Dict[str, Any]:
    """Generate deployment configuration for specified provider."""
    try:
        cloud_provider = CloudProvider(provider.lower())
    except ValueError:
        raise ValueError(f"Unsupported provider: {provider}")
    
    manager = CloudDeploymentManager()
    return manager.generate_config(cloud_provider, app_name, image_uri, **kwargs)


def validate_deployment_config(provider: str, config: Dict[str, Any]) -> List[str]:
    """Validate deployment configuration for specified provider."""
    try:
        cloud_provider = CloudProvider(provider.lower())
    except ValueError:
        return [f"Unsupported provider: {provider}"]
    
    if cloud_provider == CloudProvider.AZURE:
        from .azure_containers import validate_azure_config
        return validate_azure_config(config)
    elif cloud_provider == CloudProvider.GCP:
        from .gcp_run import validate_gcp_config
        return validate_gcp_config(config)
    
    return []


def list_cloud_providers() -> List[str]:
    """List all supported cloud providers."""
    return [provider.value for provider in CloudProvider]


def get_provider_info(provider: str) -> Dict[str, Any]:
    """Get information about a specific cloud provider."""
    try:
        cloud_provider = CloudProvider(provider.lower())
    except ValueError:
        return {'error': f"Unsupported provider: {provider}"}
    
    manager = CloudDeploymentManager()
    return manager.get_provider_requirements(cloud_provider)


def check_provider_dependencies(provider: str) -> Dict[str, bool]:
    """Check if required dependencies are installed for a provider."""
    dependencies = {
        'aws': ['boto3'],
        'azure': ['azure.mgmt.containerinstance', 'azure.mgmt.resource', 'azure.identity'],
        'gcp': ['google.cloud.run_v2', 'google.cloud.resourcemanager_v3']
    }
    
    provider_deps = dependencies.get(provider.lower(), [])
    results = {}
    
    for dep in provider_deps:
        try:
            importlib.import_module(dep)
            results[dep] = True
        except ImportError:
            results[dep] = False
    
    return results


# Convenience functions for each provider
def deploy_to_aws(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy to AWS ECS."""
    from .aws_ecs import deploy_to_aws_ecs
    return deploy_to_aws_ecs(config)


def deploy_to_azure(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy to Azure Container Instances."""
    from .azure_containers import deploy_to_azure_containers
    return deploy_to_azure_containers(config)


def deploy_to_gcp(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy to Google Cloud Run."""
    from .gcp_run import deploy_to_gcp_run
    return deploy_to_gcp_run(config)


# Export all public classes and functions
__all__ = [
    # Enums
    'CloudProvider',
    
    # Main classes
    'CloudDeploymentManager',
    
    # Deployment functions
    'deploy_to_cloud',
    'deploy_to_aws',
    'deploy_to_azure', 
    'deploy_to_gcp',
    
    # Configuration functions
    'generate_deployment_config',
    
    # Validation functions
    'validate_deployment_config',
    
    # Utility functions
    'list_cloud_providers',
    'get_provider_info',
    'check_provider_dependencies'
]
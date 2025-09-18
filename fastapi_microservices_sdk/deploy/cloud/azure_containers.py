"""
Azure Container Instances Deployment for FastAPI Microservices.

This module provides deployment capabilities for Azure Container Instances (ACI)
and Azure Container Apps with auto-scaling and load balancing.
"""

import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.mgmt.containerinstance import ContainerInstanceManagementClient
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False


@dataclass
class AzureContainerConfig:
    """Azure Container configuration."""
    name: str
    image: str
    cpu: float = 1.0
    memory: float = 1.5
    port: int = 8000
    environment_variables: Dict[str, str] = field(default_factory=dict)
    restart_policy: str = "Always"
    os_type: str = "Linux"


@dataclass
class AzureResourceGroup:
    """Azure Resource Group configuration."""
    name: str
    location: str = "East US"
    tags: Dict[str, str] = field(default_factory=dict)


class AzureContainerDeployer:
    """Azure Container Instances deployment manager."""
    
    def __init__(self, subscription_id: str, credential=None):
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure SDK is required for Azure deployment. "
                "Install with: pip install azure-mgmt-containerinstance azure-mgmt-resource azure-identity"
            )
        
        self.subscription_id = subscription_id
        self.credential = credential or DefaultAzureCredential()
        
        # Initialize Azure clients
        self.container_client = ContainerInstanceManagementClient(
            self.credential, subscription_id
        )
        self.resource_client = ResourceManagementClient(
            self.credential, subscription_id
        )
        self.network_client = NetworkManagementClient(
            self.credential, subscription_id
        )
    
    def create_resource_group(self, rg_config: AzureResourceGroup) -> Dict[str, Any]:
        """Create Azure Resource Group."""
        try:
            rg_params = {
                'location': rg_config.location,
                'tags': {
                    'CreatedBy': 'FastAPI-Microservices-SDK',
                    **rg_config.tags
                }
            }
            
            result = self.resource_client.resource_groups.create_or_update(
                rg_config.name, rg_params
            )
            
            print(f"✅ Created/Updated resource group: {rg_config.name}")
            return result.as_dict()
            
        except Exception as e:
            raise Exception(f"Failed to create resource group: {e}")
    
    def create_container_group(self, resource_group_name: str, 
                              container_group_name: str,
                              containers: List[AzureContainerConfig],
                              location: str = "East US") -> Dict[str, Any]:
        """Create Azure Container Group."""
        try:
            container_definitions = []
            
            for container in containers:
                container_def = {
                    'name': container.name,
                    'image': container.image,
                    'resources': {
                        'requests': {
                            'cpu': container.cpu,
                            'memory_in_gb': container.memory
                        }
                    },
                    'ports': [
                        {
                            'port': container.port,
                            'protocol': 'TCP'
                        }
                    ],
                    'environment_variables': [
                        {'name': k, 'value': v} 
                        for k, v in container.environment_variables.items()
                    ]
                }
                container_definitions.append(container_def)
            
            # Configure IP address (public)
            ip_address = {
                'type': 'Public',
                'ports': [
                    {
                        'port': containers[0].port,
                        'protocol': 'TCP'
                    }
                ]
            }
            
            container_group_params = {
                'location': location,
                'containers': container_definitions,
                'os_type': containers[0].os_type,
                'restart_policy': containers[0].restart_policy,
                'ip_address': ip_address,
                'tags': {
                    'CreatedBy': 'FastAPI-Microservices-SDK'
                }
            }
            
            result = self.container_client.container_groups.begin_create_or_update(
                resource_group_name,
                container_group_name,
                container_group_params
            ).result()
            
            print(f"✅ Created container group: {container_group_name}")
            return result.as_dict()
            
        except Exception as e:
            raise Exception(f"Failed to create container group: {e}")
    
    def deploy_fastapi_app(self, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy FastAPI application to Azure Container Instances."""
        app_name = app_config.get('app_name', 'fastapi-app')
        image_uri = app_config.get('image_uri')
        location = app_config.get('location', 'East US')
        cpu = app_config.get('cpu', 1.0)
        memory = app_config.get('memory', 1.5)
        port = app_config.get('port', 8000)
        
        if not image_uri:
            raise ValueError("image_uri is required for deployment")
        
        # Create resource group
        rg_name = f"{app_name}-rg"
        rg_config = AzureResourceGroup(
            name=rg_name,
            location=location,
            tags={'Application': app_name}
        )
        
        self.create_resource_group(rg_config)
        
        # Create container configuration
        container_config = AzureContainerConfig(
            name=app_name,
            image=image_uri,
            cpu=cpu,
            memory=memory,
            port=port,
            environment_variables={
                'PORT': str(port),
                'ENVIRONMENT': 'production'
            }
        )
        
        # Create container group
        container_group_name = f"{app_name}-cg"
        container_group = self.create_container_group(
            rg_name,
            container_group_name,
            [container_config],
            location
        )
        
        # Get public IP
        public_ip = container_group.get('ip_address', {}).get('ip')
        endpoint = f"http://{public_ip}:{port}" if public_ip else None
        
        return {
            'resource_group': rg_name,
            'container_group': container_group_name,
            'public_ip': public_ip,
            'endpoint': endpoint,
            'status': 'deployed'
        }
    
    def update_container_group(self, resource_group_name: str,
                              container_group_name: str,
                              new_image: str) -> Dict[str, Any]:
        """Update container group with new image."""
        try:
            # Get current container group
            current_cg = self.container_client.container_groups.get(
                resource_group_name, container_group_name
            )
            
            # Update image
            for container in current_cg.containers:
                container.image = new_image
            
            # Update container group
            result = self.container_client.container_groups.begin_create_or_update(
                resource_group_name,
                container_group_name,
                current_cg
            ).result()
            
            print(f"✅ Updated container group: {container_group_name}")
            return result.as_dict()
            
        except Exception as e:
            raise Exception(f"Failed to update container group: {e}")
    
    def delete_container_group(self, resource_group_name: str,
                              container_group_name: str) -> bool:
        """Delete container group."""
        try:
            self.container_client.container_groups.begin_delete(
                resource_group_name, container_group_name
            ).result()
            
            print(f"✅ Deleted container group: {container_group_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete container group: {e}")
            return False
    
    def get_container_logs(self, resource_group_name: str,
                          container_group_name: str,
                          container_name: str,
                          tail: int = 100) -> str:
        """Get container logs."""
        try:
            logs = self.container_client.containers.list_logs(
                resource_group_name,
                container_group_name,
                container_name,
                tail=tail
            )
            
            return logs.content
            
        except Exception as e:
            print(f"❌ Failed to get logs: {e}")
            return ""
    
    def get_container_status(self, resource_group_name: str,
                           container_group_name: str) -> Dict[str, Any]:
        """Get container group status."""
        try:
            container_group = self.container_client.container_groups.get(
                resource_group_name, container_group_name
            )
            
            status_info = {
                'provisioning_state': container_group.provisioning_state,
                'instance_view': container_group.instance_view.as_dict() if container_group.instance_view else None,
                'ip_address': container_group.ip_address.ip if container_group.ip_address else None,
                'containers': []
            }
            
            for container in container_group.containers:
                container_status = {
                    'name': container.name,
                    'image': container.image,
                    'current_state': container.instance_view.current_state.as_dict() if container.instance_view and container.instance_view.current_state else None,
                    'restart_count': container.instance_view.restart_count if container.instance_view else 0
                }
                status_info['containers'].append(container_status)
            
            return status_info
            
        except Exception as e:
            raise Exception(f"Failed to get container status: {e}")


class AzureContainerAppsDeployer:
    """Azure Container Apps deployment manager (for more advanced scenarios)."""
    
    def __init__(self, subscription_id: str, credential=None):
        if not AZURE_SDK_AVAILABLE:
            raise ImportError(
                "Azure SDK is required for Azure deployment. "
                "Install with: pip install azure-mgmt-containerinstance azure-mgmt-resource azure-identity"
            )
        
        self.subscription_id = subscription_id
        self.credential = credential or DefaultAzureCredential()
        
        # Note: Azure Container Apps would require additional SDK packages
        # This is a placeholder for future implementation
    
    def deploy_container_app(self, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Azure Container Apps (placeholder)."""
        # This would implement Azure Container Apps deployment
        # which provides more advanced features like auto-scaling,
        # traffic splitting, and better integration with Azure services
        
        raise NotImplementedError(
            "Azure Container Apps deployment is not yet implemented. "
            "Use Azure Container Instances deployment instead."
        )


def deploy_to_azure_containers(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy FastAPI application to Azure Container Instances."""
    subscription_id = config.get('subscription_id')
    if not subscription_id:
        raise ValueError("subscription_id is required for Azure deployment")
    
    # Handle authentication
    credential = None
    if config.get('client_id') and config.get('client_secret') and config.get('tenant_id'):
        credential = ClientSecretCredential(
            tenant_id=config['tenant_id'],
            client_id=config['client_id'],
            client_secret=config['client_secret']
        )
    
    deployer = AzureContainerDeployer(subscription_id=subscription_id, credential=credential)
    return deployer.deploy_fastapi_app(config)


def generate_azure_deployment_config(app_name: str, image_uri: str, 
                                    subscription_id: str) -> Dict[str, Any]:
    """Generate Azure deployment configuration."""
    return {
        'app_name': app_name,
        'image_uri': image_uri,
        'subscription_id': subscription_id,
        'location': 'East US',
        'cpu': 1.0,
        'memory': 1.5,
        'port': 8000
    }


# CLI helper functions
def list_azure_locations() -> List[str]:
    """List available Azure locations."""
    return [
        'East US', 'East US 2', 'West US', 'West US 2', 'West US 3',
        'Central US', 'North Central US', 'South Central US',
        'West Central US', 'Canada Central', 'Canada East',
        'Brazil South', 'North Europe', 'West Europe', 'UK South',
        'UK West', 'France Central', 'Germany West Central',
        'Switzerland North', 'Norway East', 'Sweden Central',
        'Australia East', 'Australia Southeast', 'Japan East',
        'Japan West', 'Korea Central', 'Asia Pacific', 'Southeast Asia',
        'Central India', 'South India', 'West India'
    ]


def validate_azure_config(config: Dict[str, Any]) -> List[str]:
    """Validate Azure deployment configuration."""
    errors = []
    
    required_fields = ['app_name', 'image_uri', 'subscription_id']
    for field in required_fields:
        if not config.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate CPU and memory
    cpu = config.get('cpu', 1.0)
    memory = config.get('memory', 1.5)
    
    if not isinstance(cpu, (int, float)) or cpu <= 0:
        errors.append("CPU must be a positive number")
    
    if not isinstance(memory, (int, float)) or memory <= 0:
        errors.append("Memory must be a positive number")
    
    # Validate location
    location = config.get('location', 'East US')
    if location not in list_azure_locations():
        errors.append(f"Invalid location: {location}")
    
    return errors
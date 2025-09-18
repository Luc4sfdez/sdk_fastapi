"""
Google Cloud Run Deployment for FastAPI Microservices.

This module provides deployment capabilities for Google Cloud Run
with auto-scaling, traffic management, and serverless deployment.
"""

import json
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

try:
    from google.cloud import run_v2
    from google.cloud import resourcemanager_v3
    from google.oauth2 import service_account
    from google.auth import default
    import google.auth.exceptions
    GCP_SDK_AVAILABLE = True
except ImportError:
    GCP_SDK_AVAILABLE = False


@dataclass
class CloudRunServiceConfig:
    """Cloud Run service configuration."""
    name: str
    image: str
    port: int = 8000
    cpu: str = "1000m"
    memory: str = "512Mi"
    min_instances: int = 0
    max_instances: int = 100
    concurrency: int = 80
    timeout: int = 300
    environment_variables: Dict[str, str] = field(default_factory=dict)
    allow_unauthenticated: bool = True


@dataclass
class CloudRunRevision:
    """Cloud Run revision configuration."""
    service_name: str
    revision_name: str
    traffic_percent: int = 100
    tag: Optional[str] = None


class GoogleCloudRunDeployer:
    """Google Cloud Run deployment manager."""
    
    def __init__(self, project_id: str, region: str = "us-central1", 
                 credentials_path: Optional[str] = None):
        if not GCP_SDK_AVAILABLE:
            raise ImportError(
                "Google Cloud SDK is required for GCP deployment. "
                "Install with: pip install google-cloud-run google-cloud-resource-manager"
            )
        
        self.project_id = project_id
        self.region = region
        
        # Initialize credentials
        if credentials_path:
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        else:
            self.credentials, _ = default()
        
        # Initialize clients
        self.run_client = run_v2.ServicesClient(credentials=self.credentials)
        self.operations_client = run_v2.OperationsClient(credentials=self.credentials)
    
    def create_service(self, service_config: CloudRunServiceConfig, 
                      location: Optional[str] = None) -> Dict[str, Any]:
        """Create Cloud Run service."""
        try:
            location = location or self.region
            parent = f"projects/{self.project_id}/locations/{location}"
            
            # Build container spec
            container = run_v2.Container(
                image=service_config.image,
                ports=[run_v2.ContainerPort(container_port=service_config.port)],
                resources=run_v2.ResourceRequirements(
                    limits={
                        "cpu": service_config.cpu,
                        "memory": service_config.memory
                    }
                ),
                env=[
                    run_v2.EnvVar(name=k, value=v)
                    for k, v in service_config.environment_variables.items()
                ]
            )
            
            # Build template spec
            template = run_v2.RevisionTemplate(
                containers=[container],
                scaling=run_v2.RevisionScaling(
                    min_instance_count=service_config.min_instances,
                    max_instance_count=service_config.max_instances
                ),
                max_instance_request_concurrency=service_config.concurrency,
                timeout=f"{service_config.timeout}s"
            )
            
            # Build service spec
            service = run_v2.Service(
                template=template,
                traffic=[
                    run_v2.TrafficTarget(
                        type_=run_v2.TrafficTargetAllocationType.TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST,
                        percent=100
                    )
                ]
            )
            
            # Create service request
            request = run_v2.CreateServiceRequest(
                parent=parent,
                service=service,
                service_id=service_config.name
            )
            
            # Execute request
            operation = self.run_client.create_service(request=request)
            
            print(f"⏳ Creating Cloud Run service: {service_config.name}")
            
            # Wait for operation to complete
            result = self._wait_for_operation(operation)
            
            print(f"✅ Created Cloud Run service: {service_config.name}")
            
            # Set IAM policy for unauthenticated access if requested
            if service_config.allow_unauthenticated:
                self._allow_unauthenticated_access(service_config.name, location)
            
            return self._service_to_dict(result)
            
        except Exception as e:
            raise Exception(f"Failed to create Cloud Run service: {e}")
    
    def update_service(self, service_name: str, new_image: str,
                      location: Optional[str] = None) -> Dict[str, Any]:
        """Update Cloud Run service with new image."""
        try:
            location = location or self.region
            service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
            
            # Get current service
            current_service = self.run_client.get_service(name=service_path)
            
            # Update image in template
            if current_service.spec.template.spec.containers:
                current_service.spec.template.spec.containers[0].image = new_image
            
            # Update service
            request = run_v2.UpdateServiceRequest(
                service=current_service
            )
            
            operation = self.run_client.update_service(request=request)
            
            print(f"⏳ Updating Cloud Run service: {service_name}")
            
            # Wait for operation to complete
            result = self._wait_for_operation(operation)
            
            print(f"✅ Updated Cloud Run service: {service_name}")
            return self._service_to_dict(result)
            
        except Exception as e:
            raise Exception(f"Failed to update Cloud Run service: {e}")
    
    def deploy_fastapi_app(self, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy FastAPI application to Cloud Run."""
        app_name = app_config.get('app_name', 'fastapi-app')
        image_uri = app_config.get('image_uri')
        region = app_config.get('region', self.region)
        port = app_config.get('port', 8000)
        cpu = app_config.get('cpu', '1000m')
        memory = app_config.get('memory', '512Mi')
        min_instances = app_config.get('min_instances', 0)
        max_instances = app_config.get('max_instances', 100)
        
        if not image_uri:
            raise ValueError("image_uri is required for deployment")
        
        # Create service configuration
        service_config = CloudRunServiceConfig(
            name=app_name,
            image=image_uri,
            port=port,
            cpu=cpu,
            memory=memory,
            min_instances=min_instances,
            max_instances=max_instances,
            environment_variables={
                'PORT': str(port),
                'ENVIRONMENT': 'production'
            }
        )
        
        # Deploy service
        service = self.create_service(service_config, region)
        
        # Get service URL
        service_url = service.get('status', {}).get('url')
        
        return {
            'service_name': app_name,
            'region': region,
            'url': service_url,
            'image': image_uri,
            'status': 'deployed'
        }
    
    def delete_service(self, service_name: str, location: Optional[str] = None) -> bool:
        """Delete Cloud Run service."""
        try:
            location = location or self.region
            service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
            
            request = run_v2.DeleteServiceRequest(name=service_path)
            operation = self.run_client.delete_service(request=request)
            
            print(f"⏳ Deleting Cloud Run service: {service_name}")
            
            # Wait for operation to complete
            self._wait_for_operation(operation)
            
            print(f"✅ Deleted Cloud Run service: {service_name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete Cloud Run service: {e}")
            return False
    
    def get_service_info(self, service_name: str, 
                        location: Optional[str] = None) -> Dict[str, Any]:
        """Get Cloud Run service information."""
        try:
            location = location or self.region
            service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
            
            service = self.run_client.get_service(name=service_path)
            return self._service_to_dict(service)
            
        except Exception as e:
            raise Exception(f"Failed to get service info: {e}")
    
    def list_services(self, location: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Cloud Run services."""
        try:
            location = location or self.region
            parent = f"projects/{self.project_id}/locations/{location}"
            
            request = run_v2.ListServicesRequest(parent=parent)
            services = self.run_client.list_services(request=request)
            
            return [self._service_to_dict(service) for service in services]
            
        except Exception as e:
            raise Exception(f"Failed to list services: {e}")
    
    def get_service_logs(self, service_name: str, location: Optional[str] = None,
                        lines: int = 100) -> List[str]:
        """Get service logs (requires Cloud Logging client)."""
        try:
            # This would require google-cloud-logging package
            # For now, return a placeholder
            print(f"ℹ️  To view logs for {service_name}, use:")
            print(f"gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name={service_name}' --limit={lines}")
            
            return [
                f"Use gcloud CLI to view logs: gcloud logs read 'resource.type=cloud_run_revision AND resource.labels.service_name={service_name}' --limit={lines}"
            ]
            
        except Exception as e:
            print(f"❌ Failed to get logs: {e}")
            return []
    
    def set_traffic_allocation(self, service_name: str, 
                             traffic_allocations: List[CloudRunRevision],
                             location: Optional[str] = None) -> Dict[str, Any]:
        """Set traffic allocation between revisions."""
        try:
            location = location or self.region
            service_path = f"projects/{self.project_id}/locations/{location}/services/{service_name}"
            
            # Get current service
            current_service = self.run_client.get_service(name=service_path)
            
            # Build traffic targets
            traffic_targets = []
            for allocation in traffic_allocations:
                target = run_v2.TrafficTarget(
                    revision=allocation.revision_name,
                    percent=allocation.traffic_percent
                )
                if allocation.tag:
                    target.tag = allocation.tag
                
                traffic_targets.append(target)
            
            # Update service traffic
            current_service.spec.traffic = traffic_targets
            
            request = run_v2.UpdateServiceRequest(service=current_service)
            operation = self.run_client.update_service(request=request)
            
            print(f"⏳ Updating traffic allocation for: {service_name}")
            
            # Wait for operation to complete
            result = self._wait_for_operation(operation)
            
            print(f"✅ Updated traffic allocation for: {service_name}")
            return self._service_to_dict(result)
            
        except Exception as e:
            raise Exception(f"Failed to set traffic allocation: {e}")
    
    def _wait_for_operation(self, operation, timeout: int = 300) -> Any:
        """Wait for long-running operation to complete."""
        start_time = time.time()
        
        while not operation.done():
            if time.time() - start_time > timeout:
                raise Exception(f"Operation timed out after {timeout} seconds")
            
            time.sleep(5)
            operation = self.operations_client.get_operation(name=operation.name)
        
        if operation.error:
            raise Exception(f"Operation failed: {operation.error}")
        
        return operation.response
    
    def _allow_unauthenticated_access(self, service_name: str, location: str) -> None:
        """Allow unauthenticated access to the service."""
        try:
            # This would require google-cloud-iam package for proper implementation
            # For now, provide instructions
            print(f"ℹ️  To allow unauthenticated access to {service_name}, run:")
            print(f"gcloud run services add-iam-policy-binding {service_name} --region={location} --member='allUsers' --role='roles/run.invoker'")
            
        except Exception as e:
            print(f"⚠️  Could not set unauthenticated access: {e}")
    
    def _service_to_dict(self, service) -> Dict[str, Any]:
        """Convert service object to dictionary."""
        try:
            return {
                'name': service.metadata.name if hasattr(service.metadata, 'name') else 'unknown',
                'url': service.status.url if hasattr(service.status, 'url') else None,
                'ready': service.status.conditions[0].status == 'True' if service.status.conditions else False,
                'image': service.spec.template.spec.containers[0].image if service.spec.template.spec.containers else None,
                'region': service.metadata.labels.get('cloud.googleapis.com/location') if hasattr(service.metadata, 'labels') else None,
                'created_time': service.metadata.creation_timestamp.isoformat() if hasattr(service.metadata, 'creation_timestamp') else None,
                'generation': service.metadata.generation if hasattr(service.metadata, 'generation') else None
            }
        except Exception:
            return {'name': 'unknown', 'status': 'error'}


def deploy_to_gcp_run(config: Dict[str, Any]) -> Dict[str, Any]:
    """Deploy FastAPI application to Google Cloud Run."""
    project_id = config.get('project_id')
    if not project_id:
        raise ValueError("project_id is required for GCP deployment")
    
    region = config.get('region', 'us-central1')
    credentials_path = config.get('credentials_path')
    
    deployer = GoogleCloudRunDeployer(
        project_id=project_id,
        region=region,
        credentials_path=credentials_path
    )
    
    return deployer.deploy_fastapi_app(config)


def generate_gcp_deployment_config(app_name: str, image_uri: str, 
                                  project_id: str) -> Dict[str, Any]:
    """Generate GCP Cloud Run deployment configuration."""
    return {
        'app_name': app_name,
        'image_uri': image_uri,
        'project_id': project_id,
        'region': 'us-central1',
        'port': 8000,
        'cpu': '1000m',
        'memory': '512Mi',
        'min_instances': 0,
        'max_instances': 100
    }


# CLI helper functions
def list_gcp_regions() -> List[str]:
    """List available GCP regions for Cloud Run."""
    return [
        'us-central1', 'us-east1', 'us-east4', 'us-west1', 'us-west2', 'us-west3', 'us-west4',
        'europe-north1', 'europe-west1', 'europe-west2', 'europe-west3', 'europe-west4', 'europe-west6',
        'asia-east1', 'asia-east2', 'asia-northeast1', 'asia-northeast2', 'asia-northeast3',
        'asia-south1', 'asia-southeast1', 'asia-southeast2',
        'australia-southeast1', 'northamerica-northeast1', 'southamerica-east1'
    ]


def validate_gcp_config(config: Dict[str, Any]) -> List[str]:
    """Validate GCP deployment configuration."""
    errors = []
    
    required_fields = ['app_name', 'image_uri', 'project_id']
    for field in required_fields:
        if not config.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate region
    region = config.get('region', 'us-central1')
    if region not in list_gcp_regions():
        errors.append(f"Invalid region: {region}")
    
    # Validate CPU format
    cpu = config.get('cpu', '1000m')
    if not isinstance(cpu, str) or not (cpu.endswith('m') or cpu.isdigit()):
        errors.append("CPU must be in format '1000m' or '1'")
    
    # Validate memory format
    memory = config.get('memory', '512Mi')
    if not isinstance(memory, str) or not (memory.endswith('Mi') or memory.endswith('Gi')):
        errors.append("Memory must be in format '512Mi' or '1Gi'")
    
    # Validate instance counts
    min_instances = config.get('min_instances', 0)
    max_instances = config.get('max_instances', 100)
    
    if not isinstance(min_instances, int) or min_instances < 0:
        errors.append("min_instances must be a non-negative integer")
    
    if not isinstance(max_instances, int) or max_instances < 1:
        errors.append("max_instances must be a positive integer")
    
    if min_instances >= max_instances:
        errors.append("min_instances must be less than max_instances")
    
    return errors


def get_gcp_project_info(project_id: str, credentials_path: Optional[str] = None) -> Dict[str, Any]:
    """Get GCP project information."""
    try:
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
        else:
            credentials, _ = default()
        
        client = resourcemanager_v3.ProjectsClient(credentials=credentials)
        project = client.get_project(name=f"projects/{project_id}")
        
        return {
            'project_id': project.project_id,
            'name': project.display_name,
            'state': project.state.name,
            'create_time': project.create_time.isoformat() if project.create_time else None
        }
        
    except Exception as e:
        return {'error': str(e)}
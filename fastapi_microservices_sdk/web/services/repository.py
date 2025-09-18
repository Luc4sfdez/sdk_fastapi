"""
Repository pattern for service data access operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta

from .models import (
    ServiceModel, 
    ServiceConfigurationModel, 
    ServiceLogModel, 
    ServiceMetricsModel,
    ServiceDeploymentModel
)
from .types import ServiceInfo, ServiceStatus, HealthStatus, ResourceUsage


class ServiceRepository:
    """Repository for service data access operations."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the service repository.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    # Service CRUD operations
    
    def create_service(self, service_info: ServiceInfo) -> ServiceModel:
        """
        Create a new service record.
        
        Args:
            service_info: Service information
            
        Returns:
            Created service model
        """
        service_model = ServiceModel(
            id=service_info.id,
            name=service_info.name,
            template_type=service_info.template_type,
            status=service_info.status.value,
            port=service_info.port,
            description=service_info.description,
            version=service_info.version,
            created_at=service_info.created_at,
            updated_at=service_info.last_updated,
            health_status=service_info.health_status.value,
            cpu_percent=service_info.resource_usage.cpu_percent,
            memory_mb=service_info.resource_usage.memory_mb,
            disk_mb=service_info.resource_usage.disk_mb,
            network_in_mb=service_info.resource_usage.network_in_mb,
            network_out_mb=service_info.resource_usage.network_out_mb,
            config=service_info.config
        )
        
        self.db.add(service_model)
        self.db.commit()
        self.db.refresh(service_model)
        
        return service_model
    
    def get_service_by_id(self, service_id: str) -> Optional[ServiceModel]:
        """
        Get service by ID.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service model or None if not found
        """
        return self.db.query(ServiceModel).filter(ServiceModel.id == service_id).first()
    
    def get_service_by_name(self, name: str) -> Optional[ServiceModel]:
        """
        Get service by name.
        
        Args:
            name: Service name
            
        Returns:
            Service model or None if not found
        """
        return self.db.query(ServiceModel).filter(ServiceModel.name == name).first()
    
    def get_all_services(self, skip: int = 0, limit: int = 100) -> List[ServiceModel]:
        """
        Get all services with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of service models
        """
        return self.db.query(ServiceModel).offset(skip).limit(limit).all()
    
    def get_services_by_status(self, status: ServiceStatus) -> List[ServiceModel]:
        """
        Get services by status.
        
        Args:
            status: Service status
            
        Returns:
            List of service models
        """
        return self.db.query(ServiceModel).filter(ServiceModel.status == status.value).all()
    
    def get_services_by_template_type(self, template_type: str) -> List[ServiceModel]:
        """
        Get services by template type.
        
        Args:
            template_type: Template type
            
        Returns:
            List of service models
        """
        return self.db.query(ServiceModel).filter(ServiceModel.template_type == template_type).all()
    
    def update_service(self, service_id: str, **kwargs) -> Optional[ServiceModel]:
        """
        Update service information.
        
        Args:
            service_id: Service identifier
            **kwargs: Fields to update
            
        Returns:
            Updated service model or None if not found
        """
        service = self.get_service_by_id(service_id)
        if service:
            for key, value in kwargs.items():
                if hasattr(service, key):
                    setattr(service, key, value)
            
            service.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(service)
        
        return service
    
    def update_service_status(self, service_id: str, status: ServiceStatus, health_status: HealthStatus = None) -> bool:
        """
        Update service status and health.
        
        Args:
            service_id: Service identifier
            status: New service status
            health_status: New health status (optional)
            
        Returns:
            True if updated successfully
        """
        service = self.get_service_by_id(service_id)
        if service:
            service.status = status.value
            if health_status:
                service.health_status = health_status.value
            service.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def update_service_resources(self, service_id: str, resource_usage: ResourceUsage) -> bool:
        """
        Update service resource usage.
        
        Args:
            service_id: Service identifier
            resource_usage: Resource usage information
            
        Returns:
            True if updated successfully
        """
        service = self.get_service_by_id(service_id)
        if service:
            service.cpu_percent = resource_usage.cpu_percent
            service.memory_mb = resource_usage.memory_mb
            service.disk_mb = resource_usage.disk_mb
            service.network_in_mb = resource_usage.network_in_mb
            service.network_out_mb = resource_usage.network_out_mb
            service.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False
    
    def delete_service(self, service_id: str) -> bool:
        """
        Delete service record.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if deleted successfully
        """
        service = self.get_service_by_id(service_id)
        if service:
            self.db.delete(service)
            self.db.commit()
            return True
        return False
    
    def search_services(self, query: str) -> List[ServiceModel]:
        """
        Search services by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching service models
        """
        return self.db.query(ServiceModel).filter(
            or_(
                ServiceModel.name.ilike(f"%{query}%"),
                ServiceModel.description.ilike(f"%{query}%")
            )
        ).all()
    
    def count_services(self) -> int:
        """
        Count total number of services.
        
        Returns:
            Total service count
        """
        return self.db.query(ServiceModel).count()
    
    def count_services_by_status(self, status: ServiceStatus) -> int:
        """
        Count services by status.
        
        Args:
            status: Service status
            
        Returns:
            Count of services with the given status
        """
        return self.db.query(ServiceModel).filter(ServiceModel.status == status.value).count()
    
    # Service configuration operations
    
    def create_service_configuration(
        self, 
        service_id: str, 
        configuration: Dict[str, Any], 
        created_by: str = None,
        description: str = None
    ) -> ServiceConfigurationModel:
        """
        Create a new service configuration version.
        
        Args:
            service_id: Service identifier
            configuration: Configuration data
            created_by: User who created the configuration
            description: Configuration description
            
        Returns:
            Created configuration model
        """
        # Get the next version number
        latest_config = self.db.query(ServiceConfigurationModel)\
            .filter(ServiceConfigurationModel.service_id == service_id)\
            .order_by(desc(ServiceConfigurationModel.version))\
            .first()
        
        next_version = (latest_config.version + 1) if latest_config else 1
        
        config_model = ServiceConfigurationModel(
            service_id=service_id,
            configuration=configuration,
            version=next_version,
            created_by=created_by,
            description=description,
            is_active=True
        )
        
        # Deactivate previous configurations
        self.db.query(ServiceConfigurationModel)\
            .filter(ServiceConfigurationModel.service_id == service_id)\
            .update({"is_active": False})
        
        self.db.add(config_model)
        self.db.commit()
        self.db.refresh(config_model)
        
        return config_model
    
    def get_service_configuration(self, service_id: str, version: int = None) -> Optional[ServiceConfigurationModel]:
        """
        Get service configuration by version.
        
        Args:
            service_id: Service identifier
            version: Configuration version (latest if None)
            
        Returns:
            Configuration model or None if not found
        """
        query = self.db.query(ServiceConfigurationModel)\
            .filter(ServiceConfigurationModel.service_id == service_id)
        
        if version:
            query = query.filter(ServiceConfigurationModel.version == version)
        else:
            query = query.filter(ServiceConfigurationModel.is_active == True)
        
        return query.first()
    
    def get_service_configuration_history(self, service_id: str) -> List[ServiceConfigurationModel]:
        """
        Get service configuration history.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of configuration models ordered by version
        """
        return self.db.query(ServiceConfigurationModel)\
            .filter(ServiceConfigurationModel.service_id == service_id)\
            .order_by(desc(ServiceConfigurationModel.version))\
            .all()
    
    # Service metrics operations
    
    def create_service_metrics(self, service_id: str, metrics_data: Dict[str, Any]) -> ServiceMetricsModel:
        """
        Create service metrics record.
        
        Args:
            service_id: Service identifier
            metrics_data: Metrics data
            
        Returns:
            Created metrics model
        """
        metrics_model = ServiceMetricsModel(
            service_id=service_id,
            **metrics_data
        )
        
        self.db.add(metrics_model)
        self.db.commit()
        self.db.refresh(metrics_model)
        
        return metrics_model
    
    def get_service_metrics(
        self, 
        service_id: str, 
        start_time: datetime = None, 
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[ServiceMetricsModel]:
        """
        Get service metrics within time range.
        
        Args:
            service_id: Service identifier
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)
            limit: Maximum number of records
            
        Returns:
            List of metrics models
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        return self.db.query(ServiceMetricsModel)\
            .filter(
                and_(
                    ServiceMetricsModel.service_id == service_id,
                    ServiceMetricsModel.timestamp >= start_time,
                    ServiceMetricsModel.timestamp <= end_time
                )
            )\
            .order_by(desc(ServiceMetricsModel.timestamp))\
            .limit(limit)\
            .all()
    
    def cleanup_old_metrics(self, retention_days: int = 30) -> int:
        """
        Clean up old metrics data.
        
        Args:
            retention_days: Number of days to retain metrics
            
        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted_count = self.db.query(ServiceMetricsModel)\
            .filter(ServiceMetricsModel.timestamp < cutoff_date)\
            .delete()
        
        self.db.commit()
        return deleted_count
    
    # Service deployment operations
    
    def create_service_deployment(
        self, 
        service_id: str, 
        deployment_id: str,
        target_environment: str,
        configuration: Dict[str, Any],
        deployed_by: str = None
    ) -> ServiceDeploymentModel:
        """
        Create service deployment record.
        
        Args:
            service_id: Service identifier
            deployment_id: Unique deployment identifier
            target_environment: Target deployment environment
            configuration: Deployment configuration
            deployed_by: User who initiated deployment
            
        Returns:
            Created deployment model
        """
        deployment_model = ServiceDeploymentModel(
            service_id=service_id,
            deployment_id=deployment_id,
            target_environment=target_environment,
            configuration=configuration,
            deployed_by=deployed_by
        )
        
        self.db.add(deployment_model)
        self.db.commit()
        self.db.refresh(deployment_model)
        
        return deployment_model
    
    def get_service_deployment(self, deployment_id: str) -> Optional[ServiceDeploymentModel]:
        """
        Get deployment by ID.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Deployment model or None if not found
        """
        return self.db.query(ServiceDeploymentModel)\
            .filter(ServiceDeploymentModel.deployment_id == deployment_id)\
            .first()
    
    def get_service_deployments(self, service_id: str) -> List[ServiceDeploymentModel]:
        """
        Get all deployments for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of deployment models
        """
        return self.db.query(ServiceDeploymentModel)\
            .filter(ServiceDeploymentModel.service_id == service_id)\
            .order_by(desc(ServiceDeploymentModel.started_at))\
            .all()
    
    def update_deployment_status(
        self, 
        deployment_id: str, 
        status: str, 
        deployment_url: str = None,
        error_message: str = None
    ) -> bool:
        """
        Update deployment status.
        
        Args:
            deployment_id: Deployment identifier
            status: New deployment status
            deployment_url: Deployment URL (optional)
            error_message: Error message if failed (optional)
            
        Returns:
            True if updated successfully
        """
        deployment = self.get_service_deployment(deployment_id)
        if deployment:
            deployment.status = status
            if deployment_url:
                deployment.deployment_url = deployment_url
            if error_message:
                deployment.error_message = error_message
            if status in ["completed", "failed"]:
                deployment.completed_at = datetime.utcnow()
            
            self.db.commit()
            return True
        return False
    
    # Utility methods
    
    def service_model_to_info(self, service_model: ServiceModel) -> ServiceInfo:
        """
        Convert ServiceModel to ServiceInfo.
        
        Args:
            service_model: Database service model
            
        Returns:
            ServiceInfo object
        """
        resource_usage = ResourceUsage(
            cpu_percent=service_model.cpu_percent or 0.0,
            memory_mb=service_model.memory_mb or 0.0,
            disk_mb=service_model.disk_mb or 0.0,
            network_in_mb=service_model.network_in_mb or 0.0,
            network_out_mb=service_model.network_out_mb or 0.0
        )
        
        return ServiceInfo(
            id=service_model.id,
            name=service_model.name,
            template_type=service_model.template_type,
            status=ServiceStatus(service_model.status),
            port=service_model.port,
            created_at=service_model.created_at,
            last_updated=service_model.updated_at,
            health_status=HealthStatus(service_model.health_status),
            resource_usage=resource_usage,
            config=service_model.config,
            description=service_model.description,
            version=service_model.version
        )
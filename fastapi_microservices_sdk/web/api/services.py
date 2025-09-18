"""
REST API endpoints for service management.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime

from ..services import ServiceManager, ServiceRepository, get_database_manager
from ..services.types import ServiceInfo, ServiceStatus, HealthStatus, ServiceDetails
from ..services.database import get_db


# Pydantic models for API requests/responses

class ServiceStatusResponse(BaseModel):
    """Service status response model."""
    id: str
    name: str
    status: str
    health_status: str
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ServiceInfoResponse(BaseModel):
    """Service information response model."""
    id: str
    name: str
    template_type: str
    status: str
    port: int
    description: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime
    last_updated: datetime
    health_status: str
    resource_usage: Dict[str, float]
    config: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class ServiceDetailsResponse(BaseModel):
    """Service details response model."""
    service_info: ServiceInfoResponse
    endpoints: List[str]
    dependencies: List[str]
    environment_variables: Dict[str, str]
    logs_path: Optional[str] = None
    metrics_enabled: bool = True
    
    class Config:
        from_attributes = True


class ServiceCreateRequest(BaseModel):
    """Service creation request model."""
    name: str = Field(..., description="Service name")
    template_type: str = Field(..., description="Service template type")
    port: int = Field(..., description="Service port", ge=1, le=65535)
    description: Optional[str] = Field(None, description="Service description")
    version: Optional[str] = Field("1.0.0", description="Service version")
    config: Optional[Dict[str, Any]] = Field(None, description="Service configuration")


class ServiceUpdateRequest(BaseModel):
    """Service update request model."""
    name: Optional[str] = Field(None, description="Service name")
    description: Optional[str] = Field(None, description="Service description")
    version: Optional[str] = Field(None, description="Service version")
    port: Optional[int] = Field(None, description="Service port", ge=1, le=65535)
    config: Optional[Dict[str, Any]] = Field(None, description="Service configuration")


class ServiceActionRequest(BaseModel):
    """Service action request model."""
    action: str = Field(..., description="Action to perform", pattern="^(start|stop|restart)$")
    force: bool = Field(False, description="Force action even if service is in transitional state")


class ServiceActionResponse(BaseModel):
    """Service action response model."""
    success: bool
    message: str
    service_id: str
    action: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Create router
router = APIRouter(prefix="/api/services", tags=["services"])


# Dependency to get service manager
async def get_service_manager() -> ServiceManager:
    """Get service manager instance."""
    # This would typically be injected from the application context
    # For now, create a new instance
    manager = ServiceManager()
    if not manager.is_initialized():
        await manager.initialize()
    return manager


# Helper functions

def service_info_to_response(service_info: ServiceInfo) -> ServiceInfoResponse:
    """Convert ServiceInfo to ServiceInfoResponse."""
    return ServiceInfoResponse(
        id=service_info.id,
        name=service_info.name,
        template_type=service_info.template_type,
        status=service_info.status.value,
        port=service_info.port,
        description=service_info.description,
        version=service_info.version,
        created_at=service_info.created_at,
        last_updated=service_info.last_updated,
        health_status=service_info.health_status.value,
        resource_usage={
            "cpu_percent": service_info.resource_usage.cpu_percent,
            "memory_mb": service_info.resource_usage.memory_mb,
            "disk_mb": service_info.resource_usage.disk_mb,
            "network_in_mb": service_info.resource_usage.network_in_mb,
            "network_out_mb": service_info.resource_usage.network_out_mb
        },
        config=service_info.config
    )


def service_details_to_response(service_details: ServiceDetails) -> ServiceDetailsResponse:
    """Convert ServiceDetails to ServiceDetailsResponse."""
    return ServiceDetailsResponse(
        service_info=service_info_to_response(service_details.service_info),
        endpoints=service_details.endpoints,
        dependencies=service_details.dependencies,
        environment_variables=service_details.environment_variables,
        logs_path=service_details.logs_path,
        metrics_enabled=service_details.metrics_enabled
    )


# API Endpoints

@router.get("/", response_model=List[ServiceInfoResponse])
async def list_services(
    skip: int = Query(0, ge=0, description="Number of services to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of services to return"),
    status: Optional[str] = Query(None, description="Filter by service status"),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    search: Optional[str] = Query(None, description="Search services by name or description"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get list of all services with optional filtering.
    
    - **skip**: Number of services to skip for pagination
    - **limit**: Maximum number of services to return
    - **status**: Filter by service status (running, stopped, etc.)
    - **template_type**: Filter by template type
    - **search**: Search services by name or description
    """
    try:
        services = await service_manager.list_services()
        
        # Apply filters
        if status:
            try:
                status_enum = ServiceStatus(status)
                services = [s for s in services if s.status == status_enum]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in ServiceStatus]}"
                )
        
        if template_type:
            services = [s for s in services if s.template_type == template_type]
        
        if search:
            search_lower = search.lower()
            services = [
                s for s in services 
                if search_lower in s.name.lower() or 
                (s.description and search_lower in s.description.lower())
            ]
        
        # Apply pagination
        total_services = services[skip:skip + limit]
        
        return [service_info_to_response(service) for service in total_services]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list services: {str(e)}")


@router.get("/{service_id}", response_model=ServiceDetailsResponse)
async def get_service(
    service_id: str = Path(..., description="Service ID"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get detailed information about a specific service.
    
    - **service_id**: Unique identifier of the service
    """
    try:
        service_details = await service_manager.get_service_details(service_id)
        
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        return service_details_to_response(service_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service details: {str(e)}")


@router.post("/{service_id}/actions", response_model=ServiceActionResponse)
async def perform_service_action(
    service_id: str = Path(..., description="Service ID"),
    action_request: ServiceActionRequest = Body(...),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Perform lifecycle actions on a service.
    
    - **service_id**: Unique identifier of the service
    - **action**: Action to perform (start, stop, restart)
    - **force**: Force action even if service is in transitional state
    """
    try:
        # Check if service exists
        service_details = await service_manager.get_service_details(service_id)
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        action = action_request.action
        success = False
        message = ""
        
        # Perform the requested action
        if action == "start":
            success = await service_manager.start_service(service_id)
            message = f"Service '{service_id}' start {'successful' if success else 'failed'}"
        elif action == "stop":
            success = await service_manager.stop_service(service_id)
            message = f"Service '{service_id}' stop {'successful' if success else 'failed'}"
        elif action == "restart":
            success = await service_manager.restart_service(service_id)
            message = f"Service '{service_id}' restart {'successful' if success else 'failed'}"
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to {action} service '{service_id}'"
            )
        
        return ServiceActionResponse(
            success=success,
            message=message,
            service_id=service_id,
            action=action
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform action: {str(e)}")


@router.get("/{service_id}/status", response_model=ServiceStatusResponse)
async def get_service_status(
    service_id: str = Path(..., description="Service ID"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get current status of a service.
    
    - **service_id**: Unique identifier of the service
    """
    try:
        service_details = await service_manager.get_service_details(service_id)
        
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        service_info = service_details.service_info
        
        return ServiceStatusResponse(
            id=service_info.id,
            name=service_info.name,
            status=service_info.status.value,
            health_status=service_info.health_status.value,
            last_updated=service_info.last_updated
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@router.get("/{service_id}/health", response_model=Dict[str, Any])
async def get_service_health(
    service_id: str = Path(..., description="Service ID"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get health status of a service.
    
    - **service_id**: Unique identifier of the service
    """
    try:
        health_status = await service_manager.get_service_health(service_id)
        
        # Get service details for additional health info
        service_details = await service_manager.get_service_details(service_id)
        
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        service_info = service_details.service_info
        
        return {
            "service_id": service_id,
            "health_status": health_status.value,
            "status": service_info.status.value,
            "last_updated": service_info.last_updated.isoformat(),
            "resource_usage": {
                "cpu_percent": service_info.resource_usage.cpu_percent,
                "memory_mb": service_info.resource_usage.memory_mb,
                "disk_mb": service_info.resource_usage.disk_mb,
                "network_in_mb": service_info.resource_usage.network_in_mb,
                "network_out_mb": service_info.resource_usage.network_out_mb
            },
            "endpoints": service_details.endpoints,
            "metrics_enabled": service_details.metrics_enabled
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service health: {str(e)}")


@router.delete("/{service_id}")
async def delete_service(
    service_id: str = Path(..., description="Service ID"),
    force: bool = Query(False, description="Force deletion even if service is running"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Delete a service.
    
    - **service_id**: Unique identifier of the service
    - **force**: Force deletion even if service is running
    """
    try:
        # Check if service exists
        service_details = await service_manager.get_service_details(service_id)
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        # Check if service is running and force is not set
        if not force and service_details.service_info.status == ServiceStatus.RUNNING:
            raise HTTPException(
                status_code=400,
                detail=f"Service '{service_id}' is currently running. Stop the service first or use force=true"
            )
        
        # Delete the service
        success = await service_manager.delete_service(service_id)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete service '{service_id}'"
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Service '{service_id}' deleted successfully",
                "service_id": service_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete service: {str(e)}")


# Additional endpoints for service management

@router.get("/{service_id}/logs")
async def get_service_logs(
    service_id: str = Path(..., description="Service ID"),
    lines: int = Query(100, ge=1, le=10000, description="Number of log lines to return"),
    follow: bool = Query(False, description="Follow log output (streaming)"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get service logs.
    
    - **service_id**: Unique identifier of the service
    - **lines**: Number of log lines to return
    - **follow**: Follow log output (for streaming)
    - **level**: Filter by log level (DEBUG, INFO, WARNING, ERROR)
    """
    try:
        # Check if service exists
        service_details = await service_manager.get_service_details(service_id)
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        # For now, return a placeholder response
        # In a full implementation, this would read actual log files
        return {
            "service_id": service_id,
            "logs": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": f"Service {service_id} is running",
                    "source": "stdout"
                }
            ],
            "total_lines": 1,
            "follow": follow,
            "level_filter": level
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service logs: {str(e)}")


@router.get("/{service_id}/metrics")
async def get_service_metrics(
    service_id: str = Path(..., description="Service ID"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    interval: str = Query("1m", description="Metrics interval (1m, 5m, 1h, etc.)"),
    service_manager: ServiceManager = Depends(get_service_manager)
):
    """
    Get service metrics.
    
    - **service_id**: Unique identifier of the service
    - **start_time**: Start time for metrics (ISO format)
    - **end_time**: End time for metrics (ISO format)
    - **interval**: Metrics aggregation interval
    """
    try:
        # Check if service exists
        service_details = await service_manager.get_service_details(service_id)
        if not service_details:
            raise HTTPException(
                status_code=404,
                detail=f"Service with ID '{service_id}' not found"
            )
        
        # For now, return current resource usage
        # In a full implementation, this would query historical metrics
        service_info = service_details.service_info
        
        return {
            "service_id": service_id,
            "start_time": start_time,
            "end_time": end_time,
            "interval": interval,
            "metrics": {
                "cpu_percent": service_info.resource_usage.cpu_percent,
                "memory_mb": service_info.resource_usage.memory_mb,
                "disk_mb": service_info.resource_usage.disk_mb,
                "network_in_mb": service_info.resource_usage.network_in_mb,
                "network_out_mb": service_info.resource_usage.network_out_mb
            },
            "timestamp": service_info.last_updated.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service metrics: {str(e)}")


# Note: Exception handlers should be added to the main FastAPI app, not the router
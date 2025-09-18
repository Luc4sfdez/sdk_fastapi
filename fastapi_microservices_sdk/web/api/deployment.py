"""
Deployment management REST API endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ..deployment.deployment_manager import (
    DeploymentManager,
    DeploymentType,
    DeploymentStatus,
    DeploymentStage,
    DeploymentConfig,
    DeploymentInfo,
    DeploymentWorkflow,
    DeploymentStep,
    DeploymentProgressUpdate
)
from ..core.dependency_container import get_deployment_manager


# Pydantic models for API

class DeploymentConfigRequest(BaseModel):
    """Request model for deployment configuration."""
    service_id: str = Field(..., description="Service identifier")
    target_environment: str = Field(..., description="Target environment (dev, staging, prod)")
    deployment_type: DeploymentType = Field(..., description="Type of deployment")
    image_name: Optional[str] = Field(None, description="Container image name")
    namespace: Optional[str] = Field("default", description="Kubernetes namespace")
    replicas: int = Field(1, description="Number of replicas", ge=1, le=100)
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    volumes: List[Dict[str, str]] = Field(default_factory=list, description="Volume mounts")
    health_checks: Dict[str, Any] = Field(default_factory=dict, description="Health check configuration")
    build_context: Optional[str] = Field(".", description="Build context path")
    dockerfile: Optional[str] = Field("Dockerfile", description="Dockerfile path")
    health_check_url: Optional[str] = Field(None, description="Health check URL")
    rollback_config: Optional[Dict[str, Any]] = Field(None, description="Rollback configuration")


class DeploymentResponse(BaseModel):
    """Response model for deployment information."""
    id: str
    service_id: str
    deployment_type: DeploymentType
    status: DeploymentStatus
    target_environment: str
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None
    deployment_url: Optional[str] = None
    current_stage: Optional[DeploymentStage] = None
    progress_percentage: float = 0.0
    error_message: Optional[str] = None


class DeploymentProgressResponse(BaseModel):
    """Response model for deployment progress."""
    deployment_id: str
    workflow_id: str
    step_id: Optional[str]
    stage: DeploymentStage
    status: DeploymentStatus
    progress_percentage: float
    message: str
    timestamp: datetime
    logs: List[str] = Field(default_factory=list)


class DeploymentWorkflowResponse(BaseModel):
    """Response model for deployment workflow."""
    id: str
    name: str
    deployment_type: DeploymentType
    current_step_index: int
    progress_percentage: float
    timeout_minutes: int
    created_at: datetime
    steps: List[Dict[str, Any]] = Field(default_factory=list)


class DeploymentStepResponse(BaseModel):
    """Response model for deployment step."""
    id: str
    name: str
    stage: DeploymentStage
    status: DeploymentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class DeploymentListResponse(BaseModel):
    """Response model for deployment list."""
    deployments: List[DeploymentResponse]
    total: int
    page: int
    page_size: int


class ValidationResponse(BaseModel):
    """Response model for configuration validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_duration: Optional[int] = None


class RollbackRequest(BaseModel):
    """Request model for deployment rollback."""
    reason: str = Field(..., description="Reason for rollback")
    rollback_to_deployment_id: Optional[str] = Field(None, description="Specific deployment to rollback to")


# Create router
router = APIRouter(prefix="/api/v1/deployments", tags=["deployments"])


@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    config: DeploymentConfigRequest,
    background_tasks: BackgroundTasks,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> DeploymentResponse:
    """
    Create and start a new deployment.
    
    Args:
        config: Deployment configuration
        background_tasks: FastAPI background tasks
        deployment_manager: Deployment manager instance
        
    Returns:
        Deployment information
    """
    try:
        # Convert request to deployment config
        deployment_config = DeploymentConfig(
            service_id=config.service_id,
            target_environment=config.target_environment,
            deployment_type=config.deployment_type,
            image_name=config.image_name,
            namespace=config.namespace,
            replicas=config.replicas,
            environment_variables=config.environment_variables,
            volumes=config.volumes,
            health_checks=config.health_checks,
            rollback_config=config.rollback_config
        )
        
        # Start deployment
        deployment_id = await deployment_manager.deploy_service(deployment_config)
        
        # Get deployment info
        deployment = await deployment_manager.get_deployment_status(deployment_id)
        if not deployment:
            raise HTTPException(status_code=500, detail="Failed to create deployment")
        
        return DeploymentResponse(
            id=deployment.id,
            service_id=deployment.service_id,
            deployment_type=deployment.deployment_type,
            status=deployment.status,
            target_environment=deployment.target_environment,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            deployed_at=deployment.deployed_at,
            deployment_url=deployment.deployment_url,
            current_stage=deployment.current_stage,
            progress_percentage=deployment.progress_percentage,
            error_message=deployment.error_message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment creation failed: {str(e)}")


@router.get("/", response_model=DeploymentListResponse)
async def list_deployments(
    service_id: Optional[str] = Query(None, description="Filter by service ID"),
    deployment_type: Optional[DeploymentType] = Query(None, description="Filter by deployment type"),
    status: Optional[DeploymentStatus] = Query(None, description="Filter by status"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> DeploymentListResponse:
    """
    List deployments with optional filtering and pagination.
    
    Args:
        service_id: Filter by service ID
        deployment_type: Filter by deployment type
        status: Filter by status
        environment: Filter by environment
        page: Page number
        page_size: Page size
        deployment_manager: Deployment manager instance
        
    Returns:
        List of deployments with pagination info
    """
    try:
        # Get all deployments
        all_deployments = await deployment_manager.list_deployments()
        
        # Apply filters
        filtered_deployments = []
        for deployment in all_deployments:
            if service_id and deployment.service_id != service_id:
                continue
            if deployment_type and deployment.deployment_type != deployment_type:
                continue
            if status and deployment.status != status:
                continue
            if environment and deployment.target_environment != environment:
                continue
            
            filtered_deployments.append(deployment)
        
        # Apply pagination
        total = len(filtered_deployments)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_deployments = filtered_deployments[start_idx:end_idx]
        
        # Convert to response models
        deployment_responses = []
        for deployment in paginated_deployments:
            deployment_responses.append(DeploymentResponse(
                id=deployment.id,
                service_id=deployment.service_id,
                deployment_type=deployment.deployment_type,
                status=deployment.status,
                target_environment=deployment.target_environment,
                created_at=deployment.created_at,
                updated_at=deployment.updated_at,
                deployed_at=deployment.deployed_at,
                deployment_url=deployment.deployment_url,
                current_stage=deployment.current_stage,
                progress_percentage=deployment.progress_percentage,
                error_message=deployment.error_message
            ))
        
        return DeploymentListResponse(
            deployments=deployment_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list deployments: {str(e)}")


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> DeploymentResponse:
    """
    Get deployment by ID.
    
    Args:
        deployment_id: Deployment identifier
        deployment_manager: Deployment manager instance
        
    Returns:
        Deployment information
    """
    try:
        deployment = await deployment_manager.get_deployment_status(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        return DeploymentResponse(
            id=deployment.id,
            service_id=deployment.service_id,
            deployment_type=deployment.deployment_type,
            status=deployment.status,
            target_environment=deployment.target_environment,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            deployed_at=deployment.deployed_at,
            deployment_url=deployment.deployment_url,
            current_stage=deployment.current_stage,
            progress_percentage=deployment.progress_percentage,
            error_message=deployment.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment: {str(e)}")


@router.delete("/{deployment_id}")
async def cancel_deployment(
    deployment_id: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> Dict[str, str]:
    """
    Cancel a running deployment.
    
    Args:
        deployment_id: Deployment identifier
        deployment_manager: Deployment manager instance
        
    Returns:
        Cancellation result
    """
    try:
        success = await deployment_manager.cancel_deployment(deployment_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel deployment")
        
        return {"message": "Deployment cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel deployment: {str(e)}")


@router.get("/{deployment_id}/progress", response_model=DeploymentProgressResponse)
async def get_deployment_progress(
    deployment_id: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> DeploymentProgressResponse:
    """
    Get current deployment progress.
    
    Args:
        deployment_id: Deployment identifier
        deployment_manager: Deployment manager instance
        
    Returns:
        Current deployment progress
    """
    try:
        progress = await deployment_manager.get_deployment_progress(deployment_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Deployment progress not found")
        
        return DeploymentProgressResponse(
            deployment_id=progress.deployment_id,
            workflow_id=progress.workflow_id,
            step_id=progress.step_id,
            stage=progress.stage,
            status=progress.status,
            progress_percentage=progress.progress_percentage,
            message=progress.message,
            timestamp=progress.timestamp,
            logs=progress.logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment progress: {str(e)}")


@router.get("/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines"),
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> Dict[str, List[str]]:
    """
    Get deployment logs.
    
    Args:
        deployment_id: Deployment identifier
        lines: Number of log lines to return
        deployment_manager: Deployment manager instance
        
    Returns:
        Deployment logs
    """
    try:
        logs = await deployment_manager.get_deployment_logs(deployment_id, lines)
        return {"logs": logs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment logs: {str(e)}")


@router.get("/{deployment_id}/workflow", response_model=DeploymentWorkflowResponse)
async def get_deployment_workflow(
    deployment_id: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> DeploymentWorkflowResponse:
    """
    Get deployment workflow information.
    
    Args:
        deployment_id: Deployment identifier
        deployment_manager: Deployment manager instance
        
    Returns:
        Deployment workflow information
    """
    try:
        # Get deployment
        deployment = await deployment_manager.get_deployment_status(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        # Create workflow from deployment config
        workflow = await deployment_manager.create_deployment_workflow(
            deployment.deployment_type,
            deployment.config
        )
        
        # Convert steps to response format
        steps = []
        for step in workflow.steps:
            steps.append({
                "id": step.id,
                "name": step.name,
                "stage": step.stage.value,
                "status": step.status.value,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "duration": step.duration,
                "logs": step.logs,
                "error_message": step.error_message,
                "retry_count": step.retry_count,
                "max_retries": step.max_retries
            })
        
        return DeploymentWorkflowResponse(
            id=workflow.id,
            name=workflow.name,
            deployment_type=workflow.deployment_type,
            current_step_index=workflow.current_step_index,
            progress_percentage=workflow.progress_percentage,
            timeout_minutes=workflow.timeout_minutes,
            created_at=workflow.created_at,
            steps=steps
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment workflow: {str(e)}")


@router.post("/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    rollback_request: RollbackRequest,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> Dict[str, str]:
    """
    Rollback a deployment.
    
    Args:
        deployment_id: Deployment identifier
        rollback_request: Rollback request details
        deployment_manager: Deployment manager instance
        
    Returns:
        Rollback result
    """
    try:
        success = await deployment_manager.rollback_deployment(
            deployment_id,
            rollback_request.reason
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to rollback deployment")
        
        return {"message": "Deployment rollback initiated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rollback deployment: {str(e)}")


@router.post("/validate", response_model=ValidationResponse)
async def validate_deployment_config(
    config: DeploymentConfigRequest,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> ValidationResponse:
    """
    Validate deployment configuration.
    
    Args:
        config: Deployment configuration to validate
        deployment_manager: Deployment manager instance
        
    Returns:
        Validation result
    """
    try:
        # Convert request to deployment config
        deployment_config = DeploymentConfig(
            service_id=config.service_id,
            target_environment=config.target_environment,
            deployment_type=config.deployment_type,
            image_name=config.image_name,
            namespace=config.namespace,
            replicas=config.replicas,
            environment_variables=config.environment_variables,
            volumes=config.volumes,
            health_checks=config.health_checks,
            rollback_config=config.rollback_config
        )
        
        # Validate configuration
        validation_result = await deployment_manager.validate_deployment_config(deployment_config)
        
        return ValidationResponse(
            valid=validation_result.get("valid", False),
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", []),
            estimated_duration=validation_result.get("estimated_duration")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")


@router.get("/{deployment_id}/history")
async def get_deployment_history(
    deployment_id: str,
    deployment_manager: DeploymentManager = Depends(get_deployment_manager)
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get deployment history and audit trail.
    
    Args:
        deployment_id: Deployment identifier
        deployment_manager: Deployment manager instance
        
    Returns:
        Deployment history
    """
    try:
        # Get deployment
        deployment = await deployment_manager.get_deployment_status(deployment_id)
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        # Create history from deployment info
        history = [
            {
                "timestamp": deployment.created_at.isoformat(),
                "event": "deployment_created",
                "status": deployment.status.value,
                "message": f"Deployment created for service {deployment.service_id}"
            },
            {
                "timestamp": deployment.updated_at.isoformat(),
                "event": "deployment_updated",
                "status": deployment.status.value,
                "message": f"Deployment status updated to {deployment.status.value}"
            }
        ]
        
        if deployment.deployed_at:
            history.append({
                "timestamp": deployment.deployed_at.isoformat(),
                "event": "deployment_completed",
                "status": "completed",
                "message": "Deployment completed successfully"
            })
        
        return {"history": history}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment history: {str(e)}")


# Health check endpoint
@router.get("/health")
async def deployment_api_health() -> Dict[str, str]:
    """
    Health check endpoint for deployment API.
    
    Returns:
        Health status
    """
    return {"status": "healthy", "service": "deployment-api"}
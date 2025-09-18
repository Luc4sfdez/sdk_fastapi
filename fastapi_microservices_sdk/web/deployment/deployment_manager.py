"""
Deployment management for the web dashboard.
"""

from typing import List, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import json
import subprocess
import tempfile
import os
from pathlib import Path

from ..core.base_manager import BaseManager


class DeploymentType(Enum):
    """Deployment types."""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CLOUD_RUN = "cloud_run"
    AZURE_CONTAINERS = "azure_containers"
    AWS_ECS = "aws_ecs"


class DeploymentStatus(Enum):
    """Deployment status."""
    PENDING = "pending"
    VALIDATING = "validating"
    PREPARING = "preparing"
    BUILDING = "building"
    PUSHING = "pushing"
    DEPLOYING = "deploying"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class DeploymentStage(Enum):
    """Deployment stages."""
    VALIDATION = "validation"
    PREPARATION = "preparation"
    BUILD = "build"
    PUSH = "push"
    DEPLOY = "deploy"
    HEALTH_CHECK = "health_check"
    FINALIZATION = "finalization"


@dataclass
class DeploymentStep:
    """Individual deployment step."""
    id: str
    name: str
    stage: DeploymentStage
    status: DeploymentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentWorkflow:
    """Deployment workflow definition."""
    id: str
    name: str
    deployment_type: DeploymentType
    steps: List[DeploymentStep] = field(default_factory=list)
    current_step_index: int = 0
    parallel_execution: bool = False
    rollback_on_failure: bool = True
    timeout_minutes: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def current_step(self) -> Optional[DeploymentStep]:
        """Get current deployment step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    @property
    def completed_steps(self) -> List[DeploymentStep]:
        """Get completed steps."""
        return [step for step in self.steps if step.status == DeploymentStatus.COMPLETED]
    
    @property
    def failed_steps(self) -> List[DeploymentStep]:
        """Get failed steps."""
        return [step for step in self.steps if step.status == DeploymentStatus.FAILED]
    
    @property
    def progress_percentage(self) -> float:
        """Calculate deployment progress percentage."""
        if not self.steps:
            return 0.0
        completed = len(self.completed_steps)
        return (completed / len(self.steps)) * 100.0


@dataclass
class DeploymentProgressUpdate:
    """Deployment progress update."""
    deployment_id: str
    workflow_id: str
    step_id: Optional[str]
    stage: DeploymentStage
    status: DeploymentStatus
    progress_percentage: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeploymentRollbackInfo:
    """Deployment rollback information."""
    rollback_id: str
    original_deployment_id: str
    rollback_to_deployment_id: Optional[str]
    reason: str
    initiated_by: str
    initiated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: DeploymentStatus = DeploymentStatus.PENDING
    steps: List[DeploymentStep] = field(default_factory=list)
    VERIFY = "verify"
    CLEANUP = "cleanup"


@dataclass
class ResourceRequirements:
    """Resource requirements for deployment."""
    cpu: str = "100m"
    memory: str = "128Mi"
    replicas: int = 1
    storage: Optional[str] = None
    gpu: Optional[str] = None
    limits: Optional[Dict[str, str]] = None


@dataclass
class NetworkConfig:
    """Network configuration for deployment."""
    ports: List[Dict[str, Any]] = field(default_factory=list)
    ingress: Optional[Dict[str, Any]] = None
    load_balancer: Optional[Dict[str, Any]] = None
    service_mesh: bool = False


@dataclass
class SecurityConfig:
    """Security configuration for deployment."""
    image_pull_secrets: List[str] = field(default_factory=list)
    service_account: Optional[str] = None
    security_context: Optional[Dict[str, Any]] = None
    network_policies: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeploymentConfig:
    """Deployment configuration."""
    service_id: str
    target_environment: str
    deployment_type: DeploymentType
    image: str
    tag: str = "latest"
    configuration: Dict[str, Any] = field(default_factory=dict)
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    health_checks: Dict[str, Any] = field(default_factory=dict)
    rollback_config: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentProgress:
    """Deployment progress information."""
    stage: DeploymentStage
    progress: float  # 0.0 to 1.0
    message: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentInfo:
    """Deployment information."""
    id: str
    service_id: str
    deployment_type: DeploymentType
    status: DeploymentStatus
    created_at: datetime
    updated_at: datetime
    config: DeploymentConfig
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    progress: List[DeploymentProgress] = field(default_factory=list)
    current_stage: Optional[DeploymentStage] = None
    rollback_info: Optional[Dict[str, Any]] = None
    deployment_url: Optional[str] = None
    health_status: Optional[str] = None


class DeploymentManager(BaseManager):
    """
    Deployment management for the web dashboard.
    
    Handles:
    - Multi-target deployments (Docker, Kubernetes, Cloud)
    - Deployment progress tracking and real-time updates
    - Rollback functionality with history
    - Configuration validation and preparation
    - Build and push automation
    - Health monitoring and verification
    """
    
    def __init__(self, name: str = "deployment", config: Optional[Dict[str, Any]] = None):
        """Initialize the deployment manager."""
        super().__init__(name, config)
        self._deployments: Dict[str, DeploymentInfo] = {}
        self._deployment_providers: Dict[DeploymentType, Callable] = {}
        self._active_deployments: Dict[str, asyncio.Task] = {}
        
        # Configuration
        self._docker_registry = self.get_config("docker_registry", "localhost:5000")
        self._kubernetes_context = self.get_config("kubernetes_context", "default")
        self._cloud_credentials = self.get_config("cloud_credentials", {})
        self._build_timeout = self.get_config("build_timeout", 600)  # 10 minutes
        self._deploy_timeout = self.get_config("deploy_timeout", 1800)  # 30 minutes
        self._health_check_timeout = self.get_config("health_check_timeout", 300)  # 5 minutes
        
        # Progress callbacks
        self._progress_callbacks: List[Callable] = []
    
    async def _initialize_impl(self) -> None:
        """Initialize the deployment manager."""
        # Register deployment providers
        self._deployment_providers = {
            DeploymentType.DOCKER: self._deploy_docker,
            DeploymentType.KUBERNETES: self._deploy_kubernetes,
            DeploymentType.CLOUD_RUN: self._deploy_cloud_run,
            DeploymentType.AZURE_CONTAINERS: self._deploy_azure_containers,
            DeploymentType.AWS_ECS: self._deploy_aws_ecs,
        }
        
        # Verify deployment tools availability
        await self._verify_deployment_tools()
        
        self.logger.info("Deployment manager initialized with providers: %s", 
                        list(self._deployment_providers.keys()))
    
    async def deploy_service(self, config: DeploymentConfig) -> str:
        """
        Deploy a service with full pipeline.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Deployment ID
        """
        result = await self._safe_execute(
            "deploy_service",
            self._deploy_service_impl,
            config
        )
        return result or ""
    
    async def validate_deployment_config(self, config: DeploymentConfig) -> Dict[str, Any]:
        """
        Validate deployment configuration.
        
        Args:
            config: Deployment configuration to validate
            
        Returns:
            Validation result with errors and warnings
        """
        return await self._safe_execute(
            "validate_deployment_config",
            self._validate_deployment_config_impl,
            config
        ) or {"valid": False, "errors": ["Validation failed"]}
    
    async def cancel_deployment(self, deployment_id: str) -> bool:
        """
        Cancel an active deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            True if cancellation successful
        """
        return await self._safe_execute(
            "cancel_deployment",
            self._cancel_deployment_impl,
            deployment_id
        ) or False
    
    async def get_deployment_logs(self, deployment_id: str, lines: int = 100) -> List[str]:
        """
        Get deployment logs.
        
        Args:
            deployment_id: Deployment identifier
            lines: Number of log lines to return
            
        Returns:
            List of log lines
        """
        return await self._safe_execute(
            "get_deployment_logs",
            self._get_deployment_logs_impl,
            deployment_id,
            lines
        ) or []
    
    async def get_deployment_progress(self, deployment_id: str) -> Optional[DeploymentProgress]:
        """
        Get current deployment progress.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Current progress information
        """
        return await self._safe_execute(
            "get_deployment_progress",
            self._get_deployment_progress_impl,
            deployment_id
        )
    
    # Workflow and Progress Tracking Methods
    
    async def create_deployment_workflow(
        self,
        deployment_type: DeploymentType,
        config: DeploymentConfig
    ) -> DeploymentWorkflow:
        """
        Create a deployment workflow based on deployment type and configuration.
        
        Args:
            deployment_type: Type of deployment
            config: Deployment configuration
            
        Returns:
            Deployment workflow
        """
        workflow_id = str(uuid.uuid4())
        workflow = DeploymentWorkflow(
            id=workflow_id,
            name=f"{deployment_type.value}-{config.service_id}",
            deployment_type=deployment_type,
            timeout_minutes=self._deploy_timeout // 60,
            metadata={"config": config.__dict__}
        )
        
        # Create workflow steps based on deployment type
        steps = await self._create_workflow_steps(deployment_type, config)
        workflow.steps = steps
        
        return workflow
    
    async def _create_workflow_steps(
        self,
        deployment_type: DeploymentType,
        config: DeploymentConfig
    ) -> List[DeploymentStep]:
        """Create workflow steps based on deployment type."""
        steps = []
        
        # Common validation step
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Validate Configuration",
            stage=DeploymentStage.VALIDATION,
            status=DeploymentStatus.PENDING,
            max_retries=1
        ))
        
        # Preparation step
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Prepare Environment",
            stage=DeploymentStage.PREPARATION,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[0].id]
        ))
        
        # Build step (if needed)
        if deployment_type in [DeploymentType.DOCKER, DeploymentType.KUBERNETES]:
            steps.append(DeploymentStep(
                id=str(uuid.uuid4()),
                name="Build Container Image",
                stage=DeploymentStage.BUILD,
                status=DeploymentStatus.PENDING,
                dependencies=[steps[-1].id],
                max_retries=2
            ))
            
            # Push step
            steps.append(DeploymentStep(
                id=str(uuid.uuid4()),
                name="Push Container Image",
                stage=DeploymentStage.PUSH,
                status=DeploymentStatus.PENDING,
                dependencies=[steps[-1].id],
                max_retries=3
            ))
        
        # Deploy step
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Deploy Service",
            stage=DeploymentStage.DEPLOY,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[-1].id],
            max_retries=2
        ))
        
        # Health check step
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Health Check",
            stage=DeploymentStage.HEALTH_CHECK,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[-1].id],
            max_retries=5
        ))
        
        # Finalization step
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Finalize Deployment",
            stage=DeploymentStage.FINALIZATION,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[-1].id]
        ))
        
        return steps
    
    async def execute_workflow(
        self,
        deployment_id: str,
        workflow: DeploymentWorkflow
    ) -> bool:
        """
        Execute a deployment workflow.
        
        Args:
            deployment_id: Deployment identifier
            workflow: Workflow to execute
            
        Returns:
            True if workflow completed successfully
        """
        try:
            self.logger.info(f"Starting workflow execution for deployment {deployment_id}")
            
            # Execute steps sequentially or in parallel
            if workflow.parallel_execution:
                return await self._execute_workflow_parallel(deployment_id, workflow)
            else:
                return await self._execute_workflow_sequential(deployment_id, workflow)
                
        except Exception as e:
            self.logger.error(f"Workflow execution failed for {deployment_id}: {e}")
            
            # Rollback if configured
            if workflow.rollback_on_failure:
                await self._rollback_deployment(deployment_id, str(e))
            
            return False
    
    async def _execute_workflow_sequential(
        self,
        deployment_id: str,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute workflow steps sequentially."""
        for i, step in enumerate(workflow.steps):
            workflow.current_step_index = i
            
            # Check dependencies
            if not await self._check_step_dependencies(step, workflow.steps):
                self.logger.error(f"Dependencies not met for step {step.name}")
                step.status = DeploymentStatus.FAILED
                step.error_message = "Dependencies not met"
                return False
            
            # Execute step with retries
            success = await self._execute_step_with_retries(deployment_id, step, workflow)
            
            if not success:
                self.logger.error(f"Step {step.name} failed after retries")
                return False
            
            # Send progress update
            await self._send_progress_update(
                deployment_id,
                workflow.id,
                step.id,
                step.stage,
                DeploymentStatus.COMPLETED,
                workflow.progress_percentage,
                f"Completed step: {step.name}"
            )
        
        return True
    
    async def _execute_workflow_parallel(
        self,
        deployment_id: str,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute workflow steps in parallel where possible."""
        # Group steps by dependencies
        step_groups = self._group_steps_by_dependencies(workflow.steps)
        
        for group in step_groups:
            # Execute all steps in group concurrently
            tasks = []
            for step in group:
                task = asyncio.create_task(
                    self._execute_step_with_retries(deployment_id, step, workflow)
                )
                tasks.append((step, task))
            
            # Wait for all tasks in group to complete
            for step, task in tasks:
                try:
                    success = await task
                    if not success:
                        self.logger.error(f"Step {step.name} failed in parallel execution")
                        return False
                except Exception as e:
                    self.logger.error(f"Step {step.name} failed with exception: {e}")
                    step.status = DeploymentStatus.FAILED
                    step.error_message = str(e)
                    return False
        
        return True
    
    async def _execute_step_with_retries(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute a single step with retry logic."""
        step.started_at = datetime.utcnow()
        step.status = DeploymentStatus.IN_PROGRESS
        
        for attempt in range(step.max_retries + 1):
            try:
                step.retry_count = attempt
                
                # Send progress update
                await self._send_progress_update(
                    deployment_id,
                    workflow.id,
                    step.id,
                    step.stage,
                    DeploymentStatus.IN_PROGRESS,
                    workflow.progress_percentage,
                    f"Executing step: {step.name} (attempt {attempt + 1})"
                )
                
                # Execute the actual step
                success = await self._execute_single_step(deployment_id, step, workflow)
                
                if success:
                    step.status = DeploymentStatus.COMPLETED
                    step.completed_at = datetime.utcnow()
                    if step.started_at:
                        step.duration = (step.completed_at - step.started_at).total_seconds()
                    return True
                
                # If not successful and we have retries left, wait before retry
                if attempt < step.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Step {step.name} failed, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"Step {step.name} failed with exception: {e}")
                step.error_message = str(e)
                step.logs.append(f"Error: {str(e)}")
                
                if attempt < step.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
        
        # All retries exhausted
        step.status = DeploymentStatus.FAILED
        step.completed_at = datetime.utcnow()
        if step.started_at:
            step.duration = (step.completed_at - step.started_at).total_seconds()
        
        return False
    
    async def _execute_single_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute a single deployment step."""
        try:
            if step.stage == DeploymentStage.VALIDATION:
                return await self._execute_validation_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.PREPARATION:
                return await self._execute_preparation_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.BUILD:
                return await self._execute_build_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.PUSH:
                return await self._execute_push_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.DEPLOY:
                return await self._execute_deploy_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.HEALTH_CHECK:
                return await self._execute_health_check_step(deployment_id, step, workflow)
            elif step.stage == DeploymentStage.FINALIZATION:
                return await self._execute_finalization_step(deployment_id, step, workflow)
            else:
                step.logs.append(f"Unknown step stage: {step.stage}")
                return False
                
        except Exception as e:
            step.logs.append(f"Step execution failed: {str(e)}")
            raise
    
    async def _send_progress_update(
        self,
        deployment_id: str,
        workflow_id: str,
        step_id: Optional[str],
        stage: DeploymentStage,
        status: DeploymentStatus,
        progress_percentage: float,
        message: str,
        logs: Optional[List[str]] = None
    ) -> None:
        """Send progress update to all registered callbacks."""
        update = DeploymentProgressUpdate(
            deployment_id=deployment_id,
            workflow_id=workflow_id,
            step_id=step_id,
            stage=stage,
            status=status,
            progress_percentage=progress_percentage,
            message=message,
            logs=logs or []
        )
        
        # Call all registered progress callbacks
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                self.logger.error(f"Progress callback failed: {e}")
    
    async def add_progress_callback(self, callback: Callable) -> None:
        """Add a progress callback."""
        self._progress_callbacks.append(callback)
    
    async def remove_progress_callback(self, callback: Callable) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def _group_steps_by_dependencies(self, steps: List[DeploymentStep]) -> List[List[DeploymentStep]]:
        """Group steps by their dependencies for parallel execution."""
        groups = []
        remaining_steps = steps.copy()
        completed_step_ids = set()
        
        while remaining_steps:
            current_group = []
            
            # Find steps that can be executed (all dependencies met)
            for step in remaining_steps[:]:
                if all(dep_id in completed_step_ids for dep_id in step.dependencies):
                    current_group.append(step)
                    remaining_steps.remove(step)
            
            if not current_group:
                # Circular dependency or other issue
                self.logger.error("Unable to resolve step dependencies")
                break
            
            groups.append(current_group)
            completed_step_ids.update(step.id for step in current_group)
        
        return groups
    
    async def _check_step_dependencies(
        self,
        step: DeploymentStep,
        all_steps: List[DeploymentStep]
    ) -> bool:
        """Check if step dependencies are satisfied."""
        if not step.dependencies:
            return True
        
        step_dict = {s.id: s for s in all_steps}
        
        for dep_id in step.dependencies:
            dep_step = step_dict.get(dep_id)
            if not dep_step or dep_step.status != DeploymentStatus.COMPLETED:
                return False
        
        return True
    
    def add_progress_callback(self, callback: Callable[[str, DeploymentProgress], None]) -> None:
        """
        Add a progress callback for real-time updates.
        
        Args:
            callback: Function to call with deployment_id and progress
        """
        self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable) -> None:
        """
        Remove a progress callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    async def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """
        Get deployment status.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Deployment information or None if not found
        """
        return await self._safe_execute(
            "get_deployment_status",
            self._get_deployment_status_impl,
            deployment_id
        )
    
    async def rollback_deployment(self, deployment_id: str) -> bool:
        """
        Rollback a deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            True if rollback successful
        """
        result = await self._safe_execute(
            "rollback_deployment",
            self._rollback_deployment_impl,
            deployment_id
        )
        return result is not None and result
    
    async def list_deployments(self, service_id: Optional[str] = None) -> List[DeploymentInfo]:
        """
        List deployments.
        
        Args:
            service_id: Optional service filter
            
        Returns:
            List of deployments
        """
        return await self._safe_execute(
            "list_deployments",
            self._list_deployments_impl,
            service_id
        ) or []
    
    # Implementation methods (to be implemented in future tasks)
    
    async def _deploy_service_impl(self, config: DeploymentConfig) -> str:
        """Implementation for deploying service."""
        # TODO: Implement actual deployment logic
        deployment_id = f"deploy_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        deployment = DeploymentInfo(
            id=deployment_id,
            service_id=config.service_id,
            deployment_type=config.deployment_type,
            status=DeploymentStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            config=config,
            logs=[]
        )
        self._deployments[deployment_id] = deployment
        return deployment_id
    
    async def _get_deployment_status_impl(self, deployment_id: str) -> Optional[DeploymentInfo]:
        """Implementation for getting deployment status."""
        return self._deployments.get(deployment_id)
    
    async def _rollback_deployment_impl(self, deployment_id: str) -> bool:
        """Implementation for rolling back deployment."""
        # TODO: Implement actual rollback logic
        if deployment_id in self._deployments:
            self._deployments[deployment_id].status = DeploymentStatus.ROLLED_BACK
            self._deployments[deployment_id].updated_at = datetime.utcnow()
            return True
        return False
    
    async def _list_deployments_impl(self, service_id: Optional[str] = None) -> List[DeploymentInfo]:
        """Implementation for listing deployments."""
        deployments = list(self._deployments.values())
        if service_id:
            deployments = [d for d in deployments if d.service_id == service_id]
        return sorted(deployments, key=lambda x: x.created_at, reverse=True)
    
    # New implementation methods
    
    async def _verify_deployment_tools(self) -> None:
        """Verify that required deployment tools are available."""
        tools_to_check = [
            ("docker", "Docker"),
            ("kubectl", "Kubernetes"),
        ]
        
        for tool, name in tools_to_check:
            try:
                result = subprocess.run([tool, "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.logger.info(f"{name} is available")
                else:
                    self.logger.warning(f"{name} is not available or not working properly")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.logger.warning(f"{name} tool not found in PATH")
    
    async def _validate_deployment_config_impl(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Implementation for validating deployment configuration."""
        errors = []
        warnings = []
        
        # Basic validation
        if not config.service_id:
            errors.append("Service ID is required")
        
        if not config.image:
            errors.append("Container image is required")
        
        if not config.target_environment:
            errors.append("Target environment is required")
        
        # Resource validation
        try:
            if config.resources.replicas < 1:
                errors.append("Replicas must be at least 1")
            if config.resources.replicas > 100:
                warnings.append("High replica count may consume significant resources")
        except (ValueError, TypeError):
            errors.append("Invalid resource configuration")
        
        # Network validation
        for port in config.network.ports:
            if not isinstance(port.get("containerPort"), int):
                errors.append(f"Invalid container port: {port}")
            if port.get("containerPort", 0) < 1 or port.get("containerPort", 0) > 65535:
                errors.append(f"Container port out of range: {port.get('containerPort')}")
        
        # Environment-specific validation
        if config.deployment_type == DeploymentType.KUBERNETES:
            if not config.target_environment.startswith("k8s-"):
                warnings.append("Kubernetes deployments typically use 'k8s-' prefix for environments")
        
        # Security validation
        if not config.security.image_pull_secrets and config.image.startswith("private"):
            warnings.append("Private images may require image pull secrets")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.utcnow().isoformat()
        }
    
    async def _deploy_service_impl(self, config: DeploymentConfig) -> str:
        """Implementation for deploying service with full pipeline."""
        deployment_id = str(uuid.uuid4())
        
        # Create deployment info
        deployment = DeploymentInfo(
            id=deployment_id,
            service_id=config.service_id,
            deployment_type=config.deployment_type,
            status=DeploymentStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            config=config,
            logs=[],
            progress=[]
        )
        
        self._deployments[deployment_id] = deployment
        
        # Start deployment pipeline asynchronously
        task = asyncio.create_task(self._run_deployment_pipeline(deployment_id))
        self._active_deployments[deployment_id] = task
        
        return deployment_id
    
    async def _run_deployment_pipeline(self, deployment_id: str) -> None:
        """Run the complete deployment pipeline."""
        deployment = self._deployments[deployment_id]
        
        try:
            # Stage 1: Validation
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.VALIDATION, 0.0, "Validating configuration"
            )
            
            validation_result = await self._validate_deployment_config_impl(deployment.config)
            if not validation_result["valid"]:
                raise Exception(f"Configuration validation failed: {validation_result['errors']}")
            
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.VALIDATION, 1.0, "Configuration validated"
            )
            
            # Stage 2: Preparation
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.PREPARATION, 0.0, "Preparing deployment"
            )
            
            await self._prepare_deployment(deployment_id)
            
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.PREPARATION, 1.0, "Deployment prepared"
            )
            
            # Stage 3: Build (if needed)
            if deployment.config.deployment_type in [DeploymentType.DOCKER, DeploymentType.KUBERNETES]:
                await self._update_deployment_progress(
                    deployment_id, DeploymentStage.BUILD, 0.0, "Building container image"
                )
                
                await self._build_image(deployment_id)
                
                await self._update_deployment_progress(
                    deployment_id, DeploymentStage.BUILD, 1.0, "Container image built"
                )
            
            # Stage 4: Deploy
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, 0.0, "Starting deployment"
            )
            
            deployment_provider = self._deployment_providers.get(deployment.config.deployment_type)
            if not deployment_provider:
                raise Exception(f"No provider for deployment type: {deployment.config.deployment_type}")
            
            await deployment_provider(deployment_id)
            
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, 1.0, "Deployment completed"
            )
            
            # Stage 5: Verify
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.VERIFY, 0.0, "Verifying deployment"
            )
            
            await self._verify_deployment(deployment_id)
            
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.VERIFY, 1.0, "Deployment verified"
            )
            
            # Mark as completed
            deployment.status = DeploymentStatus.COMPLETED
            deployment.updated_at = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.updated_at = datetime.utcnow()
            
            await self._update_deployment_progress(
                deployment_id, deployment.current_stage or DeploymentStage.DEPLOY, 
                0.0, f"Deployment failed: {str(e)}"
            )
        
        finally:
            # Cleanup
            if deployment_id in self._active_deployments:
                del self._active_deployments[deployment_id]
    
    async def _update_deployment_progress(self, deployment_id: str, stage: DeploymentStage, 
                                        progress: float, message: str, 
                                        details: Optional[Dict[str, Any]] = None) -> None:
        """Update deployment progress and notify callbacks."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return
        
        progress_info = DeploymentProgress(
            stage=stage,
            progress=progress,
            message=message,
            timestamp=datetime.utcnow(),
            details=details
        )
        
        deployment.progress.append(progress_info)
        deployment.current_stage = stage
        deployment.updated_at = datetime.utcnow()
        
        # Add to logs
        log_message = f"[{stage.value.upper()}] {message}"
        deployment.logs.append(f"{datetime.utcnow().isoformat()} - {log_message}")
        
        # Notify callbacks
        for callback in self._progress_callbacks:
            try:
                callback(deployment_id, progress_info)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
    
    async def _prepare_deployment(self, deployment_id: str) -> None:
        """Prepare deployment environment and resources."""
        deployment = self._deployments[deployment_id]
        
        # Create temporary directory for deployment files
        temp_dir = tempfile.mkdtemp(prefix=f"deploy_{deployment_id}_")
        deployment.config.configuration["temp_dir"] = temp_dir
        
        # Generate deployment manifests based on type
        if deployment.config.deployment_type == DeploymentType.KUBERNETES:
            await self._generate_kubernetes_manifests(deployment_id, temp_dir)
        elif deployment.config.deployment_type == DeploymentType.DOCKER:
            await self._generate_docker_compose(deployment_id, temp_dir)
        
        await asyncio.sleep(1)  # Simulate preparation time
    
    async def _build_image(self, deployment_id: str) -> None:
        """Build container image if needed."""
        deployment = self._deployments[deployment_id]
        
        # Simulate image building
        for i in range(5):
            await asyncio.sleep(1)
            progress = (i + 1) / 5
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.BUILD, progress, 
                f"Building image... {int(progress * 100)}%"
            )
    
    async def _verify_deployment(self, deployment_id: str) -> None:
        """Verify deployment health and readiness."""
        deployment = self._deployments[deployment_id]
        
        # Simulate health checks
        for i in range(3):
            await asyncio.sleep(2)
            progress = (i + 1) / 3
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.VERIFY, progress,
                f"Health check {i + 1}/3"
            )
        
        deployment.health_status = "healthy"
        deployment.deployment_url = f"https://{deployment.config.service_id}.{deployment.config.target_environment}.example.com"
    
    # Deployment provider implementations
    
    async def _deploy_docker(self, deployment_id: str) -> None:
        """Deploy using Docker."""
        deployment = self._deployments[deployment_id]
        
        # Simulate Docker deployment
        steps = ["Pulling image", "Creating container", "Starting container", "Configuring network"]
        
        for i, step in enumerate(steps):
            await asyncio.sleep(2)
            progress = (i + 1) / len(steps)
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, progress, step
            )
    
    async def _deploy_kubernetes(self, deployment_id: str) -> None:
        """Deploy using Kubernetes."""
        deployment = self._deployments[deployment_id]
        
        # Simulate Kubernetes deployment
        steps = ["Applying manifests", "Creating pods", "Waiting for readiness", "Configuring services"]
        
        for i, step in enumerate(steps):
            await asyncio.sleep(3)
            progress = (i + 1) / len(steps)
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, progress, step
            )
    
    async def _deploy_cloud_run(self, deployment_id: str) -> None:
        """Deploy using Google Cloud Run."""
        deployment = self._deployments[deployment_id]
        
        # Simulate Cloud Run deployment
        steps = ["Uploading image", "Creating service", "Allocating resources", "Starting instances"]
        
        for i, step in enumerate(steps):
            await asyncio.sleep(2)
            progress = (i + 1) / len(steps)
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, progress, step
            )
    
    async def _deploy_azure_containers(self, deployment_id: str) -> None:
        """Deploy using Azure Container Instances."""
        deployment = self._deployments[deployment_id]
        
        # Simulate Azure deployment
        steps = ["Creating container group", "Pulling image", "Starting containers", "Configuring networking"]
        
        for i, step in enumerate(steps):
            await asyncio.sleep(2)
            progress = (i + 1) / len(steps)
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, progress, step
            )
    
    async def _deploy_aws_ecs(self, deployment_id: str) -> None:
        """Deploy using AWS ECS."""
        deployment = self._deployments[deployment_id]
        
        # Simulate ECS deployment
        steps = ["Creating task definition", "Starting service", "Launching tasks", "Registering with load balancer"]
        
        for i, step in enumerate(steps):
            await asyncio.sleep(2)
            progress = (i + 1) / len(steps)
            await self._update_deployment_progress(
                deployment_id, DeploymentStage.DEPLOY, progress, step
            )
    
    async def _generate_kubernetes_manifests(self, deployment_id: str, temp_dir: str) -> None:
        """Generate Kubernetes deployment manifests."""
        deployment = self._deployments[deployment_id]
        config = deployment.config
        
        # Generate deployment manifest
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": config.service_id,
                "namespace": config.target_environment
            },
            "spec": {
                "replicas": config.resources.replicas,
                "selector": {
                    "matchLabels": {
                        "app": config.service_id
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": config.service_id
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": config.service_id,
                            "image": f"{config.image}:{config.tag}",
                            "ports": [{"containerPort": port["containerPort"]} for port in config.network.ports],
                            "env": [{"name": k, "value": v} for k, v in config.environment_variables.items()],
                            "resources": {
                                "requests": {
                                    "cpu": config.resources.cpu,
                                    "memory": config.resources.memory
                                }
                            }
                        }]
                    }
                }
            }
        }
        
        # Write manifest to file
        manifest_path = Path(temp_dir) / "deployment.yaml"
        with open(manifest_path, "w") as f:
            import yaml
            yaml.dump(deployment_manifest, f)
    
    async def _generate_docker_compose(self, deployment_id: str, temp_dir: str) -> None:
        """Generate Docker Compose configuration."""
        deployment = self._deployments[deployment_id]
        config = deployment.config
        
        compose_config = {
            "version": "3.8",
            "services": {
                config.service_id: {
                    "image": f"{config.image}:{config.tag}",
                    "ports": [f"{port['hostPort']}:{port['containerPort']}" 
                             for port in config.network.ports if 'hostPort' in port],
                    "environment": config.environment_variables,
                    "restart": "unless-stopped"
                }
            }
        }
        
        # Write compose file
        compose_path = Path(temp_dir) / "docker-compose.yml"
        with open(compose_path, "w") as f:
            import yaml
            yaml.dump(compose_config, f)
    
    async def _cancel_deployment_impl(self, deployment_id: str) -> bool:
        """Implementation for cancelling deployment."""
        if deployment_id in self._active_deployments:
            task = self._active_deployments[deployment_id]
            task.cancel()
            
            deployment = self._deployments.get(deployment_id)
            if deployment:
                deployment.status = DeploymentStatus.CANCELLED
                deployment.updated_at = datetime.utcnow()
                deployment.logs.append(f"{datetime.utcnow().isoformat()} - Deployment cancelled")
            
            del self._active_deployments[deployment_id]
            return True
        
        return False
    
    async def _get_deployment_logs_impl(self, deployment_id: str, lines: int = 100) -> List[str]:
        """Implementation for getting deployment logs."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return []
        
        # Return the last N lines
        return deployment.logs[-lines:] if deployment.logs else []
    
    async def _get_deployment_progress_impl(self, deployment_id: str) -> Optional[DeploymentProgress]:
        """Implementation for getting deployment progress."""
        deployment = self._deployments.get(deployment_id)
        if not deployment or not deployment.progress:
            return None
        
        # Return the latest progress
        return deployment.progress[-1]
    
    # Additional helper methods for API integration
    
    async def get_deployment_history(self, service_id: str, limit: int = 50) -> List[DeploymentInfo]:
        """
        Get deployment history for a service.
        
        Args:
            service_id: Service identifier
            limit: Maximum number of deployments to return
            
        Returns:
            List of deployment history
        """
        return await self._safe_execute(
            "get_deployment_history",
            self._get_deployment_history_impl,
            service_id,
            limit
        ) or []
    
    async def _get_deployment_history_impl(self, service_id: str, limit: int = 50) -> List[DeploymentInfo]:
        """Implementation for getting deployment history."""
        deployments = [d for d in self._deployments.values() if d.service_id == service_id]
        deployments.sort(key=lambda x: x.created_at, reverse=True)
        return deployments[:limit]
    
    async def get_active_deployments(self) -> List[DeploymentInfo]:
        """
        Get currently active deployments.
        
        Returns:
            List of active deployments
        """
        return await self._safe_execute(
            "get_active_deployments",
            self._get_active_deployments_impl
        ) or []
    
    async def _get_active_deployments_impl(self) -> List[DeploymentInfo]:
        """Implementation for getting active deployments."""
        active_statuses = {
            DeploymentStatus.PENDING,
            DeploymentStatus.VALIDATING,
            DeploymentStatus.PREPARING,
            DeploymentStatus.BUILDING,
            DeploymentStatus.PUSHING,
            DeploymentStatus.DEPLOYING,
            DeploymentStatus.IN_PROGRESS
        }
        
        return [d for d in self._deployments.values() if d.status in active_statuses]
    
    async def get_deployment_metrics(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get deployment metrics and statistics.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Deployment metrics
        """
        return await self._safe_execute(
            "get_deployment_metrics",
            self._get_deployment_metrics_impl,
            deployment_id
        ) or {}
    
    async def _get_deployment_metrics_impl(self, deployment_id: str) -> Dict[str, Any]:
        """Implementation for getting deployment metrics."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return {}
        
        # Calculate deployment duration
        duration = None
        if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
            duration = (deployment.updated_at - deployment.created_at).total_seconds()
        
        # Count stages completed
        stages_completed = len(set(p.stage for p in deployment.progress))
        total_stages = len(DeploymentStage)
        
        # Calculate overall progress
        if deployment.status == DeploymentStatus.COMPLETED:
            overall_progress = 1.0
        elif deployment.status == DeploymentStatus.FAILED:
            overall_progress = 0.0
        else:
            overall_progress = stages_completed / total_stages if total_stages > 0 else 0.0
        
        return {
            "deployment_id": deployment_id,
            "service_id": deployment.service_id,
            "status": deployment.status.value,
            "deployment_type": deployment.deployment_type.value,
            "duration_seconds": duration,
            "stages_completed": stages_completed,
            "total_stages": total_stages,
            "overall_progress": overall_progress,
            "log_lines": len(deployment.logs),
            "error_message": deployment.error_message,
            "health_status": deployment.health_status,
            "deployment_url": deployment.deployment_url,
            "created_at": deployment.created_at.isoformat(),
            "updated_at": deployment.updated_at.isoformat()
        }
    
    async def cleanup_old_deployments(self, days: int = 30) -> int:
        """
        Clean up old deployment records.
        
        Args:
            days: Number of days to keep deployments
            
        Returns:
            Number of deployments cleaned up
        """
        return await self._safe_execute(
            "cleanup_old_deployments",
            self._cleanup_old_deployments_impl,
            days
        ) or 0
    
    async def _cleanup_old_deployments_impl(self, days: int = 30) -> int:
        """Implementation for cleaning up old deployments."""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deployments_to_remove = []
        
        for deployment_id, deployment in self._deployments.items():
            # Don't remove active deployments
            if deployment_id in self._active_deployments:
                continue
            
            # Don't remove recent deployments
            if deployment.created_at > cutoff_date:
                continue
            
            # Only remove completed or failed deployments
            if deployment.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED, 
                                   DeploymentStatus.CANCELLED, DeploymentStatus.ROLLED_BACK]:
                deployments_to_remove.append(deployment_id)
        
        # Remove old deployments
        for deployment_id in deployments_to_remove:
            del self._deployments[deployment_id]
        
        self.logger.info(f"Cleaned up {len(deployments_to_remove)} old deployments")
        return len(deployments_to_remove)
    
    async def estimate_deployment_time(self, config: DeploymentConfig) -> Dict[str, Any]:
        """
        Estimate deployment time based on configuration.
        
        Args:
            config: Deployment configuration
            
        Returns:
            Time estimation details
        """
        return await self._safe_execute(
            "estimate_deployment_time",
            self._estimate_deployment_time_impl,
            config
        ) or {}
    
    async def _estimate_deployment_time_impl(self, config: DeploymentConfig) -> Dict[str, Any]:
        """Implementation for estimating deployment time."""
        # Base times in seconds for different deployment types
        base_times = {
            DeploymentType.DOCKER: 120,  # 2 minutes
            DeploymentType.KUBERNETES: 300,  # 5 minutes
            DeploymentType.CLOUD_RUN: 180,  # 3 minutes
            DeploymentType.AZURE_CONTAINERS: 240,  # 4 minutes
            DeploymentType.AWS_ECS: 360,  # 6 minutes
        }
        
        base_time = base_times.get(config.deployment_type, 300)
        
        # Adjust based on configuration
        multiplier = 1.0
        
        # More replicas = more time
        if config.resources.replicas > 1:
            multiplier += (config.resources.replicas - 1) * 0.2
        
        # Complex networking = more time
        if len(config.network.ports) > 2:
            multiplier += 0.3
        
        # Many environment variables = slight increase
        if len(config.environment_variables) > 10:
            multiplier += 0.1
        
        # Volumes = more time
        if config.volumes:
            multiplier += len(config.volumes) * 0.1
        
        estimated_seconds = int(base_time * multiplier)
        
        return {
            "estimated_seconds": estimated_seconds,
            "estimated_minutes": round(estimated_seconds / 60, 1),
            "base_time": base_time,
            "complexity_multiplier": round(multiplier, 2),
            "factors": {
                "replicas": config.resources.replicas,
                "ports": len(config.network.ports),
                "env_vars": len(config.environment_variables),
                "volumes": len(config.volumes)
            }
        }
    
    async def _get_deployment_logs_impl(self, deployment_id: str, lines: int) -> List[str]:
        """Implementation for getting deployment logs."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return []
        
        return deployment.logs[-lines:] if lines > 0 else deployment.logs
    
    async def _get_deployment_progress_impl(self, deployment_id: str) -> Optional[DeploymentProgress]:
        """Implementation for getting deployment progress."""
        deployment = self._deployments.get(deployment_id)
        if not deployment or not deployment.progress:
            return None
        
        return deployment.progress[-1]  # Return latest progress
    
    # Step execution methods
    
    async def _execute_validation_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute validation step."""
        try:
            step.logs.append("Starting configuration validation")
            
            # Get deployment config from workflow metadata
            config_dict = workflow.metadata.get("config", {})
            
            # Validate required fields
            required_fields = ["service_id", "target_environment", "deployment_type"]
            for field in required_fields:
                if not config_dict.get(field):
                    step.logs.append(f"Missing required field: {field}")
                    return False
            
            # Validate deployment type specific requirements
            deployment_type = workflow.deployment_type
            if deployment_type == DeploymentType.DOCKER:
                if not config_dict.get("image_name"):
                    step.logs.append("Docker deployment requires image_name")
                    return False
            
            elif deployment_type == DeploymentType.KUBERNETES:
                if not config_dict.get("namespace"):
                    step.logs.append("Kubernetes deployment requires namespace")
                    return False
            
            # Validate environment variables
            env_vars = config_dict.get("environment_variables", {})
            if env_vars:
                step.logs.append(f"Validated {len(env_vars)} environment variables")
            
            step.logs.append("Configuration validation completed successfully")
            return True
            
        except Exception as e:
            step.logs.append(f"Validation failed: {str(e)}")
            return False
    
    async def _execute_preparation_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute preparation step."""
        try:
            step.logs.append("Starting environment preparation")
            
            # Create necessary directories
            temp_dir = tempfile.mkdtemp(prefix=f"deploy_{deployment_id}_")
            step.metadata["temp_dir"] = temp_dir
            step.logs.append(f"Created temporary directory: {temp_dir}")
            
            # Prepare configuration files
            config_dict = workflow.metadata.get("config", {})
            
            # Write environment file
            env_file = os.path.join(temp_dir, ".env")
            env_vars = config_dict.get("environment_variables", {})
            with open(env_file, "w") as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            step.logs.append(f"Created environment file with {len(env_vars)} variables")
            
            step.logs.append("Environment preparation completed successfully")
            return True
            
        except Exception as e:
            step.logs.append(f"Preparation failed: {str(e)}")
            return False
    
    async def _execute_build_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute build step."""
        try:
            step.logs.append("Starting container build")
            
            config_dict = workflow.metadata.get("config", {})
            image_name = config_dict.get("image_name", f"{config_dict.get('service_id')}:latest")
            
            # Build Docker image
            build_context = config_dict.get("build_context", ".")
            dockerfile = config_dict.get("dockerfile", "Dockerfile")
            
            build_cmd = [
                "docker", "build",
                "-t", image_name,
                "-f", dockerfile,
                build_context
            ]
            
            step.logs.append(f"Building image: {image_name}")
            step.logs.append(f"Build command: {' '.join(build_cmd)}")
            
            # Execute build command (simulated for now)
            await asyncio.sleep(2)  # Simulate build time
            step.logs.append("Container build completed successfully (simulated)")
            step.metadata["image_name"] = image_name
            return True
                
        except Exception as e:
            step.logs.append(f"Build failed: {str(e)}")
            return False
    
    async def _execute_push_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute push step."""
        try:
            step.logs.append("Starting image push")
            
            # Get image name from previous step
            build_step = None
            for s in workflow.steps:
                if s.stage == DeploymentStage.BUILD:
                    build_step = s
                    break
            
            if not build_step or "image_name" not in build_step.metadata:
                step.logs.append("No image found from build step")
                return False
            
            image_name = build_step.metadata["image_name"]
            registry_image = f"{self._docker_registry}/{image_name}"
            
            step.logs.append(f"Pushing image to registry: {registry_image}")
            
            # Simulate push (in real implementation would use docker commands)
            await asyncio.sleep(1)
            step.logs.append("Image push completed successfully (simulated)")
            step.metadata["registry_image"] = registry_image
            return True
                
        except Exception as e:
            step.logs.append(f"Push failed: {str(e)}")
            return False
    
    async def _execute_deploy_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute deploy step."""
        try:
            step.logs.append("Starting service deployment")
            
            deployment_type = workflow.deployment_type
            
            if deployment_type == DeploymentType.DOCKER:
                return await self._deploy_docker_service(step, workflow)
            elif deployment_type == DeploymentType.KUBERNETES:
                return await self._deploy_kubernetes_service(step, workflow)
            elif deployment_type == DeploymentType.CLOUD_RUN:
                return await self._deploy_cloud_run_service(step, workflow)
            else:
                step.logs.append(f"Unsupported deployment type: {deployment_type}")
                return False
                
        except Exception as e:
            step.logs.append(f"Deploy failed: {str(e)}")
            return False
    
    async def _execute_health_check_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute health check step."""
        try:
            step.logs.append("Starting health check")
            
            config_dict = workflow.metadata.get("config", {})
            health_check_url = config_dict.get("health_check_url")
            
            if not health_check_url:
                step.logs.append("No health check URL configured, skipping")
                return True
            
            # Simulate health check
            step.logs.append(f"Performing health check on {health_check_url}")
            await asyncio.sleep(1)
            step.logs.append("Health check passed (simulated)")
            return True
            
        except Exception as e:
            step.logs.append(f"Health check failed: {str(e)}")
            return False
    
    async def _execute_finalization_step(
        self,
        deployment_id: str,
        step: DeploymentStep,
        workflow: DeploymentWorkflow
    ) -> bool:
        """Execute finalization step."""
        try:
            step.logs.append("Starting deployment finalization")
            
            # Clean up temporary resources
            for s in workflow.steps:
                temp_dir = s.metadata.get("temp_dir")
                if temp_dir and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
                    step.logs.append(f"Cleaned up temporary directory: {temp_dir}")
            
            # Update deployment status
            deployment = self._deployments.get(deployment_id)
            if deployment:
                deployment.status = DeploymentStatus.COMPLETED
                deployment.updated_at = datetime.utcnow()
                step.logs.append("Updated deployment status to completed")
            
            step.logs.append("Deployment finalization completed successfully")
            return True
            
        except Exception as e:
            step.logs.append(f"Finalization failed: {str(e)}")
            return False
    
    # Deployment service methods
    
    async def _deploy_docker_service(self, step: DeploymentStep, workflow: DeploymentWorkflow) -> bool:
        """Deploy service using Docker."""
        try:
            config_dict = workflow.metadata.get("config", {})
            service_id = config_dict.get("service_id")
            
            step.logs.append(f"Deploying Docker service: {service_id}")
            
            # Simulate Docker deployment
            await asyncio.sleep(1)
            step.logs.append("Docker service deployed successfully (simulated)")
            return True
            
        except Exception as e:
            step.logs.append(f"Docker deployment failed: {str(e)}")
            return False
    
    async def _deploy_kubernetes_service(self, step: DeploymentStep, workflow: DeploymentWorkflow) -> bool:
        """Deploy service using Kubernetes."""
        try:
            config_dict = workflow.metadata.get("config", {})
            service_id = config_dict.get("service_id")
            namespace = config_dict.get("namespace", "default")
            
            step.logs.append(f"Deploying Kubernetes service: {service_id} in namespace: {namespace}")
            
            # Simulate Kubernetes deployment
            await asyncio.sleep(2)
            step.logs.append("Kubernetes service deployed successfully (simulated)")
            return True
            
        except Exception as e:
            step.logs.append(f"Kubernetes deployment failed: {str(e)}")
            return False
    
    async def _deploy_cloud_run_service(self, step: DeploymentStep, workflow: DeploymentWorkflow) -> bool:
        """Deploy service using Google Cloud Run."""
        try:
            config_dict = workflow.metadata.get("config", {})
            service_id = config_dict.get("service_id")
            
            step.logs.append(f"Deploying Cloud Run service: {service_id}")
            
            # Simulate Cloud Run deployment
            await asyncio.sleep(1)
            step.logs.append("Cloud Run service deployed successfully (simulated)")
            return True
            
        except Exception as e:
            step.logs.append(f"Cloud Run deployment failed: {str(e)}")
            return False
    
    # Rollback functionality
    
    async def rollback_deployment(self, deployment_id: str, reason: str = "Manual rollback") -> bool:
        """
        Rollback a deployment.
        
        Args:
            deployment_id: Deployment to rollback
            reason: Reason for rollback
            
        Returns:
            True if rollback successful
        """
        return await self._safe_execute(
            "rollback_deployment",
            self._rollback_deployment,
            deployment_id,
            reason
        ) or False
    
    async def _rollback_deployment(self, deployment_id: str, reason: str) -> bool:
        """Implementation for deployment rollback."""
        try:
            deployment = self._deployments.get(deployment_id)
            if not deployment:
                self.logger.error(f"Deployment {deployment_id} not found for rollback")
                return False
            
            self.logger.info(f"Starting rollback for deployment {deployment_id}: {reason}")
            
            # Create rollback info
            rollback_info = DeploymentRollbackInfo(
                rollback_id=str(uuid.uuid4()),
                original_deployment_id=deployment_id,
                reason=reason,
                initiated_by="system"  # In real implementation, would get from context
            )
            
            # Update deployment status
            deployment.status = DeploymentStatus.ROLLED_BACK
            deployment.updated_at = datetime.utcnow()
            
            # Add rollback steps
            rollback_steps = await self._create_rollback_steps(deployment)
            rollback_info.steps = rollback_steps
            
            # Execute rollback steps
            for step in rollback_steps:
                success = await self._execute_rollback_step(step, deployment)
                if not success:
                    self.logger.error(f"Rollback step {step.name} failed")
                    rollback_info.status = DeploymentStatus.FAILED
                    return False
            
            rollback_info.status = DeploymentStatus.COMPLETED
            rollback_info.completed_at = datetime.utcnow()
            
            self.logger.info(f"Rollback completed successfully for deployment {deployment_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed for deployment {deployment_id}: {e}")
            return False
    
    async def _create_rollback_steps(self, deployment: 'DeploymentInfo') -> List[DeploymentStep]:
        """Create rollback steps for a deployment."""
        steps = []
        
        # Stop current service
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Stop Current Service",
            stage=DeploymentStage.DEPLOY,
            status=DeploymentStatus.PENDING
        ))
        
        # Restore previous version (if available)
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Restore Previous Version",
            stage=DeploymentStage.DEPLOY,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[0].id]
        ))
        
        # Verify rollback
        steps.append(DeploymentStep(
            id=str(uuid.uuid4()),
            name="Verify Rollback",
            stage=DeploymentStage.HEALTH_CHECK,
            status=DeploymentStatus.PENDING,
            dependencies=[steps[1].id]
        ))
        
        return steps
    
    async def _execute_rollback_step(self, step: DeploymentStep, deployment: 'DeploymentInfo') -> bool:
        """Execute a single rollback step."""
        try:
            step.started_at = datetime.utcnow()
            step.status = DeploymentStatus.IN_PROGRESS
            
            if step.name == "Stop Current Service":
                step.logs.append("Stopping current service")
                await asyncio.sleep(1)  # Simulate stop
                step.logs.append("Service stopped successfully")
                
            elif step.name == "Restore Previous Version":
                step.logs.append("Restoring previous version")
                await asyncio.sleep(2)  # Simulate restore
                step.logs.append("Previous version restored successfully")
                
            elif step.name == "Verify Rollback":
                step.logs.append("Verifying rollback")
                await asyncio.sleep(1)  # Simulate verification
                step.logs.append("Rollback verified successfully")
            
            step.status = DeploymentStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            if step.started_at:
                step.duration = (step.completed_at - step.started_at).total_seconds()
            
            return True
            
        except Exception as e:
            step.status = DeploymentStatus.FAILED
            step.error_message = str(e)
            step.logs.append(f"Rollback step failed: {str(e)}")
            return False
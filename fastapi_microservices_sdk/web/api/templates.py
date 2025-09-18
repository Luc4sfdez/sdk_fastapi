"""
Template Management REST API
Advanced API endpoints for template management, validation, and analytics
"""
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import io
import zipfile
import logging

from ..core.dependency_container import DependencyContainer
from ..templates_mgmt.template_manager import TemplateManager
from ..templates_mgmt.template_validator import TemplateValidator, ValidationResult
from ..templates_mgmt.template_analytics import TemplateAnalytics, TemplateUsageEvent

logger = logging.getLogger(__name__)

# Pydantic models for API
class TemplateCreateRequest(BaseModel):
    name: str = Field(..., description="Template name")
    type: str = Field(..., description="Template type")
    description: Optional[str] = Field(None, description="Template description")
    content: str = Field(..., description="Template content")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    author: Optional[str] = Field(None, description="Template author")
    version: str = Field("1.0.0", description="Template version")

class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    content: Optional[str] = Field(None, description="Template content")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    version: Optional[str] = Field(None, description="Template version")

class TemplateGenerateRequest(BaseModel):
    template_id: str = Field(..., description="Template ID")
    parameters: Dict[str, Any] = Field(..., description="Generation parameters")
    output_format: str = Field("text", description="Output format")

class TemplateTestRequest(BaseModel):
    template_id: str = Field(..., description="Template ID")
    test_case: Dict[str, Any] = Field(..., description="Test case data")

class TemplateValidationRequest(BaseModel):
    content: str = Field(..., description="Template content to validate")
    template_type: str = Field("custom", description="Template type")

class TemplateResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str]
    author: Optional[str]
    version: str
    created_at: datetime
    updated_at: datetime
    tags: List[str]
    usage_count: int
    status: str

class ValidationResponse(BaseModel):
    score: int
    passed: bool
    issues: List[Dict[str, Any]]
    suggestions: List[str]

class AnalyticsResponse(BaseModel):
    metrics: Dict[str, Any]
    charts: Dict[str, Any]
    insights: List[Dict[str, Any]]

# Create router
router = APIRouter(prefix="/api/templates", tags=["templates"])

def get_template_manager() -> TemplateManager:
    """Get template manager instance"""
    container = DependencyContainer()
    return container.get_template_manager()

def get_template_validator() -> TemplateValidator:
    """Get template validator instance"""
    return TemplateValidator()

def get_template_analytics() -> TemplateAnalytics:
    """Get template analytics instance"""
    container = DependencyContainer()
    return container.get_template_analytics()

# Template CRUD endpoints
@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    type_filter: Optional[str] = Query(None, description="Filter by template type"),
    author_filter: Optional[str] = Query(None, description="Filter by author"),
    tag_filter: Optional[str] = Query(None, description="Filter by tag"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of templates"),
    offset: int = Query(0, ge=0, description="Number of templates to skip"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """List all templates with optional filtering"""
    try:
        templates = await template_manager.list_templates(
            type_filter=type_filter,
            author_filter=author_filter,
            tag_filter=tag_filter,
            search=search,
            limit=limit,
            offset=offset
        )
        
        return [
            TemplateResponse(
                id=template.id,
                name=template.name,
                type=template.type,
                description=template.description,
                author=template.author,
                version=template.version,
                created_at=template.created_at,
                updated_at=template.updated_at,
                tags=template.tags or [],
                usage_count=template.usage_count or 0,
                status=template.status
            )
            for template in templates
        ]
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreateRequest,
    template_manager: TemplateManager = Depends(get_template_manager),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Create a new template"""
    try:
        template = await template_manager.create_template(
            name=request.name,
            type=request.type,
            content=request.content,
            description=request.description,
            variables=request.variables,
            tags=request.tags,
            author=request.author,
            version=request.version
        )
        
        # Track analytics event
        await analytics.track_event(TemplateUsageEvent(
            template_id=template.id,
            template_name=template.name,
            user_id=request.author or "anonymous",
            event_type="create",
            timestamp=datetime.now(),
            success=True
        ))
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            type=template.type,
            description=template.description,
            author=template.author,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            tags=template.tags or [],
            usage_count=0,
            status=template.status
        )
        
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Get a specific template by ID"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Track view event
        await analytics.track_event(TemplateUsageEvent(
            template_id=template.id,
            template_name=template.name,
            user_id="anonymous",
            event_type="view",
            timestamp=datetime.now(),
            success=True
        ))
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            type=template.type,
            description=template.description,
            author=template.author,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            tags=template.tags or [],
            usage_count=template.usage_count or 0,
            status=template.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    request: TemplateUpdateRequest,
    template_manager: TemplateManager = Depends(get_template_manager),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Update an existing template"""
    try:
        template = await template_manager.update_template(
            template_id=template_id,
            name=request.name,
            description=request.description,
            content=request.content,
            variables=request.variables,
            tags=request.tags,
            version=request.version
        )
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Track edit event
        await analytics.track_event(TemplateUsageEvent(
            template_id=template.id,
            template_name=template.name,
            user_id="anonymous",
            event_type="edit",
            timestamp=datetime.now(),
            success=True
        ))
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            type=template.type,
            description=template.description,
            author=template.author,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            tags=template.tags or [],
            usage_count=template.usage_count or 0,
            status=template.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Delete a template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        success = await template_manager.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete template")
        
        # Track delete event
        await analytics.track_event(TemplateUsageEvent(
            template_id=template_id,
            template_name=template.name,
            user_id="anonymous",
            event_type="delete",
            timestamp=datetime.now(),
            success=True
        ))
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template generation endpoints
@router.post("/generate")
async def generate_template(
    request: TemplateGenerateRequest,
    template_manager: TemplateManager = Depends(get_template_manager),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Generate content from a template"""
    try:
        start_time = datetime.now()
        
        result = await template_manager.generate_from_template(
            template_id=request.template_id,
            parameters=request.parameters,
            output_format=request.output_format
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Track generation event
        template = await template_manager.get_template(request.template_id)
        await analytics.track_event(TemplateUsageEvent(
            template_id=request.template_id,
            template_name=template.name if template else "unknown",
            user_id="anonymous",
            event_type="generate",
            timestamp=datetime.now(),
            execution_time=execution_time,
            success=True,
            parameters=request.parameters,
            output_size=len(str(result)) if result else 0
        ))
        
        return {
            "template_id": request.template_id,
            "generated_content": result,
            "execution_time_ms": execution_time,
            "parameters_used": request.parameters
        }
        
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        
        # Track failed generation
        template = await template_manager.get_template(request.template_id)
        await analytics.track_event(TemplateUsageEvent(
            template_id=request.template_id,
            template_name=template.name if template else "unknown",
            user_id="anonymous",
            event_type="generate",
            timestamp=datetime.now(),
            success=False,
            error_message=str(e),
            parameters=request.parameters
        ))
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview")
async def preview_template(
    request: TemplateGenerateRequest,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Preview template generation without saving"""
    try:
        result = await template_manager.preview_template(
            template_id=request.template_id,
            parameters=request.parameters
        )
        
        return {
            "template_id": request.template_id,
            "preview_content": result,
            "parameters_used": request.parameters
        }
        
    except Exception as e:
        logger.error(f"Error previewing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template validation endpoints
@router.post("/validate", response_model=ValidationResponse)
async def validate_template(
    request: TemplateValidationRequest,
    validator: TemplateValidator = Depends(get_template_validator)
):
    """Validate template content"""
    try:
        result = validator.validate_template(
            template_content=request.content,
            template_type=request.template_type
        )
        
        return ValidationResponse(
            score=result.score,
            passed=result.passed,
            issues=[
                {
                    "level": issue.level.value,
                    "message": issue.message,
                    "line": issue.line,
                    "column": issue.column,
                    "rule": issue.rule,
                    "suggestion": issue.suggestion
                }
                for issue in result.issues
            ],
            suggestions=result.suggestions
        )
        
    except Exception as e:
        logger.error(f"Error validating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}/validate", response_model=ValidationResponse)
async def validate_existing_template(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager),
    validator: TemplateValidator = Depends(get_template_validator)
):
    """Validate an existing template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        result = validator.validate_template(
            template_content=template.content,
            template_type=template.type
        )
        
        return ValidationResponse(
            score=result.score,
            passed=result.passed,
            issues=[
                {
                    "level": issue.level.value,
                    "message": issue.message,
                    "line": issue.line,
                    "column": issue.column,
                    "rule": issue.rule,
                    "suggestion": issue.suggestion
                }
                for issue in result.issues
            ],
            suggestions=result.suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating existing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Template testing endpoints
@router.post("/test")
async def test_template(
    request: TemplateTestRequest,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Test a template with specific test case"""
    try:
        start_time = datetime.now()
        
        result = await template_manager.test_template(
            template_id=request.template_id,
            test_case=request.test_case
        )
        
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "template_id": request.template_id,
            "test_case": request.test_case,
            "result": result,
            "execution_time_ms": execution_time,
            "passed": result.get("success", False),
            "output": result.get("output", ""),
            "error": result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Error testing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}/test-cases")
async def get_template_test_cases(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Get all test cases for a template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        test_cases = await template_manager.get_template_test_cases(template_id)
        
        return {
            "template_id": template_id,
            "test_cases": test_cases
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting test cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{template_id}/test-cases")
async def add_template_test_case(
    template_id: str,
    test_case: Dict[str, Any],
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Add a test case to a template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        success = await template_manager.add_template_test_case(template_id, test_case)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to add test case")
        
        return {"message": "Test case added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template analytics endpoints
@router.get("/{template_id}/analytics", response_model=AnalyticsResponse)
async def get_template_analytics(
    template_id: str,
    period: int = Query(30, ge=1, le=365, description="Period in days"),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Get analytics for a specific template"""
    try:
        # Get metrics
        metrics = await analytics.get_template_metrics(template_id, period)
        
        # Get usage trends
        trends = await analytics.get_usage_trends(template_id, period)
        
        # Get insights
        insights = await analytics.get_performance_insights(template_id)
        
        return AnalyticsResponse(
            metrics={
                "usage_count": metrics.total_uses,
                "unique_users": metrics.unique_users,
                "success_rate": metrics.success_rate,
                "avg_time": metrics.avg_execution_time,
                "last_used": metrics.last_used.isoformat() if metrics.last_used != datetime.min else None,
                "popularity_score": metrics.popularity_score,
                "error_count": metrics.error_count
            },
            charts={
                "usage_trend": trends["usage_trend"],
                "user_activity": await analytics.get_user_activity(period)
            },
            insights=insights
        )
        
    except Exception as e:
        logger.error(f"Error getting template analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/global")
async def get_global_analytics(
    period: int = Query(30, ge=1, le=365, description="Period in days"),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Get global analytics across all templates"""
    try:
        global_analytics = await analytics.get_global_analytics(period)
        
        return {
            "period_days": period,
            "global_metrics": global_analytics.get("global_metrics", {}),
            "popular_templates": global_analytics.get("popular_templates", []),
            "active_users": global_analytics.get("active_users", []),
            "error_analysis": global_analytics.get("error_analysis", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting global analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template import/export endpoints
@router.post("/import")
async def import_template(
    file: UploadFile = File(...),
    author: Optional[str] = Query(None, description="Override author"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Import a template from file"""
    try:
        content = await file.read()
        
        # Handle different file types
        if file.filename.endswith('.json'):
            template_data = json.loads(content.decode('utf-8'))
        elif file.filename.endswith(('.yaml', '.yml')):
            import yaml
            template_data = yaml.safe_load(content.decode('utf-8'))
        elif file.filename.endswith('.zip'):
            # Handle zip files with multiple templates
            return await import_template_archive(content, author, template_manager)
        else:
            # Treat as plain text template
            template_data = {
                "name": file.filename.split('.')[0],
                "type": "custom",
                "content": content.decode('utf-8'),
                "description": f"Imported from {file.filename}"
            }
        
        # Override author if provided
        if author:
            template_data["author"] = author
        
        # Create template
        template = await template_manager.create_template(**template_data)
        
        return {
            "message": "Template imported successfully",
            "template_id": template.id,
            "template_name": template.name
        }
        
    except Exception as e:
        logger.error(f"Error importing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def import_template_archive(content: bytes, author: Optional[str], template_manager: TemplateManager):
    """Import templates from a zip archive"""
    imported_templates = []
    
    with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_file:
        for file_info in zip_file.filelist:
            if file_info.filename.endswith(('.json', '.yaml', '.yml')):
                file_content = zip_file.read(file_info.filename)
                
                if file_info.filename.endswith('.json'):
                    template_data = json.loads(file_content.decode('utf-8'))
                else:
                    import yaml
                    template_data = yaml.safe_load(file_content.decode('utf-8'))
                
                # Override author if provided
                if author:
                    template_data["author"] = author
                
                # Create template
                template = await template_manager.create_template(**template_data)
                imported_templates.append({
                    "template_id": template.id,
                    "template_name": template.name
                })
    
    return {
        "message": f"Imported {len(imported_templates)} templates successfully",
        "imported_templates": imported_templates
    }

@router.get("/{template_id}/export")
async def export_template(
    template_id: str,
    format: str = Query("json", description="Export format: json, yaml"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Export a template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Prepare export data
        export_data = {
            "name": template.name,
            "type": template.type,
            "description": template.description,
            "content": template.content,
            "variables": template.variables,
            "tags": template.tags,
            "author": template.author,
            "version": template.version,
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat()
        }
        
        # Format output
        if format.lower() == "yaml":
            import yaml
            content = yaml.dump(export_data, default_flow_style=False)
            media_type = "application/x-yaml"
            filename = f"{template.name}.yaml"
        else:
            content = json.dumps(export_data, indent=2)
            media_type = "application/json"
            filename = f"{template.name}.json"
        
        return StreamingResponse(
            io.StringIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/all")
async def export_all_templates(
    format: str = Query("zip", description="Export format: zip, json"),
    type_filter: Optional[str] = Query(None, description="Filter by template type"),
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Export all templates"""
    try:
        templates = await template_manager.list_templates(type_filter=type_filter)
        
        if format.lower() == "zip":
            # Create zip archive
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for template in templates:
                    export_data = {
                        "name": template.name,
                        "type": template.type,
                        "description": template.description,
                        "content": template.content,
                        "variables": template.variables,
                        "tags": template.tags,
                        "author": template.author,
                        "version": template.version,
                        "created_at": template.created_at.isoformat(),
                        "updated_at": template.updated_at.isoformat()
                    }
                    
                    filename = f"{template.name}.json"
                    zip_file.writestr(filename, json.dumps(export_data, indent=2))
            
            zip_buffer.seek(0)
            
            return StreamingResponse(
                io.BytesIO(zip_buffer.read()),
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=templates.zip"}
            )
        
        else:
            # Export as single JSON file
            export_data = []
            for template in templates:
                export_data.append({
                    "name": template.name,
                    "type": template.type,
                    "description": template.description,
                    "content": template.content,
                    "variables": template.variables,
                    "tags": template.tags,
                    "author": template.author,
                    "version": template.version,
                    "created_at": template.created_at.isoformat(),
                    "updated_at": template.updated_at.isoformat()
                })
            
            content = json.dumps(export_data, indent=2)
            
            return StreamingResponse(
                io.StringIO(content),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=templates.json"}
            )
        
    except Exception as e:
        logger.error(f"Error exporting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template sharing and collaboration endpoints
@router.post("/{template_id}/share")
async def share_template(
    template_id: str,
    share_data: Dict[str, Any],
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Share a template with other users"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        success = await template_manager.share_template(template_id, share_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to share template")
        
        return {"message": "Template shared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}/versions")
async def get_template_versions(
    template_id: str,
    template_manager: TemplateManager = Depends(get_template_manager)
):
    """Get all versions of a template"""
    try:
        template = await template_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        versions = await template_manager.get_template_versions(template_id)
        
        return {
            "template_id": template_id,
            "versions": versions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks for analytics cleanup
@router.post("/analytics/cleanup")
async def cleanup_analytics(
    background_tasks: BackgroundTasks,
    retention_days: int = Query(90, ge=30, le=365, description="Retention period in days"),
    analytics: TemplateAnalytics = Depends(get_template_analytics)
):
    """Cleanup old analytics data"""
    try:
        background_tasks.add_task(analytics.cleanup_old_data, retention_days)
        
        return {"message": f"Analytics cleanup scheduled for data older than {retention_days} days"}
        
    except Exception as e:
        logger.error(f"Error scheduling analytics cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for template management system"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "template-management"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")
"""
Configuration Management API endpoints.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import logging

from ..core.dependency_container import get_configuration_manager
from ..configuration.configuration_manager import ConfigurationManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/configuration", 
    tags=["configuration"],
    responses={
        404: {"description": "Configuration not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


# Request/Response Models
class ConfigurationUpdateRequest(BaseModel):
    """Request model for configuration updates."""
    configuration: Dict[str, Any] = Field(..., description="Configuration data")
    user: str = Field(..., description="User making the change")


class ConfigurationValidationRequest(BaseModel):
    """Request model for configuration validation."""
    service_id: str = Field(..., description="Service ID")
    schema_name: Optional[str] = Field(None, description="Schema name for validation")
    configuration: Dict[str, Any] = Field(..., description="Configuration to validate")


class ConfigurationResponse(BaseModel):
    """Response model for configuration data."""
    service_id: str
    configuration: Dict[str, Any]
    version: int
    last_updated: str
    updated_by: str


class ValidationResponse(BaseModel):
    """Response model for validation results."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class SchemaResponse(BaseModel):
    """Response model for schema information."""
    name: str
    description: str
    version: str
    schema: Dict[str, Any]
    required_fields: List[str]
    optional_fields: List[str]


class TemplateResponse(BaseModel):
    """Response model for template information."""
    name: str
    description: str
    template_data: Dict[str, Any]
    variables: List[str]
    category: str
    tags: List[str]


class HistoryEntryResponse(BaseModel):
    """Response model for configuration history entries."""
    version: int
    configuration: Dict[str, Any]
    timestamp: str
    user: str
    change_summary: Optional[str] = None


# Configuration CRUD Endpoints
@router.get("/services/{service_id}", response_model=Dict[str, Any])
async def get_service_configuration(
    service_id: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get configuration for a specific service."""
    try:
        config = await config_manager.get_service_config(service_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for service: {service_id}"
            )
        return config
    except Exception as e:
        logger.error(f"Error retrieving configuration for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service configuration"
        )


@router.put("/services/{service_id}")
async def update_service_configuration(
    service_id: str,
    request: ConfigurationUpdateRequest,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Update configuration for a specific service."""
    try:
        success = await config_manager.update_service_config(
            service_id=service_id,
            config=request.configuration,
            user=request.user
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update service configuration"
            )
        
        return {"message": "Configuration updated successfully", "service_id": service_id}
    except Exception as e:
        logger.error(f"Error updating configuration for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update service configuration"
        )


@router.delete("/services/{service_id}")
async def delete_service_configuration(
    service_id: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Delete configuration for a specific service."""
    try:
        success = await config_manager.delete_service_config(service_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for service: {service_id}"
            )
        
        return {"message": "Configuration deleted successfully", "service_id": service_id}
    except Exception as e:
        logger.error(f"Error deleting configuration for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete service configuration"
        )


# Configuration History Endpoints
@router.get("/services/{service_id}/history", response_model=List[HistoryEntryResponse])
async def get_configuration_history(
    service_id: str,
    limit: int = 50,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get configuration history for a specific service."""
    try:
        history = await config_manager.get_config_history(service_id, limit=limit)
        
        return [
            HistoryEntryResponse(
                version=entry.get("version", 0),
                configuration=entry.get("configuration", {}),
                timestamp=entry.get("timestamp", ""),
                user=entry.get("user", "unknown"),
                change_summary=entry.get("change_summary")
            )
            for entry in history
        ]
    except Exception as e:
        logger.error(f"Error retrieving configuration history for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration history"
        )


# Configuration Validation Endpoints
@router.post("/validate", response_model=ValidationResponse)
async def validate_configuration(
    request: ConfigurationValidationRequest,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Validate a configuration against a schema."""
    try:
        result = await config_manager.validate_config(
            service_id=request.service_id,
            config=request.configuration,
            schema_name=request.schema_name
        )
        
        return ValidationResponse(
            valid=result.valid,
            errors=result.errors,
            warnings=getattr(result, 'warnings', [])
        )
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        return ValidationResponse(
            valid=False,
            errors=[f"Validation service error: {str(e)}"]
        )


# Schema Management Endpoints
@router.get("/schemas", response_model=List[SchemaResponse])
async def list_schemas(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """List all available configuration schemas."""
    try:
        schemas = await config_manager.list_schemas()
        
        return [
            SchemaResponse(
                name=schema.name,
                description=schema.description,
                version=schema.version,
                schema=schema.schema,
                required_fields=schema.required_fields,
                optional_fields=schema.optional_fields
            )
            for schema in schemas
        ]
    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schemas"
        )


@router.get("/schemas/{schema_name}", response_model=SchemaResponse)
async def get_schema(
    schema_name: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get details for a specific schema."""
    try:
        schema = await config_manager.get_schema(schema_name)
        
        if schema is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schema not found: {schema_name}"
            )
        
        return SchemaResponse(
            name=schema.name,
            description=schema.description,
            version=schema.version,
            schema=schema.schema,
            required_fields=schema.required_fields,
            optional_fields=schema.optional_fields
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving schema {schema_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schema"
        )


# Template Management Endpoints
@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """List all available configuration templates."""
    try:
        templates = await config_manager.list_templates()
        
        # Filter by category if specified
        if category:
            templates = [t for t in templates if t.category == category]
        
        return [
            TemplateResponse(
                name=template.name,
                description=template.description,
                template_data=template.template_data,
                variables=template.variables,
                category=template.category,
                tags=template.tags
            )
            for template in templates
        ]
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )


@router.get("/templates/{template_name}", response_model=TemplateResponse)
async def get_template(
    template_name: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get details for a specific template."""
    try:
        template = await config_manager.get_template(template_name)
        
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template not found: {template_name}"
            )
        
        return TemplateResponse(
            name=template.name,
            description=template.description,
            template_data=template.template_data,
            variables=template.variables,
            category=template.category,
            tags=template.tags
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving template {template_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template"
        )


# Configuration Export/Import Endpoints
@router.get("/services/{service_id}/export")
async def export_configuration(
    service_id: str,
    format: str = "json",
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Export service configuration in specified format."""
    try:
        config = await config_manager.get_service_config(service_id)
        
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found for service: {service_id}"
            )
        
        if format.lower() == "yaml":
            # Convert to YAML format
            import yaml
            content = yaml.dump(config, default_flow_style=False)
            media_type = "application/x-yaml"
            filename = f"{service_id}_config.yaml"
        else:
            # Default to JSON
            import json
            content = json.dumps(config, indent=2)
            media_type = "application/json"
            filename = f"{service_id}_config.json"
        
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Error exporting configuration for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export configuration"
        )


@router.post("/services/{service_id}/import")
async def import_configuration(
    service_id: str,
    request: ConfigurationUpdateRequest,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Import configuration for a service."""
    try:
        # Validate the imported configuration
        validation_result = await config_manager.validate_config(
            service_id=service_id,
            config=request.configuration
        )
        
        if not validation_result.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid configuration",
                    "errors": validation_result.errors
                }
            )
        
        # Update the configuration
        success = await config_manager.update_service_config(
            service_id=service_id,
            config=request.configuration,
            user=request.user
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to import configuration"
            )
        
        return {
            "message": "Configuration imported successfully",
            "service_id": service_id,
            "validation": {
                "valid": validation_result.valid,
                "warnings": getattr(validation_result, 'warnings', [])
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing configuration for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import configuration"
        )


# Backup and Restore Endpoints
@router.post("/backup")
async def create_backup(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Create a backup of all configurations."""
    try:
        backup_id = await config_manager.create_backup()
        return {
            "message": "Backup created successfully",
            "backup_id": backup_id
        }
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create backup"
        )


@router.get("/backups")
async def list_backups(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """List all available backups."""
    try:
        backups = await config_manager.list_backups()
        return backups
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list backups"
        )


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Restore configurations from a backup."""
    try:
        success = await config_manager.restore_backup(backup_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup not found: {backup_id}"
            )
        
        return {
            "message": "Backup restored successfully",
            "backup_id": backup_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup {backup_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore backup"
        )


# Additional Configuration Management Endpoints

@router.get("/services", response_model=List[str])
async def list_configured_services(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """List all services that have configurations."""
    try:
        services = await config_manager.list_configured_services()
        return services
    except Exception as e:
        logger.error(f"Error listing configured services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list configured services"
        )


@router.get("/services/{service_id}/versions", response_model=List[str])
async def list_service_versions(
    service_id: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """List all available versions for a service configuration."""
    try:
        versions = await config_manager.list_service_versions(service_id)
        return versions
    except Exception as e:
        logger.error(f"Error listing versions for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list service versions"
        )


@router.get("/services/{service_id}/versions/{version}")
async def get_service_version(
    service_id: str,
    version: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get a specific version of service configuration."""
    try:
        config = await config_manager.get_service_version(service_id, version)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for service {service_id}"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving version {version} for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service version"
        )


@router.post("/services/{service_id}/versions/{version}/restore")
async def restore_service_version(
    service_id: str,
    version: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Restore a service to a specific configuration version."""
    try:
        success = await config_manager.restore_config_version(service_id, version)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found for service {service_id}"
            )
        
        return {
            "message": "Configuration restored successfully",
            "service_id": service_id,
            "version": version
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring version {version} for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore service version"
        )


@router.post("/services/{service_id}/versions/{version1}/compare/{version2}")
async def compare_service_versions(
    service_id: str,
    version1: str,
    version2: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Compare two versions of service configuration."""
    try:
        diff = await config_manager.compare_configs(service_id, version1, version2)
        return {
            "service_id": service_id,
            "version1": version1,
            "version2": version2,
            "differences": diff
        }
    except Exception as e:
        logger.error(f"Error comparing versions {version1} and {version2} for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare service versions"
        )


@router.post("/templates/{template_name}/apply/{service_id}")
async def apply_template_to_service(
    template_name: str,
    service_id: str,
    variables: Optional[Dict[str, Any]] = None,
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Apply a configuration template to a service."""
    try:
        success = await config_manager.apply_template(
            service_id=service_id,
            template_name=template_name,
            variables=variables or {}
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to apply template {template_name} to service {service_id}"
            )
        
        return {
            "message": "Template applied successfully",
            "service_id": service_id,
            "template_name": template_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template {template_name} to service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply template"
        )


@router.get("/stats")
async def get_configuration_stats(
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Get configuration management statistics."""
    try:
        stats = await config_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving configuration stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration statistics"
        )


@router.post("/bulk-validate")
async def bulk_validate_configurations(
    service_configs: Dict[str, Dict[str, Any]],
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Validate multiple service configurations in bulk."""
    try:
        results = {}
        
        for service_id, config in service_configs.items():
            validation_result = await config_manager.validate_config(
                service_id=service_id,
                config=config
            )
            results[service_id] = {
                "valid": validation_result.valid,
                "errors": validation_result.errors,
                "warnings": getattr(validation_result, 'warnings', [])
            }
        
        return {
            "results": results,
            "summary": {
                "total": len(service_configs),
                "valid": sum(1 for r in results.values() if r["valid"]),
                "invalid": sum(1 for r in results.values() if not r["valid"])
            }
        }
    except Exception as e:
        logger.error(f"Error in bulk validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk validation"
        )


@router.post("/bulk-update")
async def bulk_update_configurations(
    service_configs: Dict[str, Dict[str, Any]],
    user: str = "system",
    config_manager: ConfigurationManager = Depends(get_configuration_manager)
):
    """Update multiple service configurations in bulk."""
    try:
        results = await config_manager.bulk_update_configs(
            updates=service_configs,
            author=user
        )
        
        return {
            "results": results,
            "summary": {
                "total": len(service_configs),
                "successful": sum(1 for success in results.values() if success),
                "failed": sum(1 for success in results.values() if not success)
            }
        }
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk update"
        )
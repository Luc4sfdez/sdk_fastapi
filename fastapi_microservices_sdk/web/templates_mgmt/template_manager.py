"""
Advanced Template Manager.
Provides comprehensive template management with custom template support,
validation, sharing, import/export, and analytics.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import yaml
import zipfile
import tempfile
import shutil
import hashlib
import asyncio
from enum import Enum
import logging

from ..core.base_manager import BaseManager
from ...templates.manager import TemplateManager as BaseTemplateManager
from ...templates.registry import TemplateRegistry

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Template types."""
    SERVICE = "service"
    API = "api"
    MODEL = "model"
    DATABASE = "database"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    CUSTOM = "custom"


class TemplateStatus(Enum):
    """Template status."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class TemplateMetadata:
    """Template metadata."""
    id: str
    name: str
    description: str
    version: str
    author: str
    template_type: TemplateType
    status: TemplateStatus
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    rating: float = 0.0
    downloads: int = 0
    file_hash: str = ""
    file_size: int = 0


@dataclass
class CustomTemplate:
    """Custom template definition."""
    metadata: TemplateMetadata
    content: str
    files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    variables: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    test_cases: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TemplateUsage:
    """Template usage statistics."""
    template_id: str
    user_id: str
    timestamp: datetime
    parameters: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    execution_time: float = 0.0


class TemplateManager(BaseManager):
    """
    Advanced Template Manager.
    
    Features:
    - Custom template creation and validation
    - Template sharing and collaboration
    - Import/export capabilities
    - Version control and history
    - Usage analytics and statistics
    - Template marketplace integration
    - Advanced search and filtering
    - Template testing and validation
    """

    def __init__(self, name: str = "template_manager", config: Optional[Dict[str, Any]] = None):
        """Initialize the template manager."""
        super().__init__(name, config)
        
        # Configuration
        self._templates_directory = Path(config.get("templates_directory", "templates/custom")) if config else Path("templates/custom")
        self._max_template_size = config.get("max_template_size", 10 * 1024 * 1024) if config else 10 * 1024 * 1024  # 10MB
        self._enable_sharing = config.get("enable_sharing", True) if config else True
        self._enable_analytics = config.get("enable_analytics", True) if config else True
        
        # Base template manager integration
        self._base_manager: Optional[BaseTemplateManager] = None
        self._registry: Optional[TemplateRegistry] = None
        
        # Custom templates storage
        self._custom_templates: Dict[str, CustomTemplate] = {}
        self._template_metadata: Dict[str, TemplateMetadata] = {}
        
        # Usage tracking
        self._usage_history: List[TemplateUsage] = []
        self._usage_stats: Dict[str, Dict[str, Any]] = {}
        
        # Sharing and collaboration
        self._shared_templates: Dict[str, CustomTemplate] = {}
        self._template_ratings: Dict[str, List[float]] = {}
        
        # Cache
        self._template_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=30)

    async def _initialize_impl(self) -> None:
        """Initialize the template manager."""
        try:
            # Create templates directory
            self._templates_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize base template manager
            self._base_manager = BaseTemplateManager()
            self._registry = TemplateRegistry()
            
            # Load existing custom templates
            await self._load_custom_templates()
            
            # Load usage statistics
            await self._load_usage_statistics()
            
            self.logger.info("Advanced template manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize template manager: {e}")
            raise

    async def _shutdown_impl(self) -> None:
        """Shutdown the template manager."""
        try:
            # Save custom templates
            await self._save_custom_templates()
            
            # Save usage statistics
            await self._save_usage_statistics()
            
            self.logger.info("Template manager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during template manager shutdown: {e}")

    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            # Check if templates directory is accessible
            if not self._templates_directory.exists():
                return False
            
            # Check if base manager is available
            return self._base_manager is not None
            
        except Exception:
            return False

    # Custom Template Management

    async def create_custom_template(
        self,
        name: str,
        description: str,
        template_type: TemplateType,
        content: str,
        author: str,
        version: str = "1.0.0",
        tags: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a new custom template.
        
        Args:
            name: Template name
            description: Template description
            template_type: Type of template
            content: Main template content
            author: Template author
            version: Template version
            tags: Template tags
            parameters: Template parameters
            files: Additional template files
            
        Returns:
            Template ID
        """
        return await self._safe_execute(
            "create_custom_template",
            self._create_custom_template_impl,
            name,
            description,
            template_type,
            content,
            author,
            version,
            tags or [],
            parameters or {},
            files or {}
        )

    async def _create_custom_template_impl(
        self,
        name: str,
        description: str,
        template_type: TemplateType,
        content: str,
        author: str,
        version: str,
        tags: List[str],
        parameters: Dict[str, Any],
        files: Dict[str, str]
    ) -> str:
        """Implementation for creating custom template."""
        try:
            # Generate template ID
            template_id = self._generate_template_id(name, author)
            
            # Validate template content
            validation_result = await self._validate_template_content(content, template_type)
            if not validation_result["valid"]:
                raise ValueError(f"Template validation failed: {validation_result['errors']}")
            
            # Calculate file hash and size
            content_bytes = content.encode('utf-8')
            file_hash = hashlib.sha256(content_bytes).hexdigest()
            file_size = len(content_bytes)
            
            # Create metadata
            metadata = TemplateMetadata(
                id=template_id,
                name=name,
                description=description,
                version=version,
                author=author,
                template_type=template_type,
                status=TemplateStatus.DRAFT,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tags=tags,
                parameters=parameters,
                file_hash=file_hash,
                file_size=file_size
            )
            
            # Create custom template
            custom_template = CustomTemplate(
                metadata=metadata,
                content=content,
                files=files,
                variables=self._extract_variables(content),
                validation_rules=self._generate_validation_rules(template_type),
                test_cases=[]
            )
            
            # Store template
            self._custom_templates[template_id] = custom_template
            self._template_metadata[template_id] = metadata
            
            # Save to disk
            await self._save_template_to_disk(template_id, custom_template)
            
            self.logger.info(f"Created custom template: {template_id}")
            return template_id
            
        except Exception as e:
            self.logger.error(f"Failed to create custom template: {e}")
            raise

    async def update_custom_template(
        self,
        template_id: str,
        content: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Update an existing custom template.
        
        Args:
            template_id: Template ID
            content: Updated template content
            metadata_updates: Metadata updates
            files: Updated template files
            
        Returns:
            True if update successful
        """
        return await self._safe_execute(
            "update_custom_template",
            self._update_custom_template_impl,
            template_id,
            content,
            metadata_updates or {},
            files or {}
        )

    async def _update_custom_template_impl(
        self,
        template_id: str,
        content: Optional[str],
        metadata_updates: Dict[str, Any],
        files: Dict[str, str]
    ) -> bool:
        """Implementation for updating custom template."""
        try:
            if template_id not in self._custom_templates:
                raise ValueError(f"Template not found: {template_id}")
            
            template = self._custom_templates[template_id]
            metadata = template.metadata
            
            # Update content if provided
            if content is not None:
                # Validate new content
                validation_result = await self._validate_template_content(content, metadata.template_type)
                if not validation_result["valid"]:
                    raise ValueError(f"Template validation failed: {validation_result['errors']}")
                
                template.content = content
                template.variables = self._extract_variables(content)
                
                # Update hash and size
                content_bytes = content.encode('utf-8')
                metadata.file_hash = hashlib.sha256(content_bytes).hexdigest()
                metadata.file_size = len(content_bytes)
            
            # Update files if provided
            if files:
                template.files.update(files)
            
            # Update metadata
            for key, value in metadata_updates.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            
            metadata.updated_at = datetime.utcnow()
            
            # Increment version if content changed
            if content is not None:
                version_parts = metadata.version.split('.')
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                metadata.version = '.'.join(version_parts)
            
            # Save to disk
            await self._save_template_to_disk(template_id, template)
            
            self.logger.info(f"Updated custom template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update custom template: {e}")
            return False

    async def delete_custom_template(self, template_id: str) -> bool:
        """
        Delete a custom template.
        
        Args:
            template_id: Template ID
            
        Returns:
            True if deletion successful
        """
        return await self._safe_execute(
            "delete_custom_template",
            self._delete_custom_template_impl,
            template_id
        )

    async def _delete_custom_template_impl(self, template_id: str) -> bool:
        """Implementation for deleting custom template."""
        try:
            if template_id not in self._custom_templates:
                return False
            
            # Remove from memory
            del self._custom_templates[template_id]
            del self._template_metadata[template_id]
            
            # Remove from disk
            template_file = self._templates_directory / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            
            # Clean up related data
            self._usage_stats.pop(template_id, None)
            self._template_ratings.pop(template_id, None)
            
            self.logger.info(f"Deleted custom template: {template_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete custom template: {e}")
            return False

    # Template Retrieval and Search

    async def get_custom_template(self, template_id: str) -> Optional[CustomTemplate]:
        """
        Get a custom template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Custom template or None
        """
        return self._custom_templates.get(template_id)

    async def list_custom_templates(
        self,
        template_type: Optional[TemplateType] = None,
        status: Optional[TemplateStatus] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[TemplateMetadata]:
        """
        List custom templates with filtering.
        
        Args:
            template_type: Filter by template type
            status: Filter by status
            author: Filter by author
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of template metadata
        """
        return await self._safe_execute(
            "list_custom_templates",
            self._list_custom_templates_impl,
            template_type,
            status,
            author,
            tags,
            limit
        )

    async def _list_custom_templates_impl(
        self,
        template_type: Optional[TemplateType],
        status: Optional[TemplateStatus],
        author: Optional[str],
        tags: Optional[List[str]],
        limit: Optional[int]
    ) -> List[TemplateMetadata]:
        """Implementation for listing custom templates."""
        try:
            results = []
            
            for metadata in self._template_metadata.values():
                # Apply filters
                if template_type and metadata.template_type != template_type:
                    continue
                if status and metadata.status != status:
                    continue
                if author and metadata.author != author:
                    continue
                if tags and not any(tag in metadata.tags for tag in tags):
                    continue
                
                results.append(metadata)
            
            # Sort by usage count and rating
            results.sort(key=lambda x: (x.usage_count, x.rating), reverse=True)
            
            # Apply limit
            if limit:
                results = results[:limit]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to list custom templates: {e}")
            return []

    async def search_templates(
        self,
        query: str,
        include_builtin: bool = True,
        include_custom: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search templates by query.
        
        Args:
            query: Search query
            include_builtin: Include built-in templates
            include_custom: Include custom templates
            
        Returns:
            List of matching templates
        """
        return await self._safe_execute(
            "search_templates",
            self._search_templates_impl,
            query,
            include_builtin,
            include_custom
        )

    async def _search_templates_impl(
        self,
        query: str,
        include_builtin: bool,
        include_custom: bool
    ) -> List[Dict[str, Any]]:
        """Implementation for searching templates."""
        try:
            results = []
            query_lower = query.lower()
            
            # Search custom templates
            if include_custom:
                for template_id, metadata in self._template_metadata.items():
                    if (query_lower in metadata.name.lower() or
                        query_lower in metadata.description.lower() or
                        any(query_lower in tag.lower() for tag in metadata.tags)):
                        
                        results.append({
                            "id": template_id,
                            "name": metadata.name,
                            "description": metadata.description,
                            "type": metadata.template_type.value,
                            "author": metadata.author,
                            "version": metadata.version,
                            "tags": metadata.tags,
                            "usage_count": metadata.usage_count,
                            "rating": metadata.rating,
                            "is_custom": True
                        })
            
            # Search built-in templates
            if include_builtin and self._registry:
                builtin_templates = self._registry.list_templates()
                for template_name in builtin_templates:
                    if query_lower in template_name.lower():
                        template_info = self._registry.get_template_info(template_name)
                        results.append({
                            "id": template_name,
                            "name": template_name,
                            "description": template_info.get("description", ""),
                            "type": template_info.get("type", "unknown"),
                            "author": "System",
                            "version": template_info.get("version", "1.0.0"),
                            "tags": template_info.get("tags", []),
                            "usage_count": 0,
                            "rating": 0.0,
                            "is_custom": False
                        })
            
            # Sort by relevance (usage count and rating)
            results.sort(key=lambda x: (x["usage_count"], x["rating"]), reverse=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search templates: {e}")
            return []

    # Template Validation

    async def _validate_template_content(
        self,
        content: str,
        template_type: TemplateType
    ) -> Dict[str, Any]:
        """Validate template content."""
        try:
            errors = []
            warnings = []
            
            # Basic validation
            if not content.strip():
                errors.append("Template content cannot be empty")
            
            # Check for required placeholders based on type
            required_placeholders = self._get_required_placeholders(template_type)
            for placeholder in required_placeholders:
                if placeholder not in content:
                    warnings.append(f"Missing recommended placeholder: {placeholder}")
            
            # Validate syntax based on template type
            if template_type == TemplateType.DOCKER:
                if not content.strip().startswith("FROM"):
                    errors.append("Dockerfile must start with FROM instruction")
            
            elif template_type == TemplateType.KUBERNETES:
                try:
                    yaml.safe_load(content)
                except yaml.YAMLError as e:
                    errors.append(f"Invalid YAML syntax: {e}")
            
            # Check for security issues
            security_issues = self._check_security_issues(content)
            warnings.extend(security_issues)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Validation error: {e}"],
                "warnings": []
            }

    def _get_required_placeholders(self, template_type: TemplateType) -> List[str]:
        """Get required placeholders for template type."""
        placeholders = {
            TemplateType.SERVICE: ["{{service_name}}", "{{port}}"],
            TemplateType.API: ["{{api_name}}", "{{version}}"],
            TemplateType.MODEL: ["{{model_name}}", "{{fields}}"],
            TemplateType.DATABASE: ["{{db_name}}", "{{connection}}"],
            TemplateType.DOCKER: ["{{app_name}}", "{{port}}"],
            TemplateType.KUBERNETES: ["{{app_name}}", "{{namespace}}"],
            TemplateType.CUSTOM: []
        }
        return placeholders.get(template_type, [])

    def _check_security_issues(self, content: str) -> List[str]:
        """Check for potential security issues in template."""
        issues = []
        
        # Check for dangerous commands
        dangerous_patterns = [
            "rm -rf /",
            "chmod 777",
            "sudo",
            "eval(",
            "exec(",
            "system(",
            "shell_exec("
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content:
                issues.append(f"Potentially dangerous pattern found: {pattern}")
        
        return issues

    def _extract_variables(self, content: str) -> Dict[str, Any]:
        """Extract variables from template content."""
        import re
        
        # Find all {{variable}} patterns
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, content)
        
        variables = {}
        for match in matches:
            var_name = match.strip()
            variables[var_name] = {
                "type": "string",
                "required": True,
                "description": f"Variable: {var_name}"
            }
        
        return variables

    def _generate_validation_rules(self, template_type: TemplateType) -> Dict[str, Any]:
        """Generate validation rules for template type."""
        rules = {
            "max_size": self._max_template_size,
            "allowed_extensions": [".py", ".yaml", ".yml", ".json", ".txt", ".md"],
            "required_files": [],
            "forbidden_patterns": ["rm -rf", "chmod 777"]
        }
        
        # Type-specific rules
        if template_type == TemplateType.DOCKER:
            rules["required_files"] = ["Dockerfile"]
        elif template_type == TemplateType.KUBERNETES:
            rules["allowed_extensions"].extend([".yaml", ".yml"])
        
        return rules

    def _generate_template_id(self, name: str, author: str) -> str:
        """Generate unique template ID."""
        base_id = f"{author}_{name}_{datetime.utcnow().timestamp()}"
        return hashlib.md5(base_id.encode()).hexdigest()[:16]

    # Import/Export

    async def export_template(
        self,
        template_id: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> Optional[bytes]:
        """
        Export template to specified format.
        
        Args:
            template_id: Template ID
            format: Export format (json, yaml, zip)
            include_metadata: Include metadata in export
            
        Returns:
            Exported template data
        """
        return await self._safe_execute(
            "export_template",
            self._export_template_impl,
            template_id,
            format,
            include_metadata
        )

    async def _export_template_impl(
        self,
        template_id: str,
        format: str,
        include_metadata: bool
    ) -> Optional[bytes]:
        """Implementation for exporting template."""
        try:
            if template_id not in self._custom_templates:
                return None
            
            template = self._custom_templates[template_id]
            
            if format == "json":
                export_data = {
                    "content": template.content,
                    "files": template.files,
                    "variables": template.variables
                }
                
                if include_metadata:
                    export_data["metadata"] = {
                        "name": template.metadata.name,
                        "description": template.metadata.description,
                        "version": template.metadata.version,
                        "author": template.metadata.author,
                        "template_type": template.metadata.template_type.value,
                        "tags": template.metadata.tags,
                        "parameters": template.metadata.parameters
                    }
                
                return json.dumps(export_data, indent=2).encode('utf-8')
            
            elif format == "yaml":
                export_data = {
                    "content": template.content,
                    "files": template.files,
                    "variables": template.variables
                }
                
                if include_metadata:
                    export_data["metadata"] = {
                        "name": template.metadata.name,
                        "description": template.metadata.description,
                        "version": template.metadata.version,
                        "author": template.metadata.author,
                        "template_type": template.metadata.template_type.value,
                        "tags": template.metadata.tags,
                        "parameters": template.metadata.parameters
                    }
                
                return yaml.dump(export_data).encode('utf-8')
            
            elif format == "zip":
                # Create temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    
                    # Write main template file
                    (temp_path / "template.txt").write_text(template.content)
                    
                    # Write additional files
                    for filename, content in template.files.items():
                        (temp_path / filename).write_text(content)
                    
                    # Write metadata if requested
                    if include_metadata:
                        metadata_data = {
                            "name": template.metadata.name,
                            "description": template.metadata.description,
                            "version": template.metadata.version,
                            "author": template.metadata.author,
                            "template_type": template.metadata.template_type.value,
                            "tags": template.metadata.tags,
                            "parameters": template.metadata.parameters,
                            "variables": template.variables
                        }
                        (temp_path / "metadata.json").write_text(json.dumps(metadata_data, indent=2))
                    
                    # Create zip file
                    zip_path = temp_path / "template.zip"
                    with zipfile.ZipFile(zip_path, 'w') as zip_file:
                        for file_path in temp_path.rglob('*'):
                            if file_path.is_file() and file_path.name != "template.zip":
                                zip_file.write(file_path, file_path.relative_to(temp_path))
                    
                    return zip_path.read_bytes()
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to export template: {e}")
            return None

    async def import_template(
        self,
        data: bytes,
        format: str = "json",
        author: Optional[str] = None
    ) -> Optional[str]:
        """
        Import template from data.
        
        Args:
            data: Template data
            format: Import format (json, yaml, zip)
            author: Override author
            
        Returns:
            Template ID if successful
        """
        return await self._safe_execute(
            "import_template",
            self._import_template_impl,
            data,
            format,
            author
        )

    async def _import_template_impl(
        self,
        data: bytes,
        format: str,
        author: Optional[str]
    ) -> Optional[str]:
        """Implementation for importing template."""
        try:
            if format == "json":
                import_data = json.loads(data.decode('utf-8'))
            elif format == "yaml":
                import_data = yaml.safe_load(data.decode('utf-8'))
            elif format == "zip":
                # Extract zip file
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    zip_path = temp_path / "import.zip"
                    zip_path.write_bytes(data)
                    
                    with zipfile.ZipFile(zip_path, 'r') as zip_file:
                        zip_file.extractall(temp_path)
                    
                    # Read metadata
                    metadata_file = temp_path / "metadata.json"
                    if metadata_file.exists():
                        import_data = json.loads(metadata_file.read_text())
                        import_data["content"] = (temp_path / "template.txt").read_text()
                        
                        # Read additional files
                        files = {}
                        for file_path in temp_path.rglob('*'):
                            if file_path.is_file() and file_path.name not in ["metadata.json", "template.txt", "import.zip"]:
                                files[file_path.name] = file_path.read_text()
                        import_data["files"] = files
                    else:
                        return None
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Extract template data
            content = import_data.get("content", "")
            files = import_data.get("files", {})
            metadata = import_data.get("metadata", {})
            
            # Create template
            template_id = await self._create_custom_template_impl(
                name=metadata.get("name", "Imported Template"),
                description=metadata.get("description", "Imported template"),
                template_type=TemplateType(metadata.get("template_type", "custom")),
                content=content,
                author=author or metadata.get("author", "Unknown"),
                version=metadata.get("version", "1.0.0"),
                tags=metadata.get("tags", []),
                parameters=metadata.get("parameters", {}),
                files=files
            )
            
            return template_id
            
        except Exception as e:
            self.logger.error(f"Failed to import template: {e}")
            return None

    # Usage Analytics

    async def record_template_usage(
        self,
        template_id: str,
        user_id: str,
        parameters: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time: float = 0.0
    ) -> None:
        """Record template usage for analytics."""
        if not self._enable_analytics:
            return
        
        try:
            usage = TemplateUsage(
                template_id=template_id,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                parameters=parameters,
                success=success,
                error_message=error_message,
                execution_time=execution_time
            )
            
            self._usage_history.append(usage)
            
            # Update template metadata
            if template_id in self._template_metadata:
                self._template_metadata[template_id].usage_count += 1
            
            # Update usage statistics
            if template_id not in self._usage_stats:
                self._usage_stats[template_id] = {
                    "total_uses": 0,
                    "successful_uses": 0,
                    "failed_uses": 0,
                    "average_execution_time": 0.0,
                    "unique_users": set()
                }
            
            stats = self._usage_stats[template_id]
            stats["total_uses"] += 1
            stats["unique_users"].add(user_id)
            
            if success:
                stats["successful_uses"] += 1
            else:
                stats["failed_uses"] += 1
            
            # Update average execution time
            if execution_time > 0:
                current_avg = stats["average_execution_time"]
                total_uses = stats["total_uses"]
                stats["average_execution_time"] = (current_avg * (total_uses - 1) + execution_time) / total_uses
            
        except Exception as e:
            self.logger.error(f"Failed to record template usage: {e}")

    async def get_template_analytics(self, template_id: str) -> Dict[str, Any]:
        """Get analytics for a specific template."""
        return await self._safe_execute(
            "get_template_analytics",
            self._get_template_analytics_impl,
            template_id
        )

    async def _get_template_analytics_impl(self, template_id: str) -> Dict[str, Any]:
        """Implementation for getting template analytics."""
        try:
            if template_id not in self._usage_stats:
                return {
                    "template_id": template_id,
                    "total_uses": 0,
                    "successful_uses": 0,
                    "failed_uses": 0,
                    "success_rate": 0.0,
                    "average_execution_time": 0.0,
                    "unique_users": 0,
                    "recent_usage": []
                }
            
            stats = self._usage_stats[template_id]
            success_rate = stats["successful_uses"] / stats["total_uses"] if stats["total_uses"] > 0 else 0.0
            
            # Get recent usage
            recent_usage = [
                {
                    "timestamp": usage.timestamp.isoformat(),
                    "user_id": usage.user_id,
                    "success": usage.success,
                    "execution_time": usage.execution_time
                }
                for usage in self._usage_history
                if usage.template_id == template_id
            ][-10:]  # Last 10 uses
            
            return {
                "template_id": template_id,
                "total_uses": stats["total_uses"],
                "successful_uses": stats["successful_uses"],
                "failed_uses": stats["failed_uses"],
                "success_rate": success_rate,
                "average_execution_time": stats["average_execution_time"],
                "unique_users": len(stats["unique_users"]),
                "recent_usage": recent_usage
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get template analytics: {e}")
            return {}

    async def get_overall_analytics(self) -> Dict[str, Any]:
        """Get overall template analytics."""
        return await self._safe_execute(
            "get_overall_analytics",
            self._get_overall_analytics_impl
        )

    async def _get_overall_analytics_impl(self) -> Dict[str, Any]:
        """Implementation for getting overall analytics."""
        try:
            total_templates = len(self._custom_templates)
            total_uses = sum(stats["total_uses"] for stats in self._usage_stats.values())
            total_users = len(set(usage.user_id for usage in self._usage_history))
            
            # Most popular templates
            popular_templates = sorted(
                self._usage_stats.items(),
                key=lambda x: x[1]["total_uses"],
                reverse=True
            )[:10]
            
            # Usage by template type
            usage_by_type = {}
            for template_id, stats in self._usage_stats.items():
                if template_id in self._template_metadata:
                    template_type = self._template_metadata[template_id].template_type.value
                    usage_by_type[template_type] = usage_by_type.get(template_type, 0) + stats["total_uses"]
            
            # Recent activity
            recent_activity = sorted(
                self._usage_history,
                key=lambda x: x.timestamp,
                reverse=True
            )[:20]
            
            return {
                "total_templates": total_templates,
                "total_uses": total_uses,
                "total_users": total_users,
                "popular_templates": [
                    {
                        "template_id": tid,
                        "name": self._template_metadata.get(tid, {}).name if tid in self._template_metadata else "Unknown",
                        "uses": stats["total_uses"]
                    }
                    for tid, stats in popular_templates
                ],
                "usage_by_type": usage_by_type,
                "recent_activity": [
                    {
                        "template_id": usage.template_id,
                        "user_id": usage.user_id,
                        "timestamp": usage.timestamp.isoformat(),
                        "success": usage.success
                    }
                    for usage in recent_activity
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get overall analytics: {e}")
            return {}

    # Persistence

    async def _load_custom_templates(self) -> None:
        """Load custom templates from disk."""
        try:
            for template_file in self._templates_directory.glob("*.json"):
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                    
                    # Reconstruct template
                    metadata_data = template_data["metadata"]
                    metadata = TemplateMetadata(
                        id=metadata_data["id"],
                        name=metadata_data["name"],
                        description=metadata_data["description"],
                        version=metadata_data["version"],
                        author=metadata_data["author"],
                        template_type=TemplateType(metadata_data["template_type"]),
                        status=TemplateStatus(metadata_data["status"]),
                        created_at=datetime.fromisoformat(metadata_data["created_at"]),
                        updated_at=datetime.fromisoformat(metadata_data["updated_at"]),
                        tags=metadata_data.get("tags", []),
                        dependencies=metadata_data.get("dependencies", []),
                        parameters=metadata_data.get("parameters", {}),
                        usage_count=metadata_data.get("usage_count", 0),
                        rating=metadata_data.get("rating", 0.0),
                        downloads=metadata_data.get("downloads", 0),
                        file_hash=metadata_data.get("file_hash", ""),
                        file_size=metadata_data.get("file_size", 0)
                    )
                    
                    template = CustomTemplate(
                        metadata=metadata,
                        content=template_data["content"],
                        files=template_data.get("files", {}),
                        variables=template_data.get("variables", {}),
                        validation_rules=template_data.get("validation_rules", {}),
                        test_cases=template_data.get("test_cases", [])
                    )
                    
                    self._custom_templates[metadata.id] = template
                    self._template_metadata[metadata.id] = metadata
                    
                except Exception as e:
                    self.logger.error(f"Failed to load template from {template_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load custom templates: {e}")

    async def _save_custom_templates(self) -> None:
        """Save custom templates to disk."""
        try:
            for template_id, template in self._custom_templates.items():
                await self._save_template_to_disk(template_id, template)
        except Exception as e:
            self.logger.error(f"Failed to save custom templates: {e}")

    async def _save_template_to_disk(self, template_id: str, template: CustomTemplate) -> None:
        """Save a single template to disk."""
        try:
            template_file = self._templates_directory / f"{template_id}.json"
            
            template_data = {
                "metadata": {
                    "id": template.metadata.id,
                    "name": template.metadata.name,
                    "description": template.metadata.description,
                    "version": template.metadata.version,
                    "author": template.metadata.author,
                    "template_type": template.metadata.template_type.value,
                    "status": template.metadata.status.value,
                    "created_at": template.metadata.created_at.isoformat(),
                    "updated_at": template.metadata.updated_at.isoformat(),
                    "tags": template.metadata.tags,
                    "dependencies": template.metadata.dependencies,
                    "parameters": template.metadata.parameters,
                    "usage_count": template.metadata.usage_count,
                    "rating": template.metadata.rating,
                    "downloads": template.metadata.downloads,
                    "file_hash": template.metadata.file_hash,
                    "file_size": template.metadata.file_size
                },
                "content": template.content,
                "files": template.files,
                "variables": template.variables,
                "validation_rules": template.validation_rules,
                "test_cases": template.test_cases
            }
            
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save template to disk: {e}")

    async def _load_usage_statistics(self) -> None:
        """Load usage statistics from disk."""
        try:
            stats_file = self._templates_directory / "usage_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    stats_data = json.load(f)
                
                # Convert sets back from lists
                for template_id, stats in stats_data.items():
                    if "unique_users" in stats:
                        stats["unique_users"] = set(stats["unique_users"])
                
                self._usage_stats = stats_data
                
        except Exception as e:
            self.logger.error(f"Failed to load usage statistics: {e}")

    async def _save_usage_statistics(self) -> None:
        """Save usage statistics to disk."""
        try:
            stats_file = self._templates_directory / "usage_stats.json"
            
            # Convert sets to lists for JSON serialization
            stats_data = {}
            for template_id, stats in self._usage_stats.items():
                stats_copy = stats.copy()
                if "unique_users" in stats_copy:
                    stats_copy["unique_users"] = list(stats_copy["unique_users"])
                stats_data[template_id] = stats_copy
            
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save usage statistics: {e}")
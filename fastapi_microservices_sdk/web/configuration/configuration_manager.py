"""
Configuration management for the web dashboard.
"""

from typing import List, Optional, Dict, Any, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json
import hashlib
import asyncio
import tempfile
import shutil

from ..core.base_manager import BaseManager

# Optional dependencies
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


class ConfigurationFormat(Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"


class ConfigurationStatus(Enum):
    """Configuration status."""
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"


class ValidationType(Enum):
    """Configuration validation types."""
    SCHEMA = "schema"
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    DEPENDENCY = "dependency"


@dataclass
class ValidationResult:
    """Configuration validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validation_type: ValidationType = ValidationType.SCHEMA
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigurationVersion:
    """Configuration version information."""
    version: str
    timestamp: datetime
    author: str
    description: str
    config_data: Dict[str, Any]
    checksum: str = ""
    status: ConfigurationStatus = ConfigurationStatus.VALID
    validation_result: Optional[ValidationResult] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate configuration checksum."""
        config_str = json.dumps(self.config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


@dataclass
class ConfigurationSchema:
    """Configuration schema definition."""
    name: str
    schema: Dict[str, Any]
    description: str
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    version: str = "1.0"
    format: ConfigurationFormat = ConfigurationFormat.JSON
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfigurationTemplate:
    """Configuration template."""
    name: str
    description: str
    template_data: Dict[str, Any]
    schema_name: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConfigurationBackup:
    """Configuration backup information."""
    backup_id: str
    service_id: str
    timestamp: datetime
    backup_path: str
    description: str
    size_bytes: int = 0
    compressed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigurationManager(BaseManager):
    """
    Advanced configuration management for the web dashboard.
    
    Features:
    - Service configuration management with validation
    - Configuration schema validation and type checking
    - Configuration versioning and history tracking
    - Configuration backup and restore functionality
    - Template management and variable substitution
    - Real-time configuration monitoring
    - Configuration diff and comparison
    - Bulk configuration operations
    """
    
    def __init__(self, name: str = "configuration", config: Optional[Dict[str, Any]] = None):
        """Initialize the configuration manager."""
        super().__init__(name, config)
        
        # Core storage
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, List[ConfigurationVersion]] = {}
        self._schemas: Dict[str, ConfigurationSchema] = {}
        self._templates: Dict[str, ConfigurationTemplate] = {}
        self._backups: Dict[str, List[ConfigurationBackup]] = {}
        
        # Configuration settings
        self._backup_enabled = self.get_config("backup_enabled", True)
        self._max_versions = self.get_config("max_versions", 50)
        self._backup_directory = Path(self.get_config("backup_directory", "./config_backups"))
        self._auto_backup = self.get_config("auto_backup", True)
        self._validation_enabled = self.get_config("validation_enabled", True)
        
        # Validation settings
        self._strict_validation = self.get_config("strict_validation", False)
        self._allow_unknown_fields = self.get_config("allow_unknown_fields", True)
        self._validate_on_update = self.get_config("validate_on_update", True)
        
        # Change tracking
        self._change_callbacks: List[Callable] = []
        self._validation_callbacks: List[Callable] = []
        
        # Create backup directory
        if self._backup_enabled:
            self._backup_directory.mkdir(parents=True, exist_ok=True)
    
    async def _initialize_impl(self) -> None:
        """Initialize the configuration manager."""
        try:
            # Load built-in schemas
            await self._load_builtin_schemas()
            
            # Load configuration templates
            await self._load_builtin_templates()
            
            # Initialize backup system
            if self._backup_enabled:
                await self._initialize_backup_system()
            
            # Load existing configurations
            await self._load_existing_configurations()
            
            self.logger.info("Configuration manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration manager: {e}")
            raise
    
    async def get_service_config(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Get service configuration.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Configuration dictionary or None if not found
        """
        return await self._safe_execute(
            "get_service_config",
            self._get_service_config_impl,
            service_id
        )
    
    async def update_service_config(self, service_id: str, config: Dict[str, Any], author: str = "system") -> bool:
        """
        Update service configuration.
        
        Args:
            service_id: Service identifier
            config: New configuration
            author: Author of the change
            
        Returns:
            True if update successful
        """
        result = await self._safe_execute(
            "update_service_config",
            self._update_service_config_impl,
            service_id,
            config,
            author
        )
        return result is not None and result
    
    async def validate_config(
        self, 
        service_id: str, 
        config: Dict[str, Any],
        schema_name: Optional[str] = None,
        validation_type: ValidationType = ValidationType.SCHEMA
    ) -> ValidationResult:
        """
        Validate configuration against schema with comprehensive validation.
        
        Args:
            service_id: Service identifier
            config: Configuration to validate
            schema_name: Specific schema to use (optional)
            validation_type: Type of validation to perform
            
        Returns:
            Detailed validation result
        """
        return await self._safe_execute(
            "validate_config",
            self._validate_config_impl,
            service_id,
            config,
            schema_name,
            validation_type
        ) or ValidationResult(valid=False, errors=["Validation failed"])
    
    async def get_config_history(self, service_id: str) -> List[ConfigurationVersion]:
        """
        Get configuration history.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of configuration versions
        """
        return await self._safe_execute(
            "get_config_history",
            self._get_config_history_impl,
            service_id
        ) or []
    
    async def restore_config_version(self, service_id: str, version: str) -> bool:
        """
        Restore configuration to a specific version.
        
        Args:
            service_id: Service identifier
            version: Version to restore
            
        Returns:
            True if restore successful
        """
        result = await self._safe_execute(
            "restore_config_version",
            self._restore_config_version_impl,
            service_id,
            version
        )
        return result is not None and result
    
    # Schema Management Methods
    
    async def register_schema(self, schema: ConfigurationSchema) -> bool:
        """
        Register a new configuration schema.
        
        Args:
            schema: Configuration schema to register
            
        Returns:
            True if registration successful
        """
        return await self._safe_execute(
            "register_schema",
            self._register_schema_impl,
            schema
        ) or False
    
    async def get_schema(self, schema_name: str) -> Optional[ConfigurationSchema]:
        """
        Get configuration schema by name.
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Configuration schema or None if not found
        """
        return await self._safe_execute(
            "get_schema",
            self._get_schema_impl,
            schema_name
        )
    
    async def list_schemas(self) -> List[ConfigurationSchema]:
        """
        List all available configuration schemas.
        
        Returns:
            List of configuration schemas
        """
        return await self._safe_execute(
            "list_schemas",
            self._list_schemas_impl
        ) or []
    
    # Template Management Methods
    
    async def create_template(self, template: ConfigurationTemplate) -> bool:
        """
        Create a new configuration template.
        
        Args:
            template: Configuration template to create
            
        Returns:
            True if creation successful
        """
        return await self._safe_execute(
            "create_template",
            self._create_template_impl,
            template
        ) or False
    
    async def get_template(self, template_name: str) -> Optional[ConfigurationTemplate]:
        """
        Get configuration template by name.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Configuration template or None if not found
        """
        return await self._safe_execute(
            "get_template",
            self._get_template_impl,
            template_name
        )
    
    async def list_templates(self, category: Optional[str] = None) -> List[ConfigurationTemplate]:
        """
        List configuration templates.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of configuration templates
        """
        return await self._safe_execute(
            "list_templates",
            self._list_templates_impl,
            category
        ) or []
    
    async def apply_template(
        self, 
        service_id: str, 
        template_name: str, 
        variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apply a configuration template to a service.
        
        Args:
            service_id: Service identifier
            template_name: Name of the template to apply
            variables: Template variables (optional)
            
        Returns:
            True if application successful
        """
        return await self._safe_execute(
            "apply_template",
            self._apply_template_impl,
            service_id,
            template_name,
            variables or {}
        ) or False
    
    # Backup and Restore Methods
    
    async def create_backup(self, service_id: str, description: str = "") -> Optional[str]:
        """
        Create a backup of service configuration.
        
        Args:
            service_id: Service identifier
            description: Backup description
            
        Returns:
            Backup ID if successful, None otherwise
        """
        return await self._safe_execute(
            "create_backup",
            self._create_backup_impl,
            service_id,
            description
        )
    
    async def restore_backup(self, service_id: str, backup_id: str) -> bool:
        """
        Restore configuration from backup.
        
        Args:
            service_id: Service identifier
            backup_id: Backup identifier
            
        Returns:
            True if restore successful
        """
        return await self._safe_execute(
            "restore_backup",
            self._restore_backup_impl,
            service_id,
            backup_id
        ) or False
    
    async def list_backups(self, service_id: str) -> List[ConfigurationBackup]:
        """
        List backups for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of configuration backups
        """
        return await self._safe_execute(
            "list_backups",
            self._list_backups_impl,
            service_id
        ) or []
    
    # Advanced Configuration Methods
    
    async def compare_configs(
        self, 
        service_id: str, 
        version1: str, 
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two configuration versions.
        
        Args:
            service_id: Service identifier
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Configuration diff
        """
        return await self._safe_execute(
            "compare_configs",
            self._compare_configs_impl,
            service_id,
            version1,
            version2
        ) or {}
    
    async def bulk_update_configs(
        self, 
        updates: Dict[str, Dict[str, Any]], 
        author: str = "system"
    ) -> Dict[str, bool]:
        """
        Update multiple service configurations in bulk.
        
        Args:
            updates: Dictionary of service_id -> config updates
            author: Author of the changes
            
        Returns:
            Dictionary of service_id -> success status
        """
        return await self._safe_execute(
            "bulk_update_configs",
            self._bulk_update_configs_impl,
            updates,
            author
        ) or {}
    
    async def export_config(
        self, 
        service_id: str, 
        format: ConfigurationFormat = ConfigurationFormat.JSON
    ) -> Optional[str]:
        """
        Export service configuration in specified format.
        
        Args:
            service_id: Service identifier
            format: Export format
            
        Returns:
            Exported configuration string or None if failed
        """
        return await self._safe_execute(
            "export_config",
            self._export_config_impl,
            service_id,
            format
        )
    
    async def import_config(
        self, 
        service_id: str, 
        config_data: str, 
        format: ConfigurationFormat = ConfigurationFormat.JSON,
        author: str = "system"
    ) -> bool:
        """
        Import service configuration from string.
        
        Args:
            service_id: Service identifier
            config_data: Configuration data string
            format: Import format
            author: Author of the import
            
        Returns:
            True if import successful
        """
        return await self._safe_execute(
            "import_config",
            self._import_config_impl,
            service_id,
            config_data,
            format,
            author
        ) or False
    
    # Callback Management
    
    async def add_change_callback(self, callback: Callable) -> None:
        """Add configuration change callback."""
        self._change_callbacks.append(callback)
    
    async def add_validation_callback(self, callback: Callable) -> None:
        """Add validation callback."""
        self._validation_callbacks.append(callback)
    
    # Implementation methods
    
    async def _get_service_config_impl(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Implementation for getting service configuration."""
        return self._configurations.get(service_id)
    
    async def _update_service_config_impl(self, service_id: str, config: Dict[str, Any], author: str) -> bool:
        """Implementation for updating service configuration."""
        # TODO: Implement actual configuration update with validation
        # Store current version in history
        if service_id in self._configurations:
            current_config = self._configurations[service_id]
            version = ConfigurationVersion(
                version=f"v{len(self._versions.get(service_id, [])) + 1}",
                timestamp=datetime.utcnow(),
                author=author,
                description="Configuration update",
                config_data=current_config.copy()
            )
            if service_id not in self._versions:
                self._versions[service_id] = []
            self._versions[service_id].append(version)
        
        # Update configuration
        self._configurations[service_id] = config
        return True
    
    async def _validate_config_impl(self, service_id: str, config: Dict[str, Any]) -> List[str]:
        """Implementation for validating configuration."""
        # TODO: Implement actual schema validation
        errors = []
        
        # Basic validation example
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
        
        return errors
    
    async def _get_config_history_impl(self, service_id: str) -> List[ConfigurationVersion]:
        """Implementation for getting configuration history."""
        return self._versions.get(service_id, [])
    
    async def _restore_config_version_impl(self, service_id: str, version: str) -> bool:
        """Implementation for restoring configuration version."""
        # TODO: Implement actual version restoration
        versions = self._versions.get(service_id, [])
        for v in versions:
            if v.version == version:
                self._configurations[service_id] = v.config_data.copy()
                return True
        return False
    
    # Enhanced Implementation Methods
    
    async def _load_builtin_schemas(self) -> None:
        """Load built-in configuration schemas."""
        try:
            # Basic service schema
            service_schema = ConfigurationSchema(
                name="service",
                description="Basic service configuration schema",
                schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "environment": {"type": "string", "enum": ["development", "staging", "production"]},
                        "replicas": {"type": "integer", "minimum": 1, "maximum": 100},
                        "resources": {
                            "type": "object",
                            "properties": {
                                "cpu": {"type": "string"},
                                "memory": {"type": "string"}
                            }
                        },
                        "environment_variables": {"type": "object"},
                        "health_check": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "interval": {"type": "integer"},
                                "timeout": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["name", "port"]
                },
                required_fields=["name", "port"],
                optional_fields=["environment", "replicas", "resources", "environment_variables", "health_check"]
            )
            self._schemas["service"] = service_schema
            
            # Database schema
            database_schema = ConfigurationSchema(
                name="database",
                description="Database configuration schema",
                schema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["postgresql", "mysql", "mongodb", "redis"]},
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "database": {"type": "string"},
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "ssl": {"type": "boolean"},
                        "pool_size": {"type": "integer", "minimum": 1, "maximum": 100}
                    },
                    "required": ["type", "host", "port", "database"]
                },
                required_fields=["type", "host", "port", "database"],
                optional_fields=["username", "password", "ssl", "pool_size"]
            )
            self._schemas["database"] = database_schema
            
            self.logger.info("Built-in schemas loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load built-in schemas: {e}")
    
    async def _load_builtin_templates(self) -> None:
        """Load built-in configuration templates."""
        try:
            # Basic web service template
            web_service_template = ConfigurationTemplate(
                name="web-service",
                description="Basic web service configuration template",
                template_data={
                    "name": "${service_name}",
                    "port": "${port:8080}",
                    "environment": "${environment:development}",
                    "replicas": "${replicas:1}",
                    "resources": {
                        "cpu": "${cpu:100m}",
                        "memory": "${memory:128Mi}"
                    },
                    "environment_variables": {
                        "NODE_ENV": "${environment}",
                        "PORT": "${port}"
                    },
                    "health_check": {
                        "path": "/health",
                        "interval": 30,
                        "timeout": 5
                    }
                },
                variables=["service_name", "port", "environment", "replicas", "cpu", "memory"],
                category="web",
                tags=["service", "web", "basic"]
            )
            self._templates["web-service"] = web_service_template
            
            # Database service template
            database_template = ConfigurationTemplate(
                name="database-service",
                description="Database service configuration template",
                template_data={
                    "type": "${db_type:postgresql}",
                    "host": "${db_host:localhost}",
                    "port": "${db_port:5432}",
                    "database": "${db_name}",
                    "username": "${db_user}",
                    "password": "${db_password}",
                    "ssl": "${ssl_enabled:false}",
                    "pool_size": "${pool_size:10}"
                },
                variables=["db_type", "db_host", "db_port", "db_name", "db_user", "db_password", "ssl_enabled", "pool_size"],
                category="database",
                tags=["database", "service"]
            )
            self._templates["database-service"] = database_template
            
            self.logger.info("Built-in templates loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load built-in templates: {e}")
    
    async def _initialize_backup_system(self) -> None:
        """Initialize the backup system."""
        try:
            if not self._backup_directory.exists():
                self._backup_directory.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Backup system initialized at {self._backup_directory}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize backup system: {e}")
    
    async def _load_existing_configurations(self) -> None:
        """Load existing configurations from storage."""
        try:
            # In a real implementation, this would load from persistent storage
            # For now, we'll just log that it's ready
            self.logger.info("Configuration storage ready")
            
        except Exception as e:
            self.logger.error(f"Failed to load existing configurations: {e}")
    
    async def _get_schema_for_service(self, service_id: str, schema_name: Optional[str] = None) -> Optional[ConfigurationSchema]:
        """Get schema for a service."""
        if schema_name:
            return self._schemas.get(schema_name)
        
        # Try to infer schema from service type or use default
        return self._schemas.get("service")
    
    async def _validate_syntax(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration syntax."""
        errors = []
        
        try:
            # Check for common syntax issues
            if not config:
                errors.append("Configuration cannot be empty")
            
            # Check for reserved keys
            reserved_keys = ["__internal__", "__system__"]
            for key in config.keys():
                if key in reserved_keys:
                    errors.append(f"Reserved key '{key}' cannot be used")
            
            # Validate nested structures
            for key, value in config.items():
                if isinstance(value, dict):
                    nested_errors = await self._validate_syntax(value)
                    errors.extend([f"{key}.{error}" for error in nested_errors])
        
        except Exception as e:
            errors.append(f"Syntax validation error: {str(e)}")
        
        return errors
    
    async def _validate_dependencies(self, service_id: str, config: Dict[str, Any]) -> List[str]:
        """Validate configuration dependencies."""
        errors = []
        
        try:
            # Check for required dependencies
            if "database" in config:
                db_config = config["database"]
                if isinstance(db_config, dict):
                    if "type" in db_config and "host" not in db_config:
                        errors.append("Database configuration requires 'host' when 'type' is specified")
        
        except Exception as e:
            errors.append(f"Dependency validation error: {str(e)}")
        
        return errors
    
    async def _apply_custom_validation_rules(self, service_id: str, config: Dict[str, Any]) -> List[str]:
        """Apply custom validation rules."""
        errors = []
        
        try:
            # Example custom rules
            if "port" in config:
                port = config["port"]
                if isinstance(port, int) and (port < 1024 and port != 80 and port != 443):
                    errors.append("Ports below 1024 (except 80, 443) require special privileges")
        
        except Exception as e:
            errors.append(f"Custom validation error: {str(e)}")
        
        return errors
    
    async def _notify_change_callbacks(self, service_id: str, config: Dict[str, Any], author: str) -> None:
        """Notify configuration change callbacks."""
        for callback in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(service_id, config, author)
                else:
                    callback(service_id, config, author)
            except Exception as e:
                self.logger.error(f"Change callback failed: {e}")
    
    async def _notify_validation_callbacks(self, service_id: str, config: Dict[str, Any], result: ValidationResult) -> None:
        """Notify validation callbacks."""
        for callback in self._validation_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(service_id, config, result)
                else:
                    callback(service_id, config, result)
            except Exception as e:
                self.logger.error(f"Validation callback failed: {e}")
    
    # Schema Management Implementation
    
    async def _register_schema_impl(self, schema: ConfigurationSchema) -> bool:
        """Implementation for registering a schema."""
        try:
            schema.updated_at = datetime.utcnow()
            self._schemas[schema.name] = schema
            self.logger.info(f"Schema '{schema.name}' registered successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to register schema '{schema.name}': {e}")
            return False
    
    async def _get_schema_impl(self, schema_name: str) -> Optional[ConfigurationSchema]:
        """Implementation for getting a schema."""
        return self._schemas.get(schema_name)
    
    async def _list_schemas_impl(self) -> List[ConfigurationSchema]:
        """Implementation for listing schemas."""
        return list(self._schemas.values())
    
    # Template Management Implementation
    
    async def _create_template_impl(self, template: ConfigurationTemplate) -> bool:
        """Implementation for creating a template."""
        try:
            self._templates[template.name] = template
            self.logger.info(f"Template '{template.name}' created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create template '{template.name}': {e}")
            return False
    
    async def _get_template_impl(self, template_name: str) -> Optional[ConfigurationTemplate]:
        """Implementation for getting a template."""
        return self._templates.get(template_name)
    
    async def _list_templates_impl(self, category: Optional[str] = None) -> List[ConfigurationTemplate]:
        """Implementation for listing templates."""
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates
    
    async def _apply_template_impl(self, service_id: str, template_name: str, variables: Dict[str, Any]) -> bool:
        """Implementation for applying a template."""
        try:
            template = self._templates.get(template_name)
            if not template:
                self.logger.error(f"Template '{template_name}' not found")
                return False
            
            # Apply variable substitution
            config = await self._substitute_template_variables(template.template_data, variables)
            
            # Update service configuration
            return await self._update_service_config_impl(service_id, config, "template-system")
            
        except Exception as e:
            self.logger.error(f"Failed to apply template '{template_name}' to service '{service_id}': {e}")
            return False
    
    async def _substitute_template_variables(self, template_data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in template data."""
        import re
        
        def substitute_value(value):
            if isinstance(value, str):
                # Handle ${variable:default} syntax
                pattern = r'\$\{([^:}]+)(?::([^}]*))?\}'
                
                def replace_var(match):
                    var_name = match.group(1)
                    default_value = match.group(2) if match.group(2) is not None else ""
                    return str(variables.get(var_name, default_value))
                
                return re.sub(pattern, replace_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(template_data)
    
    # Backup Implementation
    
    async def _create_backup_impl(self, service_id: str, description: str) -> Optional[str]:
        """Implementation for creating a backup."""
        try:
            config = self._configurations.get(service_id)
            if not config:
                self.logger.warning(f"No configuration found for service '{service_id}' to backup")
                return None
            
            backup_id = f"{service_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            backup_path = self._backup_directory / f"{backup_id}.json"
            
            # Write backup file
            with open(backup_path, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            # Create backup info
            backup_info = ConfigurationBackup(
                backup_id=backup_id,
                service_id=service_id,
                timestamp=datetime.utcnow(),
                backup_path=str(backup_path),
                description=description,
                size_bytes=backup_path.stat().st_size
            )
            
            if service_id not in self._backups:
                self._backups[service_id] = []
            self._backups[service_id].append(backup_info)
            
            self.logger.info(f"Backup created for service '{service_id}': {backup_id}")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup for service '{service_id}': {e}")
            return None
    
    async def _restore_backup_impl(self, service_id: str, backup_id: str) -> bool:
        """Implementation for restoring from backup."""
        try:
            backups = self._backups.get(service_id, [])
            backup_info = None
            
            for backup in backups:
                if backup.backup_id == backup_id:
                    backup_info = backup
                    break
            
            if not backup_info:
                self.logger.error(f"Backup '{backup_id}' not found for service '{service_id}'")
                return False
            
            # Read backup file
            backup_path = Path(backup_info.backup_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            with open(backup_path, 'r') as f:
                config = json.load(f)
            
            # Restore configuration
            return await self._update_service_config_impl(service_id, config, "backup-restore")
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup '{backup_id}' for service '{service_id}': {e}")
            return False
    
    async def _list_backups_impl(self, service_id: str) -> List[ConfigurationBackup]:
        """Implementation for listing backups."""
        return self._backups.get(service_id, [])
    
    # Advanced Methods Implementation
    
    async def _compare_configs_impl(self, service_id: str, version1: str, version2: str) -> Dict[str, Any]:
        """Implementation for comparing configurations."""
        try:
            versions = self._versions.get(service_id, [])
            config1 = None
            config2 = None
            
            for v in versions:
                if v.version == version1:
                    config1 = v.config_data
                if v.version == version2:
                    config2 = v.config_data
            
            if config1 is None or config2 is None:
                return {"error": "One or both versions not found"}
            
            # Simple diff implementation
            diff = {
                "added": {},
                "removed": {},
                "modified": {},
                "unchanged": {}
            }
            
            all_keys = set(config1.keys()) | set(config2.keys())
            
            for key in all_keys:
                if key in config1 and key in config2:
                    if config1[key] != config2[key]:
                        diff["modified"][key] = {"old": config1[key], "new": config2[key]}
                    else:
                        diff["unchanged"][key] = config1[key]
                elif key in config1:
                    diff["removed"][key] = config1[key]
                else:
                    diff["added"][key] = config2[key]
            
            return diff
            
        except Exception as e:
            self.logger.error(f"Failed to compare configurations: {e}")
            return {"error": str(e)}
    
    async def _bulk_update_configs_impl(self, updates: Dict[str, Dict[str, Any]], author: str) -> Dict[str, bool]:
        """Implementation for bulk configuration updates."""
        results = {}
        
        for service_id, config in updates.items():
            try:
                success = await self._update_service_config_impl(service_id, config, author)
                results[service_id] = success
            except Exception as e:
                self.logger.error(f"Failed to update configuration for '{service_id}': {e}")
                results[service_id] = False
        
        return results
    
    async def _export_config_impl(self, service_id: str, format: ConfigurationFormat) -> Optional[str]:
        """Implementation for exporting configuration."""
        try:
            config = self._configurations.get(service_id)
            if not config:
                return None
            
            if format == ConfigurationFormat.JSON:
                return json.dumps(config, indent=2, default=str)
            elif format == ConfigurationFormat.YAML:
                return yaml.dump(config, default_flow_style=False)
            else:
                self.logger.error(f"Unsupported export format: {format}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to export configuration for '{service_id}': {e}")
            return None
    
    async def _import_config_impl(self, service_id: str, config_data: str, format: ConfigurationFormat, author: str) -> bool:
        """Implementation for importing configuration."""
        try:
            if format == ConfigurationFormat.JSON:
                config = json.loads(config_data)
            elif format == ConfigurationFormat.YAML:
                config = yaml.safe_load(config_data)
            else:
                self.logger.error(f"Unsupported import format: {format}")
                return False
            
            return await self._update_service_config_impl(service_id, config, author)
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration for '{service_id}': {e}")
            return False    
  
  # Additional Methods for Enhanced API
    
    async def list_configured_services(self) -> List[str]:
        """
        List all services that have configurations.
        
        Returns:
            List of service IDs
        """
        return await self._safe_execute(
            "list_configured_services",
            self._list_configured_services_impl
        ) or []
    
    async def _list_configured_services_impl(self) -> List[str]:
        """Implementation for listing configured services."""
        return list(self._configurations.keys())
    
    async def list_service_versions(self, service_id: str) -> List[str]:
        """
        List all available versions for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of version strings
        """
        return await self._safe_execute(
            "list_service_versions",
            self._list_service_versions_impl,
            service_id
        ) or []
    
    async def _list_service_versions_impl(self, service_id: str) -> List[str]:
        """Implementation for listing service versions."""
        versions = self._versions.get(service_id, [])
        return [v.version for v in versions]
    
    async def get_service_version(self, service_id: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific version of service configuration.
        
        Args:
            service_id: Service identifier
            version: Version string
            
        Returns:
            Configuration dictionary or None if not found
        """
        return await self._safe_execute(
            "get_service_version",
            self._get_service_version_impl,
            service_id,
            version
        )
    
    async def _get_service_version_impl(self, service_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Implementation for getting a specific service version."""
        versions = self._versions.get(service_id, [])
        for v in versions:
            if v.version == version:
                return v.config_data
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get configuration management statistics.
        
        Returns:
            Statistics dictionary
        """
        return await self._safe_execute(
            "get_stats",
            self._get_stats_impl
        ) or {}
    
    async def _get_stats_impl(self) -> Dict[str, Any]:
        """Implementation for getting configuration statistics."""
        total_services = len(self._configurations)
        total_versions = sum(len(versions) for versions in self._versions.values())
        total_schemas = len(self._schemas)
        total_templates = len(self._templates)
        total_backups = sum(len(backups) for backups in self._backups.values())
        
        # Calculate average versions per service
        avg_versions = total_versions / total_services if total_services > 0 else 0
        
        # Get most recent activity
        latest_update = None
        for versions in self._versions.values():
            for version in versions:
                if latest_update is None or version.timestamp > latest_update:
                    latest_update = version.timestamp
        
        return {
            "services": {
                "total": total_services,
                "configured": total_services
            },
            "versions": {
                "total": total_versions,
                "average_per_service": round(avg_versions, 2)
            },
            "schemas": {
                "total": total_schemas,
                "builtin": 2,  # service and database schemas
                "custom": total_schemas - 2
            },
            "templates": {
                "total": total_templates,
                "builtin": 2,  # web-service and database-service templates
                "custom": total_templates - 2
            },
            "backups": {
                "total": total_backups
            },
            "activity": {
                "latest_update": latest_update.isoformat() if latest_update else None
            }
        }
    
    async def delete_service_config(self, service_id: str) -> bool:
        """
        Delete service configuration.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if deletion successful
        """
        return await self._safe_execute(
            "delete_service_config",
            self._delete_service_config_impl,
            service_id
        ) or False
    
    async def _delete_service_config_impl(self, service_id: str) -> bool:
        """Implementation for deleting service configuration."""
        if service_id not in self._configurations:
            return False
        
        # Remove configuration
        del self._configurations[service_id]
        
        # Remove versions
        if service_id in self._versions:
            del self._versions[service_id]
        
        # Remove backups
        if service_id in self._backups:
            del self._backups[service_id]
        
        self.logger.info(f"Configuration deleted for service '{service_id}'")
        return True
    
    async def create_backup(self, description: str = "Manual backup") -> Optional[str]:
        """
        Create a backup of all configurations.
        
        Args:
            description: Backup description
            
        Returns:
            Backup ID if successful
        """
        return await self._safe_execute(
            "create_backup",
            self._create_global_backup_impl,
            description
        )
    
    async def _create_global_backup_impl(self, description: str) -> Optional[str]:
        """Implementation for creating a global backup."""
        try:
            backup_id = f"global_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            backup_path = self._backup_directory / f"{backup_id}.json"
            
            # Create global backup data
            backup_data = {
                "configurations": self._configurations,
                "versions": {
                    service_id: [
                        {
                            "version": v.version,
                            "timestamp": v.timestamp.isoformat(),
                            "author": v.author,
                            "description": v.description,
                            "config_data": v.config_data
                        }
                        for v in versions
                    ]
                    for service_id, versions in self._versions.items()
                },
                "metadata": {
                    "backup_id": backup_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "description": description,
                    "total_services": len(self._configurations)
                }
            }
            
            # Write backup file
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            self.logger.info(f"Global backup created: {backup_id}")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create global backup: {e}")
            return None
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup information
        """
        return await self._safe_execute(
            "list_backups",
            self._list_all_backups_impl
        ) or []
    
    async def _list_all_backups_impl(self) -> List[Dict[str, Any]]:
        """Implementation for listing all backups."""
        all_backups = []
        
        # Add service-specific backups
        for service_id, backups in self._backups.items():
            for backup in backups:
                all_backups.append({
                    "backup_id": backup.backup_id,
                    "service_id": backup.service_id,
                    "timestamp": backup.timestamp.isoformat(),
                    "description": backup.description,
                    "size_bytes": backup.size_bytes,
                    "type": "service"
                })
        
        # Add global backups (scan backup directory)
        try:
            for backup_file in self._backup_directory.glob("global_*.json"):
                stat = backup_file.stat()
                all_backups.append({
                    "backup_id": backup_file.stem,
                    "service_id": None,
                    "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "description": "Global backup",
                    "size_bytes": stat.st_size,
                    "type": "global"
                })
        except Exception as e:
            self.logger.error(f"Error scanning backup directory: {e}")
        
        # Sort by timestamp (newest first)
        all_backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_backups
    
    async def restore_backup(self, backup_id: str) -> bool:
        """
        Restore configurations from a backup.
        
        Args:
            backup_id: Backup identifier
            
        Returns:
            True if restore successful
        """
        return await self._safe_execute(
            "restore_backup",
            self._restore_global_backup_impl,
            backup_id
        ) or False
    
    async def _restore_global_backup_impl(self, backup_id: str) -> bool:
        """Implementation for restoring from a global backup."""
        try:
            backup_path = self._backup_directory / f"{backup_id}.json"
            
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Read backup file
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            # Restore configurations
            if "configurations" in backup_data:
                self._configurations = backup_data["configurations"]
            
            # Restore versions
            if "versions" in backup_data:
                self._versions = {}
                for service_id, version_data in backup_data["versions"].items():
                    versions = []
                    for v_data in version_data:
                        version = ConfigurationVersion(
                            version=v_data["version"],
                            timestamp=datetime.fromisoformat(v_data["timestamp"]),
                            author=v_data["author"],
                            description=v_data["description"],
                            config_data=v_data["config_data"]
                        )
                        versions.append(version)
                    self._versions[service_id] = versions
            
            self.logger.info(f"Global backup restored: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore global backup '{backup_id}': {e}")
            return False
"""
Tests for configuration management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json
import tempfile
from pathlib import Path

from fastapi_microservices_sdk.web.configuration.configuration_manager import (
    ConfigurationManager,
    ConfigurationSchema,
    ConfigurationTemplate,
    ConfigurationVersion,
    ConfigurationBackup,
    ValidationResult,
    ConfigurationFormat,
    ConfigurationStatus,
    ValidationType
)


@pytest.fixture
def config_manager():
    """Create a configuration manager instance for testing."""
    config = {
        "backup_enabled": True,
        "max_versions": 10,
        "validation_enabled": True,
        "strict_validation": False,
        "auto_backup": True
    }
    return ConfigurationManager(config=config)


@pytest.fixture
def sample_config():
    """Create sample configuration data."""
    return {
        "name": "test-service",
        "port": 8080,
        "environment": "development",
        "replicas": 2,
        "resources": {
            "cpu": "100m",
            "memory": "128Mi"
        },
        "environment_variables": {
            "NODE_ENV": "development",
            "PORT": "8080"
        },
        "health_check": {
            "path": "/health",
            "interval": 30,
            "timeout": 5
        }
    }


@pytest.fixture
def sample_schema():
    """Create sample configuration schema."""
    return ConfigurationSchema(
        name="test-schema",
        description="Test configuration schema",
        schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "environment": {"type": "string", "enum": ["development", "staging", "production"]}
            },
            "required": ["name", "port"]
        },
        required_fields=["name", "port"],
        optional_fields=["environment"]
    )


@pytest.fixture
def sample_template():
    """Create sample configuration template."""
    return ConfigurationTemplate(
        name="test-template",
        description="Test configuration template",
        template_data={
            "name": "${service_name}",
            "port": "${port:8080}",
            "environment": "${environment:development}"
        },
        variables=["service_name", "port", "environment"],
        category="test",
        tags=["template", "test"]
    )


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, config_manager):
        """Test configuration manager initialization."""
        await config_manager.initialize()
        
        assert config_manager.is_initialized
        assert len(config_manager._schemas) > 0  # Built-in schemas loaded
        assert len(config_manager._templates) > 0  # Built-in templates loaded
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_get_set_service_config(self, config_manager, sample_config):
        """Test getting and setting service configuration."""
        await config_manager.initialize()
        
        service_id = "test-service"
        
        # Initially no configuration
        config = await config_manager.get_service_config(service_id)
        assert config is None
        
        # Set configuration
        success = await config_manager.update_service_config(service_id, sample_config, "test-user")
        assert success is True
        
        # Get configuration
        config = await config_manager.get_service_config(service_id)
        assert config is not None
        assert config["name"] == "test-service"
        assert config["port"] == 8080
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_validation(self, config_manager, sample_config):
        """Test configuration validation."""
        await config_manager.initialize()
        
        service_id = "test-service"
        
        # Valid configuration
        result = await config_manager.validate_config(service_id, sample_config)
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0
        
        # Invalid configuration (missing required field)
        invalid_config = {"port": 8080}  # Missing 'name'
        result = await config_manager.validate_config(service_id, invalid_config)
        assert result.valid is False
        assert len(result.errors) > 0
        
        # Invalid configuration (wrong type)
        invalid_config = {"name": "test", "port": "not-a-number"}
        result = await config_manager.validate_config(service_id, invalid_config)
        assert result.valid is False
        assert len(result.errors) > 0
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_versioning(self, config_manager, sample_config):
        """Test configuration versioning."""
        await config_manager.initialize()
        
        service_id = "test-service"
        
        # Set initial configuration
        await config_manager.update_service_config(service_id, sample_config, "user1")
        
        # Update configuration
        updated_config = sample_config.copy()
        updated_config["port"] = 9090
        await config_manager.update_service_config(service_id, updated_config, "user2")
        
        # Get configuration history
        history = await config_manager.get_config_history(service_id)
        assert len(history) >= 1
        assert isinstance(history[0], ConfigurationVersion)
        assert history[0].author in ["user1", "user2"]
        
        # Restore to previous version
        if len(history) > 0:
            version_to_restore = history[0].version
            success = await config_manager.restore_config_version(service_id, version_to_restore)
            assert success is True
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_schema_management(self, config_manager, sample_schema):
        """Test schema management."""
        await config_manager.initialize()
        
        # Register schema
        success = await config_manager.register_schema(sample_schema)
        assert success is True
        
        # Get schema
        schema = await config_manager.get_schema("test-schema")
        assert schema is not None
        assert schema.name == "test-schema"
        assert schema.description == "Test configuration schema"
        
        # List schemas
        schemas = await config_manager.list_schemas()
        assert len(schemas) > 0
        schema_names = [s.name for s in schemas]
        assert "test-schema" in schema_names
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_template_management(self, config_manager, sample_template):
        """Test template management."""
        await config_manager.initialize()
        
        # Create template
        success = await config_manager.create_template(sample_template)
        assert success is True
        
        # Get template
        template = await config_manager.get_template("test-template")
        assert template is not None
        assert template.name == "test-template"
        assert template.category == "test"
        
        # List templates
        templates = await config_manager.list_templates()
        assert len(templates) > 0
        template_names = [t.name for t in templates]
        assert "test-template" in template_names
        
        # List templates by category
        test_templates = await config_manager.list_templates(category="test")
        assert len(test_templates) >= 1
        assert all(t.category == "test" for t in test_templates)
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_template_application(self, config_manager, sample_template):
        """Test applying configuration templates."""
        await config_manager.initialize()
        
        # Create template
        await config_manager.create_template(sample_template)
        
        # Apply template with variables
        service_id = "templated-service"
        variables = {
            "service_name": "my-service",
            "port": "3000",
            "environment": "staging"
        }
        
        success = await config_manager.apply_template(service_id, "test-template", variables)
        assert success is True
        
        # Verify applied configuration
        config = await config_manager.get_service_config(service_id)
        assert config is not None
        assert config["name"] == "my-service"
        assert config["port"] == "3000"
        assert config["environment"] == "staging"
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_backup_and_restore(self, config_manager, sample_config):
        """Test configuration backup and restore."""
        await config_manager.initialize()
        
        service_id = "backup-test-service"
        
        # Set initial configuration
        await config_manager.update_service_config(service_id, sample_config, "test-user")
        
        # Create backup
        backup_id = await config_manager.create_backup(service_id, "Test backup")
        assert backup_id is not None
        
        # List backups
        backups = await config_manager.list_backups(service_id)
        assert len(backups) >= 1
        backup_ids = [b.backup_id for b in backups]
        assert backup_id in backup_ids
        
        # Modify configuration
        modified_config = sample_config.copy()
        modified_config["port"] = 9999
        await config_manager.update_service_config(service_id, modified_config, "test-user")
        
        # Verify modification
        current_config = await config_manager.get_service_config(service_id)
        assert current_config["port"] == 9999
        
        # Restore from backup
        success = await config_manager.restore_backup(service_id, backup_id)
        assert success is True
        
        # Verify restoration
        restored_config = await config_manager.get_service_config(service_id)
        assert restored_config["port"] == 8080  # Original value
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_comparison(self, config_manager, sample_config):
        """Test configuration comparison."""
        await config_manager.initialize()
        
        service_id = "compare-test-service"
        
        # Set initial configuration
        await config_manager.update_service_config(service_id, sample_config, "user1")
        
        # Update configuration
        updated_config = sample_config.copy()
        updated_config["port"] = 9090
        updated_config["replicas"] = 3
        del updated_config["health_check"]  # Remove a field
        updated_config["new_field"] = "new_value"  # Add a field
        
        await config_manager.update_service_config(service_id, updated_config, "user2")
        
        # Get history for comparison
        history = await config_manager.get_config_history(service_id)
        assert len(history) >= 2
        
        # Compare configurations
        diff = await config_manager.compare_configs(
            service_id, 
            history[0].version, 
            history[1].version
        )
        
        assert "modified" in diff
        assert "added" in diff
        assert "removed" in diff
        assert "unchanged" in diff
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_bulk_configuration_update(self, config_manager, sample_config):
        """Test bulk configuration updates."""
        await config_manager.initialize()
        
        # Prepare bulk updates
        updates = {
            "service1": sample_config.copy(),
            "service2": sample_config.copy(),
            "service3": sample_config.copy()
        }
        
        # Modify each config slightly
        updates["service1"]["port"] = 8081
        updates["service2"]["port"] = 8082
        updates["service3"]["port"] = 8083
        
        # Perform bulk update
        results = await config_manager.bulk_update_configs(updates, "bulk-user")
        
        assert len(results) == 3
        assert all(results.values())  # All should be successful
        
        # Verify individual configurations
        for service_id, expected_config in updates.items():
            actual_config = await config_manager.get_service_config(service_id)
            assert actual_config is not None
            assert actual_config["port"] == expected_config["port"]
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_export_import(self, config_manager, sample_config):
        """Test configuration export and import."""
        await config_manager.initialize()
        
        service_id = "export-import-test"
        
        # Set configuration
        await config_manager.update_service_config(service_id, sample_config, "test-user")
        
        # Export configuration as JSON
        json_export = await config_manager.export_config(service_id, ConfigurationFormat.JSON)
        assert json_export is not None
        
        # Verify JSON export
        exported_config = json.loads(json_export)
        assert exported_config["name"] == sample_config["name"]
        assert exported_config["port"] == sample_config["port"]
        
        # Export configuration as YAML
        yaml_export = await config_manager.export_config(service_id, ConfigurationFormat.YAML)
        assert yaml_export is not None
        assert "name: test-service" in yaml_export
        
        # Import configuration to new service
        new_service_id = "imported-service"
        success = await config_manager.import_config(
            new_service_id, 
            json_export, 
            ConfigurationFormat.JSON, 
            "import-user"
        )
        assert success is True
        
        # Verify imported configuration
        imported_config = await config_manager.get_service_config(new_service_id)
        assert imported_config is not None
        assert imported_config["name"] == sample_config["name"]
        assert imported_config["port"] == sample_config["port"]
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_validation_types(self, config_manager, sample_config):
        """Test different validation types."""
        await config_manager.initialize()
        
        service_id = "validation-test"
        
        # Schema validation
        result = await config_manager.validate_config(
            service_id, 
            sample_config, 
            validation_type=ValidationType.SCHEMA
        )
        assert isinstance(result, ValidationResult)
        assert result.validation_type == ValidationType.SCHEMA
        
        # Syntax validation
        result = await config_manager.validate_config(
            service_id, 
            sample_config, 
            validation_type=ValidationType.SYNTAX
        )
        assert result.validation_type == ValidationType.SYNTAX
        
        # Dependency validation
        result = await config_manager.validate_config(
            service_id, 
            sample_config, 
            validation_type=ValidationType.DEPENDENCY
        )
        assert result.validation_type == ValidationType.DEPENDENCY
        
        # Semantic validation (all types)
        result = await config_manager.validate_config(
            service_id, 
            sample_config, 
            validation_type=ValidationType.SEMANTIC
        )
        assert result.validation_type == ValidationType.SEMANTIC
        
        await config_manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_configuration_callbacks(self, config_manager, sample_config):
        """Test configuration change and validation callbacks."""
        await config_manager.initialize()
        
        # Setup callback tracking
        change_calls = []
        validation_calls = []
        
        async def change_callback(service_id, config, author):
            change_calls.append((service_id, config, author))
        
        async def validation_callback(service_id, config, result):
            validation_calls.append((service_id, config, result))
        
        # Add callbacks
        await config_manager.add_change_callback(change_callback)
        await config_manager.add_validation_callback(validation_callback)
        
        service_id = "callback-test"
        
        # Update configuration (should trigger callbacks)
        await config_manager.update_service_config(service_id, sample_config, "callback-user")
        
        # Verify change callback was called
        assert len(change_calls) >= 1
        assert change_calls[0][0] == service_id
        assert change_calls[0][2] == "callback-user"
        
        # Validate configuration (should trigger validation callback)
        await config_manager.validate_config(service_id, sample_config)
        
        # Verify validation callback was called
        assert len(validation_calls) >= 1
        assert validation_calls[0][0] == service_id
        
        await config_manager.shutdown()


class TestConfigurationDataClasses:
    """Test configuration data classes."""
    
    def test_configuration_version_checksum(self):
        """Test configuration version checksum calculation."""
        config_data = {"name": "test", "port": 8080}
        
        version = ConfigurationVersion(
            version="v1",
            timestamp=datetime.utcnow(),
            author="test-user",
            description="Test version",
            config_data=config_data
        )
        
        assert version.checksum != ""
        assert len(version.checksum) == 16  # SHA256 truncated to 16 chars
        
        # Same config should produce same checksum
        version2 = ConfigurationVersion(
            version="v2",
            timestamp=datetime.utcnow(),
            author="test-user2",
            description="Test version 2",
            config_data=config_data
        )
        
        assert version.checksum == version2.checksum
    
    def test_validation_result(self):
        """Test validation result data class."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            validation_type=ValidationType.SCHEMA
        )
        
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.validation_type == ValidationType.SCHEMA
        assert isinstance(result.timestamp, datetime)
    
    def test_configuration_schema(self):
        """Test configuration schema data class."""
        schema = ConfigurationSchema(
            name="test-schema",
            description="Test schema",
            schema={"type": "object"},
            required_fields=["name"],
            optional_fields=["port"]
        )
        
        assert schema.name == "test-schema"
        assert schema.version == "1.0"  # Default version
        assert schema.format == ConfigurationFormat.JSON  # Default format
        assert isinstance(schema.created_at, datetime)
        assert isinstance(schema.updated_at, datetime)
    
    def test_configuration_template(self):
        """Test configuration template data class."""
        template = ConfigurationTemplate(
            name="test-template",
            description="Test template",
            template_data={"name": "${service_name}"},
            variables=["service_name"]
        )
        
        assert template.name == "test-template"
        assert template.category == "general"  # Default category
        assert len(template.variables) == 1
        assert isinstance(template.created_at, datetime)
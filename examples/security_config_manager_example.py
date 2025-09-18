"""
Example: Security Configuration Manager

This example demonstrates how to use the SecurityConfigManager for
centralized configuration management of security components.

Features demonstrated:
- Loading configuration from multiple sources (file + environment)
- Configuration validation and error handling
- Configuration updates and change notifications
- Version management and history tracking
- Integration with security components
"""

import asyncio
import logging
import tempfile
import os
from pathlib import Path
from datetime import datetime

# Import configuration management components
from fastapi_microservices_sdk.security.advanced.config_manager import (
    SecurityConfigManager,
    FileConfigProvider,
    EnvironmentConfigProvider,
    ConfigFormat,
    ConfigChangeType,
    create_hybrid_config_manager
)
from fastapi_microservices_sdk.security.advanced.config import AdvancedSecurityConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_basic_usage():
    """Demonstrate basic configuration management usage."""
    logger.info("=== Basic Configuration Management ===")
    
    # Create a configuration manager
    config_manager = SecurityConfigManager()
    
    # Add file provider
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        initial_config = {
            "jwt_secret_key": "initial_secret_key",
            "jwt_algorithm": "HS256",
            "jwt_expiration_minutes": 60,
            "mtls_enabled": True,
            "rbac_enabled": True,
            "abac_enabled": False,
            "threat_detection_enabled": True,
            "debug_mode": False
        }
        yaml.dump(initial_config, f)
        config_file = f.name
    
    try:
        # Add providers
        file_provider = FileConfigProvider(config_file, ConfigFormat.YAML)
        config_manager.add_provider(file_provider)
        
        # Load initial configuration
        config = await config_manager.load_configuration()
        logger.info(f"Loaded configuration: {config}")
        
        # Display current version
        logger.info(f"Current version: {config_manager.current_version}")
        
        # Update configuration
        updates = {
            "jwt_secret_key": "updated_secret_key",
            "debug_mode": True,
            "new_feature_enabled": True
        }
        
        success = await config_manager.update_configuration(updates, "example_app")
        if success:
            logger.info("Configuration updated successfully")
            logger.info(f"New version: {config_manager.current_version}")
        else:
            logger.error("Failed to update configuration")
        
        # Get updated configuration
        updated_config = config_manager.get_configuration()
        logger.info(f"Updated configuration: {updated_config}")
        
    finally:
        # Cleanup
        os.unlink(config_file)


async def demonstrate_validation():
    """Demonstrate configuration validation."""
    logger.info("\n=== Configuration Validation ===")
    
    config_manager = SecurityConfigManager()
    
    # Test valid configuration
    valid_config = {
        "jwt_secret_key": "valid_secret",
        "jwt_algorithm": "HS256",
        "jwt_expiration_minutes": 60,
        "mtls_enabled": True,
        "rbac": {
            "roles": [
                {"name": "admin", "permissions": ["read", "write", "delete"]},
                {"name": "user", "permissions": ["read"]}
            ],
            "permissions": [
                {"name": "read", "description": "Read access"},
                {"name": "write", "description": "Write access"},
                {"name": "delete", "description": "Delete access"}
            ]
        },
        "abac": {
            "policies": [
                {
                    "id": "admin_policy",
                    "effect": "Permit",
                    "rule": "subject.role == 'admin'"
                }
            ]
        }
    }
    
    errors = config_manager.validate_configuration(valid_config)
    if not errors:
        logger.info("✅ Valid configuration passed validation")
    else:
        logger.error(f"❌ Validation errors: {errors}")
    
    # Test invalid configuration
    invalid_config = {
        "jwt_algorithm": "INVALID_ALGORITHM",  # Invalid algorithm
        "jwt_expiration_minutes": -10,         # Invalid value
        "mtls_enabled": "not_boolean",         # Wrong type
        "rbac": {
            "roles": "not_a_list",             # Wrong type
            "permissions": [
                {"description": "Missing name"}  # Missing required field
            ]
        },
        "abac": {
            "policies": [
                {
                    "id": "bad_policy",
                    "effect": "InvalidEffect"      # Invalid effect, missing rule
                }
            ]
        }
    }
    
    errors = config_manager.validate_configuration(invalid_config)
    if errors:
        logger.info("✅ Invalid configuration correctly rejected")
        for error in errors:
            logger.info(f"  - {error}")
    else:
        logger.error("❌ Invalid configuration incorrectly accepted")


async def demonstrate_change_notifications():
    """Demonstrate configuration change notifications."""
    logger.info("\n=== Change Notifications ===")
    
    config_manager = SecurityConfigManager()
    
    # Track changes
    changes_received = []
    
    def change_listener(change):
        """Handle configuration changes."""
        changes_received.append(change)
        logger.info(f"Configuration change detected:")
        logger.info(f"  Type: {change.change_type.value}")
        logger.info(f"  Component: {change.component}")
        logger.info(f"  Key: {change.key}")
        if change.old_value is not None:
            logger.info(f"  Old value: {change.old_value}")
        if change.new_value is not None:
            logger.info(f"  New value: {change.new_value}")
        logger.info(f"  Timestamp: {change.timestamp}")
    
    # Add change listener
    config_manager.add_change_listener(change_listener)
    
    # Initialize configuration
    config_manager.config = {
        "jwt_secret_key": "initial_secret",
        "mtls_enabled": False
    }
    
    # Make some updates
    await config_manager.update_configuration({
        "jwt_secret_key": "updated_secret",  # Update
        "rbac_enabled": True,                # Create
        "mtls_enabled": None                 # Delete (by setting to None then removing)
    }, "notification_demo")
    
    # Remove the None value to simulate deletion
    if "mtls_enabled" in config_manager.config and config_manager.config["mtls_enabled"] is None:
        del config_manager.config["mtls_enabled"]
    
    logger.info(f"Total changes received: {len(changes_received)}")


async def demonstrate_version_management():
    """Demonstrate configuration version management."""
    logger.info("\n=== Version Management ===")
    
    config_manager = SecurityConfigManager()
    
    # Initialize with base configuration
    config_manager.config = {
        "jwt_secret_key": "v1_secret",
        "jwt_algorithm": "HS256"
    }
    
    # Make several updates to create version history
    updates_sequence = [
        ({"jwt_secret_key": "v2_secret", "mtls_enabled": True}, "v2_update"),
        ({"rbac_enabled": True, "debug_mode": True}, "v3_update"),
        ({"jwt_algorithm": "HS512", "abac_enabled": True}, "v4_update")
    ]
    
    for updates, component in updates_sequence:
        await config_manager.update_configuration(updates, component)
    
    # Display version history
    versions = config_manager.get_version_history()
    logger.info(f"Configuration has {len(versions)} versions:")
    
    for version in versions:
        logger.info(f"  Version: {version.version}")
        logger.info(f"    Timestamp: {version.timestamp}")
        logger.info(f"    Checksum: {version.checksum[:12]}...")
        logger.info(f"    Changes: {len(version.changes)}")
        for change in version.changes:
            logger.info(f"      - {change.change_type.value}: {change.key}")
        logger.info("")


async def demonstrate_hybrid_configuration():
    """Demonstrate hybrid configuration (file + environment)."""
    logger.info("\n=== Hybrid Configuration (File + Environment) ===")
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        import yaml
        file_config = {
            "jwt_secret_key": "file_secret",
            "jwt_algorithm": "HS256",
            "mtls_enabled": True,
            "rbac_enabled": True
        }
        yaml.dump(file_config, f)
        config_file = f.name
    
    # Set environment variables (these will override file values)
    env_vars = {
        "SECURITY_JWT_SECRET_KEY": "env_secret_override",
        "SECURITY_DEBUG_MODE": "true",
        "SECURITY_THREAT_DETECTION_ENABLED": "true"
    }
    
    try:
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        # Create hybrid configuration manager
        config_manager = create_hybrid_config_manager(
            config_file=config_file,
            env_prefix="SECURITY_",
            format=ConfigFormat.YAML
        )
        
        # Load configuration
        config = await config_manager.load_configuration()
        
        logger.info("Hybrid configuration loaded:")
        logger.info(f"  jwt_secret_key: {config.get('jwt_secret_key')} (from environment)")
        logger.info(f"  jwt_algorithm: {config.get('jwt_algorithm')} (from file)")
        logger.info(f"  mtls_enabled: {config.get('mtls_enabled')} (from file)")
        logger.info(f"  debug_mode: {config.get('debug_mode')} (from environment)")
        logger.info(f"  threat_detection_enabled: {config.get('threat_detection_enabled')} (from environment)")
        
        # Demonstrate that environment overrides file
        assert config["jwt_secret_key"] == "env_secret_override", "Environment should override file"
        assert config["jwt_algorithm"] == "HS256", "File value should be preserved"
        
        logger.info("✅ Hybrid configuration working correctly")
        
    finally:
        # Cleanup
        os.unlink(config_file)
        for key in env_vars:
            if key in os.environ:
                del os.environ[key]


async def demonstrate_integration_with_security_config():
    """Demonstrate integration with AdvancedSecurityConfig."""
    logger.info("\n=== Integration with AdvancedSecurityConfig ===")
    
    # Create configuration manager
    config_manager = SecurityConfigManager()
    
    # Load configuration
    config_data = {
        "jwt_secret_key": "integration_secret",
        "jwt_algorithm": "HS256",
        "jwt_expiration_minutes": 120,
        "mtls_enabled": True,
        "rbac_enabled": True,
        "abac_enabled": True,
        "threat_detection_enabled": True,
        "debug_mode": True,
        "log_level": "INFO"
    }
    
    # Simulate loading from provider
    config_manager.config = config_data
    
    # Create AdvancedSecurityConfig from managed configuration
    try:
        security_config = AdvancedSecurityConfig(**config_data)
        logger.info("✅ Successfully created AdvancedSecurityConfig from managed configuration")
        logger.info(f"  JWT Algorithm: {security_config.jwt_algorithm}")
        logger.info(f"  mTLS Enabled: {security_config.mtls_enabled}")
        logger.info(f"  RBAC Enabled: {security_config.rbac_enabled}")
        logger.info(f"  ABAC Enabled: {security_config.abac_enabled}")
        logger.info(f"  Threat Detection Enabled: {security_config.threat_detection_enabled}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create AdvancedSecurityConfig: {e}")


async def demonstrate_metrics():
    """Demonstrate configuration metrics."""
    logger.info("\n=== Configuration Metrics ===")
    
    config_manager = SecurityConfigManager()
    
    # Add some providers and make changes
    config_manager.add_provider(FileConfigProvider("dummy.yaml"))
    config_manager.add_provider(EnvironmentConfigProvider())
    
    # Add change listener
    config_manager.add_change_listener(lambda change: None)
    
    # Set some configuration
    config_manager.config = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3"
    }
    
    # Make an update to create a version
    await config_manager.update_configuration({"key4": "value4"}, "metrics_demo")
    
    # Get metrics
    metrics = config_manager.get_metrics()
    
    logger.info("Configuration Manager Metrics:")
    logger.info(f"  Total versions: {metrics['total_versions']}")
    logger.info(f"  Current version: {metrics['current_version']}")
    logger.info(f"  Providers count: {metrics['providers_count']}")
    logger.info(f"  Validators count: {metrics['validators_count']}")
    logger.info(f"  Listeners count: {metrics['listeners_count']}")
    logger.info(f"  Configuration size: {metrics['config_size']} keys")
    logger.info(f"  Last update: {metrics['last_update']}")


async def main():
    """Run all configuration management examples."""
    logger.info("🚀 Security Configuration Manager Examples")
    logger.info("=" * 60)
    
    examples = [
        demonstrate_basic_usage,
        demonstrate_validation,
        demonstrate_change_notifications,
        demonstrate_version_management,
        demonstrate_hybrid_configuration,
        demonstrate_integration_with_security_config,
        demonstrate_metrics
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.error(f"❌ Example {example.__name__} failed: {e}")
        
        # Add separator between examples
        logger.info("-" * 40)
    
    logger.info("🎉 All configuration management examples completed!")
    
    # Summary
    logger.info("\n📋 Summary of Features Demonstrated:")
    logger.info("  ✅ Basic configuration loading and updating")
    logger.info("  ✅ Multi-source configuration (file + environment)")
    logger.info("  ✅ Configuration validation with detailed error reporting")
    logger.info("  ✅ Change notifications and event handling")
    logger.info("  ✅ Version management and history tracking")
    logger.info("  ✅ Integration with AdvancedSecurityConfig")
    logger.info("  ✅ Configuration metrics and monitoring")
    
    logger.info("\n🔧 Key Benefits:")
    logger.info("  • Centralized configuration management")
    logger.info("  • Automatic validation and error prevention")
    logger.info("  • Change tracking and audit trail")
    logger.info("  • Hot-reload capabilities")
    logger.info("  • Multi-environment support")
    logger.info("  • Extensible provider and validator system")


if __name__ == "__main__":
    asyncio.run(main())
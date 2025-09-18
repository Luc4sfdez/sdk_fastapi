"""
Security Configuration Manager for FastAPI Microservices SDK.

This module provides centralized configuration management for security components
with support for multiple configuration sources, validation, change tracking,
and version management.
"""

import asyncio
import hashlib
import json
import os
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
import logging

from .exceptions import AdvancedSecurityError


class SecurityConfigurationError(AdvancedSecurityError):
    """Configuration-specific security errors."""
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_source: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_source = config_source
        if config_key:
            self.details["config_key"] = config_key
        if config_source:
            self.details["config_source"] = config_source


class ConfigFormat(str, Enum):
    """Configuration file formats."""
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"


class ConfigSource(str, Enum):
    """Configuration sources."""
    FILE = "file"
    ENVIRONMENT = "environment"
    REMOTE = "remote"
    MEMORY = "memory"


class ConfigChangeType(str, Enum):
    """Types of configuration changes."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class ConfigChange:
    """Represents a configuration change."""
    change_id: str
    change_type: ConfigChangeType
    component: str
    key: str
    old_value: Any = None
    new_value: Any = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigVersion:
    """Represents a configuration version."""
    version: str
    timestamp: datetime
    checksum: str
    changes: List[ConfigChange]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigProvider(ABC):
    """Abstract base class for configuration providers."""
    
    @abstractmethod
    async def load_config(self) -> Dict[str, Any]:
        """Load configuration from the provider."""
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about the configuration source."""
        pass


class FileConfigProvider(ConfigProvider):
    """File-based configuration provider."""
    
    def __init__(self, file_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML):
        self.file_path = Path(file_path)
        self.format = format
    
    async def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.file_path.exists():
            raise SecurityConfigurationError(
                f"Configuration file not found: {self.file_path}",
                config_source=str(self.file_path)
            )
        
        try:
            with open(self.file_path, 'r') as f:
                if self.format == ConfigFormat.YAML:
                    return yaml.safe_load(f) or {}
                elif self.format == ConfigFormat.JSON:
                    return json.load(f)
                else:
                    raise SecurityConfigurationError(
                        f"Unsupported format: {self.format}",
                        config_source=str(self.file_path)
                    )
        except Exception as e:
            raise SecurityConfigurationError(
                f"Failed to load configuration from {self.file_path}: {e}",
                config_source=str(self.file_path)
            ) from e
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get file source information."""
        return {
            "source_type": ConfigSource.FILE.value,
            "file_path": str(self.file_path),
            "format": self.format.value,
            "exists": self.file_path.exists(),
            "size": self.file_path.stat().st_size if self.file_path.exists() else 0
        }


class EnvironmentConfigProvider(ConfigProvider):
    """Environment variable configuration provider."""
    
    def __init__(self, prefix: str = "SECURITY_"):
        self.prefix = prefix
    
    async def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.prefix):].lower()
                
                # Convert string values to appropriate types
                config[config_key] = self._convert_value(value)
        
        return config
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get environment source information."""
        env_vars = {k: v for k, v in os.environ.items() if k.startswith(self.prefix)}
        return {
            "source_type": ConfigSource.ENVIRONMENT.value,
            "prefix": self.prefix,
            "variables_count": len(env_vars),
            "variables": list(env_vars.keys())
        }


class ConfigValidator(ABC):
    """Abstract base class for configuration validators."""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return list of errors."""
        pass


class SecurityConfigValidator(ConfigValidator):
    """Validator for basic security configuration."""
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate security configuration."""
        errors = []
        
        # JWT validation
        if 'jwt_algorithm' in config:
            valid_algorithms = ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']
            if config['jwt_algorithm'] not in valid_algorithms:
                errors.append(f"Invalid JWT algorithm: {config['jwt_algorithm']}")
        
        if 'jwt_expiration_minutes' in config:
            try:
                exp_minutes = int(config['jwt_expiration_minutes'])
                if exp_minutes <= 0:
                    errors.append("JWT expiration minutes must be positive")
            except (ValueError, TypeError):
                errors.append("JWT expiration minutes must be a number")
        
        # Boolean field validation
        boolean_fields = ['mtls_enabled', 'rbac_enabled', 'abac_enabled', 'threat_detection_enabled', 'debug_mode']
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"{field} must be a boolean value")
        
        return errors


class RBACConfigValidator(ConfigValidator):
    """Validator for RBAC configuration."""
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate RBAC configuration."""
        errors = []
        
        if 'rbac' not in config:
            return errors
        
        rbac_config = config['rbac']
        
        # Validate roles
        if 'roles' in rbac_config:
            if not isinstance(rbac_config['roles'], list):
                errors.append("RBAC roles must be a list")
            else:
                for i, role in enumerate(rbac_config['roles']):
                    if not isinstance(role, dict):
                        errors.append(f"RBAC role {i} must be a dictionary")
                        continue
                    
                    if 'name' not in role:
                        errors.append(f"RBAC role {i} missing required 'name' field")
                    
                    if 'permissions' in role and not isinstance(role['permissions'], list):
                        errors.append(f"RBAC role {i} permissions must be a list")
        
        # Validate permissions
        if 'permissions' in rbac_config:
            if not isinstance(rbac_config['permissions'], list):
                errors.append("RBAC permissions must be a list")
            else:
                for i, permission in enumerate(rbac_config['permissions']):
                    if not isinstance(permission, dict):
                        errors.append(f"RBAC permission {i} must be a dictionary")
                        continue
                    
                    if 'name' not in permission:
                        errors.append(f"RBAC permission {i} missing required 'name' field")
        
        return errors


class ABACConfigValidator(ConfigValidator):
    """Validator for ABAC configuration."""
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate ABAC configuration."""
        errors = []
        
        if 'abac' not in config:
            return errors
        
        abac_config = config['abac']
        
        # Validate policies
        if 'policies' in abac_config:
            if not isinstance(abac_config['policies'], list):
                errors.append("ABAC policies must be a list")
            else:
                for i, policy in enumerate(abac_config['policies']):
                    if not isinstance(policy, dict):
                        errors.append(f"ABAC policy {i} must be a dictionary")
                        continue
                    
                    if 'id' not in policy:
                        errors.append(f"ABAC policy {i} missing required 'id' field")
                    
                    if 'effect' not in policy:
                        errors.append(f"ABAC policy {i} missing required 'effect' field")
                    elif policy['effect'] not in ['Permit', 'Deny']:
                        errors.append(f"ABAC policy {i} effect must be 'Permit' or 'Deny'")
                    
                    if 'rule' not in policy:
                        errors.append(f"ABAC policy {i} missing required 'rule' field")
        
        return errors


class SecurityConfigManager:
    """Centralized security configuration manager."""
    
    def __init__(self):
        self.providers: List[ConfigProvider] = []
        self.validators: List[ConfigValidator] = []
        self.change_listeners: List[Callable[[ConfigChange], None]] = []
        self.config: Dict[str, Any] = {}
        self.versions: List[ConfigVersion] = []
        self.current_version: str = "v0.0.0"
        self.logger = logging.getLogger(__name__)
    
    def add_provider(self, provider: ConfigProvider):
        """Add a configuration provider."""
        self.providers.append(provider)
    
    def add_validator(self, validator: ConfigValidator):
        """Add a configuration validator."""
        self.validators.append(validator)
    
    def add_change_listener(self, listener: Callable[[ConfigChange], None]):
        """Add a configuration change listener."""
        self.change_listeners.append(listener)
    
    async def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from all providers."""
        merged_config = {}
        
        for provider in self.providers:
            try:
                provider_config = await provider.load_config()
                merged_config.update(provider_config)
            except Exception as e:
                self.logger.error(f"Failed to load from provider {provider}: {e}")
                raise
        
        # Validate merged configuration
        errors = self.validate_configuration(merged_config)
        if errors:
            raise SecurityConfigurationError(
                f"Configuration validation failed: {'; '.join(errors)}"
            )
        
        self.config = merged_config
        return self.config
    
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration using all validators."""
        all_errors = []
        
        for validator in self.validators:
            errors = validator.validate(config)
            all_errors.extend(errors)
        
        return all_errors
    
    async def update_configuration(self, updates: Dict[str, Any], component: str) -> bool:
        """Update configuration with change tracking."""
        try:
            changes = []
            old_config = self.config.copy()
            
            for key, new_value in updates.items():
                old_value = self.config.get(key)
                
                if old_value != new_value:
                    if key not in self.config:
                        change_type = ConfigChangeType.CREATE
                    elif new_value is None:
                        change_type = ConfigChangeType.DELETE
                    else:
                        change_type = ConfigChangeType.UPDATE
                    
                    change = ConfigChange(
                        change_id=f"{component}_{key}_{datetime.now().timestamp()}",
                        change_type=change_type,
                        component=component,
                        key=key,
                        old_value=old_value,
                        new_value=new_value
                    )
                    changes.append(change)
                    
                    # Notify listeners
                    for listener in self.change_listeners:
                        try:
                            listener(change)
                        except Exception as e:
                            self.logger.error(f"Change listener error: {e}")
            
            # Apply updates
            self.config.update(updates)
            
            # Remove None values (deletion)
            keys_to_delete = [k for k, v in self.config.items() if v is None]
            for key in keys_to_delete:
                del self.config[key]
            
            # Validate updated configuration
            errors = self.validate_configuration(self.config)
            if errors:
                # Rollback
                self.config = old_config
                raise SecurityConfigurationError(
                    f"Configuration update validation failed: {'; '.join(errors)}"
                )
            
            # Create new version if there were changes
            if changes:
                self._create_version(changes)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration update failed: {e}")
            return False
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.copy()
    
    def get_version_history(self) -> List[ConfigVersion]:
        """Get configuration version history."""
        return self.versions.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get configuration manager metrics."""
        return {
            "total_versions": len(self.versions),
            "current_version": self.current_version,
            "providers_count": len(self.providers),
            "validators_count": len(self.validators),
            "listeners_count": len(self.change_listeners),
            "config_size": len(self.config),
            "last_update": self.versions[-1].timestamp.isoformat() if self.versions else None
        }
    
    def _create_version(self, changes: List[ConfigChange]):
        """Create a new configuration version."""
        # Generate version number
        version_num = len(self.versions) + 1
        version = f"v1.{version_num}.0"
        
        # Calculate checksum
        config_str = json.dumps(self.config, sort_keys=True)
        checksum = hashlib.sha256(config_str.encode()).hexdigest()
        
        # Create version
        config_version = ConfigVersion(
            version=version,
            timestamp=datetime.now(timezone.utc),
            checksum=checksum,
            changes=changes
        )
        
        self.versions.append(config_version)
        self.current_version = version


# Factory functions
def create_file_config_manager(
    config_file: Union[str, Path],
    format: ConfigFormat = ConfigFormat.YAML
) -> SecurityConfigManager:
    """Create a file-based configuration manager."""
    manager = SecurityConfigManager()
    
    # Add file provider
    file_provider = FileConfigProvider(config_file, format)
    manager.add_provider(file_provider)
    
    # Add default validators
    manager.add_validator(SecurityConfigValidator())
    manager.add_validator(RBACConfigValidator())
    manager.add_validator(ABACConfigValidator())
    
    return manager


def create_env_config_manager(prefix: str = "SECURITY_") -> SecurityConfigManager:
    """Create an environment-based configuration manager."""
    manager = SecurityConfigManager()
    
    # Add environment provider
    env_provider = EnvironmentConfigProvider(prefix)
    manager.add_provider(env_provider)
    
    # Add default validators
    manager.add_validator(SecurityConfigValidator())
    manager.add_validator(RBACConfigValidator())
    manager.add_validator(ABACConfigValidator())
    
    return manager


def create_hybrid_config_manager(
    config_file: Union[str, Path],
    env_prefix: str = "SECURITY_",
    format: ConfigFormat = ConfigFormat.YAML
) -> SecurityConfigManager:
    """Create a hybrid configuration manager (file + environment)."""
    manager = SecurityConfigManager()
    
    # Add file provider first (lower priority)
    file_provider = FileConfigProvider(config_file, format)
    manager.add_provider(file_provider)
    
    # Add environment provider second (higher priority, will override file values)
    env_provider = EnvironmentConfigProvider(env_prefix)
    manager.add_provider(env_provider)
    
    # Add default validators
    manager.add_validator(SecurityConfigValidator())
    manager.add_validator(RBACConfigValidator())
    manager.add_validator(ABACConfigValidator())
    
    return manager
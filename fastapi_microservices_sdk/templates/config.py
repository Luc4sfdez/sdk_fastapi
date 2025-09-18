"""
Template System Configuration

Configuration classes and utilities for the template engine.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import yaml
import json
from enum import Enum

from .exceptions import ConfigurationError


class TemplateCategory(Enum):
    """Template categories for organization."""
    AUTH = "authentication"
    API_GATEWAY = "api_gateway"
    DATA_SERVICE = "data_service"
    EVENT_SERVICE = "event_service"
    MONITORING = "monitoring"
    WORKER_SERVICE = "worker_service"
    WEBSOCKET_SERVICE = "websocket_service"
    CUSTOM = "custom"


class VariableType(Enum):
    """Variable types for template configuration."""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    PATH = "path"
    EMAIL = "email"
    URL = "url"


@dataclass
class TemplateVariable:
    """Template variable definition."""
    name: str
    type: VariableType
    description: str
    default: Optional[Any] = None
    required: bool = True
    choices: Optional[List[Any]] = None
    validation_pattern: Optional[str] = None
    
    def validate(self, value: Any) -> bool:
        """Validate variable value."""
        if self.required and value is None:
            return False
            
        if value is None:
            return True
            
        # Type validation
        if self.type == VariableType.STRING and not isinstance(value, str):
            return False
        elif self.type == VariableType.INTEGER and not isinstance(value, int):
            return False
        elif self.type == VariableType.BOOLEAN and not isinstance(value, bool):
            return False
        elif self.type == VariableType.LIST and not isinstance(value, list):
            return False
        elif self.type == VariableType.DICT and not isinstance(value, dict):
            return False
            
        # Choice validation
        if self.choices and value not in self.choices:
            return False
            
        return True


@dataclass
class TemplateConfig:
    """Template configuration and metadata."""
    id: str
    name: str
    description: str
    category: TemplateCategory
    version: str
    author: str
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    variables: List[TemplateVariable] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    hooks: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'TemplateConfig':
        """Load template configuration from file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
                    
            return cls.from_dict(data)
        except Exception as e:
            raise ConfigurationError(
                config_type="template_config",
                validation_errors=[f"Failed to load config from {config_path}: {str(e)}"]
            )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateConfig':
        """Create template configuration from dictionary."""
        try:
            # Parse variables
            variables = []
            for var_data in data.get('variables', []):
                variable = TemplateVariable(
                    name=var_data['name'],
                    type=VariableType(var_data['type']),
                    description=var_data['description'],
                    default=var_data.get('default'),
                    required=var_data.get('required', True),
                    choices=var_data.get('choices'),
                    validation_pattern=var_data.get('validation_pattern')
                )
                variables.append(variable)
            
            return cls(
                id=data['id'],
                name=data['name'],
                description=data['description'],
                category=TemplateCategory(data['category']),
                version=data['version'],
                author=data['author'],
                license=data.get('license', 'MIT'),
                tags=data.get('tags', []),
                variables=variables,
                dependencies=data.get('dependencies', []),
                hooks=data.get('hooks', {})
            )
        except Exception as e:
            raise ConfigurationError(
                config_type="template_config",
                validation_errors=[f"Invalid template configuration: {str(e)}"]
            )
    
    def validate_variables(self, values: Dict[str, Any]) -> List[str]:
        """Validate variable values against configuration."""
        errors = []
        
        for variable in self.variables:
            value = values.get(variable.name)
            
            if not variable.validate(value):
                if variable.required and value is None:
                    errors.append(f"Required variable '{variable.name}' is missing")
                elif value is not None:
                    errors.append(f"Invalid value for variable '{variable.name}': {value}")
        
        return errors


@dataclass
class ProjectConfig:
    """Project configuration."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    license: str = "MIT"
    python_version: str = "3.8+"
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """Create project configuration from dictionary."""
        return cls(
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0.0'),
            author=data.get('author', ''),
            license=data.get('license', 'MIT'),
            python_version=data.get('python_version', '3.8+'),
            dependencies=data.get('dependencies', []),
            dev_dependencies=data.get('dev_dependencies', []),
            services=data.get('services', [])
        )


@dataclass
class ServiceConfig:
    """Service configuration within a project."""
    name: str
    type: str
    template: str
    port: int = 8000
    database: Optional[str] = None
    message_broker: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceConfig':
        """Create service configuration from dictionary."""
        return cls(
            name=data['name'],
            type=data['type'],
            template=data['template'],
            port=data.get('port', 8000),
            database=data.get('database'),
            message_broker=data.get('message_broker'),
            dependencies=data.get('dependencies', []),
            environment=data.get('environment', {})
        )


@dataclass
class CLIConfig:
    """CLI configuration."""
    template_paths: List[str] = field(default_factory=lambda: ["~/.fastapi-sdk/templates"])
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    auto_update: bool = True
    default_author: str = ""
    default_license: str = "MIT"
    
    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> 'CLIConfig':
        """Load CLI configuration from file."""
        if config_path is None:
            config_path = Path.home() / ".fastapi-sdk" / "config.yaml"
        
        if not config_path.exists():
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            return cls(
                template_paths=data.get('template_paths', ["~/.fastapi-sdk/templates"]),
                cache_enabled=data.get('cache_enabled', True),
                cache_ttl=data.get('cache_ttl', 3600),
                auto_update=data.get('auto_update', True),
                default_author=data.get('default_author', ''),
                default_license=data.get('default_license', 'MIT')
            )
        except Exception as e:
            raise ConfigurationError(
                config_type="cli_config",
                validation_errors=[f"Failed to load CLI config: {str(e)}"]
            )
    
    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """Save CLI configuration to file."""
        if config_path is None:
            config_path = Path.home() / ".fastapi-sdk" / "config.yaml"
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'template_paths': self.template_paths,
            'cache_enabled': self.cache_enabled,
            'cache_ttl': self.cache_ttl,
            'auto_update': self.auto_update,
            'default_author': self.default_author,
            'default_license': self.default_license
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(
                config_type="cli_config",
                validation_errors=[f"Failed to save CLI config: {str(e)}"]
            )
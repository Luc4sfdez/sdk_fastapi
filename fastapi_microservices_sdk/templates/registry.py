"""
Template Registry

Central registry for managing and discovering templates.
"""

from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
import importlib
import pkgutil

from .engine import Template, TemplateLoader
from .config import TemplateCategory, CLIConfig
from .exceptions import TemplateNotFoundError, TemplateValidationError
# Template imports are done locally in _initialize_builtin_templates to avoid circular imports


@dataclass
class TemplateInfo:
    """Template information for registry."""
    id: str
    name: str
    description: str
    category: TemplateCategory
    version: str
    author: str
    tags: List[str] = field(default_factory=list)
    source: str = "builtin"  # builtin, file, plugin
    path: Optional[Path] = None


class TemplateRegistry:
    """Central template registry."""
    
    def __init__(self, config: Optional[CLIConfig] = None):
        import logging
        self._logger = logging.getLogger(__name__)
        self.config = config or CLIConfig()
        self.templates: Dict[str, TemplateInfo] = {}
        self.loader = TemplateLoader(self.config.template_paths)
        self._initialize_builtin_templates()
        self._discover_file_templates()
    
    def _initialize_builtin_templates(self) -> None:
        """Initialize built-in templates."""
        # List of available template modules
        template_modules = [
            "microservice",
            "auth_service", 
            "api_gateway",
            "data_service",
            "notification_service",
            "file_service"
        ]
        
        for module_name in template_modules:
            try:
                # Dynamic import of template module
                module = __import__(f"fastapi_microservices_sdk.templates.builtin_templates.{module_name}", 
                                  fromlist=[module_name])
                
                # Get template class (assumes class name follows pattern)
                class_name = self._module_name_to_class_name(module_name)
                template_class = getattr(module, class_name, None)
                
                if template_class and hasattr(template_class, 'create_template'):
                    try:
                        template = template_class.create_template()
                        self.register_template_info(TemplateInfo(
                            id=template.config.id,
                            name=template.config.name,
                            description=template.config.description,
                            category=template.config.category,
                            version=template.config.version,
                            author=template.config.author,
                            tags=template.config.tags,
                            source="builtin"
                        ))
                        self._logger.debug(f"Registered builtin template: {template.config.name}")
                    except Exception as e:
                        self._logger.warning(f"Failed to create template from {class_name}: {e}")
                else:
                    self._logger.warning(f"Template class {class_name} not found or invalid in {module_name}")
                    
            except ImportError as e:
                self._logger.warning(f"Failed to import builtin template module {module_name}: {e}")
            except Exception as e:
                self._logger.error(f"Unexpected error loading template {module_name}: {e}")
    
    def _module_name_to_class_name(self, module_name: str) -> str:
        """Convert module name to expected class name."""
        # Special mappings for known templates
        special_mappings = {
            "api_gateway": "APIGatewayTemplate",
            "auth_service": "AuthServiceTemplate",
            "data_service": "DataServiceTemplate",
            "file_service": "FileServiceTemplate",
            "notification_service": "NotificationServiceTemplate",
            "microservice": "MicroserviceTemplate"
        }
        
        if module_name in special_mappings:
            return special_mappings[module_name]
        
        # Fallback: Convert snake_case to PascalCase and add Template suffix
        parts = module_name.split('_')
        class_name = ''.join(word.capitalize() for word in parts) + 'Template'
        return class_name
    
    def _discover_file_templates(self) -> None:
        """Discover templates from file system."""
        for search_path in self.loader.search_paths:
            if not search_path.exists():
                continue
            
            for item in search_path.iterdir():
                if item.is_dir() and (item / "template.yaml").exists():
                    try:
                        template = self.loader.load_template(item.name)
                        self.register_template_info(TemplateInfo(
                            id=template.id,
                            name=template.name,
                            description=template.config.description,
                            category=template.config.category,
                            version=template.config.version,
                            author=template.config.author,
                            tags=template.config.tags,
                            source="file",
                            path=item
                        ))
                    except Exception:
                        # Skip invalid templates
                        continue
    
    def register_template_info(self, template_info: TemplateInfo) -> None:
        """Register template information."""
        self.templates[template_info.id] = template_info
    
    def get_template_info(self, template_id: str) -> Optional[TemplateInfo]:
        """Get template information."""
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[TemplateCategory] = None, 
                      tags: Optional[List[str]] = None) -> List[TemplateInfo]:
        """List available templates with optional filtering."""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return sorted(templates, key=lambda t: t.name)
    
    def search_templates(self, query: str) -> List[TemplateInfo]:
        """Search templates by name, description, or tags."""
        query = query.lower()
        results = []
        
        for template in self.templates.values():
            if (query in template.name.lower() or 
                query in template.description.lower() or
                any(query in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return sorted(results, key=lambda t: t.name)
    
    def get_template(self, template_id: str) -> Template:
        """Get template instance."""
        template_info = self.get_template_info(template_id)
        if not template_info:
            raise TemplateNotFoundError(template_id)
        
        if template_info.source == "builtin":
            return self._get_builtin_template(template_id)
        elif template_info.source == "file":
            return self.loader.load_template(template_id)
        else:
            raise TemplateNotFoundError(template_id)
    
    def _get_builtin_template(self, template_id: str) -> Template:
        """Get built-in template."""
        if template_id == "microservice":
            return MicroserviceTemplate.create_template()
        else:
            raise TemplateNotFoundError(template_id)
    
    def get_categories(self) -> List[TemplateCategory]:
        """Get all available template categories."""
        categories = set()
        for template in self.templates.values():
            categories.add(template.category)
        return sorted(categories, key=lambda c: c.value)
    
    def get_tags(self) -> List[str]:
        """Get all available template tags."""
        tags = set()
        for template in self.templates.values():
            tags.update(template.tags)
        return sorted(tags)
    
    def validate_template(self, template_id: str) -> List[str]:
        """Validate template and return any errors."""
        try:
            template = self.get_template(template_id)
            # Add validation logic here
            return []
        except Exception as e:
            return [str(e)]
    
    def refresh(self) -> None:
        """Refresh template registry."""
        self.templates.clear()
        self._initialize_builtin_templates()
        self._discover_file_templates()


class TemplateManager:
    """High-level template management."""
    
    def __init__(self, config: Optional[CLIConfig] = None):
        self.config = config or CLIConfig()
        self.registry = TemplateRegistry(config)
    
    def list_templates(self, category: Optional[str] = None, 
                      tags: Optional[List[str]] = None) -> List[TemplateInfo]:
        """List available templates."""
        category_enum = None
        if category:
            try:
                category_enum = TemplateCategory(category)
            except ValueError:
                pass
        
        return self.registry.list_templates(category_enum, tags)
    
    def search_templates(self, query: str) -> List[TemplateInfo]:
        """Search templates."""
        return self.registry.search_templates(query)
    
    def get_template(self, template_id: str) -> Template:
        """Get template."""
        return self.registry.get_template(template_id)
    
    def get_template_info(self, template_id: str) -> Optional[TemplateInfo]:
        """Get template information."""
        return self.registry.get_template_info(template_id)
    
    def validate_template(self, template_id: str) -> List[str]:
        """Validate template."""
        return self.registry.validate_template(template_id)
    
    def get_categories(self) -> List[str]:
        """Get available categories."""
        return [cat.value for cat in self.registry.get_categories()]
    
    def get_tags(self) -> List[str]:
        """Get available tags."""
        return self.registry.get_tags()
    
    def install_template(self, source: str, template_id: Optional[str] = None) -> str:
        """Install template from source (URL, path, etc.)."""
        # Implementation for installing templates from external sources
        # This could support Git repositories, ZIP files, etc.
        raise NotImplementedError("Template installation not yet implemented")
    
    def uninstall_template(self, template_id: str) -> bool:
        """Uninstall template."""
        template_info = self.registry.get_template_info(template_id)
        if not template_info:
            return False
        
        if template_info.source == "builtin":
            raise ValueError("Cannot uninstall built-in templates")
        
        if template_info.path and template_info.path.exists():
            import shutil
            shutil.rmtree(template_info.path)
            del self.registry.templates[template_id]
            return True
        
        return False
    
    def refresh_registry(self) -> None:
        """Refresh template registry."""
        self.registry.refresh()
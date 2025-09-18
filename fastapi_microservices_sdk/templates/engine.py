"""
Template Engine Core

Core template processing engine with loading, rendering, and caching capabilities.
"""

from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import re

from jinja2 import Environment, FileSystemLoader, Template as Jinja2Template
from jinja2.exceptions import TemplateError as Jinja2TemplateError

from .config import TemplateConfig, TemplateVariable, CLIConfig
from .exceptions import (
    TemplateError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateRenderError
)


@dataclass
class TemplateFile:
    """Represents a file within a template."""
    path: str
    content: str
    is_binary: bool = False
    executable: bool = False
    
    def render(self, variables: Dict[str, Any]) -> str:
        """Render file content with variables."""
        if self.is_binary:
            return self.content
        
        try:
            template = Jinja2Template(self.content)
            return template.render(**variables)
        except Jinja2TemplateError as e:
            raise TemplateRenderError(
                template_id=self.path,
                render_error=str(e),
                context=variables
            )


@dataclass
class Template:
    """Template definition and metadata."""
    config: TemplateConfig
    files: List[TemplateFile] = field(default_factory=list)
    base_path: Optional[Path] = None
    
    @property
    def id(self) -> str:
        """Template ID."""
        return self.config.id
    
    @property
    def name(self) -> str:
        """Template name."""
        return self.config.name
    
    @property
    def version(self) -> str:
        """Template version."""
        return self.config.version
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate variables against template configuration."""
        return self.config.validate_variables(variables)
    
    def get_variable_defaults(self) -> Dict[str, Any]:
        """Get default values for template variables."""
        defaults = {}
        for variable in self.config.variables:
            if variable.default is not None:
                defaults[variable.name] = variable.default
        return defaults


@dataclass
class RenderedTemplate:
    """Result of template rendering."""
    template: Template
    variables: Dict[str, Any]
    files: List[TemplateFile]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def write_to_directory(self, output_path: Path, overwrite: bool = False) -> None:
        """Write rendered template to directory."""
        output_path = Path(output_path)
        
        if output_path.exists() and not overwrite:
            raise TemplateError(f"Output directory {output_path} already exists")
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write files
        for file in self.files:
            file_path = output_path / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file.is_binary:
                with open(file_path, 'wb') as f:
                    f.write(file.content.encode('utf-8'))
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file.content)
            
            # Set executable permission if needed
            if file.executable:
                os.chmod(file_path, 0o755)


class TemplateLoader:
    """Template loader for loading templates from various sources."""
    
    def __init__(self, search_paths: List[str]):
        self.search_paths = [Path(p).expanduser() for p in search_paths]
    
    def load_template(self, template_id: str) -> Template:
        """Load template by ID."""
        for search_path in self.search_paths:
            template_path = search_path / template_id
            if template_path.exists() and template_path.is_dir():
                return self._load_from_directory(template_path)
        
        raise TemplateNotFoundError(
            template_id=template_id,
            search_paths=[str(p) for p in self.search_paths]
        )
    
    def list_templates(self) -> List[str]:
        """List available template IDs."""
        templates = set()
        
        for search_path in self.search_paths:
            if not search_path.exists():
                continue
            
            for item in search_path.iterdir():
                if item.is_dir() and (item / "template.yaml").exists():
                    templates.add(item.name)
        
        return sorted(templates)
    
    def _load_from_directory(self, template_path: Path) -> Template:
        """Load template from directory."""
        # Load configuration
        config_path = template_path / "template.yaml"
        if not config_path.exists():
            config_path = template_path / "template.json"
        
        if not config_path.exists():
            raise TemplateValidationError(
                template_id=template_path.name,
                validation_errors=["No template.yaml or template.json found"]
            )
        
        config = TemplateConfig.from_file(config_path)
        
        # Load template files
        files = []
        files_dir = template_path / "files"
        
        if files_dir.exists():
            for file_path in self._walk_directory(files_dir):
                relative_path = file_path.relative_to(files_dir)
                
                # Check if file is binary
                is_binary = self._is_binary_file(file_path)
                
                if is_binary:
                    with open(file_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                # Check if file should be executable
                executable = os.access(file_path, os.X_OK)
                
                template_file = TemplateFile(
                    path=str(relative_path),
                    content=content,
                    is_binary=is_binary,
                    executable=executable
                )
                files.append(template_file)
        
        return Template(
            config=config,
            files=files,
            base_path=template_path
        )
    
    def _walk_directory(self, directory: Path):
        """Recursively walk directory and yield file paths."""
        for item in directory.rglob("*"):
            if item.is_file():
                yield item
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return True


class TemplateCache:
    """Template caching system for performance optimization."""
    
    def __init__(self, cache_dir: Optional[Path] = None, ttl: int = 3600):
        self.cache_dir = cache_dir or Path.home() / ".fastapi-sdk" / "cache"
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, template_id: str) -> Optional[Template]:
        """Get template from cache."""
        cache_file = self.cache_dir / f"{template_id}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(cache_data['cached_at'])
            if datetime.now() - cached_time > timedelta(seconds=self.ttl):
                cache_file.unlink()
                return None
            
            # Reconstruct template
            config = TemplateConfig.from_dict(cache_data['config'])
            files = [
                TemplateFile(
                    path=f['path'],
                    content=f['content'],
                    is_binary=f['is_binary'],
                    executable=f['executable']
                )
                for f in cache_data['files']
            ]
            
            return Template(config=config, files=files)
            
        except Exception:
            # Remove corrupted cache file
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def put(self, template: Template) -> None:
        """Put template in cache."""
        cache_file = self.cache_dir / f"{template.id}.json"
        
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'config': {
                'id': template.config.id,
                'name': template.config.name,
                'description': template.config.description,
                'category': template.config.category.value,
                'version': template.config.version,
                'author': template.config.author,
                'license': template.config.license,
                'tags': template.config.tags,
                'dependencies': template.config.dependencies,
                'hooks': template.config.hooks,
                'variables': [
                    {
                        'name': var.name,
                        'type': var.type.value,
                        'description': var.description,
                        'default': var.default,
                        'required': var.required,
                        'choices': var.choices,
                        'validation_pattern': var.validation_pattern
                    }
                    for var in template.config.variables
                ]
            },
            'files': [
                {
                    'path': f.path,
                    'content': f.content,
                    'is_binary': f.is_binary,
                    'executable': f.executable
                }
                for f in template.files
            ]
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            # Ignore cache write errors
            pass
    
    def clear(self) -> None:
        """Clear all cached templates."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


class TemplateValidator:
    """Template validation system."""
    
    def validate_template(self, template: Template) -> List[str]:
        """Validate template structure and configuration."""
        errors = []
        
        # Validate configuration
        if not template.config.id:
            errors.append("Template ID is required")
        
        if not template.config.name:
            errors.append("Template name is required")
        
        if not template.config.version:
            errors.append("Template version is required")
        
        # Validate files
        if not template.files:
            errors.append("Template must contain at least one file")
        
        # Validate variable references in files
        for file in template.files:
            if not file.is_binary:
                file_errors = self._validate_file_variables(file, template.config.variables)
                errors.extend(file_errors)
        
        return errors
    
    def _validate_file_variables(self, file: TemplateFile, variables: List[TemplateVariable]) -> List[str]:
        """Validate variable references in file content."""
        errors = []
        variable_names = {var.name for var in variables}
        
        # Find Jinja2 variable references
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        matches = re.findall(pattern, file.content)
        
        for match in matches:
            if match not in variable_names:
                errors.append(f"Undefined variable '{match}' in file '{file.path}'")
        
        return errors


class TemplateRenderer:
    """Template rendering with variable substitution."""
    
    def __init__(self):
        self.jinja_env = Environment(
            loader=FileSystemLoader('.'),
            autoescape=False,
            keep_trailing_newline=True
        )
    
    def render_template(self, template: Template, variables: Dict[str, Any]) -> RenderedTemplate:
        """Render template with variables."""
        # Validate variables
        validation_errors = template.validate_variables(variables)
        if validation_errors:
            raise TemplateValidationError(
                template_id=template.id,
                validation_errors=validation_errors
            )
        
        # Merge with defaults
        merged_variables = template.get_variable_defaults()
        merged_variables.update(variables)
        
        # Render files
        rendered_files = []
        for file in template.files:
            try:
                rendered_content = file.render(merged_variables)
                rendered_file = TemplateFile(
                    path=file.path,
                    content=rendered_content,
                    is_binary=file.is_binary,
                    executable=file.executable
                )
                rendered_files.append(rendered_file)
            except Exception as e:
                raise TemplateRenderError(
                    template_id=template.id,
                    render_error=f"Error rendering file '{file.path}': {str(e)}",
                    context=merged_variables
                )
        
        return RenderedTemplate(
            template=template,
            variables=merged_variables,
            files=rendered_files,
            metadata={
                'rendered_at': datetime.now().isoformat(),
                'template_version': template.version
            }
        )


class TemplateEngine:
    """Core template processing engine."""
    
    def __init__(self, config: Optional[CLIConfig] = None):
        self.config = config or CLIConfig()
        self.loader = TemplateLoader(self.config.template_paths)
        self.cache = TemplateCache() if self.config.cache_enabled else None
        self.validator = TemplateValidator()
        self.renderer = TemplateRenderer()
    
    def get_template(self, template_id: str) -> Template:
        """Get template by ID."""
        # Try cache first
        if self.cache:
            template = self.cache.get(template_id)
            if template:
                return template
        
        # Load from disk
        template = self.loader.load_template(template_id)
        
        # Validate template
        validation_errors = self.validator.validate_template(template)
        if validation_errors:
            raise TemplateValidationError(
                template_id=template_id,
                validation_errors=validation_errors
            )
        
        # Cache template
        if self.cache:
            self.cache.put(template)
        
        return template
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        return self.loader.list_templates()
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> RenderedTemplate:
        """Render template with variables."""
        template = self.get_template(template_id)
        return self.renderer.render_template(template, variables)
    
    def generate_project(self, template_id: str, variables: Dict[str, Any], output_path: Path, overwrite: bool = False) -> RenderedTemplate:
        """Generate project from template."""
        rendered = self.render_template(template_id, variables)
        rendered.write_to_directory(output_path, overwrite=overwrite)
        return rendered
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        if self.cache:
            self.cache.clear()
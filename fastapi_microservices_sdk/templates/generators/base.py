"""
Base classes for code generators

This module provides the foundation classes for all code generators
in the FastAPI Microservices SDK.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class GeneratedFile:
    """Represents a generated file"""
    path: Path
    content: str
    encoding: str = "utf-8"
    executable: bool = False
    
    def write_to_disk(self, base_path: Path) -> None:
        """Write the file to disk"""
        full_path = base_path / self.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding=self.encoding) as f:
            f.write(self.content)
        
        if self.executable:
            import stat
            full_path.chmod(full_path.stat().st_mode | stat.S_IEXEC)


@dataclass
class GenerationResult:
    """Result of a code generation operation"""
    files: List[GeneratedFile]
    success: bool
    errors: List[str]
    warnings: List[str]
    
    def __post_init__(self):
        if not self.files and self.success:
            self.success = False
            if not self.errors:
                self.errors = ["No files were generated"]
    
    @property
    def file_count(self) -> int:
        """Number of generated files"""
        return len(self.files)
    
    def write_all(self, base_path: Path) -> None:
        """Write all generated files to disk"""
        for file in self.files:
            try:
                file.write_to_disk(base_path)
                logger.info(f"Generated file: {file.path}")
            except Exception as e:
                logger.error(f"Failed to write file {file.path}: {e}")
                self.errors.append(f"Failed to write {file.path}: {e}")
                self.success = False


class CodeGenerator(ABC):
    """Base class for all code generators"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def generate(self, config: Dict[str, Any], output_path: Path) -> GenerationResult:
        """Generate code based on configuration"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate the configuration and return any errors"""
        pass
    
    def get_template_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract template variables from configuration"""
        return config.copy()
    
    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables"""
        try:
            from jinja2 import Template
            template = Template(template_content)
            return template.render(**variables)
        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            raise
    
    def create_file(self, path: Union[str, Path], content: str, **kwargs) -> GeneratedFile:
        """Create a GeneratedFile instance"""
        return GeneratedFile(
            path=Path(path),
            content=content,
            **kwargs
        )
    
    def log_generation_start(self, config: Dict[str, Any]) -> None:
        """Log the start of generation"""
        self.logger.info(f"Starting {self.name} generation")
        self.logger.debug(f"Configuration: {config}")
    
    def log_generation_complete(self, result: GenerationResult) -> None:
        """Log the completion of generation"""
        if result.success:
            self.logger.info(f"Successfully generated {result.file_count} files")
        else:
            self.logger.error(f"Generation failed with {len(result.errors)} errors")
            for error in result.errors:
                self.logger.error(f"  - {error}")
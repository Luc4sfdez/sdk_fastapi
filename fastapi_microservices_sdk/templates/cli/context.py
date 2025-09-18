"""
CLI Context Management

Context management for CLI operations with configuration and state.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import os

from ..config import CLIConfig
from ..engine import TemplateEngine
from ..manager import ProjectManager, ServiceManager


@dataclass
class CLIContext:
    """CLI execution context with configuration and services."""
    
    config: CLIConfig
    template_engine: TemplateEngine
    project_manager: ProjectManager
    service_manager: ServiceManager
    current_directory: Path = field(default_factory=lambda: Path.cwd())
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    variables: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(cls, config_path: Optional[Path] = None, **kwargs) -> 'CLIContext':
        """Create CLI context with default configuration."""
        # Load configuration
        config = CLIConfig.load_from_file(config_path)
        
        # Override config with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Initialize template engine
        template_engine = TemplateEngine(config)
        
        # Initialize managers
        project_manager = ProjectManager(template_engine)
        service_manager = ServiceManager(template_engine)
        
        return cls(
            config=config,
            template_engine=template_engine,
            project_manager=project_manager,
            service_manager=service_manager,
            current_directory=Path.cwd(),
            verbose=kwargs.get('verbose', False),
            quiet=kwargs.get('quiet', False),
            dry_run=kwargs.get('dry_run', False)
        )
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set context variable."""
        self.variables[name] = value
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get context variable."""
        return self.variables.get(name, default)
    
    def update_variables(self, variables: Dict[str, Any]) -> None:
        """Update context variables."""
        self.variables.update(variables)
    
    def get_project_path(self) -> Optional[Path]:
        """Get current project path if in a project directory."""
        current = self.current_directory
        
        # Look for project metadata file
        while current != current.parent:
            project_file = current / ".fastapi-sdk" / "project.yaml"
            if project_file.exists():
                return current
            current = current.parent
        
        return None
    
    def is_in_project(self) -> bool:
        """Check if current directory is within a project."""
        return self.get_project_path() is not None
    
    def load_project(self):
        """Load current project if available."""
        project_path = self.get_project_path()
        if project_path:
            return self.project_manager.load_project(project_path)
        return None
    
    def print_info(self, message: str) -> None:
        """Print info message if not quiet."""
        if not self.quiet:
            print(f"ℹ️  {message}")
    
    def print_success(self, message: str) -> None:
        """Print success message if not quiet."""
        if not self.quiet:
            print(f"✅ {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message if not quiet."""
        if not self.quiet:
            print(f"⚠️  {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        print(f"❌ {message}")
    
    def print_verbose(self, message: str) -> None:
        """Print verbose message if verbose mode is enabled."""
        if self.verbose and not self.quiet:
            print(f"🔍 {message}")
    
    def confirm(self, message: str, default: bool = False) -> bool:
        """Ask for user confirmation."""
        if self.quiet:
            return default
        
        suffix = " [Y/n]" if default else " [y/N]"
        response = input(f"❓ {message}{suffix}: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
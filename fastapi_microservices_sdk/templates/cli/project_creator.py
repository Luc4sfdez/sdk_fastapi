"""
Project Creation CLI for FastAPI Microservices SDK

This module provides interactive project creation with wizards, templates,
and automated setup for FastAPI microservices projects.
"""

import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import yaml

from .framework import CLIFramework, Command, CommandResult
from .wizard import InteractiveWizard, WizardStep
from .context import CLIContext
from ..manager import TemplateManager
from ..registry import TemplateRegistry
from ..exceptions import TemplateError


class ProjectCreator:
    """Main project creator class for CLI integration."""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.template_registry = TemplateRegistry()
    
    def create_project(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a project with given configuration."""
        try:
            # Validate configuration
            errors = self.validate_config(config)
            if errors:
                return {
                    "success": False,
                    "errors": errors
                }
            
            # Create project structure
            project_name = config.get("name", "new_project")
            output_dir = Path.cwd() / project_name
            
            # Generate basic project files
            self._create_project_structure(output_dir, config)
            
            return {
                "success": True,
                "project_name": project_name,
                "output_dir": str(output_dir)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate project configuration."""
        errors = []
        
        # Check required fields
        if not config.get("name"):
            errors.append("Project name is required")
        
        if not config.get("description"):
            errors.append("Project description is required")
        
        # Validate project name
        name = config.get("name", "")
        if name and not self._validate_project_name(name):
            errors.append("Invalid project name. Use alphanumeric characters, hyphens, and underscores only")
        
        return errors
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates."""
        try:
            templates = self.template_registry.list_templates()
            return [t.name for t in templates]
        except Exception:
            return ["microservice", "api_gateway", "auth_service", "data_service"]
    
    def _validate_project_name(self, name: str) -> bool:
        """Validate project name."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))
    
    def _validate_version(self, version: str) -> bool:
        """Validate semantic version."""
        import re
        return bool(re.match(r'^\d+\.\d+\.\d+$', version))
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
    
    def _create_project_structure(self, output_dir: Path, config: Dict[str, Any]) -> None:
        """Create basic project structure."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create basic files
        self._create_readme(output_dir, config)
        self._create_requirements(output_dir)
        self._create_gitignore(output_dir)
        
        # Create app structure
        app_dir = output_dir / "app"
        app_dir.mkdir(exist_ok=True)
        
        # Create main.py
        main_content = f'''"""
{config.get("description", "FastAPI microservice")}
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="{config.get("name", "FastAPI Service")}",
    description="{config.get("description", "A FastAPI microservice")}",
    version="{config.get("version", "0.1.0")}"
)

@app.get("/")
async def root():
    return {{"message": "Hello from {config.get("name", "FastAPI Service")}"}}

@app.get("/health")
async def health():
    return {{"status": "healthy"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        (app_dir / "main.py").write_text(main_content, encoding="utf-8")
        (app_dir / "__init__.py").write_text("", encoding="utf-8")
    
    def _create_readme(self, output_dir: Path, config: Dict[str, Any]) -> None:
        """Create README.md file."""
        readme_content = f'''# {config.get("name", "FastAPI Project")}

{config.get("description", "A FastAPI microservices project")}

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the service:
   ```bash
   python app/main.py
   ```

3. Visit http://localhost:8000/docs for API documentation

## Project Structure

- `app/` - Application code
- `tests/` - Test files
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation

## Development

This project was created using the FastAPI Microservices SDK.

Version: {config.get("version", "0.1.0")}
Author: {config.get("author", {}).get("name", "Developer")}
'''
        
        (output_dir / "README.md").write_text(readme_content, encoding="utf-8")
    
    def _create_requirements(self, output_dir: Path) -> None:
        """Create requirements.txt file."""
        requirements_content = '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
'''
        
        (output_dir / "requirements.txt").write_text(requirements_content, encoding="utf-8")
    
    def _create_gitignore(self, output_dir: Path) -> None:
        """Create .gitignore file."""
        gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite3
'''
        
        (output_dir / ".gitignore").write_text(gitignore_content, encoding="utf-8")


class CreateProjectCommand(Command):
    """Command to create a new project."""
    
    def __init__(self):
        super().__init__(
            name="create",
            description="Create a new FastAPI microservices project"
        )
    
    def _setup_arguments(self) -> None:
        """Setup command arguments."""
        self.add_argument(
            "name",
            help="Project name"
        )
        
        self.add_option(
            "template",
            help="Template to use",
            default="microservice"
        )
        
        self.add_option(
            "output-dir",
            help="Output directory",
            default="."
        )
    
    def execute(self, context: CLIContext, args) -> CommandResult:
        """Execute the create project command."""
        try:
            creator = ProjectCreator()
            
            # Prepare configuration
            config = {
                "name": args.name,
                "description": f"A FastAPI microservice: {args.name}",
                "version": "0.1.0",
                "author": {
                    "name": "Developer",
                    "email": "developer@example.com"
                }
            }
            
            # Create project
            result = creator.create_project(config)
            
            if result["success"]:
                return CommandResult(
                    success=True,
                    message=f"Project '{args.name}' created successfully"
                )
            else:
                return CommandResult(
                    success=False,
                    message="Failed to create project",
                    data=result
                )
        
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error creating project: {str(e)}"
            )


# Main entry point for testing
if __name__ == "__main__":
    creator = ProjectCreator()
    
    # Test configuration
    test_config = {
        "name": "test_project",
        "description": "Test FastAPI project",
        "version": "0.1.0",
        "author": {
            "name": "Test Developer",
            "email": "test@example.com"
        }
    }
    
    result = creator.create_project(test_config)
    print(f"Result: {result}")
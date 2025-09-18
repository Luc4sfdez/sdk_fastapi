"""
Template Engine Example

Demonstrates the usage of the FastAPI Microservices SDK Template Engine.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

from fastapi_microservices_sdk.templates import (
    TemplateEngine,
    CRUDGenerator,
    APIGenerator,
    ProjectManager,
    ServiceManager
)
from fastapi_microservices_sdk.templates.config import CLIConfig


async def main():
    """Main example function."""
    print("🚀 FastAPI Microservices SDK - Template Engine Example")
    print("=" * 60)
    
    # Create temporary directory for examples
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Example 1: CRUD Generator
        print("\n📋 Example 1: CRUD Generator")
        print("-" * 30)
        
        crud_generator = CRUDGenerator()
        
        # Define a User model schema
        user_schema = {
            "name": "User",
            "fields": [
                {
                    "name": "email",
                    "type": "string",
                    "description": "User email address",
                    "required": True
                },
                {
                    "name": "full_name",
                    "type": "string", 
                    "description": "User full name",
                    "required": True
                },
                {
                    "name": "age",
                    "type": "integer",
                    "description": "User age",
                    "required": False,
                    "default": 18
                },
                {
                    "name": "is_active",
                    "type": "boolean",
                    "description": "User active status",
                    "required": False,
                    "default": True
                }
            ]
        }
        
        # Generate CRUD code
        crud_result = crud_generator.generate(user_schema, {
            "generate_tests": True,
            "database": "postgresql"
        })
        
        print(f"✅ Generated {len(crud_result.files)} files for User CRUD:")
        for file in crud_result.files:
            print(f"   - {file.path}")
        
        # Write generated files
        crud_output = temp_path / "crud_example"
        crud_result.write_to_directory(crud_output)
        print(f"📁 Files written to: {crud_output}")
        
        # Show sample generated model
        model_file = crud_output / "models" / "user.py"
        if model_file.exists():
            print(f"\n📄 Sample generated model (first 20 lines):")
            lines = model_file.read_text().split('\n')[:20]
            for i, line in enumerate(lines, 1):
                print(f"   {i:2d}: {line}")
            if len(lines) >= 20:
                print("   ...")
        
        # Example 2: API Generator
        print("\n\n🔌 Example 2: API Generator")
        print("-" * 30)
        
        api_generator = APIGenerator()
        
        # Define a simple OpenAPI-like schema
        api_schema = {
            "info": {
                "title": "User Management API",
                "version": "1.0.0"
            },
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "list_users",
                        "summary": "List all users",
                        "description": "Retrieve a list of all users"
                    },
                    "post": {
                        "operationId": "create_user",
                        "summary": "Create new user",
                        "description": "Create a new user account"
                    }
                },
                "/users/{user_id}": {
                    "get": {
                        "operationId": "get_user",
                        "summary": "Get user by ID",
                        "description": "Retrieve a specific user by ID"
                    },
                    "put": {
                        "operationId": "update_user",
                        "summary": "Update user",
                        "description": "Update an existing user"
                    },
                    "delete": {
                        "operationId": "delete_user",
                        "summary": "Delete user",
                        "description": "Delete a user account"
                    }
                }
            }
        }
        
        # Generate API code
        api_result = api_generator.generate(api_schema)
        
        print(f"✅ Generated {len(api_result.files)} files for User API:")
        for file in api_result.files:
            print(f"   - {file.path}")
        
        # Write generated files
        api_output = temp_path / "api_example"
        api_result.write_to_directory(api_output)
        print(f"📁 Files written to: {api_output}")
        
        # Example 3: Template Engine with Custom Template
        print("\n\n🎨 Example 3: Custom Template Creation")
        print("-" * 40)
        
        # Create a simple custom template
        custom_template_dir = temp_path / "templates" / "simple-service"
        custom_template_dir.mkdir(parents=True)
        
        # Create template configuration
        template_config = """
id: simple-service
name: Simple Service Template
description: A simple FastAPI service template
category: custom
version: 1.0.0
author: SDK Example
variables:
  - name: service_name
    type: string
    description: Name of the service
    required: true
  - name: port
    type: integer
    description: Service port
    default: 8000
    required: false
  - name: description
    type: string
    description: Service description
    default: "A simple FastAPI service"
    required: false
"""
        (custom_template_dir / "template.yaml").write_text(template_config)
        
        # Create template files
        files_dir = custom_template_dir / "files"
        files_dir.mkdir()
        
        # Main application file
        main_py = '''"""
{{ service_name }} Service

{{ description }}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{{ service_name }}",
    description="{{ description }}",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to {{ service_name }}!"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "{{ service_name }}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={{ port }})
'''
        (files_dir / "main.py").write_text(main_py)
        
        # Requirements file
        requirements_txt = '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
'''
        (files_dir / "requirements.txt").write_text(requirements_txt)
        
        # README file
        readme_md = '''# {{ service_name }}

{{ description }}

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

The service will be available at http://localhost:{{ port }}

## API Documentation

- Swagger UI: http://localhost:{{ port }}/docs
- ReDoc: http://localhost:{{ port }}/redoc
'''
        (files_dir / "README.md").write_text(readme_md)
        
        print("✅ Created custom template: simple-service")
        
        # Use the template engine
        config = CLIConfig(
            template_paths=[str(temp_path / "templates")],
            cache_enabled=False
        )
        
        engine = TemplateEngine(config)
        
        # List available templates
        templates = engine.list_templates()
        print(f"📋 Available templates: {templates}")
        
        # Generate project from custom template
        project_variables = {
            "service_name": "UserService",
            "port": 8001,
            "description": "A user management microservice"
        }
        
        project_output = temp_path / "generated_service"
        result = engine.generate_project(
            template_id="simple-service",
            variables=project_variables,
            output_path=project_output
        )
        
        print(f"✅ Generated project with {len(result.files)} files")
        print(f"📁 Project created at: {project_output}")
        
        # Show generated main.py
        main_file = project_output / "main.py"
        if main_file.exists():
            print(f"\n📄 Generated main.py:")
            content = main_file.read_text()
            lines = content.split('\n')[:25]
            for i, line in enumerate(lines, 1):
                print(f"   {i:2d}: {line}")
            if len(content.split('\n')) > 25:
                print("   ...")
        
        # Example 4: Project and Service Management
        print("\n\n🏗️ Example 4: Project Management")
        print("-" * 35)
        
        # Initialize managers
        project_manager = ProjectManager(engine)
        service_manager = ServiceManager(engine)
        
        # Create a new project
        project_path = temp_path / "my_microservices_project"
        
        try:
            project = project_manager.create_project(
                name="MyMicroservicesProject",
                template_id="simple-service",
                variables={
                    "service_name": "MainService",
                    "port": 8000,
                    "description": "Main microservices project"
                },
                output_path=project_path
            )
            
            print(f"✅ Created project: {project.name}")
            print(f"📁 Project path: {project.path}")
            
            # Add a service to the project
            user_service = service_manager.create_service(
                project=project,
                name="user-service",
                template_id="simple-service",
                variables={
                    "service_name": "UserService",
                    "port": 8001,
                    "description": "User management service"
                }
            )
            
            print(f"✅ Added service: {user_service.name}")
            
            # Add another service
            auth_service = service_manager.create_service(
                project=project,
                name="auth-service", 
                template_id="simple-service",
                variables={
                    "service_name": "AuthService",
                    "port": 8002,
                    "description": "Authentication service"
                }
            )
            
            print(f"✅ Added service: {auth_service.name}")
            
            # Show project structure
            print(f"\n📊 Project Structure:")
            print(f"   Project: {project.name}")
            print(f"   Services: {len(project.services)}")
            for service in project.services:
                print(f"     - {service.name} (port: {service.config.port})")
            
            # Validate project
            validation_errors = project_manager.validate_project(project)
            if validation_errors:
                print(f"⚠️  Validation errors: {validation_errors}")
            else:
                print("✅ Project validation passed")
            
            # Save project metadata
            project_manager.save_project(project)
            print("💾 Project metadata saved")
            
        except Exception as e:
            print(f"❌ Project management error: {e}")
        
        print("\n🎉 Template Engine examples completed!")
        print("\nKey Features Demonstrated:")
        print("✅ CRUD code generation from model schemas")
        print("✅ API generation from OpenAPI specifications")
        print("✅ Custom template creation and usage")
        print("✅ Project and service management")
        print("✅ Template validation and error handling")
        print("✅ File generation and directory management")
        
        print(f"\n📁 All examples generated in: {temp_path}")
        print("Note: Files are in temporary directory and will be cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
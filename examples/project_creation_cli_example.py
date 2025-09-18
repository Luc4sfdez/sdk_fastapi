"""
Example usage of Project Creation CLI

This example demonstrates how to use the Project Creation CLI to generate
complete FastAPI microservices projects with interactive wizards.
"""

import asyncio
from pathlib import Path
from fastapi_microservices_sdk.templates.cli.project_creator import (
    ProjectCreatorCLI,
    ProjectCreationWizard,
    CreateProjectCommand,
    ListTemplatesCommand,
    ValidateProjectCommand
)
from fastapi_microservices_sdk.templates.cli.context import CLIContext


async def main():
    """Main example function"""
    
    print("🎯 Project Creation CLI Example")
    print("=" * 50)
    
    # Initialize CLI
    cli = ProjectCreatorCLI()
    
    # Example 1: List available templates
    print("\n📋 Example 1: List Available Templates")
    print("-" * 40)
    
    try:
        # Simulate command line arguments for listing templates
        context = CLIContext()
        context.args = {"format": "table"}
        
        list_command = ListTemplatesCommand()
        result = await list_command.execute(context)
        
        if result.success:
            print("✅ Templates listed successfully")
        else:
            print(f"❌ Failed to list templates: {result.message}")
    
    except Exception as e:
        print(f"❌ Error listing templates: {e}")
    
    # Example 2: Create project in non-interactive mode
    print("\n🚀 Example 2: Create Project (Non-Interactive)")
    print("-" * 40)
    
    try:
        # Simulate command line arguments for project creation
        context = CLIContext()
        context.args = {
            "name": "example_microservice",
            "template": "microservice",
            "output_dir": "./generated_projects",
            "no_interactive": True
        }
        
        create_command = CreateProjectCommand()
        result = await create_command.execute(context)
        
        if result.success:
            print("✅ Project created successfully")
            print(f"📍 Location: {result.data.get('output_dir')}")
        else:
            print(f"❌ Failed to create project: {result.message}")
    
    except Exception as e:
        print(f"❌ Error creating project: {e}")
    
    # Example 3: Validate existing project
    print("\n🔍 Example 3: Validate Project")
    print("-" * 40)
    
    try:
        # Create a test project directory for validation
        test_project_dir = Path("./test_project")
        test_project_dir.mkdir(exist_ok=True)
        
        # Create some basic files
        app_dir = test_project_dir / "app"
        app_dir.mkdir(exist_ok=True)
        
        # Create main.py
        main_content = '''"""
Main FastAPI application
"""

from fastapi import FastAPI

app = FastAPI(
    title="Test Microservice",
    description="A test microservice",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
        
        (app_dir / "main.py").write_text(main_content)
        (app_dir / "__init__.py").write_text('"""App module"""')
        
        # Create requirements.txt
        requirements_content = '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
'''
        (test_project_dir / "requirements.txt").write_text(requirements_content)
        
        # Validate the project
        context = CLIContext()
        context.args = {"path": str(test_project_dir), "fix": True}
        
        validate_command = ValidateProjectCommand()
        result = await validate_command.execute(context)
        
        if result.success:
            print("✅ Project validation passed")
        else:
            print(f"⚠️ Project validation found issues: {result.message}")
            issues = result.data.get("issues", [])
            for issue in issues:
                print(f"  - {issue}")
    
    except Exception as e:
        print(f"❌ Error validating project: {e}")
    
    # Example 4: Interactive wizard simulation
    print("\n🧙 Example 4: Interactive Wizard Simulation")
    print("-" * 40)
    
    try:
        # This would normally be interactive, but we'll show the structure
        wizard = ProjectCreationWizard()
        
        print("Interactive wizard would collect:")
        print("1. 📋 Project Information:")
        print("   - Project name")
        print("   - Description")
        print("   - Version")
        print("   - Author details")
        print("   - License")
        
        print("\\n2. 🎯 Template Selection:")
        print("   - Available templates")
        print("   - Template details")
        
        print("\\n3. ⚙️ Project Configuration:")
        print("   - Required variables")
        print("   - Optional settings")
        
        print("\\n4. 🔧 Additional Services:")
        print("   - Auth Service")
        print("   - API Gateway")
        print("   - Data Service")
        print("   - Event Service")
        print("   - Monitoring Service")
        
        print("\\n5. 🚀 Deployment Configuration:")
        print("   - Docker setup")
        print("   - Kubernetes manifests")
        print("   - CI/CD pipelines")
        print("   - Environment configs")
        
        print("\\n6. 🏗️ Project Generation:")
        print("   - File generation")
        print("   - Git initialization")
        print("   - Next steps")
        
        print("\\n✅ Wizard structure demonstrated")
    
    except Exception as e:
        print(f"❌ Error with wizard: {e}")


def demonstrate_cli_features():
    """Demonstrate CLI features"""
    
    print("\\n🎯 Project Creation CLI Features:")
    print("\\n📋 Core Commands:")
    print("  ✅ create - Create new projects with interactive wizard")
    print("  ✅ list-templates - List available project templates")
    print("  ✅ validate - Validate existing project structure")
    
    print("\\n🔧 Supported Templates:")
    print("  📦 microservice - Basic FastAPI microservice")
    print("  🔐 auth_service - Authentication service with JWT")
    print("  🌐 api_gateway - API gateway with routing")
    print("  💾 data_service - Data service with CRUD operations")
    print("  📡 event_service - Event-driven service with CQRS")
    print("  📊 monitoring_service - Monitoring and metrics service")
    
    print("\\n🏗️ Generated Project Structure:")
    print("  📁 app/")
    print("    📄 main.py          # FastAPI application")
    print("    📄 config.py        # Configuration settings")
    print("    📁 api/             # API routes")
    print("    📁 models/          # Data models")
    print("    📁 services/        # Business logic")
    print("  📁 tests/             # Test suite")
    print("  📁 docker/            # Docker configuration")
    print("  📁 k8s/               # Kubernetes manifests")
    print("  📄 requirements.txt   # Python dependencies")
    print("  📄 Dockerfile         # Docker image")
    print("  📄 docker-compose.yml # Docker Compose")
    print("  📄 README.md          # Documentation")


def show_usage_examples():
    """Show CLI usage examples"""
    
    print("\\n⚙️ CLI Usage Examples:")
    
    print("\\n1. 🚀 Create New Project (Interactive):")
    print("   fastapi-ms create")
    
    print("\\n2. 🚀 Create New Project (Non-Interactive):")
    print("   fastapi-ms create --name my-service --template microservice")
    
    print("\\n3. 📋 List Available Templates:")
    print("   fastapi-ms list-templates")
    print("   fastapi-ms list-templates --format json")
    print("   fastapi-ms list-templates --category service")
    
    print("\\n4. 🔍 Validate Project:")
    print("   fastapi-ms validate")
    print("   fastapi-ms validate --path ./my-project")
    print("   fastapi-ms validate --path ./my-project --fix")
    
    print("\\n5. 📚 Get Help:")
    print("   fastapi-ms --help")
    print("   fastapi-ms create --help")
    print("   fastapi-ms validate --help")


def show_project_examples():
    """Show project configuration examples"""
    
    print("\\n📦 Project Configuration Examples:")
    
    print("\\n1. 🏢 Enterprise Microservice:")
    print("""
    Project Name: enterprise-api
    Template: microservice
    Services: auth_service, api_gateway, monitoring_service
    Deployment: Docker + Kubernetes + GitHub Actions
    Environments: development, staging, production
    """)
    
    print("\\n2. 🚀 Startup MVP:")
    print("""
    Project Name: startup-mvp
    Template: microservice
    Services: auth_service, data_service
    Deployment: Docker + Docker Compose
    Environments: development, production
    """)
    
    print("\\n3. 📊 Data Platform:")
    print("""
    Project Name: data-platform
    Template: data_service
    Services: event_service, monitoring_service
    Deployment: Kubernetes + GitLab CI
    Environments: development, staging, production
    """)
    
    print("\\n4. 🔐 Authentication Service:")
    print("""
    Project Name: auth-service
    Template: auth_service
    Services: monitoring_service
    Deployment: Docker + Jenkins
    Environments: development, production
    """)


def show_wizard_flow():
    """Show interactive wizard flow"""
    
    print("\\n🧙 Interactive Wizard Flow:")
    
    print("\\n📋 Step 1: Project Information")
    print("   • Project name (validation)")
    print("   • Description")
    print("   • Version (semantic versioning)")
    print("   • Author details")
    print("   • License selection")
    
    print("\\n🎯 Step 2: Template Selection")
    print("   • Browse available templates")
    print("   • View template details")
    print("   • Select base template")
    
    print("\\n⚙️ Step 3: Configuration")
    print("   • Required template variables")
    print("   • Optional settings with defaults")
    print("   • Validation and help text")
    
    print("\\n🔧 Step 4: Additional Services")
    print("   • Select complementary services")
    print("   • Configure service-specific settings")
    print("   • Service integration options")
    
    print("\\n🚀 Step 5: Deployment Options")
    print("   • Docker configuration")
    print("   • Kubernetes manifests")
    print("   • CI/CD pipeline selection")
    print("   • Environment setup")
    
    print("\\n🏗️ Step 6: Generation")
    print("   • File generation with progress")
    print("   • Git repository initialization")
    print("   • Next steps guidance")


if __name__ == "__main__":
    # Show CLI features
    demonstrate_cli_features()
    
    # Show usage examples
    show_usage_examples()
    
    # Show project examples
    show_project_examples()
    
    # Show wizard flow
    show_wizard_flow()
    
    # Run the main example
    print("\\n🚀 Running Project Creation CLI Example...")
    print("=" * 50)
    
    asyncio.run(main())
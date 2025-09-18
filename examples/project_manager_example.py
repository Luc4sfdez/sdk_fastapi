"""
Project Manager Example

Demonstrates the usage of the FastAPI Microservices SDK Project Manager.
"""

import asyncio
import tempfile
import json
from pathlib import Path

from fastapi_microservices_sdk.templates import (
    ProjectManager,
    ServiceManager,
    TemplateEngine,
    TemplateManager,
    TemplateRegistry
)
from fastapi_microservices_sdk.templates.config import CLIConfig


async def main():
    """Main example function."""
    print("🚀 FastAPI Microservices SDK - Project Manager Example")
    print("=" * 60)
    
    # Create temporary directory for examples
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Example 1: Template Registry and Management
        print("\n📋 Example 1: Template Registry")
        print("-" * 35)
        
        # Initialize template system
        config = CLIConfig(template_paths=[str(temp_path / "templates")])
        template_engine = TemplateEngine(config)
        template_manager = TemplateManager(config)
        
        # List available templates
        templates = template_manager.list_templates()
        print(f"✅ Found {len(templates)} available templates:")
        
        for template_info in templates:
            print(f"   📋 {template_info.name} ({template_info.id})")
            print(f"      Category: {template_info.category.value}")
            print(f"      Version: {template_info.version}")
            print(f"      Source: {template_info.source}")
            print(f"      Description: {template_info.description}")
            print()
        
        # Example 2: Project Creation and Management
        print("\n🏗️ Example 2: Project Creation")
        print("-" * 35)
        
        # Initialize project manager
        project_manager = ProjectManager(template_engine)
        
        # Create a new project
        project_path = temp_path / "my-microservices-project"
        
        project_variables = {
            "project_name": "my-microservices-project",
            "description": "A comprehensive microservices project",
            "author": "SDK Example",
            "version": "1.0.0",
            "database": "postgresql",
            "use_redis": True,
            "enable_observability": True,
            "enable_security": True
        }
        
        print("🔨 Creating project with microservice template...")
        project = project_manager.create_project(
            name="my-microservices-project",
            template_id="microservice",
            variables=project_variables,
            output_path=project_path
        )
        
        print(f"✅ Project created: {project.name}")
        print(f"📁 Location: {project.path}")
        print(f"📝 Description: {project.config.description}")
        print(f"👤 Author: {project.config.author}")
        print(f"🏷️ Version: {project.config.version}")
        
        # Example 3: Service Management
        print("\n🔧 Example 3: Service Management")
        print("-" * 35)
        
        # Initialize service manager
        service_manager = ServiceManager(template_engine)
        
        # Add multiple services to the project
        services_to_add = [
            {
                "name": "auth-service",
                "template_id": "microservice",
                "variables": {
                    "service_name": "auth-service",
                    "type": "auth",
                    "port": 8001,
                    "database": "postgresql",
                    "description": "Authentication and authorization service"
                }
            },
            {
                "name": "user-service",
                "template_id": "microservice", 
                "variables": {
                    "service_name": "user-service",
                    "type": "api",
                    "port": 8002,
                    "database": "postgresql",
                    "dependencies": ["auth-service"],
                    "description": "User management service"
                }
            },
            {
                "name": "notification-service",
                "template_id": "microservice",
                "variables": {
                    "service_name": "notification-service",
                    "type": "worker",
                    "port": 8003,
                    "message_broker": "rabbitmq",
                    "dependencies": ["user-service"],
                    "description": "Notification processing service"
                }
            },
            {
                "name": "api-gateway",
                "template_id": "microservice",
                "variables": {
                    "service_name": "api-gateway",
                    "type": "gateway",
                    "port": 8000,
                    "dependencies": ["auth-service", "user-service"],
                    "description": "API Gateway for routing requests"
                }
            }
        ]
        
        print("🔧 Adding services to project...")
        for service_config in services_to_add:
            try:
                service = service_manager.create_service(
                    project=project,
                    name=service_config["name"],
                    template_id=service_config["template_id"],
                    variables=service_config["variables"]
                )
                print(f"   ✅ Added service: {service.name} (port: {service.config.port})")
            except Exception as e:
                print(f"   ❌ Failed to add {service_config['name']}: {str(e)}")
        
        # Save project
        project_manager.save_project(project)
        print(f"\n💾 Project saved with {len(project.services)} services")
        
        # Example 4: Project Analysis
        print("\n📊 Example 4: Project Analysis")
        print("-" * 30)
        
        # Analyze project structure
        analysis = project_manager.analyze_project_structure(project)
        
        print("🔍 Project Structure Analysis:")
        print(f"   📊 Total Services: {analysis['services_count']}")
        print(f"   🏷️ Service Types: {analysis['service_types']}")
        print(f"   🔌 Ports Used: {analysis['ports_used']}")
        print(f"   🗄️ Databases: {analysis['databases_used']}")
        print(f"   📨 Message Brokers: {analysis['message_brokers_used']}")
        
        if analysis['dependencies']:
            print(f"   🔗 Dependencies:")
            for service, dependents in analysis['dependencies'].items():
                print(f"      {service} ← {', '.join(dependents)}")
        
        if analysis['potential_issues']:
            print(f"   ⚠️ Potential Issues:")
            for issue in analysis['potential_issues']:
                print(f"      • {issue}")
        
        # Example 5: Service Dependency Analysis
        print("\n🔗 Example 5: Service Dependency Analysis")
        print("-" * 45)
        
        for service in project.services:
            if service.config.dependencies:
                dep_analysis = service_manager.analyze_service_dependencies(project, service.name)
                
                print(f"🔧 Service: {service.name}")
                print(f"   Direct Dependencies: {dep_analysis['direct_dependencies']}")
                print(f"   Dependents: {dep_analysis['dependents']}")
                print(f"   Services Affected: {dep_analysis['impact_analysis']['services_affected']}")
                print(f"   Critical Path: {dep_analysis['impact_analysis']['critical_path']}")
                
                # Get improvement suggestions
                suggestions = service_manager.suggest_service_improvements(project, service.name)
                if suggestions:
                    print(f"   💡 Suggestions:")
                    for suggestion in suggestions:
                        print(f"      • {suggestion}")
                print()
        
        # Example 6: Documentation Generation
        print("\n📚 Example 6: Documentation Generation")
        print("-" * 40)
        
        # Generate project documentation
        documentation = project_manager.generate_project_documentation(project)
        
        # Save documentation
        doc_file = project_path / "PROJECT_DOCUMENTATION.md"
        with open(doc_file, 'w', encoding='utf-8') as f:
            f.write(documentation)
        
        print(f"✅ Generated project documentation")
        print(f"📄 Saved to: {doc_file}")
        
        # Show first few lines of documentation
        doc_lines = documentation.split('\n')[:15]
        print(f"\n📖 Documentation Preview:")
        for line in doc_lines:
            print(f"   {line}")
        if len(documentation.split('\n')) > 15:
            print("   ...")
        
        # Example 7: Project Export and Import
        print("\n💾 Example 7: Project Export/Import")
        print("-" * 35)
        
        # Export project configuration
        exported_config = project_manager.export_project_config(project)
        
        # Save exported configuration
        export_file = project_path / "project_export.json"
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(exported_config, f, indent=2, default=str)
        
        print(f"✅ Exported project configuration")
        print(f"📄 Export file: {export_file}")
        print(f"📊 Export contains:")
        print(f"   • Project metadata")
        print(f"   • {len(exported_config['project']['services'])} services")
        print(f"   • Structure analysis")
        print(f"   • SDK version: {exported_config['sdk_version']}")
        
        # Example 8: Project Cloning
        print("\n🔄 Example 8: Project Cloning")
        print("-" * 25)
        
        # Clone the project
        cloned_project_path = temp_path / "cloned-microservices-project"
        
        try:
            cloned_project = project_manager.clone_project(
                source_project=project,
                new_name="cloned-microservices-project",
                output_path=cloned_project_path
            )
            
            print(f"✅ Cloned project successfully")
            print(f"📁 Original: {project.name} ({len(project.services)} services)")
            print(f"📁 Clone: {cloned_project.name} ({len(cloned_project.services)} services)")
            print(f"📍 Clone location: {cloned_project_path}")
            
        except Exception as e:
            print(f"❌ Cloning failed: {str(e)}")
        
        # Example 9: Service Updates and Management
        print("\n🔧 Example 9: Service Updates")
        print("-" * 25)
        
        # Update a service
        if project.services:
            service_to_update = project.services[0]
            original_port = service_to_update.config.port
            
            updates = {
                "port": original_port + 1000,
                "environment": {
                    "LOG_LEVEL": "DEBUG",
                    "ENVIRONMENT": "development"
                }
            }
            
            updated_service = service_manager.update_service(
                project=project,
                service_name=service_to_update.name,
                updates=updates
            )
            
            print(f"✅ Updated service: {updated_service.name}")
            print(f"   Port: {original_port} → {updated_service.config.port}")
            print(f"   Environment variables: {len(updated_service.config.environment)}")
        
        # Example 10: Project Validation
        print("\n✅ Example 10: Project Validation")
        print("-" * 30)
        
        # Validate the project
        validation_errors = project_manager.validate_project(project)
        
        if validation_errors:
            print("❌ Project validation failed:")
            for error in validation_errors:
                print(f"   • {error}")
        else:
            print("✅ Project validation passed")
        
        # Validate individual services
        print(f"\n🔧 Service Validation:")
        for service in project.services:
            service_errors = service_manager.validate_service(service)
            if service_errors:
                print(f"   ❌ {service.name}: {len(service_errors)} issues")
                for error in service_errors[:3]:  # Show first 3 errors
                    print(f"      • {error}")
                if len(service_errors) > 3:
                    print(f"      ... and {len(service_errors) - 3} more")
            else:
                print(f"   ✅ {service.name}: Valid")
        
        # Example 11: Template Information
        print("\n📋 Example 11: Template Information")
        print("-" * 35)
        
        # Get detailed template information
        for template_info in templates[:3]:  # Show first 3 templates
            try:
                template = template_manager.get_template(template_info.id)
                
                print(f"📋 Template: {template_info.name}")
                print(f"   ID: {template_info.id}")
                print(f"   Files: {len(template.files)}")
                print(f"   Variables: {len(template.config.variables)}")
                
                if template.config.variables:
                    print(f"   Required Variables:")
                    for var in template.config.variables:
                        if var.required:
                            print(f"      • {var.name} ({var.type.value}): {var.description}")
                print()
                
            except Exception as e:
                print(f"   ❌ Error loading template: {str(e)}")
        
        print("\n🎉 Project Manager examples completed!")
        print("\nKey Features Demonstrated:")
        print("✅ Template registry and discovery")
        print("✅ Project creation from templates")
        print("✅ Multi-service project management")
        print("✅ Service dependency analysis")
        print("✅ Project structure analysis")
        print("✅ Automatic documentation generation")
        print("✅ Project export/import capabilities")
        print("✅ Project cloning functionality")
        print("✅ Service updates and configuration")
        print("✅ Comprehensive validation system")
        print("✅ Improvement suggestions")
        
        print(f"\n📁 All examples generated in: {temp_path}")
        print("Note: Files are in temporary directory and will be cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
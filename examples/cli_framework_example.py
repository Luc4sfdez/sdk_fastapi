"""
CLI Framework Example

Demonstrates the usage of the FastAPI Microservices SDK CLI Framework.
"""

import asyncio
import tempfile
import sys
from pathlib import Path

# Add the SDK to the path for the example
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi_microservices_sdk.templates.cli.framework import create_cli
from fastapi_microservices_sdk.templates.cli.context import CLIContext
from fastapi_microservices_sdk.templates.cli.wizard import (
    InteractiveWizard,
    ProjectCreationWizard,
    CRUDGenerationWizard
)


def demonstrate_cli_commands():
    """Demonstrate CLI command usage."""
    print("🚀 FastAPI Microservices SDK - CLI Framework Example")
    print("=" * 60)
    
    # Example 1: Create CLI Framework
    print("\n📋 Example 1: CLI Framework Creation")
    print("-" * 40)
    
    cli = create_cli()
    
    print(f"✅ Created CLI framework: {cli.name}")
    print(f"📋 Available commands: {cli.registry.list_commands()}")
    
    # Example 2: Demonstrate Help System
    print("\n📚 Example 2: Help System")
    print("-" * 30)
    
    print("🔍 Main help:")
    try:
        cli.run(["--help"])
    except SystemExit:
        pass  # argparse calls sys.exit() after showing help
    
    print("\n🔍 Create command help:")
    try:
        cli.run(["create", "--help"])
    except SystemExit:
        pass
    
    # Example 3: Interactive Wizard Demo
    print("\n\n🧙 Example 3: Interactive Wizard (Simulated)")
    print("-" * 45)
    
    # Create a simple wizard for demonstration
    demo_wizard = InteractiveWizard(
        name="demo_wizard",
        title="Demo Configuration Wizard",
        description="Demonstrate wizard capabilities"
    )
    
    # Add steps
    demo_wizard.add_text_step(
        "project_name",
        "Project Name",
        "Enter your project name",
        default="my-awesome-project"
    )
    
    demo_wizard.add_choice_step(
        "framework",
        "Framework",
        ["FastAPI", "Django", "Flask"],
        "Choose your framework",
        default="FastAPI"
    )
    
    demo_wizard.add_boolean_step(
        "use_database",
        "Use Database",
        "Do you want to use a database?",
        default=True
    )
    
    demo_wizard.add_number_step(
        "port",
        "Port Number",
        "Enter the port number",
        default=8000
    )
    
    print(f"✅ Created wizard with {len(demo_wizard.steps)} steps:")
    for i, step in enumerate(demo_wizard.steps, 1):
        print(f"   {i}. {step.title} ({step.input_type})")
    
    # Simulate wizard results (since we can't do interactive input in example)
    simulated_results = {
        "project_name": "my-awesome-project",
        "framework": "FastAPI",
        "use_database": True,
        "port": 8000
    }
    
    print(f"\n📊 Simulated wizard results:")
    for key, value in simulated_results.items():
        print(f"   {key}: {value}")
    
    # Example 4: CLI Context Management
    print("\n\n⚙️ Example 4: CLI Context Management")
    print("-" * 40)
    
    # Create CLI context
    context = CLIContext.create(
        verbose=True,
        dry_run=True
    )
    
    print(f"✅ Created CLI context:")
    print(f"   Verbose: {context.verbose}")
    print(f"   Dry Run: {context.dry_run}")
    print(f"   Current Directory: {context.current_directory}")
    
    # Demonstrate context methods
    context.set_variable("example_var", "example_value")
    context.update_variables({
        "var1": "value1",
        "var2": "value2"
    })
    
    print(f"\n📝 Context variables:")
    for key, value in context.variables.items():
        print(f"   {key}: {value}")
    
    # Example 5: Command Simulation
    print("\n\n🎮 Example 5: Command Simulation")
    print("-" * 35)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print(f"📁 Using temporary directory: {temp_path}")
        
        # Simulate create command
        print("\n🔨 Simulating 'create' command:")
        create_args = [
            "create",
            "my-test-project",
            "--template", "microservice",
            "--output", str(temp_path / "my-test-project"),
            "--dry-run"
        ]
        
        print(f"   Command: fastapi-sdk {' '.join(create_args)}")
        
        try:
            result = cli.run(create_args)
            print(f"   ✅ Command completed with exit code: {result}")
        except Exception as e:
            print(f"   ⚠️ Command simulation: {str(e)}")
        
        # Simulate generate command
        print("\n🔧 Simulating 'generate' command:")
        generate_args = [
            "generate",
            "crud",
            "User",
            "--dry-run",
            "--verbose"
        ]
        
        print(f"   Command: fastapi-sdk {' '.join(generate_args)}")
        
        try:
            result = cli.run(generate_args)
            print(f"   ✅ Command completed with exit code: {result}")
        except Exception as e:
            print(f"   ⚠️ Command simulation: {str(e)}")
        
        # Simulate list command
        print("\n📋 Simulating 'list' command:")
        list_args = ["list", "templates", "--verbose"]
        
        print(f"   Command: fastapi-sdk {' '.join(list_args)}")
        
        try:
            result = cli.run(list_args)
            print(f"   ✅ Command completed with exit code: {result}")
        except Exception as e:
            print(f"   ⚠️ Command simulation: {str(e)}")
    
    # Example 6: Configuration Management
    print("\n\n⚙️ Example 6: Configuration Management")
    print("-" * 40)
    
    print("🔧 Simulating config commands:")
    
    config_commands = [
        ["config", "list"],
        ["config", "get", "template-paths"],
        ["config", "set", "cache-enabled", "true"],
    ]
    
    for cmd_args in config_commands:
        print(f"\n   Command: fastapi-sdk {' '.join(cmd_args)}")
        try:
            result = cli.run(cmd_args + ["--dry-run"])
            print(f"   ✅ Exit code: {result}")
        except Exception as e:
            print(f"   ⚠️ Simulation: {str(e)}")


def demonstrate_wizard_types():
    """Demonstrate different wizard types."""
    print("\n\n🧙 Wizard Types Demonstration")
    print("=" * 40)
    
    # Project Creation Wizard
    print("\n📁 Project Creation Wizard:")
    project_wizard = ProjectCreationWizard()
    print(f"   Steps: {len(project_wizard.steps)}")
    
    step_types = {}
    for step in project_wizard.steps:
        step_types[step.input_type] = step_types.get(step.input_type, 0) + 1
    
    print("   Step types:")
    for step_type, count in step_types.items():
        print(f"     {step_type}: {count}")
    
    # CRUD Generation Wizard
    print("\n🔧 CRUD Generation Wizard:")
    crud_wizard = CRUDGenerationWizard()
    print(f"   Steps: {len(crud_wizard.steps)}")
    
    for i, step in enumerate(crud_wizard.steps, 1):
        print(f"     {i}. {step.title} ({step.input_type})")


def demonstrate_error_handling():
    """Demonstrate CLI error handling."""
    print("\n\n❌ Error Handling Demonstration")
    print("=" * 40)
    
    cli = create_cli()
    
    error_scenarios = [
        (["nonexistent-command"], "Unknown command"),
        (["create"], "Missing required arguments"),
        (["generate", "invalid-type", "test"], "Invalid generation type"),
    ]
    
    for args, description in error_scenarios:
        print(f"\n🔍 Testing: {description}")
        print(f"   Command: fastapi-sdk {' '.join(args)}")
        
        try:
            result = cli.run(args)
            print(f"   Exit code: {result}")
        except SystemExit as e:
            print(f"   ✅ Handled gracefully with exit code: {e.code}")
        except Exception as e:
            print(f"   ⚠️ Exception: {str(e)}")


def demonstrate_advanced_features():
    """Demonstrate advanced CLI features."""
    print("\n\n🚀 Advanced Features")
    print("=" * 30)
    
    # Global options
    print("\n🌐 Global Options:")
    global_options = [
        "--verbose",
        "--quiet", 
        "--dry-run",
        "--config /path/to/config.yaml"
    ]
    
    for option in global_options:
        print(f"   {option}")
    
    # Command aliases
    print("\n🔗 Command Aliases:")
    aliases = {
        "create": ["new"],
        "generate": ["gen"],
        "list": ["ls"],
        "config": ["cfg"]
    }
    
    for command, command_aliases in aliases.items():
        print(f"   {command}: {', '.join(command_aliases)}")
    
    # Auto-completion support
    print("\n⚡ Auto-completion:")
    print("   Shell completion support available for:")
    print("     - Commands and subcommands")
    print("     - Options and flags")
    print("     - File and directory paths")
    print("     - Template names")
    
    # Plugin system
    print("\n🔌 Plugin System:")
    print("   Extensible architecture supports:")
    print("     - Custom commands")
    print("     - Custom wizards")
    print("     - Custom generators")
    print("     - Custom validators")


async def main():
    """Main example function."""
    try:
        demonstrate_cli_commands()
        demonstrate_wizard_types()
        demonstrate_error_handling()
        demonstrate_advanced_features()
        
        print("\n🎉 CLI Framework examples completed!")
        print("\nKey Features Demonstrated:")
        print("✅ Complete CLI framework with command registration")
        print("✅ Interactive wizards for complex operations")
        print("✅ Comprehensive error handling and validation")
        print("✅ Context management and configuration")
        print("✅ Multiple command types (create, generate, list, config)")
        print("✅ Dry-run mode and verbose output")
        print("✅ Global options and command aliases")
        print("✅ Extensible architecture for plugins")
        
        print("\n📚 Usage Examples:")
        print("# Create a new project")
        print("fastapi-sdk create my-project --interactive")
        print()
        print("# Generate CRUD operations")
        print("fastapi-sdk generate crud User --interactive")
        print()
        print("# List available templates")
        print("fastapi-sdk list templates --verbose")
        print()
        print("# Configure CLI settings")
        print("fastapi-sdk config set default-author 'Your Name'")
        print()
        print("# Initialize project in current directory")
        print("fastapi-sdk init --interactive")
        
    except Exception as e:
        print(f"❌ Example error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
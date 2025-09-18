"""
Authentication Service Template Example

Demonstrates the comprehensive authentication service template with JWT, RBAC, and user management.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from fastapi_microservices_sdk.templates.builtin_templates.auth_service import AuthServiceTemplate


async def demonstrate_auth_service_template():
    """Demonstrate authentication service template generation."""
    print("🔐 Authentication Service Template Demonstration")
    print("=" * 60)
    
    # Initialize template
    template = AuthServiceTemplate()
    
    print(f"📋 Template: {template.name}")
    print(f"📝 Description: {template.description}")
    print(f"🏷️ Tags: {', '.join(template.tags)}")
    print(f"📦 Version: {template.version}")
    
    # Template variables
    variables = {
        # Required variables
        "service_name": "auth_service",
        "database_type": "postgresql",
        "jwt_secret_key": "your-super-secret-jwt-key-that-is-at-least-32-characters-long",
        "admin_email": "admin@example.com",
        "admin_password": "SecureAdmin123!",
        
        # Optional variables
        "service_description": "Complete authentication and authorization service",
        "service_version": "1.0.0",
        "enable_rbac": True,
        "enable_email_verification": True,
        "enable_password_reset": True,
        "enable_2fa": True,
        "jwt_algorithm": "HS256",
        "jwt_expire_minutes": 30,
        "refresh_token_expire_days": 7,
        "password_min_length": 8,
        "max_login_attempts": 5,
        "lockout_duration_minutes": 15,
        "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "your-email@gmail.com",
        "smtp_password": "your-app-password",
        "redis_url": "redis://localhost:6379",
        "include_swagger": True,
        "include_tests": True,
        "include_docker": True
    }
    
    print(f"\n🔧 Template Variables:")
    for key, value in variables.items():
        if "password" in key.lower() or "secret" in key.lower():
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")
    
    # Validate variables
    print(f"\n✅ Validating template variables...")
    validation_errors = template.validate_variables(variables)
    
    if validation_errors:
        print("❌ Validation errors found:")
        for error in validation_errors:
            print(f"  - {error}")
        return
    
    print("✅ All variables are valid!")
    
    # Generate service
    print(f"\n🚀 Generating authentication service...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "auth_service"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            generated_files = template.generate_files(variables, output_dir)
            
            print(f"✅ Generated {len(generated_files)} files successfully!")
            
            # Display generated structure
            print(f"\n📁 Generated Project Structure:")
            for root, dirs, files in output_dir.walk():
                level = len(root.relative_to(output_dir).parts)
                indent = "  " * level
                print(f"{indent}📂 {root.name}/")
                
                sub_indent = "  " * (level + 1)
                for file in files:
                    file_path = root / file
                    size = file_path.stat().st_size
                    print(f"{sub_indent}📄 {file} ({size} bytes)")
            
            # Show sample content from key files
            print(f"\n🔍 Sample Generated Content:")
            
            # User model
            user_model_path = output_dir / "app" / "models" / "user.py"
            if user_model_path.exists():
                print(f"\n📝 User Model ({user_model_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = user_model_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Auth schemas
            auth_schema_path = output_dir / "app" / "schemas" / "auth.py"
            if auth_schema_path.exists():
                print(f"\n📋 Auth Schemas ({auth_schema_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = auth_schema_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # JWT handler
            jwt_handler_path = output_dir / "app" / "auth" / "jwt_handler.py"
            if jwt_handler_path.exists():
                print(f"\n🔑 JWT Handler ({jwt_handler_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = jwt_handler_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Copy to permanent location for inspection
            permanent_dir = Path("generated_auth_service_example")
            if permanent_dir.exists():
                shutil.rmtree(permanent_dir)
            shutil.copytree(output_dir, permanent_dir)
            
            print(f"\n💾 Complete service copied to: {permanent_dir.absolute()}")
            
            # Show usage instructions
            print(f"\n📚 Usage Instructions:")
            print("1. Install dependencies:")
            print("   pip install -r requirements.txt")
            print("\n2. Set up environment variables:")
            print("   cp .env.example .env")
            print("   # Edit .env with your configuration")
            print("\n3. Initialize database:")
            print("   python scripts/init_db.py")
            print("\n4. Run the service:")
            print("   uvicorn app.main:app --reload")
            print("\n5. Access API documentation:")
            print("   http://localhost:8000/docs")
            
            return generated_files
            
        except Exception as e:
            print(f"❌ Error generating service: {e}")
            raise


async def demonstrate_template_features():
    """Demonstrate specific template features."""
    print("\n🎯 Authentication Service Features")
    print("=" * 40)
    
    template = AuthServiceTemplate()
    
    print("✅ Core Features:")
    print("  🔐 JWT Authentication with refresh tokens")
    print("  👤 User registration and management")
    print("  📧 Email verification")
    print("  🔄 Password reset functionality")
    print("  🔒 Account lockout protection")
    print("  📱 Two-factor authentication (TOTP)")
    print("  🛡️ Role-based access control (RBAC)")
    print("  🔑 Permission-based authorization")
    print("  📊 User activity tracking")
    print("  🚫 Rate limiting and security")
    
    print("\n✅ Database Support:")
    for db in template.config["supported_databases"]:
        print(f"  📊 {db.title()}")
    
    print("\n✅ Default Roles:")
    for role in template.config["default_roles"]:
        print(f"  👥 {role}")
    
    print("\n✅ Default Permissions:")
    for perm in template.config["default_permissions"]:
        print(f"  🔐 {perm}")
    
    print("\n✅ Security Features:")
    print(f"  🔒 Password minimum length: {template.config['password_min_length']}")
    print(f"  🚫 Max login attempts: {template.config['max_login_attempts']}")
    print(f"  ⏰ Lockout duration: {template.config['lockout_duration_minutes']} minutes")
    print(f"  🔑 JWT expiry: {template.config['jwt_expire_minutes']} minutes")
    print(f"  🔄 Refresh token expiry: {template.config['refresh_token_expire_days']} days")


async def demonstrate_different_configurations():
    """Demonstrate different template configurations."""
    print("\n🔧 Different Configuration Examples")
    print("=" * 40)
    
    template = AuthServiceTemplate()
    
    configurations = [
        {
            "name": "Basic Auth Service",
            "config": {
                "service_name": "basic_auth",
                "database_type": "sqlite",
                "jwt_secret_key": "basic-secret-key-for-development-only-32chars",
                "admin_email": "admin@basic.com",
                "admin_password": "BasicAdmin123!",
                "enable_rbac": False,
                "enable_2fa": False,
                "enable_email_verification": False,
                "include_tests": False,
                "include_docker": False
            }
        },
        {
            "name": "Enterprise Auth Service",
            "config": {
                "service_name": "enterprise_auth",
                "database_type": "postgresql",
                "jwt_secret_key": "enterprise-super-secure-secret-key-for-production-use",
                "admin_email": "admin@enterprise.com",
                "admin_password": "EnterpriseSecure123!@#",
                "enable_rbac": True,
                "enable_2fa": True,
                "enable_email_verification": True,
                "enable_password_reset": True,
                "jwt_expire_minutes": 15,
                "refresh_token_expire_days": 30,
                "password_min_length": 12,
                "max_login_attempts": 3,
                "lockout_duration_minutes": 30,
                "include_tests": True,
                "include_docker": True
            }
        },
        {
            "name": "MongoDB Auth Service",
            "config": {
                "service_name": "mongo_auth",
                "database_type": "mongodb",
                "jwt_secret_key": "mongodb-auth-service-secret-key-32-chars-min",
                "admin_email": "admin@mongo.com",
                "admin_password": "MongoAdmin123!",
                "enable_rbac": True,
                "enable_2fa": False,
                "enable_email_verification": True,
                "include_tests": True,
                "include_docker": True
            }
        }
    ]
    
    for config_example in configurations:
        print(f"\n📋 {config_example['name']}:")
        
        # Validate configuration
        errors = template.validate_variables(config_example['config'])
        
        if errors:
            print("  ❌ Configuration errors:")
            for error in errors:
                print(f"    - {error}")
        else:
            print("  ✅ Valid configuration")
            
            # Show key features
            config = config_example['config']
            print(f"  📊 Database: {config['database_type']}")
            print(f"  🛡️ RBAC: {'Enabled' if config.get('enable_rbac', True) else 'Disabled'}")
            print(f"  📱 2FA: {'Enabled' if config.get('enable_2fa', False) else 'Disabled'}")
            print(f"  📧 Email Verification: {'Enabled' if config.get('enable_email_verification', True) else 'Disabled'}")
            print(f"  🧪 Tests: {'Included' if config.get('include_tests', True) else 'Not included'}")
            print(f"  🐳 Docker: {'Included' if config.get('include_docker', True) else 'Not included'}")


async def main():
    """Main demonstration function."""
    print("🎯 FastAPI Microservices SDK - Authentication Service Template")
    print("=" * 70)
    
    try:
        # Demonstrate template features
        await demonstrate_template_features()
        
        # Demonstrate different configurations
        await demonstrate_different_configurations()
        
        # Demonstrate template generation
        generated_files = await demonstrate_auth_service_template()
        
        print("\n✨ Authentication Service Template demonstration completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✅ Complete authentication service generation")
        print("  ✅ JWT token management with refresh tokens")
        print("  ✅ Role-based access control (RBAC)")
        print("  ✅ Two-factor authentication (2FA)")
        print("  ✅ Email verification and password reset")
        print("  ✅ User management and security features")
        print("  ✅ Multiple database support")
        print("  ✅ Comprehensive test generation")
        print("  ✅ Docker containerization")
        print("  ✅ Production-ready configuration")
        
        if generated_files:
            print(f"\n📁 Generated {len(generated_files)} files in total")
            print("🚀 Ready to deploy authentication service!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
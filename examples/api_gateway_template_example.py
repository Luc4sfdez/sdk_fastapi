"""
API Gateway Template Example

Demonstrates the comprehensive API Gateway template with routing, rate limiting,
circuit breakers, load balancing, and advanced gateway features.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
from fastapi_microservices_sdk.templates.builtin_templates.api_gateway import APIGatewayTemplate


async def demonstrate_api_gateway_template():
    """Demonstrate API Gateway template generation."""
    print("🌐 API Gateway Template Demonstration")
    print("=" * 50)
    
    # Initialize template
    template = APIGatewayTemplate()
    
    print(f"📋 Template: {template.name}")
    print(f"📝 Description: {template.description}")
    print(f"🏷️ Tags: {', '.join(template.tags)}")
    print(f"📦 Version: {template.version}")
    
    # Template variables for a comprehensive API Gateway
    variables = {
        # Required variables
        "gateway_name": "enterprise_gateway",
        "gateway_port": 8080,
        "services": [
            {
                "name": "user_service",
                "url": "http://user-service:8001",
                "path": "/api/v1/users",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "timeout": 30,
                "retries": 3,
                "rate_limit": 1000,
                "auth_required": True,
                "required_roles": ["user", "admin"]
            },
            {
                "name": "order_service", 
                "url": "http://order-service:8002",
                "path": "/api/v1/orders",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "timeout": 45,
                "retries": 2,
                "rate_limit": 500,
                "auth_required": True,
                "required_roles": ["user", "admin"]
            },
            {
                "name": "payment_service",
                "url": "http://payment-service:8003", 
                "path": "/api/v1/payments",
                "methods": ["POST", "GET"],
                "timeout": 60,
                "retries": 5,
                "rate_limit": 100,
                "auth_required": True,
                "required_roles": ["admin"],
                "circuit_breaker_failure_threshold": 3,
                "circuit_breaker_timeout": 120
            },
            {
                "name": "notification_service",
                "url": "http://notification-service:8004",
                "path": "/api/v1/notifications",
                "methods": ["POST", "GET"],
                "timeout": 15,
                "retries": 1,
                "rate_limit": 2000,
                "auth_required": False
            },
            {
                "name": "analytics_service",
                "url": "http://analytics-service:8005",
                "path": "/api/v1/analytics",
                "methods": ["GET", "POST"],
                "timeout": 90,
                "retries": 2,
                "rate_limit": 200,
                "auth_required": True,
                "required_roles": ["admin", "analyst"]
            }
        ],
        
        # Optional variables
        "gateway_description": "Enterprise API Gateway for microservices architecture",
        "gateway_version": "2.0.0",
        "gateway_host": "0.0.0.0",
        "enable_rate_limiting": True,
        "enable_circuit_breaker": True,
        "enable_load_balancing": True,
        "enable_authentication": True,
        "enable_cors": True,
        "enable_compression": True,
        "enable_caching": True,
        "enable_metrics": True,
        "enable_tracing": True,
        "enable_health_checks": True,
        "default_timeout": 30,
        "default_retries": 3,
        "rate_limit_per_minute": 1000,
        "circuit_breaker_failure_threshold": 5,
        "circuit_breaker_timeout": 60,
        "load_balancing_algorithm": "round_robin",
        "cors_origins": ["https://app.example.com", "https://admin.example.com"],
        "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "cors_headers": ["Authorization", "Content-Type", "X-Requested-With"],
        "jwt_secret_key": "enterprise-gateway-super-secret-jwt-key-32-chars-minimum",
        "redis_url": "redis://redis-cluster:6379",
        "prometheus_enabled": True,
        "jaeger_enabled": True,
        "include_swagger": True,
        "include_tests": True,
        "include_docker": True,
        "include_kubernetes": True
    }
    
    print(f"\n🔧 Template Variables:")
    for key, value in variables.items():
        if "secret" in key.lower() or "password" in key.lower():
            print(f"  {key}: {'*' * len(str(value))}")
        elif key == "services":
            print(f"  {key}: [{len(value)} services configured]")
            for i, service in enumerate(value):
                print(f"    {i+1}. {service['name']} -> {service['url']}{service['path']}")
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
    
    # Generate gateway
    print(f"\n🚀 Generating API Gateway...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "enterprise_gateway"
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
            
            # Main application
            main_app_path = output_dir / "app" / "main.py"
            if main_app_path.exists():
                print(f"\n📝 Main Application ({main_app_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = main_app_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Routes configuration
            routes_path = output_dir / "app" / "routing" / "routes.py"
            if routes_path.exists():
                print(f"\n🔗 Routes Configuration ({routes_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = routes_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Service proxy
            proxy_path = output_dir / "app" / "routing" / "proxy.py"
            if proxy_path.exists():
                print(f"\n🔄 Service Proxy ({proxy_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = proxy_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Rate limiter
            rate_limiter_path = output_dir / "app" / "services" / "rate_limiter.py"
            if rate_limiter_path.exists():
                print(f"\n⏱️ Rate Limiter ({rate_limiter_path.relative_to(output_dir)}):")
                print("─" * 50)
                content = rate_limiter_path.read_text(encoding='utf-8')
                print(content[:800] + "..." if len(content) > 800 else content)
            
            # Copy to permanent location for inspection
            permanent_dir = Path("generated_api_gateway_example")
            if permanent_dir.exists():
                shutil.rmtree(permanent_dir)
            shutil.copytree(output_dir, permanent_dir)
            
            print(f"\n💾 Complete gateway copied to: {permanent_dir.absolute()}")
            
            # Show usage instructions
            print(f"\n📚 Usage Instructions:")
            print("1. Install dependencies:")
            print("   pip install -r requirements.txt")
            print("\n2. Set up environment variables:")
            print("   cp .env.example .env")
            print("   # Edit .env with your configuration")
            print("\n3. Start Redis (for rate limiting):")
            print("   docker run -d -p 6379:6379 redis:alpine")
            print("\n4. Run the gateway:")
            print("   uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload")
            print("\n5. Access API documentation:")
            print("   http://localhost:8080/docs")
            print("\n6. Check gateway health:")
            print("   http://localhost:8080/health")
            print("   http://localhost:8080/gateway/health/services")
            print("\n7. View metrics:")
            print("   http://localhost:8080/gateway/metrics")
            
            return generated_files
            
        except Exception as e:
            print(f"❌ Error generating gateway: {e}")
            raise


async def demonstrate_template_features():
    """Demonstrate specific template features."""
    print("\n🎯 API Gateway Features")
    print("=" * 30)
    
    template = APIGatewayTemplate()
    
    print("✅ Core Features:")
    print("  🔀 Dynamic request routing")
    print("  ⚖️ Load balancing with multiple algorithms")
    print("  ⏱️ Rate limiting with Redis backend")
    print("  🔌 Circuit breaker pattern")
    print("  🔐 JWT authentication and authorization")
    print("  🌐 CORS configuration")
    print("  📊 Prometheus metrics")
    print("  🔍 Distributed tracing")
    print("  💾 Response caching")
    print("  🗜️ Response compression")
    print("  🏥 Health checks")
    print("  📝 Request/response logging")
    print("  🚨 Centralized error handling")
    
    print("\n✅ Supported Protocols:")
    for protocol in template.config["supported_protocols"]:
        print(f"  🌐 {protocol.upper()}")
    
    print("\n✅ Load Balancing Algorithms:")
    for algorithm in template.config["load_balancing_algorithms"]:
        print(f"  ⚖️ {algorithm}")
    
    print("\n✅ Rate Limiting Strategies:")
    for strategy in template.config["rate_limiting_strategies"]:
        print(f"  ⏱️ {strategy}")
    
    print("\n✅ Circuit Breaker States:")
    for state in template.config["circuit_breaker_states"]:
        print(f"  🔌 {state}")


async def demonstrate_different_configurations():
    """Demonstrate different gateway configurations."""
    print("\n🔧 Different Gateway Configuration Examples")
    print("=" * 50)
    
    template = APIGatewayTemplate()
    
    configurations = [
        {
            "name": "Simple Gateway",
            "config": {
                "gateway_name": "simple_gateway",
                "gateway_port": 8080,
                "services": [
                    {
                        "name": "api_service",
                        "url": "http://localhost:8001",
                        "path": "/api"
                    }
                ],
                "enable_rate_limiting": False,
                "enable_circuit_breaker": False,
                "enable_authentication": False,
                "include_tests": False,
                "include_docker": False,
                "include_kubernetes": False
            }
        },
        {
            "name": "High-Performance Gateway",
            "config": {
                "gateway_name": "performance_gateway",
                "gateway_port": 8080,
                "services": [
                    {
                        "name": "fast_service",
                        "url": "http://fast-service:8001",
                        "path": "/api/v1/fast"
                    },
                    {
                        "name": "cache_service",
                        "url": "http://cache-service:8002", 
                        "path": "/api/v1/cache"
                    }
                ],
                "jwt_secret_key": "high-performance-gateway-secret-key-32-chars",
                "enable_rate_limiting": True,
                "enable_circuit_breaker": True,
                "enable_load_balancing": True,
                "enable_caching": True,
                "enable_compression": True,
                "rate_limit_per_minute": 10000,
                "load_balancing_algorithm": "least_connections"
            }
        },
        {
            "name": "Secure Enterprise Gateway",
            "config": {
                "gateway_name": "secure_gateway",
                "gateway_port": 443,
                "services": [
                    {
                        "name": "auth_service",
                        "url": "https://auth-service:8001",
                        "path": "/api/v1/auth",
                        "auth_required": True,
                        "required_roles": ["admin"]
                    },
                    {
                        "name": "data_service",
                        "url": "https://data-service:8002",
                        "path": "/api/v1/data",
                        "auth_required": True,
                        "required_roles": ["user", "admin"]
                    }
                ],
                "jwt_secret_key": "secure-enterprise-gateway-secret-key-for-production-use",
                "enable_authentication": True,
                "enable_rate_limiting": True,
                "enable_circuit_breaker": True,
                "enable_metrics": True,
                "enable_tracing": True,
                "rate_limit_per_minute": 500,
                "circuit_breaker_failure_threshold": 3,
                "circuit_breaker_timeout": 120,
                "cors_origins": ["https://secure-app.example.com"],
                "include_kubernetes": True
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
            print(f"  🌐 Port: {config['gateway_port']}")
            print(f"  🔗 Services: {len(config['services'])}")
            print(f"  ⏱️ Rate Limiting: {'Enabled' if config.get('enable_rate_limiting', True) else 'Disabled'}")
            print(f"  🔌 Circuit Breaker: {'Enabled' if config.get('enable_circuit_breaker', True) else 'Disabled'}")
            print(f"  🔐 Authentication: {'Enabled' if config.get('enable_authentication', True) else 'Disabled'}")
            print(f"  ⚖️ Load Balancing: {'Enabled' if config.get('enable_load_balancing', True) else 'Disabled'}")
            print(f"  🐳 Docker: {'Included' if config.get('include_docker', True) else 'Not included'}")
            print(f"  ☸️ Kubernetes: {'Included' if config.get('include_kubernetes', False) else 'Not included'}")


async def main():
    """Main demonstration function."""
    print("🎯 FastAPI Microservices SDK - API Gateway Template")
    print("=" * 60)
    
    try:
        # Demonstrate template features
        await demonstrate_template_features()
        
        # Demonstrate different configurations
        await demonstrate_different_configurations()
        
        # Demonstrate template generation
        generated_files = await demonstrate_api_gateway_template()
        
        print("\n✨ API Gateway Template demonstration completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  ✅ Complete API Gateway generation")
        print("  ✅ Dynamic request routing and proxying")
        print("  ✅ Rate limiting with Redis backend")
        print("  ✅ Circuit breaker pattern implementation")
        print("  ✅ Load balancing with multiple algorithms")
        print("  ✅ JWT authentication and authorization")
        print("  ✅ CORS and security middleware")
        print("  ✅ Prometheus metrics and monitoring")
        print("  ✅ Distributed tracing integration")
        print("  ✅ Health checks and service discovery")
        print("  ✅ Docker and Kubernetes deployment")
        print("  ✅ Comprehensive error handling")
        print("  ✅ Production-ready configuration")
        
        if generated_files:
            print(f"\n📁 Generated {len(generated_files)} files in total")
            print("🚀 Ready to deploy API Gateway!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
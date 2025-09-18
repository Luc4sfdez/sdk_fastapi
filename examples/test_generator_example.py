"""
Example usage of Test Generator

This example demonstrates how to use the Test Generator to create
comprehensive test suites for FastAPI microservices.
"""

import asyncio
from pathlib import Path
from fastapi_microservices_sdk.templates.generators.test_generator import TestGenerator


async def main():
    """Main example function"""
    
    print("🎯 Test Generator Example")
    print("=" * 50)
    
    # Initialize the generator
    generator = TestGenerator()
    
    # Define test schema
    test_schema = {
        "project_name": "example_microservice",
        "modules": [
            {
                "name": "user_service",
                "functions": [
                    {"name": "create_user", "type": "async"},
                    {"name": "get_user", "type": "async"},
                    {"name": "update_user", "type": "async"},
                    {"name": "delete_user", "type": "async"},
                    {"name": "validate_email", "type": "sync"}
                ]
            },
            {
                "name": "auth_service",
                "functions": [
                    {"name": "authenticate", "type": "async"},
                    {"name": "generate_token", "type": "sync"},
                    {"name": "verify_token", "type": "sync"},
                    {"name": "refresh_token", "type": "async"}
                ]
            }
        ],
        "models": [
            {
                "name": "User",
                "fields": [
                    {"name": "id", "type": "integer"},
                    {"name": "email", "type": "string"},
                    {"name": "full_name", "type": "string"},
                    {"name": "is_active", "type": "boolean"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"}
                ]
            },
            {
                "name": "Item",
                "fields": [
                    {"name": "id", "type": "integer"},
                    {"name": "name", "type": "string"},
                    {"name": "description", "type": "string"},
                    {"name": "price", "type": "float"},
                    {"name": "category", "type": "string"},
                    {"name": "in_stock", "type": "boolean"}
                ]
            }
        ],
        "apis": [
            {
                "name": "users",
                "endpoints": [
                    {"path": "/api/v1/users", "method": "GET", "name": "list_users"},
                    {"path": "/api/v1/users", "method": "POST", "name": "create_user"},
                    {"path": "/api/v1/users/{user_id}", "method": "GET", "name": "get_user"},
                    {"path": "/api/v1/users/{user_id}", "method": "PUT", "name": "update_user"},
                    {"path": "/api/v1/users/{user_id}", "method": "DELETE", "name": "delete_user"}
                ]
            },
            {
                "name": "auth",
                "endpoints": [
                    {"path": "/api/v1/auth/login", "method": "POST", "name": "login"},
                    {"path": "/api/v1/auth/logout", "method": "POST", "name": "logout"},
                    {"path": "/api/v1/auth/refresh", "method": "POST", "name": "refresh_token"},
                    {"path": "/api/v1/auth/me", "method": "GET", "name": "get_current_user"}
                ]
            }
        ],
        "services": [
            {
                "name": "UserService",
                "methods": [
                    {"name": "create", "type": "async"},
                    {"name": "get_by_id", "type": "async"},
                    {"name": "get_by_email", "type": "async"},
                    {"name": "update", "type": "async"},
                    {"name": "delete", "type": "async"},
                    {"name": "list_all", "type": "async"}
                ]
            },
            {
                "name": "AuthService",
                "methods": [
                    {"name": "authenticate_user", "type": "async"},
                    {"name": "create_access_token", "type": "sync"},
                    {"name": "verify_token", "type": "sync"},
                    {"name": "get_current_user", "type": "async"}
                ]
            }
        ],
        "test_types": ["unit", "integration", "performance", "security"],
        "coverage_threshold": 95,
        "test_framework": "pytest"
    }
    
    # Define generation options
    options = {
        "output_dir": "./generated_tests",
        "generate_unit_tests": True,
        "generate_integration_tests": True,
        "generate_performance_tests": True,
        "generate_security_tests": True
    }
    
    try:
        # Generate test files
        print("🚀 Generating comprehensive test suite...")
        generated_files = generator.generate(test_schema, options)
        
        print(f"✅ Successfully generated {len(generated_files)} test files!")
        print("\n📁 Generated test files:")
        
        for file_path in sorted(generated_files):
            print(f"  - {file_path}")
        
        print(f"\n🎉 Test suite generated successfully!")
        print(f"📍 Location: {Path(options['output_dir']).absolute()}")
        
        # Display test structure
        print("\n📋 Test Structure:")
        print("  📁 tests/")
        print("    📁 unit/              # Unit tests")
        print("      📄 test_user_service.py")
        print("      📄 test_auth_service.py")
        print("      📄 test_user_model.py")
        print("      📄 test_item_model.py")
        print("      📄 test_userservice_service.py")
        print("      📄 test_authservice_service.py")
        print("    📁 integration/       # Integration tests")
        print("      📄 test_users_api.py")
        print("      📄 test_auth_api.py")
        print("      📄 test_database_integration.py")
        print("    📁 performance/       # Performance tests")
        print("      📄 test_load.py")
        print("      📄 test_benchmarks.py")
        print("    📁 security/          # Security tests")
        print("      📄 test_security.py")
        print("    📄 conftest.py        # Pytest configuration")
        print("    📄 fixtures.py        # Test fixtures")
        print("  📄 pytest.ini          # Pytest settings")
        
        # Show next steps
        print("\n🚀 Next steps:")
        print("1. Navigate to the test directory:")
        print(f"   cd {options['output_dir']}")
        print("\n2. Install test dependencies:")
        print("   pip install pytest pytest-cov pytest-asyncio pytest-benchmark")
        print("\n3. Run all tests:")
        print("   pytest")
        print("\n4. Run specific test types:")
        print("   pytest -m unit          # Unit tests only")
        print("   pytest -m integration   # Integration tests only")
        print("   pytest -m performance   # Performance tests only")
        print("   pytest -m security      # Security tests only")
        print("\n5. Generate coverage report:")
        print("   pytest --cov=app --cov-report=html")
        print("\n6. Run with verbose output:")
        print("   pytest -v")
        
    except Exception as e:
        print(f"❌ Error generating tests: {e}")
        raise


def demonstrate_test_types():
    """Demonstrate different test types"""
    
    print("\n🎯 Test Generator Features:")
    print("\n📋 Test Types Generated:")
    print("  ✅ Unit Tests - Test individual functions and methods")
    print("  ✅ Integration Tests - Test API endpoints and database")
    print("  ✅ Performance Tests - Load testing and benchmarks")
    print("  ✅ Security Tests - SQL injection, XSS, authentication")
    
    print("\n🔧 Unit Test Features:")
    print("  📦 Module testing with mocking")
    print("  🏗️ Model validation testing")
    print("  🔧 Service layer testing")
    print("  🧪 Fixtures and test data")
    print("  ⚡ Async/await support")
    print("  🎭 Mock external dependencies")
    
    print("\n🌐 Integration Test Features:")
    print("  🔗 API endpoint testing")
    print("  🗄️ Database integration testing")
    print("  🔄 Transaction rollback testing")
    print("  🏊 Connection pool testing")
    print("  📊 End-to-end workflows")
    
    print("\n⚡ Performance Test Features:")
    print("  🚀 Load testing with concurrent requests")
    print("  📊 Benchmark testing with pytest-benchmark")
    print("  💾 Memory usage profiling")
    print("  ⏱️ Response time measurement")
    print("  📈 Throughput analysis")
    
    print("\n🔒 Security Test Features:")
    print("  💉 SQL injection protection")
    print("  🛡️ XSS protection testing")
    print("  🔐 Authentication testing")
    print("  🚫 Authorization testing")
    print("  🚦 Rate limiting testing")
    print("  🔍 Sensitive data exposure")


def show_test_configuration():
    """Show test configuration options"""
    
    print("\n⚙️ Test Configuration:")
    
    print("\n📋 Schema Structure:")
    print("""
    {
        "project_name": "my_service",
        "modules": [
            {
                "name": "user_service",
                "functions": [
                    {"name": "create_user", "type": "async"},
                    {"name": "validate_email", "type": "sync"}
                ]
            }
        ],
        "models": [
            {
                "name": "User",
                "fields": [
                    {"name": "email", "type": "string"},
                    {"name": "is_active", "type": "boolean"}
                ]
            }
        ],
        "apis": [
            {
                "name": "users",
                "endpoints": [
                    {"path": "/users", "method": "GET", "name": "list_users"}
                ]
            }
        ],
        "coverage_threshold": 90,
        "test_framework": "pytest"
    }
    """)
    
    print("\n🔧 Generation Options:")
    print("""
    {
        "output_dir": "./tests",
        "generate_unit_tests": true,
        "generate_integration_tests": true,
        "generate_performance_tests": false,
        "generate_security_tests": false
    }
    """)


def show_pytest_configuration():
    """Show pytest configuration"""
    
    print("\n📋 Generated Pytest Configuration:")
    
    print("\n📄 pytest.ini:")
    print("""
    [tool:pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    addopts = 
        -v
        --cov=app
        --cov-report=term-missing
        --cov-report=html:htmlcov
        --cov-fail-under=90
    markers =
        unit: Unit tests
        integration: Integration tests
        performance: Performance tests
        security: Security tests
    """)
    
    print("\n📄 conftest.py features:")
    print("  🔧 Test client setup")
    print("  🗄️ Test database configuration")
    print("  🔐 Authentication mocking")
    print("  🎭 External service mocking")
    print("  📊 Performance profiling")
    print("  🔒 Security test fixtures")


def show_usage_examples():
    """Show usage examples"""
    
    print("\n💡 Usage Examples:")
    
    print("\n1. 🧪 Basic Unit Tests:")
    print("""
    # Generate unit tests only
    options = {
        "generate_unit_tests": True,
        "generate_integration_tests": False,
        "generate_performance_tests": False,
        "generate_security_tests": False
    }
    """)
    
    print("\n2. 🌐 Full Test Suite:")
    print("""
    # Generate all test types
    options = {
        "generate_unit_tests": True,
        "generate_integration_tests": True,
        "generate_performance_tests": True,
        "generate_security_tests": True
    }
    """)
    
    print("\n3. ⚡ Performance Focus:")
    print("""
    # Generate performance and integration tests
    options = {
        "generate_unit_tests": False,
        "generate_integration_tests": True,
        "generate_performance_tests": True,
        "generate_security_tests": False
    }
    """)
    
    print("\n4. 🔒 Security Focus:")
    print("""
    # Generate security and unit tests
    options = {
        "generate_unit_tests": True,
        "generate_integration_tests": False,
        "generate_performance_tests": False,
        "generate_security_tests": True
    }
    """)


if __name__ == "__main__":
    # Show test generator features
    demonstrate_test_types()
    
    # Show configuration
    show_test_configuration()
    
    # Show pytest configuration
    show_pytest_configuration()
    
    # Show usage examples
    show_usage_examples()
    
    # Run the main example
    print("\n🚀 Running Test Generator Example...")
    print("=" * 50)
    
    asyncio.run(main())
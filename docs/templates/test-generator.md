# Test Generator

## Overview

The Test Generator provides comprehensive automated test generation for FastAPI microservices, including unit tests, integration tests, performance tests, and security tests with intelligent mock data generation.

## Features

### Core Capabilities
- **Unit Test Generation**: Comprehensive unit test scaffolding
- **Integration Test Templates**: API and database integration tests
- **Performance Test Creation**: Load and stress testing scenarios
- **Security Test Generation**: Vulnerability and penetration tests
- **Mock Data Generation**: Intelligent test data factories
- **Pytest Configuration**: Optimized pytest setup and configuration
- **Test Coverage Analysis**: Coverage reporting and analysis
- **Fixture Management**: Reusable test fixtures and utilities

### Supported Test Types
- **Unit Tests**: Function and class-level testing
- **Integration Tests**: API endpoint and database testing
- **Performance Tests**: Load, stress, and endurance testing
- **Security Tests**: Authentication, authorization, and vulnerability testing
- **End-to-End Tests**: Complete user journey testing
- **Contract Tests**: API contract validation

## Usage

### Basic Usage

```python
from fastapi_microservices_sdk.templates.generators.test_generator import TestGenerator

# Initialize generator
generator = TestGenerator()

# Generate comprehensive test suite
test_suite = generator.generate_comprehensive_suite(
    schema=api_schema,
    config={
        "generate_unit_tests": True,
        "generate_integration_tests": True,
        "generate_performance_tests": True,
        "generate_security_tests": True,
        "mock_data_strategy": "realistic",
        "coverage_threshold": 90
    }
)
```

### CLI Usage

```bash
# Generate tests for existing project
fastapi-ms generate tests --project-path ./my-service

# Generate specific test types
fastapi-ms generate tests --types unit,integration --output ./tests

# Generate with custom configuration
fastapi-ms generate tests --config test-config.yaml
```

## Configuration

### Test Generation Configuration

```yaml
# test-config.yaml
generation:
  unit_tests:
    enabled: true
    coverage_threshold: 95
    mock_external_dependencies: true
    generate_fixtures: true
  
  integration_tests:
    enabled: true
    test_database: true
    test_api_endpoints: true
    test_message_queues: true
  
  performance_tests:
    enabled: true
    load_test_users: 100
    stress_test_duration: "5m"
    endurance_test_duration: "30m"
  
  security_tests:
    enabled: true
    test_authentication: true
    test_authorization: true
    test_input_validation: true
    test_sql_injection: true
    test_xss: true

mock_data:
  strategy: "realistic"  # realistic, random, minimal
  locale: "en_US"
  seed: 42
  custom_providers: []

pytest:
  plugins:
    - "pytest-asyncio"
    - "pytest-cov"
    - "pytest-mock"
    - "pytest-benchmark"
  markers:
    - "unit: Unit tests"
    - "integration: Integration tests"
    - "performance: Performance tests"
    - "security: Security tests"
  coverage:
    threshold: 90
    exclude_patterns:
      - "*/tests/*"
      - "*/migrations/*"
```

### Test Types Configuration

```python
test_config = {
    "unit_tests": {
        "test_models": True,
        "test_services": True,
        "test_utils": True,
        "test_validators": True,
        "mock_dependencies": True
    },
    "integration_tests": {
        "test_api_endpoints": True,
        "test_database_operations": True,
        "test_external_services": True,
        "test_message_brokers": True
    },
    "performance_tests": {
        "load_tests": {
            "users": 100,
            "duration": "5m",
            "ramp_up": "1m"
        },
        "stress_tests": {
            "max_users": 1000,
            "duration": "10m"
        }
    },
    "security_tests": {
        "authentication_tests": True,
        "authorization_tests": True,
        "input_validation_tests": True,
        "vulnerability_tests": True
    }
}
```

## Generated Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── pytest.ini                 # Pytest settings
├── unit/                      # Unit tests
│   ├── test_models.py        # Model tests
│   ├── test_services.py      # Service tests
│   ├── test_utils.py         # Utility tests
│   └── test_validators.py    # Validator tests
├── integration/              # Integration tests
│   ├── test_api.py          # API endpoint tests
│   ├── test_database.py     # Database tests
│   └── test_external.py     # External service tests
├── performance/              # Performance tests
│   ├── test_load.py         # Load tests
│   ├── test_stress.py       # Stress tests
│   └── test_endurance.py    # Endurance tests
├── security/                 # Security tests
│   ├── test_auth.py         # Authentication tests
│   ├── test_authz.py        # Authorization tests
│   └── test_vulnerabilities.py # Vulnerability tests
├── e2e/                      # End-to-end tests
│   └── test_user_journeys.py # User journey tests
├── fixtures/                 # Test fixtures
│   ├── data.py              # Test data
│   └── mocks.py             # Mock objects
└── utils/                    # Test utilities
    ├── factories.py         # Data factories
    └── helpers.py           # Test helpers
```

## Test Generation Examples

### Unit Tests

```python
# Generated unit test example
import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.models.user import User

class TestUserService:
    @pytest.fixture
    def user_service(self, mock_db):
        return UserService(db=mock_db)
    
    @pytest.fixture
    def sample_user_data(self):
        return {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }
    
    def test_create_user_success(self, user_service, sample_user_data):
        """Test successful user creation"""
        # Arrange
        expected_user = User(**sample_user_data)
        user_service.db.add.return_value = None
        user_service.db.commit.return_value = None
        
        # Act
        result = user_service.create_user(sample_user_data)
        
        # Assert
        assert result.email == expected_user.email
        assert result.username == expected_user.username
        user_service.db.add.assert_called_once()
        user_service.db.commit.assert_called_once()
    
    def test_create_user_duplicate_email(self, user_service, sample_user_data):
        """Test user creation with duplicate email"""
        # Arrange
        user_service.db.query.return_value.filter.return_value.first.return_value = User()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Email already exists"):
            user_service.create_user(sample_user_data)
```

### Integration Tests

```python
# Generated integration test example
import pytest
from httpx import AsyncClient
from app.main import app

class TestUserAPI:
    @pytest.mark.asyncio
    async def test_create_user_endpoint(self, client: AsyncClient, sample_user_data):
        """Test user creation endpoint"""
        response = await client.post("/api/v1/users", json=sample_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == sample_user_data["email"]
        assert data["username"] == sample_user_data["username"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    @pytest.mark.asyncio
    async def test_get_user_endpoint(self, client: AsyncClient, created_user):
        """Test get user endpoint"""
        response = await client.get(f"/api/v1/users/{created_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_user.id
        assert data["email"] == created_user.email
    
    @pytest.mark.asyncio
    async def test_authentication_required(self, client: AsyncClient):
        """Test that authentication is required for protected endpoints"""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401
```

### Performance Tests

```python
# Generated performance test example
import pytest
import asyncio
from httpx import AsyncClient
from locust import HttpUser, task, between

class TestUserAPIPerformance:
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_user_creation_load(self, client: AsyncClient):
        """Test user creation under load"""
        tasks = []
        for i in range(100):
            user_data = {
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "password": "password123"
            }
            tasks.append(client.post("/api/v1/users", json=user_data))
        
        responses = await asyncio.gather(*tasks)
        
        # Assert all requests succeeded
        success_count = sum(1 for r in responses if r.status_code == 201)
        assert success_count >= 95  # 95% success rate

class UserLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def create_user(self):
        user_data = {
            "email": f"user{self.environment.runner.user_count}@example.com",
            "username": f"user{self.environment.runner.user_count}",
            "password": "password123"
        }
        self.client.post("/api/v1/users", json=user_data)
    
    @task(1)
    def get_users(self):
        self.client.get("/api/v1/users")
```

### Security Tests

```python
# Generated security test example
import pytest
from httpx import AsyncClient

class TestSecurityVulnerabilities:
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, client: AsyncClient):
        """Test SQL injection protection"""
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --"
        ]
        
        for payload in malicious_payloads:
            response = await client.get(f"/api/v1/users?search={payload}")
            # Should not return 500 or expose database errors
            assert response.status_code in [200, 400, 422]
            assert "error" not in response.text.lower()
    
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_xss_protection(self, client: AsyncClient):
        """Test XSS protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            user_data = {
                "email": "test@example.com",
                "username": payload,
                "password": "password123"
            }
            response = await client.post("/api/v1/users", json=user_data)
            
            if response.status_code == 201:
                # If user created, check that payload is sanitized
                data = response.json()
                assert "<script>" not in data["username"]
                assert "javascript:" not in data["username"]
    
    @pytest.mark.security
    @pytest.mark.asyncio
    async def test_authentication_bypass(self, client: AsyncClient):
        """Test authentication bypass attempts"""
        bypass_attempts = [
            {"Authorization": "Bearer invalid_token"},
            {"Authorization": "Bearer "},
            {"Authorization": "Basic invalid"},
            {"X-API-Key": "invalid_key"}
        ]
        
        for headers in bypass_attempts:
            response = await client.get("/api/v1/users/me", headers=headers)
            assert response.status_code == 401
```

## Mock Data Generation

### Data Factories

```python
# Generated data factory example
import factory
from faker import Faker
from app.models.user import User

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    id = factory.Sequence(lambda n: n)
    email = factory.LazyAttribute(lambda obj: fake.email())
    username = factory.LazyAttribute(lambda obj: fake.user_name())
    first_name = factory.LazyAttribute(lambda obj: fake.first_name())
    last_name = factory.LazyAttribute(lambda obj: fake.last_name())
    is_active = True
    created_at = factory.LazyAttribute(lambda obj: fake.date_time())
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if extracted:
            obj.set_password(extracted)
        else:
            obj.set_password("defaultpassword123")

class AdminUserFactory(UserFactory):
    is_admin = True
    email = factory.LazyAttribute(lambda obj: f"admin.{fake.user_name()}@example.com")

# Usage in tests
def test_user_creation():
    user = UserFactory()
    admin = AdminUserFactory()
    
    assert user.email
    assert admin.is_admin
```

### Realistic Data Generation

```python
# Generated realistic data example
from faker import Faker
from faker.providers import internet, person, company

fake = Faker()

class RealisticDataGenerator:
    def __init__(self, locale="en_US", seed=None):
        self.fake = Faker(locale)
        if seed:
            Faker.seed(seed)
    
    def generate_user_data(self):
        return {
            "email": self.fake.email(),
            "username": self.fake.user_name(),
            "first_name": self.fake.first_name(),
            "last_name": self.fake.last_name(),
            "phone": self.fake.phone_number(),
            "address": {
                "street": self.fake.street_address(),
                "city": self.fake.city(),
                "state": self.fake.state(),
                "zip_code": self.fake.zipcode(),
                "country": self.fake.country()
            },
            "company": self.fake.company(),
            "job_title": self.fake.job(),
            "bio": self.fake.text(max_nb_chars=200)
        }
    
    def generate_product_data(self):
        return {
            "name": self.fake.catch_phrase(),
            "description": self.fake.text(max_nb_chars=500),
            "price": round(self.fake.random.uniform(10.0, 1000.0), 2),
            "category": self.fake.random_element([
                "Electronics", "Clothing", "Books", "Home", "Sports"
            ]),
            "sku": self.fake.ean13(),
            "weight": round(self.fake.random.uniform(0.1, 50.0), 2),
            "dimensions": {
                "length": round(self.fake.random.uniform(1.0, 100.0), 1),
                "width": round(self.fake.random.uniform(1.0, 100.0), 1),
                "height": round(self.fake.random.uniform(1.0, 100.0), 1)
            }
        }
```

## Pytest Configuration

### Generated conftest.py

```python
# Generated conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.config import settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepassword123",
        "first_name": "Test",
        "last_name": "User"
    }

@pytest.fixture
async def created_user(client, sample_user_data):
    """Create a user for testing."""
    response = await client.post("/api/v1/users", json=sample_user_data)
    return response.json()

@pytest.fixture
async def authenticated_client(client, created_user):
    """Create an authenticated client."""
    login_data = {
        "username": created_user["email"],
        "password": "securepassword123"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    token = response.json()["access_token"]
    
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

### Generated pytest.ini

```ini
# Generated pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra
    -q
    --strict-markers
    --strict-config
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=90
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
    external: Tests that require external services
asyncio_mode = auto
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

## Advanced Features

### Custom Test Templates

```python
# Custom test template
class CustomTestTemplate:
    def __init__(self, name, template_content):
        self.name = name
        self.template_content = template_content
    
    def generate(self, context):
        return self.template_content.format(**context)

# Register custom template
generator.register_template("custom_api_test", CustomTestTemplate(
    name="custom_api_test",
    template_content="""
def test_{endpoint_name}(client, {fixtures}):
    '''Test {endpoint_description}'''
    response = client.{method}('{path}', {request_data})
    assert response.status_code == {expected_status}
    {assertions}
"""
))
```

### Test Coverage Analysis

```python
# Coverage analysis integration
from coverage import Coverage

class CoverageAnalyzer:
    def __init__(self):
        self.cov = Coverage()
    
    def analyze_coverage(self, test_results):
        """Analyze test coverage and generate reports."""
        self.cov.start()
        # Run tests
        self.cov.stop()
        
        coverage_data = self.cov.get_data()
        return {
            "total_coverage": self.cov.report(),
            "missing_lines": coverage_data.lines_missing(),
            "covered_lines": coverage_data.lines_covered()
        }
```

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Keep tests independent and isolated

### Mock Strategy
- Mock external dependencies
- Use realistic test data
- Avoid over-mocking
- Test both success and failure scenarios

### Performance Testing
- Set realistic load targets
- Monitor resource usage
- Test different scenarios
- Include ramp-up and ramp-down

### Security Testing
- Test all input validation
- Check authentication and authorization
- Test for common vulnerabilities
- Include edge cases and boundary conditions

## Integration

### CI/CD Integration

```yaml
# GitHub Actions example
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
        with:
          file: ./coverage.xml
```

### IDE Integration

The test generator integrates with popular IDEs:
- **VS Code**: Test discovery and execution
- **PyCharm**: Integrated test runner
- **Vim/Neovim**: Command-line integration

## Troubleshooting

### Common Issues

1. **Import Errors**: Check Python path and dependencies
2. **Database Errors**: Verify test database configuration
3. **Async Issues**: Ensure proper async/await usage
4. **Mock Failures**: Check mock setup and expectations

### Debug Mode

Enable debug output:

```bash
pytest -v --tb=long --capture=no
```

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Factory Boy Documentation](https://factoryboy.readthedocs.io/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [Locust Documentation](https://locust.io/)
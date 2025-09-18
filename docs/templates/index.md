# Templates Documentation

## Overview

The FastAPI Microservices SDK provides a comprehensive collection of templates for rapid microservice development. These templates implement industry best practices and proven architectural patterns to accelerate development while ensuring high quality and maintainability.

## Available Templates

### Service Templates

#### 1. [Microservice Base Template](./microservice-base-template.md)
Basic FastAPI microservice with essential components and configurations.

**Features:**
- FastAPI application setup
- Configuration management
- Health checks
- Basic middleware
- Docker configuration

#### 2. [Auth Service Template](./auth-service-template.md)
Complete authentication and authorization service with JWT, OAuth2, and user management.

**Features:**
- JWT authentication
- OAuth2 providers (Google, GitHub, Facebook)
- User registration and management
- Role-based access control (RBAC)
- Password policies and validation
- Email verification

#### 3. [API Gateway Template](./api-gateway-template.md)
Production-ready API Gateway with routing, middleware, and security features.

**Features:**
- Request routing and load balancing
- Rate limiting and throttling
- Authentication and authorization
- Request/response transformation
- Circuit breaker pattern
- Monitoring and logging

#### 4. [Data Service Template](./data-service-template.md)
Database-integrated service with ORM, migrations, and caching.

**Features:**
- SQLAlchemy ORM integration
- Database migrations with Alembic
- Multiple database support (PostgreSQL, MySQL, MongoDB)
- Caching layer with Redis
- Connection pooling
- Query optimization

#### 5. [Event Service Template](./event-service-template.md)
Event-driven microservice with Event Sourcing, CQRS, and Saga patterns.

**Features:**
- Event Sourcing implementation
- CQRS (Command Query Responsibility Segregation)
- Saga pattern for distributed transactions
- Message broker integration (Kafka, RabbitMQ, Redis, NATS)
- Event store support (PostgreSQL, MongoDB, EventStore)
- Snapshot management and event replay

#### 6. [Monitoring Service Template](./monitoring-service-template.md)
Comprehensive monitoring and observability service.

**Features:**
- Prometheus metrics collection
- Grafana dashboard integration
- AlertManager with notification channels
- Custom metrics from multiple sources
- Health check aggregation
- Performance profiling and capacity planning

### Development Tools

#### 7. [Project Creation CLI](./project-creation-cli.md)
Interactive wizard for creating FastAPI microservice projects.

**Features:**
- Interactive project creation wizard
- Template selection and browsing
- Service integration configuration
- Deployment setup (Docker, Kubernetes, CI/CD)
- Git integration and automated setup
- Project validation with auto-fix

#### 8. [Test Generator](./test-generator.md)
Comprehensive automated test generation for FastAPI microservices.

**Features:**
- Unit test scaffolding
- Integration test templates
- Performance test creation
- Security test generation
- Mock data generation with realistic factories
- Pytest configuration optimization

### Code Generators

#### 9. [API Generator](./api-generator.md)
Automated API endpoint generation from schemas and specifications.

**Features:**
- OpenAPI/Swagger schema generation
- CRUD endpoint scaffolding
- Request/response validation
- Documentation generation
- Type hints and annotations

#### 10. [CRUD Generator](./crud-generator.md)
Database CRUD operations generator with repository pattern.

**Features:**
- Repository pattern implementation
- Generic CRUD operations
- Query builders and filters
- Pagination support
- Soft delete functionality

## Template Categories

### By Use Case

#### 🔐 Authentication & Security
- [Auth Service Template](./auth-service-template.md)
- [API Gateway Template](./api-gateway-template.md)

#### 📊 Data & Storage
- [Data Service Template](./data-service-template.md)
- [CRUD Generator](./crud-generator.md)

#### 🔄 Event-Driven Architecture
- [Event Service Template](./event-service-template.md)

#### 📈 Observability & Monitoring
- [Monitoring Service Template](./monitoring-service-template.md)

#### 🛠️ Development Tools
- [Project Creation CLI](./project-creation-cli.md)
- [Test Generator](./test-generator.md)
- [API Generator](./api-generator.md)

### By Complexity Level

#### 🟢 Beginner
- [Microservice Base Template](./microservice-base-template.md)
- [CRUD Generator](./crud-generator.md)

#### 🟡 Intermediate
- [Auth Service Template](./auth-service-template.md)
- [Data Service Template](./data-service-template.md)
- [API Generator](./api-generator.md)

#### 🔴 Advanced
- [Event Service Template](./event-service-template.md)
- [API Gateway Template](./api-gateway-template.md)
- [Monitoring Service Template](./monitoring-service-template.md)

## Quick Start

### Using the CLI

```bash
# Install the SDK
pip install fastapi-microservices-sdk

# Create a new project interactively
fastapi-ms create

# Create with specific template
fastapi-ms create --name my-service --template auth_service

# List available templates
fastapi-ms templates list
```

### Programmatic Usage

```python
from fastapi_microservices_sdk.templates import TemplateManager

# Initialize template manager
manager = TemplateManager()

# Get available templates
templates = manager.list_templates()

# Generate service from template
service = manager.generate_service(
    template_name="auth_service",
    variables={
        "service_name": "my_auth_service",
        "database_type": "postgresql",
        "enable_oauth2": True
    }
)
```

## Template Structure

### Standard Template Components

Each template includes the following components:

```
template/
├── app/                    # Application code
│   ├── main.py            # FastAPI application
│   ├── config.py          # Configuration
│   ├── models/            # Data models
│   ├── services/          # Business logic
│   ├── api/               # API routes
│   └── utils/             # Utilities
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Test configuration
├── docker/               # Docker configuration
│   ├── Dockerfile        # Container definition
│   └── docker-compose.yml # Multi-service setup
├── k8s/                  # Kubernetes manifests
├── docs/                 # Documentation
├── requirements.txt      # Dependencies
└── README.md            # Project documentation
```

### Template Variables

Templates support customization through variables:

```yaml
# Template variables example
service_name: "my_service"
service_description: "My awesome microservice"
service_version: "1.0.0"
author: "Developer Name"
database_type: "postgresql"
enable_authentication: true
enable_monitoring: true
```

## Best Practices

### Template Selection

1. **Start Simple**: Begin with basic templates and add complexity as needed
2. **Consider Architecture**: Choose templates that align with your architecture
3. **Evaluate Dependencies**: Consider the dependencies and infrastructure requirements
4. **Plan for Scale**: Select templates that can grow with your needs

### Customization

1. **Use Variables**: Leverage template variables for customization
2. **Extend Templates**: Create custom templates based on existing ones
3. **Follow Conventions**: Maintain consistent naming and structure
4. **Document Changes**: Document any customizations for team members

### Development Workflow

1. **Generate Project**: Use CLI or programmatic interface
2. **Review Generated Code**: Understand the generated structure
3. **Customize Configuration**: Adjust settings for your environment
4. **Add Business Logic**: Implement your specific requirements
5. **Test Thoroughly**: Use generated tests as a starting point

## Advanced Usage

### Custom Templates

Create custom templates for your organization:

```python
from fastapi_microservices_sdk.templates import BaseTemplate

class CustomTemplate(BaseTemplate):
    name = "custom_service"
    description = "Custom service template"
    
    def generate_files(self, variables, output_dir):
        # Custom generation logic
        pass

# Register custom template
manager.register_template(CustomTemplate())
```

### Template Composition

Combine multiple templates:

```python
# Compose templates
composed_service = manager.compose_templates([
    "microservice_base",
    "auth_service",
    "monitoring_service"
], variables)
```

### CI/CD Integration

Integrate templates with CI/CD pipelines:

```yaml
# GitHub Actions example
name: Generate Service
on:
  workflow_dispatch:
    inputs:
      template:
        description: 'Template name'
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - name: Generate Service
        run: |
          fastapi-ms create --template ${{ github.event.inputs.template }} \
            --config service-config.yaml --no-interactive
```

## Migration Guide

### Upgrading Templates

When upgrading to newer template versions:

1. **Review Changes**: Check changelog for breaking changes
2. **Backup Project**: Create backup before upgrading
3. **Test Thoroughly**: Run full test suite after upgrade
4. **Update Dependencies**: Ensure all dependencies are compatible

### Legacy Template Support

For projects using older templates:

1. **Gradual Migration**: Migrate components incrementally
2. **Compatibility Layer**: Use compatibility shims if needed
3. **Documentation**: Document migration steps for team
4. **Testing**: Ensure functionality remains intact

## Troubleshooting

### Common Issues

1. **Template Not Found**: Check template name and availability
2. **Variable Errors**: Verify required variables are provided
3. **Generation Failures**: Check output directory permissions
4. **Dependency Conflicts**: Resolve version conflicts

### Debug Mode

Enable debug output for troubleshooting:

```bash
fastapi-ms create --template my_template --debug --verbose
```

### Getting Help

- **Documentation**: Check template-specific documentation
- **Examples**: Review example projects and configurations
- **Community**: Join community forums and discussions
- **Issues**: Report bugs and feature requests on GitHub

## Contributing

### Creating Templates

1. **Follow Standards**: Use established patterns and conventions
2. **Include Tests**: Provide comprehensive test coverage
3. **Document Thoroughly**: Include detailed documentation
4. **Provide Examples**: Include working examples

### Template Guidelines

1. **Modularity**: Design templates to be composable
2. **Flexibility**: Support customization through variables
3. **Quality**: Follow coding standards and best practices
4. **Maintenance**: Keep templates updated with latest practices

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [Domain-Driven Design](https://domainlanguage.com/ddd/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
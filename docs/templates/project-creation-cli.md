# Project Creation CLI

## Overview

The Project Creation CLI provides an interactive wizard for creating FastAPI microservice projects with comprehensive template selection, service integration, and deployment configuration.

## Features

### Core Capabilities
- **Interactive Wizard**: Step-by-step project creation process
- **Template Selection**: Browse and select from available templates
- **Service Integration**: Automatic integration of auth, gateway, monitoring services
- **Deployment Configuration**: Docker, Kubernetes, and CI/CD setup
- **Project Validation**: Automatic validation with auto-fix capabilities
- **Git Integration**: Automated Git repository setup
- **Multi-format Output**: Support for table, JSON, and YAML formats
- **Extensible Architecture**: Plugin system for custom templates

### Supported Templates
- **Microservice Base**: Basic FastAPI microservice
- **Auth Service**: Authentication and authorization service
- **API Gateway**: API gateway with routing and middleware
- **Data Service**: Database-integrated service
- **Event Service**: Event-driven service with CQRS
- **Monitoring Service**: Observability and monitoring service

## Usage

### Interactive Mode

```bash
# Start interactive wizard
fastapi-ms create

# Interactive wizard will guide you through:
# 1. Project Information
# 2. Template Selection
# 3. Service Integration
# 4. Deployment Configuration
# 5. Project Generation
```

### Non-Interactive Mode

```bash
# Create with specific template
fastapi-ms create --name my-service --template auth_service --no-interactive

# Create with custom configuration
fastapi-ms create --name my-service --template event_service \
  --config config.yaml --no-interactive
```

### Template Browsing

```bash
# List available templates
fastapi-ms templates list

# Show template details
fastapi-ms templates show auth_service

# Search templates
fastapi-ms templates search --tag authentication
```

## CLI Commands

### Project Creation

```bash
# Interactive creation
fastapi-ms create

# Non-interactive creation
fastapi-ms create --name SERVICE_NAME --template TEMPLATE_NAME [OPTIONS]

# Create from configuration file
fastapi-ms create --config config.yaml
```

### Template Management

```bash
# List all templates
fastapi-ms templates list [--format table|json|yaml]

# Show template details
fastapi-ms templates show TEMPLATE_NAME

# Search templates by tag or keyword
fastapi-ms templates search --tag TAG_NAME
fastapi-ms templates search --keyword KEYWORD

# Validate template
fastapi-ms templates validate TEMPLATE_NAME
```

### Project Management

```bash
# Validate existing project
fastapi-ms validate [PROJECT_PATH]

# Update project dependencies
fastapi-ms update [PROJECT_PATH]

# Generate additional components
fastapi-ms generate --type component --name COMPONENT_NAME
```

## Configuration

### Project Configuration File

```yaml
# project-config.yaml
project:
  name: "my-microservice"
  description: "My awesome microservice"
  version: "1.0.0"
  author: "Developer Name"
  email: "developer@example.com"

template:
  name: "auth_service"
  variables:
    database_type: "postgresql"
    enable_jwt: true
    enable_oauth2: true

services:
  integration:
    - name: "api_gateway"
      enabled: true
    - name: "monitoring"
      enabled: true

deployment:
  docker:
    enabled: true
    base_image: "python:3.11-slim"
  kubernetes:
    enabled: true
    namespace: "default"
  ci_cd:
    provider: "github_actions"
    enabled: true

git:
  initialize: true
  remote_url: "https://github.com/user/repo.git"
  initial_commit: true
```

### CLI Configuration

```yaml
# ~/.fastapi-ms/config.yaml
defaults:
  author: "Default Author"
  email: "author@example.com"
  template: "microservice"
  output_format: "table"

templates:
  search_paths:
    - "~/.fastapi-ms/templates"
    - "/usr/local/share/fastapi-ms/templates"

output:
  colors: true
  verbose: false
```

## Interactive Wizard Flow

### Step 1: Project Information

```
🚀 FastAPI Microservice Project Creator

📋 Project Information
? Project name: my-awesome-service
? Description: My awesome microservice for handling orders
? Version (1.0.0): 
? Author: John Developer
? Email: john@example.com
```

### Step 2: Template Selection

```
📦 Template Selection

Available templates:
  1. microservice        - Basic FastAPI microservice
  2. auth_service       - Authentication service
  3. api_gateway        - API Gateway service
  4. data_service       - Database-integrated service
  5. event_service      - Event-driven service
  6. monitoring_service - Monitoring service

? Select template (1-6): 2

✅ Selected: auth_service
📄 Description: Complete authentication service with JWT, OAuth2, and user management
🏷️  Tags: authentication, security, jwt, oauth2
```

### Step 3: Template Configuration

```
⚙️  Template Configuration

🔧 Authentication Service Configuration
? Database type (postgresql/mysql/mongodb): postgresql
? Enable JWT authentication? (Y/n): Y
? Enable OAuth2 providers? (Y/n): Y
? OAuth2 providers (google,github,facebook): google,github
? Enable user registration? (Y/n): Y
? Enable email verification? (Y/n): Y
? Password complexity requirements? (Y/n): Y
```

### Step 4: Service Integration

```
🔗 Service Integration

Available integrations:
  ☐ API Gateway - Route requests and handle middleware
  ☐ Monitoring - Metrics, logging, and health checks
  ☐ Message Broker - Async communication
  ☐ Cache Service - Redis caching layer

? Select integrations (space to select, enter to continue):
  ☑ API Gateway
  ☑ Monitoring
  ☐ Message Broker
  ☐ Cache Service
```

### Step 5: Deployment Configuration

```
🚀 Deployment Configuration

📦 Docker Configuration
? Enable Docker? (Y/n): Y
? Base image (python:3.11-slim): 
? Expose port (8000): 

☸️  Kubernetes Configuration
? Enable Kubernetes manifests? (Y/n): Y
? Namespace (default): 
? Replicas (3): 
? Resource limits? (Y/n): Y

🔄 CI/CD Configuration
? Enable CI/CD? (Y/n): Y
? Provider (github_actions/gitlab_ci/jenkins): github_actions
? Include deployment pipeline? (Y/n): Y
```

### Step 6: Git Integration

```
📚 Git Integration

? Initialize Git repository? (Y/n): Y
? Remote repository URL (optional): https://github.com/user/my-awesome-service.git
? Create initial commit? (Y/n): Y
? Default branch name (main): 
```

### Step 7: Project Generation

```
🎉 Generating Project...

✅ Created project structure
✅ Generated authentication service
✅ Configured PostgreSQL integration
✅ Added API Gateway integration
✅ Added monitoring integration
✅ Created Docker configuration
✅ Created Kubernetes manifests
✅ Generated GitHub Actions workflow
✅ Initialized Git repository
✅ Created initial commit

🎯 Project created successfully!

📁 Location: ./my-awesome-service
🚀 Next steps:
   cd my-awesome-service
   docker-compose up --build
```

## Generated Project Structure

```
my-awesome-service/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration
│   ├── auth/                  # Authentication module
│   ├── api/                   # API routes
│   ├── models/                # Data models
│   ├── services/              # Business logic
│   └── utils/                 # Utilities
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py           # Test configuration
├── docker/
│   ├── Dockerfile            # Docker configuration
│   └── docker-compose.yml   # Multi-service setup
├── k8s/
│   ├── deployment.yaml       # Kubernetes deployment
│   ├── service.yaml         # Kubernetes service
│   └── configmap.yaml       # Configuration
├── .github/
│   └── workflows/
│       └── ci-cd.yml        # GitHub Actions
├── docs/
│   ├── README.md            # Project documentation
│   └── api.md               # API documentation
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project configuration
└── .env.example             # Environment variables
```

## Advanced Features

### Custom Templates

```python
# Create custom template
from fastapi_microservices_sdk.templates.cli.project_creator import ProjectCreator

creator = ProjectCreator()

# Register custom template
creator.register_template("my_template", {
    "name": "my_template",
    "description": "My custom template",
    "variables": {
        "custom_var": {
            "type": "string",
            "description": "Custom variable",
            "default": "default_value"
        }
    }
})
```

### Plugin System

```python
# Create CLI plugin
class MyPlugin:
    def __init__(self):
        self.name = "my_plugin"
    
    def register_commands(self, cli):
        @cli.command()
        def my_command():
            """My custom command"""
            click.echo("Hello from my plugin!")
    
    def register_templates(self, registry):
        registry.register("my_template", MyTemplate())

# Register plugin
creator.register_plugin(MyPlugin())
```

### Batch Operations

```bash
# Create multiple projects from configuration
fastapi-ms batch create --config batch-config.yaml

# Update multiple projects
fastapi-ms batch update --pattern "*/pyproject.toml"
```

## Configuration Options

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | Configuration file path | None |
| `--output-dir` | Output directory | Current directory |
| `--format` | Output format (table/json/yaml) | table |
| `--verbose` | Verbose output | False |
| `--no-interactive` | Disable interactive mode | False |

### Create Command Options

| Option | Description | Default |
|--------|-------------|---------|
| `--name` | Project name | Required |
| `--template` | Template name | microservice |
| `--author` | Project author | From config |
| `--email` | Author email | From config |
| `--version` | Project version | 1.0.0 |
| `--description` | Project description | None |

### Template Options

| Option | Description | Default |
|--------|-------------|---------|
| `--tag` | Filter by tag | None |
| `--keyword` | Search keyword | None |
| `--category` | Filter by category | None |

## Best Practices

### Project Organization
- Use meaningful project names
- Include comprehensive descriptions
- Follow semantic versioning
- Maintain consistent structure

### Template Selection
- Choose templates that match your use case
- Consider future scalability needs
- Review template documentation
- Test generated projects

### Configuration Management
- Use configuration files for complex setups
- Store sensitive data in environment variables
- Version control configuration files
- Document configuration options

### Development Workflow
- Initialize Git repositories
- Set up CI/CD pipelines
- Include comprehensive tests
- Document APIs and services

## Troubleshooting

### Common Issues

1. **Template Not Found**: Check template name and availability
2. **Permission Errors**: Ensure write permissions in output directory
3. **Git Errors**: Verify Git configuration and remote URLs
4. **Dependency Conflicts**: Check Python version and dependencies

### Debug Mode

Enable debug output:

```bash
fastapi-ms create --verbose --debug
```

### Validation

Validate generated projects:

```bash
fastapi-ms validate ./my-project
```

## Examples

### Basic Microservice

```bash
fastapi-ms create --name user-service --template microservice \
  --author "John Doe" --email "john@example.com" --no-interactive
```

### Authentication Service

```bash
fastapi-ms create --name auth-service --template auth_service \
  --config auth-config.yaml --no-interactive
```

### Event-Driven Service

```bash
fastapi-ms create --name order-service --template event_service \
  --no-interactive
```

## Integration

### IDE Integration

The CLI can be integrated with popular IDEs:

- **VS Code**: Extension for project creation
- **PyCharm**: Plugin for template management
- **Vim/Neovim**: Command-line integration

### CI/CD Integration

```yaml
# GitHub Actions example
name: Create Microservice
on:
  workflow_dispatch:
    inputs:
      service_name:
        description: 'Service name'
        required: true
      template:
        description: 'Template name'
        required: true

jobs:
  create:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install CLI
        run: pip install fastapi-microservices-sdk
      - name: Create Service
        run: |
          fastapi-ms create --name ${{ github.event.inputs.service_name }} \
            --template ${{ github.event.inputs.template }} --no-interactive
```

## References

- [Click Documentation](https://click.palletsprojects.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
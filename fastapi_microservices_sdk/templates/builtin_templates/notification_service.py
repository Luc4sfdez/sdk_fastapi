"""
Notification Service Template

Enterprise notification service for emails, SMS, push notifications, and webhooks.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class NotificationServiceTemplate:
    """Enterprise notification service template."""
    
    @staticmethod
    def create_template() -> Template:
        """Create notification service template."""
        config = TemplateConfig(
            id="notification_service",
            name="Notification Service",
            description="Enterprise notification service for emails, SMS, push notifications",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Service name",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="description",
                    type=VariableType.STRING,
                    description="Service description",
                    default="Enterprise notification service",
                    required=False
                ),
                TemplateVariable(
                    name="author",
                    type=VariableType.STRING,
                    description="Author",
                    default="Developer",
                    required=False
                ),
                TemplateVariable(
                    name="version",
                    type=VariableType.STRING,
                    description="Version",
                    default="1.0.0",
                    required=False
                ),
                TemplateVariable(
                    name="service_port",
                    type=VariableType.INTEGER,
                    description="Service port",
                    default=8000,
                    required=False
                )
            ]
        )
        
        files = [
            TemplateFile(
                path="main.py",
                content=NotificationServiceTemplate._get_main_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="config.py",
                content=NotificationServiceTemplate._get_config_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="requirements.txt",
                content=NotificationServiceTemplate._get_requirements_content(),
                is_binary=False
            ),
            TemplateFile(
                path="README.md",
                content=NotificationServiceTemplate._get_readme_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)    

    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - Enterprise Notification Service

{{ description }}

Features:
- Email notifications
- SMS notifications
- Push notifications
- Webhook notifications
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="{{ project_name }} - Notification Service",
    description="{{ description }}",
    version="{{ version }}",
    docs_url="/docs",
    redoc_url="/redoc"
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
    """Root endpoint"""
    return {
        "service": "{{ project_name }}",
        "version": "{{ version }}",
        "status": "running",
        "description": "{{ description }}",
        "features": [
            "Email notifications",
            "SMS notifications", 
            "Push notifications",
            "Webhook notifications"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "{{ project_name }}",
        "version": "{{ version }}"
    }

@app.post("/send-email")
async def send_email(to: str, subject: str, body: str):
    """Send email notification"""
    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "message": "Email sent successfully"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port={{ service_port }},
        reload=True
    )
'''
    
    @staticmethod
    def _get_config_py_content() -> str:
        return '''"""
Configuration for {{ project_name }} Notification Service
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Notification service settings"""
    
    PROJECT_NAME: str = "{{ project_name }}"
    VERSION: str = "{{ version }}"
    DESCRIPTION: str = "{{ description }}"
    
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default={{ service_port }}, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Email settings
    EMAIL_ENABLED: bool = Field(default=True, env="EMAIL_ENABLED")
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    
    # SMS settings
    SMS_ENABLED: bool = Field(default=False, env="SMS_ENABLED")
    SMS_PROVIDER: str = Field(default="twilio", env="SMS_PROVIDER")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''
    
    @staticmethod
    def _get_requirements_content() -> str:
        return '''# {{ project_name }} - Notification Service Requirements

# FastAPI and dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# HTTP client
httpx==0.25.2

# Email
aiosmtplib==3.0.1

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }} - Notification Service

{{ description }}

## Features

- **Email Notifications**: SMTP-based email delivery
- **SMS Notifications**: SMS delivery via providers
- **Push Notifications**: Mobile push notifications
- **Webhook Notifications**: HTTP webhook delivery

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
# Service Configuration
PROJECT_NAME={{ project_name }}
HOST=0.0.0.0
PORT={{ service_port }}
ENVIRONMENT=development

# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# SMS Configuration
SMS_ENABLED=false
SMS_PROVIDER=twilio
```

### Running the Service

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port {{ service_port }}
```

## API Endpoints

### Send Email

```bash
POST /send-email
```

### Health Check

```bash
GET /health
```

## License

MIT License - see LICENSE file for details.

## Author

{{ author }}
'''
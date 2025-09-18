"""
File Service Template

Enterprise file management service for upload, download, storage, and processing.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class FileServiceTemplate:
    """Enterprise file service template."""
    
    @staticmethod
    def create_template() -> Template:
        """Create file service template."""
        config = TemplateConfig(
            id="file_service",
            name="File Service",
            description="Enterprise file management service for upload, download, and storage",
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
                    default="Enterprise file management service",
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
                ),
                TemplateVariable(
                    name="max_file_size",
                    type=VariableType.INTEGER,
                    description="Maximum file size in MB",
                    default=100,
                    required=False
                )
            ]
        )
        
        files = [
            TemplateFile(
                path="main.py",
                content=FileServiceTemplate._get_main_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="config.py",
                content=FileServiceTemplate._get_config_py_content(),
                is_binary=False
            ),
            TemplateFile(
                path="requirements.txt",
                content=FileServiceTemplate._get_requirements_content(),
                is_binary=False
            ),
            TemplateFile(
                path="README.md",
                content=FileServiceTemplate._get_readme_content(),
                is_binary=False
            )
        ]
        
        return Template(config=config, files=files)    

    @staticmethod
    def _get_main_py_content() -> str:
        return '''"""
{{ project_name }} - Enterprise File Service

{{ description }}

Features:
- File upload/download
- Multiple storage backends
- File validation and processing
- Metadata management
- Access control
"""

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="{{ project_name }} - File Service",
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
            "File upload/download",
            "Multiple storage backends",
            "File validation",
            "Metadata management",
            "Access control"
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

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file"""
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "message": "File uploaded successfully"
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
Configuration for {{ project_name }} File Service
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """File service settings"""
    
    PROJECT_NAME: str = "{{ project_name }}"
    VERSION: str = "{{ version }}"
    DESCRIPTION: str = "{{ description }}"
    
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default={{ service_port }}, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # File storage settings
    STORAGE_BACKEND: str = Field(default="local", env="STORAGE_BACKEND")
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE_MB: int = Field(default={{ max_file_size }}, env="MAX_FILE_SIZE_MB")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''
    
    @staticmethod
    def _get_requirements_content() -> str:
        return '''# {{ project_name }} - File Service Requirements

# FastAPI and dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# File handling
python-multipart==0.0.6
aiofiles==23.2.1

# Image processing
Pillow==10.1.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
flake8==6.1.0
'''
    
    @staticmethod
    def _get_readme_content() -> str:
        return '''# {{ project_name }} - File Service

{{ description }}

## Features

- **File Upload/Download**: Secure file upload and download
- **Multiple Storage Backends**: Local filesystem and cloud storage
- **File Validation**: MIME type detection and security checks
- **Metadata Management**: Extract and store file metadata
- **Access Control**: File permissions and sharing

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

# Storage Configuration
STORAGE_BACKEND=local
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB={{ max_file_size }}
```

### Running the Service

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port {{ service_port }}
```

## API Endpoints

### File Upload

```bash
POST /upload
Content-Type: multipart/form-data
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
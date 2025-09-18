"""
OCR Service Template

Template para crear servicios de OCR (Optical Character Recognition)
"""

from typing import Dict, Any
from pathlib import Path

from ..engine import Template, TemplateFile
from ..config import TemplateConfig, TemplateVariable, VariableType, TemplateCategory


class OCRServiceTemplate:
    """Template para servicio de OCR."""
    
    @staticmethod
    def create_template() -> Template:
        """Crear template de OCR service."""
        config = TemplateConfig(
            id="ocr_service",
            name="OCR Service",
            description="Servicio de OCR para extraer texto de imágenes y documentos",
            category=TemplateCategory.CUSTOM,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            variables=[
                TemplateVariable(
                    name="project_name",
                    type=VariableType.STRING,
                    description="Nombre del servicio OCR",
                    required=True,
                    validation_pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$'
                ),
                TemplateVariable(
                    name="port",
                    type=VariableType.INTEGER,
                    description="Puerto del servicio",
                    default=8006,
                    required=False
                ),
                TemplateVariable(
                    name="max_file_size",
                    type=VariableType.INTEGER,
                    description="Tamaño máximo de archivo en MB",
                    default=10,
                    required=False
                ),
                TemplateVariable(
                    name="supported_languages",
                    type=VariableType.STRING,
                    description="Idiomas soportados (separados por coma)",
                    default="spa,eng,fra,deu",
                    required=False
                ),
                TemplateVariable(
                    name="include_web_interface",
                    type=VariableType.BOOLEAN,
                    description="Incluir interfaz web",
                    default=True,
                    required=False
                )
            ]
        )
        
        files = [
            # Archivo principal
            TemplateFile(
                path="main.py",
                content=_get_main_py_content(),
                description="Aplicación principal FastAPI con OCR"
            ),
            
            # Configuración
            TemplateFile(
                path="requirements.txt",
                content=_get_requirements_content(),
                description="Dependencias Python"
            ),
            
            # Docker
            TemplateFile(
                path="Dockerfile",
                content=_get_dockerfile_content(),
                description="Configuración Docker"
            ),
            
            # Documentación
            TemplateFile(
                path="README.md",
                content=_get_readme_content(),
                description="Documentación del servicio"
            ),
            
            # Interfaz web (condicional)
            TemplateFile(
                path="static/index.html",
                content=_get_web_interface_content(),
                description="Interfaz web para OCR",
                condition="include_web_interface"
            ),
            
            # Tests
            TemplateFile(
                path="test_ocr_service.py",
                content=_get_test_content(),
                description="Tests del servicio OCR"
            )
        ]
        
        return Template(config=config, files=files)


def _get_main_py_content() -> str:
    """Contenido del archivo main.py"""
    return '''"""
{{project_name}} - OCR Service

Servicio de OCR para extraer texto de imágenes y documentos
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
{% if include_web_interface %}
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
{% endif %}
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import json
from datetime import datetime
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear FastAPI app
app = FastAPI(
    title="{{project_name}}",
    description="Servicio de OCR para extraer texto de imágenes y documentos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración
UPLOAD_DIR = Path("./uploads")
RESULTS_DIR = Path("./results")
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"}
MAX_FILE_SIZE = {{max_file_size}} * 1024 * 1024  # {{max_file_size}}MB
SUPPORTED_LANGUAGES = "{{supported_languages}}".split(",")

# Crear directorios
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
{% if include_web_interface %}
Path("./static").mkdir(exist_ok=True)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")
{% endif %}

# Modelos Pydantic
class OCRRequest(BaseModel):
    file_id: str
    language: str = "spa"
    extract_tables: bool = False
    extract_metadata: bool = True

class OCRResult(BaseModel):
    id: str
    file_id: str
    filename: str
    text: str
    confidence: float
    language: str
    pages: int
    processing_time: float
    metadata: Dict[str, Any]
    created_at: datetime

# Storage en memoria (usar DB en producción)
ocr_results = {}
ocr_status = {}
uploaded_files = {}

# Función OCR simulada
def extract_text_from_image(file_path: Path, language: str = "spa") -> Dict[str, Any]:
    """Extraer texto de imagen usando OCR"""
    import time
    time.sleep(2)  # Simular procesamiento
    
    # Texto simulado
    text = f"Texto extraído de {file_path.name}\\n\\nEste es un ejemplo de OCR.\\nConfianza: 95.2%"
    
    return {
        "text": text,
        "confidence": 95.2,
        "pages": 1,
        "processing_time": 2.1,
        "metadata": {
            "file_size": file_path.stat().st_size,
            "format": file_path.suffix,
            "dimensions": "1920x1080",
            "dpi": 300
        }
    }

# Endpoints
{% if include_web_interface %}
@app.get("/")
async def serve_web_interface():
    """Servir interfaz web"""
    return FileResponse("static/index.html")

@app.get("/api")
{% else %}
@app.get("/")
{% endif %}
async def api_info():
    """Información de la API"""
    return {
        "service": "{{project_name}}",
        "version": "1.0.0",
        "status": "running",
        "description": "Servicio de OCR para extraer texto de imágenes y documentos",
        "supported_formats": list(SUPPORTED_FORMATS),
        "supported_languages": SUPPORTED_LANGUAGES,
        "max_file_size": f"{{max_file_size}}MB"
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "{{project_name}}",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Subir archivo para OCR"""
    # Implementación de upload
    pass

@app.post("/process")
async def process_ocr(request: OCRRequest, background_tasks: BackgroundTasks):
    """Procesar OCR"""
    # Implementación de procesamiento
    pass

# Más endpoints...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port={{port}},
        reload=True
    )
'''


def _get_requirements_content() -> str:
    """Contenido de requirements.txt"""
    return '''fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic[email]==2.5.0
python-multipart==0.0.6
pillow==10.1.0
# Para OCR real:
# pytesseract==0.3.10
# easyocr==1.7.0
# opencv-python==4.8.1.78
'''


def _get_dockerfile_content() -> str:
    """Contenido del Dockerfile"""
    return '''FROM python:3.11-slim

WORKDIR /app

# Instalar Tesseract OCR
RUN apt-get update && apt-get install -y \\
    tesseract-ocr \\
    tesseract-ocr-spa \\
    tesseract-ocr-eng \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads results static

EXPOSE {{port}}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{{port}}"]
'''


def _get_readme_content() -> str:
    """Contenido del README.md"""
    return '''# {{project_name}}

Servicio de OCR para extraer texto de imágenes y documentos.

## Características

- Extracción de texto de imágenes
- Soporte múltiples formatos: JPG, PNG, PDF, TIFF, BMP
- Procesamiento asíncrono
- Múltiples idiomas: {{supported_languages}}
{% if include_web_interface %}
- Interfaz web incluida
{% endif %}
- API REST completa
- Documentación automática

## Instalación

```bash
pip install -r requirements.txt
python main.py
```

## Uso

{% if include_web_interface %}
### Interfaz Web
Accede a: http://localhost:{{port}}

### API
{% endif %}
Documentación: http://localhost:{{port}}/docs

## Docker

```bash
docker build -t {{project_name}} .
docker run -p {{port}}:{{port}} {{project_name}}
```
'''


def _get_web_interface_content() -> str:
    """Contenido de la interfaz web"""
    # Aquí iría el HTML completo de la interfaz web
    return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{{project_name}} - OCR Service</title>
    <!-- Bootstrap y estilos -->
</head>
<body>
    <!-- Interfaz web completa -->
</body>
</html>'''


def _get_test_content() -> str:
    """Contenido de los tests"""
    return '''#!/usr/bin/env python3
"""
Tests para {{project_name}}
"""

import requests
import time

def test_ocr_service():
    """Test del servicio OCR"""
    base_url = "http://localhost:{{port}}"
    
    # Test health check
    response = requests.get(f"{base_url}/health")
    assert response.status_code == 200
    
    print("✅ Tests completados")

if __name__ == "__main__":
    test_ocr_service()
'''
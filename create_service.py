#!/usr/bin/env python3
"""
FastAPI Microservices SDK - Service Creator

Script simple para crear microservicios usando el SDK.
"""

import os
import sys
from pathlib import Path
from jinja2 import Template as Jinja2Template

def main():
    """Crear un microservicio de forma interactiva."""
    
    print("🚀 FastAPI Microservices SDK - Service Creator")
    print("=" * 50)
    
    # Obtener información del usuario
    service_name = input("📝 Nombre del servicio (ej: user-service): ").strip()
    if not service_name:
        service_name = "my-service"
    
    port = input(f"🌐 Puerto (default: 8001): ").strip()
    if not port:
        port = "8001"
    
    print("\n📦 Templates disponibles:")
    print("1. microservice (Recomendado) - Servicio completo con auth + DB")
    print("2. auth_service - Servicio especializado en autenticación")
    print("3. api_gateway - Gateway para enrutar a otros servicios")
    print("4. data_service - Servicio CRUD especializado")
    
    template_choice = input("🎯 Elegir template (1-4, default: 1): ").strip()
    if template_choice == "2":
        template = "auth_service"
    elif template_choice == "3":
        template = "api_gateway"
    elif template_choice == "4":
        template = "data_service"
    else:
        template = "microservice"
    
    # Confirmar
    print(f"\n✅ Configuración:")
    print(f"   Servicio: {service_name}")
    print(f"   Puerto: {port}")
    print(f"   Template: {template}")
    
    confirm = input("\n¿Continuar? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', 'sí', 'si']:
        print("❌ Cancelado")
        return
    
    # Crear servicio
    try:
        create_microservice(service_name, int(port), template)
        
        print(f"\n🎉 ¡Servicio '{service_name}' creado exitosamente!")
        print(f"\n📋 Próximos pasos:")
        print(f"   1. cd {service_name}")
        print(f"   2. pip install -r requirements.txt")
        print(f"   3. cp .env.example .env")
        print(f"   4. python main.py")
        print(f"   5. Visitar: http://localhost:{port}/docs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


def create_microservice(service_name: str, port: int, template: str):
    """Crear microservicio usando el template especificado."""
    
    output_path = Path(service_name)
    
    # Variables del template
    variables = {
        'project_name': service_name,
        'service_name': service_name,
        'service_port': port,
        'author': 'Developer',
        'version': '1.0.0',
        'description': f'{service_name} - Microservicio creado con FastAPI SDK',
        'python_version': '3.8+',
        'database': 'postgresql',
        'use_redis': True,
        'enable_observability': True,
        'enable_security': True
    }
    
    # Crear directorio
    if output_path.exists():
        import shutil
        shutil.rmtree(output_path)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🔨 Generando servicio usando template '{template}'...")
    
    # Importar el template correspondiente
    if template == "auth_service":
        from fastapi_microservices_sdk.templates.builtin_templates.auth_service import AuthServiceTemplate
        template_obj = AuthServiceTemplate.create_template()
    elif template == "api_gateway":
        from fastapi_microservices_sdk.templates.builtin_templates.api_gateway import APIGatewayTemplate
        template_obj = APIGatewayTemplate.create_template()
    elif template == "data_service":
        from fastapi_microservices_sdk.templates.builtin_templates.data_service import DataServiceTemplate
        template_obj = DataServiceTemplate.create_template()
    else:
        from fastapi_microservices_sdk.templates.builtin_templates.microservice import MicroserviceTemplate
        template_obj = MicroserviceTemplate.create_template()
    
    # Generar archivos del template
    generated_files = []
    
    for template_file in template_obj.files:
        file_path = output_path / template_file.path
        
        # Crear directorios padre si no existen
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Renderizar contenido con Jinja2
        jinja_template = Jinja2Template(template_file.content)
        rendered_content = jinja_template.render(**variables)
        
        # Escribir archivo
        file_path.write_text(rendered_content, encoding='utf-8')
        generated_files.append(file_path)
        
        print(f"   ✓ {template_file.path}")
    
    # Crear archivos adicionales
    create_additional_files(output_path, variables)
    
    print(f"   ✓ Archivos adicionales creados")


def create_additional_files(output_path: Path, variables: dict):
    """Crear archivos adicionales específicos."""
    
    # .env.example
    env_example_content = f"""# Environment Configuration
ENVIRONMENT=development
HOST=0.0.0.0
PORT={variables['service_port']}

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/{variables['project_name']}

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8080","http://localhost:8000"]
"""
    
    (output_path / ".env.example").write_text(env_example_content)
    
    # app/__init__.py
    app_init_content = f'''"""
{variables['project_name']}

{variables['description']}
"""

__version__ = "{variables['version']}"
__author__ = "{variables['author']}"
'''
    
    app_dir = output_path / "app"
    app_dir.mkdir(exist_ok=True)
    (app_dir / "__init__.py").write_text(app_init_content)
    
    # Crear estructura de directorios
    dirs_to_create = [
        "app/models",
        "app/api/v1",
        "app/services", 
        "app/repositories",
        "app/schemas",
        "app/core",
        "tests/unit",
        "tests/integration"
    ]
    
    for dir_path in dirs_to_create:
        full_path = output_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        (full_path / "__init__.py").write_text("# Module init")


if __name__ == "__main__":
    sys.exit(main())
# 🚀 FastAPI Microservices SDK

**Un SDK completo para crear microservicios profesionales con FastAPI en minutos**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 ¿Qué es este SDK?

Este SDK te permite crear **microservicios enterprise-grade** con FastAPI de forma rápida y profesional. En lugar de configurar todo desde cero (que puede tomar semanas), generas un servicio completo en **5-10 minutos**.

### ⚡ Antes vs Después

| Sin SDK | Con SDK |
|---------|---------|
| 2-3 semanas | 5-10 minutos |
| Configuración manual | Generación automática |
| Errores comunes | Mejores prácticas incluidas |
| Sin estándares | Arquitectura consistente |

---

## 🛠️ Características Principales

### ✅ **Generación Automática**
- Servicios FastAPI completos con documentación
- Autenticación JWT lista para usar
- Base de datos configurada (PostgreSQL, SQLite)
- Docker y docker-compose incluidos
- Tests automáticos generados

### ✅ **Seguridad Enterprise**
- JWT Authentication con refresh tokens
- Control de acceso basado en roles (RBAC)
- Validación de requests automática
- CORS configurado correctamente

### ✅ **Observabilidad**
- Health checks integrados
- Logging estructurado
- Métricas básicas
- Documentación automática (Swagger/OpenAPI)

### ✅ **Deployment Ready**
- Dockerfile optimizado
- Docker Compose para desarrollo
- Variables de entorno configuradas
- Estructura de proyecto profesional

---

## 🚀 Inicio Rápido

### **Prerrequisitos**
```bash
# Python 3.8 o superior
python --version

# Git
git --version
```

### **Instalación**
```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/fastapi-microservices-sdk.git
cd fastapi-microservices-sdk

# 2. Instalar dependencias
pip install -r requirements.txt
```

### **Crear tu primer microservicio**
```bash
# Crear servicio de usuarios
python create_service.py

# Seguir las instrucciones interactivas
# El servicio se creará en ./mi-servicio/
```

### **Ejecutar el servicio**
```bash
cd mi-servicio
pip install -r requirements.txt
cp .env.example .env
python main.py
```

**¡Listo!** Tu servicio está ejecutándose en `http://localhost:8001`

- 📚 **Documentación**: `http://localhost:8001/docs`
- 🔍 **Health Check**: `http://localhost:8001/health/`

---

## 📦 Templates Disponibles

### **🎯 microservice** (Recomendado)
Servicio completo con todas las funcionalidades básicas.

**Incluye:**
- FastAPI + documentación automática
- Autenticación JWT completa  
- Base de datos SQLAlchemy
- Health checks
- Docker configuration
- Tests unitarios

**Perfecto para:** Cualquier tipo de microservicio

### **📊 data_service**
Servicio especializado en operaciones CRUD.

**Incluye:**
- CRUD operations automáticas
- Paginación y filtros
- Validación de datos
- Estructura de base de datos

**Perfecto para:** Gestión de entidades (usuarios, productos, pedidos, etc.)

---

## 💡 Ejemplos de Uso

### **Ejemplo 1: API de Usuarios**
```bash
# Crear servicio
python create_service.py
# Elegir: user-service, puerto 8001, template microservice

# Resultado: Servicio con:
# - CRUD de usuarios
# - Login/logout
# - Gestión de roles
# - Base de datos configurada
```

### **Ejemplo 2: API de Productos**
```bash
# Crear servicio
python create_service.py  
# Elegir: product-service, puerto 8002, template data_service

# Resultado: Servicio con:
# - CRUD de productos
# - Filtros y búsqueda
# - Paginación automática
# - Validación de datos
```

### **Ejemplo 3: Sistema Completo**
```bash
# Crear múltiples servicios
python create_service.py  # user-service (8001)
python create_service.py  # product-service (8002)  
python create_service.py  # order-service (8003)

# Resultado: Arquitectura de microservicios completa
```

---

## 🏗️ Arquitectura Generada

```
mi-servicio/
├── main.py                 # Aplicación FastAPI principal
├── config.py              # Configuración y variables de entorno
├── requirements.txt       # Dependencias Python
├── Dockerfile            # Imagen Docker optimizada
├── docker-compose.yml    # Stack completo para desarrollo
├── .env.example         # Variables de entorno de ejemplo
├── app/
│   ├── __init__.py
│   ├── health.py        # Health checks
│   ├── auth.py         # Autenticación JWT
│   ├── users.py        # APIs de usuarios (ejemplo)
│   ├── models/         # Modelos de base de datos
│   ├── schemas/        # Schemas Pydantic
│   └── services/       # Lógica de negocio
└── tests/
    ├── __init__.py
    └── test_main.py     # Tests automáticos
```

---

## 🧪 Testing

```bash
# Ejecutar tests
cd mi-servicio
pytest

# Con coverage
pytest --cov=app tests/

# Tests específicos
pytest tests/test_auth.py -v
```

---

## 🐳 Docker

### **Desarrollo Local**
```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar servicios
docker-compose down
```

### **Build de Producción**
```bash
# Build imagen
docker build -t mi-servicio:latest .

# Ejecutar container
docker run -p 8001:8001 mi-servicio:latest
```

---

## 📊 Monitoreo

### **Health Checks**
```bash
# Health básico
curl http://localhost:8001/health/

# Readiness check
curl http://localhost:8001/health/ready

# Liveness check  
curl http://localhost:8001/health/live
```

### **Métricas**
- Logs estructurados en JSON
- Métricas de performance automáticas
- Documentación OpenAPI generada
- Validación de requests/responses

---

## 🤝 Contribuir

### **Reportar Issues**
- Usa GitHub Issues para bugs y feature requests
- Incluye información del sistema y logs de error
- Proporciona pasos para reproducir el problema

### **Desarrollo**
```bash
# Fork del repositorio
git clone https://github.com/tu-usuario/fastapi-microservices-sdk.git

# Crear rama para feature
git checkout -b feature/nueva-funcionalidad

# Hacer cambios y commit
git commit -m "feat: agregar nueva funcionalidad"

# Push y crear Pull Request
git push origin feature/nueva-funcionalidad
```

---

## 📚 Documentación

- 📖 **[Guía Completa](GUIA_COMPLETA_SDK_MICROSERVICIOS.md)** - Tutorial detallado paso a paso
- 🔧 **[CLI Reference](CLI_COMMANDS_REFERENCE.md)** - Todos los comandos disponibles
- 🏗️ **[Arquitectura](DOCUMENTACION_COMPLETA_SDK_DICIEMBRE_2025.md)** - Documentación técnica completa

---

## 🗺️ Roadmap

### **v1.1 (Próximo)**
- [ ] Template `auth_service` completo
- [ ] Template `api_gateway` funcional
- [ ] CLI mejorado con más opciones
- [ ] Soporte para MongoDB

### **v1.2 (Futuro)**
- [ ] Template `notification_service`
- [ ] Template `file_service`
- [ ] Kubernetes manifests automáticos
- [ ] Observabilidad avanzada (Prometheus/Grafana)

### **v2.0 (Visión)**
- [ ] GUI para generar servicios
- [ ] Marketplace de templates
- [ ] Integración con clouds (AWS, GCP, Azure)
- [ ] Service mesh automático

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 👥 Equipo

- **Lucas** - Creador y mantenedor principal
- **Contribuidores** - Ver [CONTRIBUTORS.md](CONTRIBUTORS.md)

---

## 🙏 Agradecimientos

- [FastAPI](https://fastapi.tiangolo.com/) por el framework increíble
- [Pydantic](https://pydantic-docs.helpmanual.io/) por la validación de datos
- [SQLAlchemy](https://www.sqlalchemy.org/) por el ORM
- Comunidad Python por las herramientas y librerías

---
        
## 📞 Soporte

- 🐛 **Issues**: [GitHub Issues](https://github.com/tu-usuario/fastapi-microservices-sdk/issues)
- 💬 **Discusiones**: [GitHub Discussions](https://github.com/tu-usuario/fastapi-microservices-sdk/discussions)
- 📧 **Email**: descargastacolu@gmail.com

---

**⭐ Si este proyecto te ayuda, dale una estrella en GitHub!**

*Última actualización: 19-09-2025*

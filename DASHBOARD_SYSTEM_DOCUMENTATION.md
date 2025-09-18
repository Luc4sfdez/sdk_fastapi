# Sistema de Dashboards - Documentación Completa

## Índice
1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes Principales](#componentes-principales)
4. [Templates Avanzados](#templates-avanzados)
5. [Integración con Grafana](#integración-con-grafana)
6. [Dashboard Web](#dashboard-web)
7. [Sistema de Alertas](#sistema-de-alertas)
8. [Colector de Métricas](#colector-de-métricas)
9. [Guías de Uso](#guías-de-uso)
10. [Ejemplos Prácticos](#ejemplos-prácticos)

## Visión General

El sistema de dashboards del SDK FastAPI Microservices proporciona una solución completa de monitoreo y visualización que incluye:

- **Templates predefinidos** para casos de uso comunes
- **Dashboard web interactivo** con WebSocket en tiempo real
- **Integración nativa con Grafana**
- **Sistema de alertas inteligente**
- **Colector de métricas automatizado**
- **Visualizaciones personalizables**

### Características Principales

- ✅ 7 templates predefinidos para diferentes escenarios
- ✅ Dashboard web con streaming en tiempo real
- ✅ Integración automática con Prometheus y Grafana
- ✅ Sistema de alertas con múltiples canales
- ✅ Colector de métricas con 50+ métricas predefinidas
- ✅ Visualizaciones interactivas (gráficos, tablas, gauges)
- ✅ Configuración declarativa via YAML/JSON
- ✅ API REST para gestión programática

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard System                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  Web Dashboard  │  │ Grafana Integration │  │   Templates  │ │
│  │                 │  │                 │  │              │ │
│  │ - Real-time UI  │  │ - Auto Config   │  │ - 7 Built-in │ │
│  │ - WebSocket     │  │ - Dashboards    │  │ - Custom     │ │
│  │ - Interactive   │  │ - Alerts        │  │ - Validation │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Metrics Collector│  │ Alert System   │  │ Visualization│ │
│  │                 │  │                 │  │              │ │
│  │ - 50+ Metrics   │  │ - Smart Rules   │  │ - Charts     │ │
│  │ - Auto Discovery│  │ - Multi-channel │  │ - Tables     │ │
│  │ - Prometheus    │  │ - Escalation    │  │ - Gauges     │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Data Sources                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Prometheus    │  │    Databases    │  │   Log Files  │ │
│  │                 │  │                 │  │              │ │
│  │ - Time Series   │  │ - SQL Queries   │  │ - Structured │ │
│  │ - Metrics       │  │ - Performance   │  │ - Parsing    │ │
│  │ - Alerts        │  │ - Health        │  │ - Indexing   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Visualization Engine (`visualization.py`)

Motor principal de visualización que maneja:

```python
from fastapi_microservices_sdk.observability.dashboards.visualization import DashboardVisualization

# Inicializar el motor
viz = DashboardVisualization()

# Crear dashboard
dashboard_config = {
    "id": "my-dashboard",
    "name": "Mi Dashboard",
    "components": [
        {
            "id": "cpu_usage",
            "type": "gauge",
            "title": "CPU Usage",
            "data_source": "prometheus",
            "query": "cpu_usage_percent"
        }
    ]
}

dashboard = viz.create_dashboard(dashboard_config)
```

**Tipos de Visualización Soportados:**
- `line_chart` - Gráficos de líneas
- `bar_chart` - Gráficos de barras
- `pie_chart` - Gráficos circulares
- `gauge` - Medidores
- `metric` - Métricas simples
- `table` - Tablas de datos
- `heatmap` - Mapas de calor

### 2. Web Dashboard (`web_dashboard.py`)

Dashboard web interactivo con FastAPI:

```python
from fastapi_microservices_sdk.observability.dashboards.web_dashboard import WebDashboard

# Inicializar dashboard web
web_dashboard = WebDashboard(port=8080)

# Agregar dashboard
web_dashboard.add_dashboard("overview", dashboard_config)

# Iniciar servidor
await web_dashboard.start()
```

**Características del Web Dashboard:**
- Interfaz web responsive
- Streaming en tiempo real via WebSocket
- API REST para gestión
- Autenticación opcional
- Temas personalizables

### 3. Grafana Integration (`grafana_integration.py`)

Integración automática con Grafana:

```python
from fastapi_microservices_sdk.observability.dashboards.grafana_integration import GrafanaIntegration

# Configurar integración
grafana = GrafanaIntegration(
    url="http://grafana:3000",
    api_key="your-api-key"
)

# Crear dashboard en Grafana
grafana_dashboard = await grafana.create_dashboard_from_template(
    template_id="microservice_overview",
    service_name="my-service"
)
```

## Templates Avanzados

### Templates Disponibles

1. **Microservice Overview** (`microservice_overview`)
   - Salud del servicio
   - Tasa de requests
   - Tasa de errores
   - Tiempo de respuesta
   - Conexiones activas

2. **API Performance** (`api_performance`)
   - Tiempo de respuesta promedio
   - Throughput
   - Percentiles de latencia
   - Apdex score
   - Análisis por endpoint

3. **Infrastructure Monitoring** (`infrastructure`)
   - CPU, memoria, disco
   - I/O de red y disco
   - Load average
   - Procesos activos

4. **Error Tracking** (`error_tracking`)
   - Total de errores
   - Tasa de errores
   - Distribución por código de estado
   - Top endpoints con errores

5. **Business Metrics** (`business_metrics`)
   - Usuarios activos diarios
   - Revenue
   - Tasa de conversión
   - Valor promedio de orden

6. **Database Monitoring** (`database_monitoring`)
   - Conexiones activas
   - Duración de queries
   - Cache hit ratio
   - Queries más lentas

7. **Security Monitoring** (`security_monitoring`)
   - Intentos de login fallidos
   - IPs bloqueadas
   - Actividades sospechosas
   - Tasa de éxito de autenticación

### Uso de Templates

```python
from fastapi_microservices_sdk.observability.dashboards.advanced_templates import AdvancedDashboardTemplates

templates = AdvancedDashboardTemplates()

# Listar templates disponibles
available_templates = templates.list_templates()

# Obtener template específico
template = templates.get_template("microservice_overview")

# Buscar templates
api_templates = templates.search_templates("api")

# Crear dashboard desde template
from fastapi_microservices_sdk.observability.dashboards.advanced_templates import create_dashboard_from_template

dashboard = create_dashboard_from_template(
    template_id="microservice_overview",
    customizations={
        "variables": {"service_name": "my-api"},
        "time_range": {"from": "now-2h", "to": "now"}
    }
)
```

## Sistema de Alertas

### Configuración de Alertas

```python
from fastapi_microservices_sdk.observability.dashboards.alerts import AlertManager

alert_manager = AlertManager()

# Definir regla de alerta
alert_rule = {
    "id": "high_error_rate",
    "name": "High Error Rate",
    "condition": {
        "metric": "error_rate_percent",
        "operator": ">",
        "threshold": 5.0,
        "duration": "5m"
    },
    "severity": "critical",
    "channels": ["slack", "email"],
    "message": "Error rate is above 5% for service {{service_name}}"
}

alert_manager.add_rule(alert_rule)
```

### Canales de Notificación

```python
# Configurar Slack
alert_manager.configure_channel("slack", {
    "webhook_url": "https://hooks.slack.com/...",
    "channel": "#alerts",
    "username": "AlertBot"
})

# Configurar Email
alert_manager.configure_channel("email", {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "alerts@company.com",
    "password": "password",
    "recipients": ["team@company.com"]
})
```

## Colector de Métricas

### Métricas Automáticas

El colector incluye 50+ métricas predefinidas:

```python
from fastapi_microservices_sdk.observability.dashboards.metrics_collector import MetricsCollector

collector = MetricsCollector()

# Iniciar colección automática
await collector.start_collection()

# Métricas disponibles incluyen:
# - HTTP: requests, response_time, status_codes
# - System: cpu_usage, memory_usage, disk_usage
# - Database: connections, query_time, cache_hits
# - Business: user_activity, revenue, conversions
```

### Métricas Personalizadas

```python
# Registrar métrica personalizada
collector.register_custom_metric(
    name="custom_business_metric",
    metric_type="counter",
    description="Custom business metric",
    labels=["service", "environment"]
)

# Incrementar métrica
collector.increment("custom_business_metric", 
                   labels={"service": "api", "environment": "prod"})
```

## Guías de Uso

### 1. Configuración Inicial

```bash
# Instalar dependencias
pip install fastapi-microservices-sdk[dashboards]

# Configurar variables de entorno
export PROMETHEUS_URL=http://localhost:9090
export GRAFANA_URL=http://localhost:3000
export GRAFANA_API_KEY=your-api-key
```

### 2. Configuración Básica

```python
# config/dashboard_config.py
DASHBOARD_CONFIG = {
    "web_dashboard": {
        "enabled": True,
        "port": 8080,
        "host": "0.0.0.0"
    },
    "grafana": {
        "enabled": True,
        "auto_create_dashboards": True
    },
    "alerts": {
        "enabled": True,
        "check_interval": 30
    },
    "metrics": {
        "collection_interval": 15,
        "retention_days": 30
    }
}
```

### 3. Integración en FastAPI

```python
from fastapi import FastAPI
from fastapi_microservices_sdk.observability.dashboards import setup_dashboards

app = FastAPI()

# Configurar dashboards
setup_dashboards(
    app,
    config=DASHBOARD_CONFIG,
    templates=["microservice_overview", "api_performance"]
)
```

## Ejemplos Prácticos

### Ejemplo 1: Dashboard de Microservicio

```python
from fastapi_microservices_sdk.observability.dashboards import (
    DashboardVisualization,
    AdvancedDashboardTemplates,
    create_dashboard_from_template
)

# Crear dashboard para microservicio
templates = AdvancedDashboardTemplates()
viz = DashboardVisualization()

# Usar template predefinido
dashboard_config = create_dashboard_from_template(
    template_id="microservice_overview",
    customizations={
        "variables": {
            "service_name": "user-service"
        },
        "time_range": {
            "from": "now-1h",
            "to": "now"
        }
    }
)

# Crear dashboard
dashboard = viz.create_dashboard(dashboard_config)

# Renderizar
html_content = dashboard.render()
```

### Ejemplo 2: Dashboard Web con Streaming

```python
from fastapi_microservices_sdk.observability.dashboards.web_dashboard import WebDashboard

# Inicializar dashboard web
web_dashboard = WebDashboard(
    port=8080,
    enable_auth=True,
    theme="dark"
)

# Agregar múltiples dashboards
web_dashboard.add_dashboard("overview", overview_config)
web_dashboard.add_dashboard("performance", performance_config)
web_dashboard.add_dashboard("errors", error_config)

# Configurar streaming en tiempo real
web_dashboard.enable_realtime_streaming(
    update_interval=5,  # segundos
    max_data_points=1000
)

# Iniciar servidor
await web_dashboard.start()
```

### Ejemplo 3: Integración Completa con Grafana

```python
from fastapi_microservices_sdk.observability.dashboards.grafana_integration import GrafanaIntegration

# Configurar Grafana
grafana = GrafanaIntegration(
    url="http://grafana:3000",
    api_key="your-api-key",
    organization_id=1
)

# Crear folder para dashboards
folder = await grafana.create_folder("Microservices")

# Crear dashboards desde templates
services = ["user-service", "order-service", "payment-service"]

for service in services:
    dashboard = await grafana.create_dashboard_from_template(
        template_id="microservice_overview",
        service_name=service,
        folder_id=folder["id"]
    )
    
    print(f"Created dashboard for {service}: {dashboard['url']}")

# Configurar alertas
alert_rules = [
    {
        "name": f"High Error Rate - {service}",
        "condition": f"error_rate{{service=\"{service}\"}} > 5",
        "for": "5m",
        "annotations": {
            "summary": f"High error rate detected for {service}"
        }
    }
    for service in services
]

for rule in alert_rules:
    await grafana.create_alert_rule(rule)
```

### Ejemplo 4: Sistema de Alertas Personalizado

```python
from fastapi_microservices_sdk.observability.dashboards.alerts import AlertManager

# Configurar sistema de alertas
alert_manager = AlertManager()

# Configurar canales
alert_manager.configure_channel("slack", {
    "webhook_url": "https://hooks.slack.com/services/...",
    "channel": "#alerts",
    "username": "MonitorBot"
})

alert_manager.configure_channel("pagerduty", {
    "integration_key": "your-integration-key",
    "severity": "critical"
})

# Definir reglas de alerta
alert_rules = [
    {
        "id": "high_response_time",
        "name": "High Response Time",
        "condition": {
            "metric": "response_time_p95",
            "operator": ">",
            "threshold": 2.0,
            "duration": "5m"
        },
        "severity": "warning",
        "channels": ["slack"]
    },
    {
        "id": "service_down",
        "name": "Service Down",
        "condition": {
            "metric": "service_up",
            "operator": "==",
            "threshold": 0,
            "duration": "1m"
        },
        "severity": "critical",
        "channels": ["slack", "pagerduty"]
    },
    {
        "id": "high_memory_usage",
        "name": "High Memory Usage",
        "condition": {
            "metric": "memory_usage_percent",
            "operator": ">",
            "threshold": 90,
            "duration": "10m"
        },
        "severity": "warning",
        "channels": ["slack"]
    }
]

# Agregar reglas
for rule in alert_rules:
    alert_manager.add_rule(rule)

# Iniciar monitoreo
await alert_manager.start_monitoring()
```

## API Reference

### DashboardVisualization

```python
class DashboardVisualization:
    def create_dashboard(self, config: Dict) -> Dashboard
    def render_component(self, component: Dict) -> str
    def export_dashboard(self, dashboard_id: str) -> Dict
    def import_dashboard(self, config: Dict) -> str
```

### WebDashboard

```python
class WebDashboard:
    def __init__(self, port: int = 8080, host: str = "0.0.0.0")
    def add_dashboard(self, name: str, config: Dict)
    def remove_dashboard(self, name: str)
    async def start(self)
    async def stop(self)
```

### GrafanaIntegration

```python
class GrafanaIntegration:
    def __init__(self, url: str, api_key: str)
    async def create_dashboard(self, config: Dict) -> Dict
    async def create_dashboard_from_template(self, template_id: str, **kwargs) -> Dict
    async def create_alert_rule(self, rule: Dict) -> Dict
    async def create_folder(self, name: str) -> Dict
```

### AlertManager

```python
class AlertManager:
    def add_rule(self, rule: Dict)
    def remove_rule(self, rule_id: str)
    def configure_channel(self, name: str, config: Dict)
    async def start_monitoring(self)
    async def stop_monitoring(self)
```

## Configuración Avanzada

### Variables de Entorno

```bash
# Prometheus
PROMETHEUS_URL=http://localhost:9090
PROMETHEUS_USERNAME=admin
PROMETHEUS_PASSWORD=password

# Grafana
GRAFANA_URL=http://localhost:3000
GRAFANA_API_KEY=your-api-key
GRAFANA_ORG_ID=1

# Dashboard Web
DASHBOARD_WEB_PORT=8080
DASHBOARD_WEB_HOST=0.0.0.0
DASHBOARD_WEB_AUTH_ENABLED=true
DASHBOARD_WEB_THEME=dark

# Alertas
ALERT_CHECK_INTERVAL=30
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
ALERT_EMAIL_SMTP_SERVER=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587

# Métricas
METRICS_COLLECTION_INTERVAL=15
METRICS_RETENTION_DAYS=30
METRICS_BATCH_SIZE=1000
```

### Archivo de Configuración

```yaml
# dashboard_config.yaml
dashboard_system:
  web_dashboard:
    enabled: true
    port: 8080
    host: "0.0.0.0"
    auth:
      enabled: true
      secret_key: "your-secret-key"
    theme: "dark"
    
  grafana:
    enabled: true
    url: "http://grafana:3000"
    api_key: "your-api-key"
    auto_create_dashboards: true
    folder_name: "Microservices"
    
  alerts:
    enabled: true
    check_interval: 30
    channels:
      slack:
        webhook_url: "https://hooks.slack.com/..."
        channel: "#alerts"
      email:
        smtp_server: "smtp.gmail.com"
        smtp_port: 587
        username: "alerts@company.com"
        
  metrics:
    collection_interval: 15
    retention_days: 30
    batch_size: 1000
    custom_metrics:
      - name: "business_metric_1"
        type: "counter"
        description: "Custom business metric"
        
  templates:
    default_templates:
      - "microservice_overview"
      - "api_performance"
      - "error_tracking"
    custom_templates_path: "./custom_templates/"
```

## Troubleshooting

### Problemas Comunes

1. **Dashboard no se carga**
   ```bash
   # Verificar conexión a Prometheus
   curl http://localhost:9090/api/v1/query?query=up
   
   # Verificar logs
   tail -f logs/dashboard.log
   ```

2. **Métricas no aparecen**
   ```python
   # Verificar colector de métricas
   from fastapi_microservices_sdk.observability.dashboards.metrics_collector import MetricsCollector
   
   collector = MetricsCollector()
   status = collector.get_status()
   print(status)
   ```

3. **Alertas no se envían**
   ```python
   # Verificar configuración de canales
   alert_manager.test_channel("slack")
   alert_manager.test_channel("email")
   ```

### Logs y Debugging

```python
import logging

# Habilitar logs detallados
logging.getLogger("fastapi_microservices_sdk.observability").setLevel(logging.DEBUG)

# Logs específicos por componente
logging.getLogger("dashboard.visualization").setLevel(logging.DEBUG)
logging.getLogger("dashboard.alerts").setLevel(logging.DEBUG)
logging.getLogger("dashboard.metrics").setLevel(logging.DEBUG)
```

## Conclusión

El sistema de dashboards del SDK FastAPI Microservices proporciona una solución completa y robusta para el monitoreo y visualización de microservicios. Con sus templates predefinidos, integración nativa con Grafana, dashboard web interactivo y sistema de alertas inteligente, facilita la implementación de observabilidad de clase empresarial.

### Próximos Pasos

1. Explorar los templates disponibles
2. Configurar el dashboard web
3. Integrar con Grafana
4. Configurar alertas
5. Personalizar métricas
6. Crear templates personalizados

Para más información y ejemplos, consulta la documentación completa del SDK.
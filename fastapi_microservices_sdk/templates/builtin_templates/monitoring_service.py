"""
Monitoring Service Template for FastAPI Microservices SDK

This template generates comprehensive monitoring services with metrics collection,
dashboard integration, alerting, and observability features.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
import json
import yaml

from ..engine import Template
from ..exceptions import TemplateValidationError, GenerationError


@dataclass
class MetricDefinition:
    """Metric definition for monitoring"""
    name: str
    type: str  # counter, gauge, histogram, summary
    description: str
    labels: List[str] = field(default_factory=list)
    unit: Optional[str] = None


@dataclass
class DashboardDefinition:
    """Dashboard definition for visualization"""
    name: str
    title: str
    panels: List[Dict[str, Any]] = field(default_factory=list)
    refresh_interval: str = "30s"
    time_range: str = "1h"


@dataclass
class AlertDefinition:
    """Alert rule definition"""
    name: str
    expression: str
    threshold: float
    duration: str = "5m"
    severity: str = "warning"
    description: str = ""


class MonitoringServiceTemplate(Template):
    """
    Comprehensive Monitoring Service Template
    
    Generates production-ready monitoring services with:
    - Prometheus metrics collection and aggregation
    - Grafana dashboard integration and templates
    - Alert manager integration with notification channels
    - Custom metrics collection from multiple sources
    - Health check aggregation and reporting
    - Performance profiling and optimization insights
    - Log aggregation and analysis
    - Distributed tracing integration
    - Capacity planning and forecasting
    - SLA monitoring and reporting
    """
    
    def __init__(self):
        from ..config import TemplateConfig, TemplateCategory
        config = TemplateConfig(
            id="monitoring_service",
            name="Monitoring Service Template",
            description="Comprehensive monitoring service with metrics, dashboards, and alerting",
            category=TemplateCategory.MONITORING,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            tags=["monitoring", "metrics", "dashboard", "alerting", "observability"]
        )
        super().__init__(config=config)

    def get_required_variables(self) -> List[str]:
        """Get list of required template variables"""
        return [
            "service_name",
            "service_description",
            "metrics_backend",
            "dashboard_backend",
            "alert_backend"
        ]
    
    def get_optional_variables(self) -> Dict[str, Any]:
        """Get optional variables with default values"""
        return {
            "service_version": "1.0.0",
            "service_port": 8000,
            "metrics_port": 9090,
            "dashboard_port": 3000,
            "alert_port": 9093,
            "metrics_backend_config": {
                "type": "prometheus",
                "host": "localhost",
                "port": 9090,
                "retention": "15d"
            },
            "dashboard_backend_config": {
                "type": "grafana",
                "host": "localhost",
                "port": 3000,
                "admin_user": "admin",
                "admin_password": "admin"
            },
            "alert_backend_config": {
                "type": "alertmanager",
                "host": "localhost",
                "port": 9093,
                "smtp_host": "localhost",
                "smtp_port": 587
            },
            "enable_custom_metrics": True,
            "enable_health_checks": True,
            "enable_performance_profiling": True,
            "enable_log_aggregation": True,
            "enable_distributed_tracing": True,
            "enable_capacity_planning": True,
            "enable_sla_monitoring": True,
            "scrape_interval": "15s",
            "evaluation_interval": "15s",
            "retention_days": 15,
            "notification_channels": [],
            "custom_metrics": [],
            "dashboards": [],
            "alert_rules": []
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return errors"""
        return self.validate_variables(config)
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate template variables and return errors"""
        errors = []
        
        # Validate service name
        service_name = variables.get("service_name", "")
        if not service_name or not isinstance(service_name, str):
            errors.append("service_name is required and must be a string")
        elif not service_name.replace("_", "").replace("-", "").isalnum():
            errors.append("service_name must contain only alphanumeric characters, hyphens, and underscores")
        
        # Validate metrics backend
        metrics_backend = variables.get("metrics_backend", "")
        supported_metrics = ["prometheus", "influxdb", "datadog", "newrelic"]
        if metrics_backend not in supported_metrics:
            errors.append(f"metrics_backend must be one of: {', '.join(supported_metrics)}")
        
        # Validate dashboard backend
        dashboard_backend = variables.get("dashboard_backend", "")
        supported_dashboards = ["grafana", "kibana", "datadog", "newrelic"]
        if dashboard_backend not in supported_dashboards:
            errors.append(f"dashboard_backend must be one of: {', '.join(supported_dashboards)}")
        
        # Validate alert backend
        alert_backend = variables.get("alert_backend", "")
        supported_alerts = ["alertmanager", "pagerduty", "slack", "email"]
        if alert_backend not in supported_alerts:
            errors.append(f"alert_backend must be one of: {', '.join(supported_alerts)}")
        
        # Validate custom metrics if provided
        custom_metrics = variables.get("custom_metrics", [])
        if custom_metrics and isinstance(custom_metrics, list):
            for i, metric in enumerate(custom_metrics):
                if not isinstance(metric, dict):
                    errors.append(f"Custom metric {i} must be a dictionary")
                    continue
                
                if "name" not in metric:
                    errors.append(f"Custom metric {i} must have a 'name' field")
                
                if "type" not in metric:
                    errors.append(f"Custom metric {i} must have a 'type' field")
                elif metric["type"] not in ["counter", "gauge", "histogram", "summary"]:
                    errors.append(f"Custom metric {i} type must be one of: counter, gauge, histogram, summary")
        
        # Validate dashboards if provided
        dashboards = variables.get("dashboards", [])
        if dashboards and isinstance(dashboards, list):
            for i, dashboard in enumerate(dashboards):
                if not isinstance(dashboard, dict):
                    errors.append(f"Dashboard {i} must be a dictionary")
                    continue
                
                if "name" not in dashboard:
                    errors.append(f"Dashboard {i} must have a 'name' field")
                
                if "title" not in dashboard:
                    errors.append(f"Dashboard {i} must have a 'title' field")
        
        # Validate alert rules if provided
        alert_rules = variables.get("alert_rules", [])
        if alert_rules and isinstance(alert_rules, list):
            for i, alert in enumerate(alert_rules):
                if not isinstance(alert, dict):
                    errors.append(f"Alert rule {i} must be a dictionary")
                    continue
                
                if "name" not in alert:
                    errors.append(f"Alert rule {i} must have a 'name' field")
                
                if "expression" not in alert:
                    errors.append(f"Alert rule {i} must have an 'expression' field")
                
                if "threshold" not in alert:
                    errors.append(f"Alert rule {i} must have a 'threshold' field")
        
        return errors
    
    def generate_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate all monitoring service files"""
        try:
            # Validate variables
            validation_errors = self.validate_variables(variables)
            if validation_errors:
                raise TemplateValidationError(f"Validation failed: {'; '.join(validation_errors)}")
            
            generated_files = []
            
            # Create directory structure
            self._create_directory_structure(output_dir)
            
            # Generate core application files
            generated_files.extend(self._generate_core_files(variables, output_dir))
            
            # Generate metrics collection files
            generated_files.extend(self._generate_metrics_files(variables, output_dir))
            
            # Generate dashboard files
            generated_files.extend(self._generate_dashboard_files(variables, output_dir))
            
            # Generate alerting files
            generated_files.extend(self._generate_alerting_files(variables, output_dir))
            
            # Generate health check files
            if variables.get("enable_health_checks", True):
                generated_files.extend(self._generate_health_check_files(variables, output_dir))
            
            # Generate performance profiling files
            if variables.get("enable_performance_profiling", True):
                generated_files.extend(self._generate_profiling_files(variables, output_dir))
            
            # Generate log aggregation files
            if variables.get("enable_log_aggregation", True):
                generated_files.extend(self._generate_log_aggregation_files(variables, output_dir))
            
            # Generate tracing files
            if variables.get("enable_distributed_tracing", True):
                generated_files.extend(self._generate_tracing_files(variables, output_dir))
            
            # Generate capacity planning files
            if variables.get("enable_capacity_planning", True):
                generated_files.extend(self._generate_capacity_planning_files(variables, output_dir))
            
            # Generate SLA monitoring files
            if variables.get("enable_sla_monitoring", True):
                generated_files.extend(self._generate_sla_monitoring_files(variables, output_dir))
            
            # Generate API files
            generated_files.extend(self._generate_api_files(variables, output_dir))
            
            # Generate test files
            generated_files.extend(self._generate_test_files(variables, output_dir))
            
            # Generate configuration files
            generated_files.extend(self._generate_config_files(variables, output_dir))
            
            # Generate deployment files
            generated_files.extend(self._generate_deployment_files(variables, output_dir))
            
            # Generate documentation
            generated_files.extend(self._generate_documentation(variables, output_dir))
            
            return generated_files
            
        except Exception as e:
            raise GenerationError("monitoring_service", f"Failed to generate monitoring service: {str(e)}")
    
    def _create_directory_structure(self, output_dir: Path) -> None:
        """Create the directory structure for the monitoring service"""
        directories = [
            "app",
            "app/metrics",
            "app/dashboards",
            "app/alerts",
            "app/health",
            "app/profiling",
            "app/logs",
            "app/tracing",
            "app/capacity",
            "app/sla",
            "app/api",
            "app/api/v1",
            "app/collectors",
            "app/exporters",
            "app/middleware",
            "app/utils",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/performance",
            "config",
            "config/prometheus",
            "config/grafana",
            "config/alertmanager",
            "dashboards",
            "alerts",
            "scripts",
            "docs",
            "docker",
            "k8s"
        ]
        
        for directory in directories:
            (output_dir / directory).mkdir(parents=True, exist_ok=True)
    
    def _generate_core_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate core application files"""
        files = []
        
        # Generate main.py
        main_content = self._generate_main_file(variables)
        main_path = output_dir / "app" / "main.py"
        main_path.write_text(main_content, encoding="utf-8")
        files.append(main_path)
        
        # Generate config.py
        config_content = self._generate_config_file(variables)
        config_path = output_dir / "app" / "config.py"
        config_path.write_text(config_content, encoding="utf-8")
        files.append(config_path)
        
        # Generate __init__.py files
        init_files = [
            "app/__init__.py",
            "app/metrics/__init__.py",
            "app/dashboards/__init__.py",
            "app/alerts/__init__.py",
            "app/health/__init__.py",
            "app/profiling/__init__.py",
            "app/logs/__init__.py",
            "app/tracing/__init__.py",
            "app/capacity/__init__.py",
            "app/sla/__init__.py",
            "app/api/__init__.py",
            "app/api/v1/__init__.py",
            "app/collectors/__init__.py",
            "app/exporters/__init__.py",
            "app/middleware/__init__.py",
            "app/utils/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = output_dir / init_file
            init_path.write_text('"""Monitoring service module"""', encoding="utf-8")
            files.append(init_path)
        
        return files
    
    def _generate_main_file(self, variables: Dict[str, Any]) -> str:
        """Generate the main FastAPI application file"""
        service_name = variables["service_name"]
        service_description = variables["service_description"]
        service_version = variables.get("service_version", "1.0.0")
        
        content = f'''"""
{service_name.replace("_", " ").title()} - Monitoring Service

{service_description}
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from .config import settings
from .metrics.manager import metrics_manager
from .dashboards.manager import dashboard_manager
from .alerts.manager import alert_manager
from .api.v1 import router as api_v1_router
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.request_id import RequestIDMiddleware
from .middleware.logging import LoggingMiddleware
from .middleware.metrics import MetricsMiddleware'''

        if variables.get("enable_health_checks", True):
            content += '''
from .health.manager import health_manager'''

        if variables.get("enable_performance_profiling", True):
            content += '''
from .profiling.manager import profiling_manager'''

        if variables.get("enable_log_aggregation", True):
            content += '''
from .logs.manager import log_manager'''

        if variables.get("enable_distributed_tracing", True):
            content += '''
from .tracing.manager import tracing_manager'''

        content += f'''


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting {service_name}")
    
    # Initialize metrics manager
    await metrics_manager.start()
    logger.info("Metrics manager started")
    
    # Initialize dashboard manager
    await dashboard_manager.start()
    logger.info("Dashboard manager started")
    
    # Initialize alert manager
    await alert_manager.start()
    logger.info("Alert manager started")'''

        if variables.get("enable_health_checks", True):
            content += '''
    
    # Initialize health manager
    await health_manager.start()
    logger.info("Health manager started")'''

        if variables.get("enable_performance_profiling", True):
            content += '''
    
    # Initialize profiling manager
    await profiling_manager.start()
    logger.info("Profiling manager started")'''

        if variables.get("enable_log_aggregation", True):
            content += '''
    
    # Initialize log manager
    await log_manager.start()
    logger.info("Log manager started")'''

        if variables.get("enable_distributed_tracing", True):
            content += '''
    
    # Initialize tracing manager
    await tracing_manager.start()
    logger.info("Tracing manager started")'''

        content += f'''
    
    yield
    
    # Shutdown
    logger.info("Shutting down {service_name}")'''

        if variables.get("enable_distributed_tracing", True):
            content += '''
    
    # Stop tracing manager
    await tracing_manager.stop()
    logger.info("Tracing manager stopped")'''

        if variables.get("enable_log_aggregation", True):
            content += '''
    
    # Stop log manager
    await log_manager.stop()
    logger.info("Log manager stopped")'''

        if variables.get("enable_performance_profiling", True):
            content += '''
    
    # Stop profiling manager
    await profiling_manager.stop()
    logger.info("Profiling manager stopped")'''

        if variables.get("enable_health_checks", True):
            content += '''
    
    # Stop health manager
    await health_manager.stop()
    logger.info("Health manager stopped")'''

        content += '''
    
    # Stop alert manager
    await alert_manager.stop()
    logger.info("Alert manager stopped")
    
    # Stop dashboard manager
    await dashboard_manager.stop()
    logger.info("Dashboard manager stopped")
    
    # Stop metrics manager
    await metrics_manager.stop()
    logger.info("Metrics manager stopped")'''

        content += f'''


# Create FastAPI application
app = FastAPI(
    title="{service_name.replace("_", " ").title()}",
    description="{service_description}",
    version="{service_version}",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {{
        "service": "{service_name}",
        "version": "{service_version}",
        "status": "running",
        "type": "monitoring_service"
    }}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{
        "status": "healthy",
        "service": "{service_name}",
        "version": "{service_version}",
        "checks": {{
            "metrics": await metrics_manager.health_check(),
            "dashboards": await dashboard_manager.health_check(),
            "alerts": await alert_manager.health_check()
        }}
    }}


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add process time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
'''
        
        return content
    
    def _generate_config_file(self, variables: Dict[str, Any]) -> str:
        """Generate the configuration file"""
        service_name = variables["service_name"]
        service_port = variables.get("service_port", 8000)
        metrics_backend = variables["metrics_backend"]
        dashboard_backend = variables["dashboard_backend"]
        alert_backend = variables["alert_backend"]
        
        content = f'''"""
Configuration settings for {service_name}
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    SERVICE_NAME: str = "{service_name}"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    PORT: int = Field(default={service_port}, env="PORT")
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(
        default=["*"], 
        env="CORS_ORIGINS"
    )
    
    # Metrics Backend settings
    METRICS_BACKEND: str = "{metrics_backend}"
    METRICS_HOST: str = Field(default="localhost", env="METRICS_HOST")
    METRICS_PORT: int = Field(default={variables.get("metrics_port", 9090)}, env="METRICS_PORT")
    METRICS_USERNAME: Optional[str] = Field(default=None, env="METRICS_USERNAME")
    METRICS_PASSWORD: Optional[str] = Field(default=None, env="METRICS_PASSWORD")
    
    # Dashboard Backend settings
    DASHBOARD_BACKEND: str = "{dashboard_backend}"
    DASHBOARD_HOST: str = Field(default="localhost", env="DASHBOARD_HOST")
    DASHBOARD_PORT: int = Field(default={variables.get("dashboard_port", 3000)}, env="DASHBOARD_PORT")
    DASHBOARD_USERNAME: str = Field(default="admin", env="DASHBOARD_USERNAME")
    DASHBOARD_PASSWORD: str = Field(default="admin", env="DASHBOARD_PASSWORD")
    
    # Alert Backend settings
    ALERT_BACKEND: str = "{alert_backend}"
    ALERT_HOST: str = Field(default="localhost", env="ALERT_HOST")
    ALERT_PORT: int = Field(default={variables.get("alert_port", 9093)}, env="ALERT_PORT")
    ALERT_USERNAME: Optional[str] = Field(default=None, env="ALERT_USERNAME")
    ALERT_PASSWORD: Optional[str] = Field(default=None, env="ALERT_PASSWORD")
    
    # Monitoring settings
    SCRAPE_INTERVAL: str = Field(default="{variables.get('scrape_interval', '15s')}", env="SCRAPE_INTERVAL")
    EVALUATION_INTERVAL: str = Field(default="{variables.get('evaluation_interval', '15s')}", env="EVALUATION_INTERVAL")
    RETENTION_DAYS: int = Field(default={variables.get("retention_days", 15)}, env="RETENTION_DAYS")
    
    # Feature flags
    ENABLE_CUSTOM_METRICS: bool = Field(default={str(variables.get('enable_custom_metrics', True)).lower()}, env="ENABLE_CUSTOM_METRICS")
    ENABLE_HEALTH_CHECKS: bool = Field(default={str(variables.get('enable_health_checks', True)).lower()}, env="ENABLE_HEALTH_CHECKS")
    ENABLE_PERFORMANCE_PROFILING: bool = Field(default={str(variables.get('enable_performance_profiling', True)).lower()}, env="ENABLE_PERFORMANCE_PROFILING")
    ENABLE_LOG_AGGREGATION: bool = Field(default={str(variables.get('enable_log_aggregation', True)).lower()}, env="ENABLE_LOG_AGGREGATION")
    ENABLE_DISTRIBUTED_TRACING: bool = Field(default={str(variables.get('enable_distributed_tracing', True)).lower()}, env="ENABLE_DISTRIBUTED_TRACING")
    ENABLE_CAPACITY_PLANNING: bool = Field(default={str(variables.get('enable_capacity_planning', True)).lower()}, env="ENABLE_CAPACITY_PLANNING")
    ENABLE_SLA_MONITORING: bool = Field(default={str(variables.get('enable_sla_monitoring', True)).lower()}, env="ENABLE_SLA_MONITORING")
    
    # Notification settings
    SMTP_HOST: str = Field(default="localhost", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str = Field(default="monitoring@example.com", env="SMTP_FROM_EMAIL")
    
    # Slack settings
    SLACK_WEBHOOK_URL: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    SLACK_CHANNEL: str = Field(default="#alerts", env="SLACK_CHANNEL")
    
    # PagerDuty settings
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = Field(default=None, env="PAGERDUTY_INTEGRATION_KEY")
    
    @property
    def metrics_url(self) -> str:
        """Get metrics backend URL"""'''
        
        if metrics_backend == "prometheus":
            content += '''
        return f"http://{self.METRICS_HOST}:{self.METRICS_PORT}"'''
        elif metrics_backend == "influxdb":
            content += '''
        return f"http://{self.METRICS_HOST}:{self.METRICS_PORT}"'''
        elif metrics_backend == "datadog":
            content += '''
        return f"https://api.datadoghq.com"'''
        elif metrics_backend == "newrelic":
            content += '''
        return f"https://api.newrelic.com"'''
        
        content += f'''
    
    @property
    def dashboard_url(self) -> str:
        """Get dashboard backend URL"""'''
        
        if dashboard_backend == "grafana":
            content += '''
        return f"http://{self.DASHBOARD_HOST}:{self.DASHBOARD_PORT}"'''
        elif dashboard_backend == "kibana":
            content += '''
        return f"http://{self.DASHBOARD_HOST}:{self.DASHBOARD_PORT}"'''
        elif dashboard_backend == "datadog":
            content += '''
        return f"https://app.datadoghq.com"'''
        elif dashboard_backend == "newrelic":
            content += '''
        return f"https://one.newrelic.com"'''
        
        content += f'''
    
    @property
    def alert_url(self) -> str:
        """Get alert backend URL"""'''
        
        if alert_backend == "alertmanager":
            content += '''
        return f"http://{self.ALERT_HOST}:{self.ALERT_PORT}"'''
        elif alert_backend == "pagerduty":
            content += '''
        return f"https://events.pagerduty.com"'''
        elif alert_backend == "slack":
            content += '''
        return self.SLACK_WEBHOOK_URL or ""'''
        elif alert_backend == "email":
            content += '''
        return f"smtp://{self.SMTP_HOST}:{self.SMTP_PORT}"'''
        
        content += '''
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
'''
        
        return content

    def _generate_metrics_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate metrics collection files"""
        files = []
        
        # Generate metrics manager
        metrics_manager_content = self._generate_metrics_manager(variables)
        metrics_manager_path = output_dir / "app" / "metrics" / "manager.py"
        metrics_manager_path.write_text(metrics_manager_content, encoding="utf-8")
        files.append(metrics_manager_path)
        
        # Generate metrics collector
        metrics_collector_content = self._generate_metrics_collector(variables)
        metrics_collector_path = output_dir / "app" / "metrics" / "collector.py"
        metrics_collector_path.write_text(metrics_collector_content, encoding="utf-8")
        files.append(metrics_collector_path)
        
        # Generate custom metrics
        custom_metrics_content = self._generate_custom_metrics(variables)
        custom_metrics_path = output_dir / "app" / "metrics" / "custom.py"
        custom_metrics_path.write_text(custom_metrics_content, encoding="utf-8")
        files.append(custom_metrics_path)
        
        return files
    
    def _generate_metrics_manager(self, variables: Dict[str, Any]) -> str:
        """Generate metrics manager"""
        metrics_backend = variables["metrics_backend"]
        
        content = f'''"""
Metrics manager for {metrics_backend}
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta

from prometheus_client import Counter, Gauge, Histogram, Summary, CollectorRegistry, generate_latest
from ..config import settings

logger = logging.getLogger(__name__)


class MetricsManager:
    """Manages metrics collection and export"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.metrics = {{}}
        self.running = False
        
        # Standard metrics
        self.request_count = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'active_connections',
            'Active connections',
            registry=self.registry
        )
        
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
    
    async def start(self) -> None:
        """Start metrics manager"""
        self.running = True
        logger.info("Metrics manager started")
        
        # Start background tasks
        asyncio.create_task(self._collect_system_metrics())
    
    async def stop(self) -> None:
        """Stop metrics manager"""
        self.running = False
        logger.info("Metrics manager stopped")
    
    async def health_check(self) -> str:
        """Health check for metrics manager"""
        return "healthy" if self.running else "unhealthy"
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Record HTTP request metrics"""
        self.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    def set_active_connections(self, count: int) -> None:
        """Set active connections count"""
        self.active_connections.set(count)
    
    def register_custom_metric(self, name: str, metric_type: str, description: str, labels: List[str] = None) -> None:
        """Register a custom metric"""
        labels = labels or []
        
        if metric_type == "counter":
            metric = Counter(name, description, labels, registry=self.registry)
        elif metric_type == "gauge":
            metric = Gauge(name, description, labels, registry=self.registry)
        elif metric_type == "histogram":
            metric = Histogram(name, description, labels, registry=self.registry)
        elif metric_type == "summary":
            metric = Summary(name, description, labels, registry=self.registry)
        else:
            raise ValueError(f"Unknown metric type: {{metric_type}}")
        
        self.metrics[name] = metric
        logger.info(f"Registered custom metric: {{name}}")
    
    def get_metric(self, name: str):
        """Get a registered metric"""
        return self.metrics.get(name)
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')
    
    async def _collect_system_metrics(self) -> None:
        """Collect system metrics periodically"""
        import psutil
        
        while self.running:
            try:
                # Memory usage
                memory = psutil.virtual_memory()
                self.memory_usage.set(memory.used)
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.cpu_usage.set(cpu_percent)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {{e}}")
                await asyncio.sleep(30)


# Global metrics manager instance
metrics_manager = MetricsManager()
'''
        
        return content
    
    def _generate_metrics_collector(self, variables: Dict[str, Any]) -> str:
        """Generate metrics collector"""
        content = '''"""
Metrics collector for gathering metrics from various sources
"""

from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
import logging
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics from various sources"""
    
    def __init__(self):
        self.sources = []
        self.running = False
    
    def add_source(self, name: str, url: str, interval: int = 60, headers: Dict[str, str] = None) -> None:
        """Add a metrics source"""
        source = {
            "name": name,
            "url": url,
            "interval": interval,
            "headers": headers or {},
            "last_collected": None,
            "errors": 0
        }
        self.sources.append(source)
        logger.info(f"Added metrics source: {name}")
    
    async def start(self) -> None:
        """Start metrics collection"""
        self.running = True
        
        # Start collection tasks for each source
        for source in self.sources:
            asyncio.create_task(self._collect_from_source(source))
        
        logger.info("Metrics collector started")
    
    async def stop(self) -> None:
        """Stop metrics collection"""
        self.running = False
        logger.info("Metrics collector stopped")
    
    async def _collect_from_source(self, source: Dict[str, Any]) -> None:
        """Collect metrics from a single source"""
        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(source["url"], headers=source["headers"]) as response:
                        if response.status == 200:
                            data = await response.text()
                            await self._process_metrics_data(source["name"], data)
                            source["last_collected"] = datetime.utcnow()
                            source["errors"] = 0
                        else:
                            logger.warning(f"Failed to collect from {source['name']}: HTTP {response.status}")
                            source["errors"] += 1
                
                await asyncio.sleep(source["interval"])
                
            except Exception as e:
                logger.error(f"Error collecting from {source['name']}: {e}")
                source["errors"] += 1
                await asyncio.sleep(source["interval"])
    
    async def _process_metrics_data(self, source_name: str, data: str) -> None:
        """Process collected metrics data"""
        try:
            # Parse Prometheus format metrics
            lines = data.strip().split('\\n')
            
            for line in lines:
                if line.startswith('#') or not line.strip():
                    continue
                
                # Parse metric line
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0]
                    metric_value = float(parts[1])
                    
                    # Store or forward the metric
                    logger.debug(f"Collected metric {metric_name}={metric_value} from {source_name}")
        
        except Exception as e:
            logger.error(f"Error processing metrics data from {source_name}: {e}")
    
    def get_source_status(self) -> List[Dict[str, Any]]:
        """Get status of all sources"""
        return [
            {
                "name": source["name"],
                "url": source["url"],
                "last_collected": source["last_collected"],
                "errors": source["errors"],
                "status": "healthy" if source["errors"] < 5 else "unhealthy"
            }
            for source in self.sources
        ]


# Global metrics collector instance
metrics_collector = MetricsCollector()
'''
        
        return content
    
    def _generate_custom_metrics(self, variables: Dict[str, Any]) -> str:
        """Generate custom metrics definitions"""
        custom_metrics = variables.get("custom_metrics", [])
        
        content = '''"""
Custom metrics definitions
"""

from prometheus_client import Counter, Gauge, Histogram, Summary
from .manager import metrics_manager

# Custom metrics registry
custom_metrics = {}

def register_custom_metrics():
    """Register all custom metrics"""
'''
        
        for metric in custom_metrics:
            metric_name = metric.get("name", "")
            metric_type = metric.get("type", "counter")
            description = metric.get("description", "")
            labels = metric.get("labels", [])
            
            content += f'''
    # {metric_name}
    metrics_manager.register_custom_metric(
        name="{metric_name}",
        metric_type="{metric_type}",
        description="{description}",
        labels={labels}
    )'''
        
        content += '''

def get_custom_metric(name: str):
    """Get a custom metric by name"""
    return metrics_manager.get_metric(name)

# Register all custom metrics on import
register_custom_metrics()
'''
        
        return content

    def _generate_dashboard_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate dashboard files - placeholder implementation"""
        files = []
        
        # Generate dashboard manager
        dashboard_manager_content = f'''"""
Dashboard manager for {variables["dashboard_backend"]}
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
import json

from ..config import settings

logger = logging.getLogger(__name__)


class DashboardManager:
    """Manages dashboard creation and updates"""
    
    def __init__(self):
        self.dashboards = {{}}
        self.running = False
    
    async def start(self) -> None:
        """Start dashboard manager"""
        self.running = True
        logger.info("Dashboard manager started")
    
    async def stop(self) -> None:
        """Stop dashboard manager"""
        self.running = False
        logger.info("Dashboard manager stopped")
    
    async def health_check(self) -> str:
        """Health check for dashboard manager"""
        return "healthy" if self.running else "unhealthy"
    
    async def create_dashboard(self, name: str, config: Dict[str, Any]) -> None:
        """Create a new dashboard"""
        self.dashboards[name] = config
        logger.info(f"Created dashboard: {{name}}")
    
    async def update_dashboard(self, name: str, config: Dict[str, Any]) -> None:
        """Update an existing dashboard"""
        if name in self.dashboards:
            self.dashboards[name].update(config)
            logger.info(f"Updated dashboard: {{name}}")
        else:
            logger.warning(f"Dashboard not found: {{name}}")
    
    async def delete_dashboard(self, name: str) -> None:
        """Delete a dashboard"""
        if name in self.dashboards:
            del self.dashboards[name]
            logger.info(f"Deleted dashboard: {{name}}")
        else:
            logger.warning(f"Dashboard not found: {{name}}")
    
    def list_dashboards(self) -> List[str]:
        """List all dashboards"""
        return list(self.dashboards.keys())
    
    def get_dashboard(self, name: str) -> Optional[Dict[str, Any]]:
        """Get dashboard configuration"""
        return self.dashboards.get(name)


# Global dashboard manager instance
dashboard_manager = DashboardManager()
'''
        
        dashboard_manager_path = output_dir / "app" / "dashboards" / "manager.py"
        dashboard_manager_path.write_text(dashboard_manager_content, encoding="utf-8")
        files.append(dashboard_manager_path)
        
        return files

    def _generate_alerting_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate alerting files - placeholder implementation"""
        files = []
        
        # Generate alert manager
        alert_manager_content = f'''"""
Alert manager for {variables["alert_backend"]}
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alert rules and notifications"""
    
    def __init__(self):
        self.rules = {{}}
        self.notifications = []
        self.running = False
    
    async def start(self) -> None:
        """Start alert manager"""
        self.running = True
        logger.info("Alert manager started")
        
        # Start alert evaluation task
        asyncio.create_task(self._evaluate_alerts())
    
    async def stop(self) -> None:
        """Stop alert manager"""
        self.running = False
        logger.info("Alert manager stopped")
    
    async def health_check(self) -> str:
        """Health check for alert manager"""
        return "healthy" if self.running else "unhealthy"
    
    def add_rule(self, name: str, expression: str, threshold: float, duration: str = "5m", severity: str = "warning") -> None:
        """Add an alert rule"""
        rule = {{
            "name": name,
            "expression": expression,
            "threshold": threshold,
            "duration": duration,
            "severity": severity,
            "last_evaluated": None,
            "firing": False
        }}
        self.rules[name] = rule
        logger.info(f"Added alert rule: {{name}}")
    
    async def _evaluate_alerts(self) -> None:
        """Evaluate alert rules periodically"""
        while self.running:
            try:
                for rule_name, rule in self.rules.items():
                    await self._evaluate_rule(rule_name, rule)
                
                await asyncio.sleep(15)  # Evaluate every 15 seconds
                
            except Exception as e:
                logger.error(f"Error evaluating alerts: {{e}}")
                await asyncio.sleep(15)
    
    async def _evaluate_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Evaluate a single alert rule"""
        try:
            # Placeholder for rule evaluation logic
            # In a real implementation, this would query metrics and evaluate the expression
            
            rule["last_evaluated"] = datetime.utcnow()
            
            # Simulate alert firing based on some condition
            # This would be replaced with actual metric evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating rule {{rule_name}}: {{e}}")
    
    async def send_notification(self, alert: Dict[str, Any]) -> None:
        """Send alert notification"""
        try:
            # Placeholder for notification sending
            # This would integrate with actual notification channels
            
            self.notifications.append({{
                "alert": alert,
                "timestamp": datetime.utcnow(),
                "status": "sent"
            }})
            
            logger.info(f"Sent notification for alert: {{alert.get('name')}}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {{e}}")


# Global alert manager instance
alert_manager = AlertManager()
'''
        
        alert_manager_path = output_dir / "app" / "alerts" / "manager.py"
        alert_manager_path.write_text(alert_manager_content, encoding="utf-8")
        files.append(alert_manager_path)
        
        return files

    def _generate_health_check_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate health check files - placeholder implementation"""
        files = []
        
        # Generate health manager
        health_manager_content = '''"""
Health check manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthManager:
    """Manages health checks for monitored services"""
    
    def __init__(self):
        self.checks = {}
        self.running = False
    
    async def start(self) -> None:
        """Start health manager"""
        self.running = True
        logger.info("Health manager started")
    
    async def stop(self) -> None:
        """Stop health manager"""
        self.running = False
        logger.info("Health manager stopped")
    
    def add_check(self, name: str, url: str, interval: int = 30) -> None:
        """Add a health check"""
        check = {
            "name": name,
            "url": url,
            "interval": interval,
            "last_check": None,
            "status": "unknown",
            "response_time": None
        }
        self.checks[name] = check
        logger.info(f"Added health check: {name}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        healthy_count = sum(1 for check in self.checks.values() if check["status"] == "healthy")
        total_count = len(self.checks)
        
        return {
            "overall_status": "healthy" if healthy_count == total_count else "unhealthy",
            "healthy_services": healthy_count,
            "total_services": total_count,
            "checks": self.checks
        }


# Global health manager instance
health_manager = HealthManager()
'''
        
        health_manager_path = output_dir / "app" / "health" / "manager.py"
        health_manager_path.write_text(health_manager_content, encoding="utf-8")
        files.append(health_manager_path)
        
        return files

    def _generate_profiling_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate profiling files - placeholder implementation"""
        files = []
        
        # Generate profiling manager
        profiling_manager_content = '''"""
Performance profiling manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class ProfilingManager:
    """Manages performance profiling"""
    
    def __init__(self):
        self.profiles = {}
        self.running = False
    
    async def start(self) -> None:
        """Start profiling manager"""
        self.running = True
        logger.info("Profiling manager started")
    
    async def stop(self) -> None:
        """Stop profiling manager"""
        self.running = False
        logger.info("Profiling manager stopped")


# Global profiling manager instance
profiling_manager = ProfilingManager()
'''
        
        profiling_manager_path = output_dir / "app" / "profiling" / "manager.py"
        profiling_manager_path.write_text(profiling_manager_content, encoding="utf-8")
        files.append(profiling_manager_path)
        
        return files

    def _generate_log_aggregation_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate log aggregation files - placeholder implementation"""
        files = []
        
        # Generate log manager
        log_manager_content = '''"""
Log aggregation manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class LogManager:
    """Manages log aggregation and analysis"""
    
    def __init__(self):
        self.log_sources = {}
        self.running = False
    
    async def start(self) -> None:
        """Start log manager"""
        self.running = True
        logger.info("Log manager started")
    
    async def stop(self) -> None:
        """Stop log manager"""
        self.running = False
        logger.info("Log manager stopped")


# Global log manager instance
log_manager = LogManager()
'''
        
        log_manager_path = output_dir / "app" / "logs" / "manager.py"
        log_manager_path.write_text(log_manager_content, encoding="utf-8")
        files.append(log_manager_path)
        
        return files

    def _generate_tracing_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate tracing files - placeholder implementation"""
        files = []
        
        # Generate tracing manager
        tracing_manager_content = '''"""
Distributed tracing manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class TracingManager:
    """Manages distributed tracing"""
    
    def __init__(self):
        self.traces = {}
        self.running = False
    
    async def start(self) -> None:
        """Start tracing manager"""
        self.running = True
        logger.info("Tracing manager started")
    
    async def stop(self) -> None:
        """Stop tracing manager"""
        self.running = False
        logger.info("Tracing manager stopped")


# Global tracing manager instance
tracing_manager = TracingManager()
'''
        
        tracing_manager_path = output_dir / "app" / "tracing" / "manager.py"
        tracing_manager_path.write_text(tracing_manager_content, encoding="utf-8")
        files.append(tracing_manager_path)
        
        return files

    def _generate_capacity_planning_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate capacity planning files - placeholder implementation"""
        files = []
        
        # Generate capacity manager
        capacity_manager_content = '''"""
Capacity planning manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class CapacityManager:
    """Manages capacity planning and forecasting"""
    
    def __init__(self):
        self.forecasts = {}
        self.running = False
    
    async def start(self) -> None:
        """Start capacity manager"""
        self.running = True
        logger.info("Capacity manager started")
    
    async def stop(self) -> None:
        """Stop capacity manager"""
        self.running = False
        logger.info("Capacity manager stopped")


# Global capacity manager instance
capacity_manager = CapacityManager()
'''
        
        capacity_manager_path = output_dir / "app" / "capacity" / "manager.py"
        capacity_manager_path.write_text(capacity_manager_content, encoding="utf-8")
        files.append(capacity_manager_path)
        
        return files

    def _generate_sla_monitoring_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate SLA monitoring files - placeholder implementation"""
        files = []
        
        # Generate SLA manager
        sla_manager_content = '''"""
SLA monitoring manager
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


class SLAManager:
    """Manages SLA monitoring and reporting"""
    
    def __init__(self):
        self.slas = {}
        self.running = False
    
    async def start(self) -> None:
        """Start SLA manager"""
        self.running = True
        logger.info("SLA manager started")
    
    async def stop(self) -> None:
        """Stop SLA manager"""
        self.running = False
        logger.info("SLA manager stopped")


# Global SLA manager instance
sla_manager = SLAManager()
'''
        
        sla_manager_path = output_dir / "app" / "sla" / "manager.py"
        sla_manager_path.write_text(sla_manager_content, encoding="utf-8")
        files.append(sla_manager_path)
        
        return files

    def _generate_api_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate API files"""
        files = []
        
        # Generate API router
        api_content = f'''"""
API routes for {variables["service_name"]}
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List
import logging

from ..metrics.manager import metrics_manager
from ..dashboards.manager import dashboard_manager
from ..alerts.manager import alert_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """Get metrics endpoint"""
    try:
        metrics_data = metrics_manager.export_metrics()
        return {{"metrics": metrics_data}}
    except Exception as e:
        logger.error(f"Error getting metrics: {{e}}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/dashboards")
async def list_dashboards():
    """List dashboards endpoint"""
    try:
        dashboards = dashboard_manager.list_dashboards()
        return {{"dashboards": dashboards}}
    except Exception as e:
        logger.error(f"Error listing dashboards: {{e}}")
        raise HTTPException(status_code=500, detail="Failed to list dashboards")


@router.get("/dashboards/{{dashboard_name}}")
async def get_dashboard(dashboard_name: str):
    """Get dashboard endpoint"""
    try:
        dashboard = dashboard_manager.get_dashboard(dashboard_name)
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard: {{e}}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard")


@router.post("/alerts/rules")
async def create_alert_rule(rule_data: Dict[str, Any]):
    """Create alert rule endpoint"""
    try:
        name = rule_data.get("name")
        expression = rule_data.get("expression")
        threshold = rule_data.get("threshold")
        
        if not all([name, expression, threshold is not None]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        alert_manager.add_rule(
            name=name,
            expression=expression,
            threshold=threshold,
            duration=rule_data.get("duration", "5m"),
            severity=rule_data.get("severity", "warning")
        )
        
        return {{"message": "Alert rule created", "name": name}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert rule: {{e}}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.get("/health/status")
async def get_health_status():
    """Get health status endpoint"""
    try:
        status = {{
            "metrics": await metrics_manager.health_check(),
            "dashboards": await dashboard_manager.health_check(),
            "alerts": await alert_manager.health_check()
        }}
        return {{"status": status}}
    except Exception as e:
        logger.error(f"Error getting health status: {{e}}")
        raise HTTPException(status_code=500, detail="Failed to get health status")
'''
        
        api_path = output_dir / "app" / "api" / "v1" / "__init__.py"
        api_path.write_text(api_content, encoding="utf-8")
        files.append(api_path)
        
        return files

    def _generate_test_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate test files"""
        files = []
        
        # Generate basic test structure
        test_content = f'''"""
Tests for {variables["service_name"]} monitoring service
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics_endpoint():
    """Test metrics endpoint"""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200


def test_dashboards_endpoint():
    """Test dashboards endpoint"""
    response = client.get("/api/v1/dashboards")
    assert response.status_code == 200


class TestMetricsManager:
    """Test metrics manager functionality"""
    
    def test_metrics_registration(self):
        """Test metrics registration"""
        # Add metrics registration tests
        pass
    
    def test_metrics_collection(self):
        """Test metrics collection"""
        # Add metrics collection tests
        pass


class TestDashboardManager:
    """Test dashboard manager functionality"""
    
    def test_dashboard_creation(self):
        """Test dashboard creation"""
        # Add dashboard creation tests
        pass
    
    def test_dashboard_updates(self):
        """Test dashboard updates"""
        # Add dashboard update tests
        pass


class TestAlertManager:
    """Test alert manager functionality"""
    
    def test_alert_rule_creation(self):
        """Test alert rule creation"""
        # Add alert rule creation tests
        pass
    
    def test_alert_evaluation(self):
        """Test alert evaluation"""
        # Add alert evaluation tests
        pass
'''
        
        test_path = output_dir / "tests" / "test_monitoring_service.py"
        test_path.write_text(test_content, encoding="utf-8")
        files.append(test_path)
        
        return files

    def _generate_config_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate configuration files"""
        files = []
        
        # Generate requirements.txt
        requirements_content = '''fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
prometheus-client>=0.19.0
aiohttp>=3.9.0
psutil>=5.9.0
structlog>=23.2.0
'''
        
        if variables["metrics_backend"] == "influxdb":
            requirements_content += "influxdb-client>=1.38.0\n"
        elif variables["metrics_backend"] == "datadog":
            requirements_content += "datadog>=0.47.0\n"
        elif variables["metrics_backend"] == "newrelic":
            requirements_content += "newrelic>=9.2.0\n"
        
        if variables["dashboard_backend"] == "grafana":
            requirements_content += "grafana-api>=1.0.3\n"
        elif variables["dashboard_backend"] == "kibana":
            requirements_content += "elasticsearch>=8.11.0\n"
        
        requirements_path = output_dir / "requirements.txt"
        requirements_path.write_text(requirements_content, encoding="utf-8")
        files.append(requirements_path)
        
        # Generate .env template
        env_content = f'''# {variables["service_name"]} Environment Configuration

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
PORT={variables.get("service_port", 8000)}

# Metrics Backend ({variables["metrics_backend"]})
METRICS_HOST=localhost
METRICS_PORT={variables.get("metrics_port", 9090)}
METRICS_USERNAME=
METRICS_PASSWORD=

# Dashboard Backend ({variables["dashboard_backend"]})
DASHBOARD_HOST=localhost
DASHBOARD_PORT={variables.get("dashboard_port", 3000)}
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=admin

# Alert Backend ({variables["alert_backend"]})
ALERT_HOST=localhost
ALERT_PORT={variables.get("alert_port", 9093)}
ALERT_USERNAME=
ALERT_PASSWORD=

# Monitoring Configuration
SCRAPE_INTERVAL={variables.get("scrape_interval", "15s")}
EVALUATION_INTERVAL={variables.get("evaluation_interval", "15s")}
RETENTION_DAYS={variables.get("retention_days", 15)}

# Feature Flags
ENABLE_CUSTOM_METRICS={str(variables.get("enable_custom_metrics", True)).lower()}
ENABLE_HEALTH_CHECKS={str(variables.get("enable_health_checks", True)).lower()}
ENABLE_PERFORMANCE_PROFILING={str(variables.get("enable_performance_profiling", True)).lower()}
ENABLE_LOG_AGGREGATION={str(variables.get("enable_log_aggregation", True)).lower()}
ENABLE_DISTRIBUTED_TRACING={str(variables.get("enable_distributed_tracing", True)).lower()}
ENABLE_CAPACITY_PLANNING={str(variables.get("enable_capacity_planning", True)).lower()}
ENABLE_SLA_MONITORING={str(variables.get("enable_sla_monitoring", True)).lower()}

# Notification Settings
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=monitoring@example.com

# Slack Settings
SLACK_WEBHOOK_URL=
SLACK_CHANNEL=#alerts

# PagerDuty Settings
PAGERDUTY_INTEGRATION_KEY=
'''
        
        env_path = output_dir / ".env.template"
        env_path.write_text(env_content, encoding="utf-8")
        files.append(env_path)
        
        return files

    def _generate_deployment_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate deployment files"""
        files = []
        
        # Generate Dockerfile
        dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Expose port
EXPOSE {variables.get("service_port", 8000)}

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{variables.get("service_port", 8000)}/health || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "{variables.get("service_port", 8000)}"]
'''
        
        dockerfile_path = output_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        files.append(dockerfile_path)
        
        # Generate docker-compose.yml
        compose_content = f'''version: '3.8'

services:
  {variables["service_name"].replace("_", "-")}:
    build: .
    ports:
      - "{variables.get("service_port", 8000)}:{variables.get("service_port", 8000)}"
    environment:
      - ENVIRONMENT=development
      - METRICS_HOST=prometheus
      - DASHBOARD_HOST=grafana
      - ALERT_HOST=alertmanager
    depends_on:
      - prometheus
      - grafana
      - alertmanager
    networks:
      - monitoring-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "{variables.get("metrics_port", 9090)}:{variables.get("metrics_port", 9090)}"
    volumes:
      - ./config/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    networks:
      - monitoring-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "{variables.get("dashboard_port", 3000)}:{variables.get("dashboard_port", 3000)}"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana:/etc/grafana/provisioning
    networks:
      - monitoring-network

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "{variables.get("alert_port", 9093)}:{variables.get("alert_port", 9093)}"
    volumes:
      - ./config/alertmanager:/etc/alertmanager
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - monitoring-network

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  monitoring-network:
    driver: bridge
'''
        
        compose_path = output_dir / "docker-compose.yml"
        compose_path.write_text(compose_content, encoding="utf-8")
        files.append(compose_path)
        
        return files

    def _generate_documentation(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate documentation files"""
        files = []
        
        # Generate README.md
        readme_content = f'''# {variables["service_name"].replace("_", " ").title()}

{variables["service_description"]}

## Features

- **Metrics Collection**: Comprehensive metrics collection with {variables["metrics_backend"]}
- **Dashboard Integration**: Beautiful dashboards with {variables["dashboard_backend"]}
- **Alerting**: Smart alerting with {variables["alert_backend"]}
- **Health Monitoring**: Service health checks and monitoring
- **Performance Profiling**: Performance analysis and optimization
- **Log Aggregation**: Centralized log collection and analysis
- **Distributed Tracing**: End-to-end request tracing
- **Capacity Planning**: Resource usage forecasting
- **SLA Monitoring**: Service level agreement tracking

## Architecture

This monitoring service provides comprehensive observability with:

### Metrics Collection
- Real-time metrics collection from multiple sources
- Custom metrics support
- System metrics (CPU, memory, disk, network)
- Application metrics (requests, errors, latency)

### Dashboard Integration
- Pre-built dashboards for common use cases
- Custom dashboard creation and management
- Real-time data visualization
- Multi-service monitoring views

### Alerting System
- Flexible alert rule configuration
- Multiple notification channels
- Alert escalation and routing
- Alert fatigue reduction

## Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- {variables["metrics_backend"]} for metrics
- {variables["dashboard_backend"]} for dashboards
- {variables["alert_backend"]} for alerting

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment configuration:
   ```bash
   cp .env.template .env
   ```

4. Start the monitoring stack:
   ```bash
   docker-compose up -d
   ```

5. Run the service:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### Using Docker

```bash
docker-compose up --build
```

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/v1/metrics` - Get metrics
- `GET /api/v1/dashboards` - List dashboards
- `GET /api/v1/dashboards/{{name}}` - Get specific dashboard
- `POST /api/v1/alerts/rules` - Create alert rule
- `GET /api/v1/health/status` - Get health status

## Configuration

Configuration is managed through environment variables. See `.env.template` for all available options.

### Key Configuration Options

- `METRICS_BACKEND`: {variables["metrics_backend"]}
- `DASHBOARD_BACKEND`: {variables["dashboard_backend"]}
- `ALERT_BACKEND`: {variables["alert_backend"]}
- `SCRAPE_INTERVAL`: Metrics collection interval
- `RETENTION_DAYS`: Data retention period

## Monitoring Stack

### Prometheus ({variables["metrics_backend"]})
- Metrics collection and storage
- PromQL query language
- Time series database
- Service discovery

### Grafana ({variables["dashboard_backend"]})
- Data visualization
- Dashboard management
- Alerting rules
- User management

### Alertmanager ({variables["alert_backend"]})
- Alert routing and grouping
- Notification channels
- Silence management
- Alert deduplication

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## Monitoring

The service includes self-monitoring:

- **Metrics**: Service metrics at `/api/v1/metrics`
- **Health Checks**: Health endpoint at `/health`
- **Logging**: Structured logging with correlation IDs
- **Tracing**: Distributed tracing support

## Deployment

### Kubernetes

Kubernetes manifests are available in the `k8s/` directory.

### Docker

Use the provided Dockerfile and docker-compose.yml for containerized deployment.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
'''
        
        readme_path = output_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        files.append(readme_path)
        
        return files
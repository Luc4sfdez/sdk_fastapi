"""
Docker Compose generator for FastAPI microservices.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


class ComposeGenerator:
    """Generate Docker Compose configurations for microservices."""
    
    def __init__(self):
        self.version = "3.8"
        self.networks = {
            "microservices": {
                "driver": "bridge"
            }
        }
        self.volumes = {}
    
    def generate(self, service_name: str, service_path: Path, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate docker-compose.yml content for a single service."""
        
        if config is None:
            config = self._detect_service_config(service_path)
        
        compose_config = {
            "version": self.version,
            "services": {
                service_name: self._generate_service_config(service_name, config)
            },
            "networks": self.networks
        }
        
        # Add volumes if needed
        if self.volumes:
            compose_config["volumes"] = self.volumes
        
        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
    
    def generate_full_stack(
        self, 
        services: List[Dict[str, Any]], 
        include_infrastructure: bool = True
    ) -> str:
        """Generate complete docker-compose.yml with multiple services and infrastructure."""
        
        compose_config = {
            "version": self.version,
            "services": {},
            "networks": self.networks,
            "volumes": {}
        }
        
        # Add infrastructure services
        if include_infrastructure:
            compose_config["services"].update(self._get_infrastructure_services())
            compose_config["volumes"].update(self._get_infrastructure_volumes())
        
        # Add application services
        for service_info in services:
            service_name = service_info["name"]
            service_config = service_info.get("config", {})
            
            compose_config["services"][service_name] = self._generate_service_config(
                service_name, service_config
            )
        
        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
    
    def _detect_service_config(self, service_path: Path) -> Dict[str, Any]:
        """Detect service configuration from files."""
        
        config = {
            "port": 8000,
            "build_context": ".",
            "dockerfile": "Dockerfile",
            "environment": {},
            "depends_on": [],
            "volumes": [],
            "enable_database": False,
            "enable_redis": False,
            "enable_rabbitmq": False,
            "enable_monitoring": False
        }
        
        # Check for .env file
        env_file = service_path / ".env"
        if env_file.exists():
            config["environment"].update(self._parse_env_file(env_file))
            config["port"] = int(config["environment"].get("SERVICE_PORT", 8000))
        
        # Check for requirements.txt to detect dependencies
        requirements_file = service_path / "requirements.txt"
        if requirements_file.exists():
            dependencies = self._parse_requirements(requirements_file)
            
            # Detect database dependencies
            db_packages = ["psycopg2", "asyncpg", "pymongo", "motor", "aiomysql", "mysqlclient"]
            if any(pkg in dep for dep in dependencies for pkg in db_packages):
                config["enable_database"] = True
                config["depends_on"].append("postgres")
            
            # Detect Redis
            if any("redis" in dep for dep in dependencies):
                config["enable_redis"] = True
                config["depends_on"].append("redis")
            
            # Detect RabbitMQ
            if any("pika" in dep or "aio-pika" in dep for dep in dependencies):
                config["enable_rabbitmq"] = True
                config["depends_on"].append("rabbitmq")
        
        return config
    
    def _parse_env_file(self, env_file: Path) -> Dict[str, str]:
        """Parse environment variables from .env file."""
        
        env_vars = {}
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception:
            pass
        
        return env_vars
    
    def _parse_requirements(self, requirements_file: Path) -> List[str]:
        """Parse requirements.txt file."""
        
        dependencies = []
        
        try:
            with open(requirements_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        dependencies.append(line.lower())
        except Exception:
            pass
        
        return dependencies
    
    def _generate_service_config(self, service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Docker Compose service configuration."""
        
        service_config = {
            "build": {
                "context": config.get("build_context", "."),
                "dockerfile": config.get("dockerfile", "Dockerfile")
            },
            "ports": [
                f"{config.get('port', 8000)}:{config.get('port', 8000)}"
            ],
            "environment": self._get_service_environment(service_name, config),
            "networks": ["microservices"],
            "restart": "unless-stopped"
        }
        
        # Add dependencies
        if config.get("depends_on"):
            service_config["depends_on"] = config["depends_on"]
        
        # Add volumes
        if config.get("volumes"):
            service_config["volumes"] = config["volumes"]
        
        # Add health check
        service_config["healthcheck"] = {
            "test": f"curl -f http://localhost:{config.get('port', 8000)}/health || exit 1",
            "interval": "30s",
            "timeout": "10s",
            "retries": 3,
            "start_period": "10s"
        }
        
        return service_config
    
    def _get_service_environment(self, service_name: str, config: Dict[str, Any]) -> Dict[str, str]:
        """Get environment variables for a service."""
        
        environment = {
            "SERVICE_NAME": service_name,
            "SERVICE_PORT": str(config.get("port", 8000)),
            "ENVIRONMENT": "development"
        }
        
        # Add database environment if enabled
        if config.get("enable_database"):
            environment.update({
                "DATABASE_HOST": "postgres",
                "DATABASE_PORT": "5432",
                "DATABASE_USER": "postgres",
                "DATABASE_PASSWORD": "password",
                "DATABASE_DB": service_name.replace("-", "_")
            })
        
        # Add Redis environment if enabled
        if config.get("enable_redis"):
            environment.update({
                "REDIS_HOST": "redis",
                "REDIS_PORT": "6379"
            })
        
        # Add RabbitMQ environment if enabled
        if config.get("enable_rabbitmq"):
            environment.update({
                "RABBITMQ_HOST": "rabbitmq",
                "RABBITMQ_PORT": "5672",
                "RABBITMQ_USER": "guest",
                "RABBITMQ_PASSWORD": "guest"
            })
        
        # Merge with custom environment
        environment.update(config.get("environment", {}))
        
        return environment
    
    def _get_infrastructure_services(self) -> Dict[str, Any]:
        """Get infrastructure services configuration."""
        
        return {
            "postgres": {
                "image": "postgres:15",
                "environment": {
                    "POSTGRES_DB": "microservices",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "password"
                },
                "ports": ["5432:5432"],
                "volumes": ["postgres_data:/var/lib/postgresql/data"],
                "networks": ["microservices"],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": "pg_isready -U postgres",
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5
                }
            },
            "redis": {
                "image": "redis:7-alpine",
                "ports": ["6379:6379"],
                "volumes": ["redis_data:/data"],
                "networks": ["microservices"],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": "redis-cli ping",
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 5
                }
            },
            "rabbitmq": {
                "image": "rabbitmq:3-management",
                "environment": {
                    "RABBITMQ_DEFAULT_USER": "guest",
                    "RABBITMQ_DEFAULT_PASS": "guest"
                },
                "ports": ["5672:5672", "15672:15672"],
                "volumes": ["rabbitmq_data:/var/lib/rabbitmq"],
                "networks": ["microservices"],
                "restart": "unless-stopped",
                "healthcheck": {
                    "test": "rabbitmq-diagnostics -q ping",
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 5
                }
            },
            "jaeger": {
                "image": "jaegertracing/all-in-one:latest",
                "environment": {
                    "COLLECTOR_OTLP_ENABLED": "true"
                },
                "ports": [
                    "16686:16686",  # Jaeger UI
                    "14268:14268",  # HTTP collector
                    "4317:4317",    # OTLP gRPC
                    "4318:4318"     # OTLP HTTP
                ],
                "networks": ["microservices"],
                "restart": "unless-stopped"
            },
            "prometheus": {
                "image": "prom/prometheus:latest",
                "ports": ["9090:9090"],
                "volumes": [
                    "./config/prometheus.yml:/etc/prometheus/prometheus.yml"
                ],
                "networks": ["microservices"],
                "restart": "unless-stopped"
            },
            "grafana": {
                "image": "grafana/grafana:latest",
                "environment": {
                    "GF_SECURITY_ADMIN_PASSWORD": "admin"
                },
                "ports": ["3000:3000"],
                "volumes": ["grafana_data:/var/lib/grafana"],
                "networks": ["microservices"],
                "restart": "unless-stopped"
            }
        }
    
    def _get_infrastructure_volumes(self) -> Dict[str, Any]:
        """Get infrastructure volumes configuration."""
        
        return {
            "postgres_data": {},
            "redis_data": {},
            "rabbitmq_data": {},
            "grafana_data": {}
        }
    
    def generate_development_compose(self, services: List[Dict[str, Any]]) -> str:
        """Generate docker-compose.yml optimized for development."""
        
        compose_config = {
            "version": self.version,
            "services": {},
            "networks": self.networks,
            "volumes": self._get_infrastructure_volumes()
        }
        
        # Add infrastructure services
        compose_config["services"].update(self._get_infrastructure_services())
        
        # Add application services with development optimizations
        for service_info in services:
            service_name = service_info["name"]
            service_config = service_info.get("config", {})
            
            # Development optimizations
            dev_service_config = self._generate_service_config(service_name, service_config)
            
            # Add volume mounts for hot reload
            dev_service_config["volumes"] = [
                f"./{service_name}:/app",
                "/app/__pycache__"  # Exclude pycache
            ]
            
            # Override command for development
            dev_service_config["command"] = [
                "python", "-m", "uvicorn", "main:app", 
                "--host", "0.0.0.0", 
                "--port", str(service_config.get("port", 8000)),
                "--reload"
            ]
            
            # Add development environment variables
            dev_service_config["environment"]["ENVIRONMENT"] = "development"
            dev_service_config["environment"]["DEBUG"] = "true"
            
            compose_config["services"][service_name] = dev_service_config
        
        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
    
    def generate_production_compose(self, services: List[Dict[str, Any]]) -> str:
        """Generate docker-compose.yml optimized for production."""
        
        compose_config = {
            "version": self.version,
            "services": {},
            "networks": self.networks,
            "volumes": self._get_infrastructure_volumes()
        }
        
        # Add infrastructure services with production settings
        infra_services = self._get_infrastructure_services()
        
        # Production optimizations for infrastructure
        for service_name, service_config in infra_services.items():
            # Add resource limits
            service_config["deploy"] = {
                "resources": {
                    "limits": {
                        "memory": "512M"
                    },
                    "reservations": {
                        "memory": "256M"
                    }
                }
            }
            
            # Remove development ports for some services
            if service_name == "rabbitmq":
                service_config["ports"] = ["5672:5672"]  # Remove management UI
        
        compose_config["services"].update(infra_services)
        
        # Add application services with production optimizations
        for service_info in services:
            service_name = service_info["name"]
            service_config = service_info.get("config", {})
            
            prod_service_config = self._generate_service_config(service_name, service_config)
            
            # Production optimizations
            prod_service_config["deploy"] = {
                "replicas": service_config.get("replicas", 1),
                "resources": {
                    "limits": {
                        "memory": service_config.get("memory_limit", "256M")
                    },
                    "reservations": {
                        "memory": service_config.get("memory_reservation", "128M")
                    }
                }
            }
            
            # Production environment variables
            prod_service_config["environment"]["ENVIRONMENT"] = "production"
            prod_service_config["environment"]["DEBUG"] = "false"
            
            compose_config["services"][service_name] = prod_service_config
        
        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
    
    def generate_monitoring_compose(self) -> str:
        """Generate docker-compose.yml for monitoring stack only."""
        
        compose_config = {
            "version": self.version,
            "services": {
                "prometheus": self._get_infrastructure_services()["prometheus"],
                "grafana": self._get_infrastructure_services()["grafana"],
                "jaeger": self._get_infrastructure_services()["jaeger"]
            },
            "networks": self.networks,
            "volumes": {
                "grafana_data": {}
            }
        }
        
        return yaml.dump(compose_config, default_flow_style=False, sort_keys=False)
    
    def save_compose_file(self, content: str, output_path: Path, filename: str = "docker-compose.yml") -> Path:
        """Save docker-compose.yml content to file."""
        
        compose_path = output_path / filename
        compose_path.write_text(content)
        
        return compose_path
    
    def generate_prometheus_config(self) -> str:
        """Generate Prometheus configuration."""
        
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "scrape_configs": [
                {
                    "job_name": "prometheus",
                    "static_configs": [
                        {"targets": ["localhost:9090"]}
                    ]
                },
                {
                    "job_name": "microservices",
                    "static_configs": [
                        {"targets": ["host.docker.internal:8000"]}
                    ],
                    "metrics_path": "/metrics",
                    "scrape_interval": "10s"
                }
            ]
        }
        
        return yaml.dump(prometheus_config, default_flow_style=False)
    
    def save_prometheus_config(self, output_path: Path) -> Path:
        """Save Prometheus configuration file."""
        
        config_dir = output_path / "config"
        config_dir.mkdir(exist_ok=True)
        
        prometheus_config = self.generate_prometheus_config()
        prometheus_path = config_dir / "prometheus.yml"
        prometheus_path.write_text(prometheus_config)
        
        return prometheus_path
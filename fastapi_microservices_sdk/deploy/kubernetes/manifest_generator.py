"""
Kubernetes manifest generator for FastAPI microservices.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional


class ManifestGenerator:
    """Generate Kubernetes manifests for FastAPI microservices."""
    
    def __init__(self):
        self.api_version = "apps/v1"
        self.service_api_version = "v1"
        self.ingress_api_version = "networking.k8s.io/v1"
        self.configmap_api_version = "v1"
    
    def generate(
        self, 
        service_name: str, 
        service_path: Path, 
        namespace: str = "default",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Generate all Kubernetes manifests for a service."""
        
        if config is None:
            config = self._detect_service_config(service_path)
        
        manifests = {}
        
        # Generate Deployment
        manifests["deployment.yaml"] = self._generate_deployment(service_name, namespace, config)
        
        # Generate Service
        manifests["service.yaml"] = self._generate_service(service_name, namespace, config)
        
        # Generate ConfigMap if needed
        if config.get("environment"):
            manifests["configmap.yaml"] = self._generate_configmap(service_name, namespace, config)
        
        # Generate Ingress if enabled
        if config.get("enable_ingress", False):
            manifests["ingress.yaml"] = self._generate_ingress(service_name, namespace, config)
        
        # Generate HPA if enabled
        if config.get("enable_hpa", False):
            manifests["hpa.yaml"] = self._generate_hpa(service_name, namespace, config)
        
        # Generate ServiceMonitor for Prometheus if enabled
        if config.get("enable_monitoring", False):
            manifests["servicemonitor.yaml"] = self._generate_service_monitor(service_name, namespace, config)
        
        return manifests
    
    def _detect_service_config(self, service_path: Path) -> Dict[str, Any]:
        """Detect service configuration from files."""
        
        config = {
            "image": "microservice:latest",
            "port": 8000,
            "replicas": 1,
            "resources": {
                "requests": {
                    "memory": "128Mi",
                    "cpu": "100m"
                },
                "limits": {
                    "memory": "256Mi",
                    "cpu": "200m"
                }
            },
            "environment": {},
            "enable_ingress": False,
            "enable_hpa": False,
            "enable_monitoring": True,
            "health_check_path": "/health",
            "readiness_check_path": "/health"
        }
        
        # Check for .env file
        env_file = service_path / ".env"
        if env_file.exists():
            config["environment"].update(self._parse_env_file(env_file))
            config["port"] = int(config["environment"].get("SERVICE_PORT", 8000))
        
        # Check for Dockerfile to determine image name
        dockerfile = service_path / "Dockerfile"
        if dockerfile.exists():
            config["image"] = f"{service_path.name}:latest"
        
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
    
    def _generate_deployment(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Kubernetes Deployment manifest."""
        
        deployment = {
            "apiVersion": self.api_version,
            "kind": "Deployment",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "version": "v1",
                    "component": "microservice"
                }
            },
            "spec": {
                "replicas": config.get("replicas", 1),
                "selector": {
                    "matchLabels": {
                        "app": service_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": service_name,
                            "version": "v1"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": service_name,
                                "image": config.get("image", f"{service_name}:latest"),
                                "ports": [
                                    {
                                        "containerPort": config.get("port", 8000),
                                        "name": "http"
                                    }
                                ],
                                "env": self._generate_env_vars(service_name, config),
                                "resources": config.get("resources", {}),
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": config.get("health_check_path", "/health"),
                                        "port": "http"
                                    },
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 5,
                                    "failureThreshold": 3
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": config.get("readiness_check_path", "/health"),
                                        "port": "http"
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5,
                                    "timeoutSeconds": 3,
                                    "failureThreshold": 3
                                }
                            }
                        ],
                        "restartPolicy": "Always"
                    }
                }
            }
        }
        
        # Add ConfigMap reference if environment variables exist
        if config.get("environment"):
            deployment["spec"]["template"]["spec"]["containers"][0]["envFrom"] = [
                {
                    "configMapRef": {
                        "name": f"{service_name}-config"
                    }
                }
            ]
        
        return yaml.dump(deployment, default_flow_style=False, sort_keys=False)
    
    def _generate_service(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Kubernetes Service manifest."""
        
        service = {
            "apiVersion": self.service_api_version,
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "component": "microservice"
                }
            },
            "spec": {
                "selector": {
                    "app": service_name
                },
                "ports": [
                    {
                        "name": "http",
                        "port": 80,
                        "targetPort": config.get("port", 8000),
                        "protocol": "TCP"
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        return yaml.dump(service, default_flow_style=False, sort_keys=False)
    
    def _generate_configmap(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Kubernetes ConfigMap manifest."""
        
        configmap = {
            "apiVersion": self.configmap_api_version,
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{service_name}-config",
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "component": "config"
                }
            },
            "data": config.get("environment", {})
        }
        
        return yaml.dump(configmap, default_flow_style=False, sort_keys=False)
    
    def _generate_ingress(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Kubernetes Ingress manifest."""
        
        host = config.get("ingress_host", f"{service_name}.local")
        path = config.get("ingress_path", "/")
        
        ingress = {
            "apiVersion": self.ingress_api_version,
            "kind": "Ingress",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "component": "ingress"
                },
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "false"
                }
            },
            "spec": {
                "rules": [
                    {
                        "host": host,
                        "http": {
                            "paths": [
                                {
                                    "path": path,
                                    "pathType": "Prefix",
                                    "backend": {
                                        "service": {
                                            "name": service_name,
                                            "port": {
                                                "number": 80
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }
        
        # Add TLS if configured
        if config.get("enable_tls", False):
            ingress["spec"]["tls"] = [
                {
                    "hosts": [host],
                    "secretName": f"{service_name}-tls"
                }
            ]
        
        return yaml.dump(ingress, default_flow_style=False, sort_keys=False)
    
    def _generate_hpa(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Kubernetes HorizontalPodAutoscaler manifest."""
        
        hpa = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "component": "autoscaler"
                }
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": self.api_version,
                    "kind": "Deployment",
                    "name": service_name
                },
                "minReplicas": config.get("min_replicas", 1),
                "maxReplicas": config.get("max_replicas", 10),
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": config.get("cpu_target", 70)
                            }
                        }
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": config.get("memory_target", 80)
                            }
                        }
                    }
                ]
            }
        }
        
        return yaml.dump(hpa, default_flow_style=False, sort_keys=False)
    
    def _generate_service_monitor(self, service_name: str, namespace: str, config: Dict[str, Any]) -> str:
        """Generate Prometheus ServiceMonitor manifest."""
        
        service_monitor = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "ServiceMonitor",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": service_name,
                    "component": "monitoring"
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": service_name
                    }
                },
                "endpoints": [
                    {
                        "port": "http",
                        "path": "/metrics",
                        "interval": "30s",
                        "scrapeTimeout": "10s"
                    }
                ]
            }
        }
        
        return yaml.dump(service_monitor, default_flow_style=False, sort_keys=False)
    
    def _generate_env_vars(self, service_name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate environment variables for the container."""
        
        env_vars = [
            {
                "name": "SERVICE_NAME",
                "value": service_name
            },
            {
                "name": "SERVICE_PORT",
                "value": str(config.get("port", 8000))
            },
            {
                "name": "ENVIRONMENT",
                "value": "production"
            }
        ]
        
        return env_vars
    
    def generate_namespace(self, namespace: str) -> str:
        """Generate Kubernetes Namespace manifest."""
        
        ns = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": namespace,
                "labels": {
                    "name": namespace,
                    "component": "microservices"
                }
            }
        }
        
        return yaml.dump(ns, default_flow_style=False, sort_keys=False)
    
    def generate_full_stack(
        self, 
        services: List[Dict[str, Any]], 
        namespace: str = "microservices",
        include_infrastructure: bool = True
    ) -> Dict[str, str]:
        """Generate complete Kubernetes manifests for multiple services."""
        
        manifests = {}
        
        # Generate namespace
        manifests["namespace.yaml"] = self.generate_namespace(namespace)
        
        # Generate infrastructure if requested
        if include_infrastructure:
            infra_manifests = self._generate_infrastructure_manifests(namespace)
            manifests.update(infra_manifests)
        
        # Generate service manifests
        for service_info in services:
            service_name = service_info["name"]
            service_config = service_info.get("config", {})
            service_path = Path(service_info.get("path", "."))
            
            service_manifests = self.generate(service_name, service_path, namespace, service_config)
            
            # Prefix with service name to avoid conflicts
            for manifest_name, manifest_content in service_manifests.items():
                prefixed_name = f"{service_name}-{manifest_name}"
                manifests[prefixed_name] = manifest_content
        
        return manifests
    
    def _generate_infrastructure_manifests(self, namespace: str) -> Dict[str, str]:
        """Generate infrastructure service manifests."""
        
        manifests = {}
        
        # PostgreSQL
        manifests["postgres-deployment.yaml"] = self._generate_postgres_deployment(namespace)
        manifests["postgres-service.yaml"] = self._generate_postgres_service(namespace)
        manifests["postgres-pvc.yaml"] = self._generate_postgres_pvc(namespace)
        
        # Redis
        manifests["redis-deployment.yaml"] = self._generate_redis_deployment(namespace)
        manifests["redis-service.yaml"] = self._generate_redis_service(namespace)
        
        # RabbitMQ
        manifests["rabbitmq-deployment.yaml"] = self._generate_rabbitmq_deployment(namespace)
        manifests["rabbitmq-service.yaml"] = self._generate_rabbitmq_service(namespace)
        
        return manifests
    
    def _generate_postgres_deployment(self, namespace: str) -> str:
        """Generate PostgreSQL deployment."""
        
        deployment = {
            "apiVersion": self.api_version,
            "kind": "Deployment",
            "metadata": {
                "name": "postgres",
                "namespace": namespace,
                "labels": {
                    "app": "postgres",
                    "component": "database"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "postgres"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "postgres"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "postgres",
                                "image": "postgres:15",
                                "ports": [
                                    {
                                        "containerPort": 5432,
                                        "name": "postgres"
                                    }
                                ],
                                "env": [
                                    {
                                        "name": "POSTGRES_DB",
                                        "value": "microservices"
                                    },
                                    {
                                        "name": "POSTGRES_USER",
                                        "value": "postgres"
                                    },
                                    {
                                        "name": "POSTGRES_PASSWORD",
                                        "value": "password"
                                    }
                                ],
                                "volumeMounts": [
                                    {
                                        "name": "postgres-storage",
                                        "mountPath": "/var/lib/postgresql/data"
                                    }
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": "256Mi",
                                        "cpu": "100m"
                                    },
                                    "limits": {
                                        "memory": "512Mi",
                                        "cpu": "200m"
                                    }
                                }
                            }
                        ],
                        "volumes": [
                            {
                                "name": "postgres-storage",
                                "persistentVolumeClaim": {
                                    "claimName": "postgres-pvc"
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        return yaml.dump(deployment, default_flow_style=False, sort_keys=False)
    
    def _generate_postgres_service(self, namespace: str) -> str:
        """Generate PostgreSQL service."""
        
        service = {
            "apiVersion": self.service_api_version,
            "kind": "Service",
            "metadata": {
                "name": "postgres",
                "namespace": namespace,
                "labels": {
                    "app": "postgres",
                    "component": "database"
                }
            },
            "spec": {
                "selector": {
                    "app": "postgres"
                },
                "ports": [
                    {
                        "name": "postgres",
                        "port": 5432,
                        "targetPort": 5432,
                        "protocol": "TCP"
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        return yaml.dump(service, default_flow_style=False, sort_keys=False)
    
    def _generate_postgres_pvc(self, namespace: str) -> str:
        """Generate PostgreSQL PersistentVolumeClaim."""
        
        pvc = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": "postgres-pvc",
                "namespace": namespace,
                "labels": {
                    "app": "postgres",
                    "component": "storage"
                }
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": "1Gi"
                    }
                }
            }
        }
        
        return yaml.dump(pvc, default_flow_style=False, sort_keys=False)
    
    def _generate_redis_deployment(self, namespace: str) -> str:
        """Generate Redis deployment."""
        
        deployment = {
            "apiVersion": self.api_version,
            "kind": "Deployment",
            "metadata": {
                "name": "redis",
                "namespace": namespace,
                "labels": {
                    "app": "redis",
                    "component": "cache"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "redis"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "redis"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "redis",
                                "image": "redis:7-alpine",
                                "ports": [
                                    {
                                        "containerPort": 6379,
                                        "name": "redis"
                                    }
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": "64Mi",
                                        "cpu": "50m"
                                    },
                                    "limits": {
                                        "memory": "128Mi",
                                        "cpu": "100m"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        return yaml.dump(deployment, default_flow_style=False, sort_keys=False)
    
    def _generate_redis_service(self, namespace: str) -> str:
        """Generate Redis service."""
        
        service = {
            "apiVersion": self.service_api_version,
            "kind": "Service",
            "metadata": {
                "name": "redis",
                "namespace": namespace,
                "labels": {
                    "app": "redis",
                    "component": "cache"
                }
            },
            "spec": {
                "selector": {
                    "app": "redis"
                },
                "ports": [
                    {
                        "name": "redis",
                        "port": 6379,
                        "targetPort": 6379,
                        "protocol": "TCP"
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        return yaml.dump(service, default_flow_style=False, sort_keys=False)
    
    def _generate_rabbitmq_deployment(self, namespace: str) -> str:
        """Generate RabbitMQ deployment."""
        
        deployment = {
            "apiVersion": self.api_version,
            "kind": "Deployment",
            "metadata": {
                "name": "rabbitmq",
                "namespace": namespace,
                "labels": {
                    "app": "rabbitmq",
                    "component": "message-broker"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "rabbitmq"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "rabbitmq"
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "rabbitmq",
                                "image": "rabbitmq:3-management",
                                "ports": [
                                    {
                                        "containerPort": 5672,
                                        "name": "amqp"
                                    },
                                    {
                                        "containerPort": 15672,
                                        "name": "management"
                                    }
                                ],
                                "env": [
                                    {
                                        "name": "RABBITMQ_DEFAULT_USER",
                                        "value": "guest"
                                    },
                                    {
                                        "name": "RABBITMQ_DEFAULT_PASS",
                                        "value": "guest"
                                    }
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": "128Mi",
                                        "cpu": "100m"
                                    },
                                    "limits": {
                                        "memory": "256Mi",
                                        "cpu": "200m"
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        return yaml.dump(deployment, default_flow_style=False, sort_keys=False)
    
    def _generate_rabbitmq_service(self, namespace: str) -> str:
        """Generate RabbitMQ service."""
        
        service = {
            "apiVersion": self.service_api_version,
            "kind": "Service",
            "metadata": {
                "name": "rabbitmq",
                "namespace": namespace,
                "labels": {
                    "app": "rabbitmq",
                    "component": "message-broker"
                }
            },
            "spec": {
                "selector": {
                    "app": "rabbitmq"
                },
                "ports": [
                    {
                        "name": "amqp",
                        "port": 5672,
                        "targetPort": 5672,
                        "protocol": "TCP"
                    },
                    {
                        "name": "management",
                        "port": 15672,
                        "targetPort": 15672,
                        "protocol": "TCP"
                    }
                ],
                "type": "ClusterIP"
            }
        }
        
        return yaml.dump(service, default_flow_style=False, sort_keys=False)
    
    def save_manifests(self, manifests: Dict[str, str], output_path: Path) -> List[Path]:
        """Save all manifests to files."""
        
        output_path.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        for filename, content in manifests.items():
            manifest_path = output_path / filename
            manifest_path.write_text(content)
            saved_files.append(manifest_path)
        
        return saved_files
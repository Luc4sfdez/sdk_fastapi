"""
Kubernetes Generator for FastAPI microservices.

This module provides Kubernetes manifest generation including deployments,
services, ingress, and other K8s resources for FastAPI microservices.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import json
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    # Fallback if PyYAML is not installed
    class yaml:
        @staticmethod
        def dump(data, default_flow_style=False):
            return json.dumps(data, indent=2)

from ..config import TemplateConfig, TemplateVariable, VariableType
from ..exceptions import TemplateError


class BaseTemplate:
    """Base template class."""
    def __init__(self, name: str, description: str, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.version = version
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        raise NotImplementedError
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate files from template."""
        raise NotImplementedError


@dataclass
class K8sResource:
    """Base Kubernetes resource."""
    api_version: str
    kind: str
    metadata: Dict[str, Any]
    spec: Dict[str, Any] = field(default_factory=dict)


@dataclass
class K8sContainer:
    """Kubernetes container specification."""
    name: str
    image: str
    ports: List[Dict[str, Any]] = field(default_factory=list)
    env: List[Dict[str, Any]] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    volume_mounts: List[Dict[str, Any]] = field(default_factory=list)
    liveness_probe: Optional[Dict[str, Any]] = None
    readiness_probe: Optional[Dict[str, Any]] = None


class KubernetesGenerator:
    """Generator for Kubernetes manifests."""
    
    def __init__(self):
        self.api_versions = {
            "Deployment": "apps/v1",
            "Service": "v1",
            "Ingress": "networking.k8s.io/v1",
            "ConfigMap": "v1",
            "Secret": "v1",
            "PersistentVolumeClaim": "v1",
            "HorizontalPodAutoscaler": "autoscaling/v2",
            "NetworkPolicy": "networking.k8s.io/v1",
            "ServiceAccount": "v1",
            "Role": "rbac.authorization.k8s.io/v1",
            "RoleBinding": "rbac.authorization.k8s.io/v1"
        }
    
    def generate_deployment(self, app_name: str, image: str, 
                          replicas: int = 3, port: int = 8000,
                          env_vars: Optional[Dict[str, str]] = None,
                          resources: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate Kubernetes Deployment manifest."""
        
        container_env = []
        if env_vars:
            for key, value in env_vars.items():
                container_env.append({"name": key, "value": value})
        
        container_resources = resources or {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"}
        }
        
        deployment = {
            "apiVersion": self.api_versions["Deployment"],
            "kind": "Deployment",
            "metadata": {
                "name": app_name,
                "labels": {
                    "app": app_name,
                    "version": "v1"
                }
            },
            "spec": {
                "replicas": replicas,
                "selector": {
                    "matchLabels": {
                        "app": app_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": app_name,
                            "version": "v1"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": app_name,
                            "image": image,
                            "ports": [{
                                "containerPort": port,
                                "name": "http"
                            }],
                            "env": container_env,
                            "resources": container_resources,
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": port
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10,
                                "timeoutSeconds": 5,
                                "failureThreshold": 3
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": port
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5,
                                "timeoutSeconds": 3,
                                "failureThreshold": 3
                            }
                        }],
                        "restartPolicy": "Always"
                    }
                }
            }
        }
        
        return deployment
    
    def generate_service(self, app_name: str, port: int = 8000,
                        target_port: int = 8000, service_type: str = "ClusterIP") -> Dict[str, Any]:
        """Generate Kubernetes Service manifest."""
        
        service = {
            "apiVersion": self.api_versions["Service"],
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-service",
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "type": service_type,
                "ports": [{
                    "port": port,
                    "targetPort": target_port,
                    "protocol": "TCP",
                    "name": "http"
                }],
                "selector": {
                    "app": app_name
                }
            }
        }
        
        return service
    
    def generate_ingress(self, app_name: str, host: str, 
                        service_port: int = 8000, path: str = "/",
                        tls_enabled: bool = False, tls_secret: str = None) -> Dict[str, Any]:
        """Generate Kubernetes Ingress manifest."""
        
        ingress = {
            "apiVersion": self.api_versions["Ingress"],
            "kind": "Ingress",
            "metadata": {
                "name": f"{app_name}-ingress",
                "labels": {
                    "app": app_name
                },
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                    "nginx.ingress.kubernetes.io/ssl-redirect": "true" if tls_enabled else "false",
                    "nginx.ingress.kubernetes.io/force-ssl-redirect": "true" if tls_enabled else "false"
                }
            },
            "spec": {
                "rules": [{
                    "host": host,
                    "http": {
                        "paths": [{
                            "path": path,
                            "pathType": "Prefix",
                            "backend": {
                                "service": {
                                    "name": f"{app_name}-service",
                                    "port": {
                                        "number": service_port
                                    }
                                }
                            }
                        }]
                    }
                }]
            }
        }
        
        if tls_enabled and tls_secret:
            ingress["spec"]["tls"] = [{
                "hosts": [host],
                "secretName": tls_secret
            }]
        
        return ingress
    
    def generate_configmap(self, app_name: str, config_data: Dict[str, str]) -> Dict[str, Any]:
        """Generate Kubernetes ConfigMap manifest."""
        
        configmap = {
            "apiVersion": self.api_versions["ConfigMap"],
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "labels": {
                    "app": app_name
                }
            },
            "data": config_data
        }
        
        return configmap
    
    def generate_secret(self, app_name: str, secret_data: Dict[str, str],
                       secret_type: str = "Opaque") -> Dict[str, Any]:
        """Generate Kubernetes Secret manifest."""
        
        import base64
        
        # Encode secret data
        encoded_data = {}
        for key, value in secret_data.items():
            encoded_data[key] = base64.b64encode(value.encode()).decode()
        
        secret = {
            "apiVersion": self.api_versions["Secret"],
            "kind": "Secret",
            "metadata": {
                "name": f"{app_name}-secret",
                "labels": {
                    "app": app_name
                }
            },
            "type": secret_type,
            "data": encoded_data
        }
        
        return secret
    
    def generate_hpa(self, app_name: str, min_replicas: int = 2, max_replicas: int = 10,
                    cpu_threshold: int = 70, memory_threshold: int = 80) -> Dict[str, Any]:
        """Generate Horizontal Pod Autoscaler manifest."""
        
        hpa = {
            "apiVersion": self.api_versions["HorizontalPodAutoscaler"],
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{app_name}-hpa",
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": app_name
                },
                "minReplicas": min_replicas,
                "maxReplicas": max_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": cpu_threshold
                            }
                        }
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": memory_threshold
                            }
                        }
                    }
                ]
            }
        }
        
        return hpa
    
    def generate_network_policy(self, app_name: str, 
                               allowed_ingress: List[Dict[str, Any]] = None,
                               allowed_egress: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate NetworkPolicy manifest."""
        
        network_policy = {
            "apiVersion": self.api_versions["NetworkPolicy"],
            "kind": "NetworkPolicy",
            "metadata": {
                "name": f"{app_name}-network-policy",
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "podSelector": {
                    "matchLabels": {
                        "app": app_name
                    }
                },
                "policyTypes": []
            }
        }
        
        if allowed_ingress:
            network_policy["spec"]["policyTypes"].append("Ingress")
            network_policy["spec"]["ingress"] = allowed_ingress
        
        if allowed_egress:
            network_policy["spec"]["policyTypes"].append("Egress")
            network_policy["spec"]["egress"] = allowed_egress
        
        return network_policy
    
    def generate_database_deployment(self, database_type: str, app_name: str) -> Dict[str, Any]:
        """Generate database deployment manifest."""
        
        if database_type == "postgresql":
            return self._generate_postgresql_deployment(app_name)
        elif database_type == "mysql":
            return self._generate_mysql_deployment(app_name)
        elif database_type == "mongodb":
            return self._generate_mongodb_deployment(app_name)
        elif database_type == "redis":
            return self._generate_redis_deployment(app_name)
        else:
            raise TemplateError(f"Unsupported database type: {database_type}")
    
    def generate_pvc(self, app_name: str, storage_size: str = "10Gi",
                    storage_class: str = "standard") -> Dict[str, Any]:
        """Generate PersistentVolumeClaim manifest."""
        
        pvc = {
            "apiVersion": self.api_versions["PersistentVolumeClaim"],
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{app_name}-pvc",
                "labels": {
                    "app": app_name
                }
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": storage_class,
                "resources": {
                    "requests": {
                        "storage": storage_size
                    }
                }
            }
        }
        
        return pvc
    
    def generate_kustomization(self, resources: List[str]) -> Dict[str, Any]:
        """Generate kustomization.yaml file."""
        
        kustomization = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "resources": resources,
            "commonLabels": {
                "app.kubernetes.io/managed-by": "fastapi-microservices-sdk"
            }
        }
        
        return kustomization
    
    def generate_k8s_manifests(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Generate all Kubernetes manifests."""
        
        app_name = config.get("app_name", "fastapi-app")
        image = config.get("image", f"{app_name}:latest")
        replicas = config.get("replicas", 3)
        port = config.get("port", 8000)
        host = config.get("host", f"{app_name}.example.com")
        database_type = config.get("database_type", "postgresql")
        environment = config.get("environment", "production")
        
        manifests = {}
        resources = []
        
        # Generate main application manifests
        deployment = self.generate_deployment(app_name, image, replicas, port)
        manifests[f"k8s/{app_name}-deployment.yaml"] = yaml.dump(deployment, default_flow_style=False)
        resources.append(f"{app_name}-deployment.yaml")
        
        service = self.generate_service(app_name, port)
        manifests[f"k8s/{app_name}-service.yaml"] = yaml.dump(service, default_flow_style=False)
        resources.append(f"{app_name}-service.yaml")
        
        # Generate ingress
        ingress = self.generate_ingress(app_name, host, port)
        manifests[f"k8s/{app_name}-ingress.yaml"] = yaml.dump(ingress, default_flow_style=False)
        resources.append(f"{app_name}-ingress.yaml")
        
        # Generate ConfigMap
        config_data = {
            "ENVIRONMENT": environment,
            "PORT": str(port),
            "LOG_LEVEL": "INFO"
        }
        configmap = self.generate_configmap(app_name, config_data)
        manifests[f"k8s/{app_name}-configmap.yaml"] = yaml.dump(configmap, default_flow_style=False)
        resources.append(f"{app_name}-configmap.yaml")
        
        # Generate Secret
        secret_data = {
            "DATABASE_PASSWORD": "changeme",
            "SECRET_KEY": "your-secret-key-here"
        }
        secret = self.generate_secret(app_name, secret_data)
        manifests[f"k8s/{app_name}-secret.yaml"] = yaml.dump(secret, default_flow_style=False)
        resources.append(f"{app_name}-secret.yaml")
        
        # Generate HPA
        hpa = self.generate_hpa(app_name)
        manifests[f"k8s/{app_name}-hpa.yaml"] = yaml.dump(hpa, default_flow_style=False)
        resources.append(f"{app_name}-hpa.yaml")
        
        # Generate database manifests if needed
        if database_type != "sqlite":
            db_deployment = self.generate_database_deployment(database_type, app_name)
            manifests[f"k8s/{database_type}-deployment.yaml"] = yaml.dump(db_deployment, default_flow_style=False)
            resources.append(f"{database_type}-deployment.yaml")
            
            db_service = self.generate_service(f"{database_type}", 5432 if database_type == "postgresql" else 3306)
            manifests[f"k8s/{database_type}-service.yaml"] = yaml.dump(db_service, default_flow_style=False)
            resources.append(f"{database_type}-service.yaml")
            
            pvc = self.generate_pvc(f"{database_type}")
            manifests[f"k8s/{database_type}-pvc.yaml"] = yaml.dump(pvc, default_flow_style=False)
            resources.append(f"{database_type}-pvc.yaml")
        
        # Generate kustomization
        kustomization = self.generate_kustomization(resources)
        manifests["k8s/kustomization.yaml"] = yaml.dump(kustomization, default_flow_style=False)
        
        # Generate deployment scripts
        manifests.update(self._generate_k8s_scripts(app_name))
        
        return manifests
    
    def _generate_postgresql_deployment(self, app_name: str) -> Dict[str, Any]:
        """Generate PostgreSQL deployment."""
        
        return {
            "apiVersion": self.api_versions["Deployment"],
            "kind": "Deployment",
            "metadata": {
                "name": "postgresql",
                "labels": {
                    "app": "postgresql",
                    "tier": "database"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "postgresql"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "postgresql",
                            "tier": "database"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "postgresql",
                            "image": "postgres:15-alpine",
                            "ports": [{
                                "containerPort": 5432,
                                "name": "postgres"
                            }],
                            "env": [
                                {
                                    "name": "POSTGRES_DB",
                                    "value": f"{app_name}_db"
                                },
                                {
                                    "name": "POSTGRES_USER",
                                    "value": "postgres"
                                },
                                {
                                    "name": "POSTGRES_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": f"{app_name}-secret",
                                            "key": "DATABASE_PASSWORD"
                                        }
                                    }
                                }
                            ],
                            "volumeMounts": [{
                                "name": "postgres-storage",
                                "mountPath": "/var/lib/postgresql/data"
                            }],
                            "resources": {
                                "requests": {
                                    "cpu": "100m",
                                    "memory": "256Mi"
                                },
                                "limits": {
                                    "cpu": "500m",
                                    "memory": "1Gi"
                                }
                            }
                        }],
                        "volumes": [{
                            "name": "postgres-storage",
                            "persistentVolumeClaim": {
                                "claimName": "postgresql-pvc"
                            }
                        }]
                    }
                }
            }
        }
    
    def _generate_mysql_deployment(self, app_name: str) -> Dict[str, Any]:
        """Generate MySQL deployment."""
        
        return {
            "apiVersion": self.api_versions["Deployment"],
            "kind": "Deployment",
            "metadata": {
                "name": "mysql",
                "labels": {
                    "app": "mysql",
                    "tier": "database"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "mysql"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "mysql",
                            "tier": "database"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "mysql",
                            "image": "mysql:8.0",
                            "ports": [{
                                "containerPort": 3306,
                                "name": "mysql"
                            }],
                            "env": [
                                {
                                    "name": "MYSQL_DATABASE",
                                    "value": f"{app_name}_db"
                                },
                                {
                                    "name": "MYSQL_USER",
                                    "value": "mysql"
                                },
                                {
                                    "name": "MYSQL_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": f"{app_name}-secret",
                                            "key": "DATABASE_PASSWORD"
                                        }
                                    }
                                },
                                {
                                    "name": "MYSQL_ROOT_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": f"{app_name}-secret",
                                            "key": "DATABASE_PASSWORD"
                                        }
                                    }
                                }
                            ],
                            "volumeMounts": [{
                                "name": "mysql-storage",
                                "mountPath": "/var/lib/mysql"
                            }],
                            "resources": {
                                "requests": {
                                    "cpu": "100m",
                                    "memory": "256Mi"
                                },
                                "limits": {
                                    "cpu": "500m",
                                    "memory": "1Gi"
                                }
                            }
                        }],
                        "volumes": [{
                            "name": "mysql-storage",
                            "persistentVolumeClaim": {
                                "claimName": "mysql-pvc"
                            }
                        }]
                    }
                }
            }
        }
    
    def _generate_mongodb_deployment(self, app_name: str) -> Dict[str, Any]:
        """Generate MongoDB deployment."""
        
        return {
            "apiVersion": self.api_versions["Deployment"],
            "kind": "Deployment",
            "metadata": {
                "name": "mongodb",
                "labels": {
                    "app": "mongodb",
                    "tier": "database"
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": "mongodb"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "mongodb",
                            "tier": "database"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "mongodb",
                            "image": "mongo:6.0",
                            "ports": [{
                                "containerPort": 27017,
                                "name": "mongodb"
                            }],
                            "env": [
                                {
                                    "name": "MONGO_INITDB_DATABASE",
                                    "value": f"{app_name}_db"
                                },
                                {
                                    "name": "MONGO_INITDB_ROOT_USERNAME",
                                    "value": "mongo"
                                },
                                {
                                    "name": "MONGO_INITDB_ROOT_PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": f"{app_name}-secret",
                                            "key": "DATABASE_PASSWORD"
                                        }
                                    }
                                }
                            ],
                            "volumeMounts": [{
                                "name": "mongodb-storage",
                                "mountPath": "/data/db"
                            }],
                            "resources": {
                                "requests": {
                                    "cpu": "100m",
                                    "memory": "256Mi"
                                },
                                "limits": {
                                    "cpu": "500m",
                                    "memory": "1Gi"
                                }
                            }
                        }],
                        "volumes": [{
                            "name": "mongodb-storage",
                            "persistentVolumeClaim": {
                                "claimName": "mongodb-pvc"
                            }
                        }]
                    }
                }
            }
        }
    
    def _generate_redis_deployment(self, app_name: str) -> Dict[str, Any]:
        """Generate Redis deployment."""
        
        return {
            "apiVersion": self.api_versions["Deployment"],
            "kind": "Deployment",
            "metadata": {
                "name": "redis",
                "labels": {
                    "app": "redis",
                    "tier": "cache"
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
                            "app": "redis",
                            "tier": "cache"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "redis",
                            "image": "redis:7-alpine",
                            "ports": [{
                                "containerPort": 6379,
                                "name": "redis"
                            }],
                            "resources": {
                                "requests": {
                                    "cpu": "50m",
                                    "memory": "64Mi"
                                },
                                "limits": {
                                    "cpu": "200m",
                                    "memory": "256Mi"
                                }
                            }
                        }]
                    }
                }
            }
        }
    
    def _generate_k8s_scripts(self, app_name: str) -> Dict[str, str]:
        """Generate Kubernetes deployment scripts."""
        
        scripts = {}
        
        # Deploy script
        scripts["scripts/k8s-deploy.sh"] = f'''#!/bin/bash
set -e

echo "Deploying {app_name} to Kubernetes..."

# Apply all manifests
kubectl apply -k k8s/

# Wait for deployment to be ready
kubectl rollout status deployment/{app_name}

echo "Deployment completed successfully!"
echo "Service endpoints:"
kubectl get services
'''
        
        # Delete script
        scripts["scripts/k8s-delete.sh"] = f'''#!/bin/bash
set -e

echo "Deleting {app_name} from Kubernetes..."

# Delete all resources
kubectl delete -k k8s/

echo "Resources deleted successfully!"
'''
        
        # Status script
        scripts["scripts/k8s-status.sh"] = f'''#!/bin/bash

echo "=== Deployment Status ==="
kubectl get deployments

echo "=== Pod Status ==="
kubectl get pods

echo "=== Service Status ==="
kubectl get services

echo "=== Ingress Status ==="
kubectl get ingress

echo "=== HPA Status ==="
kubectl get hpa
'''
        
        # Logs script
        scripts["scripts/k8s-logs.sh"] = f'''#!/bin/bash

if [ -z "$1" ]; then
    echo "Getting logs for {app_name}..."
    kubectl logs -l app={app_name} --tail=100 -f
else
    echo "Getting logs for pod: $1"
    kubectl logs "$1" --tail=100 -f
fi
'''
        
        return scripts


class KubernetesTemplate(BaseTemplate):
    """Template for Kubernetes manifest generation."""
    
    def __init__(self):
        super().__init__(
            name="kubernetes",
            description="Kubernetes manifest generator for FastAPI microservices",
            version="1.0.0"
        )
        self.generator = KubernetesGenerator()
    
    def get_config(self) -> TemplateConfig:
        """Get template configuration."""
        return TemplateConfig(
            variables=[
                TemplateVariable(
                    name="app_name",
                    description="Application name",
                    type=VariableType.STRING,
                    default="fastapi-app"
                ),
                TemplateVariable(
                    name="image",
                    description="Docker image",
                    type=VariableType.STRING,
                    default="fastapi-app:latest"
                ),
                TemplateVariable(
                    name="replicas",
                    description="Number of replicas",
                    type=VariableType.INTEGER,
                    default=3
                ),
                TemplateVariable(
                    name="port",
                    description="Application port",
                    type=VariableType.INTEGER,
                    default=8000
                ),
                TemplateVariable(
                    name="host",
                    description="Ingress host",
                    type=VariableType.STRING,
                    default="fastapi-app.example.com"
                ),
                TemplateVariable(
                    name="database_type",
                    description="Database type",
                    type=VariableType.STRING,
                    choices=["postgresql", "mysql", "mongodb", "sqlite"],
                    default="postgresql"
                ),
                TemplateVariable(
                    name="environment",
                    description="Target environment",
                    type=VariableType.STRING,
                    choices=["development", "staging", "production"],
                    default="production"
                )
            ]
        )
    
    def generate(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate Kubernetes manifests."""
        return self.generator.generate_k8s_manifests(context)
"""
Database models for service management.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

Base = declarative_base()


@dataclass
class Service:
    """Service data class for API responses."""
    name: str
    description: str
    port: int
    status: str
    template_type: Optional[str] = None
    version: Optional[str] = None
    health_status: Optional[str] = "unknown"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ServiceModel(Base):
    """Database model for service information."""
    
    __tablename__ = "services"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    template_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="stopped")
    port = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Health and resource information
    health_status = Column(String, nullable=False, default="unknown")
    cpu_percent = Column(Float, default=0.0)
    memory_mb = Column(Float, default=0.0)
    disk_mb = Column(Float, default=0.0)
    network_in_mb = Column(Float, default=0.0)
    network_out_mb = Column(Float, default=0.0)
    
    # Configuration and metadata
    config = Column(JSON, nullable=True)
    environment_variables = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    endpoints = Column(JSON, nullable=True)
    
    # File paths
    service_directory = Column(String, nullable=True)
    logs_path = Column(String, nullable=True)
    
    # Flags
    metrics_enabled = Column(Boolean, default=True)
    auto_restart = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<ServiceModel(id='{self.id}', name='{self.name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'template_type': self.template_type,
            'status': self.status,
            'port': self.port,
            'description': self.description,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'health_status': self.health_status,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'disk_mb': self.disk_mb,
            'network_in_mb': self.network_in_mb,
            'network_out_mb': self.network_out_mb,
            'config': self.config,
            'environment_variables': self.environment_variables,
            'dependencies': self.dependencies,
            'endpoints': self.endpoints,
            'service_directory': self.service_directory,
            'logs_path': self.logs_path,
            'metrics_enabled': self.metrics_enabled,
            'auto_restart': self.auto_restart
        }


class ServiceConfigurationModel(Base):
    """Database model for service configuration history."""
    
    __tablename__ = "service_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, nullable=False, index=True)
    configuration = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<ServiceConfigurationModel(service_id='{self.service_id}', version={self.version})>"


class ServiceLogModel(Base):
    """Database model for service logs metadata."""
    
    __tablename__ = "service_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, nullable=False, index=True)
    log_level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String, nullable=True)  # stdout, stderr, file
    log_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<ServiceLogModel(service_id='{self.service_id}', level='{self.log_level}')>"


class ServiceMetricsModel(Base):
    """Database model for service metrics history."""
    
    __tablename__ = "service_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Resource metrics
    cpu_percent = Column(Float, default=0.0)
    memory_mb = Column(Float, default=0.0)
    disk_mb = Column(Float, default=0.0)
    network_in_mb = Column(Float, default=0.0)
    network_out_mb = Column(Float, default=0.0)
    
    # Application metrics
    request_count = Column(Integer, default=0)
    response_time_ms = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    active_connections = Column(Integer, default=0)
    
    # Custom metrics
    custom_metrics = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<ServiceMetricsModel(service_id='{self.service_id}', timestamp='{self.timestamp}')>"


class ServiceDeploymentModel(Base):
    """Database model for service deployment history."""
    
    __tablename__ = "service_deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(String, nullable=False, index=True)
    deployment_id = Column(String, nullable=False, unique=True, index=True)
    target_environment = Column(String, nullable=False)  # docker, kubernetes, cloud
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    configuration = Column(JSON, nullable=False)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    deployed_by = Column(String, nullable=True)
    
    # Deployment details
    image_tag = Column(String, nullable=True)
    replicas = Column(Integer, default=1)
    resources = Column(JSON, nullable=True)
    environment_variables = Column(JSON, nullable=True)
    
    # Results
    deployment_url = Column(String, nullable=True)
    logs = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ServiceDeploymentModel(deployment_id='{self.deployment_id}', status='{self.status}')>"
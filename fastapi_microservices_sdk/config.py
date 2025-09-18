# fastapi-microservices-sdk/fastapi_microservices_sdk/config.py 
# fastapi-microservices-sdk/fastapi_microservices_sdk/config.py
"""
Configuration management for FastAPI Microservices SDK.

This module handles all configuration aspects of the SDK, including
environment variables, default settings, and configuration validation.
Compatible with FastAPI Full-Stack Template settings.
"""

import os
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

class LogLevel(str, Enum):
    """Logging levels for the SDK."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ServiceDiscoveryType(str, Enum):
    """Service discovery backend types."""
    CONSUL = "consul"
    ETCD = "etcd"
    REDIS = "redis"
    MEMORY = "memory"  # For development
    KUBERNETES = "kubernetes"

class DatabaseType(str, Enum):
    """Database types compatible with FastAPI template."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"

class MessageBrokerType(str, Enum):
    """Message broker types."""
    RABBITMQ = "rabbitmq"
    KAFKA = "kafka"
    REDIS = "redis"
    MEMORY = "memory"  # For development

@dataclass
class DatabaseConfig:
    """Database configuration compatible with FastAPI template."""
    type: DatabaseType = DatabaseType.POSTGRESQL
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    password: str = "password"
    database: str = "app"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @property
    def url(self) -> str:
        """Get database URL compatible with FastAPI template."""
        if self.type == DatabaseType.POSTGRESQL:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == DatabaseType.MYSQL:
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == DatabaseType.SQLITE:
            return f"sqlite:///{self.database}"
        elif self.type == DatabaseType.MONGODB:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.type}")
    
    @property
    def async_url(self) -> str:
        """Get async database URL."""
        if self.type == DatabaseType.POSTGRESQL:
            return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == DatabaseType.MYSQL:
            return f"mysql+aiomysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == DatabaseType.SQLITE:
            return f"sqlite+aiosqlite:///{self.database}"
        elif self.type == DatabaseType.MONGODB:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.type}")

@dataclass
class ServiceDiscoveryConfig:
    """Service discovery configuration."""
    type: ServiceDiscoveryType = ServiceDiscoveryType.MEMORY
    url: Optional[str] = None
    timeout: int = 10
    retry_attempts: int = 3
    health_check_interval: int = 30
    
    # Consul specific
    consul_datacenter: str = "dc1"
    consul_token: Optional[str] = None
    
    # Etcd specific
    etcd_prefix: str = "/services"
    
    # Kubernetes specific
    k8s_namespace: str = "default"
    
    def __post_init__(self):
        """Set default URLs based on type."""
        if self.url is None:
            if self.type == ServiceDiscoveryType.CONSUL:
                self.url = "http://localhost:8500"
            elif self.type == ServiceDiscoveryType.ETCD:
                self.url = "http://localhost:2379"
            elif self.type == ServiceDiscoveryType.REDIS:
                self.url = "redis://localhost:6379"

@dataclass
class MessageBrokerConfig:
    """Message broker configuration."""
    type: MessageBrokerType = MessageBrokerType.MEMORY
    url: Optional[str] = None
    timeout: int = 10
    max_connections: int = 100
    
    # RabbitMQ specific
    rabbitmq_exchange: str = "microservices"
    rabbitmq_queue_prefix: str = "service"
    
    # Kafka specific
    kafka_topic_prefix: str = "microservices"
    kafka_consumer_group: str = "sdk-consumers"
    
    def __post_init__(self):
        """Set default URLs based on type."""
        if self.url is None:
            if self.type == MessageBrokerType.RABBITMQ:
                self.url = "amqp://guest:guest@localhost:5672/"
            elif self.type == MessageBrokerType.KAFKA:
                self.url = "localhost:9092"
            elif self.type == MessageBrokerType.REDIS:
                self.url = "redis://localhost:6379"

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_logging: bool = True
    
    # Prometheus metrics
    metrics_port: int = 9090
    metrics_path: str = "/metrics"
    
    # Tracing
    jaeger_url: Optional[str] = "http://localhost:14268/api/traces"
    trace_sample_rate: float = 0.1
    
    # Health checks
    health_check_path: str = "/health"
    health_check_interval: int = 30

@dataclass
class SecurityConfig:
    """Security configuration compatible with FastAPI template."""
    # JWT settings (compatible with FastAPI template)
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # API Keys
    api_key_header: str = "X-API-Key"
    require_api_key: bool = False
    
    # CORS
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Advanced security (Sprint Security 2)
    enable_advanced_security: bool = False

@dataclass
class SDKConfig:
    """Main SDK configuration class."""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: LogLevel = LogLevel.INFO
    
    # Service defaults
    default_host: str = "0.0.0.0"
    default_port: int = 8000
    default_timeout: int = 30
    
    # Auto-registration
    auto_register_services: bool = True
    service_prefix: str = ""
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    service_discovery: ServiceDiscoveryConfig = field(default_factory=ServiceDiscoveryConfig)
    message_broker: MessageBrokerConfig = field(default_factory=MessageBrokerConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Advanced security configuration (Sprint Security 2)
    _advanced_security: Optional['AdvancedSecurityConfig'] = None
    
    # Feature flags
    enable_service_discovery: bool = True
    enable_message_broker: bool = True
    enable_monitoring: bool = True
    enable_security: bool = True
    enable_hot_reload: bool = True
    
    # Performance settings
    worker_processes: int = 1
    max_requests: int = 1000
    keepalive_timeout: int = 5
    
    # Global singleton instance
    _global_config: Optional['SDKConfig'] = None
    
    @classmethod
    def from_env(cls) -> 'SDKConfig':
        """
        Create configuration from environment variables.
        Compatible with FastAPI Full-Stack Template env vars.
        
        Returns:
            SDKConfig instance with values from environment
            
        Example:
            # Set environment variables
            os.environ['SDK_ENVIRONMENT'] = 'production'
            os.environ['SDK_LOG_LEVEL'] = 'INFO'
            
            config = SDKConfig.from_env()
        """
        # Database config from env (compatible with FastAPI template)
        database_config = DatabaseConfig(
            type=DatabaseType(os.getenv('DATABASE_TYPE', 'postgresql')),
            host=os.getenv('DATABASE_HOST', 'localhost'),
            port=int(os.getenv('DATABASE_PORT', '5432')),
            username=os.getenv('DATABASE_USER', 'postgres'),
            password=os.getenv('DATABASE_PASSWORD', 'password'),
            database=os.getenv('DATABASE_DB', 'app'),
            echo=os.getenv('DATABASE_ECHO', 'false').lower() == 'true'
        )
        
        # Service discovery config
        service_discovery_config = ServiceDiscoveryConfig(
            type=ServiceDiscoveryType(os.getenv('SERVICE_DISCOVERY_TYPE', 'memory')),
            url=os.getenv('SERVICE_DISCOVERY_URL'),
            timeout=int(os.getenv('SERVICE_DISCOVERY_TIMEOUT', '10'))
        )
        
        # Message broker config
        message_broker_config = MessageBrokerConfig(
            type=MessageBrokerType(os.getenv('MESSAGE_BROKER_TYPE', 'memory')),
            url=os.getenv('MESSAGE_BROKER_URL'),
            timeout=int(os.getenv('MESSAGE_BROKER_TIMEOUT', '10'))
        )
        
        # Monitoring config
        monitoring_config = MonitoringConfig(
            enable_metrics=os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            enable_tracing=os.getenv('ENABLE_TRACING', 'true').lower() == 'true',
            jaeger_url=os.getenv('JAEGER_URL'),
            trace_sample_rate=float(os.getenv('TRACE_SAMPLE_RATE', '0.1'))
        )
        
        # Security config (compatible with FastAPI template)
        security_config = SecurityConfig(
            jwt_secret_key=os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production'),
            jwt_algorithm=os.getenv('JWT_ALGORITHM', 'HS256'),
            jwt_access_token_expire_minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30')),
            cors_origins=os.getenv('CORS_ORIGINS', '*').split(',') if os.getenv('CORS_ORIGINS') else ['*'],
            enable_advanced_security=os.getenv('ENABLE_ADVANCED_SECURITY', 'false').lower() == 'true'
        )
        
        return cls(
            environment=os.getenv('SDK_ENVIRONMENT', 'development'),
            debug=os.getenv('SDK_DEBUG', 'true').lower() == 'true',
            log_level=LogLevel(os.getenv('SDK_LOG_LEVEL', 'INFO')),
            default_host=os.getenv('SDK_DEFAULT_HOST', '0.0.0.0'),
            default_port=int(os.getenv('SDK_DEFAULT_PORT', '8000')),
            default_timeout=int(os.getenv('SDK_DEFAULT_TIMEOUT', '30')),
            auto_register_services=os.getenv('SDK_AUTO_REGISTER', 'true').lower() == 'true',
            service_prefix=os.getenv('SDK_SERVICE_PREFIX', ''),
            database=database_config,
            service_discovery=service_discovery_config,
            message_broker=message_broker_config,
            monitoring=monitoring_config,
            security=security_config,
            enable_service_discovery=os.getenv('SDK_ENABLE_DISCOVERY', 'true').lower() == 'true',
            enable_message_broker=os.getenv('SDK_ENABLE_MESSAGING', 'true').lower() == 'true',
            enable_monitoring=os.getenv('SDK_ENABLE_MONITORING', 'true').lower() == 'true',
            enable_security=os.getenv('SDK_ENABLE_SECURITY', 'true').lower() == 'true',
        )
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path]) -> 'SDKConfig':
        """
        Create configuration from JSON or YAML file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            SDKConfig instance
            
        Example:
            config = SDKConfig.from_file('config.json')
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            if file_path.suffix.lower() == '.json':
                data = json.load(f)
            elif file_path.suffix.lower() in ['.yaml', '.yml']:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required to load YAML configuration files")
            else:
                raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SDKConfig':
        """
        Create configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            SDKConfig instance
        """
        # Handle nested configurations
        database_data = data.get('database', {})
        database_config = DatabaseConfig(**database_data)
        
        service_discovery_data = data.get('service_discovery', {})
        service_discovery_config = ServiceDiscoveryConfig(**service_discovery_data)
        
        message_broker_data = data.get('message_broker', {})
        message_broker_config = MessageBrokerConfig(**message_broker_data)
        
        monitoring_data = data.get('monitoring', {})
        monitoring_config = MonitoringConfig(**monitoring_data)
        
        security_data = data.get('security', {})
        security_config = SecurityConfig(**security_data)
        
        # Remove nested keys and create main config
        config_data = data.copy()
        config_data.pop('database', None)
        config_data.pop('service_discovery', None)
        config_data.pop('message_broker', None)
        config_data.pop('monitoring', None)
        config_data.pop('security', None)
        
        return cls(
            database=database_config,
            service_discovery=service_discovery_config,
            message_broker=message_broker_config,
            monitoring=monitoring_config,
            security=security_config,
            **config_data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        result = {}
        
        # Add simple fields
        for key, value in self.__dict__.items():
            if not key.startswith('_') and not isinstance(value, (DatabaseConfig, ServiceDiscoveryConfig, 
                                                                   MessageBrokerConfig, MonitoringConfig, 
                                                                   SecurityConfig)):
                if isinstance(value, Enum):
                    result[key] = value.value
                else:
                    result[key] = value
        
        # Add nested configurations
        result['database'] = {k: v.value if isinstance(v, Enum) else v 
                             for k, v in self.database.__dict__.items()}
        result['service_discovery'] = {k: v.value if isinstance(v, Enum) else v 
                                     for k, v in self.service_discovery.__dict__.items()}
        result['message_broker'] = {k: v.value if isinstance(v, Enum) else v 
                                   for k, v in self.message_broker.__dict__.items()}
        result['monitoring'] = {k: v for k, v in self.monitoring.__dict__.items()}
        result['security'] = {k: v for k, v in self.security.__dict__.items()}
        
        return result
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages
        """
        issues = []
        
        # Validate basic settings
        if self.default_port < 1 or self.default_port > 65535:
            issues.append(f"Invalid default_port: {self.default_port}. Must be 1-65535.")
        
        if self.default_timeout < 1:
            issues.append(f"Invalid default_timeout: {self.default_timeout}. Must be > 0.")
        
        # Validate database config
        try:
            self.database.url  # This will raise if invalid
        except ValueError as e:
            issues.append(f"Database configuration error: {e}")
        
        # Validate service discovery
        if self.enable_service_discovery and self.service_discovery.type != ServiceDiscoveryType.MEMORY:
            if not self.service_discovery.url:
                issues.append("Service discovery URL is required when not using memory backend")
        
        # Validate message broker
        if self.enable_message_broker and self.message_broker.type != MessageBrokerType.MEMORY:
            if not self.message_broker.url:
                issues.append("Message broker URL is required when not using memory backend")
        
        # Validate security
        if len(self.security.jwt_secret_key) < 32:
            issues.append("JWT secret key should be at least 32 characters long for security")
        
        return issues
    
    @classmethod
    def set_global_config(cls, config: 'SDKConfig') -> None:
        """Set global configuration instance."""
        cls._global_config = config
    
    @classmethod
    def get_global_config(cls) -> Optional['SDKConfig']:
        """Get global configuration instance."""
        return cls._global_config
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == 'development'
    
    @property
    def advanced_security(self) -> Optional['AdvancedSecurityConfig']:
        """Get advanced security configuration."""
        if self._advanced_security is None and self.security.enable_advanced_security:
            # Lazy load advanced security configuration
            try:
                from .security.config import AdvancedSecurityConfig
                self._advanced_security = AdvancedSecurityConfig.from_env()
            except ImportError:
                logging.warning("Advanced security configuration requested but security module not available")
                return None
        return self._advanced_security
    
    def set_advanced_security(self, config: 'AdvancedSecurityConfig') -> None:
        """Set advanced security configuration."""
        self._advanced_security = config
        self.security.enable_advanced_security = True
    
    def validate_advanced_security(self) -> List[str]:
        """Validate advanced security configuration if enabled."""
        issues = []
        if self.security.enable_advanced_security and self.advanced_security:
            issues.extend(self.advanced_security.validate())
        return issues

# Convenience function to get current configuration
def get_config() -> SDKConfig:
    """
    Get current global configuration or create default one.
    
    Returns:
        Current SDKConfig instance
        
    Example:
        from fastapi_microservices_sdk.config import get_config
        
        config = get_config()
        print(f"Environment: {config.environment}")
    """
    config = SDKConfig.get_global_config()
    if config is None:
        # Try to load from environment first
        try:
            config = SDKConfig.from_env()
            SDKConfig.set_global_config(config)
        except Exception:
            # Fallback to default config
            config = SDKConfig()
            SDKConfig.set_global_config(config)
    return config
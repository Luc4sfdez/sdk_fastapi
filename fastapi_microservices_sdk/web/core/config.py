"""
Configuration management for the web dashboard.
"""

import os
import json
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

from ...config import SDKConfig


class WebEnvironment(Enum):
    """Web application environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///./web_dashboard.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class RedisConfig:
    """Redis configuration for caching and sessions."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    decode_responses: bool = True


@dataclass
class WebSocketConfig:
    """WebSocket configuration."""
    max_connections: int = 100
    heartbeat_interval: int = 30
    message_queue_size: int = 1000
    compression: bool = True


@dataclass
class SecurityConfig:
    """Security configuration."""
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    password_min_length: int = 8
    max_login_attempts: int = 5
    session_timeout_minutes: int = 60


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    metrics_retention_days: int = 30
    health_check_interval: int = 60
    alert_check_interval: int = 30
    max_metrics_per_service: int = 10000


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class WebConfig:
    """
    Main configuration class for the web dashboard.
    
    Provides centralized configuration management with:
    - Environment-specific settings
    - Configuration validation
    - Default values
    - Environment variable overrides
    """
    
    # Basic settings
    environment: WebEnvironment = WebEnvironment.DEVELOPMENT
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    reload: bool = True
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Feature flags
    enable_authentication: bool = True
    enable_websockets: bool = True
    enable_metrics: bool = True
    enable_deployment: bool = True
    enable_log_streaming: bool = True
    
    # Paths
    template_dir: str = "templates"
    static_dir: str = "static"
    upload_dir: str = "uploads"
    
    # SDK integration
    sdk_config: Optional[SDKConfig] = None
    
    @classmethod
    def from_env(cls) -> 'WebConfig':
        """
        Create configuration from environment variables.
        
        Returns:
            WebConfig instance with values from environment
        """
        config = cls()
        
        # Basic settings
        config.environment = WebEnvironment(os.getenv('WEB_ENVIRONMENT', 'development'))
        config.debug = os.getenv('WEB_DEBUG', 'true').lower() == 'true'
        config.host = os.getenv('WEB_HOST', '0.0.0.0')
        config.port = int(os.getenv('WEB_PORT', '8080'))
        config.reload = os.getenv('WEB_RELOAD', 'true').lower() == 'true'
        
        # Database
        config.database.url = os.getenv('DATABASE_URL', config.database.url)
        config.database.echo = os.getenv('DATABASE_ECHO', 'false').lower() == 'true'
        
        # Redis
        config.redis.host = os.getenv('REDIS_HOST', config.redis.host)
        config.redis.port = int(os.getenv('REDIS_PORT', str(config.redis.port)))
        config.redis.password = os.getenv('REDIS_PASSWORD')
        
        # Security
        config.security.secret_key = os.getenv('SECRET_KEY', config.security.secret_key)
        config.security.jwt_expiration_hours = int(os.getenv('JWT_EXPIRATION_HOURS', str(config.security.jwt_expiration_hours)))
        
        # Feature flags
        config.enable_authentication = os.getenv('ENABLE_AUTH', 'true').lower() == 'true'
        config.enable_websockets = os.getenv('ENABLE_WEBSOCKETS', 'true').lower() == 'true'
        config.enable_metrics = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
        
        return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'WebConfig':
        """
        Create configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            WebConfig instance with values from file
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'WebConfig':
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            WebConfig instance
        """
        config = cls()
        
        # Update basic settings
        for key, value in config_dict.items():
            if hasattr(config, key) and not key.startswith('_'):
                if key == 'environment':
                    setattr(config, key, WebEnvironment(value))
                elif isinstance(getattr(config, key), (DatabaseConfig, RedisConfig, WebSocketConfig, SecurityConfig, MonitoringConfig, LoggingConfig)):
                    # Handle nested configurations
                    nested_config = getattr(config, key)
                    if isinstance(value, dict):
                        for nested_key, nested_value in value.items():
                            if hasattr(nested_config, nested_key):
                                setattr(nested_config, nested_key, nested_value)
                else:
                    setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            
            if isinstance(value, Enum):
                result[key] = value.value
            elif hasattr(value, '__dict__'):
                result[key] = {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
            else:
                result[key] = value
        
        return result
    
    def save_to_file(self, config_path: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> List[str]:
        """
        Validate configuration settings.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate basic settings
        if self.port < 1 or self.port > 65535:
            errors.append("Port must be between 1 and 65535")
        
        # Validate security settings
        if len(self.security.secret_key) < 32:
            errors.append("Secret key must be at least 32 characters long")
        
        if self.security.password_min_length < 6:
            errors.append("Password minimum length must be at least 6")
        
        # Validate monitoring settings
        if self.monitoring.metrics_retention_days < 1:
            errors.append("Metrics retention days must be at least 1")
        
        # Validate WebSocket settings
        if self.websocket.max_connections < 1:
            errors.append("WebSocket max connections must be at least 1")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == WebEnvironment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == WebEnvironment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == WebEnvironment.TESTING
    
    def get_database_url(self) -> str:
        """Get database URL with proper formatting."""
        return self.database.url
    
    def get_redis_url(self) -> str:
        """Get Redis URL with proper formatting."""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        else:
            return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.logging.level.upper()),
            format=self.logging.format
        )
        
        if self.logging.file_path:
            from logging.handlers import RotatingFileHandler
            
            file_handler = RotatingFileHandler(
                self.logging.file_path,
                maxBytes=self.logging.max_file_size,
                backupCount=self.logging.backup_count
            )
            file_handler.setFormatter(logging.Formatter(self.logging.format))
            
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)


# Global configuration instance
web_config = WebConfig.from_env()
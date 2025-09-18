"""
Database Configuration for FastAPI Microservices SDK.

This module provides comprehensive configuration classes for database integration
with support for multiple database engines, connection pooling, security, and
enterprise features.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import ssl
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from pydantic import BaseModel, Field, validator, root_validator
from pydantic import ConfigDict

# Integration with existing configuration system
try:
    from ..config import SDKConfig
    from ..security.advanced.config_manager import SecurityConfigManager
    SDK_CONFIG_AVAILABLE = True
except ImportError:
    SDK_CONFIG_AVAILABLE = False


class DatabaseEngine(str, Enum):
    """Supported database engines."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"


class ConnectionPoolStrategy(str, Enum):
    """Connection pool strategies."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for database replicas."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


class TransactionIsolationLevel(str, Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


class MigrationStrategy(str, Enum):
    """Migration execution strategies."""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    STAGED = "staged"
    ROLLBACK_ON_ERROR = "rollback_on_error"


@dataclass
class DatabaseCredentials:
    """Database connection credentials."""
    username: Optional[str] = None
    password: Optional[str] = None
    auth_source: Optional[str] = None  # For MongoDB
    auth_mechanism: Optional[str] = None  # For MongoDB
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if self.username and not self.password:
            raise ValueError("Password is required when username is provided")


class SSLConfig(BaseModel):
    """SSL/TLS configuration for database connections."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    enabled: bool = False
    ca_cert_path: Optional[Path] = None
    client_cert_path: Optional[Path] = None
    client_key_path: Optional[Path] = None
    verify_mode: str = "CERT_REQUIRED"  # CERT_NONE, CERT_OPTIONAL, CERT_REQUIRED
    check_hostname: bool = True
    ssl_context: Optional[ssl.SSLContext] = None
    
    @validator('verify_mode')
    def validate_verify_mode(cls, v):
        """Validate SSL verify mode."""
        valid_modes = ['CERT_NONE', 'CERT_OPTIONAL', 'CERT_REQUIRED']
        if v not in valid_modes:
            raise ValueError(f"verify_mode must be one of {valid_modes}")
        return v
    
    @validator('ca_cert_path', 'client_cert_path', 'client_key_path')
    def validate_cert_paths(cls, v):
        """Validate certificate file paths."""
        if v and not v.exists():
            raise ValueError(f"Certificate file does not exist: {v}")
        return v
    
    def create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context from configuration."""
        if not self.enabled:
            return None
        
        if self.ssl_context:
            return self.ssl_context
        
        context = ssl.create_default_context()
        
        # Set verify mode
        if self.verify_mode == 'CERT_NONE':
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        elif self.verify_mode == 'CERT_OPTIONAL':
            context.verify_mode = ssl.CERT_OPTIONAL
        else:  # CERT_REQUIRED
            context.verify_mode = ssl.CERT_REQUIRED
        
        # Set hostname checking
        context.check_hostname = self.check_hostname
        
        # Load certificates
        if self.ca_cert_path:
            context.load_verify_locations(cafile=str(self.ca_cert_path))
        
        if self.client_cert_path and self.client_key_path:
            context.load_cert_chain(
                certfile=str(self.client_cert_path),
                keyfile=str(self.client_key_path)
            )
        
        return context


class DatabaseConnectionConfig(BaseModel):
    """Configuration for individual database connection."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Basic connection info
    engine: DatabaseEngine
    host: str = "localhost"
    port: Optional[int] = None
    database: str
    
    # Credentials
    credentials: Optional[DatabaseCredentials] = None
    
    # SSL/TLS configuration
    ssl_config: Optional[SSLConfig] = None
    
    # Connection options
    connection_options: Dict[str, Any] = Field(default_factory=dict)
    
    # Replica configuration
    replicas: List[Dict[str, Any]] = Field(default_factory=list)
    read_preference: str = "primary"  # primary, secondary, nearest
    
    # Connection timeouts
    connection_timeout: float = 30.0
    command_timeout: float = 30.0
    
    # Health check configuration
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    
    @validator('port')
    def validate_port(cls, v, values):
        """Set default port based on database engine."""
        if v is None:
            engine = values.get('engine')
            if engine == DatabaseEngine.POSTGRESQL:
                return 5432
            elif engine == DatabaseEngine.MYSQL:
                return 3306
            elif engine == DatabaseEngine.MONGODB:
                return 27017
            elif engine == DatabaseEngine.SQLITE:
                return None  # SQLite doesn't use ports
        return v
    
    @validator('connection_timeout', 'command_timeout', 'health_check_interval', 'health_check_timeout')
    def validate_timeouts(cls, v):
        """Validate timeout values."""
        if v <= 0:
            raise ValueError("Timeout values must be positive")
        return v
    
    def get_connection_url(self) -> str:
        """Generate connection URL for the database."""
        if self.engine == DatabaseEngine.SQLITE:
            return f"sqlite:///{self.database}"
        
        # Build URL components
        scheme = self.engine.value
        auth = ""
        
        if self.credentials and self.credentials.username:
            auth = f"{self.credentials.username}"
            if self.credentials.password:
                auth += f":{self.credentials.password}"
            auth += "@"
        
        host_port = self.host
        if self.port:
            host_port += f":{self.port}"
        
        url = f"{scheme}://{auth}{host_port}/{self.database}"
        
        # Add SSL parameters for PostgreSQL/MySQL
        if self.ssl_config and self.ssl_config.enabled:
            if self.engine in [DatabaseEngine.POSTGRESQL, DatabaseEngine.MYSQL]:
                url += "?ssl=true"
        
        return url


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""
    
    # Pool sizing
    min_connections: int = Field(default=1, ge=0)
    max_connections: int = Field(default=10, ge=1)
    
    # Pool strategy
    strategy: ConnectionPoolStrategy = ConnectionPoolStrategy.DYNAMIC
    
    # Connection lifecycle
    connection_timeout: float = Field(default=30.0, gt=0)
    idle_timeout: float = Field(default=300.0, gt=0)  # 5 minutes
    max_lifetime: float = Field(default=3600.0, gt=0)  # 1 hour
    
    # Pool behavior
    retry_attempts: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0)
    
    # Load balancing
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    
    # Health checking
    health_check_enabled: bool = True
    health_check_interval: float = Field(default=30.0, gt=0)
    
    # Adaptive pool settings (for ADAPTIVE strategy)
    scale_up_threshold: float = Field(default=0.8, ge=0, le=1)  # 80% utilization
    scale_down_threshold: float = Field(default=0.2, ge=0, le=1)  # 20% utilization
    scale_factor: float = Field(default=1.5, gt=1)  # 50% increase/decrease
    
    @validator('max_connections')
    def validate_max_connections(cls, v, values):
        """Ensure max_connections >= min_connections."""
        min_conn = values.get('min_connections', 1)
        if v < min_conn:
            raise ValueError("max_connections must be >= min_connections")
        return v
    
    @validator('scale_down_threshold')
    def validate_scale_thresholds(cls, v, values):
        """Ensure scale_down_threshold < scale_up_threshold."""
        scale_up = values.get('scale_up_threshold', 0.8)
        if v >= scale_up:
            raise ValueError("scale_down_threshold must be < scale_up_threshold")
        return v


class MigrationConfig(BaseModel):
    """Migration system configuration."""
    
    # Migration strategy
    strategy: MigrationStrategy = MigrationStrategy.MANUAL
    
    # Migration paths
    migrations_directory: Path = Field(default=Path("migrations"))
    
    # Migration table/collection
    migration_table: str = "_migrations"
    
    # Backup settings
    backup_before_migration: bool = True
    backup_directory: Optional[Path] = None
    
    # Rollback settings
    enable_rollback: bool = True
    max_rollback_steps: int = Field(default=10, ge=1)
    
    # Validation settings
    validate_before_apply: bool = True
    dry_run_enabled: bool = True
    
    # Concurrency settings
    lock_timeout: float = Field(default=300.0, gt=0)  # 5 minutes
    
    @validator('migrations_directory', 'backup_directory')
    def validate_directories(cls, v):
        """Validate directory paths."""
        if v and not v.exists():
            v.mkdir(parents=True, exist_ok=True)
        return v


class DatabaseSecurityConfig(BaseModel):
    """Database security configuration."""
    
    # Credential management
    use_secrets_manager: bool = True
    secrets_manager_backend: str = "vault"  # vault, env, file
    credential_rotation_enabled: bool = False
    credential_rotation_interval: int = Field(default=86400, gt=0)  # 24 hours
    
    # Connection security
    require_ssl: bool = False
    ssl_config: Optional[SSLConfig] = None
    
    # Query security
    enable_query_sanitization: bool = True
    enable_sql_injection_protection: bool = True
    max_query_length: int = Field(default=10000, gt=0)
    
    # Access control
    enable_rbac: bool = False
    rbac_config: Optional[Dict[str, Any]] = None
    
    # Audit logging
    enable_audit_logging: bool = True
    audit_log_level: str = "INFO"
    audit_sensitive_operations: bool = True
    
    # Network security
    allowed_hosts: List[str] = Field(default_factory=list)
    blocked_hosts: List[str] = Field(default_factory=list)
    
    @validator('audit_log_level')
    def validate_log_level(cls, v):
        """Validate audit log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f"audit_log_level must be one of {valid_levels}")
        return v


class DatabaseConfig(BaseModel):
    """Main database configuration."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Database connections
    databases: Dict[str, DatabaseConnectionConfig]
    default_database: str = "default"
    
    # Connection pooling
    connection_pools: ConnectionPoolConfig = Field(default_factory=ConnectionPoolConfig)
    
    # Migration system
    migration_config: MigrationConfig = Field(default_factory=MigrationConfig)
    
    # Security configuration
    security_config: DatabaseSecurityConfig = Field(default_factory=DatabaseSecurityConfig)
    
    # Global settings
    enable_query_logging: bool = False
    query_log_level: str = "DEBUG"
    enable_performance_monitoring: bool = True
    
    # Transaction settings
    default_isolation_level: TransactionIsolationLevel = TransactionIsolationLevel.READ_COMMITTED
    transaction_timeout: float = Field(default=30.0, gt=0)
    
    # Retry settings
    enable_automatic_retry: bool = True
    max_retry_attempts: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=2.0, gt=1)
    
    @validator('databases')
    def validate_databases(cls, v):
        """Validate database configurations."""
        if not v:
            raise ValueError("At least one database configuration is required")
        return v
    
    @validator('default_database')
    def validate_default_database(cls, v, values):
        """Ensure default database exists in configurations."""
        databases = values.get('databases', {})
        if v not in databases:
            raise ValueError(f"Default database '{v}' not found in database configurations")
        return v
    
    @validator('query_log_level')
    def validate_query_log_level(cls, v):
        """Validate query log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in valid_levels:
            raise ValueError(f"query_log_level must be one of {valid_levels}")
        return v
    
    def get_database_config(self, name: Optional[str] = None) -> DatabaseConnectionConfig:
        """Get database configuration by name."""
        db_name = name or self.default_database
        if db_name not in self.databases:
            raise ValueError(f"Database configuration '{db_name}' not found")
        return self.databases[db_name]
    
    def get_connection_url(self, name: Optional[str] = None) -> str:
        """Get connection URL for database."""
        config = self.get_database_config(name)
        return config.get_connection_url()
    
    @classmethod
    def from_sdk_config(cls, sdk_config: Optional['SDKConfig'] = None) -> 'DatabaseConfig':
        """Create database config from SDK configuration."""
        if not SDK_CONFIG_AVAILABLE or not sdk_config:
            # Return default configuration
            return cls(
                databases={
                    "default": DatabaseConnectionConfig(
                        engine=DatabaseEngine.SQLITE,
                        database="app.db"
                    )
                }
            )
        
        # Extract database configuration from SDK config
        db_config = getattr(sdk_config, 'database', {})
        
        # Convert to DatabaseConfig format
        databases = {}
        for name, config in db_config.get('databases', {}).items():
            databases[name] = DatabaseConnectionConfig(**config)
        
        if not databases:
            # Default SQLite configuration
            databases['default'] = DatabaseConnectionConfig(
                engine=DatabaseEngine.SQLITE,
                database="app.db"
            )
        
        return cls(
            databases=databases,
            default_database=db_config.get('default_database', 'default'),
            connection_pools=ConnectionPoolConfig(**db_config.get('connection_pools', {})),
            migration_config=MigrationConfig(**db_config.get('migration_config', {})),
            security_config=DatabaseSecurityConfig(**db_config.get('security_config', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'databases': {
                name: {
                    'engine': config.engine.value,
                    'host': config.host,
                    'port': config.port,
                    'database': config.database,
                    'connection_options': config.connection_options,
                    'replicas': config.replicas,
                    'read_preference': config.read_preference
                }
                for name, config in self.databases.items()
            },
            'default_database': self.default_database,
            'connection_pools': self.connection_pools.dict(),
            'migration_config': self.migration_config.dict(),
            'security_config': self.security_config.dict(),
            'enable_query_logging': self.enable_query_logging,
            'enable_performance_monitoring': self.enable_performance_monitoring,
            'default_isolation_level': self.default_isolation_level.value,
            'transaction_timeout': self.transaction_timeout
        }


# Factory functions for common configurations
def create_postgresql_config(
    host: str = "localhost",
    port: int = 5432,
    database: str = "app",
    username: Optional[str] = None,
    password: Optional[str] = None,
    ssl_enabled: bool = False
) -> DatabaseConnectionConfig:
    """Create PostgreSQL database configuration."""
    credentials = None
    if username:
        credentials = DatabaseCredentials(username=username, password=password)
    
    ssl_config = None
    if ssl_enabled:
        ssl_config = SSLConfig(enabled=True)
    
    return DatabaseConnectionConfig(
        engine=DatabaseEngine.POSTGRESQL,
        host=host,
        port=port,
        database=database,
        credentials=credentials,
        ssl_config=ssl_config
    )


def create_mysql_config(
    host: str = "localhost",
    port: int = 3306,
    database: str = "app",
    username: Optional[str] = None,
    password: Optional[str] = None,
    ssl_enabled: bool = False
) -> DatabaseConnectionConfig:
    """Create MySQL database configuration."""
    credentials = None
    if username:
        credentials = DatabaseCredentials(username=username, password=password)
    
    ssl_config = None
    if ssl_enabled:
        ssl_config = SSLConfig(enabled=True)
    
    return DatabaseConnectionConfig(
        engine=DatabaseEngine.MYSQL,
        host=host,
        port=port,
        database=database,
        credentials=credentials,
        ssl_config=ssl_config
    )


def create_mongodb_config(
    host: str = "localhost",
    port: int = 27017,
    database: str = "app",
    username: Optional[str] = None,
    password: Optional[str] = None,
    auth_source: str = "admin",
    ssl_enabled: bool = False
) -> DatabaseConnectionConfig:
    """Create MongoDB database configuration."""
    credentials = None
    if username:
        credentials = DatabaseCredentials(
            username=username,
            password=password,
            auth_source=auth_source
        )
    
    ssl_config = None
    if ssl_enabled:
        ssl_config = SSLConfig(enabled=True)
    
    return DatabaseConnectionConfig(
        engine=DatabaseEngine.MONGODB,
        host=host,
        port=port,
        database=database,
        credentials=credentials,
        ssl_config=ssl_config
    )


def create_sqlite_config(
    database: str = "app.db"
) -> DatabaseConnectionConfig:
    """Create SQLite database configuration."""
    return DatabaseConnectionConfig(
        engine=DatabaseEngine.SQLITE,
        database=database
    )
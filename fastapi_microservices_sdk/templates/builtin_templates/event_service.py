"""
Event Service Template for FastAPI Microservices SDK

This template generates comprehensive event-driven services with Event Sourcing,
CQRS patterns, Saga orchestration, and distributed transaction management.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
import json
import yaml

from ..engine import Template
from ..exceptions import TemplateValidationError, GenerationError


@dataclass
class EventDefinition:
    """Event definition for the service"""
    name: str
    version: str = "1.0"
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregateDefinition:
    """Aggregate definition for event sourcing"""
    name: str
    events: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    snapshots: bool = True
    snapshot_frequency: int = 100


@dataclass
class SagaDefinition:
    """Saga definition for distributed transactions"""
    name: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    compensation_steps: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = 300  # seconds


class EventServiceTemplate(Template):
    """
    Comprehensive Event Service Template
    
    Generates production-ready event-driven services with:
    - Event Sourcing with event store and replay capabilities
    - CQRS (Command Query Responsibility Segregation) pattern
    - Saga pattern for distributed transactions
    - Event streaming and message broker integration
    - Snapshot management for performance optimization
    - Event versioning and migration support
    - Distributed tracing and monitoring
    - Replay and recovery mechanisms
    """
    
    def __init__(self):
        from ..config import TemplateConfig, TemplateCategory
        config = TemplateConfig(
            id="event_service",
            name="Event Service Template",
            description="Event-driven service with Event Sourcing, CQRS, and Saga patterns",
            category=TemplateCategory.EVENT_SERVICE,
            version="1.0.0",
            author="FastAPI Microservices SDK",
            tags=["event", "sourcing", "cqrs", "saga", "streaming", "distributed"]
        )
        super().__init__(config=config)    

    def get_required_variables(self) -> List[str]:
        """Get list of required template variables"""
        return [
            "service_name",
            "service_description",
            "message_broker",
            "event_store",
            "aggregates"
        ]
    
    def get_optional_variables(self) -> Dict[str, Any]:
        """Get optional variables with default values"""
        return {
            "service_version": "1.0.0",
            "service_port": 8000,
            "message_broker_config": {
                "type": "kafka",
                "host": "localhost",
                "port": 9092
            },
            "event_store_config": {
                "type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "event_store"
            },
            "enable_snapshots": True,
            "snapshot_frequency": 100,
            "enable_sagas": True,
            "enable_projections": True,
            "enable_replay": True,
            "enable_monitoring": True,
            "enable_tracing": True,
            "enable_cqrs": True,
            "enable_event_versioning": True,
            "retention_days": 365,
            "batch_size": 1000,
            "events": [],
            "sagas": [],
            "projections": []
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
        
        # Validate message broker
        message_broker = variables.get("message_broker", "")
        supported_brokers = ["kafka", "rabbitmq", "redis", "nats"]
        if message_broker not in supported_brokers:
            errors.append(f"message_broker must be one of: {', '.join(supported_brokers)}")
        
        # Validate event store
        event_store = variables.get("event_store", "")
        supported_stores = ["postgresql", "mongodb", "eventstore"]
        if event_store not in supported_stores:
            errors.append(f"event_store must be one of: {', '.join(supported_stores)}")
        
        # Validate aggregates
        aggregates = variables.get("aggregates", [])
        if not aggregates or not isinstance(aggregates, list):
            errors.append("aggregates is required and must be a list")
        else:
            for i, aggregate in enumerate(aggregates):
                if not isinstance(aggregate, dict):
                    errors.append(f"Aggregate {i} must be a dictionary")
                    continue
                
                if "name" not in aggregate:
                    errors.append(f"Aggregate {i} must have a 'name' field")
                
                if "events" not in aggregate or not isinstance(aggregate["events"], list):
                    errors.append(f"Aggregate {i} must have an 'events' list")
        
        # Validate events if provided
        events = variables.get("events", [])
        if events and isinstance(events, list):
            for i, event in enumerate(events):
                if not isinstance(event, dict):
                    errors.append(f"Event {i} must be a dictionary")
                    continue
                
                if "name" not in event:
                    errors.append(f"Event {i} must have a 'name' field")
        
        # Validate sagas if provided
        sagas = variables.get("sagas", [])
        if sagas and isinstance(sagas, list):
            for i, saga in enumerate(sagas):
                if not isinstance(saga, dict):
                    errors.append(f"Saga {i} must be a dictionary")
                    continue
                
                if "name" not in saga:
                    errors.append(f"Saga {i} must have a 'name' field")
                
                if "steps" not in saga or not isinstance(saga["steps"], list):
                    errors.append(f"Saga {i} must have a 'steps' list")
        
        return errors 
   
    def generate_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate all event service files"""
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
            
            # Generate event sourcing files
            generated_files.extend(self._generate_event_sourcing_files(variables, output_dir))
            
            # Generate CQRS files if enabled
            if variables.get("enable_cqrs", True):
                generated_files.extend(self._generate_cqrs_files(variables, output_dir))
            
            # Generate saga files if enabled
            if variables.get("enable_sagas", True):
                generated_files.extend(self._generate_saga_files(variables, output_dir))
            
            # Generate projection files if enabled
            if variables.get("enable_projections", True):
                generated_files.extend(self._generate_projection_files(variables, output_dir))
            
            # Generate message broker files
            generated_files.extend(self._generate_message_broker_files(variables, output_dir))
            
            # Generate event store files
            generated_files.extend(self._generate_event_store_files(variables, output_dir))
            
            # Generate API files
            generated_files.extend(self._generate_api_files(variables, output_dir))
            
            # Generate monitoring files if enabled
            if variables.get("enable_monitoring", True):
                generated_files.extend(self._generate_monitoring_files(variables, output_dir))
            
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
            raise GenerationError("event_service", f"Failed to generate event service: {str(e)}")
    
    def _create_directory_structure(self, output_dir: Path) -> None:
        """Create the directory structure for the event service"""
        directories = [
            "app",
            "app/events",
            "app/aggregates",
            "app/commands",
            "app/queries",
            "app/projections",
            "app/sagas",
            "app/event_store",
            "app/message_broker",
            "app/snapshots",
            "app/replay",
            "app/api",
            "app/api/v1",
            "app/monitoring",
            "app/middleware",
            "app/utils",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/performance",
            "config",
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
            "app/events/__init__.py",
            "app/aggregates/__init__.py",
            "app/commands/__init__.py",
            "app/queries/__init__.py",
            "app/projections/__init__.py",
            "app/sagas/__init__.py",
            "app/event_store/__init__.py",
            "app/message_broker/__init__.py",
            "app/snapshots/__init__.py",
            "app/replay/__init__.py",
            "app/api/__init__.py",
            "app/api/v1/__init__.py",
            "app/monitoring/__init__.py",
            "app/middleware/__init__.py",
            "app/utils/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = output_dir / init_file
            init_path.write_text('"""Event service module"""', encoding="utf-8")
            files.append(init_path)
        
        return files
    
    def _generate_main_file(self, variables: Dict[str, Any]) -> str:
        """Generate the main FastAPI application file"""
        service_name = variables["service_name"]
        service_description = variables["service_description"]
        service_version = variables.get("service_version", "1.0.0")
        enable_monitoring = variables.get("enable_monitoring", True)
        
        content = f'''"""
{service_name.replace("_", " ").title()} - Event Service

{service_description}
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from .config import settings
from .event_store.manager import event_store_manager
from .message_broker.manager import message_broker_manager
from .api.v1 import router as api_v1_router
from .middleware.error_handler import ErrorHandlerMiddleware
from .middleware.request_id import RequestIDMiddleware
from .middleware.logging import LoggingMiddleware'''

        if enable_monitoring:
            content += '''
from .monitoring.metrics import metrics_middleware
from .monitoring.health import health_router'''

        if variables.get("enable_sagas", True):
            content += '''
from .sagas.manager import saga_manager'''

        if variables.get("enable_projections", True):
            content += '''
from .projections.manager import projection_manager'''

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
    
    # Initialize event store
    await event_store_manager.connect()
    logger.info("Event store connected")
    
    # Initialize message broker
    await message_broker_manager.connect()
    logger.info("Message broker connected")'''

        if variables.get("enable_sagas", True):
            content += '''
    
    # Initialize saga manager
    await saga_manager.start()
    logger.info("Saga manager started")'''

        if variables.get("enable_projections", True):
            content += '''
    
    # Initialize projection manager
    await projection_manager.start()
    logger.info("Projection manager started")'''

        content += f'''
    
    yield
    
    # Shutdown
    logger.info("Shutting down {service_name}")'''

        if variables.get("enable_projections", True):
            content += '''
    
    # Stop projection manager
    await projection_manager.stop()
    logger.info("Projection manager stopped")'''

        if variables.get("enable_sagas", True):
            content += '''
    
    # Stop saga manager
    await saga_manager.stop()
    logger.info("Saga manager stopped")'''

        content += '''
    
    # Close message broker connections
    await message_broker_manager.disconnect()
    logger.info("Message broker disconnected")
    
    # Close event store connections
    await event_store_manager.disconnect()
    logger.info("Event store disconnected")'''

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
app.add_middleware(ErrorHandlerMiddleware)'''

        if enable_monitoring:
            content += '''

# Add metrics middleware
app.add_middleware(metrics_middleware)'''

        content += '''

# Include routers
app.include_router(api_v1_router, prefix="/api/v1")'''

        if enable_monitoring:
            content += '''
app.include_router(health_router, prefix="/health", tags=["health"])'''

        content += '''


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "''' + service_name + '''",
        "version": "''' + service_version + '''",
        "status": "running",
        "type": "event_service"
    }


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
        message_broker = variables["message_broker"]
        event_store = variables["event_store"]
        
        content = f'''"""
Configuration settings for {service_name}
"""

import os
from typing import List, Optional
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
    
    # Message Broker settings
    MESSAGE_BROKER_TYPE: str = "{message_broker}"
    MESSAGE_BROKER_HOST: str = Field(default="localhost", env="MESSAGE_BROKER_HOST")
    MESSAGE_BROKER_PORT: int = Field(default=9092, env="MESSAGE_BROKER_PORT")
    MESSAGE_BROKER_USERNAME: Optional[str] = Field(default=None, env="MESSAGE_BROKER_USERNAME")
    MESSAGE_BROKER_PASSWORD: Optional[str] = Field(default=None, env="MESSAGE_BROKER_PASSWORD")
    
    # Event Store settings
    EVENT_STORE_TYPE: str = "{event_store}"
    EVENT_STORE_HOST: str = Field(default="localhost", env="EVENT_STORE_HOST")
    EVENT_STORE_PORT: int = Field(default=5432, env="EVENT_STORE_PORT")
    EVENT_STORE_DATABASE: str = Field(default="event_store", env="EVENT_STORE_DATABASE")
    EVENT_STORE_USERNAME: str = Field(default="postgres", env="EVENT_STORE_USERNAME")
    EVENT_STORE_PASSWORD: str = Field(default="password", env="EVENT_STORE_PASSWORD")
    
    @property
    def event_store_url(self) -> str:
        """Get event store URL based on type"""'''
        
        if event_store == "postgresql":
            content += '''
        return f"postgresql+asyncpg://{self.EVENT_STORE_USERNAME}:{self.EVENT_STORE_PASSWORD}@{self.EVENT_STORE_HOST}:{self.EVENT_STORE_PORT}/{self.EVENT_STORE_DATABASE}"'''
        elif event_store == "mongodb":
            content += '''
        return f"mongodb://{self.EVENT_STORE_USERNAME}:{self.EVENT_STORE_PASSWORD}@{self.EVENT_STORE_HOST}:{self.EVENT_STORE_PORT}/{self.EVENT_STORE_DATABASE}"'''
        elif event_store == "eventstore":
            content += '''
        return f"esdb://{self.EVENT_STORE_HOST}:{self.EVENT_STORE_PORT}"'''
        
        content += f'''
    
    @property
    def message_broker_url(self) -> str:
        """Get message broker URL based on type"""'''
        
        if message_broker == "kafka":
            content += '''
        return f"{self.MESSAGE_BROKER_HOST}:{self.MESSAGE_BROKER_PORT}"'''
        elif message_broker == "rabbitmq":
            content += '''
        auth = f"{self.MESSAGE_BROKER_USERNAME}:{self.MESSAGE_BROKER_PASSWORD}@" if self.MESSAGE_BROKER_USERNAME else ""
        return f"amqp://{auth}{self.MESSAGE_BROKER_HOST}:{self.MESSAGE_BROKER_PORT}"'''
        elif message_broker == "redis":
            content += '''
        return f"redis://{self.MESSAGE_BROKER_HOST}:{self.MESSAGE_BROKER_PORT}"'''
        elif message_broker == "nats":
            content += '''
        return f"nats://{self.MESSAGE_BROKER_HOST}:{self.MESSAGE_BROKER_PORT}"'''
        
        content += f'''
    
    # Event Sourcing settings
    ENABLE_SNAPSHOTS: bool = Field(default={str(variables.get('enable_snapshots', True)).lower()}, env="ENABLE_SNAPSHOTS")
    SNAPSHOT_FREQUENCY: int = Field(default={variables.get('snapshot_frequency', 100)}, env="SNAPSHOT_FREQUENCY")
    ENABLE_REPLAY: bool = Field(default={str(variables.get('enable_replay', True)).lower()}, env="ENABLE_REPLAY")
    RETENTION_DAYS: int = Field(default={variables.get('retention_days', 365)}, env="RETENTION_DAYS")
    BATCH_SIZE: int = Field(default={variables.get('batch_size', 1000)}, env="BATCH_SIZE")
    
    # CQRS settings
    ENABLE_CQRS: bool = Field(default={str(variables.get('enable_cqrs', True)).lower()}, env="ENABLE_CQRS")
    
    # Saga settings
    ENABLE_SAGAS: bool = Field(default={str(variables.get('enable_sagas', True)).lower()}, env="ENABLE_SAGAS")
    SAGA_TIMEOUT: int = Field(default=300, env="SAGA_TIMEOUT")
    
    # Projection settings
    ENABLE_PROJECTIONS: bool = Field(default={str(variables.get('enable_projections', True)).lower()}, env="ENABLE_PROJECTIONS")
    PROJECTION_BATCH_SIZE: int = Field(default=100, env="PROJECTION_BATCH_SIZE")
    
    # Monitoring settings
    ENABLE_MONITORING: bool = Field(default={str(variables.get('enable_monitoring', True)).lower()}, env="ENABLE_MONITORING")
    ENABLE_TRACING: bool = Field(default={str(variables.get('enable_tracing', True)).lower()}, env="ENABLE_TRACING")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
'''
        
        return content

    def _generate_event_sourcing_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate event sourcing files"""
        files = []
        
        # Generate base event classes
        base_event_content = self._generate_base_event_file(variables)
        base_event_path = output_dir / "app" / "events" / "base.py"
        base_event_path.write_text(base_event_content, encoding="utf-8")
        files.append(base_event_path)
        
        # Generate aggregate base classes
        base_aggregate_content = self._generate_base_aggregate_file(variables)
        base_aggregate_path = output_dir / "app" / "aggregates" / "base.py"
        base_aggregate_path.write_text(base_aggregate_content, encoding="utf-8")
        files.append(base_aggregate_path)
        
        # Generate specific events for each aggregate
        aggregates = variables.get("aggregates", [])
        for aggregate in aggregates:
            # Generate events for this aggregate
            for event_name in aggregate.get("events", []):
                event_content = self._generate_event_file(event_name, aggregate, variables)
                event_path = output_dir / "app" / "events" / f"{event_name.lower()}.py"
                event_path.write_text(event_content, encoding="utf-8")
                files.append(event_path)
            
            # Generate aggregate implementation
            aggregate_content = self._generate_aggregate_file(aggregate, variables)
            aggregate_path = output_dir / "app" / "aggregates" / f"{aggregate['name'].lower()}.py"
            aggregate_path.write_text(aggregate_content, encoding="utf-8")
            files.append(aggregate_path)
        
        return files
    
    def _generate_base_event_file(self, variables: Dict[str, Any]) -> str:
        """Generate base event classes"""
        content = '''"""
Base event classes for event sourcing
"""

from typing import Dict, Any, Optional, Type
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import uuid4, UUID
import json


@dataclass
class EventMetadata:
    """Event metadata"""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    event_version: str = "1.0"
    aggregate_id: str = ""
    aggregate_type: str = ""
    aggregate_version: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    user_id: Optional[str] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "aggregate_version": self.aggregate_version,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "user_id": self.user_id,
            "source": self.source
        }


class DomainEvent(ABC):
    """Base domain event class"""
    
    def __init__(self, aggregate_id: str, **kwargs):
        self.metadata = EventMetadata(
            event_type=self.__class__.__name__,
            aggregate_id=aggregate_id,
            **kwargs
        )
        self.data = self._get_event_data()
    
    @abstractmethod
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "metadata": self.metadata.to_dict(),
            "data": self.data
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> 'DomainEvent':
        """Create event from dictionary"""
        # This would need to be implemented by specific event classes
        raise NotImplementedError
    
    @classmethod
    def from_json(cls, event_json: str) -> 'DomainEvent':
        """Create event from JSON string"""
        event_dict = json.loads(event_json)
        return cls.from_dict(event_dict)


class EventStore(ABC):
    """Abstract event store interface"""
    
    @abstractmethod
    async def save_events(self, aggregate_id: str, events: list[DomainEvent], 
                         expected_version: int) -> None:
        """Save events to the store"""
        pass
    
    @abstractmethod
    async def get_events(self, aggregate_id: str, from_version: int = 0) -> list[DomainEvent]:
        """Get events for an aggregate"""
        pass
    
    @abstractmethod
    async def get_all_events(self, from_timestamp: Optional[datetime] = None, 
                           to_timestamp: Optional[datetime] = None) -> list[DomainEvent]:
        """Get all events in time range"""
        pass


class EventBus(ABC):
    """Abstract event bus interface"""
    
    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None:
        """Publish events to the bus"""
        pass
    
    @abstractmethod
    async def subscribe(self, event_type: Type[DomainEvent], handler) -> None:
        """Subscribe to events"""
        pass
'''
        
        return content
    
    def _generate_base_aggregate_file(self, variables: Dict[str, Any]) -> str:
        """Generate base aggregate classes"""
        content = '''"""
Base aggregate classes for event sourcing
"""

from typing import List, Dict, Any, Optional, Type
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import uuid4

from ..events.base import DomainEvent


class AggregateRoot(ABC):
    """Base aggregate root class"""
    
    def __init__(self, aggregate_id: Optional[str] = None):
        self.id = aggregate_id or str(uuid4())
        self.version = 0
        self.uncommitted_events: List[DomainEvent] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        """Apply an event to the aggregate"""
        # Update metadata
        event.metadata.aggregate_id = self.id
        event.metadata.aggregate_type = self.__class__.__name__
        event.metadata.aggregate_version = self.version + 1
        
        # Apply the event
        self._apply_event(event)
        
        # Update version
        self.version += 1
        self.updated_at = datetime.utcnow()
        
        # Add to uncommitted events if it's new
        if is_new:
            self.uncommitted_events.append(event)
    
    @abstractmethod
    def _apply_event(self, event: DomainEvent) -> None:
        """Apply event to aggregate state - to be implemented by subclasses"""
        pass
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get uncommitted events"""
        return self.uncommitted_events.copy()
    
    def mark_events_as_committed(self) -> None:
        """Mark all uncommitted events as committed"""
        self.uncommitted_events.clear()
    
    def load_from_history(self, events: List[DomainEvent]) -> None:
        """Load aggregate from event history"""
        for event in events:
            self.apply_event(event, is_new=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary"""
        return {
            "id": self.id,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "type": self.__class__.__name__
        }


class Repository(ABC):
    """Base repository for aggregates"""
    
    def __init__(self, event_store, event_bus):
        self.event_store = event_store
        self.event_bus = event_bus
    
    @abstractmethod
    async def get_by_id(self, aggregate_id: str) -> Optional[AggregateRoot]:
        """Get aggregate by ID"""
        pass
    
    @abstractmethod
    async def save(self, aggregate: AggregateRoot) -> None:
        """Save aggregate"""
        pass
    
    async def _save_aggregate(self, aggregate: AggregateRoot) -> None:
        """Save aggregate to event store"""
        uncommitted_events = aggregate.get_uncommitted_events()
        
        if uncommitted_events:
            # Save events to store
            await self.event_store.save_events(
                aggregate.id, 
                uncommitted_events, 
                aggregate.version - len(uncommitted_events)
            )
            
            # Publish events to bus
            await self.event_bus.publish(uncommitted_events)
            
            # Mark events as committed
            aggregate.mark_events_as_committed()
    
    async def _load_aggregate(self, aggregate_class: Type[AggregateRoot], 
                            aggregate_id: str) -> Optional[AggregateRoot]:
        """Load aggregate from event store"""
        events = await self.event_store.get_events(aggregate_id)
        
        if not events:
            return None
        
        aggregate = aggregate_class(aggregate_id)
        aggregate.load_from_history(events)
        
        return aggregate
'''
        
        return content

    def _generate_event_file(self, event_name: str, aggregate: Dict[str, Any], variables: Dict[str, Any]) -> str:
        """Generate specific event file"""
        aggregate_name = aggregate["name"]
        
        content = f'''"""
{event_name} event for {aggregate_name} aggregate
"""

from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass

from .base import DomainEvent


@dataclass
class {event_name}Data:
    """Data for {event_name} event"""
    # Add specific fields for this event
    # Example fields - customize based on your needs
    timestamp: datetime
    user_id: str
    # Add more fields as needed
    
    def to_dict(self) -> Dict[str, Any]:
        return {{
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id
        }}


class {event_name}(DomainEvent):
    """Domain event: {event_name}"""
    
    def __init__(self, aggregate_id: str, data: {event_name}Data, **kwargs):
        self.event_data = data
        super().__init__(aggregate_id, **kwargs)
    
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data"""
        return self.event_data.to_dict()
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> '{event_name}':
        """Create event from dictionary"""
        metadata = event_dict["metadata"]
        data = event_dict["data"]
        
        event_data = {event_name}Data(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data["user_id"]
        )
        
        event = cls(
            aggregate_id=metadata["aggregate_id"],
            data=event_data,
            correlation_id=metadata.get("correlation_id"),
            causation_id=metadata.get("causation_id"),
            user_id=metadata.get("user_id")
        )
        
        # Restore metadata
        event.metadata.event_id = metadata["event_id"]
        event.metadata.event_version = metadata["event_version"]
        event.metadata.aggregate_version = metadata["aggregate_version"]
        event.metadata.timestamp = datetime.fromisoformat(metadata["timestamp"])
        
        return event
'''
        
        return content
    
    def _generate_aggregate_file(self, aggregate: Dict[str, Any], variables: Dict[str, Any]) -> str:
        """Generate specific aggregate file"""
        aggregate_name = aggregate["name"]
        events = aggregate.get("events", [])
        commands = aggregate.get("commands", [])
        
        content = f'''"""
{aggregate_name} aggregate implementation
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from .base import AggregateRoot, Repository
from ..events.base import DomainEvent'''
        
        # Import specific events
        for event_name in events:
            content += f'''
from ..events.{event_name.lower()} import {event_name}'''
        
        content += f'''


@dataclass
class {aggregate_name}State:
    """State for {aggregate_name} aggregate"""
    # Add aggregate-specific state fields
    status: str = "active"
    # Add more state fields as needed
    
    def to_dict(self) -> Dict[str, Any]:
        return {{
            "status": self.status
        }}


class {aggregate_name}(AggregateRoot):
    """Domain aggregate: {aggregate_name}"""
    
    def __init__(self, aggregate_id: Optional[str] = None):
        super().__init__(aggregate_id)
        self.state = {aggregate_name}State()
    
    def _apply_event(self, event: DomainEvent) -> None:
        """Apply event to aggregate state"""
        # Handle different event types'''
        
        for event_name in events:
            content += f'''
        if isinstance(event, {event_name}):
            self._apply_{event_name.lower()}(event)'''
        
        content += f'''
    '''
        
        # Generate event handlers
        for event_name in events:
            content += f'''
    def _apply_{event_name.lower()}(self, event: {event_name}) -> None:
        """Apply {event_name} event"""
        # Update aggregate state based on event
        # Customize this based on your business logic
        pass
    '''
        
        # Generate command methods
        for command_name in commands:
            content += f'''
    def {command_name.lower()}(self, **kwargs) -> None:
        """Execute {command_name} command"""
        # Business logic validation
        # Generate and apply corresponding event
        # This is a placeholder - customize based on your needs
        pass
    '''
        
        content += f'''
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary"""
        result = super().to_dict()
        result["state"] = self.state.to_dict()
        return result


class {aggregate_name}Repository(Repository):
    """Repository for {aggregate_name} aggregate"""
    
    async def get_by_id(self, aggregate_id: str) -> Optional[{aggregate_name}]:
        """Get {aggregate_name} by ID"""
        return await self._load_aggregate({aggregate_name}, aggregate_id)
    
    async def save(self, aggregate: {aggregate_name}) -> None:
        """Save {aggregate_name} aggregate"""
        await self._save_aggregate(aggregate)'''
        
        # Add snapshot support if enabled
        if variables.get("enable_snapshots", True):
            content += f'''
    
    async def save_snapshot(self, aggregate: {aggregate_name}) -> None:
        """Save aggregate snapshot"""
        # Implement snapshot saving logic
        # This would typically save to a separate snapshot store
        pass
    
    async def load_from_snapshot(self, aggregate_id: str) -> Optional[{aggregate_name}]:
        """Load aggregate from snapshot"""
        # Implement snapshot loading logic
        # Load snapshot and then apply events since snapshot
        pass'''
        
        return content

    def _generate_cqrs_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate CQRS files - placeholder implementation"""
        files = []
        
        # Generate base CQRS classes
        base_cqrs_content = '''"""
Base CQRS classes for commands and queries
"""

from typing import Dict, Any, Optional, Generic, TypeVar
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class CommandMetadata:
    """Command metadata"""
    command_id: str
    command_type: str
    timestamp: datetime
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None


class Command(ABC):
    """Base command class"""
    
    def __init__(self, **kwargs):
        self.metadata = CommandMetadata(
            command_id=str(uuid4()),
            command_type=self.__class__.__name__,
            timestamp=datetime.utcnow(),
            user_id=kwargs.get("user_id"),
            correlation_id=kwargs.get("correlation_id"),
            source=kwargs.get("source")
        )
    
    @abstractmethod
    def validate(self) -> list[str]:
        """Validate command and return list of errors"""
        pass


class CommandHandler(ABC):
    """Base command handler"""
    
    @abstractmethod
    async def handle(self, command: Command) -> Any:
        """Handle command"""
        pass


class Query(ABC):
    """Base query class"""
    
    def __init__(self, **kwargs):
        self.metadata = {
            "query_id": str(uuid4()),
            "query_type": self.__class__.__name__,
            "timestamp": datetime.utcnow(),
            "user_id": kwargs.get("user_id")
        }


class QueryHandler(ABC):
    """Base query handler"""
    
    @abstractmethod
    async def handle(self, query: Query) -> Any:
        """Handle query"""
        pass
'''
        
        base_cqrs_path = output_dir / "app" / "commands" / "base.py"
        base_cqrs_path.write_text(base_cqrs_content, encoding="utf-8")
        files.append(base_cqrs_path)
        
        return files

    def _generate_saga_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate saga files - placeholder implementation"""
        files = []
        
        # Generate base saga classes
        base_saga_content = '''"""
Base saga classes for distributed transactions
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum


class SagaStatus(Enum):
    """Saga execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"


@dataclass
class SagaStep:
    """Individual saga step"""
    step_id: str
    step_type: str
    command: Dict[str, Any]
    compensation: Optional[Dict[str, Any]] = None
    status: str = "pending"
    executed_at: Optional[datetime] = None
    error: Optional[str] = None


class Saga(ABC):
    """Base saga class"""
    
    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id = saga_id or str(uuid4())
        self.status = SagaStatus.PENDING
        self.steps: List[SagaStep] = []
        self.current_step = 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    @abstractmethod
    def define_steps(self) -> List[SagaStep]:
        """Define saga steps"""
        pass
    
    async def execute(self) -> None:
        """Execute saga"""
        self.steps = self.define_steps()
        self.status = SagaStatus.RUNNING
        
        try:
            for i, step in enumerate(self.steps):
                self.current_step = i
                await self._execute_step(step)
                step.status = "completed"
                step.executed_at = datetime.utcnow()
            
            self.status = SagaStatus.COMPLETED
        except Exception as e:
            self.status = SagaStatus.FAILED
            await self._compensate()
    
    async def _execute_step(self, step: SagaStep) -> None:
        """Execute individual step"""
        # Implementation would depend on command type
        pass
    
    async def _compensate(self) -> None:
        """Execute compensation steps"""
        self.status = SagaStatus.COMPENSATING
        
        # Execute compensation in reverse order
        for step in reversed(self.steps[:self.current_step + 1]):
            if step.compensation and step.status == "completed":
                await self._execute_compensation(step)
        
        self.status = SagaStatus.COMPENSATED
    
    async def _execute_compensation(self, step: SagaStep) -> None:
        """Execute compensation for a step"""
        # Implementation would depend on compensation type
        pass
'''
        
        base_saga_path = output_dir / "app" / "sagas" / "base.py"
        base_saga_path.write_text(base_saga_content, encoding="utf-8")
        files.append(base_saga_path)
        
        return files

    def _generate_projection_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate projection files - placeholder implementation"""
        files = []
        
        # Generate base projection classes
        base_projection_content = '''"""
Base projection classes for read models
"""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime

from ..events.base import DomainEvent


class Projection(ABC):
    """Base projection class"""
    
    def __init__(self, projection_id: str):
        self.projection_id = projection_id
        self.last_processed_event = 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    @abstractmethod
    async def handle_event(self, event: DomainEvent) -> None:
        """Handle domain event"""
        pass
    
    @abstractmethod
    async def rebuild(self, events: List[DomainEvent]) -> None:
        """Rebuild projection from events"""
        pass


class ProjectionManager:
    """Manages projections"""
    
    def __init__(self):
        self.projections: Dict[str, Projection] = {}
        self.running = False
    
    def register_projection(self, projection: Projection) -> None:
        """Register a projection"""
        self.projections[projection.projection_id] = projection
    
    async def start(self) -> None:
        """Start projection manager"""
        self.running = True
    
    async def stop(self) -> None:
        """Stop projection manager"""
        self.running = False
    
    async def process_event(self, event: DomainEvent) -> None:
        """Process event through all projections"""
        for projection in self.projections.values():
            await projection.handle_event(event)


# Global projection manager instance
projection_manager = ProjectionManager()
'''
        
        base_projection_path = output_dir / "app" / "projections" / "base.py"
        base_projection_path.write_text(base_projection_content, encoding="utf-8")
        files.append(base_projection_path)
        
        return files

    def _generate_message_broker_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate message broker files - placeholder implementation"""
        files = []
        
        # Generate message broker manager
        broker_content = f'''"""
Message broker manager for {variables["message_broker"]}
"""

from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
import asyncio
import logging

from ..events.base import DomainEvent
from ..config import settings

logger = logging.getLogger(__name__)


class MessageBrokerManager(ABC):
    """Abstract message broker manager"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to message broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from message broker"""
        pass
    
    @abstractmethod
    async def publish_event(self, event: DomainEvent, topic: str) -> None:
        """Publish event to topic"""
        pass
    
    @abstractmethod
    async def subscribe_to_events(self, topic: str, handler: Callable) -> None:
        """Subscribe to events from topic"""
        pass


class {variables["message_broker"].title()}MessageBroker(MessageBrokerManager):
    """Message broker implementation for {variables["message_broker"]}"""
    
    def __init__(self):
        self.connected = False
        self.subscribers = {{}}
    
    async def connect(self) -> None:
        """Connect to {variables["message_broker"]}"""
        try:
            # Implementation specific to {variables["message_broker"]}
            self.connected = True
            logger.info("Connected to {variables["message_broker"]}")
        except Exception as e:
            logger.error(f"Failed to connect to {variables["message_broker"]}: {{e}}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from {variables["message_broker"]}"""
        try:
            self.connected = False
            logger.info("Disconnected from {variables["message_broker"]}")
        except Exception as e:
            logger.error(f"Failed to disconnect from {variables["message_broker"]}: {{e}}")
    
    async def publish_event(self, event: DomainEvent, topic: str) -> None:
        """Publish event to {variables["message_broker"]} topic"""
        if not self.connected:
            raise RuntimeError("Not connected to message broker")
        
        try:
            # Implementation specific to {variables["message_broker"]}
            logger.debug(f"Published event {{event.metadata.event_type}} to topic {{topic}}")
        except Exception as e:
            logger.error(f"Failed to publish event: {{e}}")
            raise
    
    async def subscribe_to_events(self, topic: str, handler: Callable) -> None:
        """Subscribe to events from {variables["message_broker"]} topic"""
        if not self.connected:
            raise RuntimeError("Not connected to message broker")
        
        try:
            self.subscribers[topic] = handler
            logger.info(f"Subscribed to topic {{topic}}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {{topic}}: {{e}}")
            raise


# Global message broker manager instance
message_broker_manager = {variables["message_broker"].title()}MessageBroker()
'''
        
        broker_path = output_dir / "app" / "message_broker" / "manager.py"
        broker_path.write_text(broker_content, encoding="utf-8")
        files.append(broker_path)
        
        return files

    def _generate_event_store_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate event store files - placeholder implementation"""
        files = []
        
        # Generate event store manager
        store_content = f'''"""
Event store manager for {variables["event_store"]}
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import logging

from ..events.base import DomainEvent, EventStore
from ..config import settings

logger = logging.getLogger(__name__)


class {variables["event_store"].title()}EventStore(EventStore):
    """Event store implementation for {variables["event_store"]}"""
    
    def __init__(self):
        self.connected = False
        self.connection = None
    
    async def connect(self) -> None:
        """Connect to {variables["event_store"]}"""
        try:
            # Implementation specific to {variables["event_store"]}
            self.connected = True
            logger.info("Connected to {variables["event_store"]} event store")
        except Exception as e:
            logger.error(f"Failed to connect to event store: {{e}}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from {variables["event_store"]}"""
        try:
            self.connected = False
            logger.info("Disconnected from event store")
        except Exception as e:
            logger.error(f"Failed to disconnect from event store: {{e}}")
    
    async def save_events(self, aggregate_id: str, events: List[DomainEvent], 
                         expected_version: int) -> None:
        """Save events to {variables["event_store"]}"""
        if not self.connected:
            raise RuntimeError("Not connected to event store")
        
        try:
            # Implementation specific to {variables["event_store"]}
            logger.debug(f"Saved {{len(events)}} events for aggregate {{aggregate_id}}")
        except Exception as e:
            logger.error(f"Failed to save events: {{e}}")
            raise
    
    async def get_events(self, aggregate_id: str, from_version: int = 0) -> List[DomainEvent]:
        """Get events for aggregate from {variables["event_store"]}"""
        if not self.connected:
            raise RuntimeError("Not connected to event store")
        
        try:
            # Implementation specific to {variables["event_store"]}
            events = []  # Load events from store
            logger.debug(f"Retrieved {{len(events)}} events for aggregate {{aggregate_id}}")
            return events
        except Exception as e:
            logger.error(f"Failed to get events: {{e}}")
            raise
    
    async def get_all_events(self, from_timestamp: Optional[datetime] = None, 
                           to_timestamp: Optional[datetime] = None) -> List[DomainEvent]:
        """Get all events in time range from {variables["event_store"]}"""
        if not self.connected:
            raise RuntimeError("Not connected to event store")
        
        try:
            # Implementation specific to {variables["event_store"]}
            events = []  # Load events from store
            logger.debug(f"Retrieved {{len(events)}} events in time range")
            return events
        except Exception as e:
            logger.error(f"Failed to get events: {{e}}")
            raise


# Global event store manager instance
event_store_manager = {variables["event_store"].title()}EventStore()
'''
        
        store_path = output_dir / "app" / "event_store" / "manager.py"
        store_path.write_text(store_content, encoding="utf-8")
        files.append(store_path)
        
        return files

    def _generate_api_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate API files - placeholder implementation"""
        files = []
        
        # Generate API router
        api_content = f'''"""
API routes for {variables["service_name"]}
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List
import logging

from ..aggregates.base import Repository
from ..commands.base import Command, CommandHandler
from ..queries.base import Query, QueryHandler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/events")
async def get_events():
    """Get events endpoint"""
    return {{"message": "Events endpoint"}}


@router.post("/commands")
async def execute_command(command_data: Dict[str, Any]):
    """Execute command endpoint"""
    return {{"message": "Command executed", "data": command_data}}


@router.get("/queries")
async def execute_query():
    """Execute query endpoint"""
    return {{"message": "Query executed"}}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {{
        "status": "healthy",
        "service": "{variables["service_name"]}",
        "type": "event_service"
    }}
'''
        
        api_path = output_dir / "app" / "api" / "v1" / "__init__.py"
        api_path.write_text(api_content, encoding="utf-8")
        files.append(api_path)
        
        return files

    def _generate_monitoring_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate monitoring files - placeholder implementation"""
        files = []
        
        # Generate monitoring setup
        monitoring_content = '''"""
Monitoring and metrics for event service
"""

from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request, Response
import time
import logging

logger = logging.getLogger(__name__)

# Metrics
events_processed = Counter('events_processed_total', 'Total events processed', ['event_type'])
command_duration = Histogram('command_duration_seconds', 'Command execution duration')
active_sagas = Gauge('active_sagas', 'Number of active sagas')
event_store_operations = Counter('event_store_operations_total', 'Event store operations', ['operation'])


async def metrics_middleware(request: Request, call_next):
    """Metrics middleware"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    # Record metrics
    if request.url.path.startswith("/api/v1/commands"):
        command_duration.observe(duration)
    
    return response


@router.get("/metrics")
async def get_metrics():
    """Metrics endpoint"""
    return {"message": "Metrics available at /metrics"}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "checks": {
            "event_store": "healthy",
            "message_broker": "healthy"
        }
    }
'''
        
        monitoring_path = output_dir / "app" / "monitoring" / "metrics.py"
        monitoring_path.write_text(monitoring_content, encoding="utf-8")
        files.append(monitoring_path)
        
        return files

    def _generate_test_files(self, variables: Dict[str, Any], output_dir: Path) -> List[Path]:
        """Generate test files - placeholder implementation"""
        files = []
        
        # Generate basic test structure
        test_content = f'''"""
Tests for {variables["service_name"]} event service
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


def test_events_endpoint():
    """Test events endpoint"""
    response = client.get("/api/v1/events")
    assert response.status_code == 200


class TestEventSourcing:
    """Test event sourcing functionality"""
    
    def test_event_creation(self):
        """Test event creation"""
        # Add event creation tests
        pass
    
    def test_aggregate_loading(self):
        """Test aggregate loading from events"""
        # Add aggregate loading tests
        pass


class TestCQRS:
    """Test CQRS functionality"""
    
    def test_command_handling(self):
        """Test command handling"""
        # Add command handling tests
        pass
    
    def test_query_handling(self):
        """Test query handling"""
        # Add query handling tests
        pass


class TestSagas:
    """Test saga functionality"""
    
    def test_saga_execution(self):
        """Test saga execution"""
        # Add saga execution tests
        pass
    
    def test_saga_compensation(self):
        """Test saga compensation"""
        # Add saga compensation tests
        pass
'''
        
        test_path = output_dir / "tests" / "test_event_service.py"
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
sqlalchemy>=2.0.0
asyncpg>=0.29.0
redis>=5.0.0
prometheus-client>=0.19.0
structlog>=23.2.0
'''
        
        if variables["message_broker"] == "kafka":
            requirements_content += "aiokafka>=0.10.0\n"
        elif variables["message_broker"] == "rabbitmq":
            requirements_content += "aio-pika>=9.3.0\n"
        elif variables["message_broker"] == "nats":
            requirements_content += "nats-py>=2.6.0\n"
        
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

# Message Broker ({variables["message_broker"]})
MESSAGE_BROKER_HOST=localhost
MESSAGE_BROKER_PORT=9092
MESSAGE_BROKER_USERNAME=
MESSAGE_BROKER_PASSWORD=

# Event Store ({variables["event_store"]})
EVENT_STORE_HOST=localhost
EVENT_STORE_PORT=5432
EVENT_STORE_DATABASE=event_store
EVENT_STORE_USERNAME=postgres
EVENT_STORE_PASSWORD=password

# Event Sourcing
ENABLE_SNAPSHOTS={str(variables.get("enable_snapshots", True)).lower()}
SNAPSHOT_FREQUENCY={variables.get("snapshot_frequency", 100)}
ENABLE_REPLAY={str(variables.get("enable_replay", True)).lower()}
RETENTION_DAYS={variables.get("retention_days", 365)}
BATCH_SIZE={variables.get("batch_size", 1000)}

# CQRS
ENABLE_CQRS={str(variables.get("enable_cqrs", True)).lower()}

# Sagas
ENABLE_SAGAS={str(variables.get("enable_sagas", True)).lower()}
SAGA_TIMEOUT=300

# Projections
ENABLE_PROJECTIONS={str(variables.get("enable_projections", True)).lower()}
PROJECTION_BATCH_SIZE=100

# Monitoring
ENABLE_MONITORING={str(variables.get("enable_monitoring", True)).lower()}
ENABLE_TRACING={str(variables.get("enable_tracing", True)).lower()}
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
      - MESSAGE_BROKER_HOST={variables["message_broker"]}
      - EVENT_STORE_HOST={variables["event_store"]}
    depends_on:
      - {variables["event_store"]}
      - {variables["message_broker"]}
    networks:
      - event-service-network

  {variables["event_store"]}:
    image: postgres:15
    environment:
      POSTGRES_DB: event_store
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - event-service-network

  {variables["message_broker"]}:'''

        if variables["message_broker"] == "kafka":
            compose_content += '''
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    depends_on:
      - zookeeper
    networks:
      - event-service-network

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - event-service-network'''
        elif variables["message_broker"] == "rabbitmq":
            compose_content += '''
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - event-service-network'''
        elif variables["message_broker"] == "redis":
            compose_content += '''
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - event-service-network'''

        compose_content += '''

volumes:
  postgres_data:

networks:
  event-service-network:
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

- **Event Sourcing**: Complete event sourcing implementation with event store
- **CQRS**: Command Query Responsibility Segregation pattern
- **Saga Pattern**: Distributed transaction management
- **Event Streaming**: Integration with {variables["message_broker"]} message broker
- **Snapshots**: Performance optimization with aggregate snapshots
- **Monitoring**: Comprehensive metrics and health checks
- **Scalability**: Designed for high-throughput event processing

## Architecture

This service implements a comprehensive event-driven architecture with:

### Event Sourcing
- Events are stored in {variables["event_store"]} event store
- Aggregates are rebuilt from event history
- Snapshot support for performance optimization

### CQRS
- Commands modify state through aggregates
- Queries read from optimized projections
- Clear separation of read and write models

### Saga Pattern
- Distributed transaction coordination
- Automatic compensation on failures
- Timeout and retry mechanisms

### Message Broker
- Event publishing to {variables["message_broker"]}
- Event subscription and processing
- Dead letter queue support

## Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- {variables["event_store"]} database
- {variables["message_broker"]} message broker

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

4. Start dependencies with Docker Compose:
   ```bash
   docker-compose up -d {variables["event_store"]} {variables["message_broker"]}
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
- `GET /api/v1/events` - Get events
- `POST /api/v1/commands` - Execute commands
- `GET /api/v1/queries` - Execute queries
- `GET /metrics` - Prometheus metrics

## Configuration

Configuration is managed through environment variables. See `.env.template` for all available options.

### Key Configuration Options

- `MESSAGE_BROKER_TYPE`: {variables["message_broker"]}
- `EVENT_STORE_TYPE`: {variables["event_store"]}
- `ENABLE_SNAPSHOTS`: Enable aggregate snapshots
- `ENABLE_SAGAS`: Enable saga pattern
- `ENABLE_PROJECTIONS`: Enable read model projections

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

The service includes comprehensive monitoring:

- **Metrics**: Prometheus metrics at `/metrics`
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
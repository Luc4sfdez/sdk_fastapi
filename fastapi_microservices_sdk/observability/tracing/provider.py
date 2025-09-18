"""
Tracing Provider with OpenTelemetry integration.

This module provides the core tracing provider functionality using OpenTelemetry
SDK with support for multiple exporters and configurable sampling strategies.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider, Resource
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.sampling import (
        TraceIdRatioBased,
        AlwaysOn,
        AlwaysOff,
        ParentBased
    )
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Create mock classes for development
    class TracerProvider:
        pass
    class Resource:
        pass
    class BatchSpanProcessor:
        pass
    class SimpleSpanProcessor:
        pass
    class JaegerExporter:
        pass
    class ZipkinExporter:
        pass
    class OTLPSpanExporter:
        pass

from ..config import TracingConfig, TracingBackend, SamplingStrategy
from .exceptions import (
    TracerProviderError,
    TraceExportError,
    SamplingError,
    handle_tracing_error
)


class ExporterType(Enum):
    """Types of trace exporters."""
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    OTLP = "otlp"
    CONSOLE = "console"


class ProcessorType(Enum):
    """Types of span processors."""
    BATCH = "batch"
    SIMPLE = "simple"


@dataclass
class TraceProviderConfig:
    """Configuration for trace provider."""
    service_name: str = "fastapi-microservice"
    service_version: str = "1.0.0"
    environment: str = "development"
    
    # Sampling configuration
    sampling_strategy: SamplingStrategy = SamplingStrategy.PROBABILISTIC
    sampling_rate: float = 0.1
    
    # Export configuration
    exporters: List[ExporterType] = field(default_factory=lambda: [ExporterType.CONSOLE])
    processor_type: ProcessorType = ProcessorType.BATCH
    
    # Batch processor settings
    max_queue_size: int = 2048
    schedule_delay_millis: int = 5000
    max_export_batch_size: int = 512
    export_timeout_millis: int = 30000
    
    # Jaeger settings
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    
    # Zipkin settings
    zipkin_endpoint: str = "http://localhost:9411/api/v2/spans"
    
    # OTLP settings
    otlp_endpoint: str = "http://localhost:4317"
    otlp_headers: Dict[str, str] = field(default_factory=dict)
    
    # Resource attributes
    resource_attributes: Dict[str, str] = field(default_factory=dict)
    
    # Advanced settings
    max_spans_per_trace: int = 1000
    span_attribute_count_limit: int = 128
    span_event_count_limit: int = 128
    span_link_count_limit: int = 128


class TracingProvider:
    """OpenTelemetry-based tracing provider."""
    
    def __init__(self, config: TraceProviderConfig):
        self.config = config
        self._tracer_provider: Optional[TracerProvider] = None
        self._processors: List[Any] = []
        self._exporters: List[Any] = []
        self._initialized = False
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
        if not OPENTELEMETRY_AVAILABLE:
            self._logger.warning("OpenTelemetry not available - tracing will be disabled")
    
    def initialize(self) -> None:
        """Initialize the tracing provider."""
        if not OPENTELEMETRY_AVAILABLE:
            raise TracerProviderError("OpenTelemetry SDK not available")
        
        with self._lock:
            if self._initialized:
                self._logger.warning("Tracing provider already initialized")
                return
            
            try:
                # Create resource
                resource = self._create_resource()
                
                # Create tracer provider
                self._tracer_provider = TracerProvider(
                    resource=resource,
                    sampler=self._create_sampler()
                )
                
                # Create and add processors
                self._create_processors()
                
                # Set as global tracer provider
                trace.set_tracer_provider(self._tracer_provider)
                
                self._initialized = True
                self._logger.info("Tracing provider initialized successfully")
                
            except Exception as e:
                self._logger.error(f"Failed to initialize tracing provider: {e}")
                raise TracerProviderError(
                    message="Failed to initialize tracing provider",
                    provider_type="opentelemetry",
                    original_error=e
                )
    
    def shutdown(self) -> None:
        """Shutdown the tracing provider."""
        with self._lock:
            if not self._initialized:
                return
            
            try:
                # Shutdown processors
                for processor in self._processors:
                    if hasattr(processor, 'shutdown'):
                        processor.shutdown()
                
                # Shutdown exporters
                for exporter in self._exporters:
                    if hasattr(exporter, 'shutdown'):
                        exporter.shutdown()
                
                self._processors.clear()
                self._exporters.clear()
                self._tracer_provider = None
                self._initialized = False
                
                self._logger.info("Tracing provider shutdown successfully")
                
            except Exception as e:
                self._logger.error(f"Error during tracing provider shutdown: {e}")
                raise TracerProviderError(
                    message="Error during tracing provider shutdown",
                    provider_type="opentelemetry",
                    original_error=e
                )
    
    def get_tracer(self, name: str, version: Optional[str] = None) -> Any:
        """Get a tracer instance."""
        if not self._initialized or not self._tracer_provider:
            raise TracerProviderError("Tracing provider not initialized")
        
        return self._tracer_provider.get_tracer(name, version)
    
    def is_initialized(self) -> bool:
        """Check if the provider is initialized."""
        return self._initialized
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        return {
            'initialized': self._initialized,
            'service_name': self.config.service_name,
            'service_version': self.config.service_version,
            'environment': self.config.environment,
            'sampling_strategy': self.config.sampling_strategy.value,
            'sampling_rate': self.config.sampling_rate,
            'exporters': [exp.value for exp in self.config.exporters],
            'processor_type': self.config.processor_type.value,
            'opentelemetry_available': OPENTELEMETRY_AVAILABLE
        }
    
    def _create_resource(self) -> Resource:
        """Create OpenTelemetry resource."""
        attributes = {
            SERVICE_NAME: self.config.service_name,
            SERVICE_VERSION: self.config.service_version,
            "service.environment": self.config.environment,
            "telemetry.sdk.name": "fastapi-microservices-sdk",
            "telemetry.sdk.version": "1.0.0"
        }
        
        # Add custom resource attributes
        attributes.update(self.config.resource_attributes)
        
        return Resource.create(attributes)
    
    def _create_sampler(self) -> Any:
        """Create sampling strategy."""
        try:
            if self.config.sampling_strategy == SamplingStrategy.ALWAYS_ON:
                return AlwaysOn()
            elif self.config.sampling_strategy == SamplingStrategy.ALWAYS_OFF:
                return AlwaysOff()
            elif self.config.sampling_strategy == SamplingStrategy.PROBABILISTIC:
                return ParentBased(root=TraceIdRatioBased(self.config.sampling_rate))
            else:
                # Default to probabilistic
                return ParentBased(root=TraceIdRatioBased(self.config.sampling_rate))
                
        except Exception as e:
            raise SamplingError(
                message=f"Failed to create sampler: {e}",
                sampling_strategy=self.config.sampling_strategy.value,
                sampling_rate=self.config.sampling_rate,
                original_error=e
            )
    
    def _create_processors(self) -> None:
        """Create and configure span processors."""
        for exporter_type in self.config.exporters:
            try:
                exporter = self._create_exporter(exporter_type)
                if exporter:
                    processor = self._create_processor(exporter)
                    self._tracer_provider.add_span_processor(processor)
                    self._processors.append(processor)
                    self._exporters.append(exporter)
                    
            except Exception as e:
                self._logger.error(f"Failed to create processor for {exporter_type.value}: {e}")
                # Continue with other exporters
    
    def _create_exporter(self, exporter_type: ExporterType) -> Optional[Any]:
        """Create trace exporter based on type."""
        try:
            if exporter_type == ExporterType.JAEGER:
                return JaegerExporter(
                    agent_host_name=self.config.jaeger_agent_host,
                    agent_port=self.config.jaeger_agent_port,
                    collector_endpoint=self.config.jaeger_endpoint
                )
            
            elif exporter_type == ExporterType.ZIPKIN:
                return ZipkinExporter(
                    endpoint=self.config.zipkin_endpoint
                )
            
            elif exporter_type == ExporterType.OTLP:
                return OTLPSpanExporter(
                    endpoint=self.config.otlp_endpoint,
                    headers=self.config.otlp_headers
                )
            
            elif exporter_type == ExporterType.CONSOLE:
                # Console exporter for development
                from opentelemetry.exporter.console import ConsoleSpanExporter
                return ConsoleSpanExporter()
            
            else:
                self._logger.warning(f"Unknown exporter type: {exporter_type}")
                return None
                
        except Exception as e:
            raise TraceExportError(
                message=f"Failed to create {exporter_type.value} exporter: {e}",
                exporter_type=exporter_type.value,
                original_error=e
            )
    
    def _create_processor(self, exporter: Any) -> Any:
        """Create span processor for exporter."""
        if self.config.processor_type == ProcessorType.BATCH:
            return BatchSpanProcessor(
                span_exporter=exporter,
                max_queue_size=self.config.max_queue_size,
                schedule_delay_millis=self.config.schedule_delay_millis,
                max_export_batch_size=self.config.max_export_batch_size,
                export_timeout_millis=self.config.export_timeout_millis
            )
        else:
            return SimpleSpanProcessor(span_exporter=exporter)


# Global tracing provider instance
_global_provider: Optional[TracingProvider] = None
_provider_lock = threading.RLock()


def get_tracer_provider() -> Optional[TracingProvider]:
    """Get the global tracer provider."""
    return _global_provider


def configure_tracing(config: Union[TracingConfig, TraceProviderConfig]) -> TracingProvider:
    """Configure global tracing provider."""
    global _global_provider
    
    with _provider_lock:
        # Shutdown existing provider if any
        if _global_provider:
            _global_provider.shutdown()
        
        # Convert TracingConfig to TraceProviderConfig if needed
        if isinstance(config, TracingConfig):
            provider_config = TraceProviderConfig(
                service_name=config.service_name,
                service_version=config.service_version or "1.0.0",
                sampling_strategy=config.sampling_strategy,
                sampling_rate=config.sampling_rate,
                jaeger_endpoint=config.jaeger_endpoint,
                jaeger_agent_host=config.jaeger_agent_host,
                jaeger_agent_port=config.jaeger_agent_port,
                otlp_endpoint=config.otlp_endpoint,
                otlp_headers=config.otlp_headers,
                resource_attributes=config.resource_attributes,
                max_spans_per_trace=config.max_spans_per_trace,
                export_timeout=config.export_timeout,
                batch_size=config.batch_size,
                max_queue_size=config.max_queue_size
            )
            
            # Map backend to exporter type
            if config.backend == TracingBackend.JAEGER:
                provider_config.exporters = [ExporterType.JAEGER]
            elif config.backend == TracingBackend.ZIPKIN:
                provider_config.exporters = [ExporterType.ZIPKIN]
            elif config.backend == TracingBackend.OTLP:
                provider_config.exporters = [ExporterType.OTLP]
            elif config.backend == TracingBackend.CONSOLE:
                provider_config.exporters = [ExporterType.CONSOLE]
        else:
            provider_config = config
        
        # Create and initialize new provider
        _global_provider = TracingProvider(provider_config)
        _global_provider.initialize()
        
        return _global_provider


def shutdown_tracing() -> None:
    """Shutdown global tracing provider."""
    global _global_provider
    
    with _provider_lock:
        if _global_provider:
            _global_provider.shutdown()
            _global_provider = None


# Utility functions
def create_provider_from_config(config: TracingConfig) -> TracingProvider:
    """Create tracing provider from TracingConfig."""
    provider_config = TraceProviderConfig(
        service_name=config.service_name,
        service_version=config.service_version or "1.0.0",
        sampling_strategy=config.sampling_strategy,
        sampling_rate=config.sampling_rate
    )
    
    return TracingProvider(provider_config)


def is_tracing_available() -> bool:
    """Check if tracing is available."""
    return OPENTELEMETRY_AVAILABLE


def get_tracing_status() -> Dict[str, Any]:
    """Get current tracing status."""
    provider = get_tracer_provider()
    
    return {
        'available': OPENTELEMETRY_AVAILABLE,
        'provider_initialized': provider is not None and provider.is_initialized(),
        'provider_info': provider.get_provider_info() if provider else None
    }


# Export main classes and functions
__all__ = [
    'ExporterType',
    'ProcessorType',
    'TraceProviderConfig',
    'TracingProvider',
    'get_tracer_provider',
    'configure_tracing',
    'shutdown_tracing',
    'create_provider_from_config',
    'is_tracing_available',
    'get_tracing_status',
    'OPENTELEMETRY_AVAILABLE',
]
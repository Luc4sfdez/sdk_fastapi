"""
Distributed Tracing module for FastAPI Microservices SDK.

This module provides comprehensive distributed tracing capabilities using
OpenTelemetry with support for multiple backends including Jaeger, Zipkin,
and OTLP collectors.

Features:
- OpenTelemetry SDK integration with automatic instrumentation
- Configurable sampling strategies (probabilistic, rate-limiting, adaptive)
- Span creation, context propagation, and lifecycle management
- HTTP header context injection/extraction
- FastAPI middleware for automatic request tracing
- Trace correlation with logging and metrics systems
- Database query tracing with sanitization
- Message broker tracing (RabbitMQ, Kafka, Redis)
- Performance analysis and bottleneck detection

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .exceptions import (
    TracingError,
    SpanCreationError,
    TraceExportError,
    SamplingError,
    ContextPropagationError
)

# Core tracing components
try:
    from .provider import (
        TracingProvider,
        TraceProviderConfig,
        get_tracer_provider,
        configure_tracing
    )
    from .tracer import (
        TracingSystem,
        Tracer,
        get_tracer,
        create_tracer
    )
    from .span import (
        Span,
        SpanContext,
        SpanKind,
        SpanStatus,
        create_span,
        get_current_span
    )
    from .sampling import (
        SamplingStrategy,
        ProbabilisticSampler,
        RateLimitingSampler,
        AdaptiveSampler,
        AlwaysOnSampler,
        AlwaysOffSampler
    )
    from .context import (
        ContextManager,
        TraceContext,
        propagate_context,
        extract_context,
        inject_context
    )
    TRACING_CORE_AVAILABLE = True
except ImportError:
    TRACING_CORE_AVAILABLE = False

# Exporters
try:
    from .exporters import (
        JaegerExporter,
        ZipkinExporter,
        OTLPExporter,
        ConsoleExporter,
        BatchSpanProcessor,
        SimpleSpanProcessor
    )
    TRACING_EXPORTERS_AVAILABLE = True
except ImportError:
    TRACING_EXPORTERS_AVAILABLE = False

# Advanced Jaeger integration
try:
    from .jaeger import (
        JaegerProtocol,
        JaegerSamplingType,
        JaegerConfig,
        AdvancedJaegerExporter,
        JaegerSamplingManager,
        JaegerTraceAnalyzer,
        create_jaeger_exporter,
        create_jaeger_config_from_tracing_config,
        JAEGER_AVAILABLE
    )
    JAEGER_ADVANCED_AVAILABLE = True
except ImportError:
    JAEGER_ADVANCED_AVAILABLE = False

# Advanced sampling strategies
try:
    from .sampling import (
        SamplingDecision,
        SamplingContext,
        SamplingStats,
        AdvancedSampler,
        ProbabilisticSampler as AdvancedProbabilisticSampler,
        RateLimitingSampler as AdvancedRateLimitingSampler,
        AdaptiveSampler as AdvancedAdaptiveSampler,
        PrioritySampler,
        CompositeSampler,
        OpenTelemetrySamplerAdapter,
        create_probabilistic_sampler,
        create_rate_limiting_sampler,
        create_adaptive_sampler,
        create_priority_sampler,
        create_composite_sampler
    )
    ADVANCED_SAMPLING_AVAILABLE = True
except ImportError:
    ADVANCED_SAMPLING_AVAILABLE = False

# Performance analysis
try:
    from .analysis import (
        PerformanceAnalyzer,
        BottleneckDetector,
        LatencyAnalysis,
        BottleneckType,
        SeverityLevel,
        PerformanceBottleneck,
        create_performance_analyzer
    )
    PERFORMANCE_ANALYSIS_AVAILABLE = True
except ImportError:
    PERFORMANCE_ANALYSIS_AVAILABLE = False

# Middleware and instrumentation
try:
    from .middleware import (
        TracingMiddleware,
        FastAPITracingMiddleware,
        create_tracing_middleware
    )
    from .instrumentation import (
        DatabaseInstrumentation,
        HTTPClientInstrumentation,
        MessageBrokerInstrumentation,
        auto_instrument
    )
    TRACING_MIDDLEWARE_AVAILABLE = True
except ImportError:
    TRACING_MIDDLEWARE_AVAILABLE = False

# Correlation and integration
try:
    from .correlation import (
        TraceCorrelation,
        correlate_with_logging,
        correlate_with_metrics,
        get_trace_correlation_id
    )
    TRACING_CORRELATION_AVAILABLE = True
except ImportError:
    TRACING_CORRELATION_AVAILABLE = False

__all__ = [
    # Exceptions
    "TracingError",
    "SpanCreationError", 
    "TraceExportError",
    "SamplingError",
    "ContextPropagationError",
    
    # Availability flags
    "TRACING_CORE_AVAILABLE",
    "TRACING_EXPORTERS_AVAILABLE", 
    "TRACING_MIDDLEWARE_AVAILABLE",
    "TRACING_CORRELATION_AVAILABLE",
    "JAEGER_ADVANCED_AVAILABLE",
    "ADVANCED_SAMPLING_AVAILABLE",
    "PERFORMANCE_ANALYSIS_AVAILABLE",
]

# Conditional exports based on availability
if TRACING_CORE_AVAILABLE:
    __all__.extend([
        "TracingProvider",
        "TraceProviderConfig",
        "get_tracer_provider",
        "configure_tracing",
        "TracingSystem",
        "Tracer",
        "get_tracer",
        "create_tracer",
        "Span",
        "SpanContext",
        "SpanKind",
        "SpanStatus",
        "create_span",
        "get_current_span",
        "SamplingStrategy",
        "ProbabilisticSampler",
        "RateLimitingSampler",
        "AdaptiveSampler",
        "AlwaysOnSampler",
        "AlwaysOffSampler",
        "ContextManager",
        "TraceContext",
        "propagate_context",
        "extract_context",
        "inject_context",
    ])

if TRACING_EXPORTERS_AVAILABLE:
    __all__.extend([
        "JaegerExporter",
        "ZipkinExporter",
        "OTLPExporter",
        "ConsoleExporter",
        "BatchSpanProcessor",
        "SimpleSpanProcessor",
    ])

if TRACING_MIDDLEWARE_AVAILABLE:
    __all__.extend([
        "TracingMiddleware",
        "FastAPITracingMiddleware",
        "create_tracing_middleware",
        "DatabaseInstrumentation",
        "HTTPClientInstrumentation",
        "MessageBrokerInstrumentation",
        "auto_instrument",
    ])

if TRACING_CORRELATION_AVAILABLE:
    __all__.extend([
        "TraceCorrelation",
        "correlate_with_logging",
        "correlate_with_metrics",
        "get_trace_correlation_id",
    ])

if JAEGER_ADVANCED_AVAILABLE:
    __all__.extend([
        "JaegerProtocol",
        "JaegerSamplingType",
        "JaegerConfig",
        "AdvancedJaegerExporter",
        "JaegerSamplingManager",
        "JaegerTraceAnalyzer",
        "create_jaeger_exporter",
        "create_jaeger_config_from_tracing_config",
        "JAEGER_AVAILABLE",
    ])

if ADVANCED_SAMPLING_AVAILABLE:
    __all__.extend([
        "SamplingDecision",
        "SamplingContext",
        "SamplingStats",
        "AdvancedSampler",
        "AdvancedProbabilisticSampler",
        "AdvancedRateLimitingSampler",
        "AdvancedAdaptiveSampler",
        "PrioritySampler",
        "CompositeSampler",
        "OpenTelemetrySamplerAdapter",
        "create_probabilistic_sampler",
        "create_rate_limiting_sampler",
        "create_adaptive_sampler",
        "create_priority_sampler",
        "create_composite_sampler",
    ])

if PERFORMANCE_ANALYSIS_AVAILABLE:
    __all__.extend([
        "PerformanceAnalyzer",
        "BottleneckDetector",
        "LatencyAnalysis",
        "BottleneckType",
        "SeverityLevel",
        "PerformanceBottleneck",
        "create_performance_analyzer",
    ])


def get_tracing_info() -> dict:
    """Get information about tracing module availability and features."""
    return {
        'core_available': TRACING_CORE_AVAILABLE,
        'exporters_available': TRACING_EXPORTERS_AVAILABLE,
        'middleware_available': TRACING_MIDDLEWARE_AVAILABLE,
        'correlation_available': TRACING_CORRELATION_AVAILABLE,
        'jaeger_advanced_available': JAEGER_ADVANCED_AVAILABLE,
        'advanced_sampling_available': ADVANCED_SAMPLING_AVAILABLE,
        'performance_analysis_available': PERFORMANCE_ANALYSIS_AVAILABLE,
        'version': '1.0.0',
        'supported_backends': [
            'Jaeger',
            'Zipkin', 
            'OTLP',
            'Console'
        ],
        'features': [
            'OpenTelemetry Integration',
            'Configurable Sampling',
            'Context Propagation',
            'FastAPI Middleware',
            'Database Tracing',
            'HTTP Client Tracing',
            'Message Broker Tracing',
            'Correlation with Logging/Metrics',
            'Advanced Jaeger Integration',
            'Intelligent Sampling Strategies',
            'Performance Analysis & Bottleneck Detection',
            'Automatic Instrumentation'
        ]
    }


# Module initialization
import logging
logger = logging.getLogger(__name__)
logger.info("FastAPI Microservices SDK Tracing module loaded")

# Log feature availability
available_features = []
if TRACING_CORE_AVAILABLE:
    available_features.append("Core Tracing")
if TRACING_EXPORTERS_AVAILABLE:
    available_features.append("Trace Exporters")
if TRACING_MIDDLEWARE_AVAILABLE:
    available_features.append("Tracing Middleware")
if TRACING_CORRELATION_AVAILABLE:
    available_features.append("Trace Correlation")
if JAEGER_ADVANCED_AVAILABLE:
    available_features.append("Advanced Jaeger Integration")
if ADVANCED_SAMPLING_AVAILABLE:
    available_features.append("Advanced Sampling")
if PERFORMANCE_ANALYSIS_AVAILABLE:
    available_features.append("Performance Analysis")

if available_features:
    logger.info(f"Available tracing features: {', '.join(available_features)}")
else:
    logger.info("Tracing core module loaded - components will be available after implementation")
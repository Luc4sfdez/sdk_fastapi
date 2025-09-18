"""
gRPC Communication Module.

This module provides comprehensive gRPC support including:
- Enterprise-grade gRPC server and client implementations
- FastAPI integration, service discovery, security, and observability features
- Streaming support with backpressure handling and interceptors
- Code generation utilities for .proto files
"""

from .server import (
    GRPCServerManager,
    GRPCServerConfig,
    FastAPIGRPCIntegration,
    EnhancedHealthServicer,
    SecurityInterceptor,
    ObservabilityInterceptor,
    create_grpc_server_config_from_communication_config,
    setup_signal_handlers
)

# Client imports with graceful fallback
try:
    from .client import (
        GRPCClient,
        GRPCClientConfig,
        LoadBalancingStrategy,
        GRPCEndpoint,
        GRPCClientInterceptor,
        AuthenticationInterceptor,
        ObservabilityClientInterceptor,
        CircuitBreakerInterceptor,
        LoadBalancer,
        create_grpc_client_config_from_communication_config,
        create_grpc_client
    )
    GRPC_CLIENT_AVAILABLE = True
except ImportError:
    GRPC_CLIENT_AVAILABLE = False

# Streaming imports with graceful fallback
try:
    from .streaming import (
        StreamingPattern,
        StreamingState,
        BackpressureStrategy,
        StreamingMetrics,
        StreamingConfig,
        StreamingError,
        BackpressureError,
        StreamingBuffer,
        StreamingInterceptor,
        AuthenticationStreamingInterceptor,
        RateLimitingStreamingInterceptor,
        StreamingMetricsCollector,
        StreamingManager,
        create_streaming_manager,
        create_authentication_interceptor as create_streaming_auth_interceptor,
        create_rate_limiting_interceptor as create_streaming_rate_limit_interceptor
    )
    GRPC_STREAMING_AVAILABLE = True
except ImportError:
    GRPC_STREAMING_AVAILABLE = False

# Code generation imports with graceful fallback
try:
    from .codegen import (
        CodeGenerationError,
        ProtoFile,
        CodeGenConfig,
        ProtoCompiler,
        ServiceStubGenerator,
        CodeGenerator,
        BuildIntegration,
        create_code_generator,
        generate_grpc_code
    )
    GRPC_CODEGEN_AVAILABLE = True
except ImportError:
    GRPC_CODEGEN_AVAILABLE = False

# Optional imports with graceful fallback
try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

try:
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    GRPC_HEALTH_AVAILABLE = True
except ImportError:
    GRPC_HEALTH_AVAILABLE = False
    health_pb2 = None
    health_pb2_grpc = None

try:
    from grpc_reflection.v1alpha import reflection
    GRPC_REFLECTION_AVAILABLE = True
except ImportError:
    GRPC_REFLECTION_AVAILABLE = False
    reflection = None


__all__ = [
    # Server components
    'GRPCServerManager',
    'GRPCServerConfig', 
    'FastAPIGRPCIntegration',
    'EnhancedHealthServicer',
    
    # Server interceptors
    'SecurityInterceptor',
    'ObservabilityInterceptor',
    
    # Client components
    'GRPCClient',
    'GRPCClientConfig',
    'LoadBalancingStrategy',
    'GRPCEndpoint',
    
    # Client interceptors
    'GRPCClientInterceptor',
    'AuthenticationInterceptor',
    'ObservabilityClientInterceptor',
    'CircuitBreakerInterceptor',
    'LoadBalancer',
    
    # Streaming components
    'StreamingPattern',
    'StreamingState',
    'BackpressureStrategy',
    'StreamingMetrics',
    'StreamingConfig',
    'StreamingError',
    'BackpressureError',
    'StreamingBuffer',
    'StreamingInterceptor',
    'AuthenticationStreamingInterceptor',
    'RateLimitingStreamingInterceptor',
    'StreamingMetricsCollector',
    'StreamingManager',
    'create_streaming_manager',
    'create_streaming_auth_interceptor',
    'create_streaming_rate_limit_interceptor',
    
    # Code generation components
    'CodeGenerationError',
    'ProtoFile',
    'CodeGenConfig',
    'ProtoCompiler',
    'ServiceStubGenerator',
    'CodeGenerator',
    'BuildIntegration',
    'create_code_generator',
    'generate_grpc_code',
    
    # Utilities
    'create_grpc_server_config_from_communication_config',
    'create_grpc_client_config_from_communication_config',
    'create_grpc_client',
    'setup_signal_handlers',
    
    # Availability flags
    'GRPC_AVAILABLE',
    'GRPC_CLIENT_AVAILABLE',
    'GRPC_STREAMING_AVAILABLE',
    'GRPC_CODEGEN_AVAILABLE',
    'GRPC_HEALTH_AVAILABLE',
    'GRPC_REFLECTION_AVAILABLE',
    
    # Re-exports (if available)
    'grpc',
    'aio',
    'health_pb2',
    'health_pb2_grpc',
    'reflection'
]


def check_grpc_dependencies():
    """Check if all required gRPC dependencies are available."""
    missing_deps = []
    
    if not GRPC_AVAILABLE:
        missing_deps.append('grpcio')
    
    if not GRPC_HEALTH_AVAILABLE:
        missing_deps.append('grpcio-health-checking')
    
    if not GRPC_REFLECTION_AVAILABLE:
        missing_deps.append('grpcio-reflection')
    
    return missing_deps


def get_grpc_status():
    """Get the status of gRPC dependencies and features."""
    missing_deps = check_grpc_dependencies()
    
    return {
        'grpc_available': GRPC_AVAILABLE,
        'client_available': GRPC_CLIENT_AVAILABLE,
        'streaming_available': GRPC_STREAMING_AVAILABLE,
        'codegen_available': GRPC_CODEGEN_AVAILABLE,
        'health_available': GRPC_HEALTH_AVAILABLE,
        'reflection_available': GRPC_REFLECTION_AVAILABLE,
        'all_dependencies_available': len(missing_deps) == 0,
        'missing_dependencies': missing_deps
    }
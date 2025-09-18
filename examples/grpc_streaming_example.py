"""
gRPC Streaming and Code Generation Example

This example demonstrates the comprehensive gRPC streaming support and code generation
utilities including:
- All streaming patterns (unary, server, client, bidirectional)
- Streaming interceptors and backpressure handling
- Code generation from .proto files
- Integration with existing gRPC client/server

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import AsyncGenerator, AsyncIterator, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import SDK components
from fastapi_microservices_sdk.communication.grpc.streaming import (
    StreamingManager,
    StreamingConfig,
    BackpressureStrategy,
    AuthenticationStreamingInterceptor,
    RateLimitingStreamingInterceptor,
    create_streaming_manager,
    create_authentication_interceptor,
    create_rate_limiting_interceptor
)

from fastapi_microservices_sdk.communication.grpc.codegen import (
    CodeGenerator,
    CodeGenConfig,
    ProtoFile,
    generate_grpc_code,
    create_code_generator
)

from fastapi_microservices_sdk.communication.grpc.client import (
    GRPCClient,
    GRPCClientConfig,
    LoadBalancingStrategy
)

from fastapi_microservices_sdk.communication.grpc.server import (
    GRPCServerManager,
    GRPCServerConfig
)


class StreamingExampleService:
    """Example service demonstrating streaming patterns."""
    
    def __init__(self, streaming_manager: StreamingManager):
        self.streaming_manager = streaming_manager
        self.logger = logging.getLogger(f"{__name__}.StreamingExampleService")
    
    async def server_streaming_example(self) -> AsyncGenerator[str, None]:
        """Example of server streaming - sending multiple responses."""
        self.logger.info("Starting server streaming example")
        
        for i in range(5):
            message = f"Server message {i + 1}"
            self.logger.info(f"Sending: {message}")
            yield message
            await asyncio.sleep(0.5)  # Simulate processing time
        
        self.logger.info("Server streaming completed")
    
    async def client_streaming_example(self) -> AsyncIterator[str]:
        """Example of client streaming - sending multiple requests."""
        self.logger.info("Starting client streaming example")
        
        for i in range(3):
            message = f"Client request {i + 1}"
            self.logger.info(f"Sending: {message}")
            yield message
            await asyncio.sleep(0.3)
        
        self.logger.info("Client streaming completed")
    
    async def bidirectional_response_handler(self, request: str) -> AsyncGenerator[str, None]:
        """Handler for bidirectional streaming responses."""
        self.logger.info(f"Processing request: {request}")
        
        # Generate multiple responses for each request
        for i in range(2):
            response = f"Response {i + 1} for '{request}'"
            self.logger.info(f"Generated response: {response}")
            yield response
            await asyncio.sleep(0.2)


async def demonstrate_streaming_patterns():
    """Demonstrate all streaming patterns."""
    logger.info("=== Demonstrating Streaming Patterns ===")
    
    # Create streaming manager with custom configuration
    config = StreamingConfig(
        max_buffer_size=100,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        enable_metrics=True,
        enable_authentication=True,
        enable_rate_limiting=True
    )
    
    streaming_manager = create_streaming_manager(config)
    
    # Add interceptors
    auth_interceptor = create_authentication_interceptor(
        token_provider=lambda: "example-jwt-token"
    )
    rate_interceptor = create_rate_limiting_interceptor(max_requests_per_second=10.0)
    
    streaming_manager.add_interceptor(auth_interceptor)
    streaming_manager.add_interceptor(rate_interceptor)
    
    service = StreamingExampleService(streaming_manager)
    
    # 1. Server Streaming Example
    logger.info("\n--- Server Streaming Example ---")
    stream_id = "server_stream_1"
    
    async for message in streaming_manager.create_server_stream(
        stream_id, service.server_streaming_example()
    ):
        logger.info(f"Received from server stream: {message}")
    
    # Get metrics for server stream
    metrics = await streaming_manager.get_stream_metrics(stream_id)
    if metrics:
        logger.info(f"Server stream metrics: {json.dumps(metrics.to_dict(), indent=2)}")
    
    # 2. Client Streaming Example
    logger.info("\n--- Client Streaming Example ---")
    stream_id = "client_stream_1"
    
    requests = await streaming_manager.create_client_stream(
        stream_id, service.client_streaming_example()
    )
    
    logger.info(f"Collected client requests: {requests}")
    
    # Get metrics for client stream
    metrics = await streaming_manager.get_stream_metrics(stream_id)
    if metrics:
        logger.info(f"Client stream metrics: {json.dumps(metrics.to_dict(), indent=2)}")
    
    # 3. Bidirectional Streaming Example
    logger.info("\n--- Bidirectional Streaming Example ---")
    stream_id = "bidirectional_stream_1"
    
    async def request_generator():
        for i in range(3):
            yield f"Bidirectional request {i + 1}"
            await asyncio.sleep(0.4)
    
    responses = []
    async for response in streaming_manager.create_bidirectional_stream(
        stream_id, request_generator(), service.bidirectional_response_handler
    ):
        logger.info(f"Received bidirectional response: {response}")
        responses.append(response)
    
    logger.info(f"Total bidirectional responses: {len(responses)}")
    
    # Get metrics for bidirectional stream
    metrics = await streaming_manager.get_stream_metrics(stream_id)
    if metrics:
        logger.info(f"Bidirectional stream metrics: {json.dumps(metrics.to_dict(), indent=2)}")
    
    # 4. Show all metrics
    logger.info("\n--- All Streaming Metrics ---")
    all_metrics = await streaming_manager.get_all_metrics()
    for stream_id, metrics in all_metrics.items():
        logger.info(f"Stream {stream_id}: {json.dumps(metrics.to_dict(), indent=2)}")


async def demonstrate_backpressure_handling():
    """Demonstrate backpressure handling."""
    logger.info("\n=== Demonstrating Backpressure Handling ===")
    
    # Create manager with small buffer for backpressure testing
    config = StreamingConfig(
        max_buffer_size=3,
        backpressure_strategy=BackpressureStrategy.DROP_OLDEST,
        enable_metrics=True
    )
    
    streaming_manager = create_streaming_manager(config)
    
    # Fast producer, slow consumer scenario
    async def fast_producer():
        for i in range(10):
            yield f"Fast message {i + 1}"
            await asyncio.sleep(0.1)  # Fast production
    
    stream_id = "backpressure_test"
    
    # Simulate slow consumption
    messages_received = []
    async for message in streaming_manager.create_server_stream(stream_id, fast_producer()):
        messages_received.append(message)
        await asyncio.sleep(0.5)  # Slow consumption
        logger.info(f"Slowly consumed: {message}")
    
    logger.info(f"Total messages received with backpressure: {len(messages_received)}")
    
    # Check backpressure metrics
    metrics = await streaming_manager.get_stream_metrics(stream_id)
    if metrics:
        logger.info(f"Backpressure metrics: backpressure_events={metrics.backpressure_events}")


def create_example_proto_file(proto_dir: Path) -> Path:
    """Create an example .proto file for code generation."""
    proto_content = '''
syntax = "proto3";

package example.streaming;

import "google/protobuf/empty.proto";
import "google/protobuf/timestamp.proto";

// Streaming service example
service StreamingService {
    // Unary RPC
    rpc GetStatus(StatusRequest) returns (StatusResponse);
    
    // Server streaming RPC
    rpc StreamData(DataRequest) returns (stream DataResponse);
    
    // Client streaming RPC
    rpc UploadData(stream UploadRequest) returns (UploadResponse);
    
    // Bidirectional streaming RPC
    rpc ProcessStream(stream ProcessRequest) returns (stream ProcessResponse);
}

// Message definitions
message StatusRequest {
    string service_name = 1;
}

message StatusResponse {
    bool healthy = 1;
    string version = 2;
    google.protobuf.Timestamp timestamp = 3;
}

message DataRequest {
    string query = 1;
    int32 limit = 2;
}

message DataResponse {
    string id = 1;
    string data = 2;
    int64 timestamp = 3;
}

message UploadRequest {
    bytes chunk = 1;
    string filename = 2;
    bool is_last = 3;
}

message UploadResponse {
    string file_id = 1;
    int64 total_size = 2;
    bool success = 3;
}

message ProcessRequest {
    string input = 1;
    map<string, string> metadata = 2;
}

message ProcessResponse {
    string output = 1;
    ProcessStatus status = 2;
}

enum ProcessStatus {
    PROCESSING = 0;
    COMPLETED = 1;
    FAILED = 2;
}
'''
    
    proto_file = proto_dir / "streaming_service.proto"
    proto_file.write_text(proto_content)
    return proto_file


async def demonstrate_code_generation():
    """Demonstrate gRPC code generation utilities."""
    logger.info("\n=== Demonstrating Code Generation ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create example proto file
        proto_file_path = create_example_proto_file(temp_path)
        logger.info(f"Created example proto file: {proto_file_path}")
        
        # Parse proto file
        proto_file = ProtoFile(proto_file_path)
        logger.info(f"Proto package: {proto_file.package}")
        logger.info(f"Proto services: {proto_file.services}")
        logger.info(f"Proto messages: {proto_file.messages}")
        logger.info(f"Proto imports: {proto_file.imports}")
        
        # Set up code generation
        output_dir = temp_path / "generated"
        
        try:
            # Generate code
            logger.info("Generating gRPC code...")
            result = generate_grpc_code(
                proto_paths=[proto_file_path],
                output_dir=output_dir,
                grpc_tools_available=False  # Skip actual protoc for demo
            )
            
            logger.info("Code generation results:")
            logger.info(f"  Compiled files: {len(result.get('compiled_files', {}))}")
            logger.info(f"  Client stubs: {list(result.get('client_stubs', {}).keys())}")
            logger.info(f"  Server stubs: {list(result.get('server_stubs', {}).keys())}")
            logger.info(f"  Errors: {len(result.get('errors', []))}")
            
            if result.get('errors'):
                for error in result['errors']:
                    logger.warning(f"  Error: {error}")
            
            # Show generated files
            if output_dir.exists():
                logger.info("Generated files:")
                for file_path in output_dir.rglob("*"):
                    if file_path.is_file():
                        logger.info(f"  {file_path.relative_to(output_dir)}")
                        
                        # Show snippet of generated client stub
                        if "client.py" in file_path.name:
                            content = file_path.read_text()
                            lines = content.split('\n')[:20]  # First 20 lines
                            logger.info("  Client stub preview:")
                            for line in lines:
                                logger.info(f"    {line}")
                            logger.info("    ...")
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            logger.info("This is expected in demo mode without protoc installed")


async def demonstrate_streaming_with_grpc_integration():
    """Demonstrate streaming integration with gRPC client/server."""
    logger.info("\n=== Demonstrating gRPC Integration ===")
    
    # Create streaming manager
    streaming_manager = create_streaming_manager()
    
    # Create gRPC client configuration
    client_config = GRPCClientConfig(
        service_name="streaming-service",
        endpoints=["localhost:50051"],
        load_balancing_strategy=LoadBalancingStrategy.ROUND_ROBIN,
        enable_streaming=True
    )
    
    logger.info(f"Created gRPC client config for streaming: {client_config.service_name}")
    
    # Create gRPC server configuration
    server_config = GRPCServerConfig(
        host="localhost",
        port=50051,
        enable_streaming=True,
        max_concurrent_streams=100
    )
    
    logger.info(f"Created gRPC server config with streaming: {server_config.host}:{server_config.port}")
    
    # Demonstrate streaming configuration integration
    logger.info("Streaming features enabled in gRPC configuration:")
    logger.info(f"  Client streaming: {client_config.enable_streaming}")
    logger.info(f"  Server streaming: {server_config.enable_streaming}")
    logger.info(f"  Max concurrent streams: {server_config.max_concurrent_streams}")


async def demonstrate_performance_monitoring():
    """Demonstrate streaming performance monitoring."""
    logger.info("\n=== Demonstrating Performance Monitoring ===")
    
    # Create streaming manager with metrics enabled
    config = StreamingConfig(
        enable_metrics=True,
        max_buffer_size=50
    )
    streaming_manager = create_streaming_manager(config)
    
    # Simulate high-throughput streaming
    async def high_throughput_generator():
        for i in range(100):
            yield f"High throughput message {i + 1}"
            await asyncio.sleep(0.01)  # Very fast generation
    
    stream_id = "performance_test"
    
    # Measure performance
    import time
    start_time = time.time()
    
    message_count = 0
    async for message in streaming_manager.create_server_stream(
        stream_id, high_throughput_generator()
    ):
        message_count += 1
        if message_count % 20 == 0:
            logger.info(f"Processed {message_count} messages...")
    
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info(f"Performance results:")
    logger.info(f"  Total messages: {message_count}")
    logger.info(f"  Duration: {duration:.2f} seconds")
    logger.info(f"  Throughput: {message_count / duration:.2f} messages/second")
    
    # Get detailed metrics
    metrics = await streaming_manager.get_stream_metrics(stream_id)
    if metrics:
        logger.info(f"Detailed metrics:")
        logger.info(f"  Messages sent: {metrics.messages_sent}")
        logger.info(f"  Bytes sent: {metrics.bytes_sent}")
        logger.info(f"  Errors: {metrics.errors}")
        logger.info(f"  Backpressure events: {metrics.backpressure_events}")


async def main():
    """Main example function."""
    logger.info("🚀 Starting gRPC Streaming and Code Generation Example")
    
    try:
        # Demonstrate streaming patterns
        await demonstrate_streaming_patterns()
        
        # Demonstrate backpressure handling
        await demonstrate_backpressure_handling()
        
        # Demonstrate code generation
        await demonstrate_code_generation()
        
        # Demonstrate gRPC integration
        await demonstrate_streaming_with_grpc_integration()
        
        # Demonstrate performance monitoring
        await demonstrate_performance_monitoring()
        
        logger.info("\n✅ All demonstrations completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
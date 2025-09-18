"""
Example: gRPC Server Integration with FastAPI

This example demonstrates how to create and run a gRPC server alongside
a FastAPI application with service discovery, health checks, and security features.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional
import uvicorn
from fastapi import FastAPI

# Import gRPC components
from fastapi_microservices_sdk.communication.grpc import (
    GRPCServerManager,
    GRPCServerConfig,
    FastAPIGRPCIntegration,
    GRPC_AVAILABLE
)
from fastapi_microservices_sdk.communication.discovery.registry import EnhancedServiceRegistry
from fastapi_microservices_sdk.communication.config import CommunicationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Example gRPC Service Implementation
# Note: In a real application, you would generate these from .proto files

class GreeterServicer:
    """Example gRPC service implementation."""
    
    SERVICE_NAME = "greeter"
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.GreeterServicer")
        self._is_healthy = True
    
    async def SayHello(self, request, context):
        """Say hello gRPC method."""
        self.logger.info(f"Received hello request: {request.name}")
        
        # Simulate some processing
        await asyncio.sleep(0.1)
        
        # In a real implementation, you would return a proper protobuf response
        response = type('HelloReply', (), {})()
        response.message = f"Hello, {request.name}!"
        
        return response
    
    async def SayHelloStream(self, request, context):
        """Streaming hello gRPC method."""
        self.logger.info(f"Received streaming hello request: {request.name}")
        
        for i in range(5):
            response = type('HelloReply', (), {})()
            response.message = f"Hello #{i+1}, {request.name}!"
            yield response
            await asyncio.sleep(0.5)
    
    def health_check(self) -> bool:
        """Custom health check for this service."""
        return self._is_healthy
    
    def set_health_status(self, is_healthy: bool):
        """Set health status for testing."""
        self._is_healthy = is_healthy


class UserServicer:
    """Another example gRPC service implementation."""
    
    SERVICE_NAME = "user"
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.UserServicer")
        self.users = {
            "1": {"id": "1", "name": "Alice", "email": "alice@example.com"},
            "2": {"id": "2", "name": "Bob", "email": "bob@example.com"}
        }
    
    async def GetUser(self, request, context):
        """Get user by ID."""
        user_id = request.user_id
        self.logger.info(f"Getting user: {user_id}")
        
        if user_id in self.users:
            user = self.users[user_id]
            response = type('User', (), {})()
            response.id = user["id"]
            response.name = user["name"]
            response.email = user["email"]
            return response
        else:
            # In real implementation, you would set proper gRPC error status
            context.set_code(404)  # grpc.StatusCode.NOT_FOUND
            context.set_details(f"User {user_id} not found")
            return None
    
    async def ListUsers(self, request, context):
        """List all users."""
        self.logger.info("Listing all users")
        
        for user_data in self.users.values():
            user = type('User', (), {})()
            user.id = user_data["id"]
            user.name = user_data["name"]
            user.email = user_data["email"]
            yield user
    
    def health_check(self) -> bool:
        """Health check for user service."""
        return len(self.users) > 0


# Mock gRPC service classes (normally generated from .proto files)
class GreeterServicer_pb2_grpc:
    """Mock gRPC service class for Greeter."""
    
    @staticmethod
    def add_to_server(servicer, server):
        """Add servicer to gRPC server."""
        logger.info(f"Added {servicer.__class__.__name__} to gRPC server")
        # In real implementation, this would add the actual gRPC service


class UserServicer_pb2_grpc:
    """Mock gRPC service class for User."""
    
    @staticmethod
    def add_to_server(servicer, server):
        """Add servicer to gRPC server."""
        logger.info(f"Added {servicer.__class__.__name__} to gRPC server")
        # In real implementation, this would add the actual gRPC service


async def create_grpc_server_example():
    """Example of creating and configuring a gRPC server."""
    logger.info("🚀 Creating gRPC Server Example")
    
    # Check if gRPC is available
    if not GRPC_AVAILABLE:
        logger.error("❌ gRPC dependencies not available. Install with: pip install grpcio grpcio-tools grpcio-health-checking grpcio-reflection")
        return None
    
    # Create gRPC server configuration
    grpc_config = GRPCServerConfig(
        host="0.0.0.0",
        port=50051,
        service_name="example-grpc-service",
        service_version="1.0.0",
        max_workers=10,
        enable_reflection=True,
        enable_health_check=True,
        enable_service_discovery=True,
        # TLS configuration (optional)
        enable_tls=False,  # Set to True for production
        # tls_cert_path="/path/to/server.crt",
        # tls_key_path="/path/to/server.key",
        graceful_shutdown_timeout=30
    )
    
    # Create service registry (optional)
    service_registry = EnhancedServiceRegistry()
    
    # Create gRPC server manager
    grpc_manager = GRPCServerManager(
        config=grpc_config,
        service_registry=service_registry
    )
    
    # Create service implementations
    greeter_service = GreeterServicer()
    user_service = UserServicer()
    
    # Add services to the server
    grpc_manager.add_service(GreeterServicer_pb2_grpc, greeter_service)
    grpc_manager.add_service(UserServicer_pb2_grpc, user_service)
    
    logger.info("✅ gRPC server configured with services:")
    logger.info(f"  - Greeter Service: {greeter_service.SERVICE_NAME}")
    logger.info(f"  - User Service: {user_service.SERVICE_NAME}")
    
    return grpc_manager, greeter_service, user_service


async def create_fastapi_app_example():
    """Example of creating a FastAPI application."""
    logger.info("🚀 Creating FastAPI Application Example")
    
    # Create FastAPI app
    app = FastAPI(
        title="gRPC + FastAPI Example",
        description="Example of running gRPC and FastAPI together",
        version="1.0.0"
    )
    
    # Add some REST endpoints
    @app.get("/")
    async def root():
        return {
            "message": "FastAPI + gRPC Integration Example",
            "services": {
                "rest_api": "http://localhost:8000",
                "grpc_api": "grpc://localhost:50051"
            }
        }
    
    @app.get("/api/status")
    async def api_status():
        return {
            "status": "running",
            "service": "fastapi",
            "version": "1.0.0"
        }
    
    @app.post("/api/users/{user_id}/greet")
    async def greet_user_via_grpc(user_id: str, name: Optional[str] = None):
        """Example of calling gRPC service from FastAPI endpoint."""
        # In a real implementation, you would use a gRPC client here
        return {
            "message": f"Would greet user {user_id} via gRPC",
            "name": name or f"User-{user_id}",
            "grpc_service": "greeter"
        }
    
    logger.info("✅ FastAPI application configured")
    return app


async def run_integrated_servers_example():
    """Example of running both FastAPI and gRPC servers together."""
    logger.info("🚀 Running Integrated Servers Example")
    
    try:
        # Create gRPC server
        grpc_result = await create_grpc_server_example()
        if not grpc_result:
            return
        
        grpc_manager, greeter_service, user_service = grpc_result
        
        # Create FastAPI app
        fastapi_app = await create_fastapi_app_example()
        
        # Create integration
        integration = FastAPIGRPCIntegration(
            fastapi_app=fastapi_app,
            grpc_manager=grpc_manager,
            fastapi_host="0.0.0.0",
            fastapi_port=8000
        )
        
        # Start gRPC server
        logger.info("🔄 Starting gRPC server...")
        await integration.start_both_servers()
        
        logger.info("✅ Both servers started successfully!")
        logger.info("📊 Server Information:")
        logger.info(f"  - FastAPI: http://localhost:8000")
        logger.info(f"  - gRPC: grpc://localhost:50051")
        logger.info(f"  - Health Check: http://localhost:8000/health")
        logger.info(f"  - Metrics: http://localhost:8000/metrics")
        
        # Display server metrics
        metrics = grpc_manager.get_metrics()
        logger.info("📈 gRPC Server Metrics:")
        for key, value in metrics.items():
            logger.info(f"  - {key}: {value}")
        
        # Simulate running for a while
        logger.info("🔄 Servers running... (Press Ctrl+C to stop)")
        
        # In a real application, you would run the FastAPI server with uvicorn
        # and keep the gRPC server running. For this example, we'll simulate it.
        try:
            await asyncio.sleep(60)  # Run for 1 minute
        except KeyboardInterrupt:
            logger.info("⏹️ Received shutdown signal")
        
        # Graceful shutdown
        logger.info("🔄 Shutting down servers...")
        await integration.stop_both_servers()
        logger.info("✅ Servers stopped gracefully")
        
    except Exception as e:
        logger.error(f"❌ Error running integrated servers: {e}")
        raise


async def demonstrate_grpc_features():
    """Demonstrate various gRPC server features."""
    logger.info("🚀 Demonstrating gRPC Features")
    
    try:
        # Create gRPC server
        grpc_result = await create_grpc_server_example()
        if not grpc_result:
            return
        
        grpc_manager, greeter_service, user_service = grpc_result
        
        # Start server
        await grpc_manager.start()
        
        # Demonstrate health checks
        logger.info("🔍 Testing Health Checks:")
        logger.info(f"  - Greeter service healthy: {greeter_service.health_check()}")
        logger.info(f"  - User service healthy: {user_service.health_check()}")
        
        # Change health status
        greeter_service.set_health_status(False)
        logger.info(f"  - Greeter service after setting unhealthy: {greeter_service.health_check()}")
        
        # Restore health
        greeter_service.set_health_status(True)
        logger.info(f"  - Greeter service after restoring health: {greeter_service.health_check()}")
        
        # Display metrics
        logger.info("📊 Server Metrics:")
        metrics = grpc_manager.get_metrics()
        for key, value in metrics.items():
            logger.info(f"  - {key}: {value}")
        
        # Demonstrate graceful shutdown
        logger.info("🔄 Testing graceful shutdown...")
        await grpc_manager.stop()
        logger.info("✅ Server stopped gracefully")
        
    except Exception as e:
        logger.error(f"❌ Error demonstrating gRPC features: {e}")
        raise


async def tls_configuration_example():
    """Example of configuring TLS for gRPC server."""
    logger.info("🔒 TLS Configuration Example")
    
    # Note: This is a demonstration of TLS configuration
    # In production, you would have actual certificate files
    
    grpc_config = GRPCServerConfig(
        host="0.0.0.0",
        port=50052,  # Different port for TLS
        service_name="secure-grpc-service",
        enable_tls=True,
        tls_cert_path="/path/to/server.crt",  # Path to server certificate
        tls_key_path="/path/to/server.key",   # Path to server private key
        tls_ca_cert_path="/path/to/ca.crt",   # Path to CA certificate (for mTLS)
        require_client_cert=True,             # Enable mTLS
        graceful_shutdown_timeout=30
    )
    
    logger.info("🔒 TLS Configuration:")
    logger.info(f"  - TLS Enabled: {grpc_config.enable_tls}")
    logger.info(f"  - Certificate Path: {grpc_config.tls_cert_path}")
    logger.info(f"  - Key Path: {grpc_config.tls_key_path}")
    logger.info(f"  - CA Certificate Path: {grpc_config.tls_ca_cert_path}")
    logger.info(f"  - Require Client Certificate: {grpc_config.require_client_cert}")
    
    # Note: We don't actually start the server here since we don't have real certificates
    logger.info("ℹ️ TLS configuration demonstrated (server not started due to missing certificates)")


def run_with_uvicorn_example():
    """Example of running FastAPI with uvicorn while gRPC runs in background."""
    logger.info("🚀 Running with Uvicorn Example")
    
    async def lifespan(app: FastAPI):
        """FastAPI lifespan event handler."""
        # Start gRPC server
        grpc_result = await create_grpc_server_example()
        if grpc_result:
            grpc_manager, _, _ = grpc_result
            await grpc_manager.start()
            logger.info("✅ gRPC server started in background")
            
            # Store in app state for access in endpoints
            app.state.grpc_manager = grpc_manager
            
            yield
            
            # Shutdown gRPC server
            await grpc_manager.stop()
            logger.info("✅ gRPC server stopped")
        else:
            yield
    
    # Create FastAPI app with lifespan
    app = FastAPI(lifespan=lifespan)
    
    @app.get("/")
    async def root():
        return {"message": "FastAPI with background gRPC server"}
    
    @app.get("/grpc-status")
    async def grpc_status():
        """Get gRPC server status."""
        if hasattr(app.state, 'grpc_manager'):
            return app.state.grpc_manager.get_metrics()
        return {"error": "gRPC server not available"}
    
    logger.info("ℹ️ To run this example with uvicorn:")
    logger.info("uvicorn examples.grpc_server_example:app --host 0.0.0.0 --port 8000")
    
    return app


# Create the app for uvicorn
app = run_with_uvicorn_example()


async def main():
    """Main function to run examples."""
    logger.info("🎯 gRPC Server Integration Examples")
    logger.info("=" * 50)
    
    examples = [
        ("Basic gRPC Server Creation", create_grpc_server_example),
        ("FastAPI Application Creation", create_fastapi_app_example),
        ("gRPC Features Demonstration", demonstrate_grpc_features),
        ("TLS Configuration", tls_configuration_example),
        # ("Integrated Servers", run_integrated_servers_example),  # Commented out as it runs for 60 seconds
    ]
    
    for name, example_func in examples:
        logger.info(f"\n📋 Running: {name}")
        logger.info("-" * 30)
        try:
            result = await example_func()
            if result:
                logger.info(f"✅ {name} completed successfully")
            else:
                logger.info(f"ℹ️ {name} completed (no result)")
        except Exception as e:
            logger.error(f"❌ {name} failed: {e}")
        
        logger.info("")
    
    logger.info("🎉 All examples completed!")
    logger.info("\n💡 To run the integrated server example:")
    logger.info("python examples/grpc_server_example.py --integrated")
    
    logger.info("\n💡 To run with uvicorn:")
    logger.info("uvicorn examples.grpc_server_example:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    import sys
    
    if "--integrated" in sys.argv:
        # Run the integrated servers example
        asyncio.run(run_integrated_servers_example())
    else:
        # Run all examples
        asyncio.run(main())
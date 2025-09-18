"""
gRPC Code Generation Utilities Module

This module provides utilities for generating gRPC code from .proto files including:
- Proto file compilation and code generation
- Service stub generation
- Message class generation
- Build integration utilities

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
import logging
import re
import ast
from abc import ABC, abstractmethod

# Internal imports
from ..exceptions import CommunicationError
from ..logging import CommunicationLogger

logger = CommunicationLogger("grpc.codegen")


class CodeGenerationError(CommunicationError):
    """Exception raised during code generation."""
    
    def __init__(self, message: str, proto_file: Optional[str] = None, 
                 command: Optional[str] = None):
        super().__init__(message)
        self.proto_file = proto_file
        self.command = command


@dataclass
class ProtoFile:
    """Represents a .proto file with metadata."""
    path: Path
    package: Optional[str] = None
    services: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List['ProtoFile'] = field(default_factory=list)
    
    def __post_init__(self):
        """Parse proto file after initialization."""
        if self.path.exists():
            self._parse_proto_file()
    
    def _parse_proto_file(self):
        """Parse proto file to extract metadata."""
        try:
            content = self.path.read_text(encoding='utf-8')
            
            # Extract package
            package_match = re.search(r'package\s+([^;]+);', content)
            if package_match:
                self.package = package_match.group(1).strip()
            
            # Extract services
            service_matches = re.findall(r'service\s+(\w+)\s*{', content)
            self.services = service_matches
            
            # Extract messages
            message_matches = re.findall(r'message\s+(\w+)\s*{', content)
            self.messages = message_matches
            
            # Extract imports
            import_matches = re.findall(r'import\s+"([^"]+)";', content)
            self.imports = import_matches
            
            logger.debug(f"Parsed proto file {self.path}: "
                        f"package={self.package}, services={self.services}, "
                        f"messages={self.messages}, imports={self.imports}")
                        
        except Exception as e:
            logger.error(f"Error parsing proto file {self.path}: {e}")
            raise CodeGenerationError(f"Failed to parse proto file: {e}", str(self.path))


@dataclass
class CodeGenConfig:
    """Configuration for code generation."""
    proto_paths: List[Path] = field(default_factory=list)
    output_dir: Path = Path("generated")
    python_out: bool = True
    grpc_python_out: bool = True
    mypy_out: bool = True
    pyi_out: bool = True
    include_paths: List[Path] = field(default_factory=list)
    protoc_executable: str = "protoc"
    grpc_tools_available: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self):
        """Validate code generation configuration."""
        if not self.proto_paths:
            raise ValueError("At least one proto path must be specified")
        
        for proto_path in self.proto_paths:
            if not proto_path.exists():
                raise ValueError(f"Proto path does not exist: {proto_path}")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if protoc is available
        try:
            result = subprocess.run([self.protoc_executable, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.warning(f"protoc not available or not working: {result.stderr}")
                self.grpc_tools_available = False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"protoc not available: {e}")
            self.grpc_tools_available = False


class ProtoCompiler:
    """Compiler for .proto files to Python code."""
    
    def __init__(self, config: CodeGenConfig):
        self.config = config
        self._compiled_files: Dict[str, Path] = {}
        
    def compile_proto_file(self, proto_file: ProtoFile) -> Dict[str, Path]:
        """Compile single proto file to Python code."""
        if not self.config.grpc_tools_available:
            logger.warning("gRPC tools not available, skipping compilation")
            return {}
        
        try:
            # Build protoc command
            cmd = [self.config.protoc_executable]
            
            # Add include paths
            for include_path in self.config.include_paths:
                cmd.extend(["-I", str(include_path)])
            
            # Add proto file directory as include path
            cmd.extend(["-I", str(proto_file.path.parent)])
            
            # Add output options
            if self.config.python_out:
                cmd.extend([f"--python_out={self.config.output_dir}"])
            
            if self.config.grpc_python_out:
                cmd.extend([f"--grpc_python_out={self.config.output_dir}"])
            
            if self.config.mypy_out:
                cmd.extend([f"--mypy_out={self.config.output_dir}"])
            
            if self.config.pyi_out:
                cmd.extend([f"--pyi_out={self.config.output_dir}"])
            
            # Add proto file
            cmd.append(str(proto_file.path))
            
            logger.info(f"Compiling proto file: {proto_file.path}")
            logger.debug(f"Protoc command: {' '.join(cmd)}")
            
            # Execute protoc
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                error_msg = f"protoc compilation failed: {result.stderr}"
                logger.error(error_msg)
                raise CodeGenerationError(error_msg, str(proto_file.path), ' '.join(cmd))
            
            # Find generated files
            generated_files = self._find_generated_files(proto_file)
            self._compiled_files.update(generated_files)
            
            logger.info(f"Successfully compiled {proto_file.path}, "
                       f"generated {len(generated_files)} files")
            
            return generated_files
            
        except subprocess.TimeoutExpired:
            error_msg = f"protoc compilation timed out for {proto_file.path}"
            logger.error(error_msg)
            raise CodeGenerationError(error_msg, str(proto_file.path))
        except Exception as e:
            error_msg = f"Unexpected error during compilation: {e}"
            logger.error(error_msg)
            raise CodeGenerationError(error_msg, str(proto_file.path))
    
    def _find_generated_files(self, proto_file: ProtoFile) -> Dict[str, Path]:
        """Find generated files for a proto file."""
        generated_files = {}
        
        # Calculate expected file names
        proto_name = proto_file.path.stem
        
        # Python message file
        pb2_file = self.config.output_dir / f"{proto_name}_pb2.py"
        if pb2_file.exists():
            generated_files['messages'] = pb2_file
        
        # gRPC service file
        grpc_file = self.config.output_dir / f"{proto_name}_pb2_grpc.py"
        if grpc_file.exists():
            generated_files['services'] = grpc_file
        
        # Type stubs
        pyi_file = self.config.output_dir / f"{proto_name}_pb2.pyi"
        if pyi_file.exists():
            generated_files['stubs'] = pyi_file
        
        return generated_files
    
    def compile_all_protos(self) -> Dict[str, Dict[str, Path]]:
        """Compile all proto files in configuration."""
        all_generated = {}
        
        for proto_path in self.config.proto_paths:
            if proto_path.is_file() and proto_path.suffix == '.proto':
                proto_file = ProtoFile(proto_path)
                generated = self.compile_proto_file(proto_file)
                all_generated[str(proto_path)] = generated
            elif proto_path.is_dir():
                # Find all .proto files in directory
                for proto_file_path in proto_path.rglob("*.proto"):
                    proto_file = ProtoFile(proto_file_path)
                    generated = self.compile_proto_file(proto_file)
                    all_generated[str(proto_file_path)] = generated
        
        return all_generated
    
    def get_compiled_files(self) -> Dict[str, Path]:
        """Get all compiled files."""
        return self._compiled_files.copy()


class ServiceStubGenerator:
    """Generator for gRPC service stubs and utilities."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_client_stub(self, proto_file: ProtoFile, 
                           service_name: str) -> Path:
        """Generate enhanced client stub for service."""
        stub_content = self._generate_client_stub_content(proto_file, service_name)
        
        stub_file = self.output_dir / f"{service_name.lower()}_client.py"
        stub_file.write_text(stub_content, encoding='utf-8')
        
        logger.info(f"Generated client stub: {stub_file}")
        return stub_file
    
    def _generate_client_stub_content(self, proto_file: ProtoFile, 
                                    service_name: str) -> str:
        """Generate content for client stub."""
        proto_name = proto_file.path.stem
        
        return f'''"""
Generated gRPC client stub for {service_name}

This file is auto-generated. Do not edit manually.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Iterator, Optional, Union

try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

# Import generated protobuf classes
try:
    from . import {proto_name}_pb2 as pb2
    from . import {proto_name}_pb2_grpc as pb2_grpc
except ImportError:
    # Fallback for different import structures
    import {proto_name}_pb2 as pb2
    import {proto_name}_pb2_grpc as pb2_grpc

from fastapi_microservices_sdk.communication.grpc.client import GRPCClient
from fastapi_microservices_sdk.communication.grpc.streaming import StreamingManager


class {service_name}Client:
    """Enhanced client for {service_name} gRPC service."""
    
    def __init__(self, grpc_client: GRPCClient, 
                 streaming_manager: Optional[StreamingManager] = None):
        self.grpc_client = grpc_client
        self.streaming_manager = streaming_manager
        self._stub = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.grpc_client.__aenter__()
        if GRPC_AVAILABLE:
            self._stub = pb2_grpc.{service_name}Stub(self.grpc_client.channel)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.grpc_client.__aexit__(exc_type, exc_val, exc_tb)
    
    @property
    def stub(self):
        """Get gRPC stub."""
        if not GRPC_AVAILABLE:
            raise RuntimeError("gRPC not available")
        return self._stub
    
    # Add your service methods here
    # Example:
    # async def your_method(self, request: pb2.YourRequest) -> pb2.YourResponse:
    #     \"\"\"Call your gRPC method.\"\"\"
    #     if not self._stub:
    #         raise RuntimeError("Client not initialized")
    #     return await self._stub.YourMethod(request)


def create_{service_name.lower()}_client(grpc_client: GRPCClient, 
                                        streaming_manager: Optional[StreamingManager] = None) -> {service_name}Client:
    """Create {service_name} client."""
    return {service_name}Client(grpc_client, streaming_manager)
'''
    
    def generate_server_stub(self, proto_file: ProtoFile, 
                           service_name: str) -> Path:
        """Generate enhanced server stub for service."""
        stub_content = self._generate_server_stub_content(proto_file, service_name)
        
        stub_file = self.output_dir / f"{service_name.lower()}_server.py"
        stub_file.write_text(stub_content, encoding='utf-8')
        
        logger.info(f"Generated server stub: {stub_file}")
        return stub_file
    
    def _generate_server_stub_content(self, proto_file: ProtoFile, 
                                    service_name: str) -> str:
        """Generate content for server stub."""
        proto_name = proto_file.path.stem
        
        return f'''"""
Generated gRPC server stub for {service_name}

This file is auto-generated. Do not edit manually.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Iterator, Optional

try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

# Import generated protobuf classes
try:
    from . import {proto_name}_pb2 as pb2
    from . import {proto_name}_pb2_grpc as pb2_grpc
except ImportError:
    # Fallback for different import structures
    import {proto_name}_pb2 as pb2
    import {proto_name}_pb2_grpc as pb2_grpc

from fastapi_microservices_sdk.communication.grpc.server import GRPCServer
from fastapi_microservices_sdk.communication.grpc.streaming import StreamingManager


class {service_name}Servicer(pb2_grpc.{service_name}Servicer if GRPC_AVAILABLE else object):
    """Implementation of {service_name} gRPC service."""
    
    def __init__(self, streaming_manager: Optional[StreamingManager] = None):
        self.streaming_manager = streaming_manager
        self.logger = logging.getLogger(f"{{__name__}}.{service_name}Servicer")
    
    # Implement your service methods here
    # Example:
    # async def YourMethod(self, request: pb2.YourRequest, 
    #                     context: grpc.aio.ServicerContext) -> pb2.YourResponse:
    #     \"\"\"Implement your gRPC method.\"\"\"
    #     self.logger.info(f"YourMethod called with request: {{request}}")
    #     
    #     # Your implementation here
    #     response = pb2.YourResponse()
    #     return response


def add_{service_name.lower()}_servicer_to_server(servicer: {service_name}Servicer, 
                                                 server: GRPCServer):
    """Add {service_name} servicer to gRPC server."""
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC not available")
    
    pb2_grpc.add_{service_name}ServicerToServer(servicer, server.server)


def create_{service_name.lower()}_servicer(streaming_manager: Optional[StreamingManager] = None) -> {service_name}Servicer:
    """Create {service_name} servicer."""
    return {service_name}Servicer(streaming_manager)
'''


class CodeGenerator:
    """Main code generator orchestrator."""
    
    def __init__(self, config: CodeGenConfig):
        self.config = config
        self.compiler = ProtoCompiler(config)
        self.stub_generator = ServiceStubGenerator(config.output_dir)
        self._proto_files: List[ProtoFile] = []
        
    def discover_proto_files(self) -> List[ProtoFile]:
        """Discover all proto files in configured paths."""
        proto_files = []
        
        for proto_path in self.config.proto_paths:
            if proto_path.is_file() and proto_path.suffix == '.proto':
                proto_files.append(ProtoFile(proto_path))
            elif proto_path.is_dir():
                for proto_file_path in proto_path.rglob("*.proto"):
                    proto_files.append(ProtoFile(proto_file_path))
        
        self._proto_files = proto_files
        logger.info(f"Discovered {len(proto_files)} proto files")
        return proto_files
    
    def generate_all(self) -> Dict[str, Any]:
        """Generate all code from proto files."""
        results = {
            'compiled_files': {},
            'client_stubs': {},
            'server_stubs': {},
            'errors': []
        }
        
        try:
            # Discover proto files
            proto_files = self.discover_proto_files()
            
            # Compile proto files
            logger.info("Starting proto compilation...")
            compiled_files = self.compiler.compile_all_protos()
            results['compiled_files'] = compiled_files
            
            # Generate service stubs
            logger.info("Generating service stubs...")
            for proto_file in proto_files:
                for service_name in proto_file.services:
                    try:
                        # Generate client stub
                        client_stub = self.stub_generator.generate_client_stub(
                            proto_file, service_name)
                        results['client_stubs'][service_name] = client_stub
                        
                        # Generate server stub
                        server_stub = self.stub_generator.generate_server_stub(
                            proto_file, service_name)
                        results['server_stubs'][service_name] = server_stub
                        
                    except Exception as e:
                        error_msg = f"Error generating stubs for {service_name}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
            
            # Generate __init__.py file
            self._generate_init_file()
            
            logger.info(f"Code generation completed. "
                       f"Generated {len(results['client_stubs'])} client stubs, "
                       f"{len(results['server_stubs'])} server stubs")
            
        except Exception as e:
            error_msg = f"Code generation failed: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
            raise CodeGenerationError(error_msg)
        
        return results
    
    def _generate_init_file(self):
        """Generate __init__.py file for generated code."""
        init_content = '''"""
Generated gRPC code package

This package contains auto-generated gRPC code.
Do not edit files in this package manually.
"""

# Import all generated modules here
# This file is auto-generated

__all__ = []

try:
    import grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

if not GRPC_AVAILABLE:
    import warnings
    warnings.warn("gRPC not available, generated code may not work properly")
'''
        
        init_file = self.config.output_dir / "__init__.py"
        init_file.write_text(init_content, encoding='utf-8')
        logger.info(f"Generated __init__.py: {init_file}")


# Factory functions
def create_code_generator(proto_paths: List[Union[str, Path]], 
                         output_dir: Union[str, Path] = "generated",
                         **kwargs) -> CodeGenerator:
    """Create code generator with configuration."""
    config = CodeGenConfig(
        proto_paths=[Path(p) for p in proto_paths],
        output_dir=Path(output_dir),
        **kwargs
    )
    return CodeGenerator(config)


def generate_grpc_code(proto_paths: List[Union[str, Path]], 
                      output_dir: Union[str, Path] = "generated",
                      **kwargs) -> Dict[str, Any]:
    """Generate gRPC code from proto files."""
    generator = create_code_generator(proto_paths, output_dir, **kwargs)
    return generator.generate_all()


# Build integration utilities
class BuildIntegration:
    """Utilities for build system integration."""
    
    @staticmethod
    def generate_setup_py_entry(proto_paths: List[Path], 
                               output_dir: Path) -> str:
        """Generate setup.py entry for proto compilation."""
        return f'''
# Add this to your setup.py for automatic proto compilation
import subprocess
from pathlib import Path

def compile_protos():
    """Compile proto files during build."""
    from fastapi_microservices_sdk.communication.grpc.codegen import generate_grpc_code
    
    proto_paths = {[str(p) for p in proto_paths]}
    output_dir = "{output_dir}"
    
    try:
        generate_grpc_code(proto_paths, output_dir)
        print("Proto compilation successful")
    except Exception as e:
        print(f"Proto compilation failed: {{e}}")
        raise

# Call during build
compile_protos()
'''
    
    @staticmethod
    def generate_makefile_target(proto_paths: List[Path], 
                               output_dir: Path) -> str:
        """Generate Makefile target for proto compilation."""
        proto_files = " ".join(str(p) for p in proto_paths)
        return f'''
# Add this target to your Makefile
.PHONY: compile-protos
compile-protos:
\tpython -c "from fastapi_microservices_sdk.communication.grpc.codegen import generate_grpc_code; generate_grpc_code(['{proto_files}'], '{output_dir}')"

# Add as dependency to your main targets
build: compile-protos
\t# Your build commands here
'''


__all__ = [
    'CodeGenerationError',
    'ProtoFile',
    'CodeGenConfig', 
    'ProtoCompiler',
    'ServiceStubGenerator',
    'CodeGenerator',
    'BuildIntegration',
    'create_code_generator',
    'generate_grpc_code'
]
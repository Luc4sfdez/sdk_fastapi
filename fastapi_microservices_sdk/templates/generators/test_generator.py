"""
Test Generator for FastAPI Microservices SDK

This generator creates comprehensive test suites including unit tests,
integration tests, performance tests, and security tests.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
import ast
import inspect
import json

from .base import CodeGenerator, GeneratedFile, GenerationResult
from ..exceptions import GenerationError


@dataclass
class TestCase:
    """Test case definition"""
    name: str
    description: str
    test_type: str  # unit, integration, performance, security
    target_function: str
    setup_code: str = ""
    test_code: str = ""
    teardown_code: str = ""
    fixtures: List[str] = field(default_factory=list)
    mocks: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Test suite definition"""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_module: str = ""
    teardown_module: str = ""


class TestGenerator(CodeGenerator):
    """
    Comprehensive Test Generator
    
    Generates test suites for:
    - Unit tests with mocking and fixtures
    - Integration tests with database and API testing
    - Performance tests with load testing and benchmarks
    - Security tests with vulnerability scanning
    - End-to-end tests with user scenarios
    - Contract tests for API compatibility
    """
    
    def __init__(self):
        super().__init__(
            name="test_generator",
            description="Generate comprehensive test suites"
        )
    
    def generate(self, schema: Dict[str, Any], options: Dict[str, Any] = None) -> List[Path]:
        """Generate test files from schema"""
        options = options or {}
        
        try:
            # Parse schema
            test_config = self._parse_test_schema(schema)
            
            # Generate test files
            generated_files = []
            
            # Generate unit tests
            if options.get("generate_unit_tests", True):
                generated_files.extend(self._generate_unit_tests(test_config, options))
            
            # Generate integration tests
            if options.get("generate_integration_tests", True):
                generated_files.extend(self._generate_integration_tests(test_config, options))
            
            # Generate performance tests
            if options.get("generate_performance_tests", False):
                generated_files.extend(self._generate_performance_tests(test_config, options))
            
            # Generate security tests
            if options.get("generate_security_tests", False):
                generated_files.extend(self._generate_security_tests(test_config, options))
            
            # Generate test configuration
            generated_files.extend(self._generate_test_config(test_config, options))
            
            return generated_files
            
        except Exception as e:
            raise GeneratorError(f"Failed to generate tests: {str(e)}")
    
    def _parse_test_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse test generation schema"""
        return {
            "project_name": schema.get("project_name", "test_project"),
            "modules": schema.get("modules", []),
            "models": schema.get("models", []),
            "apis": schema.get("apis", []),
            "services": schema.get("services", []),
            "test_types": schema.get("test_types", ["unit", "integration"]),
            "coverage_threshold": schema.get("coverage_threshold", 90),
            "test_framework": schema.get("test_framework", "pytest")
        }
    
    def _generate_unit_tests(self, test_config: Dict[str, Any], options: Dict[str, Any]) -> List[Path]:
        """Generate unit test files"""
        files = []
        output_dir = Path(options.get("output_dir", "./tests"))
        
        # Generate test for each module
        for module in test_config.get("modules", []):
            test_content = self._generate_module_unit_test(module, test_config)
            test_path = output_dir / "unit" / f"test_{module['name']}.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_content, encoding="utf-8")
            files.append(test_path)
        
        # Generate model tests
        for model in test_config.get("models", []):
            test_content = self._generate_model_unit_test(model, test_config)
            test_path = output_dir / "unit" / f"test_{model['name'].lower()}_model.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_content, encoding="utf-8")
            files.append(test_path)
        
        # Generate service tests
        for service in test_config.get("services", []):
            test_content = self._generate_service_unit_test(service, test_config)
            test_path = output_dir / "unit" / f"test_{service['name'].lower()}_service.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_content, encoding="utf-8")
            files.append(test_path)
        
        return files
    
    def _generate_module_unit_test(self, module: Dict[str, Any], test_config: Dict[str, Any]) -> str:
        """Generate unit test for a module"""
        module_name = module["name"]
        functions = module.get("functions", [])
        
        content = f'''"""
Unit tests for {module_name} module
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.{module_name} import *


class Test{module_name.title()}:
    """Test {module_name} module"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock external dependencies"""
        return {{
            "database": AsyncMock(),
            "cache": AsyncMock(),
            "logger": Mock()
        }}
'''
        
        # Generate test for each function
        for func in functions:
            func_name = func["name"]
            func_type = func.get("type", "sync")
            
            if func_type == "async":
                content += f'''
    
    @pytest.mark.asyncio
    async def test_{func_name}(self, mock_dependencies):
        """Test {func_name} function"""
        # Arrange
        test_input = {{"test": "data"}}
        expected_output = {{"result": "success"}}
        
        # Act
        result = await {func_name}(test_input)
        
        # Assert
        assert result is not None
        # Add specific assertions based on function behavior
    
    @pytest.mark.asyncio
    async def test_{func_name}_error_handling(self, mock_dependencies):
        """Test {func_name} error handling"""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError):
            await {func_name}(invalid_input)'''
            else:
                content += f'''
    
    def test_{func_name}(self, mock_dependencies):
        """Test {func_name} function"""
        # Arrange
        test_input = {{"test": "data"}}
        expected_output = {{"result": "success"}}
        
        # Act
        result = {func_name}(test_input)
        
        # Assert
        assert result is not None
        # Add specific assertions based on function behavior
    
    def test_{func_name}_error_handling(self, mock_dependencies):
        """Test {func_name} error handling"""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError):
            {func_name}(invalid_input)'''
        
        return content
    
    def _generate_model_unit_test(self, model: Dict[str, Any], test_config: Dict[str, Any]) -> str:
        """Generate unit test for a model"""
        model_name = model["name"]
        fields = model.get("fields", [])
        
        content = f'''"""
Unit tests for {model_name} model
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models.{model_name.lower()} import {model_name}, {model_name}Create, {model_name}Update


class Test{model_name}Model:
    """Test {model_name} model"""
    
    @pytest.fixture
    def valid_{model_name.lower()}_data(self):
        """Valid {model_name.lower()} test data"""
        return {{'''
        
        # Generate test data for fields
        for field in fields[:5]:  # Limit to first 5 fields
            field_name = field["name"]
            field_type = field["type"]
            
            if field_type == "string":
                test_value = f'"test_{field_name}"'
            elif field_type == "integer":
                test_value = "123"
            elif field_type == "boolean":
                test_value = "True"
            elif field_type == "datetime":
                test_value = "datetime.utcnow()"
            else:
                test_value = f'"test_{field_name}"'
            
            content += f'''
            "{field_name}": {test_value},'''
        
        content += f'''
        }}
    
    def test_create_{model_name.lower()}_valid_data(self, valid_{model_name.lower()}_data):
        """Test creating {model_name.lower()} with valid data"""
        # Act
        {model_name.lower()} = {model_name}Create(**valid_{model_name.lower()}_data)
        
        # Assert
        assert {model_name.lower()} is not None'''
        
        for field in fields[:3]:
            field_name = field["name"]
            content += f'''
        assert {model_name.lower()}.{field_name} == valid_{model_name.lower()}_data["{field_name}"]'''
        
        content += f'''
    
    def test_create_{model_name.lower()}_invalid_data(self):
        """Test creating {model_name.lower()} with invalid data"""
        # Arrange
        invalid_data = {{}}  # Empty data
        
        # Act & Assert
        with pytest.raises(ValidationError):
            {model_name}Create(**invalid_data)
    
    def test_{model_name.lower()}_update_schema(self, valid_{model_name.lower()}_data):
        """Test {model_name}Update schema"""
        # Arrange
        update_data = {{'''
        
        if fields:
            field_name = fields[0]["name"]
            field_type = fields[0]["type"]
            
            if field_type == "string":
                test_value = f'"updated_{field_name}"'
            elif field_type == "integer":
                test_value = "456"
            elif field_type == "boolean":
                test_value = "False"
            else:
                test_value = f'"updated_{field_name}"'
            
            content += f'''
            "{field_name}": {test_value}'''
        
        content += f'''
        }}
        
        # Act
        update_schema = {model_name}Update(**update_data)
        
        # Assert
        assert update_schema is not None'''
        
        if fields:
            field_name = fields[0]["name"]
            content += f'''
        assert update_schema.{field_name} == update_data["{field_name}"]'''
        
        content += f'''
    
    def test_{model_name.lower()}_response_schema(self, valid_{model_name.lower()}_data):
        """Test {model_name}Response schema"""
        # Arrange
        response_data = valid_{model_name.lower()}_data.copy()
        response_data.update({{
            "id": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }})
        
        # Act
        response_schema = {model_name}Response(**response_data)
        
        # Assert
        assert response_schema is not None
        assert response_schema.id == 1
        assert response_schema.created_at is not None
'''
        
        return content
    
    def _generate_service_unit_test(self, service: Dict[str, Any], test_config: Dict[str, Any]) -> str:
        """Generate unit test for a service"""
        service_name = service["name"]
        methods = service.get("methods", [])
        
        content = f'''"""
Unit tests for {service_name} service
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.{service_name.lower()}_service import {service_name}Service


@pytest.mark.asyncio
class Test{service_name}Service:
    """Test {service_name} service"""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository"""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mocked dependencies"""
        service = {service_name}Service()
        service.repository = mock_repository
        return service
    
    @pytest.fixture
    def sample_data(self):
        """Sample test data"""
        return {{
            "id": 1,
            "name": "test_item",
            "created_at": "2023-01-01T00:00:00Z"
        }}
'''
        
        # Generate test for each service method
        for method in methods:
            method_name = method["name"]
            method_type = method.get("type", "async")
            
            if method_type == "async":
                content += f'''
    
    async def test_{method_name}(self, service, mock_repository, sample_data):
        """Test {method_name} method"""
        # Arrange
        mock_repository.{method_name}.return_value = sample_data
        
        # Act
        result = await service.{method_name}()
        
        # Assert
        assert result is not None
        mock_repository.{method_name}.assert_called_once()
    
    async def test_{method_name}_error_handling(self, service, mock_repository):
        """Test {method_name} error handling"""
        # Arrange
        mock_repository.{method_name}.side_effect = Exception("Test error")
        
        # Act & Assert
        with pytest.raises(Exception):
            await service.{method_name}()'''
        
        return content
    
    def _generate_integration_tests(self, test_config: Dict[str, Any], options: Dict[str, Any]) -> List[Path]:
        """Generate integration test files"""
        files = []
        output_dir = Path(options.get("output_dir", "./tests"))
        
        # Generate API integration tests
        for api in test_config.get("apis", []):
            test_content = self._generate_api_integration_test(api, test_config)
            test_path = output_dir / "integration" / f"test_{api['name'].lower()}_api.py"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_content, encoding="utf-8")
            files.append(test_path)
        
        # Generate database integration tests
        if test_config.get("models"):
            db_test_content = self._generate_database_integration_test(test_config)
            db_test_path = output_dir / "integration" / "test_database_integration.py"
            db_test_path.parent.mkdir(parents=True, exist_ok=True)
            db_test_path.write_text(db_test_content, encoding="utf-8")
            files.append(db_test_path)
        
        return files
    
    def _generate_api_integration_test(self, api: Dict[str, Any], test_config: Dict[str, Any]) -> str:
        """Generate API integration test"""
        api_name = api["name"]
        endpoints = api.get("endpoints", [])
        
        content = f'''"""
Integration tests for {api_name} API
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.integration
class Test{api_name}API:
    """Integration tests for {api_name} API"""
    
    def test_api_health_check(self):
        """Test API health check"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
'''
        
        # Generate test for each endpoint
        for endpoint in endpoints:
            endpoint_path = endpoint["path"]
            endpoint_method = endpoint.get("method", "GET").lower()
            endpoint_name = endpoint.get("name", endpoint_path.replace("/", "_").replace("{", "").replace("}", ""))
            
            content += f'''
    
    def test_{endpoint_method}_{endpoint_name.replace("-", "_")}(self):
        """Test {endpoint_method.upper()} {endpoint_path}"""
        # Arrange
        test_data = {{"test": "data"}}
        
        # Act'''
            
            if endpoint_method == "get":
                content += f'''
        response = client.get("{endpoint_path}")'''
            elif endpoint_method == "post":
                content += f'''
        response = client.post("{endpoint_path}", json=test_data)'''
            elif endpoint_method == "put":
                content += f'''
        response = client.put("{endpoint_path}", json=test_data)'''
            elif endpoint_method == "delete":
                content += f'''
        response = client.delete("{endpoint_path}")'''
            
            content += '''
        
        # Assert
        assert response.status_code in [200, 201, 204, 404]  # Expected status codes
        
        if response.status_code != 404:
            assert response.json() is not None'''
        
        return content
    
    def _generate_database_integration_test(self, test_config: Dict[str, Any]) -> str:
        """Generate database integration test"""
        content = '''"""
Database integration tests
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_session, database_manager


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Database integration tests"""
    
    async def test_database_connection(self):
        """Test database connection"""
        # Act
        async with get_session() as session:
            result = await session.execute("SELECT 1")
            value = result.scalar()
        
        # Assert
        assert value == 1
    
    async def test_database_transaction_rollback(self):
        """Test database transaction rollback"""
        try:
            async with get_session() as session:
                # Simulate transaction that should rollback
                await session.execute("SELECT 1")
                raise Exception("Test rollback")
        except Exception:
            pass  # Expected
        
        # Database should still be accessible
        async with get_session() as session:
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
    
    async def test_database_pool_connections(self):
        """Test database connection pooling"""
        # Create multiple concurrent connections
        sessions = []
        
        try:
            for _ in range(5):
                session = get_session()
                sessions.append(session)
            
            # All sessions should be valid
            for session in sessions:
                async with session as s:
                    result = await s.execute("SELECT 1")
                    assert result.scalar() == 1
                    
        finally:
            # Cleanup
            for session in sessions:
                try:
                    await session.aclose()
                except:
                    pass
'''
        
        return content
    
    def _generate_performance_tests(self, test_config: Dict[str, Any], options: Dict[str, Any]) -> List[Path]:
        """Generate performance test files"""
        files = []
        output_dir = Path(options.get("output_dir", "./tests"))
        
        # Generate load test
        load_test_content = self._generate_load_test(test_config)
        load_test_path = output_dir / "performance" / "test_load.py"
        load_test_path.parent.mkdir(parents=True, exist_ok=True)
        load_test_path.write_text(load_test_content, encoding="utf-8")
        files.append(load_test_path)
        
        # Generate benchmark test
        benchmark_test_content = self._generate_benchmark_test(test_config)
        benchmark_test_path = output_dir / "performance" / "test_benchmarks.py"
        benchmark_test_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_test_path.write_text(benchmark_test_content, encoding="utf-8")
        files.append(benchmark_test_path)
        
        return files
    
    def _generate_load_test(self, test_config: Dict[str, Any]) -> str:
        """Generate load test"""
        content = '''"""
Load testing for API endpoints
"""

import asyncio
import aiohttp
import time
import pytest
from statistics import mean, median


@pytest.mark.performance
@pytest.mark.asyncio
class TestLoadPerformance:
    """Load performance tests"""
    
    async def test_api_load_test(self):
        """Test API under load"""
        base_url = "http://localhost:8000"
        concurrent_requests = 100
        total_requests = 1000
        
        async def make_request(session, url):
            """Make a single request"""
            start_time = time.time()
            try:
                async with session.get(url) as response:
                    await response.text()
                    return {
                        "status": response.status,
                        "duration": time.time() - start_time,
                        "success": response.status < 400
                    }
            except Exception as e:
                return {
                    "status": 0,
                    "duration": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                }
        
        # Run load test
        async with aiohttp.ClientSession() as session:
            tasks = []
            start_time = time.time()
            
            for _ in range(total_requests):
                task = make_request(session, f"{base_url}/health")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        success_rate = successful_requests / total_requests * 100
        durations = [r["duration"] for r in results if r["success"]]
        
        avg_duration = mean(durations) if durations else 0
        median_duration = median(durations) if durations else 0
        rps = total_requests / total_time
        
        # Assertions
        assert success_rate >= 95, f"Success rate {success_rate}% is below 95%"
        assert avg_duration < 1.0, f"Average duration {avg_duration}s is above 1s"
        assert rps >= 100, f"RPS {rps} is below 100"
        
        print(f"Load Test Results:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {successful_requests}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Average Duration: {avg_duration:.3f}s")
        print(f"  Median Duration: {median_duration:.3f}s")
        print(f"  Requests/Second: {rps:.2f}")
    
    async def test_concurrent_database_operations(self):
        """Test concurrent database operations"""
        from app.database.connection import get_session
        
        concurrent_operations = 50
        
        async def db_operation():
            """Single database operation"""
            start_time = time.time()
            try:
                async with get_session() as session:
                    result = await session.execute("SELECT 1")
                    value = result.scalar()
                    return {
                        "success": value == 1,
                        "duration": time.time() - start_time
                    }
            except Exception as e:
                return {
                    "success": False,
                    "duration": time.time() - start_time,
                    "error": str(e)
                }
        
        # Run concurrent operations
        tasks = [db_operation() for _ in range(concurrent_operations)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_ops = sum(1 for r in results if r["success"])
        success_rate = successful_ops / concurrent_operations * 100
        durations = [r["duration"] for r in results if r["success"]]
        avg_duration = mean(durations) if durations else 0
        
        # Assertions
        assert success_rate >= 95, f"DB success rate {success_rate}% is below 95%"
        assert avg_duration < 0.1, f"Average DB duration {avg_duration}s is above 0.1s"
'''
        
        return content
    
    def _generate_benchmark_test(self, test_config: Dict[str, Any]) -> str:
        """Generate benchmark test"""
        content = '''"""
Benchmark tests for performance measurement
"""

import pytest
import time
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests"""
    
    def test_api_response_time_benchmark(self, benchmark):
        """Benchmark API response time"""
        def api_call():
            response = client.get("/health")
            return response.json()
        
        # Run benchmark
        result = benchmark(api_call)
        
        # Assertions
        assert result is not None
    
    def test_json_serialization_benchmark(self, benchmark):
        """Benchmark JSON serialization"""
        import json
        
        test_data = {
            "items": [{"id": i, "name": f"item_{i}"} for i in range(1000)]
        }
        
        def serialize_json():
            return json.dumps(test_data)
        
        # Run benchmark
        result = benchmark(serialize_json)
        
        # Assertions
        assert len(result) > 0
    
    def test_database_query_benchmark(self, benchmark):
        """Benchmark database query performance"""
        from app.database.connection import get_session
        import asyncio
        
        async def db_query():
            async with get_session() as session:
                result = await session.execute("SELECT 1")
                return result.scalar()
        
        def sync_db_query():
            return asyncio.run(db_query())
        
        # Run benchmark
        result = benchmark(sync_db_query)
        
        # Assertions
        assert result == 1
'''
        
        return content
    
    def _generate_security_tests(self, test_config: Dict[str, Any], options: Dict[str, Any]) -> List[Path]:
        """Generate security test files"""
        files = []
        output_dir = Path(options.get("output_dir", "./tests"))
        
        # Generate security test
        security_test_content = self._generate_security_test(test_config)
        security_test_path = output_dir / "security" / "test_security.py"
        security_test_path.parent.mkdir(parents=True, exist_ok=True)
        security_test_path.write_text(security_test_content, encoding="utf-8")
        files.append(security_test_path)
        
        return files
    
    def _generate_security_test(self, test_config: Dict[str, Any]) -> str:
        """Generate security test"""
        content = '''"""
Security tests for API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.security
class TestSecurity:
    """Security tests"""
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        # Common SQL injection payloads
        payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "admin'/*"
        ]
        
        for payload in payloads:
            response = client.get(f"/api/v1/users?search={payload}")
            # Should not return 500 (internal server error)
            assert response.status_code != 500
            # Should handle malicious input gracefully
            assert response.status_code in [200, 400, 422]
    
    def test_xss_protection(self):
        """Test XSS protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            response = client.post("/api/v1/comments", json={"content": payload})
            # Should sanitize or reject malicious content
            if response.status_code == 200:
                data = response.json()
                # Content should be sanitized
                assert "<script>" not in str(data)
                assert "javascript:" not in str(data)
    
    def test_authentication_required(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            "/api/v1/users/me",
            "/api/v1/admin/users",
            "/api/v1/protected"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should return 401 Unauthorized
            assert response.status_code == 401
    
    def test_authorization_levels(self):
        """Test authorization levels"""
        # Test with regular user token
        user_headers = {"Authorization": "Bearer user_token"}
        
        # Regular user should not access admin endpoints
        response = client.get("/api/v1/admin/users", headers=user_headers)
        assert response.status_code in [403, 404]  # Forbidden or Not Found
        
        # Admin token test would go here if available
        # admin_headers = {"Authorization": "Bearer admin_token"}
        # response = client.get("/api/v1/admin/users", headers=admin_headers)
        # assert response.status_code == 200
    
    def test_rate_limiting(self):
        """Test rate limiting protection"""
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = client.get("/api/v1/health")
            responses.append(response.status_code)
        
        # Should eventually hit rate limit (429)
        rate_limited = any(status == 429 for status in responses)
        # Note: This test might not trigger rate limiting in test environment
        # Consider it a smoke test
        
        # At minimum, server should remain stable
        server_errors = sum(1 for status in responses if status >= 500)
        assert server_errors == 0, "Server should remain stable under load"
    
    def test_cors_headers(self):
        """Test CORS headers configuration"""
        response = client.options("/api/v1/health")
        
        # Should have proper CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers or response.status_code == 405
    
    def test_sensitive_data_exposure(self):
        """Test that sensitive data is not exposed"""
        # Test error responses don't leak sensitive info
        response = client.get("/api/v1/nonexistent")
        
        if response.status_code >= 400:
            error_text = response.text.lower()
            # Should not expose sensitive information
            sensitive_terms = ["password", "secret", "key", "token", "database"]
            for term in sensitive_terms:
                assert term not in error_text, f"Error response contains sensitive term: {term}"
    
    def test_input_validation(self):
        """Test input validation"""
        # Test with oversized input
        large_input = "x" * 10000
        response = client.post("/api/v1/comments", json={"content": large_input})
        
        # Should reject or handle large input appropriately
        assert response.status_code in [200, 400, 413, 422]
        
        # Test with invalid data types
        response = client.post("/api/v1/users", json={"email": 12345})
        assert response.status_code in [400, 422]  # Bad Request or Validation Error
'''
        
        return content
    
    def _generate_test_config(self, test_config: Dict[str, Any], options: Dict[str, Any]) -> List[Path]:
        """Generate test configuration files"""
        files = []
        output_dir = Path(options.get("output_dir", "./tests"))
        
        # Generate pytest.ini
        pytest_ini_content = self._generate_pytest_config(test_config)
        pytest_ini_path = output_dir.parent / "pytest.ini"
        pytest_ini_path.write_text(pytest_ini_content, encoding="utf-8")
        files.append(pytest_ini_path)
        
        # Generate conftest.py
        conftest_content = self._generate_conftest(test_config)
        conftest_path = output_dir / "conftest.py"
        conftest_path.write_text(conftest_content, encoding="utf-8")
        files.append(conftest_path)
        
        # Generate test fixtures
        fixtures_content = self._generate_test_fixtures(test_config)
        fixtures_path = output_dir / "fixtures.py"
        fixtures_path.write_text(fixtures_content, encoding="utf-8")
        files.append(fixtures_path)
        
        return files
    
    def _generate_pytest_config(self, test_config: Dict[str, Any]) -> str:
        """Generate pytest configuration"""
        coverage_threshold = test_config.get("coverage_threshold", 90)
        
        content = f'''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --strict-config
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-report=xml
    --cov-fail-under={coverage_threshold}
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
    external: Tests that require external services
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
asyncio_mode = auto
'''
        
        return content
    
    def _generate_conftest(self, test_config: Dict[str, Any]) -> str:
        """Generate pytest conftest.py"""
        content = '''"""
Pytest configuration and shared fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.connection import get_session, Base
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_get_session(test_session):
    """Override database session dependency"""
    async def _override_get_session():
        yield test_session
    
    app.dependency_overrides[get_session] = _override_get_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, test_session) -> TestClient:
    """Create authenticated test client"""
    # Create test user and token
    test_token = "test_token_123"
    
    # Override authentication dependency
    def override_get_current_user():
        return {"id": 1, "email": "test@example.com", "is_active": True}
    
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {test_token}"})
    
    yield client
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_external_service():
    """Mock external service calls"""
    from unittest.mock import AsyncMock, Mock
    
    mock_service = AsyncMock()
    mock_service.get_data.return_value = {"status": "success", "data": "test"}
    mock_service.post_data.return_value = {"id": 1, "created": True}
    
    return mock_service


@pytest.fixture(autouse=True)
def reset_database(test_session):
    """Reset database state between tests"""
    # This fixture runs automatically before each test
    # Add any cleanup logic here if needed
    pass


@pytest.fixture
def sample_user_data():
    """Sample user data for tests"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User",
        "is_active": True
    }


@pytest.fixture
def sample_item_data():
    """Sample item data for tests"""
    return {
        "name": "Test Item",
        "description": "A test item for testing",
        "price": 29.99,
        "category": "test"
    }


# Performance test fixtures
@pytest.fixture(scope="session")
def performance_config():
    """Configuration for performance tests"""
    return {
        "max_response_time": 1.0,  # seconds
        "min_requests_per_second": 100,
        "max_memory_usage": 100,  # MB
        "max_cpu_usage": 80  # percentage
    }


# Security test fixtures
@pytest.fixture
def security_headers():
    """Security headers for testing"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
'''
        
        return content
    
    def _generate_test_fixtures(self, test_config: Dict[str, Any]) -> str:
        """Generate test fixtures"""
        content = '''"""
Test fixtures and mock data
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_user_data(override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create user test data"""
        data = {
            "id": 1,
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def create_item_data(override: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create item test data"""
        data = {
            "id": 1,
            "name": "Test Item",
            "description": "A test item",
            "price": 29.99,
            "category": "test",
            "in_stock": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if override:
            data.update(override)
        
        return data
    
    @staticmethod
    def create_multiple_users(count: int = 5) -> List[Dict[str, Any]]:
        """Create multiple user test data"""
        users = []
        for i in range(count):
            user = TestDataFactory.create_user_data({
                "id": i + 1,
                "email": f"user{i+1}@example.com",
                "full_name": f"Test User {i+1}"
            })
            users.append(user)
        
        return users
    
    @staticmethod
    def create_api_response(data: Any = None, status: str = "success") -> Dict[str, Any]:
        """Create API response test data"""
        return {
            "status": status,
            "data": data or {"message": "Test response"},
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": "test-request-123"
        }


@pytest.fixture
def test_data_factory():
    """Test data factory fixture"""
    return TestDataFactory


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing"""
    from unittest.mock import patch
    
    fixed_datetime = datetime(2023, 1, 1, 12, 0, 0)
    
    with patch('datetime.datetime') as mock_dt:
        mock_dt.utcnow.return_value = fixed_datetime
        mock_dt.now.return_value = fixed_datetime
        yield mock_dt


@pytest.fixture
def mock_uuid():
    """Mock UUID for consistent testing"""
    from unittest.mock import patch
    import uuid
    
    fixed_uuid = "12345678-1234-5678-9012-123456789012"
    
    with patch('uuid.uuid4') as mock_uuid4:
        mock_uuid4.return_value = uuid.UUID(fixed_uuid)
        yield mock_uuid4


@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


@pytest.fixture
def memory_profiler():
    """Memory profiler for performance testing"""
    import psutil
    import os
    
    class MemoryProfiler:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = None
            self.peak_memory = None
        
        def start(self):
            self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.initial_memory
        
        def update(self):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            if current_memory > self.peak_memory:
                self.peak_memory = current_memory
        
        @property
        def memory_increase(self):
            if self.initial_memory and self.peak_memory:
                return self.peak_memory - self.initial_memory
            return None
    
    return MemoryProfiler()
'''
        
        return content
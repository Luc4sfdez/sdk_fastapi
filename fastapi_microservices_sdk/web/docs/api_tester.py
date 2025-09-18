"""
API Tester.
Provides interactive API testing capabilities with
request/response handling and testing history.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import aiohttp
from urllib.parse import urljoin
import logging

from ..core.base_manager import BaseManager
from .doc_manager import APIDocumentationManager, APIEndpoint

logger = logging.getLogger(__name__)


@dataclass
class APITestRequest:
    """API test request configuration."""
    endpoint: APIEndpoint
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    timeout: int = 30


@dataclass
class APITestResponse:
    """API test response data."""
    request_id: str
    endpoint: APIEndpoint
    status_code: int
    headers: Dict[str, str]
    body: Any
    response_time: float
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class APITestHistory:
    """API test history entry."""
    test_id: str
    request: APITestRequest
    response: APITestResponse
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    notes: str = ""


class APITester(BaseManager):
    """
    API Tester.
    
    Features:
    - Interactive API endpoint testing
    - Request parameter validation
    - Response formatting and syntax highlighting
    - Testing history and saved requests
    - Batch testing capabilities
    - Performance metrics
    """

    def __init__(self, name: str = "api_tester", config: Optional[Dict[str, Any]] = None):
        """Initialize the API tester."""
        super().__init__(name, config)
        
        # Configuration
        self._default_timeout = config.get("default_timeout", 30) if config else 30
        self._max_history_size = config.get("max_history_size", 1000) if config else 1000
        self._auto_save_requests = config.get("auto_save_requests", True) if config else True
        
        # Documentation manager reference
        self._doc_manager: Optional[APIDocumentationManager] = None
        
        # Testing history
        self._test_history: List[APITestHistory] = []
        self._saved_requests: Dict[str, APITestRequest] = {}
        
        # HTTP session
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Request counter for unique IDs
        self._request_counter = 0

    async def _initialize_impl(self) -> None:
        """Initialize the API tester."""
        try:
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._default_timeout)
            )
            
            self.logger.info("API tester initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API tester: {e}")
            raise

    async def _shutdown_impl(self) -> None:
        """Shutdown the API tester."""
        try:
            # Close HTTP session
            if self._session:
                await self._session.close()
            
            self.logger.info("API tester shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during API tester shutdown: {e}")

    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            return self._session is not None and not self._session.closed
        except Exception:
            return False

    # Manager Integration

    def set_documentation_manager(self, doc_manager: APIDocumentationManager) -> None:
        """
        Set the documentation manager reference.
        
        Args:
            doc_manager: API documentation manager instance
        """
        self._doc_manager = doc_manager

    # API Testing Methods

    async def test_endpoint(
        self,
        service_name: str,
        endpoint_path: str,
        method: str,
        parameters: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> APITestResponse:
        """
        Test a specific API endpoint.
        
        Args:
            service_name: Name of the service
            endpoint_path: Path of the endpoint
            method: HTTP method
            parameters: Query/path parameters
            headers: Request headers
            body: Request body
            timeout: Request timeout
            
        Returns:
            Test response
        """
        return await self._safe_execute(
            "test_endpoint",
            self._test_endpoint_impl,
            service_name,
            endpoint_path,
            method,
            parameters or {},
            headers or {},
            body,
            timeout or self._default_timeout
        )

    async def _test_endpoint_impl(
        self,
        service_name: str,
        endpoint_path: str,
        method: str,
        parameters: Dict[str, Any],
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
        timeout: int
    ) -> APITestResponse:
        """Implementation for endpoint testing."""
        try:
            if not self._doc_manager:
                raise ValueError("Documentation manager not set")
            
            # Get endpoint information
            endpoints = await self._doc_manager.get_service_endpoints(service_name)
            endpoint = None
            
            for ep in endpoints:
                if ep.path == endpoint_path and ep.method.upper() == method.upper():
                    endpoint = ep
                    break
            
            if not endpoint:
                raise ValueError(f"Endpoint not found: {method} {endpoint_path}")
            
            # Get service information
            services = await self._doc_manager.get_all_services()
            service = None
            
            for svc in services:
                if svc.service_name == service_name:
                    service = svc
                    break
            
            if not service:
                raise ValueError(f"Service not found: {service_name}")
            
            # Generate request ID
            self._request_counter += 1
            request_id = f"req_{self._request_counter}_{int(datetime.utcnow().timestamp())}"
            
            # Build request
            request = APITestRequest(
                endpoint=endpoint,
                parameters=parameters,
                headers=headers,
                body=body,
                timeout=timeout
            )
            
            # Execute request
            response = await self._execute_request(service.base_url, request, request_id)
            
            # Save to history if enabled
            if self._auto_save_requests:
                await self._add_to_history(request, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to test endpoint {method} {endpoint_path}: {e}")
            
            # Create error response
            self._request_counter += 1
            request_id = f"req_{self._request_counter}_{int(datetime.utcnow().timestamp())}"
            
            return APITestResponse(
                request_id=request_id,
                endpoint=APIEndpoint(
                    service_name=service_name,
                    path=endpoint_path,
                    method=method,
                    summary="",
                    description=""
                ),
                status_code=0,
                headers={},
                body=None,
                response_time=0.0,
                timestamp=datetime.utcnow(),
                error=str(e)
            )

    async def _execute_request(
        self,
        base_url: str,
        request: APITestRequest,
        request_id: str
    ) -> APITestResponse:
        """Execute HTTP request."""
        if not self._session:
            raise RuntimeError("HTTP session not available")
        
        start_time = datetime.utcnow()
        
        try:
            # Build URL
            url = urljoin(base_url.rstrip('/') + '/', request.endpoint.path.lstrip('/'))
            
            # Replace path parameters
            for param_name, param_value in request.parameters.items():
                if f"{{{param_name}}}" in url:
                    url = url.replace(f"{{{param_name}}}", str(param_value))
            
            # Prepare query parameters
            query_params = {}
            for param_name, param_value in request.parameters.items():
                if f"{{{param_name}}}" not in request.endpoint.path:
                    query_params[param_name] = param_value
            
            # Prepare request arguments
            request_kwargs = {
                "headers": request.headers,
                "timeout": aiohttp.ClientTimeout(total=request.timeout)
            }
            
            if query_params:
                request_kwargs["params"] = query_params
            
            if request.body and request.endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
                request_kwargs["json"] = request.body
            
            # Execute request
            async with self._session.request(
                request.endpoint.method.upper(),
                url,
                **request_kwargs
            ) as response:
                
                # Calculate response time
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds()
                
                # Read response body
                try:
                    if response.content_type == 'application/json':
                        response_body = await response.json()
                    else:
                        response_body = await response.text()
                except Exception:
                    response_body = await response.text()
                
                return APITestResponse(
                    request_id=request_id,
                    endpoint=request.endpoint,
                    status_code=response.status,
                    headers=dict(response.headers),
                    body=response_body,
                    response_time=response_time,
                    timestamp=start_time
                )
                
        except Exception as e:
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            return APITestResponse(
                request_id=request_id,
                endpoint=request.endpoint,
                status_code=0,
                headers={},
                body=None,
                response_time=response_time,
                timestamp=start_time,
                error=str(e)
            )

    # Batch Testing Methods

    async def test_multiple_endpoints(
        self,
        test_configs: List[Dict[str, Any]]
    ) -> List[APITestResponse]:
        """
        Test multiple endpoints in batch.
        
        Args:
            test_configs: List of test configurations
            
        Returns:
            List of test responses
        """
        return await self._safe_execute(
            "test_multiple_endpoints",
            self._test_multiple_endpoints_impl,
            test_configs
        )

    async def _test_multiple_endpoints_impl(
        self,
        test_configs: List[Dict[str, Any]]
    ) -> List[APITestResponse]:
        """Implementation for batch testing."""
        try:
            tasks = []
            
            for config in test_configs:
                task = self._test_endpoint_impl(
                    config.get("service_name"),
                    config.get("endpoint_path"),
                    config.get("method"),
                    config.get("parameters", {}),
                    config.get("headers", {}),
                    config.get("body"),
                    config.get("timeout", self._default_timeout)
                )
                tasks.append(task)
            
            # Execute all tests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert exceptions to error responses
            results = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    config = test_configs[i]
                    self._request_counter += 1
                    request_id = f"req_{self._request_counter}_{int(datetime.utcnow().timestamp())}"
                    
                    error_response = APITestResponse(
                        request_id=request_id,
                        endpoint=APIEndpoint(
                            service_name=config.get("service_name", ""),
                            path=config.get("endpoint_path", ""),
                            method=config.get("method", ""),
                            summary="",
                            description=""
                        ),
                        status_code=0,
                        headers={},
                        body=None,
                        response_time=0.0,
                        timestamp=datetime.utcnow(),
                        error=str(response)
                    )
                    results.append(error_response)
                else:
                    results.append(response)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to test multiple endpoints: {e}")
            return []

    # Request Management Methods

    async def save_request(
        self,
        name: str,
        service_name: str,
        endpoint_path: str,
        method: str,
        parameters: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """
        Save a request configuration for later use.
        
        Args:
            name: Name for the saved request
            service_name: Name of the service
            endpoint_path: Path of the endpoint
            method: HTTP method
            parameters: Query/path parameters
            headers: Request headers
            body: Request body
            timeout: Request timeout
            
        Returns:
            True if request saved successfully
        """
        return await self._safe_execute(
            "save_request",
            self._save_request_impl,
            name,
            service_name,
            endpoint_path,
            method,
            parameters or {},
            headers or {},
            body,
            timeout or self._default_timeout
        )

    async def _save_request_impl(
        self,
        name: str,
        service_name: str,
        endpoint_path: str,
        method: str,
        parameters: Dict[str, Any],
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]],
        timeout: int
    ) -> bool:
        """Implementation for saving request."""
        try:
            if not self._doc_manager:
                return False
            
            # Get endpoint information
            endpoints = await self._doc_manager.get_service_endpoints(service_name)
            endpoint = None
            
            for ep in endpoints:
                if ep.path == endpoint_path and ep.method.upper() == method.upper():
                    endpoint = ep
                    break
            
            if not endpoint:
                return False
            
            # Create request configuration
            request = APITestRequest(
                endpoint=endpoint,
                parameters=parameters,
                headers=headers,
                body=body,
                timeout=timeout
            )
            
            # Save request
            self._saved_requests[name] = request
            
            self.logger.info(f"Saved request: {name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save request {name}: {e}")
            return False

    async def load_saved_request(self, name: str) -> Optional[APITestRequest]:
        """
        Load a saved request configuration.
        
        Args:
            name: Name of the saved request
            
        Returns:
            Request configuration or None
        """
        return self._saved_requests.get(name)

    async def get_saved_requests(self) -> Dict[str, APITestRequest]:
        """
        Get all saved request configurations.
        
        Returns:
            Dictionary of saved requests
        """
        return self._saved_requests.copy()

    async def delete_saved_request(self, name: str) -> bool:
        """
        Delete a saved request configuration.
        
        Args:
            name: Name of the saved request
            
        Returns:
            True if request deleted successfully
        """
        if name in self._saved_requests:
            del self._saved_requests[name]
            self.logger.info(f"Deleted saved request: {name}")
            return True
        return False

    # History Management Methods

    async def _add_to_history(
        self,
        request: APITestRequest,
        response: APITestResponse
    ) -> None:
        """Add test to history."""
        try:
            history_entry = APITestHistory(
                test_id=response.request_id,
                request=request,
                response=response,
                timestamp=response.timestamp
            )
            
            self._test_history.append(history_entry)
            
            # Trim history if it exceeds max size
            if len(self._test_history) > self._max_history_size:
                self._test_history = self._test_history[-self._max_history_size:]
                
        except Exception as e:
            self.logger.error(f"Failed to add to history: {e}")

    async def get_test_history(
        self,
        limit: Optional[int] = None,
        service_name: Optional[str] = None
    ) -> List[APITestHistory]:
        """
        Get test history.
        
        Args:
            limit: Maximum number of entries to return
            service_name: Filter by service name
            
        Returns:
            List of history entries
        """
        try:
            history = self._test_history.copy()
            
            # Filter by service name if specified
            if service_name:
                history = [
                    entry for entry in history
                    if entry.request.endpoint.service_name == service_name
                ]
            
            # Sort by timestamp (most recent first)
            history.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit if specified
            if limit:
                history = history[:limit]
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get test history: {e}")
            return []

    async def clear_test_history(self, service_name: Optional[str] = None) -> bool:
        """
        Clear test history.
        
        Args:
            service_name: Clear history for specific service, or None for all
            
        Returns:
            True if history cleared successfully
        """
        try:
            if service_name:
                self._test_history = [
                    entry for entry in self._test_history
                    if entry.request.endpoint.service_name != service_name
                ]
            else:
                self._test_history.clear()
            
            self.logger.info(f"Cleared test history for {service_name or 'all services'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear test history: {e}")
            return False

    # Validation Methods

    async def validate_request_parameters(
        self,
        endpoint: APIEndpoint,
        parameters: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Validate request parameters against endpoint specification.
        
        Args:
            endpoint: API endpoint
            parameters: Parameters to validate
            
        Returns:
            Dictionary of validation errors
        """
        return await self._safe_execute(
            "validate_request_parameters",
            self._validate_request_parameters_impl,
            endpoint,
            parameters
        )

    async def _validate_request_parameters_impl(
        self,
        endpoint: APIEndpoint,
        parameters: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Implementation for parameter validation."""
        try:
            errors = {}
            
            # Check required parameters
            for param in endpoint.parameters:
                param_name = param.get("name")
                required = param.get("required", False)
                
                if required and param_name not in parameters:
                    if "missing" not in errors:
                        errors["missing"] = []
                    errors["missing"].append(f"Required parameter '{param_name}' is missing")
            
            # Check parameter types (basic validation)
            for param_name, param_value in parameters.items():
                # Find parameter definition
                param_def = None
                for param in endpoint.parameters:
                    if param.get("name") == param_name:
                        param_def = param
                        break
                
                if param_def:
                    expected_type = param_def.get("schema", {}).get("type", "string")
                    
                    # Basic type checking
                    if expected_type == "integer" and not isinstance(param_value, int):
                        if "type_mismatch" not in errors:
                            errors["type_mismatch"] = []
                        errors["type_mismatch"].append(
                            f"Parameter '{param_name}' should be integer, got {type(param_value).__name__}"
                        )
                    elif expected_type == "number" and not isinstance(param_value, (int, float)):
                        if "type_mismatch" not in errors:
                            errors["type_mismatch"] = []
                        errors["type_mismatch"].append(
                            f"Parameter '{param_name}' should be number, got {type(param_value).__name__}"
                        )
                    elif expected_type == "boolean" and not isinstance(param_value, bool):
                        if "type_mismatch" not in errors:
                            errors["type_mismatch"] = []
                        errors["type_mismatch"].append(
                            f"Parameter '{param_name}' should be boolean, got {type(param_value).__name__}"
                        )
            
            return errors
            
        except Exception as e:
            self.logger.error(f"Failed to validate parameters: {e}")
            return {"validation_error": [str(e)]}

    # Statistics Methods

    async def get_testing_statistics(self) -> Dict[str, Any]:
        """
        Get testing statistics.
        
        Returns:
            Statistics dictionary
        """
        return await self._safe_execute(
            "get_testing_statistics",
            self._get_testing_statistics_impl
        )

    async def _get_testing_statistics_impl(self) -> Dict[str, Any]:
        """Implementation for getting testing statistics."""
        try:
            if not self._test_history:
                return {
                    "total_tests": 0,
                    "success_rate": 0.0,
                    "average_response_time": 0.0,
                    "tests_by_service": {},
                    "tests_by_status": {},
                    "saved_requests": len(self._saved_requests)
                }
            
            total_tests = len(self._test_history)
            successful_tests = sum(
                1 for entry in self._test_history
                if 200 <= entry.response.status_code < 300 and not entry.response.error
            )
            
            success_rate = successful_tests / total_tests if total_tests > 0 else 0.0
            
            # Calculate average response time
            response_times = [
                entry.response.response_time for entry in self._test_history
                if entry.response.response_time > 0
            ]
            average_response_time = sum(response_times) / len(response_times) if response_times else 0.0
            
            # Count tests by service
            tests_by_service = {}
            for entry in self._test_history:
                service = entry.request.endpoint.service_name
                tests_by_service[service] = tests_by_service.get(service, 0) + 1
            
            # Count tests by status code
            tests_by_status = {}
            for entry in self._test_history:
                status = entry.response.status_code
                tests_by_status[str(status)] = tests_by_status.get(str(status), 0) + 1
            
            return {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "average_response_time": average_response_time,
                "tests_by_service": tests_by_service,
                "tests_by_status": tests_by_status,
                "saved_requests": len(self._saved_requests)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get testing statistics: {e}")
            return {}
# fastapi-microservices-sdk/fastapi_microservices_sdk/communication/http/client.py 
"""
HTTP client for inter-service communication.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Union, List
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient, Response

from ...config import get_config
from ...exceptions import CommunicationError, TimeoutError
from ...constants import REQUEST_ID_HEADER, SERVICE_NAME_HEADER
from ...core.service_registry import ServiceRegistry
from ...utils.helpers import generate_request_id


class HTTPServiceClient:
    """
    HTTP client for communicating with other microservices.
    
    Features:
    - Service discovery integration
    - Automatic retries
    - Request/response logging
    - Timeout handling
    - Load balancing (basic round-robin)
    """
    
    def __init__(
        self,
        service_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize HTTP service client.
        
        Args:
            service_name: Name of the target service (for service discovery)
            base_url: Base URL if not using service discovery
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.service_name = service_name
        self.base_url = base_url
        self.config = get_config()
        self.timeout = timeout or self.config.default_timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(f"http_client.{service_name or 'unknown'}")
        
        # Service discovery
        self.registry = ServiceRegistry.get_instance() if self.config.enable_service_discovery else None
        self._service_instances = []
        self._current_instance_index = 0
        
        # HTTP client
        self._client: Optional[AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True
            )
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _get_service_url(self) -> str:
        """
        Get service URL either from service discovery or base_url.
        
        Returns:
            Service base URL
            
        Raises:
            CommunicationError: If service cannot be discovered
        """
        if self.base_url:
            return self.base_url
        
        if not self.service_name:
            raise CommunicationError("Either service_name or base_url must be provided")
        
        if not self.registry:
            raise CommunicationError("Service discovery is disabled")
        
        # Discover service instances
        instances = await self.registry.discover_service(self.service_name)
        if not instances:
            raise CommunicationError(f"No healthy instances found for service: {self.service_name}")
        
        # Simple round-robin load balancing
        self._service_instances = instances
        if self._current_instance_index >= len(instances):
            self._current_instance_index = 0
        
        instance = instances[self._current_instance_index]
        self._current_instance_index = (self._current_instance_index + 1) % len(instances)
        
        return instance.url
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare request headers with standard microservice headers.
        
        Args:
            headers: Additional headers
            
        Returns:
            Complete headers dictionary
        """
        default_headers = {
            REQUEST_ID_HEADER: generate_request_id(),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.service_name:
            default_headers[SERVICE_NAME_HEADER] = self.service_name
        
        if headers:
            default_headers.update(headers)
        
        return default_headers
    
    async def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Response:
        """
        Make HTTP request with retries and error handling.
        
        Args:
            method: HTTP method
            path: Request path
            **kwargs: Additional request arguments
            
        Returns:
            HTTP response
            
        Raises:
            CommunicationError: If request fails after retries
            TimeoutError: If request times out
        """
        await self._ensure_client()
        
        # Prepare headers
        headers = self._prepare_headers(kwargs.pop('headers', None))
        kwargs['headers'] = headers
        
        last_exception = None
        
        for attempt in range(self.retries + 1):
            try:
                # Get service URL (may change between retries for load balancing)
                base_url = await self._get_service_url()
                url = urljoin(base_url, path.lstrip('/'))
                
                self.logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = await self._client.request(method, url, **kwargs)
                
                # Log response
                self.logger.debug(f"Response: {response.status_code} from {url}")
                
                return response
                
            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request timeout after {self.timeout}s", details={"url": url})
                self.logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                
            except httpx.RequestError as e:
                last_exception = CommunicationError(
                    f"Request failed: {e}",
                    service_name=self.service_name,
                    details={"url": url, "error": str(e)}
                )
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
            except Exception as e:
                last_exception = CommunicationError(
                    f"Unexpected error: {e}",
                    service_name=self.service_name,
                    details={"error": str(e)}
                )
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.retries:
                await asyncio.sleep(self.retry_delay)
        
        # All retries failed
        raise last_exception
    
    async def get(self, path: str, **kwargs) -> Response:
        """Make GET request."""
        return await self._make_request("GET", path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> Response:
        """Make POST request."""
        return await self._make_request("POST", path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> Response:
        """Make PUT request."""
        return await self._make_request("PUT", path, **kwargs)
    
    async def patch(self, path: str, **kwargs) -> Response:
        """Make PATCH request."""
        return await self._make_request("PATCH", path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> Response:
        """Make DELETE request."""
        return await self._make_request("DELETE", path, **kwargs)
    
    async def get_json(self, path: str, **kwargs) -> Dict[str, Any]:
        """
        Make GET request and return JSON response.
        
        Args:
            path: Request path
            **kwargs: Additional request arguments
            
        Returns:
            JSON response data
            
        Raises:
            CommunicationError: If request fails or response is not JSON
        """
        response = await self.get(path, **kwargs)
        
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CommunicationError(
                f"HTTP error {e.response.status_code}",
                service_name=self.service_name,
                status_code=e.response.status_code,
                details={"response": e.response.text}
            )
        except ValueError as e:
            raise CommunicationError(
                f"Invalid JSON response: {e}",
                service_name=self.service_name,
                details={"response": response.text}
            )
    
    async def post_json(self, path: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make POST request with JSON data and return JSON response.
        
        Args:
            path: Request path
            data: JSON data to send
            **kwargs: Additional request arguments
            
        Returns:
            JSON response data
        """
        response = await self.post(path, json=data, **kwargs)
        
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise CommunicationError(
                f"HTTP error {e.response.status_code}",
                service_name=self.service_name,
                status_code=e.response.status_code,
                details={"response": e.response.text}
            )
        except ValueError as e:
            raise CommunicationError(
                f"Invalid JSON response: {e}",
                service_name=self.service_name,
                details={"response": response.text}
            )
    
    async def health_check(self) -> bool:
        """
        Check if the service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.get("/health")
            return response.status_code == 200
        except Exception:
            return False

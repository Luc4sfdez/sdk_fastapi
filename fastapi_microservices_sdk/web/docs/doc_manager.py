"""
API Documentation Manager.
Provides service API discovery, OpenAPI/Swagger documentation parsing,
interactive testing integration, and documentation caching.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import yaml
import asyncio
import aiohttp
from urllib.parse import urljoin
import logging

from ..core.base_manager import BaseManager

logger = logging.getLogger(__name__)


@dataclass
class ServiceAPI:
    """Service API information."""
    service_name: str
    base_url: str
    openapi_url: str
    version: str
    title: str
    description: str
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    schemas: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    status: str = "unknown"  # active, inactive, error


@dataclass
class APIEndpoint:
    """API endpoint information."""
    service_name: str
    path: str
    method: str
    summary: str
    description: str
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    deprecated: bool = False


class APIDocumentationManager(BaseManager):
    """
    API Documentation Manager.
    
    Features:
    - Service API discovery and registration
    - OpenAPI/Swagger documentation parsing and display
    - Interactive API testing interface integration
    - API documentation caching and update mechanisms
    - Multi-service API aggregation
    - Documentation versioning and history
    """

    def __init__(self, name: str = "api_docs", config: Optional[Dict[str, Any]] = None):
        """Initialize the API documentation manager."""
        super().__init__(name, config)
        
        # Configuration
        self._cache_ttl = timedelta(minutes=config.get("cache_ttl_minutes", 30)) if config else timedelta(minutes=30)
        self._auto_discovery = config.get("auto_discovery", True) if config else True
        self._discovery_interval = config.get("discovery_interval_seconds", 300) if config else 300
        self._max_retries = config.get("max_retries", 3) if config else 3
        
        # Service registry
        self._services: Dict[str, ServiceAPI] = {}
        self._endpoints: Dict[str, List[APIEndpoint]] = {}
        
        # Cache management
        self._documentation_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Discovery task
        self._discovery_task: Optional[asyncio.Task] = None
        
        # HTTP session for API calls
        self._session: Optional[aiohttp.ClientSession] = None

    async def _initialize_impl(self) -> None:
        """Initialize the documentation manager."""
        try:
            # Create HTTP session
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            # Start auto-discovery if enabled
            if self._auto_discovery:
                self._discovery_task = asyncio.create_task(self._discovery_loop())
            
            self.logger.info("API documentation manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize API documentation manager: {e}")
            raise

    async def _shutdown_impl(self) -> None:
        """Shutdown the documentation manager."""
        try:
            # Cancel discovery task
            if self._discovery_task:
                self._discovery_task.cancel()
                try:
                    await self._discovery_task
                except asyncio.CancelledError:
                    pass
            
            # Close HTTP session
            if self._session:
                await self._session.close()
            
            self.logger.info("API documentation manager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during API documentation manager shutdown: {e}")

    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            # Check if session is available
            if not self._session or self._session.closed:
                return False
            
            # Check if we have any registered services
            return len(self._services) > 0
            
        except Exception:
            return False

    # Service Registration Methods

    async def register_service(
        self, 
        service_name: str, 
        base_url: str, 
        openapi_path: str = "/openapi.json"
    ) -> bool:
        """
        Register a service for API documentation.
        
        Args:
            service_name: Name of the service
            base_url: Base URL of the service
            openapi_path: Path to OpenAPI specification
            
        Returns:
            True if registration successful
        """
        return await self._safe_execute(
            "register_service",
            self._register_service_impl,
            service_name,
            base_url,
            openapi_path
        )

    async def _register_service_impl(
        self, 
        service_name: str, 
        base_url: str, 
        openapi_path: str
    ) -> bool:
        """Implementation for service registration."""
        try:
            openapi_url = urljoin(base_url.rstrip('/') + '/', openapi_path.lstrip('/'))
            
            # Try to fetch OpenAPI spec
            openapi_spec = await self._fetch_openapi_spec(openapi_url)
            if not openapi_spec:
                self.logger.warning(f"Could not fetch OpenAPI spec for {service_name}")
                return False
            
            # Create service API object
            service_api = ServiceAPI(
                service_name=service_name,
                base_url=base_url,
                openapi_url=openapi_url,
                version=openapi_spec.get("info", {}).get("version", "1.0.0"),
                title=openapi_spec.get("info", {}).get("title", service_name),
                description=openapi_spec.get("info", {}).get("description", ""),
                status="active"
            )
            
            # Parse endpoints
            endpoints = await self._parse_openapi_endpoints(service_name, openapi_spec)
            service_api.endpoints = [
                {
                    "path": ep.path,
                    "method": ep.method,
                    "summary": ep.summary,
                    "description": ep.description,
                    "tags": ep.tags
                }
                for ep in endpoints
            ]
            
            # Store schemas
            service_api.schemas = openapi_spec.get("components", {}).get("schemas", {})
            
            # Register service
            self._services[service_name] = service_api
            self._endpoints[service_name] = endpoints
            
            # Cache the documentation
            self._documentation_cache[service_name] = openapi_spec
            self._cache_timestamps[service_name] = datetime.utcnow()
            
            self.logger.info(f"Successfully registered service: {service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service_name}: {e}")
            return False

    async def unregister_service(self, service_name: str) -> bool:
        """
        Unregister a service.
        
        Args:
            service_name: Name of the service to unregister
            
        Returns:
            True if unregistration successful
        """
        return await self._safe_execute(
            "unregister_service",
            self._unregister_service_impl,
            service_name
        )

    async def _unregister_service_impl(self, service_name: str) -> bool:
        """Implementation for service unregistration."""
        try:
            # Remove from all registries
            self._services.pop(service_name, None)
            self._endpoints.pop(service_name, None)
            self._documentation_cache.pop(service_name, None)
            self._cache_timestamps.pop(service_name, None)
            
            self.logger.info(f"Successfully unregistered service: {service_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister service {service_name}: {e}")
            return False

    # Documentation Retrieval Methods

    async def get_service_documentation(self, service_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get documentation for a specific service.
        
        Args:
            service_name: Name of the service
            force_refresh: Force refresh from source
            
        Returns:
            OpenAPI specification or None
        """
        return await self._safe_execute(
            "get_service_documentation",
            self._get_service_documentation_impl,
            service_name,
            force_refresh
        )

    async def _get_service_documentation_impl(
        self, 
        service_name: str, 
        force_refresh: bool
    ) -> Optional[Dict[str, Any]]:
        """Implementation for getting service documentation."""
        try:
            # Check if service is registered
            if service_name not in self._services:
                self.logger.warning(f"Service {service_name} not registered")
                return None
            
            # Check cache validity
            if not force_refresh and self._is_cache_valid(service_name):
                return self._documentation_cache.get(service_name)
            
            # Refresh documentation
            service = self._services[service_name]
            openapi_spec = await self._fetch_openapi_spec(service.openapi_url)
            
            if openapi_spec:
                # Update cache
                self._documentation_cache[service_name] = openapi_spec
                self._cache_timestamps[service_name] = datetime.utcnow()
                
                # Update service info
                service.last_updated = datetime.utcnow()
                service.status = "active"
                
                return openapi_spec
            else:
                # Mark service as having issues
                service.status = "error"
                return self._documentation_cache.get(service_name)
                
        except Exception as e:
            self.logger.error(f"Failed to get documentation for {service_name}: {e}")
            return None

    async def get_all_services(self) -> List[ServiceAPI]:
        """
        Get all registered services.
        
        Returns:
            List of service API objects
        """
        return list(self._services.values())

    async def get_service_endpoints(self, service_name: str) -> List[APIEndpoint]:
        """
        Get endpoints for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of API endpoints
        """
        return self._endpoints.get(service_name, [])

    async def get_all_endpoints(self) -> Dict[str, List[APIEndpoint]]:
        """
        Get all endpoints from all services.
        
        Returns:
            Dictionary mapping service names to endpoint lists
        """
        return self._endpoints.copy()

    # Search and Discovery Methods

    async def search_endpoints(
        self, 
        query: str, 
        service_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[APIEndpoint]:
        """
        Search for endpoints matching criteria.
        
        Args:
            query: Search query (matches path, summary, description)
            service_name: Filter by service name
            tags: Filter by tags
            
        Returns:
            List of matching endpoints
        """
        return await self._safe_execute(
            "search_endpoints",
            self._search_endpoints_impl,
            query,
            service_name,
            tags
        )

    async def _search_endpoints_impl(
        self, 
        query: str, 
        service_name: Optional[str],
        tags: Optional[List[str]]
    ) -> List[APIEndpoint]:
        """Implementation for endpoint search."""
        try:
            results = []
            query_lower = query.lower()
            
            # Determine which services to search
            services_to_search = [service_name] if service_name else list(self._endpoints.keys())
            
            for svc_name in services_to_search:
                if svc_name not in self._endpoints:
                    continue
                
                for endpoint in self._endpoints[svc_name]:
                    # Text search
                    if query_lower in endpoint.path.lower() or \
                       query_lower in endpoint.summary.lower() or \
                       query_lower in endpoint.description.lower():
                        
                        # Tag filter
                        if tags and not any(tag in endpoint.tags for tag in tags):
                            continue
                        
                        results.append(endpoint)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search endpoints: {e}")
            return []

    async def discover_services(self, base_urls: List[str]) -> List[str]:
        """
        Discover services from a list of base URLs.
        
        Args:
            base_urls: List of base URLs to check
            
        Returns:
            List of successfully discovered service names
        """
        return await self._safe_execute(
            "discover_services",
            self._discover_services_impl,
            base_urls
        )

    async def _discover_services_impl(self, base_urls: List[str]) -> List[str]:
        """Implementation for service discovery."""
        discovered = []
        
        for base_url in base_urls:
            try:
                # Try common OpenAPI paths
                openapi_paths = ["/openapi.json", "/docs/openapi.json", "/api/openapi.json"]
                
                for openapi_path in openapi_paths:
                    openapi_url = urljoin(base_url.rstrip('/') + '/', openapi_path.lstrip('/'))
                    
                    # Try to fetch OpenAPI spec
                    spec = await self._fetch_openapi_spec(openapi_url)
                    if spec:
                        # Extract service name from title or URL
                        service_name = spec.get("info", {}).get("title", "").lower().replace(" ", "_")
                        if not service_name:
                            service_name = base_url.split("//")[-1].split("/")[0].replace(".", "_")
                        
                        # Register the service
                        if await self._register_service_impl(service_name, base_url, openapi_path):
                            discovered.append(service_name)
                        break
                        
            except Exception as e:
                self.logger.debug(f"Failed to discover service at {base_url}: {e}")
                continue
        
        return discovered

    # Cache Management Methods

    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if cached documentation is still valid."""
        if service_name not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[service_name]
        return datetime.utcnow() - cache_time < self._cache_ttl

    async def refresh_all_documentation(self) -> Dict[str, bool]:
        """
        Refresh documentation for all registered services.
        
        Returns:
            Dictionary mapping service names to refresh success status
        """
        return await self._safe_execute(
            "refresh_all_documentation",
            self._refresh_all_documentation_impl
        )

    async def _refresh_all_documentation_impl(self) -> Dict[str, bool]:
        """Implementation for refreshing all documentation."""
        results = {}
        
        for service_name in self._services.keys():
            try:
                doc = await self._get_service_documentation_impl(service_name, force_refresh=True)
                results[service_name] = doc is not None
            except Exception as e:
                self.logger.error(f"Failed to refresh documentation for {service_name}: {e}")
                results[service_name] = False
        
        return results

    async def clear_cache(self, service_name: Optional[str] = None) -> None:
        """
        Clear documentation cache.
        
        Args:
            service_name: Specific service to clear, or None for all
        """
        if service_name:
            self._documentation_cache.pop(service_name, None)
            self._cache_timestamps.pop(service_name, None)
        else:
            self._documentation_cache.clear()
            self._cache_timestamps.clear()

    # Utility Methods

    async def _fetch_openapi_spec(self, openapi_url: str) -> Optional[Dict[str, Any]]:
        """Fetch OpenAPI specification from URL."""
        if not self._session:
            return None
        
        for attempt in range(self._max_retries):
            try:
                async with self._session.get(openapi_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'application/json' in content_type:
                            return await response.json()
                        elif 'yaml' in content_type or 'yml' in content_type:
                            text = await response.text()
                            return yaml.safe_load(text)
                        else:
                            # Try to parse as JSON first, then YAML
                            text = await response.text()
                            try:
                                return json.loads(text)
                            except json.JSONDecodeError:
                                return yaml.safe_load(text)
                    else:
                        self.logger.debug(f"HTTP {response.status} when fetching {openapi_url}")
                        
            except Exception as e:
                self.logger.debug(f"Attempt {attempt + 1} failed for {openapi_url}: {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    async def _parse_openapi_endpoints(self, service_name: str, openapi_spec: Dict[str, Any]) -> List[APIEndpoint]:
        """Parse endpoints from OpenAPI specification."""
        endpoints = []
        paths = openapi_spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    endpoint = APIEndpoint(
                        service_name=service_name,
                        path=path,
                        method=method.upper(),
                        summary=operation.get("summary", ""),
                        description=operation.get("description", ""),
                        tags=operation.get("tags", []),
                        parameters=operation.get("parameters", []),
                        request_body=operation.get("requestBody"),
                        responses=operation.get("responses", {}),
                        deprecated=operation.get("deprecated", False)
                    )
                    endpoints.append(endpoint)
        
        return endpoints

    async def _discovery_loop(self) -> None:
        """Background task for automatic service discovery."""
        while True:
            try:
                await asyncio.sleep(self._discovery_interval)
                
                # Refresh documentation for all registered services
                await self._refresh_all_documentation_impl()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in discovery loop: {e}")

    # Statistics and Analytics Methods

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get API documentation statistics.
        
        Returns:
            Statistics dictionary
        """
        return await self._safe_execute(
            "get_statistics",
            self._get_statistics_impl
        )

    async def _get_statistics_impl(self) -> Dict[str, Any]:
        """Implementation for getting statistics."""
        try:
            total_services = len(self._services)
            active_services = sum(1 for s in self._services.values() if s.status == "active")
            total_endpoints = sum(len(endpoints) for endpoints in self._endpoints.values())
            
            # Count endpoints by method
            method_counts = {}
            for endpoints in self._endpoints.values():
                for endpoint in endpoints:
                    method = endpoint.method
                    method_counts[method] = method_counts.get(method, 0) + 1
            
            # Count endpoints by tag
            tag_counts = {}
            for endpoints in self._endpoints.values():
                for endpoint in endpoints:
                    for tag in endpoint.tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            return {
                "total_services": total_services,
                "active_services": active_services,
                "inactive_services": total_services - active_services,
                "total_endpoints": total_endpoints,
                "endpoints_by_method": method_counts,
                "endpoints_by_tag": tag_counts,
                "cache_hit_rate": self._calculate_cache_hit_rate(),
                "last_discovery": max(
                    (s.last_updated for s in self._services.values()),
                    default=datetime.utcnow()
                ).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if not self._cache_timestamps:
            return 0.0
        
        valid_caches = sum(1 for service in self._cache_timestamps.keys() if self._is_cache_valid(service))
        return valid_caches / len(self._cache_timestamps) if self._cache_timestamps else 0.0
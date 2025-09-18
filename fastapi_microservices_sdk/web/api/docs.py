"""
API Documentation REST Endpoints.
Provides REST API for documentation retrieval, testing, and management.
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging

from ..core.dependency_container import DependencyContainer
from ..docs.doc_manager import APIDocumentationManager
from ..docs.doc_viewer import APIDocumentationViewer
from ..docs.api_tester import APITester

logger = logging.getLogger(__name__)

# Pydantic models for request/response
class ServiceRegistration(BaseModel):
    service_name: str
    base_url: str
    openapi_path: str = "/openapi.json"

class TestRequest(BaseModel):
    service_name: str
    endpoint_path: str
    method: str
    parameters: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    body: Optional[Any] = None
    timeout: int = 30

class SavedRequest(BaseModel):
    name: str
    service_name: str
    endpoint_path: str
    method: str
    parameters: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    body: Optional[Any] = None
    tags: List[str] = []
    notes: str = ""

def create_docs_router(container: DependencyContainer) -> APIRouter:
    """Create API documentation router with all endpoints."""
    router = APIRouter(prefix="/api/docs", tags=["API Documentation"])
    
    # Get managers from container
    def get_doc_manager() -> APIDocumentationManager:
        return container.get_manager("api_docs")
    
    def get_doc_viewer() -> APIDocumentationViewer:
        return container.get_manager("api_doc_viewer")
    
    def get_api_tester() -> APITester:
        return container.get_manager("api_tester")

    # Service Management Endpoints
    
    @router.get("/services", response_model=List[Dict[str, Any]])
    async def get_services(doc_manager: APIDocumentationManager = Depends(get_doc_manager)):
        """Get all registered services."""
        try:
            services = await doc_manager.get_all_services()
            return [
                {
                    "service_name": service.service_name,
                    "title": service.title,
                    "version": service.version,
                    "description": service.description,
                    "base_url": service.base_url,
                    "status": service.status,
                    "last_updated": service.last_updated.isoformat(),
                    "endpoint_count": len(service.endpoints)
                }
                for service in services
            ]
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve services")

    @router.post("/services/register")
    async def register_service(
        registration: ServiceRegistration,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Register a new service for documentation."""
        try:
            success = await doc_manager.register_service(
                registration.service_name,
                registration.base_url,
                registration.openapi_path
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to register service")
            
            return {"message": "Service registered successfully", "service_name": registration.service_name}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to register service: {e}")
            raise HTTPException(status_code=500, detail="Failed to register service")

    @router.delete("/services/{service_name}")
    async def unregister_service(
        service_name: str,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Unregister a service."""
        try:
            success = await doc_manager.unregister_service(service_name)
            
            if not success:
                raise HTTPException(status_code=404, detail="Service not found")
            
            return {"message": "Service unregistered successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unregister service: {e}")
            raise HTTPException(status_code=500, detail="Failed to unregister service")

    @router.post("/services/discover")
    async def discover_services(
        base_urls: List[str],
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Discover services from base URLs."""
        try:
            discovered = await doc_manager.discover_services(base_urls)
            return {
                "message": f"Discovered {len(discovered)} services",
                "discovered_services": discovered
            }
            
        except Exception as e:
            logger.error(f"Failed to discover services: {e}")
            raise HTTPException(status_code=500, detail="Failed to discover services")

    # Documentation Retrieval Endpoints

    @router.get("/services/{service_name}/documentation", response_class=HTMLResponse)
    async def get_service_documentation(
        service_name: str,
        format: str = "html",
        force_refresh: bool = False,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager),
        doc_viewer: APIDocumentationViewer = Depends(get_doc_viewer)
    ):
        """Get documentation for a specific service."""
        try:
            if format == "json":
                doc = await doc_manager.get_service_documentation(service_name, force_refresh)
                if not doc:
                    raise HTTPException(status_code=404, detail="Service documentation not found")
                return JSONResponse(content=doc)
            
            elif format == "html":
                html_doc = await doc_viewer.render_service_documentation(service_name, "html")
                if not html_doc:
                    raise HTTPException(status_code=404, detail="Service documentation not found")
                return HTMLResponse(content=html_doc)
            
            else:
                raise HTTPException(status_code=400, detail="Unsupported format. Use 'html' or 'json'")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get documentation for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve documentation")

    @router.get("/services/{service_name}/endpoints")
    async def get_service_endpoints(
        service_name: str,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Get endpoints for a specific service."""
        try:
            endpoints = await doc_manager.get_service_endpoints(service_name)
            return [
                {
                    "service_name": ep.service_name,
                    "path": ep.path,
                    "method": ep.method,
                    "summary": ep.summary,
                    "description": ep.description,
                    "tags": ep.tags,
                    "parameters": ep.parameters,
                    "request_body": ep.request_body,
                    "responses": ep.responses,
                    "deprecated": ep.deprecated
                }
                for ep in endpoints
            ]
            
        except Exception as e:
            logger.error(f"Failed to get endpoints for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve endpoints")

    @router.get("/services/{service_name}/swagger", response_class=HTMLResponse)
    async def get_swagger_ui(
        service_name: str,
        doc_viewer: APIDocumentationViewer = Depends(get_doc_viewer)
    ):
        """Get Swagger UI for a specific service."""
        try:
            swagger_html = await doc_viewer.generate_swagger_ui(service_name)
            if not swagger_html:
                raise HTTPException(status_code=404, detail="Swagger UI not available for service")
            
            return HTMLResponse(content=swagger_html)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get Swagger UI for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate Swagger UI")

    @router.get("/services/{service_name}/export")
    async def export_service_documentation(
        service_name: str,
        format: str = "json",
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Export service documentation."""
        try:
            doc = await doc_manager.get_service_documentation(service_name)
            if not doc:
                raise HTTPException(status_code=404, detail="Service documentation not found")
            
            if format == "json":
                return JSONResponse(
                    content=doc,
                    headers={"Content-Disposition": f"attachment; filename={service_name}-docs.json"}
                )
            else:
                raise HTTPException(status_code=400, detail="Unsupported export format")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to export documentation for {service_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to export documentation")

    # Search and Navigation Endpoints

    @router.get("/search/endpoints")
    async def search_endpoints(
        query: str,
        service_name: Optional[str] = None,
        tags: Optional[str] = None,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Search for endpoints matching criteria."""
        try:
            tag_list = tags.split(",") if tags else None
            endpoints = await doc_manager.search_endpoints(query, service_name, tag_list)
            
            return [
                {
                    "service_name": ep.service_name,
                    "path": ep.path,
                    "method": ep.method,
                    "summary": ep.summary,
                    "description": ep.description,
                    "tags": ep.tags
                }
                for ep in endpoints
            ]
            
        except Exception as e:
            logger.error(f"Failed to search endpoints: {e}")
            raise HTTPException(status_code=500, detail="Failed to search endpoints")

    @router.get("/endpoints")
    async def get_all_endpoints(
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Get all endpoints from all services."""
        try:
            all_endpoints = await doc_manager.get_all_endpoints()
            
            result = {}
            for service_name, endpoints in all_endpoints.items():
                result[service_name] = [
                    {
                        "path": ep.path,
                        "method": ep.method,
                        "summary": ep.summary,
                        "tags": ep.tags
                    }
                    for ep in endpoints
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all endpoints: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve endpoints")

    # API Testing Endpoints

    @router.post("/test")
    async def test_endpoint(
        test_request: TestRequest,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Test an API endpoint."""
        try:
            response = await api_tester.test_endpoint(
                test_request.service_name,
                test_request.endpoint_path,
                test_request.method,
                test_request.parameters,
                test_request.headers,
                test_request.body,
                test_request.timeout
            )
            
            return {
                "request_id": response.request_id,
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.body,
                "response_time": response.response_time,
                "timestamp": response.timestamp.isoformat(),
                "error": response.error
            }
            
        except Exception as e:
            logger.error(f"Failed to test endpoint: {e}")
            raise HTTPException(status_code=500, detail="Failed to test endpoint")

    @router.post("/test/batch")
    async def test_multiple_endpoints(
        test_requests: List[TestRequest],
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Test multiple API endpoints in batch."""
        try:
            test_configs = [
                {
                    "service_name": req.service_name,
                    "endpoint_path": req.endpoint_path,
                    "method": req.method,
                    "parameters": req.parameters,
                    "headers": req.headers,
                    "body": req.body,
                    "timeout": req.timeout
                }
                for req in test_requests
            ]
            
            responses = await api_tester.test_multiple_endpoints(test_configs)
            
            return [
                {
                    "request_id": response.request_id,
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "body": response.body,
                    "response_time": response.response_time,
                    "timestamp": response.timestamp.isoformat(),
                    "error": response.error
                }
                for response in responses
            ]
            
        except Exception as e:
            logger.error(f"Failed to test multiple endpoints: {e}")
            raise HTTPException(status_code=500, detail="Failed to test endpoints")

    # Request Management Endpoints

    @router.post("/requests")
    async def save_request(
        saved_request: SavedRequest,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Save a request configuration."""
        try:
            success = await api_tester.save_request(
                saved_request.name,
                saved_request.service_name,
                saved_request.endpoint_path,
                saved_request.method,
                saved_request.parameters,
                saved_request.headers,
                saved_request.body
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to save request")
            
            return {"message": "Request saved successfully", "name": saved_request.name}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save request: {e}")
            raise HTTPException(status_code=500, detail="Failed to save request")

    @router.get("/requests")
    async def get_saved_requests(
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Get all saved request configurations."""
        try:
            saved_requests = await api_tester.get_saved_requests()
            
            result = {}
            for name, request in saved_requests.items():
                result[name] = {
                    "service_name": request.endpoint.service_name,
                    "endpoint_path": request.endpoint.path,
                    "method": request.endpoint.method,
                    "parameters": request.parameters,
                    "headers": request.headers,
                    "body": request.body
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get saved requests: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve saved requests")

    @router.get("/requests/{name}")
    async def get_saved_request(
        name: str,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Get a specific saved request configuration."""
        try:
            request = await api_tester.load_saved_request(name)
            if not request:
                raise HTTPException(status_code=404, detail="Saved request not found")
            
            return {
                "service_name": request.endpoint.service_name,
                "endpoint_path": request.endpoint.path,
                "method": request.endpoint.method,
                "parameters": request.parameters,
                "headers": request.headers,
                "body": request.body
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get saved request: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve saved request")

    @router.delete("/requests/{name}")
    async def delete_saved_request(
        name: str,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Delete a saved request configuration."""
        try:
            success = await api_tester.delete_saved_request(name)
            if not success:
                raise HTTPException(status_code=404, detail="Saved request not found")
            
            return {"message": "Saved request deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete saved request: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete saved request")

    @router.delete("/requests")
    async def clear_saved_requests(
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Clear all saved request configurations."""
        try:
            saved_requests = await api_tester.get_saved_requests()
            for name in list(saved_requests.keys()):
                await api_tester.delete_saved_request(name)
            
            return {"message": "All saved requests cleared successfully"}
            
        except Exception as e:
            logger.error(f"Failed to clear saved requests: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear saved requests")

    # Test History Endpoints

    @router.get("/history")
    async def get_test_history(
        limit: Optional[int] = 50,
        service_name: Optional[str] = None,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Get test history."""
        try:
            history = await api_tester.get_test_history(limit, service_name)
            
            return [
                {
                    "test_id": entry.test_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "request": {
                        "endpoint": {
                            "service_name": entry.request.endpoint.service_name,
                            "path": entry.request.endpoint.path,
                            "method": entry.request.endpoint.method,
                            "summary": entry.request.endpoint.summary
                        },
                        "parameters": entry.request.parameters,
                        "headers": entry.request.headers,
                        "body": entry.request.body
                    },
                    "response": {
                        "status_code": entry.response.status_code,
                        "response_time": entry.response.response_time,
                        "error": entry.response.error
                    },
                    "tags": entry.tags,
                    "notes": entry.notes
                }
                for entry in history
            ]
            
        except Exception as e:
            logger.error(f"Failed to get test history: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve test history")

    @router.delete("/history")
    async def clear_test_history(
        service_name: Optional[str] = None,
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Clear test history."""
        try:
            success = await api_tester.clear_test_history(service_name)
            if not success:
                raise HTTPException(status_code=400, detail="Failed to clear test history")
            
            message = f"Test history cleared for {service_name}" if service_name else "All test history cleared"
            return {"message": message}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to clear test history: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear test history")

    # Statistics and Analytics Endpoints

    @router.get("/statistics")
    async def get_documentation_statistics(
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Get API documentation statistics."""
        try:
            stats = await doc_manager.get_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get documentation statistics: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

    @router.get("/test-statistics")
    async def get_testing_statistics(
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Get API testing statistics."""
        try:
            stats = await api_tester.get_testing_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get testing statistics: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve testing statistics")

    # Management Endpoints

    @router.post("/refresh")
    async def refresh_documentation(
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Refresh documentation for all services."""
        try:
            results = await doc_manager.refresh_all_documentation()
            
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            return {
                "message": f"Refreshed {successful}/{total} services successfully",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh documentation: {e}")
            raise HTTPException(status_code=500, detail="Failed to refresh documentation")

    @router.post("/cache/clear")
    async def clear_documentation_cache(
        service_name: Optional[str] = None,
        doc_manager: APIDocumentationManager = Depends(get_doc_manager)
    ):
        """Clear documentation cache."""
        try:
            await doc_manager.clear_cache(service_name)
            
            message = f"Cache cleared for {service_name}" if service_name else "All cache cleared"
            return {"message": message}
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise HTTPException(status_code=500, detail="Failed to clear cache")

    # Validation Endpoints

    @router.post("/validate/parameters")
    async def validate_request_parameters(
        service_name: str,
        endpoint_path: str,
        method: str,
        parameters: Dict[str, Any],
        doc_manager: APIDocumentationManager = Depends(get_doc_manager),
        api_tester: APITester = Depends(get_api_tester)
    ):
        """Validate request parameters against endpoint specification."""
        try:
            # Get endpoint
            endpoints = await doc_manager.get_service_endpoints(service_name)
            endpoint = None
            
            for ep in endpoints:
                if ep.path == endpoint_path and ep.method.upper() == method.upper():
                    endpoint = ep
                    break
            
            if not endpoint:
                raise HTTPException(status_code=404, detail="Endpoint not found")
            
            # Validate parameters
            errors = await api_tester.validate_request_parameters(endpoint, parameters)
            
            return {
                "valid": len(errors) == 0,
                "errors": errors
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to validate parameters: {e}")
            raise HTTPException(status_code=500, detail="Failed to validate parameters")

    return router

# Default router for backward compatibility
def get_default_router() -> APIRouter:
    """Get default router for backward compatibility."""
    from ..core.dependency_container import DependencyContainer
    container = DependencyContainer()
    return create_docs_router(container)

# Create default router instance
router = APIRouter(prefix="/api/docs", tags=["API Documentation"])

# Add a simple health check endpoint for testing
@router.get("/health")
async def docs_health():
    """Health check endpoint for docs API."""
    return {"status": "healthy", "service": "docs"}
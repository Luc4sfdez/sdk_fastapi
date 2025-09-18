"""
Gateway routing and proxy functionality.
"""

import httpx
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import Response
from typing import Dict, Any
import logging

from config import settings

gateway_router = APIRouter()
logger = logging.getLogger(__name__)


class GatewayService:
    """Service for handling gateway operations."""
    
    @staticmethod
    async def proxy_request(service_name: str, path: str, request: Request) -> Response:
        """Proxy request to target microservice."""
        
        # Get service URL
        service_url = settings.SERVICES.get(service_name)
        if not service_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service_name}' not found"
            )
        
        # Build target URL
        target_url = f"{service_url}{path}"
        
        # Get request data
        method = request.method
        headers = dict(request.headers)
        
        # Remove host header to avoid conflicts
        headers.pop("host", None)
        
        try:
            # Get request body
            body = await request.body()
            
            # Make request to target service
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params
                )
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout calling service {service_name} at {target_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {service_name} timeout"
            )
        except httpx.ConnectError:
            logger.error(f"Connection error to service {service_name} at {target_url}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} unavailable"
            )
        except Exception as e:
            logger.error(f"Error proxying to {service_name}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal gateway error"
            )


@gateway_router.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_service(service_name: str, path: str, request: Request):
    """Proxy requests to microservices."""
    
    logger.info(f"Proxying {request.method} /{service_name}/{path}")
    
    # Add leading slash to path if not present
    if not path.startswith("/"):
        path = "/" + path
    
    return await GatewayService.proxy_request(service_name, path, request)


@gateway_router.get("/services")
async def list_services():
    """List available services."""
    
    services_status = {}
    
    async with httpx.AsyncClient(timeout=5) as client:
        for service_name, service_url in settings.SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health/")
                services_status[service_name] = {
                    "url": service_url,
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                services_status[service_name] = {
                    "url": service_url,
                    "status": "unavailable",
                    "error": str(e)
                }
    
    return {
        "gateway": "test-api-gateway",
        "services": services_status,
        "total_services": len(settings.SERVICES)
    }


@gateway_router.get("/routes")
async def list_routes():
    """List available routes."""
    
    routes = []
    for service_name, service_url in settings.SERVICES.items():
        routes.append({
            "service": service_name,
            "pattern": f"/api/{service_name}/*",
            "target": service_url,
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"]
        })
    
    return {
        "gateway_routes": routes,
        "usage": "Use /api/{service_name}/{endpoint} to access services"
    }
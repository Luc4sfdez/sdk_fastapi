"""
Health check endpoints for API Gateway.
"""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

from config import settings

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str = "1.0.0"
    gateway: str = "test-api-gateway"
    services: Dict[str, Any] = {}


@health_router.get("/", response_model=HealthResponse)
async def health_check():
    """Gateway health check with services status."""
    
    services_health = {}
    
    # Check each service health
    async with httpx.AsyncClient(timeout=5) as client:
        for service_name, service_url in settings.SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health/")
                services_health[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": service_url,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                services_health[service_name] = {
                    "status": "unavailable",
                    "url": service_url,
                    "error": str(e)
                }
    
    # Determine overall status
    all_healthy = all(
        service["status"] == "healthy" 
        for service in services_health.values()
    )
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=time.time(),
        services=services_health
    )


@health_router.get("/ready")
async def readiness_check():
    """Gateway readiness check."""
    
    return {
        "ready": True,
        "timestamp": time.time(),
        "gateway": "test-api-gateway",
        "services_configured": len(settings.SERVICES),
        "rate_limiting": True,
        "logging": True
    }


@health_router.get("/live")
async def liveness_check():
    """Gateway liveness check."""
    
    return {
        "status": "alive",
        "timestamp": time.time(),
        "gateway": "test-api-gateway"
    }
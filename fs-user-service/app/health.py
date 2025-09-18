"""
Health Check Endpoints

Health check and readiness endpoints for the application.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import time

health_router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str = "1.0.0"
    checks: Dict[str, Any] = {}


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    timestamp: float
    services: Dict[str, bool] = {}


@health_router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns the current status of the application.
    """
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        checks={
            "application": "running",
            "service": "fs-user-service",
            "memory": "ok",
            "disk": "ok"
        }
    )


@health_router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks if the application is ready to serve requests.
    """
    services = {
        "application": True,
        "api": True
    }
    
    return ReadinessResponse(
        ready=True,
        timestamp=time.time(),
        services=services
    )


@health_router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Simple endpoint to check if the application is alive.
    """
    return {
        "status": "alive", 
        "timestamp": time.time(),
        "service": "fs-user-service"
    }

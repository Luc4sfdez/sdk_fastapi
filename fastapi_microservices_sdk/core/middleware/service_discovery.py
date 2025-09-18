# fastapi-microservices-sdk/fastapi_microservices_sdk/core/middleware/service_discovery.py
"""
Service Discovery middleware for FastAPI Microservices SDK.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class ServiceDiscoveryMiddleware(BaseHTTPMiddleware):
    """Middleware for service discovery integration."""
    
    def __init__(self, app, registry=None):
        super().__init__(app)
        self.registry = registry
    
    async def dispatch(self, request: Request, call_next):
        # Add service discovery logic here
        response = await call_next(request)
        return response
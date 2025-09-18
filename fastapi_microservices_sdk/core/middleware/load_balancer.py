# fastapi-microservices-sdk/fastapi_microservices_sdk/core/middleware/load_balancer.py
"""
Load Balancer middleware for FastAPI Microservices SDK.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoadBalancerMiddleware(BaseHTTPMiddleware):
    """Middleware for load balancing."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Add load balancing logic here
        response = await call_next(request)
        return response
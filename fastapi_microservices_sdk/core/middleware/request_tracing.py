# fastapi-microservices-sdk/fastapi_microservices_sdk/core/middleware/request_tracing.py
"""
Request Tracing middleware for FastAPI Microservices SDK.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Add request tracing logic here
        response = await call_next(request)
        return response
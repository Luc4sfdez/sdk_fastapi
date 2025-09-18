# fastapi-microservices-sdk/fastapi_microservices_sdk/core/middleware/circuit_breaker.py
"""
Circuit Breaker middleware for FastAPI Microservices SDK.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """Middleware for circuit breaker pattern."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Add circuit breaker logic here
        response = await call_next(request)
        return response
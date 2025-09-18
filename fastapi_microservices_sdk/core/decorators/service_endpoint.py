# fastapi-microservices-sdk/fastapi_microservices_sdk/core/decorators/service_endpoint.py
"""
Service endpoint decorator for FastAPI Microservices SDK.
"""

import functools
from typing import Callable, Any


def service_endpoint(
    path: str = None,
    methods: list = None,
    **kwargs
):
    """
    Decorator for service endpoints with additional microservices features.
    
    Args:
        path: Endpoint path
        methods: HTTP methods
        **kwargs: Additional FastAPI route parameters
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Add any microservices-specific logic here
            return await func(*args, **kwargs)
        
        # Store metadata for later use
        wrapper._service_endpoint = True
        wrapper._endpoint_path = path
        wrapper._endpoint_methods = methods or ["GET"]
        
        return wrapper
    
    return decorator
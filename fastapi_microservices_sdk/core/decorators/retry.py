# fastapi-microservices-sdk/fastapi_microservices_sdk/core/decorators/retry.py
"""
Retry decorator for FastAPI Microservices SDK.
"""

import asyncio
import functools
import logging
from typing import Callable, Type, Union, Tuple


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Retry decorator for functions and coroutines.
    
    Args:
        attempts: Number of retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier for delay
        exceptions: Exception types to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < attempts - 1:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"All {attempts} attempts failed. Last error: {e}")
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < attempts - 1:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"All {attempts} attempts failed. Last error: {e}")
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
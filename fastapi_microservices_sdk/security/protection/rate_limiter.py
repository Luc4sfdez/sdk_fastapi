"""
Rate limiting for FastAPI Microservices SDK.

This module provides rate limiting capabilities for microservices.
"""

import time
import asyncio
from typing import Dict, Optional, Callable, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from ...exceptions import SecurityError


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    burst_size: Optional[int] = None
    key_func: Optional[Callable[[Request], str]] = None


class RateLimitStore:
    """In-memory rate limit store."""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Dict[str, Any]:
        """Get rate limit data for key."""
        async with self._lock:
            return self._data.get(key, {})
    
    async def set(self, key: str, data: Dict[str, Any]) -> None:
        """Set rate limit data for key."""
        async with self._lock:
            self._data[key] = data
    
    async def increment(self, key: str, window: str) -> int:
        """Increment counter for key and window."""
        async with self._lock:
            if key not in self._data:
                self._data[key] = {}
            if window not in self._data[key]:
                self._data[key][window] = 0
            self._data[key][window] += 1
            return self._data[key][window]
    
    async def cleanup_expired(self, ttl_seconds: int = 3600) -> None:
        """Clean up expired entries."""
        current_time = time.time()
        async with self._lock:
            expired_keys = []
            for key, data in self._data.items():
                if isinstance(data, dict) and 'last_access' in data:
                    if current_time - data['last_access'] > ttl_seconds:
                        expired_keys.append(key)
            
            for key in expired_keys:
                del self._data[key]


class RateLimiter:
    """Rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig, store: Optional[RateLimitStore] = None):
        self.config = config
        self.store = store or RateLimitStore()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean up every 5 minutes
                    await self.store.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass  # Continue cleanup loop
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    def _get_client_key(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        if self.config.key_func:
            return self.config.key_func(request)
        
        # Default: use IP address
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip
        
        return f"client:{client_ip}"
    
    def _get_time_windows(self) -> Dict[str, int]:
        """Get current time windows."""
        now = time.time()
        return {
            "minute": int(now // 60),
            "hour": int(now // 3600),
            "day": int(now // 86400)
        }
    
    async def _check_fixed_window(self, key: str) -> bool:
        """Check rate limit using fixed window strategy."""
        windows = self._get_time_windows()
        
        # Check each time window
        limits = {
            "minute": self.config.requests_per_minute,
            "hour": self.config.requests_per_hour,
            "day": self.config.requests_per_day
        }
        
        for window_name, window_time in windows.items():
            if limits[window_name] <= 0:
                continue
            
            window_key = f"{key}:{window_name}:{window_time}"
            count = await self.store.increment(window_key, "count")
            
            if count > limits[window_name]:
                return False
        
        return True
    
    async def _check_sliding_window(self, key: str) -> bool:
        """Check rate limit using sliding window strategy."""
        now = time.time()
        data = await self.store.get(key)
        
        if "requests" not in data:
            data["requests"] = deque()
        
        requests = data["requests"]
        
        # Remove old requests
        while requests and now - requests[0] > 60:  # 1 minute window
            requests.popleft()
        
        # Check limits
        minute_count = len([r for r in requests if now - r <= 60])
        hour_count = len([r for r in requests if now - r <= 3600])
        day_count = len([r for r in requests if now - r <= 86400])
        
        if (minute_count >= self.config.requests_per_minute or
            hour_count >= self.config.requests_per_hour or
            day_count >= self.config.requests_per_day):
            return False
        
        # Add current request
        requests.append(now)
        data["last_access"] = now
        await self.store.set(key, data)
        
        return True
    
    async def _check_token_bucket(self, key: str) -> bool:
        """Check rate limit using token bucket strategy."""
        now = time.time()
        data = await self.store.get(key)
        
        if "tokens" not in data:
            data["tokens"] = self.config.requests_per_minute
            data["last_refill"] = now
        
        # Refill tokens
        time_passed = now - data["last_refill"]
        tokens_to_add = time_passed * (self.config.requests_per_minute / 60.0)
        data["tokens"] = min(
            self.config.requests_per_minute,
            data["tokens"] + tokens_to_add
        )
        data["last_refill"] = now
        
        # Check if we have tokens
        if data["tokens"] < 1:
            await self.store.set(key, data)
            return False
        
        # Consume token
        data["tokens"] -= 1
        data["last_access"] = now
        await self.store.set(key, data)
        
        return True
    
    async def is_allowed(self, request: Request) -> bool:
        """Check if request is allowed."""
        key = self._get_client_key(request)
        
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            return await self._check_fixed_window(key)
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(key)
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._check_token_bucket(key)
        else:
            # Default to sliding window
            return await self._check_sliding_window(key)
    
    async def get_rate_limit_info(self, request: Request) -> Dict[str, Any]:
        """Get current rate limit information."""
        key = self._get_client_key(request)
        data = await self.store.get(key)
        
        if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            now = time.time()
            requests = data.get("requests", deque())
            
            minute_count = len([r for r in requests if now - r <= 60])
            hour_count = len([r for r in requests if now - r <= 3600])
            day_count = len([r for r in requests if now - r <= 86400])
            
            return {
                "requests_per_minute": {
                    "limit": self.config.requests_per_minute,
                    "remaining": max(0, self.config.requests_per_minute - minute_count),
                    "used": minute_count
                },
                "requests_per_hour": {
                    "limit": self.config.requests_per_hour,
                    "remaining": max(0, self.config.requests_per_hour - hour_count),
                    "used": hour_count
                },
                "requests_per_day": {
                    "limit": self.config.requests_per_day,
                    "remaining": max(0, self.config.requests_per_day - day_count),
                    "used": day_count
                }
            }
        
        return {"strategy": self.config.strategy.value}
    
    def __del__(self):
        """Cleanup on deletion."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()


# Middleware for rate limiting
class RateLimitMiddleware:
    """Rate limiting middleware for FastAPI."""
    
    def __init__(self, config: RateLimitConfig):
        self.rate_limiter = RateLimiter(config)
    
    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Check rate limit
        if not await self.rate_limiter.is_allowed(request):
            # Get rate limit info for headers
            rate_info = await self.rate_limiter.get_rate_limit_info(request)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "rate_limit_info": rate_info
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.rate_limiter.config.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        try:
            rate_info = await self.rate_limiter.get_rate_limit_info(request)
            if "requests_per_minute" in rate_info:
                response.headers["X-RateLimit-Limit"] = str(rate_info["requests_per_minute"]["limit"])
                response.headers["X-RateLimit-Remaining"] = str(rate_info["requests_per_minute"]["remaining"])
        except Exception:
            pass  # Don't fail request if rate limit info fails
        
        return response


# Decorator for rate limiting specific endpoints
def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    requests_per_day: int = 10000,
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW,
    key_func: Optional[Callable[[Request], str]] = None
):
    """Decorator to add rate limiting to specific endpoints."""
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        requests_per_day=requests_per_day,
        strategy=strategy,
        key_func=key_func
    )
    rate_limiter = RateLimiter(config)
    
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            if not await rate_limiter.is_allowed(request):
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
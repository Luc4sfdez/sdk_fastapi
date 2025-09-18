"""
Configuration for auth-service
"""

import os
from typing import List

class Settings:
    # Service configuration
    SERVICE_NAME: str = "auth-service"
    VERSION: str = "1.0.0"
    PORT: int = int(os.getenv("PORT", 8001))
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # JWT configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # External services
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://localhost:8002")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
    ]
    
    # Redis (for token blacklist in production)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

settings = Settings()
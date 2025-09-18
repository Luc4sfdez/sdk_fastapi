"""
Configuration Settings for API Gateway
"""

from typing import List, Dict
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    PROJECT_NAME: str = "test-api-gateway"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Test API Gateway"
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8092, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Microservices configuration
    SERVICES: Dict[str, str] = Field(
        default={
            "auth": "http://localhost:8001",
            "users": "http://localhost:8002", 
            "products": "http://localhost:8003",
            "orders": "http://localhost:8004"
        },
        env="SERVICES"
    )
    
    # Rate limiting
    RATE_LIMIT_CALLS: int = Field(default=100, env="RATE_LIMIT_CALLS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")
    
    # Timeout settings
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
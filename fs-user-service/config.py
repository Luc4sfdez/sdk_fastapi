"""
Configuration Settings

Application configuration using Pydantic settings.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic settings
    PROJECT_NAME: str = "fs-user-service"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "FacturaScripts User Service - Gestión de usuarios y autenticación"
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8001, env="PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost/fs-user-service",
        env="DATABASE_URL"
    )
    
    
    
    # Redis settings
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    
    # Security settings
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
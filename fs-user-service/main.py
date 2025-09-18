"""
fs-user-service - Main Application

FacturaScripts User Service - Gestión de usuarios y autenticación
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.health import health_router
from app.auth import auth_router
from app.users import users_router

# Create FastAPI app
app = FastAPI(
    title="fs-user-service",
    description="FacturaScripts User Service - Gestión de usuarios y autenticación",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to fs-user-service!",
        "version": "1.0.0",
        "status": "running",
        "service": "FacturaScripts User Service",
        "description": "Gestión de usuarios y autenticación",
        "endpoints": {
            "health": "/health/",
            "authentication": "/auth/",
            "users": "/users/",
            "documentation": "/docs"
        },
        "features": [
            "JWT Authentication",
            "User Management",
            "Role-based Access Control",
            "Health Monitoring"
        ]
    }

@app.get("/info")
async def info():
    """Service information endpoint."""
    return {
        "service_name": "fs-user-service",
        "version": "1.0.0",
        "description": "FacturaScripts User Service - Gestión de usuarios y autenticación",
        "author": "Lucas",
        "environment": settings.ENVIRONMENT,
        "port": settings.PORT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
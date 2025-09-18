"""
test-api-gateway - API Gateway

Test API Gateway
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from app.gateway import gateway_router
from app.health import health_router
from app.middleware import RateLimitMiddleware, LoggingMiddleware

# Create FastAPI app
app = FastAPI(
    title="test-api-gateway",
    description="Test API Gateway",
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

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)  # 100 calls per minute

# Include routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(gateway_router, prefix="/api", tags=["gateway"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "test-api-gateway - API Gateway",
        "version": "1.0.0",
        "status": "running",
        "services": settings.SERVICES,
        "endpoints": {
            "health": "/health/",
            "gateway": "/api/",
            "documentation": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
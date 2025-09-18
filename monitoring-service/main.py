"""
monitoring-service - Monitoring and Logging Service

Centralized logging, metrics collection, and service health monitoring
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
import httpx
import logging
import asyncio
from datetime import datetime, timedelta
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="monitoring-service",
    description="Centralized logging, metrics collection, and service health monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SERVICES = {
    "api-gateway": {"url": "http://localhost:8000", "name": "API Gateway"},
    "auth-service": {"url": "http://localhost:8001", "name": "Authentication Service"},
    "user-service": {"url": "http://localhost:8002", "name": "User Management Service"},
    "notification-service": {"url": "http://localhost:8003", "name": "Notification Service"},
    "file-storage-service": {"url": "http://localhost:8004", "name": "File Storage Service"},
}

# Enums
class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

# Models
class LogEntry(BaseModel):
    service: str
    level: LogLevel
    message: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None

class ServiceHealth(BaseModel):
    service: str
    status: ServiceStatus
    response_time: Optional[float] = None
    last_check: datetime
    error_message: Optional[str] = None
    uptime_percentage: Optional[float] = None

class MetricEntry(BaseModel):
    service: str
    metric_name: str
    metric_value: float
    timestamp: Optional[datetime] = None
    labels: Optional[Dict[str, str]] = None

class AlertRule(BaseModel):
    id: Optional[str] = None
    name: str
    service: str
    metric: str
    condition: str  # e.g., "> 100", "< 0.95"
    threshold: float
    enabled: bool = True

# In-memory storage (use database in production)
logs_db = []
health_db = {}
metrics_db = []
alerts_db = {}
service_stats = {}

# Background tasks
async def check_service_health():
    """Check health of all services"""
    while True:
        for service_id, service_info in SERVICES.items():
            try:
                start_time = datetime.utcnow()
                
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{service_info['url']}/health")
                    
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    status = ServiceStatus.HEALTHY
                    error_message = None
                else:
                    status = ServiceStatus.UNHEALTHY
                    error_message = f"HTTP {response.status_code}"
                
            except Exception as e:
                status = ServiceStatus.UNHEALTHY
                response_time = None
                error_message = str(e)
            
            # Update health status
            health_db[service_id] = {
                "service": service_id,
                "status": status,
                "response_time": response_time,
                "last_check": datetime.utcnow(),
                "error_message": error_message
            }
            
            # Update service stats
            if service_id not in service_stats:
                service_stats[service_id] = {
                    "total_checks": 0,
                    "healthy_checks": 0,
                    "response_times": []
                }
            
            stats = service_stats[service_id]
            stats["total_checks"] += 1
            
            if status == ServiceStatus.HEALTHY:
                stats["healthy_checks"] += 1
                if response_time:
                    stats["response_times"].append(response_time)
                    # Keep only last 100 response times
                    if len(stats["response_times"]) > 100:
                        stats["response_times"] = stats["response_times"][-100:]
            
            # Calculate uptime percentage
            uptime_percentage = (stats["healthy_checks"] / stats["total_checks"]) * 100
            health_db[service_id]["uptime_percentage"] = uptime_percentage
        
        # Wait 30 seconds before next check
        await asyncio.sleep(30)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(check_service_health())

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "monitoring-service",
        "version": "1.0.0",
        "status": "running",
        "description": "Centralized logging, metrics collection, and service health monitoring",
        "features": [
            "Service health monitoring",
            "Centralized logging",
            "Metrics collection",
            "Prometheus metrics",
            "Alert management"
        ],
        "endpoints": {
            "logs": "/logs",
            "health": "/health",
            "services": "/services",
            "metrics": "/metrics",
            "prometheus": "/metrics/prometheus",
            "alerts": "/alerts",
            "dashboard": "/dashboard"
        },
        "monitored_services": list(SERVICES.keys())
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "monitoring-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "total_logs": len(logs_db),
            "total_metrics": len(metrics_db),
            "monitored_services": len(SERVICES),
            "healthy_services": sum(1 for h in health_db.values() if h["status"] == ServiceStatus.HEALTHY)
        }
    }

@app.post("/logs")
async def receive_log(log_entry: LogEntry):
    """Receive log entry from services"""
    if not log_entry.timestamp:
        log_entry.timestamp = datetime.utcnow()
    
    # Store log entry
    log_data = {
        "service": log_entry.service,
        "level": log_entry.level,
        "message": log_entry.message,
        "timestamp": log_entry.timestamp,
        "metadata": log_entry.metadata or {},
        "trace_id": log_entry.trace_id
    }
    
    logs_db.append(log_data)
    
    # Keep only last 10000 logs
    if len(logs_db) > 10000:
        logs_db[:] = logs_db[-10000:]
    
    logger.info(f"Log received from {log_entry.service}: {log_entry.level} - {log_entry.message}")
    
    return {"message": "Log entry received"}

@app.get("/logs")
async def get_logs(
    service: Optional[str] = None,
    level: Optional[LogLevel] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get logs with filtering"""
    filtered_logs = logs_db
    
    # Apply filters
    if service:
        filtered_logs = [log for log in filtered_logs if log["service"] == service]
    
    if level:
        filtered_logs = [log for log in filtered_logs if log["level"] == level]
    
    # Sort by timestamp (newest first)
    filtered_logs = sorted(filtered_logs, key=lambda x: x["timestamp"], reverse=True)
    
    # Apply pagination
    total = len(filtered_logs)
    logs_slice = filtered_logs[offset:offset + limit]
    
    return {
        "logs": logs_slice,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "service": service,
            "level": level
        }
    }

@app.get("/services")
async def get_services_health():
    """Get health status of all services"""
    services_health = []
    
    for service_id, service_info in SERVICES.items():
        health_info = health_db.get(service_id, {
            "service": service_id,
            "status": ServiceStatus.UNKNOWN,
            "last_check": None,
            "response_time": None,
            "error_message": "Not checked yet",
            "uptime_percentage": None
        })
        
        services_health.append({
            **health_info,
            "name": service_info["name"],
            "url": service_info["url"]
        })
    
    return {
        "services": services_health,
        "total": len(services_health),
        "healthy": sum(1 for s in services_health if s["status"] == ServiceStatus.HEALTHY),
        "unhealthy": sum(1 for s in services_health if s["status"] == ServiceStatus.UNHEALTHY),
        "unknown": sum(1 for s in services_health if s["status"] == ServiceStatus.UNKNOWN)
    }

@app.post("/metrics")
async def receive_metric(metric: MetricEntry):
    """Receive metric from services"""
    if not metric.timestamp:
        metric.timestamp = datetime.utcnow()
    
    # Store metric
    metric_data = {
        "service": metric.service,
        "metric_name": metric.metric_name,
        "metric_value": metric.metric_value,
        "timestamp": metric.timestamp,
        "labels": metric.labels or {}
    }
    
    metrics_db.append(metric_data)
    
    # Keep only last 50000 metrics
    if len(metrics_db) > 50000:
        metrics_db[:] = metrics_db[-50000:]
    
    return {"message": "Metric received"}

@app.get("/metrics")
async def get_metrics(
    service: Optional[str] = None,
    metric_name: Optional[str] = None,
    limit: int = 100
):
    """Get metrics with filtering"""
    filtered_metrics = metrics_db
    
    # Apply filters
    if service:
        filtered_metrics = [m for m in filtered_metrics if m["service"] == service]
    
    if metric_name:
        filtered_metrics = [m for m in filtered_metrics if m["metric_name"] == metric_name]
    
    # Sort by timestamp (newest first)
    filtered_metrics = sorted(filtered_metrics, key=lambda x: x["timestamp"], reverse=True)
    
    # Apply limit
    filtered_metrics = filtered_metrics[:limit]
    
    return {
        "metrics": filtered_metrics,
        "total": len(filtered_metrics),
        "filters": {
            "service": service,
            "metric_name": metric_name
        }
    }

@app.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Get metrics in Prometheus format"""
    prometheus_metrics = []
    
    # Service health metrics
    for service_id, health_info in health_db.items():
        status_value = 1 if health_info["status"] == ServiceStatus.HEALTHY else 0
        prometheus_metrics.append(f'service_health{{service="{service_id}"}} {status_value}')
        
        if health_info.get("response_time"):
            prometheus_metrics.append(f'service_response_time_ms{{service="{service_id}"}} {health_info["response_time"]}')
        
        if health_info.get("uptime_percentage"):
            prometheus_metrics.append(f'service_uptime_percentage{{service="{service_id}"}} {health_info["uptime_percentage"]}')
    
    # Log count metrics
    log_counts = {}
    for log in logs_db[-1000:]:  # Last 1000 logs
        key = f"{log['service']}_{log['level']}"
        log_counts[key] = log_counts.get(key, 0) + 1
    
    for key, count in log_counts.items():
        service, level = key.split("_", 1)
        prometheus_metrics.append(f'log_count{{service="{service}",level="{level}"}} {count}')
    
    # System metrics
    prometheus_metrics.append(f'monitoring_total_logs {len(logs_db)}')
    prometheus_metrics.append(f'monitoring_total_metrics {len(metrics_db)}')
    prometheus_metrics.append(f'monitoring_monitored_services {len(SERVICES)}')
    
    return "\n".join(prometheus_metrics)

@app.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data"""
    # Service health summary
    services_summary = await get_services_health()
    
    # Recent logs summary
    recent_logs = logs_db[-100:] if logs_db else []
    log_levels_count = {}
    for log in recent_logs:
        level = log["level"]
        log_levels_count[level] = log_levels_count.get(level, 0) + 1
    
    # Response time statistics
    response_times = {}
    for service_id, stats in service_stats.items():
        if stats["response_times"]:
            times = stats["response_times"]
            response_times[service_id] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times)
            }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_summary,
        "logs": {
            "total": len(logs_db),
            "recent_count": len(recent_logs),
            "levels": log_levels_count
        },
        "metrics": {
            "total": len(metrics_db)
        },
        "response_times": response_times,
        "system": {
            "uptime": "Running",
            "version": "1.0.0"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    )
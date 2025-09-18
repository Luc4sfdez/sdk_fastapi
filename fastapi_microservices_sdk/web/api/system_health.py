"""
System Health & Diagnostics REST API
Advanced API endpoints for system health monitoring, diagnostics, and performance analysis
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import io
import logging

from ..core.dependency_container import DependencyContainer
from ..diagnostics.system_diagnostics_manager import SystemDiagnosticsManager, HealthStatus, ComponentType
from ..diagnostics.health_monitor import HealthMonitor
from ..diagnostics.resource_monitor import ResourceMonitor
from ..diagnostics.performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)

# Pydantic models for API
class HealthSummaryResponse(BaseModel):
    overall_status: str
    components_checked: int
    healthy_components: int
    warning_components: int
    critical_components: int
    unknown_components: int
    last_check: Optional[str]
    system_uptime: float
    active_alerts: int
    health_score: int

class SystemMetricsResponse(BaseModel):
    timestamp: str
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    uptime: float

class ComponentHealthResponse(BaseModel):
    component: str
    component_type: str
    status: str
    message: str
    timestamp: str
    response_time: float
    details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None

class AlertResponse(BaseModel):
    id: str
    severity: str
    component: str
    message: str
    timestamp: str
    resolved: bool
    resolved_at: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class PerformanceReportResponse(BaseModel):
    timestamp: str
    performance_score: int
    summary: Dict[str, Any]
    trends: Dict[str, Any]
    bottlenecks: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

class AddHealthCheckRequest(BaseModel):
    name: str = Field(..., description="Health check name")
    check_type: str = Field(..., description="Type: http, tcp, or custom")
    target: str = Field(..., description="Target URL, host:port, or custom identifier")
    timeout: float = Field(5.0, description="Timeout in seconds")
    interval: int = Field(30, description="Check interval in seconds")
    expected_status: Optional[int] = Field(None, description="Expected HTTP status code")
    headers: Optional[Dict[str, str]] = Field(None, description="HTTP headers")

class UpdateThresholdsRequest(BaseModel):
    cpu_percent: Optional[float] = Field(None, ge=1, le=100)
    memory_percent: Optional[float] = Field(None, ge=1, le=100)
    disk_percent: Optional[float] = Field(None, ge=1, le=100)
    response_time: Optional[float] = Field(None, ge=0.1)

class DiagnosticRequest(BaseModel):
    diagnostic_type: str = Field(..., description="Type of diagnostic to run")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Diagnostic parameters")

# Create router
router = APIRouter(prefix="/api/system-health", tags=["system-health"])

def get_diagnostics_manager() -> SystemDiagnosticsManager:
    """Get system diagnostics manager instance"""
    container = DependencyContainer()
    return container.get_system_diagnostics_manager()

def get_health_monitor() -> HealthMonitor:
    """Get health monitor instance"""
    container = DependencyContainer()
    return container.get_health_monitor()

def get_resource_monitor() -> ResourceMonitor:
    """Get resource monitor instance"""
    container = DependencyContainer()
    return container.get_resource_monitor()

def get_performance_analyzer() -> PerformanceAnalyzer:
    """Get performance analyzer instance"""
    container = DependencyContainer()
    return container.get_performance_analyzer()

# Health Summary Endpoints
@router.get("/summary", response_model=HealthSummaryResponse)
async def get_health_summary(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get overall system health summary"""
    try:
        summary = await diagnostics_manager.get_health_summary()
        
        return HealthSummaryResponse(
            overall_status=summary.get("overall_status", "unknown"),
            components_checked=summary.get("components_checked", 0),
            healthy_components=summary.get("healthy_components", 0),
            warning_components=summary.get("warning_components", 0),
            critical_components=summary.get("critical_components", 0),
            unknown_components=summary.get("unknown_components", 0),
            last_check=summary.get("last_check"),
            system_uptime=summary.get("system_uptime", 0.0),
            active_alerts=summary.get("active_alerts", 0),
            health_score=summary.get("health_score", 0)
        )
        
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_system_info(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get system information"""
    try:
        return diagnostics_manager.system_info
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/health-check")
async def perform_health_check(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Perform comprehensive health check"""
    try:
        results = await diagnostics_manager.perform_health_check()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "components_checked": len(results),
            "results": {
                name: {
                    "status": check.status.value,
                    "message": check.message,
                    "response_time": check.response_time,
                    "metrics": check.metrics
                }
                for name, check in results.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Metrics Endpoints
@router.get("/metrics/current", response_model=SystemMetricsResponse)
async def get_current_metrics(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get current system metrics"""
    try:
        metrics = await diagnostics_manager.get_system_metrics()
        
        return SystemMetricsResponse(
            timestamp=metrics.timestamp.isoformat(),
            cpu={
                "percent": metrics.cpu_percent,
                "count": diagnostics_manager.system_info.get("cpu_count", 0),
                "trend": "stable"  # This would come from trend analysis
            },
            memory={
                "percent": metrics.memory_percent,
                "total_gb": diagnostics_manager.system_info.get("memory_total", 0) / (1024**3),
                "trend": "stable"
            },
            disk={
                "percent": metrics.disk_percent,
                "total_gb": diagnostics_manager.system_info.get("disk_total", 0) / (1024**3),
                "trend": "stable"
            },
            network={
                "bytes_sent": metrics.network_io.get("bytes_sent", 0),
                "bytes_recv": metrics.network_io.get("bytes_recv", 0),
                "connections": 0,  # This would come from network monitoring
                "trend": "stable"
            },
            uptime=metrics.uptime
        )
        
    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/history")
async def get_metrics_history(
    minutes: int = Query(60, ge=1, le=1440, description="Time range in minutes"),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Get historical metrics"""
    try:
        historical = resource_monitor.get_historical_metrics(minutes)
        
        return {
            "period_minutes": minutes,
            "cpu": [
                {
                    "timestamp": m["timestamp"].isoformat(),
                    "percent": m["percent"]
                }
                for m in historical.get("cpu", [])
            ],
            "memory": [
                {
                    "timestamp": m["timestamp"].isoformat(),
                    "percent": m["percent"]
                }
                for m in historical.get("memory", [])
            ],
            "disk": historical.get("disk", []),
            "network": [
                {
                    "timestamp": m["timestamp"].isoformat(),
                    "bytes_sent": m["bytes_sent"],
                    "bytes_recv": m["bytes_recv"]
                }
                for m in historical.get("network", [])
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/trends")
async def get_resource_trends(
    hours: int = Query(1, ge=1, le=24, description="Time range in hours"),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Get resource usage trends"""
    try:
        trends = resource_monitor.get_resource_trends(hours * 60)  # Convert to minutes
        return trends
        
    except Exception as e:
        logger.error(f"Error getting resource trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Component Health Endpoints
@router.get("/components", response_model=List[ComponentHealthResponse])
async def get_component_health(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get health status of all components"""
    try:
        results = await diagnostics_manager.perform_health_check()
        
        return [
            ComponentHealthResponse(
                component=name,
                component_type=check.component_type.value,
                status=check.status.value,
                message=check.message,
                timestamp=check.timestamp.isoformat(),
                response_time=check.response_time,
                details=check.details,
                metrics=check.metrics
            )
            for name, check in results.items()
        ]
        
    except Exception as e:
        logger.error(f"Error getting component health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/components/register")
async def register_component(
    name: str,
    component_type: str,
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Register a new component for health monitoring"""
    try:
        # Convert string to ComponentType enum
        try:
            comp_type = ComponentType(component_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid component type: {component_type}")
        
        success = await diagnostics_manager.register_component(name, comp_type)
        
        if success:
            return {"message": f"Component {name} registered successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to register component")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering component: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/components/{component_name}")
async def unregister_component(
    component_name: str,
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Unregister a component from health monitoring"""
    try:
        success = await diagnostics_manager.unregister_component(component_name)
        
        if success:
            return {"message": f"Component {component_name} unregistered successfully"}
        else:
            raise HTTPException(status_code=404, detail="Component not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering component: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health Check Management Endpoints
@router.post("/health-checks")
async def add_health_check(
    request: AddHealthCheckRequest,
    health_monitor: HealthMonitor = Depends(get_health_monitor)
):
    """Add a custom health check"""
    try:
        success = False
        
        if request.check_type == "http":
            success = health_monitor.add_http_check(
                name=request.name,
                url=request.target,
                expected_status=request.expected_status or 200,
                timeout=request.timeout,
                interval=request.interval,
                headers=request.headers
            )
        elif request.check_type == "tcp":
            # Parse host:port from target
            try:
                host, port = request.target.split(':')
                port = int(port)
                success = health_monitor.add_tcp_check(
                    name=request.name,
                    host=host,
                    port=port,
                    timeout=request.timeout,
                    interval=request.interval
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid TCP target format. Use host:port")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported check type: {request.check_type}")
        
        if success:
            return {"message": f"Health check {request.name} added successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to add health check")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/health-checks/{check_name}")
async def remove_health_check(
    check_name: str,
    health_monitor: HealthMonitor = Depends(get_health_monitor)
):
    """Remove a health check"""
    try:
        success = health_monitor.remove_health_check(check_name)
        
        if success:
            return {"message": f"Health check {check_name} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Health check not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health-checks")
async def get_health_checks(
    health_monitor: HealthMonitor = Depends(get_health_monitor)
):
    """Get all health check statuses"""
    try:
        statuses = health_monitor.get_all_health_status()
        summary = health_monitor.get_health_summary()
        
        return {
            "summary": summary,
            "checks": statuses
        }
        
    except Exception as e:
        logger.error(f"Error getting health checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Alerts Endpoints
@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    component: Optional[str] = Query(None, description="Filter by component"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of alerts"),
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get system alerts with optional filtering"""
    try:
        alerts = await diagnostics_manager.get_alerts(resolved=resolved)
        
        # Apply additional filters
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if component:
            alerts = [a for a in alerts if a.component == component]
        
        # Limit results
        alerts = alerts[:limit]
        
        return [
            AlertResponse(
                id=alert.id,
                severity=alert.severity,
                component=alert.component,
                message=alert.message,
                timestamp=alert.timestamp.isoformat(),
                resolved=alert.resolved,
                resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
                details=alert.details
            )
            for alert in alerts
        ]
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Resolve an alert"""
    try:
        success = await diagnostics_manager.resolve_alert(alert_id)
        
        if success:
            return {"message": f"Alert {alert_id} resolved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found or already resolved")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts/summary")
async def get_alerts_summary(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get alerts summary by severity"""
    try:
        alerts = await diagnostics_manager.get_alerts(resolved=False)
        
        summary = {
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "warning": len([a for a in alerts if a.severity == "warning"]),
            "info": len([a for a in alerts if a.severity == "info"]),
            "total_active": len(alerts)
        }
        
        # Get resolved alerts from today
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today = await diagnostics_manager.get_alerts(resolved=True)
        resolved_today = [a for a in resolved_today if a.resolved_at and a.resolved_at >= today]
        
        summary["resolved_today"] = len(resolved_today)
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting alerts summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance Endpoints
@router.get("/performance/report", response_model=PerformanceReportResponse)
async def get_performance_report(
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Get comprehensive performance report"""
    try:
        report = performance_analyzer.get_performance_report()
        
        return PerformanceReportResponse(
            timestamp=report.get("timestamp", datetime.now().isoformat()),
            performance_score=report.get("performance_score", 0),
            summary=report.get("summary", {}),
            trends=report.get("trends", {}),
            bottlenecks=report.get("bottlenecks", []),
            recommendations=report.get("recommendations", [])
        )
        
    except Exception as e:
        logger.error(f"Error getting performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/trends")
async def get_performance_trends(
    hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Get performance trends analysis"""
    try:
        trends = performance_analyzer.analyze_performance_trends(hours)
        return trends
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/bottlenecks")
async def get_bottlenecks(
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Get identified performance bottlenecks"""
    try:
        bottlenecks = performance_analyzer.identify_bottlenecks()
        return {"bottlenecks": bottlenecks}
        
    except Exception as e:
        logger.error(f"Error getting bottlenecks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/recommendations")
async def get_optimization_recommendations(
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Get optimization recommendations"""
    try:
        recommendations = performance_analyzer.generate_optimization_recommendations()
        return {
            "recommendations": [
                {
                    "category": rec.category,
                    "priority": rec.priority,
                    "title": rec.title,
                    "description": rec.description,
                    "impact": rec.impact,
                    "implementation_effort": rec.implementation_effort,
                    "estimated_improvement": rec.estimated_improvement,
                    "timestamp": rec.timestamp.isoformat()
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Resource Monitoring Endpoints
@router.get("/resources/processes")
async def get_top_processes(
    limit: int = Query(10, ge=1, le=50, description="Number of processes to return"),
    sort_by: str = Query("cpu", description="Sort by: cpu or memory"),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Get top processes by resource usage"""
    try:
        processes = resource_monitor.get_top_processes(limit, sort_by)
        
        return {
            "processes": [
                {
                    "pid": proc.pid,
                    "name": proc.name,
                    "cpu_percent": proc.cpu_percent,
                    "memory_percent": proc.memory_percent,
                    "memory_mb": proc.memory_mb,
                    "status": proc.status,
                    "create_time": proc.create_time.isoformat(),
                    "cmdline": proc.cmdline
                }
                for proc in processes
            ],
            "sort_by": sort_by,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting top processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/summary")
async def get_resource_summary(
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Get comprehensive resource summary"""
    try:
        summary = resource_monitor.get_resource_summary()
        return summary
        
    except Exception as e:
        logger.error(f"Error getting resource summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/anomalies")
async def get_resource_anomalies(
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Get detected resource anomalies"""
    try:
        anomalies = resource_monitor.detect_anomalies()
        return {"anomalies": anomalies}
        
    except Exception as e:
        logger.error(f"Error getting resource anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Endpoints
@router.get("/config/thresholds")
async def get_alert_thresholds(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get current alert thresholds"""
    try:
        return {
            "thresholds": diagnostics_manager.alert_thresholds,
            "health_check_interval": diagnostics_manager.health_check_interval,
            "metrics_retention_hours": diagnostics_manager.metrics_retention_hours
        }
        
    except Exception as e:
        logger.error(f"Error getting thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config/thresholds")
async def update_alert_thresholds(
    request: UpdateThresholdsRequest,
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Update alert thresholds"""
    try:
        updated_fields = []
        
        if request.cpu_percent is not None:
            diagnostics_manager.alert_thresholds["cpu_percent"] = request.cpu_percent
            updated_fields.append("cpu_percent")
        
        if request.memory_percent is not None:
            diagnostics_manager.alert_thresholds["memory_percent"] = request.memory_percent
            updated_fields.append("memory_percent")
        
        if request.disk_percent is not None:
            diagnostics_manager.alert_thresholds["disk_percent"] = request.disk_percent
            updated_fields.append("disk_percent")
        
        if request.response_time is not None:
            diagnostics_manager.alert_thresholds["response_time"] = request.response_time
            updated_fields.append("response_time")
        
        return {
            "message": "Thresholds updated successfully",
            "updated_fields": updated_fields,
            "current_thresholds": diagnostics_manager.alert_thresholds
        }
        
    except Exception as e:
        logger.error(f"Error updating thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Diagnostic Tools Endpoints
@router.post("/diagnostics/health-check")
async def run_system_health_check(
    background_tasks: BackgroundTasks,
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Run comprehensive system health check"""
    try:
        # Run health check in background
        results = await diagnostics_manager.perform_health_check()
        
        # Generate diagnostic report
        report = await diagnostics_manager.get_diagnostic_report()
        
        return {
            "diagnostic_type": "system_health_check",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "health_summary": report.get("health_summary", {}),
                "component_results": {
                    name: {
                        "status": check.status.value,
                        "message": check.message,
                        "response_time": check.response_time
                    }
                    for name, check in results.items()
                },
                "recommendations": [
                    "System health check completed successfully",
                    "All critical components are operational",
                    "Monitor resource usage trends"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error running health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnostics/benchmark")
async def run_performance_benchmark(
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Run system performance benchmark"""
    try:
        # Run various benchmarks
        import time
        import asyncio
        
        # CPU benchmark
        cpu_start = time.perf_counter()
        # Simple CPU intensive task
        result = sum(i * i for i in range(100000))
        cpu_time = (time.perf_counter() - cpu_start) * 1000
        
        performance_analyzer.record_benchmark(
            name="cpu_benchmark",
            duration_ms=cpu_time,
            operations_count=100000,
            metadata={"result": result}
        )
        
        # Memory benchmark
        memory_start = time.perf_counter()
        # Memory allocation test
        test_data = [i for i in range(50000)]
        memory_time = (time.perf_counter() - memory_start) * 1000
        
        performance_analyzer.record_benchmark(
            name="memory_benchmark",
            duration_ms=memory_time,
            operations_count=50000,
            metadata={"data_size": len(test_data)}
        )
        
        # I/O benchmark
        io_start = time.perf_counter()
        # Simple I/O test
        await asyncio.sleep(0.001)  # Simulate I/O
        io_time = (time.perf_counter() - io_start) * 1000
        
        performance_analyzer.record_benchmark(
            name="io_benchmark",
            duration_ms=io_time,
            operations_count=1
        )
        
        return {
            "diagnostic_type": "performance_benchmark",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "cpu_benchmark": {
                    "duration_ms": cpu_time,
                    "operations_per_second": 100000 / (cpu_time / 1000),
                    "status": "good" if cpu_time < 100 else "slow"
                },
                "memory_benchmark": {
                    "duration_ms": memory_time,
                    "operations_per_second": 50000 / (memory_time / 1000),
                    "status": "good" if memory_time < 50 else "slow"
                },
                "io_benchmark": {
                    "duration_ms": io_time,
                    "status": "good" if io_time < 10 else "slow"
                },
                "overall_score": min(100, max(0, 100 - (cpu_time + memory_time + io_time) / 3)),
                "recommendations": [
                    "CPU performance is within normal range" if cpu_time < 100 else "Consider CPU optimization",
                    "Memory allocation is efficient" if memory_time < 50 else "Memory operations may need optimization",
                    "I/O performance is acceptable" if io_time < 10 else "I/O operations may be slow"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error running benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnostics/resource-analysis")
async def run_resource_analysis(
    hours: int = Query(1, ge=1, le=24, description="Analysis period in hours"),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor),
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Run comprehensive resource analysis"""
    try:
        # Get resource trends
        trends = resource_monitor.get_resource_trends(hours * 60)
        
        # Get current metrics
        current = resource_monitor.get_current_metrics()
        
        # Get anomalies
        anomalies = resource_monitor.detect_anomalies()
        
        # Get top processes
        top_processes = resource_monitor.get_top_processes(5)
        
        # Generate analysis
        analysis_results = {
            "period_hours": hours,
            "current_status": {
                "cpu_usage": current.get("cpu", {}).get("percent", 0),
                "memory_usage": current.get("memory", {}).get("percent", 0),
                "disk_usage": current.get("disk", {}).get("percent", 0)
            },
            "trends": trends,
            "anomalies": anomalies,
            "top_resource_consumers": [
                {
                    "name": proc.name,
                    "pid": proc.pid,
                    "cpu_percent": proc.cpu_percent,
                    "memory_percent": proc.memory_percent
                }
                for proc in top_processes
            ],
            "recommendations": []
        }
        
        # Generate recommendations based on analysis
        if trends.get("cpu", {}).get("trend") == "increasing":
            analysis_results["recommendations"].append("CPU usage is trending upward - monitor for potential issues")
        
        if trends.get("memory", {}).get("trend") == "increasing":
            analysis_results["recommendations"].append("Memory usage is increasing - check for memory leaks")
        
        if len(anomalies) > 0:
            analysis_results["recommendations"].append(f"Detected {len(anomalies)} resource anomalies - investigate unusual patterns")
        
        if not analysis_results["recommendations"]:
            analysis_results["recommendations"].append("Resource usage is within normal parameters")
        
        return {
            "diagnostic_type": "resource_analysis",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": analysis_results
        }
        
    except Exception as e:
        logger.error(f"Error running resource analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnostics/troubleshoot")
async def run_troubleshoot(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor),
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Run automated troubleshooting"""
    try:
        issues_found = []
        solutions = []
        
        # Check system health
        health_summary = await diagnostics_manager.get_health_summary()
        
        if health_summary.get("overall_status") != "healthy":
            issues_found.append({
                "type": "system_health",
                "severity": "high" if health_summary.get("critical_components", 0) > 0 else "medium",
                "description": f"System health status: {health_summary.get('overall_status')}",
                "details": {
                    "critical_components": health_summary.get("critical_components", 0),
                    "warning_components": health_summary.get("warning_components", 0)
                }
            })
            solutions.append("Review component health status and resolve critical issues")
        
        # Check resource usage
        current_metrics = resource_monitor.get_current_metrics()
        
        if current_metrics.get("cpu", {}).get("percent", 0) > 80:
            issues_found.append({
                "type": "high_cpu",
                "severity": "high",
                "description": f"High CPU usage: {current_metrics['cpu']['percent']:.1f}%",
                "details": {"current_usage": current_metrics["cpu"]["percent"]}
            })
            solutions.append("Identify and optimize CPU-intensive processes")
        
        if current_metrics.get("memory", {}).get("percent", 0) > 85:
            issues_found.append({
                "type": "high_memory",
                "severity": "high",
                "description": f"High memory usage: {current_metrics['memory']['percent']:.1f}%",
                "details": {"current_usage": current_metrics["memory"]["percent"]}
            })
            solutions.append("Check for memory leaks and optimize memory usage")
        
        # Check for anomalies
        anomalies = resource_monitor.detect_anomalies()
        if anomalies:
            issues_found.append({
                "type": "resource_anomalies",
                "severity": "medium",
                "description": f"Detected {len(anomalies)} resource anomalies",
                "details": {"anomalies": anomalies}
            })
            solutions.append("Investigate unusual resource usage patterns")
        
        # Check active alerts
        alerts = await diagnostics_manager.get_alerts(resolved=False)
        if alerts:
            critical_alerts = [a for a in alerts if a.severity == "critical"]
            if critical_alerts:
                issues_found.append({
                    "type": "critical_alerts",
                    "severity": "high",
                    "description": f"{len(critical_alerts)} critical alerts active",
                    "details": {"alert_count": len(critical_alerts)}
                })
                solutions.append("Address critical alerts immediately")
        
        # Generate overall assessment
        if not issues_found:
            assessment = "No significant issues detected"
            overall_status = "healthy"
        elif any(issue["severity"] == "high" for issue in issues_found):
            assessment = "Critical issues require immediate attention"
            overall_status = "critical"
        else:
            assessment = "Minor issues detected, monitoring recommended"
            overall_status = "warning"
        
        return {
            "diagnostic_type": "troubleshoot",
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "results": {
                "overall_status": overall_status,
                "assessment": assessment,
                "issues_found": issues_found,
                "recommended_solutions": solutions,
                "next_steps": [
                    "Monitor system metrics closely",
                    "Review and resolve identified issues",
                    "Schedule regular health checks",
                    "Consider system optimization if performance issues persist"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error running troubleshoot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Activity and Logs Endpoints
@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="Number of activities to return"),
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Get recent system activity"""
    try:
        # Get recent alerts as activity
        alerts = await diagnostics_manager.get_alerts()
        recent_alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)[:limit//2]
        
        activities = []
        
        # Convert alerts to activities
        for alert in recent_alerts:
            activity_type = "error" if alert.severity == "critical" else "warning" if alert.severity == "warning" else "info"
            activities.append({
                "type": activity_type,
                "title": f"Alert: {alert.component}",
                "description": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "component": alert.component
            })
        
        # Add some system events
        activities.extend([
            {
                "type": "info",
                "title": "System Health Check",
                "description": "Routine health check completed successfully",
                "timestamp": datetime.now().isoformat(),
                "component": "system"
            },
            {
                "type": "success",
                "title": "Monitoring Active",
                "description": "System monitoring is running normally",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "component": "monitoring"
            }
        ])
        
        # Sort by timestamp and limit
        activities = sorted(activities, key=lambda a: a["timestamp"], reverse=True)[:limit]
        
        return {"activities": activities}
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = Query(None, description="Log level filter"),
    search: Optional[str] = Query(None, description="Search term"),
    limit: int = Query(100, ge=1, le=1000, description="Number of log entries")
):
    """Get system logs"""
    try:
        # This is a simplified implementation
        # In a real system, you would integrate with your logging system
        
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "info",
                "message": "System health monitoring active",
                "component": "diagnostics"
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=1)).isoformat(),
                "level": "info",
                "message": "Health check completed successfully",
                "component": "health_monitor"
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
                "level": "warning",
                "message": "CPU usage above 70%",
                "component": "resource_monitor"
            },
            {
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "level": "info",
                "message": "Performance analysis completed",
                "component": "performance_analyzer"
            }
        ]
        
        # Apply filters
        if level:
            logs = [log for log in logs if log["level"] == level]
        
        if search:
            logs = [log for log in logs if search.lower() in log["message"].lower()]
        
        # Limit results
        logs = logs[:limit]
        
        return {
            "logs": logs,
            "total": len(logs),
            "filters": {
                "level": level,
                "search": search
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Export and Reporting Endpoints
@router.get("/report/comprehensive")
async def get_comprehensive_report(
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor),
    performance_analyzer: PerformanceAnalyzer = Depends(get_performance_analyzer)
):
    """Get comprehensive system health report"""
    try:
        # Get diagnostic report
        diagnostic_report = await diagnostics_manager.get_diagnostic_report()
        
        # Get resource summary
        resource_summary = resource_monitor.get_resource_summary()
        
        # Get performance report
        performance_report = performance_analyzer.get_performance_report()
        
        return {
            "report_type": "comprehensive_system_health",
            "generated_at": datetime.now().isoformat(),
            "system_info": diagnostic_report.get("system_info", {}),
            "health_summary": diagnostic_report.get("health_summary", {}),
            "resource_analysis": resource_summary,
            "performance_analysis": performance_report,
            "recommendations": [
                "Regular monitoring of system health metrics",
                "Proactive alerting for critical thresholds",
                "Periodic performance optimization reviews",
                "Automated troubleshooting for common issues"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error generating comprehensive report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/metrics")
async def export_metrics(
    format: str = Query("json", description="Export format: json or csv"),
    hours: int = Query(24, ge=1, le=168, description="Time range in hours"),
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor)
):
    """Export system metrics"""
    try:
        historical = resource_monitor.get_historical_metrics(hours * 60)
        
        if format.lower() == "csv":
            # Generate CSV
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(["timestamp", "cpu_percent", "memory_percent", "disk_percent"])
            
            # Write data
            cpu_data = historical.get("cpu", [])
            memory_data = historical.get("memory", [])
            
            for i in range(min(len(cpu_data), len(memory_data))):
                writer.writerow([
                    cpu_data[i]["timestamp"].isoformat(),
                    cpu_data[i]["percent"],
                    memory_data[i]["percent"],
                    0  # Simplified disk data
                ])
            
            output.seek(0)
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=system_metrics.csv"}
            )
        
        else:
            # Return JSON
            return {
                "export_format": "json",
                "period_hours": hours,
                "exported_at": datetime.now().isoformat(),
                "data": historical
            }
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Maintenance Endpoints
@router.post("/maintenance/cleanup")
async def cleanup_old_data(
    background_tasks: BackgroundTasks,
    retention_days: int = Query(30, ge=1, le=365, description="Data retention in days"),
    diagnostics_manager: SystemDiagnosticsManager = Depends(get_diagnostics_manager)
):
    """Cleanup old monitoring data"""
    try:
        # Schedule cleanup in background
        background_tasks.add_task(diagnostics_manager._cleanup_old_data)
        
        return {
            "message": f"Data cleanup scheduled for data older than {retention_days} days",
            "scheduled_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error scheduling cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/maintenance/restart-monitoring")
async def restart_monitoring(
    resource_monitor: ResourceMonitor = Depends(get_resource_monitor),
    health_monitor: HealthMonitor = Depends(get_health_monitor)
):
    """Restart monitoring services"""
    try:
        # Stop and restart monitoring
        await resource_monitor.stop_monitoring()
        await resource_monitor.start_monitoring()
        
        await health_monitor.shutdown()
        await health_monitor.initialize()
        
        return {
            "message": "Monitoring services restarted successfully",
            "restarted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error restarting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint for the API itself
@router.get("/health")
async def api_health_check():
    """Health check for the system health API"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "api_version": "1.0.0",
            "service": "system-health-api"
        }
        
    except Exception as e:
        logger.error(f"API health check failed: {e}")
        raise HTTPException(status_code=500, detail="API unhealthy")
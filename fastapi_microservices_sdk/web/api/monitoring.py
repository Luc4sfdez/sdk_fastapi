"""
Monitoring dashboard API endpoints.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..core.dependency_container import DependencyContainer
from ..monitoring.monitoring_manager import MonitoringManager
from ..websockets.websocket_manager import WebSocketManager


class TimeRange(str, Enum):
    """Time range options for metrics queries."""
    LAST_5M = "5m"
    LAST_15M = "15m"
    LAST_1H = "1h"
    LAST_6H = "6h"
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    CUSTOM = "custom"


class AggregationType(str, Enum):
    """Aggregation types for metrics data."""
    RAW = "raw"
    AVERAGE = "avg"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status options."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


# Request/Response Models

class MetricsQueryRequest(BaseModel):
    """Request model for metrics queries."""
    service_ids: Optional[List[str]] = Field(None, description="List of service IDs to query")
    metric_names: Optional[List[str]] = Field(None, description="List of metric names to include")
    time_range: TimeRange = Field(TimeRange.LAST_1H, description="Time range for the query")
    start_time: Optional[datetime] = Field(None, description="Custom start time (for custom range)")
    end_time: Optional[datetime] = Field(None, description="Custom end time (for custom range)")
    aggregation: AggregationType = Field(AggregationType.RAW, description="Aggregation type")
    interval: Optional[str] = Field("1m", description="Aggregation interval (e.g., '1m', '5m', '1h')")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    
    @validator('start_time', 'end_time')
    def validate_custom_time_range(cls, v, values):
        """Validate custom time range."""
        if values.get('time_range') == TimeRange.CUSTOM:
            if not v:
                raise ValueError("start_time and end_time are required for custom time range")
        return v


class MetricDataPoint(BaseModel):
    """Single metric data point."""
    timestamp: datetime
    value: Union[float, int, str]
    labels: Optional[Dict[str, str]] = None


class MetricSeries(BaseModel):
    """Metric time series data."""
    metric_name: str
    service_id: str
    data_points: List[MetricDataPoint]
    aggregation: AggregationType
    interval: str


class MetricsQueryResponse(BaseModel):
    """Response model for metrics queries."""
    query: MetricsQueryRequest
    series: List[MetricSeries]
    total_points: int
    execution_time_ms: float
    cached: bool = False


class AlertRuleRequest(BaseModel):
    """Request model for creating alert rules."""
    name: str = Field(..., description="Alert rule name")
    description: Optional[str] = Field(None, description="Alert rule description")
    service_id: Optional[str] = Field(None, description="Target service ID (None for global)")
    metric_name: str = Field(..., description="Metric to monitor")
    condition: str = Field(..., description="Alert condition (e.g., '> 80', '< 10')")
    threshold: float = Field(..., description="Alert threshold value")
    severity: AlertSeverity = Field(AlertSeverity.MEDIUM, description="Alert severity")
    enabled: bool = Field(True, description="Whether the rule is enabled")
    notification_channels: Optional[List[str]] = Field(None, description="Notification channels")
    evaluation_interval: int = Field(60, description="Evaluation interval in seconds")
    for_duration: int = Field(300, description="Duration condition must be true (seconds)")


class AlertRule(BaseModel):
    """Alert rule model."""
    id: str
    name: str
    description: Optional[str]
    service_id: Optional[str]
    metric_name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    enabled: bool
    notification_channels: List[str]
    evaluation_interval: int
    for_duration: int
    created_at: datetime
    updated_at: datetime
    last_evaluation: Optional[datetime]


class Alert(BaseModel):
    """Active alert model."""
    id: str
    rule_id: str
    rule_name: str
    service_id: Optional[str]
    metric_name: str
    current_value: float
    threshold: float
    severity: AlertSeverity
    status: AlertStatus
    message: str
    started_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
    labels: Optional[Dict[str, str]]


class DashboardConfig(BaseModel):
    """Dashboard configuration model."""
    id: str
    name: str
    description: Optional[str]
    layout: Dict[str, Any]
    widgets: List[Dict[str, Any]]
    refresh_interval: int = Field(30, description="Auto-refresh interval in seconds")
    time_range: TimeRange = Field(TimeRange.LAST_1H)
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]


class DashboardConfigRequest(BaseModel):
    """Request model for dashboard configuration."""
    name: str = Field(..., description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: Dict[str, Any] = Field(..., description="Dashboard layout configuration")
    widgets: List[Dict[str, Any]] = Field(..., description="Dashboard widgets configuration")
    refresh_interval: int = Field(30, description="Auto-refresh interval in seconds")
    time_range: TimeRange = Field(TimeRange.LAST_1H)


# API Router

def create_monitoring_router(container: DependencyContainer) -> APIRouter:
    """Create monitoring API router."""
    router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
    
    def get_monitoring_manager() -> MonitoringManager:
        """Get monitoring manager dependency."""
        return container.get_monitoring_manager()
    
    def get_websocket_manager() -> WebSocketManager:
        """Get WebSocket manager dependency."""
        return container.get_websocket_manager()
    
    @router.post("/metrics/query", response_model=MetricsQueryResponse)
    async def query_metrics(
        request: MetricsQueryRequest,
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """
        Query metrics data with time range and aggregation.
        
        This endpoint allows querying historical and real-time metrics data
        with various filtering and aggregation options.
        """
        try:
            start_time = datetime.utcnow()
            
            # Parse time range
            if request.time_range == TimeRange.CUSTOM:
                query_start = request.start_time
                query_end = request.end_time
            else:
                query_end = datetime.utcnow()
                time_deltas = {
                    TimeRange.LAST_5M: timedelta(minutes=5),
                    TimeRange.LAST_15M: timedelta(minutes=15),
                    TimeRange.LAST_1H: timedelta(hours=1),
                    TimeRange.LAST_6H: timedelta(hours=6),
                    TimeRange.LAST_24H: timedelta(days=1),
                    TimeRange.LAST_7D: timedelta(days=7),
                    TimeRange.LAST_30D: timedelta(days=30),
                }
                query_start = query_end - time_deltas[request.time_range]
            
            # Query metrics from monitoring manager
            metrics_data = await monitoring_manager.query_metrics(
                service_ids=request.service_ids,
                metric_names=request.metric_names,
                start_time=query_start,
                end_time=query_end,
                aggregation=request.aggregation.value,
                interval=request.interval,
                filters=request.filters or {}
            )
            
            # Convert to response format
            series = []
            total_points = 0
            
            for service_id, service_metrics in metrics_data.items():
                for metric_name, data_points in service_metrics.items():
                    metric_series = MetricSeries(
                        metric_name=metric_name,
                        service_id=service_id,
                        data_points=[
                            MetricDataPoint(
                                timestamp=point.get("timestamp", datetime.utcnow()),
                                value=point.get("value", 0),
                                labels=point.get("labels")
                            )
                            for point in data_points
                        ],
                        aggregation=request.aggregation,
                        interval=request.interval
                    )
                    series.append(metric_series)
                    total_points += len(data_points)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return MetricsQueryResponse(
                query=request,
                series=series,
                total_points=total_points,
                execution_time_ms=execution_time,
                cached=False  # TODO: Implement caching
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error querying metrics: {str(e)}")
    
    @router.get("/metrics/services", response_model=List[str])
    async def get_available_services(
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get list of available services with metrics."""
        try:
            services = await monitoring_manager.get_available_services()
            return services
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting services: {str(e)}")
    
    @router.get("/metrics/names", response_model=List[str])
    async def get_available_metrics(
        service_id: Optional[str] = Query(None, description="Filter by service ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get list of available metric names."""
        try:
            metrics = await monitoring_manager.get_available_metrics(service_id=service_id)
            return metrics
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")
    
    # Alert Management Endpoints
    
    @router.post("/alerts/rules", response_model=AlertRule)
    async def create_alert_rule(
        request: AlertRuleRequest,
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Create a new alert rule."""
        try:
            rule = await monitoring_manager.create_alert_rule(
                name=request.name,
                description=request.description,
                service_id=request.service_id,
                metric_name=request.metric_name,
                condition=request.condition,
                threshold=request.threshold,
                severity=request.severity.value,
                enabled=request.enabled,
                notification_channels=request.notification_channels or [],
                evaluation_interval=request.evaluation_interval,
                for_duration=request.for_duration
            )
            
            return AlertRule(**rule)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating alert rule: {str(e)}")
    
    @router.get("/alerts/rules", response_model=List[AlertRule])
    async def get_alert_rules(
        service_id: Optional[str] = Query(None, description="Filter by service ID"),
        enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get list of alert rules."""
        try:
            rules = await monitoring_manager.get_alert_rules(
                service_id=service_id,
                enabled=enabled
            )
            return [AlertRule(**rule) for rule in rules]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting alert rules: {str(e)}")
    
    @router.get("/alerts/rules/{rule_id}", response_model=AlertRule)
    async def get_alert_rule(
        rule_id: str = Path(..., description="Alert rule ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get specific alert rule."""
        try:
            rule = await monitoring_manager.get_alert_rule(rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail="Alert rule not found")
            return AlertRule(**rule)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting alert rule: {str(e)}")
    
    @router.put("/alerts/rules/{rule_id}", response_model=AlertRule)
    async def update_alert_rule(
        rule_id: str = Path(..., description="Alert rule ID"),
        request: AlertRuleRequest = ...,
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Update an alert rule."""
        try:
            rule = await monitoring_manager.update_alert_rule(
                rule_id=rule_id,
                name=request.name,
                description=request.description,
                service_id=request.service_id,
                metric_name=request.metric_name,
                condition=request.condition,
                threshold=request.threshold,
                severity=request.severity.value,
                enabled=request.enabled,
                notification_channels=request.notification_channels or [],
                evaluation_interval=request.evaluation_interval,
                for_duration=request.for_duration
            )
            
            if not rule:
                raise HTTPException(status_code=404, detail="Alert rule not found")
            
            return AlertRule(**rule)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating alert rule: {str(e)}")
    
    @router.delete("/alerts/rules/{rule_id}")
    async def delete_alert_rule(
        rule_id: str = Path(..., description="Alert rule ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Delete an alert rule."""
        try:
            success = await monitoring_manager.delete_alert_rule(rule_id)
            if not success:
                raise HTTPException(status_code=404, detail="Alert rule not found")
            return {"message": "Alert rule deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting alert rule: {str(e)}")
    
    @router.get("/alerts", response_model=List[Alert])
    async def get_alerts(
        status: Optional[AlertStatus] = Query(None, description="Filter by alert status"),
        severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
        service_id: Optional[str] = Query(None, description="Filter by service ID"),
        limit: int = Query(100, description="Maximum number of alerts to return"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get list of active alerts."""
        try:
            alerts = await monitoring_manager.get_alerts(
                status=status.value if status else None,
                severity=severity.value if severity else None,
                service_id=service_id,
                limit=limit
            )
            return [Alert(**alert) for alert in alerts]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting alerts: {str(e)}")
    
    @router.post("/alerts/{alert_id}/acknowledge")
    async def acknowledge_alert(
        alert_id: str = Path(..., description="Alert ID"),
        acknowledged_by: str = Query(..., description="User acknowledging the alert"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Acknowledge an alert."""
        try:
            success = await monitoring_manager.acknowledge_alert(alert_id, acknowledged_by)
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            return {"message": "Alert acknowledged successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")
    
    @router.post("/alerts/{alert_id}/resolve")
    async def resolve_alert(
        alert_id: str = Path(..., description="Alert ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Resolve an alert."""
        try:
            success = await monitoring_manager.resolve_alert(alert_id)
            if not success:
                raise HTTPException(status_code=404, detail="Alert not found")
            return {"message": "Alert resolved successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")
    
    # Dashboard Configuration Endpoints
    
    @router.post("/dashboards", response_model=DashboardConfig)
    async def create_dashboard(
        request: DashboardConfigRequest,
        created_by: Optional[str] = Query(None, description="User creating the dashboard"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Create a new dashboard configuration."""
        try:
            dashboard = await monitoring_manager.create_dashboard(
                name=request.name,
                description=request.description,
                layout=request.layout,
                widgets=request.widgets,
                refresh_interval=request.refresh_interval,
                time_range=request.time_range.value,
                created_by=created_by
            )
            
            return DashboardConfig(**dashboard)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating dashboard: {str(e)}")
    
    @router.get("/dashboards", response_model=List[DashboardConfig])
    async def get_dashboards(
        created_by: Optional[str] = Query(None, description="Filter by creator"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get list of dashboard configurations."""
        try:
            dashboards = await monitoring_manager.get_dashboards(created_by=created_by)
            return [DashboardConfig(**dashboard) for dashboard in dashboards]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting dashboards: {str(e)}")
    
    @router.get("/dashboards/{dashboard_id}", response_model=DashboardConfig)
    async def get_dashboard(
        dashboard_id: str = Path(..., description="Dashboard ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Get specific dashboard configuration."""
        try:
            dashboard = await monitoring_manager.get_dashboard(dashboard_id)
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")
            return DashboardConfig(**dashboard)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error getting dashboard: {str(e)}")
    
    @router.put("/dashboards/{dashboard_id}", response_model=DashboardConfig)
    async def update_dashboard(
        dashboard_id: str = Path(..., description="Dashboard ID"),
        request: DashboardConfigRequest = ...,
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Update a dashboard configuration."""
        try:
            dashboard = await monitoring_manager.update_dashboard(
                dashboard_id=dashboard_id,
                name=request.name,
                description=request.description,
                layout=request.layout,
                widgets=request.widgets,
                refresh_interval=request.refresh_interval,
                time_range=request.time_range.value
            )
            
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")
            
            return DashboardConfig(**dashboard)
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating dashboard: {str(e)}")
    
    @router.delete("/dashboards/{dashboard_id}")
    async def delete_dashboard(
        dashboard_id: str = Path(..., description="Dashboard ID"),
        monitoring_manager: MonitoringManager = Depends(get_monitoring_manager)
    ):
        """Delete a dashboard configuration."""
        try:
            success = await monitoring_manager.delete_dashboard(dashboard_id)
            if not success:
                raise HTTPException(status_code=404, detail="Dashboard not found")
            return {"message": "Dashboard deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting dashboard: {str(e)}")
    
    # Real-time WebSocket endpoints info
    
    @router.get("/websocket/info")
    async def get_websocket_info(
        websocket_manager: WebSocketManager = Depends(get_websocket_manager)
    ):
        """Get WebSocket connection information."""
        return {
            "active_connections": websocket_manager.get_connection_count(),
            "metrics_subscribers": websocket_manager.get_metrics_subscribers_count(),
            "service_status_subscribers": websocket_manager.get_service_status_subscribers_count(),
            "websocket_url": "/ws/monitoring",
            "supported_subscriptions": [
                "metrics",
                "service_status",
                "alerts"
            ]
        }
    
    return router
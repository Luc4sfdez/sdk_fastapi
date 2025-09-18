"""
Log Management API endpoints with WebSocket streaming support.
"""

from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path

from ..core.dependency_container import get_log_manager
from ..logs.log_manager import (
    LogManager, LogEntry, LogLevel, LogSource, LogFilter, 
    LogStreamConfig, LogRetentionPolicy, LogFormat, LogStats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs"])


# Request/Response Models
class LogEntryResponse(BaseModel):
    """Response model for log entries."""
    timestamp: str
    level: str
    service_id: str
    message: str
    source: str
    component: Optional[str] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    tags: List[str] = []


class LogSearchRequest(BaseModel):
    """Request model for log search."""
    service_ids: Optional[List[str]] = None
    levels: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search_text: Optional[str] = None
    regex_pattern: Optional[str] = None
    components: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)
    sort_desc: bool = True


class LogStreamRequest(BaseModel):
    """Request model for log streaming."""
    service_id: str
    client_id: str
    buffer_size: int = Field(default=100, ge=10, le=1000)
    max_rate_per_second: int = Field(default=50, ge=1, le=1000)
    include_historical: bool = False
    historical_limit: int = Field(default=100, ge=1, le=1000)
    filter: Optional[LogSearchRequest] = None


class LogRetentionRequest(BaseModel):
    """Request model for log retention policy."""
    service_id: str
    retention_days: int = Field(default=30, ge=1, le=365)
    max_size_mb: int = Field(default=1000, ge=10, le=10000)
    compression_enabled: bool = True
    archive_path: Optional[str] = None
    cleanup_enabled: bool = True


class LogExportRequest(BaseModel):
    """Request model for log export."""
    format: str = Field(default="json", pattern="^(json|csv|txt|html)$")
    filter: Optional[LogSearchRequest] = None
    filename: Optional[str] = None


class LogStatsResponse(BaseModel):
    """Response model for log statistics."""
    total_entries: int
    entries_by_level: Dict[str, int]
    entries_by_service: Dict[str, int]
    entries_by_hour: Dict[str, int]
    latest_entry: Optional[str] = None
    oldest_entry: Optional[str] = None
    storage_size_mb: float


# WebSocket connection manager
class LogStreamManager:
    """Manages WebSocket connections for log streaming."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_configs: Dict[str, LogStreamConfig] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_configs:
            del self.client_configs[client_id]
        logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_log(self, client_id: str, log_entry: LogEntry):
        """Send log entry to specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                message = {
                    "type": "log_entry",
                    "log": log_entry.to_dict()
                }
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Error sending log to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast_log(self, log_entry: LogEntry):
        """Broadcast log entry to all connected clients."""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                # Check if log matches client's filter
                if client_id in self.client_configs:
                    config = self.client_configs[client_id]
                    if config.service_id != "all" and config.service_id != log_entry.service_id:
                        continue
                
                message = {
                    "type": "log_entry",
                    "log": log_entry.to_dict()
                }
                await websocket.send_text(json.dumps(message, default=str))
                
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)


# Global stream manager
stream_manager = LogStreamManager()


# Log Search and Retrieval Endpoints

@router.get("/search", response_model=List[LogEntryResponse])
async def search_logs(
    service_ids: Optional[str] = Query(None, description="Comma-separated service IDs"),
    levels: Optional[str] = Query(None, description="Comma-separated log levels"),
    sources: Optional[str] = Query(None, description="Comma-separated log sources"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    search_text: Optional[str] = Query(None, description="Text search"),
    regex_pattern: Optional[str] = Query(None, description="Regex pattern search"),
    components: Optional[str] = Query(None, description="Comma-separated components"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    request_id: Optional[str] = Query(None, description="Request ID filter"),
    user_id: Optional[str] = Query(None, description="User ID filter"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_desc: bool = Query(True, description="Sort in descending order"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Search logs with advanced filtering options."""
    try:
        # Parse comma-separated values
        service_ids_list = service_ids.split(',') if service_ids else None
        levels_list = [LogLevel.from_string(l.strip()) for l in levels.split(',')] if levels else None
        sources_list = [LogSource(s.strip()) for s in sources.split(',')] if sources else None
        components_list = components.split(',') if components else None
        tags_list = tags.split(',') if tags else None
        
        # Create filter
        filter_criteria = LogFilter(
            service_ids=service_ids_list,
            levels=levels_list,
            sources=sources_list,
            start_time=start_time,
            end_time=end_time,
            search_text=search_text,
            regex_pattern=regex_pattern,
            components=components_list,
            tags=tags_list,
            request_id=request_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_desc=sort_desc
        )
        
        # Get logs
        logs = await log_manager.get_logs(filter_criteria)
        
        # Convert to response format
        return [
            LogEntryResponse(
                timestamp=log.timestamp.isoformat(),
                level=log.level.level_name,
                service_id=log.service_id,
                message=log.message,
                source=log.source.value,
                component=log.component,
                thread_id=log.thread_id,
                request_id=log.request_id,
                user_id=log.user_id,
                metadata=log.metadata,
                tags=log.tags
            )
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search logs"
        )


@router.post("/search", response_model=List[LogEntryResponse])
async def search_logs_post(
    request: LogSearchRequest,
    log_manager: LogManager = Depends(get_log_manager)
):
    """Search logs using POST request with detailed filter options."""
    try:
        # Convert string levels to LogLevel enum
        levels_enum = None
        if request.levels:
            levels_enum = [LogLevel.from_string(level) for level in request.levels]
        
        # Convert string sources to LogSource enum
        sources_enum = None
        if request.sources:
            sources_enum = [LogSource(source) for source in request.sources]
        
        # Create filter
        filter_criteria = LogFilter(
            service_ids=request.service_ids,
            levels=levels_enum,
            sources=sources_enum,
            start_time=request.start_time,
            end_time=request.end_time,
            search_text=request.search_text,
            regex_pattern=request.regex_pattern,
            components=request.components,
            tags=request.tags,
            request_id=request.request_id,
            user_id=request.user_id,
            limit=request.limit,
            offset=request.offset,
            sort_desc=request.sort_desc
        )
        
        # Get logs
        logs = await log_manager.get_logs(filter_criteria)
        
        # Convert to response format
        return [
            LogEntryResponse(
                timestamp=log.timestamp.isoformat(),
                level=log.level.level_name,
                service_id=log.service_id,
                message=log.message,
                source=log.source.value,
                component=log.component,
                thread_id=log.thread_id,
                request_id=log.request_id,
                user_id=log.user_id,
                metadata=log.metadata,
                tags=log.tags
            )
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search logs"
        )


@router.get("/services", response_model=List[str])
async def list_services(
    log_manager: LogManager = Depends(get_log_manager)
):
    """List all services that have logs."""
    try:
        services = await log_manager.get_service_list()
        return services
        
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list services"
        )


@router.get("/services/{service_id}/tail", response_model=List[LogEntryResponse])
async def tail_service_logs(
    service_id: str,
    lines: int = Query(100, ge=1, le=1000, description="Number of lines to tail"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Get the latest logs from a service (tail functionality)."""
    try:
        logs = await log_manager.tail_service_logs(service_id, lines)
        
        return [
            LogEntryResponse(
                timestamp=log.timestamp.isoformat(),
                level=log.level.level_name,
                service_id=log.service_id,
                message=log.message,
                source=log.source.value,
                component=log.component,
                thread_id=log.thread_id,
                request_id=log.request_id,
                user_id=log.user_id,
                metadata=log.metadata,
                tags=log.tags
            )
            for log in logs
        ]
        
    except Exception as e:
        logger.error(f"Error tailing logs for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to tail service logs"
        )


# Log Export Endpoints

@router.get("/export")
async def export_logs(
    format: str = Query("json", pattern="^(json|csv|txt|html)$"),
    service_ids: Optional[str] = Query(None),
    levels: Optional[str] = Query(None),
    sources: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    search_text: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=100000),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Export logs in specified format."""
    try:
        # Parse parameters
        service_ids_list = service_ids.split(',') if service_ids else None
        levels_list = [LogLevel.from_string(l.strip()) for l in levels.split(',')] if levels else None
        sources_list = [LogSource(s.strip()) for s in sources.split(',')] if sources else None
        
        # Create filter
        filter_criteria = LogFilter(
            service_ids=service_ids_list,
            levels=levels_list,
            sources=sources_list,
            start_time=start_time,
            end_time=end_time,
            search_text=search_text,
            limit=limit
        )
        
        # Export logs
        export_format = LogFormat(format)
        export_path = await log_manager.export_logs(filter_criteria, export_format)
        
        if not export_path or not Path(export_path).exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export logs"
            )
        
        # Return file
        return FileResponse(
            path=export_path,
            filename=Path(export_path).name,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export logs"
        )


@router.post("/export")
async def export_logs_post(
    request: LogExportRequest,
    log_manager: LogManager = Depends(get_log_manager)
):
    """Export logs using POST request."""
    try:
        # Create filter from request
        filter_criteria = LogFilter(limit=10000)  # Default filter
        
        if request.filter:
            levels_enum = None
            if request.filter.levels:
                levels_enum = [LogLevel.from_string(level) for level in request.filter.levels]
            
            sources_enum = None
            if request.filter.sources:
                sources_enum = [LogSource(source) for source in request.filter.sources]
            
            filter_criteria = LogFilter(
                service_ids=request.filter.service_ids,
                levels=levels_enum,
                sources=sources_enum,
                start_time=request.filter.start_time,
                end_time=request.filter.end_time,
                search_text=request.filter.search_text,
                regex_pattern=request.filter.regex_pattern,
                components=request.filter.components,
                tags=request.filter.tags,
                request_id=request.filter.request_id,
                user_id=request.filter.user_id,
                limit=request.filter.limit
            )
        
        # Export logs
        export_format = LogFormat(request.format)
        export_path = await log_manager.export_logs(filter_criteria, export_format)
        
        if not export_path or not Path(export_path).exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to export logs"
            )
        
        # Return file
        filename = request.filename or Path(export_path).name
        return FileResponse(
            path=export_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export logs"
        )


# Log Statistics Endpoints

@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    service_id: Optional[str] = Query(None, description="Service ID filter"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Get log statistics."""
    try:
        stats = await log_manager.get_log_stats(service_id)
        
        return LogStatsResponse(
            total_entries=stats.total_entries,
            entries_by_level=stats.entries_by_level,
            entries_by_service=stats.entries_by_service,
            entries_by_hour=stats.entries_by_hour,
            latest_entry=stats.latest_entry.isoformat() if stats.latest_entry else None,
            oldest_entry=stats.oldest_entry.isoformat() if stats.oldest_entry else None,
            storage_size_mb=stats.storage_size_mb
        )
        
    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get log statistics"
        )


@router.get("/services/{service_id}/levels", response_model=List[str])
async def get_service_log_levels(
    service_id: str,
    log_manager: LogManager = Depends(get_log_manager)
):
    """Get available log levels for a service."""
    try:
        levels = await log_manager.get_log_levels_for_service(service_id)
        return [level.level_name for level in levels]
        
    except Exception as e:
        logger.error(f"Error getting log levels for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service log levels"
        )


# Log Management Endpoints

@router.post("/services/{service_id}/collect")
async def collect_service_logs(
    service_id: str,
    log_source: str = Query(..., description="Log source (file path, docker://, journalctl://)"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Collect logs from a service source."""
    try:
        count = await log_manager.collect_service_logs(service_id, log_source)
        
        return {
            "message": f"Collected {count} log entries",
            "service_id": service_id,
            "source": log_source,
            "count": count
        }
        
    except Exception as e:
        logger.error(f"Error collecting logs for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect service logs"
        )


@router.post("/services/{service_id}/generate-sample")
async def generate_sample_logs(
    service_id: str,
    count: int = Query(100, ge=1, le=1000, description="Number of sample logs to generate"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Generate sample logs for testing purposes."""
    try:
        generated = await log_manager.generate_sample_logs(service_id, count)
        
        return {
            "message": f"Generated {generated} sample log entries",
            "service_id": service_id,
            "count": generated
        }
        
    except Exception as e:
        logger.error(f"Error generating sample logs for service {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate sample logs"
        )


# Log Retention Endpoints

@router.post("/retention")
async def set_retention_policy(
    request: LogRetentionRequest,
    log_manager: LogManager = Depends(get_log_manager)
):
    """Set log retention policy for a service."""
    try:
        policy = LogRetentionPolicy(
            service_id=request.service_id,
            retention_days=request.retention_days,
            max_size_mb=request.max_size_mb,
            compression_enabled=request.compression_enabled,
            archive_path=request.archive_path,
            cleanup_enabled=request.cleanup_enabled
        )
        
        success = await log_manager.set_retention_policy(policy)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to set retention policy"
            )
        
        return {
            "message": "Retention policy set successfully",
            "service_id": request.service_id,
            "retention_days": request.retention_days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting retention policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set retention policy"
        )


@router.post("/cleanup")
async def cleanup_old_logs(
    service_id: Optional[str] = Query(None, description="Service ID (all services if not specified)"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Clean up old logs based on retention policies."""
    try:
        cleanup_stats = await log_manager.cleanup_old_logs(service_id)
        
        return {
            "message": "Log cleanup completed",
            "cleanup_stats": cleanup_stats,
            "total_removed": sum(cleanup_stats.values())
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup logs"
        )


@router.post("/services/{service_id}/archive")
async def archive_logs(
    service_id: str,
    start_date: datetime = Query(..., description="Start date for archival"),
    end_date: datetime = Query(..., description="End date for archival"),
    log_manager: LogManager = Depends(get_log_manager)
):
    """Archive logs for a specific time period."""
    try:
        archive_path = await log_manager.archive_logs(service_id, start_date, end_date)
        
        if not archive_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to archive logs"
            )
        
        return {
            "message": "Logs archived successfully",
            "service_id": service_id,
            "archive_path": archive_path,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive logs"
        )


# WebSocket Streaming Endpoint

@router.websocket("/stream")
async def websocket_log_stream(
    websocket: WebSocket,
    log_manager: LogManager = Depends(get_log_manager)
):
    """WebSocket endpoint for real-time log streaming."""
    client_id = f"ws_{id(websocket)}"
    
    try:
        # Accept connection
        await stream_manager.connect(websocket, client_id)
        
        # Wait for initial configuration
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        
        # Create stream configuration
        stream_config = LogStreamConfig(
            service_id=config.get("service_id", "all"),
            client_id=client_id,
            buffer_size=config.get("buffer_size", 100),
            include_historical=config.get("include_historical", False),
            historical_limit=config.get("historical_limit", 100)
        )
        
        # Store client configuration
        stream_manager.client_configs[client_id] = stream_config
        
        # Start log stream
        success = await log_manager.start_log_stream(stream_config)
        if not success:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Failed to start log stream"
            }))
            return
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "service_id": stream_config.service_id
        }))
        
        # Stream logs
        while True:
            try:
                # Get logs from stream
                logs = await log_manager.get_stream_logs(client_id, timeout=1.0)
                
                # Send logs to client
                for log in logs:
                    await stream_manager.send_log(client_id, log)
                
                # Check for client messages (configuration updates, etc.)
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    # Handle client messages if needed
                except asyncio.TimeoutError:
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket stream: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        stream_manager.disconnect(client_id)
        await log_manager.stop_log_stream(client_id)


# Health and Status Endpoints

@router.get("/health")
async def log_system_health(
    log_manager: LogManager = Depends(get_log_manager)
):
    """Get log system health status."""
    try:
        health = await log_manager.health_check()
        
        return {
            "status": "healthy" if health else "unhealthy",
            "log_manager": health,
            "active_streams": len(stream_manager.active_connections),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking log system health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/status")
async def log_system_status(
    log_manager: LogManager = Depends(get_log_manager)
):
    """Get detailed log system status."""
    try:
        stats = await log_manager.get_log_stats()
        services = await log_manager.get_service_list()
        
        return {
            "services": len(services),
            "total_logs": stats.total_entries,
            "active_streams": len(stream_manager.active_connections),
            "connected_clients": list(stream_manager.active_connections.keys()),
            "latest_entry": stats.latest_entry.isoformat() if stats.latest_entry else None,
            "storage_size_mb": stats.storage_size_mb,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting log system status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get log system status"
        )
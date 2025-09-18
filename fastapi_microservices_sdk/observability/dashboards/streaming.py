"""
Dashboard Streaming - Real-time dashboard data streaming

This module provides real-time streaming capabilities for dashboards
with WebSocket support and live data updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json
import uuid

from .exceptions import DashboardStreamingError

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Streaming configuration."""
    enabled: bool = True
    real_time_updates: bool = True
    auto_refresh_interval: int = 30
    max_connections: int = 100
    buffer_size: int = 1000
    compression_enabled: bool = True


class DashboardStreaming:
    """
    Real-time dashboard streaming manager.
    
    Provides functionality for:
    - WebSocket connections management
    - Real-time data streaming
    - Live dashboard updates
    - Connection monitoring
    """
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.is_initialized = False
        
        logger.info("Dashboard streaming manager initialized")
    
    async def initialize(self) -> None:
        """Initialize streaming manager."""
        if self.is_initialized:
            return
        
        try:
            self.is_initialized = True
            logger.info("Dashboard streaming manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard streaming: {e}")
            raise DashboardStreamingError(f"Streaming initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown streaming manager."""
        if not self.is_initialized:
            return
        
        try:
            # Close all active streams
            for stream_id in list(self.active_streams.keys()):
                await self.stop_stream(stream_id)
            
            self.is_initialized = False
            logger.info("Dashboard streaming manager shutdown successfully")
            
        except Exception as e:
            logger.error(f"Error during streaming manager shutdown: {e}")
    
    async def start_stream(
        self,
        dashboard_id: str,
        config: Dict[str, Any],
        websocket: Optional[Any] = None
    ) -> str:
        """
        Start dashboard streaming.
        
        Args:
            dashboard_id: Dashboard ID
            config: Dashboard configuration
            websocket: WebSocket connection
            
        Returns:
            Stream ID
        """
        try:
            # Check connection limit
            if len(self.active_streams) >= self.config.max_connections:
                raise DashboardStreamingError("Maximum connections reached")
            
            # Generate stream ID
            stream_id = str(uuid.uuid4())
            
            # Create stream
            stream = {
                "id": stream_id,
                "dashboard_id": dashboard_id,
                "config": config,
                "websocket": websocket,
                "started_at": datetime.utcnow(),
                "last_update": datetime.utcnow(),
                "update_count": 0,
                "is_active": True
            }
            
            self.active_streams[stream_id] = stream
            
            if websocket:
                self.websocket_connections[stream_id] = websocket
            
            # Start streaming task
            asyncio.create_task(self._stream_dashboard_data(stream_id))
            
            logger.info(f"Dashboard stream started: {stream_id} for dashboard {dashboard_id}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Failed to start dashboard stream: {e}")
            raise DashboardStreamingError(f"Stream start failed: {e}")
    
    async def stop_stream(self, stream_id: str) -> None:
        """
        Stop dashboard streaming.
        
        Args:
            stream_id: Stream ID
        """
        if stream_id not in self.active_streams:
            return
        
        try:
            # Mark stream as inactive
            self.active_streams[stream_id]["is_active"] = False
            
            # Close WebSocket if exists
            if stream_id in self.websocket_connections:
                websocket = self.websocket_connections[stream_id]
                if hasattr(websocket, 'close'):
                    await websocket.close()
                del self.websocket_connections[stream_id]
            
            # Remove stream
            del self.active_streams[stream_id]
            
            logger.info(f"Dashboard stream stopped: {stream_id}")
            
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
    
    async def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stream status.
        
        Args:
            stream_id: Stream ID
            
        Returns:
            Stream status or None if not found
        """
        if stream_id not in self.active_streams:
            return None
        
        stream = self.active_streams[stream_id]
        return {
            "id": stream["id"],
            "dashboard_id": stream["dashboard_id"],
            "started_at": stream["started_at"].isoformat(),
            "last_update": stream["last_update"].isoformat(),
            "update_count": stream["update_count"],
            "is_active": stream["is_active"],
            "has_websocket": stream_id in self.websocket_connections
        }
    
    async def _stream_dashboard_data(self, stream_id: str) -> None:
        """Stream dashboard data in real-time."""
        if stream_id not in self.active_streams:
            return
        
        stream = self.active_streams[stream_id]
        
        try:
            while stream["is_active"]:
                # Generate mock streaming data
                data = await self._generate_stream_data(stream["dashboard_id"])
                
                # Send data via WebSocket if available
                if stream_id in self.websocket_connections:
                    websocket = self.websocket_connections[stream_id]
                    await self._send_websocket_data(websocket, data)
                
                # Update stream metadata
                stream["last_update"] = datetime.utcnow()
                stream["update_count"] += 1
                
                # Wait for next update
                await asyncio.sleep(self.config.auto_refresh_interval)
                
        except Exception as e:
            logger.error(f"Error in stream {stream_id}: {e}")
            await self.stop_stream(stream_id)
    
    async def _generate_stream_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Generate streaming data for dashboard."""
        # Mock streaming data - in real implementation, this would
        # fetch real-time data from various sources
        
        import random
        import time
        
        timestamp = int(time.time() * 1000)
        
        return {
            "dashboard_id": dashboard_id,
            "timestamp": timestamp,
            "data": {
                "metrics": {
                    "cpu_usage": random.uniform(20, 80),
                    "memory_usage": random.uniform(30, 90),
                    "request_rate": random.uniform(100, 1000),
                    "error_rate": random.uniform(0, 5)
                },
                "alerts": [],
                "status": "healthy"
            }
        }
    
    async def _send_websocket_data(self, websocket: Any, data: Dict[str, Any]) -> None:
        """Send data via WebSocket."""
        try:
            message = json.dumps(data)
            
            # Compress if enabled and supported
            if self.config.compression_enabled:
                # Mock compression - in real implementation, use actual compression
                pass
            
            # Send message
            if hasattr(websocket, 'send_text'):
                await websocket.send_text(message)
            elif hasattr(websocket, 'send'):
                await websocket.send(message)
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket data: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get streaming manager status."""
        return {
            "initialized": self.is_initialized,
            "active_streams": len(self.active_streams),
            "websocket_connections": len(self.websocket_connections),
            "max_connections": self.config.max_connections,
            "config": {
                "enabled": self.config.enabled,
                "real_time_updates": self.config.real_time_updates,
                "auto_refresh_interval": self.config.auto_refresh_interval,
                "compression_enabled": self.config.compression_enabled
            }
        }
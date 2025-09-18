"""
Dashboard Manager - Central dashboard management and coordination

This module provides the central dashboard management system that coordinates
all dashboard-related functionality including creation, management, streaming,
security, and visualization.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import uuid

from .builder import DashboardBuilder, DashboardConfig
from .visualization import VisualizationEngine
from .templates import DashboardTemplateManager
from .security import DashboardSecurity
from .streaming import DashboardStreaming
from .exporter import DashboardExporter
from .exceptions import (
    DashboardError,
    DashboardNotFoundError,
    DashboardPermissionError
)

logger = logging.getLogger(__name__)


class Dashboard:
    """Represents a dashboard with its configuration and metadata."""
    
    def __init__(
        self,
        id: str,
        name: str,
        config: Dict[str, Any],
        owner: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.name = name
        self.config = config
        self.owner = owner
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.version = 1
        self.tags: List[str] = []
        self.shared_with: List[str] = []
        self.is_public = False
        self.is_template = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "config": self.config,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "tags": self.tags,
            "shared_with": self.shared_with,
            "is_public": self.is_public,
            "is_template": self.is_template
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dashboard":
        """Create dashboard from dictionary."""
        dashboard = cls(
            id=data["id"],
            name=data["name"],
            config=data["config"],
            owner=data["owner"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
        dashboard.version = data.get("version", 1)
        dashboard.tags = data.get("tags", [])
        dashboard.shared_with = data.get("shared_with", [])
        dashboard.is_public = data.get("is_public", False)
        dashboard.is_template = data.get("is_template", False)
        return dashboard


class DashboardManager:
    """
    Central dashboard management system.
    
    Coordinates all dashboard functionality including creation, management,
    streaming, security, and visualization.
    """
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self.dashboards: Dict[str, Dashboard] = {}
        self.dashboard_versions: Dict[str, List[Dashboard]] = {}
        
        # Components
        self.builder = DashboardBuilder(config)
        self.visualization_engine = VisualizationEngine()
        self.template_manager: Optional[DashboardTemplateManager] = None
        self.security: Optional[DashboardSecurity] = None
        self.streaming: Optional[DashboardStreaming] = None
        self.exporter: Optional[DashboardExporter] = None
        
        # State
        self.is_initialized = False
        self.active_streams: Dict[str, Any] = {}
        
        logger.info("Dashboard manager initialized")
    
    async def initialize(self) -> None:
        """Initialize dashboard manager and all components."""
        if self.is_initialized:
            return
        
        try:
            # Initialize components
            await self.builder.initialize()
            await self.visualization_engine.initialize()
            
            if self.template_manager:
                await self.template_manager.initialize()
            
            if self.security:
                await self.security.initialize()
            
            if self.streaming:
                await self.streaming.initialize()
            
            if self.exporter:
                await self.exporter.initialize()
            
            # Load default templates if available
            if self.template_manager:
                await self._load_default_templates()
            
            self.is_initialized = True
            logger.info("Dashboard manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard manager: {e}")
            raise DashboardError(f"Initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown dashboard manager and cleanup resources."""
        if not self.is_initialized:
            return
        
        try:
            # Stop all active streams
            for stream_id in list(self.active_streams.keys()):
                await self.stop_dashboard_stream(stream_id)
            
            # Shutdown components
            if self.streaming:
                await self.streaming.shutdown()
            
            if self.exporter:
                await self.exporter.shutdown()
            
            await self.visualization_engine.shutdown()
            await self.builder.shutdown()
            
            self.is_initialized = False
            logger.info("Dashboard manager shutdown successfully")
            
        except Exception as e:
            logger.error(f"Error during dashboard manager shutdown: {e}")
    
    def set_templates(self, template_manager: DashboardTemplateManager) -> None:
        """Set dashboard template manager."""
        self.template_manager = template_manager
    
    def set_security(self, security: DashboardSecurity) -> None:
        """Set dashboard security manager."""
        self.security = security
    
    def set_streaming(self, streaming: DashboardStreaming) -> None:
        """Set dashboard streaming manager."""
        self.streaming = streaming
    
    def set_exporter(self, exporter: DashboardExporter) -> None:
        """Set dashboard exporter."""
        self.exporter = exporter
    
    async def create_dashboard(
        self,
        name: str,
        config: Dict[str, Any],
        owner: str,
        template_id: Optional[str] = None
    ) -> Dashboard:
        """
        Create a new dashboard.
        
        Args:
            name: Dashboard name
            config: Dashboard configuration
            owner: Dashboard owner
            template_id: Optional template to use
            
        Returns:
            Created dashboard
        """
        try:
            # Generate unique ID
            dashboard_id = str(uuid.uuid4())
            
            # Use template if specified
            if template_id and self.template_manager:
                template = await self.template_manager.get_template(template_id)
                if template:
                    # Merge template config with provided config
                    template_config = template.config.copy()
                    template_config.update(config)
                    config = template_config
            
            # Validate configuration
            await self.builder.validate_config(config)
            
            # Create dashboard
            dashboard = Dashboard(
                id=dashboard_id,
                name=name,
                config=config,
                owner=owner
            )
            
            # Store dashboard
            self.dashboards[dashboard_id] = dashboard
            self.dashboard_versions[dashboard_id] = [dashboard]
            
            logger.info(f"Dashboard created: {dashboard_id} ({name})")
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            raise DashboardError(f"Dashboard creation failed: {e}")
    
    async def get_dashboard(self, dashboard_id: str, user: Optional[str] = None) -> Dashboard:
        """
        Get dashboard by ID.
        
        Args:
            dashboard_id: Dashboard ID
            user: Optional user for permission check
            
        Returns:
            Dashboard instance
        """
        if dashboard_id not in self.dashboards:
            raise DashboardNotFoundError(f"Dashboard not found: {dashboard_id}")
        
        dashboard = self.dashboards[dashboard_id]
        
        # Check permissions
        if self.security and user:
            if not await self.security.can_view_dashboard(user, dashboard):
                raise DashboardPermissionError(f"No permission to view dashboard: {dashboard_id}")
        
        return dashboard
    
    async def update_dashboard(
        self,
        dashboard_id: str,
        config: Dict[str, Any],
        user: Optional[str] = None
    ) -> Dashboard:
        """
        Update dashboard configuration.
        
        Args:
            dashboard_id: Dashboard ID
            config: New configuration
            user: User making the update
            
        Returns:
            Updated dashboard
        """
        dashboard = await self.get_dashboard(dashboard_id, user)
        
        # Check permissions
        if self.security and user:
            if not await self.security.can_edit_dashboard(user, dashboard):
                raise DashboardPermissionError(f"No permission to edit dashboard: {dashboard_id}")
        
        # Validate configuration
        await self.builder.validate_config(config)
        
        # Create new version
        new_dashboard = Dashboard(
            id=dashboard.id,
            name=dashboard.name,
            config=config,
            owner=dashboard.owner,
            created_at=dashboard.created_at
        )
        new_dashboard.version = dashboard.version + 1
        new_dashboard.tags = dashboard.tags.copy()
        new_dashboard.shared_with = dashboard.shared_with.copy()
        new_dashboard.is_public = dashboard.is_public
        
        # Store new version
        self.dashboards[dashboard_id] = new_dashboard
        self.dashboard_versions[dashboard_id].append(new_dashboard)
        
        logger.info(f"Dashboard updated: {dashboard_id} (v{new_dashboard.version})")
        return new_dashboard
    
    async def delete_dashboard(self, dashboard_id: str, user: Optional[str] = None) -> None:
        """
        Delete dashboard.
        
        Args:
            dashboard_id: Dashboard ID
            user: User requesting deletion
        """
        dashboard = await self.get_dashboard(dashboard_id, user)
        
        # Check permissions
        if self.security and user:
            if not await self.security.can_delete_dashboard(user, dashboard):
                raise DashboardPermissionError(f"No permission to delete dashboard: {dashboard_id}")
        
        # Stop any active streams
        if dashboard_id in self.active_streams:
            await self.stop_dashboard_stream(dashboard_id)
        
        # Remove dashboard
        del self.dashboards[dashboard_id]
        del self.dashboard_versions[dashboard_id]
        
        logger.info(f"Dashboard deleted: {dashboard_id}")
    
    async def list_dashboards(
        self,
        user: Optional[str] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None
    ) -> List[Dashboard]:
        """
        List dashboards with optional filtering.
        
        Args:
            user: User requesting list (for permission filtering)
            tags: Filter by tags
            owner: Filter by owner
            
        Returns:
            List of dashboards
        """
        dashboards = []
        
        for dashboard in self.dashboards.values():
            # Check permissions
            if self.security and user:
                if not await self.security.can_view_dashboard(user, dashboard):
                    continue
            
            # Apply filters
            if tags and not any(tag in dashboard.tags for tag in tags):
                continue
            
            if owner and dashboard.owner != owner:
                continue
            
            dashboards.append(dashboard)
        
        return dashboards
    
    async def render_dashboard(
        self,
        dashboard_id: str,
        user: Optional[str] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render dashboard with current data.
        
        Args:
            dashboard_id: Dashboard ID
            user: User requesting render
            time_range: Optional time range filter
            
        Returns:
            Rendered dashboard data
        """
        dashboard = await self.get_dashboard(dashboard_id, user)
        
        # Build dashboard
        rendered = await self.builder.build_dashboard(dashboard.config, time_range)
        
        # Add metadata
        rendered["metadata"] = {
            "id": dashboard.id,
            "name": dashboard.name,
            "version": dashboard.version,
            "updated_at": dashboard.updated_at.isoformat(),
            "rendered_at": datetime.utcnow().isoformat()
        }
        
        return rendered
    
    async def start_dashboard_stream(
        self,
        dashboard_id: str,
        user: Optional[str] = None,
        websocket: Optional[Any] = None
    ) -> str:
        """
        Start real-time dashboard streaming.
        
        Args:
            dashboard_id: Dashboard ID
            user: User requesting stream
            websocket: WebSocket connection
            
        Returns:
            Stream ID
        """
        if not self.streaming:
            raise DashboardError("Streaming not enabled")
        
        dashboard = await self.get_dashboard(dashboard_id, user)
        
        # Start stream
        stream_id = await self.streaming.start_stream(
            dashboard_id=dashboard_id,
            config=dashboard.config,
            websocket=websocket
        )
        
        self.active_streams[stream_id] = {
            "dashboard_id": dashboard_id,
            "user": user,
            "started_at": datetime.utcnow()
        }
        
        logger.info(f"Dashboard stream started: {stream_id} for dashboard {dashboard_id}")
        return stream_id
    
    async def stop_dashboard_stream(self, stream_id: str) -> None:
        """
        Stop dashboard streaming.
        
        Args:
            stream_id: Stream ID
        """
        if not self.streaming:
            return
        
        if stream_id in self.active_streams:
            await self.streaming.stop_stream(stream_id)
            del self.active_streams[stream_id]
            logger.info(f"Dashboard stream stopped: {stream_id}")
    
    async def export_dashboard(
        self,
        dashboard_id: str,
        format: str,
        user: Optional[str] = None
    ) -> bytes:
        """
        Export dashboard in specified format.
        
        Args:
            dashboard_id: Dashboard ID
            format: Export format (json, pdf, png, etc.)
            user: User requesting export
            
        Returns:
            Exported dashboard data
        """
        if not self.exporter:
            raise DashboardError("Export not enabled")
        
        dashboard = await self.get_dashboard(dashboard_id, user)
        
        # Render dashboard
        rendered = await self.render_dashboard(dashboard_id, user)
        
        # Export
        return await self.exporter.export_dashboard(rendered, format)
    
    async def share_dashboard(
        self,
        dashboard_id: str,
        users: List[str],
        permissions: List[str],
        owner: str
    ) -> None:
        """
        Share dashboard with users.
        
        Args:
            dashboard_id: Dashboard ID
            users: Users to share with
            permissions: Permissions to grant
            owner: Dashboard owner
        """
        dashboard = await self.get_dashboard(dashboard_id, owner)
        
        if dashboard.owner != owner:
            raise DashboardPermissionError("Only owner can share dashboard")
        
        # Update sharing
        dashboard.shared_with.extend(users)
        dashboard.updated_at = datetime.utcnow()
        
        # Update security permissions if available
        if self.security:
            for user in users:
                await self.security.grant_dashboard_permissions(
                    user, dashboard_id, permissions
                )
        
        logger.info(f"Dashboard shared: {dashboard_id} with {len(users)} users")
    
    async def get_dashboard_analytics(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Get dashboard usage analytics.
        
        Args:
            dashboard_id: Dashboard ID
            
        Returns:
            Analytics data
        """
        dashboard = await self.get_dashboard(dashboard_id)
        
        # Basic analytics
        analytics = {
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
            "version": dashboard.version,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
            "views": 0,  # Would be tracked in real implementation
            "active_streams": len([s for s in self.active_streams.values() 
                                 if s["dashboard_id"] == dashboard_id]),
            "shared_with_count": len(dashboard.shared_with),
            "is_public": dashboard.is_public
        }
        
        return analytics
    
    async def _load_default_templates(self) -> None:
        """Load default dashboard templates."""
        if not self.template_manager:
            return
        
        try:
            templates = await self.template_manager.get_default_templates()
            logger.info(f"Loaded {len(templates)} default dashboard templates")
        except Exception as e:
            logger.warning(f"Failed to load default templates: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get dashboard manager status."""
        return {
            "initialized": self.is_initialized,
            "total_dashboards": len(self.dashboards),
            "active_streams": len(self.active_streams),
            "components": {
                "builder": self.builder is not None,
                "visualization_engine": self.visualization_engine is not None,
                "template_manager": self.template_manager is not None,
                "security": self.security is not None,
                "streaming": self.streaming is not None,
                "exporter": self.exporter is not None
            }
        }
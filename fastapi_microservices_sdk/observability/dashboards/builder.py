"""
Dashboard Builder - Custom dashboard creation and configuration

This module provides the dashboard builder system for creating and configuring
custom dashboards with drag-and-drop interface support and validation.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from .exceptions import DashboardConfigError, VisualizationError

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """Dashboard layout types."""
    GRID = "grid"
    FLEX = "flex"
    ABSOLUTE = "absolute"
    RESPONSIVE = "responsive"


class ComponentType(Enum):
    """Dashboard component types."""
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    TEXT = "text"
    IMAGE = "image"
    IFRAME = "iframe"
    CUSTOM = "custom"


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    streaming_enabled: bool = True
    real_time_updates: bool = True
    auto_refresh_interval: int = 30
    max_data_points: int = 1000
    cache_enabled: bool = True
    cache_ttl: int = 300
    security_enabled: bool = True
    export_enabled: bool = True
    mobile_responsive: bool = True
    theme: str = "default"
    layout_type: LayoutType = LayoutType.GRID
    grid_columns: int = 12
    grid_rows: int = 20
    component_spacing: int = 8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "streaming_enabled": self.streaming_enabled,
            "real_time_updates": self.real_time_updates,
            "auto_refresh_interval": self.auto_refresh_interval,
            "max_data_points": self.max_data_points,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "security_enabled": self.security_enabled,
            "export_enabled": self.export_enabled,
            "mobile_responsive": self.mobile_responsive,
            "theme": self.theme,
            "layout_type": self.layout_type.value,
            "grid_columns": self.grid_columns,
            "grid_rows": self.grid_rows,
            "component_spacing": self.component_spacing
        }


@dataclass
class ComponentConfig:
    """Dashboard component configuration."""
    id: str
    type: ComponentType
    title: str
    position: Dict[str, int]  # x, y, width, height
    data_source: str
    query: str
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: Optional[int] = None
    cache_enabled: bool = True
    visible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "position": self.position,
            "data_source": self.data_source,
            "query": self.query,
            "visualization_config": self.visualization_config,
            "refresh_interval": self.refresh_interval,
            "cache_enabled": self.cache_enabled,
            "visible": self.visible
        }


class DashboardBuilder:
    """
    Dashboard builder for creating and configuring custom dashboards.
    
    Provides functionality for:
    - Dashboard configuration validation
    - Component management
    - Layout management
    - Data source integration
    - Real-time dashboard building
    """
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self.data_sources: Dict[str, Any] = {}
        self.component_templates: Dict[str, Dict[str, Any]] = {}
        self.is_initialized = False
        
        logger.info("Dashboard builder initialized")
    
    async def initialize(self) -> None:
        """Initialize dashboard builder."""
        if self.is_initialized:
            return
        
        try:
            # Load component templates
            await self._load_component_templates()
            
            # Initialize data sources
            await self._initialize_data_sources()
            
            self.is_initialized = True
            logger.info("Dashboard builder initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dashboard builder: {e}")
            raise DashboardConfigError(f"Builder initialization failed: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown dashboard builder."""
        if not self.is_initialized:
            return
        
        try:
            # Cleanup data sources
            for source in self.data_sources.values():
                if hasattr(source, 'close'):
                    await source.close()
            
            self.is_initialized = False
            logger.info("Dashboard builder shutdown successfully")
            
        except Exception as e:
            logger.error(f"Error during dashboard builder shutdown: {e}")
    
    async def validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate dashboard configuration.
        
        Args:
            config: Dashboard configuration to validate
            
        Raises:
            DashboardConfigError: If configuration is invalid
        """
        try:
            # Validate required fields
            required_fields = ["layout", "components"]
            for field in required_fields:
                if field not in config:
                    raise DashboardConfigError(f"Missing required field: {field}")
            
            # Validate layout
            await self._validate_layout(config["layout"])
            
            # Validate components
            await self._validate_components(config["components"])
            
            # Validate data sources
            await self._validate_data_sources(config)
            
            logger.debug("Dashboard configuration validated successfully")
            
        except Exception as e:
            logger.error(f"Dashboard configuration validation failed: {e}")
            raise DashboardConfigError(f"Configuration validation failed: {e}")
    
    async def build_dashboard(
        self,
        config: Dict[str, Any],
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build dashboard with current data.
        
        Args:
            config: Dashboard configuration
            time_range: Optional time range filter
            
        Returns:
            Built dashboard with data
        """
        try:
            # Validate configuration
            await self.validate_config(config)
            
            # Build layout
            layout = await self._build_layout(config["layout"])
            
            # Build components with data
            components = await self._build_components(
                config["components"], 
                time_range
            )
            
            # Assemble dashboard
            dashboard = {
                "layout": layout,
                "components": components,
                "config": self.config.to_dict(),
                "built_at": datetime.utcnow().isoformat(),
                "time_range": time_range
            }
            
            logger.debug("Dashboard built successfully")
            return dashboard
            
        except Exception as e:
            logger.error(f"Dashboard build failed: {e}")
            raise DashboardConfigError(f"Dashboard build failed: {e}")
    
    async def create_component(
        self,
        component_type: ComponentType,
        title: str,
        position: Dict[str, int],
        data_source: str,
        query: str,
        **kwargs
    ) -> ComponentConfig:
        """
        Create a new dashboard component.
        
        Args:
            component_type: Type of component
            title: Component title
            position: Component position and size
            data_source: Data source name
            query: Data query
            **kwargs: Additional component configuration
            
        Returns:
            Component configuration
        """
        import uuid
        
        component_id = str(uuid.uuid4())
        
        component = ComponentConfig(
            id=component_id,
            type=component_type,
            title=title,
            position=position,
            data_source=data_source,
            query=query,
            **kwargs
        )
        
        # Validate component
        await self._validate_component(component)
        
        logger.debug(f"Component created: {component_id} ({component_type.value})")
        return component
    
    async def update_component(
        self,
        component_id: str,
        updates: Dict[str, Any]
    ) -> ComponentConfig:
        """
        Update component configuration.
        
        Args:
            component_id: Component ID
            updates: Configuration updates
            
        Returns:
            Updated component configuration
        """
        # This would typically load from storage
        # For now, create a mock component for demonstration
        component = ComponentConfig(
            id=component_id,
            type=ComponentType.CHART,
            title="Updated Component",
            position={"x": 0, "y": 0, "width": 6, "height": 4},
            data_source="metrics",
            query="SELECT * FROM metrics"
        )
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(component, key):
                setattr(component, key, value)
        
        # Validate updated component
        await self._validate_component(component)
        
        logger.debug(f"Component updated: {component_id}")
        return component
    
    async def get_available_data_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of available data sources.
        
        Returns:
            List of data source information
        """
        sources = []
        for name, source in self.data_sources.items():
            sources.append({
                "name": name,
                "type": getattr(source, 'type', 'unknown'),
                "description": getattr(source, 'description', ''),
                "available": getattr(source, 'is_available', True)
            })
        
        return sources
    
    async def get_component_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get available component templates.
        
        Returns:
            Dictionary of component templates
        """
        return self.component_templates.copy()
    
    async def _validate_layout(self, layout: Dict[str, Any]) -> None:
        """Validate dashboard layout configuration."""
        required_fields = ["type"]
        for field in required_fields:
            if field not in layout:
                raise DashboardConfigError(f"Missing layout field: {field}")
        
        layout_type = layout["type"]
        if layout_type not in [lt.value for lt in LayoutType]:
            raise DashboardConfigError(f"Invalid layout type: {layout_type}")
    
    async def _validate_components(self, components: List[Dict[str, Any]]) -> None:
        """Validate dashboard components configuration."""
        if not isinstance(components, list):
            raise DashboardConfigError("Components must be a list")
        
        component_ids = set()
        for component in components:
            # Check required fields
            required_fields = ["id", "type", "position", "data_source"]
            for field in required_fields:
                if field not in component:
                    raise DashboardConfigError(f"Missing component field: {field}")
            
            # Check unique IDs
            component_id = component["id"]
            if component_id in component_ids:
                raise DashboardConfigError(f"Duplicate component ID: {component_id}")
            component_ids.add(component_id)
            
            # Validate component type
            component_type = component["type"]
            if component_type not in [ct.value for ct in ComponentType]:
                raise DashboardConfigError(f"Invalid component type: {component_type}")
            
            # Validate position
            await self._validate_position(component["position"])
    
    async def _validate_component(self, component: ComponentConfig) -> None:
        """Validate individual component configuration."""
        # Validate position
        await self._validate_position(component.position)
        
        # Validate data source
        if component.data_source not in self.data_sources:
            raise DashboardConfigError(f"Unknown data source: {component.data_source}")
        
        # Validate query (basic check)
        if not component.query or not isinstance(component.query, str):
            raise DashboardConfigError("Component query must be a non-empty string")
    
    async def _validate_position(self, position: Dict[str, int]) -> None:
        """Validate component position."""
        required_fields = ["x", "y", "width", "height"]
        for field in required_fields:
            if field not in position:
                raise DashboardConfigError(f"Missing position field: {field}")
            
            value = position[field]
            if not isinstance(value, int) or value < 0:
                raise DashboardConfigError(f"Invalid position {field}: {value}")
        
        # Validate bounds
        if position["x"] + position["width"] > self.config.grid_columns:
            raise DashboardConfigError("Component exceeds grid width")
        
        if position["y"] + position["height"] > self.config.grid_rows:
            raise DashboardConfigError("Component exceeds grid height")
    
    async def _validate_data_sources(self, config: Dict[str, Any]) -> None:
        """Validate data sources used in configuration."""
        used_sources = set()
        
        for component in config.get("components", []):
            data_source = component.get("data_source")
            if data_source:
                used_sources.add(data_source)
        
        # Check if all used sources are available
        for source in used_sources:
            if source not in self.data_sources:
                raise DashboardConfigError(f"Data source not available: {source}")
    
    async def _build_layout(self, layout_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build dashboard layout."""
        layout = {
            "type": layout_config["type"],
            "config": self.config.to_dict(),
            "grid": {
                "columns": self.config.grid_columns,
                "rows": self.config.grid_rows,
                "spacing": self.config.component_spacing
            }
        }
        
        # Add layout-specific configuration
        if layout_config["type"] == LayoutType.RESPONSIVE.value:
            layout["breakpoints"] = {
                "xs": 0,
                "sm": 576,
                "md": 768,
                "lg": 992,
                "xl": 1200
            }
        
        return layout
    
    async def _build_components(
        self,
        components_config: List[Dict[str, Any]],
        time_range: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Build dashboard components with data."""
        components = []
        
        for component_config in components_config:
            try:
                component = await self._build_component(component_config, time_range)
                components.append(component)
            except Exception as e:
                logger.error(f"Failed to build component {component_config.get('id')}: {e}")
                # Add error component
                components.append({
                    "id": component_config.get("id", "unknown"),
                    "type": "error",
                    "error": str(e),
                    "config": component_config
                })
        
        return components
    
    async def _build_component(
        self,
        component_config: Dict[str, Any],
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build individual component with data."""
        component_id = component_config["id"]
        data_source = component_config["data_source"]
        query = component_config["query"]
        
        # Get data from source
        data = await self._fetch_component_data(data_source, query, time_range)
        
        # Build component
        component = {
            "id": component_id,
            "type": component_config["type"],
            "title": component_config.get("title", ""),
            "position": component_config["position"],
            "data": data,
            "config": component_config.get("visualization_config", {}),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return component
    
    async def _fetch_component_data(
        self,
        data_source: str,
        query: str,
        time_range: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fetch data for component."""
        # Mock data fetching - in real implementation, this would
        # connect to actual data sources (Prometheus, databases, etc.)
        
        if data_source == "metrics":
            return {
                "series": [
                    {
                        "name": "CPU Usage",
                        "data": [[1625097600000, 45.2], [1625097660000, 47.1], [1625097720000, 43.8]]
                    },
                    {
                        "name": "Memory Usage",
                        "data": [[1625097600000, 62.5], [1625097660000, 64.2], [1625097720000, 61.8]]
                    }
                ]
            }
        elif data_source == "logs":
            return {
                "entries": [
                    {"timestamp": "2025-09-09T10:00:00Z", "level": "INFO", "message": "Service started"},
                    {"timestamp": "2025-09-09T10:01:00Z", "level": "WARN", "message": "High memory usage"},
                    {"timestamp": "2025-09-09T10:02:00Z", "level": "ERROR", "message": "Connection failed"}
                ]
            }
        else:
            return {"message": f"No data available for source: {data_source}"}
    
    async def _load_component_templates(self) -> None:
        """Load component templates."""
        self.component_templates = {
            "line_chart": {
                "type": ComponentType.CHART.value,
                "visualization_config": {
                    "chart_type": "line",
                    "x_axis": "timestamp",
                    "y_axis": "value",
                    "legend": True
                }
            },
            "bar_chart": {
                "type": ComponentType.CHART.value,
                "visualization_config": {
                    "chart_type": "bar",
                    "x_axis": "category",
                    "y_axis": "value",
                    "legend": False
                }
            },
            "metric_card": {
                "type": ComponentType.METRIC.value,
                "visualization_config": {
                    "format": "number",
                    "unit": "",
                    "threshold": None
                }
            },
            "data_table": {
                "type": ComponentType.TABLE.value,
                "visualization_config": {
                    "pagination": True,
                    "sorting": True,
                    "filtering": True
                }
            }
        }
    
    async def _initialize_data_sources(self) -> None:
        """Initialize available data sources."""
        # Mock data sources - in real implementation, these would be
        # actual connections to Prometheus, databases, etc.
        
        class MockDataSource:
            def __init__(self, name: str, source_type: str):
                self.name = name
                self.type = source_type
                self.description = f"Mock {source_type} data source"
                self.is_available = True
        
        self.data_sources = {
            "metrics": MockDataSource("metrics", "prometheus"),
            "logs": MockDataSource("logs", "elasticsearch"),
            "traces": MockDataSource("traces", "jaeger"),
            "database": MockDataSource("database", "postgresql")
        }
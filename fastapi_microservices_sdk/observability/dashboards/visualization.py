"""
Visualization Engine - Chart and visualization rendering

This module provides the visualization engine for rendering charts,
graphs, and other visual components in dashboards.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json
import base64
from io import BytesIO

logger = logging.getLogger(__name__)


class ChartType(Enum):
    """Supported chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    TABLE = "table"
    METRIC = "metric"


class VisualizationEngine:
    """
    Visualization engine for rendering charts and visual components.
    
    Provides functionality for:
    - Chart rendering
    - Data transformation
    - Theme management
    - Export capabilities
    """
    
    def __init__(self):
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.chart_renderers: Dict[str, Any] = {}
        self.is_initialized = False
        
        logger.info("Visualization engine initialized")
    
    async def initialize(self) -> None:
        """Initialize visualization engine."""
        if self.is_initialized:
            return
        
        try:
            # Load themes
            await self._load_themes()
            
            # Initialize chart renderers
            await self._initialize_renderers()
            
            self.is_initialized = True
            logger.info("Visualization engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize visualization engine: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown visualization engine."""
        if not self.is_initialized:
            return
        
        self.is_initialized = False
        logger.info("Visualization engine shutdown successfully")
    
    async def render_chart(
        self,
        chart_type: ChartType,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: str = "default"
    ) -> Dict[str, Any]:
        """
        Render chart with data and configuration.
        
        Args:
            chart_type: Type of chart to render
            data: Chart data
            config: Chart configuration
            theme: Theme to use
            
        Returns:
            Rendered chart configuration
        """
        try:
            # Get theme configuration
            theme_config = self.themes.get(theme, self.themes["default"])
            
            # Render based on chart type
            if chart_type == ChartType.LINE:
                return await self._render_line_chart(data, config, theme_config)
            elif chart_type == ChartType.BAR:
                return await self._render_bar_chart(data, config, theme_config)
            elif chart_type == ChartType.PIE:
                return await self._render_pie_chart(data, config, theme_config)
            elif chart_type == ChartType.GAUGE:
                return await self._render_gauge_chart(data, config, theme_config)
            elif chart_type == ChartType.TABLE:
                return await self._render_table(data, config, theme_config)
            elif chart_type == ChartType.METRIC:
                return await self._render_metric(data, config, theme_config)
            else:
                return await self._render_generic_chart(chart_type, data, config, theme_config)
                
        except Exception as e:
            logger.error(f"Failed to render chart: {e}")
            return self._create_error_chart(str(e))
    
    async def _render_line_chart(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render line chart."""
        
        chart_config = {
            "type": "line",
            "data": {
                "datasets": []
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": config.get("title", "Line Chart")
                    },
                    "legend": {
                        "display": config.get("legend", True)
                    }
                },
                "scales": {
                    "x": {
                        "display": True,
                        "title": {
                            "display": True,
                            "text": config.get("x_axis", {}).get("label", "X Axis")
                        }
                    },
                    "y": {
                        "display": True,
                        "title": {
                            "display": True,
                            "text": config.get("y_axis", {}).get("label", "Y Axis")
                        }
                    }
                }
            }
        }
        
        # Process data series
        if "series" in data:
            for i, series in enumerate(data["series"]):
                dataset = {
                    "label": series.get("name", f"Series {i+1}"),
                    "data": series.get("data", []),
                    "borderColor": theme["colors"][i % len(theme["colors"])],
                    "backgroundColor": theme["colors"][i % len(theme["colors"])] + "20",
                    "fill": config.get("fill", False)
                }
                chart_config["data"]["datasets"].append(dataset)
        
        return chart_config
    
    async def _render_bar_chart(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render bar chart."""
        
        chart_config = {
            "type": "bar",
            "data": {
                "labels": data.get("labels", []),
                "datasets": []
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": config.get("title", "Bar Chart")
                    }
                },
                "scales": {
                    "y": {
                        "beginAtZero": True
                    }
                }
            }
        }
        
        # Process data series
        if "series" in data:
            for i, series in enumerate(data["series"]):
                dataset = {
                    "label": series.get("name", f"Series {i+1}"),
                    "data": series.get("data", []),
                    "backgroundColor": theme["colors"][i % len(theme["colors"])],
                    "borderColor": theme["colors"][i % len(theme["colors"])],
                    "borderWidth": 1
                }
                chart_config["data"]["datasets"].append(dataset)
        
        return chart_config
    
    async def _render_pie_chart(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render pie chart."""
        
        chart_config = {
            "type": "pie",
            "data": {
                "labels": data.get("labels", []),
                "datasets": [{
                    "data": data.get("values", []),
                    "backgroundColor": theme["colors"][:len(data.get("values", []))],
                    "borderWidth": 2,
                    "borderColor": theme.get("background", "#ffffff")
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": config.get("title", "Pie Chart")
                    },
                    "legend": {
                        "position": config.get("legend_position", "right")
                    }
                }
            }
        }
        
        return chart_config
    
    async def _render_gauge_chart(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render gauge chart."""
        
        value = data.get("value", 0)
        min_value = config.get("min_value", 0)
        max_value = config.get("max_value", 100)
        
        # Calculate percentage
        percentage = ((value - min_value) / (max_value - min_value)) * 100
        
        chart_config = {
            "type": "gauge",
            "data": {
                "value": value,
                "percentage": percentage,
                "min": min_value,
                "max": max_value
            },
            "options": {
                "responsive": True,
                "title": config.get("title", "Gauge"),
                "unit": config.get("unit", ""),
                "thresholds": config.get("thresholds", []),
                "colors": {
                    "success": theme.get("success", "#28a745"),
                    "warning": theme.get("warning", "#ffc107"),
                    "danger": theme.get("danger", "#dc3545")
                }
            }
        }
        
        return chart_config
    
    async def _render_table(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render data table."""
        
        table_config = {
            "type": "table",
            "data": {
                "columns": data.get("columns", []),
                "rows": data.get("rows", [])
            },
            "options": {
                "responsive": True,
                "title": config.get("title", "Data Table"),
                "pagination": config.get("pagination", True),
                "sorting": config.get("sorting", True),
                "filtering": config.get("filtering", False),
                "pageSize": config.get("page_size", 10),
                "theme": {
                    "headerBackground": theme.get("primary", "#007bff"),
                    "headerColor": theme.get("text_light", "#ffffff"),
                    "rowStripe": theme.get("light", "#f8f9fa")
                }
            }
        }
        
        return table_config
    
    async def _render_metric(
        self,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render metric card."""
        
        value = data.get("value", 0)
        previous_value = data.get("previous_value")
        
        # Calculate change if previous value available
        change = None
        change_percentage = None
        if previous_value is not None:
            change = value - previous_value
            if previous_value != 0:
                change_percentage = (change / previous_value) * 100
        
        metric_config = {
            "type": "metric",
            "data": {
                "value": value,
                "change": change,
                "change_percentage": change_percentage,
                "formatted_value": self._format_value(value, config)
            },
            "options": {
                "title": config.get("title", "Metric"),
                "unit": config.get("unit", ""),
                "precision": config.get("precision", 0),
                "format": config.get("format", "number"),
                "threshold": config.get("threshold"),
                "colors": {
                    "positive": theme.get("success", "#28a745"),
                    "negative": theme.get("danger", "#dc3545"),
                    "neutral": theme.get("secondary", "#6c757d")
                }
            }
        }
        
        return metric_config
    
    async def _render_generic_chart(
        self,
        chart_type: ChartType,
        data: Dict[str, Any],
        config: Dict[str, Any],
        theme: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Render generic chart type."""
        
        return {
            "type": chart_type.value,
            "data": data,
            "options": {
                "responsive": True,
                "title": config.get("title", f"{chart_type.value.title()} Chart"),
                "theme": theme
            }
        }
    
    def _create_error_chart(self, error_message: str) -> Dict[str, Any]:
        """Create error chart configuration."""
        
        return {
            "type": "error",
            "error": error_message,
            "options": {
                "title": "Chart Error",
                "message": f"Failed to render chart: {error_message}"
            }
        }
    
    def _format_value(self, value: Union[int, float], config: Dict[str, Any]) -> str:
        """Format value according to configuration."""
        
        format_type = config.get("format", "number")
        precision = config.get("precision", 0)
        unit = config.get("unit", "")
        
        if format_type == "percentage":
            formatted = f"{value:.{precision}f}%"
        elif format_type == "currency":
            formatted = f"${value:,.{precision}f}"
        elif format_type == "bytes":
            formatted = self._format_bytes(value)
        else:
            formatted = f"{value:,.{precision}f}"
        
        if unit:
            formatted += f" {unit}"
        
        return formatted
    
    def _format_bytes(self, bytes_value: float) -> str:
        """Format bytes value with appropriate unit."""
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        
        while bytes_value >= 1024 and unit_index < len(units) - 1:
            bytes_value /= 1024
            unit_index += 1
        
        return f"{bytes_value:.1f} {units[unit_index]}"
    
    async def _load_themes(self) -> None:
        """Load visualization themes."""
        
        self.themes = {
            "default": {
                "colors": [
                    "#007bff", "#28a745", "#ffc107", "#dc3545", 
                    "#6f42c1", "#fd7e14", "#20c997", "#6c757d"
                ],
                "background": "#ffffff",
                "text": "#212529",
                "text_light": "#ffffff",
                "primary": "#007bff",
                "secondary": "#6c757d",
                "success": "#28a745",
                "warning": "#ffc107",
                "danger": "#dc3545",
                "light": "#f8f9fa",
                "dark": "#343a40"
            },
            "dark": {
                "colors": [
                    "#4dabf7", "#51cf66", "#ffd43b", "#ff6b6b",
                    "#9775fa", "#ff922b", "#20c997", "#adb5bd"
                ],
                "background": "#212529",
                "text": "#ffffff",
                "text_light": "#ffffff",
                "primary": "#4dabf7",
                "secondary": "#adb5bd",
                "success": "#51cf66",
                "warning": "#ffd43b",
                "danger": "#ff6b6b",
                "light": "#343a40",
                "dark": "#212529"
            },
            "minimal": {
                "colors": [
                    "#000000", "#666666", "#999999", "#cccccc"
                ],
                "background": "#ffffff",
                "text": "#000000",
                "text_light": "#ffffff",
                "primary": "#000000",
                "secondary": "#666666",
                "success": "#000000",
                "warning": "#666666",
                "danger": "#000000",
                "light": "#f5f5f5",
                "dark": "#000000"
            }
        }
    
    async def _initialize_renderers(self) -> None:
        """Initialize chart renderers."""
        
        # In a real implementation, this would initialize
        # actual chart rendering libraries (Chart.js, D3.js, etc.)
        self.chart_renderers = {
            chart_type.value: f"renderer_{chart_type.value}"
            for chart_type in ChartType
        }
    
    def get_supported_chart_types(self) -> List[str]:
        """Get list of supported chart types."""
        return [chart_type.value for chart_type in ChartType]
    
    def get_available_themes(self) -> List[str]:
        """Get list of available themes."""
        return list(self.themes.keys())
    
    def get_theme_config(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """Get theme configuration."""
        return self.themes.get(theme_name)
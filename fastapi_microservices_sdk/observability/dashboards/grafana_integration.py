"""
Grafana Integration - Automatic Grafana dashboard provisioning

This module provides integration with Grafana for automatic dashboard
provisioning, data source configuration, and alert management.
"""

import asyncio
import logging
import json
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class GrafanaIntegration:
    """
    Grafana integration for automatic dashboard provisioning.
    
    Provides:
    - Automatic dashboard creation in Grafana
    - Data source configuration
    - Alert rule management
    - Dashboard synchronization
    """
    
    def __init__(
        self,
        grafana_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        username: str = "admin",
        password: str = "admin"
    ):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.username = username
        self.password = password
        
        self.session: Optional[httpx.AsyncClient] = None
        self.is_initialized = False
        
        logger.info(f"Grafana integration initialized for {grafana_url}")
    
    async def initialize(self) -> None:
        """Initialize Grafana integration."""
        if self.is_initialized:
            return
        
        try:
            # Create HTTP session
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.session = httpx.AsyncClient(
                base_url=self.grafana_url,
                headers=headers,
                timeout=30.0
            )
            
            # Test connection
            await self._test_connection()
            
            # Setup data sources
            await self._setup_data_sources()
            
            self.is_initialized = True
            logger.info("Grafana integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Grafana integration: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown Grafana integration."""
        if self.session:
            await self.session.aclose()
        
        self.is_initialized = False
        logger.info("Grafana integration shutdown")
    
    async def create_dashboard(
        self,
        dashboard_name: str,
        dashboard_config: Dict[str, Any],
        folder: str = "FastAPI SDK"
    ) -> Dict[str, Any]:
        """
        Create dashboard in Grafana.
        
        Args:
            dashboard_name: Name of the dashboard
            dashboard_config: Dashboard configuration
            folder: Grafana folder to create dashboard in
            
        Returns:
            Created dashboard information
        """
        try:
            # Ensure folder exists
            folder_id = await self._ensure_folder(folder)
            
            # Convert SDK dashboard config to Grafana format
            grafana_dashboard = await self._convert_to_grafana_format(
                dashboard_name, dashboard_config
            )
            
            # Create dashboard
            payload = {
                "dashboard": grafana_dashboard,
                "folderId": folder_id,
                "overwrite": True
            }
            
            response = await self.session.post("/api/dashboards/db", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Grafana dashboard created: {dashboard_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Grafana dashboard: {e}")
            raise
    
    async def update_dashboard(
        self,
        dashboard_uid: str,
        dashboard_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update existing Grafana dashboard.
        
        Args:
            dashboard_uid: Grafana dashboard UID
            dashboard_config: Updated dashboard configuration
            
        Returns:
            Updated dashboard information
        """
        try:
            # Get existing dashboard
            response = await self.session.get(f"/api/dashboards/uid/{dashboard_uid}")
            response.raise_for_status()
            
            existing = response.json()
            dashboard = existing["dashboard"]
            
            # Update dashboard with new config
            updated_dashboard = await self._convert_to_grafana_format(
                dashboard["title"], dashboard_config
            )
            
            # Preserve Grafana-specific fields
            updated_dashboard["id"] = dashboard["id"]
            updated_dashboard["uid"] = dashboard["uid"]
            updated_dashboard["version"] = dashboard["version"]
            
            # Update dashboard
            payload = {
                "dashboard": updated_dashboard,
                "overwrite": True
            }
            
            response = await self.session.post("/api/dashboards/db", json=payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Grafana dashboard updated: {dashboard_uid}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update Grafana dashboard: {e}")
            raise
    
    async def delete_dashboard(self, dashboard_uid: str) -> None:
        """
        Delete Grafana dashboard.
        
        Args:
            dashboard_uid: Grafana dashboard UID
        """
        try:
            response = await self.session.delete(f"/api/dashboards/uid/{dashboard_uid}")
            response.raise_for_status()
            
            logger.info(f"Grafana dashboard deleted: {dashboard_uid}")
            
        except Exception as e:
            logger.error(f"Failed to delete Grafana dashboard: {e}")
            raise
    
    async def provision_microservice_dashboards(
        self,
        service_name: str,
        service_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Provision standard dashboards for a microservice.
        
        Args:
            service_name: Name of the microservice
            service_config: Service configuration
            
        Returns:
            List of created dashboards
        """
        dashboards = []
        
        try:
            # Service Overview Dashboard
            overview_config = self._create_service_overview_config(service_name, service_config)
            overview_dashboard = await self.create_dashboard(
                f"{service_name} - Overview",
                overview_config,
                folder=f"Services/{service_name}"
            )
            dashboards.append(overview_dashboard)
            
            # Performance Dashboard
            performance_config = self._create_performance_config(service_name, service_config)
            performance_dashboard = await self.create_dashboard(
                f"{service_name} - Performance",
                performance_config,
                folder=f"Services/{service_name}"
            )
            dashboards.append(performance_dashboard)
            
            # Error Monitoring Dashboard
            error_config = self._create_error_monitoring_config(service_name, service_config)
            error_dashboard = await self.create_dashboard(
                f"{service_name} - Errors",
                error_config,
                folder=f"Services/{service_name}"
            )
            dashboards.append(error_dashboard)
            
            logger.info(f"Provisioned {len(dashboards)} dashboards for service: {service_name}")
            return dashboards
            
        except Exception as e:
            logger.error(f"Failed to provision dashboards for {service_name}: {e}")
            raise
    
    async def _test_connection(self) -> None:
        """Test connection to Grafana."""
        try:
            response = await self.session.get("/api/health")
            response.raise_for_status()
            
            health = response.json()
            logger.info(f"Grafana connection successful: {health}")
            
        except Exception as e:
            logger.error(f"Grafana connection failed: {e}")
            raise
    
    async def _setup_data_sources(self) -> None:
        """Setup required data sources in Grafana."""
        data_sources = [
            {
                "name": "Prometheus",
                "type": "prometheus",
                "url": "http://prometheus:9090",
                "access": "proxy",
                "isDefault": True
            },
            {
                "name": "Jaeger",
                "type": "jaeger",
                "url": "http://jaeger:16686",
                "access": "proxy"
            }
        ]
        
        for ds_config in data_sources:
            try:
                # Check if data source exists
                response = await self.session.get(f"/api/datasources/name/{ds_config['name']}")
                
                if response.status_code == 404:
                    # Create data source
                    response = await self.session.post("/api/datasources", json=ds_config)
                    response.raise_for_status()
                    logger.info(f"Created data source: {ds_config['name']}")
                else:
                    logger.info(f"Data source already exists: {ds_config['name']}")
                    
            except Exception as e:
                logger.warning(f"Failed to setup data source {ds_config['name']}: {e}")
    
    async def _ensure_folder(self, folder_name: str) -> int:
        """Ensure Grafana folder exists and return its ID."""
        try:
            # Check if folder exists
            response = await self.session.get("/api/folders")
            response.raise_for_status()
            
            folders = response.json()
            for folder in folders:
                if folder["title"] == folder_name:
                    return folder["id"]
            
            # Create folder
            folder_payload = {
                "title": folder_name
            }
            
            response = await self.session.post("/api/folders", json=folder_payload)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Created Grafana folder: {folder_name}")
            
            return result["id"]
            
        except Exception as e:
            logger.error(f"Failed to ensure folder {folder_name}: {e}")
            return 0  # Default folder
    
    async def _convert_to_grafana_format(
        self,
        dashboard_name: str,
        sdk_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert SDK dashboard config to Grafana format."""
        
        grafana_dashboard = {
            "title": dashboard_name,
            "tags": ["fastapi-sdk", "microservices"],
            "timezone": "browser",
            "panels": [],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "refresh": "30s",
            "schemaVersion": 30,
            "version": 1
        }
        
        # Convert components to Grafana panels
        panel_id = 1
        for component in sdk_config.get("components", []):
            panel = await self._convert_component_to_panel(component, panel_id)
            if panel:
                grafana_dashboard["panels"].append(panel)
                panel_id += 1
        
        return grafana_dashboard
    
    async def _convert_component_to_panel(
        self,
        component: Dict[str, Any],
        panel_id: int
    ) -> Optional[Dict[str, Any]]:
        """Convert SDK component to Grafana panel."""
        
        component_type = component.get("type", "")
        position = component.get("position", {})
        
        # Base panel configuration
        panel = {
            "id": panel_id,
            "title": component.get("title", "Panel"),
            "type": self._map_component_type_to_grafana(component_type),
            "gridPos": {
                "h": position.get("height", 8),
                "w": position.get("width", 12),
                "x": position.get("x", 0),
                "y": position.get("y", 0)
            },
            "targets": [
                {
                    "expr": self._convert_query_to_prometheus(component.get("query", "")),
                    "refId": "A"
                }
            ]
        }
        
        # Add type-specific configuration
        if component_type in ["line_chart", "bar_chart"]:
            panel["fieldConfig"] = {
                "defaults": {
                    "color": {
                        "mode": "palette-classic"
                    },
                    "custom": {
                        "axisLabel": "",
                        "axisPlacement": "auto",
                        "barAlignment": 0,
                        "drawStyle": "line" if component_type == "line_chart" else "bars",
                        "fillOpacity": 10,
                        "gradientMode": "none",
                        "hideFrom": {
                            "legend": False,
                            "tooltip": False,
                            "vis": False
                        },
                        "lineInterpolation": "linear",
                        "lineWidth": 1,
                        "pointSize": 5,
                        "scaleDistribution": {
                            "type": "linear"
                        },
                        "showPoints": "never",
                        "spanNulls": False,
                        "stacking": {
                            "group": "A",
                            "mode": "none"
                        },
                        "thresholdsStyle": {
                            "mode": "off"
                        }
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "red",
                                "value": 80
                            }
                        ]
                    },
                    "unit": component.get("visualization_config", {}).get("unit", "short")
                }
            }
        elif component_type == "metric":
            panel["type"] = "stat"
            panel["fieldConfig"] = {
                "defaults": {
                    "color": {
                        "mode": "thresholds"
                    },
                    "mappings": [],
                    "thresholds": {
                        "mode": "absolute",
                        "steps": [
                            {
                                "color": "green",
                                "value": None
                            },
                            {
                                "color": "red",
                                "value": 80
                            }
                        ]
                    },
                    "unit": component.get("visualization_config", {}).get("unit", "short")
                }
            }
            panel["options"] = {
                "reduceOptions": {
                    "values": False,
                    "calcs": ["lastNotNull"],
                    "fields": ""
                },
                "orientation": "auto",
                "textMode": "auto",
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto"
            }
        
        return panel
    
    def _map_component_type_to_grafana(self, component_type: str) -> str:
        """Map SDK component type to Grafana panel type."""
        
        mapping = {
            "line_chart": "timeseries",
            "bar_chart": "barchart",
            "pie_chart": "piechart",
            "gauge": "gauge",
            "metric": "stat",
            "table": "table",
            "heatmap": "heatmap"
        }
        
        return mapping.get(component_type, "timeseries")
    
    def _convert_query_to_prometheus(self, query: str) -> str:
        """Convert SDK query to Prometheus query."""
        
        # Simple query mapping - in real implementation, this would be more sophisticated
        query_mapping = {
            "cpu_usage_percent": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "memory_usage_percent": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "http_requests_per_second": "rate(http_requests_total[5m])",
            "http_error_rate": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "http_request_duration_seconds": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "db_connections_active": "db_connections_active",
            "db_query_duration_seconds": "histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))"
        }
        
        return query_mapping.get(query, query)
    
    def _create_service_overview_config(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create service overview dashboard configuration."""
        
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "components": [
                {
                    "id": "service-health",
                    "type": "metric",
                    "title": "Service Health",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": f"up{{job=\"{service_name}\"}}",
                    "visualization_config": {
                        "unit": "bool",
                        "thresholds": [
                            {"value": 0, "color": "red"},
                            {"value": 1, "color": "green"}
                        ]
                    }
                },
                {
                    "id": "request-rate",
                    "type": "metric",
                    "title": "Request Rate",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": f"rate(http_requests_total{{service=\"{service_name}\"}}[5m])",
                    "visualization_config": {
                        "unit": "reqps"
                    }
                },
                {
                    "id": "error-rate",
                    "type": "metric",
                    "title": "Error Rate",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": f"rate(http_requests_total{{service=\"{service_name}\",status=~\"5..\"}}[5m]) / rate(http_requests_total{{service=\"{service_name}\"}}[5m]) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "thresholds": [
                            {"value": 1, "color": "yellow"},
                            {"value": 5, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "response-time",
                    "type": "metric",
                    "title": "Avg Response Time",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": f"histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{{service=\"{service_name}\"}}[5m]))",
                    "visualization_config": {
                        "unit": "s"
                    }
                },
                {
                    "id": "request-timeline",
                    "type": "line_chart",
                    "title": "Request Timeline",
                    "position": {"x": 0, "y": 3, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": f"rate(http_requests_total{{service=\"{service_name}\"}}[5m])",
                    "visualization_config": {
                        "unit": "reqps"
                    }
                }
            ]
        }
    
    def _create_performance_config(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create performance monitoring dashboard configuration."""
        
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "components": [
                {
                    "id": "response-time-percentiles",
                    "type": "line_chart",
                    "title": "Response Time Percentiles",
                    "position": {"x": 0, "y": 0, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": f"histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{{service=\"{service_name}\"}}[5m]))",
                    "visualization_config": {
                        "unit": "s",
                        "legend": True
                    }
                },
                {
                    "id": "throughput-by-endpoint",
                    "type": "bar_chart",
                    "title": "Throughput by Endpoint",
                    "position": {"x": 0, "y": 6, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": f"topk(10, rate(http_requests_total{{service=\"{service_name}\"}}[5m]))",
                    "visualization_config": {
                        "unit": "reqps"
                    }
                },
                {
                    "id": "memory-usage",
                    "type": "line_chart",
                    "title": "Memory Usage",
                    "position": {"x": 6, "y": 6, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": f"process_resident_memory_bytes{{service=\"{service_name}\"}}",
                    "visualization_config": {
                        "unit": "bytes"
                    }
                }
            ]
        }
    
    def _create_error_monitoring_config(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create error monitoring dashboard configuration."""
        
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "components": [
                {
                    "id": "error-rate-timeline",
                    "type": "line_chart",
                    "title": "Error Rate Timeline",
                    "position": {"x": 0, "y": 0, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": f"rate(http_requests_total{{service=\"{service_name}\",status=~\"[45]..\"}}[5m])",
                    "visualization_config": {
                        "unit": "reqps"
                    }
                },
                {
                    "id": "errors-by-status",
                    "type": "pie_chart",
                    "title": "Errors by Status Code",
                    "position": {"x": 0, "y": 6, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": f"sum by (status) (rate(http_requests_total{{service=\"{service_name}\",status=~\"[45]..\"}}[5m]))"
                },
                {
                    "id": "error-logs",
                    "type": "table",
                    "title": "Recent Error Logs",
                    "position": {"x": 6, "y": 6, "width": 6, "height": 6},
                    "data_source": "loki",
                    "query": f"{{service=\"{service_name}\"}} |= \"ERROR\""
                }
            ]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Grafana integration status."""
        return {
            "initialized": self.is_initialized,
            "grafana_url": self.grafana_url,
            "connected": self.session is not None,
            "authentication": "api_key" if self.api_key else "basic"
        }
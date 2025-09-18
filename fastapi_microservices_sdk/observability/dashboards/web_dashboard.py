"""
Web Dashboard - Complete web-based dashboard system

This module provides a complete web-based dashboard system with
FastAPI integration, WebSocket support, and real-time updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .manager import DashboardManager, Dashboard
from .builder import DashboardBuilder, DashboardConfig
from .templates import DashboardTemplateManager
from .visualization import VisualizationEngine
from .streaming import DashboardStreaming, StreamingConfig
from .exporter import DashboardExporter
from .security import DashboardSecurity
from .exceptions import DashboardError
from .alerts import DashboardAlertManager, AlertRule, AlertSeverity
from .metrics_collector import MetricsCollector, SystemMetricsCollector

logger = logging.getLogger(__name__)


class WebDashboardSystem:
    """
    Complete web-based dashboard system.
    
    Provides:
    - Web interface for dashboard management
    - Real-time dashboard viewing
    - Dashboard creation and editing
    - Export and sharing capabilities
    - WebSocket streaming
    """
    
    def __init__(self, app: FastAPI, config: Optional[DashboardConfig] = None):
        self.app = app
        self.config = config or DashboardConfig()
        
        # Initialize components
        self.dashboard_manager = DashboardManager(self.config)
        self.template_manager = DashboardTemplateManager()
        self.visualization_engine = VisualizationEngine()
        self.streaming = DashboardStreaming(StreamingConfig())
        self.exporter = DashboardExporter()
        self.security = DashboardSecurity()
        self.alert_manager = DashboardAlertManager()
        self.metrics_collector = MetricsCollector()
        self.system_metrics = SystemMetricsCollector(self.metrics_collector)
        
        # WebSocket connections
        self.websocket_connections: Dict[str, WebSocket] = {}
        
        # Setup components
        self.dashboard_manager.set_templates(self.template_manager)
        self.dashboard_manager.set_security(self.security)
        self.dashboard_manager.set_streaming(self.streaming)
        self.dashboard_manager.set_exporter(self.exporter)
        
        # Setup routes
        self._setup_routes()
        
        logger.info("Web dashboard system initialized")
    
    async def initialize(self) -> None:
        """Initialize the web dashboard system."""
        try:
            await self.dashboard_manager.initialize()
            await self.alert_manager.initialize()
            await self.metrics_collector.initialize()
            logger.info("Web dashboard system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize web dashboard system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the web dashboard system."""
        try:
            await self.dashboard_manager.shutdown()
            await self.alert_manager.shutdown()
            await self.metrics_collector.shutdown()
            logger.info("Web dashboard system shutdown successfully")
        except Exception as e:
            logger.error(f"Error during web dashboard system shutdown: {e}")
    
    def _setup_routes(self) -> None:
        """Setup FastAPI routes for dashboard system."""
        
        # Dashboard management routes
        @self.app.get("/dashboards", response_class=JSONResponse)
        async def list_dashboards(
            user: Optional[str] = None,
            tags: Optional[str] = None,
            owner: Optional[str] = None
        ):
            """List dashboards with optional filtering."""
            try:
                tag_list = tags.split(",") if tags else None
                dashboards = await self.dashboard_manager.list_dashboards(
                    user=user, tags=tag_list, owner=owner
                )
                return [dashboard.to_dict() for dashboard in dashboards]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/dashboards", response_class=JSONResponse)
        async def create_dashboard(
            request: Request,
            dashboard_data: Dict[str, Any]
        ):
            """Create a new dashboard."""
            try:
                dashboard = await self.dashboard_manager.create_dashboard(
                    name=dashboard_data["name"],
                    config=dashboard_data["config"],
                    owner=dashboard_data.get("owner", "anonymous"),
                    template_id=dashboard_data.get("template_id")
                )
                return dashboard.to_dict()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/dashboards/{dashboard_id}", response_class=JSONResponse)
        async def get_dashboard(dashboard_id: str, user: Optional[str] = None):
            """Get dashboard by ID."""
            try:
                dashboard = await self.dashboard_manager.get_dashboard(dashboard_id, user)
                return dashboard.to_dict()
            except DashboardError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.put("/dashboards/{dashboard_id}", response_class=JSONResponse)
        async def update_dashboard(
            dashboard_id: str,
            dashboard_data: Dict[str, Any],
            user: Optional[str] = None
        ):
            """Update dashboard configuration."""
            try:
                dashboard = await self.dashboard_manager.update_dashboard(
                    dashboard_id, dashboard_data["config"], user
                )
                return dashboard.to_dict()
            except DashboardError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/dashboards/{dashboard_id}")
        async def delete_dashboard(dashboard_id: str, user: Optional[str] = None):
            """Delete dashboard."""
            try:
                await self.dashboard_manager.delete_dashboard(dashboard_id, user)
                return {"message": "Dashboard deleted successfully"}
            except DashboardError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Dashboard rendering routes
        @self.app.get("/dashboards/{dashboard_id}/render", response_class=JSONResponse)
        async def render_dashboard(
            dashboard_id: str,
            user: Optional[str] = None,
            time_range: Optional[str] = None
        ):
            """Render dashboard with current data."""
            try:
                time_range_dict = json.loads(time_range) if time_range else None
                rendered = await self.dashboard_manager.render_dashboard(
                    dashboard_id, user, time_range_dict
                )
                return rendered
            except DashboardError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Dashboard export routes
        @self.app.get("/dashboards/{dashboard_id}/export/{format}")
        async def export_dashboard(
            dashboard_id: str,
            format: str,
            user: Optional[str] = None
        ):
            """Export dashboard in specified format."""
            try:
                exported_data = await self.dashboard_manager.export_dashboard(
                    dashboard_id, format, user
                )
                
                # Get MIME type
                mime_types = {
                    "json": "application/json",
                    "pdf": "application/pdf",
                    "png": "image/png",
                    "html": "text/html",
                    "csv": "text/csv"
                }
                
                return Response(
                    content=exported_data,
                    media_type=mime_types.get(format, "application/octet-stream"),
                    headers={
                        "Content-Disposition": f"attachment; filename=dashboard_{dashboard_id}.{format}"
                    }
                )
            except DashboardError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Template management routes
        @self.app.get("/dashboard-templates", response_class=JSONResponse)
        async def list_templates(
            category: Optional[str] = None,
            tags: Optional[str] = None
        ):
            """List dashboard templates."""
            try:
                tag_list = tags.split(",") if tags else None
                templates = await self.template_manager.get_templates(
                    category=category, tags=tag_list
                )
                return [template.to_dict() for template in templates]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/dashboard-templates/{template_id}", response_class=JSONResponse)
        async def get_template(template_id: str):
            """Get dashboard template by ID."""
            try:
                template = await self.template_manager.get_template(template_id)
                if not template:
                    raise HTTPException(status_code=404, detail="Template not found")
                return template.to_dict()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # WebSocket route for real-time updates
        @self.app.websocket("/dashboards/{dashboard_id}/stream")
        async def dashboard_websocket(websocket: WebSocket, dashboard_id: str):
            """WebSocket endpoint for real-time dashboard updates."""
            await websocket.accept()
            
            connection_id = str(uuid.uuid4())
            self.websocket_connections[connection_id] = websocket
            
            try:
                # Start dashboard stream
                stream_id = await self.dashboard_manager.start_dashboard_stream(
                    dashboard_id, websocket=websocket
                )
                
                # Keep connection alive
                while True:
                    try:
                        # Wait for client messages (ping/pong, etc.)
                        message = await websocket.receive_text()
                        
                        # Handle client messages
                        if message == "ping":
                            await websocket.send_text("pong")
                        
                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        logger.error(f"WebSocket error: {e}")
                        break
                
            except Exception as e:
                logger.error(f"Dashboard streaming error: {e}")
            finally:
                # Cleanup
                if connection_id in self.websocket_connections:
                    del self.websocket_connections[connection_id]
                
                # Stop stream if it was started
                try:
                    await self.dashboard_manager.stop_dashboard_stream(stream_id)
                except:
                    pass
        
        # Alert management routes
        @self.app.get("/dashboards/{dashboard_id}/alerts", response_class=JSONResponse)
        async def get_dashboard_alerts(dashboard_id: str):
            """Get alerts for dashboard."""
            try:
                alerts = self.alert_manager.get_active_alerts(dashboard_id)
                return [alert.to_dict() for alert in alerts]
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/dashboards/{dashboard_id}/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(dashboard_id: str, alert_id: str, user: str = "anonymous"):
            """Acknowledge alert."""
            try:
                success = await self.alert_manager.acknowledge_alert(alert_id, user)
                if success:
                    return {"message": "Alert acknowledged"}
                else:
                    raise HTTPException(status_code=404, detail="Alert not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/dashboards/{dashboard_id}/metrics", response_class=JSONResponse)
        async def get_dashboard_metrics(
            dashboard_id: str,
            metric_names: Optional[str] = None,
            hours: int = 1
        ):
            """Get metrics for dashboard."""
            try:
                if metric_names:
                    names = metric_names.split(",")
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=hours)
                    return self.metrics_collector.get_multiple_metrics(
                        names, start_time, end_time
                    )
                else:
                    return self.metrics_collector.get_available_metrics()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Status and health routes
        @self.app.get("/dashboards/status", response_class=JSONResponse)
        async def dashboard_system_status():
            """Get dashboard system status."""
            return {
                "dashboard_manager": self.dashboard_manager.get_status(),
                "template_manager": self.template_manager.get_status(),
                "streaming": self.streaming.get_status(),
                "exporter": self.exporter.get_status(),
                "alert_manager": self.alert_manager.get_status(),
                "metrics_collector": self.metrics_collector.get_status(),
                "websocket_connections": len(self.websocket_connections)
            }
        
        # Web interface routes
        @self.app.get("/dashboard-ui", response_class=HTMLResponse)
        async def dashboard_ui():
            """Dashboard management UI."""
            return self._generate_dashboard_ui()
        
        @self.app.get("/dashboard-ui/{dashboard_id}", response_class=HTMLResponse)
        async def dashboard_viewer(dashboard_id: str):
            """Dashboard viewer UI."""
            return self._generate_dashboard_viewer(dashboard_id)
    
    def _generate_dashboard_ui(self) -> str:
        """Generate dashboard management UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Management</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .dashboard-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #545b62; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Dashboard Management</h1>
            <p>Create, manage, and view your dashboards</p>
            <a href="#" class="btn" onclick="createDashboard()">Create New Dashboard</a>
            <a href="#" class="btn btn-secondary" onclick="loadTemplates()">Browse Templates</a>
        </div>
        
        <div id="dashboards" class="dashboard-grid">
            <!-- Dashboards will be loaded here -->
        </div>
    </div>
    
    <script>
        // Load dashboards on page load
        window.onload = function() {
            loadDashboards();
        };
        
        async function loadDashboards() {
            try {
                const response = await fetch('/dashboards');
                const dashboards = await response.json();
                
                const container = document.getElementById('dashboards');
                container.innerHTML = '';
                
                dashboards.forEach(dashboard => {
                    const card = document.createElement('div');
                    card.className = 'dashboard-card';
                    card.innerHTML = `
                        <h3>${dashboard.name}</h3>
                        <p>Owner: ${dashboard.owner}</p>
                        <p>Created: ${new Date(dashboard.created_at).toLocaleDateString()}</p>
                        <p>Version: ${dashboard.version}</p>
                        <div>
                            <a href="/dashboard-ui/${dashboard.id}" class="btn">View</a>
                            <a href="#" class="btn btn-secondary" onclick="exportDashboard('${dashboard.id}')">Export</a>
                        </div>
                    `;
                    container.appendChild(card);
                });
                
                if (dashboards.length === 0) {
                    container.innerHTML = '<p>No dashboards found. Create your first dashboard!</p>';
                }
            } catch (error) {
                console.error('Failed to load dashboards:', error);
            }
        }
        
        function createDashboard() {
            // In a real implementation, this would open a dashboard creation modal
            alert('Dashboard creation UI would open here');
        }
        
        function loadTemplates() {
            // In a real implementation, this would show available templates
            alert('Template browser would open here');
        }
        
        function exportDashboard(dashboardId) {
            // Export dashboard as JSON
            window.open(`/dashboards/${dashboardId}/export/json`, '_blank');
        }
    </script>
</body>
</html>
"""
    
    def _generate_dashboard_viewer(self, dashboard_id: str) -> str:
        """Generate dashboard viewer UI."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Viewer</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .dashboard-grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }}
        .component {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .component h3 {{ margin-top: 0; }}
        .status {{ padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
        .status.connected {{ background: #d4edda; color: #155724; }}
        .status.disconnected {{ background: #f8d7da; color: #721c24; }}
        .btn {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }}
        .btn:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 id="dashboard-title">Loading Dashboard...</h1>
            <div id="connection-status" class="status disconnected">Connecting to real-time updates...</div>
            <div>
                <button class="btn" onclick="refreshDashboard()">Refresh</button>
                <button class="btn" onclick="exportDashboard()">Export</button>
                <a href="/dashboard-ui" class="btn">Back to List</a>
            </div>
        </div>
        
        <div id="dashboard-content" class="dashboard-grid">
            <!-- Dashboard components will be loaded here -->
        </div>
    </div>
    
    <script>
        const dashboardId = '{dashboard_id}';
        let websocket = null;
        let dashboardData = null;
        
        // Load dashboard on page load
        window.onload = function() {{
            loadDashboard();
            connectWebSocket();
        }};
        
        async function loadDashboard() {{
            try {{
                const response = await fetch(`/dashboards/${{dashboardId}}/render`);
                dashboardData = await response.json();
                
                document.getElementById('dashboard-title').textContent = dashboardData.metadata.name;
                renderDashboard(dashboardData);
            }} catch (error) {{
                console.error('Failed to load dashboard:', error);
                document.getElementById('dashboard-content').innerHTML = '<p>Failed to load dashboard</p>';
            }}
        }}
        
        function renderDashboard(data) {{
            const container = document.getElementById('dashboard-content');
            container.innerHTML = '';
            
            data.components.forEach(component => {{
                const componentDiv = document.createElement('div');
                componentDiv.className = 'component';
                componentDiv.style.gridColumn = `span ${{component.position.width}}`;
                componentDiv.style.gridRow = `span ${{component.position.height}}`;
                
                componentDiv.innerHTML = `
                    <h3>${{component.title}}</h3>
                    <div id="component-${{component.id}}">
                        <p>Component Type: ${{component.type}}</p>
                        <p>Last Updated: ${{component.last_updated}}</p>
                    </div>
                `;
                
                container.appendChild(componentDiv);
                
                // Render component based on type
                renderComponent(component);
            }});
        }}
        
        function renderComponent(component) {{
            const container = document.getElementById(`component-${{component.id}}`);
            
            if (component.type === 'line_chart' || component.type === 'bar_chart') {{
                // Create canvas for chart
                const canvas = document.createElement('canvas');
                canvas.id = `chart-${{component.id}}`;
                container.appendChild(canvas);
                
                // Render chart if data available
                if (component.data && component.data.series) {{
                    renderChart(canvas, component);
                }}
            }} else if (component.type === 'metric') {{
                // Render metric card
                container.innerHTML = `
                    <div style="text-align: center;">
                        <div style="font-size: 2em; font-weight: bold; color: #007bff;">
                            ${{component.data.formatted_value || component.data.value || 'N/A'}}
                        </div>
                        <div style="color: #666;">
                            ${{component.options.unit || ''}}
                        </div>
                    </div>
                `;
            }} else {{
                // Generic component rendering
                container.innerHTML += `<pre>${{JSON.stringify(component.data, null, 2)}}</pre>`;
            }}
        }}
        
        function renderChart(canvas, component) {{
            const ctx = canvas.getContext('2d');
            
            // Convert data to Chart.js format
            const chartData = {{
                labels: component.data.series[0].data.map(point => new Date(point[0]).toLocaleTimeString()),
                datasets: component.data.series.map((series, index) => ({{
                    label: series.name,
                    data: series.data.map(point => point[1]),
                    borderColor: `hsl(${{index * 60}}, 70%, 50%)`,
                    backgroundColor: `hsla(${{index * 60}}, 70%, 50%, 0.1)`,
                    fill: component.type === 'area_chart'
                }}))
            }};
            
            new Chart(ctx, {{
                type: component.type === 'bar_chart' ? 'bar' : 'line',
                data: chartData,
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{
                            display: true,
                            text: component.title
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        }}
        
        function connectWebSocket() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${{protocol}}//${{window.location.host}}/dashboards/${{dashboardId}}/stream`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function() {{
                document.getElementById('connection-status').className = 'status connected';
                document.getElementById('connection-status').textContent = 'Connected to real-time updates';
            }};
            
            websocket.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                // Handle real-time updates
                console.log('Real-time update:', data);
            }};
            
            websocket.onclose = function() {{
                document.getElementById('connection-status').className = 'status disconnected';
                document.getElementById('connection-status').textContent = 'Disconnected from real-time updates';
                
                // Attempt to reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            }};
            
            websocket.onerror = function(error) {{
                console.error('WebSocket error:', error);
            }};
        }}
        
        function refreshDashboard() {{
            loadDashboard();
        }}
        
        function exportDashboard() {{
            window.open(`/dashboards/${{dashboardId}}/export/json`, '_blank');
        }}
    </script>
</body>
</html>
"""
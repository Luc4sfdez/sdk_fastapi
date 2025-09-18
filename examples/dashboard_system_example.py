"""
Dashboard and Visualization System Example

This example demonstrates how to use the comprehensive dashboard and visualization
system including dashboard creation, real-time streaming, security, and export.
"""

import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

from fastapi_microservices_sdk.observability.dashboards import (
    create_dashboard_manager,
    configure_dashboard_system,
    DashboardConfig,
    VisualizationType,
    DashboardPermission,
    ExportFormat
)


async def main():
    """Main example function."""
    print("🚀 FastAPI Microservices SDK - Dashboard System Example")
    print("=" * 60)
    
    # Create dashboard manager
    print("\n1. Creating Dashboard Manager...")
    config = {
        "streaming_enabled": True,
        "real_time_updates": True,
        "auto_refresh_interval": 30,
        "security_enabled": True,
        "export_enabled": True
    }
    
    dashboard_manager = create_dashboard_manager(config, enable_streaming=True, enable_security=True)
    await dashboard_manager.initialize()
    
    print(f"✅ Dashboard manager created and initialized")
    print(f"   Status: {dashboard_manager.get_status()}")
    
    # Create a comprehensive dashboard
    print("\n2. Creating System Overview Dashboard...")
    
    dashboard_config = {
        "layout": {
            "type": "grid",
            "columns": 12,
            "rows": 20
        },
        "components": [
            {
                "id": "cpu-usage-chart",
                "type": "line_chart",
                "title": "CPU Usage Over Time",
                "position": {"x": 0, "y": 0, "width": 6, "height": 4},
                "data_source": "metrics",
                "query": "cpu_usage_percent",
                "visualization_config": {
                    "chart_type": "line",
                    "y_axis": {"min": 0, "max": 100, "unit": "%"},
                    "colors": {"primary": "#007bff"},
                    "smooth": True
                }
            },
            {
                "id": "memory-usage-chart",
                "type": "area_chart",
                "title": "Memory Usage",
                "position": {"x": 6, "y": 0, "width": 6, "height": 4},
                "data_source": "metrics",
                "query": "memory_usage_percent",
                "visualization_config": {
                    "chart_type": "area",
                    "y_axis": {"min": 0, "max": 100, "unit": "%"},
                    "fill_opacity": 0.6
                }
            },
            {
                "id": "request-rate-metric",
                "type": "metric_card",
                "title": "Request Rate",
                "position": {"x": 0, "y": 4, "width": 3, "height": 2},
                "data_source": "metrics",
                "query": "http_requests_per_second",
                "visualization_config": {
                    "format": "number",
                    "unit": "req/s",
                    "precision": 1,
                    "trend": True
                }
            },
            {
                "id": "error-rate-gauge",
                "type": "gauge",
                "title": "Error Rate",
                "position": {"x": 3, "y": 4, "width": 3, "height": 2},
                "data_source": "metrics",
                "query": "http_error_rate",
                "visualization_config": {
                    "min_value": 0,
                    "max_value": 10,
                    "unit": "%",
                    "thresholds": [
                        {"value": 1, "color": "success"},
                        {"value": 3, "color": "warning"},
                        {"value": 5, "color": "danger"}
                    ]
                }
            },
            {
                "id": "response-time-histogram",
                "type": "histogram",
                "title": "Response Time Distribution",
                "position": {"x": 6, "y": 4, "width": 6, "height": 4},
                "data_source": "metrics",
                "query": "http_request_duration_seconds",
                "visualization_config": {
                    "bins": 20,
                    "x_axis": {"unit": "ms"}
                }
            },
            {
                "id": "top-endpoints-table",
                "type": "table",
                "title": "Top Endpoints by Traffic",
                "position": {"x": 0, "y": 8, "width": 8, "height": 6},
                "data_source": "metrics",
                "query": "top_endpoints_by_requests",
                "visualization_config": {
                    "columns": [
                        {"field": "endpoint", "title": "Endpoint"},
                        {"field": "requests", "title": "Requests"},
                        {"field": "avg_response_time", "title": "Avg Response Time"},
                        {"field": "error_rate", "title": "Error Rate"}
                    ],
                    "pagination": True,
                    "page_size": 10,
                    "sorting": True
                }
            },
            {
                "id": "service-topology",
                "type": "topology",
                "title": "Service Topology",
                "position": {"x": 8, "y": 8, "width": 4, "height": 6},
                "data_source": "traces",
                "query": "service_dependencies",
                "visualization_config": {
                    "layout": "force",
                    "show_labels": True,
                    "node_size_field": "request_count",
                    "edge_width_field": "call_count"
                }
            }
        ]
    }
    
    dashboard = await dashboard_manager.create_dashboard(
        name="System Overview Dashboard",
        config=dashboard_config,
        owner="admin"
    )
    
    print(f"✅ Dashboard created: {dashboard.id}")
    print(f"   Name: {dashboard.name}")
    print(f"   Components: {len(dashboard.config['components'])}")
    
    # Demonstrate dashboard security
    print("\n3. Configuring Dashboard Security...")
    
    if dashboard_manager.security:
        # Assign roles to users
        await dashboard_manager.security.assign_role("john_doe", "viewer")
        await dashboard_manager.security.assign_role("jane_smith", "editor")
        await dashboard_manager.security.assign_role("admin", "admin")
        
        # Grant specific permissions
        await dashboard_manager.security.grant_dashboard_permissions(
            "john_doe",
            dashboard.id,
            ["view", "export"]
        )
        
        print("✅ Security configured:")
        print(f"   - john_doe: viewer role + dashboard permissions")
        print(f"   - jane_smith: editor role")
        print(f"   - admin: admin role")
        
        # Test permissions
        can_view = await dashboard_manager.security.can_view_dashboard("john_doe", dashboard)
        can_edit = await dashboard_manager.security.can_edit_dashboard("john_doe", dashboard)
        
        print(f"   - john_doe can view: {can_view}")
        print(f"   - john_doe can edit: {can_edit}")
    
    # Render dashboard
    print("\n4. Rendering Dashboard...")
    
    rendered_dashboard = await dashboard_manager.render_dashboard(dashboard.id)
    
    print("✅ Dashboard rendered successfully:")
    print(f"   Layout type: {rendered_dashboard['layout']['type']}")
    print(f"   Components rendered: {len(rendered_dashboard['components'])}")
    print(f"   Rendered at: {rendered_dashboard['metadata']['rendered_at']}")
    
    # Demonstrate visualization engine
    print("\n5. Testing Visualization Engine...")
    
    viz_engine = dashboard_manager.visualization_engine
    
    # Test different visualization types
    sample_data = {
        "series": [
            {
                "name": "CPU Usage",
                "data": [
                    [1625097600000, 45.2],
                    [1625097660000, 47.1],
                    [1625097720000, 43.8],
                    [1625097780000, 46.5],
                    [1625097840000, 44.9]
                ]
            }
        ]
    }
    
    # Render line chart
    line_chart = await viz_engine.render_visualization(
        VisualizationType.LINE_CHART,
        sample_data,
        {"x_axis": "timestamp", "y_axis": "value", "legend": True}
    )
    
    print(f"✅ Line chart rendered: {line_chart['type']}")
    
    # Render gauge
    gauge_data = {"value": 75, "max": 100}
    gauge = await viz_engine.render_visualization(
        VisualizationType.GAUGE,
        gauge_data,
        {"min_value": 0, "max_value": 100, "unit": "%"}
    )
    
    print(f"✅ Gauge rendered: {gauge['type']}")
    
    # Get supported types
    supported_types = await viz_engine.get_supported_types()
    print(f"✅ Supported visualization types: {len(supported_types)}")
    
    # Demonstrate templates
    print("\n6. Working with Dashboard Templates...")
    
    if dashboard_manager.template_manager:
        # Get default templates
        default_templates = await dashboard_manager.template_manager.get_default_templates()
        print(f"✅ Default templates available: {len(default_templates)}")
        
        for template in default_templates[:3]:  # Show first 3
            print(f"   - {template.name} ({template.category})")
        
        # Create custom template
        custom_template = await dashboard_manager.template_manager.create_template(
            name="Custom Monitoring Template",
            description="Custom template for application monitoring",
            category="custom",
            config={
                "layout": {"type": "grid"},
                "components": [
                    {
                        "id": "custom-metric",
                        "type": "metric_card",
                        "title": "Custom Metric",
                        "position": {"x": 0, "y": 0, "width": 4, "height": 2},
                        "data_source": "metrics",
                        "query": "custom_metric"
                    }
                ]
            },
            author="example_user",
            tags=["custom", "monitoring"]
        )
        
        print(f"✅ Custom template created: {custom_template.id}")
    
    # Demonstrate streaming (mock)
    print("\n7. Testing Dashboard Streaming...")
    
    if dashboard_manager.streaming:
        # Start streaming
        stream_id = await dashboard_manager.start_dashboard_stream(
            dashboard.id,
            user="admin"
        )
        
        print(f"✅ Dashboard streaming started: {stream_id}")
        
        # Get stream status
        stream_status = await dashboard_manager.streaming.get_stream_status(stream_id)
        if stream_status:
            print(f"   Stream status: {stream_status['is_active']}")
            print(f"   Started at: {stream_status['started_at']}")
        
        # Simulate some streaming time
        await asyncio.sleep(2)
        
        # Stop streaming
        await dashboard_manager.stop_dashboard_stream(stream_id)
        print("✅ Dashboard streaming stopped")
    
    # Demonstrate export functionality
    print("\n8. Testing Dashboard Export...")
    
    if dashboard_manager.exporter:
        # Export as JSON
        json_export = await dashboard_manager.export_dashboard(
            dashboard.id,
            "json",
            user="admin"
        )
        
        print(f"✅ JSON export completed: {len(json_export)} bytes")
        
        # Export as HTML
        html_export = await dashboard_manager.export_dashboard(
            dashboard.id,
            "html",
            user="admin"
        )
        
        print(f"✅ HTML export completed: {len(html_export)} bytes")
        
        # Get supported formats
        supported_formats = await dashboard_manager.exporter.get_supported_formats()
        print(f"✅ Supported export formats: {[f['format'] for f in supported_formats]}")
    
    # Dashboard analytics
    print("\n9. Dashboard Analytics...")
    
    analytics = await dashboard_manager.get_dashboard_analytics(dashboard.id)
    
    print("✅ Dashboard analytics:")
    print(f"   Dashboard ID: {analytics['dashboard_id']}")
    print(f"   Name: {analytics['name']}")
    print(f"   Version: {analytics['version']}")
    print(f"   Created: {analytics['created_at']}")
    print(f"   Shared with: {analytics['shared_with_count']} users")
    print(f"   Is public: {analytics['is_public']}")
    
    # List all dashboards
    print("\n10. Dashboard Management...")
    
    all_dashboards = await dashboard_manager.list_dashboards()
    print(f"✅ Total dashboards: {len(all_dashboards)}")
    
    for db in all_dashboards:
        print(f"   - {db.name} (v{db.version}) by {db.owner}")
    
    # Manager status
    print("\n11. System Status...")
    
    status = dashboard_manager.get_status()
    print("✅ Dashboard Manager Status:")
    print(f"   Initialized: {status['initialized']}")
    print(f"   Total dashboards: {status['total_dashboards']}")
    print(f"   Active streams: {status['active_streams']}")
    print(f"   Components enabled: {sum(status['components'].values())}/{len(status['components'])}")
    
    # Cleanup
    print("\n12. Cleanup...")
    await dashboard_manager.shutdown()
    print("✅ Dashboard manager shutdown completed")
    
    print("\n" + "=" * 60)
    print("🎉 Dashboard System Example completed successfully!")
    print("\nKey features demonstrated:")
    print("  ✅ Dashboard creation and management")
    print("  ✅ Multiple visualization types")
    print("  ✅ Security and permissions")
    print("  ✅ Real-time streaming")
    print("  ✅ Template system")
    print("  ✅ Export functionality")
    print("  ✅ Analytics and monitoring")


async def fastapi_integration_example():
    """Example of FastAPI integration with dashboard system."""
    print("\n🌐 FastAPI Integration Example")
    print("=" * 40)
    
    # Create FastAPI app
    app = FastAPI(title="Dashboard System API")
    
    # Configure dashboard system
    dashboard_manager = configure_dashboard_system(
        app,
        config={
            "streaming_enabled": True,
            "security_enabled": True,
            "export_enabled": True
        },
        mount_path="/dashboards"
    )
    
    print("✅ Dashboard system integrated with FastAPI")
    print("   Available endpoints:")
    print("   - GET /dashboards/")
    print("   - POST /dashboards/")
    print("   - GET /dashboards/{dashboard_id}")
    print("   - PUT /dashboards/{dashboard_id}")
    print("   - DELETE /dashboards/{dashboard_id}")
    print("   - GET /dashboards/{dashboard_id}/render")
    print("   - POST /dashboards/{dashboard_id}/export")
    print("   - WebSocket /dashboards/{dashboard_id}/stream")
    
    # Example dashboard creation via API
    dashboard_config = {
        "layout": {"type": "grid"},
        "components": [
            {
                "id": "api-metrics",
                "type": "line_chart",
                "title": "API Metrics",
                "position": {"x": 0, "y": 0, "width": 12, "height": 6},
                "data_source": "metrics",
                "query": "api_requests_total"
            }
        ]
    }
    
    # This would be done via HTTP POST in real usage
    dashboard = await dashboard_manager.create_dashboard(
        name="API Dashboard",
        config=dashboard_config,
        owner="api_user"
    )
    
    print(f"✅ Dashboard created via API: {dashboard.id}")
    
    # Cleanup
    await dashboard_manager.shutdown()


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Run FastAPI integration example
    asyncio.run(fastapi_integration_example())
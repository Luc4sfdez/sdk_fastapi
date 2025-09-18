"""
Example usage of Monitoring Service Template

This example demonstrates how to use the Monitoring Service Template to generate
a complete monitoring service with metrics collection, dashboards, and alerting.
"""

import asyncio
from pathlib import Path
from fastapi_microservices_sdk.templates.builtin_templates.monitoring_service import MonitoringServiceTemplate


async def main():
    """Main example function"""
    
    # Initialize the template
    template = MonitoringServiceTemplate()
    
    # Define template variables
    variables = {
        "service_name": "platform_monitoring",
        "service_description": "Comprehensive monitoring service for microservices platform",
        "service_version": "1.0.0",
        "service_port": 8002,
        "metrics_backend": "prometheus",
        "dashboard_backend": "grafana",
        "alert_backend": "alertmanager",
        "metrics_port": 9090,
        "dashboard_port": 3000,
        "alert_port": 9093,
        "custom_metrics": [
            {
                "name": "business_transactions_total",
                "type": "counter",
                "description": "Total number of business transactions",
                "labels": ["transaction_type", "status"]
            },
            {
                "name": "active_users",
                "type": "gauge",
                "description": "Number of active users",
                "labels": ["region"]
            },
            {
                "name": "request_processing_time",
                "type": "histogram",
                "description": "Request processing time in seconds",
                "labels": ["endpoint", "method"]
            },
            {
                "name": "cache_hit_ratio",
                "type": "summary",
                "description": "Cache hit ratio percentage",
                "labels": ["cache_type"]
            }
        ],
        "dashboards": [
            {
                "name": "system_overview",
                "title": "System Overview Dashboard",
                "panels": [
                    {"type": "graph", "title": "CPU Usage", "query": "cpu_usage_percent"},
                    {"type": "graph", "title": "Memory Usage", "query": "memory_usage_bytes"},
                    {"type": "graph", "title": "Request Rate", "query": "rate(http_requests_total[5m])"}
                ]
            },
            {
                "name": "application_metrics",
                "title": "Application Metrics Dashboard",
                "panels": [
                    {"type": "graph", "title": "Business Transactions", "query": "business_transactions_total"},
                    {"type": "singlestat", "title": "Active Users", "query": "active_users"},
                    {"type": "heatmap", "title": "Response Times", "query": "request_processing_time"}
                ]
            }
        ],
        "alert_rules": [
            {
                "name": "high_cpu_usage",
                "expression": "cpu_usage_percent",
                "threshold": 80.0,
                "duration": "5m",
                "severity": "warning",
                "description": "CPU usage is above 80% for 5 minutes"
            },
            {
                "name": "high_memory_usage",
                "expression": "memory_usage_percent",
                "threshold": 90.0,
                "duration": "3m",
                "severity": "critical",
                "description": "Memory usage is above 90% for 3 minutes"
            },
            {
                "name": "high_error_rate",
                "expression": "rate(http_requests_total{status=~'5..'}[5m])",
                "threshold": 0.1,
                "duration": "2m",
                "severity": "critical",
                "description": "Error rate is above 10% for 2 minutes"
            }
        ],
        "notification_channels": [
            {
                "type": "email",
                "config": {
                    "to": ["ops-team@example.com", "dev-team@example.com"],
                    "subject": "Platform Alert: {{ .GroupLabels.alertname }}"
                }
            },
            {
                "type": "slack",
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/...",
                    "channel": "#alerts",
                    "username": "AlertManager"
                }
            }
        ],
        "enable_custom_metrics": True,
        "enable_health_checks": True,
        "enable_performance_profiling": True,
        "enable_log_aggregation": True,
        "enable_distributed_tracing": True,
        "enable_capacity_planning": True,
        "enable_sla_monitoring": True,
        "scrape_interval": "15s",
        "evaluation_interval": "15s",
        "retention_days": 30
    }
    
    # Validate variables
    print("🔍 Validating template variables...")
    validation_errors = template.validate_variables(variables)
    
    if validation_errors:
        print("❌ Validation errors found:")
        for error in validation_errors:
            print(f"  - {error}")
        return
    
    print("✅ Variables validated successfully!")
    
    # Generate the service
    output_dir = Path("./generated_services/platform_monitoring")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Generating monitoring service at {output_dir}...")
    
    try:
        generated_files = template.generate_files(variables, output_dir)
        
        print(f"✅ Successfully generated {len(generated_files)} files!")
        print("\n📁 Generated files:")
        
        for file_path in sorted(generated_files):
            relative_path = file_path.relative_to(output_dir)
            print(f"  - {relative_path}")
        
        print(f"\n🎉 Monitoring service '{variables['service_name']}' generated successfully!")
        print(f"📍 Location: {output_dir.absolute()}")
        
        # Display next steps
        print("\n🚀 Next steps:")
        print("1. Navigate to the generated directory:")
        print(f"   cd {output_dir}")
        print("\n2. Install dependencies:")
        print("   pip install -r requirements.txt")
        print("\n3. Copy and configure environment:")
        print("   cp .env.template .env")
        print("   # Edit .env with your configuration")
        print("\n4. Start the monitoring stack:")
        print("   docker-compose up -d")
        print("\n5. Run the service:")
        print("   python -m uvicorn app.main:app --reload")
        print("\n6. Access the services:")
        print(f"   - Monitoring API: http://localhost:{variables['service_port']}")
        print(f"   - Prometheus: http://localhost:{variables['metrics_port']}")
        print(f"   - Grafana: http://localhost:{variables['dashboard_port']}")
        print(f"   - AlertManager: http://localhost:{variables['alert_port']}")
        print(f"   - API Docs: http://localhost:{variables['service_port']}/docs")
        
    except Exception as e:
        print(f"❌ Error generating service: {e}")
        raise


def demonstrate_template_features():
    """Demonstrate template features"""
    
    print("🎯 Monitoring Service Template Features:")
    print("\n📋 Core Features:")
    print("  ✅ Prometheus metrics collection and aggregation")
    print("  ✅ Grafana dashboard integration and templates")
    print("  ✅ AlertManager integration with notification channels")
    print("  ✅ Custom metrics collection from multiple sources")
    print("  ✅ Health check aggregation and reporting")
    print("  ✅ Performance profiling and optimization insights")
    print("  ✅ Log aggregation and analysis")
    print("  ✅ Distributed tracing integration")
    print("  ✅ Capacity planning and forecasting")
    print("  ✅ SLA monitoring and reporting")
    
    print("\n🔧 Supported Technologies:")
    print("  📊 Metrics: Prometheus, InfluxDB, DataDog, New Relic")
    print("  📈 Dashboards: Grafana, Kibana, DataDog, New Relic")
    print("  🚨 Alerts: AlertManager, PagerDuty, Slack, Email")
    print("  🔍 Tracing: OpenTelemetry, Jaeger, Zipkin")
    
    print("\n🏗️ Generated Structure:")
    print("  📁 app/")
    print("    📁 metrics/         # Metrics collection and management")
    print("    📁 dashboards/      # Dashboard creation and management")
    print("    📁 alerts/          # Alert rules and notifications")
    print("    📁 health/          # Health check aggregation")
    print("    📁 profiling/       # Performance profiling")
    print("    📁 logs/            # Log aggregation")
    print("    📁 tracing/         # Distributed tracing")
    print("    📁 capacity/        # Capacity planning")
    print("    📁 sla/             # SLA monitoring")
    print("    📁 api/             # REST API endpoints")
    print("  📁 config/            # Configuration files")
    print("    📁 prometheus/      # Prometheus configuration")
    print("    📁 grafana/         # Grafana dashboards")
    print("    📁 alertmanager/    # AlertManager rules")
    print("  📁 tests/             # Comprehensive test suite")
    print("  📁 docker/            # Docker configuration")
    print("  📁 k8s/               # Kubernetes manifests")


def show_configuration_examples():
    """Show configuration examples"""
    
    print("\n⚙️ Configuration Examples:")
    
    print("\n1. 🏢 Enterprise Monitoring Stack:")
    print("""
    {
        "service_name": "enterprise_monitoring",
        "metrics_backend": "prometheus",
        "dashboard_backend": "grafana",
        "alert_backend": "alertmanager",
        "custom_metrics": [
            {
                "name": "business_kpis_total",
                "type": "counter",
                "description": "Business KPI metrics"
            }
        ],
        "enable_capacity_planning": true,
        "enable_sla_monitoring": true,
        "retention_days": 90
    }
    """)
    
    print("\n2. ☁️ Cloud-Native Monitoring:")
    print("""
    {
        "service_name": "cloud_monitoring",
        "metrics_backend": "datadog",
        "dashboard_backend": "datadog",
        "alert_backend": "pagerduty",
        "enable_distributed_tracing": true,
        "enable_log_aggregation": true,
        "notification_channels": [
            {"type": "pagerduty", "integration_key": "..."}
        ]
    }
    """)
    
    print("\n3. 🚀 Startup Monitoring:")
    print("""
    {
        "service_name": "startup_monitoring",
        "metrics_backend": "prometheus",
        "dashboard_backend": "grafana",
        "alert_backend": "slack",
        "enable_custom_metrics": true,
        "enable_health_checks": true,
        "scrape_interval": "30s",
        "retention_days": 7
    }
    """)


def show_metrics_examples():
    """Show custom metrics examples"""
    
    print("\n📊 Custom Metrics Examples:")
    
    print("\n1. Business Metrics:")
    print("""
    {
        "name": "orders_total",
        "type": "counter",
        "description": "Total number of orders",
        "labels": ["status", "region", "product_category"]
    }
    """)
    
    print("\n2. Performance Metrics:")
    print("""
    {
        "name": "database_query_duration",
        "type": "histogram",
        "description": "Database query execution time",
        "labels": ["query_type", "database"]
    }
    """)
    
    print("\n3. System Metrics:")
    print("""
    {
        "name": "queue_size",
        "type": "gauge",
        "description": "Current queue size",
        "labels": ["queue_name", "priority"]
    }
    """)


def show_dashboard_examples():
    """Show dashboard configuration examples"""
    
    print("\n📈 Dashboard Examples:")
    
    print("\n1. System Overview Dashboard:")
    print("""
    {
        "name": "system_overview",
        "title": "System Overview",
        "panels": [
            {
                "type": "graph",
                "title": "Request Rate",
                "query": "rate(http_requests_total[5m])"
            },
            {
                "type": "singlestat",
                "title": "Error Rate",
                "query": "rate(http_requests_total{status=~'5..'}[5m])"
            }
        ]
    }
    """)
    
    print("\n2. Business Metrics Dashboard:")
    print("""
    {
        "name": "business_metrics",
        "title": "Business KPIs",
        "panels": [
            {
                "type": "graph",
                "title": "Revenue",
                "query": "sum(revenue_total)"
            },
            {
                "type": "table",
                "title": "Top Products",
                "query": "topk(10, sum by (product) (sales_total))"
            }
        ]
    }
    """)


def show_alert_examples():
    """Show alert rule examples"""
    
    print("\n🚨 Alert Rule Examples:")
    
    print("\n1. Infrastructure Alerts:")
    print("""
    {
        "name": "high_cpu_usage",
        "expression": "cpu_usage_percent > 80",
        "threshold": 80.0,
        "duration": "5m",
        "severity": "warning"
    }
    """)
    
    print("\n2. Application Alerts:")
    print("""
    {
        "name": "high_error_rate",
        "expression": "rate(http_requests_total{status=~'5..'}[5m]) > 0.1",
        "threshold": 0.1,
        "duration": "2m",
        "severity": "critical"
    }
    """)
    
    print("\n3. Business Alerts:")
    print("""
    {
        "name": "low_conversion_rate",
        "expression": "conversion_rate < 0.02",
        "threshold": 0.02,
        "duration": "10m",
        "severity": "warning"
    }
    """)


if __name__ == "__main__":
    print("🎯 Monitoring Service Template Example")
    print("=" * 50)
    
    # Show template features
    demonstrate_template_features()
    
    # Show configuration examples
    show_configuration_examples()
    
    # Show metrics examples
    show_metrics_examples()
    
    # Show dashboard examples
    show_dashboard_examples()
    
    # Show alert examples
    show_alert_examples()
    
    # Run the main example
    print("\n🚀 Running Monitoring Service Generation Example...")
    print("=" * 50)
    
    asyncio.run(main())
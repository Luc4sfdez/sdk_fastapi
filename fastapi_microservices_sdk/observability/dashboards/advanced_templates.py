"""
Advanced Dashboard Templates - Pre-built dashboard templates

This module provides advanced dashboard templates for common
monitoring scenarios and microservice patterns.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AdvancedDashboardTemplates:
    """
    Advanced dashboard templates for common monitoring scenarios.
    
    Provides pre-built templates for:
    - Microservice monitoring
    - API performance tracking
    - Infrastructure monitoring
    - Business metrics
    - Error tracking
    """
    
    def __init__(self):
        self.templates = {}
        self._initialize_templates()
        
        logger.info("Advanced dashboard templates initialized")
    
    def _initialize_templates(self) -> None:
        """Initialize all dashboard templates."""
        
        # Microservice Overview Template
        self.templates["microservice_overview"] = {
            "id": "microservice_overview",
            "name": "Microservice Overview",
            "description": "Complete overview dashboard for a microservice",
            "category": "microservices",
            "tags": ["overview", "health", "performance"],
            "config": self._create_microservice_overview_template()
        }
        
        # API Performance Template
        self.templates["api_performance"] = {
            "id": "api_performance",
            "name": "API Performance Dashboard",
            "description": "Detailed API performance monitoring",
            "category": "api",
            "tags": ["performance", "latency", "throughput"],
            "config": self._create_api_performance_template()
        }
        
        # Infrastructure Monitoring Template
        self.templates["infrastructure"] = {
            "id": "infrastructure",
            "name": "Infrastructure Monitoring",
            "description": "System resource monitoring dashboard",
            "category": "infrastructure",
            "tags": ["cpu", "memory", "disk", "network"],
            "config": self._create_infrastructure_template()
        }
        
        # Error Tracking Template
        self.templates["error_tracking"] = {
            "id": "error_tracking",
            "name": "Error Tracking Dashboard",
            "description": "Error monitoring and analysis",
            "category": "errors",
            "tags": ["errors", "exceptions", "debugging"],
            "config": self._create_error_tracking_template()
        }
        
        # Business Metrics Template
        self.templates["business_metrics"] = {
            "id": "business_metrics",
            "name": "Business Metrics Dashboard",
            "description": "Business KPI and metrics tracking",
            "category": "business",
            "tags": ["kpi", "business", "metrics"],
            "config": self._create_business_metrics_template()
        }
        
        # Database Monitoring Template
        self.templates["database_monitoring"] = {
            "id": "database_monitoring",
            "name": "Database Monitoring",
            "description": "Database performance and health monitoring",
            "category": "database",
            "tags": ["database", "queries", "connections"],
            "config": self._create_database_monitoring_template()
        }
        
        # Security Monitoring Template
        self.templates["security_monitoring"] = {
            "id": "security_monitoring",
            "name": "Security Monitoring",
            "description": "Security events and threat monitoring",
            "category": "security",
            "tags": ["security", "threats", "authentication"],
            "config": self._create_security_monitoring_template()
        }
    
    def _create_microservice_overview_template(self) -> Dict[str, Any]:
        """Create microservice overview template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 24
            },
            "refresh_interval": 30,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # Service Health Row
                {
                    "id": "service_health",
                    "type": "metric",
                    "title": "Service Health",
                    "position": {"x": 0, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "up{job=\"$service_name\"}",
                    "visualization_config": {
                        "unit": "bool",
                        "thresholds": [
                            {"value": 0, "color": "red"},
                            {"value": 1, "color": "green"}
                        ],
                        "format": "boolean"
                    }
                },
                {
                    "id": "request_rate",
                    "type": "metric",
                    "title": "Request Rate",
                    "position": {"x": 2, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "rate(http_requests_total{service=\"$service_name\"}[5m])",
                    "visualization_config": {
                        "unit": "reqps",
                        "format": "number",
                        "precision": 1
                    }
                },
                {
                    "id": "error_rate",
                    "type": "metric",
                    "title": "Error Rate",
                    "position": {"x": 4, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "rate(http_requests_total{service=\"$service_name\",status=~\"5..\"}[5m]) / rate(http_requests_total{service=\"$service_name\"}[5m]) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "format": "percentage",
                        "precision": 2,
                        "thresholds": [
                            {"value": 1, "color": "yellow"},
                            {"value": 5, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "response_time_p95",
                    "type": "metric",
                    "title": "Response Time P95",
                    "position": {"x": 6, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "unit": "s",
                        "format": "duration",
                        "precision": 3
                    }
                },
                {
                    "id": "active_connections",
                    "type": "metric",
                    "title": "Active Connections",
                    "position": {"x": 8, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "http_connections_active{service=\"$service_name\"}",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "memory_usage",
                    "type": "gauge",
                    "title": "Memory Usage",
                    "position": {"x": 10, "y": 0, "width": 2, "height": 3},
                    "data_source": "prometheus",
                    "query": "process_resident_memory_bytes{service=\"$service_name\"} / 1024 / 1024",
                    "visualization_config": {
                        "unit": "MB",
                        "min_value": 0,
                        "max_value": 1000,
                        "thresholds": [
                            {"value": 500, "color": "yellow"},
                            {"value": 800, "color": "red"}
                        ]
                    }
                },
                
                # Request Timeline
                {
                    "id": "request_timeline",
                    "type": "line_chart",
                    "title": "Request Rate Timeline",
                    "position": {"x": 0, "y": 3, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "rate(http_requests_total{service=\"$service_name\"}[5m])",
                    "visualization_config": {
                        "unit": "reqps",
                        "legend": True,
                        "fill": False
                    }
                },
                
                # Response Time Timeline
                {
                    "id": "response_time_timeline",
                    "type": "line_chart",
                    "title": "Response Time Percentiles",
                    "position": {"x": 6, "y": 3, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m]))",
                        "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m]))",
                        "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m]))"
                    ],
                    "visualization_config": {
                        "unit": "s",
                        "legend": True,
                        "series_names": ["P50", "P95", "P99"]
                    }
                },
                
                # Status Code Distribution
                {
                    "id": "status_codes",
                    "type": "pie_chart",
                    "title": "HTTP Status Codes",
                    "position": {"x": 0, "y": 9, "width": 4, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum by (status) (rate(http_requests_total{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "legend_position": "right"
                    }
                },
                
                # Top Endpoints
                {
                    "id": "top_endpoints",
                    "type": "table",
                    "title": "Top Endpoints by Request Count",
                    "position": {"x": 4, "y": 9, "width": 8, "height": 6},
                    "data_source": "prometheus",
                    "query": "topk(10, sum by (endpoint) (rate(http_requests_total{service=\"$service_name\"}[5m])))",
                    "visualization_config": {
                        "columns": ["Endpoint", "Requests/sec", "Error Rate"],
                        "sorting": True,
                        "pagination": False
                    }
                }
            ],
            "variables": [
                {
                    "name": "service_name",
                    "type": "query",
                    "query": "label_values(up, job)",
                    "default": "my-service"
                }
            ]
        }
    
    def _create_api_performance_template(self) -> Dict[str, Any]:
        """Create API performance template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 15,
            "time_range": {
                "from": "now-30m",
                "to": "now"
            },
            "components": [
                # Performance Metrics Row
                {
                    "id": "avg_response_time",
                    "type": "metric",
                    "title": "Avg Response Time",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "avg(rate(http_request_duration_seconds_sum{service=\"$service_name\"}[5m]) / rate(http_request_duration_seconds_count{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "unit": "s",
                        "format": "duration",
                        "precision": 3
                    }
                },
                {
                    "id": "throughput",
                    "type": "metric",
                    "title": "Throughput",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "unit": "reqps",
                        "format": "number",
                        "precision": 1
                    }
                },
                {
                    "id": "error_percentage",
                    "type": "metric",
                    "title": "Error Percentage",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{service=\"$service_name\",status=~\"[45]..\"}[5m])) / sum(rate(http_requests_total{service=\"$service_name\"}[5m])) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "format": "percentage",
                        "precision": 2,
                        "thresholds": [
                            {"value": 1, "color": "yellow"},
                            {"value": 5, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "apdex_score",
                    "type": "gauge",
                    "title": "Apdex Score",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "(sum(rate(http_request_duration_seconds_bucket{service=\"$service_name\",le=\"0.5\"}[5m])) + sum(rate(http_request_duration_seconds_bucket{service=\"$service_name\",le=\"2.0\"}[5m])) / 2) / sum(rate(http_request_duration_seconds_count{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "min_value": 0,
                        "max_value": 1,
                        "thresholds": [
                            {"value": 0.5, "color": "red"},
                            {"value": 0.7, "color": "yellow"},
                            {"value": 0.85, "color": "green"}
                        ]
                    }
                },
                
                # Response Time Heatmap
                {
                    "id": "response_time_heatmap",
                    "type": "heatmap",
                    "title": "Response Time Distribution",
                    "position": {"x": 0, "y": 3, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_request_duration_seconds_bucket{service=\"$service_name\"}[5m])) by (le)",
                    "visualization_config": {
                        "unit": "s",
                        "color_scheme": "RdYlGn_r"
                    }
                },
                
                # Endpoint Performance
                {
                    "id": "endpoint_performance",
                    "type": "table",
                    "title": "Endpoint Performance Analysis",
                    "position": {"x": 0, "y": 9, "width": 12, "height": 8},
                    "data_source": "prometheus",
                    "query": "sum by (endpoint) (rate(http_requests_total{service=\"$service_name\"}[5m]))",
                    "visualization_config": {
                        "columns": [
                            "Endpoint",
                            "Requests/sec",
                            "Avg Response Time",
                            "P95 Response Time",
                            "Error Rate %"
                        ],
                        "sorting": True,
                        "pagination": True,
                        "page_size": 20
                    }
                }
            ],
            "variables": [
                {
                    "name": "service_name",
                    "type": "query",
                    "query": "label_values(http_requests_total, service)",
                    "default": "api-service"
                }
            ]
        }
    
    def _create_infrastructure_template(self) -> Dict[str, Any]:
        """Create infrastructure monitoring template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 30,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # System Metrics Row
                {
                    "id": "cpu_usage",
                    "type": "gauge",
                    "title": "CPU Usage",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                    "visualization_config": {
                        "unit": "percent",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 70, "color": "yellow"},
                            {"value": 90, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "memory_usage",
                    "type": "gauge",
                    "title": "Memory Usage",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 80, "color": "yellow"},
                            {"value": 95, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "disk_usage",
                    "type": "gauge",
                    "title": "Disk Usage",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "(1 - (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"})) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 80, "color": "yellow"},
                            {"value": 95, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "load_average",
                    "type": "metric",
                    "title": "Load Average (1m)",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "node_load1",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "precision": 2
                    }
                },
                
                # Resource Timeline
                {
                    "id": "cpu_timeline",
                    "type": "line_chart",
                    "title": "CPU Usage Timeline",
                    "position": {"x": 0, "y": 4, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                    "visualization_config": {
                        "unit": "percent",
                        "fill": True,
                        "legend": False
                    }
                },
                {
                    "id": "memory_timeline",
                    "type": "line_chart",
                    "title": "Memory Usage Timeline",
                    "position": {"x": 6, "y": 4, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "fill": True,
                        "legend": False
                    }
                },
                
                # Network I/O
                {
                    "id": "network_io",
                    "type": "line_chart",
                    "title": "Network I/O",
                    "position": {"x": 0, "y": 10, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "rate(node_network_receive_bytes_total[5m])",
                        "rate(node_network_transmit_bytes_total[5m])"
                    ],
                    "visualization_config": {
                        "unit": "Bps",
                        "legend": True,
                        "series_names": ["Receive", "Transmit"]
                    }
                },
                
                # Disk I/O
                {
                    "id": "disk_io",
                    "type": "line_chart",
                    "title": "Disk I/O",
                    "position": {"x": 6, "y": 10, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "rate(node_disk_read_bytes_total[5m])",
                        "rate(node_disk_written_bytes_total[5m])"
                    ],
                    "visualization_config": {
                        "unit": "Bps",
                        "legend": True,
                        "series_names": ["Read", "Write"]
                    }
                }
            ]
        }
    
    def _create_error_tracking_template(self) -> Dict[str, Any]:
        """Create error tracking template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 30,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # Error Metrics
                {
                    "id": "total_errors",
                    "type": "metric",
                    "title": "Total Errors",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{status=~\"[45]..\"}[5m]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "precision": 0
                    }
                },
                {
                    "id": "error_rate",
                    "type": "metric",
                    "title": "Error Rate",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{status=~\"[45]..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "format": "percentage",
                        "precision": 2,
                        "thresholds": [
                            {"value": 1, "color": "yellow"},
                            {"value": 5, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "critical_errors",
                    "type": "metric",
                    "title": "5xx Errors",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{status=~\"5..\"}[5m]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "precision": 0
                    }
                },
                {
                    "id": "client_errors",
                    "type": "metric",
                    "title": "4xx Errors",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(http_requests_total{status=~\"4..\"}[5m]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "precision": 0
                    }
                },
                
                # Error Timeline
                {
                    "id": "error_timeline",
                    "type": "line_chart",
                    "title": "Error Rate Timeline",
                    "position": {"x": 0, "y": 3, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "sum(rate(http_requests_total{status=~\"4..\"}[5m]))",
                        "sum(rate(http_requests_total{status=~\"5..\"}[5m]))"
                    ],
                    "visualization_config": {
                        "unit": "short",
                        "legend": True,
                        "series_names": ["4xx Errors", "5xx Errors"]
                    }
                },
                
                # Error Distribution
                {
                    "id": "error_by_status",
                    "type": "pie_chart",
                    "title": "Errors by Status Code",
                    "position": {"x": 0, "y": 9, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum by (status) (rate(http_requests_total{status=~\"[45]..\"}[5m]))"
                },
                
                # Top Error Endpoints
                {
                    "id": "error_endpoints",
                    "type": "table",
                    "title": "Top Error Endpoints",
                    "position": {"x": 6, "y": 9, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "topk(10, sum by (endpoint) (rate(http_requests_total{status=~\"[45]..\"}[5m])))",
                    "visualization_config": {
                        "columns": ["Endpoint", "Error Rate", "Status Codes"],
                        "sorting": True
                    }
                }
            ]
        }
    
    def _create_business_metrics_template(self) -> Dict[str, Any]:
        """Create business metrics template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 16
            },
            "refresh_interval": 300,  # 5 minutes
            "time_range": {
                "from": "now-24h",
                "to": "now"
            },
            "components": [
                # Key Business Metrics
                {
                    "id": "daily_active_users",
                    "type": "metric",
                    "title": "Daily Active Users",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "count(count by (user_id) (user_activity_total[24h]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "revenue_today",
                    "type": "metric",
                    "title": "Revenue Today",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(revenue_total[24h])",
                    "visualization_config": {
                        "unit": "currency",
                        "format": "currency",
                        "precision": 2
                    }
                },
                {
                    "id": "conversion_rate",
                    "type": "metric",
                    "title": "Conversion Rate",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(conversions_total[24h]) / sum(visits_total[24h]) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "format": "percentage",
                        "precision": 2
                    }
                },
                {
                    "id": "avg_order_value",
                    "type": "metric",
                    "title": "Avg Order Value",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(revenue_total[24h]) / sum(orders_total[24h])",
                    "visualization_config": {
                        "unit": "currency",
                        "format": "currency",
                        "precision": 2
                    }
                },
                
                # Business Trends
                {
                    "id": "user_growth",
                    "type": "line_chart",
                    "title": "User Growth Trend",
                    "position": {"x": 0, "y": 3, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "count(count by (user_id) (user_registrations_total))",
                    "visualization_config": {
                        "unit": "short",
                        "fill": True
                    }
                },
                {
                    "id": "revenue_trend",
                    "type": "line_chart",
                    "title": "Revenue Trend",
                    "position": {"x": 6, "y": 3, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum(rate(revenue_total[1h]))",
                    "visualization_config": {
                        "unit": "currency",
                        "fill": True
                    }
                },
                
                # Feature Usage
                {
                    "id": "feature_usage",
                    "type": "bar_chart",
                    "title": "Feature Usage",
                    "position": {"x": 0, "y": 9, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum by (feature) (rate(feature_usage_total[24h]))",
                    "visualization_config": {
                        "unit": "short",
                        "orientation": "horizontal"
                    }
                }
            ]
        }
    
    def _create_database_monitoring_template(self) -> Dict[str, Any]:
        """Create database monitoring template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 30,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # Database Health
                {
                    "id": "db_connections_active",
                    "type": "metric",
                    "title": "Active Connections",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "db_connections_active",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "db_query_duration",
                    "type": "metric",
                    "title": "Avg Query Duration",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "avg(db_query_duration_seconds)",
                    "visualization_config": {
                        "unit": "s",
                        "format": "duration",
                        "precision": 3
                    }
                },
                {
                    "id": "db_queries_per_second",
                    "type": "metric",
                    "title": "Queries/sec",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "rate(db_queries_total[5m])",
                    "visualization_config": {
                        "unit": "qps",
                        "format": "number",
                        "precision": 1
                    }
                },
                {
                    "id": "db_slow_queries",
                    "type": "metric",
                    "title": "Slow Queries",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "rate(db_slow_queries_total[5m])",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "precision": 0
                    }
                }
            ]
        }
    
    def _create_security_monitoring_template(self) -> Dict[str, Any]:
        """Create security monitoring template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 16
            },
            "refresh_interval": 60,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # Security Metrics
                {
                    "id": "failed_logins",
                    "type": "metric",
                    "title": "Failed Logins",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(auth_failures_total[5m]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "thresholds": [
                            {"value": 10, "color": "yellow"},
                            {"value": 50, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "blocked_ips",
                    "type": "metric",
                    "title": "Blocked IPs",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "count(security_blocked_ips)",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "suspicious_activity",
                    "type": "metric",
                    "title": "Suspicious Activity",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(rate(security_alerts_total[5m]))",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "active_sessions",
                    "type": "metric",
                    "title": "Active Sessions",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "count(user_sessions_active)",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                }
            ]
        }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get templates by category."""
        return [
            template for template in self.templates.values()
            if template["category"] == category
        ]
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """Get all available templates."""
        return list(self.templates.values())
    
    def get_template_categories(self) -> List[str]:
        """Get all template categories."""
        categories = set()
        for template in self.templates.values():
            categories.add(template["category"])
        return sorted(list(categories))
    
    def _create_database_monitoring_template(self) -> Dict[str, Any]:
        """Create database monitoring template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 30,
            "time_range": {
                "from": "now-1h",
                "to": "now"
            },
            "components": [
                # Database Health Metrics
                {
                    "id": "db_connections",
                    "type": "gauge",
                    "title": "Active Connections",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "pg_stat_activity_count{state=\"active\"}",
                    "visualization_config": {
                        "unit": "short",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 70, "color": "yellow"},
                            {"value": 90, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "query_duration",
                    "type": "metric",
                    "title": "Avg Query Duration",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "avg(pg_stat_statements_mean_time_ms)",
                    "visualization_config": {
                        "unit": "ms",
                        "format": "duration",
                        "precision": 2
                    }
                },
                {
                    "id": "db_size",
                    "type": "metric",
                    "title": "Database Size",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "pg_database_size_bytes / 1024 / 1024 / 1024",
                    "visualization_config": {
                        "unit": "GB",
                        "format": "bytes",
                        "precision": 2
                    }
                },
                {
                    "id": "cache_hit_ratio",
                    "type": "gauge",
                    "title": "Cache Hit Ratio",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 4},
                    "data_source": "prometheus",
                    "query": "pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 90, "color": "red"},
                            {"value": 95, "color": "yellow"},
                            {"value": 99, "color": "green"}
                        ]
                    }
                },
                
                # Query Performance
                {
                    "id": "query_rate",
                    "type": "line_chart",
                    "title": "Query Rate",
                    "position": {"x": 0, "y": 4, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "rate(pg_stat_database_xact_commit[5m]) + rate(pg_stat_database_xact_rollback[5m])",
                    "visualization_config": {
                        "unit": "qps",
                        "legend": False
                    }
                },
                
                # Connection Pool
                {
                    "id": "connection_pool",
                    "type": "line_chart",
                    "title": "Connection Pool Status",
                    "position": {"x": 6, "y": 4, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "pg_stat_activity_count{state=\"active\"}",
                        "pg_stat_activity_count{state=\"idle\"}"
                    ],
                    "visualization_config": {
                        "unit": "short",
                        "legend": True,
                        "series_names": ["Active", "Idle"]
                    }
                },
                
                # Slow Queries
                {
                    "id": "slow_queries",
                    "type": "table",
                    "title": "Slowest Queries",
                    "position": {"x": 0, "y": 10, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": "topk(10, pg_stat_statements_mean_time_ms)",
                    "visualization_config": {
                        "columns": ["Query", "Avg Duration", "Calls", "Total Time"],
                        "sorting": True,
                        "pagination": True
                    }
                }
            ]
        }
    
    def _create_security_monitoring_template(self) -> Dict[str, Any]:
        """Create security monitoring template."""
        return {
            "layout": {
                "type": "grid",
                "columns": 12,
                "rows": 20
            },
            "refresh_interval": 60,
            "time_range": {
                "from": "now-24h",
                "to": "now"
            },
            "components": [
                # Security Metrics
                {
                    "id": "failed_logins",
                    "type": "metric",
                    "title": "Failed Logins (24h)",
                    "position": {"x": 0, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(auth_failures_total[24h])",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "thresholds": [
                            {"value": 100, "color": "yellow"},
                            {"value": 1000, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "blocked_ips",
                    "type": "metric",
                    "title": "Blocked IPs",
                    "position": {"x": 3, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "count(blocked_ips_total)",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number"
                    }
                },
                {
                    "id": "suspicious_activity",
                    "type": "metric",
                    "title": "Suspicious Activities",
                    "position": {"x": 6, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(security_alerts_total[24h])",
                    "visualization_config": {
                        "unit": "short",
                        "format": "number",
                        "thresholds": [
                            {"value": 10, "color": "yellow"},
                            {"value": 50, "color": "red"}
                        ]
                    }
                },
                {
                    "id": "auth_success_rate",
                    "type": "gauge",
                    "title": "Auth Success Rate",
                    "position": {"x": 9, "y": 0, "width": 3, "height": 3},
                    "data_source": "prometheus",
                    "query": "sum(auth_success_total[24h]) / (sum(auth_success_total[24h]) + sum(auth_failures_total[24h])) * 100",
                    "visualization_config": {
                        "unit": "percent",
                        "min_value": 0,
                        "max_value": 100,
                        "thresholds": [
                            {"value": 90, "color": "red"},
                            {"value": 95, "color": "yellow"},
                            {"value": 99, "color": "green"}
                        ]
                    }
                },
                
                # Security Events Timeline
                {
                    "id": "security_events",
                    "type": "line_chart",
                    "title": "Security Events Timeline",
                    "position": {"x": 0, "y": 3, "width": 12, "height": 6},
                    "data_source": "prometheus",
                    "query": [
                        "rate(auth_failures_total[5m])",
                        "rate(security_alerts_total[5m])",
                        "rate(blocked_requests_total[5m])"
                    ],
                    "visualization_config": {
                        "unit": "short",
                        "legend": True,
                        "series_names": ["Auth Failures", "Security Alerts", "Blocked Requests"]
                    }
                },
                
                # Top Threat Sources
                {
                    "id": "threat_sources",
                    "type": "table",
                    "title": "Top Threat Sources",
                    "position": {"x": 0, "y": 9, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "topk(10, sum by (source_ip) (security_alerts_total[24h]))",
                    "visualization_config": {
                        "columns": ["IP Address", "Alerts", "Country", "Status"],
                        "sorting": True
                    }
                },
                
                # Attack Types
                {
                    "id": "attack_types",
                    "type": "pie_chart",
                    "title": "Attack Types Distribution",
                    "position": {"x": 6, "y": 9, "width": 6, "height": 6},
                    "data_source": "prometheus",
                    "query": "sum by (attack_type) (security_alerts_total[24h])"
                }
            ]
        }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available templates, optionally filtered by category."""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        return templates
    
    def get_categories(self) -> List[str]:
        """Get all available template categories."""
        categories = set()
        for template in self.templates.values():
            if template.get("category"):
                categories.add(template["category"])
        
        return sorted(list(categories))
    
    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """Search templates by name, description, or tags."""
        query = query.lower()
        results = []
        
        for template in self.templates.values():
            # Search in name
            if query in template["name"].lower():
                results.append(template)
                continue
            
            # Search in description
            if query in template["description"].lower():
                results.append(template)
                continue
            
            # Search in tags
            tags = template.get("tags", [])
            if any(query in tag.lower() for tag in tags):
                results.append(template)
                continue
        
        return results
    
    def create_custom_template(self, template_config: Dict[str, Any]) -> str:
        """Create a custom template."""
        template_id = template_config.get("id")
        if not template_id:
            template_id = f"custom_{len(self.templates)}"
        
        self.templates[template_id] = {
            "id": template_id,
            "name": template_config.get("name", "Custom Template"),
            "description": template_config.get("description", "Custom dashboard template"),
            "category": template_config.get("category", "custom"),
            "tags": template_config.get("tags", ["custom"]),
            "config": template_config.get("config", {}),
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Created custom template: {template_id}")
        return template_id
    
    def update_template(self, template_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing template."""
        if template_id not in self.templates:
            return False
        
        template = self.templates[template_id]
        template.update(updates)
        template["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"Updated template: {template_id}")
        return True
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id not in self.templates:
            return False
        
        # Don't allow deletion of built-in templates
        template = self.templates[template_id]
        if template.get("category") != "custom":
            logger.warning(f"Cannot delete built-in template: {template_id}")
            return False
        
        del self.templates[template_id]
        logger.info(f"Deleted template: {template_id}")
        return True
    
    def export_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Export a template configuration."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        return {
            "template": template,
            "exported_at": datetime.now().isoformat(),
            "version": "1.0"
        }
    
    def import_template(self, template_data: Dict[str, Any]) -> Optional[str]:
        """Import a template configuration."""
        try:
            template = template_data.get("template")
            if not template:
                return None
            
            template_id = template.get("id")
            if not template_id:
                template_id = f"imported_{len(self.templates)}"
                template["id"] = template_id
            
            # Mark as imported
            template["category"] = "imported"
            template["imported_at"] = datetime.now().isoformat()
            
            self.templates[template_id] = template
            logger.info(f"Imported template: {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            return None
    
    def validate_template(self, template_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a template configuration."""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ["layout", "components"]
        for field in required_fields:
            if field not in template_config:
                errors.append(f"Missing required field: {field}")
        
        # Validate layout
        layout = template_config.get("layout", {})
        if "type" not in layout:
            errors.append("Layout must specify a type")
        
        # Validate components
        components = template_config.get("components", [])
        if not components:
            warnings.append("Template has no components")
        
        for i, component in enumerate(components):
            if "id" not in component:
                errors.append(f"Component {i} missing required 'id' field")
            if "type" not in component:
                errors.append(f"Component {i} missing required 'type' field")
            if "position" not in component:
                errors.append(f"Component {i} missing required 'position' field")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get statistics about available templates."""
        stats = {
            "total_templates": len(self.templates),
            "categories": {},
            "most_common_tags": {},
            "template_types": {}
        }
        
        # Count by category
        for template in self.templates.values():
            category = template.get("category", "unknown")
            stats["categories"][category] = stats["categories"].get(category, 0) + 1
        
        # Count tags
        for template in self.templates.values():
            for tag in template.get("tags", []):
                stats["most_common_tags"][tag] = stats["most_common_tags"].get(tag, 0) + 1
        
        # Count component types
        for template in self.templates.values():
            components = template.get("config", {}).get("components", [])
            for component in components:
                comp_type = component.get("type", "unknown")
                stats["template_types"][comp_type] = stats["template_types"].get(comp_type, 0) + 1
        
        return stats


# Template utility functions
def create_dashboard_from_template(template_id: str, 
                                 customizations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a dashboard configuration from a template."""
    templates = AdvancedDashboardTemplates()
    template = templates.get_template(template_id)
    
    if not template:
        raise ValueError(f"Template not found: {template_id}")
    
    # Start with template config
    dashboard_config = template["config"].copy()
    
    # Apply customizations
    if customizations:
        # Update variables
        if "variables" in customizations:
            dashboard_config["variables"] = customizations["variables"]
        
        # Update time range
        if "time_range" in customizations:
            dashboard_config["time_range"] = customizations["time_range"]
        
        # Update refresh interval
        if "refresh_interval" in customizations:
            dashboard_config["refresh_interval"] = customizations["refresh_interval"]
        
        # Update component configurations
        if "component_overrides" in customizations:
            for component_id, overrides in customizations["component_overrides"].items():
                for component in dashboard_config.get("components", []):
                    if component.get("id") == component_id:
                        component.update(overrides)
                        break
    
    # Add metadata
    dashboard_config["metadata"] = {
        "template_id": template_id,
        "template_name": template["name"],
        "created_at": datetime.now().isoformat(),
        "customized": bool(customizations)
    }
    
    return dashboard_config


def get_recommended_templates(service_type: str, 
                            monitoring_focus: List[str]) -> List[Dict[str, Any]]:
    """Get recommended templates based on service type and monitoring focus."""
    templates = AdvancedDashboardTemplates()
    all_templates = templates.list_templates()
    
    recommendations = []
    
    # Service type mapping
    service_mappings = {
        "api": ["microservice_overview", "api_performance", "error_tracking"],
        "web": ["microservice_overview", "api_performance", "business_metrics"],
        "database": ["database_monitoring", "infrastructure"],
        "worker": ["infrastructure", "error_tracking"],
        "gateway": ["api_performance", "security_monitoring", "infrastructure"]
    }
    
    # Focus area mapping
    focus_mappings = {
        "performance": ["api_performance", "infrastructure"],
        "errors": ["error_tracking"],
        "business": ["business_metrics"],
        "security": ["security_monitoring"],
        "infrastructure": ["infrastructure", "database_monitoring"]
    }
    
    # Get templates for service type
    service_templates = service_mappings.get(service_type, [])
    
    # Get templates for focus areas
    focus_templates = []
    for focus in monitoring_focus:
        focus_templates.extend(focus_mappings.get(focus, []))
    
    # Combine and deduplicate
    recommended_ids = list(set(service_templates + focus_templates))
    
    # Get template details
    for template in all_templates:
        if template["id"] in recommended_ids:
            recommendations.append(template)
    
    return recommendations


# Export the main class and utility functions
__all__ = [
    "AdvancedDashboardTemplates",
    "create_dashboard_from_template",
    "get_recommended_templates"
]
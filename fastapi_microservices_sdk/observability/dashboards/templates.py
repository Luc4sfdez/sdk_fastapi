"""
Dashboard Templates - Pre-built dashboard templates and management

This module provides dashboard template management with pre-built templates
for common use cases and custom template creation.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json
import uuid

from .exceptions import DashboardTemplateError

logger = logging.getLogger(__name__)


@dataclass
class DashboardTemplate:
    """Dashboard template definition."""
    id: str
    name: str
    description: str
    category: str
    config: Dict[str, Any]
    tags: List[str]
    author: str
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    is_default: bool = False
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "config": self.config,
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_default": self.is_default
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardTemplate":
        """Create template from dictionary."""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            config=data["config"],
            tags=data.get("tags", []),
            author=data["author"],
            version=data.get("version", "1.0.0"),
            created_at=created_at,
            is_default=data.get("is_default", False)
        )


class DashboardTemplateManager:
    """
    Dashboard template manager for creating and managing templates.
    
    Provides functionality for:
    - Loading default templates
    - Creating custom templates
    - Template validation
    - Template categorization
    """
    
    def __init__(self):
        self.templates: Dict[str, DashboardTemplate] = {}
        self.categories: Dict[str, List[str]] = {}
        self.is_initialized = False
        
        logger.info("Dashboard template manager initialized")
    
    async def initialize(self) -> None:
        """Initialize template manager."""
        if self.is_initialized:
            return
        
        try:
            # Load default templates
            await self._load_default_templates()
            
            # Build category index
            await self._build_category_index()
            
            self.is_initialized = True
            logger.info(f"Template manager initialized with {len(self.templates)} templates")
            
        except Exception as e:
            logger.error(f"Failed to initialize template manager: {e}")
            raise DashboardTemplateError(f"Template manager initialization failed: {e}")
    
    async def get_template(self, template_id: str) -> Optional[DashboardTemplate]:
        """
        Get template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template if found, None otherwise
        """
        return self.templates.get(template_id)
    
    async def get_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> List[DashboardTemplate]:
        """
        Get templates with optional filtering.
        
        Args:
            category: Filter by category
            tags: Filter by tags
            author: Filter by author
            
        Returns:
            List of matching templates
        """
        templates = []
        
        for template in self.templates.values():
            # Apply filters
            if category and template.category != category:
                continue
            
            if tags and not any(tag in template.tags for tag in tags):
                continue
            
            if author and template.author != author:
                continue
            
            templates.append(template)
        
        return templates
    
    async def get_default_templates(self) -> List[DashboardTemplate]:
        """
        Get default templates.
        
        Returns:
            List of default templates
        """
        return [t for t in self.templates.values() if t.is_default]
    
    async def get_categories(self) -> Dict[str, List[str]]:
        """
        Get template categories with template IDs.
        
        Returns:
            Dictionary of categories and template IDs
        """
        return self.categories.copy()
    
    async def create_template(
        self,
        name: str,
        description: str,
        category: str,
        config: Dict[str, Any],
        author: str,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0"
    ) -> DashboardTemplate:
        """
        Create a new template.
        
        Args:
            name: Template name
            description: Template description
            category: Template category
            config: Dashboard configuration
            author: Template author
            tags: Optional tags
            version: Template version
            
        Returns:
            Created template
        """
        try:
            # Validate configuration
            await self._validate_template_config(config)
            
            # Generate unique ID
            template_id = str(uuid.uuid4())
            
            # Create template
            template = DashboardTemplate(
                id=template_id,
                name=name,
                description=description,
                category=category,
                config=config,
                tags=tags or [],
                author=author,
                version=version
            )
            
            # Store template
            self.templates[template_id] = template
            
            # Update category index
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(template_id)
            
            logger.info(f"Template created: {template_id} ({name})")
            return template
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise DashboardTemplateError(f"Template creation failed: {e}")
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any]
    ) -> DashboardTemplate:
        """
        Update template.
        
        Args:
            template_id: Template ID
            updates: Updates to apply
            
        Returns:
            Updated template
        """
        if template_id not in self.templates:
            raise DashboardTemplateError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        # Validate updated config if changed
        if "config" in updates:
            await self._validate_template_config(template.config)
        
        logger.info(f"Template updated: {template_id}")
        return template
    
    async def delete_template(self, template_id: str) -> None:
        """
        Delete template.
        
        Args:
            template_id: Template ID
        """
        if template_id not in self.templates:
            raise DashboardTemplateError(f"Template not found: {template_id}")
        
        template = self.templates[template_id]
        
        # Don't allow deletion of default templates
        if template.is_default:
            raise DashboardTemplateError("Cannot delete default template")
        
        # Remove from category index
        if template.category in self.categories:
            if template_id in self.categories[template.category]:
                self.categories[template.category].remove(template_id)
        
        # Remove template
        del self.templates[template_id]
        
        logger.info(f"Template deleted: {template_id}")
    
    async def export_template(self, template_id: str) -> Dict[str, Any]:
        """
        Export template to dictionary.
        
        Args:
            template_id: Template ID
            
        Returns:
            Template data
        """
        if template_id not in self.templates:
            raise DashboardTemplateError(f"Template not found: {template_id}")
        
        return self.templates[template_id].to_dict()
    
    async def import_template(self, template_data: Dict[str, Any]) -> DashboardTemplate:
        """
        Import template from dictionary.
        
        Args:
            template_data: Template data
            
        Returns:
            Imported template
        """
        try:
            # Validate template data
            required_fields = ["name", "description", "category", "config", "author"]
            for field in required_fields:
                if field not in template_data:
                    raise DashboardTemplateError(f"Missing required field: {field}")
            
            # Generate new ID if not provided
            if "id" not in template_data:
                template_data["id"] = str(uuid.uuid4())
            
            # Create template
            template = DashboardTemplate.from_dict(template_data)
            
            # Validate configuration
            await self._validate_template_config(template.config)
            
            # Store template
            self.templates[template.id] = template
            
            # Update category index
            if template.category not in self.categories:
                self.categories[template.category] = []
            self.categories[template.category].append(template.id)
            
            logger.info(f"Template imported: {template.id} ({template.name})")
            return template
            
        except Exception as e:
            logger.error(f"Failed to import template: {e}")
            raise DashboardTemplateError(f"Template import failed: {e}")
    
    async def _load_default_templates(self) -> None:
        """Load default dashboard templates."""
        default_templates = [
            # System Overview Template
            {
                "id": "system-overview",
                "name": "System Overview",
                "description": "Comprehensive system monitoring dashboard",
                "category": "monitoring",
                "author": "FastAPI Microservices SDK",
                "tags": ["system", "monitoring", "overview"],
                "is_default": True,
                "config": {
                    "layout": {
                        "type": "grid",
                        "columns": 12,
                        "rows": 20
                    },
                    "components": [
                        {
                            "id": "cpu-usage",
                            "type": "line_chart",
                            "title": "CPU Usage",
                            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
                            "data_source": "metrics",
                            "query": "cpu_usage_percent",
                            "visualization_config": {
                                "chart_type": "line",
                                "y_axis": {"min": 0, "max": 100, "unit": "%"}
                            }
                        },
                        {
                            "id": "memory-usage",
                            "type": "line_chart",
                            "title": "Memory Usage",
                            "position": {"x": 6, "y": 0, "width": 6, "height": 4},
                            "data_source": "metrics",
                            "query": "memory_usage_percent",
                            "visualization_config": {
                                "chart_type": "line",
                                "y_axis": {"min": 0, "max": 100, "unit": "%"}
                            }
                        },
                        {
                            "id": "request-rate",
                            "type": "metric_card",
                            "title": "Request Rate",
                            "position": {"x": 0, "y": 4, "width": 3, "height": 2},
                            "data_source": "metrics",
                            "query": "http_requests_per_second",
                            "visualization_config": {
                                "format": "number",
                                "unit": "req/s",
                                "precision": 1
                            }
                        },
                        {
                            "id": "error-rate",
                            "type": "metric_card",
                            "title": "Error Rate",
                            "position": {"x": 3, "y": 4, "width": 3, "height": 2},
                            "data_source": "metrics",
                            "query": "http_error_rate",
                            "visualization_config": {
                                "format": "percentage",
                                "precision": 2,
                                "threshold": {"warning": 1, "critical": 5}
                            }
                        }
                    ]
                }
            },
            
            # Application Performance Template
            {
                "id": "app-performance",
                "name": "Application Performance",
                "description": "Application performance monitoring dashboard",
                "category": "performance",
                "author": "FastAPI Microservices SDK",
                "tags": ["performance", "apm", "latency"],
                "is_default": True,
                "config": {
                    "layout": {
                        "type": "grid",
                        "columns": 12,
                        "rows": 20
                    },
                    "components": [
                        {
                            "id": "response-time",
                            "type": "line_chart",
                            "title": "Response Time",
                            "position": {"x": 0, "y": 0, "width": 8, "height": 6},
                            "data_source": "metrics",
                            "query": "http_request_duration_seconds",
                            "visualization_config": {
                                "chart_type": "line",
                                "y_axis": {"unit": "ms"}
                            }
                        },
                        {
                            "id": "throughput",
                            "type": "bar_chart",
                            "title": "Throughput by Endpoint",
                            "position": {"x": 8, "y": 0, "width": 4, "height": 6},
                            "data_source": "metrics",
                            "query": "http_requests_total",
                            "visualization_config": {
                                "chart_type": "bar",
                                "orientation": "horizontal"
                            }
                        }
                    ]
                }
            },
            
            # Database Monitoring Template
            {
                "id": "database-monitoring",
                "name": "Database Monitoring",
                "description": "Database performance and health monitoring",
                "category": "database",
                "author": "FastAPI Microservices SDK",
                "tags": ["database", "performance", "connections"],
                "is_default": True,
                "config": {
                    "layout": {
                        "type": "grid",
                        "columns": 12,
                        "rows": 20
                    },
                    "components": [
                        {
                            "id": "db-connections",
                            "type": "gauge",
                            "title": "Database Connections",
                            "position": {"x": 0, "y": 0, "width": 4, "height": 4},
                            "data_source": "metrics",
                            "query": "db_connections_active",
                            "visualization_config": {
                                "min_value": 0,
                                "max_value": 100,
                                "thresholds": [
                                    {"value": 70, "color": "warning"},
                                    {"value": 90, "color": "critical"}
                                ]
                            }
                        },
                        {
                            "id": "query-duration",
                            "type": "histogram",
                            "title": "Query Duration Distribution",
                            "position": {"x": 4, "y": 0, "width": 8, "height": 4},
                            "data_source": "metrics",
                            "query": "db_query_duration_seconds",
                            "visualization_config": {
                                "bins": 20,
                                "x_axis": {"unit": "ms"}
                            }
                        }
                    ]
                }
            },
            
            # Security Dashboard Template
            {
                "id": "security-dashboard",
                "name": "Security Dashboard",
                "description": "Security monitoring and threat detection",
                "category": "security",
                "author": "FastAPI Microservices SDK",
                "tags": ["security", "threats", "authentication"],
                "is_default": True,
                "config": {
                    "layout": {
                        "type": "grid",
                        "columns": 12,
                        "rows": 20
                    },
                    "components": [
                        {
                            "id": "failed-logins",
                            "type": "line_chart",
                            "title": "Failed Login Attempts",
                            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
                            "data_source": "logs",
                            "query": "failed_authentication_attempts",
                            "visualization_config": {
                                "chart_type": "line",
                                "color": "danger"
                            }
                        },
                        {
                            "id": "threat-level",
                            "type": "gauge",
                            "title": "Threat Level",
                            "position": {"x": 6, "y": 0, "width": 3, "height": 4},
                            "data_source": "security",
                            "query": "current_threat_level",
                            "visualization_config": {
                                "min_value": 0,
                                "max_value": 10,
                                "thresholds": [
                                    {"value": 3, "color": "success"},
                                    {"value": 6, "color": "warning"},
                                    {"value": 8, "color": "danger"}
                                ]
                            }
                        }
                    ]
                }
            }
        ]
        
        # Load templates
        for template_data in default_templates:
            template = DashboardTemplate.from_dict(template_data)
            self.templates[template.id] = template
            
            logger.debug(f"Loaded default template: {template.id}")
    
    async def _build_category_index(self) -> None:
        """Build category index."""
        self.categories = {}
        
        for template in self.templates.values():
            if template.category not in self.categories:
                self.categories[template.category] = []
            self.categories[template.category].append(template.id)
    
    async def _validate_template_config(self, config: Dict[str, Any]) -> None:
        """Validate template configuration."""
        # Basic validation - in real implementation, this would be more comprehensive
        required_fields = ["layout", "components"]
        for field in required_fields:
            if field not in config:
                raise DashboardTemplateError(f"Missing required config field: {field}")
        
        # Validate layout
        layout = config["layout"]
        if "type" not in layout:
            raise DashboardTemplateError("Layout must have a type")
        
        # Validate components
        components = config["components"]
        if not isinstance(components, list):
            raise DashboardTemplateError("Components must be a list")
        
        for component in components:
            required_component_fields = ["id", "type", "position", "data_source"]
            for field in required_component_fields:
                if field not in component:
                    raise DashboardTemplateError(f"Component missing required field: {field}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get template manager status."""
        return {
            "initialized": self.is_initialized,
            "total_templates": len(self.templates),
            "default_templates": len([t for t in self.templates.values() if t.is_default]),
            "categories": len(self.categories),
            "category_breakdown": {cat: len(templates) for cat, templates in self.categories.items()}
        }
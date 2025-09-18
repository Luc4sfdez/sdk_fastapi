"""
Dashboard Exceptions - Custom exceptions for dashboard system

This module defines custom exceptions used throughout the dashboard
and visualization system.
"""

from typing import Optional, Dict, Any


class DashboardError(Exception):
    """Base exception for dashboard-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "DASHBOARD_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class DashboardNotFoundError(DashboardError):
    """Exception raised when dashboard is not found."""
    
    def __init__(self, message: str, dashboard_id: Optional[str] = None):
        super().__init__(message, "DASHBOARD_NOT_FOUND")
        if dashboard_id:
            self.details["dashboard_id"] = dashboard_id


class DashboardPermissionError(DashboardError):
    """Exception raised when user lacks permission for dashboard operation."""
    
    def __init__(
        self,
        message: str,
        user: Optional[str] = None,
        dashboard_id: Optional[str] = None,
        required_permission: Optional[str] = None
    ):
        super().__init__(message, "DASHBOARD_PERMISSION_DENIED")
        if user:
            self.details["user"] = user
        if dashboard_id:
            self.details["dashboard_id"] = dashboard_id
        if required_permission:
            self.details["required_permission"] = required_permission


class DashboardConfigError(DashboardError):
    """Exception raised when dashboard configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        config_value: Optional[Any] = None
    ):
        super().__init__(message, "DASHBOARD_CONFIG_ERROR")
        if config_field:
            self.details["config_field"] = config_field
        if config_value is not None:
            self.details["config_value"] = str(config_value)


class VisualizationError(DashboardError):
    """Exception raised when visualization rendering fails."""
    
    def __init__(
        self,
        message: str,
        visualization_type: Optional[str] = None,
        component_id: Optional[str] = None
    ):
        super().__init__(message, "VISUALIZATION_ERROR")
        if visualization_type:
            self.details["visualization_type"] = visualization_type
        if component_id:
            self.details["component_id"] = component_id


class DashboardStreamingError(DashboardError):
    """Exception raised when dashboard streaming fails."""
    
    def __init__(
        self,
        message: str,
        stream_id: Optional[str] = None,
        dashboard_id: Optional[str] = None
    ):
        super().__init__(message, "DASHBOARD_STREAMING_ERROR")
        if stream_id:
            self.details["stream_id"] = stream_id
        if dashboard_id:
            self.details["dashboard_id"] = dashboard_id


class DashboardExportError(DashboardError):
    """Exception raised when dashboard export fails."""
    
    def __init__(
        self,
        message: str,
        export_format: Optional[str] = None,
        dashboard_id: Optional[str] = None
    ):
        super().__init__(message, "DASHBOARD_EXPORT_ERROR")
        if export_format:
            self.details["export_format"] = export_format
        if dashboard_id:
            self.details["dashboard_id"] = dashboard_id


class DashboardTemplateError(DashboardError):
    """Exception raised when dashboard template operation fails."""
    
    def __init__(
        self,
        message: str,
        template_id: Optional[str] = None,
        template_name: Optional[str] = None
    ):
        super().__init__(message, "DASHBOARD_TEMPLATE_ERROR")
        if template_id:
            self.details["template_id"] = template_id
        if template_name:
            self.details["template_name"] = template_name


class DashboardDataSourceError(DashboardError):
    """Exception raised when data source operation fails."""
    
    def __init__(
        self,
        message: str,
        data_source: Optional[str] = None,
        query: Optional[str] = None
    ):
        super().__init__(message, "DASHBOARD_DATA_SOURCE_ERROR")
        if data_source:
            self.details["data_source"] = data_source
        if query:
            self.details["query"] = query
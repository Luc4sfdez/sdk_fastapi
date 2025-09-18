"""
Base manager class with common functionality and error handling.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass

from ...exceptions import SDKError


@dataclass
class ManagerError:
    """Error information for manager operations."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BaseManager(ABC):
    """
    Base class for all web dashboard managers.
    
    Provides common functionality including:
    - Logging
    - Error handling
    - Configuration management
    - Health checking
    - Async initialization
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base manager.
        
        Args:
            name: Manager name for logging and identification
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"web.{name}")
        self._initialized = False
        self._healthy = True
        self._last_health_check = None
        self._errors: List[ManagerError] = []
        
    async def initialize(self) -> bool:
        """
        Initialize the manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info(f"Initializing {self.name} manager")
            await self._initialize_impl()
            self._initialized = True
            self.logger.info(f"{self.name} manager initialized successfully")
            return True
        except Exception as e:
            error = ManagerError(
                error_code="INIT_FAILED",
                message=f"Failed to initialize {self.name} manager: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            self._add_error(error)
            self.logger.error(f"Failed to initialize {self.name} manager: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """
        Shutdown the manager and cleanup resources.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        try:
            self.logger.info(f"Shutting down {self.name} manager")
            await self._shutdown_impl()
            self._initialized = False
            self.logger.info(f"{self.name} manager shutdown successfully")
            return True
        except Exception as e:
            error = ManagerError(
                error_code="SHUTDOWN_FAILED",
                message=f"Failed to shutdown {self.name} manager: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            self._add_error(error)
            self.logger.error(f"Failed to shutdown {self.name} manager: {e}")
            return False
    
    async def health_check(self) -> bool:
        """
        Perform health check on the manager.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            self._last_health_check = datetime.utcnow()
            self._healthy = await self._health_check_impl()
            return self._healthy
        except Exception as e:
            error = ManagerError(
                error_code="HEALTH_CHECK_FAILED",
                message=f"Health check failed for {self.name} manager: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            self._add_error(error)
            self.logger.error(f"Health check failed for {self.name} manager: {e}")
            self._healthy = False
            return False
    
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized
    
    def is_healthy(self) -> bool:
        """Check if manager is healthy."""
        return self._healthy
    
    def get_last_health_check(self) -> Optional[datetime]:
        """Get timestamp of last health check."""
        return self._last_health_check
    
    def get_errors(self, limit: Optional[int] = None) -> List[ManagerError]:
        """
        Get recent errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent errors
        """
        errors = sorted(self._errors, key=lambda x: x.timestamp, reverse=True)
        if limit:
            return errors[:limit]
        return errors
    
    def clear_errors(self) -> None:
        """Clear all stored errors."""
        self._errors.clear()
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update manager configuration.
        
        Args:
            config: New configuration values
        """
        self.config.update(config)
        self.logger.info(f"Updated configuration for {self.name} manager")
    
    def _add_error(self, error: ManagerError) -> None:
        """
        Add error to error list.
        
        Args:
            error: Error to add
        """
        self._errors.append(error)
        # Keep only last 100 errors to prevent memory issues
        if len(self._errors) > 100:
            self._errors = self._errors[-100:]
    
    async def _safe_execute(self, operation_name: str, func, *args, **kwargs) -> Any:
        """
        Safely execute an operation with error handling.
        
        Args:
            operation_name: Name of the operation for logging
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurred
        """
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            error = ManagerError(
                error_code="OPERATION_FAILED",
                message=f"{operation_name} failed in {self.name} manager: {str(e)}",
                details={
                    "operation": operation_name,
                    "exception_type": type(e).__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
            )
            self._add_error(error)
            self.logger.error(f"{operation_name} failed in {self.name} manager: {e}")
            return None
    
    @abstractmethod
    async def _initialize_impl(self) -> None:
        """
        Implementation-specific initialization logic.
        
        Subclasses must implement this method.
        """
        pass
    
    async def _shutdown_impl(self) -> None:
        """
        Implementation-specific shutdown logic.
        
        Subclasses can override this method if needed.
        """
        pass
    
    async def _health_check_impl(self) -> bool:
        """
        Implementation-specific health check logic.
        
        Subclasses can override this method.
        Default implementation returns True if initialized.
        """
        return self._initialized
"""
Core components for the advanced web dashboard.
"""

from .base_manager import BaseManager
from .dependency_container import DependencyContainer
from .config import WebConfig

__all__ = [
    "BaseManager",
    "DependencyContainer", 
    "WebConfig"
]
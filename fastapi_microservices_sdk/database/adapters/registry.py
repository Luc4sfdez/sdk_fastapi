"""
Database Adapter Registry for FastAPI Microservices SDK.

This module provides a registry system for managing database adapters,
allowing for dynamic registration and retrieval of adapters based on
database engine types.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
from typing import Dict, Type, Optional, List, Any
from ..config import DatabaseEngine, DatabaseConnectionConfig
from ..exceptions import ConfigurationError
from .base import DatabaseAdapter


class AdapterRegistry:
    """Registry for database adapters."""
    
    _adapters: Dict[DatabaseEngine, Type[DatabaseAdapter]] = {}
    _instances: Dict[str, DatabaseAdapter] = {}
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def register_adapter(
        self, 
        engine: DatabaseEngine, 
        adapter_class: Type[DatabaseAdapter]
    ) -> None:
        """Register a database adapter for a specific engine."""
        if not issubclass(adapter_class, DatabaseAdapter):
            raise ConfigurationError(
                f"Adapter class must inherit from DatabaseAdapter",
                context={
                    'engine': engine.value,
                    'adapter_class': adapter_class.__name__,
                    'operation': 'register_adapter'
                }
            )
        
        self._adapters[engine] = adapter_class
        self._logger.info(f"Registered adapter {adapter_class.__name__} for engine {engine.value}")
    
    @classmethod
    def get_adapter_class(self, engine: DatabaseEngine) -> Type[DatabaseAdapter]:
        """Get the adapter class for a specific engine."""
        if engine not in self._adapters:
            raise ConfigurationError(
                f"No adapter registered for engine {engine.value}",
                context={
                    'engine': engine.value,
                    'available_engines': [e.value for e in self._adapters.keys()],
                    'operation': 'get_adapter_class'
                }
            )
        
        return self._adapters[engine]
    
    @classmethod
    def create_adapter(
        self, 
        config: DatabaseConnectionConfig,
        instance_id: Optional[str] = None
    ) -> DatabaseAdapter:
        """Create a new adapter instance."""
        adapter_class = self.get_adapter_class(config.engine)
        adapter = adapter_class(config)
        
        if instance_id:
            self._instances[instance_id] = adapter
        
        return adapter
    
    @classmethod
    def get_adapter_instance(self, instance_id: str) -> Optional[DatabaseAdapter]:
        """Get an existing adapter instance."""
        return self._instances.get(instance_id)
    
    @classmethod
    def remove_adapter_instance(self, instance_id: str) -> bool:
        """Remove an adapter instance from the registry."""
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False
    
    @classmethod
    def list_registered_engines(self) -> List[DatabaseEngine]:
        """List all registered database engines."""
        return list(self._adapters.keys())
    
    @classmethod
    def list_adapter_instances(self) -> List[str]:
        """List all adapter instance IDs."""
        return list(self._instances.keys())
    
    @classmethod
    def is_engine_supported(self, engine: DatabaseEngine) -> bool:
        """Check if an engine is supported."""
        return engine in self._adapters
    
    @classmethod
    def get_registry_status(self) -> Dict[str, Any]:
        """Get the current status of the adapter registry."""
        return {
            'registered_engines': [engine.value for engine in self._adapters.keys()],
            'adapter_classes': {
                engine.value: adapter_class.__name__ 
                for engine, adapter_class in self._adapters.items()
            },
            'active_instances': len(self._instances),
            'instance_ids': list(self._instances.keys())
        }
    
    @classmethod
    async def shutdown_all_instances(self) -> None:
        """Shutdown all adapter instances."""
        for instance_id, adapter in list(self._instances.items()):
            try:
                await adapter.shutdown()
                self._logger.info(f"Shutdown adapter instance {instance_id}")
            except Exception as e:
                self._logger.error(f"Error shutting down adapter {instance_id}: {e}")
            finally:
                del self._instances[instance_id]


# Auto-register adapters when available
def _auto_register_adapters():
    """Automatically register available database adapters."""
    
    # PostgreSQL Adapter
    try:
        from .postgresql import PostgreSQLAdapter
        AdapterRegistry.register_adapter(DatabaseEngine.POSTGRESQL, PostgreSQLAdapter)
    except ImportError:
        pass
    
    # MySQL Adapter
    try:
        from .mysql import MySQLAdapter
        AdapterRegistry.register_adapter(DatabaseEngine.MYSQL, MySQLAdapter)
    except ImportError:
        pass
    
    # MongoDB Adapter
    try:
        from .mongodb import MongoDBAdapter
        AdapterRegistry.register_adapter(DatabaseEngine.MONGODB, MongoDBAdapter)
    except ImportError:
        pass
    
    # SQLite Adapter
    try:
        from .sqlite import SQLiteAdapter
        AdapterRegistry.register_adapter(DatabaseEngine.SQLITE, SQLiteAdapter)
    except ImportError:
        pass


# Auto-register adapters on module import
_auto_register_adapters()
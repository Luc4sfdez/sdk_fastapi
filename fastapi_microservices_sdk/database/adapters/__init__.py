"""
Database Adapters for FastAPI Microservices SDK.

This module provides database adapter implementations for different database engines.
Each adapter provides a consistent interface while optimizing for the specific
database engine's capabilities and best practices.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

from .base import DatabaseAdapter, DatabaseConnection, QueryResult, TransactionContext
from .registry import AdapterRegistry

# Import specific adapters (will be available when dependencies are installed)
try:
    from .postgresql import PostgreSQLAdapter
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    PostgreSQLAdapter = None

try:
    from .mysql import MySQLAdapter
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLAdapter = None

try:
    from .mongodb import MongoDBAdapter
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoDBAdapter = None

try:
    from .sqlite import SQLiteAdapter
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SQLiteAdapter = None

__all__ = [
    'DatabaseAdapter',
    'DatabaseConnection', 
    'QueryResult',
    'TransactionContext',
    'AdapterRegistry',
    'PostgreSQLAdapter',
    'MySQLAdapter',
    'MongoDBAdapter',
    'SQLiteAdapter',
    'POSTGRESQL_AVAILABLE',
    'MYSQL_AVAILABLE',
    'MONGODB_AVAILABLE',
    'SQLITE_AVAILABLE'
]
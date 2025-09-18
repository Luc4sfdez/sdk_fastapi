"""
Database management for service storage.
"""

import logging
from typing import Optional, Generator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from .models import Base
from ...exceptions import SDKError


class ServiceDatabaseManager:
    """Database manager for service storage."""
    
    def __init__(self, database_url: str = None, echo: bool = False):
        """
        Initialize the database manager.
        
        Args:
            database_url: Database connection URL (default: SQLite in-memory)
            echo: Whether to echo SQL statements
        """
        self.logger = logging.getLogger("web.services.database")
        
        # Default to SQLite for development
        if not database_url:
            database_url = "sqlite:///./services.db"
        
        self.database_url = database_url
        self.echo = echo
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the database connection and create tables.
        
        Returns:
            True if initialization successful
        """
        try:
            # Create engine
            if self.database_url.startswith("sqlite"):
                # SQLite specific configuration
                self.engine = create_engine(
                    self.database_url,
                    echo=self.echo,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool
                )
            else:
                # PostgreSQL, MySQL, etc.
                self.engine = create_engine(
                    self.database_url,
                    echo=self.echo
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            self.logger.info(f"Database initialized successfully: {self.database_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    def get_session(self) -> Session:
        """
        Get a database session.
        
        Returns:
            SQLAlchemy session
            
        Raises:
            SDKError: If database not initialized
        """
        if not self._initialized or not self.SessionLocal:
            raise SDKError("Database not initialized. Call initialize() first.")
        
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Yields:
            Database session
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_tables(self) -> bool:
        """
        Create all database tables.
        
        Returns:
            True if tables created successfully
        """
        try:
            if not self.engine:
                raise SDKError("Database engine not initialized")
            
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            return False
    
    def drop_tables(self) -> bool:
        """
        Drop all database tables.
        
        Returns:
            True if tables dropped successfully
        """
        try:
            if not self.engine:
                raise SDKError("Database engine not initialized")
            
            Base.metadata.drop_all(bind=self.engine)
            self.logger.info("Database tables dropped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to drop database tables: {e}")
            return False
    
    def reset_database(self) -> bool:
        """
        Reset the database by dropping and recreating all tables.
        
        Returns:
            True if reset successful
        """
        try:
            self.drop_tables()
            self.create_tables()
            self.logger.info("Database reset successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            return False
    
    def check_connection(self) -> bool:
        """
        Check if database connection is working.
        
        Returns:
            True if connection is working
        """
        try:
            if not self.engine:
                return False
            
            with self.engine.connect() as connection:
                from sqlalchemy import text
                connection.execute(text("SELECT 1"))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database connection check failed: {e}")
            return False
    
    def get_database_info(self) -> dict:
        """
        Get database information.
        
        Returns:
            Dictionary with database information
        """
        info = {
            "database_url": self.database_url,
            "initialized": self._initialized,
            "connection_working": False,
            "tables": []
        }
        
        if self._initialized and self.engine:
            info["connection_working"] = self.check_connection()
            
            try:
                # Get table names
                metadata = MetaData()
                metadata.reflect(bind=self.engine)
                info["tables"] = list(metadata.tables.keys())
            except Exception as e:
                self.logger.error(f"Failed to get table information: {e}")
        
        return info
    
    def close(self) -> None:
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
            self.logger.info("Database connections closed")


# Global database manager instance
_db_manager: Optional[ServiceDatabaseManager] = None


def get_database_manager(database_url: str = None, echo: bool = False) -> ServiceDatabaseManager:
    """
    Get or create the global database manager instance.
    
    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements
        
    Returns:
        ServiceDatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = ServiceDatabaseManager(database_url, echo)
        _db_manager.initialize()
    
    return _db_manager


def get_db_session() -> Session:
    """
    Get a database session (dependency injection helper).
    
    Returns:
        Database session
    """
    db_manager = get_database_manager()
    return db_manager.get_session()


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    
    Yields:
        Database session
    """
    db_manager = get_database_manager()
    with db_manager.session_scope() as session:
        yield session


# Alias for backward compatibility
Database = ServiceDatabaseManager
"""
Unit tests for ServiceDatabaseManager.
"""

import pytest
import tempfile
import os
from pathlib import Path

from fastapi_microservices_sdk.web.services.database import ServiceDatabaseManager
from fastapi_microservices_sdk.web.services.models import Base, ServiceModel
from fastapi_microservices_sdk.exceptions import SDKError


class TestServiceDatabaseManager:
    """Test cases for ServiceDatabaseManager."""
    
    def test_initialization_sqlite_memory(self):
        """Test initialization with SQLite in-memory database."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        
        success = db_manager.initialize()
        assert success
        assert db_manager._initialized
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None
    
    def test_initialization_sqlite_file(self):
        """Test initialization with SQLite file database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            db_url = f"sqlite:///{db_path}"
            
            db_manager = ServiceDatabaseManager(db_url)
            
            success = db_manager.initialize()
            assert success
            assert db_manager._initialized
            assert db_path.exists()
    
    def test_initialization_default_sqlite(self):
        """Test initialization with default SQLite database."""
        db_manager = ServiceDatabaseManager()
        
        success = db_manager.initialize()
        assert success
        assert db_manager._initialized
        assert "sqlite" in db_manager.database_url
    
    def test_get_session_before_initialization(self):
        """Test getting session before initialization."""
        db_manager = ServiceDatabaseManager()
        
        with pytest.raises(SDKError, match="Database not initialized"):
            db_manager.get_session()
    
    def test_get_session_after_initialization(self):
        """Test getting session after initialization."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        session = db_manager.get_session()
        assert session is not None
        
        # Test that we can use the session
        from sqlalchemy import text
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
        
        session.close()
    
    def test_session_scope(self):
        """Test session scope context manager."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Test successful transaction
        with db_manager.session_scope() as session:
            service = ServiceModel(
                id="test-service",
                name="Test Service",
                template_type="base",
                status="stopped",
                port=8000
            )
            session.add(service)
            # Transaction should be committed automatically
        
        # Verify the service was saved
        with db_manager.session_scope() as session:
            saved_service = session.query(ServiceModel).filter(ServiceModel.id == "test-service").first()
            assert saved_service is not None
            assert saved_service.name == "Test Service"
    
    def test_session_scope_rollback(self):
        """Test session scope rollback on exception."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Test transaction rollback
        with pytest.raises(Exception, match="Test exception"):
            with db_manager.session_scope() as session:
                service = ServiceModel(
                    id="test-service",
                    name="Test Service",
                    template_type="base",
                    status="stopped",
                    port=8000
                )
                session.add(service)
                # Force an exception to trigger rollback
                raise Exception("Test exception")
        
        # Verify the service was not saved due to rollback
        with db_manager.session_scope() as session:
            saved_service = session.query(ServiceModel).filter(ServiceModel.id == "test-service").first()
            assert saved_service is None
    
    def test_create_tables(self):
        """Test creating database tables."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        success = db_manager.create_tables()
        assert success
        
        # Verify tables exist by querying them
        with db_manager.session_scope() as session:
            # This should not raise an exception
            session.query(ServiceModel).count()
    
    def test_drop_tables(self):
        """Test dropping database tables."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Create a service to verify table exists
        with db_manager.session_scope() as session:
            service = ServiceModel(
                id="test-service",
                name="Test Service",
                template_type="base",
                status="stopped",
                port=8000
            )
            session.add(service)
        
        # Drop tables
        success = db_manager.drop_tables()
        assert success
        
        # Recreate tables to test they were dropped
        db_manager.create_tables()
        
        # Verify the service is gone (tables were dropped and recreated)
        with db_manager.session_scope() as session:
            count = session.query(ServiceModel).count()
            assert count == 0
    
    def test_reset_database(self):
        """Test resetting database."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Create a service
        with db_manager.session_scope() as session:
            service = ServiceModel(
                id="test-service",
                name="Test Service",
                template_type="base",
                status="stopped",
                port=8000
            )
            session.add(service)
        
        # Verify service exists
        with db_manager.session_scope() as session:
            count = session.query(ServiceModel).count()
            assert count == 1
        
        # Reset database
        success = db_manager.reset_database()
        assert success
        
        # Verify service is gone
        with db_manager.session_scope() as session:
            count = session.query(ServiceModel).count()
            assert count == 0
    
    def test_check_connection(self):
        """Test checking database connection."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        
        # Before initialization
        assert not db_manager.check_connection()
        
        # After initialization
        db_manager.initialize()
        assert db_manager.check_connection()
    
    def test_get_database_info(self):
        """Test getting database information."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        
        # Before initialization
        info = db_manager.get_database_info()
        assert info["database_url"] == "sqlite:///:memory:"
        assert not info["initialized"]
        assert not info["connection_working"]
        assert info["tables"] == []
        
        # After initialization
        db_manager.initialize()
        info = db_manager.get_database_info()
        assert info["initialized"]
        assert info["connection_working"]
        assert len(info["tables"]) > 0
        assert "services" in info["tables"]
    
    def test_close(self):
        """Test closing database connections."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Verify connection works
        assert db_manager.check_connection()
        
        # Close connections
        db_manager.close()
        
        # Connection check might still work for SQLite in-memory,
        # but the engine should be disposed
        # This is mainly for testing the method doesn't raise exceptions
    
    def test_initialization_failure(self):
        """Test initialization failure with invalid database URL."""
        # Use an invalid database URL
        db_manager = ServiceDatabaseManager("invalid://database/url")
        
        success = db_manager.initialize()
        assert not success
        assert not db_manager._initialized
    
    def test_create_tables_without_engine(self):
        """Test creating tables without initialized engine."""
        db_manager = ServiceDatabaseManager()
        
        with pytest.raises(SDKError, match="Database engine not initialized"):
            db_manager.create_tables()
    
    def test_drop_tables_without_engine(self):
        """Test dropping tables without initialized engine."""
        db_manager = ServiceDatabaseManager()
        
        with pytest.raises(SDKError, match="Database engine not initialized"):
            db_manager.drop_tables()
    
    def test_echo_parameter(self):
        """Test echo parameter for SQL logging."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:", echo=True)
        db_manager.initialize()
        
        assert db_manager.echo == True
        assert db_manager.engine.echo == True
    
    def test_multiple_sessions(self):
        """Test creating multiple sessions."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        session1 = db_manager.get_session()
        session2 = db_manager.get_session()
        
        assert session1 is not session2
        
        # Both sessions should work
        from sqlalchemy import text
        result1 = session1.execute(text("SELECT 1")).scalar()
        result2 = session2.execute(text("SELECT 1")).scalar()
        
        assert result1 == 1
        assert result2 == 1
        
        session1.close()
        session2.close()
    
    def test_concurrent_transactions(self):
        """Test concurrent transactions."""
        db_manager = ServiceDatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        # Create services in separate transactions
        with db_manager.session_scope() as session1:
            service1 = ServiceModel(
                id="service-1",
                name="Service 1",
                template_type="base",
                status="stopped",
                port=8000
            )
            session1.add(service1)
        
        with db_manager.session_scope() as session2:
            service2 = ServiceModel(
                id="service-2",
                name="Service 2",
                template_type="base",
                status="stopped",
                port=8001
            )
            session2.add(service2)
        
        # Verify both services exist
        with db_manager.session_scope() as session:
            count = session.query(ServiceModel).count()
            assert count == 2
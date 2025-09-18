"""
MongoDB Database Adapter for FastAPI Microservices SDK.

This module provides MongoDB-specific database adapter implementation
with optimizations for document operations and MongoDB-specific features.

Features:
- Full motor integration with connection pooling
- MongoDB replica set support and read preferences
- SSL/TLS support with certificate validation
- Advanced MongoDB features (aggregation, indexing, GridFS)
- Connection health monitoring and recovery
- Document operations optimization and performance metrics
- Transaction management with sessions
- Change streams support for real-time updates
- Connection retry logic with exponential backoff
- MongoDB-specific data types and operations

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import ssl
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import json
import re

# Optional BSON dependency
try:
    from bson import ObjectId
    from bson.errors import InvalidId
    BSON_AVAILABLE = True
except ImportError:
    BSON_AVAILABLE = False
    ObjectId = None
    InvalidId = None

from ..config import DatabaseConnectionConfig, DatabaseEngine
from ..exceptions import (
    DatabaseError, ConnectionError, QueryError, TransactionError,
    MongoDBError, wrap_database_error
)
from .base import (
    DatabaseAdapter, DatabaseConnection, QueryResult, QueryType,
    TransactionContext, IsolationLevel, QueryMetrics
)

# Optional dependency
try:
    import motor.motor_asyncio
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
    from pymongo import MongoClient, ReadPreference, WriteConcern, ReadConcern
    from pymongo.errors import (
        ConnectionFailure, ServerSelectionTimeoutError, OperationFailure,
        DuplicateKeyError, BulkWriteError, InvalidOperation
    )
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    motor = None
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None
    AsyncIOMotorCollection = None
    MongoClient = None
    ReadPreference = None
    WriteConcern = None
    ReadConcern = None


class MongoDBAdapter(DatabaseAdapter):
    """MongoDB database adapter with motor and enterprise features."""
    
    def __init__(self, config: DatabaseConnectionConfig):
        if not MOTOR_AVAILABLE:
            raise DatabaseError(
                "motor not installed - required for MongoDB support",
                context={
                    'engine': DatabaseEngine.MONGODB.value,
                    'operation': 'configuration',
                    'database_name': self._get_database_name(config)
                }
            )
        
        # Initialize base class without calling super() to avoid engine conflict
        self.config = config
        self._engine = config.engine
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._connection_pool_dict: Dict[str, DatabaseConnection] = {}
        self._pool_lock = asyncio.Lock()
        self._is_initialized = False
        
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._connection_options = self._build_connection_options()
        self._ssl_context = self._create_ssl_context()
        self._replica_set_config = self._parse_replica_set_config()
        self._change_streams: Dict[str, Any] = {}
        
    def _get_database_name(self, config: DatabaseConnectionConfig) -> str:
        """Get database name for error reporting."""
        return getattr(config, 'name', config.database)
    
    def _build_connection_options(self) -> Dict[str, Any]:
        """Build MongoDB connection options."""
        options = {
            'host': self.config.host,
            'port': self.config.port,
            'username': self.config.credentials.username if self.config.credentials else None,
            'password': self.config.credentials.password if self.config.credentials else None,
            'authSource': self.config.database,
            'connectTimeoutMS': int(self.config.pool.connection_timeout * 1000),
            'serverSelectionTimeoutMS': 30000,
            'maxPoolSize': self.config.pool.max_connections,
            'minPoolSize': self.config.pool.min_connections,
            'maxIdleTimeMS': 300000,  # 5 minutes
            'heartbeatFrequencyMS': 10000,  # 10 seconds
            'retryWrites': True,
            'retryReads': True,
            'w': 'majority',  # Write concern
            'readPreference': 'primary'
        }
        
        # SSL configuration
        if self._ssl_context:
            options['ssl'] = True
            options['ssl_context'] = self._ssl_context
        
        # Replica set configuration
        if self._replica_set_config.get('replica_set_name'):
            options['replicaSet'] = self._replica_set_config['replica_set_name']
            options['readPreference'] = self._replica_set_config.get('read_preference', 'primary')
        
        return options
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for secure connections."""
        if not hasattr(self.config, 'ssl') or not self.config.ssl or not self.config.ssl.enabled:
            return None
        
        ssl_config = self.config.ssl
        context = ssl.create_default_context()
        
        # Configure SSL verification
        if ssl_config.verify_mode:
            context.check_hostname = ssl_config.check_hostname
            context.verify_mode = getattr(ssl, ssl_config.verify_mode)
        
        # Load certificates
        if ssl_config.ca_cert_path:
            context.load_verify_locations(ssl_config.ca_cert_path)
        
        if ssl_config.client_cert_path and ssl_config.client_key_path:
            context.load_cert_chain(ssl_config.client_cert_path, ssl_config.client_key_path)
        
        return context
    
    def _parse_replica_set_config(self) -> Dict[str, Any]:
        """Parse replica set configuration from connection config."""
        replica_config = {
            'replica_set_name': None,
            'read_preference': 'primary',
            'write_concern': 'majority',
            'read_concern': 'majority'
        }
        
        # Check if replica set is configured
        if hasattr(self.config, 'replica_set') and self.config.replica_set:
            replica_config.update(self.config.replica_set)
        
        return replica_config
    
    async def initialize(self) -> None:
        """Initialize the MongoDB adapter."""
        try:
            # Create MongoDB client
            self._client = AsyncIOMotorClient(**self._connection_options)
            
            # Get database reference
            self._database = self._client[self.config.database]
            
            # Test connection and get MongoDB version
            server_info = await self._client.server_info()
            mongodb_version = server_info.get('version', 'unknown')
            
            # Test database access
            await self._database.list_collection_names()
            
            self.logger.info(f"Connected to MongoDB: {mongodb_version}")
            
            self._is_initialized = True
            self.logger.info(f"MongoDB adapter initialized for database: {self.config.database}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="initialize",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def shutdown(self) -> None:
        """Shutdown the MongoDB adapter."""
        try:
            # Close change streams
            for stream_name, stream in self._change_streams.items():
                try:
                    await stream.close()
                except Exception as e:
                    self.logger.warning(f"Error closing change stream {stream_name}: {e}")
            
            self._change_streams.clear()
            
            # Close individual connections
            async with self._pool_lock:
                for connection in list(self._connection_pool_dict.values()):
                    await connection.close()
                self._connection_pool_dict.clear()
            
            # Close MongoDB client
            if self._client:
                self._client.close()
                self._client = None
                self._database = None
            
            self._is_initialized = False
            self.logger.info("MongoDB adapter shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during MongoDB adapter shutdown: {e}")
            raise wrap_database_error(
                e,
                operation="shutdown",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def create_connection(self) -> DatabaseConnection:
        """Create a new MongoDB connection."""
        try:
            connection_id = self._create_connection_id()
            
            # For MongoDB, we use the shared client but create a session
            if not self._client or not self._database:
                raise DatabaseError("MongoDB adapter not initialized")
            
            # Create a client session for transactions
            session = await self._client.start_session()
            
            connection = DatabaseConnection(
                connection_id=connection_id,
                config=self.config,
                native_connection=session,
                adapter=self
            )
            
            # Set connection metadata
            server_info = await self._client.server_info()
            connection.set_metadata("mongodb_version", server_info.get('version', 'unknown'))
            connection.set_metadata("server_status", await self._get_server_status())
            connection.set_metadata("replica_set_status", await self._get_replica_set_status())
            
            # Store database and client references in connection
            connection.set_metadata("database", self._database)
            connection.set_metadata("client", self._client)
            
            self.logger.debug(f"Created MongoDB connection: {connection_id}")
            return connection
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_connection",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _get_server_status(self) -> Dict[str, Any]:
        """Get MongoDB server status."""
        try:
            status = await self._database.command("serverStatus")
            return {
                'uptime': status.get('uptime', 0),
                'connections': status.get('connections', {}),
                'network': status.get('network', {}),
                'opcounters': status.get('opcounters', {})
            }
        except Exception:
            return {}
    
    async def _get_replica_set_status(self) -> Dict[str, Any]:
        """Get replica set status."""
        try:
            if self._replica_set_config.get('replica_set_name'):
                status = await self._database.command("replSetGetStatus")
                return {
                    'set': status.get('set'),
                    'members': len(status.get('members', [])),
                    'primary': next((m['name'] for m in status.get('members', []) if m.get('stateStr') == 'PRIMARY'), None)
                }
            return {'replica_set': False}
        except Exception:
            return {'replica_set': False}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform MongoDB health check."""
        try:
            start_time = datetime.now(timezone.utc)
            
            if not self._client or not self._database:
                return {
                    'healthy': False,
                    'error': 'MongoDB client not initialized',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Basic connectivity test
            await self._client.admin.command('ping')
            
            # Get server information
            server_info = await self._client.server_info()
            
            # Get database statistics
            db_stats = await self._database.command("dbStats")
            
            # Get server status
            server_status = await self._database.command("serverStatus")
            
            # Get replica set status if applicable
            replica_status = None
            try:
                if self._replica_set_config.get('replica_set_name'):
                    replica_status = await self._database.command("replSetGetStatus")
            except Exception:
                replica_status = None
            
            # Get collection count
            collections = await self._database.list_collection_names()
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'healthy': True,
                'response_time': response_time,
                'database_name': self.config.database,
                'mongodb_version': server_info.get('version'),
                'server_uptime': server_status.get('uptime', 0),
                'database_size_bytes': db_stats.get('dataSize', 0),
                'storage_size_bytes': db_stats.get('storageSize', 0),
                'index_size_bytes': db_stats.get('indexSize', 0),
                'collection_count': len(collections),
                'document_count': db_stats.get('objects', 0),
                'connections': {
                    'current': server_status.get('connections', {}).get('current', 0),
                    'available': server_status.get('connections', {}).get('available', 0),
                    'total_created': server_status.get('connections', {}).get('totalCreated', 0)
                },
                'operations': {
                    'insert': server_status.get('opcounters', {}).get('insert', 0),
                    'query': server_status.get('opcounters', {}).get('query', 0),
                    'update': server_status.get('opcounters', {}).get('update', 0),
                    'delete': server_status.get('opcounters', {}).get('delete', 0)
                },
                'replica_set': {
                    'enabled': replica_status is not None,
                    'name': replica_status.get('set') if replica_status else None,
                    'members': len(replica_status.get('members', [])) if replica_status else 0,
                    'primary': next((m['name'] for m in replica_status.get('members', []) if m.get('stateStr') == 'PRIMARY'), None) if replica_status else None
                } if replica_status else {'enabled': False},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    async def execute_query(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a MongoDB operation (translated from query-like syntax)."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self._log_query(query, parameters)
            connection.mark_used()
            
            # Parse MongoDB operation from query-like syntax
            operation = self._parse_mongodb_operation(query, parameters)
            
            # Get database and session from connection
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            # Execute operation based on type
            result = await self._execute_mongodb_operation(
                database, session, operation, query_type
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += 1
            
            # Create metrics
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=result.get('modified_count', 0) + result.get('deleted_count', 0),
                rows_returned=result.get('document_count', 0)
            )
            
            return QueryResult(
                data=result.get('documents'),
                rows_affected=result.get('modified_count', 0) + result.get('deleted_count', 0),
                rows_returned=result.get('document_count', 0),
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="execute_query",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    def _parse_mongodb_operation(self, query: str, parameters: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse query-like syntax into MongoDB operation."""
        # This is a simplified parser for demonstration
        # In practice, you might want to use a more sophisticated query parser
        
        query_lower = query.strip().lower()
        
        if query_lower.startswith('find'):
            # Parse: find collection_name filter projection
            parts = query.split()
            collection_name = parts[1] if len(parts) > 1 else 'default'
            return {
                'operation': 'find',
                'collection': collection_name,
                'filter': parameters.get('filter', {}) if parameters else {},
                'projection': parameters.get('projection') if parameters else None,
                'sort': parameters.get('sort') if parameters else None,
                'limit': parameters.get('limit') if parameters else None,
                'skip': parameters.get('skip') if parameters else None
            }
        
        elif query_lower.startswith('insert'):
            # Parse: insert collection_name document(s)
            parts = query.split()
            collection_name = parts[1] if len(parts) > 1 else 'default'
            return {
                'operation': 'insert',
                'collection': collection_name,
                'documents': parameters.get('documents', []) if parameters else []
            }
        
        elif query_lower.startswith('update'):
            # Parse: update collection_name filter update
            parts = query.split()
            collection_name = parts[1] if len(parts) > 1 else 'default'
            return {
                'operation': 'update',
                'collection': collection_name,
                'filter': parameters.get('filter', {}) if parameters else {},
                'update': parameters.get('update', {}) if parameters else {},
                'upsert': parameters.get('upsert', False) if parameters else False,
                'multi': parameters.get('multi', False) if parameters else False
            }
        
        elif query_lower.startswith('delete'):
            # Parse: delete collection_name filter
            parts = query.split()
            collection_name = parts[1] if len(parts) > 1 else 'default'
            return {
                'operation': 'delete',
                'collection': collection_name,
                'filter': parameters.get('filter', {}) if parameters else {}
            }
        
        elif query_lower.startswith('aggregate'):
            # Parse: aggregate collection_name pipeline
            parts = query.split()
            collection_name = parts[1] if len(parts) > 1 else 'default'
            return {
                'operation': 'aggregate',
                'collection': collection_name,
                'pipeline': parameters.get('pipeline', []) if parameters else []
            }
        
        else:
            # Default to find operation
            return {
                'operation': 'find',
                'collection': 'default',
                'filter': parameters or {}
            }
    
    async def _execute_mongodb_operation(
        self,
        database: AsyncIOMotorDatabase,
        session: Any,
        operation: Dict[str, Any],
        query_type: Optional[QueryType] = None
    ) -> Dict[str, Any]:
        """Execute MongoDB operation."""
        collection = database[operation['collection']]
        
        if operation['operation'] == 'find':
            # Find documents
            cursor = collection.find(
                operation['filter'],
                projection=operation.get('projection'),
                session=session
            )
            
            if operation.get('sort'):
                cursor = cursor.sort(operation['sort'])
            if operation.get('skip'):
                cursor = cursor.skip(operation['skip'])
            if operation.get('limit'):
                cursor = cursor.limit(operation['limit'])
            
            documents = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc and BSON_AVAILABLE and ObjectId and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
            
            return {
                'documents': documents,
                'document_count': len(documents)
            }
        
        elif operation['operation'] == 'insert':
            # Insert documents
            documents = operation['documents']
            if not documents:
                return {'inserted_count': 0}
            
            if len(documents) == 1:
                result = await collection.insert_one(documents[0], session=session)
                return {'inserted_count': 1, 'inserted_id': str(result.inserted_id)}
            else:
                result = await collection.insert_many(documents, session=session)
                return {
                    'inserted_count': len(result.inserted_ids),
                    'inserted_ids': [str(id) for id in result.inserted_ids]
                }
        
        elif operation['operation'] == 'update':
            # Update documents
            if operation.get('multi'):
                result = await collection.update_many(
                    operation['filter'],
                    operation['update'],
                    upsert=operation.get('upsert', False),
                    session=session
                )
            else:
                result = await collection.update_one(
                    operation['filter'],
                    operation['update'],
                    upsert=operation.get('upsert', False),
                    session=session
                )
            
            return {
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': str(result.upserted_id) if result.upserted_id else None
            }
        
        elif operation['operation'] == 'delete':
            # Delete documents
            result = await collection.delete_many(operation['filter'], session=session)
            return {'deleted_count': result.deleted_count}
        
        elif operation['operation'] == 'aggregate':
            # Aggregation pipeline
            cursor = collection.aggregate(operation['pipeline'], session=session)
            documents = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for doc in documents:
                if '_id' in doc and BSON_AVAILABLE and ObjectId and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
            
            return {
                'documents': documents,
                'document_count': len(documents)
            }
        
        else:
            raise ValueError(f"Unsupported MongoDB operation: {operation['operation']}")
    
    async def execute_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters_list: List[Dict[str, Any]],
        query_type: Optional[QueryType] = None
    ) -> QueryResult:
        """Execute a MongoDB operation multiple times with different parameters."""
        start_time = datetime.now(timezone.utc)
        
        try:
            self._log_query(query, f"Batch of {len(parameters_list)} parameter sets")
            connection.mark_used()
            
            total_affected = 0
            total_returned = 0
            all_results = []
            
            # Get database and session from connection
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            for parameters in parameters_list:
                operation = self._parse_mongodb_operation(query, parameters)
                result = await self._execute_mongodb_operation(database, session, operation, query_type)
                
                total_affected += result.get('modified_count', 0) + result.get('deleted_count', 0)
                total_returned += result.get('document_count', 0)
                
                if result.get('documents'):
                    all_results.extend(result['documents'])
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            connection.query_count += len(parameters_list)
            
            # Create metrics
            metrics = QueryMetrics(
                execution_time=execution_time,
                rows_affected=total_affected,
                rows_returned=total_returned
            )
            
            return QueryResult(
                data=all_results if all_results else None,
                rows_affected=total_affected,
                rows_returned=total_returned,
                execution_time=execution_time,
                metrics=metrics
            )
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="execute_many",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_one(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single document from MongoDB."""
        try:
            connection.mark_used()
            
            # Parse operation
            operation = self._parse_mongodb_operation(query, parameters)
            operation['limit'] = 1  # Ensure we only get one document
            
            # Get database and session from connection
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            result = await self._execute_mongodb_operation(database, session, operation)
            connection.query_count += 1
            
            documents = result.get('documents', [])
            return documents[0] if documents else None
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="fetch_one",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_many(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch multiple documents from MongoDB."""
        try:
            connection.mark_used()
            
            # Parse operation
            operation = self._parse_mongodb_operation(query, parameters)
            if size is not None:
                operation['limit'] = size
            
            # Get database and session from connection
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            result = await self._execute_mongodb_operation(database, session, operation)
            connection.query_count += 1
            
            return result.get('documents', [])
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="fetch_many",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                query=query[:100] + "..." if len(query) > 100 else query
            )
    
    async def fetch_all(
        self,
        connection: DatabaseConnection,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all documents from MongoDB."""
        return await self.fetch_many(connection, query, parameters)
    
    # Transaction management
    
    async def _begin_transaction(
        self,
        connection: DatabaseConnection,
        isolation_level: Optional[IsolationLevel] = None,
        read_only: bool = False
    ) -> None:
        """Begin a MongoDB transaction."""
        try:
            session = connection.native_connection
            
            # Configure transaction options
            transaction_options = {}
            
            # Set read concern based on isolation level
            if isolation_level == IsolationLevel.READ_COMMITTED:
                transaction_options['read_concern'] = ReadConcern('majority')
            elif isolation_level == IsolationLevel.SERIALIZABLE:
                transaction_options['read_concern'] = ReadConcern('snapshot')
            else:
                transaction_options['read_concern'] = ReadConcern('majority')
            
            # Set write concern
            transaction_options['write_concern'] = WriteConcern(w='majority')
            
            # Set read preference
            if read_only:
                transaction_options['read_preference'] = ReadPreference.SECONDARY_PREFERRED
            else:
                transaction_options['read_preference'] = ReadPreference.PRIMARY
            
            # Start transaction
            session.start_transaction(**transaction_options)
            
            self.logger.debug(f"Transaction started on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="begin_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _commit_transaction(self, connection: DatabaseConnection) -> None:
        """Commit a MongoDB transaction."""
        try:
            session = connection.native_connection
            await session.commit_transaction()
            self.logger.debug(f"Transaction committed on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="commit_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _rollback_transaction(self, connection: DatabaseConnection) -> None:
        """Rollback a MongoDB transaction."""
        try:
            session = connection.native_connection
            await session.abort_transaction()
            self.logger.debug(f"Transaction rolled back on connection {connection.connection_id}")
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="rollback_transaction",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def _create_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Create a MongoDB savepoint."""
        # MongoDB doesn't support savepoints in the traditional SQL sense
        # We can simulate this by storing the current transaction state
        raise NotImplementedError(
            "MongoDB doesn't support savepoints. Use nested transactions or "
            "implement application-level checkpointing instead."
        )
    
    async def _rollback_to_savepoint(self, connection: DatabaseConnection, name: str) -> None:
        """Rollback to a MongoDB savepoint."""
        # MongoDB doesn't support savepoints in the traditional SQL sense
        raise NotImplementedError(
            "MongoDB doesn't support savepoints. Use nested transactions or "
            "implement application-level checkpointing instead."
        )
    
    async def _close_connection(self, native_connection: Any) -> None:
        """Close a MongoDB connection."""
        try:
            if native_connection:
                # End session
                await native_connection.end_session()
                
        except Exception as e:
            self.logger.error(f"Error closing MongoDB connection: {e}")
            # Don't raise here as this is cleanup code    
    
# MongoDB-specific enterprise features
    
    async def create_collection(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a MongoDB collection with options."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            # Create collection with options
            collection_options = options or {}
            await database.create_collection(collection_name, session=session, **collection_options)
            
            return {
                'collection_name': collection_name,
                'created': True,
                'options': collection_options
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_collection",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def drop_collection(
        self,
        connection: DatabaseConnection,
        collection_name: str
    ) -> Dict[str, Any]:
        """Drop a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            
            await database.drop_collection(collection_name, session=session)
            
            return {
                'collection_name': collection_name,
                'dropped': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="drop_collection",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def create_index(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        index_spec: Union[str, List[Tuple[str, int]]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an index on a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            collection = database[collection_name]
            
            # Create index
            index_options = options or {}
            index_name = await collection.create_index(
                index_spec, 
                session=session,
                **index_options
            )
            
            return {
                'collection_name': collection_name,
                'index_name': index_name,
                'index_spec': index_spec,
                'created': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_index",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def drop_index(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        index_name: str
    ) -> Dict[str, Any]:
        """Drop an index from a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            collection = database[collection_name]
            
            await collection.drop_index(index_name, session=session)
            
            return {
                'collection_name': collection_name,
                'index_name': index_name,
                'dropped': True
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="drop_index",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def get_collection_stats(
        self,
        connection: DatabaseConnection,
        collection_name: str
    ) -> Dict[str, Any]:
        """Get statistics for a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            
            # Get collection stats
            stats = await database.command("collStats", collection_name)
            
            # Get index information
            collection = database[collection_name]
            indexes = await collection.list_indexes().to_list(length=None)
            
            connection.query_count += 2
            
            return {
                'collection_name': collection_name,
                'namespace': stats.get('ns'),
                'document_count': stats.get('count', 0),
                'size_bytes': stats.get('size', 0),
                'storage_size_bytes': stats.get('storageSize', 0),
                'total_index_size_bytes': stats.get('totalIndexSize', 0),
                'average_object_size': stats.get('avgObjSize', 0),
                'index_count': len(indexes),
                'indexes': [
                    {
                        'name': idx.get('name'),
                        'key': idx.get('key'),
                        'unique': idx.get('unique', False),
                        'sparse': idx.get('sparse', False)
                    }
                    for idx in indexes
                ],
                'capped': stats.get('capped', False),
                'max_size': stats.get('maxSize') if stats.get('capped') else None
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_collection_stats",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def aggregate_pipeline(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        pipeline: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline on a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            collection = database[collection_name]
            
            # Execute aggregation pipeline
            aggregation_options = options or {}
            cursor = collection.aggregate(pipeline, session=session, **aggregation_options)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for doc in results:
                if '_id' in doc and BSON_AVAILABLE and ObjectId and isinstance(doc['_id'], ObjectId):
                    doc['_id'] = str(doc['_id'])
            
            connection.query_count += 1
            return results
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="aggregate_pipeline",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def bulk_write(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        operations: List[Dict[str, Any]],
        ordered: bool = True
    ) -> Dict[str, Any]:
        """Perform bulk write operations on a MongoDB collection."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            session = connection.native_connection
            collection = database[collection_name]
            
            # Convert operations to pymongo format
            bulk_operations = []
            for op in operations:
                if op['operation'] == 'insert':
                    from pymongo import InsertOne
                    bulk_operations.append(InsertOne(op['document']))
                elif op['operation'] == 'update':
                    from pymongo import UpdateOne, UpdateMany
                    if op.get('multi', False):
                        bulk_operations.append(UpdateMany(
                            op['filter'], 
                            op['update'], 
                            upsert=op.get('upsert', False)
                        ))
                    else:
                        bulk_operations.append(UpdateOne(
                            op['filter'], 
                            op['update'], 
                            upsert=op.get('upsert', False)
                        ))
                elif op['operation'] == 'delete':
                    from pymongo import DeleteOne, DeleteMany
                    if op.get('multi', False):
                        bulk_operations.append(DeleteMany(op['filter']))
                    else:
                        bulk_operations.append(DeleteOne(op['filter']))
            
            # Execute bulk write
            result = await collection.bulk_write(
                bulk_operations, 
                ordered=ordered, 
                session=session
            )
            
            connection.query_count += 1
            
            return {
                'acknowledged': result.acknowledged,
                'inserted_count': result.inserted_count,
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'deleted_count': result.deleted_count,
                'upserted_count': result.upserted_count,
                'upserted_ids': {str(k): str(v) for k, v in result.upserted_ids.items()}
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="bulk_write",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def create_change_stream(
        self,
        connection: DatabaseConnection,
        collection_name: Optional[str] = None,
        pipeline: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a change stream for real-time updates."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            
            # Create change stream
            stream_options = options or {}
            
            if collection_name:
                collection = database[collection_name]
                change_stream = collection.watch(pipeline or [], **stream_options)
            else:
                # Watch entire database
                change_stream = database.watch(pipeline or [], **stream_options)
            
            # Generate stream ID
            stream_id = f"stream_{len(self._change_streams)}_{datetime.now().timestamp()}"
            
            # Store change stream
            self._change_streams[stream_id] = change_stream
            
            return stream_id
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="create_change_stream",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    async def get_change_stream_next(self, stream_id: str, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get next change from a change stream."""
        try:
            if stream_id not in self._change_streams:
                raise ValueError(f"Change stream {stream_id} not found")
            
            change_stream = self._change_streams[stream_id]
            
            # Get next change with timeout
            if timeout:
                try:
                    change = await asyncio.wait_for(change_stream.next(), timeout=timeout)
                except asyncio.TimeoutError:
                    return None
            else:
                change = await change_stream.next()
            
            # Convert ObjectId to string
            if change and '_id' in change and BSON_AVAILABLE and ObjectId and isinstance(change['_id'], ObjectId):
                change['_id'] = str(change['_id'])
            if (change and 'documentKey' in change and '_id' in change['documentKey'] and 
                BSON_AVAILABLE and ObjectId and isinstance(change['documentKey']['_id'], ObjectId)):
                change['documentKey']['_id'] = str(change['documentKey']['_id'])
            
            return change
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_change_stream_next",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                stream_id=stream_id
            )
    
    async def close_change_stream(self, stream_id: str) -> None:
        """Close a change stream."""
        try:
            if stream_id in self._change_streams:
                change_stream = self._change_streams[stream_id]
                await change_stream.close()
                del self._change_streams[stream_id]
                
        except Exception as e:
            self.logger.error(f"Error closing change stream {stream_id}: {e}")
    
    async def get_database_stats(self, connection: DatabaseConnection) -> Dict[str, Any]:
        """Get MongoDB database statistics."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            
            # Get database stats
            db_stats = await database.command("dbStats")
            
            # Get collection list
            collections = await database.list_collection_names()
            
            connection.query_count += 2
            
            return {
                'database_name': self.config.database,
                'collections': len(collections),
                'objects': db_stats.get('objects', 0),
                'data_size': db_stats.get('dataSize', 0),
                'storage_size': db_stats.get('storageSize', 0),
                'index_size': db_stats.get('indexSize', 0),
                'file_size': db_stats.get('fileSize', 0),
                'ns_size_mb': db_stats.get('nsSizeMB', 0),
                'extent_free_list': db_stats.get('extentFreeList', {}),
                'data_file_version': db_stats.get('dataFileVersion', {}),
                'collection_names': collections
            }
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="get_database_stats",
                database_name=self._get_database_name(self.config),
                engine=self.engine
            )
    
    async def explain_query(
        self,
        connection: DatabaseConnection,
        collection_name: str,
        operation: Dict[str, Any],
        verbosity: str = "executionStats"
    ) -> Dict[str, Any]:
        """Explain a MongoDB query for performance analysis."""
        try:
            connection.mark_used()
            
            database = connection.get_metadata("database")
            collection = database[collection_name]
            
            # Build explain query based on operation type
            if operation.get('operation') == 'find':
                cursor = collection.find(operation.get('filter', {}))
                if operation.get('sort'):
                    cursor = cursor.sort(operation['sort'])
                if operation.get('limit'):
                    cursor = cursor.limit(operation['limit'])
                
                explain_result = await cursor.explain(verbosity)
            
            elif operation.get('operation') == 'aggregate':
                cursor = collection.aggregate(operation.get('pipeline', []))
                explain_result = await cursor.explain(verbosity)
            
            else:
                raise ValueError(f"Explain not supported for operation: {operation.get('operation')}")
            
            connection.query_count += 1
            return explain_result
            
        except Exception as e:
            raise wrap_database_error(
                e,
                operation="explain_query",
                database_name=self._get_database_name(self.config),
                engine=self.engine,
                collection_name=collection_name
            )
    
    # Utility methods
    
    def _log_query(self, query: str, parameters: Any = None) -> None:
        """Log query execution for debugging."""
        if self.logger.isEnabledFor(logging.DEBUG):
            if parameters:
                self.logger.debug(f"Executing MongoDB operation: {query[:200]}... with parameters: {parameters}")
            else:
                self.logger.debug(f"Executing MongoDB operation: {query[:200]}...")
    
    @property
    def engine(self) -> DatabaseEngine:
        """Get the database engine type."""
        return DatabaseEngine.MONGODB
    
    @property
    def is_available(self) -> bool:
        """Check if MongoDB adapter is available."""
        return MOTOR_AVAILABLE
    
    def __str__(self) -> str:
        """String representation of the adapter."""
        return f"MongoDBAdapter(host={self.config.host}, database={self.config.database})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the adapter."""
        return (
            f"MongoDBAdapter("
            f"host={self.config.host}, "
            f"port={self.config.port}, "
            f"database={self.config.database}, "
            f"replica_set={self._replica_set_config.get('replica_set_name', 'None')}, "
            f"ssl_enabled={hasattr(self.config, 'ssl') and self.config.ssl and self.config.ssl.enabled}"
            f")"
        )
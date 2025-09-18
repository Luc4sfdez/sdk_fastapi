"""
MongoDB Database Adapter Example.

This example demonstrates the comprehensive usage of the MongoDB adapter
including enterprise features, connection management, and advanced operations.

Features demonstrated:
- Basic document operations (CRUD)
- Transaction management with sessions
- MongoDB-specific features (aggregation, indexing)
- Bulk operations and performance optimization
- SSL/TLS configuration
- Replica set configuration
- Change streams for real-time updates
- Error handling and graceful fallback

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Optional BSON dependency
try:
    from bson import ObjectId
    BSON_AVAILABLE = True
except ImportError:
    BSON_AVAILABLE = False
    ObjectId = None

from fastapi_microservices_sdk.database.config import (
    DatabaseConnectionConfig, DatabaseEngine, DatabaseCredentials,
    ConnectionPoolConfig, SSLConfig
)
from fastapi_microservices_sdk.database.adapters.mongodb import MongoDBAdapter
from fastapi_microservices_sdk.database.adapters.base import (
    QueryType, IsolationLevel, TransactionContext
)
from fastapi_microservices_sdk.database.exceptions import DatabaseError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MongoDBAdapterExample:
    """Comprehensive MongoDB adapter example."""
    
    def __init__(self):
        self.adapter: Optional[MongoDBAdapter] = None
        self.connection = None
    
    def create_basic_config(self) -> DatabaseConnectionConfig:
        """Create basic MongoDB configuration."""
        return DatabaseConnectionConfig(
            engine=DatabaseEngine.MONGODB,
            host="localhost",
            port=27017,
            database="test_microservices",
            credentials=DatabaseCredentials(
                username="test_user",
                password="test_password"
            ),
            pool=ConnectionPoolConfig(
                min_connections=2,
                max_connections=20,
                connection_timeout=30,
                idle_timeout=300,
                max_lifetime=3600
            )
        )
    
    def create_ssl_config(self) -> DatabaseConnectionConfig:
        """Create MongoDB configuration with SSL/TLS."""
        config = self.create_basic_config()
        config.ssl = SSLConfig(
            enabled=True,
            verify_mode="CERT_REQUIRED",
            check_hostname=True,
            ca_cert_path="/path/to/ca-cert.pem",
            client_cert_path="/path/to/client-cert.pem",
            client_key_path="/path/to/client-key.pem"
        )
        return config
    
    def create_replica_set_config(self) -> DatabaseConnectionConfig:
        """Create MongoDB configuration with replica set."""
        config = self.create_basic_config()
        # Add replica set configuration
        config.replica_set = {
            'replica_set_name': 'rs0',
            'read_preference': 'secondaryPreferred',
            'write_concern': 'majority',
            'read_concern': 'majority'
        }
        return config
    
    async def initialize_adapter(self, use_ssl: bool = False, use_replica_set: bool = False):
        """Initialize MongoDB adapter with configuration."""
        try:
            if use_ssl:
                config = self.create_ssl_config()
                logger.info("Creating MongoDB adapter with SSL/TLS configuration")
            elif use_replica_set:
                config = self.create_replica_set_config()
                logger.info("Creating MongoDB adapter with replica set configuration")
            else:
                config = self.create_basic_config()
                logger.info("Creating basic MongoDB adapter configuration")
            
            self.adapter = MongoDBAdapter(config)
            
            # Check availability
            if not self.adapter.is_available:
                logger.warning("MongoDB adapter not available - motor not installed")
                return False
            
            # Initialize adapter
            await self.adapter.initialize()
            logger.info(f"MongoDB adapter initialized: {self.adapter}")
            
            # Create connection
            self.connection = await self.adapter.create_connection()
            logger.info(f"Created connection: {self.connection.connection_id}")
            
            return True
            
        except DatabaseError as e:
            logger.error(f"Failed to initialize MongoDB adapter: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            return False
    
    async def demonstrate_basic_operations(self):
        """Demonstrate basic document operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Basic Document Operations Demo ===")
        
        try:
            # Create collection (optional - MongoDB creates collections automatically)
            await self.adapter.create_collection(
                self.connection,
                "users",
                {
                    "validator": {
                        "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["name", "email"],
                            "properties": {
                                "name": {"bsonType": "string"},
                                "email": {"bsonType": "string"},
                                "age": {"bsonType": "int", "minimum": 0}
                            }
                        }
                    }
                }
            )
            logger.info("Created users collection with schema validation")
            
            # Insert single document
            result = await self.adapter.execute_query(
                self.connection,
                "insert users",
                {
                    "documents": [{
                        "name": "John Doe",
                        "email": "john@example.com",
                        "age": 30,
                        "department": "Engineering",
                        "skills": ["Python", "MongoDB", "FastAPI"],
                        "metadata": {
                            "created_at": datetime.utcnow(),
                            "active": True,
                            "preferences": {
                                "theme": "dark",
                                "notifications": True
                            }
                        }
                    }]
                },
                QueryType.INSERT
            )
            logger.info(f"Inserted document: {result.data}")
            
            # Find single document
            user = await self.adapter.fetch_one(
                self.connection,
                "find users",
                {"filter": {"email": "john@example.com"}}
            )
            logger.info(f"Found user: {user}")
            
            # Update document
            result = await self.adapter.execute_query(
                self.connection,
                "update users",
                {
                    "filter": {"email": "john@example.com"},
                    "update": {"$set": {"age": 31, "metadata.last_updated": datetime.utcnow()}},
                    "multi": False
                },
                QueryType.UPDATE
            )
            logger.info(f"Updated document: {result.rows_affected} documents modified")
            
            # Find multiple documents with projection and sorting
            users = await self.adapter.fetch_many(
                self.connection,
                "find users",
                {
                    "filter": {"metadata.active": True},
                    "projection": {"name": 1, "email": 1, "department": 1},
                    "sort": [("name", 1)],
                    "limit": 10
                }
            )
            logger.info(f"Found {len(users)} active users")
            
        except DatabaseError as e:
            logger.error(f"Document operation failed: {e}")
    
    async def demonstrate_batch_operations(self):
        """Demonstrate batch operations and bulk operations."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Batch Operations Demo ===")
        
        try:
            # Batch insert using execute_many
            users_data = [
                {
                    "documents": [{
                        "name": "Alice Smith",
                        "email": "alice@example.com",
                        "age": 28,
                        "department": "Marketing",
                        "skills": ["Analytics", "Content", "SEO"]
                    }]
                },
                {
                    "documents": [{
                        "name": "Bob Johnson",
                        "email": "bob@example.com",
                        "age": 35,
                        "department": "Sales",
                        "skills": ["CRM", "Negotiation", "Presentations"]
                    }]
                },
                {
                    "documents": [{
                        "name": "Carol Brown",
                        "email": "carol@example.com",
                        "age": 42,
                        "department": "HR",
                        "skills": ["Recruiting", "Training", "Policy"]
                    }]
                }
            ]
            
            result = await self.adapter.execute_many(
                self.connection,
                "insert users",
                users_data
            )
            logger.info(f"Batch insert: {result.rows_affected} documents inserted")
            
            # Bulk write operations
            bulk_operations = [
                {
                    "operation": "insert",
                    "document": {
                        "name": "David Wilson",
                        "email": "david@example.com",
                        "age": 29,
                        "department": "Engineering"
                    }
                },
                {
                    "operation": "update",
                    "filter": {"email": "alice@example.com"},
                    "update": {"$set": {"age": 29}},
                    "multi": False
                },
                {
                    "operation": "update",
                    "filter": {"department": "Engineering"},
                    "update": {"$set": {"metadata.team": "Backend"}},
                    "multi": True
                }
            ]
            
            result = await self.adapter.bulk_write(
                self.connection,
                "users",
                bulk_operations
            )
            logger.info(f"Bulk write: {result}")
            
            # Verify total count
            total_users = await self.adapter.fetch_one(
                self.connection,
                "aggregate users",
                {"pipeline": [{"$count": "total"}]}
            )
            logger.info(f"Total users in database: {total_users.get('total', 0) if total_users else 0}")
            
        except DatabaseError as e:
            logger.error(f"Batch operation failed: {e}")
    
    async def demonstrate_transactions(self):
        """Demonstrate transaction management with sessions."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Transaction Management Demo ===")
        
        try:
            # Start transaction with isolation level
            async with TransactionContext(
                self.connection,
                isolation_level=IsolationLevel.READ_COMMITTED
            ) as tx:
                logger.info("Started transaction with READ COMMITTED isolation")
                
                # Insert a user
                await self.adapter.execute_query(
                    self.connection,
                    "insert users",
                    {
                        "documents": [{
                            "name": "Transaction User",
                            "email": "tx@example.com",
                            "age": 25,
                            "department": "Testing"
                        }]
                    }
                )
                logger.info("Inserted user in transaction")
                
                # Update user
                await self.adapter.execute_query(
                    self.connection,
                    "update users",
                    {
                        "filter": {"email": "tx@example.com"},
                        "update": {"$set": {"age": 26, "verified": True}},
                        "multi": False
                    }
                )
                logger.info("Updated user in transaction")
                
                # Verify user state within transaction
                user = await self.adapter.fetch_one(
                    self.connection,
                    "find users",
                    {"filter": {"email": "tx@example.com"}}
                )
                logger.info(f"User in transaction: age = {user.get('age') if user else 'Not found'}")
                
                # Transaction will auto-commit when exiting context
            
            logger.info("Transaction completed successfully")
            
        except DatabaseError as e:
            logger.error(f"Transaction failed: {e}")
    
    async def demonstrate_mongodb_features(self):
        """Demonstrate MongoDB-specific features."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== MongoDB-Specific Features Demo ===")
        
        try:
            # Create indexes for performance
            await self.adapter.create_index(
                self.connection,
                "users",
                [("email", 1)],
                {"unique": True, "name": "email_unique"}
            )
            logger.info("Created unique index on email field")
            
            await self.adapter.create_index(
                self.connection,
                "users",
                [("department", 1), ("age", -1)],
                {"name": "dept_age_compound"}
            )
            logger.info("Created compound index on department and age")
            
            # Text search index
            await self.adapter.create_index(
                self.connection,
                "users",
                [("name", "text"), ("skills", "text")],
                {"name": "text_search"}
            )
            logger.info("Created text search index")
            
            # Aggregation pipeline example
            pipeline_results = await self.adapter.aggregate_pipeline(
                self.connection,
                "users",
                [
                    {"$match": {"metadata.active": {"$ne": False}}},
                    {"$group": {
                        "_id": "$department",
                        "count": {"$sum": 1},
                        "avg_age": {"$avg": "$age"},
                        "skills": {"$addToSet": "$skills"}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 5}
                ]
            )
            logger.info(f"Aggregation results: {len(pipeline_results)} departments")
            for dept in pipeline_results:
                logger.info(f"  {dept['_id']}: {dept['count']} users, avg age {dept.get('avg_age', 0):.1f}")
            
            # Advanced aggregation with lookup (if you have related collections)
            advanced_pipeline = await self.adapter.aggregate_pipeline(
                self.connection,
                "users",
                [
                    {"$match": {"age": {"$gte": 25}}},
                    {"$addFields": {
                        "age_group": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$lt": ["$age", 30]}, "then": "Young"},
                                    {"case": {"$lt": ["$age", 40]}, "then": "Adult"},
                                    {"case": {"$gte": ["$age", 40]}, "then": "Senior"}
                                ],
                                "default": "Unknown"
                            }
                        }
                    }},
                    {"$group": {
                        "_id": "$age_group",
                        "count": {"$sum": 1},
                        "departments": {"$addToSet": "$department"}
                    }},
                    {"$sort": {"count": -1}}
                ]
            )
            logger.info(f"Age group analysis: {advanced_pipeline}")
            
            # Geospatial operations (if you have location data)
            await self.adapter.execute_query(
                self.connection,
                "update users",
                {
                    "filter": {"email": "john@example.com"},
                    "update": {
                        "$set": {
                            "location": {
                                "type": "Point",
                                "coordinates": [-73.9857, 40.7484]  # NYC coordinates
                            }
                        }
                    }
                }
            )
            
            # Create geospatial index
            await self.adapter.create_index(
                self.connection,
                "users",
                [("location", "2dsphere")],
                {"name": "location_geo"}
            )
            logger.info("Created geospatial index and added location data")
            
        except DatabaseError as e:
            logger.error(f"MongoDB feature demonstration failed: {e}")
    
    async def demonstrate_performance_monitoring(self):
        """Demonstrate performance monitoring and optimization."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Performance Monitoring Demo ===")
        
        try:
            # Get collection statistics
            collection_stats = await self.adapter.get_collection_stats(self.connection, "users")
            logger.info(f"Users collection stats:")
            logger.info(f"  Documents: {collection_stats['document_count']}")
            logger.info(f"  Size: {collection_stats['size_bytes']} bytes")
            logger.info(f"  Storage size: {collection_stats['storage_size_bytes']} bytes")
            logger.info(f"  Index size: {collection_stats['total_index_size_bytes']} bytes")
            logger.info(f"  Average document size: {collection_stats['average_object_size']} bytes")
            logger.info(f"  Indexes: {collection_stats['index_count']}")
            
            for idx in collection_stats['indexes']:
                logger.info(f"    - {idx['name']}: {idx['key']} (unique: {idx['unique']})")
            
            # Explain query performance
            explain_result = await self.adapter.explain_query(
                self.connection,
                "users",
                {
                    "operation": "find",
                    "filter": {"department": "Engineering"},
                    "sort": [("age", -1)]
                }
            )
            
            if 'executionStats' in explain_result:
                stats = explain_result['executionStats']
                logger.info("Query execution stats:")
                logger.info(f"  Execution time: {stats.get('executionTimeMillis', 0)} ms")
                logger.info(f"  Documents examined: {stats.get('totalDocsExamined', 0)}")
                logger.info(f"  Documents returned: {stats.get('totalDocsReturned', 0)}")
                logger.info(f"  Index used: {stats.get('indexesUsed', [])}")
            
            # Get database statistics
            db_stats = await self.adapter.get_database_stats(self.connection)
            logger.info("Database statistics:")
            logger.info(f"  Collections: {db_stats['collections']}")
            logger.info(f"  Objects: {db_stats['objects']}")
            logger.info(f"  Data size: {db_stats['data_size']} bytes")
            logger.info(f"  Storage size: {db_stats['storage_size']} bytes")
            logger.info(f"  Index size: {db_stats['index_size']} bytes")
            
        except DatabaseError as e:
            logger.error(f"Performance monitoring failed: {e}")
    
    async def demonstrate_change_streams(self):
        """Demonstrate change streams for real-time updates."""
        if not self.connection:
            logger.error("No connection available")
            return
        
        logger.info("=== Change Streams Demo ===")
        
        try:
            # Create change stream for users collection
            stream_id = await self.adapter.create_change_stream(
                self.connection,
                "users",
                [
                    {"$match": {"operationType": {"$in": ["insert", "update", "delete"]}}},
                    {"$project": {
                        "operationType": 1,
                        "documentKey": 1,
                        "fullDocument": 1,
                        "updateDescription": 1
                    }}
                ]
            )
            logger.info(f"Created change stream: {stream_id}")
            
            # Simulate some changes in another task
            async def make_changes():
                await asyncio.sleep(1)  # Wait a bit
                
                # Insert a new document
                await self.adapter.execute_query(
                    self.connection,
                    "insert users",
                    {
                        "documents": [{
                            "name": "Change Stream Test",
                            "email": "changestream@example.com",
                            "age": 25,
                            "department": "Testing"
                        }]
                    }
                )
                
                await asyncio.sleep(0.5)
                
                # Update the document
                await self.adapter.execute_query(
                    self.connection,
                    "update users",
                    {
                        "filter": {"email": "changestream@example.com"},
                        "update": {"$set": {"age": 26}},
                        "multi": False
                    }
                )
            
            # Start the changes task
            changes_task = asyncio.create_task(make_changes())
            
            # Listen for changes (with timeout)
            changes_received = 0
            max_changes = 2
            timeout = 5.0
            
            while changes_received < max_changes:
                try:
                    change = await self.adapter.get_change_stream_next(stream_id, timeout=timeout)
                    if change:
                        logger.info(f"Change detected: {change['operationType']} on {change.get('documentKey', {})}")
                        if change.get('fullDocument'):
                            logger.info(f"  Document: {change['fullDocument'].get('name', 'Unknown')}")
                        changes_received += 1
                    else:
                        logger.info("No changes detected within timeout")
                        break
                except Exception as e:
                    logger.error(f"Error reading change stream: {e}")
                    break
            
            # Wait for changes task to complete
            await changes_task
            
            # Close change stream
            await self.adapter.close_change_stream(stream_id)
            logger.info("Change stream closed")
            
        except DatabaseError as e:
            logger.error(f"Change streams demonstration failed: {e}")
    
    async def demonstrate_health_check(self):
        """Demonstrate health check functionality."""
        if not self.adapter:
            logger.error("No adapter available")
            return
        
        logger.info("=== Health Check Demo ===")
        
        try:
            # Perform health check
            health = await self.adapter.health_check()
            
            if health['healthy']:
                logger.info("✅ Database is healthy")
                logger.info(f"  Response time: {health['response_time']:.3f}s")
                logger.info(f"  Database: {health['database_name']}")
                logger.info(f"  MongoDB version: {health['mongodb_version']}")
                logger.info(f"  Server uptime: {health['server_uptime']} seconds")
                logger.info(f"  Database size: {health['database_size_bytes']} bytes")
                logger.info(f"  Collections: {health['collection_count']}")
                logger.info(f"  Documents: {health['document_count']}")
                logger.info(f"  Connections: {health['connections']['current']}/{health['connections']['available']}")
                logger.info(f"  Operations: Insert={health['operations']['insert']}, Query={health['operations']['query']}")
                
                if health['replica_set']['enabled']:
                    logger.info(f"  Replica set: {health['replica_set']['name']} ({health['replica_set']['members']} members)")
                    logger.info(f"  Primary: {health['replica_set']['primary']}")
                else:
                    logger.info("  Replica set: Not configured")
            else:
                logger.error(f"❌ Database is unhealthy: {health['error']}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.connection:
                # Clean up test data
                await self.adapter.execute_query(
                    self.connection,
                    "delete users",
                    {"filter": {}},  # Delete all documents
                    QueryType.DELETE
                )
                logger.info("Cleaned up test documents")
                
                # Drop collection
                await self.adapter.drop_collection(self.connection, "users")
                logger.info("Dropped test collection")
                
                # Close connection
                await self.connection.close()
                logger.info("Connection closed")
            
            if self.adapter:
                await self.adapter.shutdown()
                logger.info("Adapter shutdown completed")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


async def main():
    """Main example execution."""
    example = MongoDBAdapterExample()
    
    try:
        # Initialize adapter (try different configurations)
        logger.info("🚀 Starting MongoDB Adapter Example")
        
        # Try basic configuration first
        if not await example.initialize_adapter(use_ssl=False, use_replica_set=False):
            logger.warning("Failed to initialize with basic config, trying graceful fallback...")
            return
        
        # Run demonstrations
        await example.demonstrate_basic_operations()
        await example.demonstrate_batch_operations()
        await example.demonstrate_transactions()
        await example.demonstrate_mongodb_features()
        await example.demonstrate_performance_monitoring()
        await example.demonstrate_change_streams()
        await example.demonstrate_health_check()
        
        logger.info("✅ All demonstrations completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Example execution failed: {e}")
    
    finally:
        # Always cleanup
        await example.cleanup()
        logger.info("🏁 MongoDB Adapter Example completed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
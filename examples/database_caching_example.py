"""
Database Caching System Example

This example demonstrates the comprehensive database caching capabilities
of the FastAPI Microservices SDK, including multi-backend caching,
intelligent strategies, and automatic invalidation.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from fastapi_microservices_sdk.database.caching import (
    CacheManager,
    CacheConfig,
    CacheBackend,
    CacheStrategy,
    InvalidationPolicy,
    SerializationFormat,
    InvalidationManager,
    InvalidationEvent,
    InvalidationRule
)
from fastapi_microservices_sdk.database.manager import DatabaseManager
from fastapi_microservices_sdk.database.config import DatabaseConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_caching_example():
    """Demonstrate basic caching operations."""
    print("\n" + "="*60)
    print("🚀 BASIC CACHING OPERATIONS EXAMPLE")
    print("="*60)
    
    # Configure cache
    cache_config = CacheConfig(
        enabled=True,
        default_backend=CacheBackend.MEMORY,
        default_strategy=CacheStrategy.LRU,
        default_ttl=timedelta(minutes=30),
        metrics_enabled=True
    )
    
    # Create database manager (mock for example)
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    # Initialize cache manager
    cache_manager = CacheManager(cache_config, db_manager)
    await cache_manager.initialize()
    
    try:
        # Example database operations with caching
        database_name = "users_db"
        
        # 1. Cache a query result
        query = "SELECT * FROM users WHERE active = true"
        result_data = [
            {"id": 1, "name": "Alice", "email": "alice@example.com", "active": True},
            {"id": 2, "name": "Bob", "email": "bob@example.com", "active": True}
        ]
        
        print(f"📝 Caching query result...")
        success = await cache_manager.set(
            database_name=database_name,
            query=query,
            result=result_data,
            table_name="users",
            tags=["users", "active_users"]
        )
        print(f"✅ Cache set successful: {success}")
        
        # 2. Retrieve from cache
        print(f"🔍 Retrieving from cache...")
        cached_result = await cache_manager.get(
            database_name=database_name,
            query=query,
            table_name="users"
        )
        
        if cached_result:
            print(f"✅ Cache hit! Retrieved {len(cached_result)} records")
            print(f"   First record: {cached_result[0]}")
        else:
            print("❌ Cache miss")
        
        # 3. Cache with parameters
        parameterized_query = "SELECT * FROM users WHERE age > ? AND city = ?"
        parameters = {"age": 25, "city": "New York"}
        
        param_result = [
            {"id": 3, "name": "Charlie", "age": 30, "city": "New York"}
        ]
        
        await cache_manager.set(
            database_name=database_name,
            query=parameterized_query,
            result=param_result,
            parameters=parameters,
            table_name="users"
        )
        
        # Retrieve parameterized query
        cached_param_result = await cache_manager.get(
            database_name=database_name,
            query=parameterized_query,
            parameters=parameters,
            table_name="users"
        )
        
        print(f"✅ Parameterized query cached and retrieved: {cached_param_result is not None}")
        
        # 4. Get cache statistics
        stats = await cache_manager.get_stats()
        print(f"\n📊 Cache Statistics:")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Hit Rate: {stats['hit_rate']:.2%}")
        print(f"   Sets: {stats['sets']}")
        
    finally:
        await cache_manager.shutdown()


async def multi_backend_caching_example():
    """Demonstrate multi-backend caching with Redis and Memory."""
    print("\n" + "="*60)
    print("🔄 MULTI-BACKEND CACHING EXAMPLE")
    print("="*60)
    
    # Configure cache with Redis as default and Memory for specific database
    cache_config = CacheConfig(
        enabled=True,
        default_backend=CacheBackend.MEMORY,  # Using memory for demo
        redis_config={
            "host": "localhost",
            "port": 6379,
            "db": 1,
            "connection_pool_size": 5
        },
        memory_config={
            "max_size": 500,
            "max_memory_mb": 50
        }
    )
    
    # Set database-specific backend
    cache_config.set_database_config("analytics_db", {"backend": "memory"})
    
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    cache_manager = CacheManager(cache_config, db_manager)
    await cache_manager.initialize()
    
    try:
        # Cache data in different databases
        databases = ["users_db", "analytics_db", "products_db"]
        
        for db_name in databases:
            query = f"SELECT COUNT(*) FROM main_table"
            result = {"count": 1000 + hash(db_name) % 5000}
            
            await cache_manager.set(
                database_name=db_name,
                query=query,
                result=result,
                tags=[f"db:{db_name}", "count_query"]
            )
            
            print(f"✅ Cached count query for {db_name}")
        
        # Retrieve from different backends
        for db_name in databases:
            query = f"SELECT COUNT(*) FROM main_table"
            cached_result = await cache_manager.get(
                database_name=db_name,
                query=query
            )
            
            if cached_result:
                print(f"🔍 Retrieved from {db_name}: {cached_result}")
        
        # Get backend-specific stats
        for db_name in databases:
            stats = await cache_manager.get_stats(db_name)
            print(f"📊 Stats for {db_name}: {stats.get('backend_stats', {})}")
    
    finally:
        await cache_manager.shutdown()


async def cache_invalidation_example():
    """Demonstrate cache invalidation strategies."""
    print("\n" + "="*60)
    print("🗑️ CACHE INVALIDATION EXAMPLE")
    print("="*60)
    
    cache_config = CacheConfig(
        enabled=True,
        default_backend=CacheBackend.MEMORY,
        invalidation_policy=InvalidationPolicy.TAG_BASED,
        default_ttl=timedelta(hours=1)
    )
    
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    cache_manager = CacheManager(cache_config, db_manager)
    await cache_manager.initialize()
    
    try:
        database_name = "ecommerce_db"
        
        # Cache multiple queries with different tags
        queries_and_tags = [
            ("SELECT * FROM products WHERE category = 'electronics'", ["products", "electronics"]),
            ("SELECT * FROM products WHERE category = 'books'", ["products", "books"]),
            ("SELECT COUNT(*) FROM products", ["products", "count"]),
            ("SELECT * FROM orders WHERE status = 'pending'", ["orders", "pending"]),
            ("SELECT * FROM users WHERE active = true", ["users", "active"])
        ]
        
        # Cache all queries
        for query, tags in queries_and_tags:
            result = {"data": f"mock_result_for_{hash(query) % 1000}"}
            await cache_manager.set(
                database_name=database_name,
                query=query,
                result=result,
                tags=tags
            )
            print(f"✅ Cached query with tags: {tags}")
        
        # Show initial cache stats
        stats = await cache_manager.get_stats()
        print(f"\n📊 Initial cache entries: {stats['sets']}")
        
        # 1. Invalidate by specific tags
        print(f"\n🗑️ Invalidating all 'products' entries...")
        invalidated = await cache_manager.invalidate_by_tags(["products"])
        print(f"✅ Invalidated {invalidated} entries")
        
        # 2. Invalidate by table
        print(f"\n🗑️ Invalidating all 'orders' table entries...")
        await cache_manager.clear_table_cache(database_name, "orders")
        print(f"✅ Cleared orders table cache")
        
        # 3. Event-based invalidation
        print(f"\n📡 Simulating database events...")
        
        # Simulate table update event
        invalidation_event = InvalidationEvent(
            event_type="table_update",
            database_name=database_name,
            table_name="users",
            operation="UPDATE",
            tags=["users", "active"]
        )
        
        # This would typically be called by database triggers or ORM hooks
        # For demo, we'll simulate it
        await cache_manager.invalidate_by_tags(invalidation_event.tags)
        print(f"✅ Processed table update event")
        
        # Final stats
        final_stats = await cache_manager.get_stats()
        print(f"\n📊 Final cache entries: {final_stats.get('entry_count', 0)}")
        print(f"📊 Total invalidations: {final_stats.get('deletes', 0)}")
    
    finally:
        await cache_manager.shutdown()


async def cache_strategies_example():
    """Demonstrate different caching strategies."""
    print("\n" + "="*60)
    print("🧠 CACHE STRATEGIES EXAMPLE")
    print("="*60)
    
    strategies = [
        CacheStrategy.LRU,
        CacheStrategy.LFU,
        CacheStrategy.TTL,
        CacheStrategy.ADAPTIVE
    ]
    
    for strategy in strategies:
        print(f"\n🔄 Testing {strategy.value.upper()} Strategy")
        print("-" * 40)
        
        cache_config = CacheConfig(
            enabled=True,
            default_backend=CacheBackend.MEMORY,
            default_strategy=strategy,
            memory_config={
                "max_size": 5,  # Small size to trigger evictions
                "max_memory_mb": 10
            }
        )
        
        db_config = DatabaseConfig()
        db_manager = DatabaseManager(db_config)
        
        cache_manager = CacheManager(cache_config, db_manager)
        await cache_manager.initialize()
        
        try:
            database_name = "test_db"
            
            # Cache multiple entries to trigger eviction
            for i in range(8):  # More than max_size
                query = f"SELECT * FROM table_{i}"
                result = {"data": f"result_{i}", "timestamp": datetime.now().isoformat()}
                
                await cache_manager.set(
                    database_name=database_name,
                    query=query,
                    result=result,
                    ttl=timedelta(seconds=30) if strategy == CacheStrategy.TTL else None
                )
                
                print(f"   Cached query_{i}")
                
                # Access some entries multiple times for LFU testing
                if strategy == CacheStrategy.LFU and i < 3:
                    for _ in range(i + 1):
                        await cache_manager.get(database_name, query)
            
            # Check what's still in cache
            print(f"\n   Checking cache contents...")
            cached_count = 0
            for i in range(8):
                query = f"SELECT * FROM table_{i}"
                result = await cache_manager.get(database_name, query)
                if result:
                    cached_count += 1
                    print(f"   ✅ Query_{i} still cached")
            
            print(f"   📊 {cached_count}/8 entries remain in cache")
            
            # Get strategy-specific stats
            stats = await cache_manager.get_stats()
            print(f"   📈 Hit rate: {stats['hit_rate']:.2%}")
        
        finally:
            await cache_manager.shutdown()


async def performance_monitoring_example():
    """Demonstrate cache performance monitoring."""
    print("\n" + "="*60)
    print("📈 PERFORMANCE MONITORING EXAMPLE")
    print("="*60)
    
    cache_config = CacheConfig(
        enabled=True,
        default_backend=CacheBackend.MEMORY,
        metrics_enabled=True,
        metrics_interval=1.0  # Collect metrics every second
    )
    
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    cache_manager = CacheManager(cache_config, db_manager)
    await cache_manager.initialize()
    
    # Add performance callbacks
    async def on_cache_hit(key: str, value: Any):
        print(f"🎯 Cache hit for key: {key[:50]}...")
    
    async def on_cache_miss(key: str):
        print(f"❌ Cache miss for key: {key[:50]}...")
    
    cache_manager.add_hit_callback(on_cache_hit)
    cache_manager.add_miss_callback(on_cache_miss)
    
    try:
        database_name = "performance_db"
        
        # Simulate workload
        print("🏃 Simulating cache workload...")
        
        # Cache some data
        for i in range(5):
            query = f"SELECT * FROM performance_table WHERE id = {i}"
            result = {"id": i, "data": f"performance_data_{i}"}
            
            await cache_manager.set(
                database_name=database_name,
                query=query,
                result=result
            )
        
        # Mix of hits and misses
        for i in range(10):
            query = f"SELECT * FROM performance_table WHERE id = {i % 7}"  # Some will miss
            result = await cache_manager.get(database_name, query)
            
            # Simulate processing time
            await asyncio.sleep(0.1)
        
        # Get comprehensive performance stats
        stats = await cache_manager.get_stats()
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Total Operations: {stats['hits'] + stats['misses']}")
        print(f"   Cache Hits: {stats['hits']}")
        print(f"   Cache Misses: {stats['misses']}")
        print(f"   Hit Rate: {stats['hit_rate']:.2%}")
        print(f"   Average Get Time: {stats['average_get_time']:.4f}s")
        print(f"   Average Set Time: {stats['average_set_time']:.4f}s")
        
        # Backend-specific stats
        backend_stats = stats.get('backend_stats', {})
        if backend_stats:
            print(f"\n🔧 Backend Statistics:")
            for key, value in backend_stats.items():
                print(f"   {key}: {value}")
    
    finally:
        await cache_manager.shutdown()


async def integration_example():
    """Demonstrate integration with database operations."""
    print("\n" + "="*60)
    print("🔗 DATABASE INTEGRATION EXAMPLE")
    print("="*60)
    
    cache_config = CacheConfig(
        enabled=True,
        default_backend=CacheBackend.MEMORY,
        cache_warming_enabled=True,
        warming_batch_size=10
    )
    
    db_config = DatabaseConfig()
    db_manager = DatabaseManager(db_config)
    
    cache_manager = CacheManager(cache_config, db_manager)
    await cache_manager.initialize()
    
    try:
        database_name = "app_db"
        
        # Simulate typical application queries
        common_queries = [
            ("SELECT * FROM users WHERE role = 'admin'", "users"),
            ("SELECT COUNT(*) FROM orders WHERE status = 'completed'", "orders"),
            ("SELECT * FROM products WHERE featured = true", "products"),
            ("SELECT * FROM categories ORDER BY name", "categories")
        ]
        
        print("🔄 Simulating application database queries...")
        
        for query, table in common_queries:
            # Simulate database execution time
            execution_time = 0.05  # 50ms
            
            # Check if we should cache this query
            should_cache = cache_manager.should_cache_query(query, execution_time)
            print(f"   Query: {query[:40]}... Should cache: {should_cache}")
            
            if should_cache:
                # Simulate query result
                result = {
                    "data": f"mock_result_for_{table}",
                    "count": hash(query) % 100,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Cache the result
                await cache_manager.set(
                    database_name=database_name,
                    query=query,
                    result=result,
                    table_name=table
                )
        
        # Simulate cache hits on subsequent requests
        print(f"\n🔍 Simulating subsequent requests...")
        for query, table in common_queries:
            cached_result = await cache_manager.get(
                database_name=database_name,
                query=query,
                table_name=table
            )
            
            if cached_result:
                print(f"   ✅ Cache hit for {table} query")
            else:
                print(f"   ❌ Cache miss for {table} query")
        
        # Simulate database changes that require cache invalidation
        print(f"\n🔄 Simulating database changes...")
        
        # User role change - invalidate user queries
        await cache_manager.clear_table_cache(database_name, "users")
        print(f"   🗑️ Invalidated users cache after role change")
        
        # New order - invalidate order count queries
        await cache_manager.invalidate_by_tags(["orders", "count"])
        print(f"   🗑️ Invalidated order count cache after new order")
        
        # Final statistics
        final_stats = await cache_manager.get_stats()
        print(f"\n📊 Final Integration Stats:")
        print(f"   Cache Operations: {final_stats['sets'] + final_stats['hits'] + final_stats['misses']}")
        print(f"   Efficiency: {final_stats['hit_rate']:.2%} hit rate")
    
    finally:
        await cache_manager.shutdown()


async def main():
    """Run all caching examples."""
    print("🚀 FastAPI Microservices SDK - Database Caching Examples")
    print("=" * 80)
    
    examples = [
        ("Basic Caching Operations", basic_caching_example),
        ("Multi-Backend Caching", multi_backend_caching_example),
        ("Cache Invalidation", cache_invalidation_example),
        ("Cache Strategies", cache_strategies_example),
        ("Performance Monitoring", performance_monitoring_example),
        ("Database Integration", integration_example)
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n🎯 Running: {name}")
            await example_func()
            print(f"✅ Completed: {name}")
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            logger.exception(f"Error in {name}")
        
        # Small delay between examples
        await asyncio.sleep(1)
    
    print(f"\n🎉 All caching examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
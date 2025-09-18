"""
Database Monitoring & Analytics Example for FastAPI Microservices SDK.

This example demonstrates how to use the monitoring system to collect metrics,
analyze performance, detect anomalies, and generate health assessments for
database operations across different database engines.

Features demonstrated:
- Real-time metrics collection
- Performance trend analysis
- Query optimization recommendations
- Resource utilization monitoring
- Anomaly detection
- Health assessments and scoring
- Alerting and notifications
- Custom metrics and collectors

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timedelta
import random
import time

from fastapi_microservices_sdk.database import (
    DatabaseManager,
    DatabaseConfig,
    DatabaseConnectionConfig,
    DatabaseEngine
)
from fastapi_microservices_sdk.database.monitoring import (
    MonitoringManager,
    MonitoringConfig,
    MonitoringLevel,
    MetricsStorage,
    AlertChannel
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def setup_database_manager() -> DatabaseManager:
    """Setup database manager with multiple databases."""
    
    config = DatabaseConfig(
        default_database="main_db",
        databases={
            # PostgreSQL database
            "main_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.POSTGRESQL,
                host="localhost",
                port=5432,
                database="monitoring_demo",
                username="postgres",
                password="password",
                pool_size=10
            ),
            
            # MySQL database
            "analytics_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.MYSQL,
                host="localhost",
                port=3306,
                database="analytics_demo",
                username="mysql_user",
                password="mysql_password",
                pool_size=5
            ),
            
            # SQLite database
            "cache_db": DatabaseConnectionConfig(
                engine=DatabaseEngine.SQLITE,
                database="monitoring_cache.db"
            )
        }
    )
    
    manager = DatabaseManager(config)
    await manager.initialize()
    return manager


def setup_monitoring_config() -> MonitoringConfig:
    """Setup comprehensive monitoring configuration."""
    
    return MonitoringConfig(
        # General settings
        enabled=True,
        monitoring_level=MonitoringLevel.COMPREHENSIVE,
        
        # Metrics collection
        metrics_collection_interval=5.0,  # Collect every 5 seconds for demo
        metrics_retention_period=timedelta(hours=24),
        metrics_storage=MetricsStorage.MEMORY,
        
        # Query monitoring
        slow_query_threshold=1.0,  # 1 second threshold
        query_sampling_rate=1.0,  # Sample all queries for demo
        max_query_history=1000,
        
        # Performance monitoring
        performance_baseline_period=timedelta(minutes=30),
        performance_alert_threshold=2.0,
        
        # Health monitoring
        health_check_interval=10.0,  # Check every 10 seconds for demo
        health_check_timeout=5.0,
        
        # Connection monitoring
        connection_pool_monitoring=True,
        connection_leak_detection=True,
        connection_leak_threshold=300.0,
        
        # Alerting
        alerting_enabled=True,
        alert_channels=[AlertChannel.EMAIL, AlertChannel.WEBHOOK],
        alert_cooldown_period=timedelta(minutes=5),
        
        # Analytics
        analytics_enabled=True,
        query_optimization_enabled=True,
        predictive_analytics_enabled=True,
        
        # Notification settings
        notification_webhooks=["http://localhost:8080/alerts"],
        email_settings={
            "smtp_server": "localhost",
            "smtp_port": 587,
            "username": "alerts@example.com",
            "recipients": ["admin@example.com"]
        }
    )


async def simulate_database_activity(database_manager: DatabaseManager, monitoring_manager: MonitoringManager):
    """Simulate realistic database activity for monitoring demonstration."""
    logger.info("Starting database activity simulation...")
    
    # Sample queries for different scenarios
    queries = {
        "fast_queries": [
            "SELECT 1",
            "SELECT COUNT(*) FROM users WHERE active = true",
            "SELECT id, name FROM users WHERE id = 123"
        ],
        "slow_queries": [
            "SELECT * FROM users u JOIN posts p ON u.id = p.user_id WHERE u.created_at > '2023-01-01'",
            "SELECT COUNT(*) FROM posts WHERE content LIKE '%search%'",
            "SELECT u.*, p.* FROM users u, posts p WHERE u.created_at > '2020-01-01'"
        ],
        "optimization_candidates": [
            "SELECT * FROM users",  # SELECT *
            "SELECT name FROM users WHERE UPPER(name) = 'JOHN'",  # Function in WHERE
            "SELECT u.name, p.title FROM users u, posts p",  # Cartesian join
            "SELECT * FROM posts WHERE created_at > '2023-01-01'"  # No LIMIT
        ]
    }
    
    databases = ["main_db", "analytics_db", "cache_db"]
    
    # Simulate 2 minutes of activity
    for i in range(24):  # 24 iterations of 5 seconds each
        for db_name in databases:
            # Simulate different types of queries
            
            # Fast queries (most common)
            for _ in range(random.randint(5, 15)):
                query = random.choice(queries["fast_queries"])
                duration = random.uniform(0.01, 0.5)
                success = random.random() > 0.02  # 2% error rate
                
                monitoring_manager.record_query_execution(
                    db_name, query, duration, success,
                    Exception("Connection timeout") if not success else None
                )
            
            # Occasional slow queries
            if random.random() < 0.3:  # 30% chance
                query = random.choice(queries["slow_queries"])
                duration = random.uniform(1.5, 5.0)
                success = random.random() > 0.05  # 5% error rate for slow queries
                
                monitoring_manager.record_query_execution(
                    db_name, query, duration, success,
                    Exception("Query timeout") if not success else None
                )
            
            # Queries that need optimization
            if random.random() < 0.2:  # 20% chance
                query = random.choice(queries["optimization_candidates"])
                duration = random.uniform(0.5, 2.0)
                success = True
                
                monitoring_manager.record_query_execution(
                    db_name, query, duration, success
                )
        
        # Wait before next iteration
        await asyncio.sleep(5)
        
        # Log progress
        if (i + 1) % 6 == 0:
            logger.info(f"Simulation progress: {((i + 1) / 24) * 100:.0f}%")


async def demonstrate_health_monitoring(monitoring_manager: MonitoringManager):
    """Demonstrate health monitoring capabilities."""
    logger.info("\n=== Health Monitoring Demonstration ===")
    
    databases = ["main_db", "analytics_db", "cache_db"]
    
    for db_name in databases:
        try:
            health = await monitoring_manager.get_database_health(db_name)
            
            logger.info(f"\nDatabase: {db_name}")
            logger.info(f"  Overall Health: {health['overall_health']}")
            logger.info(f"  Health Score: {health['health_score']:.1f}/100")
            logger.info(f"  Assessment Time: {health['assessment_time']}")
            
            # Show trends
            if health['trends']:
                logger.info("  Performance Trends:")
                for trend in health['trends'][:3]:  # Show first 3 trends
                    direction_icon = {
                        'improving': '📈',
                        'stable': '➡️',
                        'degrading': '📉',
                        'volatile': '📊'
                    }.get(trend['direction'], '❓')
                    
                    logger.info(f"    {direction_icon} {trend['metric_name']}: {trend['change_percentage']:+.1f}%")
            
            # Show resource utilization
            if health['resource_analysis']:
                logger.info("  Resource Utilization:")
                for resource in health['resource_analysis']:
                    utilization = resource['current_utilization']
                    status_icon = '🔴' if utilization > 0.8 else '🟡' if utilization > 0.6 else '🟢'
                    logger.info(f"    {status_icon} {resource['resource_type']}: {utilization:.1%}")
            
            # Show anomalies
            if health['anomalies']:
                logger.info("  Anomalies Detected:")
                for anomaly in health['anomalies'][:3]:  # Show first 3 anomalies
                    severity_icon = {
                        'critical': '🚨',
                        'high': '⚠️',
                        'medium': '⚡',
                        'low': 'ℹ️'
                    }.get(anomaly['severity'], '❓')
                    
                    logger.info(f"    {severity_icon} {anomaly['title']}")
            
            # Show recommendations
            if health['recommendations']:
                logger.info("  Recommendations:")
                for rec in health['recommendations'][:3]:  # Show first 3 recommendations
                    logger.info(f"    💡 {rec}")
                    
        except Exception as e:
            logger.error(f"Failed to get health for {db_name}: {e}")


async def demonstrate_performance_trends(monitoring_manager: MonitoringManager):
    """Demonstrate performance trend analysis."""
    logger.info("\n=== Performance Trends Analysis ===")
    
    databases = ["main_db", "analytics_db", "cache_db"]
    
    for db_name in databases:
        try:
            # Analyze trends over the last hour (or available data)
            trends = await monitoring_manager.get_performance_trends(
                db_name, 
                period=timedelta(hours=1)
            )
            
            logger.info(f"\nDatabase: {db_name}")
            logger.info(f"  Trends analyzed: {len(trends)}")
            
            for trend in trends:
                direction_icon = {
                    'improving': '📈 Improving',
                    'stable': '➡️ Stable',
                    'degrading': '📉 Degrading',
                    'volatile': '📊 Volatile'
                }.get(trend['direction'], '❓ Unknown')
                
                logger.info(f"  📊 {trend['metric_name']}")
                logger.info(f"     Status: {direction_icon}")
                logger.info(f"     Change: {trend['change_percentage']:+.1f}%")
                logger.info(f"     Baseline: {trend['baseline_value']:.3f}")
                logger.info(f"     Current: {trend['current_value']:.3f}")
                logger.info(f"     Confidence: {trend['trend_confidence']:.1%}")
                
        except Exception as e:
            logger.error(f"Failed to analyze trends for {db_name}: {e}")


async def demonstrate_query_optimization(monitoring_manager: MonitoringManager):
    """Demonstrate query optimization recommendations."""
    logger.info("\n=== Query Optimization Analysis ===")
    
    # Sample problematic queries
    sample_queries = [
        "SELECT * FROM users WHERE created_at > '2023-01-01'",
        "SELECT name FROM users WHERE UPPER(name) = 'JOHN DOE'",
        "SELECT u.name, p.title FROM users u, posts p WHERE u.active = 1",
        "SELECT COUNT(*) FROM posts WHERE content LIKE '%search term%'",
        "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.id",
        "UPDATE users SET last_login = NOW() WHERE email = 'user@example.com'"
    ]
    
    try:
        suggestions = await monitoring_manager.get_query_optimization_suggestions(
            "main_db", 
            sample_queries
        )
        
        logger.info(f"Analyzed {len(sample_queries)} queries")
        logger.info(f"Found {len(suggestions)} optimization opportunities")
        
        for suggestion in suggestions:
            improvement_icon = '🚀' if suggestion['estimated_improvement'] > 50 else '⚡'
            
            logger.info(f"\n  {improvement_icon} {suggestion['issue_type'].replace('_', ' ').title()}")
            logger.info(f"     Issue: {suggestion['description']}")
            logger.info(f"     Suggestion: {suggestion['suggestion']}")
            logger.info(f"     Estimated Improvement: {suggestion['estimated_improvement']:.0f}%")
            logger.info(f"     Confidence: {suggestion['confidence']:.1%}")
            
            if suggestion['examples']:
                logger.info(f"     Example: {suggestion['examples'][0]}")
                
    except Exception as e:
        logger.error(f"Failed to analyze query optimization: {e}")


async def demonstrate_resource_utilization(monitoring_manager: MonitoringManager):
    """Demonstrate resource utilization analysis."""
    logger.info("\n=== Resource Utilization Analysis ===")
    
    databases = ["main_db", "analytics_db", "cache_db"]
    
    for db_name in databases:
        try:
            utilization = await monitoring_manager.get_resource_utilization(
                db_name,
                period=timedelta(hours=1)
            )
            
            logger.info(f"\nDatabase: {db_name}")
            
            for resource in utilization:
                current = resource['current_utilization']
                peak = resource['peak_utilization']
                average = resource['average_utilization']
                
                # Status indicators
                status_icon = '🔴' if current > 0.9 else '🟡' if current > 0.7 else '🟢'
                trend_icon = {
                    'improving': '📈',
                    'stable': '➡️',
                    'degrading': '📉',
                    'volatile': '📊'
                }.get(resource['trend'], '❓')
                
                logger.info(f"  {status_icon} {resource['resource_type'].replace('_', ' ').title()}")
                logger.info(f"     Current: {current:.1%}")
                logger.info(f"     Peak: {peak:.1%}")
                logger.info(f"     Average: {average:.1%}")
                logger.info(f"     Trend: {trend_icon} {resource['trend']}")
                
                if resource['projected_exhaustion']:
                    logger.info(f"     ⚠️ Projected exhaustion: {resource['projected_exhaustion']}")
                
                if resource['recommendations']:
                    logger.info("     Recommendations:")
                    for rec in resource['recommendations']:
                        logger.info(f"       💡 {rec}")
                        
        except Exception as e:
            logger.error(f"Failed to analyze resource utilization for {db_name}: {e}")


async def demonstrate_custom_metrics(monitoring_manager: MonitoringManager):
    """Demonstrate custom metrics collection."""
    logger.info("\n=== Custom Metrics Demonstration ===")
    
    # Register custom metric collectors
    async def custom_business_metric(adapter):
        """Example custom business metric."""
        # This could query business-specific data
        return random.uniform(100, 1000)  # Simulated business metric
    
    async def custom_cache_hit_ratio(adapter):
        """Example cache hit ratio metric."""
        return random.uniform(0.7, 0.95)  # Simulated cache hit ratio
    
    # Register the custom collectors
    monitoring_manager.metrics_collector.register_custom_collector(
        "business_transactions_per_minute", 
        custom_business_metric
    )
    
    monitoring_manager.metrics_collector.register_custom_collector(
        "cache_hit_ratio", 
        custom_cache_hit_ratio
    )
    
    logger.info("Registered custom metrics:")
    logger.info("  📊 business_transactions_per_minute")
    logger.info("  📊 cache_hit_ratio")
    logger.info("Custom metrics will be collected automatically with other metrics")


async def demonstrate_monitoring_status(monitoring_manager: MonitoringManager):
    """Demonstrate monitoring status and configuration."""
    logger.info("\n=== Monitoring Status ===")
    
    status = await monitoring_manager.get_monitoring_status()
    
    logger.info(f"Monitoring Status:")
    logger.info(f"  Initialized: {'✅' if status['initialized'] else '❌'}")
    logger.info(f"  Running: {'✅' if status['running'] else '❌'}")
    logger.info(f"  Metrics Collection: {'✅' if status['metrics_collection_enabled'] else '❌'}")
    logger.info(f"  Alerting: {'✅' if status['alerting_enabled'] else '❌'}")
    logger.info(f"  Analytics: {'✅' if status['analytics_enabled'] else '❌'}")
    logger.info(f"  Monitored Databases: {', '.join(status['monitored_databases'])}")
    logger.info(f"  Last Update: {status['last_update']}")


async def demonstrate_metrics_export(monitoring_manager: MonitoringManager):
    """Demonstrate metrics export functionality."""
    logger.info("\n=== Metrics Export ===")
    
    try:
        # Export metrics in JSON format
        json_metrics = await monitoring_manager.export_metrics(
            "main_db", 
            format="json", 
            period=timedelta(minutes=30)
        )
        
        logger.info("JSON Export Sample:")
        # Show first 200 characters of JSON export
        logger.info(f"  {json_metrics[:200]}...")
        
        # Export metrics in Prometheus format
        prom_metrics = await monitoring_manager.export_metrics(
            "main_db", 
            format="prometheus", 
            period=timedelta(minutes=30)
        )
        
        logger.info("\nPrometheus Export Sample:")
        # Show first few lines of Prometheus export
        lines = prom_metrics.split('\n')[:5]
        for line in lines:
            if line.strip():
                logger.info(f"  {line}")
        
        logger.info(f"\nTotal exported metrics: {len(json_metrics)} characters (JSON)")
        logger.info(f"Total exported metrics: {len(prom_metrics)} characters (Prometheus)")
        
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")


async def setup_alert_callbacks(monitoring_manager: MonitoringManager):
    """Setup alert and health callbacks for demonstration."""
    
    def alert_callback(alert_type: str, message: str, severity: str, database_name: str, metadata: dict):
        """Custom alert callback."""
        severity_icon = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }.get(severity, '❓')
        
        logger.info(f"🔔 ALERT: {severity_icon} [{database_name}] {alert_type}: {message}")
    
    async def health_callback(database_name: str, assessment: dict):
        """Custom health callback."""
        health_score = assessment.get('health_score', 0)
        overall_health = assessment.get('overall_health', 'unknown')
        
        health_icon = {
            'excellent': '💚',
            'good': '💛',
            'fair': '🧡',
            'poor': '❤️',
            'critical': '🚨'
        }.get(overall_health, '❓')
        
        logger.info(f"🏥 HEALTH: {health_icon} [{database_name}] {overall_health} ({health_score:.1f}/100)")
    
    # Register callbacks
    monitoring_manager.add_alert_callback(alert_callback)
    monitoring_manager.add_health_callback(health_callback)
    
    logger.info("Alert and health callbacks registered")


async def main():
    """Main demonstration function."""
    logger.info("Starting Database Monitoring & Analytics Example")
    
    try:
        # Setup database manager
        database_manager = await setup_database_manager()
        logger.info("Database manager initialized")
        
        # Setup monitoring configuration
        monitoring_config = setup_monitoring_config()
        logger.info("Monitoring configuration created")
        
        # Create monitoring manager
        monitoring_manager = MonitoringManager(monitoring_config, database_manager)
        
        # Setup callbacks
        await setup_alert_callbacks(monitoring_manager)
        
        # Initialize and start monitoring
        await monitoring_manager.initialize()
        await monitoring_manager.start_monitoring()
        logger.info("Monitoring started")
        
        # Show initial status
        await demonstrate_monitoring_status(monitoring_manager)
        
        # Register custom metrics
        await demonstrate_custom_metrics(monitoring_manager)
        
        # Simulate database activity
        await simulate_database_activity(database_manager, monitoring_manager)
        
        # Wait a bit for metrics to be collected
        logger.info("Waiting for metrics collection...")
        await asyncio.sleep(10)
        
        # Run demonstrations
        await demonstrate_health_monitoring(monitoring_manager)
        await demonstrate_performance_trends(monitoring_manager)
        await demonstrate_query_optimization(monitoring_manager)
        await demonstrate_resource_utilization(monitoring_manager)
        await demonstrate_metrics_export(monitoring_manager)
        
        logger.info("\n=== Example completed successfully ===")
        logger.info("Monitoring system demonstrated:")
        logger.info("  ✅ Real-time metrics collection")
        logger.info("  ✅ Performance trend analysis")
        logger.info("  ✅ Query optimization recommendations")
        logger.info("  ✅ Resource utilization monitoring")
        logger.info("  ✅ Health assessments and scoring")
        logger.info("  ✅ Custom metrics integration")
        logger.info("  ✅ Metrics export capabilities")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        
    finally:
        # Cleanup
        try:
            await monitoring_manager.stop_monitoring()
            await database_manager.shutdown()
            logger.info("Cleanup completed")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
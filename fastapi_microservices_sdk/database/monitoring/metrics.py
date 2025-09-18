"""
Metrics collection and management for database monitoring.

This module provides comprehensive metrics collection, storage, and
analysis capabilities for database performance monitoring.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import statistics
import json

from ..adapters.base import DatabaseAdapter
from ..config import DatabaseEngine
from .config import MonitoringConfig, MetricsStorage
from .exceptions import MonitoringError


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Individual metric value with timestamp."""
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetricValue':
        """Create from dictionary."""
        return cls(
            value=data['value'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            labels=data.get('labels', {})
        )


@dataclass
class DatabaseMetrics:
    """Collection of database metrics."""
    database_name: str
    engine: DatabaseEngine
    timestamp: datetime
    
    # Connection metrics
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_pool_utilization: float = 0.0
    
    # Query metrics
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    slow_queries: int = 0
    avg_query_duration: float = 0.0
    p95_query_duration: float = 0.0
    p99_query_duration: float = 0.0
    
    # Performance metrics
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    disk_utilization: float = 0.0
    network_io: float = 0.0
    
    # Error metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    deadlock_count: int = 0
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['engine'] = self.engine.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseMetrics':
        """Create from dictionary."""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['engine'] = DatabaseEngine(data['engine'])
        return cls(**data)


class MetricsCollector:
    """
    Collects and manages database metrics.
    
    Provides functionality to collect, store, and analyze various
    database performance metrics across different engines.
    """
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self._metrics_storage: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self._metric_definitions: Dict[str, Dict[str, Any]] = {}
        self._collection_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        
        # Query duration tracking
        self._query_durations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Connection tracking
        self._connection_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Custom metric collectors
        self._custom_collectors: Dict[str, Callable] = {}
    
    async def start_collection(self, database_adapters: Dict[str, DatabaseAdapter]) -> None:
        """
        Start metrics collection for all databases.
        
        Args:
            database_adapters: Dictionary of database adapters
        """
        if self._running:
            return
        
        self._running = True
        
        # Start collection tasks for each database
        for db_name, adapter in database_adapters.items():
            task = asyncio.create_task(self._collection_loop(db_name, adapter))
            self._collection_tasks[db_name] = task
    
    async def stop_collection(self) -> None:
        """Stop metrics collection."""
        self._running = False
        
        # Cancel all collection tasks
        for task in self._collection_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._collection_tasks.clear()
    
    async def _collection_loop(self, database_name: str, adapter: DatabaseAdapter) -> None:
        """Main collection loop for a database."""
        while self._running:
            try:
                await asyncio.sleep(self.config.metrics_collection_interval)
                
                if not self._running:
                    break
                
                # Collect metrics
                metrics = await self._collect_database_metrics(database_name, adapter)
                
                # Store metrics
                await self._store_metrics(database_name, metrics)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue collection
                print(f"Error collecting metrics for {database_name}: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _collect_database_metrics(self, database_name: str, adapter: DatabaseAdapter) -> DatabaseMetrics:
        """Collect metrics for a specific database."""
        engine = adapter.config.engine
        timestamp = datetime.now(timezone.utc)
        
        # Initialize metrics
        metrics = DatabaseMetrics(
            database_name=database_name,
            engine=engine,
            timestamp=timestamp
        )
        
        try:
            # Collect connection metrics
            await self._collect_connection_metrics(metrics, adapter)
            
            # Collect query metrics
            await self._collect_query_metrics(metrics, database_name)
            
            # Collect engine-specific metrics
            await self._collect_engine_specific_metrics(metrics, adapter)
            
            # Collect custom metrics
            await self._collect_custom_metrics(metrics, adapter)
            
        except Exception as e:
            raise MonitoringError(f"Failed to collect metrics for {database_name}: {e}")
        
        return metrics
    
    async def _collect_connection_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect connection-related metrics."""
        try:
            # Get connection pool information if available
            if hasattr(adapter, 'get_pool_stats'):
                pool_stats = await adapter.get_pool_stats()
                metrics.total_connections = pool_stats.get('total_connections', 0)
                metrics.active_connections = pool_stats.get('active_connections', 0)
                metrics.idle_connections = pool_stats.get('idle_connections', 0)
                metrics.failed_connections = pool_stats.get('failed_connections', 0)
                
                # Calculate utilization
                if metrics.total_connections > 0:
                    metrics.connection_pool_utilization = metrics.active_connections / metrics.total_connections
            
            # Update connection tracking
            db_name = metrics.database_name
            self._connection_metrics[db_name].update({
                'total_connections': metrics.total_connections,
                'active_connections': metrics.active_connections,
                'utilization': metrics.connection_pool_utilization,
                'last_updated': metrics.timestamp
            })
            
        except Exception as e:
            # Connection metrics are optional, don't fail collection
            pass
    
    async def _collect_query_metrics(self, metrics: DatabaseMetrics, database_name: str) -> None:
        """Collect query performance metrics."""
        try:
            # Get query durations for this database
            durations = list(self._query_durations[database_name])
            
            if durations:
                metrics.avg_query_duration = statistics.mean(durations)
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                n = len(sorted_durations)
                
                if n >= 20:  # Need sufficient data for percentiles
                    p95_index = int(0.95 * n)
                    p99_index = int(0.99 * n)
                    
                    metrics.p95_query_duration = sorted_durations[p95_index]
                    metrics.p99_query_duration = sorted_durations[p99_index]
                
                # Count slow queries
                slow_threshold = self.config.slow_query_threshold
                metrics.slow_queries = sum(1 for d in durations if d > slow_threshold)
                
                # Calculate rates
                metrics.total_queries = len(durations)
                if metrics.total_queries > 0:
                    metrics.error_rate = metrics.failed_queries / metrics.total_queries
            
        except Exception as e:
            # Query metrics are important but shouldn't fail collection
            pass
    
    async def _collect_engine_specific_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect engine-specific metrics."""
        engine = adapter.config.engine
        
        try:
            if engine == DatabaseEngine.POSTGRESQL:
                await self._collect_postgresql_metrics(metrics, adapter)
            elif engine == DatabaseEngine.MYSQL:
                await self._collect_mysql_metrics(metrics, adapter)
            elif engine == DatabaseEngine.MONGODB:
                await self._collect_mongodb_metrics(metrics, adapter)
            elif engine == DatabaseEngine.SQLITE:
                await self._collect_sqlite_metrics(metrics, adapter)
                
        except Exception as e:
            # Engine-specific metrics are optional
            pass
    
    async def _collect_postgresql_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect PostgreSQL-specific metrics."""
        try:
            # Database statistics
            db_stats = await adapter.fetch_one(
                None,
                "SELECT * FROM pg_stat_database WHERE datname = current_database()"
            )
            
            if db_stats:
                metrics.custom_metrics.update({
                    'pg_connections': db_stats.get('numbackends', 0),
                    'pg_transactions': db_stats.get('xact_commit', 0) + db_stats.get('xact_rollback', 0),
                    'pg_blocks_read': db_stats.get('blks_read', 0),
                    'pg_blocks_hit': db_stats.get('blks_hit', 0)
                })
            
            # Lock information
            locks = await adapter.fetch_all(
                None,
                "SELECT mode, count(*) as count FROM pg_locks GROUP BY mode"
            )
            
            if locks:
                lock_counts = {lock['mode']: lock['count'] for lock in locks}
                metrics.custom_metrics['pg_locks'] = lock_counts
                
        except Exception:
            pass
    
    async def _collect_mysql_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect MySQL-specific metrics."""
        try:
            # Global status
            status = await adapter.fetch_all(None, "SHOW GLOBAL STATUS")
            
            if status:
                status_dict = {row['Variable_name']: row['Value'] for row in status}
                
                metrics.custom_metrics.update({
                    'mysql_connections': int(status_dict.get('Threads_connected', 0)),
                    'mysql_queries': int(status_dict.get('Queries', 0)),
                    'mysql_slow_queries': int(status_dict.get('Slow_queries', 0)),
                    'mysql_innodb_buffer_pool_reads': int(status_dict.get('Innodb_buffer_pool_reads', 0))
                })
                
        except Exception:
            pass
    
    async def _collect_mongodb_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect MongoDB-specific metrics."""
        try:
            # Server status
            server_status = await adapter.execute_query(
                None,
                "db.runCommand",
                parameters={"serverStatus": 1}
            )
            
            if server_status and server_status.data:
                status = server_status.data
                
                metrics.custom_metrics.update({
                    'mongodb_connections': status.get('connections', {}).get('current', 0),
                    'mongodb_operations': sum(status.get('opcounters', {}).values()),
                    'mongodb_memory': status.get('mem', {}).get('resident', 0)
                })
                
        except Exception:
            pass
    
    async def _collect_sqlite_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect SQLite-specific metrics."""
        try:
            # Database size
            size_result = await adapter.fetch_one(None, "PRAGMA page_count")
            page_size_result = await adapter.fetch_one(None, "PRAGMA page_size")
            
            if size_result and page_size_result:
                db_size = size_result['page_count'] * page_size_result['page_size']
                metrics.custom_metrics['sqlite_db_size'] = db_size
                
        except Exception:
            pass
    
    async def _collect_custom_metrics(self, metrics: DatabaseMetrics, adapter: DatabaseAdapter) -> None:
        """Collect custom metrics using registered collectors."""
        for metric_name, collector in self._custom_collectors.items():
            try:
                value = await collector(adapter)
                metrics.custom_metrics[metric_name] = value
            except Exception:
                # Custom metrics shouldn't fail collection
                pass
    
    async def _store_metrics(self, database_name: str, metrics: DatabaseMetrics) -> None:
        """Store collected metrics."""
        if self.config.metrics_storage == MetricsStorage.MEMORY:
            await self._store_metrics_memory(database_name, metrics)
        elif self.config.metrics_storage == MetricsStorage.REDIS:
            await self._store_metrics_redis(database_name, metrics)
        # Add other storage backends as needed
    
    async def _store_metrics_memory(self, database_name: str, metrics: DatabaseMetrics) -> None:
        """Store metrics in memory."""
        # Store in time-series format
        storage = self._metrics_storage[database_name]
        
        # Store each metric as a time series
        metric_dict = metrics.to_dict()
        
        for key, value in metric_dict.items():
            if key not in ['database_name', 'engine', 'timestamp', 'custom_metrics']:
                metric_value = MetricValue(
                    value=value,
                    timestamp=metrics.timestamp,
                    labels={'database': database_name, 'engine': metrics.engine.value}
                )
                
                # Add to deque with max length for memory management
                storage[key].append(metric_value)
                if len(storage[key]) > 10000:  # Keep last 10k values
                    storage[key].popleft()
        
        # Store custom metrics
        for key, value in metrics.custom_metrics.items():
            metric_value = MetricValue(
                value=value,
                timestamp=metrics.timestamp,
                labels={'database': database_name, 'engine': metrics.engine.value, 'type': 'custom'}
            )
            
            storage[f"custom_{key}"].append(metric_value)
            if len(storage[f"custom_{key}"]) > 1000:
                storage[f"custom_{key}"].popleft()
    
    async def _store_metrics_redis(self, database_name: str, metrics: DatabaseMetrics) -> None:
        """Store metrics in Redis (placeholder for Redis implementation)."""
        # This would implement Redis storage
        pass
    
    def record_query_duration(self, database_name: str, duration: float) -> None:
        """
        Record query execution duration.
        
        Args:
            database_name: Name of the database
            duration: Query duration in seconds
        """
        self._query_durations[database_name].append(duration)
    
    def record_query_error(self, database_name: str, error: Exception) -> None:
        """
        Record query error.
        
        Args:
            database_name: Name of the database
            error: Query error
        """
        # Update error metrics
        if database_name in self._connection_metrics:
            metrics = self._connection_metrics[database_name]
            metrics['failed_queries'] = metrics.get('failed_queries', 0) + 1
            metrics['last_error'] = str(error)
            metrics['last_error_time'] = datetime.now(timezone.utc)
    
    def get_metrics(
        self,
        database_name: str,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricValue]:
        """
        Get stored metrics.
        
        Args:
            database_name: Name of the database
            metric_name: Specific metric name (all if None)
            start_time: Start time for filtering
            end_time: End time for filtering
            
        Returns:
            List of metric values
        """
        if database_name not in self._metrics_storage:
            return []
        
        storage = self._metrics_storage[database_name]
        
        if metric_name:
            metrics = list(storage.get(metric_name, []))
        else:
            # Get all metrics
            metrics = []
            for metric_values in storage.values():
                metrics.extend(metric_values)
        
        # Filter by time range if specified
        if start_time or end_time:
            filtered_metrics = []
            for metric in metrics:
                if start_time and metric.timestamp < start_time:
                    continue
                if end_time and metric.timestamp > end_time:
                    continue
                filtered_metrics.append(metric)
            metrics = filtered_metrics
        
        return sorted(metrics, key=lambda m: m.timestamp)
    
    def get_latest_metrics(self, database_name: str) -> Optional[DatabaseMetrics]:
        """
        Get latest metrics for a database.
        
        Args:
            database_name: Name of the database
            
        Returns:
            Latest DatabaseMetrics or None
        """
        if database_name not in self._metrics_storage:
            return None
        
        storage = self._metrics_storage[database_name]
        
        # Find the latest timestamp
        latest_timestamp = None
        latest_values = {}
        
        for metric_name, values in storage.items():
            if values:
                latest_value = values[-1]
                if latest_timestamp is None or latest_value.timestamp > latest_timestamp:
                    latest_timestamp = latest_value.timestamp
                
                latest_values[metric_name] = latest_value.value
        
        if not latest_values or latest_timestamp is None:
            return None
        
        # Reconstruct DatabaseMetrics
        # This is a simplified reconstruction - in practice, you'd want to store the full metrics object
        return DatabaseMetrics(
            database_name=database_name,
            engine=DatabaseEngine.POSTGRESQL,  # Would need to store this
            timestamp=latest_timestamp,
            **{k: v for k, v in latest_values.items() if not k.startswith('custom_')}
        )
    
    def register_custom_collector(self, metric_name: str, collector: Callable) -> None:
        """
        Register a custom metric collector.
        
        Args:
            metric_name: Name of the custom metric
            collector: Async function that takes adapter and returns metric value
        """
        self._custom_collectors[metric_name] = collector
    
    def get_summary_statistics(
        self,
        database_name: str,
        metric_name: str,
        period: timedelta = timedelta(hours=1)
    ) -> Dict[str, float]:
        """
        Get summary statistics for a metric over a time period.
        
        Args:
            database_name: Name of the database
            metric_name: Name of the metric
            period: Time period for statistics
            
        Returns:
            Dictionary with statistics (min, max, avg, p95, p99)
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - period
        
        metrics = self.get_metrics(database_name, metric_name, start_time, end_time)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values),
            'count': len(values)
        }
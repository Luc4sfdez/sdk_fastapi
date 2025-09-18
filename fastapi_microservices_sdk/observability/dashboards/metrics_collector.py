"""
Metrics Collector - Real-time metrics collection for dashboards

This module provides real-time metrics collection functionality
for dashboard components, including data aggregation and caching.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str]


@dataclass
class MetricSeries:
    """Time series of metric points."""
    name: str
    points: deque
    labels: Dict[str, str]
    
    def __post_init__(self):
        if not isinstance(self.points, deque):
            self.points = deque(self.points, maxlen=1000)  # Keep last 1000 points
    
    def add_point(self, value: Union[int, float], timestamp: Optional[datetime] = None) -> None:
        """Add a point to the series."""
        point = MetricPoint(
            timestamp=timestamp or datetime.utcnow(),
            value=value,
            labels=self.labels
        )
        self.points.append(point)
    
    def get_latest_value(self) -> Optional[Union[int, float]]:
        """Get the latest value."""
        if self.points:
            return self.points[-1].value
        return None
    
    def get_points_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricPoint]:
        """Get points within time range."""
        return [
            point for point in self.points
            if start_time <= point.timestamp <= end_time
        ]
    
    def aggregate(
        self,
        aggregation: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Optional[float]:
        """Aggregate points with specified function."""
        points = list(self.points)
        
        if start_time or end_time:
            start_time = start_time or datetime.min
            end_time = end_time or datetime.max
            points = [
                point for point in points
                if start_time <= point.timestamp <= end_time
            ]
        
        if not points:
            return None
        
        values = [point.value for point in points]
        
        if aggregation == "sum":
            return sum(values)
        elif aggregation == "avg":
            return sum(values) / len(values)
        elif aggregation == "min":
            return min(values)
        elif aggregation == "max":
            return max(values)
        elif aggregation == "count":
            return len(values)
        elif aggregation == "last":
            return values[-1]
        elif aggregation == "first":
            return values[0]
        else:
            return values[-1]  # Default to last


class MetricsCollector:
    """
    Real-time metrics collector for dashboard components.
    
    Provides:
    - Metric collection and storage
    - Real-time data aggregation
    - Metric querying and filtering
    - Data retention management
    """
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, MetricSeries] = {}
        self.collectors: Dict[str, Callable] = {}
        self.collection_intervals: Dict[str, int] = {}
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        
        logger.info("Metrics collector initialized")
    
    async def initialize(self) -> None:
        """Initialize metrics collector."""
        self.is_running = True
        
        # Start collection tasks
        for metric_name in self.collectors:
            await self._start_collection_task(metric_name)
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
        
        logger.info("Metrics collector started")
    
    async def shutdown(self) -> None:
        """Shutdown metrics collector."""
        self.is_running = False
        
        # Cancel all collection tasks
        for task in self.collection_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.collection_tasks:
            await asyncio.gather(*self.collection_tasks.values(), return_exceptions=True)
        
        logger.info("Metrics collector stopped")
    
    def register_metric_collector(
        self,
        metric_name: str,
        collector_func: Callable,
        interval_seconds: int = 30,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Register a metric collector function.
        
        Args:
            metric_name: Name of the metric
            collector_func: Function that returns metric value
            interval_seconds: Collection interval in seconds
            labels: Default labels for the metric
        """
        self.collectors[metric_name] = collector_func
        self.collection_intervals[metric_name] = interval_seconds
        
        # Initialize metric series
        self.metrics[metric_name] = MetricSeries(
            name=metric_name,
            points=deque(maxlen=1000),
            labels=labels or {}
        )
        
        # Start collection task if running
        if self.is_running:
            asyncio.create_task(self._start_collection_task(metric_name))
        
        logger.info(f"Registered metric collector: {metric_name}")
    
    def add_metric_point(
        self,
        metric_name: str,
        value: Union[int, float],
        timestamp: Optional[datetime] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Add a metric point manually.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            timestamp: Point timestamp (defaults to now)
            labels: Point labels
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = MetricSeries(
                name=metric_name,
                points=deque(maxlen=1000),
                labels=labels or {}
            )
        
        self.metrics[metric_name].add_point(value, timestamp)
    
    def get_metric_value(
        self,
        metric_name: str,
        aggregation: str = "last"
    ) -> Optional[float]:
        """
        Get current metric value.
        
        Args:
            metric_name: Name of the metric
            aggregation: Aggregation function
            
        Returns:
            Current metric value
        """
        if metric_name not in self.metrics:
            return None
        
        return self.metrics[metric_name].aggregate(aggregation)
    
    def get_metric_series(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_points: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get metric time series data.
        
        Args:
            metric_name: Name of the metric
            start_time: Start time for data
            end_time: End time for data
            max_points: Maximum number of points to return
            
        Returns:
            List of metric points
        """
        if metric_name not in self.metrics:
            return []
        
        series = self.metrics[metric_name]
        points = list(series.points)
        
        # Filter by time range
        if start_time or end_time:
            start_time = start_time or datetime.min
            end_time = end_time or datetime.max
            points = [
                point for point in points
                if start_time <= point.timestamp <= end_time
            ]
        
        # Limit number of points
        if len(points) > max_points:
            # Sample points evenly
            step = len(points) // max_points
            points = points[::step]
        
        return [
            {
                "timestamp": point.timestamp.isoformat(),
                "value": point.value,
                "labels": point.labels
            }
            for point in points
        ]
    
    def get_multiple_metrics(
        self,
        metric_names: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        aggregation: str = "last"
    ) -> Dict[str, Any]:
        """
        Get multiple metrics data.
        
        Args:
            metric_names: List of metric names
            start_time: Start time for data
            end_time: End time for data
            aggregation: Aggregation function
            
        Returns:
            Dictionary of metric data
        """
        result = {}
        
        for metric_name in metric_names:
            if metric_name in self.metrics:
                series = self.metrics[metric_name]
                
                # Get aggregated value
                value = series.aggregate(aggregation, start_time, end_time)
                
                # Get time series
                time_series = self.get_metric_series(
                    metric_name, start_time, end_time
                )
                
                result[metric_name] = {
                    "current_value": value,
                    "time_series": time_series,
                    "labels": series.labels
                }
        
        return result
    
    def query_metrics(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Query metrics with simple query language.
        
        Args:
            query: Metric query (e.g., "cpu_usage_percent")
            start_time: Start time for data
            end_time: End time for data
            
        Returns:
            Query results
        """
        # Simple query parsing - in real implementation, this would be more sophisticated
        if query in self.metrics:
            return {
                query: self.get_metric_series(query, start_time, end_time)
            }
        
        # Pattern matching
        matching_metrics = [
            name for name in self.metrics.keys()
            if query in name
        ]
        
        result = {}
        for metric_name in matching_metrics:
            result[metric_name] = self.get_metric_series(
                metric_name, start_time, end_time
            )
        
        return result
    
    def get_metric_statistics(
        self,
        metric_name: str,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        Get metric statistics for specified time period.
        
        Args:
            metric_name: Name of the metric
            hours: Number of hours to analyze
            
        Returns:
            Metric statistics
        """
        if metric_name not in self.metrics:
            return {}
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        series = self.metrics[metric_name]
        
        return {
            "metric_name": metric_name,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "statistics": {
                "min": series.aggregate("min", start_time, end_time),
                "max": series.aggregate("max", start_time, end_time),
                "avg": series.aggregate("avg", start_time, end_time),
                "sum": series.aggregate("sum", start_time, end_time),
                "count": series.aggregate("count", start_time, end_time),
                "latest": series.aggregate("last", start_time, end_time)
            },
            "labels": series.labels
        }
    
    async def _start_collection_task(self, metric_name: str) -> None:
        """Start collection task for a metric."""
        if metric_name in self.collection_tasks:
            # Cancel existing task
            self.collection_tasks[metric_name].cancel()
        
        # Start new task
        task = asyncio.create_task(
            self._collection_loop(metric_name)
        )
        self.collection_tasks[metric_name] = task
    
    async def _collection_loop(self, metric_name: str) -> None:
        """Collection loop for a specific metric."""
        collector_func = self.collectors[metric_name]
        interval = self.collection_intervals[metric_name]
        
        while self.is_running:
            try:
                # Collect metric value
                if asyncio.iscoroutinefunction(collector_func):
                    value = await collector_func()
                else:
                    value = collector_func()
                
                # Add point to series
                if value is not None:
                    self.add_metric_point(metric_name, value)
                
                # Wait for next collection
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metric {metric_name}: {e}")
                await asyncio.sleep(interval)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self.is_running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old metric data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for metric_name, series in self.metrics.items():
            original_count = len(series.points)
            
            # Remove old points
            while series.points and series.points[0].timestamp < cutoff_time:
                series.points.popleft()
            
            cleaned_count = original_count - len(series.points)
            if cleaned_count > 0:
                logger.debug(f"Cleaned {cleaned_count} old points from {metric_name}")
    
    def get_available_metrics(self) -> List[Dict[str, Any]]:
        """Get list of available metrics."""
        return [
            {
                "name": name,
                "labels": series.labels,
                "point_count": len(series.points),
                "latest_value": series.get_latest_value(),
                "has_collector": name in self.collectors
            }
            for name, series in self.metrics.items()
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status."""
        return {
            "running": self.is_running,
            "metrics_count": len(self.metrics),
            "collectors_count": len(self.collectors),
            "active_tasks": len([
                task for task in self.collection_tasks.values()
                if not task.done()
            ]),
            "retention_hours": self.retention_hours,
            "total_points": sum(len(series.points) for series in self.metrics.values())
        }


class SystemMetricsCollector:
    """System metrics collector with common system metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._setup_system_collectors()
    
    def _setup_system_collectors(self) -> None:
        """Setup common system metric collectors."""
        
        # CPU Usage
        self.metrics_collector.register_metric_collector(
            "system_cpu_usage_percent",
            self._collect_cpu_usage,
            interval_seconds=30,
            labels={"type": "system", "unit": "percent"}
        )
        
        # Memory Usage
        self.metrics_collector.register_metric_collector(
            "system_memory_usage_percent",
            self._collect_memory_usage,
            interval_seconds=30,
            labels={"type": "system", "unit": "percent"}
        )
        
        # Disk Usage
        self.metrics_collector.register_metric_collector(
            "system_disk_usage_percent",
            self._collect_disk_usage,
            interval_seconds=60,
            labels={"type": "system", "unit": "percent"}
        )
        
        # Network I/O
        self.metrics_collector.register_metric_collector(
            "system_network_bytes_sent",
            self._collect_network_sent,
            interval_seconds=30,
            labels={"type": "system", "unit": "bytes"}
        )
        
        self.metrics_collector.register_metric_collector(
            "system_network_bytes_received",
            self._collect_network_received,
            interval_seconds=30,
            labels={"type": "system", "unit": "bytes"}
        )
    
    def _collect_cpu_usage(self) -> float:
        """Collect CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except ImportError:
            # Fallback to load average
            try:
                import os
                load_avg = os.getloadavg()[0]
                cpu_count = os.cpu_count() or 1
                return min(100.0, (load_avg / cpu_count) * 100)
            except:
                return 0.0
    
    def _collect_memory_usage(self) -> float:
        """Collect memory usage percentage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent
        except ImportError:
            return 0.0
    
    def _collect_disk_usage(self) -> float:
        """Collect disk usage percentage."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100
        except ImportError:
            return 0.0
    
    def _collect_network_sent(self) -> float:
        """Collect network bytes sent."""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return float(net_io.bytes_sent)
        except ImportError:
            return 0.0
    
    def _collect_network_received(self) -> float:
        """Collect network bytes received."""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return float(net_io.bytes_recv)
        except ImportError:
            return 0.0
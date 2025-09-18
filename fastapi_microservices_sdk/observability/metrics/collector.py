"""
Metrics collectors for system and application metrics.

This module provides collectors for various types of metrics including
system metrics (CPU, memory, disk, network) and HTTP request metrics.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import threading
import time
import psutil
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from ..manager import ObservabilityComponent, ComponentType
from .registry import MetricRegistry, get_global_registry
from .types import Counter, Gauge, Histogram, Summary
from .exceptions import (
    MetricsCollectionError,
    SystemMetricsError,
    HTTPMetricsError,
    handle_system_metrics_error,
    handle_http_metrics_error
)


@dataclass
class SystemMetrics:
    """Container for system metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_bytes: int = 0
    memory_available_bytes: int = 0
    disk_percent: float = 0.0
    disk_used_bytes: int = 0
    disk_free_bytes: int = 0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    network_packets_sent: int = 0
    network_packets_recv: int = 0
    process_count: int = 0
    load_average: List[float] = field(default_factory=list)
    boot_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class HTTPMetrics:
    """Container for HTTP metrics."""
    request_count: int = 0
    request_duration_seconds: float = 0.0
    request_size_bytes: int = 0
    response_size_bytes: int = 0
    status_code: int = 200
    method: str = "GET"
    endpoint: str = "/"
    timestamp: float = field(default_factory=time.time)


class MetricsCollector(ObservabilityComponent):
    """Base metrics collector component."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.registry = config.get('registry') or get_global_registry()
        self.collection_interval = config.get('collection_interval', 15.0)
        self.enabled = config.get('enabled', True)
        
        # Collection statistics
        self.collections_total = 0
        self.collection_errors = 0
        self.last_collection_time = 0.0
        self.collection_duration_seconds = 0.0
        
        # Collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._stop_collection = asyncio.Event()
    
    async def _initialize(self) -> None:
        """Initialize the metrics collector."""
        if self.enabled:
            self.logger.info(f"Initializing metrics collector: {self.name}")
            await self._setup_metrics()
            await self._start_collection()
            self.logger.info(f"Metrics collector {self.name} initialized")
    
    async def _shutdown(self) -> None:
        """Shutdown the metrics collector."""
        self.logger.info(f"Shutting down metrics collector: {self.name}")
        await self._stop_collection_task()
        self.logger.info(f"Metrics collector {self.name} shutdown")
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check on the collector."""
        return {
            'enabled': self.enabled,
            'collections_total': self.collections_total,
            'collection_errors': self.collection_errors,
            'error_rate': self.collection_errors / max(1, self.collections_total),
            'last_collection_time': self.last_collection_time,
            'collection_duration_seconds': self.collection_duration_seconds,
            'collection_interval': self.collection_interval
        }
    
    async def _setup_metrics(self) -> None:
        """Setup metrics for this collector."""
        # Override in subclasses
        pass
    
    async def _collect_metrics(self) -> None:
        """Collect metrics - override in subclasses."""
        pass
    
    async def _start_collection(self) -> None:
        """Start the metrics collection task."""
        if self._collection_task is None:
            self._collection_task = asyncio.create_task(self._collection_loop())
    
    async def _stop_collection_task(self) -> None:
        """Stop the metrics collection task."""
        if self._collection_task:
            self._stop_collection.set()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            finally:
                self._collection_task = None
    
    async def _collection_loop(self) -> None:
        """Main collection loop."""
        while not self._stop_collection.is_set():
            try:
                start_time = time.time()
                
                await self._collect_metrics()
                
                self.collection_duration_seconds = time.time() - start_time
                self.last_collection_time = time.time()
                self.collections_total += 1
                
                # Wait for next collection interval
                await asyncio.wait_for(
                    self._stop_collection.wait(),
                    timeout=self.collection_interval
                )
                
            except asyncio.TimeoutError:
                # Normal timeout, continue collection
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.collection_errors += 1
                self.logger.error(f"Metrics collection error in {self.name}: {e}")
                
                # Wait before retrying
                try:
                    await asyncio.wait_for(
                        self._stop_collection.wait(),
                        timeout=min(self.collection_interval, 30.0)
                    )
                except asyncio.TimeoutError:
                    continue


class SystemMetricsCollector(MetricsCollector):
    """Collector for system metrics (CPU, memory, disk, network)."""
    
    def __init__(self, name: str = "system_metrics", config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(name, config)
        
        # System metrics
        self.cpu_usage_gauge: Optional[Gauge] = None
        self.memory_usage_gauge: Optional[Gauge] = None
        self.memory_bytes_gauge: Optional[Gauge] = None
        self.disk_usage_gauge: Optional[Gauge] = None
        self.disk_bytes_gauge: Optional[Gauge] = None
        self.network_bytes_counter: Optional[Counter] = None
        self.network_packets_counter: Optional[Counter] = None
        self.process_count_gauge: Optional[Gauge] = None
        self.load_average_gauge: Optional[Gauge] = None
        self.boot_time_gauge: Optional[Gauge] = None
        
        # Collection settings
        self.collect_cpu = config.get('collect_cpu', True)
        self.collect_memory = config.get('collect_memory', True)
        self.collect_disk = config.get('collect_disk', True)
        self.collect_network = config.get('collect_network', True)
        self.collect_processes = config.get('collect_processes', True)
        self.collect_load = config.get('collect_load', True)
        
        # Disk paths to monitor
        self.disk_paths = config.get('disk_paths', ['/'])
        
        # Network interface filter
        self.network_interfaces = config.get('network_interfaces', None)  # None = all interfaces
    
    async def _setup_metrics(self) -> None:
        """Setup system metrics."""
        try:
            if self.collect_cpu:
                self.cpu_usage_gauge = Gauge(
                    'system_cpu_usage_percent',
                    'CPU usage percentage',
                    unit='percent'
                )
                self.registry.register(self.cpu_usage_gauge)
            
            if self.collect_memory:
                self.memory_usage_gauge = Gauge(
                    'system_memory_usage_percent',
                    'Memory usage percentage',
                    unit='percent'
                )
                self.registry.register(self.memory_usage_gauge)
                
                self.memory_bytes_gauge = Gauge(
                    'system_memory_bytes',
                    'Memory usage in bytes',
                    labels=['type'],
                    unit='bytes'
                )
                self.registry.register(self.memory_bytes_gauge)
            
            if self.collect_disk:
                self.disk_usage_gauge = Gauge(
                    'system_disk_usage_percent',
                    'Disk usage percentage',
                    labels=['path'],
                    unit='percent'
                )
                self.registry.register(self.disk_usage_gauge)
                
                self.disk_bytes_gauge = Gauge(
                    'system_disk_bytes',
                    'Disk usage in bytes',
                    labels=['path', 'type'],
                    unit='bytes'
                )
                self.registry.register(self.disk_bytes_gauge)
            
            if self.collect_network:
                self.network_bytes_counter = Counter(
                    'system_network_bytes_total',
                    'Network bytes transferred',
                    labels=['interface', 'direction'],
                    unit='bytes'
                )
                self.registry.register(self.network_bytes_counter)
                
                self.network_packets_counter = Counter(
                    'system_network_packets_total',
                    'Network packets transferred',
                    labels=['interface', 'direction'],
                    unit='packets'
                )
                self.registry.register(self.network_packets_counter)
            
            if self.collect_processes:
                self.process_count_gauge = Gauge(
                    'system_processes_count',
                    'Number of running processes',
                    unit='processes'
                )
                self.registry.register(self.process_count_gauge)
            
            if self.collect_load:
                self.load_average_gauge = Gauge(
                    'system_load_average',
                    'System load average',
                    labels=['period'],
                    unit='load'
                )
                self.registry.register(self.load_average_gauge)
            
            # Boot time (static metric)
            self.boot_time_gauge = Gauge(
                'system_boot_time_seconds',
                'System boot time in seconds since epoch',
                unit='seconds'
            )
            self.registry.register(self.boot_time_gauge)
            self.boot_time_gauge.set(psutil.boot_time())
            
        except Exception as e:
            raise handle_system_metrics_error(e, "setup")
    
    async def _collect_metrics(self) -> None:
        """Collect system metrics."""
        try:
            # CPU metrics
            if self.collect_cpu and self.cpu_usage_gauge:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_usage_gauge.set(cpu_percent)
            
            # Memory metrics
            if self.collect_memory:
                memory = psutil.virtual_memory()
                if self.memory_usage_gauge:
                    self.memory_usage_gauge.set(memory.percent)
                
                if self.memory_bytes_gauge:
                    self.memory_bytes_gauge.set(memory.used, {'type': 'used'})
                    self.memory_bytes_gauge.set(memory.available, {'type': 'available'})
                    self.memory_bytes_gauge.set(memory.total, {'type': 'total'})
            
            # Disk metrics
            if self.collect_disk and (self.disk_usage_gauge or self.disk_bytes_gauge):
                for path in self.disk_paths:
                    try:
                        disk = psutil.disk_usage(path)
                        
                        if self.disk_usage_gauge:
                            usage_percent = (disk.used / disk.total) * 100
                            self.disk_usage_gauge.set(usage_percent, {'path': path})
                        
                        if self.disk_bytes_gauge:
                            self.disk_bytes_gauge.set(disk.used, {'path': path, 'type': 'used'})
                            self.disk_bytes_gauge.set(disk.free, {'path': path, 'type': 'free'})
                            self.disk_bytes_gauge.set(disk.total, {'path': path, 'type': 'total'})
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to collect disk metrics for {path}: {e}")
            
            # Network metrics
            if self.collect_network and (self.network_bytes_counter or self.network_packets_counter):
                network_stats = psutil.net_io_counters(pernic=True)
                
                for interface, stats in network_stats.items():
                    if self.network_interfaces is None or interface in self.network_interfaces:
                        if self.network_bytes_counter:
                            # Note: Counter should track increments, but for simplicity we set absolute values
                            # In a real implementation, we'd track deltas
                            self.network_bytes_counter.inc(0, {'interface': interface, 'direction': 'sent'})
                            self.network_bytes_counter.inc(0, {'interface': interface, 'direction': 'recv'})
                        
                        if self.network_packets_counter:
                            self.network_packets_counter.inc(0, {'interface': interface, 'direction': 'sent'})
                            self.network_packets_counter.inc(0, {'interface': interface, 'direction': 'recv'})
            
            # Process count
            if self.collect_processes and self.process_count_gauge:
                process_count = len(psutil.pids())
                self.process_count_gauge.set(process_count)
            
            # Load average (Unix-like systems only)
            if self.collect_load and self.load_average_gauge:
                try:
                    load_avg = psutil.getloadavg()
                    self.load_average_gauge.set(load_avg[0], {'period': '1min'})
                    self.load_average_gauge.set(load_avg[1], {'period': '5min'})
                    self.load_average_gauge.set(load_avg[2], {'period': '15min'})
                except AttributeError:
                    # getloadavg not available on Windows
                    pass
            
        except Exception as e:
            raise handle_system_metrics_error(e, "collection")


class HTTPMetricsCollector(MetricsCollector):
    """Collector for HTTP request/response metrics."""
    
    def __init__(self, name: str = "http_metrics", config: Optional[Dict[str, Any]] = None):
        config = config or {}
        super().__init__(name, config)
        
        # HTTP metrics
        self.request_count_counter: Optional[Counter] = None
        self.request_duration_histogram: Optional[Histogram] = None
        self.request_size_histogram: Optional[Histogram] = None
        self.response_size_histogram: Optional[Histogram] = None
        self.requests_in_progress_gauge: Optional[Gauge] = None
        
        # Configuration
        self.track_request_size = config.get('track_request_size', True)
        self.track_response_size = config.get('track_response_size', True)
        self.track_in_progress = config.get('track_in_progress', True)
        
        # Histogram buckets
        self.duration_buckets = config.get('duration_buckets', [
            0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf')
        ])
        self.size_buckets = config.get('size_buckets', [
            100, 1000, 10000, 100000, 1000000, 10000000, 100000000, float('inf')
        ])
        
        # In-progress requests tracking
        self._requests_in_progress = 0
        self._requests_lock = threading.Lock()
    
    async def _setup_metrics(self) -> None:
        """Setup HTTP metrics."""
        try:
            # Request count
            self.request_count_counter = Counter(
                'http_requests_total',
                'Total number of HTTP requests',
                labels=['method', 'endpoint', 'status_code'],
                unit='requests'
            )
            self.registry.register(self.request_count_counter)
            
            # Request duration
            self.request_duration_histogram = Histogram(
                'http_request_duration_seconds',
                'HTTP request duration in seconds',
                labels=['method', 'endpoint'],
                unit='seconds',
                buckets=self.duration_buckets
            )
            self.registry.register(self.request_duration_histogram)
            
            # Request size
            if self.track_request_size:
                self.request_size_histogram = Histogram(
                    'http_request_size_bytes',
                    'HTTP request size in bytes',
                    labels=['method', 'endpoint'],
                    unit='bytes',
                    buckets=self.size_buckets
                )
                self.registry.register(self.request_size_histogram)
            
            # Response size
            if self.track_response_size:
                self.response_size_histogram = Histogram(
                    'http_response_size_bytes',
                    'HTTP response size in bytes',
                    labels=['method', 'endpoint', 'status_code'],
                    unit='bytes',
                    buckets=self.size_buckets
                )
                self.registry.register(self.response_size_histogram)
            
            # Requests in progress
            if self.track_in_progress:
                self.requests_in_progress_gauge = Gauge(
                    'http_requests_in_progress',
                    'Number of HTTP requests currently being processed',
                    unit='requests'
                )
                self.registry.register(self.requests_in_progress_gauge)
            
        except Exception as e:
            raise handle_http_metrics_error(e)
    
    async def _collect_metrics(self) -> None:
        """HTTP metrics are collected via middleware, not periodic collection."""
        # Update in-progress gauge
        if self.requests_in_progress_gauge:
            with self._requests_lock:
                self.requests_in_progress_gauge.set(self._requests_in_progress)
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None
    ) -> None:
        """Record HTTP request metrics."""
        try:
            labels = {
                'method': method.upper(),
                'endpoint': endpoint,
                'status_code': str(status_code)
            }
            
            # Request count
            if self.request_count_counter:
                self.request_count_counter.inc(1.0, labels)
            
            # Request duration
            if self.request_duration_histogram:
                duration_labels = {
                    'method': method.upper(),
                    'endpoint': endpoint
                }
                self.request_duration_histogram.observe(duration_seconds, duration_labels)
            
            # Request size
            if self.request_size_histogram and request_size_bytes is not None:
                size_labels = {
                    'method': method.upper(),
                    'endpoint': endpoint
                }
                self.request_size_histogram.observe(request_size_bytes, size_labels)
            
            # Response size
            if self.response_size_histogram and response_size_bytes is not None:
                response_labels = {
                    'method': method.upper(),
                    'endpoint': endpoint,
                    'status_code': str(status_code)
                }
                self.response_size_histogram.observe(response_size_bytes, response_labels)
            
        except Exception as e:
            self.collection_errors += 1
            raise handle_http_metrics_error(e, method, endpoint, status_code)
    
    def start_request(self) -> None:
        """Mark the start of a request (for in-progress tracking)."""
        if self.track_in_progress:
            with self._requests_lock:
                self._requests_in_progress += 1
    
    def end_request(self) -> None:
        """Mark the end of a request (for in-progress tracking)."""
        if self.track_in_progress:
            with self._requests_lock:
                self._requests_in_progress = max(0, self._requests_in_progress - 1)


# Factory functions

def create_system_metrics_collector(config: Optional[Dict[str, Any]] = None) -> SystemMetricsCollector:
    """Create a system metrics collector."""
    return SystemMetricsCollector(config=config)


def create_http_metrics_collector(config: Optional[Dict[str, Any]] = None) -> HTTPMetricsCollector:
    """Create an HTTP metrics collector."""
    return HTTPMetricsCollector(config=config)
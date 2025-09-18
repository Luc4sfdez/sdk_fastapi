"""
Advanced Log Management System for the web dashboard.

Provides comprehensive log collection, streaming, filtering, and management
capabilities with real-time WebSocket integration.
"""

from typing import List, Optional, Dict, Any, AsyncGenerator, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import asyncio
import json
import re
import gzip
import csv
import logging
from collections import defaultdict, deque
import subprocess
import os

from ..core.base_manager import BaseManager


class LogLevel(Enum):
    """Log levels with priority ordering."""
    DEBUG = ("DEBUG", 10)
    INFO = ("INFO", 20)
    WARNING = ("WARNING", 30)
    ERROR = ("ERROR", 40)
    CRITICAL = ("CRITICAL", 50)
    
    def __init__(self, level_name: str, priority: int):
        self.level_name = level_name
        self.priority = priority
    
    @classmethod
    def from_string(cls, level_str: str) -> 'LogLevel':
        """Convert string to LogLevel."""
        level_str = level_str.upper()
        for level in cls:
            if level.level_name == level_str:
                return level
        return cls.INFO  # Default fallback


class LogFormat(Enum):
    """Log export formats."""
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    HTML = "html"


class LogSource(Enum):
    """Log sources."""
    SERVICE = "service"
    SYSTEM = "system"
    APPLICATION = "application"
    CONTAINER = "container"
    FILE = "file"


@dataclass
class LogEntry:
    """Enhanced log entry structure."""
    timestamp: datetime
    level: LogLevel
    service_id: str
    message: str
    source: LogSource = LogSource.SERVICE
    component: Optional[str] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.level_name,
            "service_id": self.service_id,
            "message": self.message,
            "source": self.source.value,
            "component": self.component,
            "thread_id": self.thread_id,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create LogEntry from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=LogLevel.from_string(data["level"]),
            service_id=data["service_id"],
            message=data["message"],
            source=LogSource(data.get("source", "service")),
            component=data.get("component"),
            thread_id=data.get("thread_id"),
            request_id=data.get("request_id"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", [])
        )


@dataclass
class LogFilter:
    """Advanced log filtering criteria."""
    service_ids: Optional[List[str]] = None
    levels: Optional[List[LogLevel]] = None
    sources: Optional[List[LogSource]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    search_text: Optional[str] = None
    regex_pattern: Optional[str] = None
    components: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: int = 1000
    offset: int = 0
    sort_desc: bool = True


@dataclass
class LogStreamConfig:
    """Configuration for log streaming."""
    service_id: str
    client_id: str
    filter: Optional[LogFilter] = None
    buffer_size: int = 100
    max_rate_per_second: int = 50
    include_historical: bool = False
    historical_limit: int = 100


@dataclass
class LogRetentionPolicy:
    """Log retention policy configuration."""
    service_id: str
    retention_days: int = 30
    max_size_mb: int = 1000
    compression_enabled: bool = True
    archive_path: Optional[str] = None
    cleanup_enabled: bool = True


@dataclass
class LogStats:
    """Log statistics."""
    total_entries: int = 0
    entries_by_level: Dict[str, int] = field(default_factory=dict)
    entries_by_service: Dict[str, int] = field(default_factory=dict)
    entries_by_hour: Dict[str, int] = field(default_factory=dict)
    latest_entry: Optional[datetime] = None
    oldest_entry: Optional[datetime] = None
    storage_size_mb: float = 0.0


class LogManager(BaseManager):
    """
    Advanced Log Management System for the web dashboard.
    
    Features:
    - Real-time log streaming with WebSocket integration
    - Advanced filtering, searching, and pagination
    - Log level filtering and highlighting
    - Log export in multiple formats
    - Log retention and archival management
    - Service log collection and aggregation
    - Performance monitoring and statistics
    """
    
    def __init__(self, name: str = "log", config: Optional[Dict[str, Any]] = None):
        """Initialize the log manager."""
        super().__init__(name, config)
        
        # Configuration
        self._retention_days = config.get("retention_days", 30) if config else 30
        self._max_cache_size = config.get("max_cache_size", 10000) if config else 10000
        self._log_directory = Path(config.get("log_directory", "logs")) if config else Path("logs")
        self._enable_compression = config.get("enable_compression", True) if config else True
        self._streaming_buffer_size = config.get("streaming_buffer_size", 100) if config else 100
        
        # Storage
        self._log_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self._max_cache_size))
        self._log_index: Dict[str, Set[str]] = defaultdict(set)  # For fast searching
        self._retention_policies: Dict[str, LogRetentionPolicy] = {}
        
        # Streaming
        self._streaming_clients: Dict[str, LogStreamConfig] = {}
        self._stream_queues: Dict[str, asyncio.Queue] = {}
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self._stats: LogStats = LogStats()
        self._stats_lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._collection_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._log_callbacks: List[Callable[[LogEntry], None]] = []
        
    async def _initialize_impl(self) -> None:
        """Initialize the log manager."""
        try:
            # Create log directory
            self._log_directory.mkdir(parents=True, exist_ok=True)
            
            # Load existing logs
            await self._load_existing_logs()
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._collection_task = asyncio.create_task(self._collection_loop())
            
            # Set up default retention policies
            await self._setup_default_retention_policies()
            
            self.logger.info(f"Log manager initialized with {len(self._log_cache)} services")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize log manager: {e}")
            raise
    
    async def _shutdown_impl(self) -> None:
        """Shutdown the log manager."""
        try:
            # Cancel background tasks
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if self._collection_task:
                self._collection_task.cancel()
                try:
                    await self._collection_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel streaming tasks
            for task in self._stream_tasks.values():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Save logs to disk
            await self._save_logs_to_disk()
            
            self.logger.info("Log manager shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during log manager shutdown: {e}")
    
    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            # Check if background tasks are running
            if self._cleanup_task and self._cleanup_task.done():
                return False
            
            if self._collection_task and self._collection_task.done():
                return False
            
            # Check log directory accessibility
            if not self._log_directory.exists():
                return False
            
            return True
            
        except Exception:
            return False
    
    # Core Log Management Methods
    
    async def add_log_entry(self, entry: LogEntry) -> bool:
        """
        Add a new log entry.
        
        Args:
            entry: Log entry to add
            
        Returns:
            True if added successfully
        """
        return await self._safe_execute(
            "add_log_entry",
            self._add_log_entry_impl,
            entry
        ) or False
    
    async def get_logs(self, filter_criteria: LogFilter) -> List[LogEntry]:
        """
        Get logs based on filter criteria with advanced filtering.
        
        Args:
            filter_criteria: Advanced log filtering criteria
            
        Returns:
            List of filtered log entries
        """
        return await self._safe_execute(
            "get_logs",
            self._get_logs_impl,
            filter_criteria
        ) or []
    
    async def search_logs(self, query: str, service_id: Optional[str] = None, use_regex: bool = False) -> List[LogEntry]:
        """
        Search logs by text query with optional regex support.
        
        Args:
            query: Search query
            service_id: Optional service filter
            use_regex: Whether to use regex matching
            
        Returns:
            List of matching log entries
        """
        return await self._safe_execute(
            "search_logs",
            self._search_logs_impl,
            query,
            service_id,
            use_regex
        ) or []
    
    async def export_logs(self, filter_criteria: LogFilter, format: LogFormat = LogFormat.JSON) -> str:
        """
        Export logs to file in specified format.
        
        Args:
            filter_criteria: Log filtering criteria
            format: Export format
            
        Returns:
            Path to exported file
        """
        result = await self._safe_execute(
            "export_logs",
            self._export_logs_impl,
            filter_criteria,
            format
        )
        return result or ""
    
    # Real-time Streaming Methods
    
    async def start_log_stream(self, config: LogStreamConfig) -> bool:
        """
        Start real-time log streaming for a client.
        
        Args:
            config: Stream configuration
            
        Returns:
            True if stream started successfully
        """
        return await self._safe_execute(
            "start_log_stream",
            self._start_log_stream_impl,
            config
        ) or False
    
    async def stop_log_stream(self, client_id: str) -> bool:
        """
        Stop log streaming for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if stream stopped successfully
        """
        return await self._safe_execute(
            "stop_log_stream",
            self._stop_log_stream_impl,
            client_id
        ) or False
    
    async def get_stream_logs(self, client_id: str, timeout: float = 1.0) -> List[LogEntry]:
        """
        Get logs from stream queue for a client.
        
        Args:
            client_id: Client identifier
            timeout: Timeout for waiting for logs
            
        Returns:
            List of log entries from stream
        """
        return await self._safe_execute(
            "get_stream_logs",
            self._get_stream_logs_impl,
            client_id,
            timeout
        ) or []
    
    # Service Log Collection Methods
    
    async def collect_service_logs(self, service_id: str, log_source: str) -> int:
        """
        Collect logs from a service source.
        
        Args:
            service_id: Service identifier
            log_source: Log source (file path, container, etc.)
            
        Returns:
            Number of logs collected
        """
        return await self._safe_execute(
            "collect_service_logs",
            self._collect_service_logs_impl,
            service_id,
            log_source
        ) or 0
    
    async def tail_service_logs(self, service_id: str, lines: int = 100) -> List[LogEntry]:
        """
        Get the latest logs from a service (tail functionality).
        
        Args:
            service_id: Service identifier
            lines: Number of latest lines to retrieve
            
        Returns:
            List of latest log entries
        """
        filter_criteria = LogFilter(
            service_ids=[service_id],
            limit=lines,
            sort_desc=True
        )
        return await self.get_logs(filter_criteria)
    
    # Log Management and Retention Methods
    
    async def set_retention_policy(self, policy: LogRetentionPolicy) -> bool:
        """
        Set log retention policy for a service.
        
        Args:
            policy: Retention policy configuration
            
        Returns:
            True if policy set successfully
        """
        return await self._safe_execute(
            "set_retention_policy",
            self._set_retention_policy_impl,
            policy
        ) or False
    
    async def cleanup_old_logs(self, service_id: Optional[str] = None) -> Dict[str, int]:
        """
        Clean up old logs based on retention policies.
        
        Args:
            service_id: Optional service to clean up (all services if None)
            
        Returns:
            Dictionary with cleanup statistics
        """
        return await self._safe_execute(
            "cleanup_old_logs",
            self._cleanup_old_logs_impl,
            service_id
        ) or {}
    
    async def archive_logs(self, service_id: str, start_date: datetime, end_date: datetime) -> str:
        """
        Archive logs for a specific time period.
        
        Args:
            service_id: Service identifier
            start_date: Start date for archival
            end_date: End date for archival
            
        Returns:
            Path to archived file
        """
        return await self._safe_execute(
            "archive_logs",
            self._archive_logs_impl,
            service_id,
            start_date,
            end_date
        ) or ""
    
    # Statistics and Analytics Methods
    
    async def get_log_stats(self, service_id: Optional[str] = None) -> LogStats:
        """
        Get log statistics.
        
        Args:
            service_id: Optional service filter
            
        Returns:
            Log statistics
        """
        return await self._safe_execute(
            "get_log_stats",
            self._get_log_stats_impl,
            service_id
        ) or LogStats()
    
    async def get_service_list(self) -> List[str]:
        """
        Get list of services with logs.
        
        Returns:
            List of service IDs
        """
        return list(self._log_cache.keys())
    
    async def get_log_levels_for_service(self, service_id: str) -> List[LogLevel]:
        """
        Get available log levels for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of log levels present in service logs
        """
        return await self._safe_execute(
            "get_log_levels_for_service",
            self._get_log_levels_for_service_impl,
            service_id
        ) or []
    
    # Callback Management
    
    def add_log_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """
        Add callback for new log entries.
        
        Args:
            callback: Callback function to call for each new log entry
        """
        self._log_callbacks.append(callback)
    
    def remove_log_callback(self, callback: Callable[[LogEntry], None]) -> None:
        """
        Remove log callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._log_callbacks:
            self._log_callbacks.remove(callback)
    
    # Implementation Methods
    
    async def _add_log_entry_impl(self, entry: LogEntry) -> bool:
        """Implementation for adding log entry."""
        try:
            # Add to cache
            self._log_cache[entry.service_id].append(entry)
            
            # Update search index
            words = entry.message.lower().split()
            for word in words:
                self._log_index[word].add(entry.service_id)
            
            # Update statistics
            async with self._stats_lock:
                self._stats.total_entries += 1
                self._stats.entries_by_level[entry.level.level_name] = \
                    self._stats.entries_by_level.get(entry.level.level_name, 0) + 1
                self._stats.entries_by_service[entry.service_id] = \
                    self._stats.entries_by_service.get(entry.service_id, 0) + 1
                
                hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
                self._stats.entries_by_hour[hour_key] = \
                    self._stats.entries_by_hour.get(hour_key, 0) + 1
                
                if not self._stats.latest_entry or entry.timestamp > self._stats.latest_entry:
                    self._stats.latest_entry = entry.timestamp
                
                if not self._stats.oldest_entry or entry.timestamp < self._stats.oldest_entry:
                    self._stats.oldest_entry = entry.timestamp
            
            # Notify streaming clients
            await self._notify_streaming_clients(entry)
            
            # Call callbacks
            for callback in self._log_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(entry)
                    else:
                        callback(entry)
                except Exception as e:
                    self.logger.error(f"Log callback failed: {e}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add log entry: {e}")
            return False
    
    async def _get_logs_impl(self, filter_criteria: LogFilter) -> List[LogEntry]:
        """Implementation for getting logs with advanced filtering."""
        try:
            logs = []
            
            # Determine which services to search
            if filter_criteria.service_ids:
                service_ids = filter_criteria.service_ids
            else:
                service_ids = list(self._log_cache.keys())
            
            # Collect logs from specified services
            for service_id in service_ids:
                if service_id in self._log_cache:
                    logs.extend(list(self._log_cache[service_id]))
            
            # Apply filters
            filtered_logs = []
            for log in logs:
                if not self._matches_filter(log, filter_criteria):
                    continue
                filtered_logs.append(log)
            
            # Sort logs
            if filter_criteria.sort_desc:
                filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
            else:
                filtered_logs.sort(key=lambda x: x.timestamp)
            
            # Apply pagination
            start_idx = filter_criteria.offset
            end_idx = start_idx + filter_criteria.limit
            
            return filtered_logs[start_idx:end_idx]
            
        except Exception as e:
            self.logger.error(f"Failed to get logs: {e}")
            return []
    
    def _matches_filter(self, log: LogEntry, filter_criteria: LogFilter) -> bool:
        """Check if log entry matches filter criteria."""
        # Level filter
        if filter_criteria.levels and log.level not in filter_criteria.levels:
            return False
        
        # Source filter
        if filter_criteria.sources and log.source not in filter_criteria.sources:
            return False
        
        # Time range filter
        if filter_criteria.start_time and log.timestamp < filter_criteria.start_time:
            return False
        
        if filter_criteria.end_time and log.timestamp > filter_criteria.end_time:
            return False
        
        # Component filter
        if filter_criteria.components and log.component not in filter_criteria.components:
            return False
        
        # Tags filter
        if filter_criteria.tags:
            if not any(tag in log.tags for tag in filter_criteria.tags):
                return False
        
        # Request ID filter
        if filter_criteria.request_id and log.request_id != filter_criteria.request_id:
            return False
        
        # User ID filter
        if filter_criteria.user_id and log.user_id != filter_criteria.user_id:
            return False
        
        # Text search filter
        if filter_criteria.search_text:
            search_text = filter_criteria.search_text.lower()
            if search_text not in log.message.lower():
                return False
        
        # Regex pattern filter
        if filter_criteria.regex_pattern:
            try:
                pattern = re.compile(filter_criteria.regex_pattern, re.IGNORECASE)
                if not pattern.search(log.message):
                    return False
            except re.error:
                # Invalid regex, skip this filter
                pass
        
        return True
    
    async def _search_logs_impl(self, query: str, service_id: Optional[str] = None, use_regex: bool = False) -> List[LogEntry]:
        """Implementation for searching logs."""
        try:
            filter_criteria = LogFilter(
                service_ids=[service_id] if service_id else None,
                search_text=query if not use_regex else None,
                regex_pattern=query if use_regex else None,
                limit=1000
            )
            return await self._get_logs_impl(filter_criteria)
            
        except Exception as e:
            self.logger.error(f"Failed to search logs: {e}")
            return []
    
    async def _export_logs_impl(self, filter_criteria: LogFilter, format: LogFormat) -> str:
        """Implementation for exporting logs."""
        try:
            # Get logs to export
            logs = await self._get_logs_impl(filter_criteria)
            
            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            service_part = f"_{filter_criteria.service_ids[0]}" if filter_criteria.service_ids and len(filter_criteria.service_ids) == 1 else ""
            filename = f"logs_export{service_part}_{timestamp}.{format.value}"
            filepath = self._log_directory / "exports" / filename
            
            # Create exports directory
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Export based on format
            if format == LogFormat.JSON:
                await self._export_json(logs, filepath)
            elif format == LogFormat.CSV:
                await self._export_csv(logs, filepath)
            elif format == LogFormat.TXT:
                await self._export_txt(logs, filepath)
            elif format == LogFormat.HTML:
                await self._export_html(logs, filepath)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return ""
    
    async def _export_json(self, logs: List[LogEntry], filepath: Path) -> None:
        """Export logs to JSON format."""
        data = [log.to_dict() for log in logs]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    async def _export_csv(self, logs: List[LogEntry], filepath: Path) -> None:
        """Export logs to CSV format."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            # Header
            writer.writerow(['timestamp', 'level', 'service_id', 'message', 'source', 'component'])
            # Data
            for log in logs:
                writer.writerow([
                    log.timestamp.isoformat(),
                    log.level.level_name,
                    log.service_id,
                    log.message,
                    log.source.value,
                    log.component or ''
                ])
    
    async def _export_txt(self, logs: List[LogEntry], filepath: Path) -> None:
        """Export logs to plain text format."""
        with open(filepath, 'w') as f:
            for log in logs:
                f.write(f"[{log.timestamp.isoformat()}] {log.level.level_name} {log.service_id}: {log.message}\n")
    
    async def _export_html(self, logs: List[LogEntry], filepath: Path) -> None:
        """Export logs to HTML format."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Log Export</title>
            <style>
                body { font-family: monospace; }
                .log-entry { margin: 2px 0; }
                .DEBUG { color: #666; }
                .INFO { color: #000; }
                .WARNING { color: #ff8c00; }
                .ERROR { color: #ff0000; }
                .CRITICAL { color: #8b0000; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>Log Export</h1>
        """
        
        for log in logs:
            html_content += f'<div class="log-entry {log.level.level_name}">'
            html_content += f'[{log.timestamp.isoformat()}] {log.level.level_name} {log.service_id}: {log.message}'
            html_content += '</div>\n'
        
        html_content += """
        </body>
        </html>
        """
        
        with open(filepath, 'w') as f:
            f.write(html_content)
    
    # Streaming Implementation Methods
    
    async def _start_log_stream_impl(self, config: LogStreamConfig) -> bool:
        """Implementation for starting log stream."""
        try:
            # Create stream queue
            queue = asyncio.Queue(maxsize=config.buffer_size)
            self._stream_queues[config.client_id] = queue
            self._streaming_clients[config.client_id] = config
            
            # Add historical logs if requested
            if config.include_historical:
                filter_criteria = config.filter or LogFilter()
                filter_criteria.service_ids = [config.service_id]
                filter_criteria.limit = config.historical_limit
                
                historical_logs = await self._get_logs_impl(filter_criteria)
                for log in reversed(historical_logs):  # Add in chronological order
                    try:
                        queue.put_nowait(log)
                    except asyncio.QueueFull:
                        break
            
            self.logger.info(f"Started log stream for client {config.client_id}, service {config.service_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start log stream: {e}")
            return False
    
    async def _stop_log_stream_impl(self, client_id: str) -> bool:
        """Implementation for stopping log stream."""
        try:
            # Remove client from streaming
            if client_id in self._streaming_clients:
                del self._streaming_clients[client_id]
            
            if client_id in self._stream_queues:
                del self._stream_queues[client_id]
            
            if client_id in self._stream_tasks:
                task = self._stream_tasks[client_id]
                task.cancel()
                del self._stream_tasks[client_id]
            
            self.logger.info(f"Stopped log stream for client {client_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop log stream: {e}")
            return False
    
    async def _get_stream_logs_impl(self, client_id: str, timeout: float) -> List[LogEntry]:
        """Implementation for getting stream logs."""
        try:
            if client_id not in self._stream_queues:
                return []
            
            queue = self._stream_queues[client_id]
            logs = []
            
            # Get all available logs with timeout
            try:
                while True:
                    log = await asyncio.wait_for(queue.get(), timeout=timeout)
                    logs.append(log)
                    if len(logs) >= 50:  # Limit batch size
                        break
            except asyncio.TimeoutError:
                pass
            
            return logs
            
        except Exception as e:
            self.logger.error(f"Failed to get stream logs: {e}")
            return []
    
    async def _notify_streaming_clients(self, entry: LogEntry) -> None:
        """Notify streaming clients of new log entry."""
        try:
            for client_id, config in self._streaming_clients.items():
                # Check if log matches client's service and filter
                if config.service_id != entry.service_id:
                    continue
                
                if config.filter and not self._matches_filter(entry, config.filter):
                    continue
                
                # Add to client's queue
                if client_id in self._stream_queues:
                    queue = self._stream_queues[client_id]
                    try:
                        queue.put_nowait(entry)
                    except asyncio.QueueFull:
                        # Remove oldest entry and add new one
                        try:
                            queue.get_nowait()
                            queue.put_nowait(entry)
                        except asyncio.QueueEmpty:
                            pass
                        
        except Exception as e:
            self.logger.error(f"Failed to notify streaming clients: {e}")    

    # Service Log Collection Implementation
    
    async def _collect_service_logs_impl(self, service_id: str, log_source: str) -> int:
        """Implementation for collecting service logs."""
        try:
            collected_count = 0
            
            # Determine log source type and collect accordingly
            if log_source.startswith('/'):
                # File path
                collected_count = await self._collect_from_file(service_id, log_source)
            elif log_source.startswith('docker://'):
                # Docker container
                container_id = log_source.replace('docker://', '')
                collected_count = await self._collect_from_docker(service_id, container_id)
            elif log_source.startswith('journalctl://'):
                # Systemd journal
                unit_name = log_source.replace('journalctl://', '')
                collected_count = await self._collect_from_journalctl(service_id, unit_name)
            else:
                self.logger.warning(f"Unknown log source type: {log_source}")
            
            return collected_count
            
        except Exception as e:
            self.logger.error(f"Failed to collect service logs: {e}")
            return 0
    
    async def _collect_from_file(self, service_id: str, file_path: str) -> int:
        """Collect logs from a file."""
        try:
            if not os.path.exists(file_path):
                return 0
            
            collected_count = 0
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse log line (basic implementation)
                    entry = await self._parse_log_line(service_id, line, LogSource.FILE)
                    if entry:
                        await self._add_log_entry_impl(entry)
                        collected_count += 1
            
            return collected_count
            
        except Exception as e:
            self.logger.error(f"Failed to collect from file {file_path}: {e}")
            return 0
    
    async def _collect_from_docker(self, service_id: str, container_id: str) -> int:
        """Collect logs from Docker container."""
        try:
            # Use docker logs command
            process = await asyncio.create_subprocess_exec(
                'docker', 'logs', '--tail', '100', container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            collected_count = 0
            if stdout:
                for line in stdout.decode().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    entry = await self._parse_log_line(service_id, line, LogSource.CONTAINER)
                    if entry:
                        await self._add_log_entry_impl(entry)
                        collected_count += 1
            
            return collected_count
            
        except Exception as e:
            self.logger.error(f"Failed to collect from Docker container {container_id}: {e}")
            return 0
    
    async def _collect_from_journalctl(self, service_id: str, unit_name: str) -> int:
        """Collect logs from systemd journal."""
        try:
            # Use journalctl command
            process = await asyncio.create_subprocess_exec(
                'journalctl', '-u', unit_name, '--lines', '100', '--output', 'json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            collected_count = 0
            if stdout:
                for line in stdout.decode().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        journal_entry = json.loads(line)
                        entry = await self._parse_journal_entry(service_id, journal_entry)
                        if entry:
                            await self._add_log_entry_impl(entry)
                            collected_count += 1
                    except json.JSONDecodeError:
                        continue
            
            return collected_count
            
        except Exception as e:
            self.logger.error(f"Failed to collect from journalctl unit {unit_name}: {e}")
            return 0
    
    async def _parse_log_line(self, service_id: str, line: str, source: LogSource) -> Optional[LogEntry]:
        """Parse a log line into LogEntry."""
        try:
            # Basic log parsing (can be enhanced with more sophisticated parsing)
            timestamp = datetime.utcnow()
            level = LogLevel.INFO
            message = line
            
            # Try to extract timestamp and level from common formats
            # Format: [2024-01-01 12:00:00] LEVEL message
            timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
            timestamp_match = re.search(timestamp_pattern, line)
            if timestamp_match:
                try:
                    timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                    message = line[timestamp_match.end():].strip()
                except ValueError:
                    pass
            
            # Try to extract log level
            level_pattern = r'\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b'
            level_match = re.search(level_pattern, message, re.IGNORECASE)
            if level_match:
                level = LogLevel.from_string(level_match.group(1))
                message = message.replace(level_match.group(0), '').strip()
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                service_id=service_id,
                message=message,
                source=source
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse log line: {e}")
            return None
    
    async def _parse_journal_entry(self, service_id: str, journal_entry: Dict[str, Any]) -> Optional[LogEntry]:
        """Parse a systemd journal entry into LogEntry."""
        try:
            # Extract timestamp
            timestamp_str = journal_entry.get('__REALTIME_TIMESTAMP')
            if timestamp_str:
                # Convert microseconds to datetime
                timestamp = datetime.fromtimestamp(int(timestamp_str) / 1000000)
            else:
                timestamp = datetime.utcnow()
            
            # Extract message
            message = journal_entry.get('MESSAGE', '')
            
            # Extract priority (syslog level)
            priority = journal_entry.get('PRIORITY', '6')  # Default to INFO
            level_map = {
                '0': LogLevel.CRITICAL,  # Emergency
                '1': LogLevel.CRITICAL,  # Alert
                '2': LogLevel.CRITICAL,  # Critical
                '3': LogLevel.ERROR,     # Error
                '4': LogLevel.WARNING,   # Warning
                '5': LogLevel.INFO,      # Notice
                '6': LogLevel.INFO,      # Info
                '7': LogLevel.DEBUG      # Debug
            }
            level = level_map.get(priority, LogLevel.INFO)
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                service_id=service_id,
                message=message,
                source=LogSource.SYSTEM,
                metadata=journal_entry
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse journal entry: {e}")
            return None
    
    # Retention and Cleanup Implementation
    
    async def _set_retention_policy_impl(self, policy: LogRetentionPolicy) -> bool:
        """Implementation for setting retention policy."""
        try:
            self._retention_policies[policy.service_id] = policy
            self.logger.info(f"Set retention policy for service {policy.service_id}: {policy.retention_days} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set retention policy: {e}")
            return False
    
    async def _cleanup_old_logs_impl(self, service_id: Optional[str] = None) -> Dict[str, int]:
        """Implementation for cleaning up old logs."""
        try:
            cleanup_stats = {}
            
            services_to_clean = [service_id] if service_id else list(self._log_cache.keys())
            
            for svc_id in services_to_clean:
                if svc_id not in self._retention_policies:
                    continue
                
                policy = self._retention_policies[svc_id]
                cutoff_date = datetime.utcnow() - timedelta(days=policy.retention_days)
                
                # Remove old logs from cache
                original_count = len(self._log_cache[svc_id])
                self._log_cache[svc_id] = deque(
                    [log for log in self._log_cache[svc_id] if log.timestamp > cutoff_date],
                    maxlen=self._max_cache_size
                )
                removed_count = original_count - len(self._log_cache[svc_id])
                
                cleanup_stats[svc_id] = removed_count
                
                if removed_count > 0:
                    self.logger.info(f"Cleaned up {removed_count} old logs for service {svc_id}")
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            return {}
    
    async def _archive_logs_impl(self, service_id: str, start_date: datetime, end_date: datetime) -> str:
        """Implementation for archiving logs."""
        try:
            # Get logs in date range
            filter_criteria = LogFilter(
                service_ids=[service_id],
                start_time=start_date,
                end_time=end_date,
                limit=100000  # Large limit for archival
            )
            logs = await self._get_logs_impl(filter_criteria)
            
            if not logs:
                return ""
            
            # Create archive filename
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            archive_filename = f"{service_id}_logs_{start_str}_{end_str}.json.gz"
            archive_path = self._log_directory / "archives" / archive_filename
            
            # Create archives directory
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write compressed archive
            data = [log.to_dict() for log in logs]
            with gzip.open(archive_path, 'wt') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Archived {len(logs)} logs for service {service_id} to {archive_path}")
            return str(archive_path)
            
        except Exception as e:
            self.logger.error(f"Failed to archive logs: {e}")
            return ""
    
    # Statistics Implementation
    
    async def _get_log_stats_impl(self, service_id: Optional[str] = None) -> LogStats:
        """Implementation for getting log statistics."""
        try:
            if service_id:
                # Service-specific stats
                service_logs = list(self._log_cache.get(service_id, []))
                
                stats = LogStats()
                stats.total_entries = len(service_logs)
                stats.entries_by_service[service_id] = len(service_logs)
                
                for log in service_logs:
                    level_name = log.level.level_name
                    stats.entries_by_level[level_name] = stats.entries_by_level.get(level_name, 0) + 1
                    
                    hour_key = log.timestamp.strftime("%Y-%m-%d %H:00")
                    stats.entries_by_hour[hour_key] = stats.entries_by_hour.get(hour_key, 0) + 1
                    
                    if not stats.latest_entry or log.timestamp > stats.latest_entry:
                        stats.latest_entry = log.timestamp
                    
                    if not stats.oldest_entry or log.timestamp < stats.oldest_entry:
                        stats.oldest_entry = log.timestamp
                
                return stats
            else:
                # Return global stats
                async with self._stats_lock:
                    return LogStats(
                        total_entries=self._stats.total_entries,
                        entries_by_level=self._stats.entries_by_level.copy(),
                        entries_by_service=self._stats.entries_by_service.copy(),
                        entries_by_hour=self._stats.entries_by_hour.copy(),
                        latest_entry=self._stats.latest_entry,
                        oldest_entry=self._stats.oldest_entry,
                        storage_size_mb=self._stats.storage_size_mb
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to get log stats: {e}")
            return LogStats()
    
    async def _get_log_levels_for_service_impl(self, service_id: str) -> List[LogLevel]:
        """Implementation for getting log levels for service."""
        try:
            if service_id not in self._log_cache:
                return []
            
            levels = set()
            for log in self._log_cache[service_id]:
                levels.add(log.level)
            
            return sorted(list(levels), key=lambda x: x.priority)
            
        except Exception as e:
            self.logger.error(f"Failed to get log levels for service: {e}")
            return []
    
    # Background Tasks
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_logs_impl()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _collection_loop(self) -> None:
        """Background log collection loop."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Collect logs from known services (placeholder)
                # In a real implementation, this would collect from various sources
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in collection loop: {e}")
    
    # Utility Methods
    
    async def _load_existing_logs(self) -> None:
        """Load existing logs from disk."""
        try:
            # Load logs from log files (placeholder implementation)
            # In a real implementation, this would load from persistent storage
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to load existing logs: {e}")
    
    async def _save_logs_to_disk(self) -> None:
        """Save logs to disk."""
        try:
            # Save logs to persistent storage (placeholder implementation)
            # In a real implementation, this would save to files or database
            pass
            
        except Exception as e:
            self.logger.error(f"Failed to save logs to disk: {e}")
    
    async def _setup_default_retention_policies(self) -> None:
        """Setup default retention policies."""
        try:
            # Set default retention policy
            default_policy = LogRetentionPolicy(
                service_id="default",
                retention_days=self._retention_days,
                max_size_mb=1000,
                compression_enabled=self._enable_compression
            )
            
            self._retention_policies["default"] = default_policy
            
        except Exception as e:
            self.logger.error(f"Failed to setup default retention policies: {e}")
    
    # Test and Demo Methods
    
    async def generate_sample_logs(self, service_id: str, count: int = 100) -> int:
        """
        Generate sample logs for testing purposes.
        
        Args:
            service_id: Service identifier
            count: Number of sample logs to generate
            
        Returns:
            Number of logs generated
        """
        try:
            generated = 0
            levels = list(LogLevel)
            sources = list(LogSource)
            
            for i in range(count):
                entry = LogEntry(
                    timestamp=datetime.utcnow() - timedelta(minutes=count - i),
                    level=levels[i % len(levels)],
                    service_id=service_id,
                    message=f"Sample log message {i + 1} for testing purposes",
                    source=sources[i % len(sources)],
                    component=f"component-{i % 3}",
                    request_id=f"req-{i // 10}",
                    metadata={"sample": True, "index": i}
                )
                
                if await self._add_log_entry_impl(entry):
                    generated += 1
            
            self.logger.info(f"Generated {generated} sample logs for service {service_id}")
            return generated
            
        except Exception as e:
            self.logger.error(f"Failed to generate sample logs: {e}")
            return 0
"""
Log Handlers for FastAPI Microservices SDK.

This module provides various log handlers for different destinations
including console, file, ELK stack, and buffered handlers with retry logic.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import threading
import time
import queue
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field

from .config import LoggingConfig
from .exceptions import LoggingError, LogShippingError, LogBufferError
from .formatters import BaseFormatter, create_formatter
from .structured_logger import LogRecord


@dataclass
class HandlerMetrics:
    """Metrics for log handlers."""
    
    logs_processed: int = 0
    logs_failed: int = 0
    logs_buffered: int = 0
    logs_dropped: int = 0
    last_flush_time: float = 0.0
    total_flush_time: float = 0.0
    flush_count: int = 0
    
    def get_success_rate(self) -> float:
        """Get success rate."""
        total = self.logs_processed + self.logs_failed
        return self.logs_processed / max(1, total)
    
    def get_average_flush_time(self) -> float:
        """Get average flush time."""
        return self.total_flush_time / max(1, self.flush_count)


class BaseHandler(ABC):
    """Base class for log handlers."""
    
    def __init__(self, config: LoggingConfig, formatter: BaseFormatter):
        self.config = config
        self.formatter = formatter
        self.metrics = HandlerMetrics()
        self._lock = threading.RLock()
        self._enabled = True
    
    @abstractmethod
    def emit(self, record: LogRecord) -> bool:
        """Emit log record."""
        pass
    
    def flush(self):
        """Flush any buffered logs."""
        pass
    
    def close(self):
        """Close handler and cleanup resources."""
        pass
    
    def enable(self):
        """Enable handler."""
        self._enabled = True
    
    def disable(self):
        """Disable handler."""
        self._enabled = False
    
    def is_enabled(self) -> bool:
        """Check if handler is enabled."""
        return self._enabled
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get handler metrics."""
        with self._lock:
            return {
                'handler_type': self.__class__.__name__,
                'enabled': self._enabled,
                'logs_processed': self.metrics.logs_processed,
                'logs_failed': self.metrics.logs_failed,
                'logs_buffered': self.metrics.logs_buffered,
                'logs_dropped': self.metrics.logs_dropped,
                'success_rate': self.metrics.get_success_rate(),
                'last_flush_time': self.metrics.last_flush_time,
                'average_flush_time': self.metrics.get_average_flush_time(),
                'flush_count': self.metrics.flush_count
            }


class ConsoleHandler(BaseHandler):
    """Console log handler."""
    
    def __init__(self, config: LoggingConfig, formatter: BaseFormatter):
        super().__init__(config, formatter)
        self._stdout = True  # Use stdout by default
    
    def emit(self, record: LogRecord) -> bool:
        """Emit log record to console."""
        if not self._enabled:
            return False
        
        try:
            formatted_message = self.formatter.format(record)
            
            # Choose output stream based on log level
            import sys
            if record.level in ['ERROR', 'CRITICAL']:
                print(formatted_message, file=sys.stderr)
            else:
                print(formatted_message, file=sys.stdout)
            
            with self._lock:
                self.metrics.logs_processed += 1
            
            return True
            
        except Exception as e:
            with self._lock:
                self.metrics.logs_failed += 1
            return False


class FileHandler(BaseHandler):
    """File log handler with rotation support."""
    
    def __init__(
        self, 
        config: LoggingConfig, 
        formatter: BaseFormatter,
        file_path: Optional[str] = None
    ):
        super().__init__(config, formatter)
        self.file_path = file_path or config.file_path or "application.log"
        self._file_handler = None
        self._setup_file_handler()
    
    def _setup_file_handler(self):
        """Setup underlying file handler."""
        try:
            if self.config.file_rotation:
                from logging.handlers import RotatingFileHandler
                
                # Parse max size
                max_bytes = self._parse_size(self.config.file_max_size)
                
                self._file_handler = RotatingFileHandler(
                    filename=self.file_path,
                    maxBytes=max_bytes,
                    backupCount=self.config.file_backup_count,
                    encoding='utf-8'
                )
            else:
                self._file_handler = logging.FileHandler(
                    filename=self.file_path,
                    encoding='utf-8'
                )
                
        except Exception as e:
            raise LoggingError(
                message=f"Failed to setup file handler: {e}",
                logger_name="FileHandler",
                original_error=e
            )
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes."""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def emit(self, record: LogRecord) -> bool:
        """Emit log record to file."""
        if not self._enabled or not self._file_handler:
            return False
        
        try:
            formatted_message = self.formatter.format(record)
            
            # Create logging record for file handler
            log_record = logging.LogRecord(
                name=record.logger_name,
                level=getattr(logging, record.level),
                pathname="",
                lineno=0,
                msg=formatted_message,
                args=(),
                exc_info=None
            )
            
            self._file_handler.emit(log_record)
            
            with self._lock:
                self.metrics.logs_processed += 1
            
            return True
            
        except Exception as e:
            with self._lock:
                self.metrics.logs_failed += 1
            return False
    
    def flush(self):
        """Flush file handler."""
        if self._file_handler:
            self._file_handler.flush()
    
    def close(self):
        """Close file handler."""
        if self._file_handler:
            self._file_handler.close()


class BufferedHandler(BaseHandler):
    """Buffered log handler with automatic flushing."""
    
    def __init__(
        self,
        config: LoggingConfig,
        formatter: BaseFormatter,
        target_handler: BaseHandler,
        buffer_size: Optional[int] = None,
        flush_interval: Optional[float] = None
    ):
        super().__init__(config, formatter)
        self.target_handler = target_handler
        self.buffer_size = buffer_size or config.buffer_size
        self.flush_interval = flush_interval or config.flush_interval
        
        self._buffer: deque = deque()
        self._last_flush_time = time.time()
        self._flush_timer: Optional[threading.Timer] = None
        self._shutdown_event = threading.Event()
        
        # Start flush timer
        self._start_flush_timer()
    
    def _start_flush_timer(self):
        """Start automatic flush timer."""
        if self._shutdown_event.is_set():
            return
        
        self._flush_timer = threading.Timer(self.flush_interval, self._auto_flush)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    def _auto_flush(self):
        """Automatic flush callback."""
        try:
            self.flush()
        except Exception:
            pass  # Ignore flush errors in timer
        finally:
            # Schedule next flush
            self._start_flush_timer()
    
    def emit(self, record: LogRecord) -> bool:
        """Emit log record to buffer."""
        if not self._enabled:
            return False
        
        try:
            with self._lock:
                # Check if buffer is full
                if len(self._buffer) >= self.buffer_size:
                    # Drop oldest record
                    self._buffer.popleft()
                    self.metrics.logs_dropped += 1
                
                # Add to buffer
                self._buffer.append(record)
                self.metrics.logs_buffered += 1
                
                # Check if we need to flush immediately
                should_flush = (
                    len(self._buffer) >= self.buffer_size or
                    record.level in ['ERROR', 'CRITICAL'] or
                    time.time() - self._last_flush_time >= self.flush_interval
                )
                
                if should_flush:
                    self._flush_buffer()
            
            return True
            
        except Exception as e:
            with self._lock:
                self.metrics.logs_failed += 1
            return False
    
    def _flush_buffer(self):
        """Flush buffer to target handler."""
        if not self._buffer:
            return
        
        start_time = time.time()
        
        try:
            # Get all records from buffer
            records_to_flush = list(self._buffer)
            self._buffer.clear()
            
            # Send to target handler
            success_count = 0
            for record in records_to_flush:
                if self.target_handler.emit(record):
                    success_count += 1
            
            # Update metrics
            self.metrics.logs_processed += success_count
            self.metrics.logs_failed += len(records_to_flush) - success_count
            self.metrics.logs_buffered -= len(records_to_flush)
            
            flush_time = time.time() - start_time
            self.metrics.last_flush_time = time.time()
            self.metrics.total_flush_time += flush_time
            self.metrics.flush_count += 1
            
        except Exception as e:
            # Put records back in buffer if flush failed
            for record in records_to_flush:
                if len(self._buffer) < self.buffer_size:
                    self._buffer.append(record)
                else:
                    self.metrics.logs_dropped += 1
            
            raise LogBufferError(
                message=f"Failed to flush buffer: {e}",
                buffer_size=len(records_to_flush),
                buffer_type="deque",
                flush_interval=self.flush_interval,
                original_error=e
            )
    
    def flush(self):
        """Manually flush buffer."""
        with self._lock:
            self._flush_buffer()
        
        # Also flush target handler
        self.target_handler.flush()
    
    def close(self):
        """Close buffered handler."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel timer
        if self._flush_timer:
            self._flush_timer.cancel()
        
        # Final flush
        try:
            self.flush()
        except Exception:
            pass
        
        # Close target handler
        self.target_handler.close()


class RetryHandler(BaseHandler):
    """Handler with retry logic for failed log deliveries."""
    
    def __init__(
        self,
        config: LoggingConfig,
        formatter: BaseFormatter,
        target_handler: BaseHandler,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        backoff_multiplier: float = 2.0
    ):
        super().__init__(config, formatter)
        self.target_handler = target_handler
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_multiplier = backoff_multiplier
        
        # Retry queue
        self._retry_queue: queue.Queue = queue.Queue()
        self._retry_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Start retry worker
        self._start_retry_worker()
    
    def _start_retry_worker(self):
        """Start retry worker thread."""
        def retry_worker():
            while not self._shutdown_event.is_set():
                try:
                    # Get record from retry queue with timeout
                    try:
                        retry_item = self._retry_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    record, attempt = retry_item
                    
                    # Calculate delay with exponential backoff
                    delay = self.retry_delay * (self.backoff_multiplier ** (attempt - 1))
                    time.sleep(delay)
                    
                    # Attempt to emit
                    if self.target_handler.emit(record):
                        # Success
                        with self._lock:
                            self.metrics.logs_processed += 1
                    else:
                        # Failed, check if we should retry
                        if attempt < self.max_retries:
                            self._retry_queue.put((record, attempt + 1))
                        else:
                            # Max retries exceeded
                            with self._lock:
                                self.metrics.logs_failed += 1
                    
                    self._retry_queue.task_done()
                    
                except Exception:
                    # Ignore errors in retry worker
                    pass
        
        self._retry_thread = threading.Thread(target=retry_worker, daemon=True)
        self._retry_thread.start()
    
    def emit(self, record: LogRecord) -> bool:
        """Emit log record with retry logic."""
        if not self._enabled:
            return False
        
        # Try immediate delivery
        if self.target_handler.emit(record):
            with self._lock:
                self.metrics.logs_processed += 1
            return True
        
        # Failed, add to retry queue
        try:
            self._retry_queue.put((record, 1), block=False)
            return True
        except queue.Full:
            with self._lock:
                self.metrics.logs_dropped += 1
            return False
    
    def flush(self):
        """Flush target handler."""
        self.target_handler.flush()
    
    def close(self):
        """Close retry handler."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for retry queue to empty
        try:
            self._retry_queue.join()
        except Exception:
            pass
        
        # Wait for retry thread
        if self._retry_thread and self._retry_thread.is_alive():
            self._retry_thread.join(timeout=5.0)
        
        # Close target handler
        self.target_handler.close()


class AsyncHandler(BaseHandler):
    """Asynchronous log handler."""
    
    def __init__(
        self,
        config: LoggingConfig,
        formatter: BaseFormatter,
        target_handler: BaseHandler,
        queue_size: Optional[int] = None,
        worker_count: int = 1
    ):
        super().__init__(config, formatter)
        self.target_handler = target_handler
        self.queue_size = queue_size or config.queue_size
        self.worker_count = worker_count
        
        # Async queue
        self._queue: queue.Queue = queue.Queue(maxsize=self.queue_size)
        self._workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        
        # Start workers
        self._start_workers()
    
    def _start_workers(self):
        """Start worker threads."""
        def worker():
            while not self._shutdown_event.is_set():
                try:
                    # Get record from queue
                    try:
                        record = self._queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    # Process record
                    if self.target_handler.emit(record):
                        with self._lock:
                            self.metrics.logs_processed += 1
                    else:
                        with self._lock:
                            self.metrics.logs_failed += 1
                    
                    self._queue.task_done()
                    
                except Exception:
                    # Ignore errors in worker
                    pass
        
        for i in range(self.worker_count):
            worker_thread = threading.Thread(target=worker, daemon=True)
            worker_thread.start()
            self._workers.append(worker_thread)
    
    def emit(self, record: LogRecord) -> bool:
        """Emit log record asynchronously."""
        if not self._enabled:
            return False
        
        try:
            self._queue.put(record, block=False)
            return True
        except queue.Full:
            with self._lock:
                self.metrics.logs_dropped += 1
            return False
    
    def flush(self):
        """Flush async handler."""
        # Wait for queue to empty
        self._queue.join()
        
        # Flush target handler
        self.target_handler.flush()
    
    def close(self):
        """Close async handler."""
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for queue to empty
        try:
            self._queue.join()
        except Exception:
            pass
        
        # Wait for workers
        for worker in self._workers:
            if worker.is_alive():
                worker.join(timeout=2.0)
        
        # Close target handler
        self.target_handler.close()


def create_handler(
    handler_type: str,
    config: LoggingConfig,
    formatter: Optional[BaseFormatter] = None,
    **kwargs
) -> BaseHandler:
    """Create handler based on type."""
    
    if formatter is None:
        formatter = create_formatter(config.log_format, config)
    
    if handler_type == "console":
        return ConsoleHandler(config, formatter, **kwargs)
    elif handler_type == "file":
        return FileHandler(config, formatter, **kwargs)
    elif handler_type == "buffered":
        target_handler = kwargs.pop('target_handler')
        return BufferedHandler(config, formatter, target_handler, **kwargs)
    elif handler_type == "retry":
        target_handler = kwargs.pop('target_handler')
        return RetryHandler(config, formatter, target_handler, **kwargs)
    elif handler_type == "async":
        target_handler = kwargs.pop('target_handler')
        return AsyncHandler(config, formatter, target_handler, **kwargs)
    else:
        raise LoggingError(
            message=f"Unsupported handler type: {handler_type}",
            logger_name="HandlerFactory"
        )


# Export main classes and functions
__all__ = [
    'HandlerMetrics',
    'BaseHandler',
    'ConsoleHandler',
    'FileHandler',
    'BufferedHandler',
    'RetryHandler',
    'AsyncHandler',
    'create_handler',
]
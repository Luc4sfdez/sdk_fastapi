"""
Advanced Jaeger Integration for Distributed Tracing.

This module provides advanced Jaeger integration with custom configuration,
performance optimization, and enterprise-grade features for production deployments.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

# Jaeger and OpenTelemetry imports
try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter as JaegerGRPCExporter
    from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
    from opentelemetry.trace import Span as OTelSpan
    from opentelemetry.sdk.trace import ReadableSpan
    import jaeger_client
    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False
    # Mock classes for development
    class JaegerExporter:
        pass
    class JaegerGRPCExporter:
        pass
    class SpanExporter:
        pass
    class ReadableSpan:
        pass
    class SpanExportResult:
        pass
    class SpanExportResult:
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"

from .exceptions import JaegerExportError, TraceExportError
from ..config import TracingConfig


class JaegerProtocol(Enum):
    """Jaeger communication protocols."""
    THRIFT_UDP = "thrift_udp"
    THRIFT_HTTP = "thrift_http"
    GRPC = "grpc"


class JaegerSamplingType(Enum):
    """Jaeger sampling types."""
    CONST = "const"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "ratelimiting"
    REMOTE = "remote"


@dataclass
class JaegerConfig:
    """Advanced Jaeger configuration."""
    # Connection settings
    agent_host: str = "localhost"
    agent_port: int = 6831
    collector_endpoint: str = "http://localhost:14268/api/traces"
    protocol: JaegerProtocol = JaegerProtocol.THRIFT_UDP
    
    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    
    # Performance settings
    max_tag_value_length: int = 1024
    max_packet_size: int = 65000
    flush_interval: float = 1.0
    queue_size: int = 100
    
    # Sampling configuration
    sampling_type: JaegerSamplingType = JaegerSamplingType.PROBABILISTIC
    sampling_rate: float = 0.1
    sampling_server_url: Optional[str] = None
    
    # Advanced settings
    tags: Dict[str, str] = field(default_factory=dict)
    process_tags: Dict[str, str] = field(default_factory=dict)
    reporter_log_spans: bool = False
    reporter_max_queue_size: int = 100
    reporter_flush_interval: float = 1.0
    
    # Retry and timeout settings
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0
    
    # Security settings
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    tls_ca_path: Optional[str] = None
    
    # Compression
    compression_enabled: bool = True
    compression_level: int = 6


class AdvancedJaegerExporter:
    """Advanced Jaeger exporter with enhanced features."""
    
    def __init__(self, config: JaegerConfig):
        self.config = config
        self._exporter: Optional[SpanExporter] = None
        self._initialized = False
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
        # Performance metrics
        self._export_count = 0
        self._export_errors = 0
        self._last_export_time = 0.0
        self._total_export_time = 0.0
        
        # Retry mechanism
        self._retry_queue: List[ReadableSpan] = []
        self._retry_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        if not JAEGER_AVAILABLE:
            self._logger.warning("Jaeger client not available - exporter will be disabled")
    
    def initialize(self) -> None:
        """Initialize the Jaeger exporter."""
        if not JAEGER_AVAILABLE:
            raise JaegerExportError("Jaeger client not available")
        
        with self._lock:
            if self._initialized:
                return
            
            try:
                self._exporter = self._create_exporter()
                self._start_retry_thread()
                self._initialized = True
                self._logger.info("Advanced Jaeger exporter initialized successfully")
            except Exception as e:
                self._logger.error(f"Failed to initialize Jaeger exporter: {e}")
                raise JaegerExportError(
                    message="Failed to initialize Jaeger exporter",
                    jaeger_endpoint=self.config.collector_endpoint,
                    original_error=e
                )
    
    def shutdown(self) -> None:
        """Shutdown the Jaeger exporter."""
        with self._lock:
            if not self._initialized:
                return
            
            try:
                # Signal shutdown
                self._shutdown_event.set()
                
                # Wait for retry thread to finish
                if self._retry_thread and self._retry_thread.is_alive():
                    self._retry_thread.join(timeout=5.0)
                
                # Shutdown exporter
                if self._exporter and hasattr(self._exporter, 'shutdown'):
                    self._exporter.shutdown()
                
                self._initialized = False
                self._logger.info("Advanced Jaeger exporter shutdown successfully")
            except Exception as e:
                self._logger.error(f"Error during Jaeger exporter shutdown: {e}")
    
    def export(self, spans: List[Any]) -> Any:
        """Export spans to Jaeger with retry mechanism."""
        if not self._initialized or not self._exporter:
            return SpanExportResult.FAILURE
        
        start_time = time.time()
        try:
            # Filter and prepare spans
            filtered_spans = self._filter_spans(spans)
            if not filtered_spans:
                return SpanExportResult.SUCCESS
            
            # Export spans
            result = self._exporter.export(filtered_spans)
            
            # Update metrics
            export_time = time.time() - start_time
            self._update_metrics(len(filtered_spans), export_time, result == SpanExportResult.SUCCESS)
            
            if result == SpanExportResult.SUCCESS:
                self._logger.debug(f"Successfully exported {len(filtered_spans)} spans to Jaeger")
            else:
                self._logger.warning(f"Failed to export {len(filtered_spans)} spans to Jaeger")
                # Add to retry queue
                self._add_to_retry_queue(filtered_spans)
            
            return result
            
        except Exception as e:
            export_time = time.time() - start_time
            self._update_metrics(len(spans), export_time, False)
            self._logger.error(f"Error exporting spans to Jaeger: {e}")
            # Add to retry queue
            self._add_to_retry_queue(spans)
            return SpanExportResult.FAILURE
    
    def get_export_metrics(self) -> Dict[str, Any]:
        """Get export performance metrics."""
        with self._lock:
            total_exports = self._export_count + self._export_errors
            avg_export_time = (
                self._total_export_time / max(1, total_exports)
            ) * 1000  # Convert to milliseconds
            
            return {
                'total_exports': total_exports,
                'successful_exports': self._export_count,
                'failed_exports': self._export_errors,
                'success_rate': self._export_count / max(1, total_exports),
                'average_export_time_ms': avg_export_time,
                'last_export_time': self._last_export_time,
                'retry_queue_size': len(self._retry_queue),
                'initialized': self._initialized
            }
    
    def _create_exporter(self) -> SpanExporter:
        """Create the appropriate Jaeger exporter based on configuration."""
        if self.config.protocol == JaegerProtocol.GRPC:
            return self._create_grpc_exporter()
        elif self.config.protocol == JaegerProtocol.THRIFT_HTTP:
            return self._create_thrift_http_exporter()
        else:  # THRIFT_UDP
            return self._create_thrift_udp_exporter()
    
    def _create_grpc_exporter(self) -> JaegerGRPCExporter:
        """Create gRPC Jaeger exporter."""
        return JaegerGRPCExporter(
            collector_endpoint=self.config.collector_endpoint,
            credentials=self._get_grpc_credentials(),
            headers=self._get_auth_headers()
        )
    
    def _create_thrift_http_exporter(self) -> JaegerExporter:
        """Create Thrift HTTP Jaeger exporter."""
        return JaegerExporter(
            collector_endpoint=self.config.collector_endpoint,
            username=self.config.username,
            password=self.config.password,
            max_tag_value_length=self.config.max_tag_value_length
        )
    
    def _create_thrift_udp_exporter(self) -> JaegerExporter:
        """Create Thrift UDP Jaeger exporter."""
        return JaegerExporter(
            agent_host_name=self.config.agent_host,
            agent_port=self.config.agent_port,
            max_tag_value_length=self.config.max_tag_value_length
        )
    
    def _get_grpc_credentials(self):
        """Get gRPC credentials for secure connection."""
        if not self.config.tls_enabled:
            return None
        
        try:
            import grpc
            if self.config.tls_cert_path and self.config.tls_key_path:
                # Mutual TLS
                with open(self.config.tls_cert_path, 'rb') as f:
                    cert = f.read()
                with open(self.config.tls_key_path, 'rb') as f:
                    key = f.read()
                
                ca_cert = None
                if self.config.tls_ca_path:
                    with open(self.config.tls_ca_path, 'rb') as f:
                        ca_cert = f.read()
                
                return grpc.ssl_channel_credentials(
                    root_certificates=ca_cert,
                    private_key=key,
                    certificate_chain=cert
                )
            else:
                # Server-side TLS only
                return grpc.ssl_channel_credentials()
        except Exception as e:
            self._logger.warning(f"Failed to create gRPC credentials: {e}")
            return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}
        if self.config.token:
            headers['Authorization'] = f'Bearer {self.config.token}'
        elif self.config.username and self.config.password:
            import base64
            credentials = base64.b64encode(
                f'{self.config.username}:{self.config.password}'.encode()
            ).decode()
            headers['Authorization'] = f'Basic {credentials}'
        return headers
    
    def _filter_spans(self, spans: List[Any]) -> List[Any]:
        """Filter spans based on configuration."""
        filtered = []
        for span in spans:
            # Skip invalid spans
            if not span or not span.name:
                continue
            
            # Apply custom filtering logic here
            # For example, filter by service name, operation name, etc.
            filtered.append(span)
        
        return filtered
    
    def _update_metrics(self, span_count: int, export_time: float, success: bool) -> None:
        """Update export metrics."""
        with self._lock:
            if success:
                self._export_count += span_count
            else:
                self._export_errors += span_count
            
            self._total_export_time += export_time
            self._last_export_time = time.time()
    
    def _add_to_retry_queue(self, spans: List[ReadableSpan]) -> None:
        """Add spans to retry queue."""
        with self._lock:
            # Limit retry queue size
            available_space = max(0, self.config.reporter_max_queue_size - len(self._retry_queue))
            spans_to_add = spans[:available_space]
            self._retry_queue.extend(spans_to_add)
            
            if len(spans) > available_space:
                self._logger.warning(
                    f"Retry queue full, dropped {len(spans) - available_space} spans"
                )
    
    def _start_retry_thread(self) -> None:
        """Start the retry thread for failed exports."""
        def retry_worker():
            while not self._shutdown_event.is_set():
                try:
                    # Wait for retry interval or shutdown
                    if self._shutdown_event.wait(self.config.retry_delay):
                        break
                    
                    # Process retry queue
                    self._process_retry_queue()
                except Exception as e:
                    self._logger.error(f"Error in retry worker: {e}")
        
        self._retry_thread = threading.Thread(target=retry_worker, daemon=True)
        self._retry_thread.start()
    
    def _process_retry_queue(self) -> None:
        """Process spans in the retry queue."""
        with self._lock:
            if not self._retry_queue:
                return
            
            # Get spans to retry
            spans_to_retry = self._retry_queue.copy()
            self._retry_queue.clear()
        
        # Attempt to export
        if spans_to_retry:
            self._logger.debug(f"Retrying export of {len(spans_to_retry)} spans")
            result = self.export(spans_to_retry)
            if result != SpanExportResult.SUCCESS:
                self._logger.warning(f"Retry export failed for {len(spans_to_retry)} spans")


class JaegerSamplingManager:
    """Advanced sampling manager for Jaeger."""
    
    def __init__(self, config: JaegerConfig):
        self.config = config
        self._sampler = None
        self._logger = logging.getLogger(__name__)
    
    def create_sampler(self):
        """Create appropriate sampler based on configuration."""
        if not JAEGER_AVAILABLE:
            self._logger.warning("Jaeger client not available - using default sampler")
            return None
        
        try:
            if self.config.sampling_type == JaegerSamplingType.CONST:
                return jaeger_client.ConstSampler(decision=self.config.sampling_rate > 0)
            elif self.config.sampling_type == JaegerSamplingType.PROBABILISTIC:
                return jaeger_client.ProbabilisticSampler(rate=self.config.sampling_rate)
            elif self.config.sampling_type == JaegerSamplingType.RATE_LIMITING:
                return jaeger_client.RateLimitingSampler(
                    max_traces_per_second=self.config.sampling_rate
                )
            elif self.config.sampling_type == JaegerSamplingType.REMOTE:
                return jaeger_client.RemoteControlledSampler(
                    service_name="fastapi-microservice",
                    sampling_server_url=self.config.sampling_server_url or "http://localhost:5778/sampling"
                )
            else:
                # Default to probabilistic
                return jaeger_client.ProbabilisticSampler(rate=self.config.sampling_rate)
        except Exception as e:
            self._logger.error(f"Failed to create Jaeger sampler: {e}")
            return None


class JaegerTraceAnalyzer:
    """Advanced trace analysis for Jaeger."""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._trace_cache: Dict[str, Dict[str, Any]] = {}
        self._performance_stats: Dict[str, List[float]] = {}
    
    def analyze_trace(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trace for performance insights."""
        try:
            trace_id = trace_data.get('traceID')
            if not trace_id:
                return {}
            
            spans = trace_data.get('spans', [])
            if not spans:
                return {}
            
            # Calculate trace metrics
            total_duration = self._calculate_total_duration(spans)
            critical_path = self._find_critical_path(spans)
            bottlenecks = self._identify_bottlenecks(spans)
            service_breakdown = self._analyze_service_breakdown(spans)
            
            analysis = {
                'trace_id': trace_id,
                'total_duration_ms': total_duration,
                'span_count': len(spans),
                'service_count': len(set(span.get('process', {}).get('serviceName') for span in spans)),
                'critical_path': critical_path,
                'bottlenecks': bottlenecks,
                'service_breakdown': service_breakdown,
                'analysis_timestamp': time.time()
            }
            
            # Cache analysis
            self._trace_cache[trace_id] = analysis
            return analysis
            
        except Exception as e:
            self._logger.error(f"Error analyzing trace: {e}")
            return {}
    
    def _calculate_total_duration(self, spans: List[Dict[str, Any]]) -> float:
        """Calculate total trace duration."""
        if not spans:
            return 0.0
        
        min_start = min(span.get('startTime', 0) for span in spans)
        max_end = max(
            span.get('startTime', 0) + span.get('duration', 0) 
            for span in spans
        )
        return (max_end - min_start) / 1000.0  # Convert to milliseconds
    
    def _find_critical_path(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the critical path through the trace."""
        # Build span hierarchy
        span_map = {span['spanID']: span for span in spans}
        root_spans = [span for span in spans if not span.get('references')]
        
        if not root_spans:
            return []
        
        # Find longest path from root
        def find_longest_path(span_id: str, visited: set) -> List[Dict[str, Any]]:
            if span_id in visited:
                return []
            
            visited.add(span_id)
            span = span_map.get(span_id)
            if not span:
                return []
            
            # Find child spans
            children = [
                s for s in spans 
                if any(
                    ref.get('spanID') == span_id 
                    for ref in s.get('references', [])
                )
            ]
            
            if not children:
                return [span]
            
            # Find longest child path
            longest_child_path = []
            for child in children:
                child_path = find_longest_path(child['spanID'], visited.copy())
                if len(child_path) > len(longest_child_path):
                    longest_child_path = child_path
            
            return [span] + longest_child_path
        
        # Find critical path from root span
        root_span = max(root_spans, key=lambda s: s.get('duration', 0))
        critical_path = find_longest_path(root_span['spanID'], set())
        
        return [
            {
                'span_id': span['spanID'],
                'operation_name': span.get('operationName', 'unknown'),
                'service_name': span.get('process', {}).get('serviceName', 'unknown'),
                'duration_ms': span.get('duration', 0) / 1000.0
            }
            for span in critical_path
        ]
    
    def _identify_bottlenecks(self, spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks in the trace."""
        # Sort spans by duration
        sorted_spans = sorted(spans, key=lambda s: s.get('duration', 0), reverse=True)
        
        # Get top 5 slowest spans
        bottlenecks = []
        for span in sorted_spans[:5]:
            duration_ms = span.get('duration', 0) / 1000.0
            if duration_ms > 10:  # Only consider spans > 10ms as potential bottlenecks
                bottlenecks.append({
                    'span_id': span['spanID'],
                    'operation_name': span.get('operationName', 'unknown'),
                    'service_name': span.get('process', {}).get('serviceName', 'unknown'),
                    'duration_ms': duration_ms,
                    'tags': span.get('tags', [])
                })
        
        return bottlenecks
    
    def _analyze_service_breakdown(self, spans: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze time breakdown by service."""
        service_stats = {}
        
        for span in spans:
            service_name = span.get('process', {}).get('serviceName', 'unknown')
            duration_ms = span.get('duration', 0) / 1000.0
            
            if service_name not in service_stats:
                service_stats[service_name] = {
                    'total_duration_ms': 0.0,
                    'span_count': 0,
                    'operations': set()
                }
            
            service_stats[service_name]['total_duration_ms'] += duration_ms
            service_stats[service_name]['span_count'] += 1
            service_stats[service_name]['operations'].add(
                span.get('operationName', 'unknown')
            )
        
        # Convert sets to lists for JSON serialization
        for service_name, stats in service_stats.items():
            stats['operations'] = list(stats['operations'])
            stats['average_duration_ms'] = (
                stats['total_duration_ms'] / stats['span_count']
            )
        
        return service_stats


# Factory functions
def create_jaeger_exporter(config: JaegerConfig) -> AdvancedJaegerExporter:
    """Create advanced Jaeger exporter."""
    exporter = AdvancedJaegerExporter(config)
    exporter.initialize()
    return exporter


def create_jaeger_config_from_tracing_config(tracing_config: TracingConfig) -> JaegerConfig:
    """Create Jaeger config from general tracing config."""
    return JaegerConfig(
        agent_host=tracing_config.jaeger_agent_host,
        agent_port=tracing_config.jaeger_agent_port,
        collector_endpoint=tracing_config.jaeger_endpoint,
        sampling_rate=tracing_config.sampling_rate,
        max_tag_value_length=1024,
        flush_interval=1.0
    )


# Export main classes and functions
__all__ = [
    'JaegerProtocol',
    'JaegerSamplingType',
    'JaegerConfig',
    'AdvancedJaegerExporter',
    'JaegerSamplingManager',
    'JaegerTraceAnalyzer',
    'create_jaeger_exporter',
    'create_jaeger_config_from_tracing_config',
    'JAEGER_AVAILABLE',
]
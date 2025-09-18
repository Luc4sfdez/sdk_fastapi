"""
Log Search and Analysis System for FastAPI Microservices SDK.
This module provides advanced log search, analysis, pattern detection,
and anomaly detection capabilities for enterprise logging systems.
Author: FastAPI Microservices SDK
Version: 1.0.0
"""
import json
import re
import statistics
from typing import Dict, Any, Optional, List, Union, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import defaultdict, Counter
import logging

# Optional dependencies for advanced analysis
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .config import LoggingConfig
from .exceptions import LoggingError


class SearchOperator(str, Enum):
    """Search operator enumeration."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class AggregationType(str, Enum):
    """Aggregation type enumeration."""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT = "distinct"
    PERCENTILE = "percentile"
    HISTOGRAM = "histogram"


class AnomalyType(str, Enum):
    """Anomaly type enumeration."""
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"
    ERROR_RATE_SPIKE = "error_rate_spike"
    RESPONSE_TIME_SPIKE = "response_time_spike"
    UNUSUAL_PATTERN = "unusual_pattern"
    NEW_ERROR_TYPE = "new_error_type"
    SECURITY_ANOMALY = "security_anomaly"


@dataclass
class SearchCriteria:
    """Log search criteria."""
    field: str
    operator: SearchOperator
    value: Any
    case_sensitive: bool = False

    def matches(self, log_data: Dict[str, Any]) -> bool:
        """Check if log data matches this criteria."""
        # Get field value
        field_value = self._get_field_value(log_data, self.field)
        if field_value is None:
            return self.operator in [SearchOperator.NOT_EXISTS, SearchOperator.NOT_EQUALS]

        # Apply case sensitivity
        if isinstance(field_value, str) and not self.case_sensitive:
            field_value = field_value.lower()
            if isinstance(self.value, str):
                compare_value = self.value.lower()
            else:
                compare_value = self.value
        else:
            compare_value = self.value

        # Apply operator
        if self.operator == SearchOperator.EQUALS:
            return field_value == compare_value
        elif self.operator == SearchOperator.NOT_EQUALS:
            return field_value != compare_value
        elif self.operator == SearchOperator.CONTAINS:
            return isinstance(field_value, str) and compare_value in field_value
        elif self.operator == SearchOperator.NOT_CONTAINS:
            return not (isinstance(field_value, str) and compare_value in field_value)
        elif self.operator == SearchOperator.STARTS_WITH:
            return isinstance(field_value, str) and field_value.startswith(compare_value)
        elif self.operator == SearchOperator.ENDS_WITH:
            return isinstance(field_value, str) and field_value.endswith(compare_value)
        elif self.operator == SearchOperator.REGEX:
            if isinstance(field_value, str):
                pattern = re.compile(compare_value, re.IGNORECASE if not self.case_sensitive else 0)
                return bool(pattern.search(field_value))
            return False
        elif self.operator == SearchOperator.GREATER_THAN:
            return field_value > compare_value
        elif self.operator == SearchOperator.LESS_THAN:
            return field_value < compare_value
        elif self.operator == SearchOperator.GREATER_EQUAL:
            return field_value >= compare_value
        elif self.operator == SearchOperator.LESS_EQUAL:
            return field_value <= compare_value
        elif self.operator == SearchOperator.IN:
            return field_value in compare_value
        elif self.operator == SearchOperator.NOT_IN:
            return field_value not in compare_value
        elif self.operator == SearchOperator.EXISTS:
            return True  # Field exists if we got here
        elif self.operator == SearchOperator.NOT_EXISTS:
            return False  # Field exists if we got here

        return False

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        keys = field_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current


@dataclass
class SearchQuery:
    """Log search query."""
    criteria: List[SearchCriteria] = field(default_factory=list)
    time_range: Optional[tuple] = None  # (start_time, end_time)
    limit: Optional[int] = None
    offset: int = 0
    sort_by: Optional[str] = None
    sort_order: str = "desc"  # asc or desc

    def matches(self, log_data: Dict[str, Any]) -> bool:
        """Check if log data matches this query."""
        # Check time range
        if self.time_range:
            log_timestamp = log_data.get('timestamp')
            if log_timestamp:
                try:
                    log_time = datetime.fromisoformat(log_timestamp.replace('Z', '+00:00'))
                    start_time, end_time = self.time_range
                    if not (start_time <= log_time <= end_time):
                        return False
                except (ValueError, TypeError):
                    pass

        # Check all criteria (AND logic)
        for criteria in self.criteria:
            if not criteria.matches(log_data):
                return False

        return True


@dataclass
class SearchResult:
    """Search result container."""
    logs: List[Dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    query_time_ms: float = 0.0
    aggregations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'logs': self.logs,
            'total_count': self.total_count,
            'query_time_ms': self.query_time_ms,
            'aggregations': self.aggregations
        }


@dataclass
class PatternMatch:
    """Pattern match result."""
    pattern_name: str
    pattern_regex: str
    matches: List[Dict[str, Any]] = field(default_factory=list)
    match_count: int = 0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pattern_name': self.pattern_name,
            'pattern_regex': self.pattern_regex,
            'matches': self.matches,
            'match_count': self.match_count,
            'confidence': self.confidence
        }


@dataclass
class Anomaly:
    """Anomaly detection result."""
    anomaly_type: AnomalyType
    description: str
    severity: str  # low, medium, high, critical
    timestamp: datetime
    affected_logs: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'anomaly_type': self.anomaly_type.value,
            'description': self.description,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'affected_logs': self.affected_logs,
            'metrics': self.metrics,
            'confidence': self.confidence
        }


class LogSearchEngine:
    """Advanced log search engine."""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Search statistics
        self._search_count = 0
        self._total_search_time = 0.0
        self._cache_hits = 0

        # Simple cache for frequent queries
        self._query_cache: Dict[str, SearchResult] = {}
        self._cache_max_size = 100

    def search(
        self,
        query: SearchQuery,
        log_source: Union[str, Iterator[Dict[str, Any]]]
    ) -> SearchResult:
        """Search logs with given query."""
        import time
        start_time = time.time()

        try:
            # Check cache
            query_hash = self._hash_query(query)
            if query_hash in self._query_cache:
                self._cache_hits += 1
                return self._query_cache[query_hash]

            # Execute search
            if isinstance(log_source, str):
                # File-based search
                result = self._search_file(query, log_source)
            else:
                # Iterator-based search
                result = self._search_iterator(query, log_source)

            # Update statistics
            query_time = (time.time() - start_time) * 1000
            result.query_time_ms = query_time
            self._search_count += 1
            self._total_search_time += query_time

            # Cache result
            self._cache_result(query_hash, result)

            return result

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            raise LoggingError(f"Search failed: {e}", original_error=e)

    def _search_file(self, query: SearchQuery, file_path: str) -> SearchResult:
        """Search logs in file."""
        result = SearchResult()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    if line_num < query.offset:
                        continue
                    if query.limit and len(result.logs) >= query.limit:
                        break

                    try:
                        log_data = json.loads(line.strip())
                        if query.matches(log_data):
                            result.logs.append(log_data)
                            result.total_count += 1
                    except json.JSONDecodeError:
                        continue

            # Sort results
            if query.sort_by and result.logs:
                reverse = query.sort_order == "desc"
                result.logs.sort(
                    key=lambda x: x.get(query.sort_by, ''),
                    reverse=reverse
                )

        except Exception as e:
            raise LoggingError(f"Failed to search file {file_path}: {e}")

        return result

    def _search_iterator(self, query: SearchQuery, log_iterator: Iterator[Dict[str, Any]]) -> SearchResult:
        """Search logs from iterator."""
        result = SearchResult()
        processed = 0

        for log_data in log_iterator:
            if processed < query.offset:
                processed += 1
                continue
            if query.limit and len(result.logs) >= query.limit:
                break

            if query.matches(log_data):
                result.logs.append(log_data)
                result.total_count += 1
            processed += 1

        # Sort results
        if query.sort_by and result.logs:
            reverse = query.sort_order == "desc"
            result.logs.sort(
                key=lambda x: x.get(query.sort_by, ''),
                reverse=reverse
            )

        return result

    def aggregate(
        self,
        query: SearchQuery,
        log_source: Union[str, Iterator[Dict[str, Any]]],
        aggregations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform aggregations on search results."""
        # First get matching logs
        search_result = self.search(query, log_source)
        logs = search_result.logs

        results = {}
        for agg_name, agg_config in aggregations.items():
            agg_type = AggregationType(agg_config['type'])
            field = agg_config['field']

            # Extract field values
            values = []
            for log in logs:
                value = self._get_field_value(log, field)
                if value is not None:
                    values.append(value)

            # Perform aggregation
            if agg_type == AggregationType.COUNT:
                results[agg_name] = len(values)
            elif agg_type == AggregationType.DISTINCT:
                results[agg_name] = len(set(values))
            elif agg_type == AggregationType.SUM:
                results[agg_name] = sum(v for v in values if isinstance(v, (int, float)))
            elif agg_type == AggregationType.AVG:
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                results[agg_name] = statistics.mean(numeric_values) if numeric_values else 0
            elif agg_type == AggregationType.MIN:
                results[agg_name] = min(values) if values else None
            elif agg_type == AggregationType.MAX:
                results[agg_name] = max(values) if values else None
            elif agg_type == AggregationType.PERCENTILE:
                percentile = agg_config.get('percentile', 50)
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    results[agg_name] = statistics.quantiles(numeric_values, n=100)[percentile-1]
                else:
                    results[agg_name] = None
            elif agg_type == AggregationType.HISTOGRAM:
                # Simple histogram implementation
                counter = Counter(values)
                results[agg_name] = dict(counter.most_common())

        return results

    def _get_field_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        keys = field_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _hash_query(self, query: SearchQuery) -> str:
        """Create hash for query caching."""
        import hashlib
        query_str = json.dumps({
            'criteria': [(c.field, c.operator.value, c.value) for c in query.criteria],
            'time_range': query.time_range,
            'limit': query.limit,
            'offset': query.offset,
            'sort_by': query.sort_by,
            'sort_order': query.sort_order
        }, sort_keys=True, default=str)
        return hashlib.md5(query_str.encode()).hexdigest()

    def _cache_result(self, query_hash: str, result: SearchResult):
        """Cache search result."""
        if len(self._query_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]
        self._query_cache[query_hash] = result

    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        avg_search_time = self._total_search_time / max(1, self._search_count)
        return {
            'total_searches': self._search_count,
            'total_search_time_ms': self._total_search_time,
            'average_search_time_ms': avg_search_time,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': self._cache_hits / max(1, self._search_count),
            'cached_queries': len(self._query_cache)
        }


class PatternDetector:
    """Log pattern detection system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Predefined patterns
        self.patterns = {
            'error_patterns': [
                (r'Exception|Error|Failed|Failure', 'error_keywords'),
                (r'HTTP [45]\d\d', 'http_errors'),
                (r'timeout|timed out', 'timeout_errors'),
                (r'connection refused|connection failed', 'connection_errors'),
                (r'out of memory|memory error', 'memory_errors'),
                (r'permission denied|access denied', 'permission_errors')
            ],
            'security_patterns': [
                (r'login failed|authentication failed', 'failed_authentication'),
                (r'unauthorized|forbidden', 'unauthorized_access'),
                (r'sql injection|xss|csrf', 'security_attacks'),
                (r'brute force|multiple failed attempts', 'brute_force'),
                (r'privilege escalation', 'privilege_escalation')
            ],
            'performance_patterns': [
                (r'slow query|query timeout', 'slow_queries'),
                (r'high cpu|cpu spike', 'cpu_issues'),
                (r'memory leak|high memory', 'memory_issues'),
                (r'disk full|disk space', 'disk_issues'),
                (r'response time|latency', 'performance_metrics')
            ]
        }

    def detect_patterns(
        self,
        logs: List[Dict[str, Any]],
        pattern_categories: Optional[List[str]] = None
    ) -> List[PatternMatch]:
        """Detect patterns in logs."""
        if pattern_categories is None:
            pattern_categories = list(self.patterns.keys())

        results = []
        for category in pattern_categories:
            if category not in self.patterns:
                continue

            for pattern_regex, pattern_name in self.patterns[category]:
                matches = self._find_pattern_matches(logs, pattern_regex, pattern_name)
                if matches.match_count > 0:
                    results.append(matches)

        return results

    def _find_pattern_matches(
        self,
        logs: List[Dict[str, Any]],
        pattern_regex: str,
        pattern_name: str
    ) -> PatternMatch:
        """Find matches for a specific pattern."""
        pattern = re.compile(pattern_regex, re.IGNORECASE)
        matches = []

        for log in logs:
            # Check message field
            message = log.get('message', '')
            if isinstance(message, str) and pattern.search(message):
                matches.append(log)

        # Calculate confidence based on match frequency
        confidence = min(len(matches) / max(1, len(logs)), 1.0)

        return PatternMatch(
            pattern_name=pattern_name,
            pattern_regex=pattern_regex,
            matches=matches,
            match_count=len(matches),
            confidence=confidence
        )

    def add_custom_pattern(self, category: str, pattern_regex: str, pattern_name: str):
        """Add custom pattern."""
        if category not in self.patterns:
            self.patterns[category] = []
        self.patterns[category].append((pattern_regex, pattern_name))


class AnomalyDetector:
    """Log anomaly detection system."""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Baseline metrics
        self._baseline_metrics = {}
        self._learning_window = 1000  # Number of logs for baseline

    def detect_anomalies(
        self,
        logs: List[Dict[str, Any]],
        time_window_minutes: int = 60
    ) -> List[Anomaly]:
        """Detect anomalies in logs."""
        anomalies = []

        # Group logs by time windows
        time_groups = self._group_logs_by_time(logs, time_window_minutes)

        for time_window, window_logs in time_groups.items():
            # Volume anomalies
            volume_anomalies = self._detect_volume_anomalies(window_logs, time_window)
            anomalies.extend(volume_anomalies)

            # Error rate anomalies
            error_anomalies = self._detect_error_rate_anomalies(window_logs, time_window)
            anomalies.extend(error_anomalies)

            # Response time anomalies
            response_time_anomalies = self._detect_response_time_anomalies(window_logs, time_window)
            anomalies.extend(response_time_anomalies)

            # Pattern anomalies
            pattern_anomalies = self._detect_pattern_anomalies(window_logs, time_window)
            anomalies.extend(pattern_anomalies)

        return anomalies

    def _group_logs_by_time(
        self,
        logs: List[Dict[str, Any]],
        window_minutes: int
    ) -> Dict[datetime, List[Dict[str, Any]]]:
        """Group logs by time windows."""
        groups = defaultdict(list)

        for log in logs:
            timestamp_str = log.get('timestamp')
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Round to window boundary
                window_start = timestamp.replace(
                    minute=(timestamp.minute // window_minutes) * window_minutes,
                    second=0,
                    microsecond=0
                )
                groups[window_start].append(log)
            except (ValueError, TypeError):
                continue

        return dict(groups)

    def _detect_volume_anomalies(
        self,
        logs: List[Dict[str, Any]],
        time_window: datetime
    ) -> List[Anomaly]:
        """Detect volume anomalies."""
        anomalies = []
        current_volume = len(logs)

        # Get baseline volume
        baseline_volume = self._baseline_metrics.get('volume', current_volume)

        # Calculate threshold (3 standard deviations)
        volume_threshold = baseline_volume * 3

        if current_volume > volume_threshold:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                description=f"Log volume spike detected: {current_volume} logs (baseline: {baseline_volume})",
                severity="high" if current_volume > volume_threshold * 2 else "medium",
                timestamp=time_window,
                affected_logs=logs[:10],  # Sample of affected logs
                metrics={
                    'current_volume': current_volume,
                    'baseline_volume': baseline_volume,
                    'threshold': volume_threshold
                },
                confidence=min((current_volume - baseline_volume) / baseline_volume, 1.0)
            ))
        elif current_volume < baseline_volume * 0.1:  # 90% drop
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.VOLUME_DROP,
                description=f"Log volume drop detected: {current_volume} logs (baseline: {baseline_volume})",
                severity="medium",
                timestamp=time_window,
                affected_logs=[],
                metrics={
                    'current_volume': current_volume,
                    'baseline_volume': baseline_volume
                },
                confidence=1.0 - (current_volume / baseline_volume)
            ))

        return anomalies

    def _detect_error_rate_anomalies(
        self,
        logs: List[Dict[str, Any]],
        time_window: datetime
    ) -> List[Anomaly]:
        """Detect error rate anomalies."""
        anomalies = []

        if not logs:
            return anomalies

        # Count error logs
        error_logs = [log for log in logs if log.get('level', '').upper() in ['ERROR', 'CRITICAL']]
        error_rate = len(error_logs) / len(logs)

        # Get baseline error rate
        baseline_error_rate = self._baseline_metrics.get('error_rate', 0.01)  # 1% default

        # Threshold: 5x baseline or minimum 10%
        error_threshold = max(baseline_error_rate * 5, 0.1)

        if error_rate > error_threshold:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.ERROR_RATE_SPIKE,
                description=f"Error rate spike detected: {error_rate:.2%} (baseline: {baseline_error_rate:.2%})",
                severity="critical" if error_rate > 0.5 else "high",
                timestamp=time_window,
                affected_logs=error_logs[:10],
                metrics={
                    'current_error_rate': error_rate,
                    'baseline_error_rate': baseline_error_rate,
                    'error_count': len(error_logs),
                    'total_logs': len(logs)
                },
                confidence=min(error_rate / baseline_error_rate, 1.0)
            ))

        return anomalies

    def _detect_response_time_anomalies(
        self,
        logs: List[Dict[str, Any]],
        time_window: datetime
    ) -> List[Anomaly]:
        """Detect response time anomalies."""
        anomalies = []

        # Extract response times
        response_times = []
        for log in logs:
            response_time = log.get('response_time')
            if isinstance(response_time, (int, float)):
                response_times.append(response_time)

        if not response_times:
            return anomalies

        # Calculate current metrics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        # Get baseline metrics
        baseline_avg = self._baseline_metrics.get('avg_response_time', avg_response_time)
        baseline_max = self._baseline_metrics.get('max_response_time', max_response_time)

        # Thresholds
        avg_threshold = baseline_avg * 3
        max_threshold = baseline_max * 2

        if avg_response_time > avg_threshold or max_response_time > max_threshold:
            slow_logs = [log for log in logs if log.get('response_time', 0) > avg_threshold]

            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.RESPONSE_TIME_SPIKE,
                description=f"Response time spike detected: avg {avg_response_time:.2f}ms, max {max_response_time:.2f}ms",
                severity="high" if avg_response_time > avg_threshold * 2 else "medium",
                timestamp=time_window,
                affected_logs=slow_logs[:10],
                metrics={
                    'current_avg_response_time': avg_response_time,
                    'current_max_response_time': max_response_time,
                    'baseline_avg_response_time': baseline_avg,
                    'baseline_max_response_time': baseline_max
                },
                confidence=min(avg_response_time / baseline_avg, 1.0)
            ))

        return anomalies

    def _detect_pattern_anomalies(
        self,
        logs: List[Dict[str, Any]],
        time_window: datetime
    ) -> List[Anomaly]:
        """Detect unusual patterns."""
        anomalies = []

        # Extract unique error messages
        error_messages = set()
        for log in logs:
            if log.get('level', '').upper() in ['ERROR', 'CRITICAL']:
                message = log.get('message', '')
                if message:
                    error_messages.add(message)

        # Check for new error types
        baseline_errors = self._baseline_metrics.get('error_messages', set())
        new_errors = error_messages - baseline_errors

        if new_errors:
            new_error_logs = [
                log for log in logs
                if log.get('level', '').upper() in ['ERROR', 'CRITICAL']
                and log.get('message', '') in new_errors
            ]

            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.NEW_ERROR_TYPE,
                description=f"New error types detected: {len(new_errors)} unique errors",
                severity="medium",
                timestamp=time_window,
                affected_logs=new_error_logs[:10],
                metrics={
                    'new_error_count': len(new_errors),
                    'new_error_messages': list(new_errors)[:5]  # Sample
                },
                confidence=len(new_errors) / max(1, len(error_messages))
            ))

        return anomalies

    def update_baseline(self, logs: List[Dict[str, Any]]):
        """Update baseline metrics from logs."""
        if len(logs) < self._learning_window:
            return

        # Calculate volume baseline
        self._baseline_metrics['volume'] = len(logs) / max(1, len(logs) // 100)  # Per 100 logs

        # Calculate error rate baseline
        error_logs = [log for log in logs if log.get('level', '').upper() in ['ERROR', 'CRITICAL']]
        self._baseline_metrics['error_rate'] = len(error_logs) / len(logs)

        # Calculate response time baseline
        response_times = [
            log.get('response_time') for log in logs
            if isinstance(log.get('response_time'), (int, float))
        ]
        if response_times:
            self._baseline_metrics['avg_response_time'] = statistics.mean(response_times)
            self._baseline_metrics['max_response_time'] = max(response_times)

        # Store error message patterns
        error_messages = set()
        for log in logs:
            if log.get('level', '').upper() in ['ERROR', 'CRITICAL']:
                message = log.get('message', '')
                if message:
                    error_messages.add(message)
        self._baseline_metrics['error_messages'] = error_messages

        self.logger.info(f"Updated baseline metrics from {len(logs)} logs")


# Factory functions
def create_search_engine(config: LoggingConfig) -> LogSearchEngine:
    """Create log search engine."""
    return LogSearchEngine(config)


def create_pattern_detector() -> PatternDetector:
    """Create pattern detector."""
    return PatternDetector()


def create_anomaly_detector(config: LoggingConfig) -> AnomalyDetector:
    """Create anomaly detector."""
    return AnomalyDetector(config)


# Export main classes and functions
__all__ = [
    'SearchOperator',
    'AggregationType',
    'AnomalyType',
    'SearchCriteria',
    'SearchQuery',
    'SearchResult',
    'PatternMatch',
    'Anomaly',
    'LogSearchEngine',
    'PatternDetector',
    'AnomalyDetector',
    'create_search_engine',
    'create_pattern_detector',
    'create_anomaly_detector',
]
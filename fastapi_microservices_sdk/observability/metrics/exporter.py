"""
Prometheus metrics exporter.

This module provides exporters for metrics in Prometheus format,
including HTTP endpoint and file-based export capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union, TextIO
from datetime import datetime, timezone
from io import StringIO

from .registry import MetricRegistry, get_global_registry
from .types import BaseMetric, Counter, Gauge, Histogram, Summary, MetricType
from .exceptions import MetricsExportError, PrometheusIntegrationError


class PrometheusFormatter:
    """Formatter for Prometheus exposition format."""
    
    @staticmethod
    def format_metric_name(name: str) -> str:
        """Format metric name for Prometheus."""
        # Replace invalid characters with underscores
        formatted = ""
        for char in name:
            if char.isalnum() or char in ['_', ':']:
                formatted += char
            else:
                formatted += '_'
        return formatted
    
    @staticmethod
    def format_label_value(value: str) -> str:
        """Format label value for Prometheus (escape special characters)."""
        # Escape backslashes and quotes
        escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return f'"{escaped}"'
    
    @staticmethod
    def format_labels(labels: Dict[str, str]) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        
        formatted_labels = []
        for key, value in sorted(labels.items()):
            formatted_value = PrometheusFormatter.format_label_value(value)
            formatted_labels.append(f'{key}={formatted_value}')
        
        return "{" + ",".join(formatted_labels) + "}"
    
    @staticmethod
    def format_value(value: Union[int, float]) -> str:
        """Format numeric value for Prometheus."""
        if isinstance(value, float):
            if value == float('inf'):
                return '+Inf'
            elif value == float('-inf'):
                return '-Inf'
            elif value != value:  # NaN check
                return 'NaN'
        return str(value)
    
    @staticmethod
    def format_timestamp(timestamp: Optional[float] = None) -> str:
        """Format timestamp for Prometheus."""
        if timestamp is None:
            timestamp = time.time()
        return str(int(timestamp * 1000))  # Prometheus expects milliseconds


class PrometheusExporter:
    """Exporter for Prometheus metrics format."""
    
    def __init__(self, registry: Optional[MetricRegistry] = None):
        self.registry = registry or get_global_registry()
        self.logger = logging.getLogger("observability.prometheus_exporter")
        self.formatter = PrometheusFormatter()
        
        # Export statistics
        self.exports_total = 0
        self.export_errors = 0
        self.last_export_time = 0.0
        self.export_duration_seconds = 0.0
    
    def export_metrics(self, include_timestamp: bool = False) -> str:
        """Export all metrics in Prometheus format."""
        try:
            start_time = time.time()
            output = StringIO()
            
            metrics = self.registry.get_all_metrics()
            
            for name, metric in metrics.items():
                try:
                    self._export_metric(output, metric, include_timestamp)
                except Exception as e:
                    self.logger.error(f"Failed to export metric {name}: {e}")
                    self.export_errors += 1
            
            result = output.getvalue()
            
            # Update statistics
            self.export_duration_seconds = time.time() - start_time
            self.last_export_time = time.time()
            self.exports_total += 1
            
            return result
            
        except Exception as e:
            self.export_errors += 1
            raise MetricsExportError(
                message=f"Failed to export metrics: {str(e)}",
                export_destination="prometheus",
                export_format="text",
                original_error=e
            )
    
    def export_metric(self, metric: BaseMetric, include_timestamp: bool = False) -> str:
        """Export a single metric in Prometheus format."""
        try:
            output = StringIO()
            self._export_metric(output, metric, include_timestamp)
            return output.getvalue()
        except Exception as e:
            raise MetricsExportError(
                message=f"Failed to export metric {metric.name}: {str(e)}",
                metric_name=metric.name,
                export_format="prometheus",
                original_error=e
            )
    
    def _export_metric(self, output: TextIO, metric: BaseMetric, include_timestamp: bool = False) -> None:
        """Export a single metric to the output stream."""
        metric_name = self.formatter.format_metric_name(metric.name)
        
        # Write HELP comment
        if metric.description:
            output.write(f"# HELP {metric_name} {metric.description}\n")
        
        # Write TYPE comment
        metric_type = self._get_prometheus_type(metric.get_type())
        output.write(f"# TYPE {metric_name} {metric_type}\n")
        
        # Export metric data based on type
        if isinstance(metric, Counter):
            self._export_counter(output, metric, metric_name, include_timestamp)
        elif isinstance(metric, Gauge):
            self._export_gauge(output, metric, metric_name, include_timestamp)
        elif isinstance(metric, Histogram):
            self._export_histogram(output, metric, metric_name, include_timestamp)
        elif isinstance(metric, Summary):
            self._export_summary(output, metric, metric_name, include_timestamp)
    
    def _export_counter(self, output: TextIO, counter: Counter, metric_name: str, include_timestamp: bool) -> None:
        """Export counter metric."""
        all_values = counter.get_all_values()
        
        if not all_values:
            # Export zero value with no labels
            timestamp = self.formatter.format_timestamp() if include_timestamp else ""
            output.write(f"{metric_name} 0 {timestamp}\n".strip() + "\n")
        else:
            for label_key, value in all_values.items():
                labels = self._parse_label_key(label_key)
                labels_str = self.formatter.format_labels(labels)
                value_str = self.formatter.format_value(value)
                timestamp = self.formatter.format_timestamp() if include_timestamp else ""
                
                output.write(f"{metric_name}{labels_str} {value_str} {timestamp}\n".strip() + "\n")
    
    def _export_gauge(self, output: TextIO, gauge: Gauge, metric_name: str, include_timestamp: bool) -> None:
        """Export gauge metric."""
        all_values = gauge.get_all_values()
        
        if not all_values:
            # Export zero value with no labels
            timestamp = self.formatter.format_timestamp() if include_timestamp else ""
            output.write(f"{metric_name} 0 {timestamp}\n".strip() + "\n")
        else:
            for label_key, value in all_values.items():
                labels = self._parse_label_key(label_key)
                labels_str = self.formatter.format_labels(labels)
                value_str = self.formatter.format_value(value)
                timestamp = self.formatter.format_timestamp() if include_timestamp else ""
                
                output.write(f"{metric_name}{labels_str} {value_str} {timestamp}\n".strip() + "\n")
    
    def _export_histogram(self, output: TextIO, histogram: Histogram, metric_name: str, include_timestamp: bool) -> None:
        """Export histogram metric."""
        all_values = histogram.get_all_values()
        
        if not all_values:
            # Export empty histogram
            timestamp = self.formatter.format_timestamp() if include_timestamp else ""
            output.write(f"{metric_name}_count 0 {timestamp}\n".strip() + "\n")
            output.write(f"{metric_name}_sum 0 {timestamp}\n".strip() + "\n")
            
            # Export buckets
            for bucket in histogram.buckets:
                bucket_str = self.formatter.format_value(bucket)
                bucket_labels = self.formatter.format_labels({"le": str(bucket)})
                output.write(f"{metric_name}_bucket{bucket_labels} 0 {timestamp}\n".strip() + "\n")
        else:
            for label_key, stats in all_values.items():
                labels = self._parse_label_key(label_key)
                labels_str = self.formatter.format_labels(labels)
                timestamp = self.formatter.format_timestamp() if include_timestamp else ""
                
                # Export count and sum
                count_str = self.formatter.format_value(stats['count'])
                sum_str = self.formatter.format_value(stats['sum'])
                
                output.write(f"{metric_name}_count{labels_str} {count_str} {timestamp}\n".strip() + "\n")
                output.write(f"{metric_name}_sum{labels_str} {sum_str} {timestamp}\n".strip() + "\n")
                
                # Export buckets
                for bucket, bucket_count in stats['buckets'].items():
                    bucket_labels = dict(labels)
                    bucket_labels['le'] = str(bucket)
                    bucket_labels_str = self.formatter.format_labels(bucket_labels)
                    bucket_count_str = self.formatter.format_value(bucket_count)
                    
                    output.write(f"{metric_name}_bucket{bucket_labels_str} {bucket_count_str} {timestamp}\n".strip() + "\n")
    
    def _export_summary(self, output: TextIO, summary: Summary, metric_name: str, include_timestamp: bool) -> None:
        """Export summary metric."""
        all_values = summary.get_all_values()
        
        if not all_values:
            # Export empty summary
            timestamp = self.formatter.format_timestamp() if include_timestamp else ""
            output.write(f"{metric_name}_count 0 {timestamp}\n".strip() + "\n")
            output.write(f"{metric_name}_sum 0 {timestamp}\n".strip() + "\n")
            
            # Export quantiles
            for quantile in summary.quantiles:
                quantile_labels = self.formatter.format_labels({"quantile": str(quantile)})
                output.write(f"{metric_name}{quantile_labels} 0 {timestamp}\n".strip() + "\n")
        else:
            for label_key, stats in all_values.items():
                labels = self._parse_label_key(label_key)
                labels_str = self.formatter.format_labels(labels)
                timestamp = self.formatter.format_timestamp() if include_timestamp else ""
                
                # Export count and sum
                count_str = self.formatter.format_value(stats['count'])
                sum_str = self.formatter.format_value(stats['sum'])
                
                output.write(f"{metric_name}_count{labels_str} {count_str} {timestamp}\n".strip() + "\n")
                output.write(f"{metric_name}_sum{labels_str} {sum_str} {timestamp}\n".strip() + "\n")
                
                # Export quantiles
                for quantile, value in stats['quantiles'].items():
                    quantile_labels = dict(labels)
                    quantile_labels['quantile'] = str(quantile)
                    quantile_labels_str = self.formatter.format_labels(quantile_labels)
                    value_str = self.formatter.format_value(value)
                    
                    output.write(f"{metric_name}{quantile_labels_str} {value_str} {timestamp}\n".strip() + "\n")
    
    def _get_prometheus_type(self, metric_type: MetricType) -> str:
        """Get Prometheus type string for metric type."""
        type_mapping = {
            MetricType.COUNTER: "counter",
            MetricType.GAUGE: "gauge",
            MetricType.HISTOGRAM: "histogram",
            MetricType.SUMMARY: "summary"
        }
        return type_mapping.get(metric_type, "untyped")
    
    def _parse_label_key(self, label_key: str) -> Dict[str, str]:
        """Parse label key back to labels dict."""
        if not label_key:
            return {}
        
        labels = {}
        for item in label_key.split(','):
            if '=' in item:
                key, value = item.split('=', 1)
                labels[key] = value
        
        return labels
    
    def get_export_statistics(self) -> Dict[str, Any]:
        """Get export statistics."""
        return {
            'exports_total': self.exports_total,
            'export_errors': self.export_errors,
            'error_rate': self.export_errors / max(1, self.exports_total),
            'last_export_time': self.last_export_time,
            'export_duration_seconds': self.export_duration_seconds
        }


class MetricsExporter:
    """Generic metrics exporter with multiple format support."""
    
    def __init__(self, registry: Optional[MetricRegistry] = None):
        self.registry = registry or get_global_registry()
        self.prometheus_exporter = PrometheusExporter(registry)
        self.logger = logging.getLogger("observability.metrics_exporter")
    
    def export(self, format_type: str = "prometheus", **kwargs) -> str:
        """Export metrics in the specified format."""
        if format_type.lower() == "prometheus":
            return self.prometheus_exporter.export_metrics(
                include_timestamp=kwargs.get('include_timestamp', False)
            )
        else:
            raise MetricsExportError(
                message=f"Unsupported export format: {format_type}",
                export_format=format_type
            )
    
    def export_to_file(self, file_path: str, format_type: str = "prometheus", **kwargs) -> None:
        """Export metrics to a file."""
        try:
            content = self.export(format_type, **kwargs)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.logger.info(f"Metrics exported to {file_path}")
            
        except Exception as e:
            raise MetricsExportError(
                message=f"Failed to export metrics to file {file_path}: {str(e)}",
                export_destination=file_path,
                export_format=format_type,
                original_error=e
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get exporter statistics."""
        return {
            'prometheus': self.prometheus_exporter.get_export_statistics()
        }


# Factory functions

def create_prometheus_exporter(registry: Optional[MetricRegistry] = None) -> PrometheusExporter:
    """Create a Prometheus exporter."""
    return PrometheusExporter(registry)


def create_metrics_exporter(registry: Optional[MetricRegistry] = None) -> MetricsExporter:
    """Create a generic metrics exporter."""
    return MetricsExporter(registry)
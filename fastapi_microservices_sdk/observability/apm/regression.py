"""
Performance Regression Detection for FastAPI Microservices SDK.

This module provides performance regression detection for CI/CD pipelines
and continuous performance monitoring.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
from scipy import stats
from collections import defaultdict, deque

from .config import APMConfig
from .exceptions import RegressionDetectionError


class RegressionSeverity(str, Enum):
    """Regression severity enumeration."""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class PerformanceRegression:
    """Performance regression detection result."""
    regression_id: str
    metric_name: str
    baseline_version: str
    current_version: str
    regression_detected: bool
    severity: RegressionSeverity
    performance_change_percent: float
    baseline_mean: float
    current_mean: float
    statistical_significance: float
    detection_method: str
    detected_at: datetime
    confidence_level: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'regression_id': self.regression_id,
            'metric_name': self.metric_name,
            'baseline_version': self.baseline_version,
            'current_version': self.current_version,
            'regression_detected': self.regression_detected,
            'severity': self.severity.value,
            'performance_change_percent': self.performance_change_percent,
            'baseline_mean': self.baseline_mean,
            'current_mean': self.current_mean,
            'statistical_significance': self.statistical_significance,
            'detection_method': self.detection_method,
            'detected_at': self.detected_at.isoformat(),
            'confidence_level': self.confidence_level
        }


@dataclass
class RegressionReport:
    """Regression detection report."""
    report_id: str
    baseline_version: str
    current_version: str
    generated_at: datetime
    regressions: List[PerformanceRegression]
    overall_status: str  # "pass", "warning", "fail"
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'baseline_version': self.baseline_version,
            'current_version': self.current_version,
            'generated_at': self.generated_at.isoformat(),
            'regressions': [r.to_dict() for r in self.regressions],
            'overall_status': self.overall_status,
            'summary': self.summary
        }


class RegressionDetector:
    """Performance regression detection system."""
    
    def __init__(self, config: APMConfig):
        """Initialize regression detector."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Regression detection state
        self.regression_history: List[PerformanceRegression] = []
        self.baseline_data: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
        
        # Version tracking
        self.current_version = "unknown"
        self.baseline_version = "unknown"
        
        # Performance data by version
        self.version_metrics: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: defaultdict(lambda: deque(maxlen=1000))
        )
    
    async def set_baseline_version(self, version: str, metrics_data: Dict[str, List[float]]):
        """Set baseline version and its performance data."""
        try:
            self.baseline_version = version
            
            for metric_name, values in metrics_data.items():
                self.baseline_data[version][metric_name] = values
            
            self.logger.info(f"Set baseline version: {version}")
            
        except Exception as e:
            self.logger.error(f"Error setting baseline version: {e}")
            raise RegressionDetectionError(
                f"Failed to set baseline version: {e}",
                baseline_version=version,
                original_error=e
            )
    
    async def set_current_version(self, version: str):
        """Set current version for comparison."""
        self.current_version = version
        self.logger.info(f"Set current version: {version}")
    
    async def add_performance_data(self, version: str, metric_name: str, value: float):
        """Add performance data for a specific version."""
        try:
            self.version_metrics[version][metric_name].append(value)
            
        except Exception as e:
            self.logger.error(f"Error adding performance data: {e}")
    
    async def detect_regression(self, metric_name: str, baseline_version: Optional[str] = None, current_version: Optional[str] = None) -> Optional[PerformanceRegression]:
        """Detect performance regression for a specific metric."""
        try:
            baseline_ver = baseline_version or self.baseline_version
            current_ver = current_version or self.current_version
            
            if baseline_ver == "unknown" or current_ver == "unknown":
                raise RegressionDetectionError("Baseline or current version not set")
            
            # Get baseline data
            baseline_data = None
            if baseline_ver in self.baseline_data and metric_name in self.baseline_data[baseline_ver]:
                baseline_data = self.baseline_data[baseline_ver][metric_name]
            elif baseline_ver in self.version_metrics and metric_name in self.version_metrics[baseline_ver]:
                baseline_data = list(self.version_metrics[baseline_ver][metric_name])
            
            if not baseline_data or len(baseline_data) < self.config.regression.min_samples:
                return None
            
            # Get current data
            current_data = list(self.version_metrics[current_ver].get(metric_name, []))
            
            if len(current_data) < self.config.regression.min_samples:
                return None
            
            # Perform regression detection
            regression_result = await self._perform_regression_analysis(
                metric_name, baseline_data, current_data, baseline_ver, current_ver
            )
            
            if regression_result:
                self.regression_history.append(regression_result)
                
                # Maintain history size
                if len(self.regression_history) > 1000:
                    self.regression_history = self.regression_history[-1000:]
            
            return regression_result
            
        except Exception as e:
            self.logger.error(f"Error detecting regression for {metric_name}: {e}")
            raise RegressionDetectionError(
                f"Failed to detect regression: {e}",
                baseline_version=baseline_version,
                current_version=current_version,
                original_error=e
            )
    
    async def detect_all_regressions(self, baseline_version: Optional[str] = None, current_version: Optional[str] = None) -> List[PerformanceRegression]:
        """Detect regressions for all available metrics."""
        try:
            baseline_ver = baseline_version or self.baseline_version
            current_ver = current_version or self.current_version
            
            regressions = []
            
            # Get all metrics that exist in both versions
            baseline_metrics = set()
            if baseline_ver in self.baseline_data:
                baseline_metrics.update(self.baseline_data[baseline_ver].keys())
            if baseline_ver in self.version_metrics:
                baseline_metrics.update(self.version_metrics[baseline_ver].keys())
            
            current_metrics = set(self.version_metrics[current_ver].keys())
            common_metrics = baseline_metrics & current_metrics
            
            for metric_name in common_metrics:
                regression = await self.detect_regression(metric_name, baseline_ver, current_ver)
                if regression:
                    regressions.append(regression)
            
            return regressions
            
        except Exception as e:
            self.logger.error(f"Error detecting all regressions: {e}")
            raise RegressionDetectionError(
                f"Failed to detect all regressions: {e}",
                original_error=e
            )
    
    async def generate_regression_report(self, baseline_version: Optional[str] = None, current_version: Optional[str] = None) -> RegressionReport:
        """Generate comprehensive regression report."""
        try:
            baseline_ver = baseline_version or self.baseline_version
            current_ver = current_version or self.current_version
            
            # Detect all regressions
            regressions = await self.detect_all_regressions(baseline_ver, current_ver)
            
            # Determine overall status
            critical_regressions = [r for r in regressions if r.severity == RegressionSeverity.CRITICAL]
            major_regressions = [r for r in regressions if r.severity == RegressionSeverity.MAJOR]
            
            if critical_regressions:
                overall_status = "fail"
            elif major_regressions:
                overall_status = "warning"
            else:
                overall_status = "pass"
            
            # Generate summary
            summary = {
                'total_metrics_compared': len(set(r.metric_name for r in regressions)),
                'regressions_detected': len([r for r in regressions if r.regression_detected]),
                'critical_regressions': len(critical_regressions),
                'major_regressions': len(major_regressions),
                'moderate_regressions': len([r for r in regressions if r.severity == RegressionSeverity.MODERATE]),
                'minor_regressions': len([r for r in regressions if r.severity == RegressionSeverity.MINOR]),
                'average_performance_change': statistics.mean([r.performance_change_percent for r in regressions]) if regressions else 0.0
            }
            
            report_id = f"regression_report_{int(datetime.now().timestamp())}"
            
            report = RegressionReport(
                report_id=report_id,
                baseline_version=baseline_ver,
                current_version=current_ver,
                generated_at=datetime.now(timezone.utc),
                regressions=regressions,
                overall_status=overall_status,
                summary=summary
            )
            
            self.logger.info(f"Generated regression report: {overall_status} ({len(regressions)} regressions)")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating regression report: {e}")
            raise RegressionDetectionError(
                f"Failed to generate regression report: {e}",
                original_error=e
            )
    
    async def _perform_regression_analysis(
        self,
        metric_name: str,
        baseline_data: List[float],
        current_data: List[float],
        baseline_version: str,
        current_version: str
    ) -> Optional[PerformanceRegression]:
        """Perform statistical regression analysis."""
        try:
            # Calculate basic statistics
            baseline_mean = statistics.mean(baseline_data)
            current_mean = statistics.mean(current_data)
            
            # Calculate performance change percentage
            if baseline_mean != 0:
                performance_change = ((current_mean - baseline_mean) / baseline_mean) * 100
            else:
                performance_change = 0.0
            
            # Determine if this is a regression (performance degradation)
            # For response time metrics, increase is bad
            # For throughput metrics, decrease is bad
            is_regression = False
            if "response_time" in metric_name.lower() or "latency" in metric_name.lower():
                is_regression = performance_change > self.config.regression.regression_threshold * 100
            elif "throughput" in metric_name.lower() or "rps" in metric_name.lower():
                is_regression = performance_change < -self.config.regression.regression_threshold * 100
            else:
                # Default: any significant increase is considered regression
                is_regression = abs(performance_change) > self.config.regression.regression_threshold * 100
            
            # Perform statistical significance test
            if "statistical_test" in self.config.regression.comparison_methods:
                t_stat, p_value = stats.ttest_ind(baseline_data, current_data)
                statistically_significant = p_value < self.config.regression.statistical_significance
            else:
                p_value = 0.0
                statistically_significant = True
            
            # Only report regression if it's statistically significant
            regression_detected = is_regression and statistically_significant
            
            # Determine severity
            severity = self._calculate_regression_severity(abs(performance_change))
            
            # Calculate confidence level
            confidence_level = 1.0 - p_value if p_value > 0 else 0.95
            
            regression_id = f"regression_{metric_name}_{int(datetime.now().timestamp())}"
            
            regression = PerformanceRegression(
                regression_id=regression_id,
                metric_name=metric_name,
                baseline_version=baseline_version,
                current_version=current_version,
                regression_detected=regression_detected,
                severity=severity,
                performance_change_percent=performance_change,
                baseline_mean=baseline_mean,
                current_mean=current_mean,
                statistical_significance=p_value,
                detection_method="statistical_test",
                detected_at=datetime.now(timezone.utc),
                confidence_level=confidence_level
            )
            
            if regression_detected:
                self.logger.warning(
                    f"Performance regression detected: {metric_name} "
                    f"({performance_change:+.2f}% change, {severity.value} severity)"
                )
            
            return regression
            
        except Exception as e:
            self.logger.error(f"Error in regression analysis: {e}")
            return None
    
    def _calculate_regression_severity(self, performance_change_percent: float) -> RegressionSeverity:
        """Calculate regression severity based on performance change."""
        threshold = self.config.regression.regression_threshold * 100
        
        if performance_change_percent >= threshold * 4:  # 4x threshold
            return RegressionSeverity.CRITICAL
        elif performance_change_percent >= threshold * 2:  # 2x threshold
            return RegressionSeverity.MAJOR
        elif performance_change_percent >= threshold * 1.5:  # 1.5x threshold
            return RegressionSeverity.MODERATE
        else:
            return RegressionSeverity.MINOR
    
    async def get_regression_history(self, metric_name: Optional[str] = None, limit: int = 100) -> List[PerformanceRegression]:
        """Get regression detection history."""
        if metric_name:
            regressions = [r for r in self.regression_history if r.metric_name == metric_name]
        else:
            regressions = self.regression_history
        
        return regressions[-limit:]
    
    async def clear_version_data(self, version: str):
        """Clear performance data for a specific version."""
        if version in self.version_metrics:
            del self.version_metrics[version]
            self.logger.info(f"Cleared data for version: {version}")
    
    async def get_detector_health(self) -> Dict[str, Any]:
        """Get regression detector health status."""
        return {
            'baseline_version': self.baseline_version,
            'current_version': self.current_version,
            'versions_tracked': len(self.version_metrics),
            'total_regressions': len(self.regression_history),
            'baseline_metrics': len(self.baseline_data.get(self.baseline_version, {}))
        }


def create_regression_detector(config: APMConfig) -> RegressionDetector:
    """Create regression detector instance."""
    return RegressionDetector(config)
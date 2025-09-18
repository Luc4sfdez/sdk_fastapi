"""
SLA Monitoring System for FastAPI Microservices SDK.

This module provides comprehensive SLA monitoring with violation detection,
reporting, and automated escalation for enterprise microservices.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import statistics
from collections import defaultdict, deque

from .config import APMConfig, SLAMetricType
from .exceptions import SLAViolationError


class SLAStatus(str, Enum):
    """SLA status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    VIOLATED = "violated"
    CRITICAL = "critical"


class ViolationType(str, Enum):
    """SLA violation type enumeration."""
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    AVAILABILITY_BREACH = "availability_breach"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_RATE_HIGH = "error_rate_high"


@dataclass
class SLADefinition:
    """SLA definition and configuration."""
    sla_id: str
    name: str
    description: str
    metric_type: SLAMetricType
    threshold_value: float
    threshold_operator: str  # "<=", ">=", "<", ">", "=="
    measurement_window: timedelta
    evaluation_frequency: timedelta
    violation_threshold: int  # Number of consecutive violations
    enabled: bool = True
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sla_id': self.sla_id,
            'name': self.name,
            'description': self.description,
            'metric_type': self.metric_type.value,
            'threshold_value': self.threshold_value,
            'threshold_operator': self.threshold_operator,
            'measurement_window': self.measurement_window.total_seconds(),
            'evaluation_frequency': self.evaluation_frequency.total_seconds(),
            'violation_threshold': self.violation_threshold,
            'enabled': self.enabled,
            'tags': self.tags
        }


@dataclass
class SLAViolation:
    """SLA violation record."""
    violation_id: str
    sla_id: str
    sla_name: str
    violation_type: ViolationType
    violation_time: datetime
    actual_value: float
    threshold_value: float
    severity: str
    duration: Optional[timedelta] = None
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'violation_id': self.violation_id,
            'sla_id': self.sla_id,
            'sla_name': self.sla_name,
            'violation_type': self.violation_type.value,
            'violation_time': self.violation_time.isoformat(),
            'actual_value': self.actual_value,
            'threshold_value': self.threshold_value,
            'severity': self.severity,
            'duration': self.duration.total_seconds() if self.duration else None,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'metadata': self.metadata
        }


@dataclass
class SLAMetrics:
    """SLA performance metrics."""
    sla_id: str
    measurement_period: timedelta
    availability_percent: float
    average_response_time: float
    error_rate_percent: float
    throughput_rps: float
    violation_count: int
    uptime_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'sla_id': self.sla_id,
            'measurement_period': self.measurement_period.total_seconds(),
            'availability_percent': self.availability_percent,
            'average_response_time': self.average_response_time,
            'error_rate_percent': self.error_rate_percent,
            'throughput_rps': self.throughput_rps,
            'violation_count': self.violation_count,
            'uptime_seconds': self.uptime_seconds
        }


@dataclass
class SLAReport:
    """SLA compliance report."""
    report_id: str
    report_period: timedelta
    generated_at: datetime
    sla_metrics: List[SLAMetrics]
    violations: List[SLAViolation]
    overall_compliance: float
    summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'report_period': self.report_period.total_seconds(),
            'generated_at': self.generated_at.isoformat(),
            'sla_metrics': [m.to_dict() for m in self.sla_metrics],
            'violations': [v.to_dict() for v in self.violations],
            'overall_compliance': self.overall_compliance,
            'summary': self.summary
        }


class SLAMonitor:
    """SLA monitoring and violation detection system."""
    
    def __init__(self, config: APMConfig):
        """Initialize SLA monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # SLA definitions and state
        self.sla_definitions: Dict[str, SLADefinition] = {}
        self.sla_status: Dict[str, SLAStatus] = {}
        self.violation_history: List[SLAViolation] = []
        self.active_violations: Dict[str, SLAViolation] = {}
        
        # Metrics collection
        self.metric_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        
        # Violation tracking
        self.consecutive_violations: Dict[str, int] = defaultdict(int)
        
        # Background tasks
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.reporting_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self.violation_callbacks: List[Callable] = []
        self.resolution_callbacks: List[Callable] = []
    
    async def start(self):
        """Start SLA monitoring."""
        try:
            if self.is_running:
                self.logger.warning("SLA monitor is already running")
                return
            
            self.logger.info("Starting SLA monitor...")
            
            # Create default SLAs if none exist
            if not self.sla_definitions:
                await self._create_default_slas()
            
            # Start background monitoring
            if self.config.sla.enabled:
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
                
                if self.config.sla.report_generation:
                    self.reporting_task = asyncio.create_task(self._reporting_loop())
            
            self.is_running = True
            self.logger.info("SLA monitor started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting SLA monitor: {e}")
            raise SLAViolationError(
                f"Failed to start SLA monitor: {e}",
                original_error=e
            )
    
    async def stop(self):
        """Stop SLA monitoring."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping SLA monitor...")
            
            # Cancel background tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self.reporting_task:
                self.reporting_task.cancel()
                try:
                    await self.reporting_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            self.logger.info("SLA monitor stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping SLA monitor: {e}")
    
    async def add_sla_definition(self, sla_definition: SLADefinition):
        """Add SLA definition."""
        try:
            self.sla_definitions[sla_definition.sla_id] = sla_definition
            self.sla_status[sla_definition.sla_id] = SLAStatus.HEALTHY
            
            self.logger.info(f"Added SLA definition: {sla_definition.name}")
            
        except Exception as e:
            self.logger.error(f"Error adding SLA definition: {e}")
            raise SLAViolationError(
                f"Failed to add SLA definition: {e}",
                sla_name=sla_definition.name,
                original_error=e
            )
    
    async def remove_sla_definition(self, sla_id: str):
        """Remove SLA definition."""
        if sla_id in self.sla_definitions:
            del self.sla_definitions[sla_id]
            self.sla_status.pop(sla_id, None)
            self.consecutive_violations.pop(sla_id, None)
            
            self.logger.info(f"Removed SLA definition: {sla_id}")
    
    async def record_metric(self, metric_type: SLAMetricType, value: float, timestamp: Optional[datetime] = None):
        """Record metric value for SLA evaluation."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            metric_key = metric_type.value
            self.metric_data[metric_key].append((timestamp, value))
            
            # Trigger immediate evaluation for critical metrics
            if metric_type in [SLAMetricType.ERROR_RATE, SLAMetricType.AVAILABILITY]:
                await self._evaluate_slas_for_metric(metric_type)
                
        except Exception as e:
            self.logger.error(f"Error recording metric: {e}")
    
    async def evaluate_sla(self, sla_id: str) -> bool:
        """Evaluate specific SLA and detect violations."""
        try:
            if sla_id not in self.sla_definitions:
                raise SLAViolationError(f"SLA definition not found: {sla_id}")
            
            sla_def = self.sla_definitions[sla_id]
            
            if not sla_def.enabled:
                return True
            
            # Get recent metric data
            metric_key = sla_def.metric_type.value
            cutoff_time = datetime.now(timezone.utc) - sla_def.measurement_window
            
            recent_data = [
                value for timestamp, value in self.metric_data[metric_key]
                if timestamp >= cutoff_time
            ]
            
            if not recent_data:
                return True  # No data to evaluate
            
            # Calculate metric value based on type
            if sla_def.metric_type == SLAMetricType.RESPONSE_TIME:
                metric_value = statistics.mean(recent_data)
            elif sla_def.metric_type == SLAMetricType.THROUGHPUT:
                metric_value = sum(recent_data) / sla_def.measurement_window.total_seconds()
            elif sla_def.metric_type == SLAMetricType.ERROR_RATE:
                metric_value = (sum(recent_data) / len(recent_data)) * 100
            elif sla_def.metric_type == SLAMetricType.AVAILABILITY:
                metric_value = (sum(recent_data) / len(recent_data)) * 100
            else:
                metric_value = statistics.mean(recent_data)
            
            # Evaluate threshold
            violation_detected = self._evaluate_threshold(
                metric_value, 
                sla_def.threshold_value, 
                sla_def.threshold_operator
            )
            
            if violation_detected:
                self.consecutive_violations[sla_id] += 1
                
                # Check if violation threshold is reached
                if self.consecutive_violations[sla_id] >= sla_def.violation_threshold:
                    await self._handle_sla_violation(sla_def, metric_value)
                    return False
            else:
                # Reset consecutive violations and resolve if needed
                if self.consecutive_violations[sla_id] > 0:
                    self.consecutive_violations[sla_id] = 0
                    await self._resolve_sla_violation(sla_id)
                
                self.sla_status[sla_id] = SLAStatus.HEALTHY
            
            return not violation_detected
            
        except Exception as e:
            self.logger.error(f"Error evaluating SLA {sla_id}: {e}")
            raise SLAViolationError(
                f"Failed to evaluate SLA: {e}",
                sla_name=sla_id,
                original_error=e
            )
    
    async def get_sla_status(self, sla_id: str) -> Optional[SLAStatus]:
        """Get current SLA status."""
        return self.sla_status.get(sla_id)
    
    async def get_all_sla_status(self) -> Dict[str, SLAStatus]:
        """Get status of all SLAs."""
        return self.sla_status.copy()
    
    async def get_violations(self, sla_id: Optional[str] = None, limit: int = 100) -> List[SLAViolation]:
        """Get SLA violations."""
        violations = self.violation_history
        
        if sla_id:
            violations = [v for v in violations if v.sla_id == sla_id]
        
        return violations[-limit:]
    
    async def get_active_violations(self) -> List[SLAViolation]:
        """Get currently active violations."""
        return list(self.active_violations.values())
    
    async def generate_sla_report(self, period: timedelta) -> SLAReport:
        """Generate SLA compliance report."""
        try:
            report_id = f"sla_report_{int(datetime.now().timestamp())}"
            cutoff_time = datetime.now(timezone.utc) - period
            
            # Calculate metrics for each SLA
            sla_metrics = []
            period_violations = []
            
            for sla_id, sla_def in self.sla_definitions.items():
                # Get period violations
                sla_violations = [
                    v for v in self.violation_history
                    if v.sla_id == sla_id and v.violation_time >= cutoff_time
                ]
                period_violations.extend(sla_violations)
                
                # Calculate SLA metrics
                metrics = await self._calculate_sla_metrics(sla_id, period)
                sla_metrics.append(metrics)
            
            # Calculate overall compliance
            total_slas = len(self.sla_definitions)
            compliant_slas = len([
                status for status in self.sla_status.values()
                if status == SLAStatus.HEALTHY
            ])
            overall_compliance = (compliant_slas / total_slas * 100) if total_slas > 0 else 100.0
            
            # Generate summary
            summary = {
                'total_slas': total_slas,
                'compliant_slas': compliant_slas,
                'violated_slas': total_slas - compliant_slas,
                'total_violations': len(period_violations),
                'critical_violations': len([
                    v for v in period_violations if v.severity == 'critical'
                ]),
                'average_resolution_time': self._calculate_average_resolution_time(period_violations)
            }
            
            report = SLAReport(
                report_id=report_id,
                report_period=period,
                generated_at=datetime.now(timezone.utc),
                sla_metrics=sla_metrics,
                violations=period_violations,
                overall_compliance=overall_compliance,
                summary=summary
            )
            
            self.logger.info(f"Generated SLA report: {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating SLA report: {e}")
            raise SLAViolationError(
                f"Failed to generate SLA report: {e}",
                original_error=e
            )
    
    def add_violation_callback(self, callback: Callable):
        """Add callback for SLA violations."""
        self.violation_callbacks.append(callback)
    
    def add_resolution_callback(self, callback: Callable):
        """Add callback for SLA violation resolutions."""
        self.resolution_callbacks.append(callback)
    
    def _evaluate_threshold(self, value: float, threshold: float, operator: str) -> bool:
        """Evaluate threshold condition."""
        if operator == "<=":
            return value > threshold
        elif operator == ">=":
            return value < threshold
        elif operator == "<":
            return value >= threshold
        elif operator == ">":
            return value <= threshold
        elif operator == "==":
            return value != threshold
        else:
            return False
    
    async def _handle_sla_violation(self, sla_def: SLADefinition, actual_value: float):
        """Handle SLA violation."""
        try:
            violation_id = f"violation_{sla_def.sla_id}_{int(datetime.now().timestamp())}"
            
            # Determine violation type and severity
            violation_type = self._determine_violation_type(sla_def.metric_type, actual_value)
            severity = self._calculate_violation_severity(sla_def, actual_value)
            
            # Create violation record
            violation = SLAViolation(
                violation_id=violation_id,
                sla_id=sla_def.sla_id,
                sla_name=sla_def.name,
                violation_type=violation_type,
                violation_time=datetime.now(timezone.utc),
                actual_value=actual_value,
                threshold_value=sla_def.threshold_value,
                severity=severity,
                metadata={
                    'consecutive_violations': self.consecutive_violations[sla_def.sla_id],
                    'measurement_window': sla_def.measurement_window.total_seconds()
                }
            )
            
            # Store violation
            self.violation_history.append(violation)
            self.active_violations[sla_def.sla_id] = violation
            
            # Update SLA status
            if severity == 'critical':
                self.sla_status[sla_def.sla_id] = SLAStatus.CRITICAL
            else:
                self.sla_status[sla_def.sla_id] = SLAStatus.VIOLATED
            
            # Maintain violation history size
            if len(self.violation_history) > 10000:
                self.violation_history = self.violation_history[-10000:]
            
            # Trigger callbacks
            for callback in self.violation_callbacks:
                try:
                    await callback(violation)
                except Exception as e:
                    self.logger.error(f"Error in violation callback: {e}")
            
            self.logger.warning(
                f"SLA violation detected: {sla_def.name} "
                f"(actual: {actual_value}, threshold: {sla_def.threshold_value})"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling SLA violation: {e}")
    
    async def _resolve_sla_violation(self, sla_id: str):
        """Resolve SLA violation."""
        if sla_id in self.active_violations:
            violation = self.active_violations[sla_id]
            violation.resolved = True
            violation.resolution_time = datetime.now(timezone.utc)
            violation.duration = violation.resolution_time - violation.violation_time
            
            del self.active_violations[sla_id]
            
            # Trigger resolution callbacks
            for callback in self.resolution_callbacks:
                try:
                    await callback(violation)
                except Exception as e:
                    self.logger.error(f"Error in resolution callback: {e}")
            
            self.logger.info(f"SLA violation resolved: {sla_id}")
    
    def _determine_violation_type(self, metric_type: SLAMetricType, value: float) -> ViolationType:
        """Determine violation type based on metric."""
        if metric_type == SLAMetricType.RESPONSE_TIME:
            return ViolationType.PERFORMANCE_DEGRADATION
        elif metric_type == SLAMetricType.ERROR_RATE:
            return ViolationType.ERROR_RATE_HIGH
        elif metric_type == SLAMetricType.AVAILABILITY:
            return ViolationType.AVAILABILITY_BREACH
        else:
            return ViolationType.THRESHOLD_EXCEEDED
    
    def _calculate_violation_severity(self, sla_def: SLADefinition, actual_value: float) -> str:
        """Calculate violation severity."""
        deviation = abs(actual_value - sla_def.threshold_value) / sla_def.threshold_value
        
        if deviation >= 0.5:  # 50% deviation
            return 'critical'
        elif deviation >= 0.2:  # 20% deviation
            return 'high'
        elif deviation >= 0.1:  # 10% deviation
            return 'medium'
        else:
            return 'low'
    
    async def _calculate_sla_metrics(self, sla_id: str, period: timedelta) -> SLAMetrics:
        """Calculate SLA metrics for a period."""
        sla_def = self.sla_definitions[sla_id]
        cutoff_time = datetime.now(timezone.utc) - period
        
        # Get period violations
        period_violations = [
            v for v in self.violation_history
            if v.sla_id == sla_id and v.violation_time >= cutoff_time
        ]
        
        # Calculate availability (simplified)
        total_time = period.total_seconds()
        violation_time = sum([
            v.duration.total_seconds() if v.duration else 0
            for v in period_violations
        ])
        availability_percent = ((total_time - violation_time) / total_time) * 100
        
        # Get metric data for period
        metric_key = sla_def.metric_type.value
        period_data = [
            value for timestamp, value in self.metric_data[metric_key]
            if timestamp >= cutoff_time
        ]
        
        # Calculate metrics
        avg_response_time = statistics.mean(period_data) if period_data else 0.0
        error_rate = 0.0  # Would be calculated from actual error data
        throughput = len(period_data) / period.total_seconds() if period_data else 0.0
        
        return SLAMetrics(
            sla_id=sla_id,
            measurement_period=period,
            availability_percent=availability_percent,
            average_response_time=avg_response_time,
            error_rate_percent=error_rate,
            throughput_rps=throughput,
            violation_count=len(period_violations),
            uptime_seconds=total_time - violation_time
        )
    
    def _calculate_average_resolution_time(self, violations: List[SLAViolation]) -> float:
        """Calculate average resolution time for violations."""
        resolved_violations = [v for v in violations if v.resolved and v.duration]
        
        if not resolved_violations:
            return 0.0
        
        total_time = sum([v.duration.total_seconds() for v in resolved_violations])
        return total_time / len(resolved_violations)
    
    async def _create_default_slas(self):
        """Create default SLA definitions."""
        try:
            # Response time SLA
            response_time_sla = SLADefinition(
                sla_id="response_time_sla",
                name="Response Time SLA",
                description="API response time should be under 1000ms",
                metric_type=SLAMetricType.RESPONSE_TIME,
                threshold_value=self.config.sla.default_response_time_ms,
                threshold_operator="<=",
                measurement_window=self.config.sla.evaluation_window,
                evaluation_frequency=self.config.sla.monitoring_interval,
                violation_threshold=self.config.sla.violation_threshold
            )
            
            # Error rate SLA
            error_rate_sla = SLADefinition(
                sla_id="error_rate_sla",
                name="Error Rate SLA",
                description="Error rate should be under 1%",
                metric_type=SLAMetricType.ERROR_RATE,
                threshold_value=self.config.sla.default_error_rate_percent,
                threshold_operator="<=",
                measurement_window=self.config.sla.evaluation_window,
                evaluation_frequency=self.config.sla.monitoring_interval,
                violation_threshold=self.config.sla.violation_threshold
            )
            
            # Availability SLA
            availability_sla = SLADefinition(
                sla_id="availability_sla",
                name="Availability SLA",
                description="Service availability should be above 99.9%",
                metric_type=SLAMetricType.AVAILABILITY,
                threshold_value=self.config.sla.default_availability_percent,
                threshold_operator=">=",
                measurement_window=timedelta(hours=1),
                evaluation_frequency=self.config.sla.monitoring_interval,
                violation_threshold=self.config.sla.violation_threshold
            )
            
            # Add default SLAs
            await self.add_sla_definition(response_time_sla)
            await self.add_sla_definition(error_rate_sla)
            await self.add_sla_definition(availability_sla)
            
            self.logger.info("Created default SLA definitions")
            
        except Exception as e:
            self.logger.error(f"Error creating default SLAs: {e}")
    
    async def _evaluate_slas_for_metric(self, metric_type: SLAMetricType):
        """Evaluate SLAs for a specific metric type."""
        for sla_id, sla_def in self.sla_definitions.items():
            if sla_def.metric_type == metric_type:
                try:
                    await self.evaluate_sla(sla_id)
                except Exception as e:
                    self.logger.error(f"Error evaluating SLA {sla_id}: {e}")
    
    async def _monitoring_loop(self):
        """Background SLA monitoring loop."""
        while self.is_running:
            try:
                # Monitor SLAs at configured interval
                await asyncio.sleep(self.config.sla.monitoring_interval.total_seconds())
                
                if not self.is_running:
                    break
                
                # Evaluate all SLAs
                for sla_id in list(self.sla_definitions.keys()):
                    try:
                        await self.evaluate_sla(sla_id)
                    except Exception as e:
                        self.logger.error(f"Error in SLA monitoring for {sla_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in SLA monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _reporting_loop(self):
        """Background SLA reporting loop."""
        while self.is_running:
            try:
                # Generate reports at configured frequency
                await asyncio.sleep(self.config.sla.report_frequency.total_seconds())
                
                if not self.is_running:
                    break
                
                # Generate daily report
                report = await self.generate_sla_report(timedelta(days=1))
                self.logger.info(f"Generated SLA report: {report.overall_compliance:.2f}% compliance")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in SLA reporting loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def get_sla_health(self) -> Dict[str, Any]:
        """Get SLA monitor health status."""
        return {
            'is_running': self.is_running,
            'total_slas': len(self.sla_definitions),
            'healthy_slas': len([
                s for s in self.sla_status.values() if s == SLAStatus.HEALTHY
            ]),
            'violated_slas': len([
                s for s in self.sla_status.values() if s in [SLAStatus.VIOLATED, SLAStatus.CRITICAL]
            ]),
            'active_violations': len(self.active_violations),
            'total_violations': len(self.violation_history)
        }


def create_sla_monitor(config: APMConfig) -> SLAMonitor:
    """Create SLA monitor instance."""
    return SLAMonitor(config)
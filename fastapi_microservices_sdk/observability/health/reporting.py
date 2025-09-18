"""
Health Reporting System for FastAPI Microservices SDK.

This module provides historical health reporting, trend analysis,
and comprehensive health documentation capabilities.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import json
import statistics
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

from .config import HealthConfig, HealthStatus
from .monitor import HealthMonitor
from .analytics import HealthAnalytics, HealthReport, HealthTrend, HealthPrediction
from .exceptions import HealthCheckError


class ReportType(str, Enum):
    """Health report type enumeration."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    INCIDENT = "incident"
    PERFORMANCE = "performance"
    TREND_ANALYSIS = "trend_analysis"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"


@dataclass
class HealthIncident:
    """Health incident record."""
    incident_id: str
    check_name: str
    incident_type: str
    severity: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    description: str = ""
    root_cause: Optional[str] = None
    resolution: Optional[str] = None
    impact: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'incident_id': self.incident_id,
            'check_name': self.check_name,
            'incident_type': self.incident_type,
            'severity': self.severity,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'description': self.description,
            'root_cause': self.root_cause,
            'resolution': self.resolution,
            'impact': self.impact
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics summary."""
    period_start: datetime
    period_end: datetime
    total_checks: int
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    availability: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'total_checks': self.total_checks,
            'average_response_time': self.average_response_time,
            'p95_response_time': self.p95_response_time,
            'p99_response_time': self.p99_response_time,
            'success_rate': self.success_rate,
            'availability': self.availability
        }


class HealthReportGenerator:
    """Health report generation system."""
    
    def __init__(
        self,
        config: HealthConfig,
        health_monitor: HealthMonitor,
        health_analytics: HealthAnalytics
    ):
        self.config = config
        self.health_monitor = health_monitor
        self.health_analytics = health_analytics
        self.logger = logging.getLogger(__name__)
        
        # Report storage
        self.reports: Dict[str, HealthReport] = {}
        self.incidents: Dict[str, HealthIncident] = {}
        
        # Report generation statistics
        self._reports_generated = 0
        self._incidents_tracked = 0
    
    async def generate_daily_report(self, date: Optional[datetime] = None) -> HealthReport:
        """Generate daily health report."""
        if date is None:
            date = datetime.now(timezone.utc)
        
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        return await self._generate_report(
            report_type=ReportType.DAILY,
            period_start=start_time,
            period_end=end_time
        )
    
    async def generate_weekly_report(self, week_start: Optional[datetime] = None) -> HealthReport:
        """Generate weekly health report."""
        if week_start is None:
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
        
        start_time = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)
        
        return await self._generate_report(
            report_type=ReportType.WEEKLY,
            period_start=start_time,
            period_end=end_time
        )
    
    async def generate_monthly_report(self, month_start: Optional[datetime] = None) -> HealthReport:
        """Generate monthly health report."""
        if month_start is None:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1)
        
        start_time = month_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate end of month
        if start_time.month == 12:
            end_time = start_time.replace(year=start_time.year + 1, month=1)
        else:
            end_time = start_time.replace(month=start_time.month + 1)
        
        return await self._generate_report(
            report_type=ReportType.MONTHLY,
            period_start=start_time,
            period_end=end_time
        )
    
    async def generate_custom_report(
        self,
        period_start: datetime,
        period_end: datetime,
        report_name: str = "custom"
    ) -> HealthReport:
        """Generate custom period health report."""
        return await self._generate_report(
            report_type=ReportType.CUSTOM,
            period_start=period_start,
            period_end=period_end,
            custom_name=report_name
        )
    
    async def _generate_report(
        self,
        report_type: ReportType,
        period_start: datetime,
        period_end: datetime,
        custom_name: str = ""
    ) -> HealthReport:
        """Generate health report for specified period."""
        try:
            # Generate base report from analytics
            period_hours = int((period_end - period_start).total_seconds() / 3600)
            base_report = await self.health_analytics.generate_health_report(period_hours)
            
            # Enhance with additional reporting features
            report_id = f"{report_type.value}-{custom_name}-{int(period_start.timestamp())}"
            
            enhanced_report = HealthReport(
                report_id=report_id,
                generated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end,
                total_checks=base_report.total_checks,
                healthy_percentage=base_report.healthy_percentage,
                average_response_time=base_report.average_response_time,
                trends=base_report.trends,
                predictions=base_report.predictions,
                performance_summary=base_report.performance_summary,
                recommendations=base_report.recommendations
            )
            
            # Add report-specific enhancements
            if report_type == ReportType.INCIDENT:
                enhanced_report = await self._enhance_incident_report(enhanced_report)
            elif report_type == ReportType.PERFORMANCE:
                enhanced_report = await self._enhance_performance_report(enhanced_report)
            elif report_type == ReportType.TREND_ANALYSIS:
                enhanced_report = await self._enhance_trend_report(enhanced_report)
            
            # Store report
            self.reports[report_id] = enhanced_report
            self._reports_generated += 1
            
            self.logger.info(f"Generated {report_type.value} health report: {report_id}")
            return enhanced_report
            
        except Exception as e:
            self.logger.error(f"Failed to generate {report_type.value} report: {e}")
            raise HealthCheckError(f"Report generation failed: {e}")
    
    async def _enhance_incident_report(self, report: HealthReport) -> HealthReport:
        """Enhance report with incident information."""
        # Add incidents that occurred during the period
        period_incidents = [
            incident for incident in self.incidents.values()
            if report.period_start <= incident.start_time <= report.period_end
        ]
        
        # Add incident summary to performance summary
        report.performance_summary['incidents'] = {
            'total_incidents': len(period_incidents),
            'critical_incidents': len([i for i in period_incidents if i.severity == 'critical']),
            'average_resolution_time': self._calculate_average_resolution_time(period_incidents),
            'most_affected_checks': self._get_most_affected_checks(period_incidents)
        }
        
        return report
    
    async def _enhance_performance_report(self, report: HealthReport) -> HealthReport:
        """Enhance report with detailed performance metrics."""
        # Calculate detailed performance metrics
        if hasattr(self.health_analytics, '_metrics_history'):
            performance_metrics = self._calculate_performance_metrics(
                report.period_start,
                report.period_end
            )
            report.performance_summary['detailed_metrics'] = performance_metrics.to_dict()
        
        return report
    
    async def _enhance_trend_report(self, report: HealthReport) -> HealthReport:
        """Enhance report with detailed trend analysis."""
        # Add trend predictions and confidence intervals
        for trend in report.trends:
            # Calculate confidence intervals (simplified)
            if trend.confidence > 0.5:
                trend.metadata = {
                    'confidence_interval': {
                        'lower': trend.predicted_value * 0.9 if trend.predicted_value else None,
                        'upper': trend.predicted_value * 1.1 if trend.predicted_value else None
                    },
                    'trend_strength': 'strong' if trend.confidence > 0.8 else 'moderate'
                }
        
        return report
    
    def _calculate_average_resolution_time(self, incidents: List[HealthIncident]) -> float:
        """Calculate average incident resolution time."""
        resolved_incidents = [i for i in incidents if i.end_time and i.duration_seconds]
        if not resolved_incidents:
            return 0.0
        
        return statistics.mean([i.duration_seconds for i in resolved_incidents])
    
    def _get_most_affected_checks(self, incidents: List[HealthIncident]) -> List[str]:
        """Get most affected health checks."""
        check_counts = {}
        for incident in incidents:
            check_counts[incident.check_name] = check_counts.get(incident.check_name, 0) + 1
        
        return sorted(check_counts.keys(), key=lambda x: check_counts[x], reverse=True)[:5]
    
    def _calculate_performance_metrics(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> PerformanceMetrics:
        """Calculate detailed performance metrics."""
        # Collect all metrics for the period
        all_metrics = []
        
        if hasattr(self.health_analytics, '_metrics_history'):
            for metrics in self.health_analytics._metrics_history.values():
                period_metrics = [
                    m for m in metrics 
                    if period_start <= m.timestamp <= period_end
                ]
                all_metrics.extend(period_metrics)
        
        if not all_metrics:
            return PerformanceMetrics(
                period_start=period_start,
                period_end=period_end,
                total_checks=0,
                average_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                success_rate=0.0,
                availability=0.0
            )
        
        # Calculate metrics
        response_times = [m.duration_ms for m in all_metrics]
        successful_checks = [m for m in all_metrics if m.status == HealthStatus.HEALTHY]
        
        # Calculate percentiles
        response_times.sort()
        p95_index = int(len(response_times) * 0.95)
        p99_index = int(len(response_times) * 0.99)
        
        return PerformanceMetrics(
            period_start=period_start,
            period_end=period_end,
            total_checks=len(all_metrics),
            average_response_time=statistics.mean(response_times),
            p95_response_time=response_times[p95_index] if response_times else 0.0,
            p99_response_time=response_times[p99_index] if response_times else 0.0,
            success_rate=len(successful_checks) / len(all_metrics),
            availability=len(successful_checks) / len(all_metrics) * 100
        )
    
    def export_report(self, report_id: str, format: ReportFormat = ReportFormat.JSON) -> str:
        """Export report in specified format."""
        report = self.reports.get(report_id)
        if not report:
            raise HealthCheckError(f"Report not found: {report_id}")
        
        if format == ReportFormat.JSON:
            return json.dumps(report.to_dict(), indent=2, default=str)
        elif format == ReportFormat.HTML:
            return self._export_html_report(report)
        elif format == ReportFormat.CSV:
            return self._export_csv_report(report)
        else:
            raise HealthCheckError(f"Unsupported export format: {format.value}")
    
    def _export_html_report(self, report: HealthReport) -> str:
        """Export report as HTML."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Health Report - {report.report_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
                .healthy {{ background-color: #d4edda; }}
                .degraded {{ background-color: #fff3cd; }}
                .unhealthy {{ background-color: #f8d7da; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Health Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Generated:</strong> {report.generated_at.isoformat()}</p>
                <p><strong>Period:</strong> {report.period_start.isoformat()} to {report.period_end.isoformat()}</p>
                <p><strong>Healthy Percentage:</strong> {report.healthy_percentage:.1f}%</p>
                <p><strong>Average Response Time:</strong> {report.average_response_time:.1f}ms</p>
            </div>
            
            <h2>Health Trends</h2>
            <table>
                <tr>
                    <th>Check Name</th>
                    <th>Direction</th>
                    <th>Confidence</th>
                    <th>Current Value</th>
                    <th>Predicted Value</th>
                </tr>
        """
        
        for trend in report.trends:
            html += f"""
                <tr>
                    <td>{trend.check_name}</td>
                    <td>{trend.direction.value}</td>
                    <td>{trend.confidence:.2f}</td>
                    <td>{trend.current_value:.2f}</td>
                    <td>{trend.predicted_value:.2f if trend.predicted_value else 'N/A'}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for recommendation in report.recommendations:
            html += f"<li>{recommendation}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def _export_csv_report(self, report: HealthReport) -> str:
        """Export report as CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Check Name', 'Trend Direction', 'Confidence', 'Current Value', 'Predicted Value'])
        
        # Write trends
        for trend in report.trends:
            writer.writerow([
                trend.check_name,
                trend.direction.value,
                trend.confidence,
                trend.current_value,
                trend.predicted_value or 'N/A'
            ])
        
        return output.getvalue()
    
    def track_incident(
        self,
        check_name: str,
        incident_type: str,
        severity: str,
        description: str = ""
    ) -> HealthIncident:
        """Track a health incident."""
        incident_id = f"incident-{check_name}-{int(time.time())}"
        
        incident = HealthIncident(
            incident_id=incident_id,
            check_name=check_name,
            incident_type=incident_type,
            severity=severity,
            start_time=datetime.now(timezone.utc),
            description=description
        )
        
        self.incidents[incident_id] = incident
        self._incidents_tracked += 1
        
        self.logger.warning(f"Health incident tracked: {incident_id}")
        return incident
    
    def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        root_cause: Optional[str] = None
    ) -> bool:
        """Resolve a health incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.end_time = datetime.now(timezone.utc)
        incident.duration_seconds = int((incident.end_time - incident.start_time).total_seconds())
        incident.resolution = resolution
        incident.root_cause = root_cause
        
        self.logger.info(f"Health incident resolved: {incident_id}")
        return True
    
    def get_report_statistics(self) -> Dict[str, Any]:
        """Get report generation statistics."""
        return {
            'reports_generated': self._reports_generated,
            'incidents_tracked': self._incidents_tracked,
            'stored_reports': len(self.reports),
            'active_incidents': len([i for i in self.incidents.values() if i.end_time is None]),
            'resolved_incidents': len([i for i in self.incidents.values() if i.end_time is not None])
        }


def create_health_report_generator(
    config: HealthConfig,
    health_monitor: HealthMonitor,
    health_analytics: HealthAnalytics
) -> HealthReportGenerator:
    """Create health report generator."""
    return HealthReportGenerator(config, health_monitor, health_analytics)


# Export main classes and functions
__all__ = [
    'ReportType',
    'ReportFormat',
    'HealthIncident',
    'PerformanceMetrics',
    'HealthReportGenerator',
    'create_health_report_generator',
]
"""
Health Analytics Reporter for FastAPI Microservices SDK.

This module provides comprehensive health reporting, dashboard generation,
and SLA monitoring capabilities for enterprise health analytics.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
from pathlib import Path

from .config import AnalyticsConfig, ReportConfig, ReportFormat
from .exceptions import ReportGenerationError
from .analyzer import HealthDataPoint, TrendAnalysis, HealthAnalyzer
from .predictor import PredictionResult, CapacityForecast, AnomalyPrediction


class ReportType(str, Enum):
    """Report type enumeration."""
    HEALTH_SUMMARY = "health_summary"
    TREND_ANALYSIS = "trend_analysis"
    CAPACITY_PLANNING = "capacity_planning"
    ANOMALY_DETECTION = "anomaly_detection"
    SLA_COMPLIANCE = "sla_compliance"
    PERFORMANCE_OVERVIEW = "performance_overview"


class ReportPeriod(str, Enum):
    """Report period enumeration."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class HealthReport:
    """Health analytics report."""
    report_id: str
    report_type: ReportType
    report_period: ReportPeriod
    generated_at: datetime
    data_period_start: datetime
    data_period_end: datetime
    summary: Dict[str, Any]
    detailed_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    predictions: Dict[str, Any]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLAMetrics:
    """SLA compliance metrics."""
    availability_percentage: float
    response_time_p95: float
    response_time_p99: float
    error_rate_percentage: float
    uptime_hours: float
    downtime_incidents: int
    sla_compliance_score: float
    violations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DashboardData:
    """Dashboard data structure."""
    dashboard_id: str
    title: str
    generated_at: datetime
    refresh_interval: int
    widgets: List[Dict[str, Any]]
    filters: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthReporter:
    """Advanced health analytics reporter."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize health reporter."""
        self.config = config
        self.report_config = config.report_config
        self.logger = logging.getLogger(__name__)
        
        # Report storage
        self._reports: Dict[str, HealthReport] = {}
        self._report_templates: Dict[ReportType, str] = {}
        
        # Initialize output directory
        self._setup_output_directory()
    
    async def generate_health_report(
        self,
        report_type: ReportType,
        data_points: List[HealthDataPoint],
        period_start: datetime,
        period_end: datetime,
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> HealthReport:
        """Generate comprehensive health report."""
        try:
            report_id = f"{report_type.value}_{int(time.time())}"
            
            self.logger.info(f"Generating health report: {report_id}")
            
            # Generate report sections
            summary = await self._generate_summary(data_points, report_type)
            detailed_metrics = await self._generate_detailed_metrics(data_points, custom_metrics)
            trends = await self._generate_trend_analysis(data_points)
            predictions = await self._generate_predictions(data_points)
            recommendations = await self._generate_recommendations(data_points, trends, predictions)
            
            # Create report
            report = HealthReport(
                report_id=report_id,
                report_type=report_type,
                report_period=self._determine_report_period(period_start, period_end),
                generated_at=datetime.now(timezone.utc),
                data_period_start=period_start,
                data_period_end=period_end,
                summary=summary,
                detailed_metrics=detailed_metrics,
                trends=trends,
                predictions=predictions,
                recommendations=recommendations,
                metadata={
                    'data_points_count': len(data_points),
                    'service_name': self.config.service_name,
                    'environment': self.config.environment
                }
            )
            
            # Store report
            self._reports[report_id] = report
            
            # Export report in configured formats
            await self._export_report(report)
            
            self.logger.info(f"Health report generated successfully: {report_id}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating health report: {e}")
            raise ReportGenerationError(
                "Failed to generate health report",
                report_type=report_type.value,
                original_error=e
            )
    
    async def _generate_summary(
        self,
        data_points: List[HealthDataPoint],
        report_type: ReportType
    ) -> Dict[str, Any]:
        """Generate report summary."""
        try:
            if not data_points:
                return {'status': 'no_data', 'message': 'No data available for analysis'}
            
            # Basic statistics
            response_times = [dp.response_time for dp in data_points]
            error_counts = [dp.error_count for dp in data_points]
            
            healthy_count = sum(1 for dp in data_points if dp.status.value == "healthy")
            total_count = len(data_points)
            
            summary = {
                'period_summary': {
                    'total_checks': total_count,
                    'healthy_checks': healthy_count,
                    'availability_percentage': (healthy_count / total_count * 100) if total_count > 0 else 0,
                    'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                    'max_response_time': max(response_times) if response_times else 0,
                    'min_response_time': min(response_times) if response_times else 0,
                    'total_errors': sum(error_counts)
                },
                'health_status': self._determine_overall_health_status(data_points),
                'key_insights': await self._generate_key_insights(data_points),
                'alert_summary': await self._generate_alert_summary(data_points)
            }
            
            return summary
            
        except Exception as e:
            self.logger.warning(f"Error generating summary: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _generate_detailed_metrics(
        self,
        data_points: List[HealthDataPoint],
        custom_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate detailed metrics."""
        try:
            if not data_points:
                return {}
            
            response_times = [dp.response_time for dp in data_points]
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            n = len(sorted_times)
            
            p50_index = int(0.5 * n)
            p95_index = int(0.95 * n)
            p99_index = int(0.99 * n)
            
            metrics = {
                'response_time_metrics': {
                    'p50': sorted_times[p50_index] if p50_index < n else 0,
                    'p95': sorted_times[p95_index] if p95_index < n else 0,
                    'p99': sorted_times[p99_index] if p99_index < n else 0,
                    'mean': sum(response_times) / len(response_times),
                    'std_dev': self._calculate_std_dev(response_times)
                },
                'availability_metrics': {
                    'uptime_percentage': await self._calculate_uptime_percentage(data_points),
                    'downtime_incidents': await self._count_downtime_incidents(data_points),
                    'mttr': await self._calculate_mttr(data_points),  # Mean Time To Recovery
                    'mtbf': await self._calculate_mtbf(data_points)   # Mean Time Between Failures
                },
                'error_metrics': {
                    'total_errors': sum(dp.error_count for dp in data_points),
                    'error_rate': await self._calculate_error_rate(data_points),
                    'error_distribution': await self._analyze_error_distribution(data_points)
                },
                'performance_trends': {
                    'hourly_patterns': await self._analyze_hourly_patterns(data_points),
                    'daily_patterns': await self._analyze_daily_patterns(data_points)
                }
            }
            
            # Add custom metrics if provided
            if custom_metrics:
                metrics['custom_metrics'] = custom_metrics
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Error generating detailed metrics: {e}")
            return {}
    
    async def _generate_trend_analysis(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Generate trend analysis."""
        try:
            if len(data_points) < 10:
                return {'status': 'insufficient_data'}
            
            analyzer = HealthAnalyzer(self.config)
            
            # Add data points to analyzer
            for dp in data_points:
                await analyzer.add_data_point(self._convert_to_health_check_result(dp))
            
            # Analyze trends
            trends = await analyzer.analyze_trends()
            
            # Convert to serializable format
            trend_data = {}
            for trend_type, analysis in trends.items():
                trend_data[trend_type.value] = {
                    'direction': analysis.direction.value,
                    'confidence': analysis.confidence,
                    'slope': analysis.slope,
                    'correlation': analysis.correlation,
                    'prediction': analysis.prediction,
                    'data_points': analysis.data_points
                }
            
            return {
                'status': 'success',
                'trends': trend_data,
                'analysis_period': '24h',
                'confidence_threshold': self.config.trend_config.confidence_threshold
            }
            
        except Exception as e:
            self.logger.warning(f"Error generating trend analysis: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _generate_predictions(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Generate predictions."""
        try:
            if len(data_points) < 10:
                return {'status': 'insufficient_data'}
            
            from .predictor import HealthPredictor, PredictionHorizon
            
            predictor = HealthPredictor(self.config)
            
            # Generate predictions for different horizons
            predictions = {}
            
            for horizon in [PredictionHorizon.SHORT_TERM, PredictionHorizon.MEDIUM_TERM, PredictionHorizon.LONG_TERM]:
                try:
                    horizon_predictions = await predictor.predict_health_metrics(data_points, horizon)
                    
                    predictions[horizon.value] = {}
                    for model, prediction in horizon_predictions.items():
                        predictions[horizon.value][model.value] = {
                            'predicted_value': prediction.predicted_value,
                            'confidence_interval': prediction.confidence_interval,
                            'confidence_level': prediction.confidence_level,
                            'metadata': prediction.metadata
                        }
                        
                except Exception as e:
                    self.logger.warning(f"Error generating predictions for {horizon.value}: {e}")
                    predictions[horizon.value] = {'status': 'error', 'message': str(e)}
            
            return {
                'status': 'success',
                'predictions': predictions,
                'models_used': [model.value for model in self.config.prediction_config.models]
            }
            
        except Exception as e:
            self.logger.warning(f"Error generating predictions: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def _generate_recommendations(
        self,
        data_points: List[HealthDataPoint],
        trends: Dict[str, Any],
        predictions: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations."""
        try:
            recommendations = []
            
            # Analyze current health status
            if not data_points:
                return ['No data available for analysis']
            
            recent_data = data_points[-10:] if len(data_points) >= 10 else data_points
            avg_response_time = sum(dp.response_time for dp in recent_data) / len(recent_data)
            error_rate = sum(dp.error_count for dp in recent_data) / len(recent_data)
            
            # Response time recommendations
            if avg_response_time > 1.0:  # 1 second threshold
                recommendations.append(
                    f"High response time detected ({avg_response_time:.2f}s). "
                    "Consider optimizing database queries, adding caching, or scaling resources."
                )
            
            # Error rate recommendations
            if error_rate > 0.1:  # 10% error rate threshold
                recommendations.append(
                    f"Elevated error rate detected ({error_rate:.1%}). "
                    "Review error logs and implement circuit breakers for external dependencies."
                )
            
            # Trend-based recommendations
            if trends.get('status') == 'success':
                trend_data = trends.get('trends', {})
                
                for trend_type, analysis in trend_data.items():
                    if analysis.get('direction') == 'degrading' and analysis.get('confidence', 0) > 0.7:
                        recommendations.append(
                            f"Degrading {trend_type} trend detected with high confidence. "
                            "Investigate root causes and consider preventive scaling."
                        )
            
            # Prediction-based recommendations
            if predictions.get('status') == 'success':
                pred_data = predictions.get('predictions', {})
                
                # Check long-term predictions
                long_term = pred_data.get('24h', {})
                for model, prediction in long_term.items():
                    if isinstance(prediction, dict) and prediction.get('predicted_value', 0) > avg_response_time * 1.5:
                        recommendations.append(
                            f"Predicted response time increase of {prediction.get('predicted_value', 0):.2f}s. "
                            "Consider proactive scaling or performance optimization."
                        )
            
            # General recommendations
            if len(recommendations) == 0:
                recommendations.append("System health appears stable. Continue monitoring for any changes.")
            
            # Add capacity planning recommendation
            if avg_response_time > 0.5:  # 500ms threshold
                recommendations.append(
                    "Consider implementing auto-scaling policies based on response time thresholds."
                )
            
            return recommendations[:10]  # Limit to top 10 recommendations
            
        except Exception as e:
            self.logger.warning(f"Error generating recommendations: {e}")
            return ["Unable to generate recommendations due to analysis error."] 
   
    def _determine_overall_health_status(self, data_points: List[HealthDataPoint]) -> str:
        """Determine overall health status."""
        if not data_points:
            return "unknown"
        
        recent_data = data_points[-10:] if len(data_points) >= 10 else data_points
        healthy_count = sum(1 for dp in recent_data if dp.status.value == "healthy")
        health_percentage = healthy_count / len(recent_data)
        
        if health_percentage >= 0.95:
            return "excellent"
        elif health_percentage >= 0.90:
            return "good"
        elif health_percentage >= 0.80:
            return "fair"
        elif health_percentage >= 0.60:
            return "poor"
        else:
            return "critical"
    
    async def _generate_key_insights(self, data_points: List[HealthDataPoint]) -> List[str]:
        """Generate key insights from data."""
        insights = []
        
        if not data_points:
            return ["No data available for insights"]
        
        try:
            # Response time insights
            response_times = [dp.response_time for dp in data_points]
            avg_response = sum(response_times) / len(response_times)
            
            if avg_response < 0.1:
                insights.append("Excellent response times maintained throughout the period")
            elif avg_response > 2.0:
                insights.append("Response times are concerning and require attention")
            
            # Availability insights
            healthy_count = sum(1 for dp in data_points if dp.status.value == "healthy")
            availability = healthy_count / len(data_points)
            
            if availability >= 0.999:
                insights.append("Exceptional availability achieved (99.9%+)")
            elif availability < 0.95:
                insights.append("Availability below target threshold (95%)")
            
            # Error pattern insights
            error_counts = [dp.error_count for dp in data_points]
            total_errors = sum(error_counts)
            
            if total_errors == 0:
                insights.append("Zero errors recorded during the analysis period")
            elif total_errors > len(data_points) * 0.1:
                insights.append("High error rate detected - investigation recommended")
            
            return insights[:5]  # Limit to top 5 insights
            
        except Exception as e:
            self.logger.warning(f"Error generating insights: {e}")
            return ["Unable to generate insights due to analysis error"]
    
    async def _generate_alert_summary(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Generate alert summary."""
        try:
            alerts = {
                'critical': 0,
                'warning': 0,
                'info': 0,
                'total': 0
            }
            
            for dp in data_points:
                if dp.status.value == "unhealthy":
                    alerts['critical'] += 1
                elif dp.response_time > 1.0:  # 1 second threshold
                    alerts['warning'] += 1
                elif dp.error_count > 0:
                    alerts['info'] += 1
            
            alerts['total'] = alerts['critical'] + alerts['warning'] + alerts['info']
            
            return alerts
            
        except Exception as e:
            self.logger.warning(f"Error generating alert summary: {e}")
            return {'critical': 0, 'warning': 0, 'info': 0, 'total': 0}
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    async def _calculate_uptime_percentage(self, data_points: List[HealthDataPoint]) -> float:
        """Calculate uptime percentage."""
        if not data_points:
            return 0.0
        
        healthy_count = sum(1 for dp in data_points if dp.status.value == "healthy")
        return (healthy_count / len(data_points)) * 100
    
    async def _count_downtime_incidents(self, data_points: List[HealthDataPoint]) -> int:
        """Count downtime incidents."""
        incidents = 0
        in_downtime = False
        
        for dp in data_points:
            if dp.status.value != "healthy" and not in_downtime:
                incidents += 1
                in_downtime = True
            elif dp.status.value == "healthy" and in_downtime:
                in_downtime = False
        
        return incidents
    
    async def _calculate_mttr(self, data_points: List[HealthDataPoint]) -> float:
        """Calculate Mean Time To Recovery."""
        if len(data_points) < 2:
            return 0.0
        
        recovery_times = []
        downtime_start = None
        
        for dp in data_points:
            if dp.status.value != "healthy" and downtime_start is None:
                downtime_start = dp.timestamp
            elif dp.status.value == "healthy" and downtime_start is not None:
                recovery_time = (dp.timestamp - downtime_start).total_seconds() / 60  # Minutes
                recovery_times.append(recovery_time)
                downtime_start = None
        
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
    
    async def _calculate_mtbf(self, data_points: List[HealthDataPoint]) -> float:
        """Calculate Mean Time Between Failures."""
        if len(data_points) < 2:
            return 0.0
        
        failure_intervals = []
        last_failure = None
        
        for dp in data_points:
            if dp.status.value != "healthy":
                if last_failure is not None:
                    interval = (dp.timestamp - last_failure).total_seconds() / 3600  # Hours
                    failure_intervals.append(interval)
                last_failure = dp.timestamp
        
        return sum(failure_intervals) / len(failure_intervals) if failure_intervals else 0.0
    
    async def _calculate_error_rate(self, data_points: List[HealthDataPoint]) -> float:
        """Calculate error rate percentage."""
        if not data_points:
            return 0.0
        
        total_errors = sum(dp.error_count for dp in data_points)
        return (total_errors / len(data_points)) * 100
    
    async def _analyze_error_distribution(self, data_points: List[HealthDataPoint]) -> Dict[str, int]:
        """Analyze error distribution."""
        distribution = {
            'no_errors': 0,
            'low_errors': 0,    # 1-2 errors
            'medium_errors': 0, # 3-5 errors
            'high_errors': 0    # 6+ errors
        }
        
        for dp in data_points:
            if dp.error_count == 0:
                distribution['no_errors'] += 1
            elif dp.error_count <= 2:
                distribution['low_errors'] += 1
            elif dp.error_count <= 5:
                distribution['medium_errors'] += 1
            else:
                distribution['high_errors'] += 1
        
        return distribution
    
    async def _analyze_hourly_patterns(self, data_points: List[HealthDataPoint]) -> Dict[int, float]:
        """Analyze hourly performance patterns."""
        hourly_data = {}
        
        for dp in data_points:
            hour = dp.timestamp.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(dp.response_time)
        
        # Calculate average response time per hour
        hourly_averages = {}
        for hour, times in hourly_data.items():
            hourly_averages[hour] = sum(times) / len(times)
        
        return hourly_averages
    
    async def _analyze_daily_patterns(self, data_points: List[HealthDataPoint]) -> Dict[str, float]:
        """Analyze daily performance patterns."""
        daily_data = {}
        
        for dp in data_points:
            day = dp.timestamp.strftime('%Y-%m-%d')
            if day not in daily_data:
                daily_data[day] = []
            daily_data[day].append(dp.response_time)
        
        # Calculate average response time per day
        daily_averages = {}
        for day, times in daily_data.items():
            daily_averages[day] = sum(times) / len(times)
        
        return daily_averages
    
    def _convert_to_health_check_result(self, data_point: HealthDataPoint):
        """Convert HealthDataPoint to HealthCheckResult for analyzer."""
        # This is a simplified conversion - in a real implementation,
        # you'd import and use the actual HealthCheckResult class
        class MockHealthCheckResult:
            def __init__(self, dp):
                self.status = dp.status
                self.response_time = dp.response_time
                self.details = dp.metadata
        
        return MockHealthCheckResult(data_point)
    
    def _determine_report_period(self, start: datetime, end: datetime) -> ReportPeriod:
        """Determine report period based on time range."""
        duration = end - start
        
        if duration <= timedelta(hours=2):
            return ReportPeriod.HOURLY
        elif duration <= timedelta(days=2):
            return ReportPeriod.DAILY
        elif duration <= timedelta(days=8):
            return ReportPeriod.WEEKLY
        elif duration <= timedelta(days=35):
            return ReportPeriod.MONTHLY
        else:
            return ReportPeriod.CUSTOM
    
    def _setup_output_directory(self):
        """Setup output directory for reports."""
        try:
            output_path = Path(self.report_config.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Report output directory: {output_path.absolute()}")
        except Exception as e:
            self.logger.warning(f"Error setting up output directory: {e}")
    
    async def _export_report(self, report: HealthReport):
        """Export report in configured formats."""
        try:
            for format_type in self.report_config.formats:
                await self._export_report_format(report, format_type)
        except Exception as e:
            self.logger.warning(f"Error exporting report: {e}")
    
    async def _export_report_format(self, report: HealthReport, format_type: ReportFormat):
        """Export report in specific format."""
        try:
            output_path = Path(self.report_config.output_directory)
            filename = f"{report.report_id}.{format_type.value}"
            file_path = output_path / filename
            
            if format_type == ReportFormat.JSON:
                await self._export_json_report(report, file_path)
            elif format_type == ReportFormat.HTML:
                await self._export_html_report(report, file_path)
            elif format_type == ReportFormat.CSV:
                await self._export_csv_report(report, file_path)
            elif format_type == ReportFormat.MARKDOWN:
                await self._export_markdown_report(report, file_path)
            
            self.logger.info(f"Report exported: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"Error exporting {format_type.value} report: {e}")
    
    async def _export_json_report(self, report: HealthReport, file_path: Path):
        """Export report as JSON."""
        try:
            report_dict = asdict(report)
            # Convert datetime objects to ISO format
            report_dict['generated_at'] = report.generated_at.isoformat()
            report_dict['data_period_start'] = report.data_period_start.isoformat()
            report_dict['data_period_end'] = report.data_period_end.isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise ReportGenerationError(f"Failed to export JSON report: {e}")
    
    async def _export_html_report(self, report: HealthReport, file_path: Path):
        """Export report as HTML."""
        try:
            html_content = self._generate_html_template(report)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        except Exception as e:
            raise ReportGenerationError(f"Failed to export HTML report: {e}")
    
    async def _export_csv_report(self, report: HealthReport, file_path: Path):
        """Export report as CSV."""
        try:
            # Simple CSV export with key metrics
            csv_content = "Metric,Value\n"
            
            summary = report.summary.get('period_summary', {})
            for key, value in summary.items():
                csv_content += f"{key},{value}\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
                
        except Exception as e:
            raise ReportGenerationError(f"Failed to export CSV report: {e}")
    
    async def _export_markdown_report(self, report: HealthReport, file_path: Path):
        """Export report as Markdown."""
        try:
            md_content = self._generate_markdown_template(report)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
        except Exception as e:
            raise ReportGenerationError(f"Failed to export Markdown report: {e}")
    
    def _generate_html_template(self, report: HealthReport) -> str:
        """Generate HTML template for report."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Health Analytics Report - {report.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ background-color: #f9f9f9; padding: 10px; margin: 5px 0; border-left: 4px solid #007cba; }}
        .recommendations {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Health Analytics Report</h1>
        <p><strong>Report ID:</strong> {report.report_id}</p>
        <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        <p><strong>Period:</strong> {report.data_period_start.strftime('%Y-%m-%d')} to {report.data_period_end.strftime('%Y-%m-%d')}</p>
    </div>
    
    <div class="section">
        <h2>Summary</h2>
        <div class="metric">
            <strong>Overall Health:</strong> {report.summary.get('health_status', 'Unknown')}
        </div>
        <div class="metric">
            <strong>Availability:</strong> {report.summary.get('period_summary', {}).get('availability_percentage', 0):.2f}%
        </div>
        <div class="metric">
            <strong>Average Response Time:</strong> {report.summary.get('period_summary', {}).get('avg_response_time', 0):.3f}s
        </div>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        <div class="recommendations">
            <ul>
                {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
            </ul>
        </div>
    </div>
</body>
</html>
        """
    
    def _generate_markdown_template(self, report: HealthReport) -> str:
        """Generate Markdown template for report."""
        return f"""# Health Analytics Report

**Report ID:** {report.report_id}  
**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Period:** {report.data_period_start.strftime('%Y-%m-%d')} to {report.data_period_end.strftime('%Y-%m-%d')}

## Summary

- **Overall Health:** {report.summary.get('health_status', 'Unknown')}
- **Availability:** {report.summary.get('period_summary', {}).get('availability_percentage', 0):.2f}%
- **Average Response Time:** {report.summary.get('period_summary', {}).get('avg_response_time', 0):.3f}s
- **Total Errors:** {report.summary.get('period_summary', {}).get('total_errors', 0)}

## Key Insights

{chr(10).join(f'- {insight}' for insight in report.summary.get('key_insights', []))}

## Recommendations

{chr(10).join(f'- {rec}' for rec in report.recommendations)}

---
*Generated by FastAPI Microservices SDK Health Analytics*
        """


class DashboardGenerator:
    """Real-time dashboard generator."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize dashboard generator."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def generate_dashboard_data(
        self,
        data_points: List[HealthDataPoint],
        dashboard_type: str = "overview"
    ) -> DashboardData:
        """Generate dashboard data."""
        try:
            dashboard_id = f"dashboard_{dashboard_type}_{int(time.time())}"
            
            widgets = await self._generate_widgets(data_points, dashboard_type)
            
            dashboard = DashboardData(
                dashboard_id=dashboard_id,
                title=f"Health Analytics Dashboard - {dashboard_type.title()}",
                generated_at=datetime.now(timezone.utc),
                refresh_interval=self.config.dashboard_refresh_interval,
                widgets=widgets,
                filters={
                    'time_range': '24h',
                    'service': self.config.service_name,
                    'environment': self.config.environment
                },
                metadata={
                    'data_points_count': len(data_points),
                    'dashboard_type': dashboard_type
                }
            )
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard data: {e}")
            raise ReportGenerationError(
                "Failed to generate dashboard data",
                original_error=e
            )
    
    async def _generate_widgets(
        self,
        data_points: List[HealthDataPoint],
        dashboard_type: str
    ) -> List[Dict[str, Any]]:
        """Generate dashboard widgets."""
        try:
            widgets = []
            
            if dashboard_type == "overview":
                widgets.extend([
                    await self._create_health_status_widget(data_points),
                    await self._create_response_time_chart_widget(data_points),
                    await self._create_availability_gauge_widget(data_points),
                    await self._create_error_rate_widget(data_points)
                ])
            elif dashboard_type == "performance":
                widgets.extend([
                    await self._create_response_time_trend_widget(data_points),
                    await self._create_percentile_chart_widget(data_points),
                    await self._create_throughput_widget(data_points)
                ])
            elif dashboard_type == "reliability":
                widgets.extend([
                    await self._create_uptime_widget(data_points),
                    await self._create_incident_timeline_widget(data_points),
                    await self._create_mttr_widget(data_points)
                ])
            
            return widgets
            
        except Exception as e:
            self.logger.warning(f"Error generating widgets: {e}")
            return []
    
    async def _create_health_status_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create health status widget."""
        if not data_points:
            status = "unknown"
            color = "gray"
        else:
            recent_data = data_points[-10:] if len(data_points) >= 10 else data_points
            healthy_count = sum(1 for dp in recent_data if dp.status.value == "healthy")
            health_percentage = healthy_count / len(recent_data)
            
            if health_percentage >= 0.95:
                status = "healthy"
                color = "green"
            elif health_percentage >= 0.80:
                status = "degraded"
                color = "yellow"
            else:
                status = "unhealthy"
                color = "red"
        
        return {
            'type': 'status_indicator',
            'title': 'Current Health Status',
            'data': {
                'status': status,
                'color': color,
                'percentage': health_percentage * 100 if data_points else 0
            },
            'size': 'small'
        }
    
    async def _create_response_time_chart_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create response time chart widget."""
        chart_data = []
        
        for dp in data_points[-50:]:  # Last 50 data points
            chart_data.append({
                'timestamp': dp.timestamp.isoformat(),
                'response_time': dp.response_time
            })
        
        return {
            'type': 'line_chart',
            'title': 'Response Time Trend',
            'data': {
                'series': [
                    {
                        'name': 'Response Time (ms)',
                        'data': chart_data
                    }
                ],
                'x_axis': 'timestamp',
                'y_axis': 'response_time'
            },
            'size': 'large'
        }
    
    async def _create_availability_gauge_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create availability gauge widget."""
        if not data_points:
            availability = 0
        else:
            healthy_count = sum(1 for dp in data_points if dp.status.value == "healthy")
            availability = (healthy_count / len(data_points)) * 100
        
        return {
            'type': 'gauge',
            'title': 'Availability',
            'data': {
                'value': availability,
                'min': 0,
                'max': 100,
                'unit': '%',
                'thresholds': [
                    {'value': 95, 'color': 'red'},
                    {'value': 99, 'color': 'yellow'},
                    {'value': 100, 'color': 'green'}
                ]
            },
            'size': 'medium'
        }
    
    async def _create_error_rate_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create error rate widget."""
        if not data_points:
            error_rate = 0
        else:
            total_errors = sum(dp.error_count for dp in data_points)
            error_rate = (total_errors / len(data_points)) * 100
        
        return {
            'type': 'metric',
            'title': 'Error Rate',
            'data': {
                'value': error_rate,
                'unit': '%',
                'trend': 'stable'  # Could be calculated from historical data
            },
            'size': 'small'
        }
    
    async def _create_response_time_trend_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create response time trend widget."""
        # Implementation similar to response time chart but with trend analysis
        return await self._create_response_time_chart_widget(data_points)
    
    async def _create_percentile_chart_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create percentile chart widget."""
        if not data_points:
            return {'type': 'chart', 'title': 'Response Time Percentiles', 'data': {}, 'size': 'medium'}
        
        response_times = sorted([dp.response_time for dp in data_points])
        n = len(response_times)
        
        percentiles = {
            'p50': response_times[int(0.5 * n)] if n > 0 else 0,
            'p95': response_times[int(0.95 * n)] if n > 0 else 0,
            'p99': response_times[int(0.99 * n)] if n > 0 else 0
        }
        
        return {
            'type': 'bar_chart',
            'title': 'Response Time Percentiles',
            'data': {
                'categories': list(percentiles.keys()),
                'values': list(percentiles.values())
            },
            'size': 'medium'
        }
    
    async def _create_throughput_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create throughput widget."""
        if not data_points:
            throughput = 0
        else:
            # Calculate requests per minute based on data points
            time_span = (data_points[-1].timestamp - data_points[0].timestamp).total_seconds() / 60
            throughput = len(data_points) / time_span if time_span > 0 else 0
        
        return {
            'type': 'metric',
            'title': 'Throughput',
            'data': {
                'value': throughput,
                'unit': 'req/min',
                'trend': 'stable'
            },
            'size': 'small'
        }
    
    async def _create_uptime_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create uptime widget."""
        return await self._create_availability_gauge_widget(data_points)
    
    async def _create_incident_timeline_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create incident timeline widget."""
        incidents = []
        in_incident = False
        incident_start = None
        
        for dp in data_points:
            if dp.status.value != "healthy" and not in_incident:
                incident_start = dp.timestamp
                in_incident = True
            elif dp.status.value == "healthy" and in_incident:
                incidents.append({
                    'start': incident_start.isoformat(),
                    'end': dp.timestamp.isoformat(),
                    'duration': (dp.timestamp - incident_start).total_seconds()
                })
                in_incident = False
        
        return {
            'type': 'timeline',
            'title': 'Incident Timeline',
            'data': {
                'incidents': incidents[-10:]  # Last 10 incidents
            },
            'size': 'large'
        }
    
    async def _create_mttr_widget(self, data_points: List[HealthDataPoint]) -> Dict[str, Any]:
        """Create MTTR widget."""
        recovery_times = []
        downtime_start = None
        
        for dp in data_points:
            if dp.status.value != "healthy" and downtime_start is None:
                downtime_start = dp.timestamp
            elif dp.status.value == "healthy" and downtime_start is not None:
                recovery_time = (dp.timestamp - downtime_start).total_seconds() / 60  # Minutes
                recovery_times.append(recovery_time)
                downtime_start = None
        
        mttr = sum(recovery_times) / len(recovery_times) if recovery_times else 0
        
        return {
            'type': 'metric',
            'title': 'Mean Time To Recovery',
            'data': {
                'value': mttr,
                'unit': 'minutes',
                'trend': 'stable'
            },
            'size': 'small'
        }


class SLAMonitor:
    """SLA monitoring and compliance tracking."""
    
    def __init__(self, config: AnalyticsConfig):
        """Initialize SLA monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Default SLA thresholds
        self.sla_thresholds = {
            'availability': 99.9,      # 99.9% uptime
            'response_time_p95': 1.0,  # 1 second 95th percentile
            'response_time_p99': 2.0,  # 2 seconds 99th percentile
            'error_rate': 0.1          # 0.1% error rate
        }
    
    async def calculate_sla_metrics(
        self,
        data_points: List[HealthDataPoint],
        custom_thresholds: Optional[Dict[str, float]] = None
    ) -> SLAMetrics:
        """Calculate SLA compliance metrics."""
        try:
            thresholds = {**self.sla_thresholds, **(custom_thresholds or {})}
            
            if not data_points:
                return SLAMetrics(
                    availability_percentage=0.0,
                    response_time_p95=0.0,
                    response_time_p99=0.0,
                    error_rate_percentage=0.0,
                    uptime_hours=0.0,
                    downtime_incidents=0,
                    sla_compliance_score=0.0
                )
            
            # Calculate availability
            healthy_count = sum(1 for dp in data_points if dp.status.value == "healthy")
            availability_percentage = (healthy_count / len(data_points)) * 100
            
            # Calculate response time percentiles
            response_times = sorted([dp.response_time for dp in data_points])
            n = len(response_times)
            
            p95_index = int(0.95 * n)
            p99_index = int(0.99 * n)
            
            response_time_p95 = response_times[p95_index] if p95_index < n else 0
            response_time_p99 = response_times[p99_index] if p99_index < n else 0
            
            # Calculate error rate
            total_errors = sum(dp.error_count for dp in data_points)
            error_rate_percentage = (total_errors / len(data_points)) * 100
            
            # Calculate uptime and downtime
            time_span = (data_points[-1].timestamp - data_points[0].timestamp).total_seconds() / 3600
            uptime_hours = time_span * (availability_percentage / 100)
            
            downtime_incidents = await self._count_sla_violations(data_points, thresholds)
            
            # Calculate overall SLA compliance score
            sla_compliance_score = await self._calculate_sla_compliance_score(
                availability_percentage,
                response_time_p95,
                response_time_p99,
                error_rate_percentage,
                thresholds
            )
            
            # Identify violations
            violations = await self._identify_sla_violations(
                data_points,
                thresholds,
                availability_percentage,
                response_time_p95,
                response_time_p99,
                error_rate_percentage
            )
            
            return SLAMetrics(
                availability_percentage=availability_percentage,
                response_time_p95=response_time_p95,
                response_time_p99=response_time_p99,
                error_rate_percentage=error_rate_percentage,
                uptime_hours=uptime_hours,
                downtime_incidents=downtime_incidents,
                sla_compliance_score=sla_compliance_score,
                violations=violations
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating SLA metrics: {e}")
            raise ReportGenerationError(
                "Failed to calculate SLA metrics",
                original_error=e
            )
    
    async def _count_sla_violations(
        self,
        data_points: List[HealthDataPoint],
        thresholds: Dict[str, float]
    ) -> int:
        """Count SLA violations."""
        violations = 0
        
        for dp in data_points:
            # Check availability violation
            if dp.status.value != "healthy":
                violations += 1
            
            # Check response time violation
            elif dp.response_time > thresholds.get('response_time_p95', 1.0):
                violations += 1
            
            # Check error rate violation
            elif dp.error_count > 0:
                violations += 1
        
        return violations
    
    async def _calculate_sla_compliance_score(
        self,
        availability: float,
        response_time_p95: float,
        response_time_p99: float,
        error_rate: float,
        thresholds: Dict[str, float]
    ) -> float:
        """Calculate overall SLA compliance score."""
        try:
            scores = []
            
            # Availability score
            availability_score = min(1.0, availability / thresholds.get('availability', 99.9))
            scores.append(availability_score)
            
            # Response time scores
            p95_threshold = thresholds.get('response_time_p95', 1.0)
            p95_score = max(0.0, 1.0 - (response_time_p95 / p95_threshold - 1.0)) if response_time_p95 <= p95_threshold else 0.0
            scores.append(p95_score)
            
            p99_threshold = thresholds.get('response_time_p99', 2.0)
            p99_score = max(0.0, 1.0 - (response_time_p99 / p99_threshold - 1.0)) if response_time_p99 <= p99_threshold else 0.0
            scores.append(p99_score)
            
            # Error rate score
            error_threshold = thresholds.get('error_rate', 0.1)
            error_score = max(0.0, 1.0 - (error_rate / error_threshold)) if error_rate <= error_threshold else 0.0
            scores.append(error_score)
            
            # Calculate weighted average (all metrics equally weighted)
            return sum(scores) / len(scores) * 100  # Convert to percentage
            
        except Exception as e:
            self.logger.warning(f"Error calculating SLA compliance score: {e}")
            return 0.0
    
    async def _identify_sla_violations(
        self,
        data_points: List[HealthDataPoint],
        thresholds: Dict[str, float],
        availability: float,
        response_time_p95: float,
        response_time_p99: float,
        error_rate: float
    ) -> List[Dict[str, Any]]:
        """Identify specific SLA violations."""
        violations = []
        
        # Availability violations
        if availability < thresholds.get('availability', 99.9):
            violations.append({
                'type': 'availability',
                'threshold': thresholds.get('availability', 99.9),
                'actual': availability,
                'severity': 'critical' if availability < 95.0 else 'warning',
                'description': f"Availability {availability:.2f}% below SLA threshold {thresholds.get('availability', 99.9)}%"
            })
        
        # Response time violations
        if response_time_p95 > thresholds.get('response_time_p95', 1.0):
            violations.append({
                'type': 'response_time_p95',
                'threshold': thresholds.get('response_time_p95', 1.0),
                'actual': response_time_p95,
                'severity': 'warning',
                'description': f"95th percentile response time {response_time_p95:.3f}s exceeds SLA threshold {thresholds.get('response_time_p95', 1.0)}s"
            })
        
        if response_time_p99 > thresholds.get('response_time_p99', 2.0):
            violations.append({
                'type': 'response_time_p99',
                'threshold': thresholds.get('response_time_p99', 2.0),
                'actual': response_time_p99,
                'severity': 'critical',
                'description': f"99th percentile response time {response_time_p99:.3f}s exceeds SLA threshold {thresholds.get('response_time_p99', 2.0)}s"
            })
        
        # Error rate violations
        if error_rate > thresholds.get('error_rate', 0.1):
            violations.append({
                'type': 'error_rate',
                'threshold': thresholds.get('error_rate', 0.1),
                'actual': error_rate,
                'severity': 'critical' if error_rate > 1.0 else 'warning',
                'description': f"Error rate {error_rate:.2f}% exceeds SLA threshold {thresholds.get('error_rate', 0.1)}%"
            })
        
        return violations


def create_health_reporter(config: AnalyticsConfig) -> HealthReporter:
    """Create health reporter instance."""
    return HealthReporter(config)


# Export main classes
__all__ = [
    'ReportType',
    'ReportPeriod',
    'HealthReport',
    'SLAMetrics',
    'DashboardData',
    'HealthReporter',
    'DashboardGenerator',
    'SLAMonitor',
    'create_health_reporter',
]
"""
Compliance Dashboards and Reporting System for FastAPI Microservices SDK.
This module provides compliance reporting, audit dashboards, and regulatory
compliance features for enterprise logging systems.
Author: FastAPI Microservices SDK
Version: 1.0.0
"""
import json
import statistics
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging

from .config import LoggingConfig, ComplianceStandard
from .exceptions import LoggingError
from .audit import AuditLogger, AuditRecord, ComplianceFramework
from .search import LogSearchEngine, SearchQuery, SearchCriteria, SearchOperator


class ReportType(str, Enum):
    """Report type enumeration."""
    COMPLIANCE_SUMMARY = "compliance_summary"
    AUDIT_TRAIL = "audit_trail"
    ACCESS_REPORT = "access_report"
    DATA_USAGE = "data_usage"
    SECURITY_EVENTS = "security_events"
    RETENTION_REPORT = "retention_report"
    VIOLATION_REPORT = "violation_report"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"
    EXCEL = "excel"


class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class ComplianceMetric:
    """Compliance metric definition."""
    name: str
    description: str
    framework: ComplianceFramework
    current_value: float
    target_value: float
    unit: str
    status: ComplianceStatus
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'framework': self.framework.value,
            'current_value': self.current_value,
            'target_value': self.target_value,
            'unit': self.unit,
            'status': self.status.value,
            'last_updated': self.last_updated.isoformat(),
            'compliance_percentage': min((self.current_value / self.target_value) * 100, 100) if self.target_value > 0 else 0
        }


@dataclass
class ComplianceReport:
    """Compliance report container."""
    report_id: str
    report_type: ReportType
    framework: ComplianceFramework
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    
    # Report data
    metrics: List[ComplianceMetric] = field(default_factory=list)
    violations: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Summary
    overall_status: ComplianceStatus = ComplianceStatus.UNKNOWN
    compliance_score: float = 0.0
    
    # Metadata
    generated_by: str = "system"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'report_type': self.report_type.value,
            'framework': self.framework.value,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'metrics': [metric.to_dict() for metric in self.metrics],
            'violations': self.violations,
            'recommendations': self.recommendations,
            'overall_status': self.overall_status.value,
            'compliance_score': self.compliance_score,
            'generated_by': self.generated_by,
            'tags': self.tags
        }


@dataclass
class DashboardWidget:
    """Dashboard widget definition."""
    widget_id: str
    title: str
    widget_type: str  # chart, table, metric, alert
    query: SearchQuery
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    refresh_interval: int = 300  # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'widget_id': self.widget_id,
            'title': self.title,
            'widget_type': self.widget_type,
            'query': {
                'criteria': [(c.field, c.operator.value, c.value) for c in self.query.criteria],
                'time_range': self.query.time_range,
                'limit': self.query.limit
            },
            'visualization_config': self.visualization_config,
            'refresh_interval': self.refresh_interval
        }


@dataclass
class Dashboard:
    """Compliance dashboard definition."""
    dashboard_id: str
    title: str
    description: str
    framework: ComplianceFramework
    widgets: List[DashboardWidget] = field(default_factory=list)
    
    # Access control
    allowed_roles: List[str] = field(default_factory=list)
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'dashboard_id': self.dashboard_id,
            'title': self.title,
            'description': self.description,
            'framework': self.framework.value,
            'widgets': [widget.to_dict() for widget in self.widgets],
            'allowed_roles': self.allowed_roles,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }


class ComplianceDashboardManager:
    """Compliance dashboard and reporting manager."""
    
    def __init__(
        self,
        config: LoggingConfig,
        audit_logger: AuditLogger,
        search_engine: LogSearchEngine
    ):
        self.config = config
        self.audit_logger = audit_logger
        self.search_engine = search_engine
        self.logger = logging.getLogger(__name__)
        
        # Dashboards and reports
        self.dashboards: Dict[str, Dashboard] = {}
        self.reports: Dict[str, ComplianceReport] = {}
        
        # Compliance metrics cache
        self._metrics_cache: Dict[str, ComplianceMetric] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Initialize default dashboards
        self._create_default_dashboards()
    
    def _create_default_dashboards(self):
        """Create default compliance dashboards."""
        # GDPR Dashboard
        gdpr_dashboard = self._create_gdpr_dashboard()
        self.dashboards[gdpr_dashboard.dashboard_id] = gdpr_dashboard
        
        # HIPAA Dashboard
        hipaa_dashboard = self._create_hipaa_dashboard()
        self.dashboards[hipaa_dashboard.dashboard_id] = hipaa_dashboard
        
        # SOX Dashboard
        sox_dashboard = self._create_sox_dashboard()
        self.dashboards[sox_dashboard.dashboard_id] = sox_dashboard
    
    def _create_gdpr_dashboard(self) -> Dashboard:
        """Create GDPR compliance dashboard."""
        widgets = [
            # Data access requests widget
            DashboardWidget(
                widget_id="gdpr_data_access",
                title="Data Access Requests",
                widget_type="chart",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_type", SearchOperator.EQUALS, "data_access"),
                        SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "gdpr")
                    ]
                ),
                visualization_config={
                    "chart_type": "line",
                    "x_axis": "timestamp",
                    "y_axis": "count",
                    "group_by": "data_subject_id"
                }
            ),
            
            # Data deletion requests widget
            DashboardWidget(
                widget_id="gdpr_data_deletion",
                title="Data Deletion Requests",
                widget_type="table",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_type", SearchOperator.EQUALS, "data_deletion"),
                        SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "gdpr")
                    ]
                ),
                visualization_config={
                    "columns": ["timestamp", "data_subject_id", "outcome", "data_categories"]
                }
            ),
            
            # Consent management widget
            DashboardWidget(
                widget_id="gdpr_consent",
                title="Consent Management",
                widget_type="metric",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_category", SearchOperator.EQUALS, "consent_management")
                    ]
                ),
                visualization_config={
                    "metric_type": "percentage",
                    "calculation": "consent_given / total_requests"
                }
            )
        ]
        
        return Dashboard(
            dashboard_id="gdpr_compliance",
            title="GDPR Compliance Dashboard",
            description="Monitor GDPR compliance metrics and data subject rights",
            framework=ComplianceFramework.GDPR,
            widgets=widgets,
            allowed_roles=["compliance_officer", "data_protection_officer", "admin"]
        )
    
    def _create_hipaa_dashboard(self) -> Dashboard:
        """Create HIPAA compliance dashboard."""
        widgets = [
            # PHI access widget
            DashboardWidget(
                widget_id="hipaa_phi_access",
                title="PHI Access Events",
                widget_type="chart",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("contains_phi", SearchOperator.EQUALS, True),
                        SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "hipaa")
                    ]
                ),
                visualization_config={
                    "chart_type": "bar",
                    "x_axis": "healthcare_provider_id",
                    "y_axis": "count"
                }
            ),
            
            # Minimum necessary compliance
            DashboardWidget(
                widget_id="hipaa_minimum_necessary",
                title="Minimum Necessary Compliance",
                widget_type="metric",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_type", SearchOperator.EQUALS, "medical_access"),
                        SearchCriteria("minimum_necessary", SearchOperator.EQUALS, True)
                    ]
                ),
                visualization_config={
                    "metric_type": "percentage",
                    "target": 100
                }
            ),
            
            # Breach incidents widget
            DashboardWidget(
                widget_id="hipaa_breaches",
                title="Security Incidents",
                widget_type="alert",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_category", SearchOperator.EQUALS, "security_incident"),
                        SearchCriteria("contains_phi", SearchOperator.EQUALS, True)
                    ]
                ),
                visualization_config={
                    "alert_threshold": 1,
                    "severity": "critical"
                }
            )
        ]
        
        return Dashboard(
            dashboard_id="hipaa_compliance",
            title="HIPAA Compliance Dashboard",
            description="Monitor HIPAA compliance and PHI protection",
            framework=ComplianceFramework.HIPAA,
            widgets=widgets,
            allowed_roles=["compliance_officer", "privacy_officer", "admin"]
        )
    
    def _create_sox_dashboard(self) -> Dashboard:
        """Create SOX compliance dashboard."""
        widgets = [
            # Financial data access widget
            DashboardWidget(
                widget_id="sox_financial_access",
                title="Financial Data Access",
                widget_type="table",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_type", SearchOperator.EQUALS, "financial_transaction"),
                        SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "sox")
                    ]
                ),
                visualization_config={
                    "columns": ["timestamp", "user_id", "financial_record_id", "sox_section", "outcome"]
                }
            ),
            
            # Control effectiveness widget
            DashboardWidget(
                widget_id="sox_controls",
                title="Control Effectiveness",
                widget_type="metric",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_category", SearchOperator.EQUALS, "sox_compliance"),
                        SearchCriteria("outcome", SearchOperator.EQUALS, "success")
                    ]
                ),
                visualization_config={
                    "metric_type": "percentage",
                    "target": 95
                }
            ),
            
            # Segregation of duties widget
            DashboardWidget(
                widget_id="sox_segregation",
                title="Segregation of Duties Violations",
                widget_type="alert",
                query=SearchQuery(
                    criteria=[
                        SearchCriteria("event_category", SearchOperator.EQUALS, "segregation_violation")
                    ]
                ),
                visualization_config={
                    "alert_threshold": 0,
                    "severity": "high"
                }
            )
        ]
        
        return Dashboard(
            dashboard_id="sox_compliance",
            title="SOX Compliance Dashboard",
            description="Monitor SOX compliance and financial controls",
            framework=ComplianceFramework.SOX,
            widgets=widgets,
            allowed_roles=["compliance_officer", "financial_controller", "admin"]
        )
    
    def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        report_type: ReportType,
        period_start: datetime,
        period_end: datetime,
        **kwargs
    ) -> ComplianceReport:
        """Generate compliance report."""
        try:
            report_id = f"report-{framework.value}-{report_type.value}-{int(period_start.timestamp())}"
            
            report = ComplianceReport(
                report_id=report_id,
                report_type=report_type,
                framework=framework,
                generated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end,
                generated_by=kwargs.get('generated_by', 'system')
            )
            
            # Generate report based on type and framework
            if report_type == ReportType.COMPLIANCE_SUMMARY:
                self._generate_compliance_summary(report)
            elif report_type == ReportType.AUDIT_TRAIL:
                self._generate_audit_trail_report(report)
            elif report_type == ReportType.ACCESS_REPORT:
                self._generate_access_report(report)
            elif report_type == ReportType.DATA_USAGE:
                self._generate_data_usage_report(report)
            elif report_type == ReportType.SECURITY_EVENTS:
                self._generate_security_events_report(report)
            elif report_type == ReportType.RETENTION_REPORT:
                self._generate_retention_report(report)
            elif report_type == ReportType.VIOLATION_REPORT:
                self._generate_violation_report(report)
            
            # Calculate overall compliance score
            self._calculate_compliance_score(report)
            
            # Store report
            self.reports[report_id] = report
            
            self.logger.info(f"Generated compliance report: {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report: {e}")
            raise LoggingError(f"Failed to generate compliance report: {e}", original_error=e)
    
    def _generate_compliance_summary(self, report: ComplianceReport):
        """Generate compliance summary report."""
        # Get compliance metrics for the framework
        metrics = self._get_compliance_metrics(report.framework, report.period_start, report.period_end)
        report.metrics.extend(metrics)
        
        # Add framework-specific recommendations
        if report.framework == ComplianceFramework.GDPR:
            report.recommendations.extend([
                "Ensure all data processing has lawful basis",
                "Implement data subject rights automation",
                "Regular privacy impact assessments",
                "Update privacy notices and consent mechanisms"
            ])
        elif report.framework == ComplianceFramework.HIPAA:
            report.recommendations.extend([
                "Conduct regular risk assessments",
                "Implement minimum necessary standards",
                "Ensure business associate agreements are current",
                "Regular security awareness training"
            ])
        elif report.framework == ComplianceFramework.SOX:
            report.recommendations.extend([
                "Strengthen internal controls over financial reporting",
                "Regular control testing and documentation",
                "Segregation of duties enforcement",
                "Management assessment of control effectiveness"
            ])
    
    def _generate_audit_trail_report(self, report: ComplianceReport):
        """Generate audit trail report."""
        # Search for audit events in the period
        query = SearchQuery(
            criteria=[
                SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, report.framework.value),
                SearchCriteria("event_category", SearchOperator.CONTAINS, "audit")
            ],
            time_range=(report.period_start, report.period_end),
            limit=10000
        )
        
        # Execute search (assuming file-based for now)
        if self.config.file_output and self.config.file_path:
            result = self.search_engine.search(query, self.config.file_path)
            
            # Add audit events to report
            for log in result.logs:
                report.violations.append({
                    'timestamp': log.get('timestamp'),
                    'event_type': log.get('event_type'),
                    'user_id': log.get('user_id'),
                    'outcome': log.get('outcome'),
                    'description': log.get('description')
                })
    
    def _generate_access_report(self, report: ComplianceReport):
        """Generate access report."""
        # Framework-specific access patterns
        if report.framework == ComplianceFramework.GDPR:
            event_types = ["data_access", "data_modification", "data_deletion"]
        elif report.framework == ComplianceFramework.HIPAA:
            event_types = ["medical_access", "phi_access"]
        elif report.framework == ComplianceFramework.SOX:
            event_types = ["financial_transaction", "financial_access"]
        else:
            event_types = ["data_access"]
        
        for event_type in event_types:
            query = SearchQuery(
                criteria=[
                    SearchCriteria("event_type", SearchOperator.EQUALS, event_type)
                ],
                time_range=(report.period_start, report.period_end),
                limit=1000
            )
            
            if self.config.file_output and self.config.file_path:
                result = self.search_engine.search(query, self.config.file_path)
                
                # Analyze access patterns
                access_summary = {
                    'event_type': event_type,
                    'total_accesses': result.total_count,
                    'unique_users': len(set(log.get('user_id') for log in result.logs if log.get('user_id'))),
                    'success_rate': len([log for log in result.logs if log.get('outcome') == 'success']) / max(1, result.total_count)
                }
                report.violations.append(access_summary)
    
    def _generate_data_usage_report(self, report: ComplianceReport):
        """Generate data usage report."""
        # Data processing activities
        query = SearchQuery(
            criteria=[
                SearchCriteria("event_category", SearchOperator.EQUALS, "data_processing")
            ],
            time_range=(report.period_start, report.period_end)
        )
        
        if self.config.file_output and self.config.file_path:
            result = self.search_engine.search(query, self.config.file_path)
            
            # Analyze data usage patterns
            data_categories = {}
            for log in result.logs:
                categories = log.get('data_categories', [])
                for category in categories:
                    data_categories[category] = data_categories.get(category, 0) + 1
            
            report.violations.append({
                'data_usage_summary': data_categories,
                'total_processing_activities': result.total_count
            })
    
    def _generate_security_events_report(self, report: ComplianceReport):
        """Generate security events report."""
        query = SearchQuery(
            criteria=[
                SearchCriteria("event_category", SearchOperator.EQUALS, "security_event")
            ],
            time_range=(report.period_start, report.period_end)
        )
        
        if self.config.file_output and self.config.file_path:
            result = self.search_engine.search(query, self.config.file_path)
            
            # Categorize security events
            security_summary = {
                'total_security_events': result.total_count,
                'critical_events': len([log for log in result.logs if log.get('risk_level') == 'critical']),
                'high_risk_events': len([log for log in result.logs if log.get('risk_level') == 'high']),
                'incidents_resolved': len([log for log in result.logs if log.get('outcome') == 'resolved'])
            }
            report.violations.append(security_summary)
    
    def _generate_retention_report(self, report: ComplianceReport):
        """Generate retention report."""
        # This would integrate with the retention manager
        retention_summary = {
            'retention_policies_active': 5,  # Placeholder
            'logs_archived': 1000,  # Placeholder
            'logs_deleted': 500,  # Placeholder
            'compliance_violations': 0  # Placeholder
        }
        report.violations.append(retention_summary)
    
    def _generate_violation_report(self, report: ComplianceReport):
        """Generate violation report."""
        query = SearchQuery(
            criteria=[
                SearchCriteria("event_category", SearchOperator.EQUALS, "compliance_violation")
            ],
            time_range=(report.period_start, report.period_end)
        )
        
        if self.config.file_output and self.config.file_path:
            result = self.search_engine.search(query, self.config.file_path)
            
            for log in result.logs:
                report.violations.append({
                    'timestamp': log.get('timestamp'),
                    'violation_type': log.get('violation_type'),
                    'severity': log.get('severity'),
                    'description': log.get('description'),
                    'remediation_status': log.get('remediation_status', 'pending')
                })
    
    def _get_compliance_metrics(
        self,
        framework: ComplianceFramework,
        period_start: datetime,
        period_end: datetime
    ) -> List[ComplianceMetric]:
        """Get compliance metrics for framework."""
        metrics = []
        
        if framework == ComplianceFramework.GDPR:
            metrics.extend([
                ComplianceMetric(
                    name="Data Subject Requests Response Time",
                    description="Average response time for data subject requests",
                    framework=framework,
                    current_value=25.0,  # days
                    target_value=30.0,
                    unit="days",
                    status=ComplianceStatus.COMPLIANT,
                    last_updated=datetime.now(timezone.utc)
                ),
                ComplianceMetric(
                    name="Consent Rate",
                    description="Percentage of valid consents",
                    framework=framework,
                    current_value=95.0,
                    target_value=90.0,
                    unit="percentage",
                    status=ComplianceStatus.COMPLIANT,
                    last_updated=datetime.now(timezone.utc)
                )
            ])
        
        elif framework == ComplianceFramework.HIPAA:
            metrics.extend([
                ComplianceMetric(
                    name="PHI Access Control",
                    description="Percentage of PHI accesses with proper authorization",
                    framework=framework,
                    current_value=98.5,
                    target_value=95.0,
                    unit="percentage",
                    status=ComplianceStatus.COMPLIANT,
                    last_updated=datetime.now(timezone.utc)
                ),
                ComplianceMetric(
                    name="Minimum Necessary Compliance",
                    description="Adherence to minimum necessary standard",
                    framework=framework,
                    current_value=92.0,
                    target_value=95.0,
                    unit="percentage",
                    status=ComplianceStatus.PARTIAL,
                    last_updated=datetime.now(timezone.utc)
                )
            ])
        
        elif framework == ComplianceFramework.SOX:
            metrics.extend([
                ComplianceMetric(
                    name="Control Effectiveness",
                    description="Percentage of effective internal controls",
                    framework=framework,
                    current_value=96.0,
                    target_value=95.0,
                    unit="percentage",
                    status=ComplianceStatus.COMPLIANT,
                    last_updated=datetime.now(timezone.utc)
                ),
                ComplianceMetric(
                    name="Segregation of Duties",
                    description="Compliance with segregation of duties requirements",
                    framework=framework,
                    current_value=100.0,
                    target_value=100.0,
                    unit="percentage",
                    status=ComplianceStatus.COMPLIANT,
                    last_updated=datetime.now(timezone.utc)
                )
            ])
        
        return metrics
    
    def _calculate_compliance_score(self, report: ComplianceReport):
        """Calculate overall compliance score."""
        if not report.metrics:
            report.compliance_score = 0.0
            report.overall_status = ComplianceStatus.UNKNOWN
            return
        
        # Calculate weighted average of metric compliance
        total_score = 0.0
        compliant_count = 0
        
        for metric in report.metrics:
            if metric.target_value > 0:
                score = min((metric.current_value / metric.target_value) * 100, 100)
                total_score += score
                
                if metric.status == ComplianceStatus.COMPLIANT:
                    compliant_count += 1
        
        report.compliance_score = total_score / len(report.metrics) if report.metrics else 0.0
        
        # Determine overall status
        compliance_rate = compliant_count / len(report.metrics)
        if compliance_rate >= 0.95:
            report.overall_status = ComplianceStatus.COMPLIANT
        elif compliance_rate >= 0.75:
            report.overall_status = ComplianceStatus.PARTIAL
        else:
            report.overall_status = ComplianceStatus.NON_COMPLIANT
    
    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard by ID."""
        return self.dashboards.get(dashboard_id)
    
    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get report by ID."""
        return self.reports.get(report_id)
    
    def list_dashboards(self, framework: Optional[ComplianceFramework] = None) -> List[Dashboard]:
        """List dashboards, optionally filtered by framework."""
        dashboards = list(self.dashboards.values())
        if framework:
            dashboards = [d for d in dashboards if d.framework == framework]
        return dashboards
    
    def list_reports(
        self,
        framework: Optional[ComplianceFramework] = None,
        report_type: Optional[ReportType] = None
    ) -> List[ComplianceReport]:
        """List reports with optional filters."""
        reports = list(self.reports.values())
        if framework:
            reports = [r for r in reports if r.framework == framework]
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        return reports
    
    def export_report(
        self,
        report_id: str,
        format: ReportFormat = ReportFormat.JSON
    ) -> Union[str, bytes]:
        """Export report in specified format."""
        report = self.get_report(report_id)
        if not report:
            raise LoggingError(f"Report not found: {report_id}")
        
        if format == ReportFormat.JSON:
            return json.dumps(report.to_dict(), indent=2, default=str)
        elif format == ReportFormat.CSV:
            return self._export_csv(report)
        elif format == ReportFormat.HTML:
            return self._export_html(report)
        else:
            raise LoggingError(f"Unsupported export format: {format.value}")
    
    def _export_csv(self, report: ComplianceReport) -> str:
        """Export report as CSV."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Metric', 'Current Value', 'Target Value', 'Status', 'Compliance %'])
        
        # Write metrics
        for metric in report.metrics:
            compliance_pct = min((metric.current_value / metric.target_value) * 100, 100) if metric.target_value > 0 else 0
            writer.writerow([
                metric.name,
                metric.current_value,
                metric.target_value,
                metric.status.value,
                f"{compliance_pct:.1f}%"
            ])
        
        return output.getvalue()
    
    def _export_html(self, report: ComplianceReport) -> str:
        """Export report as HTML."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report.framework.value.upper()} Compliance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metric {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
                .compliant {{ background-color: #d4edda; }}
                .partial {{ background-color: #fff3cd; }}
                .non-compliant {{ background-color: #f8d7da; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report.framework.value.upper()} Compliance Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Generated:</strong> {report.generated_at.isoformat()}</p>
                <p><strong>Period:</strong> {report.period_start.isoformat()} to {report.period_end.isoformat()}</p>
                <p><strong>Overall Status:</strong> {report.overall_status.value}</p>
                <p><strong>Compliance Score:</strong> {report.compliance_score:.1f}%</p>
            </div>
            
            <h2>Compliance Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Current Value</th>
                    <th>Target Value</th>
                    <th>Status</th>
                    <th>Compliance %</th>
                </tr>
        """
        
        for metric in report.metrics:
            compliance_pct = min((metric.current_value / metric.target_value) * 100, 100) if metric.target_value > 0 else 0
            status_class = metric.status.value.replace('_', '-')
            html += f"""
                <tr class="{status_class}">
                    <td>{metric.name}</td>
                    <td>{metric.current_value} {metric.unit}</td>
                    <td>{metric.target_value} {metric.unit}</td>
                    <td>{metric.status.value}</td>
                    <td>{compliance_pct:.1f}%</td>
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


# Factory functions
def create_dashboard_manager(
    config: LoggingConfig,
    audit_logger: AuditLogger,
    search_engine: LogSearchEngine
) -> ComplianceDashboardManager:
    """Create compliance dashboard manager."""
    return ComplianceDashboardManager(config, audit_logger, search_engine)


# Export main classes and functions
__all__ = [
    'ReportType',
    'ReportFormat',
    'ComplianceStatus',
    'ComplianceMetric',
    'ComplianceReport',
    'DashboardWidget',
    'Dashboard',
    'ComplianceDashboardManager',
    'create_dashboard_manager',
]
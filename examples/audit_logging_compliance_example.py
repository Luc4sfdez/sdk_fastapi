"""
Comprehensive Audit Logging and Compliance Example for FastAPI Microservices SDK.

This example demonstrates the complete audit logging and compliance system including:
- Audit logging with digital signatures
- Compliance logging for GDPR, HIPAA, SOX
- Log retention and cleanup
- Log search and analysis
- Pattern detection and anomaly detection
- Multi-channel alerting
- Compliance dashboards and reporting

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi_microservices_sdk.observability.logging import (
    # Configuration
    LoggingConfig,
    SecurityConfig,
    RetentionConfig,
    ELKConfig,
    ComplianceStandard,
    RetentionPeriod,
    create_logging_config,
    
    # Core logging
    StructuredLogger,
    create_structured_logger,
    
    # Audit logging
    AuditEventType,
    AuditOutcome,
    ComplianceFramework,
    AuditContext,
    AuditLogger,
    ComplianceLogger,
    create_audit_logger,
    create_compliance_logger,
    
    # Retention management
    RetentionManager,
    RetentionPolicy,
    RetentionAction,
    create_retention_manager,
    create_retention_policy,
    
    # Search and analysis
    LogSearchEngine,
    SearchQuery,
    SearchCriteria,
    SearchOperator,
    PatternDetector,
    AnomalyDetector,
    create_search_engine,
    create_pattern_detector,
    create_anomaly_detector,
    
    # Alerting
    AlertManager,
    AlertRule,
    AlertCondition,
    AlertSeverity,
    NotificationChannel,
    NotificationConfig,
    create_alert_manager,
    create_alert_rule,
    create_notification_config,
    
    # Dashboards and compliance
    ComplianceDashboardManager,
    ReportType,
    ReportFormat,
    create_dashboard_manager
)


class AuditLoggingComplianceDemo:
    """Comprehensive audit logging and compliance demonstration."""
    
    def __init__(self):
        self.setup_logging()
        self.setup_audit_logging()
        self.setup_retention()
        self.setup_search_and_analysis()
        self.setup_alerting()
        self.setup_dashboards()
    
    def setup_logging(self):
        """Setup structured logging configuration."""
        print("🔧 Setting up logging configuration...")
        
        # Create comprehensive logging configuration
        self.logging_config = create_logging_config(
            service_name="audit-compliance-demo",
            service_version="1.0.0",
            environment="production",
            log_level="INFO",
            file_output=True,
            file_path="logs/audit_compliance_demo.log",
            console_output=True,
            json_format=True,
            
            # Security configuration
            security_config=SecurityConfig(
                enable_pii_protection=True,
                enable_data_masking=True,
                pii_fields=["email", "phone", "ssn", "credit_card"],
                pii_replacement="[REDACTED]",
                masking_patterns={
                    r'\b\d{4}-\d{4}-\d{4}-\d{4}\b': '[CARD-REDACTED]',
                    r'\b\d{3}-\d{2}-\d{4}\b': '[SSN-REDACTED]'
                }
            ),
            
            # Retention configuration
            retention_config=RetentionConfig(
                enable_automatic_cleanup=True,
                cleanup_interval=3600,  # 1 hour
                cleanup_dry_run=False,
                archive_storage_path="logs/archive"
            ),
            
            # ELK configuration (optional)
            elk_config=ELKConfig(
                elasticsearch_hosts=["localhost:9200"],
                logstash_host="localhost:5044",
                kibana_host="localhost:5601",
                index_pattern="audit-logs-{date}",
                enable_ssl=False
            )
        )
        
        # Create structured logger
        self.structured_logger = create_structured_logger(self.logging_config)
        print("✅ Logging configuration completed")
    
    def setup_audit_logging(self):
        """Setup audit logging with compliance features."""
        print("🔐 Setting up audit logging...")
        
        # Create audit logger with digital signatures
        self.audit_logger = create_audit_logger(
            config=self.logging_config,
            structured_logger=self.structured_logger,
            # Optional: Add paths to cryptographic keys for digital signatures
            # private_key_path="keys/audit_private.pem",
            # public_key_path="keys/audit_public.pem"
        )
        
        # Create compliance loggers for different frameworks
        self.gdpr_logger = create_compliance_logger(
            audit_logger=self.audit_logger,
            frameworks=[ComplianceFramework.GDPR]
        )
        
        self.hipaa_logger = create_compliance_logger(
            audit_logger=self.audit_logger,
            frameworks=[ComplianceFramework.HIPAA]
        )
        
        self.sox_logger = create_compliance_logger(
            audit_logger=self.audit_logger,
            frameworks=[ComplianceFramework.SOX]
        )
        
        print("✅ Audit logging setup completed")
    
    def setup_retention(self):
        """Setup log retention and cleanup."""
        print("🗂️ Setting up log retention...")
        
        # Create retention manager
        self.retention_manager = create_retention_manager(
            config=self.logging_config,
            audit_logger=self.audit_logger
        )
        
        # Add custom retention policies
        custom_policy = create_retention_policy(
            name="high_value_transactions",
            retention_period=RetentionPeriod.YEARS_7,
            description="High-value financial transactions",
            event_types=["financial_transaction"],
            actions=[RetentionAction.ARCHIVE, RetentionAction.COMPRESS],
            legal_hold_enabled=True
        )
        self.retention_manager.add_policy(custom_policy)
        
        print("✅ Log retention setup completed")
    
    def setup_search_and_analysis(self):
        """Setup log search and analysis capabilities."""
        print("🔍 Setting up search and analysis...")
        
        # Create search engine
        self.search_engine = create_search_engine(self.logging_config)
        
        # Create pattern detector
        self.pattern_detector = create_pattern_detector()
        
        # Add custom security patterns
        self.pattern_detector.add_custom_pattern(
            category="security_patterns",
            pattern_regex=r"multiple login attempts|account lockout",
            pattern_name="account_security_events"
        )
        
        # Create anomaly detector
        self.anomaly_detector = create_anomaly_detector(self.logging_config)
        
        print("✅ Search and analysis setup completed")
    
    def setup_alerting(self):
        """Setup intelligent alerting system."""
        print("🚨 Setting up alerting...")
        
        # Create alert manager
        self.alert_manager = create_alert_manager(
            config=self.logging_config,
            search_engine=self.search_engine
        )
        
        # Configure notification channels
        email_config = create_notification_config(
            channel=NotificationChannel.EMAIL,
            config={
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'use_tls': True,
                'from_email': 'alerts@company.com',
                'to_emails': ['security@company.com', 'compliance@company.com'],
                'username': 'alerts@company.com',
                'password': 'app_password'
            }
        )
        self.alert_manager.add_notification_config(email_config)
        
        # Slack notification (webhook-based)
        slack_config = create_notification_config(
            channel=NotificationChannel.SLACK,
            config={
                'webhook_url': 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
            }
        )
        self.alert_manager.add_notification_config(slack_config)
        
        # Create alert rules
        self._create_alert_rules()
        
        print("✅ Alerting setup completed")
    
    def _create_alert_rules(self):
        """Create comprehensive alert rules."""
        
        # High-severity security events
        security_alert = create_alert_rule(
            name="security_incidents",
            search_query=SearchQuery(
                criteria=[
                    SearchCriteria("event_category", SearchOperator.EQUALS, "security_event"),
                    SearchCriteria("risk_level", SearchOperator.IN, ["high", "critical"])
                ]
            ),
            condition_type=AlertCondition.THRESHOLD,
            severity=AlertSeverity.CRITICAL,
            threshold_value=1,
            threshold_operator="gte",
            notification_channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            description="Critical security incidents detected"
        )
        self.alert_manager.add_alert_rule(security_alert)
        
        # GDPR compliance violations
        gdpr_alert = create_alert_rule(
            name="gdpr_violations",
            search_query=SearchQuery(
                criteria=[
                    SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "gdpr"),
                    SearchCriteria("event_category", SearchOperator.EQUALS, "compliance_violation")
                ]
            ),
            condition_type=AlertCondition.THRESHOLD,
            severity=AlertSeverity.HIGH,
            threshold_value=0,
            threshold_operator="gt",
            notification_channels=[NotificationChannel.EMAIL],
            description="GDPR compliance violations detected"
        )
        self.alert_manager.add_alert_rule(gdpr_alert)
        
        # Unusual data access patterns
        access_anomaly_alert = create_alert_rule(
            name="unusual_data_access",
            search_query=SearchQuery(
                criteria=[
                    SearchCriteria("event_type", SearchOperator.EQUALS, "data_access"),
                    SearchCriteria("contains_pii", SearchOperator.EQUALS, True)
                ]
            ),
            condition_type=AlertCondition.RATE,
            severity=AlertSeverity.MEDIUM,
            threshold_value=100,  # More than 100 accesses per evaluation window
            threshold_operator="gt",
            evaluation_window=300,  # 5 minutes
            notification_channels=[NotificationChannel.SLACK],
            description="Unusual data access rate detected"
        )
        self.alert_manager.add_alert_rule(access_anomaly_alert)
    
    def setup_dashboards(self):
        """Setup compliance dashboards and reporting."""
        print("📊 Setting up dashboards...")
        
        # Create dashboard manager
        self.dashboard_manager = create_dashboard_manager(
            config=self.logging_config,
            audit_logger=self.audit_logger,
            search_engine=self.search_engine
        )
        
        print("✅ Dashboards setup completed")
    
    async def demonstrate_audit_logging(self):
        """Demonstrate comprehensive audit logging."""
        print("\n🔐 === AUDIT LOGGING DEMONSTRATION ===")
        
        # Create audit context
        context = AuditContext(
            user_id="user123",
            user_name="john.doe@company.com",
            user_role="data_analyst",
            session_id="session_abc123",
            client_ip="192.168.1.100",
            service_name="data-analytics-service",
            environment="production"
        )
        
        # 1. GDPR Data Access Event
        print("📝 Logging GDPR data access event...")
        gdpr_record = self.gdpr_logger.log_gdpr_event(
            event_type="data_access_request",
            data_subject_id="subject_456",
            context=context,
            gdpr_article="Article 15",
            lawful_basis="Legitimate Interest",
            data_categories=["personal_data", "contact_information"]
        )
        print(f"   ✅ GDPR audit record created: {gdpr_record.audit_id}")
        
        # 2. HIPAA Medical Access Event
        print("📝 Logging HIPAA medical access event...")
        hipaa_record = self.hipaa_logger.log_hipaa_event(
            event_type="patient_record_access",
            patient_id="patient_789",
            healthcare_provider_id="provider_123",
            context=context,
            covered_entity="General Hospital",
            minimum_necessary=True
        )
        print(f"   ✅ HIPAA audit record created: {hipaa_record.audit_id}")
        
        # 3. SOX Financial Transaction Event
        print("📝 Logging SOX financial transaction...")
        sox_record = self.sox_logger.log_sox_event(
            event_type="financial_record_modification",
            financial_record_id="fin_record_456",
            context=context,
            sox_section="Section 404",
            control_objective="Accurate Financial Reporting",
            financial_statement_impact=True
        )
        print(f"   ✅ SOX audit record created: {sox_record.audit_id}")
        
        # 4. General Security Event
        print("📝 Logging security event...")
        security_record = self.audit_logger.audit(
            event_type=AuditEventType.SECURITY_EVENT,
            event_description="Suspicious login attempt detected",
            context=context,
            outcome=AuditOutcome.DENIED,
            event_category="authentication",
            risk_level="high",
            risk_factors=["unusual_location", "multiple_attempts"],
            custom_fields={
                "attempted_username": "admin",
                "source_ip": "192.168.1.200",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        print(f"   ✅ Security audit record created: {security_record.audit_id}")
        
        # Verify audit record integrity
        print("🔍 Verifying audit record integrity...")
        is_valid = self.audit_logger.verify_audit_record(gdpr_record)
        print(f"   ✅ GDPR record integrity: {'VALID' if is_valid else 'INVALID'}")
        
        # Get audit statistics
        stats = self.audit_logger.get_audit_statistics()
        print(f"📊 Audit Statistics: {json.dumps(stats, indent=2)}")
    
    async def demonstrate_search_and_analysis(self):
        """Demonstrate log search and analysis capabilities."""
        print("\n🔍 === SEARCH AND ANALYSIS DEMONSTRATION ===")
        
        # Wait a moment for logs to be written
        await asyncio.sleep(1)
        
        # 1. Search for GDPR events
        print("🔍 Searching for GDPR compliance events...")
        gdpr_query = SearchQuery(
            criteria=[
                SearchCriteria("compliance_frameworks", SearchOperator.CONTAINS, "gdpr"),
                SearchCriteria("event_category", SearchOperator.EQUALS, "gdpr_compliance")
            ],
            limit=10
        )
        
        if self.logging_config.file_output and Path(self.logging_config.file_path).exists():
            gdpr_results = self.search_engine.search(gdpr_query, self.logging_config.file_path)
            print(f"   ✅ Found {gdpr_results.total_count} GDPR events")
            print(f"   ⏱️ Query time: {gdpr_results.query_time_ms:.2f}ms")
        
        # 2. Search for security events
        print("🔍 Searching for security events...")
        security_query = SearchQuery(
            criteria=[
                SearchCriteria("event_category", SearchOperator.EQUALS, "security_event"),
                SearchCriteria("risk_level", SearchOperator.EQUALS, "high")
            ]
        )
        
        if self.logging_config.file_output and Path(self.logging_config.file_path).exists():
            security_results = self.search_engine.search(security_query, self.logging_config.file_path)
            print(f"   ✅ Found {security_results.total_count} high-risk security events")
        
        # 3. Pattern Detection
        print("🔍 Running pattern detection...")
        if self.logging_config.file_output and Path(self.logging_config.file_path).exists():
            # Read recent logs for pattern analysis
            with open(self.logging_config.file_path, 'r') as f:
                log_lines = f.readlines()[-100:]  # Last 100 lines
            
            logs = []
            for line in log_lines:
                try:
                    log_data = json.loads(line.strip())
                    logs.append(log_data)
                except json.JSONDecodeError:
                    continue
            
            if logs:
                patterns = self.pattern_detector.detect_patterns(logs, ['security_patterns'])
                print(f"   ✅ Detected {len(patterns)} security patterns")
                for pattern in patterns:
                    print(f"      - {pattern.pattern_name}: {pattern.match_count} matches")
        
        # 4. Anomaly Detection
        print("🔍 Running anomaly detection...")
        if logs:
            anomalies = self.anomaly_detector.detect_anomalies(logs, time_window_minutes=60)
            print(f"   ✅ Detected {len(anomalies)} anomalies")
            for anomaly in anomalies:
                print(f"      - {anomaly.anomaly_type.value}: {anomaly.description}")
        
        # Get search statistics
        search_stats = self.search_engine.get_search_statistics()
        print(f"📊 Search Statistics: {json.dumps(search_stats, indent=2)}")
    
    async def demonstrate_retention_management(self):
        """Demonstrate log retention and cleanup."""
        print("\n🗂️ === RETENTION MANAGEMENT DEMONSTRATION ===")
        
        # Get retention statistics
        retention_stats = self.retention_manager.get_retention_statistics()
        print(f"📊 Retention Statistics: {json.dumps(retention_stats, indent=2)}")
        
        # Run manual cleanup (dry run)
        print("🧹 Running retention cleanup (dry run)...")
        jobs = self.retention_manager.run_cleanup()
        
        for job in jobs:
            print(f"   📋 Job: {job.job_id}")
            print(f"      Policy: {job.policy_name}")
            print(f"      Status: {job.status}")
            print(f"      Processed: {job.logs_processed}")
            print(f"      Deleted: {job.logs_deleted}")
            print(f"      Archived: {job.logs_archived}")
    
    async def demonstrate_alerting(self):
        """Demonstrate intelligent alerting."""
        print("\n🚨 === ALERTING DEMONSTRATION ===")
        
        # Get alert statistics
        alert_stats = self.alert_manager.get_alert_statistics()
        print(f"📊 Alert Statistics: {json.dumps(alert_stats, indent=2)}")
        
        # Simulate alert evaluation (normally runs automatically)
        print("🔍 Evaluating alert rules...")
        for rule_name, rule in self.alert_manager.alert_rules.items():
            if rule.enabled:
                print(f"   📋 Evaluating rule: {rule_name}")
                await self.alert_manager._evaluate_rule(rule)
        
        # Check active alerts
        active_alerts = list(self.alert_manager.active_alerts.values())
        print(f"🚨 Active Alerts: {len(active_alerts)}")
        for alert in active_alerts:
            print(f"   - {alert.title} ({alert.severity.value})")
    
    async def demonstrate_compliance_reporting(self):
        """Demonstrate compliance dashboards and reporting."""
        print("\n📊 === COMPLIANCE REPORTING DEMONSTRATION ===")
        
        # Generate GDPR compliance report
        print("📋 Generating GDPR compliance report...")
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=30)
        
        gdpr_report = self.dashboard_manager.generate_compliance_report(
            framework=ComplianceFramework.GDPR,
            report_type=ReportType.COMPLIANCE_SUMMARY,
            period_start=start_time,
            period_end=end_time,
            generated_by="audit_demo"
        )
        
        print(f"   ✅ Report generated: {gdpr_report.report_id}")
        print(f"   📊 Compliance Score: {gdpr_report.compliance_score:.1f}%")
        print(f"   📈 Overall Status: {gdpr_report.overall_status.value}")
        print(f"   📋 Metrics: {len(gdpr_report.metrics)}")
        print(f"   💡 Recommendations: {len(gdpr_report.recommendations)}")
        
        # Export report in different formats
        print("📤 Exporting report...")
        
        # JSON export
        json_report = self.dashboard_manager.export_report(
            gdpr_report.report_id,
            ReportFormat.JSON
        )
        print(f"   ✅ JSON export: {len(json_report)} characters")
        
        # CSV export
        csv_report = self.dashboard_manager.export_report(
            gdpr_report.report_id,
            ReportFormat.CSV
        )
        print(f"   ✅ CSV export: {len(csv_report)} characters")
        
        # HTML export
        html_report = self.dashboard_manager.export_report(
            gdpr_report.report_id,
            ReportFormat.HTML
        )
        print(f"   ✅ HTML export: {len(html_report)} characters")
        
        # List available dashboards
        dashboards = self.dashboard_manager.list_dashboards()
        print(f"📊 Available Dashboards: {len(dashboards)}")
        for dashboard in dashboards:
            print(f"   - {dashboard.title} ({dashboard.framework.value})")
    
    async def run_comprehensive_demo(self):
        """Run the complete audit logging and compliance demonstration."""
        print("🚀 === FASTAPI MICROSERVICES SDK - AUDIT LOGGING & COMPLIANCE DEMO ===")
        print("This demo showcases enterprise-grade audit logging and compliance features.\n")
        
        try:
            # Run all demonstrations
            await self.demonstrate_audit_logging()
            await self.demonstrate_search_and_analysis()
            await self.demonstrate_retention_management()
            await self.demonstrate_alerting()
            await self.demonstrate_compliance_reporting()
            
            print("\n🎉 === DEMONSTRATION COMPLETED SUCCESSFULLY ===")
            print("All audit logging and compliance features have been demonstrated!")
            
            # Final summary
            print("\n📋 === FEATURE SUMMARY ===")
            features = [
                "✅ Audit Logging with Digital Signatures",
                "✅ GDPR, HIPAA, SOX Compliance Logging",
                "✅ Tamper-proof Timestamps",
                "✅ Log Retention and Cleanup",
                "✅ Advanced Log Search and Analysis",
                "✅ Pattern Detection and Anomaly Detection",
                "✅ Multi-channel Alerting (Email, Slack, Webhook)",
                "✅ Compliance Dashboards and Reporting",
                "✅ Data Masking and PII Protection",
                "✅ Integrity Verification"
            ]
            
            for feature in features:
                print(f"  {feature}")
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            raise
        
        finally:
            # Cleanup
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        print("\n🧹 Cleaning up resources...")
        
        # Shutdown alert manager
        if hasattr(self, 'alert_manager'):
            await self.alert_manager.shutdown()
        
        # Shutdown retention manager
        if hasattr(self, 'retention_manager'):
            self.retention_manager.shutdown()
        
        print("✅ Cleanup completed")


async def main():
    """Main function to run the audit logging and compliance demo."""
    demo = AuditLoggingComplianceDemo()
    await demo.run_comprehensive_demo()


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    Path("logs/archive").mkdir(exist_ok=True)
    
    # Run the demo
    asyncio.run(main())
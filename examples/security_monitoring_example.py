"""
Example: Security Monitoring Integration

This example demonstrates how to use the SecurityMonitor for comprehensive
security monitoring across all security components.

Features demonstrated:
- Integrated security logging with correlation IDs
- Performance metrics collection
- Real-time alerting
- Request tracing across security layers
- Metrics aggregation and reporting
"""

import asyncio
import logging
import time
import random
from datetime import datetime, timezone

# Import monitoring components
from fastapi_microservices_sdk.security.advanced.monitoring import (
    SecurityMonitor,
    PerformanceMonitor,
    SecurityMetric,
    MetricType,
    MonitoringLevel,
    create_security_monitor
)
from fastapi_microservices_sdk.security.advanced.logging import (
    SecurityEvent,
    SecurityEventSeverity
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_basic_monitoring():
    """Demonstrate basic security monitoring capabilities."""
    logger.info("=== Basic Security Monitoring ===")
    
    # Create security monitor
    monitor = create_security_monitor(MonitoringLevel.DETAILED)
    
    # Start monitoring a request
    correlation_id = await monitor.start_request_monitoring(
        metadata={"user_id": "user123", "endpoint": "/api/secure-data"}
    )
    logger.info(f"Started monitoring request: {correlation_id}")
    
    # Log some security events
    events = [
        SecurityEvent(
            event_type="authentication_attempt",
            severity=SecurityEventSeverity.INFO,
            component="auth",
            details={"method": "jwt", "user_id": "user123"}
        ),
        SecurityEvent(
            event_type="authorization_check",
            severity=SecurityEventSeverity.INFO,
            component="rbac",
            details={"permission": "data.read", "result": "granted"}
        ),
        SecurityEvent(
            event_type="data_access",
            severity=SecurityEventSeverity.INFO,
            component="application",
            details={"resource": "secure-data", "action": "read"}
        )
    ]
    
    for event in events:
        await monitor.log_security_event(event, correlation_id)
        logger.info(f"Logged event: {event.event_type}")
    
    # Record some metrics
    metrics = [
        SecurityMetric("auth.attempts", MetricType.COUNTER, 1),
        SecurityMetric("auth.success_rate", MetricType.GAUGE, 0.95),
        SecurityMetric("response.time", MetricType.HISTOGRAM, 125.5)
    ]
    
    for metric in metrics:
        await monitor.record_metric(metric)
        logger.info(f"Recorded metric: {metric.name} = {metric.value}")
    
    # Complete request monitoring
    await monitor.complete_request_monitoring(
        correlation_id, 
        success=True, 
        metadata={"status_code": 200, "response_size": 1024}
    )
    logger.info(f"Completed monitoring request: {correlation_id}")
    
    # Get request trace
    trace = monitor.get_request_trace(correlation_id)
    logger.info(f"Request trace contains {len(trace['events'])} events")
    logger.info(f"Request duration: {trace['duration']:.3f} seconds")


async def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring with context manager."""
    logger.info("\n=== Performance Monitoring ===")
    
    monitor = create_security_monitor()
    correlation_id = await monitor.start_request_monitoring()
    
    # Simulate different security operations with performance monitoring
    operations = [
        ("auth", "jwt_validation", 0.025),
        ("rbac", "permission_check", 0.015),
        ("abac", "policy_evaluation", 0.080),
        ("threat_detection", "anomaly_analysis", 0.120)
    ]
    
    for component, operation, base_duration in operations:
        # Add some randomness to simulate real performance
        duration = base_duration + random.uniform(-0.01, 0.02)
        
        async with PerformanceMonitor(
            monitor=monitor,
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            metadata={"user_id": "user123"}
        ):
            # Simulate the operation
            await asyncio.sleep(duration)
            logger.info(f"Completed {component}.{operation}")
    
    # Get performance statistics
    metrics_summary = monitor.get_metrics_summary()
    logger.info("Performance Statistics:")
    for timer_name, stats in metrics_summary["metrics"]["timers"].items():
        if stats:  # Only show timers with data
            logger.info(f"  {timer_name}:")
            logger.info(f"    Count: {stats['count']}")
            logger.info(f"    Mean: {stats['mean']:.2f}ms")
            logger.info(f"    P95: {stats['p95']:.2f}ms")
    
    await monitor.complete_request_monitoring(correlation_id, success=True)


async def demonstrate_alerting_system():
    """Demonstrate security alerting capabilities."""
    logger.info("\n=== Security Alerting ===")
    
    monitor = create_security_monitor()
    
    # Set up alert handlers
    alerts_received = []
    
    def alert_handler(alert):
        alerts_received.append(alert)
        logger.info(f"🚨 ALERT: {alert.title}")
        logger.info(f"   Severity: {alert.severity.value}")
        logger.info(f"   Component: {alert.component}")
        logger.info(f"   Description: {alert.description}")
    
    monitor.add_alert_handler(alert_handler)
    
    # Create some alerts
    correlation_id = await monitor.start_request_monitoring()
    
    # High severity event should automatically create alert
    high_severity_event = SecurityEvent(
        event_type="brute_force_detected",
        severity=SecurityEventSeverity.HIGH,
        component="auth",
        details={
            "source_ip": "192.168.1.100",
            "failed_attempts": 10,
            "time_window": "5 minutes"
        }
    )
    
    await monitor.log_security_event(high_severity_event, correlation_id)
    
    # Manual alert creation
    await monitor.create_alert(
        severity=SecurityEventSeverity.CRITICAL,
        title="Suspicious Activity Detected",
        description="Multiple security violations from same source",
        component="threat_detection",
        correlation_id=correlation_id,
        affected_resources=["user:suspicious_user", "ip:192.168.1.100"],
        metadata={"threat_score": 0.95, "confidence": 0.88}
    )
    
    # Performance alert (by exceeding threshold)
    monitor.set_performance_threshold("auth", "jwt_validation", 10.0)  # Very low threshold
    
    await monitor.record_performance(
        component="auth",
        operation="jwt_validation",
        duration_ms=50.0,  # Exceeds threshold
        correlation_id=correlation_id
    )
    
    logger.info(f"Total alerts created: {len(alerts_received)}")
    
    # Resolve an alert
    if alerts_received:
        alert_to_resolve = alerts_received[0]
        success = await monitor.resolve_alert(
            alert_to_resolve.alert_id,
            "security_admin",
            "Investigated and determined to be false positive"
        )
        if success:
            logger.info(f"✅ Resolved alert: {alert_to_resolve.alert_id}")
    
    # Show active vs resolved alerts
    active_alerts = monitor.get_active_alerts()
    logger.info(f"Active alerts: {len(active_alerts)}")
    logger.info(f"Total alerts: {len(monitor.alerts)}")


async def demonstrate_correlation_tracking():
    """Demonstrate request correlation tracking."""
    logger.info("\n=== Correlation Tracking ===")
    
    monitor = create_security_monitor()
    
    # Simulate multiple concurrent requests
    async def process_request(request_id: str, user_id: str, endpoint: str):
        correlation_id = await monitor.start_request_monitoring(
            metadata={"user_id": user_id, "endpoint": endpoint}
        )
        
        # Simulate security processing pipeline
        components = ["auth", "rbac", "abac", "application"]
        
        for i, component in enumerate(components):
            # Add some processing delay
            await asyncio.sleep(random.uniform(0.01, 0.05))
            
            # Log component processing
            await monitor.log_security_event(
                SecurityEvent(
                    event_type=f"{component}_processing",
                    severity=SecurityEventSeverity.INFO,
                    component=component,
                    details={"step": i+1, "total_steps": len(components)}
                ),
                correlation_id
            )
            
            # Record performance
            await monitor.record_performance(
                component=component,
                operation="process",
                duration_ms=random.uniform(10, 50),
                correlation_id=correlation_id
            )
        
        # Complete request
        success = random.choice([True, True, True, False])  # 75% success rate
        await monitor.complete_request_monitoring(
            correlation_id,
            success=success,
            metadata={"status_code": 200 if success else 500}
        )
        
        return correlation_id
    
    # Process multiple requests concurrently
    tasks = []
    for i in range(5):
        task = process_request(
            f"req_{i}",
            f"user_{i}",
            f"/api/endpoint_{i}"
        )
        tasks.append(task)
    
    correlation_ids = await asyncio.gather(*tasks)
    
    logger.info(f"Processed {len(correlation_ids)} concurrent requests")
    
    # Show correlation statistics
    correlation_stats = monitor.correlation_tracker.get_statistics()
    logger.info(f"Correlation tracking statistics:")
    logger.info(f"  Active requests: {correlation_stats['active_requests']}")
    logger.info(f"  Completed requests: {correlation_stats['completed_requests']}")
    logger.info(f"  Total tracked: {correlation_stats['total_tracked']}")
    
    # Show detailed trace for one request
    if correlation_ids:
        sample_id = correlation_ids[0]
        trace = monitor.get_request_trace(sample_id)
        logger.info(f"\nDetailed trace for {sample_id}:")
        logger.info(f"  Duration: {trace['duration']:.3f} seconds")
        logger.info(f"  Success: {trace['success']}")
        logger.info(f"  Components: {list(trace['components'])}")
        logger.info(f"  Events: {len(trace['events'])}")
        
        for event in trace['events'][:3]:  # Show first 3 events
            logger.info(f"    - {event['component']}: {event['event']} at {event['timestamp']}")


async def demonstrate_metrics_aggregation():
    """Demonstrate metrics collection and aggregation."""
    logger.info("\n=== Metrics Aggregation ===")
    
    monitor = create_security_monitor()
    
    # Simulate collecting various metrics over time
    logger.info("Collecting metrics...")
    
    # Authentication metrics
    for i in range(50):
        success = random.choice([True] * 9 + [False])  # 90% success rate
        
        await monitor.record_metric(SecurityMetric(
            "auth.attempts",
            MetricType.COUNTER,
            1,
            labels={"result": "success" if success else "failure"}
        ))
        
        if success:
            # Response time for successful auth
            response_time = random.uniform(20, 80)
            await monitor.record_metric(SecurityMetric(
                "auth.response_time",
                MetricType.HISTOGRAM,
                response_time
            ))
    
    # RBAC metrics
    for i in range(30):
        await monitor.record_metric(SecurityMetric(
            "rbac.checks",
            MetricType.COUNTER,
            1
        ))
        
        check_time = random.uniform(5, 25)
        await monitor.record_metric(SecurityMetric(
            "rbac.check_time",
            MetricType.TIMER,
            check_time
        ))
    
    # System metrics
    await monitor.record_metric(SecurityMetric(
        "system.active_sessions",
        MetricType.GAUGE,
        random.randint(100, 500)
    ))
    
    await monitor.record_metric(SecurityMetric(
        "system.memory_usage",
        MetricType.GAUGE,
        random.uniform(0.6, 0.9)
    ))
    
    # Get comprehensive metrics summary
    summary = monitor.get_metrics_summary()
    
    logger.info("📊 Metrics Summary:")
    logger.info(f"  Total metrics collected: {summary['metrics']['total_metrics']}")
    
    # Counters
    logger.info("  Counters:")
    for name, value in summary['metrics']['counters'].items():
        logger.info(f"    {name}: {value}")
    
    # Gauges
    logger.info("  Gauges:")
    for name, value in summary['metrics']['gauges'].items():
        logger.info(f"    {name}: {value:.2f}")
    
    # Histograms
    logger.info("  Histograms:")
    for name, stats in summary['metrics']['histograms'].items():
        if stats:
            logger.info(f"    {name}:")
            logger.info(f"      Count: {stats['count']}")
            logger.info(f"      Mean: {stats['mean']:.2f}")
            logger.info(f"      P95: {stats['p95']:.2f}")
    
    # Timers
    logger.info("  Timers:")
    for name, stats in summary['metrics']['timers'].items():
        if stats:
            logger.info(f"    {name}:")
            logger.info(f"      Count: {stats['count']}")
            logger.info(f"      Mean: {stats['mean']:.2f}ms")
            logger.info(f"      P99: {stats['p99']:.2f}ms")


async def demonstrate_integration_scenario():
    """Demonstrate complete integration scenario."""
    logger.info("\n=== Complete Integration Scenario ===")
    
    monitor = create_security_monitor(MonitoringLevel.COMPREHENSIVE)
    
    # Set up handlers
    def event_handler(event):
        if event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
            logger.info(f"🔥 High severity event: {event.event_type}")
    
    def alert_handler(alert):
        logger.info(f"🚨 Alert created: {alert.title} ({alert.severity.value})")
    
    monitor.add_event_handler(event_handler)
    monitor.add_alert_handler(alert_handler)
    
    # Simulate a complete security request flow
    correlation_id = await monitor.start_request_monitoring(
        metadata={
            "user_id": "admin_user",
            "endpoint": "/admin/sensitive-data",
            "client_ip": "192.168.1.50",
            "user_agent": "AdminApp/1.0"
        }
    )
    
    logger.info(f"🚀 Processing secure request: {correlation_id}")
    
    # Step 1: Authentication
    async with PerformanceMonitor(monitor, "auth", "jwt_validation", correlation_id):
        await asyncio.sleep(0.03)  # Simulate JWT validation
        await monitor.log_security_event(
            SecurityEvent(
                event_type="jwt_validated",
                severity=SecurityEventSeverity.INFO,
                component="auth",
                details={"user_id": "admin_user", "token_type": "access"}
            ),
            correlation_id
        )
    
    # Step 2: RBAC Check
    async with PerformanceMonitor(monitor, "rbac", "permission_check", correlation_id):
        await asyncio.sleep(0.02)  # Simulate RBAC check
        await monitor.log_security_event(
            SecurityEvent(
                event_type="rbac_check",
                severity=SecurityEventSeverity.INFO,
                component="rbac",
                details={"permission": "admin.sensitive_data.read", "result": "granted"}
            ),
            correlation_id
        )
    
    # Step 3: ABAC Evaluation
    async with PerformanceMonitor(monitor, "abac", "policy_evaluation", correlation_id):
        await asyncio.sleep(0.05)  # Simulate ABAC evaluation
        await monitor.log_security_event(
            SecurityEvent(
                event_type="abac_evaluation",
                severity=SecurityEventSeverity.INFO,
                component="abac",
                details={"policies_evaluated": 3, "decision": "permit"}
            ),
            correlation_id
        )
    
    # Step 4: Threat Detection
    async with PerformanceMonitor(monitor, "threat_detection", "anomaly_analysis", correlation_id):
        await asyncio.sleep(0.08)  # Simulate threat analysis
        
        # Simulate detecting a potential threat
        threat_score = random.uniform(0.3, 0.8)
        if threat_score > 0.7:
            await monitor.log_security_event(
                SecurityEvent(
                    event_type="anomaly_detected",
                    severity=SecurityEventSeverity.MEDIUM,
                    component="threat_detection",
                    details={"threat_score": threat_score, "anomaly_type": "unusual_access_pattern"}
                ),
                correlation_id
            )
        else:
            await monitor.log_security_event(
                SecurityEvent(
                    event_type="threat_analysis_complete",
                    severity=SecurityEventSeverity.INFO,
                    component="threat_detection",
                    details={"threat_score": threat_score, "status": "clean"}
                ),
                correlation_id
            )
    
    # Step 5: Application Processing
    async with PerformanceMonitor(monitor, "application", "data_access", correlation_id):
        await asyncio.sleep(0.04)  # Simulate data access
        await monitor.log_security_event(
            SecurityEvent(
                event_type="sensitive_data_accessed",
                severity=SecurityEventSeverity.MEDIUM,
                component="application",
                details={"resource": "sensitive_data", "records_accessed": 42}
            ),
            correlation_id
        )
    
    # Complete the request
    await monitor.complete_request_monitoring(
        correlation_id,
        success=True,
        metadata={"status_code": 200, "response_size": 2048, "cache_hit": False}
    )
    
    # Show final results
    trace = monitor.get_request_trace(correlation_id)
    summary = monitor.get_metrics_summary()
    
    logger.info("🎯 Request Processing Complete:")
    logger.info(f"  Total duration: {trace['duration']:.3f} seconds")
    logger.info(f"  Components involved: {len(trace['components'])}")
    logger.info(f"  Security events logged: {len(trace['events'])}")
    logger.info(f"  Success: {trace['success']}")
    
    logger.info("📈 Overall System Status:")
    logger.info(f"  Total requests monitored: {summary['correlation_tracking']['total_tracked']}")
    logger.info(f"  Active alerts: {summary['alerts']['active']}")
    logger.info(f"  Components monitored: {summary['components_monitored']}")


async def main():
    """Run all security monitoring examples."""
    logger.info("🔍 Security Monitoring Integration Examples")
    logger.info("=" * 60)
    
    examples = [
        demonstrate_basic_monitoring,
        demonstrate_performance_monitoring,
        demonstrate_alerting_system,
        demonstrate_correlation_tracking,
        demonstrate_metrics_aggregation,
        demonstrate_integration_scenario
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            logger.error(f"❌ Example {example.__name__} failed: {e}")
        
        # Add separator between examples
        logger.info("-" * 40)
    
    logger.info("🎉 All security monitoring examples completed!")
    
    # Summary
    logger.info("\n📋 Summary of Features Demonstrated:")
    logger.info("  ✅ Integrated security logging with correlation IDs")
    logger.info("  ✅ Performance monitoring with automatic thresholds")
    logger.info("  ✅ Real-time security alerting and resolution")
    logger.info("  ✅ Request tracing across security layers")
    logger.info("  ✅ Comprehensive metrics collection and aggregation")
    logger.info("  ✅ Complete end-to-end security monitoring")
    
    logger.info("\n🔧 Key Benefits:")
    logger.info("  • Complete visibility into security operations")
    logger.info("  • Performance bottleneck identification")
    logger.info("  • Real-time threat detection and alerting")
    logger.info("  • Request correlation for debugging")
    logger.info("  • Comprehensive security metrics")
    logger.info("  • Integration with external monitoring systems")


if __name__ == "__main__":
    asyncio.run(main())
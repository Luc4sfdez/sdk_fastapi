"""
Alert System Example for FastAPI Microservices SDK.

This example demonstrates the comprehensive alerting system including
rule-based alerts, multi-channel notifications, escalation policies,
and alert grouping/deduplication.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi_microservices_sdk.observability.alerting import (
    create_alert_config,
    create_alert_rule_config,
    create_notification_config,
    create_escalation_config,
    create_alert_manager,
    create_alert_rule,
    create_email_notifier,
    create_slack_notifier,
    create_webhook_notifier,
    create_escalation_policy,
    AlertSeverity,
    ConditionOperator,
    AggregationFunction,
    NotificationChannel,
    MetricDataPoint,
    NotificationMessage,
    create_email_settings,
    create_slack_settings,
    create_webhook_settings
)


class MockMetricsDataSource:
    """Mock metrics data source for demonstration."""
    
    def __init__(self):
        """Initialize mock data source."""
        self._metrics_data = {}
        self._base_values = {
            'response_time': 0.2,
            'error_rate': 0.01,
            'cpu_usage': 0.5,
            'memory_usage': 0.6
        }
    
    def get_metric_data(self, metric_name: str) -> List[MetricDataPoint]:
        """Get metric data points."""
        # Generate realistic mock data
        data_points = []
        base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        base_value = self._base_values.get(metric_name, 1.0)
        
        for i in range(20):  # 20 data points over 10 minutes
            timestamp = base_time + timedelta(seconds=i * 30)
            
            # Add some randomness and occasional spikes
            if metric_name == 'response_time':
                value = base_value + random.uniform(-0.05, 0.1)
                # Simulate occasional spikes
                if random.random() < 0.1:  # 10% chance of spike
                    value *= 3
            elif metric_name == 'error_rate':
                value = max(0, base_value + random.uniform(-0.005, 0.02))
                # Simulate error bursts
                if random.random() < 0.05:  # 5% chance of error burst
                    value *= 10
            else:
                value = base_value + random.uniform(-0.1, 0.2)
            
            data_point = MetricDataPoint(
                timestamp=timestamp,
                value=value,
                labels={
                    'service': 'demo-service',
                    'instance': f'instance-{random.randint(1, 3)}',
                    'environment': 'production'
                }
            )
            
            data_points.append(data_point)
        
        return data_points
    
    def simulate_incident(self, metric_name: str, duration_minutes: int = 5):
        """Simulate an incident by increasing metric values."""
        if metric_name in self._base_values:
            original_value = self._base_values[metric_name]
            
            if metric_name == 'response_time':
                self._base_values[metric_name] = original_value * 5  # 5x slower
            elif metric_name == 'error_rate':
                self._base_values[metric_name] = min(1.0, original_value * 20)  # 20x more errors
            else:
                self._base_values[metric_name] = min(1.0, original_value * 2)  # 2x higher
            
            print(f"🚨 Simulating incident: {metric_name} increased to {self._base_values[metric_name]}")
            
            # Schedule restoration
            async def restore_metric():
                await asyncio.sleep(duration_minutes * 60)
                self._base_values[metric_name] = original_value
                print(f"✅ Incident resolved: {metric_name} restored to {original_value}")
            
            asyncio.create_task(restore_metric())


async def setup_notification_channels():
    """Setup notification channels."""
    print("\n📢 SETTING UP NOTIFICATION CHANNELS")
    print("=" * 50)
    
    notification_manager = None
    
    try:
        from fastapi_microservices_sdk.observability.alerting.notifications import NotificationManager
        notification_manager = NotificationManager()
        
        # Email notification (mock configuration)
        email_config = create_notification_config(
            channel_type=NotificationChannel.EMAIL,
            name="email_alerts",
            settings=create_email_settings(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="alerts@example.com",
                password="password",
                from_email="alerts@example.com",
                to_emails=["admin@example.com", "oncall@example.com"]
            ),
            rate_limit_per_minute=5
        )
        
        email_notifier = create_email_notifier(email_config)
        notification_manager.add_channel("email", email_notifier)
        print("✅ Email notification channel configured")
        
    except Exception as e:
        print(f"⚠️  Email notification setup failed (dependencies missing): {e}")
    
    try:
        # Slack notification (mock configuration)
        slack_config = create_notification_config(
            channel_type=NotificationChannel.SLACK,
            name="slack_alerts",
            settings=create_slack_settings(
                webhook_url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                channel="#alerts",
                username="AlertBot"
            ),
            rate_limit_per_minute=10
        )
        
        slack_notifier = create_slack_notifier(slack_config)
        notification_manager.add_channel("slack", slack_notifier)
        print("✅ Slack notification channel configured")
        
    except Exception as e:
        print(f"⚠️  Slack notification setup failed (dependencies missing): {e}")
    
    try:
        # Webhook notification
        webhook_config = create_notification_config(
            channel_type=NotificationChannel.WEBHOOK,
            name="webhook_alerts",
            settings=create_webhook_settings(
                url="https://api.example.com/alerts",
                method="POST",
                headers={"Authorization": "Bearer your-token"}
            ),
            rate_limit_per_minute=20
        )
        
        webhook_notifier = create_webhook_notifier(webhook_config)
        notification_manager.add_channel("webhook", webhook_notifier)
        print("✅ Webhook notification channel configured")
        
    except Exception as e:
        print(f"⚠️  Webhook notification setup failed (dependencies missing): {e}")
    
    return notification_manager


async def setup_alert_rules():
    """Setup alert rules."""
    print("\n📋 SETTING UP ALERT RULES")
    print("=" * 50)
    
    rules = []
    
    # High response time alert
    response_time_rule = create_alert_rule_config(
        name="high_response_time",
        metric_name="response_time",
        condition_operator=ConditionOperator.GREATER_THAN,
        threshold_value=1.0,  # 1 second
        severity=AlertSeverity.HIGH,
        description="Response time is too high",
        aggregation_function=AggregationFunction.AVG,
        aggregation_window=timedelta(minutes=5),
        for_duration=timedelta(minutes=2),
        labels={
            'alertname': 'HighResponseTime',
            'service': 'demo-service',
            'team': 'platform'
        },
        annotations={
            'summary': 'High response time detected',
            'description': 'Average response time is above 1 second for 2 minutes'
        }
    )
    
    rules.append(create_alert_rule(response_time_rule))
    print("✅ High response time rule created")
    
    # High error rate alert
    error_rate_rule = create_alert_rule_config(
        name="high_error_rate",
        metric_name="error_rate",
        condition_operator=ConditionOperator.GREATER_THAN,
        threshold_value=0.05,  # 5% error rate
        severity=AlertSeverity.CRITICAL,
        description="Error rate is too high",
        aggregation_function=AggregationFunction.AVG,
        aggregation_window=timedelta(minutes=3),
        for_duration=timedelta(minutes=1),
        labels={
            'alertname': 'HighErrorRate',
            'service': 'demo-service',
            'team': 'platform'
        },
        annotations={
            'summary': 'High error rate detected',
            'description': 'Error rate is above 5% for 1 minute'
        }
    )
    
    rules.append(create_alert_rule(error_rate_rule))
    print("✅ High error rate rule created")
    
    # High CPU usage alert
    cpu_usage_rule = create_alert_rule_config(
        name="high_cpu_usage",
        metric_name="cpu_usage",
        condition_operator=ConditionOperator.GREATER_THAN,
        threshold_value=0.8,  # 80% CPU
        severity=AlertSeverity.MEDIUM,
        description="CPU usage is high",
        aggregation_function=AggregationFunction.AVG,
        aggregation_window=timedelta(minutes=5),
        for_duration=timedelta(minutes=3),
        labels={
            'alertname': 'HighCPUUsage',
            'service': 'demo-service',
            'team': 'infrastructure'
        }
    )
    
    rules.append(create_alert_rule(cpu_usage_rule))
    print("✅ High CPU usage rule created")
    
    return rules


async def setup_escalation_policies():
    """Setup escalation policies."""
    print("\n📈 SETTING UP ESCALATION POLICIES")
    print("=" * 50)
    
    policies = []
    
    # Critical alerts escalation
    critical_escalation = create_escalation_config(
        name="critical_alerts",
        description="Escalation policy for critical alerts",
        levels=[
            {
                'level': 1,
                'delay': 300,  # 5 minutes
                'notification_channels': ['slack'],
                'conditions': {}
            },
            {
                'level': 2,
                'delay': 900,  # 15 minutes
                'notification_channels': ['email', 'slack'],
                'conditions': {}
            },
            {
                'level': 3,
                'delay': 1800,  # 30 minutes
                'notification_channels': ['email', 'webhook'],
                'conditions': {}
            }
        ],
        severity_filter=[AlertSeverity.CRITICAL],
        escalation_delay=timedelta(minutes=5),
        max_escalations=3
    )
    
    policies.append(create_escalation_policy(critical_escalation))
    print("✅ Critical alerts escalation policy created")
    
    # High severity escalation
    high_escalation = create_escalation_config(
        name="high_alerts",
        description="Escalation policy for high severity alerts",
        levels=[
            {
                'level': 1,
                'delay': 600,  # 10 minutes
                'notification_channels': ['slack'],
                'conditions': {}
            },
            {
                'level': 2,
                'delay': 1800,  # 30 minutes
                'notification_channels': ['email'],
                'conditions': {}
            }
        ],
        severity_filter=[AlertSeverity.HIGH],
        escalation_delay=timedelta(minutes=10),
        max_escalations=2
    )
    
    policies.append(create_escalation_policy(high_escalation))
    print("✅ High severity escalation policy created")
    
    return policies


async def demonstrate_alert_system():
    """Demonstrate the complete alert system."""
    print("\n🚀 ALERT SYSTEM DEMONSTRATION")
    print("=" * 50)
    
    # Create alert configuration
    config = create_alert_config(
        service_name="demo-service",
        environment="production",
        enable_grouping=True,
        enable_deduplication=True,
        grouping_window=30,  # 30 seconds
        deduplication_window=60,  # 1 minute
        evaluation_interval=30,  # 30 seconds
        global_rate_limit_per_minute=50
    )
    
    # Create alert manager
    alert_manager = create_alert_manager(config)
    
    # Setup notification channels
    notification_manager = await setup_notification_channels()
    if notification_manager:
        alert_manager.notification_manager = notification_manager
    
    # Setup alert rules
    rules = await setup_alert_rules()
    for rule in rules:
        alert_manager.add_rule(rule)
    
    # Setup escalation policies
    policies = await setup_escalation_policies()
    for policy in policies:
        alert_manager.escalation_manager.add_policy(policy)
    
    # Setup mock data source
    data_source = MockMetricsDataSource()
    
    # Register data sources
    alert_manager.set_metric_data_source("response_time", data_source.get_metric_data)
    alert_manager.set_metric_data_source("error_rate", data_source.get_metric_data)
    alert_manager.set_metric_data_source("cpu_usage", data_source.get_metric_data)
    
    # Add alert callbacks
    def on_new_alert(alert):
        print(f"🚨 NEW ALERT: {alert.title} (Severity: {alert.severity.value})")
    
    def on_resolved_alert(alert):
        print(f"✅ RESOLVED: {alert.title}")
    
    alert_manager.add_alert_callback(on_new_alert)
    alert_manager.add_resolve_callback(on_resolved_alert)
    
    # Start alert manager
    await alert_manager.start()
    
    print("\n🎯 Alert system is running...")
    print("Monitoring metrics and evaluating rules...")
    
    # Let it run for a bit
    await asyncio.sleep(10)
    
    # Simulate incidents
    print("\n💥 SIMULATING INCIDENTS")
    print("-" * 30)
    
    # Simulate high response time
    data_source.simulate_incident("response_time", duration_minutes=2)
    await asyncio.sleep(5)
    
    # Simulate high error rate
    data_source.simulate_incident("error_rate", duration_minutes=1)
    await asyncio.sleep(5)
    
    # Let the system process alerts
    print("\n⏳ Processing alerts...")
    await asyncio.sleep(30)
    
    # Show alert statistics
    stats = alert_manager.get_manager_stats()
    print(f"\n📊 ALERT STATISTICS")
    print("-" * 30)
    print(f"Active alerts: {stats['active_alerts']}")
    print(f"Status counts: {stats['status_counts']}")
    print(f"Severity counts: {stats['severity_counts']}")
    
    if 'grouper_stats' in stats:
        print(f"Active groups: {stats['grouper_stats']['active_groups']}")
    
    if 'deduplicator_stats' in stats:
        print(f"Duplicates prevented: {stats['deduplicator_stats']['total_duplicates_prevented']}")
    
    # List active alerts
    active_alerts = alert_manager.list_active_alerts()
    if active_alerts:
        print(f"\n📋 ACTIVE ALERTS ({len(active_alerts)})")
        print("-" * 30)
        for alert in active_alerts:
            print(f"- {alert.alert_id}: {alert.title} ({alert.severity.value}) - {alert.status.value}")
    
    # Demonstrate alert acknowledgment
    if active_alerts:
        first_alert = active_alerts[0]
        print(f"\n👤 Acknowledging alert: {first_alert.alert_id}")
        await alert_manager.acknowledge_alert(first_alert.alert_id, "demo_user")
    
    # Let it run a bit more
    await asyncio.sleep(20)
    
    # Stop alert manager
    await alert_manager.stop()
    
    print("\n✅ Alert system demonstration completed!")


async def demonstrate_notification_channels():
    """Demonstrate notification channels."""
    print("\n📢 NOTIFICATION CHANNELS DEMONSTRATION")
    print("=" * 50)
    
    # Create test notification message
    test_message = NotificationMessage(
        alert_id="test_alert_001",
        title="Test Alert: High Response Time",
        message="This is a test alert to demonstrate notification channels. Response time has exceeded 1 second for the past 5 minutes.",
        severity=AlertSeverity.HIGH,
        timestamp=datetime.now(timezone.utc),
        labels={
            'service': 'demo-service',
            'instance': 'instance-1',
            'alertname': 'HighResponseTime'
        },
        annotations={
            'summary': 'High response time detected',
            'runbook_url': 'https://runbooks.example.com/high-response-time'
        },
        alert_url="https://monitoring.example.com/alerts/test_alert_001"
    )
    
    # Setup notification manager
    notification_manager = await setup_notification_channels()
    
    if notification_manager:
        print(f"\n📤 Sending test notification to all channels...")
        
        # Send notification
        results = await notification_manager.send_notification(test_message)
        
        print(f"\n📊 NOTIFICATION RESULTS")
        print("-" * 30)
        
        for channel_name, result in results.items():
            status_icon = "✅" if result.success else "❌"
            print(f"{status_icon} {channel_name}: {result.message}")
            
            if not result.success and result.error_details:
                print(f"   Error: {result.error_details}")
    
    else:
        print("⚠️  No notification channels available (dependencies missing)")


async def main():
    """Main demonstration function."""
    print("🚀 FASTAPI MICROSERVICES SDK - ALERT SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    try:
        # Demonstrate notification channels
        await demonstrate_notification_channels()
        
        # Demonstrate complete alert system
        await demonstrate_alert_system()
        
        print("\n🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\nThe Alert System provides:")
        print("  🚨 Rule-based alert engine with complex condition evaluation")
        print("  📢 Multi-channel notifications (Email, Slack, PagerDuty, Webhooks)")
        print("  📈 Alert escalation policies with time-based triggers")
        print("  🔗 Alert grouping and deduplication to prevent alert storms")
        print("  👤 Alert acknowledgment and resolution tracking")
        print("  📊 Comprehensive alert lifecycle management")
        print("  ⚡ Real-time alert processing and notification")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
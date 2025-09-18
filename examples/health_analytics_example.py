"""
Health Analytics Example for FastAPI Microservices SDK.

This example demonstrates the advanced health analytics capabilities including
trend analysis, predictive monitoring, capacity planning, and reporting.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import List

from fastapi_microservices_sdk.observability.health.analytics import (
    create_analytics_config,
    HealthAnalyzer,
    HealthPredictor,
    CapacityPlanner,
    AnomalyPredictor,
    HealthReporter,
    DashboardGenerator,
    SLAMonitor,
    HealthDataPoint,
    PredictionHorizon,
    ReportType,
    TrendType
)
from fastapi_microservices_sdk.observability.health.config import HealthStatus


async def generate_sample_data(count: int = 100) -> List[HealthDataPoint]:
    """Generate sample health data for demonstration."""
    data_points = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)
    
    for i in range(count):
        # Simulate realistic health data with some patterns
        timestamp = base_time + timedelta(minutes=i * 15)  # Every 15 minutes
        
        # Simulate daily patterns (higher response times during peak hours)
        hour = timestamp.hour
        base_response_time = 0.1
        
        if 9 <= hour <= 17:  # Business hours
            base_response_time += 0.2
        if 12 <= hour <= 14:  # Lunch peak
            base_response_time += 0.1
        
        # Add some randomness and occasional spikes
        response_time = base_response_time + random.uniform(0, 0.3)
        
        # Simulate occasional issues
        if random.random() < 0.05:  # 5% chance of issues
            response_time *= 3  # Spike
            status = HealthStatus.DEGRADED if random.random() < 0.7 else HealthStatus.UNHEALTHY
            error_count = random.randint(1, 5)
        else:
            status = HealthStatus.HEALTHY
            error_count = 0
        
        data_point = HealthDataPoint(
            timestamp=timestamp,
            status=status,
            response_time=response_time,
            success_rate=1.0 if status == HealthStatus.HEALTHY else random.uniform(0.7, 0.95),
            error_count=error_count,
            metadata={
                'endpoint': '/api/health',
                'instance_id': f'instance-{random.randint(1, 3)}',
                'region': 'us-east-1'
            }
        )
        
        data_points.append(data_point)
    
    return data_points


async def demonstrate_trend_analysis():
    """Demonstrate trend analysis capabilities."""
    print("\n🔍 TREND ANALYSIS DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data
    data_points = await generate_sample_data(100)
    print(f"Generated {len(data_points)} sample data points")
    
    # Create analyzer
    analyzer = HealthAnalyzer(config)
    
    # Add data points
    for dp in data_points:
        # Convert to mock health check result
        class MockResult:
            def __init__(self, dp):
                self.status = dp.status
                self.response_time = dp.response_time
                self.details = dp.metadata
        
        await analyzer.add_data_point(MockResult(dp))
    
    # Analyze trends
    trends = await analyzer.analyze_trends([TrendType.LINEAR, TrendType.MOVING_AVERAGE])
    
    print("\nTrend Analysis Results:")
    for trend_type, analysis in trends.items():
        print(f"\n{trend_type.value.upper()} TREND:")
        print(f"  Direction: {analysis.direction.value}")
        print(f"  Confidence: {analysis.confidence:.2%}")
        print(f"  Slope: {analysis.slope:.4f}")
        print(f"  Correlation: {analysis.correlation:.3f}")
        if analysis.prediction:
            print(f"  Next Prediction: {analysis.prediction:.3f}s")


async def demonstrate_predictive_monitoring():
    """Demonstrate predictive health monitoring."""
    print("\n🔮 PREDICTIVE MONITORING DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data with trend
    data_points = await generate_sample_data(50)
    
    # Create predictor
    predictor = HealthPredictor(config)
    
    # Generate predictions for different horizons
    horizons = [PredictionHorizon.SHORT_TERM, PredictionHorizon.MEDIUM_TERM, PredictionHorizon.LONG_TERM]
    
    for horizon in horizons:
        print(f"\n{horizon.value.upper()} PREDICTIONS:")
        
        try:
            predictions = await predictor.predict_health_metrics(data_points, horizon)
            
            for model, prediction in predictions.items():
                print(f"\n  {model.value.upper()} Model:")
                print(f"    Predicted Value: {prediction.predicted_value:.3f}s")
                print(f"    Confidence: {prediction.confidence_level:.2%}")
                print(f"    Confidence Interval: [{prediction.confidence_interval[0]:.3f}, {prediction.confidence_interval[1]:.3f}]")
                
        except Exception as e:
            print(f"    Error: {e}")


async def demonstrate_capacity_planning():
    """Demonstrate capacity planning capabilities."""
    print("\n📊 CAPACITY PLANNING DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data
    data_points = await generate_sample_data(80)
    
    # Create capacity planner
    planner = CapacityPlanner(config)
    
    # Define current capacity and thresholds
    current_capacity = {
        'cpu': 0.6,      # 60% CPU utilization
        'memory': 0.7,   # 70% memory utilization
        'instances': 3   # 3 instances
    }
    
    thresholds = {
        'response_time': 1.0,  # 1 second threshold
        'cpu': 0.8,           # 80% CPU threshold
        'memory': 0.85        # 85% memory threshold
    }
    
    try:
        forecast = await planner.forecast_capacity_needs(data_points, current_capacity, thresholds)
        
        print("Capacity Forecast Results:")
        print(f"  Current Utilization: {forecast.current_utilization:.2%}")
        print(f"  Predicted Utilization: {forecast.predicted_utilization:.2%}")
        print(f"  Capacity Threshold: {forecast.capacity_threshold:.2f}s")
        print(f"  Confidence: {forecast.confidence:.2%}")
        
        if forecast.time_to_threshold:
            print(f"  Time to Threshold: {forecast.time_to_threshold}")
        else:
            print("  Time to Threshold: Not applicable")
        
        print("\nScaling Recommendations:")
        recommendations = forecast.recommended_scaling
        print(f"  Action: {recommendations['action']}")
        print(f"  Scale Factor: {recommendations['scale_factor']:.2f}x")
        print(f"  Urgency: {recommendations['urgency']}")
        
        if recommendations['reasoning']:
            print("  Reasoning:")
            for reason in recommendations['reasoning']:
                print(f"    - {reason}")
                
    except Exception as e:
        print(f"Error in capacity planning: {e}")


async def demonstrate_anomaly_prediction():
    """Demonstrate anomaly prediction capabilities."""
    print("\n🚨 ANOMALY PREDICTION DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data with some anomalies
    data_points = await generate_sample_data(60)
    
    # Add some artificial anomalies
    for i in range(5):
        idx = random.randint(40, 55)
        data_points[idx].response_time *= 5  # Create response time spike
        data_points[idx].error_count = random.randint(3, 8)
        data_points[idx].status = HealthStatus.DEGRADED
    
    # Create anomaly predictor
    predictor = AnomalyPredictor(config)
    
    try:
        anomaly_predictions = await predictor.predict_anomalies(data_points)
        
        if anomaly_predictions:
            print("Anomaly Predictions:")
            
            for i, prediction in enumerate(anomaly_predictions, 1):
                print(f"\n  Anomaly {i}:")
                print(f"    Type: {prediction.anomaly_type}")
                print(f"    Probability: {prediction.anomaly_probability:.2%}")
                print(f"    Severity: {prediction.severity:.2f}")
                print(f"    Confidence: {prediction.confidence:.2%}")
                
                if prediction.expected_impact:
                    print("    Expected Impact:")
                    for key, value in prediction.expected_impact.items():
                        print(f"      {key}: {value}")
                
                if prediction.mitigation_suggestions:
                    print("    Mitigation Suggestions:")
                    for suggestion in prediction.mitigation_suggestions:
                        print(f"      - {suggestion}")
        else:
            print("No anomalies predicted for the current data set.")
            
    except Exception as e:
        print(f"Error in anomaly prediction: {e}")


async def demonstrate_health_reporting():
    """Demonstrate health reporting capabilities."""
    print("\n📋 HEALTH REPORTING DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data
    data_points = await generate_sample_data(120)
    
    # Create reporter
    reporter = HealthReporter(config)
    
    # Define report period
    period_start = data_points[0].timestamp
    period_end = data_points[-1].timestamp
    
    try:
        # Generate health summary report
        report = await reporter.generate_health_report(
            ReportType.HEALTH_SUMMARY,
            data_points,
            period_start,
            period_end
        )
        
        print("Health Report Generated:")
        print(f"  Report ID: {report.report_id}")
        print(f"  Report Type: {report.report_type.value}")
        print(f"  Period: {report.data_period_start.strftime('%Y-%m-%d')} to {report.data_period_end.strftime('%Y-%m-%d')}")
        
        # Display summary
        summary = report.summary
        period_summary = summary.get('period_summary', {})
        
        print("\nSummary Metrics:")
        print(f"  Total Checks: {period_summary.get('total_checks', 0)}")
        print(f"  Healthy Checks: {period_summary.get('healthy_checks', 0)}")
        print(f"  Availability: {period_summary.get('availability_percentage', 0):.2f}%")
        print(f"  Avg Response Time: {period_summary.get('avg_response_time', 0):.3f}s")
        print(f"  Max Response Time: {period_summary.get('max_response_time', 0):.3f}s")
        print(f"  Total Errors: {period_summary.get('total_errors', 0)}")
        print(f"  Overall Health: {summary.get('health_status', 'Unknown')}")
        
        # Display key insights
        insights = summary.get('key_insights', [])
        if insights:
            print("\nKey Insights:")
            for insight in insights:
                print(f"  - {insight}")
        
        # Display recommendations
        if report.recommendations:
            print("\nRecommendations:")
            for recommendation in report.recommendations:
                print(f"  - {recommendation}")
                
    except Exception as e:
        print(f"Error generating health report: {e}")


async def demonstrate_dashboard_generation():
    """Demonstrate dashboard generation capabilities."""
    print("\n📊 DASHBOARD GENERATION DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data
    data_points = await generate_sample_data(100)
    
    # Create dashboard generator
    generator = DashboardGenerator(config)
    
    dashboard_types = ["overview", "performance", "reliability"]
    
    for dashboard_type in dashboard_types:
        try:
            dashboard = await generator.generate_dashboard_data(data_points, dashboard_type)
            
            print(f"\n{dashboard_type.upper()} DASHBOARD:")
            print(f"  Dashboard ID: {dashboard.dashboard_id}")
            print(f"  Title: {dashboard.title}")
            print(f"  Refresh Interval: {dashboard.refresh_interval}s")
            print(f"  Widgets Count: {len(dashboard.widgets)}")
            
            # Display widget information
            for i, widget in enumerate(dashboard.widgets, 1):
                print(f"\n    Widget {i}: {widget['title']}")
                print(f"      Type: {widget['type']}")
                print(f"      Size: {widget['size']}")
                
                # Display some widget data
                if widget['type'] == 'status_indicator':
                    data = widget['data']
                    print(f"      Status: {data['status']} ({data['percentage']:.1f}%)")
                elif widget['type'] == 'gauge':
                    data = widget['data']
                    print(f"      Value: {data['value']:.1f}{data['unit']}")
                elif widget['type'] == 'metric':
                    data = widget['data']
                    print(f"      Value: {data['value']:.2f}{data['unit']}")
                    
        except Exception as e:
            print(f"Error generating {dashboard_type} dashboard: {e}")


async def demonstrate_sla_monitoring():
    """Demonstrate SLA monitoring capabilities."""
    print("\n📈 SLA MONITORING DEMONSTRATION")
    print("=" * 50)
    
    # Create configuration
    config = create_analytics_config(
        service_name="demo-service",
        environment="production"
    )
    
    # Generate sample data
    data_points = await generate_sample_data(150)
    
    # Create SLA monitor
    monitor = SLAMonitor(config)
    
    # Define custom SLA thresholds
    custom_thresholds = {
        'availability': 99.5,      # 99.5% uptime
        'response_time_p95': 0.8,  # 800ms 95th percentile
        'response_time_p99': 1.5,  # 1.5s 99th percentile
        'error_rate': 0.05         # 0.05% error rate
    }
    
    try:
        sla_metrics = await monitor.calculate_sla_metrics(data_points, custom_thresholds)
        
        print("SLA Compliance Metrics:")
        print(f"  Availability: {sla_metrics.availability_percentage:.2f}%")
        print(f"  Response Time P95: {sla_metrics.response_time_p95:.3f}s")
        print(f"  Response Time P99: {sla_metrics.response_time_p99:.3f}s")
        print(f"  Error Rate: {sla_metrics.error_rate_percentage:.2f}%")
        print(f"  Uptime Hours: {sla_metrics.uptime_hours:.1f}h")
        print(f"  Downtime Incidents: {sla_metrics.downtime_incidents}")
        print(f"  Overall SLA Score: {sla_metrics.sla_compliance_score:.1f}%")
        
        # Display SLA violations
        if sla_metrics.violations:
            print("\nSLA Violations:")
            for violation in sla_metrics.violations:
                print(f"  - {violation['type'].upper()}: {violation['description']}")
                print(f"    Severity: {violation['severity']}")
                print(f"    Threshold: {violation['threshold']}, Actual: {violation['actual']:.3f}")
        else:
            print("\nNo SLA violations detected! 🎉")
            
    except Exception as e:
        print(f"Error calculating SLA metrics: {e}")


async def main():
    """Main demonstration function."""
    print("🚀 FASTAPI MICROSERVICES SDK - HEALTH ANALYTICS DEMONSTRATION")
    print("=" * 70)
    
    try:
        # Run all demonstrations
        await demonstrate_trend_analysis()
        await demonstrate_predictive_monitoring()
        await demonstrate_capacity_planning()
        await demonstrate_anomaly_prediction()
        await demonstrate_health_reporting()
        await demonstrate_dashboard_generation()
        await demonstrate_sla_monitoring()
        
        print("\n✅ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\nThe Health Analytics system provides:")
        print("  🔍 Advanced trend analysis with multiple algorithms")
        print("  🔮 Predictive health monitoring with ML capabilities")
        print("  📊 Intelligent capacity planning and scaling recommendations")
        print("  🚨 Proactive anomaly detection and prediction")
        print("  📋 Comprehensive health reporting in multiple formats")
        print("  📊 Real-time dashboard generation with customizable widgets")
        print("  📈 SLA monitoring and compliance tracking")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
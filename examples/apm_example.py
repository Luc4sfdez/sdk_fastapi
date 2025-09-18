"""
Application Performance Monitoring (APM) Example for FastAPI Microservices SDK.

This example demonstrates how to use the comprehensive APM system
with profiling, baseline management, SLA monitoring, bottleneck detection,
trend analysis, and regression detection.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi_microservices_sdk.observability.apm import (
    APMManager,
    APMConfig,
    ProfilingConfig,
    BaselineConfig,
    SLAConfig,
    BottleneckConfig,
    TrendConfig,
    RegressionConfig,
    create_apm_manager,
    ProfilingType,
    SLAMetricType
)


async def main():
    """Main APM example function."""
    print("🚀 FastAPI Microservices SDK - APM System Example")
    print("=" * 60)
    
    # 1. Create APM configuration
    config = APMConfig(
        service_name="example-service",
        service_version="1.0.0",
        environment="development",
        enabled=True,
        
        # Profiling configuration
        profiling=ProfilingConfig(
            enabled=True,
            profiling_types=[
                ProfilingType.CPU,
                ProfilingType.MEMORY,
                ProfilingType.IO
            ],
            cpu_threshold=80.0,
            memory_threshold=85.0
        ),
        
        # Baseline configuration
        baseline=BaselineConfig(
            enabled=True,
            baseline_period=timedelta(minutes=30),
            min_data_points=20,
            drift_detection_enabled=True,
            drift_threshold=0.2
        ),
        
        # SLA configuration
        sla=SLAConfig(
            enabled=True,
            default_response_time_ms=1000.0,
            default_error_rate_percent=1.0,
            monitoring_interval=timedelta(seconds=30),
            violation_threshold=3
        ),
        
        # Bottleneck detection configuration
        bottleneck=BottleneckConfig(
            enabled=True,
            cpu_bottleneck_threshold=90.0,
            memory_bottleneck_threshold=95.0,
            generate_recommendations=True
        ),
        
        # Trend analysis configuration
        trend=TrendConfig(
            enabled=True,
            trend_window=timedelta(hours=1),
            capacity_planning_enabled=True,
            planning_horizon=timedelta(days=30)
        ),
        
        # Regression detection configuration
        regression=RegressionConfig(
            enabled=True,
            regression_threshold=0.1,
            min_samples=10
        )
    )
    
    # 2. Create and start APM manager
    print("\\n🔧 Starting APM Manager...")
    apm_manager = create_apm_manager(config)
    
    # Add callbacks for monitoring
    async def performance_callback(event_data):
        print(f"📊 Performance event: {event_data}")
    
    async def alert_callback(alert_message):
        print(f"🚨 APM Alert: {alert_message}")
    
    apm_manager.add_performance_callback(performance_callback)
    apm_manager.add_alert_callback(alert_callback)
    
    await apm_manager.start()
    
    try:
        # 3. Simulate baseline data collection
        print("\\n📈 Collecting baseline performance data...")
        
        # Simulate normal performance metrics for baseline
        for i in range(50):
            timestamp = datetime.now(timezone.utc) - timedelta(minutes=50-i)
            
            # Response time (normal: 200-400ms)
            response_time = random.normalvariate(300, 50)
            await apm_manager.record_performance_metric(
                "api_response_time", 
                max(100, response_time), 
                "response_time",
                timestamp
            )
            
            # Throughput (normal: 80-120 RPS)
            throughput = random.normalvariate(100, 15)
            await apm_manager.record_performance_metric(
                "api_throughput", 
                max(50, throughput), 
                "throughput",
                timestamp
            )
            
            # Error rate (normal: 0.5-2%)
            error_rate = random.normalvariate(1.0, 0.3)
            await apm_manager.record_performance_metric(
                "api_error_rate", 
                max(0, min(5, error_rate)), 
                "error_rate",
                timestamp
            )
            
            # CPU usage (normal: 40-60%)
            cpu_usage = random.normalvariate(50, 8)
            await apm_manager.record_resource_metric(
                "server", 
                "cpu", 
                max(10, min(100, cpu_usage)), 
                timestamp
            )
            
            # Memory usage (normal: 60-80%)
            memory_usage = random.normalvariate(70, 10)
            await apm_manager.record_resource_metric(
                "server", 
                "memory", 
                max(20, min(100, memory_usage)), 
                timestamp
            )
        
        print("✅ Baseline data collected")
        
        # 4. Wait for baselines to be established
        await asyncio.sleep(3)
        
        # 5. Demonstrate performance profiling
        print("\\n🔍 Starting performance profiling...")
        
        # Start CPU profiling
        cpu_profile_id = await apm_manager.start_profiling(
            ProfilingType.CPU, 
            timedelta(seconds=10)
        )
        print(f"Started CPU profiling: {cpu_profile_id}")
        
        # Simulate some CPU-intensive work
        await asyncio.sleep(2)
        
        # Start memory profiling
        memory_profile_id = await apm_manager.start_profiling(
            ProfilingType.MEMORY, 
            timedelta(seconds=5)
        )
        print(f"Started memory profiling: {memory_profile_id}")
        
        # Wait for profiling to complete
        await asyncio.sleep(8)
        
        # Get profiling results
        cpu_result = await apm_manager.profiler.get_profile_result(cpu_profile_id)
        if cpu_result:
            print(f"CPU profiling completed: {cpu_result.status.value}")
        
        # 6. Simulate performance degradation
        print("\\n⚠️  Simulating performance degradation...")
        
        for i in range(20):
            timestamp = datetime.now(timezone.utc)
            
            # Degraded response time (500-800ms)
            response_time = random.normalvariate(650, 100)
            await apm_manager.record_performance_metric(
                "api_response_time", 
                max(200, response_time), 
                "response_time",
                timestamp
            )
            
            # Reduced throughput (40-60 RPS)
            throughput = random.normalvariate(50, 10)
            await apm_manager.record_performance_metric(
                "api_throughput", 
                max(20, throughput), 
                "throughput",
                timestamp
            )
            
            # Higher error rate (3-5%)
            error_rate = random.normalvariate(4.0, 0.5)
            await apm_manager.record_performance_metric(
                "api_error_rate", 
                max(0, min(10, error_rate)), 
                "error_rate",
                timestamp
            )
            
            # High CPU usage (85-95%)
            cpu_usage = random.normalvariate(90, 3)
            await apm_manager.record_resource_metric(
                "server", 
                "cpu", 
                max(80, min(100, cpu_usage)), 
                timestamp
            )
            
            await asyncio.sleep(0.1)  # Small delay between metrics
        
        # 7. Detect bottlenecks
        print("\\n🔍 Detecting performance bottlenecks...")
        bottlenecks = await apm_manager.detect_bottlenecks()
        
        print(f"Detected {len(bottlenecks)} bottlenecks:")
        for bottleneck in bottlenecks:
            print(f"  - {bottleneck.bottleneck_type.value}: {bottleneck.resource_name} "
                  f"({bottleneck.utilization_percent:.1f}% utilization, {bottleneck.severity.value} severity)")
            
            if bottleneck.recommendations:
                print(f"    Recommendations:")
                for rec in bottleneck.recommendations[:2]:  # Show first 2 recommendations
                    print(f"      • {rec.title} (Priority: {rec.priority})")
        
        # 8. Generate SLA report
        print("\\n📋 Generating SLA compliance report...")
        sla_report = await apm_manager.generate_sla_report(timedelta(hours=1))
        
        print(f"SLA Report:")
        print(f"  Overall Compliance: {sla_report.overall_compliance:.1f}%")
        print(f"  Total Violations: {len(sla_report.violations)}")
        print(f"  SLA Metrics: {len(sla_report.sla_metrics)}")
        
        for violation in sla_report.violations[:3]:  # Show first 3 violations
            print(f"    - {violation.sla_name}: {violation.violation_type.value} "
                  f"(Actual: {violation.actual_value:.2f}, Threshold: {violation.threshold_value:.2f})")
        
        # 9. Analyze performance trends
        print("\\n📈 Analyzing performance trends...")
        
        response_time_trend = await apm_manager.analyze_trends("api_response_time")
        if response_time_trend:
            print(f"Response Time Trend:")
            print(f"  Direction: {response_time_trend.trend_direction.value}")
            print(f"  Growth Rate: {response_time_trend.growth_rate:+.2f}% per day")
            print(f"  Confidence: {response_time_trend.confidence_level:.2%}")
            print(f"  Forecast Points: {len(response_time_trend.predicted_values)}")
        
        # 10. Set baseline for regression detection
        print("\\n🎯 Setting performance baseline for regression detection...")
        
        baseline_metrics = {
            "api_response_time": [random.normalvariate(300, 50) for _ in range(30)],
            "api_throughput": [random.normalvariate(100, 15) for _ in range(30)],
            "api_error_rate": [random.normalvariate(1.0, 0.3) for _ in range(30)]
        }
        
        await apm_manager.set_performance_baseline("v1.0.0", baseline_metrics)
        
        # Simulate new version with regression
        print("\\n🔄 Simulating new version deployment...")
        
        # Add performance data for new version (with regression)
        for i in range(20):
            # Regressed response time (20% slower)
            response_time = random.normalvariate(360, 60)  # 20% increase
            await apm_manager.regression_detector.add_performance_data(
                "v1.1.0", "api_response_time", response_time
            )
            
            # Slightly reduced throughput
            throughput = random.normalvariate(95, 15)  # 5% decrease
            await apm_manager.regression_detector.add_performance_data(
                "v1.1.0", "api_throughput", throughput
            )
        
        # Detect regressions
        regressions = await apm_manager.detect_regressions("v1.0.0", "v1.1.0")
        
        print(f"\\n🚨 Regression Detection Results:")
        print(f"Detected {len(regressions)} potential regressions:")
        
        for regression in regressions:
            if regression.regression_detected:
                print(f"  - {regression.metric_name}: {regression.performance_change_percent:+.1f}% change "
                      f"({regression.severity.value} severity)")
                print(f"    Baseline: {regression.baseline_mean:.2f}, Current: {regression.current_mean:.2f}")
        
        # 11. Get comprehensive performance summary
        print("\\n📊 Performance Summary:")
        summary = await apm_manager.get_performance_summary()
        
        print(f"System Status: {summary['system_status']}")
        print(f"Active Issues: {summary['performance_issues']['active_bottlenecks']} bottlenecks, "
              f"{summary['performance_issues']['sla_violations']} SLA violations")
        
        print("\\nComponent Health:")
        for component, health in summary['components'].items():
            status = "✅" if health.get('is_running', False) else "❌"
            print(f"  {status} {component}: {health}")
        
        # 12. Demonstrate capacity planning
        print("\\n🔮 Capacity Planning Insights...")
        
        cpu_insights = await apm_manager.trend_analyzer.generate_capacity_insights("cpu")
        
        for insight in cpu_insights[:2]:  # Show first 2 insights
            print(f"Resource: {insight.resource_type}")
            print(f"  Current Utilization: {insight.current_utilization:.1f}%")
            print(f"  Projected Utilization: {insight.projected_utilization:.1f}%")
            print(f"  Urgency: {insight.urgency_level}")
            print(f"  Recommendation: {insight.recommended_action}")
            if insight.capacity_exhaustion_date:
                print(f"  Capacity Exhaustion: {insight.capacity_exhaustion_date.strftime('%Y-%m-%d')}")
        
        # 13. Wait for background processing
        print("\\n⏰ Waiting for background processing...")
        await asyncio.sleep(5)
        
        print("\\n✅ APM system demonstration completed successfully!")
        
        # Show final statistics
        print("\\n📈 Final Statistics:")
        print(f"  Profiles Created: {len(apm_manager.profiler.profile_history)}")
        print(f"  Baselines Established: {len(apm_manager.baseline_manager.baselines)}")
        print(f"  Bottlenecks Detected: {len(apm_manager.bottleneck_detector.bottleneck_history)}")
        print(f"  Trends Analyzed: {len(apm_manager.trend_analyzer.trend_history)}")
        print(f"  Regressions Found: {len([r for r in regressions if r.regression_detected])}")
        
    except Exception as e:
        print(f"❌ Error in APM example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean shutdown
        print("\\n🛑 Shutting down APM manager...")
        await apm_manager.stop()


async def demonstrate_advanced_apm_features():
    """Demonstrate advanced APM features."""
    print("\\n🎓 Advanced APM Features Demonstration")
    print("=" * 50)
    
    # Create APM configuration for advanced features
    config = APMConfig(
        service_name="advanced-service",
        enabled=True,
        sampling_enabled=True,
        sampling_rate=0.5,  # 50% sampling
        performance_budget_ms=500.0  # 500ms performance budget
    )
    
    apm_manager = create_apm_manager(config)
    await apm_manager.start()
    
    try:
        # 1. Performance budget monitoring
        print("💰 Performance Budget Monitoring...")
        
        # Simulate requests that exceed performance budget
        for i in range(10):
            response_time = random.uniform(400, 800)  # Some exceed 500ms budget
            await apm_manager.record_performance_metric(
                "api_response_time", 
                response_time, 
                "response_time"
            )
            
            if response_time > config.performance_budget_ms:
                print(f"  ⚠️  Budget exceeded: {response_time:.1f}ms > {config.performance_budget_ms}ms")
        
        # 2. Multi-dimensional bottleneck analysis
        print("\\n🔍 Multi-dimensional Bottleneck Analysis...")
        
        # Simulate correlated resource issues
        for i in range(15):
            # Simulate database bottleneck affecting multiple metrics
            db_response_time = random.uniform(800, 1500)  # Slow database
            cpu_usage = random.uniform(85, 95)  # High CPU due to waiting
            memory_usage = random.uniform(80, 90)  # High memory usage
            
            await apm_manager.record_performance_metric("db_response_time", db_response_time, "database")
            await apm_manager.record_resource_metric("server", "cpu", cpu_usage)
            await apm_manager.record_resource_metric("server", "memory", memory_usage)
        
        # Detect bottlenecks with correlations
        bottlenecks = await apm_manager.detect_bottlenecks()
        
        for bottleneck in bottlenecks:
            print(f"  🎯 {bottleneck.bottleneck_type.value} bottleneck detected")
            print(f"     Impact Score: {bottleneck.impact_score:.1f}")
            print(f"     Correlations: {len(bottleneck.correlation_data)} metrics")
            
            # Show top correlations
            sorted_correlations = sorted(
                bottleneck.correlation_data.items(), 
                key=lambda x: abs(x[1]), 
                reverse=True
            )
            for metric, correlation in sorted_correlations[:3]:
                print(f"       {metric}: {correlation:.3f}")
        
        # 3. Predictive capacity planning
        print("\\n🔮 Predictive Capacity Planning...")
        
        # Generate forecasts for different time horizons
        horizons = [
            timedelta(days=7),
            timedelta(days=30),
            timedelta(days=90)
        ]
        
        for horizon in horizons:
            forecast = await apm_manager.trend_analyzer.forecast_metric(
                "server_cpu", horizon
            )
            
            if forecast:
                final_prediction = forecast[-1][1]
                print(f"  📊 {horizon.days}-day forecast: {final_prediction:.1f}% CPU utilization")
        
        # 4. Automated performance optimization recommendations
        print("\\n🤖 Automated Performance Optimization...")
        
        # Get recommendations from bottleneck analysis
        for bottleneck in bottlenecks:
            if bottleneck.recommendations:
                print(f"\\n  Recommendations for {bottleneck.resource_name}:")
                
                for rec in bottleneck.recommendations:
                    print(f"    🎯 {rec.title}")
                    print(f"       Priority: {rec.priority}, Impact: {rec.estimated_impact}")
                    print(f"       Confidence: {rec.confidence_score:.1%}")
                    
                    # Show specific actions
                    for action in rec.specific_actions[:2]:
                        print(f"         • {action}")
        
        print("\\n🎉 Advanced APM features demonstration completed!")
        
    finally:
        await apm_manager.stop()


if __name__ == "__main__":
    # Run the main APM example
    asyncio.run(main())
    
    # Run advanced features demonstration
    asyncio.run(demonstrate_advanced_apm_features())
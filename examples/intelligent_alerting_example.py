"""
Intelligent Alerting System Example for FastAPI Microservices SDK.

This example demonstrates how to use the intelligent alerting system
with ML-based features like adaptive thresholds, anomaly detection,
and predictive alerting.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi_microservices_sdk.observability.alerting.intelligent import (
    IntelligentAlertManager,
    IntelligentAlertingConfig,
    AdaptiveThresholdConfig,
    AnomalyDetectionConfig,
    AlertOptimizationConfig,
    create_intelligent_alert_manager,
    PredictionHorizon,
    AnomalyDetectionModel,
    ThresholdStrategy
)
from fastapi_microservices_sdk.observability.alerting import (
    NotificationMessage,
    AlertSeverity
)


async def main():
    """Main example function."""
    print("🤖 FastAPI Microservices SDK - Intelligent Alerting Example")
    print("=" * 60)
    
    # 1. Create intelligent alerting configuration
    config = IntelligentAlertingConfig(
        service_name="example-service",
        service_version="1.0.0",
        environment="development",
        enabled=True,
        learning_mode=True,
        
        # Adaptive thresholds configuration
        adaptive_thresholds=AdaptiveThresholdConfig(
            enabled=True,
            strategy=ThresholdStrategy.STATISTICAL,
            adaptation_window=timedelta(hours=1),
            min_data_points=20,
            confidence_level=0.95
        ),
        
        # Anomaly detection configuration
        anomaly_detection=AnomalyDetectionConfig(
            enabled=True,
            models=[
                AnomalyDetectionModel.ISOLATION_FOREST,
                AnomalyDetectionModel.STATISTICAL_OUTLIER
            ],
            anomaly_threshold=0.1,
            training_window=timedelta(hours=6),
            retrain_interval=timedelta(hours=12)
        ),
        
        # Alert optimization configuration
        alert_optimization=AlertOptimizationConfig(
            enabled=True,
            optimization_window=timedelta(hours=2),
            min_alert_history=10
        )
    )
    
    # 2. Create and start intelligent alert manager
    print("\\n🚀 Starting Intelligent Alert Manager...")
    manager = create_intelligent_alert_manager(config)
    
    # Add callbacks for monitoring
    async def alert_callback(alert: NotificationMessage, result: Dict[str, Any]):
        print(f"📢 Alert processed: {alert.title}")
        print(f"   Actions taken: {result['actions_taken']}")
        if result['recommendations']:
            print(f"   Recommendations: {result['recommendations']}")
    
    async def prediction_callback(prediction):
        print(f"🔮 Prediction: {prediction.metric_name}")
        print(f"   Predicted value: {prediction.predicted_value:.2f}")
        print(f"   Confidence: {prediction.confidence.value}")
        print(f"   Breach probability: {prediction.threshold_breach_probability:.2%}")
    
    async def anomaly_callback(alert: NotificationMessage, anomaly_result):
        print(f"🚨 Anomaly detected in {alert.title}")
        print(f"   Anomaly score: {anomaly_result.anomaly_score:.3f}")
        print(f"   Model used: {anomaly_result.model_name}")
    
    manager.add_alert_callback(alert_callback)
    manager.add_prediction_callback(prediction_callback)
    manager.add_anomaly_callback(anomaly_callback)
    
    await manager.start()
    
    try:
        # 3. Simulate metric data ingestion
        print("\\n📊 Simulating metric data ingestion...")
        
        metrics = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate']
        
        # Generate normal data for training
        for i in range(100):
            timestamp = datetime.now(timezone.utc) - timedelta(minutes=100-i)
            
            for metric in metrics:
                # Generate realistic metric values
                if metric == 'cpu_usage':
                    value = random.normalvariate(50, 10)  # Normal around 50%
                elif metric == 'memory_usage':
                    value = random.normalvariate(60, 15)  # Normal around 60%
                elif metric == 'response_time':
                    value = random.normalvariate(200, 50)  # Normal around 200ms
                elif metric == 'error_rate':
                    value = random.normalvariate(1, 0.5)  # Normal around 1%
                
                value = max(0, value)  # Ensure non-negative
                await manager.add_metric_data(metric, value, timestamp)
        
        print("✅ Training data ingested")
        
        # 4. Wait for models to train
        await asyncio.sleep(2)
        
        # 5. Generate predictions
        print("\\n🔮 Generating predictions...")
        predictions = await manager.get_predictions(metrics)
        
        print(f"Generated {len(predictions)} predictions")
        
        # 6. Simulate real-time alerts
        print("\\n📢 Simulating real-time alerts...")
        
        # Normal alert
        normal_alert = NotificationMessage(
            id="alert-001",
            title="CPU Usage Alert",
            message="CPU usage is at 75%",
            severity=AlertSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            labels={
                'service': 'example-service',
                'metric_name': 'cpu_usage',
                'value': '75.0'
            }
        )
        
        result = await manager.process_alert(normal_alert)
        print(f"Normal alert processed: {len(result['actions_taken'])} actions taken")
        
        # Anomalous alert
        anomaly_alert = NotificationMessage(
            id="alert-002",
            title="Memory Usage Spike",
            message="Memory usage spiked to 95%",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.now(timezone.utc),
            labels={
                'service': 'example-service',
                'metric_name': 'memory_usage',
                'value': '95.0'
            }
        )
        
        result = await manager.process_alert(anomaly_alert)
        print(f"Anomaly alert processed: {len(result['actions_taken'])} actions taken")
        
        # 7. Simulate correlated alerts
        print("\\n🔗 Simulating correlated alerts...")
        
        # Database connection error (root cause)
        db_alert = NotificationMessage(
            id="alert-003",
            title="Database Connection Error",
            message="Failed to connect to database",
            severity=AlertSeverity.CRITICAL,
            timestamp=datetime.now(timezone.utc),
            labels={
                'service': 'database-service',
                'alert_type': 'database_connection_error'
            }
        )
        
        await manager.process_alert(db_alert)
        
        # Wait a bit for temporal correlation
        await asyncio.sleep(1)
        
        # Application error (consequence)
        app_alert = NotificationMessage(
            id="alert-004",
            title="Application Error",
            message="Application experiencing errors",
            severity=AlertSeverity.HIGH,
            timestamp=datetime.now(timezone.utc),
            labels={
                'service': 'example-service',
                'alert_type': 'application_error'
            }
        )
        
        result = await manager.process_alert(app_alert)
        if result['correlations']:
            print(f"Found {len(result['correlations'])} correlations")
            if 'root_cause_analysis' in result:
                print("Root cause analysis performed")
        
        # 8. Check system health
        print("\\n🏥 Checking system health...")
        health = await manager.get_system_health()
        
        print(f"System status: {health['system_status']}")
        print(f"Statistics: {health['statistics']}")
        print(f"Active models: {len(health['components']['predictive_models'])}")
        
        # 9. Demonstrate fatigue reduction
        print("\\n😴 Demonstrating alert fatigue reduction...")
        
        # Send multiple similar alerts
        for i in range(5):
            duplicate_alert = NotificationMessage(
                id=f"alert-dup-{i}",
                title="Repeated CPU Alert",
                message="CPU usage is high",
                severity=AlertSeverity.MEDIUM,
                timestamp=datetime.now(timezone.utc),
                labels={
                    'service': 'example-service',
                    'metric_name': 'cpu_usage',
                    'value': '80.0'
                }
            )
            
            result = await manager.process_alert(duplicate_alert)
            if result['fatigue_filtered']:
                print(f"Alert {i+1} filtered due to fatigue")
            else:
                print(f"Alert {i+1} processed normally")
        
        # 10. Model retraining
        print("\\n🔄 Demonstrating model retraining...")
        await manager.retrain_models(['cpu_usage'])
        print("Models retrained for cpu_usage")
        
        # 11. Advanced predictions with different horizons
        print("\\n🎯 Advanced predictions with different horizons...")
        
        from fastapi_microservices_sdk.observability.alerting.intelligent.predictive import PredictionHorizon
        
        for horizon in [PredictionHorizon.SHORT_TERM, PredictionHorizon.MEDIUM_TERM, PredictionHorizon.LONG_TERM]:
            prediction = await manager.predictive_alerting.predict_alerts('cpu_usage', horizon)
            if prediction:
                print(f"{horizon.value}: {prediction.predicted_value:.2f} (confidence: {prediction.confidence.value})")
        
        # 12. Wait for background tasks to run
        print("\\n⏰ Waiting for background tasks...")
        await asyncio.sleep(5)
        
        print("\\n✅ Intelligent alerting example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean shutdown
        print("\\n🛑 Shutting down intelligent alert manager...")
        await manager.stop()


async def demonstrate_advanced_features():
    """Demonstrate advanced intelligent alerting features."""
    print("\\n🎓 Advanced Features Demonstration")
    print("=" * 40)
    
    # Create configuration for advanced features
    config = IntelligentAlertingConfig(
        service_name="advanced-service",
        enabled=True,
        learning_mode=True,
        auto_model_selection=True,
        batch_processing=True,
        batch_size=50
    )
    
    manager = create_intelligent_alert_manager(config)
    await manager.start()
    
    try:
        # 1. Batch metric ingestion
        print("📦 Batch metric ingestion...")
        
        batch_data = []
        for i in range(100):
            timestamp = datetime.now(timezone.utc) - timedelta(minutes=100-i)
            # Simulate seasonal pattern
            seasonal_factor = 1 + 0.3 * (i % 24) / 24  # Daily pattern
            value = 50 * seasonal_factor + random.normalvariate(0, 5)
            
            await manager.add_metric_data('seasonal_metric', value, timestamp)
        
        # 2. Test adaptive thresholds with seasonal data
        print("🌊 Testing adaptive thresholds with seasonal data...")
        
        # The adaptive threshold should learn the seasonal pattern
        current_value = 65  # Higher than base but normal for peak time
        await manager.add_metric_data('seasonal_metric', current_value)
        
        # 3. Multi-model anomaly detection
        print("🔍 Multi-model anomaly detection...")
        
        # Test with different types of anomalies
        anomaly_types = [
            ('point_anomaly', 150),      # Single point anomaly
            ('trend_anomaly', 80),       # Trend change
            ('seasonal_anomaly', 30)     # Seasonal deviation
        ]
        
        for anomaly_type, value in anomaly_types:
            await manager.add_metric_data(anomaly_type, value)
            
            # Check if anomaly was detected
            anomaly_result = await manager.anomaly_detector.detect_anomaly(
                anomaly_type, value, datetime.now(timezone.utc)
            )
            
            if anomaly_result and anomaly_result.is_anomaly:
                print(f"  ✅ {anomaly_type}: Anomaly detected (score: {anomaly_result.anomaly_score:.3f})")
            else:
                print(f"  ❌ {anomaly_type}: No anomaly detected")
        
        # 4. Complex correlation scenarios
        print("🕸️ Complex correlation scenarios...")
        
        # Simulate a cascade failure
        cascade_alerts = [
            ("load_balancer_failure", AlertSeverity.CRITICAL, 0),
            ("service_a_timeout", AlertSeverity.HIGH, 30),
            ("service_b_timeout", AlertSeverity.HIGH, 45),
            ("database_connection_pool_exhausted", AlertSeverity.CRITICAL, 60),
            ("user_complaints", AlertSeverity.MEDIUM, 120)
        ]
        
        base_time = datetime.now(timezone.utc)
        
        for alert_name, severity, delay_seconds in cascade_alerts:
            alert = NotificationMessage(
                id=f"cascade-{alert_name}",
                title=f"{alert_name.replace('_', ' ').title()}",
                message=f"Issue with {alert_name}",
                severity=severity,
                timestamp=base_time + timedelta(seconds=delay_seconds),
                labels={
                    'service': 'cascade-test',
                    'alert_type': alert_name
                }
            )
            
            result = await manager.process_alert(alert)
            
            if result['correlations']:
                print(f"  🔗 {alert_name}: Found {len(result['correlations'])} correlations")
            
            if 'root_cause_analysis' in result:
                rca = result['root_cause_analysis']
                print(f"  🎯 Root cause: {rca['root_cause_alert_id']}")
        
        # 5. Predictive alerting with confidence intervals
        print("📈 Predictive alerting with confidence intervals...")
        
        predictions = await manager.get_predictions(['seasonal_metric'])
        
        for pred_dict in predictions:
            print(f"  📊 {pred_dict['metric_name']}:")
            print(f"     Predicted: {pred_dict['predicted_value']:.2f}")
            print(f"     Confidence: {pred_dict['confidence']} ({pred_dict['confidence_score']:.2%})")
            print(f"     Breach probability: {pred_dict['threshold_breach_probability']:.2%}")
        
        print("\\n🎉 Advanced features demonstration completed!")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Run advanced features demonstration
    asyncio.run(demonstrate_advanced_features())
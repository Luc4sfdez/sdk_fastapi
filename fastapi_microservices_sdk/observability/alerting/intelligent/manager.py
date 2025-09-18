"""
Intelligent Alert Manager for FastAPI Microservices SDK.

This module provides the main manager for intelligent alerting capabilities,
coordinating all ML-based alerting features.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
import logging

from .config import IntelligentAlertingConfig
from .exceptions import IntelligentAlertingError
from .adaptive_thresholds import AdaptiveThresholdManager, create_adaptive_threshold_manager
from .anomaly_detection import AnomalyDetector, create_anomaly_detector
from .correlation import AlertCorrelator, RootCauseAnalyzer, create_alert_correlator, create_root_cause_analyzer
from .predictive import PredictiveAlerting, create_predictive_alerting, MetricDataPoint
from .fatigue_reduction import AlertFatigueReducer, create_fatigue_reducer
from ..notifications import NotificationMessage
from ..config import AlertSeverity


class IntelligentAlertManager:
    """Main manager for intelligent alerting system."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize intelligent alert manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.adaptive_thresholds = create_adaptive_threshold_manager(config)
        self.anomaly_detector = create_anomaly_detector(config)
        self.alert_correlator = create_alert_correlator(config)
        self.root_cause_analyzer = create_root_cause_analyzer(config)
        self.predictive_alerting = create_predictive_alerting(config)
        self.fatigue_reducer = create_fatigue_reducer(config)
        
        # State management
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Metrics and statistics
        self.stats = {
            'alerts_processed': 0,
            'alerts_filtered': 0,
            'anomalies_detected': 0,
            'predictions_made': 0,
            'correlations_found': 0,
            'thresholds_adapted': 0
        }
        
        # Callbacks
        self.alert_callbacks: List[Callable] = []
        self.prediction_callbacks: List[Callable] = []
        self.anomaly_callbacks: List[Callable] = []
    
    async def start(self):
        """Start the intelligent alerting system."""
        try:
            if self.is_running:
                self.logger.warning("Intelligent alerting system is already running")
                return
            
            self.logger.info("Starting intelligent alerting system...")
            
            # Start components
            await self.adaptive_thresholds.start()
            await self.anomaly_detector.start()
            await self.fatigue_reducer.start()
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._prediction_loop()),
                asyncio.create_task(self._threshold_adaptation_loop()),
                asyncio.create_task(self._anomaly_detection_loop()),
                asyncio.create_task(self._stats_reporting_loop())
            ]
            
            self.is_running = True
            self.logger.info("Intelligent alerting system started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting intelligent alerting system: {e}")
            raise IntelligentAlertingError(
                f"Failed to start intelligent alerting system: {e}",
                intelligent_operation="system_start",
                original_error=e
            )
    
    async def stop(self):
        """Stop the intelligent alerting system."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping intelligent alerting system...")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Stop components
            await self.adaptive_thresholds.stop()
            await self.anomaly_detector.stop()
            await self.fatigue_reducer.stop()
            
            self.is_running = False
            self.background_tasks.clear()
            
            self.logger.info("Intelligent alerting system stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping intelligent alerting system: {e}")
    
    async def process_alert(self, alert: NotificationMessage) -> Dict[str, Any]:
        """Process an alert through the intelligent system."""
        try:
            self.stats['alerts_processed'] += 1
            
            processing_result = {
                'alert_id': alert.id,
                'original_alert': alert.to_dict(),
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'actions_taken': [],
                'recommendations': [],
                'correlations': [],
                'anomaly_detected': False,
                'fatigue_filtered': False,
                'threshold_adapted': False
            }
            
            # 1. Check for alert fatigue and filtering
            should_filter = await self.fatigue_reducer.should_filter_alert(alert)
            if should_filter:
                self.stats['alerts_filtered'] += 1
                processing_result['fatigue_filtered'] = True
                processing_result['actions_taken'].append('filtered_due_to_fatigue')
                return processing_result
            
            # 2. Perform anomaly detection
            anomaly_result = await self.anomaly_detector.detect_anomaly(
                alert.labels.get('metric_name', 'unknown'),
                float(alert.labels.get('value', '0')),
                alert.timestamp
            )
            
            if anomaly_result and anomaly_result.is_anomaly:
                self.stats['anomalies_detected'] += 1
                processing_result['anomaly_detected'] = True
                processing_result['actions_taken'].append('anomaly_detected')
                processing_result['recommendations'].append(
                    f"Anomaly detected with score {anomaly_result.anomaly_score:.3f}"
                )
                
                # Trigger anomaly callbacks
                for callback in self.anomaly_callbacks:
                    try:
                        await callback(alert, anomaly_result)
                    except Exception as e:
                        self.logger.error(f"Error in anomaly callback: {e}")
            
            # 3. Perform alert correlation
            correlations = await self.alert_correlator.correlate_alerts(alert)
            if correlations:
                self.stats['correlations_found'] += len(correlations)
                processing_result['correlations'] = [c.to_dict() for c in correlations]
                processing_result['actions_taken'].append('correlations_found')
                
                # Perform root cause analysis
                root_cause = await self.root_cause_analyzer.analyze_root_cause(correlations)
                if root_cause:
                    processing_result['root_cause_analysis'] = root_cause.to_dict()
                    processing_result['recommendations'].extend(root_cause.recommended_actions)
            
            # 4. Adaptive threshold adjustment
            metric_name = alert.labels.get('metric_name')
            if metric_name:
                threshold_adjusted = await self.adaptive_thresholds.adapt_threshold(
                    metric_name,
                    float(alert.labels.get('value', '0')),
                    alert.timestamp
                )
                
                if threshold_adjusted:
                    self.stats['thresholds_adapted'] += 1
                    processing_result['threshold_adapted'] = True
                    processing_result['actions_taken'].append('threshold_adapted')
            
            # 5. Update fatigue reducer with alert
            await self.fatigue_reducer.record_alert(alert)
            
            # 6. Trigger alert callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert, processing_result)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
            
            return processing_result
            
        except Exception as e:
            self.logger.error(f"Error processing alert {alert.id}: {e}")
            raise IntelligentAlertingError(
                f"Failed to process alert: {e}",
                intelligent_operation="alert_processing",
                original_error=e
            )
    
    async def add_metric_data(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add metric data for predictive analysis."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            data_point = MetricDataPoint(
                timestamp=timestamp,
                value=value,
                metric_name=metric_name
            )
            
            # Add to predictive alerting
            await self.predictive_alerting.add_metric_data(data_point)
            
            # Add to anomaly detector
            await self.anomaly_detector.add_data_point(metric_name, value, timestamp)
            
            # Add to adaptive thresholds
            await self.adaptive_thresholds.add_data_point(metric_name, value, timestamp)
            
        except Exception as e:
            self.logger.error(f"Error adding metric data: {e}")
            raise IntelligentAlertingError(
                f"Failed to add metric data: {e}",
                intelligent_operation="metric_data_ingestion",
                original_error=e
            )
    
    async def get_predictions(self, metric_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get predictions for metrics."""
        try:
            if metric_names is None:
                # Get predictions for all known metrics
                metric_names = list(self.predictive_alerting.metric_history.keys())
            
            predictions = await self.predictive_alerting.predict_multiple_metrics(metric_names)
            self.stats['predictions_made'] += len(predictions)
            
            # Trigger prediction callbacks
            for prediction in predictions:
                for callback in self.prediction_callbacks:
                    try:
                        await callback(prediction)
                    except Exception as e:
                        self.logger.error(f"Error in prediction callback: {e}")
            
            return [p.to_dict() for p in predictions]
            
        except Exception as e:
            self.logger.error(f"Error getting predictions: {e}")
            raise IntelligentAlertingError(
                f"Failed to get predictions: {e}",
                intelligent_operation="prediction_generation",
                original_error=e
            )
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get intelligent alerting system health."""
        try:
            # Get component health
            adaptive_health = await self.adaptive_thresholds.get_health()
            anomaly_health = await self.anomaly_detector.get_health()
            fatigue_health = await self.fatigue_reducer.get_health()
            
            # Get model information
            model_info = await self.predictive_alerting.get_all_models_info()
            
            return {
                'system_status': 'healthy' if self.is_running else 'stopped',
                'uptime': self._get_uptime(),
                'statistics': self.stats.copy(),
                'components': {
                    'adaptive_thresholds': adaptive_health,
                    'anomaly_detector': anomaly_health,
                    'fatigue_reducer': fatigue_health,
                    'predictive_models': {
                        name: model.to_dict() for name, model in model_info.items()
                    }
                },
                'background_tasks': {
                    'running': len([t for t in self.background_tasks if not t.done()]),
                    'total': len(self.background_tasks)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system health: {e}")
            return {
                'system_status': 'error',
                'error': str(e)
            }
    
    async def retrain_models(self, metric_names: Optional[List[str]] = None):
        """Retrain ML models."""
        try:
            self.logger.info("Starting model retraining...")
            
            if metric_names is None:
                # Retrain all models
                await self.predictive_alerting.retrain_all_models()
                await self.anomaly_detector.retrain_all_models()
                await self.adaptive_thresholds.retrain_all_models()
            else:
                # Retrain specific models
                for metric_name in metric_names:
                    await self.predictive_alerting._train_model(metric_name)
                    await self.anomaly_detector.retrain_model(metric_name)
                    await self.adaptive_thresholds.retrain_model(metric_name)
            
            self.logger.info("Model retraining completed")
            
        except Exception as e:
            self.logger.error(f"Error retraining models: {e}")
            raise IntelligentAlertingError(
                f"Failed to retrain models: {e}",
                intelligent_operation="model_retraining",
                original_error=e
            )
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for alert processing."""
        self.alert_callbacks.append(callback)
    
    def add_prediction_callback(self, callback: Callable):
        """Add callback for predictions."""
        self.prediction_callbacks.append(callback)
    
    def add_anomaly_callback(self, callback: Callable):
        """Add callback for anomaly detection."""
        self.anomaly_callbacks.append(callback)
    
    async def _prediction_loop(self):
        """Background loop for generating predictions."""
        while self.is_running:
            try:
                # Generate predictions every 5 minutes
                await asyncio.sleep(300)
                
                if not self.is_running:
                    break
                
                # Get predictions for all metrics
                await self.get_predictions()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in prediction loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _threshold_adaptation_loop(self):
        """Background loop for threshold adaptation."""
        while self.is_running:
            try:
                # Adapt thresholds every 10 minutes
                await asyncio.sleep(600)
                
                if not self.is_running:
                    break
                
                # Trigger threshold adaptation
                await self.adaptive_thresholds.periodic_adaptation()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in threshold adaptation loop: {e}")
                await asyncio.sleep(60)
    
    async def _anomaly_detection_loop(self):
        """Background loop for anomaly detection maintenance."""
        while self.is_running:
            try:
                # Maintenance every 30 minutes
                await asyncio.sleep(1800)
                
                if not self.is_running:
                    break
                
                # Perform anomaly detector maintenance
                await self.anomaly_detector.perform_maintenance()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in anomaly detection loop: {e}")
                await asyncio.sleep(60)
    
    async def _stats_reporting_loop(self):
        """Background loop for statistics reporting."""
        while self.is_running:
            try:
                # Report stats every hour
                await asyncio.sleep(3600)
                
                if not self.is_running:
                    break
                
                # Log statistics
                self.logger.info(f"Intelligent alerting stats: {self.stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in stats reporting loop: {e}")
                await asyncio.sleep(60)
    
    def _get_uptime(self) -> str:
        """Get system uptime."""
        # This would track actual uptime
        return "N/A"


def create_intelligent_alert_manager(config: IntelligentAlertingConfig) -> IntelligentAlertManager:
    """Create intelligent alert manager instance."""
    return IntelligentAlertManager(config)
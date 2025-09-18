"""
Anomaly Detection System for FastAPI Microservices SDK.

This module provides advanced anomaly detection capabilities using multiple
machine learning algorithms for metrics and logs analysis.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import json

# Optional ML dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.mixture import GaussianMixture
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .config import IntelligentAlertingConfig, MLAlgorithm, AnomalyDetectionConfig
from .exceptions import AnomalyDetectionError, MLModelError
from ..rules import MetricDataPoint


class AnomalyType(str, Enum):
    """Anomaly type classification."""
    POINT_ANOMALY = "point_anomaly"
    CONTEXTUAL_ANOMALY = "contextual_anomaly"
    COLLECTIVE_ANOMALY = "collective_anomaly"
    TREND_ANOMALY = "trend_anomaly"
    SEASONAL_ANOMALY = "seasonal_anomaly"


class AnomalySeverity(str, Enum):
    """Anomaly severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    timestamp: datetime
    metric_name: str
    value: Union[float, int, str]
    anomaly_score: float
    is_anomaly: bool
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    confidence: float
    algorithm_used: MLAlgorithm
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'metric_name': self.metric_name,
            'value': self.value,
            'anomaly_score': self.anomaly_score,
            'is_anomaly': self.is_anomaly,
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'algorithm_used': self.algorithm_used.value,
            'context': self.context
        }


@dataclass
class AnomalyModel:
    """Anomaly detection model for a specific metric."""
    metric_name: str
    algorithm: MLAlgorithm
    model: Optional[Any] = None
    scaler: Optional[Any] = None
    training_data_size: int = 0
    last_training: Optional[datetime] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    anomaly_history: List[AnomalyResult] = field(default_factory=list)
    
    def add_anomaly(self, anomaly: AnomalyResult):
        """Add anomaly to history."""
        self.anomaly_history.append(anomaly)
        
        # Keep only recent anomalies
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
        self.anomaly_history = [
            anom for anom in self.anomaly_history
            if anom.timestamp >= cutoff_time
        ]
    
    def get_recent_anomaly_rate(self) -> float:
        """Get recent anomaly rate."""
        if not self.anomaly_history:
            return 0.0
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_anomalies = [
            anom for anom in self.anomaly_history
            if anom.timestamp >= recent_cutoff and anom.is_anomaly
        ]
        
        return len(recent_anomalies) / max(len(self.anomaly_history), 1)


class AnomalyDetector:
    """Advanced anomaly detection system."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize anomaly detector."""
        self.config = config
        self.anomaly_config = config.anomaly_detection_config
        self.logger = logging.getLogger(__name__)
        
        # Models storage
        self._models: Dict[str, Dict[MLAlgorithm, AnomalyModel]] = {}
        
        # Data storage
        self._metric_data: Dict[str, List[MetricDataPoint]] = {}
        
        # Detection state
        self._running = False
        self._detection_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self._detection_stats = {
            'total_detections': 0,
            'anomalies_found': 0,
            'false_positives': 0,
            'model_retrainings': 0
        }
    
    async def start(self):
        """Start anomaly detector."""
        if self._running:
            return
        
        self._running = True
        
        if self.anomaly_config.enabled:
            self._detection_task = asyncio.create_task(self._detection_loop())
        
        self.logger.info("Anomaly detector started")
    
    async def stop(self):
        """Stop anomaly detector."""
        if not self._running:
            return
        
        self._running = False
        
        if self._detection_task:
            self._detection_task.cancel()
            try:
                await self._detection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Anomaly detector stopped")
    
    def register_metric(self, metric_name: str, algorithms: Optional[List[MLAlgorithm]] = None):
        """Register a metric for anomaly detection."""
        if algorithms is None:
            algorithms = self.anomaly_config.algorithms
        
        if metric_name not in self._models:
            self._models[metric_name] = {}
        
        for algorithm in algorithms:
            if algorithm not in self._models[metric_name]:
                self._models[metric_name][algorithm] = AnomalyModel(
                    metric_name=metric_name,
                    algorithm=algorithm
                )
                
                self.logger.info(f"Registered {algorithm.value} model for metric {metric_name}")
    
    def add_metric_data(self, metric_name: str, data_points: List[MetricDataPoint]):
        """Add metric data for anomaly detection."""
        if metric_name not in self._metric_data:
            self._metric_data[metric_name] = []
        
        self._metric_data[metric_name].extend(data_points)
        
        # Keep only recent data
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            days=self.config.data_retention_days
        )
        
        self._metric_data[metric_name] = [
            dp for dp in self._metric_data[metric_name]
            if dp.timestamp >= cutoff_time
        ]
    
    async def detect_anomalies(
        self,
        metric_name: str,
        data_points: Optional[List[MetricDataPoint]] = None
    ) -> List[AnomalyResult]:
        """Detect anomalies in metric data."""
        try:
            if data_points:
                self.add_metric_data(metric_name, data_points)
            
            if metric_name not in self._models:
                self.register_metric(metric_name)
            
            if metric_name not in self._metric_data:
                return []
            
            metric_data = self._metric_data[metric_name]
            
            if len(metric_data) < self.anomaly_config.min_samples_for_training:
                return []
            
            # Ensure models are trained
            await self._ensure_models_trained(metric_name)
            
            # Detect anomalies with each algorithm
            all_results = []
            
            for algorithm, model in self._models[metric_name].items():
                if model.model is not None:
                    results = await self._detect_with_algorithm(model, metric_data)
                    all_results.extend(results)
            
            # Ensemble voting if multiple algorithms
            if len(self._models[metric_name]) > 1:
                ensemble_results = self._ensemble_voting(all_results)
            else:
                ensemble_results = all_results
            
            # Update statistics
            self._detection_stats['total_detections'] += len(ensemble_results)
            self._detection_stats['anomalies_found'] += sum(
                1 for result in ensemble_results if result.is_anomaly
            )
            
            return ensemble_results
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies for {metric_name}: {e}")
            raise AnomalyDetectionError(
                f"Failed to detect anomalies for {metric_name}",
                detection_algorithm="ensemble",
                original_error=e
            )
    
    async def _detection_loop(self):
        """Main detection loop."""
        while self._running:
            try:
                await self._process_all_metrics()
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _process_all_metrics(self):
        """Process anomaly detection for all registered metrics."""
        detection_tasks = []
        
        for metric_name in self._models.keys():
            task = asyncio.create_task(self.detect_anomalies(metric_name))
            detection_tasks.append(task)
        
        if detection_tasks:
            results = await asyncio.gather(*detection_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Detection error for metric {list(self._models.keys())[i]}: {result}")
                elif result:
                    # Log significant anomalies
                    critical_anomalies = [
                        anom for anom in result
                        if anom.is_anomaly and anom.severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]
                    ]
                    
                    if critical_anomalies:
                        self.logger.warning(f"Found {len(critical_anomalies)} critical anomalies")
    
    async def _ensure_models_trained(self, metric_name: str):
        """Ensure all models for metric are trained."""
        if metric_name not in self._models:
            return
        
        metric_data = self._metric_data.get(metric_name, [])
        
        if len(metric_data) < self.anomaly_config.min_samples_for_training:
            return
        
        for algorithm, model in self._models[metric_name].items():
            if (model.model is None or 
                model.last_training is None or
                self._should_retrain_model(model)):
                
                await self._train_model(model, metric_data)
    
    def _should_retrain_model(self, model: AnomalyModel) -> bool:
        """Check if model should be retrained."""
        if model.last_training is None:
            return True
        
        # Retrain every 24 hours
        retrain_interval = timedelta(hours=24)
        
        if datetime.now(timezone.utc) - model.last_training > retrain_interval:
            return True
        
        # Retrain if anomaly rate is too high (possible model drift)
        anomaly_rate = model.get_recent_anomaly_rate()
        
        if anomaly_rate > 0.5:  # More than 50% anomalies indicates drift
            return True
        
        return False
    
    async def _train_model(self, model: AnomalyModel, data_points: List[MetricDataPoint]):
        """Train anomaly detection model."""
        try:
            if not SKLEARN_AVAILABLE:
                self.logger.warning("Scikit-learn not available, using statistical fallback")
                await self._train_statistical_model(model, data_points)
                return
            
            # Prepare training data
            features = self._prepare_features(data_points)
            
            if len(features) < self.anomaly_config.min_samples_for_training:
                return
            
            # Create and configure model
            if model.algorithm == MLAlgorithm.ISOLATION_FOREST:
                ml_model = IsolationForest(
                    contamination=self.anomaly_config.contamination_rate,
                    random_state=42,
                    n_estimators=100
                )
            elif model.algorithm == MLAlgorithm.ONE_CLASS_SVM:
                ml_model = OneClassSVM(
                    kernel='rbf',
                    gamma='scale',
                    nu=self.anomaly_config.contamination_rate
                )
            elif model.algorithm == MLAlgorithm.LOCAL_OUTLIER_FACTOR:
                ml_model = LocalOutlierFactor(
                    n_neighbors=20,
                    contamination=self.anomaly_config.contamination_rate,
                    novelty=True
                )
            elif model.algorithm == MLAlgorithm.GAUSSIAN_MIXTURE:
                ml_model = GaussianMixture(
                    n_components=2,
                    covariance_type='full',
                    random_state=42
                )
            elif model.algorithm == MLAlgorithm.DBSCAN_CLUSTERING:
                ml_model = DBSCAN(
                    eps=0.5,
                    min_samples=5
                )
            else:
                # Fallback to Isolation Forest\n                ml_model = IsolationForest(\n                    contamination=self.anomaly_config.contamination_rate,\n                    random_state=42\n                )\n            \n            # Scale features\n            scaler = StandardScaler()\n            scaled_features = scaler.fit_transform(features)\n            \n            # Train model\n            ml_model.fit(scaled_features)\n            \n            # Store model and scaler\n            model.model = ml_model\n            model.scaler = scaler\n            model.training_data_size = len(features)\n            model.last_training = datetime.now(timezone.utc)\n            \n            # Calculate performance metrics\n            if hasattr(ml_model, 'decision_function'):\n                try:\n                    scores = cross_val_score(ml_model, scaled_features, cv=3)\n                    model.performance_metrics['cross_val_score'] = float(np.mean(scores))\n                except:\n                    model.performance_metrics['cross_val_score'] = 0.0\n            \n            self._detection_stats['model_retrainings'] += 1\n            \n            self.logger.info(\n                f\"Trained {model.algorithm.value} model for {model.metric_name} \"\n                f\"with {len(features)} samples\"\n            )\n            \n        except Exception as e:\n            raise MLModelError(\n                f\"Failed to train {model.algorithm.value} model for {model.metric_name}\",\n                model_type=model.algorithm.value,\n                training_data_size=len(data_points),\n                original_error=e\n            )\n    \n    async def _train_statistical_model(self, model: AnomalyModel, data_points: List[MetricDataPoint]):\n        \"\"\"Train statistical anomaly detection model (fallback).\"\"\"\n        try:\n            # Extract numeric values\n            values = [\n                dp.value for dp in data_points\n                if isinstance(dp.value, (int, float))\n            ]\n            \n            if len(values) < 10:\n                return\n            \n            # Calculate statistical parameters\n            mean_val = statistics.mean(values)\n            std_val = statistics.stdev(values) if len(values) > 1 else 0\n            \n            # Store statistical model\n            model.model = {\n                'type': 'statistical',\n                'mean': mean_val,\n                'std': std_val,\n                'threshold': mean_val + (2 * std_val)  # 2 sigma threshold\n            }\n            \n            model.training_data_size = len(values)\n            model.last_training = datetime.now(timezone.utc)\n            \n            self.logger.info(\n                f\"Trained statistical model for {model.metric_name} \"\n                f\"with {len(values)} samples (mean={mean_val:.3f}, std={std_val:.3f})\"\n            )\n            \n        except Exception as e:\n            raise MLModelError(\n                f\"Failed to train statistical model for {model.metric_name}\",\n                model_type=\"statistical\",\n                original_error=e\n            )\n    \n    async def _detect_with_algorithm(\n        self,\n        model: AnomalyModel,\n        data_points: List[MetricDataPoint]\n    ) -> List[AnomalyResult]:\n        \"\"\"Detect anomalies using specific algorithm.\"\"\"\n        try:\n            if model.model is None:\n                return []\n            \n            results = []\n            \n            # Process recent data points\n            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)\n            recent_points = [\n                dp for dp in data_points\n                if dp.timestamp >= recent_cutoff\n            ]\n            \n            for dp in recent_points:\n                if isinstance(dp.value, (int, float)):\n                    anomaly_result = await self._analyze_data_point(model, dp)\n                    if anomaly_result:\n                        results.append(anomaly_result)\n                        \n                        # Add to model history\n                        model.add_anomaly(anomaly_result)\n            \n            return results\n            \n        except Exception as e:\n            raise AnomalyDetectionError(\n                f\"Failed to detect anomalies with {model.algorithm.value}\",\n                detection_algorithm=model.algorithm.value,\n                original_error=e\n            )\n    \n    async def _analyze_data_point(\n        self,\n        model: AnomalyModel,\n        data_point: MetricDataPoint\n    ) -> Optional[AnomalyResult]:\n        \"\"\"Analyze single data point for anomalies.\"\"\"\n        try:\n            if isinstance(model.model, dict) and model.model.get('type') == 'statistical':\n                return self._statistical_anomaly_detection(model, data_point)\n            \n            if not SKLEARN_AVAILABLE or model.scaler is None:\n                return self._statistical_anomaly_detection(model, data_point)\n            \n            # Prepare features\n            features = self._prepare_single_point_features(data_point)\n            scaled_features = model.scaler.transform([features])\n            \n            # Get anomaly score\n            if hasattr(model.model, 'decision_function'):\n                anomaly_score = model.model.decision_function(scaled_features)[0]\n                is_anomaly = anomaly_score < 0  # Negative scores indicate anomalies\n            elif hasattr(model.model, 'score_samples'):\n                anomaly_score = model.model.score_samples(scaled_features)[0]\n                is_anomaly = anomaly_score < self.anomaly_config.anomaly_score_threshold\n            else:\n                # Use predict method\n                prediction = model.model.predict(scaled_features)[0]\n                is_anomaly = prediction == -1\n                anomaly_score = -1.0 if is_anomaly else 1.0\n            \n            # Determine anomaly type and severity\n            anomaly_type = self._classify_anomaly_type(data_point, anomaly_score)\n            severity = self._calculate_severity(anomaly_score)\n            confidence = min(1.0, abs(anomaly_score))\n            \n            return AnomalyResult(\n                timestamp=data_point.timestamp,\n                metric_name=model.metric_name,\n                value=data_point.value,\n                anomaly_score=float(anomaly_score),\n                is_anomaly=is_anomaly,\n                anomaly_type=anomaly_type,\n                severity=severity,\n                confidence=confidence,\n                algorithm_used=model.algorithm,\n                context={\n                    'labels': data_point.labels,\n                    'model_training_size': model.training_data_size\n                }\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Error analyzing data point: {e}\")\n            return None\n    \n    def _statistical_anomaly_detection(\n        self,\n        model: AnomalyModel,\n        data_point: MetricDataPoint\n    ) -> Optional[AnomalyResult]:\n        \"\"\"Statistical anomaly detection fallback.\"\"\"\n        try:\n            if not isinstance(model.model, dict) or model.model.get('type') != 'statistical':\n                return None\n            \n            value = data_point.value\n            if not isinstance(value, (int, float)):\n                return None\n            \n            mean_val = model.model['mean']\n            std_val = model.model['std']\n            threshold = model.model['threshold']\n            \n            # Calculate z-score\n            if std_val > 0:\n                z_score = abs(value - mean_val) / std_val\n                anomaly_score = z_score\n                is_anomaly = z_score > 2.0  # 2 sigma threshold\n            else:\n                anomaly_score = abs(value - mean_val)\n                is_anomaly = abs(value - mean_val) > (mean_val * 0.1)  # 10% deviation\n            \n            if is_anomaly:\n                severity = self._calculate_severity(anomaly_score)\n                confidence = min(1.0, anomaly_score / 3.0)  # Normalize to 0-1\n                \n                return AnomalyResult(\n                    timestamp=data_point.timestamp,\n                    metric_name=model.metric_name,\n                    value=value,\n                    anomaly_score=anomaly_score,\n                    is_anomaly=True,\n                    anomaly_type=AnomalyType.POINT_ANOMALY,\n                    severity=severity,\n                    confidence=confidence,\n                    algorithm_used=MLAlgorithm.STATISTICAL_OUTLIER,\n                    context={\n                        'z_score': z_score if std_val > 0 else None,\n                        'threshold': threshold,\n                        'mean': mean_val,\n                        'std': std_val\n                    }\n                )\n            \n            return None\n            \n        except Exception as e:\n            self.logger.error(f\"Error in statistical anomaly detection: {e}\")\n            return None\n    \n    def _prepare_features(self, data_points: List[MetricDataPoint]) -> List[List[float]]:\n        \"\"\"Prepare features for ML models.\"\"\"\n        features = []\n        \n        for dp in data_points:\n            if isinstance(dp.value, (int, float)):\n                feature_vector = self._prepare_single_point_features(dp)\n                features.append(feature_vector)\n        \n        return features\n    \n    def _prepare_single_point_features(self, data_point: MetricDataPoint) -> List[float]:\n        \"\"\"Prepare features for a single data point.\"\"\"\n        # Time-based features\n        hour = data_point.timestamp.hour\n        day_of_week = data_point.timestamp.weekday()\n        minute_of_hour = data_point.timestamp.minute\n        \n        # Value-based features\n        value = float(data_point.value) if isinstance(data_point.value, (int, float)) else 0.0\n        \n        return [hour, day_of_week, minute_of_hour, value]\n    \n    def _classify_anomaly_type(self, data_point: MetricDataPoint, anomaly_score: float) -> AnomalyType:\n        \"\"\"Classify the type of anomaly.\"\"\"\n        # Simple classification based on score magnitude\n        if abs(anomaly_score) > 3.0:\n            return AnomalyType.POINT_ANOMALY\n        elif abs(anomaly_score) > 2.0:\n            return AnomalyType.CONTEXTUAL_ANOMALY\n        else:\n            return AnomalyType.TREND_ANOMALY\n    \n    def _calculate_severity(self, anomaly_score: float) -> AnomalySeverity:\n        \"\"\"Calculate anomaly severity based on score.\"\"\"\n        abs_score = abs(anomaly_score)\n        \n        if abs_score > 4.0:\n            return AnomalySeverity.CRITICAL\n        elif abs_score > 3.0:\n            return AnomalySeverity.HIGH\n        elif abs_score > 2.0:\n            return AnomalySeverity.MEDIUM\n        else:\n            return AnomalySeverity.LOW\n    \n    def _ensemble_voting(self, all_results: List[AnomalyResult]) -> List[AnomalyResult]:\n        \"\"\"Perform ensemble voting on anomaly results.\"\"\"\n        if not all_results:\n            return []\n        \n        # Group results by timestamp and metric\n        grouped_results = {}\n        \n        for result in all_results:\n            key = (result.timestamp, result.metric_name)\n            if key not in grouped_results:\n                grouped_results[key] = []\n            grouped_results[key].append(result)\n        \n        ensemble_results = []\n        \n        for key, results in grouped_results.items():\n            if len(results) == 1:\n                ensemble_results.append(results[0])\n            else:\n                # Perform voting\n                ensemble_result = self._vote_on_results(results)\n                if ensemble_result:\n                    ensemble_results.append(ensemble_result)\n        \n        return ensemble_results\n    \n    def _vote_on_results(self, results: List[AnomalyResult]) -> Optional[AnomalyResult]:\n        \"\"\"Vote on multiple anomaly results for the same data point.\"\"\"\n        if not results:\n            return None\n        \n        # Count votes for anomaly\n        anomaly_votes = sum(1 for r in results if r.is_anomaly)\n        total_votes = len(results)\n        \n        # Determine if ensemble considers it an anomaly\n        if self.anomaly_config.ensemble_voting == \"hard\":\n            is_ensemble_anomaly = anomaly_votes > (total_votes / 2)\n        else:  # soft voting\n            # Weight by confidence\n            weighted_score = sum(\n                r.anomaly_score * r.confidence for r in results if r.is_anomaly\n            ) / max(sum(r.confidence for r in results), 1)\n            \n            is_ensemble_anomaly = weighted_score > self.anomaly_config.anomaly_score_threshold\n        \n        if is_ensemble_anomaly:\n            # Create ensemble result\n            base_result = results[0]\n            \n            # Average scores and confidence\n            avg_score = statistics.mean([r.anomaly_score for r in results])\n            avg_confidence = statistics.mean([r.confidence for r in results])\n            \n            # Use highest severity\n            severities = [r.severity for r in results]\n            severity_order = [AnomalySeverity.LOW, AnomalySeverity.MEDIUM, AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]\n            max_severity = max(severities, key=lambda s: severity_order.index(s))\n            \n            return AnomalyResult(\n                timestamp=base_result.timestamp,\n                metric_name=base_result.metric_name,\n                value=base_result.value,\n                anomaly_score=avg_score,\n                is_anomaly=True,\n                anomaly_type=base_result.anomaly_type,\n                severity=max_severity,\n                confidence=avg_confidence,\n                algorithm_used=MLAlgorithm.ISOLATION_FOREST,  # Ensemble placeholder\n                context={\n                    'ensemble_voting': self.anomaly_config.ensemble_voting,\n                    'votes': f\"{anomaly_votes}/{total_votes}\",\n                    'algorithms_used': [r.algorithm_used.value for r in results]\n                }\n            )\n        \n        return None\n    \n    def get_detector_stats(self) -> Dict[str, Any]:\n        \"\"\"Get anomaly detector statistics.\"\"\"\n        total_models = sum(len(models) for models in self._models.values())\n        total_anomalies = sum(\n            len(model.anomaly_history)\n            for models in self._models.values()\n            for model in models.values()\n        )\n        \n        return {\n            'total_metrics': len(self._models),\n            'total_models': total_models,\n            'total_anomalies_detected': total_anomalies,\n            'running': self._running,\n            'detection_stats': self._detection_stats.copy(),\n            'algorithms_enabled': [alg.value for alg in self.anomaly_config.algorithms],\n            'contamination_rate': self.anomaly_config.contamination_rate,\n            'sensitivity': self.anomaly_config.sensitivity\n        }\n\n\ndef create_anomaly_detector(config: IntelligentAlertingConfig) -> AnomalyDetector:\n    \"\"\"Create anomaly detector.\"\"\"\n    return AnomalyDetector(config)\n\n\n# Export main classes and functions\n__all__ = [\n    'AnomalyType',\n    'AnomalySeverity',\n    'AnomalyResult',\n    'AnomalyModel',\n    'AnomalyDetector',\n    'create_anomaly_detector',\n]"
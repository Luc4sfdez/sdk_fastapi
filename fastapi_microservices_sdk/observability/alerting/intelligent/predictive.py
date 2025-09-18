"""
Predictive Alerting System for FastAPI Microservices SDK.

This module provides predictive alerting capabilities using machine learning
to forecast potential issues before they occur.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

from .config import IntelligentAlertingConfig
from .exceptions import PredictiveAlertingError
from ..notifications import NotificationMessage
from ..config import AlertSeverity


class PredictionHorizon(str, Enum):
    """Prediction time horizon."""
    SHORT_TERM = "5m"      # 5 minutes
    MEDIUM_TERM = "30m"    # 30 minutes
    LONG_TERM = "2h"       # 2 hours
    EXTENDED = "24h"       # 24 hours


class PredictionConfidence(str, Enum):
    """Prediction confidence level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class MetricDataPoint:
    """Metric data point for prediction."""
    timestamp: datetime
    value: float
    metric_name: str
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertPrediction:
    """Alert prediction result."""
    metric_name: str
    predicted_value: float
    prediction_time: datetime
    horizon: PredictionHorizon
    confidence: PredictionConfidence
    confidence_score: float
    threshold_breach_probability: float
    recommended_action: str
    model_used: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'metric_name': self.metric_name,
            'predicted_value': self.predicted_value,
            'prediction_time': self.prediction_time.isoformat(),
            'horizon': self.horizon.value,
            'confidence': self.confidence.value,
            'confidence_score': self.confidence_score,
            'threshold_breach_probability': self.threshold_breach_probability,
            'recommended_action': self.recommended_action,
            'model_used': self.model_used
        }


@dataclass
class PredictionModel:
    """Prediction model metadata."""
    name: str
    model_type: str
    trained_at: datetime
    accuracy_score: float
    feature_names: List[str]
    target_metric: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'model_type': self.model_type,
            'trained_at': self.trained_at.isoformat(),
            'accuracy_score': self.accuracy_score,
            'feature_names': self.feature_names,
            'target_metric': self.target_metric
        }


class PredictiveAlerting:
    """Predictive alerting engine."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize predictive alerting."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Prediction models
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.model_metadata: Dict[str, PredictionModel] = {}
        
        # Data storage
        self.metric_history: Dict[str, List[MetricDataPoint]] = {}
        self.max_history_size = 10000
        
        # Prediction parameters
        self.prediction_horizons = {
            PredictionHorizon.SHORT_TERM: timedelta(minutes=5),
            PredictionHorizon.MEDIUM_TERM: timedelta(minutes=30),
            PredictionHorizon.LONG_TERM: timedelta(hours=2),
            PredictionHorizon.EXTENDED: timedelta(hours=24)
        }
        
        # Thresholds for different metrics
        self.metric_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 1000.0,  # ms
            'error_rate': 5.0,  # %
            'request_rate': 1000.0  # requests/sec
        }
    
    async def add_metric_data(self, data_point: MetricDataPoint):
        """Add metric data point for prediction."""
        try:
            metric_name = data_point.metric_name
            
            if metric_name not in self.metric_history:
                self.metric_history[metric_name] = []
            
            self.metric_history[metric_name].append(data_point)
            
            # Maintain history size
            if len(self.metric_history[metric_name]) > self.max_history_size:
                self.metric_history[metric_name] = self.metric_history[metric_name][-self.max_history_size:]
            
            # Check if we need to retrain models
            if len(self.metric_history[metric_name]) % 100 == 0:
                await self._maybe_retrain_model(metric_name)
                
        except Exception as e:
            self.logger.error(f"Error adding metric data: {e}")
            raise PredictiveAlertingError(
                f"Failed to add metric data: {e}",
                prediction_model="data_ingestion",
                original_error=e
            )
    
    async def predict_alerts(
        self,
        metric_name: str,
        horizon: PredictionHorizon = PredictionHorizon.MEDIUM_TERM
    ) -> Optional[AlertPrediction]:
        """Predict potential alerts for a metric."""
        try:
            if metric_name not in self.metric_history:
                self.logger.warning(f"No history available for metric: {metric_name}")
                return None
            
            history = self.metric_history[metric_name]
            if len(history) < 50:  # Minimum data points needed
                self.logger.warning(f"Insufficient data for prediction: {metric_name}")
                return None
            
            # Ensure model is trained
            if metric_name not in self.models:
                await self._train_model(metric_name)
            
            # Prepare features
            features = self._prepare_features(history, horizon)
            if features is None:
                return None
            
            # Make prediction
            model = self.models[metric_name]
            scaler = self.scalers.get(metric_name)
            
            if scaler:
                features_scaled = scaler.transform([features])
            else:
                features_scaled = [features]
            
            predicted_value = model.predict(features_scaled)[0]
            
            # Calculate confidence and breach probability
            confidence_score, confidence_level = self._calculate_confidence(
                metric_name, predicted_value, features
            )
            
            breach_probability = self._calculate_breach_probability(
                metric_name, predicted_value
            )
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                metric_name, predicted_value, breach_probability
            )
            
            # Determine model used
            model_used = self.model_metadata.get(metric_name, PredictionModel(
                name="default", model_type="unknown", trained_at=datetime.now(),
                accuracy_score=0.0, feature_names=[], target_metric=metric_name
            )).model_type
            
            return AlertPrediction(
                metric_name=metric_name,
                predicted_value=predicted_value,
                prediction_time=datetime.now(timezone.utc),
                horizon=horizon,
                confidence=confidence_level,
                confidence_score=confidence_score,
                threshold_breach_probability=breach_probability,
                recommended_action=recommendation,
                model_used=model_used
            )
            
        except Exception as e:
            self.logger.error(f"Error predicting alerts for {metric_name}: {e}")
            raise PredictiveAlertingError(
                f"Failed to predict alerts: {e}",
                prediction_model=metric_name,
                prediction_horizon=horizon.value,
                original_error=e
            )
    
    async def predict_multiple_metrics(
        self,
        metric_names: List[str],
        horizon: PredictionHorizon = PredictionHorizon.MEDIUM_TERM
    ) -> List[AlertPrediction]:
        """Predict alerts for multiple metrics."""
        predictions = []
        
        for metric_name in metric_names:
            try:
                prediction = await self.predict_alerts(metric_name, horizon)
                if prediction:
                    predictions.append(prediction)
            except Exception as e:
                self.logger.error(f"Error predicting {metric_name}: {e}")
        
        return predictions
    
    async def _train_model(self, metric_name: str):
        """Train prediction model for a metric."""
        try:
            history = self.metric_history[metric_name]
            if len(history) < 100:  # Minimum training data
                self.logger.warning(f"Insufficient training data for {metric_name}")
                return
            
            # Prepare training data
            X, y = self._prepare_training_data(history)
            if len(X) == 0:
                return
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            self.scalers[metric_name] = scaler
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_scaled, y)
            
            # Evaluate model
            y_pred = model.predict(X_scaled)
            mse = mean_squared_error(y, y_pred)
            mae = mean_absolute_error(y, y_pred)
            
            # Calculate accuracy score (1 - normalized MAE)
            y_range = max(y) - min(y) if max(y) != min(y) else 1
            accuracy_score = max(0, 1 - (mae / y_range))
            
            # Store model and metadata
            self.models[metric_name] = model
            self.model_metadata[metric_name] = PredictionModel(
                name=f"{metric_name}_predictor",
                model_type="random_forest",
                trained_at=datetime.now(timezone.utc),
                accuracy_score=accuracy_score,
                feature_names=self._get_feature_names(),
                target_metric=metric_name
            )
            
            self.logger.info(
                f"Trained model for {metric_name}: "
                f"MSE={mse:.4f}, MAE={mae:.4f}, Accuracy={accuracy_score:.4f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error training model for {metric_name}: {e}")
            raise PredictiveAlertingError(
                f"Failed to train model: {e}",
                prediction_model=metric_name,
                original_error=e
            )
    
    async def _maybe_retrain_model(self, metric_name: str):
        """Check if model needs retraining."""
        if metric_name not in self.model_metadata:
            await self._train_model(metric_name)
            return
        
        metadata = self.model_metadata[metric_name]
        
        # Retrain if model is old or accuracy is low
        age = datetime.now(timezone.utc) - metadata.trained_at
        if age > timedelta(hours=24) or metadata.accuracy_score < 0.7:
            self.logger.info(f"Retraining model for {metric_name}")
            await self._train_model(metric_name)
    
    def _prepare_training_data(self, history: List[MetricDataPoint]) -> Tuple[List[List[float]], List[float]]:
        """Prepare training data from metric history."""
        X, y = [], []
        
        # Use sliding window approach
        window_size = 10  # Use last 10 data points as features
        
        for i in range(window_size, len(history)):
            # Features: last window_size values and time-based features
            window_values = [history[j].value for j in range(i - window_size, i)]
            
            # Add time-based features
            current_time = history[i].timestamp
            hour_of_day = current_time.hour
            day_of_week = current_time.weekday()
            
            # Statistical features
            window_mean = np.mean(window_values)
            window_std = np.std(window_values)
            window_trend = window_values[-1] - window_values[0]
            
            features = window_values + [
                hour_of_day, day_of_week,
                window_mean, window_std, window_trend
            ]
            
            X.append(features)
            y.append(history[i].value)
        
        return X, y
    
    def _prepare_features(
        self,
        history: List[MetricDataPoint],
        horizon: PredictionHorizon
    ) -> Optional[List[float]]:
        """Prepare features for prediction."""
        if len(history) < 10:
            return None
        
        # Use last 10 values as base features
        recent_values = [dp.value for dp in history[-10:]]
        
        # Add time-based features for prediction time
        prediction_time = datetime.now(timezone.utc) + self.prediction_horizons[horizon]
        hour_of_day = prediction_time.hour
        day_of_week = prediction_time.weekday()
        
        # Statistical features
        window_mean = np.mean(recent_values)
        window_std = np.std(recent_values)
        window_trend = recent_values[-1] - recent_values[0]
        
        features = recent_values + [
            hour_of_day, day_of_week,
            window_mean, window_std, window_trend
        ]
        
        return features
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names for model."""
        feature_names = [f"value_lag_{i}" for i in range(1, 11)]
        feature_names.extend([
            "hour_of_day", "day_of_week",
            "window_mean", "window_std", "window_trend"
        ])
        return feature_names
    
    def _calculate_confidence(
        self,
        metric_name: str,
        predicted_value: float,
        features: List[float]
    ) -> Tuple[float, PredictionConfidence]:
        """Calculate prediction confidence."""
        # Base confidence on model accuracy
        base_confidence = 0.5
        if metric_name in self.model_metadata:
            base_confidence = self.model_metadata[metric_name].accuracy_score
        
        # Adjust based on data stability
        recent_values = features[:10]  # First 10 features are recent values
        stability = 1.0 - (np.std(recent_values) / (np.mean(recent_values) + 1e-6))
        stability = max(0, min(1, stability))
        
        # Combined confidence score
        confidence_score = (base_confidence * 0.7 + stability * 0.3)
        
        # Map to confidence level
        if confidence_score >= 0.9:
            confidence_level = PredictionConfidence.VERY_HIGH
        elif confidence_score >= 0.7:
            confidence_level = PredictionConfidence.HIGH
        elif confidence_score >= 0.5:
            confidence_level = PredictionConfidence.MEDIUM
        else:
            confidence_level = PredictionConfidence.LOW
        
        return confidence_score, confidence_level
    
    def _calculate_breach_probability(
        self,
        metric_name: str,
        predicted_value: float
    ) -> float:
        """Calculate probability of threshold breach."""
        threshold = self.metric_thresholds.get(metric_name, 100.0)
        
        if predicted_value <= threshold:
            return 0.0
        
        # Simple calculation - could be enhanced with uncertainty estimation
        excess = predicted_value - threshold
        breach_probability = min(1.0, excess / threshold)
        
        return breach_probability
    
    def _generate_recommendation(
        self,
        metric_name: str,
        predicted_value: float,
        breach_probability: float
    ) -> str:
        """Generate recommendation based on prediction."""
        if breach_probability < 0.1:
            return "No action required - metrics within normal range"
        elif breach_probability < 0.3:
            return f"Monitor {metric_name} closely - potential threshold breach"
        elif breach_probability < 0.7:
            return f"Prepare for {metric_name} threshold breach - consider scaling"
        else:
            return f"Immediate action required - {metric_name} threshold breach imminent"
    
    async def get_model_info(self, metric_name: str) -> Optional[PredictionModel]:
        """Get model information for a metric."""
        return self.model_metadata.get(metric_name)
    
    async def get_all_models_info(self) -> Dict[str, PredictionModel]:
        """Get information for all trained models."""
        return self.model_metadata.copy()
    
    async def retrain_all_models(self):
        """Retrain all models."""
        for metric_name in self.metric_history.keys():
            try:
                await self._train_model(metric_name)
            except Exception as e:
                self.logger.error(f"Error retraining model for {metric_name}: {e}")


def create_predictive_alerting(config: IntelligentAlertingConfig) -> PredictiveAlerting:
    """Create predictive alerting instance."""
    return PredictiveAlerting(config)
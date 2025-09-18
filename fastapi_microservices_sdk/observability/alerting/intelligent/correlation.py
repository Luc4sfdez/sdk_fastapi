"""
Alert Correlation and Root Cause Analysis for FastAPI Microservices SDK.

This module provides intelligent alert correlation to identify related alerts
and perform root cause analysis to reduce alert noise and improve incident response.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import statistics
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging
import networkx as nx
from collections import defaultdict, Counter

from .config import IntelligentAlertingConfig, CorrelationMethod
from .exceptions import CorrelationAnalysisError
from ..notifications import NotificationMessage
from ..config import AlertSeverity


class CorrelationType(str, Enum):
    """Alert correlation type."""
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    SPATIAL = "spatial"
    SEMANTIC = "semantic"
    STATISTICAL = "statistical"


@dataclass
class CorrelationResult:
    """Alert correlation result."""
    primary_alert_id: str
    correlated_alerts: List[str]
    correlation_type: CorrelationType
    correlation_score: float
    confidence_level: float
    root_cause_probability: float
    correlation_window: timedelta
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'primary_alert_id': self.primary_alert_id,
            'correlated_alerts': self.correlated_alerts,
            'correlation_type': self.correlation_type.value,
            'correlation_score': self.correlation_score,
            'confidence_level': self.confidence_level,
            'root_cause_probability': self.root_cause_probability,
            'correlation_window': self.correlation_window.total_seconds()
        }


@dataclass
class RootCauseAnalysis:
    """Root cause analysis result."""
    root_cause_alert_id: str
    affected_alerts: List[str]
    impact_score: float
    propagation_path: List[str]
    analysis_confidence: float
    recommended_actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'root_cause_alert_id': self.root_cause_alert_id,
            'affected_alerts': self.affected_alerts,
            'impact_score': self.impact_score,
            'propagation_path': self.propagation_path,
            'analysis_confidence': self.analysis_confidence,
            'recommended_actions': self.recommended_actions
        }


class AlertCorrelator:
    """Alert correlation engine."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize alert correlator."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Correlation state
        self.alert_history: List[NotificationMessage] = []
        self.correlation_graph = nx.DiGraph()
        self.correlation_cache: Dict[str, List[CorrelationResult]] = {}
        
        # Correlation parameters
        self.temporal_window = timedelta(minutes=30)
        self.correlation_threshold = 0.7
        self.max_history_size = 10000
        
    async def correlate_alerts(
        self,
        alert: NotificationMessage,
        correlation_methods: Optional[List[CorrelationMethod]] = None
    ) -> List[CorrelationResult]:
        """Correlate alert with existing alerts."""
        try:
            if correlation_methods is None:
                correlation_methods = self.config.correlation_methods
            
            correlations = []
            
            # Add alert to history
            self._add_to_history(alert)
            
            # Apply correlation methods
            for method in correlation_methods:
                method_correlations = await self._apply_correlation_method(
                    alert, method
                )
                correlations.extend(method_correlations)
            
            # Remove duplicates and sort by score
            unique_correlations = self._deduplicate_correlations(correlations)
            unique_correlations.sort(key=lambda x: x.correlation_score, reverse=True)
            
            # Cache results
            self.correlation_cache[alert.id] = unique_correlations
            
            return unique_correlations
            
        except Exception as e:
            self.logger.error(f"Error correlating alerts: {e}")
            raise CorrelationAnalysisError(
                f"Failed to correlate alerts: {e}",
                correlation_method=str(correlation_methods),
                original_error=e
            )
    
    async def _apply_correlation_method(
        self,
        alert: NotificationMessage,
        method: CorrelationMethod
    ) -> List[CorrelationResult]:
        """Apply specific correlation method."""
        try:
            if method == CorrelationMethod.TEMPORAL:
                return await self._temporal_correlation(alert)
            elif method == CorrelationMethod.CAUSAL:
                return await self._causal_correlation(alert)
            elif method == CorrelationMethod.STATISTICAL:
                return await self._statistical_correlation(alert)
            elif method == CorrelationMethod.GRAPH_BASED:
                return await self._graph_based_correlation(alert)
            elif method == CorrelationMethod.ML_BASED:
                return await self._ml_based_correlation(alert)
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error in correlation method {method}: {e}")
            return []
    
    async def _temporal_correlation(
        self,
        alert: NotificationMessage
    ) -> List[CorrelationResult]:
        """Perform temporal correlation analysis."""
        correlations = []
        
        # Find alerts within temporal window
        cutoff_time = alert.timestamp - self.temporal_window
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp >= cutoff_time and a.id != alert.id
        ]
        
        for candidate in recent_alerts:
            # Calculate temporal correlation score
            time_diff = abs((alert.timestamp - candidate.timestamp).total_seconds())
            max_time_diff = self.temporal_window.total_seconds()
            
            # Closer in time = higher correlation
            temporal_score = 1.0 - (time_diff / max_time_diff)
            
            # Consider service and severity similarity
            service_similarity = self._calculate_service_similarity(alert, candidate)
            severity_similarity = self._calculate_severity_similarity(alert, candidate)
            
            correlation_score = (
                temporal_score * 0.4 +
                service_similarity * 0.3 +
                severity_similarity * 0.3
            )
            
            if correlation_score >= self.correlation_threshold:
                correlations.append(CorrelationResult(
                    primary_alert_id=alert.id,
                    correlated_alerts=[candidate.id],
                    correlation_type=CorrelationType.TEMPORAL,
                    correlation_score=correlation_score,
                    confidence_level=temporal_score,
                    root_cause_probability=0.5,
                    correlation_window=self.temporal_window
                ))
        
        return correlations
    
    async def _causal_correlation(
        self,
        alert: NotificationMessage
    ) -> List[CorrelationResult]:
        """Perform causal correlation analysis."""
        correlations = []
        
        # Look for known causal relationships
        causal_patterns = {
            'database_connection_error': ['application_error', 'timeout_error'],
            'high_cpu_usage': ['slow_response_time', 'memory_pressure'],
            'network_partition': ['service_unavailable', 'connection_timeout'],
            'disk_full': ['write_error', 'application_crash']
        }
        
        alert_type = self._extract_alert_type(alert)
        
        if alert_type in causal_patterns:
            # Look for downstream effects
            downstream_types = causal_patterns[alert_type]
            
            for candidate in self.alert_history[-100:]:  # Recent alerts
                candidate_type = self._extract_alert_type(candidate)
                
                if candidate_type in downstream_types:
                    # Check if candidate occurred after alert
                    if candidate.timestamp > alert.timestamp:
                        time_diff = (candidate.timestamp - alert.timestamp).total_seconds()
                        
                        # Causal relationship likely if within reasonable time
                        if time_diff <= 300:  # 5 minutes
                            causal_score = 1.0 - (time_diff / 300)
                            
                            correlations.append(CorrelationResult(
                                primary_alert_id=alert.id,
                                correlated_alerts=[candidate.id],
                                correlation_type=CorrelationType.CAUSAL,
                                correlation_score=causal_score,
                                confidence_level=0.8,
                                root_cause_probability=0.9,
                                correlation_window=timedelta(minutes=5)
                            ))
        
        return correlations
    
    async def _statistical_correlation(
        self,
        alert: NotificationMessage
    ) -> List[CorrelationResult]:
        """Perform statistical correlation analysis."""
        correlations = []
        
        # Group alerts by type and calculate co-occurrence
        alert_type = self._extract_alert_type(alert)
        
        # Count co-occurrences in recent history
        co_occurrence_counts = defaultdict(int)
        total_occurrences = defaultdict(int)
        
        for i, hist_alert in enumerate(self.alert_history[-1000:]):
            hist_type = self._extract_alert_type(hist_alert)
            total_occurrences[hist_type] += 1
            
            # Look for alerts within correlation window
            window_start = max(0, i - 10)  # Look at 10 alerts before/after
            window_end = min(len(self.alert_history), i + 10)
            
            for j in range(window_start, window_end):
                if i != j:
                    other_alert = self.alert_history[j]
                    other_type = self._extract_alert_type(other_alert)
                    
                    if hist_type == alert_type:
                        co_occurrence_counts[other_type] += 1
        
        # Calculate statistical correlation
        for other_type, co_count in co_occurrence_counts.items():
            if total_occurrences[alert_type] > 0 and total_occurrences[other_type] > 0:
                # Calculate correlation coefficient
                correlation_coeff = co_count / min(
                    total_occurrences[alert_type],
                    total_occurrences[other_type]
                )
                
                if correlation_coeff >= 0.3:  # Minimum correlation threshold
                    # Find recent alerts of this type
                    recent_candidates = [
                        a for a in self.alert_history[-50:]
                        if self._extract_alert_type(a) == other_type and a.id != alert.id
                    ]
                    
                    for candidate in recent_candidates:
                        correlations.append(CorrelationResult(
                            primary_alert_id=alert.id,
                            correlated_alerts=[candidate.id],
                            correlation_type=CorrelationType.STATISTICAL,
                            correlation_score=correlation_coeff,
                            confidence_level=min(correlation_coeff * 2, 1.0),
                            root_cause_probability=0.6,
                            correlation_window=self.temporal_window
                        ))
        
        return correlations
    
    async def _graph_based_correlation(
        self,
        alert: NotificationMessage
    ) -> List[CorrelationResult]:
        """Perform graph-based correlation analysis."""
        correlations = []
        
        # Add alert to correlation graph
        self.correlation_graph.add_node(alert.id, alert=alert)
        
        # Connect to related alerts based on service topology
        service_name = alert.labels.get('service', 'unknown')
        
        # Find alerts from related services
        for node_id, node_data in self.correlation_graph.nodes(data=True):
            if node_id != alert.id and 'alert' in node_data:
                other_alert = node_data['alert']
                other_service = other_alert.labels.get('service', 'unknown')
                
                # Check if services are related
                if self._are_services_related(service_name, other_service):
                    # Add edge with weight based on relationship strength
                    relationship_strength = self._calculate_service_relationship_strength(
                        service_name, other_service
                    )
                    
                    self.correlation_graph.add_edge(
                        alert.id, other_alert.id,
                        weight=relationship_strength
                    )
                    
                    correlations.append(CorrelationResult(
                        primary_alert_id=alert.id,
                        correlated_alerts=[other_alert.id],
                        correlation_type=CorrelationType.SPATIAL,
                        correlation_score=relationship_strength,
                        confidence_level=0.7,
                        root_cause_probability=0.5,
                        correlation_window=self.temporal_window
                    ))
        
        return correlations
    
    async def _ml_based_correlation(
        self,
        alert: NotificationMessage
    ) -> List[CorrelationResult]:
        """Perform ML-based correlation analysis."""
        # This would use trained ML models for correlation
        # For now, return empty list as placeholder
        return []
    
    def _calculate_service_similarity(
        self,
        alert1: NotificationMessage,
        alert2: NotificationMessage
    ) -> float:
        """Calculate service similarity between alerts."""
        service1 = alert1.labels.get('service', '')
        service2 = alert2.labels.get('service', '')
        
        if service1 == service2:
            return 1.0
        elif service1 and service2:
            # Simple string similarity
            common_chars = set(service1) & set(service2)
            total_chars = set(service1) | set(service2)
            return len(common_chars) / len(total_chars) if total_chars else 0.0
        else:
            return 0.0
    
    def _calculate_severity_similarity(
        self,
        alert1: NotificationMessage,
        alert2: NotificationMessage
    ) -> float:
        """Calculate severity similarity between alerts."""
        severity_weights = {
            AlertSeverity.CRITICAL: 4,
            AlertSeverity.HIGH: 3,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 1
        }
        
        weight1 = severity_weights.get(alert1.severity, 1)
        weight2 = severity_weights.get(alert2.severity, 1)
        
        # Closer severities have higher similarity
        max_diff = max(severity_weights.values()) - min(severity_weights.values())
        actual_diff = abs(weight1 - weight2)
        
        return 1.0 - (actual_diff / max_diff)
    
    def _extract_alert_type(self, alert: NotificationMessage) -> str:
        """Extract alert type from alert."""
        # Try to extract from labels or title
        alert_type = alert.labels.get('alert_type', '')
        if not alert_type:
            # Extract from title using keywords
            title_lower = alert.title.lower()
            if 'error' in title_lower:
                alert_type = 'error'
            elif 'timeout' in title_lower:
                alert_type = 'timeout'
            elif 'cpu' in title_lower:
                alert_type = 'cpu_usage'
            elif 'memory' in title_lower:
                alert_type = 'memory_usage'
            elif 'disk' in title_lower:
                alert_type = 'disk_usage'
            elif 'network' in title_lower:
                alert_type = 'network_issue'
            else:
                alert_type = 'unknown'
        
        return alert_type
    
    def _are_services_related(self, service1: str, service2: str) -> bool:
        """Check if two services are related."""
        # Simple heuristic - services with similar names are related
        if service1 == service2:
            return True
        
        # Check for common prefixes/suffixes
        common_prefixes = ['api', 'web', 'auth', 'user', 'order', 'payment']
        
        for prefix in common_prefixes:
            if service1.startswith(prefix) and service2.startswith(prefix):
                return True
        
        return False
    
    def _calculate_service_relationship_strength(
        self,
        service1: str,
        service2: str
    ) -> float:
        """Calculate relationship strength between services."""
        if service1 == service2:
            return 1.0
        
        # Simple similarity calculation
        common_chars = set(service1.lower()) & set(service2.lower())
        total_chars = set(service1.lower()) | set(service2.lower())
        
        return len(common_chars) / len(total_chars) if total_chars else 0.0
    
    def _add_to_history(self, alert: NotificationMessage):
        """Add alert to history with size management."""
        self.alert_history.append(alert)
        
        # Maintain history size
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
    
    def _deduplicate_correlations(
        self,
        correlations: List[CorrelationResult]
    ) -> List[CorrelationResult]:
        """Remove duplicate correlations."""
        seen = set()
        unique_correlations = []
        
        for correlation in correlations:
            # Create a key for deduplication
            key = (
                correlation.primary_alert_id,
                tuple(sorted(correlation.correlated_alerts)),
                correlation.correlation_type
            )
            
            if key not in seen:
                seen.add(key)
                unique_correlations.append(correlation)
        
        return unique_correlations


class RootCauseAnalyzer:
    """Root cause analysis engine."""
    
    def __init__(self, config: IntelligentAlertingConfig):
        """Initialize root cause analyzer."""
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def analyze_root_cause(
        self,
        correlations: List[CorrelationResult]
    ) -> Optional[RootCauseAnalysis]:
        """Analyze root cause from correlations."""
        try:
            if not correlations:
                return None
            
            # Build impact graph
            impact_graph = self._build_impact_graph(correlations)
            
            # Find root cause candidate
            root_cause_id = self._identify_root_cause(impact_graph, correlations)
            
            if not root_cause_id:
                return None
            
            # Analyze impact and propagation
            affected_alerts = self._find_affected_alerts(root_cause_id, correlations)
            impact_score = self._calculate_impact_score(root_cause_id, affected_alerts)
            propagation_path = self._trace_propagation_path(root_cause_id, correlations)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(root_cause_id, correlations)
            
            return RootCauseAnalysis(
                root_cause_alert_id=root_cause_id,
                affected_alerts=affected_alerts,
                impact_score=impact_score,
                propagation_path=propagation_path,
                analysis_confidence=0.8,  # Would be calculated based on correlation strength
                recommended_actions=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error in root cause analysis: {e}")
            raise CorrelationAnalysisError(
                f"Failed to analyze root cause: {e}",
                original_error=e
            )
    
    def _build_impact_graph(self, correlations: List[CorrelationResult]) -> nx.DiGraph:
        """Build impact graph from correlations."""
        graph = nx.DiGraph()
        
        for correlation in correlations:
            # Add nodes
            graph.add_node(correlation.primary_alert_id)
            for alert_id in correlation.correlated_alerts:
                graph.add_node(alert_id)
            
            # Add edges based on correlation type and score
            for alert_id in correlation.correlated_alerts:
                if correlation.correlation_type == CorrelationType.CAUSAL:
                    # Causal relationships indicate direction
                    if correlation.root_cause_probability > 0.7:
                        graph.add_edge(
                            correlation.primary_alert_id,
                            alert_id,
                            weight=correlation.correlation_score,
                            type='causal'
                        )
                else:
                    # Other relationships are bidirectional
                    graph.add_edge(
                        correlation.primary_alert_id,
                        alert_id,
                        weight=correlation.correlation_score,
                        type=correlation.correlation_type.value
                    )
        
        return graph
    
    def _identify_root_cause(
        self,
        graph: nx.DiGraph,
        correlations: List[CorrelationResult]
    ) -> Optional[str]:
        """Identify root cause from impact graph."""
        if not graph.nodes():
            return None
        
        # Calculate centrality measures
        try:
            # Out-degree centrality (alerts that cause others)
            out_centrality = nx.out_degree_centrality(graph)
            
            # Betweenness centrality (alerts in propagation paths)
            betweenness = nx.betweenness_centrality(graph)
            
            # Combine measures to find root cause
            candidates = {}
            for node in graph.nodes():
                score = (
                    out_centrality.get(node, 0) * 0.6 +
                    betweenness.get(node, 0) * 0.4
                )
                candidates[node] = score
            
            # Return node with highest score
            if candidates:
                return max(candidates, key=candidates.get)
            
        except Exception as e:
            self.logger.warning(f"Error calculating centrality: {e}")
            
            # Fallback: use correlation scores
            alert_scores = defaultdict(float)
            for correlation in correlations:
                if correlation.correlation_type == CorrelationType.CAUSAL:
                    alert_scores[correlation.primary_alert_id] += correlation.root_cause_probability
            
            if alert_scores:
                return max(alert_scores, key=alert_scores.get)
        
        return None
    
    def _find_affected_alerts(
        self,
        root_cause_id: str,
        correlations: List[CorrelationResult]
    ) -> List[str]:
        """Find alerts affected by root cause."""
        affected = set()
        
        for correlation in correlations:
            if correlation.primary_alert_id == root_cause_id:
                affected.update(correlation.correlated_alerts)
            elif root_cause_id in correlation.correlated_alerts:
                affected.add(correlation.primary_alert_id)
        
        return list(affected)
    
    def _calculate_impact_score(
        self,
        root_cause_id: str,
        affected_alerts: List[str]
    ) -> float:
        """Calculate impact score of root cause."""
        # Simple calculation based on number of affected alerts
        base_score = min(len(affected_alerts) / 10.0, 1.0)  # Normalize to 0-1
        
        # Could be enhanced with severity weights, service criticality, etc.
        return base_score
    
    def _trace_propagation_path(
        self,
        root_cause_id: str,
        correlations: List[CorrelationResult]
    ) -> List[str]:
        """Trace propagation path from root cause."""
        path = [root_cause_id]
        
        # Simple path tracing - could be enhanced with graph algorithms
        for correlation in correlations:
            if (correlation.primary_alert_id == root_cause_id and
                correlation.correlation_type == CorrelationType.CAUSAL):
                path.extend(correlation.correlated_alerts)
        
        return path
    
    def _generate_recommendations(
        self,
        root_cause_id: str,
        correlations: List[CorrelationResult]
    ) -> List[str]:
        """Generate recommendations for root cause."""
        recommendations = [
            f"Investigate root cause alert: {root_cause_id}",
            "Check service dependencies and health",
            "Review recent deployments or configuration changes",
            "Monitor for cascading failures"
        ]
        
        # Add specific recommendations based on correlation types
        causal_correlations = [
            c for c in correlations
            if c.primary_alert_id == root_cause_id and
            c.correlation_type == CorrelationType.CAUSAL
        ]
        
        if causal_correlations:
            recommendations.append("Focus on preventing cascade effects")
            recommendations.append("Consider implementing circuit breakers")
        
        return recommendations


def create_alert_correlator(config: IntelligentAlertingConfig) -> AlertCorrelator:
    """Create alert correlator instance."""
    return AlertCorrelator(config)


def create_root_cause_analyzer(config: IntelligentAlertingConfig) -> RootCauseAnalyzer:
    """Create root cause analyzer instance."""
    return RootCauseAnalyzer(config)
"""
Threat Detection System for FastAPI Microservices SDK

This module provides comprehensive threat detection capabilities including:
- Real-time threat analysis and pattern recognition
- Anomaly detection and behavioral analysis
- Attack signature matching and scoring
- Automated threat response and alerting
- Integration with existing security components

Author: FastAPI Microservices Team
Version: 1.0.0
"""

import asyncio
import json
import re
import hashlib
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from pathlib import Path
import ipaddress

from .exceptions import AdvancedSecurityError
from .logging import SecurityLogger, SecurityEvent, SecurityEventType, SecurityEventSeverity


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ThreatDetectionError(AdvancedSecurityError):
    """Exception raised for threat detection errors."""
    pass


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class ThreatLevel(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(str, Enum):
    """Types of security threats."""
    BRUTE_FORCE = "brute_force"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    TIME_ANOMALY = "time_anomaly"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    DIRECTORY_TRAVERSAL = "directory_traversal"
    MALICIOUS_USER_AGENT = "malicious_user_agent"
    SUSPICIOUS_IP = "suspicious_ip"
    ACCOUNT_TAKEOVER = "account_takeover"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class ActionType(str, Enum):
    """Types of actions that can be taken in response to threats."""
    LOG_ONLY = "log_only"
    ALERT = "alert"
    RATE_LIMIT = "rate_limit"
    BLOCK_IP = "block_ip"
    BLOCK_USER = "block_user"
    REQUIRE_MFA = "require_mfa"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"


# =============================================================================
# DATA MODELS
# =============================================================================
@dataclass
class AnomalyScore:
    """Represents an anomaly score for threat assessment."""
    
    score: float  # 0.0 to 1.0, where 1.0 is most anomalous
    confidence: float  # 0.0 to 1.0, confidence in the score
    factors: Dict[str, float] = field(default_factory=dict)  # Contributing factors
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate score and confidence values."""
        if not 0.0 <= self.score <= 1.0:
            raise ThreatDetectionError(f"Score must be between 0.0 and 1.0, got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ThreatDetectionError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def is_anomalous(self, threshold: float = 0.7) -> bool:
        """Check if the score indicates an anomaly."""
        return self.score >= threshold
    
    def weighted_score(self) -> float:
        """Get confidence-weighted anomaly score."""
        return self.score * self.confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "score": self.score,
            "confidence": self.confidence,
            "factors": self.factors,
            "timestamp": self.timestamp.isoformat(),
            "is_anomalous": self.is_anomalous(),
            "weighted_score": self.weighted_score()
        }


@dataclass
class ThreatIndicator:
    """Represents a single threat indicator."""
    
    indicator_type: str  # IP, user_agent, pattern, etc.
    value: str  # The actual indicator value
    threat_types: List[ThreatType] = field(default_factory=list)
    severity: ThreatLevel = ThreatLevel.MEDIUM
    confidence: float = 0.8
    source: str = "unknown"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if the indicator has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def matches(self, value: str, indicator_type: str) -> bool:
        """Check if this indicator matches the given value and type."""
        if self.is_expired():
            return False
        if self.indicator_type != indicator_type:
            return False
        
        # Exact match for most indicators
        if self.indicator_type in ["ip", "user_id", "session_id"]:
            return self.value == value
        
        # Pattern matching for user agents, URLs, etc.
        if self.indicator_type in ["user_agent", "url_pattern", "payload"]:
            try:
                return bool(re.search(self.value, value, re.IGNORECASE))
            except re.error:
                return self.value.lower() in value.lower()
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "indicator_type": self.indicator_type,
            "value": self.value,
            "threat_types": [t.value for t in self.threat_types],
            "severity": self.severity.value,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "is_expired": self.is_expired()
        }


@dataclass
class ThreatRule:
    """Defines a rule for detecting threats."""
    
    rule_id: str
    name: str
    description: str
    threat_type: ThreatType
    severity: ThreatLevel
    conditions: Dict[str, Any]  # Rule conditions and parameters
    enabled: bool = True
    confidence: float = 0.8
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate rule parameters."""
        if not self.rule_id:
            raise ThreatDetectionError("Rule ID cannot be empty")
        if not self.name:
            raise ThreatDetectionError("Rule name cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ThreatDetectionError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def evaluate(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """
        Evaluate the rule against event data.
        
        Args:
            event_data: Dictionary containing event information
            
        Returns:
            AnomalyScore if rule matches, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Delegate to specific rule type evaluators
            if self.threat_type == ThreatType.BRUTE_FORCE:
                return self._evaluate_brute_force(event_data)
            elif self.threat_type == ThreatType.RATE_LIMIT_VIOLATION:
                return self._evaluate_rate_limit(event_data)
            elif self.threat_type == ThreatType.GEOGRAPHIC_ANOMALY:
                return self._evaluate_geographic_anomaly(event_data)
            elif self.threat_type == ThreatType.TIME_ANOMALY:
                return self._evaluate_time_anomaly(event_data)
            elif self.threat_type == ThreatType.SUSPICIOUS_PATTERN:
                return self._evaluate_suspicious_pattern(event_data)
            elif self.threat_type == ThreatType.MALICIOUS_USER_AGENT:
                return self._evaluate_malicious_user_agent(event_data)
            else:
                return self._evaluate_generic(event_data)
                
        except Exception as e:
            # Log error but don't fail the evaluation
            return None
    
    def _evaluate_brute_force(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate brute force attack patterns."""
        failed_attempts = event_data.get("failed_attempts", 0)
        time_window = event_data.get("time_window_minutes", 5)
        threshold = self.conditions.get("max_attempts", 5)
        
        if failed_attempts >= threshold:
            # Calculate score based on how much the threshold was exceeded
            excess_ratio = (failed_attempts - threshold) / threshold
            score = min(0.5 + (excess_ratio * 0.5), 1.0)
            
            return AnomalyScore(
                score=score,
                confidence=self.confidence,
                factors={
                    "failed_attempts": failed_attempts,
                    "threshold": threshold,
                    "time_window": time_window,
                    "excess_ratio": excess_ratio
                }
            )
        
        return None
    
    def _evaluate_rate_limit(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate rate limiting violations."""
        requests_count = event_data.get("requests_count", 0)
        time_window = event_data.get("time_window_seconds", 60)
        threshold = self.conditions.get("max_requests", 100)
        
        if requests_count > threshold:
            excess_ratio = (requests_count - threshold) / threshold
            score = min(0.3 + (excess_ratio * 0.7), 1.0)
            
            return AnomalyScore(
                score=score,
                confidence=self.confidence,
                factors={
                    "requests_count": requests_count,
                    "threshold": threshold,
                    "time_window": time_window,
                    "excess_ratio": excess_ratio
                }
            )
        
        return None
    
    def _evaluate_geographic_anomaly(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate geographic anomalies (impossible travel)."""
        current_location = event_data.get("current_location")
        previous_location = event_data.get("previous_location")
        time_diff_hours = event_data.get("time_diff_hours", 0)
        
        if not current_location or not previous_location:
            return None
        
        # Calculate distance (simplified - in real implementation use proper geo calculations)
        distance_km = event_data.get("distance_km", 0)
        max_speed_kmh = self.conditions.get("max_travel_speed_kmh", 1000)  # Including flights
        
        if time_diff_hours > 0:
            required_speed = distance_km / time_diff_hours
            if required_speed > max_speed_kmh:
                # Impossible travel detected
                speed_ratio = required_speed / max_speed_kmh
                score = min(0.6 + (speed_ratio - 1) * 0.4, 1.0)
                
                return AnomalyScore(
                    score=score,
                    confidence=self.confidence,
                    factors={
                        "distance_km": distance_km,
                        "time_diff_hours": time_diff_hours,
                        "required_speed_kmh": required_speed,
                        "max_speed_kmh": max_speed_kmh,
                        "speed_ratio": speed_ratio
                    }
                )
        
        return None
    
    def _evaluate_time_anomaly(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate time-based anomalies."""
        current_hour = event_data.get("hour", datetime.now().hour)
        user_typical_hours = event_data.get("typical_hours", set(range(8, 18)))  # Default business hours
        
        if current_hour not in user_typical_hours:
            # Calculate how far outside normal hours
            if isinstance(user_typical_hours, (list, set)):
                typical_hours = set(user_typical_hours)
                min_hour = min(typical_hours)
                max_hour = max(typical_hours)
                
                if current_hour < min_hour:
                    hours_outside = min_hour - current_hour
                else:
                    hours_outside = current_hour - max_hour
                
                # Score based on how far outside normal hours
                score = min(0.2 + (hours_outside * 0.1), 0.8)
                
                return AnomalyScore(
                    score=score,
                    confidence=self.confidence * 0.6,  # Lower confidence for time anomalies
                    factors={
                        "current_hour": current_hour,
                        "typical_hours": list(typical_hours),
                        "hours_outside": hours_outside
                    }
                )
        
        return None
    
    def _evaluate_suspicious_pattern(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate suspicious patterns in requests."""
        patterns = self.conditions.get("patterns", [])
        request_data = event_data.get("request_data", {})
        
        matches = []
        for pattern_config in patterns:
            pattern = pattern_config.get("pattern", "")
            field = pattern_config.get("field", "url")
            weight = pattern_config.get("weight", 1.0)
            
            field_value = str(request_data.get(field, ""))
            
            try:
                if re.search(pattern, field_value, re.IGNORECASE):
                    matches.append({
                        "pattern": pattern,
                        "field": field,
                        "weight": weight,
                        "matched_value": field_value
                    })
            except re.error:
                continue
        
        if matches:
            # Calculate score based on matched patterns and their weights
            total_weight = sum(match["weight"] for match in matches)
            max_possible_weight = sum(p.get("weight", 1.0) for p in patterns)
            
            if max_possible_weight > 0:
                score = min(total_weight / max_possible_weight, 1.0)
                
                return AnomalyScore(
                    score=score,
                    confidence=self.confidence,
                    factors={
                        "matched_patterns": len(matches),
                        "total_patterns": len(patterns),
                        "total_weight": total_weight,
                        "matches": matches
                    }
                )
        
        return None
    
    def _evaluate_malicious_user_agent(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Evaluate malicious user agent patterns."""
        user_agent = event_data.get("user_agent", "")
        if not user_agent:
            return None
        
        malicious_patterns = self.conditions.get("malicious_patterns", [
            r"sqlmap",
            r"nikto",
            r"nmap",
            r"masscan",
            r"zap",
            r"burp",
            r"wget",
            r"curl.*bot",
            r"python-requests",
            r"<script",
            r"javascript:",
            r"vbscript:"
        ])
        
        matches = []
        for pattern in malicious_patterns:
            try:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    matches.append(pattern)
            except re.error:
                continue
        
        if matches:
            # Score based on number of matches
            score = min(0.4 + (len(matches) * 0.2), 1.0)
            
            return AnomalyScore(
                score=score,
                confidence=self.confidence,
                factors={
                    "user_agent": user_agent,
                    "matched_patterns": matches,
                    "pattern_count": len(matches)
                }
            )
        
        return None
    
    def _evaluate_generic(self, event_data: Dict[str, Any]) -> Optional[AnomalyScore]:
        """Generic rule evaluation for custom conditions."""
        # This can be extended for custom rule types
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "threat_type": self.threat_type.value,
            "severity": self.severity.value,
            "conditions": self.conditions,
            "enabled": self.enabled,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ThreatAssessment:
    """Represents a comprehensive threat assessment."""
    
    assessment_id: str
    user_id: Optional[str]
    source_ip: Optional[str]
    session_id: Optional[str]
    threat_level: ThreatLevel
    confidence: float
    detected_threats: List[ThreatType] = field(default_factory=list)
    anomaly_scores: List[AnomalyScore] = field(default_factory=list)
    triggered_rules: List[str] = field(default_factory=list)  # Rule IDs
    indicators: List[ThreatIndicator] = field(default_factory=list)
    recommended_actions: List[ActionType] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate assessment data."""
        if not self.assessment_id:
            raise ThreatDetectionError("Assessment ID cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ThreatDetectionError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def overall_anomaly_score(self) -> float:
        """Calculate overall anomaly score from all individual scores."""
        if not self.anomaly_scores:
            return 0.0
        
        # Use confidence-weighted average of scores
        total_weighted = sum(score.score * score.confidence for score in self.anomaly_scores)
        total_confidence = sum(score.confidence for score in self.anomaly_scores)
        
        if total_confidence == 0:
            return 0.0
        
        return min(total_weighted / total_confidence, 1.0)
    
    def is_high_risk(self) -> bool:
        """Check if this assessment indicates high risk."""
        return (
            self.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] or
            self.overall_anomaly_score() >= 0.8 or
            any(ActionType.BLOCK_IP in self.recommended_actions or 
                ActionType.BLOCK_USER in self.recommended_actions)
        )
    
    def add_anomaly_score(self, score: AnomalyScore):
        """Add an anomaly score to the assessment."""
        self.anomaly_scores.append(score)
        
        # Update threat level based on new score
        overall_score = self.overall_anomaly_score()
        if overall_score >= 0.9:
            self.threat_level = ThreatLevel.CRITICAL
        elif overall_score >= 0.7:
            self.threat_level = ThreatLevel.HIGH
        elif overall_score >= 0.4:
            self.threat_level = ThreatLevel.MEDIUM
        else:
            self.threat_level = ThreatLevel.LOW
    
    def add_threat_indicator(self, indicator: ThreatIndicator):
        """Add a threat indicator to the assessment."""
        self.indicators.append(indicator)
        
        # Add threat types from indicator
        for threat_type in indicator.threat_types:
            if threat_type not in self.detected_threats:
                self.detected_threats.append(threat_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "assessment_id": self.assessment_id,
            "user_id": self.user_id,
            "source_ip": self.source_ip,
            "session_id": self.session_id,
            "threat_level": self.threat_level.value,
            "confidence": self.confidence,
            "detected_threats": [t.value for t in self.detected_threats],
            "anomaly_scores": [score.to_dict() for score in self.anomaly_scores],
            "triggered_rules": self.triggered_rules,
            "indicators": [indicator.to_dict() for indicator in self.indicators],
            "recommended_actions": [action.value for action in self.recommended_actions],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "overall_anomaly_score": self.overall_anomaly_score(),
            "is_high_risk": self.is_high_risk()
        }


# =============================================================================
# ATTACK SIGNATURE DATABASE
# =============================================================================
class AttackSignatureDatabase:
    """Database of known attack patterns and signatures."""
    
    def __init__(self):
        self._signatures: Dict[str, ThreatIndicator] = {}
        self._patterns_by_type: Dict[ThreatType, List[ThreatIndicator]] = defaultdict(list)
        self._load_default_signatures()
    
    def _load_default_signatures(self):
        """Load default attack signatures."""
        
        # SQL Injection patterns
        sql_injection_patterns = [
            r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
            r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
            r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
            r"((\%27)|(\'))union",
            r"exec(\s|\+)+(s|x)p\w+",
            r"UNION.*SELECT",
            r"SELECT.*FROM.*WHERE",
            r"INSERT.*INTO.*VALUES",
            r"UPDATE.*SET.*WHERE",
            r"DELETE.*FROM.*WHERE"
        ]
        
        for i, pattern in enumerate(sql_injection_patterns):
            indicator = ThreatIndicator(
                indicator_type="payload",
                value=pattern,
                threat_types=[ThreatType.SQL_INJECTION],
                severity=ThreatLevel.HIGH,
                confidence=0.9,
                source="default_signatures",
                metadata={"pattern_id": f"sql_inj_{i}"}
            )
            self.add_signature(f"sql_injection_{i}", indicator)
        
        # XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"eval\s*\(",
            r"document\.cookie",
            r"document\.write"
        ]
        
        for i, pattern in enumerate(xss_patterns):
            indicator = ThreatIndicator(
                indicator_type="payload",
                value=pattern,
                threat_types=[ThreatType.XSS_ATTEMPT],
                severity=ThreatLevel.HIGH,
                confidence=0.85,
                source="default_signatures",
                metadata={"pattern_id": f"xss_{i}"}
            )
            self.add_signature(f"xss_{i}", indicator)
        
        # Directory traversal patterns
        traversal_patterns = [
            r"\.\.\/",
            r"\.\.\\",
            r"\/etc\/passwd",
            r"\/etc\/shadow",
            r"\/windows\/system32",
            r"\.\.%2F",
            r"\.\.%5C",
            r"%2e%2e%2f",
            r"%2e%2e%5c"
        ]
        
        for i, pattern in enumerate(traversal_patterns):
            indicator = ThreatIndicator(
                indicator_type="payload",
                value=pattern,
                threat_types=[ThreatType.DIRECTORY_TRAVERSAL],
                severity=ThreatLevel.HIGH,
                confidence=0.9,
                source="default_signatures",
                metadata={"pattern_id": f"traversal_{i}"}
            )
            self.add_signature(f"directory_traversal_{i}", indicator)
        
        # Malicious user agents
        malicious_user_agents = [
            ("sqlmap", ThreatLevel.CRITICAL),
            ("nikto", ThreatLevel.HIGH),
            ("nmap", ThreatLevel.HIGH),
            ("masscan", ThreatLevel.HIGH),
            ("zap", ThreatLevel.MEDIUM),
            ("burp", ThreatLevel.MEDIUM),
            ("wget", ThreatLevel.LOW),
            ("python-requests", ThreatLevel.LOW)
        ]
        
        for agent, severity in malicious_user_agents:
            indicator = ThreatIndicator(
                indicator_type="user_agent",
                value=agent,
                threat_types=[ThreatType.MALICIOUS_USER_AGENT],
                severity=severity,
                confidence=0.8,
                source="default_signatures",
                metadata={"tool_name": agent}
            )
            self.add_signature(f"user_agent_{agent}", indicator)
        
        # Known malicious IP ranges (examples - in production, use threat intelligence feeds)
        malicious_ips = [
            "10.0.0.0/8",  # Example - replace with actual threat intelligence
            "192.168.0.0/16",  # Example - replace with actual threat intelligence
        ]
        
        for i, ip_range in enumerate(malicious_ips):
            indicator = ThreatIndicator(
                indicator_type="ip",
                value=ip_range,
                threat_types=[ThreatType.SUSPICIOUS_IP],
                severity=ThreatLevel.MEDIUM,
                confidence=0.7,
                source="threat_intelligence",
                metadata={"ip_range": ip_range}
            )
            self.add_signature(f"malicious_ip_{i}", indicator)
    
    def add_signature(self, signature_id: str, indicator: ThreatIndicator):
        """Add a new attack signature."""
        self._signatures[signature_id] = indicator
        
        for threat_type in indicator.threat_types:
            self._patterns_by_type[threat_type].append(indicator)
    
    def remove_signature(self, signature_id: str):
        """Remove an attack signature."""
        if signature_id in self._signatures:
            indicator = self._signatures[signature_id]
            del self._signatures[signature_id]
            
            # Remove from type index
            for threat_type in indicator.threat_types:
                if indicator in self._patterns_by_type[threat_type]:
                    self._patterns_by_type[threat_type].remove(indicator)
    
    def get_signature(self, signature_id: str) -> Optional[ThreatIndicator]:
        """Get a specific signature by ID."""
        return self._signatures.get(signature_id)
    
    def get_signatures_by_type(self, threat_type: ThreatType) -> List[ThreatIndicator]:
        """Get all signatures for a specific threat type."""
        return self._patterns_by_type.get(threat_type, [])
    
    def match_indicators(self, data: Dict[str, Any]) -> List[Tuple[ThreatIndicator, str]]:
        """
        Match data against all indicators.
        
        Returns:
            List of (indicator, matched_value) tuples
        """
        matches = []
        
        for indicator in self._signatures.values():
            if indicator.is_expired():
                continue
            
            # Check different data fields based on indicator type
            if indicator.indicator_type == "ip":
                ip_value = data.get("source_ip", "")
                if ip_value and indicator.matches(ip_value, "ip"):
                    matches.append((indicator, ip_value))
            
            elif indicator.indicator_type == "user_agent":
                ua_value = data.get("user_agent", "")
                if ua_value and indicator.matches(ua_value, "user_agent"):
                    matches.append((indicator, ua_value))
            
            elif indicator.indicator_type == "payload":
                # Check various payload fields
                for field in ["url", "query_params", "body", "headers"]:
                    field_value = str(data.get(field, ""))
                    if field_value and indicator.matches(field_value, "payload"):
                        matches.append((indicator, field_value))
                        break  # Only match once per indicator
        
        return matches
    
    def get_all_signatures(self) -> Dict[str, ThreatIndicator]:
        """Get all signatures."""
        return self._signatures.copy()
    
    def load_from_file(self, file_path: Union[str, Path]):
        """Load signatures from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for sig_id, sig_data in data.items():
                indicator = ThreatIndicator(
                    indicator_type=sig_data["indicator_type"],
                    value=sig_data["value"],
                    threat_types=[ThreatType(t) for t in sig_data["threat_types"]],
                    severity=ThreatLevel(sig_data["severity"]),
                    confidence=sig_data["confidence"],
                    source=sig_data.get("source", "file"),
                    metadata=sig_data.get("metadata", {})
                )
                self.add_signature(sig_id, indicator)
                
        except Exception as e:
            raise ThreatDetectionError(f"Failed to load signatures from {file_path}: {e}")
    
    def save_to_file(self, file_path: Union[str, Path]):
        """Save signatures to a JSON file."""
        try:
            data = {}
            for sig_id, indicator in self._signatures.items():
                data[sig_id] = indicator.to_dict()
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            raise ThreatDetectionError(f"Failed to save signatures to {file_path}: {e}")


# =============================================================================
# USER BEHAVIOR MODELING
# =============================================================================

@dataclass
class UserBehaviorProfile:
    """Profile of normal user behavior patterns."""
    
    user_id: str
    typical_login_hours: Set[int] = field(default_factory=set)
    typical_locations: Set[str] = field(default_factory=set)  # Country codes or regions
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_endpoints: Dict[str, int] = field(default_factory=dict)  # endpoint -> frequency
    average_session_duration: float = 0.0  # minutes
    average_requests_per_session: float = 0.0
    last_seen: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_login_pattern(self, login_time: datetime):
        """Update typical login hours based on new login."""
        self.typical_login_hours.add(login_time.hour)
        self.last_seen = login_time
        self.updated_at = datetime.now(timezone.utc)
    
    def update_location_pattern(self, location: str):
        """Update typical locations."""
        self.typical_locations.add(location)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_user_agent_pattern(self, user_agent: str):
        """Update typical user agents."""
        # Store simplified user agent (browser + OS)
        simplified_ua = self._simplify_user_agent(user_agent)
        self.typical_user_agents.add(simplified_ua)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_endpoint_pattern(self, endpoint: str):
        """Update endpoint access patterns."""
        self.typical_endpoints[endpoint] = self.typical_endpoints.get(endpoint, 0) + 1
        self.updated_at = datetime.now(timezone.utc)
    
    def _simplify_user_agent(self, user_agent: str) -> str:
        """Simplify user agent to browser + OS."""
        # Simple extraction - in production, use a proper user agent parser
        ua_lower = user_agent.lower()
        
        browser = "unknown"
        if "chrome" in ua_lower:
            browser = "chrome"
        elif "firefox" in ua_lower:
            browser = "firefox"
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            browser = "safari"
        elif "edge" in ua_lower:
            browser = "edge"
        
        os_type = "unknown"
        if "windows" in ua_lower:
            os_type = "windows"
        elif "mac" in ua_lower or "darwin" in ua_lower:
            os_type = "macos"
        elif "linux" in ua_lower:
            os_type = "linux"
        elif "android" in ua_lower:
            os_type = "android"
        elif "ios" in ua_lower or "iphone" in ua_lower or "ipad" in ua_lower:
            os_type = "ios"
        
        return f"{browser}_{os_type}"
    
    def is_anomalous_login_time(self, login_time: datetime) -> bool:
        """Check if login time is anomalous for this user."""
        if not self.typical_login_hours:
            return False  # No pattern established yet
        
        return login_time.hour not in self.typical_login_hours
    
    def is_anomalous_location(self, location: str) -> bool:
        """Check if location is anomalous for this user."""
        if not self.typical_locations:
            return False  # No pattern established yet
        
        return location not in self.typical_locations
    
    def is_anomalous_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is anomalous for this user."""
        if not self.typical_user_agents:
            return False  # No pattern established yet
        
        simplified_ua = self._simplify_user_agent(user_agent)
        return simplified_ua not in self.typical_user_agents
    
    def calculate_endpoint_anomaly_score(self, endpoint: str) -> float:
        """Calculate anomaly score for endpoint access."""
        if not self.typical_endpoints:
            return 0.0  # No pattern established yet
        
        total_accesses = sum(self.typical_endpoints.values())
        endpoint_frequency = self.typical_endpoints.get(endpoint, 0)
        
        if endpoint_frequency == 0:
            # Never accessed this endpoint before
            return 0.6
        
        # Calculate relative frequency
        relative_frequency = endpoint_frequency / total_accesses
        
        # Lower frequency = higher anomaly score
        if relative_frequency < 0.01:  # Less than 1% of accesses
            return 0.4
        elif relative_frequency < 0.05:  # Less than 5% of accesses
            return 0.2
        else:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "typical_login_hours": list(self.typical_login_hours),
            "typical_locations": list(self.typical_locations),
            "typical_user_agents": list(self.typical_user_agents),
            "typical_endpoints": self.typical_endpoints,
            "average_session_duration": self.average_session_duration,
            "average_requests_per_session": self.average_requests_per_session,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns for anomaly detection."""
    
    def __init__(self, logger: Optional[SecurityLogger] = None):
        self._profiles: Dict[str, UserBehaviorProfile] = {}
        self._logger = logger
        self._learning_period_days = 7  # Days to establish baseline
        self._min_sessions_for_profile = 5  # Minimum sessions before anomaly detection
    
    def get_or_create_profile(self, user_id: str) -> UserBehaviorProfile:
        """Get existing profile or create new one."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserBehaviorProfile(user_id=user_id)
        return self._profiles[user_id]
    
    def update_profile(self, user_id: str, session_data: Dict[str, Any]):
        """Update user profile with new session data."""
        profile = self.get_or_create_profile(user_id)
        
        # Update various patterns
        if "login_time" in session_data:
            profile.update_login_pattern(session_data["login_time"])
        
        if "location" in session_data:
            profile.update_location_pattern(session_data["location"])
        
        if "user_agent" in session_data:
            profile.update_user_agent_pattern(session_data["user_agent"])
        
        if "endpoints" in session_data:
            for endpoint in session_data["endpoints"]:
                profile.update_endpoint_pattern(endpoint)
        
        # Update session metrics
        if "session_duration" in session_data:
            duration = session_data["session_duration"]
            if profile.average_session_duration == 0:
                profile.average_session_duration = duration
            else:
                # Exponential moving average
                profile.average_session_duration = (
                    0.8 * profile.average_session_duration + 0.2 * duration
                )
        
        if "requests_count" in session_data:
            count = session_data["requests_count"]
            if profile.average_requests_per_session == 0:
                profile.average_requests_per_session = count
            else:
                # Exponential moving average
                profile.average_requests_per_session = (
                    0.8 * profile.average_requests_per_session + 0.2 * count
                )
    
    def analyze_session_anomalies(self, user_id: str, session_data: Dict[str, Any]) -> List[AnomalyScore]:
        """Analyze session for behavioral anomalies."""
        profile = self.get_or_create_profile(user_id)
        anomalies = []
        
        # Check if we have enough data for analysis
        if not self._has_sufficient_data(profile):
            return anomalies
        
        # Time-based anomaly
        if "login_time" in session_data:
            login_time = session_data["login_time"]
            if profile.is_anomalous_login_time(login_time):
                anomalies.append(AnomalyScore(
                    score=0.4,
                    confidence=0.6,
                    factors={
                        "anomaly_type": "unusual_login_time",
                        "login_hour": login_time.hour,
                        "typical_hours": list(profile.typical_login_hours)
                    }
                ))
        
        # Location-based anomaly
        if "location" in session_data:
            location = session_data["location"]
            if profile.is_anomalous_location(location):
                anomalies.append(AnomalyScore(
                    score=0.6,
                    confidence=0.8,
                    factors={
                        "anomaly_type": "unusual_location",
                        "current_location": location,
                        "typical_locations": list(profile.typical_locations)
                    }
                ))
        
        # User agent anomaly
        if "user_agent" in session_data:
            user_agent = session_data["user_agent"]
            if profile.is_anomalous_user_agent(user_agent):
                anomalies.append(AnomalyScore(
                    score=0.5,
                    confidence=0.7,
                    factors={
                        "anomaly_type": "unusual_user_agent",
                        "current_user_agent": user_agent,
                        "typical_user_agents": list(profile.typical_user_agents)
                    }
                ))
        
        # Endpoint access anomaly
        if "endpoints" in session_data:
            endpoint_scores = []
            for endpoint in session_data["endpoints"]:
                score = profile.calculate_endpoint_anomaly_score(endpoint)
                if score > 0:
                    endpoint_scores.append((endpoint, score))
            
            if endpoint_scores:
                avg_score = sum(score for _, score in endpoint_scores) / len(endpoint_scores)
                anomalies.append(AnomalyScore(
                    score=avg_score,
                    confidence=0.6,
                    factors={
                        "anomaly_type": "unusual_endpoint_access",
                        "anomalous_endpoints": endpoint_scores
                    }
                ))
        
        return anomalies
    
    def _has_sufficient_data(self, profile: UserBehaviorProfile) -> bool:
        """Check if profile has sufficient data for anomaly detection."""
        # Check if profile is old enough and has enough activity
        age_days = (datetime.now(timezone.utc) - profile.created_at).days
        has_patterns = (
            len(profile.typical_login_hours) >= 2 or
            len(profile.typical_locations) >= 1 or
            len(profile.typical_user_agents) >= 1 or
            len(profile.typical_endpoints) >= self._min_sessions_for_profile
        )
        
        return age_days >= 1 and has_patterns  # At least 1 day old with some patterns
    
    def get_profile(self, user_id: str) -> Optional[UserBehaviorProfile]:
        """Get user profile if it exists."""
        return self._profiles.get(user_id)
    
    def get_all_profiles(self) -> Dict[str, UserBehaviorProfile]:
        """Get all user profiles."""
        return self._profiles.copy()
    
    def cleanup_old_profiles(self, days_inactive: int = 90):
        """Remove profiles for users inactive for specified days."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        
        inactive_users = [
            user_id for user_id, profile in self._profiles.items()
            if profile.last_seen and profile.last_seen < cutoff_date
        ]
        
        for user_id in inactive_users:
            del self._profiles[user_id]
        
        if self._logger and inactive_users:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.SYSTEM,
                severity=SecurityEventSeverity.LOW,
                message=f"Cleaned up {len(inactive_users)} inactive user profiles",
                details={"inactive_users": len(inactive_users), "days_inactive": days_inactive}
            ))


# =============================================================================
# RULE MANAGEMENT
# =============================================================================
class ThreatRuleEngine:
    """Engine for managing and evaluating threat detection rules."""
    
    def __init__(self, logger: Optional[SecurityLogger] = None):
        self._rules: Dict[str, ThreatRule] = {}
        self._rules_by_type: Dict[ThreatType, List[ThreatRule]] = defaultdict(list)
        self._logger = logger
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default threat detection rules."""
        
        # Brute force detection rule
        brute_force_rule = ThreatRule(
            rule_id="brute_force_login",
            name="Brute Force Login Detection",
            description="Detects multiple failed login attempts from same IP",
            threat_type=ThreatType.BRUTE_FORCE,
            severity=ThreatLevel.HIGH,
            conditions={
                "max_attempts": 5,
                "time_window_minutes": 5,
                "track_by": "source_ip"
            },
            confidence=0.9
        )
        self.add_rule(brute_force_rule)
        
        # Rate limiting rule
        rate_limit_rule = ThreatRule(
            rule_id="api_rate_limit",
            name="API Rate Limit Violation",
            description="Detects excessive API requests",
            threat_type=ThreatType.RATE_LIMIT_VIOLATION,
            severity=ThreatLevel.MEDIUM,
            conditions={
                "max_requests": 100,
                "time_window_seconds": 60,
                "track_by": "source_ip"
            },
            confidence=0.8
        )
        self.add_rule(rate_limit_rule)
        
        # Geographic anomaly rule
        geo_anomaly_rule = ThreatRule(
            rule_id="impossible_travel",
            name="Impossible Travel Detection",
            description="Detects geographically impossible travel patterns",
            threat_type=ThreatType.GEOGRAPHIC_ANOMALY,
            severity=ThreatLevel.HIGH,
            conditions={
                "max_travel_speed_kmh": 1000,  # Including commercial flights
                "min_time_diff_hours": 0.5
            },
            confidence=0.85
        )
        self.add_rule(geo_anomaly_rule)
        
        # Time anomaly rule
        time_anomaly_rule = ThreatRule(
            rule_id="unusual_access_time",
            name="Unusual Access Time",
            description="Detects access outside normal hours",
            threat_type=ThreatType.TIME_ANOMALY,
            severity=ThreatLevel.LOW,
            conditions={
                "business_hours_start": 8,
                "business_hours_end": 18,
                "weekend_access_suspicious": True
            },
            confidence=0.6
        )
        self.add_rule(time_anomaly_rule)
        
        # SQL injection detection rule
        sql_injection_rule = ThreatRule(
            rule_id="sql_injection_detection",
            name="SQL Injection Attack Detection",
            description="Detects SQL injection patterns in requests",
            threat_type=ThreatType.SUSPICIOUS_PATTERN,
            severity=ThreatLevel.CRITICAL,
            conditions={
                "patterns": [
                    {"pattern": r"(\%27)|(\')|(\-\-)|(\%23)|(#)", "field": "query_params", "weight": 1.0},
                    {"pattern": r"union.*select", "field": "query_params", "weight": 1.0},
                    {"pattern": r"exec(\s|\+)+(s|x)p\w+", "field": "query_params", "weight": 1.0}
                ]
            },
            confidence=0.95
        )
        self.add_rule(sql_injection_rule)
        
        # XSS detection rule
        xss_rule = ThreatRule(
            rule_id="xss_detection",
            name="Cross-Site Scripting Detection",
            description="Detects XSS attack patterns",
            threat_type=ThreatType.SUSPICIOUS_PATTERN,
            severity=ThreatLevel.HIGH,
            conditions={
                "patterns": [
                    {"pattern": r"<script[^>]*>", "field": "query_params", "weight": 1.0},
                    {"pattern": r"javascript:", "field": "query_params", "weight": 0.8},
                    {"pattern": r"onerror\s*=", "field": "query_params", "weight": 0.9}
                ]
            },
            confidence=0.9
        )
        self.add_rule(xss_rule)
        
        # Malicious user agent rule
        malicious_ua_rule = ThreatRule(
            rule_id="malicious_user_agent",
            name="Malicious User Agent Detection",
            description="Detects known malicious user agents",
            threat_type=ThreatType.MALICIOUS_USER_AGENT,
            severity=ThreatLevel.MEDIUM,
            conditions={
                "malicious_patterns": [
                    "sqlmap", "nikto", "nmap", "masscan", "zap", "burp"
                ]
            },
            confidence=0.85
        )
        self.add_rule(malicious_ua_rule)
    
    def add_rule(self, rule: ThreatRule):
        """Add a new threat detection rule."""
        if not isinstance(rule, ThreatRule):
            raise ThreatDetectionError("Invalid rule type")
        
        self._rules[rule.rule_id] = rule
        self._rules_by_type[rule.threat_type].append(rule)
        
        if self._logger:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.SYSTEM,
                severity=SecurityEventSeverity.LOW,
                message=f"Threat detection rule added: {rule.rule_id}",
                details={
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "threat_type": rule.threat_type.value,
                    "severity": rule.severity.value
                }
            ))
    
    def remove_rule(self, rule_id: str):
        """Remove a threat detection rule."""
        if rule_id in self._rules:
            rule = self._rules[rule_id]
            del self._rules[rule_id]
            
            # Remove from type index
            if rule in self._rules_by_type[rule.threat_type]:
                self._rules_by_type[rule.threat_type].remove(rule)
            
            if self._logger:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.SYSTEM,
                    severity=SecurityEventSeverity.LOW,
                    message=f"Threat detection rule removed: {rule_id}",
                    details={"rule_id": rule_id}
                ))
    
    def get_rule(self, rule_id: str) -> Optional[ThreatRule]:
        """Get a specific rule by ID."""
        return self._rules.get(rule_id)
    
    def get_rules_by_type(self, threat_type: ThreatType) -> List[ThreatRule]:
        """Get all rules for a specific threat type."""
        return self._rules_by_type.get(threat_type, [])
    
    def get_enabled_rules(self) -> List[ThreatRule]:
        """Get all enabled rules."""
        return [rule for rule in self._rules.values() if rule.enabled]
    
    def evaluate_rules(self, event_data: Dict[str, Any]) -> List[Tuple[ThreatRule, AnomalyScore]]:
        """
        Evaluate all enabled rules against event data.
        
        Returns:
            List of (rule, anomaly_score) tuples for rules that matched
        """
        matches = []
        
        for rule in self.get_enabled_rules():
            try:
                score = rule.evaluate(event_data)
                if score is not None:
                    matches.append((rule, score))
                    
                    if self._logger:
                        self._logger.log_event(SecurityEvent(
                            event_type=SecurityEventType.THREAT_DETECTION,
                            severity=SecurityEventSeverity.MEDIUM if rule.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] else SecurityEventSeverity.LOW,
                            message=f"Threat rule triggered: {rule.name}",
                            details={
                                "rule_id": rule.rule_id,
                                "rule_name": rule.name,
                                "threat_type": rule.threat_type.value,
                                "severity": rule.severity.value,
                                "anomaly_score": score.score,
                                "confidence": score.confidence,
                                "factors": score.factors
                            }
                        ))
            
            except Exception as e:
                if self._logger:
                    self._logger.log_event(SecurityEvent(
                        event_type=SecurityEventType.SYSTEM,
                        severity=SecurityEventSeverity.HIGH,
                        message=f"Error evaluating threat rule {rule.rule_id}: {e}",
                        details={
                            "rule_id": rule.rule_id,
                            "error": str(e)
                        }
                    ))
        
        return matches
    
    def enable_rule(self, rule_id: str):
        """Enable a specific rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            self._rules[rule_id].updated_at = datetime.now(timezone.utc)
    
    def disable_rule(self, rule_id: str):
        """Disable a specific rule."""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            self._rules[rule_id].updated_at = datetime.now(timezone.utc)
    
    def update_rule_conditions(self, rule_id: str, new_conditions: Dict[str, Any]):
        """Update rule conditions."""
        if rule_id in self._rules:
            self._rules[rule_id].conditions.update(new_conditions)
            self._rules[rule_id].updated_at = datetime.now(timezone.utc)
    
    def get_all_rules(self) -> Dict[str, ThreatRule]:
        """Get all rules."""
        return self._rules.copy()
    
    def load_rules_from_file(self, file_path: Union[str, Path]):
        """Load rules from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for rule_data in data:
                rule = ThreatRule(
                    rule_id=rule_data["rule_id"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    threat_type=ThreatType(rule_data["threat_type"]),
                    severity=ThreatLevel(rule_data["severity"]),
                    conditions=rule_data["conditions"],
                    enabled=rule_data.get("enabled", True),
                    confidence=rule_data.get("confidence", 0.8)
                )
                self.add_rule(rule)
                
        except Exception as e:
            raise ThreatDetectionError(f"Failed to load rules from {file_path}: {e}")
    
    def save_rules_to_file(self, file_path: Union[str, Path]):
        """Save rules to a JSON file."""
        try:
            data = [rule.to_dict() for rule in self._rules.values()]
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            raise ThreatDetectionError(f"Failed to save rules to {file_path}: {e}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_security_logger() -> SecurityLogger:
    """Get security logger instance."""
    # Import here to avoid circular imports
    from .logging import get_security_logger as _get_logger
    return _get_logger()


def calculate_ip_distance(location1: str, location2: str) -> float:
    """
    Calculate approximate distance between two locations (IPs or country codes).
    
    This is a simplified implementation. In production, use a proper
    geolocation service like MaxMind GeoIP2.
    
    Returns:
        Distance in kilometers (approximate)
    """
    # Country distance mapping (simplified)
    country_distances = {
        ("US", "CN"): 11000,  # US to China
        ("CN", "US"): 11000,  # China to US
        ("US", "UK"): 5500,   # US to UK
        ("UK", "US"): 5500,   # UK to US
        ("US", "CA"): 2000,   # US to Canada
        ("CA", "US"): 2000,   # Canada to US
        ("US", "MX"): 2000,   # US to Mexico
        ("MX", "US"): 2000,   # Mexico to US
    }
    
    try:
        # Check if they are country codes
        if len(location1) == 2 and len(location2) == 2:
            # Country code distance lookup
            distance = country_distances.get((location1, location2))
            if distance:
                return distance
            # If not in mapping, assume far distance for different countries
            return 8000.0 if location1 != location2 else 0.0
            
        # Try to parse as IP addresses
        ip1_int = int(ipaddress.IPv4Address(location1))
        ip2_int = int(ipaddress.IPv4Address(location2))
        
        # Very rough approximation - in reality, use proper geolocation
        ip_diff = abs(ip1_int - ip2_int)
        
        # Rough conversion to distance (this is not accurate!)
        # In production, use proper geolocation databases
        distance_km = min(ip_diff / 1000000, 20000)  # Cap at ~20,000 km
        
        return distance_km
        
    except Exception:
        # If parsing fails, assume maximum distance
        return 20000.0


def extract_location_from_ip(ip_address: str) -> str:
    """
    Extract location from IP address.
    
    This is a placeholder implementation. In production, use a proper
    geolocation service like MaxMind GeoIP2.
    
    Returns:
        Country code or region identifier
    """
    try:
        ip = ipaddress.IPv4Address(ip_address)
        
        # Very basic classification based on IP ranges
        # In production, use proper geolocation databases
        if ip.is_loopback:
            return "LOCALHOST"
        elif ip.is_private:
            return "PRIVATE"
        elif ip.is_multicast:
            return "MULTICAST"
        else:
            # Rough geographic classification (not accurate!)
            first_octet = int(str(ip).split('.')[0])
            if first_octet < 64:
                return "US"
            elif first_octet < 128:
                return "EU"
            elif first_octet < 192:
                return "ASIA"
            else:
                return "OTHER"
                
    except Exception:
        return "UNKNOWN"


def generate_assessment_id() -> str:
    """Generate a unique assessment ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = hashlib.md5(str(datetime.now().microsecond).encode()).hexdigest()[:8]
    return f"threat_assessment_{timestamp}_{random_suffix}"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Exceptions
    "ThreatDetectionError",
    
    # Enums
    "ThreatLevel",
    "ThreatType", 
    "ActionType",
    
    # Data Models
    "AnomalyScore",
    "ThreatIndicator",
    "ThreatRule",
    "ThreatAssessment",
    "UserBehaviorProfile",
    
    # Core Classes
    "AttackSignatureDatabase",
    "UserBehaviorAnalyzer",
    "ThreatRuleEngine",
    
    # Helper Functions
    "calculate_ip_distance",
    "extract_location_from_ip",
    "generate_assessment_id",
]


# =============================================================================
# THREAT DETECTOR ENGINE
# =============================================================================
class ThreatDetector:
    """
    Real-time threat detection engine with pattern analysis.
    
    Provides comprehensive threat detection capabilities including:
    - Brute force attack detection
    - Geographic anomaly detection (impossible travel)
    - Real-time event analysis
    - Configurable thresholds and rules
    """
    
    def __init__(
        self,
        behavior_analyzer: Optional[UserBehaviorAnalyzer] = None,
        rule_engine: Optional[ThreatRuleEngine] = None,
        signature_db: Optional[AttackSignatureDatabase] = None,
        logger: Optional[SecurityLogger] = None
    ):
        self.behavior_analyzer = behavior_analyzer or UserBehaviorAnalyzer()
        self.rule_engine = rule_engine or ThreatRuleEngine()
        self.signature_db = signature_db or AttackSignatureDatabase()
        self.logger = logger
        
        # Event tracking for pattern analysis
        self._login_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._location_history: Dict[str, List[Tuple[datetime, str]]] = defaultdict(list)
        self._session_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Configuration
        self._brute_force_threshold = 5  # Failed attempts
        self._brute_force_window = timedelta(minutes=15)  # Time window
        self._impossible_travel_speed = 1000  # km/h (commercial flight speed)
        self._cleanup_interval = timedelta(hours=24)  # Event cleanup
        
    def analyze_login_event(
        self,
        user_id: str,
        source_ip: str,
        success: bool,
        timestamp: Optional[datetime] = None,
        user_agent: Optional[str] = None,
        location: Optional[str] = None
    ) -> ThreatAssessment:
        """
        Analyze a login event for potential threats.
        
        Args:
            user_id: User identifier
            source_ip: Source IP address
            success: Whether login was successful
            timestamp: Event timestamp (defaults to now)
            user_agent: User agent string
            location: Geographic location
            
        Returns:
            ThreatAssessment with detected threats and risk level
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        # Create assessment
        assessment = ThreatAssessment(
            assessment_id=generate_assessment_id(),
            user_id=user_id,
            source_ip=source_ip,
            session_id=None,
            threat_level=ThreatLevel.LOW,
            confidence=0.5
        )
        
        # Track login attempt
        self._login_attempts[user_id].append(timestamp)
        if not success:
            self._failed_attempts[user_id].append(timestamp)
            
        # Perform threat analysis
        threats = []
        
        # 1. Brute force detection
        brute_force_score = self._detect_brute_force(user_id, timestamp)
        if brute_force_score > 0:
            threats.append(ThreatType.BRUTE_FORCE)
            assessment.add_anomaly_score(AnomalyScore(
                score=brute_force_score,
                confidence=0.9,
                factors={
                    "threat_type": "brute_force",
                    "failed_attempts": len(self._get_recent_failed_attempts(user_id, timestamp)),
                    "time_window": str(self._brute_force_window)
                }
            ))
            
        # 2. Geographic anomaly detection (before updating location history)
        if location:
            travel_score = self._detect_impossible_travel(user_id, location, timestamp)
            if travel_score > 0:
                threats.append(ThreatType.GEOGRAPHIC_ANOMALY)
                assessment.add_anomaly_score(AnomalyScore(
                    score=travel_score,
                    confidence=0.8,
                    factors={
                        "threat_type": "impossible_travel",
                        "current_location": location,
                        "previous_locations": [loc for _, loc in self._location_history[user_id][-3:]]
                    }
                ))
                
        # Track location if provided (after threat detection)
        if location:
            self._location_history[user_id].append((timestamp, location))
                
        # 3. IP-based threats
        ip_threats = self._analyze_ip_threats(source_ip)
        threats.extend(ip_threats)
        
        # 4. Behavioral analysis
        if user_agent or location:
            session_data = {
                "login_time": timestamp,
                "user_agent": user_agent,
                "location": location,
                "source_ip": source_ip
            }
            behavioral_anomalies = self.behavior_analyzer.analyze_session_anomalies(
                user_id, session_data
            )
            assessment.anomaly_scores.extend(behavioral_anomalies)
            
        # Update assessment based on findings
        assessment.detected_threats = threats
        if threats:
            assessment.threat_level = self._calculate_threat_level(assessment)
            assessment.confidence = min(assessment.overall_anomaly_score() + 0.3, 1.0)
            
        # Add recommended actions
        assessment.recommended_actions = self._recommend_actions(assessment)
        
        # Log security event
        if self.logger:
            self.logger.log_security_event(
                event_type="threat_analysis",
                user_id=user_id,
                source_ip=source_ip,
                details={
                    "threats_detected": [t.value for t in threats],
                    "threat_level": assessment.threat_level.value,
                    "confidence": assessment.confidence,
                    "anomaly_score": assessment.overall_anomaly_score()
                }
            )
            
        return assessment
        
    def analyze_session_event(
        self,
        user_id: str,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> ThreatAssessment:
        """
        Analyze a session event for potential threats.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            event_type: Type of event (e.g., 'api_call', 'data_access')
            event_data: Event-specific data
            timestamp: Event timestamp
            
        Returns:
            ThreatAssessment with detected threats
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        # Track session event
        event_record = {
            "timestamp": timestamp,
            "event_type": event_type,
            "data": event_data
        }
        self._session_events[session_id].append(event_record)
        
        # Create assessment
        assessment = ThreatAssessment(
            assessment_id=generate_assessment_id(),
            user_id=user_id,
            source_ip=event_data.get("source_ip"),
            session_id=session_id,
            threat_level=ThreatLevel.LOW,
            confidence=0.5
        )
        
        # Analyze session patterns
        threats = []
        
        # 1. Rapid successive requests (potential automation)
        if self._detect_rapid_requests(session_id, timestamp):
            threats.append(ThreatType.RATE_LIMIT_VIOLATION)
            assessment.add_anomaly_score(AnomalyScore(
                score=0.7,
                confidence=0.8,
                factors={
                    "threat_type": "rapid_requests",
                    "session_id": session_id
                }
            ))
            
        # 2. Privilege escalation attempts
        if self._detect_privilege_escalation(session_id, event_data):
            threats.append(ThreatType.PRIVILEGE_ESCALATION)
            assessment.add_anomaly_score(AnomalyScore(
                score=0.9,
                confidence=0.9,
                factors={
                    "threat_type": "privilege_escalation",
                    "event_type": event_type,
                    "attempted_resource": event_data.get("resource")
                }
            ))
            
        # 3. Data exfiltration patterns
        if self._detect_data_exfiltration(session_id, event_data):
            threats.append(ThreatType.DATA_EXFILTRATION)
            assessment.add_anomaly_score(AnomalyScore(
                score=0.8,
                confidence=0.7,
                factors={
                    "threat_type": "data_exfiltration",
                    "data_volume": event_data.get("data_size", 0)
                }
            ))
            
        # Update assessment
        assessment.detected_threats = threats
        if threats:
            assessment.threat_level = self._calculate_threat_level(assessment)
            assessment.confidence = min(assessment.overall_anomaly_score() + 0.2, 1.0)
            
        assessment.recommended_actions = self._recommend_actions(assessment)
        
        return assessment
        
    def _detect_brute_force(self, user_id: str, timestamp: datetime) -> float:
        """Detect brute force attacks based on failed login attempts."""
        recent_failures = self._get_recent_failed_attempts(user_id, timestamp)
        
        if len(recent_failures) >= self._brute_force_threshold:
            # Calculate score based on frequency and recency
            time_span = (timestamp - recent_failures[0]).total_seconds()
            frequency_score = min(len(recent_failures) / (self._brute_force_threshold * 2), 1.0)
            recency_score = max(0, 1.0 - (time_span / self._brute_force_window.total_seconds()))
            
            return min(frequency_score + recency_score, 1.0)
            
        return 0.0
        
    def _detect_impossible_travel(
        self,
        user_id: str,
        current_location: str,
        timestamp: datetime
    ) -> float:
        """Detect impossible travel scenarios."""
        if user_id not in self._location_history:
            return 0.0
            
        recent_locations = [
            (ts, loc) for ts, loc in self._location_history[user_id]
            if (timestamp - ts).total_seconds() <= 86400  # Last 24 hours
        ]
        
        if not recent_locations:
            return 0.0
            
        # Check against most recent location
        last_timestamp, last_location = recent_locations[-1]
        
        if last_location == current_location:
            return 0.0
            
        # Calculate required travel speed
        time_diff = (timestamp - last_timestamp).total_seconds() / 3600  # hours
        if time_diff <= 0:
            return 1.0  # Same time, different location = impossible
            
        # Estimate distance (simplified - in production use proper geolocation)
        distance = calculate_ip_distance(last_location, current_location)
        required_speed = distance / time_diff
        
        if required_speed > self._impossible_travel_speed:
            # Score based on how impossible the travel is
            impossibility_factor = min(required_speed / self._impossible_travel_speed, 5.0)
            return min(0.3 + (impossibility_factor * 0.2), 1.0)
            
        return 0.0
        
    def _analyze_ip_threats(self, source_ip: str) -> List[ThreatType]:
        """Analyze IP-based threats."""
        threats = []
        
        # Check against known threat indicators
        all_signatures = self.signature_db.get_all_signatures()
        for signature_id, indicator in all_signatures.items():
            if indicator.indicator_type == "ip" and indicator.value == source_ip:
                threats.extend(indicator.threat_types)
                
        # Check IP reputation (simplified)
        location = extract_location_from_ip(source_ip)
        if location in ["TOR", "VPN", "PROXY"]:
            threats.append(ThreatType.SUSPICIOUS_IP)
            
        return threats
        
    def _detect_rapid_requests(self, session_id: str, timestamp: datetime) -> bool:
        """Detect rapid successive requests indicating automation."""
        if session_id not in self._session_events:
            return False
            
        recent_events = [
            event for event in self._session_events[session_id]
            if (timestamp - event["timestamp"]).total_seconds() <= 60  # Last minute
        ]
        
        # More than 30 requests per minute indicates automation
        return len(recent_events) > 30
        
    def _detect_privilege_escalation(self, session_id: str, event_data: Dict[str, Any]) -> bool:
        """Detect privilege escalation attempts."""
        # Check for admin endpoint access without proper role
        resource = event_data.get("resource", "")
        user_roles = event_data.get("user_roles", [])
        
        admin_patterns = ["/admin", "/api/admin", "/management", "/config"]
        is_admin_resource = any(pattern in resource for pattern in admin_patterns)
        has_admin_role = any("admin" in role.lower() for role in user_roles)
        
        return is_admin_resource and not has_admin_role
        
    def _detect_data_exfiltration(self, session_id: str, event_data: Dict[str, Any]) -> bool:
        """Detect potential data exfiltration patterns."""
        # Check for large data downloads
        data_size = event_data.get("data_size", 0)
        if data_size > 10 * 1024 * 1024:  # 10MB threshold
            return True
            
        # Check for bulk data access patterns
        if session_id in self._session_events:
            recent_data_events = [
                event for event in self._session_events[session_id]
                if event["event_type"] == "data_access" and
                (datetime.now(timezone.utc) - event["timestamp"]).total_seconds() <= 300  # 5 minutes
            ]
            
            # More than 50 data access events in 5 minutes
            if len(recent_data_events) > 50:
                return True
                
        return False
        
    def _get_recent_failed_attempts(self, user_id: str, timestamp: datetime) -> List[datetime]:
        """Get recent failed login attempts within the time window."""
        if user_id not in self._failed_attempts:
            return []
            
        cutoff_time = timestamp - self._brute_force_window
        return [
            attempt for attempt in self._failed_attempts[user_id]
            if attempt >= cutoff_time
        ]
        
    def _calculate_threat_level(self, assessment: ThreatAssessment) -> ThreatLevel:
        """Calculate overall threat level based on detected threats and scores."""
        if not assessment.detected_threats and assessment.overall_anomaly_score() < 0.3:
            return ThreatLevel.LOW
            
        critical_threats = {
            ThreatType.PRIVILEGE_ESCALATION,
            ThreatType.DATA_EXFILTRATION,
            ThreatType.ACCOUNT_TAKEOVER
        }
        
        high_threats = {
            ThreatType.BRUTE_FORCE,
            ThreatType.CREDENTIAL_STUFFING,
            ThreatType.SUSPICIOUS_IP,
            ThreatType.SQL_INJECTION,
            ThreatType.XSS_ATTEMPT
        }
        
        if any(threat in critical_threats for threat in assessment.detected_threats):
            return ThreatLevel.CRITICAL
        elif any(threat in high_threats for threat in assessment.detected_threats):
            return ThreatLevel.HIGH
        elif assessment.overall_anomaly_score() > 0.7:
            return ThreatLevel.HIGH
        elif assessment.overall_anomaly_score() > 0.4:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW
            
    def _recommend_actions(self, assessment: ThreatAssessment) -> List[ActionType]:
        """Recommend actions based on threat assessment."""
        actions = []
        
        if assessment.threat_level == ThreatLevel.CRITICAL:
            actions.extend([ActionType.BLOCK_IP, ActionType.BLOCK_USER, ActionType.ALERT, ActionType.ESCALATE])
        elif assessment.threat_level == ThreatLevel.HIGH:
            actions.extend([ActionType.ALERT, ActionType.REQUIRE_MFA])
            if ThreatType.BRUTE_FORCE in assessment.detected_threats:
                actions.append(ActionType.BLOCK_IP)
        elif assessment.threat_level == ThreatLevel.MEDIUM:
            actions.extend([ActionType.LOG_ONLY, ActionType.RATE_LIMIT])
        else:
            actions.append(ActionType.LOG_ONLY)
            
        return actions
        
    def configure_brute_force_detection(
        self,
        threshold: int,
        time_window: timedelta
    ):
        """Configure brute force detection parameters."""
        self._brute_force_threshold = threshold
        self._brute_force_window = time_window
        
    def configure_travel_detection(self, max_speed_kmh: float):
        """Configure impossible travel detection parameters."""
        self._impossible_travel_speed = max_speed_kmh
        
    def cleanup_old_events(self, cutoff_time: Optional[datetime] = None):
        """Clean up old events to prevent memory bloat."""
        if cutoff_time is None:
            cutoff_time = datetime.now(timezone.utc) - self._cleanup_interval
            
        # Clean login attempts
        for user_id in list(self._login_attempts.keys()):
            self._login_attempts[user_id] = [
                attempt for attempt in self._login_attempts[user_id]
                if attempt >= cutoff_time
            ]
            if not self._login_attempts[user_id]:
                del self._login_attempts[user_id]
                
        # Clean failed attempts
        for user_id in list(self._failed_attempts.keys()):
            self._failed_attempts[user_id] = [
                attempt for attempt in self._failed_attempts[user_id]
                if attempt >= cutoff_time
            ]
            if not self._failed_attempts[user_id]:
                del self._failed_attempts[user_id]
                
        # Clean location history
        for user_id in list(self._location_history.keys()):
            self._location_history[user_id] = [
                (ts, loc) for ts, loc in self._location_history[user_id]
                if ts >= cutoff_time
            ]
            if not self._location_history[user_id]:
                del self._location_history[user_id]
                
        # Clean session events
        for session_id in list(self._session_events.keys()):
            self._session_events[session_id] = [
                event for event in self._session_events[session_id]
                if event["timestamp"] >= cutoff_time
            ]
            if not self._session_events[session_id]:
                del self._session_events[session_id]
                
    def get_statistics(self) -> Dict[str, Any]:
        """Get threat detection statistics."""
        return {
            "tracked_users": len(self._login_attempts),
            "active_sessions": len(self._session_events),
            "total_login_attempts": sum(len(attempts) for attempts in self._login_attempts.values()),
            "total_failed_attempts": sum(len(attempts) for attempts in self._failed_attempts.values()),
            "users_with_location_history": len(self._location_history),
            "configuration": {
                "brute_force_threshold": self._brute_force_threshold,
                "brute_force_window_minutes": self._brute_force_window.total_seconds() / 60,
                "max_travel_speed_kmh": self._impossible_travel_speed
            }
        }


# Update exports
__all__.extend([
    "ThreatDetector",
    "AlertSeverity", "AlertStatus", "ResponseAction",
    "ThreatAlert", "ResponseRule", "ThreatResponse", "IntegratedThreatSystem"
])
# ============================================================================
# THREAT RESPONSE AND ALERTING SYSTEM
# ============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status values."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ResponseAction(str, Enum):
    """Available response actions."""
    LOG_ONLY = "log_only"
    ALERT = "alert"
    BLOCK_IP = "block_ip"
    BLOCK_USER = "block_user"
    REQUIRE_MFA = "require_mfa"
    RATE_LIMIT = "rate_limit"
    QUARANTINE = "quarantine"
    ESCALATE = "escalate"


@dataclass
class ThreatAlert:
    """Represents a security threat alert."""
    alert_id: str
    threat_assessment: ThreatAssessment
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    escalated: bool = False
    escalation_count: int = 0
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def acknowledge(self, user_id: str, note: Optional[str] = None):
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now(timezone.utc)
        self.updated_at = self.acknowledged_at
        if note:
            self.notes.append(f"[{user_id}] {note}")
    
    def resolve(self, note: Optional[str] = None):
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.updated_at = self.resolved_at
        if note:
            self.notes.append(f"Resolved: {note}")
    
    def escalate(self, reason: str):
        """Escalate the alert."""
        self.escalated = True
        self.escalation_count += 1
        self.updated_at = datetime.now(timezone.utc)
        self.notes.append(f"Escalated (#{self.escalation_count}): {reason}")


@dataclass
class ResponseRule:
    """Defines automated response rules for threats."""
    rule_id: str
    name: str
    description: str
    threat_types: Set[ThreatType]
    min_threat_level: ThreatLevel
    min_confidence: float
    actions: List[ResponseAction]
    enabled: bool = True
    cooldown_period: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    max_executions_per_hour: int = 10
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, assessment: ThreatAssessment) -> bool:
        """Check if this rule matches the threat assessment."""
        if not self.enabled:
            return False
            
        # Check threat types
        if self.threat_types and not any(threat in assessment.detected_threats for threat in self.threat_types):
            return False
            
        # Check threat level
        if assessment.threat_level.value < self.min_threat_level.value:
            return False
            
        # Check confidence
        if assessment.confidence < self.min_confidence:
            return False
            
        # Check additional conditions
        for condition, value in self.conditions.items():
            if condition == "source_ip_pattern":
                if not re.match(value, assessment.source_ip or ""):
                    return False
            elif condition == "user_id_pattern":
                if not re.match(value, assessment.user_id):
                    return False
                    
        return True


class ThreatResponse:
    """
    Automated threat response system.
    
    Provides automated countermeasures and alerting for detected threats.
    """
    
    def __init__(
        self,
        logger: Optional[SecurityLogger] = None,
        alert_retention_days: int = 30,
        max_alerts_per_hour: int = 100
    ):
        self.logger = logger
        self.alert_retention_days = alert_retention_days
        self.max_alerts_per_hour = max_alerts_per_hour
        
        # Storage
        self._alerts: Dict[str, ThreatAlert] = {}
        self._response_rules: Dict[str, ResponseRule] = {}
        self._blocked_ips: Set[str] = set()
        self._blocked_users: Set[str] = set()
        self._quarantined_sessions: Set[str] = set()
        self._rate_limited_ips: Dict[str, datetime] = {}
        self._rate_limited_users: Dict[str, datetime] = {}
        
        # Execution tracking
        self._rule_executions: Dict[str, List[datetime]] = defaultdict(list)
        self._alert_counts: List[datetime] = []
        
        # Callbacks for external integrations
        self._alert_callbacks: List[Callable[[ThreatAlert], None]] = []
        self._action_callbacks: Dict[ResponseAction, List[Callable[[ThreatAssessment, Dict[str, Any]], None]]] = defaultdict(list)
        
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default response rules."""
        # Critical threat rule
        self.add_response_rule(ResponseRule(
            rule_id="critical_threats",
            name="Critical Threat Response",
            description="Immediate response to critical threats",
            threat_types={ThreatType.BRUTE_FORCE, ThreatType.PRIVILEGE_ESCALATION},
            min_threat_level=ThreatLevel.CRITICAL,
            min_confidence=0.8,
            actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT, ResponseAction.ESCALATE]
        ))
        
        # High threat rule
        self.add_response_rule(ResponseRule(
            rule_id="high_threats",
            name="High Threat Response",
            description="Response to high-confidence threats",
            threat_types=set(),  # Any threat type
            min_threat_level=ThreatLevel.HIGH,
            min_confidence=0.7,
            actions=[ResponseAction.ALERT, ResponseAction.REQUIRE_MFA, ResponseAction.RATE_LIMIT]
        ))
        
        # Geographic anomaly rule
        self.add_response_rule(ResponseRule(
            rule_id="geographic_anomaly",
            name="Geographic Anomaly Response",
            description="Response to impossible travel detection",
            threat_types={ThreatType.GEOGRAPHIC_ANOMALY},
            min_threat_level=ThreatLevel.MEDIUM,
            min_confidence=0.6,
            actions=[ResponseAction.ALERT, ResponseAction.REQUIRE_MFA]
        ))
    
    def add_response_rule(self, rule: ResponseRule):
        """Add a response rule."""
        self._response_rules[rule.rule_id] = rule
        if self.logger:
            self.logger.log_security_event(SecurityEvent(
                event_type=SecurityEventType.CONFIGURATION_CHANGE,
                severity=SecurityEventSeverity.INFO,
                message=f"Response rule added: {rule.name}",
                metadata={"rule_id": rule.rule_id, "actions": [a.value for a in rule.actions]}
            ))
    
    def remove_response_rule(self, rule_id: str):
        """Remove a response rule."""
        if rule_id in self._response_rules:
            rule = self._response_rules.pop(rule_id)
            if self.logger:
                self.logger.log_security_event(SecurityEvent(
                    event_type=SecurityEventType.CONFIGURATION_CHANGE,
                    severity=SecurityEventSeverity.INFO,
                    message=f"Response rule removed: {rule.name}",
                    metadata={"rule_id": rule_id}
                ))
    
    def register_alert_callback(self, callback: Callable[[ThreatAlert], None]):
        """Register a callback for alert notifications."""
        self._alert_callbacks.append(callback)
    
    def register_action_callback(self, action: ResponseAction, callback: Callable[[ThreatAssessment, Dict[str, Any]], None]):
        """Register a callback for specific response actions."""
        self._action_callbacks[action].append(callback)
    
    async def process_threat_assessment(self, assessment: ThreatAssessment) -> List[ThreatAlert]:
        """
        Process a threat assessment and execute appropriate responses.
        
        Args:
            assessment: The threat assessment to process
            
        Returns:
            List of alerts generated
        """
        alerts = []
        
        # Check if we should generate an alert
        if self._should_generate_alert(assessment):
            alert = await self._generate_alert(assessment)
            alerts.append(alert)
        
        # Execute matching response rules
        for rule in self._response_rules.values():
            if rule.matches(assessment) and self._can_execute_rule(rule):
                await self._execute_response_rule(rule, assessment)
        
        return alerts
    
    def _should_generate_alert(self, assessment: ThreatAssessment) -> bool:
        """Determine if an alert should be generated."""
        # Check alert rate limiting
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        self._alert_counts = [ts for ts in self._alert_counts if ts >= hour_ago]
        
        if len(self._alert_counts) >= self.max_alerts_per_hour:
            return False
        
        # Generate alert for medium+ threats with reasonable confidence
        return (
            assessment.threat_level in [ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL] and
            assessment.confidence >= 0.5
        )
    
    async def _generate_alert(self, assessment: ThreatAssessment) -> ThreatAlert:
        """Generate a threat alert."""
        alert_id = f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(assessment.assessment_id.encode()).hexdigest()[:8]}"
        
        # Determine severity based on threat level and confidence
        if assessment.threat_level == ThreatLevel.CRITICAL or assessment.confidence >= 0.9:
            severity = AlertSeverity.CRITICAL
        elif assessment.threat_level == ThreatLevel.HIGH or assessment.confidence >= 0.8:
            severity = AlertSeverity.HIGH
        elif assessment.threat_level == ThreatLevel.MEDIUM or assessment.confidence >= 0.6:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW
        
        alert = ThreatAlert(
            alert_id=alert_id,
            threat_assessment=assessment,
            severity=severity,
            metadata={
                "threat_types": [t.value for t in assessment.detected_threats],
                "anomaly_scores": len(assessment.anomaly_scores),
                "recommended_actions": [a.value for a in assessment.recommended_actions]
            }
        )
        
        self._alerts[alert_id] = alert
        self._alert_counts.append(alert.created_at)
        
        # Log the alert
        if self.logger:
            self.logger.log_security_event(SecurityEvent(
                event_type=SecurityEventType.THREAT_DETECTED,
                severity=SecurityEventSeverity.HIGH if severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] else SecurityEventSeverity.MEDIUM,
                message=f"Threat alert generated: {severity.value}",
                user_id=assessment.user_id,
                source_ip=assessment.source_ip,
                metadata={
                    "alert_id": alert_id,
                    "threat_level": assessment.threat_level.value,
                    "confidence": assessment.confidence,
                    "threats": [t.value for t in assessment.detected_threats]
                }
            ))
        
        # Notify callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                if self.logger:
                    self.logger.log_security_event(SecurityEvent(
                        event_type=SecurityEventType.SYSTEM_ERROR,
                        severity=SecurityEventSeverity.ERROR,
                        message=f"Alert callback failed: {str(e)}",
                        metadata={"alert_id": alert_id, "error": str(e)}
                    ))
        
        return alert
    
    def _can_execute_rule(self, rule: ResponseRule) -> bool:
        """Check if a rule can be executed (rate limiting)."""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        # Clean old executions
        self._rule_executions[rule.rule_id] = [
            ts for ts in self._rule_executions[rule.rule_id] if ts >= hour_ago
        ]
        
        # Check execution limit
        if len(self._rule_executions[rule.rule_id]) >= rule.max_executions_per_hour:
            return False
        
        # Check cooldown
        if self._rule_executions[rule.rule_id]:
            last_execution = max(self._rule_executions[rule.rule_id])
            if now - last_execution < rule.cooldown_period:
                return False
        
        return True
    
    async def _execute_response_rule(self, rule: ResponseRule, assessment: ThreatAssessment):
        """Execute a response rule."""
        now = datetime.now(timezone.utc)
        self._rule_executions[rule.rule_id].append(now)
        
        if self.logger:
            self.logger.log_security_event(SecurityEvent(
                event_type=SecurityEventType.THREAT_RESPONSE,
                severity=SecurityEventSeverity.INFO,
                message=f"Executing response rule: {rule.name}",
                user_id=assessment.user_id,
                source_ip=assessment.source_ip,
                metadata={
                    "rule_id": rule.rule_id,
                    "actions": [a.value for a in rule.actions],
                    "threat_level": assessment.threat_level.value
                }
            ))
        
        # Execute each action
        for action in rule.actions:
            await self._execute_action(action, assessment, {"rule_id": rule.rule_id})
    
    async def _execute_action(self, action: ResponseAction, assessment: ThreatAssessment, context: Dict[str, Any]):
        """Execute a specific response action."""
        try:
            if action == ResponseAction.BLOCK_IP and assessment.source_ip:
                self._blocked_ips.add(assessment.source_ip)
                
            elif action == ResponseAction.BLOCK_USER:
                self._blocked_users.add(assessment.user_id)
                
            elif action == ResponseAction.QUARANTINE and assessment.session_id:
                self._quarantined_sessions.add(assessment.session_id)
                
            elif action == ResponseAction.RATE_LIMIT:
                if assessment.source_ip:
                    self._rate_limited_ips[assessment.source_ip] = datetime.now(timezone.utc) + timedelta(hours=1)
                self._rate_limited_users[assessment.user_id] = datetime.now(timezone.utc) + timedelta(hours=1)
            
            # Execute callbacks
            for callback in self._action_callbacks[action]:
                try:
                    callback(assessment, context)
                except Exception as e:
                    if self.logger:
                        self.logger.log_security_event(SecurityEvent(
                            event_type=SecurityEventType.SYSTEM_ERROR,
                            severity=SecurityEventSeverity.ERROR,
                            message=f"Action callback failed: {str(e)}",
                            metadata={"action": action.value, "error": str(e)}
                        ))
            
            if self.logger:
                self.logger.log_security_event(SecurityEvent(
                    event_type=SecurityEventType.THREAT_RESPONSE,
                    severity=SecurityEventSeverity.INFO,
                    message=f"Response action executed: {action.value}",
                    user_id=assessment.user_id,
                    source_ip=assessment.source_ip,
                    metadata={"action": action.value, "context": context}
                ))
                
        except Exception as e:
            if self.logger:
                self.logger.log_security_event(SecurityEvent(
                    event_type=SecurityEventType.SYSTEM_ERROR,
                    severity=SecurityEventSeverity.ERROR,
                    message=f"Failed to execute action {action.value}: {str(e)}",
                    user_id=assessment.user_id,
                    source_ip=assessment.source_ip,
                    metadata={"action": action.value, "error": str(e)}
                ))
    
    # Query methods
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked."""
        return ip in self._blocked_ips
    
    def is_user_blocked(self, user_id: str) -> bool:
        """Check if a user is blocked."""
        return user_id in self._blocked_users
    
    def is_session_quarantined(self, session_id: str) -> bool:
        """Check if a session is quarantined."""
        return session_id in self._quarantined_sessions
    
    def is_ip_rate_limited(self, ip: str) -> bool:
        """Check if an IP is rate limited."""
        if ip not in self._rate_limited_ips:
            return False
        if datetime.now(timezone.utc) > self._rate_limited_ips[ip]:
            del self._rate_limited_ips[ip]
            return False
        return True
    
    def is_user_rate_limited(self, user_id: str) -> bool:
        """Check if a user is rate limited."""
        if user_id not in self._rate_limited_users:
            return False
        if datetime.now(timezone.utc) > self._rate_limited_users[user_id]:
            del self._rate_limited_users[user_id]
            return False
        return True
    
    def get_alert(self, alert_id: str) -> Optional[ThreatAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)
    
    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: int = 100
    ) -> List[ThreatAlert]:
        """Get alerts with optional filtering."""
        alerts = list(self._alerts.values())
        
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by creation time (newest first)
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        
        return alerts[:limit]
    
    def cleanup_old_data(self, cutoff_time: Optional[datetime] = None):
        """Clean up old alerts and tracking data."""
        if cutoff_time is None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.alert_retention_days)
        
        # Clean old alerts
        old_alert_ids = [
            alert_id for alert_id, alert in self._alerts.items()
            if alert.created_at < cutoff_time and alert.status in [AlertStatus.RESOLVED, AlertStatus.CLOSED]
        ]
        for alert_id in old_alert_ids:
            del self._alerts[alert_id]
        
        # Clean old rate limits
        now = datetime.now(timezone.utc)
        expired_ips = [ip for ip, expiry in self._rate_limited_ips.items() if now > expiry]
        for ip in expired_ips:
            del self._rate_limited_ips[ip]
            
        expired_users = [user for user, expiry in self._rate_limited_users.items() if now > expiry]
        for user in expired_users:
            del self._rate_limited_users[user]
        
        # Clean old execution tracking
        hour_ago = now - timedelta(hours=1)
        for rule_id in self._rule_executions:
            self._rule_executions[rule_id] = [
                ts for ts in self._rule_executions[rule_id] if ts >= hour_ago
            ]
        
        self._alert_counts = [ts for ts in self._alert_counts if ts >= hour_ago]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get response system statistics."""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        recent_alerts = [a for a in self._alerts.values() if a.created_at >= hour_ago]
        daily_alerts = [a for a in self._alerts.values() if a.created_at >= day_ago]
        
        return {
            "alerts": {
                "total": len(self._alerts),
                "last_hour": len(recent_alerts),
                "last_24h": len(daily_alerts),
                "by_status": {
                    status.value: len([a for a in self._alerts.values() if a.status == status])
                    for status in AlertStatus
                },
                "by_severity": {
                    severity.value: len([a for a in self._alerts.values() if a.severity == severity])
                    for severity in AlertSeverity
                }
            },
            "blocks": {
                "blocked_ips": len(self._blocked_ips),
                "blocked_users": len(self._blocked_users),
                "quarantined_sessions": len(self._quarantined_sessions),
                "rate_limited_ips": len(self._rate_limited_ips),
                "rate_limited_users": len(self._rate_limited_users)
            },
            "rules": {
                "total_rules": len(self._response_rules),
                "enabled_rules": len([r for r in self._response_rules.values() if r.enabled]),
                "executions_last_hour": sum(
                    len([ts for ts in executions if ts >= hour_ago])
                    for executions in self._rule_executions.values()
                )
            }
        }


# ============================================================================
# INTEGRATED THREAT DETECTION AND RESPONSE SYSTEM
# ============================================================================

class IntegratedThreatSystem:
    """
    Integrated threat detection and response system.
    
    Combines threat detection with automated response capabilities.
    """
    
    def __init__(
        self,
        detector: Optional[ThreatDetector] = None,
        response: Optional[ThreatResponse] = None,
        logger: Optional[SecurityLogger] = None
    ):
        self.detector = detector or ThreatDetector(logger=logger)
        self.response = response or ThreatResponse(logger=logger)
        self.logger = logger
        
        # Statistics
        self._processed_events = 0
        self._generated_alerts = 0
        self._executed_responses = 0
    
    async def analyze_and_respond(
        self,
        user_id: str,
        source_ip: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Tuple[ThreatAssessment, List[ThreatAlert]]:
        """
        Analyze an event and execute appropriate responses.
        
        Args:
            user_id: User identifier
            source_ip: Source IP address
            event_type: Type of event (login, api_call, etc.)
            event_data: Event-specific data
            timestamp: Event timestamp
            
        Returns:
            Tuple of (threat_assessment, generated_alerts)
        """
        self._processed_events += 1
        
        # Analyze the event
        if event_type == "login":
            assessment = self.detector.analyze_login_event(
                user_id=user_id,
                source_ip=source_ip,
                success=event_data.get("success", True),
                user_agent=event_data.get("user_agent"),
                location=event_data.get("location"),
                timestamp=timestamp
            )
        elif event_type == "session":
            assessment = self.detector.analyze_session_event(
                user_id=user_id,
                session_id=event_data.get("session_id", "unknown"),
                event_type=event_data.get("session_event_type", "api_call"),
                event_data=event_data,
                timestamp=timestamp
            )
        else:
            # Generic event analysis
            assessment = ThreatAssessment(
                assessment_id=generate_assessment_id(),
                user_id=user_id,
                source_ip=source_ip,
                threat_level=ThreatLevel.LOW,
                confidence=0.1
            )
        
        # Process with response system
        alerts = await self.response.process_threat_assessment(assessment)
        
        if alerts:
            self._generated_alerts += len(alerts)
        
        return assessment, alerts
    
    def is_request_allowed(
        self,
        user_id: str,
        source_ip: str,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a request should be allowed based on current blocks/limits.
        
        Args:
            user_id: User identifier
            source_ip: Source IP address
            session_id: Optional session identifier
            
        Returns:
            Tuple of (allowed, reason_if_blocked)
        """
        if self.response.is_ip_blocked(source_ip):
            return False, f"IP {source_ip} is blocked due to security threats"
        
        if self.response.is_user_blocked(user_id):
            return False, f"User {user_id} is blocked due to security threats"
        
        if session_id and self.response.is_session_quarantined(session_id):
            return False, f"Session {session_id} is quarantined due to security threats"
        
        if self.response.is_ip_rate_limited(source_ip):
            return False, f"IP {source_ip} is rate limited due to security threats"
        
        if self.response.is_user_rate_limited(user_id):
            return False, f"User {user_id} is rate limited due to security threats"
        
        return True, None
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        detector_stats = self.detector.get_statistics()
        response_stats = self.response.get_statistics()
        
        return {
            "system": {
                "processed_events": self._processed_events,
                "generated_alerts": self._generated_alerts,
                "executed_responses": self._executed_responses
            },
            "detection": detector_stats,
            "response": response_stats
        }

# =============================================================================
# Aliases for backward compatibility and convenience
# =============================================================================

# ThreatDetectionManager is an alias for IntegratedThreatSystem for better naming consistency
ThreatDetectionManager = IntegratedThreatSystem
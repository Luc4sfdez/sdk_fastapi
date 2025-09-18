"""
Advanced Sampling Strategies for Distributed Tracing.

This module provides intelligent sampling strategies including probabilistic,
rate-limiting, adaptive, and custom sampling algorithms for optimal
performance and cost management in production environments.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import logging
import time
import threading
import random
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict

# OpenTelemetry imports
try:
    from opentelemetry.sdk.trace.sampling import (
        Sampler,
        SamplingResult,
        Decision,
        TraceIdRatioBased,
        AlwaysOn,
        AlwaysOff,
        ParentBased
    )
    from opentelemetry.trace import Link, SpanKind
    from opentelemetry.util.types import Attributes
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    # Mock classes for development
    class Sampler:
        pass
    class SamplingResult:
        pass
    class Decision:
        RECORD_AND_SAMPLE = "RECORD_AND_SAMPLE"
        NOT_RECORD = "NOT_RECORD"
        RECORD_ONLY = "RECORD_ONLY"
        DROP = "DROP"
    
    class SpanKind:
        pass
    
    class Link:
        pass
    
    Attributes = dict
    
    class BaseSampler:
        def __init__(self, config=None):
            self.config = config
            self._logger = logging.getLogger(__name__)
        
        def should_sample(self, *args, **kwargs):
            return SamplingResult()

from .exceptions import SamplingError


class SamplingStrategy(Enum):
    """Sampling strategy enumeration."""
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"
    ADAPTIVE = "adaptive"
    CUSTOM = "custom"


class AdaptiveSamplingMode(Enum):
    """Adaptive sampling mode enumeration."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class SamplingConfig:
    """Configuration for sampling strategies."""
    strategy: SamplingStrategy = SamplingStrategy.PROBABILISTIC
    probabilistic_rate: float = 0.1
    max_traces_per_second: float = 100.0
    adaptive_target_tps: float = 50.0
    adaptive_mode: AdaptiveSamplingMode = AdaptiveSamplingMode.BALANCED
    adaptive_adjustment_interval: float = 30.0
    adaptive_min_rate: float = 0.001
    adaptive_max_rate: float = 1.0
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    service_specific_rates: Dict[str, float] = field(default_factory=dict)
    operation_specific_rates: Dict[str, float] = field(default_factory=dict)


class SamplingDecision(Enum):
    """Sampling decision enumeration."""
    RECORD_AND_SAMPLE = "RECORD_AND_SAMPLE"
    NOT_RECORD = "NOT_RECORD"
    RECORD_ONLY = "RECORD_ONLY"


@dataclass
class SamplingContext:
    """Context information for sampling decisions."""
    trace_id: str
    span_name: str
    span_kind: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    parent_span_context: Optional[Any] = None
    links: Optional[List[Any]] = None
    service_name: Optional[str] = None
    operation_type: Optional[str] = None
    request_rate: Optional[float] = None
    error_rate: Optional[float] = None


@dataclass
class SamplingStats:
    """Statistics for sampling decisions."""
    total_decisions: int = 0
    sampled_count: int = 0
    not_sampled_count: int = 0
    recorded_only_count: int = 0
    sampling_rate: float = 0.0
    last_reset_time: float = field(default_factory=time.time)
    
    def update_stats(self, decision: SamplingDecision) -> None:
        """Update sampling statistics."""
        self.total_decisions += 1
        
        if decision == SamplingDecision.RECORD_AND_SAMPLE:
            self.sampled_count += 1
        elif decision == SamplingDecision.NOT_RECORD:
            self.not_sampled_count += 1
        elif decision == SamplingDecision.RECORD_ONLY:
            self.recorded_only_count += 1
        
        # Update sampling rate
        if self.total_decisions > 0:
            self.sampling_rate = self.sampled_count / self.total_decisions
    
    def reset_stats(self) -> None:
        """Reset sampling statistics."""
        self.total_decisions = 0
        self.sampled_count = 0
        self.not_sampled_count = 0
        self.recorded_only_count = 0
        self.sampling_rate = 0.0
        self.last_reset_time = time.time()


class AdvancedSampler(ABC):
    """Base class for advanced sampling strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.stats = SamplingStats()
        self._logger = logging.getLogger(__name__)
    
    @abstractmethod
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make sampling decision based on context."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sampling statistics."""
        return {
            'sampler_name': self.name,
            'total_decisions': self.stats.total_decisions,
            'sampled_count': self.stats.sampled_count,
            'not_sampled_count': self.stats.not_sampled_count,
            'recorded_only_count': self.stats.recorded_only_count,
            'sampling_rate': self.stats.sampling_rate,
            'last_reset_time': self.stats.last_reset_time
        }
    
    def reset_stats(self) -> None:
        """Reset sampling statistics."""
        self.stats.reset_stats()


class ProbabilisticSampler(AdvancedSampler):
    """Probabilistic sampling strategy."""
    
    def __init__(self, sampling_rate: float, name: str = "probabilistic"):
        super().__init__(name)
        if not 0.0 <= sampling_rate <= 1.0:
            raise SamplingError(
                message=f"Invalid sampling rate: {sampling_rate}. Must be between 0.0 and 1.0",
                sampling_strategy="probabilistic",
                sampling_rate=sampling_rate
            )
        self.sampling_rate = sampling_rate
    
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make probabilistic sampling decision."""
        try:
            # Use trace ID for deterministic sampling
            trace_id_int = int(context.trace_id[-16:], 16) if context.trace_id else random.randint(0, 2**64-1)
            threshold = self.sampling_rate * (2**64 - 1)
            
            decision = (
                SamplingDecision.RECORD_AND_SAMPLE 
                if trace_id_int < threshold 
                else SamplingDecision.NOT_RECORD
            )
            
            self.stats.update_stats(decision)
            return decision
            
        except Exception as e:
            self._logger.error(f"Error in probabilistic sampling: {e}")
            # Default to not sampling on error
            decision = SamplingDecision.NOT_RECORD
            self.stats.update_stats(decision)
            return decision


class RateLimitingSampler(AdvancedSampler):
    """Rate-limiting sampling strategy."""
    
    def __init__(self, max_traces_per_second: float, name: str = "rate_limiting"):
        super().__init__(name)
        self.max_traces_per_second = max_traces_per_second
        self.tokens = max_traces_per_second
        self.last_refill_time = time.time()
        self._lock = threading.RLock()
    
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make rate-limiting sampling decision."""
        try:
            with self._lock:
                current_time = time.time()
                
                # Refill tokens based on elapsed time
                elapsed = current_time - self.last_refill_time
                self.tokens = min(
                    self.max_traces_per_second,
                    self.tokens + elapsed * self.max_traces_per_second
                )
                self.last_refill_time = current_time
                
                # Check if we have tokens available
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    decision = SamplingDecision.RECORD_AND_SAMPLE
                else:
                    decision = SamplingDecision.NOT_RECORD
                
                self.stats.update_stats(decision)
                return decision
                
        except Exception as e:
            self._logger.error(f"Error in rate limiting sampling: {e}")
            decision = SamplingDecision.NOT_RECORD
            self.stats.update_stats(decision)
            return decision


class AdaptiveSampler(AdvancedSampler):
    """Adaptive sampling strategy that adjusts based on system load and error rates."""
    
    def __init__(
        self,
        base_sampling_rate: float = 0.1,
        max_sampling_rate: float = 1.0,
        min_sampling_rate: float = 0.001,
        adaptation_interval: float = 60.0,
        error_rate_threshold: float = 0.05,
        name: str = "adaptive"
    ):
        super().__init__(name)
        self.base_sampling_rate = base_sampling_rate
        self.max_sampling_rate = max_sampling_rate
        self.min_sampling_rate = min_sampling_rate
        self.adaptation_interval = adaptation_interval
        self.error_rate_threshold = error_rate_threshold
        
        self.current_sampling_rate = base_sampling_rate
        self.last_adaptation_time = time.time()
        
        # Metrics for adaptation
        self.recent_decisions: deque = deque(maxlen=1000)
        self.error_rates: deque = deque(maxlen=100)
        self.system_load_history: deque = deque(maxlen=100)
        
        self._lock = threading.RLock()
    
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make adaptive sampling decision."""
        try:
            with self._lock:
                # Adapt sampling rate if needed
                self._adapt_sampling_rate(context)
                
                # Make probabilistic decision with current rate
                trace_id_int = int(context.trace_id[-16:], 16) if context.trace_id else random.randint(0, 2**64-1)
                threshold = self.current_sampling_rate * (2**64 - 1)
                
                decision = (
                    SamplingDecision.RECORD_AND_SAMPLE 
                    if trace_id_int < threshold 
                    else SamplingDecision.NOT_RECORD
                )
                
                # Record decision for adaptation
                self.recent_decisions.append({
                    'decision': decision,
                    'timestamp': time.time(),
                    'error_rate': context.error_rate,
                    'request_rate': context.request_rate
                })
                
                self.stats.update_stats(decision)
                return decision
                
        except Exception as e:
            self._logger.error(f"Error in adaptive sampling: {e}")
            decision = SamplingDecision.NOT_RECORD
            self.stats.update_stats(decision)
            return decision
    
    def _adapt_sampling_rate(self, context: SamplingContext) -> None:
        """Adapt sampling rate based on system conditions."""
        current_time = time.time()
        
        if current_time - self.last_adaptation_time < self.adaptation_interval:
            return
        
        try:
            # Analyze recent error rates
            if context.error_rate is not None:
                self.error_rates.append(context.error_rate)
            
            # Calculate average error rate
            if self.error_rates:
                avg_error_rate = sum(self.error_rates) / len(self.error_rates)
                
                # Increase sampling if error rate is high
                if avg_error_rate > self.error_rate_threshold:
                    self.current_sampling_rate = min(
                        self.max_sampling_rate,
                        self.current_sampling_rate * 1.5
                    )
                    self._logger.info(f"Increased sampling rate to {self.current_sampling_rate:.4f} due to high error rate")
                
                # Decrease sampling if error rate is low and system is stable
                elif avg_error_rate < self.error_rate_threshold * 0.5:
                    self.current_sampling_rate = max(
                        self.min_sampling_rate,
                        self.current_sampling_rate * 0.9
                    )
                    self._logger.debug(f"Decreased sampling rate to {self.current_sampling_rate:.4f}")
            
            # Analyze request rate
            if context.request_rate is not None:
                # Decrease sampling under high load
                if context.request_rate > 1000:  # High request rate threshold
                    self.current_sampling_rate = max(
                        self.min_sampling_rate,
                        self.current_sampling_rate * 0.8
                    )
                    self._logger.info(f"Decreased sampling rate to {self.current_sampling_rate:.4f} due to high load")
            
            self.last_adaptation_time = current_time
            
        except Exception as e:
            self._logger.error(f"Error adapting sampling rate: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adaptive sampling statistics."""
        stats = super().get_stats()
        stats.update({
            'current_sampling_rate': self.current_sampling_rate,
            'base_sampling_rate': self.base_sampling_rate,
            'recent_decisions_count': len(self.recent_decisions),
            'error_rates_count': len(self.error_rates),
            'last_adaptation_time': self.last_adaptation_time
        })
        return stats


class PrioritySampler(AdvancedSampler):
    """Priority-based sampling strategy."""
    
    def __init__(
        self,
        priority_rules: Dict[str, float],
        default_sampling_rate: float = 0.1,
        name: str = "priority"
    ):
        super().__init__(name)
        self.priority_rules = priority_rules
        self.default_sampling_rate = default_sampling_rate
    
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make priority-based sampling decision."""
        try:
            # Determine sampling rate based on priority rules
            sampling_rate = self.default_sampling_rate
            
            # Check span name patterns
            for pattern, rate in self.priority_rules.items():
                if pattern in context.span_name:
                    sampling_rate = rate
                    break
            
            # Check attributes for priority indicators
            if context.attributes:
                # High priority operations
                if context.attributes.get('priority') == 'high':
                    sampling_rate = 1.0
                elif context.attributes.get('priority') == 'low':
                    sampling_rate = 0.01
                
                # Error operations get higher priority
                if context.attributes.get('error') == 'true':
                    sampling_rate = min(1.0, sampling_rate * 5.0)
            
            # Make probabilistic decision
            trace_id_int = int(context.trace_id[-16:], 16) if context.trace_id else random.randint(0, 2**64-1)
            threshold = sampling_rate * (2**64 - 1)
            
            decision = (
                SamplingDecision.RECORD_AND_SAMPLE 
                if trace_id_int < threshold 
                else SamplingDecision.NOT_RECORD
            )
            
            self.stats.update_stats(decision)
            return decision
            
        except Exception as e:
            self._logger.error(f"Error in priority sampling: {e}")
            decision = SamplingDecision.NOT_RECORD
            self.stats.update_stats(decision)
            return decision


class CompositeSampler(AdvancedSampler):
    """Composite sampler that combines multiple sampling strategies."""
    
    def __init__(
        self,
        samplers: List[AdvancedSampler],
        combination_strategy: str = "any",  # "any", "all", "majority"
        name: str = "composite"
    ):
        super().__init__(name)
        self.samplers = samplers
        self.combination_strategy = combination_strategy
    
    def should_sample(self, context: SamplingContext) -> SamplingDecision:
        """Make composite sampling decision."""
        try:
            decisions = []
            
            # Get decisions from all samplers
            for sampler in self.samplers:
                decision = sampler.should_sample(context)
                decisions.append(decision)
            
            # Combine decisions based on strategy
            final_decision = self._combine_decisions(decisions)
            
            self.stats.update_stats(final_decision)
            return final_decision
            
        except Exception as e:
            self._logger.error(f"Error in composite sampling: {e}")
            decision = SamplingDecision.NOT_RECORD
            self.stats.update_stats(decision)
            return decision
    
    def _combine_decisions(self, decisions: List[SamplingDecision]) -> SamplingDecision:
        """Combine multiple sampling decisions."""
        if not decisions:
            return SamplingDecision.NOT_RECORD
        
        sample_count = sum(1 for d in decisions if d == SamplingDecision.RECORD_AND_SAMPLE)
        record_count = sum(1 for d in decisions if d == SamplingDecision.RECORD_ONLY)
        
        if self.combination_strategy == "any":
            # Sample if any sampler says to sample
            if sample_count > 0:
                return SamplingDecision.RECORD_AND_SAMPLE
            elif record_count > 0:
                return SamplingDecision.RECORD_ONLY
            else:
                return SamplingDecision.NOT_RECORD
        
        elif self.combination_strategy == "all":
            # Sample only if all samplers say to sample
            if sample_count == len(decisions):
                return SamplingDecision.RECORD_AND_SAMPLE
            elif sample_count + record_count == len(decisions):
                return SamplingDecision.RECORD_ONLY
            else:
                return SamplingDecision.NOT_RECORD
        
        elif self.combination_strategy == "majority":
            # Sample if majority says to sample
            majority_threshold = len(decisions) // 2 + 1
            if sample_count >= majority_threshold:
                return SamplingDecision.RECORD_AND_SAMPLE
            elif sample_count + record_count >= majority_threshold:
                return SamplingDecision.RECORD_ONLY
            else:
                return SamplingDecision.NOT_RECORD
        
        else:
            # Default to "any" strategy
            return self._combine_decisions(decisions) if self.combination_strategy != "any" else SamplingDecision.NOT_RECORD
    
    def get_stats(self) -> Dict[str, Any]:
        """Get composite sampling statistics."""
        stats = super().get_stats()
        stats['sub_samplers'] = [sampler.get_stats() for sampler in self.samplers]
        stats['combination_strategy'] = self.combination_strategy
        return stats


class OpenTelemetrySamplerAdapter:
    """Adapter to use advanced samplers with OpenTelemetry."""
    
    def __init__(self, advanced_sampler: AdvancedSampler):
        self.advanced_sampler = advanced_sampler
        self._logger = logging.getLogger(__name__)
    
    def should_sample(
        self,
        parent_context: Optional[Any],
        trace_id: int,
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Optional[Attributes] = None,
        links: Optional[List[Link]] = None,
        trace_state: Optional[str] = None
    ) -> SamplingResult:
        """OpenTelemetry sampler interface."""
        try:
            # Convert to our sampling context
            context = SamplingContext(
                trace_id=format(trace_id, '032x'),
                span_name=name,
                span_kind=kind.name if kind else None,
                attributes=dict(attributes) if attributes else None,
                parent_span_context=parent_context,
                links=links
            )
            
            # Get decision from advanced sampler
            decision = self.advanced_sampler.should_sample(context)
            
            # Convert to OpenTelemetry decision
            if OPENTELEMETRY_AVAILABLE:
                if decision == SamplingDecision.RECORD_AND_SAMPLE:
                    otel_decision = Decision.RECORD_AND_SAMPLE
                elif decision == SamplingDecision.RECORD_ONLY:
                    otel_decision = Decision.RECORD_ONLY
                else:
                    otel_decision = Decision.NOT_RECORD
                
                return SamplingResult(
                    decision=otel_decision,
                    attributes=attributes,
                    trace_state=trace_state
                )
            else:
                # Mock result for development
                return SamplingResult()
                
        except Exception as e:
            self._logger.error(f"Error in OpenTelemetry sampler adapter: {e}")
            if OPENTELEMETRY_AVAILABLE:
                return SamplingResult(decision=Decision.NOT_RECORD)
            else:
                return SamplingResult()


# Factory functions for creating samplers
def create_probabilistic_sampler(sampling_rate: float) -> ProbabilisticSampler:
    """Create probabilistic sampler."""
    return ProbabilisticSampler(sampling_rate)


def create_rate_limiting_sampler(max_traces_per_second: float) -> RateLimitingSampler:
    """Create rate-limiting sampler."""
    return RateLimitingSampler(max_traces_per_second)


def create_adaptive_sampler(
    base_sampling_rate: float = 0.1,
    **kwargs
) -> AdaptiveSampler:
    """Create adaptive sampler."""
    return AdaptiveSampler(base_sampling_rate, **kwargs)


def create_priority_sampler(
    priority_rules: Dict[str, float],
    default_sampling_rate: float = 0.1
) -> PrioritySampler:
    """Create priority-based sampler."""
    return PrioritySampler(priority_rules, default_sampling_rate)


def create_composite_sampler(
    samplers: List[AdvancedSampler],
    combination_strategy: str = "any"
) -> CompositeSampler:
    """Create composite sampler."""
    return CompositeSampler(samplers, combination_strategy)


# Export main classes and functions
__all__ = [
    'SamplingDecision',
    'SamplingContext',
    'SamplingStats',
    'AdvancedSampler',
    'ProbabilisticSampler',
    'RateLimitingSampler',
    'AdaptiveSampler',
    'PrioritySampler',
    'CompositeSampler',
    'OpenTelemetrySamplerAdapter',
    'create_probabilistic_sampler',
    'create_rate_limiting_sampler',
    'create_adaptive_sampler',
    'create_priority_sampler',
    'create_composite_sampler',
]
class RateLimitingSampler(BaseSampler):
    """Rate-limiting sampler with token bucket algorithm."""
    
    def __init__(self, config: SamplingConfig):
        super().__init__(config)
        self.max_traces_per_second = config.max_traces_per_second
        self.tokens = config.max_traces_per_second
        self.last_refill_time = time.time()
        self._lock = threading.RLock()
    
    def should_sample(
        self,
        parent_context: Optional[Any] = None,
        trace_id: int = 0,
        name: str = "",
        kind: Optional[SpanKind] = None,
        attributes: Optional[Attributes] = None,
        links: Optional[List[Link]] = None,
        trace_state: Optional[str] = None
    ) -> SamplingResult:
        """Make rate-limiting sampling decision."""
        try:
            with self._lock:
                current_time = time.time()
                
                # Refill tokens based on elapsed time
                elapsed = current_time - self.last_refill_time
                self.tokens = min(
                    self.max_traces_per_second,
                    self.tokens + elapsed * self.max_traces_per_second
                )
                self.last_refill_time = current_time
                
                # Check if we have tokens available
                if OPENTELEMETRY_AVAILABLE:
                    if self.tokens >= 1.0:
                        self.tokens -= 1.0
                        decision = Decision.RECORD_AND_SAMPLE
                    else:
                        decision = Decision.DROP
                    
                    return SamplingResult(
                        decision=decision,
                        attributes=attributes,
                        trace_state=trace_state
                    )
                else:
                    return SamplingResult()
                    
        except Exception as e:
            self._logger.error(f"Error in rate limiting sampling: {e}")
            if OPENTELEMETRY_AVAILABLE:
                return SamplingResult(decision=Decision.DROP)
            else:
                return SamplingResult()


class AdaptiveSampler(BaseSampler):
    """Adaptive sampler that adjusts based on system conditions."""
    
    def __init__(self, config: SamplingConfig):
        super().__init__(config)
        self.current_rate = config.adaptive_target_tps / 100.0  # Start conservative
        self.target_tps = config.adaptive_target_tps
        self.max_rate = config.adaptive_max_rate
        self.min_rate = config.adaptive_min_rate
        self.adjustment_interval = config.adaptive_adjustment_interval
        
        self.last_adjustment_time = time.time()
        self.recent_samples: deque = deque(maxlen=1000)
        self.error_rates: deque = deque(maxlen=100)
        
        self._lock = threading.RLock()
        self._start_adjustment_thread()
    
    def should_sample(
        self,
        parent_context: Optional[Any] = None,
        trace_id: int = 0,
        name: str = "",
        kind: Optional[SpanKind] = None,
        attributes: Optional[Attributes] = None,
        links: Optional[List[Link]] = None,
        trace_state: Optional[str] = None
    ) -> SamplingResult:
        """Make adaptive sampling decision."""
        try:
            # Record sample for adaptation
            self.recent_samples.append({
                'timestamp': time.time(),
                'trace_id': trace_id,
                'name': name,
                'attributes': dict(attributes) if attributes else {}
            })
            
            # Make probabilistic decision with current rate
            threshold = self.current_rate * (2**64 - 1)
            
            if OPENTELEMETRY_AVAILABLE:
                decision = (
                    Decision.RECORD_AND_SAMPLE 
                    if trace_id < threshold 
                    else Decision.DROP
                )
                
                return SamplingResult(
                    decision=decision,
                    attributes=attributes,
                    trace_state=trace_state
                )
            else:
                return SamplingResult()
                
        except Exception as e:
            self._logger.error(f"Error in adaptive sampling: {e}")
            if OPENTELEMETRY_AVAILABLE:
                return SamplingResult(decision=Decision.DROP)
            else:
                return SamplingResult()
    
    def _start_adjustment_thread(self):
        """Start background thread for rate adjustment."""
        def adjustment_worker():
            while True:
                try:
                    time.sleep(self.adjustment_interval)
                    self._adjust_sampling_rate()
                except Exception as e:
                    self._logger.error(f"Error in adjustment worker: {e}")
        
        thread = threading.Thread(target=adjustment_worker, daemon=True)
        thread.start()
    
    def _adjust_sampling_rate(self):
        """Adjust sampling rate based on recent activity."""
        with self._lock:
            current_time = time.time()
            
            # Calculate current TPS
            recent_window = current_time - 60.0  # Last minute
            recent_count = sum(
                1 for sample in self.recent_samples 
                if sample['timestamp'] > recent_window
            )
            current_tps = recent_count / 60.0
            
            # Adjust rate based on target TPS
            if current_tps > self.target_tps * 1.2:
                # Too many traces, reduce rate
                self.current_rate = max(self.min_rate, self.current_rate * 0.8)
                self._logger.info(f"Reduced sampling rate to {self.current_rate:.4f}")
            elif current_tps < self.target_tps * 0.8:
                # Too few traces, increase rate
                self.current_rate = min(self.max_rate, self.current_rate * 1.2)
                self._logger.info(f"Increased sampling rate to {self.current_rate:.4f}")


class CustomSampler(BaseSampler):
    """Custom sampler with user-defined logic."""
    
    def __init__(self, config: SamplingConfig, custom_logic: Callable):
        super().__init__(config)
        self.custom_logic = custom_logic
    
    def should_sample(
        self,
        parent_context: Optional[Any] = None,
        trace_id: int = 0,
        name: str = "",
        kind: Optional[SpanKind] = None,
        attributes: Optional[Attributes] = None,
        links: Optional[List[Link]] = None,
        trace_state: Optional[str] = None
    ) -> SamplingResult:
        """Make custom sampling decision."""
        try:
            # Call custom logic
            should_sample = self.custom_logic(
                parent_context, trace_id, name, kind, attributes, links, trace_state
            )
            
            if OPENTELEMETRY_AVAILABLE:
                decision = Decision.RECORD_AND_SAMPLE if should_sample else Decision.DROP
                return SamplingResult(
                    decision=decision,
                    attributes=attributes,
                    trace_state=trace_state
                )
            else:
                return SamplingResult()
                
        except Exception as e:
            self._logger.error(f"Error in custom sampling: {e}")
            if OPENTELEMETRY_AVAILABLE:
                return SamplingResult(decision=Decision.DROP)
            else:
                return SamplingResult()


class SamplingManager:
    """Manager for sampling strategies."""
    
    def __init__(self, config: SamplingConfig):
        self.config = config
        self._samplers: Dict[str, BaseSampler] = {}
        self._current_sampler: Optional[BaseSampler] = None
        self._logger = logging.getLogger(__name__)
        
        self._initialize_samplers()
    
    def _initialize_samplers(self):
        """Initialize available samplers."""
        try:
            # Create samplers based on configuration
            if self.config.strategy == SamplingStrategy.ALWAYS_ON:
                if OPENTELEMETRY_AVAILABLE:
                    self._current_sampler = AlwaysOn()
                
            elif self.config.strategy == SamplingStrategy.ALWAYS_OFF:
                if OPENTELEMETRY_AVAILABLE:
                    self._current_sampler = AlwaysOff()
                
            elif self.config.strategy == SamplingStrategy.PROBABILISTIC:
                self._current_sampler = ProbabilisticSampler(self.config)
                
            elif self.config.strategy == SamplingStrategy.RATE_LIMITING:
                self._current_sampler = RateLimitingSampler(self.config)
                
            elif self.config.strategy == SamplingStrategy.ADAPTIVE:
                self._current_sampler = AdaptiveSampler(self.config)
            
            # Wrap with parent-based sampler if enabled
            if self.config.parent_based_enabled and OPENTELEMETRY_AVAILABLE:
                self._current_sampler = ParentBased(root=self._current_sampler)
                
        except Exception as e:
            self._logger.error(f"Failed to initialize samplers: {e}")
            # Fallback to always-off sampler
            if OPENTELEMETRY_AVAILABLE:
                self._current_sampler = AlwaysOff()
    
    def get_sampler(self) -> Optional[BaseSampler]:
        """Get current sampler."""
        return self._current_sampler
    
    def update_config(self, config: SamplingConfig):
        """Update sampling configuration."""
        self.config = config
        self._initialize_samplers()
        self._logger.info(f"Updated sampling configuration: {config.strategy.value}")
    
    def get_sampling_stats(self) -> Dict[str, Any]:
        """Get sampling statistics."""
        stats = {
            'strategy': self.config.strategy.value,
            'current_sampler': type(self._current_sampler).__name__ if self._current_sampler else None
        }
        
        # Add sampler-specific stats if available
        if hasattr(self._current_sampler, 'get_stats'):
            stats.update(self._current_sampler.get_stats())
        
        return stats


# Factory functions
def create_sampling_manager(config: SamplingConfig) -> SamplingManager:
    """Create sampling manager."""
    return SamplingManager(config)


def create_probabilistic_sampler_config(rate: float) -> SamplingConfig:
    """Create probabilistic sampler configuration."""
    return SamplingConfig(
        strategy=SamplingStrategy.PROBABILISTIC,
        probabilistic_rate=rate
    )


def create_rate_limiting_sampler_config(max_tps: float) -> SamplingConfig:
    """Create rate-limiting sampler configuration."""
    return SamplingConfig(
        strategy=SamplingStrategy.RATE_LIMITING,
        max_traces_per_second=max_tps
    )


def create_adaptive_sampler_config(target_tps: float) -> SamplingConfig:
    """Create adaptive sampler configuration."""
    return SamplingConfig(
        strategy=SamplingStrategy.ADAPTIVE,
        adaptive_target_tps=target_tps
    )


# Export main classes and functions
__all__ = [
    'SamplingStrategy',
    'AdaptiveSamplingMode',
    'SamplingConfig',
    'BaseSampler',
    'ProbabilisticSampler',
    'RateLimitingSampler',
    'AdaptiveSampler',
    'CustomSampler',
    'SamplingManager',
    'create_sampling_manager',
    'create_probabilistic_sampler_config',
    'create_rate_limiting_sampler_config',
    'create_adaptive_sampler_config',
]
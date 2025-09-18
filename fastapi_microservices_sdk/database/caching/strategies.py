"""
Cache strategies for intelligent cache management.

This module provides various caching strategies including LRU, LFU, TTL-based,
and adaptive strategies for optimal cache performance.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
import heapq

from .config import CacheConfig, CacheStrategy
from .backends import CacheEntry
from .exceptions import CacheError


@dataclass
class StrategyMetrics:
    """Metrics for cache strategy performance."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    promotions: int = 0
    demotions: int = 0
    total_operations: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def eviction_rate(self) -> float:
        """Calculate eviction rate."""
        return self.evictions / self.total_operations if self.total_operations > 0 else 0.0


class CacheStrategyInterface(ABC):
    """Abstract interface for cache strategies."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.metrics = StrategyMetrics()
    
    @abstractmethod
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Determine if eviction should occur."""
        pass
    
    @abstractmethod
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Select entries for eviction."""
        pass
    
    @abstractmethod
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Handle cache access event."""
        pass
    
    @abstractmethod
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Handle cache insertion event."""
        pass
    
    @abstractmethod
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Handle cache eviction event."""
        pass
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get strategy metrics."""
        return {
            'strategy': self.__class__.__name__,
            'hits': self.metrics.hits,
            'misses': self.metrics.misses,
            'evictions': self.metrics.evictions,
            'promotions': self.metrics.promotions,
            'demotions': self.metrics.demotions,
            'total_operations': self.metrics.total_operations,
            'hit_rate': self.metrics.hit_rate,
            'eviction_rate': self.metrics.eviction_rate
        }


class LRUStrategy(CacheStrategyInterface):
    """Least Recently Used cache strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._access_order: OrderedDict[str, float] = OrderedDict()
    
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Check if eviction is needed."""
        return current_size >= max_size
    
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Select least recently used entries for eviction."""
        # Sort by last access time (oldest first)
        candidates = sorted(
            entries.items(),
            key=lambda x: x[1].last_accessed or x[1].created_at
        )
        
        eviction_keys = [key for key, _ in candidates[:count]]
        self.metrics.evictions += len(eviction_keys)
        
        return eviction_keys
    
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Update access order on cache hit."""
        self._access_order[key] = time.time()
        self._access_order.move_to_end(key)
        self.metrics.hits += 1
        self.metrics.total_operations += 1
    
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Track new entry insertion."""
        self._access_order[key] = time.time()
        self.metrics.total_operations += 1
    
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Clean up evicted entry."""
        self._access_order.pop(key, None)


class LFUStrategy(CacheStrategyInterface):
    """Least Frequently Used cache strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._frequency_counter: Dict[str, int] = defaultdict(int)
        self._frequency_buckets: Dict[int, set] = defaultdict(set)
        self._min_frequency = 0
    
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Check if eviction is needed."""
        return current_size >= max_size
    
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Select least frequently used entries for eviction."""
        eviction_keys = []
        
        # Start from minimum frequency and work up
        current_freq = self._min_frequency
        
        while len(eviction_keys) < count and current_freq in self._frequency_buckets:
            bucket = self._frequency_buckets[current_freq]
            
            # Take keys from current frequency bucket
            keys_needed = count - len(eviction_keys)
            keys_from_bucket = list(bucket)[:keys_needed]
            eviction_keys.extend(keys_from_bucket)
            
            current_freq += 1
        
        self.metrics.evictions += len(eviction_keys)
        return eviction_keys
    
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Update frequency on cache hit."""
        old_freq = self._frequency_counter[key]
        new_freq = old_freq + 1
        
        # Update frequency counter
        self._frequency_counter[key] = new_freq
        
        # Move from old bucket to new bucket
        if old_freq > 0:
            self._frequency_buckets[old_freq].discard(key)
            if not self._frequency_buckets[old_freq] and old_freq == self._min_frequency:
                self._min_frequency += 1
        
        self._frequency_buckets[new_freq].add(key)
        
        self.metrics.hits += 1
        self.metrics.total_operations += 1
    
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Track new entry insertion."""
        self._frequency_counter[key] = 1
        self._frequency_buckets[1].add(key)
        self._min_frequency = 1
        self.metrics.total_operations += 1
    
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Clean up evicted entry."""
        freq = self._frequency_counter.pop(key, 0)
        if freq > 0:
            self._frequency_buckets[freq].discard(key)


class TTLStrategy(CacheStrategyInterface):
    """Time-To-Live based cache strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._expiration_heap: List[Tuple[float, str]] = []
    
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Check if eviction is needed (always evict expired first)."""
        return current_size >= max_size or self._has_expired_entries()
    
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Select expired entries first, then oldest entries."""
        eviction_keys = []
        current_time = datetime.now(timezone.utc)
        
        # First, collect expired entries
        expired_keys = [
            key for key, entry in entries.items()
            if entry.expires_at and entry.expires_at <= current_time
        ]
        
        eviction_keys.extend(expired_keys[:count])
        
        # If we need more evictions, select oldest entries
        if len(eviction_keys) < count:
            remaining_count = count - len(eviction_keys)
            non_expired = {
                k: v for k, v in entries.items() 
                if k not in expired_keys
            }
            
            oldest_entries = sorted(
                non_expired.items(),
                key=lambda x: x[1].created_at
            )
            
            oldest_keys = [key for key, _ in oldest_entries[:remaining_count]]
            eviction_keys.extend(oldest_keys)
        
        self.metrics.evictions += len(eviction_keys)
        return eviction_keys
    
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Handle cache access."""
        self.metrics.hits += 1
        self.metrics.total_operations += 1
    
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Track new entry with expiration."""
        if entry.expires_at:
            expiration_timestamp = entry.expires_at.timestamp()
            heapq.heappush(self._expiration_heap, (expiration_timestamp, key))
        
        self.metrics.total_operations += 1
    
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Clean up evicted entry."""
        # Note: We don't remove from heap as it's expensive
        # Instead, we check validity when processing heap
        pass
    
    def _has_expired_entries(self) -> bool:
        """Check if there are expired entries."""
        current_time = time.time()
        
        while self._expiration_heap:
            expiration_time, key = self._expiration_heap[0]
            if expiration_time <= current_time:
                return True
            break
        
        return False


class AdaptiveStrategy(CacheStrategyInterface):
    """Adaptive cache strategy that switches between LRU and LFU based on workload."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._lru_strategy = LRUStrategy(config)
        self._lfu_strategy = LFUStrategy(config)
        self._current_strategy = self._lru_strategy
        
        # Adaptation parameters
        self._evaluation_window = 1000  # Operations
        self._operation_count = 0
        self._lru_performance_history: List[float] = []
        self._lfu_performance_history: List[float] = []
        self._adaptation_threshold = 0.05  # 5% improvement needed to switch
    
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Delegate to current strategy."""
        return await self._current_strategy.should_evict(current_size, max_size)
    
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Delegate to current strategy."""
        candidates = await self._current_strategy.select_eviction_candidates(entries, count)
        await self._evaluate_and_adapt()
        return candidates
    
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Handle access with both strategies for comparison."""
        await self._current_strategy.on_access(key, entry)
        
        # Also update the non-active strategy for comparison
        other_strategy = self._lfu_strategy if self._current_strategy == self._lru_strategy else self._lru_strategy
        await other_strategy.on_access(key, entry)
        
        self._operation_count += 1
        self.metrics.hits += 1
        self.metrics.total_operations += 1
    
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Handle insertion with both strategies."""
        await self._lru_strategy.on_insert(key, entry)
        await self._lfu_strategy.on_insert(key, entry)
        self._operation_count += 1
        self.metrics.total_operations += 1
    
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Handle eviction with both strategies."""
        await self._lru_strategy.on_evict(key, entry)
        await self._lfu_strategy.on_evict(key, entry)
    
    async def _evaluate_and_adapt(self) -> None:
        """Evaluate performance and adapt strategy if needed."""
        if self._operation_count % self._evaluation_window != 0:
            return
        
        # Get current performance metrics
        lru_metrics = await self._lru_strategy.get_metrics()
        lfu_metrics = await self._lfu_strategy.get_metrics()
        
        lru_hit_rate = lru_metrics['hit_rate']
        lfu_hit_rate = lfu_metrics['hit_rate']
        
        # Store performance history
        self._lru_performance_history.append(lru_hit_rate)
        self._lfu_performance_history.append(lfu_hit_rate)
        
        # Keep only recent history
        if len(self._lru_performance_history) > 10:
            self._lru_performance_history = self._lru_performance_history[-10:]
            self._lfu_performance_history = self._lfu_performance_history[-10:]
        
        # Decide if we should switch strategies
        if len(self._lru_performance_history) >= 3:
            avg_lru_performance = sum(self._lru_performance_history[-3:]) / 3
            avg_lfu_performance = sum(self._lfu_performance_history[-3:]) / 3
            
            current_is_lru = self._current_strategy == self._lru_strategy
            
            if current_is_lru and avg_lfu_performance > avg_lru_performance + self._adaptation_threshold:
                self._current_strategy = self._lfu_strategy
                self.metrics.promotions += 1
            elif not current_is_lru and avg_lru_performance > avg_lfu_performance + self._adaptation_threshold:
                self._current_strategy = self._lru_strategy
                self.metrics.promotions += 1
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get adaptive strategy metrics."""
        base_metrics = await super().get_metrics()
        
        lru_metrics = await self._lru_strategy.get_metrics()
        lfu_metrics = await self._lfu_strategy.get_metrics()
        
        base_metrics.update({
            'current_strategy': 'LRU' if self._current_strategy == self._lru_strategy else 'LFU',
            'lru_hit_rate': lru_metrics['hit_rate'],
            'lfu_hit_rate': lfu_metrics['hit_rate'],
            'adaptations': self.metrics.promotions,
            'evaluation_window': self._evaluation_window
        })
        
        return base_metrics


class FIFOStrategy(CacheStrategyInterface):
    """First-In-First-Out cache strategy."""
    
    def __init__(self, config: CacheConfig):
        super().__init__(config)
        self._insertion_order: OrderedDict[str, float] = OrderedDict()
    
    async def should_evict(self, current_size: int, max_size: int) -> bool:
        """Check if eviction is needed."""
        return current_size >= max_size
    
    async def select_eviction_candidates(
        self, 
        entries: Dict[str, CacheEntry], 
        count: int
    ) -> List[str]:
        """Select oldest entries for eviction."""
        # Sort by creation time (oldest first)
        candidates = sorted(
            entries.items(),
            key=lambda x: x[1].created_at
        )
        
        eviction_keys = [key for key, _ in candidates[:count]]
        self.metrics.evictions += len(eviction_keys)
        
        return eviction_keys
    
    async def on_access(self, key: str, entry: CacheEntry) -> None:
        """Handle cache access (no reordering in FIFO)."""
        self.metrics.hits += 1
        self.metrics.total_operations += 1
    
    async def on_insert(self, key: str, entry: CacheEntry) -> None:
        """Track insertion order."""
        self._insertion_order[key] = time.time()
        self.metrics.total_operations += 1
    
    async def on_evict(self, key: str, entry: CacheEntry) -> None:
        """Clean up evicted entry."""
        self._insertion_order.pop(key, None)


def create_strategy(strategy_type: CacheStrategy, config: CacheConfig) -> CacheStrategyInterface:
    """
    Factory function to create cache strategy instances.
    
    Args:
        strategy_type: Type of strategy to create
        config: Cache configuration
        
    Returns:
        Strategy instance
        
    Raises:
        CacheError: If strategy type is not supported
    """
    strategy_map = {
        CacheStrategy.LRU: LRUStrategy,
        CacheStrategy.LFU: LFUStrategy,
        CacheStrategy.TTL: TTLStrategy,
        CacheStrategy.ADAPTIVE: AdaptiveStrategy,
        CacheStrategy.FIFO: FIFOStrategy
    }
    
    strategy_class = strategy_map.get(strategy_type)
    if not strategy_class:
        raise CacheError(f"Unsupported cache strategy: {strategy_type}")
    
    return strategy_class(config)
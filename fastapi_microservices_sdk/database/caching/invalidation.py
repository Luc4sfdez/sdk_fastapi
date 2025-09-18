"""
Cache invalidation system for intelligent cache management.

This module provides various invalidation strategies including tag-based,
time-based, and event-based invalidation for maintaining cache consistency.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Set, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict
import weakref

from .config import CacheConfig, InvalidationPolicy
from .backends import CacheBackendInterface
from .exceptions import CacheInvalidationError

# Integration with communication logging
try:
    from ...communication.logging import CommunicationLogger
    COMMUNICATION_LOGGING_AVAILABLE = True
except ImportError:
    COMMUNICATION_LOGGING_AVAILABLE = False
    CommunicationLogger = None


@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    name: str
    pattern: str
    tags: List[str] = field(default_factory=list)
    ttl: Optional[timedelta] = None
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def matches(self, key: str, tags: List[str]) -> bool:
        """Check if rule matches given key and tags."""
        if not self.enabled:
            return False
        
        # Check pattern match
        import re
        if not re.match(self.pattern, key):
            return False
        
        # Check tag match
        if self.tags and not any(tag in tags for tag in self.tags):
            return False
        
        return True


@dataclass
class InvalidationEvent:
    """Event that triggers cache invalidation."""
    event_type: str
    database_name: str
    table_name: Optional[str] = None
    operation: Optional[str] = None  # INSERT, UPDATE, DELETE
    affected_keys: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class InvalidationManager:
    """
    Central invalidation management system.
    
    Coordinates various invalidation strategies and ensures cache consistency
    across all backends and databases.
    """
    
    def __init__(self, config: CacheConfig):
        self.config = config
        
        # Setup logging
        if COMMUNICATION_LOGGING_AVAILABLE:
            self.logger = CommunicationLogger("cache.invalidation")
        else:
            self.logger = logging.getLogger(__name__)
        
        # Invalidation strategies
        self._strategies: Dict[str, 'InvalidationStrategyInterface'] = {}
        self._rules: List[InvalidationRule] = []
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Backend references (weak references to avoid circular dependencies)
        self._backends: Dict[str, CacheBackendInterface] = {}
        
        # Statistics
        self._invalidation_stats = {
            'total_invalidations': 0,
            'by_strategy': defaultdict(int),
            'by_database': defaultdict(int),
            'by_table': defaultdict(int),
            'errors': 0
        }
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        self.logger.info("InvalidationManager initialized")
    
    async def initialize(self, backends: Dict[str, CacheBackendInterface]) -> None:
        """Initialize invalidation manager with backends."""
        self._backends = backends
        
        # Initialize default strategies
        await self._initialize_strategies()
        
        # Start background cleanup task
        if self.config.invalidation_policy != InvalidationPolicy.MANUAL:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._running = True
        
        self.logger.info("InvalidationManager initialized with backends")
    
    async def shutdown(self) -> None:
        """Shutdown invalidation manager."""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("InvalidationManager shutdown completed")
    
    async def _initialize_strategies(self) -> None:
        """Initialize invalidation strategies."""
        # Tag-based invalidation
        self._strategies['tag_based'] = TagBasedInvalidation(self.config, self._backends)
        
        # Time-based invalidation
        self._strategies['time_based'] = TimeBasedInvalidation(self.config, self._backends)
        
        # Event-based invalidation
        self._strategies['event_based'] = EventBasedInvalidation(self.config, self._backends)
        
        # Initialize all strategies
        for strategy in self._strategies.values():
            await strategy.initialize()
    
    async def add_rule(self, rule: InvalidationRule) -> None:
        """Add invalidation rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self.logger.info(f"Added invalidation rule: {rule.name}")
    
    async def remove_rule(self, rule_name: str) -> bool:
        """Remove invalidation rule."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                del self._rules[i]
                self.logger.info(f"Removed invalidation rule: {rule_name}")
                return True
        return False
    
    async def invalidate_by_tags(
        self, 
        tags: List[str], 
        database_name: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries by tags.
        
        Args:
            tags: Tags to invalidate
            database_name: Specific database or all if None
            
        Returns:
            Number of entries invalidated
        """
        try:
            strategy = self._strategies.get('tag_based')
            if not strategy:
                raise CacheInvalidationError("Tag-based invalidation strategy not available")
            
            total_invalidated = await strategy.invalidate(tags, database_name)
            
            # Update statistics
            self._invalidation_stats['total_invalidations'] += total_invalidated
            self._invalidation_stats['by_strategy']['tag_based'] += total_invalidated
            
            if database_name:
                self._invalidation_stats['by_database'][database_name] += total_invalidated
            
            self.logger.info(f"Invalidated {total_invalidated} entries by tags: {tags}")
            return total_invalidated
        
        except Exception as e:
            self._invalidation_stats['errors'] += 1
            self.logger.error(f"Tag-based invalidation failed: {e}")
            raise CacheInvalidationError(f"Tag-based invalidation failed: {e}", original_error=e)
    
    async def invalidate_by_pattern(
        self, 
        pattern: str, 
        database_name: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries by key pattern.
        
        Args:
            pattern: Regex pattern to match keys
            database_name: Specific database or all if None
            
        Returns:
            Number of entries invalidated
        """
        try:
            total_invalidated = 0
            
            # Apply pattern to all matching rules
            for rule in self._rules:
                if rule.pattern == pattern and rule.enabled:
                    invalidated = await self.invalidate_by_tags(rule.tags, database_name)
                    total_invalidated += invalidated
            
            self.logger.info(f"Invalidated {total_invalidated} entries by pattern: {pattern}")
            return total_invalidated
        
        except Exception as e:
            self._invalidation_stats['errors'] += 1
            self.logger.error(f"Pattern-based invalidation failed: {e}")
            raise CacheInvalidationError(f"Pattern-based invalidation failed: {e}", original_error=e)
    
    async def invalidate_by_event(self, event: InvalidationEvent) -> int:
        """
        Invalidate cache entries based on database event.
        
        Args:
            event: Database event that triggers invalidation
            
        Returns:
            Number of entries invalidated
        """
        try:
            strategy = self._strategies.get('event_based')
            if not strategy:
                raise CacheInvalidationError("Event-based invalidation strategy not available")
            
            total_invalidated = await strategy.handle_event(event)
            
            # Update statistics
            self._invalidation_stats['total_invalidations'] += total_invalidated
            self._invalidation_stats['by_strategy']['event_based'] += total_invalidated
            self._invalidation_stats['by_database'][event.database_name] += total_invalidated
            
            if event.table_name:
                self._invalidation_stats['by_table'][f"{event.database_name}.{event.table_name}"] += total_invalidated
            
            # Execute registered event handlers
            for handler in self._event_handlers.get(event.event_type, []):
                try:
                    await handler(event)
                except Exception as e:
                    self.logger.warning(f"Event handler failed: {e}")
            
            self.logger.info(f"Invalidated {total_invalidated} entries by event: {event.event_type}")
            return total_invalidated
        
        except Exception as e:
            self._invalidation_stats['errors'] += 1
            self.logger.error(f"Event-based invalidation failed: {e}")
            raise CacheInvalidationError(f"Event-based invalidation failed: {e}", original_error=e)
    
    async def invalidate_expired(self) -> int:
        """
        Invalidate expired cache entries.
        
        Returns:
            Number of entries invalidated
        """
        try:
            strategy = self._strategies.get('time_based')
            if not strategy:
                raise CacheInvalidationError("Time-based invalidation strategy not available")
            
            total_invalidated = await strategy.cleanup_expired()
            
            # Update statistics
            self._invalidation_stats['total_invalidations'] += total_invalidated
            self._invalidation_stats['by_strategy']['time_based'] += total_invalidated
            
            if total_invalidated > 0:
                self.logger.info(f"Invalidated {total_invalidated} expired entries")
            
            return total_invalidated
        
        except Exception as e:
            self._invalidation_stats['errors'] += 1
            self.logger.error(f"Expired entry cleanup failed: {e}")
            return 0
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler for specific event type."""
        self._event_handlers[event_type].append(handler)
        self.logger.info(f"Added event handler for: {event_type}")
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> bool:
        """Remove event handler."""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
                self.logger.info(f"Removed event handler for: {event_type}")
                return True
            except ValueError:
                pass
        return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics."""
        return {
            'total_invalidations': self._invalidation_stats['total_invalidations'],
            'by_strategy': dict(self._invalidation_stats['by_strategy']),
            'by_database': dict(self._invalidation_stats['by_database']),
            'by_table': dict(self._invalidation_stats['by_table']),
            'errors': self._invalidation_stats['errors'],
            'active_rules': len([r for r in self._rules if r.enabled]),
            'total_rules': len(self._rules),
            'strategies': list(self._strategies.keys())
        }
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired entries."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                if not self._running:
                    break
                
                # Clean up expired entries
                await self.invalidate_expired()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying


class InvalidationStrategyInterface(ABC):
    """Abstract interface for invalidation strategies."""
    
    def __init__(self, config: CacheConfig, backends: Dict[str, CacheBackendInterface]):
        self.config = config
        self.backends = backends
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the strategy."""
        pass
    
    @abstractmethod
    async def invalidate(self, criteria: Any, database_name: Optional[str] = None) -> int:
        """Invalidate entries based on criteria."""
        pass


class TagBasedInvalidation(InvalidationStrategyInterface):
    """Tag-based cache invalidation strategy."""
    
    async def initialize(self) -> None:
        """Initialize tag-based invalidation."""
        pass
    
    async def invalidate(self, tags: List[str], database_name: Optional[str] = None) -> int:
        """Invalidate entries by tags."""
        total_invalidated = 0
        
        if database_name and database_name in self.backends:
            # Invalidate in specific database backend
            backend = self.backends[database_name]
            invalidated = await backend.delete_by_tags(tags)
            total_invalidated += invalidated
        else:
            # Invalidate across all backends
            for backend_name, backend in self.backends.items():
                if backend_name == 'default':
                    continue
                try:
                    invalidated = await backend.delete_by_tags(tags)
                    total_invalidated += invalidated
                except Exception as e:
                    # Log error but continue with other backends
                    logging.error(f"Failed to invalidate tags in backend {backend_name}: {e}")
        
        return total_invalidated


class TimeBasedInvalidation(InvalidationStrategyInterface):
    """Time-based cache invalidation strategy."""
    
    async def initialize(self) -> None:
        """Initialize time-based invalidation."""
        pass
    
    async def invalidate(self, criteria: Any, database_name: Optional[str] = None) -> int:
        """Not used for time-based invalidation."""
        return 0
    
    async def cleanup_expired(self) -> int:
        """Clean up expired entries across all backends."""
        total_cleaned = 0
        
        for backend_name, backend in self.backends.items():
            try:
                # This would require backend support for expired entry cleanup
                # For now, we'll rely on backend's internal cleanup mechanisms
                stats = await backend.get_stats()
                # Implementation would depend on backend capabilities
                pass
            except Exception as e:
                logging.error(f"Failed to cleanup expired entries in backend {backend_name}: {e}")
        
        return total_cleaned


class EventBasedInvalidation(InvalidationStrategyInterface):
    """Event-based cache invalidation strategy."""
    
    def __init__(self, config: CacheConfig, backends: Dict[str, CacheBackendInterface]):
        super().__init__(config, backends)
        self._event_mapping = {
            'table_insert': self._handle_table_insert,
            'table_update': self._handle_table_update,
            'table_delete': self._handle_table_delete,
            'schema_change': self._handle_schema_change
        }
    
    async def initialize(self) -> None:
        """Initialize event-based invalidation."""
        pass
    
    async def invalidate(self, criteria: Any, database_name: Optional[str] = None) -> int:
        """Not used directly for event-based invalidation."""
        return 0
    
    async def handle_event(self, event: InvalidationEvent) -> int:
        """Handle database event and perform appropriate invalidation."""
        handler = self._event_mapping.get(event.event_type)
        if handler:
            return await handler(event)
        else:
            # Default handling - invalidate by tags
            if event.tags:
                tag_strategy = TagBasedInvalidation(self.config, self.backends)
                return await tag_strategy.invalidate(event.tags, event.database_name)
        
        return 0
    
    async def _handle_table_insert(self, event: InvalidationEvent) -> int:
        """Handle table insert event."""
        # Invalidate count queries and aggregations for the table
        tags_to_invalidate = [
            f"db:{event.database_name}",
            f"table:{event.table_name}",
            f"query_type:COUNT",
            f"query_type:AGGREGATE"
        ]
        
        tag_strategy = TagBasedInvalidation(self.config, self.backends)
        return await tag_strategy.invalidate(tags_to_invalidate, event.database_name)
    
    async def _handle_table_update(self, event: InvalidationEvent) -> int:
        """Handle table update event."""
        # Invalidate all queries for the affected table
        tags_to_invalidate = [
            f"db:{event.database_name}",
            f"table:{event.table_name}"
        ]
        
        # Add specific keys if provided
        if event.affected_keys:
            tags_to_invalidate.extend(event.affected_keys)
        
        tag_strategy = TagBasedInvalidation(self.config, self.backends)
        return await tag_strategy.invalidate(tags_to_invalidate, event.database_name)
    
    async def _handle_table_delete(self, event: InvalidationEvent) -> int:
        """Handle table delete event."""
        # Invalidate all queries for the affected table
        tags_to_invalidate = [
            f"db:{event.database_name}",
            f"table:{event.table_name}",
            f"query_type:COUNT",
            f"query_type:AGGREGATE"
        ]
        
        tag_strategy = TagBasedInvalidation(self.config, self.backends)
        return await tag_strategy.invalidate(tags_to_invalidate, event.database_name)
    
    async def _handle_schema_change(self, event: InvalidationEvent) -> int:
        """Handle schema change event."""
        # Invalidate all queries for the database
        tags_to_invalidate = [f"db:{event.database_name}"]
        
        if event.table_name:
            tags_to_invalidate.append(f"table:{event.table_name}")
        
        tag_strategy = TagBasedInvalidation(self.config, self.backends)
        return await tag_strategy.invalidate(tags_to_invalidate, event.database_name)
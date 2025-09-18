"""
APM Manager for FastAPI Microservices SDK.

This module provides the main manager for Application Performance Monitoring,
coordinating all APM components and providing a unified interface.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
import logging

from .config import APMConfig
from .exceptions import APMError
from .profiler import PerformanceProfiler, create_performance_profiler, ProfilingType
from .baseline import BaselineManager, create_baseline_manager
from .sla import SLAMonitor, create_sla_monitor, SLAMetricType
from .bottleneck import BottleneckDetector, create_bottleneck_detector
from .trends import TrendAnalyzer, create_trend_analyzer
from .regression import RegressionDetector, create_regression_detector


class APMManager:
    """Main APM manager coordinating all performance monitoring components."""
    
    def __init__(self, config: APMConfig):
        """Initialize APM manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.profiler = create_performance_profiler(config)
        self.baseline_manager = create_baseline_manager(config)
        self.sla_monitor = create_sla_monitor(config)
        self.bottleneck_detector = create_bottleneck_detector(config)
        self.trend_analyzer = create_trend_analyzer(config)
        self.regression_detector = create_regression_detector(config)
        
        # State management
        self.is_running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # Performance data aggregation
        self.performance_summary: Dict[str, Any] = {}
        
        # Callbacks
        self.performance_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
    
    async def start(self):
        """Start the APM system."""
        try:
            if self.is_running:
                self.logger.warning("APM manager is already running")
                return
            
            self.logger.info("Starting APM manager...")
            
            # Start all components
            await self.profiler.start()
            await self.baseline_manager.start()
            await self.sla_monitor.start()
            await self.bottleneck_detector.start()
            await self.trend_analyzer.start()
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._data_aggregation_loop()),
                asyncio.create_task(self._health_monitoring_loop()),
                asyncio.create_task(self._performance_summary_loop())
            ]
            
            self.is_running = True
            self.logger.info("APM manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting APM manager: {e}")
            raise APMError(
                f"Failed to start APM manager: {e}",
                apm_operation="system_start",
                original_error=e
            )
    
    async def stop(self):
        """Stop the APM system."""
        try:
            if not self.is_running:
                return
            
            self.logger.info("Stopping APM manager...")
            
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # Stop all components
            await self.profiler.stop()
            await self.baseline_manager.stop()
            await self.sla_monitor.stop()
            await self.bottleneck_detector.stop()
            await self.trend_analyzer.stop()
            
            self.is_running = False
            self.background_tasks.clear()
            
            self.logger.info("APM manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping APM manager: {e}")
    
    async def record_performance_metric(self, metric_name: str, value: float, metric_type: Optional[str] = None, timestamp: Optional[datetime] = None):
        """Record performance metric across all relevant components."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Add to baseline manager
            await self.baseline_manager.add_metric_data(metric_name, value, timestamp)
            
            # Add to trend analyzer
            await self.trend_analyzer.add_metric_data(metric_name, value, timestamp)
            
            # Add to SLA monitor if it's an SLA metric
            if metric_type:
                try:
                    sla_metric_type = SLAMetricType(metric_type)
                    await self.sla_monitor.record_metric(sla_metric_type, value, timestamp)
                except ValueError:
                    pass  # Not an SLA metric type
            
            # Add to regression detector for current version
            current_version = getattr(self.regression_detector, 'current_version', 'unknown')
            if current_version != 'unknown':
                await self.regression_detector.add_performance_data(current_version, metric_name, value)
            
        except Exception as e:
            self.logger.error(f"Error recording performance metric: {e}")
            raise APMError(
                f"Failed to record performance metric: {e}",
                apm_operation="metric_recording",
                original_error=e
            )
    
    async def record_resource_metric(self, resource_name: str, metric_type: str, value: float, timestamp: Optional[datetime] = None):
        """Record resource utilization metric."""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Add to bottleneck detector
            await self.bottleneck_detector.add_resource_metric(resource_name, metric_type, value, timestamp)
            
            # Also record as performance metric
            metric_name = f"{resource_name}_{metric_type}"
            await self.record_performance_metric(metric_name, value, timestamp=timestamp)
            
        except Exception as e:
            self.logger.error(f"Error recording resource metric: {e}")
            raise APMError(
                f"Failed to record resource metric: {e}",
                apm_operation="resource_metric_recording",
                original_error=e
            )
    
    async def start_profiling(self, profiling_type: ProfilingType, duration: Optional[timedelta] = None) -> str:
        """Start performance profiling."""
        try:
            return await self.profiler.start_profiling(profiling_type, duration)
        except Exception as e:
            self.logger.error(f"Error starting profiling: {e}")
            raise APMError(
                f"Failed to start profiling: {e}",
                apm_operation="profiling",
                component="profiler",
                original_error=e
            )
    
    async def stop_profiling(self, profile_id: str):
        """Stop performance profiling."""
        try:
            return await self.profiler.stop_profiling(profile_id)
        except Exception as e:
            self.logger.error(f"Error stopping profiling: {e}")
            raise APMError(
                f"Failed to stop profiling: {e}",
                apm_operation="profiling",
                component="profiler",
                original_error=e
            )
    
    async def detect_bottlenecks(self):
        """Detect performance bottlenecks."""
        try:
            return await self.bottleneck_detector.detect_bottlenecks()
        except Exception as e:
            self.logger.error(f"Error detecting bottlenecks: {e}")
            raise APMError(
                f"Failed to detect bottlenecks: {e}",
                apm_operation="bottleneck_detection",
                component="bottleneck_detector",
                original_error=e
            )
    
    async def generate_sla_report(self, period: timedelta):
        """Generate SLA compliance report."""
        try:
            return await self.sla_monitor.generate_sla_report(period)
        except Exception as e:
            self.logger.error(f"Error generating SLA report: {e}")
            raise APMError(
                f"Failed to generate SLA report: {e}",
                apm_operation="sla_reporting",
                component="sla_monitor",
                original_error=e
            )
    
    async def analyze_trends(self, metric_name: str):
        """Analyze performance trends."""
        try:
            return await self.trend_analyzer.analyze_trend(metric_name)
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            raise APMError(
                f"Failed to analyze trends: {e}",
                apm_operation="trend_analysis",
                component="trend_analyzer",
                original_error=e
            )
    
    async def detect_regressions(self, baseline_version: str, current_version: str):
        """Detect performance regressions."""
        try:
            await self.regression_detector.set_current_version(current_version)
            return await self.regression_detector.detect_all_regressions(baseline_version, current_version)
        except Exception as e:
            self.logger.error(f"Error detecting regressions: {e}")
            raise APMError(
                f"Failed to detect regressions: {e}",
                apm_operation="regression_detection",
                component="regression_detector",
                original_error=e
            )
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            # Get component health
            profiler_health = await self.profiler.get_profiler_health()
            baseline_health = await self.baseline_manager.get_baseline_health()
            sla_health = await self.sla_monitor.get_sla_health()
            bottleneck_health = await self.bottleneck_detector.get_detector_health()
            trend_health = await self.trend_analyzer.get_analyzer_health()
            regression_health = await self.regression_detector.get_detector_health()
            
            # Get recent performance data
            active_bottlenecks = await self.bottleneck_detector.get_active_bottlenecks()
            sla_violations = await self.sla_monitor.get_active_violations()
            recent_trends = await self.trend_analyzer.get_trend_history(limit=10)
            
            return {
                'system_status': 'healthy' if self.is_running else 'stopped',
                'components': {
                    'profiler': profiler_health,
                    'baseline_manager': baseline_health,
                    'sla_monitor': sla_health,
                    'bottleneck_detector': bottleneck_health,
                    'trend_analyzer': trend_health,
                    'regression_detector': regression_health
                },
                'performance_issues': {
                    'active_bottlenecks': len(active_bottlenecks),
                    'sla_violations': len(sla_violations),
                    'performance_trends': len(recent_trends)
                },
                'summary': self.performance_summary
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {
                'system_status': 'error',
                'error': str(e)
            }
    
    async def set_performance_baseline(self, version: str, metrics_data: Dict[str, List[float]]):
        """Set performance baseline for regression detection."""
        try:
            await self.regression_detector.set_baseline_version(version, metrics_data)
            
            # Also establish baselines in baseline manager
            for metric_name, values in metrics_data.items():
                for value in values:
                    await self.baseline_manager.add_metric_data(metric_name, value)
                
                # Force baseline establishment
                await self.baseline_manager.establish_baseline(metric_name, force=True)
            
        except Exception as e:
            self.logger.error(f"Error setting performance baseline: {e}")
            raise APMError(
                f"Failed to set performance baseline: {e}",
                apm_operation="baseline_setting",
                original_error=e
            )
    
    def add_performance_callback(self, callback: Callable):
        """Add callback for performance events."""
        self.performance_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for performance alerts."""
        self.alert_callbacks.append(callback)
    
    async def _data_aggregation_loop(self):
        """Background loop for data aggregation."""
        while self.is_running:
            try:
                # Aggregate data every 5 minutes
                await asyncio.sleep(300)
                
                if not self.is_running:
                    break
                
                # Perform cross-component data sharing
                await self._aggregate_performance_data()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in data aggregation loop: {e}")
                await asyncio.sleep(60)
    
    async def _health_monitoring_loop(self):
        """Background loop for health monitoring."""
        while self.is_running:
            try:
                # Monitor health every minute
                await asyncio.sleep(60)
                
                if not self.is_running:
                    break
                
                # Check component health and trigger alerts if needed
                await self._monitor_component_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _performance_summary_loop(self):
        """Background loop for performance summary updates."""
        while self.is_running:
            try:
                # Update summary every 10 minutes
                await asyncio.sleep(600)
                
                if not self.is_running:
                    break
                
                # Update performance summary
                await self._update_performance_summary()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in performance summary loop: {e}")
                await asyncio.sleep(60)
    
    async def _aggregate_performance_data(self):
        """Aggregate performance data across components."""
        try:
            # This could implement cross-component data sharing
            # For example, sharing bottleneck detection results with trend analyzer
            pass
        except Exception as e:
            self.logger.error(f"Error aggregating performance data: {e}")
    
    async def _monitor_component_health(self):
        """Monitor health of all components."""
        try:
            # Check if any component is unhealthy and trigger alerts
            components = {
                'profiler': self.profiler,
                'baseline_manager': self.baseline_manager,
                'sla_monitor': self.sla_monitor,
                'bottleneck_detector': self.bottleneck_detector,
                'trend_analyzer': self.trend_analyzer
            }
            
            for name, component in components.items():
                if hasattr(component, 'is_running') and not component.is_running:
                    self.logger.warning(f"Component {name} is not running")
                    
                    # Trigger alert callbacks
                    for callback in self.alert_callbacks:
                        try:
                            await callback(f"APM component {name} is not running")
                        except Exception as e:
                            self.logger.error(f"Error in alert callback: {e}")
        
        except Exception as e:
            self.logger.error(f"Error monitoring component health: {e}")
    
    async def _update_performance_summary(self):
        """Update performance summary."""
        try:
            # Get recent performance metrics
            active_bottlenecks = await self.bottleneck_detector.get_active_bottlenecks()
            sla_violations = await self.sla_monitor.get_active_violations()
            
            # Update summary
            self.performance_summary = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'active_issues': len(active_bottlenecks) + len(sla_violations),
                'bottlenecks': len(active_bottlenecks),
                'sla_violations': len(sla_violations),
                'overall_health': 'healthy' if len(active_bottlenecks) == 0 and len(sla_violations) == 0 else 'degraded'
            }
            
        except Exception as e:
            self.logger.error(f"Error updating performance summary: {e}")


def create_apm_manager(config: APMConfig) -> APMManager:
    """Create APM manager instance."""
    return APMManager(config)
"""
Template Analytics - Advanced analytics system for template usage and performance
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class TemplateUsageEvent:
    template_id: str
    template_name: str
    user_id: str
    event_type: str  # 'generate', 'edit', 'delete', 'view'
    timestamp: datetime
    parameters: Dict[str, Any]
    execution_time: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class UsageMetrics:
    total_uses: int
    unique_users: int
    success_rate: float
    avg_execution_time: float
    most_common_parameters: Dict[str, int]
    usage_by_hour: Dict[int, int]
    usage_by_day: Dict[str, int]

@dataclass
class PerformanceMetrics:
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    p95_execution_time: float
    error_rate: float
    throughput: float  # uses per minute
    resource_usage: Dict[str, float]

@dataclass
class TrendData:
    period: str
    usage_count: int
    unique_users: int
    success_rate: float
    avg_execution_time: float

class TemplateAnalytics:
    """Advanced analytics system for template usage and performance"""
    
    def __init__(self):
        self.events: List[TemplateUsageEvent] = []
        self.performance_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
    async def track_event(self, event: TemplateUsageEvent) -> None:
        """Track a template usage event"""
        try:
            self.events.append(event)
            
            # Keep only last 10000 events to prevent memory issues
            if len(self.events) > 10000:
                self.events = self.events[-10000:]
                
            # Clear cache when new events are added
            self.performance_cache.clear()
            
            logger.info(f"Tracked event: {event.event_type} for template {event.template_id}")
            
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
    
    def get_usage_metrics(self, template_id: str, days: int = 30) -> UsageMetrics:
        """Get usage metrics for a template"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_events = [
                event for event in self.events
                if event.template_id == template_id and event.timestamp >= cutoff_date
            ]
            
            if not filtered_events:
                return UsageMetrics(0, 0, 0.0, 0.0, {}, {}, {})
            
            total_uses = len(filtered_events)
            unique_users = len(set(event.user_id for event in filtered_events))
            successful_events = [event for event in filtered_events if event.success]
            success_rate = len(successful_events) / total_uses if total_uses > 0 else 0.0
            
            avg_execution_time = sum(event.execution_time for event in filtered_events) / total_uses
            
            # Most common parameters
            all_params = []
            for event in filtered_events:
                all_params.extend(event.parameters.keys())
            most_common_parameters = dict(Counter(all_params).most_common(10))
            
            # Usage by hour
            usage_by_hour = defaultdict(int)
            for event in filtered_events:
                usage_by_hour[event.timestamp.hour] += 1
            
            # Usage by day
            usage_by_day = defaultdict(int)
            for event in filtered_events:
                day_key = event.timestamp.strftime('%Y-%m-%d')
                usage_by_day[day_key] += 1
            
            return UsageMetrics(
                total_uses=total_uses,
                unique_users=unique_users,
                success_rate=success_rate,
                avg_execution_time=avg_execution_time,
                most_common_parameters=most_common_parameters,
                usage_by_hour=dict(usage_by_hour),
                usage_by_day=dict(usage_by_day)
            )
            
        except Exception as e:
            logger.error(f"Failed to get usage metrics: {e}")
            return UsageMetrics(0, 0, 0.0, 0.0, {}, {}, {})
    
    def get_performance_metrics(self, template_id: str, days: int = 30) -> PerformanceMetrics:
        """Get performance metrics for a template"""
        try:
            cache_key = f"{template_id}_{days}"
            if cache_key in self.performance_cache:
                cached_data, timestamp = self.performance_cache[cache_key]
                if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                    return cached_data
            
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_events = [
                event for event in self.events
                if event.template_id == template_id and event.timestamp >= cutoff_date
            ]
            
            if not filtered_events:
                return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {})
            
            execution_times = [event.execution_time for event in filtered_events]
            execution_times.sort()
            
            avg_execution_time = sum(execution_times) / len(execution_times)
            min_execution_time = min(execution_times)
            max_execution_time = max(execution_times)
            
            # Calculate 95th percentile
            p95_index = int(0.95 * len(execution_times))
            p95_execution_time = execution_times[p95_index] if p95_index < len(execution_times) else max_execution_time
            
            # Error rate
            failed_events = [event for event in filtered_events if not event.success]
            error_rate = len(failed_events) / len(filtered_events) if filtered_events else 0.0
            
            # Throughput (uses per minute)
            time_span_minutes = days * 24 * 60
            throughput = len(filtered_events) / time_span_minutes if time_span_minutes > 0 else 0.0
            
            # Resource usage (mock data for now)
            resource_usage = {
                "cpu_avg": 25.5,
                "memory_avg": 128.0,
                "disk_io": 15.2
            }
            
            metrics = PerformanceMetrics(
                avg_execution_time=avg_execution_time,
                min_execution_time=min_execution_time,
                max_execution_time=max_execution_time,
                p95_execution_time=p95_execution_time,
                error_rate=error_rate,
                throughput=throughput,
                resource_usage=resource_usage
            )
            
            # Cache the result
            self.performance_cache[cache_key] = (metrics, datetime.now())
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {})
    
    def get_trend_analysis(self, template_id: str, days: int = 30) -> List[TrendData]:
        """Get trend analysis for a template"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_events = [
                event for event in self.events
                if event.template_id == template_id and event.timestamp >= cutoff_date
            ]
            
            # Group by day
            daily_data = defaultdict(list)
            for event in filtered_events:
                day_key = event.timestamp.strftime('%Y-%m-%d')
                daily_data[day_key].append(event)
            
            trend_data = []
            for day, events in daily_data.items():
                successful_events = [e for e in events if e.success]
                success_rate = len(successful_events) / len(events) if events else 0.0
                avg_execution_time = sum(e.execution_time for e in events) / len(events) if events else 0.0
                unique_users = len(set(e.user_id for e in events))
                
                trend_data.append(TrendData(
                    period=day,
                    usage_count=len(events),
                    unique_users=unique_users,
                    success_rate=success_rate,
                    avg_execution_time=avg_execution_time
                ))
            
            # Sort by date
            trend_data.sort(key=lambda x: x.period)
            
            return trend_data
            
        except Exception as e:
            logger.error(f"Failed to get trend analysis: {e}")
            return []
    
    def get_user_behavior_insights(self, template_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user behavior insights for a template"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_events = [
                event for event in self.events
                if event.template_id == template_id and event.timestamp >= cutoff_date
            ]
            
            if not filtered_events:
                return {}
            
            # User activity patterns
            user_activity = defaultdict(list)
            for event in filtered_events:
                user_activity[event.user_id].append(event)
            
            # Most active users
            most_active_users = sorted(
                user_activity.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:10]
            
            # Usage patterns by hour
            hourly_usage = defaultdict(int)
            for event in filtered_events:
                hourly_usage[event.timestamp.hour] += 1
            
            # Common parameter combinations
            param_combinations = defaultdict(int)
            for event in filtered_events:
                param_keys = tuple(sorted(event.parameters.keys()))
                param_combinations[param_keys] += 1
            
            return {
                "most_active_users": [
                    {"user_id": user_id, "usage_count": len(events)}
                    for user_id, events in most_active_users
                ],
                "peak_usage_hours": sorted(
                    hourly_usage.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "common_parameter_combinations": [
                    {"parameters": list(params), "count": count}
                    for params, count in sorted(
                        param_combinations.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                ],
                "user_retention": {
                    "total_users": len(user_activity),
                    "returning_users": len([
                        user_id for user_id, events in user_activity.items()
                        if len(events) > 1
                    ])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get user behavior insights: {e}")
            return {}
    
    def get_template_comparison(self, template_ids: List[str], days: int = 30) -> Dict[str, Any]:
        """Compare multiple templates"""
        try:
            comparison_data = {}
            
            for template_id in template_ids:
                usage_metrics = self.get_usage_metrics(template_id, days)
                performance_metrics = self.get_performance_metrics(template_id, days)
                
                comparison_data[template_id] = {
                    "usage": asdict(usage_metrics),
                    "performance": asdict(performance_metrics)
                }
            
            # Calculate rankings
            rankings = {
                "most_used": sorted(
                    template_ids,
                    key=lambda tid: comparison_data[tid]["usage"]["total_uses"],
                    reverse=True
                ),
                "best_performance": sorted(
                    template_ids,
                    key=lambda tid: comparison_data[tid]["performance"]["avg_execution_time"]
                ),
                "highest_success_rate": sorted(
                    template_ids,
                    key=lambda tid: comparison_data[tid]["usage"]["success_rate"],
                    reverse=True
                )
            }
            
            return {
                "templates": comparison_data,
                "rankings": rankings
            }
            
        except Exception as e:
            logger.error(f"Failed to get template comparison: {e}")
            return {}
    
    def generate_report(self, template_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive analytics report"""
        try:
            usage_metrics = self.get_usage_metrics(template_id, days)
            performance_metrics = self.get_performance_metrics(template_id, days)
            trend_analysis = self.get_trend_analysis(template_id, days)
            user_behavior = self.get_user_behavior_insights(template_id, days)
            
            return {
                "template_id": template_id,
                "report_period": f"{days} days",
                "generated_at": datetime.now().isoformat(),
                "usage_metrics": asdict(usage_metrics),
                "performance_metrics": asdict(performance_metrics),
                "trend_analysis": [asdict(trend) for trend in trend_analysis],
                "user_behavior": user_behavior,
                "summary": {
                    "total_uses": usage_metrics.total_uses,
                    "unique_users": usage_metrics.unique_users,
                    "success_rate": f"{usage_metrics.success_rate:.2%}",
                    "avg_execution_time": f"{usage_metrics.avg_execution_time:.2f}s",
                    "performance_score": self._calculate_performance_score(usage_metrics, performance_metrics)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {}
    
    def _calculate_performance_score(self, usage_metrics: UsageMetrics, performance_metrics: PerformanceMetrics) -> int:
        """Calculate a performance score from 0-100"""
        try:
            # Weighted scoring
            success_score = usage_metrics.success_rate * 40  # 40% weight
            speed_score = max(0, (5.0 - performance_metrics.avg_execution_time) / 5.0) * 30  # 30% weight
            usage_score = min(usage_metrics.total_uses / 100, 1.0) * 20  # 20% weight
            error_score = max(0, (1.0 - performance_metrics.error_rate)) * 10  # 10% weight
            
            total_score = success_score + speed_score + usage_score + error_score
            return int(min(100, max(0, total_score)))
            
        except Exception as e:
            logger.error(f"Failed to calculate performance score: {e}")
            return 0
    
    def export_analytics_data(self, template_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Export analytics data for external analysis"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            if template_id:
                filtered_data = [
                    event for event in self.events
                    if event.template_id == template_id and event.timestamp >= cutoff_date
                ]
            else:
                filtered_data = [
                    event for event in self.events
                    if event.timestamp >= cutoff_date
                ]
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "period_days": days,
                "template_id": template_id,
                "total_events": len(filtered_data),
                "events": [
                    {
                        "template_id": record.template_id,
                        "template_name": record.template_name,
                        "user_id": record.user_id,
                        "event_type": record.event_type,
                        "timestamp": record.timestamp.isoformat(),
                        "parameters": record.parameters,
                        "execution_time": record.execution_time,
                        "success": record.success,
                        "parameters_count": len(record.parameters)
                    }
                    for record in filtered_data
                ]
            }
            
            if template_id:
                export_data.update({
                    "usage_metrics": asdict(self.get_usage_metrics(template_id)),
                    "performance_metrics": asdict(self.get_performance_metrics(template_id)),
                    "trend_analysis": [asdict(trend) for trend in self.get_trend_analysis(template_id)],
                    "user_behavior": self.get_user_behavior_insights(template_id)
                })
            
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export analytics data: {e}")
            return {}
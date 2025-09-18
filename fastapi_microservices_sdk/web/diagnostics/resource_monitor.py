"""
Resource Monitor - Advanced system resource monitoring and analysis
"""
import psutil
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    create_time: datetime
    cmdline: List[str]

@dataclass
class NetworkConnection:
    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    status: str
    pid: Optional[int]

@dataclass
class DiskUsage:
    device: str
    mountpoint: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float

class ResourceMonitor:
    """
    Advanced system resource monitoring with historical data and analysis.
    
    Features:
    - Real-time resource monitoring
    - Historical data tracking
    - Process monitoring and analysis
    - Network connection monitoring
    - Disk usage monitoring
    - Resource trend analysis
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.cpu_history = deque(maxlen=history_size)
        self.memory_history = deque(maxlen=history_size)
        self.disk_history = deque(maxlen=history_size)
        self.network_history = deque(maxlen=history_size)
        self.process_history = deque(maxlen=100)  # Keep fewer process snapshots
        
        # Baseline measurements
        self.baseline_cpu = None
        self.baseline_memory = None
        self.baseline_established = False
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self, interval: int = 5) -> bool:
        """Start continuous resource monitoring"""
        try:
            if self.monitoring_active:
                return True
            
            self.monitoring_active = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
            
            logger.info(f"Resource monitoring started with {interval}s interval")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start resource monitoring: {e}")
            return False
    
    async def stop_monitoring(self) -> bool:
        """Stop continuous resource monitoring"""
        try:
            self.monitoring_active = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Resource monitoring stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop resource monitoring: {e}")
            return False
    
    async def _monitoring_loop(self, interval: int) -> None:
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect resource metrics
                await self.collect_metrics()
                
                # Establish baseline after initial samples
                if not self.baseline_established and len(self.cpu_history) >= 10:
                    self._establish_baseline()
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            timestamp = datetime.now()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            cpu_data = {
                "timestamp": timestamp,
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": cpu_freq.current if cpu_freq else None,
                "per_cpu": psutil.cpu_percent(percpu=True)
            }
            self.cpu_history.append(cpu_data)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_data = {
                "timestamp": timestamp,
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "percent": memory.percent,
                "swap_total_gb": swap.total / (1024**3),
                "swap_used_gb": swap.used / (1024**3),
                "swap_percent": swap.percent
            }
            self.memory_history.append(memory_data)
            
            # Disk metrics
            disk_usage = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage.append(DiskUsage(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                        total_gb=usage.total / (1024**3),
                        used_gb=usage.used / (1024**3),
                        free_gb=usage.free / (1024**3),
                        percent=usage.percent
                    ))
                except PermissionError:
                    continue
            
            disk_io = psutil.disk_io_counters()
            disk_data = {
                "timestamp": timestamp,
                "partitions": [asdict(du) for du in disk_usage],
                "io_read_bytes": disk_io.read_bytes if disk_io else 0,
                "io_write_bytes": disk_io.write_bytes if disk_io else 0,
                "io_read_count": disk_io.read_count if disk_io else 0,
                "io_write_count": disk_io.write_count if disk_io else 0
            }
            self.disk_history.append(disk_data)
            
            # Network metrics
            network_io = psutil.net_io_counters()
            network_connections = self._get_network_connections()
            
            network_data = {
                "timestamp": timestamp,
                "bytes_sent": network_io.bytes_sent,
                "bytes_recv": network_io.bytes_recv,
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
                "connections": len(network_connections),
                "established_connections": len([c for c in network_connections if c.status == "ESTABLISHED"])
            }
            self.network_history.append(network_data)
            
            return {
                "cpu": cpu_data,
                "memory": memory_data,
                "disk": disk_data,
                "network": network_data,
                "timestamp": timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get the most recent metrics"""
        try:
            return {
                "cpu": self.cpu_history[-1] if self.cpu_history else None,
                "memory": self.memory_history[-1] if self.memory_history else None,
                "disk": self.disk_history[-1] if self.disk_history else None,
                "network": self.network_history[-1] if self.network_history else None
            }
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return {}
    
    def get_historical_metrics(self, minutes: int = 60) -> Dict[str, List[Any]]:
        """Get historical metrics for the specified time period"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            cpu_data = [m for m in self.cpu_history if m["timestamp"] > cutoff_time]
            memory_data = [m for m in self.memory_history if m["timestamp"] > cutoff_time]
            disk_data = [m for m in self.disk_history if m["timestamp"] > cutoff_time]
            network_data = [m for m in self.network_history if m["timestamp"] > cutoff_time]
            
            return {
                "cpu": cpu_data,
                "memory": memory_data,
                "disk": disk_data,
                "network": network_data,
                "period_minutes": minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return {}
    
    def get_top_processes(self, limit: int = 10, sort_by: str = "cpu") -> List[ProcessInfo]:
        """Get top processes by CPU or memory usage"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'memory_info', 'status', 'create_time', 'cmdline']):
                try:
                    info = proc.info
                    processes.append(ProcessInfo(
                        pid=info['pid'],
                        name=info['name'],
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_percent=info['memory_percent'] or 0.0,
                        memory_mb=info['memory_info'].rss / (1024*1024) if info['memory_info'] else 0.0,
                        status=info['status'],
                        create_time=datetime.fromtimestamp(info['create_time']),
                        cmdline=info['cmdline'] or []
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort processes
            if sort_by == "memory":
                processes.sort(key=lambda p: p.memory_percent, reverse=True)
            else:
                processes.sort(key=lambda p: p.cpu_percent, reverse=True)
            
            return processes[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get top processes: {e}")
            return []
    
    def _get_network_connections(self) -> List[NetworkConnection]:
        """Get current network connections"""
        try:
            connections = []
            
            for conn in psutil.net_connections():
                if conn.laddr and conn.raddr:
                    connections.append(NetworkConnection(
                        local_address=conn.laddr.ip,
                        local_port=conn.laddr.port,
                        remote_address=conn.raddr.ip,
                        remote_port=conn.raddr.port,
                        status=conn.status,
                        pid=conn.pid
                    ))
            
            return connections
            
        except Exception as e:
            logger.error(f"Failed to get network connections: {e}")
            return []
    
    def get_resource_trends(self, minutes: int = 60) -> Dict[str, Any]:
        """Analyze resource usage trends"""
        try:
            historical = self.get_historical_metrics(minutes)
            
            if not historical["cpu"] or not historical["memory"]:
                return {"error": "Insufficient data for trend analysis"}
            
            # CPU trend analysis
            cpu_values = [m["percent"] for m in historical["cpu"]]
            cpu_trend = self._calculate_trend(cpu_values)
            cpu_avg = sum(cpu_values) / len(cpu_values)
            cpu_max = max(cpu_values)
            cpu_min = min(cpu_values)
            
            # Memory trend analysis
            memory_values = [m["percent"] for m in historical["memory"]]
            memory_trend = self._calculate_trend(memory_values)
            memory_avg = sum(memory_values) / len(memory_values)
            memory_max = max(memory_values)
            memory_min = min(memory_values)
            
            # Disk trend analysis
            disk_values = []
            if historical["disk"]:
                for disk_data in historical["disk"]:
                    if disk_data["partitions"]:
                        # Use root partition or first partition
                        root_partition = next(
                            (p for p in disk_data["partitions"] if p["mountpoint"] == "/"),
                            disk_data["partitions"][0]
                        )
                        disk_values.append(root_partition["percent"])
            
            disk_trend = self._calculate_trend(disk_values) if disk_values else "stable"
            disk_avg = sum(disk_values) / len(disk_values) if disk_values else 0
            
            return {
                "period_minutes": minutes,
                "cpu": {
                    "trend": cpu_trend,
                    "average": round(cpu_avg, 2),
                    "maximum": round(cpu_max, 2),
                    "minimum": round(cpu_min, 2),
                    "volatility": round(self._calculate_volatility(cpu_values), 2)
                },
                "memory": {
                    "trend": memory_trend,
                    "average": round(memory_avg, 2),
                    "maximum": round(memory_max, 2),
                    "minimum": round(memory_min, 2),
                    "volatility": round(self._calculate_volatility(memory_values), 2)
                },
                "disk": {
                    "trend": disk_trend,
                    "average": round(disk_avg, 2)
                },
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze resource trends: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        # Calculate slope
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        # Determine trend based on slope
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _establish_baseline(self) -> None:
        """Establish baseline measurements for anomaly detection"""
        try:
            if len(self.cpu_history) >= 10 and len(self.memory_history) >= 10:
                cpu_values = [m["percent"] for m in list(self.cpu_history)[-10:]]
                memory_values = [m["percent"] for m in list(self.memory_history)[-10:]]
                
                self.baseline_cpu = {
                    "average": sum(cpu_values) / len(cpu_values),
                    "std_dev": self._calculate_volatility(cpu_values)
                }
                
                self.baseline_memory = {
                    "average": sum(memory_values) / len(memory_values),
                    "std_dev": self._calculate_volatility(memory_values)
                }
                
                self.baseline_established = True
                logger.info("Resource monitoring baseline established")
                
        except Exception as e:
            logger.error(f"Failed to establish baseline: {e}")
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect resource usage anomalies based on baseline"""
        anomalies = []
        
        try:
            if not self.baseline_established or not self.cpu_history or not self.memory_history:
                return anomalies
            
            current_cpu = self.cpu_history[-1]["percent"]
            current_memory = self.memory_history[-1]["percent"]
            
            # CPU anomaly detection
            cpu_threshold = self.baseline_cpu["average"] + (2 * self.baseline_cpu["std_dev"])
            if current_cpu > cpu_threshold:
                anomalies.append({
                    "type": "cpu_spike",
                    "severity": "warning" if current_cpu < cpu_threshold * 1.5 else "critical",
                    "current_value": current_cpu,
                    "baseline_average": self.baseline_cpu["average"],
                    "threshold": cpu_threshold,
                    "message": f"CPU usage spike detected: {current_cpu:.1f}% (baseline: {self.baseline_cpu['average']:.1f}%)",
                    "timestamp": datetime.now().isoformat()
                })
            
            # Memory anomaly detection
            memory_threshold = self.baseline_memory["average"] + (2 * self.baseline_memory["std_dev"])
            if current_memory > memory_threshold:
                anomalies.append({
                    "type": "memory_spike",
                    "severity": "warning" if current_memory < memory_threshold * 1.5 else "critical",
                    "current_value": current_memory,
                    "baseline_average": self.baseline_memory["average"],
                    "threshold": memory_threshold,
                    "message": f"Memory usage spike detected: {current_memory:.1f}% (baseline: {self.baseline_memory['average']:.1f}%)",
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
        
        return anomalies
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive resource summary"""
        try:
            current = self.get_current_metrics()
            trends = self.get_resource_trends(60)
            top_processes = self.get_top_processes(5)
            anomalies = self.detect_anomalies()
            
            return {
                "current_metrics": current,
                "trends": trends,
                "top_processes": [asdict(p) for p in top_processes],
                "anomalies": anomalies,
                "monitoring_status": {
                    "active": self.monitoring_active,
                    "baseline_established": self.baseline_established,
                    "history_size": len(self.cpu_history)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource summary: {e}")
            return {"error": str(e)}
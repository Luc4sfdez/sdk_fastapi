"""
Monitor command for FastAPI Microservices SDK CLI.
"""

import time
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich import print as rprint

console = Console()
monitor_app = typer.Typer(name="monitor", help="Monitor services and infrastructure")


@monitor_app.command("health")
def monitor_health(
    service_url: str = typer.Option("http://localhost:8000", help="Service URL to monitor"),
    interval: int = typer.Option(5, help="Check interval in seconds"),
    timeout: int = typer.Option(10, help="Request timeout in seconds"),
    continuous: bool = typer.Option(False, help="Continuous monitoring"),
    alert_threshold: int = typer.Option(3, help="Failed checks before alert")
):
    """Monitor service health status."""
    
    rprint(f"🏥 [blue]Monitoring health for: {service_url}[/blue]")
    rprint(f"⏱️  Check interval: {interval}s")
    
    failed_checks = 0
    check_count = 0
    
    def create_health_table(status: str, response_time: float, timestamp: str, details: Dict[str, Any] = None):
        table = Table(title="Service Health Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green" if status == "healthy" else "red")
        
        table.add_row("Status", status)
        table.add_row("Response Time", f"{response_time:.2f}ms")
        table.add_row("Last Check", timestamp)
        table.add_row("Failed Checks", str(failed_checks))
        table.add_row("Total Checks", str(check_count))
        
        if details:
            table.add_row("", "")  # Separator
            for key, value in details.items():
                table.add_row(key.title(), str(value))
        
        return table
    
    try:
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            try:
                start_time = time.time()
                
                with httpx.Client(timeout=timeout) as client:
                    response = client.get(f"{service_url}/health")
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    status = "healthy"
                    failed_checks = 0
                    
                    try:
                        health_data = response.json()
                        details = {
                            "version": health_data.get("version", "unknown"),
                            "uptime": health_data.get("uptime", "unknown"),
                            "database": health_data.get("database", "unknown"),
                            "dependencies": health_data.get("dependencies", "unknown")
                        }
                    except:
                        details = None
                else:
                    status = f"unhealthy (HTTP {response.status_code})"
                    failed_checks += 1
                    details = None
                
            except httpx.TimeoutException:
                status = "timeout"
                response_time = timeout * 1000
                failed_checks += 1
                details = None
                
            except httpx.ConnectError:
                status = "connection failed"
                response_time = 0
                failed_checks += 1
                details = None
                
            except Exception as e:
                status = f"error: {str(e)}"
                response_time = 0
                failed_checks += 1
                details = None
            
            # Display results
            table = create_health_table(status, response_time, timestamp, details)
            
            if continuous:
                console.clear()
                console.print(table)
                
                # Alert if threshold reached
                if failed_checks >= alert_threshold:
                    alert_panel = Panel(
                        f"🚨 ALERT: Service has failed {failed_checks} consecutive health checks!",
                        style="red",
                        title="Health Alert"
                    )
                    console.print(alert_panel)
            else:
                console.print(table)
                break
            
            if continuous:
                time.sleep(interval)
            else:
                break
                
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Health monitoring stopped by user[/yellow]")


@monitor_app.command("metrics")
def monitor_metrics(
    service_url: str = typer.Option("http://localhost:8000", help="Service URL to monitor"),
    metrics_endpoint: str = typer.Option("/metrics", help="Metrics endpoint path"),
    interval: int = typer.Option(10, help="Collection interval in seconds"),
    duration: int = typer.Option(60, help="Monitoring duration in seconds"),
    output_file: Optional[str] = typer.Option(None, help="Save metrics to file")
):
    """Monitor service metrics."""
    
    rprint(f"📊 [blue]Monitoring metrics for: {service_url}{metrics_endpoint}[/blue]")
    rprint(f"⏱️  Collection interval: {interval}s")
    rprint(f"⏳ Duration: {duration}s")
    
    metrics_data = []
    start_time = time.time()
    
    def create_metrics_table(current_metrics: Dict[str, Any]):
        table = Table(title="Service Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Type", style="yellow")
        
        for metric_name, metric_info in current_metrics.items():
            if isinstance(metric_info, dict):
                value = metric_info.get('value', 'N/A')
                metric_type = metric_info.get('type', 'unknown')
            else:
                value = metric_info
                metric_type = 'gauge'
            
            table.add_row(metric_name, str(value), metric_type)
        
        return table
    
    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Collecting metrics...", total=duration)
            
            while time.time() - start_time < duration:
                try:
                    with httpx.Client(timeout=10) as client:
                        response = client.get(f"{service_url}{metrics_endpoint}")
                    
                    if response.status_code == 200:
                        try:
                            # Try to parse as JSON
                            metrics = response.json()
                        except:
                            # Try to parse Prometheus format
                            metrics = _parse_prometheus_metrics(response.text)
                        
                        timestamp = datetime.now().isoformat()
                        metrics_data.append({
                            'timestamp': timestamp,
                            'metrics': metrics
                        })
                        
                        # Display current metrics
                        console.clear()
                        table = create_metrics_table(metrics)
                        console.print(table)
                        
                        # Update progress
                        elapsed = time.time() - start_time
                        progress.update(task, completed=elapsed)
                        
                    else:
                        rprint(f"⚠️  [yellow]Failed to fetch metrics: HTTP {response.status_code}[/yellow]")
                
                except Exception as e:
                    rprint(f"❌ [red]Error fetching metrics: {e}[/red]")
                
                time.sleep(interval)
        
        # Save metrics to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            rprint(f"💾 [green]Metrics saved to: {output_path}[/green]")
        
        # Show summary
        if metrics_data:
            rprint(f"✅ [green]Collected {len(metrics_data)} metric snapshots[/green]")
            _show_metrics_summary(metrics_data)
        
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Metrics monitoring stopped by user[/yellow]")


@monitor_app.command("logs")
def monitor_logs(
    service_path: str = typer.Option(".", help="Path to service directory"),
    log_file: Optional[str] = typer.Option(None, help="Specific log file to monitor"),
    follow: bool = typer.Option(True, help="Follow log file (tail -f)"),
    lines: int = typer.Option(50, help="Number of lines to show initially"),
    filter_level: Optional[str] = typer.Option(None, help="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    filter_pattern: Optional[str] = typer.Option(None, help="Filter by pattern (regex)")
):
    """Monitor service logs."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Find log file
    if log_file:
        log_path = service_path / log_file
    else:
        # Look for common log files
        possible_logs = [
            "app.log", "service.log", "application.log",
            "logs/app.log", "logs/service.log"
        ]
        
        log_path = None
        for log_name in possible_logs:
            candidate = service_path / log_name
            if candidate.exists():
                log_path = candidate
                break
        
        if not log_path:
            rprint("❌ [red]No log file found. Specify with --log-file[/red]")
            raise typer.Exit(1)
    
    if not log_path.exists():
        rprint(f"❌ [red]Log file '{log_path}' not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"📋 [blue]Monitoring logs: {log_path}[/blue]")
    if filter_level:
        rprint(f"🔍 Filter level: {filter_level}")
    if filter_pattern:
        rprint(f"🔍 Filter pattern: {filter_pattern}")
    
    try:
        import re
        
        # Read initial lines
        with open(log_path, 'r') as f:
            lines_list = f.readlines()
            initial_lines = lines_list[-lines:] if len(lines_list) > lines else lines_list
        
        # Display initial lines
        for line in initial_lines:
            _display_log_line(line.strip(), filter_level, filter_pattern)
        
        if follow:
            rprint("\n📡 [blue]Following log file... (Press Ctrl+C to stop)[/blue]")
            
            # Follow the file
            with open(log_path, 'r') as f:
                # Seek to end
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        _display_log_line(line.strip(), filter_level, filter_pattern)
                    else:
                        time.sleep(0.1)
    
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Log monitoring stopped by user[/yellow]")
    except Exception as e:
        rprint(f"❌ [red]Error monitoring logs: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("performance")
def monitor_performance(
    service_url: str = typer.Option("http://localhost:8000", help="Service URL to monitor"),
    endpoints: List[str] = typer.Option(["/health", "/docs"], help="Endpoints to test"),
    concurrent_requests: int = typer.Option(10, help="Number of concurrent requests"),
    duration: int = typer.Option(30, help="Test duration in seconds"),
    output_file: Optional[str] = typer.Option(None, help="Save results to file")
):
    """Monitor service performance and load testing."""
    
    rprint(f"⚡ [blue]Performance testing: {service_url}[/blue]")
    rprint(f"🎯 Endpoints: {', '.join(endpoints)}")
    rprint(f"🔄 Concurrent requests: {concurrent_requests}")
    rprint(f"⏳ Duration: {duration}s")
    
    results = []
    
    async def test_endpoint(endpoint: str, session: httpx.AsyncClient, semaphore: asyncio.Semaphore):
        async with semaphore:
            start_time = time.time()
            try:
                response = await session.get(f"{service_url}{endpoint}")
                response_time = (time.time() - start_time) * 1000
                
                return {
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code < 400,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return {
                    'endpoint': endpoint,
                    'status_code': 0,
                    'response_time': response_time,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
    
    async def run_performance_test():
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async with httpx.AsyncClient(timeout=30) as session:
            start_time = time.time()
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task("Running performance test...", total=duration)
                
                while time.time() - start_time < duration:
                    # Create tasks for all endpoints
                    tasks = []
                    for endpoint in endpoints:
                        task_coro = test_endpoint(endpoint, session, semaphore)
                        tasks.append(task_coro)
                    
                    # Execute tasks
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for result in batch_results:
                        if isinstance(result, dict):
                            results.append(result)
                    
                    # Update progress
                    elapsed = time.time() - start_time
                    progress.update(task, completed=elapsed)
                    
                    # Small delay between batches
                    await asyncio.sleep(0.1)
    
    try:
        # Run the performance test
        asyncio.run(run_performance_test())
        
        # Analyze results
        if results:
            _show_performance_results(results, endpoints)
            
            # Save results if requested
            if output_file:
                output_path = Path(output_file)
                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2)
                rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        else:
            rprint("❌ [red]No results collected[/red]")
    
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Performance test stopped by user[/yellow]")
    except Exception as e:
        rprint(f"❌ [red]Error during performance test: {e}[/red]")
        raise typer.Exit(1)


@monitor_app.command("dashboard")
def monitor_dashboard(
    service_url: str = typer.Option("http://localhost:8000", help="Service URL to monitor"),
    refresh_interval: int = typer.Option(5, help="Dashboard refresh interval in seconds"),
    show_metrics: bool = typer.Option(True, help="Show metrics panel"),
    show_health: bool = typer.Option(True, help="Show health panel"),
    show_logs: bool = typer.Option(False, help="Show recent logs panel")
):
    """Display a real-time monitoring dashboard."""
    
    rprint(f"📊 [blue]Starting monitoring dashboard for: {service_url}[/blue]")
    rprint("Press Ctrl+C to stop")
    
    def create_dashboard():
        panels = []
        
        if show_health:
            health_panel = _get_health_panel(service_url)
            panels.append(health_panel)
        
        if show_metrics:
            metrics_panel = _get_metrics_panel(service_url)
            panels.append(metrics_panel)
        
        if show_logs:
            logs_panel = _get_logs_panel()
            panels.append(logs_panel)
        
        return panels
    
    try:
        with Live(console=console, refresh_per_second=1/refresh_interval) as live:
            while True:
                panels = create_dashboard()
                
                # Combine panels
                if len(panels) == 1:
                    live.update(panels[0])
                else:
                    from rich.columns import Columns
                    live.update(Columns(panels))
                
                time.sleep(refresh_interval)
    
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Dashboard stopped by user[/yellow]")


def _parse_prometheus_metrics(text: str) -> Dict[str, Any]:
    """Parse Prometheus metrics format."""
    metrics = {}
    
    for line in text.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            try:
                if ' ' in line:
                    name, value = line.split(' ', 1)
                    # Remove labels if present
                    if '{' in name:
                        name = name.split('{')[0]
                    
                    try:
                        metrics[name] = float(value)
                    except ValueError:
                        metrics[name] = value
            except:
                continue
    
    return metrics


def _display_log_line(line: str, filter_level: Optional[str], filter_pattern: Optional[str]):
    """Display a log line with filtering."""
    import re
    
    # Apply level filter
    if filter_level:
        if filter_level.upper() not in line.upper():
            return
    
    # Apply pattern filter
    if filter_pattern:
        try:
            if not re.search(filter_pattern, line, re.IGNORECASE):
                return
        except re.error:
            pass  # Invalid regex, ignore filter
    
    # Color code by log level
    if 'ERROR' in line.upper():
        console.print(line, style="red")
    elif 'WARNING' in line.upper() or 'WARN' in line.upper():
        console.print(line, style="yellow")
    elif 'INFO' in line.upper():
        console.print(line, style="green")
    elif 'DEBUG' in line.upper():
        console.print(line, style="blue")
    else:
        console.print(line)


def _show_metrics_summary(metrics_data: List[Dict[str, Any]]):
    """Show summary of collected metrics."""
    if not metrics_data:
        return
    
    rprint("\n📊 [blue]Metrics Summary:[/blue]")
    
    # Get all metric names
    all_metrics = set()
    for data in metrics_data:
        all_metrics.update(data['metrics'].keys())
    
    # Calculate statistics for each metric
    table = Table(title="Metrics Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Min", style="green")
    table.add_column("Max", style="green")
    table.add_column("Avg", style="green")
    table.add_column("Latest", style="yellow")
    
    for metric_name in sorted(all_metrics):
        values = []
        latest_value = None
        
        for data in metrics_data:
            if metric_name in data['metrics']:
                value = data['metrics'][metric_name]
                if isinstance(value, (int, float)):
                    values.append(value)
                    latest_value = value
        
        if values:
            min_val = min(values)
            max_val = max(values)
            avg_val = sum(values) / len(values)
            
            table.add_row(
                metric_name,
                f"{min_val:.2f}",
                f"{max_val:.2f}",
                f"{avg_val:.2f}",
                f"{latest_value:.2f}" if latest_value is not None else "N/A"
            )
    
    console.print(table)


def _show_performance_results(results: List[Dict[str, Any]], endpoints: List[str]):
    """Show performance test results."""
    rprint("\n⚡ [blue]Performance Test Results:[/blue]")
    
    # Overall statistics
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r['success'])
    failed_requests = total_requests - successful_requests
    success_rate = (successful_requests / total_requests) * 100 if total_requests > 0 else 0
    
    # Response time statistics
    response_times = [r['response_time'] for r in results if r['success']]
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
    else:
        avg_response_time = min_response_time = max_response_time = 0
    
    # Overall summary
    summary_table = Table(title="Overall Performance Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Requests", str(total_requests))
    summary_table.add_row("Successful Requests", str(successful_requests))
    summary_table.add_row("Failed Requests", str(failed_requests))
    summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
    summary_table.add_row("Avg Response Time", f"{avg_response_time:.2f}ms")
    summary_table.add_row("Min Response Time", f"{min_response_time:.2f}ms")
    summary_table.add_row("Max Response Time", f"{max_response_time:.2f}ms")
    
    console.print(summary_table)
    
    # Per-endpoint statistics
    endpoint_table = Table(title="Per-Endpoint Statistics")
    endpoint_table.add_column("Endpoint", style="cyan")
    endpoint_table.add_column("Requests", style="green")
    endpoint_table.add_column("Success Rate", style="green")
    endpoint_table.add_column("Avg Response Time", style="green")
    
    for endpoint in endpoints:
        endpoint_results = [r for r in results if r['endpoint'] == endpoint]
        if endpoint_results:
            endpoint_total = len(endpoint_results)
            endpoint_success = sum(1 for r in endpoint_results if r['success'])
            endpoint_success_rate = (endpoint_success / endpoint_total) * 100
            
            endpoint_response_times = [r['response_time'] for r in endpoint_results if r['success']]
            endpoint_avg_time = sum(endpoint_response_times) / len(endpoint_response_times) if endpoint_response_times else 0
            
            endpoint_table.add_row(
                endpoint,
                str(endpoint_total),
                f"{endpoint_success_rate:.1f}%",
                f"{endpoint_avg_time:.2f}ms"
            )
    
    console.print(endpoint_table)


def _get_health_panel(service_url: str) -> Panel:
    """Get health status panel for dashboard."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{service_url}/health")
        
        if response.status_code == 200:
            status = "🟢 Healthy"
            style = "green"
        else:
            status = f"🔴 Unhealthy (HTTP {response.status_code})"
            style = "red"
    except:
        status = "🔴 Connection Failed"
        style = "red"
    
    return Panel(status, title="Health Status", style=style)


def _get_metrics_panel(service_url: str) -> Panel:
    """Get metrics panel for dashboard."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{service_url}/metrics")
        
        if response.status_code == 200:
            try:
                metrics = response.json()
                content = "\n".join([f"{k}: {v}" for k, v in list(metrics.items())[:5]])
            except:
                content = "Metrics available (Prometheus format)"
        else:
            content = f"Failed to fetch metrics (HTTP {response.status_code})"
    except:
        content = "Metrics unavailable"
    
    return Panel(content, title="Metrics", style="blue")


def _get_logs_panel() -> Panel:
    """Get recent logs panel for dashboard."""
    # This is a simplified version - in practice, you'd read from actual log files
    content = "Recent logs would appear here\n(Implementation depends on log configuration)"
    return Panel(content, title="Recent Logs", style="yellow")


if __name__ == "__main__":
    monitor_app()
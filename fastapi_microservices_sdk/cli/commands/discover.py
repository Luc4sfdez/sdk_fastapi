"""
Discover command for FastAPI Microservices SDK CLI.
Service discovery and exploration tools.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
import httpx
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich import print as rprint

console = Console()
discover_app = typer.Typer(name="discover", help="Discover and explore services")


@discover_app.command("services")
def discover_services(
    registry_url: str = typer.Option("http://localhost:8500", help="Service registry URL (Consul)"),
    registry_type: str = typer.Option("consul", help="Registry type (consul, etcd, kubernetes)"),
    output_format: str = typer.Option("table", help="Output format (table, json, tree)"),
    filter_service: Optional[str] = typer.Option(None, help="Filter by service name"),
    show_health: bool = typer.Option(True, help="Show health status"),
    output_file: Optional[str] = typer.Option(None, help="Save output to file")
):
    """Discover services from service registry."""
    
    rprint(f"🔍 [blue]Discovering services from {registry_type} at {registry_url}[/blue]")
    
    try:
        if registry_type == "consul":
            services = _discover_consul_services(registry_url, show_health)
        elif registry_type == "etcd":
            services = _discover_etcd_services(registry_url, show_health)
        elif registry_type == "kubernetes":
            services = _discover_k8s_services(show_health)
        else:
            rprint(f"❌ [red]Unsupported registry type: {registry_type}[/red]")
            raise typer.Exit(1)
        
        # Filter services if requested
        if filter_service:
            services = [s for s in services if filter_service.lower() in s['name'].lower()]
        
        if not services:
            rprint("❌ [yellow]No services found[/yellow]")
            return
        
        # Display results
        if output_format == "table":
            _display_services_table(services)
        elif output_format == "json":
            _display_services_json(services)
        elif output_format == "tree":
            _display_services_tree(services)
        else:
            rprint(f"❌ [red]Unsupported output format: {output_format}[/red]")
            raise typer.Exit(1)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(services, f, indent=2)
            rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        
        rprint(f"\n✅ [green]Found {len(services)} services[/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Error discovering services: {e}[/red]")
        raise typer.Exit(1)


@discover_app.command("endpoints")
def discover_endpoints(
    service_url: str = typer.Argument(..., help="Service URL to explore"),
    output_format: str = typer.Option("table", help="Output format (table, json)"),
    include_schemas: bool = typer.Option(False, help="Include request/response schemas"),
    test_endpoints: bool = typer.Option(False, help="Test endpoint availability"),
    output_file: Optional[str] = typer.Option(None, help="Save output to file")
):
    """Discover API endpoints from a service."""
    
    rprint(f"🔍 [blue]Discovering endpoints from: {service_url}[/blue]")
    
    try:
        endpoints = _discover_service_endpoints(service_url, include_schemas, test_endpoints)
        
        if not endpoints:
            rprint("❌ [yellow]No endpoints found[/yellow]")
            return
        
        # Display results
        if output_format == "table":
            _display_endpoints_table(endpoints, include_schemas)
        elif output_format == "json":
            _display_endpoints_json(endpoints)
        else:
            rprint(f"❌ [red]Unsupported output format: {output_format}[/red]")
            raise typer.Exit(1)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(endpoints, f, indent=2)
            rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        
        rprint(f"\n✅ [green]Found {len(endpoints)} endpoints[/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Error discovering endpoints: {e}[/red]")
        raise typer.Exit(1)


@discover_app.command("dependencies")
def discover_dependencies(
    service_path: str = typer.Option(".", help="Path to service directory"),
    include_versions: bool = typer.Option(True, help="Include version information"),
    check_updates: bool = typer.Option(False, help="Check for available updates"),
    output_format: str = typer.Option("table", help="Output format (table, json)"),
    output_file: Optional[str] = typer.Option(None, help="Save output to file")
):
    """Discover service dependencies and their status."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"🔍 [blue]Discovering dependencies in: {service_path}[/blue]")
    
    try:
        dependencies = _discover_service_dependencies(service_path, include_versions, check_updates)
        
        if not dependencies:
            rprint("❌ [yellow]No dependencies found[/yellow]")
            return
        
        # Display results
        if output_format == "table":
            _display_dependencies_table(dependencies, include_versions, check_updates)
        elif output_format == "json":
            _display_dependencies_json(dependencies)
        else:
            rprint(f"❌ [red]Unsupported output format: {output_format}[/red]")
            raise typer.Exit(1)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(dependencies, f, indent=2)
            rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        
        rprint(f"\n✅ [green]Found {len(dependencies)} dependencies[/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Error discovering dependencies: {e}[/red]")
        raise typer.Exit(1)


@discover_app.command("network")
def discover_network(
    target: str = typer.Argument(..., help="Target to scan (IP, hostname, or network range)"),
    ports: str = typer.Option("8000-8010,3000,5000", help="Ports to scan (comma-separated or range)"),
    timeout: int = typer.Option(3, help="Connection timeout in seconds"),
    output_format: str = typer.Option("table", help="Output format (table, json)"),
    output_file: Optional[str] = typer.Option(None, help="Save output to file")
):
    """Discover services on the network."""
    
    rprint(f"🔍 [blue]Scanning network target: {target}[/blue]")
    rprint(f"🔌 Ports: {ports}")
    
    try:
        # Parse ports
        port_list = _parse_ports(ports)
        
        # Scan network
        results = _scan_network_services(target, port_list, timeout)
        
        if not results:
            rprint("❌ [yellow]No services found[/yellow]")
            return
        
        # Display results
        if output_format == "table":
            _display_network_table(results)
        elif output_format == "json":
            _display_network_json(results)
        else:
            rprint(f"❌ [red]Unsupported output format: {output_format}[/red]")
            raise typer.Exit(1)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        
        rprint(f"\n✅ [green]Found {len(results)} open ports[/green]")
        
    except Exception as e:
        rprint(f"❌ [red]Error scanning network: {e}[/red]")
        raise typer.Exit(1)


@discover_app.command("health")
def discover_health(
    services: List[str] = typer.Argument(..., help="Service URLs to check"),
    timeout: int = typer.Option(10, help="Request timeout in seconds"),
    parallel: bool = typer.Option(True, help="Check services in parallel"),
    output_format: str = typer.Option("table", help="Output format (table, json)"),
    output_file: Optional[str] = typer.Option(None, help="Save output to file")
):
    """Discover health status of multiple services."""
    
    rprint(f"🏥 [blue]Checking health of {len(services)} services[/blue]")
    
    try:
        if parallel:
            health_results = asyncio.run(_check_services_health_parallel(services, timeout))
        else:
            health_results = _check_services_health_sequential(services, timeout)
        
        # Display results
        if output_format == "table":
            _display_health_table(health_results)
        elif output_format == "json":
            _display_health_json(health_results)
        else:
            rprint(f"❌ [red]Unsupported output format: {output_format}[/red]")
            raise typer.Exit(1)
        
        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w') as f:
                json.dump(health_results, f, indent=2)
            rprint(f"💾 [green]Results saved to: {output_path}[/green]")
        
        # Summary
        healthy_count = sum(1 for r in health_results if r['status'] == 'healthy')
        rprint(f"\n📊 [blue]Health Summary: {healthy_count}/{len(health_results)} services healthy[/blue]")
        
    except Exception as e:
        rprint(f"❌ [red]Error checking service health: {e}[/red]")
        raise typer.Exit(1)


def _discover_consul_services(registry_url: str, show_health: bool) -> List[Dict[str, Any]]:
    """Discover services from Consul."""
    
    services = []
    
    try:
        with httpx.Client(timeout=10) as client:
            # Get services list
            response = client.get(f"{registry_url}/v1/catalog/services")
            response.raise_for_status()
            
            services_data = response.json()
            
            for service_name, tags in services_data.items():
                # Get service details
                service_response = client.get(f"{registry_url}/v1/catalog/service/{service_name}")
                service_details = service_response.json()
                
                for instance in service_details:
                    service_info = {
                        'name': service_name,
                        'address': instance.get('ServiceAddress', instance.get('Address')),
                        'port': instance.get('ServicePort'),
                        'tags': tags,
                        'node': instance.get('Node'),
                        'datacenter': instance.get('Datacenter'),
                        'health': 'unknown'
                    }
                    
                    # Get health status if requested
                    if show_health:
                        try:
                            health_response = client.get(
                                f"{registry_url}/v1/health/service/{service_name}"
                            )
                            health_data = health_response.json()
                            
                            # Find health for this instance
                            for health_instance in health_data:
                                if (health_instance['Service']['Address'] == service_info['address'] and
                                    health_instance['Service']['Port'] == service_info['port']):
                                    
                                    checks = health_instance.get('Checks', [])
                                    if all(check['Status'] == 'passing' for check in checks):
                                        service_info['health'] = 'healthy'
                                    else:
                                        service_info['health'] = 'unhealthy'
                                    break
                        except:
                            service_info['health'] = 'unknown'
                    
                    services.append(service_info)
    
    except Exception as e:
        raise Exception(f"Failed to discover Consul services: {e}")
    
    return services


def _discover_etcd_services(registry_url: str, show_health: bool) -> List[Dict[str, Any]]:
    """Discover services from etcd."""
    
    # This is a simplified implementation
    # In practice, you'd use the etcd client library
    services = []
    
    try:
        with httpx.Client(timeout=10) as client:
            # Get all keys under /services/
            response = client.get(f"{registry_url}/v2/keys/services", params={'recursive': 'true'})
            response.raise_for_status()
            
            data = response.json()
            
            if 'node' in data and 'nodes' in data['node']:
                for service_node in data['node']['nodes']:
                    if 'nodes' in service_node:  # Service directory
                        service_name = service_node['key'].split('/')[-1]
                        
                        for instance_node in service_node['nodes']:
                            try:
                                instance_data = json.loads(instance_node['value'])
                                service_info = {
                                    'name': service_name,
                                    'address': instance_data.get('address', 'unknown'),
                                    'port': instance_data.get('port', 'unknown'),
                                    'tags': instance_data.get('tags', []),
                                    'health': 'unknown'
                                }
                                
                                # Basic health check if requested
                                if show_health and service_info['address'] != 'unknown':
                                    try:
                                        health_url = f"http://{service_info['address']}:{service_info['port']}/health"
                                        health_response = client.get(health_url, timeout=5)
                                        service_info['health'] = 'healthy' if health_response.status_code == 200 else 'unhealthy'
                                    except:
                                        service_info['health'] = 'unhealthy'
                                
                                services.append(service_info)
                            except:
                                continue
    
    except Exception as e:
        raise Exception(f"Failed to discover etcd services: {e}")
    
    return services


def _discover_k8s_services(show_health: bool) -> List[Dict[str, Any]]:
    """Discover services from Kubernetes."""
    
    import subprocess
    services = []
    
    try:
        # Use kubectl to get services
        result = subprocess.run([
            'kubectl', 'get', 'services', '-o', 'json'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception("kubectl command failed")
        
        k8s_data = json.loads(result.stdout)
        
        for item in k8s_data.get('items', []):
            metadata = item.get('metadata', {})
            spec = item.get('spec', {})
            
            service_info = {
                'name': metadata.get('name', 'unknown'),
                'namespace': metadata.get('namespace', 'default'),
                'cluster_ip': spec.get('clusterIP', 'unknown'),
                'ports': spec.get('ports', []),
                'type': spec.get('type', 'ClusterIP'),
                'health': 'unknown'
            }
            
            # Basic health check for LoadBalancer services
            if show_health and spec.get('type') == 'LoadBalancer':
                status = item.get('status', {})
                ingress = status.get('loadBalancer', {}).get('ingress', [])
                if ingress:
                    service_info['health'] = 'healthy'
                else:
                    service_info['health'] = 'pending'
            
            services.append(service_info)
    
    except Exception as e:
        raise Exception(f"Failed to discover Kubernetes services: {e}")
    
    return services


def _discover_service_endpoints(service_url: str, include_schemas: bool, test_endpoints: bool) -> List[Dict[str, Any]]:
    """Discover endpoints from a service's OpenAPI spec."""
    
    endpoints = []
    
    try:
        with httpx.Client(timeout=10) as client:
            # Try to get OpenAPI spec
            openapi_urls = ['/openapi.json', '/docs/openapi.json', '/api/openapi.json']
            
            openapi_data = None
            for url in openapi_urls:
                try:
                    response = client.get(f"{service_url}{url}")
                    if response.status_code == 200:
                        openapi_data = response.json()
                        break
                except:
                    continue
            
            if not openapi_data:
                raise Exception("Could not find OpenAPI specification")
            
            # Parse endpoints from OpenAPI spec
            paths = openapi_data.get('paths', {})
            
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoint_info = {
                            'path': path,
                            'method': method.upper(),
                            'summary': details.get('summary', ''),
                            'description': details.get('description', ''),
                            'tags': details.get('tags', []),
                            'parameters': details.get('parameters', []),
                            'status': 'unknown'
                        }
                        
                        # Include schemas if requested
                        if include_schemas:
                            endpoint_info['request_body'] = details.get('requestBody', {})
                            endpoint_info['responses'] = details.get('responses', {})
                        
                        # Test endpoint if requested
                        if test_endpoints:
                            try:
                                if method.upper() == 'GET':
                                    test_response = client.get(f"{service_url}{path}")
                                    endpoint_info['status'] = 'available' if test_response.status_code < 500 else 'error'
                                else:
                                    endpoint_info['status'] = 'not_tested'
                            except:
                                endpoint_info['status'] = 'unavailable'
                        
                        endpoints.append(endpoint_info)
    
    except Exception as e:
        raise Exception(f"Failed to discover endpoints: {e}")
    
    return endpoints


def _discover_service_dependencies(service_path: Path, include_versions: bool, check_updates: bool) -> List[Dict[str, Any]]:
    """Discover service dependencies from requirements files."""
    
    dependencies = []
    
    # Check requirements.txt
    requirements_file = service_path / "requirements.txt"
    if requirements_file.exists():
        with open(requirements_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    dep_info = _parse_dependency_line(line, include_versions, check_updates)
                    if dep_info:
                        dependencies.append(dep_info)
    
    # Check pyproject.toml
    pyproject_file = service_path / "pyproject.toml"
    if pyproject_file.exists():
        try:
            import toml
            with open(pyproject_file) as f:
                pyproject_data = toml.load(f)
            
            deps = pyproject_data.get('tool', {}).get('poetry', {}).get('dependencies', {})
            for name, version in deps.items():
                if name != 'python':
                    dep_info = {
                        'name': name,
                        'current_version': version if isinstance(version, str) else 'complex',
                        'source': 'pyproject.toml',
                        'status': 'installed'
                    }
                    
                    if check_updates:
                        dep_info['latest_version'] = _get_latest_version(name)
                    
                    dependencies.append(dep_info)
        except ImportError:
            pass  # toml not available
    
    return dependencies


def _parse_dependency_line(line: str, include_versions: bool, check_updates: bool) -> Optional[Dict[str, Any]]:
    """Parse a dependency line from requirements.txt."""
    
    # Remove comments
    if '#' in line:
        line = line.split('#')[0].strip()
    
    if not line:
        return None
    
    # Parse package name and version
    import re
    
    # Match patterns like: package==1.0.0, package>=1.0.0, package~=1.0.0
    match = re.match(r'^([a-zA-Z0-9_-]+)([><=!~]+)?([0-9.]+.*)?', line)
    
    if not match:
        return None
    
    name = match.group(1)
    operator = match.group(2) or ''
    version = match.group(3) or ''
    
    dep_info = {
        'name': name,
        'current_version': f"{operator}{version}" if version else 'any',
        'source': 'requirements.txt',
        'status': 'specified'
    }
    
    if check_updates:
        dep_info['latest_version'] = _get_latest_version(name)
    
    return dep_info


def _get_latest_version(package_name: str) -> str:
    """Get latest version of a package from PyPI."""
    
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(f"https://pypi.org/pypi/{package_name}/json")
            if response.status_code == 200:
                data = response.json()
                return data['info']['version']
    except:
        pass
    
    return 'unknown'


def _parse_ports(ports_str: str) -> List[int]:
    """Parse port specification string."""
    
    ports = []
    
    for part in ports_str.split(','):
        part = part.strip()
        
        if '-' in part:
            # Port range
            start, end = part.split('-', 1)
            try:
                start_port = int(start.strip())
                end_port = int(end.strip())
                ports.extend(range(start_port, end_port + 1))
            except ValueError:
                continue
        else:
            # Single port
            try:
                ports.append(int(part))
            except ValueError:
                continue
    
    return sorted(set(ports))


def _scan_network_services(target: str, ports: List[int], timeout: int) -> List[Dict[str, Any]]:
    """Scan network for services."""
    
    import socket
    results = []
    
    # Handle different target formats
    if '/' in target:
        # Network range (simplified - just scan first few IPs)
        base_ip = target.split('/')[0]
        ip_parts = base_ip.split('.')
        base = '.'.join(ip_parts[:3])
        
        targets = [f"{base}.{i}" for i in range(1, 11)]  # Scan first 10 IPs
    else:
        targets = [target]
    
    for ip in targets:
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                
                if result == 0:
                    # Port is open, try to identify service
                    service_info = {
                        'host': ip,
                        'port': port,
                        'status': 'open',
                        'service': _identify_service(ip, port)
                    }
                    results.append(service_info)
                
                sock.close()
            except:
                continue
    
    return results


def _identify_service(host: str, port: int) -> str:
    """Try to identify what service is running on a port."""
    
    try:
        with httpx.Client(timeout=3) as client:
            # Try HTTP
            for scheme in ['http', 'https']:
                try:
                    response = client.get(f"{scheme}://{host}:{port}/")
                    if response.status_code < 500:
                        # Try to identify from headers or content
                        server = response.headers.get('server', '').lower()
                        if 'fastapi' in server or 'uvicorn' in server:
                            return 'FastAPI'
                        elif 'nginx' in server:
                            return 'Nginx'
                        elif 'apache' in server:
                            return 'Apache'
                        else:
                            return 'HTTP Service'
                except:
                    continue
    except:
        pass
    
    # Common port mappings
    common_ports = {
        22: 'SSH',
        80: 'HTTP',
        443: 'HTTPS',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        6379: 'Redis',
        27017: 'MongoDB',
        5672: 'RabbitMQ',
        9092: 'Kafka'
    }
    
    return common_ports.get(port, 'Unknown')


async def _check_services_health_parallel(services: List[str], timeout: int) -> List[Dict[str, Any]]:
    """Check health of multiple services in parallel."""
    
    async def check_single_service(service_url: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{service_url}/health")
                
                return {
                    'service': service_url,
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds() * 1000,
                    'details': response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            return {
                'service': service_url,
                'status': 'error',
                'status_code': 0,
                'response_time': 0,
                'error': str(e)
            }
    
    tasks = [check_single_service(service) for service in services]
    return await asyncio.gather(*tasks)


def _check_services_health_sequential(services: List[str], timeout: int) -> List[Dict[str, Any]]:
    """Check health of multiple services sequentially."""
    
    results = []
    
    for service_url in services:
        try:
            with httpx.Client(timeout=timeout) as client:
                import time
                start_time = time.time()
                response = client.get(f"{service_url}/health")
                response_time = (time.time() - start_time) * 1000
                
                result = {
                    'service': service_url,
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'details': response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            result = {
                'service': service_url,
                'status': 'error',
                'status_code': 0,
                'response_time': 0,
                'error': str(e)
            }
        
        results.append(result)
    
    return results


def _display_services_table(services: List[Dict[str, Any]]):
    """Display services in table format."""
    
    table = Table(title="Discovered Services")
    table.add_column("Name", style="cyan")
    table.add_column("Address", style="green")
    table.add_column("Port", style="yellow")
    table.add_column("Health", style="blue")
    table.add_column("Tags", style="magenta")
    
    for service in services:
        health_style = "green" if service['health'] == 'healthy' else "red" if service['health'] == 'unhealthy' else "yellow"
        
        table.add_row(
            service['name'],
            service.get('address', 'unknown'),
            str(service.get('port', 'unknown')),
            f"[{health_style}]{service['health']}[/{health_style}]",
            ', '.join(service.get('tags', []))
        )
    
    console.print(table)


def _display_services_json(services: List[Dict[str, Any]]):
    """Display services in JSON format."""
    rprint(json.dumps(services, indent=2))


def _display_services_tree(services: List[Dict[str, Any]]):
    """Display services in tree format."""
    
    tree = Tree("🔍 Discovered Services")
    
    # Group by service name
    service_groups = {}
    for service in services:
        name = service['name']
        if name not in service_groups:
            service_groups[name] = []
        service_groups[name].append(service)
    
    for service_name, instances in service_groups.items():
        service_branch = tree.add(f"🔧 {service_name}")
        
        for instance in instances:
            health_icon = "🟢" if instance['health'] == 'healthy' else "🔴" if instance['health'] == 'unhealthy' else "🟡"
            instance_info = f"{health_icon} {instance.get('address', 'unknown')}:{instance.get('port', 'unknown')}"
            
            instance_branch = service_branch.add(instance_info)
            
            if instance.get('tags'):
                instance_branch.add(f"🏷️  Tags: {', '.join(instance['tags'])}")
    
    console.print(tree)


def _display_endpoints_table(endpoints: List[Dict[str, Any]], include_schemas: bool):
    """Display endpoints in table format."""
    
    table = Table(title="Service Endpoints")
    table.add_column("Method", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Summary", style="yellow")
    table.add_column("Tags", style="blue")
    
    if include_schemas:
        table.add_column("Status", style="magenta")
    
    for endpoint in endpoints:
        row = [
            endpoint['method'],
            endpoint['path'],
            endpoint.get('summary', '')[:50],
            ', '.join(endpoint.get('tags', []))
        ]
        
        if include_schemas:
            status = endpoint.get('status', 'unknown')
            status_style = "green" if status == 'available' else "red" if status == 'unavailable' else "yellow"
            row.append(f"[{status_style}]{status}[/{status_style}]")
        
        table.add_row(*row)
    
    console.print(table)


def _display_endpoints_json(endpoints: List[Dict[str, Any]]):
    """Display endpoints in JSON format."""
    rprint(json.dumps(endpoints, indent=2))


def _display_dependencies_table(dependencies: List[Dict[str, Any]], include_versions: bool, check_updates: bool):
    """Display dependencies in table format."""
    
    table = Table(title="Service Dependencies")
    table.add_column("Package", style="cyan")
    table.add_column("Current Version", style="green")
    table.add_column("Source", style="yellow")
    
    if check_updates:
        table.add_column("Latest Version", style="blue")
        table.add_column("Update Available", style="magenta")
    
    for dep in dependencies:
        row = [
            dep['name'],
            dep.get('current_version', 'unknown'),
            dep.get('source', 'unknown')
        ]
        
        if check_updates:
            latest = dep.get('latest_version', 'unknown')
            row.append(latest)
            
            # Simple update check (this could be more sophisticated)
            current = dep.get('current_version', '')
            if latest != 'unknown' and current != 'any' and latest not in current:
                row.append("[green]Yes[/green]")
            else:
                row.append("[yellow]No[/yellow]")
        
        table.add_row(*row)
    
    console.print(table)


def _display_dependencies_json(dependencies: List[Dict[str, Any]]):
    """Display dependencies in JSON format."""
    rprint(json.dumps(dependencies, indent=2))


def _display_network_table(results: List[Dict[str, Any]]):
    """Display network scan results in table format."""
    
    table = Table(title="Network Scan Results")
    table.add_column("Host", style="cyan")
    table.add_column("Port", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Service", style="blue")
    
    for result in results:
        table.add_row(
            result['host'],
            str(result['port']),
            result['status'],
            result.get('service', 'Unknown')
        )
    
    console.print(table)


def _display_network_json(results: List[Dict[str, Any]]):
    """Display network scan results in JSON format."""
    rprint(json.dumps(results, indent=2))


def _display_health_table(health_results: List[Dict[str, Any]]):
    """Display health check results in table format."""
    
    table = Table(title="Service Health Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Response Time", style="yellow")
    table.add_column("Status Code", style="blue")
    
    for result in health_results:
        status = result['status']
        status_style = "green" if status == 'healthy' else "red" if status in ['unhealthy', 'error'] else "yellow"
        
        table.add_row(
            result['service'],
            f"[{status_style}]{status}[/{status_style}]",
            f"{result.get('response_time', 0):.2f}ms",
            str(result.get('status_code', 0))
        )
    
    console.print(table)


def _display_health_json(health_results: List[Dict[str, Any]]):
    """Display health check results in JSON format."""
    rprint(json.dumps(health_results, indent=2))


if __name__ == "__main__":
    discover_app()
# fastapi-microservices-sdk/fastapi_microservices_sdk/utils/helpers.py 
"""
Helper utilities for the FastAPI Microservices SDK.
"""

import uuid
import socket
import time
from typing import Dict, Any, Optional
from datetime import datetime


def generate_service_id(service_name: str) -> str:
    """
    Generate a unique service ID.
    
    Args:
        service_name: Name of the service
        
    Returns:
        Unique service ID
    """
    return f"{service_name}-{uuid.uuid4().hex[:8]}"


def generate_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        Unique request ID
    """
    return str(uuid.uuid4())


def get_local_ip() -> str:
    """
    Get the local IP address.
    
    Returns:
        Local IP address
    """
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_hostname() -> str:
    """
    Get the hostname.
    
    Returns:
        Hostname
    """
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def is_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available on the given host.
    
    Args:
        host: Host address
        port: Port number
        
    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0
    except Exception:
        return False


def find_available_port(host: str = "localhost", start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
    """
    Find an available port starting from the given port.
    
    Args:
        host: Host address to check
        start_port: Starting port number
        max_attempts: Maximum number of ports to try
        
    Returns:
        Available port number or None if not found
    """
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(host, port):
            return port
    return None


def get_service_info(service_name: str, host: str, port: int, version: str = "1.0.0") -> Dict[str, Any]:
    """
    Get comprehensive service information.
    
    Args:
        service_name: Name of the service
        host: Service host
        port: Service port
        version: Service version
        
    Returns:
        Dictionary with service information
    """
    return {
        "name": service_name,
        "version": version,
        "host": host,
        "port": port,
        "url": f"http://{host}:{port}",
        "local_ip": get_local_ip(),
        "hostname": get_hostname(),
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": 0  # Will be updated by the service
    }


def format_service_url(host: str, port: int, path: str = "", scheme: str = "http") -> str:
    """
    Format a service URL.
    
    Args:
        host: Service host
        port: Service port
        path: Optional path
        scheme: URL scheme (http/https)
        
    Returns:
        Formatted URL
    """
    url = f"{scheme}://{host}:{port}"
    if path:
        if not path.startswith('/'):
            path = '/' + path
        url += path
    return url


def parse_service_url(url: str) -> Dict[str, Any]:
    """
    Parse a service URL into components.
    
    Args:
        url: Service URL to parse
        
    Returns:
        Dictionary with URL components
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": parsed.port,
        "path": parsed.path,
        "query": parsed.query,
        "fragment": parsed.fragment
    }


def create_health_check_response(
    service_name: str,
    status: str = "healthy",
    checks: Optional[Dict[str, Any]] = None,
    version: str = "1.0.0"
) -> Dict[str, Any]:
    """
    Create a standardized health check response.
    
    Args:
        service_name: Name of the service
        status: Health status
        checks: Additional health checks
        version: Service version
        
    Returns:
        Health check response dictionary
    """
    return {
        "service": service_name,
        "version": version,
        "status": status,
        "timestamp": time.time(),
        "checks": checks or {}
    }


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries.
    
    Args:
        base_config: Base configuration
        override_config: Configuration to merge in
        
    Returns:
        Merged configuration
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def sanitize_service_name(name: str) -> str:
    """
    Sanitize a service name to make it valid.
    
    Args:
        name: Service name to sanitize
        
    Returns:
        Sanitized service name
    """
    import re
    
    # Convert to lowercase
    name = name.lower()
    
    # Replace invalid characters with hyphens
    name = re.sub(r'[^a-z0-9\-]', '-', name)
    
    # Remove consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    # Ensure minimum length
    if len(name) < 3:
        name = f"service-{name}"
    
    # Ensure maximum length
    if len(name) > 50:
        name = name[:50].rstrip('-')
    
    return name

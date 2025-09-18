# fastapi-microservices-sdk/fastapi_microservices_sdk/utils/validators.py 
"""
Validation utilities for the FastAPI Microservices SDK.
"""

import re
from typing import Optional, List
from urllib.parse import urlparse


def validate_service_name(name: str) -> bool:
    """
    Validate service name according to microservices naming conventions.
    
    Rules:
    - Must be 3-50 characters long
    - Can contain lowercase letters, numbers, and hyphens
    - Must start and end with alphanumeric characters
    - Cannot contain consecutive hyphens
    
    Args:
        name: Service name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    # Length check
    if len(name) < 3 or len(name) > 50:
        return False
    
    # Pattern check: lowercase letters, numbers, hyphens
    # Must start and end with alphanumeric, no consecutive hyphens
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    if not re.match(pattern, name):
        return False
    
    # No consecutive hyphens
    if '--' in name:
        return False
    
    return True


def validate_endpoint_path(path: str) -> bool:
    """
    Validate API endpoint path.
    
    Args:
        path: Endpoint path to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not path or not isinstance(path, str):
        return False
    
    # Must start with /
    if not path.startswith('/'):
        return False
    
    # Basic path validation
    # Allow alphanumeric, hyphens, underscores, slashes, and path parameters
    pattern = r'^/[a-zA-Z0-9/_\-{}]*$'
    return bool(re.match(pattern, path))


def validate_port(port: int) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid, False otherwise
    """
    return isinstance(port, int) and 1 <= port <= 65535


def validate_host(host: str) -> bool:
    """
    Validate host address.
    
    Args:
        host: Host address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not host or not isinstance(host, str):
        return False
    
    # Allow localhost, IP addresses, and domain names
    # Simple validation - could be more comprehensive
    if host in ['localhost', '0.0.0.0', '127.0.0.1']:
        return True
    
    # Basic IP address pattern
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, host):
        # Validate IP ranges
        parts = host.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    # Basic domain name pattern
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$'
    return bool(re.match(domain_pattern, host))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_version(version: str) -> bool:
    """
    Validate semantic version format.
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not version or not isinstance(version, str):
        return False
    
    # Basic semver pattern: major.minor.patch
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9\-]+)?(\+[a-zA-Z0-9\-]+)?$'
    return bool(re.match(pattern, version))


def validate_environment(env: str) -> bool:
    """
    Validate environment name.
    
    Args:
        env: Environment name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not env or not isinstance(env, str):
        return False
    
    valid_environments = [
        'development', 'dev',
        'testing', 'test',
        'staging', 'stage',
        'production', 'prod',
        'local'
    ]
    
    return env.lower() in valid_environments


def validate_service_config(config: dict) -> List[str]:
    """
    Validate service configuration dictionary.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['name']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Validate service name
    if 'name' in config and not validate_service_name(config['name']):
        errors.append(f"Invalid service name: {config['name']}")
    
    # Validate version if present
    if 'version' in config and not validate_version(config['version']):
        errors.append(f"Invalid version format: {config['version']}")
    
    # Validate host if present
    if 'host' in config and not validate_host(config['host']):
        errors.append(f"Invalid host: {config['host']}")
    
    # Validate port if present
    if 'port' in config and not validate_port(config['port']):
        errors.append(f"Invalid port: {config['port']}")
    
    # Validate environment if present
    if 'environment' in config and not validate_environment(config['environment']):
        errors.append(f"Invalid environment: {config['environment']}")
    
    return errors

# fastapi-microservices-sdk/fastapi_microservices_sdk/version.py
"""
Version management for FastAPI Microservices SDK.

This module handles version information, compatibility checks,
and version-related utilities for the SDK.
"""

import sys
from typing import Tuple, Dict, Any
from datetime import datetime

# Current SDK version
__version__ = "0.1.0"

# Version components for programmatic access
VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 0
VERSION_PRE_RELEASE = None  # None, "alpha", "beta", "rc"
VERSION_BUILD = None  # Build number for pre-releases

# Build information
BUILD_DATE = "2024-08-23"
BUILD_COMMIT = "initial"  # Git commit hash (set during CI/CD)

# Compatibility information
PYTHON_MIN_VERSION = (3, 8)
PYTHON_MAX_VERSION = (3, 12)
FASTAPI_MIN_VERSION = "0.104.1"
FASTAPI_MAX_VERSION = "0.105.0"

def get_version() -> str:
    """
    Get the full version string.
    
    Returns:
        Version string in semver format (e.g., "0.1.0", "0.1.0-alpha.1")
        
    Example:
        from fastapi_microservices_sdk.version import get_version
        print(f"SDK Version: {get_version()}")
    """
    version = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
    
    if VERSION_PRE_RELEASE:
        version += f"-{VERSION_PRE_RELEASE}"
        if VERSION_BUILD:
            version += f".{VERSION_BUILD}"
    
    return version

def get_version_info() -> Tuple[int, int, int, str, str]:
    """
    Get version information as a tuple.
    
    Returns:
        Tuple of (major, minor, patch, pre_release, build)
        
    Example:
        major, minor, patch, pre, build = get_version_info()
        print(f"Running version {major}.{minor}.{patch}")
    """
    return (
        VERSION_MAJOR,
        VERSION_MINOR, 
        VERSION_PATCH,
        VERSION_PRE_RELEASE or "",
        VERSION_BUILD or ""
    )

def check_python_compatibility() -> bool:
    """
    Check if current Python version is compatible with the SDK.
    
    Returns:
        True if compatible, False otherwise
        
    Example:
        from fastapi_microservices_sdk.version import check_python_compatibility
        if not check_python_compatibility():
            print("Python version not supported!")
    """
    current_version = sys.version_info[:2]
    return PYTHON_MIN_VERSION <= current_version <= PYTHON_MAX_VERSION

def get_python_version_string() -> str:
    """
    Get current Python version as a string.
    
    Returns:
        Python version string (e.g., "3.9.7")
    """
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

def check_fastapi_compatibility(fastapi_version: str) -> bool:
    """
    Check if given FastAPI version is compatible with the SDK.
    
    Args:
        fastapi_version: FastAPI version string to check
        
    Returns:
        True if compatible, False otherwise
        
    Example:
        from fastapi import __version__ as fastapi_version
        from fastapi_microservices_sdk.version import check_fastapi_compatibility
        
        if check_fastapi_compatibility(fastapi_version):
            print("FastAPI version is compatible")
    """
    try:
        from packaging import version
        current = version.parse(fastapi_version)
        min_version = version.parse(FASTAPI_MIN_VERSION)
        max_version = version.parse(FASTAPI_MAX_VERSION)
        return min_version <= current < max_version
    except ImportError:
        # Fallback to string comparison if packaging not available
        return FASTAPI_MIN_VERSION <= fastapi_version < FASTAPI_MAX_VERSION

def get_build_info() -> Dict[str, Any]:
    """
    Get build information for the SDK.
    
    Returns:
        Dictionary containing build metadata
        
    Example:
        from fastapi_microservices_sdk.version import get_build_info
        info = get_build_info()
        print(f"Built on: {info['build_date']}")
    """
    return {
        "version": get_version(),
        "version_info": get_version_info(),
        "build_date": BUILD_DATE,
        "build_commit": BUILD_COMMIT,
        "python_version": get_python_version_string(),
        "python_compatible": check_python_compatibility(),
        "min_python": f"{PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}",
        "max_python": f"{PYTHON_MAX_VERSION[0]}.{PYTHON_MAX_VERSION[1]}",
        "fastapi_min": FASTAPI_MIN_VERSION,
        "fastapi_max": FASTAPI_MAX_VERSION,
    }

def print_version_info() -> None:
    """
    Print comprehensive version information to stdout.
    
    Useful for debugging and support purposes.
    
    Example:
        from fastapi_microservices_sdk.version import print_version_info
        print_version_info()
    """
    info = get_build_info()
    
    print("=" * 50)
    print("FastAPI Microservices SDK Version Info")
    print("=" * 50)
    print(f"SDK Version: {info['version']}")
    print(f"Build Date: {info['build_date']}")
    print(f"Build Commit: {info['build_commit']}")
    print()
    print("Python Compatibility:")
    print(f"  Current Python: {info['python_version']}")
    print(f"  Compatible: {'✅ Yes' if info['python_compatible'] else '❌ No'}")
    print(f"  Required: {info['min_python']} - {info['max_python']}")
    print()
    print("FastAPI Compatibility:")
    print(f"  Required FastAPI: {info['fastapi_min']} - {info['fastapi_max']}")
    print()
    
    # Check actual FastAPI version if available
    try:
        import fastapi
        fastapi_version = fastapi.__version__
        compatible = check_fastapi_compatibility(fastapi_version)
        print(f"  Installed FastAPI: {fastapi_version}")
        print(f"  Compatible: {'✅ Yes' if compatible else '❌ No'}")
    except ImportError:
        print("  FastAPI: Not installed")
    
    print("=" * 50)

def is_development_version() -> bool:
    """
    Check if this is a development version.
    
    Returns:
        True if this is a dev version (pre-release or version < 1.0.0)
        
    Example:
        from fastapi_microservices_sdk.version import is_development_version
        if is_development_version():
            print("This is a development version")
    """
    return VERSION_PRE_RELEASE is not None or VERSION_MAJOR == 0

def is_stable_version() -> bool:
    """
    Check if this is a stable version.
    
    Returns:
        True if this is a stable version (>= 1.0.0 and no pre-release)
        
    Example:
        from fastapi_microservices_sdk.version import is_stable_version
        if is_stable_version():
            print("This is a stable version")
    """
    return VERSION_MAJOR >= 1 and VERSION_PRE_RELEASE is None

def get_compatibility_report() -> Dict[str, Any]:
    """
    Get a comprehensive compatibility report.
    
    Returns:
        Dictionary with compatibility information for all dependencies
        
    Example:
        from fastapi_microservices_sdk.version import get_compatibility_report
        report = get_compatibility_report()
        
        if report['all_compatible']:
            print("All dependencies are compatible")
        else:
            print("Compatibility issues found:")
            for issue in report['issues']:
                print(f"  - {issue}")
    """
    issues = []
    
    # Check Python compatibility
    if not check_python_compatibility():
        python_version = get_python_version_string()
        issues.append(f"Python {python_version} not supported. "
                     f"Required: {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ "
                     f"to {PYTHON_MAX_VERSION[0]}.{PYTHON_MAX_VERSION[1]}")
    
    # Check FastAPI compatibility if available
    try:
        import fastapi
        if not check_fastapi_compatibility(fastapi.__version__):
            issues.append(f"FastAPI {fastapi.__version__} not supported. "
                         f"Required: {FASTAPI_MIN_VERSION} to {FASTAPI_MAX_VERSION}")
    except ImportError:
        issues.append("FastAPI not installed")
    
    return {
        "all_compatible": len(issues) == 0,
        "issues": issues,
        "python_compatible": check_python_compatibility(),
        "python_version": get_python_version_string(),
        "sdk_version": get_version(),
        "is_development": is_development_version(),
        "is_stable": is_stable_version(),
        "build_info": get_build_info(),
    }

# Module level constants for easy access
VERSION = __version__
VERSION_TUPLE = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

# Validate environment on import
if __name__ != "__main__":
    if not check_python_compatibility():
        import warnings
        warnings.warn(
            f"Python {get_python_version_string()} may not be fully supported. "
            f"Recommended: Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+",
            UserWarning,
            stacklevel=2
        )

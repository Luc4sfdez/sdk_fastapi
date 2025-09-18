# fastapi-microservices-sdk/fastapi_microservices_sdk/security/secrets/env_secrets.py
"""
Environment Variables Secret Backend for FastAPI Microservices SDK.

This backend provides secure access to environment variables with
validation, transformation, and fallback support.
"""

import os
import base64
from typing import Dict, Any, Optional, List
import logging

from .secrets_manager import SecretBackend
from ...exceptions import SecurityError


class EnvSecrets(SecretBackend):
    """
    Environment Variables Secret Backend.
    
    Features:
    - Environment variable access
    - Base64 decoding support
    - Prefix-based organization
    - Default value support
    - Validation and transformation
    """
    
    def __init__(
        self,
        prefix: str = "SECRET_",
        auto_decode_base64: bool = True,
        case_sensitive: bool = True,
        allow_empty_values: bool = False
    ):
        """
        Initialize Environment Secrets Backend.
        
        Args:
            prefix: Prefix for secret environment variables
            auto_decode_base64: Automatically decode base64 values
            case_sensitive: Case sensitive key matching
            allow_empty_values: Allow empty string values
        """
        self.prefix = prefix
        self.auto_decode_base64 = auto_decode_base64
        self.case_sensitive = case_sensitive
        self.allow_empty_values = allow_empty_values
        
        self.logger = logging.getLogger("env_secrets")
        
        # Cache environment variables for performance
        self._env_cache = dict(os.environ)
    
    async def get_secret(self, key: str, version: Optional[str] = None) -> str:
        """
        Get secret from environment variables.
        
        Args:
            key: Secret key (without prefix)
            version: Version (ignored for env vars)
            
        Returns:
            Secret value
            
        Raises:
            SecurityError: If secret not found or invalid
        """
        # Build full environment variable name
        env_key = self._build_env_key(key)
        
        # Try different case variations if not case sensitive
        possible_keys = [env_key]
        if not self.case_sensitive:
            possible_keys.extend([
                env_key.upper(),
                env_key.lower(),
                key.upper(),
                key.lower(),
                f"{self.prefix.upper()}{key.upper()}",
                f"{self.prefix.lower()}{key.lower()}",
            ])
        
        # Find the secret
        value = None
        found_key = None
        
        for possible_key in possible_keys:
            if possible_key in self._env_cache:
                value = self._env_cache[possible_key]
                found_key = possible_key
                break
        
        if value is None:
            raise SecurityError(f"Secret not found in environment: {key}")
        
        # Validate empty values
        if not self.allow_empty_values and not value.strip():
            raise SecurityError(f"Empty secret value not allowed: {key}")
        
        # Auto-decode base64 if enabled
        if self.auto_decode_base64 and self._is_base64(value):
            try:
                decoded_value = base64.b64decode(value).decode('utf-8')
                self.logger.debug(f"Decoded base64 secret: {key}")
                return decoded_value
            except Exception as e:
                self.logger.warning(f"Failed to decode base64 for {key}: {e}")
                # Return original value if decoding fails
        
        self.logger.debug(f"Retrieved secret from env: {key} (as {found_key})")
        return value
    
    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set secret in environment (runtime only).
        
        Args:
            key: Secret key
            value: Secret value
            metadata: Metadata (ignored for env vars)
            
        Returns:
            True if successful
        """
        env_key = self._build_env_key(key)
        
        # Set in both os.environ and cache
        os.environ[env_key] = value
        self._env_cache[env_key] = value
        
        self.logger.info(f"Set environment secret: {key}")
        return True
    
    async def delete_secret(self, key: str) -> bool:
        """
        Delete secret from environment (runtime only).
        
        Args:
            key: Secret key to delete
            
        Returns:
            True if successful
        """
        env_key = self._build_env_key(key)
        
        # Remove from both os.environ and cache
        if env_key in os.environ:
            del os.environ[env_key]
        
        if env_key in self._env_cache:
            del self._env_cache[env_key]
        
        self.logger.info(f"Deleted environment secret: {key}")
        return True
    
    async def list_secrets(self, prefix: str = "") -> List[str]:
        """
        List available secrets in environment.
        
        Args:
            prefix: Additional prefix filter
            
        Returns:
            List of secret keys (without prefix)
        """
        secrets = []
        search_prefix = self.prefix + prefix
        
        for env_key in self._env_cache.keys():
            if env_key.startswith(search_prefix):
                # Remove the prefix to get the secret key
                secret_key = env_key[len(self.prefix):]
                secrets.append(secret_key)
        
        return sorted(secrets)
    
    def _build_env_key(self, key: str) -> str:
        """Build full environment variable key."""
        if key.startswith(self.prefix):
            return key
        return self.prefix + key
    
    def _is_base64(self, value: str) -> bool:
        """Check if value looks like base64."""
        try:
            # Basic heuristics for base64
            if len(value) % 4 != 0:
                return False
            
            # Check for base64 characters
            import re
            base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
            if not base64_pattern.match(value):
                return False
            
            # Try to decode
            base64.b64decode(value, validate=True)
            return True
            
        except Exception:
            return False
    
    def get_secret_with_default(self, key: str, default: str = None) -> str:
        """
        Get secret with default value (synchronous).
        
        Args:
            key: Secret key
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        try:
            import asyncio
            return asyncio.run(self.get_secret(key))
        except SecurityError:
            if default is not None:
                return default
            raise
    
    def refresh_cache(self):
        """Refresh environment variable cache."""
        self._env_cache = dict(os.environ)
        self.logger.debug("Refreshed environment variable cache")
    
    def get_all_secrets(self, include_values: bool = False) -> Dict[str, Any]:
        """
        Get all secrets with optional values.
        
        Args:
            include_values: Include secret values (dangerous!)
            
        Returns:
            Dictionary of secrets
        """
        secrets = {}
        
        for env_key, env_value in self._env_cache.items():
            if env_key.startswith(self.prefix):
                secret_key = env_key[len(self.prefix):]
                
                if include_values:
                    secrets[secret_key] = env_value
                else:
                    secrets[secret_key] = {
                        "length": len(env_value),
                        "is_base64": self._is_base64(env_value),
                        "is_empty": not env_value.strip(),
                    }
        
        return secrets
    
    def validate_secrets(self, required_secrets: List[str]) -> Dict[str, Any]:
        """
        Validate that required secrets are present.
        
        Args:
            required_secrets: List of required secret keys
            
        Returns:
            Validation results
        """
        results = {
            "valid": True,
            "missing_secrets": [],
            "empty_secrets": [],
            "invalid_secrets": [],
        }
        
        for secret_key in required_secrets:
            try:
                env_key = self._build_env_key(secret_key)
                
                if env_key not in self._env_cache:
                    results["missing_secrets"].append(secret_key)
                    results["valid"] = False
                    continue
                
                value = self._env_cache[env_key]
                
                if not self.allow_empty_values and not value.strip():
                    results["empty_secrets"].append(secret_key)
                    results["valid"] = False
                
            except Exception as e:
                results["invalid_secrets"].append({
                    "key": secret_key,
                    "error": str(e)
                })
                results["valid"] = False
        
        return results
    
    def export_secrets_template(self, keys: List[str] = None) -> str:
        """
        Export secrets as environment template.
        
        Args:
            keys: Specific keys to export (all if None)
            
        Returns:
            Environment template string
        """
        if keys is None:
            keys = []
            for env_key in self._env_cache.keys():
                if env_key.startswith(self.prefix):
                    keys.append(env_key[len(self.prefix):])
        
        template_lines = [
            "# Environment Variables Template",
            "# Generated by FastAPI Microservices SDK",
            "",
        ]
        
        for key in sorted(keys):
            env_key = self._build_env_key(key)
            if env_key in self._env_cache:
                # Don't include actual values in template
                template_lines.append(f"{env_key}=your_secret_value_here")
            else:
                template_lines.append(f"{env_key}=")
        
        return "\n".join(template_lines)
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get backend information."""
        secret_count = len([k for k in self._env_cache.keys() if k.startswith(self.prefix)])
        
        return {
            "backend_type": "environment_variables",
            "prefix": self.prefix,
            "auto_decode_base64": self.auto_decode_base64,
            "case_sensitive": self.case_sensitive,
            "allow_empty_values": self.allow_empty_values,
            "secret_count": secret_count,
            "total_env_vars": len(self._env_cache),
        }
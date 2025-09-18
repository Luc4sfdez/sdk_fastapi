# fastapi-microservices-sdk/fastapi_microservices_sdk/security/secrets/vault_client.py
"""
HashiCorp Vault Client for FastAPI Microservices SDK.

This module provides integration with HashiCorp Vault for secure
secret storage and management in production environments.
"""

import asyncio
from typing import Dict, Any, Optional, List
import logging
import json

import httpx

from .secrets_manager import SecretBackend
from ...exceptions import SecurityError, ConfigurationError


class VaultClient(SecretBackend):
    """
    HashiCorp Vault Secret Backend.
    
    Features:
    - KV v1 and v2 support
    - Token and AppRole authentication
    - Secret versioning
    - Lease management
    - Health checking
    """
    
    def __init__(
        self,
        vault_url: str,
        auth_method: str = "token",
        auth_config: Optional[Dict[str, Any]] = None,
        kv_version: int = 2,
        mount_point: str = "secret",
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize Vault Client.
        
        Args:
            vault_url: Vault server URL
            auth_method: Authentication method (token, approle)
            auth_config: Authentication configuration
            kv_version: KV secrets engine version (1 or 2)
            mount_point: Secrets mount point
            timeout: Request timeout
            verify_ssl: Verify SSL certificates
        """
        self.vault_url = vault_url.rstrip('/')
        self.auth_method = auth_method
        self.auth_config = auth_config or {}
        self.kv_version = kv_version
        self.mount_point = mount_point
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        self.logger = logging.getLogger("vault_client")
        
        # Authentication state
        self._token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                verify=self.verify_ssl
            )
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid authentication token."""
        if not self._token or self._is_token_expired():
            await self._authenticate()
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired."""
        if not self._token_expires_at:
            return True
        
        import time
        return time.time() >= self._token_expires_at
    
    async def _authenticate(self):
        """Authenticate with Vault."""
        await self._ensure_client()
        
        if self.auth_method == "token":
            await self._authenticate_token()
        elif self.auth_method == "approle":
            await self._authenticate_approle()
        else:
            raise ConfigurationError(f"Unsupported auth method: {self.auth_method}")
    
    async def _authenticate_token(self):
        """Authenticate using token method."""
        token = self.auth_config.get("token")
        if not token:
            raise ConfigurationError("Token required for token authentication")
        
        self._token = token
        
        # Verify token and get TTL
        try:
            response = await self._client.get(
                f"{self.vault_url}/v1/auth/token/lookup-self",
                headers={"X-Vault-Token": self._token}
            )
            
            if response.status_code == 200:
                token_info = response.json()
                ttl = token_info.get("data", {}).get("ttl", 0)
                
                if ttl > 0:
                    import time
                    self._token_expires_at = time.time() + ttl - 60  # Refresh 1 min early
                
                self.logger.info("Successfully authenticated with Vault using token")
            else:
                raise SecurityError(f"Token validation failed: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"Failed to validate token: {e}")
    
    async def _authenticate_approle(self):
        """Authenticate using AppRole method."""
        role_id = self.auth_config.get("role_id")
        secret_id = self.auth_config.get("secret_id")
        
        if not role_id or not secret_id:
            raise ConfigurationError("role_id and secret_id required for AppRole authentication")
        
        try:
            response = await self._client.post(
                f"{self.vault_url}/v1/auth/approle/login",
                json={
                    "role_id": role_id,
                    "secret_id": secret_id
                }
            )
            
            if response.status_code == 200:
                auth_data = response.json()["auth"]
                self._token = auth_data["client_token"]
                
                # Set token expiration
                lease_duration = auth_data.get("lease_duration", 0)
                if lease_duration > 0:
                    import time
                    self._token_expires_at = time.time() + lease_duration - 60
                
                self.logger.info("Successfully authenticated with Vault using AppRole")
            else:
                raise SecurityError(f"AppRole authentication failed: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"AppRole authentication error: {e}")
    
    async def get_secret(self, key: str, version: Optional[str] = None) -> str:
        """
        Get secret from Vault.
        
        Args:
            key: Secret path
            version: Secret version (KV v2 only)
            
        Returns:
            Secret value
        """
        await self._ensure_authenticated()
        
        # Build secret path
        if self.kv_version == 2:
            path = f"v1/{self.mount_point}/data/{key}"
            params = {"version": version} if version else None
        else:
            path = f"v1/{self.mount_point}/{key}"
            params = None
        
        try:
            response = await self._client.get(
                f"{self.vault_url}/{path}",
                headers={"X-Vault-Token": self._token},
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if self.kv_version == 2:
                    secret_data = data.get("data", {}).get("data", {})
                else:
                    secret_data = data.get("data", {})
                
                # If key contains a field separator, extract specific field
                if ":" in key:
                    key_path, field = key.rsplit(":", 1)
                    if field in secret_data:
                        return secret_data[field]
                    else:
                        raise SecurityError(f"Field '{field}' not found in secret '{key_path}'")
                else:
                    # Return the first value if multiple fields exist
                    if secret_data:
                        return list(secret_data.values())[0]
                    else:
                        raise SecurityError(f"No data found in secret '{key}'")
                        
            elif response.status_code == 404:
                raise SecurityError(f"Secret not found: {key}")
            else:
                raise SecurityError(f"Failed to get secret: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"Vault request error: {e}")
    
    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Set secret in Vault.
        
        Args:
            key: Secret path
            value: Secret value
            metadata: Secret metadata
            
        Returns:
            True if successful
        """
        await self._ensure_authenticated()
        
        # Handle field-specific updates
        if ":" in key:
            key_path, field = key.rsplit(":", 1)
            secret_data = {field: value}
        else:
            secret_data = {"value": value}
        
        # Build request data
        if self.kv_version == 2:
            path = f"v1/{self.mount_point}/data/{key_path if ':' in key else key}"
            request_data = {"data": secret_data}
            if metadata:
                request_data["metadata"] = metadata
        else:
            path = f"v1/{self.mount_point}/{key_path if ':' in key else key}"
            request_data = secret_data
        
        try:
            response = await self._client.post(
                f"{self.vault_url}/{path}",
                headers={"X-Vault-Token": self._token},
                json=request_data
            )
            
            if response.status_code in [200, 204]:
                self.logger.info(f"Successfully set secret: {key}")
                return True
            else:
                raise SecurityError(f"Failed to set secret: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"Vault request error: {e}")
    
    async def delete_secret(self, key: str) -> bool:
        """
        Delete secret from Vault.
        
        Args:
            key: Secret path to delete
            
        Returns:
            True if successful
        """
        await self._ensure_authenticated()
        
        if self.kv_version == 2:
            path = f"v1/{self.mount_point}/metadata/{key}"
        else:
            path = f"v1/{self.mount_point}/{key}"
        
        try:
            response = await self._client.delete(
                f"{self.vault_url}/{path}",
                headers={"X-Vault-Token": self._token}
            )
            
            if response.status_code in [200, 204]:
                self.logger.info(f"Successfully deleted secret: {key}")
                return True
            else:
                raise SecurityError(f"Failed to delete secret: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"Vault request error: {e}")
    
    async def list_secrets(self, prefix: str = "") -> List[str]:
        """
        List secrets in Vault.
        
        Args:
            prefix: Path prefix to filter
            
        Returns:
            List of secret paths
        """
        await self._ensure_authenticated()
        
        if self.kv_version == 2:
            path = f"v1/{self.mount_point}/metadata/{prefix}"
        else:
            path = f"v1/{self.mount_point}/{prefix}"
        
        try:
            response = await self._client.request(
                "LIST",
                f"{self.vault_url}/{path}",
                headers={"X-Vault-Token": self._token}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("keys", [])
            elif response.status_code == 404:
                return []
            else:
                raise SecurityError(f"Failed to list secrets: {response.text}")
                
        except httpx.RequestError as e:
            raise SecurityError(f"Vault request error: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Vault health status."""
        await self._ensure_client()
        
        try:
            response = await self._client.get(f"{self.vault_url}/v1/sys/health")
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "healthy": True,
                    "initialized": health_data.get("initialized", False),
                    "sealed": health_data.get("sealed", True),
                    "version": health_data.get("version", "unknown"),
                }
            else:
                return {
                    "healthy": False,
                    "error": f"Health check failed: {response.status_code}",
                }
                
        except httpx.RequestError as e:
            return {
                "healthy": False,
                "error": f"Health check error: {e}",
            }
    
    async def renew_token(self) -> bool:
        """Renew the current token."""
        if not self._token:
            return False
        
        await self._ensure_client()
        
        try:
            response = await self._client.post(
                f"{self.vault_url}/v1/auth/token/renew-self",
                headers={"X-Vault-Token": self._token}
            )
            
            if response.status_code == 200:
                auth_data = response.json()["auth"]
                lease_duration = auth_data.get("lease_duration", 0)
                
                if lease_duration > 0:
                    import time
                    self._token_expires_at = time.time() + lease_duration - 60
                
                self.logger.info("Successfully renewed Vault token")
                return True
            else:
                self.logger.warning(f"Token renewal failed: {response.text}")
                return False
                
        except httpx.RequestError as e:
            self.logger.error(f"Token renewal error: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def get_client_info(self) -> Dict[str, Any]:
        """Get client configuration information."""
        return {
            "vault_url": self.vault_url,
            "auth_method": self.auth_method,
            "kv_version": self.kv_version,
            "mount_point": self.mount_point,
            "timeout": self.timeout,
            "verify_ssl": self.verify_ssl,
            "authenticated": self._token is not None,
            "token_expired": self._is_token_expired(),
        }
# fastapi-microservices-sdk/fastapi_microservices_sdk/security/secrets/secrets_manager.py
"""
Secrets Manager for FastAPI Microservices SDK.

This module provides a unified interface for managing secrets across
different backends (Vault, environment variables, cloud providers).
"""

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import logging
import json
import base64
from cryptography.fernet import Fernet

from ...exceptions import SecurityError, ConfigurationError


class SecretBackend(ABC):
    """Abstract base class for secret backends."""
    
    @abstractmethod
    async def get_secret(self, key: str, version: Optional[str] = None) -> str:
        """Get a secret value."""
        pass
    
    @abstractmethod
    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a secret value."""
        pass
    
    @abstractmethod
    async def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    async def list_secrets(self, prefix: str = "") -> List[str]:
        """List available secrets."""
        pass


class SecretsManager:
    """
    Unified Secrets Manager with support for multiple backends.
    
    Features:
    - Multiple backend support (Vault, env vars, cloud)
    - Secret caching with TTL
    - Automatic secret rotation
    - Encryption at rest
    - Audit logging
    """
    
    def __init__(
        self,
        primary_backend: SecretBackend,
        fallback_backend: Optional[SecretBackend] = None,
        cache_ttl_seconds: int = 300,
        enable_encryption: bool = True,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize Secrets Manager.
        
        Args:
            primary_backend: Primary secret backend
            fallback_backend: Fallback backend if primary fails
            cache_ttl_seconds: Cache TTL in seconds
            enable_encryption: Enable local encryption
            encryption_key: Encryption key (generated if None)
        """
        self.primary_backend = primary_backend
        self.fallback_backend = fallback_backend
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_encryption = enable_encryption
        
        self.logger = logging.getLogger("secrets_manager")
        
        # Initialize encryption
        if enable_encryption:
            if encryption_key:
                self.encryption_key = encryption_key.encode()
            else:
                self.encryption_key = Fernet.generate_key()
            self.cipher = Fernet(self.encryption_key)
        else:
            self.cipher = None
        
        # Secret cache {key: {value, expires_at, metadata}}
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
        
        # Secret rotation tracking
        self._rotation_schedule: Dict[str, Dict[str, Any]] = {}
    
    async def get_secret(
        self,
        key: str,
        use_cache: bool = True,
        fallback_on_error: bool = True
    ) -> str:
        """
        Get a secret value.
        
        Args:
            key: Secret key
            use_cache: Use cached value if available
            fallback_on_error: Use fallback backend on error
            
        Returns:
            Secret value
            
        Raises:
            SecurityError: If secret cannot be retrieved
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache and self._is_cached_and_valid(key):
                cached_value = self._get_from_cache(key)
                self._log_secret_access(key, "cache_hit", start_time)
                return cached_value
            
            # Try primary backend
            try:
                value = await self.primary_backend.get_secret(key)
                
                # Cache the value
                if use_cache:
                    self._cache_secret(key, value)
                
                self._log_secret_access(key, "primary_backend", start_time)
                return value
                
            except Exception as e:
                self.logger.warning(f"Primary backend failed for {key}: {e}")
                
                # Try fallback backend
                if fallback_on_error and self.fallback_backend:
                    try:
                        value = await self.fallback_backend.get_secret(key)
                        
                        # Cache the value
                        if use_cache:
                            self._cache_secret(key, value)
                        
                        self._log_secret_access(key, "fallback_backend", start_time)
                        return value
                        
                    except Exception as fallback_error:
                        self.logger.error(f"Fallback backend also failed for {key}: {fallback_error}")
                        raise SecurityError(f"All backends failed for secret {key}")
                else:
                    raise SecurityError(f"Failed to get secret {key}: {e}")
                    
        except SecurityError:
            self._log_secret_access(key, "error", start_time)
            raise
        except Exception as e:
            self._log_secret_access(key, "error", start_time)
            raise SecurityError(f"Unexpected error getting secret {key}: {e}")
    
    async def set_secret(
        self,
        key: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
        update_cache: bool = True
    ) -> bool:
        """
        Set a secret value.
        
        Args:
            key: Secret key
            value: Secret value
            metadata: Secret metadata
            update_cache: Update cache after setting
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            # Set in primary backend
            success = await self.primary_backend.set_secret(key, value, metadata)
            
            if success and update_cache:
                self._cache_secret(key, value, metadata)
            
            self._log_secret_operation(key, "set", start_time, success)
            return success
            
        except Exception as e:
            self._log_secret_operation(key, "set", start_time, False)
            raise SecurityError(f"Failed to set secret {key}: {e}")
    
    async def delete_secret(self, key: str, remove_from_cache: bool = True) -> bool:
        """
        Delete a secret.
        
        Args:
            key: Secret key to delete
            remove_from_cache: Remove from cache
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            # Delete from primary backend
            success = await self.primary_backend.delete_secret(key)
            
            if success and remove_from_cache:
                self._remove_from_cache(key)
            
            self._log_secret_operation(key, "delete", start_time, success)
            return success
            
        except Exception as e:
            self._log_secret_operation(key, "delete", start_time, False)
            raise SecurityError(f"Failed to delete secret {key}: {e}")
    
    async def list_secrets(self, prefix: str = "") -> List[str]:
        """List available secrets."""
        try:
            return await self.primary_backend.list_secrets(prefix)
        except Exception as e:
            if self.fallback_backend:
                try:
                    return await self.fallback_backend.list_secrets(prefix)
                except Exception:
                    pass
            raise SecurityError(f"Failed to list secrets: {e}")
    
    def _is_cached_and_valid(self, key: str) -> bool:
        """Check if secret is cached and still valid."""
        if key not in self._cache:
            return False
        
        cache_entry = self._cache[key]
        expires_at = cache_entry.get("expires_at")
        
        if expires_at and datetime.utcnow() > expires_at:
            # Expired, remove from cache
            del self._cache[key]
            return False
        
        return True
    
    def _get_from_cache(self, key: str) -> str:
        """Get secret from cache."""
        cache_entry = self._cache[key]
        encrypted_value = cache_entry["value"]
        
        if self.enable_encryption and self.cipher:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        else:
            return encrypted_value
    
    def _cache_secret(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None):
        """Cache a secret value."""
        expires_at = datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds)
        
        # Encrypt value if encryption is enabled
        if self.enable_encryption and self.cipher:
            encrypted_value = self.cipher.encrypt(value.encode()).decode()
        else:
            encrypted_value = value
        
        self._cache[key] = {
            "value": encrypted_value,
            "expires_at": expires_at,
            "cached_at": datetime.utcnow(),
            "metadata": metadata or {},
        }
    
    def _remove_from_cache(self, key: str):
        """Remove secret from cache."""
        if key in self._cache:
            del self._cache[key]
    
    def _log_secret_access(self, key: str, source: str, start_time: float):
        """Log secret access."""
        duration = time.time() - start_time
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "secret_access",
            "key": key,
            "source": source,
            "duration_ms": round(duration * 1000, 2),
        }
        
        self._audit_log.append(log_entry)
        self.logger.debug(f"Secret accessed: {key} from {source}")
    
    def _log_secret_operation(self, key: str, operation: str, start_time: float, success: bool):
        """Log secret operation."""
        duration = time.time() - start_time
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "secret_operation",
            "key": key,
            "operation": operation,
            "success": success,
            "duration_ms": round(duration * 1000, 2),
        }
        
        self._audit_log.append(log_entry)
        self.logger.info(f"Secret {operation}: {key} - {'success' if success else 'failed'}")
    
    def schedule_rotation(
        self,
        key: str,
        rotation_interval_days: int = 30,
        rotation_callback: Optional[callable] = None
    ):
        """
        Schedule automatic secret rotation.
        
        Args:
            key: Secret key to rotate
            rotation_interval_days: Rotation interval in days
            rotation_callback: Callback function for rotation
        """
        next_rotation = datetime.utcnow() + timedelta(days=rotation_interval_days)
        
        self._rotation_schedule[key] = {
            "next_rotation": next_rotation,
            "interval_days": rotation_interval_days,
            "callback": rotation_callback,
            "scheduled_at": datetime.utcnow(),
        }
        
        self.logger.info(f"Scheduled rotation for {key} at {next_rotation}")
    
    async def check_rotations(self):
        """Check and perform scheduled rotations."""
        now = datetime.utcnow()
        rotated_secrets = []
        
        for key, rotation_info in self._rotation_schedule.items():
            next_rotation = rotation_info["next_rotation"]
            
            if now >= next_rotation:
                try:
                    # Perform rotation
                    if rotation_info.get("callback"):
                        new_value = rotation_info["callback"]()
                    else:
                        # Generate new random value (placeholder)
                        new_value = base64.urlsafe_b64encode(os.urandom(32)).decode()
                    
                    # Update secret
                    await self.set_secret(key, new_value)
                    
                    # Schedule next rotation
                    interval_days = rotation_info["interval_days"]
                    rotation_info["next_rotation"] = now + timedelta(days=interval_days)
                    rotation_info["last_rotated"] = now
                    
                    rotated_secrets.append(key)
                    self.logger.info(f"Rotated secret: {key}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to rotate secret {key}: {e}")
        
        return rotated_secrets
    
    def clear_cache(self, key: Optional[str] = None):
        """Clear secret cache."""
        if key:
            self._remove_from_cache(key)
        else:
            self._cache.clear()
        
        self.logger.info(f"Cleared cache for {'all secrets' if not key else key}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        expired_count = 0
        
        for cache_entry in self._cache.values():
            expires_at = cache_entry.get("expires_at")
            if expires_at and now > expires_at:
                expired_count += 1
        
        return {
            "total_cached_secrets": len(self._cache),
            "expired_secrets": expired_count,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "encryption_enabled": self.enable_encryption,
        }
    
    def get_rotation_stats(self) -> Dict[str, Any]:
        """Get rotation statistics."""
        now = datetime.utcnow()
        due_rotations = 0
        
        for rotation_info in self._rotation_schedule.values():
            if now >= rotation_info["next_rotation"]:
                due_rotations += 1
        
        return {
            "scheduled_rotations": len(self._rotation_schedule),
            "due_rotations": due_rotations,
            "rotation_schedule": {
                key: {
                    "next_rotation": info["next_rotation"].isoformat(),
                    "interval_days": info["interval_days"],
                }
                for key, info in self._rotation_schedule.items()
            }
        }
    
    def export_audit_log(self) -> List[Dict[str, Any]]:
        """Export audit log."""
        return self._audit_log.copy()
    
    def clear_audit_log(self, older_than_hours: int = 24):
        """Clear old audit log entries."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        original_count = len(self._audit_log)
        self._audit_log = [
            log for log in self._audit_log 
            if datetime.fromisoformat(log["timestamp"]) > cutoff
        ]
        
        cleared_count = original_count - len(self._audit_log)
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old audit log entries")
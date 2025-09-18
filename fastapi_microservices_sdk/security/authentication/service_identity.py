# fastapi-microservices-sdk/fastapi_microservices_sdk/security/authentication/service_identity.py
"""
Service Identity Management for FastAPI Microservices SDK.

This module manages service identities, certificates, and trust relationships
between microservices in a secure and scalable way.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
import logging
import json

from ...exceptions import SecurityError
from ...utils.helpers import get_hostname, get_local_ip


class ServiceIdentity:
    """
    Service Identity Manager for microservices.
    
    Features:
    - Unique service identity generation
    - Service fingerprinting
    - Trust relationship management
    - Identity verification
    - Service metadata management
    """
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: str = "development",
        trust_store_enabled: bool = True
    ):
        """
        Initialize Service Identity.
        
        Args:
            service_name: Name of the service
            service_version: Version of the service
            environment: Environment (dev, staging, prod)
            trust_store_enabled: Enable trust store management
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.trust_store_enabled = trust_store_enabled
        
        self.logger = logging.getLogger(f"service_identity.{service_name}")
        
        # Generate unique service identity
        self.service_id = self._generate_service_id()
        self.service_fingerprint = self._generate_service_fingerprint()
        
        # Trust store (in production, use external store)
        self._trusted_services: Dict[str, Dict[str, Any]] = {}
        self._blocked_services: Set[str] = set()
        
        # Service metadata
        self.metadata = self._collect_service_metadata()
        
        self.logger.info(f"Service identity initialized: {self.service_id}")
    
    def _generate_service_id(self) -> str:
        """Generate unique service ID."""
        # Combine service name, hostname, and timestamp for uniqueness
        hostname = get_hostname()
        timestamp = datetime.utcnow().isoformat()
        
        identity_string = f"{self.service_name}:{hostname}:{timestamp}:{uuid.uuid4()}"
        service_id = hashlib.sha256(identity_string.encode()).hexdigest()[:16]
        
        return f"{self.service_name}-{service_id}"
    
    def _generate_service_fingerprint(self) -> str:
        """Generate service fingerprint for verification."""
        # Create fingerprint based on service characteristics
        fingerprint_data = {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "environment": self.environment,
            "hostname": get_hostname(),
            "local_ip": get_local_ip(),
        }
        
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    def _collect_service_metadata(self) -> Dict[str, Any]:
        """Collect service metadata for identity."""
        return {
            "service_name": self.service_name,
            "service_id": self.service_id,
            "service_version": self.service_version,
            "environment": self.environment,
            "hostname": get_hostname(),
            "local_ip": get_local_ip(),
            "fingerprint": self.service_fingerprint,
            "created_at": datetime.utcnow().isoformat(),
            "sdk_version": "0.1.0",  # TODO: Get from version module
        }
    
    def get_identity_claims(self) -> Dict[str, Any]:
        """
        Get identity claims for JWT tokens.
        
        Returns:
            Dictionary of identity claims
        """
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_version": self.service_version,
            "service_fingerprint": self.service_fingerprint,
            "environment": self.environment,
            "hostname": get_hostname(),
            "identity_verified": True,
        }
    
    def verify_service_identity(
        self,
        claims: Dict[str, Any],
        strict_verification: bool = True
    ) -> bool:
        """
        Verify another service's identity claims.
        
        Args:
            claims: Identity claims from another service
            strict_verification: Enable strict verification
            
        Returns:
            True if identity is verified
            
        Raises:
            SecurityError: If verification fails
        """
        try:
            # Required claims check
            required_claims = [
                "service_id", "service_name", "service_fingerprint"
            ]
            
            missing_claims = [claim for claim in required_claims if claim not in claims]
            if missing_claims:
                raise SecurityError(f"Missing identity claims: {missing_claims}")
            
            service_name = claims["service_name"]
            service_id = claims["service_id"]
            fingerprint = claims["service_fingerprint"]
            
            # Check if service is blocked
            if service_name in self._blocked_services or service_id in self._blocked_services:
                raise SecurityError(f"Service {service_name} is blocked")
            
            # Trust store verification
            if self.trust_store_enabled and strict_verification:
                if not self._verify_against_trust_store(claims):
                    raise SecurityError(f"Service {service_name} not in trust store")
            
            # Fingerprint verification (if we have it in trust store)
            if service_name in self._trusted_services:
                trusted_fingerprint = self._trusted_services[service_name].get("fingerprint")
                if trusted_fingerprint and trusted_fingerprint != fingerprint:
                    raise SecurityError(f"Service fingerprint mismatch for {service_name}")
            
            self.logger.debug(f"Verified identity for service: {service_name}")
            return True
            
        except SecurityError:
            raise
        except Exception as e:
            raise SecurityError(f"Identity verification failed: {e}")
    
    def _verify_against_trust_store(self, claims: Dict[str, Any]) -> bool:
        """Verify claims against trust store."""
        service_name = claims["service_name"]
        
        if service_name not in self._trusted_services:
            return False
        
        trusted_service = self._trusted_services[service_name]
        
        # Check if trust is still valid
        if "expires_at" in trusted_service:
            expires_at = datetime.fromisoformat(trusted_service["expires_at"])
            if datetime.utcnow() > expires_at:
                self.logger.warning(f"Trust expired for service: {service_name}")
                return False
        
        return True
    
    def add_trusted_service(
        self,
        service_name: str,
        service_fingerprint: str,
        permissions: Optional[List[str]] = None,
        expires_in_days: int = 30,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a service to the trust store.
        
        Args:
            service_name: Name of the trusted service
            service_fingerprint: Service fingerprint
            permissions: Permissions granted to the service
            expires_in_days: Trust expiration in days
            metadata: Additional metadata
        """
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        trust_entry = {
            "service_name": service_name,
            "fingerprint": service_fingerprint,
            "permissions": permissions or ["service_call"],
            "added_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "added_by": self.service_name,
            "metadata": metadata or {},
        }
        
        self._trusted_services[service_name] = trust_entry
        
        self.logger.info(f"Added trusted service: {service_name}")
    
    def remove_trusted_service(self, service_name: str):
        """Remove a service from the trust store."""
        if service_name in self._trusted_services:
            del self._trusted_services[service_name]
            self.logger.info(f"Removed trusted service: {service_name}")
    
    def block_service(self, service_name: str, reason: str = "Security policy"):
        """
        Block a service.
        
        Args:
            service_name: Service to block
            reason: Reason for blocking
        """
        self._blocked_services.add(service_name)
        self.logger.warning(f"Blocked service {service_name}: {reason}")
    
    def unblock_service(self, service_name: str):
        """Unblock a service."""
        self._blocked_services.discard(service_name)
        self.logger.info(f"Unblocked service: {service_name}")
    
    def is_service_trusted(self, service_name: str) -> bool:
        """Check if a service is trusted."""
        if service_name in self._blocked_services:
            return False
        
        if not self.trust_store_enabled:
            return True  # Trust all if trust store disabled
        
        return service_name in self._trusted_services
    
    def get_service_permissions(self, service_name: str) -> List[str]:
        """Get permissions for a trusted service."""
        if service_name in self._trusted_services:
            return self._trusted_services[service_name].get("permissions", [])
        return []
    
    def refresh_identity(self):
        """Refresh service identity (new fingerprint)."""
        old_fingerprint = self.service_fingerprint
        self.service_fingerprint = self._generate_service_fingerprint()
        self.metadata["fingerprint"] = self.service_fingerprint
        self.metadata["last_refreshed"] = datetime.utcnow().isoformat()
        
        self.logger.info(f"Refreshed service identity. Old: {old_fingerprint[:8]}..., New: {self.service_fingerprint[:8]}...")
    
    def export_identity(self) -> Dict[str, Any]:
        """Export service identity for sharing."""
        return {
            "service_name": self.service_name,
            "service_id": self.service_id,
            "service_version": self.service_version,
            "fingerprint": self.service_fingerprint,
            "environment": self.environment,
            "metadata": self.metadata.copy(),
            "exported_at": datetime.utcnow().isoformat(),
        }
    
    def import_trusted_services(self, trusted_services: Dict[str, Dict[str, Any]]):
        """Import trusted services from external source."""
        imported_count = 0
        
        for service_name, trust_data in trusted_services.items():
            try:
                # Validate trust data
                required_fields = ["fingerprint", "permissions"]
                if all(field in trust_data for field in required_fields):
                    self._trusted_services[service_name] = trust_data
                    imported_count += 1
                else:
                    self.logger.warning(f"Invalid trust data for {service_name}")
            except Exception as e:
                self.logger.error(f"Failed to import trust data for {service_name}: {e}")
        
        self.logger.info(f"Imported {imported_count} trusted services")
    
    def get_trust_store_stats(self) -> Dict[str, Any]:
        """Get trust store statistics."""
        now = datetime.utcnow()
        expired_count = 0
        
        for service_data in self._trusted_services.values():
            if "expires_at" in service_data:
                expires_at = datetime.fromisoformat(service_data["expires_at"])
                if now > expires_at:
                    expired_count += 1
        
        return {
            "total_trusted_services": len(self._trusted_services),
            "blocked_services": len(self._blocked_services),
            "expired_trusts": expired_count,
            "trust_store_enabled": self.trust_store_enabled,
            "service_identity": {
                "service_id": self.service_id,
                "fingerprint": self.service_fingerprint[:8] + "...",
                "environment": self.environment,
            }
        }
    
    def cleanup_expired_trusts(self):
        """Remove expired trust entries."""
        now = datetime.utcnow()
        expired_services = []
        
        for service_name, trust_data in self._trusted_services.items():
            if "expires_at" in trust_data:
                expires_at = datetime.fromisoformat(trust_data["expires_at"])
                if now > expires_at:
                    expired_services.append(service_name)
        
        for service_name in expired_services:
            del self._trusted_services[service_name]
            self.logger.info(f"Removed expired trust for service: {service_name}")
        
        return len(expired_services)
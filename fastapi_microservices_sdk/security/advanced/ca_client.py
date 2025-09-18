"""
Certificate Authority (CA) Client for FastAPI Microservices SDK.
This module provides integration with Certificate Authorities for automatic
certificate request, renewal, and revocation workflows.
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import base64
import secrets
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.x509.oid import NameOID, ExtensionOID

from .certificates import Certificate, CertificateInfo
from .exceptions import CertificateError, MTLSError
from .logging import get_security_logger, CertificateEvent
from .config import CertificateManagementConfig


class CAProtocol(Enum):
    """Certificate Authority protocol types."""
    ACME = "acme"  # Automated Certificate Management Environment (Let's Encrypt)
    EST = "est"    # Enrollment over Secure Transport
    SCEP = "scep"  # Simple Certificate Enrollment Protocol
    REST = "rest"  # Custom REST API
    VAULT = "vault"  # HashiCorp Vault PKI


class CertificateRequestStatus(Enum):
    """Certificate request status."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ISSUED = "issued"
    FAILED = "failed"
    REVOKED = "revoked"


@dataclass
class CertificateRequest:
    """Certificate request data."""
    request_id: str
    common_name: str
    subject_alt_names: List[str] = field(default_factory=list)
    key_type: str = "rsa"
    key_size: int = 2048
    validity_days: int = 365
    organization: Optional[str] = None
    organizational_unit: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    email: Optional[str] = None
    status: CertificateRequestStatus = CertificateRequestStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    certificate_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "common_name": self.common_name,
            "subject_alt_names": self.subject_alt_names,
            "key_type": self.key_type,
            "key_size": self.key_size,
            "validity_days": self.validity_days,
            "organization": self.organization,
            "organizational_unit": self.organizational_unit,
            "country": self.country,
            "state": self.state,
            "locality": self.locality,
            "email": self.email,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "certificate_id": self.certificate_id,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CertificateRequest':
        """Create from dictionary."""
        return cls(
            request_id=data["request_id"],
            common_name=data["common_name"],
            subject_alt_names=data.get("subject_alt_names", []),
            key_type=data.get("key_type", "rsa"),
            key_size=data.get("key_size", 2048),
            validity_days=data.get("validity_days", 365),
            organization=data.get("organization"),
            organizational_unit=data.get("organizational_unit"),
            country=data.get("country"),
            state=data.get("state"),
            locality=data.get("locality"),
            email=data.get("email"),
            status=CertificateRequestStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            certificate_id=data.get("certificate_id"),
            error_message=data.get("error_message"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )


@dataclass
class CAConfig:
    """Certificate Authority configuration."""
    protocol: CAProtocol
    base_url: str
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.base_url:
            raise ValueError("CA base_url is required")
        
        # Protocol-specific validation
        if self.protocol == CAProtocol.VAULT:
            if not self.api_key:
                raise ValueError("Vault protocol requires api_key")
        elif self.protocol == CAProtocol.EST:
            if not (self.client_cert_path and self.client_key_path):
                raise ValueError("EST protocol requires client certificate and key")


class ExponentialBackoff:
    """Exponential backoff for retry logic."""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 60.0, multiplier: float = 2.0):
        """Initialize backoff strategy."""
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.current_delay = initial_delay
    
    def get_delay(self, attempt: int) -> float:
        """Get delay for current attempt."""
        delay = min(self.initial_delay * (self.multiplier ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (2 * secrets.SystemRandom().random() - 1)
        return max(0, delay + jitter)
    
    def reset(self):
        """Reset backoff to initial state."""
        self.current_delay = self.initial_delay


class CAClient:
    """
    Certificate Authority client for automated certificate management.
    Supports multiple CA protocols and provides retry logic with exponential backoff.
    """
    
    def __init__(self, config: CAConfig):
        """Initialize CA client."""
        self.config = config
        self._logger = get_security_logger()
        self._backoff = ExponentialBackoff(
            initial_delay=config.retry_delay,
            max_delay=60.0,
            multiplier=2.0
        )
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.verify_ssl
        )
        
        # Load client certificates if provided
        if config.client_cert_path and config.client_key_path:
            self._client.cert = (config.client_cert_path, config.client_key_path)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
    
    def _generate_csr(self, request: CertificateRequest) -> Tuple[bytes, bytes]:
        """Generate Certificate Signing Request (CSR) and private key."""
        try:
            # Generate private key
            if request.key_type.lower() == "rsa":
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=request.key_size
                )
            elif request.key_type.lower() == "ec":
                private_key = ec.generate_private_key(ec.SECP256R1())
            else:
                raise ValueError(f"Unsupported key type: {request.key_type}")
            
            # Build subject
            subject_components = [
                x509.NameAttribute(NameOID.COMMON_NAME, request.common_name)
            ]
            
            if request.organization:
                subject_components.append(
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, request.organization)
                )
            
            if request.organizational_unit:
                subject_components.append(
                    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, request.organizational_unit)
                )
            
            if request.country:
                subject_components.append(
                    x509.NameAttribute(NameOID.COUNTRY_NAME, request.country)
                )
            
            if request.state:
                subject_components.append(
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, request.state)
                )
            
            if request.locality:
                subject_components.append(
                    x509.NameAttribute(NameOID.LOCALITY_NAME, request.locality)
                )
            
            if request.email:
                subject_components.append(
                    x509.NameAttribute(NameOID.EMAIL_ADDRESS, request.email)
                )
            
            subject = x509.Name(subject_components)
            
            # Build CSR
            builder = x509.CertificateSigningRequestBuilder()
            builder = builder.subject_name(subject)
            
            # Add Subject Alternative Names if provided
            if request.subject_alt_names:
                san_list = []
                for san in request.subject_alt_names:
                    if san.startswith("DNS:"):
                        san_list.append(x509.DNSName(san[4:]))
                    elif san.startswith("IP:"):
                        san_list.append(x509.IPAddress(san[3:]))
                    elif san.startswith("email:"):
                        san_list.append(x509.RFC822Name(san[6:]))
                    else:
                        # Default to DNS name
                        san_list.append(x509.DNSName(san))
                
                if san_list:
                    builder = builder.add_extension(
                        x509.SubjectAlternativeName(san_list),
                        critical=False
                    )
            
            # Sign CSR
            csr = builder.sign(private_key, hashes.SHA256())
            
            # Serialize CSR and private key
            csr_pem = csr.public_bytes(serialization.Encoding.PEM)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            return csr_pem, key_pem
            
        except Exception as e:
            raise CertificateError(f"Failed to generate CSR: {e}")
    
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        attempt = 0
        last_exception = None
        
        while attempt < self.config.max_retries:
            try:
                # Prepare headers
                request_headers = {}
                if headers:
                    request_headers.update(headers)
                
                # Add authentication headers based on protocol
                if self.config.protocol == CAProtocol.VAULT and self.config.api_key:
                    request_headers["X-Vault-Token"] = self.config.api_key
                elif self.config.username and self.config.password:
                    auth_string = base64.b64encode(
                        f"{self.config.username}:{self.config.password}".encode()
                    ).decode()
                    request_headers["Authorization"] = f"Basic {auth_string}"
                
                # Make request
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    data=data,
                    json=json_data
                )
                
                # Check for success
                if response.status_code < 400:
                    return response
                
                # Handle specific error codes
                if response.status_code in [401, 403]:
                    raise CertificateError(f"Authentication failed: {response.status_code}")
                elif response.status_code == 404:
                    raise CertificateError(f"CA endpoint not found: {url}")
                elif response.status_code >= 500:
                    # Server error, retry
                    last_exception = CertificateError(
                        f"CA server error: {response.status_code} - {response.text}"
                    )
                else:
                    # Client error, don't retry
                    raise CertificateError(
                        f"CA request failed: {response.status_code} - {response.text}"
                    )
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = CertificateError(f"CA communication error: {e}")
            
            # Wait before retry
            if attempt < self.config.max_retries - 1:
                delay = self._backoff.get_delay(attempt)
                self._logger.log_certificate_event(
                    certificate_id="ca_client",
                    operation="retry",
                    details={
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error": str(last_exception)
                    }
                )
                await asyncio.sleep(delay)
            
            attempt += 1
        
        # All retries exhausted
        raise last_exception or CertificateError("CA request failed after all retries")
    
    async def request_certificate(self, request: CertificateRequest) -> str:
        """
        Request a new certificate from the CA.
        Returns the request ID for tracking.
        """
        try:
            # Generate CSR and private key
            csr_pem, key_pem = self._generate_csr(request)
            
            # Store private key securely (implementation depends on storage backend)
            # For now, we'll include it in the request tracking
            
            # Protocol-specific certificate request
            if self.config.protocol == CAProtocol.VAULT:
                response = await self._request_vault_certificate(request, csr_pem)
            elif self.config.protocol == CAProtocol.ACME:
                response = await self._request_acme_certificate(request, csr_pem)
            elif self.config.protocol == CAProtocol.REST:
                response = await self._request_rest_certificate(request, csr_pem)
            else:
                raise CertificateError(f"Unsupported CA protocol: {self.config.protocol}")
            
            # Update request status
            request.status = CertificateRequestStatus.PROCESSING
            request.updated_at = datetime.now(timezone.utc)
            
            self._logger.log_certificate_event(
                certificate_id=request.request_id,
                operation="ca_request",
                certificate_subject=request.common_name,
                details={
                    "protocol": self.config.protocol.value,
                    "ca_url": self.config.base_url,
                    "validity_days": request.validity_days
                }
            )
            
            return request.request_id
            
        except Exception as e:
            request.status = CertificateRequestStatus.FAILED
            request.error_message = str(e)
            request.updated_at = datetime.now(timezone.utc)
            
            self._logger.log_certificate_event(
                certificate_id=request.request_id,
                operation="ca_request_failed",
                certificate_subject=request.common_name,
                details={"error": str(e)}
            )
            
            raise CertificateError(f"Certificate request failed: {e}")
    
    async def _request_vault_certificate(self, request: CertificateRequest, csr_pem: bytes) -> Dict[str, Any]:
        """Request certificate from HashiCorp Vault PKI."""
        url = f"{self.config.base_url}/v1/pki/sign/default"
        
        # Convert CSR to string
        csr_str = csr_pem.decode('utf-8')
        
        data = {
            "csr": csr_str,
            "common_name": request.common_name,
            "ttl": f"{request.validity_days}d"
        }
        
        if request.subject_alt_names:
            data["alt_names"] = ",".join(request.subject_alt_names)
        
        response = await self._make_request("POST", url, json_data=data)
        return response.json()
    
    async def _request_acme_certificate(self, request: CertificateRequest, csr_pem: bytes) -> Dict[str, Any]:
        """Request certificate using ACME protocol (Let's Encrypt)."""
        # ACME implementation would be more complex, involving:
        # 1. Account creation/registration
        # 2. Order creation
        # 3. Authorization challenges (HTTP-01, DNS-01, TLS-ALPN-01)
        # 4. Challenge completion
        # 5. Certificate finalization
        # This is a simplified placeholder
        raise NotImplementedError("ACME protocol implementation requires full ACME client")
    
    async def _request_rest_certificate(self, request: CertificateRequest, csr_pem: bytes) -> Dict[str, Any]:
        """Request certificate using custom REST API."""
        url = f"{self.config.base_url}/api/v1/certificates"
        
        data = {
            "csr": base64.b64encode(csr_pem).decode('utf-8'),
            "common_name": request.common_name,
            "subject_alt_names": request.subject_alt_names,
            "validity_days": request.validity_days
        }
        
        response = await self._make_request("POST", url, json_data=data)
        return response.json()
    
    async def get_certificate_status(self, request_id: str) -> CertificateRequestStatus:
        """Get the status of a certificate request."""
        try:
            if self.config.protocol == CAProtocol.VAULT:
                # Vault typically returns certificates immediately
                return CertificateRequestStatus.READY
            elif self.config.protocol == CAProtocol.REST:
                url = f"{self.config.base_url}/api/v1/certificates/{request_id}/status"
                response = await self._make_request("GET", url)
                data = response.json()
                return CertificateRequestStatus(data.get("status", "pending"))
            else:
                raise CertificateError(f"Status check not implemented for protocol: {self.config.protocol}")
                
        except Exception as e:
            self._logger.log_certificate_event(
                certificate_id=request_id,
                operation="status_check_failed",
                details={"error": str(e)}
            )
            raise CertificateError(f"Failed to check certificate status: {e}")
    
    async def retrieve_certificate(self, request_id: str) -> Certificate:
        """Retrieve an issued certificate."""
        try:
            if self.config.protocol == CAProtocol.VAULT:
                # For Vault, we would need to store the response from the initial request
                # This is a simplified implementation
                raise NotImplementedError("Certificate retrieval from Vault requires request tracking")
            elif self.config.protocol == CAProtocol.REST:
                url = f"{self.config.base_url}/api/v1/certificates/{request_id}"
                response = await self._make_request("GET", url)
                data = response.json()
                
                cert_pem = data.get("certificate")
                if not cert_pem:
                    raise CertificateError("Certificate not found in response")
                
                certificate = Certificate(cert_pem, certificate_id=request_id)
                
                self._logger.log_certificate_event(
                    certificate_id=request_id,
                    operation="ca_retrieve",
                    certificate_subject=certificate.info.subject,
                    certificate_issuer=certificate.info.issuer
                )
                
                return certificate
            else:
                raise CertificateError(f"Certificate retrieval not implemented for protocol: {self.config.protocol}")
                
        except Exception as e:
            self._logger.log_certificate_event(
                certificate_id=request_id,
                operation="ca_retrieve_failed",
                details={"error": str(e)}
            )
            raise CertificateError(f"Failed to retrieve certificate: {e}")
    
    async def revoke_certificate(self, certificate: Certificate, reason: str = "unspecified") -> bool:
        """Revoke a certificate."""
        try:
            if self.config.protocol == CAProtocol.VAULT:
                url = f"{self.config.base_url}/v1/pki/revoke"
                data = {
                    "serial_number": certificate.info.serial_number
                }
                response = await self._make_request("POST", url, json_data=data)
                success = response.status_code == 200
            elif self.config.protocol == CAProtocol.REST:
                url = f"{self.config.base_url}/api/v1/certificates/{certificate.certificate_id}/revoke"
                data = {
                    "reason": reason,
                    "serial_number": certificate.info.serial_number
                }
                response = await self._make_request("POST", url, json_data=data)
                success = response.status_code == 200
            else:
                raise CertificateError(f"Certificate revocation not implemented for protocol: {self.config.protocol}")
            
            if success:
                self._logger.log_certificate_event(
                    certificate_id=certificate.certificate_id,
                    operation="ca_revoke",
                    certificate_subject=certificate.info.subject,
                    details={"reason": reason}
                )
            
            return success
            
        except Exception as e:
            self._logger.log_certificate_event(
                certificate_id=certificate.certificate_id,
                operation="ca_revoke_failed",
                certificate_subject=certificate.info.subject,
                details={"error": str(e)}
            )
            raise CertificateError(f"Failed to revoke certificate: {e}")
    
    async def renew_certificate(self, certificate: Certificate, validity_days: int = 365) -> CertificateRequest:
        """Renew an existing certificate."""
        try:
            # Create renewal request based on existing certificate
            request = CertificateRequest(
                request_id=f"renewal_{certificate.certificate_id}_{int(time.time())}",
                common_name=certificate.info.subject.split("CN=")[1].split(",")[0] if "CN=" in certificate.info.subject else certificate.info.subject,
                subject_alt_names=certificate.info.subject_alt_names,
                validity_days=validity_days,
                # Extract other subject components if available
                organization=certificate.info.subject.split("O=")[1].split(",")[0] if "O=" in certificate.info.subject else None,
                organizational_unit=certificate.info.subject.split("OU=")[1].split(",")[0] if "OU=" in certificate.info.subject else None,
                country=certificate.info.subject.split("C=")[1].split(",")[0] if "C=" in certificate.info.subject else None,
                state=certificate.info.subject.split("ST=")[1].split(",")[0] if "ST=" in certificate.info.subject else None,
                locality=certificate.info.subject.split("L=")[1].split(",")[0] if "L=" in certificate.info.subject else None
            )
            
            # Request new certificate
            await self.request_certificate(request)
            
            self._logger.log_certificate_event(
                certificate_id=certificate.certificate_id,
                operation="ca_renew",
                certificate_subject=certificate.info.subject,
                details={
                    "new_request_id": request.request_id,
                    "validity_days": validity_days
                }
            )
            
            return request
            
        except Exception as e:
            self._logger.log_certificate_event(
                certificate_id=certificate.certificate_id,
                operation="ca_renew_failed",
                certificate_subject=certificate.info.subject,
                details={"error": str(e)}
            )
            raise CertificateError(f"Failed to renew certificate: {e}")


class CAClientFactory:
    """Factory for creating CA clients based on configuration."""
    
    @staticmethod
    def create_client(config: CAConfig) -> CAClient:
        """Create CA client based on configuration."""
        return CAClient(config)
    
    @staticmethod
    def create_vault_client(
        vault_url: str,
        vault_token: str,
        pki_path: str = "pki",
        **kwargs
    ) -> CAClient:
        """Create Vault PKI client."""
        config = CAConfig(
            protocol=CAProtocol.VAULT,
            base_url=f"{vault_url}/{pki_path}",
            api_key=vault_token,
            **kwargs
        )
        return CAClient(config)
    
    @staticmethod
    def create_rest_client(
        api_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ) -> CAClient:
        """Create REST API client."""
        config = CAConfig(
            protocol=CAProtocol.REST,
            base_url=api_url,
            api_key=api_key,
            username=username,
            password=password,
            **kwargs
        )
        return CAClient(config)


# Convenience functions
async def request_certificate_from_vault(
    vault_url: str,
    vault_token: str,
    common_name: str,
    subject_alt_names: Optional[List[str]] = None,
    validity_days: int = 365,
    **kwargs
) -> Tuple[CertificateRequest, CAClient]:
    """Convenience function to request certificate from Vault."""
    client = CAClientFactory.create_vault_client(vault_url, vault_token)
    
    request = CertificateRequest(
        request_id=f"vault_{common_name}_{int(time.time())}",
        common_name=common_name,
        subject_alt_names=subject_alt_names or [],
        validity_days=validity_days,
        **kwargs
    )
    
    await client.request_certificate(request)
    return request, client


async def request_certificate_from_rest_api(
    api_url: str,
    common_name: str,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    subject_alt_names: Optional[List[str]] = None,
    validity_days: int = 365,
    **kwargs
) -> Tuple[CertificateRequest, CAClient]:
    """Convenience function to request certificate from REST API."""
    client = CAClientFactory.create_rest_client(
        api_url, api_key, username, password
    )
    
    request = CertificateRequest(
        request_id=f"rest_{common_name}_{int(time.time())}",
        common_name=common_name,
        subject_alt_names=subject_alt_names or [],
        validity_days=validity_days,
        **kwargs
    )
    
    await client.request_certificate(request)
    return request, client
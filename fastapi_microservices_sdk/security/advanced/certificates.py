"""
Certificate Management for FastAPI Microservices SDK.
This module provides comprehensive X.509 certificate management including
parsing, validation, chain verification, and CRL checking.
"""
import os
import ssl
import hashlib
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import urllib.request
import urllib.error
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.x509.oid import NameOID, ExtensionOID
import ipaddress

from .exceptions import CertificateError, CertificateValidationError
from .logging import get_security_logger, CertificateEvent


class CertificateFormat(Enum):
    """Certificate format types."""
    PEM = "PEM"
    DER = "DER"


class CertificateStatus(Enum):
    """Certificate status."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class KeyType(Enum):
    """Certificate key types."""
    RSA = "RSA"
    EC = "EC"
    UNKNOWN = "UNKNOWN"


@dataclass
class CertificateInfo:
    """Certificate information extracted from X.509 certificate."""
    subject: str
    issuer: str
    serial_number: str
    not_before: datetime
    not_after: datetime
    fingerprint_sha256: str
    fingerprint_sha1: str
    key_type: KeyType
    key_size: Optional[int]
    signature_algorithm: str
    version: int
    subject_alt_names: List[str] = field(default_factory=list)
    key_usage: List[str] = field(default_factory=list)
    extended_key_usage: List[str] = field(default_factory=list)
    basic_constraints: Optional[Dict[str, Any]] = None
    authority_key_identifier: Optional[str] = None
    subject_key_identifier: Optional[str] = None
    crl_distribution_points: List[str] = field(default_factory=list)
    ocsp_urls: List[str] = field(default_factory=list)
    
    def is_expired(self) -> bool:
        """Check if certificate is expired."""
        return datetime.now(timezone.utc) > self.not_after
    
    def is_valid_for_date(self, date: datetime) -> bool:
        """Check if certificate is valid for specific date."""
        return self.not_before <= date <= self.not_after
    
    def days_until_expiry(self) -> int:
        """Get days until certificate expires."""
        delta = self.not_after - datetime.now(timezone.utc)
        return max(0, delta.days)


class Certificate:
    """
    X.509 Certificate wrapper with validation and information extraction.
    """
    
    def __init__(
        self,
        certificate_data: Union[str, bytes, x509.Certificate],
        certificate_format: CertificateFormat = CertificateFormat.PEM,
        certificate_id: Optional[str] = None
    ):
        """Initialize certificate from data."""
        self.certificate_id = certificate_id
        self.format = certificate_format
        self._cert_obj: Optional[x509.Certificate] = None
        self._info: Optional[CertificateInfo] = None
        
        # Parse certificate
        try:
            if isinstance(certificate_data, x509.Certificate):
                self._cert_obj = certificate_data
            elif isinstance(certificate_data, str):
                if certificate_format == CertificateFormat.PEM:
                    self._cert_obj = x509.load_pem_x509_certificate(certificate_data.encode())
                else:
                    # Assume base64 encoded DER
                    der_data = base64.b64decode(certificate_data)
                    self._cert_obj = x509.load_der_x509_certificate(der_data)
            elif isinstance(certificate_data, bytes):
                if certificate_format == CertificateFormat.PEM:
                    self._cert_obj = x509.load_pem_x509_certificate(certificate_data)
                else:
                    self._cert_obj = x509.load_der_x509_certificate(certificate_data)
            else:
                raise CertificateError(f"Unsupported certificate data type: {type(certificate_data)}")
                
        except Exception as e:
            raise CertificateError(f"Failed to parse certificate: {e}", certificate_id=certificate_id)
        
        # Extract certificate information
        self._extract_info()
    
    @classmethod
    def from_file(cls, file_path: Union[str, Path], certificate_id: Optional[str] = None) -> 'Certificate':
        """Load certificate from file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise CertificateError(f"Certificate file not found: {file_path}")
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Determine format based on content
            if data.startswith(b'-----BEGIN CERTIFICATE-----'):
                cert_format = CertificateFormat.PEM
            else:
                cert_format = CertificateFormat.DER
            
            return cls(data, cert_format, certificate_id or str(file_path))
        except Exception as e:
            raise CertificateError(f"Failed to load certificate from file: {e}")
    
    def _extract_info(self):
        """Extract information from certificate."""
        try:
            cert = self._cert_obj
            
            # Basic information
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            serial_number = str(cert.serial_number)
            
            # Use UTC versions to avoid deprecation warnings
            try:
                not_before = cert.not_valid_before_utc
                not_after = cert.not_valid_after_utc
            except AttributeError:
                # Fallback for older cryptography versions
                not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
                not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
            
            # Fingerprints
            cert_der = cert.public_bytes(serialization.Encoding.DER)
            fingerprint_sha256 = hashlib.sha256(cert_der).hexdigest()
            fingerprint_sha1 = hashlib.sha1(cert_der).hexdigest()
            
            # Key information
            public_key = cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                key_type = KeyType.RSA
                key_size = public_key.key_size
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                key_type = KeyType.EC
                key_size = public_key.curve.key_size
            else:
                key_type = KeyType.UNKNOWN
                key_size = None
            
            # Signature algorithm
            signature_algorithm = cert.signature_algorithm_oid._name
            
            # Version
            version = cert.version.value
            
            # Extensions
            subject_alt_names = []
            key_usage = []
            extended_key_usage = []
            basic_constraints = None
            authority_key_identifier = None
            subject_key_identifier = None
            crl_distribution_points = []
            ocsp_urls = []
            
            try:
                # Subject Alternative Names
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                for name in san_ext.value:
                    if isinstance(name, x509.DNSName):
                        subject_alt_names.append(f"DNS:{name.value}")
                    elif isinstance(name, x509.IPAddress):
                        subject_alt_names.append(f"IP:{name.value}")
                    elif isinstance(name, x509.RFC822Name):
                        subject_alt_names.append(f"email:{name.value}")
            except x509.ExtensionNotFound:
                pass
            
            try:
                # Key Usage
                ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
                ku = ku_ext.value
                if ku.digital_signature:
                    key_usage.append("digital_signature")
                if ku.key_encipherment:
                    key_usage.append("key_encipherment")
                if ku.key_agreement:
                    key_usage.append("key_agreement")
                if ku.key_cert_sign:
                    key_usage.append("key_cert_sign")
                if ku.crl_sign:
                    key_usage.append("crl_sign")
            except x509.ExtensionNotFound:
                pass
            
            try:
                # Extended Key Usage
                eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
                for usage in eku_ext.value:
                    extended_key_usage.append(usage._name)
            except x509.ExtensionNotFound:
                pass
            
            try:
                # Basic Constraints
                bc_ext = cert.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS)
                basic_constraints = {
                    "ca": bc_ext.value.ca,
                    "path_length": bc_ext.value.path_length
                }
            except x509.ExtensionNotFound:
                pass
            
            try:
                # Authority Key Identifier
                aki_ext = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_KEY_IDENTIFIER)
                if aki_ext.value.key_identifier:
                    authority_key_identifier = aki_ext.value.key_identifier.hex()
            except x509.ExtensionNotFound:
                pass
            
            try:
                # Subject Key Identifier
                ski_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER)
                subject_key_identifier = ski_ext.value.digest.hex()
            except x509.ExtensionNotFound:
                pass
            
            try:
                # CRL Distribution Points
                cdp_ext = cert.extensions.get_extension_for_oid(ExtensionOID.CRL_DISTRIBUTION_POINTS)
                for dp in cdp_ext.value:
                    if dp.full_name:
                        for name in dp.full_name:
                            if isinstance(name, x509.UniformResourceIdentifier):
                                crl_distribution_points.append(name.value)
            except x509.ExtensionNotFound:
                pass
            
            try:
                # OCSP URLs
                aia_ext = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
                for access in aia_ext.value:
                    if access.access_method == x509.AuthorityInformationAccessOID.OCSP:
                        if isinstance(access.access_location, x509.UniformResourceIdentifier):
                            ocsp_urls.append(access.access_location.value)
            except x509.ExtensionNotFound:
                pass
            
            self._info = CertificateInfo(
                subject=subject,
                issuer=issuer,
                serial_number=serial_number,
                not_before=not_before,
                not_after=not_after,
                fingerprint_sha256=fingerprint_sha256,
                fingerprint_sha1=fingerprint_sha1,
                key_type=key_type,
                key_size=key_size,
                signature_algorithm=signature_algorithm,
                version=version,
                subject_alt_names=subject_alt_names,
                key_usage=key_usage,
                extended_key_usage=extended_key_usage,
                basic_constraints=basic_constraints,
                authority_key_identifier=authority_key_identifier,
                subject_key_identifier=subject_key_identifier,
                crl_distribution_points=crl_distribution_points,
                ocsp_urls=ocsp_urls
            )
            
        except Exception as e:
            raise CertificateError(f"Failed to extract certificate information: {e}")
    
    @property
    def info(self) -> CertificateInfo:
        """Get certificate information."""
        return self._info
    
    @property
    def x509_cert(self) -> x509.Certificate:
        """Get underlying x509.Certificate object."""
        return self._cert_obj
    
    def validate(self, trusted_certs: Optional[List['Certificate']] = None) -> List[str]:
        """
        Validate certificate.
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        try:
            # Check if expired
            if self.info.is_expired():
                errors.append("Certificate has expired")
            
            # Check if not yet valid
            if datetime.now(timezone.utc) < self.info.not_before:
                errors.append("Certificate is not yet valid")
            
            # Check key size
            if self.info.key_type == KeyType.RSA and self.info.key_size and self.info.key_size < 2048:
                errors.append(f"RSA key size {self.info.key_size} is too small (minimum 2048)")
            
            # Check signature algorithm
            weak_algorithms = ['md5', 'sha1']
            if any(weak in self.info.signature_algorithm.lower() for weak in weak_algorithms):
                errors.append(f"Weak signature algorithm: {self.info.signature_algorithm}")
            
            # Validate against trusted certificates if provided
            if trusted_certs:
                chain_errors = self._validate_chain(trusted_certs)
                errors.extend(chain_errors)
                
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors
    
    def _validate_chain(self, trusted_certs: List['Certificate']) -> List[str]:
        """Validate certificate chain."""
        errors = []
        
        try:
            # Find issuer certificate
            issuer_cert = None
            for trusted_cert in trusted_certs:
                if trusted_cert.info.subject == self.info.issuer:
                    issuer_cert = trusted_cert
                    break
            
            if not issuer_cert:
                errors.append(f"Issuer certificate not found: {self.info.issuer}")
                return errors
            
            # Verify signature
            try:
                issuer_cert.x509_cert.public_key().verify(
                    self.x509_cert.signature,
                    self.x509_cert.tbs_certificate_bytes,
                    self.x509_cert.signature_algorithm_oid._name
                )
            except Exception as e:
                errors.append(f"Signature verification failed: {e}")
            
            # Check issuer validity
            if issuer_cert.info.is_expired():
                errors.append("Issuer certificate has expired")
                
        except Exception as e:
            errors.append(f"Chain validation error: {e}")
        
        return errors
    
    def verify_hostname(self, hostname: str) -> bool:
        """Verify if certificate is valid for hostname."""
        try:
            # Check subject CN
            for attribute in self.x509_cert.subject:
                if attribute.oid == NameOID.COMMON_NAME:
                    if self._match_hostname(attribute.value, hostname):
                        return True
            
            # Check Subject Alternative Names
            for san in self.info.subject_alt_names:
                if san.startswith("DNS:"):
                    dns_name = san[4:]  # Remove "DNS:" prefix
                    if self._match_hostname(dns_name, hostname):
                        return True
                elif san.startswith("IP:"):
                    ip_str = san[3:]  # Remove "IP:" prefix
                    try:
                        if str(ipaddress.ip_address(hostname)) == ip_str:
                            return True
                    except ValueError:
                        pass
            
            return False
            
        except Exception:
            return False
    
    def _match_hostname(self, cert_hostname: str, hostname: str) -> bool:
        """Match hostname with certificate hostname (supports wildcards)."""
        cert_hostname = cert_hostname.lower()
        hostname = hostname.lower()
        
        if cert_hostname == hostname:
            return True
        
        # Wildcard matching
        if cert_hostname.startswith('*.'):
            cert_domain = cert_hostname[2:]
            if '.' in hostname:
                host_domain = hostname.split('.', 1)[1]
                return cert_domain == host_domain
        
        return False
    
    def to_pem(self) -> str:
        """Convert certificate to PEM format."""
        return self.x509_cert.public_bytes(serialization.Encoding.PEM).decode()
    
    def to_der(self) -> bytes:
        """Convert certificate to DER format."""
        return self.x509_cert.public_bytes(serialization.Encoding.DER)


class CertificateChain:
    """
    Certificate chain with validation and verification capabilities.
    """
    
    def __init__(self, certificates: List[Certificate]):
        """Initialize certificate chain."""
        if not certificates:
            raise CertificateError("Certificate chain cannot be empty")
        
        self.certificates = certificates
        self.leaf_certificate = certificates[0]  # First certificate is leaf
        self.intermediate_certificates = certificates[1:-1] if len(certificates) > 2 else []
        self.root_certificate = certificates[-1] if len(certificates) > 1 else None
    
    @classmethod
    def from_pem_bundle(cls, pem_bundle: str) -> 'CertificateChain':
        """Create certificate chain from PEM bundle."""
        certificates = []
        
        # Split PEM bundle into individual certificates
        cert_blocks = []
        current_block = []
        
        for line in pem_bundle.split('\n'):
            if line.strip() == '-----BEGIN CERTIFICATE-----':
                current_block = [line]
            elif line.strip() == '-----END CERTIFICATE-----':
                current_block.append(line)
                cert_blocks.append('\n'.join(current_block))
                current_block = []
            elif current_block:
                current_block.append(line)
        
        # Parse each certificate
        for i, cert_pem in enumerate(cert_blocks):
            try:
                cert = Certificate(cert_pem, CertificateFormat.PEM, f"chain-cert-{i}")
                certificates.append(cert)
            except Exception as e:
                raise CertificateError(f"Failed to parse certificate {i} in chain: {e}")
        
        return cls(certificates)
    
    def validate_chain(self, trusted_roots: Optional[List[Certificate]] = None) -> List[str]:
        """
        Validate the entire certificate chain.
        Returns list of validation errors (empty if valid).
        """
        errors = []
        
        try:
            # Validate each certificate individually
            for i, cert in enumerate(self.certificates):
                cert_errors = cert.validate()
                for error in cert_errors:
                    errors.append(f"Certificate {i}: {error}")
            
            # Validate chain structure
            for i in range(len(self.certificates) - 1):
                current_cert = self.certificates[i]
                next_cert = self.certificates[i + 1]
                
                # Check if next certificate is the issuer of current
                if current_cert.info.issuer != next_cert.info.subject:
                    errors.append(f"Chain break: Certificate {i} issuer does not match certificate {i+1} subject")
                
                # Verify signature
                try:
                    next_cert.x509_cert.public_key().verify(
                        current_cert.x509_cert.signature,
                        current_cert.x509_cert.tbs_certificate_bytes,
                        current_cert.x509_cert.signature_algorithm_oid._name
                    )
                except Exception as e:
                    errors.append(f"Signature verification failed for certificate {i}: {e}")
            
            # Validate against trusted roots if provided
            if trusted_roots and self.root_certificate:
                root_trusted = False
                for trusted_root in trusted_roots:
                    if (self.root_certificate.info.fingerprint_sha256 == 
                        trusted_root.info.fingerprint_sha256):
                        root_trusted = True
                        break
                
                if not root_trusted:
                    errors.append("Root certificate is not trusted")
            
        except Exception as e:
            errors.append(f"Chain validation error: {e}")
        
        return errors
    
    def get_certificate_by_subject(self, subject: str) -> Optional[Certificate]:
        """Get certificate by subject DN."""
        for cert in self.certificates:
            if cert.info.subject == subject:
                return cert
        return None
    
    def is_valid(self, trusted_roots: Optional[List[Certificate]] = None) -> bool:
        """Check if certificate chain is valid."""
        return len(self.validate_chain(trusted_roots)) == 0


class CertificateRevocationList:
    """Certificate Revocation List (CRL) handler."""
    
    def __init__(self, crl_data: Union[str, bytes]):
        """Initialize CRL from data."""
        try:
            if isinstance(crl_data, str):
                if crl_data.startswith('-----BEGIN X509 CRL-----'):
                    self._crl = x509.load_pem_x509_crl(crl_data.encode())
                else:
                    # Assume base64 encoded DER
                    der_data = base64.b64decode(crl_data)
                    self._crl = x509.load_der_x509_crl(der_data)
            else:
                if crl_data.startswith(b'-----BEGIN X509 CRL-----'):
                    self._crl = x509.load_pem_x509_crl(crl_data)
                else:
                    self._crl = x509.load_der_x509_crl(crl_data)
        except Exception as e:
            raise CertificateError(f"Failed to parse CRL: {e}")
    
    @classmethod
    def from_url(cls, url: str, timeout: int = 30) -> 'CertificateRevocationList':
        """Download and parse CRL from URL."""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                crl_data = response.read()
            return cls(crl_data)
        except Exception as e:
            raise CertificateError(f"Failed to download CRL from {url}: {e}")
    
    def is_revoked(self, certificate: Certificate) -> bool:
        """Check if certificate is revoked."""
        try:
            serial_number = certificate.x509_cert.serial_number
            revoked_cert = self._crl.get_revoked_certificate_by_serial_number(serial_number)
            return revoked_cert is not None
        except Exception:
            return False
    
    def get_revocation_date(self, certificate: Certificate) -> Optional[datetime]:
        """Get revocation date for certificate."""
        try:
            serial_number = certificate.x509_cert.serial_number
            revoked_cert = self._crl.get_revoked_certificate_by_serial_number(serial_number)
            if revoked_cert:
                return revoked_cert.revocation_date.replace(tzinfo=timezone.utc)
            return None
        except Exception:
            return None


class CertificateStore:
    """
    Certificate store for managing multiple certificates and chains.
    """
    
    def __init__(self):
        """Initialize empty certificate store."""
        self.certificates: Dict[str, Certificate] = {}
        self.chains: Dict[str, CertificateChain] = {}
        self.trusted_roots: List[Certificate] = []
        self.crls: Dict[str, CertificateRevocationList] = {}
        self._logger = get_security_logger()
    
    def add_certificate(self, certificate: Certificate, certificate_id: Optional[str] = None) -> str:
        """Add certificate to store."""
        cert_id = certificate_id or certificate.certificate_id or certificate.info.fingerprint_sha256
        self.certificates[cert_id] = certificate
        
        self._logger.log_certificate_event(
            certificate_id=cert_id,
            operation="add",
            certificate_subject=certificate.info.subject,
            certificate_issuer=certificate.info.issuer
        )
        
        return cert_id
    
    def add_chain(self, chain: CertificateChain, chain_id: str) -> str:
        """Add certificate chain to store."""
        self.chains[chain_id] = chain
        
        # Also add individual certificates
        for i, cert in enumerate(chain.certificates):
            cert_id = f"{chain_id}-{i}"
            self.add_certificate(cert, cert_id)
        
        return chain_id
    
    def add_trusted_root(self, certificate: Certificate):
        """Add trusted root certificate."""
        self.trusted_roots.append(certificate)
        self.add_certificate(certificate, f"trusted-root-{certificate.info.fingerprint_sha256}")
    
    def add_crl(self, crl: CertificateRevocationList, crl_id: str):
        """Add CRL to store."""
        self.crls[crl_id] = crl
    
    def get_certificate(self, certificate_id: str) -> Optional[Certificate]:
        """Get certificate by ID."""
        return self.certificates.get(certificate_id)
    
    def get_chain(self, chain_id: str) -> Optional[CertificateChain]:
        """Get certificate chain by ID."""
        return self.chains.get(chain_id)
    
    def find_certificate_by_subject(self, subject: str) -> Optional[Certificate]:
        """Find certificate by subject DN."""
        for cert in self.certificates.values():
            if cert.info.subject == subject:
                return cert
        return None
    
    def find_certificates_by_issuer(self, issuer: str) -> List[Certificate]:
        """Find certificates by issuer DN."""
        results = []
        for cert in self.certificates.values():
            if cert.info.issuer == issuer:
                results.append(cert)
        return results
    
    def validate_certificate(self, certificate_id: str) -> Tuple[bool, List[str]]:
        """Validate certificate in store."""
        cert = self.get_certificate(certificate_id)
        if not cert:
            return False, [f"Certificate not found: {certificate_id}"]
        
        errors = cert.validate(self.trusted_roots)
        
        # Check against CRLs
        for crl in self.crls.values():
            if crl.is_revoked(cert):
                errors.append("Certificate is revoked")
                break
        
        return len(errors) == 0, errors
    
    def validate_chain(self, chain_id: str) -> Tuple[bool, List[str]]:
        """Validate certificate chain in store."""
        chain = self.get_chain(chain_id)
        if not chain:
            return False, [f"Certificate chain not found: {chain_id}"]
        
        errors = chain.validate_chain(self.trusted_roots)
        
        # Check each certificate against CRLs
        for cert in chain.certificates:
            for crl in self.crls.values():
                if crl.is_revoked(cert):
                    errors.append(f"Certificate in chain is revoked: {cert.info.subject}")
                    break
        
        return len(errors) == 0, errors
    
    def get_expiring_certificates(self, days_threshold: int = 30) -> List[Tuple[str, Certificate]]:
        """Get certificates expiring within threshold."""
        expiring = []
        for cert_id, cert in self.certificates.items():
            if cert.info.days_until_expiry() <= days_threshold:
                expiring.append((cert_id, cert))
        return expiring
    
    def cleanup_expired_certificates(self) -> int:
        """Remove expired certificates from store."""
        expired_ids = []
        for cert_id, cert in self.certificates.items():
            if cert.info.is_expired():
                expired_ids.append(cert_id)
        
        for cert_id in expired_ids:
            del self.certificates[cert_id]
            self._logger.log_certificate_event(
                certificate_id=cert_id,
                operation="cleanup_expired"
            )
        
        return len(expired_ids)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get certificate store statistics."""
        total_certs = len(self.certificates)
        expired_certs = sum(1 for cert in self.certificates.values() if cert.info.is_expired())
        expiring_soon = len(self.get_expiring_certificates(30))
        
        key_types = {}
        for cert in self.certificates.values():
            key_type = cert.info.key_type.value
            key_types[key_type] = key_types.get(key_type, 0) + 1
        
        return {
            "total_certificates": total_certs,
            "expired_certificates": expired_certs,
            "expiring_within_30_days": expiring_soon,
            "certificate_chains": len(self.chains),
            "trusted_roots": len(self.trusted_roots),
            "crls": len(self.crls),
            "key_types": key_types
        }
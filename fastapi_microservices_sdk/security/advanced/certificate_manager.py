"""
Certificate Manager for FastAPI Microservices SDK.
This module provides comprehensive certificate lifecycle management including
loading, validation, rotation, and secure storage with encryption at rest.
"""
import os
import json
import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import hmac
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .certificates import Certificate, CertificateChain, CertificateStore
from .config import CertificateManagementConfig
from .exceptions import CertificateError, CertificateRotationError
from .logging import get_security_logger, CertificateEvent


class RotationStatus(Enum):
    """Certificate rotation status."""
    NOT_NEEDED = "not_needed"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageEncryption(Enum):
    """Storage encryption methods."""
    NONE = "none"
    FERNET = "fernet"
    AES_256 = "aes_256"


@dataclass
class RotationTask:
    """Certificate rotation task."""
    certificate_id: str
    current_cert: Certificate
    rotation_reason: str
    scheduled_time: datetime
    status: RotationStatus = RotationStatus.SCHEDULED
    attempts: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        """Initialize rotation task."""
        if self.scheduled_time.tzinfo is None:
            self.scheduled_time = self.scheduled_time.replace(tzinfo=timezone.utc)


@dataclass
class CertificateMetadata:
    """Certificate metadata for storage."""
    certificate_id: str
    file_path: str
    created_at: datetime
    last_accessed: datetime
    rotation_count: int = 0
    backup_paths: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    encrypted: bool = False
    checksum: Optional[str] = None


class SecureStorage:
    """Secure storage for certificates with encryption at rest."""
    
    def __init__(
        self,
        storage_path: str,
        encryption_method: StorageEncryption = StorageEncryption.FERNET,
        encryption_key: Optional[str] = None
    ):
        """Initialize secure storage."""
        self.storage_path = Path(storage_path)
        self.encryption_method = encryption_method
        self.metadata_file = self.storage_path / "metadata.json"
        self._metadata: Dict[str, CertificateMetadata] = {}
        self._fernet: Optional[Fernet] = None
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        if encryption_method != StorageEncryption.NONE:
            self._init_encryption(encryption_key)
        
        # Load existing metadata
        self._load_metadata()
    
    def _init_encryption(self, encryption_key: Optional[str]):
        """Initialize encryption system."""
        if self.encryption_method == StorageEncryption.FERNET:
            if encryption_key:
                # Derive key from password
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'certificate_storage_salt',
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            else:
                # Generate random key
                key = Fernet.generate_key()
                # Save key to secure location (in production, use proper key management)
                key_file = self.storage_path / ".encryption_key"
                with open(key_file, 'wb') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)  # Restrict permissions
            
            self._fernet = Fernet(key)
    
    def _load_metadata(self):
        """Load certificate metadata from storage."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                for cert_id, meta_dict in data.items():
                    # Convert datetime strings back to datetime objects
                    meta_dict['created_at'] = datetime.fromisoformat(meta_dict['created_at'])
                    meta_dict['last_accessed'] = datetime.fromisoformat(meta_dict['last_accessed'])
                    self._metadata[cert_id] = CertificateMetadata(**meta_dict)
            except Exception as e:
                raise CertificateError(f"Failed to load certificate metadata: {e}")
    
    def _save_metadata(self):
        """Save certificate metadata to storage."""
        try:
            # Convert metadata to serializable format
            data = {}
            for cert_id, metadata in self._metadata.items():
                meta_dict = {
                    'certificate_id': metadata.certificate_id,
                    'file_path': metadata.file_path,
                    'created_at': metadata.created_at.isoformat(),
                    'last_accessed': metadata.last_accessed.isoformat(),
                    'rotation_count': metadata.rotation_count,
                    'backup_paths': metadata.backup_paths,
                    'tags': metadata.tags,
                    'encrypted': metadata.encrypted,
                    'checksum': metadata.checksum
                }
                data[cert_id] = meta_dict
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise CertificateError(f"Failed to save certificate metadata: {e}")
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate checksum for data integrity."""
        return hashlib.sha256(data).hexdigest()
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data if encryption is enabled."""
        if self.encryption_method == StorageEncryption.NONE or not self._fernet:
            return data
        return self._fernet.encrypt(data)
    
    def _decrypt_data(self, data: bytes) -> bytes:
        """Decrypt data if encryption is enabled."""
        if self.encryption_method == StorageEncryption.NONE or not self._fernet:
            return data
        return self._fernet.decrypt(data)
    
    def store_certificate(
        self,
        certificate_id: str,
        certificate: Certificate,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Store certificate securely."""
        try:
            # Generate file path
            safe_id = "".join(c for c in certificate_id if c.isalnum() or c in "._-")
            file_path = self.storage_path / f"{safe_id}.pem"
            
            # Get certificate data
            cert_data = certificate.to_pem().encode()
            
            # Encrypt if needed
            encrypted_data = self._encrypt_data(cert_data)
            
            # Calculate checksum
            checksum = self._calculate_checksum(cert_data)
            
            # Write to file
            with open(file_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure permissions
            os.chmod(file_path, 0o600)
            
            # Create metadata
            now = datetime.now(timezone.utc)
            metadata = CertificateMetadata(
                certificate_id=certificate_id,
                file_path=str(file_path),
                created_at=now,
                last_accessed=now,
                tags=tags or {},
                encrypted=self.encryption_method != StorageEncryption.NONE,
                checksum=checksum
            )
            
            self._metadata[certificate_id] = metadata
            self._save_metadata()
            
            return str(file_path)
            
        except Exception as e:
            raise CertificateError(f"Failed to store certificate {certificate_id}: {e}")
    
    def load_certificate(self, certificate_id: str) -> Certificate:
        """Load certificate from secure storage."""
        if certificate_id not in self._metadata:
            raise CertificateError(f"Certificate not found: {certificate_id}")
        
        try:
            metadata = self._metadata[certificate_id]
            
            # Read encrypted data
            with open(metadata.file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt data
            cert_data = self._decrypt_data(encrypted_data)
            
            # Verify checksum
            if metadata.checksum:
                calculated_checksum = self._calculate_checksum(cert_data)
                if calculated_checksum != metadata.checksum:
                    raise CertificateError(f"Certificate integrity check failed for {certificate_id}")
            
            # Create certificate object
            certificate = Certificate(cert_data.decode(), certificate_id=certificate_id)
            
            # Update access time
            metadata.last_accessed = datetime.now(timezone.utc)
            self._save_metadata()
            
            return certificate
            
        except Exception as e:
            raise CertificateError(f"Failed to load certificate {certificate_id}: {e}")
    
    def delete_certificate(self, certificate_id: str) -> bool:
        """Delete certificate from storage."""
        if certificate_id not in self._metadata:
            return False
        
        try:
            metadata = self._metadata[certificate_id]
            
            # Delete certificate file
            if Path(metadata.file_path).exists():
                os.remove(metadata.file_path)
            
            # Delete backup files
            for backup_path in metadata.backup_paths:
                if Path(backup_path).exists():
                    os.remove(backup_path)
            
            # Remove from metadata
            del self._metadata[certificate_id]
            self._save_metadata()
            
            return True
            
        except Exception as e:
            raise CertificateError(f"Failed to delete certificate {certificate_id}: {e}")
    
    def backup_certificate(self, certificate_id: str) -> str:
        """Create backup of certificate."""
        if certificate_id not in self._metadata:
            raise CertificateError(f"Certificate not found: {certificate_id}")
        
        try:
            metadata = self._metadata[certificate_id]
            
            # Generate backup path
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"{certificate_id}_backup_{timestamp}.pem"
            backup_path = self.storage_path / "backups" / backup_name
            backup_path.parent.mkdir(exist_ok=True)
            
            # Copy certificate file
            with open(metadata.file_path, 'rb') as src:
                with open(backup_path, 'wb') as dst:
                    dst.write(src.read())
            
            # Set secure permissions
            os.chmod(backup_path, 0o600)
            
            # Update metadata
            metadata.backup_paths.append(str(backup_path))
            self._save_metadata()
            
            return str(backup_path)
            
        except Exception as e:
            raise CertificateError(f"Failed to backup certificate {certificate_id}: {e}")
    
    def list_certificates(self) -> List[str]:
        """List all stored certificate IDs."""
        return list(self._metadata.keys())
    
    def get_metadata(self, certificate_id: str) -> Optional[CertificateMetadata]:
        """Get certificate metadata."""
        return self._metadata.get(certificate_id)


class CertificateManager:
    """
    Comprehensive certificate lifecycle manager with automatic rotation,
    secure storage, and monitoring capabilities.
    """
    
    def __init__(
        self,
        config: CertificateManagementConfig,
        certificate_store: Optional[CertificateStore] = None
    ):
        """Initialize certificate manager."""
        self.config = config
        self.store = certificate_store or CertificateStore()
        self.logger = get_security_logger()
        
        # Initialize secure storage
        self.storage = SecureStorage(
            storage_path=config.storage_path,
            encryption_method=StorageEncryption.FERNET if config.auto_rotation_enabled else StorageEncryption.NONE
        )
        
        # Rotation management
        self._rotation_tasks: Dict[str, RotationTask] = {}
        self._rotation_thread: Optional[threading.Thread] = None
        self._stop_rotation = threading.Event()
        
        # Start rotation monitoring if enabled
        if config.auto_rotation_enabled:
            self._start_rotation_monitor()
    
    def _start_rotation_monitor(self):
        """Start the certificate rotation monitoring thread."""
        if self._rotation_thread and self._rotation_thread.is_alive():
            return
        
        self._stop_rotation.clear()
        self._rotation_thread = threading.Thread(
            target=self._rotation_monitor_loop,
            daemon=True
        )
        self._rotation_thread.start()
        
        self.logger.log_certificate_event(
            certificate_id="system",
            operation="rotation_monitor_start"
        )
    
    def _rotation_monitor_loop(self):
        """Main rotation monitoring loop."""
        while not self._stop_rotation.is_set():
            try:
                # Check for certificates needing rotation
                self._check_rotation_needed()
                
                # Process pending rotation tasks
                self._process_rotation_tasks()
                
                # Sleep for check interval
                self._stop_rotation.wait(self.config.rotation_check_interval)
                
            except Exception as e:
                self.logger.log_certificate_event(
                    certificate_id="system",
                    operation="rotation_monitor_error",
                    details={"error": str(e)}
                )
                # Continue monitoring despite errors
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _check_rotation_needed(self):
        """Check which certificates need rotation."""
        for cert_id in self.storage.list_certificates():
            try:
                certificate = self.storage.load_certificate(cert_id)
                
                # Check if rotation is needed
                days_until_expiry = certificate.info.days_until_expiry()
                
                if days_until_expiry <= self.config.rotation_threshold_days:
                    if cert_id not in self._rotation_tasks:
                        # Schedule rotation
                        self._schedule_rotation(
                            cert_id,
                            certificate,
                            f"Certificate expires in {days_until_expiry} days"
                        )
                        
            except Exception as e:
                self.logger.log_certificate_event(
                    certificate_id=cert_id,
                    operation="rotation_check_error",
                    details={"error": str(e)}
                )
    
    def _schedule_rotation(
        self,
        certificate_id: str,
        certificate: Certificate,
        reason: str,
        scheduled_time: Optional[datetime] = None,
        callback: Optional[Callable] = None
    ):
        """Schedule certificate rotation."""
        if scheduled_time is None:
            scheduled_time = datetime.now(timezone.utc)
        
        rotation_task = RotationTask(
            certificate_id=certificate_id,
            current_cert=certificate,
            rotation_reason=reason,
            scheduled_time=scheduled_time,
            callback=callback
        )
        
        self._rotation_tasks[certificate_id] = rotation_task
        
        self.logger.log_certificate_event(
            certificate_id=certificate_id,
            operation="rotation_scheduled",
            certificate_subject=certificate.info.subject,
            details={"reason": reason, "scheduled_time": scheduled_time.isoformat()}
        )
    
    def _process_rotation_tasks(self):
        """Process pending rotation tasks."""
        now = datetime.now(timezone.utc)
        
        for cert_id, task in list(self._rotation_tasks.items()):
            if task.status == RotationStatus.SCHEDULED and task.scheduled_time <= now:
                self._execute_rotation(task)
    
    def _execute_rotation(self, task: RotationTask):
        """Execute certificate rotation."""
        task.status = RotationStatus.IN_PROGRESS
        task.attempts += 1
        
        try:
            self.logger.log_certificate_event(
                certificate_id=task.certificate_id,
                operation="rotation_start",
                certificate_subject=task.current_cert.info.subject,
                details={"attempt": task.attempts, "reason": task.rotation_reason}
            )
            
            # Create backup before rotation
            if self.config.backup_old_certificates:
                backup_path = self.storage.backup_certificate(task.certificate_id)
                self.logger.log_certificate_event(
                    certificate_id=task.certificate_id,
                    operation="rotation_backup",
                    details={"backup_path": backup_path}
                )
            
            # Generate new certificate (placeholder - in real implementation, 
            # this would request from CA or generate self-signed)
            new_certificate = self._generate_new_certificate(task.current_cert)
            
            # Store new certificate
            self.storage.store_certificate(task.certificate_id, new_certificate)
            
            # Update certificate store
            self.store.add_certificate(new_certificate, task.certificate_id)
            
            # Update metadata
            metadata = self.storage.get_metadata(task.certificate_id)
            if metadata:
                metadata.rotation_count += 1
            
            task.status = RotationStatus.COMPLETED
            
            # Execute callback if provided
            if task.callback:
                try:
                    task.callback(task.certificate_id, new_certificate)
                except Exception as e:
                    self.logger.log_certificate_event(
                        certificate_id=task.certificate_id,
                        operation="rotation_callback_error",
                        details={"error": str(e)}
                    )
            
            self.logger.log_certificate_event(
                certificate_id=task.certificate_id,
                operation="rotation_complete",
                certificate_subject=new_certificate.info.subject,
                details={"new_expiry": new_certificate.info.not_after.isoformat()}
            )
            
            # Remove completed task
            del self._rotation_tasks[task.certificate_id]
            
        except Exception as e:
            task.status = RotationStatus.FAILED
            task.last_error = str(e)
            
            self.logger.log_certificate_event(
                certificate_id=task.certificate_id,
                operation="rotation_failed",
                details={"error": str(e), "attempt": task.attempts}
            )
            
            # Retry if attempts remaining
            if task.attempts < task.max_attempts:
                task.status = RotationStatus.SCHEDULED
                task.scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)
            else:
                # Max attempts reached, remove task
                del self._rotation_tasks[task.certificate_id]
                raise CertificateRotationError(
                    f"Certificate rotation failed after {task.attempts} attempts: {e}",
                    certificate_id=task.certificate_id,
                    rotation_stage="execution"
                )
    
    def _generate_new_certificate(self, old_certificate: Certificate) -> Certificate:
        """Generate new certificate (placeholder implementation)."""
        # In a real implementation, this would:
        # 1. Generate new key pair
        # 2. Create certificate request
        # 3. Submit to CA for signing
        # 4. Return new certificate
        
        # For now, return the same certificate (this is just for testing)
        # In production, this should never be used
        raise NotImplementedError(
            "Certificate generation not implemented. "
            "This should integrate with your Certificate Authority."
        )
    
    def load_certificate(self, certificate_id: str) -> Certificate:
        """Load certificate from storage."""
        try:
            certificate = self.storage.load_certificate(certificate_id)
            
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="load",
                certificate_subject=certificate.info.subject
            )
            
            return certificate
            
        except Exception as e:
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="load_failed",
                details={"error": str(e)}
            )
            raise
    
    def store_certificate(
        self,
        certificate_id: str,
        certificate: Certificate,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Store certificate securely."""
        try:
            # Store in secure storage
            file_path = self.storage.store_certificate(certificate_id, certificate, tags)
            
            # Add to certificate store
            self.store.add_certificate(certificate, certificate_id)
            
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="store",
                certificate_subject=certificate.info.subject,
                certificate_issuer=certificate.info.issuer,
                expiry_date=certificate.info.not_after
            )
            
            return file_path
            
        except Exception as e:
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="store_failed",
                details={"error": str(e)}
            )
            raise
    
    def validate_certificate(self, certificate_id: str) -> Tuple[bool, List[str]]:
        """Validate certificate."""
        try:
            certificate = self.storage.load_certificate(certificate_id)
            
            # Validate certificate
            errors = certificate.validate(self.store.trusted_roots)
            
            # Check against CRLs
            for crl in self.store.crls.values():
                if crl.is_revoked(certificate):
                    errors.append("Certificate is revoked")
                    break
            
            is_valid = len(errors) == 0
            
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="validate",
                certificate_subject=certificate.info.subject,
                details={"valid": is_valid, "errors": errors}
            )
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="validate_failed",
                details={"error": str(e)}
            )
            raise
    
    def rotate_certificate(
        self,
        certificate_id: str,
        reason: str = "Manual rotation",
        callback: Optional[Callable] = None
    ):
        """Manually trigger certificate rotation."""
        try:
            certificate = self.storage.load_certificate(certificate_id)
            
            # Schedule immediate rotation
            self._schedule_rotation(
                certificate_id,
                certificate,
                reason,
                datetime.now(timezone.utc),
                callback
            )
            
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="manual_rotation_scheduled",
                certificate_subject=certificate.info.subject,
                details={"reason": reason}
            )
            
        except Exception as e:
            self.logger.log_certificate_event(
                certificate_id=certificate_id,
                operation="manual_rotation_failed",
                details={"error": str(e)}
            )
            raise
    
    def get_certificate_status(self, certificate_id: str) -> Dict[str, Any]:
        """Get comprehensive certificate status."""
        try:
            certificate = self.storage.load_certificate(certificate_id)
            metadata = self.storage.get_metadata(certificate_id)
            
            # Check rotation status
            rotation_task = self._rotation_tasks.get(certificate_id)
            
            status = {
                "certificate_id": certificate_id,
                "subject": certificate.info.subject,
                "issuer": certificate.info.issuer,
                "serial_number": certificate.info.serial_number,
                "not_before": certificate.info.not_before.isoformat(),
                "not_after": certificate.info.not_after.isoformat(),
                "days_until_expiry": certificate.info.days_until_expiry(),
                "is_expired": certificate.info.is_expired(),
                "key_type": certificate.info.key_type.value,
                "key_size": certificate.info.key_size,
                "fingerprint_sha256": certificate.info.fingerprint_sha256,
                "rotation_count": metadata.rotation_count if metadata else 0,
                "last_accessed": metadata.last_accessed.isoformat() if metadata else None,
                "tags": metadata.tags if metadata else {},
                "rotation_status": rotation_task.status.value if rotation_task else "none",
                "rotation_scheduled": rotation_task.scheduled_time.isoformat() if rotation_task else None
            }
            
            return status
            
        except Exception as e:
            raise CertificateError(f"Failed to get certificate status: {e}")
    
    def list_certificates(self) -> List[Dict[str, Any]]:
        """List all managed certificates with status."""
        certificates = []
        
        for cert_id in self.storage.list_certificates():
            try:
                status = self.get_certificate_status(cert_id)
                certificates.append(status)
            except Exception as e:
                # Include error information for problematic certificates
                certificates.append({
                    "certificate_id": cert_id,
                    "error": str(e),
                    "status": "error"
                })
        
        return certificates
    
    def cleanup_expired_certificates(self) -> int:
        """Remove expired certificates from storage."""
        removed_count = 0
        
        for cert_id in self.storage.list_certificates():
            try:
                certificate = self.storage.load_certificate(cert_id)
                
                if certificate.info.is_expired():
                    # Create backup before deletion if configured
                    if self.config.backup_old_certificates:
                        self.storage.backup_certificate(cert_id)
                    
                    # Remove from storage
                    self.storage.delete_certificate(cert_id)
                    removed_count += 1
                    
                    self.logger.log_certificate_event(
                        certificate_id=cert_id,
                        operation="cleanup_expired",
                        certificate_subject=certificate.info.subject
                    )
                    
            except Exception as e:
                self.logger.log_certificate_event(
                    certificate_id=cert_id,
                    operation="cleanup_failed",
                    details={"error": str(e)}
                )
        
        return removed_count
    
    def shutdown(self):
        """Shutdown certificate manager."""
        if self._rotation_thread and self._rotation_thread.is_alive():
            self._stop_rotation.set()
            self._rotation_thread.join(timeout=5.0)
            
            self.logger.log_certificate_event(
                certificate_id="system",
                operation="rotation_monitor_stop"
            )
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
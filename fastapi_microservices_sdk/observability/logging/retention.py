"""
Log Retention and Cleanup System for FastAPI Microservices SDK.

This module provides automated log retention policies, cleanup mechanisms,
and archival capabilities for compliance and storage management.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import gzip
import logging
import os
import shutil
import threading
import time
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum

from .config import LoggingConfig, RetentionConfig, LogLevel, ComplianceStandard, RetentionPeriod
from .exceptions import LogRetentionError


class RetentionAction(str, Enum):
    """Retention action enumeration."""
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    MOVE = "move"


class RetentionStatus(str, Enum):
    """Retention status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RetentionRule:
    """Log retention rule definition."""
    
    name: str
    description: str
    
    # Matching criteria
    log_level: Optional[LogLevel] = None
    service_name: Optional[str] = None
    environment: Optional[str] = None
    event_type: Optional[str] = None
    compliance_standard: Optional[ComplianceStandard] = None
    
    # Retention settings
    retention_period: RetentionPeriod = RetentionPeriod.DAYS_30
    action: RetentionAction = RetentionAction.DELETE
    
    # Archive settings
    archive_path: Optional[str] = None
    compress_archives: bool = True
    encrypt_archives: bool = False
    
    # Advanced settings
    priority: int = 0  # Higher priority rules are processed first
    enabled: bool = True
    dry_run: bool = False
    
    def matches_log(self, log_data: Dict[str, Any]) -> bool:
        """Check if this rule matches a log entry."""
        if not self.enabled:
            return False
        
        # Check log level
        if self.log_level and log_data.get('level') != self.log_level.value:
            return False
        
        # Check service name
        if self.service_name and log_data.get('service_name') != self.service_name:
            return False
        
        # Check environment
        if self.environment and log_data.get('environment') != self.environment:
            return False
        
        # Check event type
        if self.event_type and log_data.get('event_type') != self.event_type:
            return False
        
        # Check compliance standard
        if self.compliance_standard:
            standards = log_data.get('compliance_standards', [])
            if self.compliance_standard.value not in standards:
                return False
        
        return True
    
    def get_retention_days(self) -> int:
        """Get retention period in days."""
        period_map = {
            RetentionPeriod.DAYS_7: 7,
            RetentionPeriod.DAYS_30: 30,
            RetentionPeriod.DAYS_90: 90,
            RetentionPeriod.DAYS_365: 365,
            RetentionPeriod.YEARS_7: 365 * 7,
            RetentionPeriod.FOREVER: -1  # Never delete
        }
        return period_map.get(self.retention_period, 30)


@dataclass
class RetentionJob:
    """Retention job execution record."""
    
    job_id: str
    rule_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: RetentionStatus = RetentionStatus.PENDING
    
    # Statistics
    files_processed: int = 0
    files_deleted: int = 0
    files_archived: int = 0
    files_compressed: int = 0
    files_failed: int = 0
    
    # Size statistics
    bytes_processed: int = 0
    bytes_freed: int = 0
    bytes_archived: int = 0
    
    # Error information
    error_message: Optional[str] = None
    error_details: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'job_id': self.job_id,
            'rule_name': self.rule_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.value,
            'duration_seconds': (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
            'files_processed': self.files_processed,
            'files_deleted': self.files_deleted,
            'files_archived': self.files_archived,
            'files_compressed': self.files_compressed,
            'files_failed': self.files_failed,
            'bytes_processed': self.bytes_processed,
            'bytes_freed': self.bytes_freed,
            'bytes_archived': self.bytes_archived,
            'error_message': self.error_message,
            'error_count': len(self.error_details)
        }


class BaseRetentionProcessor(ABC):
    """Base class for retention processors."""
    
    def __init__(self, config: RetentionConfig):
        self.config = config
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process_file(self, file_path: Path, rule: RetentionRule, job: RetentionJob) -> bool:
        """Process a single file according to retention rule."""
        pass
    
    def should_process_file(self, file_path: Path, rule: RetentionRule) -> bool:
        """Check if file should be processed based on age."""
        try:
            # Get file modification time
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            
            # Calculate age
            age_days = (datetime.now(timezone.utc) - mtime).days
            retention_days = rule.get_retention_days()
            
            # Never delete if retention is forever
            if retention_days == -1:
                return False
            
            return age_days > retention_days
            
        except Exception as e:
            self._logger.error(f"Error checking file age for {file_path}: {e}")
            return False


class DeleteProcessor(BaseRetentionProcessor):
    """Processor for deleting old log files."""
    
    async def process_file(self, file_path: Path, rule: RetentionRule, job: RetentionJob) -> bool:
        """Delete the specified file."""
        try:
            if rule.dry_run:
                self._logger.info(f"DRY RUN: Would delete {file_path}")
                return True
            
            # Get file size before deletion
            file_size = file_path.stat().st_size
            
            # Delete the file
            file_path.unlink()
            
            # Update job statistics
            job.files_deleted += 1
            job.bytes_freed += file_size
            
            self._logger.debug(f"Deleted log file: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete {file_path}: {e}"
            self._logger.error(error_msg)
            job.error_details.append(error_msg)
            job.files_failed += 1
            return False


class ArchiveProcessor(BaseRetentionProcessor):
    """Processor for archiving old log files."""
    
    async def process_file(self, file_path: Path, rule: RetentionRule, job: RetentionJob) -> bool:
        """Archive the specified file."""
        try:
            if not rule.archive_path:
                raise LogRetentionError(
                    message="Archive path not specified for archive rule",
                    retention_policy=rule.name
                )
            
            # Create archive directory
            archive_dir = Path(rule.archive_path)
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate archive file path
            archive_file = archive_dir / file_path.name
            
            if rule.dry_run:
                self._logger.info(f"DRY RUN: Would archive {file_path} to {archive_file}")
                return True
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Copy file to archive
            if rule.compress_archives:
                # Compress while archiving
                archive_file = archive_file.with_suffix(archive_file.suffix + '.gz')
                with open(file_path, 'rb') as f_in:
                    with gzip.open(archive_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                job.files_compressed += 1
            else:
                # Simple copy
                shutil.copy2(file_path, archive_file)
            
            # Delete original file
            file_path.unlink()
            
            # Update job statistics
            job.files_archived += 1
            job.bytes_processed += file_size
            job.bytes_archived += archive_file.stat().st_size
            job.bytes_freed += file_size - archive_file.stat().st_size
            
            self._logger.debug(f"Archived log file: {file_path} -> {archive_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to archive {file_path}: {e}"
            self._logger.error(error_msg)
            job.error_details.append(error_msg)
            job.files_failed += 1
            return False


class CompressProcessor(BaseRetentionProcessor):
    """Processor for compressing old log files in place."""
    
    async def process_file(self, file_path: Path, rule: RetentionRule, job: RetentionJob) -> bool:
        """Compress the specified file in place."""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            if rule.dry_run:
                self._logger.info(f"DRY RUN: Would compress {file_path} to {compressed_path}")
                return True
            
            # Get original file size
            original_size = file_path.stat().st_size
            
            # Compress file
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Delete original file
            file_path.unlink()
            
            # Get compressed file size
            compressed_size = compressed_path.stat().st_size
            
            # Update job statistics
            job.files_compressed += 1
            job.bytes_processed += original_size
            job.bytes_freed += original_size - compressed_size
            
            self._logger.debug(f"Compressed log file: {file_path} -> {compressed_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to compress {file_path}: {e}"
            self._logger.error(error_msg)
            job.error_details.append(error_msg)
            job.files_failed += 1
            return False


class MoveProcessor(BaseRetentionProcessor):
    """Processor for moving old log files to a different location."""
    
    async def process_file(self, file_path: Path, rule: RetentionRule, job: RetentionJob) -> bool:
        """Move the specified file to archive location."""
        try:
            if not rule.archive_path:
                raise LogRetentionError(
                    message="Archive path not specified for move rule",
                    retention_policy=rule.name
                )
            
            # Create destination directory
            dest_dir = Path(rule.archive_path)
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate destination file path
            dest_file = dest_dir / file_path.name
            
            if rule.dry_run:
                self._logger.info(f"DRY RUN: Would move {file_path} to {dest_file}")
                return True
            
            # Get file size
            file_size = file_path.stat().st_size
            
            # Move file
            shutil.move(str(file_path), str(dest_file))
            
            # Update job statistics
            job.files_archived += 1
            job.bytes_processed += file_size
            
            self._logger.debug(f"Moved log file: {file_path} -> {dest_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to move {file_path}: {e}"
            self._logger.error(error_msg)
            job.error_details.append(error_msg)
            job.files_failed += 1
            return False


class RetentionManager:
    """Log retention manager with automated cleanup."""
    
    def __init__(self, config: RetentionConfig):
        self.config = config
        self._logger = logging.getLogger(__name__)
        
        # Retention rules
        self._rules: List[RetentionRule] = []
        
        # Processors
        self._processors = {
            RetentionAction.DELETE: DeleteProcessor(config),
            RetentionAction.ARCHIVE: ArchiveProcessor(config),
            RetentionAction.COMPRESS: CompressProcessor(config),
            RetentionAction.MOVE: MoveProcessor(config)
        }
        
        # Job tracking
        self._jobs: Dict[str, RetentionJob] = {}
        self._job_history: List[RetentionJob] = []
        
        # Scheduler
        self._scheduler_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Callbacks
        self._job_callbacks: List[Callable[[RetentionJob], None]] = []
        
        # Start scheduler if automatic cleanup is enabled
        if config.enable_automatic_cleanup:
            self.start_scheduler()
    
    def add_rule(self, rule: RetentionRule):
        """Add a retention rule."""
        self._rules.append(rule)
        # Sort rules by priority (higher priority first)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self._logger.info(f"Added retention rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a retention rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                del self._rules[i]
                self._logger.info(f"Removed retention rule: {rule_name}")
                return True
        return False
    
    def get_rules(self) -> List[RetentionRule]:
        """Get all retention rules."""
        return self._rules.copy()
    
    def add_job_callback(self, callback: Callable[[RetentionJob], None]):
        """Add callback for job completion."""
        self._job_callbacks.append(callback)
    
    async def execute_retention_policy(
        self,
        log_directories: List[str],
        file_patterns: Optional[List[str]] = None
    ) -> List[RetentionJob]:
        """Execute retention policy on specified directories."""
        
        if not self._rules:
            self._logger.warning("No retention rules defined")
            return []
        
        jobs = []
        file_patterns = file_patterns or ['*.log', '*.log.*']
        
        for rule in self._rules:
            if not rule.enabled:
                continue
            
            job = RetentionJob(
                job_id=f"{rule.name}_{int(time.time())}",
                rule_name=rule.name,
                start_time=datetime.now(timezone.utc),
                status=RetentionStatus.IN_PROGRESS
            )
            
            self._jobs[job.job_id] = job
            jobs.append(job)
            
            try:
                await self._execute_rule(rule, job, log_directories, file_patterns)
                job.status = RetentionStatus.COMPLETED
                
            except Exception as e:
                job.status = RetentionStatus.FAILED
                job.error_message = str(e)
                self._logger.error(f"Retention job {job.job_id} failed: {e}")
            
            finally:
                job.end_time = datetime.now(timezone.utc)
                self._job_history.append(job)
                
                # Notify callbacks
                for callback in self._job_callbacks:
                    try:
                        callback(job)
                    except Exception as e:
                        self._logger.error(f"Error in job callback: {e}")
        
        return jobs
    
    async def _execute_rule(
        self,
        rule: RetentionRule,
        job: RetentionJob,
        log_directories: List[str],
        file_patterns: List[str]
    ):
        """Execute a single retention rule."""
        
        processor = self._processors.get(rule.action)
        if not processor:
            raise LogRetentionError(
                message=f"Unknown retention action: {rule.action}",
                retention_policy=rule.name
            )
        
        # Find files to process
        files_to_process = []
        
        for directory in log_directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            
            for pattern in file_patterns:
                for file_path in dir_path.glob(pattern):
                    if file_path.is_file() and processor.should_process_file(file_path, rule):
                        files_to_process.append(file_path)
        
        self._logger.info(
            f"Processing {len(files_to_process)} files for rule {rule.name}"
        )
        
        # Process files in batches
        batch_size = self.config.cleanup_batch_size
        
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            
            # Process batch
            tasks = []
            for file_path in batch:
                task = processor.process_file(file_path, rule, job)
                tasks.append(task)
            
            # Wait for batch completion
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update job statistics
            job.files_processed += len(batch)
            
            # Log batch completion
            successful = sum(1 for r in results if r is True)
            self._logger.debug(
                f"Processed batch: {successful}/{len(batch)} files successful"
            )
    
    def start_scheduler(self):
        """Start the automatic cleanup scheduler."""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        
        def scheduler_worker():
            while not self._shutdown_event.is_set():
                try:
                    # Wait for cleanup interval
                    if self._shutdown_event.wait(self.config.cleanup_interval):
                        break
                    
                    # Execute retention policy
                    asyncio.run(self.execute_retention_policy(['.']))
                    
                except Exception as e:
                    self._logger.error(f"Error in retention scheduler: {e}")
        
        self._scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
        self._scheduler_thread.start()
        self._logger.info("Retention scheduler started")
    
    def stop_scheduler(self):
        """Stop the automatic cleanup scheduler."""
        self._shutdown_event.set()
        
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)
        
        self._logger.info("Retention scheduler stopped")
    
    def get_job_status(self, job_id: str) -> Optional[RetentionJob]:
        """Get status of a specific job."""
        return self._jobs.get(job_id)
    
    def get_job_history(self, limit: int = 100) -> List[RetentionJob]:
        """Get job history."""
        return self._job_history[-limit:]
    
    def get_retention_metrics(self) -> Dict[str, Any]:
        """Get retention system metrics."""
        total_jobs = len(self._job_history)
        successful_jobs = sum(1 for job in self._job_history if job.status == RetentionStatus.COMPLETED)
        
        total_files_processed = sum(job.files_processed for job in self._job_history)
        total_files_deleted = sum(job.files_deleted for job in self._job_history)
        total_files_archived = sum(job.files_archived for job in self._job_history)
        total_bytes_freed = sum(job.bytes_freed for job in self._job_history)
        
        return {
            'total_jobs': total_jobs,
            'successful_jobs': successful_jobs,
            'success_rate': successful_jobs / max(1, total_jobs),
            'active_rules': len([r for r in self._rules if r.enabled]),
            'total_rules': len(self._rules),
            'total_files_processed': total_files_processed,
            'total_files_deleted': total_files_deleted,
            'total_files_archived': total_files_archived,
            'total_bytes_freed': total_bytes_freed,
            'scheduler_running': self._scheduler_thread and self._scheduler_thread.is_alive(),
            'automatic_cleanup_enabled': self.config.enable_automatic_cleanup
        }


# Factory functions
def create_default_retention_rules(config: RetentionConfig) -> List[RetentionRule]:
    """Create default retention rules based on configuration."""
    rules = []
    
    # Create rules based on log levels
    for level, period in config.retention_periods.items():
        rule = RetentionRule(
            name=f"level_{level.value.lower()}",
            description=f"Retention rule for {level.value} level logs",
            log_level=level,
            retention_period=period,
            action=RetentionAction.DELETE if period != RetentionPeriod.FOREVER else RetentionAction.ARCHIVE,
            priority=10 if level in [LogLevel.CRITICAL, LogLevel.ERROR] else 5
        )
        rules.append(rule)
    
    # Create rules based on compliance standards
    for standard, period in config.compliance_retention.items():
        rule = RetentionRule(
            name=f"compliance_{standard.value}",
            description=f"Retention rule for {standard.value} compliance",
            compliance_standard=standard,
            retention_period=period,
            action=RetentionAction.ARCHIVE,
            priority=20  # High priority for compliance
        )
        rules.append(rule)
    
    return rules


# Export main classes and functions
__all__ = [
    'RetentionAction',
    'RetentionStatus',
    'RetentionRule',
    'RetentionJob',
    'BaseRetentionProcessor',
    'DeleteProcessor',
    'ArchiveProcessor',
    'CompressProcessor',
    'MoveProcessor',
    'RetentionManager',
    'create_default_retention_rules',
]
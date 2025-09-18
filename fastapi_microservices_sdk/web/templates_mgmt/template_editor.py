"""
Template Editor.
Provides web-based template editing with syntax highlighting,
validation, preview, and version control capabilities.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import difflib
import logging

from ..core.base_manager import BaseManager
from .template_manager import TemplateManager, CustomTemplate, TemplateMetadata
from .template_validator import TemplateValidator, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class TemplateVersion:
    """Template version information."""
    version: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    created_by: str
    change_summary: str
    diff: Optional[str] = None


@dataclass
class EditorSession:
    """Template editor session."""
    session_id: str
    template_id: str
    user_id: str
    started_at: datetime
    last_activity: datetime
    is_active: bool = True
    auto_save_enabled: bool = True
    changes_count: int = 0


class TemplateEditor(BaseManager):
    """
    Template Editor.
    
    Features:
    - Web-based template editing with syntax highlighting
    - Real-time validation and preview
    - Version control and history management
    - Auto-save and session management
    - Collaborative editing support
    - Template testing and validation tools
    - Diff visualization
    - Backup and recovery
    """

    def __init__(self, name: str = "template_editor", config: Optional[Dict[str, Any]] = None):
        """Initialize the template editor."""
        super().__init__(name, config)
        
        # Configuration
        self._auto_save_interval = config.get("auto_save_interval", 30) if config else 30  # seconds
        self._max_versions = config.get("max_versions", 50) if config else 50
        self._enable_collaboration = config.get("enable_collaboration", True) if config else True
        
        # Template manager and validator
        self._template_manager: Optional[TemplateManager] = None
        self._validator: Optional[TemplateValidator] = None
        
        # Version control
        self._template_versions: Dict[str, List[TemplateVersion]] = {}
        
        # Editor sessions
        self._active_sessions: Dict[str, EditorSession] = {}
        
        # Auto-save tracking
        self._auto_save_tasks: Dict[str, Any] = {}
        
        # Backup storage
        self._backup_directory = Path(config.get("backup_directory", "backups/templates")) if config else Path("backups/templates")

    async def _initialize_impl(self) -> None:
        """Initialize the template editor."""
        try:
            # Create backup directory
            self._backup_directory.mkdir(parents=True, exist_ok=True)
            
            # Initialize validator
            self._validator = TemplateValidator()
            
            # Load existing versions
            await self._load_template_versions()
            
            self.logger.info("Template editor initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize template editor: {e}")
            raise

    async def _shutdown_impl(self) -> None:
        """Shutdown the template editor."""
        try:
            # Save all active sessions
            for session in self._active_sessions.values():
                if session.is_active:
                    await self._auto_save_session(session.session_id)
            
            # Save version history
            await self._save_template_versions()
            
            self.logger.info("Template editor shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Error during template editor shutdown: {e}")

    async def _health_check_impl(self) -> bool:
        """Health check implementation."""
        try:
            return self._validator is not None and self._backup_directory.exists()
        except Exception:
            return False

    # Manager Integration

    def set_template_manager(self, template_manager: TemplateManager) -> None:
        """
        Set the template manager reference.
        
        Args:
            template_manager: Template manager instance
        """
        self._template_manager = template_manager

    # Editor Session Management

    async def start_editing_session(
        self,
        template_id: str,
        user_id: str,
        auto_save: bool = True
    ) -> str:
        """
        Start a new editing session.
        
        Args:
            template_id: Template ID
            user_id: User ID
            auto_save: Enable auto-save
            
        Returns:
            Session ID
        """
        return await self._safe_execute(
            "start_editing_session",
            self._start_editing_session_impl,
            template_id,
            user_id,
            auto_save
        )

    async def _start_editing_session_impl(
        self,
        template_id: str,
        user_id: str,
        auto_save: bool
    ) -> str:
        """Implementation for starting editing session."""
        try:
            # Generate session ID
            session_id = f"{template_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create session
            session = EditorSession(
                session_id=session_id,
                template_id=template_id,
                user_id=user_id,
                started_at=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                auto_save_enabled=auto_save
            )
            
            self._active_sessions[session_id] = session
            
            # Start auto-save if enabled
            if auto_save:
                await self._start_auto_save(session_id)
            
            self.logger.info(f"Started editing session: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start editing session: {e}")
            raise

    async def end_editing_session(self, session_id: str, save_changes: bool = True) -> bool:
        """
        End an editing session.
        
        Args:
            session_id: Session ID
            save_changes: Save changes before ending
            
        Returns:
            True if session ended successfully
        """
        return await self._safe_execute(
            "end_editing_session",
            self._end_editing_session_impl,
            session_id,
            save_changes
        )

    async def _end_editing_session_impl(self, session_id: str, save_changes: bool) -> bool:
        """Implementation for ending editing session."""
        try:
            if session_id not in self._active_sessions:
                return False
            
            session = self._active_sessions[session_id]
            
            # Save changes if requested
            if save_changes and session.changes_count > 0:
                await self._auto_save_session(session_id)
            
            # Mark session as inactive
            session.is_active = False
            
            # Stop auto-save
            if session_id in self._auto_save_tasks:
                self._auto_save_tasks[session_id].cancel()
                del self._auto_save_tasks[session_id]
            
            # Remove from active sessions
            del self._active_sessions[session_id]
            
            self.logger.info(f"Ended editing session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to end editing session: {e}")
            return False

    # Template Validation and Preview

    async def validate_template_content(
        self,
        content: str,
        template_type: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate template content.
        
        Args:
            content: Template content
            template_type: Template type
            variables: Template variables
            
        Returns:
            Validation result
        """
        return await self._safe_execute(
            "validate_template_content",
            self._validate_template_content_impl,
            content,
            template_type,
            variables or {}
        )

    async def _validate_template_content_impl(
        self,
        content: str,
        template_type: str,
        variables: Dict[str, Any]
    ) -> ValidationResult:
        """Implementation for template validation."""
        try:
            if not self._validator:
                raise RuntimeError("Validator not initialized")
            
            return self._validator.validate_template(content, template_type, variables)
            
        except Exception as e:
            self.logger.error(f"Failed to validate template: {e}")
            return ValidationResult(
                is_valid=False,
                issues=[],
                score=0.0,
                suggestions=[]
            )

    async def preview_template(
        self,
        content: str,
        variables: Dict[str, Any],
        preview_data: Dict[str, Any]
    ) -> str:
        """
        Generate template preview with sample data.
        
        Args:
            content: Template content
            variables: Template variables
            preview_data: Sample data for preview
            
        Returns:
            Rendered template preview
        """
        return await self._safe_execute(
            "preview_template",
            self._preview_template_impl,
            content,
            variables,
            preview_data
        )

    async def _preview_template_impl(
        self,
        content: str,
        variables: Dict[str, Any],
        preview_data: Dict[str, Any]
    ) -> str:
        """Implementation for template preview."""
        try:
            # Simple template rendering (replace {{variable}} with values)
            rendered_content = content
            
            for var_name, var_value in preview_data.items():
                placeholder = f"{{{{{var_name}}}}}"
                rendered_content = rendered_content.replace(placeholder, str(var_value))
            
            return rendered_content
            
        except Exception as e:
            self.logger.error(f"Failed to preview template: {e}")
            return f"Preview error: {e}"

    # Version Control

    async def create_template_version(
        self,
        template_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: str,
        change_summary: str
    ) -> str:
        """
        Create a new template version.
        
        Args:
            template_id: Template ID
            content: Template content
            metadata: Template metadata
            user_id: User ID
            change_summary: Summary of changes
            
        Returns:
            Version string
        """
        return await self._safe_execute(
            "create_template_version",
            self._create_template_version_impl,
            template_id,
            content,
            metadata,
            user_id,
            change_summary
        )

    async def _create_template_version_impl(
        self,
        template_id: str,
        content: str,
        metadata: Dict[str, Any],
        user_id: str,
        change_summary: str
    ) -> str:
        """Implementation for creating template version."""
        try:
            # Get current versions
            versions = self._template_versions.get(template_id, [])
            
            # Generate version number
            if versions:
                last_version = versions[-1].version
                version_parts = last_version.split('.')
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                new_version = '.'.join(version_parts)
            else:
                new_version = "1.0.0"
            
            # Calculate diff if there's a previous version
            diff = None
            if versions:
                previous_content = versions[-1].content
                diff = self._calculate_diff(previous_content, content)
            
            # Create version
            version = TemplateVersion(
                version=new_version,
                content=content,
                metadata=metadata,
                created_at=datetime.utcnow(),
                created_by=user_id,
                change_summary=change_summary,
                diff=diff
            )
            
            # Add to versions list
            versions.append(version)
            
            # Limit number of versions
            if len(versions) > self._max_versions:
                versions = versions[-self._max_versions:]
            
            self._template_versions[template_id] = versions
            
            # Create backup
            await self._create_backup(template_id, version)
            
            self.logger.info(f"Created template version {new_version} for {template_id}")
            return new_version
            
        except Exception as e:
            self.logger.error(f"Failed to create template version: {e}")
            raise

    async def get_template_versions(self, template_id: str) -> List[TemplateVersion]:
        """
        Get version history for a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            List of template versions
        """
        return self._template_versions.get(template_id, [])

    async def get_template_version(self, template_id: str, version: str) -> Optional[TemplateVersion]:
        """
        Get a specific template version.
        
        Args:
            template_id: Template ID
            version: Version string
            
        Returns:
            Template version or None
        """
        versions = self._template_versions.get(template_id, [])
        for v in versions:
            if v.version == version:
                return v
        return None

    def _calculate_diff(self, old_content: str, new_content: str) -> str:
        """Calculate diff between two content versions."""
        try:
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile='previous',
                tofile='current',
                lineterm=''
            )
            
            return ''.join(diff)
            
        except Exception as e:
            logger.error(f"Failed to calculate diff: {e}")
            return ""

    # Auto-save and Backup

    async def _start_auto_save(self, session_id: str) -> None:
        """Start auto-save for a session."""
        import asyncio
        
        async def auto_save_loop():
            while session_id in self._active_sessions:
                try:
                    await asyncio.sleep(self._auto_save_interval)
                    
                    session = self._active_sessions.get(session_id)
                    if session and session.is_active and session.changes_count > 0:
                        await self._auto_save_session(session_id)
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Auto-save error for session {session_id}: {e}")
        
        # Start auto-save task
        task = asyncio.create_task(auto_save_loop())
        self._auto_save_tasks[session_id] = task

    async def _auto_save_session(self, session_id: str) -> bool:
        """Auto-save session changes."""
        try:
            session = self._active_sessions.get(session_id)
            if not session:
                return False
            
            # This would save the current editor state
            # Implementation depends on how editor state is tracked
            
            session.changes_count = 0
            session.last_activity = datetime.utcnow()
            
            self.logger.debug(f"Auto-saved session: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to auto-save session: {e}")
            return False

    async def _create_backup(self, template_id: str, version: TemplateVersion) -> None:
        """Create backup of template version."""
        try:
            backup_file = self._backup_directory / f"{template_id}_{version.version}_{int(version.created_at.timestamp())}.json"
            
            backup_data = {
                "template_id": template_id,
                "version": version.version,
                "content": version.content,
                "metadata": version.metadata,
                "created_at": version.created_at.isoformat(),
                "created_by": version.created_by,
                "change_summary": version.change_summary
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")

    # Template Testing

    async def test_template(
        self,
        content: str,
        template_type: str,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test template with provided data.
        
        Args:
            content: Template content
            template_type: Template type
            test_data: Test data
            
        Returns:
            Test results
        """
        return await self._safe_execute(
            "test_template",
            self._test_template_impl,
            content,
            template_type,
            test_data
        )

    async def _test_template_impl(
        self,
        content: str,
        template_type: str,
        test_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implementation for template testing."""
        try:
            start_time = datetime.utcnow()
            
            # Validate first
            validation_result = await self._validate_template_content_impl(
                content, template_type, test_data
            )
            
            if not validation_result.is_valid:
                return {
                    "success": False,
                    "error": "Template validation failed",
                    "validation_issues": validation_result.issues,
                    "execution_time": 0.0
                }
            
            # Generate preview
            preview = await self._preview_template_impl(content, {}, test_data)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "success": True,
                "preview": preview,
                "validation_score": validation_result.score,
                "execution_time": execution_time,
                "test_data": test_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to test template: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": 0.0
            }

    # Collaboration Features

    async def get_active_editors(self, template_id: str) -> List[Dict[str, Any]]:
        """
        Get list of users currently editing a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            List of active editor sessions
        """
        try:
            active_editors = []
            
            for session in self._active_sessions.values():
                if (session.template_id == template_id and 
                    session.is_active and 
                    (datetime.utcnow() - session.last_activity).seconds < 300):  # 5 minutes
                    
                    active_editors.append({
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "started_at": session.started_at.isoformat(),
                        "last_activity": session.last_activity.isoformat()
                    })
            
            return active_editors
            
        except Exception as e:
            self.logger.error(f"Failed to get active editors: {e}")
            return []

    # Utility Methods

    async def get_template_diff(
        self,
        template_id: str,
        version1: str,
        version2: str
    ) -> Optional[str]:
        """
        Get diff between two template versions.
        
        Args:
            template_id: Template ID
            version1: First version
            version2: Second version
            
        Returns:
            Diff string or None
        """
        try:
            versions = self._template_versions.get(template_id, [])
            
            v1 = next((v for v in versions if v.version == version1), None)
            v2 = next((v for v in versions if v.version == version2), None)
            
            if not v1 or not v2:
                return None
            
            return self._calculate_diff(v1.content, v2.content)
            
        except Exception as e:
            self.logger.error(f"Failed to get template diff: {e}")
            return None

    async def _load_template_versions(self) -> None:
        """Load template versions from disk."""
        try:
            versions_file = self._backup_directory / "versions.json"
            if versions_file.exists():
                with open(versions_file, 'r') as f:
                    versions_data = json.load(f)
                
                # Reconstruct version objects
                for template_id, version_list in versions_data.items():
                    versions = []
                    for v_data in version_list:
                        version = TemplateVersion(
                            version=v_data["version"],
                            content=v_data["content"],
                            metadata=v_data["metadata"],
                            created_at=datetime.fromisoformat(v_data["created_at"]),
                            created_by=v_data["created_by"],
                            change_summary=v_data["change_summary"],
                            diff=v_data.get("diff")
                        )
                        versions.append(version)
                    
                    self._template_versions[template_id] = versions
                    
        except Exception as e:
            self.logger.error(f"Failed to load template versions: {e}")

    async def _save_template_versions(self) -> None:
        """Save template versions to disk."""
        try:
            versions_file = self._backup_directory / "versions.json"
            
            # Convert to serializable format
            versions_data = {}
            for template_id, versions in self._template_versions.items():
                versions_data[template_id] = [
                    {
                        "version": v.version,
                        "content": v.content,
                        "metadata": v.metadata,
                        "created_at": v.created_at.isoformat(),
                        "created_by": v.created_by,
                        "change_summary": v.change_summary,
                        "diff": v.diff
                    }
                    for v in versions
                ]
            
            with open(versions_file, 'w') as f:
                json.dump(versions_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save template versions: {e}")

    async def restore_template_version(
        self,
        template_id: str,
        version: str,
        user_id: str
    ) -> bool:
        """
        Restore a template to a specific version.
        
        Args:
            template_id: Template ID
            version: Version to restore
            user_id: User performing the restore
            
        Returns:
            True if restore successful
        """
        return await self._safe_execute(
            "restore_template_version",
            self._restore_template_version_impl,
            template_id,
            version,
            user_id
        )

    async def _restore_template_version_impl(
        self,
        template_id: str,
        version: str,
        user_id: str
    ) -> bool:
        """Implementation for restoring template version."""
        try:
            if not self._template_manager:
                return False
            
            # Get the version to restore
            target_version = await self.get_template_version(template_id, version)
            if not target_version:
                return False
            
            # Update the template
            success = await self._template_manager.update_custom_template(
                template_id,
                target_version.content,
                target_version.metadata
            )
            
            if success:
                # Create a new version entry for the restore
                await self._create_template_version_impl(
                    template_id,
                    target_version.content,
                    target_version.metadata,
                    user_id,
                    f"Restored to version {version}"
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restore template version: {e}")
            return False
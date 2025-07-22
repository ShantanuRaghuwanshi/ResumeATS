"""
Version Manager Service

Manages multiple resume versions with comparison capabilities, version control,
and restore functionality. Provides comprehensive version management for resumes.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import difflib
from uuid import uuid4

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.resume_version import (
    ResumeVersion,
    VersionComparison,
    VersionHistory,
    VersionTemplate,
    VersionBackup,
    VersionAnalytics,
)
from models.resume import ResumeDocument, ResumeSections
from database import get_database
from configs.config import get_logger

logger = get_logger(__name__)


class VersionManager:
    """Manages resume versions with comprehensive version control capabilities"""

    def __init__(self):
        self.db = get_database()
        self.max_versions_per_user = 50  # Configurable limit
        self.auto_backup_enabled = True
        self.backup_retention_days = 30

    async def create_version(
        self,
        user_id: str,
        resume_data: Dict[str, Any],
        name: str,
        description: Optional[str] = None,
        job_target: Optional[str] = None,
        optimization_type: Optional[str] = None,
        tags: List[str] = None,
    ) -> ResumeVersion:
        """Create a new resume version"""

        try:
            # Check version limit
            existing_versions = await self.list_versions(user_id)
            if len(existing_versions) >= self.max_versions_per_user:
                await self._cleanup_old_versions(user_id)

            # Calculate version number
            version_number = len(existing_versions) + 1

            # Calculate quality scores
            scores = await self._calculate_quality_scores(resume_data)

            # Create version
            version = ResumeVersion(
                user_id=user_id,
                name=name,
                description=description,
                resume_data=resume_data,
                version_number=version_number,
                job_target=job_target,
                optimization_type=optimization_type,
                overall_score=scores.get("overall_score"),
                ats_score=scores.get("ats_score"),
                keyword_score=scores.get("keyword_score"),
                tags=tags or [],
            )

            # Store version
            self.db.create("resume_versions", version.id, version.model_dump())

            # Create automatic backup if enabled
            if self.auto_backup_enabled:
                await self._create_backup(version.id, "auto_save")

            # Initialize analytics
            await self._initialize_analytics(user_id, version.id)

            logger.info(f"Created resume version {version.id} for user {user_id}")
            return version

        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            raise

    async def get_version(
        self, version_id: str, user_id: str
    ) -> Optional[ResumeVersion]:
        """Get a specific version by ID"""

        try:
            version_data = self.db.read("resume_versions", version_id)
            if not version_data:
                return None

            version = ResumeVersion(**version_data)

            # Verify user ownership
            if version.user_id != user_id:
                logger.warning(
                    f"User {user_id} attempted to access version {version_id} owned by {version.user_id}"
                )
                return None

            # Update analytics
            await self._update_analytics(user_id, version_id, "view")

            return version

        except Exception as e:
            logger.error(f"Failed to get version {version_id}: {e}")
            raise

    async def list_versions(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        tags: List[str] = None,
        category: Optional[str] = None,
    ) -> List[ResumeVersion]:
        """List all versions for a user with filtering and sorting"""

        try:
            # Get all versions for user
            versions_data = self.db.find("resume_versions", user_id=user_id)
            versions = [ResumeVersion(**data) for data in versions_data]

            # Apply filters
            if tags:
                versions = [v for v in versions if any(tag in v.tags for tag in tags)]

            if category:
                versions = [v for v in versions if v.category == category]

            # Sort versions
            reverse = sort_order.lower() == "desc"
            if sort_by == "created_at":
                versions.sort(key=lambda v: v.created_at, reverse=reverse)
            elif sort_by == "name":
                versions.sort(key=lambda v: v.name.lower(), reverse=reverse)
            elif sort_by == "overall_score":
                versions.sort(key=lambda v: v.overall_score or 0, reverse=reverse)
            elif sort_by == "version_number":
                versions.sort(key=lambda v: v.version_number, reverse=reverse)

            # Apply pagination
            if limit:
                versions = versions[offset : offset + limit]

            return versions

        except Exception as e:
            logger.error(f"Failed to list versions for user {user_id}: {e}")
            raise

    async def update_version(
        self,
        version_id: str,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Optional[ResumeVersion]:
        """Update version metadata (not resume data)"""

        try:
            version = await self.get_version(version_id, user_id)
            if not version:
                return None

            # Create backup before major changes
            if "resume_data" in updates:
                await self._create_backup(version_id, "pre_major_change")

            # Update allowed fields
            allowed_fields = {
                "name",
                "description",
                "job_target",
                "optimization_type",
                "tags",
                "category",
                "is_current",
                "is_template",
            }

            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(version, field, value)

            version.last_modified = datetime.utcnow()

            # Save updated version
            self.db.update("resume_versions", version_id, version.model_dump())

            # Update analytics
            await self._update_analytics(user_id, version_id, "edit")

            logger.info(f"Updated version {version_id}")
            return version

        except Exception as e:
            logger.error(f"Failed to update version {version_id}: {e}")
            raise

    async def delete_version(self, version_id: str, user_id: str) -> bool:
        """Delete a version"""

        try:
            version = await self.get_version(version_id, user_id)
            if not version:
                return False

            # Create final backup before deletion
            await self._create_backup(version_id, "pre_deletion")

            # Delete version
            success = self.db.delete("resume_versions", version_id)

            if success:
                # Clean up related data
                await self._cleanup_version_data(version_id)
                logger.info(f"Deleted version {version_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
            raise

    async def compare_versions(
        self,
        version1_id: str,
        version2_id: str,
        user_id: str,
    ) -> Optional[VersionComparison]:
        """Compare two versions and return detailed differences"""

        try:
            # Get both versions
            version1 = await self.get_version(version1_id, user_id)
            version2 = await self.get_version(version2_id, user_id)

            if not version1 or not version2:
                return None

            # Calculate overall similarity
            similarity = await self._calculate_similarity(
                version1.resume_data, version2.resume_data
            )

            # Calculate section differences
            section_differences = await self._calculate_section_differences(
                version1.resume_data, version2.resume_data
            )

            # Analyze changes
            changes = await self._analyze_changes(
                version1.resume_data, version2.resume_data
            )

            # Calculate quality difference
            quality_diff = None
            if version1.overall_score and version2.overall_score:
                quality_diff = version2.overall_score - version1.overall_score

            # Generate recommendations
            recommendations = await self._generate_comparison_recommendations(
                version1, version2, changes
            )

            # Create comparison
            comparison = VersionComparison(
                version1_id=version1_id,
                version2_id=version2_id,
                version1=version1,
                version2=version2,
                overall_similarity=similarity,
                quality_difference=quality_diff,
                section_differences=section_differences,
                additions=changes["additions"],
                deletions=changes["deletions"],
                modifications=changes["modifications"],
                content_changes=changes["content_changes"],
                formatting_changes=changes["formatting_changes"],
                structural_changes=changes["structural_changes"],
                improvements=recommendations["improvements"],
                regressions=recommendations["regressions"],
                neutral_changes=recommendations["neutral_changes"],
                merge_suggestions=recommendations["merge_suggestions"],
                rollback_recommendations=recommendations["rollback_recommendations"],
            )

            # Store comparison for future reference
            self.db.create(
                "version_comparisons", comparison.id, comparison.model_dump()
            )

            logger.info(f"Compared versions {version1_id} and {version2_id}")
            return comparison

        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            raise

    async def restore_version(
        self,
        version_id: str,
        user_id: str,
        create_backup: bool = True,
    ) -> Optional[ResumeVersion]:
        """Restore a version as the current active version"""

        try:
            version = await self.get_version(version_id, user_id)
            if not version:
                return None

            # Create backup of current state if requested
            if create_backup:
                current_versions = await self.list_versions(user_id, limit=1)
                if current_versions:
                    await self._create_backup(current_versions[0].id, "pre_restore")

            # Create new version from restored data
            restored_version = await self.create_version(
                user_id=user_id,
                resume_data=version.resume_data,
                name=f"{version.name} (Restored)",
                description=f"Restored from version created on {version.created_at.strftime('%Y-%m-%d %H:%M')}",
                job_target=version.job_target,
                optimization_type=version.optimization_type,
                tags=version.tags + ["restored"],
            )

            # Mark as current
            restored_version.is_current = True
            await self.update_version(
                restored_version.id, user_id, {"is_current": True}
            )

            # Update analytics
            await self._update_analytics(user_id, version_id, "restore")

            logger.info(f"Restored version {version_id} as {restored_version.id}")
            return restored_version

        except Exception as e:
            logger.error(f"Failed to restore version {version_id}: {e}")
            raise

    async def get_version_history(
        self, version_id: str, user_id: str
    ) -> Optional[VersionHistory]:
        """Get detailed history for a version"""

        try:
            version = await self.get_version(version_id, user_id)
            if not version:
                return None

            # Get all backups for this version
            backups = self.db.find("version_backups", version_id=version_id)

            # Calculate statistics
            changes = []
            for backup in backups:
                changes.append(
                    {
                        "timestamp": backup.get("created_at"),
                        "reason": backup.get("backup_reason"),
                        "type": "backup",
                    }
                )

            # Get modification timeline from analytics
            analytics = self.db.find("version_analytics", version_id=version_id)
            if analytics:
                for analytic in analytics:
                    # Add edit events to timeline
                    pass

            history = VersionHistory(
                version_id=version_id,
                changes=changes,
                total_changes=len(changes),
                major_revisions=len(
                    [c for c in changes if "major" in c.get("reason", "")]
                ),
                minor_revisions=len(
                    [c for c in changes if "minor" in c.get("reason", "")]
                ),
                first_created=version.created_at,
                last_modified=version.last_modified,
                modification_timeline=changes,
            )

            return history

        except Exception as e:
            logger.error(f"Failed to get version history: {e}")
            raise

    async def create_template(
        self,
        version_id: str,
        user_id: str,
        template_name: str,
        template_description: str,
        industry: Optional[str] = None,
        experience_level: Optional[str] = None,
        is_public: bool = False,
    ) -> Optional[VersionTemplate]:
        """Create a template from a successful version"""

        try:
            version = await self.get_version(version_id, user_id)
            if not version:
                return None

            # Anonymize resume data for template
            anonymized_data = await self._anonymize_resume_data(version.resume_data)

            template = VersionTemplate(
                name=template_name,
                description=template_description,
                template_structure=anonymized_data,
                industry=industry,
                experience_level=experience_level,
                is_public=is_public,
                created_by=user_id,
            )

            # Store template
            self.db.create("version_templates", template.id, template.model_dump())

            logger.info(f"Created template {template.id} from version {version_id}")
            return template

        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise

    async def get_analytics(
        self, user_id: str, version_id: str
    ) -> Optional[VersionAnalytics]:
        """Get analytics for a specific version"""

        try:
            analytics_data = self.db.find(
                "version_analytics", user_id=user_id, version_id=version_id
            )
            if not analytics_data:
                return None

            return VersionAnalytics(**analytics_data[0])

        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            raise

    # Private helper methods

    async def _calculate_quality_scores(
        self, resume_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate quality scores for resume data"""

        # Placeholder implementation - in production, this would use actual scoring algorithms
        scores = {
            "overall_score": 0.75,  # Mock score
            "ats_score": 0.80,  # Mock ATS compatibility score
            "keyword_score": 0.70,  # Mock keyword optimization score
        }

        # Basic scoring based on content completeness
        sections = resume_data.get("sections", {})

        # Check for essential sections
        essential_sections = [
            "personal_details",
            "work_experience",
            "education",
            "skills",
        ]
        present_sections = sum(
            1 for section in essential_sections if sections.get(section)
        )
        completeness_score = present_sections / len(essential_sections)

        scores["overall_score"] = min(completeness_score + 0.2, 1.0)

        return scores

    async def _cleanup_old_versions(self, user_id: str):
        """Clean up old versions when limit is reached"""

        try:
            versions = await self.list_versions(
                user_id, sort_by="created_at", sort_order="asc"
            )

            # Keep the most recent versions and delete oldest
            versions_to_delete = versions[
                : -self.max_versions_per_user + 10
            ]  # Keep 10 buffer

            for version in versions_to_delete:
                if not version.is_current and not version.is_template:
                    await self.delete_version(version.id, user_id)

        except Exception as e:
            logger.error(f"Failed to cleanup old versions: {e}")

    async def _create_backup(self, version_id: str, reason: str) -> VersionBackup:
        """Create a backup of a version"""

        try:
            version_data = self.db.read("resume_versions", version_id)
            if not version_data:
                raise ValueError(f"Version not found: {version_id}")

            backup = VersionBackup(
                version_id=version_id,
                backup_data=version_data,
                backup_reason=reason,
                expires_at=datetime.utcnow()
                + timedelta(days=self.backup_retention_days),
            )

            self.db.create("version_backups", backup.id, backup.model_dump())
            return backup

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    async def _initialize_analytics(self, user_id: str, version_id: str):
        """Initialize analytics for a new version"""

        try:
            analytics = VersionAnalytics(
                user_id=user_id,
                version_id=version_id,
            )

            self.db.create(
                "version_analytics", f"{user_id}_{version_id}", analytics.model_dump()
            )

        except Exception as e:
            logger.error(f"Failed to initialize analytics: {e}")

    async def _update_analytics(self, user_id: str, version_id: str, action: str):
        """Update analytics for version actions"""

        try:
            analytics_data = self.db.find(
                "version_analytics", user_id=user_id, version_id=version_id
            )
            if not analytics_data:
                await self._initialize_analytics(user_id, version_id)
                analytics_data = self.db.find(
                    "version_analytics", user_id=user_id, version_id=version_id
                )

            if analytics_data:
                analytics = VersionAnalytics(**analytics_data[0])

                # Update counters based on action
                if action == "view":
                    analytics.view_count += 1
                elif action == "edit":
                    analytics.edit_count += 1
                elif action == "download":
                    analytics.download_count += 1
                elif action == "share":
                    analytics.share_count += 1

                analytics.last_updated = datetime.utcnow()

                self.db.update(
                    "version_analytics",
                    f"{user_id}_{version_id}",
                    analytics.model_dump(),
                )

        except Exception as e:
            logger.error(f"Failed to update analytics: {e}")

    async def _cleanup_version_data(self, version_id: str):
        """Clean up all data related to a deleted version"""

        try:
            # Delete backups
            backups = self.db.find("version_backups", version_id=version_id)
            for backup in backups:
                self.db.delete("version_backups", backup["id"])

            # Delete analytics
            analytics = self.db.find("version_analytics", version_id=version_id)
            for analytic in analytics:
                self.db.delete("version_analytics", analytic["id"])

            # Delete comparisons
            comparisons = self.db.find("version_comparisons", version1_id=version_id)
            comparisons.extend(
                self.db.find("version_comparisons", version2_id=version_id)
            )
            for comparison in comparisons:
                self.db.delete("version_comparisons", comparison["id"])

        except Exception as e:
            logger.error(f"Failed to cleanup version data: {e}")

    async def _calculate_similarity(
        self, data1: Dict[str, Any], data2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two resume data structures"""

        try:
            # Convert to JSON strings for comparison
            str1 = json.dumps(data1, sort_keys=True)
            str2 = json.dumps(data2, sort_keys=True)

            # Use difflib to calculate similarity
            similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
            return round(similarity, 3)

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    async def _calculate_section_differences(
        self, data1: Dict[str, Any], data2: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate differences between sections"""

        differences = {}

        try:
            sections1 = data1.get("sections", {})
            sections2 = data2.get("sections", {})

            all_sections = set(sections1.keys()) | set(sections2.keys())

            for section in all_sections:
                section_data1 = sections1.get(section, {})
                section_data2 = sections2.get(section, {})

                if section_data1 != section_data2:
                    differences[section] = {
                        "changed": True,
                        "similarity": await self._calculate_similarity(
                            section_data1, section_data2
                        ),
                        "added_in_v2": section in sections2
                        and section not in sections1,
                        "removed_in_v2": section in sections1
                        and section not in sections2,
                    }
                else:
                    differences[section] = {
                        "changed": False,
                        "similarity": 1.0,
                    }

        except Exception as e:
            logger.error(f"Failed to calculate section differences: {e}")

        return differences

    async def _analyze_changes(
        self, data1: Dict[str, Any], data2: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Analyze detailed changes between versions"""

        changes = {
            "additions": [],
            "deletions": [],
            "modifications": [],
            "content_changes": {},
            "formatting_changes": [],
            "structural_changes": [],
        }

        try:
            # Compare sections
            sections1 = data1.get("sections", {})
            sections2 = data2.get("sections", {})

            # Find additions and deletions
            for section in sections2:
                if section not in sections1:
                    changes["additions"].append(f"Added section: {section}")

            for section in sections1:
                if section not in sections2:
                    changes["deletions"].append(f"Removed section: {section}")

            # Find modifications
            for section in sections1:
                if section in sections2 and sections1[section] != sections2[section]:
                    changes["modifications"].append(f"Modified section: {section}")
                    changes["content_changes"][section] = {
                        "before": sections1[section],
                        "after": sections2[section],
                    }

        except Exception as e:
            logger.error(f"Failed to analyze changes: {e}")

        return changes

    async def _generate_comparison_recommendations(
        self, version1: ResumeVersion, version2: ResumeVersion, changes: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate recommendations based on version comparison"""

        recommendations = {
            "improvements": [],
            "regressions": [],
            "neutral_changes": [],
            "merge_suggestions": [],
            "rollback_recommendations": [],
        }

        try:
            # Analyze quality scores
            if version1.overall_score and version2.overall_score:
                if version2.overall_score > version1.overall_score:
                    recommendations["improvements"].append(
                        f"Overall quality improved by {(version2.overall_score - version1.overall_score):.2%}"
                    )
                elif version2.overall_score < version1.overall_score:
                    recommendations["regressions"].append(
                        f"Overall quality decreased by {(version1.overall_score - version2.overall_score):.2%}"
                    )

            # Analyze changes
            if changes["additions"]:
                recommendations["improvements"].extend(
                    [
                        f"Consider keeping: {addition}"
                        for addition in changes["additions"]
                    ]
                )

            if changes["deletions"]:
                recommendations["rollback_recommendations"].extend(
                    [
                        f"Consider restoring: {deletion}"
                        for deletion in changes["deletions"]
                    ]
                )

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")

        return recommendations

    async def _anonymize_resume_data(
        self, resume_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Anonymize resume data for template creation"""

        try:
            anonymized = json.loads(json.dumps(resume_data))  # Deep copy

            # Anonymize personal details
            if (
                "sections" in anonymized
                and "personal_details" in anonymized["sections"]
            ):
                personal = anonymized["sections"]["personal_details"]
                personal["name"] = "[Your Name]"
                personal["email"] = "[your.email@example.com]"
                personal["phone"] = "[Your Phone Number]"
                personal["address"] = "[Your Address]"

            # Anonymize work experience
            if "sections" in anonymized and "work_experience" in anonymized["sections"]:
                for exp in anonymized["sections"]["work_experience"]:
                    exp["company"] = "[Company Name]"
                    if "location" in exp:
                        exp["location"] = "[City, State]"

            return anonymized

        except Exception as e:
            logger.error(f"Failed to anonymize resume data: {e}")
            return resume_data

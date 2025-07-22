"""
Unit tests for VersionManager service.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from services.version_manager import VersionManager
from models.resume_version import (
    ResumeVersion,
    VersionComparison,
    VersionHistory,
    VersionTemplate,
    VersionBackup,
    VersionAnalytics,
)
from conftest import create_mock_version_manager


class TestVersionManager:
    """Test cases for VersionManager service."""

    @pytest.fixture
    def version_manager(self, mock_database):
        """Create VersionManager instance for testing."""
        return create_mock_version_manager(mock_database)

    @pytest.mark.asyncio
    async def test_create_version_success(self, version_manager, sample_resume_data):
        """Test successful version creation."""
        # Mock internal methods
        version_manager.list_versions = AsyncMock(
            return_value=[]
        )  # No existing versions
        version_manager._calculate_quality_scores = AsyncMock(
            return_value={
                "overall_score": 0.75,
                "ats_score": 0.80,
                "keyword_score": 0.70,
            }
        )
        version_manager._create_backup = AsyncMock()
        version_manager._initialize_analytics = AsyncMock()

        # Create version
        version = await version_manager.create_version(
            user_id="test-user-456",
            resume_data=sample_resume_data,
            name="Software Engineer Resume",
            description="Initial version for software engineering roles",
            job_target="Software Engineer",
            tags=["tech", "entry-level"],
        )

        # Assertions
        assert version is not None
        assert isinstance(version, ResumeVersion)
        assert version.user_id == "test-user-456"
        assert version.name == "Software Engineer Resume"
        assert version.description == "Initial version for software engineering roles"
        assert version.job_target == "Software Engineer"
        assert version.version_number == 1
        assert version.overall_score == 0.75
        assert version.ats_score == 0.80
        assert version.keyword_score == 0.70
        assert "tech" in version.tags
        assert "entry-level" in version.tags

        # Verify version was stored
        stored_version = version_manager.db.read("resume_versions", version.id)
        assert stored_version is not None

    @pytest.mark.asyncio
    async def test_create_version_with_limit_cleanup(
        self, version_manager, sample_resume_data
    ):
        """Test version creation when limit is reached."""
        # Mock existing versions at limit
        existing_versions = [
            Mock() for _ in range(version_manager.max_versions_per_user)
        ]
        version_manager.list_versions = AsyncMock(return_value=existing_versions)
        version_manager._cleanup_old_versions = AsyncMock()
        version_manager._calculate_quality_scores = AsyncMock(
            return_value={
                "overall_score": 0.75,
                "ats_score": 0.80,
                "keyword_score": 0.70,
            }
        )
        version_manager._create_backup = AsyncMock()
        version_manager._initialize_analytics = AsyncMock()

        # Create version
        version = await version_manager.create_version(
            user_id="test-user-456", resume_data=sample_resume_data, name="Test Version"
        )

        # Assertions
        assert version is not None
        version_manager._cleanup_old_versions.assert_called_once_with("test-user-456")

    @pytest.mark.asyncio
    async def test_get_version_success(self, version_manager, sample_resume_version):
        """Test successful version retrieval."""
        # Store version in database
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )
        version_manager._update_analytics = AsyncMock()

        # Get version
        result = await version_manager.get_version(
            sample_resume_version.id, sample_resume_version.user_id
        )

        # Assertions
        assert result is not None
        assert result.id == sample_resume_version.id
        assert result.user_id == sample_resume_version.user_id
        version_manager._update_analytics.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, version_manager):
        """Test version retrieval when version doesn't exist."""
        result = await version_manager.get_version("nonexistent-id", "test-user-456")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_version_wrong_user(self, version_manager, sample_resume_version):
        """Test version retrieval with wrong user ID."""
        # Store version in database
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )

        # Try to get with different user ID
        result = await version_manager.get_version(
            sample_resume_version.id, "different-user-123"
        )

        # Assertions
        assert result is None

    @pytest.mark.asyncio
    async def test_list_versions_success(self, version_manager):
        """Test successful version listing."""
        # Mock database response
        mock_versions_data = [
            {
                "id": "version-1",
                "user_id": "test-user-456",
                "name": "Version 1",
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "version_number": 1,
                "resume_data": {},
                "tags": [],
                "is_current": False,
                "is_template": False,
                "category": None,
            },
            {
                "id": "version-2",
                "user_id": "test-user-456",
                "name": "Version 2",
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "version_number": 2,
                "resume_data": {},
                "tags": ["tech"],
                "is_current": True,
                "is_template": False,
                "category": None,
            },
        ]
        version_manager.db.find = Mock(return_value=mock_versions_data)

        # List versions
        versions = await version_manager.list_versions("test-user-456")

        # Assertions
        assert len(versions) == 2
        assert versions[0].name == "Version 2"  # Should be sorted by created_at desc
        assert versions[1].name == "Version 1"

    @pytest.mark.asyncio
    async def test_list_versions_with_filters(self, version_manager):
        """Test version listing with filters."""
        # Mock database response
        mock_versions_data = [
            {
                "id": "version-1",
                "user_id": "test-user-456",
                "name": "Tech Resume",
                "created_at": datetime.utcnow().isoformat(),
                "last_modified": datetime.utcnow().isoformat(),
                "version_number": 1,
                "resume_data": {},
                "tags": ["tech", "senior"],
                "is_current": False,
                "is_template": False,
                "category": "engineering",
            }
        ]
        version_manager.db.find = Mock(return_value=mock_versions_data)

        # List versions with tag filter
        versions = await version_manager.list_versions("test-user-456", tags=["tech"])

        # Assertions
        assert len(versions) == 1
        assert "tech" in versions[0].tags

    @pytest.mark.asyncio
    async def test_update_version_success(self, version_manager, sample_resume_version):
        """Test successful version update."""
        # Store version in database
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )
        version_manager._create_backup = AsyncMock()
        version_manager._update_analytics = AsyncMock()

        # Update version
        updates = {
            "name": "Updated Resume Name",
            "description": "Updated description",
            "tags": ["updated", "tech"],
        }

        result = await version_manager.update_version(
            sample_resume_version.id, sample_resume_version.user_id, updates
        )

        # Assertions
        assert result is not None
        assert result.name == "Updated Resume Name"
        assert result.description == "Updated description"
        assert "updated" in result.tags
        assert "tech" in result.tags

    @pytest.mark.asyncio
    async def test_update_version_with_resume_data(
        self, version_manager, sample_resume_version
    ):
        """Test version update with resume data changes."""
        # Store version in database
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )
        version_manager._create_backup = AsyncMock()
        version_manager._update_analytics = AsyncMock()

        # Update with resume data (should trigger backup)
        updates = {"resume_data": {"new": "data"}}

        result = await version_manager.update_version(
            sample_resume_version.id, sample_resume_version.user_id, updates
        )

        # Assertions
        assert result is not None
        version_manager._create_backup.assert_called_once_with(
            sample_resume_version.id, "pre_major_change"
        )

    @pytest.mark.asyncio
    async def test_delete_version_success(self, version_manager, sample_resume_version):
        """Test successful version deletion."""
        # Store version in database
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )
        version_manager._create_backup = AsyncMock()
        version_manager._cleanup_version_data = AsyncMock()

        # Delete version
        result = await version_manager.delete_version(
            sample_resume_version.id, sample_resume_version.user_id
        )

        # Assertions
        assert result is True
        version_manager._create_backup.assert_called_once_with(
            sample_resume_version.id, "pre_deletion"
        )
        version_manager._cleanup_version_data.assert_called_once_with(
            sample_resume_version.id
        )

        # Verify version was deleted from database
        stored_version = version_manager.db.read(
            "resume_versions", sample_resume_version.id
        )
        assert stored_version is None

    @pytest.mark.asyncio
    async def test_compare_versions_success(self, version_manager, sample_resume_data):
        """Test successful version comparison."""
        # Create two versions
        version1_data = sample_resume_data.copy()
        version2_data = sample_resume_data.copy()
        version2_data["sections"]["personal_details"]["summary"] = "Updated summary"

        version1 = ResumeVersion(
            user_id="test-user-456",
            name="Version 1",
            resume_data=version1_data,
            version_number=1,
            overall_score=0.7,
        )
        version2 = ResumeVersion(
            user_id="test-user-456",
            name="Version 2",
            resume_data=version2_data,
            version_number=2,
            overall_score=0.8,
        )

        # Store versions
        version_manager.db.create("resume_versions", version1.id, version1.model_dump())
        version_manager.db.create("resume_versions", version2.id, version2.model_dump())

        # Mock internal methods
        version_manager._calculate_similarity = AsyncMock(return_value=0.85)
        version_manager._calculate_section_differences = AsyncMock(
            return_value={"personal_details": {"changed": True, "similarity": 0.9}}
        )
        version_manager._analyze_changes = AsyncMock(
            return_value={
                "additions": [],
                "deletions": [],
                "modifications": ["Modified personal_details"],
                "content_changes": {},
                "formatting_changes": [],
                "structural_changes": [],
            }
        )
        version_manager._generate_comparison_recommendations = AsyncMock(
            return_value={
                "improvements": ["Summary was enhanced"],
                "regressions": [],
                "neutral_changes": [],
                "merge_suggestions": [],
                "rollback_recommendations": [],
            }
        )

        # Compare versions
        result = await version_manager.compare_versions(
            version1.id, version2.id, "test-user-456"
        )

        # Assertions
        assert result is not None
        assert isinstance(result, VersionComparison)
        assert result.version1_id == version1.id
        assert result.version2_id == version2.id
        assert result.overall_similarity == 0.85
        assert result.quality_difference == 0.1  # 0.8 - 0.7
        assert "Modified personal_details" in result.modifications

    @pytest.mark.asyncio
    async def test_restore_version_success(
        self, version_manager, sample_resume_version
    ):
        """Test successful version restoration."""
        # Store original version
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )

        # Mock methods
        version_manager.list_versions = AsyncMock(return_value=[sample_resume_version])
        version_manager._create_backup = AsyncMock()
        version_manager.create_version = AsyncMock(
            return_value=ResumeVersion(
                user_id=sample_resume_version.user_id,
                name=f"{sample_resume_version.name} (Restored)",
                resume_data=sample_resume_version.resume_data,
                version_number=2,
                is_current=True,
            )
        )
        version_manager.update_version = AsyncMock()
        version_manager._update_analytics = AsyncMock()

        # Restore version
        result = await version_manager.restore_version(
            sample_resume_version.id, sample_resume_version.user_id
        )

        # Assertions
        assert result is not None
        assert "(Restored)" in result.name
        assert result.is_current is True
        version_manager._create_backup.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_version_history(self, version_manager, sample_resume_version):
        """Test getting version history."""
        # Store version
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )

        # Mock backup data
        mock_backups = [
            {
                "id": "backup-1",
                "version_id": sample_resume_version.id,
                "created_at": datetime.utcnow().isoformat(),
                "backup_reason": "auto_save",
            },
            {
                "id": "backup-2",
                "version_id": sample_resume_version.id,
                "created_at": datetime.utcnow().isoformat(),
                "backup_reason": "pre_major_change",
            },
        ]
        version_manager.db.find = Mock(return_value=mock_backups)

        # Get history
        history = await version_manager.get_version_history(
            sample_resume_version.id, sample_resume_version.user_id
        )

        # Assertions
        assert history is not None
        assert isinstance(history, VersionHistory)
        assert history.version_id == sample_resume_version.id
        assert history.total_changes == 2
        assert len(history.changes) == 2

    @pytest.mark.asyncio
    async def test_create_template_success(
        self, version_manager, sample_resume_version
    ):
        """Test successful template creation."""
        # Store version
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )

        # Mock anonymization
        version_manager._anonymize_resume_data = AsyncMock(
            return_value={"anonymized": "data"}
        )

        # Create template
        template = await version_manager.create_template(
            version_id=sample_resume_version.id,
            user_id=sample_resume_version.user_id,
            template_name="Software Engineer Template",
            template_description="Template for software engineering roles",
            industry="technology",
            experience_level="mid-level",
        )

        # Assertions
        assert template is not None
        assert isinstance(template, VersionTemplate)
        assert template.name == "Software Engineer Template"
        assert template.industry == "technology"
        assert template.experience_level == "mid-level"
        assert template.created_by == sample_resume_version.user_id

    @pytest.mark.asyncio
    async def test_get_analytics(self, version_manager):
        """Test getting version analytics."""
        # Mock analytics data
        mock_analytics = {
            "id": "analytics-1",
            "user_id": "test-user-456",
            "version_id": "test-version-123",
            "view_count": 5,
            "edit_count": 2,
            "download_count": 1,
            "share_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
        }
        version_manager.db.find = Mock(return_value=[mock_analytics])

        # Get analytics
        analytics = await version_manager.get_analytics(
            "test-user-456", "test-version-123"
        )

        # Assertions
        assert analytics is not None
        assert isinstance(analytics, VersionAnalytics)
        assert analytics.view_count == 5
        assert analytics.edit_count == 2

    @pytest.mark.asyncio
    async def test_calculate_quality_scores(self, version_manager, sample_resume_data):
        """Test quality score calculation."""
        scores = await version_manager._calculate_quality_scores(sample_resume_data)

        # Assertions
        assert isinstance(scores, dict)
        assert "overall_score" in scores
        assert "ats_score" in scores
        assert "keyword_score" in scores
        assert 0.0 <= scores["overall_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_cleanup_old_versions(self, version_manager):
        """Test cleanup of old versions."""
        # Mock old versions
        old_versions = []
        for i in range(15):  # More than buffer
            version = Mock()
            version.id = f"version-{i}"
            version.is_current = False
            version.is_template = False
            old_versions.append(version)

        version_manager.list_versions = AsyncMock(return_value=old_versions)
        version_manager.delete_version = AsyncMock(return_value=True)

        # Run cleanup
        await version_manager._cleanup_old_versions("test-user-456")

        # Should delete some versions (keeping buffer)
        assert version_manager.delete_version.call_count > 0

    @pytest.mark.asyncio
    async def test_create_backup(self, version_manager, sample_resume_version):
        """Test backup creation."""
        # Store version
        version_manager.db.create(
            "resume_versions",
            sample_resume_version.id,
            sample_resume_version.model_dump(),
        )

        # Create backup
        backup = await version_manager._create_backup(
            sample_resume_version.id, "test_reason"
        )

        # Assertions
        assert backup is not None
        assert isinstance(backup, VersionBackup)
        assert backup.version_id == sample_resume_version.id
        assert backup.backup_reason == "test_reason"
        assert backup.expires_at > datetime.utcnow()

        # Verify backup was stored
        stored_backup = version_manager.db.read("version_backups", backup.id)
        assert stored_backup is not None

    @pytest.mark.asyncio
    async def test_initialize_analytics(self, version_manager):
        """Test analytics initialization."""
        await version_manager._initialize_analytics("test-user-456", "test-version-123")

        # Verify analytics was created
        analytics_data = version_manager.db.read(
            "version_analytics", "test-user-456_test-version-123"
        )
        assert analytics_data is not None

    @pytest.mark.asyncio
    async def test_update_analytics(self, version_manager):
        """Test analytics update."""
        # Initialize analytics first
        await version_manager._initialize_analytics("test-user-456", "test-version-123")

        # Update analytics
        await version_manager._update_analytics(
            "test-user-456", "test-version-123", "view"
        )

        # Verify analytics was updated
        analytics_data = version_manager.db.find(
            "version_analytics", user_id="test-user-456", version_id="test-version-123"
        )
        assert len(analytics_data) == 1
        # Note: The actual count increment would be tested in a more detailed implementation

    @pytest.mark.asyncio
    async def test_cleanup_version_data(self, version_manager):
        """Test cleanup of version-related data."""
        version_id = "test-version-123"

        # Create some related data
        version_manager.db.create(
            "version_backups", "backup-1", {"version_id": version_id}
        )
        version_manager.db.create(
            "version_analytics", "analytics-1", {"version_id": version_id}
        )
        version_manager.db.create(
            "version_comparisons", "comparison-1", {"version1_id": version_id}
        )

        # Run cleanup
        await version_manager._cleanup_version_data(version_id)

        # Verify data was cleaned up (implementation would need to be more detailed)
        # This is a basic test of the method execution

    @pytest.mark.asyncio
    async def test_calculate_similarity(self, version_manager):
        """Test similarity calculation between resume data."""
        data1 = {
            "section1": {"content": "same content"},
            "section2": {"content": "different1"},
        }
        data2 = {
            "section1": {"content": "same content"},
            "section2": {"content": "different2"},
        }

        similarity = await version_manager._calculate_similarity(data1, data2)

        # Assertions
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be somewhat similar due to shared content

    @pytest.mark.asyncio
    async def test_calculate_section_differences(self, version_manager):
        """Test section difference calculation."""
        data1 = {
            "sections": {
                "personal_details": {"name": "John Doe"},
                "work_experience": [{"title": "Engineer"}],
            }
        }
        data2 = {
            "sections": {
                "personal_details": {"name": "John Smith"},  # Changed
                "work_experience": [{"title": "Engineer"}],  # Same
                "skills": ["Python"],  # Added
            }
        }

        differences = await version_manager._calculate_section_differences(data1, data2)

        # Assertions
        assert "personal_details" in differences
        assert differences["personal_details"]["changed"] is True
        assert "work_experience" in differences
        assert differences["work_experience"]["changed"] is False
        assert "skills" in differences
        assert differences["skills"]["added_in_v2"] is True

    @pytest.mark.asyncio
    async def test_anonymize_resume_data(self, version_manager, sample_resume_data):
        """Test resume data anonymization for templates."""
        anonymized = await version_manager._anonymize_resume_data(sample_resume_data)

        # Assertions
        assert anonymized is not None
        personal_details = anonymized["sections"]["personal_details"]
        assert personal_details["name"] == "[Your Name]"
        assert personal_details["email"] == "[your.email@example.com]"
        assert personal_details["phone"] == "[Your Phone Number]"

        # Work experience should be anonymized
        work_exp = anonymized["sections"]["work_experience"][0]
        assert work_exp["company"] == "[Company Name]"

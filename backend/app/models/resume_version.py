from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class ResumeVersion(BaseModel):
    """A specific version of a resume"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None

    # Resume data
    resume_data: Dict[str, Any]

    # Version metadata
    version_number: int = 1
    is_current: bool = False
    is_template: bool = False

    # Optimization details
    job_target: Optional[str] = None
    target_industry: Optional[str] = None
    optimization_type: Optional[str] = None

    # Quality metrics
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ats_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    keyword_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)

    # Usage tracking
    download_count: int = 0
    last_downloaded: Optional[datetime] = None

    # Tags and categorization
    tags: List[str] = []
    category: Optional[str] = None


class VersionComparison(BaseModel):
    """Comparison between two resume versions"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    version1_id: str
    version2_id: str

    # Version details
    version1: ResumeVersion
    version2: ResumeVersion

    # Overall comparison
    overall_similarity: float = Field(ge=0.0, le=1.0)
    quality_difference: Optional[float] = None

    # Section-by-section differences
    section_differences: Dict[str, Dict[str, Any]] = {}

    # Change summary
    additions: List[str] = []
    deletions: List[str] = []
    modifications: List[str] = []

    # Detailed changes
    content_changes: Dict[str, Any] = {}
    formatting_changes: List[str] = []
    structural_changes: List[str] = []

    # Improvement analysis
    improvements: List[str] = []
    regressions: List[str] = []
    neutral_changes: List[str] = []

    # Recommendations
    merge_suggestions: List[str] = []
    rollback_recommendations: List[str] = []

    comparison_date: datetime = Field(default_factory=datetime.utcnow)


class VersionHistory(BaseModel):
    """History of changes for a resume version"""

    version_id: str
    changes: List[Dict[str, Any]] = []
    total_changes: int = 0
    major_revisions: int = 0
    minor_revisions: int = 0

    # Change statistics
    sections_modified: List[str] = []
    most_changed_section: Optional[str] = None
    change_frequency: Dict[str, int] = {}

    # Timeline
    first_created: datetime
    last_modified: datetime
    modification_timeline: List[Dict[str, Any]] = []


class VersionTemplate(BaseModel):
    """Template created from a successful resume version"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str

    # Template data (anonymized)
    template_structure: Dict[str, Any]
    recommended_sections: List[str] = []

    # Template metadata
    industry: Optional[str] = None
    experience_level: Optional[str] = None
    job_types: List[str] = []

    # Performance metrics
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    average_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    usage_count: int = 0

    # Template settings
    is_public: bool = False
    is_premium: bool = False

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # User ID who created the template


class VersionBackup(BaseModel):
    """Backup of a resume version for recovery"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    version_id: str
    backup_data: Dict[str, Any]
    backup_reason: Literal[
        "auto_save", "manual_save", "pre_optimization", "pre_major_change"
    ]

    # Backup metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_recoverable: bool = True

    # Recovery information
    recovery_instructions: Optional[str] = None
    dependencies: List[str] = []  # Other backups this depends on


class VersionAnalytics(BaseModel):
    """Analytics data for resume versions"""

    user_id: str
    version_id: str

    # Usage metrics
    view_count: int = 0
    edit_count: int = 0
    download_count: int = 0
    share_count: int = 0

    # Performance metrics
    average_session_duration: float = 0.0
    bounce_rate: float = 0.0
    completion_rate: float = 0.0

    # Success metrics
    job_applications: int = 0
    interview_callbacks: int = 0
    job_offers: int = 0

    # Tracking period
    tracking_start: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

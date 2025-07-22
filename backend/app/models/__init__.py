# Resume models
from .resume import (
    EducationEntry,
    WorkProject,
    WorkExperienceEntry,
    ProjectEntry,
    SkillCategory,
    PersonalDetails,
    CertificationEntry,
    LanguageEntry,
    ResumeMetadata,
    ResumeSections,
    ResumeDocument,
)

# Conversation models
from .conversation import (
    ResumeContext,
    Suggestion,
    Message,
    ConversationSession,
    AIResponse,
    ConversationSummary,
)

# Optimization models
from .optimization_request import (
    OptimizationRequest,
    OptimizationResult,
    SectionAnalysis,
    ImprovementMetrics,
    ValidationResult,
)

# Job analysis models
from .job_analysis import (
    JobDescription,
    SkillRequirement,
    JobAnalysis,
    ResumeJobMatch,
    JobMatchRecommendation,
    JobComparisonResult,
)

# Feedback models
from .feedback import (
    FeedbackItem,
    ATSCompatibilityResult,
    ConsistencyReport,
    ChangeImpactAnalysis,
    RealTimeFeedback,
    UserFeedback,
)

# Version management models
from .resume_version import (
    ResumeVersion,
    VersionComparison,
    VersionHistory,
    VersionTemplate,
    VersionBackup,
    VersionAnalytics,
)

# User preferences models
from .user_preferences import (
    UserPreference,
    SuggestionFeedback,
    UserProfile,
    LearningInsight,
    PersonalizationSettings,
)

__all__ = [
    # Resume models
    "EducationEntry",
    "WorkProject",
    "WorkExperienceEntry",
    "ProjectEntry",
    "SkillCategory",
    "PersonalDetails",
    "CertificationEntry",
    "LanguageEntry",
    "ResumeMetadata",
    "ResumeSections",
    "ResumeDocument",
    # Conversation models
    "ResumeContext",
    "Suggestion",
    "Message",
    "ConversationSession",
    "AIResponse",
    "ConversationSummary",
    # Optimization models
    "OptimizationRequest",
    "OptimizationResult",
    "SectionAnalysis",
    "ImprovementMetrics",
    "ValidationResult",
    # Job analysis models
    "JobDescription",
    "SkillRequirement",
    "JobAnalysis",
    "ResumeJobMatch",
    "JobMatchRecommendation",
    "JobComparisonResult",
    # Feedback models
    "FeedbackItem",
    "ATSCompatibilityResult",
    "ConsistencyReport",
    "ChangeImpactAnalysis",
    "RealTimeFeedback",
    "UserFeedback",
    # Version management models
    "ResumeVersion",
    "VersionComparison",
    "VersionHistory",
    "VersionTemplate",
    "VersionBackup",
    "VersionAnalytics",
    # User preferences models
    "UserPreference",
    "SuggestionFeedback",
    "UserProfile",
    "LearningInsight",
    "PersonalizationSettings",
]

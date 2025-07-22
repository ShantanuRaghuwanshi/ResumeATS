from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class FeedbackItem(BaseModel):
    """Individual feedback item"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["error", "warning", "info", "success", "suggestion"]
    category: Literal[
        "content", "formatting", "ats", "keywords", "structure", "consistency"
    ]
    title: str
    message: str
    section: Optional[str] = None
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    actionable: bool = True
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ATSCompatibilityResult(BaseModel):
    """ATS compatibility analysis result"""

    overall_score: float = Field(ge=0.0, le=1.0)
    parsing_score: float = Field(ge=0.0, le=1.0)
    formatting_score: float = Field(ge=0.0, le=1.0)
    keyword_score: float = Field(ge=0.0, le=1.0)
    structure_score: float = Field(ge=0.0, le=1.0)

    # Specific issues
    formatting_issues: List[str] = []
    parsing_issues: List[str] = []
    missing_sections: List[str] = []
    problematic_elements: List[str] = []

    # Recommendations
    recommendations: List[str] = []
    quick_fixes: List[str] = []

    analysis_date: datetime = Field(default_factory=datetime.utcnow)


class ConsistencyReport(BaseModel):
    """Report on resume consistency across sections"""

    overall_consistency_score: float = Field(ge=0.0, le=1.0)

    # Consistency checks
    date_consistency: bool = True
    formatting_consistency: bool = True
    tone_consistency: bool = True
    terminology_consistency: bool = True

    # Issues found
    date_conflicts: List[str] = []
    formatting_inconsistencies: List[str] = []
    tone_variations: List[str] = []
    terminology_conflicts: List[str] = []

    # Cross-section issues
    skill_redundancy: List[str] = []
    missing_cross_references: List[str] = []
    contradictory_information: List[str] = []

    recommendations: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChangeImpactAnalysis(BaseModel):
    """Analysis of the impact of resume changes"""

    change_id: str = Field(default_factory=lambda: str(uuid4()))
    section: str
    change_type: Literal["addition", "modification", "deletion", "restructure"]

    # Before and after content
    before_content: Dict[str, Any]
    after_content: Dict[str, Any]

    # Impact scores
    overall_impact: float = Field(
        ge=-1.0, le=1.0
    )  # Negative means worse, positive means better
    ats_impact: float = Field(ge=-1.0, le=1.0)
    keyword_impact: float = Field(ge=-1.0, le=1.0)
    readability_impact: float = Field(ge=-1.0, le=1.0)
    relevance_impact: float = Field(ge=-1.0, le=1.0)

    # Detailed analysis
    positive_changes: List[str] = []
    negative_changes: List[str] = []
    neutral_changes: List[str] = []

    # Recommendations
    further_improvements: List[str] = []
    warnings: List[str] = []

    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class RealTimeFeedback(BaseModel):
    """Real-time feedback for live editing"""

    session_id: str
    section: str
    current_content: str

    # Immediate feedback
    character_count: int
    word_count: int
    readability_score: float = Field(ge=0.0, le=1.0)
    keyword_density: Dict[str, float] = {}

    # Live suggestions
    grammar_issues: List[str] = []
    style_suggestions: List[str] = []
    keyword_suggestions: List[str] = []

    # Scores
    current_quality_score: float = Field(ge=0.0, le=1.0)
    ats_compatibility: float = Field(ge=0.0, le=1.0)

    # Comparison with previous version
    improvement_since_last: Optional[float] = None

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserFeedback(BaseModel):
    """User feedback on AI suggestions and system performance"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    suggestion_id: Optional[str] = None
    session_id: Optional[str] = None

    # Feedback details
    rating: int = Field(ge=1, le=5)
    feedback_type: Literal[
        "suggestion_quality", "system_performance", "user_experience", "bug_report"
    ]
    comment: Optional[str] = None

    # Context
    section: Optional[str] = None
    feature_used: Optional[str] = None

    # Metadata
    helpful: Optional[bool] = None
    would_recommend: Optional[bool] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

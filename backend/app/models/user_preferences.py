from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class UserPreference(BaseModel):
    """Individual user preference"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    category: Literal[
        "suggestion_type",
        "writing_style",
        "industry",
        "experience_level",
        "optimization_focus",
    ]
    preference_key: str
    preference_value: Any
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    source: Literal["explicit", "implicit", "inferred"] = "explicit"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class SuggestionFeedback(BaseModel):
    """User feedback on AI suggestions"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    suggestion_id: str
    session_id: str

    # Feedback details
    action: Literal["accepted", "rejected", "modified", "ignored"]
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None

    # Context
    section: str
    suggestion_type: str
    original_content: str
    suggested_content: str
    final_content: Optional[str] = None  # What user actually used

    # Timing
    time_to_decision_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfile(BaseModel):
    """Comprehensive user profile for personalization"""

    user_id: str

    # Basic information
    industry: Optional[str] = None
    experience_level: Optional[Literal["entry", "mid", "senior", "executive"]] = None
    job_titles: List[str] = []
    target_roles: List[str] = []

    # Preferences
    writing_style: Optional[Literal["formal", "casual", "technical", "creative"]] = None
    optimization_focus: List[str] = []  # e.g., ["ats", "keywords", "readability"]
    preferred_section_order: List[str] = []

    # Behavioral patterns
    typical_session_duration: Optional[float] = None
    preferred_suggestion_types: List[str] = []
    common_rejection_reasons: List[str] = []

    # Learning data
    suggestion_acceptance_rate: float = 0.0
    most_improved_sections: List[str] = []
    learning_velocity: float = 0.0  # How quickly user adopts suggestions

    # Metadata
    profile_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LearningInsight(BaseModel):
    """Insights derived from user behavior"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str

    # Insight details
    insight_type: Literal["preference", "pattern", "improvement_area", "strength"]
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Supporting data
    evidence: List[str] = []
    data_points: int = 0

    # Actionability
    is_actionable: bool = True
    recommended_actions: List[str] = []

    # Metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class PersonalizationSettings(BaseModel):
    """User's personalization settings"""

    user_id: str

    # AI behavior settings
    suggestion_aggressiveness: Literal["conservative", "moderate", "aggressive"] = (
        "moderate"
    )
    auto_apply_high_confidence: bool = False
    show_reasoning: bool = True

    # Notification preferences
    real_time_feedback: bool = True
    email_suggestions: bool = False
    weekly_summary: bool = True

    # Privacy settings
    allow_learning: bool = True
    share_anonymous_data: bool = False

    # Interface preferences
    preferred_theme: Literal["light", "dark", "auto"] = "auto"
    compact_mode: bool = False

    # Advanced settings
    custom_prompts: Dict[str, str] = {}
    section_priorities: Dict[str, int] = {}

    last_updated: datetime = Field(default_factory=datetime.utcnow)

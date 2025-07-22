from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class ResumeContext(BaseModel):
    """Context information about the resume for AI conversations"""

    resume_id: str
    user_id: str
    current_section: str
    full_resume_data: Dict[str, Any]
    job_description: Optional[str] = None
    optimization_goals: List[str] = []
    user_preferences: Dict[str, Any] = {}


class Suggestion(BaseModel):
    """AI suggestion for resume improvement"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["content", "structure", "keyword", "formatting", "removal"]
    title: str
    description: str
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None
    impact_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    section: str
    confidence: float = Field(ge=0.0, le=1.0)
    applied: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Message(BaseModel):
    """Chat message in a conversation"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    suggestions: List[Suggestion] = []
    metadata: Dict[str, Any] = {}


class ConversationSession(BaseModel):
    """AI conversation session for resume optimization"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    resume_id: str
    user_id: str
    section: str
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    context: ResumeContext
    messages: List[Message] = []
    is_active: bool = True
    total_suggestions: int = 0
    applied_suggestions: int = 0


class AIResponse(BaseModel):
    """Response from AI assistant"""

    message: str
    suggestions: List[Suggestion] = []
    context_updates: Optional[Dict[str, Any]] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    follow_up_questions: List[str] = []


class ConversationSummary(BaseModel):
    """Summary of a conversation session"""

    session_id: str
    section: str
    total_messages: int
    suggestions_generated: int
    suggestions_applied: int
    improvement_score: Optional[float] = None
    key_topics: List[str] = []
    duration_minutes: int
    created_at: datetime
    last_activity: datetime

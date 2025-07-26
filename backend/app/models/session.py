"""
Session management models for LLM configuration and user sessions
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class SessionStatus(str, Enum):
    """Session status enumeration"""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class LLMProviderType(str, Enum):
    """Supported LLM provider types"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMConfiguration(BaseModel):
    """LLM configuration model"""

    provider: LLMProviderType
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama or custom endpoints
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    additional_params: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserSession(BaseModel):
    """User session model with LLM configuration"""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    llm_config: LLMConfiguration
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def is_valid(self) -> bool:
        """Check if session is still valid"""
        if self.status != SessionStatus.ACTIVE:
            return False

        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False

        return True

    def update_access_time(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now(timezone.utc)


class SessionData(BaseModel):
    """Data associated with a session"""

    session_id: str
    resume_data: Dict[str, Any] = Field(default_factory=dict)
    conversation_history: List[str] = Field(default_factory=list)
    optimization_history: List[str] = Field(default_factory=list)
    job_analyses: List[str] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def add_resume(self, resume_id: str):
        """Add resume to session data"""
        if "resumes" not in self.resume_data:
            self.resume_data["resumes"] = []
        if resume_id not in self.resume_data["resumes"]:
            self.resume_data["resumes"].append(resume_id)
        self.updated_at = datetime.now(timezone.utc)

    def add_conversation(self, conversation_id: str):
        """Add conversation to session"""
        if conversation_id not in self.conversation_history:
            self.conversation_history.append(conversation_id)
        self.updated_at = datetime.now(timezone.utc)

    def add_optimization(self, optimization_id: str):
        """Add optimization to session"""
        if optimization_id not in self.optimization_history:
            self.optimization_history.append(optimization_id)
        self.updated_at = datetime.now(timezone.utc)

    def add_job_analysis(self, analysis_id: str):
        """Add job analysis to session"""
        if analysis_id not in self.job_analyses:
            self.job_analyses.append(analysis_id)
        self.updated_at = datetime.now(timezone.utc)


class LLMTestRequest(BaseModel):
    """Request model for testing LLM configuration"""

    provider: LLMProviderType
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=100, gt=0, le=1000)
    test_prompt: str = "Hello, please respond with 'Configuration test successful!'"
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class LLMTestResponse(BaseModel):
    """Response model for LLM configuration test"""

    success: bool
    response_text: Optional[str] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None
    provider_info: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    """Request model for creating a new session"""

    llm_config: LLMConfiguration
    device_id: Optional[str] = None
    session_duration_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    """Response model for session creation"""

    session_id: str
    status: str
    expires_at: Optional[datetime] = None
    message: str


class SessionValidationResponse(BaseModel):
    """Response model for session validation"""

    valid: bool
    session_id: Optional[str] = None
    status: Optional[SessionStatus] = None
    error_message: Optional[str] = None
    llm_config: Optional[LLMConfiguration] = None

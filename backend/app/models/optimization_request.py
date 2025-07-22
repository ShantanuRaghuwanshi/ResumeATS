from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class OptimizationRequest(BaseModel):
    """Request for AI-powered resume optimization"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    resume_id: str
    user_id: str
    section: str
    content: Any  # Can be Dict, List, or other types depending on section
    job_description: Optional[str] = None
    optimization_type: Literal[
        "general", "job_specific", "ats_friendly", "industry_specific"
    ]
    target_industry: Optional[str] = None
    experience_level: Optional[Literal["entry", "mid", "senior", "executive"]] = None
    specific_instructions: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["pending", "processing", "completed", "failed"] = "pending"


class OptimizationResult(BaseModel):
    """Result of resume optimization"""

    request_id: str
    optimized_content: Any  # Can be Dict, List, or other types depending on section
    suggestions: List[Dict[str, Any]]
    improvement_score: float = Field(ge=0.0, le=1.0)
    ats_score: float = Field(ge=0.0, le=1.0)
    keyword_density: Dict[str, float] = {}
    readability_score: float = Field(ge=0.0, le=1.0)
    changes_summary: str
    processing_time_seconds: float
    completed_at: datetime = Field(default_factory=datetime.utcnow)


class SectionAnalysis(BaseModel):
    """Analysis of a specific resume section"""

    section: str
    current_content: Any  # Can be Dict, List, or other types depending on section
    strengths: List[str]
    weaknesses: List[str]
    missing_elements: List[str]
    keyword_gaps: List[str]
    improvement_opportunities: List[str]
    ats_compatibility_score: float = Field(ge=0.0, le=1.0)
    content_quality_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)


class ImprovementMetrics(BaseModel):
    """Metrics showing improvement after optimization"""

    before_score: float
    after_score: float
    improvement_percentage: float
    ats_improvement: float
    keyword_improvement: float
    readability_improvement: float
    content_quality_improvement: float
    specific_improvements: Dict[str, float] = {}


class ValidationResult(BaseModel):
    """Result of validating resume changes"""

    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    consistency_issues: List[str] = []
    ats_issues: List[str] = []
    formatting_issues: List[str] = []
    overall_quality_score: float = Field(ge=0.0, le=1.0)

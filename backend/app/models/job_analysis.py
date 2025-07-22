from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class JobDescription(BaseModel):
    """Structured job description data"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_text: str
    job_title: str
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[
        Literal["full-time", "part-time", "contract", "internship"]
    ] = None
    experience_level: Optional[Literal["entry", "mid", "senior", "executive"]] = None
    salary_range: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SkillRequirement(BaseModel):
    """Individual skill requirement from job description"""

    name: str
    category: Literal["technical", "soft", "language", "certification", "tool"]
    importance: Literal["required", "preferred", "nice_to_have"]
    proficiency_level: Optional[
        Literal["beginner", "intermediate", "advanced", "expert"]
    ] = None
    years_experience: Optional[int] = None
    context: Optional[str] = None


class JobAnalysis(BaseModel):
    """Comprehensive analysis of a job description"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    job_description_id: str
    job_title: str
    company: Optional[str] = None
    industry: Optional[str] = None

    # Skills and requirements
    required_skills: List[SkillRequirement] = []
    preferred_skills: List[SkillRequirement] = []
    technical_skills: List[str] = []
    soft_skills: List[str] = []
    certifications: List[str] = []
    tools_technologies: List[str] = []

    # Experience and qualifications
    min_years_experience: Optional[int] = None
    max_years_experience: Optional[int] = None
    education_requirements: List[str] = []

    # Job details
    key_responsibilities: List[str] = []
    company_values: List[str] = []
    benefits: List[str] = []

    # Keywords and phrases
    industry_keywords: List[str] = []
    action_verbs: List[str] = []
    buzzwords: List[str] = []

    # Analysis metadata
    confidence_score: float = Field(ge=0.0, le=1.0)
    analysis_date: datetime = Field(default_factory=datetime.utcnow)
    processing_time_seconds: float = 0.0


class ResumeJobMatch(BaseModel):
    """Analysis of how well a resume matches a job"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    resume_id: str
    job_analysis_id: str

    # Overall matching
    overall_match_score: float = Field(ge=0.0, le=1.0)
    recommendation: Literal[
        "strong_match", "good_match", "moderate_match", "weak_match"
    ]

    # Section-specific scores
    section_scores: Dict[str, float] = {}

    # Skill matching
    matching_skills: List[str] = []
    missing_required_skills: List[str] = []
    missing_preferred_skills: List[str] = []
    skill_match_percentage: float = Field(ge=0.0, le=1.0)

    # Experience matching
    experience_match: bool = True
    experience_gap_years: int = 0

    # Keyword analysis
    keyword_match_score: float = Field(ge=0.0, le=1.0)
    missing_keywords: List[str] = []

    # Generated at
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobMatchRecommendation(BaseModel):
    """Specific recommendation for improving job match"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    match_id: str
    section: str
    type: Literal[
        "add_skill", "add_keyword", "modify_content", "add_experience", "restructure"
    ]
    priority: Literal["high", "medium", "low"]
    title: str
    description: str
    specific_action: str
    expected_impact: float = Field(ge=0.0, le=1.0)
    difficulty: Literal["easy", "medium", "hard"]
    estimated_time_minutes: int = 0


class JobComparisonResult(BaseModel):
    """Result of comparing multiple job descriptions"""

    job_ids: List[str]
    common_skills: List[str] = []
    common_keywords: List[str] = []
    skill_frequency: Dict[str, int] = {}
    keyword_frequency: Dict[str, int] = {}
    average_experience_requirement: Optional[float] = None
    common_responsibilities: List[str] = []
    industry_trends: List[str] = []
    merged_requirements: JobAnalysis
    comparison_date: datetime = Field(default_factory=datetime.utcnow)

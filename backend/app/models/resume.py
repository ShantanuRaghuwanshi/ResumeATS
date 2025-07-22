from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4


class EducationEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    university: str
    degree: str
    location: Optional[str] = None
    from_year: Optional[str] = None
    to_year: Optional[str] = None
    gpa: Optional[str] = None
    relevant_coursework: List[str] = []
    honors: List[str] = []
    activities: List[str] = []


class WorkProject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    summary: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: Optional[List[str]] = None
    technologies: List[str] = []
    achievements: List[str] = []
    metrics: Dict[str, str] = {}


class WorkExperienceEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    company: str
    location: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    summary: Optional[str] = None
    projects: Optional[List[WorkProject]] = None
    achievements: List[str] = []
    technologies: List[str] = []
    metrics: Dict[str, str] = {}
    is_current: bool = False


class ProjectEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    summary: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[str]
    technologies: List[str] = []
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    achievements: List[str] = []


class SkillCategory(BaseModel):
    category: str
    skills: List[str]
    proficiency_levels: Dict[str, str] = {}  # skill -> proficiency level


class PersonalDetails(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = ""
    github: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    summary: Optional[str] = None
    objective: Optional[str] = None


class CertificationEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    issuer: str
    date_obtained: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    verification_url: Optional[str] = None


class LanguageEntry(BaseModel):
    language: str
    proficiency: Literal["native", "fluent", "advanced", "intermediate", "beginner"]


class ResumeMetadata(BaseModel):
    """Metadata about the resume"""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"
    template_used: Optional[str] = None
    optimization_history: List[str] = []
    ats_score: Optional[float] = None
    keyword_score: Optional[float] = None
    overall_score: Optional[float] = None


class ResumeSections(BaseModel):
    personal_details: PersonalDetails
    education: List[EducationEntry] = []
    work_experience: List[WorkExperienceEntry] = []
    projects: List[ProjectEntry] = []
    skills: List[SkillCategory] = []
    certifications: List[CertificationEntry] = []
    languages: List[LanguageEntry] = []
    additional_sections: Dict[str, Any] = {}  # For custom sections
    metadata: ResumeMetadata = Field(default_factory=ResumeMetadata)


class ResumeDocument(BaseModel):
    """Complete resume document with all sections and metadata"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: str = "My Resume"
    sections: ResumeSections
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_modified: datetime = Field(default_factory=datetime.utcnow)

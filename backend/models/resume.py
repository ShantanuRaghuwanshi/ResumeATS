from typing import Optional, List
from pydantic import BaseModel


class EducationEntry(BaseModel):
    university: str
    degree: str
    location: Optional[str] = None
    from_year: Optional[str] = None
    to_year: Optional[str] = None
    gpa: Optional[str] = None


class WorkProject(BaseModel):
    name: str
    summary: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: Optional[List[str]] = None


class WorkExperienceEntry(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    summary: Optional[str] = None
    projects: Optional[List[WorkProject]] = None


class ProjectEntry(BaseModel):
    name: str
    summary: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[str]


class PersonalDetails(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = ""


class ResumeSections(BaseModel):
    education: List[EducationEntry]
    work_experience: List[WorkExperienceEntry]
    projects: List[ProjectEntry]
    skills: List[str]

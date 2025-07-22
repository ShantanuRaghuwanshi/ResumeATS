"""
Shared test fixtures and configuration for resume optimization tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, List
from datetime import datetime
import json
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from models.conversation import ConversationSession, Message, ResumeContext, Suggestion
from models.resume import ResumeDocument, ResumeSections
from models.job_analysis import JobAnalysis, SkillRequirement
from models.optimization_request import OptimizationRequest, OptimizationResult
from models.feedback import (
    ATSCompatibilityResult,
    ConsistencyReport,
    ChangeImpactAnalysis,
)
from models.resume_version import ResumeVersion


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    db = Mock()
    db.data = {}

    def create(collection, key, data):
        if collection not in db.data:
            db.data[collection] = {}
        db.data[collection][key] = data
        return True

    def read(collection, key):
        return db.data.get(collection, {}).get(key)

    def update(collection, key, data):
        if collection not in db.data:
            db.data[collection] = {}
        db.data[collection][key] = data
        return True

    def delete(collection, key):
        if collection in db.data and key in db.data[collection]:
            del db.data[collection][key]
            return True
        return False

    def find(collection, **filters):
        if collection not in db.data:
            return []

        results = []
        for key, data in db.data[collection].items():
            match = True
            for filter_key, filter_value in filters.items():
                if data.get(filter_key) != filter_value:
                    match = False
                    break
            if match:
                results.append(data)
        return results

    db.create = create
    db.read = read
    db.update = update
    db.delete = delete
    db.find = find

    return db


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = AsyncMock()
    provider.generate_response = AsyncMock(return_value="Mock LLM response")
    provider.generate_suggestions = AsyncMock(return_value=[])
    provider.analyze_content = AsyncMock(return_value={"analysis": "mock"})
    return provider


@pytest.fixture
def sample_resume_data():
    """Sample resume data for testing."""
    return {
        "sections": {
            "personal_details": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-0123",
                "location": "New York, NY",
                "summary": "Experienced software engineer with 5+ years in web development.",
            },
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "from_date": "2020-01",
                    "to_date": "present",
                    "location": "New York, NY",
                    "summary": "Led development of web applications",
                    "achievements": [
                        "Improved application performance by 40%",
                        "Led team of 5 developers",
                        "Implemented CI/CD pipeline",
                    ],
                    "technologies": ["Python", "React", "AWS", "Docker"],
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupXYZ",
                    "from_date": "2018-06",
                    "to_date": "2019-12",
                    "location": "San Francisco, CA",
                    "summary": "Developed full-stack web applications",
                    "achievements": [
                        "Built user authentication system",
                        "Reduced load times by 30%",
                    ],
                    "technologies": ["JavaScript", "Node.js", "MongoDB"],
                },
            ],
            "education": [
                {
                    "degree": "Bachelor of Science in Computer Science",
                    "institution": "University of Technology",
                    "graduation_date": "2018-05",
                    "gpa": "3.8",
                    "relevant_coursework": [
                        "Data Structures",
                        "Algorithms",
                        "Software Engineering",
                    ],
                }
            ],
            "skills": [
                {
                    "category": "Programming Languages",
                    "skills": ["Python", "JavaScript", "Java", "TypeScript"],
                },
                {
                    "category": "Frameworks & Libraries",
                    "skills": ["React", "Django", "Flask", "Node.js"],
                },
                {
                    "category": "Tools & Technologies",
                    "skills": ["AWS", "Docker", "Git", "Jenkins"],
                },
            ],
            "projects": [
                {
                    "name": "E-commerce Platform",
                    "description": "Built a full-stack e-commerce platform with React and Django",
                    "technologies": ["React", "Django", "PostgreSQL", "AWS"],
                    "outcomes": ["Processed 1000+ orders", "99.9% uptime"],
                    "links": ["https://github.com/johndoe/ecommerce"],
                }
            ],
        }
    }


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Senior Software Engineer - Full Stack

    We are looking for a Senior Software Engineer to join our growing team. 
    
    Requirements:
    - 5+ years of experience in software development
    - Strong proficiency in Python and JavaScript
    - Experience with React and Django frameworks
    - Knowledge of AWS cloud services
    - Experience with Docker and containerization
    - Strong problem-solving skills
    - Excellent communication skills
    
    Preferred:
    - Experience with microservices architecture
    - Knowledge of CI/CD pipelines
    - Experience with agile development methodologies
    
    Responsibilities:
    - Design and develop scalable web applications
    - Collaborate with cross-functional teams
    - Mentor junior developers
    - Participate in code reviews
    - Optimize application performance
    """


@pytest.fixture
def sample_conversation_session(sample_resume_data):
    """Sample conversation session for testing."""
    context = ResumeContext(
        resume_id="test-resume-123",
        user_id="test-user-456",
        current_section="work_experience",
        full_resume_data=sample_resume_data,
        user_preferences={},
    )

    session = ConversationSession(
        resume_id="test-resume-123",
        user_id="test-user-456",
        section="work_experience",
        title="Work Experience Optimization",
        context=context,
    )

    return session


@pytest.fixture
def sample_suggestions():
    """Sample suggestions for testing."""
    return [
        Suggestion(
            type="content",
            title="Use stronger action verbs",
            description="Replace weak verbs with powerful action words",
            impact_score=0.8,
            reasoning="Action verbs make achievements more compelling",
            section="work_experience",
            confidence=0.9,
        ),
        Suggestion(
            type="structure",
            title="Add quantified achievements",
            description="Include specific metrics and numbers",
            impact_score=0.9,
            reasoning="Quantified achievements demonstrate impact",
            section="work_experience",
            confidence=0.85,
        ),
    ]


@pytest.fixture
def sample_job_analysis():
    """Sample job analysis for testing."""
    return JobAnalysis(
        job_title="Senior Software Engineer",
        company="Tech Company",
        industry="technology",
        required_skills=[
            SkillRequirement(
                name="Python",
                category="technical",
                importance="required",
                proficiency_level="advanced",
                years_experience=5,
            ),
            SkillRequirement(
                name="JavaScript",
                category="technical",
                importance="required",
                proficiency_level="advanced",
                years_experience=3,
            ),
        ],
        preferred_skills=[
            SkillRequirement(
                name="React",
                category="technical",
                importance="preferred",
                proficiency_level="intermediate",
            )
        ],
        technical_skills=["Python", "JavaScript", "React", "Django"],
        soft_skills=["Communication", "Leadership", "Problem Solving"],
        min_years_experience=5,
        max_years_experience=8,
        key_responsibilities=[
            "Design and develop scalable web applications",
            "Collaborate with cross-functional teams",
            "Mentor junior developers",
        ],
        industry_keywords=["software", "development", "scalable", "agile"],
        confidence_score=0.85,
    )


@pytest.fixture
def sample_optimization_request(sample_resume_data):
    """Sample optimization request for testing."""
    return OptimizationRequest(
        resume_id="test-resume-123",
        user_id="test-user-456",
        section="work_experience",
        content=sample_resume_data["sections"]["work_experience"],
        optimization_type="general",
    )


@pytest.fixture
def sample_resume_version(sample_resume_data):
    """Sample resume version for testing."""
    return ResumeVersion(
        user_id="test-user-456",
        name="Software Engineer Resume v1",
        description="Initial version targeting software engineering roles",
        resume_data=sample_resume_data,
        version_number=1,
        job_target="Software Engineer",
        overall_score=0.75,
        ats_score=0.80,
        keyword_score=0.70,
    )


@pytest.fixture
def sample_ats_result():
    """Sample ATS compatibility result for testing."""
    return ATSCompatibilityResult(
        overall_score=0.85,
        parsing_score=0.90,
        formatting_score=0.80,
        keyword_score=0.85,
        structure_score=0.85,
        formatting_issues=["Contains special characters"],
        parsing_issues=[],
        missing_sections=[],
        problematic_elements=[],
        recommendations=["Use standard bullet points"],
        quick_fixes=["Replace • with -"],
    )


@pytest.fixture
def sample_consistency_report():
    """Sample consistency report for testing."""
    return ConsistencyReport(
        overall_consistency_score=0.90,
        date_consistency=True,
        formatting_consistency=True,
        tone_consistency=True,
        terminology_consistency=True,
        date_conflicts=[],
        formatting_inconsistencies=[],
        tone_variations=[],
        terminology_conflicts=[],
        skill_redundancy=[],
        missing_cross_references=[],
        contradictory_information=[],
        recommendations=[],
    )


# Mock factory functions
def create_mock_conversation_manager(mock_database):
    """Create a mock conversation manager with database."""
    from services.conversation_manager import ConversationManager

    manager = ConversationManager()
    manager.db = mock_database
    return manager


def create_mock_section_optimizer(mock_database):
    """Create a mock section optimizer with database."""
    from services.section_optimizer import SectionOptimizer

    optimizer = SectionOptimizer()
    optimizer.db = mock_database
    return optimizer


def create_mock_job_matcher(mock_llm_provider):
    """Create a mock job matcher with LLM provider."""
    from services.job_matcher import JobMatcher

    matcher = JobMatcher(mock_llm_provider)
    return matcher


def create_mock_feedback_analyzer(mock_database):
    """Create a mock feedback analyzer with database."""
    from services.feedback_analyzer import FeedbackAnalyzer

    analyzer = FeedbackAnalyzer()
    analyzer.db = mock_database
    return analyzer


def create_mock_version_manager(mock_database):
    """Create a mock version manager with database."""
    from services.version_manager import VersionManager

    manager = VersionManager()
    manager.db = mock_database
    return manager

"""
Unit tests for JobMatcher service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.job_matcher import JobMatcher
from models.job_analysis import (
    JobAnalysis,
    SkillRequirement,
    ResumeJobMatch,
    JobMatchRecommendation,
)
from models.resume import ResumeDocument, ResumeSections
from conftest import create_mock_job_matcher


class TestJobMatcher:
    """Test cases for JobMatcher service."""

    @pytest.fixture
    def job_matcher(self, mock_llm_provider):
        """Create JobMatcher instance for testing."""
        return create_mock_job_matcher(mock_llm_provider)

    @pytest.mark.asyncio
    async def test_analyze_job_description_success(
        self, job_matcher, sample_job_description
    ):
        """Test successful job description analysis."""
        # Mock LLM calls
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=[
                "Senior Software Engineer",  # Job title
                "[]",  # Required skills (empty for fallback test)
                "[]",  # Preferred skills (empty for fallback test)
                '["Design and develop scalable applications", "Collaborate with teams"]',  # Responsibilities
            ]
        )

        # Analyze job description
        result = await job_matcher.analyze_job_description(sample_job_description)

        # Assertions
        assert result is not None
        assert isinstance(result, JobAnalysis)
        assert result.job_title == "Senior Software Engineer"
        assert result.industry == "technology"  # Should be detected from keywords
        assert len(result.required_skills) > 0  # Fallback should populate some skills
        assert len(result.technical_skills) > 0
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_analyze_job_description_llm_failure(
        self, job_matcher, sample_job_description
    ):
        """Test job description analysis with LLM failure."""
        # Mock LLM to fail
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=Exception("LLM failed")
        )

        # Should still work with fallback methods
        result = await job_matcher.analyze_job_description(sample_job_description)

        # Assertions
        assert result is not None
        assert result.job_title == "Unknown Position"  # Fallback
        assert result.industry == "technology"  # Should still detect from keywords

    @pytest.mark.asyncio
    async def test_match_resume_to_job_success(
        self, job_matcher, sample_resume_data, sample_job_analysis
    ):
        """Test successful resume to job matching."""
        # Create resume document
        resume = ResumeDocument(
            id="test-resume-123",
            user_id="test-user-456",
            sections=ResumeSections(**sample_resume_data["sections"]),
        )

        # Mock internal methods
        job_matcher._calculate_section_scores = AsyncMock(
            return_value={
                "work_experience": 0.8,
                "skills": 0.9,
                "education": 0.7,
                "projects": 0.8,
                "summary": 0.6,
            }
        )
        job_matcher._analyze_skill_matching = AsyncMock(
            return_value={
                "percentage": 0.75,
                "matching": ["Python", "JavaScript"],
                "missing_required": ["React"],
                "missing_preferred": ["Docker"],
            }
        )
        job_matcher._check_experience_match = AsyncMock(return_value=(True, 0))
        job_matcher._calculate_keyword_matching = AsyncMock(
            return_value=(0.8, ["machine learning", "kubernetes"])
        )

        # Match resume to job
        result = await job_matcher.match_resume_to_job(resume, sample_job_analysis)

        # Assertions
        assert result is not None
        assert isinstance(result, ResumeJobMatch)
        assert result.resume_id == "test-resume-123"
        assert result.job_analysis_id == sample_job_analysis.id
        assert result.overall_match_score > 0
        assert result.skill_match_percentage == 0.75
        assert "Python" in result.matching_skills
        assert "React" in result.missing_required_skills

    @pytest.mark.asyncio
    async def test_generate_section_recommendations_work_experience(
        self, job_matcher, sample_job_analysis, sample_resume_data
    ):
        """Test generating recommendations for work experience section."""
        # Mock internal method
        job_matcher._generate_experience_recommendations = AsyncMock(
            return_value=[
                JobMatchRecommendation(
                    section="work_experience",
                    type="content",
                    title="Add Python experience",
                    description="Highlight your Python development experience",
                    priority="high",
                    expected_impact=0.8,
                    specific_changes=["Add Python projects to achievements"],
                    reasoning="Job requires strong Python skills",
                )
            ]
        )

        # Generate recommendations
        recommendations = await job_matcher.generate_section_recommendations(
            section="work_experience",
            job_analysis=sample_job_analysis,
            current_content=sample_resume_data["sections"]["work_experience"],
        )

        # Assertions
        assert len(recommendations) == 1
        assert recommendations[0].section == "work_experience"
        assert recommendations[0].priority == "high"
        assert recommendations[0].expected_impact == 0.8

    @pytest.mark.asyncio
    async def test_generate_section_recommendations_skills(
        self, job_matcher, sample_job_analysis, sample_resume_data
    ):
        """Test generating recommendations for skills section."""
        # Mock internal method
        job_matcher._generate_skills_recommendations = AsyncMock(
            return_value=[
                JobMatchRecommendation(
                    section="skills",
                    type="addition",
                    title="Add missing technical skills",
                    description="Add React and Docker to your skills list",
                    priority="medium",
                    expected_impact=0.6,
                    specific_changes=[
                        "Add React to Frontend frameworks",
                        "Add Docker to Tools",
                    ],
                    reasoning="These skills are mentioned in the job requirements",
                )
            ]
        )

        # Generate recommendations
        recommendations = await job_matcher.generate_section_recommendations(
            section="skills",
            job_analysis=sample_job_analysis,
            current_content=sample_resume_data["sections"]["skills"],
        )

        # Assertions
        assert len(recommendations) == 1
        assert recommendations[0].section == "skills"
        assert recommendations[0].type == "addition"
        assert "React" in recommendations[0].description

    @pytest.mark.asyncio
    async def test_calculate_match_score(
        self, job_matcher, sample_resume_data, sample_job_analysis
    ):
        """Test calculating simple match score."""
        # Create resume document
        resume = ResumeDocument(
            id="test-resume-123",
            user_id="test-user-456",
            sections=ResumeSections(**sample_resume_data["sections"]),
        )

        # Mock match_resume_to_job
        mock_match = ResumeJobMatch(
            resume_id="test-resume-123",
            job_analysis_id=sample_job_analysis.id,
            overall_match_score=0.75,
            recommendation="good_match",
            section_scores={},
            matching_skills=[],
            missing_required_skills=[],
            missing_preferred_skills=[],
            skill_match_percentage=0.8,
            experience_match=True,
            experience_gap_years=0,
            keyword_match_score=0.7,
            missing_keywords=[],
        )
        job_matcher.match_resume_to_job = AsyncMock(return_value=mock_match)

        # Calculate match score
        score = await job_matcher.calculate_match_score(resume, sample_job_analysis)

        # Assertions
        assert score == 0.75

    @pytest.mark.asyncio
    async def test_extract_job_title_with_llm(self, job_matcher):
        """Test job title extraction using LLM."""
        job_desc = "Job Title: Senior Software Engineer\nWe are looking for..."

        # Mock LLM response
        job_matcher._call_llm_for_extraction = AsyncMock(
            return_value="Senior Software Engineer"
        )

        result = await job_matcher._extract_job_title(job_desc)

        # Assertions
        assert result == "Senior Software Engineer"

    @pytest.mark.asyncio
    async def test_extract_job_title_fallback(self, job_matcher):
        """Test job title extraction with regex fallback."""
        job_desc = "Job Title: Data Scientist\nWe are looking for..."

        # Mock LLM to fail
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=Exception("LLM failed")
        )

        result = await job_matcher._extract_job_title(job_desc)

        # Assertions
        assert result == "Data Scientist"

    @pytest.mark.asyncio
    async def test_extract_company_name(self, job_matcher):
        """Test company name extraction."""
        job_desc = "Company: TechCorp Inc.\nWe are a leading technology company..."

        result = await job_matcher._extract_company_name(job_desc)

        # Assertions
        assert result == "TechCorp Inc."

    @pytest.mark.asyncio
    async def test_identify_industry_technology(self, job_matcher):
        """Test industry identification for technology."""
        job_desc = "We are looking for a software developer with programming experience in cloud computing and DevOps."

        result = await job_matcher._identify_industry(job_desc)

        # Assertions
        assert result == "technology"

    @pytest.mark.asyncio
    async def test_identify_industry_finance(self, job_matcher):
        """Test industry identification for finance."""
        job_desc = "We are seeking a financial analyst with experience in investment banking and risk management."

        result = await job_matcher._identify_industry(job_desc)

        # Assertions
        assert result == "finance"

    @pytest.mark.asyncio
    async def test_extract_skills_with_llm(self, job_matcher):
        """Test skill extraction using LLM."""
        job_desc = "Required: Python, JavaScript, React. Preferred: Docker, Kubernetes."

        # Mock LLM response
        mock_skills_data = [
            {
                "name": "Python",
                "category": "technical",
                "proficiency_level": "advanced",
                "years_experience": 3,
                "context": "Required for backend development",
            },
            {
                "name": "JavaScript",
                "category": "technical",
                "proficiency_level": "intermediate",
                "context": "Required for frontend development",
            },
        ]
        job_matcher._call_llm_for_extraction = AsyncMock(
            return_value=str(mock_skills_data).replace("'", '"')
        )

        result = await job_matcher._extract_skills(job_desc, "required")

        # Assertions
        assert len(result) == 2
        assert result[0].name == "Python"
        assert result[0].category == "technical"
        assert result[0].importance == "required"
        assert result[1].name == "JavaScript"

    @pytest.mark.asyncio
    async def test_extract_skills_fallback(self, job_matcher):
        """Test skill extraction with fallback method."""
        job_desc = "We need someone with Python and JavaScript experience, plus knowledge of React and Docker."

        # Mock LLM to fail
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=Exception("LLM failed")
        )

        result = await job_matcher._extract_skills(job_desc, "required")

        # Assertions
        assert len(result) > 0
        skill_names = [skill.name.lower() for skill in result]
        assert "python" in skill_names
        assert "javascript" in skill_names

    def test_categorize_skills(self, job_matcher):
        """Test skill categorization."""
        skills = [
            SkillRequirement(
                name="Python", category="technical", importance="required"
            ),
            SkillRequirement(
                name="Communication", category="soft", importance="required"
            ),
            SkillRequirement(name="Git", category="tool", importance="preferred"),
            SkillRequirement(
                name="Spanish", category="language", importance="preferred"
            ),
        ]

        technical_skills = job_matcher._categorize_skills(skills, "technical")
        soft_skills = job_matcher._categorize_skills(skills, "soft")
        tools = job_matcher._categorize_skills(skills, "tool")

        # Assertions
        assert technical_skills == ["Python"]
        assert soft_skills == ["Communication"]
        assert tools == ["Git"]

    @pytest.mark.asyncio
    async def test_extract_experience_requirements_range(self, job_matcher):
        """Test extracting experience requirements with range."""
        job_desc = "We are looking for someone with 3-5 years of experience in software development."

        min_years, max_years = await job_matcher._extract_experience_requirements(
            job_desc
        )

        # Assertions
        assert min_years == 3
        assert max_years == 5

    @pytest.mark.asyncio
    async def test_extract_experience_requirements_minimum(self, job_matcher):
        """Test extracting minimum experience requirements."""
        job_desc = "Minimum 5 years of experience required."

        min_years, max_years = await job_matcher._extract_experience_requirements(
            job_desc
        )

        # Assertions
        assert min_years == 5
        assert max_years is None

    @pytest.mark.asyncio
    async def test_extract_education_requirements(self, job_matcher):
        """Test extracting education requirements."""
        job_desc = (
            "Bachelor's degree in Computer Science required. Master's degree preferred."
        )

        requirements = await job_matcher._extract_education_requirements(job_desc)

        # Assertions
        assert len(requirements) >= 1
        assert any("bachelor" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_responsibilities_with_llm(self, job_matcher):
        """Test extracting responsibilities using LLM."""
        job_desc = "Responsibilities include developing software and leading teams."

        # Mock LLM response
        mock_responsibilities = [
            "Develop and maintain software applications",
            "Lead cross-functional teams",
            "Participate in code reviews",
        ]
        job_matcher._call_llm_for_extraction = AsyncMock(
            return_value=str(mock_responsibilities).replace("'", '"')
        )

        result = await job_matcher._extract_responsibilities(job_desc)

        # Assertions
        assert len(result) == 3
        assert "Develop and maintain software applications" in result

    @pytest.mark.asyncio
    async def test_extract_responsibilities_fallback(self, job_matcher):
        """Test extracting responsibilities with fallback method."""
        job_desc = """
        Responsibilities:
        • Develop web applications
        • Collaborate with team members
        • Participate in code reviews
        """

        # Mock LLM to fail
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=Exception("LLM failed")
        )

        result = await job_matcher._extract_responsibilities(job_desc)

        # Assertions
        assert len(result) > 0
        assert any("develop" in resp.lower() for resp in result)

    @pytest.mark.asyncio
    async def test_extract_company_values(self, job_matcher):
        """Test extracting company values."""
        job_desc = "Our company values innovation, integrity, and collaboration. We are committed to excellence."

        result = await job_matcher._extract_company_values(job_desc)

        # Assertions
        assert len(result) > 0
        assert any("innovation" in value.lower() for value in result)

    @pytest.mark.asyncio
    async def test_extract_benefits(self, job_matcher):
        """Test extracting benefits."""
        job_desc = "We offer competitive salary, health insurance, and flexible work arrangements."

        result = await job_matcher._extract_benefits(job_desc)

        # Assertions
        assert len(result) > 0
        assert any("salary" in benefit.lower() for benefit in result)

    def test_extract_industry_keywords(self, job_matcher):
        """Test extracting industry-specific keywords."""
        job_desc = "We are a technology company focused on software development and digital innovation."

        result = job_matcher._extract_industry_keywords(job_desc, "technology")

        # Assertions
        assert len(result) > 0
        assert "software" in result
        assert "digital" in result

    def test_extract_action_verbs(self, job_matcher):
        """Test extracting action verbs."""
        job_desc = "You will develop applications, manage projects, and collaborate with teams."

        result = job_matcher._extract_action_verbs(job_desc)

        # Assertions
        assert "develop" in result
        assert "manage" in result
        assert "collaborate" in result

    def test_extract_buzzwords(self, job_matcher):
        """Test extracting buzzwords."""
        job_desc = "We are an innovative, fast-paced company looking for dynamic, results-driven candidates."

        result = job_matcher._extract_buzzwords(job_desc)

        # Assertions
        assert "innovative" in result
        assert "fast-paced" in result
        assert "dynamic" in result
        assert "results-driven" in result

    def test_calculate_analysis_confidence(self, job_matcher):
        """Test calculating analysis confidence score."""
        job_title = "Senior Software Engineer"
        required_skills = [
            SkillRequirement(
                name="Python", category="technical", importance="required"
            ),
            SkillRequirement(
                name="JavaScript", category="technical", importance="required"
            ),
        ]
        responsibilities = [
            "Develop web applications",
            "Lead technical discussions",
            "Mentor junior developers",
        ]

        confidence = job_matcher._calculate_analysis_confidence(
            job_title, required_skills, responsibilities
        )

        # Assertions
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably confident with good data

    def test_calculate_analysis_confidence_minimal_data(self, job_matcher):
        """Test calculating confidence with minimal data."""
        confidence = job_matcher._calculate_analysis_confidence(
            "Unknown Position", [], []
        )

        # Assertions
        assert confidence == 0.0  # No useful data extracted

    @pytest.mark.asyncio
    async def test_score_work_experience(self, job_matcher, sample_job_analysis):
        """Test scoring work experience section."""
        work_experience = [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "technologies": ["Python", "JavaScript", "React"],
                "achievements": [
                    "Developed scalable web applications using Python and React",
                    "Improved application performance by 40%",
                ],
            }
        ]

        score = await job_matcher._score_work_experience(
            work_experience, sample_job_analysis
        )

        # Assertions
        assert 0.0 <= score <= 1.0
        assert (
            score > 0.0
        )  # Should have some positive score due to matching technologies

    @pytest.mark.asyncio
    async def test_score_work_experience_empty(self, job_matcher, sample_job_analysis):
        """Test scoring empty work experience."""
        score = await job_matcher._score_work_experience([], sample_job_analysis)

        # Assertions
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_call_llm_for_extraction_success(self, job_matcher):
        """Test successful LLM call for extraction."""
        # Mock LLM provider response
        job_matcher.llm_provider.generate_response = AsyncMock(
            return_value="Test response"
        )

        result = await job_matcher._call_llm_for_extraction("Test prompt")

        # Assertions
        assert result == "Test response"
        job_matcher.llm_provider.generate_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_for_extraction_failure(self, job_matcher):
        """Test LLM call failure handling."""
        # Mock LLM provider to fail
        job_matcher.llm_provider.generate_response = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await job_matcher._call_llm_for_extraction("Test prompt")

        # Assertions
        assert result is None  # Should return None on failure

    def test_determine_recommendation_level_excellent(self, job_matcher):
        """Test recommendation level for excellent match."""
        recommendation = job_matcher._determine_recommendation_level(0.9)
        assert recommendation == "excellent_match"

    def test_determine_recommendation_level_good(self, job_matcher):
        """Test recommendation level for good match."""
        recommendation = job_matcher._determine_recommendation_level(0.75)
        assert recommendation == "good_match"

    def test_determine_recommendation_level_fair(self, job_matcher):
        """Test recommendation level for fair match."""
        recommendation = job_matcher._determine_recommendation_level(0.6)
        assert recommendation == "fair_match"

    def test_determine_recommendation_level_poor(self, job_matcher):
        """Test recommendation level for poor match."""
        recommendation = job_matcher._determine_recommendation_level(0.3)
        assert recommendation == "poor_match"

    def test_calculate_overall_match_score(self, job_matcher):
        """Test overall match score calculation."""
        section_scores = {
            "work_experience": 0.8,
            "skills": 0.9,
            "education": 0.7,
            "projects": 0.8,
            "summary": 0.6,
        }
        skill_match_percentage = 0.75
        keyword_score = 0.8
        experience_match = True

        score = job_matcher._calculate_overall_match_score(
            section_scores, skill_match_percentage, keyword_score, experience_match
        )

        # Assertions
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be a decent score with good inputs

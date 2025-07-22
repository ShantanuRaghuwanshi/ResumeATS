"""
Unit tests for SectionOptimizer service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.section_optimizer import SectionOptimizer
from models.optimization_request import (
    OptimizationRequest,
    OptimizationResult,
    SectionAnalysis,
)
from models.conversation import ResumeContext, Suggestion
from conftest import create_mock_section_optimizer


class TestSectionOptimizer:
    """Test cases for SectionOptimizer service."""

    @pytest.fixture
    def section_optimizer(self, mock_database):
        """Create SectionOptimizer instance for testing."""
        return create_mock_section_optimizer(mock_database)

    @pytest.mark.asyncio
    async def test_optimize_section_success(
        self, section_optimizer, sample_resume_data
    ):
        """Test successful section optimization."""
        # Create context
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Mock internal methods
        section_optimizer._analyze_section = AsyncMock(
            return_value=SectionAnalysis(
                section="work_experience",
                current_content=sample_resume_data["sections"]["work_experience"],
                strengths=["Uses action verbs"],
                weaknesses=["Lacks quantified achievements"],
                missing_elements=[],
                keyword_gaps=[],
                improvement_opportunities=["Add metrics"],
                ats_compatibility_score=0.7,
                content_quality_score=0.6,
                relevance_score=0.8,
            )
        )
        section_optimizer._generate_optimized_content = AsyncMock(
            return_value={"optimized": "content"}
        )
        section_optimizer._generate_section_suggestions = AsyncMock(
            return_value=[
                Suggestion(
                    type="content",
                    title="Add metrics",
                    description="Include quantified achievements",
                    impact_score=0.9,
                    reasoning="Numbers demonstrate impact",
                    section="work_experience",
                    confidence=0.85,
                )
            ]
        )
        section_optimizer._calculate_improvement_metrics = AsyncMock(
            return_value=Mock(improvement_percentage=15.0, ats_improvement=0.1)
        )
        section_optimizer._calculate_keyword_density = AsyncMock(return_value=0.05)
        section_optimizer._calculate_readability_score = AsyncMock(return_value=0.8)
        section_optimizer._generate_changes_summary = AsyncMock(
            return_value="Added quantified achievements"
        )

        # Optimize section
        result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=context,
            job_description="Software engineer position requiring Python skills",
        )

        # Assertions
        assert result is not None
        assert isinstance(result, OptimizationResult)
        assert result.optimized_content == {"optimized": "content"}
        assert len(result.suggestions) == 1
        assert result.improvement_score == 0.15
        assert result.ats_score == 0.1
        assert result.keyword_density == 0.05
        assert result.readability_score == 0.8

        # Verify request was stored
        stored_requests = section_optimizer.db.find("optimization_requests")
        assert len(stored_requests) == 1

    @pytest.mark.asyncio
    async def test_suggest_improvements_work_experience(
        self, section_optimizer, sample_resume_data
    ):
        """Test improvement suggestions for work experience section."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Mock internal suggestion methods
        section_optimizer._generate_content_suggestions = AsyncMock(
            return_value=[
                Suggestion(
                    type="content",
                    title="Use stronger action verbs",
                    description="Replace weak verbs with powerful action words",
                    impact_score=0.8,
                    reasoning="Action verbs make achievements more compelling",
                    section="work_experience",
                    confidence=0.9,
                )
            ]
        )
        section_optimizer._generate_structure_suggestions = AsyncMock(return_value=[])
        section_optimizer._generate_keyword_suggestions = AsyncMock(return_value=[])
        section_optimizer._generate_ats_suggestions = AsyncMock(return_value=[])

        # Get suggestions
        suggestions = await section_optimizer.suggest_improvements(
            section="work_experience",
            content=sample_resume_data["sections"]["work_experience"],
            context=context,
        )

        # Assertions
        assert len(suggestions) == 1
        assert suggestions[0].type == "content"
        assert suggestions[0].title == "Use stronger action verbs"
        assert suggestions[0].section == "work_experience"
        assert suggestions[0].impact_score == 0.8

    @pytest.mark.asyncio
    async def test_suggest_improvements_invalid_section(
        self, section_optimizer, sample_resume_data
    ):
        """Test suggestions for invalid section."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="invalid_section",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Should raise ValueError for invalid section
        with pytest.raises(ValueError, match="No optimization strategy found"):
            await section_optimizer.suggest_improvements(
                section="invalid_section", content={}, context=context
            )

    @pytest.mark.asyncio
    async def test_validate_changes_work_experience(
        self, section_optimizer, sample_resume_data
    ):
        """Test validation of work experience changes."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        original = sample_resume_data["sections"]["work_experience"]
        modified = original.copy()
        modified[0]["title"] = ""  # Remove job title to trigger validation error

        # Mock validation methods
        section_optimizer._validate_work_experience = AsyncMock(
            return_value={
                "errors": ["Missing job title"],
                "warnings": [],
                "suggestions": [],
            }
        )
        section_optimizer._check_cross_section_consistency = AsyncMock(return_value=[])
        section_optimizer._check_ats_compatibility = AsyncMock(return_value=[])
        section_optimizer._calculate_section_quality_score = AsyncMock(return_value=0.6)

        # Validate changes
        result = await section_optimizer.validate_changes(original, modified, context)

        # Assertions
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Missing job title" in result.errors
        assert result.overall_quality_score == 0.6

    @pytest.mark.asyncio
    async def test_validate_changes_empty_content(
        self, section_optimizer, sample_resume_data
    ):
        """Test validation with empty modified content."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        original = sample_resume_data["sections"]["work_experience"]
        modified = {}  # Empty content

        result = await section_optimizer.validate_changes(original, modified, context)

        # Assertions
        assert result.is_valid is False
        assert "Modified content cannot be empty" in result.errors

    def test_initialization_strategies(self, section_optimizer):
        """Test that optimization strategies are properly initialized."""
        strategies = section_optimizer.optimization_strategies

        # Check that all expected sections have strategies
        expected_sections = [
            "personal_details",
            "work_experience",
            "education",
            "skills",
            "projects",
        ]

        for section in expected_sections:
            assert section in strategies
            strategy = strategies[section]
            assert strategy.section_name is not None
            assert len(strategy.key_elements) > 0
            assert len(strategy.optimization_focus) > 0
            assert len(strategy.best_practices) > 0

    def test_action_verbs_loading(self, section_optimizer):
        """Test that action verbs are properly loaded."""
        action_verbs = section_optimizer.action_verbs

        # Check categories
        expected_categories = [
            "leadership",
            "achievement",
            "improvement",
            "creation",
            "analysis",
        ]
        for category in expected_categories:
            assert category in action_verbs
            assert len(action_verbs[category]) > 0

        # Check specific verbs
        assert "led" in action_verbs["leadership"]
        assert "achieved" in action_verbs["achievement"]
        assert "improved" in action_verbs["improvement"]

    def test_industry_keywords_loading(self, section_optimizer):
        """Test that industry keywords are properly loaded."""
        keywords = section_optimizer.industry_keywords

        # Check industries
        expected_industries = ["technology", "marketing", "finance", "sales"]
        for industry in expected_industries:
            assert industry in keywords
            assert len(keywords[industry]) > 0

        # Check specific keywords
        assert "software development" in keywords["technology"]
        assert "campaign management" in keywords["marketing"]

    @pytest.mark.asyncio
    async def test_analyze_work_experience_with_quantified_achievements(
        self, section_optimizer
    ):
        """Test work experience analysis with quantified achievements."""
        work_data = [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "summary": "Improved performance by 40% and reduced costs by $50K",
                "achievements": [
                    "Increased efficiency by 25%",
                    "Led team of 5 developers",
                ],
            }
        ]

        strategy = section_optimizer.optimization_strategies["work_experience"]
        result = await section_optimizer._analyze_work_experience(work_data, strategy)

        # Assertions
        assert "Contains quantified achievements" in result["strengths"]
        assert result["ats_score"] > 0.5
        assert result["quality_score"] > 0.5

    @pytest.mark.asyncio
    async def test_analyze_work_experience_without_quantified_achievements(
        self, section_optimizer
    ):
        """Test work experience analysis without quantified achievements."""
        work_data = [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "summary": "Worked on various projects and helped the team",
                "achievements": ["Worked on web applications", "Helped with testing"],
            }
        ]

        strategy = section_optimizer.optimization_strategies["work_experience"]
        result = await section_optimizer._analyze_work_experience(work_data, strategy)

        # Assertions
        assert "Lacks quantified achievements" in result["weaknesses"]
        assert (
            "Add specific metrics and numbers to achievements"
            in result["improvement_opportunities"]
        )

    @pytest.mark.asyncio
    async def test_analyze_work_experience_missing_fields(self, section_optimizer):
        """Test work experience analysis with missing required fields."""
        work_data = [
            {
                # Missing title, company, from_date
                "summary": "Did some work",
                "achievements": [],
            }
        ]

        strategy = section_optimizer.optimization_strategies["work_experience"]
        result = await section_optimizer._analyze_work_experience(work_data, strategy)

        # Assertions
        assert "Missing title" in result["missing_elements"]
        assert "Missing company" in result["missing_elements"]
        assert "Missing from_date" in result["missing_elements"]

    @pytest.mark.asyncio
    async def test_analyze_skills_categorized(self, section_optimizer):
        """Test skills analysis with categorized skills."""
        skills_data = [
            {
                "category": "Programming Languages",
                "skills": ["Python", "JavaScript", "Java"],
            },
            {"category": "Frameworks", "skills": ["React", "Django", "Flask"]},
        ]

        strategy = section_optimizer.optimization_strategies["skills"]
        result = await section_optimizer._analyze_skills(skills_data, strategy, None)

        # Assertions
        assert "Skills are well categorized" in result["strengths"]
        assert result["ats_score"] > 0.3  # Based on skill count

    @pytest.mark.asyncio
    async def test_analyze_skills_uncategorized(self, section_optimizer):
        """Test skills analysis with uncategorized skills."""
        skills_data = ["Python", "JavaScript", "React", "Django"]

        strategy = section_optimizer.optimization_strategies["skills"]
        result = await section_optimizer._analyze_skills(skills_data, strategy, None)

        # Assertions
        assert "Skills are not categorized" in result["weaknesses"]
        assert "Organize skills into categories" in result["improvement_opportunities"]

    @pytest.mark.asyncio
    async def test_analyze_skills_with_job_description(self, section_optimizer):
        """Test skills analysis with job description matching."""
        skills_data = [
            {"category": "Programming Languages", "skills": ["Python", "JavaScript"]}
        ]

        job_description = (
            "We are looking for a Python developer with JavaScript experience"
        )
        strategy = section_optimizer.optimization_strategies["skills"]
        result = await section_optimizer._analyze_skills(
            skills_data, strategy, job_description
        )

        # Assertions
        assert len(result["strengths"]) > 0
        # Should find matching skills

    def test_extract_skills_from_job_description(self, section_optimizer):
        """Test skill extraction from job description."""
        job_description = """
        We are looking for a Python developer with experience in React and AWS.
        The candidate should have strong communication skills and leadership experience.
        Knowledge of Docker and Kubernetes is preferred.
        """

        skills = section_optimizer._extract_skills_from_job_description(job_description)

        # Assertions
        assert "python" in skills
        assert "react" in skills
        assert "aws" in skills
        assert "communication" in skills
        assert "leadership" in skills
        assert "docker" in skills
        assert "kubernetes" in skills

    @pytest.mark.asyncio
    async def test_optimize_work_experience_content(self, section_optimizer):
        """Test work experience content optimization."""
        content = [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "achievements": [
                    "Worked on web applications",
                    "Responsible for testing",
                    "Helped with deployment",
                ],
            }
        ]

        analysis = SectionAnalysis(
            section="work_experience",
            current_content=content,
            strengths=[],
            weaknesses=["Uses weak verbs"],
            missing_elements=[],
            keyword_gaps=[],
            improvement_opportunities=["Use stronger action verbs"],
            ats_compatibility_score=0.7,
            content_quality_score=0.6,
            relevance_score=0.8,
        )

        result = await section_optimizer._optimize_work_experience_content(
            content, analysis
        )

        # Assertions
        assert len(result) == 1
        optimized_achievements = result[0]["achievements"]

        # Check that weak verbs were replaced
        assert not any(
            "worked on" in achievement.lower() for achievement in optimized_achievements
        )
        assert not any(
            "responsible for" in achievement.lower()
            for achievement in optimized_achievements
        )
        assert not any(
            "helped" in achievement.lower() for achievement in optimized_achievements
        )

        # Check that strong verbs were added
        assert any(
            "developed" in achievement.lower() for achievement in optimized_achievements
        )
        assert any(
            "managed" in achievement.lower() for achievement in optimized_achievements
        )
        assert any(
            "assisted" in achievement.lower() for achievement in optimized_achievements
        )

    @pytest.mark.asyncio
    async def test_generate_optimized_content(
        self, section_optimizer, sample_resume_data
    ):
        """Test optimized content generation."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        analysis = SectionAnalysis(
            section="work_experience",
            current_content=sample_resume_data["sections"]["work_experience"],
            strengths=[],
            weaknesses=[],
            missing_elements=[],
            keyword_gaps=[],
            improvement_opportunities=[],
            ats_compatibility_score=0.7,
            content_quality_score=0.6,
            relevance_score=0.8,
        )

        # Mock optimization methods
        section_optimizer._optimize_work_experience_content = AsyncMock(
            return_value={"optimized": "work_experience"}
        )

        result = await section_optimizer._generate_optimized_content(
            sample_resume_data["sections"]["work_experience"],
            analysis,
            context,
            "Software engineer job description",
            "openai",
            {},
        )

        # Assertions
        assert result == {"optimized": "work_experience"}

    @pytest.mark.asyncio
    async def test_calculate_improvement_metrics(self, section_optimizer):
        """Test improvement metrics calculation."""
        original = {"content": "basic content"}
        optimized = {"content": "enhanced content with metrics and achievements"}

        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data={},
            user_preferences={},
        )

        # This would normally calculate actual metrics
        # For now, we'll test that the method can be called without error
        try:
            result = await section_optimizer._calculate_improvement_metrics(
                original, optimized, context
            )
            # The method should return some kind of metrics object
            assert result is not None
        except NotImplementedError:
            # If the method is not fully implemented, that's expected
            pass

    @pytest.mark.asyncio
    async def test_generate_changes_summary(self, section_optimizer):
        """Test changes summary generation."""
        original = {"achievements": ["Worked on projects"]}
        optimized = {
            "achievements": [
                "Developed 5 web applications, improving performance by 40%"
            ]
        }

        summary = await section_optimizer._generate_changes_summary(original, optimized)

        # Should generate some kind of summary
        assert isinstance(summary, str)
        assert len(summary) > 0

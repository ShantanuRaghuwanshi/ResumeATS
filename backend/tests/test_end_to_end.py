"""
End-to-end tests for complete user workflows.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json


class TestEndToEndWorkflows:
    """End-to-end tests for complete user workflows."""

    @pytest.fixture
    def e2e_services(self, mock_database, mock_llm_provider):
        """Create integrated services for E2E testing."""
        from conftest import (
            create_mock_conversation_manager,
            create_mock_section_optimizer,
            create_mock_job_matcher,
            create_mock_feedback_analyzer,
            create_mock_version_manager,
        )

        services = {
            "conversation_manager": create_mock_conversation_manager(mock_database),
            "section_optimizer": create_mock_section_optimizer(mock_database),
            "job_matcher": create_mock_job_matcher(mock_llm_provider),
            "feedback_analyzer": create_mock_feedback_analyzer(mock_database),
            "version_manager": create_mock_version_manager(mock_database),
        }

        # Setup common mocks for all services
        services["conversation_manager"]._get_resume_data = AsyncMock()
        services["conversation_manager"]._get_user_preferences = AsyncMock(
            return_value={}
        )
        services["conversation_manager"]._generate_initial_message = AsyncMock(
            return_value=None
        )
        services["conversation_manager"]._generate_ai_response = AsyncMock()
        services["conversation_manager"]._apply_suggestion_to_resume = AsyncMock()

        services["section_optimizer"]._analyze_section = AsyncMock()
        services["section_optimizer"]._generate_optimized_content = AsyncMock()
        services["section_optimizer"]._generate_section_suggestions = AsyncMock(
            return_value=[]
        )
        services["section_optimizer"]._calculate_improvement_metrics = AsyncMock()
        services["section_optimizer"]._calculate_keyword_density = AsyncMock(
            return_value=0.05
        )
        services["section_optimizer"]._calculate_readability_score = AsyncMock(
            return_value=0.8
        )
        services["section_optimizer"]._generate_changes_summary = AsyncMock(
            return_value="Improvements made"
        )

        services["job_matcher"]._call_llm_for_extraction = AsyncMock()
        services["job_matcher"]._calculate_section_scores = AsyncMock()
        services["job_matcher"]._analyze_skill_matching = AsyncMock()
        services["job_matcher"]._check_experience_match = AsyncMock()
        services["job_matcher"]._calculate_keyword_matching = AsyncMock()

        services["feedback_analyzer"]._calculate_overall_impact = AsyncMock(
            return_value=0.2
        )
        services["feedback_analyzer"]._calculate_ats_impact = AsyncMock(
            return_value=0.1
        )
        services["feedback_analyzer"]._calculate_keyword_impact = AsyncMock(
            return_value=0.15
        )
        services["feedback_analyzer"]._calculate_readability_impact = AsyncMock(
            return_value=0.05
        )
        services["feedback_analyzer"]._calculate_relevance_impact = AsyncMock(
            return_value=0.1
        )
        services["feedback_analyzer"]._identify_positive_changes = AsyncMock(
            return_value=["Improvements made"]
        )
        services["feedback_analyzer"]._identify_negative_changes = AsyncMock(
            return_value=[]
        )
        services["feedback_analyzer"]._identify_neutral_changes = AsyncMock(
            return_value=[]
        )
        services["feedback_analyzer"]._generate_improvement_recommendations = AsyncMock(
            return_value=[]
        )
        services["feedback_analyzer"]._generate_change_warnings = AsyncMock(
            return_value=[]
        )

        services["version_manager"]._calculate_quality_scores = AsyncMock()
        services["version_manager"]._create_backup = AsyncMock()
        services["version_manager"]._initialize_analytics = AsyncMock()
        services["version_manager"]._update_analytics = AsyncMock()

        return services

    @pytest.mark.asyncio
    async def test_complete_resume_optimization_workflow(
        self, e2e_services, sample_resume_data, sample_job_description
    ):
        """Test complete workflow: upload resume -> analyze job -> optimize -> get feedback -> save version."""

        # Step 1: User uploads resume (simulated by having resume data)
        user_id = "test-user-456"
        resume_id = "test-resume-123"

        # Step 2: User starts conversation for work experience optimization
        conversation_manager = e2e_services["conversation_manager"]
        conversation_manager._get_resume_data.return_value = sample_resume_data

        session = await conversation_manager.start_section_conversation(
            resume_id=resume_id, user_id=user_id, section="work_experience"
        )

        assert session is not None
        assert session.section == "work_experience"

        # Step 3: User sends message asking for help
        from models.conversation import AIResponse, Suggestion

        mock_ai_response = AIResponse(
            message="I can help you improve your work experience section.",
            suggestions=[
                Suggestion(
                    type="content",
                    title="Add quantified achievements",
                    description="Include specific metrics and numbers",
                    impact_score=0.9,
                    reasoning="Numbers demonstrate impact",
                    section="work_experience",
                    confidence=0.85,
                )
            ],
        )
        conversation_manager._generate_ai_response.return_value = mock_ai_response

        ai_response = await conversation_manager.send_message(
            session_id=session.id,
            content="Help me improve my work experience section",
            role="user",
        )

        assert ai_response is not None
        assert len(ai_response.suggestions) > 0

        # Step 4: User analyzes job description
        job_matcher = e2e_services["job_matcher"]
        job_matcher._call_llm_for_extraction.side_effect = [
            "Senior Software Engineer",  # Job title
            json.dumps(
                [{"name": "Python", "category": "technical", "importance": "required"}]
            ),  # Required skills
            json.dumps(
                [{"name": "React", "category": "technical", "importance": "preferred"}]
            ),  # Preferred skills
            json.dumps(["Develop applications", "Lead teams"]),  # Responsibilities
        ]

        job_analysis = await job_matcher.analyze_job_description(sample_job_description)

        assert job_analysis is not None
        assert job_analysis.job_title == "Senior Software Engineer"
        assert len(job_analysis.required_skills) > 0

        # Step 5: User optimizes section based on job analysis
        section_optimizer = e2e_services["section_optimizer"]

        from models.optimization_request import SectionAnalysis

        mock_analysis = SectionAnalysis(
            section="work_experience",
            current_content=sample_resume_data["sections"]["work_experience"],
            strengths=["Uses action verbs"],
            weaknesses=["Lacks quantified achievements"],
            missing_elements=[],
            keyword_gaps=["Python", "React"],
            improvement_opportunities=["Add metrics", "Include job-relevant keywords"],
            ats_compatibility_score=0.7,
            content_quality_score=0.6,
            relevance_score=0.8,
        )
        section_optimizer._analyze_section.return_value = mock_analysis

        optimized_content = {
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "achievements": [
                        "Developed 5 Python web applications, improving performance by 40%",
                        "Led team of 3 developers using React and modern frameworks",
                    ],
                    "technologies": ["Python", "React", "JavaScript", "AWS"],
                }
            ]
        }
        section_optimizer._generate_optimized_content.return_value = optimized_content

        mock_metrics = Mock()
        mock_metrics.improvement_percentage = 25.0
        mock_metrics.ats_improvement = 0.15
        section_optimizer._calculate_improvement_metrics.return_value = mock_metrics

        optimization_result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=session.context,
            job_description=sample_job_description,
        )

        assert optimization_result is not None
        assert optimization_result.optimized_content == optimized_content
        assert optimization_result.improvement_score == 0.25

        # Step 6: User gets feedback on changes
        feedback_analyzer = e2e_services["feedback_analyzer"]

        change_analysis = await feedback_analyzer.analyze_change_impact(
            before=sample_resume_data["sections"]["work_experience"],
            after=optimized_content["work_experience"],
            context=session.context,
        )

        assert change_analysis is not None
        assert change_analysis.overall_impact > 0
        assert "Improvements made" in change_analysis.positive_changes

        # Step 7: User saves optimized version
        version_manager = e2e_services["version_manager"]
        version_manager._calculate_quality_scores.return_value = {
            "overall_score": 0.85,
            "ats_score": 0.90,
            "keyword_score": 0.80,
        }

        # Create updated resume data
        updated_resume_data = sample_resume_data.copy()
        updated_resume_data["sections"]["work_experience"] = optimized_content[
            "work_experience"
        ]

        new_version = await version_manager.create_version(
            user_id=user_id,
            resume_data=updated_resume_data,
            name="Optimized for Senior Software Engineer",
            description="Optimized based on job analysis and AI suggestions",
            job_target="Senior Software Engineer",
        )

        assert new_version is not None
        assert new_version.name == "Optimized for Senior Software Engineer"
        assert new_version.overall_score == 0.85

        # Step 8: User applies suggestion from conversation
        conversation_manager._apply_suggestion_to_resume.return_value = {
            "section": "work_experience",
            "suggestion_applied": "Add quantified achievements",
            "updated_content": optimized_content["work_experience"],
        }

        suggestion_result = await conversation_manager.apply_suggestion(
            session_id=session.id, suggestion_id=ai_response.suggestions[0].id
        )

        assert suggestion_result["success"] is True
        assert suggestion_result["suggestion_applied"] == "Add quantified achievements"

        # Verify complete workflow success
        assert session.section == "work_experience"
        assert job_analysis.job_title == "Senior Software Engineer"
        assert optimization_result.improvement_score > 0
        assert change_analysis.overall_impact > 0
        assert new_version.overall_score > 0.8

    @pytest.mark.asyncio
    async def test_multi_section_optimization_workflow(
        self, e2e_services, sample_resume_data
    ):
        """Test workflow optimizing multiple resume sections."""

        user_id = "test-user-456"
        resume_id = "test-resume-123"
        sections_to_optimize = ["work_experience", "skills", "projects"]

        conversation_manager = e2e_services["conversation_manager"]
        section_optimizer = e2e_services["section_optimizer"]
        feedback_analyzer = e2e_services["feedback_analyzer"]

        conversation_manager._get_resume_data.return_value = sample_resume_data

        optimization_results = {}
        feedback_results = {}

        # Optimize each section
        for section in sections_to_optimize:
            # Start conversation for section
            session = await conversation_manager.start_section_conversation(
                resume_id=resume_id, user_id=user_id, section=section
            )

            assert session.section == section

            # Mock section-specific optimization
            from models.optimization_request import SectionAnalysis

            mock_analysis = SectionAnalysis(
                section=section,
                current_content=sample_resume_data["sections"][section],
                strengths=[f"Good {section} content"],
                weaknesses=[f"Could improve {section}"],
                missing_elements=[],
                keyword_gaps=[],
                improvement_opportunities=[f"Enhance {section}"],
                ats_compatibility_score=0.7,
                content_quality_score=0.6,
                relevance_score=0.8,
            )
            section_optimizer._analyze_section.return_value = mock_analysis

            optimized_content = {f"optimized_{section}": f"Enhanced {section} content"}
            section_optimizer._generate_optimized_content.return_value = (
                optimized_content
            )

            mock_metrics = Mock()
            mock_metrics.improvement_percentage = 20.0
            mock_metrics.ats_improvement = 0.1
            section_optimizer._calculate_improvement_metrics.return_value = mock_metrics

            # Optimize section
            result = await section_optimizer.optimize_section(
                section_data=sample_resume_data["sections"][section],
                context=session.context,
            )

            optimization_results[section] = result

            # Get feedback for section
            feedback = await feedback_analyzer.analyze_change_impact(
                before=sample_resume_data["sections"][section],
                after=optimized_content,
                context=session.context,
            )

            feedback_results[section] = feedback

        # Verify all sections were optimized
        assert len(optimization_results) == 3
        assert len(feedback_results) == 3

        for section in sections_to_optimize:
            assert optimization_results[section] is not None
            assert optimization_results[section].improvement_score > 0
            assert feedback_results[section] is not None
            assert feedback_results[section].overall_impact > 0

    @pytest.mark.asyncio
    async def test_version_comparison_and_rollback_workflow(
        self, e2e_services, sample_resume_data
    ):
        """Test workflow for version comparison and rollback."""

        user_id = "test-user-456"
        version_manager = e2e_services["version_manager"]

        # Create original version
        version_manager._calculate_quality_scores.return_value = {
            "overall_score": 0.70,
            "ats_score": 0.75,
            "keyword_score": 0.65,
        }

        original_version = await version_manager.create_version(
            user_id=user_id, resume_data=sample_resume_data, name="Original Resume"
        )

        # Create modified version with changes
        modified_data = sample_resume_data.copy()
        modified_data["sections"]["work_experience"][0]["achievements"].append(
            "Led major project resulting in 50% efficiency improvement"
        )

        version_manager._calculate_quality_scores.return_value = {
            "overall_score": 0.85,
            "ats_score": 0.90,
            "keyword_score": 0.80,
        }

        modified_version = await version_manager.create_version(
            user_id=user_id, resume_data=modified_data, name="Enhanced Resume"
        )

        # Compare versions
        version_manager._calculate_similarity.return_value = 0.85
        version_manager._calculate_section_differences.return_value = {
            "work_experience": {"changed": True, "similarity": 0.9},
            "skills": {"changed": False, "similarity": 1.0},
        }
        version_manager._analyze_changes.return_value = {
            "additions": ["Added achievement with metrics"],
            "deletions": [],
            "modifications": [],
            "content_changes": {"work_experience": {"added": "efficiency improvement"}},
            "formatting_changes": [],
            "structural_changes": [],
        }
        version_manager._generate_comparison_recommendations.return_value = {
            "improvements": ["Added quantified achievement"],
            "regressions": [],
            "neutral_changes": [],
            "merge_suggestions": [],
            "rollback_recommendations": [],
        }

        comparison = await version_manager.compare_versions(
            original_version.id, modified_version.id, user_id
        )

        assert comparison is not None
        assert comparison.quality_difference == 0.15  # 0.85 - 0.70
        assert "Added achievement with metrics" in comparison.additions

        # Simulate user deciding to rollback to original
        version_manager.list_versions = AsyncMock(return_value=[modified_version])
        version_manager.create_version = AsyncMock(
            return_value=Mock(
                id="restored-version-id",
                name="Original Resume (Restored)",
                is_current=True,
            )
        )
        version_manager.update_version = AsyncMock()

        restored_version = await version_manager.restore_version(
            original_version.id, user_id
        )

        assert restored_version is not None
        assert "(Restored)" in restored_version.name
        assert restored_version.is_current is True

    @pytest.mark.asyncio
    async def test_job_targeted_optimization_workflow(
        self, e2e_services, sample_resume_data, sample_job_description
    ):
        """Test complete workflow for job-targeted resume optimization."""

        user_id = "test-user-456"
        resume_id = "test-resume-123"

        job_matcher = e2e_services["job_matcher"]
        section_optimizer = e2e_services["section_optimizer"]
        version_manager = e2e_services["version_manager"]

        # Step 1: Analyze job description
        job_matcher._call_llm_for_extraction.side_effect = [
            "Senior Software Engineer",
            json.dumps(
                [
                    {
                        "name": "Python",
                        "category": "technical",
                        "importance": "required",
                        "years_experience": 5,
                    },
                    {
                        "name": "React",
                        "category": "technical",
                        "importance": "required",
                        "years_experience": 3,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "name": "Docker",
                        "category": "technical",
                        "importance": "preferred",
                    },
                    {"name": "AWS", "category": "technical", "importance": "preferred"},
                ]
            ),
            json.dumps(
                [
                    "Design and develop scalable web applications",
                    "Lead technical discussions and mentor junior developers",
                    "Collaborate with cross-functional teams",
                ]
            ),
        ]

        job_analysis = await job_matcher.analyze_job_description(sample_job_description)

        # Step 2: Match current resume to job
        from models.resume import ResumeDocument, ResumeSections

        resume = ResumeDocument(
            id=resume_id,
            user_id=user_id,
            sections=ResumeSections(**sample_resume_data["sections"]),
        )

        job_matcher._calculate_section_scores.return_value = {
            "work_experience": 0.7,
            "skills": 0.6,
            "education": 0.8,
            "projects": 0.7,
            "summary": 0.5,
        }
        job_matcher._analyze_skill_matching.return_value = {
            "percentage": 0.6,
            "matching": ["Python", "JavaScript"],
            "missing_required": ["React"],
            "missing_preferred": ["Docker", "AWS"],
        }
        job_matcher._check_experience_match.return_value = (True, 0)
        job_matcher._calculate_keyword_matching.return_value = (
            0.65,
            ["scalable", "web applications"],
        )

        match_result = await job_matcher.match_resume_to_job(resume, job_analysis)

        assert match_result.skill_match_percentage == 0.6
        assert "React" in match_result.missing_required_skills

        # Step 3: Generate section-specific recommendations
        job_matcher._generate_experience_recommendations = AsyncMock(
            return_value=[
                Mock(
                    section="work_experience",
                    title="Highlight React experience",
                    description="Emphasize React projects and achievements",
                    priority="high",
                    expected_impact=0.8,
                )
            ]
        )
        job_matcher._generate_skills_recommendations = AsyncMock(
            return_value=[
                Mock(
                    section="skills",
                    title="Add missing technical skills",
                    description="Include React, Docker, and AWS in skills section",
                    priority="high",
                    expected_impact=0.7,
                )
            ]
        )

        work_exp_recommendations = await job_matcher.generate_section_recommendations(
            "work_experience",
            job_analysis,
            sample_resume_data["sections"]["work_experience"],
        )
        skills_recommendations = await job_matcher.generate_section_recommendations(
            "skills", job_analysis, sample_resume_data["sections"]["skills"]
        )

        assert len(work_exp_recommendations) > 0
        assert len(skills_recommendations) > 0

        # Step 4: Apply job-targeted optimizations
        from models.conversation import ResumeContext

        context = ResumeContext(
            resume_id=resume_id,
            user_id=user_id,
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Mock job-targeted optimization
        from models.optimization_request import SectionAnalysis

        job_targeted_analysis = SectionAnalysis(
            section="work_experience",
            current_content=sample_resume_data["sections"]["work_experience"],
            strengths=["Relevant experience"],
            weaknesses=["Missing React emphasis"],
            missing_elements=[],
            keyword_gaps=["React", "scalable", "web applications"],
            improvement_opportunities=[
                "Highlight React projects",
                "Add scalability achievements",
            ],
            ats_compatibility_score=0.7,
            content_quality_score=0.6,
            relevance_score=0.9,  # Higher relevance due to job targeting
        )
        section_optimizer._analyze_section.return_value = job_targeted_analysis

        job_optimized_content = {
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "achievements": [
                        "Developed 5 scalable web applications using Python and React, serving 10K+ users",
                        "Led technical discussions and mentored 3 junior developers",
                        "Collaborated with cross-functional teams to deliver projects 20% faster",
                    ],
                    "technologies": ["Python", "React", "JavaScript", "Docker", "AWS"],
                }
            ]
        }
        section_optimizer._generate_optimized_content.return_value = (
            job_optimized_content
        )

        mock_metrics = Mock()
        mock_metrics.improvement_percentage = (
            35.0  # Higher improvement due to job targeting
        )
        mock_metrics.ats_improvement = 0.2
        section_optimizer._calculate_improvement_metrics.return_value = mock_metrics

        optimization_result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=context,
            job_description=sample_job_description,
            optimization_type="job_specific",
        )

        assert optimization_result.improvement_score == 0.35

        # Step 5: Save job-targeted version
        version_manager._calculate_quality_scores.return_value = {
            "overall_score": 0.90,  # Higher score due to job targeting
            "ats_score": 0.95,
            "keyword_score": 0.85,
        }

        job_targeted_resume_data = sample_resume_data.copy()
        job_targeted_resume_data["sections"]["work_experience"] = job_optimized_content[
            "work_experience"
        ]

        job_targeted_version = await version_manager.create_version(
            user_id=user_id,
            resume_data=job_targeted_resume_data,
            name=f"Optimized for {job_analysis.job_title}",
            description=f"Resume optimized for {job_analysis.job_title} position",
            job_target=job_analysis.job_title,
            optimization_type="job_specific",
            tags=["job-targeted", "senior-engineer"],
        )

        assert job_targeted_version.job_target == "Senior Software Engineer"
        assert job_targeted_version.overall_score == 0.90
        assert "job-targeted" in job_targeted_version.tags

        # Verify complete job-targeted workflow
        assert job_analysis.job_title == "Senior Software Engineer"
        assert match_result.overall_match_score > 0
        assert optimization_result.improvement_score > 0.3
        assert job_targeted_version.overall_score > 0.85

    @pytest.mark.asyncio
    async def test_real_time_feedback_workflow(self, e2e_services, sample_resume_data):
        """Test real-time feedback during live editing."""

        user_id = "test-user-456"
        session_id = "test-session-123"

        feedback_analyzer = e2e_services["feedback_analyzer"]

        # Mock real-time feedback methods
        feedback_analyzer._calculate_readability_score = AsyncMock(return_value=0.8)
        feedback_analyzer._calculate_keyword_density = AsyncMock(
            return_value={"python": 0.1, "javascript": 0.08, "react": 0.06}
        )
        feedback_analyzer._identify_grammar_issues = AsyncMock(return_value=[])
        feedback_analyzer._generate_style_suggestions = AsyncMock(
            return_value=["Use more active voice", "Add specific metrics"]
        )
        feedback_analyzer._generate_keyword_suggestions = AsyncMock(
            return_value=["Include more technical keywords", "Add industry buzzwords"]
        )
        feedback_analyzer._calculate_content_quality_score = AsyncMock(
            side_effect=[0.85, 0.70]  # Current, then previous
        )
        feedback_analyzer._calculate_ats_score = AsyncMock(return_value=0.90)

        # Simulate user typing in real-time
        typing_stages = [
            "Worked on web development",
            "Worked on web development projects",
            "Worked on web development projects using Python",
            "Developed web applications using Python and JavaScript",
            "Developed 5 web applications using Python and JavaScript, improving performance by 30%",
        ]

        feedback_history = []

        for i, content in enumerate(typing_stages):
            previous_content = typing_stages[i - 1] if i > 0 else None

            feedback = await feedback_analyzer.generate_real_time_feedback(
                session_id=session_id,
                section="work_experience",
                current_content=content,
                previous_content=previous_content,
            )

            feedback_history.append(feedback)

            assert feedback.session_id == session_id
            assert feedback.section == "work_experience"
            assert feedback.character_count == len(content)
            assert feedback.word_count == len(content.split())

        # Verify feedback progression
        assert len(feedback_history) == 5

        # Last feedback should show improvement
        final_feedback = feedback_history[-1]
        assert final_feedback.current_quality_score == 0.85
        assert final_feedback.improvement_since_last == 0.15  # 0.85 - 0.70
        assert final_feedback.ats_compatibility == 0.90

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, e2e_services, sample_resume_data):
        """Test error recovery in workflows."""

        user_id = "test-user-456"
        resume_id = "test-resume-123"

        conversation_manager = e2e_services["conversation_manager"]
        section_optimizer = e2e_services["section_optimizer"]

        # Test conversation manager error recovery
        conversation_manager._get_resume_data.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await conversation_manager.start_section_conversation(
                resume_id=resume_id, user_id=user_id, section="work_experience"
            )

        # Reset and test successful recovery
        conversation_manager._get_resume_data.side_effect = None
        conversation_manager._get_resume_data.return_value = sample_resume_data

        session = await conversation_manager.start_section_conversation(
            resume_id=resume_id, user_id=user_id, section="work_experience"
        )

        assert session is not None

        # Test section optimizer error recovery
        section_optimizer._analyze_section.side_effect = Exception("Analysis error")

        with pytest.raises(Exception):
            await section_optimizer.optimize_section(
                section_data=sample_resume_data["sections"]["work_experience"],
                context=session.context,
            )

        # Reset and test successful recovery
        section_optimizer._analyze_section.side_effect = None
        from models.optimization_request import SectionAnalysis

        section_optimizer._analyze_section.return_value = SectionAnalysis(
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
        section_optimizer._generate_optimized_content.return_value = {
            "recovered": "content"
        }

        mock_metrics = Mock()
        mock_metrics.improvement_percentage = 10.0
        mock_metrics.ats_improvement = 0.05
        section_optimizer._calculate_improvement_metrics.return_value = mock_metrics

        result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=session.context,
        )

        assert result is not None
        assert result.optimized_content == {"recovered": "content"}

    @pytest.mark.asyncio
    async def test_performance_workflow(self, e2e_services, sample_resume_data):
        """Test workflow performance with timing measurements."""
        import time

        user_id = "test-user-456"
        resume_id = "test-resume-123"

        conversation_manager = e2e_services["conversation_manager"]
        section_optimizer = e2e_services["section_optimizer"]

        conversation_manager._get_resume_data.return_value = sample_resume_data

        # Measure conversation start time
        start_time = time.time()
        session = await conversation_manager.start_section_conversation(
            resume_id=resume_id, user_id=user_id, section="work_experience"
        )
        conversation_time = time.time() - start_time

        # Measure optimization time
        from models.optimization_request import SectionAnalysis

        section_optimizer._analyze_section.return_value = SectionAnalysis(
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
        section_optimizer._generate_optimized_content.return_value = {
            "optimized": "content"
        }

        mock_metrics = Mock()
        mock_metrics.improvement_percentage = 15.0
        mock_metrics.ats_improvement = 0.1
        section_optimizer._calculate_improvement_metrics.return_value = mock_metrics

        start_time = time.time()
        result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=session.context,
        )
        optimization_time = time.time() - start_time

        # Verify performance (these are mock operations, so they should be fast)
        assert conversation_time < 1.0  # Should complete within 1 second
        assert optimization_time < 1.0  # Should complete within 1 second

        # Verify functionality still works
        assert session is not None
        assert result is not None

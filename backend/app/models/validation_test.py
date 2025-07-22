"""
Validation tests for all new data models
"""

from datetime import datetime
from typing import Dict, Any
import json

# Import all models
from .conversation import (
    ResumeContext,
    Suggestion,
    Message,
    ConversationSession,
    AIResponse,
    ConversationSummary,
)
from .optimization_request import (
    OptimizationRequest,
    OptimizationResult,
    SectionAnalysis,
    ImprovementMetrics,
    ValidationResult,
)
from .job_analysis import (
    JobDescription,
    SkillRequirement,
    JobAnalysis,
    ResumeJobMatch,
    JobMatchRecommendation,
    JobComparisonResult,
)
from .feedback import (
    FeedbackItem,
    ATSCompatibilityResult,
    ConsistencyReport,
    ChangeImpactAnalysis,
    RealTimeFeedback,
    UserFeedback,
)
from .resume_version import (
    ResumeVersion,
    VersionComparison,
    VersionHistory,
    VersionTemplate,
    VersionBackup,
    VersionAnalytics,
)
from .user_preferences import (
    UserPreference,
    SuggestionFeedback,
    UserProfile,
    LearningInsight,
    PersonalizationSettings,
)
from .resume import (
    EducationEntry,
    WorkProject,
    WorkExperienceEntry,
    ProjectEntry,
    SkillCategory,
    PersonalDetails,
    CertificationEntry,
    LanguageEntry,
    ResumeMetadata,
    ResumeSections,
    ResumeDocument,
)


def test_conversation_models():
    """Test conversation-related models"""
    print("Testing conversation models...")

    # Test ResumeContext
    context = ResumeContext(
        resume_id="test-resume-1",
        user_id="test-user-1",
        current_section="work_experience",
        full_resume_data={"test": "data"},
        job_description="Software Engineer position",
        optimization_goals=["ats_friendly", "keyword_optimization"],
    )

    # Test Suggestion
    suggestion = Suggestion(
        type="content",
        title="Improve action verbs",
        description="Use stronger action verbs to describe achievements",
        original_text="Worked on projects",
        suggested_text="Led cross-functional projects",
        impact_score=0.8,
        reasoning="Action verbs create stronger impact",
        section="work_experience",
        confidence=0.9,
    )

    # Test Message
    message = Message(
        session_id="session-1",
        role="assistant",
        content="I can help you improve your work experience section.",
        suggestions=[suggestion],
    )

    # Test ConversationSession
    session = ConversationSession(
        resume_id="test-resume-1",
        user_id="test-user-1",
        section="work_experience",
        title="Work Experience Optimization",
        context=context,
        messages=[message],
    )

    print("✅ Conversation models validated successfully")
    return True


def test_optimization_models():
    """Test optimization-related models"""
    print("Testing optimization models...")

    # Test OptimizationRequest
    request = OptimizationRequest(
        resume_id="test-resume-1",
        user_id="test-user-1",
        section="work_experience",
        content={"title": "Software Developer", "company": "Tech Corp"},
        job_description="Senior Software Engineer role",
        optimization_type="job_specific",
        target_industry="technology",
        experience_level="mid",
    )

    # Test SectionAnalysis
    analysis = SectionAnalysis(
        section="work_experience",
        current_content={"title": "Developer"},
        strengths=["Technical skills mentioned"],
        weaknesses=["Lacks quantifiable achievements"],
        missing_elements=["Leadership experience"],
        keyword_gaps=["agile", "scrum"],
        improvement_opportunities=["Add metrics and numbers"],
        ats_compatibility_score=0.7,
        content_quality_score=0.6,
        relevance_score=0.8,
    )

    print("✅ Optimization models validated successfully")
    return True


def test_job_analysis_models():
    """Test job analysis models"""
    print("Testing job analysis models...")

    # Test SkillRequirement
    skill = SkillRequirement(
        name="Python",
        category="technical",
        importance="required",
        proficiency_level="advanced",
        years_experience=3,
        context="Backend development",
    )

    # Test JobDescription
    job_desc = JobDescription(
        raw_text="Software Engineer position requiring Python and React skills...",
        job_title="Software Engineer",
        company="Tech Company",
        location="San Francisco, CA",
        employment_type="full-time",
        experience_level="mid",
    )

    # Test JobAnalysis
    job_analysis = JobAnalysis(
        job_description_id=job_desc.id,
        job_title="Software Engineer",
        company="Tech Company",
        industry="technology",
        required_skills=[skill],
        technical_skills=["Python", "React", "SQL"],
        soft_skills=["Communication", "Teamwork"],
        min_years_experience=2,
        max_years_experience=5,
        key_responsibilities=["Develop web applications", "Code reviews"],
        confidence_score=0.9,
    )

    print("✅ Job analysis models validated successfully")
    return True


def test_feedback_models():
    """Test feedback models"""
    print("Testing feedback models...")

    # Test FeedbackItem
    feedback = FeedbackItem(
        type="warning",
        category="ats",
        title="ATS Compatibility Issue",
        message="Complex formatting may not parse correctly",
        section="work_experience",
        severity="medium",
        actionable=True,
        auto_fixable=False,
        fix_suggestion="Simplify formatting and use standard bullet points",
    )

    # Test ATSCompatibilityResult
    ats_result = ATSCompatibilityResult(
        overall_score=0.8,
        parsing_score=0.9,
        formatting_score=0.7,
        keyword_score=0.8,
        structure_score=0.8,
        formatting_issues=["Complex tables detected"],
        recommendations=["Use simple bullet points", "Avoid graphics"],
    )

    print("✅ Feedback models validated successfully")
    return True


def test_version_models():
    """Test version management models"""
    print("Testing version models...")

    # Test ResumeVersion
    version = ResumeVersion(
        user_id="test-user-1",
        name="Software Engineer Resume v1",
        description="Optimized for tech companies",
        resume_data={"personal_details": {"name": "John Doe"}},
        version_number=1,
        is_current=True,
        job_target="Software Engineer",
        target_industry="technology",
        overall_score=0.85,
        ats_score=0.8,
        keyword_score=0.9,
        tags=["tech", "backend", "python"],
    )

    print("✅ Version models validated successfully")
    return True


def test_user_preference_models():
    """Test user preference models"""
    print("Testing user preference models...")

    # Test UserPreference
    preference = UserPreference(
        user_id="test-user-1",
        category="writing_style",
        preference_key="tone",
        preference_value="professional",
        confidence=0.8,
        source="explicit",
    )

    # Test UserProfile
    profile = UserProfile(
        user_id="test-user-1",
        industry="technology",
        experience_level="mid",
        job_titles=["Software Developer", "Backend Engineer"],
        target_roles=["Senior Software Engineer", "Tech Lead"],
        writing_style="technical",
        optimization_focus=["ats", "keywords"],
        suggestion_acceptance_rate=0.75,
    )

    print("✅ User preference models validated successfully")
    return True


def test_enhanced_resume_models():
    """Test enhanced resume models"""
    print("Testing enhanced resume models...")

    # Test enhanced PersonalDetails
    personal = PersonalDetails(
        name="John Doe",
        email="john.doe@email.com",
        phone="+1-555-0123",
        linkedin="linkedin.com/in/johndoe",
        github="github.com/johndoe",
        portfolio="johndoe.dev",
        summary="Experienced software engineer with 5+ years in backend development",
    )

    # Test SkillCategory
    skills = SkillCategory(
        category="Programming Languages",
        skills=["Python", "JavaScript", "Java"],
        proficiency_levels={
            "Python": "Expert",
            "JavaScript": "Advanced",
            "Java": "Intermediate",
        },
    )

    # Test enhanced WorkExperienceEntry
    work_exp = WorkExperienceEntry(
        title="Senior Software Engineer",
        company="Tech Corp",
        location="San Francisco, CA",
        from_date="2020-01",
        to_date="2023-12",
        summary="Led backend development for high-traffic web applications",
        achievements=["Improved API performance by 40%", "Led team of 5 developers"],
        technologies=["Python", "Django", "PostgreSQL", "AWS"],
        metrics={"performance_improvement": "40%", "team_size": "5"},
        is_current=False,
    )

    print("✅ Enhanced resume models validated successfully")
    return True


def run_all_validation_tests():
    """Run all model validation tests"""
    print("🧪 Starting model validation tests...\n")

    tests = [
        ("Conversation Models", test_conversation_models),
        ("Optimization Models", test_optimization_models),
        ("Job Analysis Models", test_job_analysis_models),
        ("Feedback Models", test_feedback_models),
        ("Version Models", test_version_models),
        ("User Preference Models", test_user_preference_models),
        ("Enhanced Resume Models", test_enhanced_resume_models),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"🔍 {test_name}:")
            test_func()
            passed += 1
            print()
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            failed += 1
            print()

    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All model validation tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    run_all_validation_tests()

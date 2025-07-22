#!/usr/bin/env python3
"""
Test script for FeedbackAnalyzer service
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.feedback_analyzer import FeedbackAnalyzer
from models.conversation import ResumeContext


async def test_feedback_analyzer():
    """Test the FeedbackAnalyzer service"""

    print("Testing FeedbackAnalyzer service...")

    # Initialize the service
    analyzer = FeedbackAnalyzer()

    # Test data
    resume_context = ResumeContext(
        resume_id="test-resume-1",
        user_id="test-user-1",
        current_section="work_experience",
        full_resume_data={
            "work_experience": [
                {
                    "title": "Software Engineer",
                    "company": "Tech Corp",
                    "from_date": "2022",
                    "to_date": "present",
                    "summary": "Worked on various projects and helped the team.",
                }
            ]
        },
    )

    before_content = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "summary": "Worked on various projects and helped the team.",
    }

    after_content = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "summary": "Led development of 3 major projects, improving system performance by 40% and reducing deployment time by 60%.",
    }

    try:
        # Test 1: Change Impact Analysis
        print("\n1. Testing change impact analysis...")
        impact_analysis = await analyzer.analyze_change_impact(
            before_content, after_content, resume_context
        )
        print(f"✓ Change type: {impact_analysis.change_type}")
        print(f"✓ Overall impact: {impact_analysis.overall_impact:.2f}")
        print(f"✓ Positive changes: {len(impact_analysis.positive_changes)}")
        print(f"✓ Negative changes: {len(impact_analysis.negative_changes)}")

        # Test 2: ATS Compatibility Check
        print("\n2. Testing ATS compatibility check...")
        ats_result = await analyzer.check_ats_compatibility(
            after_content, "work_experience"
        )
        print(f"✓ Overall ATS score: {ats_result.overall_score:.2f}")
        print(f"✓ Parsing score: {ats_result.parsing_score:.2f}")
        print(f"✓ Formatting score: {ats_result.formatting_score:.2f}")
        print(
            f"✓ Issues found: {len(ats_result.formatting_issues + ats_result.parsing_issues)}"
        )

        # Test 3: Consistency Validation
        print("\n3. Testing consistency validation...")
        full_resume = {
            "work_experience": [after_content],
            "skills": ["Python", "JavaScript", "React"],
            "education": [{"degree": "Bachelor of Science", "year": "2020"}],
        }
        consistency_report = await analyzer.validate_consistency(full_resume)
        print(
            f"✓ Overall consistency score: {consistency_report.overall_consistency_score:.2f}"
        )
        print(f"✓ Date consistency: {consistency_report.date_consistency}")
        print(f"✓ Formatting consistency: {consistency_report.formatting_consistency}")

        # Test 4: Real-time Feedback
        print("\n4. Testing real-time feedback...")
        feedback = await analyzer.generate_real_time_feedback(
            session_id="test-session-1",
            section="work_experience",
            current_content="Led development of 3 major projects, improving system performance by 40%",
            previous_content="Worked on various projects",
        )
        print(f"✓ Character count: {feedback.character_count}")
        print(f"✓ Word count: {feedback.word_count}")
        print(f"✓ Quality score: {feedback.current_quality_score:.2f}")
        print(f"✓ ATS compatibility: {feedback.ats_compatibility:.2f}")
        print(f"✓ Grammar issues: {len(feedback.grammar_issues)}")
        print(f"✓ Style suggestions: {len(feedback.style_suggestions)}")

        print("\n✅ All tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_feedback_analyzer())

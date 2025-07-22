"""
Test script for SectionOptimizer service
"""

import asyncio
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.section_optimizer import SectionOptimizer
from models.conversation import ResumeContext
from database import get_database


async def test_section_optimizer():
    """Test the SectionOptimizer functionality"""

    print("🧪 Testing SectionOptimizer Service...\n")

    # Initialize optimizer
    optimizer = SectionOptimizer()

    # Test data
    user_id = "test-user-optimizer"
    resume_id = "test-resume-optimizer"

    # Mock resume context
    context = ResumeContext(
        resume_id=resume_id,
        user_id=user_id,
        current_section="work_experience",
        full_resume_data={
            "personal_details": {"name": "John Doe", "email": "john@example.com"},
            "work_experience": [
                {
                    "title": "Software Developer",
                    "company": "Tech Corp",
                    "from_date": "2020-01",
                    "to_date": "2023-12",
                    "summary": "Worked on web applications",
                    "achievements": [
                        "Helped improve system performance",
                        "Worked on new features",
                    ],
                }
            ],
        },
    )

    try:
        # Test 1: Optimize work experience section
        print("1️⃣ Testing section optimization...")
        work_experience_data = [
            {
                "title": "Software Developer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "to_date": "2023-12",
                "summary": "Worked on web applications",
                "achievements": [
                    "Helped improve system performance",
                    "Worked on new features",
                ],
            }
        ]

        optimization_result = await optimizer.optimize_section(
            section_data=work_experience_data,
            context=context,
            job_description="Senior Software Engineer position requiring Python and React skills",
            optimization_type="job_specific",
        )

        print(f"✅ Section optimization completed")
        print(f"   Improvement Score: {optimization_result.improvement_score:.2f}")
        print(f"   ATS Score: {optimization_result.ats_score:.2f}")
        print(f"   Suggestions: {len(optimization_result.suggestions)}")
        print(f"   Changes: {optimization_result.changes_summary}")
        print()

        # Test 2: Generate improvement suggestions
        print("2️⃣ Testing improvement suggestions...")
        suggestions = await optimizer.suggest_improvements(
            section="work_experience",
            content=work_experience_data,
            context=context,
            focus_areas=["quantified_achievements", "action_verbs"],
        )

        print(f"✅ Generated {len(suggestions)} suggestions")
        for i, suggestion in enumerate(suggestions[:3]):  # Show top 3
            print(
                f"   {i+1}. {suggestion.title} (Impact: {suggestion.impact_score:.1f})"
            )
            print(f"      {suggestion.description}")
        print()

        # Test 3: Validate changes
        print("3️⃣ Testing change validation...")
        modified_data = [
            {
                "title": "Senior Software Developer",  # Modified title
                "company": "Tech Corp",
                "from_date": "2020-01",
                "to_date": "2023-12",
                "summary": "Led development of web applications",  # Enhanced summary
                "achievements": [
                    "Improved system performance by 40%",  # Quantified
                    "Developed 5 new features that increased user engagement",  # Enhanced
                ],
            }
        ]

        validation_result = await optimizer.validate_changes(
            original=work_experience_data, modified=modified_data, context=context
        )

        print(f"✅ Validation completed")
        print(f"   Valid: {validation_result.is_valid}")
        print(f"   Errors: {len(validation_result.errors)}")
        print(f"   Warnings: {len(validation_result.warnings)}")
        print(f"   Quality Score: {validation_result.overall_quality_score:.2f}")
        if validation_result.errors:
            print(f"   Errors: {validation_result.errors}")
        if validation_result.warnings:
            print(f"   Warnings: {validation_result.warnings}")
        print()

        print("🎉 All SectionOptimizer tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_skills_optimization():
    """Test skills section optimization"""

    print("🔧 Testing Skills Section Optimization...\n")

    optimizer = SectionOptimizer()

    # Skills context
    context = ResumeContext(
        resume_id="test-resume-skills",
        user_id="test-user-skills",
        current_section="skills",
        full_resume_data={
            "skills": ["Python", "JavaScript", "Communication", "Leadership"]
        },
    )

    try:
        # Test skills analysis
        skills_data = [
            "Python",
            "JavaScript",
            "Communication",
            "Leadership",
            "Problem Solving",
        ]

        suggestions = await optimizer.suggest_improvements(
            section="skills", content=skills_data, context=context
        )

        print(f"✅ Generated {len(suggestions)} skills suggestions")
        for suggestion in suggestions[:2]:
            print(f"   • {suggestion.title}: {suggestion.description}")

        # Test skills validation
        categorized_skills = [
            {
                "category": "Technical Skills",
                "skills": ["Python", "JavaScript", "React"],
            },
            {
                "category": "Soft Skills",
                "skills": ["Communication", "Leadership", "Problem Solving"],
            },
        ]

        validation = await optimizer.validate_changes(
            original=skills_data, modified=categorized_skills, context=context
        )

        print(
            f"✅ Skills validation: Valid={validation.is_valid}, Quality={validation.overall_quality_score:.2f}"
        )
        print()

        return True

    except Exception as e:
        print(f"❌ Skills test failed: {e}")
        return False


async def test_education_optimization():
    """Test education section optimization"""

    print("🎓 Testing Education Section Optimization...\n")

    optimizer = SectionOptimizer()

    # Education context
    context = ResumeContext(
        resume_id="test-resume-education",
        user_id="test-user-education",
        current_section="education",
        full_resume_data={},
    )

    try:
        education_data = [
            {
                "degree": "Bachelor of Science in Computer Science",
                "university": "State University",
                "from_year": "2016",
                "to_year": "2020",
                "gpa": "3.8",
            }
        ]

        suggestions = await optimizer.suggest_improvements(
            section="education", content=education_data, context=context
        )

        print(f"✅ Generated {len(suggestions)} education suggestions")

        # Test validation
        validation = await optimizer.validate_changes(
            original=education_data, modified=education_data, context=context
        )

        print(f"✅ Education validation: Valid={validation.is_valid}")
        print()

        return True

    except Exception as e:
        print(f"❌ Education test failed: {e}")
        return False


async def run_all_tests():
    """Run all section optimizer tests"""

    print("🚀 Starting SectionOptimizer Tests\n")

    tests = [
        ("Work Experience Optimization", test_section_optimizer),
        ("Skills Section Optimization", test_skills_optimization),
        ("Education Section Optimization", test_education_optimization),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"🔍 {test_name}:")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name} PASSED\n")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED: {e}\n")

    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All SectionOptimizer tests passed!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return failed == 0


if __name__ == "__main__":
    asyncio.run(run_all_tests())

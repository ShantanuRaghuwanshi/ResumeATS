"""
Test script for Section Optimization API endpoints
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_USER_ID = "test-user-section-api"
TEST_RESUME_ID = "test-resume-section-api"


def test_section_optimization_api():
    """Test the section optimization API endpoints"""

    print("🧪 Testing Section Optimization API Endpoints...\n")

    # Test data
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

    skills_data = ["Python", "JavaScript", "Communication", "Leadership"]

    try:
        # Test 1: Optimize work experience section
        print("1️⃣ Testing section optimization...")
        optimize_response = requests.post(
            f"{BASE_URL}/section/optimize",
            json={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "section": "work_experience",
                "section_data": work_experience_data,
                "job_description": "Senior Software Engineer position requiring Python and React skills",
                "optimization_type": "job_specific",
                "llm_provider": "openai",
                "llm_config": {},
            },
        )

        if optimize_response.status_code == 200:
            optimize_data = optimize_response.json()
            print(f"✅ Section optimization successful")
            print(
                f"   Improvement Score: {optimize_data['optimization_result']['improvement_score']:.2f}"
            )
            print(
                f"   ATS Score: {optimize_data['optimization_result']['ats_score']:.2f}"
            )
            print(
                f"   Suggestions: {len(optimize_data['optimization_result']['suggestions'])}"
            )
        else:
            print(f"❌ Section optimization failed: {optimize_response.status_code}")
            print(f"   Response: {optimize_response.text}")

        print()

        # Test 2: Get section suggestions
        print("2️⃣ Testing section suggestions...")
        suggestions_response = requests.post(
            f"{BASE_URL}/section/suggestions",
            json={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "section": "work_experience",
                "content": work_experience_data,
                "focus_areas": ["quantified_achievements", "action_verbs"],
            },
        )

        if suggestions_response.status_code == 200:
            suggestions_data = suggestions_response.json()
            print(f"✅ Generated {len(suggestions_data['suggestions'])} suggestions")
            for i, suggestion in enumerate(suggestions_data["suggestions"][:3]):
                print(
                    f"   {i+1}. {suggestion['title']} (Impact: {suggestion['impact_score']:.1f})"
                )
        else:
            print(f"❌ Suggestions failed: {suggestions_response.status_code}")

        print()

        # Test 3: Validate section changes
        print("3️⃣ Testing section validation...")
        modified_data = [
            {
                "title": "Senior Software Developer",
                "company": "Tech Corp",
                "from_date": "2020-01",
                "to_date": "2023-12",
                "summary": "Led development of web applications",
                "achievements": [
                    "Improved system performance by 40%",
                    "Developed 5 new features that increased user engagement",
                ],
            }
        ]

        validation_response = requests.post(
            f"{BASE_URL}/section/validate",
            json={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "section": "work_experience",
                "original_content": work_experience_data,
                "modified_content": modified_data,
            },
        )

        if validation_response.status_code == 200:
            validation_data = validation_response.json()
            print(f"✅ Validation completed")
            print(f"   Valid: {validation_data['validation']['is_valid']}")
            print(
                f"   Quality Score: {validation_data['validation']['overall_quality_score']:.2f}"
            )
            print(f"   Errors: {len(validation_data['validation']['errors'])}")
            print(f"   Warnings: {len(validation_data['validation']['warnings'])}")
        else:
            print(f"❌ Validation failed: {validation_response.status_code}")

        print()

        # Test 4: Analyze section
        print("4️⃣ Testing section analysis...")
        content_json = json.dumps(work_experience_data)
        analysis_response = requests.get(
            f"{BASE_URL}/section/analysis/work_experience",
            params={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "content": content_json,
            },
        )

        if analysis_response.status_code == 200:
            analysis_data = analysis_response.json()
            print(f"✅ Section analysis completed")
            print(
                f"   ATS Score: {analysis_data['analysis']['ats_compatibility_score']:.2f}"
            )
            print(
                f"   Quality Score: {analysis_data['analysis']['content_quality_score']:.2f}"
            )
            print(f"   Strengths: {len(analysis_data['analysis']['strengths'])}")
            print(f"   Weaknesses: {len(analysis_data['analysis']['weaknesses'])}")
        else:
            print(f"❌ Analysis failed: {analysis_response.status_code}")

        print()

        # Test 5: Get optimization strategies
        print("5️⃣ Testing optimization strategies...")
        strategies_response = requests.get(f"{BASE_URL}/section/strategies")

        if strategies_response.status_code == 200:
            strategies_data = strategies_response.json()
            print(f"✅ Retrieved optimization strategies")
            print(
                f"   Available sections: {list(strategies_data['strategies'].keys())}"
            )
        else:
            print(f"❌ Strategies failed: {strategies_response.status_code}")

        print()

        # Test 6: Get action verbs
        print("6️⃣ Testing action verbs...")
        verbs_response = requests.get(f"{BASE_URL}/section/action-verbs")

        if verbs_response.status_code == 200:
            verbs_data = verbs_response.json()
            print(f"✅ Retrieved action verbs")
            print(f"   Categories: {list(verbs_data['action_verbs'].keys())}")
        else:
            print(f"❌ Action verbs failed: {verbs_response.status_code}")

        print()

        # Test 7: Batch optimization
        print("7️⃣ Testing batch optimization...")
        batch_sections = {
            "work_experience": work_experience_data,
            "skills": skills_data,
        }

        batch_response = requests.post(
            f"{BASE_URL}/section/batch-optimize",
            json={
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
                "sections": batch_sections,
                "job_description": "Software Engineer position",
                "optimization_type": "general",
            },
        )

        if batch_response.status_code == 200:
            batch_data = batch_response.json()
            print(f"✅ Batch optimization completed")
            print(f"   Sections processed: {list(batch_data['results'].keys())}")
            for section, result in batch_data["results"].items():
                print(f"   {section}: {'Success' if result['success'] else 'Failed'}")
        else:
            print(f"❌ Batch optimization failed: {batch_response.status_code}")

        print()

        # Test 8: Compare section versions
        print("8️⃣ Testing section comparison...")
        compare_response = requests.post(
            f"{BASE_URL}/section/compare",
            json={
                "section": "work_experience",
                "version1": work_experience_data,
                "version2": modified_data,
                "resume_id": TEST_RESUME_ID,
                "user_id": TEST_USER_ID,
            },
        )

        if compare_response.status_code == 200:
            compare_data = compare_response.json()
            print(f"✅ Section comparison completed")
            print(
                f"   Improvement: {compare_data['comparison']['improvement_metrics']['improvement_percentage']:.1f}%"
            )
        else:
            print(f"❌ Comparison failed: {compare_response.status_code}")

        print()

        # Test 9: Health check
        print("9️⃣ Testing health check...")
        health_response = requests.get(f"{BASE_URL}/section/health")

        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ Health check passed")
            print(f"   Status: {health_data['status']}")
            print(f"   Available sections: {len(health_data['available_sections'])}")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")

        print()
        print("🎉 All Section Optimization API tests completed!")
        return True

    except requests.exceptions.ConnectionError:
        print(
            "❌ Connection error: Make sure the FastAPI server is running on http://localhost:8000"
        )
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def test_error_handling():
    """Test API error handling"""

    print("🔍 Testing error handling...\n")

    try:
        # Test with invalid section
        print("Testing invalid section...")
        response = requests.post(
            f"{BASE_URL}/section/suggestions",
            json={
                "resume_id": "test",
                "user_id": "test",
                "section": "invalid_section",
                "content": {},
            },
        )
        if response.status_code == 500:  # Expected error
            print("✅ Correctly handled invalid section")
        else:
            print(f"❌ Unexpected response for invalid section: {response.status_code}")

        # Test with missing required fields
        print("Testing missing required fields...")
        response = requests.post(
            f"{BASE_URL}/section/optimize",
            json={
                "resume_id": "test"
                # Missing other required fields
            },
        )
        if response.status_code == 422:  # Validation error
            print("✅ Correctly handled missing fields")
        else:
            print(f"❌ Unexpected response for missing fields: {response.status_code}")

        print("✅ Error handling tests passed\n")
        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def run_api_tests():
    """Run all API tests"""

    print("🚀 Starting Section Optimization API Tests\n")
    print("📝 Make sure to start the FastAPI server first:")
    print("   cd backend/app && uvicorn main:app --reload\n")

    # Wait a moment for user to start server if needed
    input("Press Enter when the server is running...")

    tests = [
        ("Main API functionality", test_section_optimization_api),
        ("Error handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"🔍 {test_name}:")
        try:
            result = test_func()
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
        print("🎉 All Section Optimization API tests passed!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")

    return failed == 0


if __name__ == "__main__":
    run_api_tests()

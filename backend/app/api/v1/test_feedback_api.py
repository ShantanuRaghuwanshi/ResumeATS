#!/usr/bin/env python3
"""
Test script for Feedback API endpoints
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the parent directory to the path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_feedback_api():
    """Test the Feedback API endpoints"""

    print("Testing Feedback API endpoints...")

    # Test data
    test_resume = {
        "work_experience": [
            {
                "title": "Software Engineer",
                "company": "Tech Corp",
                "from_date": "2022",
                "to_date": "present",
                "summary": "Worked on various projects and helped the team.",
            }
        ],
        "skills": ["Python", "JavaScript", "React"],
        "education": [
            {
                "degree": "Bachelor of Science",
                "institution": "University",
                "year": "2020",
            }
        ],
    }

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
        # Test 1: Health check
        print("\n1. Testing health check...")
        response = client.get("/api/v1/feedback/health")
        assert response.status_code == 200
        health_data = response.json()
        print(f"✓ Health status: {health_data['status']}")
        print(f"✓ Service: {health_data['service']}")

        # Test 2: Change Impact Analysis
        print("\n2. Testing change impact analysis...")
        response = client.post(
            "/api/v1/feedback/change-impact",
            json={
                "before_content": before_content,
                "after_content": after_content,
                "resume_id": "test-resume-1",
                "user_id": "test-user-1",
                "section": "work_experience",
                "full_resume_data": test_resume,
                "job_description": None,
            },
        )
        assert response.status_code == 200
        impact_data = response.json()
        print(f"✓ Change type: {impact_data['analysis']['change_type']}")
        print(f"✓ Overall impact: {impact_data['analysis']['overall_impact']:.2f}")
        print(f"✓ Positive changes: {len(impact_data['analysis']['positive_changes'])}")

        # Test 3: ATS Compatibility Check
        print("\n3. Testing ATS compatibility check...")
        response = client.post(
            "/api/v1/feedback/ats-compatibility",
            json={"content": after_content, "section": "work_experience"},
        )
        assert response.status_code == 200
        ats_data = response.json()
        print(
            f"✓ Overall ATS score: {ats_data['ats_compatibility']['overall_score']:.2f}"
        )
        print(f"✓ Parsing score: {ats_data['ats_compatibility']['parsing_score']:.2f}")
        print(
            f"✓ Formatting score: {ats_data['ats_compatibility']['formatting_score']:.2f}"
        )

        # Test 4: Consistency Validation
        print("\n4. Testing consistency validation...")
        response = client.post(
            "/api/v1/feedback/consistency-validation", json={"resume": test_resume}
        )
        assert response.status_code == 200
        consistency_data = response.json()
        print(
            f"✓ Overall consistency score: {consistency_data['consistency_report']['overall_consistency_score']:.2f}"
        )
        print(
            f"✓ Date consistency: {consistency_data['consistency_report']['date_consistency']}"
        )
        print(
            f"✓ Formatting consistency: {consistency_data['consistency_report']['formatting_consistency']}"
        )

        # Test 5: Real-time Feedback
        print("\n5. Testing real-time feedback...")
        response = client.post(
            "/api/v1/feedback/real-time",
            json={
                "session_id": "test-session-1",
                "section": "work_experience",
                "current_content": "Led development of 3 major projects, improving system performance by 40%",
                "previous_content": "Worked on various projects",
            },
        )
        assert response.status_code == 200
        feedback_data = response.json()
        print(f"✓ Character count: {feedback_data['feedback']['character_count']}")
        print(f"✓ Word count: {feedback_data['feedback']['word_count']}")
        print(
            f"✓ Quality score: {feedback_data['feedback']['current_quality_score']:.2f}"
        )
        print(
            f"✓ ATS compatibility: {feedback_data['feedback']['ats_compatibility']:.2f}"
        )

        # Test 6: Aggregate Scores
        print("\n6. Testing aggregate scores...")
        response = client.post(
            "/api/v1/feedback/aggregate-scores",
            json={"resume": test_resume, "job_description": None},
        )
        assert response.status_code == 200
        aggregate_data = response.json()
        print(
            f"✓ Overall score: {aggregate_data['aggregate_scores']['overall_score']:.2f}"
        )
        print(
            f"✓ Overall quality: {aggregate_data['aggregate_scores']['overall_quality']:.2f}"
        )
        print(f"✓ Overall ATS: {aggregate_data['aggregate_scores']['overall_ats']:.2f}")
        print(
            f"✓ Section scores: {len(aggregate_data['aggregate_scores']['section_scores'])}"
        )

        # Test 7: Performance Metrics Tracking
        print("\n7. Testing performance metrics tracking...")
        response = client.post(
            "/api/v1/feedback/performance-metrics",
            json={
                "session_id": "test-session-1",
                "user_id": "test-user-1",
                "action": "edit",
                "section": "work_experience",
                "metrics": {
                    "edit_duration": 30,
                    "characters_added": 50,
                    "suggestions_viewed": 3,
                },
            },
        )
        assert response.status_code == 200
        metrics_data = response.json()
        print(f"✓ Metrics tracked: {metrics_data['success']}")
        print(f"✓ Metric ID: {metrics_data['metric_id']}")

        # Test 8: Get Performance Metrics
        print("\n8. Testing get performance metrics...")
        response = client.get("/api/v1/feedback/performance-metrics/test-user-1")
        assert response.status_code == 200
        get_metrics_data = response.json()
        print(f"✓ Metrics retrieved: {get_metrics_data['success']}")
        print(f"✓ Total count: {get_metrics_data['total_count']}")

        # Test 9: User Feedback Submission
        print("\n9. Testing user feedback submission...")
        response = client.post(
            "/api/v1/feedback/user-feedback",
            json={
                "user_id": "test-user-1",
                "rating": 4,
                "feedback_type": "suggestion_quality",
                "comment": "The suggestions were very helpful",
                "session_id": "test-session-1",
                "section": "work_experience",
                "helpful": True,
                "would_recommend": True,
            },
        )
        assert response.status_code == 200
        user_feedback_data = response.json()
        print(f"✓ User feedback submitted: {user_feedback_data['success']}")
        print(f"✓ Feedback ID: {user_feedback_data['feedback_id']}")

        print("\n✅ All Feedback API tests passed successfully!")

    except AssertionError as e:
        print(f"\n❌ Test assertion failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_feedback_api()
    sys.exit(0 if success else 1)

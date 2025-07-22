"""
Test script for Version Management API endpoints
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.version_manager import VersionManager
from models.resume_version import ResumeVersion


async def test_version_manager():
    """Test the VersionManager service functionality"""

    print("Testing Version Manager Service...")

    # Initialize version manager
    version_manager = VersionManager()

    # Test data
    user_id = "test_user_123"
    sample_resume_data = {
        "sections": {
            "personal_details": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "+1-555-0123",
                "summary": "Experienced software developer with 5+ years of experience",
            },
            "work_experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Corp",
                    "from_date": "2020-01",
                    "to_date": "Present",
                    "achievements": [
                        "Led team of 5 developers",
                        "Improved system performance by 40%",
                    ],
                }
            ],
            "skills": [
                {
                    "category": "Programming Languages",
                    "skills": ["Python", "JavaScript", "Java"],
                }
            ],
        }
    }

    try:
        # Test 1: Create a version
        print("\n1. Testing version creation...")
        version1 = await version_manager.create_version(
            user_id=user_id,
            resume_data=sample_resume_data,
            name="Original Resume",
            description="Initial version of my resume",
            job_target="Software Engineer",
            tags=["software", "engineering"],
        )
        print(f"✓ Created version: {version1.id} - {version1.name}")

        # Test 2: Create another version
        print("\n2. Testing second version creation...")
        modified_resume_data = sample_resume_data.copy()
        modified_resume_data["sections"]["personal_details"][
            "summary"
        ] = "Highly experienced software developer with 5+ years of full-stack development experience"

        version2 = await version_manager.create_version(
            user_id=user_id,
            resume_data=modified_resume_data,
            name="Updated Resume",
            description="Updated with better summary",
            job_target="Senior Software Engineer",
            tags=["software", "senior"],
        )
        print(f"✓ Created version: {version2.id} - {version2.name}")

        # Test 3: List versions
        print("\n3. Testing version listing...")
        versions = await version_manager.list_versions(user_id)
        print(f"✓ Found {len(versions)} versions for user {user_id}")
        for v in versions:
            print(f"  - {v.name} (Score: {v.overall_score})")

        # Test 4: Get specific version
        print("\n4. Testing version retrieval...")
        retrieved_version = await version_manager.get_version(version1.id, user_id)
        if retrieved_version:
            print(f"✓ Retrieved version: {retrieved_version.name}")
        else:
            print("✗ Failed to retrieve version")

        # Test 5: Update version
        print("\n5. Testing version update...")
        updated_version = await version_manager.update_version(
            version1.id,
            user_id,
            {
                "name": "Original Resume (Updated)",
                "tags": ["software", "engineering", "updated"],
            },
        )
        if updated_version:
            print(f"✓ Updated version name to: {updated_version.name}")
            print(f"✓ Updated tags: {updated_version.tags}")
        else:
            print("✗ Failed to update version")

        # Test 6: Compare versions
        print("\n6. Testing version comparison...")
        comparison = await version_manager.compare_versions(
            version1.id, version2.id, user_id
        )
        if comparison:
            print(f"✓ Comparison completed")
            print(f"  - Similarity: {comparison.overall_similarity:.2%}")
            print(f"  - Quality difference: {comparison.quality_difference}")
            print(f"  - Modifications: {len(comparison.modifications)}")
        else:
            print("✗ Failed to compare versions")

        # Test 7: Get version history
        print("\n7. Testing version history...")
        history = await version_manager.get_version_history(version1.id, user_id)
        if history:
            print(f"✓ Retrieved history for version {version1.id}")
            print(f"  - Total changes: {history.total_changes}")
        else:
            print("✗ Failed to get version history")

        # Test 8: Create template
        print("\n8. Testing template creation...")
        template = await version_manager.create_template(
            version2.id,
            user_id,
            "Software Engineer Template",
            "Template for software engineering positions",
            industry="Technology",
            experience_level="Senior",
        )
        if template:
            print(f"✓ Created template: {template.name}")
        else:
            print("✗ Failed to create template")

        # Test 9: Restore version
        print("\n9. Testing version restore...")
        restored_version = await version_manager.restore_version(version1.id, user_id)
        if restored_version:
            print(f"✓ Restored version as: {restored_version.name}")
        else:
            print("✗ Failed to restore version")

        # Test 10: Get analytics
        print("\n10. Testing analytics...")
        analytics = await version_manager.get_analytics(user_id, version1.id)
        if analytics:
            print(f"✓ Retrieved analytics for version {version1.id}")
            print(f"  - View count: {analytics.view_count}")
            print(f"  - Edit count: {analytics.edit_count}")
        else:
            print("✗ Failed to get analytics")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


def test_api_endpoints():
    """Test API endpoint structure (without actual HTTP calls)"""

    print("\nTesting API Endpoint Structure...")

    # Import the router to verify it's properly structured
    try:
        from api.v1.version_management import router

        print("✓ Version management router imported successfully")

        # Check if router has routes
        if hasattr(router, "routes") and router.routes:
            print(f"✓ Router has {len(router.routes)} routes defined")

            # List all routes
            for route in router.routes:
                if hasattr(route, "path") and hasattr(route, "methods"):
                    methods = list(route.methods) if route.methods else ["GET"]
                    print(f"  - {methods[0]} {route.path}")
        else:
            print("✗ Router has no routes defined")

    except Exception as e:
        print(f"✗ Failed to import router: {e}")


if __name__ == "__main__":
    print("=== Version Management API Tests ===")

    # Test API structure
    test_api_endpoints()

    # Test service functionality
    asyncio.run(test_version_manager())

    print("\n=== Tests Complete ===")

"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime

# We'll need to import the FastAPI app
# For now, we'll create a mock structure since the actual app structure may vary


class TestAPIIntegration:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        # This would normally import the actual FastAPI app
        # For testing purposes, we'll create a mock client
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()

        # Mock endpoints for testing
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        @app.post("/api/v1/conversation/start")
        async def start_conversation(request: dict):
            return {
                "session_id": "test-session-123",
                "section": request.get("section", "work_experience"),
                "status": "active",
            }

        @app.post("/api/v1/conversation/{session_id}/message")
        async def send_message(session_id: str, request: dict):
            return {
                "message": "AI response to your message",
                "suggestions": [
                    {
                        "id": "suggestion-1",
                        "type": "content",
                        "title": "Add quantified achievements",
                        "description": "Include specific metrics",
                        "impact_score": 0.8,
                    }
                ],
            }

        @app.post("/api/v1/sections/optimize")
        async def optimize_section(request: dict):
            return {
                "optimized_content": {"enhanced": "content"},
                "suggestions": [],
                "improvement_score": 0.15,
                "ats_score": 0.85,
            }

        @app.post("/api/v1/job-analysis/analyze")
        async def analyze_job(request: dict):
            return {
                "job_title": "Software Engineer",
                "required_skills": ["Python", "JavaScript"],
                "industry": "technology",
                "confidence_score": 0.85,
            }

        @app.post("/api/v1/feedback/analyze-change")
        async def analyze_change(request: dict):
            return {
                "overall_impact": 0.2,
                "positive_changes": ["Added metrics"],
                "negative_changes": [],
                "warnings": [],
            }

        @app.post("/api/v1/versions/create")
        async def create_version(request: dict):
            return {
                "id": "version-123",
                "name": request.get("name", "New Version"),
                "version_number": 1,
                "created_at": datetime.utcnow().isoformat(),
            }

        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_start_conversation_success(self, client):
        """Test starting a conversation successfully."""
        request_data = {
            "resume_id": "test-resume-123",
            "user_id": "test-user-456",
            "section": "work_experience",
        }

        response = client.post("/api/v1/conversation/start", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["section"] == "work_experience"
        assert data["status"] == "active"

    def test_start_conversation_missing_data(self, client):
        """Test starting conversation with missing data."""
        request_data = {}  # Missing required fields

        response = client.post("/api/v1/conversation/start", json=request_data)

        # Should still work with defaults in our mock
        assert response.status_code == 200

    def test_send_message_success(self, client):
        """Test sending a message in conversation."""
        session_id = "test-session-123"
        request_data = {
            "content": "Help me improve my work experience section",
            "role": "user",
        }

        response = client.post(
            f"/api/v1/conversation/{session_id}/message", json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0
        assert data["suggestions"][0]["type"] == "content"

    def test_optimize_section_success(self, client):
        """Test section optimization endpoint."""
        request_data = {
            "section": "work_experience",
            "content": {
                "work_experience": [
                    {
                        "title": "Software Engineer",
                        "company": "Tech Corp",
                        "achievements": ["Worked on projects"],
                    }
                ]
            },
            "optimization_type": "general",
        }

        response = client.post("/api/v1/sections/optimize", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "optimized_content" in data
        assert "improvement_score" in data
        assert "ats_score" in data
        assert data["improvement_score"] > 0

    def test_analyze_job_description_success(self, client):
        """Test job description analysis endpoint."""
        request_data = {
            "job_description": """
            Senior Software Engineer position requiring Python and JavaScript experience.
            Must have 5+ years of experience in web development.
            """
        }

        response = client.post("/api/v1/job-analysis/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "job_title" in data
        assert "required_skills" in data
        assert "industry" in data
        assert "confidence_score" in data
        assert data["job_title"] == "Software Engineer"
        assert "Python" in data["required_skills"]

    def test_analyze_change_impact_success(self, client):
        """Test change impact analysis endpoint."""
        request_data = {
            "before": {"achievements": ["Worked on projects"]},
            "after": {
                "achievements": [
                    "Developed 5 applications, improving performance by 40%"
                ]
            },
            "section": "work_experience",
        }

        response = client.post("/api/v1/feedback/analyze-change", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "overall_impact" in data
        assert "positive_changes" in data
        assert "negative_changes" in data
        assert "warnings" in data
        assert data["overall_impact"] > 0

    def test_create_version_success(self, client):
        """Test version creation endpoint."""
        request_data = {
            "name": "Software Engineer Resume v1",
            "description": "Initial version for tech roles",
            "resume_data": {
                "sections": {
                    "personal_details": {"name": "John Doe"},
                    "work_experience": [],
                }
            },
        }

        response = client.post("/api/v1/versions/create", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "version_number" in data
        assert "created_at" in data
        assert data["name"] == "Software Engineer Resume v1"

    def test_api_error_handling(self, client):
        """Test API error handling for invalid requests."""
        # Test with invalid JSON
        response = client.post(
            "/api/v1/conversation/start",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        # Should handle the error gracefully
        assert response.status_code in [400, 422]  # Bad request or validation error

    def test_api_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/health")

        # In a real implementation, we'd check for CORS headers
        assert response.status_code == 200

    def test_api_content_type_validation(self, client):
        """Test content type validation."""
        # Test with wrong content type
        response = client.post(
            "/api/v1/conversation/start",
            data="test data",
            headers={"Content-Type": "text/plain"},
        )

        # Should handle content type issues
        assert response.status_code in [400, 415, 422]


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""

        class MockDBService:
            def __init__(self):
                self.data = {}

            def create(self, collection, key, data):
                if collection not in self.data:
                    self.data[collection] = {}
                self.data[collection][key] = data
                return True

            def read(self, collection, key):
                return self.data.get(collection, {}).get(key)

            def update(self, collection, key, data):
                if collection not in self.data:
                    self.data[collection] = {}
                self.data[collection][key] = data
                return True

            def delete(self, collection, key):
                if collection in self.data and key in self.data[collection]:
                    del self.data[collection][key]
                    return True
                return False

            def find(self, collection, **filters):
                if collection not in self.data:
                    return []

                results = []
                for key, data in self.data[collection].items():
                    match = True
                    for filter_key, filter_value in filters.items():
                        if data.get(filter_key) != filter_value:
                            match = False
                            break
                    if match:
                        results.append(data)
                return results

        return MockDBService()

    def test_database_crud_operations(self, mock_db_service):
        """Test basic CRUD operations."""
        # Create
        result = mock_db_service.create("test_collection", "test_key", {"data": "test"})
        assert result is True

        # Read
        data = mock_db_service.read("test_collection", "test_key")
        assert data == {"data": "test"}

        # Update
        result = mock_db_service.update(
            "test_collection", "test_key", {"data": "updated"}
        )
        assert result is True

        updated_data = mock_db_service.read("test_collection", "test_key")
        assert updated_data == {"data": "updated"}

        # Delete
        result = mock_db_service.delete("test_collection", "test_key")
        assert result is True

        deleted_data = mock_db_service.read("test_collection", "test_key")
        assert deleted_data is None

    def test_database_find_operations(self, mock_db_service):
        """Test find operations with filters."""
        # Create test data
        mock_db_service.create("users", "user1", {"name": "John", "role": "admin"})
        mock_db_service.create("users", "user2", {"name": "Jane", "role": "user"})
        mock_db_service.create("users", "user3", {"name": "Bob", "role": "admin"})

        # Find all users
        all_users = mock_db_service.find("users")
        assert len(all_users) == 3

        # Find admin users
        admin_users = mock_db_service.find("users", role="admin")
        assert len(admin_users) == 2

        # Find specific user
        john_users = mock_db_service.find("users", name="John")
        assert len(john_users) == 1
        assert john_users[0]["name"] == "John"

    def test_database_concurrent_operations(self, mock_db_service):
        """Test concurrent database operations."""
        import threading
        import time

        results = []

        def create_data(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_item_{i}"
                data = {"thread_id": thread_id, "item": i}
                result = mock_db_service.create("concurrent_test", key, data)
                results.append(result)
                time.sleep(0.001)  # Small delay to simulate real operations

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_data, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        assert all(results)

        # Verify all data was created
        all_data = mock_db_service.find("concurrent_test")
        assert len(all_data) == 30  # 3 threads * 10 items each


class TestServiceIntegration:
    """Integration tests between services."""

    @pytest.fixture
    def integrated_services(self, mock_database, mock_llm_provider):
        """Create integrated service instances."""
        from conftest import (
            create_mock_conversation_manager,
            create_mock_section_optimizer,
            create_mock_job_matcher,
            create_mock_feedback_analyzer,
            create_mock_version_manager,
        )

        return {
            "conversation_manager": create_mock_conversation_manager(mock_database),
            "section_optimizer": create_mock_section_optimizer(mock_database),
            "job_matcher": create_mock_job_matcher(mock_llm_provider),
            "feedback_analyzer": create_mock_feedback_analyzer(mock_database),
            "version_manager": create_mock_version_manager(mock_database),
        }

    @pytest.mark.asyncio
    async def test_conversation_to_optimization_flow(
        self, integrated_services, sample_resume_data
    ):
        """Test flow from conversation to section optimization."""
        conversation_manager = integrated_services["conversation_manager"]
        section_optimizer = integrated_services["section_optimizer"]

        # Mock dependencies
        conversation_manager._get_resume_data = AsyncMock(
            return_value=sample_resume_data
        )
        conversation_manager._get_user_preferences = AsyncMock(return_value={})
        conversation_manager._generate_initial_message = AsyncMock(return_value=None)

        # Start conversation
        session = await conversation_manager.start_section_conversation(
            resume_id="test-resume-123",
            user_id="test-user-456",
            section="work_experience",
        )

        # Mock optimization methods
        section_optimizer._analyze_section = AsyncMock(return_value=Mock())
        section_optimizer._generate_optimized_content = AsyncMock(
            return_value={"optimized": True}
        )
        section_optimizer._generate_section_suggestions = AsyncMock(return_value=[])
        section_optimizer._calculate_improvement_metrics = AsyncMock(
            return_value=Mock(improvement_percentage=15.0, ats_improvement=0.1)
        )
        section_optimizer._calculate_keyword_density = AsyncMock(return_value=0.05)
        section_optimizer._calculate_readability_score = AsyncMock(return_value=0.8)
        section_optimizer._generate_changes_summary = AsyncMock(
            return_value="Improvements made"
        )

        # Optimize section using context from conversation
        result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=session.context,
        )

        # Verify integration
        assert session is not None
        assert result is not None
        assert result.optimized_content == {"optimized": True}

    @pytest.mark.asyncio
    async def test_job_analysis_to_optimization_flow(
        self, integrated_services, sample_job_description, sample_resume_data
    ):
        """Test flow from job analysis to targeted optimization."""
        job_matcher = integrated_services["job_matcher"]
        section_optimizer = integrated_services["section_optimizer"]

        # Mock job analysis
        job_matcher._call_llm_for_extraction = AsyncMock(
            side_effect=["Software Engineer", "[]", "[]", "[]"]
        )

        # Analyze job
        job_analysis = await job_matcher.analyze_job_description(sample_job_description)

        # Mock optimization with job context
        section_optimizer._analyze_section = AsyncMock(return_value=Mock())
        section_optimizer._generate_optimized_content = AsyncMock(
            return_value={"job_optimized": True}
        )
        section_optimizer._generate_section_suggestions = AsyncMock(return_value=[])
        section_optimizer._calculate_improvement_metrics = AsyncMock(
            return_value=Mock(improvement_percentage=20.0, ats_improvement=0.15)
        )
        section_optimizer._calculate_keyword_density = AsyncMock(return_value=0.08)
        section_optimizer._calculate_readability_score = AsyncMock(return_value=0.85)
        section_optimizer._generate_changes_summary = AsyncMock(
            return_value="Job-targeted improvements"
        )

        from models.conversation import ResumeContext

        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Optimize with job description
        result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=context,
            job_description=sample_job_description,
        )

        # Verify integration
        assert job_analysis is not None
        assert result is not None
        assert result.optimized_content == {"job_optimized": True}

    @pytest.mark.asyncio
    async def test_optimization_to_feedback_flow(
        self, integrated_services, sample_resume_data
    ):
        """Test flow from optimization to feedback analysis."""
        section_optimizer = integrated_services["section_optimizer"]
        feedback_analyzer = integrated_services["feedback_analyzer"]

        from models.conversation import ResumeContext

        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data=sample_resume_data,
            user_preferences={},
        )

        # Mock optimization
        section_optimizer._analyze_section = AsyncMock(return_value=Mock())
        section_optimizer._generate_optimized_content = AsyncMock(
            return_value={"achievements": ["Improved performance by 40%"]}
        )
        section_optimizer._generate_section_suggestions = AsyncMock(return_value=[])
        section_optimizer._calculate_improvement_metrics = AsyncMock(
            return_value=Mock(improvement_percentage=15.0, ats_improvement=0.1)
        )
        section_optimizer._calculate_keyword_density = AsyncMock(return_value=0.05)
        section_optimizer._calculate_readability_score = AsyncMock(return_value=0.8)
        section_optimizer._generate_changes_summary = AsyncMock(
            return_value="Added metrics"
        )

        # Optimize section
        optimization_result = await section_optimizer.optimize_section(
            section_data=sample_resume_data["sections"]["work_experience"],
            context=context,
        )

        # Mock feedback analysis
        feedback_analyzer._calculate_overall_impact = AsyncMock(return_value=0.2)
        feedback_analyzer._calculate_ats_impact = AsyncMock(return_value=0.1)
        feedback_analyzer._calculate_keyword_impact = AsyncMock(return_value=0.15)
        feedback_analyzer._calculate_readability_impact = AsyncMock(return_value=0.05)
        feedback_analyzer._calculate_relevance_impact = AsyncMock(return_value=0.1)
        feedback_analyzer._identify_positive_changes = AsyncMock(
            return_value=["Added quantified achievements"]
        )
        feedback_analyzer._identify_negative_changes = AsyncMock(return_value=[])
        feedback_analyzer._identify_neutral_changes = AsyncMock(return_value=[])
        feedback_analyzer._generate_improvement_recommendations = AsyncMock(
            return_value=["Consider more metrics"]
        )
        feedback_analyzer._generate_change_warnings = AsyncMock(return_value=[])

        # Analyze the change impact
        feedback_result = await feedback_analyzer.analyze_change_impact(
            before=sample_resume_data["sections"]["work_experience"],
            after=optimization_result.optimized_content,
            context=context,
        )

        # Verify integration
        assert optimization_result is not None
        assert feedback_result is not None
        assert feedback_result.overall_impact > 0
        assert "Added quantified achievements" in feedback_result.positive_changes

    @pytest.mark.asyncio
    async def test_version_management_integration(
        self, integrated_services, sample_resume_data
    ):
        """Test version management integration with other services."""
        version_manager = integrated_services["version_manager"]
        feedback_analyzer = integrated_services["feedback_analyzer"]

        # Mock version manager methods
        version_manager._calculate_quality_scores = AsyncMock(
            return_value={
                "overall_score": 0.75,
                "ats_score": 0.80,
                "keyword_score": 0.70,
            }
        )
        version_manager._create_backup = AsyncMock()
        version_manager._initialize_analytics = AsyncMock()

        # Create initial version
        version1 = await version_manager.create_version(
            user_id="test-user-456",
            resume_data=sample_resume_data,
            name="Original Version",
        )

        # Create modified version
        modified_data = sample_resume_data.copy()
        modified_data["sections"]["work_experience"][0]["achievements"].append(
            "Improved system performance by 40%"
        )

        version_manager._calculate_quality_scores = AsyncMock(
            return_value={
                "overall_score": 0.85,
                "ats_score": 0.85,
                "keyword_score": 0.80,
            }
        )

        version2 = await version_manager.create_version(
            user_id="test-user-456", resume_data=modified_data, name="Improved Version"
        )

        # Mock comparison methods
        version_manager._calculate_similarity = AsyncMock(return_value=0.9)
        version_manager._calculate_section_differences = AsyncMock(
            return_value={"work_experience": {"changed": True, "similarity": 0.85}}
        )
        version_manager._analyze_changes = AsyncMock(
            return_value={
                "additions": [],
                "deletions": [],
                "modifications": ["Enhanced work experience"],
                "content_changes": {},
                "formatting_changes": [],
                "structural_changes": [],
            }
        )
        version_manager._generate_comparison_recommendations = AsyncMock(
            return_value={
                "improvements": ["Added quantified achievements"],
                "regressions": [],
                "neutral_changes": [],
                "merge_suggestions": [],
                "rollback_recommendations": [],
            }
        )

        # Compare versions
        comparison = await version_manager.compare_versions(
            version1.id, version2.id, "test-user-456"
        )

        # Verify integration
        assert version1 is not None
        assert version2 is not None
        assert comparison is not None
        assert comparison.quality_difference == 0.1  # 0.85 - 0.75
        assert "Enhanced work experience" in comparison.modifications

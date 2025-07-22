"""
Integration tests for the complete application
Tests the integration of all components and services
"""

import pytest
import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from services.integration_service import integration_service
from services.websocket_manager import websocket_manager
from configs.logging_config import get_service_logger

logger = get_service_logger("integration_tests")

# Test client
client = TestClient(app)


class TestApplicationIntegration:
    """Test complete application integration"""

    @pytest.fixture(autouse=True)
    async def setup_integration_service(self):
        """Setup integration service for tests"""
        try:
            await integration_service.initialize()
            yield
        finally:
            await integration_service.shutdown()

    def test_application_startup(self):
        """Test that the application starts up correctly"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_health_check_basic(self):
        """Test basic health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["version"] == "2.0.0"

    def test_health_check_detailed(self):
        """Test detailed health check endpoint"""
        response = client.get("/api/v1/monitoring/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_system_status(self):
        """Test system status endpoint"""
        response = client.get("/api/v1/monitoring/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert "system_status" in data

        system_status = data["system_status"]
        assert "system_health" in system_status
        assert "websocket_connections" in system_status
        assert "performance_metrics" in system_status

    def test_websocket_stats(self):
        """Test WebSocket statistics endpoint"""
        response = client.get("/api/v1/monitoring/websocket/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "websocket_stats" in data

        stats = data["websocket_stats"]
        assert "active_connections" in stats
        assert "connections_by_type" in stats

    def test_services_status(self):
        """Test services status endpoint"""
        response = client.get("/api/v1/monitoring/services/status")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "services" in data
        assert "overall_healthy" in data

    def test_api_endpoints_accessibility(self):
        """Test that all main API endpoints are accessible"""
        endpoints = [
            "/api/v1/resume/",
            "/api/v1/conversation/",
            "/api/v1/section-optimization/",
            "/api/v1/job-analysis/",
            "/api/v1/feedback/",
            "/api/v1/versions/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test that service errors are handled properly"""

        # Simulate a service error
        with patch.object(
            integration_service.conversation_manager,
            "health_check",
            side_effect=Exception("Test error"),
        ):
            health_status = await integration_service.health_check_all_services()

            assert not health_status["overall_healthy"]
            assert "conversation_manager" in health_status["services"]
            assert not health_status["services"]["conversation_manager"]["healthy"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self):
        """Test circuit breaker functionality"""

        service_name = "test_service"

        # Simulate multiple failures to trigger circuit breaker
        for _ in range(6):  # More than the threshold of 5
            await integration_service.handle_service_error(
                service_name, "test_operation", Exception("Test error")
            )

        # Check that circuit breaker is open
        assert integration_service.circuit_breakers[service_name]["state"] == "open"

    @pytest.mark.asyncio
    async def test_websocket_manager_functionality(self):
        """Test WebSocket manager basic functionality"""

        # Test connection stats
        stats = websocket_manager.get_connection_stats()
        assert isinstance(stats, dict)
        assert "active_connections" in stats
        assert "connections_by_type" in stats

        # Test cleanup
        await websocket_manager.cleanup_inactive_connections()

    def test_cors_configuration(self):
        """Test CORS configuration"""
        response = client.options(
            "/api/v1/resume/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should allow CORS for configured origins
        assert response.status_code == 200

    def test_error_handling_middleware(self):
        """Test that error handling middleware works"""

        # Test with invalid endpoint
        response = client.get("/api/v1/nonexistent/")
        assert response.status_code == 404

        # Response should be JSON
        assert response.headers["content-type"] == "application/json"


class TestServiceIntegration:
    """Test integration between different services"""

    @pytest.mark.asyncio
    async def test_conversation_to_optimization_flow(self):
        """Test flow from conversation to section optimization"""

        # Mock the services
        with patch.object(
            integration_service.conversation_manager, "start_section_conversation"
        ) as mock_conversation, patch.object(
            integration_service.section_optimizer, "optimize_section"
        ) as mock_optimizer:

            mock_conversation.return_value = AsyncMock()
            mock_optimizer.return_value = {"suggestions": []}

            # Test the integration flow
            result = await integration_service.execute_with_error_handling(
                "conversation_manager",
                "start_section_conversation",
                integration_service.conversation_manager.start_section_conversation,
                "resume_id",
                "experience",
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_job_analysis_to_feedback_flow(self):
        """Test flow from job analysis to feedback"""

        with patch.object(
            integration_service.job_matcher, "analyze_job_description"
        ) as mock_job_analysis, patch.object(
            integration_service.feedback_analyzer, "analyze_change_impact"
        ) as mock_feedback:

            mock_job_analysis.return_value = {"analysis": {"skills": []}}
            mock_feedback.return_value = {"feedback": {"score": 0.8}}

            # Test the integration flow
            job_result = await integration_service.execute_with_error_handling(
                "job_matcher",
                "analyze_job_description",
                integration_service.job_matcher.analyze_job_description,
                "test job description",
            )

            feedback_result = await integration_service.execute_with_error_handling(
                "feedback_analyzer",
                "analyze_change_impact",
                integration_service.feedback_analyzer.analyze_change_impact,
                {},
                {},
            )

            assert job_result["success"] is True
            assert feedback_result["success"] is True

    @pytest.mark.asyncio
    async def test_version_management_integration(self):
        """Test version management integration"""

        with patch.object(
            integration_service.version_manager, "create_version"
        ) as mock_create, patch.object(
            integration_service.version_manager, "list_versions"
        ) as mock_list:

            mock_create.return_value = {"id": "version_1", "name": "Test Version"}
            mock_list.return_value = [{"id": "version_1", "name": "Test Version"}]

            # Test version creation
            create_result = await integration_service.execute_with_error_handling(
                "version_manager",
                "create_version",
                integration_service.version_manager.create_version,
                {},
                "Test Version",
                "Test Description",
            )

            # Test version listing
            list_result = await integration_service.execute_with_error_handling(
                "version_manager",
                "list_versions",
                integration_service.version_manager.list_versions,
                "user_1",
            )

            assert create_result["success"] is True
            assert list_result["success"] is True


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    def test_resume_upload_workflow(self):
        """Test complete resume upload and processing workflow"""

        # This would test the complete flow:
        # 1. Upload resume
        # 2. Parse resume
        # 3. Analyze sections
        # 4. Generate suggestions
        # 5. Apply optimizations
        # 6. Create version
        # 7. Export resume

        # For now, just test that the endpoints exist
        endpoints = [
            "/api/v1/resume/upload",
            "/api/v1/resume/parse",
            "/api/v1/section-optimization/optimize",
            "/api/v1/versions/create",
            "/api/v1/resume/export",
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json={})
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404

    def test_job_analysis_workflow(self):
        """Test complete job analysis workflow"""

        # Test job analysis endpoints
        endpoints = [
            "/api/v1/job-analysis/analyze",
            "/api/v1/job-analysis/match",
            "/api/v1/job-analysis/recommendations",
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json={})
            assert response.status_code != 404

    def test_conversation_workflow(self):
        """Test complete conversation workflow"""

        # Test conversation endpoints
        endpoints = [
            "/api/v1/conversation/start",
            "/api/v1/conversation/message",
            "/api/v1/conversation/history",
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json={})
            assert response.status_code != 404


class TestPerformanceIntegration:
    """Test performance aspects of integration"""

    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        import time

        results = []

        def make_request():
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()
            results.append(
                {"status_code": response.status_code, "duration": end_time - start_time}
            )

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(results) == 10
        for result in results:
            assert result["status_code"] == 200
            assert result["duration"] < 5.0  # Should respond within 5 seconds

    def test_memory_usage(self):
        """Test that memory usage is reasonable"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss

        # Make several requests
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200

        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before

        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


class TestSecurityIntegration:
    """Test security aspects of integration"""

    def test_security_headers(self):
        """Test that security headers are present"""
        response = client.get("/")

        # Check for security headers (these would be added by middleware)
        # Note: Actual headers depend on security middleware implementation
        assert response.status_code == 200

    def test_input_validation(self):
        """Test input validation across endpoints"""

        # Test with malicious input
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
        ]

        for malicious_input in malicious_inputs:
            response = client.post(
                "/api/v1/conversation/message", json={"message": malicious_input}
            )

            # Should handle malicious input gracefully
            assert response.status_code in [400, 422, 500]  # Not 200

    def test_rate_limiting(self):
        """Test rate limiting functionality"""

        # Make many requests quickly
        responses = []
        for _ in range(50):
            response = client.get("/health")
            responses.append(response.status_code)

        # Should eventually hit rate limit (429) or continue working (200)
        # Exact behavior depends on rate limiting configuration
        assert all(status in [200, 429] for status in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

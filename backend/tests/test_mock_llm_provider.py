"""
Mock LLM Provider for testing purposes.
"""

import pytest
from unittest.mock import AsyncMock
from typing import Dict, Any, List


class MockLLMProvider:
    """Mock LLM provider for consistent testing."""

    def __init__(self):
        self.call_count = 0
        self.responses = {}
        self.default_response = "Mock LLM response"

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a mock response."""
        self.call_count += 1

        # Return specific response if configured
        if prompt in self.responses:
            return self.responses[prompt]

        # Return default response
        return self.default_response

    async def generate_suggestions(
        self, content: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate mock suggestions."""
        return [
            {
                "type": "content",
                "title": "Mock suggestion",
                "description": "This is a mock suggestion for testing",
                "impact_score": 0.8,
                "reasoning": "Mock reasoning",
                "confidence": 0.9,
            }
        ]

    async def analyze_content(self, content: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze content and return mock analysis."""
        return {
            "analysis_type": analysis_type,
            "quality_score": 0.75,
            "issues": [],
            "suggestions": ["Mock suggestion"],
            "confidence": 0.8,
        }

    def set_response(self, prompt: str, response: str):
        """Set a specific response for a prompt."""
        self.responses[prompt] = response

    def set_default_response(self, response: str):
        """Set the default response."""
        self.default_response = response

    def reset(self):
        """Reset the mock provider."""
        self.call_count = 0
        self.responses = {}
        self.default_response = "Mock LLM response"


class TestMockLLMProvider:
    """Test cases for MockLLMProvider."""

    @pytest.fixture
    def mock_provider(self):
        """Create MockLLMProvider instance."""
        return MockLLMProvider()

    @pytest.mark.asyncio
    async def test_generate_response_default(self, mock_provider):
        """Test default response generation."""
        response = await mock_provider.generate_response("Test prompt")

        assert response == "Mock LLM response"
        assert mock_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_response_specific(self, mock_provider):
        """Test specific response generation."""
        mock_provider.set_response("specific prompt", "specific response")

        response = await mock_provider.generate_response("specific prompt")

        assert response == "specific response"
        assert mock_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_suggestions(self, mock_provider):
        """Test suggestion generation."""
        suggestions = await mock_provider.generate_suggestions("test content", {})

        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "content"
        assert suggestions[0]["title"] == "Mock suggestion"
        assert suggestions[0]["impact_score"] == 0.8

    @pytest.mark.asyncio
    async def test_analyze_content(self, mock_provider):
        """Test content analysis."""
        analysis = await mock_provider.analyze_content("test content", "quality")

        assert analysis["analysis_type"] == "quality"
        assert analysis["quality_score"] == 0.75
        assert analysis["confidence"] == 0.8
        assert isinstance(analysis["issues"], list)
        assert isinstance(analysis["suggestions"], list)

    def test_set_default_response(self, mock_provider):
        """Test setting default response."""
        mock_provider.set_default_response("New default response")

        assert mock_provider.default_response == "New default response"

    def test_reset(self, mock_provider):
        """Test provider reset."""
        mock_provider.set_response("test", "response")
        mock_provider.set_default_response("custom default")
        mock_provider.call_count = 5

        mock_provider.reset()

        assert mock_provider.call_count == 0
        assert mock_provider.responses == {}
        assert mock_provider.default_response == "Mock LLM response"

    @pytest.mark.asyncio
    async def test_multiple_calls_increment_count(self, mock_provider):
        """Test that multiple calls increment the call count."""
        await mock_provider.generate_response("prompt 1")
        await mock_provider.generate_response("prompt 2")
        await mock_provider.generate_response("prompt 3")

        assert mock_provider.call_count == 3

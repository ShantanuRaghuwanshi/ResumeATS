"""
Unit tests for ConversationManager service.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

from services.conversation_manager import ConversationManager
from models.conversation import (
    ConversationSession,
    Message,
    AIResponse,
    Suggestion,
    ResumeContext,
)
from conftest import create_mock_conversation_manager


class TestConversationManager:
    """Test cases for ConversationManager service."""

    @pytest.fixture
    def conversation_manager(self, mock_database):
        """Create ConversationManager instance for testing."""
        return create_mock_conversation_manager(mock_database)

    @pytest.mark.asyncio
    async def test_start_section_conversation_success(
        self, conversation_manager, sample_resume_data
    ):
        """Test successful conversation session creation."""
        # Mock resume data retrieval
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

        # Assertions
        assert session is not None
        assert session.resume_id == "test-resume-123"
        assert session.user_id == "test-user-456"
        assert session.section == "work_experience"
        assert session.title == "Work Experience Optimization"
        assert session.is_active is True
        assert len(session.messages) == 0

        # Verify session was stored
        stored_session = conversation_manager.db.read("conversations", session.id)
        assert stored_session is not None

    @pytest.mark.asyncio
    async def test_start_section_conversation_resume_not_found(
        self, conversation_manager
    ):
        """Test conversation creation when resume is not found."""
        # Mock resume data retrieval to return None
        conversation_manager._get_resume_data = AsyncMock(return_value=None)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Resume not found"):
            await conversation_manager.start_section_conversation(
                resume_id="nonexistent-resume",
                user_id="test-user-456",
                section="work_experience",
            )

    @pytest.mark.asyncio
    async def test_send_message_user_message(
        self, conversation_manager, sample_conversation_session
    ):
        """Test sending a user message."""
        # Store session in mock database
        conversation_manager.db.create(
            "conversations",
            sample_conversation_session.id,
            sample_conversation_session.model_dump(),
        )
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        # Mock AI response generation
        mock_ai_response = AIResponse(
            message="I can help you improve your work experience section.",
            confidence=0.8,
            suggestions=[
                Suggestion(
                    type="content",
                    title="Add metrics",
                    description="Include quantified achievements",
                    impact_score=0.9,
                    reasoning="Numbers demonstrate impact",
                    section="work_experience",
                    confidence=0.85,
                )
            ],
        )
        conversation_manager._generate_ai_response = AsyncMock(
            return_value=mock_ai_response
        )

        # Send message
        response = await conversation_manager.send_message(
            session_id=sample_conversation_session.id,
            content="Help me improve my work experience section",
            role="user",
        )

        # Assertions
        assert response is not None
        assert (
            response.message == "I can help you improve your work experience section."
        )
        assert len(response.suggestions) == 1
        assert response.suggestions[0].title == "Add metrics"

        # Verify session was updated
        updated_session = conversation_manager.active_sessions[
            sample_conversation_session.id
        ]
        assert len(updated_session.messages) == 2  # User message + AI response
        assert updated_session.total_suggestions == 1

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(self, conversation_manager):
        """Test sending message to non-existent session."""
        with pytest.raises(ValueError, match="Session not found"):
            await conversation_manager.send_message(
                session_id="nonexistent-session", content="Test message"
            )

    @pytest.mark.asyncio
    async def test_apply_suggestion_success(
        self, conversation_manager, sample_conversation_session, sample_suggestions
    ):
        """Test successful suggestion application."""
        # Add suggestion to session
        message = Message(
            session_id=sample_conversation_session.id,
            role="assistant",
            content="Here are some suggestions",
            suggestions=sample_suggestions,
        )
        sample_conversation_session.messages.append(message)

        # Store session
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        # Mock suggestion application
        conversation_manager._apply_suggestion_to_resume = AsyncMock(
            return_value={"updated": "content"}
        )

        # Apply suggestion
        result = await conversation_manager.apply_suggestion(
            session_id=sample_conversation_session.id,
            suggestion_id=sample_suggestions[0].id,
        )

        # Assertions
        assert result["success"] is True
        assert result["updated_content"] == {"updated": "content"}
        assert sample_suggestions[0].applied is True
        assert sample_conversation_session.applied_suggestions == 1

    @pytest.mark.asyncio
    async def test_apply_suggestion_not_found(
        self, conversation_manager, sample_conversation_session
    ):
        """Test applying non-existent suggestion."""
        # Store session without suggestions
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        with pytest.raises(ValueError, match="Suggestion not found"):
            await conversation_manager.apply_suggestion(
                session_id=sample_conversation_session.id,
                suggestion_id="nonexistent-suggestion",
            )

    @pytest.mark.asyncio
    async def test_get_conversation_history(
        self, conversation_manager, sample_conversation_session
    ):
        """Test retrieving conversation history."""
        # Add messages to session
        messages = [
            Message(
                session_id=sample_conversation_session.id, role="user", content="Hello"
            ),
            Message(
                session_id=sample_conversation_session.id,
                role="assistant",
                content="Hi! How can I help?",
            ),
        ]
        sample_conversation_session.messages = messages

        # Store session
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        # Get history
        history = await conversation_manager.get_conversation_history(
            sample_conversation_session.id
        )

        # Assertions
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello"
        assert history[1].role == "assistant"
        assert history[1].content == "Hi! How can I help?"

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, conversation_manager):
        """Test retrieving active sessions for a user."""
        # Mock database response
        mock_sessions = [
            {
                "id": "session-1",
                "user_id": "test-user-456",
                "section": "work_experience",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "messages": [],
                "total_suggestions": 0,
                "applied_suggestions": 0,
                "context": {
                    "resume_id": "test-resume-123",
                    "user_id": "test-user-456",
                    "current_section": "work_experience",
                    "full_resume_data": {},
                    "user_preferences": {},
                },
            }
        ]
        conversation_manager.db.find = Mock(return_value=mock_sessions)

        # Get active sessions
        sessions = await conversation_manager.get_active_sessions("test-user-456")

        # Assertions
        assert len(sessions) == 1
        assert sessions[0].id == "session-1"
        assert sessions[0].user_id == "test-user-456"
        assert sessions[0].is_active is True

    @pytest.mark.asyncio
    async def test_end_session(self, conversation_manager, sample_conversation_session):
        """Test ending a conversation session."""
        # Store session
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        # End session
        summary = await conversation_manager.end_session(sample_conversation_session.id)

        # Assertions
        assert summary is not None
        assert summary.session_id == sample_conversation_session.id
        assert summary.section == sample_conversation_session.section
        assert summary.total_messages == len(sample_conversation_session.messages)
        assert (
            summary.suggestions_generated
            == sample_conversation_session.total_suggestions
        )
        assert (
            summary.suggestions_applied
            == sample_conversation_session.applied_suggestions
        )

        # Verify session is no longer active
        assert (
            sample_conversation_session.id not in conversation_manager.active_sessions
        )
        assert sample_conversation_session.is_active is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, conversation_manager):
        """Test cleanup of expired sessions."""
        # Create expired session
        expired_session = ConversationSession(
            resume_id="test-resume-123",
            user_id="test-user-456",
            section="work_experience",
            title="Test Session",
        )
        expired_session.last_activity = datetime.utcnow().replace(year=2020)  # Very old

        conversation_manager.active_sessions[expired_session.id] = expired_session
        conversation_manager.end_session = AsyncMock()

        # Run cleanup
        await conversation_manager.cleanup_expired_sessions()

        # Verify end_session was called
        conversation_manager.end_session.assert_called_once_with(expired_session.id)

    @pytest.mark.asyncio
    async def test_generate_initial_message(
        self, conversation_manager, sample_conversation_session
    ):
        """Test initial message generation."""
        # Test the private method
        response = await conversation_manager._generate_initial_message(
            sample_conversation_session, "openai", {}
        )

        # Assertions
        assert response is not None
        assert "Work Experience" in response.message
        assert "resume assistant" in response.message.lower()
        assert len(response.follow_up_questions) > 0

    @pytest.mark.asyncio
    async def test_generate_ai_response(
        self, conversation_manager, sample_conversation_session
    ):
        """Test AI response generation."""
        # Mock section suggestions
        conversation_manager._generate_section_suggestions = AsyncMock(
            return_value=[
                Suggestion(
                    type="content",
                    title="Test suggestion",
                    description="Test description",
                    impact_score=0.8,
                    reasoning="Test reasoning",
                    section="work_experience",
                    confidence=0.9,
                )
            ]
        )

        # Generate response
        response = await conversation_manager._generate_ai_response(
            sample_conversation_session, "Help me improve my resume", "openai", {}
        )

        # Assertions
        assert response is not None
        assert "work_experience" in response.message
        assert len(response.suggestions) == 1
        assert response.confidence > 0

    def test_build_conversation_context(
        self, conversation_manager, sample_conversation_session
    ):
        """Test conversation context building."""
        # Add some messages to session
        sample_conversation_session.messages = [
            Message(
                session_id=sample_conversation_session.id, role="user", content="Hello"
            ),
            Message(
                session_id=sample_conversation_session.id,
                role="assistant",
                content="Hi there!",
            ),
        ]

        # Build context
        context = conversation_manager._build_conversation_context(
            sample_conversation_session, "Current message"
        )

        # Assertions
        assert "Section: work_experience" in context
        assert "Current message: Current message" in context
        assert "Recent conversation:" in context
        assert "user: Hello" in context
        assert "assistant: Hi there!" in context

    @pytest.mark.asyncio
    async def test_generate_section_suggestions_work_experience(
        self, conversation_manager
    ):
        """Test section-specific suggestion generation for work experience."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="work_experience",
            full_resume_data={},
            user_preferences={},
        )

        suggestions = await conversation_manager._generate_section_suggestions(
            "work_experience", context
        )

        # Assertions
        assert len(suggestions) > 0
        assert suggestions[0].section == "work_experience"
        assert suggestions[0].type == "content"
        assert "action verbs" in suggestions[0].title.lower()

    @pytest.mark.asyncio
    async def test_generate_section_suggestions_skills(self, conversation_manager):
        """Test section-specific suggestion generation for skills."""
        context = ResumeContext(
            resume_id="test-resume-123",
            user_id="test-user-456",
            current_section="skills",
            full_resume_data={},
            user_preferences={},
        )

        suggestions = await conversation_manager._generate_section_suggestions(
            "skills", context
        )

        # Assertions
        assert len(suggestions) > 0
        assert suggestions[0].section == "skills"
        assert suggestions[0].type == "structure"
        assert "organize" in suggestions[0].title.lower()

    @pytest.mark.asyncio
    async def test_apply_suggestion_to_resume(self, conversation_manager):
        """Test applying suggestion to resume data."""
        suggestion = Suggestion(
            type="content",
            title="Test suggestion",
            description="Test description",
            impact_score=0.8,
            reasoning="Test reasoning",
            section="work_experience",
            confidence=0.9,
        )

        result = await conversation_manager._apply_suggestion_to_resume(
            "test-resume-123", "work_experience", suggestion, "user modifications"
        )

        # Assertions
        assert result["section"] == "work_experience"
        assert result["suggestion_applied"] == "Test suggestion"
        assert result["modifications"] == "user modifications"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_resume_data_from_store(self, conversation_manager):
        """Test getting resume data from global store."""
        # Mock the global store
        with patch(
            "services.conversation_manager.parsed_resume_store",
            {"resume": {"test": "data"}},
        ):
            result = await conversation_manager._get_resume_data(
                "test-resume-123", "test-user-456"
            )
            assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_resume_data_from_database(self, conversation_manager):
        """Test getting resume data from database fallback."""
        # Mock empty global store
        with patch("services.conversation_manager.parsed_resume_store", {}):
            # Mock database response
            conversation_manager.db.find = Mock(return_value=[{"test": "data"}])

            result = await conversation_manager._get_resume_data(
                "test-resume-123", "test-user-456"
            )
            assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_user_preferences(self, conversation_manager):
        """Test getting user preferences."""
        # Mock database response
        mock_preferences = [
            {"preference_key": "theme", "preference_value": "dark"},
            {"preference_key": "language", "preference_value": "en"},
        ]
        conversation_manager.db.find = Mock(return_value=mock_preferences)

        result = await conversation_manager._get_user_preferences("test-user-456")

        # Assertions
        assert result["theme"] == "dark"
        assert result["language"] == "en"

    @pytest.mark.asyncio
    async def test_get_user_preferences_default(self, conversation_manager):
        """Test getting default user preferences when none exist."""
        # Mock empty database response
        conversation_manager.db.find = Mock(return_value=[])
        conversation_manager.db.data = {"_default_preferences": {"theme": "light"}}

        result = await conversation_manager._get_user_preferences("test-user-456")

        # Assertions
        assert result == {"theme": "light"}

    @pytest.mark.asyncio
    async def test_get_session_from_memory(
        self, conversation_manager, sample_conversation_session
    ):
        """Test getting session from active memory."""
        # Store session in memory
        conversation_manager.active_sessions[sample_conversation_session.id] = (
            sample_conversation_session
        )

        result = await conversation_manager._get_session(sample_conversation_session.id)

        # Assertions
        assert result is not None
        assert result.id == sample_conversation_session.id

    @pytest.mark.asyncio
    async def test_get_session_from_database(
        self, conversation_manager, sample_conversation_session
    ):
        """Test getting session from database when not in memory."""
        # Store session in database
        conversation_manager.db.create(
            "conversations",
            sample_conversation_session.id,
            sample_conversation_session.model_dump(),
        )

        result = await conversation_manager._get_session(sample_conversation_session.id)

        # Assertions
        assert result is not None
        assert result.id == sample_conversation_session.id
        # Should be loaded into active sessions
        assert sample_conversation_session.id in conversation_manager.active_sessions

    @pytest.mark.asyncio
    async def test_update_session(
        self, conversation_manager, sample_conversation_session
    ):
        """Test updating session in database and memory."""
        original_activity = sample_conversation_session.last_activity

        await conversation_manager._update_session(sample_conversation_session)

        # Assertions
        assert sample_conversation_session.last_activity > original_activity
        # Should be stored in database
        stored_data = conversation_manager.db.read(
            "conversations", sample_conversation_session.id
        )
        assert stored_data is not None
        # Should be in active sessions
        assert sample_conversation_session.id in conversation_manager.active_sessions

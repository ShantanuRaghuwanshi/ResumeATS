"""
Conversation Manager Service

Manages AI conversations with context awareness across resume sections.
Handles session creation, message processing, and suggestion management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import json

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.conversation import (
    ConversationSession,
    Message,
    AIResponse,
    Suggestion,
    ResumeContext,
    ConversationSummary,
)
from models.resume import ResumeDocument, ResumeSections
from services.llm_provider import LLMProviderFactory
from database import get_database
from configs.config import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """Manages AI conversations for resume optimization"""

    def __init__(self):
        self.db = get_database()
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_timeout_minutes = 30

    async def start_section_conversation(
        self,
        resume_id: str,
        user_id: str,
        section: str,
        llm_provider: str = "openai",
        llm_config: Dict[str, Any] = None,
    ) -> ConversationSession:
        """Start a new conversation session for a specific resume section"""

        try:
            # Get resume data for context
            resume_data = await self._get_resume_data(resume_id, user_id)
            if not resume_data:
                raise ValueError(f"Resume not found: {resume_id}")

            # Create resume context
            context = ResumeContext(
                resume_id=resume_id,
                user_id=user_id,
                current_section=section,
                full_resume_data=resume_data,
                user_preferences=await self._get_user_preferences(user_id),
            )

            # Create conversation session
            session = ConversationSession(
                resume_id=resume_id,
                user_id=user_id,
                section=section,
                title=f"{section.replace('_', ' ').title()} Optimization",
                context=context,
            )

            # Store session in database and memory
            self.db.create("conversations", session.id, session.model_dump())
            self.active_sessions[session.id] = session

            # Send initial greeting message
            initial_message = await self._generate_initial_message(
                session, llm_provider, llm_config
            )
            if initial_message:
                await self.send_message(
                    session.id,
                    initial_message.content,
                    "assistant",
                    llm_provider,
                    llm_config,
                )

            logger.info(
                f"Started conversation session {session.id} for section {section}"
            )
            return session

        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            raise

    async def send_message(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        llm_provider: str = "openai",
        llm_config: Dict[str, Any] = None,
    ) -> AIResponse:
        """Send a message in a conversation and get AI response"""

        try:
            # Get or load session
            session = await self._get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Create user message
            user_message = Message(session_id=session_id, role=role, content=content)

            # Add message to session
            session.messages.append(user_message)
            session.last_activity = datetime.utcnow()

            # Generate AI response if user message
            ai_response = None
            if role == "user":
                ai_response = await self._generate_ai_response(
                    session, content, llm_provider, llm_config
                )

                # Create assistant message
                assistant_message = Message(
                    session_id=session_id,
                    role="assistant",
                    content=ai_response.message,
                    suggestions=ai_response.suggestions,
                )

                session.messages.append(assistant_message)
                session.total_suggestions += len(ai_response.suggestions)

            # Update session in database
            await self._update_session(session)

            logger.info(f"Message sent in session {session_id}")
            return ai_response or AIResponse(message="Message received", confidence=1.0)

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def apply_suggestion(
        self,
        session_id: str,
        suggestion_id: str,
        user_modifications: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply a suggestion to the resume section"""

        try:
            session = await self._get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Find the suggestion
            suggestion = None
            for message in session.messages:
                for sugg in message.suggestions:
                    if sugg.id == suggestion_id:
                        suggestion = sugg
                        break
                if suggestion:
                    break

            if not suggestion:
                raise ValueError(f"Suggestion not found: {suggestion_id}")

            # Apply the suggestion to resume data
            updated_content = await self._apply_suggestion_to_resume(
                session.context.resume_id,
                session.context.current_section,
                suggestion,
                user_modifications,
            )

            # Mark suggestion as applied
            suggestion.applied = True
            session.applied_suggestions += 1

            # Update session
            await self._update_session(session)

            # Log the application
            logger.info(f"Applied suggestion {suggestion_id} in session {session_id}")

            return {
                "success": True,
                "updated_content": updated_content,
                "suggestion": suggestion.model_dump(),
            }

        except Exception as e:
            logger.error(f"Failed to apply suggestion: {e}")
            raise

    async def get_conversation_history(self, session_id: str) -> List[Message]:
        """Get conversation history for a session"""

        try:
            session = await self._get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            return session.messages

        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise

    async def get_active_sessions(self, user_id: str) -> List[ConversationSession]:
        """Get all active sessions for a user"""

        try:
            sessions = self.db.find("conversations", user_id=user_id, is_active=True)
            return [ConversationSession(**session) for session in sessions]

        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            raise

    async def end_session(self, session_id: str) -> ConversationSummary:
        """End a conversation session and generate summary"""

        try:
            session = await self._get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Mark session as inactive
            session.is_active = False

            # Generate summary
            summary = ConversationSummary(
                session_id=session_id,
                section=session.section,
                total_messages=len(session.messages),
                suggestions_generated=session.total_suggestions,
                suggestions_applied=session.applied_suggestions,
                duration_minutes=int(
                    (session.last_activity - session.created_at).total_seconds() / 60
                ),
                created_at=session.created_at,
                last_activity=session.last_activity,
            )

            # Update session and save summary
            await self._update_session(session)
            self.db.create("conversation_summaries", session_id, summary.model_dump())

            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            logger.info(f"Ended conversation session {session_id}")
            return summary

        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            raise

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""

        try:
            cutoff_time = datetime.utcnow() - timedelta(
                minutes=self.session_timeout_minutes
            )
            expired_sessions = []

            for session_id, session in self.active_sessions.items():
                if session.last_activity < cutoff_time:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                await self.end_session(session_id)

            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")

    # Private helper methods

    async def _get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session from memory or database"""

        # Check active sessions first
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Load from database
        session_data = self.db.read("conversations", session_id)
        if session_data:
            session = ConversationSession(**session_data)
            if session.is_active:
                self.active_sessions[session_id] = session
            return session

        return None

    async def _update_session(self, session: ConversationSession):
        """Update session in database and memory"""

        session.last_activity = datetime.utcnow()
        self.db.update("conversations", session.id, session.model_dump())
        if session.is_active:
            self.active_sessions[session.id] = session

    async def _get_resume_data(
        self, resume_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get resume data from storage"""

        # For now, get from the global resume store
        # In production, this would query a proper database
        from api.v1.resume import parsed_resume_store

        resume_data = parsed_resume_store.get("resume")
        if resume_data:
            return resume_data

        # Fallback: try to load from database
        stored_resume = self.db.find("resumes", user_id=user_id, id=resume_id)
        if stored_resume:
            return stored_resume[0]

        return None

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for personalization"""

        preferences = self.db.find("user_preferences", user_id=user_id)
        if preferences:
            return {
                pref["preference_key"]: pref["preference_value"] for pref in preferences
            }

        # Return default preferences
        return self.db.data.get("_default_preferences", {})

    async def _generate_initial_message(
        self,
        session: ConversationSession,
        llm_provider: str,
        llm_config: Dict[str, Any],
    ) -> Optional[AIResponse]:
        """Generate initial greeting message for the conversation"""

        try:
            section_name = session.section.replace("_", " ").title()

            # Create context-aware greeting
            greeting_prompt = f"""
            You are an AI resume optimization assistant. You're starting a conversation to help improve the {section_name} section of a resume.
            
            Current section: {session.section}
            
            Provide a friendly, professional greeting that:
            1. Introduces yourself as a resume optimization assistant
            2. Mentions you're here to help with their {section_name} section
            3. Asks what specific aspect they'd like to work on
            4. Offers 2-3 specific suggestions for common improvements in this section
            
            Keep it conversational and helpful, not overly formal.
            """

            # Get LLM provider
            provider = LLMProviderFactory.create(llm_provider, llm_config or {})

            # For now, return a simple greeting
            # In production, this would call the LLM
            greeting = f"Hi! I'm your AI resume assistant, and I'm here to help you optimize your {section_name} section. What would you like to work on today? I can help with content improvement, keyword optimization, or formatting suggestions."

            return AIResponse(
                message=greeting,
                confidence=1.0,
                follow_up_questions=[
                    f"What's your main goal for the {section_name} section?",
                    "Are you targeting any specific job or industry?",
                    "What challenges are you facing with this section?",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to generate initial message: {e}")
            return None

    async def _generate_ai_response(
        self,
        session: ConversationSession,
        user_message: str,
        llm_provider: str,
        llm_config: Dict[str, Any],
    ) -> AIResponse:
        """Generate AI response to user message"""

        try:
            # Build conversation context
            context = self._build_conversation_context(session, user_message)

            # For now, return a simple response
            # In production, this would call the LLM with full context
            response_message = f"I understand you want to work on your {session.section} section. Let me analyze your current content and provide some suggestions."

            # Generate sample suggestions based on section
            suggestions = await self._generate_section_suggestions(
                session.section, session.context
            )

            return AIResponse(
                message=response_message,
                suggestions=suggestions,
                confidence=0.8,
                follow_up_questions=[
                    "Would you like me to focus on any specific aspect?",
                    "Do any of these suggestions resonate with you?",
                ],
            )

        except Exception as e:
            logger.error(f"Failed to generate AI response: {e}")
            # Return fallback response
            return AIResponse(
                message="I'm here to help with your resume. Could you tell me more about what you'd like to improve?",
                confidence=0.5,
            )

    def _build_conversation_context(
        self, session: ConversationSession, current_message: str
    ) -> str:
        """Build context string for LLM"""

        context_parts = [
            f"Section: {session.section}",
            f"Current message: {current_message}",
            f"Resume data: {json.dumps(session.context.full_resume_data, indent=2)}",
        ]

        # Add recent conversation history
        recent_messages = (
            session.messages[-5:] if len(session.messages) > 5 else session.messages
        )
        if recent_messages:
            context_parts.append("Recent conversation:")
            for msg in recent_messages:
                context_parts.append(f"{msg.role}: {msg.content}")

        return "\n".join(context_parts)

    async def _generate_section_suggestions(
        self, section: str, context: ResumeContext
    ) -> List[Suggestion]:
        """Generate suggestions for a specific section"""

        suggestions = []

        # Sample suggestions based on section type
        if section == "work_experience":
            suggestions.append(
                Suggestion(
                    type="content",
                    title="Use stronger action verbs",
                    description="Replace weak verbs with powerful action words that demonstrate impact",
                    impact_score=0.8,
                    reasoning="Action verbs make achievements more compelling to recruiters",
                    section=section,
                    confidence=0.9,
                )
            )

        elif section == "skills":
            suggestions.append(
                Suggestion(
                    type="structure",
                    title="Organize skills by category",
                    description="Group related skills together for better readability",
                    impact_score=0.7,
                    reasoning="Categorized skills are easier for recruiters to scan",
                    section=section,
                    confidence=0.8,
                )
            )

        return suggestions

    async def _apply_suggestion_to_resume(
        self,
        section: str,
        suggestion: Suggestion,
        user_modifications: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply suggestion to resume data"""

        # For now, return mock updated content
        # In production, this would actually modify the resume data
        return {
            "section": section,
            "suggestion_applied": suggestion.title,
            "modifications": user_modifications,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> bool:
        """Perform health check for conversation manager"""
        try:
            # Check if database is accessible
            if self.db is None:
                return False
            
            # Check if we can access active sessions
            if not hasattr(self, 'active_sessions'):
                return False
                
            # Clean up expired sessions as part of health check
            await self.cleanup_expired_sessions()
            
            return True
        except Exception as e:
            logger.error(f"ConversationManager health check failed: {e}")
            return False

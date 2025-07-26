"""
Session management service for LLM configuration and user sessions
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import json
from pathlib import Path

from app.models.session import (
    UserSession,
    LLMConfiguration,
    SessionData,
    SessionStatus,
    LLMTestRequest,
    LLMTestResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionValidationResponse,
)
from app.services.llm_provider import LLMProviderFactory
from app.database import InMemoryDatabase
from app.configs.config import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages user sessions with LLM configurations"""

    def __init__(self, db: InMemoryDatabase):
        self.db = db
        # Initialize session collections if they don't exist
        if "user_sessions" not in self.db.data:
            self.db.data["user_sessions"] = {}
        if "session_data" not in self.db.data:
            self.db.data["session_data"] = {}

        # Session cleanup interval (in hours)
        self.cleanup_interval_hours = 6
        self.default_session_duration_hours = 24

    async def test_llm_configuration(
        self, test_request: LLMTestRequest
    ) -> LLMTestResponse:
        """Test LLM configuration before creating session"""
        start_time = datetime.now()

        try:
            # Create temporary LLM configuration
            config_dict = {
                "api_key": test_request.api_key,
                "base_url": test_request.base_url,
                "model": test_request.model_name,
            }

            logger.info(
                f"Testing LLM configuration: {test_request.provider.value} with model {test_request.model_name}"
            )

            # Create provider instance
            provider = LLMProviderFactory.create(
                test_request.provider.value, config_dict
            )

            # Test with a simple prompt
            if hasattr(provider, "generate_simple_response"):
                response = await provider.generate_simple_response(
                    test_request.test_prompt
                )
            else:
                # Fallback for providers without simple response method
                response = f"Test successful for {test_request.provider.value} with model {test_request.model_name}"

            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            return LLMTestResponse(
                success=True,
                response_text=response,
                latency_ms=latency_ms,
                provider_info={
                    "provider": test_request.provider.value,
                    "model": test_request.model_name,
                    "temperature": test_request.temperature,
                },
            )

        except Exception as e:
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"LLM configuration test failed: {str(e)}")
            return LLMTestResponse(
                success=False, error_message=str(e), latency_ms=latency_ms
            )

    async def create_session(
        self,
        request: SessionCreateRequest,
        device_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> SessionCreateResponse:
        """Create a new user session with LLM configuration"""

        try:
            # Generate session ID
            session_id = str(uuid.uuid4())

            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=request.session_duration_hours
            )

            # Create session
            session = UserSession(
                session_id=session_id,
                llm_config=request.llm_config,
                device_id=device_id or request.device_id,
                user_agent=user_agent,
                ip_address=ip_address,
                expires_at=expires_at,
                metadata=request.metadata,
            )

            # Create session data
            session_data = SessionData(session_id=session_id)

            # Store in database
            self.db.data["user_sessions"][session_id] = session.model_dump()
            self.db.data["session_data"][session_id] = session_data.model_dump()

            # Save to disk
            self.db.save_data()

            logger.info(f"Created new session: {session_id}")

            return SessionCreateResponse(
                session_id=session_id,
                status="created",
                expires_at=expires_at,
                message="Session created successfully",
            )

        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            raise Exception(f"Failed to create session: {str(e)}")

    async def validate_session(self, session_id: str) -> SessionValidationResponse:
        """Validate and return session information"""

        try:
            # Get session from database
            session_data = self.db.data["user_sessions"].get(session_id)

            if not session_data:
                return SessionValidationResponse(
                    valid=False, error_message="Session not found"
                )

            # Create session object
            session = UserSession(**session_data)
            logger.info(f"Validating session: {session_data}")

            # Check if session is valid
            if not session.is_valid():
                # Update session status if expired
                if (
                    session.expires_at
                    and datetime.now(timezone.utc) > session.expires_at
                ):
                    await self._update_session_status(session_id, SessionStatus.EXPIRED)

                return SessionValidationResponse(
                    valid=False,
                    session_id=session_id,
                    status=session.status,
                    error_message="Session is not valid or has expired",
                )

            # Update access time
            session.update_access_time()
            self.db.data["user_sessions"][session_id] = session.model_dump()
            self.db.save_data()

            return SessionValidationResponse(
                valid=True,
                session_id=session_id,
                status=session.status,
                llm_config=session.llm_config,
            )

        except Exception as e:
            logger.error(f"Session validation failed: {str(e)}")
            return SessionValidationResponse(
                valid=False, error_message=f"Session validation error: {str(e)}"
            )

    async def get_session_llm_config(
        self, session_id: str
    ) -> Optional[LLMConfiguration]:
        """Get LLM configuration for a session"""

        validation = await self.validate_session(session_id)
        if validation.valid and validation.llm_config:
            return validation.llm_config
        return None

    async def get_session_data(self, session_id: str) -> Optional[SessionData]:
        """Get session data"""

        # First validate session
        validation = await self.validate_session(session_id)
        if not validation.valid:
            return None

        session_data = self.db.data["session_data"].get(session_id)
        if session_data:
            return SessionData(**session_data)
        return None

    async def update_session_data(self, session_id: str, update_func) -> bool:
        """Update session data using a callback function"""

        try:
            session_data = await self.get_session_data(session_id)
            if not session_data:
                return False

            # Apply update function
            update_func(session_data)

            # Save back to database
            self.db.data["session_data"][session_id] = session_data.dict()
            self.db.save_data()

            return True

        except Exception as e:
            logger.error(f"Failed to update session data: {str(e)}")
            return False

    async def add_resume_to_session(self, session_id: str, resume_id: str) -> bool:
        """Add resume to session data"""

        def update_func(session_data: SessionData):
            session_data.add_resume(resume_id)

        return await self.update_session_data(session_id, update_func)

    async def add_conversation_to_session(
        self, session_id: str, conversation_id: str
    ) -> bool:
        """Add conversation to session data"""

        def update_func(session_data: SessionData):
            session_data.add_conversation(conversation_id)

        return await self.update_session_data(session_id, update_func)

    async def add_optimization_to_session(
        self, session_id: str, optimization_id: str
    ) -> bool:
        """Add optimization to session data"""

        def update_func(session_data: SessionData):
            session_data.add_optimization(optimization_id)

        return await self.update_session_data(session_id, update_func)

    async def add_job_analysis_to_session(
        self, session_id: str, analysis_id: str
    ) -> bool:
        """Add job analysis to session data"""

        def update_func(session_data: SessionData):
            session_data.add_job_analysis(analysis_id)

        return await self.update_session_data(session_id, update_func)

    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session"""

        try:
            await self._update_session_status(session_id, SessionStatus.TERMINATED)
            logger.info(f"Terminated session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate session: {str(e)}")
            return False

    async def list_active_sessions(
        self, device_id: Optional[str] = None
    ) -> List[UserSession]:
        """List active sessions, optionally filtered by device"""

        sessions = []
        for session_data in self.db.data["user_sessions"].values():
            session = UserSession(**session_data)
            if session.is_valid():
                if device_id is None or session.device_id == device_id:
                    sessions.append(session)

        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""

        expired_count = 0
        current_time = datetime.now(timezone.utc)

        for session_id, session_data in list(self.db.data["user_sessions"].items()):
            session = UserSession(**session_data)

            # Check if session should be cleaned up
            if (
                session.status == SessionStatus.EXPIRED
                or session.status == SessionStatus.TERMINATED
                or (session.expires_at and current_time > session.expires_at)
            ):

                # Remove session and associated data
                del self.db.data["user_sessions"][session_id]
                if session_id in self.db.data["session_data"]:
                    del self.db.data["session_data"][session_id]

                expired_count += 1

        if expired_count > 0:
            self.db.save_data()
            logger.info(f"Cleaned up {expired_count} expired sessions")

        return expired_count

    async def _update_session_status(self, session_id: str, status: SessionStatus):
        """Update session status"""

        if session_id in self.db.data["user_sessions"]:
            self.db.data["user_sessions"][session_id]["status"] = status.value
            self.db.save_data()


# Global session manager instance
session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global session_manager
    if session_manager is None:
        from app.database import InMemoryDatabase

        db = InMemoryDatabase()
        session_manager = SessionManager(db)
    return session_manager


def init_session_manager(db: InMemoryDatabase) -> SessionManager:
    """Initialize session manager with specific database instance"""
    global session_manager
    session_manager = SessionManager(db)
    return session_manager

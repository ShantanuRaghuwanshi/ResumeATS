"""
Session middleware for LLM configuration management
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional, Set
import logging

from app.services.session_manager import get_session_manager
from app.models.session import SessionValidationResponse

logger = logging.getLogger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce LLM session configuration for protected endpoints"""

    def __init__(self, app, protected_paths: Optional[Set[str]] = None):
        super().__init__(app)

        # Default protected paths - all API endpoints except session management
        self.protected_paths = protected_paths or {
            "/api/v1/resume",
            "/api/v1/upload_resume",  # File upload endpoint
            "/api/v1/optimize_resume",  # Resume optimization endpoint
            "/api/v1/conversation",
            "/api/v1/section-optimization",
            "/api/v1/job-analysis",
            "/api/v1/feedback",
            "/api/v1/version-management",
            "/api/v1/export",
        }

        # Paths that are always allowed (don't require session)
        self.allowed_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
        }

        # Session endpoints that don't require existing session
        self.session_paths = {
            "/api/v1/session",
            "/api/v1/session/",
            "/api/v1/session/test-config",
            "/api/v1/session/create",
            "/api/v1/session/list",
        }

        # Monitoring and security endpoints
        self.system_paths = {
            "/api/v1/monitoring",
            "/api/v1/security",
        }

        try:
            self.session_manager = get_session_manager()
            logger.info("SessionMiddleware initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SessionMiddleware: {e}")
            raise

    async def dispatch(self, request: Request, call_next):
        """Process each request through the session middleware"""

        # Always allow OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip middleware for certain paths
        if not self._requires_session_validation(request.url.path):
            return await call_next(request)

        # Extract session ID from request
        session_id = self._extract_session_id(request)

        if not session_id:
            logger.warning(
                f"No session ID found for protected path: {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "missing_session",
                    "message": "Session ID is required",
                    "detail": "Valid session required",
                },
            )

        # Validate session
        validation = await self.session_manager.validate_session(session_id)

        if not validation.valid:
            logger.warning(f"Invalid session {session_id}: {validation.error_message}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "invalid_session",
                    "message": validation.error_message
                    or "Session is invalid or expired",
                    "detail": "Please create a new session by configuring LLM",
                },
            )

        # Add session info to request state for use in endpoints
        request.state.session_id = session_id
        request.state.session_validation = validation
        request.state.llm_config = validation.llm_config

        # Log session access
        logger.info(f"Session {session_id} accessed endpoint: {request.url.path}")

        return await call_next(request)

    def _requires_session_validation(self, path: str) -> bool:
        """Check if the path requires session validation"""

        # Special case for root path
        if path == "/":
            return False

        # Check allowed paths first (exact match or starts with)
        if path in self.allowed_paths:
            return False

        for allowed_path in self.allowed_paths:
            if path.startswith(allowed_path):
                return False

        # Check session paths
        if path in self.session_paths:
            return False

        for session_path in self.session_paths:
            if path.startswith(session_path):
                return False

        # Check system paths
        if path in self.system_paths:
            return False

        for system_path in self.system_paths:
            if path.startswith(system_path):
                return False

        # Check protected paths
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True

        # Default to requiring session for unknown API paths
        if path.startswith("/api/"):
            return True

        return False

    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request headers"""

        # Check X-Session-ID header (primary method)
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            return session_id

        # Check Authorization header as fallback (Bearer token format)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Check query parameter as last resort
        return request.query_params.get("session_id")


def get_session_from_request(request: Request) -> Optional[str]:
    """Helper function to extract session ID from request"""
    return getattr(request.state, "session_id", None)


def get_llm_config_from_request(request: Request):
    """Helper function to extract LLM config from request"""
    return getattr(request.state, "llm_config", None)


def require_session(request: Request) -> str:
    """Helper function that raises HTTPException if no valid session"""
    session_id = get_session_from_request(request)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Valid session required"
        )
    return session_id

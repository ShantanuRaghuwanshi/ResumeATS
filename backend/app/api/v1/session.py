"""
Session management API endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Depends, status, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.session import (
    LLMTestRequest,
    LLMTestResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionValidationResponse,
    UserSession,
    LLMConfiguration,
    SessionData,
)
from app.services.session_manager import get_session_manager, SessionManager
from app.middleware.session_middleware import get_session_from_request, require_session
from app.configs.logging_config import get_service_logger

logger = get_service_logger("api.session")
router = APIRouter()


def get_client_info(request: Request) -> Dict[str, Optional[str]]:
    """Extract client information from request"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "device_id": request.headers.get("X-Device-ID"),
    }


@router.post("/session/test-config", response_model=LLMTestResponse)
async def test_llm_configuration(
    test_request: LLMTestRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Test LLM configuration before creating a session.
    This endpoint validates that the LLM provider can be reached and responds correctly.
    """
    try:
        logger.info(f"Testing LLM configuration: {test_request.provider.value}")
        result = await session_manager.test_llm_configuration(test_request)

        if result.success:
            logger.info(
                f"LLM configuration test successful: {test_request.provider.value}"
            )
        else:
            logger.warning(f"LLM configuration test failed: {result.error_message}")

        return result

    except Exception as e:
        logger.error(f"LLM configuration test error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration test failed: {str(e)}",
        )


@router.post("/session/create", response_model=SessionCreateResponse)
async def create_session(
    request: Request,
    session_request: SessionCreateRequest,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Create a new session with LLM configuration.
    This should be called after successfully testing the LLM configuration.
    """
    try:
        client_info = get_client_info(request)

        logger.info(
            f"Creating session for provider: {session_request.llm_config.provider.value}"
        )

        result = await session_manager.create_session(
            session_request,
            device_id=client_info["device_id"],
            user_agent=client_info["user_agent"],
            ip_address=client_info["ip_address"],
        )

        logger.info(f"Session created successfully: {result.session_id}")
        return result

    except Exception as e:
        logger.error(f"Session creation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session creation failed: {str(e)}",
        )


@router.get("/session/validate/{session_id}", response_model=SessionValidationResponse)
async def validate_session(
    session_id: str, session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Validate a session and return its status.
    """
    try:
        result = await session_manager.validate_session(session_id)

        if result.valid:
            logger.info(f"Session validation successful: {session_id}")
        else:
            logger.warning(
                f"Session validation failed: {session_id} - {result.error_message}"
            )

        return result

    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session validation failed: {str(e)}",
        )


@router.get("/session/current", response_model=SessionValidationResponse)
async def get_current_session(
    request: Request, session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get current session information from request headers.
    """
    try:
        # Extract session ID from request
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            # Try Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_id = auth_header[7:]

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID not found in headers",
            )

        result = await session_manager.validate_session(session_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Current session retrieval error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current session: {str(e)}",
        )


@router.get("/session/{session_id}/data")
async def get_session_data(
    session_id: str, session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Get session data (resumes, conversations, etc.) for a session.
    """
    try:
        session_data = await session_manager.get_session_data(session_id)

        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or invalid",
            )

        return {
            "session_id": session_data.session_id,
            "resume_data": session_data.resume_data,
            "conversation_history": session_data.conversation_history,
            "optimization_history": session_data.optimization_history,
            "job_analyses": session_data.job_analyses,
            "user_preferences": session_data.user_preferences,
            "created_at": session_data.created_at,
            "updated_at": session_data.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session data retrieval error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session data: {str(e)}",
        )


@router.delete("/session/{session_id}")
async def terminate_session(
    session_id: str, session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Terminate a session.
    """
    try:
        success = await session_manager.terminate_session(session_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return {"message": "Session terminated successfully", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session termination error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to terminate session: {str(e)}",
        )


@router.get("/session/list")
async def list_sessions(
    device_id: Optional[str] = None,
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    List active sessions, optionally filtered by device ID.
    """
    try:
        sessions = await session_manager.list_active_sessions(device_id)

        return {
            "sessions": [
                {
                    "session_id": session.session_id,
                    "provider": session.llm_config.provider.value,
                    "model": session.llm_config.model_name,
                    "device_id": session.device_id,
                    "created_at": session.created_at,
                    "last_accessed": session.last_accessed,
                    "expires_at": session.expires_at,
                    "status": session.status.value,
                }
                for session in sessions
            ],
            "total": len(sessions),
        }

    except Exception as e:
        logger.error(f"Session listing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )


@router.post("/session/cleanup")
async def cleanup_expired_sessions(
    session_manager: SessionManager = Depends(get_session_manager),
):
    """
    Manually trigger cleanup of expired sessions.
    """
    try:
        cleaned_count = await session_manager.cleanup_expired_sessions()

        return {
            "message": "Session cleanup completed",
            "cleaned_sessions": cleaned_count,
        }

    except Exception as e:
        logger.error(f"Session cleanup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session cleanup failed: {str(e)}",
        )


# Helper endpoints for internal use (protected by session middleware)
@router.get("/session/current/llm-config")
async def get_current_llm_config(request: Request):
    """
    Get LLM configuration for current session.
    This endpoint is protected by session middleware.
    """
    session_id = require_session(request)
    llm_config = getattr(request.state, "llm_config", None)

    if not llm_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM configuration not found in session",
        )

    return {"session_id": session_id, "llm_config": llm_config.dict()}

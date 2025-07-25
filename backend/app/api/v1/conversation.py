"""
Conversation API endpoints for resume optimization chat functionality
"""

from fastapi import (
    APIRouter,
    HTTPException,
    Body,
    Query,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime

from app.services.conversation_manager import ConversationManager
from app.models.conversation import ConversationSession, Message, AIResponse
from app.configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global conversation manager instance
conversation_manager = ConversationManager()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                self.disconnect(session_id)


connection_manager = ConnectionManager()


@router.post("/conversation/start")
async def start_conversation(
    request: Request,
    resume_id: str = Body(...),
    user_id: str = Body(...),
    section: str = Body(...),
    llm_provider: str = Body("openai"),
    llm_config: Dict[str, Any] = Body({}),
):
    """Start a new conversation session for a resume section"""
    from security.middleware import llm_rate_limit
    from security.input_validation import (
        InputSanitizer,
        validate_llm_input,
        comprehensive_input_validation,
    )
    from security.audit_logging import (
        log_user_action,
        log_security_event,
        AuditEventType,
        AuditSeverity,
    )
    from security.rate_limiting import rate_limiter

    # Apply rate limiting
    await llm_rate_limit(request)

    try:
        # Validate and sanitize inputs with comprehensive validation
        resume_id = comprehensive_input_validation(resume_id, max_length=100)
        user_id = comprehensive_input_validation(user_id, max_length=100)
        section = comprehensive_input_validation(section, max_length=50)
        llm_provider = comprehensive_input_validation(llm_provider, max_length=50)

        if not all([resume_id, user_id, section]):
            raise HTTPException(status_code=400, detail="Missing required fields")

        # Validate section name
        allowed_sections = [
            "summary",
            "experience",
            "education",
            "skills",
            "projects",
            "certifications",
        ]
        if section not in allowed_sections:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={"violation": "invalid_section", "section": section},
                severity=AuditSeverity.LOW,
                success=False,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=400, detail=f"Invalid section. Allowed: {allowed_sections}"
            )

        # Log conversation start
        await log_user_action(
            "conversation_start",
            request,
            user_id=user_id,
            resource_type="conversation",
            details={
                "resume_id": resume_id,
                "section": section,
                "llm_provider": llm_provider,
            },
        )

        session = await conversation_manager.start_section_conversation(
            resume_id=resume_id,
            user_id=user_id,
            section=section,
            llm_provider=llm_provider,
            llm_config=llm_config,
        )

        return JSONResponse(
            {
                "success": True,
                "session": {
                    "id": session.id,
                    "section": session.section,
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "message_count": len(session.messages),
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")

        await log_security_event(
            AuditEventType.ERROR_OCCURRED,
            request,
            details={
                "operation": "conversation_start",
                "error": str(e),
                "resume_id": resume_id if "resume_id" in locals() else "unknown",
            },
            severity=AuditSeverity.HIGH,
            success=False,
            error_message=str(e),
            user_id=user_id if "user_id" in locals() else None,
        )

        raise HTTPException(status_code=500, detail="Failed to start conversation")


@router.post("/conversation/{session_id}/message")
async def send_message(
    session_id: str,
    request: Request,
    content: str = Body(...),
    llm_provider: str = Body("openai"),
    llm_config: Dict[str, Any] = Body({}),
):
    """Send a message in a conversation"""

    from security.middleware import llm_rate_limit
    from security.input_validation import (
        validate_llm_input,
        comprehensive_input_validation,
    )
    from security.audit_logging import log_user_action

    # Apply rate limiting
    await llm_rate_limit(request)

    try:
        # Validate and sanitize inputs
        session_id = comprehensive_input_validation(session_id, max_length=100)
        content = validate_llm_input(content, max_length=5000)
        llm_provider = comprehensive_input_validation(llm_provider, max_length=50)

        # Get client IP for reputation tracking
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Log the message attempt
        await log_user_action(
            "conversation_message",
            request,
            resource_type="conversation",
            resource_id=session_id,
            details={"message_length": len(content), "llm_provider": llm_provider},
        )

        response = await conversation_manager.send_message(
            session_id=session_id,
            content=content,
            role="user",
            llm_provider=llm_provider,
            llm_config=llm_config,
        )

        # Update rate limiter reputation for successful request
        rate_limiter.update_reputation(client_ip, True)

        # Send real-time update via WebSocket if connected
        await connection_manager.send_message(
            session_id,
            {
                "type": "message_response",
                "response": {
                    "message": response.message,
                    "suggestions": [s.model_dump() for s in response.suggestions],
                    "confidence": response.confidence,
                    "follow_up_questions": response.follow_up_questions,
                },
            },
        )

        return JSONResponse(
            {
                "success": True,
                "response": {
                    "message": response.message,
                    "suggestions": [s.model_dump() for s in response.suggestions],
                    "confidence": response.confidence,
                    "follow_up_questions": response.follow_up_questions,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""

    try:
        messages = await conversation_manager.get_conversation_history(session_id)

        return JSONResponse(
            {
                "success": True,
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "suggestions": [s.model_dump() for s in msg.suggestions],
                    }
                    for msg in messages
                ],
            }
        )

    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/{session_id}/suggestion/{suggestion_id}/apply")
async def apply_suggestion(
    session_id: str, suggestion_id: str, user_modifications: Optional[str] = Body(None)
):
    """Apply a suggestion to the resume"""

    try:
        result = await conversation_manager.apply_suggestion(
            session_id=session_id,
            suggestion_id=suggestion_id,
            user_modifications=user_modifications,
        )

        # Send real-time update via WebSocket
        await connection_manager.send_message(
            session_id, {"type": "suggestion_applied", "result": result}
        )

        return JSONResponse(result)

    except Exception as e:
        logger.error(f"Failed to apply suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/user/{user_id}/active")
async def get_active_sessions(user_id: str):
    """Get all active conversation sessions for a user"""

    try:
        sessions = await conversation_manager.get_active_sessions(user_id)

        return JSONResponse(
            {
                "success": True,
                "sessions": [
                    {
                        "id": session.id,
                        "section": session.section,
                        "title": session.title,
                        "created_at": session.created_at.isoformat(),
                        "last_activity": session.last_activity.isoformat(),
                        "message_count": len(session.messages),
                        "suggestions_total": session.total_suggestions,
                        "suggestions_applied": session.applied_suggestions,
                    }
                    for session in sessions
                ],
            }
        )

    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation/{session_id}/end")
async def end_conversation(session_id: str):
    """End a conversation session"""

    try:
        summary = await conversation_manager.end_session(session_id)

        # Notify via WebSocket
        await connection_manager.send_message(
            session_id, {"type": "session_ended", "summary": summary.model_dump()}
        )

        # Disconnect WebSocket
        connection_manager.disconnect(session_id)

        return JSONResponse({"success": True, "summary": summary.model_dump()})

    except Exception as e:
        logger.error(f"Failed to end conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current status of a conversation session"""

    try:
        # Get session from conversation manager
        session = await conversation_manager._get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return JSONResponse(
            {
                "success": True,
                "status": {
                    "id": session.id,
                    "is_active": session.is_active,
                    "section": session.section,
                    "title": session.title,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "message_count": len(session.messages),
                    "suggestions_total": session.total_suggestions,
                    "suggestions_applied": session.applied_suggestions,
                    "websocket_connected": session_id
                    in connection_manager.active_connections,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/conversation/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time conversation updates"""

    try:
        await connection_manager.connect(websocket, session_id)

        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connection_established",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                if message_data.get("type") == "ping":
                    await websocket.send_text(
                        json.dumps(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
                        )
                    )

                elif message_data.get("type") == "typing":
                    # Handle typing indicators (could broadcast to other users in future)
                    pass

                elif message_data.get("type") == "message":
                    # Handle chat messages via WebSocket
                    content = message_data.get("content", "")
                    if content:
                        response = await conversation_manager.send_message(
                            session_id=session_id,
                            content=content,
                            role="user",
                            llm_provider=message_data.get("llm_provider", "openai"),
                            llm_config=message_data.get("llm_config", {}),
                        )

                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "message_response",
                                    "response": {
                                        "message": response.message,
                                        "suggestions": [
                                            s.model_dump() for s in response.suggestions
                                        ],
                                        "confidence": response.confidence,
                                        "follow_up_questions": response.follow_up_questions,
                                    },
                                }
                            )
                        )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_text(
                    json.dumps({"type": "error", "message": str(e)})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        connection_manager.disconnect(session_id)


@router.post("/conversation/cleanup")
async def cleanup_expired_sessions():
    """Cleanup expired conversation sessions (admin endpoint)"""

    try:
        await conversation_manager.cleanup_expired_sessions()

        return JSONResponse(
            {"success": True, "message": "Expired sessions cleaned up successfully"}
        )

    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/conversation/health")
async def health_check():
    """Health check for conversation service"""

    return JSONResponse(
        {
            "status": "healthy",
            "service": "conversation_api",
            "timestamp": datetime.utcnow().isoformat(),
            "active_connections": len(connection_manager.active_connections),
        }
    )

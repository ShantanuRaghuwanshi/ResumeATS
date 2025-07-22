"""
Centralized WebSocket API endpoints for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import asyncio
from datetime import datetime
import uuid

from services.websocket_manager import (
    websocket_manager,
    ConnectionType,
    WebSocketMessage,
    send_notification,
    send_progress_update,
    send_real_time_feedback,
    send_error_notification,
)
from configs.config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/{connection_type}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_type: str,
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """
    Centralized WebSocket endpoint for all real-time connections

    Connection types:
    - conversation: For chat and conversation updates
    - feedback: For real-time feedback and suggestions
    - notifications: For system notifications
    - general: For general real-time updates
    """

    # Generate unique connection ID
    connection_id = f"{connection_type}_{uuid.uuid4().hex[:8]}"

    try:
        # Validate connection type
        try:
            conn_type = ConnectionType(connection_type)
        except ValueError:
            await websocket.close(code=4000, reason="Invalid connection type")
            return

        # Connect to WebSocket manager
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            connection_type=conn_type,
            session_id=session_id,
            user_id=user_id,
        )

        # Send connection confirmation
        await connection.send_json(
            {
                "type": "connection_established",
                "connection_id": connection_id,
                "connection_type": connection_type,
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Handle different message types
                message_type = message_data.get("type", "")

                if message_type == "ping":
                    # Handle ping-pong for connection health
                    await websocket_manager.handle_ping_pong(connection_id)

                elif message_type == "subscribe":
                    # Handle subscription to specific events
                    await handle_subscription(connection_id, message_data)

                elif message_type == "unsubscribe":
                    # Handle unsubscription from events
                    await handle_unsubscription(connection_id, message_data)

                elif message_type == "request_status":
                    # Send current status/stats
                    await send_status_update(connection_id)

                elif message_type == "heartbeat":
                    # Update last activity
                    connection.last_activity = datetime.utcnow()

                else:
                    # Forward to specific handlers based on connection type
                    await handle_connection_specific_message(connection, message_data)

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await send_error_notification(
                    connection_id, "invalid_json", "Invalid JSON format in message"
                )
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                await send_error_notification(connection_id, "message_error", str(e))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        websocket_manager.disconnect(connection_id)


async def handle_subscription(connection_id: str, message_data: dict):
    """Handle subscription requests"""

    event_types = message_data.get("events", [])

    # For now, just acknowledge subscription
    # In future, could implement event filtering
    response = WebSocketMessage(
        type="subscription_confirmed",
        data={
            "events": event_types,
            "message": f"Subscribed to {len(event_types)} event types",
        },
    )

    await websocket_manager.send_to_connection(connection_id, response)


async def handle_unsubscription(connection_id: str, message_data: dict):
    """Handle unsubscription requests"""

    event_types = message_data.get("events", [])

    response = WebSocketMessage(
        type="unsubscription_confirmed",
        data={
            "events": event_types,
            "message": f"Unsubscribed from {len(event_types)} event types",
        },
    )

    await websocket_manager.send_to_connection(connection_id, response)


async def send_status_update(connection_id: str):
    """Send current system status"""

    stats = websocket_manager.get_connection_stats()

    response = WebSocketMessage(
        type="status_update",
        data={"connection_stats": stats, "server_time": datetime.utcnow().isoformat()},
    )

    await websocket_manager.send_to_connection(connection_id, response)


async def handle_connection_specific_message(connection, message_data: dict):
    """Handle messages specific to connection type"""

    connection_type = connection.connection_type
    message_type = message_data.get("type", "")

    if connection_type == ConnectionType.CONVERSATION:
        await handle_conversation_message(connection, message_data)

    elif connection_type == ConnectionType.FEEDBACK:
        await handle_feedback_message(connection, message_data)

    elif connection_type == ConnectionType.NOTIFICATIONS:
        await handle_notification_message(connection, message_data)

    elif connection_type == ConnectionType.GENERAL:
        await handle_general_message(connection, message_data)


async def handle_conversation_message(connection, message_data: dict):
    """Handle conversation-specific messages"""

    message_type = message_data.get("type", "")

    if message_type == "typing_start":
        # Broadcast typing indicator to other users in session
        if connection.session_id:
            typing_message = WebSocketMessage(
                type="user_typing",
                data={
                    "user_id": connection.user_id,
                    "session_id": connection.session_id,
                    "typing": True,
                },
                session_id=connection.session_id,
            )
            await websocket_manager.send_to_session(
                connection.session_id, typing_message
            )

    elif message_type == "typing_stop":
        # Stop typing indicator
        if connection.session_id:
            typing_message = WebSocketMessage(
                type="user_typing",
                data={
                    "user_id": connection.user_id,
                    "session_id": connection.session_id,
                    "typing": False,
                },
                session_id=connection.session_id,
            )
            await websocket_manager.send_to_session(
                connection.session_id, typing_message
            )

    elif message_type == "request_history":
        # Request conversation history
        # This would integrate with conversation_manager
        pass


async def handle_feedback_message(connection, message_data: dict):
    """Handle feedback-specific messages"""

    message_type = message_data.get("type", "")

    if message_type == "request_feedback":
        # Request real-time feedback
        section = message_data.get("section", "")
        content = message_data.get("content", "")

        if section and content and connection.session_id:
            # This would integrate with feedback_analyzer
            feedback_data = {
                "section": section,
                "content_length": len(content),
                "word_count": len(content.split()),
                "timestamp": datetime.utcnow().isoformat(),
            }

            await send_real_time_feedback(
                connection.session_id, "content_analysis", feedback_data
            )

    elif message_type == "set_context":
        # Set context for feedback analysis
        context = message_data.get("context", {})
        # Store context for this connection
        pass


async def handle_notification_message(connection, message_data: dict):
    """Handle notification-specific messages"""

    message_type = message_data.get("type", "")

    if message_type == "mark_read":
        # Mark notifications as read
        notification_ids = message_data.get("notification_ids", [])
        # Update notification status
        pass

    elif message_type == "get_unread_count":
        # Get unread notification count
        if connection.user_id:
            # This would integrate with notification system
            unread_count = 0  # Placeholder

            response = WebSocketMessage(
                type="unread_count",
                data={"count": unread_count},
                user_id=connection.user_id,
            )

            await websocket_manager.send_to_connection(
                connection.connection_id, response
            )


async def handle_general_message(connection, message_data: dict):
    """Handle general messages"""

    message_type = message_data.get("type", "")

    if message_type == "echo":
        # Echo message back (for testing)
        echo_data = message_data.get("data", {})

        response = WebSocketMessage(type="echo_response", data=echo_data)

        await websocket_manager.send_to_connection(connection.connection_id, response)


# Health check endpoint
@router.get("/websocket/health")
async def websocket_health_check():
    """Health check for WebSocket service"""

    stats = websocket_manager.get_connection_stats()

    return {
        "status": "healthy",
        "service": "websocket_api",
        "timestamp": datetime.utcnow().isoformat(),
        "connection_stats": stats,
    }


# Admin endpoints for WebSocket management
@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get detailed WebSocket statistics (admin endpoint)"""

    return {
        "success": True,
        "stats": websocket_manager.get_connection_stats(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/websocket/cleanup")
async def cleanup_inactive_connections():
    """Cleanup inactive WebSocket connections (admin endpoint)"""

    await websocket_manager.cleanup_inactive_connections()

    return {
        "success": True,
        "message": "Inactive connections cleaned up",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/websocket/broadcast")
async def broadcast_message(
    message_type: str,
    message_data: dict,
    connection_type: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Broadcast message to WebSocket connections (admin endpoint)"""

    message = WebSocketMessage(
        type=message_type, data=message_data, user_id=user_id, session_id=session_id
    )

    sent_count = 0

    if user_id:
        sent_count = await websocket_manager.send_to_user(user_id, message)
    elif session_id:
        sent_count = await websocket_manager.send_to_session(session_id, message)
    elif connection_type:
        try:
            conn_type = ConnectionType(connection_type)
            sent_count = await websocket_manager.broadcast_to_type(conn_type, message)
        except ValueError:
            return {"success": False, "error": "Invalid connection type"}
    else:
        sent_count = await websocket_manager.broadcast_to_all(message)

    return {
        "success": True,
        "message": f"Message sent to {sent_count} connections",
        "sent_count": sent_count,
    }

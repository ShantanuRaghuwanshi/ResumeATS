"""
Centralized WebSocket connection manager for real-time updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional, Set
import json
import asyncio
from datetime import datetime
from enum import Enum
import logging

from configs.config import get_logger

logger = get_logger(__name__)


class ConnectionType(str, Enum):
    """Types of WebSocket connections"""

    CONVERSATION = "conversation"
    FEEDBACK = "feedback"
    NOTIFICATIONS = "notifications"
    GENERAL = "general"


class WebSocketMessage:
    """WebSocket message structure"""

    def __init__(
        self,
        type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.type = type
        self.data = data
        self.session_id = session_id
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
        }


class WebSocketConnection:
    """Individual WebSocket connection wrapper"""

    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        connection_type: ConnectionType,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.connection_type = connection_type
        self.session_id = session_id
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_active = True

    async def send_message(self, message: WebSocketMessage) -> bool:
        """Send message through WebSocket connection"""
        try:
            await self.websocket.send_text(json.dumps(message.to_dict()))
            self.last_activity = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            self.is_active = False
            return False

    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Send JSON data through WebSocket connection"""
        try:
            await self.websocket.send_text(json.dumps(data))
            self.last_activity = datetime.utcnow()
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket JSON: {e}")
            self.is_active = False
            return False


class WebSocketManager:
    """Centralized WebSocket connection manager"""

    def __init__(self):
        # Store connections by connection_id
        self.connections: Dict[str, WebSocketConnection] = {}

        # Index connections by different criteria for efficient lookup
        self.connections_by_session: Dict[str, Set[str]] = {}
        self.connections_by_user: Dict[str, Set[str]] = {}
        self.connections_by_type: Dict[ConnectionType, Set[str]] = {
            ConnectionType.CONVERSATION: set(),
            ConnectionType.FEEDBACK: set(),
            ConnectionType.NOTIFICATIONS: set(),
            ConnectionType.GENERAL: set(),
        }

        # Connection statistics
        self.total_connections = 0
        self.active_connections = 0

        # Message queue for offline users
        self.message_queue: Dict[str, List[WebSocketMessage]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        connection_type: ConnectionType,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> WebSocketConnection:
        """Accept and register a new WebSocket connection"""

        try:
            await websocket.accept()

            connection = WebSocketConnection(
                websocket=websocket,
                connection_id=connection_id,
                connection_type=connection_type,
                session_id=session_id,
                user_id=user_id,
            )

            # Store connection
            self.connections[connection_id] = connection

            # Update indexes
            if session_id:
                if session_id not in self.connections_by_session:
                    self.connections_by_session[session_id] = set()
                self.connections_by_session[session_id].add(connection_id)

            if user_id:
                if user_id not in self.connections_by_user:
                    self.connections_by_user[user_id] = set()
                self.connections_by_user[user_id].add(connection_id)

            self.connections_by_type[connection_type].add(connection_id)

            # Update statistics
            self.total_connections += 1
            self.active_connections += 1

            logger.info(f"WebSocket connected: {connection_id} ({connection_type})")

            # Send queued messages if any
            if user_id and user_id in self.message_queue:
                for message in self.message_queue[user_id]:
                    await connection.send_message(message)
                del self.message_queue[user_id]

            return connection

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            raise

    def disconnect(self, connection_id: str):
        """Disconnect and cleanup a WebSocket connection"""

        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]

        # Remove from indexes
        if connection.session_id:
            if connection.session_id in self.connections_by_session:
                self.connections_by_session[connection.session_id].discard(
                    connection_id
                )
                if not self.connections_by_session[connection.session_id]:
                    del self.connections_by_session[connection.session_id]

        if connection.user_id:
            if connection.user_id in self.connections_by_user:
                self.connections_by_user[connection.user_id].discard(connection_id)
                if not self.connections_by_user[connection.user_id]:
                    del self.connections_by_user[connection.user_id]

        self.connections_by_type[connection.connection_type].discard(connection_id)

        # Remove connection
        del self.connections[connection_id]

        # Update statistics
        self.active_connections -= 1

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_to_connection(
        self, connection_id: str, message: WebSocketMessage
    ) -> bool:
        """Send message to a specific connection"""

        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        return await connection.send_message(message)

    async def send_to_session(self, session_id: str, message: WebSocketMessage) -> int:
        """Send message to all connections in a session"""

        if session_id not in self.connections_by_session:
            return 0

        sent_count = 0
        connection_ids = list(self.connections_by_session[session_id])

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def send_to_user(
        self, user_id: str, message: WebSocketMessage, queue_if_offline: bool = True
    ) -> int:
        """Send message to all connections for a user"""

        if user_id not in self.connections_by_user:
            if queue_if_offline:
                if user_id not in self.message_queue:
                    self.message_queue[user_id] = []
                self.message_queue[user_id].append(message)
            return 0

        sent_count = 0
        connection_ids = list(self.connections_by_user[user_id])

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_to_type(
        self, connection_type: ConnectionType, message: WebSocketMessage
    ) -> int:
        """Broadcast message to all connections of a specific type"""

        sent_count = 0
        connection_ids = list(self.connections_by_type[connection_type])

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """Broadcast message to all active connections"""

        sent_count = 0
        connection_ids = list(self.connections.keys())

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1

        return sent_count

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""

        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "connections_by_type": {
                conn_type.value: len(connection_ids)
                for conn_type, connection_ids in self.connections_by_type.items()
            },
            "active_sessions": len(self.connections_by_session),
            "active_users": len(self.connections_by_user),
            "queued_messages": sum(
                len(messages) for messages in self.message_queue.values()
            ),
        }

    def get_user_connections(self, user_id: str) -> List[WebSocketConnection]:
        """Get all connections for a user"""

        if user_id not in self.connections_by_user:
            return []

        return [
            self.connections[connection_id]
            for connection_id in self.connections_by_user[user_id]
            if connection_id in self.connections
        ]

    def get_session_connections(self, session_id: str) -> List[WebSocketConnection]:
        """Get all connections for a session"""

        if session_id not in self.connections_by_session:
            return []

        return [
            self.connections[connection_id]
            for connection_id in self.connections_by_session[session_id]
            if connection_id in self.connections
        ]

    async def cleanup_inactive_connections(self):
        """Clean up inactive connections"""

        inactive_connections = []

        for connection_id, connection in self.connections.items():
            if not connection.is_active:
                inactive_connections.append(connection_id)

        for connection_id in inactive_connections:
            self.disconnect(connection_id)

        logger.info(f"Cleaned up {len(inactive_connections)} inactive connections")

    async def handle_ping_pong(self, connection_id: str) -> bool:
        """Handle ping-pong for connection health check"""

        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]

        try:
            await connection.send_json(
                {"type": "pong", "timestamp": datetime.utcnow().isoformat()}
            )
            return True
        except Exception as e:
            logger.error(f"Ping-pong failed for connection {connection_id}: {e}")
            self.disconnect(connection_id)
            return False


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


# Utility functions for common WebSocket operations
async def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
):
    """Send notification to user"""

    notification_message = WebSocketMessage(
        type="notification",
        data={
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
        },
        user_id=user_id,
    )

    return await websocket_manager.send_to_user(user_id, notification_message)


async def send_progress_update(
    session_id: str,
    operation: str,
    progress: float,
    status: str,
    details: Optional[str] = None,
):
    """Send progress update for long-running operations"""

    progress_message = WebSocketMessage(
        type="progress_update",
        data={
            "operation": operation,
            "progress": progress,
            "status": status,
            "details": details,
        },
        session_id=session_id,
    )

    return await websocket_manager.send_to_session(session_id, progress_message)


async def send_real_time_feedback(
    session_id: str, feedback_type: str, feedback_data: Dict[str, Any]
):
    """Send real-time feedback"""

    feedback_message = WebSocketMessage(
        type="real_time_feedback",
        data={"feedback_type": feedback_type, "feedback": feedback_data},
        session_id=session_id,
    )

    return await websocket_manager.send_to_session(session_id, feedback_message)


async def send_error_notification(
    connection_id: str,
    error_type: str,
    error_message: str,
    error_code: Optional[str] = None,
):
    """Send error notification"""

    error_msg = WebSocketMessage(
        type="error",
        data={
            "error_type": error_type,
            "error_message": error_message,
            "error_code": error_code,
        },
    )

    return await websocket_manager.send_to_connection(connection_id, error_msg)

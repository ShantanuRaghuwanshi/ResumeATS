"""
Audit logging system for tracking user actions and data changes
"""

import json
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum
from pathlib import Path
import aiofiles
from fastapi import Request
import hashlib
import uuid


class AuditEventType(Enum):
    """Types of audit events"""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    RESUME_UPLOAD = "resume_upload"
    RESUME_PARSE = "resume_parse"
    RESUME_OPTIMIZE = "resume_optimize"
    RESUME_EXPORT = "resume_export"
    RESUME_DELETE = "resume_delete"
    CONVERSATION_START = "conversation_start"
    CONVERSATION_MESSAGE = "conversation_message"
    SECTION_EDIT = "section_edit"
    JOB_ANALYSIS = "job_analysis"
    VERSION_CREATE = "version_create"
    VERSION_DELETE = "version_delete"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    ERROR_OCCURRED = "error_occurred"


class AuditSeverity(Enum):
    """Severity levels for audit events"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEvent:
    """Audit event data structure"""

    def __init__(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.event_type = event_type
        self.user_id = user_id
        self.session_id = session_id
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.action = action
        self.details = details or {}
        self.severity = severity
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "action": self.action,
            "details": self.details,
            "severity": self.severity.value,
            "success": self.success,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert audit event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """Audit logging system"""

    def __init__(self, log_directory: str = "data/audit_logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        self.current_log_file = None
        self.log_queue = asyncio.Queue()
        self.writer_task = None
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_files = 100

    async def start(self):
        """Start the audit logger"""
        if self.writer_task is None:
            self.writer_task = asyncio.create_task(self._log_writer())

    async def stop(self):
        """Stop the audit logger"""
        if self.writer_task:
            self.writer_task.cancel()
            try:
                await self.writer_task
            except asyncio.CancelledError:
                pass

    async def log_event(self, event: AuditEvent):
        """Log an audit event"""
        await self.log_queue.put(event)

    async def _log_writer(self):
        """Background task to write audit logs"""
        while True:
            try:
                event = await self.log_queue.get()
                await self._write_event(event)
                self.log_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error writing audit log: {e}")

    async def _write_event(self, event: AuditEvent):
        """Write a single audit event to file"""
        log_file = self._get_current_log_file()

        try:
            async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                await f.write(event.to_json() + "\n")
        except Exception as e:
            print(f"Failed to write audit log: {e}")

    def _get_current_log_file(self) -> Path:
        """Get the current log file, rotating if necessary"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_directory / f"audit_{today}.log"

        # Check if we need to rotate the file
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            # Find next available file number
            counter = 1
            while True:
                rotated_file = self.log_directory / f"audit_{today}_{counter}.log"
                if (
                    not rotated_file.exists()
                    or rotated_file.stat().st_size < self.max_file_size
                ):
                    log_file = rotated_file
                    break
                counter += 1

        # Clean up old log files
        self._cleanup_old_logs()

        return log_file

    def _cleanup_old_logs(self):
        """Remove old log files to maintain storage limits"""
        log_files = sorted(
            self.log_directory.glob("audit_*.log"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        # Keep only the most recent files
        for old_file in log_files[self.max_files :]:
            try:
                old_file.unlink()
            except Exception:
                pass

    async def search_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search audit events with filters"""
        events = []

        # Get all log files in date range
        log_files = list(self.log_directory.glob("audit_*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for log_file in log_files:
            try:
                async with aiofiles.open(log_file, "r", encoding="utf-8") as f:
                    async for line in f:
                        if len(events) >= limit:
                            break

                        try:
                            event_data = json.loads(line.strip())

                            # Apply filters
                            if (
                                event_type
                                and event_data.get("event_type") != event_type.value
                            ):
                                continue

                            if user_id and event_data.get("user_id") != user_id:
                                continue

                            if (
                                severity
                                and event_data.get("severity") != severity.value
                            ):
                                continue

                            event_time = datetime.fromisoformat(event_data["timestamp"])
                            if start_time and event_time < start_time:
                                continue

                            if end_time and event_time > end_time:
                                continue

                            events.append(event_data)

                        except json.JSONDecodeError:
                            continue

                if len(events) >= limit:
                    break

            except Exception:
                continue

        return events[:limit]


# Global audit logger instance
audit_logger = AuditLogger()


def get_request_info(request: Request) -> Dict[str, str]:
    """Extract request information for audit logging"""
    # Get client IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    # Get user agent
    user_agent = request.headers.get("User-Agent", "unknown")

    return {"ip_address": ip_address, "user_agent": user_agent}


async def log_security_event(
    event_type: AuditEventType,
    request: Request,
    details: Optional[Dict[str, Any]] = None,
    severity: AuditSeverity = AuditSeverity.MEDIUM,
    success: bool = True,
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
):
    """Log a security-related audit event"""
    request_info = get_request_info(request)

    event = AuditEvent(
        event_type=event_type,
        user_id=user_id,
        ip_address=request_info["ip_address"],
        user_agent=request_info["user_agent"],
        resource_id=resource_id,
        details=details,
        severity=severity,
        success=success,
        error_message=error_message,
    )

    await audit_logger.log_event(event)


async def log_user_action(
    action: str,
    request: Request,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Log a user action audit event"""
    request_info = get_request_info(request)

    event = AuditEvent(
        event_type=AuditEventType.USER_LOGIN,  # Will be overridden based on action
        user_id=user_id,
        ip_address=request_info["ip_address"],
        user_agent=request_info["user_agent"],
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        details=details,
        success=success,
        error_message=error_message,
    )

    await audit_logger.log_event(event)


async def log_llm_interaction(
    request: Request,
    provider: str,
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Log LLM interaction for monitoring and cost tracking"""
    request_info = get_request_info(request)

    details = {
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": cost,
    }

    event = AuditEvent(
        event_type=AuditEventType.LLM_REQUEST,
        user_id=user_id,
        ip_address=request_info["ip_address"],
        user_agent=request_info["user_agent"],
        details=details,
        success=success,
        error_message=error_message,
    )

    await audit_logger.log_event(event)


# Audit logging middleware
class AuditMiddleware:
    """Middleware for automatic audit logging"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        start_time = datetime.utcnow()

        # Capture response
        response_body = b""
        status_code = 200

        async def send_wrapper(message):
            nonlocal response_body, status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                response_body += message.get("body", b"")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)

            # Log successful request
            if status_code >= 400:
                await log_security_event(
                    AuditEventType.ERROR_OCCURRED,
                    request,
                    details={
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": status_code,
                        "response_time": (
                            datetime.utcnow() - start_time
                        ).total_seconds(),
                    },
                    severity=(
                        AuditSeverity.MEDIUM
                        if status_code < 500
                        else AuditSeverity.HIGH
                    ),
                    success=False,
                )

        except Exception as e:
            # Log exception
            await log_security_event(
                AuditEventType.ERROR_OCCURRED,
                request,
                details={
                    "method": request.method,
                    "path": str(request.url.path),
                    "exception": str(e),
                    "response_time": (datetime.utcnow() - start_time).total_seconds(),
                },
                severity=AuditSeverity.HIGH,
                success=False,
                error_message=str(e),
            )
            raise

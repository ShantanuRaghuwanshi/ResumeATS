"""
Comprehensive security service that integrates all security features
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from fastapi import Request, HTTPException
import json
import hashlib

from .config import get_security_config, get_validation_rules, get_file_security_config
from .input_validation import (
    InputSanitizer,
    comprehensive_input_validation,
    validate_resume_upload,
    validate_llm_input,
    validate_json_input,
    validate_file_content,
)
from .rate_limiting import rate_limiter, get_client_identifier
from .audit_logging import (
    audit_logger,
    log_security_event,
    log_user_action,
    log_llm_interaction,
    AuditEventType,
    AuditSeverity,
)
from .monitoring import security_monitor, analyze_request_security
from .authentication import auth_service, session_manager


class SecurityService:
    """Comprehensive security service"""

    def __init__(self):
        self.config = get_security_config()
        self.blocked_patterns = set()
        self.suspicious_activities = {}

    async def validate_and_sanitize_input(
        self,
        data: Any,
        data_type: str = "general_text",
        request: Optional[Request] = None,
    ) -> Any:
        """Validate and sanitize input data based on type"""

        if not self.config.enable_input_validation:
            return data

        validation_rules = get_validation_rules(data_type)

        try:
            if isinstance(data, str):
                return comprehensive_input_validation(
                    data,
                    max_length=validation_rules["max_length"],
                    check_sql=validation_rules["check_sql"],
                    check_xss=validation_rules["check_xss"],
                    check_path_traversal=validation_rules["check_path_traversal"],
                    check_command_injection=validation_rules["check_command_injection"],
                )
            elif isinstance(data, dict):
                return self._validate_dict_recursive(data, validation_rules)
            elif isinstance(data, list):
                return [
                    await self.validate_and_sanitize_input(item, data_type, request)
                    for item in data
                ]
            else:
                return data

        except HTTPException as e:
            # Log validation failure
            if request:
                await log_security_event(
                    AuditEventType.SECURITY_VIOLATION,
                    request,
                    details={
                        "violation": "input_validation_failed",
                        "data_type": data_type,
                        "error": e.detail,
                    },
                    severity=AuditSeverity.MEDIUM,
                    success=False,
                    error_message=e.detail,
                )
            raise

    def _validate_dict_recursive(self, data: dict, validation_rules: dict) -> dict:
        """Recursively validate dictionary data"""
        validated = {}

        for key, value in data.items():
            if isinstance(value, str) and value:
                validated[key] = comprehensive_input_validation(
                    value,
                    max_length=validation_rules["max_length"],
                    check_sql=validation_rules["check_sql"],
                    check_xss=validation_rules["check_xss"],
                    check_path_traversal=validation_rules["check_path_traversal"],
                    check_command_injection=validation_rules["check_command_injection"],
                )
            elif isinstance(value, dict):
                validated[key] = self._validate_dict_recursive(value, validation_rules)
            elif isinstance(value, list):
                validated[key] = [
                    (
                        comprehensive_input_validation(
                            item,
                            max_length=validation_rules["max_length"],
                            check_sql=validation_rules["check_sql"],
                            check_xss=validation_rules["check_xss"],
                            check_path_traversal=validation_rules[
                                "check_path_traversal"
                            ],
                            check_command_injection=validation_rules[
                                "check_command_injection"
                            ],
                        )
                        if isinstance(item, str) and item
                        else (
                            self._validate_dict_recursive(item, validation_rules)
                            if isinstance(item, dict)
                            else item
                        )
                    )
                    for item in value
                ]
            else:
                validated[key] = value

        return validated

    async def validate_file_upload(
        self,
        file_content: bytes,
        filename: str,
        request: Request,
        user_id: Optional[str] = None,
    ) -> bool:
        """Validate uploaded file for security"""

        try:
            # Basic validation
            validate_resume_upload(file_content, filename)

            # Get file extension
            file_ext = filename.lower().split(".")[-1] if "." in filename else ""
            file_config = get_file_security_config(file_ext)

            # Check file size against specific limits
            if len(file_content) > file_config["max_size"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"File size exceeds limit for {file_ext} files",
                )

            # Validate file content
            if file_config["allowed_mime_types"]:
                if not validate_file_content(
                    file_content, file_config["allowed_mime_types"]
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="File content does not match expected format",
                    )

            # Log successful upload validation
            await log_user_action(
                "file_upload_validated",
                request,
                user_id=user_id,
                resource_type="file",
                resource_id=filename,
                details={
                    "filename": filename,
                    "file_size": len(file_content),
                    "file_type": file_ext,
                },
                success=True,
            )

            return True

        except HTTPException as e:
            # Log validation failure
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={
                    "violation": "file_upload_validation_failed",
                    "filename": filename,
                    "file_size": len(file_content),
                    "error": e.detail,
                },
                severity=AuditSeverity.HIGH,
                success=False,
                user_id=user_id,
                error_message=e.detail,
            )
            raise

    async def check_rate_limit(
        self, request: Request, limit_type: str = "api", user_id: Optional[str] = None
    ) -> bool:
        """Check rate limit for request"""

        if not self.config.enable_rate_limiting:
            return True

        client_id = get_client_identifier(request)

        # Get appropriate rate limit
        from .config import get_rate_limit_for_endpoint

        limit, window = get_rate_limit_for_endpoint(
            limit_type, self.config.security_level
        )

        is_allowed, rate_info = rate_limiter.is_allowed(
            f"{limit_type}:{client_id}", limit, window
        )

        if not is_allowed:
            # Log rate limit violation
            await log_security_event(
                AuditEventType.RATE_LIMIT_EXCEEDED,
                request,
                details={
                    "limit_type": limit_type,
                    "limit": rate_info["limit"],
                    "remaining": rate_info["remaining"],
                    "retry_after": rate_info["retry_after"],
                },
                severity=AuditSeverity.MEDIUM,
                success=False,
                user_id=user_id,
                error_message=f"Rate limit exceeded for {limit_type}",
            )

            # Update reputation
            rate_limiter.update_reputation(client_id, False, "rate_limit")

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {limit_type}. Try again in {rate_info['retry_after']} seconds.",
                headers={
                    "Retry-After": str(rate_info["retry_after"]),
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                },
            )

        return True

    async def validate_llm_request(
        self, prompt: str, request: Request, user_id: Optional[str] = None
    ) -> str:
        """Validate LLM request for security"""

        # Check rate limit first
        await self.check_rate_limit(request, "llm", user_id)

        # Validate and sanitize input
        validated_prompt = validate_llm_input(
            prompt, max_length=self.config.max_llm_input_length
        )

        # Additional LLM-specific validation
        if self.config.enable_llm_input_filtering:
            validated_prompt = await self.validate_and_sanitize_input(
                validated_prompt, "user_message", request
            )

        return validated_prompt

    async def log_llm_usage(
        self,
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
        """Log LLM usage for monitoring and cost tracking"""

        await log_llm_interaction(
            request=request,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            success=success,
            error_message=error_message,
            user_id=user_id,
        )

    async def analyze_request_security(
        self,
        request: Request,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Any]:
        """Analyze request for security threats"""

        if not self.config.enable_security_monitoring:
            return []

        # Get request details
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else "unknown"

        user_agent = request.headers.get("User-Agent", "")

        # Read request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode("utf-8", errors="ignore")
            except Exception:
                body = None

        # Analyze for threats
        alerts = await analyze_request_security(
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=str(request.url.path),
            method=request.method,
            headers=dict(request.headers),
            body=body,
            user_id=user_id,
            session_id=session_id,
        )

        return alerts

    async def create_secure_session(
        self, user_id: str, user_data: Dict[str, Any], request: Request
    ) -> str:
        """Create a secure user session"""

        session_id = session_manager.create_session(user_id, user_data)

        # Update session with request info
        session_manager.update_session_activity(session_id, request)

        # Log session creation
        await log_user_action(
            "session_created",
            request,
            user_id=user_id,
            resource_type="session",
            resource_id=session_id,
            details={
                "user_data": {k: v for k, v in user_data.items() if k != "password"}
            },
            success=True,
        )

        return session_id

    async def validate_session(
        self, session_id: str, request: Request
    ) -> Optional[Dict[str, Any]]:
        """Validate and update session"""

        session_data = session_manager.get_session(session_id)

        if not session_data:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={"violation": "invalid_session", "session_id": session_id},
                severity=AuditSeverity.MEDIUM,
                success=False,
                error_message="Invalid session ID",
            )
            return None

        # Update session activity
        session_manager.update_session_activity(session_id, request)

        return session_data

    async def cleanup_security_data(self, days: int = 7) -> Dict[str, int]:
        """Cleanup old security data"""

        cutoff_time = datetime.utcnow() - timedelta(days=days)

        # Cleanup security monitor data
        original_alert_count = len(security_monitor.alerts)
        security_monitor.alerts = [
            alert for alert in security_monitor.alerts if alert.timestamp > cutoff_time
        ]
        cleaned_alerts = original_alert_count - len(security_monitor.alerts)

        # Cleanup IP activity
        cleaned_ips = 0
        for ip in list(security_monitor.ip_activity.keys()):
            security_monitor.ip_activity[ip] = [
                timestamp
                for timestamp in security_monitor.ip_activity[ip]
                if timestamp > cutoff_time
            ]
            if not security_monitor.ip_activity[ip]:
                del security_monitor.ip_activity[ip]
                cleaned_ips += 1

        # Cleanup expired sessions
        cleaned_sessions = session_manager.cleanup_expired_sessions(days * 24)

        # Cleanup rate limiter data
        cleaned_rate_limit_entries = 0
        for client_id in list(rate_limiter.user_reputation.keys()):
            reputation = rate_limiter.user_reputation[client_id]
            if reputation.get("last_violation"):
                if reputation["last_violation"] < cutoff_time:
                    del rate_limiter.user_reputation[client_id]
                    cleaned_rate_limit_entries += 1

        return {
            "cleaned_alerts": cleaned_alerts,
            "cleaned_ips": cleaned_ips,
            "cleaned_sessions": cleaned_sessions,
            "cleaned_rate_limit_entries": cleaned_rate_limit_entries,
        }

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""

        return {
            "security_level": self.config.security_level.value,
            "features_enabled": {
                "rate_limiting": self.config.enable_rate_limiting,
                "input_validation": self.config.enable_input_validation,
                "audit_logging": self.config.enable_audit_logging,
                "security_monitoring": self.config.enable_security_monitoring,
                "authentication": self.config.enable_authentication,
                "security_headers": self.config.enable_security_headers,
                "ip_whitelist": self.config.enable_ip_whitelist,
                "llm_input_filtering": self.config.enable_llm_input_filtering,
            },
            "statistics": {
                "total_alerts": len(security_monitor.alerts),
                "blocked_ips": len(security_monitor.blocked_ips),
                "active_sessions": len(session_manager.active_sessions),
                "tracked_clients": len(rate_limiter.user_reputation),
                "suspicious_clients": len(rate_limiter.suspicious_ips),
            },
            "configuration": {
                "max_file_size": self.config.max_file_size,
                "max_input_length": self.config.max_input_length,
                "rate_limits": {
                    "default": self.config.default_rate_limit,
                    "strict": self.config.strict_rate_limit,
                    "burst": self.config.burst_rate_limit,
                },
            },
        }


# Global security service instance
security_service = SecurityService()

"""
Security middleware integration for the FastAPI application
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import time
from typing import Callable
import logging

from .rate_limiting import RateLimitMiddleware, check_rate_limit, rate_limiter
from .audit_logging import (
    AuditMiddleware,
    audit_logger,
    log_security_event,
    AuditEventType,
    AuditSeverity,
)
from .input_validation import InputSanitizer, comprehensive_input_validation
from .monitoring import security_monitor, analyze_request_security, is_request_blocked
from .authentication import auth_service, session_manager

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""

    def __init__(self, app, csp_policy: str = None):
        super().__init__(app)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self.csp_policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for request validation and security monitoring"""

    def __init__(
        self,
        app,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        enable_validation: bool = True,
        enable_monitoring: bool = True,
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.enable_validation = enable_validation
        self.enable_monitoring = enable_monitoring

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client info
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        user_agent = request.headers.get("user-agent", "")

        # Check if IP is blocked by security monitor
        if is_request_blocked(client_ip):
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={"violation": "blocked_ip", "ip": client_ip},
                severity=AuditSeverity.HIGH,
                success=False,
                error_message="IP address is blocked due to security violations",
            )
            return JSONResponse(status_code=403, content={"error": "Access denied"})

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={"violation": "request_too_large", "size": content_length},
                severity=AuditSeverity.MEDIUM,
                success=False,
                error_message="Request size exceeds maximum allowed",
            )
            return JSONResponse(
                status_code=413, content={"error": "Request entity too large"}
            )

        # Validate request headers
        if not user_agent or len(user_agent) > 1000:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={
                    "violation": "invalid_user_agent",
                    "user_agent": user_agent[:100],
                },
                severity=AuditSeverity.LOW,
                success=False,
            )

        # Read request body for analysis
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = body_bytes.decode("utf-8", errors="ignore")
            except Exception:
                body = None

        # Analyze request for security threats
        try:
            alerts = await analyze_request_security(
                ip_address=client_ip,
                user_agent=user_agent,
                endpoint=str(request.url.path),
                method=request.method,
                headers=dict(request.headers),
                body=body,
            )

            # Block request if critical threats detected
            critical_alerts = [a for a in alerts if a.threat_level.value == "critical"]
            if critical_alerts:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Request blocked due to security policy"},
                )

            # Update rate limiter reputation
            high_alerts = [
                a for a in alerts if a.threat_level.value in ["high", "critical"]
            ]
            if high_alerts:
                rate_limiter.update_reputation(client_ip, False, "security_violation")

        except Exception as e:
            logger.error(f"Security analysis failed: {e}")

        # Check for suspicious patterns in headers
        suspicious_patterns = ["<script", "javascript:", "vbscript:", "onload="]
        for header_name, header_value in request.headers.items():
            if any(pattern in header_value.lower() for pattern in suspicious_patterns):
                await log_security_event(
                    AuditEventType.SECURITY_VIOLATION,
                    request,
                    details={
                        "violation": "malicious_header",
                        "header": header_name,
                        "value": header_value[:100],
                    },
                    severity=AuditSeverity.HIGH,
                    success=False,
                )
                return JSONResponse(
                    status_code=400, content={"error": "Invalid request headers"}
                )

        return await call_next(request)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware for IP whitelisting (optional, for production)"""

    def __init__(self, app, allowed_ips: list = None, enabled: bool = False):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips or [])
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled:
            return await call_next(request)

        # Get client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Check if IP is allowed
        if self.allowed_ips and client_ip not in self.allowed_ips:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={"violation": "ip_not_whitelisted", "ip": client_ip},
                severity=AuditSeverity.HIGH,
                success=False,
                error_message=f"IP {client_ip} not in whitelist",
            )
            return JSONResponse(status_code=403, content={"error": "Access denied"})

        return await call_next(request)


async def setup_security_middleware(app: FastAPI):
    """Setup all security middleware for the application"""
    from .config import get_security_config

    config = get_security_config()

    # Start audit logger if enabled
    if config.enable_audit_logging:
        await audit_logger.start()

    # Add security middleware in order (last added = first executed)

    # 1. Audit logging (should be outermost to catch everything)
    if config.enable_audit_logging:
        app.add_middleware(AuditMiddleware)

    # 2. Rate limiting with adaptive limits
    if config.enable_rate_limiting:
        app.add_middleware(RateLimitMiddleware, default_limit=config.default_rate_limit)

    # 3. Request validation and security monitoring
    if config.enable_input_validation or config.enable_security_monitoring:
        app.add_middleware(
            RequestValidationMiddleware,
            max_request_size=config.max_file_size,
            enable_validation=config.enable_input_validation,
            enable_monitoring=config.enable_security_monitoring,
        )

    # 4. Security headers
    if config.enable_security_headers:
        app.add_middleware(
            SecurityHeadersMiddleware, csp_policy=config.content_security_policy
        )

    # 5. IP whitelist (configurable)
    if config.enable_ip_whitelist:
        app.add_middleware(
            IPWhitelistMiddleware, allowed_ips=config.allowed_ips, enabled=True
        )

    logger.info(
        f"Security middleware setup completed for {config.security_level.value} environment"
    )


async def shutdown_security_middleware():
    """Cleanup security middleware on shutdown"""
    await audit_logger.stop()
    logger.info("Security middleware shutdown completed")


# Dependency for rate limiting specific endpoints
async def rate_limit_dependency(request: Request, limit_type: str = "api"):
    """FastAPI dependency for rate limiting"""
    rate_limit_response = await check_rate_limit(request, limit_type)
    if rate_limit_response:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


# Dependency for LLM rate limiting
async def llm_rate_limit(request: Request):
    """Rate limit dependency for LLM endpoints"""
    await rate_limit_dependency(request, "llm")


# Dependency for upload rate limiting
async def upload_rate_limit(request: Request):
    """Rate limit dependency for upload endpoints"""
    await rate_limit_dependency(request, "upload")


# Dependency for export rate limiting
async def export_rate_limit(request: Request):
    """Rate limit dependency for export endpoints"""
    await rate_limit_dependency(request, "export")

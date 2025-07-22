"""
Security decorators for FastAPI endpoints
"""

import functools
from typing import Optional, Dict, Any, Callable
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .security_service import security_service
from .authentication import (
    get_current_user,
    require_authentication,
    require_role,
    UserRole,
)
from .rate_limiting import check_rate_limit
from .audit_logging import log_user_action, AuditEventType, AuditSeverity


def secure_endpoint(
    rate_limit_type: str = "api",
    require_auth: bool = False,
    required_role: Optional[UserRole] = None,
    validate_input: bool = True,
    input_type: str = "general_text",
    log_action: Optional[str] = None,
    monitor_security: bool = True,
):
    """
    Comprehensive security decorator for FastAPI endpoints

    Args:
        rate_limit_type: Type of rate limiting to apply
        require_auth: Whether authentication is required
        required_role: Required user role (implies require_auth=True)
        validate_input: Whether to validate and sanitize inputs
        input_type: Type of input validation to apply
        log_action: Action name to log in audit trail
        monitor_security: Whether to monitor for security threats
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Look in kwargs
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=500,
                    detail="Request object not found in endpoint parameters",
                )

            user_id = None
            current_user = None

            # Handle authentication
            if required_role or require_auth:
                # Get current user from token
                security = HTTPBearer(auto_error=False)
                credentials: Optional[HTTPAuthorizationCredentials] = await security(
                    request
                )
                current_user = await get_current_user(request, credentials)

                if not current_user:
                    raise HTTPException(
                        status_code=401, detail="Authentication required"
                    )

                user_id = current_user.get("user_id")

                # Check role if required
                if required_role:
                    user_role = current_user.get("role", UserRole.USER.value)
                    if (
                        user_role != required_role.value
                        and user_role != UserRole.ADMIN.value
                    ):
                        raise HTTPException(
                            status_code=403, detail="Insufficient permissions"
                        )

            # Check rate limits
            await security_service.check_rate_limit(request, rate_limit_type, user_id)

            # Monitor security threats
            if monitor_security:
                alerts = await security_service.analyze_request_security(
                    request,
                    user_id,
                    current_user.get("session_id") if current_user else None,
                )

                # Block request if critical threats detected
                critical_alerts = [
                    a for a in alerts if a.threat_level.value == "critical"
                ]
                if critical_alerts:
                    raise HTTPException(
                        status_code=403, detail="Request blocked due to security policy"
                    )

            # Validate and sanitize inputs
            if validate_input:
                for key, value in kwargs.items():
                    if key != "request" and value is not None:
                        try:
                            kwargs[key] = (
                                await security_service.validate_and_sanitize_input(
                                    value, input_type, request
                                )
                            )
                        except HTTPException:
                            # Re-raise with context
                            raise HTTPException(
                                status_code=400,
                                detail=f"Input validation failed for parameter '{key}'",
                            )

            # Execute the original function
            try:
                result = await func(*args, **kwargs)

                # Log successful action
                if log_action:
                    await log_user_action(
                        log_action,
                        request,
                        user_id=user_id,
                        details={"endpoint": str(request.url.path)},
                        success=True,
                    )

                return result

            except Exception as e:
                # Log failed action
                if log_action:
                    await log_user_action(
                        log_action,
                        request,
                        user_id=user_id,
                        details={"endpoint": str(request.url.path), "error": str(e)},
                        success=False,
                        error_message=str(e),
                    )
                raise

        return wrapper

    return decorator


def rate_limited(limit_type: str = "api"):
    """Simple rate limiting decorator"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                await security_service.check_rate_limit(request, limit_type)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_input_data(input_type: str = "general_text"):
    """Input validation decorator"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Validate inputs
            for key, value in kwargs.items():
                if key != "request" and value is not None:
                    kwargs[key] = await security_service.validate_and_sanitize_input(
                        value, input_type, request
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def audit_action(action_name: str, resource_type: Optional[str] = None):
    """Audit logging decorator"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            user_id = None

            # Extract request and user info
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Try to get current user
            if request:
                try:
                    security = HTTPBearer(auto_error=False)
                    credentials = await security(request)
                    current_user = await get_current_user(request, credentials)
                    if current_user:
                        user_id = current_user.get("user_id")
                except:
                    pass

            try:
                result = await func(*args, **kwargs)

                # Log successful action
                if request:
                    await log_user_action(
                        action_name,
                        request,
                        user_id=user_id,
                        resource_type=resource_type,
                        details={"endpoint": str(request.url.path)},
                        success=True,
                    )

                return result

            except Exception as e:
                # Log failed action
                if request:
                    await log_user_action(
                        action_name,
                        request,
                        user_id=user_id,
                        resource_type=resource_type,
                        details={"endpoint": str(request.url.path), "error": str(e)},
                        success=False,
                        error_message=str(e),
                    )
                raise

        return wrapper

    return decorator


def file_upload_security(max_size: Optional[int] = None):
    """File upload security decorator"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            user_id = None

            # Extract request
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Get user ID if available
            if request:
                try:
                    security = HTTPBearer(auto_error=False)
                    credentials = await security(request)
                    current_user = await get_current_user(request, credentials)
                    if current_user:
                        user_id = current_user.get("user_id")
                except:
                    pass

            # Validate file uploads in kwargs
            for key, value in kwargs.items():
                if hasattr(value, "file") and hasattr(value, "filename"):
                    # This is a file upload
                    file_content = await value.read()
                    await value.seek(0)  # Reset file pointer

                    await security_service.validate_file_upload(
                        file_content, value.filename, request, user_id
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def llm_security():
    """LLM request security decorator"""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            user_id = None

            # Extract request
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            # Get user ID if available
            if request:
                try:
                    security = HTTPBearer(auto_error=False)
                    credentials = await security(request)
                    current_user = await get_current_user(request, credentials)
                    if current_user:
                        user_id = current_user.get("user_id")
                except:
                    pass

            # Validate LLM inputs
            for key, value in kwargs.items():
                if isinstance(value, str) and key in [
                    "prompt",
                    "message",
                    "text",
                    "input",
                ]:
                    kwargs[key] = await security_service.validate_llm_request(
                        value, request, user_id
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience decorators for common use cases
def admin_only(func: Callable) -> Callable:
    """Decorator for admin-only endpoints"""
    return secure_endpoint(
        require_auth=True,
        required_role=UserRole.ADMIN,
        rate_limit_type="api",
        log_action=func.__name__,
    )(func)


def authenticated_user(func: Callable) -> Callable:
    """Decorator for authenticated user endpoints"""
    return secure_endpoint(
        require_auth=True, rate_limit_type="api", log_action=func.__name__
    )(func)


def public_endpoint(rate_limit_type: str = "api"):
    """Decorator for public endpoints with rate limiting"""

    def decorator(func: Callable) -> Callable:
        return secure_endpoint(
            require_auth=False,
            rate_limit_type=rate_limit_type,
            log_action=func.__name__,
        )(func)

    return decorator


def llm_endpoint(func: Callable) -> Callable:
    """Decorator for LLM-related endpoints"""
    return secure_endpoint(
        rate_limit_type="llm",
        validate_input=True,
        input_type="user_message",
        log_action=func.__name__,
        monitor_security=True,
    )(llm_security()(func))


def upload_endpoint(func: Callable) -> Callable:
    """Decorator for file upload endpoints"""
    return secure_endpoint(
        rate_limit_type="upload",
        validate_input=False,  # Files are validated separately
        log_action=func.__name__,
        monitor_security=True,
    )(file_upload_security()(func))


def export_endpoint(func: Callable) -> Callable:
    """Decorator for export/download endpoints"""
    return secure_endpoint(
        rate_limit_type="export", log_action=func.__name__, monitor_security=True
    )(func)

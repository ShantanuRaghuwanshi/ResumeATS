"""
Security module for resume optimization API
"""

from .config import get_security_config, SecurityLevel, SecurityConfig
from .security_service import security_service
from .decorators import (
    secure_endpoint,
    rate_limited,
    validate_input_data,
    audit_action,
    file_upload_security,
    llm_security,
    admin_only,
    authenticated_user,
    public_endpoint,
    llm_endpoint,
    upload_endpoint,
    export_endpoint,
)
from .input_validation import (
    InputSanitizer,
    comprehensive_input_validation,
    validate_resume_upload,
    validate_llm_input,
    validate_json_input,
    validate_file_content,
    validate_input,
)
from .rate_limiting import (
    rate_limiter,
    check_rate_limit,
    get_client_identifier,
    RateLimitConfig,
)
from .audit_logging import (
    audit_logger,
    log_security_event,
    log_user_action,
    log_llm_interaction,
    AuditEventType,
    AuditSeverity,
)
from .monitoring import (
    security_monitor,
    analyze_request_security,
    is_request_blocked,
    ThreatLevel,
    AttackType,
)
from .authentication import (
    auth_service,
    session_manager,
    get_current_user,
    require_authentication,
    require_role,
    UserRole,
)
from .middleware import (
    setup_security_middleware,
    shutdown_security_middleware,
    rate_limit_dependency,
    llm_rate_limit,
    upload_rate_limit,
    export_rate_limit,
)

__all__ = [
    # Configuration
    "get_security_config",
    "SecurityLevel",
    "SecurityConfig",
    # Main service
    "security_service",
    # Decorators
    "secure_endpoint",
    "rate_limited",
    "validate_input_data",
    "audit_action",
    "file_upload_security",
    "llm_security",
    "admin_only",
    "authenticated_user",
    "public_endpoint",
    "llm_endpoint",
    "upload_endpoint",
    "export_endpoint",
    # Input validation
    "InputSanitizer",
    "comprehensive_input_validation",
    "validate_resume_upload",
    "validate_llm_input",
    "validate_json_input",
    "validate_file_content",
    "validate_input",
    # Rate limiting
    "rate_limiter",
    "check_rate_limit",
    "get_client_identifier",
    "RateLimitConfig",
    # Audit logging
    "audit_logger",
    "log_security_event",
    "log_user_action",
    "log_llm_interaction",
    "AuditEventType",
    "AuditSeverity",
    # Monitoring
    "security_monitor",
    "analyze_request_security",
    "is_request_blocked",
    "ThreatLevel",
    "AttackType",
    # Authentication
    "auth_service",
    "session_manager",
    "get_current_user",
    "require_authentication",
    "require_role",
    "UserRole",
    # Middleware
    "setup_security_middleware",
    "shutdown_security_middleware",
    "rate_limit_dependency",
    "llm_rate_limit",
    "upload_rate_limit",
    "export_rate_limit",
]

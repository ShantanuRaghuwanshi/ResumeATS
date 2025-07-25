"""
Comprehensive logging configuration for the application
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation
        if hasattr(record, "service"):
            log_entry["service"] = record.service
        if hasattr(record, "duration"):
            log_entry["duration"] = record.duration

        return json.dumps(log_entry)


class ContextFilter(logging.Filter):
    """Filter to add context information to log records"""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        # Add context information to the record
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class ServiceLogger:
    """Service-specific logger with context"""

    def __init__(self, service_name: str, logger: logging.Logger):
        self.service_name = service_name
        self.logger = logger
        self.context = {"service": service_name}

    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with service context"""
        extra = {**self.context, **kwargs}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def log_operation(
        self, operation: str, duration: float, success: bool = True, **kwargs
    ):
        """Log operation with performance metrics"""
        level = logging.INFO if success else logging.ERROR
        message = f"Operation {operation} {'completed' if success else 'failed'} in {duration:.2f}s"
        self._log_with_context(
            level, message, operation=operation, duration=duration, **kwargs
        )

    def log_user_action(self, user_id: str, action: str, **kwargs):
        """Log user action"""
        self._log_with_context(
            logging.INFO,
            f"User {user_id} performed action: {action}",
            user_id=user_id,
            action=action,
            **kwargs,
        )

    def log_error_with_context(self, error: Exception, operation: str, **kwargs):
        """Log error with full context"""
        self._log_with_context(
            logging.ERROR,
            f"Error in {operation}: {str(error)}",
            operation=operation,
            error_type=type(error).__name__,
            **kwargs,
        )


def setup_logging() -> Dict[str, ServiceLogger]:
    """Setup comprehensive logging configuration"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with colored output for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    console_formatter = JSONFormatter()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "application.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log", maxBytes=10 * 1024 * 1024, backupCount=10  # 10MB
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # Service-specific loggers
    service_loggers = {}

    services = [
        "integration_service",
        "conversation_manager",
        "section_optimizer",
        "job_matcher",
        "feedback_analyzer",
        "version_manager",
        "websocket_manager",
        "cache_service",
        "background_jobs",
        "security_service",
        "audit_logger",
        "performance_monitor",
        "api",
        "database",
        "llm_provider",
    ]

    for service_name in services:
        logger = logging.getLogger(service_name)
        service_logger = ServiceLogger(service_name, logger)
        service_loggers[service_name] = service_logger

        # Create service-specific file handler
        service_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{service_name}.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        )
        service_handler.setFormatter(JSONFormatter())
        service_handler.setLevel(logging.DEBUG)
        logger.addHandler(service_handler)

    # Performance logger for metrics
    perf_logger = logging.getLogger("performance")
    perf_handler = logging.handlers.RotatingFileHandler(
        log_dir / "performance.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    perf_handler.setFormatter(JSONFormatter())
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)

    # Audit logger for security events
    audit_logger = logging.getLogger("audit")
    audit_handler = logging.handlers.RotatingFileHandler(
        log_dir / "audit.log", maxBytes=10 * 1024 * 1024, backupCount=10  # 10MB
    )
    audit_handler.setFormatter(JSONFormatter())
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)

    # WebSocket logger for real-time events
    ws_logger = logging.getLogger("websocket")
    ws_handler = logging.handlers.RotatingFileHandler(
        log_dir / "websocket.log", maxBytes=5 * 1024 * 1024, backupCount=3  # 5MB
    )
    ws_handler.setFormatter(JSONFormatter())
    ws_logger.addHandler(ws_handler)
    ws_logger.setLevel(logging.INFO)

    logging.info("Logging configuration initialized")

    return service_loggers


def get_service_logger(service_name: str) -> ServiceLogger:
    """Get or create a service logger"""
    logger = logging.getLogger(service_name)
    return ServiceLogger(service_name, logger)


def log_request_response(
    endpoint: str,
    method: str,
    status_code: int,
    duration: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """Log API request/response"""
    api_logger = logging.getLogger("api")
    api_logger.info(
        f"{method} {endpoint} - {status_code} - {duration:.2f}s",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration": duration,
            "user_id": user_id,
            "request_id": request_id,
        },
    )


def log_database_operation(
    operation: str,
    table: str,
    duration: float,
    success: bool = True,
    error: Optional[str] = None,
):
    """Log database operations"""
    db_logger = logging.getLogger("database")
    level = logging.INFO if success else logging.ERROR
    message = f"Database {operation} on {table} - {'success' if success else 'failed'} - {duration:.2f}s"

    extra = {
        "operation": operation,
        "table": table,
        "duration": duration,
        "success": success,
    }

    if error:
        extra["error"] = error

    db_logger.log(level, message, extra=extra)


def log_llm_operation(
    provider: str,
    operation: str,
    tokens_used: int,
    duration: float,
    success: bool = True,
    error: Optional[str] = None,
):
    """Log LLM operations"""
    llm_logger = logging.getLogger("llm_provider")
    level = logging.INFO if success else logging.ERROR
    message = (
        f"LLM {operation} with {provider} - {tokens_used} tokens - {duration:.2f}s"
    )

    extra = {
        "provider": provider,
        "operation": operation,
        "tokens_used": tokens_used,
        "duration": duration,
        "success": success,
    }

    if error:
        extra["error"] = error

    llm_logger.log(level, message, extra=extra)


# Initialize logging on module import
service_loggers = setup_logging()

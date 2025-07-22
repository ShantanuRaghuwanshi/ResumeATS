"""
Security configuration and settings
"""

import os
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SecurityLevel(Enum):
    """Security levels for different environments"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class SecurityConfig:
    """Security configuration settings"""

    # Environment
    security_level: SecurityLevel = SecurityLevel.DEVELOPMENT

    # Rate limiting
    enable_rate_limiting: bool = True
    default_rate_limit: tuple = (100, 60)  # requests per minute
    strict_rate_limit: tuple = (50, 60)
    burst_rate_limit: tuple = (10, 1)  # requests per second

    # Input validation
    enable_input_validation: bool = True
    max_input_length: int = 10000
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_extensions: List[str] = None

    # Authentication
    enable_authentication: bool = True
    jwt_secret_key: str = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15

    # Audit logging
    enable_audit_logging: bool = True
    audit_log_directory: str = "data/audit_logs"
    max_log_file_size: int = 10 * 1024 * 1024  # 10MB
    max_log_files: int = 100

    # Security monitoring
    enable_security_monitoring: bool = True
    auto_block_threats: bool = True
    threat_detection_sensitivity: str = "medium"  # low, medium, high

    # IP filtering
    enable_ip_whitelist: bool = False
    allowed_ips: List[str] = None
    blocked_ips: List[str] = None

    # CORS settings
    allowed_origins: List[str] = None
    allow_credentials: bool = True

    # Security headers
    enable_security_headers: bool = True
    content_security_policy: str = None

    # LLM security
    enable_llm_input_filtering: bool = True
    max_llm_input_length: int = 10000
    llm_rate_limit: tuple = (20, 60)  # requests per minute

    def __post_init__(self):
        """Initialize default values based on environment"""
        if self.allowed_file_extensions is None:
            self.allowed_file_extensions = ["pdf", "docx", "doc", "txt"]

        if self.jwt_secret_key is None:
            self.jwt_secret_key = os.getenv(
                "JWT_SECRET_KEY", "dev-secret-key-change-in-production"
            )

        if self.allowed_origins is None:
            if self.security_level == SecurityLevel.DEVELOPMENT:
                self.allowed_origins = [
                    "http://localhost:3000",
                    "http://localhost:5173",
                ]
            else:
                self.allowed_origins = []

        if self.allowed_ips is None:
            self.allowed_ips = []

        if self.blocked_ips is None:
            self.blocked_ips = []

        if self.content_security_policy is None:
            self.content_security_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none';"
            )

        # Adjust settings based on security level
        if self.security_level == SecurityLevel.PRODUCTION:
            self.enable_ip_whitelist = False  # Can be enabled manually
            self.auto_block_threats = True
            self.threat_detection_sensitivity = "high"
            self.max_login_attempts = 3
            self.lockout_duration_minutes = 30
        elif self.security_level == SecurityLevel.STAGING:
            self.threat_detection_sensitivity = "medium"
            self.max_login_attempts = 5
        else:  # DEVELOPMENT
            self.auto_block_threats = False
            self.threat_detection_sensitivity = "low"


# Global security configuration
def get_security_config() -> SecurityConfig:
    """Get security configuration based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        security_level = SecurityLevel.PRODUCTION
    elif env == "staging":
        security_level = SecurityLevel.STAGING
    else:
        security_level = SecurityLevel.DEVELOPMENT

    return SecurityConfig(security_level=security_level)


# Rate limit configurations for different endpoint types
RATE_LIMIT_CONFIGS = {
    "upload": {
        "development": (10, 60),  # 10 uploads per minute
        "staging": (5, 60),  # 5 uploads per minute
        "production": (3, 60),  # 3 uploads per minute
    },
    "llm": {
        "development": (50, 60),  # 50 LLM requests per minute
        "staging": (30, 60),  # 30 LLM requests per minute
        "production": (20, 60),  # 20 LLM requests per minute
    },
    "api": {
        "development": (200, 60),  # 200 API requests per minute
        "staging": (150, 60),  # 150 API requests per minute
        "production": (100, 60),  # 100 API requests per minute
    },
    "export": {
        "development": (20, 60),  # 20 exports per minute
        "staging": (15, 60),  # 15 exports per minute
        "production": (10, 60),  # 10 exports per minute
    },
    "auth": {
        "development": (20, 60),  # 20 auth attempts per minute
        "staging": (15, 60),  # 15 auth attempts per minute
        "production": (10, 60),  # 10 auth attempts per minute
    },
}


def get_rate_limit_for_endpoint(
    endpoint_type: str, security_level: SecurityLevel
) -> tuple:
    """Get rate limit configuration for specific endpoint type and security level"""
    config = RATE_LIMIT_CONFIGS.get(endpoint_type, RATE_LIMIT_CONFIGS["api"])
    return config.get(security_level.value, config["development"])


# Security validation rules for different data types
VALIDATION_RULES = {
    "resume_text": {
        "max_length": 50000,
        "check_sql": True,
        "check_xss": True,
        "check_path_traversal": False,
        "check_command_injection": True,
    },
    "job_description": {
        "max_length": 20000,
        "check_sql": True,
        "check_xss": True,
        "check_path_traversal": False,
        "check_command_injection": True,
    },
    "user_message": {
        "max_length": 5000,
        "check_sql": True,
        "check_xss": True,
        "check_path_traversal": True,
        "check_command_injection": True,
    },
    "filename": {
        "max_length": 255,
        "check_sql": False,
        "check_xss": True,
        "check_path_traversal": True,
        "check_command_injection": True,
    },
    "general_text": {
        "max_length": 10000,
        "check_sql": True,
        "check_xss": True,
        "check_path_traversal": True,
        "check_command_injection": True,
    },
}


def get_validation_rules(data_type: str) -> Dict[str, Any]:
    """Get validation rules for specific data type"""
    return VALIDATION_RULES.get(data_type, VALIDATION_RULES["general_text"])


# Threat detection patterns
THREAT_PATTERNS = {
    "high_risk": [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\bxp_cmdshell\b)",
        r"(\bsp_executesql\b)",
        r"[;&|`$(){}[\]<>]",
        r"\b(cat|ls|dir|type|copy|move|del|rm|chmod|chown)\b",
    ],
    "medium_risk": [
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(--|#|/\*|\*/)",
        r"\.\./",
        r"\.\.\\",
    ],
    "low_risk": [
        r"ignore\s+previous\s+instructions",
        r"forget\s+everything",
        r"system\s*:",
        r"jailbreak",
        r"roleplay\s+as",
    ],
}


# File type security configurations
FILE_SECURITY_CONFIG = {
    "pdf": {
        "max_size": 10 * 1024 * 1024,  # 10MB
        "allowed_mime_types": ["application/pdf"],
        "scan_for_malware": True,
    },
    "docx": {
        "max_size": 5 * 1024 * 1024,  # 5MB
        "allowed_mime_types": [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ],
        "scan_for_malware": True,
    },
    "doc": {
        "max_size": 5 * 1024 * 1024,  # 5MB
        "allowed_mime_types": ["application/msword"],
        "scan_for_malware": True,
    },
    "txt": {
        "max_size": 1 * 1024 * 1024,  # 1MB
        "allowed_mime_types": ["text/plain"],
        "scan_for_malware": False,
    },
}


def get_file_security_config(file_extension: str) -> Dict[str, Any]:
    """Get security configuration for file type"""
    return FILE_SECURITY_CONFIG.get(
        file_extension.lower(),
        {
            "max_size": 1 * 1024 * 1024,
            "allowed_mime_types": [],
            "scan_for_malware": True,
        },
    )

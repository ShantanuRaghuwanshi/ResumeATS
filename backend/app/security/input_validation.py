"""
Input validation and sanitization utilities for security
"""

import re
import html
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException
import bleach
from pydantic import BaseModel, validator


class InputSanitizer:
    """Utility class for input sanitization and validation"""

    # Allowed HTML tags for rich text content
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "ol",
        "ul",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        "*": ["class"],
        "a": ["href", "title"],
    }

    @staticmethod
    def sanitize_html(content: str) -> str:
        """Sanitize HTML content to prevent XSS attacks"""
        if not content:
            return ""

        # Use bleach to clean HTML
        cleaned = bleach.clean(
            content,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True,
        )

        return cleaned

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize plain text input"""
        if not text:
            return ""

        # HTML escape the text
        sanitized = html.escape(text)

        # Remove any potential script injections
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )

        return sanitized.strip()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email:
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False

        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)

        # Check if it's a valid length (7-15 digits)
        return 7 <= len(digits_only) <= 15

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False

        url_pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
        return bool(re.match(url_pattern, url))

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        if not filename:
            return ""

        # Remove directory traversal attempts
        sanitized = filename.replace("..", "").replace("/", "").replace("\\", "")

        # Keep only alphanumeric, dots, hyphens, and underscores
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "", sanitized)

        # Limit length
        return sanitized[:255]

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
        """Validate file extension"""
        if not filename:
            return False

        extension = filename.lower().split(".")[-1]
        return extension in [ext.lower() for ext in allowed_extensions]


class SecureResumeData(BaseModel):
    """Pydantic model for secure resume data validation"""

    personal_details: Optional[Dict[str, Any]] = None
    sections: Optional[Dict[str, Any]] = None

    @validator("personal_details", pre=True)
    def sanitize_personal_details(cls, v):
        if not v:
            return v

        sanitized = {}
        for key, value in v.items():
            if isinstance(value, str):
                if key == "email":
                    if not InputSanitizer.validate_email(value):
                        raise ValueError(f"Invalid email format: {value}")
                    sanitized[key] = value
                elif key == "phone":
                    if not InputSanitizer.validate_phone(value):
                        raise ValueError(f"Invalid phone format: {value}")
                    sanitized[key] = value
                elif key in ["linkedin", "github", "website"]:
                    if value and not InputSanitizer.validate_url(value):
                        raise ValueError(f"Invalid URL format for {key}: {value}")
                    sanitized[key] = value
                else:
                    sanitized[key] = InputSanitizer.sanitize_text(value)
            else:
                sanitized[key] = value

        return sanitized

    @validator("sections", pre=True)
    def sanitize_sections(cls, v):
        if not v:
            return v

        sanitized = {}
        for section_name, section_data in v.items():
            if isinstance(section_data, dict):
                sanitized[section_name] = cls._sanitize_section_data(section_data)
            elif isinstance(section_data, list):
                sanitized[section_name] = [
                    (
                        cls._sanitize_section_data(item)
                        if isinstance(item, dict)
                        else InputSanitizer.sanitize_text(str(item))
                    )
                    for item in section_data
                ]
            else:
                sanitized[section_name] = InputSanitizer.sanitize_text(
                    str(section_data)
                )

        return sanitized

    @staticmethod
    def _sanitize_section_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize section data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = SecureResumeData._sanitize_section_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    (
                        SecureResumeData._sanitize_section_data(item)
                        if isinstance(item, dict)
                        else InputSanitizer.sanitize_text(str(item))
                    )
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized


def validate_resume_upload(file_content: bytes, filename: str) -> None:
    """Validate uploaded resume file"""

    # Check file extension
    allowed_extensions = ["pdf", "docx", "doc", "txt"]
    if not InputSanitizer.validate_file_extension(filename, allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}",
        )

    # Check file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400, detail="File size exceeds maximum limit of 10MB"
        )

    # Check for malicious file signatures
    malicious_signatures = [
        b"<script",
        b"javascript:",
        b"vbscript:",
        b"onload=",
        b"onerror=",
    ]

    content_lower = file_content.lower()
    for signature in malicious_signatures:
        if signature in content_lower:
            raise HTTPException(
                status_code=400, detail="File contains potentially malicious content"
            )


def validate_llm_input(text: str, max_length: int = 10000) -> str:
    """Validate and sanitize LLM input"""
    if not text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    # Check length
    if len(text) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input text exceeds maximum length of {max_length} characters",
        )

    # Sanitize the text
    sanitized = InputSanitizer.sanitize_text(text)

    # Check for prompt injection attempts
    injection_patterns = [
        r"ignore\s+previous\s+instructions",
        r"forget\s+everything",
        r"system\s*:",
        r"assistant\s*:",
        r"human\s*:",
        r"<\|.*?\|>",
        r"jailbreak",
        r"roleplay\s+as",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if",
        r"override\s+safety",
        r"disable\s+filter",
    ]

    for pattern in injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Input contains potentially malicious prompt injection",
            )

    return sanitized


def validate_json_input(data: Any, max_depth: int = 10, max_keys: int = 100) -> Any:
    """Validate JSON input to prevent DoS attacks"""

    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            raise HTTPException(
                status_code=400,
                detail=f"JSON structure too deep (max depth: {max_depth})",
            )

        if isinstance(obj, dict):
            if len(obj) > max_keys:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many keys in JSON object (max: {max_keys})",
                )
            for value in obj.values():
                check_depth(value, current_depth + 1)
        elif isinstance(obj, list):
            if len(obj) > max_keys:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many items in JSON array (max: {max_keys})",
                )
            for item in obj:
                check_depth(item, current_depth + 1)

    check_depth(data)
    return data


def validate_file_content(content: bytes, allowed_mime_types: List[str] = None) -> bool:
    """Validate file content based on magic bytes"""
    if not content:
        return False

    # Common file signatures
    file_signatures = {
        b"\x25\x50\x44\x46": "application/pdf",  # PDF
        b"\x50\x4B\x03\x04": "application/zip",  # ZIP/DOCX
        b"\xD0\xCF\x11\xE0": "application/msword",  # DOC
        b"\x89\x50\x4E\x47": "image/png",  # PNG
        b"\xFF\xD8\xFF": "image/jpeg",  # JPEG
    }

    # Check file signature
    for signature, mime_type in file_signatures.items():
        if content.startswith(signature):
            if allowed_mime_types and mime_type not in allowed_mime_types:
                return False
            return True

    # If no signature matches and we have restrictions, reject
    if allowed_mime_types:
        return False

    return True


class AdvancedInputValidator:
    """Advanced input validation with security checks"""

    @staticmethod
    def validate_sql_injection(text: str) -> bool:
        """Check for SQL injection patterns"""
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"].*['\"])",
            r"(--|#|/\*|\*/)",
            r"(\bxp_cmdshell\b)",
            r"(\bsp_executesql\b)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True

    @staticmethod
    def validate_xss_patterns(text: str) -> bool:
        """Check for XSS patterns"""
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"vbscript:",
            r"onload\s*=",
            r"onerror\s*=",
            r"onclick\s*=",
            r"onmouseover\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]

        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True

    @staticmethod
    def validate_path_traversal(path: str) -> bool:
        """Check for path traversal attempts"""
        dangerous_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"/etc/passwd",
            r"/proc/",
            r"C:\\Windows",
            r"\\Windows\\",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return False

        return True

    @staticmethod
    def validate_command_injection(text: str) -> bool:
        """Check for command injection patterns"""
        command_patterns = [
            r"[;&|`$(){}[\]<>]",
            r"\b(cat|ls|dir|type|copy|move|del|rm|chmod|chown)\b",
            r"\b(wget|curl|nc|netcat|telnet|ssh)\b",
            r"\b(python|perl|ruby|php|bash|sh|cmd|powershell)\b",
        ]

        for pattern in command_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False

        return True


def comprehensive_input_validation(
    text: str,
    check_sql: bool = True,
    check_xss: bool = True,
    check_path_traversal: bool = True,
    check_command_injection: bool = True,
    max_length: int = 10000,
) -> str:
    """Comprehensive input validation"""

    if not text:
        raise HTTPException(status_code=400, detail="Input cannot be empty")

    if len(text) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input exceeds maximum length of {max_length} characters",
        )

    # Sanitize first
    sanitized = InputSanitizer.sanitize_text(text)

    # Run security checks
    if check_sql and not AdvancedInputValidator.validate_sql_injection(sanitized):
        raise HTTPException(
            status_code=400, detail="Input contains potential SQL injection patterns"
        )

    if check_xss and not AdvancedInputValidator.validate_xss_patterns(sanitized):
        raise HTTPException(
            status_code=400, detail="Input contains potential XSS patterns"
        )

    if check_path_traversal and not AdvancedInputValidator.validate_path_traversal(
        sanitized
    ):
        raise HTTPException(
            status_code=400, detail="Input contains potential path traversal patterns"
        )

    if (
        check_command_injection
        and not AdvancedInputValidator.validate_command_injection(sanitized)
    ):
        raise HTTPException(
            status_code=400,
            detail="Input contains potential command injection patterns",
        )

    return sanitized


# Validation decorators for FastAPI endpoints
def validate_input(
    max_length: int = 10000,
    check_sql: bool = True,
    check_xss: bool = True,
    check_path_traversal: bool = True,
    check_command_injection: bool = True,
):
    """Decorator for input validation on FastAPI endpoints"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Validate string inputs in kwargs
            for key, value in kwargs.items():
                if isinstance(value, str) and value:
                    try:
                        kwargs[key] = comprehensive_input_validation(
                            value,
                            check_sql=check_sql,
                            check_xss=check_xss,
                            check_path_traversal=check_path_traversal,
                            check_command_injection=check_command_injection,
                            max_length=max_length,
                        )
                    except HTTPException as e:
                        # Add context about which field failed validation
                        raise HTTPException(
                            status_code=e.status_code,
                            detail=f"Validation failed for field '{key}': {e.detail}",
                        )
                elif isinstance(value, dict):
                    # Recursively validate dictionary values
                    kwargs[key] = validate_dict_inputs(
                        value,
                        max_length=max_length,
                        check_sql=check_sql,
                        check_xss=check_xss,
                        check_path_traversal=check_path_traversal,
                        check_command_injection=check_command_injection,
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def validate_dict_inputs(
    data: dict,
    max_length: int = 10000,
    check_sql: bool = True,
    check_xss: bool = True,
    check_path_traversal: bool = True,
    check_command_injection: bool = True,
) -> dict:
    """Recursively validate dictionary inputs"""
    validated_data = {}

    for key, value in data.items():
        if isinstance(value, str) and value:
            try:
                validated_data[key] = comprehensive_input_validation(
                    value,
                    check_sql=check_sql,
                    check_xss=check_xss,
                    check_path_traversal=check_path_traversal,
                    check_command_injection=check_command_injection,
                    max_length=max_length,
                )
            except HTTPException as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail=f"Validation failed for field '{key}': {e.detail}",
                )
        elif isinstance(value, dict):
            validated_data[key] = validate_dict_inputs(
                value,
                max_length=max_length,
                check_sql=check_sql,
                check_xss=check_xss,
                check_path_traversal=check_path_traversal,
                check_command_injection=check_command_injection,
            )
        elif isinstance(value, list):
            validated_data[key] = [
                (
                    comprehensive_input_validation(
                        item,
                        check_sql=check_sql,
                        check_xss=check_xss,
                        check_path_traversal=check_path_traversal,
                        check_command_injection=check_command_injection,
                        max_length=max_length,
                    )
                    if isinstance(item, str) and item
                    else (
                        validate_dict_inputs(
                            item,
                            max_length=max_length,
                            check_sql=check_sql,
                            check_xss=check_xss,
                            check_path_traversal=check_path_traversal,
                            check_command_injection=check_command_injection,
                        )
                        if isinstance(item, dict)
                        else item
                    )
                )
                for item in value
            ]
        else:
            validated_data[key] = value

    return validated_data

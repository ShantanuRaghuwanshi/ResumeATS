"""
Authentication and authorization system for the resume optimization API
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import secrets
import hashlib
from enum import Enum

from .audit_logging import log_security_event, AuditEventType, AuditSeverity


class UserRole(Enum):
    """User roles for authorization"""

    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class AuthConfig:
    """Authentication configuration"""

    SECRET_KEY = secrets.token_urlsafe(32)  # In production, use environment variable
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class AuthenticationService:
    """Service for handling authentication operations"""

    def __init__(self):
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM
        )
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(
            days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS
        )
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM
        )
        return encoded_jwt

    def verify_token(
        self, token: str, token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM]
            )

            # Check token type
            if payload.get("type") != token_type:
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                return None

            return payload

        except jwt.PyJWTError:
            return None

    def is_account_locked(self, identifier: str) -> bool:
        """Check if an account is locked due to failed login attempts"""
        if identifier not in self.failed_attempts:
            return False

        attempt_data = self.failed_attempts[identifier]
        attempts = attempt_data.get("count", 0)
        last_attempt = attempt_data.get("last_attempt")

        if attempts >= AuthConfig.MAX_LOGIN_ATTEMPTS:
            if last_attempt:
                lockout_end = last_attempt + timedelta(
                    minutes=AuthConfig.LOCKOUT_DURATION_MINUTES
                )
                if datetime.utcnow() < lockout_end:
                    return True
                else:
                    # Reset attempts after lockout period
                    self.failed_attempts[identifier] = {
                        "count": 0,
                        "last_attempt": None,
                    }

        return False

    def record_failed_attempt(self, identifier: str):
        """Record a failed login attempt"""
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = {"count": 0, "last_attempt": None}

        self.failed_attempts[identifier]["count"] += 1
        self.failed_attempts[identifier]["last_attempt"] = datetime.utcnow()

    def reset_failed_attempts(self, identifier: str):
        """Reset failed login attempts for an identifier"""
        if identifier in self.failed_attempts:
            self.failed_attempts[identifier] = {"count": 0, "last_attempt": None}

    def generate_session_id(self) -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)

    def hash_session_id(self, session_id: str) -> str:
        """Hash a session ID for storage"""
        return hashlib.sha256(session_id.encode()).hexdigest()


# Global authentication service instance
auth_service = AuthenticationService()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """Dependency to get current authenticated user"""

    if not credentials:
        return None

    token = credentials.credentials
    payload = auth_service.verify_token(token)

    if not payload:
        await log_security_event(
            AuditEventType.SECURITY_VIOLATION,
            request,
            details={"violation": "invalid_token"},
            severity=AuditSeverity.MEDIUM,
            success=False,
            error_message="Invalid or expired token",
        )
        return None

    return payload


async def require_authentication(
    request: Request, current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Dependency that requires authentication"""

    if not current_user:
        await log_security_event(
            AuditEventType.SECURITY_VIOLATION,
            request,
            details={"violation": "unauthenticated_access"},
            severity=AuditSeverity.MEDIUM,
            success=False,
            error_message="Authentication required",
        )
        raise HTTPException(status_code=401, detail="Authentication required")

    return current_user


async def require_role(required_role: UserRole):
    """Dependency factory for role-based authorization"""

    async def role_checker(
        request: Request, current_user: Dict[str, Any] = Depends(require_authentication)
    ) -> Dict[str, Any]:

        user_role = current_user.get("role", UserRole.USER.value)

        if user_role != required_role.value and user_role != UserRole.ADMIN.value:
            await log_security_event(
                AuditEventType.SECURITY_VIOLATION,
                request,
                details={
                    "violation": "insufficient_permissions",
                    "required_role": required_role.value,
                    "user_role": user_role,
                },
                severity=AuditSeverity.HIGH,
                success=False,
                user_id=current_user.get("user_id"),
                error_message=f"Role {required_role.value} required",
            )
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return current_user

    return role_checker


def create_api_key() -> str:
    """Generate a secure API key"""
    return f"rsa_{secrets.token_urlsafe(32)}"


def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key or not api_key.startswith("rsa_"):
        return False

    # In production, check against database
    # For now, just validate format
    return len(api_key) > 10


async def api_key_auth(
    request: Request, api_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """API key authentication"""

    # Get API key from header
    if not api_key:
        api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    if not validate_api_key(api_key):
        await log_security_event(
            AuditEventType.SECURITY_VIOLATION,
            request,
            details={"violation": "invalid_api_key"},
            severity=AuditSeverity.HIGH,
            success=False,
            error_message="Invalid API key format",
        )
        return None

    # In production, look up API key in database
    # For now, return basic user info
    return {"user_id": "api_user", "role": UserRole.USER.value, "auth_type": "api_key"}


class SessionManager:
    """Manage user sessions"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: str, user_data: Dict[str, Any]) -> str:
        """Create a new user session"""
        session_id = auth_service.generate_session_id()

        self.active_sessions[session_id] = {
            "user_id": user_id,
            "user_data": user_data,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "ip_address": None,
            "user_agent": None,
        }

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.active_sessions.get(session_id)

    def update_session_activity(self, session_id: str, request: Request):
        """Update session last activity"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["last_activity"] = datetime.utcnow()

            # Update request info
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                ip_address = forwarded_for.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else "unknown"

            self.active_sessions[session_id]["ip_address"] = ip_address
            self.active_sessions[session_id]["user_agent"] = request.headers.get(
                "User-Agent", "unknown"
            )

    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_sessions = [
            session_id
            for session_id, session_data in self.active_sessions.items()
            if session_data["last_activity"] < cutoff_time
        ]

        for session_id in expired_sessions:
            del self.active_sessions[session_id]

        return len(expired_sessions)


# Global session manager
session_manager = SessionManager()

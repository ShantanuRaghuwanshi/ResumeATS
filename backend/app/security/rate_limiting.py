"""
Rate limiting middleware and utilities for API security
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import redis
from datetime import datetime, timedelta
import json
import hashlib


class InMemoryRateLimiter:
    """In-memory rate limiter for development/testing"""

    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

    def _cleanup_old_requests(self):
        """Remove old request records"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = current_time - 3600  # Remove requests older than 1 hour
        for key in list(self.requests.keys()):
            self.requests[key] = [
                timestamp for timestamp in self.requests[key] if timestamp > cutoff_time
            ]
            if not self.requests[key]:
                del self.requests[key]

        self.last_cleanup = current_time

    def is_allowed(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed based on rate limit

        Args:
            key: Unique identifier for the client
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        self._cleanup_old_requests()

        current_time = time.time()
        window_start = current_time - window

        if key not in self.requests:
            self.requests[key] = []

        # Filter requests within the current window
        self.requests[key] = [
            timestamp for timestamp in self.requests[key] if timestamp > window_start
        ]

        request_count = len(self.requests[key])

        rate_limit_info = {
            "limit": limit,
            "remaining": max(0, limit - request_count),
            "reset_time": int(window_start + window),
            "retry_after": None,
        }

        if request_count >= limit:
            rate_limit_info["retry_after"] = int(window_start + window - current_time)
            return False, rate_limit_info

        # Add current request
        self.requests[key].append(current_time)
        rate_limit_info["remaining"] -= 1

        return True, rate_limit_info


class RedisRateLimiter:
    """Redis-based rate limiter for production use"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Test connection
            self.available = True
        except Exception:
            self.available = False
            self.fallback = InMemoryRateLimiter()

    def is_allowed(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, any]]:
        """Check if request is allowed using Redis sliding window"""
        if not self.available:
            return self.fallback.is_allowed(key, limit, window)

        try:
            current_time = time.time()
            window_start = current_time - window

            pipe = self.redis_client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, window)

            results = pipe.execute()
            request_count = results[1]

            rate_limit_info = {
                "limit": limit,
                "remaining": max(0, limit - request_count),
                "reset_time": int(current_time + window),
                "retry_after": None,
            }

            if request_count >= limit:
                # Remove the request we just added since it's not allowed
                self.redis_client.zrem(key, str(current_time))
                rate_limit_info["retry_after"] = window
                return False, rate_limit_info

            rate_limit_info["remaining"] -= 1
            return True, rate_limit_info

        except Exception:
            # Fallback to in-memory limiter
            return self.fallback.is_allowed(key, limit, window)


class RateLimitConfig:
    """Rate limit configuration for different endpoints"""

    # Default rate limits (requests per minute)
    DEFAULT_LIMITS = {
        "upload": (5, 60),  # 5 uploads per minute
        "llm": (20, 60),  # 20 LLM requests per minute
        "api": (100, 60),  # 100 API requests per minute
        "websocket": (50, 60),  # 50 WebSocket messages per minute
        "export": (10, 60),  # 10 exports per minute
        "auth": (10, 60),  # 10 auth attempts per minute
        "password_reset": (3, 60),  # 3 password resets per minute
    }

    # Burst limits (requests per second)
    BURST_LIMITS = {
        "upload": (2, 1),  # 2 uploads per second
        "llm": (5, 1),  # 5 LLM requests per second
        "api": (10, 1),  # 10 API requests per second
        "websocket": (10, 1),  # 10 WebSocket messages per second
        "export": (3, 1),  # 3 exports per second
        "auth": (2, 1),  # 2 auth attempts per second
        "password_reset": (1, 1),  # 1 password reset per second
    }

    # Strict limits for suspicious activity
    STRICT_LIMITS = {
        "upload": (2, 60),  # 2 uploads per minute
        "llm": (10, 60),  # 10 LLM requests per minute
        "api": (50, 60),  # 50 API requests per minute
        "websocket": (25, 60),  # 25 WebSocket messages per minute
        "export": (5, 60),  # 5 exports per minute
        "auth": (3, 60),  # 3 auth attempts per minute
    }


class AdaptiveRateLimiter:
    """Advanced rate limiter with adaptive limits based on user behavior"""

    def __init__(self):
        self.base_limiter = InMemoryRateLimiter()
        self.user_reputation: Dict[str, Dict[str, Any]] = {}
        self.suspicious_ips: set = set()
        self.blocked_ips: Dict[str, datetime] = {}

    def get_user_reputation(self, client_id: str) -> Dict[str, Any]:
        """Get user reputation data"""
        if client_id not in self.user_reputation:
            self.user_reputation[client_id] = {
                "score": 100,  # Start with good reputation
                "violations": 0,
                "last_violation": None,
                "total_requests": 0,
                "successful_requests": 0,
                "first_seen": datetime.now(),
            }
        return self.user_reputation[client_id]

    def update_reputation(
        self, client_id: str, success: bool, violation_type: str = None
    ):
        """Update user reputation based on behavior"""
        reputation = self.get_user_reputation(client_id)
        reputation["total_requests"] += 1

        if success:
            reputation["successful_requests"] += 1
            # Slowly improve reputation for good behavior
            if reputation["score"] < 100:
                reputation["score"] = min(100, reputation["score"] + 1)
        else:
            reputation["violations"] += 1
            reputation["last_violation"] = datetime.now()

            # Decrease reputation based on violation type
            penalty = {
                "rate_limit": 5,
                "security_violation": 15,
                "malicious_content": 25,
                "repeated_failures": 10,
            }.get(violation_type, 5)

            reputation["score"] = max(0, reputation["score"] - penalty)

            # Mark as suspicious if reputation is low
            if reputation["score"] < 30:
                self.suspicious_ips.add(client_id)

            # Block if reputation is very low
            if reputation["score"] < 10:
                self.blocked_ips[client_id] = datetime.now() + timedelta(hours=1)

    def is_blocked(self, client_id: str) -> bool:
        """Check if client is blocked"""
        if client_id in self.blocked_ips:
            if datetime.now() < self.blocked_ips[client_id]:
                return True
            else:
                # Unblock expired blocks
                del self.blocked_ips[client_id]
                if client_id in self.suspicious_ips:
                    self.suspicious_ips.remove(client_id)
        return False

    def get_adaptive_limits(self, client_id: str, limit_type: str) -> Tuple[int, int]:
        """Get adaptive rate limits based on user reputation"""
        if self.is_blocked(client_id):
            return (0, 60)  # Completely blocked

        reputation = self.get_user_reputation(client_id)
        base_limit, window = RateLimitConfig.DEFAULT_LIMITS.get(limit_type, (100, 60))

        # Adjust limits based on reputation
        if reputation["score"] >= 80:
            # Good reputation - normal limits
            return (base_limit, window)
        elif reputation["score"] >= 50:
            # Moderate reputation - slightly reduced limits
            return (int(base_limit * 0.8), window)
        elif reputation["score"] >= 30:
            # Poor reputation - reduced limits
            return (int(base_limit * 0.5), window)
        else:
            # Very poor reputation - strict limits
            strict_limit, _ = RateLimitConfig.STRICT_LIMITS.get(
                limit_type, (base_limit // 2, window)
            )
            return (strict_limit, window)

    def is_allowed(
        self, client_id: str, limit_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed with adaptive limits"""
        if self.is_blocked(client_id):
            return False, {
                "limit": 0,
                "remaining": 0,
                "reset_time": int(self.blocked_ips[client_id].timestamp()),
                "retry_after": int(
                    (self.blocked_ips[client_id] - datetime.now()).total_seconds()
                ),
                "reason": "blocked",
            }

        limit, window = self.get_adaptive_limits(client_id, limit_type)
        key = f"{limit_type}:{client_id}"

        return self.base_limiter.is_allowed(key, limit, window)


# Global rate limiter instance
rate_limiter = AdaptiveRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Get unique identifier for rate limiting"""
    # Try to get real IP from headers (for reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    # Include user agent for additional uniqueness
    user_agent = request.headers.get("User-Agent", "")

    # Create hash of IP + User Agent
    identifier = f"{client_ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"

    return identifier


async def check_rate_limit(
    request: Request,
    limit_type: str = "api",
    custom_limit: Optional[Tuple[int, int]] = None,
) -> Optional[JSONResponse]:
    """
    Check rate limit for a request

    Args:
        request: FastAPI request object
        limit_type: Type of rate limit to apply
        custom_limit: Custom (limit, window) tuple

    Returns:
        JSONResponse if rate limited, None if allowed
    """
    client_id = get_client_identifier(request)

    # Get rate limit configuration
    if custom_limit:
        limit, window = custom_limit
    else:
        limit, window = RateLimitConfig.DEFAULT_LIMITS.get(limit_type, (100, 60))

    # Check rate limit
    is_allowed, rate_info = rate_limiter.is_allowed(
        f"{limit_type}:{client_id}", limit, window
    )

    if not is_allowed:
        headers = {
            "X-RateLimit-Limit": str(rate_info["limit"]),
            "X-RateLimit-Remaining": str(rate_info["remaining"]),
            "X-RateLimit-Reset": str(rate_info["reset_time"]),
        }

        if rate_info["retry_after"]:
            headers["Retry-After"] = str(rate_info["retry_after"])

        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Too many {limit_type} requests. Try again later.",
                "retry_after": rate_info["retry_after"],
            },
            headers=headers,
        )

    return None


def rate_limit(limit_type: str = "api", custom_limit: Optional[Tuple[int, int]] = None):
    """Decorator for rate limiting endpoints"""

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Check rate limit
            rate_limit_response = await check_rate_limit(
                request, limit_type, custom_limit
            )
            if rate_limit_response:
                return rate_limit_response

            # Proceed with the original function
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


class RateLimitMiddleware:
    """Middleware for global rate limiting"""

    def __init__(self, app, default_limit: Tuple[int, int] = (100, 60)):
        self.app = app
        self.default_limit = default_limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/"]:
            await self.app(scope, receive, send)
            return

        # Check rate limit
        client_id = get_client_identifier(request)
        limit, window = self.default_limit

        is_allowed, rate_info = rate_limiter.is_allowed(
            f"global:{client_id}", limit, window
        )

        if not is_allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": rate_info["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset_time"]),
                    "Retry-After": (
                        str(rate_info["retry_after"])
                        if rate_info["retry_after"]
                        else "60"
                    ),
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

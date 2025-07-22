"""
Comprehensive caching service for performance optimization
"""

import asyncio
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum
import redis
import aioredis
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels for different types of data"""

    MEMORY = "memory"
    REDIS = "redis"
    PERSISTENT = "persistent"


@dataclass
class CacheConfig:
    """Cache configuration settings"""

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Cache TTL settings (in seconds)
    default_ttl: int = 3600  # 1 hour
    llm_response_ttl: int = 7200  # 2 hours
    resume_data_ttl: int = 1800  # 30 minutes
    job_analysis_ttl: int = 3600  # 1 hour
    user_session_ttl: int = 86400  # 24 hours

    # Memory cache settings
    max_memory_cache_size: int = 1000  # Maximum items in memory cache
    memory_cache_ttl: int = 300  # 5 minutes for memory cache

    # Performance settings
    enable_compression: bool = True
    compression_threshold: int = 1024  # Compress data larger than 1KB
    enable_cache_warming: bool = True

    # Cache key prefixes
    llm_prefix: str = "llm:"
    resume_prefix: str = "resume:"
    job_prefix: str = "job:"
    user_prefix: str = "user:"
    session_prefix: str = "session:"


class MemoryCache:
    """In-memory cache with LRU eviction"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.cache:
            return True

        entry = self.cache[key]
        if entry["expires_at"] and datetime.utcnow() > entry["expires_at"]:
            self._remove(key)
            return True

        return False

    def _remove(self, key: str):
        """Remove key from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)

    def _evict_lru(self):
        """Evict least recently used items"""
        while len(self.cache) >= self.max_size and self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]

    def _update_access_order(self, key: str):
        """Update access order for LRU"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self._is_expired(key):
            return None

        self._update_access_order(key)
        return self.cache[key]["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl

        expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None

        # Evict if necessary
        if key not in self.cache:
            self._evict_lru()

        self.cache[key] = {
            "value": value,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
        }

        self._update_access_order(key)
        return True

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            self._remove(key)
            return True
        return False

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries = sum(1 for key in self.cache.keys() if self._is_expired(key))

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "max_size": self.max_size,
            "utilization": (
                (total_entries / self.max_size) * 100 if self.max_size > 0 else 0
            ),
        }


class RedisCache:
    """Redis-based cache for distributed caching"""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self.connection_pool = None
        self.connected = False

    async def connect(self):
        """Connect to Redis"""
        try:
            self.connection_pool = aioredis.ConnectionPool.from_url(
                self.config.redis_url,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=False,  # We handle encoding ourselves
                max_connections=20,
            )

            self.redis_client = aioredis.Redis(connection_pool=self.connection_pool)

            # Test connection
            await self.redis_client.ping()
            self.connected = True
            logger.info("Connected to Redis cache")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
        if self.connection_pool:
            await self.connection_pool.disconnect()
        self.connected = False

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first for simple types
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                serialized = json.dumps(value).encode("utf-8")
            else:
                # Use pickle for complex objects
                serialized = pickle.dumps(value)

            # Compress if enabled and data is large enough
            if (
                self.config.enable_compression
                and len(serialized) > self.config.compression_threshold
            ):
                import gzip

                serialized = gzip.compress(serialized)
                # Add compression marker
                serialized = b"GZIP:" + serialized

            return serialized

        except Exception as e:
            logger.error(f"Failed to serialize value: {e}")
            raise

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            # Check for compression marker
            if data.startswith(b"GZIP:"):
                import gzip

                data = gzip.decompress(data[5:])  # Remove "GZIP:" prefix

            # Try JSON first
            try:
                return json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)

        except Exception as e:
            logger.error(f"Failed to deserialize value: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.connected:
            return None

        try:
            data = await self.redis_client.get(key)
            if data is None:
                return None

            return self._deserialize_value(data)

        except Exception as e:
            logger.error(f"Failed to get from Redis cache: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        if not self.connected:
            return False

        try:
            serialized_value = self._serialize_value(value)

            if ttl is None:
                ttl = self.config.default_ttl

            if ttl > 0:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)

            return True

        except Exception as e:
            logger.error(f"Failed to set in Redis cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.connected:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete from Redis cache: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        if not self.connected:
            return False

        try:
            result = await self.redis_client.exists(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to check existence in Redis cache: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.connected:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Failed to clear pattern from Redis cache: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        if not self.connected:
            return {"connected": False}

        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {"connected": False, "error": str(e)}


class CacheService:
    """Main cache service that manages multiple cache levels"""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.memory_cache = MemoryCache(
            max_size=self.config.max_memory_cache_size,
            default_ttl=self.config.memory_cache_ttl,
        )
        self.redis_cache = RedisCache(self.config)
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def start(self):
        """Start the cache service"""
        await self.redis_cache.connect()
        logger.info("Cache service started")

    async def stop(self):
        """Stop the cache service"""
        await self.redis_cache.disconnect()
        logger.info("Cache service stopped")

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        # Create a deterministic key from arguments
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}:{v}")
            else:
                key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")

        return ":".join(key_parts)

    async def get(
        self, key: str, cache_level: CacheLevel = CacheLevel.REDIS
    ) -> Optional[Any]:
        """Get value from cache"""

        # Try memory cache first (fastest)
        value = self.memory_cache.get(key)
        if value is not None:
            self.cache_stats["hits"] += 1
            return value

        # Try Redis cache if enabled
        if cache_level in [CacheLevel.REDIS, CacheLevel.PERSISTENT]:
            value = await self.redis_cache.get(key)
            if value is not None:
                # Store in memory cache for faster future access
                self.memory_cache.set(key, value)
                self.cache_stats["hits"] += 1
                return value

        self.cache_stats["misses"] += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        cache_level: CacheLevel = CacheLevel.REDIS,
    ) -> bool:
        """Set value in cache"""

        success = True

        # Always store in memory cache for fast access
        self.memory_cache.set(key, value, ttl or self.config.memory_cache_ttl)

        # Store in Redis if enabled
        if cache_level in [CacheLevel.REDIS, CacheLevel.PERSISTENT]:
            redis_success = await self.redis_cache.set(key, value, ttl)
            success = success and redis_success

        if success:
            self.cache_stats["sets"] += 1

        return success

    async def delete(self, key: str) -> bool:
        """Delete key from all cache levels"""
        memory_success = self.memory_cache.delete(key)
        redis_success = await self.redis_cache.delete(key)

        if memory_success or redis_success:
            self.cache_stats["deletes"] += 1
            return True

        return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern from all cache levels"""
        # Clear from memory cache
        memory_keys = [k for k in self.memory_cache.cache.keys() if pattern in k]
        for key in memory_keys:
            self.memory_cache.delete(key)

        # Clear from Redis cache
        redis_cleared = await self.redis_cache.clear_pattern(pattern)

        return len(memory_keys) + redis_cleared

    # Specialized cache methods for different data types

    async def cache_llm_response(
        self, provider: str, model: str, prompt: str, response: Any
    ) -> bool:
        """Cache LLM response"""
        key = self._generate_cache_key(self.config.llm_prefix, provider, model, prompt)
        return await self.set(key, response, self.config.llm_response_ttl)

    async def get_cached_llm_response(
        self, provider: str, model: str, prompt: str
    ) -> Optional[Any]:
        """Get cached LLM response"""
        key = self._generate_cache_key(self.config.llm_prefix, provider, model, prompt)
        return await self.get(key)

    async def cache_resume_data(self, resume_id: str, data: Dict[str, Any]) -> bool:
        """Cache resume data"""
        key = self._generate_cache_key(self.config.resume_prefix, resume_id)
        return await self.set(key, data, self.config.resume_data_ttl)

    async def get_cached_resume_data(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Get cached resume data"""
        key = self._generate_cache_key(self.config.resume_prefix, resume_id)
        return await self.get(key)

    async def cache_job_analysis(
        self, job_description_hash: str, analysis: Dict[str, Any]
    ) -> bool:
        """Cache job analysis results"""
        key = self._generate_cache_key(self.config.job_prefix, job_description_hash)
        return await self.set(key, analysis, self.config.job_analysis_ttl)

    async def get_cached_job_analysis(
        self, job_description_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached job analysis"""
        key = self._generate_cache_key(self.config.job_prefix, job_description_hash)
        return await self.get(key)

    async def cache_user_session(
        self, session_id: str, session_data: Dict[str, Any]
    ) -> bool:
        """Cache user session data"""
        key = self._generate_cache_key(self.config.session_prefix, session_id)
        return await self.set(key, session_data, self.config.user_session_ttl)

    async def get_cached_user_session(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached user session"""
        key = self._generate_cache_key(self.config.session_prefix, session_id)
        return await self.get(key)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        memory_stats = self.memory_cache.get_stats()

        return {
            "service_stats": self.cache_stats.copy(),
            "memory_cache": memory_stats,
            "redis_cache": None,  # Will be populated by async method
            "hit_rate": (
                self.cache_stats["hits"]
                / (self.cache_stats["hits"] + self.cache_stats["misses"])
                if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0
                else 0
            )
            * 100,
        }

    async def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics including Redis"""
        stats = self.get_cache_stats()
        stats["redis_cache"] = await self.redis_cache.get_stats()
        return stats


# Cache decorators for easy use


def cached(
    ttl: int = 3600,
    cache_level: CacheLevel = CacheLevel.REDIS,
    key_prefix: str = "func",
    include_self: bool = False,
):
    """
    Decorator to cache function results

    Args:
        ttl: Time to live in seconds
        cache_level: Cache level to use
        key_prefix: Prefix for cache keys
        include_self: Whether to include 'self' in cache key for methods
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache service instance
            cache_service = get_cache_service()

            # Generate cache key
            cache_args = args
            if not include_self and args and hasattr(args[0], "__class__"):
                # Skip 'self' parameter for methods
                cache_args = args[1:]

            cache_key = cache_service._generate_cache_key(
                key_prefix, func.__name__, *cache_args, **kwargs
            )

            # Try to get from cache
            cached_result = await cache_service.get(cache_key, cache_level)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_service.set(cache_key, result, ttl, cache_level)

            return result

        return wrapper

    return decorator


def cache_llm_response(ttl: int = 7200):
    """Decorator specifically for caching LLM responses"""
    return cached(ttl=ttl, key_prefix="llm", cache_level=CacheLevel.REDIS)


def cache_resume_operation(ttl: int = 1800):
    """Decorator for caching resume operations"""
    return cached(ttl=ttl, key_prefix="resume", cache_level=CacheLevel.REDIS)


def cache_job_operation(ttl: int = 3600):
    """Decorator for caching job analysis operations"""
    return cached(ttl=ttl, key_prefix="job", cache_level=CacheLevel.REDIS)


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def initialize_cache_service(config: Optional[CacheConfig] = None):
    """Initialize the global cache service"""
    global _cache_service
    _cache_service = CacheService(config)
    await _cache_service.start()


async def shutdown_cache_service():
    """Shutdown the global cache service"""
    global _cache_service
    if _cache_service:
        await _cache_service.stop()
        _cache_service = None

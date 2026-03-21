"""
Redis caching utility for improved performance.
"""
import json
import logging
from datetime import timedelta
from typing import Any, Optional

try:
    import redis
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache manager for IATRS.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        enabled: bool = True
    ):
        self.enabled = enabled and REDIS_AVAILABLE
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        
        if not self.enabled:
            logger.info("Redis caching is disabled or not available")
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get synchronous Redis client."""
        if not self.enabled:
            return None
        
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                # Test connection
                self._client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self.enabled = False
                return None
        
        return self._client
    
    @property
    async def async_client(self) -> Optional[aioredis.Redis]:
        """Get asynchronous Redis client."""
        if not self.enabled:
            return None
        
        if self._async_client is None:
            try:
                self._async_client = aioredis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                await self._async_client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
                self.enabled = False
                return None
        
        return self._async_client
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional expiration."""
        if not self.client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                return bool(self.client.setex(key, int(expire.total_seconds()), serialized))
            else:
                return bool(self.client.set(key, serialized))
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False
        
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        if not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error for pattern {pattern}: {e}")
            return 0
    
    # Async methods
    async def async_get(self, key: str) -> Optional[Any]:
        """Get value from cache asynchronously."""
        client = await self.async_client
        if not client:
            return None
        
        try:
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis async GET error for key {key}: {e}")
            return None
    
    async def async_set(
        self,
        key: str,
        value: Any,
        expire: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache asynchronously with optional expiration."""
        client = await self.async_client
        if not client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                return bool(await client.setex(key, int(expire.total_seconds()), serialized))
            else:
                return bool(await client.set(key, serialized))
        except Exception as e:
            logger.error(f"Redis async SET error for key {key}: {e}")
            return False
    
    async def async_delete(self, key: str) -> bool:
        """Delete key from cache asynchronously."""
        client = await self.async_client
        if not client:
            return False
        
        try:
            return bool(await client.delete(key))
        except Exception as e:
            logger.error(f"Redis async DELETE error for key {key}: {e}")
            return False


# Cache key templates
class CacheKeys:
    """Cache key templates for IATRS."""
    
    JOB = "job:{job_id}"
    JOB_LIST = "jobs:page:{page}:size:{size}"
    CANDIDATE = "candidate:{candidate_id}"
    APPLICATION = "application:{application_id}"
    APPLICATIONS_BY_JOB = "applications:job:{job_id}"
    INTERVIEW = "interview:{interview_id}"
    USER_PROFILE = "user:profile:{user_id}"
    ANALYTICS_DASHBOARD = "analytics:dashboard:{days}"
    STATS = "stats:{stat_type}"


# Global cache instance
cache = RedisCache()


def get_cache() -> RedisCache:
    """Get the global cache instance."""
    return cache


# Cache decorator for async functions
def cache_result(
    key_template: str,
    expire: timedelta = timedelta(minutes=30)
):
    """
    Decorator to cache function results.
    
    Usage:
        @cache_result("job:{job_id}", expire=timedelta(minutes=30))
        async def get_job(job_id: int):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Build cache key from arguments
            key = key_template.format(*args, **kwargs)
            
            # Try to get from cache
            cached = await cache.async_get(key)
            if cached:
                logger.debug(f"Cache hit for key: {key}")
                return cached
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.async_set(key, result, expire)
            logger.debug(f"Cache miss - stored result for key: {key}")
            
            return result
        return wrapper
    return decorator

"""
Redis-based caching system for BrowserBot performance optimization.
"""

import json
import hashlib
import base64
from typing import Optional, Any, Dict, Union, List
from datetime import timedelta
import redis
from redis.exceptions import RedisError
import logging
from functools import wraps
import pickle
import asyncio
from concurrent.futures import ThreadPoolExecutor

from browserbot.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching operations for BrowserBot with Redis backend."""
    
    def __init__(self, redis_url: Optional[str] = None, redis_password: Optional[str] = None):
        """Initialize cache manager with Redis connection."""
        self.redis_url = redis_url or settings.redis_url
        self.redis_password = redis_password or settings.redis_password
        self._redis_client = None
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        
    @property
    def redis_client(self) -> redis.Redis:
        """Lazy Redis client initialization."""
        if self._redis_client is None:
            try:
                # Parse URL and add password if needed
                if self.redis_password and 'redis://' in self.redis_url:
                    # Insert password into URL
                    parts = self.redis_url.split('://', 1)
                    if '@' not in parts[1]:
                        # No auth in URL, add it
                        host_parts = parts[1].split('/', 1)
                        redis_url = f"{parts[0]}://:{self.redis_password}@{parts[1]}"
                    else:
                        redis_url = self.redis_url
                else:
                    redis_url = self.redis_url
                    
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=False,  # Handle binary data
                    socket_keepalive=True,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self._redis_client.ping()
                logger.info("Redis cache connected successfully")
            except RedisError as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self._redis_client = None
        return self._redis_client
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        # Create a unique key from arguments
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        return f"browserbot:{prefix}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache asynchronously."""
        if not self.redis_client:
            return None
            
        try:
            # Run Redis operation in thread pool
            loop = asyncio.get_event_loop()
            value = await loop.run_in_executor(
                self._executor,
                self.redis_client.get,
                key
            )
            
            if value:
                self._cache_stats["hits"] += 1
                # Try to deserialize as JSON first, then pickle
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    try:
                        return pickle.loads(value)
                    except Exception:
                        return value.decode() if isinstance(value, bytes) else value
            else:
                self._cache_stats["misses"] += 1
                return None
                
        except Exception as e:
            self._cache_stats["errors"] += 1
            logger.debug(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache asynchronously."""
        if not self.redis_client:
            return False
            
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            elif isinstance(value, bytes):
                serialized = value
            else:
                serialized = pickle.dumps(value)
            
            # Run Redis operation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                lambda: self.redis_client.set(key, serialized, ex=ttl)
            )
            return bool(result)
            
        except Exception as e:
            self._cache_stats["errors"] += 1
            logger.debug(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
            
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self.redis_client.delete,
                key
            )
            return bool(result)
        except Exception as e:
            logger.debug(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self.redis_client:
            return 0
            
        try:
            loop = asyncio.get_event_loop()
            
            # Get all matching keys
            keys = await loop.run_in_executor(
                self._executor,
                lambda: list(self.redis_client.scan_iter(match=pattern))
            )
            
            if keys:
                # Delete all matching keys
                deleted = await loop.run_in_executor(
                    self._executor,
                    lambda: self.redis_client.delete(*keys)
                )
                return deleted
            return 0
            
        except Exception as e:
            logger.debug(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self._cache_stats,
            "total": total,
            "hit_rate": hit_rate
        }
    
    # Specialized caching methods
    
    async def cache_screenshot(self, url: str, selector: Optional[str], 
                             screenshot_data: bytes, ttl: int = 3600) -> bool:
        """Cache screenshot data with URL and selector as key."""
        key = self._generate_key("screenshot", url, selector or "full")
        return await self.set(key, screenshot_data, ttl)
    
    async def get_cached_screenshot(self, url: str, selector: Optional[str]) -> Optional[bytes]:
        """Get cached screenshot data."""
        key = self._generate_key("screenshot", url, selector or "full")
        return await self.get(key)
    
    async def cache_dom_snapshot(self, url: str, dom_data: Dict[str, Any], 
                                ttl: int = 1800) -> bool:
        """Cache DOM snapshot data."""
        key = self._generate_key("dom", url)
        return await self.set(key, dom_data, ttl)
    
    async def get_cached_dom_snapshot(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached DOM snapshot."""
        key = self._generate_key("dom", url)
        return await self.get(key)
    
    async def cache_ai_response(self, prompt_hash: str, response: str, 
                               model: str, ttl: int = 7200) -> bool:
        """Cache AI model response."""
        key = self._generate_key("ai_response", model, prompt_hash)
        return await self.set(key, response, ttl)
    
    async def get_cached_ai_response(self, prompt_hash: str, model: str) -> Optional[str]:
        """Get cached AI response."""
        key = self._generate_key("ai_response", model, prompt_hash)
        return await self.get(key)
    
    async def cache_extraction_result(self, url: str, extraction_prompt: str, 
                                    result: Any, ttl: int = 3600) -> bool:
        """Cache data extraction results."""
        key = self._generate_key("extraction", url, extraction_prompt)
        return await self.set(key, result, ttl)
    
    async def get_cached_extraction(self, url: str, extraction_prompt: str) -> Optional[Any]:
        """Get cached extraction result."""
        key = self._generate_key("extraction", url, extraction_prompt)
        return await self.get(key)


def cached(prefix: str, ttl: int = 3600):
    """Decorator for caching async function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Skip caching if disabled
            if not hasattr(self, '_cache_manager'):
                return await func(self, *args, **kwargs)
            
            # Generate cache key
            cache_key = self._cache_manager._generate_key(
                f"{prefix}:{func.__name__}", 
                *args, 
                **kwargs
            )
            
            # Try to get from cache
            cached_value = await self._cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
            
            # Execute function and cache result
            result = await func(self, *args, **kwargs)
            if result is not None:
                await self._cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Global cache manager instance
cache_manager = CacheManager()
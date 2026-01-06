"""
ERP Arabic OCR Microservice - Redis Cache Manager
==================================================
Caches OCR results to avoid redundant processing.
"""

import json
import time
import hashlib
import logging
import functools
from typing import Optional, Dict, Any, Callable, Union
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    errors: int = 0
    last_hit: Optional[datetime] = None
    last_miss: Optional[datetime] = None

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "errors": self.errors,
            "hit_rate": f"{self.hit_rate:.2%}",
            "last_hit": self.last_hit.isoformat() if self.last_hit else None,
            "last_miss": self.last_miss.isoformat() if self.last_miss else None
        }


class OCRCacheManager:
    """
    Redis-based cache manager for OCR results.

    Features:
    - Image hash-based cache keys
    - Configurable TTL
    - Cache statistics tracking
    - Fallback to in-memory cache if Redis unavailable
    - Decorator for easy caching
    """

    # Cache key prefix
    KEY_PREFIX = "ocr:v2:"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600,
        enabled: bool = True,
        use_memory_fallback: bool = True
    ):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Default TTL for cached items
            enabled: Whether caching is enabled
            use_memory_fallback: Use in-memory cache if Redis unavailable
        """
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled
        self.use_memory_fallback = use_memory_fallback

        self._redis_client = None
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._stats = CacheStats()

        if enabled:
            self._init_redis(redis_url)

    def _init_redis(self, redis_url: Optional[str] = None) -> None:
        """Initialize Redis connection."""
        try:
            import redis

            if redis_url is None:
                from config.settings import get_settings
                settings = get_settings()
                redis_url = settings.cache.redis_url

            self._redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )

            # Test connection
            self._redis_client.ping()
            logger.info(f"Redis cache connected: {redis_url[:30]}...")

        except ImportError:
            logger.warning("Redis package not installed, using memory fallback")
            self._redis_client = None

        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, using memory fallback")
            self._redis_client = None

    def get_image_hash(self, image_data: Union[bytes, str]) -> str:
        """
        Generate SHA-256 hash for image data.

        Args:
            image_data: Image bytes or file path

        Returns:
            Hex-encoded hash string
        """
        if isinstance(image_data, str):
            # Read file
            with open(image_data, 'rb') as f:
                image_data = f.read()

        return hashlib.sha256(image_data).hexdigest()

    def _make_key(self, image_hash: str, options: Optional[Dict] = None) -> str:
        """
        Generate cache key from image hash and options.

        Args:
            image_hash: Image content hash
            options: Processing options (engine_mode, etc.)

        Returns:
            Cache key string
        """
        key = f"{self.KEY_PREFIX}{image_hash}"

        if options:
            # Include relevant options in key
            opt_str = "_".join(f"{k}={v}" for k, v in sorted(options.items()))
            key = f"{key}:{hashlib.md5(opt_str.encode()).hexdigest()[:8]}"

        return key

    def get(
        self,
        image_hash: str,
        options: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached OCR result.

        Args:
            image_hash: Image content hash
            options: Processing options

        Returns:
            Cached result dict or None if not found
        """
        if not self.enabled:
            return None

        key = self._make_key(image_hash, options)

        try:
            # Try Redis first
            if self._redis_client:
                data = self._redis_client.get(key)
                if data:
                    self._stats.hits += 1
                    self._stats.last_hit = datetime.utcnow()
                    logger.debug(f"Cache hit: {key[:50]}")
                    return json.loads(data)

            # Try memory fallback
            elif self.use_memory_fallback and key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if time.time() < expiry:
                    self._stats.hits += 1
                    self._stats.last_hit = datetime.utcnow()
                    logger.debug(f"Memory cache hit: {key[:50]}")
                    return value
                else:
                    # Expired
                    del self._memory_cache[key]

            self._stats.misses += 1
            self._stats.last_miss = datetime.utcnow()
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self._stats.errors += 1
            return None

    def set(
        self,
        image_hash: str,
        result: Dict[str, Any],
        options: Optional[Dict] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store OCR result in cache.

        Args:
            image_hash: Image content hash
            result: OCR result to cache
            options: Processing options
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if stored successfully
        """
        if not self.enabled:
            return False

        key = self._make_key(image_hash, options)
        ttl = ttl or self.ttl_seconds

        try:
            data = json.dumps(result, ensure_ascii=False)

            # Try Redis
            if self._redis_client:
                self._redis_client.setex(key, ttl, data)
                self._stats.sets += 1
                logger.debug(f"Cached: {key[:50]} (TTL: {ttl}s)")
                return True

            # Memory fallback
            elif self.use_memory_fallback:
                expiry = time.time() + ttl
                self._memory_cache[key] = (result, expiry)
                self._stats.sets += 1

                # Cleanup old entries (simple LRU)
                self._cleanup_memory_cache()
                return True

            return False

        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self._stats.errors += 1
            return False

    def invalidate(
        self,
        image_hash: str,
        options: Optional[Dict] = None
    ) -> bool:
        """
        Invalidate cached result.

        Args:
            image_hash: Image content hash
            options: Processing options

        Returns:
            True if invalidated
        """
        key = self._make_key(image_hash, options)

        try:
            if self._redis_client:
                return bool(self._redis_client.delete(key))

            elif self.use_memory_fallback and key in self._memory_cache:
                del self._memory_cache[key]
                return True

            return False

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
            return False

    def invalidate_all(self) -> int:
        """
        Invalidate all OCR cache entries.

        Returns:
            Number of entries invalidated
        """
        count = 0

        try:
            if self._redis_client:
                keys = self._redis_client.keys(f"{self.KEY_PREFIX}*")
                if keys:
                    count = self._redis_client.delete(*keys)

            elif self.use_memory_fallback:
                count = len(self._memory_cache)
                self._memory_cache.clear()

            logger.info(f"Invalidated {count} cache entries")
            return count

        except Exception as e:
            logger.error(f"Cache invalidate_all error: {e}")
            return 0

    def cached_ocr(
        self,
        ttl: Optional[int] = None,
        include_options: bool = True
    ) -> Callable:
        """
        Decorator for caching OCR processing results.

        Args:
            ttl: Cache TTL in seconds
            include_options: Include processing options in cache key

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(image_data: Union[bytes, str], **kwargs):
                # Generate cache key
                if isinstance(image_data, str):
                    with open(image_data, 'rb') as f:
                        img_bytes = f.read()
                else:
                    img_bytes = image_data

                image_hash = self.get_image_hash(img_bytes)
                options = kwargs if include_options else None

                # Check cache
                cached = self.get(image_hash, options)
                if cached is not None:
                    logger.debug(f"Returning cached result for {image_hash[:16]}")
                    return cached

                # Process
                result = func(image_data, **kwargs)

                # Cache result
                if result:
                    # Convert to dict if needed
                    if hasattr(result, 'to_dict'):
                        cache_data = result.to_dict()
                    else:
                        cache_data = result

                    self.set(image_hash, cache_data, options, ttl)

                return result

            return wrapper
        return decorator

    def _cleanup_memory_cache(self, max_entries: int = 1000) -> None:
        """Remove expired and excess entries from memory cache."""
        now = time.time()

        # Remove expired
        expired = [k for k, (_, exp) in self._memory_cache.items() if exp < now]
        for k in expired:
            del self._memory_cache[k]

        # Remove oldest if over limit
        if len(self._memory_cache) > max_entries:
            sorted_keys = sorted(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k][1]
            )
            for k in sorted_keys[:len(self._memory_cache) - max_entries]:
                del self._memory_cache[k]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._stats.to_dict()
        stats["enabled"] = self.enabled
        stats["backend"] = "redis" if self._redis_client else "memory"
        stats["memory_entries"] = len(self._memory_cache)
        return stats

    def is_available(self) -> bool:
        """Check if caching is available."""
        if not self.enabled:
            return False

        if self._redis_client:
            try:
                self._redis_client.ping()
                return True
            except:
                return False

        return self.use_memory_fallback

    def health_check(self) -> Dict[str, Any]:
        """Health check for cache system."""
        status = "healthy"
        details = {}

        if not self.enabled:
            status = "disabled"
        elif self._redis_client:
            try:
                self._redis_client.ping()
                info = self._redis_client.info("memory")
                details = {
                    "backend": "redis",
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0)
                }
            except Exception as e:
                status = "degraded"
                details = {"error": str(e), "backend": "memory_fallback"}
        else:
            details = {
                "backend": "memory",
                "entries": len(self._memory_cache)
            }

        return {
            "status": status,
            "details": details,
            "stats": self._stats.to_dict()
        }


# Singleton instance
_cache_manager: Optional[OCRCacheManager] = None


def get_cache_manager() -> OCRCacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        try:
            from config.settings import get_settings
            settings = get_settings()
            _cache_manager = OCRCacheManager(
                redis_url=settings.cache.redis_url,
                ttl_seconds=settings.cache.ttl_seconds,
                enabled=settings.cache.enabled
            )
        except:
            _cache_manager = OCRCacheManager(enabled=True)
    return _cache_manager


# Export
__all__ = [
    "OCRCacheManager",
    "CacheStats",
    "get_cache_manager"
]

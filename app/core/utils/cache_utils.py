"""
Redis caching utility functions with metrics integration
공통 캐시 작업 유틸리티

Updated: 2025-11-21 (Cache Metrics Integration - MEDIUM PRIORITY #8)
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

import redis

from ..config import config


logger = logging.getLogger(__name__)

try:
    from app.core.monitoring.cache_metrics import cache_metrics

    METRICS_ENABLED = True
except ImportError:
    logger.warning("Cache metrics not available - metrics collection disabled")
    METRICS_ENABLED = False


def get_redis_client() -> Optional[redis.Redis]:
    """Redis 클라이언트 생성 및 반환. 연결 실패 시 None."""
    try:
        client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        logger.info("Redis cache client created successfully")
        return client
    except Exception as e:
        logger.warning(f"Redis cache unavailable: {e}")
        return None


def _record_metric(method_name: str, **kwargs: Any) -> None:
    """Record cache metric safely (swallow errors)."""
    if not METRICS_ENABLED:
        return
    try:
        method = getattr(cache_metrics, method_name, None)
        if method:
            method(**kwargs)
    except Exception as e:
        logger.warning(f"Failed to record cache {method_name} metric: {e}")


def _serialize_value(value: Any) -> str:
    """Serialize a value for Redis storage."""
    if isinstance(value, (dict, list, tuple, bool)):
        return json.dumps(value)
    return str(value)


def _deserialize_value(raw: str) -> Any:
    """Deserialize a Redis string, falling back to raw string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


class CacheManager:
    """Redis 캐시 매니저 클래스"""

    def __init__(self, ttl: int = 300, key_prefix: str = ""):
        self.redis_client = get_redis_client()
        self.ttl = ttl
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def get(self, key: str, default: Any = None) -> Any:
        """캐시에서 값 조회 (메트릭 수집 포함)."""
        if not self.redis_client:
            return default

        full_key = self._make_key(key)
        start_time = time.time()

        try:
            cached = self.redis_client.get(full_key)
            latency_ms = (time.time() - start_time) * 1000

            if cached is None:
                _record_metric("record_miss", cache_key=full_key, latency_ms=latency_ms)
                return default

            _record_metric("record_hit", cache_key=full_key, latency_ms=latency_ms)
            return _deserialize_value(cached)

        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            _record_metric("record_error", cache_key=full_key, operation="get", error_message=str(e))
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """캐시에 값 저장 (메트릭 수집 포함)."""
        if not self.redis_client:
            return False

        full_key = self._make_key(key)

        try:
            cache_ttl = ttl if ttl is not None else self.ttl
            serialized = _serialize_value(value)
            size_bytes = len(serialized.encode("utf-8"))

            self.redis_client.setex(full_key, cache_ttl, serialized)
            _record_metric("record_set", cache_key=full_key, ttl=cache_ttl, size_bytes=size_bytes)
            return True

        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            _record_metric("record_error", cache_key=full_key, operation="set", error_message=str(e))
            return False

    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제 (메트릭 수집 포함)."""
        if not self.redis_client:
            return False

        full_key = self._make_key(key)

        try:
            self.redis_client.delete(full_key)
            _record_metric("record_delete", cache_key=full_key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            _record_metric("record_error", cache_key=full_key, operation="delete", error_message=str(e))
            return False

    def exists(self, key: str) -> bool:
        """캐시에 키가 존재하는지 확인."""
        if not self.redis_client:
            return False

        try:
            return bool(self.redis_client.exists(self._make_key(key)))
        except Exception as e:
            logger.warning(f"Cache exists check error for key '{key}': {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """패턴에 맞는 모든 키 삭제."""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(self._make_key(pattern))
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear pattern error for pattern '{pattern}': {e}")
            return 0


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    함수 결과를 캐시하는 데코레이터

    사용 예시:
        @cached(ttl=600, key_prefix="stats")
        def get_statistics(user_id: str):
            return expensive_calculation(user_id)
    """

    def decorator(func: Callable) -> Callable:
        cache_manager = CacheManager(ttl=ttl, key_prefix=key_prefix)

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)
            return result

        return wrapper

    return decorator

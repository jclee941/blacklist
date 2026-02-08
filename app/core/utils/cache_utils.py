"""
Redis caching utility functions with metrics integration
공통 캐시 작업 유틸리티

Updated: 2025-11-21 (Cache Metrics Integration - MEDIUM PRIORITY #8)
Reference: docs/108-REDIS-CACHING-IMPLEMENTATION.md
"""

import os
import redis
import json
import logging
import time
from typing import Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Import cache metrics collector
try:
    from app.core.monitoring.cache_metrics import cache_metrics

    METRICS_ENABLED = True
except ImportError:
    logger.warning("Cache metrics not available - metrics collection disabled")
    METRICS_ENABLED = False


def get_redis_client() -> Optional[redis.Redis]:
    """
    Redis 클라이언트 생성 및 반환

    Returns:
        Redis client or None (연결 실패 시)
    """
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "blacklist-redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # 연결 테스트
        client.ping()
        logger.info("✅ Redis cache client created successfully")
        return client
    except Exception as e:
        logger.warning(f"⚠️ Redis cache unavailable: {e}")
        return None


class CacheManager:
    """Redis 캐시 매니저 클래스"""

    def __init__(self, ttl: int = 300, key_prefix: str = ""):
        """
        Args:
            ttl: Time to live (초 단위, 기본값: 300초 = 5분)
            key_prefix: 캐시 키 접두사
        """
        self.redis_client = get_redis_client()
        self.ttl = ttl
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        """캐시 키 생성"""
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def get(self, key: str, default: Any = None) -> Any:
        """
        캐시에서 값 조회 (메트릭 수집 포함)

        Args:
            key: 캐시 키
            default: 캐시 미스 시 반환할 기본값

        Returns:
            캐시된 값 또는 default
        """
        if not self.redis_client:
            return default

        start_time = time.time()

        try:
            cached = self.redis_client.get(self._make_key(key))
            latency_ms = (time.time() - start_time) * 1000

            if cached is None:
                # Cache miss - record metrics
                if METRICS_ENABLED:
                    try:
                        cache_metrics.record_miss(cache_key=self._make_key(key), latency_ms=latency_ms)
                    except Exception as e:
                        logger.warning(f"Failed to record cache miss metric: {e}")

                return default

            # Cache hit - record metrics
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_hit(cache_key=self._make_key(key), latency_ms=latency_ms)
                except Exception as e:
                    logger.warning(f"Failed to record cache hit metric: {e}")

            # JSON 파싱 시도 (실패 시 원본 문자열 반환)
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError):
                return cached

        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")

            # Record error metric
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_error(cache_key=self._make_key(key), operation="get", error_message=str(e))
                except Exception:
                    pass

            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        캐시에 값 저장 (메트릭 수집 포함)

        Args:
            key: 캐시 키
            value: 저장할 값
            ttl: Time to live (None이면 인스턴스 기본값 사용)

        Returns:
            성공 여부
        """
        if not self.redis_client:
            return False

        try:
            cache_ttl = ttl if ttl is not None else self.ttl

            # JSON 직렬화 가능한 값은 JSON으로 저장
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value)
            elif isinstance(value, bool):
                value = json.dumps(value)
            else:
                value = str(value)

            # Calculate approximate size
            size_bytes = len(str(value).encode("utf-8"))

            self.redis_client.setex(self._make_key(key), cache_ttl, value)

            # Record set metric
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_set(cache_key=self._make_key(key), ttl=cache_ttl, size_bytes=size_bytes)
                except Exception as e:
                    logger.warning(f"Failed to record cache set metric: {e}")

            return True

        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")

            # Record error metric
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_error(cache_key=self._make_key(key), operation="set", error_message=str(e))
                except Exception:
                    pass

            return False

    def delete(self, key: str) -> bool:
        """
        캐시에서 값 삭제 (메트릭 수집 포함)

        Args:
            key: 캐시 키

        Returns:
            성공 여부
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.delete(self._make_key(key))

            # Record delete metric
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_delete(cache_key=self._make_key(key))
                except Exception as e:
                    logger.warning(f"Failed to record cache delete metric: {e}")

            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")

            # Record error metric
            if METRICS_ENABLED:
                try:
                    cache_metrics.record_error(cache_key=self._make_key(key), operation="delete", error_message=str(e))
                except Exception:
                    pass

            return False

    def exists(self, key: str) -> bool:
        """
        캐시에 키가 존재하는지 확인

        Args:
            key: 캐시 키

        Returns:
            존재 여부
        """
        if not self.redis_client:
            return False

        try:
            return bool(self.redis_client.exists(self._make_key(key)))
        except Exception as e:
            logger.warning(f"Cache exists check error for key '{key}': {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        패턴에 맞는 모든 키 삭제

        Args:
            pattern: 패턴 (예: "user:*")

        Returns:
            삭제된 키 개수
        """
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
            # 비용이 높은 연산
            return expensive_calculation(user_id)

    Args:
        ttl: Time to live (초 단위)
        key_prefix: 캐시 키 접두사
    """

    def decorator(func: Callable) -> Callable:
        cache_manager = CacheManager(ttl=ttl, key_prefix=key_prefix)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성 (함수명 + 인자)
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # 캐시 확인
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # 함수 실행 및 캐시 저장
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result)

            return result

        return wrapper

    return decorator

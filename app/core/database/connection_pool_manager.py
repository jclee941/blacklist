#!/usr/bin/env python3
"""
스마트 PostgreSQL 연결 관리자 - 반복 오류 방지 및 로깅 개선
"""

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg2

from ..config import config

logger = logging.getLogger(__name__)


class SmartConnectionManager:
    """
    스마트 PostgreSQL 연결 관리자
    - 반복적 오류 로깅 방지
    - 연결 실패 시 캐시된 결과 반환
    - 백오프 전략 적용
    """

    def __init__(self):
        self.connection_params = config.get_postgres_params()
        self._last_error_time = None
        self._error_count = 0
        self._cached_stats: Optional[Dict[str, Any]] = None
        self._cache_timeout = 300
        self._backoff_duration = 60
        self._max_error_logs = 5

    def _should_suppress_error_logging(self) -> bool:
        """오류 로깅을 억제할지 결정"""
        now = datetime.now()

        # 처음 오류이거나 백오프 시간이 지났으면 로깅 허용
        if self._last_error_time is None:
            return False

        time_since_error = (now - self._last_error_time).total_seconds()

        # 백오프 기간 내이고 최대 로그 수를 초과했으면 억제
        if time_since_error < self._backoff_duration and self._error_count >= self._max_error_logs:
            return True

        # 백오프 기간이 지났으면 카운터 리셋
        if time_since_error >= self._backoff_duration:
            self._error_count = 0

        return False

    def _log_connection_error(self, error: Exception, host: str):
        """연결 오류 로깅 (억제 로직 포함)"""
        if self._should_suppress_error_logging():
            return

        self._error_count += 1
        self._last_error_time = datetime.now()

        if self._error_count == self._max_error_logs:
            logger.warning(
                f"PostgreSQL 연결 실패 ({host}): {error} (이후 {self._backoff_duration}초 동안 유사 오류 로깅 억제)"
            )
        else:
            logger.warning(f"PostgreSQL 연결 실패 ({host}): {error}")

    def get_connection(self) -> Optional[psycopg2.extensions.connection]:
        """PostgreSQL 연결 시도 (스마트 백오프 포함)"""
        hosts_to_try = [self.connection_params["host"]] + [
            h for h in config.POSTGRES_FALLBACK_HOSTS if h != self.connection_params["host"]
        ]

        for host in hosts_to_try:
            try:
                params = self.connection_params.copy()
                params["host"] = host
                params["connect_timeout"] = 3

                conn = psycopg2.connect(**params)

                # 연결 성공 시 오류 카운터 리셋
                self._error_count = 0
                self._last_error_time = None
                logger.info(f"PostgreSQL 연결 성공: {host}")
                return conn

            except Exception as e:
                self._log_connection_error(e, host)
                continue

        return None

    def get_stats_with_graceful_degradation(self) -> Dict[str, Any]:
        """PostgreSQL 통계 조회 (우아한 성능 저하 포함)"""
        # 캐시된 결과가 있고 유효하면 반환
        if (
            self._cached_stats
            and self._cached_stats.get("cached_at")
            and (datetime.now() - self._cached_stats["cached_at"]).total_seconds() < self._cache_timeout
        ):
            return self._cached_stats["data"]

        conn = self.get_connection()
        if not conn:
            # 연결 실패 시 기본값 반환 (오류 로깅은 get_connection에서 처리됨)
            fallback_stats = {
                "status": "degraded",
                "message": "PostgreSQL 연결 불가 - 캐시된 데이터 사용 중",
                "tables": 0,
                "connections": 0,
                "last_attempt": datetime.now().isoformat(),
            }

            # 캐시된 데이터가 있으면 그것을 우선 사용
            if self._cached_stats:
                cached_data = self._cached_stats["data"].copy()
                cached_data.update(
                    {
                        "status": "degraded",
                        "message": (
                            f"캐시된 데이터 (마지막 업데이트: {self._cached_stats['cached_at'].strftime('%H:%M:%S')})"
                        ),
                    }
                )
                return cached_data

            return fallback_stats

        try:
            with conn.cursor() as cursor:
                # 테이블 수 조회
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public'
                """
                )
                row = cursor.fetchone()
                table_count = row[0] if row else 0

                # 활성 연결 수 조회
                cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
                row = cursor.fetchone()
                connection_count = row[0] if row else 0

                stats = {
                    "status": "connected",
                    "message": "PostgreSQL 연결 정상",
                    "tables": table_count,
                    "connections": connection_count,
                    "host": conn.get_dsn_parameters().get("host", "unknown"),
                    "last_updated": datetime.now().isoformat(),
                }

                # 결과 캐시
                self._cached_stats = {"data": stats, "cached_at": datetime.now()}

                return stats

        except Exception as e:
            logger.error(f"PostgreSQL 통계 조회 실패: {e}")
            return {
                "status": "error",
                "message": f"쿼리 실패: {str(e)}",
                "tables": 0,
                "connections": 0,
            }
        finally:
            if conn:
                conn.close()


# 전역 스마트 연결 관리자
smart_connection_manager = SmartConnectionManager()


def get_postgres_stats_smart():
    """개선된 PostgreSQL 통계 조회"""
    return smart_connection_manager.get_stats_with_graceful_degradation()


def test_smart_connection():
    """스마트 연결 테스트"""
    conn = smart_connection_manager.get_connection()
    if conn:
        conn.close()
        return True
    return False


if __name__ == "__main__":
    # 테스트 실행
    logger.info("스마트 PostgreSQL 연결 테스트:")
    for i in range(3):
        stats = get_postgres_stats_smart()
        logger.info(f"테스트 {i + 1}: {stats}")
        time.sleep(1)

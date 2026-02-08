"""
Rate Limiter Module
Token Bucket 알고리즘 기반 API 요청 제한
외부 API 차단 방지를 위한 지능형 레이트 리미터
"""

import time
import logging
from threading import Lock
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token Bucket 알고리즘 기반 레이트 리미터

    특징:
    - 요청당 토큰 소비
    - 시간 경과에 따른 토큰 자동 재충전
    - 버스트 트래픽 허용 (최대 토큰 수 제한)
    - 스레드 안전
    """

    def __init__(
        self,
        requests_per_second: float = 2.0,  # 초당 2개 요청 (보수적)
        burst_size: int = 5,  # 버스트 허용 (최대 5개)
        backoff_factor: float = 2.0,  # 백오프 배수
        max_backoff: float = 300.0,  # 최대 백오프 시간 (5분)
    ):
        """
        레이트 리미터 초기화

        Args:
            requests_per_second: 초당 허용 요청 수 (2.0 = 0.5초마다 1개)
            burst_size: 버스트 모드에서 허용되는 최대 토큰 수
            backoff_factor: 실패 시 백오프 증가 배수
            max_backoff: 최대 백오프 대기 시간 (초)
        """
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff

        # Token bucket 상태
        self.tokens = float(burst_size)  # 초기 토큰 = 버스트 크기
        self.last_refill = time.time()
        self.lock = Lock()

        # Backoff 상태
        self.failure_count = 0
        self.current_backoff = 0.0
        self.last_request_time = 0.0

        # 통계 추적
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0
        self.request_history = deque(maxlen=1000)  # 최근 1000개 요청 추적

        logger.info(f"🚦 레이트 리미터 초기화: {requests_per_second} req/s, 버스트={burst_size}")

    def _refill_tokens(self):
        """시간 경과에 따른 토큰 재충전"""
        now = time.time()
        elapsed = now - self.last_refill

        # 경과 시간 동안 생성된 토큰 수
        new_tokens = elapsed * self.rate

        # 토큰 추가 (버스트 크기 제한)
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_refill = now

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        토큰 획득 (요청 허가)

        Args:
            tokens: 소비할 토큰 수 (기본 1)
            timeout: 최대 대기 시간 (None = 무제한)

        Returns:
            True: 토큰 획득 성공
            False: 타임아웃 또는 획득 실패
        """
        start_time = time.time()

        with self.lock:
            while True:
                self._refill_tokens()

                # 토큰이 충분하면 소비
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    self.total_requests += 1
                    self.last_request_time = time.time()

                    # 통계 기록
                    wait_time = time.time() - start_time
                    if wait_time > 0:
                        self.total_waits += 1
                        self.total_wait_time += wait_time

                    self.request_history.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "tokens": tokens,
                            "wait_time": wait_time,
                            "remaining_tokens": self.tokens,
                        }
                    )

                    logger.debug(f"✅ 토큰 획득: {tokens}개 소비, 잔여={self.tokens:.2f}, 대기={wait_time:.3f}초")
                    return True

                # 타임아웃 확인
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        logger.warning(f"⏰ 토큰 획득 타임아웃: {timeout}초")
                        return False

                # 다음 토큰이 생성될 때까지 대기 시간 계산
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate

                # 최소 대기 시간 (과도한 CPU 사용 방지)
                wait_time = max(0.01, wait_time)

                logger.debug(f"⏳ 토큰 대기: {wait_time:.3f}초")
                time.sleep(wait_time)

    def wait_if_needed(self):
        """필요 시 대기 (단순 인터페이스)"""
        return self.acquire(tokens=1)

    def on_success(self):
        """요청 성공 시 호출 - 백오프 리셋"""
        with self.lock:
            if self.failure_count > 0:
                logger.info("✅ 요청 성공 - 백오프 리셋")
                self.failure_count = 0
                self.current_backoff = 0.0

    def on_failure(self, error_code: Optional[int] = None):
        """
        요청 실패 시 호출 - 백오프 증가

        Args:
            error_code: HTTP 에러 코드 (429, 503 등)
        """
        with self.lock:
            self.failure_count += 1

            # 백오프 시간 계산 (지수적 증가)
            self.current_backoff = min(self.max_backoff, (self.backoff_factor**self.failure_count) * 0.5)

            # Rate Limit 에러 (429) 또는 서버 과부하 (503)인 경우 더 긴 대기
            if error_code in [429, 503]:
                self.current_backoff = min(self.max_backoff, self.current_backoff * 2)
                logger.warning(f"⚠️ API Rate Limit 감지 (HTTP {error_code}): {self.current_backoff:.2f}초 대기")
            else:
                logger.warning(f"⚠️ 요청 실패 #{self.failure_count}: {self.current_backoff:.2f}초 백오프")

            # 백오프 대기
            if self.current_backoff > 0:
                logger.info(f"⏸️  백오프 대기: {self.current_backoff:.2f}초")
                time.sleep(self.current_backoff)

    def get_stats(self) -> Dict[str, Any]:
        """레이트 리미터 통계 반환"""
        with self.lock:
            avg_wait_time = self.total_wait_time / self.total_waits if self.total_waits > 0 else 0

            # 최근 1분간 요청 수 계산
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            recent_requests = sum(
                1 for req in self.request_history if datetime.fromisoformat(req["timestamp"]) > one_minute_ago
            )

            return {
                "rate_limit": f"{self.rate} req/s",
                "burst_size": self.burst_size,
                "current_tokens": round(self.tokens, 2),
                "total_requests": self.total_requests,
                "total_waits": self.total_waits,
                "avg_wait_time": round(avg_wait_time, 3),
                "failure_count": self.failure_count,
                "current_backoff": round(self.current_backoff, 2),
                "requests_last_minute": recent_requests,
                "last_request": (
                    datetime.fromtimestamp(self.last_request_time).isoformat() if self.last_request_time > 0 else None
                ),
            }

    def reset(self):
        """레이트 리미터 리셋"""
        with self.lock:
            self.tokens = float(self.burst_size)
            self.last_refill = time.time()
            self.failure_count = 0
            self.current_backoff = 0.0
            logger.info("🔄 레이트 리미터 리셋")


class AdaptiveRateLimiter(RateLimiter):
    """
    적응형 레이트 리미터

    외부 API 응답에 따라 자동으로 요청 속도를 조절
    성공률이 높으면 속도 증가, 실패율이 높으면 속도 감소
    """

    def __init__(
        self,
        initial_rate: float = 2.0,
        min_rate: float = 0.5,
        max_rate: float = 5.0,
        **kwargs,
    ):
        """
        적응형 레이트 리미터 초기화

        Args:
            initial_rate: 초기 요청 속도
            min_rate: 최소 요청 속도
            max_rate: 최대 요청 속도
        """
        super().__init__(requests_per_second=initial_rate, **kwargs)
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.initial_rate = initial_rate

        # 적응형 조절 변수
        self.success_streak = 0
        self.failure_streak = 0
        self.rate_adjustment_threshold = 10  # 10번 연속 성공/실패 시 조절

        logger.info(f"🎯 적응형 레이트 리미터 초기화: {initial_rate} req/s (범위: {min_rate}-{max_rate})")

    def on_success(self):
        """요청 성공 시 - 속도 증가 고려"""
        super().on_success()

        with self.lock:
            self.success_streak += 1
            self.failure_streak = 0

            # 연속 성공이 임계값 초과 시 속도 증가
            if self.success_streak >= self.rate_adjustment_threshold and self.rate < self.max_rate:
                old_rate = self.rate
                self.rate = min(self.max_rate, self.rate * 1.2)  # 20% 증가
                logger.info(
                    f"📈 요청 속도 증가: {old_rate:.2f} → {self.rate:.2f} req/s (연속 성공 {self.success_streak}회)"
                )
                self.success_streak = 0

    def on_failure(self, error_code: Optional[int] = None):
        """요청 실패 시 - 속도 감소"""
        super().on_failure(error_code)

        with self.lock:
            self.failure_streak += 1
            self.success_streak = 0

            # 실패 시 즉시 속도 감소
            if self.rate > self.min_rate:
                old_rate = self.rate
                self.rate = max(self.min_rate, self.rate * 0.5)  # 50% 감소
                logger.warning(
                    f"📉 요청 속도 감소: {old_rate:.2f} → {self.rate:.2f} req/s (실패 {self.failure_streak}회)"
                )

    def reset(self):
        """리셋 시 초기 속도로 복원"""
        super().reset()
        with self.lock:
            self.rate = self.initial_rate
            self.success_streak = 0
            self.failure_streak = 0


class AuthRateLimiter(RateLimiter):
    """
    인증 전용 레이트 리미터

    특징:
    - 매우 보수적인 속도 (계정 잠금 방지)
    - 연속 실패 시 장시간 대기
    - 인증 성공 시에만 리셋
    """

    def __init__(
        self,
        requests_per_second: float = 0.2,  # 5초에 1번 (매우 보수적)
        max_attempts: int = 3,  # 최대 3회 시도
        lockout_duration: float = 600.0,  # 10분 잠금
        **kwargs,
    ):
        """
        인증 전용 레이트 리미터 초기화

        Args:
            requests_per_second: 초당 허용 요청 수 (기본 0.2 = 5초 간격)
            max_attempts: 연속 실패 허용 횟수
            lockout_duration: 최대 시도 초과 시 잠금 시간 (초)
        """
        super().__init__(
            requests_per_second=requests_per_second,
            burst_size=1,  # 인증은 버스트 불허
            backoff_factor=3.0,  # 더 공격적인 백오프
            max_backoff=lockout_duration,
            **kwargs,
        )
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.consecutive_failures = 0
        self.locked_until: float = 0.0

        logger.info(f"🔐 인증 레이트 리미터 초기화: {requests_per_second} req/s, 최대 {max_attempts}회 시도")

    def wait_if_needed(self) -> bool:
        """인증 요청 전 대기 (잠금 상태 확인)"""
        with self.lock:
            now = time.time()

            # 잠금 상태 확인
            if self.locked_until > now:
                remaining = self.locked_until - now
                logger.warning(f"🔒 인증 잠금 상태: {remaining:.0f}초 남음 (연속 {self.consecutive_failures}회 실패)")
                return False

            # 연속 실패 횟수에 따른 추가 대기
            if self.consecutive_failures > 0:
                extra_wait = min(30.0, self.consecutive_failures * 5.0)
                logger.info(f"⏳ 인증 실패 {self.consecutive_failures}회 → {extra_wait:.0f}초 추가 대기")
                time.sleep(extra_wait)

        return self.acquire(tokens=1)

    def on_success(self):
        """인증 성공 - 모든 상태 리셋"""
        with self.lock:
            if self.consecutive_failures > 0:
                logger.info(f"✅ 인증 성공 - 실패 카운터 리셋 (이전: {self.consecutive_failures}회 실패)")
            self.consecutive_failures = 0
            self.locked_until = 0.0
            self.failure_count = 0
            self.current_backoff = 0.0

    def on_failure(self, error_code: Optional[int] = None):
        """인증 실패 - 잠금 여부 결정"""
        with self.lock:
            self.consecutive_failures += 1
            self.failure_count += 1

            logger.warning(f"⚠️ 인증 실패 #{self.consecutive_failures}/{self.max_attempts}")

            # 최대 시도 횟수 초과 시 잠금
            if self.consecutive_failures >= self.max_attempts:
                self.locked_until = time.time() + self.lockout_duration
                logger.error(f"🔒 인증 잠금 활성화: {self.lockout_duration:.0f}초 동안 인증 차단")
            else:
                # 점진적 백오프
                backoff = min(60.0, (self.backoff_factor**self.consecutive_failures) * 2)
                logger.info(f"⏸️ 인증 백오프: {backoff:.0f}초 대기")
                time.sleep(backoff)

    def get_stats(self) -> Dict[str, Any]:
        """인증 레이트 리미터 통계"""
        stats = super().get_stats()
        with self.lock:
            now = time.time()
            stats.update(
                {
                    "consecutive_failures": self.consecutive_failures,
                    "max_attempts": self.max_attempts,
                    "is_locked": self.locked_until > now,
                    "locked_remaining": max(0, self.locked_until - now),
                }
            )
        return stats

    def reset(self):
        """완전 리셋 (관리자용)"""
        super().reset()
        with self.lock:
            self.consecutive_failures = 0
            self.locked_until = 0.0
            logger.info("🔓 인증 레이트 리미터 완전 리셋")


# 전역 인스턴스 (REGTECH 최적화 설정)
regtech_rate_limiter = AdaptiveRateLimiter(
    initial_rate=2.0,  # 초당 2개 요청 (0.5초 간격)
    min_rate=0.5,  # 최소 초당 0.5개 (2초 간격)
    max_rate=5.0,  # 최대 초당 5개 (0.2초 간격)
    burst_size=5,  # 버스트 5개까지 허용
    backoff_factor=2.0,  # 실패 시 2배씩 증가
    max_backoff=300.0,  # 최대 5분 대기
)

# 인증 전용 레이트 리미터 (더 보수적)
auth_rate_limiter = AuthRateLimiter(
    requests_per_second=0.2,  # 5초에 1번
    max_attempts=3,  # 3회 연속 실패 시 잠금
    lockout_duration=600.0,  # 10분 잠금
)

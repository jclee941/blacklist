"""REGTECH 수집 오류 타입 — 페이지 실패와 WAF 차단 중단 신호"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RegtechPageCollectionError(RuntimeError):
    strategy: str
    page_num: int
    attempts: int

    def __str__(self) -> str:
        return f"REGTECH page collection failed: strategy={self.strategy} page={self.page_num} attempts={self.attempts}"


@dataclass(frozen=True, slots=True)
class RegtechCollectionBlockedError(RegtechPageCollectionError):
    """WAF 쿼터/차단 신호가 연속 감지되어 수집을 즉시 중단 — 쿨다운 후 재시도해야 함"""

    consecutive_failures: int = 0

    def __str__(self) -> str:
        return (
            f"REGTECH collection blocked: strategy={self.strategy} page={self.page_num} "
            f"consecutive_block_signals={self.consecutive_failures} — WAF 쿼터/차단 의심, 쿨다운 필요"
        )


def _env_int(name: str, default: int) -> int:
    """환경변수 int 파싱 — 미설정/빈 값/잘못된 값이면 기본값"""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("잘못된 %s 값 %r — 기본값 %s 사용", name, raw, default)
        return default

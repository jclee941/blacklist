"""REGTECH 수집 날짜 전략 생성 — 전체/사용자 지정/최근 1일/최근 3개월"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def generate_date_strategies(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> List[tuple[str, Optional[str], Optional[str]]]:
    strategies: List[tuple[str, Optional[str], Optional[str]]] = []

    if start_date is None and end_date is None:
        strategies.append(("전체 데이터", None, None))
        logger.info("📋 전체 데이터 수집 모드 활성화 (날짜 필터 없음)")
        return strategies

    today = datetime.now()

    if not end_date:
        end_date = today.strftime("%Y-%m-%d")

    if start_date:
        strategies.append(("사용자 지정", start_date, end_date))
        logger.info("📋 생성된 날짜 전략: %s", [strategy[0] for strategy in strategies])
        return strategies

    recent_start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    strategies.append(("최근 1일 일일", recent_start, end_date))

    quarter_start = (today - relativedelta(months=3)).strftime("%Y-%m-%d")
    strategies.append(("최근 3개월 분기", quarter_start, end_date))

    logger.info(f"📋 생성된 날짜 전략: {[s[0] for s in strategies]}")
    return strategies

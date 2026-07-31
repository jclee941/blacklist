import logging
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Final, List, Optional

import requests
from requests.adapters import HTTPAdapter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from collector.config import CollectorConfig
from .auth import RegtechAuthMixin
from .data_processor import RegtechDataProcessorMixin
from .date_strategies import generate_date_strategies
from .errors import RegtechCollectionBlockedError, RegtechPageCollectionError, _env_int
from ..rate_limiter import auth_rate_limiter, regtech_rate_limiter
from .page_collection import RegtechPageCollectorMixin


logger = logging.getLogger(__name__)
REGTECH_PAGE_SIZE = 50
REGTECH_PAGE_ATTEMPTS: Final = 3


class RegtechCollector(RegtechAuthMixin, RegtechDataProcessorMixin, RegtechPageCollectorMixin):
    def __init__(self):
        self.base_url = CollectorConfig.REGTECH_BASE_URL
        self.session = requests.Session()

        self.proxy_url = os.getenv("WARP_PROXY_URL")
        if self.proxy_url:
            self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            logger.info(f"🌐 WARP 프록시 활성화: {self.proxy_url}")

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",  # noqa: E501
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/login/loginForm",
            }
        )

        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=3, pool_block=False)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.authenticated = False
        self._data_cache = {}
        self._last_failure_kind = None
        self._auth_cache = {}
        self._performance_cache: List[Dict[str, Any]] = []
        self._cache_ttl = 3600
        self._jwt_expiry: Optional[float] = None
        self._last_credentials: Optional[tuple[str, str]] = None

        self.rate_limiter = regtech_rate_limiter
        self.auth_rate_limiter = auth_rate_limiter
        logger.info("🚦 Rate Limiter 통합: API 차단 방지 활성화")

    def collect_blacklist_data(
        self,
        page_size: int = REGTECH_PAGE_SIZE,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_pages: Optional[int] = 100,
    ) -> List[Dict[str, Any]]:
        if not self._ensure_authenticated():
            logger.error("❌ 인증되지 않은 상태에서 수집 시도")
            return []

        effective_page_size = min(page_size, REGTECH_PAGE_SIZE)
        if max_pages is None:
            effective_max_pages = None
        else:
            requested_capacity = page_size * max_pages
            effective_max_pages = (
                max_pages
                if effective_page_size == page_size
                else max(1, (requested_capacity + effective_page_size - 1) // effective_page_size)
            )

        collection_start = time.time()

        excel_enabled = (
            effective_max_pages is not None and os.getenv("DISABLE_EXCEL_COLLECTION", "false").lower() != "true"
        )

        collected_data = []
        date_strategies = self._generate_date_strategies(start_date, end_date)

        try:
            logger.info(
                f"🚀 스마트 REGTECH 데이터 수집 시작 "
                f"(페이지 크기: {effective_page_size}, 최대 페이지: {effective_max_pages or '제한 없음'})"
            )
            logger.info(f"📅 날짜 전략 수: {len(date_strategies)}개")

            for strategy_idx, (strategy_name, start_dt, end_dt) in enumerate(date_strategies, 1):
                logger.info(f"🔄 전략 {strategy_idx}/{len(date_strategies)}: {strategy_name} ({start_dt} ~ {end_dt})")

                if excel_enabled and start_dt and end_dt:
                    excel_data = self._download_excel_data(start_dt, end_dt)
                    if excel_data:
                        detection_dates = [
                            detection_date
                            for item in excel_data
                            if isinstance((detection_date := item.get("detection_date")), str)
                        ]
                        latest_detection_date = max(detection_dates, default=None)
                        excel_is_fresh = True
                        if latest_detection_date:
                            try:
                                latest_date = datetime.strptime(latest_detection_date, "%Y-%m-%d").date()
                            except ValueError:
                                logger.warning(
                                    "REGTECH Excel 날짜 파싱 실패: 전략=%s 최신일=%s",
                                    strategy_name,
                                    latest_detection_date,
                                )
                            else:
                                excel_is_fresh = (datetime.now().date() - latest_date).days <= 3

                        if excel_is_fresh:
                            logger.info(f"✅ 전략 {strategy_name} Excel 성공: {len(excel_data)}개 IP")
                            collected_data.extend(excel_data)
                            break

                        logger.warning(
                            "REGTECH Excel 데이터가 오래되어 HTML 수집으로 전환: 전략=%s 최신일=%s",
                            strategy_name,
                            latest_detection_date,
                        )

                block_threshold = _env_int("REGTECH_BLOCK_THRESHOLD", 3)
                consecutive_block_signals = 0
                strategy_data = []
                seen_page_signatures: set[bytes] = set()
                page_num = 1
                while effective_max_pages is None or page_num <= effective_max_pages:
                    page_data = None
                    for attempt in range(1, REGTECH_PAGE_ATTEMPTS + 1):
                        page_data = self._collect_single_page(page_num, effective_page_size, start_dt, end_dt)
                        if page_data is not None:
                            break
                        if getattr(self, "_last_failure_kind", None) == "block_suspect":
                            consecutive_block_signals += 1
                        else:
                            consecutive_block_signals = 0
                        if consecutive_block_signals >= block_threshold:
                            raise RegtechCollectionBlockedError(
                                strategy=strategy_name,
                                page_num=page_num,
                                attempts=attempt,
                                consecutive_failures=consecutive_block_signals,
                            )
                        if attempt < REGTECH_PAGE_ATTEMPTS:
                            logger.warning(
                                "REGTECH 페이지 재시도: 전략=%s 페이지=%s 시도=%s/%s",
                                strategy_name,
                                page_num,
                                attempt,
                                REGTECH_PAGE_ATTEMPTS,
                            )

                    if page_data is None:
                        raise RegtechPageCollectionError(
                            strategy=strategy_name,
                            page_num=page_num,
                            attempts=REGTECH_PAGE_ATTEMPTS,
                        )

                    consecutive_block_signals = 0
                    if not page_data:
                        logger.info(f"📄 전략 {strategy_name} 페이지 {page_num}: 데이터 없음")
                        break

                    stable_page_data = [
                        {
                            key: item.get(key)
                            for key in (
                                "ip_address",
                                "source",
                                "reason",
                                "country",
                                "detection_date",
                                "removal_date",
                            )
                        }
                        for item in page_data
                    ]
                    page_signature = hashlib.sha256(
                        json.dumps(stable_page_data, sort_keys=True, default=str).encode("utf-8")
                    ).digest()
                    if page_signature in seen_page_signatures:
                        raise RegtechPageCollectionError(
                            strategy=strategy_name,
                            page_num=page_num,
                            attempts=1,
                        )
                    seen_page_signatures.add(page_signature)

                    strategy_data.extend(page_data)
                    logger.info(f"📄 전략 {strategy_name} 페이지 {page_num}: {len(page_data)}개 IP 수집")

                    if len(strategy_data) >= 10000000:
                        logger.warning("⚠️ 메모리 한계 도달 (1000만개), 현재 전략 중단")
                        break

                    page_num += 1

                if strategy_data:
                    logger.info(f"✅ 전략 {strategy_name} 성공: {len(strategy_data)}개 IP 수집")
                    collected_data.extend(strategy_data)
                    break
                else:
                    logger.warning(f"⚠️ 전략 {strategy_name} 실패: 데이터 없음")

            collection_time = time.time() - collection_start
            logger.info(f"✅ 스마트 REGTECH 수집 완료: {len(collected_data)}개 IP ({collection_time:.2f}초)")

            self._record_collection_performance(collected_data, date_strategies, collection_time)

            return self._post_process_collected_data(collected_data)

        except RegtechPageCollectionError:
            raise
        except Exception as e:
            logger.error(f"❌ REGTECH 데이터 수집 중 오류: {e}")
            return collected_data

    def _generate_date_strategies(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[tuple[str, Optional[str], Optional[str]]]:
        return generate_date_strategies(start_date, end_date)

    def _record_collection_performance(
        self,
        collected_data: List[Dict[str, Any]],
        strategies: List[tuple[str, Optional[str], Optional[str]]],
        duration: float,
    ):
        performance_log = {
            "timestamp": datetime.now().isoformat(),
            "total_strategies": len(strategies),
            "successful_collection": len(collected_data) > 0,
            "data_count": len(collected_data),
            "duration_seconds": round(duration, 2),
            "strategies_tried": [s[0] for s in strategies],
            "success_rate": (1 if len(collected_data) > 0 else 0) / len(strategies),
        }

        logger.info(f"📊 수집 성과: {performance_log}")

        self._performance_cache.append(performance_log)

        if len(self._performance_cache) > 10:
            self._performance_cache = self._performance_cache[-10:]

    def get_session_info(self) -> Dict[str, Any]:
        return {
            "authenticated": self.authenticated,
            "cookies_count": len(self.session.cookies),
            "base_url": self.base_url,
            "cache_size": len(self._data_cache),
            "auth_cache_size": len(self._auth_cache),
            "performance_mode": "optimized",
            "last_activity": datetime.now().isoformat(),
            "rate_limiter": self.rate_limiter.get_stats(),
        }

    def clear_cache(self):
        self._data_cache.clear()
        self._auth_cache.clear()
        logger.info("🧹 캐시 정리 완료")

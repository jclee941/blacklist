"""
REGTECH Collector Service
REGTECH 포털에서 블랙리스트 IP 수집

Refactored: 2026-02-08 — Split into regtech/ package
- auth.py: Authentication (login, session, token)
- data_processor.py: Data processing (parse, validate, enhance)
- collector.py: Collection orchestration (this file)
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from collector.config import CollectorConfig
from .auth import RegtechAuthMixin
from .data_processor import RegtechDataProcessorMixin
from ..rate_limiter import auth_rate_limiter, regtech_rate_limiter
from ..regtech_excel import download_excel_data


logger = logging.getLogger(__name__)
REGTECH_PAGE_SIZE = 50


class RegtechCollector(RegtechAuthMixin, RegtechDataProcessorMixin):
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
        max_pages: int = 100,
    ) -> List[Dict[str, Any]]:
        if not self._ensure_authenticated():
            logger.error("❌ 인증되지 않은 상태에서 수집 시도")
            return []

        requested_capacity = page_size * max_pages
        effective_page_size = min(page_size, REGTECH_PAGE_SIZE)
        effective_max_pages = (
            max_pages
            if effective_page_size == page_size
            else max(1, (requested_capacity + effective_page_size - 1) // effective_page_size)
        )

        collection_start = time.time()

        disable_excel = os.getenv("DISABLE_EXCEL_COLLECTION", "false").lower() == "true"

        if start_date and end_date and not disable_excel:
            logger.info(f"📥 Excel 다운로드 시도: {start_date} ~ {end_date}")
            excel_data = self._download_excel_data(start_date, end_date)

            is_excel_stale = False
            if excel_data:
                valid_dates = []
                for item in excel_data:
                    d = item.get("detection_date")
                    if d and isinstance(d, str):
                        valid_dates.append(d)

                max_date_str = max(valid_dates) if valid_dates else None

                if max_date_str:
                    try:
                        max_date = datetime.strptime(max_date_str, "%Y-%m-%d").date()
                        today = datetime.now().date()
                        if (today - max_date).days > 3:
                            is_excel_stale = True
                            logger.warning(f"⚠️ Excel 데이터가 오래됨 (최신: {max_date_str}). HTML 수집으로 전환합니다.")
                    except Exception:
                        pass

            if excel_data and not is_excel_stale:
                collection_time = time.time() - collection_start
                logger.info(f"✅ Excel 수집 완료: {len(excel_data)}개 IP ({collection_time:.2f}초)")
                return self._post_process_collected_data(excel_data)

            if not is_excel_stale:
                logger.warning("⚠️ Excel 다운로드 실패, HTML 페이지네이션으로 전환")

        collected_data = []
        date_strategies = self._generate_date_strategies(start_date, end_date)

        try:
            logger.info(
                f"🚀 스마트 REGTECH 데이터 수집 시작 "
                f"(페이지 크기: {effective_page_size}, 최대 페이지: {effective_max_pages})"
            )
            logger.info(f"📅 날짜 전략 수: {len(date_strategies)}개")

            for strategy_idx, (strategy_name, start_dt, end_dt) in enumerate(date_strategies, 1):
                logger.info(f"🔄 전략 {strategy_idx}/{len(date_strategies)}: {strategy_name} ({start_dt} ~ {end_dt})")

                if start_dt and end_dt:
                    excel_data = self._download_excel_data(start_dt, end_dt)
                    if excel_data:
                        logger.info(f"✅ 전략 {strategy_name} Excel 성공: {len(excel_data)}개 IP")
                        collected_data.extend(excel_data)
                        break

                strategy_data = []
                for page_num in range(1, effective_max_pages + 1):
                    page_data = self._collect_single_page(page_num, effective_page_size, start_dt, end_dt)

                    if not page_data:
                        logger.info(f"📄 전략 {strategy_name} 페이지 {page_num}: 데이터 없음")
                        break

                    strategy_data.extend(page_data)
                    logger.info(f"📄 전략 {strategy_name} 페이지 {page_num}: {len(page_data)}개 IP 수집")

                    if len(strategy_data) >= 10000000:
                        logger.warning("⚠️ 메모리 한계 도달 (1000만개), 현재 전략 중단")
                        break

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

        except Exception as e:
            logger.error(f"❌ REGTECH 데이터 수집 중 오류: {e}")
            return collected_data

    def _generate_date_strategies(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[tuple[str, Optional[str], Optional[str]]]:
        strategies: List[tuple[str, Optional[str], Optional[str]]] = []

        if start_date is None and end_date is None:
            strategies.append(("전체 데이터", None, None))
            logger.info("📋 전체 데이터 수집 모드 활성화 (날짜 필터 없음)")
            return strategies

        today = datetime.now()

        if not end_date:
            end_date = today.strftime("%Y-%m-%d")

        recent_start = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        strategies.append(("최근 1일 일일", recent_start, end_date))

        quarter_start = (today - relativedelta(months=3)).strftime("%Y-%m-%d")
        strategies.append(("최근 3개월 분기", quarter_start, end_date))

        if start_date:
            strategies.insert(0, ("사용자 지정", start_date, end_date))

        logger.info(f"📋 생성된 날짜 전략: {[s[0] for s in strategies]}")
        return strategies

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

    def _download_excel_data(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        return download_excel_data(
            session=self.session,
            rate_limiter=self.rate_limiter,
            proxy_url=self.proxy_url,
            base_url=self.base_url,
            start_date=start_date,
            end_date=end_date,
        )

    def _collect_single_page(
        self,
        page_num: int,
        page_size: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            data_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"

            cache_key = f"page_{page_num}_{page_size}_{start_date}_{end_date}_blacklist"
            if cache_key in self._data_cache:
                cache_time, cached_data = self._data_cache[cache_key]
                if time.time() - cache_time < 60:
                    logger.info(f"📦 페이지 {page_num} 캐시 사용")
                    return cached_data

            request_data = {
                "page": str(page_num - 1),
                "tabSort": "blacklist",
                "excelDownload": "",
                "cveId": "",
                "ipId": "",
                "estId": "",
                "startDate": start_date.replace("-", "") if start_date else "",
                "endDate": end_date.replace("-", "") if end_date else "",
                "findCondition": "all",
                "findKeyword": "",
                "excelDown": "blacklist",
                "size": str(page_size),
            }

            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://regtech.fsec.or.kr",
                "Pragma": "no-cache",
                "Referer": "https://regtech.fsec.or.kr/fcti/securityAdvisory/advisoryList",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",  # noqa: E501
            }

            logger.info(f"🔄 HAR 기반 데이터 수집: 페이지 {page_num}, 크기 {page_size}")

            if not self.rate_limiter.wait_if_needed():
                logger.warning(f"⚠️ 페이지 {page_num} Rate Limiter 대기 실패. 수집 중단.")
                return []

            cookie_count = len(self.session.cookies)
            has_jwt = any(c.name == "regtech-va" for c in self.session.cookies)
            logger.info(f"🍪 요청 쿠키 상태: {cookie_count}개, JWT 존재: {has_jwt}")

            headers_list = []
            for k, v in headers.items():
                headers_list.extend(["-H", f"{k}: {v}"])

            cookie_header = "; ".join([f"{c.name}={c.value}" for c in self.session.cookies])
            if cookie_header:
                headers_list.extend(["-H", f"Cookie: {cookie_header}"])

            curl_cmd = (
                ["curl", "-s", "-X", "POST", data_url]
                + headers_list
                + [
                    "--data",
                    urllib.parse.urlencode(request_data),
                ]
            )

            if self.proxy_url:
                curl_cmd.extend(["--proxy", self.proxy_url])

            encoded_data = urllib.parse.urlencode(request_data)
            logger.info(f"🔍 데이터 수집 curl 실행: {data_url} | page={page_num - 1}")
            logger.debug(f"📤 POST 데이터: {encoded_data}")

            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                logger.error(f"❌ curl 실행 실패: {result.stderr}")
                self.rate_limiter.on_failure()
                return []

            response_text = result.stdout
            logger.info(f"📊 응답 길이: {len(response_text)}")

            from ..archive_manager import archive_content

            archive_content(
                "REGTECH",
                response_text,
                f"regtech_page{page_num}.html",
                period_start=start_date,
                period_end=end_date,
            )

            try:

                class MockResponse:
                    def __init__(self, text, status_code):
                        self.text = text
                        self.status_code = status_code

                    def json(self):
                        return json.loads(self.text)

                response = MockResponse(response_text, 200)

            except Exception as e:
                logger.error(f"❌ 응답 객체 생성 실패: {e}")
                return []

            logger.info("📊 응답 처리 시작...")

            if response.status_code == 200:
                page_data = self._parse_response_data(response)

                self._data_cache[cache_key] = (time.time(), page_data)

                self.rate_limiter.on_success()

                logger.info(f"✅ 페이지 {page_num} 수집 완료: {len(page_data)}개 항목")
                return page_data
            else:
                logger.warning(f"⚠️ 페이지 {page_num} 요청 실패: {response.status_code}")

                self.rate_limiter.on_failure(error_code=response.status_code)

                return []

        except Exception as e:
            logger.error(f"❌ 페이지 {page_num} 수집 실패: {e}")

            self.rate_limiter.on_failure()

            return []

    def _parse_response_data(self, response) -> List[Dict[str, Any]]:
        try:
            json_data = response.json()

            if isinstance(json_data, dict) and "data" in json_data:
                raw_data = json_data["data"]
            elif isinstance(json_data, list):
                raw_data = json_data
            else:
                logger.warning("⚠️ 예상하지 못한 JSON 응답 형식")
                return self._parse_html_response(response.text)

            processed_data = []
            for item in raw_data:
                processed_item = self._process_regtech_item(item)
                if processed_item:
                    processed_data.append(processed_item)

            return processed_data

        except json.JSONDecodeError:
            logger.info("📄 JSON 파싱 실패, HTML 파싱으로 전환")
            return self._parse_html_response(response.text)
        except Exception as e:
            logger.error(f"❌ 응답 파싱 실패: {e}")
            return []

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

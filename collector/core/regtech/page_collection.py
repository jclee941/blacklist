import json
import logging
import subprocess
import time
import urllib.parse
from typing import Any, Dict, List, Optional

from collector.config import CollectorConfig

from ..bounded_process import run_text_bounded
from ..regtech_excel import download_excel_data


logger = logging.getLogger(__name__)


class RegtechPageCollectorMixin:
    _last_failure_kind: str | None = None

    def _download_excel_data(self: Any, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        return download_excel_data(
            session=self.session,
            rate_limiter=self.rate_limiter,
            proxy_url=self.proxy_url,
            base_url=self.base_url,
            start_date=start_date,
            end_date=end_date,
        )

    def _collect_single_page(
        self: Any,
        page_num: int,
        page_size: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        try:
            data_url = f"{self.base_url}/fcti/securityAdvisory/advisoryList"
            cache_key = f"page_{page_num}_{page_size}_{start_date}_{end_date}_blacklist"
            if cache_key in self._data_cache:
                cache_time, cached_data = self._data_cache[cache_key]
                if time.time() - cache_time < 60:
                    logger.info("📦 페이지 %s 캐시 사용", page_num)
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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            }
            logger.info("🔄 HAR 기반 데이터 수집: 페이지 %s, 크기 %s", page_num, page_size)
            if not self.rate_limiter.wait_if_needed():
                logger.warning("⚠️ 페이지 %s Rate Limiter 대기 실패. 수집 중단.", page_num)
                return None

            headers_list = []
            for key, value in headers.items():
                headers_list.extend(["-H", f"{key}: {value}"])
            cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in self.session.cookies)
            if cookie_header:
                headers_list.extend(["-H", f"Cookie: {cookie_header}"])

            encoded_data = urllib.parse.urlencode(request_data)
            curl_cmd = (
                [
                    "curl",
                    "-sS",
                    "--max-time",
                    "55",
                    "--max-filesize",
                    str(CollectorConfig.MAX_DOWNLOAD_BYTES),
                    "-w",
                    "\n%{http_code}",
                    "-X",
                    "POST",
                    data_url,
                ]
                + headers_list
                + [
                    "--data",
                    encoded_data,
                ]
            )
            if self.proxy_url:
                curl_cmd.extend(["--proxy", self.proxy_url])

            logger.info("🔍 데이터 수집 curl 실행: %s | page=%s", data_url, page_num - 1)
            logger.debug("📤 POST 데이터: %s", encoded_data)
            result = run_text_bounded(curl_cmd, CollectorConfig.MAX_DOWNLOAD_BYTES + 32, timeout=60)
            if result.returncode != 0:
                self._last_failure_kind = "download_too_large" if result.returncode == 63 else "curl_error"
                logger.error("❌ curl 실행 실패 (code=%s): %s", result.returncode, result.stderr.strip())
                self.rate_limiter.on_failure()
                return None

            response_text, separator, status_text = result.stdout.rpartition("\n")
            if len(response_text.encode("utf-8")) > CollectorConfig.MAX_DOWNLOAD_BYTES:
                self._last_failure_kind = "download_too_large"
                self.rate_limiter.on_failure()
                return None
            http_status = int(status_text) if separator and status_text.isdigit() else 0
            logger.info("📊 응답: HTTP %s, 길이 %s", http_status, len(response_text))
            from ..archive_manager import archive_content

            archive_content(
                "REGTECH",
                response_text,
                f"regtech_page{page_num}.html",
                period_start=start_date,
                period_end=end_date,
            )

            if http_status != 200:
                self._last_failure_kind = "block_suspect" if http_status in (403, 429) else "http_error"
                logger.warning("⚠️ 페이지 %s 요청 실패: HTTP %s", page_num, http_status)
                self.rate_limiter.on_failure(error_code=http_status or None)
                return None

            if not response_text.strip():
                self._last_failure_kind = "block_suspect"
                logger.warning("⚠️ 페이지 %s 빈 응답 (HTTP 200) — WAF 쿼터/차단 의심", page_num)
                self.rate_limiter.on_failure()
                return None

            class MockResponse:
                def __init__(self, text, status_code):
                    self.text = text
                    self.status_code = status_code

                def json(self):
                    return json.loads(self.text)

            response = MockResponse(response_text, http_status)
            logger.info("📊 응답 처리 시작...")
            page_data = self._parse_response_data(response)
            if page_data is None:
                # 데이터 테이블 없는 HTML 응답은 WAF 차단 페이지와 구분 불가 — 차단 신호로 분류
                self._last_failure_kind = "block_suspect"
                self.rate_limiter.on_failure()
                return None
            self._data_cache[cache_key] = (time.time(), page_data)
            self._last_failure_kind = None
            self.rate_limiter.on_success()
            logger.info("✅ 페이지 %s 수집 완료: %s개 항목", page_num, len(page_data))
            return page_data
        except (OSError, subprocess.SubprocessError) as exc:
            self._last_failure_kind = "curl_error"
            logger.error("REGTECH 페이지 요청 실패: 페이지=%s 오류=%s", page_num, type(exc).__name__)
            self.rate_limiter.on_failure()
            return None
        except Exception as e:
            self._last_failure_kind = "http_error"
            logger.error("❌ 페이지 %s 수집 실패: %s", page_num, e)
            self.rate_limiter.on_failure()
            return None

    def _parse_response_data(self: Any, response) -> Optional[List[Dict[str, Any]]]:
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
            logger.error("❌ 응답 파싱 실패: %s", e)
            return None

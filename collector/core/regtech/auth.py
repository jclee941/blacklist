import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class RegtechAuthMixin:
    """Authentication methods for RegtechCollector (mixin)."""

    # Mixin protocol: attributes provided by the concrete class (RegtechCollector)
    base_url: str
    session: requests.Session
    _auth_cache: dict
    _cache_ttl: int
    auth_rate_limiter: Any
    proxy_url: Optional[str]
    authenticated: bool
    _jwt_expiry: Optional[float]
    _last_credentials: Optional[tuple]

    def _find_member(self, username: str) -> Optional[str]:
        try:
            url = f"{self.base_url}/login/findOneMember"
            data = {"username": username}

            logger.info(f"🔍 사용자 조회 시도: {username}")
            response = self.session.post(url, json=data, timeout=10)

            if response.status_code == 200:
                try:
                    result = response.json()
                    if isinstance(result, dict) and "id" in result:
                        member_id = str(result["id"])
                        logger.info(f"✅ 사용자 조회 성공: {member_id}")
                        return member_id
                    else:
                        logger.warning(f"⚠️ 사용자 조회 응답 형식 오류: {result}")
                except Exception as json_err:
                    logger.error(f"❌ JSON 파싱 오류: {json_err}")
                    logger.error(f"📄 응답 내용(앞부분): {response.text[:500]}")
            else:
                logger.warning(f"⚠️ 사용자 조회 실패: {response.status_code}")
                logger.warning(f"📄 응답 내용: {response.text[:200]}")

            return None
        except Exception as e:
            logger.error(f"❌ 사용자 조회 중 오류: {e}")
            return None

    def authenticate(self, username: str, password: str) -> bool:
        auth_key = f"{username}:{hash(password)}"
        self._last_credentials = (username, password)

        if auth_key in self._auth_cache:
            cache_time, is_valid = self._auth_cache[auth_key]
            if time.time() - cache_time < self._cache_ttl and is_valid:
                if self._is_jwt_valid():
                    self.authenticated = True
                    logger.info("✅ 캐시된 REGTECH 인증 사용")
                    return True
                else:
                    logger.info("🔄 JWT 만료 - 재인증 필요")

        if not self.auth_rate_limiter.wait_if_needed():
            logger.warning("🔒 인증 Rate Limiter 차단 (잠금 상태)")
            return False

        self.session.cookies.clear()

        if self.proxy_url:
            self.session.proxies = {
                "http": self.proxy_url,
                "https": self.proxy_url,
            }

        logger.info(f"🔐 REGTECH 로그인 시도: {username}")

        try:
            login_page_url = f"{self.base_url}/login/loginForm"
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                    "Referer": login_page_url,
                }
            )
            self.session.get(login_page_url, timeout=30)

            login_payload = {
                "username": username,
                "password": password,
                "login_error": "",
                "smsTimeExcess": "N",
                "txId": "",
                "token": "",
                "memberId": "",
            }
            logger.info("📤 Step 1: /login/addLogin 로그인 요청")

            response = self.session.post(
                f"{self.base_url}/login/addLogin",
                data=login_payload,
                timeout=30,
                allow_redirects=True,
            )

            logger.info(f"📊 Step 1 응답: Status={response.status_code}, URL={response.url}")

            if "로그아웃" in response.text or "마이페이지" in response.text:
                self.authenticated = True
                logger.info("✅ REGTECH 인증 성공 (로그아웃 버튼 확인)")
                self._auth_cache[auth_key] = (time.time(), True)
                self._jwt_expiry = time.time() + 3600
                self.auth_rate_limiter.on_success()
                return True
            elif "/main" in response.url:
                self.authenticated = True
                logger.info("✅ REGTECH 인증 성공 (메인 페이지 리다이렉트)")
                self._auth_cache[auth_key] = (time.time(), True)
                self._jwt_expiry = time.time() + 3600
                self.auth_rate_limiter.on_success()
                return True
            else:
                logger.warning(f"⚠️ 인증 실패: redirect to {response.url}")
                self.auth_rate_limiter.on_failure()

        except Exception as e:
            logger.error(f"❌ 인증 오류: {e}")
            self.auth_rate_limiter.on_failure()

        self._auth_cache[auth_key] = (time.time(), False)
        logger.error("❌ REGTECH 인증 실패")
        return False

    def _is_jwt_valid(self) -> bool:
        if not self._jwt_expiry:
            return False
        return time.time() < (self._jwt_expiry - 300)

    def _ensure_authenticated(self) -> bool:
        if self.authenticated and self._is_jwt_valid():
            return True
        if self._last_credentials:
            logger.info("🔄 세션 만료 - 자동 재인증 시도")
            return self.authenticate(*self._last_credentials)
        logger.warning("⚠️ 저장된 인증 정보 없음 - 재인증 필요")
        return False

"""
Secudium (ISAP) Black IP Collector

Authenticates to secudium.skinfosec.co.kr using ID/PW + OTP (via IMAP email),
collects Black IP lists, downloads XLS attachments, and inserts into the database.

Auth flow:
1. POST /isap-api/loginProcess (is_otp=N) → check if OTP required
2. If OTP required: read OTP from email via OTPEmailReader
3. POST /isap-api/loginProcess (is_otp=Y, otp_value=XXXXXX) → get X-Auth-Token
4. GET /isap-api/secinfo/list/black_ip → DHTMLX grid JSON
5. GET /isap-api/file/SECINFO/download → XLS binary

Token format: X-Auth-Token={userId}:{timestamp}:{sha256hash}
Token delivery: query parameter AND cookie (not header)
"""

import os
import re
import time
import tempfile
import threading
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional
from urllib.parse import urlencode

import requests
import structlog
from requests.adapters import HTTPAdapter

from collector.config import CollectorConfig
from core.secudium_parsers import (
    parse_black_ip_list,
    extract_download_info,
    parse_xls_file,
)
from core.rate_limiter import auth_rate_limiter
from utils.otp_email_reader import OTPEmailReader

logger = structlog.get_logger(__name__)


class SecudiumCollector:
    """Collector for SK쉴더스 Secudium (ISAP) Black IP intelligence."""

    LOGIN_PATH = "/isap-api/loginProcess"
    MYINFO_PATH = "/isap-api/myinfo"
    BLACK_IP_LIST_PATH = "/isap-api/secinfo/list/black_ip"
    FILE_HAS_FILE_PATH = "/isap-api/file/SECINFO/hasFile"
    FILE_DOWNLOAD_PATH = "/isap-api/file/SECINFO/download"
    LOGOUT_PATH = "/isap-api/tokenout"

    # Session persistence: avoid OTP on every collection
    _cached_token: Optional[str] = None
    _token_obtained_at: Optional[datetime] = None
    _token_lock = threading.Lock()  # Thread-safe token cache access
    TOKEN_TTL_HOURS = 4  # Re-auth after 4 hours

    def __init__(self, db_service=None):
        self.base_url = CollectorConfig.SECUDIUM_BASE_URL.rstrip("/")
        self.session = self._create_session()
        self.db_service = db_service
        self._token: Optional[str] = None
        self._user_info: dict = {}

        # OTP email reader config
        self._otp_email = CollectorConfig.SECUDIUM_EMAIL
        self._otp_email_password = CollectorConfig.SECUDIUM_EMAIL_PASSWORD
        self._otp_imap_server = CollectorConfig.SECUDIUM_IMAP_SERVER

        # Rate limiting
        self._request_delay = 1.0  # seconds between requests
        self._last_request_time = 0.0
        self._auth_attempts = 0
        self._max_auth_attempts = 3

        logger.info("secudium_collector_initialized", base_url=self.base_url)

    def _create_session(self) -> requests.Session:
        """Create HTTP session with connection pooling and retries."""
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=5,
            pool_maxsize=10,
            max_retries=3,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": CollectorConfig.SECUDIUM_BASE_URL.rstrip("/"),
                "Referer": f"{CollectorConfig.SECUDIUM_BASE_URL.rstrip('/')}/",
            }
        )
        session.verify = True
        return session

    def _rate_limit(self):
        """Enforce request rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_delay:
            time.sleep(self._request_delay - elapsed)
        self._last_request_time = time.time()

    def _build_url(self, path: str, params: Optional[dict] = None) -> str:
        """Build URL with token as query parameter (Secudium convention)."""
        url = f"{self.base_url}{path}"
        query_params = {}
        if self._token:
            query_params["X-Auth-Token"] = self._token
        if params:
            query_params.update(params)
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
        return url

    def _set_token_cookie(self):
        """Set X-Auth-Token as cookie (Secudium uses both query param and cookie)."""
        if self._token:
            self.session.cookies.set("token", self._token, domain=self.base_url.split("//")[1])

    # ─── Authentication ───────────────────────────────────────────

    def authenticate(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        email_address: Optional[str] = None,
        email_password: Optional[str] = None,
        imap_server: Optional[str] = None,
    ) -> bool:
        """
        Authenticate to Secudium ISAP portal.

        Flow:
        1. Try login without OTP (is_otp=N)
        2. If OTP required, read OTP from email via IMAP
        3. Re-login with OTP (is_otp=Y, otp_value=XXXXXX)
        4. Verify token via /myinfo

        Args:
            username: Override CollectorConfig credentials (for test-auth)
            password: Override CollectorConfig credentials (for test-auth)
            email_address: Override IMAP email for OTP reading
            email_password: Override IMAP email password
            imap_server: Override IMAP server hostname

        Returns True if authentication successful.
        """
        if self._is_token_valid():
            logger.info("secudium_using_cached_token")
            return True

        if not auth_rate_limiter.wait_if_needed():
            logger.error("secudium_auth_rate_limited")
            return False

        self._auth_attempts += 1

        # Use provided credentials or fall back to env config
        if username and password:
            secudium_id, secudium_pw = username, password
        else:
            secudium_id, secudium_pw = CollectorConfig.get_secudium_credentials()

        if not secudium_id or not secudium_pw:
            logger.error("secudium_credentials_missing")
            return False

        # Override OTP email settings if provided
        otp_email = email_address or self._otp_email
        otp_email_pw = email_password or self._otp_email_password
        otp_imap = imap_server or self._otp_imap_server

        self.session.cookies.clear()

        # Step 1: Login without OTP
        logger.info("secudium_login_attempt", attempt=self._auth_attempts, with_otp=False)
        login_result = self._login(secudium_id, secudium_pw, is_otp=False, otp_value="")

        if login_result == "success":
            logger.info("secudium_login_success_no_otp")
            self._auth_attempts = 0
            return True

        if login_result == "otp_required":
            # Step 2: Read OTP from email (using overridden or default settings)
            logger.info("secudium_otp_required", email=otp_email)
            otp_code = self._read_otp_from_email(
                email_address=otp_email,
                email_password=otp_email_pw,
                imap_server=otp_imap,
            )
            if not otp_code:
                logger.error("secudium_otp_read_failed")
                return False

            # Step 3: Re-login with OTP
            logger.info("secudium_login_attempt", attempt=self._auth_attempts, with_otp=True)
            login_result = self._login(secudium_id, secudium_pw, is_otp=True, otp_value=otp_code)

            if login_result == "success":
                logger.info("secudium_login_success_with_otp")
                self._auth_attempts = 0
                return True

        logger.error("secudium_login_failed", result=login_result)
        return False

    def authenticate_step1(self, username: str, password: str) -> str:
        """
        Execute only step 1 of authentication (login without OTP).
        Used for manual OTP flow where the user provides OTP interactively.

        Stores credentials internally for authenticate_step2().

        Returns:
            "otp_required" - OTP needed, call authenticate_step2() with OTP code
            "success" - Login succeeded without OTP
            "failed" - Login failed
        """
        if self._auth_attempts >= self._max_auth_attempts:
            logger.error("secudium_auth_max_attempts_exceeded", attempts=self._auth_attempts)
            return "failed"

        self._auth_attempts += 1
        self._pending_username = username
        self._pending_password = password
        self.session.cookies.clear()

        logger.info("secudium_step1_login_attempt", with_otp=False)
        login_result = self._login(username, password, is_otp=False, otp_value="")

        if login_result == "success":
            self._auth_attempts = 0

        return login_result

    def authenticate_step2(self, otp_code: str) -> str:
        """
        Execute step 2 of authentication with user-provided OTP code.
        Must be called after authenticate_step1() returned "otp_required".

        Args:
            otp_code: 6-digit OTP code entered by user

        Returns:
            "success" - Authentication completed
            "failed" - OTP verification failed
        """
        if not hasattr(self, "_pending_username") or not self._pending_username:
            logger.error("secudium_step2_no_pending_auth")
            return "failed"

        logger.info("secudium_step2_login_attempt", with_otp=True, otp_length=len(otp_code))
        login_result = self._login(
            self._pending_username,
            self._pending_password,
            is_otp=True,
            otp_value=otp_code,
        )

        if login_result == "success":
            self._auth_attempts = 0
            self._pending_username = None
            self._pending_password = None

        return login_result

    def _login(self, user_id: str, password: str, is_otp: bool, otp_value: str, is_duplicate: bool = False) -> str:
        """
        Execute login request.

        Returns:
            "success" - login successful, token set
            "otp_required" - OTP is required
            "failed" - login failed
        """
        self._rate_limit()

        login_url = f"{self.base_url}{self.LOGIN_PATH}"
        form_data = {
            "lang": "ko",
            "is_otp": "Y" if is_otp else "N",
            "is_expire": "N",
            "login_name": user_id,
            "password": password,
            "otp_value": otp_value,
        }

        try:
            resp = self.session.post(
                login_url,
                data=form_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=CollectorConfig.REQUEST_TIMEOUT,
                allow_redirects=False,
            )

            logger.debug(
                "secudium_login_response",
                status_code=resp.status_code,
                content_length=len(resp.content),
                is_otp=is_otp,
                body_preview=resp.text[:500] if resp.text else "",
            )

            token = self._extract_token(resp)

            if token:
                self._token = token
                self._set_token_cookie()
                with SecudiumCollector._token_lock:
                    SecudiumCollector._cached_token = token
                    SecudiumCollector._token_obtained_at = datetime.now()

                if self._verify_token():
                    auth_rate_limiter.on_success()
                    return "success"
                else:
                    auth_rate_limiter.on_failure()
                    logger.warning("secudium_token_verification_failed")
                    return "failed"

            body_text = resp.text.lower() if resp.text else ""

            # Handle duplicate login — force expire existing session and retry
            if "already.login" in body_text and not is_duplicate:
                logger.info("secudium_already_login_detected", message="기존 세션 만료 후 재로그인 시도 (is_expire=Y)")
                form_data["is_expire"] = "Y"
                self._rate_limit()
                retry_resp = self.session.post(
                    login_url,
                    data=form_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=CollectorConfig.REQUEST_TIMEOUT,
                    allow_redirects=False,
                )
                token = self._extract_token(retry_resp)
                if token:
                    self._token = token
                    self._set_token_cookie()
                    with SecudiumCollector._token_lock:
                        SecudiumCollector._cached_token = token
                        SecudiumCollector._token_obtained_at = datetime.now()
                    if self._verify_token():
                        auth_rate_limiter.on_success()
                        return "success"
                retry_body = retry_resp.text.lower() if retry_resp.text else ""
                if any(ind in retry_body for ind in ["otp", "인증", "2차인증", "is_otp"]):
                    return "otp_required"
                logger.warning(
                    "secudium_duplicate_login_retry_failed", status=retry_resp.status_code, body=retry_body[:200]
                )
                return "failed"

            otp_indicators = any(indicator in body_text for indicator in ["otp", "인증", "2차인증", "is_otp"])
            redirect_otp = resp.status_code in (302, 303) and "otp" in resp.headers.get("Location", "").lower()

            if otp_indicators or redirect_otp:
                if is_otp:
                    # Already submitted OTP but server still wants OTP → OTP was wrong/expired/stale
                    logger.warning(
                        "secudium_otp_submission_rejected",
                        body=resp.text[:500] if resp.text else "",
                        status=resp.status_code,
                        otp_value_length=len(otp_value) if otp_value else 0,
                        cookies=dict(self.session.cookies),
                    )
                    return "failed"
                return "otp_required"

            logger.warning("secudium_login_unexpected_response", status=resp.status_code, body=body_text[:200])
            return "failed"

        except requests.RequestException as e:
            auth_rate_limiter.on_failure()
            logger.error("secudium_login_request_error", error=str(e))
            return "failed"

    def _extract_token(self, resp: requests.Response) -> Optional[str]:
        """Extract X-Auth-Token from response (body, cookies, or headers)."""
        try:
            body = resp.json() if resp.content else {}
            if isinstance(body, dict):
                token = body.get("X-Auth-Token") or body.get("token") or body.get("authToken")
                if token and ":" in str(token):
                    return str(token)
        except (ValueError, TypeError):
            pass

        for cookie_name in ("X-Auth-Token", "token", "authToken"):
            token = self.session.cookies.get(cookie_name)
            if token and ":" in token:
                return token

        set_cookie = resp.headers.get("Set-Cookie", "")
        token_match = re.search(r"(?:X-Auth-Token|token)=([^;]+)", set_cookie)
        if token_match:
            token = token_match.group(1)
            if ":" in token:
                return token

        text = resp.text or ""
        token_pattern = re.search(r"([a-zA-Z0-9_]+:\d+:[a-f0-9]{64})", text)
        if token_pattern:
            return token_pattern.group(1)

        return None

    def _verify_token(self) -> bool:
        """Verify token validity by fetching /myinfo."""
        self._rate_limit()
        try:
            url = self._build_url(self.MYINFO_PATH)
            resp = self.session.get(url, timeout=CollectorConfig.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                self._user_info = resp.json()
                logger.info(
                    "secudium_token_verified",
                    user_id=self._user_info.get("userId"),
                    company=self._user_info.get("companyName"),
                )
                return True
        except Exception as e:
            logger.warning("secudium_verify_error", error=str(e))
        return False

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid (within TTL)."""
        with SecudiumCollector._token_lock:
            if not SecudiumCollector._cached_token or not SecudiumCollector._token_obtained_at:
                return False
            age = datetime.now() - SecudiumCollector._token_obtained_at
            if age > timedelta(hours=self.TOKEN_TTL_HOURS):
                logger.info("secudium_token_expired", age_hours=age.total_seconds() / 3600)
                SecudiumCollector._cached_token = None
                SecudiumCollector._token_obtained_at = None
                return False
            self._token = SecudiumCollector._cached_token
            self._set_token_cookie()
            return True

    def _read_otp_from_email(
        self,
        email_address: Optional[str] = None,
        email_password: Optional[str] = None,
        imap_server: Optional[str] = None,
    ) -> Optional[str]:
        """Read OTP code from email using OTPEmailReader."""
        email = email_address or self._otp_email
        email_pw = email_password or self._otp_email_password
        imap_srv = imap_server or self._otp_imap_server

        if not email or not email_pw:
            logger.error("secudium_otp_email_credentials_missing")
            return None

        try:
            reader = OTPEmailReader(
                email_address=email,
                email_password=email_pw,
                imap_server=imap_srv,
            )
            otp_code = reader.get_latest_otp(max_wait_seconds=60)
            if otp_code:
                logger.info("secudium_otp_received", otp_length=len(otp_code))
            else:
                logger.warning("secudium_otp_timeout")
            return otp_code
        except Exception as e:
            logger.error("secudium_otp_reader_error", error=str(e))
            return None

    # ─── Data Collection ──────────────────────────────────────────

    def collect_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_pages: int = 10,
    ) -> dict:
        """
        Main collection entry point.

        Args:
            start_date: Filter start date (YYYY-MM-DD), defaults to 7 days ago
            end_date: Filter end date (YYYY-MM-DD), defaults to today
            max_pages: Maximum pages to fetch

        Returns:
            dict with keys: success, total_entries, total_ips, files_downloaded, errors
        """
        result = {
            "success": False,
            "total_entries": 0,
            "total_ips": 0,
            "files_downloaded": 0,
            "errors": [],
        }

        if not self.authenticate():
            result["errors"].append("Authentication failed")
            return result

        # Default date range: last 7 days
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info("secudium_collection_start", start_date=start_date, end_date=end_date)

        try:
            entries = self._fetch_black_ip_list(start_date, end_date, max_pages)
            result["total_entries"] = len(entries)
            logger.info("secudium_entries_found", count=len(entries))

            if not entries:
                result["success"] = True
                logger.info("secudium_no_new_entries")
                return result

            all_ips = []
            for entry in entries:
                download_info = extract_download_info(entry.get("download_html", ""))
                if not download_info:
                    logger.debug("secudium_entry_no_download", entry_id=entry.get("id"))
                    continue

                server_filename, display_filename = download_info
                try:
                    ips = self._download_and_parse(
                        server_filename=server_filename,
                        filename=display_filename,
                        entry_title=entry.get("title", ""),
                        entry_date=entry.get("date", ""),
                    )
                    all_ips.extend(ips)
                    result["files_downloaded"] += 1
                except Exception as e:
                    error_msg = f"Download failed for {display_filename}: {e}"
                    result["errors"].append(error_msg)
                    logger.error("secudium_download_error", error=str(e), filename=display_filename)

            result["total_ips"] = len(all_ips)
            logger.info("secudium_ips_collected", count=len(all_ips))

            if all_ips and self.db_service:
                inserted = self._insert_ips(all_ips)
                logger.info("secudium_ips_inserted", count=inserted)

            result["success"] = True

        except Exception as e:
            result["errors"].append(f"Collection error: {e}")
            logger.error("secudium_collection_error", error=str(e))

        finally:
            self._logout()

        return result

    def _fetch_black_ip_list(
        self,
        start_date: str,
        end_date: str,
        max_pages: int = 10,
    ) -> list[dict]:
        """
        Fetch Black IP list from Secudium.

        Returns list of entries from DHTMLX grid JSON.
        """
        all_entries = []
        page = 1
        count_per_page = 100

        while page <= max_pages:
            self._rate_limit()

            params = {
                "sdate": start_date,
                "edate": end_date,
                "dateKey": "i.reg_date",
                "count": str(count_per_page),
                "filter": "",
                "posStart": str((page - 1) * count_per_page),
            }

            url = self._build_url(self.BLACK_IP_LIST_PATH, params)

            try:
                resp = self.session.get(url, timeout=CollectorConfig.REQUEST_TIMEOUT)

                if resp.status_code == 401:
                    logger.warning("secudium_session_expired_during_collection")
                    # Try re-auth once
                    if self.authenticate():
                        url = self._build_url(self.BLACK_IP_LIST_PATH, params)
                        resp = self.session.get(url, timeout=CollectorConfig.REQUEST_TIMEOUT)
                    else:
                        break

                if resp.status_code != 200:
                    logger.error("secudium_list_error", status=resp.status_code, page=page)
                    break

                data = resp.json()
                entries = parse_black_ip_list(data)

                if not entries:
                    break

                all_entries.extend(entries)
                logger.debug("secudium_page_fetched", page=page, entries=len(entries))

                # If fewer than count_per_page, we've reached the last page
                if len(entries) < count_per_page:
                    break

                page += 1

            except requests.RequestException as e:
                logger.error("secudium_list_request_error", error=str(e), page=page)
                break

        return all_entries

    def _download_and_parse(
        self,
        server_filename: str,
        filename: str,
        entry_title: str = "",
        entry_date: str = "",
    ) -> list[dict]:
        """
        Download XLS file and parse IPs from it.

        Returns list of dicts: {ip, source, category, date, title, ...}
        """
        self._rate_limit()

        params = {
            "serverFileName": server_filename,
            "fileName": filename,
        }
        url = self._build_url(self.FILE_DOWNLOAD_PATH, params)

        try:
            resp = self.session.get(url, timeout=60, stream=True)

            if resp.status_code != 200:
                logger.error("secudium_download_failed", status=resp.status_code, filename=filename)
                return []

            suffix = ".xls" if filename.endswith(".xls") else ".xlsx"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                for chunk in resp.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = tmp.name

            logger.debug("secudium_file_downloaded", filename=filename, path=tmp_path)

            ips = parse_xls_file(tmp_path)

            for ip_record in ips:
                if entry_title and not ip_record.get("source_title"):
                    ip_record["source_title"] = entry_title
                if entry_date and not ip_record.get("source_date"):
                    ip_record["source_date"] = entry_date

            from collector.core.archive_manager import archive_file

            archive_file("SECUDIUM", tmp_path, filename, period_start=entry_date, period_end=entry_date)

            try:
                os.unlink(tmp_path)
            except OSError:
                pass

            return ips

        except requests.RequestException as e:
            logger.error("secudium_download_request_error", error=str(e), filename=filename)
            return []

    def _insert_ips(self, ips: list[dict]) -> int:
        """Insert collected IPs into database via save_blacklist_ips (UPSERT)."""
        if not self.db_service:
            logger.warning("secudium_no_db_service")
            return 0

        # Map parser 'ip' key to DB-expected 'ip_address' key and set source
        ip_data = []
        for record in ips:
            entry = dict(record)
            if "ip" in entry and "ip_address" not in entry:
                entry["ip_address"] = entry.pop("ip")
            entry.setdefault("source", "SECUDIUM")
            entry.setdefault("data_source", "SECUDIUM")

            # Enforce detection_date and removal_date = detection_date + 3 months
            detection_date_str = entry.get("source_date") or datetime.now().strftime("%Y-%m-%d")
            entry.setdefault("detection_date", detection_date_str[:10])
            try:
                det_date = datetime.strptime(entry["detection_date"][:10], "%Y-%m-%d")
                entry.setdefault("removal_date", (det_date + relativedelta(months=3)).strftime("%Y-%m-%d"))
            except (ValueError, TypeError):
                entry.setdefault("removal_date", (datetime.now() + relativedelta(months=3)).strftime("%Y-%m-%d"))

            # Map description/reason to reason field
            if not entry.get("reason"):
                entry["reason"] = entry.get("description") or "Secudium Black IP"

            ip_data.append(entry)

        try:
            result = self.db_service.save_blacklist_ips(ip_data)
            inserted = result.get("new_count", 0) + result.get("updated_count", 0)
            logger.info(
                "secudium_db_insert_complete",
                total=result.get("total", 0),
                new=result.get("new_count", 0),
                updated=result.get("updated_count", 0),
            )
            return inserted
        except Exception as e:
            logger.error("secudium_db_insert_error", error=str(e), ip_count=len(ip_data))
            return 0

    def _logout(self):
        """Logout from Secudium (release server session)."""
        try:
            url = self._build_url(self.LOGOUT_PATH)
            self.session.get(url, timeout=10)
            logger.debug("secudium_logout")
        except Exception:
            pass  # Best-effort logout

    def close(self):
        """Cleanup resources."""
        self._logout()
        self.session.close()
        logger.info("secudium_collector_closed")

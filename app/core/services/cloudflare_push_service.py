"""
Cloudflare Lists API Push Service (Real-time)

Purpose:
    - PostgreSQL NOTIFY/LISTEN으로 blacklist 변경 감지
    - 변경 시 Cloudflare Lists API에 전체 IP 목록 Push (bulk replace)
    - Cron 없이 실시간 동기화

Usage:
    python -m core.services.cloudflare_push_service
"""

import time
import psycopg2
import psycopg2.extensions
import select
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import config
from .database_lease import connection_lease

logger = logging.getLogger(__name__)


class CloudflarePushService:
    """Cloudflare Lists API 실시간 Push 서비스"""

    API_BASE = "https://api.cloudflare.com/client/v4"
    RATE_LIMIT_SECONDS = 60
    POLL_INTERVAL = 3
    POLL_TIMEOUT = 120

    def __init__(self, db_service=None):
        """
        Initialize Cloudflare push service

        Args:
            db_service: DatabaseService instance for connection pool access

        Note:
            This service maintains a separate persistent connection (self.db_conn)
            for PostgreSQL LISTEN/NOTIFY functionality. The db_service is available
            for raw connection creation.
        """
        self.db_service = db_service
        self._load_credentials()
        self.session = self._build_session()
        self.db_conn = None
        self.last_update = time.time()

    def _load_credentials(self):
        """Load CF credentials from database"""
        try:
            if self.db_service:
                with connection_lease(self.db_service) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT password, config, encrypted FROM collection_credentials "
                        "WHERE service_name = 'CLOUDFLARE' AND is_active = true"
                    )
                    row = cursor.fetchone()
                    cursor.close()
                if row:
                    password, cf_config, encrypted = row
                    if encrypted and password:
                        try:
                            from .secure_credential_service import SecureCredentialService

                            scs = SecureCredentialService()
                            creds = scs.get_credentials("CLOUDFLARE")
                            if creds:
                                self.api_token = creds.get("password", "")
                                db_config = creds.get("config", {})
                                self.account_id = db_config.get("account_id", "")
                                self.list_id = db_config.get("list_id", "")
                                logger.info("Cloudflare credentials loaded from database")
                                return
                        except Exception as e:
                            logger.warning("Failed to decrypt DB credentials: %s", e)
                    elif cf_config:
                        import json

                        config_data = cf_config if isinstance(cf_config, dict) else json.loads(cf_config)
                        self.api_token = password or ""
                        self.account_id = config_data.get("account_id", "")
                        self.list_id = config_data.get("list_id", "")
                        logger.info("Cloudflare credentials loaded from database (unencrypted)")
                        return
        except Exception as e:
            logger.error("Failed to load Cloudflare credentials from database: %s", e)

        self.api_token = ""
        self.account_id = ""
        self.list_id = ""

    def _build_session(self) -> requests.Session:
        """requests.Session with retry adapter and auth header"""
        session = requests.Session()
        if self.api_token:
            session.headers.update(
                {
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                }
            )
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 502, 503, 504],
            allowed_methods=["GET", "PUT", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        return session

    def connect_database(self):
        """
        PostgreSQL 연결 및 LISTEN 설정

        Note: Creates a persistent connection for LISTEN/NOTIFY.
        This is a special case that requires a connection outside the pool.
        """
        if self.db_service:
            self.db_conn = self.db_service.create_raw_connection()
        else:
            self.db_conn = psycopg2.connect(config.get_postgres_dsn())

        self.db_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = self.db_conn.cursor()
        cursor.execute("LISTEN blacklist_changes;")
        logger.info("PostgreSQL LISTEN started: blacklist_changes")

    def fetch_active_ips(self) -> list[str]:
        """DB에서 활성 IP 목록 직접 조회 (whitelist 제외)"""
        if not self.db_conn:
            logger.error("Database not connected")
            return []

        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT ip_address
                FROM blacklist_ips_with_auto_inactive
                WHERE is_active = true
                  AND ip_address NOT IN (
                      SELECT ip_address FROM whitelist_ips WHERE is_active = true
                  )
                ORDER BY ip_address
            """)
            rows = cursor.fetchall()
            ip_list = [row[0] for row in rows]
            logger.info("Fetched %d active IPs from database", len(ip_list))
            return ip_list
        except Exception as e:
            logger.error("Failed to fetch active IPs: %s", e)
            return []

    def push_to_cloudflare(self, ip_list: list[str]) -> bool:
        """Cloudflare Lists API에 전체 IP 목록 bulk replace"""
        if not self.api_token or not self.account_id or not self.list_id:
            logger.error(
                "Cloudflare not configured (token=%s, account=%s, list=%s)",
                bool(self.api_token),
                bool(self.account_id),
                bool(self.list_id),
            )
            return False

        url = f"{self.API_BASE}/accounts/{self.account_id}/rules/lists/{self.list_id}/items"
        items = [{"ip": ip} for ip in ip_list]

        try:
            response = self.session.put(url, json=items, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                errors = data.get("errors", [])
                logger.error("Cloudflare API error: %s", errors)
                return False

            operation_id = data["result"]["operation_id"]
            logger.info(
                "Cloudflare push started (operation=%s, ips=%d)",
                operation_id,
                len(ip_list),
            )
            return self._poll_operation(operation_id)

        except requests.RequestException as e:
            logger.error("Cloudflare push request failed: %s", e)
            return False

    def _poll_operation(self, operation_id: str) -> bool:
        """Poll bulk operation status until completed/failed/timeout"""
        url = f"{self.API_BASE}/accounts/{self.account_id}/rules/lists/bulk_operations/{operation_id}"
        deadline = time.time() + self.POLL_TIMEOUT

        while time.time() < deadline:
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    logger.error("Poll API error: %s", data.get("errors"))
                    return False

                status = data["result"]["status"]
                if status == "completed":
                    logger.info("Cloudflare push completed (operation=%s)", operation_id)
                    return True
                if status == "failed":
                    logger.error(
                        "Cloudflare operation failed (operation=%s): %s",
                        operation_id,
                        data["result"].get("error"),
                    )
                    return False

                # pending / running
                time.sleep(self.POLL_INTERVAL)

            except requests.RequestException as e:
                logger.error("Poll request failed: %s", e)
                return False

        logger.error(
            "Cloudflare poll timeout (operation=%s, timeout=%ds)",
            operation_id,
            self.POLL_TIMEOUT,
        )
        return False

    def handle_change_notification(self, payload: str):
        """DB 변경 알림 처리

        Note: INSERT/UPDATE/DELETE 모두 전체 재동기화 방식
              - 삭제된 IP도 자동으로 Cloudflare에서 제거됨
        """
        logger.info("Database change detected: %s", payload)

        # Rate limiting (60초에 1번)
        now = time.time()
        if now - self.last_update < self.RATE_LIMIT_SECONDS:
            logger.info("Rate limited (wait %ds)", self.RATE_LIMIT_SECONDS)
            return

        self.last_update = now

        # 현재 DB 상태를 전체 동기화 (삭제된 IP는 자동으로 제외됨)
        ip_list = self.fetch_active_ips()
        if ip_list:
            _ = self.push_to_cloudflare(ip_list)

    def run(self):
        """메인 루프"""
        logger.info("Starting Cloudflare Push Service...")

        if not self.api_token:
            logger.warning("Cloudflare credentials not configured, service disabled")
            return

        # Database 연결
        self.connect_database()

        if not self.db_conn:
            logger.error("Failed to establish database connection")
            return

        logger.info("Listening for database changes...")

        try:
            while True:
                # Wait for notifications (timeout 30s)
                if select.select([self.db_conn], [], [], 30) == ([], [], []):
                    continue

                self.db_conn.poll()
                while self.db_conn.notifies:
                    notify = self.db_conn.notifies.pop(0)
                    self.handle_change_notification(notify.payload)

        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if self.db_conn:
                self.db_conn.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        from .database_service import DatabaseService

        db_service = DatabaseService()
        logger.info("DatabaseService initialized for Cloudflare Push Service")
    except Exception as e:
        logger.warning("Failed to initialize DatabaseService: %s", e)
        db_service = None

    service = CloudflarePushService(db_service=db_service)
    service.run()

from flask import current_app
from werkzeug.local import LocalProxy

cloudflare_service = LocalProxy(lambda: current_app.extensions["cloudflare_service"])

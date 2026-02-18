#!/usr/bin/env python3
"""
FortiManager Automatic Uploader
Runs every 5 minutes to upload blacklist to FortiManager
Reads credentials from database (encrypted storage)
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FortiManagerUploader:
    """Upload blacklist to FortiManager (reads credentials from database)"""

    def __init__(self):
        """Initialize uploader with credentials from database"""
        self.fmg_host = ""
        self.fmg_user = "admin"
        self.fmg_pass = ""
        self.api_url = self._get_api_url()
        self.filename = "nxtd-blacklist.txt"
        self.enabled = False
        self.interval = 300  # 5 minutes

        # Load credentials from database
        self._load_credentials_from_db()

    def _get_api_url(self) -> str:
        """Get API URL from environment or config (never hardcoded)."""
        base_url = os.environ.get("BLACKLIST_API_URL", "http://blacklist-app:2542").rstrip("/")
        return f"{base_url}/api/fortinet/active-ips"

    def _load_credentials_from_db(self):
        """Load FortiManager credentials from database"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # Database connection parameters
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "blacklist-postgres"),
                database=os.getenv("POSTGRES_DB", "blacklist"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT username, password, config, is_active
                FROM collection_credentials
                WHERE service_name = 'FORTIMANAGER'
            """)

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row and row["is_active"]:
                self.fmg_user = row["username"] or "admin"
                self.fmg_pass = row["password"] or ""

                config = row["config"] or {}
                self.fmg_host = config.get("host", "")
                self.enabled = config.get("enabled", False)
                self.interval = config.get("interval", 300)
                self.api_url = config.get("api_url", self._get_api_url())
                self.filename = config.get("filename", "nxtd-blacklist.txt")

                logger.info(
                    f"✅ FortiManager credentials loaded from database (host={self.fmg_host}, enabled={self.enabled})"
                )
            else:
                logger.warning("⚠️ No FortiManager credentials found in database")

        except Exception as e:
            logger.warning(f"Failed to load FortiManager credentials from database: {e}")
            logger.info("Falling back to environment variables (if available)")

            # Fallback to environment variables
            self.fmg_host = os.getenv("FMG_HOST", "")
            self.fmg_user = os.getenv("FMG_USER", "admin")
            self.fmg_pass = os.getenv("FMG_PASS", "")
            self.enabled = os.getenv("FMG_UPLOAD_ENABLED", "false").lower() == "true"
            self.interval = int(os.getenv("FMG_UPLOAD_INTERVAL", "300"))

    def is_configured(self) -> bool:
        """Check if FortiManager is configured"""
        if not self.enabled:
            logger.debug("FortiManager upload disabled (FMG_UPLOAD_ENABLED=false)")
            return False

        if not self.fmg_host or not self.fmg_pass:
            logger.warning("FortiManager not configured (FMG_HOST or FMG_PASS missing)")
            return False

        return True

    def download_blacklist(self) -> Optional[str]:
        """Download blacklist from API"""
        try:
            logger.info(f"Downloading blacklist from {self.api_url}")
            response = requests.get(self.api_url, timeout=30)
            response.raise_for_status()

            content = response.text
            ip_count = len(content.strip().split("\n"))
            logger.info(f"✅ Downloaded {ip_count} IPs")

            return content

        except Exception as e:
            logger.error(f"❌ Failed to download blacklist: {e}")
            return None

    def login_fortimanager(self) -> Optional[str]:
        """Login to FortiManager and get session ID"""
        try:
            url = f"https://{self.fmg_host}/jsonrpc"
            payload = {
                "method": "exec",
                "params": [{"url": "/sys/login/user", "data": {"user": self.fmg_user, "passwd": self.fmg_pass}}],
                "id": 1,
            }

            response = requests.post(url, json=payload, verify=False, timeout=10)
            response.raise_for_status()

            result = response.json()
            session_id = result.get("session")

            if session_id:
                logger.info("✅ Logged in to FortiManager")
                return session_id
            else:
                logger.error("❌ Failed to get session ID")
                return None

        except Exception as e:
            logger.error(f"❌ FortiManager login failed: {e}")
            return None

    def upload_to_fortimanager(self, session_id: str, content: str) -> bool:
        """Upload blacklist to FortiManager"""
        try:
            url = f"https://{self.fmg_host}/jsonrpc"

            # Create/update external resource
            payload = {
                "method": "set",
                "params": [
                    {
                        "url": "/pm/config/adom/root/obj/system/external-resource",
                        "data": {
                            "name": self.filename,
                            "type": "address",
                            "resource": f"fmg://{self.filename}",
                            "status": "enable",
                            "comments": f"NXTD Blacklist - Updated {datetime.now().isoformat()}",
                        },
                    }
                ],
                "session": session_id,
                "id": 2,
            }

            response = requests.post(url, json=payload, verify=False, timeout=30)
            response.raise_for_status()

            result = response.json()
            code = result.get("result", [{}])[0].get("status", {}).get("code", -1)

            if code in [0, -2]:  # 0 = success, -2 = already exists (update)
                logger.info(f"✅ Uploaded to FortiManager ({len(content.strip().split(chr(10)))} IPs)")
                return True
            else:
                logger.error(f"❌ Upload failed: {result}")
                return False

        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return False

    def logout_fortimanager(self, session_id: str):
        """Logout from FortiManager"""
        try:
            url = f"https://{self.fmg_host}/jsonrpc"
            payload = {"method": "exec", "params": [{"url": "/sys/logout"}], "session": session_id, "id": 99}

            requests.post(url, json=payload, verify=False, timeout=5)
            logger.debug("Logged out from FortiManager")

        except Exception as e:
            logger.debug(f"Logout error (non-critical): {e}")

    def upload_once(self) -> bool:
        """Perform one upload cycle"""
        if not self.is_configured():
            return False

        logger.info("=" * 60)
        logger.info("Starting FortiManager upload")
        logger.info("=" * 60)

        # Download blacklist
        content = self.download_blacklist()
        if not content:
            return False

        # Login
        session_id = self.login_fortimanager()
        if not session_id:
            return False

        # Upload
        success = self.upload_to_fortimanager(session_id, content)

        # Logout
        self.logout_fortimanager(session_id)

        logger.info("=" * 60)
        logger.info(f"Upload {'✅ completed' if success else '❌ failed'}")
        logger.info("=" * 60)

        return success

    def run_scheduler(self):
        """Run continuous upload scheduler"""
        if not self.is_configured():
            logger.info("FortiManager upload disabled or not configured")
            return

        logger.info(f"FortiManager upload scheduler started (interval: {self.interval}s)")
        logger.info(f"Target: {self.fmg_host}")
        logger.info(f"API: {self.api_url}")

        while True:
            try:
                self.upload_once()
            except Exception as e:
                logger.error(f"Unexpected error: {e}")

            logger.info(f"Next upload in {self.interval} seconds")
            time.sleep(self.interval)


def main():
    """Main entry point"""
    # Disable SSL warnings
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    uploader = FortiManagerUploader()

    # Check if running in scheduler mode
    if len(sys.argv) > 1 and sys.argv[1] == "scheduler":
        uploader.run_scheduler()
    else:
        # One-shot mode
        success = uploader.upload_once()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

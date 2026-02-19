"""
Health Server for Multi-Collector Scheduler
Provides HTTP health endpoint at :8545/health
"""

from datetime import datetime
from typing import Any
from flask import Flask, jsonify, request
from waitress import serve  # type: ignore[import-untyped]
import threading
import logging
from collections import deque
from collector.config import CollectorConfig
from core.database import DatabaseService

logger = logging.getLogger(__name__)

# Global log buffer for recent logs (circular buffer)
LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=100)


class LogBufferHandler(logging.Handler):
    """Custom log handler that stores logs in memory buffer"""

    def emit(self, record):
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "line": record.lineno,
            }
            LOG_BUFFER.append(log_entry)
        except Exception:
            self.handleError(record)


class HealthServer:
    """Simple health check server for multi-collector"""

    def __init__(self, collectors_ref, scheduler_ref=None, port=8545):
        self.app = Flask(__name__)
        self.collectors = collectors_ref  # Reference to collectors dict
        self.scheduler = scheduler_ref  # Reference to scheduler instance
        self.port = port
        self.thread = None

        # Thread-safe access to pending auth state
        self._pending_auth_lock = threading.Lock()
        self._secudium_pending_auth = None

        # Cached DatabaseService instance (avoid re-creating on every request)
        self._db = DatabaseService()

        # Setup routes
        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "collectors": self._get_collector_status(),
                }
            )

        @self.app.route("/status", methods=["GET"])
        def status():
            return jsonify(
                {
                    "collectors": self._get_collector_status(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route("/logs", methods=["GET"])
        def logs():
            """Get recent logs from memory buffer"""
            return jsonify(
                {
                    "logs": list(LOG_BUFFER),
                    "count": len(LOG_BUFFER),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @self.app.route("/trigger", methods=["POST"])
        def trigger_collection():
            """Trigger manual collection for specified source (REGTECH or SECUDIUM)"""
            try:
                from flask import request as flask_request

                data = flask_request.get_json() or {}

                source = data.get("source", "regtech").upper()
                start_date = data.get("start_date")
                end_date = data.get("end_date")

                if not self.scheduler:
                    return jsonify({"success": False, "error": "Scheduler not available"}), 500

                logger.info(f"Manual collection triggered: {source}, {start_date} ~ {end_date}")

                if source in ("SECUDIUM", "REGTECH"):
                    result = self.scheduler.force_collection(source)
                else:
                    result = self.scheduler.trigger_manual_collection()

                return jsonify(
                    {
                        "success": True,
                        "result": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"Manual trigger error: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                ), 500

        @self.app.route("/api/test-auth/<source>", methods=["POST"])
        def test_authentication(source):
            """Test authentication for a specific source"""
            try:
                source_upper = source.upper()

                if source_upper not in ["REGTECH", "SECUDIUM"]:
                    return jsonify({"success": False, "error": f"Invalid source: {source_upper}"}), 400

                credentials = self._db.get_collection_credentials(source_upper)

                if not credentials:
                    return jsonify(
                        {
                            "success": False,
                            "error": f"No credentials found for {source_upper}",
                        }
                    ), 404

                username = credentials.get("username")
                password = credentials.get("password")
                enabled = credentials.get("enabled", False)

                if not enabled:
                    return jsonify(
                        {
                            "success": False,
                            "error": f"{source_upper} collection is disabled",
                        }
                    ), 403

                # Test authentication
                logger.info(f"Testing authentication for {source_upper} with user: {username}")

                auth_result = False
                if source_upper == "REGTECH":
                    from core.regtech_collector import RegtechCollector

                    collector = RegtechCollector()
                    auth_result = collector.authenticate(username, password)
                elif source_upper == "SECUDIUM":
                    from core.secudium_collector import SecudiumCollector

                    config = credentials.get("config", {})
                    otp_mode = config.get("otp_mode", "auto")

                    collector = SecudiumCollector()

                    if otp_mode == "auto":
                        # Auto mode: full auth with IMAP OTP reading
                        otp_config = CollectorConfig.get_secudium_otp_config()
                        email = config.get("email", "") or otp_config["email"]
                        email_password = config.get("email_password", "") or otp_config["email_password"]
                        imap_server = config.get("imap_server", "") or otp_config["imap_server"]

                        if not email or not email_password:
                            return jsonify(
                                {
                                    "success": False,
                                    "error": "OTP 자동 인증에 필요한 이메일 설정이 없습니다",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )

                        auth_result = collector.authenticate(
                            username,
                            password,
                            email_address=email,
                            email_password=email_password,
                            imap_server=imap_server,
                        )
                    else:
                        # Manual mode: step 1 only, return otp_required
                        step1_result = collector.authenticate_step1(username, password)
                        if step1_result == "otp_required":
                            with self._pending_auth_lock:
                                self._secudium_pending_auth = {
                                    "collector": collector,
                                    "username": username,
                                    "timestamp": datetime.now(),
                                }
                            return jsonify(
                                {
                                    "success": True,
                                    "otp_required": True,
                                    "message": "OTP 입력이 필요합니다",
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        elif step1_result == "success":
                            auth_result = True
                        else:
                            auth_result = False

                test_timestamp = datetime.now()
                test_message = "인증 성공" if auth_result else "인증 실패"
                logger.info(f"Test completed: {source_upper} - {test_message} at {test_timestamp}")

                if auth_result:
                    logger.info(f"✅ {source_upper} authentication successful")
                    return jsonify(
                        {
                            "success": True,
                            "message": "인증 성공",
                            "timestamp": test_timestamp.isoformat(),
                        }
                    )
                else:
                    logger.warning(f"❌ {source_upper} authentication failed")
                    return jsonify(
                        {
                            "success": False,
                            "error": "인증 실패",
                            "timestamp": test_timestamp.isoformat(),
                        }
                    )  # 200 OK - 테스트 결과는 항상 성공 응답

            except Exception as e:
                logger.error(f"Error testing authentication for {source}: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )  # 200 OK - 예외도 테스트 결과로 처리

        @self.app.route("/api/test-auth/secudium/otp", methods=["POST"])
        def submit_secudium_otp():
            """Submit OTP code for Secudium manual authentication (step 2)."""
            try:
                data = request.get_json() or {}
                otp_code = data.get("otp_code", "").strip()

                if not otp_code:
                    return jsonify({"success": False, "error": "OTP 코드가 필요합니다"}), 400

                if len(otp_code) != 6 or not otp_code.isdigit():
                    return jsonify({"success": False, "error": "OTP는 6자리 숫자여야 합니다"}), 400

                with self._pending_auth_lock:
                    pending = self._secudium_pending_auth
                if not pending:
                    return jsonify(
                        {
                            "success": False,
                            "error": "대기 중인 인증 세션이 없습니다. 먼저 연결 테스트를 실행하세요.",
                        }
                    ), 400

                elapsed = (datetime.now() - pending["timestamp"]).total_seconds()
                if elapsed > 300:
                    with self._pending_auth_lock:
                        self._secudium_pending_auth = None
                    return jsonify(
                        {
                            "success": False,
                            "error": "OTP 세션이 만료되었습니다. 다시 연결 테스트를 실행하세요.",
                        }
                    ), 400

                collector = pending["collector"]
                result = collector.authenticate_step2(otp_code)

                if result != "success":
                    with self._pending_auth_lock:
                        self._secudium_pending_auth = None
                    return jsonify(
                        {
                            "success": False,
                            "error": "OTP 인증 실패",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                # Auth succeeded — check if collection was requested
                trigger_collect = data.get("trigger_collect", False)
                if trigger_collect:
                    try:
                        logger.info("OTP auth success + trigger_collect: starting Secudium collection")
                        collect_result = collector.collect_data()
                        with self._pending_auth_lock:
                            self._secudium_pending_auth = None
                        return jsonify(
                            {
                                "success": True,
                                "message": "SECUDIUM 인증 및 수집 완료",
                                "collection": True,
                                "collected_count": collect_result.get("total_ips", 0)
                                if isinstance(collect_result, dict)
                                else 0,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                    except Exception as collect_err:
                        logger.error(f"Collection after OTP auth failed: {collect_err}")
                        with self._pending_auth_lock:
                            self._secudium_pending_auth = None
                        return jsonify(
                            {
                                "success": True,
                                "message": "SECUDIUM 인증 성공, 수집 실패",
                                "collection": False,
                                "error": str(collect_err),
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                with self._pending_auth_lock:
                    self._secudium_pending_auth = None
                return jsonify(
                    {
                        "success": True,
                        "message": "SECUDIUM 인증 성공",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            except Exception as e:
                logger.error(f"Error during Secudium OTP submission: {e}")
                with self._pending_auth_lock:
                    self._secudium_pending_auth = None
                return jsonify(
                    {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        @self.app.route("/api/force-collection/<source>", methods=["POST"])
        def force_collection(source):
            """Force immediate collection for a specific source"""
            try:
                source_upper = source.upper()

                if not self.scheduler:
                    return jsonify({"success": False, "error": "Scheduler not available"}), 500

                if source_upper not in ["REGTECH", "SECUDIUM"]:
                    return jsonify({"success": False, "error": f"Invalid source: {source_upper}"}), 400

                credentials = self._db.get_collection_credentials(source_upper)
                if credentials and not credentials.get("enabled", False):
                    return jsonify(
                        {
                            "success": False,
                            "error": f"{source_upper} 수집이 비활성화되어 있습니다",
                        }
                    ), 403

                logger.info(f"Forcing immediate collection for {source_upper}")
                result = self.scheduler.force_collection(source_upper)

                if result.get("success"):
                    return jsonify(
                        {
                            "success": True,
                            "message": f"{source_upper} 수집 완료",
                            "data": result,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": False,
                            "error": result.get("error", "수집 실패"),
                            "timestamp": datetime.now().isoformat(),
                        }
                    ), 500

            except Exception as e:
                logger.error(f"Error forcing collection for {source}: {e}")
                return jsonify(
                    {
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                ), 500

    def _get_collector_status(self):
        """Get current collector status from scheduler stats"""
        status = {}

        regtech_creds = self._db.get_collection_credentials("REGTECH")
        secudium_creds = self._db.get_collection_credentials("SECUDIUM")

        regtech_enabled = regtech_creds.get("enabled", False) if regtech_creds else False
        secudium_enabled = secudium_creds.get("enabled", False) if secudium_creds else False

        # Use scheduler collection_stats if available (primary source)
        if self.scheduler:
            stats = self.scheduler.collection_stats
            status["REGTECH"] = {
                "enabled": regtech_enabled,
                "run_count": stats.get("total_runs", 0),
                "error_count": stats.get("failed_runs", 0),
                "interval_seconds": stats.get("adaptive_interval", 86400),
                "last_run": stats.get("last_run"),  # Already ISO string or None
                "next_run": self.scheduler._get_next_run_time(),
            }

            # Query SECUDIUM-specific stats from collection_history (DB is source of truth)
            secudium_stats = {"run_count": 0, "error_count": 0, "last_run": None}
            try:
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        SELECT COUNT(*) AS total,
                               COUNT(*) FILTER (WHERE success = false) AS errors,
                               MAX(collection_date) AS last_run
                        FROM collection_history
                        WHERE service_name = 'SECUDIUM'
                        """
                    )
                    row = cursor.fetchone()
                    if row:
                        secudium_stats["run_count"] = row[0] or 0
                        secudium_stats["error_count"] = row[1] or 0
                        secudium_stats["last_run"] = row[2].isoformat() if row[2] else None
                    cursor.close()
            except Exception as e:
                logger.warning(f"Failed to query SECUDIUM stats from DB: {e}")

            status["SECUDIUM"] = {
                "enabled": secudium_enabled,
                "run_count": secudium_stats["run_count"],
                "error_count": secudium_stats["error_count"],
                "interval_seconds": 86400,
                "last_run": secudium_stats["last_run"],
                "next_run": None,
            }
        else:
            # Fallback: collectors_ref is empty or contains {name: method_name} string pairs
            for name in self.collectors:
                cred_enabled = False
                if name == "REGTECH":
                    cred_enabled = regtech_enabled
                elif name == "SECUDIUM":
                    cred_enabled = secudium_enabled
                status[name] = {
                    "enabled": cred_enabled,
                    "run_count": 0,
                    "error_count": 0,
                    "interval_seconds": 0,
                    "last_run": None,
                    "next_run": None,
                }

        return status

    def start(self):
        """Start health server in background thread"""
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"Health server started on port {self.port}")

    def _run_server(self):
        """Run Flask server with waitress"""
        serve(self.app, host="0.0.0.0", port=self.port, _quiet=True)


def start_health_server():
    """Start health server helper"""
    from collector.scheduler import scheduler

    # Scheduler has collection_stats, we can use that or just pass empty for now
    # Ideally, we should pass real collector status references
    server = HealthServer(collectors_ref={}, scheduler_ref=scheduler)
    server._run_server()

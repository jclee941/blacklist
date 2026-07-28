"""
Health Server for Multi-Collector Scheduler
Provides HTTP health endpoint at :8545/health
"""

from datetime import datetime
from typing import Any, TypedDict
from flask import Flask, jsonify
import threading
import logging
import importlib
from collections import deque
from .core.database import DatabaseService

logger = logging.getLogger(__name__)

# Global log buffer for recent logs (circular buffer)
LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=100)


class CollectorStatus(TypedDict):
    enabled: bool
    run_count: int
    error_count: int
    interval_seconds: int
    last_run: str | None
    next_run: str | None


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
            """Trigger manual collection for the REGTECH source."""
            try:
                from flask import request as flask_request

                data = flask_request.get_json() or {}

                source = data.get("source", "regtech").upper()
                start_date = data.get("start_date")
                end_date = data.get("end_date")

                if not self.scheduler:
                    return jsonify({"success": False, "error": "Scheduler not available"}), 500

                logger.info(f"Manual collection triggered: {source}, {start_date} ~ {end_date}")

                if source != "REGTECH":
                    return jsonify({"success": False, "error": f"Invalid source: {source}"}), 400

                result = self.scheduler.force_collection(source)

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

                if source_upper != "REGTECH":
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

                if not isinstance(username, str) or not isinstance(password, str):
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Invalid credentials found for {source_upper}",
                        }
                    ), 400

                # Test authentication
                logger.info(f"Testing authentication for {source_upper} with user: {username}")

                auth_result = False
                if source_upper == "REGTECH":
                    from .core.regtech_collector import RegtechCollector

                    collector = RegtechCollector()
                    auth_result = collector.authenticate(username, password)

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

        @self.app.route("/api/force-collection/<source>", methods=["POST"])
        def force_collection(source):
            """Force immediate collection for a specific source"""
            try:
                source_upper = source.upper()

                if not self.scheduler:
                    return jsonify({"success": False, "error": "Scheduler not available"}), 500

                if source_upper != "REGTECH":
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

    def _get_collector_status(self) -> dict[str, CollectorStatus]:
        """Get current collector status from scheduler stats"""
        status: dict[str, CollectorStatus] = {}

        regtech_creds = self._db.get_collection_credentials("REGTECH")
        regtech_enabled = regtech_creds.get("enabled", False) if regtech_creds else False
        persisted_status = self._db.get_collection_status("REGTECH")

        if persisted_status:
            stats = self.scheduler.collection_stats if self.scheduler else {}
            success_count = int(persisted_status["success_count"] or 0)
            error_count = int(persisted_status["error_count"] or 0)
            status["REGTECH"] = {
                "enabled": bool(regtech_enabled),
                "run_count": success_count + error_count,
                "error_count": error_count,
                "interval_seconds": int(stats.get("adaptive_interval", 0) or 0),
                "last_run": str(persisted_status["last_run"]) if persisted_status["last_run"] else None,
                "next_run": self.scheduler._get_next_run_time() if self.scheduler else None,
            }
        elif self.scheduler:
            stats = self.scheduler.collection_stats
            status["REGTECH"] = {
                "enabled": bool(regtech_enabled),
                "run_count": int(stats.get("total_runs", 0) or 0),
                "error_count": int(stats.get("failed_runs", 0) or 0),
                "interval_seconds": int(stats.get("adaptive_interval", 86400) or 86400),
                "last_run": str(stats["last_run"]) if stats.get("last_run") else None,
                "next_run": self.scheduler._get_next_run_time(),
            }
        else:
            # Fallback: collectors_ref is empty or contains {name: method_name} string pairs
            for name in self.collectors:
                cred_enabled = regtech_enabled if name == "REGTECH" else False
                status[name] = {
                    "enabled": bool(cred_enabled),
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
        waitress = importlib.import_module("waitress")
        waitress.serve(self.app, host="127.0.0.1", port=self.port, _quiet=True)


def start_health_server():
    """Start health server helper"""
    from .scheduler import scheduler

    # Scheduler has collection_stats, we can use that or just pass empty for now
    # Ideally, we should pass real collector status references
    server = HealthServer(collectors_ref={}, scheduler_ref=scheduler)
    server._run_server()

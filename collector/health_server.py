from typing import Any, TypedDict
from flask import Flask
import threading
import logging
import os
from collections import deque
from werkzeug.serving import make_server
from .core.database import DatabaseService
from .core.control_auth import register_control_auth
from .health_routes import register_health_routes

logger = logging.getLogger(__name__)

LOG_BUFFER: deque[dict[str, Any]] = deque(maxlen=100)


class CollectorStatus(TypedDict):
    enabled: bool
    run_count: int
    error_count: int
    interval_seconds: int
    last_run: str | None
    next_run: str | None


class HealthServer:
    def __init__(self, collectors_ref, scheduler_ref=None, port=8545):
        self.app = Flask(__name__)
        self.collectors = collectors_ref
        self.scheduler = scheduler_ref
        self.port = port
        self.thread = None

        # Cached DatabaseService instance (avoid re-creating on every request)
        self._db = DatabaseService()
        register_control_auth(self.app)

        self.log_buffer = LOG_BUFFER
        register_health_routes(self)

    def _get_collector_status(self) -> dict[str, CollectorStatus]:
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
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"Health server started on port {self.port}")

    def _run_server(self):
        certificate = os.environ.get("INTERNAL_TLS_CERT", "/run/blacklist/tls/tls.crt")
        private_key = os.environ.get("INTERNAL_TLS_KEY", "/run/blacklist/tls/tls.key")
        server = make_server(
            "0.0.0.0",
            self.port,
            self.app,
            ssl_context=(certificate, private_key),
            threaded=True,
        )
        server.serve_forever()


def start_health_server():
    from .scheduler import scheduler

    server = HealthServer(collectors_ref={}, scheduler_ref=scheduler)
    server._run_server()

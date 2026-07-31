import threading
import time
from datetime import datetime
from typing import Any, cast

import psycopg2
import requests
from flask import jsonify

from .auth.decorators import public
from .config import config


_background_tasks_lock = threading.Lock()
_background_tasks_started = False


def register_health_route(app):
    @app.route("/health")
    @public
    def health_check():
        try:
            conn = psycopg2.connect(**cast(Any, config.get_postgres_params()))
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in cursor.fetchall()]
            try:
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
                row = cursor.fetchone()
                ip_count = row[0] if row else 0
            except psycopg2.Error:
                ip_count = 0
            cursor.close()
            conn.close()
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": {
                        "connection": "successful",
                        "tables": tables,
                        "blacklist_ips_count": ip_count,
                    },
                    "message": "✅ PostgreSQL connection successful!",
                }
            ), 200
        except Exception as e:
            return jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                }
            ), 500


def start_background_tasks(app):
    try:
        db_service = app.extensions.get("db_service")
        expiry_service = app.extensions.get("expiry_service")
        if db_service and expiry_service:
            expiry_service.check_and_deactivate_expired_ips()

        if config.DISABLE_AUTO_COLLECTION:
            return

        scheduler_service = app.extensions.get("scheduler_service")
        if not db_service or not scheduler_service:
            return

        conn = db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, enabled FROM collection_credentials WHERE service_name = 'REGTECH'")
        result = cursor.fetchone()
        cursor.close()
        db_service.return_connection(conn)

        if result and result[2] and result[0] and result[1]:
            scheduler_service.start()
    except Exception as e:
        app.logger.error("Background task start failed: %s", e)


def check_collector_health(app):
    try:
        url = f"{config.COLLECTOR_URL}/health"
        resp = requests.get(url, timeout=5, **config.COLLECTOR_AUTH_REQUEST_KWARGS)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "healthy":
                app.logger.info("Collector service is healthy at %s", url)
            else:
                app.logger.warning("Collector service returned unhealthy status: %s", data.get("status"))
        else:
            app.logger.warning("Collector service returned HTTP %d at %s", resp.status_code, url)
    except requests.exceptions.ConnectionError:
        app.logger.warning(
            "Collector service unreachable at %s — collection features may be unavailable",
            config.COLLECTOR_URL,
        )
    except Exception as e:
        app.logger.warning("Could not verify collector health: %s", e)


def start_delayed_background_tasks(app):
    def delayed_background_start():
        time.sleep(5)
        with app.app_context():
            check_collector_health(app)
            start_background_tasks(app)

    global _background_tasks_started
    with _background_tasks_lock:
        if not _background_tasks_started:
            threading.Thread(target=delayed_background_start, daemon=True).start()
            _background_tasks_started = True

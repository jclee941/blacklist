import threading
import time
from contextlib import closing
from datetime import datetime
from typing import Any, cast

import psycopg2
import requests
from flask import jsonify

from .auth.decorators import public
from .config import config
from .services.database_lease import connection_lease


_background_tasks_lock = threading.Lock()
_background_tasks_started = False

# Retry delay for the Cloudflare listener: also the poll interval for credentials
# that are saved after startup.
CLOUDFLARE_RETRY_SECONDS = 60


def register_health_route(app):
    @app.route("/health")
    @public
    def health_check():
        try:
            with closing(psycopg2.connect(**cast(Any, config.get_postgres_params()))) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT 1")
                finally:
                    cursor.close()
            return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200
        except Exception:
            app.logger.exception("Health check failed")
            return jsonify({"status": "unhealthy", "timestamp": datetime.now().isoformat()}), 500


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

        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, password, enabled FROM collection_credentials WHERE service_name = 'REGTECH'"
            )
            result = cursor.fetchone()
            cursor.close()

        if result and result[2] and result[0] and result[1]:
            scheduler_service.start()
    except Exception as e:
        app.logger.error("Background task start failed: %s", e)


def start_cloudflare_sync(app):
    """Run the Cloudflare list listener in a daemon thread.

    Gunicorn runs a single worker, so this process owns the LISTEN/NOTIFY connection
    the same way it owns the collection scheduler. The loop re-reads credentials so a
    token saved from the UI after startup activates the sync without a restart.
    """
    service = app.extensions.get("cloudflare_service")
    if service is None:
        app.logger.info("Cloudflare sync not started: service is not registered")
        return

    def cloudflare_sync_loop():
        while True:
            with app.app_context():
                try:
                    service.reload_credentials()
                    if service.is_configured():
                        service.run()
                except Exception:
                    app.logger.exception("Cloudflare sync loop failed")
            time.sleep(CLOUDFLARE_RETRY_SECONDS)

    threading.Thread(target=cloudflare_sync_loop, daemon=True, name="cloudflare-sync").start()


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
            start_cloudflare_sync(app)

    global _background_tasks_started
    with _background_tasks_lock:
        if not _background_tasks_started:
            threading.Thread(target=delayed_background_start, daemon=True).start()
            _background_tasks_started = True

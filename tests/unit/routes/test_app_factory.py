import logging
from unittest.mock import patch, MagicMock

import pytest

from core.app import MemoryHandler, create_app


class TestMemoryHandler:
    def test_init_capacity(self):
        handler = MemoryHandler(capacity=5)
        assert handler.capacity == 5
        assert handler.buffer == []

    def test_emit_stores_formatted_record(self):
        handler = MemoryHandler(capacity=10)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.emit(logging.LogRecord("t", logging.INFO, "", 0, "hello", (), None))
        assert len(handler.buffer) == 1
        assert "hello" in handler.buffer[0]

    def test_emit_evicts_oldest_when_over_capacity(self):
        handler = MemoryHandler(capacity=2)
        handler.setFormatter(logging.Formatter("%(message)s"))
        for i in range(4):
            handler.emit(logging.LogRecord("t", logging.INFO, "", 0, f"m{i}", (), None))
        assert len(handler.buffer) == 2
        assert "m2" in handler.buffer[0]
        assert "m3" in handler.buffer[1]

    def test_get_logs_returns_independent_copy(self):
        handler = MemoryHandler(capacity=10)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.emit(logging.LogRecord("t", logging.INFO, "", 0, "x", (), None))
        logs = handler.get_logs()
        assert logs == handler.buffer
        assert logs is not handler.buffer


class TestCreateApp:
    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_creates_flask_instance(self, _thread, _init):
        from flask import Flask

        app = create_app()
        assert isinstance(app, Flask)
        assert app.config["SECRET_KEY"]

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_health_success(self, _thread, _init):
        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect") as mc:
            conn, cur = MagicMock(), MagicMock()
            cur.fetchall.return_value = [("blacklist_ips",)]
            cur.fetchone.return_value = (42,)
            conn.cursor.return_value = cur
            mc.return_value = conn
            resp = app.test_client().get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["database"]["blacklist_ips_count"] == 42

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_health_db_error(self, _thread, _init):
        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect", side_effect=Exception("conn refused")):
            resp = app.test_client().get("/health")
        assert resp.status_code == 500
        assert resp.get_json()["status"] == "unhealthy"

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_security_headers_present(self, _thread, _init):
        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect") as mc:
            conn, cur = MagicMock(), MagicMock()
            cur.fetchall.return_value = []
            cur.fetchone.return_value = (0,)
            conn.cursor.return_value = cur
            mc.return_value = conn
            resp = app.test_client().get("/health")
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert "strict-origin" in resp.headers.get("Referrer-Policy", "")
        assert "accelerometer" in resp.headers.get("Permissions-Policy", "")

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_gzip_compression_large_response(self, _thread, _init):
        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect") as mc:
            conn, cur = MagicMock(), MagicMock()
            cur.fetchall.return_value = [(f"table_{i}",) for i in range(100)]
            cur.fetchone.return_value = (999,)
            conn.cursor.return_value = cur
            mc.return_value = conn
            resp = app.test_client().get("/health", headers={"Accept-Encoding": "gzip"})
        assert resp.status_code == 200
        assert resp.headers.get("Content-Encoding") == "gzip"

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_no_gzip_without_accept_header(self, _thread, _init):
        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect") as mc:
            conn, cur = MagicMock(), MagicMock()
            cur.fetchall.return_value = [(f"t{i}",) for i in range(100)]
            cur.fetchone.return_value = (999,)
            conn.cursor.return_value = cur
            mc.return_value = conn
            resp = app.test_client().get("/health")
        assert resp.headers.get("Content-Encoding") != "gzip"

    @patch("core.app_lifecycle.threading.Thread")
    @patch("core.services.service_factory.initialize_services", side_effect=RuntimeError("boom"))
    def test_service_init_failure_stops_application_startup(self, _init, _thread):
        with pytest.raises(RuntimeError, match="boom"):
            create_app()

    def test_background_tasks_start_once_per_process(self):
        with (
            patch("core.app_lifecycle._background_tasks_started", False),
            patch("core.services.service_factory.initialize_services", return_value={}),
            patch("core.app_lifecycle.threading.Thread") as thread_class,
        ):
            create_app()
            create_app()

        assert thread_class.call_count == 1
        thread_class.return_value.start.assert_called_once()

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_health_ip_count_query_failure(self, _thread, _init):
        import psycopg2

        app = create_app()
        with patch("core.app_lifecycle.psycopg2.connect") as mc:
            conn, cur = MagicMock(), MagicMock()
            cur.fetchall.return_value = [("blacklist_ips",)]
            cur.execute.side_effect = [None, psycopg2.Error("count failed")]
            cur.fetchone.return_value = None
            conn.cursor.return_value = cur
            mc.return_value = conn
            resp = app.test_client().get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["database"]["blacklist_ips_count"] == 0

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_app_registers_jwt_middleware(self, _thread, _init):
        app = create_app()
        before_request_functions = app.before_request_funcs.get(None, ())

        assert any(
            function.__name__ == "jwt_required_hook" for function in before_request_functions
        )

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_protected_api_requires_bearer_token(self, _thread, _init):
        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": "false"}):
            app = create_app()
            response = app.test_client().get("/api/web-stats")

        assert response.status_code == 401
        assert response.get_json()["code"] == "AUTH_TOKEN_MISSING"

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_login_endpoint_remains_public(self, _thread, _init):
        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": "false"}):
            app = create_app()
            response = app.test_client().post("/api/auth/login", json={})

        assert response.status_code == 400
        assert response.get_json()["code"] == "AUTH_MISSING_CREDENTIALS"

    @patch("core.services.service_factory.initialize_services", return_value={})
    @patch("core.app_lifecycle.threading.Thread")
    def test_secret_key_uses_stable_deploy_secret(self, _thread, _init):
        with patch.dict("os.environ", {"SECRET_KEY": "stable-deploy-secret", "FLASK_SECRET_KEY": ""}):
            app = create_app()

        assert app.config["SECRET_KEY"] == "stable-deploy-secret"

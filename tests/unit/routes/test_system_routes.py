"""Tests for app/core/routes/system_routes.py — system monitoring blueprint."""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    from core.routes.system_routes import system_bp

    app.register_blueprint(system_bp)
    return app


class TestSystemLogs:
    """GET /api/system/logs — returns real system metrics via psutil."""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_logs_success(self):
        mock_psutil = MagicMock()
        mock_vm = MagicMock()
        mock_vm.percent = 55.2
        mock_psutil.cpu_percent.return_value = 12.5
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_disk = MagicMock()
        mock_disk.percent = 40.0
        mock_psutil.disk_usage.return_value = mock_disk

        import sys

        orig = sys.modules.get("psutil")
        sys.modules["psutil"] = mock_psutil
        try:
            with self.app.app_context():
                resp = self.client.get("/api/system/logs")

            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert "system_info" in data
            assert data["system_info"]["cpu_percent"] == 12.5
            assert len(data["logs"]) == 1
        finally:
            if orig is not None:
                sys.modules["psutil"] = orig
            else:
                sys.modules.pop("psutil", None)

    def test_logs_psutil_raises_returns_500(self):
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.side_effect = RuntimeError("hardware error")

        import sys

        orig = sys.modules.get("psutil")
        sys.modules["psutil"] = mock_psutil
        try:
            with self.app.app_context():
                resp = self.client.get("/api/system/logs")

            assert resp.status_code == 500
            data = resp.get_json()
            assert data["success"] is False
        finally:
            if orig is not None:
                sys.modules["psutil"] = orig
            else:
                sys.modules.pop("psutil", None)


class TestSystemStatus:
    """GET /api/system/status — returns hardcoded system status."""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_status_success(self):
        with self.app.app_context():
            resp = self.client.get("/api/system/status")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        status = data["status"]
        assert status["application"]["status"] == "running"
        assert status["database"]["type"] == "PostgreSQL"
        assert status["cache"]["type"] == "Redis"


class TestDetailedHealth:
    """GET /api/system/health — returns detailed health check."""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_success(self):
        with self.app.app_context():
            resp = self.client.get("/api/system/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["health"]["overall_status"] == "healthy"
        services = data["health"]["services"]
        assert services["web_server"] == "healthy"
        assert services["database"] == "healthy"


class TestEnvCheck:
    """GET /api/system/env-check — checks environment variable configuration."""

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch.dict(
        "os.environ",
        {
            "REGTECH_ID": "myuser",
            "REGTECH_PW": "secret",
            "GITHUB_TOKEN": "ghp_xxx",
            "GITHUB_REPO_OWNER": "org",
            "GITHUB_REPO_NAME": "repo",
            "VERSION": "3.5.60",
            "BUILD_NUMBER": "42",
            "VCS_REF": "abc1234def",
        },
    )
    def test_env_check_configured(self):
        with self.app.app_context():
            resp = self.client.get("/api/system/env-check")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        env = data["environment"]
        assert env["regtech_auth"]["id_configured"] is True
        assert env["regtech_auth"]["pw_configured"] is True
        assert env["regtech_auth"]["id_length"] == 6
        assert env["github_integration"]["token_configured"] is True
        assert env["github_integration"]["repo_owner"] == "org"
        assert env["build_info"]["version"] == "3.5.60"
        assert env["build_info"]["vcs_ref"] == "abc1234"

    @patch.dict("os.environ", {}, clear=True)
    def test_env_check_not_configured(self):
        with self.app.app_context():
            resp = self.client.get("/api/system/env-check")

        assert resp.status_code == 200
        data = resp.get_json()
        env = data["environment"]
        assert env["regtech_auth"]["id_configured"] is False
        assert env["regtech_auth"]["pw_configured"] is False
        assert env["github_integration"]["token_configured"] is False
        assert env["build_info"]["version"] == "unknown"

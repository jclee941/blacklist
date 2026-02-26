"""
Tests for system_api.py — endpoints attached directly to api_bp.
Covers: /api/monitoring/dashboard, /api/system-stats, /api/chart/data,
        /api/logs, /api/auth/status, /api/reset-database,
        /api/database/schema, /api/database/schema/update, /api/database/schema/fix
"""

import os
from unittest.mock import MagicMock, patch, mock_open
from flask import Flask, g
from datetime import datetime, date


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api_routes import api_bp

    app.register_blueprint(api_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app


def _mock_db_service_with_cursor(cursor_results):
    """Build a mock db_service whose get_connection().cursor() returns sequential results."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = cursor_results.get("fetchone", [])
    mock_cursor.fetchall.side_effect = cursor_results.get("fetchall", [])
    mock_cursor.close = MagicMock()

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    mock_db = MagicMock()
    mock_db.get_connection.return_value = mock_conn
    mock_db.return_connection = MagicMock()
    return mock_db


# ─── Monitoring Dashboard ──────────────────────────────────────────


class TestMonitoringDashboard:
    """GET /api/monitoring/dashboard"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_dashboard_success(self):
        mock_db = _mock_db_service_with_cursor(
            {
                "fetchone": [
                    {"total_ips": 1000},
                    {"active_ips": 800},
                ],
                "fetchall": [
                    [
                        {
                            "service_name": "REGTECH",
                            "collection_date": datetime(2025, 1, 1, 12, 0),
                            "items_collected": 50,
                            "success": True,
                        }
                    ]
                ],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/monitoring/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["total_ips"] == 1000
        assert data["data"]["active_ips"] == 800
        assert len(data["data"]["recent_collections"]) == 1

    def test_dashboard_db_error(self):
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("DB down")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/monitoring/dashboard")
        assert resp.status_code == 500


# ─── System Stats ──────────────────────────────────────────────────


class TestSystemStats:
    """GET /api/system-stats"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_system_stats_success(self):
        mock_db = _mock_db_service_with_cursor(
            {
                "fetchone": [
                    {"total_ips": 500},
                    {"active_ips": 300},
                    {"expired_ips": 200},
                ],
                "fetchall": [
                    [
                        {"data_source": "REGTECH", "count": 300, "percentage": 60.0},
                        {"data_source": "MANUAL", "count": 200, "percentage": 40.0},
                    ]
                ],
            }
        )
        # Add the last_update fetchone
        mock_cursor = mock_db.get_connection().cursor()
        mock_cursor.fetchone.side_effect = [
            {"total_ips": 500},
            {"active_ips": 300},
            {"expired_ips": 200},
            {"last_update": datetime(2025, 6, 1, 10, 0)},
        ]
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/system-stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["total_ips"] == 500
        assert data["data"]["active_ips"] == 300
        assert data["data"]["expired_ips"] == 200

    def test_system_stats_db_error(self):
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("fail")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/system-stats")
        assert resp.status_code == 500


# ─── Chart Data ────────────────────────────────────────────────────


class TestChartData:
    """GET /api/chart/data"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_chart_data_success(self):
        mock_db = _mock_db_service_with_cursor(
            {
                "fetchone": [],
                "fetchall": [
                    [
                        {"date": date(2025, 1, 1), "collected": 100},
                        {"date": date(2025, 1, 2), "collected": 200},
                    ]
                ],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/chart/data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]["daily_collection"]) == 2

    def test_chart_data_empty(self):
        mock_db = _mock_db_service_with_cursor(
            {
                "fetchone": [],
                "fetchall": [[]],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/chart/data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["daily_collection"] == []

    def test_chart_data_db_error(self):
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("fail")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/chart/data")
        assert resp.status_code == 500


# ─── System Logs ───────────────────────────────────────────────────


class TestSystemLogs:
    """GET /api/logs"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    @patch("os.path.exists", return_value=False)
    def test_logs_file_not_found(self, mock_exists):
        resp = self.client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total_lines"] == 0

    @patch("builtins.open", mock_open(read_data="line1\nline2\nline3\n"))
    @patch("os.path.exists", return_value=True)
    def test_logs_returns_lines(self, mock_exists):
        resp = self.client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total_lines"] == 3
        assert "line1" in data["data"]["logs"]

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", side_effect=PermissionError("no access"))
    def test_logs_read_error(self, mock_open_fn, mock_exists):
        resp = self.client.get("/api/logs")
        assert resp.status_code == 500


# ─── Auth Status ───────────────────────────────────────────────────


class TestAuthStatus:
    """GET /api/auth/status"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_auth_status_configured(self):
        mock_svc = MagicMock()
        mock_svc.get_credentials.return_value = {"regtech_id": "user123"}
        self.app.extensions["regtech_config_service"] = mock_svc

        resp = self.client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["has_regtech_credentials"] is True
        assert data["data"]["regtech_configured"] is True

    def test_auth_status_not_configured(self):
        mock_svc = MagicMock()
        mock_svc.get_credentials.return_value = {}
        self.app.extensions["regtech_config_service"] = mock_svc

        resp = self.client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["has_regtech_credentials"] is False

    def test_auth_status_none_credentials(self):
        mock_svc = MagicMock()
        mock_svc.get_credentials.return_value = None
        self.app.extensions["regtech_config_service"] = mock_svc

        resp = self.client.get("/api/auth/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["has_regtech_credentials"] is False

    def test_auth_status_service_error(self):
        mock_svc = MagicMock()
        mock_svc.get_credentials.side_effect = Exception("broken")
        self.app.extensions["regtech_config_service"] = mock_svc

        resp = self.client.get("/api/auth/status")
        assert resp.status_code == 500


# ─── Reset Database ────────────────────────────────────────────────


class TestResetDatabase:
    """POST /api/reset-database"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    @patch.dict(os.environ, {"ADMIN_RESET_KEY": "secret123"}, clear=False)
    def test_reset_success(self):
        mock_db = MagicMock()
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/reset-database",
            headers={"X-Admin-Key": "secret123"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "blacklist_ips" in data["data"]["deleted_tables"]

    @patch.dict(os.environ, {"ADMIN_RESET_KEY": "secret123"}, clear=False)
    def test_reset_wrong_key(self):
        """Wrong key: UnauthorizedError has bug (details kwarg unsupported) -> TypeError -> 500."""
        resp = self.client.post(
            "/api/reset-database",
            headers={"X-Admin-Key": "wrong"},
        )
        # BUG in source: UnauthorizedError() called with unsupported 'details' kwarg
        # -> TypeError -> 500 instead of 401
        assert resp.status_code == 500

    @patch.dict(os.environ, {"ADMIN_RESET_KEY": "secret123"}, clear=False)
    def test_reset_no_key(self):
        """No key: same UnauthorizedError bug -> 500."""
        resp = self.client.post("/api/reset-database")
        assert resp.status_code == 500

    @patch.dict(os.environ, {}, clear=True)
    def test_reset_no_env_key(self):
        """When ADMIN_RESET_KEY env var is not set: UnauthorizedError bug -> 500."""
        resp = self.client.post("/api/reset-database")
        assert resp.status_code == 500

    @patch.dict(os.environ, {"ADMIN_RESET_KEY": "secret123"}, clear=False)
    def test_reset_db_error(self):
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = Exception("DB locked")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/reset-database",
            headers={"X-Admin-Key": "secret123"},
        )
        assert resp.status_code == 500


# ─── Database Schema ───────────────────────────────────────────────


class TestDatabaseSchema:
    """GET /api/database/schema"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_schema_success(self):
        mock_db = _mock_db_service_with_cursor(
            {
                "fetchone": [],
                "fetchall": [
                    [
                        {
                            "table_name": "blacklist_ips",
                            "column_name": "id",
                            "data_type": "integer",
                            "is_nullable": "NO",
                        },
                        {
                            "table_name": "blacklist_ips",
                            "column_name": "ip_address",
                            "data_type": "varchar",
                            "is_nullable": "NO",
                        },
                    ]
                ],
            }
        )
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/database/schema")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "blacklist_ips" in data["data"]["schema"]
        assert data["data"]["total_tables"] == 1

    def test_schema_db_error(self):
        mock_db = MagicMock()
        mock_db.get_connection.side_effect = Exception("fail")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.get("/api/database/schema")
        assert resp.status_code == 500


class TestSchemaUpdate:
    """POST /api/database/schema/update"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_schema_update_success(self):
        mock_db = MagicMock()
        mock_db.update_schema.return_value = {"applied": 3}
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post("/api/database/schema/update")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["result"]["applied"] == 3

    def test_schema_update_error(self):
        mock_db = MagicMock()
        mock_db.update_schema.side_effect = Exception("fail")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post("/api/database/schema/update")
        assert resp.status_code == 500


class TestSchemaFix:
    """POST /api/database/schema/fix"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_schema_fix_success(self):
        mock_db = MagicMock()
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post("/api/database/schema/fix")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "country" in data["data"]["columns_added"]
        assert mock_db.execute_query.call_count == 3

    def test_schema_fix_error(self):
        mock_db = MagicMock()
        mock_db.execute_query.side_effect = Exception("permission denied")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post("/api/database/schema/fix")
        assert resp.status_code == 500

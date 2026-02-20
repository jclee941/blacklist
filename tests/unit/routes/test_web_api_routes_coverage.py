"""Unit tests for app/core/routes/web/api_routes.py — web API endpoints."""

from unittest.mock import MagicMock
from datetime import datetime
from flask import Flask, Blueprint

import core.routes.web.api_routes as mod


def make_app():
    """Create test app with web API routes and mocked services."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Support context manager pattern: with db.get_connection() as conn: with conn.cursor() as cur:
    mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    app.extensions["db_service"] = mock_db
    app.extensions["collection_service"] = MagicMock()

    # Register routes on a test blueprint to avoid collision with other tests
    bp = Blueprint("web_api_test", __name__)
    bp.add_url_rule("/favicon.ico", "favicon", mod.favicon)
    bp.add_url_rule("/api/search/<ip>", "api_search_ip", mod.api_search_ip)
    bp.add_url_rule("/api/web-stats", "api_stats", mod.api_stats)
    bp.add_url_rule("/api/collection/status", "api_collection_status", mod.api_collection_status)
    bp.add_url_rule("/api/collection/stats", "api_collection_stats", mod.api_collection_stats)
    bp.add_url_rule("/api/blacklist/list", "api_blacklist_list", mod.api_blacklist_list)
    bp.add_url_rule("/api/blacklist/export", "api_blacklist_export", mod.api_blacklist_export)
    bp.add_url_rule("/api/blacklist/export-raw", "api_blacklist_export_raw", mod.api_blacklist_export_raw)
    bp.add_url_rule("/api/chart-data", "api_chart_data", mod.api_chart_data)
    bp.add_url_rule("/api/connection/status", "api_connection_status", mod.api_connection_status)
    app.register_blueprint(bp)

    return app, mock_cursor


class TestFavicon:
    def test_returns_404(self):
        app, _ = make_app()
        resp = app.test_client().get("/favicon.ico")
        assert resp.status_code == 404


class TestSearchIp:
    def test_found(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            ("1.2.3.4", "REGTECH", "malware", 80, 5, True, datetime(2025, 6, 1), datetime(2025, 1, 1)),
        ]
        resp = app.test_client().get("/api/search/1.2.3.4")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["found"] is True
        assert len(data["data"]) == 1

    def test_not_found(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = []
        resp = app.test_client().get("/api/search/8.8.8.8")
        assert resp.status_code == 200
        assert resp.get_json()["found"] is False

    def test_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.side_effect = Exception("db")
        resp = app.test_client().get("/api/search/1.1.1.1")
        assert resp.status_code == 500


class TestWebStats:
    def test_success(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchone.return_value = (1000, 800, 50, 200)
        mock_cursor.fetchall.return_value = [("REGTECH", 500), ("MANUAL", 300)]
        resp = app.test_client().get("/api/web-stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["stats"]["total_ips"] == 1000
        assert len(data["source_breakdown"]) == 2

    def test_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchone.side_effect = Exception("db")
        resp = app.test_client().get("/api/web-stats")
        assert resp.status_code == 500


class TestCollectionStatus:
    def test_success(self):
        app, _ = make_app()
        app.extensions["collection_service"].get_collection_status.return_value = {
            "status": "idle",
            "last_run": "2025-01-01",
        }
        resp = app.test_client().get("/api/collection/status")
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_error(self):
        app, _ = make_app()
        app.extensions["collection_service"].get_collection_status.side_effect = Exception("fail")
        resp = app.test_client().get("/api/collection/status")
        assert resp.status_code == 500


class TestCollectionStats:
    def test_success(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchone.return_value = (100, 95, 1500.5, 5000)
        resp = app.test_client().get("/api/collection/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["collection_stats"]["total_collections"] == 100
        assert data["collection_stats"]["success_rate"] == 95.0

    def test_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchone.side_effect = Exception("db")
        resp = app.test_client().get("/api/collection/stats")
        assert resp.status_code == 500


class TestBlacklistList:
    def test_default(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            (
                "1.2.3.4",
                "REGTECH",
                "KR",
                datetime(2025, 1, 1),
                None,
                "malware",
                80,
                5,
                True,
                datetime(2025, 6, 1),
                datetime(2025, 1, 1),
            ),
        ]
        mock_cursor.fetchone.return_value = (1,)
        resp = app.test_client().get("/api/blacklist/list")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    def test_with_filters(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = (0,)
        resp = app.test_client().get("/api/blacklist/list?source=REGTECH&active_only=false&page=2&per_page=25")
        assert resp.status_code == 200

    def test_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.side_effect = Exception("db")
        resp = app.test_client().get("/api/blacklist/list")
        assert resp.status_code == 500


class TestBlacklistExport:
    def test_csv_export(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            (
                "1.2.3.4",
                "REGTECH",
                "KR",
                datetime(2025, 1, 1),
                datetime(2025, 6, 1),
                "malware",
                80,
                5,
                True,
                datetime(2025, 5, 1, 12, 0),
                datetime(2025, 1, 1, 10, 0),
            ),
        ]
        resp = app.test_client().get("/api/blacklist/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_with_filters(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = []
        resp = app.test_client().get("/api/blacklist/export?source=MANUAL&active_only=false")
        assert resp.status_code == 200

    def test_export_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.side_effect = Exception("db")
        resp = app.test_client().get("/api/blacklist/export")
        assert resp.status_code == 500


class TestBlacklistExportRaw:
    def test_export_raw_with_dict_raw_data(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            (
                "1.2.3.4",
                "REGTECH",
                "KR",
                datetime(2025, 1, 1),
                datetime(2025, 6, 1),
                "malware",
                80,
                5,
                True,
                datetime(2025, 5, 1, 12, 0),
                datetime(2025, 1, 1, 10, 0),
                {"ip_address": "1.2.3.4", "reason": "malware"},
            ),
        ]
        resp = app.test_client().get("/api/blacklist/export-raw")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_export_raw_with_string_raw_data(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            (
                "5.6.7.8",
                "MANUAL",
                None,
                None,
                None,
                "test",
                50,
                1,
                True,
                None,
                datetime(2025, 3, 1),
                '{"key": "value"}',
            ),
        ]
        resp = app.test_client().get("/api/blacklist/export-raw?include_empty=true")
        assert resp.status_code == 200

    def test_export_raw_null_raw_data(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            ("9.0.1.2", "REGTECH", None, None, None, "r", 50, 1, False, None, datetime(2025, 1, 1), None),
        ]
        resp = app.test_client().get("/api/blacklist/export-raw?include_empty=true&active_only=false")
        assert resp.status_code == 200

    def test_export_raw_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.side_effect = Exception("db")
        resp = app.test_client().get("/api/blacklist/export-raw")
        assert resp.status_code == 500


class TestChartData:
    def test_daily_chart(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [
            (datetime(2025, 1, 1).date(), 50),
            (datetime(2025, 1, 2).date(), 30),
        ]
        resp = app.test_client().get("/api/chart-data?type=daily")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chart_type"] == "daily"
        assert len(data["data"]) == 2

    def test_source_chart(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.return_value = [("REGTECH", 500)]
        resp = app.test_client().get("/api/chart-data?type=source")
        assert resp.status_code == 200

    def test_error(self):
        app, mock_cursor = make_app()
        mock_cursor.fetchall.side_effect = Exception("db")
        resp = app.test_client().get("/api/chart-data")
        assert resp.status_code == 500


class TestConnectionStatus:
    def test_success(self):
        app, _ = make_app()
        app.extensions["db_service"].get_connection_status.return_value = {
            "status": "healthy",
            "pool_size": 5,
            "active": 2,
        }
        resp = app.test_client().get("/api/connection/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["database_connected"] is True

    def test_error(self):
        app, _ = make_app()
        app.extensions["db_service"].get_connection_status.side_effect = Exception("fail")
        resp = app.test_client().get("/api/connection/status")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["database_connected"] is False

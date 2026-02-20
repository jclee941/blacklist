import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask, g
from datetime import datetime

from core.errors.handlers import register_error_handlers


def make_app():
    """Create test app with analytics blueprint"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)
    from core.routes.api.analytics import detection_bp

    app.register_blueprint(detection_bp)
    app.extensions["db_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


class TestAnalyticsOverview:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_overview_success(self, client, app):
        """GET /analytics/overview returns stats"""
        app.extensions["db_service"].query.return_value = [
            {
                "total_ips": 5000,
                "active_ips": 3000,
                "source_count": 5,
                "new_today": 100,
                "new_week": 500,
            }
        ]

        response = client.get("/analytics/overview")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["total_ips"] == 5000
        assert data["data"]["active_ips"] == 3000
        assert data["data"]["new_today"] == 100

    def test_overview_empty_result(self, client, app):
        """GET /analytics/overview with empty result uses defaults"""
        app.extensions["db_service"].query.return_value = [{}]

        response = client.get("/analytics/overview")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["total_ips"] == 0

    def test_overview_db_error(self, client, app):
        """GET /analytics/overview with DB error raises DatabaseError (500)"""
        app.extensions["db_service"].query.side_effect = Exception("DB down")

        response = client.get("/analytics/overview")
        assert response.status_code == 500


class TestDetectionTimeline:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_timeline_default_30_days(self, client, app):
        """GET /analytics/detection-timeline uses 30 days default"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []  # empty results
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/analytics/detection-timeline")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_timeline_invalid_days(self, client, app):
        """GET /analytics/detection-timeline?days=abc returns 400"""
        response = client.get("/analytics/detection-timeline?days=abc")
        assert response.status_code == 400


class TestRealTimeLog:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_real_time_log_success(self, client, app):
        """GET /analytics/real-time-log returns log entries"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (datetime(2026, 1, 1, 12, 0), "10.0.0.1", "REGTECH", "2026-01-01", 0.95),
        ]
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/analytics/real-time-log")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["metadata"]["total_entries"] == 1
        assert data["data"]["log_entries"][0]["ip_address"] == "10.0.0.1"

    def test_real_time_log_empty(self, client, app):
        """GET /analytics/real-time-log with no entries"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/analytics/real-time-log")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["metadata"]["total_entries"] == 0

    def test_real_time_log_db_error(self, client, app):
        """GET /analytics/real-time-log with DB error returns 500"""
        app.extensions["db_service"].get_connection.side_effect = Exception("DB down")

        response = client.get("/analytics/real-time-log")
        assert response.status_code == 500

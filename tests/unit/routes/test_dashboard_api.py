"""Unit tests for dashboard API routes."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from flask import Flask


class TestDashboardStats:
    """Tests for GET /stats."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        from core.routes.api.dashboard_api import dashboard_bp

        app.register_blueprint(dashboard_bp)

        mock_db = Mock()
        app.extensions["db_service"] = mock_db
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_stats_success(self, client, app):
        """Stats endpoint returns aggregated data."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            {"count": 100},
            {"count": 80},
            {"count": 5},
            {"count": 10},
            {"last_update": datetime(2026, 1, 1)},
        ]
        mock_cursor.fetchall.side_effect = [
            [{"source": "REGTECH", "count": 50}],
            [{"country": "KR", "count": 30}],
            [{"reason": "malware", "count": 20}],
        ]

        response = client.get("/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data

    def test_stats_db_error_returns_zeroed_data(self, client, app):
        """DB error returns zeroed stats with success=False."""
        app.extensions["db_service"].get_connection.side_effect = Exception("DB down")
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False

    def test_stats_no_db_service(self, client, app):
        """Missing db_service is handled gracefully."""
        app.extensions.pop("db_service", None)
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False


class TestDashboardStatus:
    """Tests for GET /status."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        from core.routes.api.dashboard_api import dashboard_bp

        app.register_blueprint(dashboard_bp)
        app.extensions["db_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_status_healthy(self, client, app):
        """Status returns healthy when DB is up."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        app.extensions["db_service"].get_connection.return_value = mock_conn

        response = client.get("/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_status_db_down(self, client, app):
        """Status handles DB connection failure."""
        app.extensions["db_service"].get_connection.side_effect = Exception("Connection refused")
        response = client.get("/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["components"]["database"]["status"] == "unhealthy"

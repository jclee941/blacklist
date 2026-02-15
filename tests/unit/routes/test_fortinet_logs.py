import pytest
from unittest.mock import MagicMock
from datetime import datetime, date
from flask import Flask, g


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.fortinet.logs import fortinet_logs_bp
    from core.errors.handlers import register_error_handlers

    app.register_blueprint(fortinet_logs_bp, url_prefix="/api/fortinet")
    register_error_handlers(app)

    app.extensions["db_service"] = MagicMock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


@pytest.fixture
def app():
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


class TestActiveSessions:
    def test_active_sessions_success(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "id": 1,
                    "ip_address": "1.2.3.4",
                    "country": "KR",
                    "reason": "malware",
                    "confidence_level": 90,
                    "detection_date": datetime(2026, 1, 1),
                    "removal_date": None,
                    "is_active": True,
                    "created_at": datetime(2026, 1, 1),
                    "updated_at": datetime(2026, 1, 2),
                    "active_hours": 48.5,
                }
            ],
            [
                {
                    "total_sessions": 1,
                    "active_count": 1,
                    "last_hour": 0,
                    "last_24h": 1,
                    "unique_countries": 1,
                }
            ],
        ]
        response = client.get("/api/fortinet/active-sessions")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["session_status"] == "active"
        assert data["stats"]["total_sessions"] == 1

    def test_active_sessions_expired_status(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "id": 2,
                    "ip_address": "5.6.7.8",
                    "country": "US",
                    "reason": "scan",
                    "confidence_level": 50,
                    "detection_date": datetime(2025, 1, 1),
                    "removal_date": date(2025, 6, 1),
                    "is_active": False,
                    "created_at": datetime(2025, 1, 1),
                    "updated_at": None,
                    "active_hours": 1000.0,
                }
            ],
            [
                {
                    "total_sessions": 1,
                    "active_count": 0,
                    "last_hour": 0,
                    "last_24h": 0,
                    "unique_countries": 1,
                }
            ],
        ]
        response = client.get("/api/fortinet/active-sessions")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"][0]["session_status"] == "expired"

    def test_active_sessions_invalid_limit(self, client, app):
        response = client.get("/api/fortinet/active-sessions?limit=0")
        assert response.status_code == 400

    def test_active_sessions_limit_over_500(self, client, app):
        response = client.get("/api/fortinet/active-sessions?limit=501")
        assert response.status_code == 400

    def test_active_sessions_invalid_hours(self, client, app):
        response = client.get("/api/fortinet/active-sessions?hours=0")
        assert response.status_code == 400

    def test_active_sessions_hours_over_limit(self, client, app):
        response = client.get("/api/fortinet/active-sessions?hours=8761")
        assert response.status_code == 400

    def test_active_sessions_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB down")
        response = client.get("/api/fortinet/active-sessions")
        assert response.status_code == 500


class TestPullLogs:
    def test_pull_logs_success(self, client, app):
        app.extensions["db_service"].query.side_effect = [
            [
                {
                    "id": 1,
                    "device_ip": "10.0.0.1",
                    "user_agent": "FortiGate/7.2",
                    "request_path": "/blocklist",
                    "ip_count": 100,
                    "response_time_ms": 25,
                    "response_status": 200,
                    "created_at": datetime(2026, 2, 1, 12, 0),
                }
            ],
            [
                {
                    "total_pulls": 10,
                    "successful_pulls": 9,
                    "failed_pulls": 1,
                    "unique_devices": 2,
                }
            ],
        ]
        response = client.get("/api/fortinet/pull-logs")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["device_ip"] == "10.0.0.1"
        assert data["stats"]["total_pulls"] == 10

    def test_pull_logs_invalid_limit(self, client, app):
        response = client.get("/api/fortinet/pull-logs?limit=0")
        assert response.status_code == 400

    def test_pull_logs_limit_over_500(self, client, app):
        response = client.get("/api/fortinet/pull-logs?limit=501")
        assert response.status_code == 400

    def test_pull_logs_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB error")
        response = client.get("/api/fortinet/pull-logs")
        assert response.status_code == 500

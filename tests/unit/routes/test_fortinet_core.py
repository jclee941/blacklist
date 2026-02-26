import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from flask import Flask, g


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.fortinet.core import fortinet_core_bp
    from core.errors.handlers import register_error_handlers

    app.register_blueprint(fortinet_core_bp, url_prefix="/api/fortinet")
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


class TestFortinetHealth:
    def test_health_success(self, client, app):
        app.extensions["db_service"].query.return_value = [{"count": 42}]
        response = client.get("/api/fortinet/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["active_ips"] == 42
        assert data["data"]["database"] == "healthy"

    def test_health_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB down")
        response = client.get("/api/fortinet/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["status"] == "unhealthy"
        assert data["data"]["database"] == "unhealthy"
        assert data["data"]["active_ips"] == 0


class TestFortinetActiveIps:
    def test_active_ips_success(self, client, app):
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
                }
            ],
            [{"count": 1}],
        ]
        response = client.get("/api/fortinet/active-ips?limit=10&page=1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["ip_address"] == "1.2.3.4"
        assert data["total"] == 1

    def test_active_ips_default_pagination(self, client, app):
        app.extensions["db_service"].query.side_effect = [[], [{"count": 0}]]
        response = client.get("/api/fortinet/active-ips")
        assert response.status_code == 200
        data = response.get_json()
        assert data["page"] == 1
        assert data["limit"] == 20

    def test_active_ips_invalid_limit_zero(self, client, app):
        response = client.get("/api/fortinet/active-ips?limit=0")
        assert response.status_code == 400

    def test_active_ips_limit_over_1000(self, client, app):
        response = client.get("/api/fortinet/active-ips?limit=1001")
        assert response.status_code == 400

    def test_active_ips_invalid_page(self, client, app):
        response = client.get("/api/fortinet/active-ips?page=0")
        assert response.status_code == 400

    def test_active_ips_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB error")
        response = client.get("/api/fortinet/active-ips")
        assert response.status_code == 500


class TestFortinetBlocklist:
    @patch("core.routes.api.fortinet.core._log_pull_request")
    def test_blocklist_text_format(self, mock_log, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4"},
            {"ip_address": "5.6.7.8"},
        ]
        response = client.get("/api/fortinet/blocklist")
        assert response.status_code == 200
        assert response.content_type == "text/plain; charset=utf-8"
        assert "1.2.3.4" in response.data.decode()
        assert "5.6.7.8" in response.data.decode()
        assert response.headers["X-Total-IPs"] == "2"
        mock_log.assert_called_once()

    @patch("core.routes.api.fortinet.core._log_pull_request")
    def test_blocklist_json_format(self, mock_log, client, app):
        app.extensions["db_service"].query.return_value = [{"ip_address": "1.2.3.4"}]
        response = client.get("/api/fortinet/blocklist?format=json")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["total"] == 1
        assert "1.2.3.4" in data["data"]["blocklist"]

    def test_blocklist_invalid_format(self, client, app):
        response = client.get("/api/fortinet/blocklist?format=xml")
        assert response.status_code == 400

    @patch("core.routes.api.fortinet.core._log_pull_request")
    def test_blocklist_text_db_error(self, mock_log, client, app):
        app.extensions["db_service"].query.side_effect = RuntimeError("fail")
        response = client.get("/api/fortinet/blocklist?format=text")
        assert response.status_code == 500
        assert b"Error" in response.data

    @patch("core.routes.api.fortinet.core._log_pull_request")
    def test_blocklist_json_db_error(self, mock_log, client, app):
        app.extensions["db_service"].query.side_effect = RuntimeError("fail")
        response = client.get("/api/fortinet/blocklist?format=json")
        assert response.status_code == 500


class TestFortinetConfig:
    def test_config_success(self, client, app):
        response = client.get("/api/fortinet/config")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "external_blocklist_url" in data["data"]
        assert data["data"]["enabled"] is True
        assert data["data"]["api_version"] == "1.0"

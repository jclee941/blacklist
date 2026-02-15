import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from flask import Flask, g


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.fortinet.management import fortinet_management_bp
    from core.errors.handlers import register_error_handlers

    app.register_blueprint(fortinet_management_bp, url_prefix="/api/fortinet")
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


class TestGetDevices:
    def test_devices_success(self, client, app):
        app.extensions["db_service"].query.return_value = [
            {
                "id": 1,
                "device_ip": "10.0.0.1",
                "device_name": "FGT-HQ",
                "device_model": "FortiGate-60F",
                "firmware_version": "7.2.5",
                "serial_number": "FGT60F1234",
                "location": "Seoul",
                "is_active": True,
                "last_seen": datetime(2026, 2, 1),
                "config": {"vdom": "root"},
                "created_at": datetime(2025, 1, 1),
                "updated_at": datetime(2026, 2, 1),
            }
        ]
        response = client.get("/api/fortinet/devices")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["device_name"] == "FGT-HQ"
        assert data["total"] == 1

    def test_devices_empty(self, client, app):
        app.extensions["db_service"].query.return_value = []
        response = client.get("/api/fortinet/devices")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 0

    def test_devices_db_error(self, client, app):
        app.extensions["db_service"].query.side_effect = Exception("DB error")
        response = client.get("/api/fortinet/devices")
        assert response.status_code == 500


class TestRegisterToFortigate:
    def test_register_missing_fields(self, client, app):
        response = client.post(
            "/api/fortinet/register",
            json={"device_ip": "10.0.0.1"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_register_dry_run(self, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4", "reason": "malware", "confidence_level": 90}
        ]
        response = client.post(
            "/api/fortinet/register",
            json={
                "device_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "dry_run": True,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["dry_run"] is True
        assert data["data"]["registered_count"] == 1

    @patch("core.routes.api.fortinet.management.requests")
    def test_register_success(self, mock_requests, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4", "reason": "malware", "confidence_level": 90}
        ]
        mock_check = MagicMock()
        mock_check.status_code = 200
        mock_addr = MagicMock()
        mock_addr.status_code = 200
        mock_update = MagicMock()
        mock_update.status_code = 200

        mock_requests.get.return_value = mock_check
        mock_requests.post.return_value = mock_addr
        mock_requests.put.return_value = mock_update

        response = client.post(
            "/api/fortinet/register",
            json={"device_ip": "10.0.0.1", "username": "admin", "password": "pass"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["registered_count"] == 1
        assert data["data"]["dry_run"] is False

    @patch("core.routes.api.fortinet.management.requests")
    def test_register_creates_group_on_404(self, mock_requests, client, app):
        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4", "reason": "malware", "confidence_level": 90}
        ]
        mock_check = MagicMock()
        mock_check.status_code = 404
        mock_create = MagicMock()
        mock_create.status_code = 201
        mock_addr = MagicMock()
        mock_addr.status_code = 200
        mock_update = MagicMock()
        mock_update.status_code = 200

        mock_requests.get.return_value = mock_check
        mock_requests.post.side_effect = [mock_create, mock_addr]
        mock_requests.put.return_value = mock_update

        response = client.post(
            "/api/fortinet/register",
            json={"device_ip": "10.0.0.1", "username": "admin", "password": "pass"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert mock_requests.post.call_count == 2

    @patch("core.routes.api.fortinet.management.requests")
    def test_register_connection_error(self, mock_requests, client, app):
        import requests as real_requests

        app.extensions["db_service"].query.return_value = [
            {"ip_address": "1.2.3.4", "reason": "malware", "confidence_level": 90}
        ]
        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("timeout")
        mock_requests.exceptions = real_requests.exceptions

        response = client.post(
            "/api/fortinet/register",
            json={"device_ip": "10.0.0.1", "username": "admin", "password": "pass"},
            content_type="application/json",
        )
        assert response.status_code == 500

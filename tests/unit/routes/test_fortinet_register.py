"""
Tests for fortinet_register.py — /api/fortinet/register
Uses its own blueprint: fortinet_register_bp.
"""

from unittest.mock import MagicMock, patch
from flask import Flask, g
import json


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.fortinet_register import fortinet_register_bp

    app.register_blueprint(fortinet_register_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app


class TestFortinetRegister:
    """POST /api/fortinet/register"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_missing_required_fields(self):
        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_missing_password(self):
        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps({"device_ip": "1.2.3.4", "username": "admin"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_dry_run_success(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            {"ip_address": "10.0.0.1", "reason": "malware", "confidence_level": 90},
            {"ip_address": "10.0.0.2", "reason": "phishing", "confidence_level": 80},
        ]
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps(
                {
                    "device_ip": "192.168.1.1",
                    "username": "admin",
                    "password": "pass",
                    "dry_run": True,
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["dry_run"] is True
        assert data["data"]["registered_count"] == 2

    def test_dry_run_empty_list(self):
        mock_db = MagicMock()
        mock_db.query.return_value = []
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps(
                {
                    "device_ip": "192.168.1.1",
                    "username": "admin",
                    "password": "pass",
                    "dry_run": True,
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["registered_count"] == 0

    def test_dry_run_with_vdom_and_group(self):
        mock_db = MagicMock()
        mock_db.query.return_value = [
            {"ip_address": "10.0.0.1", "reason": None, "confidence_level": 50},
        ]
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps(
                {
                    "device_ip": "10.0.0.1",
                    "username": "admin",
                    "password": "pass",
                    "vdom": "custom_vdom",
                    "address_group": "my_group",
                    "dry_run": True,
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["vdom"] == "custom_vdom"
        assert data["data"]["address_group"] == "my_group"

    @patch("core.routes.api.fortinet_register.requests")
    def test_real_register_connection_error(self, mock_requests):
        """When FortiGate API is unreachable, returns 500."""
        import requests as real_requests

        mock_requests.get.side_effect = real_requests.exceptions.ConnectionError("unreachable")
        mock_requests.exceptions = real_requests.exceptions

        mock_db = MagicMock()
        mock_db.query.return_value = [
            {"ip_address": "10.0.0.1", "reason": "test", "confidence_level": 90},
        ]
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps(
                {
                    "device_ip": "192.168.1.1",
                    "username": "admin",
                    "password": "pass",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 500

    def test_db_query_error(self):
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB error")
        self.app.extensions["db_service"] = mock_db

        resp = self.client.post(
            "/api/fortinet/register",
            data=json.dumps(
                {
                    "device_ip": "192.168.1.1",
                    "username": "admin",
                    "password": "pass",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 500

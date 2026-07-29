"""Tests for app/core/routes/proxy_routes.py — API proxy forwarding to backend and collector."""

from unittest.mock import MagicMock, patch

import requests as real_requests
from flask import Flask
from flask.testing import FlaskClient


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    from core.routes.proxy_routes import proxy_bp

    app.register_blueprint(proxy_bp)
    return app


class TestForwardToBackend:
    """Tests for the forward_to_backend helper via proxy endpoints."""

    app: Flask = create_app()
    client: FlaskClient = app.test_client()

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_collection_status_get(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "status": "healthy"}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/status")

        assert resp.status_code == 200
        mock_requests.get.assert_called_once()
        assert mock_requests.get.call_args.kwargs["verify"] == "/run/blacklist/ca.crt"

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_credentials_get(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"username": "user1"}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/credentials/regtech")

        assert resp.status_code == 200
        call_url = mock_requests.get.call_args[0][0]
        assert "/collection/credentials/regtech" in call_url

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_credentials_put(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.put.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.put(
                "/api/proxy/collection/credentials/regtech",
                json={"username": "admin", "password": "pass"},
            )

        assert resp.status_code == 200
        mock_requests.put.assert_called_once()

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_test_credentials(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post("/api/proxy/collection/credentials/regtech/test", json={})

        assert resp.status_code == 200
        call_url = mock_requests.post.call_args[0][0]
        assert "/collection/credentials/regtech/test" in call_url

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_history(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"history": []}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/history")

        assert resp.status_code == 200

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_statistics(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"total": 42}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/statistics")

        assert resp.status_code == 200

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_health(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"healthy": True}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/health")

        assert resp.status_code == 200

    @patch("core.routes.proxy_routes.requests.get")
    def test_proxy_connection_error_returns_503(self, mock_get):
        mock_get.side_effect = real_requests.exceptions.ConnectionError("refused")

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/status")

        assert resp.status_code == 503
        data = resp.get_json()
        assert data["success"] is False
        assert "unavailable" in data["error"].lower()

    @patch("core.routes.proxy_routes.requests.get")
    def test_proxy_generic_exception_returns_500(self, mock_get):
        mock_get.side_effect = RuntimeError("boom")

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/status")

        assert resp.status_code == 500
        data = resp.get_json()
        assert data["success"] is False

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_non_json_response(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "plain text body"
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/status")

        assert resp.status_code == 200

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_backend_error_status_forwarded(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": "not found"}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get("/api/proxy/collection/status")

        assert resp.status_code == 404

    @patch("core.routes.proxy_routes.requests")
    def test_proxy_forwards_authorization_header(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.get.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.get(
                "/api/proxy/collection/credentials/regtech",
                headers={"Authorization": "Bearer operator-token"},
            )

        assert resp.status_code == 200
        assert mock_requests.get.call_args.kwargs["headers"]["Authorization"] == "Bearer operator-token"


class TestTriggerProxy:
    """POST /api/proxy/collection/trigger/<source> — forwards to collector service."""

    app: Flask = create_app()
    client: FlaskClient = app.test_client()

    def setup_method(self):
        self.app = create_app()
        self.client = self.app.test_client()

    @patch("core.routes.proxy_routes.requests")
    def test_trigger_success(self, mock_requests, monkeypatch):
        monkeypatch.setenv("COLLECTOR_COLLECTION_TIMEOUT", "480")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        mock_requests.post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post("/api/proxy/collection/trigger/regtech", json={})

        assert resp.status_code == 200
        sent_json = mock_requests.post.call_args[1].get("json") or mock_requests.post.call_args.kwargs.get("json")
        assert sent_json["source"] == "regtech"
        assert mock_requests.post.call_args.kwargs["verify"] == "/run/blacklist/ca.crt"
        assert mock_requests.post.call_args.kwargs["timeout"] == 480

    @patch("core.routes.proxy_routes.requests.post")
    def test_trigger_collector_unavailable(self, mock_post):
        mock_post.side_effect = real_requests.exceptions.ConnectionError("refused")

        with self.app.app_context():
            resp = self.client.post("/api/proxy/collection/trigger/regtech", json={})

        assert resp.status_code == 503
        data = resp.get_json()
        assert "unavailable" in data["error"].lower()

    @patch("core.routes.proxy_routes.requests.post")
    def test_trigger_generic_error(self, mock_post):
        mock_post.side_effect = RuntimeError("unexpected")

        with self.app.app_context():
            resp = self.client.post("/api/proxy/collection/trigger/regtech", json={})

        assert resp.status_code == 500

    @patch("core.routes.proxy_routes.requests")
    def test_trigger_non_json_collector_response(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "OK"
        mock_requests.post.return_value = mock_resp

        with self.app.app_context():
            resp = self.client.post("/api/proxy/collection/trigger/regtech", json={})

        assert resp.status_code == 200

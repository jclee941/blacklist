"""
Tests for core_api.py — /api/docs, /api/health
These endpoints are attached directly to api_bp.
"""

from unittest.mock import MagicMock
from flask import Flask, g
from flask.testing import FlaskClient


class FlaskRouteTest:
    @property
    def app(self) -> Flask:
        return self.__dict__["app"]

    @app.setter
    def app(self, value: Flask) -> None:
        self.__dict__["app"] = value

    @property
    def client(self) -> FlaskClient:
        return self.__dict__["client"]

    @client.setter
    def client(self, value: FlaskClient) -> None:
        self.__dict__["client"] = value


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api import api_bp

    app.register_blueprint(api_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app


class TestApiDocs(FlaskRouteTest):
    """GET /api/docs"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_docs_returns_200(self):
        resp = self.client.get("/api/docs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["message"] == "API Documentation"

    def test_docs_contains_endpoints(self):
        resp = self.client.get("/api/docs")
        data = resp.get_json()
        endpoints = data["data"]["api_endpoints"]
        assert "health" in endpoints
        assert "blacklist" in endpoints
        assert "collection" in endpoints

    def test_docs_has_request_id(self):
        resp = self.client.get("/api/docs")
        data = resp.get_json()
        assert data["request_id"] == "test-request-id"

    def test_docs_has_timestamp(self):
        resp = self.client.get("/api/docs")
        data = resp.get_json()
        assert "timestamp" in data


class TestServiceHealth(FlaskRouteTest):
    """GET /api/health"""

    def setup_method(self):
        self.app = _create_app()
        self.client = self.app.test_client()

    def test_health_healthy(self):
        mock_svc = MagicMock()
        mock_svc.get_system_stats.return_value = {"total_ips": 500, "active_ips": 400}
        self.app.extensions["blacklist_service"] = mock_svc

        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert set(data) == {"status", "timestamp"}

    def test_health_unhealthy_on_exception(self):
        """Health endpoint always returns 200 with unhealthy status on error."""
        mock_svc = MagicMock()
        mock_svc.get_system_stats.side_effect = Exception("DB down")
        self.app.extensions["blacklist_service"] = mock_svc

        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "unhealthy"
        assert set(data) == {"status", "timestamp"}
        assert "DB down" not in resp.get_data(as_text=True)

    def test_health_missing_service(self):
        """When blacklist_service not in extensions, returns unhealthy."""
        # Do NOT set extensions["blacklist_service"]
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "unhealthy"
        assert set(data) == {"status", "timestamp"}

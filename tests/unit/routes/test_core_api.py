"""
Tests for core_api.py — /api/docs, /api/health
These endpoints are attached directly to api_bp.
"""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, g


def _create_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api_routes import api_bp
    import core.routes.api.core_api  # triggers @api_bp.route decorators

    app.register_blueprint(api_bp)

    from core.errors.handlers import register_error_handlers

    register_error_handlers(app)

    @app.before_request
    def _set_request_id():
        g.request_id = "test-request-id"

    return app


class TestApiDocs:
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


class TestServiceHealth:
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
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert data["data"]["total_ips"] == 500
        assert data["data"]["active_ips"] == 400
        assert data["data"]["database_connected"] is True

    def test_health_unhealthy_on_exception(self):
        """Health endpoint always returns 200 with unhealthy status on error."""
        mock_svc = MagicMock()
        mock_svc.get_system_stats.side_effect = Exception("DB down")
        self.app.extensions["blacklist_service"] = mock_svc

        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "unhealthy"
        assert data["data"]["database_connected"] is False
        assert "DB down" in data["data"]["error"]

    def test_health_missing_service(self):
        """When blacklist_service not in extensions, returns unhealthy."""
        # Do NOT set extensions["blacklist_service"]
        resp = self.client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["status"] == "unhealthy"

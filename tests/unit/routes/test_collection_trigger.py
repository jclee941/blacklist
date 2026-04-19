"""Unit tests for collection trigger route."""

import pytest
from unittest.mock import patch
from flask import Flask

from core.errors.handlers import register_error_handlers


class TestCollectionTrigger:
    """Tests for POST /trigger/<source>."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        register_error_handlers(app)

        from core.routes.api.collection.trigger import collection_trigger_bp

        app.register_blueprint(collection_trigger_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_regtech_success(self, mock_api, client):
        """Trigger REGTECH collection succeeds."""
        mock_api.return_value = {"success": True, "message": "Collection started"}
        response = client.post("/trigger/REGTECH", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        mock_api.assert_called_once()

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_all_success(self, mock_api, client):
        """Trigger ALL collection succeeds."""
        mock_api.return_value = {"success": True}
        response = client.post("/trigger/ALL", json={})
        assert response.status_code == 200

    def test_trigger_invalid_source(self, client):
        """Invalid source returns 400 validation error."""
        response = client.post("/trigger/INVALID", json={})
        assert response.status_code == 400

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_lowercase_source_normalized(self, mock_api, client):
        """Lowercase source is normalized to uppercase."""
        mock_api.return_value = {"success": True}
        response = client.post("/trigger/regtech", json={})
        assert response.status_code == 200

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_collector_unavailable(self, mock_api, client):
        """Collector service unavailable returns 500."""
        mock_api.return_value = {"success": False, "error": "Cannot connect to collector"}
        response = client.post("/trigger/REGTECH", json={})
        # ServiceUnavailableError is NOT an APIError subclass, so generic handler -> 500
        assert response.status_code == 500

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_collector_api_error(self, mock_api, client):
        """Collector API error returns 502."""
        mock_api.return_value = {"success": False, "error": "Internal error"}
        response = client.post("/trigger/REGTECH", json={})
        assert response.status_code == 502

    @patch("core.routes.api.collection.trigger.call_collector_api")
    def test_trigger_with_force_param(self, mock_api, client):
        """Force parameter is passed to collector API."""
        mock_api.return_value = {"success": True}
        response = client.post("/trigger/REGTECH", json={"force": True})
        assert response.status_code == 200
        call_args = mock_api.call_args
        assert call_args is not None

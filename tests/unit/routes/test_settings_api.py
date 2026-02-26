"""Unit tests for settings API routes."""

import pytest
from unittest.mock import Mock
from flask import Flask


class TestSettingsGet:
    """Tests for GET /settings endpoints."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.before_request
        def set_request_id():
            from flask import g

            g.request_id = "test-req-id"

        from core.routes.api.settings_api import settings_api_bp

        app.register_blueprint(settings_api_bp)

        mock_settings = Mock()
        app.extensions["settings_service"] = mock_settings
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_get_all_settings(self, client, app):
        """GET /settings returns all settings."""
        app.extensions["settings_service"].get_all_settings.return_value = [
            {"key": "site_name", "value": "Test"},
            {"key": "debug", "value": "false"},
        ]
        response = client.get("/settings")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_get_settings_with_category(self, client, app):
        """GET /settings?category=general filters by category."""
        app.extensions["settings_service"].get_all_settings.return_value = []
        response = client.get("/settings?category=general")
        assert response.status_code == 200

    def test_get_setting_by_key(self, client, app):
        """GET /settings/<key> returns single setting."""
        app.extensions["settings_service"].get_setting.return_value = "test-value"
        response = client.get("/settings/site_name")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["value"] == "test-value"

    def test_get_setting_not_found(self, client, app):
        """GET /settings/<key> returns 404 for missing key."""
        app.extensions["settings_service"].get_setting.return_value = None
        response = client.get("/settings/nonexistent")
        assert response.status_code == 404

    def test_get_grouped_settings(self, client, app):
        """GET /settings/grouped returns categorized settings."""
        app.extensions["settings_service"].get_settings_by_category.return_value = {
            "general": [{"key": "site_name", "value": "Test"}]
        }
        response = client.get("/settings/grouped")
        assert response.status_code == 200


class TestSettingsModify:
    """Tests for PUT/POST/DELETE /settings endpoints."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True

        @app.before_request
        def set_request_id():
            from flask import g

            g.request_id = "test-req-id"

        from core.routes.api.settings_api import settings_api_bp

        app.register_blueprint(settings_api_bp)
        app.extensions["settings_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_update_setting(self, client, app):
        """PUT /settings/<key> updates value."""
        app.extensions["settings_service"].set_setting.return_value = True
        response = client.put("/settings/site_name", json={"value": "New Name"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_update_setting_missing_value(self, client, app):
        """PUT /settings/<key> without value returns 400."""
        response = client.put("/settings/site_name", json={})
        assert response.status_code == 400

    def test_create_setting(self, client, app):
        """POST /settings creates new setting."""
        app.extensions["settings_service"].create_setting.return_value = True
        response = client.post(
            "/settings",
            json={
                "key": "new_key",
                "value": "new_value",
                "type": "string",
            },
        )
        assert response.status_code == 201

    def test_create_setting_missing_required(self, client, app):
        """POST /settings without required fields returns 400."""
        response = client.post("/settings", json={"key": "only_key"})
        assert response.status_code == 400

    def test_delete_setting(self, client, app):
        """DELETE /settings/<key> removes setting."""
        app.extensions["settings_service"].delete_setting.return_value = True
        response = client.delete("/settings/old_key")
        assert response.status_code == 200

    def test_delete_setting_not_found(self, client, app):
        """DELETE /settings/<key> returns 404 for missing key."""
        app.extensions["settings_service"].delete_setting.return_value = False
        response = client.delete("/settings/nonexistent")
        assert response.status_code == 404

    def test_batch_update(self, client, app):
        """PUT /settings/batch updates multiple settings."""
        app.extensions["settings_service"].set_setting.return_value = True
        response = client.put(
            "/settings/batch",
            json={
                "settings": [
                    {"key": "k1", "value": "v1"},
                    {"key": "k2", "value": "v2"},
                ]
            },
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_batch_update_missing_settings(self, client, app):
        """PUT /settings/batch without settings list returns 400."""
        response = client.put("/settings/batch", json={})
        assert response.status_code == 400

    def test_service_exception_returns_500(self, client, app):
        """Service exception returns 500 error."""
        app.extensions["settings_service"].get_all_settings.side_effect = Exception("DB error")
        response = client.get("/settings")
        assert response.status_code == 500

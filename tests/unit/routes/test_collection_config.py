import pytest
from unittest.mock import Mock, call
from flask import Flask, g

from core.errors.handlers import register_error_handlers


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.collection.config import collection_config_bp

    app.register_blueprint(collection_config_bp, url_prefix="/api")
    register_error_handlers(app)

    app.extensions["settings_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


class TestCollectionConfig:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_update_collection_config_success_all_keys_updated(self, client, app):
        app.extensions["settings_service"].set_setting.return_value = True

        payload = {
            "interval": 3600,
            "enabled": True,
            "max_retries": 5,
        }
        response = client.post("/api/collection/config/update", json=payload)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert sorted(data["data"]["updated"]) == ["enabled", "interval", "max_retries"]
        assert data["data"]["failed"] == []
        assert data["request_id"] == "test-request-id"
        assert data["timestamp"]

    def test_update_collection_config_success_calls_prefixed_keys(self, client, app):
        app.extensions["settings_service"].set_setting.return_value = True

        payload = {"interval": 3600, "enabled": False}
        response = client.post("/api/collection/config/update", json=payload)

        assert response.status_code == 200
        app.extensions["settings_service"].set_setting.assert_has_calls(
            [
                call("collection_interval", 3600),
                call("collection_enabled", False),
            ],
            any_order=True,
        )

    def test_update_collection_config_empty_body_returns_bad_request(self, client):
        response = client.post("/api/collection/config/update", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert data["title"] == "BAD_REQUEST"
        assert data["detail"] == "No configuration data provided"
        assert data["parameter"] == "body"

    def test_update_collection_config_partial_failure_returns_500(self, client, app):
        def side_effect(key, _value):
            return key == "collection_interval"

        app.extensions["settings_service"].set_setting.side_effect = side_effect

        response = client.post("/api/collection/config/update", json={"interval": 3600, "enabled": True})

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_update_collection_config_total_failure_returns_500(self, client, app):
        app.extensions["settings_service"].set_setting.return_value = False

        response = client.post("/api/collection/config/update", json={"interval": 3600})

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_update_collection_config_service_exception_returns_500(self, client, app):
        app.extensions["settings_service"].set_setting.side_effect = RuntimeError("service down")

        response = client.post("/api/collection/config/update", json={"interval": 3600})

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_update_collection_config_missing_service_returns_500(self, client, app):
        del app.extensions["settings_service"]

        response = client.post("/api/collection/config/update", json={"interval": 3600})

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

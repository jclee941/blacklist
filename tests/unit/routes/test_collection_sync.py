import pytest
from unittest.mock import Mock
from flask import Flask, g

from core.errors.handlers import register_error_handlers


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    from core.routes.api.collection.sync import collection_sync_bp

    app.register_blueprint(collection_sync_bp, url_prefix="/api")
    register_error_handlers(app)

    app.extensions["blacklist_service"] = Mock()
    app.extensions["collection_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


class TestCollectionSync:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_sync_with_collector_success(self, client, app):
        app.extensions["blacklist_service"].sync_with_collector.return_value = {"synced": True, "items": 42}

        response = client.get("/api/sync/collector")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == {"synced": True, "items": 42}
        assert data["request_id"] == "test-request-id"
        assert data["timestamp"]

    def test_sync_with_collector_service_exception_returns_500(self, client, app):
        app.extensions["blacklist_service"].sync_with_collector.side_effect = RuntimeError("sync failed")

        response = client.get("/api/sync/collector")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_sync_with_collector_missing_service_returns_500(self, client, app):
        del app.extensions["blacklist_service"]

        response = client.get("/api/sync/collector")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_force_data_refresh_success(self, client, app):
        app.extensions["collection_service"].force_refresh.return_value = {"refreshed": True}

        response = client.post("/api/data/refresh")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"] == {"refreshed": True}
        assert data["request_id"] == "test-request-id"
        assert data["timestamp"]

    def test_force_data_refresh_service_exception_returns_500(self, client, app):
        app.extensions["collection_service"].force_refresh.side_effect = RuntimeError("refresh failed")

        response = client.post("/api/data/refresh")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_force_data_refresh_missing_service_returns_500(self, client, app):
        del app.extensions["collection_service"]

        response = client.post("/api/data/refresh")

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"

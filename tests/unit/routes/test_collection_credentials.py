from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from flask import Flask, g

from core.errors.handlers import register_error_handlers


def make_app():
    """Create test app with credentials blueprint"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_error_handlers(app)
    from core.routes.api.collection.credentials import collection_credentials_bp

    app.register_blueprint(collection_credentials_bp, url_prefix="/api/collection")
    app.extensions["db_service"] = Mock()
    app.extensions["secure_credential_service"] = Mock()

    @app.before_request
    def set_request_id():
        g.request_id = "test-request-id"

    return app


class TestListCredentials:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_list_credentials_success(self, client, app):
        """GET /api/collection/credentials returns credential sources"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.return_value = {"enabled": True}

        response = client.get("/api/collection/credentials")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["data"][0]["source"] == "REGTECH"
        assert data["data"][0]["configured"] is True
        assert data["data"][0]["enabled"] is True

    def test_list_credentials_includes_cloudflare(self, client, app):
        """GET /api/collection/credentials includes CLOUDFLARE source"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.side_effect = lambda source: {"enabled": source == "CLOUDFLARE"}

        response = client.get("/api/collection/credentials")

        assert response.status_code == 200
        data = response.get_json()
        assert [item["source"] for item in data["data"]] == ["REGTECH", "CLOUDFLARE"]
        assert data["data"][1]["configured"] is True
        assert data["data"][1]["enabled"] is True

    def test_list_credentials_service_error(self, client, app):
        """GET /api/collection/credentials with service error returns graceful result"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.side_effect = Exception("Service error")

        response = client.get("/api/collection/credentials")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert all(s["configured"] is False for s in data["data"])


class TestManageCredentials:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_get_credentials_success(self, client, app):
        """GET /api/collection/credentials/regtech returns masked credentials"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.return_value = {
            "service_name": "REGTECH",
            "username": "admin",
            "password": "secret123",
            "enabled": True,
            "collection_interval": 86400,
            "last_collection": datetime(2026, 1, 1),
        }

        response = client.get("/api/collection/credentials/regtech")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["username"] == "admin"
        assert data["data"]["password"] == "***masked***"
        assert data["data"]["configured"] is True

    def test_get_credentials_invalid_source(self, client):
        """GET /api/collection/credentials/invalid returns 400"""
        response = client.get("/api/collection/credentials/invalid")
        assert response.status_code == 400

    def test_get_credentials_not_configured(self, client, app):
        """GET /api/collection/credentials/regtech when not configured returns 200 with defaults"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.return_value = None

        response = client.get("/api/collection/credentials/regtech")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["service_name"] == "REGTECH"
        assert data["data"]["username"] == ""
        assert data["data"]["enabled"] is False
        assert data["data"]["connection_status"] == "unknown"
        assert data["data"]["configured"] is False

    def test_put_credentials_success(self, client, app):
        """PUT /api/collection/credentials/regtech updates credentials"""
        svc = app.extensions["secure_credential_service"]
        svc.save_credentials.return_value = True

        with patch("core.routes.api.collection.credentials.call_collector_api") as mock_api:
            mock_api.return_value = {"success": True}

            response = client.put(
                "/api/collection/credentials/regtech",
                json={"username": "admin", "password": "newpass"},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

    def test_put_credentials_missing_username(self, client):
        """PUT /api/collection/credentials/regtech without username returns 400"""
        response = client.put(
            "/api/collection/credentials/regtech",
            json={"password": "secret"},
        )
        assert response.status_code == 400

    def test_put_credentials_cloudflare(self, client, app):
        """PUT /api/collection/credentials/cloudflare saves config fields"""
        svc = app.extensions["secure_credential_service"]
        svc.save_credentials.return_value = True

        with patch("core.routes.api.collection.credentials.call_collector_api") as mock_api:
            mock_api.return_value = {"success": True}

            response = client.put(
                "/api/collection/credentials/cloudflare",
                json={
                    "password": "cf-token",
                    "account_id": "acc-123",
                    "list_id": "list-456",
                    "enabled": True,
                },
            )

        assert response.status_code == 200
        svc.save_credentials.assert_called_once_with(
            service_name="CLOUDFLARE",
            username="cloudflare-api",
            password="cf-token",
            config={"account_id": "acc-123", "list_id": "list-456"},
            enabled=True,
            collection_interval=86400,
        )

    def test_put_credentials_no_body(self, client):
        """PUT /api/collection/credentials/regtech with no body returns 400"""
        response = client.put(
            "/api/collection/credentials/regtech",
            content_type="application/json",
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "payload",
        [
            [],
            {"username": ["admin"], "password": "secret"},
            {"username": "admin", "password": ["secret"]},
            {"username": "admin", "password": "secret", "enabled": "true"},
            {"username": "admin", "password": "secret", "collection_interval": "monthly"},
        ],
    )
    def test_put_credentials_rejects_invalid_payload_types(self, client, payload):
        response = client.put(
            "/api/collection/credentials/regtech",
            json=payload,
        )

        assert response.status_code == 400

    def test_put_cloudflare_rejects_non_string_config(self, client):
        response = client.put(
            "/api/collection/credentials/cloudflare",
            json={
                "password": "cf-token",
                "account_id": ["account"],
                "list_id": "list-456",
            },
        )

        assert response.status_code == 400


class TestTestCredentials:
    @pytest.fixture
    def app(self):
        return make_app()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @patch("core.routes.api.collection.credentials.call_collector_api")
    def test_test_credentials_success(self, mock_api, client):
        """POST /api/collection/credentials/regtech/test with successful auth"""
        mock_api.return_value = {"success": True}

        response = client.post("/api/collection/credentials/regtech/test")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["status"] == "connected"

    @patch("core.routes.api.collection.credentials.call_collector_api")
    def test_test_credentials_failed(self, mock_api, client):
        """POST /api/collection/credentials/regtech/test with auth failure"""
        mock_api.return_value = {"success": False, "error": "Invalid password"}

        response = client.post("/api/collection/credentials/regtech/test")
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["status"] == "failed"

    @patch("core.routes.api.collection.credentials.call_collector_api")
    def test_test_credentials_locked(self, mock_api, client):
        """POST /api/collection/credentials/regtech/test with locked account.
        Locked account errors are returned as ForbiddenError.
        """
        mock_api.return_value = {
            "success": False,
            "error": "Account is locked",
            "error_code": "user.is.locked",
        }

        response = client.post("/api/collection/credentials/regtech/test")
        assert response.status_code == 403

    def test_test_credentials_invalid_source(self, client):
        """POST /api/collection/credentials/invalid/test returns 400"""
        response = client.post("/api/collection/credentials/invalid/test")
        assert response.status_code == 400

    @patch("core.routes.api.collection.credentials.requests.get")
    def test_test_cloudflare_success(self, mock_get, client, app):
        """POST /api/collection/credentials/cloudflare/test returns connected on valid API response"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.return_value = {
            "service_name": "CLOUDFLARE",
            "username": "cloudflare-api",
            "password": "cf-token",
            "config": {"account_id": "acc-123", "list_id": "list-456"},
            "enabled": True,
        }
        mock_get.return_value.json.return_value = {
            "success": True,
            "result": {"name": "Blacklist", "num_items": 42},
        }

        response = client.post("/api/collection/credentials/cloudflare/test")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["status"] == "connected"
        assert data["data"]["message"] == "Connected. List: Blacklist, Items: 42"

    @patch("core.routes.api.collection.credentials.requests.get")
    def test_test_cloudflare_invalid_token(self, mock_get, client, app):
        """POST /api/collection/credentials/cloudflare/test returns failure on API error"""
        svc = app.extensions["secure_credential_service"]
        svc.get_credentials.return_value = {
            "service_name": "CLOUDFLARE",
            "username": "cloudflare-api",
            "password": "bad-token",
            "config": {"account_id": "acc-123", "list_id": "list-456"},
            "enabled": True,
        }
        mock_get.return_value.json.return_value = {
            "success": False,
            "errors": [{"message": "Authentication error"}],
        }

        response = client.post("/api/collection/credentials/cloudflare/test")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is False
        assert data["data"]["status"] == "failed"
        assert data["data"]["message"] == "API error: Authentication error"

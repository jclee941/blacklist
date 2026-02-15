"""Unit tests for auth API routes."""

import pytest
from unittest.mock import Mock, patch
from flask import Flask


class TestAuthLogin:
    """Tests for POST /api/auth/login."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        from core.routes.api.auth_routes import auth_bp

        app.register_blueprint(auth_bp)
        app.extensions["jwt_service"] = Mock()
        app.extensions["settings_service"] = Mock()
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_login_success(self, client, app):
        """Valid credentials return JWT token."""
        app.extensions["settings_service"].get_setting.side_effect = lambda key, default=None: {
            "admin_username": "admin",
            "admin_password": "secret123",
        }.get(key, default)
        app.extensions["jwt_service"].encode_token.return_value = "test-jwt-token"
        response = client.post("/api/auth/login", json={"username": "admin", "password": "secret123"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["token"] == "test-jwt-token"
        assert data["expires_in"] == 28800
        assert data["user"]["role"] == "admin"

    def test_login_missing_credentials(self, client, app):
        """Missing username/password returns 400."""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "AUTH_MISSING_CREDENTIALS"

    def test_login_missing_body(self, client, app):
        """No JSON body returns 400."""
        response = client.post("/api/auth/login", content_type="application/json", data="{}")
        assert response.status_code == 400

    def test_login_invalid_credentials(self, client, app):
        """Wrong password returns 401."""
        app.extensions["settings_service"].get_setting.side_effect = lambda key, default=None: {
            "admin_username": "admin",
            "admin_password": "correct",
        }.get(key, default)
        response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_login_invalid_username(self, client, app):
        """Wrong username returns 401."""
        app.extensions["settings_service"].get_setting.side_effect = lambda key, default=None: {
            "admin_username": "admin",
            "admin_password": "pass",
        }.get(key, default)
        response = client.post("/api/auth/login", json={"username": "hacker", "password": "pass"})
        assert response.status_code == 401

    def test_login_settings_service_fallback_to_env(self, client, app):
        """Falls back to env vars when settings_service throws."""
        app.extensions["settings_service"].get_setting.side_effect = Exception("DB down")
        app.extensions["jwt_service"].encode_token.return_value = "fallback-token"
        with patch.dict("os.environ", {"ADMIN_USERNAME": "envuser", "ADMIN_PASSWORD": "envpass"}):
            response = client.post("/api/auth/login", json={"username": "envuser", "password": "envpass"})
            assert response.status_code == 200

    def test_login_no_settings_service(self, client, app):
        """Without settings_service, returns 500 AUTH_SERVICE_UNAVAILABLE."""
        # Source code (auth_routes.py:46-56): when settings_service is None,
        # returns 500 with code AUTH_SERVICE_UNAVAILABLE
        del app.extensions["settings_service"]
        response = client.post("/api/auth/login", json={"username": "admin", "password": "pass"})
        assert response.status_code == 500
        data = response.get_json()
        assert data["code"] == "AUTH_SERVICE_UNAVAILABLE"


class TestAuthMe:
    """Tests for GET /api/auth/me."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        from core.routes.api.auth_routes import auth_bp

        app.register_blueprint(auth_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_me_returns_current_user(self, client, app):
        """Returns g.current_user data."""

        @app.before_request
        def set_user():
            from flask import g

            g.current_user = {"user_id": "admin", "role": "admin"}

        response = client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.get_json()
        assert data["user_id"] == "admin"
        assert data["role"] == "admin"


class TestAuthVerify:
    """Tests for GET /api/auth/verify."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        from core.routes.api.auth_routes import auth_bp

        app.register_blueprint(auth_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_verify_returns_valid(self, client, app):
        """Returns valid=True with user info."""

        @app.before_request
        def set_user():
            from flask import g

            g.current_user = {"user_id": "admin", "role": "admin"}

        response = client.get("/api/auth/verify")
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True

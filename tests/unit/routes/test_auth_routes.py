import pytest
from unittest.mock import Mock, patch
from flask import Flask


class TestAuthLogin:
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

    def test_login_missing_credentials(self, client):
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "AUTH_MISSING_CREDENTIALS"

    def test_login_invalid_credentials(self, client, app):
        app.extensions["settings_service"].get_setting.side_effect = lambda key, default=None: {
            "admin_username": "admin",
            "admin_password": "correct",
        }.get(key, default)
        response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_login_invalid_username(self, client, app):
        app.extensions["settings_service"].get_setting.side_effect = lambda key, default=None: {
            "admin_username": "admin",
            "admin_password": "pass",
        }.get(key, default)
        response = client.post("/api/auth/login", json={"username": "hacker", "password": "pass"})
        assert response.status_code == 401

    def test_login_settings_service_fallback_to_env(self, client, app):
        app.extensions["settings_service"].get_setting.side_effect = Exception("DB down")
        app.extensions["jwt_service"].encode_token.return_value = "fallback-token"
        with patch.dict("os.environ", {"ADMIN_USERNAME": "envuser", "ADMIN_PASSWORD": "envpass"}):
            response = client.post("/api/auth/login", json={"username": "envuser", "password": "envpass"})
            assert response.status_code == 200

    def test_login_uses_env_credentials_when_settings_are_absent(self, client, app):
        app.extensions["settings_service"].get_setting.side_effect = lambda _key, default=None: default
        app.extensions["jwt_service"].encode_token.return_value = "generated-token"

        with patch.dict("os.environ", {"ADMIN_USERNAME": "generated-user", "ADMIN_PASSWORD": "generated-pass"}):
            response = client.post(
                "/api/auth/login",
                json={"username": "generated-user", "password": "generated-pass"},
            )

        assert response.status_code == 200
        assert response.get_json()["token"] == "generated-token"

    def test_login_no_settings_service(self, client, app):
        del app.extensions["settings_service"]
        response = client.post("/api/auth/login", json={"username": "admin", "password": "pass"})
        assert response.status_code == 500
        data = response.get_json()
        assert data["code"] == "AUTH_SERVICE_UNAVAILABLE"


class TestAuthMe:
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
        """Returns the identity carried by the request's bearer token.

        The endpoint used to read g.current_user, populated by a before_request
        hook this application never registers, so it returned 500 in production.
        It now resolves the token itself; the intent of this test is unchanged.
        """
        from core.auth.jwt_service import JWTService

        secret = "test-identity-secret"
        app.config["SECRET_KEY"] = secret
        app.extensions["jwt_service"] = JWTService(secret)
        token = JWTService(secret).encode_token(user_id="admin", role="admin")

        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["sub"] == "admin"
        assert data["role"] == "admin"


class TestAuthVerify:
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
        """Returns valid=True for a genuine bearer token.

        Previously this asserted against a hand-injected g.current_user, which
        production never populated. Verifying the real token keeps the original
        intent and now exercises the path a caller actually takes.
        """
        from core.auth.jwt_service import JWTService

        secret = "test-identity-secret"
        app.config["SECRET_KEY"] = secret
        app.extensions["jwt_service"] = JWTService(secret)
        token = JWTService(secret).encode_token(user_id="admin", role="admin")

        response = client.get(
            "/api/auth/verify", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["user"]["sub"] == "admin"

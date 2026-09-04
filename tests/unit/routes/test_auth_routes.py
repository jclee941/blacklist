import pytest
from unittest.mock import Mock, patch
from flask import Flask

from core.services.auth_state_service import AdminCredentials, AuthStateUnavailableError


class TestAuthLogin:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        app.config["MAX_CONTENT_LENGTH"] = 128
        from core.routes.api.auth_routes import auth_bp

        app.register_blueprint(auth_bp)
        app.extensions["jwt_service"] = Mock()
        app.extensions["settings_service"] = Mock()
        app.extensions["auth_state_service"] = Mock()
        app.extensions["auth_state_service"].get_credentials.return_value = AdminCredentials(
            username="admin", password_hash="secret123", session_version=1
        )
        app.extensions["auth_security"] = Mock()
        app.extensions["auth_security"].is_login_locked.return_value = False
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_login_success(self, client, app):
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

    def test_login_rejects_oversized_body_before_authentication(self, client, app):
        response = client.post(
            "/api/auth/login",
            data='{"username":"admin","password":"' + ("x" * 200) + '"}',
            content_type="application/json",
        )

        assert response.status_code == 413
        app.extensions["auth_state_service"].get_credentials.assert_not_called()

    def test_login_invalid_credentials(self, client, app):
        app.extensions["auth_state_service"].get_credentials.return_value = AdminCredentials(
            username="admin", password_hash="correct", session_version=1
        )
        response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_login_invalid_username(self, client, app):
        app.extensions["auth_state_service"].get_credentials.return_value = AdminCredentials(
            username="admin", password_hash="pass", session_version=1
        )
        response = client.post("/api/auth/login", json={"username": "hacker", "password": "pass"})
        assert response.status_code == 401

    def test_login_fails_closed_when_auth_database_is_unavailable(self, client, app):
        app.extensions["auth_state_service"].get_credentials.side_effect = AuthStateUnavailableError("credential read")
        with patch.dict("os.environ", {"ADMIN_USERNAME": "envuser", "ADMIN_PASSWORD": "envpass"}):
            response = client.post("/api/auth/login", json={"username": "envuser", "password": "envpass"})
            assert response.status_code == 503

    def test_login_uses_env_credentials_when_settings_are_absent(self, client, app):
        app.extensions["auth_state_service"].get_credentials.return_value = AdminCredentials(
            username="generated-user", password_hash="generated-pass", session_version=1
        )
        app.extensions["jwt_service"].encode_token.return_value = "generated-token"

        with patch.dict("os.environ", {"ADMIN_USERNAME": "generated-user", "ADMIN_PASSWORD": "generated-pass"}):
            response = client.post(
                "/api/auth/login",
                json={"username": "generated-user", "password": "generated-pass"},
            )

        assert response.status_code == 200
        assert response.get_json()["token"] == "generated-token"

    def test_login_no_auth_state_service(self, client, app):
        del app.extensions["auth_state_service"]
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

        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
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

        response = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["valid"] is True
        assert data["user"]["sub"] == "admin"

from __future__ import annotations

import bcrypt
import pytest
from flask import Flask, Response, jsonify


class MemorySecurityStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def incr(self, key: str) -> int:
        value = int(self.values.get(key, "0")) + 1
        self.values[key] = str(value)
        return value

    def increment_with_expiry(self, key: str, seconds: int) -> int:
        value = self.incr(key)
        if value == 1:
            self.expire(key, seconds)
        return value

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            deleted += int(self.values.pop(key, None) is not None)
        return deleted

    def setex(self, key: str, seconds: int, value: str) -> bool:
        self.values[key] = value
        self.expirations[key] = seconds
        return True


class SettingsStub:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self.values.get(key, default)

    def set_setting(self, key: str, value: str, *, encrypt: bool = False) -> bool:
        assert encrypt is False
        self.values[key] = value
        return True

    def create_setting(
        self,
        key: str,
        value: str,
        setting_type: str,
        description: str,
        category: str,
        *,
        encrypt: bool = False,
    ) -> bool:
        assert setting_type == "password"
        assert category == "security"
        assert encrypt is False
        self.values[key] = value
        return True

    def get_credentials(self, default_username: str, default_password: str):
        from core.auth.security import hash_password
        from core.services.auth_state_service import AdminCredentials

        username = self.values.setdefault("admin_username", default_username)
        password_hash = self.values.get("admin_password")
        if password_hash is None:
            password_hash = hash_password(default_password)
            self.values["admin_password"] = password_hash
        self.values.setdefault("admin_session_version", "1")
        return AdminCredentials(
            username=username,
            password_hash=password_hash,
            session_version=int(self.values["admin_session_version"]),
        )

    def current_session_version(self, subject: str) -> int:
        return int(self.values.get("admin_session_version", "0"))

    def upgrade_password_hash(self, expected_password: str, replacement_hash: str) -> bool:
        if self.values.get("admin_password") != expected_password:
            return False
        self.values["admin_password"] = replacement_hash
        return True

    def rotate_password(self, subject: str, current_password: str, new_password: str) -> bool:
        from core.auth.security import hash_password, verify_password

        configured = self.values.get("admin_password", "")
        if not verify_password(current_password, configured)[0]:
            return False
        self.values["admin_password"] = hash_password(new_password)
        version = int(self.values.get("admin_session_version", "0"))
        self.values["admin_session_version"] = str(version + 1)
        return True


def _auth_app(store: MemorySecurityStore, settings: SettingsStub) -> Flask:
    from core.auth.jwt_service import JWTService
    from core.auth.security import AuthSecurity
    from core.routes.api.auth_routes import auth_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(auth_bp)
    app.extensions["auth_security"] = AuthSecurity(store)
    app.extensions["jwt_service"] = JWTService(
        "unit-jwt-secret",
        revocations=app.extensions["auth_security"],
        session_versions=settings,
    )
    app.extensions["settings_service"] = settings
    app.extensions["auth_state_service"] = settings
    return app


def test_direct_client_forwarding_is_ignored() -> None:
    from core.auth.proxy import TrustedProxyMiddleware

    app = Flask(__name__)

    @app.get("/peer")
    def peer() -> Response:
        from flask import request

        return jsonify({"peer": request.remote_addr})

    app.wsgi_app = TrustedProxyMiddleware(app.wsgi_app, ("10.0.0.0/8",))

    response = app.test_client().get(
        "/peer",
        headers={"X-Forwarded-For": "203.0.113.9"},
        environ_base={"REMOTE_ADDR": "198.51.100.7"},
    )

    assert response.get_json() == {"peer": "198.51.100.7"}


def test_trusted_proxy_uses_exactly_one_sanitized_forwarded_hop() -> None:
    from core.auth.proxy import TrustedProxyMiddleware

    app = Flask(__name__)

    @app.get("/peer")
    def peer() -> Response:
        from flask import request

        return jsonify({"peer": request.remote_addr})

    app.wsgi_app = TrustedProxyMiddleware(app.wsgi_app, ("10.0.0.0/8",))

    response = app.test_client().get(
        "/peer",
        headers={"X-Forwarded-For": "192.0.2.66, 203.0.113.9"},
        environ_base={"REMOTE_ADDR": "10.0.0.4"},
    )

    assert response.get_json() == {"peer": "203.0.113.9"}


def test_login_declares_five_per_minute_limit() -> None:
    from core.routes.api.auth_routes import login

    assert getattr(login, "_rate_limit") == "5 per minute"


def test_login_locks_account_after_five_failures() -> None:
    store = MemorySecurityStore()
    password_hash = bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode()
    app = _auth_app(store, SettingsStub({"admin_username": "admin", "admin_password": password_hash}))

    with app.test_client() as client:
        for _ in range(5):
            response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
            assert response.status_code == 401
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "correct-password"},
        )

    assert response.status_code == 429
    assert response.get_json()["code"] == "AUTH_ACCOUNT_LOCKED"


def test_login_failures_lock_the_account_across_source_ips() -> None:
    from core.auth.security import AuthSecurity

    store = MemorySecurityStore()
    security = AuthSecurity(store)
    for index in range(5):
        security.record_login_failure("admin", f"192.0.2.{index + 1}")

    assert security.is_login_locked("admin", "198.51.100.10") is True


def test_login_racing_password_rotation_mints_an_immediately_invalid_token() -> None:
    class RacingSettingsStub(SettingsStub):
        def get_credentials(self, default_username: str, default_password: str):
            credentials = super().get_credentials(default_username, default_password)
            self.values["admin_session_version"] = str(credentials.session_version + 1)
            return credentials

    store = MemorySecurityStore()
    password = "current-password"
    settings = RacingSettingsStub(
        {
            "admin_username": "admin",
            "admin_password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            "admin_session_version": "1",
        }
    )
    app = _auth_app(store, settings)

    with app.test_client() as client:
        login = client.post("/api/auth/login", json={"username": "admin", "password": password})
        assert login.status_code == 200, login.get_json()
        token = login.get_json()["token"]
        verification = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})

    assert verification.status_code == 401


def test_login_persists_hash_when_only_environment_password_exists() -> None:
    class MissingAdminRowSettings(SettingsStub):
        def set_setting(self, key: str, value: str, *, encrypt: bool = False) -> bool:
            return False

    store = MemorySecurityStore()
    settings = MissingAdminRowSettings({})
    app = _auth_app(store, settings)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ADMIN_PASSWORD", "environment-password")
        response = app.test_client().post(
            "/api/auth/login",
            json={"username": "admin", "password": "environment-password"},
        )

    assert response.status_code == 200
    assert bcrypt.checkpw(b"environment-password", settings.values["admin_password"].encode())


def test_login_reports_configured_jwt_expiry() -> None:
    from core.auth.jwt_service import JWTService
    from core.auth.security import AuthSecurity

    store = MemorySecurityStore()
    settings = SettingsStub(
        {
            "admin_username": "admin",
            "admin_password": bcrypt.hashpw(b"configured-password", bcrypt.gensalt()).decode(),
        }
    )
    app = _auth_app(store, settings)
    app.extensions["jwt_service"] = JWTService(
        "unit-jwt-secret",
        revocations=AuthSecurity(store),
        session_versions=settings,
        expiry_hours=2,
    )

    response = app.test_client().post(
        "/api/auth/login",
        json={"username": "admin", "password": "configured-password"},
    )

    assert response.status_code == 200
    assert response.get_json()["expires_in"] == 7200


def test_password_rotation_requires_current_password_and_never_returns_secrets() -> None:
    store = MemorySecurityStore()
    old_password = "current-password"
    new_password = "replacement-password"
    settings = SettingsStub(
        {
            "admin_username": "admin",
            "admin_password": bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode(),
        }
    )
    app = _auth_app(store, settings)
    token = app.extensions["jwt_service"].encode_token("admin", role="admin")

    response = app.test_client().put(
        "/api/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": old_password, "new_password": new_password},
    )

    assert response.status_code == 200
    assert bcrypt.checkpw(new_password.encode(), settings.values["admin_password"].encode())
    assert old_password not in response.get_data(as_text=True)
    assert new_password not in response.get_data(as_text=True)


def test_password_rotation_invalidates_all_existing_tokens() -> None:
    store = MemorySecurityStore()
    old_password = "current-password"
    settings = SettingsStub(
        {
            "admin_username": "admin",
            "admin_password": bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode(),
        }
    )
    app = _auth_app(store, settings)
    jwt_service = app.extensions["jwt_service"]
    first_token = jwt_service.encode_token("admin", role="admin")
    second_token = jwt_service.encode_token("admin", role="admin")

    with app.test_client() as client:
        response = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {first_token}"},
            json={"current_password": old_password, "new_password": "replacement-password"},
        )
        first_verify = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {first_token}"})
        second_verify = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {second_token}"})
        replacement_token = jwt_service.encode_token("admin", role="admin")
        replacement_verify = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {replacement_token}"})

    assert response.status_code == 200
    assert first_verify.status_code == 401
    assert second_verify.status_code == 401
    assert replacement_verify.status_code == 200


def test_logout_revokes_jti_for_subsequent_http_requests() -> None:
    store = MemorySecurityStore()
    settings = SettingsStub({})
    app = _auth_app(store, settings)
    token = app.extensions["jwt_service"].encode_token("admin", role="admin")

    with app.test_client() as client:
        logout_response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        verify_response = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})

    assert logout_response.status_code == 200
    assert verify_response.status_code == 401


def test_non_admin_token_cannot_access_protected_route() -> None:
    from core.auth.jwt_service import JWTService
    from core.auth.middleware import jwt_required_hook
    from core.auth.security import AuthSecurity

    store = MemorySecurityStore()
    app = Flask(__name__)
    app.extensions["auth_security"] = AuthSecurity(store)
    app.extensions["jwt_service"] = JWTService("unit-jwt-secret", revocations=app.extensions["auth_security"])
    app.before_request(jwt_required_hook)

    @app.post("/api/admin/mutate")
    def mutate() -> tuple[dict[str, bool], int]:
        return {"success": True}, 200

    token = app.extensions["jwt_service"].encode_token("viewer", role="user")
    response = app.test_client().post(
        "/api/admin/mutate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["code"] == "AUTH_ADMIN_REQUIRED"


def test_production_rejects_disable_jwt_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.auth.middleware import jwt_required_hook

    app = Flask(__name__)

    @app.get("/api/protected")
    def protected() -> str:
        return "protected"

    monkeypatch.setenv("DISABLE_JWT_AUTH", "true")
    monkeypatch.setenv("FLASK_ENV", "production")
    with app.test_request_context("/api/protected"):
        result = jwt_required_hook()
        assert result is not None
        response, status = result

    assert status == 500
    assert response.get_json()["code"] == "AUTH_BYPASS_FORBIDDEN"


def test_jwt_contains_unique_jti() -> None:
    from core.auth.jwt_service import JWTService

    service = JWTService("unit-jwt-secret")

    first = service.decode_token(service.encode_token("admin", role="admin"))
    second = service.decode_token(service.encode_token("admin", role="admin"))

    assert first["jti"]
    assert second["jti"]
    assert first["jti"] != second["jti"]


def test_fortigate_target_requires_an_explicit_allowed_network() -> None:
    from core.auth.fortigate import FortiGateTargetError, parse_fortigate_target

    with pytest.raises(FortiGateTargetError):
        parse_fortigate_target("10.0.0.1", ())


def test_fortigate_target_rejects_addresses_outside_allowed_networks() -> None:
    from core.auth.fortigate import FortiGateTargetError, parse_fortigate_target

    with pytest.raises(FortiGateTargetError):
        parse_fortigate_target("169.254.169.254", ("10.0.0.0/24",))

    assert parse_fortigate_target("10.0.0.1", ("10.0.0.0/24",)) == "10.0.0.1"

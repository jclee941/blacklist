from pathlib import Path
from unittest.mock import Mock

import pytest
from flask import Flask

from core.auth.jwt_service import JWTService
from core.routes.api.auth_routes import auth_bp


class SettingsServiceStub:
    def get_setting(self, _key: str, default: str | None = None) -> str | None:
        return default

    def set_setting(self, _key: str, _value: str, *, encrypt: bool = False) -> bool:
        assert encrypt is False
        return True


@pytest.fixture
def app() -> Flask:
    application = Flask(__name__)
    application.config["TESTING"] = True
    application.register_blueprint(auth_bp)
    application.extensions["jwt_service"] = JWTService(secret_key="test-auth-bootstrap-secret")
    application.extensions["settings_service"] = SettingsServiceStub()
    application.extensions["auth_security"] = Mock()
    application.extensions["auth_security"].is_login_locked.return_value = False
    return application


@pytest.mark.parametrize("configured_value", [None, "", "   "], ids=["unset", "empty", "whitespace"])
def test_login_rejects_unconfigured_admin_credentials(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    configured_value: str | None,
) -> None:
    if configured_value is None:
        monkeypatch.delenv("ADMIN_USERNAME", raising=False)
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("ADMIN_USERNAME", configured_value)
        monkeypatch.setenv("ADMIN_PASSWORD", configured_value)
    with app.test_client() as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "__SET_ADMIN_USERNAME__", "password": "__SET_ADMIN_PASSWORD__"},
        )

    assert response.status_code == 401
    assert response.get_json()["code"] == "AUTH_INVALID_CREDENTIALS"
    assert "ADMIN_USERNAME and ADMIN_PASSWORD" in caplog.text


def test_sentinel_credentials_are_absent_and_cannot_authenticate(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    app_dir = Path(__file__).parents[3] / "app"

    with app.test_client() as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "__SET_ADMIN_USERNAME__", "password": "__SET_ADMIN_PASSWORD__"},
        )

    application_source = "".join(path.read_text(encoding="utf-8") for path in app_dir.rglob("*.py"))
    assert "__SET_ADMIN_USERNAME__" not in application_source
    assert "__SET_ADMIN_PASSWORD__" not in application_source
    assert response.status_code == 401


def test_login_succeeds_with_configured_admin_credentials(
    app: Flask,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "configured-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "configured-password")
    with app.test_client() as client:
        response = client.post(
            "/api/auth/login",
            json={"username": "configured-admin", "password": "configured-password"},
        )

    assert response.status_code == 200
    assert response.get_json()["token"]

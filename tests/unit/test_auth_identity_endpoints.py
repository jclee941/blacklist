from __future__ import annotations

import pytest
from flask import Flask

from core.auth.jwt_service import JWTService
from core.routes.api.auth_routes import auth_bp


SECRET = "test-secret-key-0123456789abcdef"


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET
    app.extensions["jwt_service"] = JWTService(SECRET)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    return app.test_client()


def bearer(user_id: str = "admin", role: str = "admin") -> dict[str, str]:
    token = JWTService(SECRET).encode_token(user_id=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/auth/verify"])
def test_identity_endpoints_resolve_the_bearer_token(client, path: str) -> None:
    # Given: a caller that logged in and holds a valid token.
    response = client.get(path, headers=bearer())

    # Then: the endpoint reports the identity instead of failing. These routes
    # read g.current_user, which is only populated by a before_request hook that
    # is never registered, so they returned 500 for every caller.
    assert response.status_code == 200, response.get_data(as_text=True)
    assert "admin" in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/auth/verify"])
def test_identity_endpoints_reject_a_missing_token(client, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 401


@pytest.mark.parametrize("path", ["/api/auth/me", "/api/auth/verify"])
def test_identity_endpoints_reject_a_forged_token(client, path: str) -> None:
    forged = JWTService("a-different-signing-key-0123456789").encode_token(user_id="mallory")
    response = client.get(path, headers={"Authorization": f"Bearer {forged}"})
    # A token signed with the wrong key must never authenticate.
    assert response.status_code == 401


def test_verify_reports_validity_explicitly(client) -> None:
    response = client.get("/api/auth/verify", headers=bearer())
    assert response.get_json()["valid"] is True

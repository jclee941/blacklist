import hmac
import os
from typing import Final

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue


CONTROL_ROUTES: Final[frozenset[str]] = frozenset(
    {
        "/logs",
        "/status",
        "/trigger",
        "/api/test-auth/<source>",
        "/api/force-collection/<source>",
    }
)
AUTH_DISABLED_VALUES: Final[frozenset[str]] = frozenset({"true", "1", "yes"})


def require_control_authentication() -> ResponseReturnValue | None:
    route = request.url_rule.rule if request.url_rule else None
    if route not in CONTROL_ROUTES:
        return None

    authentication_disabled = os.getenv("DISABLE_JWT_AUTH", "false").strip().lower() in AUTH_DISABLED_VALUES
    if authentication_disabled:
        return None

    expected_token = os.getenv("COLLECTOR_AUTH_TOKEN", "")
    scheme, separator, supplied_token = request.headers.get("Authorization", "").partition(" ")
    authorized = bool(
        expected_token
        and separator
        and scheme.lower() == "bearer"
        and hmac.compare_digest(supplied_token, expected_token)
    )
    if authorized:
        return None

    return jsonify({"error": "Unauthorized"}), 401


def register_control_auth(app: Flask) -> None:
    _ = app.before_request(require_control_authentication)

from typing import Final, Never

from flask import request

from ....exceptions import BadRequestError
from .credentials import collection_credentials_bp

ALLOWED_INTERVALS: Final = frozenset({"hourly", "daily", "weekly"})


def _reject(field: str, message: str) -> Never:
    raise BadRequestError(message=message, details={"field": field})


@collection_credentials_bp.before_request
def validate_credential_update() -> None:
    if request.method != "PUT":
        return

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        _reject("body", "Request body must be a JSON object")

    username = payload.get("username")
    if username is not None and not isinstance(username, str):
        _reject("username", "Username must be a string")

    password = payload.get("password")
    if password is not None and not isinstance(password, str):
        _reject("password", "Password must be a string")

    enabled = payload.get("enabled", True)
    if not isinstance(enabled, bool):
        _reject("enabled", "Enabled must be a boolean")

    interval = payload.get("collection_interval", "daily")
    if not isinstance(interval, str) or interval not in ALLOWED_INTERVALS:
        _reject("collection_interval", "Collection interval must be hourly, daily, or weekly")

    source = request.view_args.get("source", "").upper() if request.view_args else ""
    if source == "CLOUDFLARE":
        for field in ("account_id", "list_id"):
            value = payload.get(field, "")
            if not isinstance(value, str):
                _reject(field, f"{field} must be a string")

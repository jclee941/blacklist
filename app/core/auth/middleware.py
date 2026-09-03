"""
JWT Authentication Middleware

before_request hook that enforces JWT on all routes by default.
Routes marked with @public decorator are exempt.
"""

import logging
from typing import Any

from flask import current_app, g, jsonify, request

from core.exceptions.auth_exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# Paths that are always public (no blueprint endpoint to decorate)
PUBLIC_PATH_PREFIXES = (
    "/static/",
    "/favicon.ico",
    "/robots.txt",
)


def jwt_required_hook() -> Any | None:
    # Always skip static assets
    if request.path.startswith(PUBLIC_PATH_PREFIXES):
        return None

    # Check if the endpoint function is marked @public
    endpoint_func = current_app.view_functions.get(request.endpoint or "")
    if endpoint_func and getattr(endpoint_func, "_public", False):
        return None

    from core.config import config

    if config.DISABLE_JWT_AUTH:
        if config.FLASK_ENV != "development" and not current_app.testing:
            return _auth_error("AUTH_BYPASS_FORBIDDEN", "Authentication bypass is forbidden in production"), 500
        g.current_user = {"sub": "dev", "role": "admin"}
        return None

    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return _auth_error("AUTH_TOKEN_MISSING", "Authorization header with Bearer token required"), 401

    token = auth_header[7:]  # Strip "Bearer " prefix

    # Validate token via JWTService (DI pattern)
    jwt_service = current_app.extensions.get("jwt_service")
    if not jwt_service:
        logger.error("jwt_service not registered in app.extensions")
        return _auth_error("INTERNAL_AUTH_ERROR", "Authentication service unavailable"), 500

    try:
        payload = jwt_service.validate_token(token)
        if payload.get("role") != "admin":
            return _auth_error("AUTH_ADMIN_REQUIRED", "Administrator role is required"), 403
        g.current_user = payload
        return None
    except AuthenticationError:
        return _auth_error("AUTH_TOKEN_INVALID", "Invalid or expired bearer token"), 401


def _auth_error(code: str, message: str) -> Any:
    """RFC 7807 error response for authentication failures."""
    return jsonify(
        {
            "type": f"https://blacklist.local/errors/{code.lower().replace('_', '-')}",
            "title": "Authentication Error",
            "status": 500
            if code in {"INTERNAL_AUTH_ERROR", "AUTH_BYPASS_FORBIDDEN"}
            else 403
            if code == "AUTH_ADMIN_REQUIRED"
            else 401,
            "detail": message,
            "code": code,
        }
    )

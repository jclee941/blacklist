"""
JWT Authentication Middleware

before_request hook that enforces JWT on all routes by default.
Routes marked with @public decorator are exempt.
"""

import logging
from typing import Any

from flask import current_app, g, jsonify, request

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
        g.current_user = payload
        return None
    except Exception as e:
        return _auth_error("AUTH_TOKEN_INVALID", str(e)), 401


def _auth_error(code: str, message: str) -> Any:
    """RFC 7807 error response for authentication failures."""
    return jsonify(
        {
            "type": f"https://blacklist.local/errors/{code.lower().replace('_', '-')}",
            "title": "Authentication Error",
            "status": 401 if "INTERNAL" not in code else 500,
            "detail": message,
            "code": code,
        }
    )

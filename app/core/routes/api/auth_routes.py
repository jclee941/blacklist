"""
Authentication API routes.

Provides login/logout/me endpoints for JWT-based authentication.
"""

import logging

from flask import Blueprint, jsonify, request, g, current_app

from core.auth.decorators import public

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
@public
def login():
    """Authenticate user and return JWT token.

    Request body:
        {"username": "...", "password": "..."}

    Returns:
        {"token": "...", "expires_in": 28800, "user": {"id": "...", "role": "..."}}
    """
    data = request.get_json(silent=True)
    if not data or not data.get("username") or not data.get("password"):
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Username and password are required",
                "code": "AUTH_MISSING_CREDENTIALS",
            }
        ), 400

    username = data["username"]
    password = data["password"]

    # Validate against configured admin credentials
    settings_service = current_app.extensions.get("settings_service")
    if not settings_service:
        logger.error("settings_service not available for authentication")
        return jsonify(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Authentication service unavailable",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 500

    # Check credentials against app settings
    try:
        admin_username = settings_service.get_setting("admin_username", "admin")
        admin_password = settings_service.get_setting("admin_password", "")
    except Exception:
        # Fallback to environment variables
        import os

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")

    if username != admin_username or password != admin_password:
        logger.warning(f"Failed login attempt for user: {username}")
        return jsonify(
            {
                "type": "about:blank",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Invalid username or password",
                "code": "AUTH_INVALID_CREDENTIALS",
            }
        ), 401

    # Generate JWT token
    jwt_service = current_app.extensions["jwt_service"]
    token = jwt_service.encode_token(user_id=username, role="admin")

    logger.info(f"User '{username}' logged in successfully")
    return jsonify(
        {
            "token": token,
            "expires_in": 28800,
            "user": {"id": username, "role": "admin"},
        }
    ), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    """Return current authenticated user info.

    Returns:
        {"id": "...", "role": "...", "iat": ..., "exp": ...}
    """
    return jsonify(g.current_user), 200


@auth_bp.route("/verify", methods=["GET"])
def verify():
    """Verify that the current token is valid.

    Returns:
        {"valid": true, "user": {...}}
    """
    return jsonify({"valid": True, "user": g.current_user}), 200

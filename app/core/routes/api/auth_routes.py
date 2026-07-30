"""
Authentication API routes.

Provides login/logout/me endpoints for JWT-based authentication.
"""

import logging

from flask import Blueprint, jsonify, request, current_app

from core.auth.decorators import public
from core.config import config
from core.exceptions.auth_exceptions import AuthenticationError

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

    username = data["username"].strip()
    password = data["password"]

    if not username or len(username) > 255:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Username must be between 1 and 255 characters",
                "code": "AUTH_INVALID_INPUT",
            }
        ), 400

    if len(password) > 1024:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Password exceeds maximum length",
                "code": "AUTH_INVALID_INPUT",
            }
        ), 400

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

    try:
        admin_username = settings_service.get_setting("admin_username", config.ADMIN_USERNAME)
        admin_password = settings_service.get_setting("admin_password", config.ADMIN_PASSWORD)
    except Exception as e:
        # Fallback to environment variables
        logger.warning("Settings service unavailable, falling back to env vars: %s", e)
        admin_username = config.ADMIN_USERNAME
        admin_password = config.ADMIN_PASSWORD

    credentials_configured = bool(
        admin_username and admin_username.strip() and admin_password and admin_password.strip()
    )
    if not credentials_configured:
        logger.error("Administrator login is disabled: configure ADMIN_USERNAME and ADMIN_PASSWORD")
    elif username != admin_username or password != admin_password:
        logger.warning(f"Failed login attempt for user: {username}")
    else:
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

    return jsonify(
        {
            "type": "about:blank",
            "title": "Unauthorized",
            "status": 401,
            "detail": "Invalid username or password",
            "code": "AUTH_INVALID_CREDENTIALS",
        }
    ), 401


def _resolve_bearer_identity():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    jwt_service = current_app.extensions.get("jwt_service")
    if jwt_service is None:
        return None

    try:
        return jwt_service.validate_token(header[7:])
    except AuthenticationError:
        return None


def _unauthorized():
    return jsonify(
        {
            "type": "about:blank",
            "title": "Unauthorized",
            "status": 401,
            "detail": "A valid bearer token is required",
            "code": "AUTH_TOKEN_REQUIRED",
        }
    ), 401


@auth_bp.route("/me", methods=["GET"])
def me():
    """Return current authenticated user info.

    Returns:
        {"sub": "...", "role": "...", "iat": ..., "exp": ...}
    """
    identity = _resolve_bearer_identity()
    if identity is None:
        return _unauthorized()
    return jsonify(identity), 200


@auth_bp.route("/verify", methods=["GET"])
def verify():
    """Verify that the current token is valid.

    Returns:
        {"valid": true, "user": {...}}
    """
    identity = _resolve_bearer_identity()
    if identity is None:
        return _unauthorized()
    return jsonify({"valid": True, "user": identity}), 200

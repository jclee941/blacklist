import logging
import secrets

from flask import Blueprint, jsonify, request, current_app

from core.auth.decorators import public
from core.config import config
from core.exceptions.auth_exceptions import AuthenticationError
from core.auth.security import PasswordPolicyError, verify_password
from core.services.auth_state_service import AuthStateUnavailableError
from core.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
@rate_limit("5 per minute")
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

    raw_username = data["username"]
    password = data["password"]
    if not isinstance(raw_username, str) or not isinstance(password, str):
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Username and password must be strings",
                "code": "AUTH_INVALID_INPUT",
            }
        ), 400
    username = raw_username.strip()

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

    if len(password.encode("utf-8")) > 72:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Password exceeds maximum length",
                "code": "AUTH_INVALID_INPUT",
            }
        ), 400

    auth_state_service = current_app.extensions.get("auth_state_service")
    if not auth_state_service:
        logger.error("auth_state_service not available for authentication")
        return jsonify(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Authentication service unavailable",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 500

    auth_security = current_app.extensions.get("auth_security")
    if auth_security is None:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "Authentication service unavailable",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 500

    client_ip = request.remote_addr or "unknown"
    if auth_security.is_login_locked(username, client_ip):
        return jsonify(
            {
                "type": "about:blank",
                "title": "Too Many Requests",
                "status": 429,
                "detail": "Too many failed login attempts",
                "code": "AUTH_ACCOUNT_LOCKED",
            }
        ), 429

    try:
        credentials = auth_state_service.get_credentials(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
        admin_username = credentials.username
        admin_password = credentials.password_hash
    except (AuthStateUnavailableError, PasswordPolicyError) as error:
        logger.error("Authentication state unavailable: %s", error)
        return jsonify(
            {
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "Authentication service unavailable",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 503

    credentials_configured = False
    username_valid = False
    password_valid = False
    upgraded_hash = None
    if (
        isinstance(admin_username, str)
        and admin_username.strip()
        and isinstance(admin_password, str)
        and admin_password.strip()
    ):
        credentials_configured = True
        password_valid, upgraded_hash = verify_password(password, admin_password)
        username_valid = secrets.compare_digest(username.encode(), admin_username.encode())
    if not credentials_configured:
        logger.error("Administrator login is disabled: configure ADMIN_USERNAME and ADMIN_PASSWORD")
    if credentials_configured and (not username_valid or not password_valid):
        auth_security.record_login_failure(username, client_ip)
        logger.warning("Failed login attempt for user: %s", username)
    elif credentials_configured:
        if upgraded_hash is not None:
            try:
                password_persisted = auth_state_service.upgrade_password_hash(admin_password, upgraded_hash)
            except AuthStateUnavailableError:
                return jsonify(
                    {
                        "type": "about:blank",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "Authentication service unavailable",
                        "code": "AUTH_SERVICE_UNAVAILABLE",
                    }
                ), 503
            if not password_persisted:
                logger.info("Administrator password hash was already upgraded by another request")
        auth_security.clear_login_failures(username, client_ip)
        jwt_service = current_app.extensions["jwt_service"]
        token = jwt_service.encode_token(user_id=username, role="admin")
        expiry_seconds = jwt_service.expiry_seconds
        if not isinstance(expiry_seconds, int):
            expiry_seconds = config.JWT_EXPIRY_HOURS * 60 * 60

        logger.info("User '%s' logged in successfully", username)
        return jsonify(
            {
                "token": token,
                "expires_in": expiry_seconds,
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


@auth_bp.route("/logout", methods=["POST"])
def logout():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return _unauthorized()
    jwt_service = current_app.extensions.get("jwt_service")
    if jwt_service is None:
        return _unauthorized()
    try:
        jwt_service.revoke_token(header[7:])
    except (AuthenticationError, AttributeError):
        return _unauthorized()
    return jsonify({"success": True}), 200


@auth_bp.route("/password", methods=["PUT"])
@rate_limit("5 per minute")
def rotate_password():
    identity = _resolve_bearer_identity()
    if identity is None:
        return _unauthorized()
    if identity.get("role") != "admin":
        return jsonify(
            {
                "type": "about:blank",
                "title": "Forbidden",
                "status": 403,
                "detail": "Administrator role is required",
                "code": "AUTH_ADMIN_REQUIRED",
            }
        ), 403

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    if not isinstance(current_password, str) or not isinstance(new_password, str):
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "Current and new passwords are required",
                "code": "AUTH_INVALID_INPUT",
            }
        ), 400

    auth_state_service = current_app.extensions.get("auth_state_service")
    if auth_state_service is None:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "Authentication service unavailable",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 503
    try:
        rotated = auth_state_service.rotate_password(identity["sub"], current_password, new_password)
    except PasswordPolicyError:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Bad Request",
                "status": 400,
                "detail": "New password does not meet policy",
                "code": "AUTH_PASSWORD_POLICY",
            }
        ), 400
    except AuthStateUnavailableError:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "Password rotation failed",
                "code": "AUTH_SERVICE_UNAVAILABLE",
            }
        ), 503
    if not rotated:
        return jsonify(
            {
                "type": "about:blank",
                "title": "Unauthorized",
                "status": 401,
                "detail": "Current password is invalid",
                "code": "AUTH_CURRENT_PASSWORD_INVALID",
            }
        ), 401
    return jsonify({"success": True, "message": "Password rotated successfully"}), 200


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

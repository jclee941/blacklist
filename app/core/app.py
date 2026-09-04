#!/usr/bin/env python3
import io
import uuid
import gzip
from pathlib import Path

from flask import Flask, request, g
from flask.json.provider import DefaultJSONProvider
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import redis

from core.app_lifecycle import register_health_route, start_delayed_background_tasks
from core.app_logging import MemoryHandler
from .config import config
from .auth.proxy import TrustedProxyMiddleware
from .exceptions import ConfigurationError
from .utils.rate_limit import apply_route_limits, is_rate_limit_exempt_path

__all__ = ["MemoryHandler", "create_app"]


def create_app():
    app_root = Path(__file__).parent.parent
    templates_dir = app_root / "templates"

    app = Flask(__name__, template_folder=str(templates_dir))
    app.wsgi_app = TrustedProxyMiddleware(app.wsgi_app, config.TRUSTED_PROXY_NETWORKS)
    app.config["FORTINET_FEED_TOKEN"] = config.FORTINET_FEED_TOKEN
    app.config["FORTINET_FEED_ALLOWED_NETWORKS"] = config.FORTINET_FEED_ALLOWED_NETWORKS
    app.config["FORTIGATE_ALLOWED_NETWORKS"] = config.FORTIGATE_ALLOWED_NETWORKS
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_REQUEST_BODY_BYTES

    if config.DISABLE_JWT_AUTH and config.FLASK_ENV != "development" and not config.TESTING:
        raise ConfigurationError(
            "DISABLE_JWT_AUTH is forbidden outside development",
            config_key="DISABLE_JWT_AUTH",
        )

    # Secret key for session management and CSRF protection
    flask_secret = config.FLASK_SECRET_KEY or config.SECRET_KEY
    if not flask_secret:
        raise ConfigurationError("FLASK_SECRET_KEY or SECRET_KEY is required", config_key="FLASK_SECRET_KEY")
    app.config["SECRET_KEY"] = flask_secret

    app.config["WTF_CSRF_CHECK_DEFAULT"] = False

    class UTF8JSONProvider(DefaultJSONProvider):
        ensure_ascii = False

    app.json_provider_class = UTF8JSONProvider
    app.json = UTF8JSONProvider(app)

    csrf = CSRFProtect(app)

    @app.before_request
    def csrf_protect_web_only():
        if not request.path.startswith("/api/") and request.method in [
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ]:
            csrf.protect()

    app.logger.info("✅ CSRF protection enabled (web routes only, /api/* exempt)")

    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=config.get_redis_url(database=1),
        storage_options={"socket_connect_timeout": 2},
        default_limits=["1000 per hour"],
        strategy="fixed-window",
        headers_enabled=True,
    )

    @limiter.request_filter
    def ip_whitelist_rate_limit():
        """Exempt internal health checks from rate limiting"""
        if is_rate_limit_exempt_path(request.path):
            return True
        remote_addr = get_remote_address()
        whitelist = config.RATE_LIMIT_WHITELIST
        return any(
            remote_addr.startswith(entry) if entry.endswith(".") else remote_addr == entry for entry in whitelist
        )

    app.logger.info("✅ Rate limiting enabled (Flask-Limiter with Redis)")

    # Make limiter accessible for route-specific decorators
    app.extensions["limiter"] = limiter

    try:
        from core.services.service_factory import initialize_services

        services = initialize_services(app)

        # Register services in app.extensions for dependency injection
        for service_name, service_instance in services.items():
            app.extensions[service_name] = service_instance

        app.logger.info("✅ Initialized %d services via dependency injection", len(services))
    except Exception:
        app.logger.exception("❌ Service initialization failed")
        raise

    app.config["COMPRESS_ALGORITHM"] = "gzip"
    app.config["COMPRESS_LEVEL"] = 6

    from .auth.decorators import public
    from .auth.jwt_service import JWTService
    from .auth.middleware import jwt_required_hook
    from .auth.security import AuthSecurity, RedisSecurityStore

    auth_store = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=2,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        **config.get_redis_auth_params(),
    )
    auth_security = AuthSecurity(RedisSecurityStore(auth_store))
    app.extensions["auth_security"] = auth_security
    jwt_secret = config.JWT_SECRET
    if not jwt_secret:
        raise ConfigurationError("JWT_SECRET_KEY is required", config_key="JWT_SECRET_KEY")
    jwt_service = JWTService(
        jwt_secret,
        revocations=auth_security,
        session_versions=app.extensions.get("auth_state_service"),
        expiry_hours=config.JWT_EXPIRY_HOURS,
    )
    app.extensions["jwt_service"] = jwt_service
    app.before_request(jwt_required_hook)

    app.logger.info("✅ JWT authentication enabled")

    @app.before_request
    def generate_request_id():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )

        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif request.path in ["/favicon.ico", "/robots.txt"]:
            response.headers["Cache-Control"] = "public, max-age=604800"
        elif request.path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico")):
            response.headers["Cache-Control"] = "public, max-age=86400"
        elif request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    @app.after_request
    def compress_response(response):
        if "gzip" not in request.headers.get("Accept-Encoding", "").lower():
            return response

        if (
            response.direct_passthrough
            or len(response.get_data()) < 500
            or response.status_code < 200
            or response.status_code >= 300
        ):
            return response

        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode="wb", fileobj=gzip_buffer, compresslevel=6) as gzip_file:
            gzip_file.write(response.get_data())

        response.set_data(gzip_buffer.getvalue())
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        response.headers["Content-Length"] = len(response.get_data())

        return response

    try:
        from core.routes.api.blacklist import register_blacklist_routes

        register_blacklist_routes(app)
        app.logger.info("✅ Blacklist API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Blacklist API failed: {e}")

    try:
        from core.routes.api.auth_routes import auth_bp

        csrf.exempt(auth_bp)
        app.register_blueprint(auth_bp)
        app.logger.info("✅ Auth API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Auth API failed: {e}")

    try:
        from core.routes.api import api_bp

        csrf.exempt(api_bp)
        app.register_blueprint(api_bp, name="api_unified")
        app.logger.info("✅ Unified API Blueprint registered (CSRF exempt)")
    except Exception as e:
        app.logger.error(f"❌ Unified API Blueprint failed: {e}")

    try:
        from .routes.proxy_routes import proxy_bp

        csrf.exempt(proxy_bp)
        app.register_blueprint(proxy_bp, name="proxy_web")
    except Exception as e:
        app.logger.error(f"❌ Proxy API routes failed: {e}")

    try:
        from .errors.handlers import register_error_handlers

        register_error_handlers(app)
    except Exception as e:
        app.logger.error(f"Error handler registration failed: {e}")

    try:
        from .monitoring.metrics import setup_metrics, metrics_view

        setup_metrics(app)
        app.add_url_rule("/metrics", "metrics", public(metrics_view))
        app.logger.info("✅ Prometheus metrics enabled at /metrics")
    except ImportError as e:
        app.logger.warning(f"⚠️ Prometheus metrics not available: {e}")

    register_health_route(app)
    start_delayed_background_tasks(app)
    apply_route_limits(app, limiter)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=config.APP_PORT, debug=False)

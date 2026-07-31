#!/usr/bin/env python3
import io
import logging
import secrets
import uuid
import gzip
from pathlib import Path

from flask import Flask, request, g
from flask.json.provider import DefaultJSONProvider
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from core.app_lifecycle import register_health_route, start_delayed_background_tasks
from core.app_logging import MemoryHandler
from .config import config

__all__ = ["MemoryHandler", "create_app"]


def create_app():
    app_root = Path(__file__).parent.parent
    templates_dir = app_root / "templates"

    app = Flask(__name__, template_folder=str(templates_dir))

    # Secret key for session management and CSRF protection
    flask_secret = config.FLASK_SECRET_KEY or config.SECRET_KEY
    if not flask_secret:
        logging.getLogger(__name__).warning(
            "FLASK_SECRET_KEY not set — using random key. "
            "JWTs will be invalidated on restart. Set FLASK_SECRET_KEY in production."
        )
        flask_secret = secrets.token_hex(32)
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
        default_limits=["200 per day", "50 per hour"],
        strategy="fixed-window",
        headers_enabled=True,
    )

    @limiter.request_filter
    def ip_whitelist_rate_limit():
        """Exempt internal health checks from rate limiting"""
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

        app.logger.info(f"✅ Initialized {len(services)}/15 services via dependency injection")
    except Exception:
        app.logger.exception("❌ Service initialization failed")
        raise

    app.config["COMPRESS_ALGORITHM"] = "gzip"
    app.config["COMPRESS_LEVEL"] = 6

    from .auth.decorators import public
    from .auth.jwt_service import JWTService
    from .auth.middleware import jwt_required_hook

    jwt_service = JWTService(config.JWT_SECRET or app.config["SECRET_KEY"])
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
        from core.routes.api.fortinet import register_fortinet_routes

        register_fortinet_routes(app)
        app.logger.info("✅ Fortinet API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Fortinet API failed: {e}")

    try:
        from core.routes.api.collection import register_collection_routes

        register_collection_routes(app)
        app.logger.info("✅ Collection API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Collection API failed: {e}")

    try:
        from core.routes.api import api_bp
        from core.routes.api.ip_management import ip_management_legacy_bp

        # Exempt API blueprint from CSRF - API uses other auth mechanisms (tokens, headers)
        csrf.exempt(api_bp)
        csrf.exempt(ip_management_legacy_bp)
        # Use name='api_unified' to avoid name collision with existing blueprints
        app.register_blueprint(api_bp, name="api_unified")
        app.register_blueprint(ip_management_legacy_bp)
        app.logger.info("✅ Unified API Blueprint registered (CSRF exempt)")
    except Exception as e:
        app.logger.error(f"❌ Unified API Blueprint failed: {e}")

    try:
        from .routes.web.settings import settings_bp

        csrf.exempt(settings_bp)
    except Exception as e:
        settings_bp = None
        app.logger.error(f"❌ Settings blueprint import failed: {e}")

    try:
        from .routes.web.admin import regtech_admin_bp

        csrf.exempt(regtech_admin_bp)
    except Exception as e:
        regtech_admin_bp = None
        app.logger.error(f"❌ REGTECH admin blueprint import failed: {e}")

    try:
        from .routes.web_routes import web_bp

        if "web" not in app.blueprints:
            app.register_blueprint(web_bp)
    except Exception as e:
        app.logger.error(f"❌ Web routes failed: {e}")

    if regtech_admin_bp:
        try:
            app.register_blueprint(regtech_admin_bp, url_prefix="/admin", name="regtech_admin_web")
        except Exception as e:
            app.logger.error(f"❌ REGTECH admin routes registration failed: {e}")

    if settings_bp:
        try:
            app.register_blueprint(settings_bp, name="settings_web")
        except Exception as e:
            app.logger.error(f"❌ Settings routes registration failed: {e}")

    try:
        from .routes.web.collection_panel import collection_bp

        csrf.exempt(collection_bp)
        app.register_blueprint(collection_bp, name="collection_panel_web")
    except Exception as e:
        app.logger.error(f"❌ Collection panel routes failed: {e}")

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

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=config.APP_PORT, debug=False)

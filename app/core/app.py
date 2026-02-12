#!/usr/bin/env python3
"""
Flask Application - PostgreSQL Connection and Collection Management
"""

import io
import logging
import os
import secrets
import threading
import time
import uuid
import gzip
from datetime import datetime
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, request, g
from flask.json.provider import DefaultJSONProvider
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect


# Custom MemoryHandler for capturing logs
class MemoryHandler(logging.Handler):
    def __init__(self, capacity):
        super().__init__()
        self.capacity = capacity
        self.buffer = []

    def emit(self, record):
        self.buffer.append(self.format(record))
        if len(self.buffer) > self.capacity:
            self.buffer.pop(0)

    def get_logs(self):
        return self.buffer.copy()


# Initialize logger outside create_app to avoid re-initialization
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
memory_handler = MemoryHandler(capacity=1000)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
memory_handler.setFormatter(formatter)
logger.addHandler(memory_handler)


def create_app():
    """Create Flask application instance"""
    # Set templates directory to templates (build context is src/)
    app_root = Path(__file__).parent.parent  # /app
    templates_dir = app_root / "templates"  # /app/templates

    app = Flask(__name__, template_folder=str(templates_dir))

    # ========================================================================
    # Security Configuration (Phase 1.3: CSRF & Rate Limiting)
    # ========================================================================

    # Secret key for session management and CSRF protection
    flask_secret = os.getenv("FLASK_SECRET_KEY")
    if not flask_secret:
        logging.getLogger(__name__).warning(
            "FLASK_SECRET_KEY not set — using random key. "
            "JWTs will be invalidated on restart. Set FLASK_SECRET_KEY in production."
        )
        flask_secret = secrets.token_hex(32)
    app.config["SECRET_KEY"] = flask_secret

    # CSRF Protection Configuration
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

    # Rate Limiting Configuration (Redis-backed for distributed systems)
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=f"redis://{os.getenv('REDIS_HOST', 'blacklist-redis')}:{os.getenv('REDIS_PORT', '6379')}/1",
        storage_options={"socket_connect_timeout": 2},
        default_limits=["200 per day", "50 per hour"],  # Global rate limits
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit headers to responses
    )

    # Custom rate limits for specific API endpoints
    @limiter.request_filter
    def ip_whitelist_rate_limit():
        """Exempt internal health checks from rate limiting"""
        # Exempt localhost and container network
        remote_addr = get_remote_address()
        return (
            remote_addr in ["127.0.0.1", "localhost"]
            or remote_addr.startswith("172.")
            or remote_addr.startswith("192.168.")
        )

    app.logger.info("✅ Rate limiting enabled (Flask-Limiter with Redis)")

    # Make limiter accessible for route-specific decorators
    app.extensions["limiter"] = limiter

    # ========================================================================
    # Service Dependency Injection (Phase 2: Service Container Pattern)
    # ========================================================================
    try:
        from core.services.service_factory import initialize_services

        services = initialize_services(app)

        # Register services in app.extensions for dependency injection
        for service_name, service_instance in services.items():
            app.extensions[service_name] = service_instance

        app.logger.info(f"✅ Initialized {len(services)}/15 services via dependency injection")
    except Exception as e:
        app.logger.error(f"❌ Service initialization failed: {e}")

    # Enable Gzip compression
    app.config["COMPRESS_ALGORITHM"] = "gzip"
    app.config["COMPRESS_LEVEL"] = 6

    # ========================================================================
    # JWT Authentication (Phase 1.1: Token-based API Auth)
    # ========================================================================
    try:
        from core.auth.jwt_service import JWTService
        from core.auth.decorators import public

        jwt_service = JWTService(app.config["SECRET_KEY"])
        app.extensions["jwt_service"] = jwt_service

        # JWT auth disabled — internal-only deployment, no auth required
        # app.before_request(jwt_required_hook)
        app.logger.info("ℹ️ JWT authentication middleware DISABLED")
    except Exception as e:
        app.logger.error(f"❌ JWT auth setup failed: {e}")

    # Request ID middleware
    @app.before_request
    def generate_request_id():
        """Generate unique request ID for tracing"""
        g.request_id = str(uuid.uuid4())

    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses"""
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

    # Enable Gzip compression for responses
    @app.after_request
    def compress_response(response):
        """Compress response if client supports it"""
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

    # ========================================================================
    # API Routes Registration (Consolidated)
    # ========================================================================

    # 1. Register Modular Blacklist API Routes
    try:
        from core.routes.api.blacklist import register_blacklist_routes

        register_blacklist_routes(app)
        app.logger.info("✅ Blacklist API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Blacklist API failed: {e}")

    # 2. Register Auth API Routes
    try:
        from core.routes.api.auth_routes import auth_bp

        csrf.exempt(auth_bp)
        app.register_blueprint(auth_bp)
        app.logger.info("✅ Auth API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Auth API failed: {e}")

    # 2. Register Modular Fortinet API Routes
    try:
        from core.routes.api.fortinet import register_fortinet_routes

        register_fortinet_routes(app)
        app.logger.info("✅ Fortinet API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Fortinet API failed: {e}")

    # 3. Register Modular Collection API Routes
    try:
        from core.routes.api.collection import register_collection_routes

        register_collection_routes(app)
        app.logger.info("✅ Collection API routes registered")
    except Exception as e:
        app.logger.error(f"❌ Collection API failed: {e}")

    # 4. Register Unified API Blueprint (contains system, monitoring, etc.)
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

    # 3. Register Web UI Blueprints
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

    # 4. Register Compatibility/Legacy Blueprints if not already handled
    try:
        from .routes.proxy_routes import proxy_bp

        csrf.exempt(proxy_bp)
        app.register_blueprint(proxy_bp, name="proxy_web")
    except Exception as e:
        app.logger.error(f"❌ Proxy API routes failed: {e}")

    # 5. Credentials API
    # DISABLED: Redundant with api/collection.py which implements secure credential handling
    # try:
    #     from .routes.web.credentials_routes import credentials_bp
    #
    #     csrf.exempt(credentials_bp)
    #     app.register_blueprint(credentials_bp, name="credentials_web")
    # except Exception as e:
    #     app.logger.error(f"❌ Credentials API routes failed: {e}")

    # Register error handlers
    try:
        from core.errors.handlers import register_error_handlers

        register_error_handlers(app)
    except Exception as e:
        app.logger.error(f"Error handler registration failed: {e}")

    # Setup Prometheus Metrics
    try:
        from core.monitoring.metrics import setup_metrics, metrics_view

        setup_metrics(app)
        app.add_url_rule("/metrics", "metrics", metrics_view)
        app.logger.info("✅ Prometheus metrics enabled at /metrics")
    except ImportError as e:
        app.logger.warning(f"⚠️ Prometheus metrics not available: {e}")

    @app.route("/health")
    @public
    def health_check():
        """Health check endpoint"""
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "blacklist-postgres"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "blacklist"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            )
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in cursor.fetchall()]
            try:
                cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
                row = cursor.fetchone()
                ip_count = row[0] if row else 0
            except psycopg2.Error:
                ip_count = 0
            cursor.close()
            conn.close()
            return jsonify(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "database": {
                        "connection": "successful",
                        "tables": tables,
                        "blacklist_ips_count": ip_count,
                    },
                    "message": "✅ PostgreSQL connection successful!",
                }
            ), 200
        except Exception as e:
            return jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                }
            ), 500

    def start_background_tasks():
        """Start background tasks"""
        try:
            db_service = app.extensions.get("db_service")
            expiry_service = app.extensions.get("expiry_service")
            if db_service and expiry_service:
                expiry_service.check_and_deactivate_expired_ips()

            if os.getenv("DISABLE_AUTO_COLLECTION", "").lower() in ("true", "1", "yes"):
                return

            scheduler_service = app.extensions.get("scheduler_service")
            if not db_service or not scheduler_service:
                return

            conn = db_service.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, password, enabled FROM collection_credentials WHERE service_name = 'REGTECH'"
            )
            result = cursor.fetchone()
            cursor.close()
            db_service.return_connection(conn)

            if result and result[2] and result[0] and result[1]:
                scheduler_service.start()
        except Exception as e:
            app.logger.error(f"Background task start failed: {e}")

    def delayed_background_start():
        time.sleep(5)
        with app.app_context():
            start_background_tasks()

    threading.Thread(target=delayed_background_start, daemon=True).start()

    # Credentials API Routes
    # Already registered above in section 5
    # try:
    #     from .routes.web.credentials_routes import credentials_bp
    #
    #     csrf.exempt(credentials_bp)
    #     app.register_blueprint(credentials_bp)
    # except Exception as e:
    #     app.logger.error(f"Credentials API routes failed: {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 2542))
    app.run(host="0.0.0.0", port=port, debug=False)

"""
Collection API Routes
Modular structure for Collection management
"""

from flask import Blueprint

# Import sub-blueprints
from .status import collection_status_bp
from .trigger import collection_trigger_bp
from .history import collection_history_bp
from .credentials import collection_credentials_bp
from .sync import collection_sync_bp
from .config import collection_config_bp
from .sources import sources_bp
from . import credential_validation


def register_collection_routes(app):
    """Register all Collection route blueprints"""
    # Register blueprints with explicit URL prefix where needed
    # Note: Some blueprints might define their own prefix or route paths

    # /api/collection/status, /api/collection/health
    app.register_blueprint(collection_status_bp, url_prefix="/api/collection")

    # /api/collection/trigger/<source>
    app.register_blueprint(collection_trigger_bp, url_prefix="/api/collection")

    # /api/collection/history, /api/collection/statistics
    app.register_blueprint(collection_history_bp, url_prefix="/api/collection")

    # /api/collection/credentials/<source>
    app.register_blueprint(collection_credentials_bp, url_prefix="/api/collection")

    # /api/sync/collector, /api/data/refresh
    app.register_blueprint(collection_sync_bp, url_prefix="/api")

    # /api/collection/config/update
    app.register_blueprint(collection_config_bp, url_prefix="/api")

    # /api/collection/sources
    app.register_blueprint(sources_bp, url_prefix="/api/collection")

    # Exempt API blueprints from CSRF protection
    from flask_wtf.csrf import CSRFProtect

    csrf = app.extensions.get("csrf")
    if csrf:
        csrf.exempt(collection_status_bp)
        csrf.exempt(collection_trigger_bp)
        csrf.exempt(collection_history_bp)
        csrf.exempt(collection_credentials_bp)
        csrf.exempt(collection_sync_bp)
        csrf.exempt(collection_config_bp)
        csrf.exempt(sources_bp)

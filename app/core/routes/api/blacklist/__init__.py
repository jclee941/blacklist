#!/usr/bin/env python3
"""
Blacklist API Routes Module
Modular structure for blacklist/whitelist operations

This module provides focused route blueprints for:
- Core operations (list, stats, check, JSON)
- Manual IP management (add/remove blacklist/whitelist)
- Batch operations (bulk add/remove/update)
- System status (containers, credentials, database)
- Collection triggering (REGTECH collection)
"""

from flask import jsonify
from datetime import datetime

# Import all blueprints
from .core import blacklist_core_bp
from .management import blacklist_management_bp
from .batch import blacklist_batch_bp
from .system import blacklist_system_bp
from .collection import blacklist_collection_bp


def register_blacklist_routes(app):
    """Register all blacklist route blueprints with the Flask application

    Args:
        app: Flask application instance

    Blueprints registered:
        - blacklist_core_bp: Core operations (4 routes)
        - blacklist_management_bp: Manual IP management (3 routes)
        - blacklist_batch_bp: Batch operations (3 routes)
        - blacklist_system_bp: System/credentials status (4 routes)
        - blacklist_collection_bp: Collection triggering (1 route)
    """
    # Register all blueprints with /api prefix
    app.register_blueprint(blacklist_core_bp, url_prefix="/api")
    app.register_blueprint(blacklist_management_bp, url_prefix="/api")
    app.register_blueprint(blacklist_batch_bp, url_prefix="/api")
    app.register_blueprint(blacklist_system_bp, url_prefix="/api")
    app.register_blueprint(blacklist_collection_bp, url_prefix="/api")

    # Exempt API blueprints from CSRF protection (API endpoints use tokens/headers for auth)
    from flask_wtf.csrf import CSRFProtect

    csrf = app.extensions.get("csrf")
    if csrf:
        csrf.exempt(blacklist_core_bp)
        csrf.exempt(blacklist_management_bp)
        csrf.exempt(blacklist_batch_bp)
        csrf.exempt(blacklist_system_bp)
        csrf.exempt(blacklist_collection_bp)

    # Register error handlers
    register_error_handlers(app)


def register_error_handlers(app):
    """Register error handlers for blacklist routes

    Args:
        app: Flask application instance
    """

    @app.errorhandler(404)
    def api_not_found(error):
        """API 404 핸들러"""
        return jsonify(
            {
                "success": False,
                "error": "API endpoint not found",
                "available_endpoints": [
                    "/api/blacklist/list",
                    "/api/blacklist/stats",
                    "/api/blacklist/check",
                    "/api/blacklist/manual-add",
                    "/api/whitelist/manual-add",
                    "/api/whitelist/list",
                    "/api/blacklist/batch/add",
                    "/api/blacklist/batch/remove",
                    "/api/blacklist/batch/update",
                    "/api/system/containers",
                    "/api/credential/status",
                    "/api/credentials/regtech",
                    "/api/database/tables",
                    "/api/collection/regtech/trigger",
                ],
            }
        ), 404

    @app.errorhandler(500)
    def api_server_error(error):
        """API 500 핸들러"""
        return jsonify(
            {"success": False, "error": "Internal server error", "timestamp": datetime.now().isoformat()}
        ), 500


# Export blueprints for direct access if needed
__all__ = [
    "register_blacklist_routes",
    "blacklist_core_bp",
    "blacklist_management_bp",
    "blacklist_batch_bp",
    "blacklist_system_bp",
    "blacklist_collection_bp",
]

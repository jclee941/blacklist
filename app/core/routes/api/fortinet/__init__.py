"""
Fortinet API Routes
Modular structure for Fortinet integration
"""

from flask import jsonify
from datetime import datetime

# Import sub-blueprints
from .core import fortinet_core_bp
from .logs import fortinet_logs_bp
from .management import fortinet_management_bp
from .threat_feed import fortinet_feed_bp
from core.utils.response_utils import safe_error_message


def register_fortinet_routes(app):
    """Register all Fortinet route blueprints"""
    # URL prefix is set on sub-blueprints, or we can set it here
    # Original file used /api/fortinet

    app.register_blueprint(fortinet_core_bp, url_prefix="/api/fortinet")
    app.register_blueprint(fortinet_logs_bp, url_prefix="/api/fortinet")
    app.register_blueprint(fortinet_management_bp, url_prefix="/api/fortinet")
    app.register_blueprint(fortinet_feed_bp, url_prefix="/api/fortinet")

    # Health check endpoint (needs to be available)
    # We can add it to core or register separately
    from .core import fortinet_core_bp as core_bp

    # Error handlers are already registered globally, but we can add module specific ones if needed


@fortinet_core_bp.route("/health", methods=["GET"])
def fortinet_health():
    """
    Health check for FortiGate integration
    Moved here to be part of the package structure
    """
    from flask import current_app, g

    try:
        db_service = current_app.extensions["db_service"]
        count_query = "SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive WHERE is_active = true"
        result = db_service.query(count_query)
        active_count = result[0]["count"] if result else 0

        return jsonify(
            {
                "success": True,
                "data": {
                    "status": "healthy",
                    "active_ips": active_count,
                    "database": "healthy",
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200
    except Exception as e:
        return jsonify(
            {
                "success": True,
                "data": {
                    "status": "unhealthy",
                    "active_ips": 0,
                    "database": "unhealthy",
                    "error": safe_error_message(e),
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

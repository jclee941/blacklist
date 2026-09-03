"""
Core API Endpoints
Documentation, health checks, and basic API information

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
"""

from ..api_routes import api_bp
from flask import jsonify, g, current_app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@api_bp.route("/docs", methods=["GET"])
def api_documentation():
    """
    API Documentation endpoint (Phase 1.4: Standardized Error Handling)

    GET /api/docs

    Returns:
        {
            "success": True,
            "data": {
                "message": "API Documentation",
                "dashboard_url": "/",
                "api_endpoints": {...}
            },
            "timestamp": "...",
            "request_id": "..."
        }
    """
    return jsonify(
        {
            "success": True,
            "data": {
                "message": "API Documentation",
                "dashboard_url": "/",
                "note": "Visit / or /dashboard for the web interface",
                "api_endpoints": {
                    "health": "/health",
                    "stats": "/api/stats",
                    "blacklist": "/api/blacklist/active",
                    "fortigate": "/api/fortigate",
                    "collection": "/api/collection/status",
                },
            },
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 200


@api_bp.route("/health", methods=["GET"])
def service_status():
    """Return coarse application health without operational data."""
    try:
        blacklist_service = current_app.extensions["blacklist_service"]
        blacklist_service.get_system_stats()
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200
    except Exception:
        logger.exception("Service health check failed")
        return jsonify({"status": "unhealthy", "timestamp": datetime.now().isoformat()}), 200

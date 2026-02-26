"""
Core API Endpoints
Documentation, health checks, and basic API information

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
"""

from . import api_bp
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
    """
    Service health check endpoint (Phase 1.4: Standardized Error Handling)

    GET /api/health

    Note: Health endpoints use graceful degradation (never raise exceptions).
    Always returns 200 OK with status field indicating health state.

    Returns:
        {
            "success": True,
            "data": {
                "status": "healthy" | "unhealthy",
                "service_status": "running",
                "database_connected": True,
                "cache_available": True,
                "total_ips": 1234,
                "active_ips": 1234,
                "last_updated": "..."
            },
            "timestamp": "...",
            "request_id": "..."
        }
    """
    try:
        blacklist_service = current_app.extensions["blacklist_service"]

        stats = blacklist_service.get_system_stats()

        return jsonify(
            {
                "success": True,
                "data": {
                    "status": "healthy",
                    "service_status": "running",
                    "database_connected": True,
                    "cache_available": True,
                    "total_ips": stats.get("total_ips", 0),
                    "active_ips": stats.get("active_ips", 0),
                    "last_updated": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Service status error: {e}", exc_info=True)
        # Graceful degradation - always return 200 with unhealthy status
        return jsonify(
            {
                "success": True,
                "data": {
                    "status": "unhealthy",
                    "service_status": "error",
                    "database_connected": False,
                    "cache_available": False,
                    "total_ips": 0,
                    "active_ips": 0,
                    "error": str(e),
                    "last_updated": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

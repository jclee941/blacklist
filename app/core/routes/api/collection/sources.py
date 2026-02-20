"""
Collection Sources API
Lists available data sources for threat intelligence collection
"""

from flask import Blueprint, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

sources_bp = Blueprint("collection_sources", __name__)

AVAILABLE_SOURCES = [
    {
        "id": "REGTECH",
        "name": "REGTECH (Korean Financial Security Institute)",
        "description": "Korean Financial Security Institute threat intelligence feed",
        "enabled": True,
        "requires_auth": True,
        "schedule": "daily",
        "data_types": ["ip", "domain", "url"],
    },
    {
        "id": "SECUDIUM",
        "name": "SECUDIUM",
        "description": "SECUDIUM threat intelligence (OTP 인증 기반, 수동 수집 전용)",
        "enabled": True,
        "requires_auth": True,
        "schedule": "manual",
        "data_types": ["ip"],
    },
]


@sources_bp.route("/sources", methods=["GET"])
def list_sources():
    """
    List available collection sources
    Returns metadata about each source including status and capabilities
    """
    try:
        enabled_sources = [s for s in AVAILABLE_SOURCES if s.get("enabled", False)]
        disabled_sources = [s for s in AVAILABLE_SOURCES if not s.get("enabled", False)]

        return jsonify(
            {
                "success": True,
                "sources": AVAILABLE_SOURCES,
                "summary": {
                    "total": len(AVAILABLE_SOURCES),
                    "enabled": len(enabled_sources),
                    "disabled": len(disabled_sources),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error listing collection sources: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sources_bp.route("/sources/<source_id>", methods=["GET"])
def get_source(source_id):
    """Get details for a specific collection source"""
    try:
        source = next((s for s in AVAILABLE_SOURCES if s["id"] == source_id.upper()), None)

        if not source:
            return jsonify({"success": False, "error": f"Source not found: {source_id}"}), 404

        return jsonify({"success": True, "source": source})

    except Exception as e:
        logger.error(f"Error getting source {source_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@sources_bp.route("/sources/<source_id>/status", methods=["GET"])
def get_source_status(source_id):
    """Get current status and last collection info for a source"""
    try:
        source = next((s for s in AVAILABLE_SOURCES if s["id"] == source_id.upper()), None)

        if not source:
            return jsonify({"success": False, "error": f"Source not found: {source_id}"}), 404

        if not source.get("enabled", False):
            return jsonify(
                {
                    "success": True,
                    "source_id": source_id.upper(),
                    "status": "disabled",
                    "message": source.get("deprecation_note", "Source is disabled"),
                }
            )

        db_service = current_app.extensions.get("db_service")
        if not db_service:
            return jsonify(
                {
                    "success": True,
                    "source_id": source_id.upper(),
                    "status": "unknown",
                    "message": "Database service unavailable",
                }
            )

        last_collection = db_service.query(
            """
            SELECT id, service_name, collection_date, items_collected, success, error_message
            FROM collection_history
            WHERE service_name = %s
            ORDER BY collection_date DESC
            LIMIT 1
            """,
            (source_id.upper(),),
        )

        if last_collection:
            record = last_collection[0]
            return jsonify(
                {
                    "success": True,
                    "source_id": source_id.upper(),
                    "status": "success" if record.get("success") else "failed",
                    "last_collection": {
                        "collection_date": (
                            record["collection_date"].isoformat() if record.get("collection_date") else None
                        ),
                        "items_collected": record.get("items_collected", 0),
                        "error_message": record.get("error_message"),
                    },
                }
            )

        return jsonify(
            {
                "success": True,
                "source_id": source_id.upper(),
                "status": "never_collected",
                "message": "No collection history found",
            }
        )

    except Exception as e:
        logger.error(f"Error getting source status {source_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

"""
Fortinet API Logging Operations
Handles pull request logs and active session monitoring
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app
from core.exceptions import ValidationError, DatabaseError

logger = logging.getLogger(__name__)

fortinet_logs_bp = Blueprint("fortinet_logs", __name__)


@fortinet_logs_bp.route("/active-sessions", methods=["GET"])
def get_active_sessions():
    """
    Get active threat sessions for monitoring
    """
    limit = request.args.get("limit", 50, type=int)
    hours = request.args.get("hours", 24, type=int)

    if limit < 1 or limit > 500:
        raise ValidationError(
            message="Limit must be between 1 and 500",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-500"},
        )
    if hours < 1 or hours > 8760:
        raise ValidationError(
            message="Hours must be between 1 and 8760 (1 year)",
            field="hours",
            details={"provided_value": hours, "allowed_range": "1-8760"},
        )

    db_service = current_app.extensions["db_service"]

    try:
        query = """
            SELECT
                id, ip_address, country, reason, confidence_level,
                detection_date, removal_date, is_active, created_at, updated_at,
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - detection_date)) / 3600 as active_hours
            FROM blacklist_ips_with_auto_inactive
            WHERE detection_date >= CURRENT_TIMESTAMP - INTERVAL '%s hours'
            ORDER BY detection_date DESC
            LIMIT %s
        """
        rows = db_service.query(query, (hours, limit))

        sessions = []
        for row in rows:
            if row["is_active"]:
                session_status = "active"
            elif row["removal_date"] and row["removal_date"] <= datetime.now().date():
                session_status = "expired"
            else:
                session_status = "inactive"

            sessions.append(
                {
                    "id": row["id"],
                    "ip_address": row["ip_address"],
                    "country": row["country"],
                    "reason": row["reason"],
                    "confidence_level": row["confidence_level"],
                    "detection_date": row["detection_date"].isoformat() if row["detection_date"] else None,
                    "removal_date": row["removal_date"].isoformat() if row["removal_date"] else None,
                    "is_active": row["is_active"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "active_hours": round(float(row["active_hours"]), 1) if row["active_hours"] else 0,
                    "session_status": session_status,
                }
            )

        stats_query = """
            SELECT
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN is_active = true THEN 1 END) as active_count,
                COUNT(CASE WHEN detection_date >= CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN 1 END) as last_hour,
                COUNT(CASE WHEN detection_date >= CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 1 END) as last_24h,
                COUNT(DISTINCT country) as unique_countries
            FROM blacklist_ips_with_auto_inactive
            WHERE detection_date >= CURRENT_TIMESTAMP - INTERVAL '%s hours'
        """
        stats_row = db_service.query(stats_query, (hours,))[0]

        stats = {
            "total_sessions": stats_row["total_sessions"],
            "active_count": stats_row["active_count"],
            "last_hour": stats_row["last_hour"],
            "last_24h": stats_row["last_24h"],
            "unique_countries": stats_row["unique_countries"],
        }

        return jsonify(
            {
                "success": True,
                "data": sessions,
                "stats": stats,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting active sessions: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve active threat sessions",
            details={"limit": limit, "hours": hours, "error_type": type(e).__name__},
        )


@fortinet_logs_bp.route("/pull-logs", methods=["GET"])
def get_pull_logs():
    """
    Get FortiGate pull request logs
    """
    limit = request.args.get("limit", 50, type=int)
    hours = request.args.get("hours", 24, type=int)

    if limit < 1 or limit > 500:
        raise ValidationError(
            message="Limit must be between 1 and 500",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-500"},
        )

    db_service = current_app.extensions["db_service"]

    try:
        query = """
            SELECT
                id, device_ip, user_agent, request_path,
                ip_count, response_time_ms, response_status, created_at
            FROM fortinet_pull_logs
            WHERE created_at >= CURRENT_TIMESTAMP - make_interval(hours => %s)
            ORDER BY created_at DESC
            LIMIT %s
        """
        rows = db_service.query(query, (hours, limit))

        logs = []
        for row in rows:
            logs.append(
                {
                    "id": row["id"],
                    "device_ip": row["device_ip"],
                    "user_agent": row["user_agent"],
                    "endpoint": row["request_path"],
                    "ip_count": row["ip_count"],
                    "response_time_ms": row["response_time_ms"],
                    "status_code": row["response_status"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
            )

        stats_query = """
            SELECT
                COUNT(*) as total_pulls,
                COUNT(CASE WHEN response_status = 200 THEN 1 END) as successful_pulls,
                COUNT(CASE WHEN response_status != 200 THEN 1 END) as failed_pulls,
                COUNT(DISTINCT device_ip) as unique_devices
            FROM fortinet_pull_logs
            WHERE created_at >= CURRENT_TIMESTAMP - make_interval(hours => %s)
        """
        stats_row = db_service.query(stats_query, (hours,))[0]

        return jsonify(
            {
                "success": True,
                "data": logs,
                "stats": {
                    "total_pulls": stats_row["total_pulls"],
                    "successful_pulls": stats_row["successful_pulls"],
                    "failed_pulls": stats_row["failed_pulls"],
                    "unique_devices": stats_row["unique_devices"],
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting pull logs: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve FortiGate pull logs: {type(e).__name__}",
            table="fortinet_pull_logs",
        )

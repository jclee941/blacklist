"""
Fortinet API Core Operations
Handles active IP retrieval, blocklist generation, and configuration
"""

import logging
import time
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app, Response
from ....exceptions import ValidationError, DatabaseError, InternalServerError
from .utils import _log_pull_request

logger = logging.getLogger(__name__)

fortinet_core_bp = Blueprint("fortinet_core", __name__)


@fortinet_core_bp.route("/active-ips", methods=["GET"])
def get_active_ips():
    """
    Get active blacklist IPs for FortiGate integration
    """
    limit = request.args.get("limit", 20, type=int)
    page = request.args.get("page", 1, type=int)

    if limit < 1 or limit > 1000:
        raise ValidationError(
            message="Limit must be between 1 and 1000",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-1000"},
        )
    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )

    db_service = current_app.extensions["db_service"]

    try:
        offset = (page - 1) * limit
        query = """
            SELECT
                b.id, b.ip_address, b.country, b.reason,
                b.confidence_level, b.detection_date, b.removal_date, b.is_active
            FROM blacklist_ips_with_auto_inactive b
            WHERE b.is_active = true
              AND b.ip_address NOT IN (
                  SELECT ip_address FROM whitelist_ips WHERE is_active = true
              )
            ORDER BY b.confidence_level DESC, b.detection_date DESC
            LIMIT %s OFFSET %s
        """
        rows = db_service.query(query, (limit, offset))

        active_ips = []
        for row in rows:
            active_ips.append(
                {
                    "id": row["id"],
                    "ip_address": row["ip_address"],
                    "country": row["country"],
                    "reason": row["reason"],
                    "confidence_level": row["confidence_level"],
                    "detection_date": row["detection_date"].isoformat() if row["detection_date"] else None,
                    "removal_date": row["removal_date"].isoformat() if row["removal_date"] else None,
                    "is_active": row["is_active"],
                }
            )

        count_query = """
            SELECT COUNT(*) as count
            FROM blacklist_ips_with_auto_inactive b
            WHERE b.is_active = true
              AND b.ip_address NOT IN (
                  SELECT ip_address FROM whitelist_ips WHERE is_active = true
              )
        """
        total = db_service.query(count_query)[0]["count"]

        return jsonify(
            {
                "success": True,
                "data": active_ips,
                "total": total,
                "page": page,
                "limit": limit,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting active IPs: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve active IPs for FortiGate",
            table="blacklist_ips_with_auto_inactive",
        )


@fortinet_core_bp.route("/blocklist", methods=["GET"])
def get_blocklist():
    """
    Get FortiGate External Resource compatible blocklist
    Returns plain text by default for FortiGate EBL compatibility
    """
    start_time = time.time()
    output_format = request.args.get("format", "text").lower()

    if output_format not in ["text", "json"]:
        raise ValidationError(
            message=f"Invalid format: {output_format}. Must be 'text' or 'json'",
            field="format",
            details={
                "provided_value": output_format,
                "allowed_values": ["text", "json"],
            },
        )

    db_service = current_app.extensions["db_service"]

    try:
        query = """
            SELECT ip_address
            FROM blacklist_ips_with_auto_inactive
            WHERE is_active = true
              AND ip_address NOT IN (
                  SELECT ip_address FROM whitelist_ips WHERE is_active = true
              )
            ORDER BY ip_address
        """
        rows = db_service.query(query)
        ip_list = [row["ip_address"] for row in rows]

        response_time_ms = int((time.time() - start_time) * 1000)
        _log_pull_request("/blocklist", len(ip_list), 200, response_time_ms)

        if output_format == "json":
            blocklist_text = "\n".join(ip_list)
            return jsonify(
                {
                    "success": True,
                    "data": {"blocklist": blocklist_text, "total": len(ip_list)},
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        blocklist_text = "\n".join(ip_list)
        return Response(
            blocklist_text,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "inline; filename=blocklist.txt",
                "X-Total-IPs": str(len(ip_list)),
                "X-Generated-At": datetime.now().isoformat(),
                "X-Whitelist-Excluded": "true",
                "X-Request-ID": g.request_id,
                "Cache-Control": "no-cache, must-revalidate",
            },
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error generating blocklist: {e}", exc_info=True)
        response_time_ms = int((time.time() - start_time) * 1000)
        _log_pull_request("/blocklist", 0, 500, response_time_ms)

        if output_format == "text":
            return Response(f"# Error: {str(e)}\n", mimetype="text/plain", status=500)
        else:
            raise DatabaseError(
                message="Failed to generate blocklist",
                table="blacklist_ips_with_auto_inactive",
            )


@fortinet_core_bp.route("/config", methods=["GET"])
def get_config():
    """
    Get FortiGate configuration information
    """
    try:
        config = {
            "external_blocklist_url": request.url_root.rstrip("/") + "/api/fortinet/blocklist",
            "update_interval": "hourly",
            "enabled": True,
            "api_version": "1.0",
            "last_updated": datetime.now().isoformat(),
        }

        return jsonify(
            {
                "success": True,
                "data": config,
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Error getting config: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to retrieve FortiGate configuration",
            cause=type(e).__name__,
        )

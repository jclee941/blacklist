"""
Fortinet API Threat Feed Operations
Handles threat feed generation and JSON connector formats
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app, Response
from core.auth.decorators import public
from core.auth.feed import feed_access_required
from core.exceptions import ValidationError, DatabaseError

logger = logging.getLogger(__name__)

fortinet_feed_bp = Blueprint("fortinet_feed", __name__)


@fortinet_feed_bp.route("/threat-feed", methods=["GET"])
@public
@feed_access_required
def get_threat_feed():
    """
    FortiGate Push API - Threat Feed Format (JSON)
    Compatible with FortiGate 7.2+ Push API method.
    """
    command = request.args.get("command", "snapshot").lower()
    output_format = request.args.get("format", "json").lower()

    if command not in ["snapshot", "add", "remove"]:
        raise ValidationError(
            message=f"Invalid command: {command}. Must be 'snapshot', 'add', or 'remove'",
            field="command",
            details={
                "provided_value": command,
                "allowed_values": ["snapshot", "add", "remove"],
            },
        )

    if output_format not in ["json", "text"]:
        raise ValidationError(
            message=f"Invalid format: {output_format}. Must be 'json' or 'text'",
            field="format",
            details={
                "provided_value": output_format,
                "allowed_values": ["json", "text"],
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

        if output_format == "text":
            blocklist_text = "\n".join(ip_list)
            return Response(
                blocklist_text,
                mimetype="text/plain",
                headers={
                    "X-Total-IPs": str(len(ip_list)),
                    "X-Generated-At": datetime.now().isoformat(),
                    "X-Request-ID": g.request_id,
                },
            )

        threat_feed_json = {"commands": [{"name": "ip", "command": command, "entries": ip_list}]}

        return (
            jsonify(threat_feed_json),
            200,
            {
                "X-Total-IPs": str(len(ip_list)),
                "X-Generated-At": datetime.now().isoformat(),
                "X-Request-ID": g.request_id,
                "Content-Type": "application/json",
            },
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error generating threat feed: {e}", exc_info=True)
        if output_format == "text":
            return Response("# Error: feed unavailable\n", mimetype="text/plain", status=500)
        else:
            raise DatabaseError(
                message="Failed to generate threat feed",
                query="fortinet_threat_feed",
            )


@fortinet_feed_bp.route("/json-connector", methods=["GET"])
@public
@feed_access_required
def get_json_connector():
    """
    FortiGate JSON Connector Format with metadata
    """
    limit = request.args.get("limit", type=int)
    risk_level = request.args.get("risk_level", "").lower()
    country_filter = request.args.get("country", "").upper()

    if limit is not None and (limit < 1 or limit > 10000):
        raise ValidationError(
            message="Limit must be between 1 and 10000",
            field="limit",
            details={"provided_value": limit, "allowed_range": "1-10000"},
        )

    if risk_level and risk_level not in ["high", "medium", "low"]:
        raise ValidationError(
            message=f"Invalid risk_level: {risk_level}. Must be 'high', 'medium', or 'low'",
            field="risk_level",
            details={
                "provided_value": risk_level,
                "allowed_values": ["high", "medium", "low"],
            },
        )

    db_service = current_app.extensions["db_service"]

    try:
        query = """
            SELECT
                b.ip_address, b.country, b.reason, b.confidence_level,
                b.detection_date, b.updated_at
            FROM blacklist_ips_with_auto_inactive b
            WHERE b.is_active = true
              AND b.ip_address NOT IN (
                  SELECT ip_address FROM whitelist_ips WHERE is_active = true
              )
        """
        params = []

        if risk_level == "high":
            query += " AND b.confidence_level >= 80"
        elif risk_level == "medium":
            query += " AND b.confidence_level >= 50 AND b.confidence_level < 80"
        elif risk_level == "low":
            query += " AND b.confidence_level < 50"

        if country_filter:
            query += " AND b.country = %s"
            params.append(country_filter)

        query += " ORDER BY b.confidence_level DESC, b.detection_date DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        rows = db_service.query(query, tuple(params) if params else None)

        total_query = """
            SELECT COUNT(*) as count
            FROM blacklist_ips_with_auto_inactive
            WHERE is_active = true
              AND ip_address NOT IN (
                  SELECT ip_address FROM whitelist_ips WHERE is_active = true
              )
        """
        total_count = db_service.query(total_query)[0]["count"]

        results = []
        for row in rows:
            confidence = row["confidence_level"] or 0
            if confidence >= 80:
                risk = "high"
            elif confidence >= 50:
                risk = "medium"
            else:
                risk = "low"

            results.append(
                {
                    "ip": row["ip_address"],
                    "country": row["country"] or "unknown",
                    "risk_level": risk,
                    "reason": row["reason"] or "unspecified",
                    "confidence": confidence,
                    "first_seen": row["detection_date"].isoformat() if row["detection_date"] else None,
                    "last_updated": row["updated_at"].isoformat() if row["updated_at"] else None,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "results": results,
                    "metadata": {
                        "total": total_count,
                        "filtered": len(results),
                        "generated_at": datetime.now().isoformat(),
                        "version": "1.0",
                        "filters": {
                            "risk_level": risk_level or "all",
                            "country": country_filter or "all",
                            "limit": limit or "none",
                        },
                    },
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error generating JSON connector data: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to generate FortiGate JSON connector data",
            query="fortinet_json_connector",
        )

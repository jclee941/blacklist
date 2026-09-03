#!/usr/bin/env python3
"""
Batch IP Operations
Routes: /blacklist/batch/add, /blacklist/batch/remove, /blacklist/batch/update
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import logging

import psycopg2
import redis
from core.utils.rate_limit import rate_limit
from core.services.database_lease import connection_lease
from core.utils.input_security import parse_ip_batch
from core.utils.ip_cache import invalidate_ip_caches
from core.exceptions import APIError, BadRequestError

logger = logging.getLogger(__name__)


blacklist_batch_bp = Blueprint("blacklist_batch", __name__)


@blacklist_batch_bp.route("/blacklist/batch/add", methods=["POST"])
@rate_limit("10 per hour; 2 per minute")  # Resource-intensive batch operation
def batch_add_blacklist():
    """Batch add multiple IPs to blacklist"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        data = request.get_json() or {}
        ips = parse_ip_batch(data.get("ips", []))
        reason = data.get("reason", "Batch import")
        country = data.get("country", "UNKNOWN")

        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise BadRequestError("Invalid batch reason", details={"field": "reason"})
        if not isinstance(country, str) or not country.strip() or len(country) > 10:
            raise BadRequestError("Invalid batch country", details={"field": "country"})

        # Batch insert valid IPs
        added_count = 0
        duplicate_count = 0
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            for ip in ips:
                cursor.execute(
                    """
                    INSERT INTO blacklist_ips
                    (
                        ip_address, source, country, reason,
                        detection_date, last_seen, detection_count,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, CURRENT_DATE, NOW(), 1, NOW(), NOW())
                    ON CONFLICT (ip_address, source) DO NOTHING
                    """,
                    (ip, "BATCH", country.strip().upper(), reason.strip()),
                )
                if cursor.rowcount > 0:
                    added_count += 1
                else:
                    duplicate_count += 1

            conn.commit()
            cursor.close()
        invalidate_ip_caches(ips)

        logger.info(f"✅ Batch added {added_count} IPs to blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch operation completed",
                "summary": {
                    "total_requested": len(ips),
                    "added": added_count,
                    "duplicates": duplicate_count,
                    "invalid": 0,
                },
                "invalid_ips": [],
                "timestamp": datetime.now().isoformat(),
            }
        )

    except APIError:
        raise
    except (psycopg2.Error, redis.RedisError):
        logger.exception("Batch add failed")
        return jsonify(
            {"success": False, "error": "Batch operation failed", "timestamp": datetime.now().isoformat()}
        ), 500


@blacklist_batch_bp.route("/blacklist/batch/remove", methods=["POST"])
@rate_limit("10 per hour; 2 per minute")  # Resource-intensive batch operation
def batch_remove_blacklist():
    """Batch remove multiple IPs from blacklist"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        data = request.get_json() or {}
        ips = parse_ip_batch(data.get("ips", []))

        removed_count = 0
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            for ip in ips:
                cursor.execute("DELETE FROM blacklist_ips WHERE ip_address = %s", (ip,))
                removed_count += cursor.rowcount

            conn.commit()
            cursor.close()
        invalidate_ip_caches(ips)

        logger.info(f"✅ Batch removed {removed_count} IPs from blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch remove completed",
                "summary": {"total_requested": len(ips), "removed": removed_count},
                "timestamp": datetime.now().isoformat(),
            }
        )

    except APIError:
        raise
    except (psycopg2.Error, redis.RedisError):
        logger.exception("Batch remove failed")
        return jsonify(
            {"success": False, "error": "Batch operation failed", "timestamp": datetime.now().isoformat()}
        ), 500


@blacklist_batch_bp.route("/blacklist/batch/update", methods=["POST"])
@rate_limit("10 per hour; 2 per minute")  # Resource-intensive batch operation
def batch_update_blacklist():
    """Batch update multiple blacklist entries"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        data = request.get_json() or {}
        ips = parse_ip_batch(data.get("ips", []))
        reason = data.get("reason")
        country = data.get("country")

        if not reason and not country:
            return jsonify(
                {"success": False, "error": "At least one field (reason or country) is required for update"}
            ), 400
        if reason is not None and (not isinstance(reason, str) or not reason.strip() or len(reason) > 1000):
            raise BadRequestError("Invalid batch reason", details={"field": "reason"})
        if country is not None and (not isinstance(country, str) or not country.strip() or len(country) > 10):
            raise BadRequestError("Invalid batch country", details={"field": "country"})

        updated_count = 0
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            for ip in ips:
                update_fields = []
                update_values = []

                if reason:
                    update_fields.append("reason = %s")
                    update_values.append(reason.strip())
                if country:
                    update_fields.append("country = %s")
                    update_values.append(country.strip().upper())

                update_fields.append("updated_at = NOW()")
                update_values.append(ip)
                query = f"UPDATE blacklist_ips SET {', '.join(update_fields)} WHERE ip_address = %s"
                cursor.execute(query, tuple(update_values))
                updated_count += cursor.rowcount

            conn.commit()
            cursor.close()
        invalidate_ip_caches(ips)

        logger.info(f"✅ Batch updated {updated_count} IPs in blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch update completed",
                "summary": {"total_requested": len(ips), "updated": updated_count},
                "timestamp": datetime.now().isoformat(),
            }
        )

    except APIError:
        raise
    except (psycopg2.Error, redis.RedisError):
        logger.exception("Batch update failed")
        return jsonify(
            {"success": False, "error": "Batch operation failed", "timestamp": datetime.now().isoformat()}
        ), 500

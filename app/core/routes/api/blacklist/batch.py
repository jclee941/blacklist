#!/usr/bin/env python3
"""
Batch IP Operations
Routes: /blacklist/batch/add, /blacklist/batch/remove, /blacklist/batch/update
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import logging
import re

from core.utils.rate_limit import rate_limit

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
        ips = data.get("ips", [])
        reason = data.get("reason", "Batch import")
        country = data.get("country", "UNKNOWN")

        if not ips or not isinstance(ips, list):
            return jsonify({"success": False, "error": "IPs list is required"}), 400

        # Validate all IPs
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        valid_ips = []
        invalid_ips = []

        for ip in ips:
            if re.match(ip_pattern, str(ip).strip()):
                octets = str(ip).strip().split(".")
                if all(0 <= int(octet) <= 255 for octet in octets):
                    valid_ips.append(str(ip).strip())
                else:
                    invalid_ips.append(ip)
            else:
                invalid_ips.append(ip)

        # Batch insert valid IPs
        conn = db_service.get_connection()
        cursor = conn.cursor()

        added_count = 0
        duplicate_count = 0

        for ip in valid_ips:
            try:
                cursor.execute(
                    """
                    INSERT INTO blacklist_ips
                    (
                        ip_address, source, country, reason,
                        detection_date, last_seen, detection_count,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, CURRENT_DATE, NOW(), 1, NOW(), NOW())
                    ON CONFLICT (ip_address) DO NOTHING
                """,
                    (ip, "BATCH", country, reason),
                )
                if cursor.rowcount > 0:
                    added_count += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                logger.warning(f"Failed to add IP {ip}: {e}")

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Batch added {added_count} IPs to blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch operation completed",
                "summary": {
                    "total_requested": len(ips),
                    "added": added_count,
                    "duplicates": duplicate_count,
                    "invalid": len(invalid_ips),
                },
                "invalid_ips": invalid_ips,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Batch add failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@blacklist_batch_bp.route("/blacklist/batch/remove", methods=["POST"])
@rate_limit("10 per hour; 2 per minute")  # Resource-intensive batch operation
def batch_remove_blacklist():
    """Batch remove multiple IPs from blacklist"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        data = request.get_json() or {}
        ips = data.get("ips", [])

        if not ips or not isinstance(ips, list):
            return jsonify({"success": False, "error": "IPs list is required"}), 400

        conn = db_service.get_connection()
        cursor = conn.cursor()

        removed_count = 0
        for ip in ips:
            try:
                cursor.execute("DELETE FROM blacklist_ips WHERE ip_address = %s", (str(ip).strip(),))
                removed_count += cursor.rowcount
            except Exception as e:
                logger.warning(f"Failed to remove IP {ip}: {e}")

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Batch removed {removed_count} IPs from blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch remove completed",
                "summary": {"total_requested": len(ips), "removed": removed_count},
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Batch remove failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@blacklist_batch_bp.route("/blacklist/batch/update", methods=["POST"])
@rate_limit("10 per hour; 2 per minute")  # Resource-intensive batch operation
def batch_update_blacklist():
    """Batch update multiple blacklist entries"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        data = request.get_json() or {}
        ips = data.get("ips", [])
        reason = data.get("reason")
        country = data.get("country")

        if not ips or not isinstance(ips, list):
            return jsonify({"success": False, "error": "IPs list is required"}), 400

        if not reason and not country:
            return jsonify(
                {"success": False, "error": "At least one field (reason or country) is required for update"}
            ), 400

        conn = db_service.get_connection()
        cursor = conn.cursor()

        updated_count = 0
        for ip in ips:
            try:
                # Build dynamic UPDATE query
                update_fields = []
                update_values = []

                if reason:
                    update_fields.append("reason = %s")
                    update_values.append(reason)
                if country:
                    update_fields.append("country = %s")
                    update_values.append(country)

                update_fields.append("updated_at = NOW()")
                update_values.append(str(ip).strip())

                query = f"UPDATE blacklist_ips SET {', '.join(update_fields)} WHERE ip_address = %s"
                cursor.execute(query, tuple(update_values))
                updated_count += cursor.rowcount
            except Exception as e:
                logger.warning(f"Failed to update IP {ip}: {e}")

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Batch updated {updated_count} IPs in blacklist")

        return jsonify(
            {
                "success": True,
                "message": "Batch update completed",
                "summary": {"total_requested": len(ips), "updated": updated_count},
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Batch update failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500

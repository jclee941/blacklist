"""
Dashboard API routes

Provides simplified endpoints for frontend dashboard:
- /api/stats: General statistics for dashboard cards
- /api/status: System status information
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
from psycopg2.extras import RealDictCursor
from ...services.database_lease import connection_lease

dashboard_bp = Blueprint("dashboard_api", __name__)


def get_db_connection():
    """Get database connection"""
    try:
        # Correct key is 'db_service'
        db_service = current_app.extensions.get("db_service")
        if db_service:
            return connection_lease(db_service)
    except Exception as e:
        current_app.logger.error(f"Failed to get db_service: {e}")
        pass

    # Fallback removed - we should rely on the service
    raise RuntimeError("Database service not available")


@dashboard_bp.route("/stats", methods=["GET"])
def get_dashboard_stats():
    """
    Get dashboard statistics

    Returns:
        - total_ips: Total IP addresses
        - active_ips: Active blacklisted IPs
        - recent_additions: IPs added in last 24 hours
        - whitelisted_ips: Whitelisted IP count
        - last_update: Last update timestamp
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive")
            row = cursor.fetchone()
            total_ips = row["count"] if row else 0
            cursor.execute("SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive WHERE is_active = true")
            row = cursor.fetchone()
            active_ips = row["count"] if row else 0
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive
                WHERE last_seen >= CURRENT_DATE - INTERVAL '1 day'
                """
            )
            row = cursor.fetchone()
            recent_additions = row["count"] if row else 0
            cursor.execute("SELECT COUNT(*) as count FROM whitelist_ips")
            row = cursor.fetchone()
            whitelisted_ips = row["count"] if row else 0
            cursor.execute(
                """
                SELECT MAX(last_seen) as last_update
                FROM blacklist_ips_with_auto_inactive
                """
            )
            last_update_row = cursor.fetchone()
            last_update = (
                last_update_row["last_update"].isoformat()
                if last_update_row and last_update_row["last_update"]
                else datetime.now().isoformat()
            )
            cursor.execute(
                """
                SELECT COALESCE(data_source, 'UNKNOWN') as source, COUNT(*) as count
                FROM blacklist_ips_with_auto_inactive
                WHERE is_active = true
                GROUP BY data_source
                """
            )
            by_source = {row["source"]: row["count"] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT COALESCE(country, 'UNKNOWN') as country, COUNT(*) as count
                FROM blacklist_ips_with_auto_inactive
                WHERE is_active = true
                GROUP BY country
                """
            )
            by_country = {row["country"]: row["count"] for row in cursor.fetchall()}
            cursor.execute(
                """
                SELECT COALESCE(source, 'UNKNOWN') as reason, COUNT(*) as count
                FROM blacklist_ips_with_auto_inactive
                WHERE is_active = true
                GROUP BY source
                """
            )
            by_reason = {row["reason"]: row["count"] for row in cursor.fetchall()}
            cursor.close()
        return jsonify(
            {
                "success": True,
                "data": {
                    "total_ips": total_ips,
                    "active_ips": active_ips,
                    "recent_additions": recent_additions,
                    "whitelisted_ips": whitelisted_ips,
                    "last_update": last_update,
                    "by_source": by_source,
                    "by_country": by_country,
                    "by_reason": by_reason,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Dashboard stats failed: {e}")
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "data": {
                    "total_ips": 0,
                    "active_ips": 0,
                    "recent_additions": 0,
                    "whitelisted_ips": 0,
                    "last_update": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        ), 200


@dashboard_bp.route("/status", methods=["GET"])
def get_system_status():
    """
    Get system status

    Returns:
        - service: API server status
        - components: Database and other component status
        - collection: Collection service status
    """
    try:
        db_service = current_app.extensions["db_service"]
        with connection_lease(db_service) as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT 1")
            cursor.close()
        db_status = "healthy"
    except Exception as e:
        current_app.logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    # Get collection status (simplified - assumes enabled by default)
    collection_enabled = True

    return jsonify(
        {
            "success": True,
            "data": {
                "service": {"status": "healthy"},
                "components": {"database": {"status": db_status}},
                "collection": {"collection_enabled": collection_enabled},
            },
            "timestamp": datetime.now().isoformat(),
        }
    )

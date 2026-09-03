"""
Collection API History Operations
Handles collection history and statistics
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, g, current_app
from core.exceptions import ValidationError, DatabaseError
from core.services.database_lease import connection_lease
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

collection_history_bp = Blueprint("collection_history", __name__)


@collection_history_bp.route("/history", methods=["GET"])
def get_collection_history():
    """
    Get collection history for all sources
    """
    # Get and validate parameters
    source = request.args.get("source", "").upper()
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", request.args.get("limit", "50")))
    except (TypeError, ValueError):
        raise ValidationError(
            message="Page and per_page must be valid integers",
            field="page/per_page",
        ) from None

    if page < 1:
        raise ValidationError(
            message="Page must be greater than or equal to 1",
            field="page",
            details={"provided_value": page},
        )
    if per_page < 1 or per_page > 200:
        raise ValidationError(
            message="Per-page limit must be between 1 and 200",
            field="per_page",
            details={"provided_value": per_page, "allowed_range": "1-200"},
        )

    # Use dependency injection via app.extensions
    db_service = current_app.extensions["db_service"]

    try:
        # Build query
        query = """
            SELECT
                id,
                service_name,
                collection_date,
                items_collected,
                success,
                execution_time_ms / 1000.0 as duration_seconds,
                error_message,
                details as metadata
            FROM collection_history
        """

        params = []
        if source:
            query += " WHERE service_name = %s"
            params.append(source)

        query += " ORDER BY collection_date DESC LIMIT %s OFFSET %s"
        params.extend((per_page, (page - 1) * per_page))

        # Execute query
        rows = db_service.query(query, tuple(params))

        # Format results
        history = []
        for row in rows:
            metadata = row["metadata"] or {}
            history.append(
                {
                    "id": row["id"],
                    "service_name": row["service_name"],
                    "collection_date": row["collection_date"].isoformat() if row["collection_date"] else None,
                    "items_collected": row["items_collected"],
                    "new_count": metadata.get("new_count", 0) if isinstance(metadata, dict) else 0,
                    "updated_count": metadata.get("updated_count", 0) if isinstance(metadata, dict) else 0,
                    "success": row["success"],
                    "duration_seconds": float(row["duration_seconds"]) if row["duration_seconds"] else None,
                    "error_message": row["error_message"],
                    "metadata": metadata,
                }
            )

        count_query = "SELECT COUNT(*) as total FROM collection_history"
        count_params = []
        if source:
            count_query += " WHERE service_name = %s"
            count_params.append(source)
        count_result = db_service.query(count_query, tuple(count_params))
        total_count = count_result[0]["total"] if count_result else 0

        return jsonify(
            {
                "success": True,
                "data": {
                    "history": history,
                    "total": total_count,
                    "filtered": len(history),
                    "page": page,
                    "per_page": per_page,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        )

    except Exception as e:
        logger.error(f"Error getting collection history: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve collection history",
            table="collection_history",
        )


@collection_history_bp.route("/statistics", methods=["GET"])
def get_collection_stats():
    """
    Get collection statistics (Today, Week, Month, Source breakdown)
    Matches frontend expectation: /api/collection/statistics
    """
    # Use dependency injection via app.extensions
    db_service = current_app.extensions["db_service"]

    try:
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        with connection_lease(db_service) as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT COALESCE(SUM(items_collected), 0) as today_collected
                FROM collection_history
                WHERE DATE(collection_date) = %s AND success = true
                """,
                (today,),
            )
            today_result = cursor.fetchone()
            today_collected = today_result["today_collected"] if today_result else 0
            cursor.execute(
                """
                SELECT COALESCE(SUM(items_collected), 0) as week_collected
                FROM collection_history
                WHERE DATE(collection_date) >= %s AND success = true
                """,
                (week_ago,),
            )
            week_result = cursor.fetchone()
            week_collected = week_result["week_collected"] if week_result else 0
            cursor.execute(
                """
                SELECT COALESCE(SUM(items_collected), 0) as month_collected
                FROM collection_history
                WHERE DATE(collection_date) >= %s AND success = true
                """,
                (month_ago,),
            )
            month_result = cursor.fetchone()
            month_collected = month_result["month_collected"] if month_result else 0
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_ips,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_ips
                FROM blacklist_ips
                """
            )
            ip_counts = cursor.fetchone()
            current_total_ips = ip_counts["total_ips"] if ip_counts else 0
            current_active_ips = ip_counts["active_ips"] if ip_counts else 0
            cursor.execute(
                """
                SELECT
                    service_name as source_name,
                    COUNT(*) as total_collections,
                    COALESCE(SUM(items_collected), 0) as cumulative_collected,
                    MAX(collection_date) as last_collection,
                    AVG(execution_time_ms) / 1000.0 as avg_duration,
                    COUNT(CASE WHEN success = true THEN 1 END) as success_count
                FROM collection_history
                GROUP BY service_name
                ORDER BY cumulative_collected DESC
                """
            )
            source_rows = cursor.fetchall()
            cursor.close()

        sources = {}
        for row in source_rows:
            total = row["total_collections"]
            success = row["success_count"]
            success_rate = (success / total * 100) if total > 0 else 0

            sources[row["source_name"]] = {
                "total_collections": total,
                "cumulative_collected": row["cumulative_collected"],
                "total_items": row["cumulative_collected"],
                "last_collection": (row["last_collection"].isoformat() if row["last_collection"] else None),
                "avg_duration": float(row["avg_duration"]) if row["avg_duration"] else 0,
                "success_rate": float(success_rate),
            }

        return jsonify(
            {
                "success": True,
                "data": {
                    "today_collected": today_collected,
                    "week_collected": week_collected,
                    "month_collected": month_collected,
                    "current_total_ips": current_total_ips,
                    "current_active_ips": current_active_ips,
                    "sources": sources,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        )

    except Exception as e:
        logger.error(f"Error getting collection stats: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to retrieve collection statistics",
            table="collection_history",
        )

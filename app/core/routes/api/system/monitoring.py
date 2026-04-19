"""Monitoring and statistics endpoints for the shared system API blueprint."""

from datetime import timedelta

from . import common


@common.api_bp.route("/monitoring/dashboard", methods=["GET"])
def get_monitoring_dashboard():
    """
    모니터링 대시보드 데이터 API (Phase 1.4: Standardized Error Handling)

    GET /api/monitoring/dashboard

    Returns:
        {
            "success": True,
            "data": {
                "total_ips": 1234,
                "active_ips": 1234,
                "recent_collections": [...]
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Database query failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=common.RealDictCursor)

        try:
            cursor.execute("SELECT COUNT(*) as total_ips FROM blacklist_ips_with_auto_inactive")
            total_result = cursor.fetchone()
            total_ips = total_result["total_ips"] if total_result else 0

            cursor.execute("SELECT COUNT(*) as active_ips FROM blacklist_ips_with_auto_inactive WHERE is_active = true")
            active_result = cursor.fetchone()
            active_ips = active_result["active_ips"] if active_result else 0

            cursor.execute(
                """
                SELECT service_name, collection_date, items_collected, success
                FROM collection_history
                ORDER BY collection_date DESC
                LIMIT 5
            """
            )
            recent_collections = cursor.fetchall()

        finally:
            cursor.close()
            db_service.return_connection(conn)

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "total_ips": total_ips,
                    "active_ips": active_ips,
                    "recent_collections": [
                        {
                            "service": row["service_name"],
                            "date": row["collection_date"].isoformat() if row["collection_date"] else None,
                            "items": row["items_collected"],
                            "success": row["success"],
                        }
                        for row in recent_collections
                    ],
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Monitoring dashboard error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to retrieve monitoring dashboard data",
            details={"error_type": type(e).__name__},
        )


@common.api_bp.route("/system-stats", methods=["GET"])
def get_system_stats():
    """
    시스템 통계 (Phase 1.4: Standardized Error Handling)

    GET /api/system-stats

    Returns:
        {
            "success": True,
            "data": {
                "total_ips": 1234,
                "active_ips": 1234,
                "expired_ips": 0,
                "ip_status": {...},
                "source_distribution": {...},
                "last_update": "...",
                "monthly_data": []
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Database query failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=common.RealDictCursor)

        try:
            cursor.execute("SELECT COUNT(*) as total_ips FROM blacklist_ips_with_auto_inactive")
            total_result = cursor.fetchone()
            total_ips = total_result["total_ips"] if total_result else 0

            cursor.execute("SELECT COUNT(*) as active_ips FROM blacklist_ips_with_auto_inactive WHERE is_active = true")
            active_result = cursor.fetchone()
            active_ips = active_result["active_ips"] if active_result else 0

            cursor.execute(
                "SELECT COUNT(*) as expired_ips FROM blacklist_ips_with_auto_inactive WHERE is_active = false"
            )
            expired_result = cursor.fetchone()
            expired_ips = expired_result["expired_ips"] if expired_result else 0

            cursor.execute(
                """
                 SELECT data_source, COUNT(*) as count,
                        ROUND(
                            COUNT(*) * 100.0 / NULLIF(
                                (SELECT COUNT(*) FROM blacklist_ips_with_auto_inactive), 0
                            ), 1
                        ) as percentage
                 FROM blacklist_ips_with_auto_inactive
                WHERE data_source IS NOT NULL
                GROUP BY data_source
                ORDER BY count DESC
            """
            )
            source_results = cursor.fetchall()

            source_distribution = {}
            for row in source_results:
                source_distribution[row["data_source"]] = {
                    "count": row["count"],
                    "percentage": float(row["percentage"]) if row["percentage"] else 0,
                }

            cursor.execute("SELECT MAX(created_at) as last_update FROM blacklist_ips_with_auto_inactive")
            update_result = cursor.fetchone()
            last_update = (
                update_result["last_update"].isoformat()
                if update_result and update_result["last_update"]
                else "데이터 없음"
            )

        finally:
            cursor.close()
            db_service.return_connection(conn)

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "total_ips": total_ips,
                    "active_ips": active_ips,
                    "expired_ips": expired_ips,
                    "ip_status": {
                        "total": total_ips,
                        "active": active_ips,
                        "expired": expired_ips,
                        "percentage_active": round((active_ips / total_ips * 100) if total_ips > 0 else 0, 1),
                    },
                    "source_distribution": source_distribution,
                    "last_update": last_update,
                    "monthly_data": [],
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"System stats error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to retrieve system statistics",
            details={"error_type": type(e).__name__},
        )


@common.api_bp.route("/chart/data", methods=["GET"])
def get_chart_data():
    """
    차트용 데이터 (Phase 1.4: Standardized Error Handling)

    GET /api/chart/data

    Returns:
        {
            "success": True,
            "data": {
                "daily_collection": [...]
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        DatabaseError: Database query failed
    """
    try:
        db_service = common.current_app.extensions["db_service"]
        conn = db_service.get_connection()
        cursor = conn.cursor(cursor_factory=common.RealDictCursor)

        try:
            cursor.execute(
                """
                SELECT DATE(collection_date) as date,
                       COALESCE(SUM(items_collected), 0) as collected
                FROM collection_history
                WHERE collection_date >= %s AND success = true
                GROUP BY DATE(collection_date)
                ORDER BY date DESC
                LIMIT 30
            """,
                (common.datetime.now() - timedelta(days=30),),
            )

            daily_data = []
            for row in cursor.fetchall():
                daily_data.append(
                    {
                        "date": row["date"].isoformat() if row["date"] else "",
                        "collected": row["collected"],
                    }
                )

        finally:
            cursor.close()
            db_service.return_connection(conn)

        return common.jsonify(
            {
                "success": True,
                "data": {"daily_collection": daily_data},
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Chart data error: {e}", exc_info=True)
        raise common.database_error_cls(
            message="Failed to retrieve chart data",
            details={"error_type": type(e).__name__},
        )

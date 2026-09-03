"""
API Routes
웹 인터페이스용 API 엔드포인트
"""

from flask import current_app, jsonify, request
import logging
from datetime import datetime
from . import web_bp
from .blacklist_api_routes import api_blacklist_export, api_blacklist_export_raw, api_blacklist_list
from ...services.database_lease import connection_lease

BLACKLIST_API_HANDLERS = (api_blacklist_list, api_blacklist_export, api_blacklist_export_raw)

logger = logging.getLogger(__name__)


@web_bp.route("/favicon.ico")
def favicon():
    """파비콘 라우트 - 파비콘 없음 (404 반환)"""
    return "", 404


@web_bp.route("/api/search/<ip>", methods=["GET"])
def api_search_ip(ip):
    """IP 검색 API"""
    try:
        db_service = current_app.extensions["db_service"]

        # IP 주소로 블랙리스트 검색
        with connection_lease(db_service) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        ip_address, source, reason, confidence_level,
                        detection_count, is_active, last_seen, created_at
                    FROM blacklist_ips
                    WHERE ip_address = %s
                    ORDER BY created_at DESC
                """,
                    (ip,),
                )
                results = cur.fetchall()

        if results:
            ip_data = []
            for row in results:
                ip_data.append(
                    {
                        "ip_address": row[0],
                        "source": row[1],
                        "reason": row[2],
                        "confidence_level": row[3],
                        "detection_count": row[4],
                        "is_active": row[5],
                        "last_seen": row[6].isoformat() if row[6] else None,
                        "created_at": row[7].isoformat() if row[7] else None,
                    }
                )

            return jsonify({"success": True, "found": True, "data": ip_data})
        else:
            return jsonify(
                {
                    "success": True,
                    "found": False,
                    "message": "IP 주소를 찾을 수 없습니다.",
                }
            )

    except Exception as e:
        logger.error(f"Search IP API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/web-stats", methods=["GET"])
def api_stats():
    """통계 정보 API"""
    try:
        db_service = current_app.extensions["db_service"]

        with connection_lease(db_service) as conn:
            with conn.cursor() as cur:
                # 기본 통계
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN is_active THEN 1 END) as active,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as today,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as week
                    FROM blacklist_ips
                """
                )
                stats = cur.fetchone()
                if stats is None:
                    raise RuntimeError("Blacklist statistics query returned no row")

                # 소스별 통계
                cur.execute(
                    """
                    SELECT data_source, COUNT(*) as count
                    FROM blacklist_ips
                    WHERE is_active = true
                    GROUP BY data_source
                    ORDER BY count DESC
                """
                )
                source_stats = cur.fetchall()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_ips": stats[0],
                    "active_ips": stats[1],
                    "new_today": stats[2],
                    "new_this_week": stats[3],
                },
                "source_breakdown": [{"source": row[0], "count": row[1]} for row in source_stats],
                "last_updated": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/collection/status", methods=["GET"])
def api_collection_status():
    """수집 상태 API"""
    try:
        collection_service = current_app.extensions["collection_service"]

        status = collection_service.get_collection_status()
        return jsonify({"success": True, **status})

    except Exception as e:
        logger.error(f"Collection status API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/collection/stats", methods=["GET"])
def api_collection_stats():
    """수집 통계 API"""
    try:
        db_service = current_app.extensions["db_service"]

        with connection_lease(db_service) as conn:
            with conn.cursor() as cur:
                # 최근 수집 통계
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_collections,
                        COUNT(CASE WHEN success THEN 1 END) as successful_collections,
                        AVG(execution_time_ms) as avg_execution_time,
                        SUM(items_collected) as total_items_collected
                    FROM collection_history
                    WHERE collection_date > NOW() - INTERVAL '30 days'
                """
                )
                stats = cur.fetchone()
                if stats is None:
                    raise RuntimeError("Collection statistics query returned no row")

        return jsonify(
            {
                "success": True,
                "collection_stats": {
                    "total_collections": stats[0] or 0,
                    "successful_collections": stats[1] or 0,
                    "success_rate": round((stats[1] / stats[0] * 100) if stats[0] > 0 else 0, 1),
                    "avg_execution_time_ms": round(float(stats[2]) if stats[2] else 0, 1),
                    "total_items_collected": stats[3] or 0,
                },
                "period": "Last 30 days",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Collection stats API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/chart-data", methods=["GET"])
def api_chart_data():
    """차트 데이터 API"""
    try:
        db_service = current_app.extensions["db_service"]

        chart_type = request.args.get("type", "daily")

        with connection_lease(db_service) as conn:
            with conn.cursor() as cur:
                if chart_type == "daily":
                    # 일별 추가된 IP 수
                    cur.execute(
                        """
                        SELECT
                            DATE(created_at) as date,
                            COUNT(*) as count
                        FROM blacklist_ips
                        WHERE created_at > NOW() - INTERVAL '30 days'
                        GROUP BY DATE(created_at)
                        ORDER BY date
                    """
                    )
                elif chart_type == "source":
                    # 소스별 분포
                    cur.execute(
                        """
                        SELECT
                            data_source,
                            COUNT(*) as count
                        FROM blacklist_ips
                        WHERE is_active = true
                        GROUP BY data_source
                        ORDER BY count DESC
                    """
                    )

                results = cur.fetchall()

        chart_data = [{"label": row[0], "value": row[1]} for row in results]

        return jsonify(
            {
                "success": True,
                "chart_type": chart_type,
                "data": chart_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Chart data API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/connection/status", methods=["GET"])
def api_connection_status():
    """연결 상태 API"""
    try:
        db_service = current_app.extensions["db_service"]

        status = db_service.get_connection_status()

        # 웹 페이지가 기대하는 필드 추가
        response = {
            "success": True,
            "database_connected": status.get("status") == "healthy",
            "redis_connected": True,  # Redis는 기본적으로 연결된 것으로 가정
            **status,
        }

        return jsonify(response)
    except Exception as e:
        logger.error(f"Connection status API error: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "database_connected": False,
                    "redis_connected": False,
                    "error": str(e),
                }
            ),
            500,
        )

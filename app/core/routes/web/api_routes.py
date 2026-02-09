"""
API Routes
웹 인터페이스용 API 엔드포인트
"""

from flask import jsonify, request, send_file, current_app
import logging
from datetime import datetime
import csv
import io
from . import web_bp

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
        with db_service.get_connection() as conn:
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

        with db_service.get_connection() as conn:
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

        with db_service.get_connection() as conn:
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


@web_bp.route("/api/blacklist/list", methods=["GET"])
def api_blacklist_list():
    """블랙리스트 목록 API"""
    try:
        db_service = current_app.extensions["db_service"]

        # 페이징 파라미터
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        offset = (page - 1) * per_page

        # 필터 파라미터
        source = request.args.get("source")
        active_only = request.args.get("active_only", "true").lower() == "true"

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
                # 동적 쿼리 구성
                where_conditions = []
                params = []

                if active_only:
                    where_conditions.append("is_active = %s")
                    params.append(True)

                if source:
                    where_conditions.append("source = %s")
                    params.append(source)

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # 데이터 조회 - detection_date, removal_date, country 필드 추가 (parameterized query)
                query = f"""
                    SELECT
                        ip_address, source, country, detection_date, removal_date, reason,
                        confidence_level, detection_count, is_active, last_seen, created_at
                    FROM blacklist_ips
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """
                cur.execute(query, params + [per_page, offset])
                results = cur.fetchall()

                # 전체 레코드 수 (parameterized query)
                count_query = f"SELECT COUNT(*) FROM blacklist_ips {where_clause}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()[0]

        # 응답 데이터 구성 - category 필드 제거
        blacklist_data = []
        for row in results:
            blacklist_data.append(
                {
                    "ip_address": row[0],
                    "source": row[1],
                    "country": row[2],
                    "detection_date": row[3].isoformat() if row[3] else None,
                    "removal_date": row[4].isoformat() if row[4] else None,
                    "reason": row[5],
                    "confidence_level": row[6],
                    "detection_count": row[7],
                    "is_active": row[8],
                    "last_seen": row[9].isoformat() if row[9] else None,
                    "created_at": row[10].isoformat() if row[10] else None,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": blacklist_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "pages": (total_count + per_page - 1) // per_page,
                },
                "filters": {"source": source, "active_only": active_only},
            }
        )

    except Exception as e:
        logger.error(f"Blacklist list API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/blacklist/export", methods=["GET"])
def api_blacklist_export():
    """블랙리스트 데이터 CSV 내보내기 API"""
    try:
        db_service = current_app.extensions["db_service"]

        # 필터 파라미터
        source = request.args.get("source")
        active_only = request.args.get("active_only", "true").lower() == "true"

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
                # 동적 쿼리 구성
                where_conditions = []
                params = []

                if active_only:
                    where_conditions.append("is_active = %s")
                    params.append(True)

                if source:
                    where_conditions.append("source = %s")
                    params.append(source)

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # 모든 데이터 조회 - detection_date, removal_date, country 필드 추가 (parameterized query)
                export_query = f"""
                    SELECT
                        ip_address, source, country, detection_date, removal_date, reason,
                        confidence_level, detection_count, is_active, last_seen, created_at
                    FROM blacklist_ips
                    {where_clause}
                    ORDER BY created_at DESC
                """
                cur.execute(export_query, params)
                results = cur.fetchall()

        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)

        # 헤더 작성 - category 필드 제거
        writer.writerow(
            [
                "IP Address",
                "Source",
                "Country",
                "Detection Date",
                "Removal Date",
                "Reason",
                "Confidence Level",
                "Detection Count",
                "Is Active",
                "Last Seen",
                "Created At",
            ]
        )

        # 데이터 작성 - category 필드 제거
        for row in results:
            writer.writerow(
                [
                    row[0],  # ip_address
                    row[1],  # source
                    row[2] or "",  # country
                    row[3].strftime("%Y-%m-%d") if row[3] else "",  # detection_date
                    row[4].strftime("%Y-%m-%d") if row[4] else "",  # removal_date
                    row[5],  # reason
                    row[6],  # confidence_level
                    row[7],  # detection_count
                    "Yes" if row[8] else "No",  # is_active
                    row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else "",  # last_seen
                    (row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else ""),  # created_at
                ]
            )

        # CSV 응답 반환
        output.seek(0)
        csv_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"blacklist_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    except Exception as e:
        logger.error(f"Blacklist export API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/blacklist/export-raw", methods=["GET"])
def api_blacklist_export_raw():
    """블랙리스트 Raw 데이터 CSV 내보내기 API (수집 근거 포함)"""
    try:
        db_service = current_app.extensions["db_service"]

        # 필터 파라미터
        source = request.args.get("source")
        active_only = request.args.get("active_only", "true").lower() == "true"
        include_empty = request.args.get("include_empty", "false").lower() == "true"

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
                # 동적 쿼리 구성
                where_conditions = []
                params = []

                if active_only:
                    where_conditions.append("is_active = %s")
                    params.append(True)

                if source:
                    where_conditions.append("source = %s")
                    params.append(source)

                # raw_data가 있는 레코드만 (기본값)
                if not include_empty:
                    where_conditions.append("raw_data IS NOT NULL")
                    where_conditions.append("raw_data != '{}'::jsonb")

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # raw_data 포함 모든 데이터 조회
                # removal_date < CURRENT_DATE인 경우 자동으로 비활성 처리하여 조회 (오늘 해제 IP는 아직 활성)
                export_query = f"""
                    SELECT
                        ip_address, source, country, detection_date, removal_date, reason,
                        confidence_level, detection_count,
                        CASE
                            WHEN removal_date IS NOT NULL AND removal_date < CURRENT_DATE
                            THEN false
                            WHEN detection_date < CURRENT_DATE - INTERVAL '3 months'
                            THEN false
                            ELSE is_active
                        END as is_active,
                        last_seen, created_at, raw_data
                    FROM blacklist_ips
                    {where_clause}
                    ORDER BY created_at DESC
                """
                cur.execute(export_query, params)
                results = cur.fetchall()

        # CSV 데이터 생성
        output = io.StringIO()
        writer = csv.writer(output)

        # 헤더 작성 - raw_data 필드 추가
        writer.writerow(
            [
                "IP Address",
                "Source",
                "Country",
                "Detection Date",
                "Removal Date",
                "Reason",
                "Confidence Level",
                "Detection Count",
                "Is Active",
                "Last Seen",
                "Created At",
                "Raw Data (JSON)",
            ]
        )

        # 데이터 작성 - raw_data를 JSON 문자열로 변환
        import json

        for row in results:
            raw_data_str = ""
            if row[11]:  # raw_data
                try:
                    if isinstance(row[11], dict):
                        raw_data_str = json.dumps(row[11], ensure_ascii=False)
                    elif isinstance(row[11], str):
                        raw_data_str = row[11]
                    else:
                        raw_data_str = str(row[11])
                except Exception as e:
                    logger.debug("JSON serialization fallback for raw_data: %s", e)
                    raw_data_str = str(row[11]) if row[11] else ""

            writer.writerow(
                [
                    row[0],  # ip_address
                    row[1],  # source
                    row[2] or "",  # country
                    row[3].strftime("%Y-%m-%d") if row[3] else "",  # detection_date
                    row[4].strftime("%Y-%m-%d") if row[4] else "",  # removal_date
                    row[5],  # reason
                    row[6],  # confidence_level
                    row[7],  # detection_count
                    "Yes" if row[8] else "No",  # is_active
                    row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else "",  # last_seen
                    (row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else ""),  # created_at
                    raw_data_str,  # raw_data
                ]
            )

        # CSV 응답 반환
        output.seek(0)
        csv_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name=f"blacklist_raw_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    except Exception as e:
        logger.error(f"Blacklist raw export API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/chart-data", methods=["GET"])
def api_chart_data():
    """차트 데이터 API"""
    try:
        db_service = current_app.extensions["db_service"]

        chart_type = request.args.get("type", "daily")

        with db_service.get_connection() as conn:
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

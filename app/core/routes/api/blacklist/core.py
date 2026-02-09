#!/usr/bin/env python3
"""
Core Blacklist Operations
Routes: /blacklist/list, /blacklist/stats, /blacklist/check, /json

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
Reference: docs/104-ERROR-HANDLING-STANDARDIZATION-PLAN.md
"""

from flask import Blueprint, jsonify, request, current_app, g
from datetime import datetime
import logging
from ipaddress import ip_address, AddressValueError
from ....exceptions import (
    BadRequestError,
    ValidationError,
    DatabaseError,
)

from core.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)


blacklist_core_bp = Blueprint("blacklist_core", __name__)


@blacklist_core_bp.route("/blacklist/health", methods=["GET"])
def blacklist_health():
    """
    블랙리스트 API 헬스체크
    GET /api/blacklist/health
    """
    try:
        db_service = current_app.extensions.get("db_service")
        db_ok = db_service.health_check() if db_service else False

        return jsonify(
            {
                "success": True,
                "status": "healthy" if db_ok else "degraded",
                "database": "connected" if db_ok else "disconnected",
                "timestamp": datetime.now().isoformat(),
            }
        ), 200 if db_ok else 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify(
            {
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        ), 503


@blacklist_core_bp.route("/blacklist/list", methods=["GET"])
def get_blacklist_list():
    """
    블랙리스트 목록 조회 API (Phase 1.4: Standardized Error Handling)

    GET /api/blacklist/list?page=1&per_page=50

    Returns:
        {
            "success": True,
            "data": [...],
            "pagination": {...},
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        ValidationError: Invalid pagination parameters
        DatabaseError: Database query failed
    """
    # 페이지네이션 파라미터
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)

    # Validate pagination parameters
    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )
    if per_page < 1 or per_page > 1000:
        raise ValidationError(
            message="Items per page must be between 1 and 1000",
            field="per_page",
            details={"provided_value": per_page, "allowed_range": "1-1000"},
        )

    # Use dependency injection via app.extensions
    db_service = current_app.extensions["db_service"]

    try:
        offset = (page - 1) * per_page

        # 데이터베이스 조회 (parameterized query for security)
        blacklist_data = db_service.query(
            "SELECT * FROM blacklist_ips_with_auto_inactive ORDER BY id DESC LIMIT %s OFFSET %s",
            (per_page, offset),
        )

        total_count = db_service.query("SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive")[0]["count"]

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
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.error(f"Blacklist list query failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve blacklist data (page={page}): {type(e).__name__}",
        )


@blacklist_core_bp.route("/blacklist/check", methods=["POST", "GET"])
@rate_limit("1000 per hour; 100 per minute")  # Critical endpoint - high traffic expected
def check_ip_blacklist():
    """
    IP 블랙리스트 체크 API (Phase 1.4: Standardized Error Handling)

    POST /api/blacklist/check
    GET /api/blacklist/check?ip=1.2.3.4

    Returns:
        {
            "success": True,
            "data": {
                "ip": "1.2.3.4",
                "blocked": False,
                "reason": "whitelist",
                "metadata": {...}
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        BadRequestError: IP parameter missing
        ValidationError: Invalid IP format
        DatabaseError: Database query failed
    """
    # IP 파라미터 가져오기
    if request.method == "POST":
        data = request.get_json() or {}
        ip = data.get("ip")
    else:
        ip = request.args.get("ip")

    # Validate IP parameter presence
    if not ip:
        raise BadRequestError(
            message="IP address is required",
            details={"parameter": "ip", "method": request.method},
        )

    # Validate IP address format
    try:
        ip_address(str(ip).strip())  # Validates IPv4 and IPv6 format
    except (AddressValueError, ValueError, TypeError):
        raise BadRequestError(
            message="Invalid IP address format",
            details={"parameter": "ip", "provided_value": ip},
        )

    # Use dependency injection via app.extensions
    blacklist_service = current_app.extensions["blacklist_service"]

    try:
        result = blacklist_service.check_blacklist(ip)

        # Return standardized success response
        return jsonify(
            {
                "success": True,
                "data": {
                    "ip": ip,
                    "blocked": result["blocked"],
                    "reason": result["reason"],
                    "metadata": result.get("metadata", {}),
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except ValueError as e:
        # Invalid IP format from service validation
        raise ValidationError(message=str(e), field="ip", details={"provided_value": ip})
    except Exception as e:
        # Catch database and unexpected errors
        logger.error(f"IP check failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to check IP blacklist status for {ip}: {type(e).__name__}",
        )


@blacklist_core_bp.route("/json", methods=["GET"])
def get_blacklist_json():
    """
    블랙리스트 데이터 JSON 조회 API (Phase 1.4: Standardized Error Handling)

    GET /api/json?page=1&per_page=100

    Note: This endpoint uses graceful degradation for JavaScript consumption.
    Returns empty data instead of raising errors when database is unavailable.

    Returns:
        {
            "success": True,
            "data": [...],
            "pagination": {...},
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        ValidationError: Invalid pagination parameters
    """
    # 페이지네이션 파라미터
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 100, type=int)

    # Validate pagination parameters (before database access)
    if page < 1:
        raise ValidationError(
            message="Page number must be >= 1",
            field="page",
            details={"provided_value": page},
        )
    if per_page < 1 or per_page > 1000:
        raise ValidationError(
            message="Items per page must be between 1 and 1000",
            field="per_page",
            details={"provided_value": per_page, "allowed_range": "1-1000"},
        )

    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]
        offset = (page - 1) * per_page

        # 데이터베이스 연결 시도
        conn = db_service.get_connection()
        cursor = conn.cursor()

        # 전체 카운트
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips_with_auto_inactive")
        total = cursor.fetchone()[0]

        # 데이터 조회
        cursor.execute(
            """
            SELECT ip_address, source, detection_date, updated_at, confidence_level
            FROM blacklist_ips_with_auto_inactive
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """,
            (per_page, offset),
        )

        results = cursor.fetchall()
        cursor.close()
        db_service.return_connection(conn)

        return jsonify(
            {
                "success": True,
                "data": [
                    {
                        "ip_address": row[0],
                        "source": row[1],
                        "detection_date": row[2].isoformat() if row[2] else None,
                        "updated_at": row[3].isoformat() if row[3] else None,
                        "confidence_level": row[4],
                    }
                    for row in results
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception as e:
        logger.warning(f"Database not available, returning empty data: {e}")
        # 데이터베이스 연결 실패 시 빈 데이터 반환 (JavaScript 에러 방지)
        # Graceful degradation for frontend consumption
        return jsonify(
            {
                "success": True,
                "data": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": 0,
                    "pages": 0,
                },
                "message": "Database not available - showing empty data",
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200


@blacklist_core_bp.route("/blacklist/export-raw", methods=["GET"])
def export_raw_data():
    """
    블랙리스트 Raw 데이터 CSV 내보내기 API (수집 근거 포함)
    GET /api/blacklist/export-raw?source=REGTECH&active_only=true&include_empty=false
    """
    import csv
    import io
    import json
    from flask import send_file

    try:
        db_service = current_app.extensions["db_service"]

        source = request.args.get("source")
        active_only = request.args.get("active_only", "true").lower() == "true"
        include_empty = request.args.get("include_empty", "false").lower() == "true"

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
                where_conditions = []
                params = []

                if active_only:
                    where_conditions.append("is_active = %s")
                    params.append(True)

                if source:
                    where_conditions.append("source = %s")
                    params.append(source)

                if not include_empty:
                    where_conditions.append("raw_data IS NOT NULL")
                    where_conditions.append("raw_data != '{}'::jsonb")

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                export_query = f"""
                    SELECT
                        ip_address, source, country, detection_date, removal_date, reason,
                        confidence_level, detection_count,
                        is_active,
                        last_seen, created_at, raw_data
                    FROM blacklist_ips_with_auto_inactive
                    {where_clause}
                    ORDER BY created_at DESC
                """
                cur.execute(export_query, params)
                results = cur.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)

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
                "Raw 번호",
                "Raw IP",
                "Raw 탐지일",
                "Raw 해제일",
                "Raw 탐지내용",
                "Raw 국가",
                "수집 시각",
            ]
        )

        for row in results:
            raw_no = ""
            raw_ip = ""
            raw_detection_date = ""
            raw_removal_date = ""
            raw_reason = ""
            raw_country = ""
            collection_ts = ""

            if row[11]:
                try:
                    raw_data = row[11] if isinstance(row[11], dict) else json.loads(row[11])

                    if "row_data" in raw_data:
                        row_data = raw_data["row_data"]
                        if isinstance(row_data, list):
                            raw_no = row_data[0] if len(row_data) > 0 else ""
                            raw_ip = row_data[1] if len(row_data) > 1 else ""
                            raw_detection_date = row_data[2] if len(row_data) > 2 else ""
                            raw_removal_date = row_data[3] if len(row_data) > 3 else ""
                            raw_reason = row_data[4] if len(row_data) > 4 else ""
                            raw_country = row_data[5] if len(row_data) > 5 else ""

                    elif "api_response" in raw_data:
                        api = raw_data["api_response"]
                        raw_ip = api.get("ipAddress") or api.get("ip_address", "")
                        raw_detection_date = api.get("detectedDate") or api.get("detected_date", "")
                        raw_removal_date = api.get("releaseDate") or api.get("release_date", "")
                        raw_reason = api.get("blockReason") or api.get("reason", "")
                        raw_country = api.get("country") or api.get("countryCode", "")

                    else:
                        raw_ip = raw_data.get("ip_address", "")
                        raw_detection_date = str(raw_data.get("detection_date", ""))
                        raw_removal_date = str(raw_data.get("removal_date", ""))
                        raw_reason = raw_data.get("reason", "")
                        raw_country = raw_data.get("country", "")

                    collection_ts = raw_data.get("collection_timestamp", "")

                except (json.JSONDecodeError, TypeError, AttributeError):
                    raw_reason = str(row[11])[:200] if row[11] else ""

            writer.writerow(
                [
                    row[0],
                    row[1],
                    row[2] or "",
                    row[3].strftime("%Y-%m-%d") if row[3] else "",
                    row[4].strftime("%Y-%m-%d") if row[4] else "",
                    row[5],
                    row[6],
                    row[7],
                    "Yes" if row[8] else "No",
                    row[9].strftime("%Y-%m-%d %H:%M:%S") if row[9] else "",
                    row[10].strftime("%Y-%m-%d %H:%M:%S") if row[10] else "",
                    raw_no,
                    raw_ip,
                    raw_detection_date,
                    raw_removal_date,
                    raw_reason,
                    raw_country,
                    collection_ts,
                ]
            )

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

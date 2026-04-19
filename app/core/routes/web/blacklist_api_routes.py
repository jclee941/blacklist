"""
Blacklist web API routes.
"""

import csv
import io
import json
import logging
from datetime import datetime

from flask import current_app, jsonify, request, send_file

from . import web_bp

logger = logging.getLogger(__name__)


def _get_blacklist_filters():
    """Read shared blacklist query filters from request args."""
    source = request.args.get("source")
    active_only = request.args.get("active_only", "true").lower() == "true"
    return source, active_only


def _build_blacklist_where_clause(source, active_only, include_empty=False):
    """Build shared WHERE clause and params for blacklist queries."""
    where_conditions = []
    params = []

    if active_only:
        where_conditions.append("is_active = %s")
        params.append(True)

    if source:
        where_conditions.append("source = %s")
        params.append(source)

    if not include_empty:
        return where_conditions, params

    where_conditions.append("raw_data IS NOT NULL")
    where_conditions.append("raw_data != '{}'::jsonb")
    return where_conditions, params


@web_bp.route("/api/blacklist/list", methods=["GET"])
def api_blacklist_list():
    """블랙리스트 목록 API"""
    try:
        db_service = current_app.extensions["db_service"]

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        offset = (page - 1) * per_page

        source, active_only = _get_blacklist_filters()
        where_conditions, params = _build_blacklist_where_clause(source, active_only)
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
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

                count_query = f"SELECT COUNT(*) FROM blacklist_ips {where_clause}"
                cur.execute(count_query, params)
                total_count = cur.fetchone()[0]

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

        source, active_only = _get_blacklist_filters()
        where_conditions, params = _build_blacklist_where_clause(source, active_only)
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
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
            ]
        )

        for row in results:
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
                ]
            )

        _ = output.seek(0)
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

        source, active_only = _get_blacklist_filters()
        include_empty = request.args.get("include_empty", "false").lower() == "true"
        where_conditions, params = _build_blacklist_where_clause(source, active_only, include_empty)
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        with db_service.get_connection() as conn:
            with conn.cursor() as cur:
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
                "Raw Data (JSON)",
            ]
        )

        for row in results:
            raw_data_str = ""
            if row[11]:
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
                    raw_data_str,
                ]
            )

        _ = output.seek(0)
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

"""
Collection Routes
수집 제어 관련 라우트
"""

from flask import render_template, jsonify, request, current_app
import logging
from datetime import datetime
from . import web_bp
from ...services.database_lease import connection_lease

logger = logging.getLogger(__name__)


@web_bp.route("/collection-control", methods=["GET"])
def collection_control_page():
    """수집 제어 페이지"""
    return render_template("collection_control.html")


@web_bp.route("/collection-schedule", methods=["GET"])
def collection_schedule_page():
    """수집 스케줄 페이지"""
    return render_template("collection_schedule.html")


@web_bp.route("/collection-history", methods=["GET"])
def collection_history_page():
    """수집 이력 페이지"""
    return render_template("collection_history.html")


@web_bp.route("/regtech-setup", methods=["GET"])
def regtech_setup():
    """REGTECH 설정 페이지"""
    return render_template("regtech_setup.html")


@web_bp.route("/api/collection/<source>/trigger", methods=["POST"])
def api_collection_trigger(source):
    """개별 소스 수집 트리거 API"""
    try:
        collection_service = current_app.extensions["collection_service"]

        # 소스 유효성 검증
        valid_sources = ["regtech"]
        if source.lower() not in valid_sources:
            return (
                jsonify({"success": False, "error": f"Invalid source: {source}"}),
                400,
            )

        # 요청 데이터에서 날짜 파라미터 추출
        data = request.get_json() or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # 수집 실행 (날짜 파라미터 포함)
        result = None
        if start_date and end_date:
            # 기간별 수집
            if source.lower() == "regtech":
                result = collection_service.trigger_regtech_collection(start_date=start_date, end_date=end_date)

            message = f"{source.upper()} 기간별 수집이 완료되었습니다. ({start_date} ~ {end_date})"
        else:
            # 일반 수집
            result = collection_service.trigger_collection(source.lower())
            message = f"{source.upper()} 수집이 완료되었습니다."

        if result is None:
            return jsonify({"success": False, "error": f"Invalid source: {source}"}), 400

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "collected_count": result.get("collected_count", 0),
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        else:
            return jsonify({"success": False, "error": result.get("error", "수집 실패")})

    except Exception as e:
        logger.error(f"Collection trigger API error for {source}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/collection/trigger-all", methods=["POST"])
def api_collection_trigger_all():
    """전체 수집 트리거 API"""
    try:
        collection_service = current_app.extensions["collection_service"]

        # 전체 수집 실행
        result = collection_service.trigger_all_collections()

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": "전체 수집이 완료되었습니다.",
                    "results": result.get("results", {}),
                    "total_collected": result.get("total_collected", 0),
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": result.get("error", "전체 수집 실패"),
                    "results": result.get("results", {}),
                }
            )

    except Exception as e:
        logger.error(f"Collection trigger all API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/collection/stop", methods=["POST"])
def api_collection_stop():
    """수집 중지 API"""
    try:
        collection_service = current_app.extensions["collection_service"]

        # 수집 중지
        result = collection_service.stop_all_collections()

        return jsonify(
            {
                "success": True,
                "message": "모든 수집이 중지되었습니다.",
                "stopped_sources": result.get("stopped_sources", []),
            }
        )

    except Exception as e:
        logger.error(f"Collection stop API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/expand-collection-scope", methods=["POST"])
def api_expand_collection_scope():
    """수집 범위 확대 API - Enhanced Collection"""
    try:
        collection_service = current_app.extensions["collection_service"]

        # 수집 범위 확대 실행
        result = collection_service.expand_collection_scope()

        return jsonify(
            {
                "success": result.get("success", False),
                "message": result.get("message", "수집 범위 확대 실행"),
                "total_collected": result.get("total_collected", 0),
                "sources": result.get("sources", []),
                "execution_time": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Expand collection scope API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/collection/history", methods=["GET"])
def api_collection_history():
    """수집 이력 API"""
    try:
        db_service = current_app.extensions["db_service"]

        # 페이징 파라미터
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        offset = (page - 1) * per_page

        with connection_lease(db_service) as conn:
            with conn.cursor() as cur:
                # 전체 수집 이력 조회
                cur.execute(
                    """
                    SELECT
                        service_name,
                        collection_date,
                        items_collected,
                        success,
                        execution_time_ms,
                        error_message,
                        details
                    FROM collection_history
                    ORDER BY collection_date DESC
                    LIMIT %s OFFSET %s
                """,
                    (per_page, offset),
                )
                history_data = cur.fetchall()

                # 전체 레코드 수
                cur.execute("SELECT COUNT(*) FROM collection_history")
                count_row = cur.fetchone()
                if count_row is None:
                    raise RuntimeError("Collection history count query returned no row")
                total_count = count_row[0]

        # 응답 데이터 구성
        history_list = []
        for row in history_data:
            # details에서 start_date, end_date 추출
            details = row[6] if row[6] else {}
            history_list.append(
                {
                    "service_name": row[0],
                    "collection_date": row[1].isoformat() if row[1] else None,
                    "items_collected": row[2],
                    "success": row[3],
                    "execution_time_ms": row[4],
                    "error_message": row[5],
                    "start_date": (details.get("start_date") if isinstance(details, dict) else None),
                    "end_date": (details.get("end_date") if isinstance(details, dict) else None),
                    "details": details,
                }
            )

        return jsonify(
            {
                "success": True,
                "history": history_list,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "pages": (total_count + per_page - 1) // per_page,
                },
            }
        )

    except Exception as e:
        logger.error(f"Collection history API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

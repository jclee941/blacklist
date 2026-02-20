"""
Admin Routes
관리자 기능 관련 라우트 (인증정보 관리, 데이터베이스 관리 등)
"""

from flask import render_template, jsonify, request, current_app
import logging
from . import web_bp

logger = logging.getLogger(__name__)


@web_bp.route("/database-tables", methods=["GET"])
def database_tables_page():
    """데이터베이스 테이블 현황 페이지"""
    return render_template("database_tables.html")


# REGTECH 관리자 API 엔드포인트
@web_bp.route("/api/admin/regtech/credentials", methods=["GET"])
def api_admin_get_regtech_credentials():
    """REGTECH 관리자 인증정보 조회 API"""
    try:
        regtech_service = current_app.extensions["regtech_config_service"]

        credentials = regtech_service.get_regtech_credentials()

        if not credentials:
            return jsonify(
                {
                    "success": True,
                    "has_credentials": False,
                    "data": {
                        "username": "",
                        "has_password": False,
                        "base_url": "https://regtech.fsec.or.kr",
                        "login_url": "/login/loginProcess",
                        "advisory_url": "/fcti/securityAdvisory/advisoryList",
                        "timeout_seconds": 30,
                        "request_delay_seconds": 1,
                        "max_pages": 100,
                        "items_per_page": 50,
                    },
                }
            )

        return jsonify(
            {
                "success": True,
                "has_credentials": True,
                "data": {
                    "username": credentials.get("username", ""),
                    "has_password": bool(credentials.get("password", "")),
                    "base_url": credentials.get("base_url", "https://regtech.fsec.or.kr"),
                    "login_url": credentials.get("login_url", "/login/loginProcess"),
                    "advisory_url": credentials.get("advisory_url", "/fcti/securityAdvisory/advisoryList"),
                    "timeout_seconds": credentials.get("timeout_seconds", 30),
                    "request_delay_seconds": credentials.get("request_delay_seconds", 1),
                    "max_pages": credentials.get("max_pages", 100),
                    "items_per_page": credentials.get("items_per_page", 50),
                },
            }
        )

    except Exception as e:
        logger.error(f"REGTECH 관리자 인증정보 조회 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/admin/regtech/credentials", methods=["POST"])
def api_admin_save_regtech_credentials():
    """REGTECH 관리자 인증정보 저장 API"""
    request.get_json() or {}

    # 자동 수집 시작 로직 추가
    try:
        result = api_save_credentials("regtech")
        response_data = result.get_json() if hasattr(result, "get_json") else result

        if isinstance(response_data, dict) and response_data.get("success"):
            # 자동 수집 시작
            collection_service = current_app.extensions["collection_service"]

            collection_result = collection_service.trigger_regtech_collection()

            response_data["data"] = {
                "auto_collection_started": True,
                "collection_period": "최근 7일",
                "collection_result": collection_result,
            }

        return jsonify(response_data)
    except Exception as e:
        logger.error(f"REGTECH 관리자 인증정보 저장 실패: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/admin/regtech/credentials", methods=["DELETE"])
def api_admin_delete_regtech_credentials():
    """REGTECH 관리자 인증정보 삭제 API"""
    return api_delete_credentials("regtech")


@web_bp.route("/api/admin/regtech/test-connection", methods=["POST"])
def api_admin_regtech_test_connection():
    """REGTECH 관리자 연결 테스트 API"""
    try:
        collection_service = current_app.extensions["collection_service"]

        # 연결 테스트 및 자동 수집
        result = collection_service.test_regtech_connection()

        if result.get("success"):
            # 자동 수집 시작
            collection_result = collection_service.trigger_regtech_collection()

            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH 포털 연결이 성공적으로 확인되었습니다.",
                    "auto_collection_started": True,
                    "collection_period": "최근 7일",
                    "connection_test": result,
                    "collection_result": collection_result,
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": result.get("error", "연결 테스트 실패"),
                    "connection_test": result,
                }
            )

    except Exception as e:
        logger.error(f"REGTECH 연결 테스트 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"연결 테스트 중 오류가 발생했습니다: {str(e)}",
                }
            ),
            500,
        )


@web_bp.route("/api/credentials/<service_name>", methods=["GET"])
def api_get_credentials(service_name):
    """인증정보 조회 API"""
    try:
        db_service = current_app.extensions["db_service"]

        credentials = db_service.get_collection_credentials(service_name)

        if "error" in credentials:
            return jsonify({"success": False, "error": credentials["error"]}), 500

        return jsonify(
            {
                "success": True,
                "service_name": credentials.get("service_name", service_name.upper()),
                "username": credentials.get("username", ""),
                "is_authenticated": credentials.get("is_authenticated", False),
                "created_at": credentials.get("created_at"),
                "updated_at": credentials.get("updated_at"),
            }
        )

    except Exception as e:
        logger.error(f"Get credentials API error for {service_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/credentials/<service_name>", methods=["POST"])
def api_save_credentials(service_name):
    """인증정보 저장 API"""
    try:
        pass

        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "사용자명과 비밀번호를 모두 입력해주세요.",
                    }
                ),
                400,
            )

        # 인증정보 저장 - REGTECH 서비스 사용
        regtech_service = current_app.extensions["regtech_config_service"]

        result = regtech_service.save_regtech_credentials(username, password)

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": f"{service_name.upper()} 인증정보가 저장되었습니다.",
                    "service_name": result.get("service_name"),
                    "is_authenticated": result.get("is_authenticated", False),
                }
            )
        else:
            return jsonify({"success": False, "error": result.get("error", "저장 실패")})

    except Exception as e:
        logger.error(f"Save credentials API error for {service_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/credentials/<service_name>", methods=["DELETE"])
def api_delete_credentials(service_name):
    """인증정보 삭제 API"""
    try:
        db_service = current_app.extensions["db_service"]

        result = db_service.delete_collection_credentials(service_name)

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": f"{service_name.upper()} 인증정보가 삭제되었습니다.",
                }
            )
        else:
            return jsonify({"success": False, "error": result.get("error", "삭제 실패")})

    except Exception as e:
        logger.error(f"Delete credentials API error for {service_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/database/tables", methods=["GET"])
def api_database_tables():
    """데이터베이스 테이블 현황 조회 API"""
    try:
        db_service = current_app.extensions["db_service"]

        tables_info = db_service.show_database_tables()
        return jsonify({"success": True, **tables_info})
    except Exception as e:
        logger.error(f"Database tables API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@web_bp.route("/api/database/clear", methods=["POST"])
def api_clear_database():
    """데이터베이스 초기화 API (테스트 데이터 삭제)"""
    try:
        db_service = current_app.extensions["db_service"]

        result = db_service.clear_all_blacklist_data()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Database clear API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

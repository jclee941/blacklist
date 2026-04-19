"""REGTECH 관리자 인증/연결 관련 라우트."""

import logging
from datetime import datetime, timedelta

from flask import current_app, jsonify, request

from ...config import config

logger = logging.getLogger(__name__)


def _start_auto_collection(start_date: str, end_date: str) -> dict[str, object]:
    try:
        collection_service = current_app.extensions["collection_service"]

        import threading

        def auto_collect_background():
            try:
                logger.info(f"🚀 자동 수집 시작: {start_date} ~ {end_date}")
                result = collection_service.trigger_regtech_collection(
                    start_date=start_date,
                    end_date=end_date,
                )
                if result["success"]:
                    logger.info(f"✅ 자동 수집 완료: {result['collected_count']}개 수집")
                else:
                    logger.warning(f"⚠️ 자동 수집 실패: {result.get('error', '알 수 없는 오류')}")
            except Exception as exc:
                logger.error(f"💥 자동 수집 중 오류: {exc}")

        collection_thread = threading.Thread(target=auto_collect_background, daemon=True)
        collection_thread.start()
        return {
            "started": True,
            "period": f"{start_date} ~ {end_date}",
            "message": "백그라운드에서 자동 수집이 시작되었습니다",
        }
    except Exception as exc:
        logger.error(f"💥 자동 수집 시작 중 오류: {exc}")
        return {"started": False, "error": str(exc)}


def _default_collection_period(days: int = 7) -> tuple[str, str]:
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return start_date, end_date


def register_admin_credentials_routes(bp):
    @bp.route("/regtech/credentials", methods=["POST"])
    def set_regtech_credentials():
        """🚀 고도화된 REGTECH 인증 정보 설정 및 자동 검증"""
        start_time = datetime.now()

        try:
            data = request.get_json()
            if not data:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "JSON 데이터가 필요합니다.",
                            "error_code": "NO_JSON_DATA",
                        }
                    ),
                    400,
                )

            username = (data.get("username") or data.get("regtech_id") or "").strip()
            password = data.get("password") or data.get("regtech_pw") or ""

            if not username or not password:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "사용자명과 비밀번호는 필수입니다.",
                            "error_code": "MISSING_CREDENTIALS",
                            "validation": {
                                "username_provided": bool(username),
                                "password_provided": bool(password),
                            },
                        }
                    ),
                    400,
                )

            if len(username) < 2:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "사용자명은 최소 2자 이상이어야 합니다.",
                            "error_code": "USERNAME_TOO_SHORT",
                        }
                    ),
                    400,
                )

            base_url = data.get("base_url", config.REGTECH_BASE_URL)
            login_url = data.get("login_url", "/login/loginProcess")
            advisory_url = data.get("advisory_url", "/fcti/securityAdvisory/advisoryList")
            auto_test = data.get("auto_test", True)

            logger.info(f"🔐 REGTECH 인증정보 설정 요청 - 사용자: {username}, 자동테스트: {auto_test}")

            regtech_config_service = current_app.extensions["regtech_config_service"]
            save_result = regtech_config_service.save_regtech_credentials(
                username=username,
                password=password,
                base_url=base_url,
                login_url=login_url,
                advisory_url=advisory_url,
            )

            if save_result["success"]:
                test_result = save_result.get("test_result", {})
                response_message = "✅ REGTECH 인증정보 저장 완료"
                response_data = {
                    "success": True,
                    "message": response_message,
                    "operation": save_result.get("operation", "unknown"),
                    "username": username,
                    "base_url": base_url,
                    "save_duration": save_result.get("duration", 0),
                    "timestamp": save_result.get("timestamp"),
                    "test_result": test_result,
                }

                if test_result.get("success"):
                    response_data["connection_status"] = "verified"
                    response_data["message"] = f"{response_message} 및 연결 테스트 통과"
                    if data.get("auto_collect", False):
                        start_date, end_date = _default_collection_period(days=7)
                        response_data["auto_collection"] = _start_auto_collection(
                            start_date,
                            end_date,
                        )
                else:
                    response_data["connection_status"] = "failed"
                    response_data["warning"] = test_result.get("message", "연결 테스트 실패")
                    response_data["message"] = (
                        f"{response_message} (연결 테스트 실패: {test_result.get('result_code', 'UNKNOWN')})"
                    )

                response_data["total_duration"] = (datetime.now() - start_time).total_seconds()
                return jsonify(response_data)

            error_response = {
                "success": False,
                "error": save_result.get("message", "인증정보 저장에 실패했습니다."),
                "error_code": save_result.get("error_code", "SAVE_FAILED"),
                "details": save_result.get("error"),
                "duration": save_result.get("duration", 0),
            }
            return jsonify(error_response), 500

        except Exception as exc:
            import traceback

            error_details = traceback.format_exc()
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"💥 REGTECH 인증정보 설정 중 예외 발생: {exc}")
            logger.error(f"📋 상세 오류 정보: {error_details}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"서버 오류: {str(exc)}",
                        "error_code": "SERVER_ERROR",
                        "duration": total_duration,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    @bp.route("/regtech/credentials", methods=["GET"])
    def get_regtech_credentials_info():
        """REGTECH 인증 정보 조회 (패스워드 제외)"""
        try:
            regtech_config_service = current_app.extensions["regtech_config_service"]
            credentials = regtech_config_service.get_regtech_credentials()
            if not credentials:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "REGTECH 인증 정보가 설정되지 않았습니다.",
                            "has_credentials": False,
                        }
                    ),
                    404,
                )

            safe_credentials = {
                "username": credentials["username"],
                "base_url": credentials["base_url"],
                "login_url": credentials["login_url"],
                "advisory_url": credentials["advisory_url"],
                "max_pages": credentials["max_pages"],
                "items_per_page": credentials["items_per_page"],
                "timeout_seconds": credentials["timeout_seconds"],
                "request_delay_seconds": credentials["request_delay_seconds"],
                "has_password": len(credentials["password"]) > 0,
            }
            return jsonify({"success": True, "has_credentials": True, "data": safe_credentials})
        except Exception as exc:
            logger.error(f"REGTECH 인증 정보 조회 중 오류: {exc}")
            return jsonify({"success": False, "error": f"서버 오류: {str(exc)}"}), 500

    @bp.route("/regtech/test-connection", methods=["POST"])
    def test_regtech_connection():
        """🔍 고도화된 REGTECH 연결 테스트 API"""
        start_time = datetime.now()

        try:
            logger.info("🔍 REGTECH 연결 테스트 API 호출")
            regtech_config_service = current_app.extensions["regtech_config_service"]
            result = regtech_config_service.test_regtech_connection_enhanced()
            response_data = {
                "success": result["success"],
                "message": result["message"],
                "result_code": result.get("result_code"),
                "phases": result.get("phases", {}),
                "summary": result.get("summary", {}),
                "test_duration": result.get("duration", 0),
                "timestamp": result.get("timestamp"),
                "api_duration": (datetime.now() - start_time).total_seconds(),
            }

            if result["success"]:
                try:
                    data = request.get_json() or {}
                    if data.get("auto_collect", False):
                        start_date, end_date = _default_collection_period(days=7)
                        response_data["auto_collection"] = _start_auto_collection(
                            start_date,
                            end_date,
                        )
                    else:
                        response_data["auto_collection"] = {
                            "started": False,
                            "message": "자동 수집이 요청되지 않았습니다",
                        }
                except Exception as exc:
                    logger.error(f"💥 자동 수집 시작 중 오류: {exc}")
                    response_data["auto_collection"] = {
                        "started": False,
                        "error": str(exc),
                        "message": "자동 수집 시작에 실패했습니다",
                    }
                return jsonify(response_data)

            status_code = 400
            if result.get("result_code") == "NO_CREDENTIALS":
                status_code = 404
            elif result.get("result_code") in ["COLLECTOR_UNAVAILABLE", "TEST_ERROR"]:
                status_code = 503
            return jsonify(response_data), status_code

        except Exception as exc:
            import traceback

            error_details = traceback.format_exc()
            total_duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"💥 REGTECH 연결 테스트 API 중 예외 발생: {exc}")
            logger.error(f"📋 상세 오류 정보: {error_details}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"연결 테스트 중 서버 오류: {str(exc)}",
                        "error_code": "API_ERROR",
                        "duration": total_duration,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    @bp.route("/regtech/update-password", methods=["PUT"])
    def update_regtech_password():
        """REGTECH 패스워드만 업데이트"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "JSON 데이터가 필요합니다."}), 400

            new_password = data.get("password")
            if not new_password:
                return (
                    jsonify({"success": False, "error": "새로운 password는 필수입니다."}),
                    400,
                )

            regtech_config_service = current_app.extensions["regtech_config_service"]
            success = regtech_config_service.update_regtech_password(new_password)
            if not success:
                return (
                    jsonify({"success": False, "error": "패스워드 업데이트에 실패했습니다."}),
                    500,
                )

            try:
                test_result = regtech_config_service.test_regtech_connection()
                if test_result["success"]:
                    start_date, end_date = _default_collection_period(days=30)
                    _start_auto_collection(start_date, end_date)
                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 패스워드가 업데이트되고 자동 수집이 시작되었습니다.",
                            "auto_collection_started": True,
                            "collection_period": f"{start_date} ~ {end_date}",
                        }
                    )

                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 패스워드는 업데이트되었으나 연결 테스트에 실패했습니다.",
                        "warning": test_result.get("error", "연결 실패"),
                    }
                )
            except Exception as exc:
                logger.error(f"자동 수집 시작 중 오류: {exc}")
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 패스워드는 업데이트되었으나 자동 수집 시작에 실패했습니다.",
                        "warning": str(exc),
                    }
                )
        except Exception as exc:
            logger.error(f"REGTECH 패스워드 업데이트 중 오류: {exc}")
            return jsonify({"success": False, "error": f"서버 오류: {str(exc)}"}), 500

    @bp.route("/regtech/initialize", methods=["POST"])
    def initialize_regtech():
        """REGTECH 인증 정보 초기화 (환경변수에서)"""
        try:
            regtech_config_service = current_app.extensions["regtech_config_service"]
            success = regtech_config_service.initialize_regtech_credentials()
            if not success:
                return (
                    jsonify({"success": False, "error": "REGTECH 인증 정보 초기화에 실패했습니다."}),
                    500,
                )

            try:
                test_result = regtech_config_service.test_regtech_connection()
                if test_result["success"]:
                    start_date, end_date = _default_collection_period(days=30)
                    _start_auto_collection(start_date, end_date)
                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 인증 정보가 초기화되고 자동 수집이 시작되었습니다.",
                            "auto_collection_started": True,
                            "collection_period": f"{start_date} ~ {end_date}",
                        }
                    )

                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 인증 정보는 초기화되었으나 연결 테스트에 실패했습니다.",
                        "warning": test_result.get("error", "연결 실패"),
                    }
                )
            except Exception as exc:
                logger.error(f"자동 수집 시작 중 오류: {exc}")
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 인증 정보는 초기화되었으나 자동 수집 시작에 실패했습니다.",
                        "warning": str(exc),
                    }
                )
        except Exception as exc:
            logger.error(f"REGTECH 초기화 중 오류: {exc}")
            return jsonify({"success": False, "error": f"서버 오류: {str(exc)}"}), 500

    @bp.route("/regtech/credentials", methods=["DELETE"])
    def delete_regtech_credentials():
        """REGTECH 인증 정보 삭제"""
        try:
            regtech_config_service = current_app.extensions["regtech_config_service"]
            success = regtech_config_service.delete_regtech_credentials()
            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 인증정보가 성공적으로 삭제되었습니다.",
                    }
                )
            return (
                jsonify({"success": False, "error": "삭제할 REGTECH 인증정보가 없습니다."}),
                404,
            )
        except Exception as exc:
            logger.error(f"REGTECH 인증정보 삭제 중 오류: {exc}")
            return jsonify({"success": False, "error": f"서버 오류: {str(exc)}"}), 500

    @bp.route("/regtech/credentials-enhanced", methods=["POST"])
    def enhanced_set_regtech_credentials():
        """🚀 향상된 REGTECH 인증 정보 설정 (새로운 API 경로)"""
        return set_regtech_credentials()

    @bp.route("/regtech/credentials/test", methods=["GET"])
    def enhanced_test_regtech_connection():
        """🚀 향상된 REGTECH 연결 테스트 (새로운 API 경로)"""
        try:
            regtech_config_service = current_app.extensions["regtech_config_service"]
            result = regtech_config_service.test_regtech_connection_enhanced()
            if result["success"]:
                return jsonify(result)
            return jsonify(result), 400
        except Exception as exc:
            logger.error(f"향상된 연결 테스트 오류: {exc}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"연결 테스트 실패: {str(exc)}",
                        "error_code": "CONNECTION_TEST_ERROR",
                    }
                ),
                500,
            )

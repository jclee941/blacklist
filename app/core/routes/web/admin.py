"""
REGTECH 관리자 라우트
인증 정보 설정 및 연결 테스트 기능
"""

from flask import Blueprint, request, jsonify, current_app

import logging
import os

from ...config import config

from ...config import config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

regtech_admin_bp = Blueprint("regtech_admin", __name__)


@regtech_admin_bp.route("/regtech/credentials", methods=["POST"])
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

        # 필수 필드 검증 (accept both formats: username/password OR regtech_id/regtech_pw)
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

        # 입력 검증
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

        # 선택적 필드 (기본값 사용)
        base_url = data.get("base_url", config.REGTECH_BASE_URL)
        login_url = data.get("login_url", "/login/loginProcess")
        advisory_url = data.get("advisory_url", "/fcti/securityAdvisory/advisoryList")
        auto_test = data.get("auto_test", True)  # 기본적으로 자동 테스트 수행

        logger.info(f"🔐 REGTECH 인증정보 설정 요청 - 사용자: {username}, 자동테스트: {auto_test}")

        # Use dependency injection
        regtech_config_service = current_app.extensions["regtech_config_service"]

        # 고도화된 인증정보 저장
        save_result = regtech_config_service.save_regtech_credentials(
            username=username,
            password=password,
            base_url=base_url,
            login_url=login_url,
            advisory_url=advisory_url,
        )

        if save_result["success"]:
            test_result = save_result.get("test_result", {})

            # 성공 응답 구성
            response_data = {
                "success": True,
                "message": "✅ REGTECH 인증정보 저장 완료",
                "operation": save_result.get("operation", "unknown"),
                "username": username,
                "base_url": base_url,
                "save_duration": save_result.get("duration", 0),
                "timestamp": save_result.get("timestamp"),
                "test_result": test_result,
            }

            # 연결 테스트 결과에 따른 추가 정보
            if test_result.get("success"):
                response_data["connection_status"] = "verified"
                response_data["message"] += " 및 연결 테스트 통과"

                # 성공시 자동 수집 시작 (선택적)
                auto_collect = data.get("auto_collect", False)
                if auto_collect:
                    try:
                        collection_service = current_app.extensions["collection_service"]

                        # 최근 7일간의 데이터 수집 시작
                        end_date = datetime.now().strftime("%Y-%m-%d")
                        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

                        # 백그라운드에서 수집 시작
                        import threading

                        def auto_collect_background():
                            try:
                                logger.info(f"🚀 자동 수집 시작: {start_date} ~ {end_date}")
                                result = collection_service.trigger_regtech_collection(
                                    start_date=start_date, end_date=end_date
                                )
                                if result["success"]:
                                    logger.info(f"✅ 자동 수집 완료: {result['collected_count']}개 수집")
                                else:
                                    logger.warning(f"⚠️ 자동 수집 실패: {result.get('error', '알 수 없는 오류')}")
                            except Exception as e:
                                logger.error(f"💥 자동 수집 중 오류: {e}")

                        collection_thread = threading.Thread(target=auto_collect_background, daemon=True)
                        collection_thread.start()

                        response_data["auto_collection"] = {
                            "started": True,
                            "period": f"{start_date} ~ {end_date}",
                            "message": "백그라운드에서 자동 수집이 시작되었습니다",
                        }

                    except Exception as e:
                        logger.error(f"💥 자동 수집 시작 중 오류: {e}")
                        response_data["auto_collection"] = {
                            "started": False,
                            "error": str(e),
                        }
            else:
                response_data["connection_status"] = "failed"
                response_data["warning"] = test_result.get("message", "연결 테스트 실패")
                response_data["message"] += f" (연결 테스트 실패: {test_result.get('result_code', 'UNKNOWN')})"

            total_duration = (datetime.now() - start_time).total_seconds()
            response_data["total_duration"] = total_duration

            return jsonify(response_data)

        else:
            # 저장 실패
            error_response = {
                "success": False,
                "error": save_result.get("message", "인증정보 저장에 실패했습니다."),
                "error_code": save_result.get("error_code", "SAVE_FAILED"),
                "details": save_result.get("error"),
                "duration": save_result.get("duration", 0),
            }

            return jsonify(error_response), 500

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        total_duration = (datetime.now() - start_time).total_seconds()

        logger.error(f"💥 REGTECH 인증정보 설정 중 예외 발생: {e}")
        logger.error(f"📋 상세 오류 정보: {error_details}")

        return (
            jsonify(
                {
                    "success": False,
                    "error": f"서버 오류: {str(e)}",
                    "error_code": "SERVER_ERROR",
                    "duration": total_duration,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@regtech_admin_bp.route("/regtech/credentials", methods=["GET"])
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

        # 패스워드는 제외하고 반환
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

    except Exception as e:
        logger.error(f"REGTECH 인증 정보 조회 중 오류: {e}")
        return jsonify({"success": False, "error": f"서버 오류: {str(e)}"}), 500


@regtech_admin_bp.route("/regtech/test-connection", methods=["POST"])
def test_regtech_connection():
    """🔍 고도화된 REGTECH 연결 테스트 API"""
    start_time = datetime.now()

    try:
        logger.info("🔍 REGTECH 연결 테스트 API 호출")

        regtech_config_service = current_app.extensions["regtech_config_service"]

        # 고도화된 연결 테스트 실행
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
            # 연결 테스트 성공 시 선택적 자동 수집
            try:
                data = request.get_json() or {}
                auto_collect = data.get("auto_collect", False)

                if auto_collect:
                    collection_service = current_app.extensions["collection_service"]

                    import threading

                    # 최근 7일간의 데이터 수집 시작 (30일 → 7일로 단축)
                    end_date = datetime.now().strftime("%Y-%m-%d")
                    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

                    def auto_collect_background():
                        try:
                            logger.info(f"🚀 연결 테스트 성공 후 자동 수집 시작: {start_date} ~ {end_date}")
                            collection_result = collection_service.trigger_regtech_collection(
                                start_date=start_date, end_date=end_date
                            )
                            if collection_result["success"]:
                                logger.info(f"✅ 자동 수집 완료: {collection_result['collected_count']}개 수집")
                            else:
                                logger.warning(f"⚠️ 자동 수집 실패: {collection_result.get('error', '알 수 없는 오류')}")
                        except Exception as e:
                            logger.error(f"💥 자동 수집 중 오류: {e}")

                    # 백그라운드 스레드로 수집 실행
                    collection_thread = threading.Thread(target=auto_collect_background, daemon=True)
                    collection_thread.start()

                    response_data["auto_collection"] = {
                        "started": True,
                        "period": f"{start_date} ~ {end_date}",
                        "message": "백그라운드에서 자동 수집이 시작되었습니다",
                    }

                else:
                    response_data["auto_collection"] = {
                        "started": False,
                        "message": "자동 수집이 요청되지 않았습니다",
                    }

            except Exception as e:
                logger.error(f"💥 자동 수집 시작 중 오류: {e}")
                response_data["auto_collection"] = {
                    "started": False,
                    "error": str(e),
                    "message": "자동 수집 시작에 실패했습니다",
                }

            return jsonify(response_data)

        else:
            # 연결 테스트 실패
            status_code = 400
            if result.get("result_code") == "NO_CREDENTIALS":
                status_code = 404
            elif result.get("result_code") in ["COLLECTOR_UNAVAILABLE", "TEST_ERROR"]:
                status_code = 503

            return jsonify(response_data), status_code

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        total_duration = (datetime.now() - start_time).total_seconds()

        logger.error(f"💥 REGTECH 연결 테스트 API 중 예외 발생: {e}")
        logger.error(f"📋 상세 오류 정보: {error_details}")

        return (
            jsonify(
                {
                    "success": False,
                    "error": f"연결 테스트 중 서버 오류: {str(e)}",
                    "error_code": "API_ERROR",
                    "duration": total_duration,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@regtech_admin_bp.route("/regtech/update-password", methods=["PUT"])
def update_regtech_password():
    """REGTECH 패스워드만 업데이트"""
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify({"success": False, "error": "JSON 데이터가 필요합니다."}),
                400,
            )

        new_password = data.get("password")
        if not new_password:
            return (
                jsonify({"success": False, "error": "새로운 password는 필수입니다."}),
                400,
            )

        regtech_config_service = current_app.extensions["regtech_config_service"]
        success = regtech_config_service.update_regtech_password(new_password)

        if success:
            # 패스워드 업데이트 후 자동으로 연결 테스트 및 수집 시작
            try:
                # 연결 테스트
                test_result = regtech_config_service.test_regtech_connection()

                if test_result["success"]:
                    # 연결 성공 시 자동 수집 시작
                    collection_service = current_app.extensions["collection_service"]

                    import threading

                    end_date = datetime.now().strftime("%Y-%m-%d")
                    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

                    def auto_collect():
                        try:
                            logger.info(f"패스워드 업데이트 후 자동 수집 시작: {start_date} ~ {end_date}")
                            result = collection_service.trigger_regtech_collection(
                                start_date=start_date, end_date=end_date
                            )
                            if result["success"]:
                                logger.info(f"자동 수집 완료: {result['collected_count']}개 수집")
                        except Exception as e:
                            logger.error(f"자동 수집 중 오류: {e}")

                    collection_thread = threading.Thread(target=auto_collect, daemon=True)
                    collection_thread.start()

                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 패스워드가 업데이트되고 자동 수집이 시작되었습니다.",
                            "auto_collection_started": True,
                            "collection_period": f"{start_date} ~ {end_date}",
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 패스워드는 업데이트되었으나 연결 테스트에 실패했습니다.",
                            "warning": test_result.get("error", "연결 실패"),
                        }
                    )
            except Exception as e:
                logger.error(f"자동 수집 시작 중 오류: {e}")
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 패스워드는 업데이트되었으나 자동 수집 시작에 실패했습니다.",
                        "warning": str(e),
                    }
                )
        else:
            return (
                jsonify({"success": False, "error": "패스워드 업데이트에 실패했습니다."}),
                500,
            )

    except Exception as e:
        logger.error(f"REGTECH 패스워드 업데이트 중 오류: {e}")
        return jsonify({"success": False, "error": f"서버 오류: {str(e)}"}), 500


@regtech_admin_bp.route("/regtech/initialize", methods=["POST"])
def initialize_regtech():
    """REGTECH 인증 정보 초기화 (환경변수에서)"""
    try:
        regtech_config_service = current_app.extensions["regtech_config_service"]
        success = regtech_config_service.initialize_regtech_credentials()

        if success:
            # 초기화 후 자동으로 연결 테스트 및 수집 시작
            try:
                test_result = regtech_config_service.test_regtech_connection()

                if test_result["success"]:
                    collection_service = current_app.extensions["collection_service"]

                    import threading

                    end_date = datetime.now().strftime("%Y-%m-%d")
                    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

                    def auto_collect():
                        try:
                            logger.info(f"초기화 후 자동 수집 시작: {start_date} ~ {end_date}")
                            result = collection_service.trigger_regtech_collection(
                                start_date=start_date, end_date=end_date
                            )
                            if result["success"]:
                                logger.info(f"자동 수집 완료: {result['collected_count']}개 수집")
                        except Exception as e:
                            logger.error(f"자동 수집 중 오류: {e}")

                    collection_thread = threading.Thread(target=auto_collect, daemon=True)
                    collection_thread.start()

                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 인증 정보가 초기화되고 자동 수집이 시작되었습니다.",
                            "auto_collection_started": True,
                            "collection_period": f"{start_date} ~ {end_date}",
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "message": "REGTECH 인증 정보는 초기화되었으나 연결 테스트에 실패했습니다.",
                            "warning": test_result.get("error", "연결 실패"),
                        }
                    )
            except Exception as e:
                logger.error(f"자동 수집 시작 중 오류: {e}")
                return jsonify(
                    {
                        "success": True,
                        "message": "REGTECH 인증 정보는 초기화되었으나 자동 수집 시작에 실패했습니다.",
                        "warning": str(e),
                    }
                )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "REGTECH 인증 정보 초기화에 실패했습니다.",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"REGTECH 초기화 중 오류: {e}")
        return jsonify({"success": False, "error": f"서버 오류: {str(e)}"}), 500


@regtech_admin_bp.route("/regtech/credentials", methods=["DELETE"])
def delete_regtech_credentials():
    """REGTECH 인증 정보 삭제"""
    try:
        regtech_config_service = current_app.extensions["regtech_config_service"]
        # 인증 정보 삭제
        success = regtech_config_service.delete_regtech_credentials()

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH 인증정보가 성공적으로 삭제되었습니다.",
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "삭제할 REGTECH 인증정보가 없습니다."}),
                404,
            )

    except Exception as e:
        logger.error(f"REGTECH 인증정보 삭제 중 오류: {e}")
        return jsonify({"success": False, "error": f"서버 오류: {str(e)}"}), 500


# =====================================================
# Collection Trigger Routes
# =====================================================


@regtech_admin_bp.route("/regtech/collect", methods=["POST"])
def trigger_regtech_collection():
    """
    Trigger REGTECH collection manually
    Body: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"} (optional)
    """
    try:
        # Use dependency injection via app.extensions
        collection_service = current_app.extensions["collection_service"]

        data = request.get_json() or {}
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        # Default to last 7 days if no dates provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        logger.info(f"REGTECH collection trigger requested: {start_date} to {end_date}")

        # Trigger REGTECH collection
        result = collection_service.trigger_regtech_collection(start_date=start_date, end_date=end_date)

        if result.get("success"):
            logger.info(f"✅ REGTECH collection completed: {result.get('collected_count', 0)} items")
            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH collection triggered successfully",
                    "collected_count": result.get("collected_count", 0),
                    "start_date": start_date,
                    "end_date": end_date,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            logger.warning(f"REGTECH collection failed: {result.get('error', 'Unknown error')}")
            return jsonify(
                {
                    "success": False,
                    "error": result.get("error", "Collection failed"),
                    "timestamp": datetime.now().isoformat(),
                }
            ), 500

    except Exception as e:
        logger.error(f"REGTECH collection trigger error: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


# 🚀 향상된 API 엔드포인트들 (새로운 경로)
@regtech_admin_bp.route("/regtech/credentials-enhanced", methods=["POST"])
def enhanced_set_regtech_credentials():
    """🚀 향상된 REGTECH 인증 정보 설정 (새로운 API 경로)"""
    return set_regtech_credentials()


@regtech_admin_bp.route("/regtech/credentials/test", methods=["GET"])
def enhanced_test_regtech_connection():
    """🚀 향상된 REGTECH 연결 테스트 (새로운 API 경로)"""
    try:
        regtech_config_service = current_app.extensions["regtech_config_service"]
        result = regtech_config_service.test_regtech_connection_enhanced()

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"향상된 연결 테스트 오류: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"연결 테스트 실패: {str(e)}",
                    "error_code": "CONNECTION_TEST_ERROR",
                }
            ),
            500,
        )

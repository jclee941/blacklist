"""수집 패널 뷰/인증정보 관련 라우트."""

import logging

from flask import current_app, jsonify, render_template, request

from ...config import config

logger = logging.getLogger(__name__)


def register_collection_panel_view_routes(bp, csrf):
    @bp.route("/")
    def simple_collection_panel():
        """통합 수집 관리 패널"""
        collection_service = current_app.extensions["collection_service"]

        try:
            stats = collection_service.get_collection_stats()
            history = collection_service.get_collection_history()
            template_data = {
                "total_collections": stats.get("total_collections", 0),
                "success_rate": stats.get("success_rate", 0),
                "last_collection_time": stats.get("last_collection_time", "없음"),
                "active_collections": stats.get("active_collections", 0),
                "collection_history": history,
            }
            return render_template("collection.html", **template_data)
        except Exception as exc:
            logger.error(f"Collection panel data loading failed: {exc}")
            return render_template(
                "collection.html",
                total_collections=0,
                success_rate=0,
                last_collection_time="없음",
                active_collections=0,
                collection_history=[],
            )

    @bp.route("/status")
    def panel_status():
        """패널 상태 정보"""
        return jsonify(
            {
                "status": "active",
                "message": "통합 수집 관리 패널이 정상 작동 중입니다",
                "features": ["인증정보 관리", "시스템 모니터링", "데이터 내보내기"],
            }
        )

    @bp.route("/api/save-credentials", methods=["POST"])
    @csrf.exempt
    def save_credentials():
        """UI에서 인증정보 저장 및 자동수집 활성화 (암호화)"""
        try:
            data = request.get_json()
            secure_credential_service = current_app.extensions["secure_credential_service"]

            regtech_username = data.get("regtech_username", "").strip()
            regtech_password = data.get("regtech_password", "").strip()
            if regtech_username and regtech_password:
                secure_credential_service.save_credentials(
                    "REGTECH",
                    regtech_username,
                    regtech_password,
                    {
                        "base_url": "https://regtech.fsec.or.kr",
                        "login_url": "/login/loginProcess",
                        "advisory_url": "/fcti/securityAdvisory/advisoryList",
                    },
                )
                logger.info("✅ REGTECH 인증 설정 완료 (암호화 저장)")

            fmg_host = data.get("fmg_host", "").strip()
            fmg_user = data.get("fmg_user", "admin").strip()
            fmg_password = data.get("fmg_password", "").strip()
            fmg_enabled = data.get("fmg_upload_enabled", False)
            fmg_interval = data.get("fmg_upload_interval", 300)

            if fmg_host and fmg_password:
                secure_credential_service.save_credentials(
                    "FORTIMANAGER",
                    fmg_user,
                    fmg_password,
                    {
                        "host": fmg_host,
                        "enabled": fmg_enabled,
                        "interval": fmg_interval,
                        "api_url": config.BLACKLIST_API_URL + "/api/fortinet/active-ips",
                        "filename": "nxtd-blacklist.txt",
                    },
                )
                logger.info("✅ FortiManager 인증 설정 완료 (암호화 저장)")

            if regtech_username and regtech_password:
                try:
                    scheduler = current_app.extensions.get("scheduler_service")
                    if scheduler and not scheduler.running:
                        scheduler.start()
                        logger.info("🔄 자동수집 스케줄러 시작됨")
                except Exception as scheduler_error:
                    logger.warning(f"스케줄러 시작 실패 (무시 가능): {scheduler_error}")
            else:
                logger.info("⚠️ REGTECH 인증 미설정 - 자동수집 비활성화")

            logger.info("인증정보가 성공적으로 저장되었습니다")
            return jsonify({"success": True, "message": "인증정보가 저장되었습니다"})
        except Exception as exc:
            logger.error(f"인증정보 저장 실패: {exc}")
            return jsonify({"success": False, "error": str(exc)})

    @bp.route("/api/load-credentials", methods=["GET"])
    def load_credentials():
        """저장된 인증정보 로드 (암호화된 데이터 복호화)"""
        try:
            secure_credential_service = current_app.extensions["secure_credential_service"]
            regtech_creds = secure_credential_service.get_credentials("REGTECH")
            regtech_username = regtech_creds.get("username", "") if regtech_creds else ""
            regtech_password = regtech_creds.get("password", "") if regtech_creds else ""

            fmg_creds = secure_credential_service.get_credentials("FORTIMANAGER")
            fmg_config = fmg_creds.get("config", {}) if fmg_creds else {}
            fmg_host = fmg_config.get("host", "")
            fmg_user = fmg_creds.get("username", "admin") if fmg_creds else "admin"
            fmg_password = fmg_creds.get("password", "") if fmg_creds else ""
            fmg_enabled = fmg_config.get("enabled", False)
            fmg_interval = fmg_config.get("interval", 300)

            return jsonify(
                {
                    "success": True,
                    "credentials": {
                        "regtech_username": regtech_username,
                        "regtech_password": regtech_password,
                        "fmg_host": fmg_host,
                        "fmg_user": fmg_user,
                        "fmg_password": fmg_password,
                        "fmg_upload_enabled": fmg_enabled,
                        "fmg_upload_interval": fmg_interval,
                    },
                }
            )
        except Exception as exc:
            logger.error(f"인증정보 로드 실패: {exc}")
            return jsonify({"success": False, "error": str(exc)})

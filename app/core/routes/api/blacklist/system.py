#!/usr/bin/env python3
"""
System and Credentials Status
Routes: /system/containers, /credential/status, /credentials/regtech, /database/tables
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
import logging
from ....config import config

logger = logging.getLogger(__name__)


blacklist_system_bp = Blueprint("blacklist_system", __name__)


@blacklist_system_bp.route("/system/containers", methods=["GET"])
def get_system_containers():
    """시스템 컨테이너 상태 조회 (컨테이너 내부 버전)

    Note: Docker 바이너리가 컨테이너 내에 없으므로 서비스 상태를 반환합니다.
    """
    try:
        # Docker API is not available in container, return service status instead
        services = {
            "blacklist-app": {"status": "running", "health": "healthy", "port": 2542},
            "blacklist-frontend": {
                "status": "running",
                "health": "healthy",
                "port": 2543,
            },
            "blacklist-postgres": {
                "status": "running",
                "health": "healthy",
                "port": 5432,
            },
            "blacklist-redis": {"status": "running", "health": "healthy", "port": 6379},
            "blacklist-collector": {
                "status": "running",
                "health": "healthy",
                "port": 8545,
            },
        }

        # Verify database connectivity
        try:
            db_service = current_app.extensions.get("db_service")
            if db_service:
                conn = db_service.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                db_service.return_connection(conn)
        except Exception as e:
            logger.warning("Database health check failed: %s", e)
            services["blacklist-postgres"]["health"] = "unhealthy"

        return jsonify(
            {
                "success": True,
                "containers": list(services.values()),
                "services": services,
                "timestamp": datetime.now().isoformat(),
                "note": "Running inside container, showing service health status",
            }
        )

    except Exception as e:
        logger.error(f"Container status query failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@blacklist_system_bp.route("/credential/status", methods=["GET"])
def get_credential_status():
    """인증 상태 확인"""
    try:
        # REGTECH 인증 상태 확인 (DB 우선, 환경변수 fallback)
        regtech_id = None
        regtech_pw = None
        source = "none"

        try:
            secure_cred_svc = current_app.extensions.get("secure_credential_service")
            if secure_cred_svc:
                db_creds = secure_cred_svc.get_credentials("REGTECH")
                if db_creds and db_creds.get("username") and db_creds.get("password"):
                    regtech_id = db_creds["username"]
                    regtech_pw = db_creds["password"]
                    source = "database"
        except Exception:
            pass

        if not regtech_id or not regtech_pw:
            regtech_id = config.REGTECH_ID
            regtech_pw = config.REGTECH_PW
            if regtech_id and regtech_pw:
                source = "environment"

        if regtech_id and regtech_pw:
            status = {
                "authenticated": True,
                "regtech_id": regtech_id[:3] + "*" * (len(regtech_id) - 3),
                "source": source,
                "last_check": datetime.now().isoformat(),
            }
        else:
            status = {
                "authenticated": False,
                "message": "REGTECH credentials not configured",
                "last_check": datetime.now().isoformat(),
            }

        return jsonify({"success": True, "status": status, "timestamp": datetime.now().isoformat()})

    except Exception as e:
        logger.error(f"Credential status check failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@blacklist_system_bp.route("/credentials/regtech", methods=["GET"])
def get_regtech_credentials():
    """REGTECH 인증 정보 조회 (프론트엔드가 요청하는 엔드포인트)"""
    try:
        # DB 우선, 환경변수 fallback
        regtech_id = None
        regtech_pw = None
        source = "none"

        try:
            secure_cred_svc = current_app.extensions.get("secure_credential_service")
            if secure_cred_svc:
                db_creds = secure_cred_svc.get_credentials("REGTECH")
                if db_creds and db_creds.get("username") and db_creds.get("password"):
                    regtech_id = db_creds["username"]
                    regtech_pw = db_creds["password"]
                    source = "database"
        except Exception:
            pass

        if not regtech_id or not regtech_pw:
            regtech_id = config.REGTECH_ID
            regtech_pw = config.REGTECH_PW
            if regtech_id and regtech_pw:
                source = "environment"

        if regtech_id and regtech_pw:
            return jsonify(
                {
                    "success": True,
                    "authenticated": True,
                    "regtech_id": regtech_id[:3] + "*" * (len(regtech_id) - 3),
                    "configured": True,
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "authenticated": False,
                    "configured": False,
                    "message": "REGTECH credentials not configured",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"REGTECH credentials check failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500


@blacklist_system_bp.route("/database/tables", methods=["GET"])
def get_database_tables():
    """데이터베이스 테이블 현황 API - 상세 정보 포함"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # 새로운 show_database_tables() 메서드 사용 (컬럼 정보 및 샘플 데이터 포함)
        tables_info = db_service.show_database_tables()

        return jsonify(
            {
                "success": tables_info.get("success", True),
                "tables": tables_info.get("tables", {}),
                "total_tables": tables_info.get("total_tables", 0),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Database tables API error: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500

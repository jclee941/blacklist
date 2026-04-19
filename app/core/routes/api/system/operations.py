"""Operational system endpoints for the shared system API blueprint."""

from . import common


@common.api_bp.route("/logs", methods=["GET"])
def get_system_logs():
    """
    시스템 로그 조회 (Phase 1.4: Standardized Error Handling)

    GET /api/logs

    Returns:
        {
            "success": True,
            "data": {
                "logs": [...],
                "total_lines": 100
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        InternalServerError: Log file read failed
    """
    try:
        import os

        log_file = "/app/logs/collector.log"
        if not os.path.exists(log_file):
            return common.jsonify(
                {
                    "success": True,
                    "data": {
                        "logs": ["로그 파일을 찾을 수 없습니다."],
                        "total_lines": 0,
                    },
                    "timestamp": common.datetime.now().isoformat(),
                    "request_id": common.g.request_id,
                }
            ), 200

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        recent_logs = lines[-100:] if len(lines) > 100 else lines

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "logs": [line.strip() for line in recent_logs],
                    "total_lines": len(recent_logs),
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"System logs error: {e}", exc_info=True)
        raise common.internal_server_error_cls(
            message="Failed to read system logs",
            details={"log_file": "/app/logs/collector.log", "error_type": type(e).__name__},
        )


@common.api_bp.route("/auth/status", methods=["GET"])
def get_auth_status():
    """
    인증 상태 확인 (Phase 1.4: Standardized Error Handling)

    GET /api/auth/status

    Returns:
        {
            "success": True,
            "data": {
                "has_regtech_credentials": true,
                "regtech_configured": true
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        InternalServerError: Credential service failed
    """
    try:
        regtech_config_service = common.current_app.extensions["regtech_config_service"]
        credentials = regtech_config_service.get_credentials()
        has_credentials = bool(credentials and credentials.get("regtech_id"))

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "has_regtech_credentials": has_credentials,
                    "regtech_configured": has_credentials,
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except Exception as e:
        common.logger.error(f"Auth status error: {e}", exc_info=True)
        raise common.internal_server_error_cls(
            message="Failed to retrieve authentication status",
            details={"error_type": type(e).__name__},
        )


@common.api_bp.route("/reset-database", methods=["POST"])
def reset_database():
    """
    데이터베이스 초기화 - 긴급 복구용 (Phase 1.4: Standardized Error Handling)

    POST /api/reset-database
    Header: X-Admin-Key: <admin_key>

    Returns:
        {
            "success": True,
            "data": {
                "message": "...",
                "deleted_tables": [...],
                "reset_timestamp": "..."
            },
            "timestamp": "...",
            "request_id": "..."
        }

    Raises:
        UnauthorizedError: Missing or invalid admin key
        DatabaseError: Database reset operation failed
    """
    expected_key = common.config.ADMIN_RESET_KEY
    if not expected_key:
        raise common.unauthorized_error_cls(
            message="ADMIN_RESET_KEY environment variable not configured",
            details={"header": "X-Admin-Key"},
        )

    auth_key = common.request.headers.get("X-Admin-Key")
    if auth_key != expected_key:
        raise common.unauthorized_error_cls(
            message="Invalid or missing admin key for database reset",
            details={"header": "X-Admin-Key"},
        )

    try:
        db_service = common.current_app.extensions["db_service"]

        db_service.execute_query("DELETE FROM blacklist_ips")
        db_service.execute_query("DELETE FROM collection_history")
        db_service.execute_query("DELETE FROM collection_stats")
        db_service.execute_query("ALTER SEQUENCE blacklist_ips_id_seq RESTART WITH 1")

        common.logger.warning("🚨 데이터베이스 초기화 실행됨 - 모든 데이터 삭제")

        return common.jsonify(
            {
                "success": True,
                "data": {
                    "message": "데이터베이스 초기화 완료",
                    "deleted_tables": [
                        "blacklist_ips",
                        "collection_history",
                        "collection_stats",
                    ],
                    "reset_timestamp": common.datetime.now().isoformat(),
                },
                "timestamp": common.datetime.now().isoformat(),
                "request_id": common.g.request_id,
            }
        ), 200

    except common.UnauthorizedError:
        raise
    except Exception as e:
        common.logger.error(f"Database reset error: {e}", exc_info=True)
        raise common.database_error_cls(message=f"Failed to reset database: {type(e).__name__}")

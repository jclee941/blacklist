"""
Collection API Credentials Operations
Handles credential management
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app
from core.exceptions import (
    ValidationError,
    BadRequestError,
    NotFoundError,
    DatabaseError,
    ForbiddenError,
)
from .utils import (
    call_collector_api,
    interval_seconds_to_string,
    interval_string_to_seconds,
)

logger = logging.getLogger(__name__)

collection_credentials_bp = Blueprint("collection_credentials", __name__)
ALLOWED_SOURCES = ("REGTECH", "SECUDIUM")


@collection_credentials_bp.route("/credentials", methods=["GET"])
def list_credentials():
    """List all available credential sources"""
    secure_credential_service = current_app.extensions.get("secure_credential_service")
    if not secure_credential_service:
        from core.services.secure_credential_service import secure_credential_service

    sources = ["REGTECH", "SECUDIUM"]
    result = []

    for source in sources:
        try:
            creds = secure_credential_service.get_credentials(source)
            result.append({
                "source": source,
                "configured": creds is not None,
                "enabled": creds.get("enabled", False) if creds else False,
            })
        except Exception:
            result.append({"source": source, "configured": False, "enabled": False})

    return jsonify({
        "success": True,
        "data": result,
        "timestamp": datetime.now().isoformat(),
        "request_id": g.request_id,
    })


@collection_credentials_bp.route("/credentials/<source>", methods=["GET", "PUT"])
def manage_credentials(source: str):
    """
    Get or update collection credentials
    """
    source_upper = source.upper()

    # Validate source parameter
    if source_upper not in ALLOWED_SOURCES:
        raise ValidationError(
            message=f"Invalid source: {source}. Must be one of {[s.lower() for s in ALLOWED_SOURCES]}",
            field="source",
            details={
                "provided_value": source,
                "allowed_values": [s.lower() for s in ALLOWED_SOURCES],
            },
        )

    # Use secure_credential_service for all operations (via dependency injection)
    secure_credential_service = current_app.extensions.get("secure_credential_service")

    # Fallback to direct import if not in extensions (should be there)
    if not secure_credential_service:
        from core.services.secure_credential_service import secure_credential_service

    try:
        if request.method == "GET":
            # Get credentials via secure service
            credentials = secure_credential_service.get_credentials(source_upper)

            if not credentials:
                raise NotFoundError(
                    message=f"Credentials not found for {source_upper}",
                    resource="collection_credentials",
                    details={"source": source_upper},
                )

            response_data = {
                        "service_name": credentials["service_name"],
                        "username": credentials["username"],
                        "password": "***masked***",
                        "enabled": credentials.get("enabled", True),
                        "collection_interval": interval_seconds_to_string(
                            credentials.get("collection_interval", 86400)
                        ),
                        "last_collection": credentials["last_collection"].isoformat()
                        if credentials.get("last_collection")
                        else None,
                    }

            # Include Secudium OTP config fields
            if source_upper == "SECUDIUM":
                config = credentials.get("config", {})
                response_data["otp_mode"] = config.get("otp_mode", "auto")
                response_data["email"] = config.get("email", "")
                response_data["imap_server"] = config.get("imap_server", "imap.kakao.com")

            return jsonify(
                {
                    "success": True,
                    "data": response_data,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            )

        elif request.method == "PUT":
            # Update credentials
            data = request.get_json()
            if not data:
                raise BadRequestError(
                    message="Missing request body",
                    details={"field": "body"},
                )

            # Validate required fields
            username = data.get("username")
            password = data.get("password")
            enabled = data.get("enabled", True)
            collection_interval = data.get("collection_interval", "daily")

            if not username:
                raise BadRequestError(
                    message="Username is required",
                    details={"field": "username"},
                )

            # Convert interval to seconds
            interval_seconds = interval_string_to_seconds(collection_interval)

            # Build config for Secudium OTP settings
            config = {}
            if source_upper == "SECUDIUM":
                config = {
                    "otp_mode": data.get("otp_mode", "auto"),
                    "email": data.get("email", ""),
                    "email_password": data.get("email_password", ""),
                    "imap_server": data.get("imap_server", "imap.kakao.com"),
                }

            # Determine if we have a new password provided
            has_new_password = password and password != "***masked***"

            if has_new_password:
                success = secure_credential_service.save_credentials(
                    service_name=source_upper,
                    username=username,
                    password=password,
                    config=config,
                    enabled=enabled,
                    collection_interval=interval_seconds,
                )

                if not success:
                    raise DatabaseError(
                        message=f"Failed to save credentials securely for {source_upper}",
                    )
            else:
                current_creds = secure_credential_service.get_credentials(source_upper)
                if not current_creds:
                    raise NotFoundError(
                        message=f"Credentials not found for {source_upper}. Please provide a password to create new credentials.",
                        resource="collection_credentials",
                        details={"source": source_upper},
                    )

                success = secure_credential_service.update_credential_settings(
                    service_name=source_upper,
                    username=username,
                    enabled=enabled,
                    collection_interval=interval_seconds,
                )

                if not success:
                    raise DatabaseError(
                        message=f"Failed to update credential settings for {source_upper}",
                    )

            logger.info(f"✅ Updated credentials for {source_upper}")

            # Restart scheduler to pick up new credentials
            restart_result = call_collector_api("/api/scheduler/restart", method="POST")

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "message": f"Credentials updated for {source_upper}",
                        "scheduler_restart": restart_result.get("success", False),
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except Exception:
        raise


@collection_credentials_bp.route("/credentials/secudium/otp", methods=["POST"])
def submit_secudium_otp():
    """Submit OTP code for Secudium manual authentication"""
    data = request.get_json()
    if not data:
        raise ValidationError(message="요청 데이터가 없습니다")

    otp_code = data.get("otp_code", "").strip()
    session_id = data.get("session_id", "").strip()

    if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
        raise ValidationError(
            message="유효하지 않은 OTP 코드입니다",
            details={"expected": "6자리 숫자"},
        )

    result = call_collector_api(
        "/api/test-auth/secudium/otp",
        method="POST",
        json_data={"otp_code": otp_code, "session_id": session_id},
    )

    if result.get("success"):
        return jsonify(
            {
                "success": True,
                "data": {"status": "connected", "message": "OTP 인증 성공"},
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    error_detail = result.get("error", "OTP 인증 실패")
    return jsonify(
        {
            "success": True,
            "data": {"status": "failed", "message": error_detail},
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    ), 200


@collection_credentials_bp.route("/credentials/<source>/test", methods=["POST"])
def test_credentials(source: str):
    """Test credentials by attempting to authenticate with the collector service"""
    try:
        source_upper = source.upper()
        if source_upper not in ALLOWED_SOURCES:
            raise ValidationError(
                message=f"지원하지 않는 소스입니다: {source}",
                details={"allowed_sources": list(ALLOWED_SOURCES)},
            )

        result = call_collector_api(
            f"/api/test-auth/{source_upper}",
            method="POST",
        )

        collector_data = result if isinstance(result, dict) else {}

        # Handle Secudium OTP intermediate response
        if collector_data.get("otp_required"):
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "status": "otp_required",
                        "message": "OTP 입력이 필요합니다",
                        "session_id": collector_data.get("session_id", ""),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        if collector_data.get("success"):
            return jsonify(
                {
                    "success": True,
                    "data": {"status": "connected", "message": "인증 성공"},
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        # Authentication failed - check if account is locked
        error_msg = collector_data.get("error", "").lower()
        error_code = collector_data.get("error_code", "")

        if (
            "잠긴" in str(error_msg)
            or "locked" in str(error_msg)
            or error_code == "user.is.locked"
        ):
            raise ForbiddenError(
                message="계정이 잠겼습니다",
                details={"source": source_upper, "error_code": error_code},
            )
        else:
            error_detail = collector_data.get("error", "알 수 없는 오류")
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "status": "failed",
                        "message": f"{source_upper} 인증 실패"
                        if error_detail == "인증 실패"
                        else f"인증 실패: {error_detail}",
                        "error_code": error_code,
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

    except Exception:
        raise

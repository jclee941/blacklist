"""
Collection API Credentials Operations
Handles credential management
"""

import logging
import requests
from datetime import datetime
from flask import Blueprint, jsonify, request, g, current_app
from ....exceptions import (
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
ALLOWED_SOURCES = ("REGTECH", "CLOUDFLARE")


@collection_credentials_bp.route("/credentials", methods=["GET"])
def list_credentials():
    """List all available credential sources"""
    secure_credential_service = current_app.extensions.get("secure_credential_service")
    if not secure_credential_service:
        from core.services.secure_credential_service import secure_credential_service

    sources = ["REGTECH", "CLOUDFLARE"]
    result = []

    for source in sources:
        try:
            creds = secure_credential_service.get_credentials(source)
            result.append(
                {
                    "source": source,
                    "configured": creds is not None,
                    "enabled": creds.get("enabled", False) if creds else False,
                }
            )
        except Exception as e:
            logger.warning("Failed to get credentials for source %s: %s", source, e)
            result.append({"source": source, "configured": False, "enabled": False})

    return jsonify(
        {
            "success": True,
            "data": result,
            "timestamp": datetime.now().isoformat(),
            "request_id": g.request_id,
        }
    )


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
                # Unconfigured credentials is a valid state, not an error.
                # Return 200 with defaults so the frontend polling loop
                # doesn't generate 404s every 30 seconds.
                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "service_name": source_upper,
                            "username": "",
                            "password": "",
                            "config": {},
                            "enabled": False,
                            "collection_interval": "daily",
                            "last_collection": None,
                            "connection_status": "unknown",
                        },
                        "timestamp": datetime.now().isoformat(),
                        "request_id": g.request_id,
                    }
                )

            response_data = {
                "service_name": credentials["service_name"],
                "username": credentials["username"],
                "password": "***masked***",
                "config": credentials.get("config", {}),
                "enabled": credentials.get("enabled", True),
                "collection_interval": interval_seconds_to_string(credentials.get("collection_interval", 86400)),
                "last_collection": credentials["last_collection"].isoformat()
                if credentials.get("last_collection")
                else None,
            }

            return jsonify(
                {
                    "success": True,
                    "data": response_data,
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            )

        else:
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

            if source_upper == "CLOUDFLARE":
                username = username or "cloudflare-api"
            elif not username:
                raise BadRequestError(
                    message="Username is required",
                    details={"field": "username"},
                )

            # Convert interval to seconds
            interval_seconds = interval_string_to_seconds(collection_interval)

            config = {}
            if source_upper == "CLOUDFLARE":
                config = {
                    "account_id": data.get("account_id", ""),
                    "list_id": data.get("list_id", ""),
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
                        message=(
                            f"Credentials not found for {source_upper}. "
                            "Please provide a password to create new credentials."
                        ),
                        resource="collection_credentials",
                        details={"source": source_upper},
                    )

                if source_upper == "CLOUDFLARE":
                    success = secure_credential_service.save_credentials(
                        service_name=source_upper,
                        username=username,
                        password=current_creds.get("password", ""),
                        config=config,
                        enabled=enabled,
                        collection_interval=interval_seconds,
                    )
                else:
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

    except Exception as e:
        logger.error("manage_credentials failed: %s", e)
        raise


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

        if source_upper == "CLOUDFLARE":
            secure_credential_service = current_app.extensions.get("secure_credential_service")
            if not secure_credential_service:
                from core.services.secure_credential_service import secure_credential_service

            credentials = secure_credential_service.get_credentials(source_upper)
            result = _test_cloudflare_connection(credentials or {})

            return jsonify(
                {
                    "success": result.get("success", False),
                    "data": {
                        "status": "connected" if result.get("success") else "failed",
                        "message": result.get("message", "Unknown error"),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        result = call_collector_api(
            f"/api/test-auth/{source_upper}",
            method="POST",
        )

        collector_data = result if isinstance(result, dict) else {}

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

        if "잠긴" in str(error_msg) or "locked" in str(error_msg) or error_code == "user.is.locked":
            raise ForbiddenError(message=f"계정이 잠겼습니다 ({source_upper}, {error_code})")
        else:
            error_detail = collector_data.get("error", "알 수 없는 오류")
            return jsonify(
                {
                    "success": False,
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

    except Exception as e:
        logger.error("test_credentials failed: %s", e)
        raise


def _test_cloudflare_connection(credentials):
    """Test Cloudflare Lists API connection"""
    api_token = credentials.get("password", "")
    config = credentials.get("config", {})
    account_id = config.get("account_id", "")
    list_id = config.get("list_id", "")

    if not all([api_token, account_id, list_id]):
        return {"success": False, "message": "Missing required fields (api_token, account_id, list_id)"}

    try:
        response = requests.get(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/rules/lists/{list_id}",
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            timeout=10,
        )
        data = response.json()
        if data.get("success"):
            result = data.get("result", {})
            return {
                "success": True,
                "message": f"Connected. List: {result.get('name', 'unknown')}, Items: {result.get('num_items', 0)}",
            }
        errors = data.get("errors", [])
        return {
            "success": False,
            "message": f"API error: {errors[0].get('message', 'Unknown') if errors else 'Unknown'}",
        }
    except requests.RequestException as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}

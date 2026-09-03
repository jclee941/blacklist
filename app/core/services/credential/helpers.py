"""Compatibility helpers for REGTECH credential operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import current_app
from werkzeug.local import LocalProxy

secure_credential_service = LocalProxy(lambda: current_app.extensions["secure_credential_service"])


def save_regtech_credentials(username: str, password: str) -> bool:
    """Save REGTECH credentials through the secure service."""
    config = {
        "base_url": "https://regtech.fsec.or.kr",
        "login_url": "/login/loginProcess",
        "advisory_url": "/advisory/advisory01_search",
        "timeout_seconds": 30,
        "max_pages": 100,
        "items_per_page": 50,
        "request_delay_seconds": 1,
    }
    return secure_credential_service.save_credentials("REGTECH", username, password, config)


def get_regtech_credentials() -> Optional[Dict[str, Any]]:
    """Get REGTECH credentials through the secure service."""
    return secure_credential_service.get_credentials("REGTECH")


def validate_regtech_credentials() -> Dict[str, Any]:
    """Validate REGTECH credentials through the secure service."""
    return secure_credential_service.validate_credentials("REGTECH")


def delete_regtech_credentials() -> bool:
    """Delete REGTECH credentials through the secure service."""
    return secure_credential_service.delete_credentials("REGTECH")


def validate_credentials(service: Any, service_name: str, logger: Any) -> Dict[str, Any]:
    """Validate stored credentials for a service."""
    try:
        credentials = service.get_credentials(service_name)

        if not credentials:
            return {
                "valid": False,
                "error": "인증정보가 존재하지 않음",
                "service_name": service_name,
            }

        username = credentials.get("username", "").strip()
        password = credentials.get("password", "").strip()

        if not username or not password:
            return {
                "valid": False,
                "error": "사용자명 또는 비밀번호가 비어있음",
                "service_name": service_name,
                "username": username,
            }

        return {
            "valid": True,
            "service_name": service_name,
            "username": username,
            "encrypted": credentials.get("encrypted", False),
            "created_at": credentials.get("created_at"),
            "updated_at": credentials.get("updated_at"),
        }
    except Exception as exc:
        logger.error(f"❌ {service_name} 인증정보 검증 실패: {exc}")
        return {"valid": False, "error": str(exc), "service_name": service_name}


def migrate_existing_credentials(service: Any, logger: Any) -> Dict[str, Any]:
    """Migrate plaintext credentials to the encrypted storage format."""
    try:
        with service._get_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT service_name, username, password, config
                FROM collection_credentials
                WHERE (encrypted = false OR encrypted IS NULL)
                AND is_active = true
                AND password IS NOT NULL
                AND password != ''
                """
            )
            results = cursor.fetchall()
            cursor.close()

        migrated_count = 0
        errors = []

        for row in results:
            service_name, username, password, config = row

            try:
                if service.save_credentials(service_name, username, password, config if config else {}):
                    migrated_count += 1
                    logger.info(f"✅ {service_name} 인증정보 마이그레이션 완료")
                else:
                    errors.append(f"{service_name}: 저장 실패")
            except Exception as exc:
                errors.append(f"{service_name}: {str(exc)}")
                logger.error(f"❌ {service_name} 마이그레이션 실패: {exc}")

        return {
            "success": True,
            "migrated_count": migrated_count,
            "total_found": len(results),
            "errors": errors,
        }
    except Exception as exc:
        logger.error(f"❌ 인증정보 마이그레이션 실패: {exc}")
        return {"success": False, "error": str(exc), "migrated_count": 0}

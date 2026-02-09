#!/usr/bin/env python3
"""
Manual IP Management
Routes: /blacklist/manual-add, /whitelist/manual-add, /whitelist/list
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import logging
from ....exceptions import BadRequestError, ConflictError, NotFoundError
import re

from core.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)


blacklist_management_bp = Blueprint("blacklist_management", __name__)


def validate_ip_address(ip_address):
    """Validate IPv4 address format and range"""
    # IP 주소 형식 검증 (IPv4)
    ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(ip_pattern, ip_address):
        return False, "유효하지 않은 IP 주소 형식입니다"

    # 각 옥텟이 0-255 범위인지 확인
    octets = ip_address.split(".")
    for octet in octets:
        if int(octet) > 255:
            return False, "IP 주소 범위가 올바르지 않습니다 (0-255)"

    return True, None


@blacklist_management_bp.route("/blacklist/manual-add", methods=["POST"])
@rate_limit("20 per hour; 5 per minute")  # State-changing operation
def manual_add_ip():
    """수동 IP 등록 API (블랙리스트)"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # 요청 데이터 검증
        data = request.get_json() or {}
        ip_address = data.get("ip_address", "").strip()
        country = data.get("country", "UNKNOWN").strip()
        notes = data.get("notes", "").strip()

        if not ip_address:
            raise BadRequestError("IP address is required", details={"field": "ip_address"})

        valid, error_msg = validate_ip_address(ip_address)
        if not valid:
            raise BadRequestError(error_msg or "Invalid IP address", details={"ip_address": ip_address})

        existing = db_service.query(
            "SELECT COUNT(*) as count FROM blacklist_ips WHERE ip_address = %s",
            (ip_address,),
        )
        if existing and existing[0]["count"] > 0:
            raise ConflictError(
                "IP address already exists in blacklist",
                details={"ip_address": ip_address},
            )

        # DB에 저장
        conn = db_service.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO blacklist_ips
            (ip_address, source, country, detection_date, last_seen, detection_count, created_at, updated_at)
            VALUES (%s, %s, %s, CURRENT_DATE, NOW(), 1, NOW(), NOW())
        """,
            (ip_address, "MANUAL", country),
        )

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Manual IP added to blacklist: {ip_address} (country: {country})")

        return jsonify(
            {
                "success": True,
                "message": "IP 주소가 성공적으로 등록되었습니다",
                "data": {
                    "ip_address": ip_address,
                    "source": "MANUAL",
                    "country": country,
                    "notes": notes,
                    "created_at": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except (BadRequestError, ConflictError):
        raise
    except Exception as e:
        logger.error(f"Manual IP add failed: {e}")
        raise


@blacklist_management_bp.route("/blacklist/remove/<ip_address>", methods=["DELETE"])
@rate_limit("20 per hour; 5 per minute")  # State-changing operation
def manual_remove_ip(ip_address):
    """수동 IP 제거 API (블랙리스트)"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # IP 주소 형식 검증
        valid, error_msg = validate_ip_address(ip_address)
        if not valid:
            raise BadRequestError(error_msg or "Invalid IP address", details={"ip_address": ip_address})

        # IP 존재 여부 확인
        existing = db_service.query(
            "SELECT COUNT(*) as count FROM blacklist_ips WHERE ip_address = %s",
            (ip_address,),
        )
        if not existing or existing[0]["count"] == 0:
            raise NotFoundError(
                "IP address not found in blacklist",
                resource="blacklist_ips",
                details={"ip_address": ip_address},
            )

        # DB에서 삭제
        conn = db_service.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM blacklist_ips WHERE ip_address = %s", (ip_address,))

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Manual IP removed from blacklist: {ip_address}")

        return jsonify(
            {
                "success": True,
                "message": "IP 주소가 블랙리스트에서 성공적으로 제거되었습니다",
                "data": {
                    "ip_address": ip_address,
                    "removed_at": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except (BadRequestError, NotFoundError):
        raise
    except Exception as e:
        logger.error(f"Manual IP removal failed: {e}")
        raise


@blacklist_management_bp.route("/whitelist/manual-add", methods=["POST"])
@rate_limit("20 per hour; 5 per minute")  # State-changing operation
def manual_add_whitelist_ip():
    """수동 IP 등록 API (화이트리스트)"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # 요청 데이터 검증
        data = request.get_json() or {}
        ip_address = data.get("ip_address", "").strip()
        country = data.get("country", "UNKNOWN").strip()
        reason = data.get("reason", "수동 등록").strip()

        if not ip_address:
            raise BadRequestError("IP address is required", details={"field": "ip_address"})

        valid, error_msg = validate_ip_address(ip_address)
        if not valid:
            raise BadRequestError(error_msg or "Invalid IP address", details={"ip_address": ip_address})

        existing = db_service.query(
            "SELECT COUNT(*) as count FROM whitelist_ips WHERE ip_address = %s",
            (ip_address,),
        )
        if existing and existing[0]["count"] > 0:
            raise ConflictError(
                "IP address already exists in whitelist",
                details={"ip_address": ip_address},
            )

        # DB에 저장
        conn = db_service.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO whitelist_ips
            (ip_address, source, country, reason, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        """,
            (ip_address, "MANUAL", country, reason),
        )

        conn.commit()
        cursor.close()
        db_service.return_connection(conn)

        logger.info(f"✅ Manual IP added to whitelist: {ip_address} (country: {country}, reason: {reason})")

        return jsonify(
            {
                "success": True,
                "message": "IP 주소가 화이트리스트에 성공적으로 등록되었습니다",
                "data": {
                    "ip_address": ip_address,
                    "source": "MANUAL",
                    "country": country,
                    "reason": reason,
                    "created_at": datetime.now().isoformat(),
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except (BadRequestError, ConflictError):
        raise
    except Exception as e:
        logger.error(f"Manual whitelist IP add failed: {e}")
        raise


@blacklist_management_bp.route("/whitelist/list", methods=["GET"])
def get_whitelist_list():
    """화이트리스트 목록 조회 API"""
    try:
        # Use dependency injection via app.extensions
        db_service = current_app.extensions["db_service"]

        # 페이지네이션 파라미터
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        offset = (page - 1) * per_page

        # 데이터베이스 조회 (parameterized query for security)
        whitelist_data = db_service.query(
            "SELECT * FROM whitelist_ips ORDER BY id DESC LIMIT %s OFFSET %s",
            (per_page, offset),
        )

        total_count = db_service.query("SELECT COUNT(*) as count FROM whitelist_ips")[0]["count"]

        return jsonify(
            {
                "success": True,
                "data": whitelist_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "pages": (total_count + per_page - 1) // per_page,
                },
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Whitelist list API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

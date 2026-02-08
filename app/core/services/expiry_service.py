"""
IP 만료/해제일 관리 서비스
해제일이 지난 IP들을 자동으로 비활성화
"""

import logging
from datetime import date
from typing import Dict, Any

logger = logging.getLogger(__name__)


class IPExpiryService:
    """IP 만료 관리 서비스"""

    def __init__(self, db_service=None):
        """
        Initialize IP expiry service

        Args:
            db_service: DatabaseService instance for connection pool access
        """
        self.db_service = db_service

    def check_and_deactivate_expired_ips(self) -> Dict[str, Any]:
        """해제일이 지난 IP들을 비활성화"""
        try:
            today = date.today()

            # 해제일이 지났지만 아직 활성화된 IP들 조회
            expired_ips = self.db_service.query(
                """
                SELECT id, ip_address, source, removal_date
                FROM blacklist_ips
                WHERE removal_date IS NOT NULL
                AND removal_date < %s
                AND is_active = true
                """,
                (today,),
            )

            if not expired_ips:
                logger.info("만료된 IP가 없습니다.")
                return {
                    "success": True,
                    "expired_count": 0,
                    "message": "만료된 IP가 없습니다.",
                }

            # 만료된 IP들을 비활성화
            expired_ids = [ip["id"] for ip in expired_ips]

            updated_count = self.db_service.execute(
                """
                UPDATE blacklist_ips
                SET is_active = false,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
                """,
                (expired_ids,),
            )

            logger.info(f"만료된 IP {updated_count}개를 비활성화했습니다.")

            # 만료된 IP 목록 로그
            for ip in expired_ips:
                logger.info(f"비활성화: {ip['ip_address']} (소스: {ip['source']}, 해제일: {ip['removal_date']})")

            return {
                "success": True,
                "expired_count": updated_count,
                "expired_ips": [
                    {
                        "ip_address": ip["ip_address"],
                        "source": ip["source"],
                        "removal_date": (ip["removal_date"].isoformat() if ip["removal_date"] else None),
                    }
                    for ip in expired_ips
                ],
                "message": f"{updated_count}개의 만료된 IP를 비활성화했습니다.",
            }

        except Exception as e:
            logger.error(f"IP 만료 처리 실패: {e}")
            return {"success": False, "error": str(e), "expired_count": 0}

    def get_expiry_stats(self) -> Dict[str, Any]:
        """만료 관련 통계 반환"""
        try:
            today = date.today()

            # 통계 쿼리
            stats_result = self.db_service.query(
                """
                SELECT
                    COUNT(*) as total_ips,
                    COUNT(CASE WHEN is_active = true THEN 1 END) as active_ips,
                    COUNT(CASE WHEN is_active = false THEN 1 END) as inactive_ips,
                    COUNT(CASE WHEN removal_date IS NOT NULL AND removal_date < %s AND is_active = true THEN 1 END) as pending_expiry,
                    COUNT(CASE WHEN removal_date IS NOT NULL AND removal_date >= %s THEN 1 END) as future_expiry
                FROM blacklist_ips
                """,
                (today, today),
            )

            stats = stats_result[0] if stats_result else {}

            return {
                "success": True,
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "inactive_ips": stats.get("inactive_ips", 0),
                "pending_expiry": stats.get("pending_expiry", 0),
                "future_expiry": stats.get("future_expiry", 0),
                "check_date": today.isoformat(),
            }

        except Exception as e:
            logger.error(f"만료 통계 조회 실패: {e}")
            return {"success": False, "error": str(e)}

    def manually_expire_ip(self, ip_address: str, source: str = None) -> Dict[str, Any]:
        """특정 IP를 수동으로 만료/비활성화"""
        try:
            # IP 조회
            if source:
                ip_records = self.db_service.query(
                    "SELECT id, ip_address, source, is_active FROM blacklist_ips WHERE ip_address = %s AND source = %s",
                    (ip_address, source),
                )
            else:
                ip_records = self.db_service.query(
                    "SELECT id, ip_address, source, is_active FROM blacklist_ips WHERE ip_address = %s",
                    (ip_address,),
                )

            ip_record = ip_records[0] if ip_records else None

            if not ip_record:
                return {
                    "success": False,
                    "error": f"IP {ip_address}를 찾을 수 없습니다.",
                }

            if not ip_record["is_active"]:
                return {
                    "success": False,
                    "error": f"IP {ip_address}는 이미 비활성화되어 있습니다.",
                }

            # IP 비활성화
            self.db_service.query(
                """
                UPDATE blacklist_ips
                SET is_active = false,
                    removal_date = CURRENT_DATE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (ip_record["id"],),
            )

            logger.info(f"수동 만료: {ip_address} (소스: {ip_record['source']})")

            return {
                "success": True,
                "message": f"IP {ip_address}를 성공적으로 비활성화했습니다.",
                "ip_address": ip_address,
                "source": ip_record["source"],
            }

        except Exception as e:
            logger.error(f"수동 IP 만료 실패: {e}")
            return {"success": False, "error": str(e)}


from flask import current_app
from werkzeug.local import LocalProxy

expiry_service = LocalProxy(lambda: current_app.extensions["expiry_service"])

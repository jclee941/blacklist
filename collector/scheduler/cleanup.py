from __future__ import annotations

import logging
from typing import Any

from .dependencies import db_service

logger = logging.getLogger(f"{__package__}.operations")


def cleanup_expired_ips(database: Any = db_service) -> None:
    try:
        logger.info("🧹 만료된 IP 정리 시작")
        with database.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = false
                WHERE is_active = true
                  AND removal_date IS NOT NULL
                  AND removal_date < CURRENT_DATE
                """
            )
            expired_count = cursor.rowcount
            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = false, updated_at = NOW()
                WHERE is_active = true
                  AND detection_date < CURRENT_DATE - INTERVAL '3 months'
                  AND (removal_date IS NULL OR removal_date < CURRENT_DATE)
                """
            )
            old_count = cursor.rowcount
            cursor.execute(
                """
                UPDATE blacklist_ips
                SET is_active = true, updated_at = NOW()
                WHERE is_active = false
                  AND removal_date IS NOT NULL
                  AND removal_date >= CURRENT_DATE
                """
            )
            reactivated_count = cursor.rowcount
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
            active_count = cursor.fetchone()[0]
            cursor.close()

        logger.info(
            "✅ 만료된 IP 정리 완료: 만료 %s개, 3개월+ %s개 비활성화, %s개 재활성화 (활성 IP: %s개)",
            expired_count,
            old_count,
            reactivated_count,
            f"{active_count:,}",
        )
    except Exception as exc:
        logger.error("❌ 만료된 IP 정리 오류: %s", exc)

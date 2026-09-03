"""
Collection persistence helpers
수집 데이터 저장 책임 분리
"""

from datetime import datetime
from typing import Any, Dict, List

import logging

from ..database_lease import connection_lease

logger = logging.getLogger(__name__)


def save_collection_data(db_service, source: str, data: List[Dict[str, Any]]) -> bool:
    """수집된 데이터를 데이터베이스에 저장 (v3.3.5 - detection_date/removal_date 지원)"""
    try:
        with connection_lease(db_service) as conn:
            cursor = conn.cursor()
            for item in data:
                cursor.execute(
                    """
                    INSERT INTO blacklist_ips (
                        ip_address, source, reason, confidence_level,
                        detection_count, is_active, country, detection_date, removal_date,
                        last_seen, created_at, raw_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ip_address, source) DO UPDATE SET
                        detection_count = blacklist_ips.detection_count + 1,
                        last_seen = EXCLUDED.last_seen,
                        reason = COALESCE(EXCLUDED.reason, blacklist_ips.reason),
                        country = COALESCE(EXCLUDED.country, blacklist_ips.country),
                        detection_date = COALESCE(EXCLUDED.detection_date, blacklist_ips.detection_date),
                        removal_date = COALESCE(EXCLUDED.removal_date, blacklist_ips.removal_date),
                        is_active = CASE
                            WHEN COALESCE(EXCLUDED.removal_date, blacklist_ips.removal_date) < CURRENT_DATE
                            THEN false
                            ELSE EXCLUDED.is_active
                        END,
                        raw_data = EXCLUDED.raw_data,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        item["ip_address"],
                        item["source"],
                        item.get("reason"),
                        item.get("confidence_level", 50),
                        item.get("detection_count", 1),
                        item.get("is_active", True),
                        item.get("country"),
                        item.get("detection_date"),
                        item.get("removal_date"),
                        item.get("last_seen", datetime.now()),
                        datetime.now(),
                        item.get("raw_data", {}),
                    ),
                )

            conn.commit()
            cursor.close()
        logger.info(f"Saved {len(data)} items from {source}")
        return True

    except Exception as e:
        logger.error(f"Failed to save collection data: {e}")
        return False

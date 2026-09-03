import logging
from datetime import date, datetime
from typing import Optional

from .database_lease import connection_lease

logger = logging.getLogger(__name__)
RowValue = str | int | float | bool | date | datetime | None


class BlacklistRepository:
    def __init__(self, db_service):
        self.db = db_service

    def count_whitelist_by_ip(self, ip: str) -> int:
        result = self.db.query(
            """
            SELECT COUNT(*) as count FROM whitelist_ips
            WHERE ip_address = %s AND is_active = true
            """,
            (ip,),
        )
        return result[0]["count"] if result else 0

    def get_blacklist_entry(self, ip: str) -> Optional[dict[str, RowValue]]:
        results = self.db.query(
            """
            SELECT ip_address, reason, source, detection_count
            FROM blacklist_ips_with_auto_inactive
            WHERE ip_address = %s AND is_active = true
            """,
            (ip,),
        )
        return results[0] if results else None

    def insert_blacklist(
        self,
        ip_address: str,
        reason: str = "Manual block",
        source: str = "MANUAL",
        confidence_level: int = 100,
    ) -> bool:
        try:
            self.db.execute(
                """
                INSERT INTO blacklist_ips (ip_address, reason, source, confidence_level, is_active)
                VALUES (%s, %s, %s, %s, true)
                ON CONFLICT (ip_address, source) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    confidence_level = EXCLUDED.confidence_level,
                    is_active = true,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (ip_address, reason, source, confidence_level),
            )
            return True
        except Exception as e:
            logger.error("insert_blacklist failed for IP %s: %s", ip_address, e)
            return False

    def insert_whitelist(
        self,
        ip_address: str,
        reason: str = "Manual whitelist",
        source: str = "MANUAL",
    ) -> bool:
        try:
            self.db.execute(
                """
                INSERT INTO whitelist_ips (ip_address, reason, source, is_active)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (ip_address) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    source = EXCLUDED.source,
                    is_active = true,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (ip_address, reason, source),
            )
            return True
        except Exception as e:
            logger.error("insert_whitelist failed for IP %s: %s", ip_address, e)
            return False

    def count_blacklist_ips(self) -> int:
        result = self.db.query("SELECT COUNT(*) as count FROM blacklist_ips")
        return result[0]["count"] if result else 0

    def get_source_stats(self) -> list[dict[str, RowValue]]:
        return self.db.query(
            """
            SELECT data_source, COUNT(*) as count, MAX(last_seen) as last_seen
            FROM blacklist_ips
            GROUP BY data_source
            """
        )

    def get_active_blacklist_enhanced(self) -> list[dict[str, RowValue]]:
        return self.db.query(
            """
            SELECT ip_address, reason, source,
                   is_active, last_seen, detection_count
            FROM blacklist_ips_with_auto_inactive
            WHERE is_active = true
            ORDER BY last_seen DESC
            """
        )

    def get_active_blacklist_ips(self) -> list[str]:
        results = self.db.query("SELECT ip_address FROM blacklist_ips_with_auto_inactive WHERE is_active = true")
        return [row["ip_address"] for row in results]

    def count_active_blacklist_ips(self) -> int:
        result = self.db.query("SELECT COUNT(*) as count FROM blacklist_ips_with_auto_inactive WHERE is_active = true")
        return result[0]["count"] if result else 0

    def get_source_counts(self) -> dict[str, dict[str, int]]:
        results = self.db.query(
            """
            SELECT data_source, COUNT(*) as count
            FROM blacklist_ips
            GROUP BY data_source
            """
        )
        return {row["data_source"]: {"count": row["count"]} for row in results}

    def deactivate_by_source(self, source: str) -> None:
        self.db.execute(
            "UPDATE blacklist_ips SET is_active = false WHERE data_source = %s",
            (source,),
        )

    def upsert_blacklist_from_collector(
        self,
        ip_address: str,
        reason: str,
        country: Optional[str],
        detection_date: Optional[str],
    ) -> bool:
        try:
            self.db.execute(
                """
                INSERT INTO blacklist_ips
                (ip_address, reason, source, country, detection_date,
                 is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (ip_address, source) DO UPDATE SET
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP
                """,
                (ip_address, reason, "REGTECH", country, detection_date, True),
            )
            return True
        except Exception as e:
            logger.error("upsert_blacklist_from_collector failed for IP %s: %s", ip_address, e)
            return False

    def add_column_if_not_exists(self, column_name: str, column_type: str) -> bool:
        try:
            with connection_lease(self.db) as conn:
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE blacklist_ips ADD COLUMN {column_name} {column_type};")
                conn.commit()
                cursor.close()
                return True
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e).lower():
                return False
            raise

    def create_whitelist_table(self) -> None:
        self.db.query("""
            CREATE TABLE IF NOT EXISTS whitelist_ips (
                id SERIAL PRIMARY KEY,
                ip_address VARCHAR(45) NOT NULL,
                reason VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ip_address)
            )
        """)

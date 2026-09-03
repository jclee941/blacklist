"""
IP Management Repository Layer - Raw SQL queries for whitelist/blacklist operations.
Extracted from ip_management_api.py for separation of concerns.
"""

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from contextlib import ExitStack
from typing import Any, Optional
from psycopg2.extras import RealDictCursor
import logging

from core.services.database_lease import connection_lease

logger = logging.getLogger(__name__)
RowValue = str | int | float | bool | date | datetime | None


class IPManagementRepository:
    """Repository for IP whitelist/blacklist database operations."""

    WHITELIST_COLUMNS = {"ip_address", "reason", "source", "country"}
    BLACKLIST_COLUMNS = {
        "ip_address",
        "reason",
        "source",
        "data_source",
        "confidence_level",
        "detection_count",
        "is_active",
        "country",
        "detection_date",
        "removal_date",
    }

    def __init__(self, db_service: Any):
        self.db_service = db_service

    def _get_connection(self, connections: ExitStack):
        return connections.enter_context(connection_lease(self.db_service))

    def _serialize_row(self, row: Mapping[str, RowValue]) -> dict[str, RowValue]:
        result = dict(row)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result

    def _serialize_rows(self, rows: Sequence[Mapping[str, RowValue]]) -> list[dict[str, RowValue]]:
        return [self._serialize_row(row) for row in rows]

    def get_unified_list(
        self,
        page: int,
        limit: int,
        list_type: Optional[str] = None,
        search_ip: Optional[str] = None,
        is_active: Optional[bool] = True,
        source: Optional[str] = None,
    ) -> tuple[list[dict[str, RowValue]], int]:
        """Get unified IP list with pagination. Returns (items, total_count)."""
        offset = (page - 1) * limit
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build UNION of blacklist + whitelist instead of querying empty unified_ip_list table
            union_sql = """
                SELECT 'blacklist' AS list_type, id, ip_address, reason, source,
                       data_source, confidence_level, detection_count, is_active,
                       country, detection_date, removal_date, last_seen,
                       created_at, updated_at, auto_active
                FROM blacklist_ips_with_auto_inactive
                UNION ALL
                SELECT 'whitelist' AS list_type, id, ip_address, reason, source,
                       NULL AS data_source, NULL AS confidence_level, NULL AS detection_count, TRUE AS is_active,
                       country, NULL AS detection_date, NULL AS removal_date, NULL AS last_seen,
                       created_at, updated_at, TRUE AS auto_active
                FROM whitelist_ips
            """

            where_clauses = []
            params: list[Any] = []

            if list_type in ("whitelist", "blacklist"):
                where_clauses.append("list_type = %s")
                params.append(list_type)

            if search_ip:
                where_clauses.append("ip_address LIKE %s")
                params.append(f"%{search_ip}%")

            if is_active is not None:
                where_clauses.append("is_active = %s")
                params.append(is_active)

            if source:
                where_clauses.append("source = %s")
                params.append(source)

            where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

            cursor.execute(
                f"SELECT COUNT(*) as total FROM ({union_sql}) AS unified WHERE {where_sql}",
                params,
            )
            total_result = cursor.fetchone()
            total = total_result["total"] if total_result else 0

            cursor.execute(
                f"""
                SELECT
                    list_type, id, ip_address, reason, source,
                    data_source, confidence_level, detection_count, is_active,
                    country, detection_date, removal_date, last_seen,
                    created_at, updated_at, auto_active
                FROM ({union_sql}) AS unified
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            data = cursor.fetchall()

            cursor.close()

            return self._serialize_rows(data), total

        except Exception as e:
            logger.error("get_unified_list failed: %s", e)
            raise
        finally:
            connections.close()

    def get_statistics(self) -> list[dict[str, RowValue]]:
        """Get unified IP statistics from the canonical IP tables."""
        try:
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT
                        'blacklist' AS list_type,
                        source,
                        COUNT(*) AS count,
                        COUNT(*) FILTER (WHERE is_active = true) AS active_count,
                        MAX(updated_at) AS last_updated
                    FROM blacklist_ips
                    GROUP BY source
                    UNION ALL
                    SELECT
                        'whitelist' AS list_type,
                        source,
                        COUNT(*) AS count,
                        COUNT(*) FILTER (WHERE is_active = true) AS active_count,
                        MAX(updated_at) AS last_updated
                    FROM whitelist_ips
                    GROUP BY source
                    ORDER BY list_type, source
                """)
                stats = cursor.fetchall()
                cursor.close()

            return self._serialize_rows(stats)

        except Exception as e:
            logger.error("get_statistics failed: %s", e)
            raise

    def get_whitelist(self, page: int, limit: int) -> tuple[list[dict[str, RowValue]], int]:
        """Get whitelist entries with pagination. Returns (items, total_count)."""
        offset = (page - 1) * limit
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT COUNT(*) as total FROM whitelist_ips")
            total_result = cursor.fetchone()
            total = total_result["total"] if total_result else 0

            cursor.execute(
                """
                SELECT id, ip_address, reason, source, country, created_at, updated_at
                FROM whitelist_ips
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            data = cursor.fetchall()

            cursor.close()

            return self._serialize_rows(data), total

        except Exception as e:
            logger.error("get_whitelist failed: %s", e)
            raise
        finally:
            connections.close()

    def create_whitelist(
        self,
        ip_address: str,
        reason: str = "VIP Protection",
        source: str = "MANUAL",
        country: Optional[str] = None,
    ) -> dict[str, RowValue]:
        """Create or update whitelist entry (upsert on ip_address+source)."""
        connections = ExitStack()
        conn = self._get_connection(connections)
        now = datetime.now()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                INSERT INTO whitelist_ips (ip_address, reason, source, country, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip_address) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    source = EXCLUDED.source,
                    country = COALESCE(EXCLUDED.country, whitelist_ips.country),
                    updated_at = EXCLUDED.updated_at
                RETURNING id, ip_address, reason, source, country, created_at, updated_at
                """,
                (ip_address, reason, source, country, now, now),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            if result is None:
                raise RuntimeError("Whitelist upsert returned no row")

            return self._serialize_row(result)

        except Exception as e:
            logger.error("create_whitelist failed: %s", e)
            raise
        finally:
            connections.close()

    def update_whitelist(self, id: int, data: Mapping[str, RowValue]) -> Optional[dict[str, RowValue]]:
        """Update whitelist entry. Returns updated entry or None if not found."""
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            update_fields = []
            params: list[Any] = []

            for key, value in data.items():
                if key in self.WHITELIST_COLUMNS:
                    update_fields.append(f"{key} = %s")
                    params.append(value)

            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            params.append(id)

            cursor.execute(
                f"""
                UPDATE whitelist_ips
                SET {", ".join(update_fields)}
                WHERE id = %s
                RETURNING id, ip_address, reason, source, country, created_at, updated_at
                """,
                params,
            )

            result = cursor.fetchone()

            if result:
                conn.commit()
                cursor.close()
                return self._serialize_row(result)

            cursor.close()
            return None

        except Exception as e:
            logger.error("update_whitelist failed: %s", e)
            raise
        finally:
            connections.close()

    def delete_whitelist(self, id: int) -> Optional[str]:
        """Delete whitelist entry. Returns deleted IP or None if not found."""
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                "DELETE FROM whitelist_ips WHERE id = %s RETURNING ip_address",
                (id,),
            )
            result = cursor.fetchone()

            if result:
                conn.commit()
                cursor.close()
                return result["ip_address"]

            cursor.close()
            return None

        except Exception as e:
            logger.error("delete_whitelist failed: %s", e)
            raise
        finally:
            connections.close()

    def get_blacklist(self, page: int, limit: int) -> tuple[list[dict[str, RowValue]], int]:
        """Get blacklist entries with pagination. Returns (items, total_count)."""
        offset = (page - 1) * limit
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT COUNT(*) as total FROM blacklist_ips_with_auto_inactive")
            total_result = cursor.fetchone()
            total = total_result["total"] if total_result else 0

            cursor.execute(
                """
                SELECT id, ip_address, reason, source, data_source,
                       confidence_level, detection_count, is_active, country,
                       detection_date, removal_date, last_seen,
                       created_at, updated_at, auto_active
                FROM blacklist_ips_with_auto_inactive
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            data = cursor.fetchall()

            cursor.close()

            return self._serialize_rows(data), total

        except Exception as e:
            logger.error("get_blacklist failed: %s", e)
            raise
        finally:
            connections.close()

    def create_blacklist(
        self,
        ip_address: str,
        reason: str = "Malicious Activity",
        source: str = "MANUAL",
        data_source: str = "REGTECH",
        confidence_level: int = 50,
        detection_count: int = 1,
        is_active: bool = True,
        country: Optional[str] = None,
        detection_date: Optional[str] = None,
        removal_date: Optional[str] = None,
    ) -> dict[str, RowValue]:
        """Create or update blacklist entry (upsert on ip_address+source)."""
        connections = ExitStack()
        conn = self._get_connection(connections)
        now = datetime.now()

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                """
                INSERT INTO blacklist_ips
                (ip_address, reason, source, data_source, confidence_level,
                 detection_count, is_active, country, detection_date,
                 removal_date, last_seen, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip_address, source) DO UPDATE SET
                    reason = EXCLUDED.reason,
                    data_source = EXCLUDED.data_source,
                    confidence_level = EXCLUDED.confidence_level,
                    detection_count = blacklist_ips.detection_count + 1,
                    is_active = EXCLUDED.is_active,
                    country = COALESCE(EXCLUDED.country, blacklist_ips.country),
                    detection_date = EXCLUDED.detection_date,
                    removal_date = EXCLUDED.removal_date,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, ip_address, reason, source, data_source,
                          confidence_level, detection_count, is_active, country,
                          detection_date, removal_date, last_seen,
                          created_at, updated_at
                """,
                (
                    ip_address,
                    reason,
                    source,
                    data_source,
                    confidence_level,
                    detection_count,
                    is_active,
                    country,
                    detection_date,
                    removal_date,
                    now,
                    now,
                    now,
                ),
            )

            result = cursor.fetchone()
            conn.commit()
            cursor.close()

            if result is None:
                raise RuntimeError("Blacklist upsert returned no row")

            return self._serialize_row(result)

        except Exception as e:
            logger.error("create_blacklist failed: %s", e)
            raise
        finally:
            connections.close()

    def update_blacklist(self, id: int, data: Mapping[str, RowValue]) -> Optional[dict[str, RowValue]]:
        """Update blacklist entry. Returns updated entry or None if not found."""
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            update_fields = []
            params: list[Any] = []

            for key, value in data.items():
                if key in self.BLACKLIST_COLUMNS:
                    update_fields.append(f"{key} = %s")
                    params.append(value)

            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            params.append(id)

            cursor.execute(
                f"""
                UPDATE blacklist_ips
                SET {", ".join(update_fields)}
                WHERE id = %s
                RETURNING id, ip_address, reason, source, data_source,
                          confidence_level, detection_count, is_active, country,
                          detection_date, removal_date, last_seen,
                          created_at, updated_at
                """,
                params,
            )

            result = cursor.fetchone()

            if result:
                conn.commit()
                cursor.close()
                return self._serialize_row(result)

            cursor.close()
            return None

        except Exception as e:
            logger.error("update_blacklist failed: %s", e)
            raise
        finally:
            connections.close()

    def delete_blacklist(self, id: int) -> Optional[str]:
        """Delete blacklist entry. Returns deleted IP or None if not found."""
        connections = ExitStack()
        conn = self._get_connection(connections)

        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                "DELETE FROM blacklist_ips WHERE id = %s RETURNING ip_address",
                (id,),
            )
            result = cursor.fetchone()

            if result:
                conn.commit()
                cursor.close()
                return result["ip_address"]

            cursor.close()
            return None

        except Exception as e:
            logger.error("delete_blacklist failed: %s", e)
            raise
        finally:
            connections.close()

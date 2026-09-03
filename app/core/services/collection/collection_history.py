"""
Collection History Manager
수집 이력 관리
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import current_app
from ..database_lease import connection_lease

logger = logging.getLogger(__name__)


class CollectionHistoryManager:
    """수집 이력 관리 클래스"""

    def __init__(self):
        self.history_retention_days = 90  # 90일간 이력 보존

    @property
    def db_service(self):
        return current_app.extensions["db_service"]

    def record_collection_history(
        self,
        collection_type: str,
        collected_count: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: int = 0,
    ) -> bool:
        """수집 이력 기록

        Args:
            collection_type: 수집 타입 (REGTECH)
            collected_count: 수집된 아이템 수
            start_date: 수집 시작 날짜 (optional)
            end_date: 수집 종료 날짜 (optional)
            additional_info: 추가 정보 (optional)
            success: 수집 성공 여부
            error_message: 에러 메시지 (실패 시)
            execution_time_ms: 실행 시간 (밀리초)
        """
        try:
            import json

            details = json.dumps(additional_info) if additional_info else "{}"
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO collection_history
                    (service_name, collection_date, items_collected,
                     success, error_message, execution_time_ms, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        collection_type,
                        datetime.now(),
                        collected_count,
                        success,
                        error_message,
                        execution_time_ms,
                        details,
                    ),
                )
                conn.commit()
                cursor.close()

            logger.info(f"Collection history recorded: {collection_type}, {collected_count} items, success={success}")
            return True

        except Exception as e:
            logger.error(f"Failed to record collection history: {e}")
            return False

    def _ensure_history_table_exists(self, cursor):
        """collection_history 테이블 존재 확인 - 테이블은 마이그레이션에서 생성됨"""
        # 테이블은 postgres/migrations/000_init_complete_schema.sql에서 생성됨
        # 이 함수는 하위 호환성을 위해 유지
        pass

    def get_recent_history(self, collection_type: Optional[str] = None, days: int = 30) -> List[Dict[str, Any]]:
        """최근 수집 이력 조회"""
        try:
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT service_name, items_collected, collection_date, collection_date,
                           details, collection_date
                    FROM collection_history
                    WHERE collection_date >= %s
                """
                params: list[datetime | str] = [datetime.now() - timedelta(days=days)]

                if collection_type:
                    query += " AND service_name = %s"
                    params.append(collection_type)

                query += " ORDER BY collection_date DESC LIMIT 100"
                cursor.execute(query, params)
                results = cursor.fetchall()
                cursor.close()

            history = []
            columns = [
                "service_name",
                "items_collected",
                "start_date",
                "end_date",
                "details",
                "collection_date",
            ]

            for row in results:
                history_item = dict(zip(columns, row))
                for date_field in ["start_date", "end_date", "collection_date"]:
                    if history_item[date_field]:
                        history_item[date_field] = history_item[date_field].isoformat()
                history.append(history_item)

            return history

        except Exception as e:
            logger.error(f"Failed to get collection history: {e}")
            return []

    def get_collection_statistics(self) -> Dict[str, Any]:
        """수집 통계 조회"""
        try:
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor()

                total_collections = 0
                total_collected_items = 0
                last_7_days: dict[str, dict[str, int]] = {}
                by_type: dict[str, dict[str, int | str | None]] = {}

                # 전체 수집 횟수 및 아이템 수
                cursor.execute(
                    """
                SELECT COUNT(*), COALESCE(SUM(items_collected), 0)
                FROM collection_history
                WHERE collection_date >= %s
                    """,
                    (datetime.now() - timedelta(days=30),),
                )

                result = cursor.fetchone()
                if result:
                    total_collections = result[0]
                    total_collected_items = result[1]

                # 최근 7일간 일별 수집 현황
                cursor.execute(
                    """
                SELECT DATE(collection_date) as collection_date,
                       COUNT(*) as collection_count,
                       COALESCE(SUM(items_collected), 0) as item_count
                FROM collection_history
                WHERE collection_date >= %s
                GROUP BY DATE(collection_date)
                ORDER BY collection_date DESC
                    """,
                    (datetime.now() - timedelta(days=7),),
                )

                for row in cursor.fetchall():
                    date_str = row[0].isoformat() if row[0] else "unknown"
                    last_7_days[date_str] = {
                        "collections": row[1],
                        "items": row[2],
                    }

                # 수집 타입별 통계
                cursor.execute(
                    """
                SELECT service_name,
                       COUNT(*) as collection_count,
                       COALESCE(SUM(items_collected), 0) as item_count,
                       MAX(collection_date) as last_collection
                FROM collection_history
                WHERE collection_date >= %s
                GROUP BY service_name
                    """,
                    (datetime.now() - timedelta(days=30),),
                )

                for row in cursor.fetchall():
                    by_type[row[0]] = {
                        "collections": row[1],
                        "items": row[2],
                        "last_collection": row[3].isoformat() if row[3] else None,
                    }

                cursor.close()

            return {
                "total_collections": total_collections,
                "total_collected_items": total_collected_items,
                "last_7_days": last_7_days,
                "by_type": by_type,
                "success_rate": 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to get collection statistics: {e}")
            return {
                "total_collections": 0,
                "total_collected_items": 0,
                "last_7_days": {},
                "by_type": {},
                "success_rate": 0.0,
            }

    def cleanup_old_history(self) -> int:
        """오래된 이력 정리"""
        try:
            with connection_lease(self.db_service) as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=self.history_retention_days)
                cursor.execute(
                    """
                    DELETE FROM collection_history
                    WHERE collection_date < %s
                    """,
                    (cutoff_date,),
                )
                deleted_count = cursor.rowcount
                conn.commit()
                cursor.close()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old history records")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")
            return 0


# Singleton instance
history_manager = CollectionHistoryManager()

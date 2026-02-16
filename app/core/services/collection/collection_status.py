"""
Collection Status Manager
수집 상태 관리
"""

import logging
from datetime import datetime
from typing import Dict, Any, Set
from flask import current_app

logger = logging.getLogger(__name__)


class CollectionStatusManager:
    """수집 상태 관리 클래스"""

    def __init__(self):
        self.active_collections: Set[str] = set()
        self.collection_status = {
            "regtech": {"running": False, "last_run": None, "last_error": None},
            "secudium": {"running": False, "last_run": None, "last_error": None},
        }

    @property
    def db_service(self):
        return current_app.extensions["db_service"]

    def get_collection_status(self) -> Dict[str, Any]:
        """현재 수집 상태 조회"""
        try:
            # 데이터베이스에서 통계 정보 조회
            stats = self._get_database_stats()

            # 수집 서비스 상태
            status = {
                "collection_enabled": True,
                "active_collections": list(self.active_collections),
                "collection_status": self.collection_status.copy(),
                "last_updated": datetime.now().isoformat(),
                **stats,
            }

            # 컬렉터 컨테이너 상태 체크
            collector_status = self._check_collector_container()
            status["collector_container"] = collector_status

            return status

        except Exception as e:
            logger.error(f"Failed to get collection status: {e}")
            return {
                "collection_enabled": False,
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
            }

    def _get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        try:
            conn = self.db_service.get_connection()
            cursor = conn.cursor()

            # 기본 통계
            cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE is_active = true")
            total_ips = cursor.fetchone()[0] or 0

            cursor.execute(
                """
                SELECT data_source, COUNT(*)
                FROM blacklist_ips
                WHERE is_active = true
                GROUP BY data_source
            """
            )
            sources = dict(cursor.fetchall()) if cursor.fetchall() else {}

            cursor.close()
            conn.close()

            return {"total_ips": total_ips, "sources": sources}

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"total_ips": 0, "sources": {}}

    def _check_collector_container(self) -> Dict[str, Any]:
        """컬렉터 컨테이너 상태 체크"""
        try:
            import requests

            from ...config import config

            response = requests.get(f"{config.COLLECTOR_URL}/health", timeout=5)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "url": config.COLLECTOR_URL,
                    "last_check": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "last_check": datetime.now().isoformat(),
                }

        except requests.RequestException as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": datetime.now().isoformat(),
            }

    def start_collection(self, collection_type: str) -> bool:
        """수집 시작"""
        try:
            if collection_type in self.active_collections:
                logger.warning(f"Collection {collection_type} is already running")
                return False

            self.active_collections.add(collection_type)
            self.collection_status[collection_type] = {
                "running": True,
                "last_run": datetime.now().isoformat(),
                "last_error": None,
            }

            logger.info(f"Started collection: {collection_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to start collection {collection_type}: {e}")
            return False

    def stop_collection(self, collection_type: str) -> bool:
        """수집 중지"""
        try:
            if collection_type not in self.active_collections:
                logger.warning(f"Collection {collection_type} is not running")
                return False

            self.active_collections.discard(collection_type)
            self.collection_status[collection_type] = {
                "running": False,
                "last_run": self.collection_status.get(collection_type, {}).get("last_run"),
                "last_error": None,
            }

            logger.info(f"Stopped collection: {collection_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop collection {collection_type}: {e}")
            return False

    def stop_all_collections(self) -> Dict[str, Any]:
        """모든 수집 중지"""
        try:
            stopped_collections = list(self.active_collections)

            for collection_type in stopped_collections:
                self.stop_collection(collection_type)

            return {
                "success": True,
                "stopped_collections": stopped_collections,
                "message": f"Stopped {len(stopped_collections)} collections",
            }

        except Exception as e:
            logger.error(f"Failed to stop all collections: {e}")
            return {"success": False, "error": str(e)}

    def update_collection_error(self, collection_type: str, error: str):
        """수집 오류 상태 업데이트"""
        if collection_type in self.collection_status:
            self.collection_status[collection_type]["last_error"] = error
            self.collection_status[collection_type]["running"] = False
            self.active_collections.discard(collection_type)

    def _check_and_create_collection_alerts(self, collection_status: Dict[str, Any]):
        """수집 상태 알림 생성"""
        try:
            # 오류가 있는 수집 서비스 체크
            for service_name, status in collection_status.get("collection_status", {}).items():
                if status.get("last_error"):
                    logger.warning(f"Collection service {service_name} has error: {status['last_error']}")

            # 컬렉터 컨테이너 상태 체크
            collector_status = collection_status.get("collector_container", {})
            if collector_status.get("status") != "healthy":
                logger.warning(
                    f"Collector container is {collector_status.get('status')}: {collector_status.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Failed to check collection alerts: {e}")


# Singleton instance
status_manager = CollectionStatusManager()

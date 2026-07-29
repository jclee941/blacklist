import sys
import structlog
from typing import Any, Dict, Protocol

from ..config import config


logger = structlog.get_logger(__name__)


class SupportsBlacklistCollector(Protocol):
    repo: Any

    def get_system_stats(self) -> Dict[str, Any]: ...
    def _copy_data_from_collector(self, collector_data: Dict[str, Any]) -> int: ...
    def _fallback_direct_collection(self) -> Dict[str, Any]: ...


class BlacklistCollectorMixin:
    def sync_with_collector(self: SupportsBlacklistCollector) -> Dict[str, Any]:
        try:
            blacklist_service_module = sys.modules.get("core.services.blacklist_service") or sys.modules.get(
                "app.core.services.blacklist_service"
            )
            requests_module = blacklist_service_module.requests if blacklist_service_module else __import__("requests")

            try:
                health_response = requests_module.get(
                    f"{config.COLLECTOR_URL}/health",
                    timeout=5,
                    **config.COLLECTOR_AUTH_REQUEST_KWARGS,
                )
                collector_healthy = health_response.status_code == 200
            except Exception:
                collector_healthy = False

            stats = self.get_system_stats()

            return {
                "success": True,
                "collector_status": "healthy" if collector_healthy else "unreachable",
                "total_ips": stats.get("total_ips", 0),
                "active_ips": stats.get("active_ips", 0),
                "database_shared": True,
                "message": f"총 {stats.get('total_ips', 0)}개 IP (활성: {stats.get('active_ips', 0)}개)",
                "note": "메인앱과 컬렉터는 같은 데이터베이스를 공유합니다",
            }

        except Exception as e:
            logger.error(f"동기화 상태 확인 실패: {e}")
            return {"success": False, "error": str(e), "collector_status": "error"}

    def force_schema_fix(self: SupportsBlacklistCollector) -> Dict[str, Any]:
        try:
            added_is_active = self.repo.add_column_if_not_exists("is_active", "BOOLEAN DEFAULT TRUE")
            added_country = self.repo.add_column_if_not_exists("country", "VARCHAR(10)")
            added_detection_date = self.repo.add_column_if_not_exists("detection_date", "DATE")
            added_removal_date = self.repo.add_column_if_not_exists("removal_date", "DATE")

            return {
                "success": True,
                "message": "스키마 강제 수정 완료",
                "added_columns": {
                    "is_active": added_is_active,
                    "country": added_country,
                    "detection_date": added_detection_date,
                    "removal_date": added_removal_date,
                },
            }

        except Exception as e:
            logger.error(f"스키마 강제 수정 실패: {e}")
            return {"success": False, "error": str(e)}

    def force_data_refresh(self: SupportsBlacklistCollector) -> Dict[str, Any]:
        try:
            blacklist_service_module = sys.modules.get("core.services.blacklist_service") or sys.modules.get(
                "app.core.services.blacklist_service"
            )
            requests_module = blacklist_service_module.requests if blacklist_service_module else __import__("requests")

            try:
                data_response = requests_module.get(
                    f"{config.COLLECTOR_URL}/api/data",
                    timeout=30,
                    **config.COLLECTOR_AUTH_REQUEST_KWARGS,
                )

                if data_response.status_code == 200:
                    collector_data = data_response.json()
                    copied_count = self._copy_data_from_collector(collector_data)

                    return {
                        "success": True,
                        "message": f"컬렉터에서 {copied_count}개 IP 데이터를 복사했습니다",
                        "copied_count": copied_count,
                        "source": "collector_data_copy",
                    }

                logger.warning(f"컬렉터 데이터 API 실패: {data_response.status_code}")
                return self._fallback_direct_collection()

            except requests_module.exceptions.RequestException as e:
                logger.warning(f"컬렉터 연결 실패: {e}")
                return self._fallback_direct_collection()

        except Exception as e:
            logger.error(f"강제 데이터 새로고침 실패: {e}")
            return {"success": False, "error": str(e)}

    def _copy_data_from_collector(self: SupportsBlacklistCollector, collector_data: Dict[str, Any]) -> int:
        copied_count = 0

        try:
            self.repo.deactivate_by_source("REGTECH")

            for ip_data in collector_data.get("data", []):
                if self.repo.upsert_blacklist_from_collector(
                    ip_address=ip_data.get("ip_address"),
                    reason=ip_data.get("reason", ""),
                    country=ip_data.get("country"),
                    detection_date=ip_data.get("detection_date"),
                ):
                    copied_count += 1

        except Exception as e:
            logger.error(f"데이터 복사 실패: {e}")

        return copied_count

    def _fallback_direct_collection(self: SupportsBlacklistCollector) -> Dict[str, Any]:
        logger.info("컬렉터 사용 불가, 메인 앱에서 직접 수집 시도")
        return {
            "success": False,
            "error": "컬렉터 연결 실패 및 직접 수집 미구현",
            "fallback_attempted": True,
            "suggestion": "수동으로 REGTECH 포털에서 데이터를 다운로드하세요",
        }

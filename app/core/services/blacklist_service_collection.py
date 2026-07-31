import logging
import sys
from datetime import datetime
from typing import Any, Dict

import requests

from ..config import config

logger = logging.getLogger(__name__)


class BlacklistCollectionMixin:
    async def enable_collection(self) -> Dict[str, Any]:
        try:
            logger.info("Collection system enabled")
            return {
                "success": True,
                "message": "수집 시스템이 활성화되었습니다",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Collection enable failed: {e}")
            return {"success": False, "error": str(e)}

    async def disable_collection(self) -> Dict[str, Any]:
        try:
            logger.info("Collection system disabled")
            return {
                "success": True,
                "message": "수집 시스템이 비활성화되었습니다",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Collection disable failed: {e}")
            return {"success": False, "error": str(e)}

    async def collect_all_data(self, force: bool = False) -> Dict[str, Any]:
        results = {"regtech": await self._collect_regtech_data(force)}
        success_count = sum(1 for result in results.values() if result.get("success", False))
        return {
            "success": success_count > 0,
            "results": results,
            "summary": {
                "total_sources": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
            },
        }

    async def _collect_regtech_data(self, force: bool = False) -> Dict[str, Any]:
        facade_module = sys.modules.get(type(self).__module__)
        requests_module = getattr(facade_module, "requests", requests) if facade_module else requests
        logger_module = getattr(facade_module, "logger", logger) if facade_module else logger
        try:
            response = requests_module.post(
                f"{config.COLLECTOR_URL}/api/force-collection/REGTECH",
                json={"force": force},
                timeout=config.COLLECTOR_COLLECTION_TIMEOUT,
                **config.COLLECTOR_AUTH_REQUEST_KWARGS,
            )
            if response.status_code == 200:
                result = response.json()
                collected_count = result.get("collected", result.get("count", 0))
                logger_module.info(f"✅ REGTECH 수집 완료 (via collector): {collected_count}개")
                return {
                    "success": True,
                    "collected": collected_count,
                    "message": "REGTECH 수집 완료",
                    "timestamp": datetime.now().isoformat(),
                }
            error_msg = f"Collector API error: {response.status_code}"
            logger_module.error(f"❌ REGTECH 수집 실패: {error_msg}")
            return {"success": False, "error": error_msg}
        except requests.exceptions.ConnectionError:
            logger_module.warning("Collector 서비스에 연결할 수 없음 - 서비스가 실행 중인지 확인하세요")
            return {
                "success": False,
                "error": "Cannot connect to collector service",
                "details": "Collector container may be down or unhealthy",
            }
        except Exception as e:
            logger_module.error(f"REGTECH collection failed: {e}")
            return {"success": False, "error": str(e)}

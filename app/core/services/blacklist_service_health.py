from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Protocol

from ..utils.version import get_app_version
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class HealthStatus:
    status: str
    version: str
    timestamp: datetime
    components: Dict[str, Any]


class SupportsBlacklistHealth(Protocol):
    repo: Any
    redis_client: Any
    _components: Dict[str, Any]


class BlacklistHealthMixin:
    def get_health(self: SupportsBlacklistHealth) -> HealthStatus:
        try:
            ip_count = self.repo.count_blacklist_ips()
            redis_status = "unavailable"
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    redis_status = "healthy"
                except Exception as e:
                    logger.warning("Redis health check failed: %s", e)
                    redis_status = "degraded"
            components = {
                "database": {"status": "healthy", "ip_count": ip_count},
                "redis": {"status": redis_status, "enabled": self._components["redis"]},
                "regtech": {"status": "healthy", "enabled": True},
            }
            overall_status = "healthy" if redis_status in ["healthy", "unavailable"] else "degraded"
            return HealthStatus(overall_status, get_app_version(), datetime.now(), components)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus("degraded", get_app_version(), datetime.now(), {"error": str(e)})

    def get_collection_status(self: SupportsBlacklistHealth) -> Dict[str, Any]:
        try:
            sources = self.repo.get_source_stats()
            status: Dict[str, Any] = {
                "collection_enabled": True,
                "sources": {},
                "total_ips": sum(s["count"] for s in sources),
                "last_updated": datetime.now().isoformat(),
            }
            for source in sources:
                status["sources"][source["data_source"].lower()] = {
                    "total_ips": source["count"],
                    "last_seen": source["last_seen"].isoformat() if source["last_seen"] else None,
                    "enabled": True,
                }
            return status
        except Exception as e:
            logger.error(f"Collection status check failed: {e}")
            return {"error": str(e), "collection_enabled": False}

    def get_system_stats(self: SupportsBlacklistHealth) -> Dict[str, Any]:
        try:
            return {
                "success": True,
                "total_ips": self.repo.count_blacklist_ips(),
                "active_ips": self.repo.count_active_blacklist_ips(),
                "sources": self.repo.get_source_counts(),
                "categories": {},
                "last_updated": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"System stats retrieval failed: {e}")
            return {"success": False, "error": str(e), "total_ips": 0, "active_ips": 0, "sources": {}, "categories": {}}

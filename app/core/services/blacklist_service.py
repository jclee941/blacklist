import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, cast
import structlog
import redis
import json
import requests

from ..config import config

from ..monitoring.metrics import (
    blacklist_decisions_total,
    blacklist_whitelist_hits_total,
)
from .blacklist_repository import BlacklistRepository
from .blacklist_service_collection import BlacklistCollectionMixin
from .blacklist_service_health import BlacklistHealthMixin, HealthStatus
from .blacklist_service_sync import BlacklistCollectorMixin

logger = structlog.get_logger(__name__)
standard_logger = logging.getLogger(__name__)

__all__ = ["BlacklistService", "HealthStatus", "requests"]


class BlacklistService(BlacklistCollectionMixin, BlacklistHealthMixin, BlacklistCollectorMixin):
    def __init__(self, db_service=None):
        self.db_service: Any = db_service
        self.repo: Any = BlacklistRepository(db_service) if db_service else None
        self._components: Dict[str, Any] = {"regtech": True, "database": True, "redis": False}

        try:
            self.redis_client: Any = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                **config.get_redis_auth_params(),
            )
            self.redis_client.ping()
            self._components["redis"] = True
            standard_logger.info("✅ Redis cache initialized successfully")
        except Exception as e:
            standard_logger.warning(f"⚠️ Redis cache unavailable (will use DB only): {e}")
            self.redis_client = None

        # 캐시 TTL 설정 (5분 = 300초)
        self.cache_ttl = 300

    def log_decision(
        self,
        ip: str,
        decision: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        log_data = {
            "ip": ip,
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if metadata:
            log_data.update(metadata)

        cast(Any, blacklist_decisions_total).labels(decision=decision, reason=reason).inc()

        logger.info("blacklist_decision", **log_data)

    def is_whitelisted(self, ip: str) -> bool:
        cache_key = f"whitelist:{ip}"

        try:
            if self.redis_client:
                try:
                    cached = self.redis_client.get(cache_key)
                    if cached is not None:
                        is_whitelisted = cached == "true"
                        if is_whitelisted:
                            cast(Any, blacklist_whitelist_hits_total).labels(ip_type="vip").inc()
                            self.log_decision(
                                ip,
                                "ALLOWED",
                                "whitelisted",
                                {"whitelist_hit": True, "cache_hit": True},
                            )
                        return is_whitelisted
                except Exception as redis_err:
                    standard_logger.warning(f"Redis cache read failed: {redis_err}")

            is_whitelisted = self.repo.count_whitelist_by_ip(ip) > 0

            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, self.cache_ttl, "true" if is_whitelisted else "false")
                except Exception as redis_err:
                    standard_logger.warning(f"Redis cache write failed: {redis_err}")

            if is_whitelisted:
                cast(Any, blacklist_whitelist_hits_total).labels(ip_type="vip").inc()
                self.log_decision(
                    ip,
                    "ALLOWED",
                    "whitelisted",
                    {"whitelist_hit": True, "cache_hit": False},
                )

            return is_whitelisted

        except Exception as e:
            standard_logger.warning(f"Whitelist check failed for {ip}: {e}")
            return False

    def _create_whitelist_table(self):
        try:
            self.repo.create_whitelist_table()
            standard_logger.info("Whitelist table created successfully")
        except Exception as e:
            standard_logger.error(f"Failed to create whitelist table: {e}")

    def check_blacklist(self, ip: str) -> Dict[str, Any]:
        cache_key = f"blacklist:{ip}"

        try:
            if self.is_whitelisted(ip):
                return {
                    "blocked": False,
                    "reason": "whitelisted",
                    "metadata": {"source": "whitelist", "priority": "high"},
                }

            if self.redis_client:
                try:
                    cached = self.redis_client.get(cache_key)
                    if cached:
                        result = json.loads(cast(str, cached))
                        result["metadata"]["cache_hit"] = True

                        if result["blocked"]:
                            self.log_decision(
                                ip,
                                "BLOCKED",
                                result["reason"],
                                {**result["metadata"], "cache_hit": True},
                            )
                        else:
                            self.log_decision(ip, "ALLOWED", result["reason"], {"cache_hit": True})

                        return result
                except Exception as redis_err:
                    standard_logger.warning(f"Redis cache read failed: {redis_err}")

            result = self.repo.get_blacklist_entry(ip)

            if result:
                reason = result["reason"] or "blacklisted"
                source = result["source"] or "unknown"
                detection_count = result["detection_count"] or 1

                response = {
                    "blocked": True,
                    "reason": reason,
                    "metadata": {
                        "source": source,
                        "detection_count": detection_count,
                        "cache_hit": False,
                    },
                }

                self.log_decision(
                    ip,
                    "BLOCKED",
                    reason,
                    {
                        "source": source,
                        "detection_count": detection_count,
                        "blacklist_match": True,
                        "cache_hit": False,
                    },
                )
            else:
                response = {
                    "blocked": False,
                    "reason": "not_in_blacklist",
                    "metadata": {"checked": True, "cache_hit": False},
                }

                self.log_decision(ip, "ALLOWED", "not_in_blacklist", {"cache_hit": False})

            if self.redis_client:
                try:
                    self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(response))
                except Exception as redis_err:
                    standard_logger.warning(f"Redis cache write failed: {redis_err}")

            return response

        except Exception as e:
            standard_logger.error(f"Blacklist check failed for {ip}: {e}")
            self.log_decision(ip, "ERROR", str(e), {"error": True})

            return {"blocked": False, "reason": "error", "metadata": {"error": str(e)}}

    def add_to_blacklist(self, ip_address, reason="Manual block", source="MANUAL", confidence=1.0):
        try:
            return self.repo.insert_blacklist(ip_address, reason, source, int(confidence * 100))
        except Exception as e:
            standard_logger.error(f"Failed to add to blacklist: {e}")
            return False

    def add_to_whitelist(self, ip_address, reason="Manual whitelist", source="MANUAL"):
        try:
            return self.repo.insert_whitelist(ip_address, reason, source)
        except Exception as e:
            standard_logger.error(f"Failed to add to whitelist: {e}")
            return False

    async def get_active_blacklist(self, format_type: str = "text") -> Dict[str, Any]:
        try:
            if format_type == "enhanced":
                rows = self.repo.get_active_blacklist_enhanced()
                data = [
                    {
                        "ip_address": row["ip_address"],
                        "reason": row["reason"],
                        "source": row["source"],
                        "is_active": row["is_active"],
                        "last_seen": row["last_seen"].isoformat() if row.get("last_seen") else None,
                        "detection_count": row.get("detection_count", 0),
                    }
                    for row in rows
                ]

            elif format_type == "fortigate":
                ips = self.repo.get_active_blacklist_ips()
                data = {
                    "entries": [{"ip": ip, "action": "block"} for ip in ips],
                    "total": len(ips),
                    "format": "fortigate_external_connector",
                }

            else:
                data = self.repo.get_active_blacklist_ips()

            return {
                "success": True,
                "data": data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Active blacklist retrieval failed: {e}")
            return {"success": False, "error": str(e)}

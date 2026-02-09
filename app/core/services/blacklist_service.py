"""
블랙리스트 통합 서비스
모든 블랙리스트 관련 비즈니스 로직을 처리하는 서비스 클래스
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..utils.version import get_app_version
import structlog
import redis
import json

from ..monitoring.metrics import (
    blacklist_decisions_total,
    blacklist_whitelist_hits_total,
)
from .blacklist_repository import BlacklistRepository

# 구조화된 로깅 설정
logger = structlog.get_logger(__name__)
standard_logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    status: str
    version: str
    timestamp: datetime
    components: Dict[str, Any]


class BlacklistService:
    def __init__(self, db_service=None):
        self.db_service = db_service
        self.repo = BlacklistRepository(db_service) if db_service else None
        self._components = {"regtech": True, "database": True, "redis": False}

        # Redis 캐시 초기화
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "blacklist-redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                db=0,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Redis 연결 테스트
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
            "timestamp": datetime.utcnow().isoformat(),
        }

        if metadata:
            log_data.update(metadata)

        blacklist_decisions_total.labels(decision=decision, reason=reason).inc()

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
                            blacklist_whitelist_hits_total.labels(ip_type="vip").inc()
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
                blacklist_whitelist_hits_total.labels(ip_type="vip").inc()
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
                        result = json.loads(cached)
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

    def get_health(self) -> HealthStatus:
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

            return HealthStatus(
                status=overall_status,
                version=get_app_version(),
                timestamp=datetime.now(),
                components=components,
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="degraded",
                version=get_app_version(),
                timestamp=datetime.now(),
                components={"error": str(e)},
            )

    def get_collection_status(self) -> Dict[str, Any]:
        try:
            sources = self.repo.get_source_stats()

            status = {
                "collection_enabled": True,
                "sources": {},
                "total_ips": sum(s["count"] for s in sources),
                "last_updated": datetime.now().isoformat(),
            }

            for source in sources:
                status["sources"][source["data_source"].lower()] = {
                    "total_ips": source["count"],
                    "last_seen": (source["last_seen"].isoformat() if source["last_seen"] else None),
                    "enabled": True,
                }

            return status
        except Exception as e:
            logger.error(f"Collection status check failed: {e}")
            return {"error": str(e), "collection_enabled": False}

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

    def get_statistics(self) -> Dict[str, Any]:
        try:
            total_ips = self.repo.count_blacklist_ips()
            active_ips = self.repo.count_active_blacklist_ips()
            sources = self.repo.get_source_counts()
            categories = {}

            statistics = {
                "total_ips": total_ips,
                "active_ips": active_ips,
                "sources": sources,
                "categories": categories,
                "last_updated": datetime.now().isoformat(),
            }

            return {"success": True, "statistics": statistics}

        except Exception as e:
            logger.error(f"Statistics retrieval failed: {e}")
            return {"success": False, "error": str(e)}

    def get_system_stats(self) -> Dict[str, Any]:
        try:
            total_ips = self.repo.count_blacklist_ips()
            active_ips = self.repo.count_active_blacklist_ips()
            sources = self.repo.get_source_counts()
            categories = {}

            return {
                "success": True,
                "total_ips": total_ips,
                "active_ips": active_ips,
                "sources": sources,
                "categories": categories,
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"System stats retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_ips": 0,
                "active_ips": 0,
                "sources": {},
                "categories": {},
            }

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
        results = {}

        regtech_result = await self._collect_regtech_data(force)
        results["regtech"] = regtech_result

        success_count = sum(1 for r in results.values() if r.get("success", False))

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
        import requests

        COLLECTOR_URL = os.environ.get("COLLECTOR_URL", "http://localhost:8545")

        try:
            response = requests.post(
                f"{COLLECTOR_URL}/api/force-collection/REGTECH",
                json={"force": force},
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                collected_count = result.get("collected", result.get("count", 0))
                logger.info(f"✅ REGTECH 수집 완료 (via collector): {collected_count}개")
                return {
                    "success": True,
                    "collected": collected_count,
                    "message": "REGTECH 수집 완료",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                error_msg = f"Collector API error: {response.status_code}"
                logger.error(f"❌ REGTECH 수집 실패: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.ConnectionError:
            logger.warning("Collector 서비스에 연결할 수 없음 - 서비스가 실행 중인지 확인하세요")
            return {
                "success": False,
                "error": "Cannot connect to collector service",
                "details": "Collector container may be down or unhealthy",
            }
        except Exception as e:
            logger.error(f"REGTECH collection failed: {e}")
            return {"success": False, "error": str(e)}

    # REGTECH 및 SECUDIUM 수집 지원

    def sync_with_collector(self) -> Dict[str, Any]:
        try:
            import requests

            try:
                collector_url = os.environ.get("COLLECTOR_URL", "http://localhost:8545")
                health_response = requests.get(f"{collector_url}/health", timeout=5)
                collector_healthy = health_response.status_code == 200
            except BaseException:
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

    def force_schema_fix(self) -> Dict[str, Any]:
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

    def force_data_refresh(self) -> Dict[str, Any]:
        try:
            import requests

            collector_url = os.environ.get("COLLECTOR_URL", "http://localhost:8545")
            try:
                data_response = requests.get(f"{collector_url}/api/data", timeout=30)

                if data_response.status_code == 200:
                    collector_data = data_response.json()
                    copied_count = self._copy_data_from_collector(collector_data)

                    return {
                        "success": True,
                        "message": f"컬렉터에서 {copied_count}개 IP 데이터를 복사했습니다",
                        "copied_count": copied_count,
                        "source": "collector_data_copy",
                    }
                else:
                    logger.warning(f"컬렉터 데이터 API 실패: {data_response.status_code}")
                    return self._fallback_direct_collection()

            except requests.exceptions.RequestException as e:
                logger.warning(f"컬렉터 연결 실패: {e}")
                return self._fallback_direct_collection()

        except Exception as e:
            logger.error(f"강제 데이터 새로고침 실패: {e}")
            return {"success": False, "error": str(e)}

    def _copy_data_from_collector(self, collector_data) -> int:
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

    def _fallback_direct_collection(self) -> Dict[str, Any]:
        logger.info("컬렉터 사용 불가, 메인 앱에서 직접 수집 시도")
        return {
            "success": False,
            "error": "컬렉터 연결 실패 및 직접 수집 미구현",
            "fallback_attempted": True,
            "suggestion": "수동으로 REGTECH 포털에서 데이터를 다운로드하세요",
        }

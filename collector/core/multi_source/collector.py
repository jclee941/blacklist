import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from collector.config import CollectorConfig
from collector.core.multi_source.models import SourceConfig, SourceType
from collector.core.multi_source.parsers import MultiSourceParserMixin
from collector.core.regtech_collector import regtech_collector

logger = logging.getLogger(__name__)


class MultiSourceCollector(MultiSourceParserMixin):
    def __init__(self):
        self.sources: Dict[str, SourceConfig] = {}
        self.collection_stats = {
            "total_sources": 0,
            "active_sources": 0,
            "total_collected": 0,
            "collection_history": [],
        }
        self._setup_default_sources()

    def _setup_default_sources(self):
        self.add_source(
            SourceConfig(
                source_type=SourceType.REGTECH,
                name="한국 금융보안원 REGTECH",
                url="https://regtech.fsec.or.kr",
                priority=1,
                rate_limit=0.5,
                confidence_boost=20,
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.URLHAUS,
                name="URLhaus Malware URLs",
                url="https://urlhaus-api.abuse.ch/v1/payloads/recent/",
                priority=2,
                rate_limit=2.0,
                data_format="json",
                ip_field="url_host",
                confidence_boost=15,
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.THREATFOX,
                name="ThreatFox IOCs",
                url="https://threatfox-api.abuse.ch/api/v1/",
                priority=2,
                rate_limit=2.0,
                data_format="json",
                ip_field="ioc",
                confidence_boost=15,
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.FEODO,
                name="Feodo Tracker Botnet C&C",
                url="https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt",
                priority=2,
                rate_limit=1.0,
                data_format="text",
                confidence_boost=18,
                category="botnet",
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.PHISHTANK,
                name="PhishTank Phishing URLs",
                url="http://data.phishtank.com/data/online-valid.json",
                priority=3,
                rate_limit=0.2,
                data_format="json",
                ip_field="url",
                confidence_boost=10,
                category="phishing",
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.OPENPHISH,
                name="OpenPhish Feed",
                url="https://openphish.com/feed.txt",
                priority=3,
                rate_limit=1.0,
                data_format="text",
                confidence_boost=8,
                category="phishing",
            )
        )

        self.add_source(
            SourceConfig(
                source_type=SourceType.CUSTOM_API,
                name="Custom Threat Feed",
                url="https://example.com/threat-feed",
                priority=4,
                enabled=False,
                rate_limit=1.0,
                headers={"X-API-Key": "YOUR_API_KEY"},
                confidence_boost=5,
            )
        )

        logger.info(f"📋 기본 위협 정보 소스 {len(self.sources)}개 설정 완료")

    def add_source(self, source_config: SourceConfig):
        source_id = f"{source_config.source_type.value}_{source_config.name.replace(' ', '_')}"
        self.sources[source_id] = source_config

        if source_config.enabled:
            self.collection_stats["active_sources"] += 1
        self.collection_stats["total_sources"] += 1

        logger.info(f"➕ 위협 정보 소스 추가: {source_config.name} ({source_config.source_type.value})")

    async def collect_from_all_sources(
        self,
        max_ips_per_source: int = 50000,
        parallel_sources: int = 5,
        date_range_days: int = 7,
    ) -> Dict[str, Any]:
        collection_start = time.time()
        logger.info("🚀 다중 소스 넓은 범위 수집 시작")
        logger.info(f"📊 설정: 소스당 최대 {max_ips_per_source:,}개, 병렬 {parallel_sources}개")

        active_sources = [(source_id, config) for source_id, config in self.sources.items() if config.enabled]
        active_sources.sort(key=lambda x: x[1].priority)

        collected_results = {}
        total_collected = 0

        semaphore = asyncio.Semaphore(parallel_sources)

        async def collect_from_source(source_id: str, config: SourceConfig):
            async with semaphore:
                try:
                    logger.info(f"🔄 소스 수집 시작: {config.name}")

                    if config.source_type == SourceType.REGTECH:
                        result = await self._collect_regtech_async(max_ips_per_source, date_range_days)
                    else:
                        result = await self._collect_from_external_source(source_id, config, max_ips_per_source)

                    collected_results[source_id] = result
                    logger.info(f"✅ {config.name}: {len(result.get('data', []))}개 수집")

                    return result

                except Exception as e:
                    logger.error(f"❌ {config.name} 수집 실패: {e}")
                    collected_results[source_id] = {
                        "success": False,
                        "error": str(e),
                        "data": [],
                    }
                    return {"success": False, "error": str(e), "data": []}

        tasks = [collect_from_source(source_id, config) for source_id, config in active_sources]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_collected_data = []
        source_stats = {}

        for (source_id, config), result in zip(active_sources, results):
            if isinstance(result, Exception):
                logger.error(f"❌ {config.name} 수집 예외: {result}")
                source_stats[source_id] = {"collected": 0, "error": str(result)}
                continue

            if isinstance(result, dict) and result.get("success"):
                source_data = result.get("data", [])
                all_collected_data.extend(source_data)
                source_stats[source_id] = {
                    "collected": len(source_data),
                    "source_name": config.name,
                    "confidence_boost": config.confidence_boost,
                }
            else:
                error_msg = result.get("error", "알 수 없는 오류") if isinstance(result, dict) else str(result)
                source_stats[source_id] = {"collected": 0, "error": error_msg}

        unique_data = self._deduplicate_and_enhance(all_collected_data)
        total_collected = len(unique_data)

        collection_time = time.time() - collection_start

        collection_result = {
            "success": True,
            "total_collected": total_collected,
            "unique_ips": len(set(item.get("ip_address") for item in unique_data)),
            "sources_attempted": len(active_sources),
            "sources_successful": len([s for s in source_stats.values() if "error" not in s]),
            "collection_time_seconds": round(collection_time, 2),
            "source_breakdown": source_stats,
            "data": unique_data,
            "timestamp": datetime.now().isoformat(),
        }

        self.collection_stats["total_collected"] += total_collected
        self.collection_stats["collection_history"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "total_collected": total_collected,
                "sources_used": len(active_sources),
                "collection_time": collection_time,
            }
        )

        logger.info(f"🎯 다중 소스 수집 완료: {total_collected:,}개 IP, {collection_time:.2f}초")
        return collection_result

    async def _collect_regtech_async(self, max_ips: int, date_range_days: int) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()

        def sync_collect():
            try:
                if not regtech_collector.authenticated:
                    username = CollectorConfig.REGTECH_ID
                    password = CollectorConfig.REGTECH_PW
                    if not regtech_collector.authenticate(username, password):
                        return {"success": False, "error": "REGTECH 인증 실패", "data": []}

                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=date_range_days)).strftime("%Y-%m-%d")

                collected_data = regtech_collector.collect_blacklist_data(
                    page_size=2000,
                    start_date=start_date,
                    end_date=end_date,
                    max_pages=max_ips // 2000 + 1,
                )

                if len(collected_data) > max_ips:
                    collected_data = collected_data[:max_ips]

                return {
                    "success": True,
                    "data": collected_data,
                    "source": "REGTECH",
                    "collection_params": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "max_pages": max_ips // 2000 + 1,
                    },
                }

            except Exception as e:
                return {"success": False, "error": str(e), "data": []}

        return await loop.run_in_executor(None, sync_collect)

    async def _collect_from_external_source(self, source_id: str, config: SourceConfig, max_ips: int) -> Dict[str, Any]:
        import aiohttp

        try:
            await asyncio.sleep(1.0 / config.rate_limit)

            headers = config.headers or {}
            params = config.params or {}

            timeout = aiohttp.ClientTimeout(total=config.timeout)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                if config.source_type == SourceType.THREATFOX:
                    post_data = {"query": "get_iocs", "days": 7}
                    async with session.post(config.url, json=post_data, headers=headers) as response:
                        data = await response.json()
                        return self._parse_threatfox_data(data, config, max_ips)

                elif config.data_format == "text":
                    async with session.get(config.url, headers=headers, params=params) as response:
                        text_data = await response.text()
                        return self._parse_text_feed(text_data, config, max_ips)

                elif config.data_format == "json":
                    async with session.get(config.url, headers=headers, params=params) as response:
                        json_data = await response.json()
                        return self._parse_json_feed(json_data, config, max_ips)

                else:
                    return {
                        "success": False,
                        "error": f"지원하지 않는 데이터 형식: {config.data_format}",
                        "data": [],
                    }

        except Exception as e:
            logger.error(f"❌ {config.name} 수집 오류: {e}")
            return {"success": False, "error": str(e), "data": []}

    def _deduplicate_and_enhance(self, all_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ip_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in all_data:
            ip = item.get("ip_address")
            if ip:
                if ip not in ip_groups:
                    ip_groups[ip] = []
                ip_groups[ip].append(item)

        enhanced_data = []

        for ip, items in ip_groups.items():
            if len(items) == 1:
                enhanced_data.append(items[0])
            else:
                merged_item = self._merge_multiple_sources(items)
                enhanced_data.append(merged_item)

        return enhanced_data

    def _merge_multiple_sources(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        base_item = max(items, key=lambda x: x.get("confidence_level", 0))

        sources = [item.get("source", "Unknown") for item in items]

        total_detections = sum(item.get("detection_count", 1) for item in items)

        total_confidence = sum(item.get("confidence_level", 0) for item in items)
        avg_confidence = min(100, int(total_confidence / len(items)) + len(items) * 2)

        best_reason = max(items, key=lambda x: len(x.get("reason", "")))["reason"]

        detection_dates = [item.get("detection_date") for item in items if item.get("detection_date")]
        earliest_date = min(detection_dates) if detection_dates else None

        merged = base_item.copy()
        merged.update(
            {
                "source": f"Multi-Source ({len(sources)}개)",
                "sources": sources,
                "reason": best_reason,
                "confidence_level": avg_confidence,
                "detection_count": total_detections,
                "detection_date": earliest_date,
                "multi_source": True,
                "source_count": len(sources),
            }
        )

        return merged

    def get_source_status(self) -> Dict[str, Any]:
        active_sources = []
        inactive_sources = []

        for source_id, config in self.sources.items():
            source_info = {
                "id": source_id,
                "name": config.name,
                "type": config.source_type.value,
                "priority": config.priority,
                "rate_limit": config.rate_limit,
                "confidence_boost": config.confidence_boost,
            }

            if config.enabled:
                active_sources.append(source_info)
            else:
                inactive_sources.append(source_info)

        return {
            "total_sources": len(self.sources),
            "active_sources": len(active_sources),
            "inactive_sources": len(inactive_sources),
            "active_source_list": active_sources,
            "inactive_source_list": inactive_sources,
            "collection_stats": self.collection_stats,
        }

    def enable_source(self, source_type: str, enabled: bool = True):
        for source_id, config in self.sources.items():
            if source_type.lower() in source_id.lower():
                config.enabled = enabled
                logger.info(f"{'✅' if enabled else '❌'} 소스 {config.name} {'활성화' if enabled else '비활성화'}")
                return True
        return False

    def add_custom_source(
        self,
        name: str,
        url: str,
        source_type: SourceType = SourceType.CUSTOM_API,
        **kwargs,
    ) -> bool:
        try:
            config = SourceConfig(source_type=source_type, name=name, url=url, **kwargs)
            self.add_source(config)
            return True
        except Exception as e:
            logger.error(f"❌ 사용자 정의 소스 추가 실패: {e}")
            return False


multi_source_collector = MultiSourceCollector()

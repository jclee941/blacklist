import ipaddress
import json
import logging
from datetime import datetime
from typing import Any, Dict

from collector.core.multi_source.models import SourceConfig

logger = logging.getLogger(__name__)


class MultiSourceParserMixin:
    def _parse_threatfox_data(self, data: Dict, config: SourceConfig, max_ips: int) -> Dict[str, Any]:
        collected_ips = []

        try:
            if data.get("query_status") == "ok":
                iocs = data.get("data", [])

                for ioc_data in iocs[:max_ips]:
                    ioc_value = ioc_data.get("ioc")
                    ioc_type = ioc_data.get("ioc_type", "")

                    if ioc_type in ["ip:port", "ip"] and self._is_valid_ip(ioc_value.split(":")[0]):
                        ip_address = ioc_value.split(":")[0]

                        collected_ips.append(
                            {
                                "ip_address": ip_address,
                                "source": config.name,
                                "reason": ioc_data.get("threat_type", "ThreatFox IOC"),
                                "category": self._determine_category_from_threat_type(ioc_data.get("threat_type", "")),
                                "confidence_level": 70 + config.confidence_boost,
                                "detection_count": 1,
                                "is_active": True,
                                "last_seen": datetime.now(),
                                "detection_date": ioc_data.get("first_seen", "")[:10]
                                if ioc_data.get("first_seen")
                                else None,
                                "malware_family": ioc_data.get("malware", ""),
                                "threat_type": ioc_data.get("threat_type", ""),
                            }
                        )

            return {"success": True, "data": collected_ips}

        except Exception as e:
            return {"success": False, "error": str(e), "data": []}

    def _parse_text_feed(self, text_data: str, config: SourceConfig, max_ips: int) -> Dict[str, Any]:
        collected_ips = []

        try:
            lines = text_data.strip().split("\n")
            ip_count = 0

            for line in lines:
                if ip_count >= max_ips:
                    break

                line = line.strip()

                if not line or line.startswith("#") or line.startswith("//"):
                    continue

                if line.startswith("http"):
                    try:
                        from urllib.parse import urlparse

                        parsed = urlparse(line)
                        potential_ip = parsed.hostname
                    except Exception:
                        potential_ip = line
                else:
                    potential_ip = line.split(":")[0]

                if self._is_valid_ip(potential_ip):
                    collected_ips.append(
                        {
                            "ip_address": potential_ip,
                            "source": config.name,
                            "reason": f"{config.name} 위협 목록",
                            "category": config.category,
                            "confidence_level": 65 + config.confidence_boost,
                            "detection_count": 1,
                            "is_active": True,
                            "last_seen": datetime.now(),
                            "original_entry": line,
                        }
                    )
                    ip_count += 1

            return {"success": True, "data": collected_ips}

        except Exception as e:
            return {"success": False, "error": str(e), "data": []}

    def _parse_json_feed(self, json_data: Any, config: SourceConfig, max_ips: int) -> Dict[str, Any]:
        collected_ips = []

        try:
            if isinstance(json_data, list):
                data_items = json_data
            elif isinstance(json_data, dict):
                data_items = (
                    json_data.get("data")
                    or json_data.get("results")
                    or json_data.get("items")
                    or json_data.get("entries")
                    or [json_data]
                )
            else:
                data_items = []

            ip_count = 0
            for item in data_items:
                if ip_count >= max_ips:
                    break

                if not isinstance(item, dict):
                    continue

                ip_address = None
                for field in [
                    config.ip_field,
                    "ip",
                    "ip_address",
                    "host",
                    "target",
                    "url",
                ]:
                    if field in item:
                        ip_candidate = str(item[field])

                        if ip_candidate.startswith("http"):
                            try:
                                from urllib.parse import urlparse

                                parsed = urlparse(ip_candidate)
                                ip_candidate = parsed.hostname
                            except Exception:
                                continue

                        if self._is_valid_ip(ip_candidate):
                            ip_address = ip_candidate
                            break

                if ip_address:
                    reason = item.get(config.reason_field or "description", f"{config.name} 위협")
                    detection_date = item.get(config.date_field or "date", "")

                    collected_ips.append(
                        {
                            "ip_address": ip_address,
                            "source": config.name,
                            "reason": reason,
                            "category": config.category,
                            "confidence_level": 60 + config.confidence_boost,
                            "detection_count": 1,
                            "is_active": True,
                            "last_seen": datetime.now(),
                            "detection_date": detection_date[:10] if detection_date else None,
                            "raw_data": json.dumps(item)[:500],
                        }
                    )
                    ip_count += 1

            return {"success": True, "data": collected_ips}

        except Exception as e:
            return {"success": False, "error": str(e), "data": []}

    def _determine_category_from_threat_type(self, threat_type: str) -> str:
        threat_lower = threat_type.lower()

        if any(keyword in threat_lower for keyword in ["botnet", "c2", "command"]):
            return "botnet"
        elif any(keyword in threat_lower for keyword in ["phishing", "phish"]):
            return "phishing"
        elif any(keyword in threat_lower for keyword in ["malware", "trojan", "rat"]):
            return "malware"
        elif any(keyword in threat_lower for keyword in ["spam", "bulk"]):
            return "spam"
        else:
            return "malicious"

    def _is_valid_ip(self, ip_str: str) -> bool:
        try:
            if not ip_str:
                return False

            ip_obj = ipaddress.ip_address(ip_str.strip())

            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast:
                return False

            return True

        except ValueError:
            return False

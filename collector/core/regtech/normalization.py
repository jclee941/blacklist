import ipaddress
import logging
from datetime import datetime
from typing import Any, Dict, Final, Optional

logger = logging.getLogger(__name__)

_COUNTRY_MAPPING: Final[dict[str, str]] = {
    "KR": "KR",
    "KOREA": "KR",
    "한국": "KR",
    "US": "US",
    "USA": "US",
    "UNITED STATES": "US",
    "CN": "CN",
    "CHINA": "CN",
    "중국": "CN",
    "JP": "JP",
    "JAPAN": "JP",
    "일본": "JP",
}
_THREAT_ADJUSTMENTS: Final[dict[str, int]] = {
    "critical": 15,
    "high": 10,
    "medium": 0,
    "low": -10,
}
_DATE_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%Y%m%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
)


class RegtechNormalizationMixin:
    def _normalize_country_code(self, country_value) -> Optional[str]:
        if not country_value:
            return None

        country_str = str(country_value).upper().strip()
        return _COUNTRY_MAPPING.get(country_str, country_str[:2] if len(country_str) >= 2 else None)

    def _determine_confidence(self, item: Dict[str, Any]) -> int:
        base_confidence = 80
        threat_level = str(item.get("threatLevel", "medium")).lower()
        confidence = base_confidence + _THREAT_ADJUSTMENTS.get(threat_level, 0)
        if item.get("verified"):
            confidence += 5
        if item.get("reportCount", 0) > 10:
            confidence += 5
        return max(10, min(100, confidence))

    def _parse_date(self, date_str: Any) -> Optional[str]:
        if not date_str:
            return None

        logger.info(f"📅 날짜 파싱 시도: '{date_str}' (타입: {type(date_str)})")
        for fmt in _DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                result = parsed_date.strftime("%Y-%m-%d")
                logger.info(f"✅ 날짜 파싱 성공: '{date_str}' -> '{result}' (형식: {fmt})")
                return result
            except ValueError:
                continue
        logger.warning(f"❌ 날짜 파싱 실패: '{date_str}' - 지원되지 않는 형식")
        return None

    def _is_valid_ip(self, ip_str: str) -> bool:
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
            return not (ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast)
        except ValueError:
            return False

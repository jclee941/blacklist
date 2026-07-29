import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegtechDataProcessorMixin:
    def _post_process_collected_data(self, collected_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not collected_data:
            return []

        logger.info(f"🔧 수집 데이터 후처리 시작: {len(collected_data)}개 항목")

        valid_data = []
        for item in collected_data:
            ip_addr = item.get("ip_address", "").strip()
            if self._is_valid_ip(ip_addr):
                item["ip_address"] = ip_addr
                valid_data.append(item)

        unique_data = self._fast_deduplication(valid_data)

        enhanced_data = []
        for item in unique_data:
            enhanced_item = self._enhance_data_quality(item)
            enhanced_data.append(enhanced_item)

        logger.info(f"✅ 후처리 완료: {len(enhanced_data)}개 IP")
        return enhanced_data

    def _fast_deduplication(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_ips = set()
        unique_data = []

        for item in data:
            ip_key = f"{item.get('ip_address')}:{item.get('source', 'REGTECH')}"
            if ip_key not in seen_ips:
                seen_ips.add(ip_key)
                unique_data.append(item)

        return unique_data

    def _enhance_data_quality(self, item: Dict[str, Any]) -> Dict[str, Any]:
        removal_date = self._parse_date(item.get("removal_date"))

        is_active = True
        if removal_date:
            today = datetime.now().date()
            if isinstance(removal_date, str):
                removal_date_obj = datetime.strptime(removal_date, "%Y-%m-%d").date()
            else:
                removal_date_obj = removal_date.date() if hasattr(removal_date, "date") else removal_date

            if removal_date_obj < today:
                is_active = False
                logger.info(
                    f"🔴 [품질향상] IP {item.get('ip_address')} 비활성화: 해제일 {removal_date_obj} < 오늘 {today}"
                )

        original_reason = item.get("reason", "")
        if not original_reason or original_reason in [
            "REGTECH HTML Parse",
            "REGTECH Blacklist",
        ]:
            for alt_field in [
                "contents",
                "detail",
                "description",
                "threat_desc",
                "block_reason",
            ]:
                alt_content = item.get(alt_field, "").strip()
                if alt_content and len(alt_content) > 5:
                    original_reason = alt_content
                    break
            if not original_reason:
                original_reason = "REGTECH 위협 IP"

        enhanced_item = {
            "ip_address": item.get("ip_address", "").strip(),
            "source": "REGTECH",
            "reason": original_reason,
            "confidence_level": self._determine_confidence(item),
            "detection_count": 1,
            "is_active": is_active,
            "last_seen": datetime.now(),
            "country": self._normalize_country_code(item.get("country")),
            "detection_date": self._parse_date(item.get("detection_date")),
            "removal_date": removal_date,
            "collection_timestamp": datetime.now().isoformat(),
            "data_source_version": "optimized_v2.0",
        }

        return enhanced_item

    def _normalize_country_code(self, country_value) -> Optional[str]:
        if not country_value:
            return None

        country_str = str(country_value).upper().strip()

        country_mapping = {
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

        return country_mapping.get(country_str, country_str[:2] if len(country_str) >= 2 else None)

    def _process_regtech_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            ip_fields = ["ipAddr", "ip_address", "ip", "IP", "target_ip"]
            ip_address = None

            for field in ip_fields:
                if field in item and item[field]:
                    ip_address = str(item[field]).strip()
                    break

            if not ip_address or not self._is_valid_ip(ip_address):
                return None

            logger.info(f"🔍 원본 REGTECH 데이터: {item}")

            detection_fields = [
                "regDt",
                "detectionDate",
                "reg_dt",
                "detect_dt",
                "created_dt",
            ]
            removal_fields = ["delDt", "removalDate", "del_dt", "remove_dt", "end_dt"]
            reason_fields = [
                "blockReason",
                "reason",
                "block_reason",
                "description",
                "content",
            ]

            detection_date = None
            removal_date = None
            detection_reason = "REGTECH Blacklist"

            for field in detection_fields:
                if field in item and item[field]:
                    detection_date = self._parse_date(item[field])
                    logger.info(f"✅ 탐지일 발견: {field} = {item[field]} -> {detection_date}")
                    break

            for field in removal_fields:
                if field in item and item[field]:
                    removal_date = self._parse_date(item[field])
                    logger.info(f"✅ 해제일 발견: {field} = {item[field]} -> {removal_date}")
                    break

            for field in reason_fields:
                if field in item and item[field]:
                    raw_reason = str(item[field]).strip()
                    if raw_reason and raw_reason not in [
                        "REGTECH HTML Parse",
                        "REGTECH Blacklist",
                        "",
                    ]:
                        detection_reason = raw_reason
                        logger.info(f"✅ 원본 탐지내용 발견: {field} = {detection_reason}")
                        break
                    elif raw_reason:
                        detection_reason = raw_reason
                        logger.info(f"📝 기본 탐지내용 사용: {field} = {detection_reason}")

            additional_content_fields = [
                "contents",
                "detail",
                "description",
                "threat_desc",
                "attack_info",
                "malware_name",
            ]
            for field in additional_content_fields:
                if field in item and item[field]:
                    additional_content = str(item[field]).strip()
                    if additional_content and len(additional_content) > len(detection_reason):
                        detection_reason = additional_content
                        logger.info(f"✅ 상세 탐지내용 발견: {field} = {detection_reason}")
                        break

            is_active = True
            if removal_date:
                today = datetime.now().date()
                if isinstance(removal_date, str):
                    removal_date_obj = datetime.strptime(removal_date, "%Y-%m-%d").date()
                else:
                    removal_date_obj = removal_date.date() if hasattr(removal_date, "date") else removal_date

                if removal_date_obj < today:
                    is_active = False
                    logger.info(f"🔴 IP {ip_address} 비활성화: 해제일 {removal_date_obj} < 오늘 {today}")

            processed_item = {
                "ip_address": ip_address,
                "source": "REGTECH",
                "reason": detection_reason,
                "confidence_level": self._determine_confidence(item),
                "detection_count": 1,
                "is_active": is_active,
                "last_seen": datetime.now(),
                "country": item.get("country") or item.get("countryCode"),
                "detection_date": detection_date,
                "removal_date": removal_date,
                "raw_data": {
                    "api_response": item,
                    "collection_timestamp": datetime.now().isoformat(),
                },
            }

            return processed_item

        except Exception as e:
            logger.debug(f"항목 처리 중 오류 (무시): {e}")
            return None

    def _determine_confidence(self, item: Dict[str, Any]) -> int:
        base_confidence = 80

        threat_level = str(item.get("threatLevel", "medium")).lower()
        threat_adjustments = {"critical": 15, "high": 10, "medium": 0, "low": -10}

        confidence = base_confidence + threat_adjustments.get(threat_level, 0)

        if item.get("verified"):
            confidence += 5
        if item.get("reportCount", 0) > 10:
            confidence += 5

        return max(10, min(100, confidence))

    def _parse_date(self, date_str: Any) -> Optional[str]:
        if not date_str:
            return None

        logger.info(f"📅 날짜 파싱 시도: '{date_str}' (타입: {type(date_str)})")

        date_formats = [
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
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                result = parsed_date.strftime("%Y-%m-%d")
                logger.info(f"✅ 날짜 파싱 성공: '{date_str}' -> '{result}' (형식: {fmt})")
                return result
            except ValueError:
                continue

        logger.warning(f"❌ 날짜 파싱 실패: '{date_str}' - 지원되지 않는 형식")
        return None

    def _parse_html_response(self, html_content: str) -> Optional[List[Dict[str, Any]]]:
        from core.regtech_parsers import parse_html_response

        return parse_html_response(html_content)

    def _extract_country_info(self, cell_texts: List[str]) -> Optional[str]:
        if not cell_texts:
            return None

        country_patterns = {
            "KR": ["KR", "Korea", "한국", "South Korea", "Republic of Korea"],
            "US": ["US", "USA", "United States", "미국", "America"],
            "CN": ["CN", "China", "중국", "CHN"],
            "JP": ["JP", "Japan", "일본", "JPN"],
            "RU": ["RU", "Russia", "러시아", "Russian"],
            "DE": ["DE", "Germany", "독일", "German"],
            "FR": ["FR", "France", "프랑스", "French"],
            "GB": ["GB", "UK", "United Kingdom", "영국", "Britain"],
            "IN": ["IN", "India", "인도", "Indian"],
        }

        for cell_text in cell_texts:
            if not cell_text or len(cell_text.strip()) < 2:
                continue

            cell_upper = cell_text.upper().strip()

            for country_code, patterns in country_patterns.items():
                for pattern in patterns:
                    if pattern.upper() in cell_upper:
                        logger.info(f"✅ 국가 정보 발견: '{cell_text}' -> {country_code}")
                        return country_code

            if len(cell_text.strip()) == 2 and cell_text.strip().isalpha():
                country_code = cell_text.strip().upper()
                logger.info(f"✅ 국가 코드 발견: {country_code}")
                return country_code

        return None

    def _is_valid_ip(self, ip_str: str) -> bool:
        try:
            import ipaddress

            ip_obj = ipaddress.ip_address(ip_str.strip())

            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast:
                return False

            return True

        except ValueError:
            return False

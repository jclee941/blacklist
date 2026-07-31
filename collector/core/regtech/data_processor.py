import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .html_parsing import RegtechHtmlParsingMixin
from .normalization import RegtechNormalizationMixin

logger = logging.getLogger(__name__)


class RegtechDataProcessorMixin(RegtechNormalizationMixin, RegtechHtmlParsingMixin):
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

        enhanced_data = [self._enhance_data_quality(item) for item in unique_data]

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
            removal_date_obj = datetime.strptime(removal_date, "%Y-%m-%d").date()

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

        return {
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
                removal_date_obj = datetime.strptime(removal_date, "%Y-%m-%d").date()

                if removal_date_obj < today:
                    is_active = False
                    logger.info(f"🔴 IP {ip_address} 비활성화: 해제일 {removal_date_obj} < 오늘 {today}")

            return {
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

        except Exception as e:
            logger.debug(f"항목 처리 중 오류 (무시): {e}")
            return None

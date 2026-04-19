"""Database helper methods extracted from DatabaseService."""

import ipaddress
import json
import logging
from datetime import datetime
from typing import Any, Dict, List


logger = logging.getLogger(__package__ or __name__)


class DatabaseQueryMixin:
    def _filter_invalid_ips(self, ip_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
        """
        사설 IP 및 오탐 IP 필터링

        제외 대상:
        - 사설 IP 대역 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
        - Loopback (127.0.0.0/8)
        - Link-local (169.254.0.0/16)
        - 잘못된 IP 형식
        - Reserved IP
        - 해제일(removal_date)이 이미 지난 IP
        """
        valid_ips = []
        excluded_count = 0
        expired_count = 0
        today = datetime.now().date()

        for item in ip_data:
            ip_str = item.get("ip_address")
            if not ip_str:
                excluded_count += 1
                continue

            try:
                ip = ipaddress.ip_address(ip_str)

                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    excluded_count += 1
                    logger.debug(f"🚫 제외된 IP: {ip_str} (사설/예약 대역)")
                    continue

                removal_date = self._convert_date_string(item.get("removal_date"))
                if removal_date and removal_date < today:
                    expired_count += 1
                    logger.debug(f"🚫 제외된 IP: {ip_str} (해제일 {removal_date} 경과)")
                    continue

                valid_ips.append(item)

            except ValueError:
                excluded_count += 1
                logger.debug(f"🚫 제외된 IP: {ip_str} (잘못된 형식)")
                continue

        excluded_msg = f"{excluded_count}개 제외 (사설/형식), {expired_count}개 제외 (해제일 경과)"
        logger.info(f"📊 IP 필터링: {len(valid_ips)}개 유효, {excluded_msg}")
        return valid_ips, excluded_count + expired_count

    def _memory_optimized_dedup(self, ip_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """메모리 최적화된 중복 제거 - 대용량 데이터 지원"""
        seen_ips = set()
        unique_data = []

        for item in ip_data:
            ip_addr = item.get("ip_address")
            if ip_addr and ip_addr not in seen_ips:
                seen_ips.add(ip_addr)
                unique_data.append(item)

                if len(unique_data) >= getattr(self, "_cache_max_size"):
                    logger.warning(f"⚠️ 메모리 제한에 도달: {len(unique_data)}개 IP로 제한")
                    break

        return unique_data

    def _batch_check_existing_ips(self, ip_addresses: List[str]) -> set[str]:
        """배치로 기존 IP 존재 여부 확인 - 성능 최적화"""
        if not ip_addresses:
            return set()

        existing_ips: set[str] = set()

        try:
            with getattr(self, "get_connection")() as conn:
                cursor = conn.cursor()

                batch_size = 1000
                for batch in self._get_batches(ip_addresses, batch_size):
                    placeholders = ",".join(["%s"] * len(batch))
                    query = f"""
                        SELECT DISTINCT ip_address
                        FROM blacklist_ips
                        WHERE ip_address IN ({placeholders})
                    """
                    cursor.execute(query, batch)
                    results = cursor.fetchall()
                    existing_ips.update(row[0] for row in results)

                cursor.close()

        except Exception as e:
            logger.error(f"기존 IP 확인 실패: {e}")

        return existing_ips

    def _get_batches(self, data: List[Any], batch_size: int):
        """메모리 효율적인 배치 분할"""
        for i in range(0, len(data), batch_size):
            yield data[i : i + batch_size]

    def _optimized_batch_insert(self, cursor, batch: List[Dict[str, Any]]) -> int:
        """최적화된 배치 삽입 - 직접 executemany 사용"""
        if not batch:
            return 0

        return self._fallback_batch_insert(cursor, batch)

    def _fallback_batch_insert(self, cursor, batch: List[Dict[str, Any]]) -> int:
        """대체 배치 삽입 방식 - executemany (raw_data JSONB 포함)"""
        values = []
        for item in batch:
            raw_data_value = item.get("raw_data")
            if raw_data_value and isinstance(raw_data_value, dict):
                raw_data_json = json.dumps(raw_data_value, ensure_ascii=False)
            elif isinstance(raw_data_value, str):
                raw_data_json = raw_data_value
            else:
                raw_data_json = json.dumps(
                    {
                        "ip_address": item.get("ip_address"),
                        "country": item.get("country"),
                        "reason": item.get("reason"),
                        "detection_date": str(item.get("detection_date")) if item.get("detection_date") else None,
                        "removal_date": str(item.get("removal_date")) if item.get("removal_date") else None,
                        "confidence_level": item.get("confidence_level"),
                        "collection_timestamp": datetime.now().isoformat(),
                    },
                    ensure_ascii=False,
                )

            removal_date = self._convert_date_string(item.get("removal_date"))
            if removal_date and removal_date < datetime.now().date():
                is_active = False
            else:
                is_active = item.get("is_active", True)

            values.append(
                (
                    item.get("ip_address"),
                    item.get("reason", "Blacklist IP"),
                    item.get("source", "COLLECTOR"),
                    self._convert_confidence_to_int(item.get("confidence_level", 50)),
                    item.get("detection_count", 1),
                    item.get("last_seen", datetime.now()),
                    is_active,
                    datetime.now(),
                    datetime.now(),
                    self._convert_date_string(item.get("detection_date")),
                    removal_date,
                    item.get("country"),
                    raw_data_json,
                    item.get("data_source", "REGTECH"),
                )
            )

        try:
            cursor.executemany(
                """
                INSERT INTO blacklist_ips
                (ip_address, reason, source, confidence_level,
                 detection_count, last_seen, is_active, created_at, updated_at,
                 detection_date, removal_date, country, raw_data, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip_address, source) DO UPDATE SET
                    detection_count = blacklist_ips.detection_count + 1,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at,
                    reason = EXCLUDED.reason,
                    removal_date = COALESCE(EXCLUDED.removal_date, blacklist_ips.removal_date),
                    is_active = CASE
                        WHEN COALESCE(EXCLUDED.removal_date, blacklist_ips.removal_date) < CURRENT_DATE
                        THEN false
                        ELSE EXCLUDED.is_active
                    END,
                    country = COALESCE(EXCLUDED.country, blacklist_ips.country),
                    raw_data = EXCLUDED.raw_data,
                    data_source = COALESCE(blacklist_ips.data_source, EXCLUDED.data_source)
            """,
                values,
            )
            return cursor.rowcount
        except Exception as e:
            logger.error(f"배치 삽입 실패: {e}")
            return 0

    def _convert_confidence_to_int(self, confidence_value) -> int:
        """신뢰도 값을 정수로 변환"""
        if isinstance(confidence_value, int):
            return confidence_value
        if isinstance(confidence_value, str):
            confidence_mapping = {
                "high": 90,
                "medium": 50,
                "low": 10,
                "critical": 95,
                "unknown": 5,
            }
            return confidence_mapping.get(confidence_value.lower(), 50)
        return 50

    def _convert_date_string(self, date_str):
        """날짜 문자열을 date 객체로 변환"""
        if not date_str or not isinstance(date_str, str):
            return None

        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None

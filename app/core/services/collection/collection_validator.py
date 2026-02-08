"""
Collection Validator
수집 데이터 검증 및 전처리
"""

import logging
import ipaddress
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CollectionValidator:
    """수집 데이터 검증 및 전처리 클래스"""

    def __init__(self):
        self.validation_rules = {
            "ip_address": self._validate_ip_address,
            "confidence_level": self._validate_confidence_level,
            "source": self._validate_source,
        }

    def _convert_confidence_to_int(self, confidence_value) -> int:
        """Convert confidence string to integer value for database storage"""
        if isinstance(confidence_value, int):
            return max(0, min(100, confidence_value))
        elif isinstance(confidence_value, str):
            confidence_mapping = {
                "high": 90,
                "medium": 50,
                "low": 10,
                "critical": 95,
                "very_high": 85,
                "moderate": 40,
                "suspicious": 70,
            }
            return confidence_mapping.get(confidence_value.lower(), 50)
        else:
            return 50  # Default confidence

    def _validate_ip_address(self, ip_address: str) -> bool:
        """IP 주소 유효성 검증"""
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return False

    def _validate_confidence_level(self, confidence: Any) -> int:
        """신뢰도 검증 및 변환"""
        return self._convert_confidence_to_int(confidence)

    def _validate_source(self, source: str) -> str:
        """데이터 소스 검증"""
        if not source or not isinstance(source, str):
            return "unknown"
        return source.upper()[:50]  # 최대 50자

    def validate_collection_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """수집된 데이터 전체 검증"""
        validated_data = []

        for item in data:
            if self._validate_single_item(item):
                validated_item = self._process_single_item(item)
                if validated_item:
                    validated_data.append(validated_item)

        logger.info(f"Validated {len(validated_data)} items out of {len(data)} total")
        return validated_data

    def _validate_single_item(self, item: Dict[str, Any]) -> bool:
        """단일 아이템 기본 검증"""
        if not isinstance(item, dict):
            return False

        # IP 주소는 필수
        if "ip_address" not in item or not self._validate_ip_address(item["ip_address"]):
            return False

        return True

    def _process_single_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """단일 아이템 처리 및 변환"""
        try:
            processed_item = {
                "ip_address": item["ip_address"].strip(),
                "source": self._validate_source(item.get("source", "REGTECH")),
                "confidence_level": self._validate_confidence_level(item.get("confidence_level", 50)),
                "reason": (item.get("reason", "").strip()[:500] if item.get("reason") else None),
                "detection_date": self._process_date(item.get("detection_date")),
                "removal_date": self._process_date(item.get("removal_date")),
                "country": (item.get("country", "").strip()[:10] if item.get("country") else None),
                "is_active": bool(item.get("is_active", True)),
            }

            return processed_item

        except Exception as e:
            logger.error(f"Error processing item {item}: {e}")
            return None

    def _process_date(self, date_value: Any) -> Optional[str]:
        """날짜 값 처리"""
        if not date_value:
            return None

        if isinstance(date_value, datetime):
            return date_value.date().isoformat()
        elif isinstance(date_value, str):
            try:
                # 다양한 날짜 형식 처리
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                    try:
                        parsed_date = datetime.strptime(date_value, fmt)
                        return parsed_date.date().isoformat()
                    except ValueError:
                        continue
            except BaseException:
                pass

        return None

    def _validate_collection_prerequisites(self, username: str = None, password: str = None) -> Dict[str, Any]:
        """수집 전제조건 검증"""
        validation_result = {"valid": True, "errors": [], "warnings": []}

        # 인증 정보 검증
        if username and len(username.strip()) < 3:
            validation_result["errors"].append("Username must be at least 3 characters")
            validation_result["valid"] = False

        if password and len(password) < 6:
            validation_result["errors"].append("Password must be at least 6 characters")
            validation_result["valid"] = False

        # 시스템 리소스 검증
        try:
            import psutil

            # 메모리 사용량 체크
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                validation_result["warnings"].append(f"High memory usage: {memory.percent}%")

            # 디스크 공간 체크
            disk = psutil.disk_usage("/")
            if disk.percent > 90:
                validation_result["warnings"].append(f"Low disk space: {disk.percent}% used")

        except ImportError:
            pass

        return validation_result


# Singleton instance
validator = CollectionValidator()

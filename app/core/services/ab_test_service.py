#!/usr/bin/env python3
"""
A/B 테스트 서비스 - Phase 3.3: 점진적 롤아웃
새로운 블랙리스트 로직을 안전하게 배포
"""

import logging
import hashlib
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ABTestService:
    """A/B 테스트 관리 서비스"""

    def __init__(self):
        # A/B 테스트 설정
        self.NEW_LOGIC_PERCENTAGE = 10  # 10%만 새 로직 적용
        self.FEATURE_FLAGS = {
            "scoring_system": {
                "enabled": True,
                "percentage": 10,
                "description": "스코어링 시스템 점진적 롤아웃",
            },
            "whitelist_priority": {
                "enabled": True,
                "percentage": 100,  # 이미 전체 적용
                "description": "화이트리스트 우선 체크",
            },
        }

    def should_use_new_logic(self, ip: str, feature: str = "scoring_system") -> bool:
        """
        새 로직 적용 여부 결정 (일관성 보장)

        Args:
            ip: IP 주소
            feature: 기능 이름

        Returns:
            True if 새 로직 적용, False if 기존 로직 적용
        """
        feature_config = self.FEATURE_FLAGS.get(feature)

        if not feature_config or not feature_config["enabled"]:
            return False

        percentage = feature_config["percentage"]

        if percentage >= 100:
            return True

        # IP 기반 일관된 해싱 (같은 IP는 항상 같은 결과)
        ip_hash = int(hashlib.md5(ip.encode()).hexdigest(), 16)
        bucket = ip_hash % 100

        return bucket < percentage

    def track_experiment(self, ip: str, feature: str, variant: str, result: Dict[str, Any]) -> None:
        """
        실험 결과 추적

        Args:
            ip: IP 주소
            feature: 기능 이름
            variant: 실험 변형 ("control" or "treatment")
            result: 결과 데이터
        """
        log_data = {
            "event": "ab_test_result",
            "ip": ip,
            "feature": feature,
            "variant": variant,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"A/B Test: {log_data}")

    def get_feature_status(self) -> Dict[str, Any]:
        """
        모든 기능 플래그 상태 조회

        Returns:
            기능 플래그 현황
        """
        return {
            "features": self.FEATURE_FLAGS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def update_feature_percentage(self, feature: str, percentage: int) -> Dict[str, Any]:
        """
        기능 롤아웃 비율 업데이트

        Args:
            feature: 기능 이름
            percentage: 새로운 비율 (0-100)

        Returns:
            업데이트 결과
        """
        if feature not in self.FEATURE_FLAGS:
            return {"success": False, "error": f"Unknown feature: {feature}"}

        if not 0 <= percentage <= 100:
            return {"success": False, "error": "Percentage must be between 0 and 100"}

        old_percentage = self.FEATURE_FLAGS[feature]["percentage"]
        self.FEATURE_FLAGS[feature]["percentage"] = percentage

        logger.info(f"Feature '{feature}' percentage updated: {old_percentage}% → {percentage}%")

        return {
            "success": True,
            "feature": feature,
            "old_percentage": old_percentage,
            "new_percentage": percentage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# 전역 서비스 인스턴스 대체
# ab_test_service = ABTestService()
from flask import current_app
from werkzeug.local import LocalProxy

ab_test_service = LocalProxy(lambda: current_app.extensions["ab_test_service"])

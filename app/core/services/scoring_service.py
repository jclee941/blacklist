#!/usr/bin/env python3
"""
스코어링 서비스 - Phase 3.2: 위협 스코어링 시스템
IP 위협 수준을 점수화하여 차단 여부 결정
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class ThreatScoringService:
    """위협 스코어링 서비스"""

    def __init__(self):
        # 스코어링 임계값
        self.BLOCK_THRESHOLD = 80
        self.CHALLENGE_THRESHOLD = 50
        self.ALLOW_THRESHOLD = 0

    def calculate_score(self, ip: str, context: Optional[Dict[str, Any]] = None) -> int:
        """
        IP 위협 점수 계산 (Phase 3.2)

        Args:
            ip: IP 주소
            context: 추가 컨텍스트 정보

        Returns:
            위협 점수 (0-100)
        """
        score = 0
        context = context or {}

        # 1. 블랙리스트 매칭 (50점)
        if context.get("in_blacklist", False):
            score += 50
            logger.info(f"Score +50: {ip} in blacklist")

        # 2. 탐지 횟수 (최대 30점)
        detection_count = context.get("detection_count", 0)
        if detection_count > 0:
            detection_score = min(detection_count * 5, 30)
            score += detection_score
            logger.info(f"Score +{detection_score}: {ip} detected {detection_count} times")

        # 3. 소스 신뢰도 (최대 20점)
        source = context.get("source", "unknown")
        source_scores = {
            "REGTECH": 15,  # 공신력 높음
            "manual": 20,  # 수동 등록 (의심)
            "unknown": 10,
        }
        source_score = source_scores.get(source, 10)
        score += source_score
        logger.info(f"Score +{source_score}: {ip} from {source}")

        # 4. 최근 활동 (최대 10점)
        last_seen = context.get("last_seen")
        if last_seen:
            # 최근 24시간 이내 활동이면 가산점
            try:
                if isinstance(last_seen, str):
                    last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                else:
                    last_seen_dt = last_seen

                if last_seen_dt.tzinfo is None:
                    last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)

                if datetime.now(timezone.utc) - last_seen_dt < timedelta(hours=24):
                    score += 10
                    logger.info(f"Score +10: {ip} active within 24h")
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to parse last_seen: {e}")

        return min(score, 100)  # 최대 100점

    def get_action(self, score: int) -> str:
        """
        점수 기반 액션 결정

        Args:
            score: 위협 점수

        Returns:
            액션 ("BLOCK", "CHALLENGE", "ALLOW")
        """
        if score >= self.BLOCK_THRESHOLD:
            return "BLOCK"
        elif score >= self.CHALLENGE_THRESHOLD:
            return "CHALLENGE"  # CAPTCHA 등
        else:
            return "ALLOW"

    def evaluate_with_scoring(self, ip: str, blacklist_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        스코어링 기반 종합 평가

        Args:
            ip: IP 주소
            blacklist_data: 블랙리스트 데이터

        Returns:
            평가 결과
        """
        context = {}

        if blacklist_data:
            context["in_blacklist"] = True
            context["detection_count"] = blacklist_data.get("detection_count", 0)
            context["source"] = blacklist_data.get("source", "unknown")
            context["last_seen"] = blacklist_data.get("last_seen")
        else:
            context["in_blacklist"] = False

        score = self.calculate_score(ip, context)
        action = self.get_action(score)

        return {
            "ip": ip,
            "score": score,
            "action": action,
            "threshold": {
                "block": self.BLOCK_THRESHOLD,
                "challenge": self.CHALLENGE_THRESHOLD,
                "allow": self.ALLOW_THRESHOLD,
            },
            "details": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def explain_score(self, ip: str, score_result: Dict[str, Any]) -> str:
        """
        점수 설명 텍스트 생성

        Args:
            ip: IP 주소
            score_result: 스코어링 결과

        Returns:
            설명 텍스트
        """
        score = score_result["score"]
        action = score_result["action"]
        details = score_result["details"]

        explanation_parts = [f"IP {ip}의 위협 점수: {score}/100 → {action}"]

        if details.get("in_blacklist"):
            explanation_parts.append(f"- 블랙리스트 등록됨 (소스: {details.get('source', 'unknown')})")

        if details.get("detection_count", 0) > 0:
            explanation_parts.append(f"- 탐지 횟수: {details['detection_count']}회")

        if action == "BLOCK":
            explanation_parts.append("→ 권장: 즉시 차단")
        elif action == "CHALLENGE":
            explanation_parts.append("→ 권장: CAPTCHA 인증 요구")
        else:
            explanation_parts.append("→ 권장: 허용")

        return "\n".join(explanation_parts)


# 전역 서비스 인스턴스 대체
# scoring_service = ThreatScoringService()
from flask import current_app
from werkzeug.local import LocalProxy

scoring_service = LocalProxy(lambda: current_app.extensions["scoring_service"])

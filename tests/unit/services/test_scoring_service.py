"""ThreatScoringService 유닛 테스트"""

import pytest
from datetime import datetime, timedelta

from app.core.services.scoring_service import ThreatScoringService


@pytest.mark.unit
class TestThreatScoringServiceInit:
    """초기화 테스트"""

    def test_default_thresholds(self):
        service = ThreatScoringService()
        assert service.BLOCK_THRESHOLD == 80
        assert service.CHALLENGE_THRESHOLD == 50
        assert service.ALLOW_THRESHOLD == 0


@pytest.mark.unit
class TestCalculateScore:
    """calculate_score 메서드 테스트"""

    def setup_method(self):
        self.service = ThreatScoringService()

    def test_no_context_returns_base_source_score(self):
        """컨텍스트 없으면 unknown 소스 기본점수 10점"""
        score = self.service.calculate_score("1.2.3.4")
        assert score == 10

    def test_none_context_returns_base_score(self):
        score = self.service.calculate_score("1.2.3.4", None)
        assert score == 10

    def test_empty_context_returns_base_score(self):
        score = self.service.calculate_score("1.2.3.4", {})
        assert score == 10

    def test_blacklist_adds_50(self):
        score = self.service.calculate_score("1.2.3.4", {"in_blacklist": True})
        # 50 (blacklist) + 10 (unknown source) = 60
        assert score == 60

    def test_blacklist_false_no_bonus(self):
        score = self.service.calculate_score("1.2.3.4", {"in_blacklist": False})
        assert score == 10

    def test_detection_count_scoring(self):
        """탐지 횟수: count * 5, 최대 30점"""
        # 1회 -> 5점
        score = self.service.calculate_score("1.2.3.4", {"detection_count": 1})
        assert score == 15  # 5 + 10 (unknown source)

        # 3회 -> 15점
        score = self.service.calculate_score("1.2.3.4", {"detection_count": 3})
        assert score == 25  # 15 + 10

        # 6회 -> 30점 (cap)
        score = self.service.calculate_score("1.2.3.4", {"detection_count": 6})
        assert score == 40  # 30 + 10

    def test_detection_count_cap_at_30(self):
        """탐지 횟수 최대 30점 제한"""
        score = self.service.calculate_score("1.2.3.4", {"detection_count": 100})
        assert score == 40  # 30 (cap) + 10 (unknown source)

    def test_detection_count_zero_no_bonus(self):
        score = self.service.calculate_score("1.2.3.4", {"detection_count": 0})
        assert score == 10

    def test_source_scores(self):
        """소스별 점수"""
        assert self.service.calculate_score("1.2.3.4", {"source": "REGTECH"}) == 15
        assert self.service.calculate_score("1.2.3.4", {"source": "manual"}) == 20
        assert self.service.calculate_score("1.2.3.4", {"source": "unknown"}) == 10
        assert self.service.calculate_score("1.2.3.4", {"source": "other_source"}) == 10

    def test_recent_activity_within_24h(self):
        """24시간 이내 활동이면 +10점"""
        recent = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        score = self.service.calculate_score("1.2.3.4", {"last_seen": recent})
        assert score == 20  # 10 (unknown source) + 10 (recent)

    def test_recent_activity_beyond_24h_no_bonus(self):
        """24시간 이후 활동은 가산점 없음"""
        old = (datetime.utcnow() - timedelta(hours=48)).isoformat()
        score = self.service.calculate_score("1.2.3.4", {"last_seen": old})
        assert score == 10

    def test_recent_activity_datetime_object(self):
        """datetime 객체도 처리 가능"""
        recent = datetime.utcnow() - timedelta(hours=1)
        score = self.service.calculate_score("1.2.3.4", {"last_seen": recent})
        assert score == 20

    def test_recent_activity_invalid_string(self):
        """잘못된 날짜 문자열은 무시"""
        score = self.service.calculate_score("1.2.3.4", {"last_seen": "not-a-date"})
        assert score == 10

    def test_max_score_capped_at_100(self):
        """최대 100점 제한"""
        recent = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        context = {
            "in_blacklist": True,  # 50
            "detection_count": 100,  # 30 (cap)
            "source": "manual",  # 20
            "last_seen": recent,  # 10
        }
        score = self.service.calculate_score("1.2.3.4", context)
        assert score == 100  # 50+30+20+10 = 110 -> capped at 100

    def test_combined_score_below_cap(self):
        """복합 점수 100 이하"""
        context = {
            "in_blacklist": True,  # 50
            "detection_count": 2,  # 10
            "source": "REGTECH",  # 15
        }
        score = self.service.calculate_score("1.2.3.4", context)
        assert score == 75


@pytest.mark.unit
class TestGetAction:
    """get_action 메서드 테스트"""

    def setup_method(self):
        self.service = ThreatScoringService()

    def test_block_at_threshold(self):
        assert self.service.get_action(80) == "BLOCK"

    def test_block_above_threshold(self):
        assert self.service.get_action(100) == "BLOCK"
        assert self.service.get_action(90) == "BLOCK"

    def test_challenge_at_threshold(self):
        assert self.service.get_action(50) == "CHALLENGE"

    def test_challenge_between_thresholds(self):
        assert self.service.get_action(79) == "CHALLENGE"
        assert self.service.get_action(65) == "CHALLENGE"

    def test_allow_below_challenge(self):
        assert self.service.get_action(49) == "ALLOW"
        assert self.service.get_action(0) == "ALLOW"
        assert self.service.get_action(10) == "ALLOW"


@pytest.mark.unit
class TestEvaluateWithScoring:
    """evaluate_with_scoring 메서드 테스트"""

    def setup_method(self):
        self.service = ThreatScoringService()

    def test_no_blacklist_data(self):
        result = self.service.evaluate_with_scoring("1.2.3.4")
        assert result["ip"] == "1.2.3.4"
        assert result["score"] == 10  # unknown source only
        assert result["action"] == "ALLOW"
        assert result["details"]["in_blacklist"] is False
        assert "threshold" in result
        assert "timestamp" in result

    def test_with_blacklist_data(self):
        data = {
            "detection_count": 3,
            "source": "REGTECH",
        }
        result = self.service.evaluate_with_scoring("1.2.3.4", data)
        assert result["details"]["in_blacklist"] is True
        # 50 (blacklist) + 15 (3*5) + 15 (REGTECH) = 80
        assert result["score"] == 80
        assert result["action"] == "BLOCK"

    def test_result_shape(self):
        result = self.service.evaluate_with_scoring("1.2.3.4")
        assert "ip" in result
        assert "score" in result
        assert "action" in result
        assert "threshold" in result
        assert "details" in result
        assert "timestamp" in result
        assert result["threshold"]["block"] == 80
        assert result["threshold"]["challenge"] == 50
        assert result["threshold"]["allow"] == 0

    def test_none_blacklist_data(self):
        result = self.service.evaluate_with_scoring("1.2.3.4", None)
        assert result["details"]["in_blacklist"] is False


@pytest.mark.unit
class TestExplainScore:
    """explain_score 메서드 테스트"""

    def setup_method(self):
        self.service = ThreatScoringService()

    def test_block_explanation(self):
        score_result = {
            "score": 85,
            "action": "BLOCK",
            "details": {
                "in_blacklist": True,
                "detection_count": 3,
                "source": "REGTECH",
            },
        }
        explanation = self.service.explain_score("1.2.3.4", score_result)
        assert "85/100" in explanation
        assert "BLOCK" in explanation
        assert "블랙리스트 등록됨" in explanation
        assert "탐지 횟수: 3회" in explanation
        assert "즉시 차단" in explanation

    def test_challenge_explanation(self):
        score_result = {
            "score": 60,
            "action": "CHALLENGE",
            "details": {"in_blacklist": True, "detection_count": 0, "source": "unknown"},
        }
        explanation = self.service.explain_score("1.2.3.4", score_result)
        assert "CAPTCHA" in explanation

    def test_allow_explanation(self):
        score_result = {
            "score": 10,
            "action": "ALLOW",
            "details": {"in_blacklist": False, "detection_count": 0},
        }
        explanation = self.service.explain_score("1.2.3.4", score_result)
        assert "허용" in explanation
        assert "블랙리스트 등록됨" not in explanation

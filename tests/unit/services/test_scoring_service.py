"""Unit tests for ScoringService"""

import pytest
from app.core.services.scoring_service import scoring_service

class TestScoring:
    def test_calculate_risk_score(self):
        result = scoring_service.calculate_score({"detection_count": 5, "sources": 2})
        assert isinstance(result, (int, float))

    def test_score_range(self):
        result = scoring_service.calculate_score({})
        assert 0 <= result <= 100


"""Tests for DataQualityManager pure methods from core/data_quality_manager.py."""

import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "test-key-for-unit-tests")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

from core.data_quality_manager import DataQualityManager


@pytest.fixture
def manager():
    return DataQualityManager()


class TestGenerateRecommendations:
    def test_low_active_rate(self, manager):
        report = {"metrics": {"active_rate": 50, "freshness_score": 80}}
        recs = manager._generate_recommendations(report)
        assert len(recs) == 1
        assert "활성 IP" in recs[0]

    def test_low_freshness(self, manager):
        report = {"metrics": {"active_rate": 90, "freshness_score": 40}}
        recs = manager._generate_recommendations(report)
        assert any("신선도" in r for r in recs)

    def test_high_duplicate_rate(self, manager):
        report = {"metrics": {"active_rate": 90, "duplicate_rate": 10}}
        recs = manager._generate_recommendations(report)
        assert any("중복" in r for r in recs)

    def test_missing_detection_date(self, manager):
        report = {"metrics": {"active_rate": 90, "missing_detection_date": 5}}
        recs = manager._generate_recommendations(report)
        assert any("탐지일" in r for r in recs)

    def test_all_good_no_recommendations(self, manager):
        report = {
            "metrics": {
                "active_rate": 95,
                "freshness_score": 85,
                "duplicate_rate": 1,
                "missing_detection_date": 0,
            }
        }
        recs = manager._generate_recommendations(report)
        assert len(recs) == 0

    def test_multiple_issues(self, manager):
        report = {
            "metrics": {
                "active_rate": 50,
                "freshness_score": 40,
                "duplicate_rate": 10,
                "missing_detection_date": 3,
            }
        }
        recs = manager._generate_recommendations(report)
        assert len(recs) == 4

    def test_empty_metrics(self, manager):
        # All defaults are 0: active_rate=0 (<80 triggers), freshness_score=0 (<70 triggers)
        report = {"metrics": {}}
        recs = manager._generate_recommendations(report)
        assert len(recs) == 2
        assert any("활성 IP" in r for r in recs)
        assert any("신선도" in r for r in recs)

    def test_missing_metrics_key(self, manager):
        # Same as empty metrics — all defaults trigger active_rate and freshness
        report = {}
        recs = manager._generate_recommendations(report)
        assert len(recs) == 2

    def test_boundary_active_rate_at_threshold(self, manager):
        report = {"metrics": {"active_rate": 80, "freshness_score": 80}}
        recs = manager._generate_recommendations(report)
        assert len(recs) == 0

    def test_boundary_active_rate_just_below(self, manager):
        report = {"metrics": {"active_rate": 79.9, "freshness_score": 80}}
        recs = manager._generate_recommendations(report)
        assert len(recs) == 1

    def test_boundary_freshness_at_threshold(self, manager):
        report = {"metrics": {"active_rate": 90, "freshness_score": 70}}
        recs = manager._generate_recommendations(report)
        assert not any("신선도" in r for r in recs)

    def test_boundary_duplicate_at_threshold(self, manager):
        report = {"metrics": {"active_rate": 90, "duplicate_rate": 5}}
        recs = manager._generate_recommendations(report)
        assert not any("중복" in r for r in recs)


class TestCalculateQualityScore:
    def test_perfect_scores(self, manager):
        report = {
            "metrics": {
                "active_rate": 100,
                "freshness_score": 100,
                "duplicate_rate": 0,
            },
            "issues": [],
        }
        score = manager._calculate_quality_score(report)
        assert score == 100

    def test_all_zeros(self, manager):
        report = {
            "metrics": {
                "active_rate": 0,
                "freshness_score": 0,
                "duplicate_rate": 0,
            },
            "issues": [],
        }
        # 0*0.3 + 0*0.3 + 100*0.2 + 100*0.2 = 40
        score = manager._calculate_quality_score(report)
        assert score == 40

    def test_many_issues_reduce_integrity(self, manager):
        report = {
            "metrics": {
                "active_rate": 100,
                "freshness_score": 100,
                "duplicate_rate": 0,
            },
            "issues": ["issue1", "issue2", "issue3", "issue4", "issue5"],
        }
        # active: 100*0.3=30, fresh: 100*0.3=30, dup: 100*0.2=20, integ: max(0,100-50)=50*0.2=10
        score = manager._calculate_quality_score(report)
        assert score == 90

    def test_high_duplicate_rate(self, manager):
        report = {
            "metrics": {
                "active_rate": 100,
                "freshness_score": 100,
                "duplicate_rate": 5,
            },
            "issues": [],
        }
        # dup_score = max(0, 100 - 5*20) = 0
        # 100*0.3 + 100*0.3 + 0*0.2 + 100*0.2 = 30+30+0+20 = 80
        score = manager._calculate_quality_score(report)
        assert score == 80

    def test_empty_report(self, manager):
        report = {}
        score = manager._calculate_quality_score(report)
        # all defaults: active=0, fresh=0, dup=0 → dup_score=100, integ=100
        # 0*0.3 + 0*0.3 + 100*0.2 + 100*0.2 = 40
        assert score == 40

    def test_returns_int(self, manager):
        report = {
            "metrics": {
                "active_rate": 75,
                "freshness_score": 65,
                "duplicate_rate": 2,
            },
            "issues": ["one"],
        }
        score = manager._calculate_quality_score(report)
        assert isinstance(score, int)

    def test_ten_issues_zeroes_integrity(self, manager):
        report = {
            "metrics": {
                "active_rate": 100,
                "freshness_score": 100,
                "duplicate_rate": 0,
            },
            "issues": [f"issue{i}" for i in range(10)],
        }
        # integrity = max(0, 100 - 100) = 0
        # 30 + 30 + 20 + 0 = 80
        score = manager._calculate_quality_score(report)
        assert score == 80

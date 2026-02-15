"""Tests for REGTECHPolicyMonitor._compare_structures from core/policy_monitor.py."""

import pytest
from core.policy_monitor import REGTECHPolicyMonitor


@pytest.fixture
def monitor():
    config = {
        "regtech_base_url": "https://example.com",
        "postgres_host": "localhost",
    }
    return REGTECHPolicyMonitor(config)


def _make_structure(**overrides):
    base = {
        "forms": 2,
        "tables": 3,
        "inputs": 5,
        "selects": 1,
        "buttons": 4,
        "scripts": 6,
        "css_links": 2,
        "html_hash": "abcdef1234567890",
        "content_hash": "1234567890abcdef",
        "table_headers": [["IP", "Country", "Reason"]],
    }
    base.update(overrides)
    return base


class TestCompareStructures:
    def test_no_baseline(self, monitor):
        result = monitor._compare_structures({"forms": 1}, None)
        assert result["change_detected"] is False
        assert "No baseline" in result["message"]

    def test_empty_baseline(self, monitor):
        result = monitor._compare_structures({"forms": 1}, {})
        assert result["change_detected"] is False

    def test_identical_structures(self, monitor):
        s = _make_structure()
        result = monitor._compare_structures(s, s.copy())
        assert result["change_detected"] is False
        assert result["change_percentage"] == 0.0
        assert len(result["changes"]) == 0

    def test_one_element_changed(self, monitor):
        baseline = _make_structure()
        current = _make_structure(forms=10)
        result = monitor._compare_structures(current, baseline)
        assert "forms" in result["changes"][0]
        # 1 out of 10 = 10%, below 15% threshold
        assert result["change_detected"] is False

    def test_two_elements_changed_triggers_detection(self, monitor):
        baseline = _make_structure()
        current = _make_structure(forms=10, tables=10)
        result = monitor._compare_structures(current, baseline)
        assert result["change_detected"] is True
        assert result["severity"] == "medium"

    def test_html_hash_changed(self, monitor):
        baseline = _make_structure()
        current = _make_structure(html_hash="different_hash_value")
        result = monitor._compare_structures(current, baseline)
        assert any("HTML" in c for c in result["changes"])

    def test_content_hash_changed(self, monitor):
        baseline = _make_structure()
        current = _make_structure(content_hash="different_content")
        result = monitor._compare_structures(current, baseline)
        assert any("콘텐츠" in c for c in result["changes"])

    def test_table_headers_changed(self, monitor):
        baseline = _make_structure()
        current = _make_structure(table_headers=[["IP", "NewColumn"]])
        result = monitor._compare_structures(current, baseline)
        assert any("테이블 헤더" in c for c in result["changes"])

    def test_severity_high_above_50_percent(self, monitor):
        baseline = _make_structure()
        current = _make_structure(
            forms=99,
            tables=99,
            inputs=99,
            selects=99,
            buttons=99,
            scripts=99,
            html_hash="x",
            content_hash="y",
        )
        result = monitor._compare_structures(current, baseline)
        assert result["change_detected"] is True
        assert result["severity"] == "high"

    def test_severity_medium_between_25_and_50(self, monitor):
        baseline = _make_structure()
        # Change 3 structure keys + 1 hash = 4/10 = 40%
        current = _make_structure(forms=99, tables=99, inputs=99, html_hash="x")
        result = monitor._compare_structures(current, baseline)
        assert result["change_detected"] is True
        assert result["severity"] == "medium"

    def test_below_threshold_no_detection(self, monitor):
        baseline = _make_structure()
        current = _make_structure(forms=99)
        result = monitor._compare_structures(current, baseline)
        assert result["change_detected"] is False
        assert result["severity"] == "low"

    def test_change_percentage_calculation(self, monitor):
        baseline = _make_structure()
        # Change all 7 structure keys + 3 hash/header = 10/10 = 100%
        current = _make_structure(
            forms=99,
            tables=99,
            inputs=99,
            selects=99,
            buttons=99,
            scripts=99,
            css_links=99,
            html_hash="x",
            content_hash="y",
            table_headers=[["New"]],
        )
        result = monitor._compare_structures(current, baseline)
        assert result["change_percentage"] == 100.0

    def test_missing_keys_in_current(self, monitor):
        baseline = _make_structure()
        current = {}
        result = monitor._compare_structures(current, baseline)
        # All 7 structure keys differ (0 vs N), plus hashes and headers missing
        assert result["change_detected"] is True

    def test_missing_keys_in_baseline_no_false_positive(self, monitor):
        baseline = {"forms": 2, "tables": 3}
        current = {"forms": 2, "tables": 3}
        result = monitor._compare_structures(current, baseline)
        assert result["change_detected"] is False

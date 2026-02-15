"""Tests for RegtechDataProcessorMixin from core/regtech/data_processor.py."""

import pytest

from core.regtech.data_processor import RegtechDataProcessorMixin


class ProcessorHost(RegtechDataProcessorMixin):
    pass


@pytest.fixture
def proc():
    return ProcessorHost()


class TestFastDeduplication:
    def test_no_duplicates(self, proc):
        data = [
            {"ip_address": "1.1.1.1", "source": "REGTECH"},
            {"ip_address": "2.2.2.2", "source": "REGTECH"},
        ]
        result = proc._fast_deduplication(data)
        assert len(result) == 2

    def test_removes_duplicates(self, proc):
        data = [
            {"ip_address": "1.1.1.1", "source": "REGTECH"},
            {"ip_address": "1.1.1.1", "source": "REGTECH"},
        ]
        result = proc._fast_deduplication(data)
        assert len(result) == 1

    def test_same_ip_different_source_kept(self, proc):
        data = [
            {"ip_address": "1.1.1.1", "source": "REGTECH"},
            {"ip_address": "1.1.1.1", "source": "OTHER"},
        ]
        result = proc._fast_deduplication(data)
        assert len(result) == 2

    def test_empty_list(self, proc):
        assert proc._fast_deduplication([]) == []

    def test_preserves_order(self, proc):
        data = [
            {"ip_address": "3.3.3.3", "source": "REGTECH"},
            {"ip_address": "1.1.1.1", "source": "REGTECH"},
            {"ip_address": "2.2.2.2", "source": "REGTECH"},
        ]
        result = proc._fast_deduplication(data)
        assert [r["ip_address"] for r in result] == ["3.3.3.3", "1.1.1.1", "2.2.2.2"]


class TestNormalizeCountryCode:
    def test_kr(self, proc):
        assert proc._normalize_country_code("KR") == "KR"

    def test_korea_english(self, proc):
        assert proc._normalize_country_code("Korea") == "KR"

    def test_korea_korean(self, proc):
        assert proc._normalize_country_code("한국") == "KR"

    def test_us(self, proc):
        assert proc._normalize_country_code("US") == "US"

    def test_usa(self, proc):
        assert proc._normalize_country_code("USA") == "US"

    def test_china(self, proc):
        assert proc._normalize_country_code("CN") == "CN"

    def test_japan(self, proc):
        assert proc._normalize_country_code("JP") == "JP"

    def test_none_returns_none(self, proc):
        assert proc._normalize_country_code(None) is None

    def test_empty_returns_none(self, proc):
        assert proc._normalize_country_code("") is None

    def test_unknown_code_truncated_to_2(self, proc):
        assert proc._normalize_country_code("BRAZIL") == "BR"

    def test_single_char_returns_none(self, proc):
        assert proc._normalize_country_code("X") is None

    def test_case_insensitive(self, proc):
        assert proc._normalize_country_code("korea") == "KR"


class TestDetermineConfidence:
    def test_default_medium(self, proc):
        assert proc._determine_confidence({}) == 80

    def test_critical(self, proc):
        assert proc._determine_confidence({"threatLevel": "critical"}) == 95

    def test_high(self, proc):
        assert proc._determine_confidence({"threatLevel": "high"}) == 90

    def test_low(self, proc):
        assert proc._determine_confidence({"threatLevel": "low"}) == 70

    def test_verified_bonus(self, proc):
        assert proc._determine_confidence({"verified": True}) == 85

    def test_high_report_count(self, proc):
        assert proc._determine_confidence({"reportCount": 20}) == 85

    def test_combined_max(self, proc):
        item = {"threatLevel": "critical", "verified": True, "reportCount": 50}
        assert proc._determine_confidence(item) == 100

    def test_floor_at_10(self, proc):
        assert proc._determine_confidence({"threatLevel": "low"}) >= 10


class TestParseDate:
    def test_iso_format(self, proc):
        assert proc._parse_date("2026-01-15") == "2026-01-15"

    def test_iso_with_time(self, proc):
        assert proc._parse_date("2026-01-15 10:30:00") == "2026-01-15"

    def test_slash_format(self, proc):
        assert proc._parse_date("2026/01/15") == "2026-01-15"

    def test_dot_format(self, proc):
        assert proc._parse_date("2026.01.15") == "2026-01-15"

    def test_compact(self, proc):
        assert proc._parse_date("20260115") == "2026-01-15"

    def test_none_returns_none(self, proc):
        assert proc._parse_date(None) is None

    def test_empty_returns_none(self, proc):
        assert proc._parse_date("") is None

    def test_invalid_returns_none(self, proc):
        assert proc._parse_date("not-a-date") is None


class TestIsValidIp:
    def test_public_ip(self, proc):
        assert proc._is_valid_ip("8.8.8.8") is True

    def test_private_ip(self, proc):
        assert proc._is_valid_ip("10.0.0.1") is False

    def test_loopback(self, proc):
        assert proc._is_valid_ip("127.0.0.1") is False

    def test_invalid_format(self, proc):
        assert proc._is_valid_ip("xyz") is False

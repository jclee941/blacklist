"""Tests for DatabaseService pure helper methods from core/database.py."""

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "test-key-for-unit-tests")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

from core.database import DatabaseService


@pytest.fixture
def db_svc():
    svc = DatabaseService.__new__(DatabaseService)
    svc.pool = None
    svc._ip_cache = {}
    svc._cache_max_size = 1000000
    svc._batch_buffer = []
    svc._cipher_suite = None
    return svc


class TestConvertConfidenceToInt:
    def test_int_passthrough(self, db_svc):
        assert db_svc._convert_confidence_to_int(85) == 85

    def test_high(self, db_svc):
        assert db_svc._convert_confidence_to_int("high") == 90

    def test_medium(self, db_svc):
        assert db_svc._convert_confidence_to_int("medium") == 50

    def test_low(self, db_svc):
        assert db_svc._convert_confidence_to_int("low") == 10

    def test_critical(self, db_svc):
        assert db_svc._convert_confidence_to_int("critical") == 95

    def test_unknown(self, db_svc):
        assert db_svc._convert_confidence_to_int("unknown") == 5

    def test_unrecognized_string(self, db_svc):
        assert db_svc._convert_confidence_to_int("whatever") == 50

    def test_case_insensitive(self, db_svc):
        assert db_svc._convert_confidence_to_int("HIGH") == 90

    def test_none_returns_default(self, db_svc):
        assert db_svc._convert_confidence_to_int(None) == 50

    def test_float_returns_default(self, db_svc):
        assert db_svc._convert_confidence_to_int(3.14) == 50


class TestConvertDateString:
    def test_valid_date(self, db_svc):
        assert db_svc._convert_date_string("2026-02-01") == date(2026, 2, 1)

    def test_none_returns_none(self, db_svc):
        assert db_svc._convert_date_string(None) is None

    def test_empty_string(self, db_svc):
        assert db_svc._convert_date_string("") is None

    def test_int_returns_none(self, db_svc):
        assert db_svc._convert_date_string(123) is None

    def test_invalid_format(self, db_svc):
        assert db_svc._convert_date_string("not-a-date") is None

    def test_slash_format_not_supported(self, db_svc):
        assert db_svc._convert_date_string("2026/02/01") is None

    def test_valid_boundary_date(self, db_svc):
        assert db_svc._convert_date_string("2000-01-01") == date(2000, 1, 1)


class TestFilterInvalidIps:
    def test_public_ip_passes(self, db_svc):
        data = [{"ip_address": "8.8.8.8"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 1
        assert excluded == 0

    def test_private_ip_excluded(self, db_svc):
        data = [{"ip_address": "192.168.1.1"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_loopback_excluded(self, db_svc):
        data = [{"ip_address": "127.0.0.1"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_link_local_excluded(self, db_svc):
        data = [{"ip_address": "169.254.0.1"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_invalid_format_excluded(self, db_svc):
        data = [{"ip_address": "not-an-ip"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_missing_ip_address_excluded(self, db_svc):
        data = [{"reason": "test"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_expired_removal_date_excluded(self, db_svc):
        data = [{"ip_address": "8.8.8.8", "removal_date": "2020-01-01"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1

    def test_future_removal_date_passes(self, db_svc):
        data = [{"ip_address": "8.8.8.8", "removal_date": "2099-01-01"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 1
        assert excluded == 0

    def test_no_removal_date_passes(self, db_svc):
        data = [{"ip_address": "1.1.1.1"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 1
        assert excluded == 0

    def test_mixed_valid_invalid(self, db_svc):
        data = [
            {"ip_address": "8.8.8.8"},
            {"ip_address": "192.168.1.1"},
            {"ip_address": "1.1.1.1"},
            {"ip_address": "not-ip"},
        ]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 2
        assert excluded == 2

    def test_empty_list(self, db_svc):
        valid, excluded = db_svc._filter_invalid_ips([])
        assert len(valid) == 0
        assert excluded == 0

    def test_ten_dot_ip_excluded(self, db_svc):
        data = [{"ip_address": "10.0.0.1"}]
        valid, excluded = db_svc._filter_invalid_ips(data)
        assert len(valid) == 0
        assert excluded == 1


class TestMemoryOptimizedDedup:
    def test_no_duplicates(self, db_svc):
        data = [
            {"ip_address": "8.8.8.8"},
            {"ip_address": "1.1.1.1"},
        ]
        result = db_svc._memory_optimized_dedup(data)
        assert len(result) == 2

    def test_duplicates_keep_first(self, db_svc):
        data = [
            {"ip_address": "8.8.8.8", "reason": "first"},
            {"ip_address": "8.8.8.8", "reason": "second"},
        ]
        result = db_svc._memory_optimized_dedup(data)
        assert len(result) == 1
        assert result[0]["reason"] == "first"

    def test_missing_ip_excluded(self, db_svc):
        data = [
            {"ip_address": "8.8.8.8"},
            {"reason": "no ip"},
            {"ip_address": None},
        ]
        result = db_svc._memory_optimized_dedup(data)
        assert len(result) == 1

    def test_empty_list(self, db_svc):
        result = db_svc._memory_optimized_dedup([])
        assert len(result) == 0

    def test_cache_max_size_limit(self, db_svc):
        db_svc._cache_max_size = 3
        data = [{"ip_address": f"1.1.1.{i}"} for i in range(10)]
        result = db_svc._memory_optimized_dedup(data)
        assert len(result) == 3


class TestGetBatches:
    def test_even_split(self, db_svc):
        data = [1, 2, 3, 4]
        batches = list(db_svc._get_batches(data, 2))
        assert batches == [[1, 2], [3, 4]]

    def test_uneven_split(self, db_svc):
        data = [1, 2, 3, 4, 5]
        batches = list(db_svc._get_batches(data, 2))
        assert batches == [[1, 2], [3, 4], [5]]

    def test_batch_larger_than_data(self, db_svc):
        data = [1, 2]
        batches = list(db_svc._get_batches(data, 10))
        assert batches == [[1, 2]]

    def test_empty_list(self, db_svc):
        batches = list(db_svc._get_batches([], 5))
        assert batches == []

    def test_batch_size_one(self, db_svc):
        data = [1, 2, 3]
        batches = list(db_svc._get_batches(data, 1))
        assert batches == [[1], [2], [3]]

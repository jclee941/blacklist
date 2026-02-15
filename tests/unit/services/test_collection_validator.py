"""Unit tests for CollectionValidator"""

import pytest
from unittest.mock import patch
from datetime import datetime


@pytest.mark.unit
class TestCollectionValidator:
    """Tests for CollectionValidator"""

    def setup_method(self):
        """Setup test fixtures"""
        from app.core.services.collection.collection_validator import CollectionValidator

        self.validator = CollectionValidator()

    # --- _validate_ip_address ---

    def test_validate_ip_address_valid_ipv4(self):
        assert self.validator._validate_ip_address("192.168.1.1") is True

    def test_validate_ip_address_valid_ipv6(self):
        assert self.validator._validate_ip_address("::1") is True

    def test_validate_ip_address_invalid(self):
        assert self.validator._validate_ip_address("not-an-ip") is False

    def test_validate_ip_address_empty(self):
        assert self.validator._validate_ip_address("") is False

    def test_validate_ip_address_none(self):
        assert self.validator._validate_ip_address(None) is False

    def test_validate_ip_address_with_port(self):
        assert self.validator._validate_ip_address("192.168.1.1:8080") is False

    # --- _convert_confidence_to_int ---

    def test_convert_confidence_int_normal(self):
        assert self.validator._convert_confidence_to_int(75) == 75

    def test_convert_confidence_int_clamped_high(self):
        assert self.validator._convert_confidence_to_int(150) == 100

    def test_convert_confidence_int_clamped_low(self):
        assert self.validator._convert_confidence_to_int(-10) == 0

    def test_convert_confidence_string_high(self):
        assert self.validator._convert_confidence_to_int("high") == 90

    def test_convert_confidence_string_medium(self):
        assert self.validator._convert_confidence_to_int("medium") == 50

    def test_convert_confidence_string_low(self):
        assert self.validator._convert_confidence_to_int("low") == 10

    def test_convert_confidence_string_critical(self):
        assert self.validator._convert_confidence_to_int("critical") == 95

    def test_convert_confidence_string_very_high(self):
        assert self.validator._convert_confidence_to_int("very_high") == 85

    def test_convert_confidence_string_moderate(self):
        assert self.validator._convert_confidence_to_int("moderate") == 40

    def test_convert_confidence_string_suspicious(self):
        assert self.validator._convert_confidence_to_int("suspicious") == 70

    def test_convert_confidence_unknown_string(self):
        assert self.validator._convert_confidence_to_int("unknown") == 50

    def test_convert_confidence_none(self):
        assert self.validator._convert_confidence_to_int(None) == 50

    # --- _validate_source ---

    def test_validate_source_normal(self):
        assert self.validator._validate_source("regtech") == "REGTECH"

    def test_validate_source_long_string(self):
        result = self.validator._validate_source("a" * 100)
        assert len(result) <= 50

    def test_validate_source_empty(self):
        assert self.validator._validate_source("") == "unknown"

    def test_validate_source_none(self):
        assert self.validator._validate_source(None) == "unknown"

    # --- _validate_single_item ---

    def test_validate_single_item_valid(self):
        item = {"ip_address": "10.0.0.1", "source": "REGTECH"}
        assert self.validator._validate_single_item(item) is True

    def test_validate_single_item_missing_ip(self):
        item = {"source": "REGTECH"}
        assert self.validator._validate_single_item(item) is False

    def test_validate_single_item_invalid_ip(self):
        item = {"ip_address": "invalid", "source": "REGTECH"}
        assert self.validator._validate_single_item(item) is False

    def test_validate_single_item_not_dict(self):
        assert self.validator._validate_single_item("not a dict") is False

    def test_validate_single_item_none(self):
        assert self.validator._validate_single_item(None) is False

    # --- validate_collection_data ---

    def test_validate_collection_data_all_valid(self):
        data = [
            {"ip_address": "10.0.0.1", "source": "regtech"},
            {"ip_address": "10.0.0.2", "source": "regtech"},
        ]
        result = self.validator.validate_collection_data(data)
        assert len(result) == 2

    def test_validate_collection_data_filters_invalid(self):
        data = [
            {"ip_address": "10.0.0.1", "source": "regtech"},
            {"ip_address": "invalid", "source": "regtech"},
            {"ip_address": "10.0.0.3", "source": "regtech"},
        ]
        result = self.validator.validate_collection_data(data)
        assert len(result) == 2

    def test_validate_collection_data_empty_list(self):
        result = self.validator.validate_collection_data([])
        assert result == []

    def test_validate_collection_data_all_invalid(self):
        data = [
            {"ip_address": "invalid1"},
            {"ip_address": "invalid2"},
        ]
        result = self.validator.validate_collection_data(data)
        assert result == []

    # --- _process_date ---

    def test_process_date_datetime_object(self):
        """datetime object is converted to date-only isoformat"""
        dt = datetime(2025, 1, 15, 10, 30)
        result = self.validator._process_date(dt)
        # Source strips time: date_value.date().isoformat() -> "2025-01-15"
        assert result == "2025-01-15"

    def test_process_date_date_string_dash(self):
        """YYYY-MM-DD string parsed correctly"""
        result = self.validator._process_date("2025-01-15")
        assert result is not None

    def test_process_date_date_string_slash(self):
        """YYYY/MM/DD string parsed correctly"""
        result = self.validator._process_date("2025/01/15")
        assert result is not None

    def test_process_date_iso_string_with_T(self):
        """ISO string with T separator is NOT supported — returns None"""
        result = self.validator._process_date("2025-01-15T10:30:00")
        # Source only tries ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']
        assert result is None

    def test_process_date_invalid_string(self):
        result = self.validator._process_date("not-a-date")
        assert result is None

    def test_process_date_none(self):
        result = self.validator._process_date(None)
        assert result is None

    # --- _validate_collection_prerequisites ---

    def test_validate_prerequisites_valid(self):
        """Valid credentials pass validation"""
        result = self.validator._validate_collection_prerequisites("admin", "password123")
        assert result.get("valid") is True

    def test_validate_prerequisites_short_username(self):
        """Username too short fails validation"""
        result = self.validator._validate_collection_prerequisites("ab", "password123")
        assert result.get("valid") is False

    def test_validate_prerequisites_short_password(self):
        """Password too short fails validation"""
        result = self.validator._validate_collection_prerequisites("admin", "12345")
        assert result.get("valid") is False

    def test_validate_prerequisites_empty_username(self):
        """Empty username passes validation (empty string is falsy, skips length check)"""
        result = self.validator._validate_collection_prerequisites("", "password123")
        # Empty string '' is falsy in Python, so `if username:` is False.
        # The length check is skipped, so valid=True (unless password fails).
        assert result.get("valid") is True

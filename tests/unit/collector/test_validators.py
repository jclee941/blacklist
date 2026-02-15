"""Tests for collector/core/validators.py — IP validation and normalization."""

import pytest
from core.validators import (
    validate_ip,
    validate_ip_or_cidr,
    is_private_ip,
    is_public_ip,
    normalize_ip,
    filter_valid_public_ips,
    validate_country_code,
)


class TestValidateIp:
    def test_valid_ipv4(self):
        assert validate_ip("192.168.1.1") is True
        assert validate_ip("10.0.0.1") is True
        assert validate_ip("255.255.255.255") is True
        assert validate_ip("0.0.0.0") is True

    def test_invalid_ipv4(self):
        assert validate_ip("256.1.1.1") is False
        assert validate_ip("1.2.3") is False
        assert validate_ip("abc.def.ghi.jkl") is False
        assert validate_ip("") is False
        assert validate_ip(None) is False

    def test_strips_whitespace(self):
        assert validate_ip("  10.0.0.1  ") is True

    def test_cidr_rejected(self):
        assert validate_ip("10.0.0.0/8") is False


class TestValidateIpOrCidr:
    def test_plain_ip(self):
        assert validate_ip_or_cidr("192.168.1.1") is True

    def test_cidr(self):
        assert validate_ip_or_cidr("10.0.0.0/8") is True
        assert validate_ip_or_cidr("192.168.0.0/24") is True
        assert validate_ip_or_cidr("0.0.0.0/0") is True

    def test_invalid_cidr(self):
        assert validate_ip_or_cidr("10.0.0.0/33") is False

    def test_empty(self):
        assert validate_ip_or_cidr("") is False
        assert validate_ip_or_cidr(None) is False


class TestIsPrivateIp:
    def test_private_ranges(self):
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("192.168.1.1") is True

    def test_loopback(self):
        assert is_private_ip("127.0.0.1") is True

    def test_link_local(self):
        assert is_private_ip("169.254.1.1") is True

    def test_public_ip(self):
        assert is_private_ip("8.8.8.8") is False

    def test_cidr_input(self):
        assert is_private_ip("10.0.0.0/8") is True

    def test_invalid_returns_false(self):
        assert is_private_ip("not-an-ip") is False


class TestIsPublicIp:
    def test_public(self):
        assert is_public_ip("8.8.8.8") is True
        assert is_public_ip("1.1.1.1") is True

    def test_private(self):
        assert is_public_ip("10.0.0.1") is False
        assert is_public_ip("192.168.1.1") is False

    def test_reserved(self):
        assert is_public_ip("0.0.0.0") is False
        assert is_public_ip("240.0.0.1") is False

    def test_invalid_returns_false(self):
        assert is_public_ip("garbage") is False


class TestNormalizeIp:
    def test_plain_ip(self):
        assert normalize_ip("8.8.8.8") == "8.8.8.8"

    def test_strips_whitespace(self):
        assert normalize_ip("  8.8.8.8  ") == "8.8.8.8"

    def test_cidr_strict_false(self):
        assert normalize_ip("10.0.0.5/8") == "10.0.0.0/8"

    def test_invalid_returns_none(self):
        assert normalize_ip("not-valid") is None

    def test_empty_returns_none(self):
        assert normalize_ip("") is None
        assert normalize_ip(None) is None


class TestFilterValidPublicIps:
    def test_mixed_list(self):
        valid, rejected = filter_valid_public_ips(
            [
                "8.8.8.8",
                "10.0.0.1",
                "1.1.1.1",
                "not-ip",
                "192.168.1.1",
            ]
        )
        assert "8.8.8.8" in valid
        assert "1.1.1.1" in valid
        assert len(valid) == 2
        assert len(rejected) == 3

    def test_empty_list(self):
        valid, rejected = filter_valid_public_ips([])
        assert valid == []
        assert rejected == []


class TestValidateCountryCode:
    def test_valid_codes(self):
        assert validate_country_code("KR") == "KR"
        assert validate_country_code("us") == "US"
        assert validate_country_code(" kr ") == "KR"

    def test_invalid_codes(self):
        assert validate_country_code("KOR") is None
        assert validate_country_code("1") is None
        assert validate_country_code("12") is None
        assert validate_country_code("") is None
        assert validate_country_code(None) is None

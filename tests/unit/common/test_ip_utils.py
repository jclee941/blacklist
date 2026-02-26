"""Tests for core.common.ip_utils"""

from core.common.ip_utils import IPUtils


class TestIsValidIp:
    def test_valid_ipv4(self):
        assert IPUtils.is_valid_ip("192.168.1.1") is True

    def test_valid_ipv6(self):
        assert IPUtils.is_valid_ip("::1") is True

    def test_invalid_ip(self):
        assert IPUtils.is_valid_ip("not-an-ip") is False

    def test_empty_string(self):
        assert IPUtils.is_valid_ip("") is False

    def test_none(self):
        assert IPUtils.is_valid_ip(None) is False

    def test_valid_public(self):
        assert IPUtils.is_valid_ip("8.8.8.8") is True

    def test_cidr_notation(self):
        assert IPUtils.is_valid_ip("192.168.1.0/24") is False


class TestIsPrivateIp:
    def test_private_10(self):
        assert IPUtils.is_private_ip("10.0.0.1") is True

    def test_private_172(self):
        assert IPUtils.is_private_ip("172.16.0.1") is True

    def test_private_192(self):
        assert IPUtils.is_private_ip("192.168.0.1") is True

    def test_public_ip(self):
        assert IPUtils.is_private_ip("8.8.8.8") is False

    def test_loopback(self):
        assert IPUtils.is_private_ip("127.0.0.1") is True

    def test_invalid_ip(self):
        assert IPUtils.is_private_ip("invalid") is False


class TestGetIpType:
    def test_private(self):
        assert IPUtils.get_ip_type("192.168.1.1") == "private"

    def test_loopback(self):
        assert IPUtils.get_ip_type("127.0.0.1") == "loopback"

    def test_multicast(self):
        assert IPUtils.get_ip_type("224.0.0.1") == "multicast"

    def test_public(self):
        assert IPUtils.get_ip_type("8.8.8.8") == "public"

    def test_invalid(self):
        assert IPUtils.get_ip_type("not-ip") == "invalid"

    def test_ipv6_loopback(self):
        assert IPUtils.get_ip_type("::1") == "loopback"

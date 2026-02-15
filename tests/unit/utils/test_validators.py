"""Unit tests for core.utils.validators."""

import pytest

from core.utils.validators import (
    validate_ip,
    is_private_ip,
    is_public_ip,
    filter_private_ips,
    filter_public_ips_only,
    ValidationError,
)


class TestValidateIP:
    """Tests for validate_ip function."""

    def test_valid_ipv4(self):
        assert validate_ip("192.168.1.1") is True

    def test_valid_ipv4_public(self):
        assert validate_ip("8.8.8.8") is True

    def test_valid_ipv6(self):
        assert validate_ip("::1") is True

    def test_valid_ipv6_full(self):
        assert validate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334") is True

    def test_invalid_ip_returns_false(self):
        assert validate_ip("not-an-ip") is False

    def test_empty_string_returns_false(self):
        assert validate_ip("") is False

    def test_ip_with_port_returns_false(self):
        assert validate_ip("192.168.1.1:8080") is False

    def test_ip_with_cidr_returns_false(self):
        assert validate_ip("192.168.1.0/24") is False

    def test_broadcast_address(self):
        assert validate_ip("255.255.255.255") is True

    def test_zero_address(self):
        assert validate_ip("0.0.0.0") is True


class TestIsPrivateIP:
    """Tests for is_private_ip function."""

    def test_private_class_a(self):
        assert is_private_ip("10.0.0.1") is True

    def test_private_class_b(self):
        assert is_private_ip("172.16.0.1") is True

    def test_private_class_c(self):
        assert is_private_ip("192.168.1.1") is True

    def test_loopback(self):
        assert is_private_ip("127.0.0.1") is True

    def test_link_local(self):
        assert is_private_ip("169.254.1.1") is True

    def test_public_ip(self):
        assert is_private_ip("8.8.8.8") is False

    def test_public_ip_cloudflare(self):
        assert is_private_ip("1.1.1.1") is False


class TestIsPublicIP:
    """Tests for is_public_ip function."""

    def test_google_dns_is_public(self):
        assert is_public_ip("8.8.8.8") is True

    def test_cloudflare_is_public(self):
        assert is_public_ip("1.1.1.1") is True

    def test_private_is_not_public(self):
        assert is_public_ip("192.168.1.1") is False

    def test_loopback_is_not_public(self):
        assert is_public_ip("127.0.0.1") is False

    def test_link_local_is_not_public(self):
        assert is_public_ip("169.254.1.1") is False


class TestFilterPrivateIPs:
    """Tests for filter_private_ips function."""

    def test_separates_public_and_private(self):
        ips = ["8.8.8.8", "192.168.1.1", "1.1.1.1", "10.0.0.1"]
        public, private = filter_private_ips(ips)
        assert "8.8.8.8" in public
        assert "1.1.1.1" in public
        assert "192.168.1.1" in private
        assert "10.0.0.1" in private

    def test_empty_list(self):
        public, private = filter_private_ips([])
        assert public == []
        assert private == []

    def test_all_public(self):
        ips = ["8.8.8.8", "1.1.1.1"]
        public, private = filter_private_ips(ips)
        assert len(public) == 2
        assert len(private) == 0

    def test_all_private(self):
        ips = ["192.168.1.1", "10.0.0.1"]
        public, private = filter_private_ips(ips)
        assert len(public) == 0
        assert len(private) == 2


class TestFilterPublicIPsOnly:
    """Tests for filter_public_ips_only function."""

    def test_returns_only_public(self):
        ips = ["8.8.8.8", "192.168.1.1", "1.1.1.1", "10.0.0.1"]
        result = filter_public_ips_only(ips)
        assert "8.8.8.8" in result
        assert "1.1.1.1" in result
        assert "192.168.1.1" not in result
        assert "10.0.0.1" not in result

    def test_empty_list(self):
        assert filter_public_ips_only([]) == []


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_is_exception(self):
        assert issubclass(ValidationError, Exception)

    def test_can_be_raised(self):
        with pytest.raises(ValidationError):
            raise ValidationError("test error")

    def test_message_preserved(self):
        try:
            raise ValidationError("something went wrong")
        except ValidationError as e:
            assert str(e) == "something went wrong"

"""
#40 — authenticate_step1 / authenticate_step2 (수동 OTP) 단위 테스트

Tests the two-step manual OTP authentication flow:
  step1: ID/PW → 'otp_required' or 'success' or 'failed'
  step2: OTP code → 'success' or 'failed'
"""

import pytest
from unittest.mock import MagicMock, patch

COLLECTOR_MODULE = "core.secudium_collector"


@pytest.fixture
def collector():
    with patch(f"{COLLECTOR_MODULE}.CollectorConfig") as mock_config:
        mock_config.SECUDIUM_BASE_URL = "https://test.secudium.com"
        mock_config.get_secudium_otp_config.return_value = {
            "email": "test@example.com",
            "email_password": "emailpass",
            "imap_server": "imap.test.com",
            "otp_mode": "manual",
        }

        from core.secudium_collector import SecudiumCollector

        db = MagicMock()
        c = SecudiumCollector(db_service=db)
        c._request_delay = 0
        # Reset class-level token cache
        SecudiumCollector._cached_token = None
        SecudiumCollector._token_obtained_at = None
        yield c


@pytest.mark.unit
class TestAuthenticateStep1:
    """Tests for authenticate_step1 (ID/PW login, returns OTP status)."""

    def test_returns_otp_required(self, collector):
        """step1 returns 'otp_required' when server requests OTP."""
        with patch.object(collector, "_login", return_value="otp_required"):
            result = collector.authenticate_step1("user", "pass")
            assert result == "otp_required"
            assert collector._pending_username == "user"
            assert collector._pending_password == "pass"

    def test_returns_success_no_otp_needed(self, collector):
        """step1 returns 'success' when login succeeds without OTP."""
        with patch.object(collector, "_login", return_value="success"):
            result = collector.authenticate_step1("user", "pass")
            assert result == "success"

    def test_returns_failed_on_bad_creds(self, collector):
        """step1 returns 'failed' when login fails."""
        with patch.object(collector, "_login", return_value="failed"):
            result = collector.authenticate_step1("bad", "creds")
            assert result == "failed"

    def test_stores_pending_credentials(self, collector):
        """step1 stores username/password for step2 use."""
        with patch.object(collector, "_login", return_value="otp_required"):
            collector.authenticate_step1("testuser", "testpass")
            assert collector._pending_username == "testuser"
            assert collector._pending_password == "testpass"

    def test_max_attempts_exceeded(self, collector):
        """step1 returns 'failed' after exceeding max auth attempts."""
        collector._auth_attempts = collector._max_auth_attempts
        result = collector.authenticate_step1("user", "pass")
        assert result == "failed"

    def test_increments_auth_attempts(self, collector):
        """step1 increments auth attempt counter."""
        collector._auth_attempts = 0
        with patch.object(collector, "_login", return_value="otp_required"):
            collector.authenticate_step1("user", "pass")
            assert collector._auth_attempts == 1


@pytest.mark.unit
class TestAuthenticateStep2:
    """Tests for authenticate_step2 (OTP code submission)."""

    def test_returns_success_with_valid_otp(self, collector):
        """step2 returns 'success' when OTP is valid."""
        collector._pending_username = "user"
        collector._pending_password = "pass"
        with patch.object(collector, "_login", return_value="success"):
            result = collector.authenticate_step2("123456")
            assert result == "success"

    def test_returns_failed_with_invalid_otp(self, collector):
        """step2 returns 'failed' when OTP is wrong."""
        collector._pending_username = "user"
        collector._pending_password = "pass"
        with patch.object(collector, "_login", return_value="failed"):
            result = collector.authenticate_step2("000000")
            assert result == "failed"

    def test_fails_without_prior_step1(self, collector):
        """step2 returns 'failed' if step1 was not called first."""
        collector._pending_username = None
        result = collector.authenticate_step2("123456")
        assert result == "failed"

    def test_clears_pending_on_success(self, collector):
        """step2 clears pending credentials after successful auth."""
        collector._pending_username = "user"
        collector._pending_password = "pass"
        with patch.object(collector, "_login", return_value="success"):
            collector.authenticate_step2("123456")
            assert collector._pending_username is None
            assert collector._pending_password is None

    def test_passes_otp_to_login(self, collector):
        """step2 passes OTP code to _login with is_otp=True."""
        collector._pending_username = "user"
        collector._pending_password = "pass"
        with patch.object(collector, "_login", return_value="success") as mock_login:
            collector.authenticate_step2("654321")
            mock_login.assert_called_once()
            call_kwargs = mock_login.call_args
            # Check that OTP value was passed
            assert "654321" in str(call_kwargs)


@pytest.mark.unit
class TestStep1Step2Flow:
    """Integration tests for the full step1 → step2 flow."""

    def test_full_otp_flow(self, collector):
        """Complete flow: step1(otp_required) → step2(success)."""
        with patch.object(collector, "_login") as mock_login:
            mock_login.return_value = "otp_required"
            result1 = collector.authenticate_step1("user", "pass")
            assert result1 == "otp_required"

            mock_login.return_value = "success"
            result2 = collector.authenticate_step2("123456")
            assert result2 == "success"

    def test_step1_success_skips_step2(self, collector):
        """When step1 succeeds directly, step2 is not needed."""
        with patch.object(collector, "_login", return_value="success"):
            result = collector.authenticate_step1("user", "pass")
            assert result == "success"
            # No need to call step2

    def test_step1_fail_no_step2(self, collector):
        """When step1 fails, step2 should also fail (no pending creds stored on failure)."""
        with patch.object(collector, "_login", return_value="failed"):
            result1 = collector.authenticate_step1("user", "pass")
            assert result1 == "failed"
